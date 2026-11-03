"""Task D2 — `answer_question()`: the refusal, the grounded answer, validation.

The product argument is the refusal. Anyone can wire a model to a prompt; the claim
this feature makes is that the assistant **declines rather than guesses**, and that a
confident-sounding answer with no citation is refused even when the model set
`insufficient_context: false`.

Two strings matter and both are asserted exactly:

* `REFUSAL` — D17's wide-corpus wording. The old SAOSO-only string is wrong because
  the OPP answers questions the standard does not (fees, joining, procedure).
* the refusal is **never** a fabricated answer when Gemini is down. `UpstreamModelError`
  propagates; the view shows an honest unavailable notice.

The corpus side stays here too: D46 and D52 are the two live refusals whose cause was the
corpus rather than the model, and they pin that a *real* ingest produces a sentence the audit
accepts while the model's recorded paraphrase is still refused. `scripts/fast.sh --critical`
names this file for exactly that property, so the guards that prove it stay in it.

What the prompt tells the model is `test_chatbot_prompt.py`; the reviewed corpus artefact is
`test_chatbot_artefact.py`; what a turn stores is `test_chatbot_turns.py`.
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
    chat_retrieval_limit,
    default_retrieval,
)
from core.tests.chat_helpers import (
    ask as _ask,
    grounded_reply as _grounded_reply,
    retrieved_from_stored as _retrieved_from_stored,
)

PDF_DIR = Path(__file__).resolve().parents[2] / "pgs_docs"


@pytest.fixture(autouse=True)
def committed_extraction(monkeypatch):
    """Ingest from the committed pages, not through a PDF reader (D57).

    Two tests below build a real stored chunk by ingesting `pgs_docs/`. The gate runs with
    `PDFTOTEXT_BIN` pointed at a path that cannot exist, so the bytes come from
    `knowledge/tests/fixtures/pages/` — the same bytes, committed as evidence.
    """
    from knowledge.tests.page_fixtures import stub_ingest_extraction

    stub_ingest_extraction(monkeypatch)


pytestmark = pytest.mark.django_db


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
    from core.services import _chat_guard, _chatbot

    seen: dict[str, object] = {}

    def spy(terms, *, standard_set, limit, question, context_query=""):
        seen["terms"] = terms
        seen["limit"] = limit
        seen["context_query"] = context_query
        return _chatbot.RetrievalResult(
            query=question,
            standard_set_id=standard_set.pk,
            lexical_only=True,
        )

    # Patched on the module `default_retrieval` actually reads it from: since the
    # context-cut split it lives in `_chat_guard`, and patching `_chatbot` would install
    # the spy where nothing looks -- a test that passes for the wrong reason.
    monkeypatch.setattr(_chat_guard, "search_terms", spy)
    settings.CHAT_RETRIEVAL_LIMIT = 3

    default_retrieval("how do I sign up?", chat_standard_set)

    assert seen["limit"] == 3
    assert seen["terms"] == ["sign"]
    # Stage 1: the arm is passed through and is empty for a first question, so this
    # path still retrieves what it retrieved before.
    assert seen["context_query"] == ""


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
    """No corpus chunk is retrieved, so the model is not asked and the reason says why.

    This case used to be recorded as `INSUFFICIENT_CONTEXT`, the same value the model's own
    `insufficient_context` flag produces. They are different findings — "nothing matched
    the question" is a retrieval/key defect, "the passages did not govern it" is a
    coverage gap — so the empty-retrieval branch records `NO_RETRIEVAL` and the reason
    below is asserted rather than left to the log (`CHAT_TRUTHFULNESS_PRD.md` §4.1).
    """
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
    assert model.calls == [], "the model was asked to answer from an empty result set"
    assert EscalatedQuery.objects.count() == 1
    assert EscalatedQuery.objects.get().reason == EscalatedQuery.Reason.NO_RETRIEVAL


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


def test_a_refusal_records_its_reason_on_the_turn(chat_session, chat_corpus, fake_chat_model):
    """The turn carries the reason, so the thread can explain itself without a join.

    The template reads `refusal_reason`, not the text: comparing the stored sentence was
    how a copy change could silently remove the contact link and the warm styling.
    """
    from core.services._chatbot import REFUSAL, ModelReply

    model = fake_chat_model(
        reply=ModelReply(
            answer="An answer the audit will refuse.",
            citations=(
                {"section_ref": "S99.9", "quote": "a sentence that is not in the chunk"},
            ),
            model="fake-model",
        )
    )

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert out.text == REFUSAL
    assistant = ChatMessage.objects.filter(role=ChatMessage.Role.ASSISTANT).latest("id")
    assert assistant.refusal_reason == "CITATION_AUDIT"
    assert assistant.content == REFUSAL, "the fixed sentence is stored, unchanged"
    assert assistant.refusal_note, "the turn can explain itself"


def test_a_grounded_answer_stores_no_refusal_reason(chat_session, chat_corpus, fake_chat_model):
    model = fake_chat_model(reply=_grounded_reply())

    _ask(chat_session, "What does the standard require for traceability?", model)

    assistant = ChatMessage.objects.filter(role=ChatMessage.Role.ASSISTANT).latest("id")
    assert assistant.refusal_reason == ""
    assert assistant.refusal_note == ""


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


