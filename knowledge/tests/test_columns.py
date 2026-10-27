"""D46 — the column-aware page transform.

These tests are the contract `knowledge/columns.py` must satisfy, and the corpus
guards that stop it silently mangling a page.

The order matters. The synthetic tests below run with no Poppler, no database and no
PDF: they describe the transform's shape. Everything after them runs on the **shipped
PDFs**, because the defect this module fixes was measured on those bytes — a fixture
that reproduced the interleaving by hand would encode the same assumption as the
transform and could not catch the real thing.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from knowledge.tests.page_fixtures import pages

from knowledge.columns import (
    PAGE_LAYOUT_EXCLUSIONS,
    apply_layout,
    column_bands,
    de_column,
)

# --- 1. The synthetic contract ----------------------------------------------

LEFT = [
    "The organic farm",
    "is an element of",
    "an environment or",
    "ecosystem. The",
    "balanced management",
    "of this system is",
    "important and it",
    "must be documented.",
]
RIGHT = [
    "A clear long term",
    "soil fertility plan",
    "must be in place",
    "on every farm and",
    "should include the",
    "mechanisms and",
    "practices that",
    "increase organic matter.",
]
PAGE = "\n".join(f"{left:<28}{right}" for left, right in zip(LEFT, RIGHT))
BAND = [(22, 28)]


def test_column_bands_finds_the_gutter():
    """The measured gutter in `PAGE` is a band covering its whitespace run."""
    bands = column_bands(PAGE)
    assert bands, "a two-column page must yield at least one band"
    start, end = bands[0]
    assert start <= BAND[0][0] and end >= BAND[0][1]


def test_columns_are_emitted_left_to_right():
    assert de_column(PAGE, bands=BAND) == "\n".join(LEFT + RIGHT)


def test_a_line_that_crosses_the_band_is_kept_whole():
    footnote = "a footnote spanning the whole width of the page"
    spanning = PAGE + "\n" + footnote.center(50)
    out = de_column(spanning, bands=BAND)
    assert footnote in [line.strip() for line in out.split("\n")], "a spanning line must not be cut"


def test_blank_runs_inside_a_column_are_preserved():
    page = "\n".join(f"{left:<28}{right}" for left, right in zip(LEFT[:4], RIGHT[:4]))
    rows = page.split("\n")
    rows.insert(2, "")
    out = de_column("\n".join(rows), bands=BAND).split("\n")
    assert out[2] == "" and out[3] == LEFT[2]


def test_no_band_returns_the_same_object():
    """The fallback is a no-op, never a guess — and not merely an equal string.

    Returning an equal-but-new string would let a caller's identity check pass a
    test while a page was silently rebuilt.
    """
    prose = "A single column of prose.\nWith no gutter anywhere.\n"
    assert de_column(prose) is prose
    assert column_bands(prose) == []


def test_the_transform_is_deterministic():
    assert de_column(PAGE, bands=BAND) == de_column(PAGE, bands=BAND)


# --- 2. The shipped corpus --------------------------------------------------

PDF_DIR = Path(__file__).resolve().parents[2] / "pgs_docs"

PDFS = {
    "saoso": "saoso-version-2.1-2026.pdf",
    "bpp": "Basic Production Principles_ENG_PRINT.pdf",
    "landscape": "PGS Certification landscape_Final.pdf",
    "opp": "Outeniqua pgs principles, policies and procedures 2026.pdf",
}

#: The pages the transform MUST change, as **PDF** page numbers — `extract_pages()[n-1]`.
#: SAOSO prints `pdf - 1` (D42), so printed 76-91 is pdf 77-92. Appendix 4 Table 1
#: (pdf 82-83) is excluded: its 4-column rows are already coherent on the raw page.
EXPECTED_TRANSFORMED_PAGES = {
    "bpp": {3, 4, 5, 6, 7, 8, 9, 10},
    "landscape": {2, 3, 4, 5, 6, 7, 8, 9},
    # pdf 4 (§3.1 committee roles) and pdf 11 (§6.5) are excluded: both are 3-column
    # tables with two gutters, so a two-band split is column-major by construction. pdf 4
    # stopped being detected on 2026-10-27 only because the 66 bullets the extraction had
    # been dropping came back (`-enc UTF-8`, `knowledge/extraction.py`) — it is now an
    # explicit exclusion, so the accident cannot come back either way.
    "opp": {12},
    "saoso": set(range(77, 93)) - {79, 81, 82, 83, 85},
}


@pytest.fixture(scope="module")
def corpus():
    """The committed pages, not a fresh extraction (D57).

    The assertions are unchanged: these are the same `pdftotext -layout` bytes the goldens
    below were measured on, read from `fixtures/pages/` so the gate needs no extractor.
    """
    return {key: pages(key) for key in PDFS}


def non_space(text: str) -> Counter:
    """The loss-free invariant: every non-space, non-newline character.

    Newlines are excluded deliberately. Reordering changes them by definition, so
    counting them reports all 32 transformed pages as total data loss and looks like
    catastrophic corruption.
    """
    return Counter(text.replace(" ", "").replace("\n", ""))


def flat(text: str) -> str:
    """Exactly what `audit_citations` compares: whitespace-normalised text.

    A raw `in` fails on a contiguous sentence because `pdftotext` breaks lines inside
    it.
    """
    return " ".join(text.split())


BPP_SENTENCE = (
    "Animal manure must be preferably composted prior to application, and must be "
    "sourced from farms under organic management, or from extensive farming practice."
)
RAW_MANURE_RULE = (
    "raw manure is only permitted if applied a minimum 60 days before harvesting a crop "
    "that might come into contact with the manure"
)
APPENDIX_2_CONDITION = (
    "Shall not constitute the main source of nitrogen in the absence of complimentary "
    "and additional nitrogen generating practices on farm and shall not be from "
    "conventional intensive livestock production systems without prior permission "
    "from the control body"
)


def chunks_of(pages: list[str], scheme: str) -> list:
    from knowledge.chunking import chunk_sections
    from knowledge.sections import registry

    return chunk_sections(registry.get(scheme).parse("\f".join(pages)))


def test_the_bpp_manure_sentence_is_quotable_from_one_chunk(corpus):
    """Spans PDF pages 4→5, so it is only meaningful on post-ingest chunk text."""
    chunks = chunks_of([de_column(page) for page in corpus["bpp"]], "heading")
    carriers = [c for c in chunks if flat(BPP_SENTENCE) in flat(c.text)]
    assert len(carriers) == 1
    assert carriers[0].anchor == "general-principles"


def test_the_appendix_2_condition_is_quotable(corpus):
    chunks = chunks_of([de_column(page) for page in corpus["saoso"]], "saoso")
    carriers = [c for c in chunks if flat(APPENDIX_2_CONDITION) in flat(c.text)]
    assert len(carriers) == 1
    assert carriers[0].section_ref == "Appendix 2"
    assert carriers[0].page == 76  # printed page, D42


def test_the_bpp_raw_manure_rule_is_quotable(corpus):
    """The sentence a farmer asks about when they ask "can I use horse manure?".

    Default detection split it: a left-column list item on BPP PDF 4 overflows into the
    maximal band, so rule 2 kept that line whole and stranded the right column's
    `harvesting a crop…` line in the left block. The measured (40, 42) override in
    `PAGE_LAYOUT_BANDS` makes it contiguous. Pinned because the success-gate sentence
    passing did not catch it.
    """
    pages, _ = apply_layout(corpus["bpp"], doc_key="bpp")
    chunks = chunks_of(pages, "heading")
    carriers = [c for c in chunks if flat(RAW_MANURE_RULE) in flat(c.text)]
    assert len(carriers) == 1
    assert carriers[0].anchor == "general-principles"


def test_the_bpp_page_4_band_override_is_applied(corpus):
    """The override is data in `PAGE_LAYOUT_BANDS`, so a regression in `apply_layout`
    fails here even if `de_column` still works on its own."""
    pages, _ = apply_layout(corpus["bpp"], doc_key="bpp")
    assert flat(RAW_MANURE_RULE) in flat(pages[3])


@pytest.mark.parametrize("doc_key", sorted(PDFS))
def test_no_non_space_character_is_lost_on_any_page(corpus, doc_key):
    losses = [
        number
        for number, page in enumerate(corpus[doc_key], 1)
        if non_space(page) != non_space(de_column(page))
    ]
    assert losses == []


@pytest.mark.parametrize("doc_key", sorted(PDFS))
def test_exactly_the_expected_pages_are_transformed(corpus, doc_key):
    # Through `apply_layout`, because an excluded page is unchanged by the *pipeline*,
    # not by the pure function: `de_column` alone would happily reorder the TOC.
    _, changed = apply_layout(corpus[doc_key], doc_key=doc_key)
    assert set(changed) == EXPECTED_TRANSFORMED_PAGES[doc_key]


@pytest.mark.parametrize("doc_key", sorted(PDFS))
def test_a_second_pass_still_preserves_every_character(corpus, doc_key):
    """The transform is not idempotent, so this is the invariant that must hold.

    Measured: a second pass is a no-op on some pages and reorders others further (the
    landscape and BPP both have such pages). Ingest applies it exactly once; a second
    application still must not lose a character.
    """
    for page in corpus[doc_key]:
        once = de_column(page)
        assert non_space(once) == non_space(de_column(once))


def test_the_transform_is_not_assumed_to_be_idempotent(corpus):
    """Measured, not feared: landscape PDF 4 gains bands on a second pass.

    Pinned so nobody "fixes" the pipeline by running it twice, and so the single-pass
    contract in `ingest_standard` has evidence behind it.
    """
    page = corpus["landscape"][3]
    once = de_column(page)
    assert de_column(once) != once


@pytest.mark.parametrize(
    "doc_key,pages",
    [("saoso", [40, 60]), ("opp", [1, 6, 8]), ("bpp", [1, 2])],
)
def test_single_column_control_pages_are_byte_identical(corpus, doc_key, pages):
    for number in pages:
        assert de_column(corpus[doc_key][number - 1]) == corpus[doc_key][number - 1]


def test_excluded_pages_are_byte_identical(corpus):
    for doc_key, exclusions in PAGE_LAYOUT_EXCLUSIONS.items():
        fixed, changed = apply_layout(corpus[doc_key], doc_key=doc_key)
        for number, reason in exclusions.items():
            assert fixed[number - 1] == corpus[doc_key][number - 1], (
                f"{doc_key} pdf {number} must not be transformed: {reason}"
            )
            assert number not in changed


def test_every_detected_page_is_either_transformed_or_excluded(corpus):
    """The silent failure this whole PRD exists to prevent.

    A page that is column-laid-out and falls between the two lists would be silently
    skipped — coverage would look complete and one document's text would stay
    interleaved.
    """
    for doc_key, pages in corpus.items():
        for number, page in enumerate(pages, 1):
            if not column_bands(page):
                continue
            excluded = number in PAGE_LAYOUT_EXCLUSIONS.get(doc_key, {})
            transformed = number in EXPECTED_TRANSFORMED_PAGES[doc_key]
            assert excluded or transformed, f"{doc_key} pdf {number} is unaccounted for"
