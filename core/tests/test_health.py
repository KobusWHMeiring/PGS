"""Task A5 — `/health/`.

`build_principles.md` §VII.1: "/health/ verifies DB (SELECT 1), Redis (PING), Celery
broker, and Celery worker liveness. Returns JSON; any failed dependency returns HTTP
503."

The trap this file exists to catch is that **broker liveness is not worker
liveness**. Redis answers `PING` perfectly well with zero Celery workers consuming
from it, so a health check that only pings the broker reports a healthy system while
every background task sits in a queue that nobody drains. `celery_worker` therefore
uses `app.control.ping()`, which returns `[]` when no worker responds, and the two
checks are asserted to be independent.

Second trap: §VII.2 — "A hung external call blocks a Celery worker indefinitely."
A health check that hangs is worse than one that fails, because the load balancer
never learns anything. Every external call below declares an explicit timeout, and
there is a test that the timeouts are actually passed rather than defaulted.

Readiness, not liveness: a dead worker returns 503 even though the web process can
still serve pages. That is the specified behaviour and it is correct for a load
balancer deciding whether to send traffic — but it means a dev box with no worker
running reports unhealthy, which is honest rather than convenient.
"""

from __future__ import annotations

import inspect

import pytest
from django.test import Client

from core.services import _health
from core.views import _health as health_view

pytestmark = pytest.mark.django_db

URL = "/health/"


@pytest.fixture
def all_up(monkeypatch):
    """Every dependency healthy. Worker ping is patched because CI runs no worker."""

    def fake_ping(*args, **kwargs):
        return [{"celery@test": {"ok": "pong"}}]

    monkeypatch.setattr(_health.celery_app.control, "ping", fake_ping)
    return None


# --- The happy path ---------------------------------------------------------


def test_health_ok_when_all_dependencies_up(client: Client, all_up):
    response = client.get(URL)
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {
        "db": "ok",
        "redis": "ok",
        "celery_broker": "ok",
        "celery_worker": "ok",
    }


def test_health_returns_json(client: Client, all_up):
    response = client.get(URL)
    assert response["Content-Type"].startswith("application/json")


def test_health_is_never_cached(client: Client, all_up):
    """A cached health response is a lie with a timestamp on it.

    Proxies and browsers must not serve a stale `ok` for a system that has since
    lost Redis.
    """
    response = client.get(URL)
    cache_control = response.get("Cache-Control", "")
    assert "no-store" in cache_control or "no-cache" in cache_control


def test_health_needs_no_authentication(client: Client, all_up):
    """A load balancer has no session. Requiring auth makes the check useless."""
    assert client.get(URL).status_code == 200


# --- Failure paths: each dependency fails independently ---------------------


def test_health_503_when_redis_is_down(client: Client, all_up, monkeypatch):
    """The plan's named test: 503 when Redis is down (client raises).

    Patched at `redis.from_url`, not at `_redis_ping`: replacing the check function
    would bypass its own error handling and prove nothing about the code under test.
    Patching the client exercises the real `except` path.
    """

    def boom(*args, **kwargs):
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr(_health.redis, "from_url", boom)

    response = client.get(URL)
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["checks"]["redis"] == "error"
    # The other checks still ran and are still reported — a health check that
    # stops at the first failure hides how many things are wrong.
    assert body["checks"]["db"] == "ok"


def test_health_503_when_db_is_down(client: Client, all_up, monkeypatch):
    """Patched at the cursor, so `_check_db`'s own `except` is what runs."""

    def boom(*args, **kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(_health.connection, "cursor", boom)

    response = client.get(URL)
    assert response.status_code == 503
    assert response.json()["checks"]["db"] == "error"


def test_health_503_when_no_celery_worker_responds(client: Client, monkeypatch):
    """Broker up, worker down — the failure a broker-only check cannot see.

    This is the whole reason `celery_worker` exists as a separate check. The broker
    pings fine here; only the worker is missing.
    """
    monkeypatch.setattr(_health.celery_app.control, "ping", lambda *a, **k: [])

    response = client.get(URL)
    assert response.status_code == 503

    body = response.json()
    assert body["checks"]["celery_broker"] == "ok"
    assert body["checks"]["celery_worker"] == "error"


def test_worker_check_does_not_merely_repeat_the_broker_check(all_up, monkeypatch):
    """Pinned as a property of the service, not just of the view."""
    assert _health.check_health().checks["celery_worker"] == "ok"

    monkeypatch.setattr(_health.celery_app.control, "ping", lambda *a, **k: [])
    report = _health.check_health()
    assert report.checks["celery_worker"] == "error"
    assert report.checks["celery_broker"] == "ok"


def test_health_503_when_worker_ping_raises(client: Client, monkeypatch):
    """A broker that refuses the connection raises rather than returning []."""

    def boom(*args, **kwargs):
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(_health.celery_app.control, "ping", boom)

    response = client.get(URL)
    assert response.status_code == 503
    assert response.json()["checks"]["celery_worker"] == "error"


# --- Explicit timeouts (§VII.2) --------------------------------------------


def test_every_redis_ping_declares_a_timeout():
    """A health check that hangs teaches the load balancer nothing."""
    src = inspect.getsource(_health._redis_ping)
    assert "socket_connect_timeout" in src
    assert "socket_timeout" in src


def test_worker_ping_declares_a_timeout():
    src = inspect.getsource(_health._check_celery_worker)
    assert "timeout" in src
    # And it must be bounded, not merely mentioned.
    assert "WORKER_PING_TIMEOUT" in src


def test_timeouts_are_short_enough_to_be_useful():
    """A health check slower than a load balancer's own timeout never reports.

    One second per dependency is the budget: anything longer and the probe is
    killed before it answers, so a slow dependency looks identical to a dead one.
    """
    assert _health.WORKER_PING_TIMEOUT <= 2.0
    assert _health.REDIS_TIMEOUT <= 2.0


# --- It must not leak the deployment's secrets ------------------------------


def test_health_does_not_leak_credentials_or_dsns(client: Client, all_up, settings):
    """`/health/` is reachable unauthenticated, so it must not echo config.

    A DSN contains the database password; a traceback contains paths and versions.
    Neither belongs in a public JSON body.
    """
    body = client.get(URL).content.decode()
    assert settings.DATABASES["default"].get("PASSWORD", "x") not in body
    assert settings.CELERY_BROKER_URL not in body
    assert "Traceback" not in body


def test_failure_detail_is_not_exposed_by_default(client: Client, all_up, monkeypatch):
    """The reason a dependency failed is logged, not published.

    Exception text can name hosts, ports and users. `DEBUG=False` must keep it out
    of the response while still reporting *which* check failed.
    """

    def boom(*args, **kwargs):
        raise ConnectionError("redis://user:secret@internal-host:6379 refused")

    monkeypatch.setattr(_health.redis, "from_url", boom)
    body = client.get(URL).content.decode()

    assert "internal-host" not in body
    assert "secret" not in body
    assert "redis" in body  # the check name is still reported


# --- Shape and structure ----------------------------------------------------


@pytest.mark.slow  # measured >=0.6s warm: spawns a process (see pytest.ini `slow`)
def test_report_is_an_immutable_dataclass():
    """§II: compound return values are `@dataclass(frozen=True)`."""
    report = _health.check_health()
    assert hasattr(report, "checks")
    with pytest.raises(Exception):
        report.status = "mutated"  # type: ignore[misc]


def test_view_is_thin(client: Client, all_up):
    """§II: a view may parse a request, call one service, and return a response.

    Asserted on the source rather than trusted, because a "temporary" query in a
    view is how the service layer erodes.
    """
    src = inspect.getsource(health_view.health)
    code_lines = [
        line
        for line in src.splitlines()
        if line.strip() and not line.strip().startswith(("#", '"""', "'''"))
    ]
    assert len(code_lines) <= 20, f"view is {len(code_lines)} lines:\n{src}"
