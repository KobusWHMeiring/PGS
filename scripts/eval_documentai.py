#!/usr/bin/env python
"""D80 S2c — Document AI scored against the eight shapes, by the same instrument as the other two arms.

    gcloud auth application-default login          # ADC, on the owner's machine. No key file.
    python scripts/eval_documentai.py \
        --processor form=3da842fc37f31e08 --processor layout=68e47c3bc90cc6ab \
        --project 803140233794 --location us --json _scratch/adc/scores.json

This is the **extractive** class: the service reads the page and returns text with boxes. It does not
*write* text it did not see — but measured 2026-11-04 it does **misread**: on Appendix 7 it returned
`No more than 1~g/|` where the paper prints `1 g/l`. So "extractive" is not the same as "the characters
are ours": this arm is scored on its own reading, and every cell is *also* checked against the committed
page pass. A cell that does not resolve there is `unverified_in_our_pass`, and it is the reason
requirement 3 exists rather than an argument that it can be skipped.

Three mapping decisions, recorded because they are judgements:

* **Cell text comes from `document.text` via each cell's text anchor.** That is the service's own
  reading, so this arm is scored as delivered — the honest thing to compare against Docling's cells.
  Every cell is *also* checked against the committed page pass (`scripts/table_reads.resolve`) and any
  cell that does not resolve there is reported as `unverified_in_our_pass`. A low count means the two
  readings of the same paper agree; a high one means the corpus artefact and this arm disagree about
  characters, which is a finding about the artefact.
* **A merged cell is filed under the first cell it covers and the cells it covers are `""`** — the
  fixtures' convention (`empty_cells` notes: 'the merged cell is one cell and is filed under Step 1').
  Docling's instrument replicates a span instead; the arms are compared per shape, never summed.
* **A table that continues on the next page is joined, and the join is reported.** Document AI returns
  one table per page, so a row that crosses a page break arrives as two. Joining them in page order is
  what the paper does; `joined_pages` says it happened, so the reader can discount it if they disagree.

Nothing here is imported by the suite, and `pypdfium2` / `google.auth` are imported lazily: the gate
needs no extractor and no credential (requirement 10).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
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
from scripts.table_reads import (  # noqa: E402
    drop_row_number_gutter,
    page_runs,
    resolve,
)

SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def token() -> tuple[str, str | None]:
    """A bearer token from Application Default Credentials, and its quota project.

    Never a key file in the repo. A *user* credential must name the project to bill (the
    `x-goog-user-project` header) or Google refuses the call; a service-account credential carries it
    itself, so the header is only sent when the credential has one.
    """
    try:
        import google.auth  # noqa: F401
        from google.auth.transport.requests import Request
    except ImportError:  # pragma: no cover - the evaluation machine has it
        raise SystemExit(
            "google-auth is not installed in this interpreter. It is deliberately not a dependency "
            "of the project: install it in a throwaway venv and run this script with that venv's "
            "python, or use the ADC token from `gcloud auth print-access-token`."
        ) from None
    import google.auth

    credentials, _ = google.auth.default(scopes=[SCOPE])
    credentials.refresh(Request())
    return credentials.token, getattr(credentials, "quota_project_id", None)


def build_pdf(case) -> bytes:
    """One PDF holding exactly the shape's pages, so we are billed for the shape and nothing else."""
    try:
        import pypdfium2 as pdfium  # noqa: F401
    except ImportError:  # pragma: no cover
        raise SystemExit(
            "pypdfium2 is not installed in this interpreter. Install it in a throwaway venv."
        ) from None
    import pypdfium2 as pdfium

    record = page_fixtures.entry(case.doc_key)
    source = pdfium.PdfDocument(str(REPO_ROOT / record["source"]))
    chosen = pdfium.PdfDocument.new()
    chosen.import_pages(source, pages=[page - 1 for page in case.pdf_pages])
    import io

    stream = io.BytesIO()
    chosen.save(stream)
    return stream.getvalue()


def process(
    pdf: bytes,
    *,
    project: str,
    location: str,
    processor: str,
    version: str | None = None,
    timeout: int = 300,
) -> dict:
    """One `:process` call. Returns the `document` object, plus how long it took.

    `version` pins a processor version. It is not optional in spirit: the default for a new processor
    is the *stable* version, and measured 2026-11-04 that was `pretrained-form-parser-v2.0-2022-11-10`
    (four years old) and `pretrained-layout-parser-v1.0-2024-06-03`. A score without its version is
    not evidence, so the runner records it and can pin it.
    """
    suffix = f"/processorVersions/{version}" if version else ""
    url = (
        f"https://{location}-documentai.googleapis.com/v1/projects/{project}"
        f"/locations/{location}/processors/{processor}{suffix}:process"
    )
    body = json.dumps(
        {
            "rawDocument": {
                "content": base64.b64encode(pdf).decode(),
                "mimeType": "application/pdf",
            },
            # The online endpoint caps at 15 pages and returns synchronously; ours are 1-2 pages.
            "skipHumanReview": True,
        }
    ).encode()
    bearer, quota = token()
    headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"}
    if quota:
        headers["x-goog-user-project"] = quota
    request = urllib.request.Request(url, data=body, headers=headers)
    started = time.perf_counter()
    # Retried, because measured 2026-11-04 a long run died mid-flight with
    # `WinError 10053 — an established connection was aborted by the software in your host machine`
    # after 10 of 16 calls. A dropped socket is not a result, and re-running the whole panel to
    # recover two shapes wastes money and the reader's patience.
    payload = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
            break
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:600]
            if error.code < 500 or attempt == 2:
                raise SystemExit(f"{processor}: HTTP {error.code} — {detail}") from None
            time.sleep(2 + 4 * attempt)
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == 2:
                raise SystemExit(f"{processor}: connection failed 3 times — {error}") from None
            time.sleep(2 + 4 * attempt)
    document = (payload or {}).get("document") or {}
    document["_seconds"] = round(time.perf_counter() - started, 1)
    return document


def cell_text(document: dict, cell: dict) -> str:
    """The cell's own characters. Never retyped, but the two processors deliver them differently.

    Measured 2026-11-04: the Form Parser anchors each cell into `document.text`
    (`layout.textAnchor.textSegments`); the Layout Parser nests a `textBlock` per cell instead and
    returns no `document.text` at all. Reading only the first shape scored the Layout Parser **0 of 8
    with "no table found" on every page** — an instrument bug, not a tool result, and the reason this
    function handles both.
    """
    text = document.get("text", "")
    parts = []
    for segment in (cell.get("layout", {}).get("textAnchor", {}) or {}).get("textSegments", []) or []:
        start, end = int(segment.get("startIndex", 0)), int(segment.get("endIndex", 0))
        parts.append(text[start:end])
    if not parts:
        for block in cell.get("blocks", []) or []:
            nested = (block.get("textBlock") or {}).get("text")
            if nested:
                parts.append(nested)
    return flat(" ".join(parts))


def grid(rows: list[dict], document: dict, width: int) -> list[list[str]]:
    """Rows -> a rectangle. A merged cell sits in its first slot; the slots it covers are empty."""
    out: list[list[str]] = []
    for row in rows:
        out.append(["" for _ in range(width)])
    covered = [[False] * width for _ in range(len(rows))]
    for index, row in enumerate(rows):
        column = 0
        for cell in row.get("cells", []):
            while column < width and covered[index][column]:
                column += 1
            if column >= width:
                break
            value = cell_text(document, cell)
            down = max(1, int(cell.get("rowSpan", 1) or 1))
            across = max(1, int(cell.get("colSpan", 1) or 1))
            for extra_row in range(down):
                for extra_column in range(across):
                    r, c = index + extra_row, column + extra_column
                    if r < len(rows) and c < width:
                        covered[r][c] = True
                        if (extra_row, extra_column) != (0, 0):
                            out[r][c] = ""
            out[index][column] = value
            column += across
    return out


def _layout_tables(blocks: list, printed_pages: tuple[int, ...]) -> list[dict]:
    """Tables inside the Layout Parser's block hierarchy, which nests them under their heading."""
    found = []
    for block in blocks:
        if "tableBlock" in block:
            table = block["tableBlock"]
            span = block.get("pageSpan") or {}
            index = max(0, int(span.get("pageStart", 1)) - 1)
            found.append((printed_pages[index] if index < len(printed_pages) else index + 1, table))
        for kind in ("textBlock", "listBlock"):
            nested = (block.get(kind) or {}).get("blocks")
            if nested:
                found.extend(_layout_tables(nested, printed_pages))
    return found


def tables_from(document: dict, printed_pages: tuple[int, ...]) -> list[dict]:
    """Every table in the response, with its page, columns and rows already rectangular.

    Two shapes, because the two processors disagree about where a table lives: the Form Parser puts
    `pages[].tables[]` and anchors text into `document.text`; the Layout Parser returns a block tree
    with `tableBlock` nested under the heading it belongs to, and no `document.text`.
    """
    found = []
    if document.get("documentLayout"):
        for printed, table in _layout_tables(
            (document["documentLayout"] or {}).get("blocks", []), printed_pages
        ):
            built = _rectangular(table, document)
            if built:
                found.append({"page": printed, **built})
    for page_index, page in enumerate(document.get("pages", [])):
        printed = printed_pages[page_index] if page_index < len(printed_pages) else page_index + 1
        for table in page.get("tables", []) or []:
            built = _rectangular(table, document)
            if built:
                found.append({"page": printed, **built})
    return found


def _rectangular(table: dict, document: dict) -> dict | None:
    """One table as columns + a rectangle of rows, or None when it carries no cells."""
    header_rows = table.get("headerRows", []) or []
    body_rows = table.get("bodyRows", []) or []
    width = 0
    for row in header_rows + body_rows:
        span = sum(max(1, int(cell.get("colSpan", 1) or 1)) for cell in row.get("cells", []))
        width = max(width, span)
    if not width:
        return None
    headers = grid(header_rows, document, width) if header_rows else []
    return {"columns": tuple(headers[-1]) if headers else (), "rows": grid(body_rows, document, width)}


def overlaps(case, table: dict) -> int:
    """How many of the shape's anchors and expected cells this table's text contains."""
    blob = flat(" ".join(table["columns"]) + " " + " ".join(" ".join(row) for row in table["rows"]))
    wanted = [flat(text) for _, text in case.anchors]
    for cell in case.cells:
        for value in (cell.text, cell.starts, cell.ends, cell.contains):
            if value:
                wanted.append(flat(value))
    return sum(1 for value in wanted if value and value in blob)


def joined(case, tables: list[dict]) -> tuple[list[dict], bool]:
    """Tables that continue across the shape's pages, in page order, when they share a width."""
    if len(case.pdf_pages) < 2 or len(tables) < 2:
        return tables, False
    by_page = sorted(tables, key=lambda table: table["page"])
    width = len(by_page[0]["rows"][0]) if by_page[0]["rows"] else 0
    if not width or any(len(row) != width for table in by_page for row in table["rows"]):
        return tables, False
    return (
        [
            {
                "page": by_page[0]["page"],
                "columns": by_page[0]["columns"],
                "rows": [row for table in by_page for row in table["rows"]],
                "pages": [table["page"] for table in by_page for row in table["rows"]],
            }
        ],
        True,
    )


def evaluate(
    case,
    name: str,
    processor: str,
    *,
    project: str,
    location: str,
    version: str | None = None,
    verbose: bool = False,
    cache: Path | None = None,
) -> dict:
    pdf = build_pdf(case)
    stored = None
    if cache is not None:
        stored = cache / f"{name}__{case.key}.json"
        if stored.exists():
            document = json.loads(stored.read_text(encoding="utf-8"))
            document["_seconds"] = document.get("_seconds", 0.0)
    if cache is None or stored is None or not stored.exists():
        document = process(
            pdf, project=project, location=location, processor=processor, version=version
        )
        if cache is not None:
            cache.mkdir(parents=True, exist_ok=True)
            stored.write_text(json.dumps(document, indent=1), encoding="utf-8")
    printed = dict(zip(case.pdf_pages, case.printed_pages))
    printed_pages = tuple(printed[page] for page in case.pdf_pages)
    tables = tables_from(document, printed_pages)
    result = {
        "shape": case.key,
        "label": case.shape,
        "doc": case.doc_key,
        "model": f"documentai {name}",
        "processor": processor,
        "processor_version": version or "(default)",
        "location": location,
        "pdf_pages": list(case.pdf_pages),
        "printed_pages": list(case.printed_pages),
        "seconds": document.get("_seconds", 0),
        "tables_on_pages": [{"page": t["page"], "rows": len(t["rows"]), "cols": len(t["rows"][0]) if t["rows"] else 0} for t in tables],
        "text_chars": len(document.get("text", "")),
    }
    if not tables:
        missing = [f"{case.key}: the processor returned no table on pages {list(case.pdf_pages)}"]
        result.update(
            {
                "found": False,
                "verdict": "no table found on the page",
                "rows_found": 0,
                "rows_expected": case.row_count,
                "columns_found": 0,
                "columns_expected": len(case.columns),
                "as_extracted": {"verdict": "fail", "mismatches": missing, "columns": [], "rows": [], "rows_total": 0},
                "with_row_number_gutter": {"identical_to_as_extracted": True},
                "joined_pages": False,
            }
        )
        return result

    chosen = max(tables, key=lambda table: overlaps(case, table))
    candidates, did_join = joined(case, [table for table in tables if overlaps(case, table) > 0])
    if did_join:
        chosen = candidates[0]
    page = chosen.get("pages", [chosen["page"]] * len(chosen["rows"]))
    read = TableRead(
        columns=tuple(flat(column) for column in chosen["columns"]),
        rows=tuple(tuple(row) for row in chosen["rows"]),
        pages=tuple(page),
        dividers=(),
    )
    guttered, dropped = drop_row_number_gutter(read)
    strict = mismatches(case, read)
    guttered_found = mismatches(case, guttered) if dropped else strict

    # Does our own committed pass agree with this reading? A cell that does not resolve there is not a
    # failure of the arm — it is a disagreement between two readings of the same paper, and it matters
    # because a quote in the corpus is checked against the artefact, not against Document AI.
    runs = page_runs(case)
    unverified = []
    for index, row in enumerate(read.rows):
        for column, value in enumerate(row):
            if not value:
                continue
            found = resolve(value, runs, {})
            if not found["ok"]:
                unverified.append({"row": index, "column": column, "cell": value[:120]})

    if verbose:
        print(f"\n--- {case.key}: {name} on page(s) {chosen.get('pages') or chosen['page']}")
        print(f"    columns: {read.columns}")
        for index, row in enumerate(read.rows):
            print(f"    row {index}: {row}")

    if not strict:
        verdict = "pass"
    elif not guttered_found:
        verdict = "pass (needs row-number gutter)"
    else:
        verdict = "fail"

    def reading(one: TableRead, found: list[str]) -> dict:
        return {
            "verdict": "pass" if not found else "fail",
            "mismatches": found,
            "columns": [column[:200] for column in one.columns],
            "rows": [[cell[:200] for cell in row] for row in one.rows[:4]],
            "rows_total": len(one.rows),
        }

    result.update(
        {
            "found": True,
            "verdict": verdict,
            "rows_found": len(read.rows),
            "rows_expected": case.row_count,
            "columns_found": len(read.columns),
            "columns_expected": len(case.columns),
            "as_extracted": reading(read, strict),
            "with_row_number_gutter": (
                {"identical_to_as_extracted": True} if not dropped else reading(guttered, guttered_found)
            ),
            "row_number_gutter_rows": dropped,
            "joined_pages": did_join,
            "unverified_in_our_pass": unverified,
        }
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--processor",
        action="append",
        required=True,
        help="name=processor_id[@version], e.g. form=3da842fc37f31e08@pretrained-form-parser-v2.1-2023-06-26. Repeat for a panel.",
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default="us")
    parser.add_argument("--json", help="Write the full result, per shape and processor, to this path.")
    parser.add_argument("--shape", help="Comma-separated shape keys (default: all eight).")
    parser.add_argument(
        "--cache",
        default=str(REPO_ROOT / "_scratch" / "adc" / "responses"),
        help="Raw responses per (processor, shape); a cached one is never re-asked, so a key fix or "
        "a resolver fix re-scores for free. Pass an empty string to disable.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    cache = Path(args.cache) if args.cache else None

    cases = SHAPES
    if args.shape:
        keys = [part.strip() for part in args.shape.split(",") if part.strip()]
        unknown = [key for key in keys if key not in BY_KEY]
        if unknown:
            print(f"unknown shape(s): {', '.join(unknown)}; known: {', '.join(BY_KEY)}", file=sys.stderr)
            return 2
        cases = [BY_KEY[key] for key in keys]

    processors = []
    for spec in args.processor:
        name, _, rest = spec.partition("=")
        processor, _, version = rest.partition("@")
        if not processor:
            print(f"--processor needs name=id[@version], got {spec!r}", file=sys.stderr)
            return 2
        processors.append((name, processor, version or None))

    results: list[dict] = []
    total = time.perf_counter()
    for name, processor, version in processors:
        for case in cases:
            result = evaluate(
                case,
                name,
                processor,
                project=args.project,
                location=args.location,
                version=version,
                verbose=args.verbose,
                cache=cache,
            )
            results.append(result)
            mark = {
                "pass": "PASS",
                "pass (needs row-number gutter)": "PASS+",
            }.get(result["verdict"], "FAIL")
            detail = result["verdict"]
            if result["verdict"] == "fail":
                detail = (
                    f"{len(result['as_extracted']['mismatches'])} mismatches, "
                    f"{len(result.get('unverified_in_our_pass', []))} unverified in our pass"
                )
            print(
                f"{mark:5s} {name:7s} {case.key:20s} {result['seconds']:6.1f}s  "
                f"rows {result.get('rows_found', 0)}/{case.row_count} "
                f"cols {result.get('columns_found', 0)}/{len(case.columns)}  {detail}"
            )
        subset = [r for r in results if r["model"] == results[-1]["model"]]
        passed = sum(1 for r in subset if r["verdict"].startswith("pass"))
        found = sum(1 for r in subset if r.get("rows_found"))
        print(
            f"  documentai {name}: {passed}/{len(subset)} pass, {found}/{len(subset)} tables found, "
            f"{sum(r['seconds'] for r in subset):.1f}s, "
            f"{sum(len(r.get('unverified_in_our_pass', [])) for r in subset)} cells our pass does not confirm\n"
        )
    print(f"{time.perf_counter() - total:.1f}s total")

    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        per = {}
        for result in results:
            per.setdefault(result["model"], []).append(result)
        payload = {
            "instrument": "scripts/eval_documentai.py",
            "arm": "Document AI (extractive) — cells from the service's own text, checked against our pass",
            "project": args.project,
            "location": args.location,
            "checked": f"{len(results)} calls: {len(processors)} processor(s) x {len(cases)} shape(s)",
            "processors": {
                name: {
                    "shapes": len(rows),
                    "pass": sum(1 for r in rows if r["verdict"].startswith("pass")),
                    "tables_found": sum(1 for r in rows if r.get("rows_found")),
                    "seconds": round(sum(r["seconds"] for r in rows), 1),
                    "unverified_in_our_pass": sum(len(r.get("unverified_in_our_pass", [])) for r in rows),
                }
                for name, rows in per.items()
            },
            "results": results,
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
