"""Identity: the account and the roles it holds.

`User` is a **custom user model from the first migration**, not a later addition.
Swapping it afterwards is a painful, multi-step migration, which is why sub-plan A
gates everything else in MVP 0.

Role is **plural and contextual** (spec §3, axis 1). A person is not "a Farmer",
they *hold* the Farmer role, and one person is routinely several at once — the
spec's own example is a farmer who is also a peer assessor and a consumer. So
roles are rows in `UserRole`, never boolean fields on `User`.

`Member` — the membership record that governs *eligibility*, independent of login —
is the second half of this module (spec §4.1 "Core & Membership"). A `User` can
exist with no membership at all: that is a plain public visitor, and the spec's
`User.graduated_from_public_at` records the moment they engage further.

`Farm`, `FarmAlias`, `FarmCategory` and `FarmContact` are the farm's identity. Two
rules keep them honest: **`FarmCategory.status` has no pre-application value**
(D36 — a tick in the public self-check must not become an application), and
**census fields live on `Member`, never on `Farm`** (they describe a person, so a
public farm page has no route to them by construction).
"""

from __future__ import annotations

import re
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

# --- Roles ------------------------------------------------------------------


class Role(models.TextChoices):
    """The seven account roles (spec §3, axis 1).

    These are **code, not seeded data**. `build_principles.md` §I splits the two:
    data encodes the standard and the group (seals, categories, documents,
    questionnaires), while the *PGS process* — and role is part of the process —
    is common to every group and belongs in code.
    """

    FARMER = "FARMER", "Farmer"
    ASSESSOR = "ASSESSOR", "Assessor"
    CONSUMER = "CONSUMER", "Consumer"
    # The group's own term. Never "retailer" (backlog CONVENTION.md).
    VALUE_CHAIN_ACTOR = "VALUE_CHAIN_ACTOR", "Value chain actor"
    ACADEMIC = "ACADEMIC", "Academic"
    ADMIN = "ADMIN", "Administrator"
    COMMITTEE = "COMMITTEE", "Committee"


# Spec §3: "`ADMIN` | Staff ... | Also implies `ASSESSOR`." The implication is
# applied at the call site — spec §3's own idiom is `has_role('ASSESSOR', 'ADMIN')`
# — and is deliberately **not** expanded inside `has_role` or stored as a row, so
# that role rows always record exactly what a human granted.
#
# It is a named constant because the failure mode is silent: a view gating the
# assessor PWA on `has_role(Role.ASSESSOR)` alone would lock out every
# administrator, with no error to notice. Call sites pass `*ASSESSOR_CAPABILITY`.
ASSESSOR_CAPABILITY: frozenset[Role] = frozenset({Role.ASSESSOR, Role.ADMIN})


class Language(models.TextChoices):
    """D7/D18 — English and Afrikaans are both first-class.

    The *mechanism* is bilingual from the start; page content and chatbot answers
    stay English until a named Afrikaans-speaking member has reviewed them. A
    machine translation never satisfies this.
    """

    EN = "en", "English"
    AF = "af", "Afrikaans"


# --- Accounts ---------------------------------------------------------------


class User(AbstractUser):
    """An account. Holds zero or more roles; holds no inherent capability.

    Extends `AbstractUser` rather than replacing it: the password hashing,
    permission machinery and admin integration are not worth reimplementing, and
    the extra fields below are additive.

    POPIA note: consent is recorded as a *timestamp of an act*, never as a
    boolean default. `popia_consent_at` is null until someone consents, and
    purpose-specific consent (assessment processing, public farm profile,
    photographic publication) is recorded separately in MVP 2. Sentry is
    configured with `send_default_pii=False` for the same reason.
    """

    phone = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Store as entered; normalise to E.164 at the UI boundary, not here.",
    )
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Null means unverified. Absence of verification is not a lockout.",
    )
    popia_consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When POPIA consent was given. Null means it has not been.",
    )
    preferred_language = models.CharField(
        max_length=8,
        choices=Language.choices,
        default=Language.EN,
        help_text="Default language for this user's surface (D7).",
    )
    graduated_from_public_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Spec §3.1 — when a public visitor became a member. The same User is "
            "kept throughout; roles are added to it rather than a new person created."
        ),
    )

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def has_role(self, *roles: str) -> bool:
        """Any-of check over the roles this user actually holds.

        In:  `roles` — `Role` members or raw values, e.g. `has_role(Role.ASSESSOR)`.
        Out: True if the user holds at least one of them.
        Side Effects: none; performs one query.
        Fails: never — a user holding no roles simply returns False.

        `ADMIN` is **not** expanded here. A capability that admins share with
        assessors must be requested as `has_role(*ASSESSOR_CAPABILITY)`, so that a
        stored role row always means what it says (spec §3).
        """
        if not roles:
            return False
        return self.roles.filter(role__in=roles).exists()


class UserRole(models.Model):
    """A role held by a user. Zero or more per user (spec §3, axis 1).

    Its own table rather than a `ManyToManyField` so that a grant can later carry
    its own facts (who granted it, when, per visit) without a schema rewrite.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    role = models.CharField(max_length=32, choices=Role.choices)

    class Meta:
        constraints = [
            # Holding ASSESSOR twice grants nothing and only creates ambiguity
            # about which row a reviewer should trust.
            models.UniqueConstraint(fields=["user", "role"], name="uniq_user_role"),
        ]
        ordering = ["user_id", "role"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.user_id}:{self.role}"


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


_SPACE_RUN = re.compile(r"\s+")


def _name_key(value: str) -> str:
    """Case, outer whitespace and runs of internal whitespace removed."""
    return _SPACE_RUN.sub(" ", value or "").strip().casefold()
