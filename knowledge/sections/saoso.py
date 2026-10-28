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

**An appendix is one section, and this is not a shortcut.** Measured on the shipped
PDF (2026-10-19), Appendix 1 holds **two independently numbered criteria lists** — one
for organic production (printed pp. 71–72) and one for processing (pp. 73–75) — and
both run `1.`–`6.` with `1.1`, `1.2`, … ff. So `1.2` inside Appendix 1 is ambiguous
between two documents that share a page range and a heading. Clause refs there would
manufacture exactly the ambiguity reality 3 warns about, so appendix content is cited
as `Appendix 1` plus its page, and its sub-headings stay in the body text where FTS
finds them. The alternative — emitting `Appendix 1(1.2)` — was rejected because it
*looks* precise while resolving to two different paragraphs.
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

#: The page-run banner: the part letter, printed at the top of every page of the part
#: (`SECTION B` centred, at indent 8–63; and at column 0 on the appendix pages).
SECTION_LINE = re.compile(r"^\s*SECTION ([A-C])\s*$")

#: The part's title, printed beneath the banner in capitals at the same indent
#: (`DEFINITIONS, GENERAL PRINCIPLES, RECOMMENDATIONS AND STANDARDS`).
RUNNING_TITLE = re.compile(r"^\s{8,}[A-Z0-9][A-Z0-9 ,&.'()/\-]*$")


def _running_head(page_lines: list[str], index: int) -> tuple[int, bool]:
    """Out: the index just past the running head at `index`, and whether it had a title.

    `page_lines[index]` must be a `SECTION <letter>` line. The head is that line plus the
    blank lines and capitalised title lines directly under it.
    """
    end = index + 1
    titled = False
    while end < len(page_lines):
        line = page_lines[end]
        if RUNNING_TITLE.match(line) and not APPENDIX.match(line):
            titled = True
            end += 1
            continue
        # A blank line *between* the banner and its title belongs to the head; one after
        # the title is the first paragraph boundary.
        if (
            not line.strip()
            and end + 1 < len(page_lines)
            and RUNNING_TITLE.match(page_lines[end + 1])
            and not APPENDIX.match(page_lines[end + 1])
        ):
            end += 1
            continue
        break
    return end, titled


def without_running_head(page_lines: list[str]) -> list[str]:
    """Drop the page's running head: `SECTION B` and the part title printed under it.

    In:  one page's lines. Out: the same lines without the running head.
    Side effects: none. Fails: never.

    The banner is furniture — it is stamped on every page of the part — but it is *not*
    excluded by `is_furniture`, so it became the tail of twelve branches, telling a reader
    that a new part starts and then following nothing
    (`BugFixes/saoso_text_glyphs_and_boundaries.md` §3).

    Measured on the shipped Part B (2026-10-28): **21 pages open with it and no page opens
    with any other all-caps line at indent 8 or more.** Every other indented page-start is a
    label (`South African specific`), a table header or a wrapped sentence — which is why a
    bare `SECTION <letter>` is dropped only at a page start, where the document prints it.

    Mid-page it is dropped only when the part's title line sits directly under it: printed
    p. 40 puts a centred footnote above the banner (`S4.8.6`), and the title is what makes
    that head unambiguous wherever it lands.
    """
    kept: list[str] = []
    index = 0
    at_page_start = True
    while index < len(page_lines):
        line = page_lines[index]
        if SECTION_LINE.match(line):
            end, titled = _running_head(page_lines, index)
            if titled or at_page_start:
                index = end
                continue
        if line.strip():
            at_page_start = False
        kept.append(line)
        index += 1
    return kept


def canonical_appendix_label(part: str, table: str | None) -> str:
    """`APPENDIX 4, TABLE 2` -> `Appendix 4. Table 2`, the TOC's own label.

    The body prints the heading four different ways (`APPENDIX 4, TABLE 1`,
    `APPENDIX 4 TABLE 2:`, `APPENDIX 5:`, `APPENDIX 6a:`); the TOC prints one. A
    citation must show the form the reader can search for, so the body is normalised
    to the TOC's shape rather than left as extracted.

    The trailing letter stays **lowercase** (`Appendix 6a`, not `Appendix 6A`): `.title()`
    upper-cases it, and the TOC — which is the canonical label's source — prints `6a`.
    A citation that does not match the page it points at is not a citation.
    """
    label = part.title()
    if table:
        label = f"{label}. Table {table}"
    return re.sub(r"([0-9])([A-Z])$", lambda m: m.group(1) + m.group(2).lower(), label)


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

    def body_lines(
        self, text: str, part: str | None = None
    ) -> list[tuple[int, int | None, str]]:
        """The lines this parser treats as the document's body, with their pages.

        In:  `text` — pages of `pdftotext -layout` output, form-feed separated.
        Out: `(pdf_page, printed_page, line)` for every line of every page that belongs to
             `part`, TOC and other-part pages excluded. Blank lines are kept: they are
             the chunker's paragraph boundaries.
        Side effects: none. Fails: never.

        **This is not a convenience.** The corpus generator (D53) has to slice this
        document's sections out of a line stream, and it used to slice them out of *every
        page*. That produced a draft whose `S1` carried text from pages the reader never
        sees and whose `Appendix 7` reproduced all of Section C three times, because a
        section's body ran to the next heading *anywhere in the PDF*. One expression, one
        place: `parse()` is built on this, so the artefact cannot disagree with the
        parser about what the document's body is.
        """
        wanted = (part or self.PART).upper()
        current_part: str | None = None

        lines: list[tuple[int, int | None, str]] = []
        for pdf_page, raw_page in enumerate(text.split("\f"), 1):
            if TOC.search(raw_page):
                continue
            header = HDR.search(raw_page)
            if header:
                current_part = header.group(1)
            if current_part != wanted:
                continue
            printed = page_number(raw_page)
            page_lines = without_running_head(raw_page.splitlines())
            lines.extend((pdf_page, printed, line) for line in page_lines)
        return lines

    def parse(self, text: str, part: str | None = None, **_: object) -> list[ParsedSection]:
        """In:  `text` — one or more pages of `pdftotext -layout` output, form-feed
                   separated; `part` — the part letter, defaulting to D41's `B`.
        Out: sections in document order, each with a `section_ref`, a printed `page`,
             a `heading_path`, and text that partitions the document (a section
             never contains a sibling's text).
        Fails: nothing. A document with no part header yields `[]`, which is the
             correct answer for the TOC and for Section A.
        """
        return self._build(
            [(printed, line) for _pdf, printed, line in self.body_lines(text, part)]
        )

    def _build(self, lines: list[tuple[int | None, str]]) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        # Heading stack for `heading_path`, shallowest first: [(depth, printed title)].
        stack: list[tuple[int, str]] = []
        body: list[str] = []
        current: dict | None = None
        in_appendix = False

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
                    heading_path=(
                        current["ref"]
                        if current["kind"] == "appendix"
                        # The path **includes** the section itself, which is the corpus
                        # format's rule (`knowledge/corpus.py`) and the only form that is
                        # useful alone: `20. PROCESSING AND HANDLING > 20.1. General` says
                        # where the clause is, while its parent alone says where it is not.
                        # The reviewed artefact derives the same path from the `#` depth,
                        # so the two paths agree and `test_corpus_saoso.py` can prove it
                        # (changed 2026-10-28, when the artefact landed).
                        else " > ".join(title for _, title in stack)
                    ),
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

            depth, ref, printed_title, anchor, kind = heading

            if kind == "clause" and in_appendix:
                # Inside an appendix every clause-shaped line is body text. Appendix 1
                # alone contains two lists that both start at `1.`, so splitting there
                # would emit `S1.2` twice for two different paragraphs (see the module
                # docstring). The appendix is one section; its page is the locator.
                if current is not None and not is_furniture(line):
                    body.append(line)
                continue

            flush()
            body = []
            in_appendix = kind == "appendix"
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, printed_title))
            current = {
                "ref": ref,
                "heading": line.strip(),
                "page": printed,
                "anchor": anchor,
                "kind": kind,
            }

        flush()
        return sections

    def _as_heading(self, line: str) -> tuple[int, str, str, str, str] | None:
        """Classify a line as a heading.

        Out: `(depth, section_ref, printed_title, anchor, kind)` or None, where `kind`
            is `"appendix"` or `"clause"`. `depth` is the number of dotted parts (so
            `20` is 1, `20.1.1` is 3) and exists only to build `heading_path`; it is
            never part of the citation.
        """
        appendix = APPENDIX.match(line)
        if appendix:
            label = canonical_appendix_label(appendix.group(1), appendix.group(2))
            return 0, label, label, "", "appendix"

        clause = CLAUSE.match(line)
        if clause:
            number = clause.group(1)
            depth = number.count(".") + 1
            return depth, f"S{number}", line.strip(), "", "clause"

        return None


__all__ = ["APPENDIX", "CLAUSE", "HDR", "SaosoParser", "appendix_number"]
