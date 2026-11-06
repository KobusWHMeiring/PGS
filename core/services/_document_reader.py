"""The document reader: which document, which branch, which passages - and the page.

Split out of `core/services/_documents.py` (CONTEXT_CUTS_PRD step 7). `_documents.py` owns
**what the group publishes** and **how the served copy comes to exist**; this module owns
**what a reader sees**: the section tree as navigation, the one open branch, the passages in
it, the search hits across the whole document, and the citation a URL can carry. The shapes
it renders live in `_document_shapes.py`.

It reads the ingested corpus and the reviewed artefact, and writes nothing: three or four
queries per page, no rows. `_documents` re-exports `reader_for`, so
`from core.services._documents import reader_for` still works.
"""

from __future__ import annotations


from dataclasses import dataclass, replace
from django.urls import reverse
from core.models import PublicDocument
from knowledge.concordance import ConcordanceSection, build_concordance
from knowledge.glossary import GLOSSARY_BRANCH, glossary_entries, with_term_anchors
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
from knowledge.references import annotate, build_reference_index
from knowledge.tables import (
    TableDivider,
    align_artefact_grid,
    artefact_grid_for,
)

from core.services._document_shapes import (
    ReaderCitation,
    ReaderGrid,
    ReaderPassage,
    _artefact_grid,
    _cited_row,
)


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
    #: The printed grid for a reviewed artefact table (D72.3) — a two-column appendix as much as
    #: the landscape's five columns. Every reviewed table is the artefact's own block, so the
    #: reader draws it from the same parse the ingest chunks (S5).
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
    # **A grid's cells carry the document's references too.** The rows used to be passages, so
    # `annotate` reached their words on the way to the template; the grid is drawn from
    # `_artefact_grid` before the index exists, so the annotation is applied here, once, after it.
    # Measured 2026-11-05 (the first S5-b run): `See Section B – Appendix 6 …` in a condition cell
    # rendered as text, which is the regression this fixes. Terms are not linked inside a cell: a
    # table cell is not a glossary definition, and `_passage_blocks.html` would print an id per
    # occurrence of a word the paper uses as a substance.
    if grid is not None:
        grid = replace(
            grid,
            rows=tuple(
                replace(
                    row,
                    cells=tuple(
                        (
                            column,
                            annotate(
                                blocks,
                                index,
                                open_branch=selected.key if selected is not None else "",
                            ),
                        )
                        for column, blocks in row.cells
                    ),
                )
                for row in grid.rows
            ),
        )
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

    # The reviewed table is the artefact's own block now, and it reached the page through `grid`
    # above: `structure_for` and the Python rows it compared are gone (S5-b).
    rows: list[ReaderPassage] = []
    for position, ((chunk, _anchor), text) in enumerate(zip(branch_pairs, texts)):
        blocks = passage_blocks(text)
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
        grid=grid,
        cited=cited,
    )
