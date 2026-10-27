"""Probe the concordance derivation against the corpus in this database.

Read-only. Prints what `product/backlog/ready/CONCORDANCE_PLAN.md` claims, so the claims can be
checked before Task 1 is started and again after it lands:

- the branches each document produces, their printed pages and their passage counts;
- the branch titles once the stored TOC is applied (SAOSO's is read from the committed page
  fixture, because the fieldwork for the plan ran before `StandardDocument.toc` existed);
- the printed sections the corpus does not hold;
- how many passage anchors are ambiguous — the defect `CONCORDANCE_PLAN.md` Task 4 closes.

Usage:
    python scripts/probe_concordance.py            # all ingested documents
    python scripts/probe_concordance.py --toc      # ... with SAOSO's stored TOC applied

Before running it on a developer machine:

    python manage.py publish_documents       # if the reader says "not published the text"
    python manage.py ingest_standard --doc saoso \\
        --file pgs_docs/saoso-version-2.1-2026.pdf --no-embed   # if the corpus is empty

Two things this does **not** establish: the page's weight after the change, and the phone layout.
Those are Task 9 and `tests/uat/concordance_uat.md`.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")

import django  # noqa: E402

django.setup()

from django.utils.text import slugify  # noqa: E402

from knowledge.models import DocumentChunk, StandardDocument  # noqa: E402
from knowledge.reading import _slugify_locator, reading_anchor, reading_chunks  # noqa: E402
from knowledge.sections.toc import parse_toc  # noqa: E402

#: Roman section numbers the OPP prints beside decimal body numbering (`§II` covers `2.1`).
_ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
}

#: The plan's anchor budget: the first few words of a passage, so the anchor reads like a locator.
DISAMBIGUATOR_WORDS = 4
MAX_DISAMBIGUATOR_CHARS = 40
TRAILING_CONNECTIVES = {"and", "or", "of", "the", "with", "for", "to"}


def _ref_key(section_ref: str) -> str:
    """`S5.1.9` → `S5`; `§4.5(2)(c)` → `§4`; `§II` → `§2`; `Appendix 2` unchanged."""
    ref = section_ref.strip()
    for prefix in ("S", "§"):
        if ref.startswith(prefix):
            head = ref.split(".", 1)[0].strip()[len(prefix) :]
            if head.upper() in _ROMAN:
                return f"{prefix}{_ROMAN[head.upper()]}"
            return f"{prefix}{head}"
    return ref


def _match_key(label: str) -> str:
    """The key a TOC label and a branch key can be compared on (`S5` and `5` are one division)."""
    ref = label.strip()
    if len(ref) > 1 and ref[0] in "S§" and ref[1].isdigit():
        return ref[1:]
    return ref


def _branch_key(at: DocumentChunk) -> str:
    if at.section_ref:
        return _ref_key(at.section_ref)
    if at.heading_path:
        return at.heading_path.split(" > ", 1)[0].strip()
    return "Preliminary pages"


def _first_heading(chunks: list[DocumentChunk]) -> str | None:
    for at in chunks:
        if at.heading_path:
            return at.heading_path.split(" > ", 1)[0].strip()
    return None


def _content_slug(chunk: DocumentChunk) -> str:
    for candidate in (
        chunk.anchor,
        (chunk.text or "").split("\n", 1)[0],
        chunk.heading_path.split(" > ")[-1],
    ):
        slug = _slugify_locator(candidate) if candidate and candidate.strip() else ""
        if slug:
            words = slug.split("-")[:DISAMBIGUATOR_WORDS]
            while len(words) > 1 and words[-1] in TRAILING_CONNECTIVES:
                words.pop()
            return "-".join(words)[:MAX_DISAMBIGUATOR_CHARS].strip("-")
    return "passage"


def unique_anchors(chunks: list[DocumentChunk]) -> list[tuple[DocumentChunk, str]]:
    """The plan's Task 4 derivation: the first passage of a shared reference keeps the bare anchor."""
    used: set[str] = set()
    pairs: list[tuple[DocumentChunk, str]] = []
    for chunk in chunks:
        base = reading_anchor(chunk.section_ref, chunk.anchor, chunk.heading_path)
        if base not in used:
            used.add(base)
            pairs.append((chunk, base))
            continue
        candidate = f"{base}-{_content_slug(chunk)}"
        attempt = 1
        while candidate in used:
            attempt += 1
            candidate = f"{base}-{attempt}"
        used.add(candidate)
        pairs.append((chunk, candidate))
    return pairs


def _toc_title(entry: dict) -> str:
    label = entry["label"].strip()
    title = (entry.get("title") or "").strip()
    return f"{label}. {title}" if title else label


def _reference_title(key: str, chunks: list[DocumentChunk]) -> str:
    section_ref = chunks[0].section_ref if chunks else None
    if section_ref and section_ref.startswith("S") and section_ref[1:].isdigit():
        return f"Section {section_ref[1:]}"
    return section_ref or key


def build(document: StandardDocument, toc: list[dict]) -> tuple[list[dict], list[str]]:
    """The plan's `build_concordance`, as a dict-per-row report."""
    pairs = unique_anchors(reading_chunks(document))
    order: list[str] = []
    grouped: dict[str, list[DocumentChunk]] = {}
    anchored: dict[str, list[tuple[DocumentChunk, str]]] = {}
    for at, anchor in pairs:
        key = _branch_key(at)
        if key not in grouped:
            order.append(key)
            grouped[key], anchored[key] = [], []
        grouped[key].append(at)
        anchored[key].append((at, anchor))

    headings = {key: _first_heading(grouped[key]) for key in order}
    shared = Counter(heading for heading in headings.values() if heading)
    by_label: dict[str, list[str]] = {}
    for key in order:
        by_label.setdefault(_match_key(key), []).append(key)

    def first_page(key: str) -> int | None:
        pages = [at.page for at in grouped[key] if at.page is not None]
        return min(pages) if pages else None

    matched: set[str] = set()
    sections: list[dict] = []
    missing: list[str] = []

    def branch_for(entry: dict) -> str | None:
        keys = [key for key in by_label.get(_match_key(entry["label"]), []) if key not in matched]
        if not keys:
            return None
        page = entry.get("printed_page")
        if page is None:
            return keys[0]
        exact = [key for key in keys if first_page(key) == page]
        return exact[0] if exact else None

    def render(key: str, entry: dict | None = None) -> dict:
        passages = anchored[key]
        heading = headings[key]
        if entry is not None:
            title = _toc_title(entry)
        elif heading and shared[heading] == 1:
            title = heading
        else:
            title = _reference_title(key, grouped[key])
        return {
            "key": key,
            "title": title,
            "anchor": passages[0][1],
            "page": first_page(key),
            "count": len(passages),
            "reserved": False,
        }

    for entry in toc:
        if entry["kind"] == "RANGE":
            sections.append(
                {
                    "key": _match_key(entry["label"]),
                    "title": _toc_title(entry),
                    "anchor": slugify(entry["label"]),
                    "page": entry.get("printed_page"),
                    "count": 0,
                    "reserved": True,
                }
            )
            continue
        key = branch_for(entry)
        if key is None:
            missing.append(_toc_title(entry))
            continue
        matched.add(key)
        sections.append(render(key, entry))

    for key in order:
        if key not in matched:
            sections.append(render(key))

    return sections, missing


def saoso_toc() -> list[dict]:
    """The printed TOC from the committed page fixture (`pdftotext -layout`, printed p.2)."""
    raw = (REPO_ROOT / "knowledge/tests/fixtures/saoso_toc.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    return [
        {
            "part": entry.part,
            "kind": entry.kind,
            "label": entry.label,
            "title": entry.title,
            "printed_page": entry.printed_page,
        }
        for entry in parse_toc(raw)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--toc",
        action="store_true",
        help="apply SAOSO's printed TOC from the committed fixture (pre-Task-1 behaviour)",
    )
    args = parser.parse_args()

    documents = list(StandardDocument.objects.order_by("id"))
    if not documents:
        print("No corpus ingested. See the module docstring for the ingest command.")
        return 1

    ambiguous_total = 0
    for document in documents:
        # `getattr`: this probe is useful *before* Task 1 adds the field, and the plan says to run
        # it before Task 1. Once the field exists this is an ordinary attribute read.
        stored = list(getattr(document, "toc", None) or [])
        if args.toc and document.section_scheme == "saoso":
            stored = saoso_toc()
        sections, missing = build(document, stored)
        passages = sum(row["count"] for row in sections)
        print(f"\n{'-' * 88}\n{document.title}\n  [{document.section_scheme}]  {document.source_file}")
        print(
            f"  rows={len(sections)}  passages={passages}/{document.chunk_count}"
            f"  toc={'stored' if stored else 'none'}  missing={len(missing)}"
        )
        for row in sections:
            mark = "  (reserved)" if row["reserved"] else ""
            print(f"    {row['count']:>4} p{str(row['page']):>4}  {row['title'][:62]}{mark}")
        if missing:
            print("  not in the corpus:")
            for title in missing:
                print(f"    - {title}")

        anchors = [anchor for _chunk, anchor in unique_anchors(reading_chunks(document))]
        duplicates = {anchor: n for anchor, n in Counter(anchors).items() if n > 1}
        ambiguous_total += sum(n - 1 for n in duplicates.values())

    total = DocumentChunk.objects.count()
    print(f"\n{'=' * 88}")
    print(f"passages={total}  ambiguous anchors={ambiguous_total}")
    print(
        "  0 is the answer CONCORDANCE_PLAN.md Task 4 targets; today's committed reader produces"
        "\n  57 with its order-derived suffix. If this prints 0, the plan's algorithm is sound."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
