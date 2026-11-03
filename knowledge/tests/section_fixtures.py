"""Where A10's committed page fixtures are, and how to read one.

`scripts/extract_fixtures.py` extracts them from the shipped PDFs and the files are
**never hand-edited**: a hand-written fixture encodes the same assumption as the parser
it tests, which is how MVP 0 v1 passed its tests while matching zero lines of the real
document. `MANIFEST.json` is what the parsers' tests re-verify before any parser runs.

Three lines, one copy: both halves of `test_section_parsers` read the same bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))


def fixture(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")
