"""The gate must not need a PDF reader — and that must not quietly stop being true.

The first real deployment gate failed 15 tests and 61 errors because the target has
poppler and the goldens were measured on Xpdf (`testing_hazards.md` §2.9). The fix is not
"install Xpdf on the box": it is that the parsers' inputs are committed
(`knowledge/tests/page_fixtures.py`) and `scripts/verify.sh` points `PDFTOTEXT_BIN` at a
path that cannot exist, discarding any inherited value.

These two assertions are the whole policy, and both fail silently in the other direction:

* delete the export, and the gate starts using whatever extractor the machine happens to
  have — green here, red on the deploy target;
* create the file the variable names, and the poison stops poisoning.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY = REPO_ROOT / "scripts" / "verify.sh"
POISON = REPO_ROOT / "scripts" / "_no_extractor"

EXPORT = 'export PDFTOTEXT_BIN="$REPO_ROOT/scripts/_no_extractor"'


def test_the_gate_poisons_the_extractor():
    """Mutation: removing the export makes this red, and re-breaks portability."""
    assert EXPORT in VERIFY.read_text(encoding="utf-8")


def test_the_poisoned_path_cannot_exist():
    """Mutation: creating `scripts/_no_extractor` silently defeats the poison."""
    assert not POISON.exists(), (
        f"{POISON} exists — the gate's `PDFTOTEXT_BIN` must point at a path that cannot "
        "be a program, or extractor-independence stops being proved"
    )
