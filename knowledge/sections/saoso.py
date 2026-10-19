"""The SAOSO Standard's section scheme — `20.1.1.` cited as `S20.1.1` (D14, D43).

Written against the verbatim fixtures and the measurements in SPEC §4.5. The four
realities this parser has to respect, each of which broke a plausible-looking
earlier design:

1. **The part letter is a running page header, not a body heading.** `SECTION A`
   never appears in the body; `SECTION B` heads 22 body pages and `SECTION C` heads
   three (its appendices). The letter is read from the header and **carried
   forward**, because most pages print none — the letter is on one side of each
   spread only. A parser that forgets the carry-forward attributes page 62's clauses
   to whichever part it saw last, which is how a citation becomes unfindable.
2. **The TOC matches the clause pattern.** `1.         Introduction - …    4` is
   clause-shaped, so the TOC pages are skipped explicitly or 60+ duplicate clauses
   are ingested.
3. **Appendix headings exist in the body, in UPPERCASE**, with four different
   separator shapes and indentation from 0 to 62 columns. The TOC supplies the
   canonical *label*, which is what `section_ref` shows, but not the boundary.
4. **Section A's numbering collides with itself**, so MVP 0 ingests Section B and its
   appendices only (D41). That is `PART`'s default and the reason `part` is checked
   rather than assumed.

`sub_refs` are deliberately **not** emitted for SAOSO: the standard's items are
lettered (`a  Indicate …`) without a printed, citable numbering, and SPEC §4.5 emits
`sub_ref` "only where the source actually enumerates a clause". Inventing
`S20.1.1(a)` would be the same class of error as the withdrawn `B.20.1.1`.
"""

from __future__ import annotations

import re

from knowledge.sections import (
    ParsedSection,
    any_level_end,
    is_furniture,
    line_offsets,
    page_number,
)

#: `20.`, `20.1.`, `20.1.1.` — always at column 0, always with a trailing period.
#: Verified: the body never prints `B-20.1.1` or `B.20.1.1` (that prefix was invented
#: and withdrawn, D43).
CLAUSE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)\.\s+(\S.*)$")

#: The running part header. Indent 8+ excludes the TOC's column-0 `SECTION A`.
HDR = re.compile(r"^\s{8,}SECTION ([A-C])\s*$", re.MULTILINE)

#: UPPERCASE appendix heading, tolerating `,` / `:` / `.` / nothing, and the
#: `TABLE 1` / `TABLE 2` variants of Appendix 4. Case-sensitivity is load-bearing:
#: a title-case pattern matches nothing in the body and false-positives on p63
#: (`Appendix 4.` starting a mid-sentence line) — see A10's fixture notes.
APPENDIX = re.compile(
    r"^\s*(APPENDIX\s+(?:\d{1,2}[a-z]?|[A-C]))"      # APPENDIX 4, APPENDIX 6a, APPENDIX A
    r"(?:\s*,?\s*TABLE\s+(\d{1,2}))?"                 # optional: , TABLE 1 / TABLE 2
    r"\s*[.:]?\s*$"
)

#: A page whose only job is to list the document's contents.
TOC = re.compile(r"TABLE OF CONTENTS")


def canonical_appendix_label(part: str, table: str | None) -> str:
    """`APPENDIX 4, TABLE 2` -> `Appendix 4. Table 2`, the TOC's own label.

    The body prints the heading four different ways (`APPENDIX 4, TABLE 1`,
    `APPENDIX 4 TABLE 2:`, `APPENDIX 5:`, `APPENDIX 6a:`); the TOC prints one. A
    citation must show the form the reader can search for, so the body is normalised
    to the TOC's shape rather than left as extracted.
    """
    label = part.title()
    if table:
        return f"{label}. Table {table}"
    return label


def appendix_number(part: str) -> str:
    """`APPENDIX 6a` -> `6a`; `APPENDIX A` -> `A`."""
    return part.split(None, 1)[1]


class SaosoParser:
    """Parse the SAOSO body into cited sections. Pure: text in, sections out."""

    scheme = "saoso"

    #: D41: Section B is the ingested part. Section A's numbers collide within
    #: Section A itself and Section C restarts at 1, so nothing outside B carries a
    #: unique `section_ref`.
    PART = "B"

    def parse(self, text: str, part: str | None = None, **_: object) -> list[ParsedSection]:
        """In:  `text` — one or more pages of `pdftotext -layout` output, form-feed
                   separated; `part` — the part letter, defaulting to D41's `B`.
        Out: sections in document order, each with a `section_ref`, a printed `page`,
             a `heading_path`, and text that partitions the document (a section
             never contains a sibling's text).
        Fails: nothing. A document with no part header yields `[]`, which is the
             correct answer for the TOC and for Section A.
        """
        wanted = (part or self.PART).upper()
        current_part: str | None = None

        # Flatten to (printed page, line), skipping TOC pages entirely and every page
        # that belongs to another part.
        lines: list[tuple[int | None, str]] = []
        for raw_page in text.split("\f"):
            if TOC.search(raw_page):
                continue
            header = HDR.search(raw_page)
            if header:
                current_part = header.group(1)
            if current_part != wanted:
                continue
            printed = page_number(raw_page)
            lines.extend((printed, line) for line in raw_page.splitlines())

        return self._build(lines)

    def _build(self, lines: list[tuple[int | None, str]]) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        # Heading stack for `heading_path`, shallowest first: [(depth, printed title)].
        stack: list[tuple[int, str]] = []
        body: list[str] = []
        current: dict | None = None

        def flush() -> None:
            if current is None:
                return
            # The heading line is included so a parent heading with no body of its own
            # is still a citable, non-empty section (e.g. `20. PROCESSING AND HANDLING`).
            section_lines = [current["heading"], *body]
            text_value = "\n".join(section_lines)
            sections.append(
                ParsedSection(
                    section_ref=current["ref"],
                    text=text_value,
                    heading_path=" > ".join(title for _, title in stack[:-1]),
                    page=current["page"],
                    anchor=current["anchor"],
                )
            )

        for printed, line in lines:
            heading = self._as_heading(line)
            if heading is None:
                if current is not None and not is_furniture(line):
                    body.append(line)
                continue

            flush()
            body = []
            depth, ref, printed_title, anchor = heading
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, printed_title))
            current = {
                "ref": ref,
                "heading": line.strip(),
                "page": printed,
                "anchor": anchor,
            }

        flush()
        return sections

    def _as_heading(self, line: str) -> tuple[int, str, str, str] | None:
        """Classify a line as a heading.

        Out: `(depth, section_ref, printed_title, anchor)` or None. `depth` is the
            number of dotted parts (so `20` is 1, `20.1.1` is 3) and exists only to
            build `heading_path`; it is never part of the citation.
        """
        appendix = APPENDIX.match(line)
        if appendix:
            label = canonical_appendix_label(appendix.group(1), appendix.group(2))
            return 0, label, label, ""

        clause = CLAUSE.match(line)
        if clause:
            number = clause.group(1)
            depth = number.count(".") + 1
            return depth, f"S{number}", line.strip(), ""

        return None


__all__ = ["APPENDIX", "CLAUSE", "HDR", "SaosoParser", "appendix_number"]
