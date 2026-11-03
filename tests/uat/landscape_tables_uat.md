# UAT — The certification landscape's tables: cards, a fork, and a spreadsheet

**Feature slug:** `landscape_tables`
**PRD:** `product/backlog/Done/LANDSCAPE_TABLES_PRD.md` (§12f, built in §12g, signed in §12h)
**Decision:** `PGS_PLATFORM_SPEC.md` §18.3 D72 (the rows are reviewed data), D76 (the printed grid), **D77 (a layout per table)**
**Design:** `product/design/d76d_c3_and_the_split.html` · `product/design/DESIGN.md` §7.13
**Status:** **SIGNED** — 6 PASS, 0 FAIL, 0 N/A, signed by Kobus (Product): **first pass 2026-11-01 against `ecd3c8d`**, **re-signed 2026-11-03 against `c4c362e`** after §12h (the seals legend) and §12i (the folds moved to the prose), which changed Scenarios 2 and 4. Applied by `scripts/uat_signoff.py` both times; the second export carried the first pass's card dates, so the `**Signed against:**` line is what dates the re-judge. The PGS administrator and committee reviewer seats are still empty (D4) and are not blocking.
**Date:** 2026-11-01

---

## Purpose

Per `build_principles.md` §VIII, **UAT holds only checks a human must judge.** Every item below
carries a `Judgement:` clause naming the human-only call. What a test can prove — three cards, five
columns, a `<details>` that is closed, an anchor that resolves, no forbidden claim — is in
*Automated coverage* and is **not** put in front of the reviewer as work.

This slice has one question behind all six scenarios, and it is the report that started it:

> A reader asked *"what does it cost to join a PGS group?"* of a page that rendered the paper's
> five-column table as column-major soup, cut mid-cell. The rows are now reviewed data and the
> reader draws them in two shapes. **Does a reader who is not us get the answer, and does the page
> still read as the paper rather than as a brochure about the paper?**

Two things are deliberately *not* judged here, and the handover names them instead: `TABLE_BANDS`
(a transposition *inside* one printed row-line is still unpinned) and the corpus-level table-page
guard.

---

## Pre-test setup

**The setup is buttons now.** Open **`/uat/?uat=landscape_tables`** on the instance you are judging
(staff login), press *Seed the deployment*, *Publish the documents*, *Re-check the instance*, then
*Rebuild the UAT page*. The page shows each preflight check with its observed and expected value,
the three reader addresses below as links, and the exact command behind every button. Nothing there
decides a verdict — that stays yours.

The commands, if you prefer a terminal or the console is unreachable:

1. `python manage.py seed_deployment && python manage.py publish_documents`, then
   `python manage.py runserver`.
2. **No re-ingest is needed for this slice.** The artefact gained four header fields
   (`layout:`, `branch:`, `title:`, `fee_label:`) and its chunk text is byte-identical; the reader
   reads the artefact from disk. `python manage.py corpus_check` will still say `landscape drift` —
   that is the artefact file's hash moving, not the text (see the handover). Judging on a drifting
   corpus is fine here; judging on a *stale* one is not, so if you re-ingest first, use
   `corpus_refresh --apply`.
3. Keep these three branches open in tabs — one per table:
   - `/documents/certification-landscape/read/?section=establishing-a-pgs-group`
   - `/documents/certification-landscape/read/?section=saoso-organic-certification`
   - `/documents/certification-landscape/read/?section=pgs-seals-and-their-use`
4. Have a **real phone** in hand for Scenario 5, and judge it in daylight if you can.

---

## Automated coverage (NOT UAT — asserted by the suite)

Recorded so the manual list is not padded with machine-provable work.

| What | Where |
|------|-------|
| `ESTABLISHING A PGS GROUP` renders exactly 3 cards, in printed order, each with its reviewer title; Resources and Seals are `<details>` closed by default; Use of seals is visible prose | `core/tests/test_document_reader_grid.py::test_the_establishing_branch_renders_three_step_cards`, `…::test_the_two_folded_facets_are_closed_and_the_seal_rule_is_not` |
| The merged Fee cell is **one** box spanning Steps 1–2 and Step 3's its own, each holding the full cell; no amount appears alone | `…::test_the_merged_fee_is_one_box_with_the_whole_cell_under_steps_1_and_2` |
| `SAOSO ORGANIC CERTIFICATION` renders 2 step cards + a fork; Path A links to Step 2 and repeats no fee; the direct route keeps its own full cell | `…::test_the_saoso_branch_renders_two_steps_and_the_fork`, `…::test_path_a_is_a_pointer_to_step_2_and_repeats_no_fee` |
| `PGS SEALS AND THEIR USE` is a real `<table>` with `<colgroup>`, a separator per boundary, and a `data-grid-key`; the columns resize by keyboard and the width survives a reload; Compact changes the type size | `…::test_the_grid_carries_what_the_resizer_needs_and_nothing_it_requires`, `tests/e2e/test_reader_layout.py` (keyboard resize, Compact) |
| At 1280 px the cards are one row and the fee boxes sit under them; at 390 px they stack; the two paths are one column; neither page scrolls sideways | `tests/e2e/test_reader_layout.py` |
| The four header fields are refused when malformed (unknown `layout:`, a `branch:` naming no row, a `title:` list of the wrong length), and the artefact's own declarations are pinned | `knowledge/tests/test_corpus_tables.py`, `knowledge/tests/test_corpus_landscape.py` |
| The page-crop exclusion does nothing to the shipped corpus: the ingest never transforms a page, and a reviewed cell is still not quotable off the excluded page | `knowledge/tests/test_ingest.py::test_the_landscape_page_exclusion_has_no_reach_into_the_ingest`, `knowledge/tests/test_columns.py` (§5.7) |
| No forbidden certification claim on the reader, and no unrendered template syntax | `core/tests/test_claim_discipline.py`, `core/tests/test_public.py` |

---

## Scenario 1 — The fee question, which is why any of this exists

**Setup:** the *establishing a PGS group* branch, read as a visitor would — from the top, not
through the contents list.

1. Read the three cards in order, down to the fee boxes. Ask the page the question the reader
   asked: *what does it cost to join?*
2. Without scrolling back, say out loud what the joining fee covers and who it is paid to.
3. Read Step 3's own fee the same way.

**Expected:** the two fees are in boxes under the steps they belong to; the joining box states the
annual membership and the once-off amount **inside the paper's sentence**, and says it covers
Steps 1–2; the certification fee sits under Step 3.

**Judgement:** *Did you find the answer without hunting, and does each box say what the money buys
and who it is paid to?* A box holding a bare "R500" is the failure D72.2 forbids — the amount is
never published on its own. Say plainly whether you would quote this page to a farmer who asked.
**Result:** PASS · Kobus (Product) · 2026-11-01

**Status:** `Ready`

---

## Scenario 2 — A card you can scan, and the one fold the design left to UAT

**Setup:** the same branch. All three cards now fold their two **text** facets — Resources and
*Use of seals* — closed by default. The `Seals and logos` column is not drawn: its cell is the
printed caption of a picture the corpus does not store.

1. Read the three cards as they arrive, judging the step body on its own.
2. Open Resources, then *Use of seals*, on each step that has one. Read them.
3. Notice what you had to open to answer a question, and what you never needed.

**Expected:** each card leads with the step and what happens in it; the reference material and the
long rule are each one closed fold away, signed by the paper's own column heading; nothing is
behind a fold that you did not want to open.

**Judgement:** *Is the step body now the thing that leads, and is anything you needed behind a
fold?* This is the decision the design deferred (§12f item 3) and **the owner took it on
2026-11-03** (`LANDSCAPE_TABLES_PRD` §12i): *Use of seals* folds with the same element as
Resources, because on Step 3 it is ten paragraphs and the facet that used to fold opened onto one
caption, "Proud member of". Say whether that reads better than the open rule did.
**Result:** PASS · Kobus (Product) · 2026-11-01

**Status:** `Ready`

---

## Scenario 3 — The fork reads as a fork, not as a fourth step

**Setup:** the *SAOSO organic certification* branch.

1. Read Step 1 and Step 2 as steps.
2. Read the third column top to bottom, through the `or`.
3. Compare the pointer's wording with Step 2 — is it a signpost or a second summary?

**Expected:** the third column holds **two** cards stacked with an `or` between them; the first is a
pointer to Step 2, the second is the paper's direct route with its own fee; the frames are dashed.

**Judgement:** *Would a reader understand they must take one route or the other — and that the
pointer is a signpost, not a second summary of Step 2?* The risk the design named: Path A
drifting into a duplicate of Step 2, and repeating its fees (which D72.2 would then break in a
new place). Judge whether it reads as a signpost at this size.
**Result:** PASS · Kobus (Product) · 2026-11-01

**Status:** `Ready`

---

## Scenario 4 — The comparison is a spreadsheet, and it reads without being dragged

**Setup:** the *PGS seals and their use* branch. **First resize nothing.**

1. Compare the two seal rows across the five columns.
2. Drag a column edge — or tab to a handle and use the arrow keys. Then reload the page.
3. Press **Compact**, read the same rows, and press it again.

**Expected:** the header and the first column stay put as you compare; every column is the same type
size; the resize handle is discoverable and does nothing destructive; Compact tightens the same
columns rather than rearranging them.

**Judgement:** *Is the comparison legible without touching a control — and if you did resize, did
the table end up more useful rather than merely different?* A reader who never drags must still be
able to compare the two seals. Say whether Compact is worth having at all.
**Result:** PASS · Kobus (Product) · 2026-11-01

**Status:** `Ready`

---

## Scenario 5 — A real phone, 390 px, in daylight

**Setup:** a **real phone** at default zoom — not a browser's device emulation.

1. Open all three branches in turn.
2. On the establishing branch, read the fee answer.
3. On the SAOSO branch, find the fork and read which route is which.
4. On the seals branch, compare the two rows.

**Expected:** the cards stack in printed order, the fork follows the step it branches from, the
spreadsheet restacks into labelled blocks, and nothing needs a sideways swipe.

**Judgement:** *On a phone in daylight, can a farmer read the fee answer without pinching or
swiping?* This is the one judgement a browser at 1280 px cannot make, and it is the reason the
design refused an `overflow-x` rail.
**Result:** PASS · Kobus (Product) · 2026-11-01

**Status:** `Ready`

---

## Scenario 6 — What the pages refuse to claim

**Setup:** all three branches, read for words rather than for structure.

1. Read each branch and note every word the page adds that the paper does not print.
2. Check what the pages say about the seals and about who is certified.
3. Read the legend above each table.

**Expected:** the cards and fee boxes carry the paper's own words. The labels the renderer adds are
neutral — `Steps 1–2`, `Step 3`, `Path A`, `Path B` — and the legend says the seals are pictures
that are not stored. No page says a farm, a person or a product is certified.

**Judgement:** *Would the committee be comfortable with these three pages as the group's public
statement of what the landscape says?* `test_claim_discipline.py` catches the forbidden terms and
nothing about framing; the residue — a fee that reads as a quote, a route that reads as an
endorsement — is this scenario.
**Result:** PASS · Kobus (Product) · 2026-11-01

**Status:** `Ready`

---

## Sign-off

| Role | Name | Date | Result | Notes |
|---|---|---|---|---|
| Product owner | | | | |
| PGS administrator | | | | |
| Committee reviewer | | | | |

### Per-scenario results

| Scenario | Category | Result | Reviewer | Role | Date |
|---|---|---|---|---|---|
| 1. The fee question, which is why any of this exists |  | PASS | Kobus | Product | 2026-11-01 |
| 2. A card you can scan, and the one fold the design left to UAT |  | PASS | Kobus | Product | 2026-11-01 |
| 3. The fork reads as a fork, not as a fourth step |  | PASS | Kobus | Product | 2026-11-01 |
| 4. The comparison is a spreadsheet, and it reads without being dragged |  | PASS | Kobus | Product | 2026-11-01 |
| 5. A real phone, 390 px, in daylight |  | PASS | Kobus | Product | 2026-11-01 |
| 6. What the pages refuse to claim |  | PASS | Kobus | Product | 2026-11-01 |

**Results:** 6 PASS · 0 FAIL · 0 N/A — signed by Kobus (Product).

**Signed against:** commit `c4c362e` (clean), database `pgs`, generated 2026-11-03.
