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
#: and `test_tables.py` fails.
TABLE_BANDS: dict[int, int] = {76: 60, 77: 64, 78: 64}


@dataclass(frozen=True)
class TableRow:
    """One printed table row: a substance cell and the condition printed beside it."""

    page: int
    substance: str
    condition: str = ""

    @property
    def text(self) -> str:
        """The chunk text: both cells, in reading order, separated by a line break."""
        return f"{self.substance}\n{self.condition}" if self.condition else self.substance

    @property
    def heading_path(self) -> str:
        label = " ".join(self.substance.split())
        return f"Appendix 2 — {label[:80]}"

    def as_chunk(self) -> Chunk:
        return Chunk(
            section_ref="Appendix 2",
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

#: Section reference -> curated rows. Data, not a branch: another document with a
#: reviewed table adds a key, and the ingestion code does not change.
TABLE_ROWS: dict[str, tuple[TableRow, ...]] = {"Appendix 2": APPENDIX_2_ROWS}


def rows_for(section_ref: str | None) -> tuple[TableRow, ...]:
    """In: a section reference. Out: its reviewed rows, or an empty tuple."""
    return TABLE_ROWS.get(section_ref or "", ())


def chunks_for_rows(section_ref: str) -> list[Chunk]:
    """One chunk per reviewed row, in printed order."""
    return [row.as_chunk() for row in rows_for(section_ref)]


__all__ = [
    "APPENDIX_2_ROWS",
    "FIRST_PAGE",
    "TABLE_ROWS",
    "TableRow",
    "chunks_for_rows",
    "rows_for",
]
