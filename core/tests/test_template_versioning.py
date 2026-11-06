"""Task B2 — template versioning (spec §4.2, §4.9; D27; `build_principles.md` §I Immutable History).

A questionnaire is corrected, not rewritten: the FORM gets a fix, a clause moves, a verdict's wording
is sharpened. When that happens, one rule decides everything else on this page:

    **An assessment freezes a full copy of the template's schema when the visit starts.**

So an edit to a live template would rewrite the meaning of every visit that used it. The version is
therefore the unit of change — a corrected questionnaire is a new row, and the old row stops being the
one a visit may use without being touched at all. Three consequences, and each is a test:

- **One active template per category**, enforced by a partial unique index, not only by the service.
  A service check is a rule the next caller can skip; the database is the one place two writers
  cannot both win.
- **Activation moves the flag** for that category only. The animal sheet's version has nothing to do
  with the crop sheet's.
- **An inactive template cannot start an assessment.** The guard is a service function
  (`assert_template_usable`), because the `Assessment` model belongs to a later task and A5 set the
  precedent: build the guard where the rule lives, and let its caller arrive when it exists.

`activate_template` also refuses a template whose schema does not validate. Otherwise `load_template`
could be bypassed with a `--activate` flag on a file whose author never ran the validator, and the
first visitor to notice would be an assessor in a field.
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from core.models import AssessmentTemplate, Category
from core.services._templates import (
    InactiveTemplateError,
    NoActiveTemplateError,
    SchemaValidationError,
    activate_template,
    assert_template_usable,
    current_template,
)

pytestmark = pytest.mark.django_db


def _schema(**overrides) -> dict:
    schema = {
        "schema_version": 1,
        "sections": [
            {
                "key": "part_a",
                "title": "PART A — General information",
                "questions": [
                    {
                        "key": "crops.Q1.1",
                        "ref": "1.1",
                        "text": "List the crops you are currently producing.",
                        "respondent": "FARMER",
                        "type": "TEXT",
                    }
                ],
            }
        ],
        "verdicts": [
            {"key": "crops.V01", "ref": "V01", "text": "Is the information correct?", "polarity": "POSITIVE"}
        ],
    }
    schema.update(overrides)
    return schema


@pytest.fixture
def crops(db):
    return Category.objects.create(code="CROPS", label="Crops")


@pytest.fixture
def animals(db):
    return Category.objects.create(code="ANIMAL_HUSBANDRY", label="Animal husbandry")


def _template(category, version="v1", *, active=False, schema=None) -> AssessmentTemplate:
    return AssessmentTemplate.objects.create(
        category=category,
        version=version,
        standard_version="SAOSO v2.1 (2026)",
        schema=schema or _schema(),
        is_active=active,
    )


# --- Activation moves one flag, for one category ----------------------------


def test_activating_a_template_deactivates_the_previous_one_for_that_category(crops):
    first = _template(crops, "v1", active=True)
    second = _template(crops, "v2")

    activate_template(second)

    first.refresh_from_db()
    second.refresh_from_db()
    assert second.is_active is True
    assert first.is_active is False


def test_activation_leaves_another_category_alone(crops, animals):
    """The animal sheet's version has nothing to do with the crop sheet's."""
    crops_v1 = _template(crops, "v1", active=True)
    animals_v1 = _template(animals, "v1", active=True)

    activate_template(_template(crops, "v2"))

    animals_v1.refresh_from_db()
    crops_v1.refresh_from_db()
    assert animals_v1.is_active is True, "another category's live template was switched off"
    assert crops_v1.is_active is False


def test_reactivating_a_superseded_version_moves_the_flag_back(crops):
    """A rollback is a normal act, not an edit: the row is untouched and only the flag moves."""
    v1 = _template(crops, "v1", active=True)
    v2 = _template(crops, "v2")
    activate_template(v2)

    activate_template(v1)

    v1.refresh_from_db()
    v2.refresh_from_db()
    assert (v1.is_active, v2.is_active) == (True, False)


# --- One active template per category, enforced twice -----------------------


def test_two_active_templates_for_one_category_are_refused_by_the_database(crops):
    """A service check is a rule the next caller can skip. The partial unique index is not.

    `accounting` on purpose: the assertion is that Postgres rejects the second row, so a test that
    only called the service would pass while an admin edit, a fixture or a data migration created
    the state the rule forbids.
    """
    _template(crops, "v1", active=True)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _template(crops, "v2", active=True)


def test_two_categories_may_each_have_one_active_template(crops, animals):
    _template(crops, "v1", active=True)
    _template(animals, "v1", active=True)
    assert AssessmentTemplate.objects.filter(is_active=True).count() == 2


# --- What a live template is, and what a visit may use ---------------------


def test_current_template_returns_the_active_one(crops):
    _template(crops, "v1")
    v2 = _template(crops, "v2", active=True)
    assert current_template(crops) == v2


def test_current_template_refuses_to_return_nothing(crops):
    """No active template is a deployment fault, not an empty questionnaire.

    Returning None would let a caller render zero questions and call it a visit.
    """
    _template(crops, "v1")
    with pytest.raises(NoActiveTemplateError) as caught:
        current_template(crops)
    assert "CROPS" in str(caught.value)


def test_an_inactive_template_cannot_start_an_assessment(crops):
    """The guard C1/E will call — built here, waiting for its caller (A5's pattern)."""
    draft = _template(crops, "v1")
    with pytest.raises(InactiveTemplateError):
        assert_template_usable(draft)

    activate_template(draft)
    assert_template_usable(draft)


# --- A malformed template cannot go live ------------------------------------


def test_a_template_that_fails_validation_cannot_be_activated(crops):
    """`load_template` is not the only way in: an admin edit or a data migration is another."""
    broken = _template(crops, "v1", schema=_schema(schema_version=99))
    with pytest.raises(SchemaValidationError) as caught:
        activate_template(broken)
    assert any("schema_version" in problem for problem in caught.value.problems)
    broken.refresh_from_db()
    assert broken.is_active is False
