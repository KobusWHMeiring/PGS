"""Building `DocumentChunk`s from a reviewed table: one row, one quotable slice.

Split out of `knowledge/tables.py` (CONTEXT_CUTS_PRD step 8). The table itself is the artefact's
`<!-- table … -->` block; this module turns its rows into chunks — the prose around a grid, the row
chunks themselves, and the rendition a row is embedded from.

**This is the one place a chunk is not `section.text[start:end]`.** A row chunk's text joins
cells the paper prints in separate columns, which is why the citation audit's substring rule
needed the artefact's own row text (D73) and why `row_chunk` is the only constructor here.
"""

from __future__ import annotations

from dataclasses import replace

from knowledge.chunking import Chunk, chunk_section, estimate_tokens
from knowledge.corpus import section_anchor


#: Printed page numbers, as the reader sees them (`DocumentChunk.page`).
FIRST_PAGE = 76


def chunks_for_parsed_section(section) -> list[Chunk]:
    """One chunk per reviewed row of an artefact table, plus the prose around it.

    In:  `section` — a `ParsedSection` carrying `tables` parsed from a
         `<!-- table … -->` block (`knowledge.corpus`). Its cells are already slices of
         `section.text`.
    Out: chunks in document order: the prose before/between/after the tables, chunked by the
         ordinary chunker, and one chunk per row whose text is that row's cells.
    Side effects: none.
    Fails: never. A section with no tables yields exactly what `chunk_section` would, so a
         caller may route every section through here — but `chunks_for_sections` does not,
         because the common case should not pay for a branch it never takes.

    **Why the chunker cannot do this itself** (§3a rule 2, measured): a pipe table is one
    paragraph, and adding blank lines between rows changes nothing, because the chunker packs
    paragraphs to the token target. The row boundary is structure, so the row chunk is
    produced here and substituted.
    """
    rows = []
    for table in section.tables:
        for row in table.rows:
            span = (row.cells[0].start, row.cells[-1].end) if row.cells else (0, 0)
            rows.append((span[0], span[1], row, table.columns))
    if not rows:
        return [chunk_section(section)]

    rows.sort(key=lambda entry: entry[0])
    chunks: list[Chunk] = []
    cursor = 0
    for start, end, row, columns in rows:
        if start > cursor:
            chunks.extend(_prose_chunks(section, cursor, start))
        chunks.append(row_chunk(section, row, columns))
        cursor = max(cursor, end)
    if cursor < len(section.text):
        chunks.extend(_prose_chunks(section, cursor, len(section.text)))
    return chunks


def _prose_chunks(section, start: int, end: int) -> list[Chunk]:
    """Chunk the section text in `[start, end)` as though it were its own section.

    Offsets are shifted back into the owning section so `source_start` keeps meaning "where
    this chunk sits in the section" — the offsets are the only evidence that nothing was lost.
    Leading whitespace is skipped rather than kept: a segment that starts at a row's end starts
    with the newline that ended that row, and a chunk whose first line is blank is noise in the
    reader and in the prompt.
    """
    # A segment that begins at a row's end begins with the newline that ended the row, so the
    # chunk would start with a blank line — shown by the reader and read by the model as an
    # empty first line. Measured 2026-11-01 on the OPP's §2.3, whose notes under the sliding
    # scale are the sentences that qualify every amount above them. The offsets move with the
    # text, so `source_start` still says exactly where the slice sits.
    while start < end and section.text[start].isspace():
        start += 1
    piece = section.text[start:end]
    if not piece.strip():
        return []
    refs = tuple(
        ref for ref in section.sub_refs if start <= ref.start < end
    )
    shifted = replace(
        section,
        text=piece,
        sub_refs=tuple(
            type(ref)(ref.ref, max(ref.start, start) - start, min(ref.end, end) - start)
            for ref in refs
        ),
    )
    heading = section.text.partition("\n")[0]
    chunks = [
        replace(chunk, source_start=chunk.source_start + start,
                source_end=chunk.source_end + start)
        for chunk in chunk_section(shifted)
    ]
    # A table section that opens straight into its rows has no prose before the first cell
    # except the heading, and the chunker then yields a chunk that is *only* the heading. It
    # would be retrievable and citable while saying nothing. Measured 2026-10-30 on the
    # landscape's `PGS SEALS AND THEIR USE` table, which prints no lead-in sentence.
    return [chunk for chunk in chunks if chunk.text.removeprefix(heading).strip()]


def row_chunk(section, row, columns: tuple[str, ...] = ()) -> Chunk:
    """One reviewed row's chunk: its cells, the page it starts on, and a locator.

    `text` is the row's cells joined by a newline — the documented exception to "a chunk is
    always `section.text[start:end]`" (assumption 3, and §5.1 of the landscape PRD: a blank
    line would make the reader build two paragraph blocks for one row). `heading_path` carries
    the label so a citation can say which step it came from, and the label is *not* text: on
    this document it is also printed in the first cell, and a corpus that repeated it would be
    quoting a word the paper prints once.

    **`embedding_text` is the row's labels, and it is why a numeric row is retrievable at all
    (D73).** `Below R 250,000 / 1,500 / 900` shares no word with any question, so a vector of
    the cells describes nothing; `columns` supplies the words — `Annual farm turnover (gross
    sales): Below R 250,000 · Initial certification fee (R): 1,500 · Renewal fee (R): 900`.
    Measured 2026-11-01: without it the sliding scale's six bands ranked nowhere, and `/ask/`
    answered *"the document does not specify the exact assessment fee"* for a fee the document
    prints (`CHAT_ANSWER_COVERAGE_PRD` G10). `text` is untouched: the quote audit and the
    reader see only what the paper prints.
    """
    label = row.label_text
    heading_path = (
        f"{section.heading_path} — {label[:80]}" if label else section.heading_path
    )
    text = row.text
    return Chunk(
        section_ref=section.section_ref,
        text=text,
        token_count=estimate_tokens(text),
        heading_path=heading_path,
        page=row.page if row.page is not None else section.page,
        anchor=section_anchor(f"{section.heading_path} {label}") if label else section.anchor,
        embedding_text=_embedding_rendition(heading_path, row, columns),
    )


def _embedding_rendition(heading_path: str, row, columns: tuple[str, ...]) -> str:
    """The text a row is embedded from: its heading, then `column: cell` for each printed cell.

    In:  `heading_path` — the section plus the row's label; `row` — a `ParsedTableRow`;
         `columns` — the table's printed column labels.
    Out: one line, `·`-separated. Empty cells are skipped: an empty cell is *silence*, and a
         label with nothing after it would embed a word the row does not say.
    """
    parts = [heading_path]
    for index, cell in enumerate(row.cells):
        value = " ".join((cell.text or "").split())
        if not value:
            continue
        column = columns[index] if index < len(columns) else ""
        parts.append(f"{column}: {value}" if column else value)
    return " · ".join(parts)

