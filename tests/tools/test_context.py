"""`scripts/context.py` is the instrument the read recipes depend on.

**Why these tests exist.** AGENTS.md now sends every session to `python scripts/context.py
--task <task>` instead of a "read these first" table. That makes two silent failures expensive:

1. **A recipe points at a file that moved.** The backlog convention moves PRDs between
   directories, so a path in `TASKS` can rot the moment `product/backlog.py --apply` runs. A
   recipe that sends the reader to a missing file is worse than no recipe: it burns the budget
   and returns nothing.
2. **The output cannot be printed.** This script once crashed with `UnicodeEncodeError` on a
   Windows `cp1252` console, while printing `≈` at the end of the read budget. Every task recipe
   was therefore broken on the machine it was written on, and nothing failed until a human ran
   it. Printed output must stay ASCII.

`--check` is enforced by the gate (`scripts/verify.sh` step 1/4), so a breach anywhere makes
this suite's own gate run red. These tests assert that it *reports* correctly — the breach
that proves the gate can fail lives in `tests/tools/test_verify_gate.py`.
"""

from __future__ import annotations

import re

import pytest

from scripts import context

SPEC = context.REPO_ROOT / "product/backlog/Refinement/PGS_PLATFORM_SPEC.md"
DECISION_TOKEN = re.compile(r"`([^`\n]+\.(?:md|html))`")


def test_every_recipe_entry_exists():
    """A missing recipe file is a dead end discovered only by running the recipe."""
    missing = [
        f"{task}: {name}"
        for task, entries in context.TASKS.items()
        for name, _why, _mode in entries
        if not (context.REPO_ROOT / name).is_file()
    ]
    missing += [
        f"ALWAYS: {name}"
        for name, _why, _mode in context.ALWAYS
        if not (context.REPO_ROOT / name).is_file()
    ]
    assert not missing, missing


@pytest.mark.parametrize("task", sorted(context.TASKS))
def test_every_recipe_prints_an_ascii_read_budget(task, capsys):
    """`main` must complete and print a budget; `≈` here is a cp1252 crash on Windows."""
    assert context.main(["--task", task]) == 0
    out = capsys.readouterr().out
    assert "read budget" in out
    assert out.isascii(), "printed output must be ASCII (Windows cp1252 console)"


def test_help_is_ascii(capsys):
    """`--help` is a print path: argparse renders `description=__doc__` to stdout.

    The docstring keeps the repo's typography (`≈`, `§`, an em dash), so passing it to
    argparse unmodified re-introduced the exact cp1252 crash the recipe tests guard against -
    and `--task`/`--check` stayed green while `--help` was broken.
    """
    with pytest.raises(SystemExit) as excinfo:
        context.main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "--task" in out
    assert out.isascii(), "printed output must be ASCII (Windows cp1252 console)"


def test_check_reports_without_crashing(capsys):
    """A breach is exit 1 and the report must still be produced: `verify.sh` prints it."""
    status = context.check()
    out = capsys.readouterr().out
    assert status in (0, 1)
    assert "context budgets" in out
    assert "breach" in out
    assert "verify.sh" in out, "the report must say what runs it"
    assert out.isascii(), "printed output must be ASCII (Windows cp1252 console)"


def unresolvable_links(spec_text):
    """Every backticked `.md`/`.html` path in a decision row, minus the ones that resolve.

    A `<doc>` token is prose rather than a path — `knowledge/corpus/<doc>.md` names four
    files — so it is skipped, and everything else must be a repo-root-relative path.
    """
    bad = []
    for line in spec_text.splitlines():
        if not line.startswith("| D"):
            continue
        row = line.split("|")[1].strip()
        for token in DECISION_TOKEN.findall(line):
            if "<" not in token and not (context.REPO_ROOT / token).is_file():
                bad.append(f"{row}: {token}")
    return bad


def test_every_decision_row_link_resolves():
    """A row's evidence is its link (`CONTEXT_BUDGET.md` §4.2); a basename is not a link.

    When the 14 over-budget rows were cut to a sentence and a link, 12 of them pointed at
    paths that do not exist from the spec's own directory — bare filenames for PRDs in
    `In Progress/`, and `Refinement/` for one that had moved to `Done/` — and nothing
    failed, because no test ever read a row's link.
    """
    assert not unresolvable_links(SPEC.read_text(encoding="utf-8"))


def test_the_link_check_can_fail():
    """Prove the guard before trusting it green: a bare basename must be named."""
    assert unresolvable_links("| D999 | q | **Yes** (`CHAT_ANSWER_COVERAGE_PRD.md`). |") == [
        "D999: CHAT_ANSWER_COVERAGE_PRD.md"
    ]
    resolved = "| D999 | q | **Yes** (`product/backlog/In Progress/CHAT_ANSWER_COVERAGE_PRD.md`). |"
    assert unresolvable_links(resolved) == []


def test_an_unknown_task_names_the_known_ones():
    """The error is the help: it must list the recipes rather than print a traceback."""
    with pytest.raises(SystemExit) as excinfo:
        context.main(["--task", "nonesuch"])
    assert excinfo.value.code == 2
