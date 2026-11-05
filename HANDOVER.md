# Handover — D82 answered as a composite, and a judgement surface taught us to put both sides on screen

> ## START HERE — S2 is closed: the arms were each best at a different job
>
> **`INGESTION_ENGINE_PRD.md` §3.14 is the decision (2026-11-05, session `1o`): D82 is not "which
> extractor".** The owner's call — *"we take our best options from each"* — is now the PRD's answer:
> **Layout Parser v1.6-pro for structure** (8/8 tables found; the only arm that reads the 1,112-character
> cell end to end), **the page's own text layer for characters** (every extractor misreads something: 43
> cells the Layout Parser cannot confirm, Docling's `bov ine`, the VLM's `70°C`), **Docling for Appendix
> 7's four columns** (its grid was right all along, and it finds no table on the landscape's merged
> cells), **the VLM `lines` form as a cheap proposer**, and **S4's harness for the verdict**. No
> credential buys the semantic half, which is why the union stops at **5 of 8** whatever is spent.
>
> **What S2 measured and what it cost.** Six measurements (§3.5–§3.9) across Docling 2.146.0, two VLMs ×
> three prompt forms, and Document AI's Form and Layout parsers; **$0.55 of model spend**, one GCP
> credential on the owner's own project (ADC — nothing in the repo), and the two API arms' raw answers
> cached, so the re-score after the key was corrected cost **nothing**. The Layout Parser's structure is
> 60–85 s/page on a 135-page corpus: **one-off, ~2.5 h, never in the edit loop** (requirement 10). Time
> was never the axis; unconfirmed cells and human correction are.
>
> **The key is signed and settled, and the review changed an arm's score.** 68 of 68 claims reviewed
> (§3.11, D85), **one amended** (`long_cell.cell.0.0` starts with the printed `Step 3`), and the re-score
> (§3.12) moved the **Layout Parser 2/8 → 3/8** with Docling byte-identical. The arbitration of the
> eleven remaining disputes (§3.13) then **kept** Appendix 6a's two-label header — so four readers
> merging it is a **tool failure**, not our defect, and §3.12's guess that it was ours is withdrawn.
> **Seven claims are unjudged and no longer gate anything**; S5 reviews those two shapes through the
> harness, with the page beside the transcription.
>
> **The lesson that cost this session its last hour, and it is written down twice.** A judgement surface
> is a **comparison**: the shape-key review put the page *beside* the grid and 68 of 68 were judged with
> no "can't tell"; the arbitration surface *stacked* evidence above the question and showed only a
> shape's first page, and the owner's notes came back as *"I can't figure out what you need from me"* —
> four of eleven verdicts caused by layout, not by the paper. It is **hard rule 9** in
> `pgs-presenting-uat`, and `product/design/uat/arbitrate_shapes.html` is now side-by-side with the
> full-size page one click away.
>
> **What is next is S3 and S5, not more evaluation.** S3 emits `<!-- table … -->` blocks from the
> composite and records the extraction mode on the artefact; S5 re-reviews Appendix 6a (20 rows) and
> Appendix 7 through the harness and deletes their bespoke handling. `scripts/fast.sh --critical` is the
> after-edit check, `scripts/verify.sh` the gate.
>
> **Instruments, all committed, none a dependency.** `scripts/eval_extractors.py` (Docling),
> `scripts/eval_openrouter.py` + `scripts/table_reads.py` (VLM), `scripts/eval_documentai.py` (REST +
> ADC), `scripts/shape_review.py` (the signed key's surface), `scripts/shape_arbitration.py` +
> `shape_disputes.py` (the disputes and what each arm said), `scripts/shape_review_signoff.py`
> (`--from` for a full review, `--amend` for one claim). 44 tests across the tooling, guards broken and
> watched red; 8 browser tests drive the two surfaces.
>
> **Two hazards to inherit.** *An evidence file's clip is not the read* — the arm JSONs keep four sampled
> rows and clip cells at 200 characters, so a probe reading them as the read accuses arms of defects
> they do not have (`testing_hazards.md` §3.31). And *read the response before believing the score*: the
> Layout Parser returns a block hierarchy with no `document.text`, and reading it like the Form Parser
> scored it 0 of 8 on every page — our bug, not the tool's.
>
> **Do not refresh the dev corpus casually.** `corpus_check` here reports `landscape` **drift** and its
> 17 chunks carry **0** labelled renditions against live's 8, so dev is behind live. The repo `.env`
> holds only `DJANGO_SECRET_KEY`, but **this shell holds `GEMINI_API_KEY`**, so a refresh *from an agent
> shell* would embed for real — and a refresh without a working key writes **17 NULL vectors that then
> report "already ingested" forever** (`deploy/README.md` §4). Live is the reference DB, not this box.
>
> **Do not run `scripts/build_corpus.py --force` on a document with a table block** — it refuses before
> writing; the only way past is `--discard-tables`, and then the review is yours to retype.
> **"Corpus is current" does not mean "rebuilt"** — drift compares the artefact's hash and the chunk
> count, not the derived text (`testing_hazards.md` §3.24). After a chunker or parser change,
> `ingest_standard --doc <x> --force` then `relink_evidence --apply`.
>
> **Two housekeeping notes for the next session.** This working tree carries **another session's
> uncommitted work** (`scripts/copy_deck.py`, `product/design/COPY_DECK.md`, `COPY_VOICE.md`,
> `REFERENCE_COPY_CORPUS.md`, `fetch_reference_copy.py`, and edits to the public templates) — commit
> paths explicitly, never `git add -A`. And `scripts/copy_deck.py` is **31 KB**, which fails
> `scripts/context.py --check` on this tree (not on any commit — a clean checkout of HEAD reports 0
> breaches); splitting it is that session's job.

The landscape is closed (session `0z`): UAT re-signed against `c4c362e`, 6 PASS;
`LANDSCAPE_TABLES_PRD` in `Done/`; `TABLE_BANDS` and the corpus-level table-page guard carried into
D80 by name.

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4, context-budget, context-frame,
landscape-sign-off, chat-split, handover-truth-up, shapes-harness, docling-evaluation, vlm-arm,
re-score, and arbitration sessions
**Repo state:** `main` — **unpushed**, and this file will not tell you how many: sessions `1h`, `1n`,
and `1o` are three unpushed runs (`1h`'s five commits: the OpenRouter arm, §3.8's correction, the
Docling re-run, the D82 page, the Document AI arm; `1n`'s eight: the verification surface, its docs, the
browser test, the count correction, the unclaimed-cell wording, the signed review, the `Step 3`
amendment and re-sign, and the D83→D85 reconciliation; `1o`'s three: the re-score with its evidence and
§3.12, the arbitration instrument with its browser tests, and the first pass with §3.13–§3.14).
**Let the command answer:** `git rev-list --count origin/main..HEAD`. Everything before `1h` is pushed.
`main` and `feat/mvp1a-visit` (`../pgs-visit`, MVP 1a sub-plan A) are **separate unpushed lines** with no
code overlap; `HANDOVER.md` and `testing_hazards.md` are edited on both sides, so a merge needs one hand
on those two files.

**On this tree** (2026-11-05, session `1o`, after the last commit): `python -m pytest -q --create-db`
— the gate's own pytest step — **1756 passed / 1 skipped / 8 xfailed in 139.13 s**, run as
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify` (the gate defaults to 5432 and this box
serves 5433, `testing_hazards.md` §3.1). The same command measured **79.37 s** a few runs earlier with
1750 tests on an idle box — quote cold *and* warm (§3.17). `scripts/fast.sh --critical` **172 passed /
4 deselected in 12.45 s**. **`scripts/verify.sh` cannot be quoted green from this working tree**: its
first step fails on **another session's** `scripts/copy_deck.py` (31 KB); a clean checkout of HEAD
reports **0 breaches**, so the commits are shippable and the tree is not.

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
