# Handover — two strands in flight, and the application flow now walks end to end

> ## START HERE — **MVP 1a sub-plan A is 5 of 8 tasks in; the application walks and the money stays with the group**
>
> **Worktree `../pgs-visit`, branch `feat/mvp1a-visit`** — deliberately separate from `main`, because
> a second agent is running D80's S2 (Docling) there. Nothing in this strand has touched `main`.
>
> **Landed:** **A1** (`243cedd`) — `Member`, `Farm`, `FarmAlias`, `FarmCategory`, `FarmContact`,
> `MembershipFee`, migration `0010`, 19 tests. **A2** (`4e86a81`) — `CommitteePosition`,
> `CommitteeTerm`, the OPP §VII roster, migration `0011`, 12 tests. **A3** (`a4b2e4b`) — `Pledge`,
> `record_pledge`, migration `0012`, 30 tests. **A5** (`66977cb`) — `TurnoverBand`,
> `AssessmentFee`, migration `0013`, the OPP §2.3 scale seeded, `declare_assessment_fee` and the
> gate, 32 tests. **A6** (`5f64fd6`) — `ConsentText`, `ConsentRecord`, migration `0014`, the Q8 draft
> seeded, `core/services/_application.py`, four steps + a summary, 32 tests. **D83** (`0cc2112` and
> session `1i`'s close) — the pledge stays in the application. **D84** — 1a sends no mail, and the
> interface says so. **Two seam cuts, both driven by the 30 KB cap:** `_core.py` → `_membership.py`
> (`ab42443`), and `_membership.py` → `_fees.py` (`66977cb`, the OPP's own §II seam).
>
> **A6 in one paragraph, so nothing has to be re-derived:** self-register → the Q8 consent → the
> account (`Member{APPLICANT}`, `email_verified_at` null, CTA "Create an account") → **the pledge,
> after the account**, via A3's `record_pledge` → categories (a tick becomes a `FarmCategory` here,
> never in the self-check) → turnover, via A5's `declare_assessment_fee` → a summary that names the
> band, the assessment fee and the membership fee, and says who records the money. **Steps are
> derived from rows, never a session**, so `/apply/` resumes where a farmer got to; the order is
> enforced in `core.views._portal._step` by `assert_step_ready()`, not by URL shape.
>
> **Three refusals are A6's substance, and each is a place a friendlier shortcut would lie:**
> (1) **No consent, no account.** `ConsentText` is versioned, never edited, and the step posts the
> version it *rendered* — a form opened before the wording changed is refused, because a consent
> record naming the wrong text is worse than none. With no `ACCOUNT` row, the page says so and
> creates nothing. (2) **The applicant cannot pay.** No view writes a `MembershipFee`: the fee year is
> the group's (D39) and a `paid_on` from a self-registration would make
> `assert_fees_paid_for_assessment()` lie. `record_membership_fee()` and
> `record_membership_payment()` (APPLICANT → ACTIVE, never out of TERMINATED) are built, tested, and
> called by nothing yet — A5's pattern, waiting for A7/C1. (3) **The pledge is history:** a second
> POST redirects instead of appending a second attestation.
>
> **The Q8 draft is shown as a draft** (`SELF_CHECK_PRD` §11.6/§11.7): both `[DECIDE]` markers are
> rendered on the page a farmer reads, with a banner saying the group has not approved the wording,
> and an account *is* allowed under it — refusing every account until approval dead-ends the demo,
> and "must not ship while either marker remains" is a release rule. Approval is one data edit
> (`ConsentText.approved_at`), the banner disappears, nothing else changes. **The product owner
> should confirm this reading**; overruling it is one line.
>
> **Gate** (its five steps run with `python`; `scripts/verify.sh` cannot start here — §3.31): 0
> context breaches, `manage.py check` clean, `makemigrations --check` clean, `lint-imports` 1 kept /
> 0 broken, **1794 passed / 1 skipped / 8 xfailed in 152.70 s** `--create-db` (warm without it:
> 153.55 s), after dropping the leftover `test_pgs` (§3.15, `_scratch/a5/dropdb.py`).
>
> **What is next: B1 + B3** (the template's `self_check` markers), and **then A8** (the public
> self-check) — its only exit is this application flow, which now exists. **A7** (eligibility gates)
> can move after A8. **A4** likewise. **Do not build A8 before A6**; it is done.
>
> **A7 has a named prerequisite now:** in a running instance every applicant stays `APPLICANT` and
> unpaid, because nothing records a membership fee or its payment. The transition exists
> (`record_membership_payment`), the way to reach it does not. `todo.md` carries it as a decision
> (A7's own surface, or a one-screen administrator page), not a bug.
>
> **Approved by the product owner on 2026-11-04:** `product/design/before_you_apply_prototype.html`,
> the `/before-you-apply/` flow as a **stepped wizard** (5 question steps + result + account), built
> from the D71 wording ledger and driven with Playwright. It is the build target for **A8** and is
> labelled `DESIGN SPEC … Ready for implementation` at the top of the file.
>
> **Three things are still the product owner's, and none of them blocks A8's structure:** the three
> roster ambiguities from `1i` (first-name-only holders; whether Lilani Pretorius is a co-treasurer;
> Guy and Jacques unrecorded), whether `APPLICANT` is the right word for an account that has not
> applied, and the two `[DECIDE]` markers in §11.6 (retention period, withdrawal address — the latter
> is also blocked on publishing the administrator's contact details).
>
> **Corrections recorded rather than fixed quietly.** (1) The plan's own A1 fee test hardcoded a
> period that expired on 2026-03-01 — `testing_hazards.md` §1.35. (2) `git checkout <file>` is not a
> mutation-testing restore; it deleted a session's uncommitted model — §1.36. (3) A
> `CheckConstraint` containing `NULL IN (…)` **is satisfied** by Postgres, so A3's in-conversion rule
> passed the row it existed to refuse — §1.37. (4) `FileField(storage=callable)` resolves the
> callable at import, so a settings-derived storage cannot be redirected in a test and bakes a path
> into the migration — §1.38. (5) A boundary test whose samples never land on the boundary cannot see
> the rule — §1.39.
>
> **D83's substance:** the pledge cannot move to account creation, because it attests to *"all the
> land for which I/we are applying"*. The account collects identity + farm name, nearest town,
> contact, and nothing declarative. **The land-history contradiction is three-way, not two**
> (SAOSO 4.2.3 and the OPP pledge both say 12/12/18; OPP §V alone says 18/12/12), so A3's
> `land_history_conflict` is `min_reading <= declared < max_reading` — the band where the documents
> actually disagree — and **not** a comparison against OPP §V. Below the lower reading the two agree,
> and that is the visit's business, not the flag's (D31). `land_history_conflict` is **stored**, where
> `is_paid_up` is derived: a declaration does not roll over, and the flag records what the documents
> said the day it was signed.
>
> **A5's finding worth knowing before A8:** the OPP §2.3 table as printed has a hole — *"Below
> R 250,000"* then *"R 250,001 – R 500,000"* — so band bounds are stored half-open and the printed
> wording is the `label`. `AssessmentFee` snapshots the band, its label and the amount; it never
> re-reads the schedule. The guard is `assert_fees_paid_for_assessment(member, farm)` (membership
> first, then the fee): **C1's `confirm_visit()` calls it** — A5 did not pre-build `FarmVisit`.
>
> **A6's finding worth knowing before A8:** the self-check's account step (§11.5 screen 7) is the
> same account `create_application()` makes, so A8 should call that service rather than write its own
> — and it carries the three Q7 fields the check never asks. The check's ticks still must **not**
> become `FarmCategory` rows; they wait for A6's categories step, which is where they now belong.
>
> **The current purpose is a demo to PGS** (product owner, 2026-11-05): show the *shape* of the flow —
> the self-check, the application, the account — before the group's go-ahead. That changes the bar
> (make the flow real and honest, not production-complete) and does **not** change any rule below.

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4, context-budget, context-frame,
landscape-sign-off, chat-split, handover-truth-up, shapes-harness **and the MVP1a sub-plan A
sessions** (`1i` onward)
**Repo state:** **two worktrees, and the path matters.**
- `C:/Users/Kobus Meiring/Documents/Dev/pgs` — `main`, the sibling strand (D80 S2 / D82 as of
  `b27b9a6`). Still moving.
- `C:/Users/Kobus Meiring/Documents/Dev/pgs-visit` — **this one**: branch `feat/mvp1a-visit` on top
  of `781cf37`, **19 commits**: A1, A2, A3, A5, A6, D83, D84, Q8's draft consent, the approved
  prototype, two model-seam cuts, the doc closes.
Neither is merged and **nothing on this branch is pushed** — `git rev-list --count origin/main..HEAD`
prints `19` and `git ls-remote --heads origin feat/mvp1a-visit` prints nothing. **Both worktrees
have rewritten the START HERE block, so a merge conflicts here by design: keep both strands' state,
do not pick one.**

**Start the next agent here, not in `pgs`:** the A-sub-plan's code is only in `pgs-visit`. Run
everything from that worktree, note that it has no `.venv` (`testing_hazards.md` §3.31 — the gate's
own script picks `python3`, which has no `celery`; use `python` and the five steps in §5), and drop
the leftover test database before a `--create-db` run (`_scratch/a5/dropdb.py`, §3.15).

**On this tree** (2026-11-05, sessions `1j`–`1n`): the gate's five steps — not `scripts/verify.sh`
itself, which cannot start here (§3.31) — **green at 1794 passed / 1 skipped / 8 xfailed in
152.70 s**, run with `--create-db` and the test database dropped first. Warm without `--create-db`:
**153.55 s**. Quote cold *and* warm (§3.17) — never one number.

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
