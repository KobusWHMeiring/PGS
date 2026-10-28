"""`relink_evidence` — rebuild a turn's evidence links after a `--force` re-ingest.

**Why this exists.** `--force` deletes the document and its chunks inside one transaction,
and `ChatMessage.retrieved_chunks` cascades with them: `HANDOVER.md` §17 records the cost
("`--force` stays out of `deploy.sh` — it destroys every `ChatMessage.retrieved_chunks`
trail"). The `grounding` snapshot (migration `core/0006`, P2.5a) was added so the *record*
of what an answer stood on survives that. This command is the other half: it turns the
snapshot back into rows **when the text is unchanged**, and says plainly when it cannot.

**What it must never do** is re-point a link at different words. A stored citation that
resolves to a passage it never quoted is the failure mode `build_principles.md` §I and
D68 Q8 name: a wrong answer that looks right. So a passage whose `text_sha` no longer
exists is reported as *text changed* and left unlinked — the snapshot still carries it.

The fixtures build the snapshot with the **real** `_grounding_snapshot()`, from chunks the
ORM created, and read it back with the real command. A hand-written snapshot dict would
encode the same assumption on both sides and pass while the product was broken
(`testing_hazards.md` §1.32).
"""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from core.models import ChatMessage, ChatSession
from core.services._chatbot import _grounding_snapshot
from core.services._evidence import relink_evidence
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.services import chunks_by_id

pytestmark = pytest.mark.django_db

SOURCE = "pgs_docs/saoso-version-2.1-2026.pdf"


@pytest.fixture
def corpus(db):
    standard_set = StandardSet.objects.create(
        code="outeniqua", label="Outeniqua", is_default=True
    )
    document = StandardDocument.objects.create(
        standard_set=standard_set,
        kind=StandardDocument.Kind.STANDARD,
        title="SAOSO Standard",
        version="2.1",
        source_file=SOURCE,
        sha256="a" * 64,
        section_scheme="saoso",
    )
    return document


@pytest.fixture
def session(corpus):
    return ChatSession.objects.create(standard_set=corpus.standard_set)


def _chunk(document, text, *, section_ref="S23.3", page=67, heading_path="23. HUMAN RIGHTS"):
    return DocumentChunk.objects.create(
        document=document,
        section_ref=section_ref,
        heading_path=heading_path,
        page=page,
        text=text,
    )


def _answered(session, document, chunks, *, question="What does 23.3 forbid?"):
    """A stored assistant turn whose grounding snapshot is the real one.

    The chunks are read back through the retrieval layer, exactly as `_ask` does, so the
    snapshot's locator and sha are produced by the code that produces them in production.
    """
    retrieved = chunks_by_id([chunk.pk for chunk in chunks], standard_set=document.standard_set)
    message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content="Operators shall not use forced or involuntary labour.",
        grounding=_grounding_snapshot(retrieved),
    )
    message.retrieved_chunks.set(chunk.pk for chunk in chunks)
    ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.USER, content=question
    )
    return message


def _rebuild(document, chunks):
    """What `--force` does to a document's chunks: they are deleted and re-created."""
    document.chunks.all().delete()
    return [_chunk(document, text, section_ref=ref, page=page) for text, ref, page in chunks]


def test_a_relink_restores_the_link_when_the_text_is_unchanged(corpus, session):
    """The whole point: the corpus was rebuilt, the words are the same, the link comes back."""
    first = _chunk(corpus, "Operators shall not use forced or involuntary labour.")
    second = _chunk(corpus, "Operators shall not discriminate.", section_ref="S23.5")
    message = _answered(session, corpus, [first, second])
    assert message.retrieved_chunks.count() == 2

    rebuilt = _rebuild(
        corpus,
        [
            ("Operators shall not use forced or involuntary labour.", "S23.3", 67),
            ("Operators shall not discriminate.", "S23.5", 68),
        ],
    )
    message.refresh_from_db()
    assert message.retrieved_chunks.count() == 0, "the fixture did not simulate a rebuild"

    report = relink_evidence(write=True)

    assert report.relinked == 2, report
    message.refresh_from_db()
    assert set(message.retrieved_chunks.values_list("pk", flat=True)) == {
        chunk.pk for chunk in rebuilt
    }, "the links point at the old rows, not the ones the corpus now holds"


def test_a_dry_run_reports_and_writes_nothing(corpus, session):
    """The default has to be safe: an operator reads the counts before anything is written."""
    _answered(session, corpus, [_chunk(corpus, "The words the paper prints.")])
    _rebuild(corpus, [("The words the paper prints.", "S23.3", 67)])

    report = relink_evidence()

    assert report.relinked == 1
    assert report.written is False
    assert ChatMessage.objects.get(role=ChatMessage.Role.ASSISTANT).retrieved_chunks.count() == 0


def test_a_passage_whose_text_changed_is_named_and_not_linked(corpus, session):
    """`m²` merged into one line is a *different passage*, and a link would be a lie.

    This is the shape of the corpus work the command exists to make safe: the three
    letterspaced lines and the superscript are exactly sentences whose text will change.
    """
    _answered(
        session,
        corpus,
        [_chunk(corpus, "more\n\n 2 \n\nthan 25kg weight/m .")],
    )
    _rebuild(corpus, [("more than 25kg weight/m².", "S23.3", 67)])

    report = relink_evidence(write=True)

    assert report.relinked == 0
    assert report.text_changed == 1, report
    assert report.unresolved[0].locator == "S23.3"
    assert ChatMessage.objects.get(role=ChatMessage.Role.ASSISTANT).retrieved_chunks.count() == 0


def test_a_passage_the_document_no_longer_has_is_reported_as_gone(corpus, session):
    """A re-ingest that drops a section must say so rather than silently relink nothing."""
    _answered(session, corpus, [_chunk(corpus, "A clause the artefact will remove.")])
    _rebuild(corpus, [("A different clause entirely.", "S23.9", 69)])

    report = relink_evidence(write=True)

    assert report.relinked == 0
    assert report.gone == 1, report
    assert report.text_changed == 0, "a removed locator is not a changed passage"


def test_thirty_rows_sharing_a_locator_are_told_apart_by_their_own_text(corpus, session):
    """Appendix 2 prints 30 rows under one locator — the case a locator-only match corrupts.

    Thirty rows all carry `section_ref="Appendix 2"`, so a relink that matched on the
    locator alone would attach "cardboard" to "Farmyard manure" — the D68 Q8 defect,
    reintroduced by the repair tool. The sha is what keeps them apart.
    """
    rows = [
        _chunk(corpus, "Farmyard manure, slurry and urine.", section_ref="Appendix 2", page=76),
        _chunk(corpus, "Wood, bark and sawdust.", section_ref="Appendix 2", page=76),
        _chunk(corpus, "Cardboard.", section_ref="Appendix 2", page=76),
    ]
    message = _answered(session, corpus, [rows[2]])

    rebuilt = _rebuild(
        corpus,
        [
            ("Farmyard manure, slurry and urine.", "Appendix 2", 76),
            ("Wood, bark and sawdust.", "Appendix 2", 76),
            ("Cardboard.", "Appendix 2", 76),
        ],
    )
    report = relink_evidence(write=True)

    assert report.relinked == 1
    message.refresh_from_db()
    linked = message.retrieved_chunks.get()
    assert linked.text == "Cardboard.", f"relinked to {linked.text!r} — the wrong row"
    assert linked.pk == rebuilt[2].pk


def test_a_second_run_does_not_duplicate_the_link(corpus, session):
    """Operators run this until the numbers look right; a repeat must be a no-op."""
    _answered(session, corpus, [_chunk(corpus, "A clause that survives the rebuild.")])
    _rebuild(corpus, [("A clause that survives the rebuild.", "S23.3", 67)])

    relink_evidence(write=True)
    second = relink_evidence(write=True)

    message = ChatMessage.objects.get(role=ChatMessage.Role.ASSISTANT)
    assert message.retrieved_chunks.count() == 1
    assert second.already_linked == 1, second
    assert second.relinked == 0


def test_a_turn_with_no_snapshot_is_counted_and_left_alone(corpus, session):
    """50 of this instance's 60 assistant turns predate `core/0006`; the command must say so.

    It cannot invent evidence for them, and it must not count them as a defect it
    repaired — the honest output is "no snapshot, nothing to do".
    """
    _answered(session, corpus, [_chunk(corpus, "A clause with a snapshot.")])
    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content="An answer recorded before the snapshot existed.",
    )
    _rebuild(corpus, [("A clause with a snapshot.", "S23.3", 67)])

    report = relink_evidence(write=True)

    assert report.without_snapshot == 1, report
    assert report.examined == 2
    assert report.relinked == 1


def test_the_command_prints_the_counts_and_requires_apply_to_write(corpus, session, capsys):
    """Thin command, thick service: `--apply` is the only way this writes anything."""
    _answered(session, corpus, [_chunk(corpus, "A clause the operator wants linked.")])
    _rebuild(corpus, [("A clause the operator wants linked.", "S23.3", 67)])

    call_command("relink_evidence")
    dry = capsys.readouterr().out
    assert "relinkable" in dry.lower(), dry
    assert "Nothing was written" in dry, "a dry run must say it wrote nothing"
    assert ChatMessage.objects.get(role=ChatMessage.Role.ASSISTANT).retrieved_chunks.count() == 0

    call_command("relink_evidence", "--apply")
    applied = capsys.readouterr().out
    assert "1 passage(s) relinked" in applied, applied
    assert ChatMessage.objects.get(role=ChatMessage.Role.ASSISTANT).retrieved_chunks.count() == 1


def test_a_snapshot_naming_a_document_the_corpus_lost_is_not_linked_to_another(corpus, session):
    """Scoped by document: a same-locator passage in a *different* document is not the passage.

    The OPP and SAOSO both print a `S1`-shaped locator in places; attaching one document's
    evidence to the other's text would be a citation to a file the answer never read.
    """
    clause = "Operators shall not use forced or involuntary labour."
    _answered(session, corpus, [_chunk(corpus, clause)])
    other = StandardDocument.objects.create(
        standard_set=corpus.standard_set,
        kind=StandardDocument.Kind.PRINCIPLES,
        title="Principles, Policies & Procedures",
        source_file="pgs_docs/opp.pdf",
        sha256="b" * 64,
        section_scheme="opp",
    )
    # The OPP prints the *same words* under the *same locator* — a plausible accident,
    # and the only arrangement in which document scoping is what prevents the link.
    _chunk(other, clause, section_ref="S23.3", page=67)
    corpus.chunks.all().delete()

    report = relink_evidence(write=True)

    assert report.relinked == 0, "a same-locator passage in another document was linked"
    assert report.gone == 1, report
    assert ChatMessage.objects.get(role=ChatMessage.Role.ASSISTANT).retrieved_chunks.count() == 0


def test_the_command_refuses_to_report_success_when_nothing_was_examined(corpus):
    """An empty run must be visible, not a silent green.

    `testing_hazards.md` §1.6: a command whose guard matches nothing reports success. A
    corpus with no chat history relinks zero passages, and that is a fact about the
    instance — printed, not passed over.
    """
    with pytest.raises(CommandError, match="no assistant turns"):
        call_command("relink_evidence")
