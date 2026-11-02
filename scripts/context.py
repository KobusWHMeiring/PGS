"""What a session must read, how big it is, and whether the tree is inside its budgets.

    python scripts/context.py                 # sizes of the read-set, and the recipes
    python scripts/context.py --task chat     # what to read for one kind of task
    python scripts/context.py --check         # report every budget breach (report-only today)

**Why this exists.** `AGENTS.md` says "read these first" and lists seven files totalling
**521 KB** — about 145k tokens, which is more than the context window of a mid-size model and
about half a day of a session's budget before any work starts. `build_principles.md` §V calls
`python summarise.py` the context buffet; that file has never existed in this repo.

So the numbers live here, measured, and the doc that explains them is
`product/docs/context/CONTEXT_BUDGET.md`. This script is the measuring instrument for both: it
counts, it names the offenders, and `--check` is the shape a gate would take once the tree is
inside the budgets.

**Not wired into `verify.sh` on purpose** (2026-11-02): the tree is over budget in 11 Python
files, in `HANDOVER.md` and in nine decision rows, so a hard check would be red for as long as
the split does not exist. A gate that is red on day one teaches people to ignore it — the same
reason `testing_hazards.md` §3.11 exists.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Bytes per token, for this repo's prose. Roughly 3.6, so a 180 KB file is ~50k tokens. Good
#: enough to make a budget legible; do not use it for anything else.
BYTES_PER_TOKEN = 3.6

#: §II of `build_principles.md`: no source file exceeds 30 KB. The cap the repo already claims
#: to hold; the list `--check` prints is the debt against it, measured 2026-11-02.
SOURCE_CAP_BYTES = 30 * 1024

SOURCE_GLOBS = (
    "core/**/*.py",
    "knowledge/**/*.py",
    "scripts/*.py",
    "pgs/**/*.py",
    "tests/**/*.py",
)

#: The current-state file a new session must read. Its budget is the hard one: every session
#: loads it and every session appends to it. 2,553 lines on 2026-11-02, of which ~72 are the
#: state and the rest is 22 sessions of history.
HANDOVER = REPO_ROOT / "HANDOVER.md"
HANDOVER_BUDGET_LINES = 250

#: The spec's decision table: 72 KB of the file's 172 KB is §18.3 rows, one per decision, and
#: the largest single row is 3.7 KB. Evidence belongs in the linked exploration, not here.
SPEC = REPO_ROOT / "product" / "backlog" / "Refinement" / "PGS_PLATFORM_SPEC.md"
DECISION_ROW_BUDGET_BYTES = 1500

#: One entry per file: `(path, why, mode)`. `mode` is what makes a recipe a budget rather than
#: a syllabus — **read** means the whole file, **search** means find the section and stop. Only
#: `read` entries are added up, because a 91 KB service file is not read whole; it is grepped.
READ, SEARCH = "read", "search"

TASKS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "chat": (
        ("HANDOVER.md", "read it whole now — 101 lines of state; history is in product/docs/handover/", READ),
        ("product/backlog/In Progress/CHAT_ANSWER_COVERAGE_PRD.md", "the gap you are closing", READ),
        ("product/docs/context/testing_hazards.md", "the refusal/retry headings only", SEARCH),
        ("core/services/_chatbot.py", "`COST_QUESTION_RULE`, `audit_citations`, `answer_question`", SEARCH),
    ),
    "corpus": (
        ("HANDOVER.md", "read it whole now — 101 lines of state", READ),
        ("knowledge/corpus.py", "the format docstring: rules 1-6", SEARCH),
        ("knowledge/tables.py", "`row_chunk`, `_embedding_rendition`, `chunks_for_parsed_section`", SEARCH),
        ("product/backlog/In Progress/CORPUS_CANONICAL_FORMAT_PLAN.md", "the plan and its gates", READ),
    ),
    "reader": (
        ("HANDOVER.md", "read it whole now — 101 lines of state", READ),
        ("product/design/DESIGN.md", "§7.13 for tables, §1 for the claim rules", SEARCH),
        ("core/services/_documents.py", "the three joins: branch, grid, structure", SEARCH),
        ("core/templates/public/document_reader.html", "the shapes", SEARCH),
    ),
    "public": (
        ("HANDOVER.md", "read it whole now — 101 lines of state", READ),
        ("product/design/content_inventory.md", "the live site is the content baseline", READ),
        ("core/services/_public.py", "the reviewed constants", SEARCH),
        ("product/backlog/In Progress/PUBLIC_BOARD_PRD.md", "only if the board is the change", SEARCH),
    ),
    "backlog": (
        ("product/backlog/backlog.md", "the generated index — not the PRDs", READ),
        ("product/backlog/CONVENTION.md", "the convention, once", READ),
    ),
}

#: The two files every session reads, and both are cheap on purpose.
ALWAYS: tuple[tuple[str, str, str], ...] = (
    ("AGENTS.md", "the rules that bite: claims, budgets, hazards", READ),
    ("product/docs/context/build_principles.md", "the non-negotiables — 13 KB, read whole", READ),
)

READ_SET = (
    "HANDOVER.md",
    "product/docs/context/build_principles.md",
    "product/docs/context/testing_hazards.md",
    "product/backlog/Refinement/PGS_PLATFORM_SPEC.md",
    "product/backlog/In Progress/MVP0_PRD.md",
    "product/backlog/ready/MVP1A_PRD.md",
)


def size_of(path: Path) -> tuple[int, int]:
    """In: a file. Out: `(lines, bytes)`, or `(0, 0)` when it is absent."""
    if not path.is_file():
        return 0, 0
    data = path.read_bytes()
    return data.count(b"\n") + 1, len(data)


def tokens(byte_count: int) -> int:
    """A legible estimate, not a measurement. Quoted to one significant figure."""
    return round(byte_count / BYTES_PER_TOKEN / 1000) * 1000


def show_sizes() -> None:
    print("The read-set AGENTS.md currently names\n")
    print(f"{'lines':>7} {'KB':>6} {'~tokens':>9}  file")
    total = 0
    for name in READ_SET:
        lines, size = size_of(REPO_ROOT / name)
        total += size
        print(f"{lines:>7} {size / 1024:>6.0f} {tokens(size):>9}  {name}")
    print(f"\n{'':>7} {total / 1024:>6.0f} {tokens(total):>9}  TOTAL")
    print(
        "\nThat is the number this file exists for: a session that reads the set whole has spent\n"
        "its budget before it has run a test. The recipes below are what replaces it."
    )


def show_task(task: str) -> None:
    entries = TASKS.get(task)
    if entries is None:
        print(f"no recipe for {task!r}; known: {', '.join(sorted(TASKS))}", file=sys.stderr)
        raise SystemExit(2)
    print(f"Read for a {task!r} task — in this order, and stop when the question is answered\n")
    run = 0
    for name, why, mode in (*ALWAYS, *entries):
        lines, size = size_of(REPO_ROOT / name)
        if mode == READ:
            run += size
        print(f"  {mode.upper():>6}  {size / 1024:>5.0f} KB  {lines:>5} lines  {name}\n              {why}")
    print(f"\n  read budget: {run / 1024:>5.0f} KB  ≈ {tokens(run):,} tokens")
    print("  A SEARCH entry is not read: find the section, stop, and name it in the handover.")


def check() -> int:
    """Report every budget breach. Exit 1 when any is broken (report-only today)."""
    broken: list[str] = []

    lines, _ = size_of(HANDOVER)
    if lines > HANDOVER_BUDGET_LINES:
        broken.append(
            f"HANDOVER.md is {lines} lines (budget {HANDOVER_BUDGET_LINES}): "
            f"{lines - HANDOVER_BUDGET_LINES} lines of history belong in product/docs/handover/"
        )

    over: list[tuple[int, str]] = []
    for pattern in SOURCE_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if not path.is_file():
                continue
            _, size = size_of(path)
            if size > SOURCE_CAP_BYTES:
                over.append((size, path.relative_to(REPO_ROOT).as_posix()))
    for size, name in sorted(over, reverse=True):
        broken.append(f"{name} is {size / 1024:.0f} KB (cap {SOURCE_CAP_BYTES // 1024} KB, §II)")

    if SPEC.is_file():
        rows = [
            line
            for line in SPEC.read_text(encoding="utf-8").splitlines()
            if line.startswith("| D") and line.count("|") >= 3
        ]
        for line in rows:
            if len(line) > DECISION_ROW_BUDGET_BYTES:
                ref = line.split("|")[1].strip()
                broken.append(
                    f"{ref} row is {len(line)} bytes (budget {DECISION_ROW_BUDGET_BYTES}): "
                    "its evidence belongs in the linked exploration or PRD"
                )

    print(f"context budgets — {len(broken)} breach(es)\n")
    for entry in broken:
        print(f"  - {entry}")
    if not broken:
        print("  every budget holds")
    print(
        "\nReport-only: these are the four cuts in CONTEXT_BUDGET.md, not a gate yet. "
        "Wire --check into verify.sh once the tree is inside the budgets."
    )
    return 1 if broken else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--task", help=f"what to read for one task: {', '.join(sorted(TASKS))}")
    parser.add_argument("--check", action="store_true", help="report every budget breach")
    args = parser.parse_args(argv)

    if args.check:
        return check()
    if args.task:
        show_task(args.task)
        return 0
    show_sizes()
    print("\nRecipes: " + ", ".join(f"--task {name}" for name in sorted(TASKS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
