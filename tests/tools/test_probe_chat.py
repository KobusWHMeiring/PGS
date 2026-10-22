"""The probe must measure the product's retrieval path, not a convenient one.

G8 was found by a reviewer and **hidden by this instrument**: `probe_chat.py` retrieved
with `limit=8` while `answer_question()` retrieves with `settings.CHAT_RETRIEVAL_LIMIT`
(5), so the probe printed a grounded answer for a question `/ask/` refuses. A measuring
tool that measures a different path is the "passes for the wrong reason" pattern
(`testing_hazards.md` §2.7).

Two guarantees, both mutation-checked:

* the default limit is read from **settings when the parser is built**, so a hardcoded
  number cannot come back;
* retrieval goes through `core.services._chatbot.default_retrieval` — the same function
  the view path uses — so there is one retrieval path, not two that agree by accident.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.services import _chatbot
from scripts import probe_chat


def test_the_default_limit_is_the_chat_limit(settings):
    """Mutation: `default=8` in the parser makes this red."""
    settings.CHAT_RETRIEVAL_LIMIT = 3
    args = probe_chat.build_parser().parse_args(["a question"])
    assert args.limit == 3


def test_an_explicit_limit_still_wins():
    args = probe_chat.build_parser().parse_args(["--limit", "12", "a question"])
    assert args.limit == 12


def test_the_probe_has_no_retrieval_call_of_its_own():
    """One retrieval path. Mutation: calling `search_terms(...)` here makes this red."""
    source = Path(probe_chat.__file__).read_text(encoding="utf-8")
    assert "search_terms(" not in source


def test_the_probe_passes_its_limit_to_the_product_helper(monkeypatch, settings):
    """The limit the probe resolves is the limit the shared helper is called with."""
    settings.CHAT_RETRIEVAL_LIMIT = 4
    seen: dict[str, object] = {}

    def spy(question, standard_set, *, limit=None):
        seen["question"] = question
        seen["limit"] = limit
        return SimpleNamespace(chunks=(), lexical_only=False, warnings=())

    # The three fakes exist because the probe prints terms and document frequencies
    # before it retrieves; the corpus is not this test's subject, the limit is.
    monkeypatch.setattr(_chatbot, "default_retrieval", spy)
    monkeypatch.setattr(_chatbot, "default_standard_set", lambda: object())
    monkeypatch.setattr(_chatbot, "significant_terms", lambda question: ["term"])
    monkeypatch.setattr(
        "knowledge.services.document_frequency", lambda term, standard_set: 1
    )

    probe_chat.probe("a question", chunks_only=True, limit=None)

    assert seen == {"question": "a question", "limit": 4}
