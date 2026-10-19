"""Identity: the account and the roles it holds.

`User` is a **custom user model from the first migration**, not a later addition.
Swapping it afterwards is a painful, multi-step migration, which is why sub-plan A
gates everything else in MVP 0.

Role is **plural and contextual** (spec §3, axis 1). A person is not "a Farmer",
they *hold* the Farmer role, and one person is routinely several at once — the
spec's own example is a farmer who is also a peer assessor and a consumer. So
roles are rows in `UserRole`, never boolean fields on `User`.

`Member` — the membership record that governs *eligibility*, independent of login
— is a different concept and arrives with sub-plan B/§4.1, not here. A `User` can
exist with no membership at all: that is a plain public visitor.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models

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
