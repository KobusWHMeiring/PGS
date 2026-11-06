"""Eligibility: may this member be assessed, or keep a certificate at all?

A7's gate, sliced out of `_membership.py` when that module passed the 30 KB cap
(`build_principles.md` §II). The seam is the domain's own: `_membership` records what a
member attested and invoiced (the pledge, the fee scale, the subscription), and this
module decides what **standing** those records add up to. `_membership` imports the one
refusal it still needs; nothing here imports back.

OPP §2.3 states the money rule — *"Only fully paid-up members will be eligible for farm
assessments and receive certificates."* OPP §4.6 states the one exception to the
*standing* rule, and the two are not the same sentence:

- **Termination for a critical transgression forfeits the logo.** Termination for a
  non-critical one does not: the membership stands, the right to use the logo stands, and
  the member is *"under probation for one calendar year following the ruling"*. So
  `PROBATION` is a pass with a warning and not a refusal — refusing it here would revoke a
  right the OPP explicitly keeps.
- **Probation does not excuse the subscription.** "Fully paid-up" is §2.3's rule for every
  member, so a probationary member who has not paid is refused for the same reason an
  active one would be.

This is the **member** half of the visit gate. A5's `assert_fees_paid_for_assessment()` in
`_membership.py` is the **farm** half: a member can be perfectly eligible and still owe
this farm's assessment fee, and "your membership has lapsed" is a different conversation
from "this farm's fee is unpaid". C1's `confirm_visit()` is where the two meet.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.models import Member


class NotEligibleError(Exception):
    """The family every "this member may not be assessed" refusal belongs to.

    A caller that only has to say *not yet* catches this one class; a caller that has to
    say **why** catches the named subclass — the same shape as `PledgeDeclarationError`
    carrying three different mismatches.

    Raised alone only for a `Member.status` this module does not recognise, where there is
    no better name to give and failing closed is the only safe answer.
    """


class MembershipUnpaidError(NotEligibleError):
    """OPP §2.3: *"Only fully paid-up members will be eligible for farm assessments."*

    Lives here because every other refusal in this family does, and `_membership.py`'s
    `assert_fees_paid_for_assessment()` imports it to raise the same refusal on the visit
    path: an unpaid member is not eligible, whether the question is asked about the
    certificate or about the visit.
    """


class ApplicantNotEligibleError(NotEligibleError):
    """An application that has not become a paid-up membership yet.

    OPP §2.3 makes *fully paid-up* the condition, and an applicant has been invoiced
    nothing: the group records the fee and its payment, and only then is there a member to
    assess (A6's `record_membership_fee()` / `record_membership_payment()`).
    """


class MembershipLapsedError(NotEligibleError):
    """A membership that stopped being current, so the logo cannot be carried.

    Distinct from an unpaid subscription: a lapsed member is not a lapsed *invoice*, and
    reinstatement is a committee decision (OPP §4.7), not a payment.
    """


class MembershipTerminatedError(NotEligibleError):
    """OPP §4.6, the critical branch: *"the right to market their products bearing our
    endorsement and logo will be forfeited."*

    A receipt does not undo this — `record_membership_payment()` refuses to reinstate a
    terminated member for exactly this reason, and OPP §4.7 makes re-application a new
    application one calendar year later.
    """


#: The warning code a caller branches on. A code, not the English sentence, so no caller
#: has to match on prose (the same reason `MISSING_RECORD_BLOCKS_FINALISE` is a constant).
PROBATION_WARNING = "PROBATION"


@dataclass(frozen=True)
class EligibilityWarning:
    """One thing a caller must say about a member the gate let through.

    `code` is for logic and stays stable; `message` is the reviewed sentence a page
    renders. Both, because a view needs the sentence and a later guard needs the code.
    """

    code: str
    message: str


@dataclass(frozen=True)
class EligibilityVerdict:
    """A pass, and the warnings that come with it.

    **A refusal is an exception, not a value.** There is deliberately no `allowed` field:
    a field that can only ever be `True` is an invitation to write `if verdict.allowed:`
    and quietly do nothing about the refusal, which is the failure mode the raise exists to
    prevent.

    **There is no `status` field either.** The status lives on `Member.status`, and a copy
    in a frozen value object is a second source of truth that goes stale the moment the row
    changes — the objection D39 raises to a stored `is_paid_up`. What the gate *adds* is the
    warning list, so that is all it returns.
    """

    warnings: tuple[EligibilityWarning, ...] = ()


def _probation_warning(member: Member) -> EligibilityWarning:
    """The sentence a page shows for a probationary member (OPP §4.6).

    OPP §4.6 fixes the period at one calendar year; when the group recorded an end date
    (D38's `probation_until`) it is printed, because "until when?" is the next question and
    the answer is data the group entered.
    """
    message = (
        "This member is under probation after a non-critical transgression: OPP §4.6 "
        "keeps the membership and the right to use the logo, and reviews the probation "
        "after one calendar year."
    )
    if member.probation_until is not None:
        until = member.probation_until
        message = f"{message} The group recorded it as ending on {until.day} {until:%B %Y}."
    return EligibilityWarning(code=PROBATION_WARNING, message=message)


def assert_eligible_for_assessment(member: Member) -> EligibilityVerdict:
    """The member-standing gate: may this member be assessed, or keep a certificate?

    In:  `member` — the row, read as it stands. Nothing is passed in that could stand in
         for the row: a caller cannot hand this function a status or a paid-up flag.
    Out: `EligibilityVerdict` — a pass, carrying the warnings a caller must surface. For an
         `ACTIVE`, paid-up member the value is empty, which is the ordinary case.
    Side Effects: at most one query — `Member.is_paid_up` reads the fee rows (D39).
    Fails: `ApplicantNotEligibleError`, `MembershipLapsedError`,
         `MembershipTerminatedError`, or `MembershipUnpaidError`, all subclasses of
         `NotEligibleError`. The status is checked **before** the payment, deliberately:
         telling a terminated member they owe a subscription is the wrong conversation, and
         it is the order `assert_fees_paid_for_assessment()` already uses. A status this
         module does not recognise fails closed rather than open.

    **`PROBATION` passes with a warning**, and that is the shape decision A7 had to make: a
    function that raises has no return value to carry a flag, so it returns a verdict with
    `warnings` instead of `None`. The alternative — pass silently and let each caller read
    `member.status` — would put OPP §4.6's exception in every caller instead of here, where
    the clause is cited, and the first caller that forgot it would refuse a member the OPP
    protects. No `is_eligible` field is added to `Member` (A5/A8 precedent: derive the fact,
    or store it — never both).
    """
    status = member.status
    if status == Member.Status.APPLICANT:
        raise ApplicantNotEligibleError(
            "the application is not complete: OPP §2.3 makes fully paid-up membership the "
            "condition, and the group records the fee and its payment first"
        )
    if status == Member.Status.LAPSED:
        raise MembershipLapsedError(
            "OPP §2.3: a lapsed membership is not eligible for farm assessments; "
            "reinstatement is a committee decision (OPP §4.7)"
        )
    if status == Member.Status.TERMINATED:
        raise MembershipTerminatedError(
            "OPP §4.6: a terminated membership forfeits the right to market under the logo"
        )
    if status not in (Member.Status.ACTIVE, Member.Status.PROBATION):
        raise NotEligibleError(
            f"unrecognised member status {status!r} — the gate fails closed rather than "
            "guessing what an unknown state permits (spec §4.1 lists five)"
        )
    if not member.is_paid_up:
        raise MembershipUnpaidError(
            "OPP §2.3: only fully paid-up members are eligible for farm assessments"
        )
    if status == Member.Status.PROBATION:
        return EligibilityVerdict(warnings=(_probation_warning(member),))
    return EligibilityVerdict()
