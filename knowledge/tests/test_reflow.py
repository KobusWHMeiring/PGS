"""D52 — a word hyphenated across a line break must be quotable as the reader sees it.

Measured defect (2026-10-21, UAT Scenario 10 / CHAT_ANSWER_COVERAGE_PRD.md G1–G2):
`pdftotext -layout` breaks a line inside a hyphenated word —

    The percentage of non-organic feed may not exceed 10% dry matter per ruminant
    and 15% dry matter per non-

    ruminant calculated on an annual basis.

— and the citation audit then requires a quote to contain `non- ruminant`, which no
reader writes. Two live answers were refused for quotes that were *substantively*
verbatim: the model elided with `...` rather than copy the mangled word. The corpus was
the defect, so the corpus is repaired, exactly as `columns.py` repaired the gutter: the
audit stays strict (`testing_hazards.md` §1.22).

The counts below are measured on the shipped PDFs. They are pinned per document so a
regression to a no-op fails loudly — a loss-free assertion alone passes when the
transform never runs (hazard §1.20).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from knowledge.tests.page_fixtures import pages

from knowledge.columns import apply_layout
from knowledge.extraction import extract_pages
from knowledge.reflow import join_hyphenated, reflow_pages

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = REPO_ROOT / "pgs_docs"

PDFS = {
    "saoso": "saoso-version-2.1-2026.pdf",
    "opp": "Outeniqua pgs principles, policies and procedures 2026.pdf",
    "bpp": "Basic Production Principles_ENG_PRINT.pdf",
    "landscape": "PGS Certification landscape_Final.pdf",
}

#: Measured 2026-10-21 on the four governed documents, after `de_column`. Every one is a
#: genuine compound the PDF wrapped at a line end: `post-harvest`, `in-country`,
#: `non-ruminant`, `self-assessment`, `cobalt-sulphate`, `semi-sparkling`, …
#: Re-measured 2026-10-22 after `column_bands` was narrowed to the untouched run: BPP
#: went 3 -> 5 because two more wrapped words became adjacent once the gutter stopped
#: cutting inside the left column. SAOSO and OPP are unchanged, which is the point of
#: narrowing inside the detected band rather than re-detecting.
#: narrowly inside the detected band rather than re-detecting.
#: Re-measured 2026-10-27 after the extraction started asking for `-enc UTF-8` (the OPP's
#: 66 `●` bullets came back): OPP went 4 -> 3, because PDF p4 is no longer de-columned at
#: all (`knowledge/columns.py` records why a two-band split is wrong for its 3-column
#: table). SAOSO, BPP and landscape are unchanged.
EXPECTED_WRAPS = {"saoso": 12, "opp": 3, "bpp": 5, "landscape": 1}


@pytest.fixture(scope="module")
def corpus() -> dict[str, list[str]]:
    """The shipped PDFs, de-columned — the exact pages ingest hands to the parser."""
    return {key: apply_layout(pages(key), doc_key=key)[0] for key in PDFS}


def non_space(text: str) -> Counter:
    """Every non-space, non-newline character: the loss-free invariant."""
    return Counter(text.replace(" ", "").replace("\n", ""))


def flat(text: str) -> str:
    """Exactly what `audit_citations` compares."""
    return " ".join(text.split())


# --- 1. The synthetic contract ----------------------------------------------


def test_a_word_split_by_a_line_break_becomes_one_word():
    assert (
        join_hyphenated("and 15% dry matter per non-\nruminant calculated on an annual basis.")
        == "and 15% dry matter per non-ruminant calculated on an annual basis."
    )


def test_the_hyphen_is_kept():
    """`non-\nruminant` is the printed `non-ruminant`; dropping the hyphen invents a word."""
    assert join_hyphenated("post-\nharvest pesticides") == "post-harvest pesticides"


def test_the_blank_line_between_the_halves_is_removed():
    """SAOSO prints its body double-spaced, so the halves are two paragraphs apart."""
    assert join_hyphenated("per non-\n\n\nruminant") == "per non-ruminant"


def test_a_word_split_over_three_lines_is_joined_once_per_break():
    """A printed hyphen is kept wherever it appears; `-layout` only reports printed ones.

    The module does not try to guess a typesetter's soft hyphen: a hyphen on the page
    is a hyphen on the page. What this pins is that the loop joins every break, not
    only the first.
    """
    assert join_hyphenated("cross-\n\npolli-\nnation") == "cross-polli-nation"


def test_a_hyphen_before_a_capitalised_line_is_left_alone():
    """A capital after the hyphen is a new sentence or a list item, not a word wrap."""
    page = "the pesticide is non-\nOrganic farming is different"
    assert join_hyphenated(page) is page


def test_a_hyphen_preceded_by_a_space_is_not_a_word_wrap():
    page = "the following 14 -\nitems are prohibited"
    assert join_hyphenated(page) is page


def test_a_hyphen_followed_by_a_non_letter_is_left_alone():
    page = "see appendix non-\n3 for details"
    assert join_hyphenated(page) is page


def test_a_page_with_nothing_to_join_is_the_same_object():
    page = "5.5.1. Animals shall be fed organic feed.\n\nRequirements:\n"
    assert join_hyphenated(page) is page


def test_the_join_loses_no_character():
    page = "per non-\n\nruminant calculated"
    assert non_space(join_hyphenated(page)) == non_space(page)


def test_the_join_is_idempotent():
    once = join_hyphenated("per non-\n\nruminant")
    assert join_hyphenated(once) == once


# --- 2. The corpus it was measured on ---------------------------------------


@pytest.mark.parametrize("doc_key", sorted(PDFS))
def test_exactly_the_measured_wraps_are_rejoined(corpus, doc_key):
    """Pinned per document: a detector that regresses to a no-op fails here.

    A loss-free assertion cannot catch that (hazard §1.20), and neither can a count of
    the whole corpus dragged along by one document.
    """
    _, changed = reflow_pages(corpus[doc_key])
    assert len(changed) == EXPECTED_WRAPS[doc_key]


@pytest.mark.parametrize("doc_key", sorted(PDFS))
def test_no_wrap_crosses_a_page_boundary(corpus, doc_key):
    """The measured reason a per-page pass is complete.

    `join_hyphenated` sees one page at a time, so a word hyphenated at the very bottom
    of a page and continued at the top of the next would be missed. Measured on the
    shipped PDFs: no page ends with a wrapped word, so there is no such case. If a new
    edition introduces one, this fails rather than silently leaving the mangled word.
    """
    for number, page in enumerate(corpus[doc_key][:-1], 1):
        lines = [line for line in page.split("\n") if line.strip()]
        if not lines:
            continue
        assert not lines[-1].rstrip().endswith("-"), (
            f"{doc_key} PDF p{number} ends inside a hyphenated word; reflow is per page "
            "and would not see its continuation"
        )


# --- 3. The two live refusals, on the shipped pages -------------------------


def test_the_ducks_clause_is_quotable_from_one_chunk(corpus):
    """S5.5.1 — `non-ruminant` is the word the model refused to write (G1)."""
    from knowledge.chunking import chunk_sections
    from knowledge.sections import registry

    pages, _ = reflow_pages(corpus["saoso"])
    chunks = chunk_sections(registry.get("saoso").parse("\f".join(pages)))
    carriers = [
        chunk
        for chunk in chunks
        if flat(
            "may not exceed 10% dry matter per ruminant and 15% dry matter per "
            "non-ruminant calculated on an annual basis"
        )
        in flat(chunk.text)
    ]
    assert len(carriers) == 1
    assert carriers[0].section_ref == "S5.5.1"


def test_the_seed_clause_is_quotable_from_one_chunk(corpus):
    """S4.1.1 — `post-harvest` is the word the model paraphrased around (G2)."""
    from knowledge.chunking import chunk_sections
    from knowledge.sections import registry

    pages, _ = reflow_pages(corpus["saoso"])
    chunks = chunk_sections(registry.get("saoso").parse("\f".join(pages)))
    carriers = [
        chunk
        for chunk in chunks
        if flat(
            "conventional materials may be used provided that they have not been "
            "treated with post-harvest pesticides not otherwise permitted by this Standard"
        )
        in flat(chunk.text)
    ]
    assert len(carriers) == 1
    assert carriers[0].section_ref == "S4.1.1"
