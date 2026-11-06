"""Appendix 7's grid: the row-number gutter, and a column bounded by the next one (S5-c).

Split out of `tests/tools/test_table_blocks.py` at the 30 KB file cap (`build_principles.md` §II).
The rules are the emitter's, proved in that file; this one proves the three declarations Appendix 7
needed, each against a page built at the printed 88 grid's measured edges:

* **`band` names every column's left edge once a table is wider than two columns**, so a cell that
  wraps *inside* a column is bounded by the next one — `Air,` is printed on the same line as
  `using gaseous oxygen`, and it is the products column's cell, not the practice's last two words.
* **`gutter: 1`** makes the arm's first column the printed row number: resolved and claimed against
  the page, written as the row's label, never a column the reader draws.
* **`locators`** replace the arm's transcription of a cell (`\(70^{\circ}C\)` for `70oC`) without
  supplying a character — the emitter still slices the page.

The grid below is the page's, not the arm's: the same left edges and the same wraps as
`knowledge/tests/page_fixtures.py`'s `-table` rendering of pdf 89, cut down to three rows so the
claim is readable.
"""

from __future__ import annotations

from knowledge.table_proposals import (
    ProposedLocator,
    ProposedProfile,
    ProposedRow,
    ProposedTable,
)
from scripts.table_blocks import emit
from tests.tools.test_table_blocks import first_table

# --- S5-c: Appendix 7, the row-number gutter and a column bounded by the next one -----
#
# Appendix 7 prints five columns on one line grid: the row number in the gutter, then the
# practice, its authorised products, the conditions and the limits. A cell wraps *inside* its own
# column while the next column's first line sits beside it — `Air,` is printed on the same line as
# `using gaseous oxygen`. Appendix 2's `band:` is one boundary; this table needs every column's
# left edge, and `gutter: 1` says the arm's first column is the printed row number rather than a
# column the reader prints.

APPENDIX_7_COLUMNS = (
    "Oenological practice",
    "Authorised products",
    "Conditions of use (1)",
    "Limits on use and Applications",
)
#: The left edge of each printed column on printed 88 (pdf 89), from the page's own `-table`
#: lines: the header prints them at 4, 32, 60 and 89, and the gutter occupies 0–3.
APPENDIX_7_BAND = (0, 4, 32, 60, 89)


def grid(*cells: str) -> str:
    """One printed line of Appendix 7's grid, at the page's measured left edges."""
    out = ""
    for start, cell in zip(APPENDIX_7_BAND, cells):
        out = out.ljust(start) + cell
    return out


APPENDIX_7_BODY = [
    "<!-- page: 89 printed: 88 -->",
    grid(
        "",
        "Oenological practice",
        "Authorised products",
        "Conditions of use (1)",
        "Limits on use and",
    ),
    grid("1", "Aeration or oxygenation", "Air,"),
    grid("", "using gaseous oxygen", "Gaseous oxygen"),
    grid("2", "Heat treatments", "Maximum temperature"),
    grid("", "", "70oC"),
    grid("3", "Centrifuging and", "Perlite,", "", "Use of an agent must not"),
    grid("", "filtration with or without", "Cellulose,", "", "leave undesirable"),
    grid("", "an inert filtering agent", "Diatomaceous earths", "", "residues in the treated"),
    grid("", "", "", "", "product"),
]

APPENDIX_7_ROWS = (
    ("1", "Aeration or oxygenation using gaseous oxygen", "Air, Gaseous oxygen", "", ""),
    ("2", "Heat treatments", "Maximum temperature 70oC", "", ""),
    (
        "3",
        "Centrifuging and filtration with or without an inert filtering agent",
        "Perlite, Cellulose, Diatomaceous earths",
        "",
        "Use of an agent must not leave undesirable residues in the treated product",
    ),
)

#: The arm's own header: five columns, the first of them the row-number gutter, unlabelled.
ARM_GUTTER_COLUMNS = ("",) + APPENDIX_7_COLUMNS


def appendix_7(rows=APPENDIX_7_ROWS, **profile) -> ProposedTable:
    return ProposedTable(
        index=0,
        pdf_pages=(89,),
        columns=ARM_GUTTER_COLUMNS,
        rows=tuple(ProposedRow(tuple(row)) for row in rows),
        extraction="table",
        structure="documentai-layout-v1.6-pro",
        processor="id@version",
        profile=ProposedProfile(columns=APPENDIX_7_COLUMNS, **profile),
    )


def test_a_cell_that_wraps_inside_a_column_is_bounded_by_the_next_column():
    """The plan's named guard for S5-c, and the refusal it replaces.

    Without every column's left edge the line is one run, so the practice cell's head is read as
    `Aeration or oxygenation Air,` — the neighbour's words in the middle of it — and the row is
    refused as out of printed order. With the measured grid declared, `Air,` belongs to the next
    column and each cell wraps inside its own.
    """
    _lines, emitted, refused = emit([appendix_7(gutter=1)], APPENDIX_7_BODY)
    assert emitted == ()
    assert refused[0].where == "row 1, column 2"
    assert "out of printed order" in refused[0].detail

    lines, emitted, refused = emit(
        [appendix_7(gutter=1, band={88: APPENDIX_7_BAND})], APPENDIX_7_BODY
    )
    assert refused == (), [str(refusal) for refusal in refused]
    rows = first_table(lines).rows
    assert [cell.text for cell in rows[0].cells] == [
        "Aeration or oxygenation\nusing gaseous oxygen",
        "Air,\nGaseous oxygen",
        "",
        "",
    ]
    assert rows[2].cells[3].text == (
        "Use of an agent must not\nleave undesirable\nresidues in the treated\nproduct"
    )


def test_the_gutter_is_the_rows_label_and_not_a_column():
    """`gutter: 1` says the arm's first column is the printed row number: it is resolved against
    the page like every other cell, written as the row's label, and never becomes a column the
    reader draws — the paper prints it as the row's number, which is what a citation wants."""
    lines, emitted, refused = emit(
        [appendix_7(gutter=1, band={88: APPENDIX_7_BAND})], APPENDIX_7_BODY
    )
    assert refused == (), [str(refusal) for refusal in refused]
    table = first_table(lines)
    assert table.columns == APPENDIX_7_COLUMNS
    assert [row.label for row in table.rows] == ["1", "2", "3"]
    assert all(len(row.cells) == 4 for row in table.rows)


def test_a_gutter_the_page_does_not_print_is_refused():
    """The row number is the page's characters like any other cell. A block whose label came from
    the arm rather than the paper would file a citation under a row nobody can find."""
    body = [line.replace("1   Aeration", "7   Aeration", 1) for line in APPENDIX_7_BODY]
    _lines, emitted, refused = emit(
        [appendix_7(gutter=1, band={88: APPENDIX_7_BAND})], body
    )
    assert emitted == ()
    assert refused[0].where == "row 1, column 1"
    assert "row number" in refused[0].detail


def test_a_reviewed_locator_replaces_the_arms_transcription_and_not_the_paper():
    r"""The arm writes the degree sign as LaTeX — `\(70^{\circ}C\)` — where the page prints
    `70oC`, so the cell cannot be found and the row is refused. The reviewed locator names the
    page's own characters; what reaches the block is still the page's slice, never the review's."""
    arm = r"Maximum temperature \(70^{\circ}C\)"
    rows = (APPENDIX_7_ROWS[0], ("2", "Heat treatments", arm, "", ""))
    _lines, emitted, refused = emit(
        [appendix_7(rows=rows, gutter=1, band={88: APPENDIX_7_BAND})], APPENDIX_7_BODY
    )
    assert emitted == ()
    assert refused[0].where == "row 2, column 3"

    lines, emitted, refused = emit(
        [
            appendix_7(
                rows=rows,
                gutter=1,
                band={88: APPENDIX_7_BAND},
                locators=(ProposedLocator(1, 3, "Maximum temperature 70oC"),),
            )
        ],
        APPENDIX_7_BODY,
    )
    assert refused == (), [str(refusal) for refusal in refused]
    assert first_table(lines).rows[1].cells[1].text == "Maximum temperature\n70oC"


def test_a_reviewed_locator_the_page_does_not_print_is_refused():
    """A locator is a locator: the review may replace the arm's transcription, not the paper."""
    _lines, emitted, refused = emit(
        [
            appendix_7(
                gutter=1,
                band={88: APPENDIX_7_BAND},
                locators=(ProposedLocator(0, 3, "Oxygen, air"),),
            )
        ],
        APPENDIX_7_BODY,
    )
    assert emitted == ()
    assert refused[0].where == "row 1, column 3"
