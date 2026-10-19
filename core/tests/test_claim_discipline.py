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
def seeded(db, public_surface):
    """The deployed seals, categories and standard set.

    `test_no_seal_is_rendered_at_all` reads the seal labels from the database, so the
    seed has to have run — and asserting that it *did* is the point: with an empty
    `Seal` table the test would iterate over nothing and pass (testing_hazards.md §1.6).

    `public_surface` (below) is applied here too, because a seal label can appear on a
    *document row* as readily as in prose.
    """
    return None


@pytest.fixture(scope="session")
def _media_root(tmp_path_factory):
    return tmp_path_factory.mktemp("media")


@pytest.fixture(autouse=True)
def public_surface(settings, _media_root):
    """Seed the deployment **and publish the document files**, for every test here.

    Without this fixture `/documents/` renders zero rows, so the claim and refusal
    sweeps below asserted nothing at all about the eight titles and notes the group
    publishes — a mutation that added `Publishing soon` back into a document row left
    all 36 tests green. That is testing_hazards.md §1.6 with a database behind it: the
    page exists, so the URL looks covered, and the rows do not, so it is not.
    """
    settings.MEDIA_ROOT = _media_root
    call_command("seed_deployment")
    call_command("publish_documents", verbosity=0)


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


#: Claims the *live* site makes that the governed documents do not support. Each is a
#: content decision, not a design one, so each needs the product owner's word before it
#: appears — and once refused, this list is what stops it coming back with the next copy
#: paste from the WordPress site.
#:
#: `february` — `/become-a-member/` on the live site says membership fees are "payable by
#: the end of February" each year. `pdftotext -layout` over the OPP contains no month name
#: at all; §2.3 says only "Fees are payable prior to the farm assessment visit." Struck by
#: the product owner 2026-10-19 (`C1_BUILD_PLAN.md` §6 #7).
UNSOURCED = ["february"]


@pytest.mark.parametrize("url", PUBLIC_URLS, ids=[u.strip("/") or "home" for u in PUBLIC_URLS])
def test_no_unsourced_claim(client: Client, url: str):
    """A refused claim must not reappear on any public route.

    Same shape as `test_no_unsupported_claim`, and the same mutation test applies: put
    "by the end of February" back into `become_a_member.html` and this must go red.
    """
    assert UNSOURCED, "an empty list makes this test pass vacuously (testing_hazards.md §1.6)"
    html = client.get(url).content.decode().lower()
    for term in UNSOURCED:
        assert term not in html, f"{term!r} is refused but appears on {url}"


@pytest.mark.parametrize("url", PUBLIC_URLS, ids=[u.strip("/") or "home" for u in PUBLIC_URLS])
def test_nothing_is_pending_on_a_public_route(client: Client, url: str):
    """No `Publishing soon` chip survives C2 — and, if one returns, it is not a link.

    This replaces C4's `test_pending_documents_are_not_links`, which asserted the chip
    was present and unclickable. C2 published the documents, so the chip's absence is
    now the invariant; the original rule (DESIGN rule 8: *unresolved data is a tinted
    chip, never a plausible-looking fake*) is kept for anything that becomes pending
    again, by keeping the second half of the check.

    Mutation-tested both ways: re-adding a chip fails the first assertion, and making
    that chip an `<a>` fails the second.
    """
    html = client.get(url).content.decode()
    for chunk in html.split("Publishing soon")[:-1]:
        opening = chunk.rsplit("<", 1)[-1]
        assert not opening.startswith("a "), "a pending item is rendered as a link"

    assert "Publishing soon" not in html, (
        f"{url} still claims something is 'Publishing soon' — C2 published every "
        "document in `core/services/_documents.DOCUMENTS`"
    )
