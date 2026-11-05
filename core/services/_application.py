"""The application flow — Flow A, spec §7 — as rules, not as pages.

The pages live in `core/views/_portal.py` and the markup in `core/templates/portal/`.
What lives here is what a view is not allowed to decide: whether an account may exist,
what an account creates, what counts as a completed step, and which step may be reached.

Three boundaries are deliberate:

- **The account is not an application.** `Member{APPLICANT}` is the internal state (D83);
  nothing here sets `ACTIVE`, because OPP §2.3 ties that to a paid membership fee and a
  self-registration cannot pay it. A view that could write `Member.status` would make
  `assert_eligible_for_assessment` a suggestion.
- **Steps are derived from rows, never from a session.** "Where am I in the flow?" is a
  query: a pledge exists, categories exist, a fee is declared. A session flag would let a
  refreshed tab disagree with the database, and a resumed application is the whole reason
  the account exists.
- **The Q8 consent is required, and versioned.** No consent text, no account; a form
  rendered against an older version is refused rather than recorded against wording the
  farmer did not read (`ConsentText`). This is also where a deployment that has not
  written the text fails **closed** instead of shipping a checkbox with nothing behind it.

Nothing here knows about `FarmVisit`. `confirm_visit()` belongs to C1 and calls A5's
`assert_fees_paid_for_assessment()`; the application flow only produces the rows that
gate reads. Building the visit here would be a forward dependency, and A5's precedent was
to leave the guard waiting for its caller.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from core.models import (
    AssessmentFee,
    Category,
    ConsentPurpose,
    ConsentRecord,
    ConsentText,
    Farm,
    FarmCategory,
    FarmContact,
    Member,
    Pledge,
    Role,
    User,
    UserRole,
)


class ApplicationError(Exception):
    """Base for everything a view must turn into a message, never a 500."""


class ConsentRequiredError(ApplicationError):
    """No Q8 consent (or no wording to consent to) — SELF_CHECK_PRD §11.6."""


class ConsentTextChangedError(ApplicationError):
    """The wording changed after the form was rendered. The farmer read the old one."""


class EmailAlreadyRegisteredError(ApplicationError):
    """One account per address: the address is the username."""


class FarmNameTakenError(ApplicationError):
    """A1 resolves spellings to one farm; a self-registration must not fork it."""


class StepOutOfOrderError(ApplicationError):
    """A later step was reached before an earlier one was done."""


class CategoriesRequiredError(ApplicationError):
    """A category tick *is* the application (D36); an empty list applies for nothing."""


@dataclass(frozen=True)
class ApplicantDetails:
    """Exactly what the account step collects (Q7), and nothing declarative.

    D83 is why there is no land history, no attestation and no turnover here: the pledge
    attests to *"all the land for which I/we are applying"*, and that sentence cannot be
    signed before the account names the farm.
    """

    first_name: str
    last_name: str
    email: str
    phone: str
    farm_name: str
    nearest_town: str
    contact_name: str


@dataclass(frozen=True)
class ApplicationStep:
    """One step of the applicant's own part of Flow A.

    `done` is read from the database at the moment it is asked, never stored. The
    membership fee is **not** a step: the applicant's part ends at the declaration, and
    the group records the money (see `core.services._membership.record_membership_fee`).
    """

    key: str
    title: str
    done: bool


STEP_TITLES: tuple[tuple[str, str], ...] = (
    ("account", "Your account"),
    ("pledge", "The farmer pledge"),
    ("categories", "What you want assessed"),
    ("turnover", "Your turnover"),
)


def create_application(
    details: ApplicantDetails,
    *,
    password: str,
    consent_version: str,
    consent_given: bool,
) -> Member:
    """Create the account, the membership record and the farm — one transaction.

    In:  `details` — the seven fields the account step asks (Q7).
         `password` — already validated by the form; hashed here by `create_user`.
         `consent_version` — the version string the rendered form carried.
         `consent_given` — the tick, as an act and not a default (§3.6).
    Out: the new `Member`, status `APPLICANT`, with `User`, `UserRole{FARMER}`, `Farm`,
         `FarmContact` and one `ConsentRecord` behind it.
    Side Effects: five INSERTs. Sets `User.popia_consent_at` — the spec's own column
         (§7.2) — and the consent record, so the fact and the wording are both kept.
    Fails: `ConsentRequiredError` when the tick is absent or no account wording exists;
         `ConsentTextChangedError` when the posted version is not the current one;
         `EmailAlreadyRegisteredError`; `FarmNameTakenError`.
    """
    text = ConsentText.objects.current(ConsentPurpose.ACCOUNT)
    if text is None:
        raise ConsentRequiredError(
            "The wording for holding an account has not been written for this deployment "
            "yet (SELF_CHECK_PRD Q8), so no account can be created. Ask the administrator."
        )
    if not consent_given:
        raise ConsentRequiredError(
            "We cannot keep your details without your consent. Your answers are not stored "
            "unless you tick the box."
        )
    if consent_version != text.version:
        raise ConsentTextChangedError(
            "The consent wording changed while this form was open. Please read it again "
            "and re-confirm."
        )

    email = (details.email or "").strip().lower()
    if User.objects.filter(username__iexact=email).exists() or User.objects.filter(
        email__iexact=email
    ).exists():
        raise EmailAlreadyRegisteredError(
            "An account with this email address already exists — log in instead of "
            "registering again."
        )
    farm_name = (details.farm_name or "").strip()
    if Farm.resolve(farm_name) is not None:
        raise FarmNameTakenError(
            f"A farm recorded as “{farm_name}” is already in the group's records. The "
            "administrator will help you connect this account to it rather than create a "
            "second one."
        )

    with transaction.atomic():
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=details.first_name.strip(),
            last_name=details.last_name.strip(),
            phone=(details.phone or "").strip(),
            popia_consent_at=timezone.now(),
        )
        UserRole.objects.create(user=user, role=Role.FARMER)
        member = Member.objects.create(user=user)
        farm = Farm.objects.create(
            member=member,
            name=farm_name,
            nearest_town=(details.nearest_town or "").strip(),
        )
        FarmContact.objects.create(
            farm=farm,
            name=details.contact_name.strip(),
            role="APPLICANT",
            email=email,
            phone=(details.phone or "").strip(),
        )
        ConsentRecord.objects.create(user=user, text=text)
    return member


def application_farm(member: Member) -> Farm:
    """The farm this application is about.

    In: `member`.
    Out: the member's first farm, by id.
    Side Effects: one query.
    Fails: `ApplicationError` — an account with no farm is not an application, and a
         silent None would make every later step write to nothing.
    """
    farm = member.farms.order_by("id").first()
    if farm is None:
        raise ApplicationError("this account has no farm yet, so there is nothing to apply for")
    return farm


def application_progress(member: Member) -> tuple[ApplicationStep, ...]:
    """Where the applicant is, derived from rows (never from a session).

    In: `member`.
    Out: one `ApplicationStep` per step, in flow order, with `done` read now.
    Side Effects: at most three queries.
    Fails: never — an account with no farm simply has the account step done and the rest
         open.
    """
    farm = member.farms.order_by("id").first()
    done = {
        "account": True,
        "pledge": member.pledges.filter(kind=Pledge.Kind.FARMER).exists(),
        "categories": bool(farm and farm.categories.exists()),
        "turnover": bool(
            farm and AssessmentFee.objects.filter(member=member, farm=farm).exists()
        ),
    }
    return tuple(ApplicationStep(key, title, done[key]) for key, title in STEP_TITLES)


def assert_step_ready(member: Member, key: str) -> None:
    """Refuse a step whose predecessor is not done.

    In: `member`; `key` — the step being entered.
    Out: None.
    Side Effects: reads `application_progress`.
    Fails: `StepOutOfOrderError`, naming the first step that is still open. A view turns
         that into a redirect to `core:apply`, which lands the applicant on that step.
    """
    order = [step_key for step_key, _ in STEP_TITLES]
    if key not in order:
        raise ValueError(f"unknown application step: {key!r}")
    for earlier in application_progress(member)[: order.index(key)]:
        if not earlier.done:
            raise StepOutOfOrderError(
                f"“{key}” needs “{earlier.key}” first — that step is still open."
            )


def record_application_categories(member: Member, *, category_ids) -> list[FarmCategory]:
    """Turn the applicant's ticks into `FarmCategory` rows (spec §7.4).

    In:  `member`; `category_ids` — the posted ids, already validated by the form.
    Out: the farm's category rows after the write, ordered by category.
    Side Effects: INSERTs for new ticks, and DELETEs for ticks removed **while still
         `APPLIED`**. An `ASSESSED` row is history and is never deleted by a re-submit
         (build_principles §I, Immutable History).
    Fails: `CategoriesRequiredError` for an empty list; `ValueError` for an id that is
         not an active category.
    """
    ids = {int(pk) for pk in category_ids}
    if not ids:
        raise CategoriesRequiredError(
            "Tick at least one category: a tick is what makes this an application."
        )
    active = set(Category.objects.filter(pk__in=ids, is_active=True).values_list("pk", flat=True))
    if active != ids:
        raise ValueError(f"not an active category: {sorted(ids - active)}")

    farm = application_farm(member)
    with transaction.atomic():
        existing = {row.category_id: row for row in farm.categories.all()}
        for category_id in ids - set(existing):
            FarmCategory.objects.create(
                farm=farm, category_id=category_id, status=FarmCategory.Status.APPLIED
            )
        for category_id, row in existing.items():
            if category_id not in ids and row.status == FarmCategory.Status.APPLIED:
                row.delete()
    return list(farm.categories.order_by("category_id").select_related("category"))
