"""The membership domain: who is a member, what they farm, and what they hold.

Split out of `_core.py` when that slice reached 21 KB against the 30 KB cap
(`build_principles.md` §II). The seam is the one the spec already draws: §4.1 is
titled *"Core & Membership"*, and this module is the second half of it. `_core.py`
keeps the **account** (`User`, `UserRole`, `Role`, `Language`); this one holds the
**membership record and everything that hangs off it** — the farm, its spellings,
the categories applied for, the people the group contacts, the committee roster and
the fees.

A `User` can exist with no membership at all: that is a plain public visitor, and
the spec's `User.graduated_from_public_at` records the moment they engage further.
Nothing here may be assumed from a login, and nothing here grants a capability —
membership governs *eligibility*, roles govern *access*.

Three rules keep these models honest, each with the decision that produced it:

- **`is_paid_up` is derived, never stored**, and it reads the fee row's own period
  (D39). "Payable by the end of February" is group policy, and group policy is data.
- **`FarmCategory.status` has no pre-application value** (D36). A tick in the public
  self-check must not be able to become an application (`test_membership.py`
  names this test `test_a_tick_is_not_an_application`).
- **Census fields live on `Member`, never on `Farm`.** They describe a person, so a
  public farm page has no route to them by construction rather than by an exclusion
  list somebody has to remember.
"""

from __future__ import annotations

import os
import re
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify

from core.models._core import User

# --- Membership (spec §4.1) -------------------------------------------------


class Member(models.Model):
    """The membership record — it governs *eligibility*, independent of login.

    `membership_no` is printed on certificates, so it is **public** and shaped
    `OUT-<year>-<seq:04d>`, never a bare autoincrement (D39).
    """

    class Status(models.TextChoices):
        APPLICANT = "APPLICANT", "Applicant"
        ACTIVE = "ACTIVE", "Active"
        PROBATION = "PROBATION", "Probation"
        LAPSED = "LAPSED", "Lapsed"
        TERMINATED = "TERMINATED", "Terminated"

    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="member")
    membership_no = models.CharField(max_length=32, unique=True, blank=True)
    joined_on = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.APPLICANT)
    probation_until = models.DateField(null=True, blank=True)  # D38: the way out
    expertise = models.ManyToManyField(
        "core.Category", blank=True, related_name="experts"
    )  # drives peer-assessor assignment (§3.1)

    # FORM Sheet A census fields. ``sensitive`` in the spec's sense: they are
    # excluded from every public surface, and they are here rather than on `Farm`
    # so that exclusion is structural instead of remembered.
    census_gender = models.CharField(max_length=32, blank=True)
    census_age_band = models.CharField(max_length=32, blank=True)
    census_demographic_group = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["membership_no"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return self.membership_no or f"member:{self.pk}"

    @property
    def is_paid_up(self) -> bool:
        """Derived, never stored (D39) — and read from the row's own period.

        "Payable by the end of February" is group policy, so it is data on the
        fee row, not a calendar year in this method. A stored boolean would be a
        second source of truth that goes stale the day a period rolls over.
        """
        today = timezone.localdate()
        return self.fees.filter(
            paid_on__isnull=False, period_start__lte=today, period_end__gte=today
        ).exists()

    def save(self, *args, **kwargs):
        if not self.membership_no:
            self.membership_no = self._next_membership_no()
        super().save(*args, **kwargs)

    @classmethod
    def _next_membership_no(cls) -> str:
        """`OUT-<year>-<seq:04d>` (D39).

        Two concurrent first-of-year applications can read the same maximum; the
        unique index on the column is what makes that safe (one wins, the other
        fails its insert) rather than silently issuing a duplicate number. A
        retry belongs with the service that creates members, not here.
        """
        prefix = f"OUT-{timezone.localdate().year}-"
        last = (
            cls.objects.filter(membership_no__startswith=prefix)
            .order_by("-membership_no")
            .values_list("membership_no", flat=True)
            .first()
        )
        seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
        return f"{prefix}{seq:04d}"


_SPACE_RUN = re.compile(r"\s+")


def _name_key(value: str) -> str:
    """Case, outer whitespace and runs of internal whitespace removed."""
    return _SPACE_RUN.sub(" ", value or "").strip().casefold()


class Farm(models.Model):
    """A farm, its canonical name, and the spellings that must resolve to it.

    No `catchment` (D37 — a deployment setting), no `current_status` (D35 — it
    derives from a Certificate that does not exist in 1a), and no PostGIS: GPS is
    optional, never published and never spatially queried (D34).
    """

    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="farms")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    physical_address = models.TextField(blank=True)
    nearest_town = models.CharField(max_length=120, blank=True)  # D39: plain text
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    total_hectares = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    public_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    publish_consent = models.BooleanField(default=False)
    publish_consent_at = models.DateTimeField(null=True, blank=True)
    first_certified_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:120]
        super().save(*args, **kwargs)

    @classmethod
    def resolve(cls, name: str) -> "Farm | None":
        """One canonical farm from any spelling the group has used (§4.1).

        The live records carry "Chillin Out Farm" / "CHILLOUT FARM" and worse, so
        a lookup that only matches `name` silently forks a farm. Case, surrounding
        whitespace and runs of internal whitespace are all noise.

        The common case is an exact (case-insensitive) hit and stays in SQL. The
        normalised scan is the honest fallback for the rest; a group has tens of
        farms, not millions, and a key column the spec does not have would be a
        schema invention to serve a micro-optimisation.
        """
        stripped = (name or "").strip()
        if not stripped:
            return None

        exact = cls.objects.filter(name__iexact=stripped).first()
        if exact is not None:
            return exact
        alias = FarmAlias.objects.filter(name__iexact=stripped).select_related("farm").first()
        if alias is not None:
            return alias.farm

        key = _name_key(stripped)
        for candidate_name, pk in cls.objects.values_list("name", "pk").iterator():
            if _name_key(candidate_name) == key:
                return cls.objects.get(pk=pk)
        for alias_name, farm_id in FarmAlias.objects.values_list("name", "farm_id").iterator():
            if _name_key(alias_name) == key:
                return cls.objects.get(pk=farm_id)
        return None


class FarmAlias(models.Model):
    """A historical or external spelling of a farm's name.

    Exists so the migration and every later spelling resolve to one farm, and so a
    verification lookup by an old name still lands.
    """

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="aliases")
    name = models.CharField(max_length=200)
    source = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["farm_id", "name"]
        constraints = [
            models.UniqueConstraint(fields=["farm", "name"], name="uniq_farm_alias"),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return self.name


class FarmCategory(models.Model):
    """What a farm applies to be assessed for, and where that application got to.

    The four values are an **application lifecycle**. There is deliberately no
    pre-application value: a category ticked in the public self-check is a label in
    `SelfCheckReport.other_categories`, never a row here (SELF_CHECK_PRD §4.1,
    "a tick is not an application").
    """

    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Applied"
        FOR_ASSESSMENT = "FOR_ASSESSMENT", "For assessment"
        ASSESSED = "ASSESSED", "Assessed"
        INACTIVE = "INACTIVE", "Inactive"

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="categories")
    category = models.ForeignKey(
        "core.Category", on_delete=models.PROTECT, related_name="farm_categories"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.APPLIED)
    first_assessed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["farm_id", "category_id"]
        constraints = [
            models.UniqueConstraint(fields=["farm", "category"], name="uniq_farm_category"),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.farm_id}:{self.category_id}"


class FarmContact(models.Model):
    """A person the group deals with about this farm, including the hosting contact."""

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=64, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["farm_id", "name"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.name} ({self.role})" if self.role else self.name


class CommitteePosition(models.TextChoices):
    """The eleven positions OPP §3.1 defines and OPP §VII fills (spec §3.2).

    A committee *position* is not the `COMMITTEE` account role: the position is a
    governance fact about a term, the role is a capability on a login. They are
    deliberately separate, because the roster is renewed at every AGM while the
    logins are not.
    """

    CHAIRPERSON = "CHAIRPERSON", "Chairperson"
    VICE_CHAIRPERSON = "VICE_CHAIRPERSON", "Vice-Chairperson"
    SECRETARY = "SECRETARY", "Secretary"
    TREASURER = "TREASURER", "Treasurer"
    FARM_VISIT_ADMINISTRATION = (
        "FARM_VISIT_ADMINISTRATION",
        "Farm visit administration and reporting",
    )
    TECHNICAL_FARMING_SUPPORT = "TECHNICAL_FARMING_SUPPORT", "Technical farming support"
    COMMUNICATIONS = "COMMUNICATIONS", "Communications"
    EVENTS_COORDINATION = "EVENTS_COORDINATION", "Events coordination and management"
    CONSUMER_REPRESENTATIVE = "CONSUMER_REPRESENTATIVE", "Consumer representative"
    RETAIL_MARKET_REPRESENTATIVE = (
        "RETAIL_MARKET_REPRESENTATIVE",
        "Retail and market representative",
    )
    ACADEMIC_REPRESENTATIVE = "ACADEMIC_REPRESENTATIVE", "Academic representative"


class CommitteeTerm(models.Model):
    """One person's hold on one committee position for one AGM year.

    A **term**, not an attribute (spec §3.2): composition is renewed at every AGM, so
    a `User.is_committee` flag would have to be cleared every year and would lose the
    history of who served when.

    `user` is **nullable**, and `holder_name` is the printed name. The OPP's roster
    names eight people who do not have accounts — and should not be given empty ones
    to satisfy a FK. When a holder registers, the term is linked; until then the name
    is the record.

    A **blank `holder_name` is a vacancy**, not a missing row: the OPP advertises
    events coordination and academic representation as open (`TBC — call for
    expressions of interest`). Deleting the row instead would make "nobody has
    applied" indistinguishable from "we lost the data".

    No contact details: a position is a public governance fact (plan A2).
    """

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="committee_terms",
        help_text="Set once the holder has an account. The roster precedes the login.",
    )
    holder_name = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=64, choices=CommitteePosition.choices)
    agm_year = models.PositiveSmallIntegerField()
    elected_on = models.DateField(
        null=True,
        blank=True,
        help_text="Null when the source names only the AGM year — never invent the day.",
    )
    vacated_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["agm_year", "position", "holder_name"]
        constraints = [
            # The natural key that makes seeding idempotent. It is NOT unique on
            # (position, agm_year): one position can be held by several people at once
            # (farm visit administration: four), and one person can hold two positions.
            models.UniqueConstraint(
                fields=["position", "agm_year", "holder_name"], name="uniq_committee_term"
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.get_position_display()}: {self.holder_name or 'vacant'} ({self.agm_year})"

    @property
    def is_vacant(self) -> bool:
        """True for an advertised open seat — a row that exists and has no holder."""
        return not (self.holder_name or "").strip()


def pledge_evidence_storage_location() -> str:
    """The private root (§VI) — evidence photos are personal data, not public assets.

    A function rather than an inlined `settings.PRIVATE_MEDIA_ROOT` so the path is read
    from whichever settings module is loaded (test, dev, production) instead of at import.
    """
    return os.path.abspath(settings.PRIVATE_MEDIA_ROOT)


@deconstructible
class PrivateMediaStorage(FileSystemStorage):
    """`FileSystemStorage` rooted at `PRIVATE_MEDIA_ROOT`, with no public URL at all.

    Not `FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)`: Django resolves the
    `storage=` callable **once, at field definition time**, so an instance built from
    settings at import bakes the path in — a test cannot point it at a temporary
    directory, and the migration serialises the machine that generated it. Hence a
    deconstructible subclass (migrations name the class, not a path) whose `location` is
    read per access.

    `base_url` is None, so `FieldFile.url` raises rather than handing back a `/media/`
    URL that would 404 at best. Private media is served only after Django authorises the
    request and hands off to nginx via `X-Accel-Redirect` against an `internal` location.
    """

    @property
    def location(self) -> str:
        return pledge_evidence_storage_location()

    @property
    def base_url(self) -> None:  # type: ignore[override]
        return None


class Pledge(models.Model):
    """What a member attested, and in what form the group can evidence it.

    **Two pledges, not one with optional parts.** The OPP prints a farmer pledge and
    a consumer pledge on facing pages; only the farmer's attests to land. `kind` is
    therefore required, and a consumer row carrying a land history, a witness or an
    in-conversion declaration is refused by the service *and* by a constraint — the
    form never offered those fields, so a row that has them describes a signing that
    did not happen.

    **The farmer pledge is an OR.** Either the land-history attestation ("free of
    prohibited pesticides, herbicides and fertilisers for at least 12 months … 12 …
    18 …") or "I/We have applied for In-Conversion status" with a 12-or-18-month
    selection. Exactly one branch is representable, because that is what is printed,
    and both are recorded because they are the basis of the In-Conversion decision.

    **`land_history_conflict` is stored, where `Member.is_paid_up` is derived.** A
    fee period rolls over, so a stored paid-up boolean goes stale; a signed
    declaration does not change, and the flag is the record of what the two
    governing documents said *on the day it was signed* (build_principles §I,
    Immutable History). It is set by `core.services._membership.record_pledge` — the rule that
    computes it belongs in the service layer (§II) — and `None` means "not
    applicable": no land-history branch was taken, so there is nothing to judge.

    `evidence_document` is the OPP §I.2 record for a pledge given verbally or by
    distinctive mark: *"recorded by the PGS through photographic or other documented
    record"*.
    """

    class Kind(models.TextChoices):
        FARMER = "FARMER", "Farmer"
        CONSUMER = "CONSUMER", "Consumer"

    class Method(models.TextChoices):
        SIGNATURE = "SIGNATURE", "Signed"
        # OPP §I.2: "Signature(s)/distinctive marks" — the path for members who
        # cannot read and sign. Not a lesser pledge; a different way of making one.
        DISTINCTIVE_MARK = "DISTINCTIVE_MARK", "Signed with a distinctive mark"
        VERBAL_WITNESSED = "VERBAL_WITNESSED", "Given verbally, witnessed and recorded"

    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="pledges")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    method = models.CharField(
        max_length=32, choices=Method.choices, default=Method.SIGNATURE
    )
    signed_on = models.DateField(default=timezone.localdate)
    place = models.CharField(max_length=120, blank=True)

    # --- The farmer pledge's OR --------------------------------------------
    declared_land_history_ok = models.BooleanField(default=False)
    in_conversion_declared = models.BooleanField(default=False)
    in_conversion_months = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="The 12-or-18-month period the form offers."
    )
    # The months declared clear of prohibited inputs, per crop group. Decimal months
    # are not representable and are not asked for: the form says "at least 12".
    declared_annual_clear_months = models.PositiveSmallIntegerField(null=True, blank=True)
    declared_pasture_clear_months = models.PositiveSmallIntegerField(null=True, blank=True)
    declared_perennial_clear_months = models.PositiveSmallIntegerField(null=True, blank=True)
    land_history_conflict = models.BooleanField(
        null=True,
        blank=True,
        help_text=(
            "D31/D83 — True when a declared period falls in the band where SAOSO "
            "4.2.3 and OPP §V disagree. None when no land history was declared."
        ),
    )

    # --- Who recorded it, and on what evidence ------------------------------
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_pledges",
        help_text="OPP §I.2: the administrator completes the documentation on the member's behalf.",
    )
    witness_name = models.CharField(max_length=200, blank=True)
    witness_designation = models.CharField(max_length=120, blank=True)
    witness_signature = models.CharField(max_length=200, blank=True)
    evidence_document = models.FileField(
        upload_to="pledge_evidence/%Y/%m/",
        storage=PrivateMediaStorage(),
        blank=True,
        help_text="The photograph or other documented record of a verbal pledge (OPP §I.2).",
    )

    class Meta:
        ordering = ["member_id", "signed_on"]
        constraints = [
            # The consumer pledge has no witness block and no land history. Blanking
            # the fields instead of refusing them would store a claim the member never
            # made; the service refuses it with a message, and this is the backstop.
            models.CheckConstraint(
                condition=~models.Q(kind="CONSUMER")
                | models.Q(
                    witness_name="",
                    witness_designation="",
                    witness_signature="",
                    evidence_document="",
                    declared_land_history_ok=False,
                    in_conversion_declared=False,
                    in_conversion_months__isnull=True,
                    declared_annual_clear_months__isnull=True,
                    declared_pasture_clear_months__isnull=True,
                    declared_perennial_clear_months__isnull=True,
                    land_history_conflict__isnull=True,
                ),
                name="pledge_consumer_carries_no_farmer_declarations",
            ),
            # "□ 12 months or □ 18 months (select)" — the form offers two, so a row
            # can hold neither, one, or the other, and nothing else.
            #
            # The `isnull=False` is load-bearing, not decoration: `NULL IN (12, 18)` is
            # NULL in SQL, and a CHECK that evaluates to NULL is *satisfied* by Postgres.
            # Without it, "in-conversion, no period selected" — the exact row this is
            # meant to refuse — passed the constraint and the test caught it.
            models.CheckConstraint(
                condition=~models.Q(in_conversion_declared=True)
                | (
                    models.Q(in_conversion_months__isnull=False)
                    & models.Q(in_conversion_months__in=(12, 18))
                ),
                name="pledge_in_conversion_period_is_offered_by_the_form",
            ),
            # "… for at least 12 months … OR I/We have applied for In-Conversion" —
            # exactly one branch, because the printed form is an OR.
            models.CheckConstraint(
                condition=~models.Q(kind="FARMER")
                | (
                    models.Q(declared_land_history_ok=True)
                    & models.Q(in_conversion_declared=False)
                )
                | (
                    models.Q(declared_land_history_ok=False)
                    & models.Q(in_conversion_declared=True)
                ),
                name="pledge_farmer_takes_exactly_one_branch",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.get_kind_display()} pledge ({self.signed_on})"
