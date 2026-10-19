"""Task B2 — section parsers, written against A10's verbatim fixtures.

The fixtures are extracted from the shipped PDFs by `scripts/extract_fixtures.py`
and are **never hand-edited**; a hand-written fixture encodes the same assumption as
the parser it tests, which is how MVP 0 v1 passed its tests while matching zero lines
of the real document. Two tests here re-verify that premise before any parser runs:
the files still hash to what `MANIFEST.json` recorded, and each declared anchor is
still present on the page the extractor verified it on.

Decisions this file encodes (all from the spec, not from preference):

- **D43** — `section_ref` is the citation a human reads: `S20.1.1`, `§V`, `§4.2(5)`.
  `sub_refs` stay plain (`4.5(2)(c)`), and `B.20.1.1` is withdrawn (it appears nowhere
  in either document; the only `B-20` is a heading in the FORM workbook).
- **D42** — the SAOSO parser reads `page` from the document's own footer (`P a g e |
  60`), which is the reader's page, not the PDF index.
- **D41** — SAOSO's Section B is the ingested part. Section A collides with itself and
  Section C restarts at `1.`, so the parser must *carry the part letter forward* from
  the running header and refuse to emit clauses belonging to another part.

The §4.5 item-numbering test is the sharpest one in the suite. The plan's own `ITEM`
regex requires at least two leading spaces, so against this fixture it misses items
`4.` and `5.` (at column 0, after a page break) and *invents* `4.5(3)` from the third
attendee of the (c) list. See `test_missing_item_number_is_reported_not_invented` and
the `max_item_depth` note in `opp.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from django.conf import settings

from knowledge.models import StandardDocument
from knowledge.sections import ParsedSection, SubRef
from knowledge.sections.heading import HeadingParser
from knowledge.sections.opp import OppParser
from knowledge.sections.registry import UnknownSectionScheme, get, get_for
from knowledge.sections.saoso import SaosoParser

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))


def fixture(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")


# --- 0. The fixtures are still the fixtures ----------------------------------


@pytest.mark.parametrize("name", sorted(MANIFEST["fixtures"]))
def test_fixture_matches_the_manifest(name):
    """sha256 per fixture: regenerating from the PDFs must not have drifted."""
    recorded = MANIFEST["fixtures"][name]
    digest = hashlib.sha256((FIXTURES / f"{name}.txt").read_bytes()).hexdigest()
    assert digest == recorded["sha256"]
    # Parametrising over the manifest means a fixture added without a manifest entry
    # is invisible here — so assert the count in both directions.
    assert len(list(FIXTURES.glob("*.txt"))) == len(MANIFEST["fixtures"])


@pytest.mark.parametrize("name", sorted(MANIFEST["fixtures"]))
def test_fixture_still_contains_its_verified_anchor(name):
    """The anchor the extractor proved is still on the page it proved it on.

    This is A10's guard surviving into B2: if a fixture were hand-edited, the anchor
    would still match and the hash above would fail — but if the *PDF* changed, the
    hash and the anchor fail together, which is what tells a reader which happened.

    `anchor_page` is a PDF page number, while the fixture contains only its extract's
    page range, so the anchor is checked against the fixture's **first** page (every
    extract declares its anchor on `start_page`).
    """
    recorded = MANIFEST["fixtures"][name]
    start_page = int(recorded["pages"].split("-")[0])
    assert recorded["anchor_page"] == start_page, (
        "the extractor verifies an anchor on the extract's start page; the manifest "
        "records them disagreeing, so the fixture's first page is not the anchored page"
    )
    first_page = fixture(name).split("\f")[0]
    assert re.search(recorded["anchor"], first_page, re.MULTILINE), (
        f"{name}: anchor {recorded['anchor']!r} missing from the fixture's first page "
        f"(PDF p{recorded['anchor_page']}); does the fixture still match its PDF?"
    )


# --- 1. SAOSO ----------------------------------------------------------------


def test_saoso_yields_sections_with_refs():
    sections = SaosoParser().parse(fixture("saoso_part_b"))
    assert len(sections) > 0                      # v1 returned []
    assert all(s.section_ref for s in sections)
    assert "S20.1.1" in {s.section_ref for s in sections}


def test_saoso_never_emits_the_invented_ref():
    """`B.20.1.1` and `B-20.1.1` are both withdrawn (D43, F1)."""
    refs = {s.section_ref for s in SaosoParser().parse(fixture("saoso_part_b"))}
    assert not [r for r in refs if "B." in r or "B-" in r]


def test_saoso_part_letter_comes_from_the_running_header():
    """The fixture's only part heading is `SECTION B`, printed as a running header.

    Parsing without being told the part must still yield Section B refs — the letter
    is read from the page header and carried forward, because only 22 of 98 body pages
    print one (SPEC §4.5 reality 1).
    """
    sections = SaosoParser().parse(fixture("saoso_part_b"))
    assert all(s.section_ref.startswith("S2") for s in sections)


def test_saoso_refuses_clauses_from_another_part():
    """Section A is out of scope (D41) and its numbers collide with Section B's.

    The TOC fixture contains a `SECTION B` heading on its second page, so a parser
    that ignored the part would emit Sections A *and* B clauses from it. It must emit
    neither, because the page is a table of contents.
    """
    assert SaosoParser().parse(fixture("saoso_toc")) == []


def test_toc_page_is_excluded_before_clause_detection():
    """The TOC matches the clause pattern and would ingest as 60+ duplicate clauses.

    Asserted directly on a real TOC line, so the test fails if the exclusion is
    removed *or* if the pattern stops matching the fixture.
    """
    toc = fixture("saoso_toc")
    assert re.search(r"^\d+\.\s+\S.*\d+\s*$", toc, re.M), "TOC is no longer clause-shaped"
    assert SaosoParser().parse(toc) == []


def test_toc_exclusion_is_load_bearing():
    """A TOC page that also carries an indented part header is still skipped.

    On the real fixture the TOC is excluded twice over: by the explicit skip, and as a
    side effect of reading the part letter only from an indented header (the TOC prints
    `SECTION A` at column 0). A guard that passes only because a second mechanism
    covers it is not a guard — so this pins the skip alone, on the one page shape where
    they disagree: a TOC whose part header is indented, as a continued TOC would be.
    """
    toc_page = (
        "                                          TABLE OF CONTENTS\n"
        "                                                               SECTION B\n"
        "1.         Introduction - The Principles of Organic Agriculture            4\n"
    )
    assert re.search(r"^\s{8,}SECTION B\s*$", toc_page, re.M), "the header is not indented"
    assert SaosoParser().parse(toc_page) == []


def test_appendix_headings_are_found_in_the_body():
    """All twelve appendix headings exist in the body, in UPPERCASE (reality 4)."""
    refs = {s.section_ref for s in SaosoParser().parse(fixture("saoso_appendices"))}
    assert "Appendix 1" in refs


def test_the_title_case_appendix_regex_is_never_used():
    """The evidence for A10's trap, and the guard that the parser does not repeat it.

    `Appendix 4.` starts a mid-sentence line on p63 of `saoso_part_b`. A title-case,
    column-0 `APPX` regex matches that and nothing in the real headings, so the parser
    must be UPPERCASE-anchored. Both halves are asserted: the false positive is present
    in the fixture, and no section is emitted for it.
    """
    part_b = fixture("saoso_part_b")
    assert re.search(r"^Appendix\s+\d+\.\s*$", part_b, re.M), "p63 false positive is gone"
    refs = {s.section_ref for s in SaosoParser().parse(part_b)}
    assert not [r for r in refs if r and "Appendix" in r]


def test_saoso_page_is_the_printed_number():
    """D42: `P a g e | 60` in the footer, not the PDF index (which is 61)."""
    sections = {s.section_ref: s for s in SaosoParser().parse(fixture("saoso_part_b"))}
    assert sections["S20.1.1"].page == 60
    assert sections["S20.1.1"].heading_path == "20. PROCESSING AND HANDLING > 20.1. General"


def test_saoso_section_text_is_partitioned_not_duplicated():
    """Every section carries its own heading and its own body; none repeats a child's.

    A parent that swallowed its subsections would triple-index the document and make
    `S20.1.1` retrievable three times (SPEC §4.5: chunks stay section-level).
    """
    sections = SaosoParser().parse(fixture("saoso_part_b"))
    assert all(s.text.strip() for s in sections)
    parent = next(s for s in sections if s.section_ref == "S20.1")
    assert "20.1.2." not in parent.text, "a section swallowed its sibling"


# --- 2. OPP ------------------------------------------------------------------


def test_opp_roman_sections_are_reachable():
    refs = {s.section_ref for s in OppParser().parse(fixture("opp_seals"))}
    assert {"§V", "§VI"} <= refs                            # v1 missed both


def test_opp_decimal_sections_are_reachable():
    """`4.6`/`4.7` are at indent 0 and 4; `6.1` sits under the indented `VI.`."""
    refs = {s.section_ref for s in OppParser().parse(fixture("opp_seals"))}
    assert {"§4.6", "§4.7", "§6.1"} <= refs


def test_opp_indented_heading_is_found():
    """`VI.` is at indent 6 — a column-0 regex misses it (reality 5)."""
    fixture_text = fixture("opp_seals")
    assert re.search(r"^\s{1,7}VI\.\s", fixture_text, re.M)
    assert "§VI" in {s.section_ref for s in OppParser().parse(fixture_text)}


def test_depth_three_resolves():
    subs = {r.ref for s in OppParser().parse(fixture("opp_4_5")) for r in s.sub_refs}
    assert "4.5(2)(c)" in subs


def test_depth_four_is_never_synthesised():
    for section in OppParser().parse(fixture("opp_4_5")):
        assert all(r.ref.count("(") <= 2 for r in section.sub_refs)


def test_missing_item_number_is_reported_not_invented():
    """§4.5's outer items are 1, 2, 4, 5 — item 3 does not exist.

    The (2)(c) attendee list restarts at `1.` and runs to `3.`, so a naive state
    machine manufactures `4.5(3)`. This asserts both halves: 3 is absent, and the real
    4 and 5 are present (a parser that simply dropped every nested `N.` would pass the
    first assert and fail the second).
    """
    subs = {r.ref for s in OppParser().parse(fixture("opp_4_5")) for r in s.sub_refs}
    assert "4.5(3)" not in subs
    assert {"4.5(1)", "4.5(2)", "4.5(4)", "4.5(5)"} <= subs


def test_opp_item_markers_that_start_at_column_zero_are_found():
    """Items 4 and 5 sit at column 0 because a page footer shifted the left margin.

    The plan's `ITEM` regex requires `\\s{2,}`, so it silently drops them — and because
    3 is then absent, a reader could mistake the resulting output for SPEC §4.5's
    "item 3 is missing" claim. It is missing for a different reason.
    """
    fixture_text = fixture("opp_4_5")
    assert re.search(r"^4\.\s+The complaint will be read", fixture_text, re.M)
    assert re.search(r"^5\.\s+The meeting will rule", fixture_text, re.M)
    subs = {r.ref for s in OppParser().parse(fixture_text) for r in s.sub_refs}
    assert {"4.5(4)", "4.5(5)"} <= subs


def test_opp_4_1_uses_a_different_item_marker():
    """§4.1's items are `1.`-`3.`, not `1)`: three markers exist across the OPP."""
    subs = {r.ref for s in OppParser().parse(fixture("opp_4_1")) for r in s.sub_refs}
    assert "4.1(1)" in subs


def test_opp_4_2_items_run_to_twelve():
    """§4.2(5) (conclusion within 5 days) and §4.2(12) (traceability) are the citations
    SPEC §4.5 names."""
    subs = {r.ref for s in OppParser().parse(fixture("opp_4_2")) for r in s.sub_refs}
    assert {"4.2(5)", "4.2(12)"} <= subs


def test_sub_refs_are_plain_but_section_refs_are_citations():
    """D43: the `§` lives on `section_ref`, never on a `sub_ref`."""
    sections = OppParser().parse(fixture("opp_4_5"))
    assert all(s.section_ref.startswith("§") for s in sections if s.section_ref)
    assert all(not r.ref.startswith("§") for s in sections for r in s.sub_refs)


def test_every_sub_ref_slices_its_own_section_text():
    """The contract B1's `validate_sub_refs` enforces, proved parser-side.

    A `sub_ref` that points outside its chunk is a citation that renders half a
    sentence; this asserts the offsets before they ever reach the database.
    """
    from knowledge.models import validate_sub_refs

    for name in ("opp_4_1", "opp_4_2", "opp_4_5", "opp_seals"):
        for section in OppParser().parse(fixture(name)):
            assert section.text.strip()
            validate_sub_refs([r.as_dict() for r in section.sub_refs], section.text)
            for ref in section.sub_refs:
                assert section.text[ref.start : ref.end].strip()


# --- 3. Heading-only documents (BPP, LANDSCAPE) ------------------------------


def test_heading_parser_emits_no_section_ref():
    """SPEC §4.5: LANDSCAPE/BPP cite as 'page + heading'; there is no clause number."""
    sections = HeadingParser().parse(fixture("bpp_intro"))
    assert sections
    assert all(s.section_ref is None for s in sections)
    assert all(s.anchor for s in sections), "a heading-only section needs a locator"
    assert all(s.heading_path for s in sections)


def test_heading_parser_finds_caps_headings_in_a_two_column_layout():
    """`pdftotext -layout` puts right-column text on the left heading's line.

    So the heading pattern must tolerate a trailing column and must not end-anchor.
    """
    headings = {s.heading_path for s in HeadingParser().parse(fixture("bpp_intro"))}
    assert "INTRODUCTION" in headings
    assert "GENERAL PRINCIPLES" in headings
    # A wrapped heading's second line is merged, not emitted as its own section.
    assert "DEFINITION OF ORGANIC AGRICULTURE" in headings
    assert "AGRICULTURE" not in headings


def test_running_header_is_not_a_section():
    """`PGS SA - SOUTH AFRICAN ORGANIC CERTIFICATION LANDSCAPE` heads most pages.

    A detector that emitted every caps line would produce one bogus section per page —
    a citation the user cannot locate, which is the definition of a bad citation. The
    fixture spans three pages and the line is stamped on two of them, so this is a
    measured repetition, not an assumed one.
    """
    fixture_text = fixture("landscape_seals")
    running = "PGS SA - SOUTH AFRICAN ORGANIC CERTIFICATION LANDSCAPE"
    pages_with_running = sum(running in page for page in fixture_text.split("\f"))
    assert pages_with_running >= 2, "the running header is no longer repeated"
    anchors = {s.anchor for s in HeadingParser().parse(fixture_text)}
    assert "pgs-sa-south-african-organic-certification-landscape" not in anchors
    assert "pgs-seals-and-their-use" in anchors


def test_heading_parser_uses_the_printed_page():
    """D42 applies to every scheme, not just SAOSO.

    The certification landscape stamps a bare number that equals its PDF index
    (fixture pages 6–8 stamp 6, 7, 8), so there is no cover offset for this document.
    """
    sections = HeadingParser().parse(fixture("landscape_seals"))
    assert all(s.page is not None for s in sections)
    assert {s.page for s in sections} <= {6, 7, 8}
    assert {"PGS SEALS AND THEIR USE", "SAOSO ORGANIC CERTIFICATION"} & {
        s.heading_path for s in sections
    }


# --- 4. The registry --------------------------------------------------------


def test_registry_selects_a_parser_by_scheme():
    assert isinstance(get("saoso"), SaosoParser)
    assert isinstance(get("opp"), OppParser)
    assert isinstance(get("heading"), HeadingParser)


def test_registry_fails_loudly_on_an_unknown_scheme():
    """A missing parser must not silently return the heading fallback."""
    with pytest.raises(UnknownSectionScheme):
        get("eu-2018-848")


def test_registry_takes_the_scheme_from_the_document_row():
    """B2's acceptance: the parser is chosen by `StandardDocument.section_scheme`."""
    document = StandardDocument(
        standard_set_id=1,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.1",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="f" * 64,
        section_scheme="opp",
    )
    assert isinstance(get_for(document), OppParser)
    assert settings.EMBEDDING_DIM  # unrelated, keeps the settings import honest


# --- 5. The section contract -------------------------------------------------


def test_parsed_section_is_immutable_and_serialisable():
    """B6 hands these straight to `DocumentChunk.objects.create(**…)`."""
    section = ParsedSection(
        section_ref="§4.5",
        text="Non-compliance and discipline.",
        heading_path="4.5 Non-compliance",
        page=6,
        sub_refs=(SubRef(ref="4.5(1)", start=0, end=4),),
    )
    assert section.sub_refs[0].as_dict() == {"ref": "4.5(1)", "start": 0, "end": 4}
    assert section.as_chunk_kwargs()["section_ref"] == "§4.5"
    with pytest.raises(Exception):
        section.section_ref = "§4.6"  # frozen dataclass
