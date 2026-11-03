"""The fixtures every `ingest_standard` test needs, in one place.

They were module-level in `test_ingest.py` until that file crossed the 30 KB cap and
split into three. Importing them keeps one copy: `pytest` discovers a fixture by the
name in the test module's namespace, so `from ... import standard_set` is enough.

Two of them are autouse guards, and both exist because the failure they prevent is
silent:

- `no_live_embeddings` replaces the Gemini provider with a bomb. This box has a key in
  its environment and the command defaults to embedding, so a test that forgets
  `embed=False` would otherwise spend someone's quota.
- `committed_extraction` feeds the ingest the committed pages instead of running
  `pdftotext` (D57): the gate must run where no reader exists, and poppler and Xpdf
  disagree about columns and wrapping (`testing_hazards.md` §2.9).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge.models import StandardSet
from knowledge.tests.page_fixtures import stub_ingest_extraction


@pytest.fixture
def undeclared_opp(monkeypatch):
    """`CORPUS_DOCUMENTS["opp"]` with its `corpus_artefact` declaration removed (D55).

    The behaviour is not a historical accident: a deployment may add a fifth governed document
    before anyone has reviewed it, and then it must parse its PDF. With all four shipped
    documents reviewed, that path needs an explicit fixture rather than a live example.
    """
    from knowledge import ingest

    descriptor = dict(ingest.CORPUS_DOCUMENTS["opp"])
    descriptor.pop("corpus_artefact")
    monkeypatch.setitem(ingest.CORPUS_DOCUMENTS, "opp", descriptor)

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = REPO_ROOT / "pgs_docs"
MANIFEST = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "MANIFEST.json").read_text(encoding="utf-8")
)

#: The plan's ratchet, re-measured. See the module docstring: the appendix fix removed
#: the whole population, so this is a hard zero rather than a known cost.
KNOWN_SAOSO_DUPLICATES = 0

PDFS = {
    "saoso": PDF_DIR / "saoso-version-2.1-2026.pdf",
    "opp": PDF_DIR / "Outeniqua pgs principles, policies and procedures 2026.pdf",
    "bpp": PDF_DIR / "Basic Production Principles_ENG_PRINT.pdf",
    "landscape": PDF_DIR / "PGS Certification landscape_Final.pdf",
}

@pytest.fixture(autouse=True)
def committed_extraction(monkeypatch):
    """Feed the ingest the committed pages instead of running `pdftotext` (D57).

    The ingest's extraction step is the only place this module needs a PDF reader, and the
    deployment gate must run where no reader exists (poppler and Xpdf disagree about
    columns and wrapping — `testing_hazards.md` §2.9). `knowledge/tests/page_fixtures.py`
    holds the seam; nothing about the ingest changes.

    A test that *should* fail when the extractor changes cannot live in the gate: that job
    belongs to `scripts/check_extraction.py`, run by whoever builds artefacts.
    """
    stub_ingest_extraction(monkeypatch)


@pytest.fixture(autouse=True)
def no_live_embeddings(monkeypatch):
    """Any attempt to build the real provider fails the test.

    An ingest test that omits `embed=False` would otherwise make a live API call: the
    command defaults to embedding, and this shell has a key in its environment.
    """

    def bomb(*args, **kwargs):  # pragma: no cover - only runs when the guard fires
        raise AssertionError(
            "a live GeminiEmbeddingProvider was constructed in a test; pass "
            "embed=False or an explicit provider"
        )

    # `embed_texts` resolves the class in `knowledge.embedding`, which is the only
    # place a provider is built when none is injected.
    monkeypatch.setattr(
        "knowledge.embedding.GeminiEmbeddingProvider", bomb, raising=False
    )


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(
        code="outeniqua", label="Outeniqua PGS corpus", is_default=True
    )


@pytest.fixture
def saoso_pdf():
    path = PDFS["saoso"]
    assert path.exists(), f"the governing document is missing: {path}"
    return path


class FakeProvider:
    def __init__(self, dimension=768):
        self.dimension = dimension
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return [[0.1] * self.dimension for _ in texts]


