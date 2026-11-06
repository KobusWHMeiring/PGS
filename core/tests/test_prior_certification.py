"""Task A4 — prior certification history (spec §4.1 line 207, FORM Sheet A, D30).

Sheet A of the printed FORM asks about prior PGS certification, prior third-party
certification, and — in D30's own words — *prior **denial** of certification with
reasons*, because "a denial is materially relevant to a certification decision". OPP §4.5
also makes misuse of a third-party logo serious misconduct, which is the reason the
certifier's name has to be on the row rather than in free prose.

Four decisions this file pins, each with the reason it is pinned:

- **The denial rule is a `CheckConstraint` *and* a `save()` guard.** `objects.create()`
  calls `save()` but never `full_clean()`, so a rule written only in `clean()` is green
  in a form and absent from every test — the shape A7 lost an hour to. The constraint is
  the backstop for any writer that bypasses `save()` (the tests prove it with
  `bulk_create`); the guard is what a caller actually sees.
- **`denial_reason` is `NOT NULL`, `default=""`, and the check reads `~Q(denial_reason="")`.**
  `NULL IN (…)` is satisfied by Postgres (§1.37), so a nullable column here would make the
  constraint constrain nothing at the exact row it exists to refuse.
- **A `DENIED` row carries no expiry.** A denied application never produced a certificate,
  so an `expires_on` on it describes an instrument that does not exist — D38's "a field
  that can be entered but means nothing" trap. On a `GRANTED` row it is optional, because
  "we do not know when it lapsed" is a real answer and a required date would be invented.
- **The row holds exactly the fields §4.1 lists.** No `declared_on`, no source document,
  no "verified" flag: the form asks none of those, and a field nobody captured would
  record a provenance the group never had.

Nothing in this slice writes the table. C2's questionnaire renders Sheet A, and the visit
and its report read the rows.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import PriorCertification

pytestmark = pytest.mark.django_db

PGS = PriorCertification.Kind.PGS
THIRD_PARTY = PriorCertification.Kind.THIRD_PARTY
GRANTED = PriorCertification.Outcome.GRANTED
DENIED = PriorCertification.Outcome.DENIED


def _row(farm, **overrides):
    """An unsaved row that is valid unless a test says otherwise."""
    values = {
        "farm": farm,
        "kind": PGS,
        "body_name": "Southern Cape PGS",
        "outcome": GRANTED,
    }
    values.update(overrides)
    return PriorCertification(**values)


# --- A denial names its reason ------------------------------------------------


def test_a_denial_without_a_reason_raises_on_save(farm):
    """D30: a denial is materially relevant, so "denied, for no stated reason" is not a row."""
    with pytest.raises(ValidationError):
        _row(farm, outcome=DENIED).save()


def test_a_denial_with_a_reason_saves_and_stores_it_verbatim(farm):
    """The reason is evidence: the group's words, not a normalised version of them."""
    reason = (
        "  Contamination risk on the northern block — see the 2024 inspection.\n"
        "Re-apply once the 12-month land history is clear.  "
    )
    row = _row(farm, outcome=DENIED, denial_reason=reason)
    row.save()

    row.refresh_from_db()
    assert row.denial_reason == reason


def test_the_database_refuses_a_denial_without_a_reason(farm):
    """Proves the constraint is real: `bulk_create` skips `save()`, so only the database is left.

    The reason is **omitted**, not passed as `""` — that is how a caller with nothing to
    say writes the row, and it is what makes `denial_reason`'s `NOT NULL, default=""`
    load-bearing: on a nullable column this insert stores `NULL`, the check reads `NULL`,
    and Postgres satisfies it (§1.37).
    """
    with pytest.raises(IntegrityError), transaction.atomic():
        PriorCertification.objects.bulk_create([_row(farm, outcome=DENIED)])


# --- The certifying body is named, whichever kind it is -----------------------


@pytest.mark.parametrize("kind", [PGS, THIRD_PARTY])
def test_body_name_is_required_for_both_kinds(farm, kind):
    with pytest.raises(ValidationError):
        _row(farm, kind=kind, body_name="").save()


@pytest.mark.parametrize("kind", [PGS, THIRD_PARTY])
def test_the_database_refuses_an_unnamed_body(farm, kind):
    with pytest.raises(IntegrityError), transaction.atomic():
        PriorCertification.objects.bulk_create([_row(farm, kind=kind, body_name="")])


# --- A denial has no expiry ---------------------------------------------------


def test_a_denial_carrying_an_expiry_is_refused(farm):
    """A denial issued no certificate, so there is nothing that could expire."""
    with pytest.raises(ValidationError):
        _row(
            farm,
            outcome=DENIED,
            denial_reason="Land history not met.",
            expires_on=timezone.localdate() + timedelta(days=365),
        ).save()


def test_the_database_refuses_a_denial_carrying_an_expiry(farm):
    with pytest.raises(IntegrityError), transaction.atomic():
        PriorCertification.objects.bulk_create(
            [
                _row(
                    farm,
                    outcome=DENIED,
                    denial_reason="Land history not met.",
                    expires_on=timezone.localdate(),
                )
            ]
        )


# --- One farm, several histories ----------------------------------------------


def test_a_farm_holds_several_prior_certifications(farm):
    """The real Sheet A answer: a prior PGS group, a third-party certifier, and a denial."""
    today = timezone.localdate()

    _row(
        farm,
        kind=PGS,
        body_name="Southern Cape PGS",
        certificate_ref="SCPGS-2019-014",
        outcome=GRANTED,
        expires_on=today + timedelta(days=365),
    ).save()
    _row(
        farm,
        kind=THIRD_PARTY,
        body_name="Ecocert SA",
        certificate_ref="ECO-2021-2231",
        outcome=GRANTED,
        # No expiry: "we do not know when it lapsed" is a real answer.
    ).save()
    _row(
        farm, kind=PGS, body_name="Overberg PGS", outcome=DENIED, denial_reason="Prohibited inputs."
    ).save()

    assert farm.prior_certifications.count() == 3
    assert set(farm.prior_certifications.values_list("outcome", flat=True)) == {GRANTED, DENIED}


# --- Nothing invented ---------------------------------------------------------


def test_the_row_holds_exactly_the_fields_the_spec_lists():
    """§4.1 line 207, and no declared_on / source / verified flag beside it."""
    assert {field.name for field in PriorCertification._meta.fields} == {
        "id",
        "farm",
        "kind",
        "body_name",
        "certificate_ref",
        "outcome",
        "expires_on",
        "denial_reason",
    }
