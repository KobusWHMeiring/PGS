"""A reviewed row's blocks: a substance heading, then its condition's paragraphs.

`passage_blocks()` reads a *page*: it groups markers, joins hard wraps, and decides what a term is
from the shape of the lines around it. A curated table row is not a page — it is two reviewed cells
joined by a newline, its condition's paragraphs separated by a blank line on purpose — so it gets its
own function, and the page formatter is left exactly as it was.

The one thing that must never happen: **a row with no condition must not gain a paragraph.** The
paper's condition cell is empty and the prompt keeps *silence is not permission*; a reader that fills
the gap with an empty paragraph, or with anything else, has invented a condition. That assertion is
the reason this file exists.

These assertions run over the real 30 rows, not a hand-written row, because the shapes that break the
formatter (`Guano` with no condition, `Blood meal, meat meal, bone, bone meal` with commas, the
two-sentence *Factory farming* row) are the corpus's (`testing_hazards.md` §1.32).
"""

from __future__ import annotations

import pytest

from knowledge.passages import (
    Heading,
    Paragraph,
    RowHeading,
    Term,
    flatten,
    passage_blocks,
    row_blocks,
)
from knowledge.tables import APPENDIX_2_ROWS


def normalise(text: str) -> str:
    return " ".join((text or "").split())


def _row(substance_prefix: str):
    return next(row for row in APPENDIX_2_ROWS if row.substance.startswith(substance_prefix))


def test_a_row_is_its_substance_then_its_condition():
    """The shape, on the row every reader meets first."""
    row = APPENDIX_2_ROWS[0]

    blocks = row_blocks(row.text)

    assert blocks[0] == RowHeading("Farmyard manure, slurry and urine")
    assert all(isinstance(block, Paragraph) for block in blocks[1:])
    assert len(blocks) == 5, "one heading and the four printed condition paragraphs"
    assert blocks[1].text.startswith("Shall not constitute the main source of nitrogen")
    assert blocks[-1].text == "Forbidden if from factory farming origin."


def test_a_row_with_no_condition_is_its_heading_and_nothing_else():
    """`Guano` prints a substance and an empty cell. The reader may not fill it."""
    assert _row("Guano").substance == "Guano"

    assert row_blocks("Guano") == (RowHeading("Guano"),)


def test_a_substance_cell_with_commas_stays_one_heading():
    """The row is not split on punctuation; the cell is the substance, however long."""
    row = _row("Blood meal")

    blocks = row_blocks(row.text)

    assert blocks == (RowHeading("Blood meal, meat meal, bone, bone meal"),)


def test_a_one_paragraph_condition_is_one_paragraph():
    row = _row("Wood, bark")

    blocks = row_blocks(row.text)

    assert blocks[0].text == "Wood, bark, sawdust, wood shavings, wood ash, wood charcoal"
    assert len(blocks) == 2
    assert blocks[1].text == "Only if not chemically treated"


def test_the_condition_splits_on_blank_lines_and_never_on_a_hard_wrap():
    """A wrapped line inside a condition paragraph belongs to that paragraph.

    Synthetic, because the reviewed cells are already whitespace-normalised — the wrap this guards
    is the *page's*, which is why `passage_blocks` joins it and a row must join it too.
    """
    text = (
        "Seaweed products\n\nOnly if the need for\nuse is motivated to the control body.\n\n"
        "Fermentation products are permitted."
    )

    blocks = row_blocks(text)

    assert [block.kind for block in blocks] == ["row", "paragraph", "paragraph"]
    assert blocks[1].text == "Only if the need for use is motivated to the control body."
    assert blocks[2].text == "Fermentation products are permitted."


def test_empty_text_is_no_blocks():
    assert row_blocks("") == ()
    assert row_blocks("   \n\n  ") == ()


@pytest.mark.parametrize("row", APPENDIX_2_ROWS, ids=lambda row: row.substance[:32])
def test_a_row_is_lossless(row):
    """The guard over all 30 rows: the blocks reproduce the stored text, whitespace aside.

    `flatten()` needs no change for this — `RowHeading` carries `.text` and hits the same branch a
    `Paragraph` does — and asserting it here is what keeps that true if the block kinds change.
    """
    assert normalise(flatten(row_blocks(row.text))) == normalise(row.text)


@pytest.mark.parametrize("row", APPENDIX_2_ROWS, ids=lambda row: row.substance[:32])
def test_a_row_is_never_reinterpreted_as_prose(row):
    """No lists, no terms, no headings: a curated row has no printed structure to find.

    `passage_blocks("Guano")` returns a `Paragraph`; a row must not, because the reader sets a row
    entry and prose at different weights (D70.1).
    """
    kinds = {block.kind for block in row_blocks(row.text)}

    assert kinds <= {"row", "paragraph"}
    assert "row" in kinds


def test_the_page_formatter_is_unchanged():
    """`row_blocks` is new, not a replacement: a substance alone is still a paragraph of a page."""
    assert [block.kind for block in passage_blocks("Guano")] == ["paragraph"]
    assert RowHeading("Guano").kind == "row"
    assert Heading("1. DEFINITIONS").kind == "heading"
    assert Term("ACB").kind == "term"
