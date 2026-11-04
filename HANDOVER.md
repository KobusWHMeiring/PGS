# Handover — Docling scored 0 of 8 as extracted, and the next arm needs no new account

> ## START HERE — S2 is measured for two arms and **both fail; the failures have moved, and that is the finding**
>
> **`INGESTION_ENGINE_PRD.md` is `In Progress`** and carries D80's decision as prose (X2 now, X3 when a
> document demands it) plus six slices. **S0, S1 and S4 landed. S2 is measured for two arms** (§3.5
> Docling, §3.7 the OpenRouter VLM).
>
> **Docling (§3.5): 0 of 8 shapes pass as extracted, 1 of 8 once row 0 is taken as the header, and 2 of
> 8 tables are not detected at all.** It marks no cell as a column header on any page, merges 6a's two
> header labels, splits p4's five columns into six, turns Appendix 2's dividers into rows, and loses
> p5's continuation row set. 163–330 s for the eight.
>
> **The OpenRouter VLM arm (§3.7, measured 2026-11-04): 2 of 8 at best — and that is 2 better than
> Docling, for $0.55.** Two models (`gemini-3.1-flash-lite`, `claude-sonnet-5.5`) × three prompt forms
> (`lines` verbatim, `anchors` first/last words, `indices` line numbers only) × the same eight shapes:
> **48 calls, 4–8× faster than Docling (5 s/shape).** It **finds every table (8/8)** and gets **header
> association right on 7–8 of 8** — the requirement Docling lost completely — and it **proposes
> dividers**, which no layout model returns (Appendix 2 passes outright in `anchors` form). What it
> cannot do is be trusted with **characters** or with **where a cell ends**: it re-wraps the 1,112-char
> cell, replicates the merged fee box into the row below, drops the label printed beside a seal, and
> shifts Appendix 7 one column right by treating the paper's row number as a column — **Docling's exact
> failure, from a different mechanism**. Up to sixteen times the price bought nothing: the expensive model
> is not better than the cheap one and no form dominates, so this is a finding about the task.
>
> **§3.8 corrects the first reading of this, and the correction is the finding.** The `indices` form
> scores 0 of 8 because a printed line **is a whole row**, and a row-structured pass **cannot be built
> from the committed text at all**: on Appendix 7 the gap between two columns collapses to one space
> when a cell overflows (`1 Aeration or oxygenation Air,`), so de-interleaving needs per-word geometry
> neither pass carries. But re-scoring the **cached** answers showed the biggest single defect was
> ours, not the tools': the paper prints a bare row number beside each row (`1`, `6b`) and **both arms
> read it as a leading column**, shifting every cell. Declare it (`drop_row_number_gutter`, narrow
> enough that a real first column is never touched) and **both arms pass Appendix 7** — Docling 2.146.0
> re-run on 2026-11-04 with the same instrument: `rows 7/7, cols 5/4`, `pass (needs row-number gutter)`.
>
> **So the honest scoreboard is: Docling 2/8, VLM 3/8 — and they pass different shapes.** Best arm is
> sonnet `lines` (numeric_row, column_major, artwork_cell); flash-lite `anchors` gets qualifier;
> Docling gets numeric_row and column_major. **Union of everything any arm passes: 4 of 8.** Never
> passed by anyone: **headerless_values** (one header printed across four lines), **long_cell** (a
> 1,112-character cell boundary), **empty_cells** (a merged fee box plus a label beside a seal), and
> **page_break_row** (right grid, characters unverified). Those four are **semantic**, not structural —
> judgements a human made in the fixtures.
>
> **What is next, in order: S3, then S5.** The extractor is no longer the load-bearing decision — a
> credential would have to beat a union of four, and the three it would still lose are the three no
> general extractor returns. **Document AI is now the least promising next spend** (§3.8 reverses
> D81's reasoning), and should be reconsidered only if S5 shows the semantic shapes are cheaper to buy
> than to review. The cheap interim is the `lines` form as a **proposer**: the model says which printed
> lines are a cell, the page supplies the characters, the S4 harness checks the result. **A Gemini API key is NOT a GCP credential** — verified 2026-11-04: 200 on
> `generativelanguage`, 401 on `documentai`. Cheaper options that need no account remain: a second
> local parser (Unstructured `hi_res`, Marker, MinerU, PaddleOCR) and **`anchors` re-scored against a
> row-structured pass**. Then **S3** (the generator emits blocks, and records the extraction mode), then
> **S5** (re-review Appendices 6a and 7 *through* the harness). **If no arm is wanted**, D is the honest
> fallback: hand-review those 24 chunks and write the generalisation debt down. **`read_table()` is
> still the seam.** The numbers a second run must beat are in
> `product/docs/evidence/2026-11-03_s2_docling_scores.json` and `…2026-11-04_s2b_openrouter_scores.json`,
> both regenerable in one command.
>
> **The audit was established, not inherited** (`SESSION_1e…` §1). Measured: **44** reviewed rows
> carrying column meaning across **three** documents (OPP §2.3 6, landscape 8, Appendix 2 30), plus
> **20** Appendix 6a rows that carry none, **ten** table-shape test modules (not four), Appendix 7's
> **4** interleaved chunks, and the landscape's longest cell at **1,112** characters.
>
> **S0** = `knowledge/tests/shape_fixtures.py` (eight `ShapeCase`s: page provenance, expectation,
> IR verdict, gap, `covered_by`; the page is **read** from the committed fixtures, never copied) and
> `test_ingestion_shapes.py` (28 green, **8 strict-xfail targets** calling a `read_table()` that does
> not exist yet, so the gap is counted every run and an `XPASS` fails the suite). **S1** = `build_corpus.py --force` **refuses** to drop a reviewed `<!-- table -->` block and names
> `--discard-tables` as the override (hazard §3.25).
>
> **S4** = `knowledge/table_harness.py` (requirements 2–7 as `check_table`/`check_document`, named
> `R2`–`R7` violations, no extractor, no PDF), `scripts/check_tables.py` (the gate: one document and
> its declared row counts per run) and 27 tests. **The four reviewed tables — 14 rows — pass**, there is
> **one mutation per requirement** the harness names, and two guards were broken and watched red. Two
> things it refuses to guess: the row count (`--rows`; undeclared is a violation) and **the extraction
> mode the cells came from** (the landscape passes against `-table` and fails 10 ways against `-layout`),
> which S3 must record on the artefact.
>
> **The F3 loose end is closed:** `product/design/f3_saoso_outreach_and_role.html` is committed with
> a `todo.md` line. It is a review surface (two documents to approve, three decisions), not D80's
> work and not a PRD.
>
> **Do not refresh the dev corpus casually.** `corpus_check` here reports `landscape` **drift** and its
> 17 chunks carry **0** labelled renditions against live's 8, so dev is behind live. The old blocker was
> the key, and it has half lifted: the repo `.env` holds only `DJANGO_SECRET_KEY`, but **this shell holds
> `GEMINI_API_KEY`** and `pgs/settings.py` reads it with `env("GEMINI_API_KEY")`, so a refresh *from an
> agent shell* would embed for real. The trap is unchanged and is the reason not to do it by accident: a
> refresh without a working key writes **17 NULL vectors that then report "already ingested" forever**
> (`deploy/README.md` §4). So: confirm the key is present, refresh deliberately, then run `corpus_check`
> — and know that **live is the reference DB**, not this box.
>
> **Do not run `scripts/build_corpus.py --force` on a document with a table block** — it now refuses
> before writing, so the accident that lost `opp.md`'s §2.3 review on 2026-11-01 cannot recur. Read
> the refusal: the only way past it is `--discard-tables`, and then the review is yours to retype.
>
> **"corpus is current" does not mean "rebuilt"** — drift compares the artefact's hash and the
> chunk count, not the derived text (`testing_hazards.md` §3.24). After a chunker or parser change,
> `ingest_standard --doc <x> --force` then `relink_evidence --apply`.

The landscape is closed (session `0z`): UAT re-signed against `c4c362e`, 6 PASS;
`LANDSCAPE_TABLES_PRD` in `Done/`; `TABLE_BANDS` and the corpus-level table-page guard carried into
D80 by name.

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4, context-budget, context-frame,
landscape-sign-off, chat-split, handover-truth-up, shapes-harness, docling-evaluation and
vlm-arm sessions
**Repo state:** `main` — **three commits ahead of `origin/main`**, all session `1h`'s: the OpenRouter
arm and its instrument; §3.8's correction; and the Docling re-run with the shared normalisation. Everything before it is pushed: the
licence commit, the chat-split follow-ups, the six test/generator cuts, the flake fix, `1c`'s close,
session `1d`'s (the truth-up, five row batches, the link guard, the gate wiring, the PRD close),
`1e`'s (the D80 PRD, S0's fixtures, S1's generator guard, F3), `1f`'s (the S4 harness, the gate
script, a corrected unpushed count), `1g`'s (D81, the explainer page, and Docling's measurement).
**Check it, do not quote it:** `git rev-list --count origin/main..HEAD` prints `3` on this tree, and
`0` once session `1h` is pushed.

**On this tree** (2026-11-04, session `1h`): `scripts/verify.sh` **green at 1695 passed /
1 skipped / 8 xfailed in 124.90 s** (a busy box; the same gate measured 59.16 s an hour earlier), run as
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify` (the gate defaults to 5432 and this box
serves 5433, `testing_hazards.md` §3.1). Quote cold *and* warm (§3.17) — the same gate measured
141.85 s on a busy box in session `1g` and 219.16 s cold in `1e`. `scripts/fast.sh` measured **1680
passed / 1 skipped / 15 deselected / 8 xfailed in 43.77 s**, and `--critical` **172 passed /
4 deselected in 9.83 s** (all three 2026-11-04).

**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **three commits to push** (session
`1h`'s): `git rev-list --count origin/main..HEAD` prints `3` (the number was wrong twice by being
quoted; let the command answer).
**Live:** `https://organicguarantee.africa` on the homtini VPS, deployed 2026-11-03 at **`06bb11a`**
(last read back from the box in session `1b`; `/health/` answered `{"status": "ok", ...}` on 2026-11-04,
but that body carries no commit, so **this file cannot see which commit is serving** — verify on the box
with `git rev-parse --short HEAD`). It serves a **current** corpus (401 chunks). **A deploy is owed** for
everything after `06bb11a` — sessions `1f`, `1g` and `1h`: the dev box has no SSH key, so the operator runs
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

- `1h` 2026-11-04 (session 20) — the VLM arm scores 2 of 8, and the failures move — [`SESSION_1h_2026-11-04_the-vlm-arm-scores-2-of-8-and-the-failures-move.md`](product/docs/handover/SESSION_1h_2026-11-04_the-vlm-arm-scores-2-of-8-and-the-failures-move.md)
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
