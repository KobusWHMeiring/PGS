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

The second half of this file guards the **context budgets** (`CONTEXT_BUDGET.md` §4.4).
Wiring `context.py --check` into the gate is only worth anything if a breach fails it, so
the wiring is asserted as text and the failure is asserted by running the same `check()`
the gate calls against a tree that is deliberately over budget.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import context

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY = REPO_ROOT / "scripts" / "verify.sh"
POISON = REPO_ROOT / "scripts" / "_no_extractor"

EXPORT = 'export PDFTOTEXT_BIN="$REPO_ROOT/scripts/_no_extractor"'
BUDGET_STEP = '"$PYTHON" scripts/context.py --check'


def test_the_gate_poisons_the_extractor():
    """Mutation: removing the export makes this red, and re-breaks portability."""
    assert EXPORT in VERIFY.read_text(encoding="utf-8")


def test_the_poisoned_path_cannot_exist():
    """Mutation: creating `scripts/_no_extractor` silently defeats the poison."""
    assert not POISON.exists(), (
        f"{POISON} exists — the gate's `PDFTOTEXT_BIN` must point at a path that cannot "
        "be a program, or extractor-independence stops being proved"
    )


# --- The context budgets -----------------------------------------------------


@pytest.fixture
def scratch_tree(tmp_path, monkeypatch):
    """A miniature repo whose budgets `context.check()` can be pointed at.

    `check()` reads module-level constants, so they are monkeypatched rather than the
    real tree being mutated: a test that breaks `HANDOVER.md` and restores it leaves the
    repo broken if it crashes half-way, and the gate would then fail for a reason nobody
    can see.
    """
    (tmp_path / "HANDOVER.md").write_text("# state\n", encoding="utf-8")
    spec = tmp_path / "spec.md"
    spec.write_text("| # | Decision | Resolution |\n|---|---|---|\n", encoding="utf-8")
    monkeypatch.setattr(context, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(context, "HANDOVER", tmp_path / "HANDOVER.md")
    monkeypatch.setattr(context, "SPEC", spec)
    monkeypatch.setattr(context, "SOURCE_GLOBS", ("*.py",))
    monkeypatch.setattr(context, "SOURCE_CAP_BYTES", 512)
    return tmp_path


def test_the_gate_runs_the_budget_check():
    """`verify.sh` must run the check, and must not leave a breach to `set -e` alone.

    A bare invocation exits the script on a breach and prints the script's line number.
    The guarded form is what says *which* budget broke and where the argument belongs, and
    it survives a later `| tee` or a function wrapper, both of which suspend `set -e`.
    """
    lines = [
        line.strip()
        for line in VERIFY.read_text(encoding="utf-8").splitlines()
        if BUDGET_STEP in line and not line.lstrip().startswith("#")
    ]
    assert lines, "scripts/verify.sh no longer runs scripts/context.py --check"
    assert any(line.startswith("if !") for line in lines), (
        "the budget check is run unguarded; a breach must say which budget broke "
        f"(found: {lines})"
    )


def test_a_budget_breach_fails_the_check(scratch_tree, capsys):
    """The half that makes the wiring worth anything: over budget => non-zero exit."""
    (scratch_tree / "oversized.py").write_text("x" * 4096, encoding="utf-8")
    assert context.check() == 1
    out = capsys.readouterr().out
    assert "oversized.py" in out
    assert "1 breach(es)" in out


def test_a_clean_tree_passes_the_check(scratch_tree, capsys):
    """The other half: a check that always fails would prove nothing either."""
    (scratch_tree / "small.py").write_text("x" * 64, encoding="utf-8")
    assert context.check() == 0
    assert "every budget holds" in capsys.readouterr().out


def test_an_absent_handover_is_a_breach(scratch_tree, capsys):
    """`size_of` returns `(0, 0)` for a missing file, so absence must be caught first.

    Without this, deleting `HANDOVER.md` — or running the gate where `product/` was never
    checked out — reads as a state file comfortably inside its 250-line budget, and the
    gate goes green on the artefact's absence.
    """
    (scratch_tree / "HANDOVER.md").unlink()
    assert context.check() == 1
    assert "HANDOVER.md is missing" in capsys.readouterr().out
