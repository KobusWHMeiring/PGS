"""`scripts/build_corpus.py` — what a draft keeps, and what it must never keep.

The generator is the *drafting* half of the artefact review (D53, D58): the human reads a diff,
which only means anything if the draft actually carries the document. Measured 2026-10-30, it did
not — the generic branch set

    keep = is_page_furniture

and that function's own docstring begins *"Content the artefact must not carry"*. A generated
landscape draft was therefore five headings and the page numbers (`## R500`, `## PGS SA.`,
`## SAOSO`) with **no body text at all**, and every guard downstream stayed green because an
artefact with no body has nothing that can be wrong. That is the shape of defect this repo's
hazard log is for: not a wrong value, an empty one.

`body_filter(parser)` is the seam these assertions pin, and it exists as a function rather than a
line inside `build()` so it can be tested without a PDF or an extractor (the gate runs with
`PDFTOTEXT_BIN=/usr/bin/true`, `testing_hazards.md` §2.9).

Four decisions, and the fourth is the subtle one: **a blank line is content.** The blank lines are
the chunker's paragraph boundaries (`build_corpus.py` rule 3), so a filter that drops them produces
a draft whose paragraphs run together — a diff nobody could review, and chunks packed differently
from the committed artefact.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import scripts.build_corpus as corpusgen
from knowledge.corpus import CorpusEdit

#: The branch a document with no `body_lines` takes: bpp, opp and landscape.
GENERIC = SimpleNamespace(body_lines=None)

#: A parser that declares its own body stream: SAOSO.
WITH_BODY_LINES = SimpleNamespace(body_lines=lambda joined: [])


def test_a_body_line_is_kept():
    assert corpusgen.body_filter(GENERIC)("The terms of reference for these principles are")


def test_a_blank_line_is_kept_because_it_is_a_paragraph_boundary():
    assert corpusgen.body_filter(GENERIC)("")


def test_the_contact_block_is_dropped():
    keep = corpusgen.body_filter(GENERIC)
    assert not keep("Postnet Suite 123, Private Bag X1")
    assert not keep("www.pgssa.org.za")


def test_a_bare_printed_page_number_is_dropped():
    """In `-raw` order the stamp arrives *before* the body, so it would head the section."""
    assert not corpusgen.body_filter(GENERIC)("02")


def test_a_parser_with_its_own_body_stream_keeps_its_blank_lines_and_digits():
    """SAOSO's page is double-spaced and its lone digits are superscripts and table cells.

    The parser owns that judgement (`SaosoParser.body_lines`), so the generator must not apply
    the page-stamp rule on top of it — that is how the first draft lost `m²` and Appendix 6a's
    values (`BugFixes/saoso_text_glyphs_and_boundaries.md` §2, §5).
    """
    keep = corpusgen.body_filter(WITH_BODY_LINES)
    assert keep("")
    assert keep("02")
    assert not keep("P a g e | 47")


# --- What a page's *furniture* is, and why it is data -------------------------
#
# Measured 2026-10-30: regenerating `bpp.md` differed from the reviewed artefact by **57 lines**,
# and two thirds of that was the four `The Principle / Of Health.` pairs — printed down the margin
# of pages 6, 8 and 10, so the draft carried the block three times where a reviewer kept it once.
#
# **The rule is data, not inference.** The inferential version — "a line printed on N different
# pages is furniture" — was measured against the shipped documents before it was written, and it
# destroys SAOSO: `General Principle` appears on 26 pages, `Requirements:` on 25 and
# `South African specific` on 18, and all three are content. The block-repetition version is worse
# still: SAOSO prints one poultry derogation verbatim on pages 45, 46 and 47, and dropping it would
# silently edit the standard. So the document's own reviewer names its running labels
# (`BODY_FURNITURE`), the way `PAGE_LAYOUT_EXCLUSIONS` and `PAGE_LAYOUT_BANDS` already work.


def test_a_running_label_block_is_kept_on_its_first_page_and_dropped_after():
    """The BPP's four principle labels, printed down pages 6, 8 and 10.

    Kept **once**, which is what the reviewed artefact does — so the diff is silence rather than
    a review decision the generator cannot reproduce.
    """
    labels = ("The Principle", "Of Health.")
    lines = [
        (6, "c. the water source is clean,"),
        (6, "The Principle"),
        (6, "Of Health."),
        (8, "ii. Ruminants shall have daily"),
        (8, "The Principle"),
        (8, "Of Health."),
        (10, "b. Records of all purchases"),
        (10, "The Principle"),
        (10, "Of Health."),
    ]
    assert corpusgen.drop_body_furniture(lines, labels) == [
        (6, "c. the water source is clean,"),
        (6, "The Principle"),
        (6, "Of Health."),
        (8, "ii. Ruminants shall have daily"),
        (10, "b. Records of all purchases"),
    ]


def test_a_label_printed_twice_on_its_first_page_is_kept_twice():
    """A per-line "keep the first occurrence" rule would halve the block.

    The paper prints four *pairs* on one page: `The Principle / Of Health. / The Principle /
    Of Ecology. …`. The unit is the page that first carries a label, not the label's first line.
    """
    labels = ("The Principle", "Of Health.", "Of Ecology.")
    lines = [
        (6, "The Principle"),
        (6, "Of Health."),
        (6, "The Principle"),
        (6, "Of Ecology."),
        (8, "The Principle"),
        (8, "Of Health."),
        (8, "The Principle"),
        (8, "Of Ecology."),
    ]
    assert [line for _page, line in corpusgen.drop_body_furniture(lines, labels)] == [
        "The Principle",
        "Of Health.",
        "The Principle",
        "Of Ecology.",
    ]


def test_a_document_with_no_named_furniture_is_untouched():
    """SAOSO, OPP and every future standard: no entry, no change (the retarget rule)."""
    lines = [(45, "South African specific poultry derogation"), (46, "Requirements:")]
    assert corpusgen.drop_body_furniture(lines, ()) == lines


def test_a_named_label_that_the_text_no_longer_prints_is_not_an_error():
    """A reprint may drop a running label; that is a smaller diff, not a corpus failure.

    Deliberately unlike `apply_review`, which fails loudly when a reviewed *correction* stops
    matching: a correction that no longer applies is a review of a different document, while
    furniture that is no longer printed is simply gone.
    """
    assert corpusgen.drop_body_furniture([(6, "Body.")], ("The Principle",)) == [(6, "Body.")]


def test_private_use_glyphs_are_not_text():
    """U+F06E is a Wingdings bullet in the BPP's text layer, not a character anyone can quote.

    It is also the character that killed `--stdout` on this box (`testing_hazards.md` §3.21), and
    both shipped artefacts already carry none — so stripping the range changes no reviewed text.
    """
    # The glyph and the space the paper puts after it; the artefact keeps the space.
    assert corpusgen.strip_private_use("\uf06e Planting:") == " Planting:"
    assert corpusgen.strip_private_use("no glyphs here") == "no glyphs here"


# --- Page markers: a page that carries only blank lines is not a page ----------


def test_a_page_whose_only_kept_line_is_blank_gets_no_marker():
    """Measured on the BPP: the draft ended with `<!-- page: 13 printed: none -->` and nothing.

    The blank line that produced it belongs to the page before. A marker that heads no text is a
    locator pointing at the end of the document.
    """
    lines = [(3, "a"), (3, ""), (4, ""), (5, "b")]
    body, last = corpusgen.assemble_body(lines, {3: None, 4: None, 5: None}, lambda line: True)
    assert body == [
        "<!-- page: 3 printed: none -->",
        "a",
        "",
        "",
        "<!-- page: 5 printed: none -->",
        "b",
    ]
    assert last == 5


def test_a_page_marker_carries_the_printed_number_the_parser_reads():
    body, _ = corpusgen.assemble_body([(7, "x")], {7: 6}, lambda line: "9" not in line)
    assert body == ["<!-- page: 7 printed: 6 -->", "x"]


def test_the_first_marker_is_not_repeated_when_the_heading_already_emitted_it():
    """`build()` emits the heading's page marker itself, then hands the body to `assemble_body`."""
    body, last = corpusgen.assemble_body(
        [(3, "heading body")], {3: 1}, lambda line: True, after=3
    )
    assert body == ["heading body"]
    assert last == 3


# --- `apply_review`: what regeneration does with a reviewed correction --------
#
# This function had no test until 2026-10-30, and it was silently corrupting the BPP. Its
# docstring promised `SystemExit` when an edit "matches more than once", but it called
# `subn(..., count=1)`, whose second return value is the number of *substitutions it made* — so a
# pattern with two matches returned 1 and the `!= 1` guard could never fire. And `flat()` was
# `flat()` was applied to the replacement, so a correction that moves a paragraph collapsed it
# onto one line. Both fixed 2026-10-30, both proved red first.


def test_a_correction_that_moves_a_paragraph_keeps_its_lines():
    """The BPP's footnote 2 belongs on its bullet, three printed lines below the glue point.

    A replacement flattened onto one line is the same *words* and a different *paragraph* — and
    `flat()` comparison is exactly why the corruption below went unnoticed for a day.
    """
    edit = CorpusEdit(
        page=4,
        original="land available will not be allowed.",
        replacement="land available will not be allowed.\n2 Sustainable means: it does.",
        reason="a move, expressed as a lift plus a place",
    )
    text = "a. Sustainable land management2 –\nland available will not be allowed.\nb. Wetlands\n"
    assert corpusgen.apply_review(text, (edit,)) == (
        "a. Sustainable land management2 –\n"
        "land available will not be allowed.\n"
        "2 Sustainable means: it does.\n"
        "b. Wetlands\n"
    )


def test_the_original_may_span_a_line_break():
    """The match is whitespace-tolerant: an edit names a sentence, not a line."""
    edit = CorpusEdit(page=3, original="the sentence as printed", replacement="corrected", reason="x")
    assert (
        corpusgen.apply_review("intro\nthe sentence\nas printed\noutro\n", (edit,))
        == "intro\ncorrected\noutro\n"
    )


def test_a_correction_that_no_longer_matches_fails_loudly():
    edit = CorpusEdit(page=4, original="text that is gone", replacement="x", reason="x")
    with pytest.raises(SystemExit, match="page 4.*matched 0 times"):
        corpusgen.apply_review("nothing like it here", (edit,))


def test_a_correction_that_matches_twice_fails_loudly():
    """The guard `count=1` cannot provide: `subn(count=1)` reports one substitution either way.

    A doubled anchor means the reviewer's correction is about to be applied to whichever
    occurrence came first in the stream — which is how the BPP's footnote edit put `land
    available will not be allowed.` at the foot of page 4.
    """
    edit = CorpusEdit(page=4, original="twice here", replacement="x", reason="x")
    with pytest.raises(SystemExit, match="matched 2 times"):
        corpusgen.apply_review("twice here and twice here", (edit,))
