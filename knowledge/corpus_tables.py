"""The artefact's table block: `<!-- table` … `<!-- /table -->`, parsed as structure.

Split out of `knowledge/corpus.py` (CONTEXT_CUTS_PRD step 6). A table is a block **whose
structure is parsed, never recovered from text** (D73, rule 5 of the format): `<!-- table`
opens it with `cols:` and the optional D77 shape fields, `<!-- row: Label -->` starts a row,
`<!-- cell -->` starts a cell, `<!-- row-divider: … -->` labels the row beneath it, and
`<!-- /table -->` closes it.

**Why the block exists at all.** A GFM pipe table chunks as *one* chunk and blank lines
between rows change nothing (the chunker packs paragraphs), so a table written as prose keeps
all of its text and loses every boundary — and until 2026-10-30 `<!-- cell -->` was silently
dropped as a reviewer's note, with every other guard green. So an annotation that does not
parse **raises**, and a comment whose first word is a format word it misspells
(`cells`, `col:`) raises too: a reviewer's note is invisible afterwards, a lost cell is not.

`CorpusFormatError` is defined here rather than in `corpus.py` because this is the lowest
layer that raises it — leaving it there would make this module import the parser that imports
it. `corpus.py` re-exports it, so `from knowledge.corpus import CorpusFormatError` is unchanged.

The cells are *slices* of `section.text`, not copies: the offsets are computed once, by the
caller, from the body-line indices this class records.
"""

from __future__ import annotations

import re
from typing import Callable, Sequence

from knowledge.sections import (
    ParsedTable,
    ParsedTableRow,
    TableCell,
    TableRowDivider,
)


class CorpusFormatError(ValueError):
    """The artefact is malformed. Never swallowed: a silent default loses provenance."""


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
#: reviewed note the reader prints above the grid; four are D77's shape fields — `layout` (which
#: shape), `branch` (where the rows fork), `title` (one per row) and `fee_label` (one per fee box);
#: `extraction` is S3's datum (below). Every one is reviewed data: the renderer infers none of them.
TABLE_FIELD = re.compile(
    r"^\s*(cols|legend|layout|branch|title|fee_label|extraction|silence):\s*(.*?)\s*$"
)

#: The shapes the reader can draw (D77). `grid` is the default so every table written before D77
#: keeps the shape it had; `process` is the cards.
TABLE_LAYOUTS = ("grid", "process")

#: The extraction passes a block's cells can have been transcribed from, named as `pdftotext`'s
#: modes are (`knowledge/tests/page_fixtures.py`, whose `MODES` a test asserts equal to this).
#:
#: **Why this is a format field and not a command-line flag.** The landscape's reviewed tables pass
#: requirement 3 against `-table` and fail ten ways against `-layout`; the OPP's three-column fee
#: page is the other way round. A gate that defaults the pass is a gate reporting on paper it did not
#: read, so the datum travels on the artefact with the cells it describes (S3, requirement 1).
#:
#: The vocabulary is validated rather than free text: `extraction: tbael` must not read as "unknown
#: pass, judge it anyway", which is the class of silence this format exists to make loud.
EXTRACTION_MODES = ("layout", "raw", "table")

#: A letter-spaced run is at least this many single letters in a row (`b o v i n e` is 6,
#: `( S A O S O` is 5). The same threshold the emitter (`scripts/table_blocks.py`) and the row
#: reader (`scripts/table_reads.py`) use, for the same reason, kept here because both the emitter
#: and the harness must agree about what "the page letter-spaces this word" means.
SPACED_RUN = 3


def has_letter_spacing(text: str) -> bool:
    """Whether the page prints a run of single letters ('t h a n', 'b o v i n e') in this text.

    Appendix 6a prints its class column in tracking: the text layer emits one token per letter, so
    the corpus's quote (`Other bovine animals less than one year old`, a reviewed `CORPUS_EDITS`
    replacement) is not a substring of the printed line. Both the emitter (which slices the page)
    and the harness (which locates a cell on it) need the same narrow answer to "is this line
    letter-spaced?", and a second copy of the rule would be a second answer.
    """
    run = 0
    for token in text.split(" "):
        if len(token) == 1 and token.isalpha():
            run += 1
            if run >= SPACED_RUN:
                return True
        else:
            run = 0
    return False


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


class TableBlock:
    """One open `<!-- table … -->` block, and its state machine.

    The state is the raw dict the parser stores: `columns`, `fields`, `rows`, and the open
    `row`/`cell`. `close()` returns that dict for the section's `tables` list, exactly as the
    parser recorded it before this module existed.
    """

    def __init__(self) -> None:
        self.header = True
        self.fields: dict[str, object] = {}
        self.columns: tuple[str, ...] = ()
        self.rows: list[dict] = []
        self.row: dict | None = None
        self.cell: dict | None = None
        self.pending_dividers: list = []
        self.branch: int | None = None

    @classmethod
    def open(cls) -> "TableBlock":
        return cls()

    # -- the header --------------------------------------------------------------------

    def read_header_line(self, line: str, where: int) -> None:
        """One `key: value` line inside the header. Raises on a field it cannot accept."""
        field = TABLE_FIELD.match(line)
        if not field:
            raise CorpusFormatError(
                f"line {where}: a table header line that is not one of `cols:`, `legend:`, "
                f"`layout:`, `branch:`, `title:`, `fee_label:`, `extraction:`, `silence:` or "
                f"`-->`: {line!r}"
            )
        key = field.group(1)
        if key in self.fields:
            raise CorpusFormatError(
                f"line {where}: `{key}:` appears twice in one table header. The second "
                "would silently replace the first."
            )
        if key == "cols":
            value = tuple(part.strip() for part in field.group(2).split("|"))
            if not value or not all(value):
                raise CorpusFormatError(
                    f"line {where}: `cols:` names an empty column: {field.group(2)!r}. "
                    "Columns are `|`-separated, and a blank one would make every cell "
                    "beneath it unlabelled."
                )
        elif key == "layout":
            value = field.group(2)
            if value not in TABLE_LAYOUTS:
                raise CorpusFormatError(
                    f"line {where}: `layout: {value}` is not a shape the reader draws. "
                    f"Use one of: {', '.join(TABLE_LAYOUTS)}. An unknown shape would "
                    "render as whatever the template's fallback branch guessed."
                )
        elif key == "extraction":
            value = field.group(2)
            if value not in EXTRACTION_MODES:
                raise CorpusFormatError(
                    f"line {where}: `extraction: {value}` is not an extraction mode. Use one "
                    f"of: {', '.join(EXTRACTION_MODES)}. The mode is which rendering of the page "
                    "the cells were transcribed from, and the gate checks every cell against "
                    "that rendering — an unknown mode would be judged against a guess."
                )
        elif key in ("title", "fee_label"):
            value = tuple(part.strip() for part in field.group(2).split("|"))
            if not all(value):
                raise CorpusFormatError(
                    f"line {where}: `{key}:` has an empty entry: {field.group(2)!r}. "
                    f"The entries are `|`-separated, one per "
                    f"{'row' if key == 'title' else 'fee box'}, and a blank one would "
                    "render a heading with no words in it."
                )
        else:
            # `legend` and `branch`. `branch` is resolved when the table closes, because
            # until then there are no rows for it to point at.
            value = field.group(2)
        self.fields[key] = value

    def close_header(self, where: int) -> None:
        columns = self.fields.get("cols", ())
        if not columns:
            raise CorpusFormatError(
                f"line {where}: a `table` block with no `cols:` field. The column "
                "labels are what the reader prints above the grid and what tells a "
                "cell which column it belongs to."
            )
        self.columns = columns
        self.header = False

    # -- the body ----------------------------------------------------------------------

    def close_cell(self, where: int, body: list[str]) -> None:
        """Finish the open cell, trimming the blank lines that only space it out."""
        cell = self.cell
        if cell is None:
            return
        while cell["lines"] and not body[cell["lines"][0]].strip():
            cell["lines"].pop(0)
        while cell["lines"] and not body[cell["lines"][-1]].strip():
            cell["lines"].pop()
        cell["first"] = cell["lines"][0] if cell["lines"] else None
        cell["last"] = cell["lines"][-1] if cell["lines"] else None
        self.row["cells"].append(cell)
        self.cell = None

    def close_row(self, where: int, body: list[str]) -> None:
        if self.row is None:
            return
        self.close_cell(where, body)
        row = self.row
        columns = len(self.columns)
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
        self.rows.append(row)
        self.row = None

    def close(self, where: int, body: list[str]) -> dict:
        """Finish the block and return it in the shape the section stores."""
        self.close_row(where, body)
        if not self.rows:
            raise CorpusFormatError(
                f"line {where}: a `table` block with no rows. Its column labels would render "
                "as a table with nothing in it, and the page's text would be missing from the "
                "corpus entirely — which is the defect this block exists to prevent."
            )
        if self.pending_dividers:
            raise CorpusFormatError(
                f"line {where}: a `row-divider` after the table's last row. A divider "
                "qualifies the row beneath it, and there is none — the label would silently "
                "vanish."
            )
        if "branch" in self.fields:
            self.branch = branch_row(self.fields["branch"], self.rows, where)
        titles = self.fields.get("title", ())
        if titles and len(titles) != len(self.rows):
            raise CorpusFormatError(
                f"line {where}: `title:` names {len(titles)} titles for {len(self.rows)} rows. "
                "Titles are `|`-separated, one per row in printed order, or omitted entirely — "
                "a short list would silently shift every title onto the row above."
            )
        raw = {
            "header": self.header,
            "fields": self.fields,
            "columns": self.columns,
            "rows": self.rows,
            "row": self.row,
            "cell": self.cell,
            "pending_dividers": self.pending_dividers,
        }
        if self.branch is not None:
            raw["branch"] = self.branch
        return raw

    def add_divider(self, value: str, where: int, body: list[str]) -> None:
        self.close_cell(where, body)
        self.pending_dividers.append(row_divider(value))

    def open_row(
        self, where: int, label: str | None, page: int | None, body: list[str]
    ) -> None:
        self.close_row(where, body)
        self.row = {
            "label": (label or "").strip(),
            "page": page,
            "cells": [],
            # A divider is printed *between* rows and qualifies the one beneath it, so it is
            # collected while no row is open and claimed by the next `<!-- row: … -->`.
            "dividers": tuple(self.pending_dividers),
            "cursor": len(body),
        }
        self.pending_dividers = []

    def open_cell(self, where: int, body: list[str]) -> None:
        if self.row is None:
            raise CorpusFormatError(
                f"line {where}: a `cell` annotation before any row. A cell belongs to a "
                "row; outside one "
                "its text would become a chunk no column label points at."
            )
        self.close_cell(where, body)
        self.cell = {"lines": [], "pages": {}, "first": None, "last": None, "cursor": len(body)}

    def add_cell_line(self, index: int, printed: int | None = None) -> None:
        """Record the body-line index of a line the caller just appended, and its printed page."""
        self.cell["lines"].append(index)
        self.cell["pages"][index] = printed


def parsed_tables(
    raw_tables: Sequence[dict],
    char_offset: Callable[[int], int],
    lines_in_text: Sequence[str],
    text: str,
) -> tuple[ParsedTable, ...]:
    """Turn the recorded raw tables into the shapes a section carries.

    `char_offset` is the caller's body-line → character-offset function: the offsets belong to
    the section's text (heading included), so they cannot be computed here.
    """

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
        body = text[start:end]
        first = raw["lines"].index(raw["first"])
        pages = tuple(raw.get("pages", {}).get(index) for index in raw["lines"])
        return TableCell(body, start, end, pages[first : first + body.count("\n") + 1])

    return tuple(
        ParsedTable(
            columns=raw["columns"],
            legend=raw["fields"].get("legend", ""),
            silence=raw["fields"].get("silence", ""),
            extraction=raw["fields"].get("extraction", ""),
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
        for raw in raw_tables
    )
