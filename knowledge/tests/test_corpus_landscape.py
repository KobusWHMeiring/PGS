"""The landscape artefact: reviewed, traceable, and the document's three real branches.

`LANDSCAPE_TABLES_PRD` step 2 turned the certification landscape from a PDF-path document into a
reviewed artefact. This file answers the questions that make a transcription trustworthy, in the
same order `test_corpus_bpp.py` does:

1. **Is it the same document?** The header's sha256 is the shipped PDF's, and the page markers
   stay inside it.
2. **Does it open the document's real branches?** The PDF path read a fee cell (`R500`) and two
   seal captions (`PGS SA.`, `SAOSO`) as headings, because they are CAPS lines. The artefact
   carries the paper's three table headings and nothing else.
3. **Is every prose block on the page it names?** A block that cannot be found on paper is a
   quote nobody can verify; the table cells are proved line by line in
   `test_landscape_table_block.py`.
4. **Does it invent a character?** Every non-space character in a body block must be on the
   pages the artefact covers (§8 requirement 4).
5. **Is the chunk count the measured one?** §12a warned that 11 was a prediction. Eleven is what
   eight reviewed rows and three prose blocks produce; the number is asserted here, as measured.

**What is deliberately absent:** pages 1–3 (the introduction, the six basic elements and the three
certification routes) and page 9's colophon are front matter, not tables, and are step 5 of the
PRD (`D72.6`). The artefact starts at PDF 4, and `test_the_front_matter_is_still_absent` records
that as a gap rather than pretending the document is complete.
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

#: The PDF pages the artefact covers. 1-3 and 9 are step 5 (front matter and colophon).
COVERED = (4, 5, 6, 7, 8)

#: Measured 2026-10-30: eight reviewed rows plus the three prose blocks that surround them
#: (the p4 lead-in, the p6 trailing paragraphs, the p7 lead-in). §12a's 11/12 was eight rows
#: plus three front-matter passages and the lead-in; the front matter is step 5 and will raise
#: this number when it lands, which is why the count is asserted after the artefact, not before.
EXPECTED_CHUNKS = 11


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


def test_it_opens_the_three_printed_branches(document):
    assert [
        (section.anchor, section.heading_path, section.page, section.section_ref)
        for section in document.sections
    ] == [
        ("establishing-a-pgs-group", "ESTABLISHING A PGS GROUP", 4, None),
        ("pgs-seals-and-their-use", "PGS SEALS AND THEIR USE", 6, None),
        ("saoso-organic-certification", "SAOSO ORGANIC CERTIFICATION", 7, None),
    ]


def test_it_carries_no_false_heading(document):
    """The three the parser opened from a fee cell and two seal captions (§12b)."""
    anchors = {section.anchor for section in document.sections}
    assert "r500" not in anchors
    assert "pgs-sa" not in anchors
    assert "saaso" not in anchors, "the seal caption after SAOSO ORGANIC CERTIFICATION"
    headings = {section.heading_path for section in document.sections}
    assert headings == {
        "ESTABLISHING A PGS GROUP",
        "PGS SEALS AND THEIR USE",
        "SAOSO ORGANIC CERTIFICATION",
    }


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


def test_the_chunk_count_is_the_measured_eleven(document):
    chunks = chunks_for_sections(list(document.sections))
    assert len(chunks) == EXPECTED_CHUNKS, [
        (chunk.page, chunk.heading_path) for chunk in chunks
    ]
    rows = sum(len(section.tables[0].rows) for section in document.sections)
    prose = len(chunks) - rows
    assert (rows, prose) == (8, 3), "eight reviewed rows and three prose blocks"


def test_a_table_that_opens_straight_into_its_rows_gets_no_heading_only_chunk(document):
    """`PGS SEALS AND THEIR USE` prints no lead-in, and a chunk with only a heading says
    nothing while remaining retrievable and citable."""
    chunks = chunks_for_sections(list(document.sections))
    assert not [
        chunk
        for chunk in chunks
        if flat(chunk.text) in {section.heading_path for section in document.sections}
    ]


# --- The gap that step 5 closes ---------------------------------------------


def test_the_front_matter_is_still_absent(document):
    """Pages 1-3 and 9 are step 5 (`D72.6`), and this test is the honest record of the gap.

    When the front matter lands, this test is **deleted with the gap**: the four probes in
    `LANDSCAPE_TABLES_PRD` §9 step 5 that return zero today must then return one chunk each.
    """
    body = flat(" ".join(block.text for block in document.blocks))
    assert "Participatory Guarantee Systems" not in body
    assert "First-Party Claim" not in body
    assert "Gesellschaft für" not in body, "the p9 colophon"
    assert min(block.page for block in document.blocks) == 4
