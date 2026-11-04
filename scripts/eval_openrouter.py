#!/usr/bin/env python
"""D80 S2b — the OpenRouter VLM arm: the model proposes the grid, the page supplies the characters.

This is the second arm of `INGESTION_ENGINE_PRD.md` §3.6, and it is an **evaluation instrument, not a
pipeline step** — the same rule as `eval_extractors.py`: it runs once, on a machine with a key and a
rasteriser, and the thing that enters the repo is its output (the §3.5-style table and the JSON). The
gate must never need it (requirement 10), so nothing here is imported by the suite and `pypdfium2` is
imported lazily inside `render()`.

    export OPENROUTER_API_KEY=...
    python scripts/eval_openrouter.py --model google/gemini-3.1-flash-lite --json _scratch/or/x.json

**Why this arm is admissible at all.** A VLM *writes* the text it believes it read, so a wrong digit
looks identical to a right one, and requirement 9 says a quote is characters we verified. So the model
proposes the grid and the **extraction pass** already committed for that page
(`knowledge/tests/page_fixtures.py`) supplies the characters. Three consequences, all recorded rather
than hidden, and all implemented in `scripts/table_reads.py`:

* a quoted line that is not a **contiguous run** of its page is a violation (requirement 3), and the
  cell is reported unresolved — the arm is only as good as the check;
* the one **declared normalisation** (the paper letter-spaces some words) is reported per cell, never
  applied silently;
* a merged cell's text stays in the first cell it covers and the cells it covers are `""` — the
  paper's silence, not a replicated value (Docling's mapping replicates; the fixtures side with
  "filed under the cell that prints it", and the arms are compared per shape, never summed).

**Three prompt forms, because the rule has three readings** — `lines` (the model copies each cell
verbatim), `anchors` (it names a cell's first and last words and the page is sliced between them) and
`indices` (it returns line numbers and never emits a character). Two readings are always published:
as the model gave it, and once the paper's **row-number gutter** is declared.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = Path(__file__).resolve().parents[1]

from knowledge.tests import page_fixtures  # noqa: E402
from knowledge.tests.shape_fixtures import BY_KEY, SHAPES, TableRead, mismatches  # noqa: E402
from scripts.table_reads import (  # noqa: E402
    drop_row_number_gutter,
    has_letter_spacing,
    other_mode,
    numbered_pages,
    page_runs,
    read_from,
    read_from_anchors,
    read_from_indices,
)

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

#: How much of a cell the evidence file keeps. The score is computed on the whole cell.
CELL_CLIP = 200

#: The instruction. It asks for **structure and verbatim lines**, never for a reading of the document,
#: and it names the four things a general extractor loses (header association, dividers, spans,
#: non-text) because those are exactly the requirements the score is measuring.
PROMPT = """You are reading page images of a printed certification standard and returning the \
printed table as JSON. Copy characters exactly as the page prints them.

Return ONE JSON object with these keys:

- "columns": the printed column headings, left to right, one string each. Use [] when the page
  prints no heading row.
- "rows": the printed body rows, top to bottom. Each row is an object
  {"page": <1-based image number the row starts on>, "cells": [<cell>, ...]}.
  A cell is the printed text of that cell, with each printed line separated by "\\n".
  Copy the page's own spelling, punctuation, commas and dashes. Never translate, correct, expand,
  reorder, rejoin or summarise. If a cell is empty on the page, use "" — never omit a cell, never
  fill it from a neighbouring cell or the row above.
- "dividers": text printed between two body rows that labels the rows beneath it (a part heading or
  a qualifier), as {"before_row": <index into rows>, "text": "...", "kind": "part" | "qualifier"}.
  Use [] when there are none. A divider is not a row and not a column heading.
- "spans": merged cells, as {"row": <index>, "column": <index>, "rowspan": <n>, "colspan": <m>}.
  The merged text stays in the first cell it covers; the cells it covers are "".
- "non_text": artwork inside a cell, as {"row": <index>, "column": <index>, "label": "<the caption
  printed beside it, or \\"\\">"}.

If the page prints no table, return {"columns": [], "rows": [], "dividers": [], "spans": [],
"non_text": []}. Output the JSON object only: no prose, no code fence, no commentary."""

#: The second mode, and the faithful form of the rule in this PRD: the model names where each cell
#: **starts and ends**, and the extraction pass supplies every character in between. Asking a VLM to
#: re-type a 1,112-character cell verbatim asks it to re-wrap a paragraph, and measured 2026-11-04 it
#: re-wraps at its own width — a transcription failure that says nothing about whether it found the
#: cell. Boundaries are the model's judgement; characters are the page's.
PROMPT_ANCHORS = """You are reading page images of a printed certification standard and returning the \
printed table as JSON. You are locating cells, not transcribing them.

Return ONE JSON object with these keys:

- "columns": the printed column headings, left to right, copied character for character. Use [] when
  the page prints no heading row.
- "rows": the printed body rows, top to bottom. Each row is an object
  {"page": <1-based image number the row starts on>, "cells": [<cell>, ...]} where a cell is
  {"first": "<the first three to six words printed in that cell>",
   "last": "<the last three to six words printed in that cell>"}.
  Copy those words exactly as printed — do not correct, translate or reorder them. For a cell whose
  whole text is shorter than six words, use the whole text in both fields. For a cell that prints
  nothing, use {"first": "", "last": ""}: never omit a cell, never fill it from a neighbour.
- "dividers": text printed between two body rows that labels the rows beneath it, as
  {"before_row": <index into rows>, "text": "...", "kind": "part" | "qualifier"}. Use [] when
  there are none. A divider is not a row and not a column heading.
- "spans": merged cells, as {"row": <index>, "column": <index>, "rowspan": <n>, "colspan": <m>}.
  The merged text stays in the first cell it covers; the cells it covers print nothing.
- "non_text": artwork inside a cell, as {"row": <index>, "column": <index>, "label": "<the caption
  printed beside it, or \"\">"}.

If the page prints no table, return {"columns": [], "rows": [], "dividers": [], "spans": [],
"non_text": []}. Output the JSON object only: no prose, no code fence, no commentary."""

#: The third mode, and the one that makes requirement 9 structural rather than a promise: the model is
#: given the page's **numbered lines** and returns **line numbers only**. It cannot mistype a character
#: because it never emits one — every cell is a join of lines the extraction pass printed. What it owns
#: is the assignment (which line belongs to which cell, which line is a heading, which is a divider),
#: and every index it returns is checkable against the page.
PROMPT_INDICES = """You are given a printed certification standard: the page image, and the page's \
extracted text as numbered lines. Return the printed table's structure as JSON. Refer to text ONLY by
line number — never retype, correct or summarise any text.

Return ONE JSON object with these keys:

- "columns": one entry per printed column, left to right, each entry the list of line numbers that
  make up that column's heading. Use [] when the page prints no heading row.
- "rows": the printed body rows, top to bottom. Each row is {"page": <1-based image number the row
  starts on>, "cells": [<cell>, ...]} where a cell is the list of line numbers holding that cell's
  text, in printed order. A cell that prints nothing is []. Never omit a cell, never put a neighbour's
  line in it.
- "dividers": printed lines that label the rows beneath them rather than being a row of their own, as
  {"before_row": <index into rows>, "line": <line number>, "kind": "part" | "qualifier"}. Use []
  when there are none.
- "spans": merged cells, as {"row": <index>, "column": <index>, "rowspan": <n>, "colspan": <m>}.
- "non_text": artwork inside a cell, as {"row": <index>, "column": <index>, "label_line": <line
  number of the caption printed beside it, or null>}.

If the page prints no table, return {"columns": [], "rows": [], "dividers": [], "spans": [],
"non_text": []}. Output the JSON object only: no prose, no code fence, no commentary."""

PROMPTS = {"lines": PROMPT, "anchors": PROMPT_ANCHORS, "indices": PROMPT_INDICES}

def documents_for(case) -> tuple[str, str]:
    record = page_fixtures.entry(case.doc_key)
    return str(REPO_ROOT / record["source"]), case.doc_key


#: Rendered pages, keyed by (pdf path, page, dpi). One run asks the same page for several models.
_IMAGES: dict[tuple[str, int, int], bytes] = {}


def render(pdf: str, pages: tuple[int, ...], dpi: int = 200) -> list[bytes]:
    """Rasterise just the shape's pages, as PNG. Lazily imports the rasteriser, like `docling`.

    200 dpi is measured, not assumed: at 200 dpi an 8 pt printed line is ~22 px tall, which is what a
    VLM needs to resolve `1,500` from `1,800`. A higher dpi costs image tokens quadratically and buys
    nothing the extraction pass does not already carry.
    """
    try:
        import pypdfium2  # noqa: F401
    except ImportError as error:  # pragma: no cover - the evaluation machine has it
        raise SystemExit(
            "pypdfium2 is not installed in this interpreter. It is deliberately not a dependency of "
            "the project: install it in a throwaway venv and run this script with that venv's "
            f"python. ({error})"
        ) from None
    import pypdfium2 as pdfium

    document = None
    out: list[bytes] = []
    for page in pages:
        key = (pdf, page, dpi)
        if key in _IMAGES:
            out.append(_IMAGES[key])
            continue
        if document is None:
            document = pdfium.PdfDocument(pdf)
        image = document[page - 1].render(scale=dpi / 72).to_pil()
        buffer = _png_bytes(image)
        _IMAGES[key] = buffer
        out.append(buffer)
    return out


def _png_bytes(image) -> bytes:
    import io

    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=True)
    return stream.getvalue()


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "OPENROUTER_API_KEY is not set in this shell. It is not in the repo `.env` and must not "
            "be: this script reads the session environment, like the Docling arm reads its venv."
        )
    return key


def ask(
    model: str,
    images: list[bytes],
    timeout: int = 300,
    cache: Path | None = None,
    key: str = "",
    prompt: str = PROMPT,
    numbered: str = "",
) -> dict:
    """One request, or the cached response. Returns the parsed JSON object plus the call's accounting.

    The cache is not an optimisation: a resolver fix must be re-scorable without buying a new sample
    from a provider whose temperature-0 output is not guaranteed to be the same twice. The stored file
    is the provider's own body, so the evidence JSON can be regenerated from it offline.
    """
    if cache is not None:
        stored = cache / f"{key}.json"
        if stored.exists():
            payload = json.loads(stored.read_text(encoding="utf-8"))
            return _account(payload, model, replayed=True)
    content: list[dict] = [
        {
            "type": "text",
            "text": prompt
            + f"\n\nThe page images are attached in printed order: image 1 is the first page of the "
            f"table, image {len(images)} the last.",
        }
    ]
    if numbered:
        content.append({"type": "text", "text": numbered})
    for image in images:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64," + base64.b64encode(image).decode()},
            }
        )
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "usage": {"include": True},
        }
    ).encode()
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
            "X-Title": "PGS D80 S2b extractor evaluation",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:600]
        raise SystemExit(f"{model}: HTTP {error.code} — {detail}") from None
    payload["seconds"] = round(time.perf_counter() - started, 2)
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"{key}.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return _account(payload, model, replayed=False)


def _account(payload: dict, model: str, *, replayed: bool) -> dict:
    message = (payload.get("choices") or [{}])[0].get("message", {})
    text = message.get("content") or ""
    return {
        "model": payload.get("model", model),
        "text": text,
        "seconds": payload.get("seconds", 0.0),
        "usage": payload.get("usage") or {},
        "finish_reason": (payload.get("choices") or [{}])[0].get("finish_reason"),
        "parsed": parse_json(text),
        "replayed": replayed,
    }


def parse_json(text: str) -> dict | None:
    """The object the model returned, or None. A fenced block is tolerated; a wrong shape is not."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        value = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def evaluate(
    case,
    model: str,
    dpi: int = 200,
    verbose: bool = False,
    cache: Path | None = None,
    mode: str = "lines",
    text_mode: str | None = None,
) -> dict:
    """One shape, one model: render, ask, resolve, score. The score is `mismatches()`, S0's own."""
    pdf, doc_key = documents_for(case)
    images = render(pdf, case.pdf_pages, dpi)
    # The model call is keyed without the text mode: the pass only affects how the answer is
    # *verified*, so a different pass must re-score the same answer rather than buy a new one.
    key = f"{re.sub(r'[^a-z0-9]+', '-', model.lower())}__{case.key}__dpi{dpi}__{mode}"
    numbered = ""
    numbered_lines: dict[int, list[str]] = {}
    if mode == "indices":
        numbered, numbered_lines = numbered_pages(case, text_mode)
    call = ask(model, images, cache=cache, key=key, prompt=PROMPTS[mode], numbered=numbered)
    gutter = 0
    result = {
        "shape": case.key,
        "label": case.shape,
        "doc": doc_key,
        "model": call["model"],
        "mode": mode,
        "text_mode": text_mode or case.mode,
        "row_number_gutter": gutter,
        "pdf_pages": list(case.pdf_pages),
        "printed_pages": list(case.printed_pages),
        "dpi": dpi,
        "seconds": round(call["seconds"], 1),
        "usage": call["usage"],
        "finish_reason": call["finish_reason"],
        "replayed": call["replayed"],
    }
    if call["parsed"] is None:
        result.update(
            {
                "verdict": "fail",
                "found": False,
                "as_extracted": {
                    "verdict": "fail",
                    "mismatches": [f"{case.key}: the model returned no JSON object"],
                    "columns": [],
                    "rows": [],
                    "rows_total": 0,
                },
                "first_row_as_header": {
                    "verdict": "fail",
                    "mismatches": [f"{case.key}: the model returned no JSON object"],
                    "columns": [],
                    "rows": [],
                    "rows_total": 0,
                },
                "violations": [],
                "raw_head": call["text"][:400],
            }
        )
        return result

    proposal = call["parsed"]
    runs = page_runs(case, text_mode)
    if mode == "anchors":
        read, violations = read_from_anchors(proposal, case, runs)
    elif mode == "indices":
        read, violations = read_from_indices(proposal, case, runs, numbered_lines)
    else:
        read, violations = read_from(proposal, case, runs)
    # Both readings are always computed and published, like Docling's two: the answer as the model
    # gave it, and the answer once the paper's row-number gutter is declared. A tool that needs a
    # convention to pass is a different finding from one that cannot pass.
    guttered_read, gutter = drop_row_number_gutter(read)
    strict = mismatches(case, read)
    guttered = mismatches(case, guttered_read) if gutter else strict
    conventional = strict
    if not read.columns and len(read.rows) > 1:
        conventional_read = TableRead(
            columns=read.rows[0], rows=read.rows[1:], pages=read.pages[1:], dividers=read.dividers
        )
        conventional = mismatches(case, conventional_read)
    else:
        conventional_read = read

    if verbose:
        print(f"\n--- {case.key}: {call['model']}")
        print(f"    columns: {read.columns}")
        for index, row in enumerate(read.rows):
            print(f"    row {index} (p{read.pages[index]}): {row}")
        if read.dividers:
            print(f"    dividers: {read.dividers}")
        for violation in violations:
            print(f"    VIOLATION {violation}")

    # A grid that matches while some cell quotes did not resolve is **not** a pass: the characters
    # would then be the model's, which is the thing this arm exists to refuse. It is named, not folded
    # into the fail column, because 'the structure was right and the quoting was not' is the finding.
    if not strict and not violations:
        verdict = "pass"
    elif not guttered and not violations:
        verdict = "pass (needs row-number gutter)"
    elif not conventional and not violations:
        verdict = "pass (needs header convention)"
    elif not (strict and guttered and conventional):
        verdict = "pass (grid only, quotes unresolved)"
    else:
        verdict = "fail"

    def reading(one: TableRead, found: list[str]) -> dict:
        return {
            "verdict": "pass" if not found else "fail",
            "mismatches": found,
            "columns": [column[:CELL_CLIP] for column in one.columns],
            # Four rows, each cell clipped: a 1,112-character cell sampled four times is 22 KB of
            # evidence for a claim the mismatch list already carries, and this file is meant to be
            # small enough to read and diff (evidence/README.md). The grid is regenerable.
            "rows": [[cell[:CELL_CLIP] for cell in row] for row in one.rows[:4]],
            "rows_total": len(one.rows),
            "rows_sampled": min(4, len(one.rows)),
        }

    result.update(
        {
            "found": bool(read.rows),
            "verdict": verdict,
            "rows_found": len(read.rows),
            "rows_expected": case.row_count,
            "columns_found": len(read.columns),
            "columns_expected": len(case.columns),
            "as_extracted": reading(read, strict),
            "with_row_number_gutter": (
                {"identical_to_as_extracted": True}
                if not gutter
                else reading(guttered_read, guttered)
            ),
            # The second reading is only a second reading when the model returned no column labels:
            # otherwise the two grids are the same object, and writing it twice doubles the evidence
            # file for nothing. A consumer that wants the rows checks this flag.
            "first_row_as_header": (
                {"identical_to_as_extracted": True}
                if conventional_read is read
                else reading(conventional_read, conventional)
            ),
            "violations": violations,
            # Cells whose page text still carries the paper's letter-spacing. Not a model failure and
            # not a pass: the reviewed literal rejoins the word, which is a declared normalisation the
            # generator (S3) owns, so the count is published beside the score rather than folded in.
            "letter_spaced_cells": [
                {"row": index, "column": column}
                for index, row in enumerate(read.rows)
                for column, cell in enumerate(row)
                if has_letter_spacing(cell)
            ],
            "spans": proposal.get("spans") or [],
            "non_text": proposal.get("non_text") or [],
        }
    )
    return result


def _conventional_pass(result: dict) -> bool:
    """Whether the grid passes once row 0 is taken as the header (the Docling arm's second column)."""
    second = result["first_row_as_header"]
    if second.get("identical_to_as_extracted"):
        return result["as_extracted"]["verdict"] == "pass"
    return second.get("verdict") == "pass"


def cost_of(usage: dict) -> float | None:
    for key in ("cost", "total_cost"):
        if isinstance(usage.get(key), (int, float)):
            return float(usage[key])
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        action="append",
        help="OpenRouter model id; repeat for a panel. Default: the three in PANEL.",
    )
    parser.add_argument("--json", help="Write the full result, per shape and model, to this path.")
    parser.add_argument("--shape", help="Comma-separated shape keys (default: all eight).")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument(
        "--mode",
        action="append",
        choices=sorted(PROMPTS),
        help="Prompt form; repeat for both. 'lines' asks for verbatim lines, 'anchors' for first/last "
        "words (the faithful form: the page supplies every character). Default: both.",
    )
    parser.add_argument(
        "--cache",
        default=str(REPO_ROOT / "_scratch" / "or" / "responses"),
        help="Directory of raw provider responses; a cached (model, shape, dpi) is never re-asked.",
    )
    parser.add_argument(
        "--text-mode",
        choices=("layout", "table", "raw", "other"),
        help="The pass the characters are verified against. 'other' means the pass the shape does "
        "not declare — the same cached model answer, re-scored against a different page text.",
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

    models = args.model or list(PANEL)
    modes = args.mode or list(PROMPTS)
    results: list[dict] = []
    total = time.perf_counter()
    for model in models:
        for mode in modes:
            for case in cases:
                pass_mode = args.text_mode
                if pass_mode == "other":
                    pass_mode = other_mode(case)
                    if pass_mode is None:
                        print(
                            f"skip  {case.key}: {case.doc_key} has one committed pass "
                            f"({case.mode}); there is no second pass to score against",
                            file=sys.stderr,
                        )
                        continue
                result = evaluate(
                    case,
                    model,
                    dpi=args.dpi,
                    verbose=args.verbose,
                    cache=cache,
                    mode=mode,
                    text_mode=pass_mode,
                )
                results.append(result)
                mark = {
                    "pass": "PASS",
                    "pass (needs header convention)": "PASS*",
                    "pass (grid only, quotes unresolved)": "GRID?",
                }.get(result["verdict"], "FAIL")
                detail = result["verdict"]
                if result["verdict"] == "fail":
                    detail = (
                        f"{len(result['as_extracted']['mismatches'])} mismatches, "
                        f"{len(result['violations'])} quote violations"
                    )
                print(
                    f"{mark:5s} {mode:8s} {case.key:20s} {result['seconds']:6.1f}s  "
                    f"rows {result.get('rows_found', 0)}/{case.row_count} "
                    f"cols {result.get('columns_found', 0)}/{len(case.columns)}  {detail}"
                )
            subset = [r for r in results if r["model"] == results[-1]["model"] and r["mode"] == mode]
            strict_pass = sum(1 for r in subset if r["verdict"] == "pass")
            grid_only = sum(
                1 for r in subset if r["verdict"] == "pass (grid only, quotes unresolved)"
            )
            gutter_pass = sum(
                1 for r in subset if r["verdict"] == "pass (needs row-number gutter)"
            )
            conventional_pass = sum(
                1
                for r in subset
                if r["verdict"]
                in ("pass", "pass (needs header convention)", "pass (needs row-number gutter)")
            )
            spend = sum(cost_of(r["usage"]) or 0 for r in subset)
            calls = [r["usage"] for r in subset]
            print(
                f"  {results[-1]['model']} [{mode}]: {strict_pass}/{len(subset)} pass, "
                f"{gutter_pass} gutter-only, {grid_only} grid-only, "
                f"{conventional_pass}/{len(subset)} with row 0 as header, "
                f"{sum(c.get('prompt_tokens', 0) for c in calls)} in / "
                f"{sum(c.get('completion_tokens', 0) for c in calls)} out tokens, "
                f"${spend:.4f}\n"
            )
    elapsed = time.perf_counter() - total
    print(f"{elapsed:.1f}s total")

    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        per_model = {}
        for result in results:
            per_model.setdefault(f"{result['model']} [{result['mode']}]", []).append(result)
        payload = {
            "instrument": "scripts/eval_openrouter.py",
            "arm": "VLM via OpenRouter — the model proposes the grid, the page supplies the characters",
            "prompts": PROMPTS,
            "dpi": args.dpi,
            "cells_clipped_at": CELL_CLIP,
            "checked": (
                f"{len(results)} calls: {len(models)} model(s) x {len(modes)} mode(s) x "
                f"{len(cases)} shape(s)"
            ),
            "models": {
                name: {
                    "shapes": len(rows),
                    "pass": sum(1 for r in rows if r["verdict"] == "pass"),
                    "grid_only": sum(
                        1 for r in rows if r["verdict"] == "pass (grid only, quotes unresolved)"
                    ),
                    "gutter_only": sum(
                        1 for r in rows if r["verdict"] == "pass (needs row-number gutter)"
                    ),
                    "as_extracted": sum(1 for r in rows if r["as_extracted"]["verdict"] == "pass"),
                    "first_row_as_header": sum(1 for r in rows if _conventional_pass(r)),
                    "prompt_tokens": sum(r["usage"].get("prompt_tokens", 0) for r in rows),
                    "completion_tokens": sum(r["usage"].get("completion_tokens", 0) for r in rows),
                    "cost_usd": round(sum(cost_of(r["usage"]) or 0 for r in rows), 4),
                    "seconds": round(sum(r["seconds"] for r in rows), 1),
                    "quote_violations": sum(len(r["violations"]) for r in rows),
                }
                for name, rows in per_model.items()
            },
            "results": results,
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")
    return 0


#: The panel: a cheap fast model, a mid, and the strong one — three points on the price curve, so the
#: finding is "what does a VLM do" and not "what did one vendor's cheapest do on one day".
PANEL = (
    "google/gemini-3.1-flash-lite",
    "anthropic/claude-sonnet-5.5",
    "openai/gpt-5.6",
)


if __name__ == "__main__":
    raise SystemExit(main())
