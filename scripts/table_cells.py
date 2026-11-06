"""Cell resolution: where a proposed cell sits in the page's own printed lines.

Split out of `scripts/table_blocks.py` (`build_principles.md` §II, and the S5-b slice pushed that file
past 30 KB). These are the primitives the emitter's rules are made of — a run found in a line, a line
cut into its two columns, a cell's characters and the page each of its lines was printed on — and they
are pure: text in, a `(line, offset)` or a `_Cell` out. The block writer, the region rule and the
refusals stay in `table_blocks.py`.

Kept together because they share one contract: **a cell's characters are the page's**. `_resolve`
finds the locator and `_cell_lines` slices the characters, and both read the declared `band:` through
`_column_view`, so "what counts as the page's words" cannot change in one half only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from knowledge.corpus_tables import has_letter_spacing

#: `<!-- page: 12 printed: 11 -->` — the same marker `knowledge.corpus` parses, so a row's page is
#: read from the draft exactly as the parser will read it from the artefact.
PAGE = re.compile(r"^<!--\s*page:\s*(\d+)\s+printed:\s*(\d+|none)\s*-->\s*$")



@dataclass(frozen=True)
class _Cell:
    """Where a resolved cell sits: `(first_line, last_line, start, end)` in the body.

    `side` is the declared column the cell was read from: `None` when the line is the whole line
    (a divider, or a table with no `band:`), `0` for the left of the declared boundary and `1` for
    the right. The band is not stored here because a cell that continues onto the next page is
    printed on *that* page's boundary, and the two numbers differ (Appendix 2: 60 on printed 76, 64
    on 77 from then on).
    """

    first: int
    last: int
    start: int
    end: int
    side: int | None = None


def _column_view(line: str, band: int | None, side: int | None) -> tuple[str, int]:
    """`(the characters of this line that belong to one column, where they start in the raw line)`.

    A two-column table printed on one line grid puts both cells on the same printed line, so a cell
    is only a run of the page once the line is cut at the boundary the review declared. Without a
    band the whole line is the run, which is every table that prints one cell per line.
    """
    if band is None or side is None:
        return line, 0
    if side == 0:
        return line[:band], 0
    return line[band:], band


def _band_at(
    bands: Mapping[int, int] | None,
    pages: Sequence[tuple[int, int | None]] | None,
    index: int,
) -> int | None:
    """The boundary declared for the printed page this body line is printed on, or None."""
    if not bands or pages is None:
        return None
    printed = pages[index][1]
    return None if printed is None else bands.get(printed)



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
    bands: Mapping[int, int] | None = None,
    side: int | None = None,
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
        band = _band_at(bands, pages, i)
        text, base = _column_view(lines[i], band, side)
        start_at = max(offset - base, 0)
        while start_at < len(text) and text[start_at] == " ":
            start_at += 1
        found = _run_in_line(text, wanted, start_at)
        if found is not None:
            return _Cell(i, i, found[0] + base, found[1] + base, side), (i, found[1] + base)
        if spaced or has_letter_spacing(text):
            found = _despaced_run(text, wanted, start_at)
            if found is not None:
                return _Cell(i, i, found[0] + base, found[1] + base, side), (i, found[1] + base)
        # A cell may begin mid-line and continue; the rest of this line must begin it.
        head, head_offsets = _flat_map(text[start_at:])
        head_start = base + start_at + head_offsets[0] if head_offsets else offset
        if head and (wanted == head or wanted.startswith(head + " ")):
            remainder = wanted[len(head):].lstrip()
            for j in range(i + 1, len(lines)):
                if allowed is not None and pages is not None and pages[j][0] not in allowed:
                    break
                piece_text, piece_base = _column_view(
                    lines[j], _band_at(bands, pages, j), side
                )
                piece = flat(piece_text)
                if not piece:
                    continue
                if remainder == piece:
                    end = piece_base + len(piece_text.rstrip())
                    return _Cell(i, j, head_start, end, side), (j, end)
                if remainder.startswith(piece + " "):
                    remainder = remainder[len(piece):].lstrip()
                    continue
                # **A word hyphenated across the break.** The page ends one line `cobalt-` and
                # begins the next `sulphate`, so the reviewed cell's flat text holds
                # `cobalt-sulphate` and no printed line holds the whole word. The harness has had
                # this rule since 2026-11-03 (`table_harness._locate` splits at the hyphen and
                # requires both halves as printed lines in order); the emitter refused it until
                # S5-b, which is why Appendix 2's trace-elements row could not be emitted. Narrow
                # on purpose: the printed piece must *end* with the hyphen and the remainder must
                # continue with a word, so a piece that merely shares a prefix cannot match.
                if (
                    piece.endswith("-")
                    and len(remainder) > len(piece)
                    and remainder.startswith(piece)
                    and remainder[len(piece)].isalpha()
                ):
                    remainder = remainder[len(piece):].lstrip()
                    continue
                if piece.startswith(remainder) and (
                    len(piece) == len(remainder) or piece[len(remainder)] == " "
                ):
                    _text, offsets = _flat_map(piece_text)
                    end = piece_base + offsets[len(remainder) - 1] + 1
                    return _Cell(i, j, head_start, end, side), (j, end)
                break
        i, offset = i + 1, 0
    return None


def _page_of(line: str) -> tuple[int, int | None] | None:
    """`(pdf page, printed page)` a marker line declares, or None."""
    marker = PAGE.match(line)
    if not marker:
        return None
    printed = None if marker.group(2) == "none" else int(marker.group(2))
    return int(marker.group(1)), printed


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


def _cell_lines(
    lines: Sequence[str],
    cell: _Cell,
    pages: Sequence[tuple[int, int | None]] | None = None,
    bands: Mapping[int, int] | None = None,
) -> tuple[tuple[str, tuple[int, int | None]], ...]:
    """The cell's characters and the page each line was printed on.

    In:  `lines` — the body; `cell` — where it resolved; `pages`/`bands` — the page in force at
         each line and the declared column boundary per printed page.
    Out: one `(line, page)` per line the cell carries, in printed order, cut at the declared band.
         Blank lines are kept as they are printed: SAOSO's appendix cells are several paragraphs
         each, and a blank line is the chunker's paragraph boundary.
    Side effects: none.
    Fails: never.

    A page marker inside a cell's range is **not** copied into the cell: it is the annotation that
    made the range cross a page, and the emitter writes it back inside the cell from the data here.
    """

    def view(index: int) -> tuple[str, int]:
        band = _band_at(bands, pages, index)
        return _column_view(lines[index], band, cell.side)

    def page_at(index: int) -> tuple[int, int | None]:
        return pages[index] if pages is not None else (0, None)

    out: list[tuple[str, tuple[int, int | None]]] = []
    if cell.first == cell.last:
        text, base = view(cell.first)
        return ((text[max(cell.start - base, 0) : max(cell.end - base, 0)], page_at(cell.first)),)
    text, base = view(cell.first)
    head = text[max(cell.start - base, 0) :].rstrip()
    if head:
        out.append((head, page_at(cell.first)))
    for index in range(cell.first + 1, cell.last):
        # A page marker that fell inside the range is not text: it is the annotation that made the
        # cell cross a page, and `block_lines` writes it back from the per-line pages here.
        if _page_of(lines[index]) is not None or lines[index].lstrip().startswith("<!--"):
            continue
        middle, _ = view(index)
        # **A blank line inside a cell is kept** (rule 4/5: Appendix 2's conditions are several
        # paragraphs each), but a band-clipped line loses the spaces that padded it out to the
        # boundary — they are the grid's, not the cell's.
        out.append((middle.rstrip() if middle.strip() else middle, page_at(index)))
    text, base = view(cell.last)
    tail = text[: max(cell.end - base, 0)].rstrip()
    if tail:
        out.append((tail, page_at(cell.last)))
    return tuple(out)


def _slice(
    lines: Sequence[str],
    cell: _Cell,
    pages: Sequence[tuple[int, int | None]] | None = None,
    bands: Mapping[int, int] | None = None,
) -> str:
    """The cell's characters: the body's own lines, from `first` to `last`, trimmed at the edges."""
    return "\n".join(text for text, _page in _cell_lines(lines, cell, pages, bands))


