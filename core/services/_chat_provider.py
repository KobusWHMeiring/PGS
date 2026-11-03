"""The live provider: Gemini, its schema, and the truncation rule.

Split out of `_chatbot.py` (CONTEXT_CUTS_PRD step 4). This is the only module that talks to
a network, and the only one a deployment can replace wholesale: `ChatModel` is the seam, and
`answer_question` accepts a `provider=` for tests.

**Nothing here decides whether an answer is grounded.** It returns what the model said, or
it raises; the audit and the contract judge the result. A provider that quietly repaired a
reply would be the failure the whole feature exists to prevent -- which is why a reply cut
at the output cap raises `AnswerTruncatedError` instead of being trimmed to look complete.

The two output caps are fallbacks for a `getattr` and are kept equal to the settings
defaults on purpose: a fallback that drifts from the setting is the §2.7 hazard this
deployment has already paid for once (the instrument read 8 while the product ran 5).
"""

from __future__ import annotations

import json
from typing import Sequence

from django.conf import settings

from core.models import ChatMessage
from core.services._chat_prompt import SYSTEM_PROMPT, build_prompt
from core.services._chat_values import (
    AnswerTruncatedError,
    ModelReply,
    UpstreamModelError,
)
from knowledge.services import RetrievedChunk


MODEL_DEFAULT = "gemini-2.5-flash"


MODEL_TIMEOUT_MS = 30_000


#: The output-token budget per generation attempt, and the larger cap one truncation retry
#: may ask for. A cap *below* the JSON's natural size truncates the payload mid-string, and
#: the failure surfaces as "Gemini returned text that is not the requested JSON schema" — a
#: transport limit wearing a parse error's clothes, which the view then renders as an outage.
#: 1024 cut a four-citation answer on 2026-10-19; 2048 cut again on 2026-10-27, because
#: **gemini-2.5-flash's thinking tokens are counted against this cap** — a measured attempt
#: thought 1962 tokens and had 72 left for the answer, so the turn paid for a second call
#: (`_scratch/answer_probe.py`, and `settings.CHAT_MAX_OUTPUT_TOKENS` for the full numbers).
#:
#: Kept equal to the settings defaults on purpose: these are the fallbacks a `getattr` reaches
#: only when settings do not define the name, and a fallback that drifts from the setting is
#: the §2.7 hazard this deployment has already paid for once — the instrument read 8 while the
#: product ran 5. The retry grows to the ceiling and no further: a second truncation is
#: reported, never retried again.
MAX_OUTPUT_TOKENS = 4096
MAX_OUTPUT_TOKENS_CEILING = 8192


#: Gemini's structured-output schema (SPEC Â§13). `sub_ref` is optional because most
#: clauses have none; when supplied it must exist in the chunk's offset map.
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section_ref": {"type": "string"},
                    "sub_ref": {"type": "string"},
                    "quote": {
                        "type": "string",
                        "description": (
                            "A single contiguous excerpt copied character-for-character "
                            "from the cited passage. No ellipses and no stitching; emit a "
                            "separate citation for a separate excerpt."
                        ),
                    },
                },
                "required": ["section_ref", "quote"],
            },
        },
        "insufficient_context": {"type": "boolean"},
    },
    "required": ["answer", "citations", "insufficient_context"],
}


# --- Generation -------------------------------------------------------------



def _finish_reason(response) -> object | None:
    """The provider's reason for stopping, or None when it did not say.

    Defensive on purpose: a missing `candidates` list is common in fakes and must not
    be read as truncation. Only an explicit `MAX_TOKENS` counts.
    """
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    return getattr(candidates[0], "finish_reason", None)


def _is_truncated(finish_reason) -> bool:
    """True only for `MAX_TOKENS`, whether the SDK hands back an enum or a string.

    `FinishReason.MAX_TOKENS` prints as `MAX_TOKENS` or `FinishReason.MAX_TOKENS`
    depending on where it was crossed, so the suffix is matched rather than equality.
    """
    if finish_reason is None:
        return False
    value = getattr(finish_reason, "name", None) or str(finish_reason)
    return str(value).upper().endswith("MAX_TOKENS")


class GeminiChatModel:
    """The live provider. The SDK client is built lazily, and only if a key exists.

    Lazy for the same reason as `knowledge.embedding`: importing this module must not
    require a Gemini key, and a test suite must not be able to construct a live
    client by accident. `timeout=` is passed in **milliseconds**, matching
    `google.genai.types.HttpOptions.timeout`.
    """

    name = "gemini"

    def __init__(
        self,
        client=None,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_ms: int | None = None,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self.model = model or getattr(settings, "CHAT_MODEL", MODEL_DEFAULT)
        self.timeout_ms = int(
            timeout_ms
            if timeout_ms is not None
            else getattr(settings, "CHAT_TIMEOUT_MS", MODEL_TIMEOUT_MS)
        )

    @property
    def client(self):
        """In: nothing. Out: a configured client.
        Fails: `UpstreamModelError` when no key is set."""
        if self._client is not None:
            return self._client

        from google import genai  # imported here so the package is optional at import

        key = self._api_key if self._api_key is not None else settings.GEMINI_API_KEY
        if not key:
            raise UpstreamModelError(
                "GEMINI_API_KEY is not set. The assistant cannot generate an answer; "
                "it must not fall back to an ungrounded one."
            )
        self._client = genai.Client(api_key=key)
        return self._client

    def _output_cap(self) -> int:
        """How many output tokens one attempt may use. A setting, so a deployment can
        raise it without a release (the same rule as every other `CHAT_*` limit)."""
        return int(getattr(settings, "CHAT_MAX_OUTPUT_TOKENS", MAX_OUTPUT_TOKENS))

    def _ceiling(self) -> int:
        """The largest cap a retry may ask for. Truncation is retried once, never looped."""
        return int(
            getattr(
                settings, "CHAT_MAX_OUTPUT_TOKENS_CEILING", MAX_OUTPUT_TOKENS_CEILING
            )
        )

    def _generate(self, prompt: str, max_output_tokens: int):
        """One request at a given cap. Transport failures become `UpstreamModelError`."""
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ANSWER_SCHEMA,
            temperature=0.0,
            max_output_tokens=max_output_tokens,
            http_options=types.HttpOptions(timeout=self.timeout_ms),
        )
        try:
            return self.client.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
        except UpstreamModelError:
            raise
        except Exception as error:  # noqa: BLE001 - re-raised as the domain error
            raise UpstreamModelError(
                f"Gemini request failed ({type(error).__name__}: {error})"
            ) from error

    def answer(
        self,
        *,
        question: str,
        chunks: Sequence[RetrievedChunk],
        history: Sequence[ChatMessage],
    ) -> ModelReply:
        """In: the question, the retrieved chunks and the bounded history.
        Out: a parsed `ModelReply`.
        Side Effects: one network call, or two when the first is cut at the cap.
        Fails: `AnswerTruncatedError` when the provider cut the reply at the cap even
            after the retry; `UpstreamModelError` for any transport, parse or
            empty-response failure.
        """
        prompt = build_prompt(question, chunks, history)

        cap = self._output_cap()
        response = self._generate(prompt, cap)

        # `finish_reason` is the authority, not the JSON parser: a payload cut after a
        # complete citation array parses fine and is still half an answer. Retrying at
        # a larger cap is the cheap fix when the model simply had more to say.
        if _is_truncated(_finish_reason(response)):
            retry_cap = max(cap, min(cap * 2, self._ceiling()))
            if retry_cap > cap:
                response = self._generate(prompt, retry_cap)
                cap = retry_cap
            if _is_truncated(_finish_reason(response)):
                raise AnswerTruncatedError(
                    f"Gemini truncated the reply at the {cap}-token output cap, so it "
                    "is a fragment. A cut answer is not an answer: it is not shown and "
                    "not recorded as one."
                )

        text = getattr(response, "text", None)
        if not text:
            raise UpstreamModelError(
                "Gemini returned no text. An empty response is not an answer."
            )

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise UpstreamModelError(
                f"Gemini returned text that is not the requested JSON schema: {error}"
            ) from error

        if not isinstance(payload, dict):
            raise UpstreamModelError("Gemini returned JSON that is not an object.")

        usage = getattr(response, "usage_metadata", None)
        return ModelReply(
            answer=str(payload.get("answer") or ""),
            citations=tuple(payload.get("citations") or ()),
            insufficient_context=bool(payload.get("insufficient_context")),
            model=self.model,
            prompt_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            completion_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
        )
