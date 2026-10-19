"""Task A6 — Celery, and a retry-policy rule that actually enforces something.

`build_principles.md` §VII.3: "Every `@shared_task` declares `autoretry_for`,
`max_retries`, `default_retry_delay`. Non-idempotent tasks opt out explicitly with
`autoretry_for=()`."

The plan proposes this meta-test:

    assert task.autoretry_for is not None or task.max_retries == 0

**It does not work**, and it fails in the least helpful way available. Probed
against Celery 5.6:

    @shared_task
    def naked(): pass

    hasattr(naked_task, "autoretry_for")   -> False
    naked_task.max_retries                 -> 3     (Celery's default)
    naked_task.default_retry_delay         -> 180   (Celery's default)

`autoretry_for` is **not an attribute at all** unless the task declares it, so
`task.autoretry_for is not None` raises `AttributeError` rather than asserting. The
task it is meant to catch is the one that crashes the test with a traceback pointing
at Celery internals instead of at the missing decorator argument.

There is a second flaw: `or task.max_retries == 0` accepts a task with no
`autoretry_for` and `max_retries=0` — but §VII.3 requires the opt-out to be *explicit*,
`autoretry_for=()`. A task that "opts out" by leaving `autoretry_for` unset has not
opted out; it has simply never declared anything, and nobody can tell the difference
between a considered decision and an oversight.

So the rule is restated here as a pure function, `retry_policy_violations()`, and
tested two ways: against synthetic tasks that must be rejected, and against the real
registry. A meta-test that cannot fail is decoration.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from celery import shared_task

from core.tasks._maintenance import heartbeat
from core.tests.policy_rules import retry_policy_violations

REPO_ROOT = Path(__file__).resolve().parents[2]


def _registry_report() -> dict:
    """Inspect the real task registry the way a worker does.

    Deliberately mimics worker startup rather than calling `finalize()` alone:
    `app.autodiscover_tasks()` defers discovery into Celery's `_pending_tasks`, which
    is flushed by `loader.import_default_modules()` — the call a `WorkController`
    makes after `django.setup()`. Probing with `finalize()` alone returns `[]` for a
    perfectly healthy project, which is a misleading green.

    Out: `{"violations": [...], "tasks": [...]}`.
    Fails: AssertionError carrying the subprocess's stderr if it failed — a broken
        probe must never read as a clean registry.
    """
    snippet = (
        "import django, json, os\n"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pgs.settings')\n"
        "django.setup()\n"
        # Only the rule module and the project app. Importing `core.tests.test_tasks`
        # here would pull in `core.tasks._maintenance` as a side effect and mask the
        # very bug this probe exists to catch — which is exactly what an earlier
        # version of this function did.
        "from core.tests.policy_rules import retry_policy_violations\n"
        "from pgs.celery import app\n"
        "app.loader.import_default_modules()\n"
        "app.finalize()\n"
        "print(json.dumps({\n"
        "    'violations': retry_policy_violations(app.tasks),\n"
        "    'tasks': sorted(app.tasks),\n"
        "}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


# --- The rule itself must be able to fail -----------------------------------


def test_rule_rejects_a_task_that_declares_nothing():
    """The exact case the plan's test crashes on, here rejected with a clear message."""

    @shared_task(name="probe.naked")
    def naked():
        pass

    violations = retry_policy_violations([("probe.naked", naked)])
    assert len(violations) == 1
    assert "autoretry_for" in violations[0]


def test_rule_accepts_an_explicit_opt_out():
    @shared_task(name="probe.opted_out", autoretry_for=(), max_retries=0)
    def opted_out():
        pass

    assert retry_policy_violations([("probe.opted_out", opted_out)]) == []


def test_rule_rejects_a_contradictory_opt_out():
    """`autoretry_for=()` with max_retries=3 is a task that will retry nothing but
    claims otherwise."""

    @shared_task(name="probe.contradictory", autoretry_for=(), max_retries=3)
    def contradictory():
        pass

    violations = retry_policy_violations([("probe.contradictory", contradictory)])
    assert len(violations) == 1
    assert "max_retries=0" in violations[0]


def test_rule_rejects_retries_that_can_never_happen():
    """A non-empty `autoretry_for` with `max_retries=0` is a dead configuration:
    it reads as retrying and never does."""

    @shared_task(
        name="probe.dead", autoretry_for=(ValueError,), max_retries=0, default_retry_delay=10
    )
    def dead():
        pass

    violations = retry_policy_violations([("probe.dead", dead)])
    assert len(violations) == 1
    assert "never actually retries" in violations[0]


def test_rule_rejects_a_retry_with_no_delay():
    @shared_task(
        name="probe.nodelay", autoretry_for=(ValueError,), max_retries=3, default_retry_delay=0
    )
    def nodelay():
        pass

    violations = retry_policy_violations([("probe.nodelay", nodelay)])
    assert len(violations) == 1
    assert "default_retry_delay" in violations[0]


def test_rule_accepts_a_well_formed_policy():
    @shared_task(
        name="probe.good", autoretry_for=(ValueError,), max_retries=3, default_retry_delay=30
    )
    def good():
        pass

    assert retry_policy_violations([("probe.good", good)]) == []


# --- The real registry (the plan's named test, corrected) -------------------


def test_every_task_declares_a_retry_policy():
    """§VII.3 over every task registered in this project.

    Run in a **fresh interpreter**, not in-process. Celery's task registry is
    populated on `app.finalize()` and is not reliably isolated between apps within
    one process: probing showed a task decorated onto a throwaway app appearing in
    the default app's registry, and `app._tasks` being empty until finalize. A
    subprocess sidesteps the question and is the more faithful check anyway — it is
    exactly what a freshly started worker sees.
    """
    report = _registry_report()
    assert report["violations"] == [], "retry policy violations:\n" + "\n".join(
        report["violations"]
    )


def test_the_heartbeat_task_exists():
    """A6's acceptance: a `heartbeat` task exists in a real worker's registry."""
    assert "core.tasks.heartbeat" in _registry_report()["tasks"]


def test_autodiscovery_alone_registers_tasks():
    """The real-worker case: importing `pgs.celery` and nothing else.

    This is the test that would have caught the empty-registry bug. The earlier
    version of `test_every_task_declares_a_retry_policy` imported the test module,
    which imported `core.tasks._maintenance` as a side effect, so the registry
    looked populated while a real worker had none.

    Concretely: `autodiscover_tasks()` imports each app's `tasks` module, which for
    a package means `core/tasks/__init__.py` only. A task in `_maintenance.py` is
    invisible unless that `__init__` imports it — and a worker with an empty
    registry discards every queued task while still answering pings.
    """
    report = _registry_report()
    assert "core.tasks.heartbeat" in report["tasks"], (
        "importing pgs.celery alone did not register the heartbeat task, so a real "
        "worker would start with an empty registry and discard every queued task. "
        f"Registered: {report['tasks']}"
    )


def test_no_probe_tasks_leak_into_the_real_registry():
    """Guards the guard.

    If the probe tasks defined above ever reached the real registry, the meta-test
    would be inspecting the wrong thing and passing for the wrong reason.
    """
    leaked = [n for n in _registry_report()["tasks"] if n.startswith("probe.")]
    assert leaked == [], f"test tasks leaked into the project registry: {leaked}"


def test_heartbeat_opts_out_of_retries_explicitly():
    """A liveness probe that retries is a probe that reports its own backoff.

    Retrying a heartbeat would make a worker look busy while it is actually
    failing, so it opts out — explicitly, with `autoretry_for=()`, per §VII.3.
    """
    assert heartbeat.autoretry_for == ()
    assert heartbeat.max_retries == 0


def test_heartbeat_is_idempotent():
    """Running it twice must be indistinguishable from running it once."""
    assert heartbeat() == heartbeat()


# --- One Celery app, not two ------------------------------------------------


def test_project_celery_app_reads_settings(settings):
    """`pgs/celery.py` must configure from Django settings, not from literals."""
    from pgs.celery import app as project_app

    assert project_app.conf.broker_url == settings.CELERY_BROKER_URL
    assert project_app.conf.result_backend == settings.CELERY_RESULT_BACKEND


def test_celery_app_is_importable_from_the_project_package():
    """`pgs/__init__.py` must export it, or `celery -A pgs` and the worker's
    `@shared_task` registry disagree about which app is current."""
    import pgs

    assert hasattr(pgs, "celery_app")


def test_health_check_uses_the_project_app_not_a_second_one():
    """A5 built a stopgap Celery app inside the health service; A6 retires it.

    Two apps would mean `/health/` reports on a broker connection the worker does
    not use — a check that can pass while the real deployment is broken.
    """
    from core.services import _health
    from pgs.celery import app as project_app

    assert _health.celery_app is project_app


def test_tasks_are_namespaced_by_module():
    """Bare task names collide silently between apps when they share a worker."""
    for name in _registry_report()["tasks"]:
        if name.startswith("celery."):
            continue
        assert "." in name, f"{name} is not namespaced"
