"""The chunker: section-level chunks with re-based `sub_refs` (D15, SPEC §4.5).

Two rules decide everything here.

**Chunks stay section-level.** Sub-item boundaries never split a chunk; they produce
offsets into it. Splitting at every enumerated item would turn the OPP into hundreds
of context-poor fragments and degrade retrieval — B4's acceptance is a chunk count in
the low tens.

**Chunk text is a slice of the section text, never a reconstruction.** Every chunk is
`section.text[start:end]`, so the offsets are exact by construction and a chunk cannot
contain a sentence the source does not. That is also why the `sub_refs` can be re-based
with subtraction rather than by re-finding text.

Splitting order: blank-line paragraphs first, and only a paragraph that is itself
larger than the target is cut at line boundaries. A chunk boundary inside a paragraph
is the last resort, because a quotation that starts mid-sentence is a poor citation.

**A note on overlapping `sub_refs`.** `MVP0_PLAN_V2.md` B4 says "sub_refs never
overlap". Nested references necessarily do, and deliberately: `4.5(2)` contains
`4.5(2)(a)`, `(b)` and `(c)`, and a citation for `4.5(2)` that stopped before its own
sub-items would quote a heading and nothing else. What the plan's rule is protecting —
duplicated or lost references — is asserted instead: each `sub_ref` lands in exactly
one chunk, no ref appears twice, and no two *siblings* (same depth, same parent)
overlap.

`Chunk` carries the section's identity fields as well as the text, so B6 writes a
`DocumentChunk` row straight from `as_chunk_kwargs()`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from knowledge.sections import ParsedSection, SubRef

#: SPEC §4.5: "~800-token targets". No tokeniser runs in the ingestion path — a model
#: dependency there would make chunk boundaries non-deterministic and unmeasurable.
CHARS_PER_TOKEN = 4
TARGET_TOKENS = 800
OVERLAP_TOKENS = 100

#: A blank line (or a line holding only spaces) separates paragraphs.
PARAGRAPH_GAP = re.compile(r"\n[ \t]*\n")


def estimate_tokens(text: str) -> int:
    """Tokens, estimated at four characters each. Zero for empty text.

    Deliberately an estimate: the number is used to bound chunk size, never to bill or
    to cite. `token_count` on the chunk records it so a later slice can compare.
    """
    if not text:
        return 0
    return math.ceil(len(text) / CHARS_PER_TOKEN)


@dataclass(frozen=True)
class Chunk:
    """One `DocumentChunk` worth of text, with offsets relative to itself."""

    section_ref: str | None
    text: str
    token_count: int
    sub_refs: tuple[SubRef, ...] = field(default=())
    heading_path: str = ""
    page: int | None = None
    anchor: str = ""
    #: Where this chunk sits inside its section's text. Not stored in the database;
    #: it is what makes overlap measurable (and therefore testable).
    source_start: int = 0
    source_end: int = 0

    def as_chunk_kwargs(self) -> dict:
        """The keyword arguments `DocumentChunk.objects.create(**…)` takes."""
        return {
            "section_ref": self.section_ref,
            "text": self.text,
            "heading_path": self.heading_path,
            "page": self.page,
            "anchor": self.anchor,
            "sub_refs": [ref.as_dict() for ref in self.sub_refs],
            "token_count": self.token_count,
        }


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Spans of non-empty paragraphs, in order."""
    spans: list[tuple[int, int]] = []
    cursor = 0
    for gap in PARAGRAPH_GAP.finditer(text):
        if gap.start() > cursor:
            spans.append((cursor, gap.start()))
        cursor = gap.end()
    if cursor < len(text):
        spans.append((cursor, len(text)))
    return [(start, end) for start, end in spans if text[start:end].strip()]


def _line_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Split one paragraph at its line boundaries, keeping non-empty lines."""
    spans: list[tuple[int, int]] = []
    cursor = start
    for line in text[start:end].split("\n"):
        if line.strip():
            spans.append((cursor, cursor + len(line)))
        cursor += len(line) + 1
    return spans


def _hard_split_spans(
    text: str, start: int, end: int, target_chars: int
) -> list[tuple[int, int]]:
    """Last resort: a single line longer than the target, cut into fixed windows."""
    return [(position, min(position + target_chars, end))
            for position in range(start, end, target_chars)]


def _units(text: str, target_tokens: int) -> list[tuple[int, int]]:
    """The smallest spans the chunker will not cut: paragraphs, lines, then windows."""
    target_chars = target_tokens * CHARS_PER_TOKEN
    units: list[tuple[int, int]] = []
    for start, end in _paragraph_spans(text):
        if estimate_tokens(text[start:end]) <= target_tokens:
            units.append((start, end))
            continue
        for line_start, line_end in _line_spans(text, start, end):
            if estimate_tokens(text[line_start:line_end]) <= target_tokens:
                units.append((line_start, line_end))
            else:
                units.extend(
                    _hard_split_spans(text, line_start, line_end, target_chars)
                )
    return units


def _span_tokens(text: str, spans: list[tuple[int, int]]) -> int:
    return sum(estimate_tokens(text[start:end]) for start, end in spans)


def _overlap_tail(
    text: str, spans: list[tuple[int, int]], overlap_tokens: int
) -> list[tuple[int, int]]:
    """The trailing whole units of `spans` that fit inside the overlap budget."""
    tail: list[tuple[int, int]] = []
    total = 0
    for span in reversed(spans):
        cost = estimate_tokens(text[span[0] : span[1]])
        if total + cost > overlap_tokens:
            break
        tail.insert(0, span)
        total += cost
    return tail


def _assign_sub_refs(
    section: ParsedSection,
    text: str,
    windows: list[tuple[int, int]],
) -> list[list[SubRef]]:
    """Put every `sub_ref` in exactly one window, re-based to that window.

    In:  `section` — the parent; `text` — its text; `windows` — `(start, end)` per
         chunk, in order.
    Out: one list per window, in the same order.

    A ref is assigned to the **first** window containing its start, which is what
    makes the overlap safe: without the "first" rule, a ref sitting in the shared tail
    would be claimed by two chunks and the same clause would be citable twice with two
    different quote ranges.
    """
    buckets: list[list[SubRef]] = [[] for _ in windows]
    for ref in section.sub_refs:
        for index, (start, end) in enumerate(windows):
            if start <= ref.start < end:
                new_start = max(ref.start, start) - start
                new_end = min(ref.end, end) - start
                if new_end > new_start:
                    buckets[index].append(SubRef(ref.ref, new_start, new_end))
                break
    return buckets


def chunk_section(
    section: ParsedSection,
    *,
    target_tokens: int = TARGET_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    """Split one section into chunks. Never mixes two sections; never loses a sub_ref.

    In:  `section` — from a `knowledge.sections` parser; `target_tokens`/`overlap_tokens`
         — bounds, defaulted from SPEC §4.5 and overridable for tests.
    Out: at least one chunk. A section that fits the target yields exactly one chunk
         whose text is the section's text, so the common case is lossless.
    """
    text = section.text
    units = _units(text, target_tokens)
    if not units:
        return [_chunk_from(section, text, 0, len(text), list(section.sub_refs))]

    windows: list[tuple[int, int]] = []
    current: list[tuple[int, int]] = []
    for unit in units:
        if current and _span_tokens(text, current) + _span_tokens(text, [unit]) > target_tokens:
            windows.append((current[0][0], current[-1][1]))
            current = _overlap_tail(text, current, overlap_tokens)
        current.append(unit)
    if current:
        windows.append((current[0][0], current[-1][1]))

    buckets = _assign_sub_refs(section, text, windows)
    return [
        _chunk_from(section, text, start, end, refs)
        for (start, end), refs in zip(windows, buckets)
    ]


def _chunk_from(
    section: ParsedSection,
    text: str,
    start: int,
    end: int,
    refs: list[SubRef],
) -> Chunk:
    chunk_text = text[start:end]
    return Chunk(
        section_ref=section.section_ref,
        text=chunk_text,
        token_count=estimate_tokens(chunk_text),
        sub_refs=tuple(refs),
        heading_path=section.heading_path,
        page=section.page,
        anchor=section.anchor,
        source_start=start,
        source_end=end,
    )


def chunk_sections(
    sections: list[ParsedSection],
    *,
    target_tokens: int = TARGET_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    """Chunk a whole document, section by section, preserving document order."""
    chunks: list[Chunk] = []
    for section in sections:
        chunks.extend(
            chunk_section(
                section, target_tokens=target_tokens, overlap_tokens=overlap_tokens
            )
        )
    return chunks
