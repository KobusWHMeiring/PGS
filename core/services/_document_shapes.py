"""The shapes a reader page is made of: passages, cards, the grid and the fee box.

Split out of `_document_reader.py` (CONTEXT_CUTS_PRD step 7). These are the values the
template renders and the builders that make them from one branch of the corpus - the printed
grid for a reviewed artefact table (D72.3), the cards for a landscape process table, the fee
box, the folded facets. **They decide presentation from data that is already parsed**; they
choose nothing about which branch is open, which is `_document_reader.reader_for`'s job.

Everything here returns dataclasses, so the page is assembled once and rendered without logic
(`build_principles.md` II): a template that has to work out which cell is which is a template
that can disagree with the citation.
"""

from __future__ import annotations


import re
from dataclasses import dataclass, replace
from pathlib import Path
from knowledge.concordance import ConcordanceSection, build_concordance
from knowledge.corpus import load_document
from knowledge.ingest import corpus_artifact, doc_key_for
from knowledge.models import StandardDocument
from knowledge.passages import passage_blocks
from knowledge.reading import (
    SearchHit,
    branch_texts,
    passage_locator,
    printed_locators,
    reading_chunks,
    search_in_document,
    strip_overlap,
    unique_anchors,
)
from knowledge.tables import (
    TableDivider,
    align_artefact_grid,
    artefact_grid_for,
)


@dataclass(frozen=True)
class ReaderPassage:
    """One passage as the reader renders it.

    `text` is the stored chunk with a **leading chunk overlap removed** when the passage above
    already printed those words (`knowledge.reading.strip_overlap`); nothing else is changed.
    `blocks` is the display layout (`knowledge.passages.passage_blocks`): paragraphs, headings and
    lists, derived per request. The words are the stored words; only whitespace between them is
    normalised, and flattening the blocks reproduces `text`.
    """

    anchor: str
    locator: str
    page: int | None
    heading_path: str
    text: str
    blocks: tuple = ()
    #: True when this passage is a row of `Reader.grid`, whose cells carry its text. The template
    #: draws the grid once, at `grid.first_anchor`, and skips the row passages.
    in_grid: bool = False
    #: False when the passage above prints the same locator and page — one line per run, and the
    #: passage keeps its `id` either way.
    show_locator: bool = True


@dataclass(frozen=True)
class ReaderGridRow:
    """One reviewed artefact row, ready for a `<table>`.

    `cells` pairs each printed column's label with that cell's blocks, so the stacked phone layout
    can print the label beside the value (`data-label`) without the template indexing two tuples.
    Empty cells are kept (an empty list of blocks): the paper is silent there, and the template is
    what decides not to draw an empty labelled field.
    """

    anchor: str
    page: int | None
    cells: tuple[tuple[str, tuple], ...]
    #: True when this row starts on a different printed page from the row above — a table that
    #: crosses a page break (Step 3 is on p5) says so once.
    show_page: bool = True
    #: D77: the row's printed label (`Step 1`), or its first cell where the paper prints no
    #: number. The card's heading, when the reviewer wrote no title.
    label: str = ""
    #: D77: the reviewer's title for this row (`Get together`), or "" — the card then prints the
    #: label alone. Derived from the artefact, never from the row's words.
    title: str = ""
    #: D77: True when this row is an **alternative path** rather than a step — the rows from the
    #: reviewer's `branch:` onward. The template stacks these in the last column, dashed, with an
    #: `or` between them.
    is_path: bool = False
    #: D79 option E: True when a citation landed on this row. The template washes the row and the
    #: note above the table says why, so the row label and column heading the answer named are
    #: visible around the quoted cell instead of being asserted in a sentence elsewhere.
    is_cited: bool = False
    #: The column index of the quoted cell, when exactly one cell contains the quote. None when
    #: the quote spans cells (or none matched): the row is still marked, and no single cell is —
    #: pointing at one would claim the quote is that cell alone.
    cited_cell: int | None = None
    #: The printed text of each cell, in column order, before it is laid out into blocks. Kept for
    #: `_cited_row`, which has a citation's quote and needs the cell it came from.
    cell_texts: tuple[str, ...] = ()
    #: The heading(s) the paper prints immediately above this row (`I. PLANT AND ANIMAL ORIGIN`,
    #: `South African specific`). Empty for a table whose paper prints no heading inside it. The
    #: block carries them as `row-divider` annotations, so the artefact — not a Python constant —
    #: is what the reader draws.
    dividers: tuple[TableDivider, ...] = ()
    #: What the reader prints where a cell is empty (Appendix 2's *no condition printed*), or empty.
    note: str = ""


@dataclass(frozen=True)
class ReaderGrid:
    """The printed grid for a reviewed artefact table (D72.3, D77).

    `first_anchor` is where the template draws it: the first row's passage. Prose before and after
    the rows is rendered as ordinary passages, so the grid lands between them without the template
    tracking a cursor.

    `layout` says which shape: `grid` is one `<table>` (the seals comparison, D76), `process` is a
    card per step with its facets (D77). Both shapes read the same rows — only the markup differs.
    """

    columns: tuple[str, ...]
    legend: str
    first_anchor: str
    rows: tuple[ReaderGridRow, ...]
    #: `grid` or `process`, from the artefact's own `layout:` field.
    layout: str = "grid"
    #: `<doc_key>.<section anchor>`, the identity this table's column widths are stored under.
    #: The **artefact's** section anchor, not the branch's: a table with no lead-in takes its
    #: first row's anchor as the branch anchor, and a stored width must not move when a row is
    #: re-labelled.
    key: str = ""
    #: One heading per fee box, in printed order, or empty — the reviewer's words (`Steps 1–2`),
    #: never a label the renderer invented (D72.2).
    fee_labels: tuple[str, ...] = ()
    #: For `layout: process` only: the same rows, grouped the way a card needs them (D77 §12f.2).
    #: Empty for `grid` — the spreadsheet is `rows` + `columns` and needs no grouping.
    cards: tuple[ReaderCard, ...] = ()
    #: For `layout: process` only: the Fee cells as boxes under the cards they belong to.
    fee_boxes: tuple[ReaderFeeBox, ...] = ()

    # -- the process shape's groupings ------------------------------------------------
    #
    # Properties rather than fields: they are a view of `cards`, and a field would be a second
    # copy of the same fact (the rule `ReaderGridRow.cells` already follows for column labels).

    @property
    def steps(self) -> tuple[ReaderCard, ...]:
        """The cards before the fork, in printed order. Every card, for a linear table."""
        return tuple(card for card in self.cards if not card.is_path)

    @property
    def paths(self) -> tuple[ReaderCard, ...]:
        """The cards from the fork on — SAOSO's direct route. Empty for a linear table."""
        return tuple(card for card in self.cards if card.is_path)

    @property
    def card_columns(self) -> int:
        """How many columns the cards take: one per step, plus the split's own column."""
        return max(len(self.steps) + (1 if self.paths else 0), 1)

    @property
    def pointer_anchor(self) -> str:
        """The step the fork branches from — where Path A sends the reader (§12f.5)."""
        steps = self.steps
        return steps[-1].anchor if steps else ""

    @property
    def pointer_label(self) -> str:
        """That step's printed label (`Step 2`), so the pointer invents no wording of its own."""
        steps = self.steps
        return steps[-1].label if steps else ""


#: A `process` card's facets are named by the paper's own column heading (D77 §12f.2, amended
#: 2026-11-03 in `LANDSCAPE_TABLES_PRD` §12i): the two **text** columns fold away so the step body
#: leads. Every other heading renders visible — an unrecognised one is a **taller card, never a
#: lost cell**, which is why this is a prefix list and not a rule about what a column "is".
#: *Use of seals* used to stay visible "because it is the rule a reader checks"; on Step 3 that
#: rule is ten paragraphs, and the facet that did fold opened onto a picture caption, so the folds
#: moved to the prose.
FOLDED_FACETS = ("resource", "use of seals")


#: The heading of a column whose cell is a **picture's printed label**, not prose: the artwork is
#: not stored (D72.1), so at most a caption survives, and a control that opens onto a fragment of
#: an absent picture is worse than no control. Such a column is not drawn as a facet at all.
#: Safe only while the cell really is a label — `test_the_picture_column_holds_a_label_and_never_prose`
#: fails if a review ever puts a sentence here, so nothing disappears silently.
PICTURE_FACETS = ("seals and logos",)


#: The printed heading of the column whose cell becomes a fee box. The paper prints `Fee`; a
#: `process` table with no such column renders every cell as a facet and loses nothing.
FEE_COLUMN = "fee"


@dataclass(frozen=True)
class ReaderFacet:
    """One of a card's side columns: its printed heading and its blocks.

    `folded` is the fold decision, made once here rather than in the template — a card with six
    facets should not have the fold decision repeated six times in markup.
    """

    label: str
    blocks: tuple
    folded: bool = False


@dataclass(frozen=True)
class ReaderCard:
    """One step of a printed process, as a card (D77 C3).

    `body` is the first printed column — the step itself — with a leading block removed when it
    only repeats the label the card's heading already prints (`Step 1` is the first cell's first
    line **and** the heading, because the paper prints it inside the cell and the reviewer copied
    it into `<!-- row: Step 1 -->`). `facets` are every other column except the fee, and `label`
    plus `title` are reviewed data, never inferred.
    """

    anchor: str
    label: str
    title: str
    page: int | None
    show_page: bool
    body: tuple
    facets: tuple[ReaderFacet, ...]
    #: True when this card is an **alternative path** — the rows from the reviewer's `branch:`.
    is_path: bool = False
    #: `B`, `C`, … for a path card; empty for a step. The renderer adds the word `Path`; the
    #: ordinal is here so a table with two alternative paths does not need a template change.
    route: str = ""


@dataclass(frozen=True)
class ReaderFeeBox:
    """A Fee cell as a box under the card(s) it belongs to (D77 §12f.2, D72.2).

    `start` and `span` are in **cards**, 0-based: the merged Fee cell on `ESTABLISHING A PGS
    GROUP` starts under Step 1 and covers Steps 1–2, so it is `start=0, span=2`. The span is read
    from the printed emptiness that follows it — the paper prints one box across two rows and
    leaves the second row's Fee cell empty — never from the legend's prose.

    `blocks` is the **whole** cell. An amount on its own is the derived fact D72.2 refuses.
    """

    label: str
    blocks: tuple
    start: int
    span: int


def _card_body(blocks: tuple, label: str) -> tuple:
    """The step body, without the copy of the label the card's heading already prints.

    Called with the label **only when the card's heading prints it** — that is, for a step. A path
    card's heading is `Path B`, and its label is the opening of its own sentence (`For farmers
    wanting direct 3rd party certification to the SAOSO standard.`), so stripping it there would
    leave a fragment and reprinting it would say it twice.

    The paper prints `Step 1` as the first cell's first line, and the reviewer copies it into
    `<!-- row: Step 1 -->` — so the cell and the heading say it twice, and only the heading should.
    Two shapes, both measured on the real rows: the label is its own block (Step 1, read as a
    `Term`, which is what a printed sub-heading is) or the extraction merged it into the following
    sentence (Step 2, whose blank line the PDF's text layer lost). The second is stripped as a
    **prefix**, and only when the block carries no cross-reference segments — those point into the
    text that was there when they were built, and re-pointing them from here would be a guess.
    """
    if not label or not blocks:
        return blocks
    wanted = re.sub(r"\s+", " ", label).strip()
    first = blocks[0]
    text = getattr(first, "text", "")
    flat = re.sub(r"\s+", " ", text).strip()
    if flat == wanted:
        return blocks[1:]
    if flat.startswith(f"{wanted} ") and not getattr(first, "segments", ()):
        return (replace(first, text=flat[len(wanted) :].strip()), *blocks[1:])
    return blocks


def _folds(label: str) -> bool:
    lowered = label.strip().lower()
    return any(lowered.startswith(prefix) for prefix in FOLDED_FACETS)


def _is_picture(label: str) -> bool:
    lowered = label.strip().lower()
    return any(lowered.startswith(prefix) for prefix in PICTURE_FACETS)


def _cards_for(
    rows: tuple[ReaderGridRow, ...], fee_labels: tuple[str, ...] = ()
) -> tuple[tuple[ReaderCard, ...], tuple[ReaderFeeBox, ...]]:
    """In: the rows, with their cells, and the reviewer's fee labels. Out: cards and fee boxes.

    Why the span is derived and not inferred: the merged cell is *printed* as one box across two
    rows, and its second row's Fee cell is **recorded** as empty ("silence is not permission"). A
    fee box therefore runs until the next printed Fee cell, which is the same fact the legend
    states in prose — read from the cells, not from the sentence about them.
    """
    columns = tuple(column for column, _blocks in rows[0].cells) if rows else ()
    fee_index = next(
        (index for index, column in enumerate(columns) if column.strip().lower() == FEE_COLUMN),
        None,
    )
    cards: list[ReaderCard] = []
    printed_fees: list[tuple[int, tuple]] = []
    path_order = 0
    for position, row in enumerate(rows):
        body: tuple = ()
        facets: list[ReaderFacet] = []
        fee: tuple = ()
        for index, (column, blocks) in enumerate(row.cells):
            if index == 0:
                body = _card_body(blocks, "" if row.is_path else row.label)
            elif index == fee_index:
                fee = blocks
            else:
                if _is_picture(column):
                    continue
                facets.append(ReaderFacet(label=column, blocks=blocks, folded=_folds(column)))
        cards.append(
            ReaderCard(
                anchor=row.anchor,
                label=row.label,
                title=row.title,
                page=row.page,
                show_page=row.show_page,
                body=body,
                facets=tuple(facets),
                is_path=row.is_path,
                route="" if not row.is_path else chr(ord("B") + path_order),
            )
        )
        if row.is_path:
            path_order += 1
        if fee:
            printed_fees.append((position, fee))

    boxes: list[ReaderFeeBox] = []
    fallback = columns[fee_index] if fee_index is not None else "Fee"
    for order, (position, blocks) in enumerate(printed_fees):
        following = printed_fees[order + 1][0] if order + 1 < len(printed_fees) else len(rows)
        boxes.append(
            ReaderFeeBox(
                label=fee_labels[order] if order < len(fee_labels) else fallback,
                blocks=blocks,
                start=position,
                span=max(following - position, 1),
            )
        )
    return tuple(cards), tuple(boxes)


@dataclass(frozen=True)
class ReaderCitation:
    """`D79` option E on the reader: the row and cell an answer cited, from the printed table.

    The answer's citation shows a context line (row, column) and a quote. Following it must let
    a reader *see* that context, not take it on trust: this is what the reader marks — the row,
    and the one cell the quote occupies, under its printed heading. Every field comes from the
    `ArtefactGrid` the reader already draws; the `quote` is the only thing the URL carries, and
    a quote that matches no cell produces no marks rather than a wrong one.
    """

    row_anchor: str
    row_label: str
    column: str
    quote: str
    #: Index into `ReaderGridRow.cells` for the quoted cell, or None when the quote spans cells.
    cell_index: int | None = None


def _artefact_grid(
    document_row: StandardDocument,
    selected: ConcordanceSection | None,
    texts: tuple[str, ...],
    anchors: list[str],
    pages: list[int | None],
    section_refs: frozenset[str] = frozenset(),
) -> tuple[ReaderGrid | None, set[int]]:
    """The printed grid for a branch whose rows live in a reviewed artefact, or `(None, set())`.

    In:  `document_row` — the ingested twin; `selected` — the open branch; `texts` — the passage
         texts about to be rendered; `anchors`/`pages` — their locators and pages;
         `section_refs` — the clause references the branch's own passages carry.
    Out: the grid (columns, legend, rows with per-cell blocks) and the passage positions it covers.
         `(None, set())` for every branch that is not a reviewed artefact table, and for a corpus
         that disagrees with the artefact (a stale row, a re-ordered branch) — the plain page is
         what the reader renders today, and a mislabelled grid is worse than none.
    Side effects: one file read (`knowledge/corpus/<doc>.md`), no queries.
    Fails: never. A missing or malformed artefact falls back, because a published document whose
        review is absent must still render its corpus text.
    """
    if selected is None:
        return None, set()
    doc_key = doc_key_for(document_row.source_file)
    path = corpus_artifact(doc_key) if doc_key else None
    if path is None or not path.is_file():
        return None, set()
    try:
        reviewed = load_document(path)
    except (OSError, ValueError):
        return None, set()
    section = next(
        (
            section
            for section in reviewed.sections
            # The branch's anchor is its **first passage's** anchor, which for a table whose first
            # chunk is a row is the row's anchor (the seals table has no lead-in). The section's
            # own anchor survives on the prose passage after the rows, so match either.
            if (
                section.anchor == selected.anchor
                or section.anchor in anchors
                # A numbered clause's reading anchor is its reference (`2-3`), not the
                # artefact's heading slug, so the anchor join cannot find it. The OPP's
                # §2.3 is the first table in a *numbered* document; the landscape's sections
                # are unnumbered, which is why the anchor alone was enough there.
                or (section.section_ref and section.section_ref in section_refs)
            )
            # A branch may hold several sections and one of them may be a table. The OPP's
            # `II. Membership fees` branch is §2.1–§2.5 with §2.3's sliding scale in the middle:
            # matching on the branch alone picked §2.1, which has no table, and returned no grid
            # (measured 2026-11-01, P4). The first section that *has* a table is the one to draw.
            and section.tables
        ),
        None,
    )
    if section is None:
        return None, set()
    grid = artefact_grid_for(section)
    if grid is None:
        return None, set()
    positions = align_artefact_grid(grid, texts)
    if positions is None:
        return None, set()

    rows: list[ReaderGridRow] = []
    previous_page: int | None = None
    for index, (position, cells) in enumerate(zip(positions.positions, grid.rows)):
        page = pages[position]
        rows.append(
            ReaderGridRow(
                anchor=anchors[position],
                page=page,
                show_page=page != previous_page,
                label=grid.labels[index] if index < len(grid.labels) else "",
                title=grid.title_for(index),
                # The split is a *passage*, so a branch row is one whose passage is at or after
                # it — which is the same thing as `index >= grid.branch`, said in the terms the
                # corpus agreed to.
                is_path=positions.split is not None and position >= positions.split,
                cells=tuple(
                    (column, passage_blocks(cell_text))
                    for column, cell_text in zip(grid.columns, cells)
                ),
                cell_texts=tuple(cells),
                dividers=tuple(
                    TableDivider(index, text, kind)
                    for text, kind in (
                        grid.dividers[index] if index < len(grid.dividers) else ()
                    )
                ),
                # The silence label belongs to the row that *is* silent: a label on every row would
                # be a claim about rows the paper prints conditions for.
                note=(
                    grid.silence
                    if grid.silence and any(not cell.strip() for cell in cells)
                    else ""
                ),
            )
        )
        previous_page = page
    cards, fee_boxes = (
        _cards_for(tuple(rows), grid.fee_labels) if grid.layout == "process" else ((), ())
    )
    return (
        ReaderGrid(
            columns=grid.columns,
            legend=grid.legend,
            layout=grid.layout,
            key=f"{doc_key}.{section.anchor}",
            fee_labels=grid.fee_labels,
            cards=cards,
            fee_boxes=fee_boxes,
            first_anchor=anchors[positions.positions[0]],
            rows=tuple(rows),
        ),
        set(positions.positions),
    )


def _cited_row(
    grid: ReaderGrid | None, section: str, quote: str
) -> ReaderCitation | None:
    """In: a branch's grid, the `?section=` value and the citation's quote. Out: the mark, or None.

    `D79` option E's reader half. The answer's citation shows a row and a column as *context*;
    this finds the same row in the printed table so the page can mark it and name the same
    column. Two rules keep it honest:

    * a quote that matches no cell marks **nothing** — the citation still opens the branch, and
      an unmarked table is better than a highlighted wrong row (the fallback `_artefact_grid`
      already follows when a corpus disagrees with the artefact);
    * a quote that spans cells marks the row but **no cell**, because a single-cell mark would
      say the quote is that one cell.

    The row is chosen by the `?section=` anchor when it names a row, because that is the row the
    citation's fragment will scroll to; the quote then only decides the cell. Otherwise the first
    row whose cells contain the quote is used.
    """
    if grid is None or not quote.strip():
        return None
    wanted = " ".join(quote.split())
    wanted_section = section.strip()
    row = next((row for row in grid.rows if row.anchor == wanted_section), None)
    if row is None:
        row = next(
            (
                row
                for row in grid.rows
                if wanted in " ".join(" ".join(row.cell_texts).split())
            ),
            None,
        )
    if row is None:
        return None
    matches = [
        index
        for index, cell in enumerate(row.cell_texts)
        if wanted and wanted in " ".join(cell.split())
    ]
    index = matches[0] if len(matches) == 1 else None
    return ReaderCitation(
        row_anchor=row.anchor,
        row_label=row.label,
        column=(
            grid.columns[index]
            if index is not None and index < len(grid.columns)
            else ""
        ),
        quote=quote.strip(),
        cell_index=index,
    )
