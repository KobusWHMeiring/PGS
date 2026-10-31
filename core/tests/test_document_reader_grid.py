"""The reader's printed grid for the landscape's five-column tables (D72.3, D76).

The corpus is quotable; this is the surface that has to *show* it. `LANDSCAPE_TABLES_PRD` §5.4
measured the fit problem, and `product/design/d76_reader_table_fit.html` recorded the decision:
a real `<table>` at the passages pane's full width, a scroll region with a sticky first column,
and the same markup stacked below 900 px.

These tests pin the shape, not the pixels:

- the branch renders **one** table with the paper's five column names;
- the row chunks are **inside** the grid, and the lead-in/trailing prose stays outside it;
- every row keeps its citation anchor (`id="establishing-a-pgs-group-step-3"`), so a citation to
  the row still lands on the row;
- a branch that is not a reviewed table renders no grid at all.

The visual questions — does the fee read, is the sticky column right at 840 px — are UAT's, not
this file's.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.models import PublicDocument
from knowledge.ingest import ingest_standard
from knowledge.models import StandardSet
from knowledge.tests.page_fixtures import stub_ingest_extraction

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF = REPO_ROOT / "pgs_docs" / "PGS Certification landscape_Final.pdf"
SOURCE = "pgs_docs/PGS Certification landscape_Final.pdf"
ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "landscape.md"


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)


@pytest.fixture
def landscape(standard_set, monkeypatch):
    """The real artefact, ingested, plus the published row that traces to the same file."""
    stub_ingest_extraction(monkeypatch)
    ingest_standard(
        pdf_path=PDF,
        standard_set=standard_set,
        doc_key="landscape",
        embed=False,
        corpus_path=ARTEFACT,
    )
    return PublicDocument.objects.create(
        code="certification-landscape",
        title="The South African Organic Certification Landscape",
        file_path="public/documents/certification-landscape.pdf",
        source_path=SOURCE,
        is_published=True,
    )


def html(client, section: str) -> str:
    response = client.get(
        f"/documents/certification-landscape/read/?section={section}"
    )
    assert response.status_code == 200
    return response.content.decode()


# --- One table, five printed columns ----------------------------------------


def test_the_establishing_branch_renders_one_grid_with_the_papers_columns(client, landscape):
    page = html(client, "establishing-a-pgs-group")

    assert page.count('<table class="reader__grid"') == 1
    for column in (
        "Key steps",
        "Resource documents, guidelines and requirements",
        "Use of seals and logos",
        "Seals and logos",
        "Fee",
    ):
        assert column in page, column
    # `<th scope="row">` is the step label — the column that stays pinned while the fee scrolls.
    assert page.count('<th scope="row">') == 3


def test_the_fee_is_inside_the_grid_and_readable(client, landscape):
    page = html(client, "establishing-a-pgs-group")

    table = page.split('<table class="reader__grid"', 1)[1].split("</table>", 1)[0]
    flat = " ".join(table.split())
    assert "Annual membership fee (paid by the PGS group to PGS SA): R500" in flat
    assert "R1 000" in flat, "the once-off amount is part of the same merged Fee cell"


def test_the_lead_in_prose_is_before_the_grid_and_not_inside_it(client, landscape):
    page = html(client, "establishing-a-pgs-group")
    lead_in = "The table below outlines the steps for the establishment of a PGS group"

    assert page.index(lead_in) < page.index('<table class="reader__grid"')
    table = page.split('<table class="reader__grid"', 1)[1].split("</table>", 1)[0]
    assert lead_in not in " ".join(table.split())


def test_every_row_keeps_its_citation_anchor(client, landscape):
    page = html(client, "establishing-a-pgs-group")

    assert 'id="establishing-a-pgs-group-step-1"' in page
    assert 'id="establishing-a-pgs-group-step-2"' in page
    assert 'id="establishing-a-pgs-group-step-3"' in page
    # The row passage is *inside* the grid, not rendered again as an article.
    assert page.count('id="establishing-a-pgs-group-step-1"') == 1


def test_a_table_that_crosses_a_page_says_so_once(client, landscape):
    page = html(client, "establishing-a-pgs-group")
    table = page.split('<table class="reader__grid"', 1)[1].split("</table>", 1)[0]

    assert "printed p. 4" in table
    assert "printed p. 5" in table, "Step 3 starts on PDF 5 (D72.5)"
    assert table.count("printed p. 4") == 1, "the page marker changes once, not per row"


# --- The seals table opens straight into its rows ---------------------------


def test_the_seals_branch_renders_two_rows_and_the_prose_after_the_grid(client, landscape):
    page = html(client, "pgs-seals-and-their-use")
    trailing = "PGS SA is developing guidelines to facilitate trade between PGS groups"

    assert page.count('<th scope="row">') == 2
    assert 'id="pgs-seals-and-their-use-pgs-organic-in-conversion"' in page
    assert 'id="pgs-seals-and-their-use-pgs-organic"' in page
    assert page.index("</table>") < page.index(trailing)


def test_the_saoso_branch_renders_three_rows_including_the_direct_route(client, landscape):
    page = html(client, "saoso-organic-certification")

    assert page.count('<th scope="row">') == 3
    assert "For farmers wanting direct" in page
    assert "R2 500" in " ".join(page.split()), "the retail licensing amount"


# --- Branches that are not tables -------------------------------------------


@pytest.mark.parametrize("section", ["introduction", "colophon", "first-party-claim"])
def test_a_prose_branch_renders_no_grid(client, landscape, section):
    page = html(client, section)
    assert '<table class="reader__grid"' not in page


# --- The fallback, and the doc-key map --------------------------------------


def test_a_corpus_that_disagrees_with_the_artefact_renders_no_grid(client, landscape):
    """A stale row is worse than no grid: the reader falls back to the plain passages.

    Simulated by editing one stored chunk — the artefact still has the row, but the corpus no
    longer does, which is exactly the state a failed re-ingest leaves behind.
    """
    from knowledge.models import DocumentChunk

    row = DocumentChunk.objects.get(
        document__source_file=SOURCE,
        anchor="establishing-a-pgs-group-step-1",
    )
    row.text = row.text.replace("R500", "R5OO")
    row.save(update_fields=["text"])

    page = html(client, "establishing-a-pgs-group")
    assert '<table class="reader__grid"' not in page
    assert "Annual membership fee" in page, "the plain passage still renders the row's text"


def test_a_source_file_maps_to_its_doc_key():
    from knowledge.ingest import doc_key_for

    assert doc_key_for(SOURCE) == "landscape"
    assert doc_key_for("pgs_docs/not-a-governed-document.pdf") is None
    assert doc_key_for(None) is None
