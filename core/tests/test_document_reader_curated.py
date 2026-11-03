"""The reader when the branch is a reviewed table — the grid, the links, the locators.

A curated branch is not just long text: it has a caption and a legend printed once, dividers
that name the rows under them, cells that are quoted by the chat, cross-references the paper
prints, and a locator that repeats only when the printed page changes. Those are the
properties here, and they all need `curated_rows` — a branch built from reviewed rows.

The reader page itself, its tree and its passages are `test_document_reader.py`.
"""

from __future__ import annotations

import pytest

from core.models import PublicDocument
from core.services._documents import reader_for
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from core.tests.reader_fixtures import (  # noqa: F401 - pytest discovers fixtures by name
    CORPUS_SOURCE,
)

pytestmark = pytest.mark.django_db


# --- The table branch: a curated appendix renders as the paper's table --------


@pytest.fixture
def curated_rows(db):
    """A published document whose Appendix 2 is the **30 reviewed rows**, plus one plain branch.

    The chunks are built by the same function ingest uses (`chunks_for_rows`), so the text under
    test is the reviewed text — not a hand-written row that would let the renderer pass while the
    corpus is different (`testing_hazards.md` §1.32).
    """
    from knowledge.table_chunks import chunks_for_rows

    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    document = StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Curated",
        version="2.1",
        source_file=CORPUS_SOURCE,
        sha256="c" * 64,
        section_scheme="saoso",
        toc=[
            {"part": "A", "kind": "SECTION", "label": "1", "title": "Introduction", "printed_page": 4},
            {"part": "B", "kind": "SECTION", "label": "1", "title": "Definitions", "printed_page": 22},
            {"part": "B", "kind": "SECTION", "label": "4", "title": "Crop Production", "printed_page": 35},
            {"part": "B", "kind": "SECTION", "label": "6", "title": "Wild Harvesting", "printed_page": 52},
            {"part": "B", "kind": "SECTION", "label": "22", "title": "Labelling", "printed_page": 65},
        ],
    )
    for row_chunk in chunks_for_rows("Appendix 2"):
        DocumentChunk.objects.create(
            document=document,
            section_ref=row_chunk.section_ref,
            heading_path=row_chunk.heading_path,
            page=row_chunk.page,
            text=row_chunk.text,
            token_count=row_chunk.token_count,
        )
    DocumentChunk.objects.create(
        document=document,
        section_ref="S5.1.3",
        heading_path="5. ANIMAL HUSBANDRY",
        page=41,
        text="Animals must have access to pasture during the grazing season.",
    )
    # The branches the references point at, and the two passages that print references.
    for section_ref, page, text, heading in (
        ("S4.1", 35, "Crop rotation is required.", "4. CROP PRODUCTION"),
        (
            "S1",
            22,
            "1. DEFINITIONS\n\nACB\n\nAccredited Certification Body. Accredited to ISO 17065 "
            "or international equivalent.",
            "1. DEFINITIONS",
        ),
        (
            "S6.1",
            52,
            "Harvesting is permitted; see Section 4.6.2 for the rule on wild plants.",
            "6. WILD HARVESTING",
        ),
        (
            "S22.1.7",
            65,
            "Labels must follow Section A – 2.3, Appendix 4 for inputs, and Appendix 6 for "
            "housing, and see Appendix 9 for what this standard does not say. The ACB approves "
            "a label before it is printed.",
            "22. LABELLING",
        ),
        (
            "Appendix 6a",
            76,
            "Minimum surface areas for laying hens indoors.",
            "Minimum Surface Areas for Laying Hens Indoors",
        ),
        (
            "Appendix 6b",
            76,
            "Minimum surface areas for livestock housing.",
            "Minimum Surface Areas Indoors and Outdoors and other Characteristics of Housing",
        ),
        ("Appendix 4. Table 1", 80, "Permitted products.", "Appendix 4. Table 1"),
        ("Appendix 4. Table 2", 80, "Restricted products.", "Appendix 4. Table 2"),
    ):
        DocumentChunk.objects.create(
            document=document,
            section_ref=section_ref,
            heading_path=heading,
            page=page,
            text=text,
        )
    document.chunk_count = 39
    document.save(update_fields=["chunk_count"])

    PublicDocument.objects.create(
        code="saoso-curated",
        title="SAOSO Curated",
        file_path="public/documents/saoso-curated.pdf",
        source_path=CORPUS_SOURCE,
        is_published=True,
    )
    return PublicDocument.objects.get(code="saoso-curated")


def test_the_curated_branch_reports_its_structure(curated_rows):
    """The reader says what the branch is; the page's own sentence is the reviewed one."""
    from knowledge.tables import TABLE_SECTIONS, TableDivider

    reader = reader_for(curated_rows, "", "appendix-2")

    assert reader.table is not None
    assert reader.table.section is TABLE_SECTIONS["Appendix 2"]
    assert reader.table.labels.count("no condition printed") == 19
    assert reader.passages[15].dividers == (TableDivider(15, "II. MINERAL ORIGIN", "part"),)
    assert reader.passages[2].dividers == ()
    assert reader.passages[2].note == "no condition printed"  # Guano
    assert reader.passages[0].note == ""


def test_the_page_prints_the_caption_and_the_legend_once(client, curated_rows):
    from knowledge.tables import TABLE_SECTIONS

    body = client.get("/documents/saoso-curated/read/?section=appendix-2").content.decode()
    section = TABLE_SECTIONS["Appendix 2"]

    assert body.count(section.legend) == 1
    assert section.columns[0] in body and section.columns[1] in body
    assert body.index("reader__table-bar") < body.index('<p class="passage__row">')
    assert body.count("no condition printed") == 19


def test_every_reviewed_row_renders_as_an_entry(client, curated_rows):
    """The defect this task exists for: `Guano` used to render at body weight, as prose."""
    reader = reader_for(curated_rows, "", "appendix-2")
    body = client.get("/documents/saoso-curated/read/?section=appendix-2").content.decode()

    assert all(passage.blocks[0].kind == "row" for passage in reader.passages)
    assert '<p class="passage__row">Guano</p>' in body
    assert body.count('<p class="passage__row">') == 30

    # The empty condition cell stays empty: the entry is its heading and the label, and no
    # paragraph was invented between them (silence is not permission).
    guano = body[body.index('<p class="passage__row">Guano</p>') :]
    guano = guano[: guano.index("</article>")]
    assert "passage__text" not in guano
    assert "no condition printed" in guano


def test_the_dividers_render_above_the_rows_they_name(client, curated_rows):
    body = client.get("/documents/saoso-curated/read/?section=appendix-2").content.decode()

    pane = body[body.index("reader__table-bar") :]
    assert body.count("South African specific") == 3
    assert pane.index("II. MINERAL ORIGIN") < pane.index("Calcareous and magnesium amendments")
    assert pane.index("I. PLANT AND ANIMAL ORIGIN") < pane.index("Farmyard manure, slurry and urine")


def test_a_branch_without_reviewed_rows_renders_as_before(client, curated_rows):
    """S5.1.3 is not curated: no caption, no label, and the blocks are `passage_blocks`."""
    reader = reader_for(curated_rows, "", "s5-1-3")

    assert reader.selected is not None and reader.selected.key == "S5"
    assert reader.table is None
    assert all(passage.dividers == () and passage.note == "" for passage in reader.passages)
    assert reader.passages[0].blocks[0].kind == "paragraph"

    body = client.get("/documents/saoso-curated/read/?section=s5-1-3").content.decode()

    assert "no condition printed" not in body
    assert "The standard prints this appendix as a table" not in body


def test_the_table_costs_no_extra_query(curated_rows, django_assert_num_queries):
    """Three, the same as before this slice: the structure is derived from data already in hand."""
    with django_assert_num_queries(3):
        reader_for(curated_rows, "", "appendix-2")

# --- References: the page makes the document's own cross-references clickable -


def test_a_reference_to_an_appendix_is_a_link_in_a_new_tab(client, curated_rows):
    """The measured sentence: `See Section B – Appendix 6 Minimum Surface Areas Indoors and…`.

    `Section B –` is followed by a word, not a number, so it is not a section reference and carries
    no link; the appendix reference is the target, resolved by the words the paper prints.
    """
    body = client.get("/documents/saoso-curated/read/?section=appendix-2").content.decode()
    anchor = (
        '<a class="passage__ref" href="?section=appendix-6b#appendix-6b" target="_blank" '
        'rel="noopener">Appendix 6 Minimum Surface Areas Indoors and Outdoors'
    )

    assert anchor in body
    assert body.count("Appendix 6 Minimum Surface Areas Indoors and Outdoors") == 1


def test_the_part_a_reference_explains_itself_on_the_page(client, curated_rows):
    """`Section A – 2.3` is Part A, which the corpus does not hold: never Section 2."""
    reader = reader_for(curated_rows, "", "s22-1-7")
    body = client.get(f"/documents/saoso-curated/read/?section={reader.selected.anchor}").content.decode()
    part_a = next(
        segment
        for passage in reader.passages
        for block in passage.blocks
        for segment in getattr(block, "segments", ())
        if segment.text == "Section A – 2.3"
    )

    assert part_a.branch == ""
    assert part_a.fragment == "not-in-corpus"
    assert 'href="#not-in-corpus"' in body
    assert 'id="not-in-corpus"' in body
    assert "not in this corpus" in part_a.title
    # The note is outside the phone disclosure, or a fragment inside it cannot be scrolled to.
    assert body.index('id="not-in-corpus"') > body.index("</details>")


def test_every_reference_announces_that_it_opens_a_new_tab(client, curated_rows):
    anchor = reader_for(curated_rows, "", "s22-1-7").selected.anchor
    body = client.get(f"/documents/saoso-curated/read/?section={anchor}").content.decode()
    anchors = body.count('class="passage__ref"')

    assert anchors >= 1
    assert body.count("(opens in a new tab)") == anchors


def test_an_undecidable_appendix_names_its_parts_without_becoming_a_link(client, curated_rows):
    """Bare `Appendix 4` has two tables: the tooltip says which, and the words stay text."""
    anchor = reader_for(curated_rows, "", "s22-1-7").selected.anchor
    body = client.get(f"/documents/saoso-curated/read/?section={anchor}").content.decode()

    assert '<span class="passage__ref-note" title="Appendix 4 is printed in parts:' in body
    assert "Table 1" in body and "Table 2" in body


def test_a_reference_to_a_branch_the_document_has_not_got_stays_text(client, curated_rows):
    """`Appendix 9` is what the BPP and the landscape print; this document has no such branch."""
    anchor = reader_for(curated_rows, "", "s22-1-7").selected.anchor
    body = client.get(f"/documents/saoso-curated/read/?section={anchor}").content.decode()

    assert "Appendix 9" in body
    assert "?section=appendix-9" not in body


def test_a_bare_section_resolves_inside_the_part_it_is_printed_in(client, curated_rows):
    anchor = reader_for(curated_rows, "", "s6-1").selected.anchor
    body = client.get(f"/documents/saoso-curated/read/?section={anchor}").content.decode()

    assert (
        '<a class="passage__ref" href="?section=s4-1#s4-1" target="_blank" rel="noopener">'
        "Section 4.6.2" in body
    )


def test_the_references_cost_no_extra_query(curated_rows, django_assert_num_queries):
    """Three: the index is built from the tree the page already has."""
    with django_assert_num_queries(3):
        reader_for(curated_rows, "", "s22-1-7")


# --- The locator: printed once per run ----------------------------------------


def test_the_locator_prints_once_for_a_branch_that_shares_one(client, curated_rows):
    """Thirty rows share `Appendix 2 · printed p. 76`; the reader prints it three times, not thirty.

    Every passage keeps its `id`, so a citation still lands on the row it quotes.
    """
    reader = reader_for(curated_rows, "", "appendix-2")
    body = reader.passages

    assert len(body) == 30
    assert sum(1 for passage in body if passage.show_locator) == 3
    assert [passage.show_locator for passage in body[:2]] == [True, False]

    rendered = client.get("/documents/saoso-curated/read/?section=appendix-2").content.decode()
    assert rendered.count('class="passage__locator"') == 3
    assert all(f'id="{passage.anchor}"' in rendered for passage in body)


def test_a_locator_prints_again_when_the_printed_page_changes(client, curated_rows):
    document = StandardDocument.objects.get(source_file=CORPUS_SOURCE)
    DocumentChunk.objects.create(
        document=document,
        section_ref="S5.1.3",
        heading_path="5. ANIMAL HUSBANDRY",
        page=42,
        text="A second clause on the next printed page.",
    )

    reader = reader_for(curated_rows, "", "s5-1-3")

    assert [passage.show_locator for passage in reader.passages] == [True, True]
    assert reader.passages[1].locator == reader.passages[0].locator  # same reference, new page


# --- The glossary: a defined word is a click away -----------------------------


def test_a_defined_word_links_to_its_definition(client, curated_rows):
    """`ACB` in 22.1.7 opens the glossary at the definition's own id, not at the branch's top."""
    anchor = reader_for(curated_rows, "", "s22-1-7").selected.anchor
    body = client.get(f"/documents/saoso-curated/read/?section={anchor}").content.decode()

    assert (
        '<a class="passage__ref" href="?section=s1#term-acb" target="_blank" rel="noopener">ACB'
        in body
    )


def test_the_definition_carries_the_id_the_link_names(client, curated_rows):
    body = client.get("/documents/saoso-curated/read/?section=s1").content.decode()

    assert '<p class="passage__term" id="term-acb">ACB</p>' in body


def test_the_glossary_page_does_not_link_to_itself(client, curated_rows):
    """The definitions are on this page already; 71 self-links would be noise, not navigation."""
    body = client.get("/documents/saoso-curated/read/?section=s1").content.decode()

    assert "?section=s1#term-" not in body
