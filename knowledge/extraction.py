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
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

PDFTOTEXT = "pdftotext"
PDFTOTEXT_ARGS = ("-layout",)

#: wkhtmltopdf/poppler separate pages with a form feed. It is kept in the text rather
#: than consumed here, because page-awareness is a requirement of B2/B3 and of the
#: `page` column (D42): a fixture or an ingest that flattened pages could not place a
#: clause on a page at all.
PAGE_SEPARATOR = "\f"


class ExtractionError(RuntimeError):
    """The PDF could not be read. Never swallowed: an empty ingest looks like success."""


def pdftotext_text(pdf_path: str | Path) -> str:
    """The whole document, raw, pages separated by form feeds.

    In:  `pdf_path` — a path to a PDF.
    Out: the text as `pdftotext -layout` emits it, decoded UTF-8 with replacement.
    Fails: `ExtractionError` when `pdftotext` is missing or exits non-zero, naming the
        file — a missing poppler install must not read as "the document is empty".
    """
    path = Path(pdf_path)
    try:
        result = subprocess.run(
            [PDFTOTEXT, *PDFTOTEXT_ARGS, str(path), "-"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as error:  # pragma: no cover - environment guard
        raise ExtractionError(
            f"`{PDFTOTEXT}` not found. It is part of poppler-utils and is required to "
            "read the corpus documents; install it or the ingest cannot run."
        ) from error
    except subprocess.CalledProcessError as error:  # pragma: no cover - environment
        raise ExtractionError(
            f"`{PDFTOTEXT}` failed on {path.name}: {error.stderr!r}"
        ) from error
    return result.stdout.decode("utf-8", errors="replace")


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


def extract_pages(pdf_path: str | Path) -> list[str]:
    """The document as normalised pages — what the section parsers consume."""
    return pages_of(pdftotext_text(pdf_path))


def sha256_of(path: str | Path) -> str:
    """The content hash used as the re-ingestion idempotency key (B6)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


__all__ = [
    "ExtractionError",
    "PDFTOTEXT",
    "PDFTOTEXT_ARGS",
    "extract_pages",
    "normalise",
    "pages_of",
    "pdftotext_text",
    "sha256_of",
]
