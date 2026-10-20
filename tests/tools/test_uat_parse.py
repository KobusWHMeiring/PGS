"""The UAT format, the `Judgement:` gate, and the applicability scan.

Three properties are load-bearing and each is tested by breaking it rather than by
asserting it holds:

* a scenario with no `Judgement:` stops the run and is **named** (the gate);
* an N/A scenario must cite a decision that exists **and still defers** — the check that
  stops a greyed-out card outliving the decision that greyed it out;
* the real `tests/uat/` files parse, and their scenario counts are pinned so a scenario
  silently flipping to N/A (or disappearing) is a failing test rather than a quiet
  change to what a reviewer is asked to sign.
"""

from __future__ import annotations

import pytest

from scripts.uat_parse import (
    UatFormatError,
    duplicate_decisions,
    parse_decisions,
    parse_uat,
    scan_applicability,
)

from .conftest import REAL_SPEC, REAL_UAT

HEADER = """# Test UAT — An example

**Feature slug:** `example_feature`
**Plan:** `plan.md`
**PRD:** `prd.md`
**Status:** Drafted
**Date:** 2026-01-01

---

## Purpose of this document

Only checks a human must judge.

---

## Pre-test setup

1. Run the app.

---

## Automated coverage (NOT UAT — asserted by the suite)

| What | Where |
|---|---|
| Every route returns 200 | `core/tests/test_public.py` |

---

"""


def scenario(number: int, title: str = "A thing", *, judgement: str | None = "Does it read right?") -> str:
    """One well-formed scenario, optionally with its judgement clause removed."""
    body = [
        f"## Scenario {number} — {title}",
        "",
        "**Category:** grounding",
        "**Setup:** Open `/ask/`.",
        "",
        "1. Ask a question.",
        "2. Read the answer.",
        "",
        "**Expected:** An answer with a citation.",
        "",
    ]
    if judgement is not None:
        body.append(f"**Judgement:** {judgement}")
        body.append("")
    body.append("---")
    body.append("")
    return "\n".join(body)


# ------------------------------------------------------------------ the parse itself


def test_parse_finds_scenarios_and_ignores_the_automated_table(write_uat):
    path = write_uat(HEADER + scenario(1) + scenario(2))
    uat = parse_uat(path)

    assert [s.number for s in uat.scenarios] == [1, 2]
    assert uat.slug == "example_feature"
    assert uat.title == "Test UAT — An example"
    # The automated-coverage table is not a scenario and must not become one.
    assert len(uat.scenarios) == 2
    assert "test_public.py" not in " ".join(s.judgement for s in uat.scenarios)


def test_steps_are_split_out_of_the_setup_paragraph(write_uat):
    """The setup paragraph, the steps and the fenced command are one segment in the file.

    Without the split the card renders a wall of prose with no ordered actions — the part
    the reviewer actually works from. Break `_split_at_first_step` and this fails.
    """
    path = write_uat(HEADER + scenario(1))
    uat = parse_uat(path)
    one = uat.scenarios[0]

    assert one.steps == ("Ask a question.", "Read the answer.")
    assert "Open `/ask/`." in one.setup
    assert "Ask a question" not in one.setup


def test_a_fenced_block_is_opaque(write_uat):
    """A `**Something:**` line inside a shell snippet is part of the snippet."""
    text = (
        HEADER
        + """## Scenario 1 — A thing

**Category:** corpus
**Setup:** Re-ingest:

```bash
python manage.py ingest_standard --doc saoso --force
# **Note:** a comment that looks like a label
```

1. Ask.

**Expected:** An answer.

**Judgement:** Does it read right?

---
"""
    )
    uat = parse_uat(write_uat(text))
    one = uat.scenarios[0]

    assert one.notes == ()
    assert "python manage.py ingest_standard" in one.setup
    assert one.steps == ("Ask.",)


def test_scenario_numbers_must_be_unique(write_uat):
    path = write_uat(HEADER + scenario(1) + scenario(1, "A different thing"))
    with pytest.raises(UatFormatError) as raised:
        parse_uat(path)

    assert "Scenario 1 appears twice" in str(raised.value)
    assert "writes back by number" in str(raised.value)


def test_a_missing_judgement_is_refused_and_names_the_scenario(write_uat):
    """The gate. A card with no judgement is an automated test in a checklist costume."""
    path = write_uat(HEADER + scenario(1) + scenario(2, "The unjudged one", judgement=None))
    with pytest.raises(UatFormatError) as raised:
        parse_uat(path)

    problems = raised.value.problems
    assert any("Scenario 2" in problem and "no `Judgement:`" in problem for problem in problems)
    assert not any("Scenario 1" in problem for problem in problems)


def test_a_missing_feature_slug_is_refused(write_uat):
    path = write_uat((HEADER.replace("**Feature slug:** `example_feature`\n", "")) + scenario(1))
    with pytest.raises(UatFormatError) as raised:
        parse_uat(path)

    assert any("Feature slug" in problem for problem in raised.value.problems)


def test_an_empty_file_is_refused(write_uat):
    with pytest.raises(UatFormatError) as raised:
        parse_uat(write_uat("# Nothing here\n"))

    assert any("no `## Scenario" in problem for problem in raised.value.problems)


# ------------------------------------------------------------------- the decisions


def test_parse_decisions_reads_the_real_spec():
    decisions = parse_decisions(REAL_SPEC.read_text(encoding="utf-8"))

    assert "D44" in decisions
    assert decisions["D44"].lower().startswith("**deferred")
    assert len(decisions) > 40


def test_duplicate_decision_ids_are_reported():
    spec = "\n".join(
        [
            "| # | Decision | Resolution |",
            "|---|----------|------------|",
            "| D1 | First | Deferred. |",
            "| D2 | Second | Decided. |",
            "| D1 | First again | Decided. |",
        ]
    )

    assert duplicate_decisions(spec) == ("D1",)
    # Last row wins, because that is the row a reader would act on.
    assert parse_decisions(spec)["D1"] == "Decided."


# ------------------------------------------------------------- the applicability scan


def _na_scenario(decision: str | None = "D44") -> str:
    cite = f" decision **{decision}**." if decision else ""
    return f"""## Scenario 5 — Afrikaans quality

**Status:** Not applicable to MVP 0.{cite} There is no translator.

**Category:** language
**Setup:** Read the site in Afrikaans.

1. Read the home page.

**Expected:** Afrikaans.

**Judgement:** Does it read as written by a speaker?

---
"""


def test_na_with_no_cited_decision_is_refused(write_uat):
    uat = parse_uat(write_uat(HEADER + _na_scenario(decision=None)))
    problems = scan_applicability(uat, {"D44": "Deferred."})

    assert len(problems) == 1
    assert "cites no decision" in problems[0]


def test_na_citing_an_unknown_decision_is_refused(write_uat):
    uat = parse_uat(write_uat(HEADER + _na_scenario("D999")))
    problems = scan_applicability(uat, {"D44": "Deferred."})

    assert len(problems) == 1
    assert "D999" in problems[0] and "not a row" in problems[0]


def test_na_whose_decision_stopped_deferring_is_refused(write_uat):
    """The whole reason the scan exists: D44 edited to "picked up" must fail loudly.

    Without this, the runner keeps printing a greyed-out card for a scenario that has
    become deliverable, and the release gate keeps passing on nine judged scenarios when
    ten are required.
    """
    uat = parse_uat(write_uat(HEADER + _na_scenario("D44")))
    picked_up = {"D44": "**Picked up 2027-01-01.** C3 is in MVP 1."}

    problems = scan_applicability(uat, picked_up)

    assert len(problems) == 1
    assert "no longer reads as a deferral" in problems[0]
    assert "re-judge the scenario" in problems[0]


def test_an_applicable_scenario_is_not_checked_for_a_decision(write_uat):
    uat = parse_uat(write_uat(HEADER + scenario(1)))
    assert scan_applicability(uat, {}) == []


def test_a_deferral_marker_anywhere_in_the_resolution_is_enough(write_uat):
    uat = parse_uat(write_uat(HEADER + _na_scenario("D7")))
    for marker in ("deferred", "out of MVP", "not applicable", "withheld", "post-MVP"):
        assert scan_applicability(uat, {"D7": f"Something. {marker} here."}) == []


# ------------------------------------------------------------------ the real files


def test_the_real_mvp0_uat_parses_and_scans_clean():
    uat = parse_uat(REAL_UAT)
    decisions = parse_decisions(REAL_SPEC.read_text(encoding="utf-8"))

    assert scan_applicability(uat, decisions) == []
    assert uat.slug == "mvp0_standards_and_public_site"


def test_the_real_mvp0_uat_still_has_nine_applicable_scenarios():
    """Pinned, so a scenario cannot silently flip to N/A or vanish.

    Nine applicable + one N/A (Scenario 5, D44) is what the PRD's slice 1 promises to get
    signed. A change here is a change to what a reviewer is asked to judge, and it should
    be a deliberate edit to this test and to D44 — not a side effect.
    """
    uat = parse_uat(REAL_UAT)

    assert len(uat.scenarios) == 10
    assert [s.number for s in uat.not_applicable] == [5]
    assert len(uat.applicable) == 9
    assert all(s.judgement for s in uat.applicable)


def test_every_real_mvp1a_scenario_carries_a_judgement():
    """1a is not buildable yet, and its UAT is still held to the gate."""
    from .conftest import REPO_ROOT

    uat = parse_uat(REPO_ROOT / "tests/uat/mvp1a_in_office_visit_uat.md")

    assert len(uat.scenarios) == 12
    assert all(s.judgement for s in uat.scenarios)
    assert scan_applicability(uat, {}) == []
