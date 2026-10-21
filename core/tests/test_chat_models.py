"""Task D1 — the chat models.

SPEC §4.6 fixes three things this file protects:

1. **An anonymous visitor may chat.** `ChatSession.user` is nullable, so the public
   surface works without an account — that is the whole point of a public chatbot.
2. **A visitor graduates without losing history.** Attaching a `User` to an existing
   session is allowed, and leaves the session (and its messages) in place.
3. **A session is pinned to the corpus it started against.** `standard_set` is a
   foreign key, not a lookup at answer time, so a corpus swap cannot silently change
   what an in-progress conversation is allowed to cite.

The public identifier is a UUID, never the sequential primary key: `§I` forbids a
sequential id on any public surface, and a chat session id is a public URL/JS value.
"""

from __future__ import annotations

import uuid

import pytest

from core.models import ChatMessage, ChatSession, EscalatedQuery
from knowledge.models import DocumentChunk, StandardDocument, StandardSet

pytestmark = pytest.mark.django_db


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(code="chat-models", label="Chat models", is_default=True)


@pytest.fixture
def document(standard_set):
    return StandardDocument.objects.create(
        standard_set=standard_set,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.1",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="a" * 64,
        section_scheme="saoso",
    )


@pytest.fixture
def chunk(document):
    return DocumentChunk.objects.create(
        document=document,
        section_ref="S20.1.1",
        heading_path="Traceability",
        page=43,
        text="Traceability is required for every batch.",
    )


def test_an_anonymous_session_needs_no_user(standard_set):
    session = ChatSession.objects.create(standard_set=standard_set)

    assert session.user is None
    assert session.public_uuid is not None
    assert session.ip_hash == "", "an unknown IP is blank, never a fake hash"


def test_a_visitor_can_be_attached_later_without_losing_the_session(standard_set, user_factory):
    from core.services._chatbot import attach_user

    user = user_factory()
    session = ChatSession.objects.create(standard_set=standard_set)
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content="Hello")

    attached = attach_user(session.public_uuid, user)

    assert attached.pk == session.pk, "attaching a user must not start a new conversation"
    assert attached.user == user
    assert attached.messages.count() == 1, "the anonymous history is kept"


def test_public_uuid_is_a_uuid_and_not_the_sequential_id(standard_set):
    first = ChatSession.objects.create(standard_set=standard_set)
    second = ChatSession.objects.create(standard_set=standard_set)

    assert isinstance(first.public_uuid, uuid.UUID)
    assert first.public_uuid != second.public_uuid
    assert first.public_uuid.int != first.pk, "the public identifier must not be the row id"


def test_a_session_is_pinned_to_the_corpus_it_started_against(standard_set):
    other = StandardSet.objects.create(code="other-corpus", label="Other")

    session = ChatSession.objects.create(standard_set=standard_set)

    assert session.standard_set_id == standard_set.pk
    assert session.standard_set_id != other.pk
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        # PROTECT, not CASCADE: deleting a corpus that a conversation was started
        # against would leave its citations pointing at nothing.
        standard_set.delete()


def test_a_message_can_carry_the_chunks_the_answer_was_grounded_on(standard_set, chunk):
    session = ChatSession.objects.create(standard_set=standard_set)

    message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content="Traceability is required.",
        latency_ms=812,
        model="fake-model",
        prompt_tokens=120,
        completion_tokens=24,
    )
    message.retrieved_chunks.add(chunk)

    assert message.retrieved_chunks.count() == 1
    assert message.retrieved_chunks.get() == chunk
    assert message.latency_ms == 812
    assert message.prompt_tokens == 120
    assert message.completion_tokens == 24


def test_the_message_role_is_a_closed_pair(standard_set):
    session = ChatSession.objects.create(standard_set=standard_set)

    assert set(ChatMessage.Role.values) == {"USER", "ASSISTANT"}


def test_escalation_reasons_are_the_four_the_spec_names(standard_set):
    """Four since D54. The fourth exists so the record can tell three findings apart.

    `NO_CITATIONS` = the model cited nothing; `INSUFFICIENT_CONTEXT` = the corpus could not
    ground the question; `CITATION_AUDIT` = it cited something the audit could not verify
    (a paraphrase, an absent section, an invented `sub_ref`). The first and third used to
    share a reason, which made a model-contract violation read like a thin corpus.
    """
    assert set(EscalatedQuery.Reason.values) == {
        "INSUFFICIENT_CONTEXT",
        "NO_CITATIONS",
        "CITATION_AUDIT",
        "USER_REQUESTED",
    }


def test_an_escalation_starts_open_and_records_the_question(standard_set):
    session = ChatSession.objects.create(standard_set=standard_set)
    message = ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.USER, content="Which fertiliser should I buy?"
    )

    escalation = EscalatedQuery.objects.create(
        message=message,
        question="Which fertiliser should I buy?",
        reason=EscalatedQuery.Reason.INSUFFICIENT_CONTEXT,
    )

    assert escalation.status == EscalatedQuery.Status.OPEN
    assert escalation.answered_at is None
    assert escalation.answered_by is None
