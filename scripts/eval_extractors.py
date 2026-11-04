#!/usr/bin/env python
"""D80 S2 — run a structure extractor over the eight shape pages and score it.

This is an **evaluation instrument, not a pipeline step**. It runs once, on a machine that has the
extractor, and the thing that enters the repo is its output: the results table in
`INGESTION_ENGINE_PRD.md` and the JSON this writes. The gate must never need an extractor
(requirement 10), which is why nothing here is imported by the test suite and why `docling` is
imported lazily inside `convert()`.

    python scripts/eval_extractors.py --json _scratch/docling/scores.json
    python scripts/eval_extractors.py --shape numeric_row,headerless_values --verbose

What it does, per shape (`knowledge/tests/shape_fixtures.py`):

1. converts only the pages that shape is printed on (`page_range`), from the committed PDF, whose
   sha256 is checked by `page_fixtures.entry`;
2. picks the table on those pages whose cells best overlap the shape's anchors — a heuristic, printed
   so a human can audit the choice rather than trust it;
3. maps the extractor's table onto `TableRead` (our side of the contract) and scores it with
   `mismatches()`, which is S0's own instrument and S4's `check_table` consumer;
4. prints one row per shape and writes the JSON.

Three mapping decisions are recorded because they are judgements, not facts:

* **Header rows, scored two ways.** A row whose cells Docling marks as column headers becomes
  `TableRead.columns`, in column order. Measured 2026-11-03 on the OPP's fee table: Docling produced a
  perfect 7x3 grid with the header row first and **marked no cell as a header**, so the strict read has
  no column labels at all. That is a real finding about requirement 2, and it is also not the whole
  story: "row 0 is the header" is a one-line convention a caller could apply. So every shape is scored
  **twice** — `as_extracted` and `first_row_as_header` — and both columns are published. A tool that
  needs a convention to pass is a different finding from a tool that cannot pass.
* **Spanning cells are replicated** across the rows and columns they cover, because that is how a
  merged cell reads. The alternative (text only in the start cell, blanks beside it) would score an
  extractor as "empty" for a cell it actually got right.
* **Dividers are always empty.** No general extractor returns a "label printed between two rows" as
  structure; the `qualifier` shape exists to measure that gap, so it is expected to fail here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = Path(__file__).resolve().parents[1]

from knowledge.tests import page_fixtures  # noqa: E402
from knowledge.tests.shape_fixtures import (  # noqa: E402
    BY_KEY,
    SHAPES,
    TableRead,
    flat,
    mismatches,
)


def documents_for(case) -> tuple[str, str]:
    """The PDF to convert, and the doc key whose manifest record proves it is the right one."""
    record = page_fixtures.entry(case.doc_key)
    return str(REPO_ROOT / record["source"]), case.doc_key


def convert(pdf: str, pages: tuple[int, ...]):
    """Convert just `pages` with Docling's default pipeline, recording how long it took.

    In: `pdf` — the committed PDF; `pages` — 1-based PDF pages the shape is printed on.
    Out: `(document, seconds)`. Fails loudly if docling is absent: this script never degrades into
    reporting an empty document as a score.
    """
    try:
        import docling.document_converter  # noqa: F401
    except ImportError as error:  # pragma: no cover - the evaluation machine has it
        raise SystemExit(
            "docling is not installed in this interpreter. It is deliberately not a dependency of "
            "the project: install it in a throwaway venv and run this script with that venv's "
            f"python. ({error})"
        ) from None
    started = time.perf_counter()
    result = _converter().convert(pdf, page_range=(min(pages), max(pages)))
    return result.document, time.perf_counter() - started


#: One converter for the whole run. Measured 2026-11-03: building a `DocumentConverter` per shape put
#: the model load (a few seconds) inside every timing, so the first run's "seconds" measured startup
#: more than extraction. A pipeline loads once, so the evaluation must too.
_CONVERTER = None


def _extractor_name() -> str:
    """The tool and the exact version: a score without its version is not evidence."""
    from importlib.metadata import version

    try:
        return f"docling {version('docling')}"
    except Exception:  # pragma: no cover - only on a broken install
        return "docling (version unknown)"


def _converter():
    global _CONVERTER
    if _CONVERTER is None:
        from docling.document_converter import DocumentConverter

        _CONVERTER = DocumentConverter()
    return _CONVERTER


def overlapped_table(document, case):
    """The table on the shape's pages that best matches the shape, and its score.

    The heuristic is deliberate and printed: a wrong table would score the *extractor* for our
    choice, so the runner names what it picked (rows, columns, page) and the caller can see it.
    """
    anchors = [flat(text) for _, text in case.anchors]
    wanted = []
    for cell in case.cells:
        for value in (cell.text, cell.starts, cell.ends, cell.contains):
            if value:
                wanted.append(flat(value))
    best = None
    for table in document.tables:
        pages = {prov.page_no for prov in table.prov}
        if not pages & set(case.pdf_pages):
            continue
        texts = [flat(cell.text) for cell in table.data.table_cells]
        blob = " ".join(texts)
        hits = sum(1 for value in anchors + wanted if value and value in blob)
        if best is None or hits > best[0]:
            best = (hits, table, sorted(pages))
    return (None, []) if best is None else (best[1], best[2])


def as_table_read(table, page: int, *, first_row_is_header: bool = False) -> TableRead:
    """Map a Docling table onto our `TableRead`. See the module docstring for the three decisions.

    Docling's `*_offset_idx` fields are **half-open**: a cell printed as `r0-1 c2-3` occupies row 0,
    column 2. Measured 2026-11-03 — the first version of this function treated the ends as inclusive
    and indexed one past the grid.
    """
    data = table.data
    header_rows = sorted(
        {cell.start_row_offset_idx for cell in data.table_cells if cell.column_header}
    )
    if not header_rows and first_row_is_header and data.num_rows > 1:
        header_rows = [0]
    first_body_row = (max(header_rows) + 1) if header_rows else 0

    width = data.num_cols or max([cell.end_col_offset_idx for cell in data.table_cells], default=0)
    height = data.num_rows or max([cell.end_row_offset_idx for cell in data.table_cells], default=0)
    grid = [["" for _ in range(width)] for _ in range(height)]
    for cell in data.table_cells:
        text = flat(cell.text)
        if not text:
            continue
        for row in range(cell.start_row_offset_idx, min(cell.end_row_offset_idx, height)):
            for column in range(cell.start_col_offset_idx, min(cell.end_col_offset_idx, width)):
                if not grid[row][column]:
                    grid[row][column] = text

    columns = tuple(grid[header_rows[-1]]) if header_rows else ()
    body = [tuple(row) for row in grid[first_body_row:]]
    return TableRead(
        columns=columns,
        rows=tuple(body),
        pages=tuple(page for _ in body),
        dividers=(),
    )


def evaluate(case, verbose: bool = False) -> dict:
    """One shape: convert, pick, map, score — twice (see the module docstring).

    Both readings are always present, even when no table was found, so a consumer never has to
    branch on `found` to read a verdict. Rows are kept in the JSON as a **sample of four** with the
    real total alongside: the full grid of a 20-row table is a megabyte of text that the verdict and
    the mismatch list already summarise, and the command that regenerates it is in this docstring.
    """
    pdf, doc_key = documents_for(case)
    document, seconds = convert(pdf, case.pdf_pages)

    # `TableRead.pages` is the page the *document prints* (D42), and S0's expectations are printed
    # pages: SAOSO pdf 86 is printed 85. The case carries both lists in parallel, so the mapping is
    # read, never inferred from an offset.
    printed_for = dict(zip(case.pdf_pages, case.printed_pages))
    on_pages = [
        {
            "pages": sorted({prov.page_no for prov in other.prov}),
            "rows": other.data.num_rows,
            "cols": other.data.num_cols,
        }
        for other in document.tables
        if {prov.page_no for prov in other.prov} & set(case.pdf_pages)
    ]
    result = {
        "shape": case.key,
        "label": case.shape,
        "doc": doc_key,
        "pdf_pages": list(case.pdf_pages),
        "printed_pages": list(case.printed_pages),
        "seconds": round(seconds, 1),
        "tables_on_pages": on_pages,
    }

    table, pages = overlapped_table(document, case)
    if table is None:
        missing = [
            f"{case.key}: the extractor returned no table on pages {list(case.pdf_pages)} "
            f"({len(on_pages)} table(s) found on those pages)"
        ]
        result.update(
            {
                "found": False,
                "verdict": "no table found on the page",
                "table_pages": [],
                "rows_found": 0,
                "rows_expected": case.row_count,
                "columns_found": 0,
                "columns_expected": len(case.columns),
                "as_extracted": {"verdict": "fail", "mismatches": missing, "columns": [], "rows": [], "rows_total": 0},
                "first_row_as_header": {"verdict": "fail", "mismatches": missing, "columns": [], "rows": [], "rows_total": 0},
            }
        )
        return result

    page = printed_for.get(pages[0] if pages else case.pdf_pages[0], case.printed_pages[0])
    strict = as_table_read(table, page)
    conventional = as_table_read(table, page, first_row_is_header=True)
    strict_found = mismatches(case, strict)
    conventional_found = mismatches(case, conventional)
    if verbose:
        print()
        print(f"--- {case.key}: chose a table on pages {pages}")
        print(f"    columns: {strict.columns}")
        for index, row in enumerate(strict.rows):
            print(f"    row {index}: {row}")
        if conventional.columns != strict.columns:
            print(f"    first-row-as-header columns: {conventional.columns}")

    if not strict_found:
        verdict = "pass"
    elif not conventional_found:
        verdict = "pass (needs header convention)"
    else:
        verdict = "fail"

    def reading(read, found: list[str]) -> dict:
        return {
            "verdict": "pass" if not found else "fail",
            "mismatches": found,
            "columns": list(read.columns),
            "rows": [list(row) for row in read.rows[:4]],
            "rows_total": len(read.rows),
            "rows_sampled": min(4, len(read.rows)),
        }

    result.update(
        {
            "found": True,
            "verdict": verdict,
            "table_pages": pages,
            "rows_found": len(strict.rows),
            "rows_expected": case.row_count,
            "columns_found": len(strict.columns),
            "columns_expected": len(case.columns),
            "as_extracted": reading(strict, strict_found),
            "first_row_as_header": reading(conventional, conventional_found),
        }
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="Write the full result, per shape, to this path.")
    parser.add_argument(
        "--shape", help="Comma-separated shape keys (default: all eight)."
    )
    parser.add_argument("--verbose", action="store_true", help="Print each chosen table.")
    args = parser.parse_args(argv)

    cases = SHAPES
    if args.shape:
        keys = [part.strip() for part in args.shape.split(",") if part.strip()]
        unknown = [key for key in keys if key not in BY_KEY]
        if unknown:
            print(f"unknown shape(s): {', '.join(unknown)}; known: {', '.join(BY_KEY)}", file=sys.stderr)
            return 2
        cases = [BY_KEY[key] for key in keys]

    results = []
    total = time.perf_counter()
    for case in cases:
        result = evaluate(case, verbose=args.verbose)
        results.append(result)
        mark = {"pass": "PASS", "pass (needs header convention)": "PASS*"}.get(
            result["verdict"], "FAIL"
        )
        detail = result["verdict"]
        if result["verdict"] == "fail":
            detail = f"{len(result['first_row_as_header']['mismatches'])} mismatches"
        print(
            f"{mark:5s} {case.key:20s} {result['seconds']:6.1f}s  "
            f"rows {result.get('rows_found', 0)}/{case.row_count} "
            f"cols {result.get('columns_found', 0)}/{len(case.columns)}  {detail}"
        )
    elapsed = time.perf_counter() - total
    passed = sum(1 for result in results if result["verdict"] == "pass")
    strict_pass = sum(
        1 for result in results if result.get("as_extracted", {}).get("verdict") == "pass"
    )
    conventional_pass = sum(
        1 for result in results if result.get("first_row_as_header", {}).get("verdict") == "pass"
    )
    print(
        f"\n{strict_pass}/{len(results)} shapes pass as extracted, "
        f"{conventional_pass}/{len(results)} once row 0 is taken as the header "
        f"· {elapsed:.1f}s total"
    )

    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "instrument": "scripts/eval_extractors.py",
            "extractor": _extractor_name(),
            "python": sys.version.split()[0],
            "checked": (
                f"{len(results)} shapes; {strict_pass} pass as extracted, "
                f"{conventional_pass} pass once row 0 is taken as the header"
            ),
            "results": results,
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
