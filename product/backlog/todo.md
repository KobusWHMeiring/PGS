# To Do

Ideas that have no PRD file yet. `python product/backlog.py --write` pulls this into
the generated index's "To Do" section.

## Platform

- [ ] Set up `summarise.py` to generate `product/docs/state/` once there is code to summarise.
- [ ] `docker-compose.yml` + `Dockerfile` (MVP 0, sub-plan A).
- [ ] Decide the production host for the platform (the group currently has no server).
- [ ] Add a second physical backup copy — currently a single local external drive (R11, accepted gap).

## Decided, not yet queued (2026-11-02)

- [ ] **Context budget cuts 4.2–4.4** (`product/docs/context/CONTEXT_BUDGET.md`): a §18.3 row
      becomes a sentence + a link (14 rows are over 1.5 KB), split `core/services/_chatbot.py`
      (91 KB, 3× the §II cap) and `knowledge/corpus.py` (49 KB), then wire
      `scripts/context.py --check` into the gate. 4.1 (the HANDOVER split) and the
      `AGENTS.md` context-discipline block are done; `--check` reports 25 breaches today (11
      source files, 14 decision rows).
- [ ] **Ingestion engine generalisation** (**D80**: X2 now, X3 when a document demands it) —
      **has a PRD, and S2 is closed** (2026-11-05): `product/backlog/In Progress/INGESTION_ENGINE_PRD.md`.
      S0 is the **eight-shape fixture set**; S1 is `build_corpus.py` refusing to overwrite a reviewed
      `<!-- table -->` block; S4 is the **verification harness** (`knowledge/table_harness.py` +
      `scripts/check_tables.py`); S2 measured three arms against the eight shapes over six
      investigations and **answered D82 as a composite** (PRD §3.14) — Layout Parser for structure (8/8
      tables found), the page's own text layer for characters (R3), Docling for Appendix 7's four
      columns, the VLM `lines` form as a cheap proposer, the harness for the verdict. Nothing new is
      bought and no single arm wins. **What is left is three items, below.**
- [ ] **F3 — SAOSO outreach and the digital systems role** — `product/design/f3_saoso_outreach_and_role.html`
      (committed 2026-11-03, session `1e`): a review surface with two documents to approve (the SAOSO
      email, the role description) and three decisions they force. No PRD references it and no
      decision row exists yet; it is parked here deliberately rather than absorbed into D80.
- [x] **G11 build (D79 = E, decided 2026-11-02)** — show the table as structure, quote cells only,
      render the row's context from the artefact at cite time. **All three slices landed** (2026-11-02;
      session record `SESSION_0y_…`). **Slice 1:** the reserved seat is now filled in the vector arm's
      own order (it was filled from the fused head, which was truncated to `limit`, so a
      vector-only chunk could never be seated) and a heading-only chunk cannot consume one.
      Measured: a fee band is **reachable at all** for the
      first time (it appeared in no lexical ranking and ranked 15th fused) and
      `curated-unannounced-visit` went from not-found to rank 3; R@8 unchanged at 0.812, MRR
      0.387 → 0.385, and `curated-conversion-period` lost (rank 7 → not found) —
      `RETRIEVAL_EVAL_SPIKE.md` §8b. **Reachable is not reliable:** the band is the last of eight
      seats on one phrasing and out on two others, so **slice 2's unit is the table** — when a chunk
      belongs to a reviewed table its rows travel with it — not a bigger reservation. **Slice 2
      landed the same day:** `knowledge/table_context.py` gives a passage its reviewed table and
      `search_terms` appends its rows (after the passages, so no rank moves and `eval_retrieval` is
      unchanged); `build_prompt` renders the table once with its printed headings above one-cell-per-
      line rows; `Citation.row_label` carries the row's printed label and both citation templates
      render it as context. Both phrasings now answer with the document's own numbers — R900 renewal
      below R250 000, R1 500 initial — grounded, quoting single cells. **Slice 3 (the design pass)
      landed:** `Citation.column_label` names the printed column (only when exactly one cell holds the
      quote), the snapshot keeps row+column so the answer page stops disagreeing with the transcript,
      one legend per answer explains the dashed/solid pair, and the reader marks the cited row and
      cell. **Signed 2026-11-02:** the product owner judged UAT Scenario 8 — the dashed line reads as
      context, not a quotation — so D79 option E stands and the fallback to option A is not taken.
      Mechanism: `product/design/g11_option_e_explainer.html`; argument:
      `g11_row_labels_exploration.html`. The fee answer G10 opened now works.

## Product, deferred from the aimed spec

- [ ] Voice notes — recorder UI and Gemini transcription (`PGS_PLATFORM_SPEC.md` §17.2).
- [ ] "PGS pasture-raised" seal — seeded inactive; enable when the national working
      group publishes criteria (`Seal`, §4.3 / D11).
- [ ] Aggregation approval workflow — case-by-case sign-off, supplying-farm
      declarations, 6-month self-claim expiry, separation checks (§4.4 / D13).
- [ ] Aquaculture, Wine and Input Supplier Attestation — forms and workflow (§17.1).
- [ ] Complaints, hearings and discipline workflow (OPP §4.5–4.7).
- [ ] Membership fee *collection* (fees are tracked only; no gateway).

## Corpus and chat — found while building

- [ ] **`corpus_check` says nothing about a document with no artefact.** `knowledge/drift.py`
      short-circuits at `if artefact is None → NO_ARTEFACT; continue`, so `opp` gets no chunk count,
      no comparison, and no warning — and the same "no artefact" line is printed whether it holds
      30 chunks from an old parser or **zero**. Measured on the VPS 2026-10-30: the report said
      `no artefact` while the box's `opp` + `landscape` held **37** chunks against the dev box's
      **38**, built by whatever code ran on 2026-10-22 and never rebuilt since. **Half resolved
      2026-10-30:** the landscape now has a reviewed artefact and reports `current 11 / 11`, so the
      remaining case is `opp`. P4 gives it an artefact and the question disappears. Reopen if either
      document is ever edited from the PDF again.

- [ ] LLM classifier / alias routing for out-of-vocabulary subjects. **Deferred 2026-10-21**:
      it would not have fixed any of the round-3 failures. Reopen only when a suite question
      retrieves the *wrong section*; prefer a seeded alias table to a model call
      (`CHAT_ANSWER_COVERAGE_PRD.md` G5).
- [ ] Publish the administrator's email/phone on `/contact/` (currently `contact details to
      confirm` chips). Needed for the escalation path either way
      (`Refinement/ESCALATION_ANSWER_PATH_PRD.md`).
- [ ] **A way to start a new conversation on `/ask/`.** The thread is keyed by a cookie
      (`ChatSession.public_uuid`) and neither the panel nor the view offers a reset, so a
      visitor's only recourse is deleting cookies. Found 2026-10-22 while re-testing a refusal —
      which it made harder, because you cannot ask a fresh question without clearing them.
- [ ] **Set a retention schedule for public chat transcripts** (D59: kept indefinitely until
      then). Public questions can contain personal data about a third party; the group already has
      a POPIA retention schedule for assessment records. Revisit at MVP 2 registry work at the
      latest. Plan: `CORPUS_CANONICAL_FORMAT_PLAN.md` P2.8.
- [ ] **SAOSO's text loses glyphs, and `S1` ends with the next part's half-title.** 30 of 366 chunks
      hold U+FFFD where the paper prints `°`, `²`, `≥`, a bullet, an en dash or `ü`; one superscript
      `2` sits on its own line and splits the *Factory farming* sentence; the last `S1` chunk carries
      the `SECTION B` half-title of printed p.30. Found 2026-10-27 reading the definitions branch.
      This needs the revised artefact and `--force`, not a view change — full evidence and DoD in
      `BugFixes/saoso_text_glyphs_and_boundaries.md`.

## Ingestion engine — what S2 left (2026-11-05)

- [ ] **S3 — the generator emits `<!-- table … -->` blocks, and records the extraction mode on the
      artefact.** This is the slice that makes the composite real: the Layout Parser *proposes* the
      grid, the page's text layer supplies the characters, the harness refuses a block that breaks
      requirements 2–7. The harness's one unfinished datum is the **extraction mode** the cells came
      from (the landscape passes against `-table` and fails ten ways against `-layout`), which S3 must
      write onto every block it emits. Depends on nothing external: no credential, no new install.
      Evidence and the requirements it must satisfy: `INGESTION_ENGINE_PRD.md` §4 and §5.
- [ ] **S5 — re-review Appendix 6a (20 rows) and Appendix 7 (4 chunks) through the harness**, and
      delete their bespoke handling. These are the two live defects the PRD measures and the two the
      harness cannot see, because they are not table blocks at all. The review must be **side by side**
      — page beside transcription — which is now hard rule 9 in `pgs-presenting-uat`. 6a's header
      grouping is settled (the owner kept the key's two labels, 2026-11-05), so what is left there is
      association per row, not a decision.
- [ ] **R3's verdict wording — "our pass cannot order this page" is not "the model is wrong".**
      Both VLMs score **0 mismatches** on `page_break_row` and are demoted only because page 5's
      `-table` pass interleaves three columns on one printed line, so no cell's quotes can appear in
      read order. The instrument currently reports that as unverified characters. Found 2026-11-05
      (PRD §3.12/§3.14); cheap, and it changes how the scoreboard reads.
- [ ] **The arbitration page: finish its 7 open claims, or retire it.** `scripts/shape_arbitration.py`
      and `product/design/uat/arbitrate_shapes.html` are built and tested (10 cards, side-by-side, export
      → `shape_review_signoff.py --amend`). 61 of 68 claims stand as signed; **7 are unjudged and gate
      nothing** — two of them (6a's header, the merged fee box) were settled by other means. Keep it for
      the next time a claim is disputed, or delete it and regenerate if it drifts; what it must not be is
      a stale surface that looks like work in progress.

## Human gates — on the box
- [ ] **Deploy the corpus/D80 line to production** (owed since session `1f`; live is at `06bb11a`,
      read back in session `1b`). Sessions `1f`–`1o` are unpushed-or-pushed-but-not-deployed and carry
      **no migration and no runtime application change** — tests, fixtures, scripts, product docs and the
      `deploy.sh` verified-commit fix — so the deploy is low risk and changes nothing a user sees. The
      dev box has no SSH key: the operator runs
      `sudo bash /home/carbonplanner/apps/pgs/deploy/deploy.sh` and reads the `/health/` body plus
      `git rev-parse --short HEAD` on the box. **Do not refresh the dev corpus as part of it** — see
      `deploy/README.md` §4 and the next item.
- [ ] **Dev corpus refresh needs `GEMINI_API_KEY` in the dev `.env`** (it holds only `DJANGO_SECRET_KEY`).
      `corpus_check` reports `landscape` **drift** and its 17 chunks carry 0 labelled renditions against
      live's 8. A refresh without a working key writes **17 NULL vectors that then report "already
      ingested" forever** (`deploy/README.md` §4). Live is the reference DB, not the dev box.


- [ ] **Rehearse the backup restore on the VPS** (A9, R11). `docs/RUNBOOK.md` §2.1 has one row, from
      the dev box, and says of itself: *"It does **not** prove the VPS's drive, permissions, or
      `postgresql-client` version are correct."* Closed when §2.1 gains a **server-dated** row with
      13/13 tables and matching media checksums, run against the production database.
      Blocks: MVP 0 close-out (`MVP0_PLAN_V2.md` §4.1 item 3).

## Project — before we present to the committee

Project-level, not build-level: these need a meeting, not a commit, and none of them can happen
until the platform has been shown to the group. Logged here and linked from the plan so the repo
points at them instead of pretending they are imminent (D60).

- [ ] **Committee confirmation that the public surface makes no certification claim.**
      It is the second half of `MVP0_PLAN_V2.md` §4 item 7 and was moved out of the MVP 0 close-out by
      **D60**. `core/tests/test_claim_discipline.py` proves the *grep* and remains the standing
      guarantee — it cannot prove the committee read the site and agreed. Closed when a dated minute
      or email from the committee is recorded against §4 item 7.
- [ ] **Raise and fill the missing UAT seats** (D4, D23) — see the sign-off table in
      `tests/uat/mvp0_standards_and_public_site_uat.md`. The PGS administrator, committee reviewer and
      consumer member rows are empty. **Product and founder are two seats held by one person**, which
      is one voice, not two; D23 calls signing on the product owner's word alone *"self-certification"*.
      Scenarios **1, 3 and 8** are the ones it names. Two ways to close it: sit the three seats before
      the committee presentation, or record those three **provisional** and re-run at MVP 1 kickoff,
      which D23 explicitly permits. Leaving it unstated is the one option D23 closes off.

## Content

- [ ] **Second reader for the Crops template.** `ready/MVP1A_PLAN.md` Task B3 hand-authors 38 questions
      and 37 verdicts from the FORM workbook (D28), including six sub-verdict groups. The tests assert
      the counts and the schema; *whether the wording says what the FORM says* is a domain judgement no
      test can make. Recorded only as a gate row in `HANDOVER.md` §3 until now.
- [ ] Confirm plain-language wording for the membership-is-not-certification disclaimer.
- [ ] Afrikaans: decide whether to translate the full site or navigation and headings only.

## Test-suite cost — found while measuring (2026-10-28)

Measured across five repos from the session logs (819 pytest invocations, 8.1 h in pgs alone;
49 h in the fleet). Playbook: `product/docs/context/TEST_COST_PLAYBOOK.md`; plan and results:
`product/docs/context/TESTING_TIME_PLAN.md`. The first two stages shipped in this session; what
follows is the unfiled remainder.

- [ ] **Stage 3 — the value audit (blocks any test deletion).** Commit a `scripts/test_inventory.py`,
      write the hand-built invariant map (invariant → every witness → which is primary), and run a
      mutation pilot on `knowledge/retrieval.py` and `core/services/_chatbot*.py`. Until all three
      exist, **no test may be removed on the strength of coverage overlap**: 743 tests are sole
      witness of no line while asserting 743 distinct claims (`TESTING_TIME_PLAN.md` §3, §9).
- [ ] **`pytest tests/e2e` is not green at HEAD.** 43 passed, 34 errors when the directory is run
      as a whole; each file passes alone (37 passed for `test_public_site.py). The errors are
      `django.db.backends.postgresql InterfaceError` while setting `autocommit` under
      `live_server` — a dropped connection when several modules share one session. This is
      `testing_hazards.md` §3.11 again, and it means the 79 s the e2e run costs currently buys 34
      false alarms. It is also the reason `--reuse-db` is not yet the local default.
- [ ] **Fleet rollout, in the order the measurements justify** (`TEST_COST_PLAYBOOK.md` §7):
      **homitini** first — 225 `create_user(password=…)` sites with no hasher override and 29 h of
      pytest time, the largest single win anywhere in the fleet, and a one-file change with
      `pgs/settings_test.py` as the template; then **harvester** (bare `pytest` has three collection
      errors, so it has never run a full suite in 612 invocations); then **ngo-finance**
      (`testcost floor`/`profile` — do not guess); **homtini_store** is the control group, leave it.
- [ ] **Wire the ratchet.** `testcost profile --budget` needs a warm number measured on a quiet tree
      before it can gate CI — every figure taken on 2026-10-28 was contaminated by concurrent
      edits and a loaded box (`TESTING_TIME_PLAN.md` §9).
