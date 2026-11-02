"""Appendix table rows — the one place a chunk is a reconstruction, not a slice.

Two storages, one shape: reviewed rows live as Python literals (`TABLE_ROWS`, Appendix 2
and 6a) or as a `<!-- table … -->` block in the reviewed corpus artefact (D73, and every
table curated from 2026-10-30 onward). Both end as one `DocumentChunk` per row, whose text
is the row's cells in printed order.

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
7. **Two storages, one shape — and this module is where both become chunks.** Appendix 2
   and 6a are reviewed rows held in Python (`TABLE_ROWS`); every table curated from now on
   is a `<!-- table … -->` block in the reviewed artefact (`knowledge.corpus`, D73), parsed
   into `ParsedSection.tables` and chunked by `chunks_for_parsed_section` here. Appendices
   3, 4, 6b/7 are still uncurated and keep the current pipeline and its documented
   limitations. This module must not pretend otherwise — assumption 7 said "Appendix 2
   only" until 2026-10-30, and it had been false since 6a landed.
8. **A changed standard is a changed table.** If SAOSO v2.2 reprints Appendix 2, this
   data is re-reviewed; the golden test (`test_tables.py`) fails loudly rather than
   letting the corpus drift from the paper.

No migration and no schema change: the rows become ordinary `DocumentChunk`s with
`section_ref="Appendix 2"`, so the citation audit, retrieval and the answer cache all
behave as before.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from knowledge.chunking import Chunk, chunk_section, estimate_tokens
from knowledge.corpus import section_anchor

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


def chunks_for_parsed_section(section) -> list[Chunk]:
    """One chunk per reviewed row of an artefact table, plus the prose around it.

    In:  `section` — a `ParsedSection` carrying `tables` parsed from a
         `<!-- table … -->` block (`knowledge.corpus`). Its cells are already slices of
         `section.text`.
    Out: chunks in document order: the prose before/between/after the tables, chunked by the
         ordinary chunker, and one chunk per row whose text is that row's cells.
    Side effects: none.
    Fails: never. A section with no tables yields exactly what `chunk_section` would, so a
         caller may route every section through here — but `chunks_for_sections` does not,
         because the common case should not pay for a branch it never takes.

    **Why the chunker cannot do this itself** (§3a rule 2, measured): a pipe table is one
    paragraph, and adding blank lines between rows changes nothing, because the chunker packs
    paragraphs to the token target. The row boundary is structure, so the row chunk is
    produced here and substituted, exactly as `chunks_for_rows` substitutes Appendix 2's.
    """
    rows = []
    for table in section.tables:
        for row in table.rows:
            span = (row.cells[0].start, row.cells[-1].end) if row.cells else (0, 0)
            rows.append((span[0], span[1], row, table.columns))
    if not rows:
        return [chunk_section(section)]

    rows.sort(key=lambda entry: entry[0])
    chunks: list[Chunk] = []
    cursor = 0
    for start, end, row, columns in rows:
        if start > cursor:
            chunks.extend(_prose_chunks(section, cursor, start))
        chunks.append(row_chunk(section, row, columns))
        cursor = max(cursor, end)
    if cursor < len(section.text):
        chunks.extend(_prose_chunks(section, cursor, len(section.text)))
    return chunks


def _prose_chunks(section, start: int, end: int) -> list[Chunk]:
    """Chunk the section text in `[start, end)` as though it were its own section.

    Offsets are shifted back into the owning section so `source_start` keeps meaning "where
    this chunk sits in the section" — the offsets are the only evidence that nothing was lost.
    Leading whitespace is skipped rather than kept: a segment that starts at a row's end starts
    with the newline that ended that row, and a chunk whose first line is blank is noise in the
    reader and in the prompt.
    """
    # A segment that begins at a row's end begins with the newline that ended the row, so the
    # chunk would start with a blank line — shown by the reader and read by the model as an
    # empty first line. Measured 2026-11-01 on the OPP's §2.3, whose notes under the sliding
    # scale are the sentences that qualify every amount above them. The offsets move with the
    # text, so `source_start` still says exactly where the slice sits.
    while start < end and section.text[start].isspace():
        start += 1
    piece = section.text[start:end]
    if not piece.strip():
        return []
    refs = tuple(
        ref for ref in section.sub_refs if start <= ref.start < end
    )
    shifted = replace(
        section,
        text=piece,
        sub_refs=tuple(
            type(ref)(ref.ref, max(ref.start, start) - start, min(ref.end, end) - start)
            for ref in refs
        ),
    )
    heading = section.text.partition("\n")[0]
    chunks = [
        replace(chunk, source_start=chunk.source_start + start,
                source_end=chunk.source_end + start)
        for chunk in chunk_section(shifted)
    ]
    # A table section that opens straight into its rows has no prose before the first cell
    # except the heading, and the chunker then yields a chunk that is *only* the heading. It
    # would be retrievable and citable while saying nothing. Measured 2026-10-30 on the
    # landscape's `PGS SEALS AND THEIR USE` table, which prints no lead-in sentence.
    return [chunk for chunk in chunks if chunk.text.removeprefix(heading).strip()]


def row_chunk(section, row, columns: tuple[str, ...] = ()) -> Chunk:
    """One reviewed row's chunk: its cells, the page it starts on, and a locator.

    `text` is the row's cells joined by a newline — the documented exception to "a chunk is
    always `section.text[start:end]`" (assumption 3, and §5.1 of the landscape PRD: a blank
    line would make the reader build two paragraph blocks for one row). `heading_path` carries
    the label so a citation can say which step it came from, and the label is *not* text: on
    this document it is also printed in the first cell, and a corpus that repeated it would be
    quoting a word the paper prints once.

    **`embedding_text` is the row's labels, and it is why a numeric row is retrievable at all
    (D73).** `Below R 250,000 / 1,500 / 900` shares no word with any question, so a vector of
    the cells describes nothing; `columns` supplies the words — `Annual farm turnover (gross
    sales): Below R 250,000 · Initial certification fee (R): 1,500 · Renewal fee (R): 900`.
    Measured 2026-11-01: without it the sliding scale's six bands ranked nowhere, and `/ask/`
    answered *"the document does not specify the exact assessment fee"* for a fee the document
    prints (`CHAT_ANSWER_COVERAGE_PRD` G10). `text` is untouched: the quote audit and the
    reader see only what the paper prints.
    """
    label = row.label_text
    heading_path = (
        f"{section.heading_path} — {label[:80]}" if label else section.heading_path
    )
    text = row.text
    return Chunk(
        section_ref=section.section_ref,
        text=text,
        token_count=estimate_tokens(text),
        heading_path=heading_path,
        page=row.page if row.page is not None else section.page,
        anchor=section_anchor(f"{section.heading_path} {label}") if label else section.anchor,
        embedding_text=_embedding_rendition(heading_path, row, columns),
    )


def _embedding_rendition(heading_path: str, row, columns: tuple[str, ...]) -> str:
    """The text a row is embedded from: its heading, then `column: cell` for each printed cell.

    In:  `heading_path` — the section plus the row's label; `row` — a `ParsedTableRow`;
         `columns` — the table's printed column labels.
    Out: one line, `·`-separated. Empty cells are skipped: an empty cell is *silence*, and a
         label with nothing after it would embed a word the row does not say.
    """
    parts = [heading_path]
    for index, cell in enumerate(row.cells):
        value = " ".join((cell.text or "").split())
        if not value:
            continue
        column = columns[index] if index < len(columns) else ""
        parts.append(f"{column}: {value}" if column else value)
    return " · ".join(parts)


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
    "APPENDIX_6A_ROWS",
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
