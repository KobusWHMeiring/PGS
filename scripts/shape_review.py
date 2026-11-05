#!/usr/bin/env python
"""D85 — the eight-shape answer key, judged against the paper cell by cell.

    python scripts/shape_review.py                 # write product/design/uat/shape_key_review.html
    python scripts/shape_review.py --check         # is the committed artefact current?
    python scripts/shape_review.py --out /tmp/x.html

**The problem this exists for.** `INGESTION_ENGINE_PRD.md` §3.10: the key that scores every
extractor arm — `knowledge/tests/shape_fixtures.py` — was written by an agent (commit `5c45550`),
and no human has ever checked a cell. Characters are already verified (R3 asserts every cell is a
contiguous run of the committed page text); the **groupings** are not: whether the paper's bare row
numbers are a column, whether `Proud member of` sits in column 3, whether `Step 3` is inside the
1,112-character cell, and how Appendix 6a's four printed header lines become two labels are all
decisions the fixtures encode and no person made. Three independent readers disagree with the key
on the same judgement shapes, so a re-score before this page is signed scores the arms against a
convention, not against the paper.

**What it produces.** One self-contained HTML file — no CDN, no font, no build, no network, opens
from disk with the wifi off — in which each of the eight shapes is **the page image from the real
PDF beside the grid the key expects**, with one verdict per claim: *yes*, *no*, *can't tell*, and a
reason for the last two. It is a judgement surface, not a test: nothing here scores, checks or
decides (`pgs-presenting-uat`'s hard rule 1). `scripts/shape_review_signoff.py` turns a reviewer's
export into `knowledge/tests/shape_review.json`, and the gate fails the moment the key changes under
a signed claim — a signature cannot outlive what it signed.

This module is the contract and the console. **What the key claims** is `scripts/shape_claims.py`;
**how the page looks** is `scripts/shape_review_template.py`; **the markup** is
`scripts/shape_review_page.py`. They are separate because `build_principles.md` §II caps a file at
30 KB, and because the four pieces fail differently: a claim is wrong in a review, a stylesheet is
wrong in a browser, a template is wrong in the artefact, and this file is wrong in CI.

The page images are committed bytes (`knowledge/tests/fixtures/shape_pages/`, rendered once by
`scripts/render_shape_pages.py`), so this script needs no PDF reader. The gate imports this module
and asserts its output; nothing here touches an extractor or a network (requirement 10).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from knowledge.tests.shape_fixtures import SHAPES  # noqa: E402,F401  (re-exported for tests)
from scripts.shape_claims import (  # noqa: E402,F401  (re-exported: the sign-off reads the same key)
    Claim,
    VERDICTS,
    all_claims,
    cell_spec,
    claims,
    claim_ids,
)
from scripts.shape_review_page import build_html, escape  # noqa: E402,F401

DEFAULT_OUT = REPO_ROOT / "product/design/uat/shape_key_review.html"
ARTEFACT_NAME = "product/design/uat/shape_key_review.html"
KIND = "pgs-shape-key-review"
VERSION = 1


def _display(path: Path) -> str:
    """A path for a console message: short inside the tree, absolute when a caller moved it."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check", action="store_true", help="compare with the committed artefact; write nothing"
    )
    args = parser.parse_args(argv)

    html = build_html(ARTEFACT_NAME, KIND, VERSION)
    out = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    if args.check:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != html:
            print(f"STALE {_display(out)} - regenerate with scripts/shape_review.py")
            return 1
        print(f"current: {_display(out)} ({len(html) / 1024:.0f} KB)")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    print(
        f"wrote {_display(out)} - {len(SHAPES)} shapes, "
        f"{len(all_claims())} claims, {len(html) / 1024:.0f} KB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
