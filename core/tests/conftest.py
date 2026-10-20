"""pytest fixtures for `core`.

MVP0_PLAN_V2.md §2 does not list this file, but pytest only discovers fixtures
from `conftest.py`, and the plan's A3 tests are written to call `user_factory()`
directly — so a thin adapter from the factories in `factories.py` is required.

Each fixture requests `db`, which is what makes it transactional: a test needs no
`@pytest.mark.django_db` of its own if it uses a factory.
"""

from __future__ import annotations

import pytest

from core.tests.factories import UserFactory


@pytest.fixture
def user_factory(db):
    """Callable so a test can build several users: `user_factory()`. """

    def _make(**kwargs):
        return UserFactory(**kwargs)

    return _make


@pytest.fixture
def user(user_factory):
    """A single role-less public visitor, for tests that need only one."""
    return user_factory()


# --- Chat corpus fixtures (sub-plan D) -------------------------------------
#
# A tiny, hand-built corpus rather than the real PDFs. Retrieval is exercised by
# `knowledge/tests/test_retrieval.py` against the shipped documents; these fixtures
# exist so the *chat* tests can control exactly which passages exist and what a fake
# model is allowed to cite. The question/passage pairs below are deliberately worded
# so FTS returns the intended chunk and not all four.


@pytest.fixture
def chat_cache(settings):
    """An isolated cache for the chat tests.

    The deployment's cache is Redis DB 2. A rate-limit or answer-cache test that
    incremented the real cache would leak between tests and leave a dev box with a
    spent budget. `override_settings` also makes the answer cache deterministic.
    """
    from django.core.cache import cache

    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "chat-tests",
        }
    }
    cache.clear()
    yield cache
    cache.clear()


@pytest.fixture
def chat_standard_set(db, chat_cache):
    from knowledge.models import StandardSet

    return StandardSet.objects.create(
        code="chat-corpus", label="Chat corpus", is_default=True
    )


@pytest.fixture
def chat_corpus(chat_standard_set):
    """Four chunks across the three citation shapes the corpus actually has.

    * `S20.1.1` — a SAOSO clause, the FORM's own convention (D43);
    * `§2.1` — an OPP section with no sub-ref;
    * `§4.5(2)(c)` — an OPP clause *with* a stored sub-ref offset map (D15);
    * an anchor-only chunk, because the BPP and landscape print no numbering.
    """
    from types import SimpleNamespace

    from knowledge.models import DocumentChunk, StandardDocument

    document = StandardDocument.objects.create(
        standard_set=chat_standard_set,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.1",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="a" * 64,
        section_scheme="saoso",
    )

    traceability_text = (
        "Traceability is required for every batch of organic product. Records must "
        "be kept so that a product can be followed from the farm to the buyer."
    )
    fee_text = (
        "The annual membership fee for a farmer or consumer member is R100. The "
        "group pays an annual PGS South Africa membership fee of R500."
    )
    minutes_text = (
        "The committee records its decision in the minutes of the meeting. The "
        "minuted meeting is the record of the decision."
    )
    heading_text = (
        "The six basic elements of a Participatory Guarantee System are a shared "
        "vision, participation, transparency, trust, a learning process and a "
        "horizontal structure."
    )

    traceability = DocumentChunk.objects.create(
        document=document,
        section_ref="S20.1.1",
        heading_path="Traceability",
        page=43,
        text=traceability_text,
    )
    fee = DocumentChunk.objects.create(
        document=document,
        section_ref="§2.1",
        heading_path="Membership fees",
        page=2,
        text=fee_text,
    )
    minutes = DocumentChunk.objects.create(
        document=document,
        section_ref="§4.5(2)(c)",
        heading_path="Committee decisions",
        page=9,
        text=minutes_text,
        sub_refs=[{"ref": "4.5(2)(c)", "start": 0, "end": len(minutes_text)}],
    )
    heading = DocumentChunk.objects.create(
        document=document,
        section_ref=None,
        anchor="six-basic-elements",
        heading_path="SIX BASIC ELEMENTS",
        page=None,
        text=heading_text,
    )

    return SimpleNamespace(
        document=document,
        traceability=traceability,
        fee=fee,
        minutes=minutes,
        heading=heading,
    )


@pytest.fixture
def chat_session(chat_standard_set):
    from core.models import ChatSession

    return ChatSession.objects.create(standard_set=chat_standard_set)


class FakeChatModel:
    """A generation provider that returns a fixed reply and records what it was given."""

    name = "fake-model"

    def __init__(self, reply=None, error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def answer(self, *, question, chunks, history):
        self.calls.append(
            {"question": question, "chunks": tuple(chunks), "history": tuple(history)}
        )
        if self.error is not None:
            raise self.error
        return self.reply


@pytest.fixture
def fake_chat_model():
    return FakeChatModel
