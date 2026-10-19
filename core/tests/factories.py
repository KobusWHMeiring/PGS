"""factory_boy factories (build_principles.md §VIII).

Test data is built here, not inline in each test, so that a schema change updates
one place. Factories exist for models that tests need repeatedly; they are added
as models arrive rather than pre-emptively.

Note the two-layer pattern: this module holds the *recipes*, and
`core/tests/conftest.py` exposes them as fixtures. pytest only discovers fixtures
from `conftest.py`, so the split is what lets the plan's tests call
`user_factory()` directly.
"""

from __future__ import annotations

from factory import Faker, LazyAttribute, Sequence
from factory.django import DjangoModelFactory

from core.models import Language, User


class UserFactory(DjangoModelFactory):
    """A plain account holding **no roles** — a public visitor (spec §3).

    Deliberately role-less: a factory that quietly granted a role would make
    every capability test pass for the wrong reason.
    """

    class Meta:
        model = User
        # Keeps `UserFactory(username="kobus")` idempotent across calls.
        django_get_or_create = ("username",)

    username = Sequence(lambda n: f"user{n}")
    email = LazyAttribute(lambda o: f"{o.username}@example.org")
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    # Blank rather than null: an absent phone number is "" (no null on strings).
    phone = ""
    preferred_language = Language.EN
