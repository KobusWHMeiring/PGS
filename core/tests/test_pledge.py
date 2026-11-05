"""Task A3 — the pledge (OPP §I.1–I.2, spec §4.1, Decision D31 and D83).

The OPP carries **two** pledges on facing pages, and they are not variants of one
another: the farmer pledge attests to land, the consumer pledge attests to support
for IFOAM's principles and nothing else. So `kind` is a required field, and the
farmer-only declarations are refused on a consumer row rather than silently blanked
— the form says so, and a row that says otherwise misrepresents what a person signed.

Three decisions this file pins, each with the reason it is pinned:

- **The conflict band is a band, not a comparison** (D83). SAOSO 4.2.3 and the OPP
  pledge both print 12/12/18; **OPP §V alone prints 18/12/12**. So
  `land_history_conflict` is `min_reading <= declared < max_reading` — the period
  where a farmer's honest answer depends on which document they were shown. It is
  **not** "differs from OPP §V": written that way, the rule would report every
  farmer who signed the pledge as printed as being in conflict, which is the
  *answer*, not a fault. Pasture has no band because both documents agree at 12.
- **The flag is stored, where `Member.is_paid_up` is derived** (D39). A fee period
  rolls over, so a stored paid-up boolean would go stale; a declaration does not
  change once signed, and the flag is needed as a record of what the two documents
  said *on the day it was signed* (build_principles §I, Immutable History). The
  parametrised test below states the bands as literal numbers so that a future edit
  to either the table or the writer has to change the expectation deliberately.
- **Nothing is adjudicated** (D31). The service records what was declared and flags
  the ambiguity; it never resolves it, and `resolved_in_conversion_months` does not
  exist so that "we decided for the farmer" is not representable.

A verbal pledge is the OPP §I.2 path for members who cannot read and sign, and it is
not a convenience: the pledge must be *"recorded by the PGS through photographic or
other documented record"* with a witness's name and designation. The service refuses
it without them, because a verbal pledge with no record is an attestation nobody can
evidence.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from core.models import Member, Pledge
from core.services._membership import (
    PledgeDeclarationError,
    WitnessRequiredError,
    record_pledge,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _private_media(settings, tmp_path):
    """Evidence lands under PRIVATE_MEDIA_ROOT (§VI) — never in the repo's media dir."""
    settings.PRIVATE_MEDIA_ROOT = tmp_path / "private_media"
    return settings.PRIVATE_MEDIA_ROOT


@pytest.fixture
def doc():
    return SimpleUploadedFile("pledge-scan.jpg", b"a photographed verbal pledge")


# --- The plan's named tests ---------------------------------------------------


def test_verbal_pledge_requires_witness_and_evidence(member):
    with pytest.raises(WitnessRequiredError):
        record_pledge(member, kind="FARMER", method="VERBAL_WITNESSED")


def test_distinctive_mark_is_a_valid_pledge_method(member, doc):
    # OPP §I.2 — the pledge is signed with a "Signature(s)/distinctive marks" line,
    # so a member who cannot sign is a member who can still pledge.
    p = record_pledge(
        member,
        kind="FARMER",
        method="DISTINCTIVE_MARK",
        witness_name="S. Mentz",
        witness_designation="Administrator",
        evidence_document=doc,
        declared_annual_clear_months=24,
    )
    assert p.method == "DISTINCTIVE_MARK"


def test_land_history_conflict_is_the_band_where_the_documents_disagree(member):
    # D31 + D83. SAOSO 4.2.3 and the pledge say 12/12/18; OPP §V says 18/12/12.
    # The flag is NOT "differs from OPP §V" -- at 12 months for annuals the answer
    # genuinely depends on which document you read, and a farmer who signed the
    # pledge as printed is in that band. Flag the ambiguity, not the farmer.
    p = record_pledge(
        member, kind="FARMER", method="SIGNATURE", declared_annual_clear_months=12
    )
    assert p.land_history_conflict is True  # 12 is inside [12, 18)
    assert not hasattr(p, "resolved_in_conversion_months")  # D31: record, never adjudicate


def test_a_declaration_past_both_readings_is_not_a_conflict(member):
    p = record_pledge(
        member, kind="FARMER", method="SIGNATURE", declared_annual_clear_months=24
    )
    assert p.land_history_conflict is False


def test_pasture_has_no_conflict_band_because_both_documents_agree(member):
    # Both say 12 for pasture and meadows, so no declaration can be ambiguous.
    p = record_pledge(
        member, kind="FARMER", method="SIGNATURE", declared_pasture_clear_months=12
    )
    assert p.land_history_conflict is False


# --- The band, stated as the documents state it -------------------------------

BANDS = [
    # (field, declared months, expected) -- the numbers, not a reference to the code.
    ("declared_annual_clear_months", 11, False),  # short of both: a visit's business, not a band
    ("declared_annual_clear_months", 12, True),  # the pledge's number
    ("declared_annual_clear_months", 17, True),
    ("declared_annual_clear_months", 18, False),  # OPP §V's number is outside the band
    ("declared_annual_clear_months", 24, False),
    ("declared_perennial_clear_months", 12, True),  # OPP §V is the low reading here
    ("declared_perennial_clear_months", 17, True),
    ("declared_perennial_clear_months", 18, False),  # the pledge's number
    ("declared_pasture_clear_months", 12, False),  # both documents agree
    ("declared_pasture_clear_months", 18, False),
]


@pytest.mark.parametrize(("field", "declared", "expected"), BANDS)
def test_the_band_is_where_the_two_documents_disagree(member, field, declared, expected):
    p = record_pledge(
        member, kind="FARMER", method="SIGNATURE", **{field: declared}
    )
    assert p.land_history_conflict is expected


def test_a_period_below_both_readings_is_not_a_documentary_conflict(member):
    """11 months fails both documents, and that is *not* what this flag reports.

    The flag answers one question — which document do you read? — and below the
    lower reading both documents give the same answer, so there is no ambiguity to
    report. Widening the band to "anything under the maximum" would turn a record of
    a documentary disagreement into a verdict on the farmer (D31), and the verdict
    belongs to the visit.
    """
    p = record_pledge(
        member, kind="FARMER", method="SIGNATURE", declared_annual_clear_months=11
    )
    assert p.land_history_conflict is False


# --- Land history, or in-conversion, never both and never neither -------------


def test_in_conversion_records_the_selected_period_and_flags_nothing(member):
    p = record_pledge(
        member, kind="FARMER", method="SIGNATURE", in_conversion_declared=True,
        in_conversion_months=18,
    )
    assert p.in_conversion_declared is True
    assert p.in_conversion_months == 18
    assert p.land_history_conflict is None, "no land-history declaration, nothing to judge"


def test_a_farmer_pledge_cannot_declare_both_branches(member):
    """The form is an OR: "… for at least 12 months … OR I/We have applied for In-Conversion"."""
    with pytest.raises(PledgeDeclarationError):
        record_pledge(
            member, kind="FARMER", method="SIGNATURE", in_conversion_declared=True,
            in_conversion_months=12, declared_annual_clear_months=12,
        )


def test_a_farmer_pledge_must_take_one_of_the_two_branches(member):
    with pytest.raises(PledgeDeclarationError):
        record_pledge(member, kind="FARMER", method="SIGNATURE")


def test_in_conversion_months_are_the_two_the_form_offers(member):
    with pytest.raises(PledgeDeclarationError):
        record_pledge(
            member, kind="FARMER", method="SIGNATURE", in_conversion_declared=True,
            in_conversion_months=24,
        )


# --- The consumer pledge is not the farmer pledge ------------------------------


def test_a_consumer_pledge_needs_nothing_but_the_member(member):
    p = record_pledge(member, kind="CONSUMER")
    assert p.kind == "CONSUMER"
    assert p.method == "SIGNATURE"
    assert p.land_history_conflict is None
    assert p.witness_name == ""


def test_a_consumer_pledge_cannot_carry_a_land_history(member):
    with pytest.raises(PledgeDeclarationError):
        record_pledge(
            member, kind="CONSUMER", declared_annual_clear_months=12
        )


def test_a_consumer_pledge_cannot_carry_a_witness(member):
    """The consumer pledge has no witness block; a row that has one describes a signing
    that the form never offered."""
    with pytest.raises(PledgeDeclarationError):
        record_pledge(member, kind="CONSUMER", witness_name="S. Mentz")


# --- The database is a backstop, and it can fail ------------------------------


def test_the_database_refuses_a_consumer_row_carrying_a_declaration(member):
    """Proves the constraint is real: the service is not the only writer forever."""
    with pytest.raises(IntegrityError), transaction.atomic():
        Pledge.objects.create(
            member=member, kind="CONSUMER",
            declared_annual_clear_months=12, land_history_conflict=True,
        )


def test_the_database_refuses_a_farmer_row_that_takes_neither_branch(member):
    with pytest.raises(IntegrityError), transaction.atomic():
        Pledge.objects.create(member=member, kind="FARMER")


def test_the_database_refuses_in_conversion_without_its_period(member):
    with pytest.raises(IntegrityError), transaction.atomic():
        Pledge.objects.create(
            member=member, kind="FARMER", in_conversion_declared=True,
            in_conversion_months=None,
        )


def test_the_database_refuses_in_conversion_months_the_form_does_not_offer(member):
    with pytest.raises(IntegrityError), transaction.atomic():
        Pledge.objects.create(
            member=member, kind="FARMER", in_conversion_declared=True,
            in_conversion_months=24,
        )


# --- The record, not the adjudication -----------------------------------------


def test_the_pledge_records_who_recorded_it_and_when_it_was_signed(member, user):
    p = record_pledge(
        member, kind="FARMER", method="SIGNATURE", declared_annual_clear_months=24,
        place="Riversdale", recorded_by=user,
    )
    assert p.recorded_by == user
    assert p.signed_on == timezone.localdate()  # §1.35: never a hardcoded date
    assert p.place == "Riversdale"


def test_a_recorded_pledge_cannot_be_deleted_by_deleting_its_member(member):
    """Evidentiary: what a member attested outlives the membership row (§I)."""
    record_pledge(member, kind="FARMER", method="SIGNATURE", declared_annual_clear_months=24)
    with pytest.raises(ProtectedError):
        Member.objects.get(pk=member.pk).delete()


def test_the_evidence_document_is_uploaded_under_the_private_root(member, doc, _private_media):
    p = record_pledge(
        member, kind="FARMER", method="VERBAL_WITNESSED",
        witness_name="S. Mentz", witness_designation="Administrator",
        evidence_document=doc, declared_annual_clear_months=24,
    )
    assert p.evidence_document.name.startswith("pledge_evidence/")
    assert (_private_media / p.evidence_document.name).exists(), (
        "evidence is personal data: it must land in PRIVATE_MEDIA_ROOT, not media/"
    )
