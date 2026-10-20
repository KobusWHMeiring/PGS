"""Column-aware reading order for extracted PDF pages (D46).

`pdftotext -layout` keeps both columns of a two-column page on one visual line, so a
page read line by line alternates columns and no sentence that spans the gutter is a
quotable substring:

    The organic farm is an element
    a. Mechanisms and practices to
    within an environment or ecosystem.
    increase levels of organic matter in

A human can read that page. The citation audit cannot, because it accepts a quote only
when it is a verbatim, whitespace-normalised substring of one stored chunk. This module
re-emits such a page in reading order — column 1 top to bottom, then column 2 — and
leaves every other page byte-identical.

Four properties make it safe to run over the whole corpus:

- **Measured, not per-document.** Detection separates the populations cleanly on the
  four governed documents (coverage 0.70-1.0 on column pages, 0.16-0.17 on prose), so a
  retarget to another standard needs no allow-list and no migration.
- **Loss-free or a no-op.** Every non-space, non-newline character survives; a page with
  no qualifying band is returned as the same string object. The fallback is never a guess.
- **Not idempotent, and not assumed to be.** It runs once, at ingest, on `-layout`
  output. Measured: a second pass is a no-op on BPP pdf 4 and OPP pdf 11, but landscape
  pdf 4 gains bands and reorders further. Apply it exactly once.
- **Declinable.** A pure function cannot refuse once a band is found, so pages that are
  column-laid-out but must not be transformed live in `PAGE_LAYOUT_EXCLUSIONS`, and
  `apply_layout()` consults them. Data, not a flag: a new edition that starts
  mis-detecting fails a test rather than silently degrading citations.

Pure: a function of a page string. No Django, no PDF library, no clock, no locale.
"""

from __future__ import annotations

#: A gutter index qualifies when this fraction of the lines that *cross* it are blank
#: at it. Measured on the four governed documents: 0.70-1.0 on column pages, 0.16-0.17
#: on prose. The gap is wide enough that no per-document allow-list is needed.
MIN_COVERAGE = 0.70
#: A band inside a handful of lines is noise, not a gutter.
MIN_CROSSING_LINES = 6
#: Both sides must carry real text, or the band is the page margin.
MIN_CHAR_SHARE = 0.12


def column_bands(page: str) -> list[tuple[int, int]]:
    """The gutters of a column-laid-out page: `(start, end)` column indices, left to right.

    Detection has two steps, and the second exists because the first was measurably too
    generous.

    1. **The maximal band.** A run of column indices where the *coverage* — the fraction
       of lines that cross the index and are blank at it — is at least `MIN_COVERAGE`, the
       run is crossed by at least `MIN_CROSSING_LINES` lines, and both sides carry at
       least `MIN_CHAR_SHARE` of the page's non-space characters.
    2. **Narrowed to the untouched run.** A long left-column line can overflow into the
       first columns of the gutter and still leave coverage above 0.70, so the maximal
       band starts *inside* the left column. `de_column` then sees text at the band and
       keeps that line whole — which is the defect this narrowing removes. Measured on
       the shipped BPP (2026-10-22): the maximal band produced **66** lines that a band
       could not cut, and narrowing it to the columns no line writes in produced **13**,
       losslessly, on 6 pages. SAOSO and OPP are unchanged, so the table pages keep the
       bands their reviewed rows were measured with.

    The narrowed run is chosen inside the maximal band and is loss-free **by
    construction**: coverage 1.00 means no crossing line has a non-space character in
    that column, and the only characters dropped are the ones no line writes. When no
    column qualifies (a page whose columns really do touch, e.g. BPP pdf 3) the maximal
    band is kept — the refinement never invents a gutter.

    In:  `page` — one page as `pdftotext -layout` emits it.
    Out: the bands, or `[]` when the page is not column-laid-out.
    Fails: never. A page with no lines, or one line, has no bands.
    """
    lines = page.split("\n")
    width = max((len(line) for line in lines), default=0)
    if not width:
        return []
    non_space_total = sum(len(line.replace(" ", "")) for line in lines)

    def counts(index: int) -> tuple[int, int]:
        """`(lines that cross this column, of those, how many are blank here)`."""
        crossing = blank = 0
        for line in lines:
            if not line[:index].rstrip() or not line[index:].lstrip():
                continue  # the line does not cross this column
            crossing += 1
            if index < len(line) and line[index] == " ":
                blank += 1
        return crossing, blank

    def coverage(index: int) -> float:
        crossing, blank = counts(index)
        if crossing < MIN_CROSSING_LINES:
            return 0.0
        return blank / crossing

    def untouched(index: int) -> bool:
        """True when every line that crosses this column is blank at it."""
        crossing, blank = counts(index)
        return crossing >= MIN_CROSSING_LINES and blank == crossing

    def side_share(index: int) -> float:
        if not non_space_total:
            return 0.0
        left = sum(len(line[:index].replace(" ", "")) for line in lines)
        right = sum(len(line[index:].replace(" ", "")) for line in lines)
        return min(left, right) / non_space_total

    def qualifies(index: int) -> bool:
        return coverage(index) >= MIN_COVERAGE and side_share(index) >= MIN_CHAR_SHARE

    bands: list[tuple[int, int]] = []
    index = 0
    while index < width:
        if qualifies(index):
            start = index
            while index < width and qualifies(index):
                index += 1
            bands.append(_narrow_to_untouched(start, index, untouched))
        else:
            index += 1
    return bands


def _narrow_to_untouched(
    start: int, end: int, untouched
) -> tuple[int, int]:
    """The longest run of columns inside `[start, end)` that no line writes into.

    Returns the maximal band unchanged when it holds no such run — the fallback is never
    a guess, because a narrower band than the columns allow would cut a line mid-word.
    """
    best: tuple[int, int] | None = None
    index = start
    while index < end:
        if untouched(index):
            run_start = index
            while index < end and untouched(index):
                index += 1
            if best is None or (index - run_start) > (best[1] - best[0]):
                best = (run_start, index)
        else:
            index += 1
    return best if best is not None else (start, end)


def de_column(page: str, *, bands: list[tuple[int, int]] | None = None) -> str:
    """The page in reading order — column 1 top to bottom, then column 2, ….

    A line that still has text at the band positions (a spanning footnote, a full-width
    heading, a table row overflowing its cell) is **not** cut: it stays one fragment and
    is assigned to a column by its own start position. That assignment by position, not
    by index in the cut list, is what keeps a short line from shifting the rest left.

    In:  `page`; `bands` to override detection (tests, and applying a chosen band).
    Out: the reordered page, or **the same string object** when there is no band.
    Fails: never.
    """
    if bands is None:
        bands = column_bands(page)
    if not bands:
        return page  # the fallback is a no-op, never a guess

    columns: dict[int, list[str]] = {}
    for line in page.split("\n"):
        if any(line[start:end].strip() for start, end in bands):
            fragments = [(0, line)]  # a spanning line is never cut
        else:
            fragments = []
            cursor = 0
            for start, end in bands:
                fragments.append((cursor, line[cursor:start]))
                cursor = end
            fragments.append((cursor, line[cursor:]))
        for offset, text in fragments:
            column = sum(1 for start, _ in bands if offset >= start)
            columns.setdefault(column, []).append(text)

    blocks: list[str] = []
    for column in sorted(columns):
        rows = [text.rstrip() for text in columns[column]]
        while rows and not rows[0].strip():
            rows.pop(0)
        while rows and not rows[-1].strip():
            rows.pop()
        blocks.extend(rows)
    return "\n".join(blocks)


#: Pages that are column-laid-out but must NOT be transformed, with the measured reason.
#: Data, not a `layout` field: a retarget to another standard needs no migration, and a
#: new edition that starts mis-detecting fails a test rather than silently degrading.
PAGE_LAYOUT_EXCLUSIONS: dict[str, dict[int, str]] = {
    "saoso": {
        2: (
            "table of contents: its right-hand column IS the printed page numbers, so "
            "de-columning detaches every entry from its page and takes `parse_toc` from "
            "29 entries to 8 (appendix_spans then reports Appendix 1 ending on p.80 "
            "instead of p.75). Measured 2026-10-19."
        ),
        82: (
            "Appendix 4 Table 1: a 4-column additive table whose cells are one line "
            "each. Every character survives, but column-major order leaves the INS "
            "numbers (`INS 170`, `INS 184`, …) in one block, the product names in "
            "another and the `X` markers in a third, so no row can be located or "
            "quoted — the raw page is already row-coherent. Measured 2026-10-19."
        ),
        83: (
            "Appendix 4 Table 1 (continued): the same 4-column additive table. "
            "Column-major order separates `INS 508 Potassium chloride X` into pieces "
            "across three blocks; row association is destroyed and the raw page is "
            "already row-coherent. Measured 2026-10-19."
        ),
    },
    "opp": {
        11: (
            "3-column table (§6.5 labelling categories): one band where the page has two "
            "gutters, so every character is preserved but the reading order is wrong — "
            "`Self-claim organic | Applies where there is no organic certification and "
            "the organic claim is self- label or seal. | declared.` Measured 2026-10-19."
        ),
    },
}

#: Per-page band overrides, measured. A band is data when the detector's *maximal* run
#: starts a character or two inside a left-column line that overflows the gutter: rule 2
#: then keeps that line whole, and the right column's line on the same row is stranded in
#: the left block. BPP PDF 4 is the measured case — its left list item
#: `a. Sustainable land management2 ?` reaches column 40, so the maximal band (38, 42)
#: split the raw-manure rule: `raw manure … 60 days before` and `harvesting a crop …`
#: landed in different blocks. The measured gutter for the page is (40, 42), which makes
#: both that rule and `the addition of animal manure (composted)` contiguous while keeping
#: the success-gate manure sentence intact. Measured 2026-10-20.
#:
#: BPP PDF 3 is the second entry, and a different shape: its two columns are *vertically
#: offset* (the right column starts lower), so only a handful of lines carry text on both
#: sides and no column is "crossed by six lines". Detection therefore keeps the maximal
#: band (39, 45), which begins inside the left column's long lines, and the right column's
#: fragments (`biodiversity and cycles adapted`, `combines tradition, innovation`) were
#: emitted in the middle of the introduction — the same defect class as G7. `(43, 44)` is
#: the widest loss-free band, found by searching every band of width 1-7 for the fewest
#: spanning lines; it leaves only the full-width footnote and the page stamp, which are
#: genuinely spanning. Measured 2026-10-22.
PAGE_LAYOUT_BANDS: dict[str, dict[int, list[tuple[int, int]]]] = {
    "bpp": {3: [(43, 44)], 4: [(40, 42)]},
}


def apply_layout(
    pages: list[str], *, doc_key: str | None = None
) -> tuple[list[str], tuple[int, ...]]:
    """Transform every page except the recorded exclusions.

    In:  `pages` — normalised pages, `pages[N - 1]` is PDF page N; `doc_key` — a
         `CORPUS_DOCUMENTS` name, so exclusions can be applied. A new standard has no
         exclusion table: generic detection, no special case (D16, and the retarget
         rule in `build_principles.md` §I).
    Out: `(transformed_pages, changed)` where `changed` is the 1-based **PDF** page
         numbers whose text is different.
    Fails: never.
    """
    excluded = PAGE_LAYOUT_EXCLUSIONS.get(doc_key or "", {})
    overrides = PAGE_LAYOUT_BANDS.get(doc_key or "", {})
    transformed: list[str] = []
    changed: list[int] = []
    for number, page in enumerate(pages, 1):
        if number in excluded:
            transformed.append(page)
            continue
        fixed = de_column(page, bands=overrides.get(number))
        if fixed != page:
            changed.append(number)
        transformed.append(fixed)
    return transformed, tuple(changed)


__all__ = [
    "MIN_CHAR_SHARE",
    "MIN_COVERAGE",
    "MIN_CROSSING_LINES",
    "PAGE_LAYOUT_BANDS",
    "PAGE_LAYOUT_EXCLUSIONS",
    "apply_layout",
    "column_bands",
    "de_column",
]
