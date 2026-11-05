"""The farmer portal — the application flow's pages (spec §7, task A6).

Thin views (`build_principles.md` §II): parse, call one service, render. Everything that
could be wrong — whether an account may exist, which step may be reached, what the fee
band is — is in `core.services._application`, `_membership` and `_fees`. If a view here
grows a branch about money or status, the rule is in the wrong layer.

The step order is enforced **server-side**, by `_step`. A guarded step reached too early
redirects to `core:apply`, which re-reads the database and lands the applicant on the
first thing they have not done — so a refreshed tab, a bookmarked URL and a stale back
button all resolve to the same honest answer instead of a half-filled later step.

The pages are public *routes* with a login requirement on the steps after the account:
a farmer must be able to read what applying involves before creating anything.
"""

from __future__ import annotations

from functools import wraps

from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from core.forms._application import (
    AccountForm,
    CategoriesForm,
    PledgeForm,
    SignInForm,
    TurnoverForm,
)
from core.models import AssessmentFee, ConsentPurpose, ConsentText, Pledge
from core.services._application import (
    ApplicationError,
    StepOutOfOrderError,
    application_farm,
    application_progress,
    assert_step_ready,
    record_application_categories,
)
from core.services._membership import (
    FeeScheduleNotSeededError,
    PledgeDeclarationError,
    WitnessRequiredError,
    declare_assessment_fee,
)
from core.services._public import Page, chrome_context

#: Where each step lives. Views hold routes; services hold rules — a service that knew
#: URL names would be a service you cannot call from a task.
STEP_URLS: dict[str, str] = {
    "account": "core:apply",
    "pledge": "core:apply_pledge",
    "categories": "core:apply_categories",
    "turnover": "core:apply_turnover",
}
SUMMARY_URL = "core:apply_summary"

APPLY_PAGES: dict[str, Page] = {
    "account": Page(
        key="apply",
        title="Create an account to apply — Outeniqua PGS",
        description=(
            "Start an application: an account keeps your details, your farm and your "
            "answers in one place. It is not an application on its own."
        ),
        eyebrow="Applying for membership",
        heading="Create an account",
        lede=(
            "An account keeps your details in one place, so you do not retype them and the "
            "group has one record to work from. It is not an application yet, and it "
            "carries no declaration."
        ),
    ),
    "pledge": Page(
        key="apply_pledge",
        title="The farmer pledge — Outeniqua PGS",
        description="The member pledge from the group's Principles, Policies and Procedures.",
        eyebrow="Step 2 of 4",
        heading="The farmer pledge",
        lede=(
            "This is the pledge printed in the group's Principles, Policies and Procedures. "
            "Read it as it is written: it is what a visit is measured against."
        ),
    ),
    "categories": Page(
        key="apply_categories",
        title="What you want assessed — Outeniqua PGS",
        description="The categories an application covers, one assessment each.",
        eyebrow="Step 3 of 4",
        heading="What do you want assessed?",
        lede=(
            "Each category is assessed in its own right, on its own questionnaire. The "
            "tick you make here is the application — nothing is applied for by accident."
        ),
    ),
    "turnover": Page(
        key="apply_turnover",
        title="Your turnover and the assessment fee — Outeniqua PGS",
        description=(
            "Turnover is self-declared and peer-reviewed; the assessment fee follows the "
            "group's published sliding scale."
        ),
        eyebrow="Step 4 of 4",
        heading="Your annual turnover",
        lede=(
            "The assessment fee follows a sliding scale the members approve each year. You "
            "declare a turnover; the scale decides the band, and the group reviews it."
        ),
    ),
    "summary": Page(
        key="apply_summary",
        title="Your application — Outeniqua PGS",
        description="What you have declared, what is owed, and what happens next.",
        eyebrow="Application",
        heading="Your part is done",
        lede=(
            "Here is what the group now has, and what happens next. Nothing is confirmed "
            "until the group has spoken to you."
        ),
    ),
}


def _next_step_url(member) -> str:
    """The first step still open, or the summary when none is."""
    key = next((step.key for step in application_progress(member) if not step.done), None)
    return STEP_URLS[key] if key else SUMMARY_URL


def _context(request, page_key: str, current: str, **extra) -> dict:
    """Chrome + the step rail, so no view assembles presentation twice."""
    member = getattr(request.user, "member", None)
    return chrome_context(APPLY_PAGES[page_key]) | {
        "steps": application_progress(member) if member else (),
        "current": current,
    } | extra


def _step(key: str):
    """Require a signed-in applicant and every earlier step (server-side, not by URL)."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            member = getattr(request.user, "member", None)
            if member is None:
                return redirect("core:home")
            try:
                assert_step_ready(member, key)
            except StepOutOfOrderError:
                return redirect("core:apply")
            return view(request, member, *args, **kwargs)

        return wrapper

    return decorator


def _account_context(request, form, consent) -> dict:
    return _context(
        request, "account", "account", form=form, consent=consent,
        email_verification_available=False,
    )


def apply(request):
    member = getattr(request.user, "member", None) if request.user.is_authenticated else None
    if member is not None:
        return redirect(_next_step_url(member))
    if request.user.is_authenticated:
        return redirect("core:home")
    consent = ConsentText.objects.current(ConsentPurpose.ACCOUNT)
    form = AccountForm(
        request.POST or None, initial={"consent_version": consent.version if consent else ""}
    )
    if request.method == "POST" and form.is_valid():
        try:
            member = form.create()
        except ApplicationError as exc:
            form.add_error(None, str(exc))
        else:
            auth_login(request, member.user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect(_next_step_url(member))
    return render(request, "portal/apply_account.html", _account_context(request, form, consent))


@_step("pledge")
def apply_pledge(request, member):
    # A signature is history: a second POST must not append a second pledge to the same
    # application. The step is done, so the applicant is sent forward — not offered the
    # form again, which would silently duplicate an attestation (build_principles §I).
    if member.pledges.filter(kind=Pledge.Kind.FARMER).exists():
        return redirect(_next_step_url(member))
    form = PledgeForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.record(member)
        except (PledgeDeclarationError, WitnessRequiredError) as exc:
            form.add_error(None, str(exc))
        else:
            return redirect(_next_step_url(member))
    return render(
        request,
        "portal/apply_pledge.html",
        _context(request, "pledge", "pledge", form=form, farm=application_farm(member), member=member),
    )


@_step("categories")
def apply_categories(request, member):
    form = CategoriesForm(request.POST or None, farm=application_farm(member))
    if request.method == "POST" and form.is_valid():
        record_application_categories(
            member, category_ids=form.cleaned_data["categories"].values_list("pk", flat=True)
        )
        return redirect(_next_step_url(member))
    return render(
        request, "portal/apply_categories.html", _context(request, "categories", "categories", form=form)
    )


@_step("turnover")
def apply_turnover(request, member):
    form = TurnoverForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            declare_assessment_fee(
                member,
                application_farm(member),
                declared_turnover_cents=form.cents(),
                kind=AssessmentFee.Kind.INITIAL,
            )
        except FeeScheduleNotSeededError as exc:
            form.add_error(None, str(exc))
        else:
            return redirect(_next_step_url(member))
    return render(request, "portal/apply_turnover.html", _context(request, "turnover", "turnover", form=form))


@login_required
def apply_summary(request):
    member = getattr(request.user, "member", None)
    if member is None:
        return redirect("core:home")
    if any(not step.done for step in application_progress(member)):
        return redirect(_next_step_url(member))
    farm = application_farm(member)
    fee = AssessmentFee.objects.filter(member=member, farm=farm).order_by("-id").first()
    return render(
        request,
        "portal/apply_summary.html",
        _context(request, "summary", "", member=member, farm=farm, fee=fee),
    )


def login(request):
    """The way back in. 1a has no mail provider (D84), so a password is the only route."""
    return LoginView.as_view(
        template_name="portal/login.html",
        authentication_form=SignInForm,
        redirect_authenticated_user=True,
        extra_context=chrome_context(APPLY_PAGES["account"]) | {"steps": (), "current": ""},
    )(request)


def logout(request):
    return LogoutView.as_view(next_page="core:home")(request)
