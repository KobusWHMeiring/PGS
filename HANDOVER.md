# Handover — Appendix 7 is a grid, and its table is five printed pages long

> ## START HERE — S5-c landed for printed 88; Appendix 7's rows 7–25 are the next review
>
> **`INGESTION_ENGINE_PRD.md` §3.18 is what landed, and `INGESTION_ENGINE_S5_PLAN.md` §8 says how.**
> Appendix 7's **printed-88 page** is a `<!-- table … -->` block of **7 rows and 4 columns**, emitted
> from the cached Layout Parser read of pdf 89 (`layout16pro__column_major.json`, appended with
> `--append`). `scripts/check_tables.py --doc saoso --rows 30,20,7` → `ok — 3 tables, 57 rows, 0
> violations`. `--doc opp --rows 6` and `--doc landscape --rows 3,2,3` unchanged.
>
> **Three declarations, each refused first.** `gutter: 1` — the arm's first column is the printed row
> number: resolved and claimed against the page, written as the row's **label** (`<!-- row: 6a -->`),
> never a column the reader draws. `band: {"88": [0, 4, 32, 60, 89]}` — S5-b's one boundary widened
> to **every column's left edge**, so the line is sliced between columns and `Air,` stops landing
> inside `using gaseous oxygen`; a single number on a wider table is refused. `locators: [{row,
> column, text}]` — the arm **transcribed** two cells (`\(70^{\circ}C\)` for the page's `70oC`, and
> `excipient:-` closed up), so the review says the page's spelling of that cell and the emitter still
> slices the page's characters. `knowledge/proposals/README.md` documents all three.
>
> **The measurement that corrects the plan.** The plan said Appendix 7 is 7 rows on printed 88. The
> paper prints **25 rows and a `NOTE` across printed 88–92**: printed 89 opens with the rest of 6b's
> condition and carries 7–9, printed 90 rows 9–15, printed 91 rows 15–20, printed 92 rows 20–25. The
> arm was sent one page, so **rows 7–25 are still the paper's `-layout` prose** (3 of the section's
> 11 chunks). Closing them is Appendix 2's act: a person reads the rows, `--continue` promotes them as
> locators, the emitter refuses what it cannot find. No arm may be re-run.
>
> **Measured.** `build_corpus --doc saoso --force` → one section, `134 insertions(+), 54 deletions(-)`;
> `--doc opp --force` leaves `opp.md` **byte for byte** unchanged. Chunk count **341 → 348** (Appendix
> 7's section 4 → 11), measured with `chunks_for_sections` — **not** by summing
> `chunks_for_parsed_section`, which returns a list holding a list and undercounts every table-less
> section (**§3.43**). Full suite **1790 passed / 1 skipped / 8 xfailed in 122–187 s**
> (`--reuse-db`, 5433; 187.27 s, 131.06 s and 121.87 s on three runs); `fast.sh --critical` **182 passed / 4 deselected in 19–33 s** (19.07 s, 32.74 s). Four guards broken and
> watched red: the band, the gutter, the locator, and each `_band`/`_gutter` refusal.
>
> **`scripts/verify.sh` still cannot be quoted from this tree** — step 1 fails on **another session's**
> `scripts/copy_deck.py` (32 KB, untouched). The full suite above is the gate's substance; steps 2–4
> (`manage.py check`, `makemigrations --check`, `lint-imports`) passed in the previous session and
> nothing here touches them.
>
> **Also new: `build_corpus --stdout` dies on this box's cp1252 console** on `≥`, leaving an empty
> redirect after a successful build — `PYTHONIOENCODING=utf-8` or `--force` (**§3.44**).
>
> **What is left of S5, and each is a review.** *Appendix 7's rows 7–25* — the continuation act above.
> *The landscape* (S5-d) — its four declarations (bullets, the merged fee box, the seal artwork, the
> page-break row) and a splice that does not rewrite the reviewer's front matter (pages 2–3 and 9,
> commit `8674d7a`). *Then S5-e/f* — the shape markers come off as each target passes (`column_major`'s
> page is now a block, but `read_table()` does not read the artefact yet), then the last of the
> bespoke path. Plan §5 has the slices and their gates.
>
> **Do not re-run the arms and do not re-open the key.** **Do not delete a test** to make a count
> match: the ratchets (`test_table_harness.py` 71 rows, `test_check_tables.py` `30,20,7`,
> `test_corpus_saoso.py`'s "another pass" set) were *moved*, with the measurement in the commit.
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
re-score, arbitration, S5-a (Appendix 6a), S5-b (Appendix 2) and S5-c (Appendix 7) sessions
**Repo state:** `main` — **two commits from session `1s`** (S5-c and its handover), pushed.
Everything before it is pushed; `origin/main` was at `8d5ccb3` when this session started. The stale
"three unpushed runs" note this file carried twice is itself the example of why the next line is the
only one that answers it. **Let the command answer:** `git rev-list --count origin/main..HEAD`.
**The merge, measured 2026-11-06** in a throwaway worktree (`git merge --no-commit --no-ff` from
`bacaeeb`): `feat/mvp1a-visit` (`../pgs-visit`, 98 files, MVP 1a sub-plan A) merges with **three
conflicts** — `HANDOVER.md`, `product/docs/context/testing_hazards.md` and
`product/backlog/backlog.md`. The third is a **generated** index: resolve it by re-running
`python product/backlog.py --write` after the merge, never by hand. `todo.md` auto-merges. The branch
is **not pushed** (`22b2aab` has no upstream), so push it or merge it locally. **Clean this tree
first:** it still holds another session's uncommitted edits, and one of them —
`core/services/_public.py` — is a file the visit branch also changes, so the merge is refused or those
edits are at risk until that session commits. After the merge: regenerate the index, run the full
suite (both sides add tests), then `verify.sh` — which will still fail step 1 until
`scripts/copy_deck.py` is under 30 KB.

**On this tree** (2026-11-06, session `1s`, after its commit): `python -m pytest -q --reuse-db` —
**1790 passed / 1 skipped / 8 xfailed in 121.87 s**, run as
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify` (the gate defaults to 5432 and this box
serves 5433, `testing_hazards.md` §3.1). Quote cold *and* warm (§3.17), and this box is not idle —
session `1p` measured 240.27 s `--create-db` and 234.99 s warm, and session `1r` measured 100–223 s on
four warm runs of the previous suite. `scripts/fast.sh --critical` **182 passed / 4 deselected in
32.74 s**. **`scripts/verify.sh` cannot be quoted green from this working tree**: its first step fails
on **another session's** `scripts/copy_deck.py` (32 KB); my own files are all inside the cap, and
steps 2–4 passed in session `1r` — `manage.py check` clean, `makemigrations --check` "No changes
detected", `lint-imports` `knowledge must never import core KEPT`.

**Live:** `https://organicguarantee.africa` on the homtini VPS, deployed 2026-11-03 at **`06bb11a`**
(last read back from the box in session `1b`; `/health/` answered `{"status": "ok", ...}` on 2026-11-04,
but that body carries no commit, so **this file cannot see which commit is serving** — verify on the box
with `git rev-parse --short HEAD`). It serves a **current** corpus (401 chunks). **A deploy is owed** for
everything after `06bb11a` — sessions `1f`–`1s`, i.e. all three S5 tables and the reader's grid. It
moves the corpus by **seven chunks** (Appendix 7's section is 11 chunks where the interleaved prose
was 4: SAOSO 341 → 348, so the live total 401 → 408).
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

- `1s` 2026-11-06 (session 26) — S5-c: Appendix 7 becomes a grid, and the paper is five pages longer than the plan — [`SESSION_1s_2026-11-06_appendix-7-is-a-grid.md`](product/docs/handover/SESSION_1s_2026-11-06_appendix-7-is-a-grid.md)
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
