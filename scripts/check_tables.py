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
* **the extraction mode** — read from each block's `extraction:` field, never defaulted. The
  landscape's reviewed cells pass against `-table` and fail ten ways against `-layout`, so a gate
  that guessed the pass would report on paper it did not read. `--pages-mode` is the **draft-only**
  escape: it supplies the datum for an artefact written before S3, is refused when it contradicts
  what the artefact records, and says so in the report when it is used.

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
from knowledge.table_harness import check_document, recorded_extraction  # noqa: E402
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


def extraction_mode(document, override: str | None) -> tuple[str | None, str]:
    """Which rendering to check the cells against, and where the answer came from.

    In:  `document` — the parsed artefact; `override` — `--pages-mode`, or None.
    Out: `(mode, source)` where source is `"artifact"`, `"flag"`, or None when the run must stop.
    Side Effects: prints the refusal to stderr when the answer cannot be trusted.
    Fails: never — a refusal is a printed message and a `None` mode, so `main` can return 2
         rather than the shell seeing an exception.

    The four refusals are the four ways this datum can be wrong, and each is a sentence an operator
    can act on: no block records a mode and no flag was given; the blocks disagree; the flag
    contradicts the artefact; the flag names a mode the page fixtures do not have.
    """
    modes, disagreements = recorded_extraction(document)
    if disagreements:
        print(disagreements[0], file=sys.stderr)
        return None, ""
    if len(modes) > 1:  # pragma: no cover - recorded_extraction names it above
        return None, ""
    recorded = modes[0] if modes else None
    if override is None and recorded is None:
        print(
            "refusing to report a pass: no block in this artefact records the extraction its cells "
            "came from, so every cell would be checked against a guessed rendering. Add "
            "`extraction: <mode>` to each `<!-- table` header (S3's generator writes it), or pass "
            "`--pages-mode` to judge a draft on the record.",
            file=sys.stderr,
        )
        return None, ""
    if override is not None and recorded is not None and override != recorded:
        print(
            f"refusing to report a pass: the artefact records `{recorded}` and `--pages-mode` says "
            f"`{override}`. One of the two is wrong; the artefact is the one a reviewer signed.",
            file=sys.stderr,
        )
        return None, ""
    if override is not None:
        if override not in page_fixtures.MODES:
            print(f"--pages-mode {override!r} is not a committed extraction pass", file=sys.stderr)
            return None, ""
        return override, "flag"
    return recorded, "artifact"


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
        default=None,
        choices=sorted(page_fixtures.MODES),
        help=(
            "Only for a draft whose blocks record no `extraction:` — the mode is otherwise read "
            "from the artefact, and a flag that contradicts it is refused."
        ),
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
    document = parse_blocks(artefact.read_text(encoding="utf-8"))
    mode, source = extraction_mode(document, args.pages_mode)
    if mode is None:
        return 2
    try:
        pages = page_fixtures.pages(args.doc, mode)
    except AssertionError as error:
        print(f"{args.doc}: {error}", file=sys.stderr)
        return 2

    report = check_document(
        document,
        pages=pages,
        expected_rows=args.rows,
        expected_tables=len(args.rows),
    )
    where = (
        "recorded on the artefact"
        if source == "artifact"
        else "supplied by --pages-mode; the artefact records none"
    )
    print(
        f"{args.doc}: {'ok' if report.ok else 'FAIL'} — {report.tables} tables, "
        f"{report.rows} rows, {len(report.violations)} violations "
        f"({mode} pages, {where})"
    )
    for line in report.lines():
        print(f"  {line}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
