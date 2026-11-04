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

from factory import Faker, LazyAttribute, Sequence, SubFactory
from factory.django import DjangoModelFactory

from core.models import (
    Category,
    Farm,
    FarmAlias,
    FarmCategory,
    FarmContact,
    Language,
    Member,
    User,
)


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


class CategoryFactory(DjangoModelFactory):
    """A seeded category. Codes/titles are group data, so the factory makes its own
    unique code rather than borrowing a deployed one."""

    class Meta:
        model = Category

    code = Sequence(lambda n: f"CAT{n}")
    label = LazyAttribute(lambda o: f"Category {o.code}")
    standard_ref = ""


class MemberFactory(DjangoModelFactory):
    """An account that holds a membership record.

    `membership_no` is left blank on purpose: it is generated in `Member.save()`
    (D39), so the factory must not pre-empt the rule it is meant to exercise.
    """

    class Meta:
        model = Member

    user = SubFactory(UserFactory)
    status = Member.Status.APPLICANT


class FarmFactory(DjangoModelFactory):
    """A farm with no catchment, no PostGIS field and a generated public uuid."""

    class Meta:
        model = Farm

    member = SubFactory(MemberFactory)
    name = Sequence(lambda n: f"Farm {n}")
    nearest_town = "Rheenendal"


class FarmAliasFactory(DjangoModelFactory):
    class Meta:
        model = FarmAlias

    farm = SubFactory(FarmFactory)
    name = Sequence(lambda n: f"Old Name {n}")
    source = "live site"


class FarmCategoryFactory(DjangoModelFactory):
    class Meta:
        model = FarmCategory

    farm = SubFactory(FarmFactory)
    category = SubFactory(CategoryFactory)
    status = FarmCategory.Status.APPLIED


class FarmContactFactory(DjangoModelFactory):
    class Meta:
        model = FarmContact

    farm = SubFactory(FarmFactory)
    name = Faker("name")
    role = "HOSTING"
