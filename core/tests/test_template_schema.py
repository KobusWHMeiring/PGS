"""Task B1 — the assessment template model and the v1 schema validator (§4.2, D27, D28, D71).

The template is the one irreversible artefact in 1a: `Assessment.template_schema` freezes a full copy
of it at visit creation, so a wrong key or a missing polarity becomes evidence nobody can re-derive
later. Two consequences shape this file:

- **`validate_schema` returns every problem at once, not the first.** An author fixing a
  38-question template one error per run would take a day; worse, the thing being authored is the
  printed FORM, and the failure mode that matters is an omission the validator *can* see (a
  duplicate key, a verdict with no polarity) sitting behind a typo it reports first.
- **The messages name the path.** "polarity is missing" is not actionable in a schema with 37
  verdicts; `verdicts[12].polarity` is.

The `self_check` block (D71 / `SELF_CHECK_PRD` §4.6) is validated here rather than in the self-check
service because the wording has one home: if the marker is malformed the *template* is wrong, and a
public page that discovered it at request time would 500 on the front door.
"""

from __future__ import annotations

import copy

import pytest
from django.db import IntegrityError, transaction

from core.models import AssessmentTemplate, Category
from core.services._templates import (
    SchemaValidationError,
    assert_valid_schema,
    validate_schema,
)

pytestmark = pytest.mark.django_db


def _question(key: str, ref: str, **extra) -> dict:
    base = {
        "key": key,
        "ref": ref,
        "text": "Describe your soil fertility plan.",
        "respondent": "FARMER",
        "type": "TEXT",
    }
    base.update(extra)
    return base


def _verdict(key: str, ref: str, **extra) -> dict:
    base = {"key": key, "ref": ref, "text": "Is the information correct?", "polarity": "POSITIVE"}
    base.update(extra)
    return base


#: The smallest schema that is complete: one section, one question, one verdict.
MINIMAL = {
    "schema_version": 1,
    "standard_version": "SAOSO v2.1 (2026)",
    "sections": [
        {"key": "part_a", "title": "PART A — General information", "questions": [_question("crops.Q1.1", "1.1")]},
    ],
    "verdicts": [_verdict("crops.V01", "V01")],
}


def problems(**overrides) -> list[str]:
    """Validate a copy of MINIMAL with top-level keys replaced."""
    schema = copy.deepcopy(MINIMAL)
    schema.update(overrides)
    return validate_schema(schema)


# --- The happy path is the baseline -----------------------------------------


def test_a_complete_schema_has_no_problems():
    """The plan's acceptance: a valid Crops schema returns `[]`."""
    assert validate_schema(MINIMAL) == []


def test_a_standard_ref_may_be_null():
    """Not every FORM question cites a clause — `null` is an answer, not a gap."""
    schema = copy.deepcopy(MINIMAL)
    schema["verdicts"][0]["standard_ref"] = None
    schema["sections"][0]["questions"][0]["standard_ref"] = None
    assert validate_schema(schema) == []


def test_allowed_ref_gaps_is_accepted_as_data():
    """`allowed_ref_gaps` is how the FORM's own numbering holes (V15, V31) are declared."""
    schema = copy.deepcopy(MINIMAL)
    schema["allowed_ref_gaps"] = ["V15", "V31"]
    assert validate_schema(schema) == []


# --- The four rules the plan names ------------------------------------------


def test_a_duplicate_key_is_rejected():
    schema = copy.deepcopy(MINIMAL)
    schema["sections"][0]["questions"].append(_question("crops.Q1.1", "1.2"))
    found = validate_schema(schema)
    assert any("duplicate" in problem.lower() and "crops.Q1.1" in problem for problem in found), found


def test_a_key_that_does_not_match_the_grammar_is_rejected():
    for bad in ("crops.q1", "crops.Q1.", "other.Q1", "crops.X1", "crops"):  # lower-case prefix only
        schema = copy.deepcopy(MINIMAL)
        schema["sections"][0]["questions"][0]["key"] = bad
        found = validate_schema(schema)
        assert found, f"{bad!r} was accepted"


def test_a_verdict_without_polarity_is_rejected():
    schema = copy.deepcopy(MINIMAL)
    del schema["verdicts"][0]["polarity"]
    found = validate_schema(schema)
    assert any("polarity" in problem for problem in found), found


def test_a_polarity_outside_the_three_is_rejected():
    schema = copy.deepcopy(MINIMAL)
    schema["verdicts"][0]["polarity"] = "POSITIVE-ISH"
    assert any("polarity" in problem for problem in validate_schema(schema))


def test_a_schema_version_other_than_one_is_rejected():
    assert any("schema_version" in problem for problem in problems(schema_version=2))


def test_a_missing_schema_version_is_rejected():
    schema = copy.deepcopy(MINIMAL)
    del schema["schema_version"]
    assert any("schema_version" in problem for problem in validate_schema(schema))


# --- The D71 self_check block ----------------------------------------------


def test_a_question_may_carry_a_self_check_marker():
    """`SELF_CHECK_PRD` §4.6: the twelve derived controls get one of these."""
    schema = copy.deepcopy(MINIMAL)
    schema["sections"][0]["questions"][0]["self_check"] = {
        "tier": 1,
        "why": "The FORM's verdict V4 calls adequate on-farm composting a key requirement.",
    }
    assert validate_schema(schema) == []


def test_an_unknown_key_inside_self_check_is_rejected():
    """A typo'd `whyy` must not silently become copy that renders empty on the front door."""
    schema = copy.deepcopy(MINIMAL)
    schema["sections"][0]["questions"][0]["self_check"] = {"tier": 1, "whyy": "because"}
    found = validate_schema(schema)
    assert any("self_check" in problem and "whyy" in problem for problem in found), found


def test_only_tier_one_exists():
    """A second tier is a decision, not a default (SELF_CHECK_PRD §4.6)."""
    schema = copy.deepcopy(MINIMAL)
    schema["sections"][0]["questions"][0]["self_check"] = {"tier": 2, "why": "because"}
    assert any("tier" in problem for problem in validate_schema(schema))


def test_a_self_check_without_a_why_is_rejected():
    schema = copy.deepcopy(MINIMAL)
    schema["sections"][0]["questions"][0]["self_check"] = {"tier": 1, "why": "  "}
    assert any("why" in problem for problem in validate_schema(schema))


# --- Every problem, in one pass --------------------------------------------


def test_every_problem_is_reported_in_one_pass():
    """Three defects, three messages — an author fixes the file, not one error per run."""
    schema = copy.deepcopy(MINIMAL)
    schema["schema_version"] = 2
    schema["sections"][0]["questions"][0]["key"] = "bad key"
    del schema["verdicts"][0]["polarity"]
    found = validate_schema(schema)
    assert len(found) >= 3, found
    assert any("schema_version" in p for p in found)
    assert any("key" in p for p in found)
    assert any("polarity" in p for p in found)


def test_the_messages_name_the_path_not_just_the_rule():
    schema = copy.deepcopy(MINIMAL)
    del schema["verdicts"][0]["polarity"]
    (problem,) = [p for p in validate_schema(schema) if "polarity" in p]
    assert "verdicts[0]" in problem, problem


# --- Shape errors, not just field errors ------------------------------------


@pytest.mark.parametrize("not_a_schema", [None, "{}", [], 1])
def test_something_that_is_not_an_object_is_rejected_without_raising(not_a_schema):
    found = validate_schema(not_a_schema)
    assert found and "object" in found[0].lower(), found


def test_an_empty_sections_list_is_rejected():
    """A template with no questions would render a questionnaire with nothing in it."""
    assert any("sections" in problem for problem in problems(sections=[]))


def test_a_question_type_outside_the_closed_set_is_rejected():
    """The types are code: a renderer must exist for each one."""
    schema = copy.deepcopy(MINIMAL)
    schema["sections"][0]["questions"][0]["type"] = "MAGIC"
    assert any("type" in problem for problem in validate_schema(schema))


def test_a_respondent_outside_the_two_roles_is_rejected():
    schema = copy.deepcopy(MINIMAL)
    schema["sections"][0]["questions"][0]["respondent"] = "SOMEONE"
    assert any("respondent" in problem for problem in validate_schema(schema))


def test_a_verdict_key_that_disagrees_with_its_ref_is_rejected():
    """`crops.V04` next to `ref: "V05"` is a transcription slip, and the visit would cite V05."""
    schema = copy.deepcopy(MINIMAL)
    schema["verdicts"][0]["key"] = "crops.V04"
    found = validate_schema(schema)
    assert any("V04" in problem and "V01" in problem for problem in found), found


def test_a_question_key_that_disagrees_with_its_ref_is_rejected():
    schema = copy.deepcopy(MINIMAL)
    schema["sections"][0]["questions"][0]["key"] = "crops.Q4.2"
    found = validate_schema(schema)
    assert any("Q4.2" in problem and "1.1" in problem for problem in found), found


def test_two_prefixes_in_one_template_are_rejected():
    """One template is one category; `crops.` and `animals.` in one file is a copy-paste."""
    schema = copy.deepcopy(MINIMAL)
    schema["verdicts"][0]["key"] = "animals.V01"
    found = validate_schema(schema)
    assert any("prefix" in problem.lower() for problem in found), found


def test_a_sub_question_is_a_child_and_may_not_be_a_verdict_row():
    """V4/V10/V11/V19/V21/V35 carry printed children; a child never gets its own top-level row."""
    schema = copy.deepcopy(MINIMAL)
    schema["verdicts"][0]["sub_questions"] = [
        {"key": "crops.V01.a", "text": "Is the compost of a good quality?", "polarity": "POSITIVE",
         "options": ["YES", "NO", "NA"], "required": True},
    ]
    assert validate_schema(schema) == []

    schema["verdicts"].append(_verdict("crops.V01.a", "V01"))
    found = validate_schema(schema)
    assert any("sub_questions" in problem or "child" in problem for problem in found), found


def test_a_sub_question_without_polarity_is_rejected():
    schema = copy.deepcopy(MINIMAL)
    schema["verdicts"][0]["sub_questions"] = [{"key": "crops.V01.a", "text": "…"}]
    assert any("polarity" in problem for problem in validate_schema(schema))


def test_assert_valid_schema_raises_with_every_problem_attached():
    """`load_template` needs the list to print it; a boolean would lose it."""
    with pytest.raises(SchemaValidationError) as caught:
        assert_valid_schema({**MINIMAL, "schema_version": 9})
    assert caught.value.problems
    assert "schema_version" in str(caught.value)


# --- The model --------------------------------------------------------------


def test_a_template_is_unique_per_category_and_version():
    category = Category.objects.create(code="CROPS", label="Crops")
    AssessmentTemplate.objects.create(
        category=category, version="v1", standard_version="SAOSO v2.1 (2026)", schema=MINIMAL
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AssessmentTemplate.objects.create(
                category=category, version="v1", standard_version="SAOSO v2.1 (2026)", schema=MINIMAL
            )


def test_two_categories_may_each_have_a_v1():
    """The version is per category, not global: the animal sheet starts numbering again."""
    crops = Category.objects.create(code="CROPS", label="Crops")
    animals = Category.objects.create(code="ANIMAL_HUSBANDRY", label="Animal husbandry")
    for category in (crops, animals):
        AssessmentTemplate.objects.create(
            category=category, version="v1", standard_version="SAOSO v2.1 (2026)", schema=MINIMAL
        )
    assert AssessmentTemplate.objects.count() == 2


def test_a_template_is_inactive_until_it_is_activated():
    """B2 owns activation. The default matters here: a half-authored file must not be live."""
    category = Category.objects.create(code="CROPS", label="Crops")
    template = AssessmentTemplate.objects.create(
        category=category, version="v1", standard_version="SAOSO v2.1 (2026)", schema=MINIMAL
    )
    assert template.is_active is False
