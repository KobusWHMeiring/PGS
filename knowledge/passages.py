"""A passage's display layout: paragraphs, headings and lists, without changing a word.

`DocumentChunk.text` is the extracted page: the paper's line breaks, the paper's indentation as
literal spaces, and — for SAOSO, printed double-spaced — a blank line between every line. Rendered
raw, the hanging indent of a lettered condition collapses (HTML collapses runs of spaces), so
`a  Sufficient free movement…` reads as prose, and a wrapped sentence becomes a ladder of lines.

This module turns one chunk into **blocks** for the reader:

* `Paragraph` — wrapped lines joined, whitespace collapsed;
* `Heading` — the document's own heading (`1. DEFINITIONS`, `## INTRODUCTION` from the BPP
  artefact), kept as text, not as a page heading;
* `ListBlock` / `ListItem` — a real list, nested when the marker family changes at a greater indent.

**The transformation is display-only.** Nothing is written back; retrieval, chunking, embeddings,
anchors and the citation audit never see these blocks. The words, their order and their punctuation
are unchanged: `flatten(blocks)` reproduces the chunk's text (whitespace-normalised) and the guard in
`knowledge/tests/test_passages.py` asserts that over every chunk of the real SAOSO ingest.

The marker a reader sees (`a.`) is **presentation**: the corpus prints a bare `a`, so the period is
the browser's list marker (`::marker`), not a character added to the document. `ListItem.marker` keeps
what the page actually printed, so a future reviewed artefact that prints `a.` needs no change here.

Grouping rules, each measured on the shipped corpus rather than assumed (PRD §3):

1. **Sequence decides, not indentation.** `a, b, c` is one list even when the paper mis-indents it
   (`S5.6` prints its first item at column 8 and the rest at 0). A marker that does not continue the
   sequence starts a new list, which keeps `S2.1.4`'s two `a`-starting lists apart.
2. **A family change at a greater indent nests.** `S8.1` is `a` → `i.`/`ii.` → `b`; the OPP prints
   `1.`/`2.` then `a.`/`b.` then restarts at `1.`.
3. **A continuation belongs to the item above** while its indent is between the item's marker and its
   body column + 4, which keeps `pigs: … for poultry: …` inside `S5.1.3` item `f` and SAOSO's glossary
   definitions (body column 3, text at column 0) inside their item. A centred heading is far past
   that column and ends the list.
4. **A printed heading is not a list row.** A numeric marker on the chunk's first line, whose body is
   all capitals (or a short roman section title), is a heading. A *lettered* all-caps body (`a  ACB`)
   is still an item — SAOSO's glossary.
5. **Unrecognised shapes are paragraphs.** The formatter never raises and never drops text.

No Django, no `core` import (`build_principles.md` §I).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: A marker: a bullet, a number, a roman numeral, or a single letter, with the printed punctuation
#: that follows it and the gap before the body. The gap is what separates a marker from an article
#: (`a lot of things` is prose); a bare letter needs two spaces, because the corpus prints `a      `.
_MARKER = re.compile(
    r"^(?P<indent>[ \t]*)"
    r"(?P<open>\()?"
    r"(?P<marker>[•‣▪◦●*\-–—]|\d{1,3}|[ivxlcdmIVXLCDM]{1,7}|[A-Za-z])"
    r"(?P<punct>[.)])?"
    r"(?P<gap>[ \t]+)"
    r"(?P<body>\S.*)$"
)

#: The BPP artefact carries markdown heading levels (`## INTRODUCTION`). It is the only shape in the
#: corpus that this module removes, and `flatten()` reports the same text, so the guard accounts for it.
_HASH_HEADING = re.compile(r"^#{1,6}(?:[ \t]+|$)")

#: The printed bullet shapes the corpus actually holds. `•` is SAOSO's and the landscape's;
#: `●` is the OPP's — and it only appeared on 2026-10-27, when the extraction started asking
#: for `-enc UTF-8` and the 66 bullets it had been dropping outright came back
#: (`knowledge/extraction.py`). An unrecognised marker is not a disaster — the line renders
#: as a paragraph — but the OPP's lists would read as prose.
_BULLETS = "•‣▪◦●*-–—"
_ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
_TERMINAL = (".", ";", "?", "!")


@dataclass(frozen=True)
class Paragraph:
    """A run of prose, its hard wraps joined. `kind` exists so a template can branch on it.

    `segments` is filled by `knowledge.references.annotate()` for a page that links the document's
    own cross-references: a tuple of `Segment`s whose texts join back to `text`. Empty means "print
    the text", so nothing here depends on the reader.
    """

    text: str
    kind: str = "paragraph"
    segments: tuple = ()


@dataclass(frozen=True)
class Heading:
    """The document's own heading, as printed (`1. DEFINITIONS`). Not a page heading."""

    text: str
    kind: str = "heading"


@dataclass(frozen=True)
class Term:
    """A glossary term or a printed sub-heading (`ACB`, `General Principle`, `Buffer Zones`).

    A short standalone line followed by a longer one. Kept distinct from `Heading` so the page can
    set a term at body size above its definition, while a section title keeps the larger role.
    """

    text: str
    kind: str = "term"
    #: The id a glossary link lands on (`term-acb`), set by the reader for the glossary branch only.
    #: Empty elsewhere, so a term-shaped line in another branch is never a link target.
    anchor: str = ""


@dataclass(frozen=True)
class RowHeading:
    """A reviewed table row's substance cell (`Guano`, `Wood, bark, sawdust…`).

    Deliberately not a `Term`: a term is a glossary headword and a row heading is an entry in a
    table, and the two must not carry the same weight on the page (D70.1). It exists so a row with
    no condition still reads as an *entry* rather than as body text, which is what the appendix
    looked like before.
    """

    text: str
    kind: str = "row"


@dataclass(frozen=True)
class ListItem:
    """One printed list row: the marker as printed, its text, and any nested lists."""

    marker: str
    text: str
    children: tuple["Block", ...] = ()
    #: See `Paragraph.segments` — filled by the reader, empty in the corpus.
    segments: tuple = ()


@dataclass(frozen=True)
class ListBlock:
    """A printed list. `style` is a CSS `list-style-type`; `start` is a printed marker's value."""

    style: str
    start: int
    items: tuple[ListItem, ...]
    kind: str = "list"


Block = Paragraph | Heading | Term | RowHeading | ListBlock


@dataclass
class _Mark:
    """A parsed marker line, before grouping decides what it belongs to."""

    indent: int
    marker: str
    body: str
    style: str
    family: str
    ordinal: int | None
    text_column: int
    #: A bare letter with only one space before its body. SAOSO prints `m Dry stone walls;` inside a
    #: list that otherwise indents by fourteen columns, so the marker is real only when it continues
    #: an open lettered list; otherwise `a lot of things` would be read as a list.
    weak: bool = False


@dataclass
class _Item:
    marker: str
    lines: list[str]
    marker_indent: int
    text_column: int
    children: list[Block]

    def freeze(self) -> ListItem:
        return ListItem(
            marker=self.marker,
            text=_collapse(" ".join(self.lines)),
            children=tuple(self.children),
        )


@dataclass
class _OpenList:
    style: str
    family: str
    indent: int
    expected: int | None
    start: int
    items: list[_Item]

    @classmethod
    def of(cls, mark: _Mark) -> "_OpenList":
        return cls(
            style=mark.style,
            family=mark.family,
            indent=mark.indent,
            expected=None if mark.ordinal is None else mark.ordinal + 1,
            start=1 if mark.ordinal is None else mark.ordinal,
            items=[_item(mark)],
        )

    def add(self, mark: _Mark) -> None:
        self.items.append(_item(mark))
        self.expected = None if mark.ordinal is None else mark.ordinal + 1

    def freeze(self) -> ListBlock:
        return ListBlock(
            style=self.style,
            start=self.start,
            items=tuple(item.freeze() for item in self.items),
        )


def _item(mark: _Mark) -> _Item:
    return _Item(
        marker=mark.marker,
        lines=[mark.body],
        marker_indent=mark.indent,
        text_column=mark.text_column,
        children=[],
    )


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _is_caps(body: str) -> bool:
    return any(char.isalpha() for char in body) and not any(char.islower() for char in body)


def _roman(token: str) -> int | None:
    """A valid roman numeral, or None. Strict on purpose: `mix` is a word, not 1009."""
    if not token or len(token) > 12 or any(char not in _ROMAN_VALUES for char in token):
        return None
    total = 0
    previous = 0
    for char in reversed(token):
        value = _ROMAN_VALUES[char]
        if value < previous:
            total -= value
        else:
            total += value
            previous = value
    return total if _to_roman(total) == token else None


def _to_roman(value: int) -> str:
    if not 0 < value < 4000:
        return ""
    out: list[str] = []
    for amount, numeral in (
        (1000, "m"),
        (900, "cm"),
        (500, "d"),
        (400, "cd"),
        (100, "c"),
        (90, "xc"),
        (50, "l"),
        (40, "xl"),
        (10, "x"),
        (9, "ix"),
        (5, "v"),
        (4, "iv"),
        (1, "i"),
    ):
        while value >= amount:
            out.append(numeral)
            value -= amount
    return "".join(out)


def _mark(line: str) -> _Mark | None:
    """Parse one line as a list marker, or None when it is prose (or a near miss)."""
    match = _MARKER.match(line)
    if match is None:
        return None
    token = match.group("marker")
    opened = bool(match.group("open"))
    punct = match.group("punct") or ""
    gap = match.group("gap")
    indent = len(match.group("indent"))
    text_column = match.start("body")

    if opened and not punct:
        return None  # `(a text` is not a marker

    printed = ("(" if opened else "") + token + punct

    if token in _BULLETS:
        return _Mark(indent, printed, match.group("body"), "disc", "disc", None, text_column)

    if token.isdigit():
        if not punct:
            return None  # `5.2.2     …` is a printed clause number, not a list row
        value = int(token)
        return _Mark(indent, printed, match.group("body"), "decimal", "decimal", value, text_column)

    lower = token.lower()
    if len(token) > 1:
        if not punct:
            return None  # `mix  the compost` is a word
        value = _roman(lower)
        if value is None:
            return None
        style = "lower-roman" if token.islower() else "upper-roman"
        return _Mark(indent, printed, match.group("body"), style, "roman", value, text_column)

    if punct and lower in _ROMAN_VALUES:
        value = _roman(lower)
        if value is not None:
            style = "lower-roman" if token.islower() else "upper-roman"
            return _Mark(indent, printed, match.group("body"), style, "roman", value, text_column)

    value = ord(lower) - ord("a") + 1
    if not 1 <= value <= 26:
        return None
    style = "lower-alpha" if token.islower() else "upper-alpha"
    return _Mark(
        indent,
        printed,
        match.group("body"),
        style,
        "alpha",
        value,
        text_column,
        weak=not punct and len(gap) < 2,
    )


def _is_term(stripped: str, next_line: str, indent: int) -> bool:
    """A glossary term or a printed sub-heading: short, standalone, followed by prose.

    `ACB` / `General Principle` / `Buffer Zones` all print as one short line before the text they
    introduce. A centred line is not a term — it is one of the document's labels, handled as a
    heading when its paragraph flushes. A line that ends a sentence is prose, however short.
    """
    if indent >= 10:
        return False
    words = stripped.split()
    if not 1 <= len(words) <= 8 or len(stripped) > 70:
        return False
    if not stripped[:1].isupper() or stripped.endswith(_TERMINAL):
        return False
    if not next_line or len(next_line) < 30 or not next_line[:1].isupper():
        return False
    following = _mark(next_line)
    return following is None or following.weak


def _is_opener(mark: _Mark, *, first: bool) -> bool:
    """A numeric marker on the chunk's first line that titles the section, not a list row.

    `1. DEFINITIONS` and `21. WINE MAKING` are headings because their bodies are capitals; the OPP's
    `I. Membership procedure` and `IV. Assessment Process:` are short roman titles. A title is
    allowed a trailing colon, because the OPP prints one.
    """
    if not first:
        return False
    if mark.family == "decimal":
        return _is_caps(mark.body)
    if mark.family == "roman":
        return _is_caps(mark.body) or (
            len(mark.body.split()) <= 8 and not mark.body.endswith(_TERMINAL)
        )
    return False


def _continues(level: _OpenList, mark: _Mark) -> bool:
    """Does this marker continue the open list, or start/nest another one?"""
    if level.family == mark.family:
        return level.expected is None or mark.ordinal == level.expected
    # `h` followed by `i.` is an alphabetic row the paper happens to punctuate.
    return (
        level.family == "alpha"
        and mark.family == "roman"
        and mark.ordinal == level.expected
    )


def passage_blocks(text: str) -> tuple[Block, ...]:
    """In: one chunk's stored text. Out: the blocks the reader renders.

    In:  `text` — `DocumentChunk.text`, verbatim from the extraction.
    Out: a tuple of `Paragraph` / `Heading` / `ListBlock`; empty for an empty chunk.
    Side effects: none.
    Fails: never deliberately. An unrecognised shape is a paragraph, never an exception — the reader
        has no error surface for a passage, and losing text would be worse than losing structure.
    """
    if not text or not text.strip():
        return ()

    blocks: list[Block] = []
    stack: list[_OpenList] = []
    paragraph: list[str] = []
    paragraph_indent: int | None = None
    seen_first = False

    def flush_paragraph() -> None:
        nonlocal paragraph_indent
        if paragraph:
            text = _collapse(" ".join(paragraph))
            # A single centred line is the document's own heading, not prose: SAOSO centres
            # `Regional or other exception` and `SOUTH AFRICAN specific` in the middle of a
            # clause, and they read as headings on the paper. A line indented that far cannot be
            # body text in a single column.
            centred = (
                paragraph_indent is not None
                and paragraph_indent >= 10
                and len(text) <= 100
                and not text.endswith(_TERMINAL)
            )
            blocks.append(Heading(text) if centred else Paragraph(text))
            paragraph.clear()
        paragraph_indent = None

    def place(mark: _Mark) -> None:
        """Put a marker line on the right list: continue, nest, or start a new one.

        Popping rather than closing everything is what lets `S8.1`'s `b` return to its outer
        lettered list after the nested `i.`/`ii.` list closes, and what makes the OPP's restarted
        `1.` start a new list at the top level instead of inside the previous one.
        """
        while stack:
            top = stack[-1]
            if _continues(top, mark):
                top.add(mark)
                return
            if top.items and mark.indent > top.indent:
                stack.append(_OpenList.of(mark))
                return
            close_top()
        stack.append(_OpenList.of(mark))

    def close_top() -> None:
        opened = stack.pop()
        frozen = opened.freeze()
        if stack:
            stack[-1].items[-1].children.append(frozen)
        else:
            blocks.append(frozen)

    def close_lists() -> None:
        while stack:
            close_top()

    lines = [raw.rstrip() for raw in text.splitlines() if raw.strip()]
    for index, line in enumerate(lines):
        stripped = line.strip()
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""

        hash_heading = _HASH_HEADING.match(stripped)
        if hash_heading:
            close_lists()
            flush_paragraph()
            title = stripped[hash_heading.end() :].strip()
            if title:
                blocks.append(Heading(_collapse(title)))
            continue

        mark = _mark(line)
        if mark is not None and mark.weak and not (
            stack and stack[-1].family == "alpha" and _continues(stack[-1], mark)
        ):
            mark = None
        first = not seen_first
        seen_first = True

        if mark is not None and _is_opener(mark, first=first):
            close_lists()
            flush_paragraph()
            blocks.append(Heading(_collapse(line)))
            continue

        if mark is not None:
            flush_paragraph()
            place(mark)
            continue

        indent = len(line) - len(line.lstrip(" \t"))
        if stack:
            item = stack[-1].items[-1]
            within = item.marker_indent <= indent <= item.text_column + 4
            # A line at (or left of) the marker continues the item only while the item has not
            # closed its sentence: SAOSO's glossary is `a  ACB` + the definition at column 0, but
            # `b  Two;` followed by a new sentence at column 0 is the prose after the list.
            open_sentence = not _collapse(" ".join(item.lines)).endswith(_TERMINAL)
            if within and (indent > item.marker_indent or open_sentence or stripped[:1].islower()):
                item.lines.append(stripped)
                continue
            close_lists()
        if _is_term(stripped, next_line, indent):
            flush_paragraph()
            blocks.append(Term(stripped))
            continue
        if paragraph and paragraph_indent is not None and abs(indent - paragraph_indent) >= 6:
            # A centred line (`South African specific`) is its own block, not the tail of the
            # paragraph before it.
            flush_paragraph()
        if not paragraph:
            paragraph_indent = indent
        paragraph.append(stripped)

    close_lists()
    flush_paragraph()
    return tuple(blocks)


def row_blocks(text: str) -> tuple[Block, ...]:
    """In: one reviewed row's stored text (`TableRow.text`). Out: the blocks the reader renders.

    In:  `text` — the substance cell, then the condition, its paragraphs separated by a blank line
         (that is how `TableRow.text` is written, and the double-spaced-body rule that governs
         `passage_blocks` must not apply here: a curated row's paragraph breaks are deliberate).
    Out: `RowHeading(substance)`, then one `Paragraph` per non-empty condition paragraph; `()` for
         empty input; **no paragraph at all** when the condition cell is empty, because the paper's
         silence is not a condition (the prompt's rule, and the reason this function exists).
    Side effects: none.
    Fails: never. `passage_blocks()` is not consulted and its behaviour is unchanged.
    """
    lines = [line.strip() for line in (text or "").splitlines()]
    if not any(lines):
        return ()

    first = lines.index(next(line for line in lines if line))
    blocks: list[Block] = [RowHeading(_collapse(lines[first]))]
    paragraph: list[str] = []
    for line in lines[first + 1 :]:
        if line:
            paragraph.append(line)
            continue
        if paragraph:
            blocks.append(Paragraph(_collapse(" ".join(paragraph))))
            paragraph = []
    if paragraph:
        blocks.append(Paragraph(_collapse(" ".join(paragraph))))
    return tuple(blocks)


def flatten(blocks: tuple[Block, ...] | list[Block]) -> str:
    """Out: the blocks' text in document order, markers included. The lossless check.

    A marker is stored apart from its item's text so a template can render it as a list marker;
    this puts it back. Paragraphs and headings contribute their text. Nested lists recurse.
    """
    parts: list[str] = []
    for block in blocks:
        if block.kind == "list":
            for item in block.items:
                parts.append(item.marker)
                if item.text:
                    parts.append(item.text)
                parts.append(flatten(item.children))
        elif block.text:
            parts.append(block.text)
    return " ".join(part for part in parts if part)


__all__ = [
    "Block",
    "Heading",
    "ListBlock",
    "ListItem",
    "Paragraph",
    "RowHeading",
    "Term",
    "flatten",
    "passage_blocks",
    "row_blocks",
]
