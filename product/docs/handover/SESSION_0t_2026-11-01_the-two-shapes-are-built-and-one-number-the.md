<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0t. 2026-11-01 (session 6) — the two shapes are built, and one number the design did not decide

**State: green, committed in six slices.** `e6d7b17` is the data (parser, alignment, reader shape);
`e29a27b` is the shape itself (template, CSS, JS, tests); `a0254be`/`8d6f61b` are the handover and
the UAT; `e7a331a` is §5.7 verified; `e14c616` is the `/uat/` registry and the preflight pin;
`a1358c7` records `testing_hazards` §3.23. `fast.sh` **1467 passed / 1 skipped in 34.4 s** (warm), `verify.sh` **1481 passed / 1 skipped
in 48.3 s** (`--create-db`, 5433), `pytest tests/e2e` **71 passed**. §12f.3 steps 1–8 are done;
**step 7 is untouched** and is the whole of what remains, apart from the two guards.

### 0t.1 What the reader does now

| Table | `layout:` | What it draws |
|---|---|---|
| `ESTABLISHING A PGS GROUP` | `process` | 3 cards (`Step N · title`), Resources and Seals folded, Use of seals visible, the merged joining Fee as one box under Steps 1–2 and certification Fee under Step 3 |
| `PGS SEALS AND THEIR USE` | `grid` | the spreadsheet: frozen header and first column, resizable columns, Compact, Reset, widths persisted |
| `SAOSO ORGANIC CERTIFICATION` | `process` | 2 step cards + a split in the last column: Path A (a pointer to Step 2, no fees) `or` Path B (the paper's direct route) |

`ReaderCard`, `ReaderFacet`, `ReaderFeeBox` and `ReaderGrid.cards` are the display model;
`knowledge/tables.GridAlignment` now carries the row positions **and** the passage the fork starts
at. No migration, no model change.

### 0t.2 The judgement that was not in the design

§12f.1 says `fee_label:` is "one per fee box" but never says **how a box knows which cards it
covers**. The merged joining fee must sit under Steps 1–2 and a fifth data field was not among the
four the owner approved. It is read from the **recorded empty cells**: a fee box runs until the next
printed Fee cell, which is Step 3 — Step 2's Fee cell is printed empty and the artefact records
silence as empty. The legend still says it in prose; the renderer does not parse the legend. Pinned
by `test_the_merged_fee_cell_is_one_box_under_steps_1_and_2`.

Two smaller readings, each with a fallback that loses nothing: the **folded facets** are the ones
the paper's own headings name (`Resource…`, `Seals and logos`) and any other heading renders visible;
the **fee column** is the one printed `Fee`, and a `process` table without one renders every cell as
a facet.

### 0t.3 Three things the real rows taught, and a mock could not

1. **The label is printed twice**, and arrives in two shapes. `Step 1` is its own block
   (`passage_blocks` reads it as a `Term`); `Step 2`'s blank line is lost in the PDF's text layer, so
   it merged into the following sentence and had to be stripped as a prefix. Not stripped when the
   block carries cross-reference segments — those point into the text they were built from.
2. **A path card keeps its label.** Path B's first cell is one sentence — *"For farmers wanting
   direct 3rd party certification to the SAOSO standard. …"* — so stripping the label there leaves a
   fragment. The rule is tied to what the heading prints: a step's heading prints the label, a
   path's prints `Path B`.
3. **`reader.css` crossed §II's 30 KB cap** at 35.4 KB and the gate said so by name. The table
   domain moved to `reader-tables.css` — the seam the design already had: the reader, and the
   printed table.

### 0t.4 What the browser lane found that nothing else could

- **A 6 px sideways scroll at 1280 px.** `reader-grid.js` measured the auto layout, froze it, and
  `table-layout: fixed` added the collapsed borders back — so the wrapper scrolled by the borders'
  width. Fixed two ways: the resizer is not attached to the **last** column (it overflowed the
  table's right edge by half its width), and `apply()` now takes any residual excess off the widest
  column.
- **The CSS split changed nothing visually** but would have gone unnoticed as a 500 or a missing
  rule; the e2e suite is what confirms both shapes still render from the new stylesheet.

### 0t.5 Guards, and the count

**+36 test functions** (against `a01f698`), of which 31 are in the gate: 16 in
`knowledge/tests/test_corpus_tables.py` (four fields, four refusals), 4 in `test_corpus_landscape.py`
(the artefact's own declarations), 11 in `core/tests/test_document_reader_grid.py` (cards, facets,
fee spans, the fork, the resizer markup). The gate's collected count went **1449 → 1482**. The
browser lane gained 5, to **71 collected**. Every refusal was mutated and watched red before it was
trusted.

### 0t.6 Step 7, half done — and a preflight that was lying

**§5.7 is verified** (`e7a331a`). Three guards now hold "reading order restored, *nothing more*":
p4–8 are still detected as column-laid-out and the exclusion leaves them byte-identical;
`apply_layout` is replaced with a bomb during a landscape **artefact** ingest and never runs, so the
exclusion cannot reach the shipped corpus; and the Step 1 cell is still **not** a contiguous run of
the excluded page, which is the "nothing more" half. The claim was designed in §5.7 and had never
been re-measured.

**The UAT is drafted and unsigned** — `tests/uat/landscape_tables_uat.md`, six judgment scenarios,
presented to `product/design/uat/landscape_tables.html`, pinned in `tests/tools/test_uat_parse.py`
so a scenario cannot vanish. It stays in `In Progress/` until a signature exists.

**The preflight was failing on its own stale constant.** `EXPECTED_CHUNKS` read 385 (SAOSO 319 +
landscape 8) — which is what the *live* box holds. This dev box holds **394**, because SAOSO and
landscape are now built from their reviewed artefacts (319 → 338, 8 → 17). So `uat_seed --check`
reported `NOT ready` against a corpus that is exactly right: a blocking failure that was the
check's fault, which is the worst shape a preflight can take. Now 394, composition and reason
written beside it, pin moved with it (`e14c616`). OPP (30) is the one component still parsed from
its PDF.

**`/uat/` prepares any registered UAT.** It already ran the setup as buttons but was pinned to the
MVP 0 file, so *Rebuild the UAT page* would have regenerated the wrong artefact. `UATS` is now a
**registry** (`core/services/_uat_console.py`), chosen with `?uat=<slug>`; an unknown slug is a 400
on GET and POST, because a request must never name a file for a rebuild. The console also lists the
addresses the selected UAT tells the reviewer to open, read from the markdown.

**Two operational notes for whoever starts the dev box.** Start `runserver` **without**
`--noreload` when editing Python and templates together: with it, the running process executes the
old view and renders the new template, which produced a `NoReverseMatch` on `/uat/` while every
test passed (`testing_hazards.md` §3.23). And `scripts/probe_chat.py` prints a `●` — on this console
that is `UnicodeEncodeError` unless you run it as `PYTHONIOENCODING=utf-8 python
scripts/probe_chat.py …` (§3.21).

### 0t.7 The fee question, measured — three answers and one refusal

The owner asked `/ask/` what the yearly cost is, got the R100 membership fee, followed the citation
to the OPP and found §2.3's sliding scale rendered as prose. Five runs through the product's own
path, same day, 394 chunks:

| Question | Answer |
|---|---|
| *"What is the yearly cost to get certified, including the farm visit?"* (the eval set's wording) | complete — membership, assessment (all six bands), transport, licence — **3 of 3 runs**, grounded |
| *"what does it cost to join"* | complete — §2.1, §2.3, §2.4, grounded |
| *"what is the yearly cost of membership"* | **membership only** — R100 + R500 |
| *"what is the yearly cost"* | one run **REFUSED** (7 raw / 6 audited), one complete (10 raw / 8 audited) |

**Retrieval is not the cause**: the top eight are §2.3 (1), §2.4 (2), §2.2 (3), §2.5 (4), §2.6,
§4.7, §2.1 (7), §4.6 — every locator `escalated-yearly-cost` grades. The thin answer is a scope
choice, and G3's acceptance therefore holds only when the question names certification or the visit.
The refusal is a **second, unlocated** finding: a correct answer discarded because two of ten
citations failed, cause not captured before the session ended — reproduce with
`scripts/why_refused.py`, which is how G9 was named. Both are `CHAT_ANSWER_COVERAGE_PRD` **G10**,
and the instrument cannot see either, because `eval_retrieval` grades where a clause *ranks*.

### 0t.8 What is left, and the one command that still hurts

- **Step 7's signature, then the move** — the UAT is drafted, presented and pinned; §5.7 is
  verified. What is left is a person judging six scenarios and `scripts/uat_signoff.py`.
- **A cost-question answer rule**, then **P4's OPP artefact with §2.3 as a table** — the two halves
  of the owner's report, measured in §0t.7 and filed as `CHAT_ANSWER_COVERAGE_PRD` G10 and
  `CORPUS_CANONICAL_FORMAT_PLAN` P4 (whose "blocked as written" note is stale: the inverted `keep`
  it names was fixed on 2026-10-30).
- **`TABLE_BANDS`** and **the corpus-level table-page guard** — both still open, both still named.
- **`scripts/build_corpus.py --force --doc landscape` still destroys the review.** Nothing this
  session changed that, and the generator still has no table-block rule.
- The **live box** now misses two sessions (grid + shapes) and its corpus is still PDF-built.

---
