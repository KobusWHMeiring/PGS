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

The corpus fixes the ingest applies are `test_ingest_transforms.py`; the reviewed
artefact as the source of record is `test_ingest_artefact.py`. This file is the ingest
itself: what it produces, what it stores and what it refuses.
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from knowledge.embedding import EmbeddingError
from knowledge.ingest import (
    CORPUS_DOCUMENTS,
    IngestError,
    chunks_per_section_ref,
    ingest_standard,
    resolve_standard_set,
)
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.tests.ingest_fixtures import (  # noqa: F401 - pytest discovers fixtures by name
    FakeProvider,
    KNOWN_SAOSO_DUPLICATES,
    MANIFEST,
    PDFS,
    committed_extraction,
    no_live_embeddings,
    saoso_pdf,
    standard_set,
)

pytestmark = pytest.mark.django_db


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


def test_the_command_names_the_text_of_record_it_read(saoso_pdf, standard_set):
    """The line an operator reads is the only place the default is visible (D55)."""
    out = StringIO()
    call_command(
        "ingest_standard",
        "--doc",
        "saoso",
        "--file",
        str(saoso_pdf),
        "--no-embed",
        stdout=out,
    )

    assert "source=corpus" in out.getvalue()


def test_the_command_can_still_parse_the_pdf_on_request(saoso_pdf, standard_set):
    """`--from-pdf` through argparse, not just through the service: the flag is the
    documented way back to the extraction path, so its wiring is part of the claim."""
    out = StringIO()
    call_command(
        "ingest_standard",
        "--doc",
        "saoso",
        "--file",
        str(saoso_pdf),
        "--no-embed",
        "--from-pdf",
        stdout=out,
    )

    assert "source=pdf" in out.getvalue()


def test_the_command_exits_non_zero_when_the_artefact_is_gone(
    standard_set, monkeypatch, tmp_path
):
    """A deploy script can only see an exit status, so the refusal has to be an exception
    the command turns into `CommandError` — never a warning on a successful run."""
    monkeypatch.setattr("knowledge.ingest.CORPUS_DIR", tmp_path)

    with pytest.raises(CommandError, match="build_corpus"):
        call_command(
            "ingest_standard", "--doc", "bpp", "--file", str(PDFS["bpp"]), "--no-embed"
        )


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
    # And it read the text of record the document declares (D55): the reviewed artefact
    # where one exists, the PDF where none does yet.
    assert bool(report.corpus_digest) == ("corpus_artefact" in CORPUS_DOCUMENTS[doc_key])
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


def test_a_table_rows_embedding_rendition_is_stored(standard_set):
    """D73's vector half, end to end — and the guard the first version of it lacked.

    The ingest builds `DocumentChunk(...)` **field by field** rather than through
    `Chunk.as_chunk_kwargs()`, so a new field on the chunk is silently dropped unless it is
    added there too. Measured 2026-11-01: the rendition reached every row chunk and not one
    row in the database, so the vectors were still the bare cells and the sliding scale
    ranked nowhere. This test would have said so in a second.
    """
    report = ingest_standard(
        pdf_path=PDFS["opp"], standard_set=standard_set, doc_key="opp", embed=False
    )

    row = DocumentChunk.objects.get(
        document_id=report.document_id, section_ref="§2.3", text__startswith="Below R"
    )
    assert row.embedding_text, "the row was stored without the text its vector is built from"
    assert "Annual farm turnover (gross sales): Below R 250,000" in row.embedding_text
    assert "Initial certification fee (R): 1,500" in row.embedding_text
    assert row.text == "Below R 250,000\n1,500\n900", (
        "`text` stays exactly what a citation quotes"
    )


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


def test_an_unreadable_file_is_a_loud_extraction_error(standard_set, tmp_path):
    """An extraction failure propagates; it never becomes an empty document.

    The extraction itself is stubbed by `committed_extraction` (D57), and it raises for a
    path that is not one of the governed PDFs — which is the point here: *ingest* must not
    swallow the error. What `pdftotext` does with a corrupt file is not this suite's subject.
    """
    from knowledge.extraction import ExtractionError

    not_a_pdf = tmp_path / "not-a-pdf.pdf"
    not_a_pdf.write_bytes(b"this is not a PDF")
    with pytest.raises(ExtractionError):
        ingest_standard(
            pdf_path=not_a_pdf,
            standard_set=standard_set,
            doc_key="saoso",
            embed=False,
            from_pdf=True,
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


# --- D68: the printed table of contents is stored once per document ----------


def test_ingest_stores_the_printed_toc(saoso_pdf, standard_set):
    """Through `ingest_standard`, not by setting the field (`testing_hazards.md` §1.32):
    the claim is about what the writer stores, so the writer must produce it.
    """
    report = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )

    toc = StandardDocument.objects.get(pk=report.document_id).toc

    assert len(toc) == 29
    assert {"part", "kind", "label", "title", "printed_page"} == set(toc[0])
    assert [entry["label"] for entry in toc if entry["kind"] == "RANGE"] == ["10 to 19"]


def test_a_document_with_no_printed_toc_stores_an_empty_list(standard_set):
    """The BPP prints no contents page; the field must be empty rather than absent."""
    report = ingest_standard(
        pdf_path=PDFS["bpp"], standard_set=standard_set, doc_key="bpp", embed=False
    )

    assert StandardDocument.objects.get(pk=report.document_id).toc == []
