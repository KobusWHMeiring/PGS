"""Membership rules: the pledge, and the assessment fee gate.

The pledge half is about what a member attested; the fees half is about what must be
settled before the group spends a day on a farm. Both live here because both are
`_membership` concerns, and because `build_principles.md` §II puts the *rule* in the
service layer — where it is testable before the view that reaches it exists.

## The pledge

Two things are true of a pledge that are not true of a row:

- **It is evidentiary.** A verbal pledge or a distinctive mark is the OPP §I.2 path for
  members who cannot read and sign, and it is only worth anything if a witness and a
  record exist. The service refuses the combinations that would leave the group holding
  an attestation it cannot evidence, rather than storing them for someone to notice later.
- **It is not adjudicated.** The land-history periods in the pledge (12/12/18) and in
  OPP §V (18/12/12) disagree, and the platform's job is to record the declaration and
  mark the disagreement (D31). So `land_history_conflict` reports *"the answer depends
  on which document you read"* — the band between the two readings — and never *"the
  farmer is wrong"*. Below the lower reading both documents agree, and the visit decides.

The readings are data in the plain sense: a table of what two documents print, named as
they print it. Correcting OPP §V (it is the lone outlier) is a one-line change here plus
a deliberate change to the expectations in `test_pledge.py`; it is not a migration.

## The fees

OPP §2.3's notes state the four rules this module enforces, and each one is cited at the
function that applies it: fees are *per farm assessment visit*; they are *payable prior
to the visit*; *only fully paid-up members are eligible*; and *renewal fees apply only
where no significant changes have occurred*. The scale itself is **data** — a seeded
`TurnoverBand` table (§4.8, D12) — so `band_for()` reads policy and `declare_assessment_fee()`
snapshots it. Nothing here re-reads the current schedule for a fee already declared.

What those records **add up to** is A7's standing gate, `assert_eligible_for_assessment()`
in `_eligibility.py`: this module records the pledge and the money, that one decides whether
the member may be assessed on them. The slice is the 30 KB cap (`build_principles.md` §II),
and the seam is the domain's own.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from core.models import (
    AssessmentFee,
    Farm,
    Member,
    MembershipFee,
    Pledge,
    TurnoverBand,
    User,
)

# A7's family lives in `_eligibility` (sliced out when this module passed the 30 KB cap,
# `build_principles.md` §II). Both names are re-exported here so an existing
# `from core.services._membership import MembershipUnpaidError` keeps working, and so the
# fee gate below raises the *same* class the eligibility gate does — a second copy of it
# would make `except MembershipUnpaidError` miss the gate's refusal.
from core.services._eligibility import MembershipUnpaidError, NotEligibleError  # noqa: F401


class WitnessRequiredError(Exception):
    """A pledge made for a member who cannot sign, with nobody to attest to it.

    OPP §I.2: the pledge *"will be recorded by the PGS through photographic or other
    documented record"*, and the farmer pledge carries a witness block requiring name
    and designation. Not a `ValidationError` — this is an administrator recording a
    paper form, and an empty witness box is a form to go back and complete, not a field
    error on a public page.
    """


class PledgeDeclarationError(Exception):
    """The declarations do not match the pledge form that was signed.

    Three shapes: a consumer pledge carrying farmer-only declarations; a farmer pledge
    taking both branches or neither; an in-conversion period the form does not offer.
    All three are inventions about what a person signed, so all three fail loudly.
    """


# --- The two documents, as printed -------------------------------------------


@dataclass(frozen=True)
class ClearanceReading:
    """One document's printed clearance periods, in months.

    `source` is the citation a reviewer can check; the three numbers are what it says.
    """

    source: str
    annual: int
    pasture: int
    perennial: int


# D83: SAOSO 4.2.3 and the OPP farmer pledge print 12/12/18. OPP §V alone prints 18/12/12.
# OPP §V is the outlier, which is exactly why the flag cannot be "differs from OPP §V".
LAND_HISTORY_READINGS: tuple[ClearanceReading, ...] = (
    ClearanceReading("SAOSO 4.2.3 and the OPP farmer pledge", annual=12, pasture=12, perennial=18),
    ClearanceReading("OPP §V", annual=18, pasture=12, perennial=12),
)

# Which pledge field carries each crop group's declaration. The crop names are the
# form's own words: "annual production", "pastures and meadows", "other perennials".
CLEARANCE_FIELDS: dict[str, str] = {
    "annual": "declared_annual_clear_months",
    "pasture": "declared_pasture_clear_months",
    "perennial": "declared_perennial_clear_months",
}

IN_CONVERSION_PERIODS = (12, 18)


def conflict_band(crop: str) -> tuple[int, int] | None:
    """The months where the documents disagree for one crop group; None when they agree.

    In:  `crop` — a key of `CLEARANCE_FIELDS`.
    Out: `(low, high)` — the half-open band `low <= declared < high` — or None when every
         document prints the same number (pasture: both say 12).
    Fails: KeyError for a crop group no document names.
    """
    if crop not in CLEARANCE_FIELDS:
        raise KeyError(f"no clearance reading for crop group {crop!r}")
    readings = [getattr(reading, crop) for reading in LAND_HISTORY_READINGS]
    low, high = min(readings), max(readings)
    return None if low == high else (low, high)


def lands_in_conflict(crop: str, declared_months: int | None) -> bool:
    """True when this declaration falls inside the band where the documents disagree.

    In:  `crop` — a key of `CLEARANCE_FIELDS`.
         `declared_months` — the member's declared clear period; None means undeclared.
    Out: bool. False when the crop has no band, when nothing was declared, or when the
         period sits outside the band — including *below* it, where both documents
         agree and the answer is a compliance question for the visit (D31).
    Fails: KeyError for an unknown crop group.
    """
    band = conflict_band(crop)
    if band is None or declared_months is None:
        return False
    return band[0] <= declared_months < band[1]


# --- Recording ----------------------------------------------------------------


def _validate_witness(method: str, witness_name: str, witness_designation: str,
                      evidence_document: Any) -> None:
    """OPP §I.2 — a pledge made without a signature needs a witness and a record."""
    if method == Pledge.Method.VERBAL_WITNESSED:
        missing = [
            label
            for label, value in (
                ("the witness's name", witness_name),
                ("the witness's designation", witness_designation),
                ("an evidence document", evidence_document),
            )
            if not value
        ]
        if missing:
            raise WitnessRequiredError(
                "A verbal pledge must be witnessed and recorded (OPP §I.2): "
                + ", ".join(missing)
            )
    elif method == Pledge.Method.DISTINCTIVE_MARK:
        missing = [
            label
            for label, value in (
                ("the witness's name", witness_name),
                ("the witness's designation", witness_designation),
            )
            if not value
        ]
        if missing:
            raise WitnessRequiredError(
                "A distinctive mark must be witnessed (OPP §I.2): " + ", ".join(missing)
            )


def record_pledge(
    member: Member,
    *,
    kind: str,
    method: str = Pledge.Method.SIGNATURE,
    signed_on: date | None = None,
    place: str = "",
    declared_land_history_ok: bool | None = None,
    in_conversion_declared: bool = False,
    in_conversion_months: int | None = None,
    declared_annual_clear_months: int | None = None,
    declared_pasture_clear_months: int | None = None,
    declared_perennial_clear_months: int | None = None,
    recorded_by: User | None = None,
    witness_name: str = "",
    witness_designation: str = "",
    witness_signature: str = "",
    evidence_document: UploadedFile | None = None,
) -> Pledge:
    """Record one signed pledge and the declarations it carries.

    In:  `member` — whose pledge it is.
         `kind` — `Pledge.Kind.FARMER` or `CONSUMER`; the two OPP pledges are not variants.
         `method` — `SIGNATURE`, `DISTINCTIVE_MARK` or `VERBAL_WITNESSED` (OPP §I.2).
         `signed_on` — the date on the form; defaults to today in the local timezone.
         `place` — the place on the form; optional in the record, printed on the paper.
         `declared_land_history_ok` — True for the land-history branch. `None` infers it
         from the declared periods, and stating it False while declaring periods is a
         contradiction and fails.
         `in_conversion_declared` / `in_conversion_months` — the other branch, 12 or 18.
         `declared_*_clear_months` — months clear of prohibited inputs, per crop group.
         `recorded_by` — the administrator who captured it (OPP §I.2).
         `witness_*` — the farmer pledge's witness block.
         `evidence_document` — the photograph or other record (§I.2).
    Out: the saved `Pledge`. `land_history_conflict` is computed here: True inside the
         band where the two documents disagree, False outside it, None when the row takes
         the in-conversion branch or is a consumer pledge.
    Side Effects: one INSERT; writes `evidence_document` under `PRIVATE_MEDIA_ROOT`.
    Fails: `WitnessRequiredError` when a verbal or marked pledge has no witness/evidence.
           `PledgeDeclarationError` when the declarations cannot belong to the form
           signed — both branches, neither branch, an in-conversion period the form does
           not offer, or farmer declarations on a consumer pledge.
           `ValueError` for a `kind` or `method` outside the choices.
    """
    kind = Pledge.Kind(kind)
    method = Pledge.Method(method)

    declared_months = {
        crop: months
        for crop, months in (
            ("annual", declared_annual_clear_months),
            ("pasture", declared_pasture_clear_months),
            ("perennial", declared_perennial_clear_months),
        )
    }
    anything_declared = any(months is not None for months in declared_months.values())

    if kind is Pledge.Kind.CONSUMER:
        # The consumer pledge attests to support for IFOAM's principles and nothing else;
        # it has no land, no in-conversion box and no witness block. Blanking these would
        # store a claim the member never made, so they are refused.
        if anything_declared or in_conversion_declared:
            raise PledgeDeclarationError(
                "The consumer pledge carries no land-history or in-conversion declaration."
            )
        if witness_name or witness_designation or witness_signature or evidence_document:
            raise PledgeDeclarationError(
                "The consumer pledge has no witness block; only the farmer pledge does."
            )
        land_history_conflict = None
        declared_land_history_ok = False
    else:
        _validate_witness(method, witness_name, witness_designation, evidence_document)

        if in_conversion_declared and anything_declared:
            raise PledgeDeclarationError(
                "The farmer pledge is a land history OR an in-conversion declaration, "
                "not both."
            )
        if in_conversion_declared and in_conversion_months not in IN_CONVERSION_PERIODS:
            raise PledgeDeclarationError(
                "In-conversion is recorded for the 12 or the 18 months the form offers; "
                f"got {in_conversion_months!r}."
            )
        if in_conversion_declared:
            land_history_conflict = None
            declared_land_history_ok = False
        else:
            if not anything_declared:
                raise PledgeDeclarationError(
                    "A farmer pledge declares either the land history or in-conversion; "
                    "neither was given."
                )
            if declared_land_history_ok is False:
                raise PledgeDeclarationError(
                    "declared_land_history_ok=False contradicts the declared clear periods."
                )
            declared_land_history_ok = True
            land_history_conflict = any(
                lands_in_conflict(crop, months) for crop, months in declared_months.items()
            )

    with transaction.atomic():
        return Pledge.objects.create(
            member=member,
            kind=kind,
            method=method,
            signed_on=signed_on or timezone.localdate(),
            place=place,
            declared_land_history_ok=declared_land_history_ok,
            in_conversion_declared=in_conversion_declared,
            in_conversion_months=in_conversion_months,
            declared_annual_clear_months=declared_annual_clear_months,
            declared_pasture_clear_months=declared_pasture_clear_months,
            declared_perennial_clear_months=declared_perennial_clear_months,
            land_history_conflict=land_history_conflict,
            recorded_by=recorded_by,
            witness_name=witness_name,
            witness_designation=witness_designation,
            witness_signature=witness_signature,
            evidence_document=evidence_document or "",
        )


# --- The assessment fee gate (OPP §2.3, D32) ----------------------------------
#
# `MembershipUnpaidError` — the refusal this gate raises first — is defined in
# `_eligibility.py` with the rest of A7's family and imported above. Two modules needed
# it, and one class with two definitions would make `except MembershipUnpaidError` miss
# whichever copy it did not name.


class FeeScheduleNotSeededError(Exception):
    """No turnover bands, or a scale with a hole. A fee must never be invented.

    Fail closed, like `ingest_standard` refusing to guess a `StandardSet`: an unseeded
    deployment that returned R0 would invoice a farmer nothing and record it as paid-in-full.
    """


class AssessmentFeeUnpaidError(Exception):
    """OPP §2.3: *"Fees are payable prior to the farm assessment visit."*

    Named for the fee, but the guard reads the row rather than a due date: `paid_on` is
    the evidence, and a fee past its `due_on` with no receipt is not paid (D32).
    """


class SignificantChangeError(Exception):
    """OPP §2.3: renewal applies *"only where no significant changes … have occurred"*.

    A significant change is an **initial** assessment at the initial rate. The group *may*
    require one — it is their discretion — so the service refuses the contradictory pair
    rather than applying the higher rate itself, which would be an adjudication.
    """


def band_for(declared_turnover_cents: int) -> TurnoverBand:
    """The band the OPP's sliding scale puts this declared turnover in.

    In:  `declared_turnover_cents` — turnover as the member declared it (D29: declared,
         never inferred). Cents, per §III's integer-money rule.
    Out: the `TurnoverBand` row.
    Side Effects: one query.
    Fails: `ValueError` for a negative turnover; `FeeScheduleNotSeededError` when the
         scale is empty, when it does not start at zero, or when no band covers the
         figure (a hole in the seeded data is a deployment fault, not a fee of zero).
    """
    if declared_turnover_cents < 0:
        raise ValueError(f"declared turnover cannot be negative: {declared_turnover_cents}")
    bands = list(TurnoverBand.objects.order_by("min_turnover_cents"))
    if not bands:
        raise FeeScheduleNotSeededError(
            "no turnover bands are seeded — run `manage.py seed_deployment` (OPP §2.3)"
        )
    for band in bands:
        if band.covers(declared_turnover_cents):
            return band
    raise FeeScheduleNotSeededError(
        f"no turnover band covers {declared_turnover_cents} cents; the scale ends at "
        f"{bands[-1].code} (max {bands[-1].max_turnover_cents}) and must be open-ended "
        "on its top band"
    )


def fee_cents_for(declared_turnover_cents: int, *, kind: str) -> int:
    """The printed fee for that turnover and that kind of assessment.

    In:  `declared_turnover_cents` — as `band_for`.
         `kind` — `AssessmentFee.Kind.INITIAL` or `RENEWAL`.
    Out: integer cents, read from the band row — never computed from a percentage.
    Side Effects: one query.
    Fails: as `band_for`; `ValueError` for an unknown kind.
    """
    band = band_for(declared_turnover_cents)
    if AssessmentFee.Kind(kind) is AssessmentFee.Kind.INITIAL:
        return band.initial_fee_cents
    return band.renewal_fee_cents


def declare_assessment_fee(
    member: Member,
    farm: Farm,
    *,
    declared_turnover_cents: int,
    kind: str = AssessmentFee.Kind.INITIAL,
    declared_on: date | None = None,
    due_on: date | None = None,
    paid_on: date | None = None,
    receipt_no: str = "",
    is_significant_change: bool = False,
) -> AssessmentFee:
    """Record the fee a member was asked for, for one farm.

    In:  `member` — who owes it. `farm` — which farm it is for (OPP §2.3: *per farm*).
         `declared_turnover_cents` — self-declared, subject to peer review (D29).
         `kind` — INITIAL or RENEWAL.
         `declared_on` / `due_on` / `paid_on` / `receipt_no` — the paper trail; `due_on`
         is set when the visit is scheduled, and `paid_on` is the only evidence of payment.
         `is_significant_change` — OPP §2.3's renewal condition.
    Out: the saved `AssessmentFee`, with the band code, its printed label and the amount
         **snapshotted** from the schedule as it stands now.
    Side Effects: one INSERT. Does not touch the schedule.
    Fails: `SignificantChangeError` for a renewal declared alongside a significant change;
         `FeeScheduleNotSeededError` when the scale is missing or has a hole; `ValueError`
         for a negative turnover or an unknown kind.
    """
    kind = AssessmentFee.Kind(kind)
    if is_significant_change and kind is AssessmentFee.Kind.RENEWAL:
        raise SignificantChangeError(
            "OPP §2.3: renewal fees apply only where no significant changes have occurred. "
            "A significant change is declared as an INITIAL fee at the initial rate."
        )
    if declared_turnover_cents < 0:
        raise ValueError(f"declared turnover cannot be negative: {declared_turnover_cents}")

    band = band_for(declared_turnover_cents)
    amount_cents = (
        band.initial_fee_cents
        if kind is AssessmentFee.Kind.INITIAL
        else band.renewal_fee_cents
    )

    with transaction.atomic():
        return AssessmentFee.objects.create(
            member=member,
            farm=farm,
            kind=kind,
            turnover_band=band.code,
            band_label=band.label,
            declared_turnover_cents=declared_turnover_cents,
            amount_cents=amount_cents,
            declared_on=declared_on or timezone.localdate(),
            due_on=due_on,
            paid_on=paid_on,
            receipt_no=receipt_no,
            is_significant_change=is_significant_change,
        )


def assert_assessment_fee_paid(member: Member, farm: Farm) -> None:
    """Every path that costs the group a visit day calls this first (D32).

    In:  `member`, `farm` — the pair the fee is owed on.
    Out: None. Returns quietly when a paid fee exists for that farm.
    Side Effects: one query.
    Fails: `AssessmentFeeUnpaidError` when the farm has no fee row, or none with a
         `paid_on`. An unpaid declaration is named as such, because "declared but not
         paid" and "never declared" are different conversations with the member.
    """
    paid = AssessmentFee.objects.filter(member=member, farm=farm, paid_on__isnull=False)
    if paid.exists():
        return
    declared = AssessmentFee.objects.filter(member=member, farm=farm).count()
    if declared:
        raise AssessmentFeeUnpaidError(
            f"{declared} assessment fee(s) declared for this farm, none recorded as paid "
            "(OPP §2.3: fees are payable prior to the visit)"
        )
    raise AssessmentFeeUnpaidError(
        "no assessment fee has been declared for this farm "
        "(OPP §2.3: fees are payable prior to the visit)"
    )


def assert_fees_paid_for_assessment(member: Member, farm: Farm) -> None:
    """The single entry point for "may this visit go ahead?" — D32.

    In:  `member`, `farm`.
    Out: None.
    Side Effects: two queries.
    Fails: `MembershipUnpaidError` first, then `AssessmentFeeUnpaidError`. The order is
         deliberate: an unpaid membership is the more fundamental failure, and telling a
         member they owe an assessment fee while their membership has lapsed is the wrong
         conversation.
    """
    if not member.is_paid_up:
        raise MembershipUnpaidError(
            "OPP §2.3: only fully paid-up members are eligible for farm assessments"
        )
    assert_assessment_fee_paid(member, farm)


# --- The membership subscription: the group's part of the application ---------
#
# A6's applicant flow ends at the declaration (turnover). The subscription is not the
# farmer's act: the group invoices it, records it, and confirms payment. These two
# services are built here — with the rules that matter — but **no view calls them yet**,
# the same way A5 left `assert_fees_paid_for_assessment()` waiting for C1's
# `confirm_visit()`. The recording surface belongs with the committee's work in A7 and
# the visit in C1, and inventing one now would put a `paid_on` in a farmer's hands.


def record_membership_fee(
    member: Member,
    *,
    period_start: date,
    period_end: date,
    amount_cents: int,
    kind: str = "ANNUAL",
    paid_on: date | None = None,
    receipt_no: str = "",
) -> MembershipFee:
    """Record what a member was invoiced, for the period the group invoiced it for.

    In:  `member` — who owes it. `period_start` / `period_end` — **the group's fee year,
         passed in, never inferred**: D39 says "payable by the end of February" is group
         policy and lives on the row, and the OPP does not state a fee year at all. A
         service that computed one would invent policy the group has not made.
         `amount_cents` — the AGM figure, integer cents (§III). `paid_on` is the only
         evidence of payment; `receipt_no` is the paper trail.
    Out: the saved `MembershipFee`.
    Side Effects: one INSERT. Does not change `Member.status` — paying does that
         (`record_membership_payment`), so that an invoice and a payment stay distinct.
    Fails: `ValueError` for a period that ends before it starts, or a negative amount.
    """
    if period_end < period_start:
        raise ValueError(
            f"a fee period cannot end before it starts: {period_start}..{period_end}"
        )
    if amount_cents < 0:
        raise ValueError(f"a membership fee cannot be negative: {amount_cents}")
    with transaction.atomic():
        return MembershipFee.objects.create(
            member=member,
            kind=kind,
            period_start=period_start,
            period_end=period_end,
            amount_cents=amount_cents,
            paid_on=paid_on,
            receipt_no=receipt_no,
        )


def record_membership_payment(
    fee: MembershipFee, *, paid_on: date | None = None, receipt_no: str = ""
) -> MembershipFee:
    """Record that a membership fee was paid, and activate an applicant.

    In:  `fee` — the row the group invoiced. `paid_on` — the date on the receipt;
         defaults to today in the local timezone. `receipt_no` — optional.
    Out: the updated `MembershipFee`.
    Side Effects: UPDATEs the fee, and moves `APPLICANT → ACTIVE` (spec §7.7: *"on
         payment, Member.status → ACTIVE and is_paid_up → True"*).
    Fails: never deliberately.

    **One transition, one direction.** A receipt does not reinstate a `TERMINATED` or
    `LAPSED` member: OPP §4.7 makes reinstatement a committee decision after a calendar
    year, and a payment record that undid it would silently restore a member the group
    removed.
    """
    with transaction.atomic():
        fee.paid_on = paid_on or timezone.localdate()
        if receipt_no:
            fee.receipt_no = receipt_no
        fee.save(update_fields=["paid_on", "receipt_no"])
        member = fee.member
        if member.status == Member.Status.APPLICANT:
            member.status = Member.Status.ACTIVE
            member.save(update_fields=["status"])
    return fee
