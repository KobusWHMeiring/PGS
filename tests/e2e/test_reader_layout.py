"""The reader's two panes: the tree holds the left column, the passages hold the right.

This file exists because of one defect, found by eye on 2026-10-27 and by nothing else: the
missing-sections note was moved out of the phone `<details>` (D70.6) and became a **third child**
of `.reader__body`, which is a two-column grid. The passages wrapped to the next row, and the
sticky tree — still in column one — sat **on top of the text**, so a reader following a citation
arrived at a page where the quoted line was behind the contents list.

No gate test could see it: the markup was right, the text was present, the anchors resolved and
the console was clean. That is what this suite is for (`conftest.py`'s own docstring lists three
earlier members of the same family).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

READER = "/documents/saoso-standard-v2.1/read/?section=s5-1-3"

TREE = ".reader__tree"
COLUMN = ".reader__tree-column"
PASSAGES = ".reader__passages"


def _overlap(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def test_on_a_desk_the_passages_sit_beside_the_tree_not_under_it(page, live_server, reader_corpus):
    """The measured defect: two boxes that overlap, in the one place a reader must read."""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(live_server.url + READER, wait_until="networkidle")

    tree = page.locator(COLUMN).bounding_box()
    passages = page.locator(PASSAGES).bounding_box()

    assert tree and passages, "the reader rendered without one of its two panes"
    assert not _overlap(tree, passages), (
        f"the tree overlaps the passages: tree {tree} passages {passages}"
    )
    assert passages["x"] >= tree["x"] + tree["width"], (
        "the passages are not in the column beside the tree"
    )


def test_the_quoted_clause_is_not_behind_the_contents_list(page, live_server, reader_corpus):
    """What a reader actually does: arrive at `#s5-1-3` and read it.

    The highlighted passage must be on screen and uncovered — a `:target` rule that bleeds a
    background behind a floating panel is the failure mode this asserts against.
    """
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(live_server.url + READER + "#s5-1-3", wait_until="networkidle")

    passage = page.locator("article.passage:target").bounding_box()
    tree = page.locator(COLUMN).bounding_box()

    assert passage, "no :target passage — the citation did not land"
    assert not _overlap(tree, passage), f"the target passage is behind the tree: {passage} {tree}"
    assert passage["y"] >= 0, "the target passage is above the viewport"


def test_on_a_phone_the_tree_is_a_disclosure_and_the_note_is_readable(page, live_server, reader_corpus):
    """D70.6 on the device it was decided for: the tree folds away, the note does not hide.

    A fragment inside a closed `<details>` cannot be scrolled to, which is why the note about the
    sections the corpus does not hold sits outside the disclosure. If it ever moves back inside,
    `Section A – 2.3` links into a closed box and looks broken.
    """
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(live_server.url + READER, wait_until="networkidle")

    summary = page.locator(".reader__tree-summary")
    note = page.locator("#not-in-corpus")

    assert summary.is_visible(), "the phone has no tree disclosure"
    assert page.evaluate(
        "() => !document.querySelector('.reader__tree-details').open"
    ), "the tree should start closed on a phone"
    assert note.is_visible(), "the missing-sections note is hidden behind the disclosure"
    assert note.bounding_box()["width"] > 0

    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0, f"the reader scrolls sideways at 390 px by {overflow}px"


def test_a_definition_link_lands_below_the_search_bar(page, live_server, reader_corpus):
    """`#term-synthetic` must land on `Synthetic`, and the definition must be readable.

    Two measured defects, both reported from the live page on 2026-10-27: the jump inherited
    `root.css`'s `scroll-behavior: smooth` and animated across ~11 000 px (seconds, and any wheel
    nudge cancels it), and a definition's `id` sits on a `<p>` *inside* a passage, so `.passage`'s
    `scroll-margin-top` never applied to it and it landed at y=96 — behind a search panel whose
    bottom is 191. The page arrived, and the definition was covered.
    """
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(live_server.url + "/documents/saoso-standard-v2.1/read/?section=s1#term-synthetic")
    page.wait_for_timeout(400)

    assert (
        page.evaluate("() => getComputedStyle(document.documentElement).scrollBehavior") == "auto"
    ), "the reader animates its jumps: a citation would crawl, and a wheel nudge cancels it"

    boxes = page.evaluate(
        """() => {
            const term = document.getElementById('term-synthetic');
            const search = document.querySelector('.reader__search').getBoundingClientRect();
            const box = term && term.getBoundingClientRect();
            return term ? {top: box.top, bottom: search.bottom,
                           height: window.innerHeight} : null;
        }"""
    )

    assert boxes, "the definition is not on the page at all"
    assert boxes["top"] >= boxes["bottom"], (
        f"the definition is behind the search panel: term top {boxes['top']}, "
        f"search bottom {boxes['bottom']}"
    )
    assert 0 <= boxes["top"] < boxes["height"], "the definition is not in the viewport"


def test_a_printed_margin_label_is_not_a_section_heading(page, live_server, reader_corpus):
    """`South African specific` is a printer's label, and must not weigh what a division weighs.

    SAOSO centres it above each definition that adds to or amends the international wording — 26 of
    them in `S1` alone, plus 23 `Regional or other exception`. The layout found them as centred
    lines and rendered them at `passage__heading`'s weight, so the definitions page read as a dozen
    sections all called *South African specific*. Reported from the live page on 2026-10-27.
    """
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(live_server.url + "/documents/saoso-standard-v2.1/read/?section=s1", wait_until="networkidle")

    measured = page.evaluate(
        """() => {
            const q = document.querySelector('.passage__qualifier');
            const h = document.querySelector('.passage__heading');
            return {
                qualifiers: document.querySelectorAll('.passage__qualifier').length,
                wrong: [...document.querySelectorAll('.passage__heading')]
                    .filter(e => /South African|Regional or other exception/i.test(e.textContent)).length,
                qualifier_size: q && parseFloat(getComputedStyle(q).fontSize),
                heading_size: h && parseFloat(getComputedStyle(h).fontSize),
            };
        }"""
    )

    assert measured["qualifiers"] >= 1, "the printed label did not render at all"
    assert measured["wrong"] == 0, "a printed margin label rendered at section-heading weight"
    assert measured["qualifier_size"] < measured["heading_size"], (
        f"the label is not subordinate to the heading: {measured}"
    )


def test_a_wrapped_clause_reads_and_selects_as_one_sentence(page, live_server, reader_corpus):
    """`S23.3` wraps mid-sentence on a hanging indent; the browser must show, and select, one sentence.

    Found by the product owner reading `?section=s23` on 2026-10-28: the clause arrived as two
    paragraphs, so it could not be selected as one sentence and copying it gave
    `…property or documents.23.5. Operators…`. The fix is a display rule, so this belongs in a
    browser: the gate can prove the blocks, only the page can prove the paragraph.
    """
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(
        live_server.url + "/documents/saoso-standard-v2.1/read/?section=s23-3",
        wait_until="networkidle",
    )

    measured = page.evaluate(
        r"""() => {
            const paragraphs = [...document.querySelectorAll('p.passage__text')];
            const clause = paragraphs.find(p => p.textContent.includes('forced or involuntary'));
            if (!clause) return null;
            const range = document.createRange();
            range.selectNodeContents(clause);
            return {
                paragraphs: paragraphs.length,
                sentence: clause.textContent,
                selected: range.toString(),
                startsLowercase: /^\s*[a-z]/.test(clause.textContent),
            };
        }"""
    )

    assert measured, "the clause did not render at all"
    assert not measured["startsLowercase"], "the continuation is still its own paragraph"
    assert "workers\u2019 wages, property or documents." in measured["sentence"]
    assert "part of the workers\u2019 wages" in measured["selected"], (
        f"the sentence does not select as one clause: {measured['selected'][:120]}"
    )
    assert measured["paragraphs"] == 2, (
        f"two printed clauses should be two paragraphs, got {measured['paragraphs']}"
    )
