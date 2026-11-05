#!/usr/bin/env python
"""D80's verification surface needs the paper itself: one page image per shape, committed.

    python scripts/render_shape_pages.py            # render what is missing
    python scripts/render_shape_pages.py --force    # re-render every page, then re-pin the manifest
    python scripts/render_shape_pages.py --check    # verify the committed images; write nothing

Why images exist at all. §3.10 of `INGESTION_ENGINE_PRD.md` found that the eight-shape answer
key is agent-authored: `knowledge/tests/shape_fixtures.py`'s column groupings and cell values
were never read against the paper by a human, so a "pass" means "agrees with our grouping".
`scripts/shape_review.py` builds the surface where the owner judges that key cell by cell, and a
judgement surface without the page is a second copy of the key claiming to be evidence.

Why they are committed, not rendered on the fly. Requirement 10: the gate needs no extractor.
`pypdfium2` is imported lazily inside `render()` and is not a dependency of the suite, exactly like
the eval instruments — so the page images are a build-time act with a recorded banner, like
`pdftotext` (`P1`'s rule and `knowledge/tests/page_fixtures.py`'s manifest). The PDFs themselves
are already committed and already sha256-pinned by `page_fixtures`; this script re-reads that
pinning rather than inventing a second source path.

Scale is a reading decision, not a default: 170 dpi puts a 9 pt table line at ~21 px, which is
legible at fit-width on a laptop and stays legible when the reviewer opens the image full size.
Grayscale JPEG because the documents print black on white and the whole set has to fit in one
self-contained HTML file without a megabyte of photographic noise.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.tests.page_fixtures import MANIFEST as PAGE_MANIFEST  # noqa: E402
from knowledge.tests.shape_fixtures import SHAPES  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "knowledge/tests/fixtures/shape_pages"
MANIFEST = OUT_DIR / "MANIFEST.json"

DEFAULT_DPI = 170
JPEG_QUALITY = 78
BANNER = "pypdfium2"
MANIFEST_VERSION = 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_pdf(doc_key: str) -> tuple[str, Path, str]:
    """The PDF a document key names, its pinned sha256, from the page fixtures' own manifest.

    The page fixtures already pin each document to a committed PDF and its sha256; a second
    lookup table here would be a second place for the paper to move.
    """
    for key, record in PAGE_MANIFEST["pages"].items():
        if key.split(".")[0] == doc_key:
            return record["source"], REPO_ROOT / record["source"], record["pdf_sha256"]
    raise SystemExit(f"no committed page fixture names document {doc_key!r}")


def pages_needed() -> list[tuple[str, int]]:
    """Every (document, PDF page) a shape names, in registry order, without duplicates."""
    wanted: list[tuple[str, int]] = []
    for case in SHAPES:
        for page in case.pdf_pages:
            pair = (case.doc_key, page)
            if pair not in wanted:
                wanted.append(pair)
    return wanted


def image_name(doc_key: str, page: int) -> str:
    return f"{doc_key}_p{page}.jpg"


def render(pdf_path: Path, page_number: int, dpi: int) -> tuple[bytes, int, int]:
    """One PDF page as a grayscale JPEG, with its pixel size. `pypdfium2` lives here only."""
    import pypdfium2 as pdfium  # noqa: PLC0415  (build-time only; the gate never imports it)

    document = pdfium.PdfDocument(str(pdf_path))
    try:
        page = document[page_number - 1]
        bitmap = page.render(scale=dpi / 72)
        image = bitmap.to_pil().convert("L")
    finally:
        document.close()
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue(), image.width, image.height


def build(dpi: int = DEFAULT_DPI, force: bool = False) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries: dict[str, dict] = {}
    for doc_key, page in pages_needed():
        source, pdf_path, pinned = source_pdf(doc_key)
        if not pdf_path.exists():  # pragma: no cover - the PDFs are committed
            raise SystemExit(f"the PDF {source!r} is not on this tree")
        if sha256(pdf_path) != pinned:
            raise SystemExit(
                f"{source!r} no longer hashes to what the page fixtures were made from — "
                "re-extract the page fixtures before judging the key against new ink"
            )
        target = OUT_DIR / image_name(doc_key, page)
        if force or not target.exists():
            data, width, height = render(pdf_path, page, dpi)
            target.write_bytes(data)
        else:  # a re-run without --force still records the size the surface lays out to
            from PIL import Image  # noqa: PLC0415  (build-time only)

            with Image.open(target) as opened:
                width, height = opened.size
        entries[f"{doc_key}:{page}"] = {
            "doc": doc_key,
            "pdf_page": page,
            "source": source,
            "pdf_sha256": sha256(pdf_path),
            "image": target.name,
            "image_sha256": sha256(target),
            "dpi": dpi,
            "width": width,
            "height": height,
            "bytes": target.stat().st_size,
        }
    manifest = {
        "version": MANIFEST_VERSION,
        "banner": BANNER,
        "note": (
            "Rendered from the committed PDFs by `scripts/render_shape_pages.py`. Both hashes are "
            "checked on every read (`knowledge/tests/shape_pages.py`): a swapped PDF or a "
            "hand-cropped image must fail loudly rather than quietly judging the key against "
            "different ink."
        ),
        "pages": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def check() -> list[str]:
    """Every way the committed images disagree with the manifest or with the PDFs they came from."""
    if not MANIFEST.exists():
        return [f"{MANIFEST.relative_to(REPO_ROOT)} is missing — run scripts/render_shape_pages.py"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems: list[str] = []
    for key, record in manifest["pages"].items():
        image = OUT_DIR / record["image"]
        if not image.exists():
            problems.append(f"{key}: {record['image']} is missing")
            continue
        if sha256(image) != record["image_sha256"]:
            problems.append(f"{key}: {record['image']} changed since it was rendered")
        pdf_path = REPO_ROOT / record["source"]
        if not pdf_path.exists():
            problems.append(f"{key}: the source PDF {record['source']!r} is missing")
        elif sha256(pdf_path) != record["pdf_sha256"]:
            problems.append(f"{key}: {record['source']!r} changed since the image was rendered")
    missing = [
        f"{doc}:{page}"
        for doc, page in pages_needed()
        if f"{doc}:{page}" not in manifest["pages"]
    ]
    problems.extend(f"{key}: no image is committed for a page a shape names" for key in missing)
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument("--force", action="store_true", help="re-render every page")
    parser.add_argument("--check", action="store_true", help="verify, write nothing")
    args = parser.parse_args(argv)

    if args.check:
        problems = check()
        for problem in problems:
            print(f"DRIFT {problem}")
        print(f"{len(pages_needed())} pages, {len(problems)} problem(s)")
        return 1 if problems else 0

    manifest = build(dpi=args.dpi, force=args.force)
    total = sum(record["bytes"] for record in manifest["pages"].values())
    print(f"wrote {len(manifest['pages'])} page images, {total / 1024:.0f} KB, to {OUT_DIR.name}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
