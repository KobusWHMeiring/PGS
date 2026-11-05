#!/usr/bin/env python
"""Reduce a cached extractor response into the structure a corpus artefact is built from (S3).

The composite D82 settled (`INGESTION_ENGINE_PRD.md` §3.14) puts one arm in charge of *structure*:
Document AI's Layout Parser says where the tables are, how many rows and columns they have and which
printed line belongs to which cell. This script is the build-time act that turns one cached answer
into committed data — `knowledge/proposals/<doc>.structure.json` — so that the generator needs no
credential, no network and no extractor, and so a reviewer can diff the structure in the same commit
as the artefact it produced.

    python scripts/propose_tables.py \\
        --response _scratch/adc/responses/layout16pro__numeric_row.json \\
        --structure documentai-layout-v1.6-pro \\
        --processor 68e47c3bc90cc6ab@pretrained-layout-parser-v1.6-pro-2025-12-01 \\
        --project 803140233794 --shape numeric_row --doc opp \\
        --json knowledge/proposals/opp.structure.json

Three rules, and the third is the one that keeps this honest:

1. **No credential, no network, no rasteriser.** The response is read from disk; the only imports are
   `json` and the shape registry. Requirement 10's rule is that running an extractor is a recorded
   build-time act — this is the record.
2. **The banner travels with the data.** `processor`, `project`, `structure`, `captured` and
   `reduced_from` are written into the JSON, because a proposal whose arm is unknown is a structure
   nobody can re-derive.
3. **It refuses what the block format cannot yet express.** A merged cell (`rowSpan`/`colSpan` > 1)
   and a response with no table are refusals with a name, not an empty file: the emitter's job is to
   verify characters, and it cannot verify a cell boundary the arm did not report.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

#: The arm whose structure the composite adopted, named once so a typo is one line to fix.
DEFAULT_STRUCTURE = "documentai-layout-v1.6-pro"


class ProposalError(ValueError):
    """A response this reducer will not turn into data. Printed by `main`, never swallowed."""


def pages_of_shape(shape_key: str) -> tuple[str, tuple[int, ...], str]:
    """`(doc_key, pdf_pages, declared extraction mode)` for a shape in S0's registry."""
    from knowledge.tests.shape_fixtures import SHAPES

    for case in SHAPES:
        if case.key == shape_key:
            return case.doc_key, case.pdf_pages, case.mode
    known = ", ".join(case.key for case in SHAPES)
    raise SystemExit(f"--shape {shape_key!r} is not one of the eight: {known}")


def table_blocks(document: dict) -> list[tuple[int, dict]]:
    """Every table in a Layout Parser response, with the 1-based index of the page it starts on.

    The index is into the pages that were *sent*, in order — one image or two, per shape — so the
    caller maps it onto real PDF pages. `layout_tables` is the arm's one reader (`eval_documentai`),
    reused rather than re-written: reading this block tree the Form Parser's way scored the Layout
    Parser 0 of 8 (§3.9), and a second reader is a second chance to make that mistake.
    """
    from scripts.eval_documentai import layout_tables

    blocks = (document.get("documentLayout") or {}).get("blocks", []) or []
    found = layout_tables(blocks, tuple(range(1, 1000)))
    return [(page, table) for page, table in found]


def spans(table: dict) -> list[int]:
    """The cells of one table that cover more than one slot, as `(row, column)` indices."""
    found = []
    for kind in ("headerRows", "bodyRows"):
        for row_index, row in enumerate(table.get(kind, []) or []):
            for column, cell in enumerate(row.get("cells", []) or []):
                down = int(cell.get("rowSpan", 1) or 1)
                across = int(cell.get("colSpan", 1) or 1)
                if down > 1 or across > 1:
                    found.append((kind, row_index, column, down, across))
    return found


def structure_from(response_path: Path, doc_key: str, pages: tuple[int, ...]) -> list[dict]:
    """The proposal's tables: the arm's grid, with the pages the shape says they were read from.

    In:  `response_path` — a cached Layout Parser response; `doc_key` — the document it describes;
         `pages` — the PDF pages that were sent, in order (the shape's `pdf_pages`).
    Out: one dict per table, `{"pdf_pages": [...], "columns": [...], "rows": [{"cells": [...]}]}`.
    Fails: `ProposalError` when the response holds no table or a merged cell — both are structures
         the block format cannot express yet, and an empty proposal would hide that.
    """
    from scripts.eval_documentai import cell_text, grid

    document = json.loads(response_path.read_text(encoding="utf-8"))
    found = table_blocks(document)
    if not found:
        raise ProposalError(
            f"{response_path.name}: the arm returned no table on pages {list(pages)}. Nothing was "
            "written — an empty proposal would say 'this page has no table' in the same file as "
            "'the emitter verified one', and the two are different facts."
        )
    tables = []
    for index, (page, table) in enumerate(found, 1):
        merged = spans(table)
        if merged:
            kind, row_index, column, down, across = merged[0]
            raise ProposalError(
                f"{response_path.name} table {index}: {kind}[{row_index}] cell {column} covers "
                f"{down}x{across} slots. A merged cell is a declaration the block format has no "
                "field for yet (S5 writes it with the paper in front of it); refusing rather than "
                "flattening it, because a flattened box is a cell the emitter cannot verify."
            )
        headers = table.get("headerRows", []) or []
        body = table.get("bodyRows", []) or []
        width = max((len(row.get("cells", []) or []) for row in headers + body), default=0)
        rows = grid(headers + body, document, width)
        if not rows:
            continue
        columns = rows[0]
        pdf_page = pages[page - 1] if 1 <= page <= len(pages) else pages[0]
        tables.append(
            {
                "pdf_pages": [pdf_page],
                "columns": columns,
                "rows": [{"cells": row} for row in rows[1:]],
                # Kept for the reviewer: the arm's own flat read of each cell, so a disagreement
                # with the page is visible in the diff rather than only in the emitter's refusal.
                "arm_text": [[cell_text(document, cell) for cell in row.get("cells", []) or []]
                             for row in headers + body],
            }
        )
    if not tables:
        raise ProposalError(f"{response_path.name}: every table in the response had no cells")
    return tables


def pdf_path_for(doc_key: str, override: str | None) -> Path:
    """The PDF the response was produced from: `--pdf`, or the document's recorded source.

    A document the registry does not know has no recorded source, so it must pass `--pdf` — which
    is the retarget path, and the reason this lookup is not a constant table of its own.
    """
    if override:
        return Path(override)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")
    import django

    django.setup()
    from knowledge.ingest import CORPUS_DOCUMENTS

    descriptor = CORPUS_DOCUMENTS.get(doc_key)
    if descriptor is None:
        raise SystemExit(
            f"{doc_key!r} is not a corpus document, so there is no PDF on record for it. "
            "Pass --pdf: that is the whole of ingesting a new standard (S3)."
        )
    return REPO_ROOT / descriptor["source"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", required=True, help="A cached extractor response (JSON).")
    parser.add_argument("--structure", default=DEFAULT_STRUCTURE, help="The arm, as a reviewer names it.")
    parser.add_argument("--processor", required=True, help="`<processor-id>@<model-version>`.")
    parser.add_argument("--project", default="", help="Document AI project, when the arm has one.")
    parser.add_argument("--doc", help="The corpus key this response belongs to.")
    parser.add_argument("--shape", help="An S0 shape key: supplies --doc, --pages and the mode.")
    parser.add_argument("--pdf", help="The PDF the response was produced from (default: --doc's).")
    parser.add_argument("--pages", help="The PDF pages that were sent, e.g. `4,5`.")
    parser.add_argument("--extraction", help="The pass the cells will be judged against.")
    parser.add_argument("--captured", help="The date the arm ran (default: the cache file's date).")
    parser.add_argument("--json", required=True, help="Where to write the structure JSON.")
    args = parser.parse_args(argv)

    if args.shape:
        doc_key, shape_pages, shape_mode = pages_of_shape(args.shape)
    else:
        doc_key, shape_pages, shape_mode = None, (), None
    doc_key = args.doc or doc_key
    if not doc_key:
        raise SystemExit("name the document: --doc, or --shape for one of the eight")
    if args.pages:
        pages = tuple(int(part) for part in args.pages.replace(" ", "").split(",") if part)
        if not pages:
            raise SystemExit("--pages names no pages")
    else:
        pages = shape_pages
    if not pages:
        raise SystemExit("name the pages the response covers: --pages, or --shape")
    extraction = args.extraction or shape_mode
    if not extraction:
        raise SystemExit(
            "name the extraction the cells will be judged against: --extraction, or --shape for "
            "the pass the shape declares"
        )

    from knowledge.corpus_tables import EXTRACTION_MODES
    from knowledge.extraction import sha256_of

    if extraction not in EXTRACTION_MODES:
        print(f"--extraction {extraction!r} is not one of {list(EXTRACTION_MODES)}", file=sys.stderr)
        return 2

    response_path = Path(args.response)
    if not response_path.exists():
        raise SystemExit(f"no such response: {response_path}")
    pdf_path = pdf_path_for(doc_key, args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"no such PDF: {pdf_path}")

    captured = args.captured or datetime.date.fromtimestamp(
        response_path.stat().st_mtime
    ).isoformat()
    try:
        tables = structure_from(response_path, doc_key, pages)
    except ProposalError as error:
        print(error, file=sys.stderr)
        return 2
    for table in tables:
        table["extraction"] = extraction
    payload = {
        "doc_key": doc_key,
        "sha256": sha256_of(pdf_path),
        "structure": args.structure,
        "processor": args.processor,
        "project": args.project,
        "captured": captured,
        "shape": args.shape or "",
        "reduced_from": response_path.as_posix().replace(REPO_ROOT.as_posix() + "/", ""),
        "tables": tables,
    }
    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="")
    print(
        f"{out.as_posix()}: {len(tables)} table(s) from {response_path.name} "
        f"({args.structure}, {extraction} characters)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
