"""Task C4 — no unsupported certification claim on any public surface.

`MVP0_PLAN_V2.md` C4 and SPEC §12 ("claim discipline"). The rule the OPP imposes on
this group's credibility:

    The public surface may reproduce only the four FORM outcomes and the **active**
    seals. "pasture raised", "GMO free", "biodynamic", "chemical-free" and "spray-free"
    are producer statements, never PGS endorsements. Membership is never implied to be
    certification.

This file is not hypothetical. The live `/endorsed-farms/` page publishes *"their cattle
and sheep with their chickens being **certified pasture raised** on certified organic
pasture, **GMO free**"* today (quoted in `content_inventory.md` §5) — in prose, with no
seal image at all, which is why a grep catches it and an image review would not.

**What this file cannot see, and what therefore stays human:** *tone*. A member list under
a heading like "Our certified farms" overclaims without using a forbidden term. That is
UAT Scenario 8, and no test here replaces it. Read
`tests/uat/mvp0_standards_and_public_site_uat.md` alongside this file.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.test import Client

from core.tests.test_public import PAGES

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(db):
    """The deployed seals, categories and standard set.

    `test_no_seal_is_rendered_at_all` reads the seal labels from the database, so the
    seed has to have run — and asserting that it *did* is the point: with an empty
    `Seal` table the test would iterate over nothing and pass (testing_hazards.md §1.6).
    """
    call_command("seed_deployment")
    return None


PUBLIC_URLS = [url for _, url, _ in PAGES]

#: The six terms the OPP's credibility depends on never being used as a PGS
#: endorsement. `pasture raised` appears twice — with and without the hyphen — because a
#: copy edit that adds the hyphen must not slip past the check.
FORBIDDEN = [
    "pasture raised",
    "pasture-raised",
    "gmo free",
    "gmo-free",
    "biodynamic",
    "chemical-free",
    "spray-free",
]


def test_the_forbidden_list_is_not_empty():
    """A guard against the guard.

    An empty `FORBIDDEN` makes every test below pass vacuously — the exact failure mode
    in `testing_hazards.md` §1.6. Asserted explicitly, because the cheapest way to "fix"
    a failing claim-discipline test is to empty this list.
    """
    assert len(FORBIDDEN) >= 6
    assert all(term == term.lower() for term in FORBIDDEN), "terms are matched lowercased"


@pytest.mark.parametrize("url", PUBLIC_URLS, ids=[u.strip("/") or "home" for u in PUBLIC_URLS])
def test_no_unsupported_claim(client: Client, url: str):
    html = client.get(url).content.decode().lower()
    for term in FORBIDDEN:
        assert term not in html, f"{term!r} appears on {url}"


@pytest.mark.parametrize("url", PUBLIC_URLS, ids=[u.strip("/") or "home" for u in PUBLIC_URLS])
def test_no_seal_is_rendered_at_all(client: Client, seeded, url: str):
    """MVP 0 publishes **no** seal (`MVP0_PRD` §3), active or otherwise.

    Asserted against the database rather than against a hardcoded list, because seals are
    data (§4.8): a group that seeds a new seal must not accidentally publish it. The
    inactive pasture-raised seal is the specific case D11 forbids — *"an inactive seal is
    never rendered on a public page"* — and this test would catch it being rendered by
    name, whatever the markup.
    """
    from core.models import Seal

    labels = [seal.label for seal in Seal.objects.all()]
    assert labels, "seed_deployment has not run — this test would otherwise prove nothing"

    html = client.get(url).content.decode()
    for label in labels:
        assert label.lower() not in html.lower(), f"seal {label!r} rendered on {url}"


@pytest.mark.parametrize("url", PUBLIC_URLS, ids=[u.strip("/") or "home" for u in PUBLIC_URLS])
def test_no_implied_certification_in_a_link(client: Client, url: str):
    """No link offers a certificate, a farm status or a verification page.

    There is no registry in MVP 0, so any such link would be a promise the deployment
    cannot keep — and it would be the first half of an overclaim.
    """
    html = client.get(url).content.decode().lower()
    for href in ("/certificate", "/verify/", "/registry", "/endorsed-farms", "/farm-status"):
        assert href not in html, f"{url} links to {href}, which does not exist in MVP 0"


def test_pending_documents_are_not_links(client: Client):
    """"Publishing soon" must not be clickable.

    DESIGN rule 8: unresolved data is a visible chip, never a plausible-looking fake. A
    chip that is an `<a>` is a button that does nothing, which is how a reader concludes
    the site is broken — or worse, that the document exists.
    """
    html = client.get("/").content.decode()
    assert "Publishing soon" in html

    for chunk in html.split("Publishing soon")[:-1]:
        opening = chunk.rsplit("<", 1)[-1]
        assert not opening.startswith("a "), "a pending document is rendered as a link"
