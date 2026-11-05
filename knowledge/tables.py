"""Appendix table rows — the one place a chunk is a reconstruction, not a slice.

One storage now, and one table still in Python. Reviewed rows live as a `<!-- table … -->` block
in the reviewed corpus artefact (D73, and every table curated from 2026-10-30 onward); both storages
end as one `DocumentChunk` per row, whose text is the row's cells in printed order.

**Appendix 6a left this module on 2026-11-05 (S5).** Its twenty rows were Python literals until the
generator could emit their block from the page: `APPENDIX_6A_ROWS`, `TABLE_ROWS["Appendix 6a"]` and
`TABLE_SECTIONS["Appendix 6a"]` are gone, and the artefact carries the pairing with column meaning.
Appendix 2 is the last of the reviewed tables still held here, and it is waiting on the same thing —
30 rows, three printed pages, and no arm read for two of them (`INGESTION_ENGINE_S5_PLAN.md` §4).

**Why this module exists.** `pdftotext -layout` renders Appendix 2 as two columns on
one line grid, and the condition column is vertically offset from the substance column.
`de_column` fixes the pages whose rows do not overflow the gutter; this table's do, so a
spanning line is kept whole (rule 2 of the transform) and the stored text reads:

    Trace elements, e.g.: boric acid, sodium borate, calcium Use restricted to cases where…

The sentence on the paper is correct; the chunk is not quotable, and the model's faithful
quote is refused by the citation audit. Worse, the proximity of a condition to the wrong
substance made a grounded answer say straw must be untreated — a condition the standard
attaches to **wood**.

`pdftotext -table` aligns the same page's rows correctly. Measured 2026-10-21 on
SAOSO pdf pages 77–79: `Biodegradable processing by-products …` pairs with `Free of
significant contaminants…`, and `Wood, bark, sawdust …` pairs with `Only if not
chemically treated`. Row alignment is therefore a property of the *extraction mode*, not
something this module invents.

**Assumptions, stated because they are product decisions, not facts the code can see:**

1. The pairing below is the printed table's, reviewed by the product owner on
   2026-10-21. Where the text is ambiguous — `Free of significant contaminants` sits
   beside three unconditioned rows as well — the reviewed pairing wins, and the code
   does not infer one.
2. A **row** is the unit of permission: one substance cell and its condition cell,
   left to right, top to bottom. A row with no condition is still an Appendix 2 entry;
   an empty condition is **not** permission (the prompt keeps "silence is not
   permission").
3. Each **cell** is verbatim: a whitespace-normalised substring of the `-table`
   extraction of its page. The row text joins two cells; the join itself is not on the
   paper. A quote may cover either cell or the whole row, and a reader checks it by
   finding the row, not a sentence. This is the deliberate exception to
   `chunking.py`'s "a chunk is always `section.text[start:end]`".
4. **Cross-page continuations are merged by hand and recorded**, not inferred. The
   seaweed row's `(iii) fermentation.` is printed at the top of the next page and belongs
   to it. The parenthesis is the page's: **printed 79** carries `iii) fermentation.` beside
   `Coffee grounds` in Appendix 3, which is where the review's spelling came from until
   2026-11-05 (see `test_the_seaweed_condition_crosses_the_page_break`).
5. **Centred sub-headings are not rows.** "South African specific" qualifies the row
   beneath it; it is page furniture for pairing purposes, so it is not repeated into a
   cell and cannot be quoted as one.
6. **Sub-item headings are not rows.** `I. PLANT AND ANIMAL ORIGIN`, `II. MINERAL
   ORIGIN`, `III. MICROBIOLOGICAL` and `IV. OTHERS` organise the table; they are not
   permissions.
7. **Two storages, one shape — and the second is the one to use.** Every table curated from
   2026-11-05 is a `<!-- table … -->` block in the reviewed artefact (`knowledge.corpus`, D73),
   parsed into `ParsedSection.tables` and chunked by `chunks_for_parsed_section`. Appendix 2 is the
   only table still held here as Python rows; Appendix 6a was the second until S5 emitted its block.
   Appendices 3, 4, 6b/7 are still uncurated and keep the current pipeline and its documented
   limitations. This module must not pretend otherwise — assumption 7 said "Appendix 2 only" until
   2026-10-30, and it had been false since 6a landed.
8. **A changed standard is a changed table.** If SAOSO v2.2 reprints Appendix 2, this
   data is re-reviewed; the golden test (`test_tables.py`) fails loudly rather than
   letting the corpus drift from the paper.

No migration and no schema change: the rows become ordinary `DocumentChunk`s with
`section_ref="Appendix 2"`, so the citation audit, retrieval and the answer cache all
behave as before.

**The chunk-building is not here.** Turning a row into a `DocumentChunk` -- the prose around a
grid, `row_chunk`, the embedding rendition -- lives in `table_chunks.py` (CONTEXT_CUTS_PRD step
8). This module is the reviewed *data*: what the rows say, and the structure the reader draws.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from knowledge.chunking import Chunk, chunk_section, estimate_tokens
from knowledge.corpus import section_anchor


#: Where the condition column starts in `pdftotext -table` output, per printed page.
#: Measured 2026-10-21 (the `CONDITIONS FOR USE` header sits at column 60 on printed
#: 76; the continuation page's cells start at 64). Used to *verify* the curated cells
#: against the page — ingestion does not split anything at runtime, because the rows
#: are already the reviewed data. A reprint that moves the column changes this number
#: and `test_tables.py` fails. Printed 85 is Appendix 6a's single value column, measured
#: 2026-10-28 in `-table` output (the numbers start at column 88).
TABLE_BANDS: dict[int, int] = {76: 60, 77: 64, 78: 64, 85: 88}


@dataclass(frozen=True)
class TableRow:
    """One printed table row: a substance cell and the condition printed beside it.

    `section_ref` is carried here rather than hardcoded in `as_chunk`, because this shape is not
    Appendix 2's alone: Appendix 6a paired a class of animal with a stocking rate until S5 emitted
    it as a block. A hardcoded "Appendix 2" would make every appended row claim to be a substance —
    the kind of quiet mislabelling a reader cannot see and a citation inherits.
    """

    page: int
    substance: str
    condition: str = ""
    section_ref: str = "Appendix 2"

    @property
    def text(self) -> str:
        """The chunk text: both cells, in reading order, separated by a line break."""
        return f"{self.substance}\n{self.condition}" if self.condition else self.substance

    @property
    def heading_path(self) -> str:
        label = " ".join(self.substance.split())
        return f"{self.section_ref} — {label[:80]}"

    def as_chunk(self) -> Chunk:
        # **No `embedding_text`, and that is measured, not an omission** (2026-11-02).
        # Appendix 2's cells are prose, so its `text` already describes itself; prefixing
        # `substance:`/`condition:` labels to it dilutes the vector and cost three suite
        # questions their answers — the horse-manure, cardboard and ducks questions all
        # refused after a re-embed with the labels on (`scripts/probe_chat.py`, 9 → 6
        # grounded). D73's rendition exists for a row whose cells are **numbers**, which is
        # the artefact case (`row_chunk`), not for one that is already a sentence.
        return Chunk(
            section_ref=self.section_ref,
            text=self.text,
            token_count=estimate_tokens(self.text),
            heading_path=self.heading_path,
            page=self.page,
        )


#: Verbatim cells from SAOSO v2.1 (2026), Appendix 2, printed pp. 76–78. Reviewed
#: 2026-10-21. Do not tidy the punctuation: `selenic acid, selenic acid` and the trailing
#: commas are the document's.
APPENDIX_2_ROWS: tuple[TableRow, ...] = (
    TableRow(
        page=76,
        substance="Farmyard manure, slurry and urine",
        condition=(
            "Shall not constitute the main source of nitrogen in the absence of "
            "complimentary and additional nitrogen generating practices on farm and "
            "shall not be from conventional intensive livestock production systems "
            "without prior permission from the control body\n\n"
            "Coming from extensive livestock farming.\n\n"
            "If sourced from intensive livestock farming or not sourced from organic "
            "production systems, then the need for use thereof shall be motivated to "
            "the certification body, and it shall be composted.\n\n"
            "Forbidden if from factory farming origin."
        ),
    ),
    TableRow(
        page=76,
        substance="Farmyard manure, slurry and urine",
        condition=(
            "Manure applications should not be the primary source of nitrogen. See "
            "Section B – Appendix 6 Minimum Surface Areas Indoors and Outdoors and "
            "other Characteristics of Housing in the Different Species and Types of "
            "Production for the density of livestock for the equivalent of 170 Kg "
            "nitrogen per hectare per year."
        ),
    ),
    TableRow(page=76, substance="Guano"),
    TableRow(
        page=76,
        substance="Source separated human excrement",
        condition="Specifically prohibited.",
    ),
    TableRow(page=76, substance="Vermicastings"),
    TableRow(page=76, substance="Blood meal, meat meal, bone, bone meal"),
    TableRow(
        page=76,
        substance=(
            "Hoof and horn meal, feather meal, fish and shell products, wool, hide, "
            "fur, hair, dairy products"
        ),
    ),
    TableRow(
        page=76,
        substance=(
            "Biodegradable processing by-products, plant or animal origin, e.g., "
            "by-products of food, feed, oilseed, brewery, distillery or textile "
            "processing"
        ),
        condition=(
            "Free of significant contaminants; or composted before bringing onto "
            "organic land and confirmed free of significant contaminants"
        ),
    ),
    TableRow(
        page=76,
        substance="Crop residues and plant materials, mulch, green manure, straw",
    ),
    TableRow(
        page=76,
        substance="Wood, bark, sawdust, wood shavings, wood ash, wood charcoal",
        condition="Only if not chemically treated",
    ),
    TableRow(
        page=76,
        substance="Seaweed and seaweed products",
        condition=(
            "As far as obtained by: i) physical processes including dehydration, "
            "freezing and grinding; ii) extraction with water or potassium hydroxide "
            "solutions, provided that the minimum amount of solvent necessary is used "
            "for extraction; (iii) fermentation."
        ),
    ),
    TableRow(
        page=77,
        substance="Peat (prohibited for soil conditioning)",
        condition=(
            "Excluding synthetic additives; permitted only in horticulture "
            "(floriculture, nursery plants, potting mixes)."
        ),
    ),
    TableRow(page=77, substance="Plant preparations and extracts"),
    TableRow(
        page=77,
        substance=(
            "Compost made from ingredients listed in this appendix, Spent mushroom "
            "waste, humus from worms and insects,"
        ),
    ),
    TableRow(
        page=77,
        substance=(
            "Urban composts and household wastes from separated sources which are "
            "monitored for contamination"
        ),
        condition=(
            "Maximum concentrations in milligrams per kilogram (mg/kg) of dry matter: "
            "a) cadmium: 0,7; b) copper: 70; c) nickel: 25; d) lead: 45; e) zinc: 200; "
            "f) mercury: 0,4; g) chromium (total): 70; h) chromium (VI): 0"
        ),
    ),
    TableRow(
        page=77,
        substance=(
            "Calcareous and magnesium amendments: Limestone, gypsum, marl, maerl, "
            "chalk, sugar beet lime"
        ),
    ),
    TableRow(page=77, substance="Calcium chloride"),
    TableRow(
        page=77,
        substance=(
            "Magnesium rock, kieserite and Epsom salt (magnesium sulphate)"
        ),
    ),
    TableRow(
        page=77,
        substance="Other non-synthetic calcareous and magnesium amendments",
    ),
    TableRow(
        page=77,
        substance="Clay (e.g., bentonite, perlite, vermiculite, zeolite)",
    ),
    TableRow(
        page=77,
        substance=(
            "Mineral potassium (e.g., sulphate of potash, muriate of potash, kainite, "
            "sylvanite, patentkali)"
        ),
        condition=(
            "Shall be obtained by physical procedures but not enriched by chemical "
            "processes"
        ),
    ),
    TableRow(
        page=77,
        substance=(
            "Phosphates in non-synthetic form (e.g., rock phosphate, colloidal "
            "phosphate, apatite)"
        ),
        condition="Cadmium content less than or equal to 90 mg/kg of P2O5",
    ),
    TableRow(page=77, substance="Pulverized rock, stone meal, crushed stone."),
    TableRow(page=77, substance="Sodium chloride"),
    TableRow(page=77, substance="Sulphur"),
    TableRow(
        page=77,
        substance=(
            "Trace elements, e.g.: boric acid, sodium borate, calcium borate, "
            "borethanolamin, cobalt-acetate, cobalt-sulphate, copper oxide, copper "
            "sulphate, copper hydroxide, copper silicate, copper carbonate, copper "
            "citrate, ferric oxide, ferric sulphate, ferrous sulphate, iron citrate, "
            "iron sulphate, or iron tartrate manganous oxide, manganese sulphate and "
            "manganese carbonate selenic acid, selenic acid, sodium molybdate, "
            "molybdic oxide zinc carbonate, zinc oxide, zinc silicate, and zinc sulphate"
        ),
        condition=(
            "Use restricted to cases where soil/plant nutrient deficiency is "
            "documented by soil or tissue testing or diagnosed by an independent "
            "expert. Micronutrients in either chloride or nitrate forms are prohibited. "
            "Micronutrients may not be used as a defoliant, herbicide, or desiccant."
        ),
    ),
    TableRow(
        page=77,
        substance=(
            "Biodegradable processing by-products of microbial origin, e.g., "
            "by-products of brewery or distillery processing"
        ),
    ),
    TableRow(
        page=78,
        substance="Microbiological preparations based on naturally occurring organisms",
    ),
    TableRow(page=78, substance="Biodynamic preparations"),
    TableRow(page=78, substance="Calcium lignosulfonate"),
)


#: Section reference -> curated rows. Data, not a branch: another document with a
#: reviewed table adds a key, and the ingestion code does not change.
TABLE_ROWS: dict[str, tuple[TableRow, ...]] = {
    "Appendix 2": APPENDIX_2_ROWS,
}

#: What the reader prints where the paper's condition cell is empty (D70.4). A fragment, not a
#: sentence: it sits in 19 rows, and nineteen sentences would be noise. Silence is not permission —
#: the legend says so once, above the table.
NO_CONDITION_LABEL = "no condition printed"


@dataclass(frozen=True)
class TableDivider:
    """A printed heading *inside* the table: a part, or a centred qualifier.

    `before_row` is an index into `TABLE_ROWS[section_ref]`, because the divider is attached to the
    row it precedes — that is where the paper prints it, and a citation that lands mid-table must
    see the divider that governs the row it landed on, never the one above it.
    """

    before_row: int
    text: str
    kind: str  # "part" | "qualifier"


@dataclass(frozen=True)
class TableSection:
    """What the page prints once, above the rows: the columns, the claim, the dividers.

    The words are reviewed data for the same reason the cells are: the caption quotes the paper, and
    the legend is the group's own sentence, so it is swept by the claim-discipline test rather than
    inferred from the rows.
    """

    columns: tuple[str, str]
    legend: str
    dividers: tuple[TableDivider, ...]


@dataclass(frozen=True)
class TableStructure:
    """A curated section's structure, aligned to its rows — or nothing at all."""

    section: TableSection
    dividers: tuple[tuple[TableDivider, ...], ...]
    labels: tuple[str, ...]


#: Section reference -> printed structure. Reviewed 2026-10-27 against the `-table` extraction of
#: printed pp. 76–78; `knowledge/tests/test_table_sections.py` proves every divider is still the
#: line immediately above the row it names.
TABLE_SECTIONS: dict[str, TableSection] = {
    "Appendix 2": TableSection(
        columns=(
            "Substances — description, compositional requirements",
            "Conditions for use",
        ),
        legend=(
            "The standard prints this appendix as a table: each entry is a substance and the "
            "condition printed beside it. Where it prints no condition, nothing is permitted by "
            "its silence."
        ),
        dividers=(
            TableDivider(0, "I. PLANT AND ANIMAL ORIGIN", "part"),
            TableDivider(1, "South African specific", "qualifier"),
            TableDivider(3, "South African specific", "qualifier"),
            TableDivider(14, "South African specific", "qualifier"),
            TableDivider(15, "II. MINERAL ORIGIN", "part"),
            TableDivider(26, "III. MICROBIOLOGICAL", "part"),
            TableDivider(28, "IV. OTHERS", "part"),
        ),
    ),
}


def _squash(text: str) -> str:
    return " ".join((text or "").split())


def rows_for(section_ref: str | None) -> tuple[TableRow, ...]:
    """In: a section reference. Out: its reviewed rows, or an empty tuple."""
    return TABLE_ROWS.get(section_ref or "", ())


def section_for(section_ref: str | None) -> TableSection | None:
    """In: a section reference. Out: its reviewed structure, or None. Never rebuilt per call."""
    return TABLE_SECTIONS.get(section_ref or "")


def structure_for(section_ref: str | None, texts: tuple[str, ...]) -> TableStructure | None:
    """In: a section reference and the texts about to be rendered. Out: the structure, or None.

    In:  `texts` — the stored chunk text of each passage, in printed order.
    Out: the section, its dividers aligned per row, and one label per row; **None** unless the
         section has reviewed rows, the count matches, and every text is its row's text
         (whitespace-normalised).
    Side effects: none.
    Fails: never. A corpus that disagrees with the reviewed data renders the plain page it renders
        today, because mislabelled rows would be worse than no structure.
    """
    section = section_for(section_ref)
    rows = rows_for(section_ref)
    if section is None or not rows or len(rows) != len(texts):
        return None
    if any(_squash(row.text) != _squash(text) for row, text in zip(rows, texts)):
        return None

    per_row: list[list[TableDivider]] = [[] for _ in rows]
    for divider in section.dividers:
        per_row[divider.before_row].append(divider)
    return TableStructure(
        section=section,
        dividers=tuple(tuple(entry) for entry in per_row),
        labels=tuple(NO_CONDITION_LABEL if not row.condition else "" for row in rows),
    )


@dataclass(frozen=True)
class ArtefactGrid:
    """A reviewed artefact table, in the shape the reader draws.

    The two-column `TableStructure` above is Appendix 2's shape: a substance cell and a condition
    cell, rendered as a heading over a paragraph. The landscape's tables have five columns, so the
    reader needs the printed column labels and every cell — not a label per row. The data is the
    artefact's own (`ParsedTable`), never a reconstruction: the rows are the chunks the reader has.

    D77's four fields travel unaltered. They are the reviewer's, and the renderer reads them
    rather than deriving a fork from a missing `Step` prefix or naming a fee box from the
    columns around it.
    """

    columns: tuple[str, ...]
    legend: str
    #: One entry per row; each is that row's cells in printed column order.
    rows: tuple[tuple[str, ...], ...]
    #: The printed label of each row (`Step 1`, or the route's own wording where the paper prints
    #: no number), in row order. The card's heading falls back to this when no title is reviewed.
    labels: tuple[str, ...] = ()
    #: Which shape the reader draws: `grid` (a spreadsheet) or `process` (cards).
    layout: str = "grid"
    #: The row index where the remaining rows become an alternative path, or None.
    branch: int | None = None
    #: One reviewer title per row, in row order, or empty.
    titles: tuple[str, ...] = ()
    #: One heading per fee box, in printed order, or empty.
    fee_labels: tuple[str, ...] = ()

    @property
    def row_texts(self) -> tuple[str, ...]:
        """Each row as the chunk text the ingest stores (`ParsedTableRow.text`)."""
        return tuple("\n".join(cells) for cells in self.rows)

    def title_for(self, index: int) -> str:
        """The reviewer title for a row, or `""` — the template then prints the row label."""
        return self.titles[index] if 0 <= index < len(self.titles) else ""


@dataclass(frozen=True)
class GridAlignment:
    """Where a reviewed grid lands in the passages the reader is about to render.

    Two facts, not one: `positions` is the row-to-passage mapping, and `split` is the **passage**
    at which the remaining rows become an alternative path. The renderer stacks those in one
    column, so it needs the passage, not the row index — `grid.branch` says which row it is.
    """

    positions: tuple[int, ...]
    #: The passage index the alternative path starts at, or None for a linear table.
    split: int | None = None


def artefact_grid_for(section) -> ArtefactGrid | None:
    """In: a `ParsedSection` from a reviewed artefact. Out: its table as a grid, or None.

    A section with more than one table returns the first: every landscape section has one, and a
    section with two would need the template to place them, which is a different design question.
    """
    if not section.tables:
        return None
    table = section.tables[0]
    return ArtefactGrid(
        columns=table.columns,
        legend=table.legend,
        layout=table.layout,
        branch=table.branch,
        titles=table.titles,
        fee_labels=table.fee_labels,
        labels=tuple(row.label_text for row in table.rows),
        rows=tuple(tuple(cell.text for cell in row.cells) for row in table.rows),
    )


def align_artefact_grid(grid: ArtefactGrid, texts: tuple[str, ...]) -> GridAlignment | None:
    """In: a grid and the passage texts about to be rendered. Out: where its rows land, or None.

    In:  `texts` — one entry per passage in the branch, in printed order. Prose before, between or
         after the rows is allowed and ignored.
    Out: the index of each row's passage, in row order, plus the passage the alternative path
         starts at when the table declares a `branch:`. **None** unless every row matches exactly
         (whitespace-normalised) and the matches keep their order.
    Fails: never. A corpus that disagrees with the artefact renders the plain page it renders today,
        for the same reason `structure_for` does: a mislabelled row is worse than no grid.
    """
    positions: list[int] = []
    cursor = 0
    for wanted in grid.row_texts:
        needle = _squash(wanted)
        found = next(
            (index for index in range(cursor, len(texts)) if _squash(texts[index]) == needle),
            None,
        )
        if found is None:
            return None
        positions.append(found)
        cursor = found + 1
    split = None if grid.branch is None else positions[grid.branch]
    return GridAlignment(positions=tuple(positions), split=split)


__all__ = [
    "APPENDIX_2_ROWS",
    "FIRST_PAGE",
    "NO_CONDITION_LABEL",
    "TABLE_BANDS",
    "TABLE_ROWS",
    "TABLE_SECTIONS",
    "ArtefactGrid",
    "GridAlignment",
    "TableDivider",
    "TableRow",
    "TableSection",
    "TableStructure",
    "align_artefact_grid",
    "artefact_grid_for",
    "chunks_for_parsed_section",
    "chunks_for_rows",
    "row_chunk",
    "rows_for",
    "section_for",
    "structure_for",
]
