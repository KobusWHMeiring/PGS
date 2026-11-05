# Session `1q` — 2026-11-05 — Appendix 6a becomes a block, and a body is the pass its block declares

**Repo:** `main` at `1aa152c`, clean apart from another session's `copy_deck` work.
**Task:** S5 of `INGESTION_ENGINE_PRD.md` — re-review Appendix 6a and Appendix 7 through the
harness and delete their bespoke handling.

## 1. What I did first, and what it changed

I read the recipe (`scripts/context.py --task corpus`, `--task backlog`), the PRD's §3.14, §3.15,
§4, §5, §6, and the four files the prompt named, then **measured the tree before writing a line**.
Five measurements changed the shape of the job, and each is now a hazard entry or a plan section:

1. **`saoso.md` reproduces byte for byte** today (171 479 chars, diff 0). S5's safety net: a block
   added to it is a reviewable diff and nothing else moves.
2. **`opp.md` reproduces byte for byte**, and `check_tables --doc opp --rows 6` → `ok`.
3. **`check_tables --doc landscape --rows 3,2,3` → `ok — 3 tables, 8 rows, 0 violations`.** The
   landscape's *artefact* is fine; its *generator* is what is broken.
4. **`build --doc landscape` cannot reproduce `landscape.md`, and that is pre-existing.** Pages 2–3
   and 9 print no heading `HeadingParser` opens; those sections are the **reviewer's** (commit
   `8674d7a`, "the front matter the PDF parser could never open"). A wholesale `--force` would
   delete INTRODUCTION, SIX BASIC ELEMENTS, the three route sections and the colophon. So the DoD's
   "landscape.md regenerated so the diff is the review" has to be read as "the *blocks* are
   generated; the reviewed front matter is not rewritten".
5. **A page is not a section.** Appendix 5's body runs to the line before Appendix 6a's heading, so
   it carries page 86's top lines. My first page-scoped substitution put the whole `-table` page —
   title, header and 20 rows — inside Appendix 5 as well. Hazard §3.35.

## 2. What landed (S5-a)

**The missing capability: the body is the pass the block declares.** A block records
`extraction: table|layout|raw` and the gate judges its cells against *that* pass — but the generator
sliced every section from the de-columned geometry stream. So a `-table` block was assembled from
`-layout` text and judged against `-table` text; one of the two was always wrong. That is precisely
why S3 could not emit the landscape: `choose_pages` takes its pages from `-raw`, the page-4 header is
not a run of any line in that stream, and the emitter refused at `column 1`.

`scripts/corpus_pages.substitute_pass` (pure, fixture-testable) replaces the lines of the pages a
proposal names with those pages from the pass the proposal declares, and
`scripts/corpus_pages.pass_texts` slices the other pass **through the document's own `body_lines`
rule** — one furniture judgement, two renderings. `build()` substitutes only in the section whose
heading page the proposal names.

**The reviewed column label.** Appendix 6a prints its header once, as two levels of type across four
lines with a merged cell; all four arms flattened it. The owner arbitrated the two labels on
2026-11-05, and a one-line `cols:` cannot be a slice of a multi-line header — so
`knowledge/proposals/saoso.reviewed.json` carries `columns`, and the emitter writes it instead of
resolving the arm's. Cells are untouched by it: `test_a_reviewed_label_never_makes_a_cell_the_reviewers`
proves a cell the page does not print is still refused.

**The one declared normalisation, gated.** The paper letter-spaces part of the class column
(`Other b o v i n e …`); `CORPUS_EDITS` already rejoins it, with a page and a reason. R3 now accepts
the review's spelling **only** on a line that itself carries a spaced run, and refuses a page that
glues its letters. `CORPUS_EDITS`' multiplicity guard became `occurrences:` — a block writes a row's
label as an annotation *and* the same words as the cell, so a corrected cell occurs twice.

**Appendix 6a is a block, and the Python is gone.** `APPENDIX_6A_ROWS`,
`TABLE_ROWS["Appendix 6a"]` and `TABLE_SECTIONS["Appendix 6a"]` are deleted; the ingest reads the
artefact's block through `chunks_for_parsed_section`.

**And the block fixed the paper.** The committed artefact paired `Equines over six months old` with
`5` — its neighbour's value, the `-layout` interleaving. The emitted block pairs it with `2`. That
hunk is the PRD's opening defect, in the diff.

## 3. Measured

* `build_corpus --doc saoso --force` → `101 insertions(+), 25 deletions(-)`, one section: the
  interleaved page becomes a 20-row block. `--doc opp --force` leaves `opp.md` **byte for byte**
  unchanged (S3's regression).
* `python scripts/check_tables.py --doc saoso --rows 20` → `ok — 1 tables, 20 rows, 0 violations
  (table pages, recorded on the artefact)`.
* `python scripts/check_tables.py --doc landscape --rows 3,2,3` → `ok — 3 tables, 8 rows, 0
  violations` (unchanged; its blocks are still the reviewed ones).
* Full suite: **1831 passed / 1 skipped / 8 xfailed in 97.74 s** `--reuse-db` against
  `…/5433/pgs_verify` (warm; the same suite measured 79.19 s on a less loaded minute — quote both,
  §3.17). `scripts/fast.sh --critical` **182 passed / 4 deselected in 18.42 s**.
* Three guards broken and watched red: the reviewed label, the pass substitution, R3's
  letter-spacing fallback (`3 failed` mutated → `3 passed` restored).
* `scripts/verify.sh` still cannot be quoted green from this tree: step 1 fails on **another
  session's** `scripts/copy_deck.py` (32 KB). My own files are inside the cap —
  `scripts/build_corpus.py` was 30.5 KB after the change and is 29.1 KB again, because
  `pass_texts` moved to `corpus_pages.py`.

## 4. What S5 still needs, and why it is a review rather than a chore

`INGESTION_ENGINE_S5_PLAN.md` §5 has the slices. The three reasons, measured this session:

* **Appendix 2 is 30 rows, not 11.** The cached `qualifier` response is the shape page (pdf 77 =
  printed 76, 11 rows); printed 77–78 have no arm read and S5 may not re-run the arm. Emitting 11
  rows would leave 19 interleaved *and* `APPENDIX_2_ROWS` in place — deleting nothing.
* **Appendix 7's cells wrap inside a column.** `Aeration or oxygenation` / `using gaseous oxygen`,
  with `Air,` beside it on the *same* line and belonging to the next column. `_resolve`'s
  continuation branch takes "the rest of the line" as the cell's head, so it cannot express a cell
  bounded by the next column. Docling's grid (`rows 7/7, cols 5/4` with the gutter declared) is the
  evidence for those boundaries.
* **The landscape's four declarations** (§3.15) plus the splice: its artefact cannot be regenerated
  wholesale (measurement 4). With the pass rule in place its refusal moved from `column 1` to
  `column 2` — `Resource documents, guidelines and requirements` is printed across two lines, which
  is the same reviewed-`columns` declaration 6a needed. That is real progress and it is *not* a table.

The PRD stays in `In Progress/`. §5's S5 row and §6 carry what is true now, with the remainder named.

## 5. Files

* `scripts/corpus_pages.py` — `substitute_pass`, `pass_texts`.
* `scripts/build_corpus.py` — the body is the pass the block declares; the page in force at a body's
  *start* is what `emit_tables` is given; `declared_passes` accumulates (a dict comprehension keyed
  by extraction kept only the last table's pages).
* `scripts/table_blocks.py` — the reviewed `columns` branch.
* `knowledge/table_harness.py` — R3's letter-spacing fallback, gated on `has_letter_spacing`.
* `knowledge/corpus_tables.py` — `has_letter_spacing` / `SPACED_RUN`, one copy for emitter and judge.
* `knowledge/table_proposals.py` — `ProposedProfile.columns`, refused when the count disagrees.
* `knowledge/corpus_edits.py`, `scripts/corpus_review.py` — `CorpusEdit.occurrences`.
* `scripts/propose_tables.py` — `--append`, so a document's structure can be assembled from several
  responses into one banner.
* `knowledge/proposals/saoso.structure.json`, `saoso.reviewed.json`, `README.md`.
* `knowledge/tables.py` — `APPENDIX_6A_ROWS` and its two registry entries deleted.
* `knowledge/corpus/saoso.md` — the block.
* Tests: `tests/tools/test_table_blocks.py`, `test_build_corpus.py`, `test_check_tables.py`,
  `knowledge/tests/test_table_harness.py`, `test_table_proposals.py`, `test_tables.py`,
  `test_corpus_saoso.py`, `test_passages.py`.
* `product/docs/context/testing_hazards.md` §3.35–§3.38; `INGESTION_ENGINE_S5_PLAN.md`; PRD §3.16.

## 6. The owner read the paper, and it paid (added after the fact)

S5-b looked like a decision that could be made from measurements. It could not, and the thing that
settled it was a person looking at the page.

Two artefacts were built for that in `product/design/`:

* `s5b_appendix_2_rows_exploration.html` — the decision: Appendix 2 prints 30 rows on three pages,
  the cached arm read 11, and **39 of 41 cells are already runs of the page** once the printed line is
  cut at the column boundary `TABLE_BANDS` has held since 2026-10-21. Recommendation A (band + the two
  continuations, 30 rows, delete the bespoke path); "what would change my mind" included.
* `s5b_appendix_2_pages.html` — Appendix 2's three printed pages beside the review, the machine read
  and the artefact's current text. Flag-a-row, verdict, export.

From the second, three findings:

1. **The seaweed row's tail is printed `(iii) fermentation.`** — with the opening bracket — as the
   first line of printed 77. The reviewed cell had dropped it. `_scratch/seaweed_probe.py` shows the
   string in all three passes.
2. **Where the wrong spelling came from:** printed 79, where Appendix 3 prints
   `Coffee grounds    iii) fermentation.` — a different table, two pages later. One phrase, two
   spellings, one document.
3. **Rows 27–29 (printed 78) read right**, as printed.

**The guard could not have caught it.**
`test_the_seaweed_condition_crosses_the_page_break` asserted `endswith("iii) fermentation.")` and
`"iii) fermentation." in <printed 77>`; both were true of the wrong text because the shorter string is
a substring of the page's. It is character-level now, proved red on the old data, and the cell is
corrected by one character (hazard §3.39). `_words()` strips brackets by design, so every word-level
guard in `test_tables.py` is blind to this class.

The correction reaches `DocumentChunk` on the next `ingest_standard --doc saoso --force`; the artefact
is untouched, because Appendix 2's rows are still Python data — which is S5-b's job. **The lesson for
S5-b is in the plan §4:** the reviewed rows are a good source and *not an oracle*, so every one of
them enters as a locator the emitter must find on the page.

## 7. The next session's first command

```bash
python scripts/check_tables.py --doc saoso --rows 20   # ok, 0 violations
python scripts/check_tables.py --doc landscape --rows 3,2,3
python scripts/build_corpus.py --doc saoso --stdout >/dev/null   # 20 rows emitted, 0 refusals
```

Then S5-b: Appendix 2's 30 rows. Read `INGESTION_ENGINE_S5_PLAN.md` §4 first — the continuation act
is the decision, not the code.
