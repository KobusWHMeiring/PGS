"""The fixtures every retrieval test needs: one corpus, two corpora, and two arms.

They were module-level in `test_retrieval.py` until that file split. Importing them keeps
one copy, which matters here for three reasons:

- `no_live_embeddings` (autouse) is the guard that stops a test reaching Gemini by
  accident — a second copy is a second guard that can disagree.
- `saoso_ingested` and `opp_ingested` ingest the **real** PDFs through the committed page
  fixtures (D57), so they are the expensive part of the suite and must be defined once.
- `FakeProvider` and `vec` define what "a vector" means in these tests; a copy that
  drifted would make one file assert a direction the other never stores.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.ingest import ingest_standard
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.tests.page_fixtures import stub_ingest_extraction

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = REPO_ROOT / "pgs_docs"
SAOSO_PDF = PDF_DIR / "saoso-version-2.1-2026.pdf"
OPP_PDF = PDF_DIR / "Outeniqua pgs principles, policies and procedures 2026.pdf"


def no_live_embeddings(monkeypatch):
    """Retrieval tests must not reach Gemini by accident."""

    def bomb(*args, **kwargs):  # pragma: no cover - only when the guard fires
        raise AssertionError("a live GeminiEmbeddingProvider was constructed in a test")

    monkeypatch.setattr("knowledge.embedding.GeminiEmbeddingProvider", bomb, raising=False)


@pytest.fixture
def saoso_set(db):
    return StandardSet.objects.create(code="saoso-only", label="SAOSO", is_default=True)


@pytest.fixture
def saoso_ingested(saoso_set, settings, monkeypatch):
    settings.GEMINI_API_KEY = ""
    stub_ingest_extraction(monkeypatch)  # D57: no PDF reader in the gate
    return ingest_standard(
        pdf_path=SAOSO_PDF, standard_set=saoso_set, doc_key="saoso", embed=False
    )


@pytest.fixture
def opp_ingested(saoso_set, settings, monkeypatch):
    """The OPP into the same set shape the deployment uses — one corpus, two documents."""
    settings.GEMINI_API_KEY = ""
    stub_ingest_extraction(monkeypatch)
    return ingest_standard(
        pdf_path=OPP_PDF, standard_set=saoso_set, doc_key="opp", embed=False
    )


class FakeProvider:
    """A deterministic provider: the vector encodes which marker word is present."""

    def __init__(self, dimension=768):
        self.dimension = dimension
        self.calls = 0
        self.queries: list[str] = []

    def embed(self, texts):
        self.calls += 1
        self.queries.extend(texts)
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimension
            lowered = text.lower()
            for index, marker in enumerate(
                ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]
            ):
                if marker in lowered:
                    vector[index] = 1.0
            if not any(vector):
                vector[self.dimension - 1] = 0.001
            vectors.append(vector)
        return vectors


def vec(*head: float) -> list[float]:
    """A `vector(768)`-shaped test vector with a meaningful leading direction.

    The column is `vector(768)` because D3/D20 freeze the dimension, so a tidy 2- or
    8-element vector is a `DataError`, not a shortcut. The tail is zero-padded.
    """
    assert len(head) <= 768
    return list(head) + [0.0] * (768 - len(head))


def make_chunk(document, *, ref, text, embedding=None, page=1, heading_path=None):
    return DocumentChunk.objects.create(
        document=document,
        section_ref=ref,
        text=text,
        heading_path=ref if heading_path is None else heading_path,
        page=page,
        embedding=embedding,
    )


@pytest.fixture
def two_sets(db):
    """Two coexisting corpora, each with one document and two chunks."""
    first = StandardSet.objects.create(code="alpha-set", label="Alpha", is_default=True)
    second = StandardSet.objects.create(code="beta-set", label="Beta")
    doc_first = StandardDocument.objects.create(
        standard_set=first, kind="STANDARD", issuing_body="A", title="Alpha standard",
        version="1", source_file="a.pdf", sha256="1" * 64, section_scheme="saoso",
    )
    doc_second = StandardDocument.objects.create(
        standard_set=second, kind="SOP", issuing_body="B", title="Beta procedures",
        version="1", source_file="b.pdf", sha256="2" * 64, section_scheme="opp",
    )
    in_set = make_chunk(doc_first, ref="S20.1.2", text="alpha traceability requirement")
    out_of_set = make_chunk(doc_second, ref="§4.2", text="alpha traceability requirement elsewhere")
    return first, second, in_set, out_of_set


