"""The printed table's skeleton — the parts, the qualifiers, the headers and the silence.

`TABLE_ROWS` stores the 30 reviewed rows and deliberately drops everything else about the page:
the four part headings, the three centred `South African specific` qualifiers and the two column
headers. Without them the reader renders a bare list of substances, which is what a reviewer saw on
2026-10-27 ("why is there a list of standalone inputs?").

The structure is **reviewed data**, keyed by section reference beside `TABLE_ROWS`, and this file is
the guard that keeps it honest: each divider must still sit, on the printed page, immediately above
the row it names. That is the `CORPUS_EDITS` idiom — a decision recorded as data has to be shown to
be *necessary and applied*, or a reprint moves the page out from under it silently.

The page under test is the committed `-table` extraction (`knowledge/tests/page_fixtures.py`): the
gate has no PDF reader (D57), and `-table` is the mode the rows were curated from.
"""

from __future__ import annotations

import pytest

from knowledge.tables import (
    APPENDIX_2_ROWS,
    NO_CONDITION_LABEL,
    TABLE_SECTIONS,
    TableDivider,
    section_for,
    structure_for,
)
from knowledge.tests.page_fixtures import pages

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


@pytest.fixture(scope="module")
def table_pages() -> list[str]:
    """The SAOSO PDF as `pdftotext -table` renders it, one string per PDF page."""
    return pages("saoso", "table")


@pytest.fixture(scope="module")
def texts() -> tuple[str, ...]:
    return tuple(row.text for row in APPENDIX_2_ROWS)


def _squash(text: str) -> str:
    return " ".join((text or "").split())


def test_the_dividers_are_the_ones_the_paper_prints():
    """Seven, in row order, with the printed wording and the kind that decides their weight."""
    section = TABLE_SECTIONS["Appendix 2"]

    assert len(section.dividers) == 7
    assert [(d.before_row, d.text, d.kind) for d in section.dividers] == list(DIVIDERS)
    assert all(isinstance(d, TableDivider) for d in section.dividers)


@pytest.mark.parametrize(
    "divider",
    TABLE_SECTIONS["Appendix 2"].dividers,
    ids=lambda d: f"row{d.before_row}-{d.kind}",
)
def test_each_divider_sits_directly_above_the_row_it_names(table_pages, divider):
    """Necessary and applied, on the printed page — over the **shipped** data, not a copy of it.

    Parametrising over `TABLE_SECTIONS` is what makes this the guard the reprint needs: a test that
    iterated its own list would stay green while the module drifted (the lesson of §21: an
    instrument that holds its own copy measures itself).

    The first 25 characters of the substance cell distinguish every row here *except* rows 0 and 1,
    which print the same substance twice on purpose — the qualifier between them is what this test
    exists for, so "the next line starts like this row" is the right claim even when the text is
    shared.
    """
    before_row, text, _kind = divider.before_row, divider.text, divider.kind
    row = APPENDIX_2_ROWS[before_row]
    needle = _squash(row.substance)[:25]
    page = table_pages[row.page].splitlines()

    for index, line in enumerate(page):
        if text not in _squash(line):
            continue
        following = next((_squash(other) for other in page[index + 1 :] if other.strip()), "")
        if following.startswith(needle):
            return

    pytest.fail(
        f"{text!r} is not directly above {row.substance[:40]!r} on printed page {row.page}: "
        "the reviewed structure has drifted from the printed table"
    )


def test_the_column_headers_are_the_papers(table_pages):
    """The caption quotes the page, and the review's sentence case is the review's, not the paper's."""
    section = TABLE_SECTIONS["Appendix 2"]
    page = table_pages[APPENDIX_2_ROWS[0].page]

    assert section.columns == COLUMNS
    assert "SUBSTANCES" in page
    assert "CONDITIONS FOR USE" in page


def test_the_legend_is_the_reviewed_sentence():
    """One sentence, and it carries the claim the empty-cell label must not contradict."""
    section = TABLE_SECTIONS["Appendix 2"]

    assert section.legend == LEGEND
    assert section.legend.count(".") == 2  # two sentences: what it is, and what silence means
    assert "no condition" in section.legend.lower()
    assert section.legend.rstrip().endswith(
        "Where it prints no condition, nothing is permitted by its silence."
    )


def test_the_label_is_a_label_and_not_a_sentence():
    """It sits in 19 rows: a fragment, muted, never a second legend saying the same thing twice."""
    assert NO_CONDITION_LABEL == "no condition printed"
    assert NO_CONDITION_LABEL[0].islower()
    assert not NO_CONDITION_LABEL.endswith(".")
    assert NO_CONDITION_LABEL not in TABLE_SECTIONS["Appendix 2"].legend
    assert NO_CONDITION_LABEL not in {"", " "}


def test_nineteen_rows_print_no_condition(texts):
    """The measured count, and the shape of the answer: a label per empty cell, aligned to its row."""
    structure = structure_for("Appendix 2", texts)

    assert structure is not None
    assert len(structure.labels) == 30
    assert structure.labels.count(NO_CONDITION_LABEL) == 19
    assert sum(1 for row in APPENDIX_2_ROWS if not row.condition) == 19

    guano = next(i for i, row in enumerate(APPENDIX_2_ROWS) if row.substance == "Guano")
    assert structure.labels[guano] == NO_CONDITION_LABEL
    assert structure.labels[0] == ""  # Farmyard manure does print conditions


def test_the_dividers_are_aligned_to_their_rows(texts):
    """`dividers[i]` is what prints above row `i`, so the reader never indexes by divider list."""
    structure = structure_for("Appendix 2", texts)

    assert structure is not None
    assert structure.dividers[0] == (TableDivider(0, "I. PLANT AND ANIMAL ORIGIN", "part"),)
    assert structure.dividers[2] == ()
    assert structure.dividers[15] == (TableDivider(15, "II. MINERAL ORIGIN", "part"),)
    assert sum(len(per_row) for per_row in structure.dividers) == 7


def test_structure_for_refuses_a_corpus_that_disagrees(texts):
    """A corpus that is not the reviewed table already renders today's page — never mislabelled rows."""
    assert structure_for("Appendix 2", texts[:29]) is None
    assert structure_for("Appendix 2", texts + ("extra",)) is None

    altered = list(texts)
    altered[0] = altered[0] + " and something the paper does not print"
    assert structure_for("Appendix 2", tuple(altered)) is None


def test_an_unreviewed_section_has_no_structure():
    """Appendices 1, 3, 4, 5, 6a, 6b and 7 are not curated rows; inventing structure is unreviewed data."""
    assert section_for("Appendix 3") is None
    assert section_for(None) is None
    assert structure_for("Appendix 3", ("anything",)) is None
    assert structure_for(None, ()) is None


def test_section_for_does_not_rebuild_the_data_per_call():
    """Identity, not equality: a per-request rebuild would be a silent cost on every reader page."""
    assert section_for("Appendix 2") is TABLE_SECTIONS["Appendix 2"]
