#!/usr/bin/env python3
"""board.py — render the *published* backlog into the artefact the site reads.

The board at `/building/` is a **release artefact**, not a live view of `product/backlog/`
(`PUBLIC_BOARD_PRD.md` §3, D74b). This script is the whole of publishing:

    python scripts/board.py            # write core/services/_board_data.py
    python scripts/board.py --check    # verify the committed artefact matches its source

Run it before a push that will be deployed. `deploy/deploy.sh` runs `--check` before it backs
up anything, so a stale board aborts the deploy rather than shipping.

**Zero Django.** The artefact is a module of plain tuples; the typed shape and the column
titles live in `core/services/_board.py`, which is the only thing that imports it. That keeps
this script runnable on a box with no settings, no database and no virtualenv.

**Three refusals, each because the alternative is silent:**

1. an opted-in PRD that cannot become a card (no summary, over 180 characters, or a
   directory with no column) — a silent drop would make the board look complete;
2. a summary containing a claim-discipline term (`FORBIDDEN_CLAIMS`), which would fail the
   build one gate later and be much harder to trace from there;
3. `--check` on an artefact whose bytes differ from what the tree would produce now.

**No timestamp is written into the artefact, deliberately.** A generated-at line changes on
every run, so `--check` would fail on a tree nobody touched, and the obvious fix — ignore that
line — is a comparison with a hole in it. The digest identifies the content; git identifies
when.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTEFACT = REPO_ROOT / "core" / "services" / "_board_data.py"

sys.path.insert(0, str(REPO_ROOT))
from core.services._public import FORBIDDEN_CLAIMS  # noqa: E402  (needs REPO_ROOT on the path)

#: Display order. The *titles* live in `core/services/_board.py`, so renaming a column does
#: not need a regeneration; the order is structural, so it does.
COLUMN_ORDER: tuple[str, ...] = ("refinement", "ready", "in_progress", "done")

#: "Shipped" is a recent-history column, not an archive. Six is a board, sixty is a changelog.
DONE_LIMIT = 6


def _display(path: Path) -> str:
    """The path as a human reads it: repo-relative when it is in the repo, else absolute.

    The tests point `ARTEFACT` at `tmp_path`, and `relative_to()` raises on a path outside
    the repo — during a *failure* message, which is the worst possible time to raise.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_backlog_module():
    """`product/backlog.py`, loaded **by path**.

    Never `sys.path.insert(0, "product"); import backlog`: `product/` holds both `backlog.py`
    and `backlog/`, and the module wins only because `backlog/` has no `__init__.py`. Adding
    one would flip the import to the package and silently change what `scan()` reads.
    """
    path = REPO_ROOT / "product" / "backlog.py"
    spec = importlib.util.spec_from_file_location("pgs_backlog", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["pgs_backlog"] = module
    spec.loader.exec_module(module)
    return module


def arrange(cards):
    """Order and cap, deterministically.

    In:  the `cards` list from `board_payload()`.
    Out: a tuple in column order; `Shipped` newest first and capped; every other column by
         title. Cards lose `rel` on the way out — a path is not something a public module
         carries.
    Side effects: none.
    """
    buckets: dict[str, list[dict]] = {key: [] for key in COLUMN_ORDER}
    for card in cards:
        if card["column"] in buckets:
            buckets[card["column"]].append(card)

    ordered: list[dict] = []
    for key in COLUMN_ORDER:
        group = buckets[key]
        if key == "done":
            # Newest first; the date comes from the PRD's own header, never from an mtime —
            # a checkout's mtime is the clone time, so this would reorder on every deploy.
            group.sort(key=lambda card: (card["updated"], card["title"].lower()), reverse=True)
            group = group[:DONE_LIMIT]
        else:
            group.sort(key=lambda card: (card["title"].lower(), card["rel"]))
        ordered.extend(group)

    return tuple(
        {key: card[key] for key in ("title", "summary", "column", "updated")} for card in ordered
    )


def claim_violations(cards) -> list[str]:
    """One message per card whose summary uses a term the group may not claim.

    The page is swept a second time by `core/tests/test_claim_discipline.py`, and that sweep is
    the load-bearing one. This check exists so the failure arrives while the summary is being
    written — with the file named — instead of as a red public test in another module.
    """
    found = []
    for card in cards:
        haystack = card["summary"].lower()
        for term in FORBIDDEN_CLAIMS:
            if term in haystack:
                found.append(
                    f"{card['rel']}: summary contains {term!r}. The public surface may not "
                    f"make that claim — see `core/services/_public.py` FORBIDDEN_CLAIMS."
                )
    return found


def build_source(payload, *, done_limit: int = DONE_LIMIT) -> str:
    """The artefact's text, as a pure function of the payload.

    In:  a `board_payload()` dict.
    Out: the exact bytes `ARTEFACT` should hold. `--check` compares against this, so it must
         be deterministic: no timestamp, no environment, no set iteration.
    Side effects: none.
    """
    arranged = arrange(payload["cards"])

    lines = [
        '"""The public board\'s published set — GENERATED, do not edit by hand.',
        "",
        "Written by `scripts/board.py` from the `**Public:** yes` PRDs under",
        "`product/backlog/`. Regenerate before a push that will be deployed:",
        "",
        "    python scripts/board.py",
        "",
        "`scripts/board.py --check` (and `deploy/deploy.sh`, before it backs anything up)",
        "fails when this file disagrees with the tree, so a stale board aborts the deploy",
        "instead of shipping. Remove a card by deleting its `**Public:** yes` line and",
        "regenerating — never by editing this file.",
        "",
        "The shape and the column titles are `core/services/_board.py`'s; this module is data.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        f"SOURCE_DIGEST = {payload['digest']!r}",
        "",
        f"COLUMN_ORDER: tuple[str, ...] = {COLUMN_ORDER!r}",
        "",
        "#: (title, summary, column, updated) — one sentence per card, no paths, no statuses,",
        "#: no owners. `updated` orders the Shipped column and is never rendered.",
        "CURATED: tuple[dict[str, str], ...] = (",
    ]
    for card in arranged:
        lines.append("    {")
        for key in ("title", "summary", "column", "updated"):
            lines.append(f"        {key!r}: {card[key]!r},")
        lines.append("    },")
    if not arranged:
        lines.append("    # Nothing is marked `**Public:** yes` — the page says so rather than")
        lines.append("    # rendering an empty board.")
    lines.append(")")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None, *, module=None) -> int:
    """Write or verify the artefact. Returns a process exit code; prints why it failed.

    `module` is injectable so the tests can point the real `product/backlog.py` at a fixture
    tree without monkeypatching a loader that `main` would have to remember to call.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed artefact matches the tree; write nothing",
    )
    args = parser.parse_args(argv)

    module = module or load_backlog_module()
    payload = module.board_payload()

    refused = [
        f"{entry['rel']}: {entry['reason']}" for entry in payload["rejected"]
    ] + claim_violations(payload["cards"])
    if refused:
        print("Refusing to build the board:\n", file=sys.stderr)
        for problem in refused:
            print(f"  {problem}", file=sys.stderr)
        print(
            f"\n{len(refused)} problem(s). A published card must be a future a visitor can "
            f"read, so this is a failure, not a filter.",
            file=sys.stderr,
        )
        return 1

    source = build_source(payload)
    cards = arrange(payload["cards"])

    if args.check:
        if not ARTEFACT.is_file():
            print(f"{_display(ARTEFACT)} is missing. Run: python scripts/board.py", file=sys.stderr)
            return 1
        if ARTEFACT.read_text(encoding="utf-8") != source:
            print(
                f"{_display(ARTEFACT)} is stale — the backlog has changed since it "
                f"was generated.\nRun: python scripts/board.py",
                file=sys.stderr,
            )
            return 1
        print(f"{_display(ARTEFACT)} matches the tree ({len(cards)} card(s)).")
        return 0

    ARTEFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTEFACT.write_text(source, encoding="utf-8", newline="\n")
    print(f"Wrote {_display(ARTEFACT)} — {len(cards)} card(s), {payload['digest'][:19]}…")
    if not cards:
        print("  (no PRD carries `**Public:** yes` — the page will say so)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
