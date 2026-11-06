# Handover — sub-plan A is complete (8 of 8) and sub-plan B is complete (4 of 4)

> ## START HERE — **A is 8 of 8, B is 4 of 4, and the next move is a decision, not a task**
>
> **Worktree `../pgs-visit`, branch `feat/mvp1a-visit`** — deliberately separate from `main`, because
> a second agent runs D80's S2 (Docling) there. Nothing in this strand has touched `main`.
>
> **Landed since the last block:** **A4 — prior certification history** (`PriorCertification` in
> `core/models/_membership.py`, migration `0018`, `core/tests/test_prior_certification.py`, 11 tests,
> 4 mutations all caught in `_scratch/a4/mutate.py`). **That is the last task in sub-plan A.** Before
> it: A1 `Member`/`Farm` `0010` · A2 the OPP §VII roster `0011` · A3 the pledge `0012` · A5 the fee
> scale `0013` · A6 the application flow `0014` · B1/B2/B4 templates `0015`–`0016` · B3 the Crops
> template · A8 the public self-check `0017` · A7 the eligibility gates · D83 · D84 · Q8's draft
> consent.
>
> **A4 in one paragraph, for the next reader.** `PriorCertification(farm, kind ∈ PGS|THIRD_PARTY,
> body_name, certificate_ref, outcome ∈ GRANTED|DENIED, expires_on, denial_reason)` is FORM Sheet A
> (D30) and nothing more: §4.1's field list exactly, pinned by a test — no `declared_on`, no source
> document, no "verified" flag. The denial rule is written **twice on purpose** — a `save()` guard
> the caller sees and a `CheckConstraint` the database enforces — because `objects.create()` calls
> `save()` but never `full_clean()`, so a rule in `clean()` alone is green in a form and absent from
> every test. `denial_reason` is `NOT NULL, default=""` and the check reads `~Q(denial_reason="")`,
> because a nullable column makes the check read `NULL`, which Postgres *satisfies* (§1.37);
> `_scratch/a4/mutate.py` reverts the column to nullable to prove the test can fail. A `DENIED` row
> may not carry `expires_on` (a denial issued no certificate — D38's enterable-and-meaningless
> field), while a `GRANTED` row may omit it. The model sits beside `Farm` in `_membership.py`:
> **28.7 KB, 1.3 KB under the 30 KB cap**, so the next Farm-side model cuts a slice rather than
> growing the file. **Nothing writes the table in 1a**: C2's questionnaire renders Sheet A, and the
> visit and its report read the rows — and, unlike A7's fee surface, nothing is refused on a missing
> row, so the gap is one sentence and not a test.
>
> **What is next is a decision, not a task: merge `feat/mvp1a-visit` to `main`, or start C1.** Sub-plan
> A is 8 of 8 and B is 4 of 4, and none of it is merged or pushed. Both worktrees have rewritten this
> block, so the merge conflicts here by design — keep both strands' state, do not pick one. C1 is
> `confirm_visit()`, where A5's fee gate and A7's standing gate finally meet (**they are not chained
> yet**), and the likeliest place for `MISSING_FEE_SURFACE` to be answered.
>
> **The demo needs three data acts, and the dev database has fewer migrations than the last handover
> said:** `python manage.py showmigrations core` shows the last **applied** migration is **`0009`**,
> so **`0010`–`0018` are unapplied** and every A and B table is absent (this block read "at 0014"
> before; 0014 was never applied either). `migrate`, then `seed_deployment`, then
> `load_template core/templates_data/crops.v1.json --activate`. A4 did not move it: a model task does
> not migrate the dev database.
>
> **Seven traps, all with evidence in `testing_hazards.md`**
> - `scripts/verify.sh` cannot run here (§3.31): no `.venv` → it picks a `python3` without `celery`
>   and dies in step 2 looking like a broken tree. Run the five steps with `python`, and drop the
>   test DB first (§3.15, `_scratch/a5/dropdb.py`).
> - **Line endings, measured in binary.** The model files in this checkout are **CRLF** while the test
>   files are LF, and `Path.read_text()` reports *zero* CRLF because it has already converted them —
>   so a multi-line mutation anchor is "not found" with the text visible in `grep` (§1.41). Read and
>   write with `newline=""`, count `\r` on binary reads, and check `git diff --numstat` before
>   believing a restore. Session `1q`'s variant: `Path.write_text()` flips every ending in the file.
> - Restore mutation files from `_scratch/` copies, never `git checkout <file>` (§1.36). Three
>   harnesses now: `_scratch/a8/mutate.py` (the self-check), `a7` (eligibility) and `a4` (the denial
>   rule, which rebuilds the test database for the constraint mutation).
> - **A7's gate passes for nobody in a running instance**, and that is a test: no view records a
>   membership fee or its payment, so every self-registration stays `APPLICANT` and unpaid
>   (`_scratch/a7/mutate.py`, `MISSING_FEE_SURFACE`, session `1q`).
> - Any test asserting something about *now* derives its dates from `timezone.localdate()` (§1.35).
> - A `CheckConstraint` that evaluates to `NULL` is satisfied by Postgres (§1.37) — the nullable
>   column, not an `isnull` in the predicate, is what makes it vanish — and a boundary test whose
>   samples never land on the boundary cannot see the rule (§1.39).
> - A template that exists is **history**: an assessment freezes a copy of its schema. A changed
>   questionnaire is a new version, and `load_template` refuses an edit rather than applying it.
>
> **Waiting on the product owner, none of it blocking the merge or C1:** `todo.md::MISSING_FEE_SURFACE`
> (three options, described in session `1q`); the three roster ambiguities from `1i`; whether
> `APPLICANT` is the right word; the two `[DECIDE]` markers in `SELF_CHECK_PRD` §11.6 (retention
> period, withdrawal address) — **and the same retention answer for the two public consents**; whether
> the FORM's V21 child should ask for a percentage instead of Yes/No; five of the record "why"
> sentences that name no clause; and the `/ask/` refusal link that `SELF_CHECK_PRD` §4.3 asks for and
> A8 did not build.
>
> **The current purpose is still a demo to PGS** (product owner, 2026-11-05): show the *shape* of the
> flow — the self-check, the application, the account, the gate — before the group's go-ahead. That
> sets the bar (real and honest, not production-complete) and does **not** change any rule below.

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4, context-budget, context-frame,
landscape-sign-off, chat-split, handover-truth-up, shapes-harness **and the MVP1a sub-plan A and B
sessions** (`1i` onward)
**Repo state:** **two worktrees, and the path matters.**
- `C:/Users/Kobus Meiring/Documents/Dev/pgs` — `main`, the sibling strand (D80 S2 / D82 as of
  `b27b9a6`). Still moving.
- `C:/Users/Kobus Meiring/Documents/Dev/pgs-visit` — **this one**: branch `feat/mvp1a-visit` on top
  of `781cf37`, **33 commits before this session and 35 at this doc close** — a number in this
  file is always one commit behind, so measure it: `git log --oneline 781cf37..HEAD | wc -l`.
  Those are: A1, A2, A3, A4, A5, A6, A7, A8, B1–B4, D83, D84, Q8's
  draft consent, the approved prototype, four service-seam cuts, the doc closes.
Neither is merged and **nothing on this branch is pushed** — `git rev-list --count origin/main..HEAD`
prints the branch's own count (35 at this doc close — the number moves with every doc commit,
which is why the command is quoted beside it) and
`git ls-remote --heads origin feat/mvp1a-visit` prints nothing — that command prints **nothing**, which
is the fact that matters. **Both worktrees
have rewritten the START HERE block, so a merge conflicts here by design: keep both strands' state,
do not pick one.**

**Start the next agent here, not in `pgs`:** the A and B sub-plans' code is only in `pgs-visit`. Run
everything from that worktree, note that it has no `.venv` (`testing_hazards.md` §3.31 — the gate's own
script picks `python3`, which has no `celery`; use `python` and the five steps in §5), and drop the
leftover test database before a `--create-db` run (`_scratch/a5/dropdb.py`, §3.15).

**On this tree** (2026-11-05, session `1r`): the gate's five steps — not `scripts/verify.sh` itself,
which cannot start here (§3.31) — **1971 passed / 1 skipped / 8 xfailed**: **220 s cold** with the test
database dropped first, and **197 s warm** (`--reuse-db`), both on the final tree. The count is A7's
1960 plus A4's 11 tests. Every run is green, and the times are **not** last session's 117/118 s —
warm measured slower than cold on two of three attempts (197–311 s for one tree), because the sibling
worktree was active throughout. Quote both and name the contention, or claim nothing (§3.17); what
the numbers are evidence for is the count. `tests/e2e` is outside the gate (it needs a browser) and
was not run: A4 adds no template and no view.

**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **this branch is entirely
local** (`git rev-list --count origin/main..HEAD` prints the same count (29 at this doc close — the number
moves with every doc commit, which is why the command is quoted beside it), and `git ls-remote --heads origin
feat/mvp1a-visit` prints nothing). That is the session-`1f` line
rewritten for the current tree, because the old one said `0` and was true of `main`, not of this
worktree. Nothing needs pushing for the demo; pushing is a deliberate act because it makes the
branch visible to the sibling agent.
**Live:** `https://organicguarantee.africa` on the homtini VPS at **`06bb11a`**, deployed
2026-11-03 with a **current** corpus (401 chunks). **A deploy is owed** for everything after it
(the session `1f` push, and S4's commit on top): the dev box has no SSH key, so the operator runs
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

- `1r` 2026-11-05 (session 27, **`feat/mvp1a-visit` strand** — the tag namespace has diverged: `main` also uses `1n`–`1q` for other sessions, so a tag here is strand-local and nothing was renamed) — A4 lands, sub-plan A is 8 of 8, and the denial rule is written twice — [`SESSION_1r_2026-11-05_the-last-brick-and-the-denial-rule-written-twice.md`](product/docs/handover/SESSION_1r_2026-11-05_the-last-brick-and-the-denial-rule-written-twice.md)
- `1q` 2026-11-05 (session 26) — the gate that passes for nobody, and the warning that had to be a verdict — [`SESSION_1q_2026-11-05_the-gate-that-passes-for-nobody-and-the-warning-that-was-a-verdict.md`](product/docs/handover/SESSION_1q_2026-11-05_the-gate-that-passes-for-nobody-and-the-warning-that-was-a-verdict.md)
- `1p` 2026-11-05 (session 25) — the self-check lands, and the browser finds the form that was not there — [`SESSION_1p_2026-11-05_the-self-check-lands-and-the-browser-finds-the-form-that-was-not-there.md`](product/docs/handover/SESSION_1p_2026-11-05_the-self-check-lands-and-the-browser-finds-the-form-that-was-not-there.md)
- `1o` 2026-11-05 (session 24) — sub-plan B lands, and the printed FORM corrects the plan three times — [`SESSION_1o_2026-11-05_sub-plan-b-lands-and-the-printed-form-corrects-the-plan-three-times.md`](product/docs/handover/SESSION_1o_2026-11-05_sub-plan-b-lands-and-the-printed-form-corrects-the-plan-three-times.md)
- `1n` 2026-11-05 (session 23) — the application flow walks, and the money stays with the group — [`SESSION_1n_2026-11-05_the-application-flow-walks-and-the-money-stays-with-the-group.md`](product/docs/handover/SESSION_1n_2026-11-05_the-application-flow-walks-and-the-money-stays-with-the-group.md)
- `1m` 2026-11-05 (session 22) — the consent drafted, the mail decision taken, and the worktree handed over — [`SESSION_1m_2026-11-05_the-consent-drafted-the-mail-decided-and-the-worktree-handed-over.md`](product/docs/handover/SESSION_1m_2026-11-05_the-consent-drafted-the-mail-decided-and-the-worktree-handed-over.md)
- `1k` 2026-11-05 (session 21) — the fee scale is data, the gate is a service, and my own tests were the weak part — [`SESSION_1k_2026-11-05_the-fee-scale-is-data-and-my-own-tests-were-the-weak-part.md`](product/docs/handover/SESSION_1k_2026-11-05_the-fee-scale-is-data-and-my-own-tests-were-the-weak-part.md)
- `1j` 2026-11-05 (session 20) — the pledge lands, and two guards that were green for the wrong reason — [`SESSION_1j_2026-11-05_the-pledge-lands-and-two-guards-that-were-green.md`](product/docs/handover/SESSION_1j_2026-11-05_the-pledge-lands-and-two-guards-that-were-green.md)
- `1i` 2026-11-04 (session 19) — the joining flow is designed before it is built — [`SESSION_1i_2026-11-04_the-joining-flow-designed-before-it-is-built.md`](product/docs/handover/SESSION_1i_2026-11-04_the-joining-flow-designed-before-it-is-built.md)
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
