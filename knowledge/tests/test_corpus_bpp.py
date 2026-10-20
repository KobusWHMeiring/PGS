"""The BPP artefact: reviewed, traceable, and equivalent to the PDF path (D53).

This is the guard that makes a transcription trustworthy. The artefact is *derived* from
the PDF, so the tests here answer four questions in order:

1. **Is it the same document?** The header's sha256 is the PDF's, and the artefact carries
   every character the PDF path's sections produce — the difference is exactly the
   reviewed edits, and nothing else.
2. **Is every block on the page it names?** A block that cannot be found on paper is a
   quote nobody can verify, which is the one thing the chatbot must never emit.
3. **Was every correction necessary, and applied?** Each `CorpusEdit` is data: its
   `original` must be in the PDF-derived text for that page (so the defect was real) and
   its `replacement` must be in the artefact (so the fix landed). A dropped edit with no
   replacement must actually be gone.
4. **Does it still say what the corpus has to say?** The sentences the chat tests and the
   UATs depend on are asserted contiguous here, because a transcription that mangles one
   of them is worse than the extractor defect it replaced.

The edit count is a ratchet, not a budget: five corrections in thirteen pages is the
review doing its job, and the number may only go down without a reason.
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

import pytest

from knowledge.columns import apply_layout
from knowledge.corpus import CORPUS_EDITS, flat, load_document
from knowledge.extraction import extract_pages, sha256_of
from knowledge.reflow import reflow_pages
from knowledge.sections.heading import HeadingParser
from knowledge.tests.test_columns import BPP_SENTENCE, RAW_MANURE_RULE

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF = REPO_ROOT / "pgs_docs" / "Basic Production Principles_ENG_PRINT.pdf"
ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "bpp.md"

#: Measured 2026-10-22: five corrections. Raises only with a reason recorded in the PRD.
MAX_EDITS = 5


@pytest.fixture(scope="module")
def document():
    return load_document(ARTEFACT)


@pytest.fixture(scope="module")
def pdf_pages():
    """Both renderings: the artefact is drafted from whichever page is word-clean."""
    laid, _ = apply_layout(extract_pages(PDF), doc_key="bpp")
    laid, _ = reflow_pages(laid)
    raw, _ = reflow_pages(extract_pages(PDF, mode="raw"))
    return laid, raw


@pytest.fixture(scope="module")
def pdf_sections(pdf_pages):
    laid, _ = pdf_pages
    return HeadingParser().parse("\f".join(laid))


def chars(text: str) -> collections.Counter:
    return collections.Counter("".join(text.split()))


def body_text(document) -> str:
    """Every body block, whitespace-normalised — what `audit_citations` compares."""
    return flat(" ".join(block.text for block in document.blocks))


def squash(text: str) -> str:
    """All whitespace removed.

    Glue repair inserts spaces the page does not have (`Sourcedlocallyfromneighbouring` ->
    `Sourced locally from neighbouring`), so a traceable block is one whose *characters*
    appear in order on the page. Order is still checked; only spacing is forgiven.
    """
    return "".join((text or "").split())


def on_page(block: str, pages: list[str], start: int, span: int = 3) -> bool:
    """Is `block` a contiguous slice of the pages from `start` onwards?"""
    needle = squash(block)
    return any(
        needle in squash(" ".join(pages[start - 1 : start - 1 + width]))
        for width in range(1, span + 1)
    )


# --- 1. It is the same document ---------------------------------------------


def test_the_header_is_the_shipped_pdf(document):
    assert document.source == "pgs_docs/Basic Production Principles_ENG_PRINT.pdf"
    assert document.sha256 == sha256_of(PDF)
    assert document.generator.startswith("knowledge corpusgen")


def test_the_page_markers_are_monotonic_and_inside_the_document(document, pdf_pages):
    pages = [block.page for block in document.blocks]
    assert pages == sorted(pages), "a page marker went backwards"
    assert max(pages) <= len(pdf_pages[0])
    assert len(set(pages)) >= 8, "the artefact lost most of its page markers"


def test_the_artefact_carries_every_character_the_pdf_path_produces(
    document, pdf_sections
):
    """The difference must be exactly the reviewed edits — no silent loss, no invention.

    Character multiset rather than order, because the edits *move* text (a footnote) as
    well as re-space it. Order is covered by the traceability test below.
    """
    expected = collections.Counter()
    for section in pdf_sections:
        # Body only: the artefact carries headings as Markdown, and a heading is
        # structure rather than text (`body_text` excludes them on both sides).
        expected.update(chars(section.text.partition(chr(10))[2]))
    for edit in CORPUS_EDITS["bpp"]:
        if edit.kind == "move":
            continue  # the same characters at a new position
        expected.subtract(chars(edit.original))
        expected.update(chars(edit.replacement))
    expected = +expected

    actual = chars(body_text(document))
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"the artefact dropped characters: {dict(missing)}"
    assert not extra, f"the artefact invented characters: {dict(extra)}"


def test_the_artefact_keeps_the_pdf_paths_section_identity(document, pdf_sections):
    """Anchors, printed pages, refs and heading paths must not drift in a transcription.

    Text may differ where a review corrected it; identity may not, because identity is
    what a citation resolves through.
    """
    identity = lambda section: (  # noqa: E731 - a one-line tuple, used twice
        section.section_ref,
        section.anchor,
        section.page,
        section.heading_path,
    )
    assert [identity(s) for s in document.sections] == [
        identity(s) for s in pdf_sections
    ]


# --- 2. Every block is on the page it names ---------------------------------


def test_every_block_is_on_the_page_it_names(document, pdf_pages):
    """With one declared exception: a reviewed re-spacing, which no page contains.

    A block is accepted when it is a contiguous slice of the pages starting at its marked
    page (a paragraph may cross one page break), or when it contains a replacement this
    review declared. Anything else is text nobody can find on paper.
    """
    laid, raw = pdf_pages
    # The review declares which characters it removed; a block that is on the page *after*
    # those removals is traceable. The removals themselves are justified by
    # `test_each_edit_was_necessary`, so this cannot become a place to hide text.
    drops = collections.defaultdict(list)
    for edit in CORPUS_EDITS["bpp"]:
        if edit.kind == "drop":
            drops[edit.page].append(squash(edit.original))
    replacements = collections.defaultdict(list)
    for edit in CORPUS_EDITS["bpp"]:
        if edit.replacement:
            replacements[edit.page].append(squash(edit.replacement))

    def traceable(block) -> bool:
        for pages in (laid, raw):
            if on_page(block.text, pages, block.page):
                return True
            # A block is still on paper when the only difference is a character the
            # review declared dropped (`02`, the bare page stamp). Try each occurrence,
            # so removing `02` cannot silently eat the `02` inside `2022`.
            needle = squash(block.text)
            window = squash(" ".join(pages[block.page - 1 : block.page + 2]))
            for drop in drops[block.page]:
                for match in re.finditer(re.escape(drop), window):
                    candidate = window[: match.start()] + window[match.end() :]
                    if needle in candidate:
                        return True
        return False

    untraceable = []
    for block in document.blocks:
        if traceable(block):
            continue
        if any(replacement in squash(block.text) for replacement in replacements[block.page]):
            continue
        untraceable.append((block.page, flat(block.text)[:90]))
    assert untraceable == []


# --- 3. Every correction was necessary, and applied -------------------------


@pytest.mark.parametrize(
    "edit", CORPUS_EDITS["bpp"], ids=lambda e: f"page-{e.page}"
)
def test_each_edit_was_necessary(edit, pdf_pages):
    """The `original` must really be in the PDF-derived text for that page."""
    laid, raw = pdf_pages
    assert flat(edit.original) in flat(laid[edit.page - 1]) or flat(
        edit.original
    ) in flat(raw[edit.page - 1]), (
        f"page {edit.page}: the edit claims to repair {edit.original[:60]!r}, which is "
        "not in the PDF's text. A stale edit is a change nobody can justify."
    )


def page_text(document, page: int) -> str:
    return flat(" ".join(block.text for block in document.blocks if block.page == page))


@pytest.mark.parametrize(
    "edit", CORPUS_EDITS["bpp"], ids=lambda e: f"page-{e.page}"
)
def test_each_edit_was_applied(edit, document):
    if edit.replacement:
        assert flat(edit.replacement) in body_text(document)
        return
    # A dropped original must be gone from *its own page* — the same text may legitimately
    # survive elsewhere (the four-principle strip is kept on page 6 and dropped on 8/10) —
    # and it must not be found as a substring of a longer number (`02` inside `2022`).
    pattern = r"(?<!\w)" + re.escape(flat(edit.original)) + r"(?!\w)"
    assert not re.search(pattern, page_text(document, edit.page)), (
        f"page {edit.page}: the edit drops {edit.original[:60]!r} but it is still there"
    )


def test_the_reviewed_edits_do_not_grow_without_a_reason():
    assert len(CORPUS_EDITS["bpp"]) <= MAX_EDITS


# --- 4. The sentences the product depends on --------------------------------


@pytest.mark.parametrize(
    "sentence",
    [
        BPP_SENTENCE,
        RAW_MANURE_RULE,
        "The use of synthetic fertilisers (agro-chemicals) is expressly prohibited.",
        "Preventative methods (disruption, elimination of habitat and access to facilities);",
    ],
    ids=["manure", "raw-manure-rule", "agro-chemicals", "preventative"],
)
def test_the_sentences_the_chatbot_quotes_are_contiguous(document, sentence):
    """G7's acceptance, and a regression guard on the whole transcription.

    Each of these was either refused live or is pinned by a chat test; a transcription
    that splits one is worse than the defect it replaced.
    """
    text = flat(" ".join(section.text for section in document.sections))
    assert flat(sentence) in text


def test_a_block_names_the_only_page_it_could_have_come_from(document, pdf_pages):
    """A dropped page marker must fail, even though a block may span three pages.

    The span allowance above means a block from page 7 would still be "found" from page 6,
    so deleting a marker went unnoticed until this test existed. A block that fits
    entirely on exactly one page has no such ambiguity: if it is on page 7 and says page 6,
    the provenance is wrong.
    """
    laid, raw = pdf_pages
    wrong = []
    for block in document.blocks:
        needle = squash(block.text)
        hits = [
            number
            for number in range(1, len(laid) + 1)
            if needle in squash(laid[number - 1]) or needle in squash(raw[number - 1])
        ]
        if len(hits) == 1 and hits[0] != block.page:
            wrong.append((block.page, hits[0], flat(block.text)[:60]))
    assert wrong == []


# --- 5. Ten reviewed examples: quotable from exactly one chunk ---------------
#
# Each is a sentence a farmer would actually ask about, copied *from the artefact* rather
# than from memory — the twelfth candidate in the first draft of this list was rejected
# because the BPP prints "Employment practice should be", singular, and a paraphrase would
# have asserted against text the document does not contain.
#
# Why one chunk matters: a section may be split by the chunker, and a quote that straddles
# two chunks is refused by the audit exactly as if it were invented. These are the
# BPP's substantive requirements, so each must survive chunking on its own.

REVIEWED_QUOTES: tuple[tuple[str, str], ...] = (
    (
        "synthetic-fertilisers",
        "The use of synthetic fertilisers (agro-chemicals) is expressly prohibited.",
    ),
    (
        "gm-seed",
        "Any GM seeds or seedlings are expressly forbidden in organic agriculture.",
    ),
    (
        "organic-seed-verifiable",
        "Purchase organic seeds or seedlings from a verifiable source.",
    ),
    (
        "conventional-seed-approval",
        "If organic seeds or seedlings are not available, conventionally grown "
        "seed/seedlings may be used with the approval of the PGS assessment team "
        "(notifiable exemption within a stipulated time frame).",
    ),
    (
        "landless-husbandry",
        "Landless animal husbandry systems are prohibited;",
    ),
    (
        "daily-pasture-access",
        "All animals shall have unrestricted and daily access to pasture or a "
        "soil-based open-air area;",
    ),
    (
        "laying-hens-rest",
        "For laying hens, a minimum daily rest period of eight continuous hours without "
        "artificial light shall be respected.",
    ),
    (
        "breeding-stock-ten-percent",
        "Breeding stock may be brought in from conventional farms to a yearly maximum of "
        "10% of the adult animals of the same species on the farm.",
    ),
    (
        "cleaning-agents",
        "Only cleaning and disinfecting agents approved for use in organic production may "
        "be used;",
    ),
    (
        "feed-from-farm",
        "More than 50% of the feed shall come from the farm unit itself,",
    ),
)


@pytest.mark.parametrize(
    "label,sentence", REVIEWED_QUOTES, ids=[label for label, _ in REVIEWED_QUOTES]
)
def test_a_reviewed_example_is_quotable_from_exactly_one_chunk(document, label, sentence):
    from knowledge.chunking import chunk_sections

    chunks = chunk_sections(document.sections)
    carriers = [chunk for chunk in chunks if flat(sentence) in flat(chunk.text)]
    assert len(carriers) == 1, (
        f"{label}: expected exactly one chunk to carry the sentence, found "
        f"{len(carriers)}. A quote that straddles a chunk boundary is refused by the "
        "citation audit exactly as if it were invented."
    )
    assert carriers[0].anchor == "general-principles"
