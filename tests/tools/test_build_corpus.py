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

import scripts.build_corpus as corpusgen

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
