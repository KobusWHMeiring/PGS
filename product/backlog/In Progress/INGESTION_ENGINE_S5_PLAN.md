# Plan — S5 of the ingestion engine: the last four tables stop being Python

**Status:** In Progress — **S5-a landed 2026-11-05** (§6, PRD §3.16); **S5-b landed 2026-11-05**
(§7, PRD §3.17); S5-c…S5-f open
**Parent:** `INGESTION_ENGINE_PRD.md` §5's S5 row, §3.14 (the composite), §3.15 (what S3 landed)
**Written:** 2026-11-05, session `1q`, at `1aa152c` (clean apart from another session's `copy_deck` work)
**Scope:** the last slice of the PRD. When every §6 criterion holds, the PRD moves to `Done/`.

## 1. What S5 has to do

Four tables stop being Python data and become emitted `<!-- table … -->` blocks:

| Table | Where the page prints it | Rows × cols | Shape (S0 key) | What is missing today |
|---|---|---|---|---|
| Appendix 2 | SAOSO printed 76–78 | 30 × 2 | `qualifier` (pdf 77) | dividers (`I. PLANT…`, `South African specific`), `-table` pass, 30 rows of locators |
| Appendix 6a | SAOSO printed 85 | 20 × 2 | `headerless_values` | the two-label header; row association |
| Appendix 7 | SAOSO printed 88 | 7 × 4 (5 with the row-number gutter) | `column_major` | de-interleaving: a cell wraps *inside* a column |
| Landscape 4/5, 6, 7/8 | landscape printed 4–8 | 3, 2, 3 rows × 5 | `page_break_row`, `empty_cells`, `artwork_cell` | bullets, the merged fee box, seal artwork, the page-break row |

The DoD from the PRD, verbatim: 6a's 20 chunks carry column meaning, 7's chunks are rows, 2's
dividers survive as block data; all eight shape targets pass with the strict-xfail markers gone; the
bespoke handling is **deleted**; `verify.sh` is green with `PDFTOTEXT_BIN` poisoned.

## 2. What I measured before writing this plan (2026-11-05, this tree)

Every number below is a command's output, not an expectation.

1. **`saoso.md` reproduces byte for byte today** (`build()` in memory, 171 479 chars, diff 0). So a
   block added to it is a reviewable diff and nothing else moves. This is S5's safety net.
2. **`opp.md` reproduces byte for byte** (S3's regression), and `check_tables --doc opp --rows 6` →
   `ok — 1 tables, 6 rows, 0 violations`.
3. **`check_tables --doc landscape --rows 3,2,3` → `ok — 3 tables, 8 rows, 0 violations`** against the
   committed blocks. The landscape's *generator* is what is broken, not its artefact.
4. **`build --doc landscape` cannot reproduce `landscape.md`, and that is pre-existing.** Pages 2–3
   and 9 print no heading `HeadingParser` opens; their sections are the **reviewer's** (commit
   `8674d7a`: "the front matter the PDF parser could never open"). A full `--force` would delete the
   INRTODUCTION, SIX BASIC ELEMENTS, the three route sections and the colophon. **S5 may therefore
   not regenerate `landscape.md` wholesale** — the DoD's "regenerated so the diff is the review" has
   to be read as "the *blocks* are generated; the reviewed front matter is not rewritten".
5. **The landscape's table body cannot come from the stream `build()` assembles.** `choose_pages`
   takes pages 1–10 from `-raw` (content-stream order), so the page-4 header is not a run of any
   printed line and the emitter refuses at `proposal 1, column 1` — which is exactly the refusal S3
   recorded. Meanwhile the block declares `extraction: table`. **The body must be sliced from the
   pass the block declares**; that is the missing capability, and it is why S3 could not emit it.
6. **The arm's `columns` are not labels.** 6a's are `Maximum number of animals per ha Class or
   species` / `Maximum number of animals per ha equivalent to 170 kg N/ha/year` (one merged header
   row, the failure the owner arbitrated on 2026-11-05); Appendix 7's carry LaTeX escapes
   (`Conditions of use \(^{(1)}\)`) and a leading row-number gutter column. A printed header is
   multi-line and two-level, so a one-line `cols:` field **cannot** be a slice of it. The labels are
   therefore reviewed data — the same status `TABLE_SECTIONS["Appendix 2"].columns` already has.
7. **6a letter-spaces words** (`Other b o v i n e a n i m a l s less t h a n o n e year old`). The
   reviewed row rejoins them (`test_the_one_declared_spelling_difference_is_the_letter_spaced_row`
   says the rejoining "must be declared rather than applied silently"). So the emitter needs a
   declared `spacing: rejoin`, applied only to runs of ≥3 single letters.
8. **Appendix 2 is 30 rows, not 11.** The cached `qualifier` response is the shape page (pdf 77 =
   printed 76, 11 rows); rows 12–30 are printed on 77–78 and no cached arm read exists for them,
   because S5 may not re-run the arm. The PRD's brief says `--rows 11,20,7`; the paper's Appendix 2
   block is **30** rows and the shape fixture is the page-76 slice. Emitting 11 would leave 19 rows
   interleaved and `APPENDIX_2_ROWS` in place — i.e. it would not delete the bespoke handling.
9. **Appendix 7's cells wrap inside a column.** `Aeration or oxygenation` / `using gaseous oxygen` on
   the page, and `Air,` beside it on the *same* line belongs to the next column. `_resolve`'s
   continuation branch takes "the rest of the line" as the cell's head, so it cannot express a cell
   bounded by the next column. This is the one place S5 genuinely needs a new resolution rule, and
   Docling's grid (`rows 7/7, cols 5/4` once the gutter is declared, §3.14) is the evidence for the
   column boundaries.

## 3. Design — declarations, never widened matchers

Three new reviewed fields, all in `knowledge/proposals/<doc>.reviewed.json`, all refused if they
disagree with the structure they describe. **None of them loosens R3/R9**: the cells stay slices of
the page; the declarations name *structure*, which no extractor produces.

| Field | On | What it says | Why it is not a widened matcher |
|---|---|---|---|
| `columns: [...]` | table | the labels the reader prints (reviewed wording, flat) | the paper's header is multi-line and two-level; a one-line `cols:` field cannot be a page slice. The **cells** are still verified, one by one |
| `spacing: rejoin` | table | the page letter-spaces words for justification; rejoin runs of ≥3 single letters | applied only where the page's own characters prove the same letters in the same order, at word boundaries — the same narrowness as `_despaced_run` |
| `gutter: 1` | table | the arm's first column is the printed row number, not a column | it becomes the row's **label** (`heading_path`), which is where a citation wants it |

Two new **generator** capabilities, both declarative:

1. **The body is the pass the block declares.** `build_corpus.build()` already slices a section's
   body from the geometry stream. When a pending proposal declares `extraction: table` for pages the
   section covers, those pages are sliced from that pass instead
   (`knowledge/tests/page_fixtures.pages(doc, "table")` is byte-identical to
   `extract_pages(pdf, mode="table")`, so the emitter's characters and the harness's judging page are
   the same rendering). Without this the emitter is resolving `-layout` text and the harness is
   judging `-table` text, and one of the two is always wrong.
2. **`propose_tables.py --append`.** A document's structure is one file, and one arm response covers
   one page. `--append` merges a second response into the same proposal, refusing a differing
   `sha256`/`structure`/`processor` so the banner can never describe two arms at once.

Refusal first, declaration second: each field is added only after a test that names the refusal it
replaces (see §5).

## 4. How Appendix 2, and the landscape, get their structure

Neither can be finished inside this session's safe budget, and both reasons are measured:

* **Appendix 2** has no arm read for printed 77–78. The only honest sources are (a) a fresh arm run —
  forbidden (`do not re-open the DocumentAI key`, `do not re-run the arm evaluation`), or (b) the
  **already-reviewed** `APPENDIX_2_ROWS` (owner, 2026-10-21) used as *locators* for rows 12–30, which
  the emitter then verifies cell by cell against the page. (b) is defensible — a locator is not a
  cell, and every character is still the page's — but it must be a **recorded, separately reviewable
  act**, not a quiet default: `--continue` with the reviewed file named in the banner, and a test
  that every continued locator is a whitespace-normalised substring of the page's own `-table` line.
  That is a slice of its own.

  **The owner read the rendered pages on 2026-11-05 and found one character of (b) already wrong.**
  The seaweed row's tail is printed `(iii) fermentation.` (first line of printed 77); the reviewed
  cell had lost the bracket, and it is printed that way — `iii)` — beside `Coffee grounds` on
  **printed 79**, Appendix 3. No test could see it: `"iii) fermentation." in "(iii) fermentation."`
  is true because the shorter string is a substring of the longer one (PRD §3.16,
  `testing_hazards.md` §3.39). Corrected, and the guard is character-level now. The lesson for the
  continuation act: **the reviewed rows are a good source and not an oracle** — every one of them
  enters as a locator the emitter must find on the page, or it is a cell somebody typed.
* **Appendix 7** needs the column-bounded continuation rule of §2.9. The declaration is Docling's
  grid, recorded in the proposal banner; the rule must be refused first (a test that proves the
  current emitter refuses, then a test that proves the new one cuts at the column boundary).
* **The landscape** needs §2.5 (the body pass) **and** an emission path that does not rewrite the
  reviewed front matter: emit the blocks from the page prose and splice them into the committed
  artefact in place of the current table region, with the diff being the review.

## 5. Slices, in order, each with its gate

| # | Slice | Named test that must be red first | Gate |
|---|---|---|---|
| **S5-a** | The reviewed `columns` + `spacing` declarations, the body-pass rule, and **Appendix 6a emitted**; `APPENDIX_6A_ROWS` deleted | `test_a_reviewed_column_label_is_used_instead_of_the_arms` (red: the arm's merged label), `test_the_body_is_sliced_from_the_pass_the_block_declares` (red: `-raw` order), `test_appendix_6a_is_emitted_from_its_page` (red: no block) | `check_tables --doc saoso --rows 20` → ok; `build --doc saoso --force` diff is only the block; ingest/chunking/retrieval green |
| **S5-b** | Appendix 2: `qualifier` dividers as `row-divider:`, the 30-row continuation act, `APPENDIX_2_ROWS`/`TABLE_ROWS`/`rows_for` deleted | `test_appendix_2_divider_is_a_block_annotation`, `test_a_continued_locator_is_a_run_of_the_pages_table_line` | **Landed 2026-11-05 (§7, PRD §3.17).** `check_tables --doc saoso --rows 30,20` → ok (2 tables, 50 rows); the reader's dividers render from the block; `test_the_dividers_are_written_where_the_paper_prints_them` and `test_a_continued_locator_is_a_run_of_the_pages_table_line` are the guards, and the divider test's name changed with the format it writes |
| **S5-c** | Appendix 7: `gutter:` + the column-bounded continuation, Docling's grid in the banner | `test_a_cell_that_wraps_inside_a_column_is_bounded_by_the_next_column` (red: "out of printed order") | `check_tables --doc saoso --rows 30,20,7` → ok incl. `--pages-mode` absent |
| **S5-d** | The landscape: bullets, the merged fee box, the seal artwork, the page-break row; blocks spliced, front matter untouched | one test per declaration, each proved red first | `check_tables --doc landscape --rows 3,2,3` → ok from *emitted* blocks; `landscape.md` diff is only the blocks |
| **S5-e** | `read_table()` reads the artefact block for a shape's pages; markers come off as each shape passes; `UNCOVERED` empties | `test_the_shape_is_read_from_its_page[<key>]` stops `xfail` | 8 targets pass, audit reports zero uncovered shapes |
| **S5-f** | Delete the last of the bespoke path, close the loop: PRD §3.16/§5/§6, handover, `backlog.py --apply` → `Done/` | — | `verify.sh` green with `PDFTOTEXT_BIN` poisoned |

S5-e is a ratchet, not a switch: a marker comes off only for a shape whose target is green, and the
audit's `UNCOVERED` shrinks by exactly that key. `XPASS(strict)` is the detector that keeps us honest
in the other direction.

## 7. S5-b, as landed (2026-11-05)

**What the plan called "the expensive one" was three declarations and one bucket.** The order §5
named — band, hyphen, tail, block — held, and each one was refused before it was declared. The
surprises, in the order they cost time:

1. **`build_corpus.build()` could not run at all.** `corpus_pages.pass_texts` was called on a module
   that was never imported, and no test calls `build()` — only `emit()` (`testing_hazards.md` §3.40).
   The handover's S5-a measurement of that command predates the refactor that broke it.
2. **The pre-check answered yes in the wrong section.** `_appears` asks whether a row's first cell is
   in the section, and `Farmyard manure, slurry and urine` is printed in `S8.1` too, so the proposal
   was refused there and marked attempted twenty pages before its own table (§3.41). A table is now
   attempted only in a section whose heading page it declares.
3. **A single forward cursor cannot express a two-column grid.** Both cells of a row share every
   printed line, so the condition's first line is *above* the substance's last one. With the band,
   each column is a stream, the cursor follows the stream, and a row's floor stops a column resuming
   above the row.
4. **The hyphen was needed, but not where the exploration said.** The *flat* 41-cell probe called
   `cobalt-`/`sulphate` an exception; the emitter resolved it as two lines already. What it could not
   do was consume a *continuation* line that ends in a hyphen mid-word, which is what the real page
   prints three lines into the cell (§4 step 2's rule, applied one line later than expected).
5. **R6's "the paper prints it once" was false.** Appendix 2 prints `South African specific` three
   times, once above each row it qualifies (§3.42). The guard counts claims against occurrences now.
6. **A cell that crosses a page needed the parser, not just the emitter.** The block writes a page
   marker inside the cell; the parser stores one page per cell line; R3 checks each line against its
   own page. That is the smallest honest version of requirement 4's "a row whose later half is on the
   next page".

**Deviations from §5, and why.**

* The plan's §5 named `test_appendix_2_divider_is_a_block_annotation`. It is
  `test_the_dividers_are_written_where_the_paper_prints_them` and its refusal twin
  `test_a_divider_the_page_does_not_print_is_refused` — the block format already had
  `row-divider:`, so the test's subject is the emitter writing and claiming them, not a new field.
* The plan's §4 said the continuation's test should check "every continued locator is a
  whitespace-normalised substring of the page's `-table` line". It does, band-sliced per column and
  with the page's own hyphenation joined (`cobalt-` + `sulphate`), and it names the declared tail as
  the one cell checked on the page it is printed on.
* The plan did not foresee the 31st chunk: the header prose above the grid is a chunk again, as it
  never was while Python rows replaced the section's chunks. Corpus total 340 → 341.
* `knowledge/tables.py` is **181 lines**, not deleted: `TABLE_BANDS` is the measurement the reviewed
  `band:` must equal, and the grid/alignment the reader draws are that module's remaining job.

**Measured.** `check_tables --doc saoso --rows 30,20` → ok (2 tables, 50 rows, 0 violations);
`--doc opp --rows 6` and `--doc landscape --rows 3,2,3` unchanged; `build_corpus --doc opp --force`
leaves `opp.md` byte for byte unchanged; `--doc saoso --force` is one section's diff
(`204 insertions(+), 104 deletions(-)`); full suite 1776 passed / 1 skipped / 8 xfailed (100–223 s on four warm runs); four guards
broken and watched red (band, tail, R3's per-line page, R6's counting).

## 6. What this session lands (landed 2026-11-05)

**S5-a only**, plus this plan, the measurements in §2 as `testing_hazards.md` entries, and an honest
§3.16 in the PRD. The reason is §2.4/§2.8/§2.9: three of the four tables need a capability that has
to be refused and declared rather than waved through, and each one is a review with the paper in
front of it. Landing half of that in one commit is how a table block becomes a hand-tidied copy of a
page — the exact defect this PRD exists to prevent.

The PRD stays in `In Progress/`. §6's criteria are each marked with what is true now.

**S5-a, as landed, measured.** `check_tables --doc saoso --rows 20` → `ok — 1 tables, 20 rows, 0
violations`; `build_corpus --doc saoso --force` → `101 insertions(+), 25 deletions(-)` in one section,
and the diff *corrects* a pairing (`Equines over six months old 5` → `2`); `--doc opp --force` leaves
`opp.md` byte for byte unchanged; `APPENDIX_6A_ROWS`, `TABLE_ROWS["Appendix 6a"]` and
`TABLE_SECTIONS["Appendix 6a"]` deleted; full suite 1831 passed / 8 xfailed. **What the slice taught
the plan:** measuring first moved S5-d (the landscape) earlier in importance — the pass rule makes its
refusal move from `column 1` to `column 2`, which is the same reviewed-`columns` declaration S5-a
built, so S5-d is now cheaper than §5 implies. S5-b is now the expensive one, and §4's continuation act
is the reason.
