"""Task B6 — `ingest_standard`.

These tests read the **real PDFs** in `pgs_docs/`, because B6's whole purpose is to
prove the parsers run against the documents as shipped. That is what v1 never did: its
tests passed against hand-written fixtures while its parser matched zero lines of the
real file.

Three guards keep the suite honest and offline:

- `no_live_embeddings` (autouse) replaces the Gemini provider with a bomb, so a test
  that forgets `--no-embed` fails loudly instead of spending someone's API quota.
  Merging is what would otherwise happen, because this box has a key in its
  environment and the command defaults to embedding.
- The corpus sha256 recorded on the document is compared with A10's `MANIFEST.json`,
  which proves the ingest read the same bytes the fixtures were extracted from.
- The duplicate-`section_ref` ratchet is asserted at **0**, not at the plan's "~50".

That last number is the interesting one. Every duplicate the plan measured came from
Appendix 1, which contains two independently numbered criteria lists (`1.`–`6.` with
`1.1`, `1.2` … on printed pp. 71–72, and again on pp. 73–75). Once an appendix is one
section rather than a clause list, the duplicates are gone — so the ratchet holds at
zero and any reappearance is a parser regression, not a known cost.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core.management import call_command

from knowledge.embedding import EmbeddingError, GeminiEmbeddingProvider
from knowledge.ingest import (
    CORPUS_DOCUMENTS,
    IngestError,
    chunks_per_section_ref,
    ingest_standard,
    resolve_standard_set,
)
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.tests.test_columns import EXPECTED_TRANSFORMED_PAGES

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = REPO_ROOT / "pgs_docs"
MANIFEST = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "MANIFEST.json").read_text(encoding="utf-8")
)

#: The plan's ratchet, re-measured. See the module docstring: the appendix fix removed
#: the whole population, so this is a hard zero rather than a known cost.
KNOWN_SAOSO_DUPLICATES = 0

PDFS = {
    "saoso": PDF_DIR / "saoso-version-2.1-2026.pdf",
    "opp": PDF_DIR / "Outeniqua pgs principles, policies and procedures 2026.pdf",
    "bpp": PDF_DIR / "Basic Production Principles_ENG_PRINT.pdf",
    "landscape": PDF_DIR / "PGS Certification landscape_Final.pdf",
}


@pytest.fixture(autouse=True)
def no_live_embeddings(monkeypatch):
    """Any attempt to build the real provider fails the test.

    An ingest test that omits `embed=False` would otherwise make a live API call: the
    command defaults to embedding, and this shell has a key in its environment.
    """

    def bomb(*args, **kwargs):  # pragma: no cover - only runs when the guard fires
        raise AssertionError(
            "a live GeminiEmbeddingProvider was constructed in a test; pass "
            "embed=False or an explicit provider"
        )

    # `embed_texts` resolves the class in `knowledge.embedding`, which is the only
    # place a provider is built when none is injected.
    monkeypatch.setattr(
        "knowledge.embedding.GeminiEmbeddingProvider", bomb, raising=False
    )


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(
        code="outeniqua", label="Outeniqua PGS corpus", is_default=True
    )


@pytest.fixture
def saoso_pdf():
    path = PDFS["saoso"]
    assert path.exists(), f"the governing document is missing: {path}"
    return path


class FakeProvider:
    def __init__(self, dimension=768):
        self.dimension = dimension
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return [[0.1] * self.dimension for _ in texts]


# --- The plan's three tests --------------------------------------------------


def test_ingest_produces_citable_chunks(saoso_pdf, standard_set):
    call_command(
        "ingest_standard", "--doc", "saoso", "--file", str(saoso_pdf), "--no-embed"
    )
    chunks = DocumentChunk.objects.all()
    assert chunks.count() > 0
    assert not chunks.filter(section_ref="").exists()          # v1's silent failure
    assert chunks.filter(section_ref__startswith="S20.1").exists()


def test_ingest_is_idempotent_on_sha256(saoso_pdf, standard_set):
    call_command(
        "ingest_standard", "--doc", "saoso", "--file", str(saoso_pdf), "--no-embed"
    )
    count = DocumentChunk.objects.count()
    call_command(
        "ingest_standard", "--doc", "saoso", "--file", str(saoso_pdf), "--no-embed"
    )
    assert DocumentChunk.objects.count() == count
    assert StandardDocument.objects.count() == 1, "a second document row was written"


def test_ingest_reports_being_a_no_op(saoso_pdf, standard_set):
    ingest_standard(pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False)
    report = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )
    assert report.created is False
    assert report.chunk_count > 0
    assert any("already ingested" in warning for warning in report.warnings)


def test_duplicate_refs_are_reported_and_the_ratchet_holds(saoso_pdf, standard_set):
    """The ratchet is on *sections* sharing a citation, not on chunks.

    `S1` is the glossary and spans eight chunks, all cited `S1` — expected and healthy.
    Two *sections* sharing a citation is the failure, and it fails the reader: `S1.2`
    would resolve to two different paragraphs. Measured at zero after the appendix fix.
    """
    report = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )
    assert report.duplicate_ref_count <= KNOWN_SAOSO_DUPLICATES
    assert report.duplicate_refs == {}
    # And the chunks-per-ref diagnostic shows the split is happening as designed.
    document = StandardDocument.objects.get(pk=report.document_id)
    assert chunks_per_section_ref(document), "no citation spans more than one chunk"


# --- The acceptance test: every corpus document ingests ----------------------


@pytest.mark.parametrize("doc_key", sorted(CORPUS_DOCUMENTS))
def test_each_corpus_document_ingests(doc_key, standard_set):
    report = ingest_standard(
        pdf_path=PDFS[doc_key], standard_set=standard_set, doc_key=doc_key, embed=False
    )
    assert report.created is True
    assert report.chunk_count > 0
    assert report.duplicate_ref_count == 0

    document = StandardDocument.objects.get(pk=report.document_id)
    assert document.section_scheme == CORPUS_DOCUMENTS[doc_key]["section_scheme"]
    assert document.chunks.count() == report.chunk_count
    assert document.chunk_count == report.chunk_count

    # Every chunk is locatable: a citation, or (heading-only documents) an anchor.
    for chunk in document.chunks.all():
        assert chunk.section_ref or chunk.anchor or chunk.heading_path


def test_the_ingest_read_the_bytes_a10_extracted(standard_set, saoso_pdf):
    """The cross-check that makes the fixtures evidence for the ingest too.

    A10's manifest records the sha256 of each corpus PDF. If the ingest ever reads a
    different file — or a different edition of the same file — this fails, and it fails
    before a parser is blamed for text it never saw.
    """
    report = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )
    document = StandardDocument.objects.get(pk=report.document_id)
    recorded = MANIFEST["corpus_sources"]["saoso-version-2.1-2026.pdf"]["sha256"]
    assert document.sha256 == recorded


def test_source_file_is_recorded_relative_to_the_repo(standard_set, saoso_pdf):
    report = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )
    document = StandardDocument.objects.get(pk=report.document_id)
    assert document.source_file == "pgs_docs/saoso-version-2.1-2026.pdf"


# --- Chunk content -----------------------------------------------------------


def test_search_vector_is_populated_by_ingest(saoso_pdf, standard_set):
    """B1's generated column, proven on ingested rows rather than on a hand-built one.

    The clause is `S20.1.2` — *"shall ensure traceability in the organic processing and
    handling chain"*. `S20.1.1` is the co-mingling clause, and an earlier version of this
    test asserted "traceab" against it.
    """
    ingest_standard(pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False)
    chunk = DocumentChunk.objects.filter(section_ref="S20.1.2").first()
    assert chunk is not None, "the traceability clause was not ingested"
    assert "traceab" in chunk.search_vector


def test_pages_are_the_printed_numbers(saoso_pdf, standard_set):
    """D42 end to end: S20.1.1 is printed on page 60 and the PDF index is 61."""
    ingest_standard(pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False)
    chunk = DocumentChunk.objects.get(section_ref="S20.1.1")
    assert chunk.page == 60


def test_opp_sub_refs_survive_into_the_database(standard_set):
    """D15 end to end: §4.5's offsets are stored and still slice their own chunk.

    §4.5 splits across two chunks, so the refs are gathered from all of them.
    """
    from knowledge.models import validate_sub_refs

    ingest_standard(
        pdf_path=PDFS["opp"], standard_set=standard_set, doc_key="opp", embed=False
    )
    chunks = DocumentChunk.objects.filter(section_ref="§4.5")
    assert chunks.exists()
    refs = {ref["ref"] for chunk in chunks for ref in chunk.sub_refs}
    assert {"4.5(1)", "4.5(2)(c)", "4.5(4)"} <= refs
    assert "4.5(3)" not in refs          # the missing item is still missing
    for chunk in chunks:
        validate_sub_refs(chunk.sub_refs, chunk.text)


def test_appendix_content_is_cited_as_an_appendix(standard_set, saoso_pdf):
    """Not as `S1.2`: Appendix 1 numbers its two lists from 1 independently.

    Both halves matter. The content must be *in* chunks cited `Appendix 1`, and no
    chunk outside the appendices may claim it — a parser that split on those clause
    lines would file Appendix 1's criteria under Section B's clause numbers.
    """
    ingest_standard(pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False)
    assert DocumentChunk.objects.filter(
        section_ref="Appendix 1", text__contains="Necessity and Alternatives"
    ).exists()
    assert not DocumentChunk.objects.filter(
        section_ref__startswith="S", text__contains="Necessity and Alternatives"
    ).exists()


def test_heading_documents_store_no_section_ref(standard_set):
    """B1's CHECK allows NULL and forbids `""`; the heading scheme produces NULL."""
    ingest_standard(
        pdf_path=PDFS["bpp"], standard_set=standard_set, doc_key="bpp", embed=False
    )
    assert not DocumentChunk.objects.filter(section_ref="").exists()
    assert DocumentChunk.objects.filter(section_ref__isnull=True).exists()
    assert all(chunk.anchor for chunk in DocumentChunk.objects.all())


# --- Embeddings --------------------------------------------------------------


def test_a_missing_key_writes_chunks_without_vectors_and_warns(
    standard_set, saoso_pdf, settings
):
    settings.GEMINI_API_KEY = ""
    report = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso"
    )
    assert report.embedded is False
    assert report.chunk_count > 0
    assert any("GEMINI_API_KEY" in warning for warning in report.warnings)
    assert DocumentChunk.objects.filter(embedding__isnull=True).count() == report.chunk_count


def test_embeddings_are_stored_when_a_provider_is_supplied(standard_set, saoso_pdf):
    provider = FakeProvider()
    report = ingest_standard(
        pdf_path=saoso_pdf,
        standard_set=standard_set,
        doc_key="saoso",
        provider=provider,
    )
    assert report.embedded is True
    assert provider.calls >= 1
    assert DocumentChunk.objects.filter(embedding__isnull=True).count() == 0
    chunk = DocumentChunk.objects.filter(section_ref="S20.1.1").get()
    assert len(chunk.embedding) == 768


def test_an_embedding_failure_writes_nothing(standard_set, saoso_pdf):
    """Embedding happens before the transaction, so a failure cannot half-ingest."""

    class Failing(FakeProvider):
        def embed(self, texts):
            raise EmbeddingError("provider down")

    with pytest.raises(EmbeddingError):
        ingest_standard(
            pdf_path=saoso_pdf,
            standard_set=standard_set,
            doc_key="saoso",
            provider=Failing(),
        )
    assert StandardDocument.objects.count() == 0
    assert DocumentChunk.objects.count() == 0


# --- Failing loudly ----------------------------------------------------------


def test_a_document_that_parses_to_nothing_is_refused(standard_set):
    """Zero sections is the v1 failure; the ingest must refuse, not write nothing.

    The OPP read with the SAOSO scheme is the realistic case: a documents that prints no
    indented `SECTION` header yields no clauses, and an ingest that accepted that would
    report success while the chatbot could cite nothing.
    """
    with pytest.raises(IngestError, match="zero sections"):
        ingest_standard(
            pdf_path=PDFS["opp"],
            standard_set=standard_set,
            title="Wrong scheme",
            kind="STANDARD",
            section_scheme="saoso",
            embed=False,
        )
    assert StandardDocument.objects.count() == 0


def test_a_file_that_is_not_a_pdf_is_a_loud_extraction_error(standard_set, tmp_path):
    from knowledge.extraction import ExtractionError

    not_a_pdf = tmp_path / "not-a-pdf.pdf"
    not_a_pdf.write_bytes(b"this is not a PDF")
    with pytest.raises(ExtractionError):
        ingest_standard(
            pdf_path=not_a_pdf, standard_set=standard_set, doc_key="saoso", embed=False
        )


def test_an_unknown_scheme_is_refused_before_any_write(standard_set, saoso_pdf):
    with pytest.raises(Exception) as error:
        ingest_standard(
            pdf_path=saoso_pdf,
            standard_set=standard_set,
            title="Fabricated",
            kind="STANDARD",
            section_scheme="eu-2018-848",
            embed=False,
        )
    assert "No section parser" in str(error.value)
    assert StandardDocument.objects.count() == 0


def test_missing_metadata_is_refused(standard_set, saoso_pdf):
    with pytest.raises(IngestError, match="Missing"):
        ingest_standard(pdf_path=saoso_pdf, standard_set=standard_set, embed=False)


def test_a_missing_pdf_is_refused(standard_set):
    with pytest.raises(IngestError, match="No such PDF"):
        ingest_standard(
            pdf_path="pgs_docs/does-not-exist.pdf", standard_set=standard_set, doc_key="saoso"
        )


def test_resolve_standard_set_requires_an_unambiguous_default(db):
    with pytest.raises(IngestError, match="exactly one default"):
        resolve_standard_set()
    StandardSet.objects.create(code="a", label="A", is_default=True)
    assert resolve_standard_set().code == "a"
    assert resolve_standard_set("a").code == "a"
    with pytest.raises(IngestError, match="No StandardSet"):
        resolve_standard_set("nope")


# --- D46: the column transform runs at ingest, and says so -------------------


@pytest.mark.parametrize("doc_key", sorted(EXPECTED_TRANSFORMED_PAGES))
def test_the_ingest_reports_the_pages_it_transformed(doc_key, standard_set):
    """The report is how a human sees the transform ran.

    Values come from the golden table, which is the point: a detector regression that
    reports zero pages takes the expectation with it, which is why the BPP count is
    also pinned as a literal below.
    """
    report = ingest_standard(
        pdf_path=PDFS[doc_key], standard_set=standard_set, doc_key=doc_key, embed=False
    )
    assert report.created is True
    assert set(report.layout_pages) == EXPECTED_TRANSFORMED_PAGES[doc_key]
    assert report.layout_pages == tuple(sorted(report.layout_pages))


def test_bpp_reports_eight_layout_pages(standard_set):
    # A literal on purpose. If the detector regresses to zero, the golden set and the
    # report would agree with each other and both be wrong.
    report = ingest_standard(
        pdf_path=PDFS["bpp"], standard_set=standard_set, doc_key="bpp", embed=False
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

    `knowledge/tables.py` holds the reviewed pairing; this asserts the ingest actually
    uses it. The `calcium Use restricted` assertion is the 2026-10-21 defect verbatim:
    the model quoted the real page and the audit refused it because the stored text had
    the condition column spliced into the substance column.
    """
    from knowledge.tables import APPENDIX_2_ROWS

    report = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )
    document = StandardDocument.objects.get(pk=report.document_id)
    rows = list(document.chunks.filter(section_ref="Appendix 2").order_by("id"))

    assert len(rows) == len(APPENDIX_2_ROWS)
    assert not any("calcium Use restricted" in chunk.text for chunk in rows), (
        "the interleaved -layout chunk survived the curated table"
    )
    wood = next(chunk for chunk in rows if chunk.text.startswith("Wood, bark, sawdust"))
    assert wood.text.endswith("Only if not chemically treated")
    straw = next(chunk for chunk in rows if chunk.text.startswith("Crop residues"))
    assert straw.text == "Crop residues and plant materials, mulch, green manure, straw"


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
#: a no-op that reported nothing would otherwise look like a clean ingest.
EXPECTED_REFLOW_PAGES = {"saoso": 12, "opp": 4, "bpp": 3, "landscape": 1}


def flat(text: str) -> str:
    """Exactly what `audit_citations` compares."""
    return " ".join(text.split())


@pytest.mark.parametrize("doc_key", sorted(EXPECTED_REFLOW_PAGES))
def test_the_ingest_reports_the_pages_it_rejoined(doc_key, standard_set):
    report = ingest_standard(
        pdf_path=PDFS[doc_key], standard_set=standard_set, doc_key=doc_key, embed=False
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
