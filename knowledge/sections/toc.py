"""Task B3 — the TOC page map and appendix attribution.

What this module is for, given that B2 already finds appendix headings in the body:
it is the **cross-check and the fallback**. Measured 2026-10-19, the SAOSO body does
print all twelve appendix headings in UPPERCASE (SPEC §4.5 reality 4, corrected), so
boundaries come from the body. The TOC is what supplies:

- the **canonical label** (`Appendix 4. Table 2`, where the body prints
  `APPENDIX 4 TABLE 2:`),
- the **page numbers**, which let a page with no heading on it — the second and third
  pages of an appendix — still be attributed to an appendix instead of being absorbed
  into the preceding clause, which is B3's acceptance test,
- an independent check that a heading was not missed.

**Coordinates.** The TOC prints the *reader's* page (D42), and for SAOSO that is the
PDF index minus one: `Appendix 1` is TOC page 70 and PDF page 71, cross-checked
against A10's `MANIFEST.json`, whose `saoso_appendices` extract starts at PDF 71.
Because confusing those two is precisely the error D42 exists to prevent,
`appendix_for_page()` takes the coordinate **explicitly** and refuses anything else.
The plan's B3 test asks for `segment_appendix(page=71) == "Appendix 1"` — that is the
PDF coordinate, and `appendix_for_page(71, coordinate="pdf")` is how to say it.

The TOC is not uniform, and the parser records rather than repairs that: `10 to 19.`
is a range with **no page number** at all, and several entries wrap onto a second line
(`Appendix 1. … 70` / `Production and Processing`). A parser that assumed one
`label … page` per line would misread both.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: SAOSO's front cover is unnumbered, so the page the document prints is one less than
#: the PDF viewer's index. Measured on the shipped PDF (`P a g e | 20` is PDF p21) and
#: confirmed against A10's fixture manifest. Not a guess: only SAOSO has this offset
#: among the four corpus documents — the OPP and the certification landscape stamp
#: numbers that equal their PDF index.
PRINTED_TO_PDF_OFFSET = 1

#: `SECTION B` in the TOC, at column 0. In the *body* the same words are indented ~30
#: columns, which is how `saoso.py` distinguishes a running header from the TOC.
PART_MARKER = re.compile(r"^SECTION ([A-C])\s*$")

#: `20.        Processing Handling                        60`
TOC_CLAUSE = re.compile(r"^(\d{1,2})\.\s+(\S.*?)\s+(\d{1,3})\s*$")

#: `Appendix 4. Table 2. Indicative List of …            83`
#: Section C adds letter appendices (`Appendix A. SAOSO Organic Logos`), so the
#: number class must accept letters as well — the first run of this regex silently
#: dropped all three of them, and the span for Appendix 7 then swallowed Section C.
TOC_APPENDIX = re.compile(
    r"^(Appendix\s+(?:\d{1,2}[a-z]?|[A-C])(?:\.\s*Table\s+\d{1,2})?)\.\s+"
    r"(\S.*?)\s+(\d{1,3})\s*$"
)

#: `10 to 19.  Left blank to facilitate future enterprises` — no page number exists.
TOC_RANGE = re.compile(r"^(\d{1,2})\s+to\s+(\d{1,2})\.\s*(.*)$")

CLAUSE = "CLAUSE"
APPENDIX = "APPENDIX"
RANGE = "RANGE"


@dataclass(frozen=True)
class TocEntry:
    """One table-of-contents line. `printed_page` is None for a range entry."""

    part: str | None
    kind: str
    label: str
    title: str
    printed_page: int | None

    @property
    def pdf_page(self) -> int | None:
        """The PDF index this entry starts on, for `pdftotext -f`."""
        if self.printed_page is None:
            return None
        return self.printed_page + PRINTED_TO_PDF_OFFSET


@dataclass(frozen=True)
class AppendixSpan:
    """The page range an appendix occupies, in printed pages.

    `last_printed_page` is None when nothing follows it in the TOC — an open-ended
    final span. Callers that know the document's length can pass it to close the span
    instead of guessing.
    """

    part: str | None
    label: str
    title: str
    first_printed_page: int
    last_printed_page: int | None

    def contains_printed(self, page: int) -> bool:
        if page < self.first_printed_page:
            return False
        return self.last_printed_page is None or page <= self.last_printed_page


def parse_toc(text: str) -> list[TocEntry]:
    """In:  `text` — the TOC pages of `pdftotext -layout` output.
    Out: entries in document order, each tagged with the `SECTION` letter carried
         forward from the last marker seen. Front matter, the wrapped continuation
         lines and the contact block are ignored.
    """
    entries: list[TocEntry] = []
    part: str | None = None

    for line in text.replace("\f", "\n").splitlines():
        marker = PART_MARKER.match(line)
        if marker:
            part = marker.group(1)
            continue

        appendix = TOC_APPENDIX.match(line)
        if appendix:
            entries.append(
                TocEntry(
                    part=part,
                    kind=APPENDIX,
                    label=appendix.group(1),
                    title=appendix.group(2),
                    printed_page=int(appendix.group(3)),
                )
            )
            continue

        blank_range = TOC_RANGE.match(line)
        if blank_range:
            entries.append(
                TocEntry(
                    part=part,
                    kind=RANGE,
                    label=f"{blank_range.group(1)} to {blank_range.group(2)}",
                    title=blank_range.group(3).strip(),
                    printed_page=None,
                )
            )
            continue

        clause = TOC_CLAUSE.match(line)
        if clause:
            entries.append(
                TocEntry(
                    part=part,
                    kind=CLAUSE,
                    label=clause.group(1),
                    title=clause.group(2),
                    printed_page=int(clause.group(3)),
                )
            )

    return entries


def appendix_spans(
    entries: list[TocEntry],
    *,
    last_printed_page: int | None = None,
) -> list[AppendixSpan]:
    """The page range of each appendix, derived from the next appendix's start page.

    In:  `entries` — from `parse_toc`; `last_printed_page` — the document's final
         printed page, used to close the last span. Omit it and the last span stays
         open-ended rather than claiming a boundary that was never printed.
    Out: spans in TOC order. A span ends one page before the next one begins, even
         across a `SECTION` boundary (Appendix 7 ends where Section C's appendix A
         begins).
    """
    ordered = [entry for entry in entries if entry.kind == APPENDIX and entry.printed_page]
    ordered.sort(key=lambda entry: entry.printed_page or 0)

    spans: list[AppendixSpan] = []
    for index, entry in enumerate(ordered):
        following = ordered[index + 1].printed_page if index + 1 < len(ordered) else None
        end = last_printed_page if following is None else following - 1
        spans.append(
            AppendixSpan(
                part=entry.part,
                label=entry.label,
                title=entry.title,
                first_printed_page=entry.printed_page or 0,
                last_printed_page=end,
            )
        )
    return spans


def appendix_for_page(
    page: int,
    spans: list[AppendixSpan],
    *,
    coordinate: str = "printed",
) -> str | None:
    """Which appendix a page belongs to, or None for clause territory.

    In:  `page` — a page number; `spans` — from `appendix_spans`; `coordinate` —
         `"printed"` (the document's own page number, D42, and what
         `DocumentChunk.page` stores) or `"pdf"` (the viewer's index).
    Out: the canonical appendix label, or None.
    Fails: `ValueError` for any other coordinate. This is deliberate: an implicit
         one-page offset is exactly the silent error D42 exists to prevent.
    """
    if coordinate == "printed":
        printed = page
    elif coordinate == "pdf":
        printed = page - PRINTED_TO_PDF_OFFSET
    else:
        raise ValueError(
            f"coordinate must be 'printed' or 'pdf', got {coordinate!r}. "
            "They differ by one for SAOSO (D42); naming the one you mean is the point."
        )

    for span in spans:
        if span.contains_printed(printed):
            return span.label
    return None
