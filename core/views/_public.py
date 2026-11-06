"""The public pages — home, the three "who we are" pages, joining, and contact.

Thin views (`build_principles.md` §II): parse nothing, call one service, render.
Every string, figure and route a template needs comes from
`core.services._public.public_context`, so a page cannot disagree with another page
about the membership fee, and no template holds business logic.

MVP 0 ships these as public preview pages (D21) — the registry, farm status and
certificates are MVP 2 and are deliberately absent (DESIGN §1, `MVP0_PRD` §3).
"""

from __future__ import annotations

from django.contrib.auth import login as auth_login
from django.shortcuts import redirect, render

from core.forms._application import AccountForm
from core.forms._selfcheck import SelfCheckAnswersForm
from core.models import ConsentPurpose, ConsentText
from core.services._application import ApplicationError
from core.services._board import board_context
from core.services._chat_guard import client_ip_hash
from core.services._documents import documents_context
from core.services._public import public_context
from core.services._selfcheck import (
    RateLimitedError,
    SelfCheckError,
    build_check,
    check_submit_budget,
    evaluate,
    submit,
)


def home(request):
    # The home page carries the documents band, so it needs the same list the
    # documents page renders — from one service, in the order the seed declares.
    return render(request, "public/home.html", public_context("home") | documents_context())


def organics(request):
    return render(request, "public/organics.html", public_context("organics"))


def how_it_works(request):
    return render(request, "public/how_it_works.html", public_context("how_it_works"))


def members(request):
    return render(request, "public/members.html", public_context("members"))


def become_a_member(request):
    return render(request, "public/become_a_member.html", public_context("become_a_member"))


def building(request):
    # The board is a generated artefact (`core/services/_board_data.py`), not a query and not
    # a read of `product/backlog/`: this view touches no database, so a PRD edit cannot change
    # the public site between deploys (D74b).
    return render(request, "public/building.html", public_context("building") | board_context())


def contact(request):
    return render(request, "public/contact.html", public_context("contact"))


TEMPLATE = "public/before_you_apply.html"


def before_you_apply(request):
    """The public self-check (A8, D71): parse, call one service, render (`SELF_CHECK_PRD` §4.3).

    Two POSTs share the route and neither is a second page: the check itself, and the optional
    account at the end. The account is **A6's** — `AccountForm` calls `create_application()` — so
    this route cannot grow a second registration with different rules, and it writes no
    `FarmCategory` row: a category tick is not an application, and A6's categories step makes those.
    """
    check = build_check()
    context = public_context("before_you_apply") | {
        "check": check,
        "account_consent": ConsentText.objects.current(ConsentPurpose.ACCOUNT),
        "account_form": AccountForm(),
        "template_name": TEMPLATE,
    }
    if request.method != "POST":
        return render(request, TEMPLATE, context | {"form": SelfCheckAnswersForm(check=check)})
    if request.POST.get("step") == "account":
        return _save_details(request, context)
    form = SelfCheckAnswersForm(request.POST, check=check)
    if not form.is_valid():
        return render(request, TEMPLATE, context | {"form": form})
    try:
        check_submit_budget(client_ip_hash(request))
    except RateLimitedError as exc:
        return render(
            request,
            TEMPLATE,
            context | {"form": form, "retry_after": exc.retry_after},
            status=429,
        )
    try:
        report = None if form.is_bot else _submit(form, check)
    except (SelfCheckError, ApplicationError) as exc:
        # A refused consent is a sentence on the page, never a 500 (§3.6).
        form.add_error(None, str(exc))
        return render(request, TEMPLATE, context | {"form": form})
    return render(
        request,
        TEMPLATE,
        context
        | {
            "form": form,
            "result": evaluate(form.cleaned_data, check=check),
            "stored": report is not None,
        },
    )


def _submit(form: SelfCheckAnswersForm, check):
    """Hand the act to the service, with the two consents as acts and the version on screen."""
    return submit(
        form.cleaned_data,
        research_consent=bool(form.cleaned_data.get("research_consent")),
        demographic_consent=bool(form.cleaned_data.get("demographic_consent")),
        demographic=form.cleaned_data,
        check=check,
    )


def _save_details(request, context):
    """The optional account at the end of the flow — A6's form and A6's service, verbatim."""
    form = AccountForm(request.POST)
    if form.is_valid():
        try:
            member = form.create()
        except ApplicationError as exc:
            form.add_error(None, str(exc))
        else:
            auth_login(request, member.user, backend="django.contrib.auth.backends.ModelBackend")
            # A6's `/apply/` resumes at the first open step: the pledge, not the account.
            return redirect("core:apply")
    return render(request, TEMPLATE, context | {"account_form": form, "account_open": True})
