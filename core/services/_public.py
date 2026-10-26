"""Content for the public site — every page's title, heading and figures in one place.

Two rules from `build_principles.md` meet here:

* **§II — no logic in templates.** A template displays; it does not hold a fee
  figure, a page title or a route table. Everything a template needs arrives in the
  context, and money arrives as integer cents (§III) to be formatted at the boundary
  by `pgs_extras.format_zar`.
* **§I — code encodes the process; data encodes the standard and the group.** The
  fee schedule below is transcribed from **OPP §2.1 and §2.3**, which the group's
  AGM approved. It is a constant rather than a model because MVP 0 has no
  `MembershipFee` rows to read it from and a fee schedule is not per-farm data; MVP 1
  replaces it with `AssessmentFee` rows keyed by `turnover_band` (D29).

**Provenance of every figure here:** `pgs_docs/Outeniqua pgs principles, policies and
procedures 2026.pdf`, §2.1 (R100 farmer & consumer; R500 PGS South Africa) and §2.3
(the six turnover bands, initial and renewal). Verified with `pdftotext -layout`, not
against the design prototype — the prototype happens to agree, which is not the same
as being the source of truth. If these numbers ever change, they change in the OPP
first.

`section_ref` strings (`§2.3`, `S20.1.1`) follow D43: the citation as a human reads
it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple


class NavLink(NamedTuple):
    """One header/footer link. `route` is a URLConf name, never a path."""

    label: str
    route: str


#: The header's links. `Become a member` is the CTA button and is deliberately not
#: in this tuple (DESIGN §7.1: nav is links plus one button). `Ask` was added on
#: 2026-10-20 at the product owner's request; the header must still hold one line at
#: 768 px and up, which `tests/e2e/test_public_site.py` measures.
#: `Documents` joins in C2 — and it joins *with* its route, because a link to a route
#: that does not exist raises `NoReverseMatch` at render time, so it cannot be added
#: early "temporarily".
NAV: tuple[NavLink, ...] = (
    NavLink("Organics", "core:organics"),
    NavLink("How it works", "core:how_it_works"),
    NavLink("Members", "core:members"),
    NavLink("Documents", "core:documents"),
    NavLink("Ask", "core:ask"),
    NavLink("Contact", "core:contact"),
)


class FeeBand(NamedTuple):
    """One row of OPP §2.3, in integer cents (build_principles.md §III).

    `label` is the turnover range as the OPP prints it. The band is *declared* by
    the farmer and never computed by this application (§III, "Declared, not
    computed"), which is why nothing here maps a turnover figure to a band.
    """

    label: str
    initial_cents: int
    renewal_cents: int


#: OPP §2.1 — the annual membership fee for a farmer or consumer member.
MEMBERSHIP_FARMER_CENTS = 10_000  # R100

#: OPP §2.1 — what the group pays PGS South Africa annually, funded from the above.
MEMBERSHIP_PGS_SA_CENTS = 50_000  # R500

#: OPP §2.3 — the assessment sliding scale, initial certification and renewal.
#: The order is the OPP's, and the labels are its own wording.
FEE_BANDS: tuple[FeeBand, ...] = (
    FeeBand("Below R250 000", 150_000, 90_000),
    FeeBand("R250 001 – R500 000", 250_000, 200_000),
    FeeBand("R500 001 – R1 000 000", 300_000, 250_000),
    FeeBand("R1 000 001 – R2 500 000", 370_000, 320_000),
    FeeBand("R2 500 001 – R5 000 000", 500_000, 500_000),
    FeeBand("Above R5 000 000", 800_000, 800_000),
)


@dataclass(frozen=True)
class Page:
    """One public page's metadata.

    `heading` + `heading_accent` are the `h1` split into the two lines the design
    sets (the second line in italic ochre — DESIGN §7.2). One source for the `h1`
    whether the page draws a hero or a plain page head.
    """

    key: str
    title: str
    description: str
    eyebrow: str
    heading: str
    heading_accent: str = ""
    lede: str = ""

    @property
    def h1(self) -> str:
        """The `h1` as a single string, for tests and for `<title>` fallbacks."""
        return f"{self.heading} {self.heading_accent}".strip()


PAGES: dict[str, Page] = {
    "home": Page(
        key="home",
        title="Outeniqua PGS — organic assurance built by farmers, for farmers",
        description=(
            "A Participatory Guarantee System of farmer and consumer members along the "
            "Outeniqua mountain range, assessing organic practice against SAOSO v2.1."
        ),
        eyebrow="Participatory Guarantee System · Western Cape",
        heading="Organic assurance built by",
        heading_accent="farmers, for farmers.",
        lede=(
            "We are a locally focused quality assurance group. Members assess one another "
            "against the SAOSO organic standard, on each other's farms, in the open — built "
            "on trust, social networks and knowledge exchange, not a distant inspector."
        ),
    ),
    "organics": Page(
        key="organics",
        title="What organic means here — Outeniqua PGS",
        description=(
            "The four principles of organic agriculture, the six basic elements of a "
            "Participatory Guarantee System, and how first-, second- and third-party "
            "assurance differ."
        ),
        eyebrow="Organics",
        heading="Organic agriculture, and what a PGS adds",
        lede=(
            "“Organic agriculture is a production system that sustains the health of soils, "
            "ecosystems and people. It relies on ecological processes, biodiversity and cycles "
            "adapted to local conditions, rather than the use of inputs with adverse effects.” "
            "— the IFOAM–Organics International definition, which SAOSO adopts in full."
        ),
    ),
    "how_it_works": Page(
        key="how_it_works",
        title="How membership and assessment work — Outeniqua PGS",
        description=(
            "Six steps from applying to a recorded decision, the composition of a farm visit "
            "team, and what a visit produces."
        ),
        eyebrow="Membership procedure",
        heading="How it works",
        lede=(
            "Every prospective farmer and producer member follows the same path, in the same "
            "order. It is set out in the group's Principles, Policies and Procedures."
        ),
    ),
    "members": Page(
        key="members",
        title="Members — Outeniqua PGS",
        description=(
            "Who belongs to the group: farmer and producer members, consumer members, and "
            "retailer and market members. Membership is not certification."
        ),
        eyebrow="Members",
        heading="Who is in the group",
        lede=(
            "Any farmer growing food organically along the Outeniqua mountain range — roughly "
            "from Mossel Bay to the Crags — is welcome to apply."
        ),
    ),
    "documents": Page(
        key="documents",
        title="Documents — Outeniqua PGS",
        description=(
            "The four documents the group assesses against, the farm visit preparation "
            "list and the blank participant checklists, at addresses you can bookmark "
            "and cite."
        ),
        eyebrow="Documents",
        heading="What we publish,",
        heading_accent="and what we do not.",
        lede=(
            "Four governed documents set out the standard, our own procedures and the "
            "wider certification landscape. The rest are the working forms a farm visit "
            "uses. Farm visit reports and application dossiers are never published: they "
            "contain a farmer's personal information."
        ),
    ),
    "become_a_member": Page(
        key="become_a_member",
        title="Become a member — Outeniqua PGS",
        description=(
            "Membership fees and the assessment fee schedule, set on a cost-recovery basis "
            "and approved by the members at the annual general meeting."
        ),
        eyebrow="Join",
        heading="What membership and assessment cost",
        lede=(
            "Fees are set on a cost-recovery basis and approved by the members at the annual "
            "general meeting. The assessment fee reflects the scale and commercial intensity "
            "of the farm."
        ),
    ),
    "ask": Page(
        key="ask",
        title="Ask the standard — Outeniqua PGS",
        description=(
            "Ask a question about the SAOSO standard, the Outeniqua PGS procedures, the "
            "Basic Production Principles or the certification landscape. Every answer "
            "cites the passage it came from, or says plainly that it cannot."
        ),
        # The eyebrow names the surface, not the page: with a one-line `h1`, an
        # eyebrow reading "Ask the standard" directly above it printed the same
        # words twice, which reads as a broken template rather than as hierarchy.
        eyebrow="The assistant",
        heading="Ask the standard",
        # The page is the window, so the head band is one line of invitation and no
        # more. The four-sentence explainer that used to live here said what the aside
        # beside the window already says, in less room and further from the thing it
        # describes — and it pushed the composer below the fold on a laptop.
        lede="Ask any question about the organic standards. Answers from the documents only.",
    ),
    "contact": Page(
        key="contact",
        title="Contact — Outeniqua PGS",
        description=(
            "How to reach the Outeniqua PGS administrator and committee, and how the group is "
            "governed."
        ),
        eyebrow="Contact",
        heading="Who to talk to",
        lede=(
            "The group is run by its members. The administrator coordinates visits and "
            "records; the committee reviews every assessment and records the decision."
        ),
    ),
}


def chrome_context(page: Page) -> dict:
    """The chrome for a page whose `Page` is built per request.

    `/ask/<slug>/` and `/documents/<code>/read/` have no entry in `PAGES` — they are rows,
    not routes — but they still need the nav, the footer and the fee figures every public
    page reads. Passing a `Page` instance keeps one shape for `base.html`'s `og:` tags.
    """
    return {
        "page": page,
        "nav": NAV,
        "pages": PAGES,
        "membership_farmer_cents": MEMBERSHIP_FARMER_CENTS,
        "membership_pgs_sa_cents": MEMBERSHIP_PGS_SA_CENTS,
        "fee_bands": FEE_BANDS,
    }


def public_context(page_key: str) -> dict:
    """The context every public template is rendered with.

    In:      a key in `PAGES`.
    Out:     a plain dict — `page`, `nav`, `pages` (all pages, for the footer and the
             CTA), and the fee figures as integer cents.
    Side effects: none.
    Fails:   `KeyError` on an unknown key. Deliberately loud: a typo in a view must
             not render a blank page that still returns 200.

    The fee figures ride along on every page because the key-facts ribbon on the home
    page and the fee table on `/become-a-member/` must never disagree — they read the
    same constant, and `core/tests/test_public.py` asserts that.
    """
    return chrome_context(PAGES[page_key])
