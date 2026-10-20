"""Task D3 — citation validity, and the corpus boundary as a filter.

SPEC §4.5 makes the scope a filter retrieval *cannot* escape, and SPEC §13 makes a
citation the thing that must be checkable. This file proves both from the chat side:

* a reference the retriever never returned is not a citation;
* a sub-reference absent from the chunk's stored offset map is not a citation;
* a quote that is not in the chunk is not a citation;
* a chunk from another `StandardSet` cannot be cited even if the model names it;
* a heading-only chunk (BPP / landscape, which print no clause numbers) is citable by
  its content-derived anchor.

The first four all force the same outcome: **the whole answer is refused**. Trimming
the bad citation and keeping the plausible ones would leave a confident answer with
one invented reference — exactly the failure this feature exists to prevent.
"""

from __future__ import annotations

import pytest

from core.models import EscalatedQuery
from core.services._chatbot import (
    REFUSAL,
    ModelReply,
    answer_question,
    audit_citations,
    build_retrieval_query,
    significant_terms,
)
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.services import RetrievedChunk, search, search_terms

pytestmark = pytest.mark.django_db


def _reply(citations, *, answer="A grounded answer.", insufficient_context=False):
    return ModelReply(
        answer=answer,
        citations=tuple(citations),
        insufficient_context=insufficient_context,
        model="fake-model",
        prompt_tokens=10,
        completion_tokens=5,
    )


def _ask(session, question, provider):
    return answer_question(
        session.public_uuid, question, provider=provider, ip_hash=""
    )


def test_the_retrieval_query_is_an_or_expression_of_significant_words():
    """The transformation that makes a natural question retrievable at all.

    `websearch_to_tsquery` ANDs words by default. The full question "What does the
    standard require for traceability?" therefore matched **nothing** in a chunk that
    says "Records must be kept…" — measured against the shipped corpus. The model
    still receives the original question; only retrieval is widened.
    """
    assert build_retrieval_query("What does the standard require for traceability?") == (
        "standard OR require OR traceability"
    )
    assert build_retrieval_query("the and of") == "the and of", (
        "an all-stopword question must still search for something"
    )


def test_function_words_are_not_search_terms():
    assert significant_terms("What does the standard say about traceability?") == [
        "standard",
        "traceability",
    ]


def test_a_natural_question_now_finds_the_chunk(chat_standard_set, chat_corpus):
    result = search_terms(
        significant_terms("What does the standard require for traceability?"),
        standard_set=chat_standard_set,
    )
    assert chat_corpus.traceability.pk in [chunk.chunk_id for chunk in result.chunks]


def test_the_rarest_term_leads_the_result(chat_standard_set, chat_corpus):
    """The common word is in three chunks; the rare one must come first.

    Without this, "standard OR traceability" ranked a landscape paragraph above the
    SAOSO clause that actually answers the question, because the paragraph happened to
    contain the word "standard" too.
    """
    document = chat_corpus.document
    for index in range(3):
        DocumentChunk.objects.create(
            document=document,
            section_ref=f"§9.{index}",
            heading_path="Standard",
            page=50 + index,
            text="The standard mentions a general principle here.",
        )

    result = search_terms(
        ["standard", "traceability"], standard_set=chat_standard_set, limit=5
    )

    first = result.chunks[0]
    assert first.chunk_id == chat_corpus.traceability.pk, (
        "the common term led the result: " + ", ".join(
            chunk.section_ref or chunk.anchor for chunk in result.chunks
        )
    )


def test_a_citation_naming_an_unretrieved_ref_is_dropped_and_forces_refusal(
    chat_session, chat_corpus, fake_chat_model
):
    model = fake_chat_model(
        reply=_reply(
            [{"section_ref": "S99.9", "quote": "This clause does not exist."}],
            answer="The standard says exactly what you want to hear.",
        )
    )

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert out.text == REFUSAL
    assert out.citations == []
    assert out.insufficient_context is True
    assert EscalatedQuery.objects.count() == 1


def test_an_invented_sub_ref_is_rejected(chat_session, chat_corpus, fake_chat_model):
    """Depth four does not exist in the source (§4.5). It must not be synthesised."""
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "§4.5(2)(c)",
                    "sub_ref": "4.5(2)(c)(4)",
                    "quote": "The committee records its decision in the minutes",
                }
            ]
        )
    )

    out = _ask(chat_session, "How does the committee record a decision in its minutes?", model)

    assert out.text == REFUSAL
    assert out.citations == []
    assert EscalatedQuery.objects.get().reason == EscalatedQuery.Reason.NO_CITATIONS


def test_a_real_sub_ref_is_accepted(chat_session, chat_corpus, fake_chat_model):
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "§4.5(2)(c)",
                    "sub_ref": "4.5(2)(c)",
                    "quote": "The committee records its decision in the minutes",
                }
            ]
        )
    )

    out = _ask(chat_session, "How does the committee record a decision in its minutes?", model)

    assert out.text == "A grounded answer."
    assert len(out.citations) == 1
    assert out.citations[0].sub_ref == "4.5(2)(c)"
    assert out.citations[0].locator == "4.5(2)(c)"


def test_a_bare_item_number_is_resolved_when_it_is_unambiguous(
    chat_session, chat_corpus, fake_chat_model
):
    """`c` means `4.5(2)(c)` when that is the only stored ref ending in `(c)`.

    The canonical form is what gets stored and shown; accepting the shorthand is a
    convenience for a model that copied the item marker from the passage, not a
    relaxation of the rule. An ambiguous shorthand is still refused.
    """
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "§4.5(2)(c)",
                    "sub_ref": "c",
                    "quote": "The committee records its decision in the minutes",
                }
            ]
        )
    )

    out = _ask(chat_session, "How does the committee record a decision in its minutes?", model)

    assert out.text == "A grounded answer."
    assert out.citations[0].sub_ref == "4.5(2)(c)", (
        "the canonical stored ref, not the model's shorthand"
    )


def test_a_quote_that_is_not_in_the_cited_chunk_is_rejected(
    chat_session, chat_corpus, fake_chat_model
):
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "S20.1.1",
                    "quote": "The standard requires a five-year plan.",
                }
            ]
        )
    )

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert out.text == REFUSAL
    assert out.citations == []


def test_whitespace_around_a_verbatim_quote_is_tolerated(
    chat_session, chat_corpus, fake_chat_model
):
    """Line breaks and runs of spaces are formatting, not paraphrase."""
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "S20.1.1",
                    "quote": "Traceability is required\nfor every batch   of organic product",
                }
            ]
        )
    )

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert out.text == "A grounded answer."
    assert len(out.citations) == 1


def test_no_answer_can_cite_a_chunk_outside_the_session_standard_set(
    chat_session, chat_corpus, fake_chat_model
):
    """A second corpus exists with a tempting, *better* match. It is still out of scope."""
    other_set = StandardSet.objects.create(code="other-corpus", label="Other")
    other_document = StandardDocument.objects.create(
        standard_set=other_set,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="EU",
        title="EU Regulation",
        version="2018",
        source_file="pgs_docs/other.pdf",
        sha256="b" * 64,
        section_scheme="saoso",
    )
    foreign = DocumentChunk.objects.create(
        document=other_document,
        section_ref="S99.9",
        heading_path="Foreign",
        page=1,
        text="Traceability is required for every batch of organic product.",
    )

    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "S99.9",
                    "quote": "Traceability is required for every batch of organic product.",
                }
            ]
        )
    )

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert out.text == REFUSAL
    assert out.citations == []
    assert foreign.pk not in [
        chunk.pk for chunk in chat_corpus.document.chunks.all()
    ]


def test_a_heading_only_chunk_is_citable_by_its_anchor(
    chat_session, chat_corpus, fake_chat_model
):
    """The BPP and the landscape print no clause numbers; D43's anchor is the locator."""
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "six-basic-elements",
                    "quote": "The six basic elements of a Participatory Guarantee System",
                }
            ]
        )
    )

    out = _ask(chat_session, "What are the six basic elements of a PGS?", model)

    assert out.text == "A grounded answer."
    assert len(out.citations) == 1
    assert out.citations[0].section_ref == "six-basic-elements"
    assert out.citations[0].chunk_id == chat_corpus.heading.pk


def test_an_unversioned_document_has_no_dangling_v(
    chat_session, chat_standard_set, fake_chat_model
):
    """The BPP and the landscape print no version; "Title v" is a display bug."""
    document = StandardDocument.objects.create(
        standard_set=chat_standard_set,
        kind=StandardDocument.Kind.LANDSCAPE,
        issuing_body="SAOSO",
        title="The South African Organic Certification Landscape",
        version="",
        source_file="pgs_docs/landscape.pdf",
        sha256="c" * 64,
        section_scheme="heading",
    )
    DocumentChunk.objects.create(
        document=document,
        section_ref=None,
        anchor="landscape-test",
        heading_path="LANDSCAPE TEST",
        page=None,
        text="The landscape test passage is here.",
    )
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "landscape-test",
                    "quote": "The landscape test passage is here.",
                }
            ]
        )
    )

    out = _ask(chat_session, "landscape test", model)

    assert out.citations[0].document == "The South African Organic Certification Landscape"


def test_duplicate_citations_are_rendered_once(chat_session, chat_corpus, fake_chat_model):
    citation = {
        "section_ref": "S20.1.1",
        "quote": "Traceability is required for every batch",
    }
    model = fake_chat_model(reply=_reply([citation, dict(citation)]))

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert len(out.citations) == 1


def test_the_audit_is_all_or_nothing(chat_session, chat_corpus, fake_chat_model):
    """One good citation beside one invented one is still a refusal."""
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "S20.1.1",
                    "quote": "Traceability is required for every batch",
                },
                {"section_ref": "S99.9", "quote": "Invented."},
            ]
        )
    )

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assert out.text == REFUSAL
    assert out.citations == []


# --- A ref the model spelled differently is still the same ref ---------------
#
# Measured 2026-10-19 against the shipped corpus, with the live provider: three
# questions ("What does the standard say about traceability?", "Do i need to know
# where horse manure comes from before I can use it?", "Does it say anything about
# input sourcing?") were refused by the audit, and the traceability one was refused
# for exactly one reason — the model returned `"sub_ref": "(12)"` for the stored
# `4.2(12)`. The item marker a reader sees in the passage is printed `(12)`; the
# brackets are typography, not a different reference.
#
# The rule the audit must keep is that nothing *uncheckable* gets through. Resolving
# a spelling is safe only when it lands on exactly one stored ref; the ambiguity test
# below is what stops "normalisation" from becoming a relaxation.


def _manure_chunk(standard_set):
    """The OPP's §4.2 with the item map the model copied `(12)` out of."""
    document = StandardDocument.objects.create(
        standard_set=standard_set,
        kind=StandardDocument.Kind.SOP,
        issuing_body="Outeniqua PGS",
        title="Outeniqua PGS Principles, Policies and Procedures",
        version="2026",
        source_file="pgs_docs/opp.pdf",
        sha256="d" * 64,
        section_scheme="opp",
    )
    text = (
        "Traceability: Retailer and market members or farmer members selling their "
        "own produce shall ensure that an invoicing/delivery note system is in place "
        "to trace horse manure back to the supplying farm."
    )
    return DocumentChunk.objects.create(
        document=document,
        section_ref="§4.2",
        heading_path="Assessment",
        page=5,
        text=text,
        sub_refs=[{"ref": "4.2(12)", "start": 0, "end": len(text)}],
    )


def test_a_parenthesised_item_number_resolves_to_the_stored_sub_ref(
    chat_session, chat_standard_set, fake_chat_model
):
    chunk = _manure_chunk(chat_standard_set)
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "§4.2",
                    "sub_ref": "(12)",
                    "quote": "to trace horse manure back to the supplying farm",
                }
            ]
        )
    )

    out = _ask(chat_session, "Where does horse manure come from?", model)

    assert out.text == "A grounded answer.", (
        "the model copied the printed item marker; that is a spelling, not a fabrication"
    )
    assert len(out.citations) == 1
    assert out.citations[0].sub_ref == "4.2(12)", "the stored ref, not the model's spelling"
    assert out.citations[0].chunk_id == chunk.pk


def test_a_section_ref_without_the_section_sign_resolves_to_the_stored_locator(
    chat_session, chat_standard_set, fake_chat_model
):
    """The OPP never prints `§` (D43), so a model may quietly drop it."""
    chunk = _manure_chunk(chat_standard_set)
    model = fake_chat_model(
        reply=_reply(
            [
                {
                    "section_ref": "4.2",
                    "quote": "to trace horse manure back to the supplying farm",
                }
            ]
        )
    )

    out = _ask(chat_session, "Where does horse manure come from?", model)

    assert out.text == "A grounded answer."
    assert out.citations[0].section_ref == "§4.2", (
        "the citation must report the locator the reader can look up, not the model's"
    )
    assert out.citations[0].chunk_id == chunk.pk


def test_a_ref_that_would_match_two_stored_locators_is_refused():
    """Normalisation must not become ambiguity. Two locators, one key: no guess."""
    chunks = tuple(
        RetrievedChunk(
            chunk_id=index,
            document_title="OPP",
            document_version="2026",
            section_ref=locator,
            heading_path="Assessment",
            page=5,
            anchor="",
            text="The clause text.",
            score=1.0,
            standard_set_id=1,
        )
        for index, locator in enumerate(("§4.2", "4.2"), start=1)
    )

    citations, problems = audit_citations(
        [{"section_ref": "4.2", "quote": "The clause text."}],
        chunks,
        standard_set_id=1,
    )

    assert citations == []
    assert problems, "an ambiguous locator is not a citation"
