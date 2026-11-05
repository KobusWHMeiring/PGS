"""Task B4 — `load_template` (spec §4.9, D28): the only door a questionnaire comes in through.

Four behaviours are the point, and each is a refusal:

- a file that does not validate **writes nothing** and prints **every** problem, because an author
  fixing a 38-question FORM one error per run stops reading;
- a version that already exists is **never overwritten** — a past assessment froze a copy of it, so a
  changed file for the same version is an error, not an update;
- an unchanged file re-run is a **successful no-op**, which is what makes the command re-runnable on
  every deploy;
- `--activate` is explicit, and it goes through B2's service so the previous version is stood down.

The command's `category`/`version`/`standard_version` come from the file, not from flags: a
questionnaire that does not name its own category can be loaded into the wrong one, and the mistake
would surface as a visit asking the animal sheet's questions on a crop farm.
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from core.models import AssessmentTemplate, Category

pytestmark = pytest.mark.django_db


def _schema(**overrides) -> dict:
    schema = {
        "schema_version": 1,
        "category": "CROPS",
        "version": "v1",
        "standard_version": "SAOSO v2.1 (2026)",
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


def _file(tmp_path, schema: dict):
    path = tmp_path / "crops.v1.json"
    path.write_text(json.dumps(schema), encoding="utf-8")
    return path


def _run(path, *args):
    out, err = StringIO(), StringIO()
    call_command("load_template", str(path), *args, stdout=out, stderr=err)
    return out.getvalue(), err.getvalue()


# --- The happy path ---------------------------------------------------------


def test_a_valid_file_creates_one_inactive_template(crops, tmp_path):
    out, _ = _run(_file(tmp_path, _schema()))

    template = AssessmentTemplate.objects.get()
    assert (template.category, template.version) == (crops, "v1")
    assert template.standard_version == "SAOSO v2.1 (2026)"
    assert template.is_active is False, "loading must not make a questionnaire live"
    assert "created" in out.lower()


def test_running_twice_is_a_successful_no_op(crops, tmp_path):
    path = _file(tmp_path, _schema())
    _run(path)
    out, _ = _run(path)

    assert AssessmentTemplate.objects.count() == 1
    assert "unchanged" in out.lower()


def test_activate_makes_it_the_live_template(crops, tmp_path):
    _run(_file(tmp_path, _schema()), "--activate")
    assert AssessmentTemplate.objects.get().is_active is True


# --- The three refusals ----------------------------------------------------


def test_a_changed_file_for_an_existing_version_is_an_error(crops, tmp_path):
    """A template that exists is history: every past assessment froze a copy of it."""
    path = _file(tmp_path, _schema())
    _run(path)

    edited = _schema()
    edited["sections"][0]["questions"][0]["text"] = "A quietly improved question."
    with pytest.raises(CommandError) as caught:
        _run(_file(tmp_path, edited))

    assert "version" in str(caught.value).lower()
    assert AssessmentTemplate.objects.get().schema["sections"][0]["questions"][0]["text"] == (
        "List the crops you are currently producing."
    )


def test_an_invalid_schema_prints_every_problem_and_writes_nothing(crops, tmp_path):
    broken = _schema(schema_version=99)
    broken["verdicts"][0].pop("polarity")

    err = StringIO()
    with pytest.raises(CommandError):
        call_command(
            "load_template", str(_file(tmp_path, broken)), stdout=StringIO(), stderr=err
        )

    text = err.getvalue()
    assert "schema_version" in text and "polarity" in text, text
    assert AssessmentTemplate.objects.count() == 0


def test_an_unseeded_category_is_refused_and_named(crops, tmp_path):
    schema = _schema(category="WINE", sections=_rename(_schema()["sections"], "wine"),
                     verdicts=_rename(_schema()["verdicts"], "wine"))
    with pytest.raises(CommandError) as caught:
        _run(_file(tmp_path, schema))
    assert "WINE" in str(caught.value)
    assert "CROPS" in str(caught.value), "the error should name what is seeded"
    assert AssessmentTemplate.objects.count() == 0


def test_a_file_without_a_version_is_refused(crops, tmp_path):
    schema = _schema()
    del schema["version"]
    with pytest.raises(CommandError) as caught:
        _run(_file(tmp_path, schema))
    assert "version" in str(caught.value)
    assert AssessmentTemplate.objects.count() == 0


def test_malformed_json_is_refused_without_a_traceback(crops, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(CommandError) as caught:
        _run(path)
    assert "json" in str(caught.value).lower()


def test_a_missing_file_is_refused(crops, tmp_path):
    with pytest.raises(CommandError):
        _run(tmp_path / "nope.json")


def _rename(items, prefix):
    """Re-prefix keys so a refused file is internally consistent (and still refused)."""
    renamed = []
    for item in items:
        copy = json.loads(json.dumps(item))
        copy["key"] = copy["key"].replace("crops.", f"{prefix}.")
        renamed.append(copy)
    return renamed
