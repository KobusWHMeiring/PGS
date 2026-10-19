"""Task A4 — `Category` and `Seal` as data, the seed, and the seal-issuance guard.

The governing rule (spec §4.8, `build_principles.md` §I): *code encodes the PGS
process; data encodes the standard and the group.* Seals and categories are
therefore **tables, not enums**, and the acceptance test for that is: **retargeting
to another standard or PGS group must not require a migration.**

The trap this file exists to prevent is D11/F3. OPP §V authorises three marks, and
the third — "PGS pasture-raised" — carries the standard's own admission that its
criteria are *"details on this forthcoming"*. Verified against the shipped PDF, not
against the spec: `pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf`,
§V. A mark whose criteria the standard calls forthcoming cannot be substantiated to
a consumer, so:

1. `is_active=False` blocks issuance **unconditionally** — no administrator override;
2. an inactive seal is **never rendered** on a public page.

Scope note: the plan's A4 snippet calls `certificate_factory(...)`, but `Certificate`
is an **MVP 2** model and HANDOVER §4 says not to build it. The guard is therefore a
service function (`assert_seal_issuable`) rather than a model save hook — which is
also where `build_principles.md` §II puts business rules. When MVP 2's Certificate
arrives, its service calls this same guard; the invariant is tested today without
pre-building an MVP 2 model.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command

from core.models import Category, Seal
from core.services._certification import (
    InactiveSealError,
    UndefinedCriteriaError,
    assert_seal_issuable,
    issuable_seals,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded():
    """The deployed Outeniqua state. Seeding is idempotent, so this is safe."""
    call_command("seed_deployment")
    return None


# --- Seals: the active set (the plan's first test) ---------------------------


def test_only_two_seals_are_active(seeded):
    active = set(Seal.objects.filter(is_active=True).values_list("code", flat=True))
    assert active == {"PGS_ORGANIC_CERTIFIED", "PGS_ORGANIC_IN_CONVERSION"}
    assert Seal.objects.get(code="PGS_PASTURE_RAISED").is_active is False
    assert Seal.objects.get(code="PGS_PASTURE_RAISED").criteria_defined is False


def test_seal_set_is_exactly_the_three_marks_opp_v_authorises(seeded):
    """OPP §V lists three marks — "there are three, not two" (spec §4.3).

    A fourth seal invented in code, or one silently dropped, changes what the
    platform can claim on a public page. Pinned as a literal set.
    """
    assert set(Seal.objects.values_list("code", flat=True)) == {
        "PGS_ORGANIC_CERTIFIED",
        "PGS_ORGANIC_IN_CONVERSION",
        "PGS_PASTURE_RAISED",
    }


def test_every_seal_cites_the_standard_clause_it_comes_from(seeded):
    """A seal with no `standard_ref` is an unsubstantiated claim with a database row."""
    for seal in Seal.objects.all():
        assert seal.standard_ref.strip(), seal.code


def test_pasture_raised_keeps_a_reason_for_being_inactive(seeded):
    """The row is dormant, not forgotten. `display_note` records why, so the next
    reader does not "fix" the inactive flag by enabling it."""
    pasture = Seal.objects.get(code="PGS_PASTURE_RAISED")
    assert pasture.display_note.strip()
    assert "forthcoming" in pasture.display_note.lower()


# --- Seals: issuance is blocked, unconditionally (D11/F3) --------------------


def test_inactive_seal_cannot_be_issued(seeded):
    with pytest.raises(InactiveSealError):
        assert_seal_issuable(Seal.objects.get(code="PGS_PASTURE_RAISED"))


def test_inactive_seal_cannot_be_issued_even_with_an_override_rationale(seeded):
    """The distinction that matters, and the one a future reader would get wrong.

    `criteria_defined=False` on an **active** seal is overridable by an
    administrator with a recorded rationale (spec §4.3). `is_active=False` is not:
    "no administrator override" is explicit, because a seal with no published
    criteria is a claim that cannot be substantiated. An override must not become
    a bypass for the one seal the group has decided not to ship.
    """
    with pytest.raises(InactiveSealError):
        assert_seal_issuable(
            Seal.objects.get(code="PGS_PASTURE_RAISED"),
            override_rationale="approved by the committee at the AGM",
        )


def test_active_seals_are_issuable(seeded):
    for code in ("PGS_ORGANIC_CERTIFIED", "PGS_ORGANIC_IN_CONVERSION"):
        assert_seal_issuable(Seal.objects.get(code=code))  # does not raise


def test_active_seal_without_defined_criteria_needs_a_recorded_rationale(seeded):
    """Spec §4.3's general case: an active seal whose criteria cannot be
    machine-checked requires an administrator override *with a rationale*."""
    seal = Seal.objects.get(code="PGS_ORGANIC_CERTIFIED")
    seal.criteria_defined = False
    seal.save()

    with pytest.raises(UndefinedCriteriaError):
        assert_seal_issuable(seal)

    assert_seal_issuable(seal, override_rationale="criteria assessed manually")  # ok


def test_an_override_must_actually_say_something(seeded):
    """An empty string is not a recorded rationale — otherwise the audit trail is
    satisfied by a blank field."""
    seal = Seal.objects.get(code="PGS_ORGANIC_CERTIFIED")
    seal.criteria_defined = False
    seal.save()
    with pytest.raises(UndefinedCriteriaError):
        assert_seal_issuable(seal, override_rationale="   ")


def test_issuable_seals_excludes_the_deferred_mark(seeded):
    """Whatever lists seals for issuance must not offer pasture-raised.

    This is the query a future form or API would reuse, so the exclusion is
    asserted at the query rather than trusted at each call site.
    """
    codes = set(issuable_seals().values_list("code", flat=True))
    assert codes == {"PGS_ORGANIC_CERTIFIED", "PGS_ORGANIC_IN_CONVERSION"}


# --- Categories -------------------------------------------------------------


def test_categories_in_development_are_seeded_inactive_not_omitted(seeded):
    """Spec §4.1: the last three are *in development* in FORM Sheets F/G/H.

    Seeded inactive rather than omitted, so publishing them later is a data change
    and the schema never needs a migration for a new category.
    """
    active = set(Category.objects.filter(is_active=True).values_list("code", flat=True))
    assert active == {"CROPS", "ANIMAL_HUSBANDRY", "SEED_PRODUCTION", "AGRO_PROCESSING"}

    inactive = set(Category.objects.filter(is_active=False).values_list("code", flat=True))
    assert inactive == {"AQUACULTURE", "WINE", "INPUT_SUPPLIER"}


def test_category_set_is_exactly_the_deployed_set(seeded):
    assert set(Category.objects.values_list("code", flat=True)) == {
        "CROPS",
        "ANIMAL_HUSBANDRY",
        "SEED_PRODUCTION",
        "AGRO_PROCESSING",
        "AQUACULTURE",
        "WINE",
        "INPUT_SUPPLIER",
    }


def test_categories_are_ordered_for_display(seeded):
    """`display_order` exists so the admin and the public site agree without either
    hardcoding a list."""
    orders = list(Category.objects.values_list("display_order", flat=True))
    assert orders == sorted(orders)


# --- Seeding ----------------------------------------------------------------


def test_seeding_is_idempotent(seeded):
    """A seed that is not re-runnable cannot be part of a deploy."""
    call_command("seed_deployment")
    call_command("seed_deployment")
    assert Category.objects.filter(code="CROPS").count() == 1
    assert Seal.objects.filter(code="PGS_PASTURE_RAISED").count() == 1


def test_seeding_does_not_reactivate_a_seal_a_deployment_switched_off(seeded):
    """Re-running the seed must not undo a deliberate deployment decision.

    Concretely: if the group retires a seal, `seed_deployment` on the next release
    must not silently bring it back and resume publishing a claim.
    """
    Seal.objects.filter(code="PGS_ORGANIC_IN_CONVERSION").update(is_active=False)
    call_command("seed_deployment")
    assert Seal.objects.get(code="PGS_ORGANIC_IN_CONVERSION").is_active is False


# --- Data, not code (§4.8) --------------------------------------------------


def test_seal_and_category_are_data_not_enums(seeded):
    """The acceptance test for §4.8, asserted on the schema.

    A `choices=` list on `code` would make adding a seal or a category a *code*
    change, and a `makemigrations` run — exactly what "data, not code" forbids.
    """
    assert Seal._meta.get_field("code").choices is None
    assert Category._meta.get_field("code").choices is None

    # And the proof by behaviour: a brand-new seal and category are insertable
    # with no schema change.
    Seal.objects.create(code="PGS_TEST_ONLY", label="Test", standard_ref="OPP §V")
    Category.objects.create(code="TEST_ONLY", label="Test", display_order=99)
    assert Seal.objects.filter(code="PGS_TEST_ONLY").exists()
