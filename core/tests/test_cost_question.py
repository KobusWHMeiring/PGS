"""G10's first fix: a cost question gets the components, and what cannot be totalled.

The defect this pins was reported by the product owner, reading `/ask/`: *"when I ask
what the yearly cost is it only mentions the R100"*. Measured 2026-11-01 through
`scripts/probe_chat.py` on the 394-chunk dev corpus:

| Question | Answer | Citations |
|---|---|---|
| *"what does it cost to join"* | complete — §2.1, §2.3, §2.4 | 5 audited, grounded |
| *"what is the yearly cost of membership"* | **membership only** — R100 + R500 | 2 audited, grounded |
| *"what is the yearly cost"* | complete (one run of five refused — G10's second finding) | 8 audited, grounded |

Retrieval is not the cause: on the membership phrasing, `§2.3`, `§2.2`, `§2.4` and
`§2.5` are all in the eight passages supplied, and the model cites the one section the
question names. That is faithful to the question and still fails the reader — the R100
is presented as the price of membership when it is one component of a year.

Three things are pinned here, and none of them needs a model call:

1. `looks_like_cost_question()` recognises the four measured phrasings and does not
   claim ordinary questions.
2. `build_prompt()` carries the answer rule **only** for a cost question, and the rule
   names no section reference and no amount — a rule that names them would invite the
   model to cite a passage retrieval did not supply, which the audit refuses
   (`CHAT_TRUTHFULNESS_PRD.md` F3 is the same hazard in a different shape).
3. `cost_question_warnings()` records an answer that states no limit, as an advisory
   review note. It never refuses: G10's second finding is that a refusal and "the
   corpus cannot answer" are indistinguishable to the visitor.
"""

from __future__ import annotations

import pytest

from core.models import ChatMessage
from core.services._chatbot import (
    COST_QUESTION_RULE,
    PROMPT_VERSION,
    ModelReply,
    answer_question,
    build_prompt,
    cost_question_warnings,
    looks_like_cost_question,
)
from knowledge.services import RetrievalResult, RetrievedChunk

pytestmark = pytest.mark.django_db


# --- The detector -----------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        # G10's own four measured phrasings.
        "What is the yearly cost to get certified, including the farm visit?",
        "what does it cost to join",
        "what is the yearly cost of membership",
        "what is the yearly cost",
        # The shapes a visitor actually types.
        "How much do I pay for a farm visit?",
        "What are the fees?",
        "What is the price of the seal licence?",
        "Is certification expensive?",
        "How much rand is membership?",
        "Do I have to pay annually?",
    ],
)
def test_a_cost_question_is_recognised(question):
    assert looks_like_cost_question(question)


@pytest.mark.parametrize(
    "question",
    [
        "Can I use cardboard from my neighbour?",
        "What does the standard say about the minimum rest period for laying hens?",
        "Do i need to know where my horse manure comes from?",
        "How do I sign up?",
        "If my ducks aren't fed organic food and I make compost from their bedding, "
        "will I still pass?",
        "What is required for traceability?",
        "What does the OPP say about terminating membership?",
    ],
)
def test_an_ordinary_question_is_not_a_cost_question(question):
    assert not looks_like_cost_question(question)


def test_the_empty_question_is_not_a_cost_question():
    assert not looks_like_cost_question("")


# --- The prompt rule --------------------------------------------------------


def test_a_cost_question_prompt_carries_the_answer_rule(chat_corpus):
    chunks = [_retrieved(chat_corpus.fee)]
    prompt = build_prompt("what is the yearly cost of membership", chunks, [])
    assert COST_QUESTION_RULE in prompt


def test_an_ordinary_question_prompt_gains_nothing(chat_corpus):
    chunks = [_retrieved(chat_corpus.traceability)]
    prompt = build_prompt("What is required for traceability?", chunks, [])
    assert COST_QUESTION_RULE not in prompt
    assert "cost" not in prompt.split("Passages:")[0].lower()


def test_the_rule_names_no_section_reference(chat_corpus):
    """A rule that names §2.3 invites a citation retrieval may not have supplied.

    The audit is all-or-nothing and refuses the whole answer for one citation that was
    not retrieved this turn, so a prompt that volunteers an address is a refusal
    generator — the F3 lesson (`CHAT_TRUTHFULNESS_PRD.md`), and G10's own second finding.
    """
    assert "§" not in COST_QUESTION_RULE
    assert "S2.3" not in COST_QUESTION_RULE


def test_the_rule_names_no_amount(chat_corpus):
    """The amounts belong to the passages. A rule that prints one is the model's memory."""
    assert not any(character.isdigit() for character in COST_QUESTION_RULE)


def test_the_rule_forbids_presenting_one_component_as_the_whole():
    lowered = COST_QUESTION_RULE.lower()
    assert "whole" in lowered or "total" in lowered
    assert "leave" in lowered or "not included" in lowered or "separate" in lowered


def test_the_rule_separates_what_the_group_pays_from_what_a_member_pays():
    """The owner's correction, 2026-11-01: the group's national fee is not a member's charge.

    §2.1: *"PGS South Africa membership fee: the group will pay the annual membership fee to
    SAOSO. The funds for this national membership will be secured from our membership fees."*
    The first version of this rule left that R500 inside "the yearly cost of membership", so a
    reader could not tell whose money it was. It is a rule about *shape*, so it names no
    document and no amount — the passages carry those.
    """
    lowered = COST_QUESTION_RULE.lower()
    assert "member pays" in lowered or "what a member pays" in lowered
    assert "group pays" in lowered
    assert "obligation" in lowered or "on its members' behalf" in lowered


def test_the_rule_says_the_assessment_fee_is_the_unavoidable_part():
    """A farm cannot be certified without a visit — so the R100 is not the cost of a year."""
    lowered = COST_QUESTION_RULE.lower()
    assert "must be assessed" in lowered
    assert "entering or renewing certification" in lowered
    assert "membership fee alone" in lowered


def test_the_rule_allows_a_floor_and_no_other_arithmetic():
    """D79: the only sum permitted is membership + one named band, called a floor.

    The public page publishes exactly this shape (`FIRST_YEAR_FROM_CENTS`, "a floor, not a
    total"), and the first version of the rule forbade every total, so the site and the
    assistant disagreed in the one place the owner had asked them to agree.
    """
    lowered = COST_QUESTION_RULE.lower()
    assert "one floor and no other total" in lowered
    assert "membership fee plus one band" in lowered
    assert "called a floor" in lowered


def test_the_prompt_version_moved_with_the_rule():
    """`d79-2` is the version that carries the cost rule and the table rule (pinned in
    `test_follow_up` too)."""
    assert PROMPT_VERSION == "d79-2"


# --- The advisory note ------------------------------------------------------


def test_an_answer_that_states_no_limit_is_recorded():
    """The measured membership answer: two fees, one component, no exclusion."""
    answer = (
        "The annual Farmer & consumer Membership fee for Outeniqua Natural and "
        "Organic PGS group members is R100. Additionally, the group pays an annual "
        "PGS South Africa membership fee of R500 to SAOSO."
    )
    notes = cost_question_warnings("what is the yearly cost of membership", answer)
    assert notes, "an answer that presents one component as the cost was not recorded"
    assert "limit" in notes[0] or "leave" in notes[0]


def test_an_answer_that_says_what_is_separate_is_not_recorded():
    answer = (
        "Membership is R100 a year. The assessment fee is set on a sliding scale and "
        "is charged separately, transport is at the AA rate, and the R500 seal licence "
        "only applies once the farm is certified."
    )
    assert cost_question_warnings("what is the yearly cost", answer) == ()


def test_an_ordinary_question_is_never_recorded():
    answer = "Records must let a product be traced from farm to buyer."
    assert cost_question_warnings("What is required for traceability?", answer) == ()


def test_the_note_is_never_a_refusal(
    chat_standard_set, chat_corpus, chat_session, fake_chat_model
):
    """An advisory note goes to the record; the visitor still gets the answer."""
    answer = "The annual membership fee is R100."
    retrieval = _retrieval([_retrieved(chat_corpus.fee)])
    reply = ModelReply(
        answer=answer,
        citations=(
            {
                "section_ref": "§2.1",
                "quote": "The annual membership fee for a farmer or consumer member is R100.",
            },
        ),
        insufficient_context=False,
        model="fake-model",
        prompt_tokens=10,
        completion_tokens=10,
    )

    result = answer_question(
        chat_session.public_uuid,
        "what is the yearly cost of membership",
        provider=fake_chat_model(reply=reply),
        retrieval=retrieval,
        ip_hash="",
    )

    assert result.text == answer
    assert result.insufficient_context is False
    message = ChatMessage.objects.get(pk=result.message_id)
    assert message.review_notes, "the note was not stored on the turn"
    assert any("cost" in note.lower() for note in message.review_notes)


def test_a_grounded_cost_answer_gains_no_note(
    chat_standard_set, chat_corpus, chat_session, fake_chat_model
):
    answer = (
        "The annual membership fee is R100. The assessment fee is set on a sliding "
        "scale and is charged separately."
    )
    retrieval = _retrieval([_retrieved(chat_corpus.fee)])
    reply = ModelReply(
        answer=answer,
        citations=(
            {
                "section_ref": "§2.1",
                "quote": "The annual membership fee for a farmer or consumer member is R100.",
            },
        ),
        insufficient_context=False,
        model="fake-model",
        prompt_tokens=10,
        completion_tokens=10,
    )

    result = answer_question(
        chat_session.public_uuid,
        "what is the yearly cost",
        provider=fake_chat_model(reply=reply),
        retrieval=retrieval,
        ip_hash="",
    )

    message = ChatMessage.objects.get(pk=result.message_id)
    assert message.review_notes == []


# --- helpers ----------------------------------------------------------------


def _retrieved(chunk) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk.pk,
        document_title="SAOSO Standard",
        document_version="2.1",
        section_ref=chunk.section_ref,
        heading_path=chunk.heading_path,
        page=chunk.page,
        anchor=chunk.anchor or "",
        text=chunk.text,
        score=0.5,
        standard_set_id=chunk.document.standard_set_id,
    )


def _retrieval(chunks):
    def retrieve(question, standard_set, *, context_query=""):
        return RetrievalResult(
            query=question,
            standard_set_id=standard_set.pk,
            chunks=list(chunks),
            lexical_only=True,
        )

    return retrieve
