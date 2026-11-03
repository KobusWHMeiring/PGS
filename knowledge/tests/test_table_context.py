"""Slice 2 of `D79` — a reviewed table travels with its passage, and is shown as a table.

Three properties, each of which fails if it is merely intended:

1. **The table arrives.** Retrieving the OPP §2.3 *introduction* — the passage retrieval
   actually finds — must bring the six fee bands with it, because the bands alone are
   vector-only and their order is noise (measured: `RETRIEVAL_EVAL_SPIKE.md` §8b).
2. **The rows do not displace the evidence.** They are appended, so a question that found
   eight passages still has its eight.
3. **A row knows its label.** Slice 3 renders the context at cite time from it, and the
   prompt needs it to say which cell sits under which column.

The OPP is the corpus to use: it is the one document whose table is artefact-backed *and*
whose rows cannot be found by their own words.
"""

from __future__ import annotations

import pytest

from knowledge.models import DocumentChunk
from knowledge.retrieval import search_terms
from knowledge.table_context import (
    TABLE_ROW_SEATS,
    column_label_for,
    reviewed_table_for,
    reviewed_table_for_section,
)
from knowledge.tests.retrieval_fixtures import opp_ingested, saoso_set  # noqa: F401

pytestmark = pytest.mark.django_db

OPP = "pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf"
FEE_TITLE = "2.3 PGS assessment fee structure (initial certification and renewal)"


def _texts(result):
    return " ".join(chunk.text for chunk in result.chunks)


def test_the_introduction_brings_the_whole_scale(opp_ingested, saoso_set):
    """Retrieving §2.3's prose must bring the six bands — the question G10 could not answer.

    `Below R 250,000 / 1,500 / 900` shares no word with any question, so a band is
    vector-only by construction and sits within 0.023 of its five siblings: which one is
    retrieved, if any, is noise. The introduction *is* retrieved, and it names no number.
    """
    result = search_terms(["sliding", "scale"], standard_set=saoso_set, limit=8)

    texts = _texts(result)
    assert "Below R 250,000" in texts, "the first band did not arrive"
    assert "Above R 5,000,000" in texts, "the last band did not arrive — the scale is cut"
    assert "2,500" in texts


def test_the_rows_carry_their_printed_columns_and_their_own_label(opp_ingested, saoso_set):
    result = search_terms(["sliding", "scale"], standard_set=saoso_set, limit=8)

    rows = [chunk for chunk in result.chunks if chunk.table is not None]
    assert rows, "no passage was recognised as a row of a reviewed table"
    first = next(chunk for chunk in rows if chunk.text.startswith("Below R 250,000"))
    assert first.table.columns == (
        "Annual farm turnover (gross sales)",
        "Initial certification fee (R)",
        "Renewal fee (R)",
    )
    assert first.table.row_label == "Below R 250,000"
    assert FEE_TITLE in first.table.title


def test_the_table_does_not_displace_the_passages_that_found_it(opp_ingested, saoso_set):
    """The rows are appended, so `limit` stays a budget for *retrieval*.

    `eval_retrieval` scores the passages at their ranks; if the rows took seats, every
    table question would silently lose evidence it had before this slice.
    """
    result = search_terms(["sliding", "scale"], standard_set=saoso_set, limit=8)

    retrieved = [chunk for chunk in result.chunks if chunk.score > 0.0]
    added = [chunk for chunk in result.chunks if chunk.score == 0.0]
    assert retrieved, "the query retrieved nothing; this test would pass vacuously"
    assert added, "no row was added; this test would pass vacuously"
    assert [chunk.text for chunk in result.chunks[: len(retrieved)]] == [
        chunk.text for chunk in retrieved
    ], "the rows were inserted among the passages that found them"


def test_the_number_of_rows_a_table_adds_is_bounded(opp_ingested, saoso_set):
    """A six-row table is five rows *added* over the introduction that brought it."""
    result = search_terms(["sliding", "scale"], standard_set=saoso_set, limit=8)

    added = [chunk for chunk in result.chunks if chunk.score == 0.0]
    assert 0 < len(added) <= TABLE_ROW_SEATS


def test_a_passage_outside_a_reviewed_table_is_left_alone(saoso_set, settings, monkeypatch):
    """A SAOSO clause has no artefact table, so nothing is added and nothing is labelled."""
    from knowledge.ingest import ingest_standard
    from knowledge.tests.page_fixtures import stub_ingest_extraction
    from pathlib import Path

    settings.GEMINI_API_KEY = ""
    stub_ingest_extraction(monkeypatch)
    ingest_standard(
        pdf_path=Path("pgs_docs/saoso-version-2.1-2026.pdf"),
        standard_set=saoso_set,
        doc_key="saoso",
        embed=False,
    )

    result = search_terms(["traceability"], standard_set=saoso_set, limit=8)

    assert all(chunk.table is None for chunk in result.chunks)


def test_the_artefact_lookup_finds_a_row_and_refuses_a_paragraph(opp_ingested):
    """`reviewed_table_for` matches a row by its cells, and a paragraph by nothing."""
    row = DocumentChunk.objects.get(text="Below R 250,000\n1,500\n900")
    table = reviewed_table_for(OPP, row.text)
    assert table is not None
    assert table.row_label(row.text) == "Below R 250,000"

    paragraph = DocumentChunk.objects.get(section_ref="§2.3", text__startswith="2.3 PGS")
    assert reviewed_table_for(OPP, paragraph.text) is None, (
        "the introduction is not a row, and must not be given a column heading"
    )
    assert reviewed_table_for_section(OPP, "§2.3", paragraph.heading_path) is not None, (
        "the introduction is the *trigger* for the table"
    )


def test_an_unknown_document_costs_nothing():
    assert reviewed_table_for("pgs_docs/does-not-exist.pdf", "Below R 250,000") is None
    assert reviewed_table_for_section("pgs_docs/does-not-exist.pdf", "§2.3", "") is None


# --- D79 option E, slice 3: the quoted cell names its column -----------------


def _band_context(opp_ingested):
    row = DocumentChunk.objects.get(text="Below R 250,000\n1,500\n900")
    table = reviewed_table_for(OPP, row.text)
    assert table is not None
    return table.context_for(row.text)


def test_the_quoted_cell_names_its_printed_column(opp_ingested):
    """Slice 3's other half: the frame is a row **and a column**, from the same reviewed row.

    The answer says *"below R250,000 … a renewal fee of R900"*, and the citation shows the
    cell (`900`). Naming the column is what lets the reader see why the cell is a renewal
    fee; the label alone would leave `900` and `1,500` indistinguishable context.
    """
    context = _band_context(opp_ingested)

    assert context.cells == ("Below R 250,000", "1,500", "900")
    assert column_label_for(context, "900") == "Renewal fee (R)"
    assert column_label_for(context, "1,500") == "Initial certification fee (R)"
    assert column_label_for(context, "Below R 250,000") == (
        "Annual farm turnover (gross sales)"
    )


def test_a_quote_across_cells_is_given_no_column(opp_ingested):
    """E's one real risk is a heading the reader cannot reconcile with the quote.

    A quote that spans cells has no single column. Naming the first would claim the whole
    quote belongs there; `""` leaves the row context and prints no column at all.
    """
    context = _band_context(opp_ingested)

    assert column_label_for(context, "1,500\n900") == ""
    assert column_label_for(context, "not in this row") == ""
    assert column_label_for(context, "") == ""
    assert column_label_for(None, "900") == "", "a prose passage has no column"


def test_a_process_table_is_not_shown_as_a_grid(opp_ingested):
    """`layout: process` is reviewed data (D77), and its rows are already passages.

    The landscape's "establishing a PGS group" table is a sequence of steps whose cells are
    paragraphs. Shown as a grid of cells they become a puzzle, and they cost eight seats for
    nothing — measured 2026-11-02: the fee question's prompt grew to 11,969 characters and
    three of the eight added rows were landscape steps.
    """
    landscape = "pgs_docs/PGS Certification landscape_Final.pdf"
    assert reviewed_table_for_section(landscape, None, "ESTABLISHING A PGS GROUP") is None
