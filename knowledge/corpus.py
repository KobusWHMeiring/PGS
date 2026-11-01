"""The canonical corpus format — document text as reviewed data (D53).

Every other part of ingestion trusts this module. A `*.md` file under
`knowledge/corpus/` is *the* text of a governed document: the chunker slices it, the
chatbot quotes it, and a human has read it. The PDF is still the source of truth, but it
is read **once**, by `scripts/build_corpus.py`, and the result is reviewed in a diff
instead of being re-derived by layout heuristics on every ingest.

That is a deliberate inversion of D46/D51/D52. Those decisions kept repairing the
extractor (`columns.py`, `tables.py`, `reflow.py`) because the extractor was on the
runtime path: every layout defect was a production bug in the chatbot. Here the
extractor becomes a generator that runs per *edition*, and the reviewed artefact — not
the heuristic — is what ships.

The format is Markdown with machine annotations, because the two audiences are a human
with a red pen and a parser with no opinions:

    <!-- corpus
    doc_key: bpp
    source: pgs_docs/Basic Production Principles_ENG_PRINT.pdf
    sha256: 9f3a…
    generator: knowledge corpusgen v1
    -->
    <!-- page: 3 printed: none -->
    ## INTRODUCTION

    The terms of reference for these principles …

Rules the reader enforces, because each one is a silent corruption otherwise:

1. **A page marker before any text.** `<!-- page: N printed: M -->` — `N` is the PDF
   page index (1-based) and `M` the number the document prints, or `none` (D42: the BPP
   prints no page numbers). A block with no page is a block whose quote cannot be traced
   to paper, so it is an error, not a default.
2. **Provenance is per block, not per section.** A section may span pages; the page marker
   in force when a block starts is that block's page. `ParsedSection.page` stays what D42
   says it is — the *printed* page of the section's heading.
3. **A heading is `#`-level Markdown.** Depth is the number of `#`s and exists only to
   build `heading_path`; it is never part of a citation. `section_ref` comes from an
   optional `<!-- ref: S20.1.1 -->` annotation immediately before the heading, so the
   reader needs no per-document scheme — BPP has none, SAOSO emits one.
4. **Everything else is text, verbatim.** Blank lines included: they are the chunker's
   paragraph boundaries, and a reader that "tidies" them changes chunk boundaries.
5. **A table is a block, and its structure is parsed, never recovered from text** (D73).
   `<!-- table` opens it with `cols:` (and an optional `legend:`), `<!-- row: Label -->`
   starts a row, `<!-- cell -->` starts a cell, `<!-- row-divider: … -->` labels the row
   beneath it, and `<!-- /table -->` closes it. The cells stay in `section.text` — a cell is
   still a slice — while the column labels and the row/cell offsets travel beside it, the
   way `sub_refs` carries offsets. **Measured, and the reason the block exists:** a GFM
   pipe table chunks as *one* chunk, blank lines between rows change nothing (the chunker
   packs paragraphs), and until 2026-10-30 `<!-- cell -->` was silently dropped as a
   reviewer's note — the table kept all its text and lost every boundary, with every other
   guard green. So a table annotation that does not parse **raises**, and a comment whose
   first word is a format word it misspells (`cells`, `col:`) raises too.
6. **A sub-clause is a marker, and its slice is computed like the parser's** (rule 6; added
   for P4, 2026-11-01). `<!-- sub: 4.5(2)(c) -->` says the *next* text line opens a
   sub-clause an artefact can otherwise only lose: the OPP prints items `1)`/`a.` inside
   `4.5` and they have no heading of their own, so a heading-only transcription would turn
   twenty-four citable addresses into one. The depth comes from the address itself
   (`sub_ref_depth`), and the end of a slice is the next marker of the same or shallower
   depth — the same `any_level_end` rule `OppParser` uses, because the artefact must
   reproduce the parser's spans, not merely its text. **The failure this prevents is silent
   and it was measured:** converting the OPP to an artefact without this rule dropped
   `4.5(1)`, `4.5(2)(c)` and `4.5(4)` while every other guard stayed green
   (`test_opp_sub_refs_survive_into_the_database` caught it, 2026-11-01).

Reviewed edits are *not* annotated in the file. The artefact says what the document says;
which lines needed a human is recorded as data in `knowledge/corpus.py` (`CORPUS_EDITS`),
so the traceability test can prove the edit was necessary (its `original` is on that
page) and applied (its `replacement` is in the file). An edit nobody can justify is a
failing test, not a comment.

Pure: text in, `ParsedSection`s out. No Django, no PDF, no clock, no network.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from knowledge.sections import (
    ParsedSection,
    ParsedTable,
    ParsedTableRow,
    TableCell,
    TableRowDivider,
    any_level_end,
    slug,
)


class CorpusFormatError(ValueError):
    """The artefact is malformed. Never swallowed: a silent default loses provenance."""


#: `<!-- page: 12 printed: 11 -->` — PDF page and the number the document prints.
PAGE = re.compile(r"^<!--\s*page:\s*(\d+)\s+printed:\s*(\d+|none)\s*-->\s*$")

#: `<!-- ref: S20.1.1 -->` — the citation for the heading that follows.
REF = re.compile(r"^<!--\s*ref:\s*(\S.*?)\s*-->\s*$")

#: `<!-- sub: 4.5(2)(c) -->` — a sub-clause printed *inside* a section, opening at the next text
#: line. See rule 6: the OPP's items are the case, and dropping them costs 24 citable addresses.
SUB = re.compile(r"^<!--\s*sub:\s*(\S.*?)\s*-->\s*$")

#: `<!-- cell -->` — a cell boundary inside a table row. Structural, not a paragraph break, so a
#: cell may hold blank lines and lists: Appendix 2's conditions are five paragraphs each.
CELL = re.compile(r"^<!--\s*cell\s*-->\s*$")

#: `<!-- row: Step 1 -->`, or `<!-- row -->` when the paper prints no label column.
ROW = re.compile(r"^<!--\s*row(?::\s*(.*?))?\s*-->\s*$")

#: `<!-- row-divider: South African specific qualifier -->` — a label printed *between* rows,
#: applying to the row beneath it. A trailing `part` or `qualifier` sets the kind; the rest is
#: the printed text.
DIVIDER = re.compile(r"^<!--\s*row-divider:\s*(.+?)\s*-->\s*$")

#: `<!-- table` opens a block whose fields follow, `<!-- /table -->` closes it. The close is
#: explicit because a table that ends by inference is a table whose last row can swallow the
#: prose after it.
TABLE_OPEN = re.compile(r"^<!--\s*table\s*$")
TABLE_CLOSE = re.compile(r"^<!--\s*/table\s*-->\s*$")

#: A field inside a `<!-- table` header. `cols` is required (`|`-separated); `legend` is the
#: reviewed note the reader prints above the grid; the other four are D77's shape fields —
#: `layout` (which shape), `branch` (where the rows fork), `title` (one per row) and `fee_label`
#: (one per fee box). Every one is reviewed data: the renderer infers none of them.
TABLE_FIELD = re.compile(
    r"^\s*(cols|legend|layout|branch|title|fee_label):\s*(.*?)\s*$"
)

#: The shapes the reader can draw (D77). `grid` is the default so every table written before D77
#: keeps the shape it had; `process` is the cards.
TABLE_LAYOUTS = ("grid", "process")

#: `<!-- corpus` … `-->` at the top of the file.
HEADER_OPEN = re.compile(r"^<!--\s*corpus\s*$")
HEADER_CLOSE = re.compile(r"^-->\s*$")
HEADER_FIELD = re.compile(r"^\s*([a-z0-9_]+):\s*(.*?)\s*$")

#: `## INTRODUCTION`
HEADING = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$")

#: The annotation vocabulary, plus the field names a `<!-- table` header accepts. A comment
#: that *starts* like one of these is an annotation attempt and must parse strictly; one that
#: does not is a reviewer's note.
#:
#: This list is load-bearing, and the reason is measured: `ANNOTATION` matched only
#: `corpus|page|ref` until 2026-10-30, so `<!-- cell -->` fell through to `COMMENT` and was
#: dropped as a note. A table typed with it kept all of its text and lost every cell
#: boundary, with every other guard green — a quote that can never be cited.
ANNOTATION_WORDS = (
    "corpus",
    "page",
    "ref",
    "sub",
    "table",
    "/table",
    "row",
    "row-divider",
    "cell",
    "cols",
    "legend",
)

#: Any other HTML comment: a reviewer's note. Ignored, and never emitted as text.
COMMENT = re.compile(r"^<!--.*-->\s*$")

REQUIRED_HEADER_FIELDS = ("doc_key", "source", "sha256", "generator")


def annotation_attempt(line: str) -> str | None:
    """The format word a comment is a misspelling of, or `None` for a reviewer's note.

    In:  `line` — one line that `COMMENT` already matched, e.g. `<!-- cells -->`.
    Out: the annotation it was reaching for (`"cell"`), or `None`.

    Why a prefix test and not edit distance: the vocabulary is closed and tiny, and the typos
    that cost this repo a session are the ones a person actually types — `cells`, `col:`, an
    annotation missing its colon. A reviewer's note whose first word happens to be `table` will
    raise, which is the right way round: the note is easily reworded, and the silent drop is
    not detectable afterwards.
    """
    body = line.strip()[4:]  # after `<!--`
    if body.endswith("-->"):
        body = body[:-3]
    words = body.strip().split()
    if not words:
        return None
    token = words[0].rstrip(":,").lower()
    for name in ANNOTATION_WORDS:
        if token == name:
            return name
        if len(token) >= 3 and (name.startswith(token) or token.startswith(name)):
            return name
    return None


def row_divider(value: str):
    """A `row-divider`'s text and kind. The kind trails, as the format says it does."""
    words = value.split()
    if words and words[-1].lower() in ("part", "qualifier"):
        return TableRowDivider(" ".join(words[:-1]), words[-1].lower())
    return TableRowDivider(value.strip(), "qualifier")


def branch_row(value: str, rows: list[dict], where: int) -> int:
    """In: a `branch:` field, the table's raw rows, and the line. Out: a 0-based row index.

    Why two spellings: the reviewer reading the paper writes the row's **label** (`branch: Step
    3`), and the artefact format's own vocabulary is the **index** (`branch: 2`). Both resolve to
    the same thing here, so nothing downstream has to know which was typed.

    Refuses an index past the last row and a label that names no row. Silence is the failure this
    guards against: a fork pointing at nothing renders a linear table that looks like it has an
    alternative path, and the two paths would be the same path.
    """
    count = len(rows)
    wanted = value.strip()
    if wanted.isdigit():
        index = int(wanted)
        if index >= count:
            raise CorpusFormatError(
                f"line {where}: `branch: {wanted}` names row {index} of a {count}-row table "
                "(the index is 0-based). The alternative path would start past the last row, "
                "so no row would be one."
            )
        return index
    index = next(
        (
            position
            for position, row in enumerate(rows)
            if row["label"].strip().casefold() == wanted.casefold()
        ),
        -1,
    )
    if index < 0:
        labels = ", ".join(repr(row["label"]) for row in rows)
        raise CorpusFormatError(
            f"line {where}: `branch: {wanted}` names no row of this table. Its rows are "
            f"{labels}, and a fork that points at none of them would render as two paths that "
            "are the same path."
        )
    return index

#: `DocumentChunk.anchor` is a `CharField(max_length=128)`. A clause heading can be a whole
#: sentence, so its slug overruns the column (the SAOSO artefact's first ingest failed with
#: `value too long`, 2026-10-28).
ANCHOR_MAX = 128


def sub_ref_depth(ref: str) -> int:
    """How deep a printed sub-clause sits, from its own address: `4.5(2)(c)` is depth 3.

    A depth is what `any_level_end` needs in order to decide where a slice stops, and the
    address is where it already lives. **Derived from the reference, never from indentation:**
    `OppParser`'s calibration to the OPP's printed margins is exactly the kind of per-document
    rule the artefact exists to stop repeating.

    Fails: `CorpusFormatError` for an address with no parenthesised level. A `sub:` that reads
    `4.5` is a second heading for a section that already has one, and the duplicate would be a
    citation that resolves to two spans.
    """
    ref = (ref or "").strip()
    depth = ref.count("(") + 1
    if depth == 1:
        raise CorpusFormatError(
            f"`sub: {ref}` has no parenthesised level. A sub-clause is `4.5(2)` or "
            "`4.5(2)(c)`; a `sub:` that repeats the section's own reference would give one "
            "address two spans."
        )
    return depth


def section_anchor(title: str) -> str:
    """A locator for a section the source never numbered, inside the column's limit.

    Truncated at a word boundary rather than mid-word. This only ever shortens a *fallback*
    locator: `reading_anchor` prefers a `section_ref`, and a document that prints clause
    numbers keeps its real address.
    """
    value = slug(title)
    if len(value) <= ANCHOR_MAX:
        return value
    return value[:ANCHOR_MAX].rsplit("-", 1)[0]


@dataclass(frozen=True)
class Block:
    """One paragraph of document text with the page it came from.

    `page` is the **PDF** page (provenance: what the traceability test checks against);
    `printed` is the number the document shows the reader (D42). They are different
    things and confusing them is how a citation points at the wrong paper.
    """

    page: int
    printed: int | None
    text: str


@dataclass(frozen=True)
class CorpusDocument:
    """One reviewed document: its metadata, its text blocks and its sections."""

    doc_key: str
    source: str
    sha256: str
    generator: str
    sections: tuple[ParsedSection, ...]
    blocks: tuple[Block, ...]
    path: Path | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def digest(self) -> str:
        """sha256 of the artefact file — recorded on ingest so drift is visible."""
        if self.path is None or not self.path.exists():  # pragma: no cover - tests
            return ""
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    @property
    def text(self) -> str:
        """The whole document as one string, sections in order — what gets chunked."""
        return "\n\n".join(section.text for section in self.sections)


def _parse_header(lines: list[str], index: int) -> tuple[dict[str, str], int]:
    """Read the `<!-- corpus … -->` header. Returns the fields and the next line index."""
    if not lines or not HEADER_OPEN.match(lines[0]):
        raise CorpusFormatError(
            "expected a `<!-- corpus` header on line 1; without it the artefact has no "
            "source PDF and no sha256, so nothing downstream can tell where it came from"
        )
    fields: dict[str, str] = {}
    while index < len(lines):
        line = lines[index]
        index += 1
        if HEADER_CLOSE.match(line):
            break
        match = HEADER_FIELD.match(line)
        if not match:
            raise CorpusFormatError(f"header line {index} is not `key: value`: {line!r}")
        fields[match.group(1)] = match.group(2)
    else:  # pragma: no cover - unreachable without a broken file
        raise CorpusFormatError("the header comment is never closed with `-->`")
    missing = [name for name in REQUIRED_HEADER_FIELDS if not fields.get(name)]
    if missing:
        raise CorpusFormatError(f"header is missing {', '.join(missing)}")
    return fields, index


#: `## `, `### ` … at the start of a line — the artefact's structural marker.
HEADING_MARKER = re.compile(r"^#{1,6}[ 	]+")


def _heading_text(current: dict) -> str:
    """The heading line as the section's **text**: the marker comes off when it has a `ref:`.

    A `#`-heading in the artefact is *structure* — it builds `heading_path` and nothing else
    (`knowledge/corpus.py` rules 3). A section annotation tells the reader that the heading is
    the document's own cited line, and for SAOSO that line is the clause itself
    (`23.3. Operators shall not use forced or involuntary labour …`). Left in, the marker
    became a `Heading` block in the reader, so every clause printed at heading weight and its
    wrapped continuation split off again — the defect
    `BugFixes/reader_clause_line_breaks.md` had just fixed from the other direction.

    The BPP has no `ref:` annotations, so its headings are real headings and keep the marker
    (`## INTRODUCTION` renders as one, `PASSAGE_LAYOUT_PRD` §3).
    """
    return HEADING_MARKER.sub("", current["heading"]) if current["ref"] else current["heading"]


def parse_blocks(text: str) -> CorpusDocument:
    """Parse an artefact's text into sections and page-attributed blocks.

    In:  `text` — the contents of a `knowledge/corpus/*.md` file.
    Out: a `CorpusDocument`. Sections partition the text: a section's `text` is its
         heading plus every body line up to the next heading, exactly as written.
    Fails: `CorpusFormatError` for a missing header, an unparseable page marker, or body
         text before the first page marker.
    """
    lines = text.split("\n")
    fields, index = _parse_header(lines, 1)

    sections: list[ParsedSection] = []
    blocks: list[Block] = []
    stack: list[tuple[int, str]] = []
    pending_ref: str | None = None
    #: A `sub:` waiting for the text line it opens. One at a time: a marker with no text is a
    #: slice of nothing, and a second marker before the first line would silently drop one.
    pending_sub: str | None = None
    page: int | None = None
    printed: int | None = None
    current: dict | None = None
    new_block = True
    #: The open `<!-- table … -->` block, if any. One at a time: a nested table is a typo, and a
    #: table that never closes is an error rather than a section that quietly owns the rest.
    table: dict | None = None

    def add_text(line: str, where: int) -> int:
        """Append one body line. Returns its index in `current["body"]`.

        The index is what lets a cell keep a *slice* of the section rather than a copy: the
        offsets are computed once, in `flush()`, from these indices.
        """
        nonlocal new_block, pending_sub
        current["body"].append(line)
        if line.strip() and pending_sub is not None:
            current["subs"].append((pending_sub, len(current["body"]) - 1))
            pending_sub = None
        if line.strip() and pending_ref is not None:
            # A `ref:` annotates the heading *below* it. Body text in between means the
            # annotation was typed in the wrong place, and silently attaching it to a
            # heading further down would give a section someone else's citation.
            raise CorpusFormatError(
                f"line {where}: `ref: {pending_ref}` must be immediately before its "
                "heading, not followed by body text"
            )
        if not line.strip():
            new_block = True
            return len(current["body"]) - 1
        if page is None:
            raise CorpusFormatError(
                f"block on line {where} has no page marker: {line[:60]!r}"
            )
        if new_block or not blocks or blocks[-1].page != page or blocks[-1].printed != printed:
            blocks.append(Block(page=page, printed=printed, text=line))
        else:
            # Consecutive non-blank lines are one block; a blank line ends it.
            previous = blocks[-1]
            blocks[-1] = Block(
                page=previous.page,
                printed=previous.printed,
                text=f"{previous.text}\n{line}",
            )
        new_block = False
        return len(current["body"]) - 1

    # -- the table block ------------------------------------------------------------------

    def close_cell(where: int) -> None:
        """Finish the open cell, trimming the blank lines that only space it out."""
        nonlocal table
        cell = table["cell"]
        if cell is None:
            return
        body = current["body"]
        while cell["lines"] and not body[cell["lines"][0]].strip():
            cell["lines"].pop(0)
        while cell["lines"] and not body[cell["lines"][-1]].strip():
            cell["lines"].pop()
        cell["first"] = cell["lines"][0] if cell["lines"] else None
        cell["last"] = cell["lines"][-1] if cell["lines"] else None
        table["row"]["cells"].append(cell)
        table["cell"] = None

    def close_row(where: int) -> None:
        nonlocal table
        if table["row"] is None:
            return
        close_cell(where)
        row = table["row"]
        columns = len(table["columns"])
        if not row["cells"]:
            raise CorpusFormatError(
                f"line {where}: a `row` with no cells. A row that cites nothing is a row the "
                "reviewer did not finish — two `<!-- row: … -->` annotations in a row lose the "
                "one between them."
            )
        if len(row["cells"]) > columns:
            raise CorpusFormatError(
                f"line {where}: a `row` with more cells ({len(row['cells'])}) than the "
                f"table's `cols` ({columns}). The extra cell would never be rendered or "
                "quoted, because nothing knows which column it belongs to."
            )
        if all(not cell["lines"] for cell in row["cells"]):
            raise CorpusFormatError(
                f"line {where}: a `row` with no text in any cell. It would become a "
                "zero-length chunk — a citation with nothing in it, and a row the reviewer "
                "left unfinished."
            )
        table["rows"].append(row)
        table["row"] = None

    def close_table(where: int) -> None:
        nonlocal table
        close_row(where)
        if not table["rows"]:
            raise CorpusFormatError(
                f"line {where}: a `table` block with no rows. Its column labels would render "
                "as a table with nothing in it, and the page's text would be missing from the "
                "corpus entirely — which is the defect this block exists to prevent."
            )
        if table["pending_dividers"]:
            raise CorpusFormatError(
                f"line {where}: a `row-divider` after the table's last row. A divider "
                "qualifies the row beneath it, and there is none — the label would silently "
                "vanish."
            )
        fields = table["fields"]
        rows = table["rows"]
        if "branch" in fields:
            table["branch"] = branch_row(fields["branch"], rows, where)
        titles = fields.get("title", ())
        if titles and len(titles) != len(rows):
            raise CorpusFormatError(
                f"line {where}: `title:` names {len(titles)} titles for {len(rows)} rows. "
                "Titles are `|`-separated, one per row in printed order, or omitted entirely — "
                "a short list would silently shift every title onto the row above."
            )
        current["tables"].append(dict(table))
        table = None

    def open_row(where: int, label: str | None) -> None:
        nonlocal table
        close_row(where)
        table["row"] = {
            "label": (label or "").strip(),
            "page": printed,
            "cells": [],
            # A divider is printed *between* rows and qualifies the one beneath it, so it is
            # collected while no row is open and claimed by the next `<!-- row: … -->`.
            "dividers": tuple(table["pending_dividers"]),
            "cursor": len(current["body"]),
        }
        table["pending_dividers"] = []

    def open_cell(where: int) -> None:
        nonlocal table
        if table["row"] is None:
            raise CorpusFormatError(
                f"line {where}: a `cell` annotation before any row. A cell belongs to a "
                "row; outside one "
                "its text would become a chunk no column label points at."
            )
        close_cell(where)
        table["cell"] = {"lines": [], "first": None, "last": None,
                         "cursor": len(current["body"])}

    # -- flush ----------------------------------------------------------------------------

    def flush() -> None:
        nonlocal table, pending_sub
        if current is None:
            return
        if pending_sub is not None:
            raise CorpusFormatError(
                f"`sub: {pending_sub}` has no text. A sub-clause marker opens the line below "
                "it, and a marker with nothing under it is a slice that quotes nothing."
            )
        refs = [ref for ref, _ in current["subs"]]
        duplicates = sorted({ref for ref in refs if refs.count(ref) > 1})
        if duplicates:
            raise CorpusFormatError(
                f"`sub` marker repeated in one section: {', '.join(duplicates)}. Two markers "
                "with one address give a citation two spans, and the audit cannot quote both."
            )
        if table is not None:
            raise CorpusFormatError(
                "a `table` block was never closed with `<!-- /table -->`. Its rows would be "
                "read as body text from here to the end of the section, so the last row would "
                "silently own every paragraph after it."
            )
        body = current["body"]
        while body and not body[-1].strip():
            body.pop()
        heading_text = _heading_text(current)
        lines_in_text = [heading_text, *body]
        text = "\n".join(lines_in_text).strip()
        offsets: list[int] = []
        cursor = 0
        for line in lines_in_text:
            offsets.append(cursor)
            cursor += len(line) + 1

        def char_offset(line_index: int) -> int:
            """The character offset of a **body** line (`0` is the first after the heading)."""
            position = line_index + 1
            if position >= len(lines_in_text):
                return len(text)
            return min(offsets[position], len(text))

        def cell_of(raw: dict) -> TableCell:
            if raw["first"] is None:
                # An empty cell means *silence*, which §4 item 3 requires to be distinguishable
                # from a cell nobody filled in — so it is recorded, with a zero-width slice.
                at = char_offset(raw["cursor"])
                return TableCell("", at, at)
            start = char_offset(raw["first"])
            end = min(
                char_offset(raw["last"]) + len(lines_in_text[raw["last"] + 1]), len(text)
            )
            return TableCell(text[start:end], start, end)

        # Rule 6: markers become offsets through the same helper the PDF parsers use, so an
        # artefact reproduces the parser's *slices* and not just its words. `lines_in_text`
        # puts the heading at 0 and the first body line at 1, which is what `char_offset`
        # already assumes.
        subs = tuple(
            any_level_end(
                [(ref, sub_ref_depth(ref), line_index + 1) for ref, line_index in current["subs"]],
                offsets,
                len(text),
            )
        )

        tables = tuple(
            ParsedTable(
                columns=raw["columns"],
                legend=raw["fields"].get("legend", ""),
                layout=raw["fields"].get("layout", "grid"),
                branch=raw.get("branch"),
                titles=raw["fields"].get("title", ()),
                fee_labels=raw["fields"].get("fee_label", ()),
                rows=tuple(
                    ParsedTableRow(
                        cells=tuple(cell_of(cell) for cell in row["cells"]),
                        label=row["label"],
                        page=row["page"],
                        dividers=row["dividers"],
                    )
                    for row in raw["rows"]
                ),
            )
            for raw in current["tables"]
        )

        sections.append(
            ParsedSection(
                section_ref=current["ref"],
                text=text,
                heading_path=(
                    " > ".join(title for _, title in stack) or current["title"]
                ),
                page=current["page"],
                anchor=section_anchor(current["title"]),
                tables=tables,
                sub_refs=subs,
            )
        )

    while index < len(lines):
        line = lines[index]
        index += 1

        marker = PAGE.match(line)
        if marker:
            if table is not None and table["header"]:
                raise CorpusFormatError(
                    f"line {index}: a page marker inside a table's header. The header is a list "
                    "of `key: value` fields; a page marker there was meant for a row."
                )
            page = int(marker.group(1))
            printed = None if marker.group(2) == "none" else int(marker.group(2))
            continue

        if table is not None and table["header"]:
            if HEADER_CLOSE.match(line):
                columns = table["fields"].get("cols", ())
                if not columns:
                    raise CorpusFormatError(
                        f"line {index}: a `table` block with no `cols:` field. The column "
                        "labels are what the reader prints above the grid and what tells a "
                        "cell which column it belongs to."
                    )
                table["columns"] = columns
                table["header"] = False
                continue
            field = TABLE_FIELD.match(line)
            if not field:
                raise CorpusFormatError(
                    f"line {index}: a table header line that is not one of `cols:`, `legend:`, "
                    f"`layout:`, `branch:`, `title:`, `fee_label:` or `-->`: {line!r}"
                )
            key = field.group(1)
            if key in table["fields"]:
                raise CorpusFormatError(
                    f"line {index}: `{key}:` appears twice in one table header. The second "
                    "would silently replace the first."
                )
            if key == "cols":
                value = tuple(part.strip() for part in field.group(2).split("|"))
                if not value or not all(value):
                    raise CorpusFormatError(
                        f"line {index}: `cols:` names an empty column: {field.group(2)!r}. "
                        "Columns are `|`-separated, and a blank one would make every cell "
                        "beneath it unlabelled."
                    )
            elif key == "layout":
                value = field.group(2)
                if value not in TABLE_LAYOUTS:
                    raise CorpusFormatError(
                        f"line {index}: `layout: {value}` is not a shape the reader draws. "
                        f"Use one of: {', '.join(TABLE_LAYOUTS)}. An unknown shape would "
                        "render as whatever the template's fallback branch guessed."
                    )
            elif key in ("title", "fee_label"):
                value = tuple(part.strip() for part in field.group(2).split("|"))
                if not all(value):
                    raise CorpusFormatError(
                        f"line {index}: `{key}:` has an empty entry: {field.group(2)!r}. "
                        f"The entries are `|`-separated, one per "
                        f"{'row' if key == 'title' else 'fee box'}, and a blank one would "
                        "render a heading with no words in it."
                    )
            else:
                # `legend` and `branch`. `branch` is resolved when the table closes, because
                # until then there are no rows for it to point at.
                value = field.group(2)
            table["fields"][key] = value
            continue

        if TABLE_OPEN.match(line):
            if current is None:
                raise CorpusFormatError(
                    f"line {index}: a table before any heading. A table belongs to a section "
                    "— without one there is no heading path and no page to cite it by."
                )
            if table is not None:
                raise CorpusFormatError(
                    f"line {index}: a second `<!-- table` while one is already open. Close the "
                    "first with `<!-- /table -->`, or the rows run into each other."
                )
            table = {
                "header": True,
                "fields": {},
                "columns": (),
                "rows": [],
                "row": None,
                "cell": None,
                "pending_dividers": [],
            }
            continue

        if TABLE_CLOSE.match(line):
            if table is None:
                raise CorpusFormatError(
                    f"line {index}: `<!-- /table -->` without an open table. A close with no "
                    "open is a table whose rows the reviewer wrote but whose header is "
                    "missing — the rows would be silently read as prose."
                )
            close_table(index)
            continue

        if table is not None:
            divider = DIVIDER.match(line)
            if divider:
                close_cell(index)
                table["pending_dividers"].append(row_divider(divider.group(1)))
                continue
            row = ROW.match(line)
            if row:
                open_row(index, row.group(1))
                continue
            if CELL.match(line):
                open_cell(index)
                continue
            if HEADING.match(line):
                raise CorpusFormatError(
                    f"line {index}: a heading inside a table block. A heading opens a new "
                    "section, and the table's cells after it would belong to that section "
                    "with no row to carry them."
                )
            if SUB.match(line):
                raise CorpusFormatError(
                    f"line {index}: a `sub:` marker inside a table block. A row is its own "
                    "chunk and carries its own address, so a sub-clause has no span to open "
                    "here. Move the marker above the table."
                )
            if COMMENT.match(line):
                attempt = annotation_attempt(line)
                if attempt:
                    raise CorpusFormatError(
                        f"line {index}: malformed annotation inside a table block — "
                        f"`{line.strip()}` starts like `{attempt}` but does not parse. Only "
                        "`<!-- row: … -->`, `<!-- row-divider: … -->`, `<!-- cell -->` and "
                        "`<!-- /table -->` are allowed here."
                    )
                continue  # a reviewer's note, never text
            if line.lstrip().startswith("<!--"):
                raise CorpusFormatError(
                    f"line {index}: malformed comment inside a table block: {line!r}"
                )
            if table["cell"] is None:
                if line.strip():
                    raise CorpusFormatError(
                        f"line {index}: text inside a table block but outside any `cell`: "
                        f"{line[:60]!r}. A cell is delimited by `<!-- cell -->`; text with no "
                        "cell has no column, so no row could quote it."
                    )
                continue  # a blank line between rows, for the reviewer's eye only
            add_text(line, index)
            table["cell"]["lines"].append(len(current["body"]) - 1)
            continue

        ref = REF.match(line)
        if ref:
            if pending_ref is not None:
                raise CorpusFormatError(
                    f"line {index}: two `ref:` annotations in a row before one heading "
                    f"({pending_ref!r}, then {ref.group(1)!r}). One reference per heading — "
                    "the second would silently replace the first."
                )
            pending_ref = ref.group(1)
            continue

        sub = SUB.match(line)
        if sub:
            if pending_sub is not None:
                raise CorpusFormatError(
                    f"line {index}: two `sub:` markers in a row without text between them "
                    f"({pending_sub!r}, then {sub.group(1)!r}). The first would open a slice "
                    "with no words in it."
                )
            pending_sub = sub.group(1)
            continue

        heading = HEADING.match(line)
        if heading:
            flush()
            depth = len(heading.group(1))
            title = heading.group(2)
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, title))
            if page is None:
                raise CorpusFormatError(
                    f"heading {title!r} has no page marker before it; every block must "
                    "be traceable to a PDF page"
                )
            new_block = True
            current = {
                "ref": pending_ref,
                "heading": line.rstrip(),
                "title": title,
                "page": printed,
                "body": [],
                "tables": [],
                #: Rule 6: `(ref, body-line index)` for each `<!-- sub: … -->` marker.
                "subs": [],
            }
            pending_ref = None
            continue

        if CELL.match(line) or ROW.match(line) or DIVIDER.match(line):
            kind = "cell" if CELL.match(line) else ("row-divider" if DIVIDER.match(line) else "row")
            raise CorpusFormatError(
                f"line {index}: a `{kind}` annotation outside a table block. Open the block "
                "with `<!-- table` and its `cols:` field first — an annotation outside one "
                "has no table to belong to and would be dropped."
            )

        if COMMENT.match(line):
            attempt = annotation_attempt(line)
            if attempt:
                raise CorpusFormatError(
                    f"line {index}: malformed annotation — `{line.strip()}` starts like "
                    f"`{attempt}` but does not parse. A comment is either a known annotation "
                    "(`corpus`, `page`, `ref`, `table`, `row`, `row-divider`, `cell`) or a "
                    "reviewer's note; an annotation nobody parses is silently dropped, and a "
                    "dropped `cell` is a row that can never be quoted."
                )
            continue  # a reviewer's note, never text

        if line.lstrip().startswith("<!--"):
            raise CorpusFormatError(f"line {index}: malformed comment: {line!r}")

        if current is None:
            if line.strip():
                raise CorpusFormatError(
                    f"line {index} has text before any heading: {line!r}"
                )
            continue

        add_text(line, index)

    flush()
    if not sections:
        raise CorpusFormatError("the artefact contains no headings, so no sections")
    return CorpusDocument(
        doc_key=fields["doc_key"],
        source=fields["source"],
        sha256=fields["sha256"],
        generator=fields["generator"],
        sections=tuple(sections),
        blocks=tuple(blocks),
        extra={
            key: value
            for key, value in fields.items()
            if key not in REQUIRED_HEADER_FIELDS
        },
    )


def load_document(path: str | Path) -> CorpusDocument:
    """Load one artefact from disk. In: a `knowledge/corpus/*.md` path."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    document = parse_blocks(text)
    return CorpusDocument(
        doc_key=document.doc_key,
        source=document.source,
        sha256=document.sha256,
        generator=document.generator,
        sections=document.sections,
        blocks=document.blocks,
        path=path,
        extra=document.extra,
    )


def flat(text: str) -> str:
    """Exactly what `audit_citations` compares: whitespace-normalised text."""
    return " ".join((text or "").split())


__all__ = [
    "Block",
    "CORPUS_EDITS",
    "CorpusDocument",
    "CorpusFormatError",
    "CorpusEdit",
    "flat",
    "load_document",
    "parse_blocks",
]


@dataclass(frozen=True)
class CorpusEdit:
    """One reviewed correction, and the evidence that it was necessary.

    In:  `page` — the PDF page; `original` — the text the *PDF* produces there (the
         defact being repaired); `replacement` — what the artefact now says;
         `reason` — how the defect arose, in one sentence, so the generator can be
         improved rather than the symptom patched forever.
    Out: data consumed by the traceability test. `original` must be found on `page`, and
         `replacement` must be found in the artefact, which is what stops this table
         becoming a place to hide text nobody checked.
    """

    page: int
    original: str
    replacement: str
    reason: str
    #: `replace` (a correction), `drop` (furniture removed) or `move` (the same text at a
    #: new position). The distinction matters to the coverage test: a move changes no
    #: character, so counting it as a substitution would invent text.
    #:
    #: **`move` cannot be regenerated, and must not be used for one (2026-10-30).**
    #: `scripts/build_corpus.apply_review` is a text *substitution*: it has an `original` and a
    #: `replacement` and no notion of a source and a destination. The BPP's footnote-2 entry was
    #: a `move` for a day and applying it deleted `must be preferably composted` and reprinted
    #: `land available will not be allowed.` at the foot of page 4 — and no test failed, because
    #: the traceability test compares `flat()` strings and `flat` joins lines, so a corruption
    #: that reintroduces the line above reads as a faithful move. Express a move as **a lift and
    #: a place**: a `replace` that removes the text from where the extraction glued it, and a
    #: `replace` anchored on the text it belongs beside (`LANDSCAPE_TABLES_PRD` §12b.2).
    kind: str = "replace"


#: Reviewed corrections, per corpus document. **Every entry is a generator defect that
#: was found by reading the artefact.** Keeping them here rather than as comments in the
#: Markdown is deliberate: a comment cannot fail a test, and this table can.
CORPUS_EDITS: dict[str, tuple[CorpusEdit, ...]] = {
    "saoso": (
        CorpusEdit(
            page=25,
            original="fattening of chickens with more 2 than 25kg weight/m .",
            replacement="fattening of chickens with more than 25kg weight/m².",
            reason=(
                "The `²` of `m²` is drawn as a superscript, so `pdftotext` puts the digit "
                "on its own line *between* `more` and `than` and leaves the base line as "
                "`m .` — the sentence read `…with more / 2 / than 25kg weight/m .` and could "
                "not be quoted. Read from the page image: one sentence, `weight/m²`. The "
                "lone digit is the superscript, not a page stamp, so it is merged rather "
                "than dropped (`BugFixes/saoso_text_glyphs_and_boundaries.md` §2)."
            ),
        ),
        CorpusEdit(
            page=50,
            original="p u r c h a s e d",
            replacement="purchased",
            reason=(
                "A tracked (letterspaced) word in a heading run: the text layer emits one "
                "token per letter, so `purchased` matched nothing in search or retrieval. "
                "Read from the page image, the word is set in tracking, not spelled out "
                "(ibid. §4)."
            ),
        ),
        CorpusEdit(
            page=86,
            original="Other b o v i n e a n i m a l s less t h a n o n e year old",
            replacement="Other bovine animals less than one year old",
            reason=(
                "Two letterspaced runs inside one Appendix 6a row (`bovine animals`, "
                "`than one`). Recorded as one edit because both are on the same printed "
                "line and the same cell; `bovine` has to be findable, since the appendix "
                "is where a farmer looks up a stocking rate (ibid. §4–§5)."
            ),
        ),
    ),
    "bpp": (
        CorpusEdit(
            kind="drop",
            page=3,
            original="02",
            replacement="",
            reason=(
                "The printed page number is furniture. `-raw` puts it on its own line "
                "before the body and `-layout` glues it to the footnote's last line; "
                "either way it is not text."
            ),
        ),
        # Two edits, not one `move` (2026-10-30). A `move` says "the same characters at a new
        # position", and `apply_review` is a single text **substitution** — so the one `move`
        # entry this replaced silently deleted `must be preferably composted` and printed
        # `land available will not be allowed.` a second time, at the foot of page 4. Nothing
        # caught it: the traceability test asserts `flat(original)` on the page and
        # `flat(replacement)` in the artefact, and `flat` joins lines, so a corruption that
        # reintroduces a line from two lines above reads as a faithful move. The review's
        # decision is unchanged — the footnote belongs with the bullet that carries its
        # marker — but it now takes a lift and a place, so regeneration reproduces the
        # reviewed artefact instead of mangling it.
        CorpusEdit(
            page=4,
            original=(
                "must be preferably composted 2 Sustainable means: meeting the needs of "
                "the present without compromising the ability of future generations to "
                "meet their own needs; conserving an ecological balance by avoiding "
                "depletion or destruction of natural resources.(IFOAM: Organics "
                "International 3.0)"
            ),
            replacement="must be preferably composted",
            reason=(
                "`-raw` emits footnote 2 at the end of page 4, which is inside the "
                "manure sentence (`must be preferably composted` / footnote / `prior to "
                "application`), so the BPP's most-quoted sentence was unquotable. This "
                "lifts the footnote out; the next edit puts it back on its bullet."
            ),
        ),
        CorpusEdit(
            page=4,
            original="land available will not be allowed.",
            replacement=(
                "land available will not be allowed.\n"
                "2 Sustainable means: meeting the needs of the present without compromising "
                "the ability of future\n"
                "generations to meet their own needs; conserving an ecological balance by "
                "avoiding depletion or\n"
                "destruction of natural resources.(IFOAM: Organics International 3.0)"
            ),
            reason=(
                "The other half of the pair above: footnote 2 is printed at the foot of "
                "page 4 but belongs to the marker it follows on `a. Sustainable land "
                "management2`. Anchored on the bullet's own sentence, which occurs once "
                "on the page, so the insert cannot land in the manure rule instead."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=8,
            original="ii. Preventativemethods(disruption,",
            replacement="ii. Preventative methods (disruption,",
            reason=(
                "The PDF's text layer has no spaces in this line, so no extractor can "
                "recover them; read from the page, it is two words and a parenthesis."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=8,
            original=(
                "The Principle Of Health. The Principle Of Ecology. The Principle Of "
                "Fairness. The Principle Of Care."
            ),
            replacement="",
            reason=(
                "The brochure prints the four-principle strip on pages 1, 6, 8 and 10. "
                "The first occurrence (page 6) carries the content and sits at a "
                "paragraph boundary; the repeats interrupt numbered lists, so they are "
                "dropped rather than moved."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=10,
            original=(
                "The Principle Of Health. The Principle Of Ecology. The Principle Of "
                "Fairness. The Principle Of Care."
            ),
            replacement="",
            reason="The same repeated strip; see the page-8 entry.",
        ),
        CorpusEdit(
            kind="drop",
            page=5,
            original="\uf06e",
            replacement="",
            reason=(
                "A private-use glyph (U+F06E): the producer's Dingbats bullet before "
                "`Planting:`. Nothing in Unicode names it — pdftotext can emit only the "
                "code the embedded font assigns — so keeping it would put a character in "
                "the corpus that no reader can see, no search can match and no audit can "
                "quote. Only the glyph is dropped: `Planting:` is the list item it marks. "
                "It reached the artefact on 2026-10-27, because before `-enc UTF-8` the "
                "extraction dropped such glyphs silently and the artefact never held one."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=6,
            original="\uf06e",
            replacement="",
            reason="The second private-use bullet, the same shape; see the page-5 entry.",
        ),
    ),
}
