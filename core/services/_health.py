"""Health checks — `build_principles.md` §VII.1.

Four dependencies, checked independently: the database, Redis, the Celery broker,
and Celery **worker liveness**. The last two are not the same check and must never
be collapsed into one.

    Redis answers `PING` perfectly well with zero Celery workers consuming from it.
    A health check that only pings the broker reports a healthy system while every
    background task sits in a queue nobody drains.

So `celery_broker` is a Redis `PING`, and `celery_worker` is `app.control.ping()`,
which returns `[]` when no worker responds.

Three properties are deliberate and each has a test:

* **Every external call declares an explicit timeout** (§VII.2). A health check that
  hangs is worse than one that fails: the load balancer's own timeout fires first,
  so a slow dependency and a dead one become indistinguishable. The budget is ~1s
  per dependency.
* **All four checks always run**, even after one fails. Stopping at the first
  failure hides how many things are wrong, which is the question an operator is
  actually asking at 3 a.m.
* **The report never carries credentials or exception text.** `/health/` is
  unauthenticated by necessity — a load balancer has no session — so a DSN, a
  password, or a traceback naming internal hosts must not appear in the body. The
  detail goes to the log; the response says only *which* check failed.

Readiness, not liveness: a dead worker returns 503 even though the web process can
still serve pages. That is what §VII.1 specifies and what a load balancer needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import redis
import structlog
from django.conf import settings
from django.db import connection

# One Celery app for the project (A6). A5 built a local stopgap app from
# CELERY_BROKER_URL because `pgs/celery.py` did not exist yet; two apps would mean
# this check reports on a broker connection the worker does not use, so it could say
# `celery_worker: ok` while the real worker was dead. Imported from the project app
# now that A6 exists.
from pgs.celery import app as celery_app

logger = structlog.get_logger(__name__)

# Budget: short enough that the probe answers before a load balancer gives up.
REDIS_TIMEOUT = 1.0
WORKER_PING_TIMEOUT = 1.0

Status = Literal["ok", "error"]


@dataclass(frozen=True)
class HealthReport:
    """The result of one health probe. Frozen: a report is a fact, not a draft."""

    status: Status
    checks: dict[str, Status]

    @property
    def is_ok(self) -> bool:
        return self.status == "ok"


def _check_db() -> Status:
    """`SELECT 1` — the cheapest proof the connection is usable, not merely open."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        # Never `except: pass` (§VII.5): log with context and report the failure.
        logger.exception("health.db.failed")
        return "error"
    return "ok"


def _redis_ping() -> Status:
    """Ping the **cache** Redis, with both timeouts explicit.

    `socket_connect_timeout` bounds establishing the connection and
    `socket_timeout` bounds the reply. Without both, a black-holed host blocks the
    worker until the OS gives up, which can be minutes.
    """
    try:
        client = redis.from_url(
            settings.CACHES["default"]["LOCATION"],
            socket_connect_timeout=REDIS_TIMEOUT,
            socket_timeout=REDIS_TIMEOUT,
        )
        client.ping()
    except Exception:
        logger.exception("health.redis.failed")
        return "error"
    return "ok"


def _check_celery_broker() -> Status:
    """The broker is reachable. Says nothing about whether anything consumes it."""
    try:
        client = redis.from_url(
            settings.CELERY_BROKER_URL,
            socket_connect_timeout=REDIS_TIMEOUT,
            socket_timeout=REDIS_TIMEOUT,
        )
        client.ping()
    except Exception:
        logger.exception("health.celery_broker.failed")
        return "error"
    return "ok"


def _check_celery_worker() -> Status:
    """At least one worker answers a broadcast ping within the timeout.

    `control.ping()` returns a list of responding workers — `[]` when none reply,
    which is the case a broker check cannot distinguish from healthy. The timeout is
    passed explicitly so a broker that accepts the publish but never delivers cannot
    hang the probe.
    """
    try:
        replies = celery_app.control.ping(timeout=WORKER_PING_TIMEOUT)
    except Exception:
        logger.exception("health.celery_worker.failed")
        return "error"

    if not replies:
        # Not an exception — an absent worker is a normal state, and it must be
        # logged at warning rather than error so a dev box does not page anyone.
        logger.warning("health.celery_worker.no_workers_responded")
        return "error"
    return "ok"


def check_health() -> HealthReport:
    """Probe every dependency and report.

    In: none.
    Out: `HealthReport(status, checks)` — `status` is `"ok"` only if every check is.
    Side Effects: opens and closes short-lived connections; logs failures.
    Fails: never — a failing dependency is reported, not raised, because the caller
         is a load balancer that needs an answer either way.
    """
    checks: dict[str, Status] = {
        "db": _check_db(),
        "redis": _redis_ping(),
        "celery_broker": _check_celery_broker(),
        "celery_worker": _check_celery_worker(),
    }
    status: Status = "ok" if all(v == "ok" for v in checks.values()) else "error"

    if status == "error":
        # Names only. The detail is already in the log; the log line is the thing
        # an operator can act on, and it is not served to the internet.
        logger.error("health.degraded", failed=[k for k, v in checks.items() if v != "ok"])

    return HealthReport(status=status, checks=checks)
