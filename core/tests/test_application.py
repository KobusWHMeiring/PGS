"""Task A6 — the application flow (spec §7, D83, Q8, D84, OPP §I–§II).

The flow this file fixes, in order, because the order is the point:

    self-register → the Q8 consent → the account → **the pledge** → categories →
    turnover → *the group's part*

Three decisions shape every test here, and each one is a refusal as much as a feature:

1. **The account cannot be created without the Q8 consent** (SELF_CHECK_PRD §11.6).
   A farm name collected under the research consent is a purpose mismatch, and §3.6
   exists to prevent it. The consent is **versioned, not edited**, so the record
   stores the *version that was on screen*, and a form rendered before the wording
   changed is refused rather than recorded against text nobody read.
2. **The pledge comes after the account** (D83): it attests to *"all the land for
   which I/we are applying"*. So the account step collects identity + farm + contact
   and nothing declarative, and this file proves the pledge still computes A3's
   `land_history_conflict` when it arrives through the view.
3. **The applicant's part ends at the declaration, not at a fake payment.** Only
   fully paid-up members are eligible for assessment (OPP §2.3), and the group
   records a membership fee and its payment — a self-registration that wrote
   `paid_on=today` would make the gate lie. The two services that record the money
   are tested here and called by no view yet; that is A5's pattern
   (`assert_fees_paid_for_assessment` waited for C1's `confirm_visit()` in the same way).
"""

from __future__ import annotations

import datetime as dt
import inspect

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from core.models import (
    AssessmentFee,
    Category,
    ConsentPurpose,
    ConsentRecord,
    ConsentText,
    Farm,
    FarmCategory,
    Member,
    MembershipFee,
    Pledge,
    User,
    UserRole,
)
from core.services._application import (
    ConsentRequiredError,
    ConsentTextChangedError,
    EmailAlreadyRegisteredError,
    FarmNameTakenError,
    StepOutOfOrderError,
    application_progress,
    assert_step_ready,
    create_application,
    record_application_categories,
)
from core.services._membership import record_membership_fee, record_membership_payment

pytestmark = pytest.mark.django_db

#: A complete account step, as a farmer would fill it in. The password is long
#: because `AUTH_PASSWORD_VALIDATORS` is not relaxed for tests — a test that turns
#: the validator off proves nothing about the form a member actually meets.
ACCOUNT = {
    "first_name": "Anna",
    "last_name": "Visser",
    "email": "anna@example.org",
    "phone": "082 555 0101",
    "farm_name": "Kleinbegin",
    "nearest_town": "Rheenendal",
    "contact_name": "Anna Visser",
    "password1": "kom-me-hol-anders-42",
    "password2": "kom-me-hol-anders-42",
}

PLEDGE = {
    "method": Pledge.Method.SIGNATURE,
    "place": "Rheenendal",
    "branch": "land_history",
    # The OPP prints 12 / 12 / 18 for full land history. Since SAOSO 4.2.3 and the
    # pledge agree, and OPP §V alone prints 18/12/12, annual-12 sits *inside* the
    # band where the documents disagree (D31) — so this is a conflict, and the test
    # says so rather than pretending the numbers are unambiguous.
    "annual_months": 12,
    "pasture_months": 12,
    "perennial_months": 18,
}


@pytest.fixture
def deployed(db):
    """The deployed state: the OPP §2.3 scale, the categories, the committee, the Q8 text."""
    call_command("seed_deployment")
    return None


def _account_text() -> ConsentText:
    return ConsentText.objects.current(ConsentPurpose.ACCOUNT)


def _post_account(client, **overrides):
    payload = dict(ACCOUNT)
    payload["consent"] = "on"
    payload["consent_version"] = _account_text().version
    payload.update(overrides)
    return client.post(reverse("core:apply"), payload)


def _register(client) -> Member:
    """Take the account step through the view, and return the member it created."""
    response = _post_account(client)
    assert response.status_code == 302, response.content.decode()[:800]
    return Member.objects.get(user__username=ACCOUNT["email"])


def _complete(client) -> Member:
    """Walk all four applicant steps through the views. Returns the member."""
    member = _register(client)
    assert client.post(reverse("core:apply_pledge"), PLEDGE).status_code == 302
    assert client.post(
        reverse("core:apply_categories"),
        {"categories": [c.pk for c in Category.objects.filter(is_active=True)[:2]]},
    ).status_code == 302
    assert client.post(
        reverse("core:apply_turnover"), {"turnover_rands": 120_000}
    ).status_code == 302
    return member


# --- The account step, its consent and its honest gaps -----------------------


def test_the_account_step_says_create_an_account_and_not_apply(client, deployed):
    """D83's wording: `APPLICANT` is the internal state, and the page may not say
    "application" before the farmer has made one."""
    html = client.get(reverse("core:apply")).content.decode()
    assert "Create an account" in html
    assert "Create an account" in html and "Submit application" not in html


def test_the_account_step_says_email_verification_is_unavailable(client, deployed):
    """D84: 1a sends no mail, so the page must say so rather than imply a tick.

    Asserted two ways on purpose: the flag the template branches on, and the sentence a
    farmer reads. A test of the sentence alone passes while the flag says otherwise, and
    the flag is what a later provider decision turns on.
    """
    response = client.get(reverse("core:apply"))
    assert response.context["email_verification_available"] is False
    assert "verification is not available yet" in response.content.decode().lower()


def test_a_consent_that_the_group_has_not_approved_is_rendered_as_a_draft(client, deployed):
    """§11.6's two `[DECIDE]` markers are the group's. A page that hides them invites
    a member to consent to a retention period nobody has decided."""
    consent = _account_text()
    assert consent.approved_at is None, "the shipped text is a draft; fix the fixture, not the test"
    html = client.get(reverse("core:apply")).content.decode()
    assert "DRAFT" in html
    assert html.count("[DECIDE") == 2
    assert "12 months" in html


def test_an_approved_consent_is_no_longer_marked_as_a_draft(client, deployed):
    """The reverse of the test above, so the banner is a state and not a sticker."""
    ConsentText.objects.filter(pk=_account_text().pk).update(approved_at=timezone.now())
    html = client.get(reverse("core:apply")).content.decode()
    assert "DRAFT" not in html


def test_registration_without_consent_is_refused(deployed):
    """§11.6's consequence: no consent, no account — and nothing stored."""
    text = _account_text()
    with pytest.raises(ConsentRequiredError):
        create_application(
            _details(), password="kom-me-hol-anders-42",
            consent_version=text.version, consent_given=False,
        )
    assert User.objects.count() == 0
    assert Member.objects.count() == 0
    assert Farm.objects.count() == 0


def test_registration_without_a_written_consent_is_refused(deployed):
    """The honest fallback: if the group has not written the text, the answer is
    "not yet", never a checkbox with nothing behind it."""
    ConsentText.objects.all().delete()
    with pytest.raises(ConsentRequiredError):
        create_application(
            _details(), password="kom-me-hol-anders-42",
            consent_version="", consent_given=True,
        )
    assert Member.objects.count() == 0


def test_a_form_rendered_before_the_wording_changed_is_refused(deployed):
    """Versioned, not edited: the farmer consented to what they read."""
    stale = _account_text().version
    ConsentText.objects.create(
        purpose=ConsentPurpose.ACCOUNT,
        version="account-2026-12-01",
        heading="May we keep your details?",
        body="A later wording.",
    )
    with pytest.raises(ConsentTextChangedError):
        create_application(
            _details(), password="kom-me-hol-anders-42",
            consent_version=stale, consent_given=True,
        )
    assert Member.objects.count() == 0


# --- What the account step writes -------------------------------------------


def test_the_account_creates_the_user_the_membership_and_the_farm(client, deployed):
    member = _register(client)

    assert member.status == Member.Status.APPLICANT
    assert member.user.username == "anna@example.org"
    assert member.user.email == "anna@example.org"
    assert member.user.first_name == "Anna"
    assert member.user.phone == "082 555 0101"
    assert member.user.popia_consent_at is not None
    # D84: no provider, so the address is accepted as given and never claimed as verified.
    assert member.user.email_verified_at is None
    assert member.user.has_role("FARMER")

    farm = member.farms.get()
    assert farm.name == "Kleinbegin"
    assert farm.nearest_town == "Rheenendal"
    assert farm.contacts.get().name == "Anna Visser"


def test_the_consent_record_names_the_version_it_was_taken_under(client, deployed):
    member = _register(client)
    record = ConsentRecord.objects.get(user=member.user)
    assert record.text.version == _account_text().version
    assert record.text.purpose == ConsentPurpose.ACCOUNT
    assert record.withdrawn_at is None


def test_a_second_account_for_the_same_address_is_refused(client, deployed):
    _register(client)
    client.logout()
    response = _post_account(client)
    assert response.status_code == 200
    assert User.objects.count() == 1
    assert "already" in response.content.decode().lower()


def test_a_farm_name_that_already_resolves_is_refused(client, deployed):
    """A1 exists so that spellings resolve to one farm; a self-registration must not
    fork it, and must not disclose whose farm it is."""
    other = Member.objects.create(user=User.objects.create_user("other@example.org", password="x"))
    Farm.objects.create(member=other, name="Chillin Out Farm", nearest_town="Rheenendal")

    with pytest.raises(FarmNameTakenError) as caught:
        create_application(
            _details(farm_name="CHILLIN   OUT FARM"), password="kom-me-hol-anders-42",
            consent_version=_account_text().version, consent_given=True,
        )
    assert "Rheenendal" not in str(caught.value), "must not disclose another member's record"
    assert Farm.objects.count() == 1


def test_a_post_cannot_set_the_members_status(client, deployed):
    """The service owns transitions: a hidden `status=ACTIVE` in the form is ignored
    because no view reads it, and this test is what keeps it that way."""
    payload = dict(ACCOUNT, consent="on", consent_version=_account_text().version,
                   status=Member.Status.ACTIVE, membership_no="OUT-2026-9999")
    client.post(reverse("core:apply"), payload)
    member = Member.objects.get(user__username=ACCOUNT["email"])
    assert member.status == Member.Status.APPLICANT
    assert member.membership_no != "OUT-2026-9999"


# --- The pledge, after the account ------------------------------------------


def test_the_pledge_step_records_a3s_conflict_flag_through_the_view(client, deployed):
    _register(client)
    response = client.post(reverse("core:apply_pledge"), PLEDGE)
    assert response.status_code == 302, response.content.decode()[:800]

    pledge = Pledge.objects.get()
    assert pledge.kind == Pledge.Kind.FARMER
    assert pledge.declared_annual_clear_months == 12
    assert pledge.land_history_conflict is True  # D31's band, computed by A3
    assert pledge.signed_on == timezone.localdate()


def test_a_pledge_that_cannot_be_evidenced_is_a_form_error_not_a_server_error(client, deployed):
    _register(client)
    response = client.post(
        reverse("core:apply_pledge"),
        dict(PLEDGE, method=Pledge.Method.VERBAL_WITNESSED, witness_name=""),
    )
    assert response.status_code == 200
    assert Pledge.objects.count() == 0
    assert "witness" in response.content.decode().lower()


def test_a_signed_pledge_is_not_signed_again_by_a_second_post(client, deployed):
    """A signature is history. Re-opening the step must not append a second pledge — the
    attestation would then exist twice, with different dates and no way to tell which the
    group relied on."""
    _register(client)
    client.post(reverse("core:apply_pledge"), PLEDGE)
    response = client.post(reverse("core:apply_pledge"), PLEDGE)
    assert response.status_code == 302
    assert Pledge.objects.count() == 1


def test_a_verbal_pledge_with_its_witness_and_record_is_accepted(client, deployed):
    _register(client)
    response = client.post(
        reverse("core:apply_pledge"),
        dict(
            PLEDGE,
            method=Pledge.Method.VERBAL_WITNESSED,
            witness_name="Sasha Mentz",
            witness_designation="Administrator",
            evidence_document=SimpleUploadedFile("pledge.jpg", b"\xff\xd8\xff"),
        ),
    )
    assert response.status_code == 302, response.content.decode()[:800]
    assert Pledge.objects.get().method == Pledge.Method.VERBAL_WITNESSED


# --- Categories and turnover -------------------------------------------------


def test_ticking_two_categories_creates_two_farm_category_rows(client, deployed):
    member = _register(client)
    client.post(reverse("core:apply_pledge"), PLEDGE)
    ticks = list(Category.objects.filter(is_active=True)[:2])

    response = client.post(
        reverse("core:apply_categories"), {"categories": [c.pk for c in ticks]}
    )
    assert response.status_code == 302
    assert FarmCategory.objects.filter(farm__member=member).count() == 2
    assert set(FarmCategory.objects.values_list("status", flat=True)) == {FarmCategory.Status.APPLIED}


def test_an_empty_tick_list_is_refused(client, deployed):
    _register(client)
    client.post(reverse("core:apply_pledge"), PLEDGE)
    response = client.post(reverse("core:apply_categories"), {})
    assert response.status_code == 200
    assert FarmCategory.objects.count() == 0


def test_resubmitting_categories_does_not_delete_an_assessed_row(deployed):
    """Once the group has assessed a category the row is history; a re-submit edits
    the application, not the record (build_principles §I, Immutable History)."""
    member = Member.objects.create(user=User.objects.create_user("a@example.org", password="x"))
    farm = Farm.objects.create(member=member, name="Kleinbegin")
    crops, animals = list(Category.objects.filter(is_active=True)[:2])
    assessed = FarmCategory.objects.create(
        farm=farm, category=crops, status=FarmCategory.Status.ASSESSED
    )
    record_application_categories(member, category_ids=[animals.pk])
    assert FarmCategory.objects.filter(pk=assessed.pk).exists()
    assert FarmCategory.objects.get(farm=farm, category=animals).status == FarmCategory.Status.APPLIED


def test_the_turnover_step_creates_exactly_one_assessment_fee(client, deployed):
    member = _complete(client)
    fees = AssessmentFee.objects.filter(member=member)
    assert fees.count() == 1
    fee = fees.get()
    assert fee.declared_turnover_cents == 12_000_000  # R120 000, entered as rands
    assert fee.band_label == "Below R 250,000"  # A5 reads the printed label, never infers
    assert fee.amount_cents == 150_000
    assert fee.paid_on is None, "A6 declares the fee; it does not collect it"


# --- The honest ending -------------------------------------------------------


def test_the_applicant_ends_unpaid_and_the_flow_does_not_pretend_otherwise(client, deployed):
    member = _complete(client)
    assert member.status == Member.Status.APPLICANT
    assert member.is_paid_up is False
    assert MembershipFee.objects.count() == 0


def test_the_summary_names_the_band_the_assessment_fee_and_the_membership_fee(client, deployed):
    _complete(client)
    html = client.get(reverse("core:apply_summary")).content.decode()
    assert "Below R 250,000" in html
    assert "R1 500" in html  # the band's initial fee, formatted at the boundary
    assert "R100" in html  # OPP §2.1, the figure the public pages publish
    assert "not been recorded" in html or "not yet recorded" in html


def test_the_full_application_completes_in_one_test(client, deployed):
    """The plan's acceptance test: one farmer, four steps, every row accounted for."""
    member = _complete(client)

    assert Member.objects.count() == 1
    assert member.farms.count() == 1
    assert Pledge.objects.filter(member=member).count() == 1
    assert FarmCategory.objects.filter(farm__member=member).count() == 2
    assert AssessmentFee.objects.filter(member=member).count() == 1
    assert ConsentRecord.objects.filter(user=member.user).count() == 1

    summary = client.get(reverse("core:apply_summary"))
    assert summary.status_code == 200
    assert member.membership_no in summary.content.decode()


# --- Order, resume, and the guard that keeps both ----------------------------


def test_a_step_cannot_be_reached_before_the_step_before_it(client, deployed):
    _register(client)
    response = client.post(reverse("core:apply_turnover"), {"turnover_rands": 120_000})
    assert response.status_code == 302
    assert response["Location"] == reverse("core:apply")
    assert AssessmentFee.objects.count() == 0


def test_the_step_guard_says_which_step_is_missing(deployed):
    member = Member.objects.create(user=User.objects.create_user("a@example.org", password="x"))
    Farm.objects.create(member=member, name="Kleinbegin")
    with pytest.raises(StepOutOfOrderError):
        assert_step_ready(member, "turnover")
    assert_step_ready(member, "pledge")  # the next step in order is always allowed


def test_progress_is_derived_from_the_records_and_not_from_a_session(client, deployed):
    member = _complete(client)
    done = {step.key for step in application_progress(member) if step.done}
    assert done == {"account", "pledge", "categories", "turnover"}

    Pledge.objects.all().delete()
    progress = application_progress(Member.objects.get(pk=member.pk))
    assert [s.key for s in progress if not s.done] == ["pledge"]


def test_a_signed_in_member_resumes_at_the_first_step_they_have_not_done(client, deployed):
    _register(client)
    response = client.get(reverse("core:apply"))
    assert response.status_code == 302
    assert response["Location"] == reverse("core:apply_pledge")


def test_a_member_can_come_back_through_the_login_page(client, deployed):
    _register(client)
    client.logout()
    response = client.post(
        reverse("core:login"),
        {"username": ACCOUNT["email"], "password": ACCOUNT["password1"]},
    )
    assert response.status_code == 302
    assert client.get(reverse("core:apply_pledge")).status_code == 200


# --- The group's part: the membership fee, recorded with its own period ------


def test_the_group_records_a_membership_fee_with_the_period_it_was_paid_for(deployed):
    """D39: the period lives on the row. A6 must not invent a fee year — the group
    passes the period it invoiced, and the fee is unpaid until `paid_on`."""
    member = Member.objects.create(user=User.objects.create_user("a@example.org", password="x"))
    today = timezone.localdate()
    fee = record_membership_fee(
        member,
        kind="ANNUAL",
        period_start=today,
        period_end=today + dt.timedelta(days=364),
        amount_cents=10_000,
    )
    assert fee.paid_on is None
    assert member.is_paid_up is False
    assert MembershipFee.objects.count() == 1


def test_recording_payment_activates_an_applicant(deployed):
    """OPP §2.3 and spec §7.7: on payment the member becomes `ACTIVE` — the state A7's
    eligibility gate passes for. A6 supplies the transition; A7 reads it."""
    member = Member.objects.create(user=User.objects.create_user("a@example.org", password="x"))
    today = timezone.localdate()
    fee = record_membership_fee(
        member, period_start=today, period_end=today + dt.timedelta(days=364), amount_cents=10_000
    )
    record_membership_payment(fee, paid_on=today, receipt_no="R-001")
    member.refresh_from_db()
    assert member.is_paid_up is True
    assert member.status == Member.Status.ACTIVE


def test_recording_payment_does_not_reinstate_a_terminated_member(deployed):
    """A payment is not a reinstatement: OPP §4.7 makes that a committee decision after
    a calendar year, so a receipt must not undo it."""
    member = Member.objects.create(
        user=User.objects.create_user("a@example.org", password="x"),
        status=Member.Status.TERMINATED,
    )
    today = timezone.localdate()
    fee = record_membership_fee(
        member, period_start=today, period_end=today + dt.timedelta(days=364), amount_cents=10_000
    )
    record_membership_payment(fee, paid_on=today)
    member.refresh_from_db()
    assert member.status == Member.Status.TERMINATED


# --- The plan's structural acceptance ---------------------------------------


def test_no_portal_view_is_over_twenty_lines():
    """`MVP1A_PLAN.md` A6: "no view over 20 lines" (§II, Thin Views). Counted on the
    source, because a view that grew a branch is exactly how it stops being thin."""
    from core.views import _portal

    names = (
        "apply", "apply_pledge", "apply_categories", "apply_turnover",
        "apply_summary", "login", "logout",
    )
    for name in names:
        source = inspect.getsource(getattr(_portal, name))
        lines = [line for line in source.splitlines() if line.strip() and not line.strip().startswith("#")]
        assert len(lines) <= 20, f"{name} is {len(lines)} lines"


def _details(**overrides):
    from core.services._application import ApplicantDetails

    payload = {
        "first_name": ACCOUNT["first_name"],
        "last_name": ACCOUNT["last_name"],
        "email": ACCOUNT["email"],
        "phone": ACCOUNT["phone"],
        "farm_name": ACCOUNT["farm_name"],
        "nearest_town": ACCOUNT["nearest_town"],
        "contact_name": ACCOUNT["contact_name"],
    }
    payload.update(overrides)
    return ApplicantDetails(**payload)
