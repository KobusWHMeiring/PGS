"""Seal issuance rules.

`build_principles.md` §II puts business logic in services, so the seal guard lives
here rather than in a model `save()` override or a view. That also lets the rule be
tested *before* MVP 2's `Certificate` model exists: when it arrives, its service
calls `assert_seal_issuable()` and inherits the invariant rather than restating it.

Why this matters enough to have its own module: a seal is a public claim. Issuing
"PGS pasture-raised" would assert that a farm meets criteria the standard itself
says are "forthcoming" (OPP §V) — a claim that cannot be substantiated to a
consumer. So the failure mode is not a wrong row in a table; it is an unsubstantiated
public claim, which is why `is_active=False` has no override path at all.
"""

from __future__ import annotations

from django.db.models import QuerySet

from core.models import Seal


class InactiveSealError(Exception):
    """Raised when issuance is attempted for a seal this deployment does not ship.

    Deliberately **not** a subclass of a validation error that a view might swallow
    into a form message: reaching this is a programming or configuration error, not
    something a user can correct by editing a field.
    """


class UndefinedCriteriaError(Exception):
    """An active seal whose criteria are not published, issued without a rationale."""


def assert_seal_issuable(seal: Seal, *, override_rationale: str = "") -> None:
    """Guard every path that would issue a seal.

    In:  `seal` — the row about to be issued.
         `override_rationale` — an administrator's recorded justification. It is
         **only** consulted for an active seal with undefined criteria, and it must
         be non-blank, so the audit trail cannot be satisfied by an empty string.
    Out: None.
    Side Effects: none. Deliberately side-effect free so callers control the
         transaction and the audit record.
    Fails:
        InactiveSealError — `is_active` is False. **Unconditional**; the override
            is not consulted, so no administrator can issue a seal the group has
            decided not to ship (D11/F3).
        UndefinedCriteriaError — the seal is active but its criteria are not
            published, and no non-blank rationale was supplied.
    """
    # Checked first and unconditionally. Ordering is the safeguard: an override can
    # never reach a seal this deployment does not issue.
    if not seal.is_active:
        raise InactiveSealError(
            f"Seal {seal.code!r} is inactive for this deployment and cannot be issued. "
            f"{seal.display_note}".strip()
        )

    if not seal.criteria_defined and not override_rationale.strip():
        raise UndefinedCriteriaError(
            f"Seal {seal.code!r} has no published criteria; an administrator override "
            f"with a recorded rationale is required to issue it."
        )


def issuable_seals() -> QuerySet[Seal]:
    """The seals this deployment may offer, for forms, APIs and listings.

    In: none. Out: `QuerySet[Seal]` of active seals.
    Side Effects: none.
    Fails: never.

    Excludes inactive seals at the query so that a future form or endpoint cannot
    offer the deferred mark by forgetting to filter — the exclusion is asserted by
    test rather than trusted at each call site.
    """
    return Seal.objects.filter(is_active=True)
