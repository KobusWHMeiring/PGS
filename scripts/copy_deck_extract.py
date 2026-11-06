"""The reading half of `copy_deck.py`: template text in, rows with exact source spans out.

Split out on 2026-11-06. `copy_deck.py` was 32 KB and `build_principles.md` section II caps a
source file at 30 KB - `scripts/context.py --check`, step 1 of `scripts/verify.sh`, had been
red on it since the tool was written, so `verify.sh` could not be quoted green from a tree
holding it. The seam is a real one: everything here reads a string and writes nothing, while
`--apply`'s guarantees (which region is replaced, and the refusal of a stale `old:`) all live
in the other half.

**`ROOT` is deliberately not here.** It belongs to the caller. `copy_deck_selftest.py`
monkeypatches `copy_deck.ROOT` to a throwaway tree holding a copy of the templates, and a
second `ROOT` in this module would be the one that read the real ones.

Nothing here decides whether a sentence is true, and nothing here knows what a page means.
`template_rows_from()` takes the source as a string for that reason: it is testable without a
filesystem, and the selftest runs its properties against a temp copy of the site.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

#: Inline elements never break a run of prose: a `<strong>` inside a sentence is still one
#: sentence to rewrite. Anything not listed here is a block boundary.
INLINE = frozenset({
    "a", "abbr", "b", "bdi", "br", "cite", "code", "data", "em", "i", "kbd", "mark",
    "q", "s", "samp", "small", "span", "strong", "sub", "sup", "time", "u", "var", "wbr",
})

#: Raw-text elements whose contents are not prose.
OPAQUE = frozenset({"script", "style", "svg", "template"})

VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
                  "meta", "param", "source", "track", "wbr"})

#: A class on the element that owns the run, matching one of these, makes it `locked`.
LOCKED_CLASSES = re.compile(r"\b(cite|pill|step__label|step__num|footer__chip|footer__name)\b")

#: Runs that are **quotations from a named source**, keyed by template path suffix and the
#: class their container carries. A rewrite of one is a misquotation of a document, not a
#: style improvement, so `--apply` refuses them whatever a writer asks for.
#:
#: This list is asserted by hand from the `{% comment %}` in each file, and it is the one thing
#: the extractor cannot infer: a quotation looks exactly like prose on the page.
#: * `_element_cards.html` - DESIGN §7.4 requires these six definitions **verbatim** from
#:   `pgs_docs/PGS Certification landscape_Final.pdf` p2, which also supplies the titles.
#: * `home.html` - the IFOAM-Organics International definition and its attribution line.
QUOTED: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("sections/_element_cards.html", ("element-card__title", "element-card__body")),
    ("home.html", ("quote__text", "quote__source")),
)

#: Classes whose text is domain data rather than prose: the fee schedule's band names and
#: money cells come from OPP §2.3, and they change in the OPP, not in a rewrite.
DATA_CLASSES = re.compile(r"\b(fee-table__|fee-band|band__)")

#: A `{{ ... }}` expression inside the run. Visible in the deck, but not auto-applied.
EXPRESSION = re.compile(r"\{\{.*?\}\}", re.S)

#: A newline, named so a diff helper is not written as a string literal inside a string literal.
NL = "\n"

#: A run that is nothing but one expression renders a string defined in PAGES, which has
#: its own row in `Page metadata`. Editing it here would edit a placeholder.
PURE_EXPRESSION = re.compile(r"^\{\{[^{}]*\}\}$")

COMMENT_BLOCK = re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.S)
COMMENT_INLINE = re.compile(r"\{#.*?#\}", re.S)
STATEMENT_TAG = re.compile(r"\{%.*?%\}", re.S)


@dataclass
class Row:
    id: str = ""
    group: str = ""
    also: list[str] = field(default_factory=list)
    label: str = ""
    source: str = ""
    lines: tuple[int, int] = (0, 0)
    cols: tuple[int, int] = (0, 0)
    mode: str = "auto"
    text: str = ""
    note: str = ""
    py_field: str = ""  # set for rows read from PAGES in _public.py
    new: str = ""


# ------------------------------------------------------------------------ extraction


def _blank(m: re.Match[str]) -> str:
    """Replace a match with spaces, keeping every newline so line numbers hold."""
    return re.sub(r"[^\n]", " ", m.group(0))


def _prepare(src: str) -> str:
    """Source with comments and `{% %}` statements blanked, `{{ }}` expressions kept.

    Keeping expressions is deliberate: the deck should show `{{ fee }}` where a number
    lands, and a run containing one is `manual` rather than silently mangled.
    """
    src = COMMENT_BLOCK.sub(_blank, src)
    src = COMMENT_INLINE.sub(_blank, src)
    return STATEMENT_TAG.sub(_blank, src)


def _unescape(text: str) -> str:
    return html.unescape(text)


class _Collector(HTMLParser):
    """Collect contiguous prose runs with exact source line/column spans."""

    def __init__(self, fed: str, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.fed = fed
        self.source = source
        self.rows: list[Row] = []
        self.opaque = 0
        self.stack: list[tuple[str, str]] = []  # (tag, class)
        self.locked_at: int | None = None
        self.parts: list[str] = []
        self.tag_pending = False  # an inline tag since the last text, so a swap would eat it
        self.broken = False  # markup strictly inside the run: not safe to swap as text
        self.start = (0, 0)
        self.end = (0, 0)

    # -- run bookkeeping ---------------------------------------------------
    @staticmethod
    def _advance(pos: tuple[int, int], s: str) -> tuple[int, int]:
        """Move a (line, col) position along `s`, honouring any newlines in it."""
        line, col = pos
        nl = s.count("\n")
        return (line + nl, len(s) - s.rfind("\n") - 1) if nl else (line, col + len(s))

    def _is_quoted(self) -> bool:
        """True when this run is a verbatim quotation, not prose of our own."""
        label = self._label()
        for suffix, classes in QUOTED:
            if self.source.endswith(suffix) and any(c in label for c in classes):
                return True
        return False

    def _label(self) -> str:
        for tag, cls in reversed(self.stack):
            if cls:
                return f"{tag}.{cls.split()[0]}"
            if tag in ("h1", "h2", "h3", "h4", "p", "li", "blockquote"):
                return tag
        return "prose"

    def _flush(self) -> None:
        if not self.parts:
            return
        raw = "".join(self.parts)
        self.parts = []
        broken, self.broken, self.tag_pending = self.broken, False, False
        core = raw.strip()
        self.start = self._advance(self.start, raw[:len(raw) - len(raw.lstrip())])
        self.end = self._advance(self.start, core)
        text = _unescape(re.sub(r"\s+", " ", core))
        if len(text) < 2 or not re.search(r"[A-Za-z]", text):
            return
        at_start, at_end = self.start, self.end

        if self.locked_at is not None:
            mode = "locked"
        elif DATA_CLASSES.search(" ".join(c for _, c in self.stack)):
            mode = "locked"
        elif self._is_quoted():
            mode = "locked"
        elif PURE_EXPRESSION.match(text):
            # the editable string is the PAGES row, not this placeholder
            mode = "locked"
        elif EXPRESSION.search(raw):
            mode = "manual"
        elif broken:
            mode = "manual"
        else:
            mode = "auto"

        self.rows.append(Row(
            source=self.source,
            lines=(at_start[0], at_end[0]),
            cols=(at_start[1], at_end[1]),
            mode=mode,
            text=text,
            label=self._label(),
            note=("renders a PAGES string - edit it under Page metadata"
                  if PURE_EXPRESSION.match(text) else
                  "a verbatim quotation - do not rewrite, it is a document's own words"
                  if self._is_quoted() else
                  "carries a {{ }} expression" if EXPRESSION.search(raw) else
                  "has inline markup" if broken else ""),
        ))

    def _touch(self, chunk: str) -> None:
        line, col = self.getpos()
        if not self.parts:
            self.start = (line, col)
        elif self.tag_pending:
            self.broken = True
        self.tag_pending = False
        self.end = self._advance((line, col), chunk)
        self.parts.append(chunk)

    # -- HTMLParser hooks --------------------------------------------------
    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in OPAQUE:
            self._flush()
            self.opaque += 1
            return
        if self.opaque:
            return
        cls = dict(attrs).get("class") or ""
        if tag in VOID:
            if tag in INLINE:
                self.tag_pending = True
            else:
                self._flush()
            return
        if tag in INLINE:
            if LOCKED_CLASSES.search(cls):
                self._flush()
                if self.locked_at is None:
                    self.locked_at = len(self.stack)
            elif cls:
                # A classed inline element - a styled span, a button-looking link, a chip -
                # is a leaf with its own text, not part of the sentence around it. Break
                # there so `--apply` can rewrite the leaf without touching its wrapper.
                self._flush()
            else:
                self.tag_pending = True
        else:
            self._flush()
        self.stack.append((tag, cls))

    def handle_startendtag(self, tag: str, attrs) -> None:
        if self.opaque:
            return
        if tag in INLINE:
            self.tag_pending = True
        else:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in OPAQUE:
            self.opaque = max(0, self.opaque - 1)
            return
        if self.opaque:
            return
        if tag in INLINE:
            if self.locked_at is not None and len(self.stack) == self.locked_at + 1:
                self._flush()
                self.locked_at = None
            elif self.stack and self.stack[-1][0] == tag and self.stack[-1][1]:
                self._flush()
            else:
                self.tag_pending = True
        else:
            self._flush()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data: str) -> None:
        if not self.opaque and data.strip():
            self._touch(data)

    def handle_entityref(self, name: str) -> None:
        if not self.opaque:
            self._touch(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.opaque:
            self._touch(f"&#{name};")


def template_rows_from(src: str, name: str) -> list[Row]:
    collector = _Collector(_prepare(src), name)
    collector.feed(collector.fed)
    collector.close()
    collector._flush()
    return collector.rows
