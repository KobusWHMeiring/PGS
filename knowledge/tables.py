"""Appendix table rows — the one place a chunk is a reconstruction, not a slice.

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
   seaweed row's `iii) fermentation.` is printed at the top of the next page and belongs
   to it.
5. **Centred sub-headings are not rows.** "South African specific" qualifies the row
   beneath it; it is page furniture for pairing purposes, so it is not repeated into a
   cell and cannot be quoted as one.
6. **Sub-item headings are not rows.** `I. PLANT AND ANIMAL ORIGIN`, `II. MINERAL
   ORIGIN`, `III. MICROBIOLOGICAL` and `IV. OTHERS` organise the table; they are not
   permissions.
7. **This covers Appendix 2 only.** Appendices 3, 4, 6a/6b and 7 keep the current
   pipeline and its documented limitations. This module must not pretend otherwise.
8. **A changed standard is a changed table.** If SAOSO v2.2 reprints Appendix 2, this
   data is re-reviewed; the golden test (`test_tables.py`) fails loudly rather than
   letting the corpus drift from the paper.

No migration and no schema change: the rows become ordinary `DocumentChunk`s with
`section_ref="Appendix 2"`, so the citation audit, retrieval and the answer cache all
behave as before.
"""

from __future__ import annotations

from dataclasses import dataclass

from knowledge.chunking import Chunk, estimate_tokens

#: Printed page numbers, as the reader sees them (`DocumentChunk.page`).
FIRST_PAGE = 76

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

    `section_ref` is carried here rather than hardcoded in `as_chunk`, because there is more
    than one reviewed table now: Appendix 2 pairs a substance with a condition, Appendix 6a
    pairs a class of animal with a stocking rate. A hardcoded "Appendix 2" would make every
    appended row claim to be a substance — the kind of quiet mislabelling a reader cannot see
    and a citation inherits.
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
            "for extraction; iii) fermentation."
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


#: Verbatim cells from SAOSO v2.1 (2026), Appendix 6a, printed p. 85 — one row per class of
#: animal. Reviewed 2026-10-28 against the `-table` extraction of that page and against the
#: EU regulation the appendix cites (`Source: EU 2092/91`), which agree row for row.
#:
#: **Why this needed a review and not a parser.** `-layout` puts the value column on the
#: same line grid as the class column, so five values landed on a neighbour's line and the
#: other fifteen piled up at the end of the page: no pairing survived, and "how many laying
#: hens per hectare?" was unanswerable from the branch that answers it
#: (`BugFixes/saoso_text_glyphs_and_boundaries.md` §5). The pairing is the table's meaning,
#: so it is data a person read, never inferred.
APPENDIX_6A_ROWS: tuple[TableRow, ...] = (
    TableRow(
        page=85,
        substance="Equines over six months old",
        condition="2",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Calves for fattening",
        condition="5",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Other bovine animals less than one year old",
        condition="5",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Male bovine animals from one to less than two years old",
        condition="3,3",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Female bovine animals from one to less than two years old",
        condition="3,3",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Male bovine animals two years old or over",
        condition="2",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Breeding heifers",
        condition="2,5",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Heifers for fattening",
        condition="2,5",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Dairy cows",
        condition="2",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Cull dairy cows",
        condition="2",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Other cows",
        condition="2,5",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Female breeding rabbits",
        condition="100",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Ewes",
        condition="13,3",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Goats",
        condition="13,3",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Piglets",
        condition="74",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Breeding sows",
        condition="6,5",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Pigs for fattening",
        condition="14",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Other pigs",
        condition="14",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Table chickens",
        condition="580",
        section_ref="Appendix 6a",
    ),
    TableRow(
        page=85,
        substance="Laying hens",
        condition="230",
        section_ref="Appendix 6a",
    ),
)

#: Section reference -> curated rows. Data, not a branch: another document with a
#: reviewed table adds a key, and the ingestion code does not change.
TABLE_ROWS: dict[str, tuple[TableRow, ...]] = {
    "Appendix 2": APPENDIX_2_ROWS,
    "Appendix 6a": APPENDIX_6A_ROWS,
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
    "Appendix 6a": TableSection(
        columns=(
            "Class or species",
            "Maximum number of animals per ha equivalent to 170 kg N/ha/year",
        ),
        legend=(
            "The standard prints this appendix as a table: each row is a class of animal and "
            "the maximum number of animals per hectare whose manure it may contribute, at the "
            "limit of 170 kg of nitrogen per hectare per year."
        ),
        dividers=(),
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


def chunks_for_rows(section_ref: str) -> list[Chunk]:
    """One chunk per reviewed row, in printed order."""
    return [row.as_chunk() for row in rows_for(section_ref)]


__all__ = [
    "APPENDIX_2_ROWS",
    "APPENDIX_6A_ROWS",
    "FIRST_PAGE",
    "NO_CONDITION_LABEL",
    "TABLE_BANDS",
    "TABLE_ROWS",
    "TABLE_SECTIONS",
    "TableDivider",
    "TableRow",
    "TableSection",
    "TableStructure",
    "chunks_for_rows",
    "rows_for",
    "section_for",
    "structure_for",
]
