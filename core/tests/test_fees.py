"""Task A5 — the assessment fee scale, the declared fee, and the gate before a visit.

OPP §2.3 prints a six-band sliding scale, and the notes under it settle four things
that would otherwise be invented here. Each is cited because each one changes the code:

- *"Fees are per farm assessment visit."* — so the fee hangs off a **farm**, not a
  member. A member with three farms owes three fees, which is why `AssessmentFee`
  carries `farm` and spec §4.1's original line (member + visit only) could not say it.
- *"Fees are payable prior to the farm assessment visit."* and *"Only fully paid-up
  members will be eligible for farm assessments"* — two separate gates, and the
  membership one is checked first, because "you have not paid your membership" is a
  different sentence from "you have not paid this farm's assessment fee".
- *"Annual turnover is self-declared by the farmer and subject to peer review."* —
  declared, never inferred (§III, D29). The service stores what a human declared; it
  does not read a turnover from anywhere.
- *"Renewal fees apply only where no significant changes to land, production system, or
  inputs have occurred. Where major changes are identified, the PGS group may require a
  full assessment at the initial certification rate."* — so `RENEWAL` **plus**
  `is_significant_change=True` is a contradiction, not a discount. The group's
  discretion ("may require") stays with the group: the service refuses the pair rather
  than silently charging the higher rate, because a rule that quietly overrides a
  declared field is an adjudication.

**The scale is data, not code** (§4.8, D12, and spec §4.1's *"Content, not logic"* row).
`TurnoverBand` is a table seeded by `seed_deployment`, so a group that changes its fees
at the AGM edits rows rather than code, and the acceptance test for the whole of §4.8 —
*"a retarget must not require a migration"* — is exercised directly below by changing a
band's amount and watching the fee follow.

**The printed table has a hole, and the code closes it deliberately.** The bands read
*"Below R 250,000"* then *"R 250,001 – R 500,000"*, so a turnover of R250,000.50 belongs
to neither as printed. The rows therefore store *half-open cent bounds* (`min` inclusive,
`max` exclusive) and keep the printed text in `label`: R250,000.00 opens the second band.
Rounding to whole rand would be a second, invented rule on top of the first; half-open on
the cent is one rule and it leaves no turnover unbanded. `test_the_printed_scale_has_no_hole`
sweeps the scale to prove it.

A declared fee **snapshots** the band code, its printed label and the amount, rather than
pointing at the schedule row. The schedule is policy and it changes at an AGM; the fee row
is what somebody was asked to pay. A fee that re-read its amount from the current schedule
would silently re-price last year's invoice.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from core.models import AssessmentFee, Farm, MembershipFee, TurnoverBand
from core.services._membership import (
    AssessmentFeeUnpaidError,
    FeeScheduleNotSeededError,
    MembershipUnpaidError,
    SignificantChangeError,
    assert_assessment_fee_paid,
    assert_fees_paid_for_assessment,
    band_for,
    declare_assessment_fee,
    fee_cents_for,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def scale(db):
    """The deployed scale — seeded through the command a release runs, not hand-inserted."""
    call_command("seed_deployment")


def pay_membership(member):
    today = timezone.localdate()  # §1.35: never a hardcoded period
    return MembershipFee.objects.create(
        member=member,
        kind="ANNUAL",
        period_start=today - timedelta(days=30),
        period_end=today + timedelta(days=335),
        amount_cents=10_000,
        paid_on=today,
    )


# --- The scale, as the OPP prints it -----------------------------------------


OPP_SCALE = [
    # (declared turnover in cents, band code, initial cents, renewal cents)
    (0, "B1", 150_000, 90_000),  # "Below R 250,000"
    (24_999_999, "B1", 150_000, 90_000),
    (25_000_000, "B2", 250_000, 200_000),  # "R 250,001 – R 500,000"
    (49_999_999, "B2", 250_000, 200_000),
    (50_000_000, "B3", 300_000, 250_000),  # "R 500,001 – R 1,000,000"
    (100_000_000, "B4", 370_000, 320_000),  # "R 1,000,001 – R 2,500,000"
    (250_000_000, "B5", 500_000, 500_000),  # "R 2,500,001 – R 5,000,000"
    (500_000_000, "B6", 800_000, 800_000),  # "Above R 5,000,000"
    (9_999_999_999, "B6", 800_000, 800_000),
]


@pytest.mark.parametrize(("turnover_cents", "code", "initial", "renewal"), OPP_SCALE)
def test_turnover_band_matches_opp_2_3(scale, turnover_cents, code, initial, renewal):
    assert band_for(turnover_cents).code == code
    assert fee_cents_for(turnover_cents, kind=AssessmentFee.Kind.INITIAL) == initial
    assert fee_cents_for(turnover_cents, kind=AssessmentFee.Kind.RENEWAL) == renewal


def test_the_printed_scale_has_no_hole(scale):
    """Every cent of turnover belongs to exactly one band.

    As printed, "Below R 250,000" and "R 250,001 – R 500,000" leave R250,000.50
    unbanded. The rows store half-open bounds, so this sweep finds no gap and no
    overlap — the property the printed table cannot state about itself.

    The boundaries are checked **at the boundary**, not only at sampled cents: a sweep
    whose step never lands on R250,000.00 cannot tell half-open bounds from closed ones,
    and an earlier version of this test passed against a `<=` mutation for exactly that
    reason. Closing the bounds there put R250,000.00 in two bands at once, which is the
    hole's mirror image and just as wrong.
    """
    bands = list(TurnoverBand.objects.order_by("min_turnover_cents"))
    assert bands[0].min_turnover_cents == 0, "the scale must start at zero, not at a gap"
    assert bands[-1].max_turnover_cents is None, "the top band is open-ended"

    for lower, upper in zip(bands, bands[1:]):
        assert lower.max_turnover_cents == upper.min_turnover_cents, (
            f"{lower.code} ends at {lower.max_turnover_cents} but {upper.code} "
            f"starts at {upper.min_turnover_cents}"
        )

    probes = {0}
    for band in bands:
        probes.add(band.min_turnover_cents)
        probes.add(band.min_turnover_cents + 1)
        if band.max_turnover_cents is not None:
            probes.add(band.max_turnover_cents - 1)
            probes.add(band.max_turnover_cents)  # the cent the *next* band opens on
            probes.add(band.max_turnover_cents + 1)
    probes.update(range(0, 600_000_000, 3_333_333))

    for cents in sorted(probes):
        matches = [b for b in bands if b.covers(cents)]
        assert len(matches) == 1, f"{cents} cents matched {[b.code for b in matches]}"

    assert not any(b.covers(b.max_turnover_cents) for b in bands if b.max_turnover_cents), (
        "a band claims the cent that opens the next one: the bounds are closed, not half-open"
    )


def test_above_the_top_band_uses_the_open_ended_row(scale):
    top = fee_cents_for(10**12, kind=AssessmentFee.Kind.INITIAL)
    assert top == 800_000


def test_negative_turnover_is_refused(scale):
    with pytest.raises(ValueError):
        band_for(-1)


# --- Declared, not computed ----------------------------------------------------


def test_fee_is_declared_not_computed(scale, member, farm):
    # D29: turnover is self-declared and peer-reviewed, never inferred
    fee = declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL
    )
    assert fee.turnover_band == "B1"
    assert fee.declared_turnover_cents == 20_000_000
    assert fee.amount_cents == 150_000
    assert fee.band_label == "Below R 250,000"


def test_the_row_snapshots_the_band_it_was_declared_under(scale, member, farm):
    """A schedule change must not re-price a fee somebody was already asked to pay."""
    first = declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL
    )
    TurnoverBand.objects.filter(code="B1").update(initial_fee_cents=999_000)

    first.refresh_from_db()
    assert first.amount_cents == 150_000, "the declared fee moved with the schedule"

    second = declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL
    )
    assert second.amount_cents == 999_000, "a new declaration must read the current schedule"


def test_the_schedule_is_data_not_code(scale):
    """§4.8's acceptance test, exercised: change the policy, no migration, no code edit."""
    TurnoverBand.objects.filter(code="B3").update(initial_fee_cents=333_000)
    assert fee_cents_for(60_000_000, kind=AssessmentFee.Kind.INITIAL) == 333_000


def test_a_later_declaration_keeps_the_earlier_row(scale, member, farm):
    """A farm's fee history is a history: the renewal does not overwrite the initial."""
    today = timezone.localdate()
    declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL
    )
    declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000,
        kind=AssessmentFee.Kind.RENEWAL, declared_on=today,
    )
    assert AssessmentFee.objects.filter(member=member, farm=farm).count() == 2


def test_a_renewal_cannot_be_declared_where_a_significant_change_was_found(scale, member, farm):
    """OPP §2.3: renewal "only where no significant changes … have occurred".

    Not silently upgraded to the initial rate — the group's discretion is the group's,
    and a computation that overrides a declared field is an adjudication (A3's lesson).
    """
    with pytest.raises(SignificantChangeError):
        declare_assessment_fee(
            member, farm, declared_turnover_cents=20_000_000,
            kind=AssessmentFee.Kind.RENEWAL, is_significant_change=True,
        )


def test_the_schedule_fails_closed_when_it_is_not_seeded(db, member, farm):
    """An unseeded deployment must not charge R0 and call it a fee."""
    assert not TurnoverBand.objects.exists()
    with pytest.raises(FeeScheduleNotSeededError):
        declare_assessment_fee(
            member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL
        )


# --- The gate before a visit (D32, OPP §2.3) -----------------------------------


def test_unpaid_membership_is_refused_first(scale, member, farm):
    declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL
    )
    with pytest.raises(MembershipUnpaidError):
        assert_fees_paid_for_assessment(member, farm)


def test_the_gate_refuses_an_unpaid_assessment_fee(scale, member, farm):
    pay_membership(member)
    declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL
    )
    with pytest.raises(AssessmentFeeUnpaidError):
        assert_fees_paid_for_assessment(member, farm)


def test_a_membership_fee_alone_does_not_clear_the_gate(scale, member, farm):
    """The two gates are separate obligations, not one payment counted twice."""
    pay_membership(member)
    with pytest.raises(AssessmentFeeUnpaidError):
        assert_fees_paid_for_assessment(member, farm)


def test_the_gate_passes_when_both_are_paid(scale, member, farm):
    pay_membership(member)
    declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL,
        paid_on=timezone.localdate(), receipt_no="R-1",
    )
    assert_fees_paid_for_assessment(member, farm)  # raises if anything is missing


def test_the_gate_is_per_farm(scale, member, farm):
    """"Fees are per farm assessment visit" — a paid fee for one farm clears one farm."""
    other = Farm.objects.create(member=member, name="Rietvlei")
    pay_membership(member)
    declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL,
        paid_on=timezone.localdate(),
    )
    with pytest.raises(AssessmentFeeUnpaidError):
        assert_assessment_fee_paid(member, other)
    assert_assessment_fee_paid(member, farm)


def test_an_unpaid_declaration_does_not_clear_the_gate_beside_a_paid_one(scale, member, farm):
    """A stale unpaid row for this year does not cancel a paid one — but the gate reads
    the fee that is *paid*, and an unpaid renewal row beside it must not fail a visit
    that this year's fee already covers."""
    pay_membership(member)
    today = timezone.localdate()
    declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.INITIAL,
        paid_on=today,
    )
    declare_assessment_fee(
        member, farm, declared_turnover_cents=20_000_000, kind=AssessmentFee.Kind.RENEWAL,
        declared_on=today,
    )
    assert_fees_paid_for_assessment(member, farm)


# --- The seed -----------------------------------------------------------------


def test_the_seeded_scale_is_the_opps_six_bands(scale):
    bands = list(TurnoverBand.objects.order_by("display_order"))
    assert [b.code for b in bands] == ["B1", "B2", "B3", "B4", "B5", "B6"]
    assert [b.label for b in bands] == [
        "Below R 250,000",
        "R 250,001 – R 500,000",
        "R 500,001 – R 1,000,000",
        "R 1,000,001 – R 2,500,000",
        "R 2,500,001 – R 5,000,000",
        "Above R 5,000,000",
    ]
    assert [b.initial_fee_cents for b in bands] == [
        150_000, 250_000, 300_000, 370_000, 500_000, 800_000,
    ]
    assert [b.renewal_fee_cents for b in bands] == [
        90_000, 200_000, 250_000, 320_000, 500_000, 800_000,
    ]


def test_seeding_the_scale_twice_is_idempotent(scale):
    before = TurnoverBand.objects.count()
    call_command("seed_deployment")
    assert TurnoverBand.objects.count() == before


def test_the_seed_does_not_re_price_a_band_an_administrator_changed(scale):
    """`updated` in the seed's result counts *rows matched*, and the fields it may touch
    are amounts the group sets. An edited amount survives a deploy — the same rule as
    seals' `is_active`: a release does not overrule a human."""
    TurnoverBand.objects.filter(code="B2").update(initial_fee_cents=275_000)
    call_command("seed_deployment")
    assert TurnoverBand.objects.get(code="B2").initial_fee_cents == 275_000
