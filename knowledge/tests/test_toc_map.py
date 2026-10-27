"""Task B3 — the TOC page map and appendix attribution.

Written against `saoso_toc.txt` (pages 2–3 of the shipped PDF) and cross-checked
against `saoso_appendices.txt`, whose `MANIFEST.json` entry records that A10's
extractor verified `APPENDIX 1` on PDF page 71. Those two fixtures disagree about
which page `Appendix 1` is on — 70 or 71 — and both are right: the TOC prints the
reader's page (D42) and the PDF viewer counts from the unnumbered cover. That is the
one fact this file exists to keep straight, so every call names its coordinate.

The plan's B3 test asks for `segment_appendix(page=71) == "Appendix 1"`, i.e. the PDF
coordinate; `appendix_for_page(70)` says the same thing in D42's coordinate. Both are
in the suite.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge.sections.toc import (
    APPENDIX,
    CLAUSE,
    PRINTED_TO_PDF_OFFSET,
    RANGE,
    appendix_for_page,
    appendix_spans,
    parse_toc,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))


def fixture(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")


@pytest.fixture
def entries():
    return parse_toc(fixture("saoso_toc"))


@pytest.fixture
def spans(entries):
    return appendix_spans(entries, last_printed_page=98)


# --- The plan's acceptance test, in both coordinates -------------------------


def test_the_toc_page_numbers_are_as_shipped(entries):
    """B3's acceptance, verbatim from the plan: the TOC's own numbers."""
    by_label = {entry.label: entry.printed_page for entry in entries if entry.kind == APPENDIX}
    assert by_label["Appendix 1"] == 70
    assert by_label["Appendix 4. Table 2"] == 83
    assert by_label["Appendix 6a"] == 85


def test_appendix_1_resolves_in_the_pdf_coordinate(spans):
    """`segment_appendix(page=71)` in the plan is the PDF index (D42)."""
    assert appendix_for_page(71, spans, coordinate="pdf") == "Appendix 1"


def test_the_coordinate_actually_changes_the_answer(spans):
    """Asserted on a span boundary, where the two coordinates disagree.

    A mutation test found the softer version of this test passing while the offset was
    ignored entirely: printed 70 and PDF 71 both fall inside Appendix 1's span (70-75),
    so the page only *looks* sensitive. On the boundary the offset matters — printed 75
    is Appendix 1 and printed 76 is Appendix 2, so the same pair read as PDF indices is
    76 and 77. Ignore the offset and a page of Appendix 1's content is cited as
    Appendix 2.
    """
    assert appendix_for_page(75, spans) == "Appendix 1"
    assert appendix_for_page(76, spans) == "Appendix 2"
    assert appendix_for_page(76, spans, coordinate="pdf") == "Appendix 1"
    assert appendix_for_page(77, spans, coordinate="pdf") == "Appendix 2"


def test_appendix_1_resolves_in_the_printed_coordinate(spans):
    """The same page, named the way `DocumentChunk.page` stores it (D42)."""
    assert appendix_for_page(70, spans) == "Appendix 1"


def test_an_unknown_coordinate_fails_loudly(spans):
    """A silent default offset is the bug this parameter exists to prevent."""
    with pytest.raises(ValueError, match="coordinate must be"):
        appendix_for_page(70, spans, coordinate="page")


def test_the_offset_matches_a10s_verified_extraction(spans):
    """The cross-artifact check: TOC page + offset == the page the extractor proved.

    A10's manifest records `saoso_appendices` verified `APPENDIX 1` on PDF page 71.
    The TOC says printed 70. If either number ever drifts, this fails — and it fails
    for the right reason, because both sides are evidence rather than assumption.
    """
    recorded = MANIFEST["fixtures"]["saoso_appendices"]
    assert recorded["anchor_page"] == 71
    assert 70 + PRINTED_TO_PDF_OFFSET == recorded["anchor_page"]
    assert "APPENDIX 1" in fixture("saoso_appendices").split("\f")[0]


# --- B3's acceptance: appendix pages are attributed to an appendix -----------


def test_every_page_of_the_appendices_fixture_is_attributed_to_an_appendix(spans):
    """The acceptance test: not to the preceding clause.

    Without the map, pages 71 and 72 (the continuation of `APPENDIX 1`) carry no
    heading of their own and would be absorbed into `§23 Social Justice`, whose text
    ends before page 70. The fixture's three pages are printed 70, 71 and 72.
    """
    pages = fixture("saoso_appendices").split("\f")
    printed = [70, 71, 72]
    assert len(pages) == len(printed), "fixture page count changed; the stamps moved"
    for page in printed:
        assert appendix_for_page(page, spans) == "Appendix 1"


def test_clause_territory_is_not_an_appendix(spans):
    """`§23 Social Justice` is at TOC page 67, immediately before Appendix 1."""
    assert appendix_for_page(67, spans) is None
    assert appendix_for_page(69, spans) is None
    assert appendix_for_page(70, spans) == "Appendix 1"


def test_spans_end_where_the_next_appendix_begins(spans):
    by_label = {span.label: span for span in spans}
    assert by_label["Appendix 1"].first_printed_page == 70
    assert by_label["Appendix 1"].last_printed_page == 75     # Appendix 2 starts at 76
    assert by_label["Appendix 2"].first_printed_page == 76
    # Section C's appendix A follows Appendix 7 in the TOC, so the span crosses the
    # SECTION boundary rather than pretending the part ends the appendix.
    assert by_label["Appendix 7"].last_printed_page == 92     # Appendix A starts at 93


def test_the_final_span_is_open_ended_without_a_document_length(entries):
    """A boundary that was never printed must not be invented."""
    spans = appendix_spans(entries)
    assert spans[-1].label == "Appendix C"
    assert spans[-1].last_printed_page is None
    assert appendix_for_page(98, spans) == "Appendix C"
    assert appendix_for_page(200, spans) == "Appendix C"


def test_the_final_span_closes_when_the_document_length_is_known(entries):
    spans = appendix_spans(entries, last_printed_page=98)
    assert spans[-1].last_printed_page == 98
    assert appendix_for_page(99, spans) is None


# --- The TOC is not uniform, and the parser records that ---------------------


def test_the_blank_range_entry_has_no_page_number(entries):
    """`10 to 19.  Left blank to facilitate future enterprises` prints no page.

    A parser that required `label … page` on every line would drop it silently; a
    parser that invented a page would put `§10` somewhere it does not exist.
    """
    ranges = [entry for entry in entries if entry.kind == RANGE]
    assert [entry.label for entry in ranges] == ["10 to 19"]
    assert ranges[0].printed_page is None
    assert ranges[0].pdf_page is None


def test_wrapped_entries_do_not_become_their_own_entries(entries):
    """`Appendix 1. … 70` wraps to `Production and Processing` on the next line."""
    labels = [entry.label for entry in entries if entry.kind == APPENDIX]
    assert labels.count("Appendix 1") == 1
    assert not [entry for entry in entries if entry.label.startswith("Production")]


def test_part_letters_are_carried_forward(entries):
    """Clause `1.` appears in Section A *and* Section B — the TOC proves reality 3.

    Which is why D41 scopes ingestion to Section B: a bare `1` is not a citation.
    """
    ones = [entry for entry in entries if entry.label == "1"]
    assert [entry.part for entry in ones] == ["A", "B"]
    assert [entry.part for entry in entries if entry.label == "Appendix 4. Table 2"] == ["B"]
    assert [entry.part for entry in entries if entry.label == "Appendix A"] == ["C"]


def test_entries_are_in_document_order(entries):
    pages = [entry.printed_page for entry in entries if entry.printed_page is not None]
    assert pages == sorted(pages)
    assert pages[0] == 4  # Section A's `1. Introduction`


def test_front_matter_is_not_an_entry(entries):
    """`Foundation of the SAOSO Standards    2` has no number, so it is not a clause."""
    titles = {entry.title for entry in entries}
    assert not [title for title in titles if "Foundation of the SAOSO" in title]
    assert not [entry for entry in entries if entry.printed_page == 2]


# --- D68: the printed TOC is read at ingest ----------------------------------


def test_the_toc_is_read_from_the_page_that_prints_it():
    """`saoso_toc.txt` is a verbatim `pdftotext -layout` extract of printed p.2.

    A hand-written TOC would encode the same assumption as the regex it tests
    (`testing_hazards.md` §3.7). Measured 2026-10-27: 29 entries, of which one is the
    reserved range and three are the appendices the corpus does not contain (§10.6).
    """
    from knowledge.sections.toc import toc_from_pages

    entries = toc_from_pages([fixture("saoso_toc")])

    assert len(entries) == 29
    assert [entry.kind for entry in entries].count(RANGE) == 1
    assert [entry.label for entry in entries if entry.kind == APPENDIX][-3:] == [
        "Appendix A",
        "Appendix B",
        "Appendix C",
    ]


def test_a_page_with_no_contents_heading_yields_nothing():
    """Bounded on purpose: `APPENDICES` appears in the body too, and a body clause matches
    the TOC's clause pattern. A body page must produce no entries."""
    from knowledge.sections.toc import toc_from_pages

    assert toc_from_pages([fixture("saoso_part_b")]) == []


def test_the_stored_shape_is_a_dict_of_the_entry():
    """`StandardDocument.toc` is JSONB; the concordance reads `entry["label"]`."""
    from knowledge.sections.toc import toc_from_pages

    entry = toc_from_pages([fixture("saoso_toc")])[0]

    assert entry.as_dict() == {
        "part": "A",
        "kind": CLAUSE,
        "label": "1",
        "title": "Introduction - The Principles of Organic Agriculture",
        "printed_page": 4,
    }
