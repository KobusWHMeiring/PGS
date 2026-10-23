"""Task D2 — `answer_question()`: grounded answers and the refusal.

The product argument is the refusal. Anyone can wire a model to a prompt; the claim
this feature makes is that the assistant **declines rather than guesses**, and that a
confident-sounding answer with no citation is refused even when the model set
`insufficient_context: false`.

Two strings matter and both are asserted exactly:

* `REFUSAL` — D17's wide-corpus wording. The old SAOSO-only string is wrong because
  the OPP answers questions the standard does not (fees, joining, procedure).
* the refusal is **never** a fabricated answer when Gemini is down. `UpstreamModelError`
  propagates; the view shows an honest unavailable notice.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.models import ChatMessage, EscalatedQuery
from core.services._chatbot import (
    REFUSAL,
    RETRIEVAL_LIMIT,
    SYSTEM_PROMPT,
    GroundedAnswer,
    InvalidQuestionError,
    ModelReply,
    SessionNotFoundError,
    UpstreamModelError,
    answer_question,
    audit_citations,
    build_prompt,
    chat_retrieval_limit,
    default_retrieval,
)

@pytest.fixture(autouse=True)
def committed_extraction(monkeypatch):
    """Ingest from the committed BPP pages, not through a PDF reader (D57).

    Two tests below build a real stored chunk by ingesting `pgs_docs/`. The gate runs with
    `PDFTOTEXT_BIN` pointed at a path that cannot exist, so the bytes come from
    `knowledge/tests/fixtures/pages/` — the same bytes, committed as evidence.
    """
    from knowledge.tests.page_fixtures import stub_ingest_extraction

    stub_ingest_extraction(monkeypatch)


pytestmark = pytest.mark.django_db


def _grounded_reply(**overrides):
    fields = {
        "answer": "Records must let a product be traced from farm to buyer.",
        "citations": (
            {
                "section_ref": "S20.1.1",
                "quote": "Traceability is required for every batch of organic product",
            },
        ),
        "insufficient_context": False,
        "model": "fake-model",
        "prompt_tokens": 140,
        "completion_tokens": 36,
    }
    fields.update(overrides)
    return ModelReply(**fields)


def _ask(session, question, provider, **kwargs):
    return answer_question(
        session.public_uuid, question, provider=provider, ip_hash="", **kwargs
    )


# --- The refusal ------------------------------------------------------------


def test_the_system_prompt_forbids_unsupported_claims():
    """The static claim sweep cannot see a generated sentence; the prompt must."""
    lowered = SYSTEM_PROMPT.lower()
    for term in ("pasture raised", "gmo free", "biodynamic", "chemical-free", "spray-free"):
        assert term in lowered, f"{term!r} is not named in the system prompt"


def test_the_shipped_retrieval_budget_and_the_fallback_agree(settings):
    """One number, not two that are believed to be one.

    The 2026-10-21 answer-coverage work changed `RETRIEVAL_LIMIT` from 5 to 8, but
    `settings.CHAT_RETRIEVAL_LIMIT` always exists, so the constant is a fallback that is
    never read and the product kept a five-passage budget. Measured 2026-10-22: at 5 the
    cardboard question returns no inputs clause and refuses; at 8 it answers from
    Appendix 2 (`testing_hazards.md` §2.7).
    """
    assert settings.CHAT_RETRIEVAL_LIMIT == 8
    assert RETRIEVAL_LIMIT == settings.CHAT_RETRIEVAL_LIMIT
    assert chat_retrieval_limit() == settings.CHAT_RETRIEVAL_LIMIT


def test_default_retrieval_passes_the_shipped_budget(chat_standard_set, monkeypatch, settings):
    """`default_retrieval` is the view's path; it must use the setting, not a literal."""
    from core.services import _chatbot

    seen: dict[str, object] = {}

    def spy(terms, *, standard_set, limit, question):
        seen["terms"] = terms
        seen["limit"] = limit
        return _chatbot.RetrievalResult(
            query=question,
            standard_set_id=standard_set.pk,
            lexical_only=True,
        )

    monkeypatch.setattr(_chatbot, "search_terms", spy)
    settings.CHAT_RETRIEVAL_LIMIT = 3

    default_retrieval("how do I sign up?", chat_standard_set)

    assert seen["limit"] == 3
    assert seen["terms"] == ["sign"]


def test_the_refusal_is_the_d17_wording():
    """A guard on the guard: the exact string is the contract, not a paraphrase."""
    assert REFUSAL == (
        "I cannot find a definitive answer in the SAOSO standard or the Outeniqua "
        "PGS documents."
    )


def test_the_system_prompt_allows_a_governing_rule_when_the_item_is_not_named():
    """D17 revised (2026-10-21): a rule the standard states is an answer.

    "Can I use cardboard from my neighbours?" is governed by SAOSO 4.4.4 (material
    applied to land must comply with Appendix 2) even though the standard never names
    cardboard. The old rule allowed only a *definitive* answer, so a governing rule was
    refused. The replacement must still forbid two things: inventing the missing detail,
    and reading permission into silence.
    """
    lowered = SYSTEM_PROMPT.lower()
    assert "governs the question" in lowered
    assert "does not name" in lowered
    assert "silence is not permission" in lowered
    assert "insufficient_context" in lowered


def test_an_answer_that_says_the_item_is_not_named_is_grounded(
    chat_session, chat_corpus, fake_chat_model
):
    """A named gap plus a cited rule is a grounded answer, not a refusal.

    This is the shape the cardboard question produces: say plainly that the document
    does not name the item, state the rule that governs it, and cite the passage. The
    citation audit still decides — an unsupported sentence in the same reply would not
    be rescued by this test.
    """
    model = fake_chat_model(
        reply=_grounded_reply(
            answer=(
                "The standard does not name cardboard. It requires traceability for "
                "every batch of organic product."
            ),
        )
    )

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert out.text != REFUSAL
    assert out.insufficient_context is False
    assert len(out.citations) == 1
    assert EscalatedQuery.objects.count() == 0


def test_an_ungrounded_question_refuses_and_escalates(chat_session, fake_chat_model):
    model = fake_chat_model(
        reply=_grounded_reply(
            answer="Buy the blue fertiliser from the shop in George.",
            citations=(),
            insufficient_context=True,
        )
    )

    out = _ask(chat_session, "Which fertiliser brand should I buy in George?", model)

    assert out.text == REFUSAL
    assert out.insufficient_context is True
    assert out.citations == []
    assert EscalatedQuery.objects.count() == 1
    assert EscalatedQuery.objects.get().reason == EscalatedQuery.Reason.INSUFFICIENT_CONTEXT


def test_refusal_fires_on_empty_citations_even_if_the_flag_is_false(
    chat_session, chat_corpus, fake_chat_model
):
    """The structured flag is not trusted on its own.

    A model can be confident and cite nothing. The fix for the brittle prose-scraping
    contract (SPEC §13) is not "trust the boolean more" — it is to require a citation
    that survives an audit.
    """
    model = fake_chat_model(
        reply=_grounded_reply(answer="The fee is R100.", citations=(), insufficient_context=False)
    )

    out = _ask(chat_session, "What is the membership fee?", model)

    assert out.text == REFUSAL
    assert out.insufficient_context is True
    escalation = EscalatedQuery.objects.get()
    assert escalation.reason == EscalatedQuery.Reason.NO_CITATIONS
    assert escalation.question == "What is the membership fee?"


def test_no_retrieved_chunks_means_the_model_is_never_called(
    chat_standard_set, chat_corpus, fake_chat_model
):
    """Nothing to ground on ⇒ nothing to ask the model.

    A model given an empty context will happily answer from memory. The refusal has
    to happen before the call, not after the prose has been judged.
    """
    from core.models import ChatSession

    session = ChatSession.objects.create(standard_set=chat_standard_set)
    model = fake_chat_model(reply=_grounded_reply())

    out = _ask(session, "What is the zoning rule for a herd of zebra in Alberta?", model)

    assert out.text == REFUSAL
    assert model.calls == [], "the model was called with no retrieved context"
    assert EscalatedQuery.objects.count() == 1


# --- A grounded answer ------------------------------------------------------


def test_a_grounded_answer_is_returned_with_its_citation(chat_session, chat_corpus, fake_chat_model):
    model = fake_chat_model(reply=_grounded_reply())

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert isinstance(out, GroundedAnswer)
    assert out.text == _grounded_reply().answer
    assert out.insufficient_context is False
    assert out.cached is False
    assert len(out.citations) == 1
    citation = out.citations[0]
    assert citation.section_ref == "S20.1.1"
    assert citation.chunk_id == chat_corpus.traceability.pk
    assert citation.document.startswith("SAOSO Standard")
    assert citation.page == 43
    assert EscalatedQuery.objects.count() == 0


def test_both_sides_of_the_exchange_are_persisted(chat_session, chat_corpus, fake_chat_model):
    model = fake_chat_model(reply=_grounded_reply())

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert ChatMessage.objects.filter(session=chat_session).count() == 2
    user, assistant = list(chat_session.messages.all())
    assert user.role == ChatMessage.Role.USER
    assert user.content == "What does the standard require for traceability?"
    assert assistant.pk == out.message_id
    assert assistant.role == ChatMessage.Role.ASSISTANT
    assert assistant.content == _grounded_reply().answer
    assert assistant.model == "fake-model"
    assert assistant.prompt_tokens == 140
    assert assistant.completion_tokens == 36
    assert assistant.latency_ms is not None
    assert assistant.retrieved_chunks.count() >= 1, "the evidence was not recorded"


def test_the_refusal_is_persisted_as_the_assistant_message(chat_session, fake_chat_model):
    model = fake_chat_model(reply=_grounded_reply(citations=()))

    _ask(chat_session, "What is the membership fee?", model)

    assistant = ChatMessage.objects.get(role=ChatMessage.Role.ASSISTANT)
    assert assistant.content == REFUSAL


# --- Failures are never answers --------------------------------------------


def test_an_upstream_failure_never_fabricates_an_answer(chat_session, chat_corpus, fake_chat_model):
    model = fake_chat_model(error=UpstreamModelError("Gemini is down"))

    with pytest.raises(UpstreamModelError):
        _ask(chat_session, "What does the standard require for traceability?", model)

    assert ChatMessage.objects.filter(role=ChatMessage.Role.ASSISTANT).count() == 0
    assert EscalatedQuery.objects.count() == 0, "a transport failure is not a corpus gap"


# --- Validation -------------------------------------------------------------


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
def test_a_blank_question_is_rejected_before_any_side_effect(
    chat_session, fake_chat_model, question
):
    model = fake_chat_model(reply=_grounded_reply())

    with pytest.raises(InvalidQuestionError):
        _ask(chat_session, question, model)

    assert model.calls == []
    assert ChatMessage.objects.count() == 0


def test_a_question_over_five_hundred_characters_is_rejected(chat_session, fake_chat_model):
    model = fake_chat_model(reply=_grounded_reply())

    with pytest.raises(InvalidQuestionError):
        _ask(chat_session, "x" * 501, model)

    assert model.calls == []
    assert ChatMessage.objects.count() == 0


def test_an_unknown_session_is_not_silently_created(fake_chat_model):
    import uuid

    model = fake_chat_model(reply=_grounded_reply())

    with pytest.raises(SessionNotFoundError):
        answer_question(uuid.uuid4(), "What is the membership fee?", provider=model, ip_hash="")

    assert model.calls == []


def test_exactly_five_hundred_characters_is_allowed(chat_session, chat_corpus, fake_chat_model):
    """The cap is 500, not 499 — an off-by-one here rejects a valid question."""
    model = fake_chat_model(reply=_grounded_reply())

    out = _ask(chat_session, "traceability " * 38 + "traceability"[:6], model)

    assert out.text
    assert model.calls


# --- D46: the corpus sentence is quotable, and the audit stays strict --------
#
# The manure question was refused twice on 2026-10-19. One of the two causes was
# corruption at ingest: the BPP page is two-column, `pdftotext -layout` interleaved
# it, and the sentence the model quoted could not be a substring of any chunk.
#
# These tests run the *real* audit over *really ingested* bytes. The first pins the
# corpus fix; the second pins the audit's strictness, so a later session cannot make
# a recorded paraphrased reply pass by loosening the rule.

PDF_DIR = Path(__file__).resolve().parents[2] / "pgs_docs"
BPP_PDF = PDF_DIR / "Basic Production Principles_ENG_PRINT.pdf"

#: The model's actual 2026-10-19 quote. It is a paraphrase — "must preferably be
#: composted and sourced from…" where the standard prints "must be preferably
#: composted prior to application, and must be sourced from…". A perfect corpus does
#: not make it verbatim.
RECORDED_PARAPHRASE = (
    "Animal manure must preferably be composted and sourced from farms under organic "
    "management or extensive farming practices"
)


def _retrieved_from_stored(chunk, standard_set):
    from knowledge.services import RetrievedChunk

    return RetrievedChunk(
        chunk_id=chunk.pk,
        document_title=chunk.document.title,
        document_version=chunk.document.version,
        section_ref=chunk.section_ref,
        heading_path=chunk.heading_path,
        page=chunk.page,
        anchor=chunk.anchor,
        text=chunk.text,
        score=1.0,
        standard_set_id=standard_set.pk,
        sub_refs=tuple(chunk.sub_refs or ()),
    )


def _stored_bpp_manure_chunk(standard_set):
    from knowledge.ingest import ingest_standard
    from knowledge.models import DocumentChunk

    ingest_standard(
        pdf_path=BPP_PDF, standard_set=standard_set, doc_key="bpp", embed=False
    )
    return DocumentChunk.objects.get(
        document__title__contains="Basic Production", text__contains="Animal manure"
    )


def test_the_verbatim_corpus_sentence_is_accepted_by_the_audit(chat_standard_set):
    from knowledge.tests.test_columns import BPP_SENTENCE

    chunk = _stored_bpp_manure_chunk(chat_standard_set)
    retrieved = _retrieved_from_stored(chunk, chat_standard_set)

    citations, problems = audit_citations(
        [{"section_ref": chunk.anchor, "quote": BPP_SENTENCE}],
        [retrieved],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].quote == BPP_SENTENCE
    assert citations[0].anchor == "general-principles"


def test_the_paraphrased_live_reply_is_still_refused(chat_standard_set):
    """A perfect corpus does not make a paraphrase verbatim.

    The refusal is the point: a reordered or reworded passage is not a quote, and
    this pins the audit's strictness rather than relaxing it to fit a bad answer.
    """
    chunk = _stored_bpp_manure_chunk(chat_standard_set)
    retrieved = _retrieved_from_stored(chunk, chat_standard_set)

    citations, problems = audit_citations(
        [{"section_ref": chunk.anchor, "quote": RECORDED_PARAPHRASE}],
        [retrieved],
        standard_set_id=chat_standard_set.pk,
    )

    assert citations == []
    assert problems == (f"{chunk.anchor}: the quote is not in the cited chunk",)


# --- D52: the two refusals that were the corpus's fault ---------------------
#
# The live 2026-10-21 probe refused two correct answers (CHAT_ANSWER_COVERAGE_PRD.md
# G1/G2). Both were blamed on the model, and both were the corpus: `pdftotext -layout`
# had wrapped a hyphenated word — `per non-` / page footer / `ruminant` — so no quote
# of the printed sentence could be a substring. The fix is ingest-side (`reflow.py`,
# `is_furniture`); the audit is untouched, and these tests pin both halves: the
# recorded elision is still refused, the repaired sentence is accepted.

SAOSO_PDF = PDF_DIR / "saoso-version-2.1-2026.pdf"

#: The model's actual 2026-10-21 quote for the ducks question, before D52. It elided
#: the word the corpus had mangled. A correct corpus does not make an elision a quote.
RECORDED_ELISION = (
    "The percentage of non-organic feed may not exceed ... 15% dry matter per "
    "non-ruminant calculated on an annual basis."
)

#: What the page prints, and what the audit now finds.
S5_5_1_SENTENCE = (
    "The percentage of non-organic feed may not exceed 10% dry matter per ruminant "
    "and 15% dry matter per non-ruminant calculated on an annual basis."
)


def _stored_saoso_chunk(standard_set, section_ref: str):
    from knowledge.ingest import ingest_standard
    from knowledge.models import DocumentChunk

    ingest_standard(
        pdf_path=SAOSO_PDF, standard_set=standard_set, doc_key="saoso", embed=False
    )
    return DocumentChunk.objects.get(section_ref=section_ref)


def test_the_reflowed_ducks_sentence_is_accepted_by_the_audit(chat_standard_set):
    chunk = _stored_saoso_chunk(chat_standard_set, "S5.5.1")
    retrieved = _retrieved_from_stored(chunk, chat_standard_set)

    citations, problems = audit_citations(
        [{"section_ref": "S5.5.1", "quote": S5_5_1_SENTENCE}],
        [retrieved],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].quote == S5_5_1_SENTENCE


def test_the_elided_live_reply_is_still_refused(chat_standard_set):
    """The corpus fix must not become an audit relaxation (hazard §1.22)."""
    chunk = _stored_saoso_chunk(chat_standard_set, "S5.5.1")
    retrieved = _retrieved_from_stored(chunk, chat_standard_set)

    citations, problems = audit_citations(
        [{"section_ref": "S5.5.1", "quote": RECORDED_ELISION}],
        [retrieved],
        standard_set_id=chat_standard_set.pk,
    )

    assert citations == []
    assert problems == ("S5.5.1: the quote is not in the cited chunk",)


def test_a_lettered_item_in_the_passage_is_not_a_sub_ref(chat_standard_set):
    """`5.5.1` prints items a-d but emits no `sub_refs` (D14), and the model tried them.

    The live refusal was `S5.5.1: sub_ref 'a' does not exist in the chunk` — the model
    read the printed list as a clause numbering. The prompt tells it to omit `sub_ref`
    when the passage lists none; the audit refuses the citation when it does not, and
    this pins that it still does now that the quote itself is valid.
    """
    chunk = _stored_saoso_chunk(chat_standard_set, "S5.5.1")
    retrieved = _retrieved_from_stored(chunk, chat_standard_set)
    quote = "Organic feed is of inadequate quantity or quality;"

    citations, problems = audit_citations(
        [{"section_ref": "S5.5.1", "sub_ref": "a", "quote": quote}],
        [retrieved],
        standard_set_id=chat_standard_set.pk,
    )

    assert citations == []
    assert problems == ("S5.5.1: sub_ref 'a' does not exist in the chunk",)

    # The same quote without the invented sub_ref is a valid citation.
    citations, problems = audit_citations(
        [{"section_ref": "S5.5.1", "quote": quote}],
        [retrieved],
        standard_set_id=chat_standard_set.pk,
    )
    assert problems == ()


# --- D47: the citation contract the model is given --------------------------
#
# Two live turns on 2026-10-20 were refused for citation-format reasons, not corpus
# reasons: one invented a `sub_ref` from a heading, the other joined two passages with
# an ellipsis. The decision (D47, option A) is to fix the contract the model is given,
# not to loosen the audit. These tests pin the contract text and the two passage shapes
# that make it actionable.

def _prompt_for(chunk, standard_set, question="What does the passage say?"):
    from core.services._chatbot import build_prompt

    return build_prompt(question, [_retrieved_from_stored(chunk, standard_set)], [])


def test_the_system_prompt_requires_a_character_for_character_quote():
    lowered = SYSTEM_PROMPT.lower()
    assert "character-for-character" in lowered
    assert "paraphrase" in lowered
    assert "ellipsis" in lowered
    assert "`...`" in SYSTEM_PROMPT


def test_the_system_prompt_forbids_a_sub_ref_that_is_not_listed():
    lowered = SYSTEM_PROMPT.lower()
    assert "omit `sub_ref`" in lowered
    assert "numbered sub-clauses available" in lowered
    assert "heading" in lowered, (
        "the live failure was a heading returned as a sub_ref; name it explicitly"
    )


def test_a_passage_with_no_sub_refs_tells_the_model_to_omit_them(
    chat_corpus, chat_standard_set
):
    prompt = _prompt_for(chat_corpus.fee, chat_standard_set)

    assert "Numbered sub-clauses available: none" in prompt
    assert "omit `sub_ref`" in prompt


def test_a_passage_with_a_stored_sub_ref_lists_it(chat_corpus, chat_standard_set):
    prompt = _prompt_for(chat_corpus.minutes, chat_standard_set)

    assert "Numbered sub-clauses available: 4.5(2)(c)" in prompt
    assert "none" not in prompt.split("Numbered sub-clauses available:")[1].split("\n")[0]


def test_the_system_prompt_forbids_a_stitched_quote():
    """A quote that joins two non-adjacent sentences is not checkable on paper.

    Observed live on 2026-10-20 on "can i use horse manure?": the model returned
    citations with `...` between separate passages. The audit refused the whole answer,
    correctly, but the prompt had not made the one-contiguous-excerpt rule explicit
    enough. This pins that rule and the escape hatch: one citation per excerpt.
    """
    lowered = SYSTEM_PROMPT.lower()
    assert "one contiguous excerpt" in lowered
    assert "single unbroken span" in lowered
    assert "separate citation" in lowered
    assert "stitch" in lowered


def test_the_quote_schema_describes_the_same_contract():
    """The schema is the second place the model reads the contract, so it must agree."""
    from core.services._chatbot import ANSWER_SCHEMA

    quote = ANSWER_SCHEMA["properties"]["citations"]["items"]["properties"]["quote"]
    description = quote["description"].lower()
    assert "contiguous" in description
    assert "no ellipses" in description
    assert "separate citation" in description


def test_a_reviewed_table_row_is_one_citable_passage(chat_corpus, chat_standard_set):
    """A row chunk joins two printed cells; a quote may cover the row.

    `knowledge/tables.py` reconstructs Appendix 2 as one chunk per printed row, so the
    substance and its condition are adjacent even though the page prints them in two
    columns. The audit is unchanged: it checks a whitespace-normalised substring of the
    chunk, and "substance + condition" is one. This pins that contract so a future
    chunker change cannot split the pair apart again.
    """
    from knowledge.models import DocumentChunk

    row = DocumentChunk.objects.create(
        document=chat_corpus.document,
        section_ref="Appendix 2",
        heading_path="Appendix 2 — Wood, bark, sawdust",
        page=76,
        text=(
            "Wood, bark, sawdust, wood shavings, wood ash, wood charcoal\n"
            "Only if not chemically treated"
        ),
    )

    citations, problems = audit_citations(
        [
            {
                "section_ref": "Appendix 2",
                "quote": (
                    "Wood, bark, sawdust, wood shavings, wood ash, wood charcoal "
                    "Only if not chemically treated"
                ),
            }
        ],
        [_retrieved_from_stored(row, chat_standard_set)],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].section_ref == "Appendix 2"
    assert citations[0].page == 76


# --- The locator a model actually copies (2026-10-22, live on /ask/) ---------
#
# The passage header used to read `[6] Appendix 2 — SAOSO Standard for Organic
# Production and Processing v2.1, page 77`: locator and document glued together with an
# em dash. Asked "can i use borax powder?" on the live site, the model answered
# correctly, quoted the Appendix 2 trace-elements row verbatim, and set `section_ref` to
# that whole header. The audit looked for a locator it had never been given, refused, and
# the visitor was told "I cannot find a definitive answer". `why_refused.py` on the box:
#
#     citations: 1 raw, 0 audited
#     AUDIT: REFUSED
#       ! Appendix 2 — SAOSO Standard … v2.1: not present in the retrieved set
#
# Two defences, and the cause is the first one: the prompt now prints `LOCATOR:` on its
# own line, and the audit treats everything from a dash on as decoration.


def test_a_passage_prints_its_locator_on_its_own_line(chat_corpus, chat_standard_set):
    """The locator must not share a line with the document it belongs to."""
    prompt = _prompt_for(chat_corpus.fee, chat_standard_set)
    header = next(line for line in prompt.splitlines() if line.startswith("[1]"))

    assert header.startswith("[1] LOCATOR: "), header
    assert chat_corpus.fee.document.title not in header, (
        "the document title is metadata, and sharing the line invited the model to cite it"
    )
    assert f"Document: {chat_corpus.fee.document.title}" in prompt


def test_the_system_prompt_says_which_value_is_the_address():
    lowered = SYSTEM_PROMPT.lower()
    assert "locator:" in lowered
    assert "nothing else" in lowered
    assert "never the document title" in lowered


def test_a_locator_decorated_with_the_document_label_still_audits(
    chat_corpus, chat_standard_set
):
    """The live borax citation, verbatim: it must be accepted, not refused."""
    chunk = chat_corpus.fee
    decorated = f"{chunk.section_ref} — {chunk.document.title} v{chunk.document.version}"

    citations, problems = audit_citations(
        [{"section_ref": decorated, "quote": chunk.text[:60].strip()}],
        [_retrieved_from_stored(chunk, chat_standard_set)],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].section_ref == chunk.section_ref, (
        "the citation must resolve to the stored locator, not echo the decoration"
    )


def test_a_decorated_locator_that_is_ambiguous_still_refuses(chat_corpus, chat_standard_set):
    """Stripping the label widens format tolerance, never identity.

    `4.2` and `§4.2` are the same address spelled two ways, so the key unites them — and
    the audit refuses to resolve a citation through a key that two stored locators
    produce. The decoration strip must not reopen that: the live failure must be fixed
    for a bare locator without ever making an ambiguous one acceptable.
    """
    from knowledge.models import DocumentChunk

    plain = DocumentChunk.objects.create(
        document=chat_corpus.document,
        section_ref="4.2",
        heading_path="4.2 Fees",
        page=30,
        text="Fees are payable in February each year.",
    )
    signed = DocumentChunk.objects.create(
        document=chat_corpus.document,
        section_ref="§4.2",
        heading_path="§4.2 Fees (second printing)",
        page=31,
        text="Fees are payable in February each year.",
    )

    citations, problems = audit_citations(
        [
            {
                "section_ref": f"{plain.section_ref} — {plain.document.title}",
                "quote": plain.text,
            }
        ],
        [
            _retrieved_from_stored(plain, chat_standard_set),
            _retrieved_from_stored(signed, chat_standard_set),
        ],
        standard_set_id=chat_standard_set.pk,
    )

    assert citations == []
    assert any("ambiguous" in problem for problem in problems), problems


# --- The corpus artefact (D53): ten reviewed examples, audited end to end -----
#
# The BPP is ingested from its reviewed artefact (`knowledge/corpus/bpp.md`), then each
# example is put through the *real* audit. The knowledge-side test proves each sentence
# survives chunking; this proves the audit accepts a citation of it against the rows the
# artefact actually produced. Two halves of one claim, on the correct side of the
# knowledge/core boundary.

def _bpp_from_artefact(standard_set):
    from pathlib import Path

    from knowledge.ingest import ingest_standard

    artefact = (
        Path(__file__).resolve().parents[2] / "knowledge" / "corpus" / "bpp.md"
    )
    ingest_standard(
        pdf_path=BPP_PDF,
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        corpus_path=artefact,
    )
    return artefact


def test_every_reviewed_example_is_accepted_by_the_audit(chat_standard_set):
    from knowledge.models import DocumentChunk
    from knowledge.tests.test_corpus_bpp import REVIEWED_QUOTES

    _bpp_from_artefact(chat_standard_set)
    retrieved = [
        _retrieved_from_stored(chunk, chat_standard_set)
        for chunk in DocumentChunk.objects.filter(
            document__standard_set=chat_standard_set, anchor="general-principles"
        )
    ]
    assert retrieved, "the artefact produced no general-principles chunks"

    refused = {}
    for label, sentence in REVIEWED_QUOTES:
        citations, problems = audit_citations(
            [{"section_ref": "general-principles", "quote": sentence}],
            retrieved,
            standard_set_id=chat_standard_set.pk,
        )
        if problems or not citations:
            refused[label] = problems
    assert refused == {}


def test_a_paraphrase_of_a_reviewed_example_is_still_refused(chat_standard_set):
    """The corpus does not make a paraphrase verbatim — the guard on the guard."""
    from knowledge.models import DocumentChunk
    from knowledge.tests.test_corpus_bpp import REVIEWED_QUOTES

    _bpp_from_artefact(chat_standard_set)
    retrieved = [
        _retrieved_from_stored(chunk, chat_standard_set)
        for chunk in DocumentChunk.objects.filter(
            document__standard_set=chat_standard_set, anchor="general-principles"
        )
    ]
    original = dict(REVIEWED_QUOTES)["daily-pasture-access"]
    paraphrased = original.replace("All animals shall have", "Every animal must have")

    citations, problems = audit_citations(
        [{"section_ref": "general-principles", "quote": paraphrased}],
        retrieved,
        standard_set_id=chat_standard_set.pk,
    )
    assert citations == []
    assert problems == ("general-principles: the quote is not in the cited chunk",)
