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

**`--continue` is the other way a table's structure enters this repository**, and it is a review
rather than a reading (`INGESTION_ENGINE_S5_PLAN.md` §4). Some pages were never sent to an arm, and
their rows were reviewed from the paper by the product owner instead. Those rows are promoted into a
proposal **as locators**: the emitter still verifies every cell against the page and refuses the ones
that are not there, so the promotion cannot author a value. The entry it writes names the review it
came from (`continued_from`), because the file's banner describes the arm that read the *other* pages
and a banner that claimed both would be false.
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

#: The review a continued table's rows came from, written into its entry so the file cannot claim an
#: arm read them. `knowledge/tables.py` is where the review was stored until S5-b promoted it.
CONTINUED_FROM = "knowledge/tables.py::APPENDIX_2_ROWS (the owner's review, 2026-10-21)"


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


def reviewed_tables(doc_key: str, offset: int = 0) -> list[dict]:
    """The reviewed rows still held in Python, as proposal entries — the S5-b continuation act.

    In:  `doc_key` — the corpus key whose tables are still `knowledge.tables.TABLE_ROWS`; `offset` —
         the PDF's page offset (printed page + offset = PDF page; SAOSO prints `pdf - 1`, so 1).
    Out: one `structure.json` entry per reviewed table, in document order. Each carries its cells as
         **locators** — the reviewed spelling, whitespace-normalised — plus `continued_from`, the
         review's name. No `columns`: those are reviewed wording, and the structure file does not
         pretend an arm supplied them.
    Fails: `SystemExit` when the document has no reviewed Python rows; a continuation of nothing
         would read as a review of nothing.

    **Why this still exists when nothing is left to continue.** It performed S5-b's act — Appendix
    2's thirty rows, the owner's 2026-10-21 review, promoted to locators — and `knowledge/tables.py`
    holds no rows any more because that act removed the second storage. It stays for the same reason
    the act is recorded in the proposal: the capability (a person's reading becomes verification
    rather than authorship) is what the next unreviewed table needs, and a tool that was deleted
    with its first input is a capability nobody can find.
    """
    try:
        from knowledge.tables import TABLE_ROWS
    except ImportError:  # pragma: no cover - the import is the message
        TABLE_ROWS = {}

    out: list[dict] = []
    for _ref, rows in TABLE_ROWS.items():
        if not rows:
            continue
        pages = sorted({row.page for row in rows})
        out.append(
            {
                "pdf_pages": [page + offset for page in pages],
                "rows": [
                    {
                        "cells": [
                            " ".join(row.substance.split()),
                            " ".join(row.condition.split()),
                        ]
                    }
                    for row in rows
                ],
                "extraction": "table",
                "continued_from": CONTINUED_FROM,
            }
        )
    if not out:
        raise SystemExit(
            f"{doc_key!r} has no reviewed rows held in Python, so there is nothing to continue. "
            "A continued proposal promotes rows a person already read; write one with an arm "
            "response (`--response`) instead."
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", help="A cached extractor response (JSON).")
    parser.add_argument("--structure", default=DEFAULT_STRUCTURE, help="The arm, as a reviewer names it.")
    parser.add_argument(
        "--processor", default="", help="`<processor-id>@<model-version>`."
    )
    parser.add_argument("--project", default="", help="Document AI project, when the arm has one.")
    parser.add_argument("--doc", help="The corpus key this response belongs to.")
    parser.add_argument("--shape", help="An S0 shape key: supplies --doc, --pages and the mode.")
    parser.add_argument("--pdf", help="The PDF the response was produced from (default: --doc's).")
    parser.add_argument("--pages", help="The PDF pages that were sent, e.g. `4,5`.")
    parser.add_argument("--extraction", help="The pass the cells will be judged against.")
    parser.add_argument("--captured", help="The date the arm ran (default: the cache file's date).")
    parser.add_argument("--json", required=True, help="Where to write the structure JSON.")
    parser.add_argument(
        "--append",
        action="store_true",
        help=(
            "Merge this response's tables into an existing proposal instead of overwriting it. "
            "One arm response covers the pages it was sent, and a document's appendix is not one "
            "page, so a document's structure is assembled from several — one file, one banner."
        ),
    )
    parser.add_argument(
        "--continue",
        dest="continue_rows",
        action="store_true",
        help=(
            "Append the rows a person already reviewed (still held in `knowledge.tables`) to an "
            "existing proposal, as locators the emitter must find on the page. S5-b."
        ),
    )
    parser.add_argument(
        "--pdf-offset",
        type=int,
        default=0,
        help=(
            "With `--continue`: printed page + this = PDF page (SAOSO prints `pdf - 1`, so pass 1). "
            "A wrong offset is refused by the emitter, which cannot find a cell on the wrong page."
        ),
    )
    args = parser.parse_args(argv)

    if args.continue_rows:
        return _continue(args)
    if not args.response:
        raise SystemExit(
            "--response is required: it is the cached arm reading this proposal records. "
            "(`--continue` is the other way, for rows a person reviewed instead.)"
        )
    if not args.processor:
        raise SystemExit(
            "--processor is required: a proposal whose arm is unknown is a structure nobody can "
            "re-derive."
        )

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
    if args.append and out.exists():
        try:
            payload = _merged(out, payload)
        except ProposalError as error:
            print(error, file=sys.stderr)
            return 2
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="")
    print(
        f"{out.as_posix()}: {len(payload['tables'])} table(s) from {response_path.name} "
        f"({args.structure}, {extraction} characters)"
    )
    return 0


def _continue(args) -> int:
    """Append reviewed rows to the proposal they complete, or refuse and say why."""
    from knowledge.extraction import sha256_of

    if not args.doc:
        raise SystemExit("--continue needs --doc: the rows it promotes belong to one document's table")
    out = Path(args.json)
    if not out.exists():
        raise SystemExit(
            f"{out.as_posix()}: no proposal to continue. A continuation completes a proposal an arm "
            "produced — the banner in that file describes it, and this act may not invent one."
        )
    pdf_path = pdf_path_for(args.doc, args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"no such PDF: {pdf_path}")
    existing = json.loads(out.read_text(encoding="utf-8"))
    if existing.get("doc_key") != args.doc:
        raise SystemExit(
            f"{out.name} describes {existing.get('doc_key')!r}, not {args.doc!r}. One file is one "
            "document."
        )
    if existing.get("sha256") != sha256_of(pdf_path):
        raise SystemExit(
            f"{out.name} describes different bytes than {pdf_path.name}. A reprint is a new "
            "document and its tables have not been reviewed."
        )
    try:
        merged = _merge_tables(existing, reviewed_tables(args.doc, args.pdf_offset), out.name)
    except ProposalError as error:
        print(error, file=sys.stderr)
        return 2
    merged["captured"] = args.captured or datetime.date.today().isoformat()
    out.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline=""
    )
    added = len(merged["tables"]) - len(existing.get("tables", []))
    print(
        f"{out.as_posix()}: {added} continued table(s) appended from {CONTINUED_FROM} — "
        "every cell is a locator the emitter must find on the page"
    )
    return 0


def _merge_tables(existing: dict, tables: list[dict], name: str) -> dict:
    """The existing proposal with `tables` appended, or a refusal naming the pages that clash.

    **Two structures for one page is two answers to where its rows are**, so a clash is refused here
    rather than resolved by order: the emitter would write the first one twice and the second would
    be a review nobody sees.
    """
    existing_pages = {
        page for table in existing.get("tables", []) for page in table.get("pdf_pages", [])
    }
    clashes = sorted(
        page
        for table in tables
        for page in table.get("pdf_pages", [])
        if page in existing_pages
    )
    if clashes:
        raise ProposalError(
            f"{name}: pages {clashes} already have a table. Two structures for one page is two "
            "answers to where its rows are, and the emitter would write the first one twice."
        )
    merged = dict(existing)
    merged["tables"] = list(existing.get("tables", [])) + list(tables)
    return merged


def _merged(out: Path, payload: dict) -> dict:
    """In: an existing proposal and a new one. Out: the two merged, or a refusal by name.

    **The banner may not describe two arms at once.** A merged file whose `structure`, `processor`,
    `sha256` or `project` disagree would say the whole document was read by one arm when half of it
    was read by another — and the emitter trusts the banner when it decides which characters to
    slice. Only `tables` grows, and `reduced_from` names every response that contributed.
    """
    existing = json.loads(out.read_text(encoding="utf-8"))
    for field in ("sha256", "structure", "processor", "project"):
        if existing.get(field) != payload.get(field):
            raise ProposalError(
                f"{out.name}: `{field}` is {existing.get(field)!r} and this response's is "
                f"{payload.get(field)!r}. A proposal is one document read by one arm; two banners "
                "in one file would say the whole structure came from either."
            )
    merged = _merge_tables(existing, payload["tables"], out.name)
    reduced = [existing.get("reduced_from", "")]
    if payload.get("reduced_from"):
        reduced.append(payload["reduced_from"])
    merged["reduced_from"] = ", ".join(item for item in reduced if item)
    merged["captured"] = payload.get("captured") or existing.get("captured", "")
    return merged


if __name__ == "__main__":
    raise SystemExit(main())
