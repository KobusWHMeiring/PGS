"""Settings for the pytest run only. Never imported by `manage.py`, WSGI or a deploy.

**Why:** Django's default PBKDF2 runs at production iterations for every
`create_user(password=…)`, and `client.login()` hashes again. On an auth-heavy suite that is
the single largest fixed cost — measured at 10–25× on a 41-test subset of a sibling repo
(`~/.agents/skills/measuring-test-suite-cost/reference.md`). In this repo it was 12–15s of a
~60s warm suite: every user a test creates pays it twice over.

**Why a separate module rather than an autouse fixture:** a fixture would re-apply settings
per test (invisible to `--co`, easy to forget in a new root conftest), and it would need a
`settings` fixture in every conftest that has users. One module, named by `pytest.ini`, is
one place to read and one place to guard. `tests/tools/test_test_harness.py` fails if
`pgs/settings.py` ever mentions a hasher, or if anything but pytest loads this module.

Test passwords are throwaway strings; nothing here protects a credential.
"""

from __future__ import annotations

from pgs.settings import *  # noqa: F401,F403

# MD5 rather than a 1-iteration PBKDF2: it is the only hasher Django ships that is not
# deliberately slow, and the value here is "fast and obviously not production".
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
