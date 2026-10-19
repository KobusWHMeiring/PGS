"""Section-reference parsers, one per source format (spec §4.5, D14/D15/D43).

`knowledge` is a library over documents, and this package is the one genuinely
standard-specific step in it: extracting citations. Each format is read as it is
printed, and the format is chosen by **data** (`StandardDocument.section_scheme` ->
`registry.get`), never by a branch in the ingestion code.

Three schemes ship:

===========  ==============================  ===========================
scheme       document                        citation
===========  ==============================  ===========================
``saoso``    SAOSO Standard v2.1             ``S20.1.1``
``opp``      Outeniqua OPP                   ``§V``, ``§4.2``, ``§4.2(5)``
``heading``  BPP, certification landscape    page + heading (no ref)
===========  ==============================  ===========================

Two conventions are shared by all three and are **contract**, not preference:

1. `page` is the number printed in the document's own footer — the reader's page
   (D42). It differs from the PDF viewer's index by one, because the cover is
   unnumbered. `page_number()` reads it from the footer, so no caller has to know
   the offset.
2. A `ParsedSection` is passed straight to `DocumentChunk(**parsed.as_chunk_kwargs())`
   by B6. `sub_refs` are emitted as plain dicts (`SubRef.as_dict`) because that is
   what `DocumentChunk.sub_refs` (JSONB) and `validate_sub_refs` expect.

Reference depth is bounded at three (D15): ``section_ref`` is one level,
``sub_ref`` up to two, and nothing deeper is synthesised. See `opp.py` for the one
place the source's own numbering would otherwise force a fourth level.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

#: Every SAOSO/OPP page footer prints the reader's page number as `P a g e | 60`
#: (letters spaced by the PDF's own kerning). D42: this — not the PDF index — is
#: what `DocumentChunk.page` stores.
PAGE_FOOTER = re.compile(r"P\s*a\s*g\s*e\s*\|\s*(\d+)")

#: Page furniture that is never a heading and never body text. Kept as patterns
#: rather than as exact strings because the phone/fax/e-mail block varies.
FURNITURE = (
    re.compile(r"Registration\s+\d"),
    re.compile(r"Postnet Suite"),
    re.compile(r"The South African Organic Sector Organisation"),
    re.compile(r"^\s*www\.", re.M),
)


def page_number(page_text: str) -> int | None:
    """The reader's page number from a page's footer, or None.

    In:  one page of `pdftotext -layout` output (no form feed).
    Out: the integer printed after `Page |`, or None when the page has no footer
        (the cover, and the front matter).
    """
    match = PAGE_FOOTER.search(page_text)
    return int(match.group(1)) if match else None


def is_furniture(line: str) -> bool:
    """True for the repeating footer/contact block, which is not content."""
    return any(pattern.search(line) for pattern in FURNITURE)


def slug(text: str) -> str:
    """A URL- and citation-safe locator stem: `4.5 Non-compliance` -> `4.5-non-compliance`.

    Used only where the source prints no reference at all, so the anchor is derived
    from content rather than invented as a fake clause number (§4.5).
    """
    lowered = text.strip().lower()
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", lowered)).strip("-")


@dataclass(frozen=True)
class SubRef:
    """One enumerated clause inside a chunk, as character offsets into its text.

    In:  `ref` — the plain reference (`4.5(2)(c)`, never `§4.5(2)(c)`, D43);
        `start`/`end` — offsets into the owning `ParsedSection.text`.
    Out: `as_dict()` for `DocumentChunk.sub_refs`.

    Offsets rather than separate chunks is D15: splitting at every item would
    fragment the OPP into hundreds of context-poor chunks, so the chunk stays
    section-level and a citation slices the text it needs.
    """

    ref: str
    start: int
    end: int

    def as_dict(self) -> dict:
        return {"ref": self.ref, "start": self.start, "end": self.end}


@dataclass(frozen=True)
class ParsedSection:
    """One citation-bearing unit of a document, ready to become a `DocumentChunk`.

    `section_ref` is None only for a scheme that prints no numbering (`heading`),
    which is exactly the case B1's CHECK constraint permits and `""` is not.
    """

    section_ref: str | None
    text: str
    heading_path: str = ""
    page: int | None = None
    anchor: str = ""
    sub_refs: tuple[SubRef, ...] = field(default=())

    def as_chunk_kwargs(self) -> dict:
        """The keyword arguments `DocumentChunk.objects.create(**…)` takes."""
        return {
            "section_ref": self.section_ref,
            "text": self.text,
            "heading_path": self.heading_path,
            "page": self.page,
            "anchor": self.anchor,
            "sub_refs": [ref.as_dict() for ref in self.sub_refs],
        }


class SectionParser(Protocol):
    """What `registry.get` returns. `parse` is pure: text in, sections out."""

    scheme: str

    def parse(self, text: str, **kwargs) -> list[ParsedSection]:  # pragma: no cover
        ...


def line_offsets(lines: list[str]) -> tuple[list[int], int]:
    """Character offsets of each line inside `"\\n".join(lines)`.

    Out: `(offsets, text_length)`. `text_length` excludes the final newline, so
        `end <= text_length` holds for the last line (B1's `validate_sub_refs`).
    """
    offsets: list[int] = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line) + 1
    return offsets, max(position - 1, 0)


def any_level_end(
    refs: list[tuple[str, int, int]],
    offsets: list[int],
    text_length: int,
) -> list[SubRef]:
    """Turn `(ref, depth, line_index)` markers into offset-bearing `SubRef`s.

    A marker's slice runs to the next marker of the same or shallower depth, so a
    parent's slice includes its children (`4.5(2)` contains `(a)`, `(b)`, `(c)`)
    and a leaf's slice stops at its next sibling. That is what a citation needs:
    quoting `4.5(2)` must not stop mid-sentence.
    """
    ordered = sorted(refs, key=lambda item: item[2])
    out: list[SubRef] = []
    for index, (ref, depth, line_index) in enumerate(ordered):
        start = offsets[line_index]
        end = text_length
        for later_ref, later_depth, later_line in ordered[index + 1 :]:
            if later_depth <= depth:
                end = offsets[later_line]
                break
        out.append(SubRef(ref=ref, start=start, end=end))
    return out
