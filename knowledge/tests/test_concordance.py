"""The tree is the document's own structure, derived from chunks.

The three rules below were found by running the derivation over the shipped corpus
(`CONCORDANCE_PRD` §10.1–10.3) and each silently mis-files passages if it is dropped.

The last section ingests the real certification landscape: a reviewed branch title is a
claim about what ingest *and* derivation produce together, so a hand-built document would
prove nothing (`testing_hazards.md` §1.32).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.concordance import (
    REVIEWED_BRANCH_TITLES,
    _branch_key,
    build_concordance,
    concordance_sections,
)
from knowledge.ingest import ingest_standard
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.reading import reading_chunks
from knowledge.tests.page_fixtures import stub_ingest_extraction

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
PDFS = {
    "saoso": REPO_ROOT / "pgs_docs" / "saoso-version-2.1-2026.pdf",
    "opp": REPO_ROOT / "pgs_docs" / "Outeniqua pgs principles, policies and procedures 2026.pdf",
    "bpp": REPO_ROOT / "pgs_docs" / "Basic Production Principles_ENG_PRINT.pdf",
    "landscape": REPO_ROOT / "pgs_docs" / "PGS Certification landscape_Final.pdf",
}


@pytest.fixture(autouse=True)
def committed_extraction(monkeypatch):
    """The gate has no PDF reader (D57); the committed pages are the input."""
    stub_ingest_extraction(monkeypatch)


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(
        code="outeniqua", label="Outeniqua", is_default=True
    )


@pytest.fixture
def document(db) -> StandardDocument:
    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    return StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.1",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="0" * 64,
        section_scheme="saoso",
    )


def chunk(document, section_ref, page, text, heading_path="", anchor=""):
    return DocumentChunk.objects.create(
        document=document,
        section_ref=section_ref,
        heading_path=heading_path,
        page=page,
        text=text,
        anchor=anchor,
    )


# --- The three grouping rules ------------------------------------------------


def test_an_opening_chunk_stays_in_its_own_section(document):
    """SAOSO prints `1. DEFINITIONS` as a chunk with a reference and *no* heading.

    A heading-first grouping files the section's title page under the *next* section —
    the one thing a table of contents must never do (§10.1).
    """
    opener = chunk(document, "S1", 22, "1. DEFINITIONS")
    body = chunk(
        document, "S2.1", 30, "Ecosystem management.", "2. ORGANIC ECOSYSTEMS > 2.1 Ecosystem"
    )

    sections = {section.key: section for section in concordance_sections(document)}

    assert [c.pk for c, _a in sections["S1"].passages] == [opener.pk]
    assert [c.pk for c, _a in sections["S2"].passages] == [body.pk]


def test_a_roman_heading_merges_with_its_decimal_body(document):
    """The OPP prints `§II` as the heading and numbers the body `2.1`–`2.5` (§10.2).

    Without the roman→decimal conversion the same section is two branches, one a stub.
    """
    stub = chunk(document, "§II", 1, "II. Membership fees")
    body = chunk(document, "§2.1", 1, "2.1 Membership Fees")

    sections = {
        c.pk: section
        for section in concordance_sections(document)
        for c, _a in section.passages
    }

    assert sections[stub.pk] is sections[body.pk]
    assert sections[stub.pk].key == "§2"


def test_a_heading_shared_by_several_branches_is_not_a_title(document):
    """SAOSO prints `APPENDICES` above Appendices 1–7 (§10.3): seven branches named after
    the divider give a reader no way to choose one."""
    for number in (1, 2):
        chunk(
            document,
            f"Appendix {number}",
            70 + number,
            f"Appendix {number} body",
            "APPENDICES > x",
        )

    titles = [section.title for section in concordance_sections(document)]

    assert "APPENDICES" not in titles
    assert titles == ["Appendix 1", "Appendix 2"]


# --- Names, reserved rows, and what the corpus does not hold -----------------


def test_a_branch_is_named_from_the_printed_toc(document):
    """The TOC is the only source that names a branch correctly (§10.5): `S1`'s chunks carry
    no heading at all, and Appendix 2's first heading names its first sub-table."""
    document.toc = [
        {"part": "B", "kind": "CLAUSE", "label": "1", "title": "Definitions", "printed_page": 22},
        {
            "part": "B",
            "kind": "RANGE",
            "label": "10 to 19",
            "title": "Left blank to facilitate future enterprises",
            "printed_page": None,
        },
        {
            "part": "B",
            "kind": "APPENDIX",
            "label": "Appendix 2",
            "title": "Fertilizers Conditioners and Soil Conditioners",
            "printed_page": 76,
        },
    ]
    document.save(update_fields=["toc"])
    chunk(document, "S1", 22, "1. DEFINITIONS")
    chunk(
        document,
        "Appendix 2",
        76,
        "Farmyard manure, slurry and urine",
        "Appendix 2 - Farmyard manure, slurry and urine",
    )

    sections = concordance_sections(document)

    assert [s.title for s in sections] == [
        "1. Definitions",
        "10 to 19. Left blank to facilitate future enterprises",
        "Appendix 2. Fertilizers Conditioners and Soil Conditioners",
    ]


def test_a_reserved_row_has_no_passages(document):
    """`10 to 19. Left blank…` is a row a reader can see and cannot open (§10.8)."""
    document.toc = [
        {
            "part": "B",
            "kind": "RANGE",
            "label": "10 to 19",
            "title": "Left blank to facilitate future enterprises",
            "printed_page": None,
        }
    ]
    document.save(update_fields=["toc"])
    chunk(document, "S9", 57, "9. AQUACULTURE")

    reserved = [s for s in concordance_sections(document) if s.reserved]

    assert len(reserved) == 1
    assert reserved[0].chunk_count == 0
    assert reserved[0].anchor == "10-to-19"


def test_the_tree_reports_the_printed_sections_the_corpus_does_not_hold(document):
    """Section A prints clauses 1–3 on pp. 4–11 and Section C prints Appendices A–C on
    pp. 93–96; neither is ingested (§10.6). The page must be able to say so."""
    document.toc = [
        {"part": "A", "kind": "CLAUSE", "label": "1", "title": "Introduction", "printed_page": 4},
        {"part": "A", "kind": "CLAUSE", "label": "2", "title": "General", "printed_page": 7},
        {"part": "B", "kind": "CLAUSE", "label": "1", "title": "Definitions", "printed_page": 22},
        {
            "part": "C",
            "kind": "APPENDIX",
            "label": "Appendix A",
            "title": "SAOSO Organic Logos",
            "printed_page": 93,
        },
    ]
    document.save(update_fields=["toc"])
    chunk(document, "S1", 22, "1. DEFINITIONS")

    concordance = build_concordance(document)

    assert [s.title for s in concordance.sections] == ["1. Definitions"]
    assert concordance.missing == (
        "1. Introduction",
        "2. General",
        "Appendix A. SAOSO Organic Logos",
    )


def test_the_printed_page_is_the_branchs_first_page(document):
    """A reader choosing a branch uses the printed page number, so it must be the
    branch's own first page and not a chunk's arbitrary page."""
    chunk(document, "S5.1", 42, "5.1 first")
    chunk(document, "S5.1.9", 41, "5.1.9 printed earlier (out of document order)")

    branch = concordance_sections(document)[0]

    assert branch.key == "S5"
    assert branch.page == 41


# --- Reviewed titles for the document with no TOC ----------------------------


def test_the_landscape_branches_are_named_for_what_they_are(standard_set):
    """Measured 2026-10-27: the certification landscape's heading scheme reads a price line
    (`R500`) and a truncation (`PGS SA.`) as headings, so two of six branches were named after
    table cells (§10.5). Reviewed titles live in `REVIEWED_BRANCH_TITLES`.

    Ingested, not hand-built: the claim is about what the ingest and the derivation produce
    together (`testing_hazards.md` §1.32).
    """
    report = ingest_standard(
        pdf_path=PDFS["landscape"], standard_set=standard_set, doc_key="landscape", embed=False
    )
    document = StandardDocument.objects.get(pk=report.document_id)

    titles = [section.title for section in concordance_sections(document)]

    assert "R500" not in titles, "a price line is still a branch title"
    assert "Cost of joining a PGS group" in titles
    assert "Working with PGS South Africa" in titles


def test_every_reviewed_title_matches_a_real_branch(standard_set):
    """A reviewed correction that matches nothing is a stale entry: it must fail rather than
    sit there looking authoritative (the `CORPUS_EDITS` idiom)."""
    report = ingest_standard(
        pdf_path=PDFS["landscape"], standard_set=standard_set, doc_key="landscape", embed=False
    )
    document = StandardDocument.objects.get(pk=report.document_id)
    keys = {_branch_key(at) for at in reading_chunks(document)}

    for source, key in REVIEWED_BRANCH_TITLES:
        if source == document.source_file:
            assert key in keys, f"reviewed title for {key!r} matches no branch"
