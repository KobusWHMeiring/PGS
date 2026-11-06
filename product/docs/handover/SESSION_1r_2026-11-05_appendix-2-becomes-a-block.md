# Session 1r — 2026-11-05 — Appendix 2 becomes a block, and three declarations it needed

**For:** the next agent.
**From:** the corpus-and-retrieval line, session `1r`.
**Repo state at the start:** `main`, clean except another session's `copy_deck` work (unchanged and
untouched by this session — it is still in the working tree, uncommitted, and was never staged).

## What this session was

`HANDOVER.md`'s START HERE said S5-b: "Appendix 2's next step is decided; read its two pages first".
The plan (`INGESTION_ENGINE_S5_PLAN.md` §5) said S5-b is the expensive one: 30 rows across three
printed pages, no arm read for two of them, and the owner's 2026-10-21 review as the only honest
source. The exploration's recommendation was option A — band, hyphen, tail, then emit — and §4 of the
plan called it "a review rather than a chore".

That is what landed. Appendix 2 is now a `<!-- table … -->` block of 30 rows with its seven printed
dividers, `APPENDIX_2_ROWS` and `TABLE_ROWS` and the whole curated rendering path are deleted, and
the emitter can now express a two-column table printed on one line grid.

## The order it happened in, and what each step taught

**1. The declarations, refused first.** `ProposedProfile` grew `band`, `dividers`, `tails` and
`silence`, each validated in `knowledge/table_proposals.py` against the structure it describes (a
band on a table that is not two columns is refused; a divider naming no row is refused; a tail naming
no cell is refused). `scripts/table_blocks.py` grew `_column_view` (one line, two columns), a
per-column cursor, the hyphen continuation and `_tail_line` — and outgrew the 30 KB cap doing it, so
the cell primitives moved to a new `scripts/table_cells.py` (22.7 KB + 13.2 KB, and the band and the
slice still read the declared boundary through one function).

**2. The generator could not run.** The first real `build_corpus --doc saoso` died with
`NameError: name 'corpus_pages' is not defined` — `build()` calls `corpus_pages.pass_texts` and the
module was imported by name only. No test calls `build()`, only `emit()`, so 1831 tests were green
over a script that could not run (`testing_hazards.md` §3.40). Fixed by one import.

**3. The pre-check answered yes twenty pages early.** `_appears` asks "is a row's first cell in this
section?", and `Farmyard manure, slurry and urine` is printed in `S8.1` as well as Appendix 2. The
proposal was attempted in `S8.1`, refused there, and marked `attempted` — so the appendix section
never saw it and the artefact came out with 6a only. A table is now attempted only in a section whose
heading page it declares (§3.41). This is the defect that would have shipped as a *clean* artefact
with a missing table.

**4. One forward cursor cannot express a two-column grid.** Row 4 of printed 76 wraps both cells down
the same five lines, so the condition's first word sits above the substance's last one. With the band
declared, each column is a stream: the cursor follows the stream and `min(cursors)` is the row's
floor. This is the design change the band makes, and it is why `_resolve`'s old single cursor was the
real blocker — not the band itself.

**5. The hyphen was needed one line later than the exploration said.** The exploration's flat-text
probe called `cobalt-`/`sulphate` an exception; the emitter already resolved it, because the break
lands exactly at a line boundary and the remainder equals the next line. What it could not do was
consume a *continuation* line that ends in a hyphen mid-word, which is what the page prints three
lines into the trace-elements cell. Same rule, different position in the walk.

**6. A cell that crosses a page needs the parser too.** The block writes `<!-- page: -->` **inside**
the cell; `TableBlock.add_cell_line` records the printed page of every line; `TableCell.pages` carries
one per line; R3 checks each line against its own page and resets its cursor at the boundary. That is
the smallest honest form of requirement 4's "a row whose later half is on the next page" — and it is
why the tail is a declaration rather than an inference.

**7. R6's "the paper prints it once" was simply false.** Appendix 2 prints `South African specific`
three times, once above each row it qualifies (§3.42). The guard now counts claims against the
occurrences on the page. The two failures the first gate run reported were both this: the same text
claimed by rows 2 and 4, then by rows 2 and 15.

## The deletion, and what it cost

`APPENDIX_2_ROWS`, `TABLE_ROWS`, `TABLE_SECTIONS`, `rows_for`, `section_for`, `structure_for`,
`chunks_for_rows`, `NO_CONDITION_LABEL`, `TableRow`, `TableSection`, `row_blocks` and `RowHeading` are
gone. That pulled the reader's curated branch out with them: `Reader.table`, `ReaderPassage.dividers`,
`ReaderPassage.note`, the template's caption bar and the `passage__row`/`passage__divider` blocks.
The reader now draws Appendix 2 through `_artefact_grid`, which gained `dividers` (rendered as
`reader__grid-divider` rows) and the `silence` label for an empty cell.

Two regressions this caught, both worth naming:

* **The grid's cells were not annotated**, so `See Section B – Appendix 6 …` in a condition cell
  rendered as text. `_artefact_grid` runs before `build_reference_index`, so the annotation is applied
  after it, once, in `reader_for`. The curated tests caught this because one of them asserts a
  reference inside a row.
* **The `silence` label was attached to every row**, not to the silent ones — 30 labels instead of 19.
  `note=""` unless a cell is actually empty.

The chunk count moved 340 → **341**: the header prose above the grid is a chunk again, as it never was
while Python rows replaced the section's chunks.

## Numbers, measured on this box

| Command | Output |
|---|---|
| `check_tables --doc saoso --rows 30,20` | `ok — 2 tables, 50 rows, 0 violations` |
| `check_tables --doc opp --rows 6` | `ok — 1 tables, 6 rows, 0 violations` |
| `check_tables --doc landscape --rows 3,2,3` | `ok — 3 tables, 8 rows, 0 violations` |
| `build_corpus --doc saoso --force` | one section, `204 insertions(+), 104 deletions(-)` |
| `build_corpus --doc opp --force` | `opp.md` byte for byte unchanged |
| full suite (`--reuse-db`, 5433) | **1776 passed / 1 skipped / 8 xfailed** — 100.44 s, 135.24 s, 177.16 s, 223.31 s |
| `fast.sh --critical` | **182 passed / 4 deselected in 18.29 s** |
| `manage.py check` / `makemigrations --check` / `lint-imports` | clean / no changes / `knowledge must never import core KEPT` |

Four guards broken and watched red before being trusted: the band (`_column_view` ignoring it → 3
failed), the tail (declared → `None` → 3 failed), R3's per-line page (`declared = None` → 1 failed),
and R6's counting (proved by the gate failing before the fix, with the exact message in the log).

**`scripts/verify.sh` was not run end to end** and cannot be quoted from this tree: it still fails its
first step on another session's `scripts/copy_deck.py` (32 KB, over the file cap). Steps 2–4 were run
by hand and are in the table above.

## What the artifacts now say

* `knowledge/proposals/saoso.structure.json` has **two** tables. The second carries
  `continued_from: "knowledge/tables.py::APPENDIX_2_ROWS (the owner's review, 2026-10-21)"` and no
  `columns` — the file's banner is Document AI's read of page 86 and may not claim pages nobody sent
  it. `ProposedTable.where` names the review, so a refusal reads like a review, not an arm.
* `knowledge/proposals/saoso.reviewed.json`'s second entry is the review: two `columns`, the legend,
  `silence: no condition printed`, `band: {76: 60, 77: 64, 78: 64}`, seven `dividers`, one `tails`.
  `test_the_declared_band_is_the_measured_one` keeps it equal to `TABLE_BANDS`.
* `knowledge/tables.py` is 181 lines: `TABLE_BANDS`, `TableDivider`, the grid, its alignment. Its
  docstring says why nothing else is there.

## What is left in S5

* **S5-c, Appendix 7** — `gutter: 1` (the arm's first column is the printed row number) and a cell
  that wraps *inside* a column with `Air,` beside it on the same line. Docling's grid is the evidence
  for the boundary, and the band is Appendix 2's shape, not this one.
* **S5-d, the landscape** — four declarations (bullets, the merged fee box, seal artwork, the
  page-break row) and a splice that does not rewrite the reviewer's front matter.
* **S5-e/f** — the shape markers come off, `UNCOVERED` empties, the last of the bespoke path goes.

## Hazards this session added

`testing_hazards.md` §3.40 (a generator path no test calls), §3.41 (a pre-check that answers yes in the
wrong section and marks the work done), §3.42 (a uniqueness guard over a label the paper repeats).

## For the next agent, in one paragraph

Appendix 2 is emitted, gated, chunked and drawn from the artefact; the Python is gone. If you touch
the emitter, the tests that matter are in `tests/tools/test_table_blocks.py` (the band, the hyphen,
the divider, the tail) and `tests/tools/test_propose_tables.py::test_a_continued_locator_is_a_run_of_the_pages_table_line`
(the promotion's one guard). If you touch the reader, `core/tests/test_document_reader_curated.py`
now asserts the grid: 30 `<th scope="row">`, 7 divider rows, 19 silence labels, 3 page labels. And
regenerate the artefact with `build_corpus --doc saoso --force` whenever `saoso.md` and the proposal
disagree — `check_tables --rows 30,20` is the gate, and it needs the declaration.
