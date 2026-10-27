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
from core.services._documents import reader_for
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


def test_every_chunk_has_its_anchor_in_the_tree(seeded_documents):
    """The anchors are what citations point at, so they are asserted, not assumed.

    Every branch carries its passages' anchors; only the selected branch is rendered as text.
    """
    from core.services._documents import reader_for

    reader = reader_for(PublicDocument.objects.get(code="saoso-standard-v2.1"))
    anchors = [anchor for section in reader.sections for _chunk, anchor in section.passages]

    assert anchors == ["appendix-2", "appendix-2-1"]


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
    assert [citation.reading_anchor for citation in citations] == [
        "s1",
        "s1-genetically-modified-organism-gmo",
    ], "the second chunk shares the locator, so it must be named for its own words"
    assert citations[1].read_url == (
        "/documents/saoso-standard-v2.1/read/#s1-genetically-modified-organism-gmo"
    )

    # The page renders one branch at a time (D68), so the anchor is asserted where the tree
    # puts it; Task 7/8 select the branch through `?section=` and check the rendered page.
    reader = reader_for(PublicDocument.objects.get(code="saoso-standard-v2.1"), section="s1")
    anchors = [anchor for section in reader.sections for _chunk, anchor in section.passages]
    assert "s1" in anchors and "s1-genetically-modified-organism-gmo" in anchors


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

    assert '<a class="reader__hit-locator" href="?section=appendix-2#appendix-2">' in body
    assert "<mark>contaminants</mark>" in body


def test_a_search_with_no_match_says_the_documents_do_not_settle_it(client, seeded_documents):
    body = client.get("/documents/saoso-standard-v2.1/read/?q=hydroponic").content.decode()

    assert "No passage in this document matches" in body


def test_a_citation_to_the_second_row_of_a_table_opens_that_row(client, seeded_documents):
    """`CONCORDANCE_PRD` §10.7 / `BugFixes/citation_anchor_collision.md`: 57 of 366 passages
    share a reference, so a citation to Appendix 2's second row used to open the first.

    The anchor is the passage's own words, and the link a reader follows must carry it.
    """
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    wood = DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2",
        heading_path="APPENDICES > Appendix 2",
        page=77,
        text="Wood, bark and sawdust, only if not chemically treated.",
    )
    document.chunk_count = 3
    document.save(update_fields=["chunk_count"])
    standard_set = document.standard_set

    citations, problems = audit_citations(
        [{"section_ref": "Appendix 2", "quote": wood.text}],
        chunks_by_id([wood.pk], standard_set=standard_set),
        standard_set_id=standard_set.pk,
        document_codes={CORPUS_SOURCE: "saoso-standard-v2.1"},
    )

    assert problems == ()
    citation = citations[0]
    assert citation.reading_anchor == "appendix-2-wood-bark-and-sawdust"
    assert citation.read_url.endswith("#appendix-2-wood-bark-and-sawdust")

    body = client.get(citation.read_url).content.decode()
    assert 'id="appendix-2-wood-bark-and-sawdust"' in body


# --- The concordance: a tree and one open branch -----------------------------


def test_the_reader_opens_the_first_branch_when_nothing_selects_one(seeded_documents):
    """No `?section=`: the document's beginning, not a wall of text."""
    from core.services._documents import reader_for

    reader = reader_for(PublicDocument.objects.get(code="saoso-standard-v2.1"))

    assert reader.selected is not None
    assert reader.selected.anchor == reader.sections[0].anchor
    assert all(p.anchor.startswith("appendix-2") for p in reader.passages)


def test_a_citation_anchor_selects_the_branch_that_contains_it(seeded_documents):
    """A citation names a *passage*; the tree navigates by *section*. The join is the feature."""
    from core.services._documents import reader_for

    reader = reader_for(
        PublicDocument.objects.get(code="saoso-standard-v2.1"), section="appendix-2-1"
    )

    assert reader.selected.key == "Appendix 2.1"
    assert [p.text for p in reader.passages] == [
        "Wood, bark and sawdust, only if not chemically treated."
    ]


def test_an_unknown_section_falls_back_rather_than_404ing(seeded_documents):
    """A stale link must still show the document it names."""
    from core.services._documents import reader_for

    reader = reader_for(
        PublicDocument.objects.get(code="saoso-standard-v2.1"), section="no-such-thing"
    )

    assert reader.selected.key == reader.sections[0].key


def test_only_the_open_branch_is_returned(seeded_documents):
    """The weight reduction is a property of the service, so it is asserted here and not
    inferred from a page-size measurement."""
    from core.services._documents import reader_for

    reader = reader_for(
        PublicDocument.objects.get(code="saoso-standard-v2.1"), section="appendix-2"
    )

    assert len(reader.sections) == 2
    assert [p.locator for p in reader.passages] == ["Appendix 2"]


# --- The route: a branch names itself ----------------------------------------


def test_a_branch_is_in_the_title_and_canonical_link(client, seeded_documents):
    """D68 §7.7: the standard's own words at a stable address are the one surface where SEO is
    honest — so a branch says which branch it is, and names one address for itself."""
    body = client.get("/documents/saoso-standard-v2.1/read/?section=appendix-2").content.decode()

    assert "<title>SAOSO Organic Standard v2.1 — Appendix 2" in body
    assert 'rel="canonical"' in body
    assert (
        'href="http://testserver/documents/saoso-standard-v2.1/read/?section=appendix-2"'
        in body
    )


def test_the_page_renders_one_branch_and_says_nothing_about_the_others(client, seeded_documents):
    body = client.get("/documents/saoso-standard-v2.1/read/?section=appendix-2").content.decode()

    assert "free of significant contaminants" in body
    assert "Wood, bark and sawdust" not in body


# --- The template: the tree, the pane, and what is absent --------------------


def test_the_tree_marks_the_open_branch(client, seeded_documents):
    body = client.get(
        "/documents/saoso-standard-v2.1/read/?section=appendix-2-1"
    ).content.decode()

    assert 'aria-current="page"' in body
    current = body.split('aria-current="page"', 1)[0].rsplit("<a", 1)[1]
    assert "appendix-2-1" in current


def test_the_page_states_the_printed_sections_it_does_not_hold(client, seeded_documents):
    """§10.6: the corpus is 22 of 28 printed sections. A tree presented as "the standard"
    would claim more than the corpus holds, so the page says what is absent."""
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    document.toc = [
        {
            "part": "A",
            "kind": "CLAUSE",
            "label": "3",
            "title": "Minimum Inspection Requirements",
            "printed_page": 11,
        }
    ]
    document.save(update_fields=["toc"])

    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()

    assert "not in the corpus" in body
    assert "Minimum Inspection Requirements" in body


def test_a_reserved_row_is_visible_and_is_not_a_link(client, seeded_documents):
    """`10 to 19. Left blank…`: a reader can see it, and cannot open it, because it is not text."""
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
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

    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()

    assert "Left blank to facilitate future enterprises" in body
    assert "reader__tree-link--reserved" in body
    assert 'href="?section=10-to-19"' not in body


def test_a_search_hit_links_to_its_own_passage(client, seeded_documents):
    body = client.get("/documents/saoso-standard-v2.1/read/?q=sawdust").content.decode()

    assert 'href="?section=appendix-2-1#appendix-2-1"' in body


def test_the_selected_branch_is_the_one_rendered_with_its_anchor(client, seeded_documents):
    """A citation selects a branch; the passage it names must be in the page with its id."""
    body = client.get(
        "/documents/saoso-standard-v2.1/read/?section=appendix-2-1"
    ).content.decode()

    assert 'id="appendix-2-1"' in body
    assert "Wood, bark and sawdust" in body
    assert "free of significant contaminants" not in body
