# Proposals — the structure a document's tables were read from

One pair of files per document, both keyed by the PDF's **sha256** (which the file records, and the
artefact header records the same digest). A renamed document is a different document, and a reprint
finds no proposal — which is the truthful outcome: nobody has read its tables yet.

| File | Who writes it | What it holds |
|---|---|---|
| `<doc>.structure.json` | `scripts/propose_tables.py`, from a cached extractor response | the arm's grid: columns, rows, the pages, and the banner (`structure`, `processor`, `project`, `captured`, `reduced_from`) |
| `<doc>.reviewed.json` | a person, once per table | the block fields **no extractor produces**: `legend`, `layout`, `titles`, `fee_labels`, `branch`, `silence`, `band`, `gutter`, `locators`, `dividers`, `tails`, and **`columns`** — the labels the reader prints, when the paper's header is multi-line and two-level so a one-line `cols:` cannot be a slice of it (Appendix 6a, S5) |

**What must never be edited by hand** is `.structure.json`. It is a transcription of what the arm
returned, and hand-editing it would make the one thing in this path that is *not* a guess into one.
If the arm's read is wrong, the cell is wrong in the diff — the emitter verifies every cell against
the page's own text layer and refuses the ones the arm got wrong, naming them. The one exception is
`--continue` below, which writes an entry from a review rather than from an arm and says so in it.

## The fields that name structure

Each of these is reviewed data, is refused if it disagrees with the page, and **loosens no cell
rule**: the cells stay slices of the page, verified one by one.

| Field | What it says | Why it is not a widened matcher |
|---|---|---|
| `columns` | the labels the reader prints, flat | the paper's header is multi-line and two-level; a one-line `cols:` cannot be a page slice. The cells beneath it are still verified |
| `band: {"76": 60}` / `{"88": [0, 4, 32, 60, 89]}` | where the columns start on each **printed** page: one boundary for a two-column table, every column's left edge once there are more | a cell may then only claim its own column, and each column's cells are resolved in their own forward cursor — the alternative is a left cell that reads `Biodegradable Free of contaminants` with its neighbour's words in the middle (`Air,` printed beside `using gaseous oxygen`) |
| `gutter: 1` | the arm's first column is the **printed row number**, not a column the reader draws | it is resolved and claimed like every other cell, and written as the row's label — the block cites the page's number instead of putting a column of digits beside every row |
| `locators: [{row, column, text}]` | the reviewed spelling of a cell the arm **transcribed** rather than read (`\(70^{\circ}C\)` for the page's `70oC`) | it is a locator like any other: the emitter resolves it against the page and writes the page's characters, so the review cannot author a value — and a locator the page does not print is refused |
| `dividers: [{before, text, kind}]` | a heading printed *between* rows (`I. PLANT AND ANIMAL ORIGIN`, `South African specific`) | each is located on a line of its own and written as `<!-- row-divider: … -->`, so the block carries the label and R6 can claim it |
| `tails: [{row, column, page, text}]` | a cell whose last words are printed at the top of the next page | the words must be the **first** line printed on the declared page; an inferred continuation is how `(iii) fermentation.` was once transcribed from two pages later |
| `silence` | what the reader prints where a cell is empty (`no condition printed`) | one reviewed sentence per table, not nineteen in a template |

## Assembling one document from several responses

One arm response covers the pages it was sent, and an appendix is not one page. `--append` merges a
second response into an existing proposal, refusing a differing `sha256`, `structure`, `processor` or
`project` (one file, one banner) and refusing two tables for the same page:

```bash
python scripts/propose_tables.py --append --response _scratch/adc/responses/layout16pro__qualifier.json     --structure documentai-layout-v1.6-pro --processor … --project … --shape qualifier --doc saoso     --json knowledge/proposals/saoso.structure.json
```

**What must never be put here** is a typed-out table. The cell characters come from the page
(`scripts/table_blocks.py` slices them out of the artefact's body stream); a cell typed here would be
a quote nobody verified, and the harness would pass it.

`reviewed` entries are matched to tables by **index, in document order**, and a review that names an
index the structure does not have is an error rather than an ignored line.

**`columns` reviews a header, never a cell.** The paper prints a table's header once, as two levels of
type across several lines with merged cells; every arm flattens it. A one-line `cols:` field cannot be
a run of that, so those labels are reviewed data — the same status the reader's own column labels
already had. What must not follow is a shorthand for a *cell*: the emitter still locates every cell on
the page and refuses the ones that are not there, so a review cannot author a value.

## Continuing a table no arm ever read

Some pages were never sent to an extractor. If a person has reviewed their rows from the paper,
`--continue` promotes those rows into the proposal **as locators** — the emitter still verifies every
cell against the page and refuses the ones that are not there, so a promotion cannot author a value:

```bash
python scripts/propose_tables.py --continue --doc saoso --pdf-offset 1 \
    --json knowledge/proposals/saoso.structure.json
```

The entry it writes carries `continued_from` naming the review, because the file's banner describes
the arm that read the *other* pages and a banner claiming both would be false. It omits `columns`
for the same reason: those labels are reviewed wording, and `reviewed.json` supplies them.

## Regenerating

```bash
python scripts/propose_tables.py \
    --response _scratch/adc/responses/layout16pro__numeric_row.json \
    --structure documentai-layout-v1.6-pro \
    --processor 68e47c3bc90cc6ab@pretrained-layout-parser-v1.6-pro-2025-12-01 \
    --project 803140233794 --shape numeric_row --doc opp \
    --json knowledge/proposals/opp.structure.json
```

The raw response is cached under `_scratch/` and is **not committed** (it is 8–28 KB per page and
the credential that produced it belongs to the owner, not the repository) — the same rule
`product/docs/evidence/README.md` records for the S2 arms. For a document the shape registry does not
know, pass `--pdf` and `--pages` instead of `--shape`.
