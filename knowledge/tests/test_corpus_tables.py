"""The artefact's table block — parsed as structure, and **loud** when malformed.

Why this file exists at all: measured on the shipped parser, a `<!-- cell -->` annotation is
silently dropped. `ANNOTATION` matches only `corpus|page|ref`, so anything else falls through
to `COMMENT` and is treated as a reviewer's note. A table typed into an artefact therefore
loses its row boundaries with **every other guard still green** — the text is all there, the
counts still add up, and no cell can ever be cited. That is the failure mode
`product/docs/context/testing_hazards.md` exists for, so the guard comes first: an annotation
that does not parse must raise.

The structure is *parsed*, never recovered from text (`TABLES_AS_DATA_PRD` §3a rule 1). A
GFF pipe table chunks as one paragraph and blank lines between rows change nothing, so the
row and cell boundaries have to travel beside `section.text` — the way `sub_refs` carries
offsets rather than re-finding clauses.
"""

from __future__ import annotations

import pytest

from knowledge.corpus import CorpusFormatError, parse_blocks
from knowledge.tables import align_artefact_grid, artefact_grid_for

HEADER = """<!-- corpus
doc_key: landscape
source: pgs_docs/PGS Certification landscape_Final.pdf
sha256: 0000000000000000000000000000000000000000000000000000000000000000
generator: knowledge corpusgen v1
-->"""

TABLE = """<!-- table
cols: Key steps | Fee
-->
<!-- row: Step 1 -->
<!-- cell -->
Farmers who are already producing a surplus.
<!-- cell -->
R500
<!-- /table -->"""


def artefact(body: str) -> str:
    return f"{HEADER}\n{body}\n"


def page(body: str) -> str:
    return f"<!-- page: 4 printed: 4 -->\n## ESTABLISHING A PGS GROUP\n{body}"


# --------------------------------------------------------------------------------------
# The guard: every one of these is a table that cannot be parsed, and none may be ignored.
# --------------------------------------------------------------------------------------


def test_a_cell_annotation_outside_a_table_block_is_an_error():
    with pytest.raises(CorpusFormatError, match="cell.*outside a table"):
        parse_blocks(artefact(page("<!-- cell -->\nstep one")))


def test_a_row_annotation_outside_a_table_block_is_an_error():
    with pytest.raises(CorpusFormatError, match="row.*outside a table"):
        parse_blocks(artefact(page("<!-- row: Step 1 -->\nstep one")))


def test_a_table_close_without_an_open_table_is_an_error():
    with pytest.raises(CorpusFormatError, match="without an open table"):
        parse_blocks(artefact(page("<!-- /table -->\ntext")))


def test_a_table_block_that_is_never_closed_is_an_error():
    with pytest.raises(CorpusFormatError, match="never closed"):
        parse_blocks(
            artefact(
                page(
                    "<!-- table\ncols: Key steps | Fee\n-->\n<!-- row: Step 1 -->\n"
                    "<!-- cell -->\nFarmers.\n<!-- cell -->\nR500"
                )
            )
        )


def test_a_table_block_with_no_cols_field_is_an_error():
    with pytest.raises(CorpusFormatError, match="cols"):
        parse_blocks(
            artefact(
                page(
                    "<!-- table\nlegend: nothing here\n-->\n<!-- row: Step 1 -->"
                    "\n<!-- cell -->\nFarmers.\n<!-- /table -->"
                )
            )
        )


def test_an_unknown_field_in_the_table_header_is_an_error():
    with pytest.raises(CorpusFormatError, match="colums"):
        parse_blocks(
            artefact(
                page(
                    "<!-- table\ncols: Key steps | Fee\ncolums: typo\n-->\n"
                    "<!-- row: Step 1 -->\n<!-- cell -->\nFarmers.\n<!-- cell -->\nR500\n"
                    "<!-- /table -->"
                )
            )
        )


def test_a_typo_that_looks_like_a_cell_annotation_is_an_error_not_a_note():
    """The measured hazard: `<!-- cells -->` is a comment today, so the cell vanishes."""
    with pytest.raises(CorpusFormatError, match="annotation"):
        parse_blocks(
            artefact(
                page(
                    "<!-- table\ncols: Key steps | Fee\n-->\n<!-- row: Step 1 -->\n"
                    "<!-- cells -->\nFarmers.\n<!-- /table -->"
                )
            )
        )


def test_a_misspelt_annotation_outside_a_table_is_an_error_not_a_note():
    with pytest.raises(CorpusFormatError, match="annotation"):
        parse_blocks(artefact(page("<!-- celll -->\ntext")))


def test_a_cell_before_any_row_is_an_error():
    with pytest.raises(CorpusFormatError, match="before any row"):
        parse_blocks(
            artefact(
                page(
                    "<!-- table\ncols: Key steps | Fee\n-->\n<!-- cell -->\nFarmers.\n"
                    "<!-- /table -->"
                )
            )
        )


def test_a_row_with_no_cells_is_an_error():
    with pytest.raises(CorpusFormatError, match="no cells"):
        parse_blocks(
            artefact(
                page(
                    "<!-- table\ncols: Key steps | Fee\n-->\n<!-- row: Step 1 -->\n"
                    "<!-- /table -->"
                )
            )
        )


def test_a_row_with_more_cells_than_columns_is_an_error():
    with pytest.raises(CorpusFormatError, match="more cells"):
        parse_blocks(
            artefact(
                page(
                    "<!-- table\ncols: Key steps | Fee\n-->\n<!-- row: Step 1 -->\n"
                    "<!-- cell -->\nFarmers.\n<!-- cell -->\nR500\n<!-- cell -->\nspare\n"
                    "<!-- /table -->"
                )
            )
        )


def test_a_table_with_no_rows_is_an_error():
    with pytest.raises(CorpusFormatError, match="no rows"):
        parse_blocks(
            artefact(
                page("<!-- table\ncols: Key steps | Fee\n-->\n<!-- /table -->")
            )
        )


def test_a_heading_inside_a_table_block_is_an_error():
    with pytest.raises(CorpusFormatError, match="heading inside a table"):
        parse_blocks(
            artefact(
                page(
                    "<!-- table\ncols: Key steps | Fee\n-->\n## Step 1\n<!-- row: Step 1 -->"
                    "\n<!-- cell -->\nFarmers.\n<!-- cell -->\nR500\n<!-- /table -->"
                )
            )
        )


def test_a_table_before_any_heading_is_an_error():
    with pytest.raises(CorpusFormatError, match="before any heading"):
        parse_blocks(
            artefact(
                "<!-- page: 4 printed: 4 -->\n<!-- table\ncols: Key steps | Fee\n-->\n"
                "<!-- row: Step 1 -->\n<!-- cell -->\nFarmers.\n<!-- cell -->\nR500\n"
                "<!-- /table -->"
            )
        )


def test_a_second_table_header_inside_a_block_is_an_error():
    with pytest.raises(CorpusFormatError, match="already open"):
        parse_blocks(
            artefact(
                page(
                    "<!-- table\ncols: Key steps | Fee\n-->\n<!-- row: Step 1 -->\n"
                    "<!-- table\ncols: A | B\n-->\n<!-- cell -->\nFarmers.\n"
                    "<!-- /table -->"
                )
            )
        )


# --------------------------------------------------------------------------------------
# The structure itself.
# --------------------------------------------------------------------------------------


def test_a_table_parses_into_columns_rows_and_cells():
    document = parse_blocks(artefact(page(TABLE)))
    section = document.sections[0]
    assert len(section.tables) == 1
    table = section.tables[0]
    assert table.columns == ("Key steps", "Fee")
    assert len(table.rows) == 1
    row = table.rows[0]
    assert row.label == "Step 1"
    assert [cell.text for cell in row.cells] == [
        "Farmers who are already producing a surplus.",
        "R500",
    ]


def test_every_cell_is_a_slice_of_the_section_text():
    """Rule 1 of §3a: the offsets travel beside the text, so a cell is never re-found."""
    section = parse_blocks(artefact(page(TABLE))).sections[0]
    for row in section.tables[0].rows:
        for cell in row.cells:
            assert section.text[cell.start : cell.end] == cell.text


def test_the_annotations_are_not_text_but_the_cells_are():
    """The label is structure; the cells are the text. A `row:` label is not a cell."""
    section = parse_blocks(artefact(page(TABLE))).sections[0]
    assert "<!--" not in section.text
    assert "cols:" not in section.text
    assert "Farmers who are already producing a surplus." in section.text
    assert section.tables[0].rows[0].label == "Step 1", "the label travels as structure"


def test_a_row_with_no_label_takes_its_first_cell():
    body = """<!-- table
cols: Class or species | Number per ha
-->
<!-- row -->
<!-- cell -->
Ewes
<!-- cell -->
13,3
<!-- /table -->"""
    row = parse_blocks(artefact(page(body))).sections[0].tables[0].rows[0]
    assert row.label == ""
    assert row.label_text == "Ewes"


def test_a_cell_may_hold_blank_lines_and_lists():
    body = """<!-- table
cols: Class or species | Number per ha
-->
<!-- row: Sheep -->
<!-- cell -->
Ewes, rams

- first
- second
<!-- cell -->
13,3
<!-- /table -->"""
    row = parse_blocks(artefact(page(body))).sections[0].tables[0].rows[0]
    assert row.cells[0].text == "Ewes, rams\n\n- first\n- second"


def test_an_empty_cell_is_recorded_as_empty_never_as_missing():
    """§4 item 3: `silence` and `no data captured` must not look the same."""
    body = """<!-- table
cols: Key steps | Fee
-->
<!-- row: Step 1 -->
<!-- cell -->
Farmers.
<!-- cell -->
<!-- /table -->"""
    row = parse_blocks(artefact(page(body))).sections[0].tables[0].rows[0]
    assert len(row.cells) == 2
    assert row.cells[1].text == ""


def test_a_page_marker_between_rows_sets_the_second_rows_page():
    """D72.5: a row that opens on the next page carries the page it starts on."""
    body = """<!-- table
cols: Key steps | Fee
-->
<!-- row: Step 1 -->
<!-- cell -->
Farmers.
<!-- cell -->
R500
<!-- page: 5 printed: 5 -->
<!-- row: Step 2 -->
<!-- cell -->
The group agrees.
<!-- cell -->
R1 000
<!-- /table -->"""
    section = parse_blocks(artefact(page(body))).sections[0]
    assert [row.page for row in section.tables[0].rows] == [4, 5]


def test_a_row_divider_is_recorded_against_the_row_beneath_it():
    body = """<!-- table
cols: Class or species | Number per ha
-->
<!-- row: Cattle -->
<!-- cell -->
Cattle
<!-- cell -->
2
<!-- row-divider: South African specific qualifier -->
<!-- row: Sheep -->
<!-- cell -->
Ewes
<!-- cell -->
13,3
<!-- /table -->"""
    table = parse_blocks(artefact(page(body))).sections[0].tables[0]
    assert [entry.text for entry in table.rows[1].dividers] == ["South African specific"]
    assert [entry.kind for entry in table.rows[1].dividers] == ["qualifier"]
    assert table.rows[0].dividers == ()


# --------------------------------------------------------------------------------------
# One chunk per row, produced by the table code (TABLES_AS_DATA_PRD §3a rule 2).
# --------------------------------------------------------------------------------------

from knowledge.chunking import chunk_sections  # noqa: E402
from knowledge.ingest import chunks_for_sections  # noqa: E402

INTRO = (
    "The table below outlines the steps for the establishment of a PGS group and its "
    "membership to PGS SA."
)


def two_row_section() -> str:
    return page(
        f"""{INTRO}

<!-- table
cols: Key steps | Fee
-->
<!-- row: Step 1 -->
<!-- cell -->
Farmers who are already producing a surplus.
<!-- cell -->
R500
<!-- row: Step 2 -->
<!-- cell -->
The group agrees on operational procedures.
<!-- cell -->
R1 000
<!-- /table -->

Closing prose after the grid."""
    )


def test_one_chunk_per_row_and_no_chunk_holds_a_whole_table():
    document = parse_blocks(artefact(two_row_section()))
    chunks = chunks_for_sections(list(document.sections))
    row_chunks = [chunk for chunk in chunks if "Farmers who" in chunk.text or "group agrees" in chunk.text]
    assert [chunk.text for chunk in row_chunks] == [
        "Farmers who are already producing a surplus.\nR500",
        "The group agrees on operational procedures.\nR1 000",
    ]


def test_the_chunker_alone_would_flatten_the_table_into_one_chunk():
    """The measurement behind §3a rule 2, kept as a test so the reason cannot be forgotten."""
    document = parse_blocks(artefact(two_row_section()))
    naive = chunk_sections(list(document.sections))
    assert len([c for c in naive if "R500" in c.text]) == 1
    assert any("R500" in c.text and "R1 000" in c.text for c in naive), (
        "a small table is one paragraph bundle: both rows in one chunk, so neither can be cited"
    )


def test_the_prose_around_a_table_is_kept_and_ordered():
    document = parse_blocks(artefact(two_row_section()))
    chunks = chunks_for_sections(list(document.sections))
    texts = [chunk.text for chunk in chunks]
    assert any(INTRO in text for text in texts), "the lead-in is still citable"
    assert any("Closing prose after the grid." in text for text in texts)
    assert texts.index(next(t for t in texts if INTRO in t)) == 0, "document order"
    assert any("R1 000" in text for text in texts), "the last row is last"


def test_a_row_is_embedded_from_its_column_labels_not_its_cells():
    """D73's vector half: `Below R 250 000 / 1 500 / 900` describes nothing on its own.

    Measured 2026-11-01: without this, the six bands of the OPP's sliding scale ranked nowhere
    for any fee question and `/ask/` said the document "does not specify the exact assessment
    fee" — a grounded answer that was wrong by omission, and the reason a table row needs a
    second rendition at all.
    """
    document = parse_blocks(artefact(two_row_section()))
    chunks = chunks_for_sections(list(document.sections))
    rows = [chunk for chunk in chunks if chunk.embedding_text]
    assert rows, "no row carried a rendition — every row would embed its bare cells"
    for chunk in rows:
        assert "<table" not in chunk.embedding_text
        for cell in chunk.text.split("\n"):
            if cell.strip():
                assert cell.strip() in chunk.embedding_text, (cell, chunk.embedding_text)
    first = rows[0].embedding_text
    assert first.startswith(rows[0].heading_path), first
    assert "Key steps: Farmers who are already producing a surplus." in first, first
    assert "Fee: R500" in first, first


def test_a_row_with_an_empty_cell_does_not_label_the_silence():
    """An empty cell is *silence* (§4 item 3): a label with nothing after it embeds a word
    the row does not say."""
    document = parse_blocks(
        artefact(
            """<!-- page: 3 printed: 3 -->
### SEALS
<!-- table
cols: Seal | Use | Fee
-->
<!-- row: PGS Organic -->
<!-- cell -->
PGS Organic
<!-- cell -->
<!-- cell -->
R500
<!-- /table -->"""
        )
    )
    row = next(
        chunk
        for chunk in chunks_for_sections(list(document.sections))
        if chunk.embedding_text
    )
    assert "Use:" not in row.embedding_text, row.embedding_text
    assert "Fee: R500" in row.embedding_text


def test_the_prose_after_a_table_does_not_start_with_a_blank_line():
    """Measured 2026-11-01 on the OPP's §2.3: the notes under the scale began with a newline.

    A chunk's first line is what the reader shows and what the model reads first, and a row's
    end is the newline that closed it — so the slice has to skip whitespace, not keep it.
    """
    document = parse_blocks(artefact(two_row_section()))
    chunks = chunks_for_sections(list(document.sections))
    after = next(c for c in chunks if "Closing prose after the grid." in c.text)
    assert not after.text.startswith(("\n", " ", "\t")), repr(after.text[:40])


def test_a_table_section_with_no_lead_in_does_not_become_a_heading_only_chunk():
    """Measured 2026-10-30 on the landscape's `PGS SEALS AND THEIR USE` table.

    The chunker treats the heading as section text, so the prose before the first cell is a
    chunk that is *only* the heading. It is retrievable and citable and says nothing, which is
    worse than a missing chunk: the citation audit would accept a quote that names the table and
    no rule in it.
    """
    body = """<!-- page: 6 printed: 6 -->
## PGS SEALS AND THEIR USE
<!-- table
cols: Key steps | Fee
-->
<!-- row: PGS Organic -->
<!-- cell -->
Farmers who are fully compliant.
<!-- cell -->
As above
<!-- /table -->
"""
    chunks = chunks_for_sections(list(parse_blocks(artefact(body)).sections))
    assert [chunk.text for chunk in chunks] == ["Farmers who are fully compliant.\nAs above"]


def test_a_row_chunk_carries_the_page_and_a_label_derived_heading():
    body = two_row_section().replace(
        "<!-- row: Step 2 -->", "<!-- page: 5 printed: 5 -->\n<!-- row: Step 2 -->"
    )
    sections = list(parse_blocks(artefact(body)).sections)
    chunks = chunks_for_sections(sections)
    second = next(chunk for chunk in chunks if "R1 000" in chunk.text)
    assert second.page == 5, "D72.5: the page the row starts on"
    assert second.heading_path.endswith(" — Step 2")
    assert second.section_ref is None, "D42: a heading-scheme document keeps no ref"
    assert second.anchor and second.anchor != sections[0].anchor


def test_two_sections_with_the_same_row_label_get_different_anchors():
    """Requirement 6: the locator is section-scoped, so `Step 1` cannot point at the wrong table.

    Two rows with the same label *inside one section* still share a base anchor; the reader's
    `unique_anchors` suffixes the second by its own words. That is existing, tested behaviour
    (`knowledge/reading.py`), and the landscape does not print it: `Step 1` occurs once per
    table, and each table is its own section.
    """
    body = """<!-- page: 4 printed: 4 -->
## ESTABLISHING A PGS GROUP
<!-- table
cols: Key steps | Fee
-->
<!-- row: Step 1 -->
<!-- cell -->
Farmers get together.
<!-- cell -->
R500
<!-- /table -->

<!-- page: 5 printed: 5 -->
## PGS SEALS AND THEIR USE
<!-- table
cols: Use of seals | Fee
-->
<!-- row: Step 1 -->
<!-- cell -->
Groups may use the logo.
<!-- cell -->
R1 000
<!-- /table -->"""
    chunks = chunks_for_sections(list(parse_blocks(artefact(body)).sections))
    anchors = [chunk.anchor for chunk in chunks if "R500" in chunk.text or "R1 000" in chunk.text]
    assert len(anchors) == 2
    assert len(set(anchors)) == 2, anchors


def test_a_row_with_no_text_at_all_is_an_error():
    body = """<!-- table
cols: Key steps | Fee
-->
<!-- row: Step 1 -->
<!-- cell -->
<!-- cell -->
<!-- /table -->"""
    with pytest.raises(CorpusFormatError, match="no text"):
        parse_blocks(artefact(page(body)))


# --------------------------------------------------------------------------------------
# The grid the reader draws (D72.3): columns + cells, aligned to the passages it renders.
# --------------------------------------------------------------------------------------


def test_the_artefact_grid_pairs_columns_with_cells_and_aligns_the_prose_around_it():
    body = (
        "The lead-in sentence.\n\n"
        + TABLE
        + "\n\nThe trailing sentence."
    )
    section = parse_blocks(artefact(page(body))).sections[0]

    grid = artefact_grid_for(section)

    assert grid.columns == ("Key steps", "Fee")
    assert grid.rows == (("Farmers who are already producing a surplus.", "R500"),)
    assert grid.row_texts == ("Farmers who are already producing a surplus.\nR500",)

    texts = (
        "The lead-in sentence.",
        "Farmers who are already producing a surplus.\nR500",
        "The trailing sentence.",
    )
    alignment = align_artefact_grid(grid, texts)
    assert alignment.positions == (1,), "prose before/after the row is allowed"
    assert alignment.split is None, "a table with no `branch:` has no alternative path"


def test_the_grid_refuses_a_corpus_that_disagrees_with_the_artefact():
    """A stale row is worse than no grid — the same rule `structure_for` follows."""
    section = parse_blocks(artefact(page(TABLE))).sections[0]
    grid = artefact_grid_for(section)

    assert align_artefact_grid(grid, ("Farmers who are already producing a surplus.\nR5OO",)) is None
    assert align_artefact_grid(grid, ()) is None
    assert align_artefact_grid(grid, ("A different row entirely.\nR500",)) is None


def test_a_prose_section_has_no_grid():
    body = "A sentence, a second sentence, and no table at all."
    section = parse_blocks(artefact(page(body))).sections[0]
    assert artefact_grid_for(section) is None


# --------------------------------------------------------------------------------------
# D77: the shape the reader draws. Four fields in the header, each reviewed data — a row
# without a `Step` prefix is a hint, not a rule, so the fork and the titles are written.
# --------------------------------------------------------------------------------------


PROCESS = """<!-- table
cols: Key steps | Resource documents | Fee
{fields}-->
<!-- row: Step 1 -->
<!-- cell -->
Step 1

Get together.
<!-- cell -->
IFOAM PGS tool kit
<!-- cell -->
R500
<!-- row: Step 2 -->
<!-- cell -->
Step 2

Agree and establish.
<!-- cell -->
Farmer/consumer pledge example
<!-- cell -->
<!-- row: Step 3 -->
<!-- cell -->
Step 3

Visit and certify.
<!-- cell -->
Farm visit assessment form
<!-- cell -->
R350
<!-- /table -->"""


def process_table(fields: str = "") -> str:
    return PROCESS.format(fields=fields)


def test_a_table_with_no_layout_field_is_a_grid():
    """Backward compatibility, and the reason it is a default rather than a required field."""
    grid = artefact_grid_for(parse_blocks(artefact(page(TABLE))).sections[0])
    assert grid.layout == "grid"
    assert grid.branch is None
    assert grid.titles == ()
    assert grid.fee_labels == ()


def test_a_process_table_declares_its_layout_and_keeps_its_cells():
    section = parse_blocks(artefact(page(process_table("layout: process\n")))).sections[0]
    grid = artefact_grid_for(section)
    assert grid.layout == "process"
    assert len(grid.rows) == 3, "the cards are the rows; the layout changes no cell"
    assert grid.rows[0][0].startswith("Step 1"), grid.rows[0][0]


def test_the_titles_are_one_per_row_and_ride_beside_the_rows():
    fields = "layout: process\ntitle: Get together | Agree and establish | Visit and certify\n"
    grid = artefact_grid_for(parse_blocks(artefact(page(process_table(fields)))).sections[0])
    assert grid.titles == ("Get together", "Agree and establish", "Visit and certify")
    assert grid.rows[0][0].split("\n")[0] == "Step 1", "the printed label is untouched by a title"


def test_a_branch_names_the_row_where_the_remaining_rows_become_an_alternative_path():
    fields = "layout: process\nbranch: 2\n"
    grid = artefact_grid_for(parse_blocks(artefact(page(process_table(fields)))).sections[0])
    assert grid.branch == 2, "0-based, as the format says: row index 2 is the third row"


def test_a_branch_may_name_its_row_by_the_label_instead_of_its_index():
    """The index is a position; the label is what the reviewer reading the paper writes."""
    fields = "layout: process\nbranch: Step 3\n"
    grid = artefact_grid_for(parse_blocks(artefact(page(process_table(fields)))).sections[0])
    assert grid.branch == 2


def test_the_fee_labels_are_one_per_fee_box():
    fields = "layout: process\nfee_label: Steps 1–2 | Step 3\n"
    grid = artefact_grid_for(parse_blocks(artefact(page(process_table(fields)))).sections[0])
    assert grid.fee_labels == ("Steps 1–2", "Step 3"), (
        "the reviewer's own words; the renderer must not invent `joining`/`certification`"
    )


def test_the_new_header_fields_are_structure_and_not_text():
    fields = (
        "layout: process\nbranch: Step 3\ntitle: A | B | C\nfee_label: One | Two\n"
    )
    section = parse_blocks(artefact(page(process_table(fields)))).sections[0]
    for value in ("layout:", "branch:", "title:", "fee_label:"):
        assert value not in section.text, value


def test_an_unknown_layout_value_is_an_error():
    """A shape nobody drew would render as whatever the template's `else` branch guesses."""
    with pytest.raises(CorpusFormatError, match="layout.*cards"):
        parse_blocks(artefact(page(process_table("layout: cards\n"))))


def test_a_branch_index_past_the_last_row_is_an_error():
    with pytest.raises(CorpusFormatError, match="branch"):
        parse_blocks(artefact(page(process_table("layout: process\nbranch: 7\n"))))


def test_a_branch_label_that_names_no_row_is_an_error():
    with pytest.raises(CorpusFormatError, match="branch"):
        parse_blocks(artefact(page(process_table("layout: process\nbranch: Step 9\n"))))


def test_a_branch_at_the_last_row_is_an_error():
    """A fork whose alternative path has no row is a split with nothing on one side."""
    with pytest.raises(CorpusFormatError, match="branch"):
        parse_blocks(artefact(page(process_table("layout: process\nbranch: 3\n"))))


def test_a_title_list_of_the_wrong_length_is_an_error():
    with pytest.raises(CorpusFormatError, match="title"):
        parse_blocks(artefact(page(process_table("layout: process\ntitle: A | B\n"))))


def test_an_empty_title_is_an_error():
    with pytest.raises(CorpusFormatError, match="title"):
        parse_blocks(artefact(page(process_table("layout: process\ntitle: A |  | C\n"))))


def test_an_empty_fee_label_is_an_error():
    with pytest.raises(CorpusFormatError, match="fee_label"):
        parse_blocks(artefact(page(process_table("layout: process\nfee_label: Steps 1–2 |\n"))))


def test_the_alignment_carries_the_position_of_the_split():
    """The renderer stacks the paths in one column, so it needs the passage, not the row index."""
    fields = "layout: process\nbranch: 2\n"
    section = parse_blocks(artefact(page(process_table(fields)))).sections[0]
    grid = artefact_grid_for(section)
    texts = (
        "Step 1\n\nGet together.\nIFOAM PGS tool kit\nR500",
        "Step 2\n\nAgree and establish.\nFarmer/consumer pledge example\n",
        "Step 3\n\nVisit and certify.\nFarm visit assessment form\nR350",
    )
    alignment = align_artefact_grid(grid, texts)
    assert alignment.positions == (0, 1, 2)
    assert alignment.split == 2, "the third row's passage is where the alternative path begins"


def test_a_disagreeing_corpus_has_no_split_either():
    fields = "layout: process\nbranch: 2\n"
    section = parse_blocks(artefact(page(process_table(fields)))).sections[0]
    grid = artefact_grid_for(section)
    assert align_artefact_grid(grid, ("Step 1\n\nGet together.\nIFOAM PGS tool kit\nR50O",)) is None


# --------------------------------------------------------------------------------------
# The extraction the cells came from (S3, requirement 1)
# --------------------------------------------------------------------------------------
#
# `check_tables.py --pages-mode` was the last per-document fact living on a command line, and its own
# docstring said S3 is where it stops being a flag: **the landscape passes against `-table` and fails
# ten ways against `-layout`**, so a gate that defaults the pass is a gate reporting on paper it did
# not read. The block now carries it. It is validated against a fixed vocabulary because a typo
# (`tbael`) must not read as "unknown pass, judge it anyway" — the silence this file exists for.


def test_a_block_records_the_extraction_its_cells_came_from():
    body = TABLE.replace("cols: Key steps | Fee", "cols: Key steps | Fee\nextraction: table")
    table = parse_blocks(artefact(page(body))).sections[0].tables[0]
    assert table.extraction == "table"


def test_an_unknown_extraction_mode_is_an_error_not_a_silent_default():
    body = TABLE.replace("cols: Key steps | Fee", "extraction: tbael\ncols: Key steps | Fee")
    with pytest.raises(CorpusFormatError, match="is not an extraction mode"):
        parse_blocks(artefact(page(body)))


def test_a_block_with_no_extraction_field_parses_and_says_so():
    """Every artefact written before S3 has none. The parser does not invent one for them; the
    harness turns the empty string into R1, which is where the reader can act on it."""
    assert parse_blocks(artefact(page(TABLE))).sections[0].tables[0].extraction == ""


def test_the_format_and_the_page_fixtures_agree_about_the_modes():
    """The library may not import a test module, so the vocabulary is declared here and the
    fixtures are asserted equal — one list, checked, rather than two that drift."""
    from knowledge.corpus_tables import EXTRACTION_MODES
    from knowledge.tests import page_fixtures

    assert set(EXTRACTION_MODES) == set(page_fixtures.MODES)
