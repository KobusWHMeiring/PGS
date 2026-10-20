"""Read a UAT file, and refuse to present one that breaks the judgement contract.

This module is the only thing that understands the shape of `tests/uat/*.md`. The
runner and the write-back script both consume `UatFile`, so the file's format is
defined once, in code, instead of three times in three regexes.

**Why it refuses rather than copes.** A UAT card with no `Judgement:` clause is an
automated test wearing a checklist costume — the exact failure the
`writing-uat-tests` skill exists to prevent, and the one thing a sign-off tool must
never present. So a missing judgement is a hard error with the scenario named, not a
warning and not an empty card. Same for a scenario number that appears twice: the
sign-off writes back by number, and a duplicate would silently record one result
against two scenes.

**Why the applicability scan lives here (2026-10-22).** An N/A scenario outlives the
decision that made it N/A unless something checks. Scenario 5 is not applicable
*because* D44 deferred the bilingual shell; when C3 is picked up, D44's resolution in
`PGS_PLATFORM_SPEC.md` §18.3 stops saying "deferred" — and if nothing failed at that
moment, the runner would keep printing a greyed-out card for a scenario that had
become deliverable, and the release gate would keep passing on nine judged scenarios
when ten were required. `scan_applicability()` is that check:

1. an N/A scenario must cite a decision id (`D<n>`), machine-readably;
2. that id must exist in §18.3;
3. its resolution must still read as a deferral;
4. every scenario must carry a `Judgement:` clause.

It is deliberately deterministic. A model cannot answer "is this still applicable?"
— the answer has to be reproducible from the commit, or a signature written against
it is not evidence of anything. This is the same reasoning as HANDOVER §4's "do not
add a classifier": prefer a checkable rule to an ungrounded call.

Pure: no Django, no network, no writes. Text in, dataclasses out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: A level-2 heading. `## Scenario 4 — …`, `## Sign-off`, `## Automated coverage …`.
H2_RE = re.compile(r"^##\s+(.*?)\s*$")

#: `## Scenario 4 — Does the public site read as *the group's* site?`
SCENARIO_H2_RE = re.compile(r"^Scenario\s+(\d+)\s+[—–-]\s+(.*)$")

#: `**Judgement:** …`, `**Observed 2026-10-20 (dev box):** …`. The label may not
#: contain an asterisk, so an emphasised phrase is never mistaken for a label.
LABEL_RE = re.compile(r"^\*\*([^*]+?):\*\*\s?(.*)$")

#: `1. Ask: …` — a scenario step.
STEP_RE = re.compile(r"^(\d+)\.\s+(.*)$")

#: `| D44 | C3 (bilingual shell) — in MVP 0 or not? | **Deferred …** |`
DECISION_ROW_RE = re.compile(r"^\|\s*(D\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")

#: `\bD44\b` inside a scenario's `**Status:**` field.
DECISION_CITE_RE = re.compile(r"\bD(\d+)\b")

#: A word that marks a decision's resolution as still deferring something. Deliberately
#: a small explicit list: a resolution that says none of these has moved, and the
#: scenario must be re-judged by a person rather than staying silently greyed out.
DEFERRAL_MARKERS = (
    "deferred",
    "not applicable",
    "out of mvp",
    "out of scope",
    "withheld",
    "post-mvp",
)

#: The scenario is not applicable. Matched against the `**Status:**` field only, so a
#: phrase in prose ("that case is not applicable to a smallholding") cannot flip a card.
NOT_APPLICABLE_RE = re.compile(r"not\s+applicable", re.IGNORECASE)

#: The `**Result:**` line the write-back owns. `**Result:** PASS · Name (Role) · date — note`
RESULT_LINE_RE = re.compile(r"^\*\*Result:\*\*")

#: The `**Signed against:**` line the write-back owns.
SIGNED_AGAINST_RE = re.compile(r"^\*\*Signed against:\*\*")

#: Everything the runner must never present. The PRD (§3) is explicit: rendering the
#: automated rows as checklist items is the failure the skill exists to prevent.
AUTOMATED_COVERAGE_H2 = "automated coverage"


class UatFormatError(Exception):
    """The UAT file cannot be presented. Carries every problem found, not the first.

    Reporting one problem at a time means the reviewer fixes a file, re-runs, and finds
    the next — so the message lists them all.
    """

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


@dataclass(frozen=True)
class Scenario:
    """One judged scene, with the line spans the write-back needs.

    `line_start`/`line_end` are **0-based**, `line_start` inclusive and `line_end`
    exclusive, so they index the original file's `lines` list directly.

    `judgement_insert_at` is the 0-based index a `**Result:**` line belongs at —
    immediately after the last line of the `Judgement:` paragraph, before whatever follows
    it (a recorded observation, a rule, the closing `---`). `uat_signoff.py` inserts there
    and applies its edits bottom-up, so earlier indices stay valid.
    """

    number: int
    title: str
    category: str
    setup: str
    steps: tuple[str, ...]
    expected: str
    judgement: str
    status: str
    notes: tuple[tuple[str, str], ...]
    result: str
    line_start: int
    line_end: int
    judgement_insert_at: int

    @property
    def not_applicable(self) -> bool:
        return bool(NOT_APPLICABLE_RE.search(self.status))

    @property
    def cited_decisions(self) -> tuple[str, ...]:
        """Every `D<n>` in the status field, normalised to `D<n>`."""
        return tuple(f"D{m}" for m in DECISION_CITE_RE.findall(self.status))


@dataclass(frozen=True)
class UatFile:
    """A parsed UAT document. `lines` is the file as it stood, for the write-back."""

    path: Path
    slug: str
    title: str
    plan: str
    prd: str
    status: str
    date: str
    purpose: str
    pre_test_setup: str
    scenarios: tuple[Scenario, ...]
    lines: tuple[str, ...]
    newline_at_eof: bool

    @property
    def applicable(self) -> tuple[Scenario, ...]:
        return tuple(s for s in self.scenarios if not s.not_applicable)

    @property
    def not_applicable(self) -> tuple[Scenario, ...]:
        return tuple(s for s in self.scenarios if s.not_applicable)

    def scenario(self, number: int) -> Scenario | None:
        for candidate in self.scenarios:
            if candidate.number == number:
                return candidate
        return None


# --------------------------------------------------------------------------- parse


def _segments(lines: list[str], first: int, last: int) -> list[tuple[str | None, int, list[str]]]:
    """Split a section body into `(label, start_line, lines)` segments.

    A fenced code block is opaque: a `**Something:**` line inside a shell snippet is
    part of the snippet, not a field. Without this the runner would treat an example
    command's `**# expect:**` comment as a heading of the card.
    """
    segments: list[tuple[str | None, int, list[str]]] = []
    label: str | None = None
    start = first
    body: list[str] = []
    fenced = False

    for index in range(first, last):
        line = lines[index]
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced:
            match = LABEL_RE.match(line)
            if match:
                segments.append((label, start, body))
                label, start, body = match.group(1).strip(), index, [match.group(2)]
                continue
        body.append(line)

    segments.append((label, start, body))
    return segments


def _join(body: list[str]) -> str:
    """Collapse a soft-wrapped markdown paragraph to one line, keeping fences intact."""
    out: list[str] = []
    fenced = False
    for line in body:
        if line.startswith("```"):
            fenced = not fenced
            out.append(line)
            continue
        if fenced:
            out.append(line)
            continue
        stripped = line.strip()
        if not stripped:
            if out and out[-1] != "":
                out.append("")
            continue
        if out and out[-1] not in ("",) and not stripped.startswith(("* ", "- ")):
            out[-1] = f"{out[-1]} {stripped}"
        else:
            out.append(stripped)
    return "\n".join(out).strip()


def _split_at_first_step(body: list[str]) -> tuple[list[str], list[str]]:
    """Cut a segment body where its numbered steps begin, outside any fence.

    Steps follow `**Setup:**` with no label of their own — in several scenarios the
    setup paragraph, a fenced command and the steps are one segment. Without this cut
    the setup text swallows the steps and the card renders a wall of prose with no
    ordered actions, which is precisely the part the reviewer works from.
    """
    fenced = False
    for index, line in enumerate(body):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if not fenced and STEP_RE.match(line.strip()):
            return body[:index], body[index:]
    return body, []


def _steps(body: list[str]) -> tuple[str, ...]:
    """Numbered steps from a body, joining continuation lines onto the step they follow.

    The scenarios' steps are hard-wrapped prose, so splitting on the wrap would cut a
    step in half at exactly the point the reviewer needs the detail. A blank line ends
    a step; a `3.` starts the next.
    """
    found: list[str] = []
    current: str | None = None
    fenced = False
    for line in body:
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = STEP_RE.match(line.strip())
        if match:
            if current is not None:
                found.append(current)
            current = match.group(2).strip()
        elif current is not None and line.strip():
            current = f"{current} {line.strip()}"
        elif current is not None:
            found.append(current)
            current = None
    if current is not None:
        found.append(current)
    return tuple(found)


def parse_uat(path: Path) -> UatFile:
    """Parse one UAT markdown file. Raises `UatFormatError` with every problem found.

    In: `path` — a `tests/uat/*.md`.
    Out: `UatFile` with every scenario, its line spans and its existing result line.
    Side Effects: reads the file.
    Fails: `UatFormatError` when the file cannot be presented faithfully — no
         scenarios, duplicate numbers, a scenario with no `Judgement:`.
    """
    text = path.read_text(encoding="utf-8")
    newline_at_eof = text.endswith("\n")
    lines = text.splitlines()

    headings = [(i, H2_RE.match(line).group(1)) for i, line in enumerate(lines) if H2_RE.match(line)]
    problems: list[str] = []

    def section(name: str) -> tuple[int, int] | None:
        for position, (index, title) in enumerate(headings):
            if title.lower().startswith(name):
                end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
                return index, end
        return None

    meta: dict[str, str] = {}
    for line in lines[: headings[0][0] if headings else 0]:
        match = LABEL_RE.match(line)
        if match:
            meta[match.group(1).strip().lower()] = match.group(2).strip()

    slug = meta.get("feature slug", "").strip("`").strip()
    if not slug:
        # The slug is the artefact's filename and the export's identity; guessing it from
        # the title would produce a file the sign-off can no longer match to its source.
        problems.append("the header has no `**Feature slug:**` line")

    title = next(
        (line.lstrip("# ").strip() for line in lines if line.startswith("# ")),
        "",
    )

    purpose_span = section("purpose")
    purpose = _join(lines[purpose_span[0] + 1 : purpose_span[1]]) if purpose_span else ""

    setup_span = section("pre-test setup")
    pre_test_setup = _join(lines[setup_span[0] + 1 : setup_span[1]]) if setup_span else ""

    scenarios: list[Scenario] = []
    seen: dict[int, str] = {}
    for position, (index, heading) in enumerate(headings):
        match = SCENARIO_H2_RE.match(heading)
        if not match:
            continue
        number = int(match.group(1))
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        # A `---` rule closes the section; it is not part of the block the write-back owns.
        while end > index + 1 and lines[end - 1].strip() in ("", "---"):
            end -= 1

        if number in seen:
            problems.append(
                f"Scenario {number} appears twice (also “{seen[number]}”); the sign-off "
                "writes back by number, so a duplicate would record one result twice"
            )
        seen[number] = match.group(2)

        segments = _segments(lines, index + 1, end)
        fields: dict[str, str] = {}
        notes: list[tuple[str, str]] = []
        steps: list[str] = []
        # Steps run from the setup paragraph to `**Expected:**`. A numbered list after
        # that is part of what the reviewer should see, not an action to perform.
        steps_open = True
        judgement_insert_at = index + 1
        for label, _start, body in segments:
            if label is None:
                if steps_open:
                    steps.extend(_steps(body))
                continue
            key = label.lower()
            if key in ("expected", "judgement"):
                steps_open = False
            if key == "setup" and steps_open:
                prose, step_body = _split_at_first_step(body)
                fields[key] = _join(prose)
                steps.extend(_steps(step_body))
                continue
            joined = _join(body)
            if key in ("category", "setup", "expected", "judgement", "status", "result"):
                fields[key] = joined
                if key == "judgement":
                    # `_start` is the 0-based index of the label line and `body[0]` is the
                    # text on it, so body[n] sits on line `_start + n`. The result line
                    # goes after the last non-blank one.
                    last = _start
                    for offset, raw in enumerate(body):
                        if raw.strip():
                            last = _start + offset
                    judgement_insert_at = last + 1
            else:
                notes.append((label, joined))

        judgment = fields.get("judgement", "").strip()
        if not judgment:
            # The gate. Named, not counted, so the author knows which scene to fix.
            problems.append(
                f"Scenario {number} (“{match.group(2)}”) has no `Judgement:` clause — "
                "an item without one is an automated test, not UAT"
            )

        scenarios.append(
            Scenario(
                number=number,
                title=match.group(2).strip(),
                category=fields.get("category", "").strip(),
                setup=fields.get("setup", "").strip(),
                steps=tuple(steps),
                expected=fields.get("expected", "").strip(),
                judgement=judgment,
                status=fields.get("status", "").strip(),
                notes=tuple((label, body) for label, body in notes if body),
                result=fields.get("result", "").strip(),
                line_start=index,
                line_end=end,
                judgement_insert_at=judgement_insert_at,
            )
        )

    if not scenarios:
        problems.append("no `## Scenario N — …` sections were found")

    if problems:
        raise UatFormatError(problems)

    scenarios.sort(key=lambda s: s.number)

    return UatFile(
        path=path,
        slug=slug,
        title=title,
        plan=meta.get("plan", ""),
        prd=meta.get("prd", ""),
        status=meta.get("status", ""),
        date=meta.get("date", ""),
        purpose=purpose,
        pre_test_setup=pre_test_setup,
        scenarios=tuple(scenarios),
        lines=tuple(lines),
        newline_at_eof=newline_at_eof,
    )


# ----------------------------------------------------------------------- decisions


def parse_decisions(spec_text: str) -> dict[str, str]:
    """Every `| D<n> | question | resolution |` row in the spec's §18.3 table.

    In: the text of `PGS_PLATFORM_SPEC.md`.
    Out: `{"D44": "<resolution text>", …}`. The **last** row wins if an id repeats,
         because that is the row a reader would act on — but a repeat is a defect, and
         `scan_applicability()` reports it.
    Side Effects: none.
    Fails: never.
    """
    decisions: dict[str, str] = {}
    for line in spec_text.splitlines():
        match = DECISION_ROW_RE.match(line)
        if match:
            decisions[match.group(1)] = match.group(3)
    return decisions


def duplicate_decisions(spec_text: str) -> tuple[str, ...]:
    """Decision ids that appear in more than one §18.3 row. Sorted, for a stable message."""
    seen: dict[str, int] = {}
    for line in spec_text.splitlines():
        match = DECISION_ROW_RE.match(line)
        if match:
            seen[match.group(1)] = seen.get(match.group(1), 0) + 1
    return tuple(sorted(k for k, v in seen.items() if v > 1))


def scan_applicability(uat: UatFile, decisions: dict[str, str]) -> list[str]:
    """The applicability scan: is each N/A still justified by a live decision?

    In: a parsed `UatFile` and the spec's §18.3 decisions.
    Out: a list of problems, each naming the scenario and what to do. Empty = clean.
    Side Effects: none.
    Fails: never — the caller decides whether a problem stops the run.
    """
    problems: list[str] = []
    for scenario in uat.not_applicable:
        cited = scenario.cited_decisions
        if not cited:
            problems.append(
                f"Scenario {scenario.number} is marked not applicable but its `**Status:**` "
                "line cites no decision (expected e.g. “decision **D44**”), so nothing can "
                "tell when it became applicable again"
            )
            continue
        for decision in cited:
            resolution = decisions.get(decision)
            if resolution is None:
                problems.append(
                    f"Scenario {scenario.number} cites {decision}, which is not a row in "
                    "PGS_PLATFORM_SPEC.md §18.3"
                )
                continue
            lowered = resolution.lower()
            if not any(marker in lowered for marker in DEFERRAL_MARKERS):
                problems.append(
                    f"Scenario {scenario.number} is marked not applicable because of {decision}, "
                    "but that decision no longer reads as a deferral — re-judge the scenario "
                    "and remove its `**Status:**` line, or record a new decision that defers it"
                )
    return problems
