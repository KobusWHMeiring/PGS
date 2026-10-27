"""The document's own references: resolved to a branch, or left as text.

A reference is a claim by the document about its own structure (`See Section B – 5`, `Appendix 6b`,
`Appendices 2`). Three properties matter and each is a test below:

1. **Nothing is guessed.** A reference resolves to a branch the tree actually renders, or it stays
   text. `Section A – 2.3` is Part A, which the corpus does not hold: it must go to the page's
   missing-sections note and **never** to `S2`, which is a different part entirely (measured trap,
   `READER_STRUCTURE_PRD` §1.3).
2. **The part is data, not a hard-coded letter.** The part a branch belongs to comes from the printed
   TOC; a document with no TOC has no parts, so an unqualified `Section n` there is undecidable and
   stays text.
3. **A segment never changes a word.** `"".join(segment.text …)` reproduces the paragraph, over every
   passage of the shipped SAOSO — the reader may add targets, never text (`build_principles.md` §I's
   cousin: the citation audit reads the corpus, the page reads segments).

The corpus-level test at the end ingests the shipped SAOSO from the committed pages (`D57`), because
the inventory it asserts (39 mentions → 30 links, 9 plain) is a fact about the real document.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.concordance import build_concordance
from knowledge.ingest import ingest_standard
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.passages import Heading, RowHeading, Term, passage_blocks
from knowledge.reading import reading_chunks
from knowledge.references import (
    ReferenceIndex,
    Segment,
    annotate,
    build_reference_index,
    segments_for,
)
from knowledge.tests.page_fixtures import stub_ingest_extraction

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
SAOSO_PDF = REPO_ROOT / "pgs_docs" / "saoso-version-2.1-2026.pdf"
CORPUS_SOURCE = "pgs_docs/saoso-version-2.1-2026.pdf"


@pytest.fixture(autouse=True)
def committed_extraction(monkeypatch):
    """The gate has no PDF reader (D57); the committed pages are the input."""
    stub_ingest_extraction(monkeypatch)


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)


#: The printed TOC as `StandardDocument.toc` stores it: part A and part B both exist.
TOC = [
    {"part": "A", "kind": "SECTION", "label": "1", "title": "Introduction", "printed_page": 4},
    {"part": "B", "kind": "SECTION", "label": "1", "title": "Definitions", "printed_page": 22},
    {"part": "B", "kind": "SECTION", "label": "5", "title": "Animal Husbandry", "printed_page": 41},
    {"part": "B", "kind": "SECTION", "label": "6", "title": "Wild Harvesting", "printed_page": 52},
]


def _document(standard_set, toc=None, title="SAOSO Standard"):
    return StandardDocument.objects.create(
        standard_set=standard_set,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title=title,
        version="2.1",
        source_file=CORPUS_SOURCE,
        sha256="f" * 64,
        section_scheme="saoso",
        toc=TOC if toc is None else toc,
    )


def _chunk(document, section_ref, text, page=41, heading_path=""):
    return DocumentChunk.objects.create(
        document=document,
        section_ref=section_ref,
        heading_path=heading_path,
        page=page,
        text=text,
    )


@pytest.fixture
def corpus(standard_set):
    """Two sections, two appendices, one table branch — enough for every printed shape."""
    document = _document(standard_set)
    _chunk(document, "S5.1.9", "Animals must have access to pasture.")
    _chunk(document, "S6.1", "Harvesting is permitted where the plant is wild.")
    _chunk(document, "Appendix 2", "Farmyard manure, slurry and urine")
    _chunk(
        document,
        "Appendix 6a",
        "Minimum surface areas for laying hens indoors.",
        heading_path="Minimum Surface Areas for Laying Hens Indoors",
    )
    _chunk(
        document,
        "Appendix 6b",
        "Minimum surface areas for livestock housing.",
        heading_path="Minimum Surface Areas Indoors and Outdoors and other Characteristics of Housing",
    )
    _chunk(document, "Appendix 4. Table 1", "Permitted products.")
    _chunk(document, "Appendix 4. Table 2", "Restricted products.")
    return document


def _index(document) -> ReferenceIndex:
    return build_reference_index(document)


def _resolved(text, document, *, open_branch="S6"):
    index = _index(document)
    return [match for match in segments_for(text, index, open_branch=open_branch) if match.branch or match.fragment]


def test_a_part_letter_selects_the_part_it_names(corpus):
    index = _index(corpus)

    segments = segments_for("See Section B – 5 Animal Husbandry 5.3, 5.5, 5.6.", index, open_branch="S6")
    links = [segment for segment in segments if segment.branch]

    assert len(links) == 1
    assert links[0].text == "Section B – 5"
    assert links[0].branch == index.branches["S5"].anchor
    assert links[0].fragment == index.branches["S5"].anchor


def test_part_a_is_printed_and_not_in_the_corpus(corpus):
    """The measured trap: a naive `S<n>` mapping sends this to Section 2, a different part."""
    index = _index(corpus)
    segments = segments_for("See Section A – 2.3 for the opening provisions.", index, open_branch="S6")
    links = [segment for segment in segments if segment.fragment]

    assert len(links) == 1
    assert links[0].branch == ""
    assert links[0].fragment == "not-in-corpus"
    assert "not in this corpus" in links[0].title.lower()
    assert links[0].branch != index.branches["S5"].anchor


def test_a_section_the_corpus_does_not_hold_is_not_the_missing_note(corpus):
    """Part B, number 9: there is no `S9` branch, and Part A is not what it means."""
    assert _resolved("See Section B – 9.", corpus) == []


def test_an_unqualified_section_resolves_inside_its_own_part(corpus):
    """`Section 4.6.2` is printed in part B, where `Section 4` means that part's section 4."""
    index = _index(corpus)
    segments = segments_for("Section 5.3 applies.", index, open_branch="S6")
    links = [segment for segment in segments if segment.branch]

    assert len(links) == 1
    assert links[0].text == "Section 5.3"
    assert links[0].branch == index.branches["S5"].anchor


def test_a_document_with_no_toc_has_no_parts(standard_set):
    """No TOC means no part, and an unqualified `Section n` cannot be decided — so it stays text."""
    document = _document(standard_set, toc=[])
    _chunk(document, "S2.1", "Ecosystem management.")

    segments = segments_for("Section 2.1 applies.", _index(document), open_branch="S2")

    assert segments == (Segment("Section 2.1 applies."),)


def test_an_appendix_resolves_by_its_letter_or_its_printed_title(corpus):
    index = _index(corpus)

    by_letter = [s for s in segments_for("Appendix 6b applies.", index) if s.branch]
    by_words = [s for s in segments_for("Appendix 6 Minimum Surface Areas Indoors and", index) if s.branch]
    bare = segments_for("Appendix 6 applies.", index)

    assert [s.branch for s in by_letter] == [index.branches["Appendix 6b"].anchor]
    assert [s.branch for s in by_words] == [index.branches["Appendix 6b"].anchor]
    assert by_words[0].text == "Appendix 6 Minimum Surface Areas Indoors and"
    assert all(s.branch == "" and s.fragment == "" for s in bare), "6a or 6b is undecidable"


def test_two_tables_are_named_and_not_guessed(corpus):
    """Bare `Appendix 4` (8 mentions) carries a tooltip naming both tables, and is not a link."""
    index = _index(corpus)
    segments = segments_for("Appendix 4 lists both.", index)
    appendix_four = next(segment for segment in segments if segment.text == "Appendix 4")

    assert appendix_four.branch == ""
    assert "Table 1" in appendix_four.title and "Table 2" in appendix_four.title

    named = [s for s in segments_for("Appendix 4 Table 1 and Appendix 4 Table 2.", index) if s.branch]
    assert [s.branch for s in named] == [
        index.branches["Appendix 4. Table 1"].anchor,
        index.branches["Appendix 4. Table 2"].anchor,
    ]


def test_a_reference_to_the_open_branch_is_not_a_link(corpus):
    """The real corpus has 0 of these today, so this is the only guard the rule has."""
    segments = segments_for("Appendix 2 applies to inputs.", _index(corpus), open_branch="Appendix 2")

    assert len(segments) == 1
    assert segments[0].branch == "" and segments[0].fragment == ""


def test_a_reference_to_a_branch_the_document_does_not_have_stays_text(corpus):
    """The negative control: the BPP prints `Appendix 5`, the landscape `Appendix 9`; neither exists."""
    index = _index(corpus)

    for text in ("See Appendix 5.", "See Appendix 9."):
        segments = segments_for(text, index)
        assert segments == (Segment(text),), f"{text!r} produced a target"


def test_an_empty_index_leaves_the_text_alone():
    assert segments_for("Section 4.6.2", ReferenceIndex({}, {})) == (Segment("Section 4.6.2"),)


def test_segments_never_change_a_word(corpus):
    """Joining the segments reproduces the paragraph, punctuation and all."""
    index = _index(corpus)
    text = (
        "Inputs listed in Appendix 2 are permitted; see Section A – 2.3 and Section 5.3, then "
        "Appendix 6a and Appendix 4 for the rest."
    )

    segments = segments_for(text, index, open_branch="S6")

    assert "".join(segment.text for segment in segments) == text
    assert any(segment.branch for segment in segments)


def test_matches_are_sorted_and_never_overlap(corpus):
    index = _index(corpus)
    text = "Section B – 5 Section 5.3 Appendix 4 Table 2 Appendix 6b"

    segments = segments_for(text, index, open_branch="S6")
    positions = []
    cursor = 0
    for segment in segments:
        positions.append(text.index(segment.text, cursor))
        cursor = positions[-1] + len(segment.text)

    assert cursor == len(text)


def test_structure_blocks_are_never_segmented(corpus):
    """A printed heading is the document naming itself and a headword is not a sentence."""
    blocks = (
        Heading("APPENDICES"),
        Term("ACB"),
        RowHeading("Guano"),
        *passage_blocks("See Appendix 2."),
    )

    annotated = annotate(blocks, _index(corpus), open_branch="S6")

    for block in annotated[:3]:
        assert getattr(block, "segments", ()) == ()
    assert any(segment.branch for block in annotated[3:] for segment in block.segments)


# --- The shipped corpus -------------------------------------------------------

#: The measured inventory (`scripts/probe_reader_structure.py`, 2026-10-27): 10 section references
#: and 29 appendix mentions, 30 of which resolve to a branch and 9 of which cannot.
EXPECTED_MENTIONS = 39
EXPECTED_LINKS = 30
EXPECTED_PLAIN = 9


def test_the_shipped_corpus_resolves_as_measured(standard_set):
    """One ingest (six seconds), three facts: the inventory, the two traps, and losslessness."""
    ingest_standard(pdf_path=SAOSO_PDF, standard_set=standard_set, doc_key="saoso", embed=False)
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    index = build_reference_index(document)
    concordance = build_concordance(document)

    branch_of = {
        chunk.pk: section.key for section in concordance.sections for chunk, _anchor in section.passages
    }
    links = plain = 0
    part_a = None

    for chunk, _anchor in [(chunk, anchor) for section in concordance.sections for chunk, anchor in section.passages]:
        text = " ".join(chunk.text.split())
        segments = segments_for(text, index, open_branch=branch_of[chunk.pk])
        assert "".join(segment.text for segment in segments) == text
        for segment in segments:
            if segment.branch:
                links += 1
            elif segment.fragment == "not-in-corpus":
                links += 1
                part_a = segment
            elif segment.title:
                plain += 1

    assert links == EXPECTED_LINKS
    assert plain == EXPECTED_PLAIN
    assert links + plain == EXPECTED_MENTIONS

    assert part_a is not None, "`Section A – 2.3` did not reach the missing-section note"
    assert part_a.branch == ""
    assert part_a.text == "Section A – 2.3"
    assert part_a.fragment == "not-in-corpus"

    # Spot-check the resolutions a reader will meet, by the paper's own words.
    text = [chunk.text for chunk in reading_chunks(document)]
    joined = " ".join(" ".join(item.split()) for item in text)
    assert "Section B – 5 Animal Husbandry" in joined
    assert "Appendix 6 Minimum Surface Areas Indoors and Outdoors and other" in joined
    assert "defined in Section B Appendix 6b" in joined

    six_b = segments_for("Appendix 6 Minimum Surface Areas Indoors and", index)
    assert [s.branch for s in six_b if s.branch] == [index.branches["Appendix 6b"].anchor]
