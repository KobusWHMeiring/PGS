#!/usr/bin/env python
"""Generate a canonical corpus artefact from a governed PDF (D53).

This is the *only* place layout heuristics still run. It produces a first draft of
`knowledge/corpus/<doc_key>.md` from the PDF and a human then reviews that draft against
the paper. The reviewed artefact — not the heuristic — is what `ingest_standard` reads
when it is told to, so a layout defect stops being a production bug in the chatbot and
becomes a line in a diff.

Why a draft rather than hand-authored text: a hand-typed corpus encodes the same
assumption as its reviewer and has no provenance at all. Every block this emits carries
the PDF page it starts on, and `knowledge/tests/test_corpus_bpp.py` checks that the block
really is on paper there — so the review has a queue (the blocks that fail) instead of
being an open-ended read.

    python scripts/build_corpus.py --doc bpp
    python scripts/build_corpus.py --doc bpp --force   # overwrite a reviewed artefact

Four rules that matter:

1. **Never overwrite a reviewed artefact without `--force`.** The generator cannot tell a
   fresh draft from a file a human corrected; only the operator can, so the default is to
   refuse rather than to quietly undo a review.
2. **No timestamps.** Output is a function of the PDF and the generator version, so
   re-running produces a byte-identical file and a new edition produces a reviewable diff.
   The review date belongs in git, not in the artefact.
3. **Paragraphs come from the page, not from the parser.** `HeadingParser` skips blank
   lines, so its section text is one unbroken run. The blank lines are the chunker's
   preferred boundary and the reviewer's unit, so this walks the de-columned pages
   directly and uses the parser only for *which headings exist, in what order*.
4. **Furniture never reaches the artefact.** Registration block, page footer and the
   printed page number are dropped here, exactly as the parsers drop them.
"""

from __future__ import annotations

import argparse
import bisect
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# `CORPUS_DOCUMENTS` lives beside the ingest service, which imports the models, so this
# developer tool needs settings configured even though it touches no database. (A later
# slice should move the document descriptors into a Django-free module; recorded in
# `product/backlog/In Progress/CORPUS_CANONICAL_FORMAT_PRD.md` rather than fixed here.)
import os  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")

import django  # noqa: E402

django.setup()

from knowledge.chunking import chunk_sections  # noqa: E402
from knowledge.columns import apply_layout  # noqa: E402
from knowledge.corpus import CORPUS_EDITS, flat  # noqa: E402
from knowledge.extraction import extract_pages, sha256_of  # noqa: E402
from knowledge.ingest import CORPUS_DOCUMENTS  # noqa: E402
from knowledge.reflow import reflow_pages  # noqa: E402
from knowledge.sections import is_furniture, registry  # noqa: E402
from knowledge.sections.heading import page_stamp  # noqa: E402

CORPUS_DIR = REPO_ROOT / "knowledge" / "corpus"

#: The four governed PDFs, by corpus key. Duplicated from `scripts/extract_fixtures.py`
#: deliberately: a shared map would live in `knowledge/`, and the library must not know
#: where tools keep their files.
PDF_FILES = {
    "saoso": "saoso-version-2.1-2026.pdf",
    "opp": "Outeniqua pgs principles, policies and procedures 2026.pdf",
    "bpp": "Basic Production Principles_ENG_PRINT.pdf",
    "landscape": "PGS Certification landscape_Final.pdf",
}

#: Documents whose `-raw` rendering is unusable even on pages where its word multiset
#: matches. SAOSO is printed double-spaced in one column, so Xpdf's content-stream order
#: leaves the page word-for-word identical but line-broken so that no heading can be found
#: by the clause parser (measured 2026-10-28: `--doc saoso` with the fallback on parsed
#: **zero** sections). The flag is still available; it is not the default for these.
RAW_FALLBACK_OFF = {"saoso"}

#: Bump when the *shape* of the artefact changes (annotations, block rules). The value is
#: written into every header, so a file produced by an older generator is visibly stale.
GENERATOR = "knowledge corpusgen v2"


#: A line that is nothing but a printed page number (`02`, `8`).
BARE_PAGE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$")


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
    if len(raw) != len(laid):  # pragma: no cover - the two modes always agree
        return laid, (), stamps
    chosen: list[str] = []
    used: list[int] = []
    for number, (geometry, stream) in enumerate(zip(laid, raw), 1):
        fixed = repair_glued(stream, geometry)
        if words(geometry) == words(fixed):
            chosen.append(fixed)
            used.append(number)
        else:
            chosen.append(geometry)
    return chosen, tuple(used), stamps


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


def locate_sections(
    sections: list, lines: list[tuple[int, str]], starts: list[int], norm: str
) -> list[tuple[int, int]]:
    """`(first_line, last_line)` of each section's **heading**, in document order.

    Sections partition the document, so each heading is searched for forward from the end
    of the previous one. A heading the parser produced but the page does not contain is a
    contradiction, and this stops rather than guessing.
    """
    spans: list[tuple[int, int]] = []
    cursor = 0
    for section in sections:
        heading = section.text.partition("\n")[0]
        needle = "".join(heading.split())
        found = norm.find(needle, cursor)
        if found < 0:
            raise SystemExit(
                f"the parser emitted heading {heading!r} but the document does not "
                f"contain it from offset {cursor}. Fix the parser or the transform "
                "before generating an artefact from it."
            )
        first = bisect.bisect_right(starts, found) - 1
        last = bisect.bisect_right(starts, found + len(needle) - 1) - 1
        spans.append((first, last))
        cursor = found + len(needle)
    return spans


def body_filter(parser) -> "callable":
    """Which lines of the body stream this document's artefact keeps.

    In:  `parser` — the section parser the document's scheme selects.
    Out: a predicate over one line.
    Fails: never.

    **This was a one-word bug, and it emptied the draft.** Measured 2026-10-30: the generic
    branch read `keep = is_page_furniture` — a helper whose docstring began *"Content the artefact
    must not carry"*, i.e. the predicate was inverted — so `--doc landscape` wrote five headings and
    the page stamps with no body text, and `--doc opp` (P4's blocked step) would have done the same. Every guard stayed green
    because an empty artefact has nothing that can be wrong. `tests/tools/test_build_corpus.py`
    pins the four decisions, and the second one is the easy one to get wrong: **a blank line is
    content**, because it is the chunker's paragraph boundary (`build_corpus.py` rule 3).

    A parser that declares `body_lines` owns its own furniture judgement — SAOSO's page is printed
    double-spaced and a lone digit there is a superscript or a table cell, not a page stamp — so
    the page-stamp rule must not be applied on top of it.
    """
    if getattr(parser, "body_lines", None) is not None:
        return lambda line: not is_furniture(line)
    return lambda line: not (is_furniture(line) or BARE_PAGE_NUMBER.match(line))


def build(pdf_path: Path, doc_key: str, *, raw_fallback: bool = True) -> str:
    """The artefact text for one document."""
    descriptor = CORPUS_DOCUMENTS[doc_key]
    pages, raw_pages, printed = pages_of(pdf_path, doc_key, raw_fallback=raw_fallback)
    parser = registry.get(descriptor["section_scheme"])
    joined = "\f".join(pages)
    sections = parser.parse(joined)
    if not sections:
        raise SystemExit(f"{pdf_path.name} parsed to zero sections; nothing to write")

    # Slice from the stream the **parser** reads. A parser that declares `body_lines`
    # knows which pages are this document's body (SAOSO: Part B only, the TOC skipped) and
    # which lines are furniture; slicing every page instead produced a draft that carried
    # other parts' text into sections and repeated Section C three times
    # (`SaosoParser.body_lines`).
    body_lines = getattr(parser, "body_lines", None)
    if body_lines is not None:
        stream = body_lines(joined)
        lines = [(pdf_page, line) for pdf_page, _page_number, line in stream]
        printed = {pdf_page: number for pdf_page, number, _line in stream}
    else:
        lines, _starts, _norm = flatten(pages)
    # The parser's own furniture rule where it has one, the page's where it does not — and the
    # reason that distinction exists is in `body_filter`.
    keep = body_filter(parser)
    starts, norm = offsets(lines)
    spans = locate_sections(sections, lines, starts, norm)

    out: list[str] = [
        "<!-- corpus",
        f"doc_key: {doc_key}",
        f"source: {pdf_path.relative_to(REPO_ROOT).as_posix()}",
        f"sha256: {sha256_of(pdf_path)}",
        f"generator: {GENERATOR}",
        f"raw_pages: {','.join(str(n) for n in raw_pages) or 'none'}",
        "-->",
    ]

    current_page: int | None = None

    def marker(number: int) -> str:
        value = printed.get(number)
        return (
            f"<!-- page: {number} "
            f"printed: {'none' if value is None else value} -->"
        )

    for index, section in enumerate(sections):
        heading_line, _ = spans[index]
        body_start = spans[index][1] + 1
        body_end = spans[index + 1][0] if index + 1 < len(spans) else len(lines)
        heading_page = lines[heading_line][0]
        if heading_page != current_page:
            out.append(marker(heading_page))
            current_page = heading_page
        if section.section_ref:
            out.append(f"<!-- ref: {section.section_ref} -->")
        # An appendix's heading is its *canonical label*, not the printed form: the paper
        # prints `APPENDIX 6a:`, `APPENDIX 4, TABLE 1` and `APPENDIX 5` four different ways,
        # while the toc — the source of the label — prints one. The parser uses the label as
        # the section's `heading_path` (it is the only name an appendix has), so writing the
        # printed form here would make the artefact's tree label differ from the parser's.
        title = (
            section.heading_path
            if section.heading_path == section.section_ref
            else section.text.partition(chr(10))[0]
        )
        depth = section.heading_path.count(" > ") + 2
        out.append(f"{'#' * depth} {title}")

        for number, line in lines[body_start:body_end]:
            if not keep(line):
                continue
            if number != current_page:
                out.append(marker(number))
                current_page = number
            out.append(line.rstrip())

    text = "\n".join(out) + "\n"
    # Collapse runs of blank lines to one: a page break between two paragraphs must not
    # invent a second boundary the chunker would treat as a separate paragraph.
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return apply_review(text, CORPUS_EDITS.get(doc_key, ()))


def apply_review(text: str, edits) -> str:
    """Apply the reviewed corrections (`CORPUS_EDITS`) to a freshly generated artefact.

    In: the draft text and the document's reviewed edits. Out: the text with each edit's
    `replacement` in place of its `original`.
    Fails: `SystemExit` when an edit matches nothing or matches more than once — a review
    that no longer applies is a review of a different document, and regenerating on a reprint
    must fail loudly rather than quietly drop a correction a person made.

    Why here and not as a hand edit: a reprint regenerates this file, and a correction that
    only lives in the working tree is lost the first time somebody runs `--force`. The edits
    are data (`knowledge/corpus.py`), the generator applies them, and
    `knowledge/tests/test_corpus_saoso.py` still proves each one was necessary and applied.

    The match is **whitespace-tolerant**, because a correction can join lines: the `m²`
    superscript sits on its own line, so the edit names the sentence by its words.
    """
    for edit in edits:
        if not edit.replacement:
            continue
        pattern = re.compile(
            r"\s+".join(re.escape(word) for word in flat(edit.original).split())
        )
        text, replaced = pattern.subn(flat(edit.replacement), text, count=1)
        if replaced != 1:
            raise SystemExit(
                f"the reviewed edit for PDF page {edit.page} matched {replaced} times in the "
                f"draft: {edit.original[:60]!r}. A reprint has moved the text — re-review it "
                "rather than deleting the edit."
            )
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", required=True, choices=sorted(CORPUS_DOCUMENTS))
    parser.add_argument("--file", help="The PDF. Defaults to pgs_docs/ via the doc key.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing artefact. Required, because a human reviews these.",
    )
    parser.add_argument("--stdout", action="store_true", help="Print instead of writing.")
    parser.add_argument(
        "--no-raw-fallback",
        action="store_true",
        help=(
            "Use only the de-columned text. The fallback is on by default because it is "
            "measured: it fires only on pages where `-raw` is word-for-word identical to "
            "the de-columned page, and those are the pages whose columns defeat the band "
            "detector. Documents in RAW_FALLBACK_OFF (SAOSO) start without it."
        ),
    )
    args = parser.parse_args(argv)

    pdf_path = (
        Path(args.file)
        if args.file
        else REPO_ROOT / "pgs_docs" / PDF_FILES[args.doc]
    )
    if not pdf_path.exists():
        raise SystemExit(f"no such PDF: {pdf_path}")

    target = CORPUS_DIR / f"{args.doc}.md"
    raw_fallback = not args.no_raw_fallback and args.doc not in RAW_FALLBACK_OFF
    text = build(pdf_path, args.doc, raw_fallback=raw_fallback)
    if args.stdout:
        sys.stdout.write(text)
        return 0
    if target.exists() and not args.force:
        raise SystemExit(
            f"{target.relative_to(REPO_ROOT)} already exists and may have been reviewed. "
            "Pass --force to regenerate it — and expect the diff to be the review."
        )
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    # `newline=""` is load-bearing: on Windows `write_text` translates a line feed to
    # carriage-return + line feed, so the same PDF and generator would produce a different
    # artefact (and a different sha256) on the VPS. The fixtures already pin this rule.
    with open(target, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)

    pages, raw_pages, _ = pages_of(pdf_path, args.doc, raw_fallback=raw_fallback)
    sections = registry.get(CORPUS_DOCUMENTS[args.doc]["section_scheme"]).parse(
        "\f".join(pages)
    )
    print(
        f"{target.relative_to(REPO_ROOT)}: {text.count('<!-- page:')} page markers, "
        f"{len(sections)} sections, {len(chunk_sections(sections))} chunks, "
        f"{len(raw_pages)} raw pages, {len(text)} chars"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
