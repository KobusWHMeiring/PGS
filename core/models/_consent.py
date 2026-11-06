"""POPIA consent: the wording, and the act of agreeing to it.

Two tables, because a consent has two halves and conflating them loses the one that
matters:

- **`ConsentText` is the wording**, written by the group (SELF_CHECK_PRD Q8: *"written by
  the group rather than by the build"*). It is **versioned, not edited**: a row is added,
  never changed, so a member's consent keeps the meaning it had when they gave it — the
  same rule as `Assessment.template_schema` and `FarmCategory`'s missing pre-application
  value. `approved_at` is null for a draft, so a page can say *"the group has not approved
  this yet"* instead of implying that it has.
- **`ConsentRecord` is the act** — who agreed to which version, when. It is a timestamp
  of something a person did, never a boolean default (§3.6) and never an inference from
  a form submission that did not carry a tick.

The purposes are **code, not data**, and that is the one place this module departs from
"data encodes the standard and the group": a purpose is a POPIA fact about *this*
platform's processing (spec §3, §7), and §3.6's whole argument is that the purposes are
distinct and stay distinct. The *wording* of each one is data, which is what makes a
group able to approve, tighten or translate it without a migration.

Why not `User.popia_consent_at` alone: it records *that* registration consent was given,
not *what* was agreed to. Both are written by the same act in A6 — the column is the
cheap query the spec names, this table is the audit trail Q8 requires.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from core.models._core import User


class ConsentPurpose(models.TextChoices):
    """The processing purposes a member can consent to, kept separate (§3.6).

    `RESEARCH` and `DEMOGRAPHICS` are the public self-check's two consents (E1 and E2 in
    `SELF_CHECK_PRD`); `ACCOUNT` is Q8's third. They are listed together so that a page
    can explain what it is *not* asking, which §11.6's "why we ask" body does in as many
    words.
    """

    RESEARCH = "RESEARCH", "Research reporting"
    DEMOGRAPHICS = "DEMOGRAPHICS", "Census and demographics"
    ACCOUNT = "ACCOUNT", "Holding an account"


class ConsentTextQuerySet(models.QuerySet):
    """The one query this table exists to answer: which wording is current?"""

    def current(self, purpose: str) -> "ConsentText | None":
        """The newest text for a purpose, or None when the group has not written one.

        In:  `purpose` — a `ConsentPurpose` value.
        Out: the latest `ConsentText` row, or None.
        Side Effects: one query.
        Fails: never. None is the honest answer, and every caller must handle it —
             accepting a consent with no wording behind it is the failure this returns
             None to prevent.
        """
        return self.filter(purpose=purpose).order_by("-id").first()


class ConsentText(models.Model):
    """One version of one consent, as the group wrote it."""

    purpose = models.CharField(max_length=32, choices=ConsentPurpose.choices)
    version = models.CharField(
        max_length=64,
        help_text=(
            "A slug the record keeps forever, e.g. 'account-2026-11-05'. Never the "
            "primary fact: `ConsentRecord` points at the row, so the wording travels with it."
        ),
    )
    heading = models.CharField(max_length=200)
    body = models.TextField(help_text="Plain text; blank lines separate paragraphs.")
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Null means DRAFT — written by the build for the group to correct, not yet "
            "adopted by it. The interface must say so rather than present it as approved."
        ),
    )

    objects = ConsentTextQuerySet.as_manager()

    class Meta:
        ordering = ["purpose", "-id"]
        constraints = [
            # Two versions cannot share a name: a consent record quoting a version must
            # identify exactly one wording.
            models.UniqueConstraint(
                fields=["purpose", "version"], name="uniq_consent_text_version"
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.purpose}:{self.version}"

    @property
    def is_draft(self) -> bool:
        """True until the group adopts this wording. Display only — never a guard."""
        return self.approved_at is None


class ConsentRecord(models.Model):
    """One person's consent to one version of one text.

    `withdrawn_at` rather than a delete: a withdrawal is evidence too, and Q8 promises
    that writing in is enough to withdraw — no login is required to be deleted, so the
    absence of a row cannot be the proof that consent was withdrawn.
    """

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="consents")
    text = models.ForeignKey(ConsentText, on_delete=models.PROTECT, related_name="records")
    given_at = models.DateTimeField(default=timezone.now)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["user_id", "-given_at"]
        constraints = [
            # Consenting twice to the same wording is the same consent. Withdrawal is a
            # timestamp on the row, not a second row.
            models.UniqueConstraint(
                fields=["user", "text"], name="uniq_user_consent_text"
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.user_id}:{self.text_id}"
