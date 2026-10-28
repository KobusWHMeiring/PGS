"""The SAOSO artefact: reviewed, traceable, and equivalent to the PDF path (D53, P6).

This is the guard that makes a 101-page transcription trustworthy. It answers the same four
questions `test_corpus_bpp.py` asks, plus the five defects the artefact exists to fix
(`BugFixes/saoso_text_glyphs_and_boundaries.md` §2–§5):

1. **Is it the same document?** The header's sha256 is the PDF's, every section identity is
   the parser's, and every section's text is the PDF path's text — the difference is exactly
   the reviewed edits, and nothing else.
2. **Is every block on the page it names?** A block nobody can find on paper is a quote the
   chatbot must never emit.
3. **Was every correction necessary, and applied?** Each `CorpusEdit` is data: its
   `original` must be in the PDF-derived text for that page, and its `replacement` must be
   in the artefact. A correction nobody can justify is a failing test.
4. **Are the defects actually gone?** No part banner survives inside a branch, no letterspaced
   run survives, and the `m²` sentence reads whole.

**What is deliberately not the same.** For an appendix section the PDF parser leaves `anchor`
empty (the label is the locator), while the artefact derives an anchor from the heading text.
Nothing resolves through a section anchor when a `section_ref` exists — `reading_anchor`
prefers the reference — and the reader's branch anchors are unchanged (`test_anchors.py`,
`test_document_reader.py`). The identity guard therefore pins `(ref, page, heading_path)`,
which is what a citation resolves through.
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

import pytest

from knowledge.chunking import chunk_sections
from knowledge.columns import apply_layout
from knowledge.corpus import CORPUS_EDITS, flat, load_document
from knowledge.extraction import sha256_of
from knowledge.passages import flatten, passage_blocks
from knowledge.reflow import reflow_pages
from knowledge.sections.saoso import SaosoParser
from knowledge.tests.page_fixtures import pages

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF = REPO_ROOT / "pgs_docs" / "saoso-version-2.1-2026.pdf"
ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "saoso.md"

#: Measured 2026-10-28: three corrections in 101 pages. A ratchet, not a budget — the review
#: found what it found, and the number may only go down without a reason recorded in the bug.
MAX_EDITS = 3

HASH = re.compile(r"^#{1,6}[ \t]+", re.MULTILINE)

#: A run of three or more single-character words: a tracked (letterspaced) line as the text
#: layer emits it. Measured: three such runs before the review, none after.
LETTERSPACED = re.compile(r"(?<!\w)\w( \w){3,}")


@pytest.fixture(scope="module")
def document():
    return load_document(ARTEFACT)


@pytest.fixture(scope="module")
def pdf_pages():
    laid, _ = apply_layout(pages("saoso"), doc_key="saoso")
    laid, _ = reflow_pages(laid)
    return laid


@pytest.fixture(scope="module")
def pdf_sections(pdf_pages):
    return SaosoParser().parse("\f".join(pdf_pages))


def chars(text: str) -> collections.Counter:
    return collections.Counter("".join(text.split()))


def body_text(document) -> str:
    return flat(" ".join(block.text for block in document.blocks))


def squash(text: str) -> str:
    return "".join((text or "").split())


def section_text(section) -> str:
    """A section's text with the Markdown heading prefix removed — the words alone."""
    return HASH.sub("", section.text)


def on_page(block: str, laid: list[str], start: int, span: int = 2) -> bool:
    needle = squash(block)
    return any(
        needle in squash(" ".join(laid[start - 1 : start - 1 + width]))
        for width in range(1, span + 1)
    )


# --- 1. It is the same document ---------------------------------------------


def test_the_header_is_the_shipped_pdf(document):
    assert document.source == "pgs_docs/saoso-version-2.1-2026.pdf"
    assert document.sha256 == sha256_of(PDF)
    assert document.generator.startswith("knowledge corpusgen")
    assert document.extra.get("raw_pages") == "none", (
        "SAOSO is one double-spaced column: the `-raw` fallback glues its pages so no heading "
        "can be found, so the artefact must record that it was not used"
    )


def test_the_page_markers_are_monotonic_and_inside_the_document(document, pdf_pages):
    marked = [block.page for block in document.blocks]
    assert marked == sorted(marked), "a page marker went backwards"
    assert max(marked) <= len(pdf_pages)
    assert len(set(marked)) >= 60, "the artefact lost most of its page markers"


def test_every_section_keeps_the_parsers_identity(document, pdf_sections):
    """A citation resolves through `section_ref` and the branch through `heading_path`."""
    def identity(section):
        return (section.section_ref, section.page, section.heading_path)

    assert [identity(s) for s in document.sections] == [identity(s) for s in pdf_sections]
    assert len(document.sections) == 271, "the parser's section count changed — re-measure"


def test_every_section_says_what_the_pdf_path_says(document, pdf_sections):
    """The difference must be exactly the reviewed edits, named section by section.

    A whole-document comparison would pass while two sections swapped text; this names the
    section, so the failure says where to look.
    """
    differing = []
    for theirs, ours in zip(pdf_sections, document.sections):
        # **Body only.** A heading is structure in the artefact (Markdown) and text in the PDF
        # path, and an appendix's artefact heading is its canonical label rather than the
        # printed form (`APPENDIX 6a:` → `Appendix 6a`). That difference is pinned by the
        # identity test above; what must not differ is a word of the body.
        expected = flat(theirs.text.partition(chr(10))[2])
        # Matched by containment, not by page: `CorpusEdit.page` is a **PDF** page (what the
        # traceability test checks against), while `section.page` is the number the paper
        # prints. Most of this document prints `pdf - 1`.
        for edit in CORPUS_EDITS["saoso"]:
            if edit.replacement:
                expected = expected.replace(flat(edit.original), flat(edit.replacement))
        actual = flat(section_text(ours).partition(chr(10))[2])
        if expected != actual:
            differing.append((theirs.section_ref, expected, actual))

    assert [ref for ref, _e, _a in differing] == [], (
        "the artefact differs from the PDF path outside the reviewed edits: "
        f"{[ref for ref, _e, _a in differing][:6]}"
    )


def test_the_artefact_carries_every_character_the_pdf_path_produces(document, pdf_sections):
    """Character multiset, so a moved word is not invented text (see `test_corpus_bpp`)."""
    expected = collections.Counter()
    for section in pdf_sections:
        # Body only: the artefact carries headings as Markdown, and a heading is structure
        # rather than text (`body_text` excludes them on both sides).
        expected.update(chars(section_text(section).partition(chr(10))[2]))
    for edit in CORPUS_EDITS["saoso"]:
        expected.subtract(chars(edit.original))
        expected.update(chars(edit.replacement))
    expected = +expected

    actual = chars(body_text(document))
    assert not expected - actual, f"the artefact dropped characters: {dict(expected - actual)}"
    assert not actual - expected, f"the artefact invented characters: {dict(actual - expected)}"


def test_the_artefact_yields_the_parsers_chunks(document, pdf_sections):
    """Chunk count and refs, before the reviewed tables replace a section's chunks."""
    theirs = chunk_sections(list(pdf_sections))
    ours = chunk_sections(list(document.sections))

    assert len(ours) == len(theirs)
    assert [c.section_ref for c in ours] == [c.section_ref for c in theirs]


# --- 2. Every block is on the page it names ---------------------------------


def test_every_block_is_on_the_page_it_names(document, pdf_pages):
    replacements = collections.defaultdict(list)
    for edit in CORPUS_EDITS["saoso"]:
        if edit.replacement:
            replacements[edit.page].append(squash(edit.replacement))

    untraceable = []
    for block in document.blocks:
        if on_page(block.text, pdf_pages, block.page):
            continue
        if any(replacement in squash(block.text) for replacement in replacements[block.page]):
            continue
        untraceable.append((block.page, flat(block.text)[:90]))
    assert untraceable == []


# --- 3. Every correction was necessary, and applied -------------------------


@pytest.mark.parametrize("edit", CORPUS_EDITS["saoso"], ids=lambda e: f"page-{e.page}")
def test_each_edit_was_necessary(edit, pdf_pages):
    assert flat(edit.original) in flat(pdf_pages[edit.page - 1]), (
        f"page {edit.page}: the edit claims to repair {edit.original[:60]!r}, which is not "
        "in the PDF's text for that page. A stale edit is a change nobody can justify."
    )


@pytest.mark.parametrize("edit", CORPUS_EDITS["saoso"], ids=lambda e: f"page-{e.page}")
def test_each_edit_was_applied(edit, document):
    assert flat(edit.replacement) in body_text(document), (
        f"page {edit.page}: {edit.replacement[:60]!r} is not in the artefact"
    )


def test_the_reviewed_edits_do_not_grow_without_a_reason():
    assert len(CORPUS_EDITS["saoso"]) <= MAX_EDITS


# --- 4. The defects the artefact exists to fix are gone ---------------------


def test_no_part_banner_survives_inside_a_branch(document):
    """§3: `SECTION B` and the part title closed twelve branches and opened nothing.

    The banner is the page's running head, printed on every page of the part. The parser
    now drops it (`SaosoParser.body_lines`), so neither path may carry it as text.
    """
    carriers = [
        section.section_ref
        for section in document.sections
        if re.search(r"\bSECTION [A-C]\b", section.text)
    ]
    assert carriers == [], f"a part banner is still a section's text: {carriers}"


def test_no_letterspaced_run_survives(document):
    """§4: three tracked words were extracted one token per letter, so they matched nothing."""
    runs = [
        (section.section_ref, match.group(0))
        for section in document.sections
        for match in LETTERSPACED.finditer(section.text)
    ]
    assert runs == [], f"a letterspaced run survives: {runs[:5]}"


def test_the_superscript_sentence_reads_whole(document):
    """§2: `…with more / 2 / than 25kg weight/m .` could not be quoted.

    *Factory farming* is a glossary term inside `S1`, not a section of its own — the term and
    its definition are two lines of the same section's body.
    """
    glossary = next(s for s in document.sections if s.section_ref == "S1")
    sentence = flat(section_text(glossary))

    assert "with more than 25kg weight/m²." in sentence
    assert "weight/m ." not in sentence


def test_appendix_6a_still_carries_its_twenty_classes_and_twenty_values(document):
    """§5: the artefact is the *record* the curated rows are checked against.

    The chunks for this appendix come from `knowledge/tables.py` (reviewed rows), so this
    guard is about the page text: if a reprint moves a class or a value, the review queue
    shows it here rather than in a reader who cannot find *laying hens*.
    """
    appendix = next(s for s in document.sections if s.section_ref == "Appendix 6a")
    values = re.findall(r"(?<![\d,])\d{1,3}(?:,\d)?(?![\d,])", flat(section_text(appendix)))

    assert "Laying hens" in appendix.text
    assert "Equines over six months old" in appendix.text
    assert len(values) >= 20, f"the value column lost numbers: {values}"


def test_the_reader_can_answer_the_laying_hens_question(document):
    """The end-to-end promise of §5, on the artefact's own text plus the reviewed rows."""
    from knowledge.tables import rows_for

    rows = rows_for("Appendix 6a")
    laying = next(row for row in rows if row.substance == "Laying hens")
    assert laying.condition == "230"
    assert flat(laying.text) == "Laying hens 230"


def test_every_chunk_of_the_artefact_renders_without_losing_a_word(document):
    """The reader's layout over the new text: `flatten` must reproduce every chunk."""
    for chunk in chunk_sections(list(document.sections)):
        source = flat(HASH.sub("", chunk.text))
        rendered = flat(flatten(passage_blocks(chunk.text)))
        assert rendered == source, f"{chunk.section_ref}: the layout changed the text"
