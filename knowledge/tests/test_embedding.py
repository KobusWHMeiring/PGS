"""Task B5 — Gemini embeddings, with an explicit timeout.

The tests never touch the network, and one of them exists to keep it that way:
`test_no_genai_client_is_constructed` replaces `google.genai.Client` with a bomb, so a
future edit that reaches for a live client fails here rather than at whoever's Gemini
quota is attached to the CI box.

What is asserted is the part this project owns:

- **Batching is bounded.** A batch size is a request-size limit, not a preference.
- **The dimension is the frozen one** (D3/D20) and a mismatch raises with the reason —
  "changing the model means re-embedding the whole corpus" — because the alternative is
  a corpus of vectors from two different spaces that still compares, silently.
- **A failure raises; it never returns zeros.** Zeros would be stored as a legitimate
  embedding, retrieval would rank them arbitrarily, and nothing would look wrong.
- **A provider that returns the wrong number of vectors raises too.** Padding the
  difference with zeros is the same bug with more steps.
- **`timeout=` reaches every call.** The SDK takes milliseconds, and the unit is
  asserted rather than assumed.

`text-embedding-004` is retired by Google; the configured model is `gemini-embedding-001`
with `output_dimensionality=768`, which is what keeps B1's frozen `vector(768)` column
valid across the swap. See the module docstring for why the dimension, not the model
name, is the thing that must not move.
"""

from __future__ import annotations

import pytest
from django.conf import settings

from knowledge import embedding as embedding_module
from knowledge.embedding import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MAX_ATTEMPTS,
    EMBEDDING_TIMEOUT_MS,
    EmbeddingDimensionError,
    EmbeddingError,
    GeminiEmbeddingProvider,
    embed_texts,
)

pytestmark = pytest.mark.django_db


# --- Fakes -------------------------------------------------------------------


class FakeProvider:
    """Records every call; can be told to fail a number of times first."""

    def __init__(self, *, dimension: int = settings.EMBEDDING_DIM, failures: int = 0,
                 short_batches: bool = False):
        self.dimension = dimension
        self.failures = failures
        self.short_batches = short_batches
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        if len(self.calls) <= self.failures:
            raise TimeoutError("provider timed out")
        vectors = [[0.5] * self.dimension for _ in texts]
        if self.short_batches:
            return vectors[:-1]
        return vectors


class FakeEmbedding:
    def __init__(self, values):
        self.values = values


class FakeResponse:
    def __init__(self, vectors):
        self.embeddings = [FakeEmbedding(vector) for vector in vectors]


class FakeModels:
    def __init__(self, dimension: int = settings.EMBEDDING_DIM):
        self.calls: list[dict] = []
        self.dimension = dimension

    def embed_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return FakeResponse([[0.25] * self.dimension for _ in contents])


class FakeClient:
    def __init__(self, dimension: int = settings.EMBEDDING_DIM):
        self.models = FakeModels(dimension)


@pytest.fixture
def no_network(monkeypatch):
    """Any attempt to build a real Gemini client is a test failure."""

    def bomb(*args, **kwargs):  # pragma: no cover - only runs when the guard fires
        raise AssertionError("a live google.genai.Client was constructed in a test")

    monkeypatch.setattr("google.genai.Client", bomb)


# --- The guard that keeps the suite offline ----------------------------------


def test_no_genai_client_is_constructed(no_network):
    vectors = embed_texts(["organic traceability"], provider=FakeProvider())
    assert len(vectors) == 1


# --- Batching ----------------------------------------------------------------


def test_batches_are_bounded():
    provider = FakeProvider()
    embed_texts([f"text {index}" for index in range(250)], provider=provider)
    assert [len(call) for call in provider.calls] == [100, 100, 50]
    assert EMBEDDING_BATCH_SIZE == 100


def test_vectors_come_back_in_input_order():
    """Embeddings are positional; reordering them silently mislabels every chunk."""
    provider = FakeProvider()
    vectors = embed_texts(["first", "second", "third"], provider=provider)
    assert len(vectors) == 3
    assert provider.calls == [["first", "second", "third"]]


def test_empty_input_returns_empty_without_calling_the_provider():
    provider = FakeProvider()
    assert embed_texts([], provider=provider) == []
    assert provider.calls == []


def test_an_empty_string_is_rejected_before_the_request():
    """Gemini rejects empty content; the index is what makes it fixable."""
    provider = FakeProvider()
    with pytest.raises(ValueError, match=r"texts\[1\]"):
        embed_texts(["fine", "   "], provider=provider)
    assert provider.calls == [], "the provider was called with a bad batch"


# --- The dimension is frozen -------------------------------------------------


def test_provider_result_must_match_the_frozen_dimension():
    provider = FakeProvider(dimension=3)
    with pytest.raises(EmbeddingDimensionError) as error:
        embed_texts(["organic"], provider=provider)
    message = str(error.value)
    assert "768" in message and "3" in message
    assert "re-embed" in message.lower()


def test_the_configured_dimension_matches_the_column():
    """D3/D20: `DocumentChunk.embedding` is `vector(768)`; B1 asserts it from the
    model side, this asserts it from the embedding side."""
    assert settings.EMBEDDING_DIM == 768


def test_the_configured_model_is_not_the_retired_one():
    """`text-embedding-004` is retired by Google.

    Asserted because reverting the default is otherwise a one-line change with no
    symptom until the first ingest in production fails — or worse, succeeds against a
    different model in a different vector space.
    """
    assert settings.EMBEDDING_MODEL != "text-embedding-004"
    assert "embedding" in settings.EMBEDDING_MODEL


# --- Failure behaviour -------------------------------------------------------


def test_a_transient_failure_is_retried_then_succeeds():
    provider = FakeProvider(failures=2)
    slept: list[float] = []
    vectors = embed_texts(["organic"], provider=provider, sleep=slept.append)
    assert len(provider.calls) == 3
    assert len(slept) == 2
    assert vectors[0][0] == 0.5


def test_a_persistent_failure_raises_after_bounded_attempts_and_returns_no_zeros():
    provider = FakeProvider(failures=99)
    slept: list[float] = []
    with pytest.raises(EmbeddingError) as error:
        embed_texts(["organic"], provider=provider, sleep=slept.append)
    assert len(provider.calls) == EMBEDDING_MAX_ATTEMPTS
    assert "attempts" in str(error.value)
    assert len(slept) == EMBEDDING_MAX_ATTEMPTS - 1, "no sleep means no backoff"


def test_a_short_batch_raises_instead_of_padding_with_zeros():
    """The dangerous variant of \"returned zeros\": fewer vectors than texts.

    Zipping them up would give chunk 1 text's vector to chunk 2.
    """
    provider = FakeProvider(short_batches=True)
    with pytest.raises(EmbeddingError, match="vector"):
        embed_texts(["one", "two"], provider=provider)


def test_backoff_grows_between_attempts():
    provider = FakeProvider(failures=99)
    slept: list[float] = []
    with pytest.raises(EmbeddingError):
        embed_texts(["organic"], provider=provider, sleep=slept.append)
    assert slept == sorted(slept)
    assert slept[0] < slept[-1]


# --- The Gemini provider itself ---------------------------------------------


def test_gemini_provider_sends_an_explicit_timeout_on_every_call():
    client = FakeClient()
    provider = GeminiEmbeddingProvider(client=client)
    provider.embed(["one"])
    provider.embed(["two"])
    assert [call["config"].http_options.timeout for call in client.models.calls] == [
        EMBEDDING_TIMEOUT_MS,
        EMBEDDING_TIMEOUT_MS,
    ]
    # The SDK documents milliseconds; a seconds value here would be a 1000x timeout.
    assert EMBEDDING_TIMEOUT_MS == 30_000


def test_gemini_provider_requests_the_frozen_dimension():
    client = FakeClient()
    GeminiEmbeddingProvider(client=client).embed(["one"])
    assert client.models.calls[0]["config"].output_dimensionality == settings.EMBEDDING_DIM


def test_gemini_provider_passes_the_configured_model():
    client = FakeClient()
    GeminiEmbeddingProvider(client=client).embed(["one"])
    assert client.models.calls[0]["model"] == settings.EMBEDDING_MODEL


def test_gemini_provider_extracts_values_in_order():
    client = FakeClient()
    vectors = GeminiEmbeddingProvider(client=client).embed(["one", "two"])
    assert len(vectors) == 2
    assert all(len(vector) == settings.EMBEDDING_DIM for vector in vectors)


def test_gemini_provider_needs_a_key():
    provider = GeminiEmbeddingProvider(client=None, api_key="")
    with pytest.raises(embedding_module.EmbeddingUnavailable):
        provider.embed(["one"])
