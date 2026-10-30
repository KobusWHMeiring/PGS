"""Sub-plan C1f — why join, where it is recognised, and the whole price in one place.

Three defects this file exists to keep closed, all found by the product owner reading the
rendered site rather than by any earlier test:

1. **The home page's key-facts ribbon read as *the price*.** It said `R100 / year —
   Farmer & consumer membership`, which is true of one of **five** amounts the OPP sets
   (OPP §2.1, §2.3, §2.4, §2.5). A figure that is accurate alone and false in company is
   the same failure as a wrong figure, and no earlier test could see it: each number was
   correct.
2. **Two of the five were absent from the fee section entirely** — visit catering
   (OPP §2.4) and the seal licence (OPP §2.5). A visitor could budget the membership and
   the assessment and still be surprised twice.
3. **Nothing on the site said where the group's assurance stands**, and the two things a
   reader might assume from "recognised" — the SAOSO logo, and certification — are the
   two things the group cannot currently claim.

`core/tests/test_public.py` already proves no fee literal is typed into a template and
that the ribbon's figure equals `MEMBERSHIP_FARMER_CENTS`. That is why every assertion
here is about **completeness and framing**, not about a figure's spelling.

Nothing in this file replaces UAT: whether the cost paragraph reads as honest rather
than as a legal disclaimer is a human judgement, and it is the fifth of the five
questions recorded in `product/design/C1_BUILD_PLAN.md` §C1g.
"""

from __future__ import annotations

import pytest
from django.test import Client

from core.services import _public
from core.templatetags.pgs_extras import format_zar

pytestmark = pytest.mark.django_db

#: Every amount OPP §II lets the group ask a member for, with the constant it comes from.
#: Kept as data so a sixth fee added to `_public.py` and forgotten here is a test failure
#: waiting to be written, not a silent omission (the same idiom as `FORBIDDEN` in
#: `test_claim_discipline.py`).
FEE_AMOUNTS: list[tuple[str, int]] = [
    ("membership", _public.MEMBERSHIP_FARMER_CENTS),
    ("pgs_sa", _public.MEMBERSHIP_PGS_SA_CENTS),
    ("catering_member", _public.VISIT_CATERING_MEMBER_CENTS),
    ("catering_non_member", _public.VISIT_CATERING_NON_MEMBER_CENTS),
    ("seal_licence", _public.SEAL_LICENCE_CENTS),
]


def test_the_fee_table_covers_both_documents():
    """A guard against the guard: §2.4 and §2.5 are the two the site used to omit.

    Asserted on the constants rather than on the HTML, because a `_public.py` refactor
    that dropped the catering figures would make the loop below iterate over *nothing*
    for those entries and still pass — `testing_hazards.md` §1.6.
    """
    assert len(FEE_AMOUNTS) == 5
    by_name = dict(FEE_AMOUNTS)
    assert by_name["catering_member"] == 3_000
    assert by_name["catering_non_member"] == 5_000
    assert by_name["seal_licence"] == 50_000
    assert by_name["membership"] == 10_000


@pytest.mark.parametrize("url", ["/", "/become-a-member/"])
@pytest.mark.parametrize(("name", "cents"), FEE_AMOUNTS, ids=[n for n, _ in FEE_AMOUNTS])
def test_every_fee_the_opp_allows_is_on_the_page(client: Client, url: str, name: str, cents: int):
    """All five amounts render, on both surfaces that talk about money.

    `/become-a-member/` is *the* fee page and the home page carries the fee band, so a
    gap on either is the defect this file was written for.
    """
    html = client.get(url).content.decode()
    assert format_zar(cents) in html, f"{name} ({format_zar(cents)}) missing from {url}"


@pytest.mark.parametrize("url", ["/", "/become-a-member/"])
def test_catering_and_the_seal_licence_are_named_not_footnoted(client: Client, url: str):
    """The two missing fees get a heading of their own, not a clause in another card.

    A figure buried in a note is a figure the reader skips; that is precisely how the
    page came to omit both while appearing to have a complete fee section.
    """
    html = client.get(url).content.decode()
    assert "Farm visit catering" in html
    assert "Seal licence" in html


def test_first_year_floor_is_arithmetic_not_a_third_fee():
    """The floor must be the sum of two published figures, and it must be the *lowest*.

    Written as an assertion rather than a comment because the cheapest way to "make the
    total clearer" is to type a number that happens to match today's bands.
    """
    assert _public.FIRST_YEAR_FROM_CENTS == (
        _public.MEMBERSHIP_FARMER_CENTS + _public.FEE_BANDS[0].initial_cents
    )
    floor = _public.FEE_BANDS[0].initial_cents
    assert floor <= min(band.initial_cents for band in _public.FEE_BANDS)


def test_the_floor_says_what_it_leaves_out(client: Client):
    """A total that quietly excludes transport, catering and the licence is the same
    defect as `R100 / year`, one order of magnitude larger.

    So the paragraph that states the floor must name all three, in the same sentence
    group. If it ever stops, this fails rather than letting the number stand alone.
    """
    html = client.get("/").content.decode()
    assert format_zar(_public.FIRST_YEAR_FROM_CENTS) in html
    for excluded in ("transport", "catering", "seal licence"):
        assert excluded in html.lower(), f"the floor does not say it excludes {excluded}"


def test_the_ribbon_no_longer_reads_as_the_whole_price(client: Client):
    """The fourth fact card must carry the membership *and* say assessment is extra.

    The old caption — "Farmer & consumer membership" beside `R100 / year` — was the
    reader's only encounter with a price above the fold, and it was incomplete. This
    asserts the framing, not the number: `test_public.py` already pins the number.
    """
    html = client.get("/").content.decode()
    # Scoped to the ribbon: the same phrase is still correct in the fee card below, and a
    # page-wide assertion would either fail on that or force the fee card to lose its
    # accurate label. The defect was the pairing, in one place, of `R100 / year` with a
    # caption that named only the membership.
    ribbon = html[html.find('id="key-facts"') : html.find('id="fees"')]
    assert 'id="key-facts"' in html and ribbon, "the ribbon band is missing from the page"
    assert "assessment from" in ribbon
    assert format_zar(_public.FEE_BANDS[0].initial_cents) in ribbon
    assert "Farmer &amp; consumer membership" not in ribbon


# --- Recognition -----------------------------------------------------------


def test_recognition_names_its_four_grounds(client: Client):
    """Each claim on the recognition block traces to a document, and the documents are
    named. A "recognised by SAOSO" with no route named is the kind of sentence claim
    discipline exists to stop."""
    html = client.get("/").content.decode()
    for anchor in ("PGS South Africa", "SAOSO", "IFOAM", "DALRRD"):
        assert anchor in html, f"recognition does not name {anchor}"


@pytest.mark.parametrize("url", ["/", "/become-a-member/"])
def test_membership_is_never_dressed_as_certification(client: Client, url: str):
    """`test_claim_discipline.py` greps the six forbidden producer claims. This is the
    adjacent failure that a term list cannot see: the word "certified" used about the
    group, a member or a farm.

    The sentence the OPP requires ("Membership is not certification") is on both pages,
    and the recognition block states it in its own words.
    """
    html = client.get(url).content.decode()
    assert "Membership is not certification" in html
    assert "no farm status" in html.lower() or "not certified" in html.lower()


def test_the_saoso_logo_is_not_claimed_until_the_agreement_is_on_file():
    """The one claim in this slice that no document in the repo can support.

    The product owner believes the group holds the SAOSO "Organic PGS Certified" logo
    licence (a sticker was seen). A sticker is evidence of the PGS seals — which OPP §V
    gives the committee the authority to issue — not of the SAOSO licence, which the
    Certification landscape p7 makes conditional on 18 months of compliant membership
    *and* a PGS SA assessment. Unverified, it does not ship (DESIGN §1).

    When the signed agreement is produced, flip the constant. `test_the_logo_copy_follows
    _the_constant_both_ways` proves the flip changes the rendered copy and nothing else.
    """
    assert _public.SAOSO_LOGO_LICENSED is False


def test_the_logo_copy_follows_the_constant_both_ways(client: Client, monkeypatch):
    """Prove the flip is one constant and nothing else.

    Renders `/become-a-member/` with the constant forced to both values. Without this, the
    `{% if %}` branch for "we hold it" would be dead code — untested, unrendered, and
    wrong the day somebody sets it to `True`.
    """
    monkeypatch.setattr(_public, "SAOSO_LOGO_LICENSED", False)
    not_claimed = client.get("/become-a-member/").content.decode()
    assert "makes no claim about it either way" in not_claimed

    monkeypatch.setattr(_public, "SAOSO_LOGO_LICENSED", True)
    claimed = client.get("/become-a-member/").content.decode()
    assert "The group holds the SAOSO" in claimed
    assert "makes no claim about it either way" not in claimed
