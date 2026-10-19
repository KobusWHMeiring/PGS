"""Task A2 — settings come from the environment, and nothing secret is in source.

These are the tests the plan names, plus the three rules from
`build_principles.md` that A2 is the only chance to get right:

* §VI — "Secrets never hardcoded. `.env` via `python-dotenv` is the sole source
  of instance configuration."
* §VIII — "Use a separate Redis database number for cache versus the Celery
  broker." Sharing one is invisible until a cache flush drops queued work.
* §VII — Sentry is present but optional, so a dev box starts without a DSN.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SETTINGS_SOURCE = Path("pgs/settings.py")


def test_required_settings_come_from_env(settings):
    """The plan's first assertion: the DB name and the two media roots are real."""
    assert settings.DATABASES["default"]["NAME"] == "pgs"
    assert settings.PRIVATE_MEDIA_ROOT != settings.MEDIA_ROOT


def test_no_secret_is_literal_in_source():
    """The plan's second assertion — a leaked key is not fixable from the repo."""
    src = SETTINGS_SOURCE.read_text(encoding="utf-8")
    assert "django-insecure" not in src


def test_secret_key_is_required_not_defaulted(monkeypatch):
    """A missing SECRET_KEY must fail loudly, not fall back to a shared constant.

    Two assertions, because either one alone is beatable:

    * the *helper* behaviour, asserted by calling `require_env` directly. This one
      does not cover the wiring — mutating the setting to
      `env("DJANGO_SECRET_KEY", "django-insecure-oops")` leaves `require_env`
      intact and this assertion still passes.
    * the *wiring*, asserted on the source text. No behavioural test can reach
      it: `.env` is located relative to `pgs/settings.py`, not the working
      directory, so a subprocess cannot dodge a developer's local `.env` to
      observe the missing-key path.

    Source assertions are the weaker kind, so they are confined to the one thing
    they are the only way to check, and the expected line is exact.
    """
    from django.core.exceptions import ImproperlyConfigured

    from pgs import settings as pgs_settings

    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    with pytest.raises(ImproperlyConfigured) as exc:
        pgs_settings.require_env("DJANGO_SECRET_KEY")
    # The message must name the variable, or the operator cannot fix it.
    assert "DJANGO_SECRET_KEY" in str(exc.value)

    src = SETTINGS_SOURCE.read_text(encoding="utf-8")
    assert 'SECRET_KEY = require_env("DJANGO_SECRET_KEY")' in src


def test_cache_and_celery_broker_use_different_redis_databases(settings):
    """build_principles §VIII. Asserted on the parsed URLs, not on the raw env."""
    broker_db = settings.CELERY_BROKER_URL.rsplit("/", 1)[-1]
    cache_db = settings.CACHES["default"]["LOCATION"].rsplit("/", 1)[-1]
    assert broker_db != cache_db, "a cache flush must not drop the broker's queue"
    assert settings.CACHES["default"]["BACKEND"].endswith("RedisCache")


def test_allowed_hosts_are_parsed_from_env(monkeypatch, settings):
    """Asserted on the parser, not only on `settings.ALLOWED_HOSTS`.

    Django appends `testserver` to `ALLOWED_HOSTS` for the duration of a test
    run, so a bare `assert settings.ALLOWED_HOSTS` is truthy even when the
    configured list is empty — a test written that way passes no matter how
    wrong the settings are. Hence: test `env_list` directly, and assert on the
    hosts *minus* `testserver`.
    """
    from pgs import settings as pgs_settings

    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", " pgs.example.org ,www.pgs.example.org,, ")
    assert pgs_settings.env_list("DJANGO_ALLOWED_HOSTS") == [
        "pgs.example.org",
        "www.pgs.example.org",
    ]

    # Absent, the call site's default must yield a usable dev list.
    monkeypatch.delenv("DJANGO_ALLOWED_HOSTS", raising=False)
    assert pgs_settings.env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1") == [
        "localhost",
        "127.0.0.1",
    ]

    configured = [h for h in settings.ALLOWED_HOSTS if h != "testserver"]
    assert configured, "a deployment with no hosts rejects every request"


def test_local_apps_and_pgvector_are_installed(settings):
    """`pgvector.django` must be an app so B1's VectorExtension migration can run.

    The app path is `pgvector.django`; the app *label* is `pgvector`, so asserting
    on the bare label fails against correct settings.
    """
    for app in ("core", "knowledge", "pgvector.django"):
        assert app in settings.INSTALLED_APPS, app


def test_sentry_dsn_is_declared_and_optional(settings):
    """Sentry is wired but must not be load-bearing for a dev box without a DSN.

    The stronger guarantee — that the whole settings module imports with nothing
    set but DJANGO_SECRET_KEY — is the subprocess test below.
    """
    assert isinstance(settings.SENTRY_DSN, str)


def test_settings_module_imports_with_only_a_secret_key(tmp_path):
    """Acceptance: `manage.py check` clean with an empty .env bar DJANGO_SECRET_KEY.

    Run in a subprocess with a scrubbed environment so nothing else can rescue a
    hardcoded dependency on another variable. Bounded honestly: a developer's
    local `.env` is still read, so on a machine where `.env` holds extra values
    this proves less than it does in CI, where there is no `.env` at all.
    """
    repo_root = Path(__file__).resolve().parents[2]
    env = {
        "DJANGO_SECRET_KEY": "test-only-key-never-used-outside-this-test",
        "PATH": "",
        "SYSTEMROOT": "C:\\Windows",  # required for Python to start on Windows
    }
    result = subprocess.run(
        [sys.executable, "-c", "import pgs.settings as s; print(len(s.INSTALLED_APPS))"],
        env=env,
        cwd=repo_root,  # so `pgs` is importable regardless of where pytest ran
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
