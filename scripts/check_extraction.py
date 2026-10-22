#!/usr/bin/env python
"""Does the configured `pdftotext` still produce the committed pages?

The gate cannot answer this: it runs with `PDFTOTEXT_BIN` pointed at a path that cannot
exist, on purpose, because the deployment target's extractor is a different build
(`testing_hazards.md` §2.9). So the question moves here — a **build-time** check run by the
person producing artefacts, and after any `pdftotext` upgrade.

    python scripts/check_extraction.py              # diff every mode of every document
    python scripts/check_extraction.py --doc saoso  # one document
    python scripts/check_extraction.py --limit 20   # stop after 20 differing pages

Exit codes: 0 = the committed pages are what this extractor produces; 1 = drift.

What to do with a drift report: it is a **re-baseline**, not a refresh. Poppler and Xpdf
wrap lines and detect columns differently, and `-table` exists only in Xpdf 4.x, so the
pages behind the parsers' goldens are a measurement of *one build*. Regenerate with
`python scripts/extract_fixtures.py --force` only after deciding that the new build is the
reference — then re-run the gate and review what the goldens say.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from knowledge.extraction import extract_pages, pdftotext_bin  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "knowledge" / "tests" / "fixtures"


def load_manifest() -> dict:
    path = FIXTURE_DIR / "MANIFEST.json"
    if not path.exists():  # pragma: no cover - the fixtures are committed
        raise SystemExit(f"no manifest at {path}; run scripts/extract_fixtures.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def first_difference(expected: list[str], actual: list[str]) -> tuple[int, str]:
    """The first page whose text differs: (page number, a one-line explanation)."""
    if len(expected) != len(actual):
        return 0, f"page count differs: committed {len(expected)}, this build {len(actual)}"
    for number, (want, got) in enumerate(zip(expected, actual), start=1):
        if want == got:
            continue
        want_lines, got_lines = want.splitlines(), got.splitlines()
        for index, (a, b) in enumerate(zip(want_lines, got_lines), start=1):
            if a != b:
                return number, f"page {number} line {index}:\n    committed: {a!r}\n    this build: {b!r}"
        return number, (
            f"page {number}: {len(got_lines)} lines here, {len(want_lines)} committed "
            "(identical prefix)"
        )
    return 0, "identical"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--doc", help="one document key (saoso, opp, bpp, landscape)")
    parser.add_argument("--limit", type=int, default=0, help="stop after N differing fixtures")
    args = parser.parse_args(argv)

    manifest = load_manifest()
    recorded = manifest.get("extractor", "unrecorded")
    print(f"committed by: {recorded}")
    print(f"this build:   {pdftotext_bin()}")
    if recorded != "unrecorded":
        print("")

    drift = 0
    for key in sorted(manifest["pages"]):
        doc_key, mode = key.split(".", 1)
        if args.doc and doc_key != args.doc:
            continue
        record = manifest["pages"][key]
        committed = (REPO_ROOT / record["file"]).read_text(encoding="utf-8").split("\f")
        actual = extract_pages(REPO_ROOT / record["source"], mode=mode)
        page, detail = first_difference(committed, actual)
        if page == 0 and detail == "identical":
            print(f"[ok  ] {key:18} {len(committed):4} pages")
            continue
        drift += 1
        print(f"[DIFF] {key:18} {detail}")
        if args.limit and drift >= args.limit:
            print(f"\nstopping after {drift} differing fixture(s) (--limit)")
            break

    if drift:
        print(
            f"\n{drift} fixture(s) differ from what this extractor produces.\n"
            "This is a re-baseline of the parsers' goldens, not a refresh: decide whether\n"
            "this build is the reference, then `python scripts/extract_fixtures.py --force`\n"
            "and review the resulting diff with the gate green."
        )
        return 1
    print("\nno drift — the committed pages are what this extractor produces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
