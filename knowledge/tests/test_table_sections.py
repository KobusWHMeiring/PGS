"""The printed table's skeleton — the parts, the qualifiers, the headers and the silence.

A `<!-- table … -->` block drops everything the page prints *around* the rows: the four part
headings, the three centred `South African specific` qualifiers and the two column headers.
Without them the reader renders a bare list of substances, which is what a reviewer saw on
2026-10-27 ("why is there a list of standalone inputs?").

Until S5-b that skeleton was Python data (`TABLE_SECTIONS`, `NO_CONDITION_LABEL`) beside the rows.
Now it is the block itself — `row-divider:` annotations, `cols:`, `legend:`, `silence:` — and this
file is the guard that keeps it honest: each divider must still sit, on the printed page,
immediately above the row it names. That is the `CORPUS_EDITS` idiom — a decision recorded as data
has to be shown to be *necessary and applied*, or a reprint moves the page out from under it
silently.

The page under test is the committed `-table` extraction (`knowledge/tests/page_fixtures.py`): the
gate has no PDF reader (D57), and `-table` is the pass the block's cells were read from.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.corpus import load_document
from knowledge.tables import TABLE_BANDS, align_artefact_grid, artefact_grid_for
from knowledge.tests.page_fixtures import pages

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The page's own claim, reviewed by the product owner on 2026-10-27 (D70.4 answer 1). Pinned here
#: as a golden string: the sweep in `core/tests/test_claim_discipline.py` checks it against the
#: forbidden terms, and this one checks that nobody quietly reworded the sentence the label rests on.
LEGEND = (
    "The standard prints this appendix as a table: each entry is a substance and the condition "
    "printed beside it. Where it prints no condition, nothing is permitted by its silence."
)

COLUMNS = (
    "Substances — description, compositional requirements",
    "Conditions for use",
)

#: What the reader prints where the paper's condition cell is empty. A fragment, not a sentence: it
#: sits in 19 rows, and nineteen sentences would be noise.
SILENCE = "no condition printed"

#: `(before_row, text, kind)`, in row order. Measured against the `-table` extraction, not assumed.
DIVIDERS = (
    (0, "I. PLANT AND ANIMAL ORIGIN", "part"),
    (1, "South African specific", "qualifier"),
    (3, "South African specific", "qualifier"),
    (14, "South African specific", "qualifier"),
    (15, "II. MINERAL ORIGIN", "part"),
    (26, "III. MICROBIOLOGICAL", "part"),
    (28, "IV. OTHERS", "part"),
)


def _block():
    """The artefact's Appendix 2 section and its table, parsed from the committed corpus."""
    document = load_document(REPO_ROOT / "knowledge" / "corpus" / "saoso.md")
    section = next(s for s in document.sections if s.section_ref == "Appendix 2")
    return section, section.tables[0]


def _dividers():
    """`(row index, text, kind)` for every divider the block carries, in printed order."""
    _section, table = _block()
    return tuple(
        (index, divider.text, divider.kind)
        for index, row in enumerate(table.rows)
        for divider in row.dividers
    )


@pytest.fixture(scope="module")
def table_pages() -> list[str]:
    """The SAOSO PDF as `pdftotext -table` renders it, one string per PDF page."""
    return pages("saoso", "table")


def test_the_dividers_are_the_ones_the_paper_prints():
    """Seven, in row order, with the printed wording and the kind that decides their weight."""
    assert _dividers() == DIVIDERS


@pytest.mark.parametrize("divider", DIVIDERS, ids=lambda d: f"row{d[0]}-{d[2]}")
def test_each_divider_sits_directly_above_the_row_it_names(table_pages, divider):
    """Necessary and applied, on the printed page — over the **shipped** data, not a copy of it.

    Parametrising over the artefact's own dividers is what makes this the guard the reprint needs: a
    test that iterated its own list would stay green while the block drifted (the lesson of §21: an
    instrument that holds its own copy measures itself).

    The first 25 characters of the substance cell distinguish every row here *except* rows 0 and 1,
    which print the same substance twice on purpose — the qualifier between them is what this test
    exists for, so "the next line starts like this row" is the right claim even when the text is
    shared.
    """
    before_row, text, _kind = divider
    _section, table = _block()
    row = table.rows[before_row]
    page = table_pages[row.page].splitlines()
    needle = " ".join(row.cells[0].text.split())[:25]

    for index, line in enumerate(page):
        if text not in " ".join(line.split()):
            continue
        following = next(
            (" ".join(other.split()) for other in page[index + 1 :] if other.strip()), ""
        )
        if following.startswith(needle):
            return

    pytest.fail(
        f"{text!r} is not directly above {needle!r} on printed page {row.page}: "
        "the block's dividers have drifted from the printed table"
    )


def test_the_column_headers_are_the_papers(table_pages):
    """The captured labels quote the page, and the review's sentence case is the review's."""
    _section, table = _block()
    page = table_pages[table.rows[0].page]

    assert table.columns == COLUMNS
    assert "SUBSTANCES" in page
    assert "CONDITIONS FOR USE" in page


def test_the_legend_is_the_reviewed_sentence():
    """One claim, carried once by the block, and it is the sentence the empty-cell label rests on."""
    _section, table = _block()

    assert table.legend == LEGEND
    assert "no condition" in table.legend.lower()
    assert table.legend.rstrip().endswith(
        "Where it prints no condition, nothing is permitted by its silence."
    )


def test_the_label_is_a_label_and_not_a_sentence():
    """It sits in 19 rows: a fragment, muted, never a second legend saying the same thing twice."""
    _section, table = _block()

    assert table.silence == SILENCE
    assert SILENCE[0].islower()
    assert not SILENCE.endswith(".")
    assert SILENCE not in table.legend


def test_nineteen_rows_print_no_condition():
    """The measured count, and the shape of the answer: a label where the paper is silent."""
    _section, table = _block()
    empty = [row for row in table.rows if not row.cells[1].text.strip()]

    assert len(table.rows) == 30
    assert len(empty) == 19
    guano = next(row for row in table.rows if row.cells[0].text.startswith("Guano"))
    assert not guano.cells[1].text.strip()
    assert table.rows[0].cells[1].text.strip()  # Farmyard manure does print conditions


def test_the_reader_prints_the_label_where_the_cell_is_empty():
    """The service, not the template, decides: a grid row carries the silence label, no other does."""
    section, _table = _block()
    grid = artefact_grid_for(section)
    assert grid is not None and grid.silence == SILENCE

    rows = grid.rows
    empty = [index for index, cells in enumerate(rows) if not cells[1].strip()]
    non_empty = [index for index, cells in enumerate(rows) if cells[1].strip()]
    assert len(empty) == 19 and len(non_empty) == 11


def test_the_dividers_are_aligned_to_their_rows():
    """`row.dividers` is what prints above that row, so a renderer never indexes a divider list."""
    _section, table = _block()

    assert [d.text for d in table.rows[0].dividers] == ["I. PLANT AND ANIMAL ORIGIN"]
    assert [d.text for d in table.rows[2].dividers] == []
    assert [d.text for d in table.rows[15].dividers] == ["II. MINERAL ORIGIN"]
    assert sum(len(row.dividers) for row in table.rows) == 7


def test_the_declared_band_is_the_measured_one():
    """The numbers that slice the page are reviewed data; `TABLE_BANDS` is their measurement.

    Two copies of one fact is a drift waiting to happen, so the copy that *acts* (`band:` in
    `saoso.reviewed.json`) is compared with the copy that *proves* (`TABLE_BANDS`, measured
    2026-10-21). A reprint that moves the column must change both, and this fails until it does.
    """
    import json

    reviewed = json.loads(
        (REPO_ROOT / "knowledge" / "proposals" / "saoso.reviewed.json").read_text(encoding="utf-8")
    )
    declared = {
        int(page): int(cut)
        for page, cut in reviewed["tables"][1]["band"].items()
    }
    assert declared == {76: TABLE_BANDS[76], 77: TABLE_BANDS[77], 78: TABLE_BANDS[78]}


def test_the_grid_refuses_a_corpus_that_disagrees():
    """A corpus that is not the reviewed table renders today's page — never mislabelled rows."""
    section, _table = _block()
    grid = artefact_grid_for(section)
    assert grid is not None

    assert align_artefact_grid(grid, grid.row_texts[:29]) is None
    altered = list(grid.row_texts)
    altered[0] = altered[0] + " and something the paper does not print"
    assert align_artefact_grid(grid, tuple(altered)) is None


def test_an_unreviewed_section_has_no_grid():
    """Appendices 1, 3, 4, 5 and 7 print no reviewed block, and inventing one is unreviewed data."""
    document = load_document(REPO_ROOT / "knowledge" / "corpus" / "saoso.md")
    section = next(s for s in document.sections if s.section_ref == "Appendix 3")
    assert artefact_grid_for(section) is None


# --- S5-c: Appendix 7, the row number's gutter and four printed columns ---------------
#
# Appendix 7 prints five columns on one line grid and numbers its rows in the first of them:
# `Air,` sits on the same printed line as `using gaseous oxygen`, and `70oC` on the line below
# `Maximum temperature`. The block holds the four columns the reader draws, and the printed row
# number is the row's label — what a citation says it came from.

APPENDIX_7_COLUMNS = (
    "Oenological practice",
    "Authorised products",
    "Conditions of use (1)",
    "Limits on use and Applications",
)


def _appendix_7():
    """The artefact's Appendix 7 section and its table, parsed from the committed corpus."""
    document = load_document(REPO_ROOT / "knowledge" / "corpus" / "saoso.md")
    section = next(s for s in document.sections if s.section_ref == "Appendix 7")
    return section, section.tables[0]


def test_appendix_7_is_a_four_column_grid_labelled_by_its_printed_row_numbers():
    """The gutter is not a column: seven rows, four columns, and each row's label is the number
    the page prints beside it (`6a` and `6b` as printed, not as a reviewer might number them)."""
    _section, table = _appendix_7()
    assert table.columns == APPENDIX_7_COLUMNS
    assert [len(row.cells) for row in table.rows] == [4] * 7
    assert [row.label for row in table.rows] == ["1", "2", "3", "4", "5", "6a", "6b"]


def test_the_column_beside_a_wrapped_cell_is_its_own_column():
    """The reason the grid is declared rather than inferred: `Air,` and `Gaseous oxygen` are
    printed on the same two lines as `Aeration or oxygenation` / `using gaseous oxygen`, and each
    is its own cell. A reader that took "the rest of the line" would put one inside the other."""
    _section, table = _appendix_7()
    assert table.rows[0].cells[0].text == "Aeration or oxygenation\n\nusing gaseous oxygen"
    assert table.rows[0].cells[1].text == "Air,\n\nGaseous oxygen"
    assert table.rows[1].cells[1].text == "Maximum temperature\n\n70oC"
