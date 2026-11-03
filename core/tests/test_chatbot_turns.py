"""What a turn records, what a citation links to, and how a table is shown.

Three slices, one subject — the *stored* side of an answer:

* P2.5a — the turn records what it claimed and which check refused it, and a re-ingest
  does not erase it (D59 keeps transcripts indefinitely).
* A2 — a stored citation knows the public document it came from, so `/ask/` links to it.
* D79 option E — a reviewed table is shown as structure, and a quote of its cells knows
  the printed column it came from.
"""

from __future__ import annotations

import pytest

from core.models import ChatMessage, EscalatedQuery
from core.services._chatbot import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    audit_citations,
    build_prompt,
)
from core.tests.chat_helpers import (
    ask as _ask,
    grounded_reply as _grounded_reply,
    retrieved_from_stored as _retrieved_from_stored,
)

pytestmark = pytest.mark.django_db


# --- P2.5a: the turn records what it claimed, and what refused it ------------
#
# G9 was a refusal on the live site that was indistinguishable from a coverage gap:
# `EscalatedQuery.reason` said `CITATION_AUDIT`, the retrieved chunks were stored, and
# the citation the model actually returned was gone. Diagnosing it needed a re-ask of the
# model against the box's database (`scripts/why_refused.py`), which is a measurement
# nobody can reproduce later. These tests pin the record instead.

def test_a_grounded_answer_records_what_it_claimed(
    chat_session, chat_corpus, fake_chat_model, chat_cache
):
    model = fake_chat_model(reply=_grounded_reply())

    out = _ask(chat_session, "What does the standard require for traceability?", model)
    message = ChatMessage.objects.get(pk=out.message_id)

    assert message.prompt_version == PROMPT_VERSION
    assert message.corpus_fingerprint, "an answer must be attributable to a corpus"
    assert message.refusal_checks == []
    assert message.citations["accepted"], "the citation the visitor saw must be stored"
    accepted = message.citations["accepted"][0]
    assert accepted["section_ref"] == "S20.1.1"
    assert accepted["quote"] and accepted["document"]
    assert message.citations["raw"][0]["section_ref"] == "S20.1.1"

    assert message.grounding, "the passages it stood on must be recorded"
    assert {"locator", "page", "heading_path", "document", "text_sha"} <= set(
        message.grounding[0]
    )


def test_a_refused_citation_records_which_check_fired(
    chat_session, chat_corpus, fake_chat_model, chat_cache
):
    """`CITATION_AUDIT` alone cannot tell a prompt defect from a corpus defect."""
    model = fake_chat_model(
        reply=_grounded_reply(
            citations=(
                {
                    "section_ref": "S20.1.1",
                    "quote": "a sentence the passage does not contain anywhere at all",
                },
            )
        )
    )

    out = _ask(chat_session, "What does the standard require for traceability?", model)
    message = ChatMessage.objects.get(pk=out.message_id)

    assert out.insufficient_context
    assert message.refusal_checks, "the refusal must say which check refused it"
    assert "not in the cited chunk" in message.refusal_checks[0]
    assert message.citations["accepted"] == []
    assert message.citations["raw"][0]["quote"].startswith("a sentence the passage")
    assert message.prompt_version == PROMPT_VERSION
    assert EscalatedQuery.objects.get(pk=out.escalated_query_id).reason == (
        EscalatedQuery.Reason.CITATION_AUDIT
    )


def test_the_grounding_snapshot_survives_a_corpus_rebuild(
    chat_session, chat_corpus, fake_chat_model, chat_cache
):
    """`--force` deletes the chunks and takes the M2M rows with them.

    D59 keeps transcripts indefinitely; a routine re-ingest must not erase what they
    stood on. This simulates the rebuild by deleting every chunk, which is what the
    ingest transaction does to a document's chunks.
    """
    from knowledge.models import DocumentChunk

    model = fake_chat_model(reply=_grounded_reply())
    out = _ask(chat_session, "What does the standard require for traceability?", model)
    message = ChatMessage.objects.get(pk=out.message_id)
    assert message.retrieved_chunks.exists()
    before = [entry["locator"] for entry in message.grounding]
    assert before, (
        "an empty snapshot would make this test pass by comparing [] with [] — the "
        "exact defect it exists to catch (build_principles §VIII)"
    )

    DocumentChunk.objects.all().delete()
    message.refresh_from_db()

    assert message.retrieved_chunks.count() == 0, "the M2M is expected to cascade"
    assert [entry["locator"] for entry in message.grounding] == before


def test_a_cached_answer_still_records_its_citations(
    chat_session, chat_corpus, fake_chat_model, chat_cache
):
    """The cache must not turn the second turn into evidence-free history."""
    question = "What does the standard require for traceability?"
    model = fake_chat_model(reply=_grounded_reply())

    _ask(chat_session, question, model)
    second = _ask(chat_session, question, model)

    assert second.cached is True
    assert len(model.calls) == 1
    message = ChatMessage.objects.get(pk=second.message_id)
    assert message.citations["accepted"][0]["section_ref"] == "S20.1.1"
    assert message.grounding


# --- A2: a citation knows the public document it came from -------------------


@pytest.fixture
def published_saoso(db):
    """The published row whose `source_path` matches the ingested document's `source_file`.

    That equality is the whole join: the publish seed and the ingest read the same
    `pgs_docs/` filenames, and `source_path` exists so a published file can be traced to the
    shipped document. No mapping table, and nothing to migrate.
    """
    from core.models import PublicDocument

    return PublicDocument.objects.create(
        code="saoso-standard-v2.1",
        title="SAOSO Organic Standard v2.1",
        file_path="public/documents/saoso-standard-v2.1.pdf",
        source_path="pgs_docs/saoso-version-2.1-2026.pdf",
        is_published=True,
    )


def test_a_citation_knows_the_public_document_it_came_from(
    chat_session, chat_corpus, fake_chat_model, published_saoso
):
    model = fake_chat_model(reply=_grounded_reply())

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    citation = out.citations[0]
    assert citation.document_code == "saoso-standard-v2.1"
    assert citation.reading_anchor == "s20-1-1"
    assert citation.read_url == (
        "/documents/saoso-standard-v2.1/read/?section=s20-1-1#s20-1-1"
    )


def test_a_corpus_document_with_no_published_twin_carries_no_code(
    chat_session, chat_corpus, fake_chat_model
):
    """The link must be **absent**, not broken.

    A corpus may be ingested from a document the group does not publish. The citation is
    still showable — the quote is the evidence — but a link to nowhere is worse than plain
    text, so `read_url` is empty and the template renders no anchor tag.
    """
    model = fake_chat_model(reply=_grounded_reply())

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert out.citations[0].document_code == ""
    assert out.citations[0].read_url == ""


def test_the_stored_citation_can_still_link_after_a_re_ingest(
    chat_session, chat_corpus, fake_chat_model, published_saoso
):
    """A card outlives the corpus, so the code and the anchor go into the snapshot.

    Resolving them at render time would let a page silently re-point a citation after a
    rebuild — a claim nobody can audit (P2.5a's reasoning, applied to the board).
    """
    model = fake_chat_model(reply=_grounded_reply())

    out = _ask(chat_session, "What does the standard require for traceability?", model)
    stored = ChatMessage.objects.get(pk=out.message_id).citations["accepted"][0]

    assert stored["document_code"] == "saoso-standard-v2.1"
    assert stored["reading_anchor"] == "s20-1-1"


# --- D79 option E, slice 2: a table is shown as a table ----------------------#


def _table_row_chunk(chat_corpus):
    """A stored row chunk carrying its reviewed table's columns, as retrieval labels it."""
    from dataclasses import replace

    from knowledge.table_context import TableContext

    chunk = chat_corpus.fee
    table = TableContext(
        title="2.3 PGS assessment fee structure (initial certification and renewal)",
        columns=(
            "Annual farm turnover (gross sales)",
            "Initial certification fee (R)",
            "Renewal fee (R)",
        ),
        section_ref=chunk.section_ref,
        row_label="Below R 250,000",
    )
    return replace(
        _retrieved_from_stored(chunk, chunk.document.standard_set), table=table
    )


def test_a_reviewed_table_is_shown_as_structure(chat_corpus, chat_standard_set):
    """Columns once, above the rows, and the row's cells exactly as printed (D79/E).

    This is option E's whole mechanism: the model can see which cell is which column, and
    the quote it copies is still a substring of the row's own chunk text — so the audit
    needs no new rule. Option A (pasting the heading into each row) is what this replaces;
    it repeats a line the paper prints once.
    """
    from core.services._chatbot import build_prompt

    row = _table_row_chunk(chat_corpus)
    prompt = build_prompt("What does the passage say?", [row], [])

    assert "TABLE: 2.3 PGS assessment fee structure" in prompt
    assert "Annual farm turnover (gross sales) | Initial certification fee (R)" in prompt
    assert prompt.count("Renewal fee (R)") == 1, "the headings were repeated per row"
    assert row.text in prompt, "the row was reformatted, so its quote would be refused"
    assert "|" not in row.text


def test_a_quote_of_the_row_cells_is_still_accepted(chat_corpus, chat_standard_set):
    row = _table_row_chunk(chat_corpus)
    citations, problems = audit_citations(
        [{"section_ref": row.section_ref or row.anchor, "quote": row.text}],
        [row],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].row_label == "Below R 250,000", (
        "the citation must know which row it quotes; slice 3 renders its context from it"
    )


# --- D79 option E, slice 3: the quote knows its column, and the link carries it --


def _fee_band_row(chat_corpus):
    """A retrieved chunk whose text is the band's printed cells, with its reviewed table.

    The double in `_table_row_chunk` keeps the fixture's sentence text because it tests the
    prompt shape; a citation's column can only be resolved from the cells the paper prints.
    """
    from dataclasses import replace

    from knowledge.services import RetrievedChunk
    from knowledge.table_context import TableContext

    chunk = chat_corpus.fee
    table = TableContext(
        title="2.3 PGS assessment fee structure (initial certification and renewal)",
        columns=(
            "Annual farm turnover (gross sales)",
            "Initial certification fee (R)",
            "Renewal fee (R)",
        ),
        section_ref="§2.3",
        row_label="Below R 250,000",
        cells=("Below R 250,000", "1,500", "900"),
    )
    return replace(
        _retrieved_from_stored(chunk, chunk.document.standard_set),
        text="Below R 250,000\n1,500\n900",
        section_ref="§2.3",
        heading_path="2.3 PGS assessment fee structure",
        table=table,
    )


def test_a_quoted_cell_knows_its_printed_column(chat_corpus, chat_standard_set):
    """Slice 3: the frame is row **and column**, both rendered from the reviewed table.

    Without the column the citation shows `Table row: Below R 250,000` above `900`, and a
    reader still cannot tell a renewal fee from an initial one — the ambiguity the whole
    decision exists to remove.
    """
    row = _fee_band_row(chat_corpus)

    citations, problems = audit_citations(
        [{"section_ref": "§2.3", "quote": "900"}],
        [row],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].row_label == "Below R 250,000"
    assert citations[0].column_label == "Renewal fee (R)"


def test_a_quote_spanning_cells_gets_no_column(chat_corpus, chat_standard_set):
    """D79-2 lets consecutive cells be quoted together; naming one column would be a lie."""
    row = _fee_band_row(chat_corpus)

    citations, problems = audit_citations(
        [{"section_ref": "§2.3", "quote": "1,500\n900"}],
        [row],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].row_label == "Below R 250,000", "the row context still applies"
    assert citations[0].column_label == "", "two cells is not one column"


def test_the_reader_link_carries_the_quote_only_when_a_row_frames_it(chat_corpus):
    """The reader marks the quoted cell, so the link has to name it — and only then.

    A prose citation has no row and no cell; adding `quote=` to every link would make the
    reader search every branch for a paragraph and mark nothing, for no reason.
    """
    from core.services._chatbot import Citation

    framed = Citation(
        section_ref="§2.3",
        quote="900",
        chunk_id=1,
        document_code="opp",
        reading_anchor="below-r-250-000",
        row_label="Below R 250,000",
        column_label="Renewal fee (R)",
    )
    assert "quote=900" in framed.read_url
    assert framed.read_url.endswith("#below-r-250-000")

    plain = Citation(
        section_ref="S20.1.1",
        quote="Records must be kept.",
        chunk_id=2,
        document_code="saoso-standard-v2.1",
        reading_anchor="s20-1-1",
    )
    assert "quote=" not in plain.read_url


def test_the_snapshot_keeps_the_row_and_column_of_a_citation(chat_corpus, chat_standard_set):
    """A card outlives the corpus, so the frame is stored with the quote (D79/E).

    The answer page reads the snapshot, not the corpus. Before slice 3 the snapshot dropped
    `row_label`, so a card silently rendered no context while the transcript rendered it —
    two surfaces disagreeing about the same citation.
    """
    from core.services._chatbot import citation_records

    row = _fee_band_row(chat_corpus)
    citations, _problems = audit_citations(
        [{"section_ref": "§2.3", "quote": "900"}],
        [row],
        standard_set_id=chat_standard_set.pk,
    )

    records = citation_records(citations)

    assert records[0]["row_label"] == "Below R 250,000"
    assert records[0]["column_label"] == "Renewal fee (R)"


def test_the_system_prompt_says_the_headings_are_not_quotable():
    """Without this rule the model quotes the heading it was shown, and the audit refuses."""
    lowered = SYSTEM_PROMPT.lower()
    assert "8b." in lowered
    assert "context, not evidence" in lowered
    assert "never include a column heading" in lowered
