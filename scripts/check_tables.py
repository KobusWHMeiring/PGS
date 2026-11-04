#!/usr/bin/env python
"""D80 S4 — check a corpus artefact's tables against the pages they were transcribed from.

This is the gate for a document that is *about* to be reviewed: it runs the harness in
`knowledge/table_harness.py` over every `<!-- table … -->` block in an artefact and names each
violation of the ingestion engine's requirements 2-7.

    python scripts/check_tables.py --doc landscape --rows 3,2,3 --pages-mode table
    python scripts/check_tables.py --doc opp --rows 6

Two things are declarations rather than inference, and both are the point:

* **`--rows`** — a page cannot say how many rows it prints in machine-readable form, so a gate that
  infers the count asserts nothing. Omit it and nothing is asserted, so the script refuses rather
  than printing a pass.
* **`--pages-mode`** — `layout` or `table`, the extraction the cells were transcribed from. It is
  the last per-document datum in this path; the landscape's grid pages came from `-table` and the
  OPP's three-column page from `-layout`. S3's generator is where it stops being a command-line
  flag and becomes a recorded banner on the artefact.

One document per run, because the declaration is per document: a single `--rows` cannot describe
four artefacts, and a gate that guessed which count belonged to which table would be the inference
this file exists to avoid. The corpus gate runs it once per document
(`tests/tools/test_check_tables.py`).

The pages are the committed fixtures (`knowledge/tests/fixtures/`), so this needs no `pdftotext`
and no network — requirement 10's "the gate needs no extractor".
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")

import django  # noqa: E402

django.setup()

from knowledge.corpus import parse_blocks  # noqa: E402
from knowledge.ingest import CORPUS_DOCUMENTS, corpus_artifact  # noqa: E402
from knowledge.table_harness import check_document  # noqa: E402
from knowledge.tests import page_fixtures  # noqa: E402


def row_counts(value: str) -> tuple[int, ...]:
    """`"3,2,3"` -> `(3, 2, 3)`. A typo is an error, not a silently smaller declaration."""
    try:
        counts = tuple(int(part) for part in value.replace(" ", "").split(",") if part)
    except ValueError:
        raise argparse.ArgumentTypeError(f"--rows wants `3,2,3`, not {value!r}") from None
    if not counts:
        raise argparse.ArgumentTypeError("--rows names no counts")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", required=True)
    parser.add_argument(
        "--rows",
        type=row_counts,
        help="Row counts, one per table in document order: `3,2,3`. Required — see the docstring.",
    )
    parser.add_argument(
        "--pages-mode",
        default="layout",
        choices=sorted(page_fixtures.MODES),
        help="The extraction the cells were transcribed from (default: layout).",
    )
    args = parser.parse_args(argv)

    if args.rows is None:
        print(
            "refusing to report a pass: `--rows` is the declaration that makes the row count an "
            "assertion. Pass the counts the page prints, one per table in document order.",
            file=sys.stderr,
        )
        return 2

    artefact = corpus_artifact(args.doc)
    if artefact is None:
        declared = ", ".join(sorted(CORPUS_DOCUMENTS))
        print(f"{args.doc!r}: no reviewed artefact is declared (the governed keys are {declared})",
              file=sys.stderr)
        return 2
    try:
        pages = page_fixtures.pages(args.doc, args.pages_mode)
    except AssertionError as error:
        print(f"{args.doc}: {error}", file=sys.stderr)
        return 2

    report = check_document(
        parse_blocks(artefact.read_text(encoding="utf-8")),
        pages=pages,
        expected_rows=args.rows,
        expected_tables=len(args.rows),
    )
    print(
        f"{args.doc}: {'ok' if report.ok else 'FAIL'} — {report.tables} tables, "
        f"{report.rows} rows, {len(report.violations)} violations "
        f"({args.pages_mode} pages)"
    )
    for line in report.lines():
        print(f"  {line}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
