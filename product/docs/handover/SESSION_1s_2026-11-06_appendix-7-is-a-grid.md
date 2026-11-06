# Session 1s — 2026-11-06 — Appendix 7 is a grid, and the paper is five pages longer than the plan

**For:** the next agent.
**From:** the corpus-and-retrieval line, session `1s`.
**Repo state at the start:** `main` at `8d5ccb3`, clean except another session's `copy_deck` work
(unchanged and untouched — still uncommitted, never staged).

## What this session was

`HANDOVER.md`'s START HERE said S5-c: Appendix 7, `gutter: 1`, and a cell that wraps inside a column
with `Air,` printed beside it. The plan (§5) named one guard and one gate. Docling's cached grid
(`_scratch/or/docling-gutter.json`: `rows 8/5`, "pass once row 0 is taken as the header", i.e. 7 body
rows and 5 columns with the row-number gutter) was the evidence the plan pointed at.

That is what landed: Appendix 7's **printed-88 page** is a `<!-- table … -->` block of 7 rows and 4
columns, emitted from the same cached Layout Parser response S2 scored, with three declarations.

## What the first real build found, in the order it cost time

**1. The plan's row count is the arm's page, not the table.** The cached response reads seven body
rows because it was sent one page. The paper prints **25 rows and a `NOTE` across printed 88–92**:
printed 89 opens with the rest of 6b's condition and carries rows 7–9, printed 90 rows 9–15, printed
91 rows 15–20, printed 92 rows 20–25. This was invisible until the artefact was regenerated and read;
the plan's §1, the PRD's DoD and the handover all said "7 rows". So S5-c is a **slice** of the
appendix, not the appendix, and rows 7–25 are still the paper's `-layout` prose. The honest route for
them is Appendix 2's: a person reads the rows, `propose_tables.py --continue` promotes them as
locators, the emitter refuses anything it cannot find. No arm read those pages and no arm may be
re-run.

**2. The arm transcribed two cells, so "the arm's cells are locators" was false twice.** Its Layout
Parser writes the degree sign as `\(70^{\circ}C\)` where the page prints `70oC`, and closes up
`excipient:-` where the page prints it closed up. Neither could be resolved, so rows 2 and 6b
refused. The declaration that fixes this without widening a matcher is a **reviewed `locators:`**
entry: the page's spelling of the same cell, resolved by the emitter and sliced from the page. It is
the third declaration the plan did not foresee, and it is the same act as a continued row — a
person's reading becomes verification, never authorship.

**3. `band` was one boundary, and a five-column grid needs every column's left edge.** S5-b's
`band: {76: 60}` says where the second column starts. Appendix 7 prints four data columns plus the
gutter, and the wrap is *inside* a column while the next column's first line sits beside it. So
`band` now accepts one edge per printed column (`{88: [0, 4, 32, 60, 89]}`, first 0, strictly
rightwards); `_column_view` slices between edges, and the continuation branch reads "the rest of the
column" instead of "the rest of the line". The four edges are the page's own: the header line prints
its labels at 4, 32, 60 and 89 and every row on printed 88 agrees.

**4. The gutter is a cell, not a column.** `gutter: 1` resolves the arm's first column against the
page like every other cell (so the row's label cannot be a number somebody typed), claims it, and
writes it as the row's label — `<!-- row: 6a -->`. The block keeps the four columns the paper prints.
More than one gutter is refused (a row has one label), and a gutter without reviewed `columns` is
refused (the arm's gutter header is blank).

## Numbers, measured on this box

| Command | Output |
|---|---|
| `check_tables --doc saoso --rows 30,20,7` | `ok — 3 tables, 57 rows, 0 violations` |
| `check_tables --doc opp --rows 6` / `--doc landscape --rows 3,2,3` | `ok — 1 tables, 6 rows` / `ok — 3 tables, 8 rows` |
| `build_corpus --doc saoso --force` | one section, `134 insertions(+), 54 deletions(-)` |
| `build_corpus --doc opp --force` | `opp.md` byte for byte unchanged |
| chunks, measured with `chunks_for_sections` | **341 → 348** (Appendix 7's section 4 → 11) |
| full suite (`--reuse-db`, 5433) | **1790 passed / 1 skipped / 8 xfailed in 121.87 s, 131.06 s and 187.27 s** |
| `fast.sh --critical` | **182 passed / 4 deselected in 19.07 s and 32.74 s** |

Four guards broken and watched red: the band (ignored → 7 failed), the gutter (ignored → 4 failed),
the locator (ignored → 2 failed), and each `_band`/`_gutter` refusal (one test each).

`scripts/verify.sh` was **not** run end to end and still cannot be quoted from this tree: its first
step fails on another session's `scripts/copy_deck.py` (32 KB, untouched). Steps 2–4 by hand are in
the previous handover and were not re-run here; the full suite above is the gate's substance.

## What the artefacts now say

* `knowledge/proposals/saoso.structure.json` has **three** tables. The third is Document AI's read of
  pdf 89 (`layout16pro__column_major.json`), appended with `--append`; its header row keeps the
  arm's LaTeX and its blank gutter label, because the structure file is the arm's transcription.
* `knowledge/proposals/saoso.reviewed.json`'s third entry is the review: four `columns`,
  `gutter: 1`, `band: {"88": [0, 4, 32, 60, 89]}`, two `locators`, the legend.
* `knowledge/proposals/README.md` documents `gutter` and `locators` beside the fields S5-a/S5-b added.
* `knowledge/tests/test_table_sections.py` gained two parser-level assertions: four columns with the
  printed row numbers as labels, and `Air,` in its own cell beside `using gaseous oxygen`.
* The S5-c emitter tests live in `tests/tools/test_table_blocks_grid.py`, not in
  `test_table_blocks.py`: adding them pushed that file to 36 KB, and `context.py --check` (the gate's
  first step) refuses anything over 30 KB. `artefact_of`/`first_table` moved to
  `tests/tools/draft_fixtures.py` so both modules use the same building blocks.
* `knowledge/tests/test_table_harness.py` (71 rows over 7 tables) and `tests/tools/test_check_tables.py`
  (`30,20,7`) moved their ratchets; `test_corpus_saoso.py`'s "another pass" set now names Appendix 7.

## Hazards this session added

`testing_hazards.md` §3.43 (`chunks_for_parsed_section` returns a list holding a list, so summing it
undercounts every table-less section — it cost two hours reconciling 322 against 341) and §3.44
(`build_corpus --stdout` dies on this box's cp1252 console on `≥`, leaving an empty redirect after a
successful build).

## What is left

* **S5-c's remainder — a review.** Rows 7–25 of Appendix 7 (printed 89–92). The capability exists;
  the act is reading the page and promoting locators (`propose_tables.py --continue` needs a review
  source; there is none for these rows yet, so it is the owner's read, like 2026-10-21's).
* **S5-d — the landscape.** Four declarations (bullets, the merged fee box, the seal artwork, the
  page-break row) and a splice that does not rewrite the reviewer's front matter (pages 2–3 and 9,
  commit `8674d7a`).
* **S5-e/f — the ratchet.** The shape markers come off as each target passes (`column_major`'s page
  is now a block, but `read_table()` does not read the artefact yet), then the last of the bespoke
  path goes.

## For the next agent, in one paragraph

Appendix 7's first page is emitted, gated, chunked and parsed as a grid; the rest of the appendix is
still interleaved prose and that is the recorded state, not an oversight. If you touch the emitter,
the tests that matter are `tests/tools/test_table_blocks_grid.py` (the n-column band, the gutter,
the locator), `knowledge/tests/test_table_proposals.py` (the refusals each declaration replaced) and
`test_table_sections.py` (the parsed grid). Regenerate with `build_corpus --doc saoso --force` when
the artefact and the proposal disagree, then `check_tables --rows 30,20,7`. Do not measure a chunk
count with `chunks_for_parsed_section`.
