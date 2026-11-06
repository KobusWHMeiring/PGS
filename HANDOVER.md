# Handover — Appendix 2 is a block, and the curated table path is gone

> ## START HERE — S5-b landed; S5-c (Appendix 7) is the next slice, and it needs a gutter
>
> **`INGESTION_ENGINE_PRD.md` §3.17 is what landed, and `INGESTION_ENGINE_S5_PLAN.md` §7 says how.**
> Appendix 2's **30 rows** are emitted from its three printed pages, with its seven printed dividers,
> and `APPENDIX_2_ROWS`, `TABLE_ROWS`, `TABLE_SECTIONS`, `rows_for`, `structure_for`, `chunks_for_rows`,
> `NO_CONDITION_LABEL`, `TableRow`, `TableSection`, `row_blocks` and `RowHeading` are **deleted**.
> `scripts/check_tables.py --doc saoso --rows 30,20` → `ok — 2 tables, 50 rows, 0 violations`.
>
> **Four declarations, each refused before it was declared.** `band: {76: 60, 77: 64, 78: 64}` (where
> the condition column starts, per printed page — the emitter slices each line into two streams, so a
> wrapped left cell no longer swallows its neighbour's words); the **hyphen** rule the harness already
> had (`cobalt-`/`sulphate`); `dividers:` (seven printed headings, written as `row-divider` and claimed
> by the emitter); `tails:` (the seaweed row's `(iii) fermentation.` is printed at the top of printed
> 77 — declared, verified as that page's *first* line, and recorded as a page marker **inside** the
> cell, which is what lets R3 judge each line against its own page). The 30 rows entered as **locators
> promoted from the owner's 2026-10-21 review** (`propose_tables.py --continue`), and the emitter
> re-verified every one; `test_a_continued_locator_is_a_run_of_the_pages_table_line` is the guard.
>
> **The curated rendering path went with the data.** The reader draws Appendix 2 through
> `_artefact_grid` now: `ReaderGridRow.dividers` render as `reader__grid-divider` rows, and the
> `silence:` label (`no condition printed`) sits in the 19 empty cells. Three regressions this caught:
> grid cells were not annotated with the reference index (a `See Section B – Appendix 6` link vanished),
> the silence label was attached to all 30 rows, and `Reader.table`/`passage.dividers`/`passage.note`
> became dead code and were removed.
>
> **Measured.** `build_corpus --doc saoso --force` → one section, `204 insertions(+), 104 deletions(-)`;
> `build_corpus --doc opp --force` leaves `opp.md` **byte for byte** unchanged. `check_tables` →
> `opp` 6, `landscape` 3+2+3, `saoso` 30+20: **6 tables, 64 rows, 0 violations**. Chunk count
> **340 → 341** (the header prose above the grid is a chunk again). Full suite **1776 passed / 1 skipped
> / 8 xfailed** (100.44 s, 135.24 s, 177.16 s and 223.31 s on four warm runs — quote a range, §3.17);
> `fast.sh --critical` **182 passed / 4 deselected in 18.29 s**. Four guards broken and watched red.
>
> **`scripts/verify.sh` still cannot be quoted from this tree** — step 1 fails on **another session's**
> `scripts/copy_deck.py` (32 KB, untouched). Steps 2–4 pass by hand: `manage.py check` clean,
> `makemigrations --check` "No changes detected", `lint-imports` `knowledge must never import core KEPT`.
>
> **Three defects the first real build found, all now hazards.** `build_corpus.build()` called
> `corpus_pages.pass_texts` on a module it never imported — no test calls `build()`, so the suite was
> green over a script that could not run (**§3.40**). The "is this table here at all?" pre-check said
> yes in `S8.1` (where `Farmyard manure, slurry and urine` is also printed), refused the table there
> and marked it attempted, so the artefact came out with 6a only (**§3.41**). R6's "the paper prints
> it once" was false for `South African specific` — printed three times (**§3.42**).
>
> **S5's remaining two, and each is a review.** *Appendix 7* (S5-c) needs `gutter: 1` (the arm's first
> column is the printed row number) and a cell that wraps **inside** a column with `Air,` beside it on
> the same printed line; Docling's grid is the evidence for the boundary, and the band is not that
> shape. *The landscape* (S5-d) needs its four declarations and a splice that does not rewrite the
> reviewer's front matter (pages 2–3 and 9, commit `8674d7a`). Plan §5 has the slices and their gates.
>
> **Do not re-run the arms and do not re-open the key.** **Do not delete a test** to make a count
> match: the Appendix 2 guards were *converted* to read the block, and `test_row_blocks.py` went only
> because `row_blocks` did (its losslessness claim is carried by
> `test_the_real_corpus_survives_the_layout_and_produces_lists`).
>
> **Housekeeping.** This working tree still carries **another session's uncommitted work**
> (`scripts/copy_deck.py`, `product/design/COPY_DECK.md`, `COPY_VOICE.md`, `REFERENCE_COPY_CORPUS.md`,
> `fetch_reference_copy.py`, and edits to the public templates and `core/services/_public.py`) — stage
> explicit paths, never `git add -A`. **Do not refresh the dev corpus** — `GEMINI_API_KEY` is in the
> shell but not in the repo `.env`, and a refresh without it writes 17 NULL vectors that report
> "already ingested" forever (`deploy/README.md` §4).

---

The landscape is closed (session `0z`): UAT re-signed against `c4c362e`, 6 PASS;
`LANDSCAPE_TABLES_PRD` in `Done/`; `TABLE_BANDS` and the corpus-level table-page guard carried into
D80 by name.

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4, context-budget, context-frame,
landscape-sign-off, chat-split, handover-truth-up, shapes-harness, docling-evaluation, vlm-arm,
re-score, arbitration, S5-a (Appendix 6a) and S5-b (Appendix 2) sessions
**Repo state:** `main` — **one commit from session `1r`** (S5-b), pushed. Everything before it is
pushed; `origin/main` was at `8563ba2` when this session started. The stale "three unpushed runs" note
this file carried twice is itself the example of why the next line is the only one that answers it.
**Let the command answer:** `git rev-list --count origin/main..HEAD`.
`main` and `feat/mvp1a-visit` (`../pgs-visit`, MVP 1a sub-plan A) are **separate lines** with no code
overlap; `HANDOVER.md` and `testing_hazards.md` are edited on both sides, so a merge needs one hand on
those two files.

**On this tree** (2026-11-05, session `1r`, after its commit): `python -m pytest -q --reuse-db` —
**1776 passed / 1 skipped / 8 xfailed in 100–223 s** on four warm runs (100.44, 135.24, 177.16, 223.31 s), run as
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify` (the gate defaults to 5432 and this box
serves 5433, `testing_hazards.md` §3.1). Quote cold *and* warm (§3.17), and this box is not idle —
session `1p` measured 240.27 s `--create-db` and 234.99 s warm on the same suite with 11 fewer tests.
`scripts/fast.sh --critical` **182 passed / 4 deselected in 18.29 s**. **`scripts/verify.sh` cannot be quoted green from this
working tree**: its first step fails on **another session's** `scripts/copy_deck.py` (32 KB); my own
files are all inside the cap, and steps 2–4 pass by hand — `manage.py check` clean,
`makemigrations --check` "No changes detected", `lint-imports` `knowledge must never import core KEPT`,
then the suite above.

**Live:** `https://organicguarantee.africa` on the homtini VPS, deployed 2026-11-03 at **`06bb11a`**
(last read back from the box in session `1b`; `/health/` answered `{"status": "ok", ...}` on 2026-11-04,
but that body carries no commit, so **this file cannot see which commit is serving** — verify on the box
with `git rev-parse --short HEAD`). It serves a **current** corpus (401 chunks). **A deploy is owed** for
everything after `06bb11a` — sessions `1f`–`1r`, i.e. both S5 tables and the reader's grid. It moves
the corpus by **one chunk** (Appendix 2's header prose: SAOSO 340 → 341, so the live total 401 → 402).
The dev box has no SSH key, so the operator runs
`sudo bash /home/carbonplanner/apps/pgs/deploy/deploy.sh` and reads the `/health/` body back — the
script verifies origin's tip on the box before it pulls. Its `deploy.sh` on disk is the pre-`3c2c39d`
one, and **the §3.27 window is self-closing, not debt**: that script still `pull`s origin's tip,
but it already carries the re-exec, so the next deploy re-runs the fixed script, which verifies
origin's tip afresh and fast-forwards to *that* — before the backup and the first migration
(`deploy/README.md`: "re-executes itself if the pull changed it"). No manual fix is owed.
**The dev box is NOT current — it is behind live**, and says so: `corpus_check` reports
`landscape` **drift**, and its 17 landscape chunks carry **0** labelled renditions against live's
8. Do not refresh it until `GEMINI_API_KEY` is in the dev `.env` (it holds only
`DJANGO_SECRET_KEY`), or the refresh writes 17 NULL vectors that then report "already ingested"
forever (`deploy/README.md` §4). Live is the reference DB.

## Session archive

History, verbatim, one file per session. **Read only the session a task sends you to.**
A new session writes its narrative to `product/docs/handover/SESSION_<tag>_<date>_<slug>.md`
and adds one line here; this file stays state.

- `1r` 2026-11-05 (session 25) — S5-b: Appendix 2 becomes a block, and the curated table path is gone
  — [`SESSION_1r_2026-11-05_appendix-2-becomes-a-block.md`](product/docs/handover/SESSION_1r_2026-11-05_appendix-2-becomes-a-block.md)
- `1q` 2026-11-05 (session 24) — S5-a: Appendix 6a becomes a block, and a body is the pass its block declares — [`SESSION_1q_2026-11-05_appendix-6a-becomes-a-block.md`](product/docs/handover/SESSION_1q_2026-11-05_appendix-6a-becomes-a-block.md)
- `1p` 2026-11-05 (session 23) — S3: the generator emits the table block, and the page supplies the characters — [`SESSION_1p_2026-11-05_s3-the-generator-writes-the-block.md`](product/docs/handover/SESSION_1p_2026-11-05_s3-the-generator-writes-the-block.md)
- `1o` 2026-11-05 (session 22) — the re-score moves an arm a shape, and a surface that stacked its evidence — [`SESSION_1o_2026-11-05_the-re-score-and-a-surface-that-stacked.md`](product/docs/handover/SESSION_1o_2026-11-05_the-re-score-and-a-surface-that-stacked.md)
- `1n` 2026-11-05 (session 21) — the verification surface, and 68 claims the owner has not judged — [`SESSION_1n_2026-11-05_the-verification-surface.md`](product/docs/handover/SESSION_1n_2026-11-05_the-verification-surface.md)
- `1h` 2026-11-04 (session 20) — three arms measured, and an answer key nobody checked — [`SESSION_1h_2026-11-04_three-arms-and-an-answer-key-nobody-checked.md`](product/docs/handover/SESSION_1h_2026-11-04_three-arms-and-an-answer-key-nobody-checked.md)
- `1g` 2026-11-04 (session 19) — Docling measured, and it does not pass; a Gemini key is not a GCP key (in `SESSION_1f…` §7–§8) — [`SESSION_1f_2026-11-03_the-harness-reads-the-table-and-the-count-stops-being-quoted.md`](product/docs/handover/SESSION_1f_2026-11-03_the-harness-reads-the-table-and-the-count-stops-being-quoted.md)
- `1f` 2026-11-03 (session 18) — the harness reads the table, and the count stops being quoted — [`SESSION_1f_2026-11-03_the-harness-reads-the-table-and-the-count-stops-being-quoted.md`](product/docs/handover/SESSION_1f_2026-11-03_the-harness-reads-the-table-and-the-count-stops-being-quoted.md)
- `1e` 2026-11-03 (session 17) — the eight shapes, and the two that have no test — [`SESSION_1e_2026-11-03_the-eight-shapes-and-the-two-with-no-test.md`](product/docs/handover/SESSION_1e_2026-11-03_the-eight-shapes-and-the-two-with-no-test.md)
- `1d` 2026-11-03 (session 16) — the state said what was not true, and the rows were cut — [`SESSION_1d_2026-11-03_the-state-said-what-was-not-true-and-t.md`](product/docs/handover/SESSION_1d_2026-11-03_the-state-said-what-was-not-true-and-t.md)
- `1c` 2026-11-03 (session 15) — the six remaining cuts, and every file is inside its cap — [`SESSION_1c_2026-11-03_the-six-remaining-cuts.md`](product/docs/handover/SESSION_1c_2026-11-03_the-six-remaining-cuts.md)
- `1b` 2026-11-03 (session 14) — deployed, and the deploy verified one commit and installed another — [`SESSION_1b_2026-11-03_deployed-and-the-deploy-verified-one-commit.md`](product/docs/handover/SESSION_1b_2026-11-03_deployed-and-the-deploy-verified-one-commit.md)
- `1a` 2026-11-03 (session 13) — five splits: the chat split lands, and `_chatbot.py` is 23 KB — [`SESSION_1a_2026-11-03_the-chat-split-lands-in-seven-modules.md`](product/docs/handover/SESSION_1a_2026-11-03_the-chat-split-lands-in-seven-modules.md)
- `0z` 2026-11-03 (session 12) — the landscape is signed, and "As above" is the paper's word — [`SESSION_0z_2026-11-03_the-landscape-is-signed-and-the-as-above.md`](product/docs/handover/SESSION_0z_2026-11-03_the-landscape-is-signed-and-the-as-above.md)
- `0y` 2026-11-02 (session 11) — slice 3: the context is a row and a column, both surfaces say so, and Scenario 8 is signed — [`SESSION_0y_2026-11-02_slice-3-the-context-is-a-row-and-a-column.md`](product/docs/handover/SESSION_0y_2026-11-02_slice-3-the-context-is-a-row-and-a-column.md)
- `0x` 2026-11-02 (session 10) — G11 answered, and two of its three slices landed — [`SESSION_0x_2026-11-02_g11-answered-and-two-slices-landed.md`](product/docs/handover/SESSION_0x_2026-11-02_g11-answered-and-two-slices-landed.md)
- `0w` 2026-11-02 (session 9) — the context balloon is the loop, not the handover — [`SESSION_0w_2026-11-02_the-context-balloon-is-the-loop-not-the-handover.md`](product/docs/handover/SESSION_0w_2026-11-02_the-context-balloon-is-the-loop-not-the-handover.md)
- `0v` 2026-11-02 (session 8) — the cost rule, P4's printed scale, two decision pages, and the handover becomes state — [`SESSION_0v_2026-11-02_the-cost-rule-p4-two-decisions-and-the-handover-b.md`](product/docs/handover/SESSION_0v_2026-11-02_the-cost-rule-p4-two-decisions-and-the-handover-b.md)
- `0u` 2026-11-01 (session 7) — the cost rule, the OPP's printed scale, and the refusal located — [`SESSION_0u_2026-11-01_the-cost-rule-the-opp-s-printed-scale-and-th.md`](product/docs/handover/SESSION_0u_2026-11-01_the-cost-rule-the-opp-s-printed-scale-and-th.md)
- `0t` 2026-11-01 (session 6) — the two shapes are built, and one number the design did not decide — [`SESSION_0t_2026-11-01_the-two-shapes-are-built-and-one-number-the.md`](product/docs/handover/SESSION_0t_2026-11-01_the-two-shapes-are-built-and-one-number-the.md)
- `0s` 2026-10-31 (session 5) — the display model settled: C3, the split, the spreadsheet — [`SESSION_0s_2026-10-31_the-display-model-settled-c3-the-split-the-s.md`](product/docs/handover/SESSION_0s_2026-10-31_the-display-model-settled-c3-the-split-the-s.md)
- `0r` 2026-10-31 — step 6: the reader draws the printed grid, and the fit was measured wrong — [`SESSION_0r_2026-10-31_step-6-the-reader-draws-the-printed-grid-and.md`](product/docs/handover/SESSION_0r_2026-10-31_step-6-the-reader-draws-the-printed-grid-and.md)
- `0q` 2026-10-30 (session 4) — step 5: the front matter, and four probes that were zero — [`SESSION_0q_2026-10-30_step-5-the-front-matter-and-four-probes-that.md`](product/docs/handover/SESSION_0q_2026-10-30_step-5-the-front-matter-and-four-probes-that.md)
- `0p` 2026-10-30 (session 3) — the landscape is a reviewed artefact, and the false headings are gone — [`SESSION_0p_2026-10-30_the-landscape-is-a-reviewed-artefact-and-the.md`](product/docs/handover/SESSION_0p_2026-10-30_the-landscape-is-a-reviewed-artefact-and-the.md)
- `0o` 2026-10-30 (session 2) — the two preconditions for step 2, and a corruption in the review path — [`SESSION_0o_2026-10-30_the-two-preconditions-for-step-2-and-a-corru.md`](product/docs/handover/SESSION_0o_2026-10-30_the-two-preconditions-for-step-2-and-a-corru.md)
- `0n` 2026-10-30 — the table block landed, and step 1 is mechanism only — [`SESSION_0n_2026-10-30_the-table-block-landed-and-step-1-is-mechani.md`](product/docs/handover/SESSION_0n_2026-10-30_the-table-block-landed-and-step-1-is-mechani.md)
- `0m` 2026-10-29/30 — the backlog gets a public page, and it is six sentences, not a mirror — [`SESSION_0m_2026-10-29_the-backlog-gets-a-public-page-and-it-is-six.md`](product/docs/handover/SESSION_0m_2026-10-29_the-backlog-gets-a-public-page-and-it-is-six.md)
- `0l` 2026-10-30 — session close: deployed, verified, and a clean slate for the table block — [`SESSION_0l_2026-10-30_session-close-deployed-verified-and-a-clean.md`](product/docs/handover/SESSION_0l_2026-10-30_session-close-deployed-verified-and-a-clean.md)
- `0k` 2026-10-30 — the baseline got measured, the whole price got published, and the tree got committed — [`SESSION_0k_2026-10-30_the-baseline-got-measured-the-whole-price-go.md`](product/docs/handover/SESSION_0k_2026-10-30_the-baseline-got-measured-the-whole-price-go.md)
- `0j` 2026-10-29 — the landscape's tables are decided; retrieval gets a brief for the instrument it lacks — [`SESSION_0j_2026-10-29_the-landscape-s-tables-are-decided-retrieval.md`](product/docs/handover/SESSION_0j_2026-10-29_the-landscape-s-tables-are-decided-retrieval.md)
- `0i` 2026-10-28 — the corpus can say whether it is current, and the ingest fails closed — [`SESSION_0i_2026-10-28_the-corpus-can-say-whether-it-is-current-and.md`](product/docs/handover/SESSION_0i_2026-10-28_the-corpus-can-say-whether-it-is-current-and.md)
- `0a` 2026-10-23 — `/ask/` became a board of answer pages, and citations became clickable — [`SESSION_0a_2026-10-23_ask-became-a-board-of-answer-pages-and-citat.md`](product/docs/handover/SESSION_0a_2026-10-23_ask-became-a-board-of-answer-pages-and-citat.md)
- `0b` 2026-10-27 — the concordance is decided and planned; nothing is built — [`SESSION_0b_2026-10-27_the-concordance-is-decided-and-planned-nothi.md`](product/docs/handover/SESSION_0b_2026-10-27_the-concordance-is-decided-and-planned-nothi.md)
- `0c` 2026-10-27 — the concordance is built; the reader is the document's tree — [`SESSION_0c_2026-10-27_the-concordance-is-built-the-reader-is-the-d.md`](product/docs/handover/SESSION_0c_2026-10-27_the-concordance-is-built-the-reader-is-the-d.md)
- `0d` 2026-10-27 — a passage is laid out as the document prints it — [`SESSION_0d_2026-10-27_a-passage-is-laid-out-as-the-document-prints.md`](product/docs/handover/SESSION_0d_2026-10-27_a-passage-is-laid-out-as-the-document-prints.md)
- `0e` 2026-10-27 — the reader is refined; what is left is judged, not built — [`SESSION_0e_2026-10-27_the-reader-is-refined-what-is-left-is-judged.md`](product/docs/handover/SESSION_0e_2026-10-27_the-reader-is-refined-what-is-left-is-judged.md)
- `0f` 2026-10-27 — the corpus keeps its glyphs: `-enc UTF-8`, and the U+FFFD mystery is closed — [`SESSION_0f_2026-10-27_the-corpus-keeps-its-glyphs-enc-utf-8-and-th.md`](product/docs/handover/SESSION_0f_2026-10-27_the-corpus-keeps-its-glyphs-enc-utf-8-and-th.md)
- `0g` 2026-10-27 — the reader is the document: a table, references that go somewhere, and a glossary — [`SESSION_0g_2026-10-27_the-reader-is-the-document-a-table-reference.md`](product/docs/handover/SESSION_0g_2026-10-27_the-reader-is-the-document-a-table-reference.md)
- `0h` 2026-10-28 — SAOSO is a reviewed artefact, and three bugs the draft found — [`SESSION_0h_2026-10-28_saoso-is-a-reviewed-artefact-and-three-bugs.md`](product/docs/handover/SESSION_0h_2026-10-28_saoso-is-a-reviewed-artefact-and-three-bugs.md)
- `0` The one thing to know first — [`SESSION_0_undated_the-one-thing-to-know-first.md`](product/docs/handover/SESSION_0_undated_the-one-thing-to-know-first.md)
