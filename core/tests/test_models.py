"""Task A3 — the custom `User`, plural roles, and the role-derived capability rule.

Role is **plural and contextual** (spec §3, axis 1): a person is not "a Farmer",
they *hold* the Farmer role, and one person is routinely several at once — a farmer
who is also a peer assessor and a consumer. Hence `UserRole` rather than booleans
on `User`.

Capabilities are derived from the role set and never checked ad hoc in views
(spec §3). The `ADMIN` role "also implies `ASSESSOR`" (spec §3 table) — see
`test_capability_never_implies_role_storage` for how that implication is applied
and why it is not stored as a row.
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import ASSESSOR_CAPABILITY, Language, Role, User, UserRole

pytestmark = pytest.mark.django_db


# --- Plural roles (the plan's two named tests) -------------------------------


def test_user_holds_zero_or_more_roles(user_factory):
    u = user_factory()
    assert not u.has_role("ASSESSOR")
    u.roles.create(role="ASSESSOR")
    u.roles.create(role="FARMER")
    assert u.has_role("ASSESSOR", "FARMER")  # any-of semantics
    assert not u.has_role("ADMIN")


def test_capability_never_implies_role_storage(user_factory):
    """`ADMIN` confers assessor capability without an `ASSESSOR` row appearing.

    The implication is applied by the *caller* — spec §3's own idiom is
    `user.has_role('ASSESSOR', 'ADMIN')` — so `has_role` stays a pure membership
    check and role rows always say exactly what a human granted.
    """
    u = user_factory()
    u.roles.create(role="ADMIN")
    assert u.has_role("ASSESSOR") is False
    assert not u.roles.filter(role=Role.ASSESSOR).exists()


def test_assessor_capability_covers_admin_without_being_forgotten(user_factory):
    """The implication is named once, so a view cannot silently deny an admin.

    A view that gates the assessor PWA on `has_role('ASSESSOR')` alone would lock
    out every administrator — a bug with no error message. `ASSESSOR_CAPABILITY`
    exists so call sites pass the whole set and the rule lives in one place.
    """
    u = user_factory()
    u.roles.create(role=Role.ADMIN)
    assert u.has_role(*ASSESSOR_CAPABILITY)
    assert ASSESSOR_CAPABILITY == frozenset({Role.ASSESSOR, Role.ADMIN})


def test_has_role_accepts_either_the_enum_or_the_raw_value(user_factory):
    u = user_factory()
    u.roles.create(role=Role.COMMITTEE)
    assert u.has_role(Role.COMMITTEE)
    assert u.has_role("COMMITTEE")


def test_no_roles_means_a_plain_public_visitor(user_factory):
    """Spec §3: a user holding no roles is a plain public visitor — not an error."""
    u = user_factory()
    assert u.roles.count() == 0
    assert not u.has_role(*Role.values)


def test_the_same_role_cannot_be_held_twice(user_factory):
    u = user_factory()
    u.roles.create(role=Role.FARMER)
    with pytest.raises(IntegrityError), transaction.atomic():
        u.roles.create(role=Role.FARMER)


def test_role_set_is_exactly_the_governing_spec_set():
    """Roles are PGS process, so they are code (spec §3 table), not seeded data.

    Pinned as a literal set so that inventing a role, or dropping one, is a
    deliberate edit and not a silent divergence. `VALUE_CHAIN_ACTOR` is the
    group's own term — never "retailer" (backlog CONVENTION.md).
    """
    assert set(Role.values) == {
        "FARMER",
        "ASSESSOR",
        "CONSUMER",
        "VALUE_CHAIN_ACTOR",
        "ACADEMIC",
        "ADMIN",
        "COMMITTEE",
    }


# --- The custom user's own fields (spec §4 model sketch) ---------------------


def test_popia_and_verification_consent_are_never_assumed(user_factory):
    """A fresh account has consented to nothing (spec §, POPIA).

    `popia_consent_at` is set from an explicit act, so a default of `now()` — or a
    non-null field — would manufacture consent that was never given.
    """
    u = user_factory()
    assert u.popia_consent_at is None
    assert u.email_verified_at is None
    assert u.graduated_from_public_at is None


def test_graduated_from_public_at_records_promotion(user_factory):
    """Spec §3.1: a public visitor keeps the same `User` when they become a member."""
    u = user_factory()
    u.graduated_from_public_at = timezone.now()
    u.roles.create(role=Role.FARMER)
    u.save()
    u.refresh_from_db()
    assert u.graduated_from_public_at is not None
    assert u.has_role(Role.FARMER)


def test_preferred_language_defaults_to_english_and_offers_afrikaans(user_factory):
    """D7/D18: English and Afrikaans are both first-class, so both must be offered.

    Defaults to English because content is English until a named Afrikaans
    speaker reviews it (D18) — the shell is bilingual, the content is not yet.
    """
    assert user_factory().preferred_language == Language.EN
    assert set(Language.values) == {"en", "af"}


def test_a_username_is_still_required(user_factory):
    """The custom user extends `AbstractUser`; it does not abandon its contract.

    `blank=False` is a *validation* rule, not a database constraint — Postgres
    happily stores an empty string, because `unique=True` only forbids a second
    one. So the honest assertion is on `full_clean()`, not on `save()`. Writing
    this test against `IntegrityError` fails, which is what happened here first.
    """
    from django.core.exceptions import ValidationError

    field = User._meta.get_field("username")
    assert field.blank is False
    assert field.unique is True

    with pytest.raises(ValidationError) as exc:
        User(username="", email="someone@example.org").full_clean()
    assert "username" in exc.value.message_dict


def test_django_superuser_does_not_imply_the_admin_role(user_factory):
    """`is_superuser` and `Role.ADMIN` are different axes and must stay separate.

    `createsuperuser` yields `is_staff`/`is_superuser` but **no roles** — verified
    by running it. That is correct: Django's flags are technical access to
    `/admin/`, while `Role.ADMIN` is PGS standing to drive visits and compile
    reports (spec §3). A database administrator is not automatically a PGS
    administrator, and `has_role` must not consult `is_superuser` — otherwise the
    domain rule silently inherits a technical one.

    The practical consequence: seeding the first ADMIN role is a deliberate act.
    """
    u = user_factory(is_staff=True, is_superuser=True)
    assert u.has_role(Role.ADMIN) is False
    u.roles.create(role=Role.ADMIN)
    assert u.has_role(Role.ADMIN) is True


def test_user_role_rows_delete_with_their_user(user_factory):
    """Roles are not evidentiary, so `CASCADE` is correct here (§I lists the
    immutable models, and `UserRole` is not one of them)."""
    u = user_factory()
    u.roles.create(role=Role.CONSUMER)
    user_id = u.pk
    u.delete()
    assert not UserRole.objects.filter(user_id=user_id).exists()
