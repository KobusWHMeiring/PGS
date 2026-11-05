# Handover — the key was the variable: one amended claim, and an arm gains a shape

> ## START HERE — the re-score is done, and it moved the scoreboard, not the tools
>
> **`INGESTION_ENGINE_PRD.md` §3.12 is the state (2026-11-05, session `1o`).** The owner's review of
> the eight-shape key — 68 of 68 claims Yes, one claim amended — was signed in session `1n`; this
> session spent it. All three arms were re-scored against the signed key: the two API arms replayed
> from cache (no credential, no network, no spend), Docling re-run in its venv (**545 s**, because
> this arm keeps no response cache).
>
> **The result.** Document AI's Layout Parser **2/8 → 3/8**. Docling **identical — 0 of 8 shapes
> changed** (it returns no table on that page, so the amended cell is never consulted). Form Parser
> **1/8, same verdict, sharper reason** (it reads the cell as the bare label `Step 3`, so it now fails
> `contains` where it used to fail `starts`). Both VLM `lines` arms: passes unchanged, but `long_cell`
> goes from 1 mismatch to **0 mismatches with 4–11 cells our committed pass cannot confirm**. Evidence
> `2026-11-05_s2_rescore_{docling,documentai}.json` and `…_s2b_rescore_openrouter.json`; **6 of 72
> combos moved, all on `long_cell`, one line each.**
>
> **What it means.** `long_cell.cell.0.0` went from `starts="The group conducts…"` to
> `starts="Step 3", contains=…` — **one claim on the key, worth a whole shape for two arms.** The
> union of shapes any arm passes is **4 → 5 of 8**, and §3.8's closing claim ("the three it would
> still lose are the three no general extractor returns") was wrong: the long cell was our defect.
> **The scoreboard is a property of the key as much as of the arms**, with a measurement behind the
> suspicion §3.10 had.
>
> **The three shapes still passed by nobody are three different problems** (§3.12), and none of them
> is "no extractor can do this":
> * `headerless_values` — **probably our key.** The paper prints four header lines
>   (`Maximum number of animals per ha` / `Class or species`, then `Maximum number of animals per ha
>   equivalent` / `to 170 kg N/ha/year`). Our `columns` claim keeps both of column 1's lines and only
>   the second of column 0's, while our own anchor (`'Class or species to 170 kg N/ha/year'`) admits
>   the geometry. All four arms read column 0 with both lines. **Correcting it would take the Layout
>   Parser and sonnet `lines` to 4/8 each, and the union to 6 of 8.**
> * `empty_cells` — **genuinely the tools.** Checked against the landscape artefact's own legend: the
>   fee box spans Steps 1–2 and is filed under Step 1 (so `R500` belongs in cell 0,4), cell 1,3 is
>   exactly `Proud member of`, cell 1,4 is empty. Every arm splits the spanning box or duplicates the
>   two-line header.
> * `page_break_row` — **our committed pass, and R3's verdict.** Both VLMs score **0 mismatches** and
>   are demoted by quotes "out of printed order on page 5", because page 5's `-table` pass interleaves
>   three columns on one printed line (`its farmer members in the relevant   •  Farm visit checklist`).
>   No cell's quotes can appear in read order. That is §3.8's second finding biting again.
>
> **Next, in this order.** (1) The owner arbitrates the Appendix 6a header claim — the surface is
> built and committed: `product/design/uat/arbitrate_shapes.html` (`scripts/shape_arbitration.py`,
> `--check` guards it) presents **the 11 claims at least two arms contradict on shapes nobody passes**,
> each with the page, our own anchors, and every arm's own mismatch line. One verdict per claim; the
> export goes back through **`scripts/shape_review_signoff.py --amend`**, which refuses unless the
> fixture already says the text the reviewer judged. (2) **R3's verdict wording**: "our pass cannot
> order this page" must stop being scored as "the model's characters are unverified". (3) Re-score
> again (free), and then D82 has evidence under it. **Do not record "the VLM is the way" or "the
> Layout Parser is the way" on these numbers.**
>
> **Two hazards to inherit.** *An evidence file's clip is not the read*: the arm JSONs keep four
> sampled rows per shape and clip cells at 200 characters, so a probe that reads them as the read will
> accuse all five arms of a defect none has (`testing_hazards.md` §3.31 — go to the cache, and read
> claims from the `mismatches` lines). And *read the response before believing the score*: the Layout
> Parser returns a block hierarchy and no `document.text`, and reading it like the Form Parser scored
> it **0 of 8, "no table found" on every page** — our bug, not the tool's.
>
> **Time is not the decision axis, and here is the size of it.** The four governed documents are
> **143 pages** (SAOSO 100, BPP 12, OPP 14, landscape 9) — one extraction each, one-off, never in the
> 3-minute edit loop (requirement 10: the gate reads committed fixtures and imports no extractor). At
> measured rates that is ~2.5 h for the Layout Parser, ~2 h for Docling, ~25 min and a few dollars for
> the VLM. What *is* the axis: 43–59 cells per arm that our committed pass does not confirm, and
> whether a human must correct them.
>
> **The instruments are committed and are not dependencies:** `scripts/eval_extractors.py` (Docling),
> `scripts/eval_openrouter.py` + `scripts/table_reads.py` (VLM; three prompt forms, per-cell contiguity
> checks, declared normalisations, raw-response cache), `scripts/eval_documentai.py` (REST + ADC, reads
> both response shapes, retries, caches). 38 tests across the three, guards broken and watched red.
> The eight-shape key is `knowledge/tests/shape_fixtures.py`; the signature and its amendment are
> `knowledge/tests/shape_review.json`; the surface that produced them is
> `product/design/uat/shape_key_review.html`, generated by `scripts/shape_review.py` (`--check` fails
> when the committed file drifts from the key) and never hand-edited.
>
> **The story for a non-developer:** `product/design/d82_table_extraction_what_we_learned.html` — four
> investigations, the scoreboard, the options, and a §18.3 export for D85 (the key — **answered**) and
> D82 (which extractor — still open). It carries a dated 2026-11-05 update with the re-score in it.
> Nothing is written into the spec until the answers exist.
>
> **Do not refresh the dev corpus casually.** `corpus_check` here reports `landscape` **drift** and
> its 17 chunks carry **0** labelled renditions against live's 8, so dev is behind live. The repo
> `.env` holds only `DJANGO_SECRET_KEY`, but **this shell holds `GEMINI_API_KEY`** and
> `pgs/settings.py` reads it with `env("GEMINI_API_KEY")`, so a refresh *from an agent shell* would
> embed for real. The trap: a refresh without a working key writes **17 NULL vectors that then report
> "already ingested" forever** (`deploy/README.md` §4). Live is the reference DB, not this box.
>
> **Do not run `scripts/build_corpus.py --force` on a document with a table block** — it now refuses
> before writing, so the accident that lost `opp.md`'s §2.3 review on 2026-11-01 cannot recur. The
> only way past is `--discard-tables`, and then the review is yours to retype.
>
> **"Corpus is current" does not mean "rebuilt"** — drift compares the artefact's hash and the chunk
> count, not the derived text (`testing_hazards.md` §3.24). After a chunker or parser change,
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
**Repo state:** `main` — **thirteen commits ahead of `origin/main`**: session `1h`'s five (the
OpenRouter arm; §3.8's correction; the Docling re-run with the shared normalisation; the D82
explanation page; and the Document AI arm with §3.9–§3.10), then session `1n`'s eight (the verification
surface; its docs; a browser test for the JavaScript-off check; a count-correction commit; the
unclaimed-cell wording; **the signed review** with the two drawing fixes its notes exposed; **the
`Step 3` amendment with its re-sign**; and **the D83→D85 / `1i`→`1n` reconciliation** with the visit
worktree). Everything before `1h` is pushed: the
licence commit, the chat-split follow-ups, the six test/generator cuts, the flake fix, `1c`'s close,
session `1d`'s (the truth-up, five row batches, the link guard, the gate wiring, the PRD close),
`1e`'s (the D80 PRD, S0's fixtures, S1's generator guard, F3), `1f`'s (the S4 harness, the gate
script, a corrected unpushed count), `1g`'s (D81, the explainer page, and Docling's measurement).
**Check it, do not quote it:** `git rev-list --count origin/main..HEAD` prints `13` on this tree, and
`0` once sessions `1h` and `1n` are pushed — and note that `main` and `feat/mvp1a-visit` are separate unpushed lines.

**On this tree** (2026-11-05, session `1n`): `scripts/verify.sh` **green at 1727 passed /
1 skipped / 8 xfailed in 120.44 s**, run as
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify` (the gate defaults to 5432 and this box
serves 5433, `testing_hazards.md` §3.1). Quote cold *and* warm (§3.17) — the same gate measured
283.09 s here an hour earlier on a loaded box. `scripts/fast.sh` measured **1712 passed / 1 skipped /
15 deselected / 8 xfailed in 81.37 s**, and `--critical` **172 passed / 4 deselected in 10.36 s**.
One gate run in between reported `1 failed, 40 errors`; that was an orphan `idle in transaction`
backend, not the tree — §3.16 now says so.

**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **five commits to push** (session
`1h`'s): `git rev-list --count origin/main..HEAD` prints `5` (the number was wrong twice by being
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
