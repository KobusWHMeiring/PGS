# Outeniqua PGS Product Backlog

> **Generated index** - do not edit by hand. Regenerate with `python product/backlog.py --write`.
> Generated: 2026-10-30 10:22

## Ready (up next)

- **MVP 1a Implementation Plan — In-Office Visit Flow** - `ready\MVP1A_PLAN.md` - Status: Ready
- **PRD: MVP 1a — In-Office Visit Flow** - `ready\MVP1A_PRD.md` - Status: Ready — all blocking decisions closed (spec §18.3 D27–D39, D45). **Prerequisite satisfied:** MVP 0 sub-plan A (A1–A10) landed 2026-10-19; the custom `User` is migrated and first. See `MVP1A_PLAN.md` §0.2.

## In Progress

- **The ask board, the answer page and the document reader — Implementation Plan** - `In Progress\ASK_SURFACE_PLAN.md` - Status: no status
- **PRD — The ask surface, second shape (board + answer pages)** - `In Progress\ASK_SURFACE_PRD.md` - Status: In Progress — shape decided (**D62**); follow-up stage 1 landed (**D63**);
- **PRD: Chat answer coverage — governing rules, table rows, and the gaps left** - `In Progress\CHAT_ANSWER_COVERAGE_PRD.md` - Status: In Progress — built 2026-10-21. **UAT signed 2026-10-21 (product owner):** Scenarios 1, 2, 3, 9 and 10 carry a result, with **G8** recorded as an open defect rather than absorbed (see §7). The remaining seats (PGS administrator, committee reviewer, consumer member) are unsigned.
- **Corpus Canonical Format — Implementation Plan** - `In Progress\CORPUS_CANONICAL_FORMAT_PLAN.md` - Status: In Progress — P0 settled (D55–D59); **P1 landed 2026-10-22**; **P2.1–P2.4 landed
- **PRD: A canonical corpus — reviewed text as data, extraction as a build step** - `In Progress\CORPUS_CANONICAL_FORMAT_PRD.md` - Status: In Progress — **SAOSO and BPP** are built, reviewed and are the text of record (`knowledge/corpus/saoso.md`, `bpp.md`); the OPP and landscape are not converted (P4, P5). **2026-10-28:** the ingest fails closed on a declared review (P7.1) and a deployment can tell whether its corpus is current (P2.1–P2.4).
- **Corpus Column-Aware Extraction — Implementation Plan** - `In Progress\CORPUS_COLUMN_EXTRACTION_PLAN.md` - Status: In Progress — C0–C9 landed 2026-10-20; **UAT Scenario 9 signed 2026-10-21** by the product owner.
- **PRD: Corpus column-aware extraction (all four governed documents)** - `In Progress\CORPUS_COLUMN_EXTRACTION_PRD.md` - Status: In Progress — built 2026-10-20; **UAT Scenario 9 signed 2026-10-21** by the product owner (the BPP-citation sub-check is recorded in the scenario's own text).
- **MVP 0 Implementation Plan (v2) — Standards Foundation & Public Shop Window** - `In Progress\MVP0_PLAN_V2.md` - Status: In Progress — sub-plans **A (A1–A10)**, **B (B1–B7)**, **C1 (C1a–C1e, public pages)**, **C2 (`/documents/`)**, **C4 (claim discipline)** and **D (D1–D5, grounded chatbot)** landed 2026-10-19; **C3 (bilingual shell)** deferred to a later slice (D44, no Afrikaans translator). **§4 audited 2026-10-22:** four of the seven DoD criteria are proved with evidence — `verify.sh` green at **804 tests** with `lint-imports` kept, four documents ingesting **340/340 embedded** and **0 duplicate `section_ref`s** — and the chatbot UAT is signed by the product owner (9 PASS · 1 N/A). **§4.1 is the close-out: two items left, both human gates** — the VPS restore rehearsal and the missing UAT seats. `f4e8907` deployed and the corpus was rebuilt with `--force` on 2026-10-22 (364 chunks, all embedded, `lexical_only=False`); committee confirmation of no-claims left for a project-level gate (**D60**). Nothing outside §4.1 is in scope for closing MVP 0. The §9 group-A gate closed as D27 (verdict polarity is template data) and D14–D15; D41–D44 were added while building B and C. C1's implementation notes and its open content decisions live in `product/design/C1_BUILD_PLAN.md` — #7 (the February fee deadline) was **withheld** while building C2.
- **PRD: MVP 0 — Standards Foundation & Public Shop Window** - `In Progress\MVP0_PRD.md` - Status: In Progress — sub-plans A (A1–A10), B (B1–B7), C1 (public site), C2 (`/documents/`) and C4 (claim discipline) landed 2026-10-19, and **D (D1–D5, chatbot)** landed with it, so every sub-plan except the deferred C3 is built. C3 (bilingual shell) is **deferred out of MVP 0** (spec D44 — no Afrikaans translator). §9 group A closed as D27 and D14–D15. Groups B and C stay open: they are MVP 1 and MVP 2 scope decisions, not MVP 0 blockers. **Closing MVP 0 is now an enumerated list, not a judgement call** — `MVP0_PLAN_V2.md` §4.1 (audited 2026-10-22): two engineering items, three human gates, one fix in flight. C1's open content decisions are listed in `product/design/C1_BUILD_PLAN.md` §6.
- **Implementation Plan — Building in the open (public board)** - `In Progress\PUBLIC_BOARD_PLAN.md` - Status: In Progress — B0–B6 landed 2026-10-29; **B7 (UAT) outstanding**, so the item stays
- **PRD: Building in the open — the public backlog board** - `In Progress\PUBLIC_BOARD_PRD.md` - Status: In Progress — built 2026-10-29 (D74a–c); every guard green, **UAT signature
- **PRD: UAT sign-off tooling — an HTML judgement surface with the data already loaded** - `In Progress\UAT_SIGN_OFF_TOOLING_PRD.md` - Status: **Slice 1 BUILT 2026-10-22** — moved to `In Progress/`. 768 tests green, artefact driven
- **Deployment: organicguarantee.africa on the homtini VPS** - `In Progress\VPS_DEPLOYMENT.md` - Status: In Progress — **redeploy path exercised 2026-10-22** (six runs; four deploy-blocking defects found and

## Refinement

- **PRD: The `/ask/` panel — the answered board, and a way to start over** - `Refinement\ASK_PANEL_REFINEMENTS_PRD.md` - Status: Refinement — the product owner's request, 2026-10-28, for the next session. Two items; the
- **PRD: Chat truthfulness — a refusal that names its cause, and an answer that claims no more than it cites** - `Refinement\CHAT_TRUTHFULNESS_PRD.md` - Status: Refinement — findings recorded 2026-10-27 from a four-turn live conversation. **5.1, 5.2, 5.3, 5.5, 5.7, 5.8, 5.9 and 5.10 landed the same day** (gate green at 920): every refusal in that conversation answers, the two GM-outcome turns state the rule instead of the verdict, G3 is closed, and a definition citation lands on the definition. Remaining: D-2's re-measure on the box, 5.6 (the follow-up window, needs S6), and the box sweeps.
- **PRD: The code atlas — one generated view of the application as built** - `Refinement\CODE_ATLAS_PRD.md` - Status: Refinement — a requirement from the product owner (2026-10-28); two decisions (§4) and a plan before it can be built. Supersedes the `CONVENTION.md` note that a state doc was "premature until there is code" — there is code now.
- **PRD: The escalation answer path — a refusal that can reach a person** - `Refinement\ESCALATION_ANSWER_PATH_PRD.md` - Status: Refinement — design needed, no code written
- **PRD: The certification landscape's tables — reviewed rows, and the rule for every other table** - `Refinement\LANDSCAPE_TABLES_PRD.md` - Status: Refinement — **all seven decisions taken 2026-10-29** (D72.1–D72.7, §6); nothing built.
- **Outeniqua PGS Digital Platform — Aimed Design Spec (Target State)** - `Refinement\PGS_PLATFORM_SPEC.md` - Status: Refinement — final PRD review completed 2026-10-18. Findings F1–F5 applied; decisions D14–D24 recorded in §18.3. MVP 0 is specified in `MVP0_PRD.md` and `MVP0_PLAN_V2.md`; it awaits one system brainstorm (`MVP0_PRD.md` §9) before implementation.
- **Refinement: The Regenerative Add-On — architecture findings, and what to decide before MVP 2** - `Refinement\REGENERATIVE_ADDON_ARCHITECTURE.md` - Status: Refinement — target shape agreed (A, §2); implementation paused until the standard itself exists. Three decisions are nonetheless time-sensitive (§8), because MVP 1a and MVP 2 will otherwise freeze them by accident.
- **Refinement: SAOSA multi-branch readiness — is this blueprint only for Outeniqua?** - `Refinement\SAOSA_MULTI_BRANCH_READINESS.md` - Status: Refinement — findings recorded 2026-10-19; no build approved. Awaits a product decision on deployment shape (§8) and the four leaks in §5.
- **PRD: The public self-check — "Before you apply"** - `Refinement\SELF_CHECK_PRD.md` - Status: Refinement — shape decided (**D71**, 2026-10-29). Every control and its wording judged by
- **PRD: Tables as reviewed data — so the reader can display any table without new code** - `Refinement\TABLES_AS_DATA_PRD.md` - Status: **Refinement** — **§7 Q1 answered 2026-10-29: option 2, the corpus artefact.

## On Hold

_none_

## Spikes

- **Spike: `0∥` — Offline capture on the assessor's real device** - `spike\OFFLINE_SPIKE_PRD.md` - Status: Spike — not started. Brief written from the spec; no code, no decision yet.
- **Spike: an instrument for retrieval quality — the eval set we do not have** - `spike\RETRIEVAL_EVAL_SPIKE.md` - Status: Spike — **S1 done 2026-10-30: the set, the runner, the integrity tests and the

## Bug Fixes

- **Bug: a citation opens the wrong passage when its reference is shared** - `BugFixes\citation_anchor_collision.md` - Status: **Closed 2026-10-27** — fixed and guarded while building the concordance (SPEC §18.3
- **Bug: a wrapped clause renders as two paragraphs, and copies back glued** - `BugFixes\reader_clause_line_breaks.md` - Status: **Closed 2026-10-28** — the hanging indent no longer splits a clause, and a numbered clause
- **Bug: SAOSO's text — a lost superscript, a swallowed part title, letterspaced words and two tables that lost their rows** - `BugFixes\saoso_text_glyphs_and_boundaries.md` - Status: **§1 closed 2026-10-27** — the glyph loss was an encoding bug in the extraction, not a

## Done

- **The Concordance — Implementation Plan** - `Done\CONCORDANCE_PLAN.md` - Status: **Done** — all eleven tasks landed 2026-10-27; **UAT SIGNED 2026-10-28** — `tests/uat/concordance_uat.md` carries eleven **PASS** results, signed by Kobus (Product) against commit `4e02d71`; applied by `scripts/uat_signoff.py`. The PGS administrator, committee reviewer and consumer-member seats are still empty (D4).
- **PRD: The concordance — the standard on one screen, and a citation that opens a line** - `Done\CONCORDANCE_PRD.md` - Status: **Done** — built 2026-10-27 (all eleven tasks of `CONCORDANCE_PLAN.md`), and
- **PRD: The documents page offers the concordance** - `Done\DOCUMENTS_READER_LINK_PRD.md` - Status: **Done 2026-10-28** — built, and **UAT Scenario 12 SIGNED PASS** by Kobus (Product) in
- **MVP 0 Implementation Plan — Standards Foundation & Public Shop Window** - `Done\MVP0_PLAN.md` - Status: Superseded — do not execute; see `MVP0_PLAN_V2.md`
- **Passage layout — Implementation Plan** - `Done\PASSAGE_LAYOUT_PLAN.md` - Status: **Done** — all six tasks landed 2026-10-27; **UAT Scenario 8 signed PASS 2026-10-28
- **PRD: Passage layout — the document's lists, rendered as lists** - `Done\PASSAGE_LAYOUT_PRD.md` - Status: **Done** — built 2026-10-27 (the display-only option A, chosen by the product owner
- **The reader's structure — Implementation Plan** - `Done\READER_STRUCTURE_PLAN.md` - Status: **Done** — all ten tasks built 2026-10-27 (gate 1139 passed / 1 skipped, Playwright 58). **UAT SIGNED 2026-10-28** — `tests/uat/concordance_uat.md` carries eleven **PASS** results, signed by Kobus (Product) against commit `4e02d71`; applied by `scripts/uat_signoff.py`. The PGS administrator, committee reviewer and consumer-member seats are still empty (D4). What differs from the plan — one corrected
- **PRD: The reader's structure — a table reads as a table, and a reference goes somewhere** - `Done\READER_STRUCTURE_PRD.md` - Status: **Done** — built 2026-10-27 and **UAT SIGNED 2026-10-28** — `tests/uat/concordance_uat.md` carries eleven **PASS** results, signed by Kobus (Product) against commit `4e02d71`; applied by `scripts/uat_signoff.py`. The PGS administrator, committee reviewer and consumer-member seats are still empty (D4).

## To Do (ideas without a PRD yet)

# To Do

Ideas that have no PRD file yet. `python product/backlog.py --write` pulls this into
the generated index's "To Do" section.

## Platform

- [ ] Set up `summarise.py` to generate `product/docs/state/` once there is code to summarise.
- [ ] `docker-compose.yml` + `Dockerfile` (MVP 0, sub-plan A).
- [ ] Decide the production host for the platform (the group currently has no server).
- [ ] Add a second physical backup copy — currently a single local external drive (R11, accepted gap).

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
      short-circuits at `if artefact is None → NO_ARTEFACT; continue`, so `opp` and `landscape`
      get no chunk count, no comparison, and no warning — and the same "no artefact" line is
      printed whether they hold 30 chunks from an old parser or **zero**. Measured on the VPS
      2026-10-30: the report said `no artefact` while the box's `opp` + `landscape` held **37**
      chunks against the dev box's **38**, built by whatever code ran on 2026-10-22 and never
      rebuilt since. Not drift by the current definition (there is nothing to compare against),
      and deliberately not fixed now: P4/P5 give both documents an artefact and the question
      disappears. Reopen if either document is ever edited from the PDF again.

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

## Human gates — on the box

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

## Drift (suggested moves)

_none_
