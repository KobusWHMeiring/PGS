"""The heading-only scheme — BPP and the certification landscape (SPEC §4.5).

These two documents print **no clause numbering at all**, so their citation is
"page + heading" and `section_ref` is None. B1's CHECK constraint permits NULL and
refuses the empty string precisely so this case is storable and a parser bug is not.

How headings are found:

- **Segments, not lines.** `pdftotext -layout` puts left- and right-column text on
  the *same* line (`INTRODUCTION                    DEFINITION OF ORGANIC`), so before
  the page is de-columned it is split on a run of three or more spaces. That split is
  kept after the column transform too, because a line that still holds two headings
  side by side (a spanning heading, a table header) is not cut by the transform.
- **UPPERCASE only.** Title-case lines (`First-Party Claim`) are therefore *missed*.
  That is a known, documented gap: catching them needs more than a column heuristic,
  and a false heading is a worse citation than a missing one.
- **Running headers are suppressed by repetition.** `PGS SA - SOUTH AFRICAN ORGANIC
  CERTIFICATION LANDSCAPE` is stamped on most pages; a detector that emitted every
  caps line would produce one bogus section per page, and a section the reader cannot
  locate is the definition of a bad citation.
- **A one-word continuation is merged** into the heading above it, so BPP's
  `DEFINITION OF ORGANIC` / `AGRICULTURE` is one heading rather than one heading plus
  a spurious one.

**Body attribution is exact for column pages.** The page is de-columned at ingest
(`knowledge/columns.py`, D46), so the parser walks one column at a time and a section's
body is its own column's text. Before that transform body attribution in a two-column
document was approximate — right-column text could land in the left column's section.
The transform leaves table rows separated rather than associated (§3.5), which is a
reading caveat, not an attribution one.

`page` is again the number printed in the document (D42). The certification landscape
stamps a bare number; the BPP stamps a bare number on only some pages (measured:
`None, None, None, 10`), so its other chunks carry `page=None` and the `anchor` is the
only locator.
"""

from __future__ import annotations

import re

from knowledge.sections import ParsedSection, is_furniture, page_number, slug

#: Column separation. Three spaces is wide enough not to split normal prose.
COLUMN_GAP = re.compile(r"\s{3,}")

#: A heading occupies a column segment and is printed in capitals.
CAPS = re.compile(r"^[A-Z0-9][A-Z0-9 ,&.'()/\-]*$")

BARE_PAGE = re.compile(r"^\d{1,3}$")

MIN_HEADING = 4
MAX_HEADING = 80


def page_stamp(page_text: str) -> int | None:
    """The page number a heading-only document prints, or None.

    Two shapes exist in the corpus: a labelled footer (`Page | 6`, SAOSO and the OPP,
    read by `page_number`) and a bare number (the certification landscape prints `6`, and
    the BPP prints `02` at the foot of a page). The bare stamp is searched for anywhere,
    not just at the end: the stamp is page furniture, and re-ordering a two-column page
    moves it into the middle. Searching only the tail found it before the column
    transform and lost it after, silently nulling every landscape citation (D42, hazard
    §1.21).

    Public because the corpus generator (D53) has to produce the same `page` the parser
    does — two implementations of "the printed page" would drift, and the artefact's
    equivalence test would be checking the wrong number.
    """
    labelled = page_number(page_text)
    if labelled is not None:
        return labelled
    stamps = [
        int(line.strip())
        for line in page_text.splitlines()
        if BARE_PAGE.match(line.strip())
    ]
    return stamps[-1] if stamps else None


class HeadingParser:
    """Parse a heading-only document into anchored sections."""

    scheme = "heading"

    def parse(self, text: str, **_: object) -> list[ParsedSection]:
        """In:  `text` — `pdftotext -layout` output, form-feed separated.
        Out: one section per heading, `section_ref=None`, `anchor` from the heading,
             `page` from the document's own page stamp where it has one.
        """
        pages = text.split("\f")
        # Group segments by page *and* line: repetition across pages is a running
        # header, repetition within a page is a table header and stays a heading.
        pages_segments: list[list[list[str]]] = [
            [
                [segment for segment in COLUMN_GAP.split(line) if segment.strip()]
                for line in page.splitlines()
            ]
            for page in pages
        ]
        repeated = self._repeated_headings(pages_segments)

        sections: list[ParsedSection] = []
        current: dict | None = None
        previous_was_heading = False

        def flush() -> None:
            nonlocal current
            if current is None:
                return
            body = current["body"]
            while body and not body[-1].strip():
                body.pop()
            sections.append(
                ParsedSection(
                    section_ref=None,
                    text="\n".join([current["heading"], *body]).strip(),
                    heading_path=current["heading"],
                    page=current["page"],
                    anchor=slug(current["heading"]),
                )
            )
            current = None

        printed: int | None = None
        for page, page_segments in zip(pages, pages_segments):
            stamp = self._page_stamp(page)
            if stamp is not None:
                printed = stamp
            elif printed is not None:
                printed += 1

            for line_segments in page_segments:
                if len(line_segments) == 1 and BARE_PAGE.match(line_segments[0].strip()):
                    continue
                for segment in line_segments:
                    segment = segment.strip()
                    if not segment:
                        continue
                    if self._is_heading(segment, repeated):
                        if (
                            previous_was_heading
                            and current is not None
                            and len(segment.split()) == 1
                        ):
                            # `DEFINITION OF ORGANIC` / `AGRICULTURE`.
                            current["heading"] = f"{current['heading']} {segment}".strip()
                            previous_was_heading = True
                            continue
                        flush()
                        current = {"heading": segment.upper(), "body": [], "page": printed}
                        previous_was_heading = True
                        continue
                    if current is not None and not is_furniture(segment):
                        current["body"].append(segment)
                    previous_was_heading = False

        flush()
        return sections

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _page_stamp(page_text: str) -> int | None:
        """Kept as the method the parser calls; the logic lives in `page_stamp`."""
        return page_stamp(page_text)

    @staticmethod
    def _repeated_headings(pages_segments: list[list[list[str]]]) -> set[str]:
        """Heading-shaped segments appearing on more than one page.

        A running header is the same text on page after page; a real heading appears
        once. Pages are tracked as a set per heading, so a heading printed twice on a
        single page (a table header, say) is not mistaken for furniture.
        """
        pages_by_heading: dict[str, set[int]] = {}
        for page_index, page_segments in enumerate(pages_segments):
            for line_segments in page_segments:
                for segment in line_segments:
                    if HeadingParser._looks_like_heading(segment):
                        pages_by_heading.setdefault(segment.strip().upper(), set()).add(
                            page_index
                        )
        return {heading for heading, pages in pages_by_heading.items() if len(pages) >= 2}

    @staticmethod
    def _looks_like_heading(segment: str) -> bool:
        stripped = segment.strip()
        return (
            MIN_HEADING <= len(stripped) <= MAX_HEADING
            and bool(CAPS.match(stripped))
            and any(character.isalpha() for character in stripped)
        )

    @classmethod
    def _is_heading(cls, segment: str, repeated: set[str]) -> bool:
        stripped = segment.strip()
        if not cls._looks_like_heading(stripped):
            return False
        if stripped.upper() in repeated:
            return False
        return not is_furniture(stripped) and not BARE_PAGE.match(stripped)


__all__ = ["HeadingParser", "page_stamp"]
