#!/usr/bin/env python
"""Emit a `<!-- table … -->` block from a proposed structure and the page's own characters (S3).

`INGESTION_ENGINE_PRD.md` §3.14 splits the work and gives the halves to different tools: **structure**
from an extractor's layout read (`knowledge/proposals/`), **characters** from the page's text layer,
**the verdict** from the harness. This module is the middle: it takes the first, slices the artefact's
own body text for the second, and refuses — by name — whatever it cannot do honestly.

Three rules, and the third is the one that costs a review if it is missing:

1. **A cell's characters are the page's.** The proposed cell is a *locator*: it is resolved against
   the body's printed lines (exact first, then with whitespace set aside **only where the page letter-
   spaces a word**, as Appendix 6a does), and what gets written is the slice — line breaks and all.
   So a cell can never hold a character the page did not print, which is requirement 3 and rule 9 at
   once. A cell whose words are not there is a refusal, never a copy of the arm's text.
2. **Cells resolve in one forward-only cursor.** A cell cannot stitch a line from above the table into
   a row, and a table whose cells are printed out of order (a merged box the arm split, a page whose
   columns were de-interleaved in the wrong order) is refused rather than silently re-ordered — the
   reviewer decides that, with the paper in front of them.
3. **Everything inside the region is claimed.** The region runs from the first line a cell claimed to
   the last. A printed line inside it that no cell claims is a line the corpus loses, and `--force`
   would then delete text while every character-level guard stayed green (`testing_hazards.md` §3.25).
   Blank lines and page markers are the only things allowed to go unclaimed.

**The cell primitives live in `scripts/table_cells.py`** since S5-b: `_resolve` and the functions it
needs (the run-in-a-line rule, the band, the despace fallback, the slice) were the bulk of this file,
and this module kept the block writer, the region rule and the refusals. What the split may not do is
separate two answers to "what counts as the page's words", so the band and the slice read the declared
`band:` through one function, in one file.

**What this module deliberately cannot do.** No PDF, no fixture, no credential, no extractor: the body
lines are the input, exactly as `build_corpus.py` holds them. It does not write reviewed fields — the
legend, the shape, the titles, the fee labels and the fork come from
`knowledge/proposals/<doc>.reviewed.json`, because no extractor produces them and a generator that
invented one would be authoring a claim. And it does not judge: `knowledge/table_harness.py` does that,
on the artefact, afterwards.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from knowledge.table_proposals import ProposedTable
from scripts.table_cells import (
    PAGE,
    _Cell,
    _band_at,
    _cell_lines,
    _flat_map,
    _page_of,
    _resolve,
    _run_in_line,
    _slice,
    flat,
    has_letter_spacing,
)

#: `<!-- page: 12 printed: 11 -->` — the same marker `knowledge.corpus` parses, so a row's page is
#: read from the draft exactly as the parser will read it from the artefact.

__all__ = ["Emitted", "Refusal", "block_lines", "emit", "emit_one", "flat", "has_letter_spacing"]


@dataclass(frozen=True)
class Emitted:
    """One table the emitter wrote. `rows` is what the harness will compare with the declaration."""

    index: int
    columns: tuple[str, ...]
    rows: int


@dataclass(frozen=True)
class Refusal:
    """One table the emitter would not write, named so an operator can act on it."""

    index: int
    where: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover - formatting only
        return f"proposal {self.index + 1}, {self.where}: {self.detail}"


@dataclass(frozen=True)
class _Resolved:
    lines: list[str]
    emitted: Emitted | None
    refusal: Refusal | None
    #: True when the proposal's first cell is nowhere in this text — "not in this section", which is
    #: a different fact from "refused" and must not be reported (or the operator sees twenty messages
    #: about the same table, one per section of the document).
    absent: bool = False


def _label(text: str) -> str:
    """A row's label: the first printed line of its first non-empty cell (or nothing).

    The paper's own words, never a title somebody invented — `row_chunk` puts this into a citation's
    heading path, so it has to be quotable.
    """
    for line in text.splitlines():
        if line.strip():
            return flat(line)
    return ""


def _page_in_force(
    body: Sequence[str], start: tuple[int, int | None] = (0, None)
) -> list[tuple[int, int | None]]:
    """For each body line, the page a page marker has put in force.

    `start` is the page already in force when the body begins: a section's own page marker is emitted
    *before* its heading (`assemble_body`'s `after=`), so the body of §2.3 carries no marker at all
    and a row there would otherwise have no page to cite.
    """
    pages: list[tuple[int, int | None]] = []
    current = start
    for line in body:
        declared = _page_of(line)
        if declared is not None:
            current = declared
        pages.append(current)
    return pages


def block_lines(
    table: ProposedTable,
    columns: tuple[str, ...],
    rows: Sequence[tuple[Sequence[tuple[tuple[str, tuple[int, int | None]], ...]], tuple[int, int | None]]],
    start_page: tuple[int, int | None],
    labels: Sequence[str] | None = None,
) -> list[str]:
    """The block, in the order the reviewed artefacts already use (so a regeneration is one added
    line and nothing else).

    In:  `table` — the proposal; `columns` — the resolved column labels (the page's characters, not
         the arm's); `rows` — `(cells, (pdf page, printed page))` per row, in printed order, each
         cell a list of `(line, the page it was printed on)`; `labels` — a row's label where the
         paper prints one in a gutter of its own (Appendix 7's row number), else None and the
         label is the first printed line of the row's first cell.
    Out: the block's lines, ready to splice into the artefact body.

    **The page marker follows the characters, not the row.** A row that starts a new page carries a
    marker before its label; a cell whose last line was printed on the next page carries a marker
    inside itself, at the line the page turns. That is the one place a block records a
    cross-page continuation, and the parser reads it: each cell line then knows the page it came
    from, which is what R3 checks it against.
    """
    profile = table.profile
    out = ["<!-- table", "cols: " + " | ".join(columns), f"layout: {profile.layout}"]
    if profile.legend:
        out.append(f"legend: {flat(profile.legend)}")
    if profile.silence:
        out.append(f"silence: {profile.silence}")
    if profile.titles:
        out.append("title: " + " | ".join(flat(title) for title in profile.titles))
    if profile.fee_labels:
        out.append("fee_label: " + " | ".join(flat(label) for label in profile.fee_labels))
    if profile.branch is not None:
        out.append(f"branch: {profile.branch}")
    out.append(f"extraction: {table.extraction}")
    out.append("-->")
    # The page in force when the block starts is already in the body (the marker `assemble_body`
    # wrote), so a marker is only written *inside* the block where the printed page changes.
    current = start_page

    def mark(page: tuple[int, int | None]) -> str:
        pdf_page, printed = page
        return f"<!-- page: {pdf_page} printed: {'none' if printed is None else printed} -->"

    dividers = table.divider_cells()
    for index, (cells, page) in enumerate(rows):
        if page != current:
            out.append(mark(page))
            current = page
        for divider in dividers.get(index, ()):
            out.append(f"<!-- row-divider: {divider.text} {divider.kind} -->")
        label = (
            flat(labels[index])
            if labels is not None and index < len(labels)
            else _label("\n".join(text for cell in cells for text, _page in cell))
        )
        out.append(f"<!-- row: {label} -->" if label else "<!-- row -->")
        for cell in cells:
            out.append("<!-- cell -->")
            for text, line_page in cell:
                if line_page != current:
                    out.append(mark(line_page))
                    current = line_page
                out.append(text)
    out.append("<!-- /table -->")
    return out


def _appears(target: str, body: Sequence[str]) -> bool:
    """Whether `target` is a run of any of these lines — the "is this table here at all?" question.

    Cheap and deliberately narrow: the emitter is called once per section, and a proposal that
    belongs to §2.3 must not be reported as refused in the twenty-seven sections before it.
    """
    wanted = flat(target)
    return bool(wanted) and any(_run_in_line(line, wanted, 0) is not None for line in body)


def _tail_line(
    body: Sequence[str],
    pages: Sequence[tuple[int, int | None]],
    tail,
    cursor: tuple[int, int],
) -> tuple[int, int] | None:
    """`(line index, end offset)` of a declared tail, or None. **It must be the page's first line.**

    The declaration says the cell's last words are printed at the top of the next page
    (`INGESTION_ENGINE_S5_PLAN.md` §4). So the words must be a run at the start of the first
    non-blank line printed on the declared page — not merely somewhere on it. That is the rule the
    owner's read of printed 77 established: `(iii) fermentation.` is that page's first line, and the
    review's spelling had come from printed 79, where the phrase is printed without the bracket.
    """
    wanted = flat(tail.text)
    if not wanted:
        return None
    for index in range(cursor[0] + 1, len(body)):
        if pages[index][1] != tail.page:
            continue
        if _page_of(body[index]) is not None or not body[index].strip():
            continue
        text = flat(body[index])
        if not text.startswith(wanted):
            return None
        _flat, offsets = _flat_map(body[index])
        return index, offsets[len(wanted) - 1] + 1
    return None


def emit_one(
    table: ProposedTable, body: Sequence[str], start_page: tuple[int, int | None] = (0, None)
) -> _Resolved:
    """Resolve one proposal against a body stream: the new lines, or the refusal that stopped it."""
    reviewed = table.profile.columns
    first_column = reviewed[0] if reviewed else table.columns[0]
    if not _appears(first_column, body) and not any(
        row.cells and _appears(row.cells[0], body) for row in table.rows
    ):
        return _Resolved(list(body), None, None, absent=True)
    pages = _page_in_force(body, start_page)
    allowed = set(table.pdf_pages)
    bands = table.profile.band
    # **A table is attempted in the section that opens on one of its pages.** The emitter is called
    # once per section, and a table's row-openers are ordinary phrases: Appendix 2's
    # `Farmyard manure, slurry and urine` is also printed in S8.1, so the "is this table here at
    # all?" question answered yes in a section twenty pages early, the divider it could not find
    # was refused, and the proposal was marked attempted before the appendix was reached — measured
    # 2026-11-05 (S5-b). A section whose heading page the table does not print cannot hold it.
    if start_page[0] and start_page[0] not in allowed:
        return _Resolved(list(body), None, None, absent=True)
    cursor: tuple[int, int] = (0, 0)
    claimed: dict[int, bool] = {}

    def claim(cell: _Cell) -> None:
        for line_index in range(cell.first, cell.last + 1):
            claimed[line_index] = True

    def side_of(column_index: int) -> int | None:
        """Which of the declared columns this arm cell is read from; None when there is no band."""
        if not bands:
            return None
        return column_index

    # **A reviewed label is not resolved against the page, and that is the whole point of the
    # declaration.** The paper prints a table's header once, as two levels of type across several
    # lines (`Maximum number of animals per ha` over `Class or species`, with the second column's
    # label split beneath it). A one-line `cols:` field cannot be a slice of that, so the labels are
    # reviewed data — the same status `TABLE_SECTIONS["Appendix 2"].columns` already has. The
    # printed header lines then stay in the section as prose, which is where a citation of "what
    # the numbers are per hectare" belongs; nothing is deleted to make room for the labels.
    columns: list[str] = []
    gutter = table.profile.gutter
    if reviewed:
        columns = [flat(column) for column in reviewed]
    else:
        for index, column in enumerate(table.columns):
            if index < gutter:
                # A gutter is the printed row number, not a column the reader draws.
                continue
            found = _resolve(column, body, cursor, allowed, pages)
            if found is None:
                return _Resolved(
                    list(body),
                    None,
                    Refusal(table.index, f"column {index + 1}", f"the printed column {column!r} is "
                            "not a contiguous run of one of the page's printed lines"),
                )
            cell, cursor = found
            columns.append(_slice(body, cell, pages, bands))
            claim(cell)

    dividers = table.divider_cells()
    # **One forward cursor per column, and that is what a declared band means.** A row whose two
    # cells both wrap occupies the *same* printed lines (measured on Appendix 2, row 4 of printed
    # 76: the substance runs down lines 64–68 in the left column while its condition runs down the
    # same lines on the right). A single cursor across the row can only resolve the second cell
    # after the first one's last line, which is below the condition's first word — so it refuses a
    # row the paper prints correctly. The band already split one line into two streams; the cursor
    # follows the stream, and no column may resume above the earliest point the row may start.
    cursors: list[tuple[int, int]] = [(0, 0) for _ in (table.rows[0].cells if table.rows else ())]
    rows: list[tuple[tuple[tuple[tuple[str, tuple[int, int | None]], ...], ...], tuple[int, int | None]]] = []
    #: One label per row where the paper prints it in a gutter (`gutter: 1`), else nothing.
    row_labels: list[str] = []
    for row_index, row in enumerate(table.rows):
        floor = min(cursors) if cursors else (0, 0)
        # **A declared band is a measurement of every page the table prints on.** A row that lands
        # on a page the declaration does not name cannot be cut, so it is refused as *under-
        # declared* — before any cell is resolved, which is what makes the message name the page
        # instead of blaming a cell for the missing boundary.
        if bands and pages[floor[0]][1] not in bands:
            declared = ", ".join(str(page) for page in sorted(bands))
            return _Resolved(
                list(body),
                None,
                Refusal(
                    table.index,
                    f"row {row_index + 1}",
                    f"this row is printed on page {pages[floor[0]][1]} and the proposal declares a "
                    f"column boundary for {declared} only. Without one, the row's cells would be "
                    "resolved against both columns and claim the neighbour's words",
                ),
            )
        # A divider is printed *above* the row it qualifies, on a line of its own — the whole line,
        # never one side of the band: `South African specific` is centred across the boundary.
        for divider in dividers.get(row_index, ()):
            found = _resolve(divider.text, body, floor, allowed, pages, bands=None, side=None)
            if found is None:
                return _Resolved(
                    list(body),
                    None,
                    Refusal(
                        table.index,
                        f"divider before row {row_index + 1}",
                        f"{flat(divider.text)[:80]!r} is not a contiguous run of any printed "
                        "line before the row it qualifies",
                    ),
                )
            cell, floor = found
            claim(cell)
            cursors = [max(cursor, floor) for cursor in cursors]
        cells: list[tuple[tuple[str, tuple[int, int | None]], ...]] = []
        page: tuple[int, int | None] | None = None
        row_label: str | None = None
        for column_index, proposed in enumerate(row.cells):
            # **The printed row number is a cell, not a column.** `gutter: 1` says the arm's first
            # column is where the paper prints the row's number: it is resolved and claimed like
            # every other cell — so the label cannot be a number somebody typed — and written as
            # the row's label (`row_chunk`'s `heading_path`), never as a column the reader draws.
            if column_index < gutter:
                start = cursors[column_index] if column_index < len(cursors) else floor
                found = _resolve(
                    flat(proposed), body, max(start, floor), allowed, pages, bands,
                    side_of(column_index),
                )
                if found is None:
                    return _Resolved(
                        list(body),
                        None,
                        Refusal(
                            table.index,
                            f"row {row_index + 1}, column {column_index + 1}",
                            f"the printed row number {flat(proposed)[:80]!r} is not a run of any "
                            "printed line after the row before it (out of printed order, or not "
                            "on the page)",
                        ),
                    )
                cell, cursor = found
                claim(cell)
                cursors[column_index] = cursor
                if page is None:
                    page = pages[cell.first]
                row_label = _label(
                    "\n".join(text for text, _p in _cell_lines(body, cell, pages, bands))
                )
                continue
            if not flat(proposed):
                cells.append(())
                continue
            # **A reviewed locator is how a cell the arm transcribed is found.** The arm may write
            # `\\(70^{\\circ}C\\)` where the page prints `70oC` (Appendix 7, S5-c); the review may
            # say the page's spelling so the cell can be resolved — and the block still holds the
            # page's characters, because the slice is the page's, not the locator's.
            wanted = flat(table.locator_for(row_index, column_index + 1) or proposed)
            tail = table.tail_for(row_index, column_index + 1)
            if tail is not None:
                wanted_tail = flat(tail.text)
                if not wanted.endswith(wanted_tail):
                    return _Resolved(
                        list(body),
                        None,
                        Refusal(
                            table.index,
                            f"row {row_index + 1}, column {column_index + 1}",
                            f"the declared tail {wanted_tail!r} is not the end of this cell, so "
                            "the declaration and the row disagree about what crosses the page",
                        ),
                    )
                wanted = wanted[: len(wanted) - len(wanted_tail)].rstrip()
            start = cursors[column_index] if column_index < len(cursors) else floor
            found = _resolve(
                wanted,
                body,
                max(start, floor),
                allowed,
                pages,
                bands,
                side_of(column_index),
            )
            if found is None:
                return _Resolved(
                    list(body),
                    None,
                    Refusal(
                        table.index,
                        f"row {row_index + 1}, column {column_index + 1}",
                        f"{wanted[:80]!r} is not a contiguous run of any printed line after "
                        "the cell before it (out of printed order, or not on the page)",
                    ),
                )
            cell, cursor = found
            claim(cell)
            lines = list(_cell_lines(body, cell, pages, bands))
            if page is None:
                page = pages[cell.first]
            if tail is not None:
                found_tail = _tail_line(body, pages, tail, cursor)
                if found_tail is None:
                    return _Resolved(
                        list(body),
                        None,
                        Refusal(
                            table.index,
                            f"row {row_index + 1}, column {column_index + 1}",
                            f"the declared tail {flat(tail.text)[:80]!r} is not the first printed "
                            f"line of page {tail.page}, so it is not where the declaration says "
                            "it is",
                        ),
                    )
                index, end = found_tail
                lines.append((body[index].rstrip(), pages[index]))
                claimed[index] = True
                cursor = (index, end)
            cursors[column_index] = cursor
            cells.append(tuple(lines))
        joined = "\n".join(text for cell in cells for text, _page in cell)
        if not joined.strip():
            return _Resolved(
                list(body),
                None,
                Refusal(table.index, f"row {row_index + 1}", "every cell is empty, which the format "
                        "refuses: a row with no text is a citation with nothing in it"),
            )
        if page is None or page[0] == 0:
            return _Resolved(
                list(body),
                None,
                Refusal(table.index, f"row {row_index + 1}", "no page marker is in force, so the row "
                        "cannot say which page it starts on (D72.5)"),
            )
        if bands and page[1] not in bands:
            declared = ", ".join(str(page_number) for page_number in sorted(bands))
            return _Resolved(
                list(body),
                None,
                Refusal(
                    table.index,
                    f"row {row_index + 1}",
                    f"this row is printed on page {page[1]} and the proposal declares a column "
                    f"boundary for {declared} only. Without one, the row's cells would be resolved "
                    "against both columns and claim the neighbour's words",
                ),
            )
        rows.append((tuple(cells), page))
        row_labels.append(row_label or "")

    first = min(claimed)
    last = max(claimed)
    for line_index in range(first, last + 1):
        if line_index in claimed:
            continue
        line = body[line_index]
        if not line.strip() or _page_of(line) is not None:
            continue
        if line.lstrip().startswith("<!--"):
            return _Resolved(
                list(body),
                None,
                Refusal(table.index, "table", f"the annotation {line.strip()[:60]!r} sits inside the "
                        "table's region; the parser refuses one there, and moving it would move a "
                        "citation"),
            )
        return _Resolved(
            list(body),
            None,
            Refusal(table.index, "table", f"no cell claims the printed line {flat(line)[:80]!r}, so "
                    "writing this block would delete it from the corpus"),
        )

    block = block_lines(
        table,
        tuple(columns),
        rows,
        pages[first],
        labels=tuple(row_labels) if gutter else None,
    )
    return _Resolved(
        list(body[:first]) + block + list(body[last + 1 :]),
        Emitted(index=table.index, columns=tuple(columns), rows=len(rows)),
        None,
    )


def emit(
    proposals: Sequence[ProposedTable],
    body: Sequence[str],
    start_page: tuple[int, int | None] = (0, None),
) -> tuple[list[str], tuple[Emitted, ...], tuple[Refusal, ...]]:
    """Every proposal, applied to one body stream.

    In:  `proposals` — the document's proposals (`knowledge.table_proposals.proposals_for`); `body` —
         the drafting body lines, page markers and all (what `build_corpus.build()` assembled for a
         section, or the whole document flattened — the emitter does not care which); `start_page` —
         the `(pdf page, printed page)` already in force when the body begins, which a section's body
         does not repeat.
    Out: the body with every block that resolved spliced in place; the tables written; the refusals.
         A refused proposal leaves the body exactly as it arrived, so `--force` keeps the page's
         prose and S1's `table_loss_refusal` still sees the reviewed block it would have dropped.
    Fails: never. A refusal is data, and `build_corpus.py` prints it.
    """
    lines = list(body)
    emitted: list[Emitted] = []
    refused: list[Refusal] = []
    for table in proposals:
        result = emit_one(table, lines, start_page)
        lines = result.lines
        if result.refusal is not None:
            refused.append(result.refusal)
        elif result.emitted is not None:
            emitted.append(result.emitted)
    return lines, tuple(emitted), tuple(refused)
