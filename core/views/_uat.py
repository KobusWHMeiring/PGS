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
    links_in,
    run_action,
    uat_files,
    uat_for,
)

#: `staff_member_required` needs somewhere to send an anonymous visitor, and the admin
#: login is the only login this build has. Passed explicitly rather than adding a
#: `LOGIN_URL` setting for one page.
LOGIN = "/admin/login/"


def _context(outcome=None, uat=None) -> dict:
    selected = uat or uat_for(None)
    report = preflight()

    def rendered(commands):
        """Each command with the selected UAT's file in it, so the page shows what will run."""
        return tuple(
            {"item": item, "command": item.command.replace("{uat}", selected.path)}
            for item in commands
        )

    return {
        "page": {
            "title": "UAT console — Outeniqua PGS",
            "description": "Staff-only page: prepare and check the instance a UAT reviewer signs.",
        },
        "report": report,
        "actions": rendered(ACTIONS),
        "manual_only": rendered(MANUAL_ONLY),
        "database": database_name(),
        "outcome": outcome,
        "uats": uat_files(),
        "uat": selected,
        "links": links_in(selected),
        "artefact": f"product/design/uat/{selected.slug}.html",
    }


@staff_member_required(login_url=LOGIN)
@require_http_methods(["GET"])
def console(request):
    """The console for one UAT, chosen with `?uat=<slug>` — a **choice among registered
    files**, never a path. An unknown slug is a 400 rather than a guess, for the same reason
    an unknown action key is."""
    try:
        selected = uat_for(request.GET.get("uat") or None)
    except KeyError:
        return HttpResponseBadRequest(
            f"unknown UAT: {request.GET.get('uat')!r}"
        )
    return render(request, "uat/console.html", _context(uat=selected))


@staff_member_required(login_url=LOGIN)
@require_POST
def run(request, action: str):
    try:
        selected = uat_for(request.POST.get("uat") or None)
    except KeyError:
        return HttpResponseBadRequest(f"unknown UAT: {request.POST.get('uat')!r}")
    try:
        outcome = run_action(action, selected)
    except KeyError:
        # Named, not generic: the console offers a fixed set, so an unknown key means a
        # stale page or a hand-made request, and both deserve a plain 400.
        return HttpResponseBadRequest(f"unknown UAT action: {action!r}")
    return render(request, "uat/console.html", _context(outcome, selected))
