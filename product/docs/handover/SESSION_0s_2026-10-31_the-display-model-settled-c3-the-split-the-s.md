<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0s. 2026-10-31 (session 5) — the display model settled: C3, the split, the spreadsheet

**State: green, and no code changed.** The gate is the same tree as §0r: `fast.sh` **1434 passed /
1 skipped in 36.6 s** (warm), `verify.sh` **1448 passed / 1 skipped in 49.7 s**. The session
produced **design artifacts and a decision**; the reader still renders the interim fixed grid from
§12e. Design artifacts at `2190279`; this documentation commit follows it. The live box is still
`8d2839d`.

### 0s.1 What the owner decided

1. **E — a layout per table, as reviewed data.** `layout: process | grid` on the
   `<!-- table -->` block. The seals comparison is a grid; the two process tables are cards. One
   renderer bent to fit three shapes was rejected.
2. **C3 — horizontal cards** for *Establishing a PGS group* and *SAOSO organic certification*: the
   step body, then its facets, then the fee. The merged Fee cell is a box under Steps 1–2 and
   Step 3's Fee a box under Step 3.
3. **Resources and Seals fold away** (`<details>`, closed by default) so the step body leads.
   *Use of seals* stays visible; if the cards are still too tall at UAT, fold it with the same
   element.
4. **The split is two stacked cards in column three.** SAOSO's direct route is an alternative
   path, not a fourth step: Path A (PGS) and Path B (direct), stacked with an `or`, dashed borders,
   and a `branch:` marker on the block. Path A points at Step 2 and repeats no fee.
5. **The seals comparison is a resizable spreadsheet**: frozen header and first column, one
   13.5 px type size, pointer + keyboard column resizing, compact toggle, reset, persisted widths.
6. **The short step titles stay** as reviewed data; `Step 1/2/3` alone is the fallback.

**Why:** two of the three tables are **processes**, not records — that is what the owner saw as
“flowchart-type content”. The artifacts are `d76_reader_table_fit.html` (the fit),
`d76b_reader_table_examples.html` (six display shapes; E chosen), `d76c_process_flow_variants.html`
(four process iterations) and `d76d_c3_and_the_split.html` (**the final**: C3, folded facets, the
split). The fit's 323-character figure was the page's **blank padding line**; the printed row ends
at **153–169**, and the pane is **52.5 rem**. The type inequality the owner noticed came from the
stacked phone view's 16 px serif heading — the rule is one size for every column, the step label
bold rather than larger.

### 0s.2 What was not done, deliberately

- **No parser field, no template branch, no JS, no CSS.** The reader is still the fixed grid from
  §12e. The implementation is `LANDSCAPE_TABLES_PRD` **§12f.3**, with acceptance criteria in
  **§12f.4** and traps in **§12f.5**.
- **`TABLE_BANDS`** and the corpus-level table-page guard are still open.
- **Step 7** (the UAT fee scenario, the backlog move, the §5.7 exclusion check) is untouched.

### 0s.3 The one command that still hurts

`scripts/build_corpus.py --force --doc landscape` replaces the review with the p4–8 column soup —
the generator has no table-block rule. The per-line guard fails loudly if it does; the command has
no other defence.

---
