"""pytest fixtures for `core`.

MVP0_PLAN_V2.md §2 does not list this file, but pytest only discovers fixtures
from `conftest.py`, and the plan's A3 tests are written to call `user_factory()`
directly — so a thin adapter from the factories in `factories.py` is required.

Each fixture requests `db`, which is what makes it transactional: a test needs no
`@pytest.mark.django_db` of its own if it uses a factory.
"""

from __future__ import annotations

import pytest

from core.tests.factories import UserFactory


@pytest.fixture
def user_factory(db):
    """Callable so a test can build several users: `user_factory()`. """

    def _make(**kwargs):
        return UserFactory(**kwargs)

    return _make


@pytest.fixture
def user(user_factory):
    """A single role-less public visitor, for tests that need only one."""
    return user_factory()
