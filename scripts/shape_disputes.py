#!/usr/bin/env python
"""Which of the key's claims the measured arms disagree with — read off their own mismatch lines.

This is the *evidence* half of `scripts/shape_arbitration.py`, split out because it fails
differently: an attribution rule is wrong in a count, the page is wrong in a browser.

**Why the mismatch lines and not the stored reads.** Each arm's evidence JSON keeps only four
sampled rows per shape and clips cells at 200 characters (`testing_hazards.md` §3.31), so reading
a cell out of that file invents a defect the arm does not have. The `mismatches` list, by contrast,
is produced by `shape_fixtures.mismatches()` against the **whole** read, so its lines are exact
statements about the arm — and each line names its own claim.

**The rule is narrow and named.** A line is `"<shape>: <what went wrong>"`, and only five shapes of
sentence occur (`row pages`, `row R cell C`, `N rows, the page prints`, `columns`, `dividers`). A
line that matches none of them is `None` — deliberately, because `the extractor returned no table`
is a statement about the arm, not about a claim we can arbitrate.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The arms and the evidence each one's score came from, newest first. `None` selects every
#: result in the file; a string keeps only the rows whose `model` contains it (and, for the VLM
#: arm, only the `lines` form — the form that is closest to passing, so the one where a key
#: defect is most likely to be hiding a pass).
ARMS: tuple[tuple[str, str, str | None], ...] = (
    ("docling 2.146.0", "2026-11-05_s2_rescore_docling.json", None),
    ("documentai form21", "2026-11-05_s2_rescore_documentai.json", "form21"),
    ("documentai layout16pro", "2026-11-05_s2_rescore_documentai.json", "layout16pro"),
    ("vlm claude-sonnet-5.5 lines", "2026-11-05_s2b_rescore_openrouter.json", "claude"),
    ("vlm gemini-3.1-flash-lite lines", "2026-11-05_s2b_rescore_openrouter.json", "flash"),
)

EVIDENCE_DIR = REPO_ROOT / "product" / "docs" / "evidence"

_CELL = re.compile(r"^row (\d+) cell (\d+) ")
_ROW_COUNT = re.compile(r"^\d+ rows, the page prints \d+")
_NO_TABLE = re.compile(r"returned no table")
_DIVIDER = re.compile(r"\((\d+), '[^']*', '(\w+)'\)")


@dataclass(frozen=True)
class Arm:
    """One measured reader, and what it said about each shape.

    `lines` is the reading the arm can *reach under the declared normalisations*: when the
    paper's row-number gutter had to be dropped, the guttered tier is the one attributed, because
    the gutter is a declared convention (`scripts/table_reads.py`) and not an arm defect. Reading
    `as_extracted` instead reports the gutter itself as five arms disagreeing with the key — which
    is exactly what the first run of this module did on Appendix 7.
    """

    name: str
    file: str
    lines: dict[str, tuple[str, ...]]
    #: Shapes this arm returned no table for at all.
    blind: tuple[str, ...]
    #: Shapes this arm passes outright under the declared normalisations. A shape one arm passes
    #: is not a key dispute: the claim is demonstrably satisfiable, and the others' failure is a
    #: tool finding. A shape *no* arm passes is the set a human has to arbitrate.
    passed: frozenset[str]

    def verdict(self, shape: str) -> str:
        return "no table found" if shape in self.blind else f"{len(self.lines.get(shape, ()))} mismatches"


def attributed_tier(result: dict) -> dict:
    """The reading whose mismatches are attributable: guttered when the gutter took rows out."""
    guttered = result.get("with_row_number_gutter") or {}
    if result.get("row_number_gutter_rows") and guttered.get("mismatches") is not None:
        return guttered
    return result.get("as_extracted") or {}


def passes(result: dict) -> bool:
    """Does this arm read the shape correctly — by the instrument's own verdict?

    The published scoreboard counts a shape passed once a declared convention repairs it (`pass
    (needs row-number gutter)`, `pass (needs header convention)`), and does **not** count `pass (grid
    only, quotes unresolved)` — the characters are unverified, so the claim is not demonstrated. The
    rule is stated here rather than inferred from the tier, because the tiers disagree: the VLM's
    `as_extracted` block says `pass` for a shape whose overall verdict is grid-only.
    """
    verdict = result.get("verdict") or ""
    return verdict.startswith("pass") and "grid only" not in verdict        

@dataclass(frozen=True)
class Disagreement:
    """One claim of the key, and the arms whose own report contradicts it."""

    claim_id: str
    arms: tuple[tuple[str, str], ...]

    @property
    def count(self) -> int:
        return len(self.arms)


def attribute(shape: str, line: str) -> tuple[str, ...]:
    """The claim ids a mismatch line names. Empty when the line names the arm, not a claim.

    One line can name several claims: `dividers` is a single comparison of the whole tuple, so it
    is attributed to every divider id discovered in the expected side rather than to a claim id
    that does not exist.
    """
    prefix = f"{shape}: "
    if not line.startswith(prefix):
        return ()
    body = line[len(prefix) :]
    if body.startswith("row pages"):
        return (f"{shape}.pages",)
    cell = _CELL.match(body)
    if cell:
        return (f"{shape}.cell.{cell.group(1)}.{cell.group(2)}",)
    if _ROW_COUNT.match(body):
        return (f"{shape}.rows",)
    if body.startswith("columns "):
        return (f"{shape}.header",)
    if body.startswith("dividers "):
        return tuple(f"{shape}.divider.{row}.{kind}" for row, kind in _DIVIDER.findall(body))
    return ()


def _results(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["results"]


def load_arms(arms=ARMS, evidence_dir: Path = EVIDENCE_DIR) -> tuple[Arm, ...]:
    """Every arm's mismatch lines by shape. A missing evidence file is an error, not a skip."""
    loaded: list[Arm] = []
    for name, filename, match in arms:
        path = evidence_dir / filename
        lines: dict[str, list[str]] = {}
        blind: list[str] = []
        won: list[str] = []
        for result in _results(path):
            if match is not None and match not in (result.get("model") or ""):
                continue
            if "openrouter" in filename and result.get("mode") != "lines":
                continue
            shape = result["shape"]
            if passes(result):
                # An arm that reads the shape correctly under the declared normalisations does not
                # disagree with a claim in it, whatever its as-extracted tier says: the gutter and
                # the header row are conventions the key declares, so scoring them against the arm
                # would report the convention itself as a disagreement (the VLM's Appendix 7 read
                # is exactly this case — `pass (needs row-number gutter)` with the raw tier failing
                # six cells).
                won.append(shape)
                continue
            block = attributed_tier(result)
            for line in block.get("mismatches") or ():
                lines.setdefault(shape, []).append(line)
            for line in block.get("mismatches") or ():
                if _NO_TABLE.search(line):
                    blind.append(shape)
        loaded.append(
            Arm(
                name=name,
                file=filename,
                lines={k: tuple(v) for k, v in lines.items()},
                blind=tuple(blind),
                passed=frozenset(won),
            )
        )
    return tuple(loaded)


def disagreements(
    arms: tuple[Arm, ...], threshold: int = 2, unsatisfied_only: bool = True
) -> tuple[Disagreement, ...]:
    """Claims at least `threshold` arms contradict, in claim-id order.

    `unsatisfied_only` drops claims whose shape *some* arm passes: those are tool findings, not
    questions for the key's owner, and mixing them in makes the surface look like 30 problems when
    the key has three.
    """
    found: dict[str, list[tuple[str, str]]] = {}
    for arm in arms:
        for shape, lines in arm.lines.items():
            for line in lines:
                for claim_id in attribute(shape, line):
                    found.setdefault(claim_id, []).append((arm.name, line))
    satisfied = set().union(*(arm.passed for arm in arms)) if arms else set()
    return tuple(
        Disagreement(claim_id=claim_id, arms=tuple(sorted(found[claim_id])))
        for claim_id in sorted(found)
        if len(found[claim_id]) >= threshold
        and (not unsatisfied_only or claim_id.split(".")[0] not in satisfied)
    )


def main() -> int:
    arms = load_arms()
    for arm in arms:
        print(f"{arm.name:34s} {sum(len(v) for v in arm.lines.values()):3d} mismatch lines, blind on {len(arm.blind)}")
    print()
    for item in disagreements(arms):
        print(f"{item.count}/{len(arms)}  {item.claim_id}")
        for arm_name, line in item.arms:
            print(f"    {arm_name}: {line[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
