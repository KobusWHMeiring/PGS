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
