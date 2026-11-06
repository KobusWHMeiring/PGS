"""Task B3 — the Crops template, hand-authored from FORM Sheet B.1 (D28).

This file is the template's *specification*: every assertion here is a fact read off the printed FORM
(`pgs_docs/6. PGS Farm visit assessment form … .xlsx`, sheet `6.B.1.Crops`), transcribed into
`core/templates_data/crops.v1.json`. It is not a test of the code — it is the reviewer's checklist in
executable form, which is what makes it useful: a human compares the JSON to the sheet, and this file
catches the omissions a human misses on the third reading.

**Three numbers in `MVP1A_PLAN.md` Task B3 do not match the sheet, and the sheet wins.** Each is
recorded here with the evidence, because a later reader will otherwise "fix" the JSON to the plan:

1. **Eleven derived controls, not twelve.** D71 and `SELF_CHECK_PRD` §3.4 give the twelve as B1–B7
   (the seven Sheet I §2 records) + C1–C5 (five practices). But C5 — *"Do you buy in produce from
   other farmers to sell on?"* — is **FORM Sheet A, Aggregation**, not the Crops sheet; the other four
   (Q4.2, Q5.1, Q11.1, Q11.2) are. So the Crops template carries **eleven** markers, and C5 becomes an
   own control in `SELF_CHECK_ITEMS` (A8's service) where its wording still has exactly one home.
2. **Nine printed child rows, not thirteen.** The plan lists V4(2), V10(2), V11(2), V19(3), V21(2),
   V35(2). The sheet's grey blocks hold one child row per parent except V4 and V19: rows 30–31 (V4),
   42 (V6), 64 (V10), 79 (V11), 122–123 (V19), 136 (V21), 213 (V35) — **nine**, and the plan omits
   V6's. Transcribed as printed; `test_the_child_groups_are_the_ones_the_sheet_prints` names the rows.
3. **The 38 questions are numbered *blocks*, and their sub-items are what is answered.** The plan's own
   marker example is `crops.Q4.2`, a printed sub-item, so a "Question N" is a container with `items`.
   The count of 38 is the count of `Question N` headings; the items are the 84 answerable cells.

The plan's other numbers hold exactly: **37 verdicts** (V1–V38 less the V15/V31 gaps, with V32 printed
twice), the four polarities it names, `links_to: INPUT_REGISTER` on Q4.3, and `allowed_ref_gaps`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core.management import call_command

from core.models import AssessmentTemplate, Category
from core.services._templates import validate_schema

pytestmark = pytest.mark.django_db

TEMPLATE_FILE = Path(__file__).resolve().parents[1] / "templates_data" / "crops.v1.json"


def load_crops_schema() -> dict:
    """The template as `load_template` reads it — the same file, not a copy in the test."""
    return json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))


def _questions(schema: dict) -> list[dict]:
    return [question for section in schema["sections"] for question in section["questions"]]


def _items(schema: dict) -> list[dict]:
    return [item for question in _questions(schema) for item in question.get("items", [])]


def _verdicts(schema: dict) -> list[dict]:
    return schema["verdicts"]


def _markers(schema: dict) -> dict[str, dict]:
    """Every `self_check` in the file, keyed by the question, item or record that carries it."""
    found: dict[str, dict] = {}
    for node in [*_questions(schema), *_items(schema), *schema.get("records", []), *_verdicts(schema)]:
        if "self_check" in node:
            found[node["key"]] = node["self_check"]
    return found


# --- The file is a loadable template ----------------------------------------


def test_the_crops_template_validates():
    assert validate_schema(load_crops_schema()) == []


def test_the_file_names_its_own_category_and_version():
    """`load_template` refuses a file that does not, so the file has to say."""
    schema = load_crops_schema()
    assert (schema["category"], schema["version"]) == ("CROPS", "v1")
    assert schema["standard_version"].startswith("SAOSO v2.1")


def test_the_file_loads_through_the_command_and_becomes_live():
    """The end-to-end door: the file, the validator, the loader and B2's activation."""
    Category.objects.create(code="CROPS", label="Crops")
    call_command("load_template", str(TEMPLATE_FILE), "--activate", verbosity=0)
    template = AssessmentTemplate.objects.get()
    assert template.is_active is True
    assert template.question_count == 38
    assert template.verdict_count == 37


# --- Completeness: the plan's numbers that hold ----------------------------


def test_crops_template_matches_the_workbook():
    schema = load_crops_schema()
    assert len(_questions(schema)) == 38
    # 79 printed sub-items, counted per question: 1+3+2 (A), 18 (B1), 12 (B2), 10 (B3), 6 (B4),
    # 8 (B5), 9 (B6), 5 (C7), 5 (C8). The plan's 38 counts the `Question N` headings, not these.
    assert len(_items(schema)) == 79
    assert len(_verdicts(schema)) == 37


def test_the_duplicate_v32_is_keyed_twice_but_printed_once():
    """Q31 and Q32 both print "V32" on the sheet. Two keys, one ref, so the count stays 37."""
    verdicts = _verdicts(load_crops_schema())
    keys = [verdict["key"] for verdict in verdicts]
    assert "crops.V32a" in keys and "crops.V32b" in keys
    assert {v["ref"] for v in verdicts if v["key"].startswith("crops.V32")} == {"V32"}


def test_known_gaps_are_declared_not_silent():
    """The sheet numbers V1–V38 but prints neither V15 nor V31; the gap is data, not an omission."""
    schema = load_crops_schema()
    assert schema["allowed_ref_gaps"] == ["V15", "V31"]
    assert not any(verdict["ref"] in ("V15", "V31") for verdict in schema["verdicts"])


@pytest.mark.parametrize("ref", ["V03", "V16", "V23"])
def test_inverted_and_informational_verdicts_carry_the_right_polarity(ref):
    polarity = {verdict["ref"]: verdict["polarity"] for verdict in _verdicts(load_crops_schema())}
    assert polarity[ref] != "POSITIVE"


def test_every_other_verdict_is_positive():
    negative_or_informational = {"V03", "V16", "V23"}
    for verdict in _verdicts(load_crops_schema()):
        if verdict["ref"] not in negative_or_informational:
            assert verdict["polarity"] == "POSITIVE", verdict["ref"]


def test_the_three_polarities_the_plan_names_are_the_three_used():
    schema = load_crops_schema()
    assert {v["polarity"] for v in schema["verdicts"]} == {"POSITIVE", "NEGATIVE", "INFORMATIONAL"}


# --- Structure: containers, items, children --------------------------------


def test_every_verdict_names_the_numbered_question_it_judges():
    """A verdict with no question has nowhere to sit on the page; `question_ref` is that link."""
    schema = load_crops_schema()
    refs = {question["ref"] for question in _questions(schema)}
    for verdict in _verdicts(schema):
        assert verdict.get("question_ref") in refs, verdict["ref"]


def test_every_question_holds_at_least_one_item_and_no_item_holds_items():
    for question in _questions(load_crops_schema()):
        assert question.get("items"), question["key"]
        for item in question["items"]:
            assert "items" not in item, item["key"]


def test_the_child_groups_are_the_ones_the_sheet_prints():
    """Nine printed child rows, with the sheet's row numbers, not the plan's thirteen.

    Rows: 30–31 (V4), 42 (V6), 64 (V10), 79 (V11), 122–123 (V19), 136 (V21), 213 (V35). Each was read
    off `6.B.1.Crops`: a row with text in column B and no verdict in column A, inside a grey block.
    """
    schema = load_crops_schema()
    subs = {v["key"]: v.get("sub_questions", []) for v in _verdicts(schema)}
    assert {key for key, group in subs.items() if group} == {
        "crops.V04", "crops.V06", "crops.V10", "crops.V11", "crops.V19", "crops.V21", "crops.V35",
    }
    assert all(isinstance(child, dict) and child.get("key") for group in subs.values() for child in group)
    assert sum(len(group) for group in subs.values()) == 9
    assert [len(subs[key]) for key in ("crops.V04", "crops.V19")] == [2, 2]


def test_a_child_key_is_its_parent_plus_a_letter():
    for verdict in _verdicts(load_crops_schema()):
        for child in verdict.get("sub_questions", []):
            assert child["key"].startswith(verdict["key"] + "."), child["key"]
            assert child["polarity"] in {"POSITIVE", "NEGATIVE", "INFORMATIONAL"}, child["key"]


# --- The FORM's two roles --------------------------------------------------


def test_every_answerable_item_is_the_farmers():
    """The FORM's white cells are farmer-supplied and its grey cells are the assessment report.

    Read off the sheet's fills, not assumed: every question row in `6.B.1.Crops` has no fill
    (`A=<none>`), every verdict row is grey (`FFD8D8D8`, and `FFD9D9D9` for V35's second line). So
    every item is `FARMER`; verdicts have no `respondent` because a verdict is the assessor's.
    """
    items = _items(load_crops_schema())
    assert items and all(item["respondent"] == "FARMER" for item in items)


def test_only_the_types_a_renderer_exists_for_are_used():
    allowed = {"TEXT", "TEXTAREA", "YES_NO", "NUMBER", "CHOICE", "LIST", "DATE"}
    assert {item["type"] for item in _items(load_crops_schema())} <= allowed


# --- The FORM's own instructions, as data ----------------------------------


def test_the_input_register_link_is_on_q4_3():
    """D30: B.1 Q4.3 directs the farmer to FORM Sheet B.2, the input register."""
    item = {i["key"]: i for i in _items(load_crops_schema())}["crops.Q4.3"]
    assert item["links_to"] == "INPUT_REGISTER"


def test_the_sheets_attachment_requests_are_declared():
    """Sheet I §2 requires documents; the FORM also asks for four of them inside the questionnaire."""
    with_attachments = {
        item["key"] for item in _items(load_crops_schema()) if item.get("attachments")
    }
    assert with_attachments == {
        "crops.Q5.2",   # compost supplier letter — V5's own recommendation
        "crops.Q10.3",  # soil test results
        "crops.Q11.2",  # seed supplier letter: untreated and non-GMO
        "crops.Q11.5",  # seedling supplier letter
        "crops.Q16.2",  # water test results
    }


# --- D71's markers ---------------------------------------------------------


def test_the_template_carries_eleven_derived_controls():
    """B1–B7 (records) + C1–C4 (practices). C5 is Sheet A, so it is A8's own control — see the
    module docstring for the arithmetic and why the plan's twelve cannot all be on this sheet."""
    markers = _markers(load_crops_schema())
    assert len(markers) == 11
    assert set(markers) == {
        "crops.Q4.2", "crops.Q5.1", "crops.Q11.1", "crops.Q11.2",
        "crops.R01", "crops.R02", "crops.R03", "crops.R04", "crops.R05", "crops.R06", "crops.R07",
    }


def test_every_marker_resolves_to_a_question_item_or_record_that_exists():
    """A8 derives its controls from these; a marker pointing at nothing is a blank control."""
    schema = load_crops_schema()
    existing = {node["key"] for node in [*_questions(schema), *_items(schema), *schema["records"]]}
    assert set(_markers(schema)) <= existing


def test_every_marker_is_tier_one_with_a_why_sentence():
    for key, marker in _markers(load_crops_schema()).items():
        assert marker["tier"] == 1, key
        assert len(marker["why"]) > 40, key


#: The markers whose reviewed copy explains what the record is *for* without naming a clause. Five of
#: the seven records are written that way in D71's ledger ("A diary is the evidence trail…", "A soil
#: test is a snapshot of soil health, not a pass mark"), where R01 and R05 do cite (SAOSO 4.6, OPP
#: §VI.3). `SELF_CHECK_PRD` §3.3 asks every control's "why" to name its source, so this is a real gap in
#: the approved wording — recorded here rather than corrected, because the copy is the group's and was
#: reviewed. A8's page build is where the clause is added, and this test is what keeps the list honest:
#: a *new* marker without a citation fails, and removing one of these five from the copy also fails.
NO_CITED_CLAUSE = {"crops.R02", "crops.R03", "crops.R04", "crops.R06", "crops.R07"}


def test_every_marker_names_the_form_or_a_clause_it_comes_from():
    """The whole point of a "why" (SELF_CHECK_PRD §3.3): it cites something a reader can check."""
    missing = {
        key
        for key, marker in _markers(load_crops_schema()).items()
        if not any(token in marker["why"] for token in ("FORM", "SAOSO", "OPP"))
    }
    assert missing == NO_CITED_CLAUSE, (
        f"marker(s) with no cited source: {sorted(missing - NO_CITED_CLAUSE)}"
    )


def test_the_seven_record_markers_are_the_seven_sheet_i_records():
    schema = load_crops_schema()
    records = {record["key"]: record for record in schema["records"]}
    assert [record["ref"] for record in schema["records"]] == [
        "a", "b", "c", "d", "e", "f", "soil_water",
    ]
    assert all("self_check" in record for record in records.values())
