"""What a session must read, how big it is, and whether the tree is inside its budgets.

    python scripts/context.py                 # sizes of the read-set, and the recipes
    python scripts/context.py --task chat     # what to read for one kind of task
    python scripts/context.py --check         # report every budget breach (report-only today)

**Why this exists.** `AGENTS.md` used to say "read these first" and list every document a
session might need. Read whole, that set is ~340 KB, or roughly 100k tokens, before any work
starts. The numbers here are measured on every run; the budgets and the proposed cuts are in
`product/docs/context/CONTEXT_BUDGET.md`.

**Why the output is ASCII-only.** This tool is run from a Windows `cp1252` console as often as
from a POSIX shell. A `~` or a section sign in a printed string is a `UnicodeEncodeError` there,
which is how this script once failed at the exact moment it was meant to save context. Prose in
docstrings and comments may use the repo's typography; anything `print()`ed may not - and
`--help` is a print path, because argparse prints this docstring as its description. Every
printed string therefore goes through `ascii_fold()`, this page included.

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
#: loads it and every session appends to it. 2,553 lines on 2026-11-02, of which ~72 were the
#: state and the rest was session history.
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
        ("HANDOVER.md", "read it whole now - state only; history is in product/docs/handover/", READ),
        ("product/backlog/In Progress/CHAT_ANSWER_COVERAGE_PRD.md", "the gap you are closing", READ),
        ("product/docs/context/testing_hazards.md", "the refusal/retry headings only", SEARCH),
        ("core/services/_chat_prompt.py", "`SYSTEM_PROMPT`, `COST_QUESTION_RULE`, `build_prompt`", SEARCH),
        ("core/services/_chat_audit.py", "`audit_citations` and the two warning lists", SEARCH),
        ("core/services/_chat_provider.py", "`GeminiChatModel`, `ANSWER_SCHEMA`, the truncation retry", SEARCH),
        ("core/services/_chatbot.py", "`answer_question`, the cache, the refusal", SEARCH),
    ),
    "corpus": (
        ("HANDOVER.md", "read it whole now - state only", READ),
        ("knowledge/corpus.py", "the format docstring: rules 1-6", SEARCH),
        ("knowledge/corpus_tables.py", "`TableBlock`: rules 5 and the table state machine", SEARCH),
        ("knowledge/table_chunks.py", "`row_chunk`, `_embedding_rendition`, `chunks_for_parsed_section`", SEARCH),
        ("product/backlog/In Progress/CORPUS_CANONICAL_FORMAT_PLAN.md", "the plan and its gates", READ),
    ),
    "reader": (
        ("HANDOVER.md", "read it whole now - state only", READ),
        ("product/design/DESIGN.md", "section 7.13 for tables, section 1 for the claim rules", SEARCH),
        ("core/services/_document_reader.py", "the three joins: branch, search, citation", SEARCH),
        ("core/services/_document_shapes.py", "cards, the printed grid, the fee box", SEARCH),
        ("core/templates/public/document_reader.html", "the shapes", SEARCH),
    ),
    "public": (
        ("HANDOVER.md", "read it whole now - state only", READ),
        ("product/design/content_inventory.md", "the live site is the content baseline", READ),
        ("core/services/_public.py", "the reviewed constants", SEARCH),
        ("product/backlog/In Progress/PUBLIC_BOARD_PRD.md", "only if the board is the change", SEARCH),
    ),
    "backlog": (
        ("product/backlog/backlog.md", "the generated index - not the PRDs", READ),
        ("product/backlog/CONVENTION.md", "the convention, once", READ),
    ),
}

#: The two files every session reads, and both are cheap on purpose.
ALWAYS: tuple[tuple[str, str, str], ...] = (
    ("AGENTS.md", "the rules that bite: claims, budgets, hazards", READ),
    ("product/docs/context/build_principles.md", "the non-negotiables - 13 KB, read whole", READ),
)

READ_SET = (
    "HANDOVER.md",
    "product/docs/context/build_principles.md",
    "product/docs/context/testing_hazards.md",
    "product/backlog/Refinement/PGS_PLATFORM_SPEC.md",
    "product/backlog/In Progress/MVP0_PRD.md",
    "product/backlog/ready/MVP1A_PRD.md",
)


def ascii_fold(text: str) -> str:
    """Fold the repo's typography to ASCII for printing.

    The docstring says prose may keep `§`, an em dash and `≈` while printed output may not;
    `--help` sits on both sides of that line, so the fold happens at the boundary. Anything not
    in the table becomes `?` instead of a `UnicodeEncodeError` on a cp1252 console.
    """
    for char, replacement in _FOLD.items():
        text = text.replace(char, replacement)
    return text.encode("ascii", "replace").decode("ascii")


#: The characters this repo actually uses in prose. Order is irrelevant: none is a prefix of
#: another, so no replacement can be folded twice.
_FOLD = {
    "\u2014": "-",  # em dash
    "\u2013": "-",  # en dash
    "\u2248": "~",  # almost-equal, the read-budget marker
    "\u00a7": "section ",  # section sign: `§II` reads as `section II`
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u00d7": "x",
    "\u2192": "->",
}


def size_of(path: Path) -> tuple[int, int]:
    """In: a file. Out: `(lines, bytes)`, or `(0, 0)` when it is absent."""
    if not path.is_file():
        return 0, 0
    data = path.read_bytes()
    return data.count(b"\n") + 1, len(data)


def _where(path: Path) -> str:
    """A path as a reader sees it: relative to the repo when it is inside it."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def tokens(byte_count: int) -> int:
    """A legible estimate, not a measurement. Quoted to one significant figure."""
    return round(byte_count / BYTES_PER_TOKEN / 1000) * 1000


def show_sizes() -> None:
    print("The historical read-set (the old 'read these first' table, before the recipe)\n")
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
    print(f"Read for a {task!r} task - in this order, and stop when the question is answered\n")
    run = 0
    for name, why, mode in (*ALWAYS, *entries):
        lines, size = size_of(REPO_ROOT / name)
        if mode == READ:
            run += size
        print(f"  {mode.upper():>6}  {size / 1024:>5.0f} KB  {lines:>5} lines  {name}\n              {why}")
    print(f"\n  read budget: {run / 1024:>5.0f} KB  ~ {tokens(run):,} tokens")
    print("  A SEARCH entry is not read: find the section, stop, and name it in the handover.")


def check() -> int:
    """Report every budget breach. Exit 1 when any is broken.

    `scripts/verify.sh` runs this as its first step, so a breach is not a report any more:
    it fails the gate. That is why an **absent** file is a breach too — `size_of` returns
    `(0, 0)` for a path that is not there, so without this a deleted `HANDOVER.md` or spec
    would read as a file comfortably inside its budget, and the gate would pass on the
    artefact's absence.
    """
    broken: list[str] = []

    for path in (HANDOVER, SPEC):
        if not path.is_file():
            broken.append(
                f"{_where(path)} is missing: an absent file is not a file inside its budget"
            )

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
        broken.append(f"{name} is {size / 1024:.0f} KB (cap {SOURCE_CAP_BYTES // 1024} KB, section II)")

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

    print(f"context budgets - {len(broken)} breach(es)\n")
    for entry in broken:
        print(f"  - {entry}")
    if not broken:
        print("  every budget holds")
    print(
        "\nThese are the four cuts in CONTEXT_BUDGET.md, and scripts/verify.sh runs this "
        "check as its first step: a breach fails the gate."
    )
    return 1 if broken else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=ascii_fold(__doc__ or ""),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
