"""The document's own cross-references, resolved to the tree — or left as text.

A standards document cites itself constantly: `Section B – 5 Animal Husbandry 5.3, 5.5, 5.6`, `See
Appendix 6 Minimum Surface Areas Indoors and Outdoors`, `Appendices 2`. On the reader those were dead
text; this module turns each one into a target, and — the important half — leaves it alone when it
cannot.

Three rules, each measured on the shipped SAOSO (`READER_STRUCTURE_PRD` §1.3, §4.2) rather than
invented:

1. **A target is a branch that exists.** The index is built from `knowledge.concordance`, so a link
   can only point at a branch the page renders. `Appendix 5` in the BPP and `Appendix 9` in the
   certification landscape name branches neither document has, and therefore produce no links at all
   — the correct behaviour, and the negative control.
2. **A part letter is data.** `Section A – 2.3` is Part A's clause 2.3, which the corpus does not
   hold; a naive `S<n>` mapping would send it to Section 2 (*Organic Ecosystems*), a different part
   entirely. The part comes from the printed TOC — `StandardDocument.toc` rows carry `part` beside
   `label` — and a Part A reference goes to the page's missing-sections note. A document with **no**
   TOC has no parts, so an unqualified `Section n` there is undecidable and stays text.
3. **Segments, not markup.** A reference becomes a `Segment` (plain text, or an anchor plus a
   fragment). Nothing here builds a URL: `knowledge` knows branches, not routes
   (`build_principles.md` §I), so the template does `?section=…` from the anchor it is given.

`segments_for()` is lossless by construction — `"".join(s.text …)` is the string it was handed — which
is what lets the reader add targets without ever changing the document's words.

No `core` import.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from knowledge.concordance import ConcordanceSection, _match_key, build_concordance
from knowledge.passages import Block, ListBlock, Paragraph

if TYPE_CHECKING:  # pragma: no cover - typing only
    from knowledge.glossary import GlossaryEntry
    from knowledge.models import StandardDocument

#: Where a reference to a printed section the corpus does not hold points. The reader gives the
#: note that names those sections this `id`, so the link explains itself instead of guessing.
MISSING_ANCHOR = "not-in-corpus"

#: `Section B – 5`, `Section B Appendix 6b` (no number, so no match), `Section A – 2.3`.
#: The separator is whatever the paper prints — an en dash today, a hyphen in the OPP, a colon in a
#: reprint — so it is a class of punctuation rather than a literal.
_SECTION_WITH_PART = re.compile(
    r"\bSection\s+(?P<part>[A-Z])\s*(?:[^\w\s]{1,3}\s*)?(?P<number>\d{1,2}(?:\.\d+)*)"
)

#: `Section 4.6.2`, `section 5.7`, `Section 22 Labelling` (the label words stay text).
_SECTION_BARE = re.compile(r"\bSection\s+(?P<number>\d{1,2}(?:\.\d+)*)", re.IGNORECASE)

#: `Appendix 2`, `Appendices 2`, `Appendix 6b`, `Appendix 6 Minimum Surface Areas Indoors and…`
_APPENDIX = re.compile(
    r"\bAppendi(?:x|ces)\s+(?P<number>\d{1,2})(?P<letter>[a-z])?(?:\s+(?P<words>[A-Z][^.;:\n]{0,60}))?"
)


@dataclass(frozen=True)
class Target:
    """A branch a reference can point at: its key, its anchor in the tree, and its printed title."""

    key: str
    anchor: str
    title: str


@dataclass(frozen=True)
class Match:
    """One reference the document printed, resolved or not.

    `branch` empty and `fragment` empty means *no target* — the words stay text. `title` may still
    carry an explanation for a reader (bare `Appendix 4` names both its tables).
    """

    start: int
    end: int
    text: str
    branch: str = ""
    fragment: str = ""
    title: str = ""


@dataclass(frozen=True)
class Segment:
    """A run of a paragraph: the document's words, and — when they name something — where to go."""

    text: str
    branch: str = ""
    fragment: str = ""
    title: str = ""


@dataclass(frozen=True)
class ReferenceIndex:
    """What the document says about itself: its branches, the part each belongs to, and which parts
    it prints at all.

    `printed_parts` is the TOC's parts, kept apart from the parts the branches carry: a Part A
    reference has a real target (the page's missing-sections note) precisely because Part A is
    printed and *not* held, and the two sets differ only there.
    """

    branches: Mapping[str, Target]
    parts: Mapping[str, str | None]
    printed_parts: frozenset[str] = frozenset()

    def target(self, key: str) -> Target | None:
        return self.branches.get(key)


def _toc_parts(document: "StandardDocument") -> dict[str, str]:
    """`{label without its section prefix: part}` from the printed TOC (`5` → `B`)."""
    parts: dict[str, str] = {}
    for entry in document.toc or []:
        label = (entry.get("label") or "").strip()
        part = entry.get("part")
        if label and part:
            parts[_match_key(label)] = part
    return parts


def build_reference_index(
    document: "StandardDocument", sections: Sequence["ConcordanceSection"] | None = None
) -> ReferenceIndex:
    """In: a document. Out: its branches and their parts. One query, via the concordance.

    In:  the document (its chunks and its stored `toc`); `sections` — the tree, when the caller has
         already built it, so the reader does not pay for a second `reading_chunks()` query.
    Out: `ReferenceIndex` — every rendered branch by key, and the printed part each belongs to.
         A reserved row (the printed `10 to 19`) is not a target: it has no text.
    Side effects: one query for the chunks, and none when `sections` is given.
    Fails: never. A document with no TOC simply has no parts.
    """
    if sections is None:
        sections = build_concordance(document).sections
    branches = {
        section.key: Target(key=section.key, anchor=section.anchor, title=section.title)
        for section in sections
        if not section.reserved
    }
    printed = _toc_parts(document)
    parts = {key: printed.get(_match_key(key)) for key in branches}
    return ReferenceIndex(
        branches=branches,
        parts=parts,
        printed_parts=frozenset(
            entry["part"] for entry in document.toc or [] if entry.get("part")
        ),
    )


def _number_branch(number: str) -> str:
    """`5.3` → `S5`: a section reference names a section, and its sub-clauses are inside it."""
    return f"S{number.split('.', 1)[0]}"


def _resolve_section(
    index: ReferenceIndex, *, part: str | None, number: str, open_branch: str
) -> tuple[str, str, str]:
    """Out: `(branch, fragment, title)` — all empty when the reference has no honest target."""
    if part is None:
        return "", "", ""
    key = _number_branch(number)
    target = index.target(key)
    if target is not None and index.parts.get(key) == part:
        if key == open_branch:
            return "", "", ""
        return target.anchor, target.anchor, ""
    # A part this document prints and the corpus does not hold (Part A today). The reference is
    # real; the target is the page's own statement about what is missing — never another part.
    held = {value for value in index.parts.values() if value}
    if part not in held and part in index.printed_parts:
        return "", MISSING_ANCHOR, f"Section {part} is printed and not in this corpus"
    return "", "", ""


def _appendix_candidates(index: ReferenceIndex, number: str) -> list[Target]:
    """Every branch that answers to `Appendix <number>`: `Appendix 2`, `Appendix 6a` and `6b`."""
    head = f"Appendix {number}"
    return [
        target
        for key, target in index.branches.items()
        if key == head or key.startswith(f"{head} ") or key.startswith(f"{head}.")
        or re.fullmatch(rf"{re.escape(head)}[a-z]", key)
    ]


def _appendix_by_words(candidates: list[Target], words: list[str]) -> tuple[Target, int] | None:
    """The candidate whose printed title contains the words the paper put after the number."""
    for count in range(len(words), 0, -1):
        phrase = " ".join(words[:count])
        titled = [target for target in candidates if phrase.lower() in target.title.lower()]
        if len(titled) == 1:
            return titled[0], count
        if len(titled) > 1:
            return None
    return None


def _resolve_appendix(
    index: ReferenceIndex,
    *,
    number: str,
    letter: str,
    words: list[str],
    open_branch: str,
) -> tuple[str, str, str, int]:
    """Out: `(branch, fragment, title, words_consumed)`."""
    if letter:
        candidates = [t for t in _appendix_candidates(index, number) if t.key.endswith(letter)]
    else:
        candidates = _appendix_candidates(index, number)

    chosen: Target | None = None
    consumed = 0
    if letter:
        chosen = candidates[0] if len(candidates) == 1 else None
    elif len(candidates) == 1:
        chosen = candidates[0]
    elif words:
        by_words = _appendix_by_words(candidates, words)
        if by_words is not None:
            chosen, consumed = by_words

    if chosen is not None:
        if chosen.key == open_branch:
            return "", "", "", consumed
        return chosen.anchor, chosen.anchor, "", consumed

    if candidates and not letter:
        printed = f"Appendix {number}"
        titles = "; ".join(target.title for target in candidates)
        return "", "", f"{printed} is printed in parts: {titles}", consumed
    return "", "", "", consumed


def matches(
    text: str,
    index: ReferenceIndex,
    *,
    open_branch: str = "",
    terms: Mapping[str, "GlossaryEntry"] | None = None,
    seen: set[str] | None = None,
) -> list[Match]:
    """In: a string, an index. Out: every reference it contains, in order, resolved or not.

    In:  `text` — one block's text (already whitespace-collapsed by the layout); `open_branch` — the
         branch key the passage is printed in, which is what makes an unqualified `Section n`
         decidable and what suppresses a link to the page you are already on; `terms` — the
         glossary, when the caller wants defined words matched too; `seen` — terms already linked,
         so a caller can hold the one-link-per-passage rule.
    Out: `Match` rows sorted by `start`, never overlapping. A row with an empty `branch` and
         `fragment` is still a match — it is how the inventory of "9 mentions that cannot be
         decided" is countable.
    Side effects: adds linked terms to `seen` when given.
    Fails: never.
    """
    found: list[Match] = []
    position = 0
    while position < len(text):
        candidates = [
            (pattern.search(text, position), priority)
            for priority, pattern in enumerate(
                (_SECTION_WITH_PART, _APPENDIX, _SECTION_BARE)
            )
        ]
        candidates = [(match, priority) for match, priority in candidates if match is not None]
        if not candidates:
            break
        match, priority = min(candidates, key=lambda pair: (pair[0].start(), pair[1]))
        end = match.end()

        if priority == 0:
            part = match.group("part")
            branch, fragment, title = _resolve_section(
                index, part=part, number=match.group("number"), open_branch=open_branch
            )
            found.append(Match(match.start(), end, match.group(0), branch, fragment, title))
        elif priority == 1:
            words = (match.group("words") or "").split()
            branch, fragment, title, consumed = _resolve_appendix(
                index,
                number=match.group("number"),
                letter=match.group("letter") or "",
                words=words,
                open_branch=open_branch,
            )
            if consumed:
                end = match.start("words") + len(" ".join(words[:consumed]))
            found.append(Match(match.start(), end, text[match.start() : end], branch, fragment, title))
        else:
            part = index.parts.get(open_branch)
            branch, fragment, title = _resolve_section(
                index, part=part, number=match.group("number"), open_branch=open_branch
            )
            found.append(Match(match.start(), end, match.group(0), branch, fragment, title))

        position = max(end, match.start() + 1)

    if terms:
        found.extend(
            _term_matches(text, terms, index=index, open_branch=open_branch, seen=seen)
        )
        found.sort(key=lambda entry: (entry.start, -entry.end))
        kept: list[Match] = []
        for match in found:
            if kept and match.start < kept[-1].end:
                continue
            kept.append(match)
        return kept

    return found


def _term_matches(
    text: str,
    terms: Mapping[str, "GlossaryEntry"],
    *,
    index: ReferenceIndex,
    open_branch: str,
    seen: set[str] | None,
) -> list[Match]:
    """First occurrence of each defined term, longest first, at most once per `seen` set."""
    open_target = index.branches.get(open_branch)
    open_anchor = open_target.anchor if open_target is not None else ""
    linked: list[Match] = []
    taken: list[tuple[int, int]] = []
    for term in sorted(terms, key=len, reverse=True):
        entry = terms[term]
        if seen is not None and term in seen:
            continue
        if entry.branch_anchor and entry.branch_anchor == open_anchor:
            continue  # the definitions are on this page already
        pattern = re.compile(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", re.IGNORECASE)
        match = pattern.search(text)
        if match is None:
            continue
        if any(match.start() < end and start < match.end() for start, end in taken):
            continue
        taken.append((match.start(), match.end()))
        if seen is not None:
            seen.add(term)
        linked.append(
            Match(
                match.start(),
                match.end(),
                match.group(0),
                entry.branch_anchor,
                entry.fragment,
                "",  # no tooltip: the link's own text is the word it defines
            )
        )
    return linked


def segments_for(
    text: str,
    index: ReferenceIndex,
    *,
    open_branch: str = "",
    terms: Mapping[str, "GlossaryEntry"] | None = None,
    seen: set[str] | None = None,
) -> tuple[Segment, ...]:
    """In: a block's text. Out: that text as segments, with targets where the document points.

    The words are never changed: joining the segments reproduces `text` exactly. A match with no
    target and no title is folded back into the surrounding text, so a reader sees one string where
    the document printed one string.
    """
    hits = matches(text, index, open_branch=open_branch, terms=terms, seen=seen)
    if not hits:
        return (Segment(text),)

    segments: list[Segment] = []
    cursor = 0
    for hit in hits:
        if not hit.branch and not hit.fragment and not hit.title:
            continue
        if hit.start > cursor:
            segments.append(Segment(text[cursor : hit.start]))
        segments.append(Segment(hit.text, hit.branch, hit.fragment, hit.title))
        cursor = hit.end
    if cursor < len(text):
        segments.append(Segment(text[cursor:]))
    return tuple(segments) if segments else (Segment(text),)


def annotate(
    blocks: Sequence[Block],
    index: ReferenceIndex,
    *,
    open_branch: str = "",
    terms: Mapping[str, "GlossaryEntry"] | None = None,
) -> tuple[Block, ...]:
    """In: a passage's blocks. Out: the same blocks, their paragraphs and list items segmented.

    `seen` is created per call, which is what makes "at most one link per term per passage" a
    property of the caller: the reader calls this once per passage.
    """
    seen: set[str] = set()
    return tuple(_annotate_block(block, index, open_branch, terms, seen) for block in blocks)


def _annotate_block(
    block: Block,
    index: ReferenceIndex,
    open_branch: str,
    terms: Mapping[str, "GlossaryEntry"] | None,
    seen: set[str],
) -> Block:
    if isinstance(block, Paragraph):
        return replace(
            block,
            segments=segments_for(
                block.text, index, open_branch=open_branch, terms=terms, seen=seen
            ),
        )
    if isinstance(block, ListBlock):
        items = tuple(
            replace(
                item,
                segments=segments_for(
                    item.text, index, open_branch=open_branch, terms=terms, seen=seen
                ),
                children=tuple(
                    _annotate_block(child, index, open_branch, terms, seen)
                    for child in item.children
                ),
            )
            for item in block.items
        )
        return replace(block, items=items)
    return block


__all__ = [
    "MISSING_ANCHOR",
    "Match",
    "ReferenceIndex",
    "Segment",
    "Target",
    "annotate",
    "build_reference_index",
    "matches",
    "segments_for",
]
