"""Maintenance tasks.

`build_principles.md` §VII.3: every `@shared_task` declares `autoretry_for`,
`max_retries` and `default_retry_delay`, and non-idempotent tasks opt out
**explicitly** with `autoretry_for=()`.

`core/tests/test_tasks.py` enforces that over the whole registry, so a task added
later without a policy fails the build rather than being caught in review — which it
would not be, because Celery's defaults (`max_retries=3`, delay 180s) make a missing
declaration invisible at runtime.
"""

from __future__ import annotations

import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)


@shared_task(name="core.tasks.heartbeat", autoretry_for=(), max_retries=0)
def heartbeat() -> dict[str, str]:
    """Liveness probe. Returns a constant, touches nothing.

    In: none.
    Out: `{"status": "ok"}`.
    Side Effects: one log line. No database access, no external calls — so a
         failure means Celery itself is unwell, not that a dependency is.
    Fails: never deliberately.
    Idempotency: yes, trivially. Running it twice is indistinguishable from once.

    Opts out of retries **explicitly** (`autoretry_for=()`, `max_retries=0`). A
    heartbeat that retried would make a struggling worker look busy while it was
    actually failing, which is the opposite of what a liveness probe is for.
    """
    logger.info("heartbeat")
    return {"status": "ok"}
