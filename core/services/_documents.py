"""The public document library — which files are published, and how they get there.

Two jobs, deliberately in one module because they are the same decision seen twice:
**what the group publishes** (`DOCUMENTS`, the data) and **how the served copy comes
to exist** (`publish_documents`, the deploy step). Splitting them invites the two to
disagree — a spec added here and never copied would 503 at request time, which is why
the copy and the row are written from the same tuple in one pass.

**The list is eight, not seven.** `MVP0_PLAN_V2.md` C2 says "exactly seven items
(D22)" and then names eight; `pgs_docs/` has eight PDFs. D22's ninth candidate — the
assessment workbook (`…summary_2026.xlsx`) — is excluded until the committee confirms
it, and it is excluded by *not being in this tuple* rather than by a flag, so no
template can render it and no test has to trust a boolean.

**Where the files go.** `MEDIA_ROOT/public/documents/<code>.pdf`, never a media URL.
`build_principles.md` §VI keeps public derivatives under a separate public root and
forbids publishing the private root; the `public/` prefix is that boundary. Serving
goes through `core/views/_documents.py`, so `is_published` is consulted on every
request — a static file at a guessable path could not offer that.

**Idempotent on content, not on timestamp.** The copy compares sha256, so re-running
on every deploy neither rewrites 8.6 MB of unchanged files nor leaves a half-written
one visible: the bytes land in a temporary file and are renamed into place.
"""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import NamedTuple

from django.conf import settings
from django.db import transaction
from django.urls import reverse

from core.models import PublicDocument
from knowledge.concordance import ConcordanceSection, build_concordance
from knowledge.corpus import load_document
from knowledge.ingest import CORPUS_DOCUMENTS, corpus_artifact, doc_key_for
from knowledge.models import DocumentChunk, StandardDocument
from knowledge.passages import passage_blocks, row_blocks
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
from knowledge.glossary import GLOSSARY_BRANCH, glossary_entries, with_term_anchors
from knowledge.references import annotate, build_reference_index
from knowledge.tables import (
    TableDivider,
    TableStructure,
    align_artefact_grid,
    artefact_grid_for,
    structure_for,
)

logger = logging.getLogger(__name__)

#: The shipped documents. `PDF`s only: D22's workbook is not here until the committee
#: confirms it, and `content_inventory.md` §6.8's pledge downloads are not D22 items.
#:
#: Anchored to `BASE_DIR`, NOT a bare `Path("pgs_docs")`. A relative path resolves
#: against the process's working directory, and the two callers that matter do not
#: share one: systemd sets `WorkingDirectory` to the app dir, while a provisioning
#: script run as `sudo bash /home/carbonplanner/apps/pgs/deploy/first-install.sh`
#: inherits the caller's `~`. The first production install failed exactly here —
#: `CommandError: saoso-standard-v2.1: pgs_docs/saoso-version-2.1-2026.pdf is not in
#: the tree` — with all eight PDFs present in the checkout.
DOCS_SOURCE_DIR = Path(settings.BASE_DIR) / "pgs_docs"

#: Under MEDIA_ROOT. The `public/` segment is the boundary from PRIVATE_MEDIA_ROOT.
PUBLIC_SUBDIR = Path("public") / "documents"


@dataclass(frozen=True)
class DocumentSpec:
    """One document the group publishes.

    In: none. Out: a row and a served file. Side effects: none.
    Fails: nothing here — `publish_documents` fails if `source` is not on disk.

    `note` is the one-line description the design prints under the title. It is in
    Python rather than in a template for the same reason the fee figures are: one
    source, and a test can compare the two pages that show the same document.
    """

    code: str
    title: str
    note: str
    source: str
    download_name: str
    display_order: int
    is_published: bool = True


#: Order follows the documents page and the home page's band: the four governed
#: documents first (D16's corpus), then the working forms.
DOCUMENTS: tuple[DocumentSpec, ...] = (
    DocumentSpec(
        code="saoso-standard-v2.1",
        title="SAOSO Organic Standard v2.1",
        note="The standard we assess against · 2026",
        source="saoso-version-2.1-2026.pdf",
        download_name="SAOSO-Organic-Standard-v2.1.pdf",
        display_order=10,
    ),
    DocumentSpec(
        code="opp",
        title="Principles, Policies & Procedures",
        note="How our own PGS is governed",
        source="Outeniqua pgs principles, policies and procedures 2026.pdf",
        download_name="Outeniqua-PGS-Principles-Policies-Procedures.pdf",
        display_order=20,
    ),
    DocumentSpec(
        code="basic-production-principles",
        title="Basic Production Principles",
        note="Growing the organic sector in South Africa",
        source="Basic Production Principles_ENG_PRINT.pdf",
        download_name="Basic-Production-Principles.pdf",
        display_order=30,
    ),
    DocumentSpec(
        code="certification-landscape",
        title="Certification Landscape",
        note="Seals and recognition in the SA organic sector",
        source="PGS Certification landscape_Final.pdf",
        download_name="Certification-Landscape.pdf",
        display_order=40,
    ),
    DocumentSpec(
        code="farm-visit-preparation",
        title="Farm Visit Preparation List",
        note="What to have ready before the visit",
        source="5. PGS Farm Visit preparation list.pdf",
        download_name="PGS-Farm-Visit-Preparation-List.pdf",
        display_order=50,
    ),
    DocumentSpec(
        code="checklist-crops",
        title="Checklist — Crops",
        note="Blank participant checklist",
        source="7.a  PGS Farm Visit Checklist_ Crops.pdf",
        download_name="PGS-Farm-Visit-Checklist-Crops.pdf",
        display_order=60,
    ),
    DocumentSpec(
        code="checklist-crops-animals",
        title="Checklist — Crops & Animals",
        note="Blank participant checklist",
        source="7.b PGS Farm Visit Checklist - Crops _ Animals.pdf",
        download_name="PGS-Farm-Visit-Checklist-Crops-and-Animals.pdf",
        display_order=70,
    ),
    DocumentSpec(
        code="checklist-seed-production",
        title="Checklist — Seed Production",
        note="Blank participant checklist",
        source="7.c  PGS Farm Visit Checklist - Seed Production.pdf",
        download_name="PGS-Farm-Visit-Checklist-Seed-Production.pdf",
        display_order=80,
    ),
)


class PublishResult(NamedTuple):
    """What `publish_documents` did. Printed by the command, asserted by the tests."""

    created: int
    updated: int
    copied: int
    unchanged: int

    def __str__(self) -> str:
        return (
            f"created={self.created} updated={self.updated} "
            f"copied={self.copied} unchanged={self.unchanged}"
        )


class DocumentSourceMissing(RuntimeError):
    """A spec names a file the repository does not ship. Never silently skipped."""


def sha256_of(path: Path) -> str:
    """The digest both the copy step and the tests compare. Read in chunks: the BPP
    is 4.6 MB and reading several of those whole into memory buys nothing."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 256), b""):
            digest.update(block)
    return digest.hexdigest()


def absolute_path(document: PublicDocument) -> Path:
    """Where the served file lives, resolved **at call time**.

    Not a `FileField` — see `core/models/_public.py` for why a storage location is the
    wrong thing to cache here.
    """
    return Path(settings.MEDIA_ROOT) / document.file_path


def published_documents() -> list[PublicDocument]:
    """The documents a public page may show. One query, ordered by the seed."""
    return list(PublicDocument.objects.published())


@dataclass(frozen=True)
class DocumentRow:
    """One line of the public document list: the file, and where its text can be read.

    `read_url` is empty for a document whose text is not ingested. That is not a disabled
    control: a form is published as a file, and that is the whole truth about it
    (`DOCUMENTS_READER_LINK_PRD` D2). The row prints nothing rather than a promise the
    reader page would have to take back.
    """

    document: PublicDocument
    read_url: str = ""


def public_codes_by_source() -> dict[str, str]:
    """In: nothing. Out: `{source_file: code}` for the published documents. One query.

    The join that makes a citation clickable without a migration: `PublicDocument.source_path`
    and `StandardDocument.source_file` both hold `pgs_docs/<file>.pdf`, because the publish
    seed and the ingest read the same filenames — `source_path` exists precisely so a
    published file can be traced to the shipped document.

    A corpus document with no published twin is simply absent from the mapping, and a
    citation from it renders as text rather than as a link to nowhere. Only **published**
    documents are listed: `is_published` is the only gate, and a citation is not an exception
    to it.
    """
    return {
        document.source_path: document.code
        for document in PublicDocument.objects.published().exclude(source_path="")
    }


def documents_context() -> dict:
    """The context fragment every page that carries the list needs.

    In: none. Out: `{"documents": [DocumentRow, ...]}`. Side effects: two queries.
    Fails: never deliberately.

    Each row carries the reader's address **when the document's text is ingested**, and an
    empty string when it is not. The set is resolved once for the whole list rather than by
    asking `corpus_for()` per row: that function is a query, and a public page must not grow a
    query each time the group publishes a ninth document (`DOCUMENTS_READER_LINK_PRD` §4).
    """
    documents = published_documents()
    with_text = ingested_sources()
    return {
        "documents": [
            DocumentRow(
                document=document,
                read_url=(
                    reverse("core:document_reader", kwargs={"code": document.code})
                    if document.source_path in with_text
                    else ""
                ),
            )
            for document in documents
        ]
    }


def ingested_sources() -> set[str]:
    """In: nothing. Out: the `source_file` of every corpus document that holds text.

    One query, and the join is provenance: `PublicDocument.source_path` and
    `StandardDocument.source_file` both hold `pgs_docs/<file>.pdf`, because the publish seed
    and the ingest read the same filenames.

    Derived from `DocumentChunk`, not from `StandardDocument.chunk_count`: a denormalised
    counter is one interrupted ingest away from promising a reader a page with no text in it,
    and this is the value that decides whether the row prints the link at all.
    """
    return set(
        DocumentChunk.objects.values_list("document__source_file", flat=True).distinct()
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
    #: The printed divider(s) the paper puts immediately above this row (`I. PLANT AND ANIMAL
    #: ORIGIN`, `South African specific`). Empty for a passage that is not a reviewed row.
    dividers: tuple[TableDivider, ...] = ()
    #: What the paper's condition cell says where it says nothing: a label, never a condition.
    note: str = ""
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


#: A `process` card's facets are named by the paper's own column heading (D77 §12f.2):
#: `Resource documents, guidelines and requirements` and `Seals and logos` fold away so the step
#: body leads. Every other heading renders visible — an unrecognised one is a **taller card, never
#: a lost cell**, which is why this is a prefix list and not a rule about what a column "is".
FOLDED_FACETS = ("resource", "seals and logos")

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


@dataclass(frozen=True)
class Reader:
    """Everything `/documents/<code>/read/` renders — the concordance.

    One section at a time, with the document's own structure as the navigation: the reader is
    the standard's table of contents, not a page of text with a list beside it. That is also what
    makes the page light — only the selected branch is rendered, so a 319-passage document costs
    one branch's markup instead of 333 KB of it (D68).
    """

    document: PublicDocument
    corpus: StandardDocument | None
    sections: tuple[ConcordanceSection, ...]
    selected: ConcordanceSection | None
    passages: tuple[ReaderPassage, ...]
    #: Printed sections with text that no branch covers — stated on the page (§10.6).
    missing: tuple[str, ...]
    hits: tuple[SearchHit, ...]
    query: str
    section: str
    #: The branch's reviewed structure, when its rows were curated: the printed caption, the
    #: legend sentence and the dividers (D70.1). None for every other branch.
    table: TableStructure | None = None
    #: The printed grid for a reviewed artefact table (D72.3) — the landscape's five columns.
    #: Distinct from `table`: that is the two-column appendix shape, this is a real grid.
    grid: ReaderGrid | None = None
    #: D79 option E: the row and cell a citation landed on, when the URL carried its quote.
    cited: ReaderCitation | None = None

    @property
    def title(self) -> str:
        """The document and the open branch — what a `<title>` says, and what a search result
        shows. A branch page is about a section, not about the whole document."""
        if self.selected is None:
            return self.document.title
        return f"{self.document.title} — {self.selected.title}"

    @property
    def canonical_path(self) -> str:
        """The one address for this branch. The `?section=` form, because the branch has to
        travel in the query string: a browser never sends the fragment to the server (§6.4)."""
        base = reverse("core:document_reader", kwargs={"code": self.document.code})
        return f"{base}?section={self.selected.anchor}" if self.selected else base


def corpus_for(document: PublicDocument) -> StandardDocument | None:
    """In: a published document. Out: the ingested twin, or None. One query.

    The join is provenance, not guesswork: `source_path` and `source_file` both hold
    `pgs_docs/<file>.pdf` because the publish seed and the ingest read the same filenames.
    When a document exists in two corpora the deployed default wins, so the reader shows the
    text the assistant is actually answering from.
    """
    return (
        StandardDocument.objects.filter(source_file=document.source_path)
        .select_related("standard_set")
        .order_by("-standard_set__is_default", "id")
        .first()
    )


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


def _select_section(
    sections: list[ConcordanceSection], wanted: str
) -> ConcordanceSection | None:
    """Which branch the reader is on. Accepts a branch anchor **or** any passage anchor.

    Both are needed and they are not the same thing: the tree navigates by section, while a
    citation names a passage (`s20-1-1`), and a citation's link must land on the branch that
    contains that passage. An unknown value falls back to the first branch rather than 404ing —
    a stale link should still show the reader the document.
    """
    if not sections:
        return None
    if not wanted:
        return sections[0]
    for section in sections:
        if section.anchor == wanted:
            return section
    for section in sections:
        if any(anchor == wanted for _chunk, anchor in section.passages):
            return section
    return sections[0]


def reader_for(
    document: PublicDocument, query: str = "", section: str = "", quote: str = ""
) -> Reader:
    """In: a published document, what the reader searched for, which branch, and the quote.

    In:  `query` — free text from the search box; `section` — the branch to open, by branch
         anchor or by any passage anchor (a citation names a passage, not a section); `quote`
         — the cell a citation quoted, when the visitor arrived from one (`D79` option E).
    Out: the document's section tree (including reserved rows), the selected branch, that
         branch's passages, the printed sections the corpus does not hold, and any search hits —
         searched across the **whole** document, not the open branch, because a reader who
         searches is looking for where a word is, not whether it is here.
    Side effects: at most four queries.
    Fails: never. A published document whose text has not been ingested returns `corpus=None`;
        the view explains, because a citation pointing here must not 404.
    """
    document_row = corpus_for(document)
    if document_row is None:
        return Reader(
            document=document,
            corpus=None,
            sections=(),
            selected=None,
            passages=(),
            missing=(),
            hits=(),
            query=query.strip(),
            section=section.strip(),
        )

    concordance = build_concordance(document_row)
    sections = list(concordance.sections)
    selected = _select_section(sections, section.strip())
    pairs = {
        chunk.pk: anchor for chunk, anchor in unique_anchors(reading_chunks(document_row))
    }
    # Adjacent chunks of one printed section overlap on purpose, so retrieval can see both
    # sides of a boundary. A reader must not: `S1`'s eight chunks repeat 21–57 words at five
    # boundaries, and the definitions page printed the previous chunk's tail again at the top
    # of the next one. The stored text is untouched; only what this page renders is trimmed.
    branch_pairs = selected.passages if selected is not None else ()
    texts = branch_texts(branch_pairs)
    # The printed grid, when this branch's rows were reviewed into the artefact (D72.3). Built from
    # the same texts the page is about to render, so a corpus that disagrees falls back instead of
    # labelling a row it cannot vouch for — `align_artefact_grid` returns None, not a guess.
    grid, grid_positions = _artefact_grid(
        document_row,
        selected,
        texts,
        [pairs[chunk.pk] for chunk, _anchor in branch_pairs],
        [chunk.page for chunk, _anchor in branch_pairs],
        frozenset(
            chunk.section_ref for chunk, _anchor in branch_pairs if chunk.section_ref
        ),
    )

    # The reviewed structure is looked up against the text that is about to be rendered, so a
    # corpus that no longer matches the reviewed rows falls back to today's page instead of
    # labelling rows it cannot vouch for (`knowledge.tables.structure_for`).
    section_ref = branch_pairs[0][0].section_ref if branch_pairs else None
    structure = structure_for(section_ref, tuple(texts))
    # `D79` option E, reader side: a citation that carried its quote marks the row it landed on
    # and the cell it quoted. The mark is built from the grid the page is about to draw, so the
    # note above the table and the highlighted cells cannot disagree about which row it is.
    cited = _cited_row(grid, section, quote)
    if cited is not None and grid is not None:
        grid = replace(
            grid,
            rows=tuple(
                replace(
                    row,
                    is_cited=row.anchor == cited.row_anchor,
                    cited_cell=(
                        cited.cell_index if row.anchor == cited.row_anchor else None
                    ),
                )
                for row in grid.rows
            ),
        )
    # One index per request, built from the tree the page already rendered: a reference can only
    # point at a branch that is in it.
    index = build_reference_index(document_row, sections)
    # One locator per run: 30 Appendix 2 rows share three locator lines, and 52 of `S5`'s clauses
    # share one. Every passage keeps its id, so a citation still lands on the row it quotes.
    show_locator = printed_locators(
        [(passage_locator(chunk), chunk.page) for chunk, _anchor in branch_pairs]
    )

    # The glossary, for the branch that defines the document's words: derived from the blocks the
    # reader would render there (so the ids and the links cannot disagree), from data already in
    # hand — one branch's passages, no query.
    glossary_key = GLOSSARY_BRANCH.get(document_row.source_file)
    glossary_section = next((entry for entry in sections if entry.key == glossary_key), None)
    terms = {}
    if glossary_section is not None:
        glossary_blocks = [
            block
            for text in branch_texts(glossary_section.passages)
            for block in passage_blocks(text)
        ]
        terms = {
            entry.term: entry
            for entry in glossary_entries(
                document_row.source_file, glossary_blocks, glossary_section.anchor
            )
        }
    term_seen: set[str] = set()

    rows: list[ReaderPassage] = []
    for position, ((chunk, _anchor), text) in enumerate(zip(branch_pairs, texts)):
        blocks = row_blocks(text) if structure is not None else passage_blocks(text)
        rows.append(
            ReaderPassage(
                anchor=pairs[chunk.pk],
                locator=passage_locator(chunk),
                page=chunk.page,
                heading_path=chunk.heading_path,
                text=text,
                blocks=annotate(
                    with_term_anchors(blocks, term_seen)
                    if selected is not None and selected.key == glossary_key
                    else blocks,
                    index,
                    open_branch=selected.key if selected is not None else "",
                    terms=terms,
                ),
                dividers=structure.dividers[position] if structure is not None else (),
                note=structure.labels[position] if structure is not None else "",
                show_locator=show_locator[position],
                in_grid=position in grid_positions,
            )
        )
    passages = tuple(rows)
    return Reader(
        document=document,
        corpus=document_row,
        sections=tuple(sections),
        selected=selected,
        passages=passages,
        missing=concordance.missing,
        hits=tuple(search_in_document(document_row, query, anchors=pairs)) if query.strip() else (),
        query=query.strip(),
        section=section.strip(),
        table=structure,
        grid=grid,
        cited=cited,
    )


def _recorded_source(source: Path) -> str:
    """The path as `source_path` records it: repository-relative whenever it can be.

    Absolute would be wrong in two ways. It differs per machine, so the provenance column
    would say something different on every deployment; and it would never equal
    `StandardDocument.source_file`, which is the *join a citation uses* to find its public
    address (`public_codes_by_source`). The field's own help text has always promised
    `pgs_docs/<file>.pdf`, and that is what this returns — `ingest._relative_source` does the
    same thing for the corpus side, because the two must agree for a citation to be clickable.
    """
    try:
        return source.resolve().relative_to(Path(settings.BASE_DIR).resolve()).as_posix()
    except ValueError:  # a `--source-dir` outside the tree; keep the trace we can
        return source.resolve().as_posix()


def _destination(source: Path, destination: Path) -> bool:
    """Copy `source` to `destination` if the bytes differ. Returns True if copied.

    Written via a temporary file in the same directory and an atomic replace: a deploy
    interrupted mid-copy must not leave a truncated PDF that `publish_documents` then
    considers up to date because a path exists at all.
    """
    if destination.is_file() and sha256_of(destination) == sha256_of(source):
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f".{destination.name}.part")
    shutil.copyfile(source, staging)
    staging.replace(destination)
    return True


@transaction.atomic
def publish_documents(source_dir: Path | None = None) -> PublishResult:
    """Copy the shipped documents into the public media root and upsert the rows.

    In:      an optional directory to read from (defaults to `pgs_docs/`).
    Out:     `PublishResult(created, updated, copied, unchanged)`.
    Side effects: writes under `MEDIA_ROOT/public/documents/` and to `PublicDocument`.
    Fails:   `DocumentSourceMissing` if a spec names a file that is not shipped —
             loudly, because the alternative is a page linking to a 503.
    Idempotency: yes, on content. A second run copies nothing, creates nothing and
             updates nothing unless a spec actually changed.

    The rows are written in one transaction (§VI). The *files* cannot be — a
    filesystem has no rollback — so a crash between a copy and its row leaves an
    unreferenced file, never a row without a file. The sha256 comparison makes the
    next run's copy a no-op either way, which is why the atomicity here is about the
    rows and the idempotency is about both.
    """
    origin = Path(source_dir) if source_dir is not None else DOCS_SOURCE_DIR
    created = updated = copied = unchanged = 0

    for spec in DOCUMENTS:
        source = origin / spec.source
        if not source.is_file():
            raise DocumentSourceMissing(
                f"{spec.code}: {source.resolve()} is not in the tree. The published copy "
                f"would have nothing to serve, and /documents/{spec.code}/ would 503."
            )

        relative = (PUBLIC_SUBDIR / f"{spec.code}{source.suffix}").as_posix()
        destination = Path(settings.MEDIA_ROOT) / relative
        if _destination(source, destination):
            copied += 1
        else:
            unchanged += 1

        defaults = {
            "title": spec.title,
            "note": spec.note,
            "file_path": relative,
            "content_type": "application/pdf",
            "source_path": _recorded_source(source),
            "download_name": spec.download_name,
            "display_order": spec.display_order,
        }
        # D22 is group data: a *newly* seeded document is published as the spec says,
        # but a group that unpublishes one keeps it unpublished. `is_published` is
        # therefore applied on create only, exactly as `Seal.is_active` is — a release
        # must never silently republish a document the group took down.
        document, was_created = PublicDocument.objects.get_or_create(
            code=spec.code,
            defaults={**defaults, "is_published": spec.is_published},
        )
        if was_created:
            created += 1
            continue

        changed = [field for field, value in defaults.items() if getattr(document, field) != value]
        if changed:
            for field in changed:
                setattr(document, field, defaults[field])
            document.save(update_fields=changed)
            updated += 1

    # The keys are prefixed because `extra` may not shadow a LogRecord attribute:
    # `created` is the record's own timestamp, and passing it raises KeyError at log
    # time rather than at import — the seed is otherwise fine and the failure looks
    # like a test problem. Same family as `name`, `args`, `levelname`.
    logger.info(
        "public documents published",
        extra={
            "documents_created": created,
            "documents_updated": updated,
            "documents_copied": copied,
            "documents_unchanged": unchanged,
        },
    )
    return PublishResult(created, updated, copied, unchanged)
