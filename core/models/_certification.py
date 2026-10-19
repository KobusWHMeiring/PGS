"""Certification data: the seals the standard authorises and the categories assessed.

These are **tables, not enums** (spec §4.8, `build_principles.md` §I). The
acceptance test is: *retargeting to another standard or PGS group must not require
a migration.* Adding a seal, retiring one, or publishing a new assessment category
is therefore a seed change.

The rule that carries the most weight here is D11/F3, and it is a rule about what
the platform may **claim**, not about what it may store:

    OPP §V authorises three marks. The third, "PGS pasture-raised", carries the
    standard's own admission that its criteria are "details on this forthcoming".
    It is a real seal with undefined criteria, and it is not being shipped.

So it exists as an **inactive row**. When the national working group publishes
criteria, enabling it is a seed change — not a migration, not a code release. Until
then, two rules keep it off the public surface:

1. `is_active=False` blocks issuance **unconditionally** — see
   `core/services/_certification.assert_seal_issuable`, where no override reaches it.
2. An inactive seal is **never rendered** on a public page. It is a dormant row
   awaiting the working group, not content.

Note the distinction that a future reader is most likely to collapse:
`is_active=False` is *not* the same as `criteria_defined=False`. An **active** seal
whose criteria cannot be machine-checked is overridable by an administrator with a
recorded rationale. An **inactive** seal is not overridable at all, because the
group has decided not to publish the claim.
"""

from __future__ import annotations

from django.db import models


class Seal(models.Model):
    """A mark the standard authorises a group to issue (OPP §V).

    `code` deliberately carries **no `choices=`**. A choice list would make adding a
    seal a code change plus a migration, which is exactly what §4.8 forbids; the
    deployed set is seeded per group by `seed_deployment`.
    """

    code = models.CharField(
        max_length=64,
        unique=True,
        help_text="Stable identifier, e.g. PGS_ORGANIC_CERTIFIED. Not a choice field.",
    )
    label = models.CharField(
        max_length=128,
        help_text="The mark's name exactly as the standard prints it.",
    )
    standard_ref = models.CharField(
        max_length=64,
        help_text="The clause that authorises this seal, e.g. 'OPP §V'.",
    )
    is_active = models.BooleanField(
        default=False,
        help_text=(
            "Whether this deployment may issue the seal. False blocks issuance "
            "unconditionally — no administrator override (D11/F3)."
        ),
    )
    criteria_defined = models.BooleanField(
        default=True,
        help_text=(
            "Whether the seal's criteria are published and machine-checkable. "
            "False on an *active* seal requires an override with a recorded rationale."
        ),
    )
    display_note = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Why the seal is in its current state, in the standard's own words where "
            "possible. Shown as a 'criteria forthcoming' note, never as a claim."
        ),
    )

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.code} ({'active' if self.is_active else 'inactive'})"


class Category(models.Model):
    """An assessment category (FORM Sheets A–H).

    Also **no `choices=`**: the deployed set is group data. `AQUACULTURE`, `WINE`
    and `INPUT_SUPPLIER` are marked *in development* in FORM Sheets F/G/H and are
    seeded **inactive** rather than omitted, so publishing them later is a data
    change (spec §4.1).
    """

    code = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=128)
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Ordering for the admin and the public site, so neither hardcodes a list.",
    )
    is_active = models.BooleanField(default=True)
    standard_ref = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="The FORM sheet or clause this category is assessed against.",
    )

    class Meta:
        ordering = ["display_order", "code"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return self.code
