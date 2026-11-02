<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0r. 2026-10-31 — step 6: the reader draws the printed grid, and the fit was measured wrong

**State: green, committed.** `fast.sh` **1434 passed / 1 skipped in 36.6 s** (warm) and
`verify.sh` **1448 passed / 1 skipped in 49.7 s** (`--create-db`, 5433). Code at `d37bd9f`; this
documentation commit follows. The dev corpus is unchanged (17 / 17, 394 chunks); the live box is
still `8d2839d`.

### 0r.1 The decision artifact, and the number it corrected

`product/design/d76_reader_table_fit.html` lays out four options with **live mocks built from the
real Step 1 / Step 2 rows**, gives each its strongest case and its weakness, and recommends
**A + B + C, with D as the multiplier**: a real `<table>` at the passages pane's full width, a
14 px grid, a focusable scroll region with a sticky first column, and the same markup stacked
below 900 px with `data-label` column names. The D76 choice is the **product owner's** to confirm;
the implementation follows the recommendation and is one CSS/template change away from any of A–D.

**The artifact's Part 1 corrected the PRD's own measurement.** §5.4 said the widest row is
**323 characters** and “2× too wide”. `max(len(line))` on the `-layout` page returns the page's
**blank padding line**, not a row: the printed row's last non-space character sits at
**153–169**. And the grid's pane is **52.5 rem**, not 72 — the tree takes 17 rem and the gap 2.5.
So the fee starts at the pane's edge and only its **last 25–40 characters** scroll. One column's
worth, not two. §5.4 is corrected in place, with the command quoted in the artifact.

### 0r.2 What the reader does now

| Piece | Where |
|---|---|
| the artefact grid (columns + cells) | `knowledge/tables.ArtefactGrid`, `artefact_grid_for`, `align_artefact_grid` |
| the reader's grid | `core/services/_documents._artefact_grid`, `ReaderGrid`, `ReaderPassage.in_grid` |
| the markup | `document_reader.html`: one `<table class="reader__grid">`, sticky `<th scope="row">`, `data-label` per cell |
| the CSS | `reader.css`: full passages-pane width, 14 px, scroll + sticky, stacked below 900 px |
| the map | `knowledge/ingest.source` + `doc_key_for` — a stored document to its artefact, no title guessing |
| `DESIGN.md` | §7.13 — the component and the rules it carries |

**The fallback is the plain page.** `align_artefact_grid` returns `None` when any row's chunk no
longer matches the artefact, and the reader renders the passages it has — a mislabelled row is
worse than no grid, the same rule `structure_for` already follows. A test edits a stored chunk
(`R500` → `R5OO`) and proves the grid disappears while the text still renders.

### 0r.3 The guards

- `core/tests/test_document_reader_grid.py` (12): five column names, the fee inside the grid, the
  lead-in outside it, each row's citation anchor exactly once, the seals table's two rows and the
  prose after it, the direct-route row, a prose branch with no grid, and the stale-corpus fallback.
- `knowledge/tests/test_corpus_tables.py` (+3): `ArtefactGrid` columns/cells, alignment with prose
  around the row, and `None` on any disagreement.
- `tests/e2e/test_reader_layout.py` (+2, browser): at 1280 px the grid wrapper does not scroll and
  the Fee cell holds `R500`; at 390 px the same markup restacks, the page does not scroll sideways,
  and the `Fee` label is on screen. The fit is a CSS question the Django client cannot answer.
- `DESIGN.md` §7.13 records the rules: the table is the one place the 38 rem measure gives way; the
  first column is pinned; below 900 px the same markup restacks; empty cells disappear on the
  phone; page breaks are marked once.

### 0r.4 What is left

- **D77 — the display model.** The owner chose **E** (a `layout: process | grid` field; a process
  flow for Establishing/SAOSO, a resizable spreadsheet for the seals comparison) and **C3** as the
  process shape. The branch is two stacked cards in one column (`branch:` data), explored in
  `product/design/d76d_c3_and_the_split.html`; the split placement and the short titles are the last
  open details. The current reader is the fixed grid from §12e; it stays until those are picked.
- **D76's confirmation** — the fit artifact; D77 revises it.
- **`TABLE_BANDS`** — a transposition *inside one printed row-line* is still unpinned. A corpus
  guard, not a reader feature.
- **The corpus-level table-page guard.**
- **Step 7** — the `tests/uat/` fee scenario, the backlog move, and the §5.7 exclusion verified as
  “reading order restored, nothing more”.

**Do not run `scripts/build_corpus.py --force --doc landscape`.** The generator has no table-block
rule; the per-line guard fails loudly if it does, but the command has no other defence.

---
