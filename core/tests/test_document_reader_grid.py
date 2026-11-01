"""The reader's printed grid for the landscape's five-column tables (D72.3, D76).

The corpus is quotable; this is the surface that has to *show* it. `LANDSCAPE_TABLES_PRD` §5.4
measured the fit problem, and `product/design/d76_reader_table_fit.html` recorded the decision:
a real `<table>` at the passages pane's full width, a scroll region with a sticky first column,
and the same markup stacked below 900 px.

These tests pin the shape, not the pixels:

- the branch renders **one** table with the paper's five column names;
- the row chunks are **inside** the grid, and the lead-in/trailing prose stays outside it;
- every row keeps its citation anchor (`id="establishing-a-pgs-group-step-3"`), so a citation to
  the row still lands on the row;
- a branch that is not a reviewed table renders no grid at all.

The visual questions — does the fee read, is the sticky column right at 840 px — are UAT's, not
this file's.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.models import PublicDocument
from knowledge.ingest import ingest_standard
from knowledge.models import StandardSet
from knowledge.tests.page_fixtures import stub_ingest_extraction

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF = REPO_ROOT / "pgs_docs" / "PGS Certification landscape_Final.pdf"
SOURCE = "pgs_docs/PGS Certification landscape_Final.pdf"
ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "landscape.md"


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)


@pytest.fixture
def landscape(standard_set, monkeypatch):
    """The real artefact, ingested, plus the published row that traces to the same file."""
    stub_ingest_extraction(monkeypatch)
    ingest_standard(
        pdf_path=PDF,
        standard_set=standard_set,
        doc_key="landscape",
        embed=False,
        corpus_path=ARTEFACT,
    )
    return PublicDocument.objects.create(
        code="certification-landscape",
        title="The South African Organic Certification Landscape",
        file_path="public/documents/certification-landscape.pdf",
        source_path=SOURCE,
        is_published=True,
    )


def html(client, section: str) -> str:
    response = client.get(
        f"/documents/certification-landscape/read/?section={section}"
    )
    assert response.status_code == 200
    return response.content.decode()


# --- ESTABLISHING A PGS GROUP is a process: three cards (D77 C3) -------------


def cards(page: str) -> list[str]:
    """The card markup of a process branch, in order, as strings."""
    return page.split('<article class="reader__card"')[1:]


def test_the_establishing_branch_renders_three_step_cards(client, landscape):
    page = html(client, "establishing-a-pgs-group")

    assert '<table class="reader__grid"' not in page, "a process is not a spreadsheet"
    assert page.count('<article class="reader__card"') == 3
    for step, title in (
        ("Step 1", "Get together"),
        ("Step 2", "Agree and establish"),
        ("Step 3", "Visit and certify"),
    ):
        assert step in page and title in page, (step, title)
    assert page.index("Get together") < page.index("Agree and establish") < page.index(
        "Visit and certify"
    ), "printed order"


def test_the_two_folded_facets_are_closed_and_the_seal_rule_is_not(client, landscape):
    """§12f item 3: Resources and Seals fold so the step body leads; Use of seals stays visible."""
    page = html(client, "establishing-a-pgs-group")

    assert "<details" in page
    assert "<details open" not in page, "closed by default"
    assert "Use of seals and logos" in page
    # The Step 2 rule a reader checks is not inside a folded facet.
    rule = "entitled to make use of the"
    assert rule in page
    before, after = page.split("<details", 1)
    assert rule not in after.split("</details>", 1)[0]


def test_the_merged_fee_is_one_box_with_the_whole_cell_under_steps_1_and_2(
    client, landscape
):
    """D72.2: the amount never appears alone, and the merged cell is not split per step."""
    page = html(client, "establishing-a-pgs-group")

    assert "--fee-start: 1; --fee-span: 2" in page, "the joining box covers cards 1-2"
    assert "--fee-start: 3; --fee-span: 1" in page, "the certification box covers card 3"

    boxes = page.split('<div class="reader__fee"')[1:]
    assert len(boxes) == 2
    joined = " ".join(boxes[0].split())
    assert "Steps 1–2" in joined
    assert "Annual membership fee (paid by the PGS group to PGS SA): R500" in joined
    assert "R1 000" in joined, "the once-off amount is part of the same printed cell"
    certified = " ".join(boxes[1].split())
    assert "Step 3" in certified
    assert "R350" in certified
    for box in (joined, certified):
        assert "R" in box, box


def test_the_lead_in_prose_is_before_the_cards_and_not_inside_them(client, landscape):
    page = html(client, "establishing-a-pgs-group")
    lead_in = "The table below outlines the steps for the establishment of a PGS group"

    assert page.index(lead_in) < page.index('<article class="reader__card"')
    first_card = page.split('<article class="reader__card"', 1)[1].split("</article>", 1)[0]
    assert lead_in not in " ".join(first_card.split())


def test_a_card_that_starts_on_a_new_page_says_so_once(client, landscape):
    """D72.5: the page marker changes once, at the card that crosses the break."""
    page = html(client, "establishing-a-pgs-group")
    body = page.split('class="reader__process"', 1)[1].split("reader__provenance", 1)[0]

    assert body.count("printed p. 4") == 1, "Steps 1 and 2 share p4, and it says so once"
    assert body.count("printed p. 5") == 1, "Step 3 starts on PDF 5"


# --- The seals table opens straight into its rows, and it is the grid -------


def test_the_seals_branch_renders_the_spreadsheet_and_the_prose_after_it(client, landscape):
    page = html(client, "pgs-seals-and-their-use")
    trailing = "PGS SA is developing guidelines to facilitate trade between PGS groups"

    assert page.count('<table class="reader__grid"') == 1
    assert page.count('<th scope="row">') == 2
    assert 'id="pgs-seals-and-their-use-pgs-organic-in-conversion"' in page
    assert 'id="pgs-seals-and-their-use-pgs-organic"' in page
    assert page.index("</table>") < page.index(trailing)
    assert "reader__process" not in page, "a comparison is not a process"


def test_the_grid_carries_what_the_resizer_needs_and_nothing_it_requires(client, landscape):
    """D77: sizing is an enhancement — the separator and the colgroup are inert without the script."""
    page = html(client, "pgs-seals-and-their-use")

    assert 'data-reader-grid' in page
    assert 'data-grid-key="landscape.pgs-seals-and-their-use"' in page
    assert page.count("<colgroup>") == 1
    # One separator per boundary *between* columns: the first column is the pinned row label and
    # the last has nothing to its right to widen against. Five columns, three handles.
    assert page.count('role="separator"') == 3
    assert 'aria-orientation="vertical"' in page
    assert "reader-grid.js" in page


# --- SAOSO ORGANIC CERTIFICATION: two steps and a fork ----------------------


def test_the_saoso_branch_renders_two_steps_and_the_fork(client, landscape):
    """§12f item 4: the direct route is an alternative path, not a fourth step."""
    page = html(client, "saoso-organic-certification")

    assert '<table class="reader__grid"' not in page
    assert page.count('<article class="reader__card') == 4, (
        "two steps + the Path A pointer + the direct route's own card"
    )
    assert "Step 1" in page and "Step 2" in page
    assert "Path A" in page and "Path B" in page
    assert page.index("Path A") < page.index("Path B"), "stacked, Path A first"
    assert '<div class="reader__or"' in page, "the `or` rule, not a second step number"


def test_path_a_is_a_pointer_to_step_2_and_repeats_no_fee(client, landscape):
    """§12f.5: if Path A repeats Step 2's licence fees, D72.2 is broken in a new place."""
    page = html(client, "saoso-organic-certification")

    pointer = page.split('reader__card--pointer', 1)[1].split("</article>", 1)[0]
    assert 'href="#saoso-organic-certification-step-2"' in pointer
    assert "See Step 2" in pointer
    assert "R500" not in pointer and "R2 500" not in pointer
    assert "R500" in page, "Step 2's licence fees are stated once, in its own fee box"


def test_the_direct_route_keeps_its_own_full_fee_cell(client, landscape):
    page = html(client, "saoso-organic-certification")
    boxes = page.split('<div class="reader__fee"')[1:]

    assert len(boxes) == 3, "a fee per printed row"
    assert "--fee-start: 3; --fee-span: 1" in page, "the direct route's box is under column 3"
    assert "Quote to be provided by the Accredited Certifying Body" in " ".join(boxes[2].split())


# --- Branches that are not tables -------------------------------------------


@pytest.mark.parametrize("section", ["introduction", "colophon", "first-party-claim"])
def test_a_prose_branch_renders_no_grid(client, landscape, section):
    page = html(client, section)
    assert '<table class="reader__grid"' not in page


# --- The fallback, and the doc-key map --------------------------------------


def test_a_corpus_that_disagrees_with_the_artefact_renders_no_grid(client, landscape):
    """A stale row is worse than no grid: the reader falls back to the plain passages.

    Simulated by editing one stored chunk — the artefact still has the row, but the corpus no
    longer does, which is exactly the state a failed re-ingest leaves behind.
    """
    from knowledge.models import DocumentChunk

    row = DocumentChunk.objects.get(
        document__source_file=SOURCE,
        anchor="establishing-a-pgs-group-step-1",
    )
    row.text = row.text.replace("R500", "R5OO")
    row.save(update_fields=["text"])

    page = html(client, "establishing-a-pgs-group")
    assert '<table class="reader__grid"' not in page
    assert "Annual membership fee" in page, "the plain passage still renders the row's text"


def test_a_source_file_maps_to_its_doc_key():
    from knowledge.ingest import doc_key_for

    assert doc_key_for(SOURCE) == "landscape"
    assert doc_key_for("pgs_docs/not-a-governed-document.pdf") is None
    assert doc_key_for(None) is None


# --- D77: the shape the artefact declares, carried to the reader ------------


def grid_for(landscape, section: str):
    """The reader's grid for a branch, from the service — the shape the template will draw."""
    from core.services._documents import reader_for

    grid = reader_for(landscape, section=section).grid
    assert grid is not None, f"{section} is a reviewed artefact table"
    return grid


def test_the_establishing_table_asks_for_the_process_shape(landscape):
    """D77 E+C3: three cards, each with the reviewer's title, one fee box per reviewed label."""
    grid = grid_for(landscape, "establishing-a-pgs-group")

    assert grid.layout == "process"
    assert [row.label for row in grid.rows] == ["Step 1", "Step 2", "Step 3"]
    assert [row.title for row in grid.rows] == [
        "Get together",
        "Agree and establish",
        "Visit and certify",
    ]
    assert not any(row.is_path for row in grid.rows), "three steps in a row: there is no fork"
    assert grid.fee_labels == ("Steps 1–2", "Step 3"), (
        "the reviewer's words — the paper does not print 'joining' or 'certification'"
    )

def test_the_saoso_table_splits_after_step_2(landscape):
    """The direct route is an alternative path, not a fourth step (D77, §12f item 4)."""
    grid = grid_for(landscape, "saoso-organic-certification")

    assert grid.layout == "process"
    assert [row.is_path for row in grid.rows] == [False, False, True]
    assert grid.rows[2].label == "For farmers wanting direct 3rd party certification"
    assert grid.rows[2].title == "", "the fourth field is optional; the label is the fallback"
    assert grid.fee_labels == (), (
        "SAOSO states a fee per row, so no fee box is merged and no label is needed"
    )


def test_the_seals_table_asks_for_the_grid_shape(landscape):
    grid = grid_for(landscape, "pgs-seals-and-their-use")

    assert grid.layout == "grid"
    assert [row.label for row in grid.rows] == ["PGS Organic In-Conversion", "PGS Organic"]
    assert not any(row.is_path for row in grid.rows), "a comparison has no fork"


# --- D77 C3: the rows grouped the way a card needs them ---------------------


def test_the_establishing_cards_take_the_first_column_as_the_step_body(landscape):
    grid = grid_for(landscape, "establishing-a-pgs-group")

    assert [card.label for card in grid.cards] == ["Step 1", "Step 2", "Step 3"]
    assert [card.title for card in grid.cards] == [
        "Get together",
        "Agree and establish",
        "Visit and certify",
    ]
    assert grid.cards[0].body[0].text.startswith("Farmers who are already producing"), (
        "the heading prints `Step 1`, so the cell's duplicate of it is dropped"
    )
    assert not any(
        block.kind == "paragraph" and block.text.strip() == "Step 1"
        for block in grid.cards[0].body
    )


def test_the_facets_keep_the_printed_column_order_and_fold_only_two_of_them(landscape):
    """§12f item 3: Resources and Seals fold; Use of seals is the rule a reader checks."""
    card = grid_for(landscape, "establishing-a-pgs-group").cards[1]

    assert [facet.label for facet in card.facets] == [
        "Resource documents, guidelines and requirements",
        "Use of seals and logos",
        "Seals and logos",
    ]
    assert [facet.folded for facet in card.facets] == [True, False, True]


def test_the_merged_fee_cell_is_one_box_under_steps_1_and_2(landscape):
    """D72.2 + §12f.5: the whole cell, once, spanning the rows it is printed across."""
    from knowledge.passages import flatten

    grid = grid_for(landscape, "establishing-a-pgs-group")

    assert [box.label for box in grid.fee_boxes] == ["Steps 1–2", "Step 3"]
    assert [(box.start, box.span) for box in grid.fee_boxes] == [(0, 2), (2, 1)]
    merged = " ".join(flatten(grid.fee_boxes[0].blocks).split())
    assert "Annual membership fee (paid by the PGS group to PGS SA): R500" in merged
    assert "R1 000" in merged, "the once-off amount is in the same printed cell"


def test_saoso_states_a_fee_per_row_so_every_box_covers_one_card(landscape):
    grid = grid_for(landscape, "saoso-organic-certification")

    assert [(box.start, box.span) for box in grid.fee_boxes] == [(0, 1), (1, 1), (2, 1)]
    assert [box.label for box in grid.fee_boxes] == ["Fee", "Fee", "Fee"], (
        "no `fee_label:` was reviewed, so the printed column heading is the heading"
    )
    assert [card.is_path for card in grid.cards] == [False, False, True]


def test_the_seals_comparison_carries_no_cards_and_no_fee_boxes(landscape):
    grid = grid_for(landscape, "pgs-seals-and-their-use")

    assert grid.layout == "grid"
    assert grid.cards == ()
    assert grid.fee_boxes == ()
