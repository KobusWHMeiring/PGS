"""Stage 1 of the follow-up decision: carry the previous question into retrieval.

The problem this pins, in one sentence: a follow-up such as *"what if I compost it
first?"* is searched as `compost`, while the model is handed the earlier conversation
and therefore cites the clause from it — which the all-or-nothing audit refuses because
that clause was never retrieved this turn.

Stage 1 fixes it without a model call:

1. `looks_like_follow_up()` decides, deterministically, whether the new question is
   continuing the last one. It **fails closed**: anything it cannot recognise is a new
   question, which is exactly today's behaviour, so a wrong answer costs nothing.
2. When it is a follow-up, `default_retrieval()` also searches `parent + question` and
   fuses those passages in, displacing the weakest match rather than splitting the
   budget.
3. The answer cache is keyed on the conversation too. It was keyed on the question
   alone, which was already wrong (the prompt has carried history since D2) and becomes
   a cross-conversation leak the moment a follow-up's answer depends on its parent.

No model is called anywhere in this module's subject under test.
"""

from __future__ import annotations

import pytest

from core.models import ChatMessage, ChatSession
from core.services._chatbot import (
    PROMPT_VERSION,
    ModelReply,
    _cache_key,
    _history_digest,
    answer_question,
    build_prompt,
    looks_like_follow_up,
)
from knowledge.services import RetrievalResult, RetrievedChunk

pytestmark = pytest.mark.django_db


# --- The detector -----------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "and for goats?",
        "what if I compost it first?",
        "what about the fees?",
        "is that allowed for poultry too?",
        "does that apply to my neighbour as well?",
        "why?",
        "then what about straw?",
    ],
)
def test_a_continuation_is_recognised(question):
    assert looks_like_follow_up(question, "Can I use cardboard from my neighbour?")


@pytest.mark.parametrize(
    "question",
    [
        "What is the yearly cost to get certified, including the farm visit?",
        "Can I use Korean Natural Farming preparations on my farm?",
        "How do I make lactic acid bacteria for my compost?",
        "Do I need EU organic certification to export to Germany?",
    ],
)
def test_a_standalone_question_is_not_a_follow_up(question):
    """Fails closed: a question that makes sense alone gets today's behaviour."""
    assert not looks_like_follow_up(question, "Can I use cardboard from my neighbour?")


def test_asking_the_same_question_again_is_not_a_follow_up():
    """It shares every word, so the shared-term rule would say yes. It must not.

    A repeat is the case the cache exists for: same question, same answer, no model call.
    """
    question = "What does the standard require for traceability?"
    assert not looks_like_follow_up(question, question)
    # Case and whitespace are how a *same* question differs, so they are normalised
    # away before the comparison.
    assert not looks_like_follow_up("  WHAT does the   STANDARD require for traceability? ", question)


def test_there_is_no_follow_up_without_a_previous_question():
    assert not looks_like_follow_up("and for goats?", "")


def test_a_short_question_sharing_a_term_is_a_follow_up():
    """The third signal: short and overlapping. 'Does manure apply to goats too?'"""
    assert looks_like_follow_up(
        "does manure apply to goats too?",
        "Do I need to know where my horse manure comes from?",
    )


def test_a_long_question_that_shares_a_term_is_still_standalone():
    """Length is part of the test: a long question has its own subject."""
    assert not looks_like_follow_up(
        "I want to know whether the manure rule for horses also covers goats, cattle "
        "and poultry on a mixed farm with several production units",
        "Do I need to know where my horse manure comes from?",
    )


# --- The plumbing -----------------------------------------------------------


def _retrieved(chunk) -> RetrievedChunk:
    """The fixture corpus row as retrieval would hand it to the answer engine."""
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


class RecordingRetrieval:
    """A retrieval stand-in that records how it was called.

    The contract carries one keyword: `context_query`, the previous question to fuse in.
    Recording the call is the point — this is the seam where a follow-up is either
    carried into retrieval or silently dropped.
    """

    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def __call__(self, question, standard_set, *, context_query=""):
        self.calls.append({"question": question, "context_query": context_query})
        return RetrievalResult(
            query=question,
            standard_set_id=standard_set.pk,
            chunks=tuple(self.chunks),
        )


def _grounded():
    fields = {
        "answer": "Records must let a product be traced from farm to buyer.",
        "citations": (
            {"section_ref": "S20.1.1", "quote": "Traceability is required for every batch of organic product"},
        ),
        "model": "fake-model",
        "prompt_tokens": 10,
        "completion_tokens": 5,
    }
    return ModelReply(**fields)


def _session_with_history(standard_set, question, *, citations=None):
    session = ChatSession.objects.create(standard_set=standard_set)
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content=question)
    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content="An earlier answer.",
        citations=citations or {},
    )
    return session


def test_a_follow_up_carries_the_previous_question_into_retrieval(
    chat_standard_set, chat_corpus, fake_chat_model
):
    session = _session_with_history(
        chat_standard_set, "Can I use cardboard from my neighbour?"
    )
    retrieval = RecordingRetrieval([_retrieved(chat_corpus.traceability)])

    answer_question(
        session.public_uuid,
        "what if I compost it first?",
        provider=fake_chat_model(reply=_grounded()),
        retrieval=retrieval,
        ip_hash="",
    )

    assert retrieval.calls[0]["question"] == "what if I compost it first?"
    assert "cardboard" in retrieval.calls[0]["context_query"], (
        "the previous question was not carried into retrieval, so the follow-up is "
        "searched as the bare fragment"
    )


def test_a_standalone_question_does_not_carry_the_previous_question(
    chat_standard_set, chat_corpus, fake_chat_model
):
    session = _session_with_history(
        chat_standard_set, "Can I use cardboard from my neighbour?"
    )
    retrieval = RecordingRetrieval([_retrieved(chat_corpus.traceability)])

    answer_question(
        session.public_uuid,
        "What is the yearly cost to get certified, including the farm visit?",
        provider=fake_chat_model(reply=_grounded()),
        retrieval=retrieval,
        ip_hash="",
    )

    assert retrieval.calls[0]["context_query"] == ""


def test_a_follow_up_can_still_cite_the_clause_it_inherited(
    chat_standard_set, chat_corpus, fake_chat_model
):
    """The audit's rule is "only what was retrieved this turn".

    A follow-up that quotes the clause the visitor just read therefore needs that clause
    in *this* turn's set. The parent's audited citation is the cheapest possible source
    of it: one passage, known to be relevant, already scoped to the corpus.
    """
    session = _session_with_history(
        chat_standard_set,
        "Can I use cardboard from my neighbour?",
        citations={
            "accepted": [
                {"section_ref": "S20.1.1", "chunk_id": chat_corpus.traceability.pk},
            ]
        },
    )
    model = fake_chat_model(reply=_grounded())

    answer_question(
        session.public_uuid,
        "what if I compost it first?",
        provider=model,
        retrieval=RecordingRetrieval([_retrieved(chat_corpus.fee)]),
        ip_hash="",
    )

    served = [chunk.chunk_id for chunk in model.calls[0]["chunks"]]
    assert chat_corpus.traceability.pk in served, (
        "the inherited clause was dropped, so a faithful follow-up citation would be refused"
    )


def test_a_standalone_question_does_not_inherit_the_previous_clause(
    chat_standard_set, chat_corpus, fake_chat_model
):
    session = _session_with_history(
        chat_standard_set,
        "Can I use cardboard from my neighbour?",
        citations={
            "accepted": [
                {"section_ref": "S20.1.1", "chunk_id": chat_corpus.traceability.pk},
            ]
        },
    )
    model = fake_chat_model(reply=_grounded())

    answer_question(
        session.public_uuid,
        "What is the yearly cost to get certified, including the farm visit?",
        provider=model,
        retrieval=RecordingRetrieval([_retrieved(chat_corpus.fee)]),
        ip_hash="",
    )

    served = [chunk.chunk_id for chunk in model.calls[0]["chunks"]]
    assert chat_corpus.traceability.pk not in served, (
        "a new question must not have the previous answer's evidence pushed into it"
    )


def test_the_first_question_in_a_conversation_carries_nothing(
    chat_session, chat_corpus, fake_chat_model
):
    retrieval = RecordingRetrieval([_retrieved(chat_corpus.traceability)])

    answer_question(
        chat_session.public_uuid,
        "what if I compost it first?",
        provider=fake_chat_model(reply=_grounded()),
        retrieval=retrieval,
        ip_hash="",
    )

    assert retrieval.calls[0]["context_query"] == ""


# --- The cache --------------------------------------------------------------


def test_two_conversations_do_not_share_a_follow_up_answer(
    chat_standard_set, chat_corpus, fake_chat_model, chat_cache
):
    """The defect: `sha256(question)` alone, with a conversation-dependent prompt.

    Two visitors typing the same fragment after different questions must not share one
    cached answer. Before stage 1 the second visitor received the first one's reply.
    """
    first = _session_with_history(chat_standard_set, "Can I use cardboard from my neighbour?")
    second = _session_with_history(chat_standard_set, "Can I use straw mulch?")
    model = fake_chat_model(reply=_grounded())

    for session in (first, second):
        answer_question(
            session.public_uuid,
            "what if I compost it first?",
            provider=model,
            retrieval=RecordingRetrieval([_retrieved(chat_corpus.traceability)]),
            ip_hash="",
        )

    assert len(model.calls) == 2, "the second conversation was served the first one's answer"


def test_the_same_conversation_still_hits_the_cache(
    chat_standard_set, chat_corpus, fake_chat_model, chat_cache
):
    """Correctness must not cost every cache hit.

    Two sessions with identical history and the same question are the same request, so
    the second is served from the cache and the model is called once.
    """
    parent = "Can I use cardboard from my neighbour?"
    first = _session_with_history(chat_standard_set, parent)
    second = _session_with_history(chat_standard_set, parent)
    model = fake_chat_model(reply=_grounded())

    for session in (first, second):
        answer_question(
            session.public_uuid,
            "what if I compost it first?",
            provider=model,
            retrieval=RecordingRetrieval([_retrieved(chat_corpus.traceability)]),
            ip_hash="",
        )

    assert len(model.calls) == 1


def test_the_history_digest_is_empty_without_history(chat_standard_set):
    assert _history_digest([]) == ""


def test_the_cache_key_separates_conversations(chat_standard_set):
    assert _cache_key("what if I compost it first?", chat_standard_set, "fp", "aaa") != (
        _cache_key("what if I compost it first?", chat_standard_set, "fp", "bbb")
    )


# --- The prompt -------------------------------------------------------------


def test_the_prompt_learns_it_is_answering_a_conversation(chat_corpus):
    """The instruction that makes the fused passages usable.

    Without it the model treats the earlier turns as the answer material; with it, the
    earlier turns only resolve the reference, and the supplied passages carry the claim.
    """
    chunks = [_retrieved(chat_corpus.traceability)]
    history = [
        ChatMessage(role=ChatMessage.Role.USER, content="Can I use cardboard?"),
        ChatMessage(role=ChatMessage.Role.ASSISTANT, content="It is a by-product with a condition."),
    ]

    prompt = build_prompt("what if I compost it first?", chunks, history)

    assert "Conversation so far" in prompt
    assert "follow-up" in prompt.lower()
    assert "supplied below" in prompt


def test_a_first_question_prompt_gains_nothing(chat_corpus):
    chunks = [_retrieved(chat_corpus.traceability)]
    prompt = build_prompt("What does the standard require for traceability?", chunks, [])
    assert "Conversation so far" not in prompt
    assert "follow-up" not in prompt.lower()


def test_the_prompt_version_moved():
    """A prompt change that is not versioned is a cache entry nobody can interpret."""
    assert PROMPT_VERSION == "d50-1"
