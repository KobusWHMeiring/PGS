"""Task A7 — the eligibility gates: may this member be assessed at all?

OPP §2.3 makes *"fully paid-up members"* the condition for an assessment and for a
certificate; OPP §4.6 makes probation the one standing exception. The four refusals and
the one pass are here, each a named error, because each one is a different sentence to
say to a farmer:

- an **applicant** has been invoiced nothing yet, and the group's records are the reason;
- a **lapsed** member stopped being current, and reinstatement is a committee decision;
- a **terminated** member forfeited the logo (OPP §4.6, critical branch);
- an **unpaid** member owes the group the subscription it invoiced (OPP §2.3);
- a **probationary** member passes — OPP §4.6 keeps the membership and the logo — and the
  verdict carries the warning a page must show.

**Two things this file refuses to do, both of which would make a green test meaningless.**

1. It never writes `status=ACTIVE` to pass a member through the gate. There is a service
   that produces that state (`record_membership_payment()`), so the pass case pays a real
   invoice for a real period and asserts the gate on the row it produced. The paid-up
   *derivation* is exercised too: the "active but unpaid" case is last year's fee paid and
   this year's invoice open, which is what a member in arrears actually looks like.
2. It sets `LAPSED`, `TERMINATED` and `PROBATION` directly, and says so. Nothing in this
   platform produces those states — the discipline workflow is out of scope (§17.1) and
   D38's `probation_until` is written by nobody — so there is no service to call. A test
   that pretended otherwise would be inventing a workflow A7 does not own.

The gap this task cannot close is asserted below rather than described in a comment: no
module in a running instance records a membership fee or its payment, so in a live demo
every applicant stays `APPLICANT` and the gate refuses them. `MISSING_FEE_SURFACE` in
`product/backlog/todo.md` is the decision that closes it.
"""

from __future__ import annotations

import ast
import pathlib
from datetime import timedelta

import pytest
from django.utils import timezone

from core.models import Member, MembershipFee
from core.services._eligibility import (
    PROBATION_WARNING,
    ApplicantNotEligibleError,
    EligibilityVerdict,
    MembershipLapsedError,
    MembershipTerminatedError,
    MembershipUnpaidError,
    NotEligibleError,
    assert_eligible_for_assessment,
)
from core.services._membership import record_membership_fee, record_membership_payment

pytestmark = pytest.mark.django_db


def _pay(member, *, days_ago=0):
    """Pay one annual period that covers today, through the real services.

    A period that ended last year is what `days_ago=400` builds: the member was paid up
    then and is not now.
    """
    today = timezone.localdate()  # §1.35: dates about "now" are derived, never written
    start = today - timedelta(days=days_ago)
    fee = record_membership_fee(
        member,
        kind="ANNUAL",
        period_start=start,
        period_end=start + timedelta(days=364),
        amount_cents=10_000,
    )
    return record_membership_payment(fee, paid_on=start, receipt_no="R-001")


def _paid_up_member(member, status=None):
    """A member who paid the subscription the group invoiced, in the given status.

    `status=None` leaves the status the services produce (`ACTIVE`); the three states no
    service produces are passed in explicitly by the test that needs them.
    """
    _pay(member)
    if status is not None:
        member.status = status
        member.save(update_fields=["status"])
    member.refresh_from_db()
    return member


# --- The four refusals -------------------------------------------------------


def test_an_applicant_is_refused(member):
    """An applicant is not a member yet: nothing has been invoiced, so nothing is paid.

    The message has to name the group's act, not the applicant's omission — a farmer who
    filled in every step of A6's flow has done nothing wrong.
    """
    assert member.status == Member.Status.APPLICANT
    with pytest.raises(ApplicantNotEligibleError) as caught:
        assert_eligible_for_assessment(member)
    assert "paid-up" in str(caught.value)


def test_a_lapsed_member_is_refused_even_though_the_dues_were_paid(member):
    """Lapsed is a standing failure, not an arrears one — so this member is paid up.

    If the gate only checked money, this test would pass for the wrong reason.
    """
    member = _paid_up_member(member, status=Member.Status.LAPSED)
    assert member.is_paid_up is True
    with pytest.raises(MembershipLapsedError):
        assert_eligible_for_assessment(member)


def test_a_terminated_member_is_refused_even_though_the_dues_were_paid(member):
    """OPP §4.6: termination forfeits the right to market under the logo."""
    member = _paid_up_member(member, status=Member.Status.TERMINATED)
    assert member.is_paid_up is True
    with pytest.raises(MembershipTerminatedError) as caught:
        assert_eligible_for_assessment(member)
    assert "logo" in str(caught.value)


def test_an_active_member_in_arrears_is_refused(member):
    """Last year's fee paid, this year's invoice open — an active member who owes.

    This is the only honest way to build "ACTIVE and unpaid": the services activate on
    payment, so the row arrives ACTIVE from a real receipt and then stops being paid up
    when the period it paid for ends. Writing `status=ACTIVE` by hand would assert
    nothing about the payment half of the gate.
    """
    _pay(member, days_ago=400)
    member.refresh_from_db()
    assert member.status == Member.Status.ACTIVE
    assert member.is_paid_up is False
    with pytest.raises(MembershipUnpaidError):
        assert_eligible_for_assessment(member)


# --- The pass, and the warning that comes with it ----------------------------


def test_an_active_paid_up_member_passes(member):
    """The ordinary case: the value is empty, and it is the verdict type, not `None`."""
    member = _paid_up_member(member)
    verdict = assert_eligible_for_assessment(member)
    assert isinstance(verdict, EligibilityVerdict)
    assert verdict.warnings == ()


def test_probation_passes_with_a_warning(member):
    """OPP §4.6, the non-critical branch: the membership and the logo are **not** revoked.

    A gate that refused this would revoke a right the OPP explicitly keeps, which is why
    the warning exists instead of an exception.
    """
    member = _paid_up_member(member, status=Member.Status.PROBATION)
    verdict = assert_eligible_for_assessment(member)
    assert [warning.code for warning in verdict.warnings] == [PROBATION_WARNING]
    assert "§4.6" in verdict.warnings[0].message


def test_the_probation_warning_prints_the_end_date_the_group_recorded(member):
    """D38's `probation_until` is a date nothing writes yet — so if it is set, print it.

    Otherwise the field is write-only in both directions: set by nobody, read by nobody.
    """
    member = _paid_up_member(member, status=Member.Status.PROBATION)
    member.probation_until = timezone.localdate() + timedelta(days=200)
    member.save(update_fields=["probation_until"])
    message = assert_eligible_for_assessment(member).warnings[0].message
    assert f"{member.probation_until.day} {member.probation_until:%B %Y}" in message


def test_probation_does_not_excuse_an_unpaid_subscription(member):
    """OPP §2.3's money rule applies to every member; §4.6 only softens the standing one."""
    _pay(member, days_ago=400)
    member.status = Member.Status.PROBATION
    member.save(update_fields=["status"])
    with pytest.raises(MembershipUnpaidError):
        assert_eligible_for_assessment(member)


# --- The edges that keep the gate honest ------------------------------------


def test_the_status_is_checked_before_the_payment(member):
    """A terminated member in arrears is refused for the termination.

    The order is the wrong-conversation rule A5 already applies to the fee gate: "you owe
    us" is not the first thing to say to a member the group removed.
    """
    member = _paid_up_member(member, status=Member.Status.TERMINATED)
    MembershipFee.objects.filter(member=member).update(paid_on=None)
    with pytest.raises(MembershipTerminatedError):
        assert_eligible_for_assessment(member)


@pytest.mark.parametrize(
    "status",
    [
        Member.Status.APPLICANT,
        Member.Status.LAPSED,
        Member.Status.TERMINATED,
    ],
)
def test_every_refusal_is_one_catch(member, status):
    """One `except` for the family, a named subclass for the reason.

    A caller that can only render "not yet" should not have to enumerate the reasons, and
    a caller that must explain itself should not have to match on a message string.
    """
    member = _paid_up_member(member, status=status)
    with pytest.raises(NotEligibleError):
        assert_eligible_for_assessment(member)


def test_a_hand_written_active_status_is_not_evidence_of_payment(member):
    """The gate reads the fee rows, not the status a writer typed.

    A row with `status=ACTIVE` and no receipt is refused. This is the guard against the
    cheapest way to make a demo look right: setting the status instead of recording the
    money the group actually received.
    """
    member.status = Member.Status.ACTIVE
    member.save(update_fields=["status"])
    with pytest.raises(MembershipUnpaidError):
        assert_eligible_for_assessment(member)


def test_an_unrecognised_status_fails_closed(member):
    """`TextChoices` is a Python-side list, not a database constraint (§1.37's family).

    A row can carry a status this code has never heard of — a data load, a hand-run
    UPDATE, a future enum nothing here knows. Passing it would mean *"unknown state, treat
    as eligible"*, which is the one answer that cannot be defended. The member is paid up
    on purpose: without that, the unpaid check would refuse the row anyway and the test
    could not tell the guard from the fall-through.
    """
    member = _paid_up_member(member)
    Member.objects.filter(pk=member.pk).update(status="WOBBLE")
    member.refresh_from_db()
    with pytest.raises(NotEligibleError) as caught:
        assert_eligible_for_assessment(member)
    assert "WOBBLE" in str(caught.value)


# --- The gap that blocks the pilot, asserted rather than remembered ----------


def test_the_two_modules_refuse_with_one_class():
    """`_membership` re-exports `MembershipUnpaidError`; a second definition would break it.

    This session shipped exactly that mistake for a few minutes: the class was copied into
    `_membership.py` while being moved to `_eligibility.py`, so `except
    MembershipUnpaidError` from the fee gate would not have caught the eligibility gate's
    refusal. Identity, not equality, is the assertion that sees it.
    """
    from core.services import _eligibility, _membership

    assert _membership.MembershipUnpaidError is _eligibility.MembershipUnpaidError
    assert issubclass(_membership.NotEligibleError, _eligibility.NotEligibleError)


def test_nothing_in_a_running_instance_records_a_membership_fee():
    """`record_membership_fee`/`_payment` have no caller outside this test tree.

    Verified on the source, in the spirit of `test_no_portal_view_is_over_twenty_lines`:
    there is no view, command or admin action that records the subscription, so every
    applicant stays `APPLICANT` and every member stays unpaid — and `A7`'s gate refuses
    every one of them in a running instance. The gate is correct and the *product* has a
    hole, so the hole is a failing test the day somebody closes it.

    When this fails, the surface exists: delete this test, update `MISSING_FEE_SURFACE`
    in `product/backlog/todo.md`, and check that the surface calls the services instead of
    writing `paid_on` (a `paid_on` written by hand leaves the member `APPLICANT`).
    """
    core = pathlib.Path(__file__).resolve().parents[1]  # .../core
    services = {"record_membership_fee", "record_membership_payment"}
    offenders = []
    for path in sorted(core.rglob("*.py")):
        if "tests" in path.parts or path.name == "_membership.py":
            continue
        # A *call*, parsed rather than pattern-matched: a docstring that names the service
        # in backticks is not a surface (§1.40's lesson — assert the thing you mean).
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in services:
                offenders.append(f"{path.relative_to(core)}:{node.lineno}")
    assert offenders == [], (
        "a surface now records a membership fee — delete this test and update "
        f"todo.md::MISSING_FEE_SURFACE: {offenders}"
    )
