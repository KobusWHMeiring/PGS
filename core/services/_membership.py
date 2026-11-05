"""The pledge: recording what a member attested, and flagging where the documents disagree.

`build_principles.md` §II puts the rule in the service, and here that is load- bearing
rather than stylistic. Two things are true of a pledge that are not true of a row:

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
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from core.models import Member, Pledge, User


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
