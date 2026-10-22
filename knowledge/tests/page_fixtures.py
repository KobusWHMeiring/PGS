"""The committed pages every extraction-dependent test reads (D57).

`pdftotext` is not one thing. Poppler and Xpdf wrap lines and detect columns differently,
and `-table` exists only in Xpdf — measured 2026-10-22: the deployment target's gate failed
15 tests and 61 errors, all of them extraction differences (`testing_hazards.md` §2.9). The
parsers' goldens were measured on Xpdf 4.00, so the gate cannot keep *calling* an extractor
and still be portable.

These fixtures are that output, committed once: every page of the four governed documents, in
each mode the tests need, with the extractor banner and the source PDF's sha256 recorded in
`MANIFEST.json`. The tests apply the transform themselves, so their assertions are unchanged
— only their input moves from a pipe to a file.

Provenance is checked on every read, in both directions: the shipped PDF must still hash to
the digest the fixture was made from, and the fixture file must still hash to the digest in
the manifest. A swapped PDF or a hand-edited fixture fails loudly instead of quietly testing
different bytes.

`scripts/extract_fixtures.py` regenerates these; `scripts/check_extraction.py` re-extracts
and diffs them against the current extractor, on the machine that builds artefacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
MANIFEST = json.loads((FIXTURE_DIR / "MANIFEST.json").read_text(encoding="utf-8"))

#: What each fixture may be read as. `table` is SAOSO-only: it exists to verify Appendix 2's
#: reviewed cells against the printed page, and no other document has a table under test.
MODES = {"layout": "layout", "raw": "raw", "table": "table"}


def entry(doc_key: str, mode: str = "layout") -> dict:
    """The manifest record for one fixture, or an error naming what does exist."""
    if mode not in MODES:
        raise ValueError(f"unknown extraction mode {mode!r}; expected {sorted(MODES)}")
    key = f"{doc_key}.{mode}"
    record = MANIFEST["pages"].get(key)
    if record is None:
        available = ", ".join(sorted(MANIFEST["pages"]))
        raise AssertionError(
            f"no committed pages for {key!r} — available: {available}. "
            "Regenerate with `python scripts/extract_fixtures.py`."
        )
    return record


def pages(doc_key: str, mode: str = "layout") -> list[str]:
    """The document's pages, exactly as `extract_pages(pdf, mode=mode)` returns them."""
    record = entry(doc_key, mode)

    pdf = REPO_ROOT / record["source"]
    if not pdf.exists():  # pragma: no cover - the PDFs are committed
        raise AssertionError(f"{record['source']} is missing from the tree")
    pdf_digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if pdf_digest != record["pdf_sha256"]:
        raise AssertionError(
            f"{record['source']} is not the PDF these pages were extracted from "
            f"(fixture {record['pdf_sha256'][:12]}, file {pdf_digest[:12]}). "
            "Regenerate the fixtures deliberately; do not edit the manifest."
        )

    # Universal newlines: the fixture is stored with `\n`, and a Windows checkout may hand
    # back `\r\n`. Re-encoding after normalisation is what the manifest hashed.
    text = (REPO_ROOT / record["file"]).read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != record["sha256"]:
        raise AssertionError(
            f"{record['file']} has been edited (manifest {record['sha256'][:12]}, "
            f"file {digest[:12]}). Regenerate with `python scripts/extract_fixtures.py`; "
            "a hand-edited page stops being evidence."
        )

    page_list = text.split("\f")
    if len(page_list) != record["pages"]:
        raise AssertionError(
            f"{record['file']} has {len(page_list)} pages, manifest says {record['pages']}"
        )
    return page_list


def stub_ingest_extraction(monkeypatch) -> None:
    """Point `knowledge.ingest.extract_pages` at the committed pages.

    The seam exists so a test can run *the real ingest* — the real parser, chunker, table
    rows and transaction — without a PDF reader, which the deployment gate deliberately
    does not have (D57). It patches the import, not the service, so nothing about ingest
    changes.

    An unknown path raises `ExtractionError`, keeping the one property the ingest must
    never lose: an extraction failure is loud, never an empty document.
    """
    from knowledge import ingest
    from knowledge.extraction import ExtractionError

    key_by_name = {
        Path(record["source"]).name: key.split(".", 1)[0]
        for key, record in MANIFEST["pages"].items()
    }

    def _committed(path, *, mode="layout"):
        doc_key = key_by_name.get(Path(path).name)
        if doc_key is None:
            raise ExtractionError(f"`pdftotext` failed on {Path(path).name}: not a PDF")
        return pages(doc_key, mode)

    monkeypatch.setattr(ingest, "extract_pages", _committed)
