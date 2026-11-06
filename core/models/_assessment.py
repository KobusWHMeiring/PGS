"""Assessment templates: the questionnaire a farm is assessed against, as versioned data.

Schema and snapshots, not questionnaires in code. The spec's §4.8 rule is the reason this file is
small: *code encodes the PGS process; data encodes the standard and the group.* A questionnaire is
the standard's, so `schema` is a JSON document imported from a file by `load_template` (D28), and a
new standard version is a new row — never a migration.

**The one rule that cannot be softened:** `Assessment.template_schema` (MVP 1a Flow C) freezes a
*full copy* of this JSON when a visit starts. Editing a template must never alter a historical
assessment, which is why a correction is a new `version` and why `is_active` moves rather than
overwrites (B2). A template row is therefore append-mostly: the schema of a template that has ever
been used is history, and this module offers no path that edits one.

Versioning lives in the service layer (`core.services._templates`), not here: `activate_template`,
`current_template` and the schema validator are rules, and §II puts rules where they can be tested
before the view that reaches them exists.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class AssessmentTemplate(models.Model):
    """One version of one category's questionnaire.

    `version` is per category, not global: the animal sheet's numbering starts again at v1, and the
    pair `(category, version)` is what `load_template` is idempotent on.

    `standard_version` names the *standard* this template implements (e.g. `SAOSO v2.1 (2026)`), so a
    visit from three years ago can say which standard its questions came from without reading the
    schema for a clue. It is free text on purpose: SAOSO's own version strings are the standard's
    language, not this platform's.
    """

    category = models.ForeignKey(
        "core.Category",
        on_delete=models.PROTECT,
        related_name="templates",
        help_text="The FORM sheet this questionnaire belongs to (spec §4.1).",
    )
    version = models.CharField(
        max_length=32,
        help_text="Per category, e.g. 'v1'. Changing a question is a new version, never an edit.",
    )
    standard_version = models.CharField(
        max_length=64,
        help_text="The standard this template implements, e.g. 'SAOSO v2.1 (2026)'.",
    )
    schema = models.JSONField(
        help_text=(
            "The questionnaire: sections, questions, verdicts and their polarity. Validated by "
            "core.services._templates.validate_schema before it is written, never by the database."
        ),
    )
    effective_from = models.DateField(
        default=timezone.localdate,
        help_text="When this version became the one a new visit may use.",
    )
    is_active = models.BooleanField(
        default=False,
        help_text=(
            "Whether a visit may be started against this version. Default False: a half-authored "
            "file must not be live. Activation is B2's service, which deactivates the previous one."
        ),
    )

    class Meta:
        ordering = ["category_id", "-effective_from", "-id"]
        constraints = [
            # `load_template` is idempotent on this pair, so the pair has to mean one row.
            models.UniqueConstraint(
                fields=["category", "version"], name="uniq_assessment_template_version"
            ),
            # B2: one live template per category at any time. A partial unique index rather than a
            # service check, because the service is a rule the next caller can skip — an admin edit,
            # a fixture or a data migration would create the state a check alone only forbids in one
            # doorway. Two writers cannot both win an index.
            models.UniqueConstraint(
                fields=["category"],
                condition=models.Q(is_active=True),
                name="uniq_active_template_per_category",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.category_id}:{self.version}"

    @property
    def question_count(self) -> int:
        """How many questions the schema holds. Display only — no visitor logic reads a count."""
        return sum(
            len(section.get("questions") or [])
            for section in (self.schema or {}).get("sections") or []
        )

    @property
    def verdict_count(self) -> int:
        """How many verdicts the schema holds — the completeness invariant B3 asserts."""
        return len((self.schema or {}).get("verdicts") or [])
