"""`scripts/table_blocks.py` — the emitter: the arm's structure, the page's characters, a refusal by name.

The three rules this file proves, one test each, and the third is the one that costs a review if it
is missing:

1. **A cell's characters are the page's.** The arm proposes a boundary; what reaches the artefact is
   a run of the body's printed lines, sliced out — so a cell can never hold a character the page did
   not print (requirement 3 and R9 read together). The arm's own spelling (`bovine`, `70°C`) is not
   what gets written, and where it disagrees with the paper by more than spacing the table is refused.
2. **Cells resolve in one forward-only cursor.** A cell cannot stitch a line from above the table into
   a row, and a table whose cells are printed out of order is refused rather than silently re-ordered.
3. **Everything inside the region is claimed by a cell.** A printed line nobody claims is a line the
   corpus loses, and `--force` would then delete text while every character-level guard stayed green
   (`testing_hazards.md` §3.25).

Nothing here reads a PDF, a fixture or a credential: the body lines are the input, and the same
function is called by `build_corpus.py` and by the tests that build the body from committed pages.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.corpus import parse_blocks
from knowledge.table_harness import check_document
from knowledge.extraction import sha256_of
from knowledge.table_proposals import (
    ProposedDivider,
    ProposedProfile,
    ProposedRow,
    ProposedTable,
    ProposedTail,
    proposals_for,
)
from tests.tools.draft_fixtures import fixture_body
from scripts.table_blocks import emit

FEE_COLUMNS = (
    "Annual farm turnover (gross sales)",
    "Initial certification fee (R)",
    "Renewal fee (R)",
)

HEADER = """<!-- corpus
doc_key: opp
source: pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf
sha256: 0000000000000000000000000000000000000000000000000000000000000000
generator: knowledge corpusgen v2
-->"""

BODY = [
    "<!-- page: 2 printed: 2 -->",
    "Annual farm turnover (gross sales) Initial certification fee (R) Renewal fee (R)",
    "Below R 250,000 1,500 900",
    "Above R 5,000,000 8,000 8,000",
    "● Fees are per farm assessment visit.",
]

ROWS = (("Below R 250,000", "1,500", "900"), ("Above R 5,000,000", "8,000", "8,000"))


def proposal(rows=ROWS, columns=FEE_COLUMNS, pdf_pages=(2,), **profile) -> ProposedTable:
    return ProposedTable(
        index=0,
        pdf_pages=pdf_pages,
        columns=columns,
        rows=tuple(ProposedRow(tuple(row)) for row in rows),
        extraction=profile.pop("extraction", "layout"),
        structure="documentai-layout-v1.6-pro",
        processor="id@version",
        profile=ProposedProfile(**profile),
    )


def artefact_of(lines) -> str:
    """The emitted body as artefact text. A heading goes in because a block outside a section is not
    a table the parser will accept — the emitter always writes inside a section."""
    lines = list(lines)
    marker = lines[0] if lines and lines[0].startswith("<!-- page:") else ""
    rest = lines[1:] if marker else lines
    head = f"{marker}\n" if marker else ""
    return f"{HEADER}\n{head}## 2.3 A heading\n" + "\n".join(rest) + "\n"


def first_table(lines):
    document = parse_blocks(artefact_of(lines))
    return next(table for section in document.sections for table in section.tables)


# --- rule 1: the characters are the page's -------------------------------------------


def test_a_cell_is_the_pages_characters_not_the_arms_spelling():
    """R3's rule read backwards. The arm may report `bovine` for a page that prints `b o v i n e`,
    and what reaches the artefact is the page's run, because that is the only thing the harness can
    locate on the paper."""
    body = ["<!-- page: 2 printed: 2 -->", "Description Fee", "b o v i n e   Cattle", "1,500  900"]
    lines, emitted, refused = emit(
        [proposal([("bovine", "Cattle"), ("1,500", "900")], columns=("Description", "Fee"))], body
    )
    assert refused == ()
    assert "b o v i n e" in lines, "the arm's characters are not what gets written"
    assert [cell.text for cell in first_table(lines).rows[0].cells] == ["b o v i n e", "Cattle"]


def test_a_cell_the_page_does_not_print_is_refused_and_its_prose_is_left_alone():
    body = ["<!-- page: 2 printed: 2 -->", "Temperature", "70oC for 30 minutes"]
    lines, emitted, refused = emit([proposal([("70°C",)], columns=("Temperature",))], body)
    assert lines == body, "a refused table must not touch the draft"
    assert emitted == ()
    assert refused[0].where == "row 1, column 1"
    assert "70°C" in refused[0].detail
    assert str(refused[0]).startswith("proposal 1")


def test_the_arm_may_disagree_about_spacing_but_not_about_a_word():
    """`1,500` and `1,500 ` are one cell; `1,5OO` is a different one, and the second is refused."""
    body = ["<!-- page: 2 printed: 2 -->", "a b", "1,500  900"]
    assert emit([proposal([("1,500 ", "900")], columns=("a", "b"))], body)[2] == ()
    _lines, _emitted, refused = emit([proposal([("1,5OO", "900")], columns=("a", "b"))], body)
    assert refused and "1,5OO" in refused[0].detail


# --- rule 2: one forward cursor ------------------------------------------------------


def test_a_cell_printed_above_the_row_it_is_filed_under_is_refused():
    """The merged box / page-order defect: the paper prints `late` before `early`, and a table that
    silently re-orders them is a table whose citation points at the wrong line."""
    body = [
        "<!-- page: 2 printed: 2 -->",
        "First",
        "late words",
        "early words",
    ]
    _lines, _emitted, refused = emit(
        [proposal([("early words",), ("late words",)], columns=("First",))], body
    )
    assert refused, "a cell that only appears above the cursor was accepted"
    assert "row 2, column 1" in refused[0].where


def test_the_cursor_carries_within_a_row_so_one_printed_line_holds_three_cells():
    """The OPP's rows are one printed line: `Below R 250,000 1,500 900`. The three cells are three
    runs of it, and the cursor has to move along the line rather than to the next one."""
    lines, emitted, refused = emit([proposal()], BODY)
    assert refused == () and emitted[0].rows == 2
    table = first_table(lines)
    assert [cell.text for cell in table.rows[0].cells] == ["Below R 250,000", "1,500", "900"]


# --- rule 3: the region is claimed ---------------------------------------------------


def test_a_printed_line_inside_the_table_that_no_cell_claims_is_refused():
    body = [
        "<!-- page: 2 printed: 2 -->",
        "Band",
        "Below R 250,000 1,500 900",
        "R 250,001 - R 500,000 2,500 2,000",
        "Above R 5,000,000 8,000 8,000",
    ]
    rows = (("Below R 250,000", "1,500", "900"), ("Above R 5,000,000", "8,000", "8,000"))
    lines, _emitted, refused = emit([proposal(rows, columns=("Band",))], body)
    assert lines == body
    assert refused and "no cell claims" in refused[0].detail
    assert "R 250,001" in refused[0].detail


def test_a_sub_clause_marker_inside_the_region_is_refused():
    """The parser raises on `<!-- sub: … -->` inside a block, so the emitter must never write one —
    a refusal here is the difference between a loud failure and a draft that will not parse."""
    body = ["<!-- page: 2 printed: 2 -->", "a b", "<!-- sub: 2.3 -->", "Below R 250,000 1,500"]
    _lines, _emitted, refused = emit([proposal([("Below R 250,000", "1,500")], columns=("a", "b"))], body)
    assert refused and "annotation" in refused[0].detail


# --- what the block says -------------------------------------------------------------


def test_the_emitted_block_is_the_reviewed_shape_of_the_fee_table():
    """A golden, because every character here was reviewed: columns, one row marker per band, one
    cell per column, the reviewed legend, and the extraction last."""
    lines, _emitted, _refused = emit([proposal(legend="One row per band.")], BODY)
    assert lines == [
        "<!-- page: 2 printed: 2 -->",
        "<!-- table",
        "cols: Annual farm turnover (gross sales) | Initial certification fee (R) | Renewal fee (R)",
        "layout: grid",
        "legend: One row per band.",
        "extraction: layout",
        "-->",
        "<!-- row: Below R 250,000 -->",
        "<!-- cell -->",
        "Below R 250,000",
        "<!-- cell -->",
        "1,500",
        "<!-- cell -->",
        "900",
        "<!-- row: Above R 5,000,000 -->",
        "<!-- cell -->",
        "Above R 5,000,000",
        "<!-- cell -->",
        "8,000",
        "<!-- cell -->",
        "8,000",
        "<!-- /table -->",
        "● Fees are per farm assessment visit.",
    ]


def test_an_empty_cell_is_recorded_empty_and_never_filled():
    """Requirement 5. The paper is silent in that column, and silence is not permission: the parser
    must be able to tell an empty cell from a missing one."""
    body = ["<!-- page: 2 printed: 2 -->", "Key steps Fee", "Step 1", "R500"]
    lines, _emitted, refused = emit(
        [proposal([("Step 1", ""), ("", "R500")], columns=("Key steps", "Fee"))], body
    )
    assert refused == ()
    table = first_table(lines)
    assert [cell.text for cell in table.rows[0].cells] == ["Step 1", ""]
    assert table.rows[1].cells[1].text == "R500"


def test_a_row_is_labelled_from_the_first_printed_line_of_its_first_cell():
    """The label is what a citation says it came from (`row_chunk`'s `heading_path`), so it is the
    paper's own words and never a title somebody invented."""
    body = [
        "<!-- page: 2 printed: 2 -->",
        "Key steps Fee",
        "Step 1",
        "Farmers who are already producing",
        "a surplus.",
        "R500",
    ]
    lines, _emitted, refused = emit(
        [proposal([("Step 1 Farmers who are already producing a surplus.", "R500")], columns=("Key steps", "Fee"))],
        body,
    )
    assert refused == ()
    assert "<!-- row: Step 1 -->" in lines
    assert first_table(lines).rows[0].label == "Step 1"


def test_a_row_that_starts_on_a_new_page_carries_its_page_marker():
    """D72.5: a row is filed under the page it starts on, so a table that crosses a page break has
    to say where — and the parser reads the row's page from the marker in force."""
    body = [
        "<!-- page: 4 printed: 4 -->",
        "Key steps Fee",
        "Step 1",
        "R500",
        "<!-- page: 5 printed: 5 -->",
        "Step 2",
        "R600",
    ]
    lines, _emitted, refused = emit(
        [proposal([("Step 1", "R500"), ("Step 2", "R600")], columns=("Key steps", "Fee"), pdf_pages=(4, 5))],
        body,
    )
    assert refused == ()
    assert "<!-- page: 5 printed: 5 -->" in lines
    assert [row.page for row in first_table(lines).rows] == [4, 5]


def test_the_emitted_block_records_the_extraction_it_was_emitted_from():
    """Requirement 1, at the point where the datum is decided: it is the proposal's, and the block
    carries it so the gate never has to guess."""
    lines, emitted, _refused = emit([proposal(extraction="table")], BODY)
    assert "extraction: table" in lines
    assert first_table(lines).extraction == "table"
    assert emitted[0].columns == FEE_COLUMNS


def test_the_shape_fields_the_reader_draws_are_written_through_from_the_review():
    lines, _emitted, refused = emit(
        [
            proposal(
                [("Step 1", "R500"), ("Step 2", "R600")],
                columns=("Key steps", "Fee"),
                layout="process",
                titles=("Get together", "Agree"),
                fee_labels=("Steps 1-2",),
            )
        ],
        ["<!-- page: 2 printed: 2 -->", "Key steps Fee", "Step 1", "R500", "Step 2", "R600"],
    )
    assert refused == ()
    assert "layout: process" in lines
    assert "title: Get together | Agree" in lines
    assert "fee_label: Steps 1-2" in lines


def test_the_emitted_block_passes_the_harness():
    """R1-R7 on the emitter's own output, judged by the gate's own harness with the page text
    supplied — the loop S3 exists to close, with no PDF anywhere near it."""
    page = (
        "Annual farm turnover (gross sales) Initial certification fee (R) Renewal fee (R)\n"
        "Below R 250,000 1,500 900\n"
        "Above R 5,000,000 8,000 8,000\n"
    )
    lines, _emitted, _refused = emit([proposal(legend="One row per band.")], BODY)
    report = check_document(
        parse_blocks(artefact_of(lines)),
        pages=["page one has no table", page],
        expected_rows=(2,),
        expected_tables=1,
    )
    assert report.ok, report.lines()


def test_no_proposal_leaves_the_body_exactly_as_it_arrived():
    lines, emitted, refused = emit([], BODY)
    assert lines == BODY and emitted == () and refused == ()


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_line_inside_a_cell_is_kept(blank):
    """Rule 4/5 of the corpus format: a cell may hold blank lines (Appendix 2's conditions are five
    paragraphs each), so the emitter must not flatten a cell to one line."""
    body = ["<!-- page: 2 printed: 2 -->", "Key steps Fee", "First paragraph.", blank, "Second paragraph.", "R500"]
    lines, _emitted, refused = emit(
        [proposal([("First paragraph. Second paragraph.", "R500")], columns=("Key steps", "Fee"))], body
    )
    assert refused == ()
    assert first_table(lines).rows[0].cells[0].text == f"First paragraph.\n{blank}\nSecond paragraph."


def test_a_cell_is_not_found_inside_a_longer_number():
    """`1,500` occurs inside `11,5000` as a run — and writing that slice would put a number the page
    does not print into a row, with R3 still green, because the slice *is* a run of the line. The
    word-boundary rule is what stops it."""
    body = ["<!-- page: 2 printed: 2 -->", "Band Fee", "11,5000"]
    lines, _emitted, refused = emit(
        [proposal([("1,500",)], columns=("Band", "Fee"))], body
    )
    assert lines == body
    assert refused and "1,500" in refused[0].detail


# --- the regression S3 promises: the generator reproduces a reviewed block ----------
#
# No PDF and no extractor: the body is built from `knowledge/tests/fixtures/pages/`, exactly as
# `build_corpus.pages_of` builds it (`choose_pages` is the same function), so what this asserts is
# what `python scripts/build_corpus.py --doc opp` writes. The gate runs with
# `PDFTOTEXT_BIN=/usr/bin/true`, which is why the input has to come from the fixtures.

REPO_ROOT = Path(__file__).resolve().parents[2]
OPP_PDF = REPO_ROOT / "pgs_docs" / "Outeniqua pgs principles, policies and procedures 2026.pdf"
OPP_ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "opp.md"


def block_of(lines: list[str]) -> list[str]:
    start = lines.index("<!-- table")
    end = lines.index("<!-- /table -->")
    return lines[start : end + 1]


def test_the_generator_reproduces_the_reviewed_fee_table_from_the_committed_pages():
    """The block that comes out of the fixture-built body is **the block a reviewer signed**,
    character for character — the extraction line included, because the artefact carries it too."""
    body = fixture_body("opp")
    lines, emitted, refused = emit(proposals_for(sha256_of(OPP_PDF)), body)
    assert refused == (), [str(refusal) for refusal in refused]
    assert [table.rows for table in emitted] == [6]
    reviewed = OPP_ARTEFACT.read_text(encoding="utf-8").splitlines()
    assert block_of(lines) == block_of(reviewed)


def test_the_prose_outside_the_emitted_block_is_untouched():
    """The half a block-only assertion would miss: the emitter must splice, not rewrite. Everything
    before the table and everything after it is the same list it was given."""
    body = fixture_body("opp")
    lines, _emitted, _refused = emit(proposals_for(sha256_of(OPP_PDF)), body)
    start = lines.index("<!-- table")
    end = lines.index("<!-- /table -->")
    assert body.index("Annual farm turnover (gross sales) Initial certification fee (R) Renewal fee (R)") == start
    assert lines[:start] == body[:start]
    tail = len(lines) - end - 1
    assert lines[end + 1 :] == body[len(body) - tail :], (
        "the prose after the table was rewritten"
    )


def test_the_regenerated_document_passes_the_gate():
    """The whole loop, offline: emit into the reviewed artefact's own body, parse it, judge it with
    the page fixture — R1 through R7 on the generator's output."""
    from knowledge.tests import page_fixtures

    reviewed = OPP_ARTEFACT.read_text(encoding="utf-8").splitlines()
    report = check_document(
        parse_blocks("\n".join(reviewed) + "\n"),
        pages=page_fixtures.pages("opp", "layout"),
        expected_rows=(6,),
        expected_tables=1,
    )
    assert report.ok, report.lines()


def test_a_document_with_no_proposal_is_drafted_exactly_as_before():
    """SAOSO, the BPP and every future document: no proposal, no block, no warning — the generator's
    behaviour must not change for the documents whose tables nobody has proposed."""
    lines, emitted, refused = emit(proposals_for("0" * 64), fixture_body("opp"))
    assert emitted == () and refused == ()
    assert "<!-- table" not in lines


# --- the reviewed label: a declaration, not a widened matcher --------------------------


ARM_COLUMNS = (
    "Maximum number of animals per ha Class or species",
    "Maximum number of animals per ha equivalent to 170 kg N/ha/year",
)
REVIEWED_COLUMNS = (
    "Class or species",
    "Maximum number of animals per ha equivalent to 170 kg N/ha/year",
)
SIX_A = [
    "<!-- page: 86 printed: 85 -->",
    "             Maximum number of animals per ha          Maximum  number of animals per ha     equivalent",
    "                         Class or species                            to 170 kg N/ha/year",
    "Equines over six months old                                                     2",
    "Calves for fattening                                                            5",
]


def six_a(rows=(("Equines over six months old", "2"), ("Calves for fattening", "5")), **profile):
    return ProposedTable(
        index=0,
        pdf_pages=(86,),
        columns=ARM_COLUMNS,
        rows=tuple(ProposedRow(tuple(row)) for row in rows),
        extraction="table",
        structure="documentai-layout-v1.6-pro",
        processor="id@version",
        profile=ProposedProfile(columns=REVIEWED_COLUMNS, **profile),
    )


def test_a_reviewed_column_label_is_used_instead_of_the_arms():
    """The paper prints Appendix 6a's header once, as two levels of type across four lines with a
    merged cell the arm flattened into one string. A one-line `cols:` cannot be a run of that, so
    the owner's arbitration (two labels, 2026-11-05) is reviewed data and the emitter writes it.

    The arm's own label is not a run of any printed line, which is what made the table refuse.
    """
    lines, emitted, refused = emit([six_a()], SIX_A)
    assert refused == ()
    table = first_table(lines)
    assert table.columns == REVIEWED_COLUMNS
    assert [cell.text for cell in table.rows[0].cells] == ["Equines over six months old", "2"]


def test_a_reviewed_label_never_makes_a_cell_the_reviewers():
    """The declaration replaces the header and nothing else: a cell the page does not print is
    still refused, which is the difference between reviewing a structure and authoring a table."""
    body = ["<!-- page: 86 printed: 85 -->", "Class or species Fee", "Equines over six months old 2"]
    _lines, emitted, refused = emit(
        [six_a(rows=(("Equines over six months old", "2,5"),))], body
    )
    assert emitted == ()
    assert refused[0].where == "row 1, column 2"
    assert "2,5" in refused[0].detail


# --- S5-b: the band, the hyphen, the divider and the declared tail --------------------
#
# Appendix 2 is printed on one line grid: two cells share every printed line, and each cell wraps
# down its own column. Four capabilities were needed to emit it, and each one is a declaration the
# emitter refuses to make up — a `band:` per printed page, a divider written as a `row-divider`,
# and a `tail:` for the one cell whose last words are printed at the top of the next page.

CUT = 16


def column(left: str, right: str = "") -> str:
    """One printed line of a two-column table at `CUT`."""
    return f"{left:<{CUT}}{right}"


TWO_COLUMN = [
    "<!-- page: 77 printed: 76 -->",
    column("Substances", "Conditions for use"),
    "I. PLANT AND ANIMAL ORIGIN",
    column("Biodegradable", "Free of contaminants"),
    column("by-products", "and composted"),
    "South African specific",
    column("Guano"),
]


def two_column(rows, pdf_pages=(77,), **profile) -> ProposedTable:
    return ProposedTable(
        index=0,
        pdf_pages=pdf_pages,
        columns=("Substances", "Conditions for use"),
        rows=tuple(ProposedRow(tuple(row)) for row in rows),
        extraction="table",
        structure="reviewed-locators",
        processor="knowledge/tables.py::APPENDIX_2_ROWS",
        profile=ProposedProfile(
            columns=("Substances", "Conditions for use"),
            dividers=(
                ProposedDivider(0, "I. PLANT AND ANIMAL ORIGIN", "part"),
                ProposedDivider(1, "South African specific", "qualifier"),
            ),
            **profile,
        ),
    )


TWO_COLUMN_ROWS = (
    ("Biodegradable by-products", "Free of contaminants and composted"),
    ("Guano", ""),
)


def test_a_cell_that_wraps_inside_its_column_is_bounded_by_the_declared_band():
    """The capability Appendix 2 needs, and the refusal it replaces.

    Without a `band:` the line is one run, so the left cell's first line reads
    `Biodegradable Free of contaminants` — the neighbour's words in the middle of it — and the
    cell is refused. With the measured boundary declared per printed page, each column is its own
    stream: both cells resolve, and each slice holds only its own column's characters.
    """
    without = two_column(TWO_COLUMN_ROWS)
    _lines, emitted, refused = emit([without], TWO_COLUMN)
    assert emitted == ()
    assert refused[0].where == "row 1, column 1"

    lines, emitted, refused = emit([two_column(TWO_COLUMN_ROWS, band={76: CUT})], TWO_COLUMN)
    assert refused == (), [str(refusal) for refusal in refused]
    table = first_table(lines)
    assert [cell.text for cell in table.rows[0].cells] == [
        "Biodegradable\nby-products",
        "Free of contaminants\nand composted",
    ]
    assert [cell.text for cell in table.rows[1].cells] == ["Guano", ""]


def test_a_band_declared_for_another_page_does_not_cover_this_one():
    """A boundary is a measurement of one printed page. A row on a page the declaration does not
    name is refused rather than resolved against a line nobody cut."""
    _lines, emitted, refused = emit([two_column(TWO_COLUMN_ROWS, band={77: CUT})], TWO_COLUMN)
    assert emitted == ()
    assert refused[0].where == "row 1"
    assert "page 76" in refused[0].detail and "77" in refused[0].detail


def test_the_dividers_are_written_where_the_paper_prints_them():
    """A divider is a whole printed line, not one column of it — `South African specific` is
    centred across the boundary — so it is resolved and claimed on its own, and written as the
    `row-divider` the reader already draws."""
    lines, emitted, refused = emit([two_column(TWO_COLUMN_ROWS, band={76: CUT})], TWO_COLUMN)
    assert refused == ()
    block = block_of(lines)

    def at(annotation):
        return next(i for i, line in enumerate(block) if line.startswith(annotation))

    assert at("<!-- row-divider: I. PLANT AND ANIMAL ORIGIN part -->") < at(
        "<!-- row: Biodegradable"
    )
    assert at("<!-- row-divider: South African specific qualifier -->") < at("<!-- row: Guano -->")
    table = first_table(lines)
    assert [d.text for d in table.rows[1].dividers] == ["South African specific"]


def test_a_divider_the_page_does_not_print_is_refused():
    """It is a claim about the paper, like every other locator: a divider the page does not print
    is refused, not written into the block."""
    body = [line for line in TWO_COLUMN if "South African specific" not in line]
    _lines, emitted, refused = emit([two_column(TWO_COLUMN_ROWS, band={76: CUT})], body)
    assert emitted == ()
    assert refused[0].where == "divider before row 2"
    assert "South African specific" in refused[0].detail


def test_a_word_hyphenated_across_the_line_break_is_resolved_by_both_halves():
    """`cobalt-` at the end of one printed line and `sulphate` at the start of the next is one
    printed word. The harness has had this rule since 2026-11-03; the emitter had it not, which is
    why Appendix 2's trace-elements row could not be emitted (S5 plan §2.9)."""
    body = [
        "<!-- page: 78 printed: 77 -->",
        "Substances Conditions for use",
        "Trace elements, e.g.: boric acid, sodium borate, calcium",
        "borate, borethanolamin, cobalt-acetate, cobalt-",
        "sulphate, copper oxide",
    ]
    lines, emitted, refused = emit(
        [
            proposal(
                [
                    (
                        "Trace elements, e.g.: boric acid, sodium borate, calcium borate, "
                        "borethanolamin, cobalt-acetate, cobalt-sulphate, copper oxide",
                    )
                ],
                columns=("Substances", "Conditions for use"),
                extraction="table",
                pdf_pages=(78,),
            )
        ],
        body,
    )
    assert refused == (), [str(refusal) for refusal in refused]
    # The page's lines, not the review's one-line spelling: the cell is a slice of what was printed.
    assert first_table(lines).rows[0].cells[0].text == (
        "Trace elements, e.g.: boric acid, sodium borate, calcium\n"
        "borate, borethanolamin, cobalt-acetate, cobalt-\n"
        "sulphate, copper oxide"
    )


TAIL_BODY = [
    "<!-- page: 77 printed: 76 -->",
    "Substances Conditions for use",
    "I. PLANT AND ANIMAL ORIGIN",
    column("Seaweed", "As far as obtained by physical processes;"),
    "<!-- page: 78 printed: 77 -->",
    "(iii) fermentation.",
    "<!-- page: 79 printed: 78 -->",
    "South African specific",
    column("Peat", "Excluded."),
]

TAIL_ROWS = (
    ("Seaweed", "As far as obtained by physical processes; (iii) fermentation."),
    ("Peat", "Excluded."),
)


def test_a_cell_whose_last_words_are_on_the_next_page_is_declared_not_inferred():
    """The seaweed row: its condition ends at the top of printed 77. Undeclared, the continuation
    is refused — the emitter may not decide that a cell crosses a page. Declared, the block carries
    a page marker **inside** the cell, so each line records the page it was printed on."""
    undeclared = two_column(
        TAIL_ROWS, pdf_pages=(77, 78, 79), band={76: CUT, 77: CUT, 78: CUT}
    )
    _lines, emitted, refused = emit([undeclared], TAIL_BODY)
    assert emitted == ()
    assert refused[0].where == "row 1, column 2"

    declared = two_column(
        TAIL_ROWS,
        pdf_pages=(77, 78, 79),
        band={76: CUT, 77: CUT, 78: CUT},
        tails=(ProposedTail(0, 2, 77, "(iii) fermentation."),),
    )
    lines, emitted, refused = emit([declared], TAIL_BODY)
    assert refused == (), [str(refusal) for refusal in refused]
    block = block_of(lines)
    cut = block.index("<!-- cell -->", block.index("<!-- cell -->") + 1)
    assert "<!-- page: 78 printed: 77 -->" in block[cut:], "the page break inside the cell is not recorded"
    table = first_table(lines)
    cell = table.rows[0].cells[1]
    assert cell.text == "As far as obtained by physical processes;\n(iii) fermentation."
    # One page per line, which is what lets R3 judge the tail against the page it is printed on.
    assert cell.pages == (76, 77)


def test_a_declared_tail_the_page_does_not_print_there_is_refused():
    """The declaration must be true where it says: `(iii) fermentation.` is the **first** line of
    printed 77, and a page whose first line is something else refuses the claim."""
    body = list(TAIL_BODY)
    body[5] = "something else entirely"
    _lines, emitted, refused = emit(
        [
            two_column(
                TAIL_ROWS,
                pdf_pages=(77, 78, 79),
                band={76: CUT, 77: CUT, 78: CUT},
                tails=(ProposedTail(0, 2, 77, "(iii) fermentation."),),
            )
        ],
        body,
    )
    assert emitted == ()
    assert "is not the first printed line of page 77" in refused[0].detail


def test_the_declared_tail_passes_the_harness_on_its_own_page():
    """R3 read backwards: the tail is checked against printed page 77, not against the row's page.

    This is the loop that made the tail a declaration instead of a hole in the rule — a cell line
    is judged against the page the block says printed it.
    """
    declared = two_column(
        TAIL_ROWS,
        pdf_pages=(77, 78, 79),
        band={76: CUT, 77: CUT, 78: CUT},
        tails=(ProposedTail(0, 2, 77, "(iii) fermentation."),),
    )
    lines, _emitted, refused = emit([declared], TAIL_BODY)
    assert refused == ()
    page_76 = "\n".join(
        [
            column("Substances", "Conditions for use"),
            "I. PLANT AND ANIMAL ORIGIN",
            column("Seaweed", "As far as obtained by physical processes;"),
        ]
    )
    # One string per PDF page, index 0 = page 1: the block's markers say pdf 77/78/79.
    pages = [""] * 79
    pages[76] = page_76
    pages[77] = "(iii) fermentation."
    pages[78] = "\n".join(["South African specific", column("Peat", "Excluded.")])
    report = check_document(
        parse_blocks(artefact_of(lines)),
        pages=pages,
        expected_rows=(2,),
        expected_tables=1,
    )
    assert report.ok, report.lines()


