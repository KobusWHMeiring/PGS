"""The test harness must be fast without being one import away from production.

Password hashing is the largest fixed cost in a suite that logs users in: Django's PBKDF2
runs at production iterations for *every* `create_user(password=…)` and again for every
`login`. Measured on this repo's fleet (see
`~/.agents/skills/measuring-test-suite-cost/reference.md`): 10–25× on an auth-heavy subset
when the hasher is swapped, on suites that had `--reuse-db` and xdist already.

So the swap is worth having, and it is also the kind of change that must not be able to
reach a deployment. It therefore gets a guard, not a comment:

* the active settings really are fast (a property, not a hasher name);
* the *production* module still declares the slow one — proved in a subprocess with a
  scrubbed environment, because importing `pgs.settings` in-process would read the
  developer's `.env` and prove less;
* pytest is the only thing that loads the test settings module.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_the_active_settings_hash_a_password_in_milliseconds():
    """The property the whole override exists for: a hash must not cost half a second."""
    from django.contrib.auth.hashers import make_password

    start = time.perf_counter()
    make_password("a-throwaway-password")
    elapsed = time.perf_counter() - start

    # Production PBKDF2 (1.2M iterations) takes ~0.3-0.9s on a dev box. 50ms is generous
    # enough for a slow CI runner and still fails if anyone reinstates the real hasher.
    assert elapsed < 0.05, f"one hash took {elapsed * 1000:.0f}ms — the fast hasher is not active"


def test_the_production_settings_do_not_declare_a_hasher_at_all():
    """The override lives in `pgs.settings_test`; `pgs.settings` must not mention one.

    Django's default is production PBKDF2, so the guarantee is *absence*: any
    `PASSWORD_HASHERS` line in the production module is either a weak hasher leaked out of
    the test settings, or a hand-tuned iteration count nobody re-measured. Both are
    regressions, so the assertion is on the module's source, not on a rendered value — the
    value would depend on whichever environment happened to load it.
    """
    production = (REPO_ROOT / "pgs" / "settings.py").read_text(encoding="utf-8")
    assert "PASSWORD_HASHERS" not in production, (
        "pgs/settings.py declares PASSWORD_HASHERS; the fast hasher must stay in "
        "pgs/settings_test.py, and a deployment must keep Django's default"
    )

    test_settings = (REPO_ROOT / "pgs" / "settings_test.py").read_text(encoding="utf-8")
    assert "PASSWORD_HASHERS" in test_settings, "the override moved; the timing test will fail"


def test_only_pytest_loads_the_test_settings_module():
    """`manage.py`, the WSGI app and the deploy gate must all keep using `pgs.settings`."""
    ini = (REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "DJANGO_SETTINGS_MODULE = pgs.settings_test" in ini

    for relative in ("manage.py", "pgs/wsgi.py", "pgs/asgi.py", "scripts/verify.sh"):
        path = REPO_ROOT / relative
        assert path.exists(), relative
        assert "settings_test" not in path.read_text(encoding="utf-8"), (
            f"{relative} loads the test settings; the override must stay inside pytest"
        )


def test_the_fast_lane_exists_and_excludes_the_marked_slow_tests():
    """A documented loop is not a loop. The lane must exist and must deselect `slow`."""
    script = REPO_ROOT / "scripts" / "fast.sh"
    assert script.exists(), "scripts/fast.sh is the documented inner loop"

    body = script.read_text(encoding="utf-8")
    assert "not slow" in body
    assert "--reuse-db" in body, "the loop must not rebuild the schema"

    ini = (REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "slow:" in ini, "the slow marker must be registered (--strict-markers is on)"


def test_the_gate_still_rebuilds_the_schema_and_reports_the_slowest_tests():
    """`--create-db` is cheap here (~1.2s of migrations) and proves migrations apply.

    It belongs in the gate only; the loop reuses. And the gate must report durations, or
    drift has no signal.

    Asserted on the **command line**, not on the file text: both flags are also named in the
    surrounding comments, so a substring check passed with the flag deleted (proved
    2026-10-28 — the same "passes for the wrong reason" shape as testing_hazards §2).
    """
    gate = (REPO_ROOT / "scripts" / "verify.sh").read_text(encoding="utf-8")
    # Non-comment lines only: the flag names appear in the surrounding commentary too, and a
    # regex that takes the first `-m pytest` in the file takes the comment on line 44.
    commands = [line for line in gate.splitlines()
                if re.search(r"-m pytest|^\s*pytest\b", line)
                and not line.lstrip().startswith("#")]
    assert commands, "verify.sh no longer runs pytest"
    runs_pytest = [line for line in commands if "--create-db" in line]
    assert runs_pytest, commands
    assert any(re.search(r"--durations=\d+", line) for line in runs_pytest), runs_pytest
