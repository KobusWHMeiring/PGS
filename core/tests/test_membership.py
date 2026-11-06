"""Task A1 — farms and members.

The membership half of the domain: `Member`, `Farm`, `FarmAlias`, `FarmCategory`,
`FarmContact` (spec §4.1). Everything here is a *rule the OPP states*, expressed so
that breaking it fails a test rather than a visit.

Three decisions this file pins, each with the reason it is pinned:

- **`is_paid_up` is derived, never stored** (D39). A stored boolean is a second
  source of truth that goes stale the day a period rolls over.
- **`is_paid_up` reads the row's own period**, not the calendar year (D39). "Payable
  by the end of February" is group policy, and group policy is data — a February
  deadline must never be hardcoded in the model.
- **`FarmCategory.status` has no pre-application value** (D36). This is the one that
  guards the front door: the public self-check ends with an optional "save my
  details" account, and a *tick* in that check must not be able to become a
  `FarmCategory`. See `test_a_tick_is_not_an_application`.

Census fields (FORM Sheet A: gender, age band, demographic group) belong to the
*person*, so they live on `Member` and never on `Farm` — a public farm page has no
route to them by construction rather than by remembering an exclusion list.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import (
    Category,
    Farm,
    FarmAlias,
    FarmCategory,
    FarmContact,
    Member,
    MembershipFee,
)

pytestmark = pytest.mark.django_db


# --- The plan's named tests ---------------------------------------------------


def test_member_is_paid_up_is_derived_not_stored(member):
    assert not member.is_paid_up
    today = timezone.localdate()
    MembershipFee.objects.create(
        member=member,
        amount_cents=10000,
        paid_on=today,
        period_start=today - timedelta(days=30),
        period_end=today + timedelta(days=30),
    )
    assert Member.objects.get(pk=member.pk).is_paid_up is True


def test_is_paid_up_uses_the_row_period_not_the_calendar_year(member):
    # D39: periods are explicit on the row, so "payable by end of February" is never
    # hardcoded. The payment is in a *previous* calendar year but its period covers
    # today, so a calendar-year rule calls this unpaid and the row rule calls it paid.
    #
    # Deliberately relative to today: the plan's version of this test hardcoded
    # 2025-03-01..2026-02-28 and started failing on 2026-03-01. A fee test that names
    # a date is a test with an expiry date of its own.
    today = timezone.localdate()
    MembershipFee.objects.create(
        member=member,
        amount_cents=10000,
        paid_on=today - timedelta(days=400),
        period_start=today - timedelta(days=30),
        period_end=today + timedelta(days=30),
    )
    assert Member.objects.get(pk=member.pk).is_paid_up is True


def test_an_expired_period_is_not_paid_up_even_though_it_was_paid(member):
    # The other half of the rule: "paid" is not "paid up". A lapsed membership is
    # exactly this row, and `assert_eligible_for_assessment` depends on the difference.
    today = timezone.localdate()
    MembershipFee.objects.create(
        member=member,
        amount_cents=10000,
        paid_on=today - timedelta(days=400),
        period_start=today - timedelta(days=400),
        period_end=today - timedelta(days=35),
    )
    assert Member.objects.get(pk=member.pk).is_paid_up is False


def test_an_unpaid_fee_is_not_paid_up(member):
    today = timezone.localdate()
    MembershipFee.objects.create(
        member=member,
        amount_cents=10000,
        paid_on=None,
        period_start=today - timedelta(days=30),
        period_end=today + timedelta(days=30),
    )
    assert Member.objects.get(pk=member.pk).is_paid_up is False


def test_probation_has_an_end_date(member):
    # D38: OPP §4.6 — probation is one calendar year. A status you can enter but
    # never leave is a data trap.
    member.status = "PROBATION"
    member.probation_until = date(2027, 3, 1)
    member.save()
    assert Member.objects.get(pk=member.pk).probation_until == date(2027, 3, 1)


def test_farm_has_no_catchment_and_no_postgis_field(farm):
    # D37 (catchment is a deployment setting) and D34 (no PostGIS, no GDAL).
    assert not hasattr(farm, "catchment")
    assert farm.latitude is None and farm.longitude is None
    assert "location" not in {f.name for f in Farm._meta.get_fields()}


def test_farm_aliases_resolve_to_one_canonical_farm(farm):
    # §4.1: the live records spell the same farm several ways. "Chillin Out Farm"
    # and "CHILLOUT FARM" must never fork into two farms.
    for spelling in ("CHILLOUT FARM", "Chillin Out Farm", "chillout  farm"):
        FarmAlias.objects.create(farm=farm, name=spelling, source="live site")

    assert Farm.resolve("chillout farm") == farm
    assert Farm.resolve("CHILLOUT FARM") == farm
    assert Farm.resolve("  Chillin Out Farm ") == farm


def test_resolve_survives_a_run_of_internal_whitespace(farm_factory):
    # The exact/iexact path cannot match this one, so it exercises the normalised
    # scan. Without this test that branch is decoration (testing_hazards §0).
    farm = farm_factory(name="Hamel  en   Harden", slug="hamel-en-harden")
    assert Farm.resolve("hamel en harden") == farm


def test_resolve_returns_none_rather_than_a_near_match(farm):
    # A verification lookup must never land on a farm it was not asked about.
    assert Farm.resolve("Chillin Out") is None
    assert Farm.resolve("") is None
    assert Farm.resolve("   ") is None


def test_farm_public_uuid_is_not_sequential(farm):
    assert isinstance(farm.public_uuid, uuid.UUID)
    assert farm.public_uuid.int > 10**20


# --- Membership identity (D39) ------------------------------------------------


def test_membership_no_is_human_facing_not_a_bare_autoincrement(member):
    # D39: printed on certificates, so it is PUBLIC and must be shaped
    # OUT-<year>-<seq:04d>, never a raw pk.
    assert member.membership_no.startswith("OUT-")
    year, seq = member.membership_no.split("-")[1:]
    assert len(year) == 4 and year.isdigit()
    assert len(seq) == 4 and seq.isdigit()


def test_membership_no_is_unique(member):
    with pytest.raises(IntegrityError), transaction.atomic():
        Member.objects.create(user=member.user, membership_no=member.membership_no)


# --- The guards this session added (the front door) ---------------------------


def test_member_status_is_exactly_the_five_frozen_values():
    # The self-check ends with an optional "save my details" account. The obvious
    # shortcut is a sixth status ("PROSPECT"/"REGISTERED") so that an account which
    # has not applied can exist. That is a DECISION, not an edit: `status` gates
    # `assert_eligible_for_assessment` and feeds `FarmCategory`, so a sixth value
    # changes the meaning of every gate downstream. If this test fails, write the
    # decision row first — do not add the choice.
    assert [c[0] for c in Member._meta.get_field("status").choices] == [
        "APPLICANT",
        "ACTIVE",
        "PROBATION",
        "LAPSED",
        "TERMINATED",
    ]


def test_a_tick_is_not_an_application(farm):
    # SELF_CHECK_PRD §4.1: "a tick is not an application" — the self-check's
    # category answers are labels, deliberately not FKs. D36 gives FarmCategory a
    # four-value application lifecycle, and every one of them asserts that an
    # APPLICATION exists. There must be no value a tick could land in.
    assert [c[0] for c in FarmCategory._meta.get_field("status").choices] == [
        "APPLIED",
        "FOR_ASSESSMENT",
        "ASSESSED",
        "INACTIVE",
    ]
    assert FarmCategory._meta.get_field("status").default == "APPLIED"


def test_census_fields_are_on_the_member_not_the_farm(member, farm):
    # FORM Sheet A census fields describe a person, not a place. Keeping them off
    # `Farm` means a public farm page cannot leak them by construction. The
    # serializer-level guard lands with the first public farm surface (MVP 2).
    for field in ("census_gender", "census_age_band", "census_demographic_group"):
        assert field not in {f.name for f in Farm._meta.get_fields()}, field
    assert [f.name for f in Member._meta.get_fields() if f.name.startswith("census_")] == [
        "census_gender",
        "census_age_band",
        "census_demographic_group",
    ]


# --- Farm identity and contacts ----------------------------------------------


def test_a_farm_belongs_to_a_member_and_can_carry_contacts(member, farm):
    FarmContact.objects.create(
        farm=farm, name="Anna", role="HOSTING", phone="044 000 0000", email=""
    )
    assert list(farm.contacts.all()) == list(FarmContact.objects.filter(farm=farm))
    assert farm.member == member


def test_farm_slug_is_unique(farm):
    with pytest.raises(IntegrityError), transaction.atomic():
        Farm.objects.create(member=farm.member, name="Another", slug=farm.slug)


def test_a_farm_can_hold_several_categories(farm, category):
    # §4.1: FarmCategory is 1..n per farm — a farm that grows crops and processes
    # them holds two rows, one lifecycle each.
    FarmCategory.objects.create(farm=farm, category=category)
    FarmCategory.objects.create(
        farm=farm, category=Category.objects.create(code="AGRO", label="Agro-processing")
    )
    assert farm.categories.count() == 2


def test_the_same_category_cannot_be_applied_for_twice(farm, category):
    FarmCategory.objects.create(farm=farm, category=category)
    with pytest.raises(IntegrityError), transaction.atomic():
        FarmCategory.objects.create(farm=farm, category=category)
