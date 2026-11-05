"""The money: membership subscriptions and the OPP §2.3 assessment fee scale.

Cut out of `_membership.py` when that slice passed the 30 KB cap (§II), and the seam is
the OPP's own: §II is *"Membership fees, farm assessment fees, licensing fees"* — a
different half of the document from §I, which is the pledge and the application.

Nothing here is a computed price. `TurnoverBand` is data (§4.8, D12) seeded by
`seed_deployment`, and every fee row **snapshots** the band code, its printed label and
the amount it was declared under, because the schedule is policy that changes at an AGM
while a fee row is what a member was asked to pay. Integer cents only, `_cents` suffix,
never a float (§III).
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from core.models._membership import Farm, Member


class MembershipFee(models.Model):
    """A membership subscription payment for one explicit period.

    The period lives on the **row**, never in the calendar (D39): "payable by the
    end of February" is group policy, so a February deadline is data. `paid_on` is
    nullable because a fee can be recorded before it is settled — `Member.is_paid_up`
    requires a date.

    `kind` is a plain `CharField` with no `choices=`: fee kinds are group data, and
    sub-plan A5 decides the vocabulary. Inventing an enum here would put a
    deployment's fee names into code.
    """

    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="fees")
    kind = models.CharField(max_length=32, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    amount_cents = models.IntegerField()  # §III: integer cents, never a float
    paid_on = models.DateField(null=True, blank=True)
    receipt_no = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["member_id", "period_start"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.period_start}..{self.period_end}"

class TurnoverBand(models.Model):
    """One row of the OPP §2.3 sliding scale — **data**, seeded per deployment.

    OPP §2.3: *"The farm assessment visit fee is set based on a sliding scale … This fee
    applies to all commercial farms entering or renewing PGS certification."* The scale is
    the group's approved policy (it is tabled and approved at the AGM), so §4.8's rule
    applies without ambiguity: *fee bands are per-deployment seed and settings — content,
    not logic*. Changing them is a row edit, and a retarget of the blueprint to another
    group needs no migration.

    **Half-open bounds, and the reason is the printed table.** The OPP reads *"Below R
    250,000"* then *"R 250,001 – R 500,000"*, leaving R250,000.50 in neither band. Storing
    `min_turnover_cents` inclusive and `max_turnover_cents` exclusive closes that hole with
    one rule instead of two, and keeps the printed wording in `label` for display.

    A band is never deleted by a re-seed and never re-priced: `initial_fee_cents` and
    `renewal_fee_cents` are set on create only, because a release must not change what a
    farmer was already invoiced.
    """

    code = models.CharField(max_length=8, unique=True)
    label = models.CharField(max_length=64, help_text="As the OPP prints it.")
    min_turnover_cents = models.BigIntegerField(help_text="Inclusive; the scale starts at 0.")
    max_turnover_cents = models.BigIntegerField(
        null=True, blank=True, help_text="Exclusive. Null on the open-ended top band."
    )
    initial_fee_cents = models.IntegerField()
    renewal_fee_cents = models.IntegerField()
    display_order = models.PositiveSmallIntegerField()
    standard_ref = models.CharField(max_length=64, default="OPP §2.3")

    class Meta:
        ordering = ["display_order"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(min_turnover_cents__gte=0),
                name="turnover_band_starts_at_or_above_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(max_turnover_cents__isnull=True)
                | models.Q(max_turnover_cents__gt=models.F("min_turnover_cents")),
                name="turnover_band_is_not_empty",
            ),
            models.UniqueConstraint(
                fields=["min_turnover_cents"], name="uniq_turnover_band_floor"
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.code}: {self.label}"

    def covers(self, declared_turnover_cents: int) -> bool:
        """True when this band holds that turnover. `min` inclusive, `max` exclusive.

        In:  `declared_turnover_cents` — the turnover the member declared.
        Out: bool.
        Side Effects: none; no query.
        """
        if declared_turnover_cents < self.min_turnover_cents:
            return False
        return self.max_turnover_cents is None or declared_turnover_cents < self.max_turnover_cents

class AssessmentFee(models.Model):
    """The assessment fee a member was asked to pay, for one farm.

    **Per farm, not per member.** OPP §2.3: *"Fees are per farm assessment visit."* A
    member with three farms owes three fees, which is why `farm` is required here and why
    spec §4.1's original line (member + visit only) could not carry the rule. The visit FK
    arrives with `FarmVisit` (task C1): the fee is declared *before* a visit exists, so the
    farm is the anchor and the visit is the later, optional link. A nullable FK added by a
    later migration is cheap; inventing a stub visit model now would be a model no task
    owns.

    **The row snapshots the band.** `turnover_band`, `band_label` and `amount_cents` are
    copied at declaration time rather than read through an FK: the schedule is policy and
    changes at an AGM, while this row is what somebody was asked to pay. A fee that re-read
    the current schedule would silently re-price last year's invoice (§I, Immutable
    History).

    `declared_turnover_cents` is stored because the fee is **declared, not computed** (D29):
    turnover is self-declared by the farmer and subject to peer review, so the number a human
    gave is evidence, not an input to be re-derived.
    """

    class Kind(models.TextChoices):
        INITIAL = "INITIAL", "Initial certification"
        RENEWAL = "RENEWAL", "Renewal"

    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="assessment_fees")
    farm = models.ForeignKey(Farm, on_delete=models.PROTECT, related_name="assessment_fees")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.INITIAL)

    # The snapshot of the band this fee was declared under.
    turnover_band = models.CharField(max_length=8, help_text="The band code, e.g. B3.")
    band_label = models.CharField(max_length=64, help_text="The band as the OPP prints it.")
    declared_turnover_cents = models.BigIntegerField()
    amount_cents = models.IntegerField()  # §III: integer cents, never a float

    declared_on = models.DateField(default=timezone.localdate)
    due_on = models.DateField(
        null=True,
        blank=True,
        help_text="OPP §2.3: payable prior to the farm assessment visit. Set when the visit is scheduled.",
    )
    paid_on = models.DateField(null=True, blank=True)
    receipt_no = models.CharField(max_length=64, blank=True)
    is_significant_change = models.BooleanField(
        default=False,
        help_text=(
            "OPP §2.3: renewal applies only where no significant changes have occurred; "
            "a significant change means the initial rate, declared as an INITIAL fee."
        ),
    )

    class Meta:
        ordering = ["member_id", "farm_id", "declared_on"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(declared_turnover_cents__gte=0),
                name="assessment_fee_turnover_is_not_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(amount_cents__gte=0),
                name="assessment_fee_amount_is_not_negative",
            ),
            # OPP §2.3: "Renewal fees apply only where no significant changes … have
            # occurred." The two are contradictory, so the pair is refused rather than
            # quietly re-priced: which rate applies is the group's call, not a computation's.
            models.CheckConstraint(
                condition=~models.Q(is_significant_change=True) | models.Q(kind="INITIAL"),
                name="assessment_fee_significant_change_is_not_a_renewal",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.get_kind_display()} {self.turnover_band} @ {self.farm_id}"

    @property
    def is_paid(self) -> bool:
        """Paid as recorded — never inferred from a due date (§III)."""
        return self.paid_on is not None
