"""Which extractor ran, and does the error say so.

The gate is calibrated to one `pdftotext` implementation. Poppler and Xpdf 4.x wrap lines
and detect columns differently, and `-table` exists only in Xpdf — measured 2026-10-22:
the VPS gate (poppler 24.02.0) failed 15 tests and 61 errors, all extraction differences.
So a deployment must be able to say *which* binary it means, and a missing binary must not
read as an empty document (`testing_hazards.md` §2.9).
"""

from __future__ import annotations

import pytest

from knowledge.extraction import (
    PDFTOTEXT_ENV,
    ExtractionError,
    pdftotext_bin,
    pdftotext_text,
)


def test_the_extractor_defaults_to_path(monkeypatch):
    monkeypatch.delenv(PDFTOTEXT_ENV, raising=False)
    assert pdftotext_bin() == "pdftotext"


def test_an_empty_value_means_the_default(monkeypatch):
    """`.env.example` ships `PDFTOTEXT_BIN=`. An empty binary name is not a binary.

    Mutation: `os.environ.get(NAME, PDFTOTEXT)` returns "" here and the ingest dies with
    `PermissionError: [Errno 13]` on a path that is not a program.
    """
    monkeypatch.setenv(PDFTOTEXT_ENV, "")
    assert pdftotext_bin() == "pdftotext"


def test_the_extractor_can_be_pinned_by_environment(monkeypatch):
    """Mutation: reading the binary at import instead of per call makes this red."""
    monkeypatch.setenv(PDFTOTEXT_ENV, "/opt/xpdf/bin/pdftotext")
    assert pdftotext_bin() == "/opt/xpdf/bin/pdftotext"


def test_a_missing_pinned_binary_names_itself(monkeypatch):
    """The error must name the configured binary, not a default the caller never used."""
    monkeypatch.setenv(PDFTOTEXT_ENV, "definitely-not-pdftotext")
    with pytest.raises(ExtractionError) as caught:
        pdftotext_text("does-not-matter.pdf")
    assert "definitely-not-pdftotext" in str(caught.value)
    assert PDFTOTEXT_ENV in str(caught.value)
