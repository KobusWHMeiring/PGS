"""The corpus fixes the ingest applies, and the pages it says it touched — D46, D52.

Both decisions are the same shape: a live answer was refused, the cause turned out to be
the corpus rather than the model, and the fix went to the ingest. So each one is pinned
in two places — the corpus now produces a quotable sentence, and the ingest **reports**
the pages it changed, because a no-op that reported nothing would look like a clean run.

`test_reflow.py` pins the pure functions beside these; this file pins that the ingest
calls them and says so. The reviewed Appendix 2 rows live here too: a reviewed table is
another shape the ingest stores rather than derives.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.embedding import EmbeddingError
from knowledge.ingest import ingest_standard
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.tests.ingest_fixtures import (  # noqa: F401 - pytest discovers fixtures by name
    PDFS,
    committed_extraction,
    no_live_embeddings,
    saoso_pdf,
    standard_set,
)
from knowledge.tests.test_columns import EXPECTED_TRANSFORMED_PAGES

pytestmark = pytest.mark.django_db


# --- D46: the column transform runs at ingest, and says so -------------------


@pytest.mark.parametrize("doc_key", sorted(EXPECTED_TRANSFORMED_PAGES))
def test_the_ingest_reports_the_pages_it_transformed(doc_key, standard_set):
    """The report is how a human sees the transform ran.

    Values come from the golden table, which is the point: a detector regression that
    reports zero pages takes the expectation with it, which is why the BPP count is
    also pinned as a literal below.
    """
    report = ingest_standard(
        pdf_path=PDFS[doc_key],
        standard_set=standard_set,
        doc_key=doc_key,
        embed=False,
        from_pdf=True,
    )
    assert report.created is True
    assert set(report.layout_pages) == EXPECTED_TRANSFORMED_PAGES[doc_key]
    assert report.layout_pages == tuple(sorted(report.layout_pages))


def test_bpp_reports_eight_layout_pages(standard_set):
    # A literal on purpose. If the detector regresses to zero, the golden set and the
    # report would agree with each other and both be wrong.
    report = ingest_standard(
        pdf_path=PDFS["bpp"],
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        from_pdf=True,
    )
    assert len(report.layout_pages) == 8


def test_a_new_standard_gets_generic_detection(standard_set, saoso_pdf):
    """No doc_key means no exclusion table — generic detection, no special case (D16).

    For SAOSO that includes PDF 2 (the TOC), which is precisely why the four governed
    documents are ingested with `--doc`: the exclusion is a measured fact about *this*
    document, and the same generic treatment applies to a standard that is not one of
    them. No shared allow-list, no migration.
    """
    report = ingest_standard(
        pdf_path=saoso_pdf,
        standard_set=standard_set,
        kind="STANDARD",
        title="SAOSO, ingested without a corpus key",
        section_scheme="saoso",
        embed=False,
    )
    assert report.layout_pages
    assert 2 in report.layout_pages  # the TOC *is* transformed without a doc_key


def test_two_sets_may_hold_the_same_document(db):
    """`sha256` is unique per set, so one PDF can belong to two coexisting corpora."""
    other = StandardSet.objects.create(code="other", label="Other", is_default=True)
    first = ingest_standard(
        pdf_path=PDFS["opp"], standard_set=other, doc_key="opp", embed=False
    )
    third = StandardSet.objects.create(code="third", label="Third")
    second = ingest_standard(
        pdf_path=PDFS["opp"], standard_set=third, doc_key="opp", embed=False
    )
    assert first.created is True and second.created is True
    assert StandardDocument.objects.count() == 2


# --- The reviewed Appendix 2 table (2026-10-21) ------------------------------


def test_appendix_2_is_stored_as_reviewed_rows(saoso_pdf, standard_set):
    """The interleaved `-layout` chunk is replaced by one chunk per printed row.

    Appendix 2's rows are the artefact's `<!-- table -->` block (S5-b deleted the Python copy); this
    asserts the ingest actually chunks them, and that each row is one chunk. The
    `calcium Use restricted` assertion is the 2026-10-21 defect verbatim: the model quoted the real
    page and the audit refused it because the stored text had the condition column spliced into the
    substance column.
    """
    from knowledge.corpus import parse_blocks
    from knowledge.ingest import corpus_artifact

    report = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )
    document = StandardDocument.objects.get(pk=report.document_id)
    rows = list(document.chunks.filter(section_ref="Appendix 2").order_by("id"))
    artefact = parse_blocks(Path(corpus_artifact("saoso")).read_text(encoding="utf-8"))
    table = next(s for s in artefact.sections if s.section_ref == "Appendix 2").tables[0]

    assert len(table.rows) == 30
    # 31 chunks: the header prose before the grid, then one per row (`chunks_for_parsed_section`).
    assert len(rows) == 31
    assert not any("calcium Use restricted" in chunk.text for chunk in rows), (
        "the interleaved -layout chunk survived the table block"
    )
    wood = next(chunk for chunk in rows if chunk.text.startswith("Wood, bark, sawdust"))
    assert wood.text.endswith("Only if not chemically treated")
    straw = next(chunk for chunk in rows if chunk.text.startswith("Crop residues"))
    # The page wraps this row across two lines, and the chunk is the page's characters.
    assert (
        " ".join(straw.text.split())
        == "Crop residues and plant materials, mulch, green manure, straw"
    )


def test_force_replaces_a_document_with_unchanged_bytes(saoso_pdf, standard_set):
    first = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )
    second = ingest_standard(
        pdf_path=saoso_pdf,
        standard_set=standard_set,
        doc_key="saoso",
        embed=False,
        force=True,
    )

    assert second.created is True
    assert second.document_id != first.document_id
    assert StandardDocument.objects.count() == 1
    assert not DocumentChunk.objects.filter(document_id=first.document_id).exists()


def test_a_failed_embedding_under_force_leaves_the_old_corpus(saoso_pdf, standard_set):
    """`force` deletes inside the transaction, after the embed: a failure is not a wipe."""

    class FailingProvider:
        def embed(self, texts):  # pragma: no cover - only the raise is the point
            raise EmbeddingError("embedding service is down")

    first = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )

    with pytest.raises(EmbeddingError):
        ingest_standard(
            pdf_path=saoso_pdf,
            standard_set=standard_set,
            doc_key="saoso",
            embed=True,
            provider=FailingProvider(),
            force=True,
        )

    assert StandardDocument.objects.filter(pk=first.document_id).exists()
    assert DocumentChunk.objects.filter(document_id=first.document_id).exists()


# --- D52: the hyphen reflow runs at ingest, and says so ----------------------

#: Measured on the shipped PDFs (test_reflow.py pins the same numbers beside the pure
#: function). Literal here because the report is how an operator sees the transform ran:
#: a no-op that reported nothing would otherwise look like a clean ingest. OPP went 4 -> 3
#: on 2026-10-27 with `-enc UTF-8`: PDF 4 (§3.1's 3-column table) is no longer de-columned.
EXPECTED_REFLOW_PAGES = {"saoso": 12, "opp": 3, "bpp": 5, "landscape": 1}


def flat(text: str) -> str:
    """Exactly what `audit_citations` compares."""
    return " ".join(text.split())


@pytest.mark.parametrize("doc_key", sorted(EXPECTED_REFLOW_PAGES))
def test_the_ingest_reports_the_pages_it_rejoined(doc_key, standard_set):
    report = ingest_standard(
        pdf_path=PDFS[doc_key],
        standard_set=standard_set,
        doc_key=doc_key,
        embed=False,
        from_pdf=True,
    )
    assert report.created is True
    assert len(report.reflow_pages) == EXPECTED_REFLOW_PAGES[doc_key]
    assert report.reflow_pages == tuple(sorted(report.reflow_pages))


def test_the_ducks_clause_is_ingested_quotable(saoso_pdf, standard_set):
    """G1, end to end: `S5.5.1` holds the sentence a reader sees, and no page footer.

    Before D52 the stored chunk read `… per non-` / `P a g e | 47` / `ruminant …`, so the
    live answer elided the word with `...` and the audit refused a correct answer.
    """
    ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )
    carriers = [
        chunk
        for chunk in DocumentChunk.objects.filter(section_ref="S5.5.1")
        if flat(
            "may not exceed 10% dry matter per ruminant and 15% dry matter per "
            "non-ruminant calculated on an annual basis"
        )
        in flat(chunk.text)
    ]
    assert len(carriers) == 1
    assert "P a g e |" not in carriers[0].text


def test_the_seed_clause_is_ingested_quotable(saoso_pdf, standard_set):
    """G2, end to end: `S4.1.1` holds `post-harvest` as one word."""
    ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )
    chunk = DocumentChunk.objects.get(section_ref="S4.1.1")
    assert "treated with post-harvest pesticides not otherwise permitted by this Standard" in flat(
        chunk.text
    )


def test_no_chunk_in_any_document_carries_the_printed_page_footer(standard_set):
    """The footer is a page property, so the guard runs over every governed document."""
    for doc_key in PDFS:
        ingest_standard(
            pdf_path=PDFS[doc_key], standard_set=standard_set, doc_key=doc_key, embed=False
        )
    offenders = [
        (chunk.section_ref, chunk.anchor)
        for chunk in DocumentChunk.objects.all()
        if "P a g e |" in chunk.text or "Page |" in chunk.text
    ]
    assert offenders == []
    assert DocumentChunk.objects.count() > 300, "nothing was ingested"


