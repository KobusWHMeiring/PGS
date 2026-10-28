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
