"""What the parsers do to a **shipped page** — D46's locator, and page furniture.

Two things here are not about a parser's rules but about the pages those rules run on:

- **D46 / CO-3** — the column transform runs before the parser, and it may not move a
  locator: `page` and `anchor` must be the ones the paper prints, on every shipped
  document. The measurement is per document (`expected_pages`), not a spot check.
- **Page furniture** — the printed footer, the running part banner, a label that opens
  a page: what the parser must drop and what it must keep.

`test_section_parsers.py` is the parsers against A10's fixtures. This file is those
fixtures' pages.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from knowledge.sections.registry import get
from knowledge.sections.saoso import SaosoParser
from knowledge.tests.page_fixtures import pages
from knowledge.tests.section_fixtures import fixture

pytestmark = pytest.mark.django_db


# --- 6. The column transform must not move a locator (D46, CO-3) -------------
#
# The pages are re-ordered at ingest, so every parser runs against different bytes
# than it did before D46. `(section_ref, anchor, page)` is the citation contract:
# a moved locator means a citation that renders the wrong place on the page.
#
# The landscape is why this section exists. Its bare page number is the last
# non-blank line of the *raw* page but lands around line 50 of 90 after reordering,
# so `_page_stamp` returned None for all six sections until it searched the whole
# page — and every landscape citation silently lost its page (D42).

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = REPO_ROOT / "pgs_docs"

SHIPPED = {
    "saoso": ("saoso-version-2.1-2026.pdf", "saoso"),
    "bpp": ("Basic Production Principles_ENG_PRINT.pdf", "heading"),
    "landscape": ("PGS Certification landscape_Final.pdf", "heading"),
    "opp": ("Outeniqua pgs principles, policies and procedures 2026.pdf", "opp"),
}

#: Measured on the shipped PDFs, 2026-10-19. SAOSO's list is run-length encoded
#: (`(page, count)`) because pinning 271 literals hides the shape it is guarding.
EXPECTED_PAGES = {
    "saoso": [
        (22, 1), (30, 3), (31, 5), (32, 14), (33, 8), (34, 7), (35, 5), (36, 7),
        (37, 9), (38, 8), (39, 5), (40, 6), (41, 5), (42, 4), (43, 3), (44, 2),
        (45, 1), (47, 10), (48, 5), (49, 4), (50, 7), (51, 9), (52, 2), (53, 9),
        (54, 10), (55, 2), (56, 3), (57, 14), (58, 9), (59, 12), (60, 11), (61, 8),
        (62, 10), (63, 7), (64, 7), (65, 9), (66, 3), (67, 8), (68, 6), (69, 4),
        (70, 1), (76, 1), (79, 1), (81, 1), (83, 1), (84, 1), (85, 1), (86, 1),
        (88, 1),
    ],
    "landscape": [4, 4, 6, 7, 7, 9],
    "bpp": [None, None, None, 10],
    "opp": [
        1, 1, 1, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 6, 6, 6, 8, 8, 8, 9, 9, 10,
        10, 10, 11, 12, 12,
    ],
}


def expected_pages(doc_key: str) -> list:
    if doc_key != "saoso":
        return EXPECTED_PAGES[doc_key]
    pages: list = []
    for page, count in EXPECTED_PAGES["saoso"]:
        pages.extend([page] * count)
    return pages


@pytest.fixture(scope="module")
def shipped_corpus():
    """Committed pages (D57): the gate must not need a PDF reader to place a clause."""
    return {key: pages(key) for key in SHIPPED}


@pytest.mark.parametrize("doc_key", sorted(SHIPPED))
def test_page_attribution_survives_the_transform(shipped_corpus, doc_key):
    from knowledge.columns import apply_layout

    parser = get(SHIPPED[doc_key][1])
    raw = parser.parse("\f".join(shipped_corpus[doc_key]))
    fixed_pages, changed = apply_layout(shipped_corpus[doc_key], doc_key=doc_key)
    fixed = parser.parse("\f".join(fixed_pages))

    assert [s.page for s in raw] == expected_pages(doc_key)
    assert [(s.section_ref, s.anchor, s.page) for s in fixed] == [
        (s.section_ref, s.anchor, s.page) for s in raw
    ]
    assert list(changed), "the transform did not run, so this test proves nothing"


def test_the_toc_map_is_unchanged(shipped_corpus):
    """Appendix 2's page range comes from this map; SAOSO pdf 2 is excluded for it."""
    from knowledge.columns import apply_layout
    from knowledge.sections.toc import parse_toc

    raw = "\f".join(shipped_corpus["saoso"])
    fixed_pages, _ = apply_layout(shipped_corpus["saoso"], doc_key="saoso")
    assert parse_toc("\f".join(fixed_pages)) == parse_toc(raw)
    assert len(parse_toc(raw)) == 29


# --- 7. Page furniture -------------------------------------------------------


def test_the_printed_page_footer_is_furniture():
    """`P a g e | 47` is the reader's page number, not body text (D42, D52).

    It has to survive long enough for `page_number()` to read it and must never reach a
    chunk: the footer sits at every page boundary, so before D52 it landed in the middle
    of a clause that continues onto the next page (S5.5.1) and split a sentence the
    citation audit then could not find.
    """
    from knowledge.sections import is_furniture

    assert is_furniture("P a g e | 47")
    assert is_furniture(" " * 60 + "P a g e | 48")
    assert is_furniture("Page | 10")


def test_a_clause_is_not_furniture():
    from knowledge.sections import is_furniture

    assert not is_furniture("5.5.1. Animals shall be fed organic feed.")
    assert not is_furniture("The page is a footer-free sentence.")


def test_no_saoso_section_carries_the_printed_page_footer(shipped_corpus):
    """Measured 2026-10-21: 65 chunks carried one before the footer became furniture."""
    from knowledge.columns import apply_layout

    pages, _ = apply_layout(shipped_corpus["saoso"], doc_key="saoso")
    sections = SaosoParser().parse("\f".join(pages))
    carriers = [
        section.section_ref
        for section in sections
        if "P a g e |" in section.text or "Page |" in section.text
    ]
    assert carriers == []
    assert sections, "the parser emitted nothing, so this test proves nothing"


def test_the_body_stream_is_exactly_what_the_parser_parses():
    """`body_lines` exists so the artefact generator slices the *reader's* document.

    Measured cost of the alternative (2026-10-28, generating `knowledge/corpus/saoso.md`):
    slicing every page instead of this stream produced a draft whose `S1` carried text from
    pages the parser drops, and whose `Appendix 7` reproduced the whole of Section C three
    times — because a section's body then ran to the next heading *anywhere in the PDF*.
    """
    text = fixture("saoso_part_b")

    stream = SaosoParser().body_lines(text)
    parsed = SaosoParser().parse(text)

    assert stream, "the fixture produced no body lines"
    assert all(isinstance(pdf_page, int) and pdf_page >= 1 for pdf_page, _printed, _ in stream)
    # Every section's lines are found, in order, in the stream the generator will slice.
    joined = "\n".join(line for _pdf, _printed, line in stream)
    cursor = 0
    for section in parsed:
        for line in section.text.splitlines():
            found = joined.find(line, cursor)
            assert found >= 0, f"{section.section_ref}: {line!r} is not in the body stream"
            cursor = found


NL = chr(10)
FF = chr(12)
#: The page-run banner exactly as the paper prints it: the part letter centred, then the
#: part's title beneath it, both at an indent no body line reaches.
BANNER = (
    "                                                   SECTION B" + NL + NL
    + "                  DEFINITIONS, GENERAL PRINCIPLES, RECOMMENDATIONS"
)


def test_the_running_part_banner_is_not_body_text():
    """`SECTION B` + the part's title is the page's running head, printed on every page.

    Measured on the shipped SAOSO (2026-10-28): 21 pages open with it, and **no** page opens
    with any other all-caps line at indent 8 or more — every other indented page-start is a
    label (`South African specific`, `Regional or other exception`), a table header or a
    wrapped sentence. Left in, it became the tail of twelve branches, telling a reader a new
    part starts and then following nothing (`saoso_text_glyphs_and_boundaries.md` §3).
    """
    text = FF.join(
        [
            # The banner is how the part letter is found, so a page that carries body text
            # opens with it — that is the shape the shipped document has.
            BANNER + NL + NL + "1. FIRST" + NL + "Nothing here yet.",
            BANNER + NL + "2. SECOND" + NL + "Operators shall do the thing.",
            # And the column-0 variant the appendix pages print.
            "SECTION B" + NL + "3. THIRD" + NL + "Operators shall do the other thing.",
        ]
    )

    sections = SaosoParser().parse(text)

    assert [s.section_ref for s in sections] == ["S1", "S2", "S3"]
    for section in sections:
        assert "SECTION B" not in section.text, section.text
        assert "DEFINITIONS, GENERAL PRINCIPLES" not in section.text, section.text


def test_a_page_that_opens_with_a_label_keeps_it():
    """The banner rule must not eat `South African specific` or a wrapped sentence."""
    text = (
        BANNER + NL + NL + "1. FIRST" + NL + "Some body." + FF
        + "                             South African specific" + NL
        + "2. SECOND" + NL + "Operators shall do the thing."
    )

    sections = SaosoParser().parse(text)

    assert "South African specific" in sections[0].text


def test_a_banner_printed_mid_page_is_dropped_too():
    """`S4.8.6` ends with the banner *after* a centred footnote, not at the page top.

    The one exception to "the banner opens the page" the shipped document has: printed
    p. 40 puts the footnote `certifiers using this standard.` above the part banner, so the
    head had to be recognised by its own title line rather than by its position.
    """
    text = (
        BANNER + NL + NL + "4.8.6. The natural reproductive ability is respected." + NL
        + "This excludes techniques that reduce the germination capacities." + NL + NL
        + BANNER + NL + NL + "4.8.7. Something else entirely."
    )

    sections = SaosoParser().parse(text)

    assert [s.section_ref for s in sections] == ["S4.8.6", "S4.8.7"]
    assert "SECTION B" not in sections[0].text, sections[0].text
    assert "DEFINITIONS, GENERAL PRINCIPLES" not in sections[0].text
