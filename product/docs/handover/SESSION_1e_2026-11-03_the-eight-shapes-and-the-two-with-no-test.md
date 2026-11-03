# Session `1e` — 2026-11-03 — the eight shapes, and the two that have no test

**For:** the next agent.
**Task:** D80 / G12 — write the ingestion engine's PRD, then commit the eight-shape fixture set
before any engine code, and settle the untracked F3 review surface.
**Repo state at the close:** `main`, five commits on top of `1d`'s close, unpushed.

---

## 1. What this session had to establish first, and did not inherit

The handover said the spec's measured starting point was "44 reviewed table rows across four
documents, four bespoke test files, and two tables still mangled", and that **which of the eight
shapes already have a test is the first thing to establish, not a fact to inherit**. Measured on this
tree with no PDF and no database (a probe over the artefacts, `knowledge/tables.py`, and the page
fixtures):

| Claim | Measured |
|---|---|
| 44 reviewed rows, four documents | **44 rows, three documents**: OPP §2.3 **6** (artefact block, PDF 2), landscape **8** (three blocks, PDF 4–8), SAOSO Appendix 2 **30** (Python literals, printed 76–78). BPP has no table. |
| …and Appendix 6a? | **20 further rows exist as literals** — `TableRow(substance, condition)` — and each ships as a chunk reading `"Equines over six months old\n2"` with **empty** `embedding_text`. So the corpus holds 64 reviewed rows and 44 of them carry column meaning. |
| four bespoke test files | **ten modules assert a table shape**, of which four are the shape-level ones: `test_corpus_tables` (52 tests), `test_tables` (18), `test_landscape_table_block` (14), `test_row_blocks` (9). |
| two tables still mangled | confirmed, and worse than "mangled": Appendix 6a ships **20** chunks with no column label, and Appendix 7 ships **4** interleaved chunks (`"7 Use of sulphur dioxide, Sulphur dioxide,\n\npotassium bisulphite or …"`). |

And the answer to the actual question — **six of the eight shapes already have a test; zero of the
eight has a test whose input is the shape.** Every existing assertion reads a *review* (a human's fix,
already applied). The two shapes with no test at all are exactly the two live defects: header lost
(6a) and column-major interleaving (7). That is now a test, not a paragraph
(`test_the_two_live_defects_are_the_two_shapes_with_no_test`).

Three further measurements the fixture set needed, taken from the review's own numbers so nothing is
inherited: the landscape's longest cell is **1,112** characters (the exploration says 1,107 — same
cell, line breaks counted differently), **12** empty cells across the landscape's three tables, and
Appendix 2's 11 rows on printed page 76 carry dividers before rows 0, 1 and 3.

## 2. What was built

**The PRD** — `product/backlog/In Progress/INGESTION_ENGINE_PRD.md`. Written before the fixtures, as
the task ordered, and with the audit above as §3.1 so the register and the paper cannot disagree. It
carries D80's recorded decision (X2 now, X3 when a document demands it) as prose, six slices
(S0 fixtures, S1 generator guard, S2 extractor evaluation, S3 generator emits blocks, S4 harness,
S5 re-review 6a/7), ten requirements, and the exploration's own falsifier ("if extractors lose spans
or qualifiers on more than two of the eight, X3 moves first").

**S0 — the eight-shape fixture set**, in two files:

* `knowledge/tests/shape_fixtures.py` — eight `ShapeCase`s. Each names the governed document, the
  extraction mode and the PDF page; an **anchor** (words the page prints, matched against the
  committed page fixture) as provenance; the **expectation** (`TableRead`: columns, rows, printed
  page per row, dividers, and `Cell` assertions including "printed empty"); what the artefact format
  can say today (`ir`: expressible / partly / no); the **gap**; and `covered_by`, the tests that
  exist for that shape.
  **The page text is not copied into the fixture.** It is read from
  `knowledge/tests/page_fixtures.py`, whose manifest pins the extractor banner and the source PDF's
  sha256 — one copy of the paper, one provenance chain. A hand-tidied copy of the page is the exact
  defect this set exists to catch.
* `knowledge/tests/test_ingestion_shapes.py` — 28 green tests and 8 strict-xfail targets.
  The green ones are about the fixtures: every anchor is a run of the page it names; the set is the
  exploration's eight in order; every cited test exists in the tree; the uncovered set is exactly
  `{headerless_values, column_major}`; every shape names a gap and an IR verdict; and the one place
  where the page's characters and the corpus's disagree is **declared** (6a prints
  `Other b o v i n e a n i m a l s less t h a n o n e year old`, the reviewed row rejoins it).
  The eight targets call `read_table()` — which raises `NotImplementedError` because there is no
  reader from a page to a table yet. They are `xfail(strict=True)`, so the gap is **counted in every
  run** (`8 xfailed`) and a shape that starts passing turns the suite red (`XPASS(strict)`) until the
  marker is removed and the audit updated.

The checker (`shape_fixtures.mismatches`) returns failures rather than asserting, so it can be
proved to fail: six mutations — a short row set, a filled-in silence, a transposed row, a dropped
divider, a wrong page, a missing column — each named, plus "a missing cell is not an empty one".

**S1 — `--force` may not delete a table block.** `scripts/build_corpus.py` gains
`table_block_counts()` and `table_loss_refusal()` (pure, no PDF and no extractor, like
`body_filter()`), and `main()` refuses **before writing** when the artefact on disk carries more
`<!-- table` / `<!-- row:` / `<!-- cell` / `<!-- row-divider:` markers than the draft would. The
refusal names the counts, the hazard (§3.25), and the override: **`--discard-tables`**, deliberately
not spelled `--force`, because a flag that means "overwrite" must not also mean "delete the review".
A draft that keeps *more* markers is allowed: that is the day S3 lands.

While wiring it, two `Path.relative_to(REPO_ROOT)` calls in `main()` turned out to crash when the
corpus directory is a temporary one — a guard that raises `ValueError` instead of refusing is not a
guard. `shown()` now handles both.

## 3. Verified, not assumed

| Check | Result |
|---|---|
| `scripts/fast.sh --critical` | **172 passed / 4 deselected in 52.15 s** — same eight files |
| `scripts/verify.sh` (`DATABASE_URL=…:5433/pgs_verify`) | **1644 passed / 1 skipped / 8 xfailed in 219.16 s**; step 1/4 printed `every budget holds` |
| Guard proved red #1 | removing `headerless_values` from `UNCOVERED` and changing one anchor to `Laying hens 999` → the audit and the provenance test both fail (restored) |
| Guard proved red #2 | disabling the refusal in `main()` → `test_main_refuses_before_it_writes` fails (restored) |
| Dev corpus | **untouched.** No `build_corpus.py`, no `ingest_standard`, no `corpus_refresh`. Live stays the reference DB |
| Budgets | the D80 row was 1,492 bytes; the PRD link needed 17 more, so two claims were **corrected** ("four documents" → three, "four bespoke test files" → ten) and the row landed at exactly **1500** bytes — under the cap without raising it |

**Gate cost went up 35 s** (183.57 → 219.16 s, one cold run each; quote the range, never one number).
The eight shape tests are 1.7 s; the rest is the fixture reads hashing the four PDFs.

## 4. The loose end: F3

`product/design/f3_saoso_outreach_and_role.html` was untracked (24 KB, "F3 — SAOSO outreach and the
digital systems role", a review surface with two documents to approve and three decisions they
force). **Committed, with a line in `todo.md`.** It is not D80's work and it is not a PRD: F1 and F2
were committed the same way, as design artefacts with no backlog entry. Deleting it would have thrown
away the only record of two documents the group still has to approve; absorbing it into D80 would
have mislabelled it. It is parked, named, and findable.

## 5. What is next

1. **S2 — the extractor evaluation.** Two candidates with published table structure (Docling,
   Document AI), measured against S0's eight pages: cells, headers, spans, speed. The output is a
   table in the PRD, not a preference. `read_table()` is the seam; the day it returns a `TableRead`
   the eight targets turn green and `strict` turns the suite red until the markers go.
2. **S5's honest order.** Appendix 6a is 20 rows and Appendix 7 is 17; both close *through* the
   harness, not through another hand review. Until then the audit test keeps naming them.
3. **Do not refresh the dev corpus**, and **do not run `build_corpus.py --force`** anywhere without
   reading the refusal first — it now refuses on OPP and landscape, and `--discard-tables` is the
   only way past it.
4. `CORPUS_CANONICAL_FORMAT_PLAN.md` still owns P2.6–P2.8, pdf 11's §6.5 table, and P6 step 4 for
   Appendices 3, 4 Table 1, 6b and 7.
