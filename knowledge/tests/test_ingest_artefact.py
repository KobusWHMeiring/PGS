"""The reviewed artefact is the source of record — D53, D55.

A document that declares a review must ingest from it, and must fail closed when the
artefact is missing rather than silently falling back to a PDF parse (D55). D53's
argument is the artefact itself: `knowledge/corpus/<doc>.md` is what a reviewer signed,
so it is what the corpus is built from, and the digest on the document says which one.

`tests/tools/test_corpus_artefacts.py` guards the artefacts' own format; this file guards
that the ingest uses them.
"""

from __future__ import annotations

import hashlib

import pytest

from knowledge.ingest import IngestError, ingest_standard
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.tests.ingest_fixtures import (  # noqa: F401 - pytest discovers fixtures by name
    PDFS,
    REPO_ROOT,
    committed_extraction,
    no_live_embeddings,
    standard_set,
    undeclared_opp,
)

pytestmark = pytest.mark.django_db


# --- D53: ingesting the reviewed corpus artefact -----------------------------

CORPUS_ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "bpp.md"


def flat_text(text: str) -> str:
    return " ".join(text.split())


def test_the_artefact_exists_and_is_the_one_this_document_reviews():
    assert CORPUS_ARTEFACT.exists(), "the BPP artefact is the spike's deliverable"


def test_ingesting_from_the_artefact_uses_its_sections(standard_set):
    report = ingest_standard(
        pdf_path=PDFS["bpp"],
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        corpus_path=CORPUS_ARTEFACT,
    )
    assert report.created is True
    assert report.chunk_count == 9
    assert report.corpus_digest == hashlib.sha256(CORPUS_ARTEFACT.read_bytes()).hexdigest()
    assert report.layout_pages == () and report.reflow_pages == (), (
        "nothing is transformed at ingest when the text is reviewed data"
    )
    assert DocumentChunk.objects.filter(section_ref__isnull=False).count() == 0
    assert DocumentChunk.objects.filter(anchor="general-principles").exists()


LANDSCAPE_ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "landscape.md"


def test_the_landscape_page_exclusion_has_no_reach_into_the_ingest(
    standard_set, monkeypatch
):
    """D72.7 verified as "reading order restored, nothing more" — the ingest half.

    `PAGE_LAYOUT_EXCLUSIONS["landscape"] = {4:…, 5:…, 6:…, 7:…, 8:…}` is a statement about how
    the **artefact was authored**, not about how the corpus is read: an artefact ingest parses
    the reviewed sections and touches the PDF only for the printed table of contents, so the
    column transform never runs. Proved by making it explode rather than by reading the code —
    the day someone routes artefact documents through `apply_layout`, the exclusion starts
    changing what ships and this test says so.
    """

    def bomb(*args, **kwargs):  # pragma: no cover - only runs when the guard fires
        raise AssertionError(
            "apply_layout ran during an artefact ingest: the landscape's page exclusion is "
            "no longer inert (LANDSCAPE_TABLES_PRD §5.7)"
        )

    monkeypatch.setattr("knowledge.ingest.apply_layout", bomb)

    report = ingest_standard(
        pdf_path=PDFS["landscape"],
        standard_set=standard_set,
        doc_key="landscape",
        embed=False,
        corpus_path=LANDSCAPE_ARTEFACT,
    )

    assert report.created is True
    assert report.chunk_count == 17, "the reviewed artefact's measured count"
    assert report.layout_pages == () and report.reflow_pages == (), (
        "nothing is transformed at ingest when the text is reviewed data"
    )


def test_an_artefact_ingest_records_the_digest_on_the_document(standard_set):
    """The report is for the operator; the *row* is what a deploy can compare (D56).

    Without it, `corpus_check` has nothing to compare and a box can serve a corpus built
    from a review that has since changed its mind, silently.
    """
    report = ingest_standard(
        pdf_path=PDFS["bpp"],
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        corpus_path=CORPUS_ARTEFACT,
    )

    document = StandardDocument.objects.get(pk=report.document_id)
    assert document.corpus_digest == report.corpus_digest
    assert document.corpus_digest == hashlib.sha256(CORPUS_ARTEFACT.read_bytes()).hexdigest()


def test_a_pdf_ingest_records_no_artefact_digest(standard_set, undeclared_opp):
    """Empty, not absent: "parsed from the PDF at ingest" is the fact drift is measured
    against, and a guess would hide the difference between the two paths.

    The declaration is removed for this test (`undeclared_opp`): from 2026-11-01 all four
    governed documents declare a reviewed artefact, so the no-declaration path has no live
    example — and the behaviour still matters, because a deployment may add a fifth document
    before it has been reviewed.
    """
    report = ingest_standard(
        pdf_path=PDFS["opp"], standard_set=standard_set, doc_key="opp", embed=False
    )

    assert report.corpus_digest == ""
    assert StandardDocument.objects.get(pk=report.document_id).corpus_digest == ""


def test_the_artefact_and_the_pdf_produce_the_same_document(db):
    """The migration's safety net: switching a document to its artefact may not move a
    section, a page or a locator. Only the text a review corrected may differ."""
    from knowledge.models import StandardSet

    from_pdf = StandardSet.objects.create(code="bpp-pdf", label="PDF", is_default=True)
    from_corpus = StandardSet.objects.create(code="bpp-corpus", label="Corpus")
    ingest_standard(
        pdf_path=PDFS["bpp"], standard_set=from_pdf, doc_key="bpp", embed=False
    )
    ingest_standard(
        pdf_path=PDFS["bpp"],
        standard_set=from_corpus,
        doc_key="bpp",
        embed=False,
        corpus_path=CORPUS_ARTEFACT,
    )

    def identity(standard_set):
        return sorted(
            (chunk.section_ref, chunk.anchor, chunk.page, chunk.heading_path)
            for chunk in DocumentChunk.objects.filter(document__standard_set=standard_set)
        )

    assert identity(from_pdf) == identity(from_corpus)
    assert (
        DocumentChunk.objects.filter(document__standard_set=from_pdf).count()
        == DocumentChunk.objects.filter(document__standard_set=from_corpus).count()
    )


def test_the_g7_sentence_is_quotable_from_a_chunk_built_from_the_artefact(standard_set):
    """G7's acceptance: the prohibition is one contiguous, citable passage."""
    ingest_standard(
        pdf_path=PDFS["bpp"],
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        corpus_path=CORPUS_ARTEFACT,
    )
    carriers = [
        chunk
        for chunk in DocumentChunk.objects.all()
        if "The use of synthetic fertilisers (agro-chemicals) is expressly prohibited."
        in flat_text(chunk.text)
    ]
    assert len(carriers) == 1


def test_an_artefact_for_another_pdf_is_refused(standard_set, tmp_path):
    """A transcription that does not name these bytes is not this document."""
    text = CORPUS_ARTEFACT.read_text(encoding="utf-8")
    tampered = tmp_path / "bpp.md"
    tampered.write_text(
        text.replace(
            "sha256: " + CORPUS_ARTEFACT.read_text(encoding="utf-8").split("sha256: ")[1][:64],
            "sha256: " + "0" * 64,
        ),
        encoding="utf-8",
    )
    with pytest.raises(IngestError, match="built from a different PDF"):
        ingest_standard(
            pdf_path=PDFS["bpp"],
            standard_set=standard_set,
            doc_key="bpp",
            embed=False,
            corpus_path=tampered,
        )


def test_an_artefact_for_another_document_is_refused(standard_set):
    with pytest.raises(IngestError, match="artefact for"):
        ingest_standard(
            pdf_path=PDFS["bpp"],
            standard_set=standard_set,
            doc_key="opp",
            embed=False,
            corpus_path=CORPUS_ARTEFACT,
        )


# --- D55: the ingest fails closed --------------------------------------------


def test_a_document_that_declares_a_review_ingests_from_it_by_default(standard_set):
    """D55: for a document with a reviewed artefact, the artefact *is* the text of record.

    Parsing the PDF is now a deliberate act, so a deploy cannot quietly serve a heuristically
    extracted corpus that a review has already superseded.
    """
    report = ingest_standard(
        pdf_path=PDFS["bpp"], standard_set=standard_set, doc_key="bpp", embed=False
    )

    assert report.corpus_digest == hashlib.sha256(CORPUS_ARTEFACT.read_bytes()).hexdigest()
    assert report.layout_pages == () and report.reflow_pages == ()


def test_a_missing_artefact_stops_the_ingest_and_names_the_generator(standard_set, monkeypatch, tmp_path):
    """The failure D55 forbids is the silent one: no artefact, so parse the PDF anyway.

    A machine that lost `knowledge/corpus/` would otherwise serve different text from the
    review, with every guard green — the corpus is only evidence if something checks it.
    """
    monkeypatch.setattr("knowledge.ingest.CORPUS_DIR", tmp_path)

    with pytest.raises(IngestError) as caught:
        ingest_standard(
            pdf_path=PDFS["bpp"], standard_set=standard_set, doc_key="bpp", embed=False
        )

    message = str(caught.value)
    assert "bpp.md" in message, "the error must name the file it looked for"
    assert "scripts/build_corpus.py" in message, "and the command that produces it"
    assert "--from-pdf" in message, "and the flag that says 'I meant the PDF'"
    assert DocumentChunk.objects.count() == 0, "nothing may be written on the way out"


def test_from_pdf_is_still_the_diagnostic_path(standard_set):
    """D55 keeps `--from-pdf`: it is the equivalence oracle, and the only PDF parse left."""
    report = ingest_standard(
        pdf_path=PDFS["saoso"],
        standard_set=standard_set,
        doc_key="saoso",
        embed=False,
        from_pdf=True,
    )

    assert report.corpus_digest == ""
    assert report.layout_pages, "the extraction path did not run"


def test_asking_for_both_sources_at_once_is_refused(standard_set):
    with pytest.raises(IngestError, match="choose one"):
        ingest_standard(
            pdf_path=PDFS["bpp"],
            standard_set=standard_set,
            doc_key="bpp",
            embed=False,
            corpus_path=CORPUS_ARTEFACT,
            from_pdf=True,
        )


def test_a_document_with_no_declared_artefact_still_parses_its_pdf(standard_set, undeclared_opp):
    """The declaration is data, not a file-exists probe — and it must stay that way.

    The OPP was the last governed document without an artefact (P4 landed 2026-11-01), so the
    fixture removes its declaration rather than pointing at a document that has none. A test
    that needed an unreviewed governed document would fail the day the last one is reviewed,
    which is exactly what happened here.
    """
    report = ingest_standard(
        pdf_path=PDFS["opp"], standard_set=standard_set, doc_key="opp", embed=False
    )

    assert report.corpus_digest == ""
    assert report.chunk_count > 0


