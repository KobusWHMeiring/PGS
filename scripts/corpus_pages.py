"""The page stream an artefact is drafted from — two renderings, repaired and flattened.

Split out of `scripts/build_corpus.py` when that file crossed the 30 KB cap. `build()`
decides what the artefact says; this module decides what its pages are:

- the geometry-first rendering (de-columned, then de-hyphenated) and the producer's own
  content-stream order, with `-raw`'s glued words repaired from `-layout`'s boundaries;
- the printed page number each PDF page carries (D42);
- the whitespace-free offsets a heading is found at, over whatever line stream the caller
  actually walks — the pages, or a parser's own body stream.

Nothing here decides content. A rule about what the artefact keeps belongs in
`build_corpus.py`, next to the review that has to diff it.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from knowledge.columns import apply_layout
from knowledge.corpus import flat
from knowledge.extraction import extract_pages
from knowledge.reflow import reflow_pages
from knowledge.sections.heading import page_stamp


def words(text: str) -> Counter:
    """The word multiset of a page, whitespace-normalised."""
    return Counter(flat(text).split())


def repair_glued(raw_page: str, layout_page: str) -> str:
    """Re-space `-raw`'s glued runs using `-layout`'s word boundaries.

    `-raw` preserves the producer's order but drops the spaces between text-show
    operations, so a line becomes `Sourcedlocallyfromneighbouring`. `-layout` has the
    spaces and the same characters; only its *order* is wrong on a column page. So the
    repair is a dictionary lookup, not a guess: each glued token is split into the run of
    consecutive `-layout` words that concatenate to exactly that token. A token with no
    such run is left alone, and the caller's multiset check then rejects the page rather
    than shipping a word nobody wrote.

    In:  `raw_page` — content-stream order; `layout_page` — the same page, de-columned.
    Out: the raw page's word order and line breaks, with the layout page's word
         boundaries. Line breaks must survive: they are what the section parsers detect
         headings on, and a flattened page parses to zero sections.
    Fails: never. Unrepairable tokens survive unchanged; the caller decides.
    """
    layout_words = flat(layout_page).split()
    known = set(layout_words)

    def repair_line(line: str) -> str:
        repaired: list[str] = []
        for token in line.split():
            if token in known:
                repaired.append(token)
                continue
            match: list[str] | None = None
            for start in range(len(layout_words)):
                joined = ""
                for end in range(start, len(layout_words)):
                    joined += layout_words[end]
                    if len(joined) > len(token):
                        break
                    if joined == token:
                        match = layout_words[start : end + 1]
                        break
                if match is not None:
                    break
            repaired.append(" ".join(match) if match is not None else token)
        return " ".join(repaired)

    return "\n".join(repair_line(line) for line in raw_page.split("\n"))


def choose_pages(laid: list[str], raw: list[str]) -> tuple[list[str], tuple[int, ...]]:
    """Which of the two renderings each page's text comes from, and which pages used `-raw`.

    In:  `laid` — the geometry-first pages (de-columned, de-hyphenated); `raw` — the producer's
         content-stream pages.
    Out: the chosen pages, and the 1-based numbers of those taken from `raw`.
    Fails: never. Two renderings that disagree about the page *count* are not mixed: pairing page 3
         of one with page 3 of the other is only sound while both have the same pages.

    Split out of `pages_of()` so the decision is testable without a PDF: the gate runs with
    `PDFTOTEXT_BIN=/usr/bin/true` (`testing_hazards.md` §2.9), and S3's emitter is proved against a
    body stream built from committed fixtures — which is only the generator's stream if this
    function is the generator's function.
    """
    if len(raw) != len(laid):
        return list(laid), ()
    chosen: list[str] = []
    used: list[int] = []
    for number, (geometry, stream) in enumerate(zip(laid, raw), 1):
        fixed = repair_glued(stream, geometry)
        if words(geometry) == words(fixed):
            chosen.append(fixed)
            used.append(number)
        else:
            chosen.append(geometry)
    return chosen, tuple(used)


def substitute_pass(
    lines: list[tuple[int, str]],
    pass_pages: dict[int, str],
    wanted: set[int],
    keep=None,
) -> list[tuple[int, str]]:
    """Replace the lines of `wanted` pages with the same pages from another extraction pass.

    In:  `lines` — `(pdf page, text)` in document order, one run per page; `pass_pages` — the other
         pass's page text, keyed by 1-based PDF page; `wanted` — the pages to take from it; `keep` —
         the document's body filter, applied to the substituted lines so the two passes carry the
         same furniture rule.
    Out: the same stream with each wanted page's lines replaced, in place.
    Fails: never. A wanted page the other pass does not have is left as it arrived — the emitter
         will then refuse the cell it cannot find, which is the loud outcome.

    **Why this exists (S5).** A block records the extraction its cells came from
    (`extraction: table|layout|raw`), and the gate judges the cells against *that* pass
    (`scripts/check_tables.py` → `page_fixtures.pages(doc, mode)`). Until S5 the generator sliced
    every section from the geometry stream regardless, so a `-table` block was assembled from
    `-layout` text and judged against `-table` text: one of the two was always wrong. The
    landscape's page-4 header is the measured case — `-raw` content-stream order put the five
    column labels on lines of their own and the emitter refused at `column 1` (2026-11-05).

    The page's *printed* number is not disturbed: `stamps` is computed from the geometry pass, and
    a page's stamp does not depend on which rendering its words came from.
    """
    out: list[tuple[int, str]] = []
    previous: int | None = None
    for page, text in lines:
        if page not in wanted:
            out.append((page, text))
            previous = page
            continue
        if page == previous:
            # The rest of a run already substituted: those lines are the pass's now.
            continue
        replacement = pass_pages.get(page)
        if replacement is None:
            out.append((page, text))
            previous = page
            continue
        new_lines = replacement.split("\n")
        if keep is not None:
            new_lines = [line for line in new_lines if keep(line)]
        out.extend((page, line) for line in new_lines)
        previous = page
    return out


NEWLINE = chr(10)
FORMFEED = chr(12)


def pass_texts(parser, pdf_path: Path, wanted: dict[str, set[int]]) -> dict[str, dict[int, str]]:
    """`mode -> {pdf page: the page's body lines, as this document's parser slices them}`.

    In:  `parser` — the document's section parser; `pdf_path` — the PDF; `wanted` — which pages
         each extraction pass must supply.
    Out: one page-text map per pass, ready for `substitute_pass`.
    Fails: whatever `pdftotext` fails with — a build-time act, not the gate (requirement 10).

    **Sliced through the document's own rule, not a second one.** A parser that declares
    `body_lines` (SAOSO) owns its furniture judgement: the running part banner, the printed page
    number and the appendix head are all decided there. Applying only `body_filter` to a
    substituted page put `SECTION B` and the repeated `APPENDIX 6a:` title into the section
    (measured 2026-11-05). One rule, two renderings.
    """
    out: dict[str, dict[int, str]] = {}
    body_lines = getattr(parser, "body_lines", None)
    for mode in wanted:
        alt = extract_pages(pdf_path, mode=mode)
        if body_lines is None:
            out[mode] = dict(enumerate(alt, 1))
            continue
        grouped: dict[int, list[str]] = {}
        for pdf_page, _number, line in body_lines(FORMFEED.join(alt)):
            grouped.setdefault(pdf_page, []).append(line)
        out[mode] = {page: NEWLINE.join(lines) for page, lines in grouped.items()}
    return out


def pages_of(
    pdf_path: Path, doc_key: str, *, raw_fallback: bool = True
) -> tuple[list[str], tuple[int, ...], dict[int, int | None]]:
    """The pages the artefact is drafted from, and which of them used `-raw`.

    Two renderings are computed here: the geometry-first one (de-columned, then
    de-hyphenated) and the producer's own content-stream order. `-raw` loses the spaces
    between text-show operations, so it glues words on some pages
    (`Sourcedlocallyfromneighbouring`); where it does **not** — where its word multiset is
    identical to the geometry path's — its order is authoritative and needs no band at
    all. Measured on the shipped BPP (2026-10-22): 8 of 13 pages qualify, including 3 and 6,
    the two pages whose columns defeat the detector. The choice is recorded in the header
    so a reader can see which pages were reconstructed rather than de-columned.

    Out: `(pages, raw_pages, stamps)`. `raw_pages` is empty when nothing was substituted;
         `stamps` maps PDF page to the number the document prints there, computed from the
         **de-columned** page — D42's rule was measured on that rendering, and the two
         renderings disagree exactly where the stamp shares a line with body text (BPP
         page 3, where `-raw` puts `02` alone and `-layout` glues it to the footnote, which
         would have given the INTRODUCTION a page number it does not print).
    """
    laid, _ = apply_layout(extract_pages(pdf_path), doc_key=doc_key)
    laid, _ = reflow_pages(laid)
    stamps = {number: page_stamp(page) for number, page in enumerate(laid, 1)}
    if not raw_fallback:
        return laid, (), stamps
    raw, _ = reflow_pages(extract_pages(pdf_path, mode="raw"))
    chosen, used = choose_pages(laid, raw)
    return chosen, used, stamps


def flatten(pages: list[str]) -> tuple[list[tuple[int, str]], list[int], str]:
    """Every line with its page, plus the whitespace-free offsets used to find headings.

    Out: `(lines, starts, norm)` where `lines[i] == (pdf_page, text)`, `starts[i]` is the
    offset of line i in `norm`, and `norm` is the whole document with every whitespace
    character removed. Normalising here rather than matching printed text is what makes a
    heading split across lines (`DEFINITION OF ORGANIC` / `AGRICULTURE`) findable.
    """
    lines = [
        (number, line)
        for number, page in enumerate(pages, 1)
        for line in page.split("\n")
    ]
    starts, norm = offsets(lines)
    return lines, starts, norm


def offsets(lines: list[tuple[int, str]]) -> tuple[list[int], str]:
    """The whitespace-free offsets of an explicit line stream, and its squashed text.

    Split out of `flatten` because the SAOSO artefact is sliced from the *parser's* body
    stream rather than from every page (see `SaosoParser.body_lines`): the offsets must
    describe the lines the generator actually walks, or `locate_sections` searches one
    document and slices another.
    """
    starts: list[int] = []
    chunks: list[str] = []
    offset = 0
    for _, line in lines:
        starts.append(offset)
        squashed = "".join(line.split())
        chunks.append(squashed)
        offset += len(squashed)
    return starts, "".join(chunks)


