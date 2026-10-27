"""PDF to page text — one implementation, used by the fixtures and by ingestion.

This module exists because of a specific hazard. A10's fixtures are evidence *only*
because they are byte-identical to `pdftotext -layout` output from the shipped PDFs.
B2's parsers were written and tested against those bytes. If ingestion extracted text
some other way — a different tool, a different flag, its own line-ending handling — the
parsers would be tested against one rendering and run against another, and the failure
mode is the one that started this project: a parser that matches nothing in the real
document while its tests stay green.

So there is exactly one extraction call, `pdftotext -layout <pdf> -`, and both
`scripts/extract_fixtures.py` and `knowledge/ingest.py` go through it. The script still
verifies anchors and writes the manifest; it no longer owns the extraction.

`-layout` is not decoration: without it the two-column BPP and landscape interleave
differently, and the SAOSO footers this parser reads page numbers from move. The flag
is part of the contract with the fixtures.

`-enc UTF-8` is not decoration either, and it cost this project 83 characters
(`testing_hazards.md` §1.33). Xpdf 4.00's output encoding defaults to **Latin-1**, so its
`-layout` stream carries raw 8-bit bytes for every glyph it maps outside ASCII — the degree
sign in `360°`, the superscript in `100 m²`, the en dash in `Section B – Appendix 6`, the
`é` in `rosé`. Decoding that stream as UTF-8 (as this module did, with `errors="replace"`)
turns each one into U+FFFD, and the corpus then quotes a sentence the document does not
print. Poppler's default happens to be UTF-8, which is exactly why the defect could only
appear on one of the two builds this repo supports — so the flag is now explicit and the
decode is strict.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

#: The extractor binary. `pdftotext` resolves through PATH — poppler on Debian/Ubuntu,
#: Xpdf on a developer box — and the two do **not** produce the same bytes: they wrap
#: lines and detect columns differently, so the parsers' golden tables (which pages are
#: column-laid-out, which wraps are rejoined) match only the implementation they were
#: measured against. `PDFTOTEXT_BIN` pins one explicitly, per deployment, without
#: shadowing `pdftotext` for every other app on a shared host.
#:
#: Measured 2026-10-22: the VPS gate ran poppler 24.02.0 and failed 15 tests and 61
#: errors, every one of them an extraction difference; `-table` does not exist in
#: poppler at all (`exit 99`), so Appendix 2's verification is Xpdf-4-only.
PDFTOTEXT = "pdftotext"
PDFTOTEXT_ENV = "PDFTOTEXT_BIN"

#: The encoding every mode asks the extractor for. Explicit because the two supported builds
#: disagree by default (Xpdf: Latin-1, poppler: UTF-8), and the decode below is strict.
PDFTOTEXT_ENCODING = "UTF-8"

PDFTOTEXT_ARGS = ("-layout", "-enc", PDFTOTEXT_ENCODING)

#: The second extraction mode. Xpdf's `-table` aligns cells row by row where `-layout`
#: leaves a table's condition column vertically offset; measured 2026-10-21 on SAOSO
#: Appendix 2 (pdf 77–79). It is used to *curate and verify* `knowledge/tables.py`, not
#: to ingest free text: the reviewed rows are data, and the golden test checks every cell
#: against this output. Adding a mode is deliberate — a document must not silently flip
#: rendering, because the parsers were written against `-layout`.
PDFTOTEXT_TABLE_ARGS = ("-table", "-enc", PDFTOTEXT_ENCODING)

#: The third extraction mode: the producer's own content-stream order. It is not the
#: corpus contract — spacing between text-show operations is lost, so words glue together
#: (`Sourcedlocallyfromneighbouring`) — but it is the only *order* oracle available without
#: a layout library, and it is a character-for-character permutation of `-layout` on every
#: page of the four governed documents (measured 2026-10-22). `scripts/build_corpus.py`
#: uses it only where it is word-clean, as a per-page fallback for columns that defeat the
#: geometry (D53).
PDFTOTEXT_RAW_ARGS = ("-raw", "-enc", PDFTOTEXT_ENCODING)

_MODES = {"layout": PDFTOTEXT_ARGS, "table": PDFTOTEXT_TABLE_ARGS, "raw": PDFTOTEXT_RAW_ARGS}

#: wkhtmltopdf/poppler separate pages with a form feed. It is kept in the text rather
#: than consumed here, because page-awareness is a requirement of B2/B3 and of the
#: `page` column (D42): a fixture or an ingest that flattened pages could not place a
#: clause on a page at all.
PAGE_SEPARATOR = "\f"


class ExtractionError(RuntimeError):
    """The PDF could not be read. Never swallowed: an empty ingest looks like success."""


def pdftotext_bin() -> str:
    """The extractor to run: `PDFTOTEXT_BIN`, else `pdftotext` from PATH.

    Read per call, not at import, so a deployment (and a test) can pin the implementation
    without a module reload — and so the value a run actually used is the value that
    appears in its error messages.
    """
    # `or`, not a default argument: `.env.example` ships `PDFTOTEXT_BIN=` (empty), and an
    # empty binary name is a `PermissionError`, not "use the default".
    return os.environ.get(PDFTOTEXT_ENV) or PDFTOTEXT


def pdftotext_text(pdf_path: str | Path, *, mode: str = "layout") -> str:
    """The whole document, raw, pages separated by form feeds.

    In:  `pdf_path` — a path to a PDF; `mode` — `"layout"` (the corpus contract) or
         `"table"` (row-aligned, for reading and verifying a printed table).
    Out: the text as `pdftotext <mode> -enc UTF-8` emits it, decoded strictly as UTF-8.
    Fails: `ExtractionError` when `pdftotext` is missing or exits non-zero, naming the
        file — a missing poppler install must not read as "the document is empty" —
        when the build ignores `-enc` and returns bytes that are not UTF-8, and
        `ValueError` for an unknown mode, so a typo cannot silently fall back to the
        wrong rendering.

    The decode is strict on purpose. `errors="replace"` looks forgiving and is not: it is
    how `360°`, `100 m²` and `rosé` became `360�`, `100 m�` and `ros�` in the corpus, with
    no error anywhere and a passing test suite (§1.33).
    """
    args = _MODES.get(mode)
    if args is None:
        raise ValueError(f"unknown extraction mode {mode!r}; expected one of {sorted(_MODES)}")
    path = Path(pdf_path)
    binary = pdftotext_bin()
    try:
        result = subprocess.run(
            [binary, *args, str(path), "-"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as error:  # pragma: no cover - environment guard
        raise ExtractionError(
            f"`{binary}` not found. It is required to read the corpus documents "
            f"(set {PDFTOTEXT_ENV} to pin a specific build); install it or the ingest "
            "cannot run."
        ) from error
    except subprocess.CalledProcessError as error:  # pragma: no cover - environment
        raise ExtractionError(
            f"`{binary}` failed on {path.name}: {error.stderr!r}"
        ) from error
    try:
        return result.stdout.decode(PDFTOTEXT_ENCODING)
    except UnicodeDecodeError as error:
        # Loud, and specific about the cause: a build whose `-enc` is ignored (or a
        # differently-named flag) is the only way to reach this, and the fix is the binary.
        raise ExtractionError(
            f"`{binary}` did not return {PDFTOTEXT_ENCODING} on {path.name}: {error}. "
            "The extraction asks for `-enc UTF-8`; a build that ignores it returns "
            "Latin-1, and every accented or symbol character then arrives as a raw byte."
        ) from error


def normalise(text: str) -> str:
    """Make text byte-stable across platforms and runs.

    `\\r\\n` -> `\\n` (pdftotext honours the platform's line separator), and trailing
    whitespace stripped per line. Applied identically by the fixture script and by
    ingestion — a difference here is a difference between the tested bytes and the
    ingested ones.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n"))


def pages_of(text: str) -> list[str]:
    """Split raw document text into normalised pages. Page N is `pages[N - 1]`."""
    return [normalise(page) for page in text.split(PAGE_SEPARATOR)]


def extract_pages(pdf_path: str | Path, *, mode: str = "layout") -> list[str]:
    """The document as normalised pages — what the section parsers consume."""
    return pages_of(pdftotext_text(pdf_path, mode=mode))


def sha256_of(path: str | Path) -> str:
    """The content hash used as the re-ingestion idempotency key (B6)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


__all__ = [
    "ExtractionError",
    "PDFTOTEXT",
    "PDFTOTEXT_ARGS",
    "PDFTOTEXT_ENCODING",
    "PDFTOTEXT_ENV",
    "PDFTOTEXT_RAW_ARGS",
    "PDFTOTEXT_TABLE_ARGS",
    "extract_pages",
    "normalise",
    "pages_of",
    "pdftotext_bin",
    "pdftotext_text",
    "sha256_of",
]
