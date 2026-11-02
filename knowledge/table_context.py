"""The reviewed table a passage belongs to, and the rows that make it whole (D79/E).

`G10`'s last measurement is the reason this module exists. The assistant can name the
membership fee and the assessment fee's *rule*, and cannot state a single band: the band
row it would need is `Below R 250,000 / 1,500 / 900` — three cells with no column meaning
on the line the paper prints them, and no word in common with any question. Slice 1
(`SEMANTIC_SEATS`, the semantic arm's own order) made such a row *reachable*; it did not
make it *reliable*, because the six bands sit within 0.023 of each other in the vector arm
and their order is noise. **No similarity ranking chooses a band.**

So the unit has to be the table. When any passage of a reviewed table is retrieved — the
section's introduction is enough, and it is the one that *is* reliably retrieved — the
table's rows travel with it, and the prompt shows the model the printed columns once.

**What this module does not do.** It does not put a heading into chunk text (`D69`: the
corpus is the paper's characters, and option A was rejected for exactly that), and it does
not render the row's context into a citation — that is slice 3, and `Citation.row_label`
is the identity it will need. Here, the label is *structure*: it tells the prompt which
cell sits under which column, and it is never a quote target.

**Cost.** One `stat` per candidate document, one cached artefact parse (keyed on the
file's mtime and size, so a regenerated corpus is never read stale), and one query per
table that arrives. Only the OPP and the landscape artefact hold `<!-- table -->` blocks
today; the marker check happens before any parsing, so a SAOSO question pays a 170 KB read
and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from knowledge.corpus import load_document
from knowledge.models import DocumentChunk, StandardSet
from knowledge.tables import ArtefactGrid, artefact_grid_for

#: How many of a table's rows one question may add to the set. The OPP's sliding scale is
#: six bands and the landscape's largest table is eight rows, so this covers a whole table
#: and bounds the prompt. It is a *cap on rows added*, not a lid on the passage set: the
#: retrieved passages keep their positions, which is why a table can arrive without
#: reordering — or losing — the evidence a question already had.
TABLE_ROW_SEATS = 8

#: What a reviewed table block looks like in an artefact. Checked before parsing anything.
_TABLE_MARKER = "<!-- table"


@dataclass(frozen=True)
class TableContext:
    """The printed table a passage is part of, as the prompt needs it.

    Carried on `RetrievedChunk` rather than looked up again in `build_prompt`, because a
    prompt built from a second trip to disk is a prompt that can disagree with the passages
    it renders. `row_label` is the printed label of *this* passage's row, or "" when the
    passage is the section's prose (the introduction, or the notes under the table).
    """

    title: str
    columns: tuple[str, ...]
    section_ref: str | None = None
    row_label: str = ""

    @property
    def key(self) -> tuple[str, ...]:
        """What makes two passages members of the same table.

        The title and the columns, not the section reference: a landscape section prints
        no numbering, and two tables with the same columns in one section would be one
        block anyway.
        """
        return (self.title, *self.columns)


@dataclass(frozen=True)
class ReviewedTable:
    """One reviewed artefact table: its heading, its printed columns, and its rows."""

    title: str
    columns: tuple[str, ...]
    rows: tuple[str, ...]
    labels: tuple[str, ...]
    section_ref: str | None = None

    def row_label(self, text: str) -> str | None:
        """In: a passage's text. Out: the printed label of the row it is, or None.

        Whitespace-normalised equality against the row's cells joined by newlines — the
        same normal form the citation audit uses, so a row the prompt calls a row is a row
        the audit can check.
        """
        wanted = " ".join(text.split())
        for cells, label in zip(self.rows, self.labels):
            if " ".join(cells.split()) == wanted:
                return label
        return None

    def context_for(self, text: str) -> TableContext:
        return TableContext(
            title=self.title,
            columns=self.columns,
            section_ref=self.section_ref,
            row_label=self.row_label(text) or "",
        )


def reviewed_table_for(document_source_file: str | None, text: str) -> ReviewedTable | None:
    """In: a passage's document and its text. Out: the reviewed table it belongs to, or None.

    Matches a **row** by its cells. The introduction is deliberately not matched here: it
    is not a row, and calling it one would put a column heading over a paragraph.
    """
    for table in _tables_of(document_source_file):
        if table.row_label(text) is not None:
            return table
    return None


def reviewed_table_for_section(
    document_source_file: str | None, section_ref: str | None, heading_path: str
) -> ReviewedTable | None:
    """In: a passage's document, section reference and heading trail. Out: its table, or None.

    This is the trigger, and it is deliberately wider than `reviewed_table_for`: **the
    introduction counts**. The fee table's introduction is what retrieval actually finds
    (the bands are vector-only and their order is noise), so "a row brings its table"
    would never fire on the question that motivated the slice.
    """
    wanted_ref = (section_ref or "").strip()
    wanted_heading = " ".join((heading_path or "").split())
    for table in _tables_of(document_source_file):
        if wanted_ref and table.section_ref and wanted_ref == table.section_ref:
            return table
        if wanted_heading and table.title and wanted_heading.split(">")[-1].strip().startswith(
            table.title
        ):
            return table
    return None


def row_chunks_for(
    table: ReviewedTable, *, standard_set: StandardSet, source_file: str
) -> list[DocumentChunk]:
    """In: a reviewed table. Out: the stored chunks that are its rows, in printed order.

    One query, and one that cannot escape the corpus boundary: the filter carries the
    session's `StandardSet` as well as the document, for the same reason every arm in
    `knowledge.services` does (`D16`). A row whose text does not match the artefact is
    dropped rather than labelled — a mislabelled row is worse than a missing one, which is
    the rule `align_artefact_grid` already follows for the reader.
    """
    if not table.rows:
        return []
    chunks = DocumentChunk.objects.filter(
        document__standard_set=standard_set,
        document__source_file=source_file,
        section_ref=table.section_ref,
    ).select_related("document")
    by_text = {" ".join(chunk.text.split()): chunk for chunk in chunks}
    return [
        by_text[" ".join(row.split())] for row in table.rows if " ".join(row.split()) in by_text
    ]


def _tables_of(document_source_file: str | None) -> tuple[ReviewedTable, ...]:
    """In: a document's source path. Out: its reviewed artefact tables, or ().

    Fails: never. A missing artefact, an unreadable file or a parse error all return an
    empty tuple: retrieval must not lose a passage because a review file is absent.
    """
    if not document_source_file:
        return ()

    # Imported here, not at module scope: `knowledge.ingest` imports `knowledge.tables`,
    # so a module-level import would close the cycle.
    from knowledge.ingest import corpus_artifact, doc_key_for

    path = corpus_artifact(doc_key_for(document_source_file))
    if path is None or not path.is_file():
        return ()
    try:
        stat = path.stat()
    except OSError:
        return ()
    return _parsed_tables(str(path), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=8)
def _parsed_tables(path: str, mtime_ns: int, size: int) -> tuple[ReviewedTable, ...]:
    """Every table in one artefact. Cached on the file's identity, never on its path alone.

    Keyed on `mtime_ns` and `size` as well as the path, because a cache keyed on the path
    would serve the table a *previous* ingest was built from — `testing_hazards.md` §3.24's
    shape, where "the corpus is current" and "the corpus was rebuilt" came apart.
    """
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return ()
    if _TABLE_MARKER not in text:
        return ()
    try:
        reviewed = load_document(path)
    except (OSError, ValueError):
        return ()

    tables: list[ReviewedTable] = []
    for section in reviewed.sections:
        grid: ArtefactGrid | None = artefact_grid_for(section)
        if grid is None or grid.layout != "grid":
            # A `layout: process` table is a sequence of steps with prose cells, and it is
            # drawn as cards for that reason (`D77`). Its rows are already readable
            # passages — "Step 3 … The group conducts farm visits" — so showing them as a
            # grid of cells would replace a passage with a puzzle. Only a grid table has
            # the defect this module exists for: cells that mean nothing without a heading.
            continue
        tables.append(
            ReviewedTable(
                title=" ".join((section.heading_path or "").split()),
                columns=tuple(" ".join(column.split()) for column in grid.columns),
                rows=tuple("\n".join(cells) for cells in grid.rows),
                labels=tuple(grid.labels),
                section_ref=section.section_ref,
            )
        )
    return tuple(tables)
