"""The OPP artefact: reviewed, traceable, and equivalent to the PDF path (D53, P4).

P4 is the second document to stop being parsed from its PDF and start being read from a
reviewed artefact. Two things make the transcription trustworthy, and they are the same two
questions `test_corpus_bpp.py` and `test_corpus_saoso.py` ask:

1. **Is it the same document?** The header's sha256 is the shipped PDF's, the artefact carries
   every character the PDF path's sections produce, and every section keeps the identity a
   citation resolves through — `section_ref`, printed page and `heading_path`.
2. **Does the reading hold on the page it names?** The sentences the chatbot quotes are
   asserted contiguous here, because a transcription that mangles one is worse than the
   extractor defect it replaced.

**The identity gate is new for this document, and it needed a parser fix.** `OppParser` built
`heading_path` from `stack[:-1]` — the section's ancestors without the section — while the
corpus format (and `SaosoParser`, since 2026-10-28) includes the section itself. Comparing the
two would have compared a sentence to a breadcrumb. The one-word fix is in `opp.py` and the
first test below is what would have caught it (D75's third remaining item).

**§2.3 is this document's first `<!-- table -->` block.** The sliding scale was one
1,613-character chunk whose columns were spaces, so six turnover bands rendered as prose and
the model had to guess which of two bare numbers was the initial fee — measured on `/ask/`,
2026-11-01, `CHAT_ANSWER_COVERAGE_PRD.md` G10. Six reviewed rows replace it: one chunk per
band, each carrying the printed cells and nothing else (D73).

**What is deliberately not here:** pdf 11's §6.5 labelling table, which is still excluded from
the column transform and still prose in this artefact. It is the second table P4 names and it
is the next slice, not this one.
"""

from __future__ import annotations

import collections
from pathlib import Path

import pytest

from knowledge.columns import apply_layout
from knowledge.corpus import flat, load_document
from knowledge.extraction import sha256_of
from knowledge.ingest import chunks_for_sections
from knowledge.reflow import reflow_pages
from knowledge.sections.opp import OppParser
from knowledge.tables import artefact_grid_for
from knowledge.tests.page_fixtures import pages

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF = REPO_ROOT / "pgs_docs" / (
    "Outeniqua pgs principles, policies and procedures 2026.pdf"
)
ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "opp.md"

#: Measured 2026-11-01: 28 sections, and **37 chunks** — 30 as the PDF path produced them,
#: plus seven: §2.3's single chunk became a lead-in, six reviewed bands and the notes that
#: follow the table. Pinned as a number rather than a range so a reprint (or an accidental
#: extra table) fails here with the count, not months later in a citation.
EXPECTED_SECTIONS = 28
EXPECTED_CHUNKS = 37

#: The bands exactly as the paper prints them, in the paper's order. The two fee columns are
#: the printed amounts, which carry no thousands separator and no currency symbol.
BANDS = (
    ("Below R 250,000", "1,500", "900"),
    ("R 250,001 – R 500,000", "2,500", "2,000"),
    ("R 500,001 – R 1,000,000", "3,000", "2,500"),
    ("R 1,000,001 – R 2,500,000", "3,700", "3,200"),
    ("R 2,500,001 – R 5,000,000", "5,000", "5,000"),
    ("Above R 5,000,000", "8,000", "8,000"),
)


@pytest.fixture(scope="module")
def document():
    return load_document(ARTEFACT)


@pytest.fixture(scope="module")
def pdf_sections():
    """The PDF path — the artefact is a transcription of *this*, so it is the control."""
    laid, _ = apply_layout(pages("opp"), doc_key="opp")
    laid, _ = reflow_pages(laid)
    return OppParser().parse("\f".join(laid))


@pytest.fixture(scope="module")
def scale(document):
    return next(
        section for section in document.sections if section.section_ref == "§2.3"
    )


def chars(text: str) -> collections.Counter:
    return collections.Counter("".join(text.split()))


# --- 1. It is the same document ---------------------------------------------


def test_the_header_is_the_shipped_pdf(document):
    assert document.source == (
        "pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf"
    )
    assert document.sha256 == sha256_of(PDF)
    assert document.generator.startswith("knowledge corpusgen")


def test_the_page_markers_are_monotonic_and_inside_the_document(document):
    numbers = [block.page for block in document.blocks]
    assert numbers == sorted(numbers), "a page marker went backwards"
    assert 1 <= min(numbers) and max(numbers) <= 15


def test_every_section_keeps_the_parsers_identity(document, pdf_sections):
    """A citation resolves through `section_ref`, the page, and the branch path."""
    identity = lambda section: (  # noqa: E731 - a one-line tuple, used twice
        section.section_ref,
        section.page,
        section.heading_path,
    )
    assert [identity(s) for s in document.sections] == [
        identity(s) for s in pdf_sections
    ]
    assert len(document.sections) == EXPECTED_SECTIONS


def test_the_path_includes_the_section_itself(document):
    """The rule `SaosoParser` was corrected to; `OppParser` kept the old one until P4.

    Without it the artefact is generated at its parent's depth (`## 2.1` beside `## II.`),
    which is what the generator derives the `#` level from.
    """
    section = next(s for s in document.sections if s.section_ref == "§2.1")
    assert section.heading_path == (
        "II. Membership fees, farm assessment fees, licensing fees > 2.1 Membership Fees"
    )


def test_the_artefact_carries_every_character_the_pdf_path_produces(
    document, pdf_sections
):
    """No silent loss and no invention: the transcription is character-for-character.

    Multiset rather than order, because `flat()` forgives spacing that a re-print removes.
    Order is covered by the identity gate above and by the quotable sentences below.

    **The one exception is the printed column header**, which the table block carries as its
    `cols:` field. It is structure, not text: the reader prints it above the grid and a row
    chunk must not repeat it (D70.1/D73 — the label is not part of what a row quotes). The
    missing characters are asserted to be exactly that line, so a second silent loss cannot
    hide behind the exception.
    """
    header_line = (
        "Annual farm turnover (gross sales) Initial certification fee (R) Renewal fee (R)"
    )
    expected = collections.Counter()
    for section in pdf_sections:
        expected.update(chars(section.text.partition("\n")[2]))
    expected.subtract(chars(header_line))
    expected = +expected

    actual = chars(flat(" ".join(block.text for block in document.blocks)))
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"the artefact dropped characters: {dict(missing)}"
    assert not extra, f"the artefact invented characters: {dict(extra)}"


def test_every_sub_clause_survives_with_the_same_span(document, pdf_sections):
    """Rule 6 end to end: 24 addresses, and each quotes the words the PDF path quoted.

    This is the guard the whole `sub:` annotation exists for. Converting the OPP to an
    artefact without it dropped `4.5(1)`, `4.5(2)(c)` and `4.5(4)` — the OPP is the one
    governed document whose citations go three levels deep (D15), and nothing else noticed
    until `test_opp_sub_refs_survive_into_the_database` did.
    """
    def spans(section):
        return [(ref.ref, flat(section.text[ref.start : ref.end])) for ref in section.sub_refs]

    artefact_spans = {s.section_ref: spans(s) for s in document.sections}
    pdf_spans = {s.section_ref: spans(s) for s in pdf_sections}

    assert artefact_spans == pdf_spans
    assert sum(len(value) for value in artefact_spans.values()) == 24, (
        "measured 2026-11-01: 4.1 has 3, 4.2 has 12 and 4.5 has 9"
    )


# --- 2. The sliding scale is a reviewed table -------------------------------


def test_the_scale_declares_a_grid_with_the_papers_three_columns(scale):
    assert len(scale.tables) == 1
    table = scale.tables[0]
    assert table.layout == "grid"
    assert table.columns == (
        "Annual farm turnover (gross sales)",
        "Initial certification fee (R)",
        "Renewal fee (R)",
    )
    assert table.legend, "a reviewed table states what its cells do not"


def test_each_band_is_one_row_of_the_printed_cells(scale):
    rows = scale.tables[0].rows
    assert len(rows) == len(BANDS)
    assert [tuple(cell.text for cell in row.cells) for row in rows] == [
        band for band in BANDS
    ]
    assert [row.label for row in rows] == [band[0] for band in BANDS]


def test_each_band_is_its_own_chunk_and_still_cites_the_scale(document):
    """Six bands, six chunks — and each keeps `§2.3`, so a citation still resolves."""
    rows = [c for c in chunks_for_sections(list(document.sections)) if c.section_ref == "§2.3"]
    bands = [c for c in rows if c.heading_path.rsplit(" — ", 1)[-1] in dict.fromkeys(b[0] for b in BANDS)]
    assert len(bands) == len(BANDS)
    for chunk, band in zip(bands, BANDS):
        assert chunk.text == "\n".join(band)
        assert chunk.page == 2, "the whole scale is printed on pdf page 2"


def test_the_chunk_count_is_the_measured_thirty_seven(document):
    chunks = chunks_for_sections(list(document.sections))
    assert len(chunks) == EXPECTED_CHUNKS, [
        (chunk.section_ref, chunk.heading_path, chunk.text[:40]) for chunk in chunks
    ]


def test_the_reader_aligns_the_grid_from_the_reviewed_data(scale):
    """The display model the reader draws: three columns, six rows, a grid."""
    grid = artefact_grid_for(scale)
    assert grid is not None
    assert grid.layout == "grid"
    assert grid.columns == scale.tables[0].columns
    assert grid.row_texts == tuple("\n".join(band) for band in BANDS)


# --- 3. What the corpus has to keep saying ----------------------------------


def test_the_lead_in_is_quotable(document):
    """The sentence that says the fee is a scale and travel is not in it."""
    text = flat(" ".join(block.text for block in document.blocks))
    assert (
        "The farm assessment visit fee is set based on a sliding scale (see below), "
        "excluding transport costs for the administrator (charged at an AA rate per km)."
    ) in text


def test_the_notes_under_the_table_survive_the_review(document):
    """The conditions that qualify every amount above them are still contiguous."""
    text = flat(" ".join(block.text for block in document.blocks))
    for sentence in (
        "Transport costs for the PGS administrator are charged separately at cost. (AA rate)",
        "Renewal fees apply only where no significant changes to land, production system, "
        "or inputs have occurred.",
        "Annual turnover is self-declared by the farmer and subject to peer review within "
        "the PGS group.",
        "Only fully paid-up members will be eligible for farm assessments and receive "
        "certificates.",
    ):
        assert sentence in text, sentence


def test_the_amounts_the_public_page_publishes_are_on_the_page(document):
    """`_public.FEE_BANDS` is the site's copy of this scale; the two must not drift.

    Checked as text rather than by importing `core` (this package may not import it): every
    amount on the public page is a string printed in this table.
    """
    from knowledge.tests.page_fixtures import pages as _pages

    printed = " ".join(" ".join(page.split()) for page in _pages("opp"))
    for _band, initial, renewal in BANDS:
        assert f" {initial} " in f" {printed} ", initial
        assert f" {renewal} " in f" {printed} ", renewal
