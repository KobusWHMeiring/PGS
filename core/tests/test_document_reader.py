"""The document reader — the surface a citation lands on.

Three properties are load-bearing and none of them is visual: the text is **verbatim from the
stored corpus** (a reader checking a quotation against this page must find it), the anchors are
**the ones citations use** (`knowledge.reading.reading_anchor`), and the page never exposes a
sequential id or a media path (`build_principles.md` §I, §VI).

The visual questions — does landing on the clause feel like arriving in context, is it legible
at 390 px — are UAT Scenarios 3 and 5. No test here replaces them.

`test_document_reader_curated.py` is the other half: what the page does when a branch is a
**reviewed table** — the printed grid, the cross-references, the locators and the glossary.
"""

from __future__ import annotations

import pytest

from core.models import PublicDocument
from core.services._chatbot import audit_citations
from core.services._documents import reader_for
from knowledge.models import DocumentChunk, StandardDocument
from knowledge.services import chunks_by_id
from core.tests.reader_fixtures import (  # noqa: F401 - pytest discovers fixtures by name
    CORPUS_SOURCE,
    seeded_documents,
)

pytestmark = pytest.mark.django_db


def test_the_reader_is_reachable_at_the_published_code(client, seeded_documents):
    response = client.get("/documents/saoso-standard-v2.1/read/")

    assert response.status_code == 200
    assert b"free of significant contaminants" in response.content


def test_the_text_is_the_stored_text_not_a_reformatting(client, seeded_documents):
    """Asserted against the database, not a fixture string.

    The reader lays a passage out as paragraphs and lists, so the bytes are not contiguous in the
    HTML — but flattening the rendered blocks must reproduce the stored text exactly, whitespace
    aside. That is the property that lets a reader check a quotation against this page.
    """
    import re

    from knowledge.passages import flatten

    chunk = DocumentChunk.objects.get(section_ref="Appendix 2")
    reader = reader_for(PublicDocument.objects.get(code="saoso-standard-v2.1"))

    assert re.sub(r"\s+", " ", flatten(reader.passages[0].blocks)) == re.sub(
        r"\s+", " ", chunk.text
    )

    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()

    assert "free of significant contaminants" in body


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
        "/documents/saoso-standard-v2.1/read/"
        "?section=s1-genetically-modified-organism-gmo#s1-genetically-modified-organism-gmo"
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


def test_a_citation_link_selects_the_branch_and_scrolls_to_the_passage(seeded_documents):
    """The fragment scrolls, the query parameter selects: a browser never sends the fragment to
    the server, so both are needed in one link (§6.4)."""
    from core.services._chatbot import Citation

    citation = Citation(
        section_ref="Appendix 2.1",
        quote="Wood",
        chunk_id=1,
        document_code="saoso-standard-v2.1",
        reading_anchor="appendix-2-wood-bark-and-sawdust",
    )

    assert citation.read_url == (
        "/documents/saoso-standard-v2.1/read/"
        "?section=appendix-2-wood-bark-and-sawdust#appendix-2-wood-bark-and-sawdust"
    )


# --- Passage layout: the document's lists, rendered as lists -----------------


def test_the_page_renders_a_lettered_clause_as_a_list(client, seeded_documents):
    """`S5.1.3` prints `a … b …` with no punctuation and a hanging indent; the reader must show a
    list, with the marker as presentation rather than characters invented in the text."""
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    DocumentChunk.objects.create(
        document=document,
        section_ref="S5.1.3",
        heading_path="5. ANIMAL HUSBANDRY",
        page=41,
        text=(
            "5.1.3. The operator shall ensure the following conditions:\n\n"
            "a              Sufficient free movement;\n\n"
            "b              Space to stand naturally, lie down easily and\n\n"
            "               nest comfortably;"
        ),
    )
    document.chunk_count = 3
    document.save(update_fields=["chunk_count"])

    body = client.get("/documents/saoso-standard-v2.1/read/?section=s5-1-3").content.decode()

    assert "passage__list--lower-alpha" in body
    assert "Sufficient free movement;" in body
    assert "Space to stand naturally, lie down easily and nest comfortably;" in body
    assert "a. Sufficient" not in body, "the marker is a list marker, not text added to the document"


def test_a_wrapped_clause_is_one_paragraph_on_the_page(client, seeded_documents):
    """`S23.3` wraps mid-sentence on a hanging indent, and the page must show one paragraph.

    Two paragraphs meant a reader could not select the clause as one sentence, and copying the
    page glued the next clause on with no break and no space — `…property or documents.23.5.
    Operators…`. The reader only decides where a paragraph ends; not a character of the document
    changes (`BugFixes/reader_clause_line_breaks.md`).
    """
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    DocumentChunk.objects.create(
        document=document,
        section_ref="S23.3",
        heading_path="23. HUMAN RIGHTS AND SOCIAL JUSTICE",
        page=67,
        text=(
            "23.3. Operators shall not use forced or involuntary labour or apply any pressure such "
            "as retaining part of the\n"
            "         workers\u2019 wages, property or documents.\n"
            "\n"
            "23.5. Operators shall provide their employees and contractors equal opportunity."
        ),
    )
    document.chunk_count = 3
    document.save(update_fields=["chunk_count"])

    body = client.get("/documents/saoso-standard-v2.1/read/?section=s23-3").content.decode()

    assert (
        "retaining part of the workers\u2019 wages, property or documents." in body
    ), "the wrapped clause must read as one sentence"
    assert '<p class="passage__text">workers\u2019' not in body, "the continuation is not a block"
    assert body.count('<p class="passage__text">') == 2, "two clauses, two paragraphs"


def test_a_nested_list_is_rendered_inside_its_item(client, seeded_documents):
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    DocumentChunk.objects.create(
        document=document,
        section_ref="S8.1",
        heading_path="8. MUSHROOM PRODUCTION",
        page=56,
        text=(
            "8.1. Only the following substrates may be used:\n\n"
            "a  Farmyard manure:\n\n   i. from organic holdings;\n   ii. or satisfying Appendix 2;\n\n"
            "b  Products of agricultural origin."
        ),
    )
    document.chunk_count = 3
    document.save(update_fields=["chunk_count"])

    body = client.get("/documents/saoso-standard-v2.1/read/?section=s8-1").content.decode()

    assert "passage__list--lower-roman" in body
    outer = body.split("passage__list--lower-alpha", 1)[1]
    assert "passage__list--lower-roman" in outer, "the roman list must be inside the lettered item"


def test_a_chunk_overlap_is_printed_only_once(client, seeded_documents):
    """The chunker overlaps adjacent chunks for retrieval; the reader must not print the repeat.

    Measured on `S1`: eight chunks, five boundaries repeating 21–57 words. The definitions page
    printed the previous chunk's last paragraph again at the top of the next one.
    """
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    first = "one two three four five six seven eight alpha beta"
    DocumentChunk.objects.create(document=document, section_ref="S1", page=22, text=first)
    DocumentChunk.objects.create(
        document=document, section_ref="S1", page=22, text="four five six seven eight alpha beta kappa lambda"
    )
    document.chunk_count = 4
    document.save(update_fields=["chunk_count"])

    reader = reader_for(PublicDocument.objects.get(code="saoso-standard-v2.1"), section="s1")

    assert [passage.text for passage in reader.passages] == [first, "kappa lambda"]

    body = client.get("/documents/saoso-standard-v2.1/read/?section=s1").content.decode()
    assert body.count("four five six seven eight alpha beta") == 1


def test_the_page_renders_a_glossary_term_above_its_definition(client, seeded_documents):
    """`S1` is a glossary: a term on its own line, then the definition. Rendered as one paragraph,
    the definitions page was a wall of text."""
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    DocumentChunk.objects.create(
        document=document,
        section_ref="S1",
        page=22,
        text=(
            "ACB\n\nAccredited Certification Body. Accredited to ISO 17065.\n\n"
            "Habitat\n\n"
            "The area over which a plant or animal species naturally exists."
        ),
    )
    document.chunk_count = 3
    document.save(update_fields=["chunk_count"])

    body = client.get("/documents/saoso-standard-v2.1/read/?section=s1").content.decode()

    assert '<p class="passage__term" id="term-acb">ACB</p>' in body
    assert '<p class="passage__term" id="term-habitat">Habitat</p>' in body
    assert "Accredited Certification Body." in body

