"""The §VII.3 retry-policy rule, as a pure function.

Lives in its own module — **not** in `test_tasks.py` — because the meta-test that
applies it must be able to import the rule *without* importing any task module.
That distinction is the whole point: an earlier version of this test imported
`test_tasks`, which imports `core.tasks._maintenance` as a side effect, so the
registry appeared correctly populated even when `pgs.celery` alone registered
nothing. The test passed for the wrong reason, and a real worker had an empty
registry.

So this module imports nothing from `core.tasks`.
"""

from __future__ import annotations


def retry_policy_violations(tasks) -> list[str]:
    """Return one message per task that does not declare a usable retry policy.

    In:  `tasks` — a mapping of {name: task} or an iterable of (name, task) pairs.
    Out: human-readable violations; empty means compliant.
    Side Effects: none.
    Fails: never.

    The rule, stated precisely, because the plan's version of it is ambiguous and
    crashes on the case it exists to catch:

    * `autoretry_for` must be **declared** — present as an attribute. Absent is a
      violation, because it cannot be distinguished from an oversight.
    * `autoretry_for=()` is an **explicit opt-out**, and then `max_retries` must be
      0. Anything else is contradictory.
    * Otherwise `autoretry_for` must be a non-empty tuple of exceptions **and** the
      retries must be able to happen: `max_retries > 0`, `default_retry_delay > 0`.
      A non-empty `autoretry_for` with `max_retries=0` silently never retries.

    Celery's defaults make all of this invisible at runtime: a task that declares
    nothing still has `max_retries=3` and `default_retry_delay=180`, and only lacks
    the `autoretry_for` attribute altogether.
    """
    pairs = tasks.items() if hasattr(tasks, "items") else tasks
    violations: list[str] = []

    for name, task in pairs:
        if name.startswith("celery."):
            continue

        if not hasattr(task, "autoretry_for"):
            violations.append(
                f"{name}: does not declare `autoretry_for`. Declare the retry policy "
                f"or opt out explicitly with `autoretry_for=()`. (Celery defaults it "
                f"to absent, with max_retries=3 and delay=180s, so the omission is "
                f"invisible at runtime.)"
            )
            continue

        autoretry_for = task.autoretry_for
        if autoretry_for == ():
            if getattr(task, "max_retries", None) != 0:
                violations.append(
                    f"{name}: opts out with `autoretry_for=()` but sets "
                    f"max_retries={task.max_retries!r}; an explicit opt-out must "
                    f"also set max_retries=0."
                )
            continue

        if not isinstance(autoretry_for, tuple) or not autoretry_for:
            violations.append(
                f"{name}: autoretry_for={autoretry_for!r} is not a tuple of exceptions."
            )
            continue

        if not getattr(task, "max_retries", 0):
            violations.append(
                f"{name}: declares autoretry_for={autoretry_for!r} but max_retries="
                f"{task.max_retries!r}, so it never actually retries."
            )
        if not getattr(task, "default_retry_delay", 0):
            violations.append(
                f"{name}: declares autoretry_for={autoretry_for!r} but "
                f"default_retry_delay={task.default_retry_delay!r}."
            )

    return violations
