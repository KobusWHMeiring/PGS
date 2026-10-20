"""The write-back: only results change, a second application changes nothing, and a
malformed export is refused rather than half-applied.

The property that matters is the **diff**. A sign-off is reviewable only if every changed
line in it is a result — if applying an export also rewrites a scenario's wording, the
reviewer signing the file is signing a document they did not read. `strip_owned()` below
removes exactly what the write-back is allowed to touch, and the tests assert that what
remains is byte-identical.
"""

from __future__ import annotations

import json
import shutil

import pytest

from scripts.uat_parse import parse_uat
from scripts.uat_signoff import RESULTS_SECTION, apply_export, main, result_line, validate

from .conftest import REAL_UAT


def make_export(uat, *, result: str = "PASS", overrides: dict | None = None) -> dict:
    """An export in the shape the page produces, one entry per scenario."""
    overrides = overrides or {}
    results = []
    for scenario in uat.scenarios:
        entry = {
            "number": scenario.number,
            "title": scenario.title,
            "result": "N/A" if scenario.not_applicable else result,
            "reason": "D44: no Afrikaans translator." if scenario.not_applicable else "",
            "note": "",
            "reviewer": "Kobus Meiring",
            "role": "Product",
            "date": "2026-10-22",
            "evidence": None,
            "evidence_name": "",
        }
        if entry["result"] == "FAIL":
            entry["reason"] = "It refused a question the standard answers."
        entry.update(overrides.get(scenario.number, {}))
        results.append(entry)
    return {
        "kind": "pgs-uat-signoff",
        "version": 1,
        "file": uat.path.as_posix(),
        "slug": uat.slug,
        "title": uat.title,
        "environment": {
            "commit": "deadbee",
            "working_tree": "modified",
            "database": "pgs_uat",
            "generated_on": "2026-10-22",
        },
        "results": results,
    }


def strip_owned(text: str) -> str:
    """Everything the write-back must leave alone: drop result lines and the new section."""
    kept = []
    for line in text.splitlines():
        if line.strip() == RESULTS_SECTION:
            break
        if line.startswith("**Result:**"):
            continue
        kept.append(line)
    return "\n".join(kept).rstrip()


@pytest.fixture
def real_copy(tmp_path):
    """A copy of the real MVP 0 UAT, keeping its filename so an export can name it."""
    copy = tmp_path / REAL_UAT.name
    shutil.copy(REAL_UAT, copy)
    return copy


# --------------------------------------------------------------------- the format


def test_result_line_is_one_reviewable_line():
    line = result_line(
        {
            "result": "FAIL",
            "reason": "It refused a question\nthe standard answers.",
            "note": "",
            "reviewer": "Kobus Meiring",
            "role": "Product",
            "date": "2026-10-22",
        }
    )

    assert line == (
        "**Result:** FAIL · Kobus Meiring (Product) · 2026-10-22 — "
        "It refused a question the standard answers."
    )
    assert "\n" not in line


def test_a_result_without_a_role_is_still_one_line():
    line = result_line({"result": "PASS", "reviewer": "A Reviewer", "role": "", "date": "2026-10-22"})
    assert line == "**Result:** PASS · A Reviewer · 2026-10-22"


# ------------------------------------------------------------------- the round trip


def test_the_real_uat_round_trips_and_is_idempotent(real_copy):
    uat = parse_uat(real_copy)
    before = real_copy.read_text(encoding="utf-8")
    export = make_export(uat)

    after = apply_export(uat, export)
    assert strip_owned(before) == strip_owned(after), "the write-back touched lines it does not own"

    real_copy.write_text(after, encoding="utf-8", newline="\n")
    reparsed = parse_uat(real_copy)
    assert len(reparsed.scenarios) == 10
    for scenario in reparsed.scenarios:
        assert scenario.result, f"scenario {scenario.number} has no result"
        assert scenario.result.startswith("N/A" if scenario.not_applicable else "PASS")

    # Applying the same export again must produce the same bytes.
    assert apply_export(reparsed, export) == after


def test_every_scenario_gains_exactly_one_result_line(real_copy):
    uat = parse_uat(real_copy)
    after = apply_export(uat, make_export(uat))

    assert after.count("**Result:**") == 10
    assert after.count(RESULTS_SECTION) == 1


def test_the_result_lands_after_the_judgement_and_before_what_follows(real_copy):
    """Scenario 9 has a recorded observation after its judgement; the result goes above it."""
    uat = parse_uat(real_copy)
    after = apply_export(uat, make_export(uat)).splitlines()

    result_index = next(i for i, line in enumerate(after) if "**Result:**" in line and i > 220)
    observed_index = next(i for i, line in enumerate(after) if line.startswith("**Observed 2026-10-20"))

    assert result_index < observed_index


def test_the_signoff_section_records_what_was_signed_against(real_copy):
    uat = parse_uat(real_copy)
    after = apply_export(uat, make_export(uat))

    assert "**Signed against:** commit `deadbee` (modified), database `pgs_uat`" in after
    assert "**Results:** 9 PASS · 0 FAIL · 1 N/A" in after


# --------------------------------------------------------------------- the refusals


def test_a_missing_result_is_refused(real_copy):
    uat = parse_uat(real_copy)
    export = make_export(uat)
    export["results"][0]["result"] = ""

    problems = validate(uat, export)

    assert any("scenario 1: result ''" in problem for problem in problems)


def test_fail_without_a_reason_is_refused(real_copy):
    uat = parse_uat(real_copy)
    export = make_export(uat, overrides={1: {"result": "FAIL", "reason": ""}})

    problems = validate(uat, export)

    assert any("scenario 1 is FAIL but carries no reason" in problem for problem in problems)


def test_na_without_a_reason_is_refused(real_copy):
    uat = parse_uat(real_copy)
    export = make_export(uat, overrides={5: {"result": "N/A", "reason": "  "}})

    problems = validate(uat, export)

    assert any("scenario 5 is N/A but carries no reason" in problem for problem in problems)


def test_a_missing_reviewer_or_date_is_refused(real_copy):
    uat = parse_uat(real_copy)
    export = make_export(uat, overrides={1: {"reviewer": "  "}, 2: {"date": "22/10/2026"}})

    problems = validate(uat, export)

    assert any("scenario 1 has no reviewer name" in problem for problem in problems)
    assert any("scenario 2 has no date in YYYY-MM-DD form" in problem for problem in problems)


def test_an_export_for_another_file_is_refused(real_copy):
    uat = parse_uat(real_copy)
    export = make_export(uat)
    export["slug"] = "something_else"
    export["file"] = "tests/uat/other.md"

    problems = validate(uat, export)

    assert any("export is for 'something_else'" in problem for problem in problems)
    assert any("the export names" in problem for problem in problems)


def test_a_scenario_the_file_does_not_have_is_refused(real_copy):
    uat = parse_uat(real_copy)
    export = make_export(uat)
    export["results"].append(dict(export["results"][0], number=99))

    problems = validate(uat, export)

    assert any("scenario 99, which this file does not have" in problem for problem in problems)


def test_a_scenario_with_no_result_entry_is_refused(real_copy):
    uat = parse_uat(real_copy)
    export = make_export(uat)
    export["results"] = export["results"][:-1]

    problems = validate(uat, export)

    assert any("scenario 10 has no result" in problem for problem in problems)


def test_a_silent_na_on_an_applicable_scenario_warns_but_does_not_fail(real_copy, capsys):
    """A reviewer may be unable to run an applicable scenario. It must not be silent:
    the release gate counts judged scenarios, and this one is not judged."""
    uat = parse_uat(real_copy)
    export = make_export(uat, overrides={2: {"result": "N/A", "reason": "The instance was down."}})

    problems = validate(uat, export)

    assert problems == []
    assert "scenario 2 is applicable but was marked N/A" in capsys.readouterr().err


# ------------------------------------------------------------------------ the CLI


def test_main_writes_in_place_and_then_reports_nothing_to_do(real_copy, tmp_path, capsys, write_json):
    uat = parse_uat(real_copy)
    export_path = write_json(make_export(uat))

    assert main(["--file", str(real_copy), "--from", str(export_path)]) == 0
    assert "sign-off applied" in capsys.readouterr().out

    once = real_copy.read_text(encoding="utf-8")
    assert main(["--file", str(real_copy), "--from", str(export_path)]) == 0
    assert "nothing to change" in capsys.readouterr().out
    assert real_copy.read_text(encoding="utf-8") == once


def test_dry_run_prints_a_diff_and_writes_nothing(real_copy, capsys, write_json):
    uat = parse_uat(real_copy)
    export_path = write_json(make_export(uat))
    before = real_copy.read_text(encoding="utf-8")

    assert main(["--file", str(real_copy), "--from", str(export_path), "--dry-run"]) == 0

    printed = capsys.readouterr().out
    assert "+**Result:** PASS" in printed
    assert "dry run" in printed
    assert real_copy.read_text(encoding="utf-8") == before


def test_main_refuses_a_malformed_export_and_leaves_the_file_alone(real_copy, capsys, write_json):
    uat = parse_uat(real_copy)
    export = make_export(uat)
    export["results"] = export["results"][:3]
    export_path = write_json(export)
    before = real_copy.read_text(encoding="utf-8")

    assert main(["--file", str(real_copy), "--from", str(export_path)]) == 1
    assert "cannot be applied" in capsys.readouterr().err
    assert real_copy.read_text(encoding="utf-8") == before


def test_main_rejects_something_that_is_not_an_export(real_copy, tmp_path, capsys):
    path = tmp_path / "not-an-export.json"
    path.write_text(json.dumps({"hello": "world"}), encoding="utf-8")

    assert main(["--file", str(real_copy), "--from", str(path)]) == 1
    assert "is not a pgs-uat-signoff file" in capsys.readouterr().err


def test_main_reports_unreadable_json_rather_than_tracebacking(real_copy, tmp_path, capsys):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")

    assert main(["--file", str(real_copy), "--from", str(path)]) == 2
    assert "could not read the export" in capsys.readouterr().err
