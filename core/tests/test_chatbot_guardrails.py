"""Task D4 — guardrails: the endpoint is public and the model is paid.

SPEC §13 lists the guardrails, and each has a test that would fail if it were only
intended:

* **per-IP rate limit** — a fixed window, 429 when spent;
* **500-character cap** — enforced in the service, not only by the form;
* **conversation-window cap** — the model never receives an unbounded transcript;
* **answer cache** — keyed on a *normalised* question, not the raw string, so case and
  whitespace cannot be used to buy the same answer twice;
* **token accounting** — provider usage is stored per assistant message, and a cache
  hit records zero rather than double-counting yesterday's tokens.

The rate-limit tests pass `now=` so they do not sleep and do not depend on the wall
clock. The cache is overridden to `LocMemCache` by the `chat_standard_set` fixture.
"""

from __future__ import annotations

import pytest
from django.test import override_settings

from core.models import ChatMessage, ChatSession
from core.services._chatbot import (
    InvalidQuestionError,
    ModelReply,
    RateLimitedError,
    answer_question,
    check_rate_limit,
    normalise_question,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _isolated_cache(chat_cache):
    """Rate-limit keys must not leak between tests or into Redis DB 2."""
    return chat_cache


def _reply(**overrides):
    fields = {
        "answer": "Records must let a product be traced.",
        "citations": (
            {
                "section_ref": "S20.1.1",
                "quote": "Traceability is required for every batch of organic product",
            },
        ),
        "insufficient_context": False,
        "model": "fake-model",
        "prompt_tokens": 21,
        "completion_tokens": 7,
    }
    fields.update(overrides)
    return ModelReply(**fields)


def _ask(session, question, model, **kwargs):
    return answer_question(
        session.public_uuid, question, provider=model, ip_hash="", **kwargs
    )


# --- Rate limiting ----------------------------------------------------------


@override_settings(CHAT_RATE_LIMIT=3, CHAT_RATE_LIMIT_WINDOW_SECONDS=60)
def test_the_rate_limit_allows_the_budget_then_refuses():
    for _ in range(3):
        check_rate_limit("client-a", now=10)

    with pytest.raises(RateLimitedError) as raised:
        check_rate_limit("client-a", now=10)

    assert raised.value.retry_after == 50, "the wait is the rest of the window"


@override_settings(CHAT_RATE_LIMIT=3, CHAT_RATE_LIMIT_WINDOW_SECONDS=60)
def test_a_new_window_resets_the_budget():
    for _ in range(3):
        check_rate_limit("client-a", now=10)
    check_rate_limit("client-a", now=70)     # the next fixed window


@override_settings(CHAT_RATE_LIMIT=3, CHAT_RATE_LIMIT_WINDOW_SECONDS=60)
def test_each_client_has_its_own_budget():
    for _ in range(3):
        check_rate_limit("client-a", now=10)
    check_rate_limit("client-b", now=10)


def test_a_blank_ip_is_not_rate_limited():
    """A test or a management command has no IP; it must not be counted globally."""
    for _ in range(1000):
        check_rate_limit("", now=10)


@override_settings(CHAT_RATE_LIMIT=1, CHAT_RATE_LIMIT_WINDOW_SECONDS=60)
def test_answer_question_refuses_before_writing_when_rate_limited(
    chat_session, chat_corpus, fake_chat_model
):
    model = fake_chat_model(reply=_reply())

    answer_question(
        chat_session.public_uuid, "traceability", provider=model, ip_hash="ip", now=10
    )

    with pytest.raises(RateLimitedError):
        answer_question(
            chat_session.public_uuid, "traceability", provider=model, ip_hash="ip", now=10
        )

    assert ChatMessage.objects.filter(session=chat_session).count() == 2
    assert len(model.calls) == 1, "the refused question reached the model"


# --- The question cap -------------------------------------------------------


@override_settings(CHAT_MAX_QUESTION_CHARS=10)
def test_the_question_cap_is_read_at_call_time(chat_session, fake_chat_model):
    model = fake_chat_model(reply=_reply())

    with pytest.raises(InvalidQuestionError):
        _ask(chat_session, "elevenchars", model)


# --- The conversation window ------------------------------------------------


@override_settings(CHAT_HISTORY_MESSAGES=4)
def test_the_history_sent_to_the_model_is_capped(
    chat_session, chat_corpus, fake_chat_model
):
    for index in range(20):
        ChatMessage.objects.create(
            session=chat_session,
            role=(
                ChatMessage.Role.USER
                if index % 2 == 0
                else ChatMessage.Role.ASSISTANT
            ),
            content=f"prior message {index}",
        )
    model = fake_chat_model(reply=_reply())

    _ask(chat_session, "What does the standard require for traceability?", model)

    assert len(model.calls) == 1
    assert len(model.calls[0]["history"]) == 4, (
        "the model received the whole transcript, not the configured window"
    )
    assert [message.content for message in model.calls[0]["history"]] == [
        "prior message 16",
        "prior message 17",
        "prior message 18",
        "prior message 19",
    ]


# --- The answer cache -------------------------------------------------------


def test_the_cache_key_is_normalised():
    assert normalise_question("  What IS the   fee? ") == "what is the fee?"
    assert normalise_question("what is the fee?") == normalise_question(
        "WHAT  IS  THE FEE?"
    )


def test_a_repeated_question_is_answered_from_the_cache(
    chat_session, chat_corpus, fake_chat_model
):
    model = fake_chat_model(reply=_reply())

    first = _ask(
        chat_session, "What does the standard require for traceability?", model
    )
    second = _ask(
        chat_session, "what   does the standard require for traceability?", model
    )

    assert len(model.calls) == 1, "the second question paid for Gemini twice"
    assert first.cached is False
    assert second.cached is True
    assert second.text == first.text
    assert len(second.citations) == 1


def test_a_cache_hit_records_zero_tokens(chat_session, chat_corpus, fake_chat_model):
    model = fake_chat_model(reply=_reply())

    _ask(chat_session, "What does the standard require for traceability?", model)
    second = _ask(
        chat_session, "what does the standard require for traceability?", model
    )

    assistant = ChatMessage.objects.get(pk=second.message_id)
    assert second.cached is True
    assert assistant.prompt_tokens == 0
    assert assistant.completion_tokens == 0, "cached tokens were counted twice"


def test_the_cache_is_not_shared_between_standard_sets(
    chat_standard_set, chat_corpus, fake_chat_model
):
    from knowledge.models import DocumentChunk, StandardDocument, StandardSet

    other = StandardSet.objects.create(code="other-chat-corpus", label="Other")
    other_document = StandardDocument.objects.create(
        standard_set=other,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.2",
        source_file="pgs_docs/saoso-version-2.2-2026.pdf",
        sha256="b" * 64,
        section_scheme="saoso",
    )
    DocumentChunk.objects.create(
        document=other_document,
        section_ref="S20.1.1",
        heading_path="Traceability",
        page=43,
        text="Traceability is required for every batch of organic product.",
    )
    first_session = ChatSession.objects.create(standard_set=chat_standard_set)
    second_session = ChatSession.objects.create(standard_set=other)
    model = fake_chat_model(reply=_reply())

    _ask(first_session, "What does the standard require for traceability?", model)
    _ask(second_session, "What does the standard require for traceability?", model)

    assert len(model.calls) == 2, "a cached answer crossed the corpus boundary"


# --- Token accounting -------------------------------------------------------


def test_provider_usage_is_stored_on_the_assistant_message(
    chat_session, chat_corpus, fake_chat_model
):
    model = fake_chat_model(reply=_reply(prompt_tokens=321, completion_tokens=54))

    out = _ask(chat_session, "What does the standard require for traceability?", model)

    assistant = ChatMessage.objects.get(pk=out.message_id)
    assert (assistant.prompt_tokens, assistant.completion_tokens) == (321, 54)
    assert assistant.latency_ms is not None
    assert assistant.model == "fake-model"
