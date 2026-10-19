"""Celery tasks.

Every task declares `autoretry_for`, `max_retries` and `default_retry_delay`;
`core/tests/test_tasks.py` asserts this over the whole registry rather than trusting
review, because Celery's defaults (`max_retries=3`, delay 180s) make an undeclared
policy invisible at runtime.

**The imports below are load-bearing, not tidiness.** `app.autodiscover_tasks()` (in
`pgs/celery.py`) imports each installed app's `tasks` module — which, for a
*package*, means importing this file and nothing deeper. A task living in
`_maintenance.py` is therefore never registered unless this `__init__` imports it.

The failure mode is silent and total: a worker starts with an empty registry and
discards every queued task it receives, while `/health/` reports
`celery_worker: ok`, because a worker *is* responding — it simply has nothing
registered to run. Verified by running it: importing `pgs.celery` alone yielded
`[]`, and only an incidental import elsewhere made the task appear.

This mirrors `core/models/__init__.py`, which re-exports its slices for the same
class of reason (Django discovers models through it).
"""

from core.tasks._maintenance import heartbeat

__all__ = ["heartbeat"]
