"""Which extractor ran, in which encoding, and does the error say so.

The gate is calibrated to one `pdftotext` implementation. Poppler and Xpdf 4.x wrap lines
and detect columns differently, and `-table` exists only in Xpdf — measured 2026-10-22:
the VPS gate (poppler 24.02.0) failed 15 tests and 61 errors, all extraction differences.
So a deployment must be able to say *which* binary it means, and a missing binary must not
read as an empty document (`testing_hazards.md` §2.9).

**The output encoding is part of that contract** (`testing_hazards.md` §1.34). Xpdf 4.00's
`-enc` default is Latin-1, not UTF-8: measured 2026-10-27, 275 of the 433 154 bytes in the
eight shipped PDFs are 8-bit and none of them is valid UTF-8. Decoding that stream as UTF-8
with `errors="replace"` — which is what this module did until then — turned every `°`, `²`,
`–`, `§` and `é` in the corpus into U+FFFD: 83 characters across the four ingested
documents, including `ros�` for `rosé` on a public page.
"""

from __future__ import annotations

import subprocess

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


# --- The output encoding ------------------------------------------------------

#: A per-character test, not a PDF test: these are the bytes Xpdf writes when it is not asked
#: for UTF-8. `360\xb0` is what the shipped SAOSO page 26 actually contains (it prints 360°).
LATIN1_DEGREE = b"moving freely around 360\xb0, or kept in isolation\n"
UTF8_DEGREE = "moving freely around 360\u00b0, or kept in isolation\n"


def _fake_extractor(monkeypatch, stdout: bytes) -> dict:
    """Replace `pdftotext` with a process that returns `stdout`, recording the command."""
    seen: dict = {}

    def fake_run(command, **kwargs):
        seen["command"] = list(command)
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return seen


def test_the_extract_asks_the_build_for_utf8(monkeypatch):
    """`-enc UTF-8` is the corpus contract, in every mode.

    Mutation: drop the flag and Xpdf emits Latin-1, and the byte it emits for `°` is not
    valid UTF-8 — so the character is lost even though the page prints it. This is the one
    place the requirement can be asserted on a machine with no PDF reader (D57).
    """
    seen = _fake_extractor(monkeypatch, UTF8_DEGREE.encode("utf-8"))
    assert pdftotext_text("page.pdf") == UTF8_DEGREE

    command = seen["command"]
    assert "-enc" in command, command
    assert command[command.index("-enc") + 1] == "UTF-8", command


def test_every_mode_asks_for_utf8():
    """`-table` and `-raw` are extractions too, and a mode that forgets the flag is a mode
    whose comparison is made against U+FFFD: `knowledge/tables.py` is verified with `-table`
    and `scripts/build_corpus.py` reads `-raw`."""
    from knowledge.extraction import (
        PDFTOTEXT_ARGS,
        PDFTOTEXT_RAW_ARGS,
        PDFTOTEXT_TABLE_ARGS,
    )

    for args in (PDFTOTEXT_ARGS, PDFTOTEXT_RAW_ARGS, PDFTOTEXT_TABLE_ARGS):
        assert "-enc" in args and "UTF-8" in args, args


def test_a_build_that_ignores_the_encoding_fails_loudly(monkeypatch):
    """A Latin-1 stream must not become U+FFFD in silence.

    Mutation: `errors="replace"` is exactly that silence — the reader then prints `360�`
    where the paper prints `360°`, and the audit compares a quote against a text that no
    longer holds the character the document prints.
    """
    _fake_extractor(monkeypatch, LATIN1_DEGREE)
    with pytest.raises(ExtractionError) as caught:
        pdftotext_text("latin-1-page.pdf")

    message = str(caught.value)
    assert "UTF-8" in message
    assert "latin-1-page.pdf" in message, "the failure must name the file it was reading"
