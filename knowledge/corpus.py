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

from knowledge.corpus_edits import CORPUS_EDITS, CorpusEdit
from knowledge.corpus_tables import (
    CELL,
    DIVIDER,
    ROW,
    TABLE_CLOSE,
    TABLE_OPEN,
    CorpusFormatError,
    TableBlock,
    parsed_tables,
)
from knowledge.sections import ParsedSection, any_level_end, slug


#: `<!-- page: 12 printed: 11 -->` — PDF page and the number the document prints.
PAGE = re.compile(r"^<!--\s*page:\s*(\d+)\s+printed:\s*(\d+|none)\s*-->\s*$")

#: `<!-- ref: S20.1.1 -->` — the citation for the heading that follows.
REF = re.compile(r"^<!--\s*ref:\s*(\S.*?)\s*-->\s*$")

#: `<!-- sub: 4.5(2)(c) -->` — a sub-clause printed *inside* a section, opening at the next text
#: line. See rule 6: the OPP's items are the case, and dropping them costs 24 citable addresses.
SUB = re.compile(r"^<!--\s*sub:\s*(\S.*?)\s*-->\s*$")

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
    table: TableBlock | None = None

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

        tables = parsed_tables(current["tables"], char_offset, lines_in_text, text)

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
            if table is not None and table.header:
                raise CorpusFormatError(
                    f"line {index}: a page marker inside a table's header. The header is a list "
                    "of `key: value` fields; a page marker there was meant for a row."
                )
            page = int(marker.group(1))
            printed = None if marker.group(2) == "none" else int(marker.group(2))
            continue

        if table is not None and table.header:
            if HEADER_CLOSE.match(line):
                table.close_header(index)
                continue
            table.read_header_line(line, index)
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
            table = TableBlock.open()
            continue

        if TABLE_CLOSE.match(line):
            if table is None:
                raise CorpusFormatError(
                    f"line {index}: `<!-- /table -->` without an open table. A close with no "
                    "open is a table whose rows the reviewer wrote but whose header is "
                    "missing — the rows would be silently read as prose."
                )
            current["tables"].append(table.close(index, current["body"]))
            table = None
            continue

        if table is not None:
            divider = DIVIDER.match(line)
            if divider:
                table.add_divider(divider.group(1), index, current["body"])
                continue
            row = ROW.match(line)
            if row:
                table.open_row(index, row.group(1), printed, current["body"])
                continue
            if CELL.match(line):
                table.open_cell(index, current["body"])
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
            if table.cell is None:
                if line.strip():
                    raise CorpusFormatError(
                        f"line {index}: text inside a table block but outside any `cell`: "
                        f"{line[:60]!r}. A cell is delimited by `<!-- cell -->`; text with no "
                        "cell has no column, so no row could quote it."
                    )
                continue  # a blank line between rows, for the reviewer's eye only
            add_text(line, index)
            table.add_cell_line(len(current["body"]) - 1)
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
