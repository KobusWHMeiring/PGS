"""Embeddings for the corpus — Gemini, with an explicit timeout (B5, D3/D20).

**The dimension is the contract; the model name is not.** `DocumentChunk.embedding` is
a `vector(768)` column, and D3/D20 freeze it because changing it means re-embedding the
whole corpus. The model that produces the vectors may change — so the request asks for
`output_dimensionality=768` explicitly rather than trusting a model's default to be the
same width. `settings.EMBEDDING_MODEL` is `gemini-embedding-001`; `text-embedding-004`,
which `.env.example` originally named, is retired by Google. The freeze is on the
vector's shape, and it survives the swap.

**Failures raise. They never produce zeros.** A zero vector is a legitimate-looking
float list: it would be stored, ranked arbitrarily, and nothing would look broken. Three
shapes of failure are therefore separated:

1. A *transient* provider error is retried with growing backoff up to
   `EMBEDDING_MAX_ATTEMPTS`, then raised as `EmbeddingError`.
2. A *short batch* — fewer vectors than inputs — raises immediately. Padding the
   difference is the same bug as returning zeros, but quieter: `zip()` would hand each
   chunk its neighbour's vector. It is not retried, because it is a provider contract
   violation, not a hiccup.
3. A *wrong width* raises `EmbeddingDimensionError` naming both numbers and the
   consequence, because comparing vectors from two different spaces does not error, it
   just ranks nonsense.

`timeout=` is set per call through `EmbedContentConfig.http_options`. The SDK's unit is
**milliseconds** (`HttpOptions.timeout` documents it), which the suite asserts, because a
timeout of `30` would be 30 ms and every request would fail while looking configured.
"""

from __future__ import annotations

import time
from typing import Protocol

from django.conf import settings

#: A batch size is a request-size limit. 100 keeps a single ingest request well inside
#: the API's payload limit while still amortising round trips per chunk.
EMBEDDING_BATCH_SIZE = 100

#: Milliseconds, matching `google.genai.types.HttpOptions.timeout`. 30 s is generous
#: for a batch of 100 short passages and short enough that a hung call cannot pin a
#: Celery worker — build_principles §VII.2.
EMBEDDING_TIMEOUT_MS = 30_000

#: Total attempts per batch, not additional retries. B6's Celery task carries its own
#: policy; this one exists so a transient 503 inside a live ingest does not discard the
#: whole run.
EMBEDDING_MAX_ATTEMPTS = 3

#: Base seconds for the backoff between attempts: 1, 2 (doubling per attempt).
EMBEDDING_RETRY_BASE_SECONDS = 1.0


class EmbeddingError(RuntimeError):
    """Embedding failed, or the provider broke its side of the contract."""


class EmbeddingDimensionError(EmbeddingError):
    """A vector's width is not the frozen `EMBEDDING_DIM` (D3/D20)."""


class EmbeddingUnavailable(EmbeddingError):
    """No API key is configured, so no request was attempted."""


class EmbeddingProvider(Protocol):
    """What `embed_texts` needs. Tests supply a fake; nothing else changes."""

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        ...


class GeminiEmbeddingProvider:
    """The live provider. The SDK client is built lazily, and only if a key exists.

    Lazy on purpose: importing `knowledge` — which the public site does through the
    retrieval path — must not require a Gemini key, and a test suite must not be able to
    construct a live client by accident.
    """

    name = "gemini"

    def __init__(
        self,
        client=None,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_ms: int = EMBEDDING_TIMEOUT_MS,
        dimension: int | None = None,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self.model = model or settings.EMBEDDING_MODEL
        self.timeout_ms = timeout_ms
        self.dimension = dimension or settings.EMBEDDING_DIM

    @property
    def client(self):
        """In:  nothing. Out: a configured client.
        Fails: `EmbeddingUnavailable` when no key is set — before any import of the SDK
            client is constructed.
        """
        if self._client is not None:
            return self._client

        from google import genai  # imported here so the package is optional at import

        key = self._api_key if self._api_key is not None else settings.GEMINI_API_KEY
        if not key:
            raise EmbeddingUnavailable(
                "GEMINI_API_KEY is not set. Embeddings are unavailable; the corpus can "
                "still be ingested without them (FTS-only retrieval), but B6 must say so."
            )
        self._client = genai.Client(api_key=key)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        """In:  `texts` — non-empty strings, already batched by the caller.
        Out: one vector per text, in order.
        Fails: whatever the SDK raises; `embed_texts` decides what is retryable.
        """
        from google.genai import types

        config = types.EmbedContentConfig(
            output_dimensionality=self.dimension,
            http_options=types.HttpOptions(timeout=self.timeout_ms),
        )
        response = self.client.models.embed_content(
            model=self.model,
            contents=list(texts),
            config=config,
        )
        return [list(embedding.values) for embedding in response.embeddings]


def embed_texts(
    texts: list[str],
    *,
    provider: EmbeddingProvider | None = None,
    batch_size: int = EMBEDDING_BATCH_SIZE,
    dimension: int | None = None,
    attempts: int = EMBEDDING_MAX_ATTEMPTS,
    sleep=time.sleep,
) -> list[list[float]]:
    """Embed `texts`, in bounded batches, in input order.

    In:  `texts` — the chunk texts; `provider` — defaults to Gemini; `dimension` —
         defaults to the frozen `settings.EMBEDDING_DIM`; `sleep` — injectable so tests
         do not wait out the backoff.
    Out: `list[list[float]]`, positionally aligned with `texts`.
    Side Effects: network calls when the real provider is used.
    Fails: `ValueError` for an empty/blank text (naming its index);
        `EmbeddingDimensionError` for a wrong-width vector;
        `EmbeddingError` after `attempts` transient failures, or for a short batch.
    """
    if not texts:
        return []

    for index, text in enumerate(texts):
        if not text or not text.strip():
            raise ValueError(
                f"texts[{index}] is empty. Gemini rejects empty content, and an empty "
                "chunk means the chunker produced one — fix it there, not here."
            )

    target_dimension = dimension or settings.EMBEDDING_DIM
    provider = provider or GeminiEmbeddingProvider()
    vectors: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        batch_vectors = _embed_batch(batch, provider, attempts=attempts, sleep=sleep)
        for offset, vector in enumerate(batch_vectors):
            if len(vector) != target_dimension:
                raise EmbeddingDimensionError(
                    f"texts[{start + offset}] came back with {len(vector)} dimensions, "
                    f"but the corpus column is vector({target_dimension}) "
                    f"({settings.EMBEDDING_MODEL}). A vector of another width is not a "
                    "near-miss: changing the model or the dimension means re-embedding "
                    "the whole corpus."
                )
        vectors.extend(batch_vectors)

    return vectors


def _embed_batch(
    batch: list[str],
    provider: EmbeddingProvider,
    *,
    attempts: int,
    sleep,
) -> list[list[float]]:
    """One batch, retried on a transient error, then raised."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            vectors = provider.embed(batch)
            if len(vectors) != len(batch):
                raise EmbeddingError(
                    f"provider returned {len(vectors)} vectors for {len(batch)} texts. "
                    "Padding the difference with zeros would silently give one chunk "
                    "another chunk's embedding."
                )
            return vectors
        except EmbeddingError:
            raise                      # a contract violation, not a hiccup
        except Exception as error:     # noqa: BLE001 - re-raised below, never swallowed
            last_error = error
            if attempt < attempts:
                sleep(EMBEDDING_RETRY_BASE_SECONDS * (2 ** (attempt - 1)))

    raise EmbeddingError(
        f"embedding failed after {attempts} attempts "
        f"({type(last_error).__name__}: {last_error})"
    ) from last_error
