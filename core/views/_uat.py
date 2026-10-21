"""`/uat/` — the console that runs the UAT's setup commands.

Thin by rule (`build_principles.md` §II): authenticate, parse one action key, call one
service, render. Everything the page knows lives in `core/services/_uat_console.py`.

**Staff only, and not a public page.** The console can seed rows and rebuild the artefact,
so an anonymous visitor must never reach it; `staff_member_required` sends them to the
admin login. It is deliberately absent from `core.services._public.PAGES`, which is what
the public sweeps (`test_claim_discipline`, the Playwright route list) work from — so the
absence is not an oversight to fix, and `test_uat_console.py` asserts it.

**POST only for actions.** A GET must not be able to change anything, so every button is a
form with a CSRF token. The action is a *key*, never a command: an unknown key is a 400
before any code runs.
"""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_http_methods

from core.services._uat import preflight
from core.services._uat_console import (
    ACTIONS,
    MANUAL_ONLY,
    database_name,
    run_action,
)

#: `staff_member_required` needs somewhere to send an anonymous visitor, and the admin
#: login is the only login this build has. Passed explicitly rather than adding a
#: `LOGIN_URL` setting for one page.
LOGIN = "/admin/login/"


def _context(outcome=None) -> dict:
    report = preflight()
    return {
        "page": {
            "title": "UAT console — Outeniqua PGS",
            "description": "Staff-only page: prepare and check the instance a UAT reviewer signs.",
        },
        "report": report,
        "actions": ACTIONS,
        "manual_only": MANUAL_ONLY,
        "database": database_name(),
        "outcome": outcome,
    }


@staff_member_required(login_url=LOGIN)
@require_http_methods(["GET"])
def console(request):
    return render(request, "uat/console.html", _context())


@staff_member_required(login_url=LOGIN)
@require_POST
def run(request, action: str):
    try:
        outcome = run_action(action)
    except KeyError:
        # Named, not generic: the console offers a fixed set, so an unknown key means a
        # stale page or a hand-made request, and both deserve a plain 400.
        return HttpResponseBadRequest(f"unknown UAT action: {action!r}")
    return render(request, "uat/console.html", _context(outcome))
