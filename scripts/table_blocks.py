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
from typing import Sequence

from knowledge.table_proposals import ProposedTable

#: `<!-- page: 12 printed: 11 -->` — the same marker `knowledge.corpus` parses, so a row's page is
#: read from the draft exactly as the parser will read it from the artefact.
PAGE = re.compile(r"^<!--\s*page:\s*(\d+)\s+printed:\s*(\d+|none)\s*-->\s*$")

#: A letter-spaced run is at least this many single letters in a row ('b o v i n e' is 6,
#: '( S A O S O' is 5). The same threshold `scripts/table_reads.py` uses, for the same reason.
_SPACED_RUN = 3


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
class _Cell:
    """Where a resolved cell sits: `(first_line, last_line, start, end)` in the body."""

    first: int
    last: int
    start: int
    end: int


@dataclass(frozen=True)
class _Resolved:
    lines: list[str]
    emitted: Emitted | None
    refusal: Refusal | None
    #: True when the proposal's first cell is nowhere in this text — "not in this section", which is
    #: a different fact from "refused" and must not be reported (or the operator sees twenty messages
    #: about the same table, one per section of the document).
    absent: bool = False


def flat(text: str) -> str:
    """Whitespace-normalised — the comparison every quote check in this repo makes."""
    return " ".join(text.split())


def _flat_map(text: str) -> tuple[str, list[int]]:
    """`(flat_text, offsets)` where `offsets[i]` is the index in `text` of flat character `i`."""
    out: list[str] = []
    offsets: list[int] = []
    for position, character in enumerate(text):
        if character.isspace():
            if out and out[-1] != " ":
                out.append(" ")
                offsets.append(position)
            continue
        out.append(character)
        offsets.append(position)
    while out and out[-1] == " ":
        out.pop()
        offsets.pop()
    return "".join(out), offsets


def has_letter_spacing(text: str) -> bool:
    """Whether the page prints a run of single letters ('t h a n') in this text."""
    run = 0
    for token in text.split(" "):
        if len(token) == 1 and token.isalpha():
            run += 1
            if run >= _SPACED_RUN:
                return True
        else:
            run = 0
    return False


def _run_in_line(line: str, wanted: str, offset: int) -> tuple[int, int] | None:
    """`(start, end)` of `wanted` as a whole-word run of `line` at or after `offset`, or None.

    The word-boundary check is the difference between a cell and a coincidence: `1,500` occurs inside
    `11,5000` as a run, and writing that slice would put a number the paper does not print into a
    row — with R3 still green, because the slice *is* a run of the line.
    """
    text, offsets = _flat_map(line[offset:])
    start = text.find(wanted)
    while start >= 0:
        end = start + len(wanted)
        before = start == 0 or text[start - 1] == " "
        after = end == len(text) or text[end] == " "
        if before and after:
            return offset + offsets[start], offset + offsets[end - 1] + 1
        start = text.find(wanted, start + 1)
    return None


def _resolve(
    target: str,
    lines: Sequence[str],
    cursor: tuple[int, int],
    allowed: set[int] | None = None,
    pages: Sequence[tuple[int, int | None]] | None = None,
) -> tuple[_Cell, tuple[int, int]] | None:
    """The cell's place in the body, and the cursor after it. One pass, forwards only.

    Exact first. Where the page letter-spaces a word, the comparison drops spaces instead — and the
    fallback is only admissible because the page's own characters prove the same sequence is there
    (`scripts/table_reads.py` records the same normalisation for the evaluation arms).

    `allowed` is the set of PDF pages the proposal says the table is on. **It is not a nicety:** the
    landscape prints the same five column labels at the top of every table page, so a page-blind
    search resolves a header to whichever page printed it first and then reports the row as "out of
    printed order" — a true sentence about the wrong page (measured 2026-11-05).
    """
    wanted = flat(target)
    if not wanted:
        return None
    spaced = has_letter_spacing(wanted)
    i, offset = cursor
    while i < len(lines):
        if allowed is not None and pages is not None and pages[i][0] not in allowed:
            i, offset = i + 1, 0
            continue
        line = lines[i]
        while offset < len(line) and line[offset] == " ":
            offset += 1
        found = _run_in_line(line, wanted, offset)
        if found is not None:
            return _Cell(i, i, found[0], found[1]), (i, found[1])
        if spaced or has_letter_spacing(line):
            found = _despaced_run(line, wanted, offset)
            if found is not None:
                return _Cell(i, i, found[0], found[1]), (i, found[1])
        # A cell may begin mid-line and continue; the rest of this line must begin it.
        head, head_offsets = _flat_map(line[offset:])
        head_start = offset + head_offsets[0] if head_offsets else offset
        if head and (wanted == head or wanted.startswith(head + " ")):
            remainder = wanted[len(head):].lstrip()
            for j in range(i + 1, len(lines)):
                if allowed is not None and pages is not None and pages[j][0] not in allowed:
                    break
                piece = flat(lines[j])
                if not piece:
                    continue
                if remainder == piece:
                    end = len(lines[j].rstrip())
                    return _Cell(i, j, head_start, end), (j, end)
                if remainder.startswith(piece + " "):
                    remainder = remainder[len(piece):].lstrip()
                    continue
                if piece.startswith(remainder) and (
                    len(piece) == len(remainder) or piece[len(remainder)] == " "
                ):
                    _text, offsets = _flat_map(lines[j])
                    end = offsets[len(remainder) - 1] + 1
                    return _Cell(i, j, head_start, end), (j, end)
                break
        i, offset = i + 1, 0
    return None


def _despaced_run(line: str, wanted: str, offset: int) -> tuple[int, int] | None:
    """`wanted` found in `line` with every space dropped from both — the letter-spacing fallback.

    The map is built from the **raw** line, one entry per non-space character: the page's own
    spacing is what the slice has to keep, so a flat index cannot stand in for a raw one
    (measured 2026-11-05 — the flat map returned the position of a space and the cell came back as
    `b o v i n e Cattle`, i.e. the arm's boundary with the page's text bolted onto it).
    """
    bare_wanted = wanted.replace(" ", "")
    if not bare_wanted:
        return None
    offsets: list[int] = []
    for position in range(offset, len(line)):
        if not line[position].isspace():
            offsets.append(position)
    bare_text = "".join(line[position] for position in offsets)
    at = bare_text.find(bare_wanted)
    if at < 0:
        return None
    return offsets[at], offsets[at + len(bare_wanted) - 1] + 1


def _slice(lines: Sequence[str], cell: _Cell) -> str:
    """The cell's characters: the body's own lines, from `first` to `last`, trimmed at the edges."""
    if cell.first == cell.last:
        return lines[cell.first][cell.start : cell.end]
    middle = list(lines[cell.first + 1 : cell.last])
    return "\n".join([lines[cell.first][cell.start :]] + middle + [lines[cell.last][: cell.end]])


def _label(text: str) -> str:
    """A row's label: the first printed line of its first non-empty cell (or nothing).

    The paper's own words, never a title somebody invented — `row_chunk` puts this into a citation's
    heading path, so it has to be quotable.
    """
    for line in text.splitlines():
        if line.strip():
            return flat(line)
    return ""


def _page_of(line: str) -> tuple[int, int | None] | None:
    """`(pdf page, printed page)` a marker line declares, or None."""
    marker = PAGE.match(line)
    if not marker:
        return None
    printed = None if marker.group(2) == "none" else int(marker.group(2))
    return int(marker.group(1)), printed


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
    rows: Sequence[tuple[Sequence[str], tuple[int, int | None]]],
    start_page: tuple[int, int | None],
) -> list[str]:
    """The block, in the order the reviewed artefacts already use (so a regeneration is one added
    line and nothing else).

    In:  `table` — the proposal; `columns` — the resolved column labels (the page's characters, not
         the arm's); `rows` — `(cells, (pdf page, printed page))` per row, in printed order, each
         cell already the page's slice.
    Out: the block's lines, ready to splice into the artefact body.
    """
    profile = table.profile
    out = ["<!-- table", "cols: " + " | ".join(columns), f"layout: {profile.layout}"]
    if profile.legend:
        out.append(f"legend: {flat(profile.legend)}")
    if profile.titles:
        out.append("title: " + " | ".join(flat(title) for title in profile.titles))
    if profile.fee_labels:
        out.append("fee_label: " + " | ".join(flat(label) for label in profile.fee_labels))
    if profile.branch is not None:
        out.append(f"branch: {profile.branch}")
    out.append(f"extraction: {table.extraction}")
    out.append("-->")
    # The page in force when the block starts is already in the body (the marker `assemble_body`
    # wrote), so a marker is only written *inside* the block where a row begins a new page.
    current = start_page
    for cells, page in rows:
        if page != current:
            pdf_page, printed = page
            out.append(f"<!-- page: {pdf_page} printed: {'none' if printed is None else printed} -->")
            current = page
        label = _label("\n".join(cells))
        out.append(f"<!-- row: {label} -->" if label else "<!-- row -->")
        for cell in cells:
            out.append("<!-- cell -->")
            for line in cell.split("\n"):
                out.append(line)
    out.append("<!-- /table -->")
    return out


def _appears(target: str, body: Sequence[str]) -> bool:
    """Whether `target` is a run of any of these lines — the "is this table here at all?" question.

    Cheap and deliberately narrow: the emitter is called once per section, and a proposal that
    belongs to §2.3 must not be reported as refused in the twenty-seven sections before it.
    """
    wanted = flat(target)
    return bool(wanted) and any(_run_in_line(line, wanted, 0) is not None for line in body)


def emit_one(
    table: ProposedTable, body: Sequence[str], start_page: tuple[int, int | None] = (0, None)
) -> _Resolved:
    """Resolve one proposal against a body stream: the new lines, or the refusal that stopped it."""
    if not _appears(table.columns[0], body) and not any(
        row.cells and _appears(row.cells[0], body) for row in table.rows
    ):
        return _Resolved(list(body), None, None, absent=True)
    pages = _page_in_force(body, start_page)
    allowed = set(table.pdf_pages)
    cursor: tuple[int, int] = (0, 0)
    claimed: dict[int, bool] = {}

    columns: list[str] = []
    for index, column in enumerate(table.columns):
        found = _resolve(column, body, cursor, allowed, pages)
        if found is None:
            return _Resolved(
                list(body),
                None,
                Refusal(table.index, f"column {index + 1}", f"the printed column {column!r} is not a "
                        "contiguous run of one of the page's printed lines"),
            )
        cell, cursor = found
        columns.append(_slice(body, cell))
        for line_index in range(cell.first, cell.last + 1):
            claimed[line_index] = True

    rows: list[tuple[tuple[str, ...], tuple[int, int | None]]] = []
    for row_index, row in enumerate(table.rows, 1):
        cells: list[str] = []
        page: tuple[int, int | None] | None = None
        for column_index, proposed in enumerate(row.cells, 1):
            if not flat(proposed):
                cells.append("")
                continue
            found = _resolve(proposed, body, cursor, allowed, pages)
            if found is None:
                return _Resolved(
                    list(body),
                    None,
                    Refusal(
                        table.index,
                        f"row {row_index}, column {column_index}",
                        f"{flat(proposed)[:80]!r} is not a contiguous run of any printed line after "
                        "the cell before it (out of printed order, or not on the page)",
                    ),
                )
            cell, cursor = found
            cells.append(_slice(body, cell))
            if page is None:
                page = pages[cell.first]
            for line_index in range(cell.first, cell.last + 1):
                claimed[line_index] = True
        joined = "\n".join(cells)
        if not joined.strip():
            return _Resolved(
                list(body),
                None,
                Refusal(table.index, f"row {row_index}", "every cell is empty, which the format "
                        "refuses: a row with no text is a citation with nothing in it"),
            )
        if page is None or page[0] == 0:
            return _Resolved(
                list(body),
                None,
                Refusal(table.index, f"row {row_index}", "no page marker is in force, so the row "
                        "cannot say which page it starts on (D72.5)"),
            )
        rows.append((tuple(cells), page))

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

    block = block_lines(table, tuple(columns), rows, pages[first])
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
