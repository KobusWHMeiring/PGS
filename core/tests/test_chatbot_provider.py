"""The provider boundary — `GeminiChatModel` itself, with a fake client.

A live Gemini reply occasionally stops mid-token. Measured on 2026-10-19 against
`gemini-2.5-flash` with `max_output_tokens=1024`, a follow-up question in a real
conversation produced:

    json.decoder.JSONDecodeError: Unterminated string starting at: line 2 column 13

which `answer()` re-raised as `UpstreamModelError`, which the view rendered as
*"The assistant cannot reach the answering service right now."*

That is a lie with a cost: the service was reachable, the model had already been
paid for, and the visitor was told to try again later instead of being told the
answer was too long to verify. Worse, it is indistinguishable from a real outage,
so nobody looks for it.

Two rules follow, and this file exists to hold them:

1. The output cap must be large enough for a real answer to finish. 1024 tokens is
   not (the answer that truncated carried four citations).
2. `finish_reason` is the authority on truncation, not the JSON parser. A truncated
   reply is retried once at a larger cap, and if it truncates again the failure is
   `AnswerTruncatedError` — a name that says what happened, so the view can say it
   too, without pretending the model is down.

The fake client is the *boundary* (`models.generate_content`), never the method under
test: patching `answer()` would bypass the very `finish_reason` check this file
guards (testing_hazards §1.3).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.test import override_settings
from google.genai import types

from core.services._chatbot import (
    AnswerTruncatedError,
    GeminiChatModel,
    UpstreamModelError,
)

#: A real-shaped reply: the answer plus one citation, as the schema asks for it.
GOOD_JSON = (
    '{"answer": "Records must let a product be traced.", "citations": '
    '[{"section_ref": "S20.1.1", "quote": "Traceability is required."}], '
    '"insufficient_context": false}'
)

#: What a reply cut mid-string actually looks like, byte for byte from the incident.
TRUNCATED_JSON = '{"answer": "The fee is R100, and the visit fee is '


class _Models:
    """Records the config it was handed and returns the queued responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.configs = []

    def generate_content(self, *, model, contents, config):
        self.configs.append(config)
        if not self._responses:
            raise AssertionError("generate_content called more times than expected")
        return self._responses.pop(0)


class _Client:
    def __init__(self, responses):
        self.models = _Models(responses)

    @property
    def configs(self):
        return self.models.configs


def _response(text, finish_reason, *, prompt_tokens=120, completion_tokens=64):
    return SimpleNamespace(
        text=text,
        candidates=[SimpleNamespace(finish_reason=finish_reason)],
        usage_metadata=SimpleNamespace(
            prompt_token_count=prompt_tokens,
            candidates_token_count=completion_tokens,
        ),
    )


def _model_with(*responses):
    return GeminiChatModel(client=_Client(responses), api_key="test-key")


def _ask(model):
    return model.answer(question="What does the standard require for traceability?",
                        chunks=(), history=())


# --- The cap ---------------------------------------------------------------


def test_the_output_cap_is_read_from_settings_and_can_carry_a_real_answer():
    """1024 tokens truncated a four-citation answer. The floor is 2048, not a taste."""
    client = _Client([_response(GOOD_JSON, types.FinishReason.STOP)])
    model = GeminiChatModel(client=client, api_key="test-key")

    _ask(model)

    assert client.configs[0].max_output_tokens >= 2048, (
        "the shipped 1024-token cap truncated the JSON mid-string in production"
    )


@override_settings(CHAT_MAX_OUTPUT_TOKENS=3000)
def test_the_output_cap_is_overridable_without_touching_code():
    client = _Client([_response(GOOD_JSON, types.FinishReason.STOP)])
    model = GeminiChatModel(client=client, api_key="test-key")

    _ask(model)

    assert client.configs[0].max_output_tokens == 3000, (
        "the setting is not wired to the request"
    )


# --- Truncation ------------------------------------------------------------


def test_a_truncated_reply_is_retried_once_with_a_larger_cap():
    """One retry, with room to finish — not the same cap that just failed."""
    client = _Client(
        [
            _response(TRUNCATED_JSON, types.FinishReason.MAX_TOKENS),
            _response(GOOD_JSON, types.FinishReason.STOP),
        ]
    )
    model = GeminiChatModel(client=client, api_key="test-key")

    reply = _ask(model)

    assert reply.answer == "Records must let a product be traced."
    assert len(client.configs) == 2, "the truncation was not retried"
    assert client.configs[1].max_output_tokens > client.configs[0].max_output_tokens


def test_a_reply_truncated_twice_is_answer_truncated_not_a_json_error():
    """The JSON message is a symptom. The cause has to be the one that is reported."""
    model = _model_with(
        _response(TRUNCATED_JSON, types.FinishReason.MAX_TOKENS),
        _response(TRUNCATED_JSON, types.FinishReason.MAX_TOKENS),
    )

    with pytest.raises(AnswerTruncatedError) as raised:
        _ask(model)

    assert "truncat" in str(raised.value).lower()
    assert "not the requested JSON schema" not in str(raised.value)


def test_a_truncated_reply_is_not_accepted_even_when_the_json_parses():
    """A payload cut after a complete citation array is still a cut answer."""
    complete_but_cut = (
        '{"answer": "The fee is R100 and the visit fee is", "citations": [], '
        '"insufficient_context": false}'
    )
    model = _model_with(
        _response(complete_but_cut, types.FinishReason.MAX_TOKENS),
        _response(complete_but_cut, types.FinishReason.MAX_TOKENS),
    )

    with pytest.raises(AnswerTruncatedError):
        _ask(model)


def test_truncation_is_reported_even_when_the_provider_omits_a_candidate():
    """A missing `candidates` list is not evidence of truncation; parse normally."""
    response = SimpleNamespace(
        text=GOOD_JSON, candidates=[], usage_metadata=None
    )
    model = _model_with(response)

    reply = _ask(model)

    assert reply.answer == "Records must let a product be traced."


# --- Everything else is still an upstream failure --------------------------


def test_bad_json_from_an_untruncated_reply_is_a_plain_upstream_error():
    model = _model_with(_response('{"answer": oops}', types.FinishReason.STOP))

    with pytest.raises(UpstreamModelError) as raised:
        _ask(model)

    assert not isinstance(raised.value, AnswerTruncatedError), (
        "a malformed reply must not be excused as truncation"
    )
    assert "JSON" in str(raised.value)


def test_an_empty_reply_is_an_upstream_error():
    model = _model_with(_response("", types.FinishReason.STOP))

    with pytest.raises(UpstreamModelError):
        _ask(model)
