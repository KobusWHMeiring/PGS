"""The landscape artefact: reviewed, traceable, and the document's own branches.

`LANDSCAPE_TABLES_PRD` steps 2–5 turned the certification landscape from a PDF-path document
into a reviewed artefact: three tables of reviewed rows, then the front matter the PDF parser
could never open. This file answers the questions that make a transcription trustworthy, in the
same order `test_corpus_bpp.py` does:

1. **Is it the same document?** The header's sha256 is the shipped PDF's, and the page markers
   stay inside it.
2. **Does it open the document's real branches?** The PDF path read a fee cell (`R500`) and two
   seal captions (`PGS SA.`, `SAOSO`) as headings, because they are CAPS lines. The artefact
   carries the paper's headings and the three the reviewer adds for pages that print none.
3. **Is every prose block on the page it names?** A block that cannot be found on paper is a
   quote nobody can verify; the table cells are proved line by line in
   `test_landscape_table_block.py`, the front matter here.
4. **Does it invent a character?** Every non-space character in a body block must be on the
   pages the artefact covers (§8 requirement 4).
5. **Is the chunk count the measured one?** §8/§12a's 11 was a prediction about a different
   composition. Seventeen is what 8 rows, 3 table-prose blocks and 6 front-matter sections
   produce; the number is asserted here, as measured.

**What is deliberately absent:** page 1 (a cover whose only line is the running header, which is
furniture) and page 10 (blank). Both contribute no chunk, and `COVERED` says so.
"""

from __future__ import annotations

import collections
from pathlib import Path

import pytest

from knowledge.corpus import flat, load_document
from knowledge.extraction import sha256_of
from knowledge.ingest import chunks_for_sections
from knowledge.tests.page_fixtures import pages

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF = REPO_ROOT / "pgs_docs" / "PGS Certification landscape_Final.pdf"
ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "landscape.md"

#: The PDF pages the artefact covers. 1 is a cover (its only line is the running header, which
#: is furniture) and 10 is blank; both stay out and contribute no chunk.
COVERED = (2, 3, 4, 5, 6, 7, 8, 9)

#: Measured 2026-10-30: **17 chunks** — 8 reviewed rows, 3 prose blocks around the tables (the p4
#: lead-in, the p6 trailing paragraphs, the p7 lead-in), and 6 front-matter sections (the intro,
#: the six basic elements, the three certification routes, the colophon). §8's predicted 11 was 8
#: rows + 3 front-matter passages; the routes are three sections because the paper prints three
#: headings, and the six elements is its own section so its probe resolves to one chunk.
EXPECTED_CHUNKS = 17


@pytest.fixture(scope="module")
def document():
    return load_document(ARTEFACT)


def squash(text: str) -> str:
    """All whitespace removed — the traceability comparison's normal form."""
    return "".join(text.split())


def body_chars(document) -> collections.Counter:
    return collections.Counter("".join("".join(block.text for block in document.blocks).split()))


# --- 1. It is the same document ---------------------------------------------


def test_the_header_is_the_shipped_pdf(document):
    assert document.source == "pgs_docs/PGS Certification landscape_Final.pdf"
    assert document.sha256 == sha256_of(PDF)


def test_the_page_markers_are_monotonic_and_inside_the_document(document):
    seen = [block.page for block in document.blocks]
    assert seen == sorted(seen), "a page marker went backwards"
    assert set(seen) <= set(COVERED), "the artefact covers a page it should not"
    assert set(seen) == set(COVERED), "a table page contributed no body text"


# --- 2. The document's real branches ----------------------------------------


def test_it_opens_the_documents_branches(document):
    """Three printed table headings, three printed route headings, and three reviewed ones.

    Pages 1–3 print no heading the PDF parser will open, so `INTRODUCTION`, `SIX BASIC ELEMENTS`
    and `COLOPHON` are the reviewer's (`D72.6`); the routes and the tables are the paper's own.
    """
    assert [
        (section.anchor, section.heading_path, section.page, section.section_ref)
        for section in document.sections
    ] == [
        ("introduction", "INTRODUCTION", 2, None),
        ("six-basic-elements", "SIX BASIC ELEMENTS", 2, None),
        ("first-party-claim", "First-Party Claim", 3, None),
        ("second-party-certification", "Second-Party Certification", 3, None),
        ("third-party-certification", "Third-Party Certification", 3, None),
        ("establishing-a-pgs-group", "ESTABLISHING A PGS GROUP", 4, None),
        ("pgs-seals-and-their-use", "PGS SEALS AND THEIR USE", 6, None),
        ("saoso-organic-certification", "SAOSO ORGANIC CERTIFICATION", 7, None),
        # Page 9 prints no page number, so D42's `page` is None; the block is on PDF 9.
        ("colophon", "COLOPHON", None, None),
    ]


def test_it_carries_no_false_heading(document):
    """The three the parser opened from a fee cell and two seal captions (§12b)."""
    anchors = {section.anchor for section in document.sections}
    assert "r500" not in anchors
    assert "pgs-sa" not in anchors
    assert "saaso" not in anchors, "the seal caption after SAOSO ORGANIC CERTIFICATION"


# --- 3. The prose is on the page it names -----------------------------------


#: Every prose block the artefact carries, and the PDF page that prints it. The table cells are
#: not listed: they are proved one printed line at a time in `test_landscape_table_block.py`.
PROSE = (
    (
        4,
        "The table below outlines the steps for the establishment of a PGS group and its "
        "membership to PGS SA.",
    ),
    (
        6,
        "PGS SA is developing guidelines to facilitate trade between PGS groups to ensure "
        "traceability.",
    ),
    (
        6,
        "PGS Organic and PGS Organic In-Conversion seals are as acceptable forms of organic "
        "certification, as any other type of certification, only the process for achieving the "
        "outcome of organic recognition is different.",
    ),
    (
        7,
        "PGS groups that wish to enter more formal markets and use the nationally recognised "
        "SAOSO “Organic PGS Certified” logo would take the following steps.",
    ),
)


@pytest.mark.parametrize("page,prose", PROSE, ids=[f"p{page}:{p[:24]}" for page, p in PROSE])
def test_the_prose_is_a_contiguous_run_of_its_page(page, prose):
    """The reviewed prose is the paper's, re-spaced — never re-worded."""
    printed = squash(pages("landscape", "layout")[page - 1])
    assert squash(prose) in printed, f"not on PDF page {page}: {prose[:70]!r}"


# --- 4. No character invented -----------------------------------------------


def test_it_invents_no_character(document):
    """§8 requirement 4, first clause: the body is a subset of the pages' characters.

    A multiset equality would also catch a *dropped* cell, but it cannot survive a review that
    drops furniture and a repeated table header on purpose. The line-pinned guard in
    `test_landscape_table_block.py` is what proves nothing was dropped from a cell; this proves
    nothing was typed in.
    """
    covered = collections.Counter()
    for page in COVERED:
        covered.update("".join(pages("landscape", "table")[page - 1].split()))
    invented = body_chars(document) - covered
    assert not invented, f"the artefact carries characters no covered page prints: {dict(invented)}"


# --- 5. The measured chunk count --------------------------------------------


def test_the_chunk_count_is_the_measured_seventeen(document):
    chunks = chunks_for_sections(list(document.sections))
    assert len(chunks) == EXPECTED_CHUNKS, [
        (chunk.page, chunk.heading_path) for chunk in chunks
    ]
    rows = sum(len(section.tables[0].rows) for section in document.sections if section.tables)
    front_matter = 6
    prose = len(chunks) - rows - front_matter
    assert (rows, prose, front_matter) == (8, 3, 6)


def test_a_table_that_opens_straight_into_its_rows_gets_no_heading_only_chunk(document):
    """`PGS SEALS AND THEIR USE` prints no lead-in, and a chunk with only a heading says
    nothing while remaining retrievable and citable."""
    chunks = chunks_for_sections(list(document.sections))
    assert not [
        chunk
        for chunk in chunks
        if flat(chunk.text) in {section.heading_path for section in document.sections}
    ]


# --- Step 5: the front matter, and the four probes that returned zero ---------

#: `LANDSCAPE_TABLES_PRD` §1.4: before step 5 these four probes matched **0** chunks, because the
#: PDF parser opens no section on pages 2–3. Each must now resolve to exactly one chunk.
FRONT_MATTER_PROBES = (
    ("Participatory Guarantee Systems", "introduction"),
    ("six basic elements", "six-basic-elements"),
    ("First-Party", "first-party-claim"),
    ("Third-Party", "third-party-certification"),
)


@pytest.mark.parametrize(
    "probe,anchor", FRONT_MATTER_PROBES, ids=[probe for probe, _ in FRONT_MATTER_PROBES]
)
def test_the_front_matter_probes_each_resolve_to_one_chunk(document, probe, anchor):
    """§1.4's four zeros, measured again after the review.

    The probe is case-insensitive on purpose: the paper prints `6 basic elements` and the reviewer's
    heading supplies the word `six`, which is what a full-text search for the *question's* wording
    needs. FTS is case-insensitive, so the test is too.
    """
    chunks = chunks_for_sections(list(document.sections))
    holders = [
        chunk
        for chunk in chunks
        if probe.lower() in " ".join(chunk.text.lower().split())
    ]
    assert len(holders) == 1, [chunk.anchor for chunk in holders]
    assert holders[0].anchor == anchor


#: The printed page for each front-matter section, because page 9 prints no page number and
#: `ParsedSection.page` is therefore None (D42) even though the block is on PDF 9.
FRONT_MATTER_PAGES = {
    "INTRODUCTION": 2,
    "SIX BASIC ELEMENTS": 2,
    "First-Party Claim": 3,
    "Second-Party Certification": 3,
    "Third-Party Certification": 3,
    "COLOPHON": 9,
}


@pytest.mark.parametrize("heading", sorted(FRONT_MATTER_PAGES))
def test_each_front_matter_line_is_a_printed_line(document, heading):
    """The review reads the page; the test only checks that it did not type its own words.

    One paragraph at a time (a page's two columns put one column's lines out of page order, the
    same reason the table guard resets per cell), every line must be a contiguous run of a
    printed `-layout` line, and a paragraph's lines must keep their order.
    """
    section = next(section for section in document.sections if section.heading_path == heading)
    printed = [
        " ".join(line.split())
        for line in pages("landscape", "layout")[FRONT_MATTER_PAGES[heading] - 1].splitlines()
    ]
    body = section.text.partition("\n")[2]
    checked = 0
    for paragraph in body.split("\n\n"):
        cursor = -1
        for line in paragraph.splitlines():
            if not line.strip():
                continue
            wanted = " ".join(line.split())
            found = next(
                (index for index in range(cursor + 1, len(printed)) if wanted in printed[index]),
                None,
            )
            assert found is not None, (
                f"{heading}: this line is not a run of any printed line on PDF "
                f"{FRONT_MATTER_PAGES[heading]}: {wanted[:70]!r}"
            )
            assert found > cursor, (
                f"{heading}: printed out of order, {found} after {cursor}: {wanted[:70]!r}"
            )
            cursor = found
            checked += 1
    assert checked > 5, f"{heading} checked only {checked} lines"


def test_the_reviewer_added_headings_are_not_printed(document):
    """D72.6: three headings are the reviewer's, and the review says so instead of pretending."""
    printed = " ".join(pages("landscape", "layout")).lower()
    assert "introduction" not in printed
    assert "six basic elements" not in printed
    assert "colophon" not in printed
    assert "first-party claim" in printed, "a route heading IS printed (Title case)"


def test_the_colophon_carries_the_funders_and_the_copyright(document):
    section = next(section for section in document.sections if section.anchor == "colophon")
    body = " ".join(section.text.split())
    assert "Deutsche Gesellschaft für Internationale Zusammenarbeit (GIZ)" in body
    assert "© PGS South Africa/South African Organic Sector Organisation (SAOSO), 2021" in body
    assert "These organisations are not responsible for the content nor the accuracy" in body
