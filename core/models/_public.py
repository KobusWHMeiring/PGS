"""The public document library: the files the group publishes (D22).

`build_principles.md` §I: *code encodes the process; data encodes the standard and
the group.* Which documents a group publishes is group data — another PGS group
publishes its own standard, its own procedures and its own forms — so the list is a
table seeded per deployment, never a Python tuple rendered by a template. Adding or
retiring a document is a seed change; the acceptance test in §4.8 ("retargeting must
not require a migration") applies here exactly as it does to `Seal` and `Category`.

**Why `file_path` is a `CharField` and not a `FileField`.** A `FileField` resolves
its location through `FileSystemStorage.location`, which is a **cached property** —
so a settings override (in a test, or in a deploy that moves `MEDIA_ROOT`) keeps
serving the first location it ever computed, silently. `testing_hazards.md` §1 is
full of that shape: the runner changes the value under test and the test passes
anyway. A plain relative path read through `settings.MEDIA_ROOT` at request time has
no cache to go stale, and it makes the rule §VI states — *public derivatives live
under a separate public root* — a property of the path rather than of storage
configuration.

**What this model does not have is as deliberate as what it has.** There is no
`is_restricted` flag and no `audience` field: D22 says dossiers are **never**
public, so a dossier is not a row at all. A flag would invite a template to render a
restricted row, and the first mistake there publishes a farmer's personal data. The
only gate is `is_published`, and the download view cannot see an unpublished row.
"""

from __future__ import annotations

from pathlib import Path

from django.core.validators import RegexValidator
from django.db import models

#: A URL segment, not Django's slug. `validate_slug` is `[-a-zA-Z0-9_]+`, which would
#: refuse `saoso-standard-v2.1` at `full_clean()` while the database accepted it —
#: the §1.7 trap (validation is not a constraint), inverted. A version number belongs
#: in the address, because a document cited as `/documents/saoso-standard-v2.1/` must
#: not silently change when v2.2 is published.
CODE_PATTERN = RegexValidator(
    r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$",
    "Lowercase letters, digits, and single dots or hyphens between them — the code is "
    "a URL segment, so it may not contain spaces, slashes or capitals.",
)


class PublicDocumentQuerySet(models.QuerySet):
    """`published()` is the only filter a public view may use."""

    def published(self) -> PublicDocumentQuerySet:
        return self.filter(is_published=True)


class PublicDocument(models.Model):
    """One published file, at a stable `/documents/<code>/` address.

    `code` is the URL. It is validated at write time and matched by a `<str:code>`
    route, because Django's own slug validator is narrower than a URL segment and
    would have refused the version number in `saoso-standard-v2.1`.
    """

    code = models.CharField(
        max_length=64,
        unique=True,
        validators=[CODE_PATTERN],
        help_text="Stable URL segment, e.g. 'opp'. The document lives at /documents/<code>/.",
    )
    title = models.CharField(max_length=160)
    note = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="The one-line description under the title on the documents list.",
    )
    file_path = models.CharField(
        max_length=255,
        help_text=(
            "Path under MEDIA_ROOT, e.g. 'public/documents/opp.pdf'. Never a media URL: "
            "the public address is /documents/<code>/ and nothing else."
        ),
    )
    content_type = models.CharField(
        max_length=100,
        default="application/pdf",
        help_text="Stored, not guessed from the suffix: a browser that receives "
        "application/octet-stream downloads a PDF that it would otherwise display.",
    )
    source_path = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Where the served copy came from, e.g. 'pgs_docs/saoso-version-2.1-2026.pdf'. "
            "Provenance, so a published file can be traced to the shipped document."
        ),
    )
    download_name = models.CharField(
        max_length=160,
        blank=True,
        default="",
        help_text=(
            "The filename the browser saves, e.g. 'SAOSO-Organic-Standard-v2.1.pdf'. "
            "Seed data, not derived: 'saoso-standard-v2.1.pdf' is a URL segment, and a "
            "farmer filing it wants the document's name."
        ),
    )
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(
        default=False,
        help_text="False hides the row from the list and 404s its download. The only gate.",
    )

    objects = PublicDocumentQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "code"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.code} ({'published' if self.is_published else 'unpublished'})"

    @property
    def kind(self) -> str:
        """The type badge the design prints (`PDF`), derived so it cannot disagree."""
        return Path(self.file_path).suffix.lstrip(".").upper() or "FILE"
