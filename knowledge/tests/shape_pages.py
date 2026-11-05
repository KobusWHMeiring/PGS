"""The committed page images the verification surface judges the answer key against (D85).

`knowledge/tests/shape_fixtures.py` says what a correct read of eight pages must contain. That
expectation is anchored in the page *text* (`page_fixtures.py`), and text is what R3 checks. But a
reviewer deciding whether a bare row number is a column, or whether `Proud member of` belongs in
column 3, has to look at the paper — and the paper is a PDF that the gate deliberately cannot read
(requirement 10, `P1`'s rule).

So the pages are rendered once (`scripts/render_shape_pages.py`, `pypdfium2` imported there and
nowhere else) and committed here as grayscale JPEGs with both hashes recorded: the PDF they came
from and the image itself. Provenance is checked in both directions on every read, exactly as
`page_fixtures` does: a swapped PDF fails, and a hand-cropped image fails — a cropped screenshot of
a table is precisely the "hand-tidied copy of the page" this repository refuses to call evidence
(`testing_hazards.md` §3.25).

`data_uri()` is what the surface embeds. It is a `data:` URI on purpose: the artefact must open from
disk with the wifi off and make no request at all, and an image that is a separate file is an image
that will one day be missing beside an email attachment.
"""

from __future__ import annotations

import base64
import hashlib
import json
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGE_DIR = Path(__file__).resolve().parent / "fixtures/shape_pages"
MANIFEST = json.loads((IMAGE_DIR / "MANIFEST.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _verified(key: str) -> tuple[bytes, dict]:
    """The committed image for `key`, after proving it and its source PDF are the pinned bytes."""
    record = MANIFEST["pages"].get(key)
    if record is None:
        available = ", ".join(sorted(MANIFEST["pages"]))
        raise AssertionError(
            f"no committed page image for {key!r} — available: {available}. "
            "Render it with `python scripts/render_shape_pages.py`."
        )

    pdf = REPO_ROOT / record["source"]
    if not pdf.exists():  # pragma: no cover - the PDFs are committed
        raise AssertionError(f"{record['source']} is missing from the tree")
    pdf_digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if pdf_digest != record["pdf_sha256"]:
        raise AssertionError(
            f"{record['source']} is not the PDF this page was rendered from "
            f"(manifest {record['pdf_sha256'][:12]}, file {pdf_digest[:12]}). "
            "Re-render deliberately; do not edit the manifest."
        )

    image = IMAGE_DIR / record["image"]
    data = image.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != record["image_sha256"]:
        raise AssertionError(
            f"{record['image']} has been edited (manifest {record['image_sha256'][:12]}, "
            f"file {digest[:12]}). Re-render with `python scripts/render_shape_pages.py`; a "
            "hand-cropped page stops being the paper."
        )
    return data, record


def image(doc_key: str, pdf_page: int) -> bytes:
    """One page's committed JPEG bytes."""
    return _verified(f"{doc_key}:{pdf_page}")[0]


def record(doc_key: str, pdf_page: int) -> dict:
    """The manifest record for one page — source PDF, both hashes, dpi, size."""
    return _verified(f"{doc_key}:{pdf_page}")[1]


def css_class(doc_key: str, pdf_page: int) -> str:
    """The class the surface's stylesheet defines for this page (`page-<doc>_p<n>`)."""
    return f"page-{doc_key}_p{pdf_page}"


def data_uri(doc_key: str, pdf_page: int) -> str:
    """The page as a `data:` URI, for a `background-image` in one self-contained file."""
    data = image(doc_key, pdf_page)
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
