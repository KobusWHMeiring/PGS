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

`--check` is report-only by design (`CONTEXT_BUDGET.md` §4.4), so it may exit 1 while the tree
is over budget. The test asserts it reports, not that it is green.
"""

from __future__ import annotations

import pytest

from scripts import context


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
    """Report-only: a breach is exit 1, but the report itself must always be produced."""
    status = context.check()
    out = capsys.readouterr().out
    assert status in (0, 1)
    assert "context budgets" in out
    assert "breach" in out
    assert out.isascii(), "printed output must be ASCII (Windows cp1252 console)"


def test_an_unknown_task_names_the_known_ones():
    """The error is the help: it must list the recipes rather than print a traceback."""
    with pytest.raises(SystemExit) as excinfo:
        context.main(["--task", "nonesuch"])
    assert excinfo.value.code == 2
