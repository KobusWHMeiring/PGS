"""The `/uat/` console: staff-only, POST-only, and a whitelist that cannot be widened.

Three things must not be true of a page that can seed rows and rebuild artefacts:

* an anonymous visitor can load it (`staff_member_required`);
* a GET — a link, a prefetch, a browser refresh — can run something (`require_POST`);
* a request can name the command it wants (the key is looked up in `ACTIONS`; anything
  else is a 400 before any code runs).

The last one is the reason `test_no_destructive_command_is_exposed` exists: `--force`
re-ingests the corpus, and the guard against a mis-click is that it is not reachable at
all, not that the button looks scary.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from core.models import EscalatedQuery  # noqa: F401  (import cost is a smoke test)
from core.services._uat_console import (
    ACTIONS,
    MANUAL_ONLY,
    links_in,
    run_action,
    uat_for,
)

pytestmark = pytest.mark.django_db

URL = "/uat/"
RUN = "/uat/run/{action}/"


@pytest.fixture
def staff(db):
    return get_user_model().objects.create_user(
        username="uat-staff", password="pw-for-the-console", is_staff=True
    )


@pytest.fixture
def member(db):
    return get_user_model().objects.create_user(username="uat-member", password="pw-for-the-console")


# ------------------------------------------------------------------ who may see it


def test_an_anonymous_visitor_is_sent_to_the_admin_login():
    response = Client().get(URL)

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def test_a_non_staff_member_is_refused(member):
    client = Client()
    client.force_login(member)

    response = client.get(URL)

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def test_the_console_is_not_one_of_the_public_pages():
    """The public sweeps work from `PAGES`; the console must be absent from it on purpose.

    If this fails because someone added `/uat/` to the public route table, the claim
    discipline and Playwright sweeps start treating a staff tool as a page the group
    publishes.
    """
    # The same table the claim-discipline and Playwright sweeps work from.
    from core.tests.test_public import PAGES

    assert all(URL != path for _, path, _ in PAGES)


@pytest.mark.slow  # measured >=0.6s warm: spawns a process (see pytest.ini `slow`)
def test_staff_see_the_preflight_and_one_button_per_action(staff):
    client = Client()
    client.force_login(staff)

    response = client.get(URL)
    body = response.content.decode()

    assert response.status_code == 200
    assert "UAT console" in body
    for row_name in ("corpus present", "corpus embedded", "documents published"):
        assert row_name in body
    for action in ACTIONS:
        assert action.label in body
        assert reverse("core:uat_run", args=[action.key]) in body
    # The destructives are shown with their reason, not as buttons.
    for item in MANUAL_ONLY:
        assert item.label in body
        assert item.reason.split("`")[0][:40] in body


@pytest.mark.slow  # measured >=0.6s warm: spawns a process (see pytest.ini `slow`)
def test_the_page_is_not_indexable(staff):
    client = Client()
    client.force_login(staff)

    body = client.get(URL).content.decode()

    assert 'name="robots" content="noindex, nofollow"' in body


# ------------------------------------------------------------------ how it runs


def test_a_get_cannot_run_an_action(staff):
    client = Client()
    client.force_login(staff)

    response = client.get(RUN.format(action="publish_documents"))

    assert response.status_code == 405


def test_an_unknown_action_is_refused_before_anything_runs(staff):
    client = Client()
    client.force_login(staff)

    response = client.post(RUN.format(action="ingest_standard"))

    assert response.status_code == 400
    assert "unknown UAT action" in response.content.decode()


def test_no_destructive_command_is_reachable(staff):
    """`--force` must be unreachable, not merely unattractive.

    It deletes the document, re-embeds every chunk (API cost, minutes) and detaches every
    historical `ChatMessage` from its evidence. A guard that relies on a button being
    styled as secondary is not a guard.
    """
    keys = {action.key for action in ACTIONS}

    assert "ingest_standard" not in keys
    assert not any("force" in action.command for action in ACTIONS)
    assert any("--force" in item.command for item in MANUAL_ONLY)

    client = Client()
    client.force_login(staff)
    response = client.post(RUN.format(action="ingest_standard_force"))
    assert response.status_code == 400


def test_csrf_is_enforced(staff):
    client = Client(enforce_csrf_checks=True)
    client.force_login(staff)

    response = client.post(RUN.format(action="check"))

    assert response.status_code == 403


@pytest.mark.slow  # measured >=0.6s warm: spawns a process (see pytest.ini `slow`)
def test_a_button_runs_its_command_and_shows_the_output(staff, monkeypatch):
    calls: list[tuple[str, tuple]] = []

    def _fake_call(command, *args, **kwargs):
        calls.append((command, args))
        kwargs["stdout"].write("documents: 8 published")

    monkeypatch.setattr("core.services._uat_console.call_command", _fake_call)

    client = Client()
    client.force_login(staff)
    response = client.post(RUN.format(action="publish_documents"), follow=True)
    body = response.content.decode()

    assert calls == [("publish_documents", ())]
    assert "Publish the documents — done" in body
    assert "documents: 8 published" in body


@pytest.mark.slow  # measured >=0.6s warm: spawns a process (see pytest.ini `slow`)
def test_a_failing_command_reports_instead_of_raising(staff, monkeypatch):
    def _explode(command, *args, **kwargs):
        raise RuntimeError("the database said no")

    monkeypatch.setattr("core.services._uat_console.call_command", _explode)

    client = Client()
    client.force_login(staff)
    response = client.post(RUN.format(action="seed_deployment"), follow=True)
    body = response.content.decode()

    assert response.status_code == 200
    assert "Seed the deployment — failed" in body
    assert "the database said no" in body


def test_the_check_button_runs_the_preflight_and_writes_nothing(staff, monkeypatch):
    monkeypatch.setattr(
        "core.services._uat_console.preflight",
        lambda *a, **k: _Report(),
    )

    outcome = run_action("check")

    assert outcome.ok is True
    assert "preflight: ready" in outcome.output


def test_run_action_refuses_a_key_outside_the_whitelist():
    with pytest.raises(KeyError):
        run_action("rm -rf /")


def _Report():
    from core.services._uat import PreflightReport, PreflightRow

    return PreflightReport(
        rows=(
            PreflightRow(
                name="corpus present",
                command="python manage.py shell -c …",
                expected="366 chunks",
                observed="366 chunks",
                ok=True,
                blocking=True,
            ),
        )
    )


# ------------------------------------------------- which UAT the page prepares
#
# The console used to name one file. It now prepares a **registered** UAT chosen with
# `?uat=<slug>` — a choice among files the code owns, refused when it is anything else, so a
# request still cannot name what gets rebuilt.


def test_the_console_opens_on_the_first_registered_uat(staff):
    client = Client()
    client.force_login(staff)

    body = client.get(URL).content.decode()

    assert uat_for(None).slug in body
    assert 'href="?uat=landscape_tables"' in body, "every registered UAT is offered"


def test_the_console_can_prepare_each_registered_uat(staff):
    client = Client()
    client.force_login(staff)

    body = client.get(URL + "?uat=landscape_tables").content.decode()

    assert "tests/uat/landscape_tables_uat.md" in body
    assert 'name="uat" value="landscape_tables"' in body, "the buttons carry the selection"
    assert "product/design/uat/landscape_tables.html" in body, "the artefact it regenerates"


def test_an_unknown_uat_slug_is_refused_before_the_page_renders(staff):
    client = Client()
    client.force_login(staff)

    response = client.get(URL + "?uat=../../etc/passwd")

    assert response.status_code == 400
    assert b"unknown UAT" in response.content


def test_a_post_naming_an_unknown_uat_runs_nothing(staff, monkeypatch):
    ran: list[str] = []
    monkeypatch.setattr(
        "core.services._uat_console.call_command", lambda *a, **k: ran.append(a[0])
    )

    client = Client()
    client.force_login(staff)
    response = client.post(RUN.format(action="publish_documents"), {"uat": "nope"})

    assert response.status_code == 400
    assert ran == [], "a refused UAT must not reach a command"


@pytest.mark.slow  # measured >=0.6s warm: spawns a process (see pytest.ini `slow`)
def test_rebuild_rebuilds_the_uat_the_page_is_showing(staff, monkeypatch):
    """The button used to rebuild the MVP 0 page whatever the reviewer was reading."""
    seen: list[tuple] = []

    class _Done:
        returncode = 0
        stdout = "wrote: product/design/uat/landscape_tables.html"
        stderr = ""

    def _fake_run(args, **kwargs):
        seen.append(tuple(args))
        return _Done()

    monkeypatch.setattr("core.services._uat_console.subprocess.run", _fake_run)

    client = Client()
    client.force_login(staff)
    client.post(RUN.format(action="regenerate"), {"uat": "landscape_tables"})

    runner = next(args for args in seen if "scripts/uat_runner.py" in args)
    assert "--file" in runner
    assert "tests/uat/landscape_tables_uat.md" in runner, runner


def test_the_page_offers_the_addresses_its_uat_tells_the_reviewer_to_open(staff):
    client = Client()
    client.force_login(staff)

    body = client.get(URL + "?uat=landscape_tables").content.decode()

    for branch in ("establishing-a-pgs-group", "saoso-organic-certification", "pgs-seals-and-their-use"):
        assert branch in body, branch
    assert 'href="/documents/certification-landscape/read/' in body


def test_only_in_site_paths_are_offered_as_links():
    """The list is read from a markdown file, so an external URL must never become a button."""
    links = links_in(uat_for("landscape_tables"))

    assert links, "the UAT names its addresses"
    assert all(link.startswith("/") and not link.startswith("//") for link in links)


def test_uat_for_is_a_registry_and_raises_outside_it():
    assert uat_for(None).slug == uat_for("").slug
    with pytest.raises(KeyError):
        uat_for("mvp9")
