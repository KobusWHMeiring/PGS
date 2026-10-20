"""Write a reviewer's exported sign-off back into the UAT markdown.

    python scripts/uat_runner.py --file tests/uat/mvp0_standards_and_public_site_uat.md
    # … a reviewer judges every scenario and downloads uat-<slug>-signoff.json …
    python scripts/uat_signoff.py --file tests/uat/mvp0_standards_and_public_site_uat.md \\
                                  --from ~/Downloads/uat-mvp0_standards_and_public_site-signoff.json \\
                                  --dry-run

**The UAT markdown stays the source of truth.** A signature that lives only in a
downloaded JSON file is a signature the backlog cannot read, so this writes exactly two
things and nothing else:

1. one `**Result:**` line per scenario, immediately after its `Judgement:` paragraph —
   `PASS`, `FAIL — reason` or `N/A — reason`, followed by the reviewer, the seat and the
   date, on a single line so a diff reads as a result rather than a paragraph;
2. a `### Per-scenario results` table at the end of the `## Sign-off` section, plus a
   `**Signed against:**` line naming the commit and database the reviewer was looking at.

Nothing else in the file changes — not a scenario's wording, not the existing role rows.
That is what makes the write-back reviewable: `--dry-run` prints a diff in which every
changed line is a result.

**It refuses rather than guesses.** A missing result, a `FAIL` with no reason, a name
with no date, a result for a scenario the file does not have, an export from another
file: each is named and the write does not happen. A half-applied sign-off is worse than
none, because the file would then claim judgements nobody made.

Re-running the same export changes nothing (idempotent): existing `**Result:**` lines are
replaced in place and the table is rebuilt from the export rather than appended to.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.uat_parse import (  # noqa: E402  (see the sys.path insert above)
    RESULT_LINE_RE,
    SIGNED_AGAINST_RE,
    Scenario,
    UatFile,
    UatFormatError,
    parse_uat,
)

KIND = "pgs-uat-signoff"
VERSION = 1
RESULTS_SECTION = "### Per-scenario results"
VALID_RESULTS = ("PASS", "FAIL", "N/A")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _one_line(text: str) -> str:
    """Collapse anything a reviewer typed into a single line a diff can show."""
    return " ".join(str(text).split())


def result_line(entry: dict) -> str:
    """The one line the write-back owns for a scenario.

    In: one result entry from the export.
    Out: `**Result:** PASS · Name (Role) · 2026-10-22` and, where the reviewer gave one,
         ` — reason; note`.
    Side Effects: none.
    Fails: never — `validate()` has already refused anything malformed.
    """
    reviewer = _one_line(entry.get("reviewer", ""))
    role = _one_line(entry.get("role", ""))
    who = f"{reviewer} ({role})" if role else reviewer
    line = f"**Result:** {entry['result']} · {who} · {_one_line(entry.get('date', ''))}"
    detail = "; ".join(
        part for part in (_one_line(entry.get("reason", "")), _one_line(entry.get("note", ""))) if part
    )
    return f"{line} — {detail}" if detail else line


def validate(uat: UatFile, export: dict) -> list[str]:
    """Every reason this export must not be applied. Empty list = apply it.

    The checks are deliberately redundant with the page's JavaScript guard. A guard that
    exists only in the browser is a guard the reviewer can bypass with devtools or a
    stale tab, and the file it writes is then evidence of nothing.
    """
    problems: list[str] = []

    if export.get("kind") != KIND:
        return [f"this is not a {KIND} file (kind: {export.get('kind')!r})"]
    if export.get("version") != VERSION:
        problems.append(f"export version {export.get('version')!r}, expected {VERSION}")
    if export.get("slug") != uat.slug:
        problems.append(
            f"the export is for {export.get('slug')!r} but this file is {uat.slug!r}"
        )
    if Path(str(export.get("file", ""))).name != uat.path.name:
        problems.append(
            f"the export names {export.get('file')!r} but this file is {uat.path.as_posix()!r}"
        )

    results = export.get("results")
    if not isinstance(results, list):
        return problems + ["the export carries no `results` list"]

    entries: dict[int, dict] = {}
    for entry in results:
        if not isinstance(entry, dict) or not isinstance(entry.get("number"), int):
            problems.append(f"a result entry has no scenario number: {entry!r}")
            continue
        number = entry["number"]
        if number in entries:
            problems.append(f"scenario {number} appears twice in the export")
        entries[number] = entry

    known = {s.number for s in uat.scenarios}
    for number in sorted(set(entries) - known):
        problems.append(f"the export judges scenario {number}, which this file does not have")
    for number in sorted(known - set(entries)):
        problems.append(f"scenario {number} has no result — a sign-off cannot leave a blank")

    for number in sorted(set(entries) & known):
        entry = entries[number]
        result = entry.get("result")
        if result not in VALID_RESULTS:
            problems.append(f"scenario {number}: result {result!r} is not one of {VALID_RESULTS}")
            continue
        if result in ("FAIL", "N/A") and not _one_line(entry.get("reason", "")):
            problems.append(f"scenario {number} is {result} but carries no reason")
        if not _one_line(entry.get("reviewer", "")):
            problems.append(f"scenario {number} has no reviewer name")
        if not DATE_RE.match(_one_line(entry.get("date", ""))):
            problems.append(f"scenario {number} has no date in YYYY-MM-DD form")

        scenario = uat.scenario(number)
        if scenario is not None and result == "N/A" and not scenario.not_applicable:
            # Not fatal: a reviewer may have been unable to run an applicable scenario.
            # It must not be silent, though — the release gate counts judged scenarios,
            # and this one is not judged.
            print(
                f"warning: scenario {number} is applicable but was marked N/A — record the "
                "decision that makes that acceptable, or the release gate is incomplete",
                file=sys.stderr,
            )

    return problems


def apply_export(uat: UatFile, export: dict) -> str:
    """Return the UAT file's full text with the results and the sign-off table applied.

    In: the parsed file and a validated export.
    Out: the new file text, ending as the original did.
    Side Effects: none — the caller writes.
    Idempotency: applying the same export twice yields the same text, because an
         existing `**Result:**` line is replaced rather than added to.
    Fails: never — `validate()` runs first and the caller stops on any problem.
    """
    lines = list(uat.lines)
    entries = {entry["number"]: entry for entry in export["results"]}

    # Bottom-up: an insertion shifts every later line, and the spans were computed
    # against the file as it is now.
    for scenario in sorted(uat.scenarios, key=lambda s: s.line_start, reverse=True):
        entry = entries[scenario.number]
        new_line = result_line(entry)
        existing = _existing_result_index(lines, scenario)
        if existing is not None:
            lines[existing] = new_line
        else:
            lines.insert(scenario.judgement_insert_at, new_line)

    _rebuild_signoff(lines, uat, export)
    text = "\n".join(lines)
    return f"{text}\n" if uat.newline_at_eof else text


def _existing_result_index(lines: list[str], scenario: Scenario) -> int | None:
    """The index of a `**Result:**` line already inside this scenario, if any."""
    for index in range(scenario.line_start, min(scenario.line_end, len(lines))):
        if RESULT_LINE_RE.match(lines[index]):
            return index
    return None


def _rebuild_signoff(lines: list[str], uat: UatFile, export: dict) -> None:
    """Drop any previous results block, then append a fresh one at the end of the file."""
    for index, line in enumerate(lines):
        if line.strip() == RESULTS_SECTION:
            del lines[index:]
            break
    for index, line in enumerate(lines):
        if SIGNED_AGAINST_RE.match(line):
            del lines[index:]
            break

    while lines and not lines[-1].strip():
        lines.pop()

    entries = {entry["number"]: entry for entry in export["results"]}
    rows = [
        "| Scenario | Category | Result | Reviewer | Role | Date |",
        "|---|---|---|---|---|---|",
    ]
    for scenario in sorted(uat.scenarios, key=lambda s: s.number):
        entry = entries[scenario.number]
        title = _one_line(scenario.title).replace("|", "\\|")
        if len(title) > 70:
            title = f"{title[:67]}…"
        rows.append(
            "| {n}. {title} | {category} | {result} | {reviewer} | {role} | {date} |".format(
                n=scenario.number,
                title=title,
                category=_one_line(scenario.category).replace("|", "\\|"),
                result=entry["result"],
                reviewer=_one_line(entry.get("reviewer", "")).replace("|", "\\|"),
                role=_one_line(entry.get("role", "")).replace("|", "\\|"),
                date=_one_line(entry.get("date", "")),
            )
        )

    counts = {value: sum(1 for e in entries.values() if e["result"] == value) for value in VALID_RESULTS}
    seats = sorted(
        {
            f"{_one_line(e.get('reviewer', ''))} ({_one_line(e.get('role', ''))})"
            if _one_line(e.get("role", ""))
            else _one_line(e.get("reviewer", ""))
            for e in entries.values()
        }
    )
    env = export.get("environment") or {}
    signed_against = (
        "**Signed against:** commit `{commit}` ({tree}), database `{database}`, "
        "generated {generated}.".format(
            commit=env.get("commit", "unknown"),
            tree=env.get("working_tree", "unknown"),
            database=env.get("database", "not stated"),
            generated=env.get("generated_on", "unknown"),
        )
    )
    summary = (
        f"**Results:** {counts['PASS']} PASS · {counts['FAIL']} FAIL · {counts['N/A']} N/A"
        f" — signed by {', '.join(seats)}."
    )

    lines.extend(["", RESULTS_SECTION, "", *rows, "", summary, "", signed_against])


def diff(before: str, after: str, path: Path) -> str:
    """A unified diff naming the file, so a reviewer can see exactly what would change."""
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
            n=2,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--file", required=True, help="Path to tests/uat/<slug>.md")
    parser.add_argument("--from", dest="source", required=True, help="Exported sign-off JSON ('-' for stdin)")
    parser.add_argument("--dry-run", action="store_true", help="Print the diff and write nothing")
    args = parser.parse_args(argv)

    path = Path(args.file)
    try:
        uat = parse_uat(path)
    except UatFormatError as exc:
        print("error: this UAT file cannot be read:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    try:
        raw = sys.stdin.read() if args.source == "-" else Path(args.source).read_text(encoding="utf-8")
        export = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: could not read the export: {exc}", file=sys.stderr)
        return 2

    problems = validate(uat, export)
    if problems:
        print("error: this export cannot be applied:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    before = path.read_text(encoding="utf-8")
    after = apply_export(uat, export)
    if before == after:
        print(f"uat:    {path.as_posix()} already carries this sign-off - nothing to change")
        return 0

    if args.dry_run:
        print(diff(before, after, path), end="")
        print(f"\n(dry run — {path.as_posix()} was not modified)")
        return 0

    # `newline="\n"`: a CRLF rewrite would show as a whole-file diff in review
    # (testing_hazards.md §1.27).
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(after)
    print(f"uat:    {path.as_posix()} - sign-off applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
