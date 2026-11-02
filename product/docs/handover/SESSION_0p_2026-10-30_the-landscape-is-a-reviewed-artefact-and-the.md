<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0p. 2026-10-30 (session 3) — the landscape is a reviewed artefact, and the false headings are gone

**State: green, committed, and the dev box's landscape is current.** `fast.sh` **1407 passed / 1
skipped in 78 s** (warm) and `verify.sh` **1421 passed / 1 skipped in 92.6 s** (`--create-db`, 5433).
Code at `7e67492`; this documentation commit follows. The live box is still `8d2839d` (see the top).

### 0p.1 Steps 2–4 landed together, because a partial artefact cannot be ingested

`knowledge/corpus/landscape.md` carries **PDF 4–8** as three `<!-- table -->` blocks — 8 rows:
`ESTABLISHING A PGS GROUP` (Step 1–3, p4–5), `PGS SEALS AND THEIR USE` (2 seal rows), `SAOSO
ORGANIC CERTIFICATION` (Step 1–2 and the direct third-party route on p8). `CORPUS_DOCUMENTS["landscape"]`
declares it, so ingest reads the review; `corpus_check` says `landscape current 11 / 11`.

**The three false headings are gone, and with them the reviewed titles.** `R500` is a fee cell,
`PGS SA.` and `SAOSO` are seal captions. `REVIEWED_BRANCH_TITLES` is now **empty** — the two
landscape entries renamed branches that no longer exist — and the document has its three printed
branches. `ESTABLISHING A PGS GROUP` holds all three steps as one branch (proved in
`test_concordance.py`).

**The measured count is 11, not the predicted 11/12, because the composition is different:** 8
rows + 3 prose blocks (p4 lead-in, p6 trailing paragraphs, p7 lead-in). The PRD's 11 was 8 rows +
3 front-matter passages, plus the lead-in as a 12th — the front matter is step 5, so it is simply not
in the count yet. The number is asserted as measured (`test_corpus_landscape.py`), and will rise
when step 5 lands.

### 0p.2 Three defects the review found, all proved red

1. **A table section with no lead-in produced a heading-only chunk.** `PGS SEALS AND THEIR USE`
   opens straight into its rows; `_prose_chunks` chunked the pre-cell gap as the heading alone. It
   was retrievable, citable, and said nothing. Fixed in `knowledge/tables.py`; reverting it makes
   the count 11 → 12 and fails both the count and the heading-only guard.
2. **`row_chunk`'s em-dash label was becoming a branch.** `heading_path` is `ESTABLISHING A PGS
   GROUP — Step 1`, and `_branch_key` split only on ` > `, so the concordance would have shown eight
   branches. `_branch_of` strips the row label; no printed heading in the four governed documents
   contains an em dash. Proved red.
3. **The eval set named a locator the fix deletes.** `uat-saoso-logo` expected `pgs-sa`; it now
   names `saoso-organic-certification-step-2`. `test_every_locator_resolves_against_the_ingested_corpus`
   is what caught it — the gate, not a review.

Also worth knowing: **the Fee column is one merged box** in `ESTABLISHING A PGS GROUP`. `-table`
renders `Annual membership fee … R500` level with `Step 2`, and the paper prints no row rule there,
so the cell cannot be split. It is filed under **Step 1**, where it starts, and the table's legend
says so — which is what makes the reader's fee question answerable from one chunk. The audit accepts
the verbatim sentence through `test_the_landscape_fee_is_quotable_from_its_reviewed_row`.

### 0p.3 D72.7's one re-ingest, measured on the dev box

`--force` re-ingest from the artefact: **8 → 11 chunks**, all embedded. **0 evidence links were
dropped** — no message had ever cited a landscape chunk on this box. `relink_evidence --apply`:
**0 relinked / 66 already linked / 30 same-locator-different-text / 0 no-longer-has**; the 30 are
the pre-existing bpp/saoso drift (that box was built from their PDFs). Totals: **388 chunks, 0
unembedded**. **bpp and saoso still report `drift` on dev**, which is out of this slice.

### 0p.4 What is still open from the PRD, and the one command that will hurt

- **`TABLE_BANDS`** — the measured column offsets. A transposition *inside one printed row-line*
  is still unpinned. It belongs with the reader (step 6), which is the surface that measures columns.
- **The corpus-level table-page guard** — needs a cross-document definition of “table-shaped”; only
  the landscape's pages are curated so far.
- **Front matter (p1–3) and the colophon (p9)** — step 5, the next act.
- **The printed-grid reader** — step 6; and the **UAT scenario + backlog move** — step 7.

**`scripts/build_corpus.py --force --doc landscape` destroys the review.** The generator has no
rule that emits a `<!-- table -->` block, and `CORPUS_EDITS` is a text substitution, so `--force`
would write the p4–8 column soup over the artefact. The per-line guard fails immediately if it does,
but nothing stops the command. Regeneration of a table artefact is a separate piece of work
(`TABLES_AS_DATA_PRD`).

---
