"""D80 S4 — the verification harness: requirements 2-7 of `INGESTION_ENGINE_PRD.md` as code.

The PRD's §3.1 finding was that **six of the eight shapes have a test and none of the eight has a
test whose input is the shape**: every existing assertion reads a human's fix. This module is the
instrument that reads the *table* instead, so a document that has not been hand-reviewed can still
be refused before it reaches the corpus.

What it checks, one function per requirement, all named in `REQUIREMENTS`:

* **R1 the extraction is recorded** — a block says which rendering of the page its cells were
  transcribed from, or it is judged against a guess. The landscape passes against `-table` and
  fails ten ways against `-layout`; the mode is a **declaration** like the row count, and a block
  that does not make it is named rather than defaulted (`check_tables.py` used to default it).
* **R2 header association** — a row's `embedding_text` names each printed column that has a value.
  Without this the row is retrievable only by the words inside its cells, so a numeric row (the
  landscape's fee bands) is reachable by nobody (`CHAT_ANSWER_COVERAGE_PRD` G10).
* **R3 cell fidelity** — every line a cell carries is a contiguous run of one *printed line* on the
  row's own page, and a cell's lines appear in printed order. This is the landscape rule,
  generalised: the failure it catches is Appendix 2's, where a condition printed beside the wrong
  substance produced a grounded answer that was wrong.
* **R4 row count** — the rows equal the rows the page prints. A page cannot say how many rows it has
  in machine-readable form, so the count is a **declaration** the caller makes (Module `shape_fixtures`
  makes it in `ShapeCase.row_count`; `scripts/check_tables.py` makes it with `--rows`). A count that
  was not declared is reported as a violation, never as a pass: an unasserted property that reads
  green is the hazard this repo keeps writing down.
* **R5 empty is data** — a cell is a slice of the section text or it is a lie; an empty cell is
  recorded as empty, never dropped, never filled from the cell above, and a row may not simply omit
  a column's cell.
* **R6 spans stay whole** — a divider is claimed exactly once (the paper prints it once, between
  two rows, qualifying the one beneath), and the table's shape fields agree with its rows.
* **R7 non-text is never quoted** — a picture, a private-use glyph or a stray annotation marker in
  a cell is not text a quote can be verified against.

**What this module deliberately does not do.** It does not extract, does not read a PDF, and does
not decide whether the *artifact* matches the paper byte for byte — that is the reviewed artefact's
job. It takes the parsed tables plus the extracted page text, so the gate needs no extractor
(requirement 10) and a shape fixture can supply committed pages.

Pages enter as `pages` — one string per PDF page, index 0 being page 1 — and the printed-page to
PDF-page mapping is read from the artefact's own `<!-- page: N printed: M -->` markers
(`printed_page_index`). Nothing here guesses an offset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from knowledge.sections import ParsedSection, ParsedTable
from knowledge.table_chunks import row_chunk

#: Requirement ids, quoted so a failure message names the rule and not the line number.
REQUIREMENTS: dict[str, str] = {
    "R1": "the block records the extraction its cells came from",
    "R2": "a row's rendition names each printed column that has a value",
    "R3": "cell fidelity: each cell line is a contiguous run of one printed line, in printed order",
    "R4": "row count: the rows equal the rows the page prints",
    "R5": "empty is data: a cell is its slice, and emptiness is recorded, never dropped or filled",
    "R6": "spans stay whole: a divider is claimed once, and the shape fields agree with the rows",
    "R7": "non-text is never quoted: no picture, private-use glyph or marker in a cell",
}

#: Text that is not text. `U+FFFD` is what a lost glyph becomes (session `0f`); the private-use
#: range is where a symbol font hides its icons (`saoso_text_glyphs_and_boundaries.md`); `<!--`
#: is an artefact annotation that reached a cell, which means a boundary was lost.
NOT_TEXT = re.compile(r"<!--|\ufffd|[\ue000-\uf8ff]")


def flat(text: str) -> str:
    """Whitespace-normalised, the way every quote check in this repo compares text."""
    return " ".join(text.split())


@dataclass(frozen=True)
class Violation:
    """One way a document failed a requirement, named so a reviewer can act on it."""

    requirement: str
    where: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover - formatting only
        return f"{self.requirement} {self.where}: {self.detail}"


@dataclass(frozen=True)
class Report:
    """What the harness saw and what it found. `ok` is about the violations, nothing else."""

    violations: tuple[Violation, ...]
    tables: int
    rows: int

    @property
    def ok(self) -> bool:
        return not self.violations

    def lines(self) -> list[str]:
        return [str(violation) for violation in self.violations]


def printed_page_index(document) -> dict[int, int]:
    """`printed page -> 1-based PDF page`, from the artefact's own page markers.

    A marker is `<!-- page: 12 printed: 11 -->`: the first number is the PDF page the block sits
    on, the second the number the document prints in its footer (D42). Reading both is why no
    caller needs to know an offset, and why a document that starts printing at 7 needs no
    per-document constant.
    """
    mapping: dict[int, int] = {}
    for block in getattr(document, "blocks", ()):
        if block.printed is None or block.page is None:
            continue
        mapping.setdefault(block.printed, block.page)
    return mapping


def check_table(
    section: ParsedSection,
    table: ParsedTable,
    *,
    where: str,
    pages: Sequence[str] | None = None,
    printed_to_pdf: Mapping[int, int] | None = None,
    expected_row_count: int | None = None,
) -> list[Violation]:
    """Every violation of requirements 2-7 in one parsed table.

    In:  `section` — the section the table belongs to (its text is what a cell must be a slice
         of); `table` — the parsed table; `where` — a human-readable locator for the messages;
         `pages` — the document's extracted pages, index 0 = page 1, or None when the caller has
         no page text (then R3 is reported as unasserted, not skipped); `printed_to_pdf` — the
         mapping `printed_page_index` builds; `expected_row_count` — the declared count, or None
         when nobody declared one.
    Out: violations, in requirement order. Empty means the table passed every check that could be
         made, and `check_document` is where "could be made" is turned into a count.
    """
    found: list[Violation] = []
    printed_to_pdf = printed_to_pdf or {}

    if not table.extraction:
        found.append(
            Violation(
                "R1",
                where,
                "the block does not record the extraction its cells came from, so every cell was "
                "checked against a pass nobody declared — add `extraction: layout|raw|table` to "
                "the block's header (S3), or pass `--pages-mode` to judge a draft",
            )
        )

    if not table.columns:
        found.append(
            Violation(
                "R2",
                where,
                "the table prints no column labels, so no cell can carry column meaning — this is "
                "the Appendix 6a shape, and the format cannot express it",
            )
        )

    for index, row in enumerate(table.rows):
        found.extend(
            _check_row(
                section,
                table,
                row,
                where=f"{where} row {index + 1}",
                pages=pages,
                printed_to_pdf=printed_to_pdf,
            )
        )

    found.extend(_check_spans(table, where))
    found.extend(_check_non_text(table, where))

    if expected_row_count is None:
        found.append(
            Violation(
                "R4",
                where,
                "no row count was declared, so the rows were never compared with the page",
            )
        )
    elif expected_row_count != len(table.rows):
        found.append(
            Violation(
                "R4",
                where,
                f"{len(table.rows)} rows, the declaration says the page prints {expected_row_count}",
            )
        )
    return found


def _check_row(
    section: ParsedSection,
    table: ParsedTable,
    row,
    *,
    where: str,
    pages: Sequence[str] | None,
    printed_to_pdf: Mapping[int, int],
) -> list[Violation]:
    found: list[Violation] = []
    chunk = row_chunk(section, row, table.columns)

    # R2 — the rendition, not the text: `text` stays what the paper prints.
    for index, cell in enumerate(row.cells):
        value = flat(cell.text)
        if not value:
            continue
        label = table.columns[index] if index < len(table.columns) else ""
        if not label:
            found.append(
                Violation(
                    "R2",
                    where,
                    f"cell {index + 1} carries text and the table prints no column for it",
                )
            )
        elif f"{label}: {value}" not in chunk.embedding_text:
            found.append(
                Violation(
                    "R2",
                    where,
                    f"cell {index + 1} is not rendered under its printed column {label!r}",
                )
            )

    # R5 — a cell is its slice; emptiness is recorded.
    if len(row.cells) < len(table.columns):
        found.append(
            Violation(
                "R5",
                where,
                f"{len(row.cells)} cells for {len(table.columns)} columns: a missing cell is not "
                "an empty cell, and one of them would be quoted as silence",
            )
        )
    for index, cell in enumerate(row.cells):
        if section.text[cell.start : cell.end] != cell.text:
            found.append(
                Violation(
                    "R5",
                    where,
                    f"cell {index + 1} is not a slice of its section text — a fabricated cell "
                    "cannot be quoted and cannot be checked",
                )
            )
        elif cell.text.strip() and cell.start == cell.end:
            found.append(Violation("R5", where, f"cell {index + 1} has text and no slice"))
        elif not cell.text.strip() and cell.start != cell.end:
            found.append(
                Violation("R5", where, f"cell {index + 1} is empty and carries a slice")
            )

    found.extend(_check_cells_on_the_page(row, where=where, pages=pages, printed_to_pdf=printed_to_pdf))
    return found


def _check_cells_on_the_page(
    row,
    *,
    where: str,
    pages: Sequence[str] | None,
    printed_to_pdf: Mapping[int, int],
) -> list[Violation]:
    """R3 — every cell line is a contiguous run of one printed line, and the lines run in order."""
    if pages is None:
        return [
            Violation(
                "R3",
                where,
                "cell fidelity was not asserted: no page text was supplied, so nothing compared "
                "the cells with the paper",
            )
        ]
    if row.page is None:
        return [
            Violation(
                "R3",
                where,
                "the row declares no printed page, so its cells cannot be checked against any page",
            )
        ]
    pdf_page = printed_to_pdf.get(row.page)
    if pdf_page is None:
        return [
            Violation(
                "R3",
                where,
                f"printed page {row.page} has no page marker in the artefact, so the page it "
                "should be checked against is unknown",
            )
        ]
    if not 1 <= pdf_page <= len(pages):
        return [
            Violation(
                "R3",
                where,
                f"the artefact says printed page {row.page} is PDF page {pdf_page}, and the "
                f"document has {len(pages)} pages",
            )
        ]
    printed = [flat(line) for line in pages[pdf_page - 1].splitlines()]
    printed = [line for line in printed if line]

    found: list[Violation] = []
    for index, cell in enumerate(row.cells):
        # One cursor per **cell**: a cell's own lines run top to bottom, and that is the order a
        # quote reads in. It is not shared across the row, because a merged box (the landscape's
        # fee spans two steps) prints its text beside the row above the one it is filed under —
        # measured 2026-11-03: a shared cursor reported 171 violations on three tables and every
        # one of them was the spanning cell's position rather than a lost word.
        cursor = 0
        for line in cell.text.splitlines():
            value = flat(line)
            if not value:
                continue
            position = _locate(value, printed, cursor)
            if position is None:
                found.append(
                    Violation(
                        "R3",
                        where,
                        f"cell {index + 1} carries {value[:60]!r}, which is not a contiguous run "
                        f"of a printed line on page {row.page}, in the order the cell prints them",
                    )
                )
            else:
                cursor = position
    return found


def _locate(value: str, printed: Sequence[str], cursor: int) -> int | None:
    """The index of the printed line `value` runs inside at or after `cursor`, or None.

    The rule is requirement 3's: a cell's line is a **contiguous run inside one printed line**.
    One case needs a second reading, and it is the paper's, not a convenience: a word hyphenated
    across the break prints as `self-` at the end of one line and `assessment` at the start of
    the next, so a cell that keeps the word whole carries a line no single printed line holds.

    Measured 2026-11-03 on the landscape's reviewed tables: 3 of 8 rows do it, all of them wraps.
    So the strict match runs first, and the fallback splits the cell's line at its own hyphens and
    requires *both* halves to be printed lines in order — which is narrow on purpose. Joining
    every line instead would weaken R3 to "the words appear somewhere on the page", which is the
    thing it exists not to be.
    """
    for offset in range(cursor, len(printed)):
        if value in printed[offset]:
            return offset
    for split in range(1, len(value) - 1):
        if value[split] != "-" or not value[split + 1].isalpha():
            continue
        head = next(
            (offset for offset in range(cursor, len(printed)) if value[: split + 1] in printed[offset]),
            None,
        )
        if head is None:
            continue
        tail = next(
            (
                offset
                for offset in range(head + 1, len(printed))
                if value[split + 1 :] in printed[offset]
            ),
            None,
        )
        if tail is not None:
            return tail
    return None


def _check_spans(table: ParsedTable, where: str) -> list[Violation]:
    """R6 — a divider qualifies one row, and the shape fields agree with the rows."""
    found: list[Violation] = []
    claimed: dict[str, int] = {}
    for index, row in enumerate(table.rows):
        for divider in row.dividers:
            claimed.setdefault(divider.text, index + 1)
            if not flat(divider.text):
                found.append(Violation("R6", where, f"row {index + 1} claims a blank divider"))
            elif claimed[divider.text] != index + 1:
                found.append(
                    Violation(
                        "R6",
                        where,
                        f"the divider {divider.text[:40]!r} is claimed by rows "
                        f"{claimed[divider.text]} and {index + 1}; the paper prints it once",
                    )
                )
    if table.titles and len(table.titles) != len(table.rows):
        found.append(
            Violation(
                "R6",
                where,
                f"{len(table.titles)} titles for {len(table.rows)} rows",
            )
        )
    if table.branch is not None and not 0 <= table.branch < len(table.rows):
        found.append(
            Violation("R6", where, f"the branch names row {table.branch}, which does not exist")
        )
    if any(not flat(label) for label in table.fee_labels):
        found.append(Violation("R6", where, "a fee box label is blank"))
    return found


def _check_non_text(table: ParsedTable, where: str) -> list[Violation]:
    """R7 — a picture is named, never quoted: no glyph that is not text reaches a cell."""
    found: list[Violation] = []
    if NOT_TEXT.search(table.legend):
        found.append(Violation("R7", where, "the legend carries a glyph that is not text"))
    for index, row in enumerate(table.rows):
        for cell_index, cell in enumerate(row.cells):
            match = NOT_TEXT.search(cell.text)
            if match:
                found.append(
                    Violation(
                        "R7",
                        where,
                        f"row {index + 1} cell {cell_index + 1} carries {match.group(0)!r}, "
                        "which is not text a quote can be verified against",
                    )
                )
    return found


def recorded_extraction(document) -> tuple[tuple[str, ...], tuple[Violation, ...]]:
    """The extraction modes a document's blocks declare, and their disagreement, if any.

    In:  `document` — a `CorpusDocument` (`knowledge.corpus.parse_blocks`).
    Out: the modes in first-seen order, and one `R1` violation when there is more than one.
    Fails: never. A block with no mode contributes nothing here — `check_table` names it, because
         this function is about the *document's* answer and that is per block.

    Why a document-level fact needs its own function: `check_tables.py` has one `pages` sequence per
    document (a fixture set is per document and per mode), so two modes in one artefact is a gate
    about to read one paper and report on another. Averaging them, or letting the last block win,
    is the silent default this repository keeps writing down.
    """
    modes: list[str] = []
    for section in document.sections:
        for table in section.tables:
            if table.extraction and table.extraction not in modes:
                modes.append(table.extraction)
    if len(modes) < 2:
        return tuple(modes), ()
    return (
        tuple(modes),
        (
            Violation(
                "R1",
                "document",
                "the blocks record more than one extraction "
                f"({', '.join(modes)}). Each mode is a different rendering of the page and a "
                "different fixture set, so one run cannot check both — split the check by mode, "
                "or make the transcription agree.",
            ),
        ),
    )


def check_document(
    document,
    *,
    pages: Sequence[str] | None = None,
    expected_rows: Sequence[int] | None = None,
    expected_tables: int | None = None,
) -> Report:
    """Every table in a parsed document, checked, with the declarations it needs.

    In:  `document` — a `CorpusDocument` (`knowledge.corpus.parse_blocks`); `pages` — the
         document's extracted pages, index 0 = page 1; `expected_rows` — the row count for each
         table, **in document order** (a count is a declaration, see R4); `expected_tables` — how
         many tables the document has, so a document whose blocks went missing fails instead of
         passing with nothing to check (`build_corpus.py --force` refusing to drop a block is the
         other half of that guard).
    Out: a `Report`. `tables` and `rows` are what was checked — a document with no tables returns
         zero of each, and the assertions above are what make that a failure rather than a pass.
    """
    printed_to_pdf = printed_page_index(document)
    violations: list[Violation] = []
    tables = 0
    rows = 0
    for section in document.sections:
        for index, table in enumerate(section.tables):
            where = f"{section.heading_path or section.section_ref} table {index + 1}"
            declared = (
                expected_rows[tables]
                if expected_rows is not None and tables < len(expected_rows)
                else None
            )
            violations.extend(
                check_table(
                    section,
                    table,
                    where=where,
                    pages=pages,
                    printed_to_pdf=printed_to_pdf,
                    expected_row_count=declared,
                )
            )
            tables += 1
            rows += len(table.rows)

    if expected_tables is not None and expected_tables != tables:
        violations.append(
            Violation(
                "R4",
                "document",
                f"{tables} tables and the declaration names {expected_tables}: a block that went "
                "missing takes its rows and its checks with it",
            )
        )
    if expected_rows is not None and len(expected_rows) != tables:
        violations.append(
            Violation(
                "R4",
                "document",
                f"{tables} tables and {len(expected_rows)} declared row counts",
            )
        )
    return Report(tuple(violations), tables, rows)
