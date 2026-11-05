"""The public self-check's two tables — what a visitor answered, if they let us keep it.

D71 and `SELF_CHECK_PRD` §4.1. Two rules shape these models and both are absences:

- **No FK to `Member` or `Farm`, and no `User`.** Most visitors will never have either, and a report
  must never *become* an application record — the whole promise of `/before-you-apply/` is that it is
  not an application. The service resolves a ticked category to a `Category` row (categories are
  data), and stops there.
- **Nothing here is a status.** There is no `is_eligible`, no `score`, no derived boolean. A report is
  what somebody answered on a day; the farm visit decides, and `MVP1A_PRD` §5.8 is the rule the
  result page quotes.

`SelfCheckDemographic` is a **separate table** rather than a set of nullable columns, and that is
§3.6's argument in schema form: "excluded from every serializer" holds by construction, and a
withdrawal can delete the census details without deleting the answers (or the other way round). It
is a `OneToOneField`, because one report has one demographic answer set.

`public_uuid` is the only identifier a browser sees — a sequential id in a URL would publish how many
farmers answered, which is a claim about the group's catchment before anybody has decided to publish
one (`build_principles.md` §I).

The wording a visitor agreed to is not copied into the row: `consent_text_version` names the
`ConsentText` row, exactly as `Member`'s consents do (`ConsentRecord`). Two versions of the same
purpose cannot share a name (a constraint on `ConsentText`), so the version string identifies one
text — and the report keeps the *version*, not a copy, because a copy would drift.
"""

from __future__ import annotations

import uuid

from django.db import models

from core.models._certification import Category


class SelfCheckReport(models.Model):
    """One completed check, kept only because research consent was ticked.

    Every band is a **label**, never a number and never derived from another column: the OPP's fee
    labels are printed as the OPP prints them, and hectares are a band because an exact figure plus a
    category plus a turnover band names a farm in a catchment of a few dozen (`SELF_CHECK_PRD` §3.1).
    """

    public_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_on = models.DateField(auto_now_add=True)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text="The first category ticked; the rest are labels in `other_categories`.",
    )
    other_categories = models.JSONField(
        default=list, blank=True, help_text="Category keys, never FKs: a tick is not an application."
    )
    hectares_band = models.CharField(max_length=32, blank=True)
    pasture_band = models.CharField(max_length=32, blank=True)
    land_history_band = models.CharField(max_length=32, blank=True)
    turnover_band = models.CharField(
        max_length=64, blank=True, help_text="The OPP §2.3 label, declared by the visitor."
    )
    records_held = models.JSONField(
        default=dict, blank=True, help_text='{"B1": "YES" | "PARTLY" | "NO" | "RATHER_NOT_SAY", …}'
    )
    practices = models.JSONField(
        default=dict, blank=True, help_text='{"C1": "YES" | "NO" | "MIX" | …, …}'
    )
    exit_reason = models.CharField(max_length=32, blank=True)
    exit_note = models.CharField(max_length=280, blank=True)
    research_consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Null would mean a row written without consent — which the service never does.",
    )
    consent_text_version = models.CharField(
        max_length=64,
        blank=True,
        help_text="The `ConsentText.version` the visitor read. A version, not a copy of the text.",
    )

    class Meta:
        ordering = ["-created_on", "-id"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"self-check {self.public_uuid}"


class SelfCheckDemographic(models.Model):
    """The census answer set, in its own table, only when both consents were given.

    The three field names and their storage are **the same as `Farm`'s** on purpose: an export must
    not be able to tell the two apart by accident, and a classification that changes in two places is
    a classification that disagrees with itself. They are free text (the FORM prints the categories,
    so the categories are the group's data), and they are blank-able because "rather not say" is an
    answer (`SELF_CHECK_PRD` §3.5).
    """

    report = models.OneToOneField(
        SelfCheckReport,
        on_delete=models.CASCADE,
        related_name="demographic",
        primary_key=True,
    )
    census_gender = models.CharField(max_length=32, blank=True)
    census_age_band = models.CharField(max_length=32, blank=True)
    census_demographic_group = models.CharField(max_length=64, blank=True)

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"self-check demographics {self.report_id}"
