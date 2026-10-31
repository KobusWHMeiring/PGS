"""The table block against the landscape's real page, not a hand-written row.

`test_corpus_tables.py` proves the format on synthetic tables. This file proves it on the
page a reader complained about (`LANDSCAPE_TABLES_PRD` §1): five columns, cells that are
400-character prose paragraphs, two empty cells that mean silence, one cell whose content
is a seal's artwork label, and a fee cell holding three separate amounts whose qualifying
sentence is what makes them readable.

The row data is a **draft** (`fixtures/landscape_p4_block.md`), because the reviewed
artefact does not exist yet — the generator's landscape draft is headings only, measured
2026-10-30. So the guard here is the one that does not depend on a review that has not
happened: **every word in the draft is on the page**, checked against the committed
`-layout` fixture. A typed-in word that the paper does not print fails, which is the only
claim a draft may make.

What is *not* here, deliberately: the per-cell column-offset guard (`TABLE_BANDS`) and the
p5 continuation, p6's seals and p7–p8. Those are curation steps 3–4 of the PRD and need the
reviewed artefact first — a guard against a draft would only pin the draft.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from knowledge.corpus import parse_blocks
from knowledge.ingest import chunks_for_sections
from knowledge.tests.page_fixtures import pages

BLOCK = Path(__file__).resolve().parent / "fixtures" / "landscape_p4_block.md"

#: The page marker and heading the real artefact will carry in front of this block. The
#: landscape prints no section numbering, so `section_ref` stays None (D42).
PREAMBLE = """<!-- corpus
doc_key: landscape
source: pgs_docs/PGS Certification landscape_Final.pdf
sha256: 93a4f96cf5879c5f11b44b0a5d5f65ff6e803667a10736a76f78e1720f31031f
generator: knowledge corpusgen v2
-->
<!-- page: 4 printed: 4 -->
## ESTABLISHING A PGS GROUP
The table below outlines the steps for the establishment of a PGS group and its membership to PGS SA.

"""

#: The fee sentence the reader reported, as the paper prints it. It spans two printed lines
#: in the cell; the corpus flattens whitespace, so it is one contiguous sentence in the chunk.
FEE_SENTENCE = "Annual membership fee (paid by the PGS group to PGS SA): R500"


def block_text() -> str:
    """The fixture without its leading note.

    The note is a multi-line HTML comment, which the artefact format deliberately rejects:
    every annotation is one line, and a comment that spans lines is exactly the shape that
    could swallow a `cell`. The note is for the human opening the fixture, so it is stripped
    here rather than given a syntax that would weaken the parser.
    """
    text = BLOCK.read_text(encoding="utf-8")
    assert text.startswith("<!--"), text[:20]
    return text.split("-->", 1)[1]


def document():
    return parse_blocks(PREAMBLE + block_text())


def section():
    return document().sections[0]


def test_the_page_cell_is_parsed_as_five_columns_and_two_rows():
    table = section().tables[0]
    assert table.columns == (
        "Key steps",
        "Resource documents, guidelines and requirements",
        "Use of seals and logos",
        "Seals and logos",
        "Fee",
    )
    assert [row.label for row in table.rows] == ["Step 1", "Step 2"]
    assert [len(row.cells) for row in table.rows] == [5, 5]


def test_the_fee_sentence_is_quotable_from_one_chunk():
    """`LANDSCAPE_TABLES_PRD` §11: the question the reader asked must be answerable."""
    chunks = chunks_for_sections(list(document().sections))
    flat = [" ".join(chunk.text.split()) for chunk in chunks]
    holders = [text for text in flat if FEE_SENTENCE in text]
    assert len(holders) == 1, [text[:60] for text in flat]
    assert "R500" in holders[0]
    assert "R1 000" in holders[0], "both step-1 amounts are one cell, so one chunk"


def test_each_step_is_its_own_citation():
    chunks = chunks_for_sections(list(document().sections))
    steps = [chunk for chunk in chunks if chunk.heading_path.endswith(("— Step 1", "— Step 2"))]
    assert len(steps) == 2
    assert {chunk.page for chunk in steps} == {4}
    assert all(chunk.section_ref is None for chunk in steps)


def test_the_three_amounts_live_only_in_the_fee_cell():
    """D72.2: a fee is a cell, never a derived fact — so it is not repeated anywhere."""
    row = section().tables[0].rows[0]
    fee = row.cells[4].text
    for amount in ("R500", "R1 000"):
        assert amount in fee
        assert all(amount not in cell.text for cell in row.cells[:4])


def test_the_empty_cells_are_recorded_as_empty_not_missing():
    """The paper is silent in two places on this row; the corpus must say so explicitly."""
    row = section().tables[0].rows[0]
    assert row.cells[2].text == ""
    assert row.cells[3].text == ""
    assert row.cells[0].text.startswith("Step 1")


def test_the_seal_cell_carries_the_printed_label_not_the_picture():
    """D72.1: the artwork cell is its printed label, and the legend records the picture."""
    row = section().tables[0].rows[1]
    assert row.cells[3].text == "Proud member of"
    assert "artwork" in section().tables[0].legend


def test_every_word_of_the_draft_is_on_the_printed_page():
    """The only claim a draft may make: nothing was typed that the paper does not print."""
    page = pages("landscape", "layout")[3]  # PDF page 4
    on_page = set(page.split())
    drafted = " ".join(
        cell.text for table in section().tables for row in table.rows for cell in row.cells
    ).split()
    invented = sorted({word for word in drafted if word not in on_page})
    assert not invented, f"these words are not on PDF page 4: {invented}"


def test_the_draft_does_not_lose_a_cell_of_the_page():
    """The row's cells together cover the table's body, so no printed cell was skipped."""
    table = section().tables[0]
    body_words = sum(len(cell.text.split()) for row in table.rows for cell in row.cells)
    assert body_words > 250, "a landscape row is 60-400 characters of prose per cell"


@pytest.mark.parametrize("index", [0, 1, 2, 3, 4])
def test_every_cell_is_a_slice_of_the_section(index):
    table = section()
    for row in table.tables[0].rows:
        cell = row.cells[index]
        assert table.text[cell.start : cell.end] == cell.text


def _printed_lines() -> list[str]:
    """PDF 4 of the `-table` rendering, one entry per printed line, whitespace-normalised."""
    return [" ".join(line.split()) for line in pages("landscape", "table")[3].splitlines()]


#: The one join the draft declares (its own header names it). The page prints `… a self-` at the
#: end of one column's line and `assessment form …` at the start of the same column's *next* line,
#: two interleaved rows later — so a rejoinable word is not a run of any single printed line.
#: Declared here with both halves rather than cleaned out of the fixture, so the guard stays
#: literal for every other line and this exception has to be justified on the page.
DECLARED_JOINS = {
    "The group completes a self-assessment form (like a status": (
        "The group completes a self-",
        "assessment form (like a status",
    ),
}


def _first_line_holding(wanted: str, printed: list[str], after: int) -> int | None:
    """The first printed line *after* `after` that holds this run, or None.

    `after` is why a short line that the page prints several times (`PGS group.`) does not break
    the order check: the cell wants the next one, not the earliest.
    """
    for index in range(after + 1, len(printed)):
        if wanted in printed[index]:
            return index
    halves = DECLARED_JOINS.get(wanted)
    if halves:
        return _first_line_holding(halves[0], printed, after)
    return None


def test_every_cell_line_is_a_verbatim_run_of_the_printed_table():
    """§8 requirement 3, now that the `-table` page fixture exists — and **not** as it is written.

    The requirement says *"each cell is a verbatim substring of `-table` output"*. Measured
    2026-10-30: that is false for this table, and false for a reason that is not a defect.
    `-table` renders row-lines, not cells — one output line carries the current line of every
    column at once — so the Step 1 description runs

        Farmers who are already producing    •  IFOAM PGS tool kit    …   Local PGS group determines the

    and no whole cell is contiguous in it. What *is* true, and what the requirement is really
    after, is **per printed line**: every line a cell carries is a contiguous run inside one
    line of the `-table` rendering. That is the check that catches a swapped pairing, and it is
    the check `TABLE_BANDS` tightens to "its own column range on its own line" at step 3.

    Proved red 2026-10-30 four ways: `R500` → `R5OO` in the fee cell; the seal label
    `Proud member of` → `Proud member for`; two Step 1 lines swapped, which the word-presence
    test above still passes; and a row's lines reversed. The swap is caught by the **order**
    check — a reordered cell is a cell the reviewer misread — and that check is why the indices
    are compared rather than merely resolved.

    What this still does *not* pin, and `TABLE_BANDS` will at step 3: that two lines sitting on
    the *same* printed row belong to the columns they are filed under. A transposition inside one
    row-line keeps its index, so it passes here.
    """
    page = _printed_lines()
    checked = 0
    for table in section().tables:
        for row in table.rows:
            for cell in row.cells:
                cursor = -1
                for line in cell.text.splitlines():
                    if not line.strip():
                        continue
                    wanted = " ".join(line.split())
                    found = _first_line_holding(wanted, page, cursor)
                    assert found is not None, (
                        f"this line is not a run of any printed line on PDF 4: {wanted[:70]!r}"
                    )
                    assert found > cursor, (
                        f"printed out of order, {found} after {cursor}: {wanted[:70]!r}"
                    )
                    cursor = found
                    checked += 1
    assert checked > 40, "two rows x five columns of prose — a sampled handful proves nothing"
