"""Appendix tables in the artefact — the grid the reader draws, and the measured band.

**One storage, and it is the artefact.** Every reviewed table is a `<!-- table … -->` block in the
reviewed corpus (`knowledge.corpus`, D73), parsed into `ParsedSection.tables` and chunked by
`chunks_for_parsed_section`; the reader draws it from the same parse. There is no second copy in
Python: Appendix 6a left this module in S5-a and Appendix 2 in S5-b, and what remains here is what
the *renderer* needs — the grid, its alignment, and the printed divider's shape.

**Why the band is here and not only in the proposal.** `TABLE_BANDS` is the measurement (2026-10-21)
of where Appendix 2's second column starts on each printed page. The declaration that actually slices
the page lives in `knowledge/proposals/saoso.reviewed.json` (`band:`), because a number a reviewer can
read beside the table is data; this constant is the *evidence* for it, and
`test_the_declared_band_is_the_measured_one` fails if the two ever disagree.

**What this module deliberately does not do.** It does not read a page, hold a cell, or know a
document. A cell's characters are the page's, sliced by `scripts/table_blocks.py` and judged by
`knowledge/table_harness.py`; a renderer that could reconstruct a table would be a third answer to
what the paper prints.
"""

from __future__ import annotations

from dataclasses import dataclass


#: Where the condition column starts in `pdftotext -table` output, per printed page — the
#: measurement the reviewed `band:` declaration must equal.
#: Measured 2026-10-21 (the `CONDITIONS FOR USE` header sits at column 60 on printed
#: 76; the continuation page's cells start at 64). Used to *verify* the curated cells
#: against the page — ingestion does not split anything at runtime, because the rows
#: are already the reviewed data. A reprint that moves the column changes this number
#: and `test_tables.py` fails. Printed 85 is Appendix 6a's single value column, measured
#: 2026-10-28 in `-table` output (the numbers start at column 88).
TABLE_BANDS: dict[int, int] = {76: 60, 77: 64, 78: 64, 85: 88}


@dataclass(frozen=True)
class TableDivider:
    """A printed heading *inside* the table: a part, or a centred qualifier.

    `before_row` is an index into `TABLE_ROWS[section_ref]`, because the divider is attached to the
    row it precedes — that is where the paper prints it, and a citation that lands mid-table must
    see the divider that governs the row it landed on, never the one above it.
    """

    before_row: int
    text: str
    kind: str  # "part" | "qualifier"




def _squash(text: str) -> str:
    return " ".join((text or "").split())




@dataclass(frozen=True)
class ArtefactGrid:
    """A reviewed artefact table, in the shape the reader draws.

    The two-column `TableStructure` above is Appendix 2's shape: a substance cell and a condition
    cell, rendered as a heading over a paragraph. The landscape's tables have five columns, so the
    reader needs the printed column labels and every cell — not a label per row. The data is the
    artefact's own (`ParsedTable`), never a reconstruction: the rows are the chunks the reader has.

    D77's four fields travel unaltered. They are the reviewer's, and the renderer reads them
    rather than deriving a fork from a missing `Step` prefix or naming a fee box from the
    columns around it.
    """

    columns: tuple[str, ...]
    legend: str
    #: One entry per row; each is that row's cells in printed column order.
    rows: tuple[tuple[str, ...], ...]
    #: The printed label of each row (`Step 1`, or the route's own wording where the paper prints
    #: no number), in row order. The card's heading falls back to this when no title is reviewed.
    labels: tuple[str, ...] = ()
    #: Which shape the reader draws: `grid` (a spreadsheet) or `process` (cards).
    layout: str = "grid"
    #: The row index where the remaining rows become an alternative path, or None.
    branch: int | None = None
    #: One reviewer title per row, in row order, or empty.
    titles: tuple[str, ...] = ()
    #: One heading per fee box, in printed order, or empty.
    fee_labels: tuple[str, ...] = ()
    #: One tuple of printed headings per row, in row order — `((text, kind), …)`, where `kind` is
    #: `part` or `qualifier`. Empty for every table whose paper prints no heading inside it.
    dividers: tuple[tuple[tuple[str, str], ...], ...] = ()
    #: What the reader prints where a cell is empty, or empty when silence needs no words.
    silence: str = ""

    @property
    def row_texts(self) -> tuple[str, ...]:
        """Each row as the chunk text the ingest stores (`ParsedTableRow.text`)."""
        return tuple("\n".join(cells) for cells in self.rows)

    def title_for(self, index: int) -> str:
        """The reviewer title for a row, or `""` — the template then prints the row label."""
        return self.titles[index] if 0 <= index < len(self.titles) else ""


@dataclass(frozen=True)
class GridAlignment:
    """Where a reviewed grid lands in the passages the reader is about to render.

    Two facts, not one: `positions` is the row-to-passage mapping, and `split` is the **passage**
    at which the remaining rows become an alternative path. The renderer stacks those in one
    column, so it needs the passage, not the row index — `grid.branch` says which row it is.
    """

    positions: tuple[int, ...]
    #: The passage index the alternative path starts at, or None for a linear table.
    split: int | None = None


def artefact_grid_for(section) -> ArtefactGrid | None:
    """In: a `ParsedSection` from a reviewed artefact. Out: its table as a grid, or None.

    A section with more than one table returns the first: every landscape section has one, and a
    section with two would need the template to place them, which is a different design question.
    """
    if not section.tables:
        return None
    table = section.tables[0]
    return ArtefactGrid(
        columns=table.columns,
        legend=table.legend,
        layout=table.layout,
        branch=table.branch,
        titles=table.titles,
        fee_labels=table.fee_labels,
        labels=tuple(row.label_text for row in table.rows),
        rows=tuple(tuple(cell.text for cell in row.cells) for row in table.rows),
        dividers=tuple(
            tuple((divider.text, divider.kind) for divider in row.dividers)
            for row in table.rows
        ),
        silence=table.silence,
    )


def align_artefact_grid(grid: ArtefactGrid, texts: tuple[str, ...]) -> GridAlignment | None:
    """In: a grid and the passage texts about to be rendered. Out: where its rows land, or None.

    In:  `texts` — one entry per passage in the branch, in printed order. Prose before, between or
         after the rows is allowed and ignored.
    Out: the index of each row's passage, in row order, plus the passage the alternative path
         starts at when the table declares a `branch:`. **None** unless every row matches exactly
         (whitespace-normalised) and the matches keep their order.
    Fails: never. A corpus that disagrees with the artefact renders the plain page it renders today:
        a mislabelled row is worse than no grid.
    """
    positions: list[int] = []
    cursor = 0
    for wanted in grid.row_texts:
        needle = _squash(wanted)
        found = next(
            (index for index in range(cursor, len(texts)) if _squash(texts[index]) == needle),
            None,
        )
        if found is None:
            return None
        positions.append(found)
        cursor = found + 1
    split = None if grid.branch is None else positions[grid.branch]
    return GridAlignment(positions=tuple(positions), split=split)



__all__ = [
    "TABLE_BANDS",
    "ArtefactGrid",
    "GridAlignment",
    "TableDivider",
    "align_artefact_grid",
    "artefact_grid_for",
    "chunks_for_parsed_section",
    "row_chunk",
]
