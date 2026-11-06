"""D80 S4 — the harness is proved by its failures, and the reviewed corpus passes it.

Two kinds of test, deliberately different (the pattern `test_ingestion_shapes.py` set):

* **The corpus** — the four reviewed tables (three landscape, one OPP, fourteen rows) pass every
  requirement that can be checked, against the extraction mode each artefact was built from. This
  is the first assertion in the tree whose input is a *table* rather than a human's fix.
* **The harness** — one mutation per requirement, each asserted to be *named*. A guard nobody has
  watched go red is a guard nobody has tested (`product/docs/context/testing_hazards.md` §1.5), and
  the failure mode this harness exists for — a table that lost its boundaries with every other
  guard green — is exactly the kind that reads green.

The mutations are applied to parsed objects, not to text: `dataclasses.replace` on a `ParsedTable`
is the smallest possible lie, so a violation can only come from the property it names.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from knowledge.corpus import parse_blocks
from knowledge.ingest import chunks_for_sections
from knowledge.table_chunks import row_chunk
from knowledge.table_harness import (
    REQUIREMENTS,
    check_document,
    check_table,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

HEADER = """<!-- corpus
doc_key: landscape
source: pgs_docs/PGS Certification landscape_Final.pdf
sha256: 0000000000000000000000000000000000000000000000000000000000000000
generator: knowledge corpusgen v2
-->"""

#: Two rows, one printed page, one deliberately empty cell. The page below is the *extraction*
#: (`-table` puts the two columns side by side), which is why a cell's line is a run of a printed
#: line and not the whole line.
TABLE = """<!-- page: 1 printed: 1 -->
## ESTABLISHING A PGS GROUP

<!-- table
cols: Key steps | Fee
extraction: table
-->
<!-- row: Step 1 -->
<!-- cell -->
Farmers who are already producing
a surplus.
<!-- cell -->
R500
<!-- row: Step 2 -->
<!-- cell -->
The group agrees on operational
procedures.
<!-- cell -->
<!-- /table -->"""

#: What `pdftotext -table` prints for that page: the second row's fee box is empty on the paper.
PAGE = """ESTABLISHING A PGS GROUP

Farmers who are already producing            R500
a surplus.

The group agrees on operational
procedures.
"""

PAGES = [PAGE]


def document(body: str = TABLE):
    return parse_blocks(f"{HEADER}\n{body}\n")


def only_table(parsed=None):
    parsed = parsed or document()
    section = parsed.sections[0]
    return section, section.tables[0]


def where() -> str:
    return "ESTABLISHING A PGS GROUP table 1"


def violations_of(report_or_list, requirement: str) -> list[str]:
    items = report_or_list.violations if hasattr(report_or_list, "violations") else report_or_list
    return [str(item) for item in items if item.requirement == requirement]


# ---------------------------------------------------------------------------------------
# The corpus: every reviewed table passes, in the mode its artefact was built from.
# ---------------------------------------------------------------------------------------

#: `doc_key -> (extraction mode, row count per table in document order)`. The mode is the one the
#: artefact's cells were transcribed from — `-table` for the landscape's five-column grid pages
#: (`LANDSCAPE_TABLES_PRD` §8 requirement 3), `-layout` for the OPP's three-column one. It is the
#: last per-document datum in this path, and S3's generator is where it stops being a comment.
CORPUS = {
    "landscape": ("table", (3, 2, 3)),
    "opp": ("layout", (6,)),
    # S5: Appendix 2's thirty rows, Appendix 6a's twenty and Appendix 7's seven, all emitted from
    # `-table` pages and declared on the block, in document order.
    "saoso": ("table", (30, 20, 7)),
}


@pytest.fixture
def corpus_report(doc_key):
    from knowledge.tests import page_fixtures

    mode, rows = CORPUS[doc_key]
    artefact = REPO_ROOT / "knowledge" / "corpus" / f"{doc_key}.md"
    parsed = parse_blocks(artefact.read_text(encoding="utf-8"))
    return check_document(
        parsed,
        pages=page_fixtures.pages(doc_key, mode),
        expected_rows=rows,
        expected_tables=len(rows),
    )


@pytest.mark.parametrize("doc_key", sorted(CORPUS))
def test_every_reviewed_table_passes_every_requirement(doc_key, corpus_report):
    assert corpus_report.violations == (), corpus_report.lines()


@pytest.mark.parametrize("doc_key", sorted(CORPUS))
def test_the_corpus_really_was_checked(doc_key, corpus_report):
    """A report with nothing checked is a pass that means nothing — count what was covered."""
    _, rows = CORPUS[doc_key]
    assert corpus_report.tables == len(rows)
    assert corpus_report.rows == sum(rows)


def test_the_reviewed_tables_are_seventy_one_rows():
    """A ratchet, not a budget: the register and the gate disagree by a row the moment a table is
    added, removed or re-read, and that is what this file is for."""
    total = sum(sum(rows) for _mode, rows in CORPUS.values())
    # 71 since S5-c: Appendix 7's 7 rows joined Appendix 2's 30, the landscape's 8, the OPP's 6
    # and 6a's 20. Appendix 7's printed table continues on printed 89, which no arm read and this
    # slice does not emit (PRD §3.18) — when it does, this number moves again.
    assert total == 71, "the register and the PRD disagree; re-measure both"


def test_the_harness_checks_the_chunk_the_chunker_emits():
    """The harness reads `row_chunk`; this pins that the wired chunker emits the same chunk."""
    parsed = document()
    section, table = only_table(parsed)
    emitted = [chunk.text for chunk in chunks_for_sections(list(parsed.sections))]
    for row in table.rows:
        assert row_chunk(section, row, table.columns).text in emitted


# ---------------------------------------------------------------------------------------
# The harness: one lie per requirement, and every one of them is named.
# ---------------------------------------------------------------------------------------


def test_a_table_with_no_columns_cannot_carry_column_meaning():
    """The Appendix 6a shape: 20 reviewed rows and no printed column anywhere."""
    section, table = only_table()
    found = check_table(
        section,
        replace(table, columns=()),
        where=where(),
        pages=PAGES,
        printed_to_pdf={1: 1},
        expected_row_count=2,
    )
    assert violations_of(found, "R2"), found


def test_a_cell_with_no_printed_column_is_named():
    section, table = only_table()
    row = table.rows[0]
    extra = replace(row.cells[1], text=row.cells[1].text)
    grown = replace(row, cells=row.cells + (extra,))
    found = check_table(
        section,
        replace(table, rows=(grown,) + table.rows[1:]),
        where=where(),
        pages=PAGES,
        printed_to_pdf={1: 1},
        expected_row_count=2,
    )
    assert any("prints no column" in line for line in violations_of(found, "R2")), found


def test_a_cell_that_is_not_on_its_page_is_named():
    section, table = only_table()
    row = table.rows[0]
    cells = (row.cells[0], replace(row.cells[1], text="cabbages"))
    found = check_table(
        section,
        replace(table, rows=(replace(row, cells=cells),) + table.rows[1:]),
        where=where(),
        pages=PAGES,
        printed_to_pdf={1: 1},
        expected_row_count=2,
    )
    assert any("cabbages" in line for line in violations_of(found, "R3")), found


def test_a_cell_whose_lines_are_out_of_printed_order_is_named():
    section, table = only_table()
    row = table.rows[1]
    lines = row.cells[0].text.splitlines()
    shuffled = replace(row.cells[0], text="\n".join(reversed(lines)))
    found = check_table(
        section,
        replace(table, rows=table.rows[:1] + (replace(row, cells=(shuffled, row.cells[1])),)),
        where=where(),
        pages=PAGES,
        printed_to_pdf={1: 1},
        expected_row_count=2,
    )
    assert any("The group agrees" in line for line in violations_of(found, "R3")), found


def test_cell_fidelity_without_pages_is_a_violation_and_not_a_skip():
    section, table = only_table()
    found = check_table(section, table, where=where(), expected_row_count=2)
    assert any("not asserted" in line for line in violations_of(found, "R3")), found


def test_a_wrong_row_count_is_named():
    report = check_document(document(), pages=PAGES, expected_rows=(3,), expected_tables=1)
    assert violations_of(report, "R4"), report.lines()


def test_an_undeclared_row_count_is_named():
    report = check_document(document(), pages=PAGES, expected_tables=1)
    assert any("never compared with the page" in line for line in violations_of(report, "R4"))


def test_a_document_whose_block_went_missing_fails_rather_than_passing_nothing():
    prose = TABLE.split("<!-- table")[0].rstrip() + "\n"
    report = check_document(document(prose), pages=PAGES, expected_tables=1)
    assert report.tables == 0
    assert any("went missing" in line for line in violations_of(report, "R4")), report.lines()


def test_a_fabricated_cell_is_named():
    section, table = only_table()
    row = table.rows[0]
    invented = replace(row.cells[1], text="an invented fee", start=row.cells[1].end)
    found = check_table(
        section,
        replace(table, rows=(replace(row, cells=(row.cells[0], invented)),) + table.rows[1:]),
        where=where(),
        pages=PAGES,
        printed_to_pdf={1: 1},
        expected_row_count=2,
    )
    assert any("not a slice" in line for line in violations_of(found, "R5")), found


def test_a_row_that_omits_a_cell_is_named():
    """The second row's fee cell is printed empty; dropping it is not the same as its being empty."""
    section, table = only_table()
    row = table.rows[1]
    found = check_table(
        section,
        replace(table, rows=(table.rows[0], replace(row, cells=row.cells[:1]))),
        where=where(),
        pages=PAGES,
        printed_to_pdf={1: 1},
        expected_row_count=2,
    )
    assert any("a missing cell is not an empty cell" in line for line in violations_of(found, "R5"))


def test_a_divider_claimed_by_two_rows_is_named():
    section, table = only_table()
    divider = table.rows[0].dividers or ()
    from knowledge.sections import TableRowDivider

    one = TableRowDivider("South African specific", "qualifier")
    rows = (replace(table.rows[0], dividers=(one,)), replace(table.rows[1], dividers=(one,)))
    found = check_table(
        section,
        replace(table, rows=rows),
        where=where(),
        pages=PAGES,
        printed_to_pdf={1: 1},
        expected_row_count=2,
    )
    # The message counts instead of assuming: a label may be claimed as often as the page prints
    # it, and this page prints it none of the times the two rows claim it (S5-b).
    assert any(
        "belongs to one row on each line it is printed" in line
        for line in violations_of(found, "R6")
    ), (divider, found)


def test_a_lost_glyph_in_a_cell_is_named():
    section, table = only_table()
    row = table.rows[0]
    lost = replace(row.cells[1], text="\ufffd 500")
    found = check_table(
        section,
        replace(table, rows=(replace(row, cells=(row.cells[0], lost)),) + table.rows[1:]),
        where=where(),
        pages=PAGES,
        printed_to_pdf={1: 1},
        expected_row_count=2,
    )
    assert violations_of(found, "R7"), found


def test_an_annotation_that_reached_a_cell_is_named():
    section, table = only_table()
    row = table.rows[0]
    annotation = replace(row.cells[1], text="<!-- cell -->")
    found = check_table(
        section,
        replace(table, rows=(replace(row, cells=(row.cells[0], annotation)),) + table.rows[1:]),
        where=where(),
        pages=PAGES,
        printed_to_pdf={1: 1},
        expected_row_count=2,
    )
    assert violations_of(found, "R7"), found


def test_every_requirement_has_a_way_to_fail():
    """The set of requirements is pinned: a new one needs a check *and* a mutation."""
    assert set(REQUIREMENTS) == {"R1", "R2", "R3", "R4", "R5", "R6", "R7"}
    assert all(REQUIREMENTS.values())


def test_a_cell_wrapped_at_a_hyphen_is_one_run_of_two_printed_lines():
    """The paper's own hyphenation, kept as a unit test because the corpus has exactly one case."""
    printed = ["The group completes a self-", "assessment form (like a status"]
    from knowledge.table_harness import _locate

    # The cursor comes back where the run *ends*, because the next cell line must start at or
    # after it — a cell's lines run down the page, and the wrap is inside this one line of it.
    assert _locate("The group completes a self-assessment form (like a status", printed, 0) == 1
    assert _locate("assessment form", printed, 0) == 1, "the tail is on the second line"
    assert _locate("self assessment", printed, 0) is None, (
        "a break that is not the paper's hyphenation is two lines, not one run"
    )


def test_the_corpus_check_would_notice_the_wrong_extraction():
    """Prove the corpus pass is not vacuous: the same cells against the other mode must fail.

    The landscape's tables were transcribed from `pdftotext -table`; the `-layout` extraction puts
    two columns on one printed line, so a cell's sentence is not a run of one of its lines. If this
    check passed, R3 would be asserting nothing about which page text the cells came from.
    """
    from knowledge.tests import page_fixtures

    artefact = REPO_ROOT / "knowledge" / "corpus" / "landscape.md"
    parsed = parse_blocks(artefact.read_text(encoding="utf-8"))
    report = check_document(
        parsed,
        pages=page_fixtures.pages("landscape", "layout"),
        expected_rows=CORPUS["landscape"][1],
        expected_tables=3,
    )
    assert violations_of(report, "R3"), "R3 passed on text the cells did not come from"


# ---------------------------------------------------------------------------------------
# R1 — the extraction the cells came from (S3)
# ---------------------------------------------------------------------------------------
#
# The mode was the last datum this path took from a command line (`check_tables.py --pages-mode`),
# and the landscape proves why it cannot be inferred: its reviewed cells pass against `-table` and
# fail ten ways against `-layout`. A block that does not say which pass it came from is a block the
# gate can only judge against a guess, so it is named instead.


def test_a_block_with_no_extraction_mode_is_an_r1_violation():
    plain = TABLE.replace("extraction: table\n", "")
    section, table = only_table(document(plain))
    found = check_table(
        section, table, where=where(), pages=PAGES, printed_to_pdf={1: 1}, expected_row_count=2
    )
    assert violations_of(found, "R1"), found


def test_a_block_that_records_its_extraction_passes_r1():
    section, table = only_table()
    found = check_table(
        section, table, where=where(), pages=PAGES, printed_to_pdf={1: 1}, expected_row_count=2
    )
    assert table.extraction == "table"
    assert not violations_of(found, "R1"), found


def test_a_document_whose_blocks_disagree_about_the_pass_is_named():
    """Two passes are two fixture sets, so a document that declares both is a gate about to read
    one paper and report on another. The pair is named, not averaged or defaulted."""
    from knowledge.table_harness import recorded_extraction

    other = TABLE.replace("extraction: table", "extraction: layout")
    modes, violations = recorded_extraction(document(TABLE + "\n" + other))
    assert modes == ("table", "layout")
    assert [violation.requirement for violation in violations] == ["R1"]
    assert "table" in violations[0].detail and "layout" in violations[0].detail


def test_one_mode_for_the_whole_document_has_nothing_to_disagree_about():
    from knowledge.table_harness import recorded_extraction

    modes, violations = recorded_extraction(document(TABLE + "\n" + TABLE))
    assert modes == ("table",) and violations == ()


# --- R3 and the one declared normalisation: a letter-spaced run -------------------------

LETTER_SPACED = """<!-- page: 1 printed: 1 -->
## APPENDIX 6a

<!-- table
cols: Class or species | Maximum number of animals per ha
extraction: table
-->
<!-- row: Other bovine animals less than one year old -->
<!-- cell -->
Other bovine animals less than one year old
<!-- cell -->
5
<!-- /table -->"""

#: What `pdftotext -table` prints: the class column is set in tracking, one token per letter.
SPACED_PAGE = """APPENDIX 6a

Other b o v i n e a n i m a l s less t h a n o n e year old            5
"""

#: The same row on a page that *glues* its letters: the fallback must not reach it.
GLUED_PAGE = """APPENDIX 6a

Otherbovineanimalslessthanoneyearold            5
"""


def test_r3_accepts_the_reviewed_rejoin_of_a_letter_spaced_run():
    """Appendix 6a prints `b o v i n e`; the artefact keeps the word whole because `CORPUS_EDITS`
    says so with a page number and a reason. R3 must accept that review on a line the page itself
    letter-spaces — and nowhere else."""
    parsed = document(LETTER_SPACED)
    report = check_document(parsed, pages=[SPACED_PAGE], expected_rows=(1,), expected_tables=1)
    assert report.violations == (), report.lines()


def test_r3_still_refuses_a_rejoined_cell_on_a_page_that_does_not_letter_space():
    """The guard on the guard: set spaces aside only where the page prints a spaced run. A page
    that glues its letters is not a page the review may reword."""
    parsed = document(LETTER_SPACED)
    report = check_document(parsed, pages=[GLUED_PAGE], expected_rows=(1,), expected_tables=1)
    assert any("not a contiguous run" in line for line in report.lines()), report.lines()
