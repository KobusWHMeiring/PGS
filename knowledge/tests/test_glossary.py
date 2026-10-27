"""A defined word, and the place the document defines it.

`S1` renders as a glossary and every term in it was dead text. This module derives the list from the
document's own glossary branch — the `Term` blocks the layout already finds there — and gives each
definition an id, so a link can land on the definition rather than on the top of a 21 000-character
branch.

**The list is derived and the review is the rejection list** (D70.7). Measured 2026-10-27: `S1` holds
78 `Term` blocks and **71 distinct headwords**; the seven repeats are the chunk overlap the reader
already trims, so deriving from the rendered blocks yields unique headwords and unique ids. The
hand-typed alternative — 71 strings — is exactly the data that goes stale without a test noticing.

Two rules are load-bearing and each is a test: **once per term per passage**, and **no glossary links
while the glossary branch is open** (the definitions are on that page already, and 71 self-links
would make `S1` the most link-studded page in the product).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.concordance import build_concordance
from knowledge.glossary import (
    GLOSSARY_BRANCH,
    REJECTED,
    GlossaryEntry,
    _reviewed,
    glossary_entries,
    with_term_anchors,
)
from knowledge.ingest import ingest_standard
from knowledge.models import StandardDocument, StandardSet
from knowledge.passages import (
    Heading,
    ListBlock,
    ListItem,
    Paragraph,
    Term as TermBlock,
    passage_blocks,
    row_blocks,
)
from knowledge.references import ReferenceIndex, Target, annotate, segments_for
from knowledge.tests.page_fixtures import stub_ingest_extraction

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
SAOSO_PDF = REPO_ROOT / "pgs_docs" / "saoso-version-2.1-2026.pdf"
CORPUS_SOURCE = "pgs_docs/saoso-version-2.1-2026.pdf"

S1_TEXT = (
    "1. DEFINITIONS\n\n"
    "ACB\n\n"
    "Accredited Certification Body. Accredited to ISO 17065, SANS 17065 or international "
    "equivalent.\n\n"
    "Soil\n\nThe upper layer of earth in which plants grow.\n\n"
    "Conversion Period\n\nThe time between the start of organic management and the certification "
    "of the product."
)


@pytest.fixture(autouse=True)
def committed_extraction(monkeypatch):
    stub_ingest_extraction(monkeypatch)


def _entries(text: str = S1_TEXT) -> tuple[GlossaryEntry, ...]:
    return glossary_entries(CORPUS_SOURCE, passage_blocks(text), "s1")


def _index() -> ReferenceIndex:
    return ReferenceIndex(
        branches={
            "S1": Target(key="S1", anchor="s1", title="1. Definitions"),
            "S6": Target(key="S6", anchor="s6", title="6. Wild Harvesting"),
        },
        parts={},
    )


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)


def _terms(entries) -> dict[str, GlossaryEntry]:
    return {entry.term: entry for entry in entries}


def test_the_glossary_branch_is_reviewed_data():
    """Which section defines a document's words is a fact about the document, not a guess."""
    assert GLOSSARY_BRANCH[CORPUS_SOURCE] == "S1"
    assert isinstance(REJECTED[CORPUS_SOURCE], tuple)


def test_entries_are_the_terms_the_branch_defines():
    entries = _entries()

    assert [entry.term for entry in entries] == ["ACB", "Soil", "Conversion Period"]
    assert [entry.slug for entry in entries] == ["acb", "soil", "conversion-period"]
    assert [entry.fragment for entry in entries] == ["term-acb", "term-soil", "term-conversion-period"]
    assert all(entry.branch_anchor == "s1" for entry in entries)


def test_a_term_repeated_by_the_chunk_overlap_is_one_entry():
    """The overlap is trimmed before this runs; the guard is that a repeat cannot double an id."""
    entries = _entries(S1_TEXT + "\n\nSoil\n\nThe upper layer of earth in which plants grow.")

    assert [entry.term for entry in entries].count("Soil") >= 1
    assert len({entry.slug for entry in entries}) == len(entries)


def test_a_document_with_no_glossary_branch_has_no_entries():
    assert glossary_entries("pgs_docs/unknown.pdf", passage_blocks(S1_TEXT), "s1") == ()


def test_a_rejection_that_matches_nothing_is_a_stale_review():
    """With today's empty rejection list this is the only way the guard stays alive."""
    with pytest.raises(ValueError, match="Not A Term"):
        _reviewed(("ACB", "Soil"), ("Not A Term",))

    assert _reviewed(("ACB", "Soil"), ()) == ("ACB", "Soil")
    assert _reviewed(("ACB", "Soil"), ("Soil",)) == ("ACB",)


def test_each_definition_gets_its_own_id():
    blocks = passage_blocks(S1_TEXT)

    anchored = with_term_anchors(blocks)

    terms = [block for block in anchored if block.kind == "term"]
    assert [term.anchor for term in terms] == ["term-acb", "term-soil", "term-conversion-period"]
    assert all(getattr(block, "anchor", "") == "" for block in anchored if block.kind != "term")


def test_a_definition_link_lands_on_the_definition():
    entries = _terms(_entries())

    segments = segments_for(
        "See ACB for the body that certifies.", _index(), terms=entries, open_branch="S6"
    )
    link = next(segment for segment in segments if segment.branch)

    assert link.text == "ACB"
    assert link.branch == "s1"
    assert link.fragment == "term-acb"


def test_one_link_per_term_per_passage():
    """`Soil` nineteen times in a branch must not become nineteen links.

    The limit is per **passage**, so it holds across the paragraphs and list items of one passage —
    which is why the `seen` set is created by `annotate()`, not by the scan.
    """
    entries = _terms(_entries())
    blocks = (
        Paragraph("Soil texture improves Soil structure, and Soil is not a nutrient."),
        Paragraph("A Soil test is required."),
        ListBlock(
            style="lower-alpha",
            start=1,
            items=(ListItem(marker="a", text="Soil must be sampled."),),
        ),
    )

    annotated = annotate(blocks, _index(), terms=entries, open_branch="S6")

    links = [segment for block in annotated for segment in getattr(block, "segments", ()) if segment.branch]
    item_links = [
        link
        for block in annotated
        if block.kind == "list"
        for item in block.items
        for link in item.segments
        if link.branch
    ]
    assert [link.text for link in links] == ["Soil"]
    assert item_links == []


def test_the_longest_term_wins():
    entries = _terms(_entries())

    segments = segments_for(
        "The Conversion Period is two years; the Conversion Stage is not a term.", _index(), terms=entries, open_branch="S6"
    )
    links = [segment for segment in segments if segment.branch]

    assert [link.text for link in links] == ["Conversion Period"]
    assert "Stage" not in "".join(link.text for link in links)


def test_matching_is_case_insensitive():
    entries = _terms(_entries())

    segments = segments_for("the acb decides.", _index(), terms=entries, open_branch="S6")
    links = [segment for segment in segments if segment.branch]

    assert links and links[0].text == "acb"


def test_no_glossary_links_while_the_glossary_branch_is_open():
    """The definitions are on this page; 71 self-links would make `S1` unreadable."""
    entries = _terms(_entries())

    segments = segments_for("Soil is defined by ACB.", _index(), terms=entries, open_branch="S1")

    assert all(segment.branch == "" for segment in segments)


def test_a_term_inside_a_heading_is_not_a_link():
    entries = _terms(_entries())
    blocks = (Heading("SOIL MANAGEMENT"), TermBlock("Soil"), row_blocks("Soil\n\nOnly if composted.")[0])

    annotated = annotate(blocks, _index(), terms=entries, open_branch="S6")

    assert all(getattr(block, "segments", ()) == () for block in annotated)


def test_the_shipped_glossary_has_sixty_nine_rendered_headwords(standard_set):
    """One ingest; the number is the measurement that made the derived list the design (D70.7).

    Measured 2026-10-27 on the shipped SAOSO: `S1` holds 78 `Term` blocks, **71 distinct headwords**,
    and **69** of them survive the reader's overlap trimming — which is what the page can anchor.
    `Buffer Zone` and `Homeopathic Treatment` are the two that do not: their definitions are the
    *tail* of a chunk that is also the head of the next, so the trimmed page prints them as the last
    paragraph of a passage, where the layout heuristic cannot see a following line and does not call
    them terms. They are therefore not linkable, and this test says so instead of letting the count
    drift silently.
    """
    ingest_standard(pdf_path=SAOSO_PDF, standard_set=standard_set, doc_key="saoso", embed=False)
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    branch = next(
        section
        for section in build_concordance(document).sections
        if section.key == GLOSSARY_BRANCH[CORPUS_SOURCE]
    )
    from knowledge.reading import strip_overlap

    # Exactly what the reader renders: the same overlap trimming, passage by passage.
    texts: list[str] = []
    previous = None
    for chunk, _anchor in branch.passages:
        text = chunk.text
        if previous is not None and previous.section_ref == chunk.section_ref:
            text = strip_overlap(previous.text, text)
        texts.append(text)
        previous = chunk
    blocks = [block for text in texts for block in passage_blocks(text)]

    entries = glossary_entries(CORPUS_SOURCE, blocks, branch.anchor)

    assert len(entries) == 69 - len(REJECTED[CORPUS_SOURCE])
    assert len({entry.slug for entry in entries}) == len(entries)
    assert entries[0].term == "ACB"
    assert [entry.term for entry in entries].count("Breeding") == 1

    # Provenance: every entry is a `Term` the layout actually found in the branch.
    defined = {block.text for block in blocks if block.kind == "term"}
    assert {entry.term for entry in entries} <= defined

    # The two the overlap trimming costs us — recorded, not discovered later by a reader.
    assert {"Buffer Zone", "Homeopathic Treatment"} & {entry.term for entry in entries} == set()
