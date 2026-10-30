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

import re

import pytest
from django.core.management import call_command
from django.test import Client

from core.services._public import FORBIDDEN_CLAIMS
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
#: endorsement. The list itself is **canonical in `core/services/_public.py`**, because the
#: board generator (`scripts/board.py`) must refuse a publishable summary containing one of
#: them before it can reach a page — two copies that agree today are two copies that
#: disagree the day one is edited.
FORBIDDEN = list(FORBIDDEN_CLAIMS)


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


# --- The reader: quoting a document is not making a claim -------------------


#: Routes that reproduce a document's own words. They are exempt from the term sweep, and they
#: are not exempt in spirit: the sweep asks whether *the group* makes an unsupported claim, and
#: a quotation is not a claim. Every entry names its reason, and
#: `test_the_exemption_is_necessary` proves the exemption is load-bearing rather than a
#: convenience. Measured on the shipped PDFs, not assumed:
#:
#:     pdftotext pgs_docs/saoso-version-2.1-2026.pdf - | grep -ic biodynamic   → 5
#:     pdftotext "pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf" - \
#:         | grep -ic "pasture.raised"                                          → 3
VERBATIM_ROUTES: dict[str, str] = {
    "/documents/saoso-standard-v2.1/read/": (
        "SAOSO v2.1 prints 'biodynamic' five times and the OPP prints 'pasture raised'. Both "
        "are in FORBIDDEN. Reproducing a standard is not endorsing it — and a reader checking "
        "a quotation must be able to see the document's own words."
    ),
}


@pytest.fixture
def ingested_saoso(public_surface):
    """The corpus document behind the published `/documents/saoso-standard-v2.1/` row.

    `public_surface` has already run `seed_deployment` and `publish_documents`, so the public
    row exists with a repo-relative `source_path`. This fixture adds the ingested twin whose
    `source_file` matches it — the join the reader resolves — and one passage that uses the
    word the sweep forbids.
    """
    from knowledge.models import DocumentChunk, StandardDocument, StandardSet

    corpus = StandardSet.objects.get(is_default=True)
    document = StandardDocument.objects.get_or_create(
        standard_set=corpus,
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        defaults={
            "kind": StandardDocument.Kind.STANDARD,
            "issuing_body": "SAOSO",
            "title": "SAOSO Standard for Organic Production and Processing",
            "version": "2.1",
            "sha256": "b" * 64,
            "section_scheme": "saoso",
        },
    )[0]
    DocumentChunk.objects.create(
        document=document,
        section_ref="S5.6.1",
        heading_path="LIVESTOCK > Biodynamic preparations",
        page=31,
        text=(
            "Biodynamic preparations may be used where they are produced from substances "
            "listed in Appendix 2."
        ),
    )
    return document


def test_the_exemption_list_has_a_reason_per_route():
    """A guard against the guard: an empty exemption list exempts nothing and hides why."""
    assert VERBATIM_ROUTES, "an empty exemption list is a list that exempts nothing"
    assert all(reason.strip() for reason in VERBATIM_ROUTES.values())
    for url in VERBATIM_ROUTES:
        assert url not in PUBLIC_URLS, (
            f"{url} is exempt *and* swept — the exemption would be doing nothing, and the "
            "sweep would fail on the document's own words"
        )


def test_the_exemption_is_necessary(client: Client, ingested_saoso):
    """Prove the guard can fail: the reader *does* render a forbidden term.

    Without this, the exemption is indistinguishable from a route that happens to be clean,
    and the next person deletes it without noticing what it protected.
    """
    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode().lower()
    assert "biodynamic" in body, "the fixture passage is missing, so this proves nothing"


def test_the_reader_adds_no_claim_of_its_own(client: Client, ingested_saoso):
    """Strip the document's words; sweep what is left — the group's own copy.

    This is the half of the sweep the exemption must not lose. The head, the search box, the
    contents list and the provenance line are the group speaking, and none of them may make a
    certification claim or render a seal.
    """
    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode().lower()
    our_words = re.sub(r'<article class="passage".*?</article>', "", body, flags=re.S)
    our_words = re.sub(r'<p class="reader__hit-text">.*?</p>', "", our_words, flags=re.S)

    for term in FORBIDDEN:
        assert term not in our_words, f"{term!r} appears in the reader's own copy"

    from core.models import Seal

    for label in Seal.objects.values_list("label", flat=True):
        assert label.lower() not in our_words, f"seal {label!r} rendered on the reader"


@pytest.fixture
def published_answer(public_surface, django_user_model):
    """A published card whose *quoted clause* uses a forbidden term.

    The same rule as the reader, on a different surface: the answer page reproduces the
    document's own words in its clause block, and those words may include "biodynamic" or
    "pasture raised". The page is therefore not in `PUBLIC_URLS` either — it is a row, not a
    route — and the sweep below is applied to everything *except* the quotation.
    """
    from django.utils import timezone

    from core.models import PublicQuestion
    from core.services._ask import approve

    user = django_user_model.objects.create_user(username="claims-reviewer", password="x")
    card = PublicQuestion.objects.create(
        question="May I use preparations I make myself?",
        asked_key="k-claims",
        answer=(
            "The standard permits them only where their ingredients are listed in Appendix 2. "
            "The preparation's name does not make it permitted; its ingredients do."
        ),
        topic="Inputs",
        citations=[
            {
                "section_ref": "S5.6.1",
                "sub_ref": None,
                "page": 31,
                "document": "SAOSO Standard v2.1",
                "quote": "Biodynamic preparations may be used where they are produced from "
                "substances listed in Appendix 2.",
                "chunk_id": 1,
                "document_code": "saoso-standard-v2.1",
                "reading_anchor": "s5-6-1",
            }
        ],
        last_asked_at=timezone.now(),
    )
    return approve(card.pk, user=user, topic="Inputs")


def test_quoting_a_document_on_an_answer_page_is_not_a_claim(
    client: Client, published_answer
):
    """Prove the answer page's quotation really does trip the term list.

    Without this, the strip below could pass because the fixture never contained a forbidden
    term — the guard-the-guard shape in `testing_hazards.md` §1.6.
    """
    body = client.get(f"/ask/{published_answer.slug}/").content.decode().lower()
    assert "biodynamic" in body


def test_the_answer_page_makes_no_claim_of_its_own(client: Client, published_answer):
    """The group's copy and the reviewed answer prose are swept; the clause is not.

    The answer text *is* something the group stands behind at a permanent URL (D65), so it is
    swept. The blockquote is the document speaking, so it is not — and stripping it is what
    makes this test able to fail on a real overclaim instead of failing on the standard's own
    vocabulary.
    """
    body = client.get(f"/ask/{published_answer.slug}/").content.decode().lower()
    our_words = re.sub(r'<blockquote class="answer__quote">.*?</blockquote>', "", body, flags=re.S)
    our_words = re.sub(r'<p class="answer__cite".*?</p>', "", our_words, flags=re.S)

    for term in FORBIDDEN + UNSOURCED:
        assert term not in our_words, f"{term!r} appears on a published answer page"
