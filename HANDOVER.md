# Handover — merged, migrated, seeded, copy deck landed: UI refinement is the next act

> ## START HERE — **the tree is shippable at `66bc6c1`; the next act is UI refinement**
>
> **The next act is UI refinement** (product owner, 2026-11-06, at `66bc6c1`): **page headers read
> too big, back buttons are missing where a flow needs them, and there is a list of basic UI
> improvements.** `Refinement/UI_REFINEMENT_PRD.md` stages it and holds **no design decision**: §3 is
> four questions only the owner can answer, §4 is the screenshot pass (375 / 768 / 1440) whose
> findings table must exist *before* any CSS, and §5 is the smaller act the owner asked for — **a
> short investigation into UI-refinement practice before a local `pgs-refining-ui` skill is written**
> (four `pgs-*` skills exist and none is about the browser). The demo to PGS/SAOSO is still the
> purpose and C1 still waits for the group. **Read `product/design/DESIGN.md` before changing a
> view** — §4 is where "too big" is decided, and Lora is deliberately *not* bold — and check
> `product/backlog/` with the local `pgs-reading-the-backlog` skill first, so a queued refinement is
> not invented again. The dev database is migrated and seeded, so every screen is judged in a browser.
>
> **What landed.** `feat/mvp1a-visit` (`22b2aab`, **36 commits**: MVP 1a A1–A8, B1–B4, D83, D84, Q8's
> draft consent) is merged into `main` (`06cb013`, D80/D82 and S5-a/b/c) at the merge commit above it.
> The conflict surface was measured from `bacaeeb` in a throwaway worktree and it held exactly:
> **three conflicts, and no migration collision** — `main` stopped at `0009`, the strand adds
> `0010`–`0018`, so the graph is linear and `git log --graph` has one side branch that is now closed.
> This is **one tree and one branch**: work in `../pgs` from here. `../pgs-visit` is merged and may be
> removed (`git worktree remove ../pgs-visit`) once this commit is verified green.
>
> **Both refs are pushed, and that was the first act, not the last.** The strand had **no upstream**
> (`22b2aab` was local-only, in a second worktree, with a second agent in the same repo) — so it was
> pushed to `origin/feat/mvp1a-visit` *before* the merge was attempted. A merge that goes wrong is
> now a `git reset`, not a lost month. `main` was already level with `origin/main`; the merge commit
> is pushed after the suite went green. **Let the command answer** which refs are current:
> `git rev-list --count origin/main..HEAD` (0 when pushed) and `git ls-remote --heads origin`.
>
> **The three conflicts, and the rule each was resolved by — not by taste.**
> - `HANDOVER.md` — both strands had rewritten this block, by design, because both are state files.
>   Neither side was right alone. This file is the merge: the corpus strand's position (S5-c, and what
>   is left of S5) and the application strand's position (A 8/8, B 4/4, C1 designed and held) in one
>   short block, with both session indexes as the union (50 files, 50 lines).
> - `product/docs/context/testing_hazards.md` — **the numbering collided in section 3**: `main` had
>   grown §3.31–§3.44 (ingestion, tables, the reader), and the strand had its own §3.31 (`verify.sh`
>   in a second worktree) and §3.32 (a scripted slice move). The strand said the rule in advance:
>   **main's numbers win**. Its two moved to **§3.45/§3.46**, each with one line saying what it was
>   called before the merge; its seven §1.35–§1.41 entries (main stops at §1.34) kept their numbers.
>   Counted after: **98 entries = 89 + 9**, none lost and none duplicated. Archived session docs were
>   **not** renumbered — they are history and say what they said.
> - `product/backlog/backlog.md` — **generated**, and the conflict was its timestamp line and nothing
>   else. Never merged by hand: `python product/backlog.py --write`. Then `python product/backlog.py`
>   reports **0 drift**, 46 To Do items preserved, and `todo.md` (auto-merged) still holds both
>   strands' items — `MISSING_FEE_SURFACE` and `C1_HELD_FOR_GROUP`.
>
> **The dev database is migrated and seeded, so the flow runs end to end and is ready to refine.**
> The three data acts landed on 2026-11-06: `migrate` (**0010–0018 applied**, 0 pending anywhere),
> `seed_deployment` (6 turnover bands · 15 committee terms · 3 consents created; 3 seals and 7
> categories updated in place, `is_active` untouched), `load_template
> core/templates_data/crops.v1.json --activate` → `created CROPS:v1` / **activated**. Counts now:
> **CROPS v1 active**, 2 active seals (*PGS Organic Certified*, *PGS Organic In-Conversion*), 7
> categories, 6 turnover bands, 15 committee terms, 3 consents, and **0 members / 0 farms / 0 prior
> certifications** — the next applicant is the first. A template that exists is **history**: an
> assessment freezes a copy of its schema, and `load_template` refuses an edit rather than applying
> it — a changed questionnaire is a new version. Before the migrations ran, the dev DB was dumped to
> `../pgs-db-backup-2026-11-06.dump` (1.7 MB; rollback is `pg_restore -c`).
>
> **Applying them exposed three things worth knowing before touching the flow.** *(a)* **There is no
> gate screen**: no view reads `is_paid_up` or eligibility, so the A5 unpaid refusal and the A7
> standing refusal are service rules with tests behind them and the flow ends at the summary's
> "Your part is done" — correct, and the surface `MISSING_FEE_SURFACE` is about. *(b)* **The dev
> corpus is one build behind** — `corpus_check` reports `bpp` current but `landscape`/`opp` drift and
> `saoso` **338 / 348** chunks, so the reader and `/ask/` show pre-S5-c text. Do **not** refresh it
> from a shell that is missing `GEMINI_API_KEY` in `.env`: 17 NULL vectors then report "already
> ingested" forever (`deploy/README.md` §4). *(c)* `/health/` answers **503** on a dev box because
> `celery_worker` is `error` while `db`, `redis` and `celery_broker` are `ok`; **nothing in a request
> path enqueues work** (only `core.tasks.heartbeat` does), so it does not affect a clickthrough.
>
> **Measured on this tree** (2026-11-06): `scripts/verify.sh` is **green** — context budgets
> **0 breaches**, `manage.py check` clean, `makemigrations --check` "No changes detected",
> `lint-imports` KEPT, and **2090 passed / 1 skipped / 8 xfailed in 321.27 s** — a *cold* run
> (`--create-db`, `DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify`). The warm number for
> the same tree is **76.57 s** (`python -m pytest -q --reuse-db`); quote cold and warm together and
> never one alone (§3.17). `scripts/fast.sh --critical` **187 passed / 4 deselected in 11.34 s** —
> five more than `main`'s 182, because the strand brought its own critical-lane tests with it.
>
> **The copy deck landed, and with it a latent gate break was found and fixed** (both pushed to
> `origin/main`). `1cb2667` — **527 strings** in `product/design/COPY_DECK.md`, **0 drift**, 0
> templates outside it, `copy_deck_selftest.py` **PASS**, and the first rewrite applied to
> `home.html` / `_key_facts.html` / `_why_join.html` / `_public.py`'s `home` `Page`. `copy_deck.py`
> was **split** (23 KB + `copy_deck_extract.py` 11 KB) to get under §II's 30 KB cap, which is what
> step 1 had been failing on. It also exposed a break that is **not** the deck's: `abb5a9a` —
> `tests/tools/test_new_document_ingest.py` genuinely needs a PDF reader (the ingest re-reads the
> printed TOC, D68 §7.5) and `verify.sh` poisons `PDFTOTEXT_BIN`, so those two tests were red **in
> the gate** from `665b1fb`; nobody saw it because step 1 stopped the run before pytest. **A gate
> that fails at step 1 is not evidence about steps 2–4** (§3.48). **A dev server is running on
> `127.0.0.1:8000`** (`_scratch/runserver.log`, `--noreload`) — it holds Python in memory, so
> **restart it after editing a `.py`**; templates are read per request (§3.23).
>
> **What is left of the application strand.** **C1 is designed and deliberately not built**, because
> two of its questions are about what the OPP *means*: **may submit refuse unanswered farmer
> questions, or is a blank something the visit records** (OPP §4.1(2) says the *completed*
> questionnaire reaches the team — what "completed" means is theirs), and **if a farmer unticks a
> category after answering, are those answers kept as history or withdrawn**. The design is in
> `MVP1A_PLAN.md`'s C1 section, parked in `todo.md::C1_HELD_FOR_GROUP`; nothing of it is in the tree.
> **What the demo can honestly show, in this order:** the public self-check (`/before-you-apply/`),
> register → consent → pledge → categories → turnover (A6), the fee scale (A5), and the two gates
> (A5's unpaid refusal, A7's standing refusal). **What it will do at the gate is refuse**: no surface
> records a membership fee or its payment, so every self-registration stays `APPLICANT` and unpaid
> and A7 refuses it by name — correct, and the first thing the group will ask about
> (`MISSING_FEE_SURFACE`, session `1q`). A4's prior-certification table is **empty** until C2 writes
> it, and 1a issues **no outcome, seal or certificate** (D33). Say so before the group assumes
> otherwise. **The current purpose is still a demo to PGS/SAOSO** (product owner, 2026-11-05): show
> the *shape* of the flow before the group's go-ahead — real and honest, not production-complete.
>
> **What is left of the corpus strand, and each is a review.** *Appendix 7's rows 7–25* — the paper
> prints **25 rows and a `NOTE` across printed 88–92**, the arm was sent one page, so rows 7–25 are
> still the paper's `-layout` prose (3 of the section's 11 chunks). Closing them is Appendix 2's act:
> a person reads the rows, `--continue` promotes them as locators, the emitter refuses what it cannot
> find. **No arm may be re-run.** *The landscape* (S5-d) — its four declarations (bullets, the merged
> fee box, the seal artwork, the page-break row) and a splice that does not rewrite the reviewer's
> front matter (pages 2–3 and 9, commit `8674d7a`). *Then S5-e/f* — the shape markers come off as each
> target passes (`column_major`'s page is now a block, but `read_table()` does not read the artefact
> yet), then the last of the bespoke path. `INGESTION_ENGINE_S5_PLAN.md` §5 has the slices and gates.
> **Do not re-run the arms and do not re-open the key**, and **do not delete a test** to make a count
> match — the ratchets were *moved*, with the measurement in the commit. SAOSO's chunk count is
> **348**, measured with `chunks_for_sections` and **not** by summing `chunks_for_parsed_section`,
> which undercounts every table-less section (**§3.43**).
>
> **The traps that still cost time, all with evidence in `testing_hazards.md`.**
> - **Line endings, measured in binary.** The model files in this checkout are **CRLF** while the test
>   files are LF, and `Path.read_text()` reports *zero* CRLF because it has already converted them —
>   so a multi-line mutation anchor is "not found" with the text visible in `grep` (**§1.41**). Read
>   and write with `newline=""`, count `\r` on binary reads, and check `git diff --numstat` before
>   believing a restore. `Path.write_text()` flips every ending in the file.
> - **Restore mutation files from `_scratch/` copies, never `git checkout <file>`** (**§1.36**) —
>   `git checkout` discards every uncommitted change in that file, including the feature whose guard
>   you are proving. Three harnesses: `_scratch/a8/mutate.py`, `a7`, `a4`.
> - **Any test asserting something about *now* derives its dates from `timezone.localdate()`**
>   (**§1.35**), never from a literal: a plan written in the past ships a test that fails in the
>   future, and the failure reads as a regression in code nobody touched.
> - **A `CheckConstraint` that evaluates to `NULL` is *satisfied* by Postgres** (**§1.37**) — the
>   nullable column, not an `isnull` in the predicate, is what makes it vanish; and a boundary test
>   whose samples never land on the boundary cannot see the rule (**§1.39**).
> - **A7's gate passes for nobody in a running instance**, and that is a test, not a bug
>   (`MISSING_FEE_SURFACE`). A `ChoiceField`'s default `Select` renders **nothing** when a template
>   iterates it (**§1.40**).
> - **`verify.sh | tail` reports success whatever the gate did** (**§3.15**), and a killed run leaves
>   the test database behind so every later run fails ~700 tests (**§3.16**, `_scratch/a5/dropdb.py`).
>   Run the gate's own `DATABASE_URL` (**§3.1**; it defaults to 5432 and this box serves 5433:
>   `postgres://pgs:pgs@localhost:5433/pgs_verify`).
>
> **Waiting on the product owner, none of it blocking the merge:** `todo.md::MISSING_FEE_SURFACE`
> (three options, session `1q`); **the two C1 questions above** (`todo.md::C1_HELD_FOR_GROUP`); the
> three roster ambiguities from `1i`; whether `APPLICANT` is the right word; the two `[DECIDE]`
> markers in `SELF_CHECK_PRD` §11.6 (retention period, withdrawal address) — **and the same retention
> answer for the two public consents**; whether the FORM's V21 child should ask for a percentage
> instead of Yes/No; five of the record "why" sentences that name no clause; and the `/ask/` refusal
> link that `SELF_CHECK_PRD` §4.3 asks for and A8 did not build.

---

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4, context-budget, context-frame, landscape-sign-off,
chat-split, handover-truth-up, shapes-harness, docling-evaluation, vlm-arm, re-score, arbitration,
S5-a (Appendix 6a), S5-b (Appendix 2), S5-c (Appendix 7), the MVP1a sub-plan A and B sessions, and
the merge session.
**Repo state:** `main` carries **one merge commit** whose second parent is `feat/mvp1a-visit`
(`22b2aab`, 36 commits); `origin/main` and `origin/feat/mvp1a-visit` both exist and both are pushed.
`../pgs-visit` is merged and removable. **A number in this file is always one commit behind — let the
command answer** (`git rev-list --count origin/main..HEAD`).
**Live:** `https://organicguarantee.africa` on the homtini VPS, deployed 2026-11-03 at **`06bb11a`**
(last read back from the box in session `1b`; `/health/` answered `{"status": "ok", ...}` on 2026-11-04,
but that body carries no commit, so **this file cannot see which commit is serving** — verify on the box
with `git rev-parse --short HEAD`). It serves a **current** corpus (401 chunks). **A deploy is owed** for
everything after `06bb11a` — sessions `1f`–`1s` and this merge, i.e. all three S5 tables, the reader's
grid, and sub-plans A and B. It moves the corpus by **seven chunks** (Appendix 7's section is 11 chunks
where the interleaved prose was 4: SAOSO 341 → 348, so the live total 401 → 408).
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
and adds one line here; this file stays state. **Tags `1n`–`1r` were used by both strands** — they
ran in parallel, so a repeated tag is two different sessions (the file name, not the tag, identifies
one). Where a tag repeats, the `main` line comes first.

- `1u` 2026-11-06 (session 29) — the copy deck lands, and the gate it was hiding: step 1 red stops
  every step after it — [`SESSION_1u_2026-11-06_the-copy-deck-lands-and-the-gate-it-uncovered.md`](product/docs/handover/SESSION_1u_2026-11-06_the-copy-deck-lands-and-the-gate-it-uncovered.md)
- `1t` 2026-11-06 (session 28, merge session) — the two strands become one tree: three conflicts, and each resolved by a rule rather than a taste — [`SESSION_1t_2026-11-06_the-merge-three-conflicts-and-two-strands.md`](product/docs/handover/SESSION_1t_2026-11-06_the-merge-three-conflicts-and-two-strands.md)
- `1s` 2026-11-06 (session 26) — S5-c: Appendix 7 becomes a grid, and the paper is five pages longer than the plan — [`SESSION_1s_2026-11-06_appendix-7-is-a-grid.md`](product/docs/handover/SESSION_1s_2026-11-06_appendix-7-is-a-grid.md)
- `1r` 2026-11-05 (session 25) — S5-b: Appendix 2 becomes a block, and the curated table path is gone — [`SESSION_1r_2026-11-05_appendix-2-becomes-a-block.md`](product/docs/handover/SESSION_1r_2026-11-05_appendix-2-becomes-a-block.md)
- `1r` 2026-11-05 (session 27, **`feat/mvp1a-visit` strand** — the tag namespace has diverged: `main` also uses `1n`–`1q` for other sessions, so a tag here is strand-local and nothing was renamed) — A4 lands, sub-plan A is 8 of 8, C1 is designed and held for PGS/SAOSO, and the denial rule is written twice — [`SESSION_1r_2026-11-05_the-last-brick-and-the-denial-rule-written-twice.md`](product/docs/handover/SESSION_1r_2026-11-05_the-last-brick-and-the-denial-rule-written-twice.md)
- `1q` 2026-11-05 (session 24) — S5-a: Appendix 6a becomes a block, and a body is the pass its block declares — [`SESSION_1q_2026-11-05_appendix-6a-becomes-a-block.md`](product/docs/handover/SESSION_1q_2026-11-05_appendix-6a-becomes-a-block.md)
- `1q` 2026-11-05 (session 26) — the gate that passes for nobody, and the warning that had to be a verdict — [`SESSION_1q_2026-11-05_the-gate-that-passes-for-nobody-and-the-warning-that-was-a-verdict.md`](product/docs/handover/SESSION_1q_2026-11-05_the-gate-that-passes-for-nobody-and-the-warning-that-was-a-verdict.md)
- `1p` 2026-11-05 (session 23) — S3: the generator emits the table block, and the page supplies the characters — [`SESSION_1p_2026-11-05_s3-the-generator-writes-the-block.md`](product/docs/handover/SESSION_1p_2026-11-05_s3-the-generator-writes-the-block.md)
- `1p` 2026-11-05 (session 25) — the self-check lands, and the browser finds the form that was not there — [`SESSION_1p_2026-11-05_the-self-check-lands-and-the-browser-finds-the-form-that-was-not-there.md`](product/docs/handover/SESSION_1p_2026-11-05_the-self-check-lands-and-the-browser-finds-the-form-that-was-not-there.md)
- `1o` 2026-11-05 (session 22) — the re-score moves an arm a shape, and a surface that stacked its evidence — [`SESSION_1o_2026-11-05_the-re-score-and-a-surface-that-stacked.md`](product/docs/handover/SESSION_1o_2026-11-05_the-re-score-and-a-surface-that-stacked.md)
- `1o` 2026-11-05 (session 24) — sub-plan B lands, and the printed FORM corrects the plan three times — [`SESSION_1o_2026-11-05_sub-plan-b-lands-and-the-printed-form-corrects-the-plan-three-times.md`](product/docs/handover/SESSION_1o_2026-11-05_sub-plan-b-lands-and-the-printed-form-corrects-the-plan-three-times.md)
- `1n` 2026-11-05 (session 21) — the verification surface, and 68 claims the owner has not judged — [`SESSION_1n_2026-11-05_the-verification-surface.md`](product/docs/handover/SESSION_1n_2026-11-05_the-verification-surface.md)
- `1n` 2026-11-05 (session 23) — the application flow walks, and the money stays with the group — [`SESSION_1n_2026-11-05_the-application-flow-walks-and-the-money-stays-with-the-group.md`](product/docs/handover/SESSION_1n_2026-11-05_the-application-flow-walks-and-the-money-stays-with-the-group.md)
- `1m` 2026-11-05 (session 22) — the consent drafted, the mail decision taken, and the worktree handed over — [`SESSION_1m_2026-11-05_the-consent-drafted-the-mail-decided-and-the-worktree-handed-over.md`](product/docs/handover/SESSION_1m_2026-11-05_the-consent-drafted-the-mail-decided-and-the-worktree-handed-over.md)
- `1k` 2026-11-05 (session 21) — the fee scale is data, the gate is a service, and my own tests were the weak part — [`SESSION_1k_2026-11-05_the-fee-scale-is-data-and-my-own-tests-were-the-weak-part.md`](product/docs/handover/SESSION_1k_2026-11-05_the-fee-scale-is-data-and-my-own-tests-were-the-weak-part.md)
- `1j` 2026-11-05 (session 20) — the pledge lands, and two guards that were green for the wrong reason — [`SESSION_1j_2026-11-05_the-pledge-lands-and-two-guards-that-were-green.md`](product/docs/handover/SESSION_1j_2026-11-05_the-pledge-lands-and-two-guards-that-were-green.md)
- `1i` 2026-11-04 (session 19) — the joining flow is designed before it is built — [`SESSION_1i_2026-11-04_the-joining-flow-designed-before-it-is-built.md`](product/docs/handover/SESSION_1i_2026-11-04_the-joining-flow-designed-before-it-is-built.md)
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
- `0h` 2026-10-28 — SAOSO is a reviewed artefact, and three bugs the draft found — [`SESSION_0h_2026-10-28_saoso-is-a-reviewed-artefact-and-three-bugs.md`](product/docs/handover/SESSION_0h_2026-10-28_saoso-is-a-reviewed-artefact-and-three-bugs.md)
- `0g` 2026-10-27 — the reader is the document: a table, references that go somewhere, and a glossary — [`SESSION_0g_2026-10-27_the-reader-is-the-document-a-table-reference.md`](product/docs/handover/SESSION_0g_2026-10-27_the-reader-is-the-document-a-table-reference.md)
- `0f` 2026-10-27 — the corpus keeps its glyphs: `-enc UTF-8`, and the U+FFFD mystery is closed — [`SESSION_0f_2026-10-27_the-corpus-keeps-its-glyphs-enc-utf-8-and-th.md`](product/docs/handover/SESSION_0f_2026-10-27_the-corpus-keeps-its-glyphs-enc-utf-8-and-th.md)
- `0e` 2026-10-27 — the reader is refined; what is left is judged, not built — [`SESSION_0e_2026-10-27_the-reader-is-refined-what-is-left-is-judged.md`](product/docs/handover/SESSION_0e_2026-10-27_the-reader-is-refined-what-is-left-is-judged.md)
- `0d` 2026-10-27 — a passage is laid out as the document prints it — [`SESSION_0d_2026-10-27_a-passage-is-laid-out-as-the-document-prints.md`](product/docs/handover/SESSION_0d_2026-10-27_a-passage-is-laid-out-as-the-document-prints.md)
- `0c` 2026-10-27 — the concordance is built; the reader is the document's tree — [`SESSION_0c_2026-10-27_the-concordance-is-built-the-reader-is-the-d.md`](product/docs/handover/SESSION_0c_2026-10-27_the-concordance-is-built-the-reader-is-the-d.md)
- `0b` 2026-10-27 — the concordance is decided and planned; nothing is built — [`SESSION_0b_2026-10-27_the-concordance-is-decided-and-planned-nothi.md`](product/docs/handover/SESSION_0b_2026-10-27_the-concordance-is-decided-and-planned-nothi.md)
- `0a` 2026-10-23 — `/ask/` became a board of answer pages, and citations became clickable — [`SESSION_0a_2026-10-23_ask-became-a-board-of-answer-pages-and-citat.md`](product/docs/handover/SESSION_0a_2026-10-23_ask-became-a-board-of-answer-pages-and-citat.md)
- `0` The one thing to know first — [`SESSION_0_undated_the-one-thing-to-know-first.md`](product/docs/handover/SESSION_0_undated_the-one-thing-to-know-first.md)
