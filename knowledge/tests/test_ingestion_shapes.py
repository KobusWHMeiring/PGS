"""D80's eight-shape fixture set — the provenance guards, the audit, and the eight red targets.

Two kinds of test live here, and they are deliberately different:

* **Green, and about the fixtures themselves** — every anchor is a line the committed page
  actually prints, every cited test exists, every shape names its gap, and the set of shapes with no
  shape-level test is exactly the two live defects. These are the tests that stop the register
  decaying into a wish list.
* **Red, and about the engine** — one target per shape, calling `read_table()`. There is no reader
  from a page to a table today: every table in the corpus is a human's transcription. Each target is
  `xfail(strict=True)`, so the gap is **counted** in every run (`8 xfailed`) and a shape that starts
  passing turns the suite **red** (`XPASS(strict)`) until the marker is removed and the audit is
  updated. That is the difference between a recorded gap and a forgotten one.

The checker is proved to fail before it is trusted: `test_the_checker_fails_on_every_kind_of_bad_read`
feeds it a transposed row, a filled-in silence, a dropped divider and a wrong page, and asserts each
one is named. A guard nobody has watched go red is a guard nobody has tested
(`product/docs/context/testing_hazards.md`).

What this module deliberately does **not** do: measure the current corpus and assert it. Six of the
eight shapes already have that assertion (`covered_by`), on a human's fix, and repeating it here
would assert the same thing twice.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from knowledge.tests import shape_fixtures as shapes
from knowledge.tests.shape_fixtures import (
    SHAPES,
    SHAPE_NAMES,
    UNCOVERED,
    Cell,
    ShapeCase,
    TableRead,
    mismatches,
    normalised_lines,
    page_run,
    page_text,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def read_table(case: ShapeCase) -> TableRead:
    """The engine's side of the contract — **and today there is no engine**.

    Slice S2 of `INGESTION_ENGINE_PRD.md` replaces this body with the extractor-backed reader
    (`knowledge/shapes.py`: page text in, `TableRead` out). Until then the honest answer is that the
    page has never been read: the artefact block above it was typed by a person, and that person is
    the coverage.
    """
    raise NotImplementedError(
        f"D80 S2: no reader from a page to a table ({case.key}). The expectation above is the "
        "target; the artefact block it mirrors was written by hand."
    )


# --- The fixtures are the paper ---------------------------------------------


def test_the_set_is_the_explorations_eight_shapes_in_order():
    assert [case.shape for case in SHAPES] == list(SHAPE_NAMES)
    assert len({case.key for case in SHAPES}) == 8, "a key is used twice"


@pytest.mark.parametrize("case", SHAPES, ids=[case.key for case in SHAPES])
def test_every_anchor_is_a_line_the_page_prints(case):
    """The anchor is the fixture's provenance: if the paper moves, the case names the new page."""
    for pdf_page, line in case.anchors:
        assert " ".join(line.split()) in page_run(case, pdf_page), (
            f"{case.key}: PDF {pdf_page} does not print {line!r}. The page moved, or the anchor "
            "was written from memory rather than from the page."
        )


def test_the_two_live_defects_are_the_two_shapes_with_no_test():
    """The finding this set exists to make checkable, asserted rather than narrated.

    Six shapes have a test whose input is a human's fix. Two have none — and they are exactly the
    two defects the spec measures: Appendix 6a's headerless rows and Appendix 7's interleaving.
    """
    without = {case.key for case in SHAPES if not case.covered_by}
    assert without == set(UNCOVERED), (
        "the uncovered shapes moved. If a shape now has a test, name it in `covered_by` and remove "
        f"it from UNCOVERED; if a shape lost its test, that is a regression: {sorted(without)}"
    )
    assert {case.shape for case in SHAPES if case.key in UNCOVERED} == {
        "Header lost entirely",
        "Column-major interleaving",
    }


def test_every_cited_test_exists():
    """`covered_by` is a claim about the tree, so it is checked against the tree."""
    missing: list[str] = []
    for case in SHAPES:
        for module, name in case.covered_by:
            path = REPO_ROOT / module
            if not path.is_file() or f"def {name}(" not in path.read_text(encoding="utf-8"):
                missing.append(f"{case.key}: {module}::{name}")
    assert not missing, f"the register cites tests that are not there: {missing}"


@pytest.mark.parametrize("case", SHAPES, ids=[case.key for case in SHAPES])
def test_every_shape_names_its_gap_and_what_the_format_can_say(case):
    assert case.gap, f"{case.key} has no gap: a shape we already read is not a shape"
    assert case.ir.split(" ")[0] in {"expressible", "partly", "no"}, case.ir
    assert case.row_count and len(case.row_pages) == case.row_count, (
        f"{case.key}: one page per row, or the page break is not modelled"
    )
    assert case.cells, f"{case.key}: no expectation to assert"


def test_the_one_declared_spelling_difference_is_the_letter_spaced_row():
    """Appendix 6a prints intra-word letter spacing; the reviewed row rejoins it.

    Declared here, with both halves, rather than silently normalised: this is the only place where
    the page's characters and the corpus's characters disagree, and the disagreement is the
    justification for the harness's one normalisation.
    """
    case = shapes.BY_KEY["headerless_values"]
    printed = normalised_lines(page_text(case, 86))
    assert "Other b o v i n e a n i m a l s less t h a n o n e year old 5" in printed
    expected = next(cell for cell in case.cells if cell.row == 2 and cell.column == 0)
    assert expected.text == "Other bovine animals less than one year old"


# --- The checker can fail ---------------------------------------------------


def a_small_case() -> ShapeCase:
    """A two-row case built from memory, so the mutation tests need no page at all."""
    return ShapeCase(
        key="checker",
        shape="Checker self-test",
        doc="in memory",
        doc_key="landscape",
        mode="table",
        pdf_pages=(4,),
        printed_pages=(4,),
        anchors=(),
        columns=("A", "B"),
        row_count=2,
        cells=(
            Cell(0, 0, text="one"),
            Cell(0, 1, empty=True),
            Cell(1, 0, text="two"),
            Cell(1, 1, text="3"),
        ),
        row_pages=(4, 5),
        dividers=((1, "Qualifier", "qualifier"),),
        gap="none — this case exists to test the checker",
    )


def a_small_read() -> TableRead:
    return TableRead(
        columns=("A", "B"),
        rows=(("one", ""), ("two", "3")),
        pages=(4, 5),
        dividers=((1, "Qualifier", "qualifier"),),
    )


def test_the_checker_accepts_a_correct_read():
    assert mismatches(a_small_case(), a_small_read()) == []


@pytest.mark.parametrize(
    "read, named",
    [
        (replace(a_small_read(), rows=(("one", ""),)), "rows"),
        (replace(a_small_read(), rows=(("one", "filled"), ("two", "3"))), "must be empty"),
        (replace(a_small_read(), rows=(("", "one"), ("two", "3"))), "cell 0"),
        (replace(a_small_read(), dividers=()), "dividers"),
        (replace(a_small_read(), pages=(4, 4)), "row pages"),
        (replace(a_small_read(), columns=("A",)), "columns"),
    ],
)
def test_the_checker_fails_on_every_kind_of_bad_read(read, named):
    found = "\n".join(mismatches(a_small_case(), read))
    assert named in found, f"the checker did not name {named!r}:\n{found}"


def test_the_checker_reports_a_missing_cell_rather_than_treating_it_as_empty():
    """An absent cell and an empty one are different findings — shapes 5 and 2 depend on it."""
    read = replace(a_small_read(), rows=(("one",), ("two", "3")))
    found = "\n".join(mismatches(a_small_case(), read))
    assert "missing from the read" in found


# --- The engine's targets, one per shape, red until S2 ----------------------


@pytest.mark.parametrize("case", SHAPES, ids=[case.key for case in SHAPES])
@pytest.mark.xfail(
    strict=True,
    reason="D80 S2: the page has never been read — every table in the corpus is a human transcription",
)
def test_the_shape_is_read_from_its_page(case):
    found = mismatches(case, read_table(case))
    assert not found, "\n".join(found)
