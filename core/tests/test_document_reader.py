"""The document reader — the surface a citation lands on.

Three properties are load-bearing and none of them is visual: the text is **verbatim from the
stored corpus** (a reader checking a quotation against this page must find it), the anchors are
**the ones citations use** (`knowledge.reading.reading_anchor`), and the page never exposes a
sequential id or a media path (`build_principles.md` §I, §VI).

The visual questions — does landing on the clause feel like arriving in context, is it legible
at 390 px — are UAT Scenarios 3 and 5. No test here replaces them.
"""

from __future__ import annotations

import pytest

from core.models import PublicDocument
from core.services._chatbot import audit_citations
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.services import chunks_by_id

pytestmark = pytest.mark.django_db

CORPUS_SOURCE = "pgs_docs/saoso-version-2.1-2026.pdf"

APPENDIX = (
    "Biodegradable processing by-products, plant or animal origin. Condition: free of "
    "significant contaminants; or composted before bringing onto organic land."
)


@pytest.fixture
def seeded_documents(db):
    """A published row and an ingested corpus document that trace to the same file.

    The equality of `source_path` and `source_file` is the join the reader depends on, so the
    fixture builds both from one constant. A fixture that faked the join would prove nothing
    about the thing that can silently break.
    """
    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    document = StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard for Organic Production and Processing",
        version="2.1",
        source_file=CORPUS_SOURCE,
        sha256="a" * 64,
        section_scheme="saoso",
    )
    DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2",
        heading_path="APPENDICES > Appendix 2",
        page=76,
        text=APPENDIX,
    )
    DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2.1",
        heading_path="APPENDICES > Appendix 2",
        page=77,
        text="Wood, bark and sawdust, only if not chemically treated.",
    )
    document.chunk_count = 2
    document.save(update_fields=["chunk_count"])

    rows = {
        "saoso": PublicDocument.objects.create(
            code="saoso-standard-v2.1",
            title="SAOSO Organic Standard v2.1",
            file_path="public/documents/saoso-standard-v2.1.pdf",
            source_path=CORPUS_SOURCE,
            is_published=True,
        ),
        "opp": PublicDocument.objects.create(
            code="opp",
            title="Principles, Policies & Procedures",
            file_path="public/documents/opp.pdf",
            source_path="pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf",
            is_published=True,
        ),
    }
    return rows


def test_the_reader_is_reachable_at_the_published_code(client, seeded_documents):
    response = client.get("/documents/saoso-standard-v2.1/read/")

    assert response.status_code == 200
    assert b"free of significant contaminants" in response.content


def test_the_text_is_the_stored_text_not_a_reformatting(client, seeded_documents):
    """Asserted against the database, not a fixture string.

    A template that rewrapped, truncated or re-flowed the passage would still look right, and
    the whole point of the surface is that a reader can check a quotation against it.
    """
    chunk = DocumentChunk.objects.get(section_ref="Appendix 2")

    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()

    assert chunk.text in body


def test_every_chunk_has_its_anchor_on_the_page(client, seeded_documents):
    """The anchors are what citations point at, so they are asserted, not assumed."""
    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()

    assert 'id="appendix-2"' in body
    assert 'id="appendix-2-1"' in body


def test_a_citation_lands_on_the_definition_itself(client, seeded_documents):
    """F7: eight SAOSO §1 chunks share `S1`, so the section anchor is not the passage.

    Every definition citation used to link to `#s1` — the top of a 21 000-character
    section — while the reader renders `s1`, `s1-2`, … for the chunks under it. The
    citation must use the reader's own id for the chunk it quotes, or the chip opens
    thousands of characters above its own quote (2026-10-27, `CHAT_TRUTHFULNESS_PRD.md`).
    """
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    acb = DocumentChunk.objects.create(
        document=document,
        section_ref="S1",
        heading_path="",
        page=22,
        text="ACB: Accredited Certification Body, accredited to ISO 17065.",
    )
    gmo = DocumentChunk.objects.create(
        document=document,
        section_ref="S1",
        heading_path="",
        page=22,
        text=(
            "Genetically Modified Organism (GMO): an organism produced through techniques "
            "in which the genetic material has been altered."
        ),
    )
    document.chunk_count = 4
    document.save(update_fields=["chunk_count"])
    standard_set = document.standard_set

    citations, problems = audit_citations(
        [
            {"section_ref": "S1", "quote": acb.text},
            {"section_ref": "S1", "quote": gmo.text},
        ],
        chunks_by_id([acb.pk, gmo.pk], standard_set=standard_set),
        standard_set_id=standard_set.pk,
        document_codes={CORPUS_SOURCE: "saoso-standard-v2.1"},
    )

    assert problems == ()
    assert [citation.reading_anchor for citation in citations] == ["s1", "s1-2"], (
        "the second chunk shares the locator, so it must carry the reader's suffix"
    )
    assert citations[1].read_url == "/documents/saoso-standard-v2.1/read/#s1-2"

    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()
    assert 'id="s1"' in body and 'id="s1-2"' in body
    gmo_passage = body.split('id="s1-2"', 1)[1]
    assert "Genetically Modified Organism" in gmo_passage[:400], (
        "the anchor must be on the passage the citation quotes"
    )


def test_an_unpublished_document_has_no_reader(client, seeded_documents):
    PublicDocument.objects.filter(code="saoso-standard-v2.1").update(is_published=False)

    assert client.get("/documents/saoso-standard-v2.1/read/").status_code == 404


def test_an_unknown_code_is_the_same_404(client, seeded_documents):
    assert client.get("/documents/no-such-document/read/").status_code == 404


def test_a_published_document_with_no_ingested_text_says_so(client, seeded_documents):
    """Not a 404 and not a 500: the document exists, its *text* is what is missing.

    A citation links here. A 404 would tell the reader the document is gone, and a 500 would
    tell them the site is broken — both false, and both leave a quotation they cannot check.
    """
    response = client.get("/documents/opp/read/")

    assert response.status_code == 200
    assert b"not published the text" in response.content


def test_the_reader_never_renders_a_sequential_id_or_a_media_path(client, seeded_documents):
    """`build_principles.md` §I: a sequential id never reaches a public surface.

    The passage anchors are section references; a `id="1"`/`id="2"` here would leak the chunk
    table's primary keys into a page anyone can read.
    """
    chunk = DocumentChunk.objects.get(section_ref="Appendix 2")

    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()

    assert f'id="{chunk.pk}"' not in body
    assert "/media/" not in body


def test_search_finds_the_passage_and_marks_the_word(client, seeded_documents):
    response = client.get("/documents/saoso-standard-v2.1/read/?q=contaminants")

    body = response.content.decode()

    assert '<a class="reader__hit-locator" href="#appendix-2">' in body
    assert "<mark>contaminants</mark>" in body


def test_a_search_with_no_match_says_the_documents_do_not_settle_it(client, seeded_documents):
    body = client.get("/documents/saoso-standard-v2.1/read/?q=hydroponic").content.decode()

    assert "No passage in this document matches" in body
