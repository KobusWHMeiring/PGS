"""The Outeniqua OPP's section scheme — `V.`, `4.2`, items `1)`, letters `a.` (§4.5, D15).

The OPP is the hardest of the three formats, and every difficulty below was found by
running the parser against the fixture rather than by reading the document.

**Headings are indented 0–7 columns.** `V. Seals` is at column 0 and `VI.` at indent
6, so a column-0 regex loses the two sections the review actually added. `4.1`–`4.7`
sit at indent 0 or 4.

**Three item markers exist**: `1.` in §4.1, `1)` in §4.2, `a.` in §4.5(2).

**§4.5's outer items are 1, 2, 4, 5 — and a nested list is why.** The (2)(c) attendee
list restarts at `1.` and runs to `3.`, at the same indentation as the outer items, so
the marker numbers alone cannot separate the lists: `3.` is an attendee, not item 3.
What separates them is that the *page layout shifts*: items 4 and 5 begin at column 0
because the p6→p7 break reset the left margin, while the attendee list stays at indent
4. The rule implemented here is therefore structural — **a numeric list opened inside
another closes only on a dedent below its own indent** — and it is calibrated to this
document's printed layout, not derived from a numbering convention. It is worth
knowing that the plan's own `ITEM` regex (`^\\s{2,}`) drops items 4 and 5 entirely
*and* manufactures `4.5(3)` out of the third attendee; that is why
`test_missing_item_number_is_reported_not_invented` asserts the absence of 3 **and** the
presence of 4 and 5.

Nested numeric items are deliberately **not** emitted as `sub_refs`: `4.5(2)(c)(1)`
would be depth four, which D15 forbids and the source does not support.

`sub_refs` are emitted for decimal sections only. A Roman numeral section has no
printed item numbering (`V(1)` is not a form the OPP uses), so inventing one would
repeat the `B.20.1.1` mistake in a new shape.

The unnumbered blocks (`Action: First warning…`, `Examples of serious misconduct are:`)
take a content-derived `anchor` in the spec's plan (`4.5#action-first-warning`). That is
**not implemented in B2** — these are body text inside item 5, and they are locatable
through `§4.5` plus `sub_ref 4.5(5)`. If a later slice needs to cite them individually,
that is the place to add anchors, not by fabricating item numbers.
"""

from __future__ import annotations

import re

from knowledge.sections import (
    ParsedSection,
    any_level_end,
    line_offsets,
)

#: `V. Seals …` at indent 0–7. Column 0 alone misses `VI.` at indent 6 (reality 5).
ROMAN = re.compile(r"^\s{0,7}([IVX]+)\.\s+(\S.*)$")

#: `4.5 Non-compliance and discipline:` at indent 0–7.
SUB = re.compile(r"^\s{0,7}(\d{1,2}\.\d{1,2})\s+(\S.*)$")

#: Items (`1.`, `1)`) at any indent — §4.5's items 4 and 5 are at column 0.
ITEM = re.compile(r"^(\s*)(\d{1,2})[.)]\s+\S")

#: Letters (`a.`, `b.`) indented 8+, which is how §4.5(2) and §4.5(5) print them.
LET = re.compile(r"^(\s{8,})([a-z])\.\s+\S")

#: The OPP stamps a bare page number on a line of its own, and unlike SAOSO it
#: prints no `Page |` label. `printed == PDF index` for this document (A10's
#: `opp_4_1` is PDF page 4 and stamps 4), so D42's printed-page rule needs no offset
#: here — but the stamp is still what is read, so a future edition with a cover is
#: handled by the same code.
BARE_PAGE = re.compile(r"^\d{1,3}$")


class OppParser:
    """Parse the OPP into cited sections and enumerated `sub_refs`."""

    scheme = "opp"

    def parse(self, text: str, **_: object) -> list[ParsedSection]:
        """In:  `text` — `pdftotext -layout` output, form-feed separated.
        Out: sections in document order. Roman sections cite `§V`; decimal sections
             cite `§4.5` and carry `sub_refs` (`4.5(2)(c)`).
        """
        sections: list[ParsedSection] = []
        stack: list[tuple[int, str]] = []
        current: dict | None = None
        printed: int | None = None

        def flush() -> None:
            nonlocal current
            if current is None:
                return
            body = current["body"]
            if body and body[-1] == "":
                body.pop()
            lines = [current["heading"], *body]
            offsets, text_length = line_offsets(lines)
            subs: tuple = ()
            if current["base"] is not None:
                subs = tuple(any_level_end(current["markers"], offsets, text_length))
            sections.append(
                ParsedSection(
                    section_ref=current["ref"],
                    text="\n".join(lines),
                    heading_path=" > ".join(title for _, title in stack[:-1]),
                    page=current["page"],
                    sub_refs=subs,
                )
            )
            current = None

        for raw_page in text.split("\f"):
            stamp = self._page_stamp(raw_page)
            if stamp is not None:
                printed = stamp
            elif printed is not None:
                printed += 1

            for line in raw_page.splitlines():
                if BARE_PAGE.match(line.strip()):
                    continue  # the page stamp, not content

                heading = self._as_heading(line)
                if heading is not None:
                    flush()
                    depth, ref, base = heading
                    while stack and stack[-1][0] >= depth:
                        stack.pop()
                    stack.append((depth, line.strip()))
                    current = {
                        "ref": ref,
                        "base": base,
                        "heading": line.strip(),
                        "page": printed,
                        "body": [],
                        "markers": [],
                        "item": None,        # last top-level item number
                        "nested": None,      # indent of an open nested numeric list
                    }
                    continue

                if current is None:
                    continue

                # Marker lines are content too, so every line is appended and the
                # marker is registered against the index it will occupy. Registering
                # from `len(body)` *before* appending is what keeps the offsets exact:
                # consumed-but-unappended lines made every following marker share one
                # line index, and a `sub_ref` whose slice was empty.
                line_index = len(current["body"]) + 1  # heading occupies index 0
                self._consume_marker(current, line, line_index)
                current["body"].append(line)

        flush()
        return sections

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _page_stamp(page_text: str) -> int | None:
        """The bare page number printed on this page, if it has one."""
        for line in page_text.splitlines():
            if BARE_PAGE.match(line.strip()):
                return int(line.strip())
        return None

    def _as_heading(self, line: str) -> tuple[int, str, str | None] | None:
        """Out: `(depth, section_ref, base_for_sub_refs)` or None.

        `base_for_sub_refs` is the plain reference (`4.5`) for a decimal section and
        None for a Roman one, which has no printed item numbering.
        """
        roman = ROMAN.match(line)
        if roman:
            return 1, f"§{roman.group(1)}", None
        sub = SUB.match(line)
        if sub:
            return 2, f"§{sub.group(1)}", sub.group(1)
        return None

    def _consume_marker(self, current: dict, line: str, line_index: int) -> None:
        """Register an item/letter as a `sub_ref`. Body text registers nothing.

        The nested-list rule lives here. See the module docstring: while a nested
        numeric list is open, a marker is nested unless it *dedents* below the
        nested list's indent.
        """
        if current["base"] is None:
            return

        item = ITEM.match(line)
        if item:
            indent = len(item.group(1))
            number = int(item.group(2))
            nested = current["nested"]

            if nested is not None and indent < nested:
                current["nested"] = None      # the outer list resumes
                nested = None

            if nested is not None:
                return                         # a nested item: content, not a citation

            top = current["item"]
            if top is None or number > top:
                current["item"] = number
                current["markers"].append(
                    (f"{current['base']}({number})", 2, line_index)
                )
                return

            # A number that goes backwards opens a nested list (the attendee list).
            current["nested"] = indent
            return

        letter = LET.match(line)
        if letter and current["item"] is not None:
            current["markers"].append(
                (
                    f"{current['base']}({current['item']})({letter.group(2)})",
                    3,
                    line_index,
                )
            )


__all__ = ["BARE_PAGE", "ITEM", "LET", "OppParser", "ROMAN", "SUB"]
