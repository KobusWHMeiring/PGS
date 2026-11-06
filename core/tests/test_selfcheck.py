"""Task A8 — the public self-check, `/before-you-apply/` (D71, SELF_CHECK_PRD).

Two rules decide everything in this file, and both are *absences*:

1. **Nothing is stored without research consent.** With neither box ticked the page renders the
   result from the submitted form in the same request, and no row exists. `submit()` returning
   `None` is a normal result, not a failure.
2. **The result is a mirror, never a verdict.** Counts out of a known denominator, a to-do list of
   records, and the two facts nobody publishes — the land-history disagreement and the declared fee
   band. There is no score, no percentage and no eligibility claim. `test_the_page_states_no_claim`
   is the guard, and it is the same discipline `test_claim_discipline.py` sweeps.

The third thing this file pins is the seam B3 left open: the **eleven** derived controls come out of
the *active* Crops template's `self_check` markers, and the service names each one explicitly. A
marker with no name is a control nobody shows; a name with no marker is a crash at render time
instead of a red test.

`test_the_page_renders_with_no_template_live` exists because the demo runs before
`load_template --activate` is a deploy step: the page must answer honestly (a caveat) rather than
500 or pretend the questionnaire is empty.
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from core.models import (
    Category,
    ConsentPurpose,
    ConsentText,
    FarmCategory,
    Member,
    SelfCheckDemographic,
    SelfCheckReport,
)
from core.services._public import FEE_BANDS
from core.services._selfcheck import (
    ANSWER_NO,
    ANSWER_PARTLY,
    ANSWER_RATHER_NOT_SAY,
    ANSWER_YES,
    DERIVED_CONTROLS,
    MISSING_RECORD_BLOCKS_FINALISE,
    MISSING_RECORD_IS_A_RECORD_NOT_A_BLOCKER,
    SELF_CHECK_ITEMS,
    TEXT_ONLY_CITATIONS,
    ConsentNotWrittenError,
    DemographicConsentRequiredError,
    ReportNotFoundError,
    UnknownCategoryError,
    build_check,
    evaluate,
    submit,
    withdraw,
)
from core.templatetags.pgs_extras import format_zar

pytestmark = pytest.mark.django_db

TEMPLATE_FILE = Path(__file__).resolve().parents[1] / "templates_data" / "crops.v1.json"
URL = "/before-you-apply/"


@pytest.fixture(autouse=True)
def isolated_cache(settings):
    """The per-IP budget is a cache counter: without this the test spends the real budget.

    Same reasoning as `conftest.chat_cache`: a rate-limit test that incremented the deployment's
    cache would leak between tests and leave a dev box with a spent budget.
    """
    from django.core.cache import cache

    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "selfcheck-tests"}
    }
    cache.clear()
    yield cache
    cache.clear()


@pytest.fixture
def seeded(db):
    """The deployment seed: categories, seals, the fee scale and the three consent texts."""
    call_command("seed_deployment", verbosity=0)


@pytest.fixture
def crops_live(seeded):
    """The Crops questionnaire, loaded and activated — the only category that has one."""
    call_command("load_template", str(TEMPLATE_FILE), "--activate", verbosity=0)


@pytest.fixture
def payload() -> dict:
    """A complete, valid submission with the answer set the ledger reviewed."""
    return {
        "A1": ["CROPS"],
        "A2": "1–5 ha",
        "A3": "Less than 1 ha",
        "A4": "12–17 months",
        "A5": "R250 001 – R500 000",
        "B1": ANSWER_YES,
        "B2": ANSWER_YES,
        "B3": ANSWER_PARTLY,
        "B4": ANSWER_NO,
        "B5": ANSWER_NO,
        "B6": ANSWER_NO,
        "B7": ANSWER_RATHER_NOT_SAY,
        "C1": "YES",
        "C2": "NO",
        "C3": "MIX",
        "C4": "SOME",
        "C5": "NO",
        "D1": "COST",
        "D1_note": "",
        "consent_version": "research-2026-11-05",
    }


def _research_text() -> ConsentText:
    return ConsentText.objects.current(ConsentPurpose.RESEARCH)


# --- The consent rule -------------------------------------------------------


def test_nothing_is_stored_without_consent(client: Client, seeded, crops_live, payload):
    response = client.post(URL, payload)
    assert response.status_code == 200
    assert SelfCheckReport.objects.count() == 0
    assert not SelfCheckDemographic.objects.exists()
    # ...and the result still renders from the submitted form, in the same request (§3.6).
    assert "Of the seven records a visit checks" in response.content.decode()


def test_research_consent_writes_one_row_and_stores_no_identifier(
    client: Client, seeded, crops_live, payload
):
    client.post(URL, {**payload, "research_consent": "on"})
    report = SelfCheckReport.objects.get()
    field_names = {field.name for field in SelfCheckReport._meta.get_fields()}
    # There is no such field to set: the report cannot become an application record.
    assert not {"member", "member_id", "farm", "farm_id", "user", "user_id"} & field_names
    assert report.research_consent_at is not None
    assert report.consent_text_version == _research_text().version
    assert report.records_held["B1"] == ANSWER_YES


def test_demographic_consent_is_refused_without_research_consent(
    client: Client, seeded, crops_live, payload
):
    response = client.post(
        URL,
        {**payload, "demographic_consent": "on", "census_gender": "Female"},
    )
    assert response.status_code == 200
    assert not SelfCheckReport.objects.exists()
    assert not SelfCheckDemographic.objects.exists()
    assert "consent" in response.content.decode().lower()


def test_submit_refuses_demographic_consent_on_its_own(seeded, crops_live, payload):
    with pytest.raises(DemographicConsentRequiredError):
        submit(payload, research_consent=False, demographic_consent=True)


def test_demographic_consent_writes_the_second_table(seeded, crops_live, payload):
    report = submit(
        payload,
        research_consent=True,
        demographic_consent=True,
        demographic={
            "census_gender": "Female",
            "census_age_band": "34-50",
            "census_demographic_group": "African",
        },
    )
    assert report is not None
    row = SelfCheckDemographic.objects.get()
    assert row.report_id == report.pk
    assert row.census_gender == "Female"
    assert row.census_demographic_group == "African"


def test_a_stale_consent_version_is_refused(seeded, crops_live, payload):
    from core.services._application import ConsentTextChangedError

    with pytest.raises(ConsentTextChangedError):
        submit(
            {**payload, "consent_version": "research-2020-01-01"},
            research_consent=True,
            demographic_consent=False,
        )
    assert not SelfCheckReport.objects.exists()


def test_no_research_wording_means_nothing_can_be_stored(seeded, crops_live, payload):
    ConsentText.objects.filter(purpose=ConsentPurpose.RESEARCH).delete()
    with pytest.raises(ConsentNotWrittenError):
        submit(payload, research_consent=True, demographic_consent=False)
    assert not SelfCheckReport.objects.exists()


def test_withdraw_deletes_both_rows(seeded, crops_live, payload):
    report = submit(
        payload,
        research_consent=True,
        demographic_consent=True,
        demographic={"census_gender": "Female"},
    )
    withdraw(report.public_uuid)
    assert not SelfCheckReport.objects.exists()
    assert not SelfCheckDemographic.objects.exists()


def test_withdraw_refuses_an_unknown_reference(seeded):
    import uuid

    with pytest.raises(ReportNotFoundError):
        withdraw(uuid.uuid4())


def test_the_honeypot_writes_nothing(client: Client, seeded, crops_live, payload):
    response = client.post(URL, {**payload, "research_consent": "on", "website": "spam"})
    assert response.status_code == 200
    assert not SelfCheckReport.objects.exists()


def test_the_post_budget_is_per_ip(client: Client, seeded, crops_live, payload, settings):
    settings.SELF_CHECK_RATE_LIMIT = 2
    settings.SELF_CHECK_RATE_WINDOW_SECONDS = 3600
    assert client.post(URL, payload).status_code == 200
    assert client.post(URL, payload).status_code == 200
    assert client.post(URL, payload).status_code == 429


# --- The result is a mirror ------------------------------------------------


def test_the_two_fixed_lines_come_from_the_finalise_gate_constant(seeded):
    """§5.8: a MISSING record is a record, not a blocker.

    The public promise and the visit's finalise gate read one constant, so changing one cannot
    leave the other behind.
    """
    assert MISSING_RECORD_BLOCKS_FINALISE is False
    result = evaluate({})
    assert result.fixed_lines["missing_record"] == MISSING_RECORD_IS_A_RECORD_NOT_A_BLOCKER
    assert result.fixed_lines["visit_decides"]
    assert result.fixed_lines["visit_decides"] != result.fixed_lines["missing_record"]


def test_the_mirror_counts_out_of_a_known_denominator(seeded, crops_live):
    result = evaluate(
        {
            "B1": ANSWER_YES,
            "B2": ANSWER_YES,
            "B3": ANSWER_PARTLY,
            "B4": ANSWER_NO,
            "B5": ANSWER_RATHER_NOT_SAY,
        }
    )
    assert "Of the seven records a visit checks" in result.mirror
    assert "3 in place" in result.mirror
    assert result.records_in_place == 3
    assert result.records_missing == 1
    assert result.records_not_said == 1


def test_rather_not_say_produces_no_todo_item_and_is_not_counted_missing(
    seeded, crops_live, payload
):
    result = evaluate(payload)
    assert all(item.key != "B7" for item in result.todo)
    assert result.records_not_said == 1
    # The count that makes "not counted as missing" mean something: B4, B5 and B6 are NO, and a
    # "rather not say" that leaked into this number would make the mirror's denominator a lie.
    assert result.records_missing == 3
    # B4, B5 and B6 are NO, B3 is PARTLY: four open items, and B7 is not one of them.
    assert [item.key for item in result.todo] == ["B3", "B4", "B5", "B6"]


def test_a_partly_held_record_is_a_different_sentence_from_a_missing_one(seeded, crops_live):
    result = evaluate({"B1": ANSWER_PARTLY, "B2": ANSWER_NO})
    framings = {item.key: item.framing for item in result.todo}
    assert framings["B1"] != framings["B2"]


def test_the_land_history_note_prints_both_thresholds(seeded, crops_live):
    result = evaluate({"A4": "12–17 months"})
    assert "12 months" in result.land_history_note
    assert "18 months" in result.land_history_note
    assert "not yet settled" in result.land_history_note  # D31 is shown, never resolved


@pytest.mark.parametrize(
    "band",
    ["Not yet", "Under 12 months", "12–17 months", "18 months or more", "I am not sure"],
)
def test_every_land_history_band_has_its_own_note(seeded, crops_live, band):
    """A band with no note would render an empty box — an unanswered control is normal, a blank
    answer to a question that was answered is not."""
    result = evaluate({"A4": band})
    assert len(result.land_history_note) > 40


def test_no_land_history_answer_means_no_note(seeded, crops_live):
    assert evaluate({}).land_history_note == ""


def test_the_declared_band_prints_the_opp_figure(seeded, crops_live):
    result = evaluate({"A5": "R250 001 – R500 000"})
    band = next(b for b in FEE_BANDS if b.label == "R250 001 – R500 000")
    assert result.fee_band is not None
    assert result.fee_band.label == band.label
    assert format_zar(band.initial_cents) in result.fee_band.note


def test_rather_not_say_on_turnover_shows_no_figure(seeded, crops_live):
    result = evaluate({"A5": "I would rather not say"})
    assert result.fee_band is None


def test_a_non_crops_category_gets_a_caveat_not_an_empty_form(client: Client, seeded):
    response = client.post(URL, {"A1": ["ANIMAL_HUSBANDRY"]})
    assert response.status_code == 200
    assert "still being written" in response.content.decode()


def test_the_page_states_no_claim(client: Client, seeded):
    """No eligibility verdict, in any form. The visa is the visit's, not the page's."""
    html = client.get(URL).content.decode().lower()
    for term in ("you are ready", "you qualify", "you are eligible", "approved", "certified"):
        assert term not in html, f"{term!r} is on the self-check page"


def test_every_todo_citation_is_declared_text_only(seeded, crops_live):
    result = evaluate({key: ANSWER_NO for key in ("B1", "B2", "B3", "B4", "B5", "B6", "B7")})
    assert len(result.todo) == 7
    for item in result.todo:
        if item.citation.kind == "TEXT_ONLY":
            assert item.citation.label in TEXT_ONLY_CITATIONS
        else:  # pragma: no cover - no clause citation exists yet, and that is the point
            assert item.citation.anchor


# --- The eleven derived controls resolve from the template -----------------


def test_the_eleven_derived_controls_resolve_from_the_active_template(crops_live):
    check = build_check("CROPS")
    derived = [control for control in check.controls if control.template_key]
    assert len(derived) == 11
    assert {control.key for control in derived} == {
        "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4"
    }
    assert all(control.why for control in derived)
    assert all(control.template_text for control in derived)


def test_every_template_marker_is_named_and_every_name_has_a_marker(crops_live):
    """Both directions. A new marker nobody shows is as wrong as a name with no marker."""
    from core.models import AssessmentTemplate

    schema = json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
    markers = set()

    def walk(node):
        if isinstance(node, dict):
            if "self_check" in node:
                markers.add(node["key"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    assert AssessmentTemplate.objects.count() == 1
    assert markers == {control.template_key for control in DERIVED_CONTROLS}


def test_the_service_carries_no_copy_for_a_derived_control():
    """One home for each sentence: a derived control's `why` is the template's, never the code's."""
    assert all(control.why == "" for control in DERIVED_CONTROLS)
    assert all(control.why for control in SELF_CHECK_ITEMS)
    assert all(control.template_key == "" for control in SELF_CHECK_ITEMS)


def test_the_own_controls_are_the_nine_the_handover_names():
    assert [control.key for control in SELF_CHECK_ITEMS] == [
        "A1", "A2", "A3", "A4", "A5", "C5", "D1", "E1", "E2"
    ]


def test_the_check_has_the_five_groups_in_order(crops_live):
    check = build_check("CROPS")
    assert [group.key for group in check.groups] == ["A", "B", "C", "D", "E"]
    assert [len(group.controls) for group in check.groups] == [5, 7, 5, 1, 2]


def test_a_live_template_missing_a_marker_is_a_loud_failure(crops_live):
    """The template and the service name the same eleven controls, and a mismatch must be loud.

    Silently rendering nineteen controls because `crops.Q4.2` lost its marker is the failure this
    guard exists for: the front door would promise a slightly different check from the one the visit
    performs, and nobody would notice until a farmer was asked about compost for the first time on
    the day.
    """
    import copy

    from core.models import AssessmentTemplate

    from core.services._selfcheck import MarkerMissingError

    template = AssessmentTemplate.objects.get()
    schema = copy.deepcopy(template.schema)
    for section in schema["sections"]:
        for question in section["questions"]:
            for item in question.get("items", []):
                if item.get("key") == "crops.Q4.2":
                    item.pop("self_check")
    AssessmentTemplate.objects.filter(pk=template.pk).update(schema=schema)

    with pytest.raises(MarkerMissingError):
        build_check("CROPS")


def test_an_unknown_category_is_a_named_error(seeded):
    with pytest.raises(UnknownCategoryError):
        build_check("NOT_A_CATEGORY")


def test_the_page_renders_with_no_template_live(client: Client, seeded):
    """The demo runs before `load_template --activate`. It must say so, not 500 and not lie."""
    response = client.get(URL)
    html = response.content.decode()
    assert response.status_code == 200
    assert "records" in html.lower()


def test_the_page_renders_its_own_controls_with_no_template_live(client: Client, seeded):
    html = client.get(URL).content.decode()
    assert "How much land do you farm in total?" in html
    assert "Roughly what was your turnover last year?" in html


# --- The account at the end is A6's, and it writes no category --------------


def test_the_account_step_creates_the_account_and_no_farm_category(
    client: Client, seeded, crops_live
):
    from core.models import Farm, User

    consent = ConsentText.objects.current(ConsentPurpose.ACCOUNT)
    assert consent is not None
    response = client.post(
        URL,
        {
            "step": "account",
            "first_name": "Lena",
            "last_name": "Booysen",
            "email": "lena@example.com",
            "phone": "082 000 0000",
            "farm_name": "Bergsig",
            "nearest_town": "George",
            "contact_name": "Lena Booysen",
            "password1": "a-long-enough-password-42",
            "password2": "a-long-enough-password-42",
            "consent": "on",
            "consent_version": consent.version,
        },
    )
    assert response.status_code == 302
    member = Member.objects.get()
    assert member.user.username == "lena@example.com"
    assert Farm.objects.filter(member=member, name="Bergsig").exists()
    # The check's category ticks are not an application (A6's categories step makes those).
    assert not FarmCategory.objects.exists()


def test_the_account_step_without_consent_stores_nothing(client: Client, seeded, crops_live):
    from core.models import User

    response = client.post(
        URL,
        {
            "step": "account",
            "first_name": "Lena",
            "last_name": "Booysen",
            "email": "lena@example.com",
            "farm_name": "Bergsig",
            "nearest_town": "George",
            "contact_name": "Lena Booysen",
            "password1": "a-long-enough-password-42",
            "password2": "a-long-enough-password-42",
        },
    )
    assert response.status_code == 200
    assert not Member.objects.exists()
    assert not User.objects.filter(username="lena@example.com").exists()


# --- The aggregate is a command, not a page -------------------------------


def _report(*args: str) -> str:
    out = StringIO()
    call_command("report_self_check", *args, stdout=out)
    return out.getvalue()


def test_the_report_counts_each_band(seeded, crops_live, payload):
    submit(payload, research_consent=True, demographic_consent=False)
    submit({**payload, "A2": "20–100 ha"}, research_consent=True, demographic_consent=False)
    text = _report()
    assert "20–100 ha" in text
    assert "1–5 ha" in text
    assert "B7" in text  # uptake per record control


def test_the_report_refuses_a_cell_under_the_threshold(seeded, crops_live, payload):
    submit(
        payload,
        research_consent=True,
        demographic_consent=True,
        demographic={"census_gender": "Female"},
    )
    text = _report("--demographics")
    assert "not shown" in text.lower()
    assert "Female" not in text


def test_the_report_prints_a_cell_at_the_threshold(seeded, crops_live, payload):
    for _ in range(5):
        submit(
            payload,
            research_consent=True,
            demographic_consent=True,
            demographic={"census_gender": "Female"},
        )
    text = _report("--demographics")
    assert "Female" in text


# --- The seeds A6 did not write -----------------------------------------


def test_the_two_public_consents_are_seeded_as_drafts(seeded):
    for purpose in (ConsentPurpose.RESEARCH, ConsentPurpose.DEMOGRAPHICS):
        text = ConsentText.objects.current(purpose)
        assert text is not None, f"{purpose} has no wording to consent to"
        assert text.is_draft is True, "the build cannot approve the group's wording"
        assert text.body.strip()


def test_the_seed_does_not_overwrite_a_consent_the_group_adopted(seeded):
    ConsentText.objects.filter(purpose=ConsentPurpose.RESEARCH).update(
        approved_at=timezone.now()
    )
    call_command("seed_deployment", verbosity=0)
    assert ConsentText.objects.get(purpose=ConsentPurpose.RESEARCH).approved_at is not None


def test_the_pages_registry_covers_the_route(seeded):
    from core.services._public import PAGES
    from core.tests.test_public import PAGES as SWEPT

    assert "before_you_apply" in PAGES
    assert ("before-you-apply", URL, PAGES["before_you_apply"].heading) in SWEPT


def test_the_result_renders_after_a_real_post(client: Client, seeded, crops_live, payload):
    html = client.post(URL, {**payload, "research_consent": "on"}).content.decode()
    assert "The farm visit decides." in html
    assert "A missing record does not stop an assessment." in html
    for term in ("you are ready", "you qualify", "you are eligible", "approved"):
        assert term not in html.lower()


def test_the_category_is_resolved_from_the_ticks(seeded, crops_live, payload):
    report = submit(
        {**payload, "A1": ["CROPS", "AGRO_PROCESSING"]},
        research_consent=True,
        demographic_consent=False,
    )
    assert report.category is not None
    assert report.category.code == "CROPS"
    assert report.other_categories == ["AGRO_PROCESSING"]
    assert Category.objects.filter(code="AGRO_PROCESSING").exists()
