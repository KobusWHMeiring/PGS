"""The table block against the landscape's reviewed artefact, not a draft.

`test_corpus_tables.py` proves the format on synthetic tables. This file proves it on the page a
reader complained about (`LANDSCAPE_TABLES_PRD` §1): five columns, cells that are 400-character
prose paragraphs, two cells the paper leaves empty, one cell whose content is a seal's artwork
label, and a fee cell holding three separate amounts whose qualifying sentence is what makes them
readable.

**The rows live in `knowledge/corpus/landscape.md` since 2026-10-30.** They used to be a fixture
(`fixtures/landscape_p4_block.md`) that could only claim "every word is on the page"; now the
artefact is the text of record, so the guard can claim what a review must: each line a cell
carries is a contiguous run inside **one printed line** of the `-table` rendering, in the order
the page prints it. That is §8's requirement 3 corrected (§12b.1): a *cell* is not contiguous in
`-table` output, because one output line carries the current line of every column at once.

What this still does **not** pin, and `TABLE_BANDS` will at the reader step: that two lines
sitting on the *same* printed row belong to the columns they are filed under. A transposition
inside one row-line keeps its index, so it passes here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.corpus import load_document
from knowledge.ingest import chunks_for_sections
from knowledge.tests.page_fixtures import pages

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "landscape.md"

#: The fee sentence the reader reported, as the paper prints it. It spans two printed lines in
#: the cell; `flat()` joins them, so it is one contiguous sentence in the chunk.
FEE_SENTENCE = "Annual membership fee (paid by the PGS group to PGS SA): R500"


@pytest.fixture(scope="module")
def document():
    return load_document(ARTEFACT)


def sections(document):
    return {section.anchor: section for section in document.sections}


def table(document, anchor):
    return sections(document)[anchor].tables[0]


def chunks(document):
    return chunks_for_sections(list(document.sections))


def flat(text: str) -> str:
    return " ".join(text.split())


# --- The shape of the three printed tables ----------------------------------


def test_the_document_opens_three_tables_and_eight_reviewed_rows(document):
    """§11: 3 + 2 + 3 rows across three tables. The count is the review's unit of work."""
    assert [
        (section.anchor, [row.label for row in section.tables[0].rows])
        for section in document.sections
        if section.tables
    ] == [
        ("establishing-a-pgs-group", ["Step 1", "Step 2", "Step 3"]),
        ("pgs-seals-and-their-use", ["PGS Organic In-Conversion", "PGS Organic"]),
        (
            "saoso-organic-certification",
            ["Step 1", "Step 2", "For farmers wanting direct 3rd party certification"],
        ),
    ]


@pytest.mark.parametrize(
    "anchor",
    ["establishing-a-pgs-group", "pgs-seals-and-their-use", "saoso-organic-certification"],
)
def test_every_table_has_the_papers_five_columns_and_five_cells_a_row(document, anchor):
    parsed = table(document, anchor)
    assert parsed.columns == (
        "Key steps",
        "Resource documents, guidelines and requirements",
        "Use of seals and logos",
        "Seals and logos",
        "Fee",
    )
    assert [len(row.cells) for row in parsed.rows] == [5] * len(parsed.rows)


def test_a_row_belongs_to_the_page_it_starts_on(document):
    """D72.5: PDF 5 restarts the table, and Step 3 is still a row of the same table."""
    rows = table(document, "establishing-a-pgs-group").rows
    assert [row.page for row in rows] == [4, 4, 5]
    assert [row.page for row in table(document, "saoso-organic-certification").rows] == [7, 7, 8]


# --- The reader's question: what does it cost? ------------------------------


def test_the_fee_sentence_is_quotable_from_one_chunk(document):
    """`LANDSCAPE_TABLES_PRD` §11: the question the reader asked must be answerable."""
    flat_chunks = [flat(chunk.text) for chunk in chunks(document)]
    holders = [text for text in flat_chunks if FEE_SENTENCE in text]
    assert len(holders) == 1, [text[:60] for text in flat_chunks]
    assert "R500" in holders[0]
    assert "R1 000" in holders[0], "both step-1 amounts are one cell, so one chunk"


def test_the_three_amounts_live_only_in_the_fee_cell(document):
    """D72.2: a fee is a cell, never a derived fact — so it is not repeated anywhere."""
    row = table(document, "establishing-a-pgs-group").rows[0]
    fee = row.cells[4].text
    for amount in ("R500", "R1 000"):
        assert amount in fee
        assert all(amount not in cell.text for cell in row.cells[:4])


def test_the_fee_box_spans_steps_one_and_two_and_is_filed_under_step_one(document):
    """A merged cell is one cell: it cannot be split across the row boundary it crosses."""
    rows = table(document, "establishing-a-pgs-group").rows
    assert "R500" in rows[0].cells[4].text
    assert "R1 000" in rows[0].cells[4].text
    assert rows[1].cells[4].text == ""
    assert "R350" in rows[2].cells[4].text, "Step 3 carries its own fee, on its own page"


def test_the_empty_cells_are_recorded_as_empty_not_missing(document):
    """The paper is silent in two places on this row; the corpus must say so explicitly."""
    row = table(document, "establishing-a-pgs-group").rows[0]
    assert row.cells[2].text == ""
    assert row.cells[3].text == ""
    assert row.cells[0].text.startswith("Step 1")


def test_the_seal_cell_carries_the_printed_label_not_the_picture(document):
    """D72.1: the artwork cell is its printed label, and the legend records the picture."""
    row = table(document, "establishing-a-pgs-group").rows[1]
    assert row.cells[3].text == "Proud member of"
    assert "artwork" in table(document, "establishing-a-pgs-group").legend


# --- One chunk per row, and the seals' own table ----------------------------


def test_each_step_is_its_own_citation(document):
    steps = [
        chunk
        for chunk in chunks(document)
        if chunk.heading_path.endswith(("— Step 1", "— Step 2", "— Step 3"))
    ]
    # Step 1 and Step 2 appear once each on the establishing table and once on SAOSO's.
    assert len(steps) == 5
    assert {chunk.page for chunk in steps} == {4, 5, 7}
    assert all(chunk.section_ref is None for chunk in steps), "the landscape prints no numbering"


def test_a_seal_is_a_row_and_its_name_heads_the_use_of_seals_column(document):
    """D72.1: two seals, two rows; the picture is not in the text layer, so the printed name
    beside it is the locator, and the artwork cell is empty rather than invented."""
    rows = table(document, "pgs-seals-and-their-use").rows
    assert [row.cells[0].text.splitlines()[0] for row in rows] == [
        "PGS Organic In-Conversion",
        "PGS Organic",
    ]
    assert [row.cells[2].text.splitlines()[0] for row in rows] == [
        "PGS Organic In-Conversion",
        "PGS Organic",
    ]
    assert all(row.cells[3].text == "" for row in rows), "the picture is not stored"
    assert all(row.cells[4].text == "As above" for row in rows)


def test_the_third_saoso_row_is_the_direct_route_with_no_printed_step_number(document):
    row = table(document, "saoso-organic-certification").rows[2]
    assert row.page == 8
    assert row.cells[0].text.startswith("For farmers wanting direct")
    assert "Certification body" in row.cells[1].text
    assert "IFOAM Family of Standards" in row.cells[2].text
    assert "Accredited Certifying Body" in row.cells[4].text


# --- Every cell is on the page it names, line by line ------------------------

#: The one join the artefact declares: the paper prints `The group completes a self-` at the end
#: of one column's line and `assessment form …` at the start of the same column's *next* line,
#: two interleaved rows later. A rejoinable word is therefore not a run of any single printed
#: line. Declared here with both halves rather than cleaned out of the artefact, so the guard
#: stays literal for every other line and this exception has to be justified on the page.
DECLARED_JOINS = {
    "The group completes a self-assessment form (like a status": (
        "The group completes a self-",
        "assessment form (like a status",
    ),
}


def printed_page(page: int) -> list[str]:
    """One entry per printed line of the `-table` rendering, whitespace-normalised."""
    return [" ".join(line.split()) for line in pages("landscape", "table")[page - 1].splitlines()]


def first_line_holding(wanted: str, printed: list[str], after: int) -> int | None:
    """The first printed line *after* `after` that holds this run, or None.

    `after` is why a short line that the page prints several times (`PGS group.`) does not break
    the order check: the cell wants the next one, not the earliest.
    """
    for index in range(after + 1, len(printed)):
        if wanted in printed[index]:
            return index
    halves = DECLARED_JOINS.get(wanted)
    if halves:
        return first_line_holding(halves[0], printed, after)
    return None


def test_every_cell_line_is_a_verbatim_run_of_its_own_printed_table(document):
    """§8 requirement 3, **as corrected** (§12b.1) — and over the shipped rows, not a draft.

    Measured 2026-10-30: "each cell is a verbatim substring of `-table` output" is false for this
    table, and false for a reason that is not a defect. `-table` renders row-lines, not cells —
    one output line carries the current line of every column at once — so the Step 1 description
    runs

        Farmers who are already producing    •  IFOAM PGS tool kit    …   Local PGS group determines the

    and no whole cell is contiguous in it. What *is* true, and what the requirement is really
    after, is **per printed line**: every line a cell carries is a contiguous run inside one line
    of the `-table` rendering, and a cell's lines appear on the page in order. That is the check
    that catches a swapped pairing, and it is the check `TABLE_BANDS` tightens to "its own column
    range on its own line".

    Proved red 2026-10-30 four ways on the draft: `R500` → `R5OO` in the fee cell, the seal label
    `Proud member of` → `Proud member for`, two Step 1 lines swapped (which the word-presence test
    still passes), and a row's lines reversed. The swap is caught by the **order** check.
    """
    checked = 0
    for section in document.sections:
        for parsed in section.tables:
            for row in parsed.rows:
                printed = printed_page(row.page)
                for cell in row.cells:
                    cursor = -1
                    for line in cell.text.splitlines():
                        if not line.strip():
                            continue
                        wanted = " ".join(line.split())
                        found = first_line_holding(wanted, printed, cursor)
                        assert found is not None, (
                            f"this line is not a run of any printed line on PDF {row.page}: "
                            f"{wanted[:70]!r}"
                        )
                        assert found > cursor, (
                            f"printed out of order, {found} after {cursor}: {wanted[:70]!r}"
                        )
                        cursor = found
                        checked += 1
    assert checked > 250, "eight rows of five columns — a sampled handful proves nothing"
