# Handover — sub-plan A is five of eight and sub-plan B is complete; the Crops sheet is data

> ## START HERE — **A is 5 of 8, B is 4 of 4, and A8 is unblocked**
>
> **Worktree `../pgs-visit`, branch `feat/mvp1a-visit`** — deliberately separate from `main`, because
> a second agent is running D80's S2 (Docling) there. Nothing in this strand has touched `main`.
>
> **Landed:** **A1** (`243cedd`) `Member`, `Farm`, `FarmAlias`, `FarmCategory`, `FarmContact`,
> migration `0010`, 19 tests. **A2** (`4e86a81`) the OPP §VII committee roster, `0011`, 12 tests.
> **A3** (`a4b2e4b`) `Pledge`, `record_pledge`, `0012`, 30 tests. **A5** (`66977cb`) `TurnoverBand`,
> `AssessmentFee`, the OPP §2.3 scale as data, `declare_assessment_fee` and the gate, `0013`, 32 tests.
> **A6** (`5f64fd6`) `ConsentText`/`ConsentRecord`, `_application.py`, the four application steps and
> the summary, `0014`, 32 tests. **B1/B2/B4** (`36eedfe`) `AssessmentTemplate`, `validate_schema`, one
> live version per category, `load_template`, `0015`–`0016`, 49 tests. **B3** (`93a5cac`) the Crops
> template and its review copy, 27 tests. **D83** the pledge stays in the application. **D84** 1a
> sends no mail, and the interface says so. **Two seam cuts, both driven by the 30 KB cap:**
> `_core.py` → `_membership.py` (`ab42443`), `_membership.py` → `_fees.py` (`66977cb`).
>
> **Sub-plan B in one paragraph:** a questionnaire is **data**, so `core/templates_data/crops.v1.json`
> holds the FORM's 38 numbered questions (79 answerable sub-items), 37 verdicts, 9 printed child rows
> and 7 Sheet I §2 records. `validate_schema` returns *every* problem with its path;
> `load_template` validates, refuses to overwrite an existing version, and activates only on request;
> `activate_template` moves one flag and the **partial unique index** makes "two live templates for one
> category" impossible. Nothing starts an assessment yet — `assert_template_usable` is the guard C1/E
> calls (A5's pattern).
>
> **B3 corrected the plan three times, and the printed FORM won each time** (evidence in
> `test_crops_template.py`'s docstring, assertions that hold it, and `SELF_CHECK_PRD` §3.4/§4.6 +
> D71 amended in place): (1) the Crops template carries **eleven** D71 self-check markers, not twelve —
> C5's aggregation question is **FORM Sheet A**, so it is an own control in `SELF_CHECK_ITEMS`;
> (2) the sheet prints **nine** child rows, not thirteen (rows 30–31, 42, 64, 79, 122–123, 136, 213);
> (3) a "Question N" is a **container** whose `items` are the answerable lines, because the plan's own
> marker example is `crops.Q4.2`.
>
> **Read the template as a document, not as JSON:** `product/docs/templates/crops_v1_review.md` is
> generated from the shipped file by `scripts/crops_template_review.py`, one row per printed line in
> sheet order, and a test fails if the committed copy is stale. That is B3's "second pair of eyes".
>
> **What is next: A8 — the public self-check** (D71, `SELF_CHECK_PRD`, prototype
> `product/design/before_you_apply_prototype.html`, approved 2026-11-04 as a stepped wizard). It is
> unblocked on every count it needed: eleven markers in the frozen template, C5 beside them as an own
> control, and its only exit — the application flow — built in A6. **Then A7** (eligibility gates,
> which still needs the payment surface named in `todo.md`) and **A4**.
>
> **Three things are still the product owner's, none of them blocks A8:** the three roster ambiguities
> from `1i`; whether `APPLICANT` is the right word for an account that has not applied; and the two
> `[DECIDE]` markers in `SELF_CHECK_PRD` §11.6 (retention period, withdrawal address — the latter also
> blocked on publishing the administrator's contact details). **A fourth is now queued:** whether the
> FORM's V21 child should ask for a percentage instead of Yes/No (`todo.md`).
>
> **Corrections recorded rather than fixed quietly.** (1) The plan's own A1 fee test hardcoded a period
> that expired on 2026-03-01 — `testing_hazards.md` §1.35. (2) `git checkout <file>` is not a
> mutation-testing restore — §1.36. (3) A `CheckConstraint` containing `NULL IN (…)` **is satisfied** by
> Postgres — §1.37. (4) `FileField(storage=callable)` resolves the callable at import — §1.38. (5) A
> boundary test whose samples never land on the boundary cannot see the rule — §1.39. (6) A suite timed
> once is timed wrong: the same tree measured 152.70 s and 261.21 s forty minutes apart — §3.17, with
> both numbers on record. (7) **The commit count in this block was carried forward instead of
> measured** — `1m` said 18 and the true count was 19, `1n` said 19 and it was 22, this block first said
> 21 and it is 25 — so it now names the command that produces it.
>
> **D83's substance:** the pledge cannot move to account creation, because it attests to *"all the land
> for which I/we are applying"*. The account collects identity + farm name, nearest town, contact, and
> nothing declarative. **The land-history contradiction is three-way, not two** (SAOSO 4.2.3 and the
> OPP pledge both say 12/12/18; OPP §V alone says 18/12/12), so A3's `land_history_conflict` is
> `min_reading <= declared < max_reading` — the band where the documents actually disagree — and **not**
> a comparison against OPP §V. It is **stored**, where `is_paid_up` is derived.
>
> **A5's finding worth knowing before A8:** the OPP §2.3 table as printed has a hole — *"Below
> R 250,000"* then *"R 250,001 – R 500,000"* — so band bounds are stored half-open and the printed
> wording is the `label`. `AssessmentFee` snapshots the band, its label and the amount; it never
> re-reads the schedule. The guard is `assert_fees_paid_for_assessment(member, farm)` (membership first,
> then the fee): **C1's `confirm_visit()` calls it** — A5 did not pre-build `FarmVisit`.
>
> **A6's finding worth knowing before A8:** the self-check's account step (§11.5 screen 7) is the same
> account `create_application()` makes, so A8 should call that service rather than write its own — and
> it carries the three Q7 fields the check never asks. The check's ticks still must **not** become
> `FarmCategory` rows; they wait for A6's categories step.
>
> **The current purpose is a demo to PGS** (product owner, 2026-11-05): show the *shape* of the flow —
> the self-check, the application, the account — before the group's go-ahead. That changes the bar
> (make the flow real and honest, not production-complete) and does **not** change any rule below.

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
  of `781cf37`, **25 commits**: A1, A2, A3, A5, A6, B1–B4, D83, D84, Q8's draft consent, the approved
  prototype, two model-seam cuts, the doc closes.
Neither is merged and **nothing on this branch is pushed** — `git rev-list --count origin/main..HEAD`
prints `25` (measured, `git log --oneline 781cf37..HEAD | wc -l`) and
`git ls-remote --heads origin feat/mvp1a-visit` prints nothing. **Both worktrees
have rewritten the START HERE block, so a merge conflicts here by design: keep both strands' state,
do not pick one.**

**Start the next agent here, not in `pgs`:** the A and B sub-plans' code is only in `pgs-visit`. Run
everything from that worktree, note that it has no `.venv` (`testing_hazards.md` §3.31 — the gate's own
script picks `python3`, which has no `celery`; use `python` and the five steps in §5), and drop the
leftover test database before a `--create-db` run (`_scratch/a5/dropdb.py`, §3.15).

**On this tree** (2026-11-05, sessions `1j`–`1o`): the gate's five steps — not `scripts/verify.sh`
itself, which cannot start here (§3.31) — **green at 1883 passed / 1 skipped / 8 xfailed**, run with
`--create-db` and the test database dropped first, at **204.69 s** (the pre-B3 tree, same session, at
233.18 s). Two numbers from one day are not a benchmark: use `testcost profile --reps 2` for a claim
(§3.17).

**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **this branch is entirely
local** (`18` commits ahead of `origin/main`, no remote branch). That is the session-`1f` line
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
