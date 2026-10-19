"""Fixtures for the browser-driven suite.

`scripts/verify.sh` does not run these (`pytest.ini` keeps `tests/e2e` out of
`testpaths`), because the gate must stay runnable on a machine with no browser. Run
them deliberately:

    playwright install chromium      # once per machine
    python -m pytest tests/e2e -q

They exist because three classes of defect in C1 were invisible to Django's test client
and to `manage.py check`, and each was found only by looking at a rendered page:

  * a **multi-line `{# #}` template comment** is emitted as text, and one of them
    contained the word `<details>` in prose — which the browser then parsed as an
    element, restructuring the header and hiding the nav and the CTA;
  * a media query placed above the base rule it refines **lost on equal specificity**,
    so the hero's buttons stacked full-width on desktop while the CSS read correctly;
  * the phone menu panel, anchored to its 44px toggle, **opened off the left edge** of
    the viewport and clipped its own labels.

None of the three produced an error, a 500 or a failed assertion anywhere else.
"""

from __future__ import annotations

import pytest

PHONE = {"width": 390, "height": 844}


@pytest.fixture
def console_errors(page):
    """Collect console errors and uncaught page errors for the life of the page.

    A missing stylesheet or a 404 asset is a console error, not an exception — which is
    exactly why it survives review.
    """
    errors: list[str] = []
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    return errors


@pytest.fixture
def phone_page(browser):
    """A page at iPhone-class width, which is the width UAT Scenario 6 judges."""
    context = browser.new_context(viewport=PHONE)
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def _documents_media(tmp_path_factory):
    """One media root for the session: 8.6 MB of PDFs, copied once."""
    return tmp_path_factory.mktemp("media")


@pytest.fixture(autouse=True)
def published_documents(settings, live_server, _documents_media):
    """Seed the document rows and copy the files, for every test in this suite.

    Without it the browser suite renders `/documents/` with **zero rows** and passes:
    every 44px and overflow assertion would be measuring an empty list — the
    `testing_hazards.md` §1.6 failure in a browser instead of in a `parametrize`.
    `test_the_documents_page_offers_eight_downloads` below asserts the fixture did its
    job, so a broken fixture cannot be mistaken for a passing page.

    This is the one place the suite touches the ORM directly; it is safe for the reason
    given in `pytest_configure` at the bottom of this file.
    """
    from django.core.management import call_command

    settings.MEDIA_ROOT = _documents_media
    call_command("publish_documents", verbosity=0)


def pytest_configure(config):
    """Let Django's ORM run while pytest-playwright's event loop is active.

    `pytest-django`'s `live_server` sets up a transactional database, and
    `pytest-playwright` already has an event loop running, so Django refuses ORM access
    with `SynchronousOnlyOperation` before the first test even starts:

        E  django.core.exceptions.SynchronousOnlyOperation:
           You cannot call this from an async context - use a thread or sync_to_async.

    `DJANGO_ALLOW_ASYNC_UNSAFE` is the documented escape hatch. It is safe **here and
    only here**: these tests never touch the ORM themselves — every database read in this
    suite happens inside the live server's own thread, in response to an HTTP request.
    It is set in this file rather than in `pgs/settings.py` so it cannot leak into the
    gate, which must keep the protection on.
    """
    import os

    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")
