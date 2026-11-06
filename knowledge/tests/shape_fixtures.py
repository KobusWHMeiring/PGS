"""D80's eight-shape fixture set — the test set an extractor must survive.

`product/design/g12_ingestion_generalisation.html` Part 1 names eight table shapes, every one of
them already in our corpus, and every one of them something today's pipeline either mangles or
special-cases by hand. This module is those eight shapes as **data**: which page prints them, which
lines prove it is that page, what a correct read of that page must contain, and what the engine has
to learn before it can produce one.

**The page text is not copied here.** Each case names a governed document, an extraction mode and a
PDF page, and the text is read from the committed page fixtures
(`knowledge/tests/page_fixtures.py`) — the same bytes the rest of the suite tests, with the
extractor banner and the source PDF's sha256 in `MANIFEST.json`. One copy of the paper, one
provenance chain; a hand-tidied copy of a page would be the exact defect this set exists to catch
(`testing_hazards.md` §3.25 is the same failure in the generator).

**`covered_by` is measured, not inherited.** It names the tests that exist today for that shape, and
the test module asserts three things about them: the named test exists, its input is a reviewed
artefact (a human's fix), and the set of shapes with *no* such test is exactly
`{headerless_values, column_major}` — the two live defects the spec names. When S2's extractor makes
a shape work from the page, the audit fails and the register has to be updated honestly.

Measured 2026-11-03 against this tree: 44 reviewed rows carry column meaning (OPP §2.3 6,
landscape 8, Appendix 2 30), 20 do not (Appendix 6a), Appendix 7 ships 4 interleaved chunks, and the
landscape's longest cell is 1,112 characters.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from knowledge.tests.page_fixtures import pages

#: The eight shapes, in the exploration's order. The test module asserts this tuple is the
#: sequence `SHAPES` defines, so a shape cannot be quietly dropped or renamed into coverage.
SHAPE_NAMES: tuple[str, ...] = (
    "Numeric row, no labels",
    "Header lost entirely",
    "Column-major interleaving",
    "Very long cell",
    "Deliberate empty cell",
    "Row spanning a page break",
    "Two-level qualifier structure",
    "A picture in a cell",
)


@dataclass(frozen=True)
class Cell:
    """One assertion about one cell of the read: `row` and `column` are 0-based.

    Exactly one of `text`, `empty`, `starts`/`ends`/`contains`/`at_least` is normally used.
    `text` is an exact match after whitespace normalisation; `empty` says the paper prints nothing
    there and the read must say so rather than omitting the cell.
    """

    row: int
    column: int
    text: str | None = None
    empty: bool = False
    starts: str = ""
    ends: str = ""
    contains: str = ""
    at_least: int = 0


@dataclass(frozen=True)
class TableRead:
    """What a correct read of a shape's page is. The engine's output, not its input.

    `rows` are the printed rows in printed order, one tuple of cells each; `pages` is the printed
    page each row starts on; `dividers` are `(row index, text, kind)` — the qualifier or part heading
    that governs the row beneath it.
    """

    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    pages: tuple[int, ...] = ()
    dividers: tuple[tuple[int, str, str], ...] = ()


@dataclass(frozen=True)
class ShapeCase:
    """One of the eight: where it is, how to prove it is there, and what reading it must produce."""

    key: str
    shape: str
    doc: str
    doc_key: str
    mode: str
    pdf_pages: tuple[int, ...]
    printed_pages: tuple[int, ...]
    #: `(pdf page, line)` — the line is matched against the page's whitespace-normalised lines.
    anchors: tuple[tuple[int, str], ...]
    columns: tuple[str, ...]
    row_count: int
    cells: tuple[Cell, ...]
    row_pages: tuple[int, ...]
    dividers: tuple[tuple[int, str, str], ...] = ()
    #: What the artefact format can say today. "expressible", "partly" or "no", with the reason.
    ir: str = ""
    #: What the engine must learn. Never empty: a shape with no gap is not a shape we have.
    gap: str = ""
    #: Existing tests for this shape. Their input is a review; that is the point.
    covered_by: tuple[tuple[str, str], ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)


def page_text(case: ShapeCase, pdf_page: int) -> str:
    """The committed text of one page of the case's document, as the extractor produced it."""
    return pages(case.doc_key, case.mode)[pdf_page - 1]


def page_texts(case: ShapeCase) -> str:
    """The case's pages, joined by `\\f` exactly as `extract_pages` returns them."""
    return "\f".join(page_text(case, page) for page in case.pdf_pages)


def normalised_lines(text: str) -> list[str]:
    """One entry per printed line, whitespace-normalised. The provenance check's unit."""
    return [" ".join(line.split()) for line in text.splitlines()]


def flat(text: str) -> str:
    return " ".join((text or "").split())


def page_run(case: ShapeCase, pdf_page: int) -> str:
    """One page's text as one line, for the anchor check: a run, not a whole line.

    `-table` renders row-lines, not cells, so a phrase like a seal's caption is *inside* a printed
    line rather than being one. The anchor asks "are these words, in this order, on this page?",
    which a run answers and a line-equality check would answer only for headings.
    """
    return flat(page_text(case, pdf_page))


SHAPES: tuple[ShapeCase, ...] = (
    ShapeCase(
        key="numeric_row",
        shape=SHAPE_NAMES[0],
        doc="OPP §2.3 assessment fee structure",
        doc_key="opp",
        mode="layout",
        pdf_pages=(2,),
        printed_pages=(2,),
        anchors=(
            (2, "Annual farm turnover (gross sales) Initial certification fee (R) Renewal fee (R)"),
            (2, "Below R 250,000 1,500 900"),
            (2, "Above R 5,000,000 8,000 8,000"),
        ),
        columns=(
            "Annual farm turnover (gross sales)",
            "Initial certification fee (R)",
            "Renewal fee (R)",
        ),
        row_count=6,
        cells=(
            Cell(0, 0, text="Below R 250,000"),
            Cell(0, 1, text="1,500"),
            Cell(0, 2, text="900"),
            Cell(5, 0, text="Above R 5,000,000"),
            Cell(5, 2, text="8,000"),
        ),
        row_pages=(2, 2, 2, 2, 2, 2),
        ir="expressible — a `cols:` header plus one `<!-- row: -->` per band; the labels never enter the cell text",
        gap=(
            "the row shares no word with a question, so its column labels have to travel beside it: "
            "the `embedding_text` rendition that `knowledge/table_chunks.py` already builds for artefact rows"
        ),
        covered_by=(
            (
                "knowledge/tests/test_corpus_tables.py",
                "test_a_row_is_embedded_from_its_column_labels_not_its_cells",
            ),
            ("knowledge/tests/test_ingest.py", "test_a_table_rows_embedding_rendition_is_stored"),
        ),
        notes=(
            "The header is one printed line carrying all three column labels: splitting it into "
            "columns is the extraction, not a text transform.",
            "Measured: six bands, one 1,613-character prose chunk before P4, 32 → 37 chunks for the "
            "document (CORPUS_CANONICAL_FORMAT_PLAN §P4).",
        ),
    ),
    ShapeCase(
        key="headerless_values",
        shape=SHAPE_NAMES[1],
        doc="SAOSO Appendix 6a",
        doc_key="saoso",
        mode="table",
        pdf_pages=(86,),
        printed_pages=(85,),
        anchors=(
            (86, "Maximum number of animals per ha Maximum number of animals per ha equivalent"),
            (86, "Class or species to 170 kg N/ha/year"),
            (86, "Equines over six months old 2"),
            (86, "Laying hens 230"),
            (86, "APPENDIX 6a:"),
        ),
        columns=(
            "Class or species",
            "Maximum number of animals per ha equivalent to 170 kg N/ha/year",
        ),
        row_count=20,
        cells=(
            Cell(0, 0, text="Equines over six months old"),
            Cell(0, 1, text="2"),
            Cell(2, 0, text="Other bovine animals less than one year old"),
            Cell(19, 0, text="Laying hens"),
            Cell(19, 1, text="230"),
        ),
        row_pages=(85,) * 20,
        ir="expressible — `cols:` carries exactly the two labels the page prints once, at the top",
        gap=(
            "associate the printed header with the values beneath it: today all 20 rows ship as "
            "`\"Equines over six months old\\n2\"` with an empty `embedding_text`, so `2` is 'what, per what?'"
        ),
        notes=(
            "The header is printed once and split across four lines, with 'equivalent / to 170 kg "
            "N/ha/year' printed under the second column: the association is the whole shape.",
            "The paper letter-spaces some words ('Other b o v i n e a n i m a l s less t h a n o n e "
            "year old'). The reviewed literal is 'Other bovine animals less than one year old', so a "
            "correct read rejoins intra-word letter spacing; that is the one declared normalisation "
            "cell fidelity needs, and it must be declared rather than applied silently.",
        ),
    ),
    ShapeCase(
        key="column_major",
        shape=SHAPE_NAMES[2],
        doc="SAOSO Appendix 7",
        doc_key="saoso",
        mode="table",
        pdf_pages=(89,),
        printed_pages=(88,),
        anchors=(
            (89, "Oenological practice Authorised products Conditions of use (1) Limits on use and"),
            (89, "1 Aeration or oxygenation Air,"),
            (89, "using gaseous oxygen Gaseous oxygen"),
            (89, "6b Use to encourage yeast Thiamine hydrochloride"),
        ),
        columns=(
            "Oenological practice",
            "Authorised products",
            "Conditions of use (1)",
            "Limits on use and Applications",
        ),
        row_count=7,
        cells=(
            Cell(0, 0, text="Aeration or oxygenation using gaseous oxygen"),
            Cell(0, 1, text="Air, Gaseous oxygen"),
            Cell(0, 2, empty=True),
            Cell(0, 3, empty=True),
            Cell(6, 0, starts="Use to encourage yeast development"),
            Cell(6, 3, contains="No more than 0,6 mg/l"),
        ),
        row_pages=(88,) * 7,
        ir="no — the artefact holds one printed order; a human must de-interleave before it can hold this page",
        gap=(
            "de-interleave a `-layout` page into rows: today the page ships as 4 chunks whose text "
            "reads '7 Use of sulphur dioxide, Sulphur dioxide, / potassium bisulphite or …'"
        ),
        notes=(
            "Rows 1–6b are on printed page 88; the appendix continues on later pages, so the "
            "expectation is page-scoped and does not claim the whole appendix.",
            "`test_ingest_transforms.py::test_…` proves a *reviewed* row set replaces an interleaved "
            "chunk. Appendix 7 has no reviewed rows, which is why nothing catches it.",
        ),
    ),
    ShapeCase(
        key="long_cell",
        shape=SHAPE_NAMES[3],
        doc="Landscape — ESTABLISHING A PGS GROUP, Step 3",
        doc_key="landscape",
        mode="table",
        pdf_pages=(5,),
        printed_pages=(5,),
        anchors=(
            (5, "Key steps Resource documents, Use of seals and logos Seals and logos Fee"),
            (5, "These two seals were developed by PGS SA"),
            (5, "Step 3"),
        ),
        columns=(
            "Key steps",
            "Resource documents, guidelines and requirements",
            "Use of seals and logos",
            "Seals and logos",
            "Fee",
        ),
        row_count=1,
        cells=(
            # The row label is inside the cell. The paper prints a bold `Step 3` above the prose and
            # the reviewed landscape block keeps it, so the cell *starts* with the label and the
            # prose is asserted separately. Corrected 2026-11-05 from the owner's review of this key
            # (D85): the first version asserted the cell started at "The group conducts…", which
            # demanded a read that dropped the label our own artefact keeps.
            Cell(
                0,
                0,
                starts="Step 3",
                contains="The group conducts farm visits and",
            ),
            Cell(
                0,
                2,
                starts="These two seals were developed by PGS SA",
                ends="the use of these seals.",
                at_least=1000,
            ),
            Cell(0, 3, empty=True),
            Cell(0, 4, starts="A newly established PGS group"),
        ),
        row_pages=(5,),
        ir="expressible — a cell keeps its blank lines (rules 4 and 5); D70.1 renders it as a definition list",
        gap=(
            "a cell is a paragraph: keep it whole at 1,112 characters, and never let it become a "
            "column the reader has to scroll sideways (D76 measured the reading measure at ~85 characters)"
        ),
        covered_by=(
            (
                "knowledge/tests/test_landscape_table_block.py",
                "test_every_cell_line_is_a_verbatim_run_of_its_own_printed_table",
            ),
            (
                "knowledge/tests/test_landscape_table_block.py",
                "test_the_picture_column_holds_a_label_and_never_prose",
            ),
        ),
        notes=(
            "Measured 1,112 characters on this tree; the exploration says 1,107 — the same cell, "
            "with the paper's line breaks counted differently.",
            "The first column's row label is inside the cell: `Step 3` is printed bold above the "
            "prose, and the reviewed landscape block keeps it (owner's review, 2026-11-05).",
        ),
    ),
    ShapeCase(
        key="empty_cells",
        shape=SHAPE_NAMES[4],
        doc="Landscape — ESTABLISHING A PGS GROUP, Steps 1–2",
        doc_key="landscape",
        mode="table",
        pdf_pages=(4,),
        printed_pages=(4,),
        anchors=(
            (4, "Key steps Resource documents, Use of seals and logos Seals and logos Fee"),
            (4, "Step 1"),
            (4, "Proud member of"),
            (4, "Local PGS group determines the"),
            (4, "Annual membership fee (paid"),
        ),
        columns=(
            "Key steps",
            "Resource documents, guidelines and requirements",
            "Use of seals and logos",
            "Seals and logos",
            "Fee",
        ),
        row_count=2,
        cells=(
            Cell(0, 0, starts="Step 1"),
            Cell(0, 2, empty=True),
            Cell(0, 3, empty=True),
            Cell(0, 4, contains="R500"),
            Cell(1, 3, text="Proud member of"),
            Cell(1, 4, empty=True),
        ),
        row_pages=(4, 4),
        ir="expressible — a `<!-- cell -->` with nothing beneath it is recorded empty; the parser proves it",
        gap=(
            "distinguish an empty cell from an absent one, and never fill from the cell above: the "
            "paper is silent in two places on this row, and a filler destroys the finding"
        ),
        covered_by=(
            (
                "knowledge/tests/test_corpus_tables.py",
                "test_an_empty_cell_is_recorded_as_empty_never_as_missing",
            ),
            (
                "knowledge/tests/test_corpus_tables.py",
                "test_a_row_with_an_empty_cell_does_not_label_the_silence",
            ),
        ),
        notes=(
            "Measured: 12 empty cells across the landscape's three tables.",
            "Step 2's fee cell is empty because Step 1's fee box is merged across the two rows "
            "(shape 6's neighbour): the merged cell is one cell and is filed under Step 1.",
        ),
    ),
    ShapeCase(
        key="page_break_row",
        shape=SHAPE_NAMES[5],
        doc="Landscape — the Step 1–3 row set across PDF 4 and 5",
        doc_key="landscape",
        mode="table",
        pdf_pages=(4, 5),
        printed_pages=(4, 5),
        anchors=(
            (4, "Step 1"),
            (4, "Step 2"),
            (5, "Step 3"),
            (5, "Recommended annual fee for"),
            (5, "R350 [to be divided between"),
            (5, "the use of these seals."),
        ),
        columns=(
            "Key steps",
            "Resource documents, guidelines and requirements",
            "Use of seals and logos",
            "Seals and logos",
            "Fee",
        ),
        row_count=3,
        cells=(
            Cell(0, 0, starts="Step 1"),
            Cell(1, 0, starts="Step 2"),
            Cell(2, 0, starts="Step 3"),
            Cell(2, 4, contains="R350"),
        ),
        row_pages=(4, 4, 5),
        ir="partly — a row has one page (D72.5). The format can file a continued row under the page it starts on; it cannot say 'continued'",
        gap=(
            "one row, two pages: Step 1 and Step 2 are on PDF 4 and Step 3 is on PDF 5, and a naive "
            "read produces two half-rows or a row on the wrong page"
        ),
        covered_by=(
            (
                "knowledge/tests/test_landscape_table_block.py",
                "test_a_row_belongs_to_the_page_it_starts_on",
            ),
            ("knowledge/tests/test_tables.py", "test_the_seaweed_condition_crosses_the_page_break"),
        ),
        notes=(
            "The page restarts the table on PDF 5: the header line is printed again, and the "
            "extractor must not open a second table.",
            "Appendix 2's 'Seaweed and seaweed products' condition crosses printed pages 76–77 the "
            "same way, with the page furniture inside the column's x-range.",
        ),
    ),
    ShapeCase(
        key="qualifier",
        shape=SHAPE_NAMES[6],
        doc="SAOSO Appendix 2 — part and qualifier dividers",
        doc_key="saoso",
        mode="table",
        pdf_pages=(77,),
        printed_pages=(76,),
        anchors=(
            (77, "I. PLANT AND ANIMAL ORIGIN"),
            (77, "South African specific"),
            (77, "Farmyard manure, slurry and urine Manure applications should not be the primary"),
            (77, "APPENDIX 2"),
        ),
        columns=(
            "SUBSTANCES DESCRIPTION, COMPOSITIONAL REQUIREMENTS",
            "CONDITIONS FOR USE",
        ),
        row_count=11,
        cells=(
            Cell(0, 0, text="Farmyard manure, slurry and urine"),
            Cell(0, 1, starts="Shall not constitute the main source of nitrogen"),
            Cell(2, 0, text="Guano"),
            Cell(2, 1, empty=True),
            Cell(4, 1, empty=True),
        ),
        row_pages=(76,) * 11,
        dividers=(
            (0, "I. PLANT AND ANIMAL ORIGIN", "part"),
            (1, "South African specific", "qualifier"),
            (3, "South African specific", "qualifier"),
        ),
        ir="expressible but authored — `<!-- row-divider: … -->` holds it, and a human writes that line",
        gap=(
            "derive a divider from the page: 'South African specific' is printed between rows and "
            "'I. PLANT AND ANIMAL ORIGIN' is a part heading — neither is a row and neither is a heading"
        ),
        covered_by=(
            (
                "knowledge/tests/test_corpus_tables.py",
                "test_a_row_divider_is_recorded_against_the_row_beneath_it",
            ),
            (
                "core/tests/test_document_reader_curated.py",
                "test_the_dividers_render_above_the_rows_they_name",
            ),
        ),
        notes=(
            "The printed header is upper case and wraps ('SUBSTANCES DESCRIPTION, COMPOSITIONAL' / "
            "'REQUIREMENTS'); the artefact's reviewed `cols:` label is the same words in sentence case, "
            "which is a spelling difference and not a second reading.",
            "Measured: 11 rows on printed page 76, dividers before rows 0, 1 and 3 (and 14, 15, 26, "
            "28 on the following pages).",
            "The qualifier repeats a substance's name: rows 0 and 1 are both 'Farmyard manure, "
            "slurry and urine' and differ only by the qualifier above them.",
        ),
    ),
    ShapeCase(
        key="artwork_cell",
        shape=SHAPE_NAMES[7],
        doc="Landscape — PGS SEALS AND THEIR USE",
        doc_key="landscape",
        mode="table",
        pdf_pages=(6,),
        printed_pages=(6,),
        anchors=(
            (6, "PGS SEALS AND THEIR USE"),
            (6, "PGS Organic In-Conversion"),
            (6, "As above"),
            (6, "Labelling regulations state that use of the word"),
        ),
        columns=(
            "Key steps",
            "Resource documents, guidelines and requirements",
            "Use of seals and logos",
            "Seals and logos",
            "Fee",
        ),
        row_count=2,
        cells=(
            Cell(0, 0, starts="PGS Organic In-Conversion"),
            Cell(0, 2, starts="PGS Organic In-Conversion"),
            Cell(0, 3, empty=True),
            Cell(0, 4, text="As above"),
            Cell(1, 0, starts="PGS Organic"),
            Cell(1, 3, empty=True),
        ),
        row_pages=(6, 6),
        ir="no — the format is text. Artwork is recorded as a legend note plus the printed label, never as a cell value",
        gap=(
            "detect non-text in a cell and record the printed label beside it, saying the artwork is "
            "not stored: today a human decides that (D72.1), and a picture can be neither a chunk nor a quote"
        ),
        covered_by=(
            (
                "knowledge/tests/test_landscape_table_block.py",
                "test_the_seal_cell_carries_the_printed_label_not_the_picture",
            ),
        ),
        notes=(
            "Both rows' Fee cells read 'As above', and the referent is on PDF 4–5: the cell stays "
            "literal and the legend names the branch (§12h).",
            "The 'Seals and logos' column is empty on both rows because the picture is not stored; "
            "the printed label lives one column to the left.",
        ),
    ),
)

BY_KEY = {case.key: case for case in SHAPES}

#: The shapes with no test whose input is the shape itself. The audit in
#: `test_ingestion_shapes.py` asserts this is exactly the set with no `covered_by`, so that
#: coverage cannot be claimed and quietly inherited.
UNCOVERED: frozenset[str] = frozenset({"headerless_values", "column_major"})


def cell_at(read: TableRead, row: int, column: int) -> str | None:
    """The cell's text, or None when the read has no such cell (which is a defect, not an empty)."""
    if row >= len(read.rows) or column >= len(read.rows[row]):
        return None
    return read.rows[row][column]


def mismatches(case: ShapeCase, read: TableRead) -> list[str]:
    """Every way `read` disagrees with the case, as readable lines. An empty list is a pass.

    Returns rather than asserts so a test can prove the checker fails: feeding it a transposed row
    or a filled-in silence must produce a named failure (`testing_hazards.md` §1.5 — a guard nobody
    has watched go red is a guard nobody has tested).
    """
    found: list[str] = []
    if read.columns != case.columns:
        found.append(f"{case.key}: columns {read.columns!r} != {case.columns!r}")
    if len(read.rows) != case.row_count:
        found.append(f"{case.key}: {len(read.rows)} rows, the page prints {case.row_count}")
    if case.row_pages and read.pages != case.row_pages:
        found.append(f"{case.key}: row pages {read.pages!r} != {case.row_pages!r}")
    if read.dividers != case.dividers:
        found.append(f"{case.key}: dividers {read.dividers!r} != {case.dividers!r}")
    for wanted in case.cells:
        value = cell_at(read, wanted.row, wanted.column)
        where = f"{case.key}: row {wanted.row} cell {wanted.column}"
        if value is None:
            found.append(f"{where} is missing from the read")
            continue
        text = flat(value)
        if wanted.empty and text:
            found.append(f"{where} must be empty, the read says {text[:60]!r}")
        elif wanted.text is not None and text != flat(wanted.text):
            found.append(f"{where} is {text[:60]!r}, expected {wanted.text!r}")
        if wanted.starts and not text.startswith(flat(wanted.starts)):
            found.append(f"{where} does not start {wanted.starts!r}: {text[:60]!r}")
        if wanted.ends and not text.endswith(flat(wanted.ends)):
            found.append(f"{where} does not end {wanted.ends!r}: {text[-60:]!r}")
        if wanted.contains and flat(wanted.contains) not in text:
            found.append(f"{where} does not hold {wanted.contains!r}")
        if wanted.at_least and len(text) < wanted.at_least:
            found.append(f"{where} is {len(text)} characters, expected at least {wanted.at_least}")
    return found
