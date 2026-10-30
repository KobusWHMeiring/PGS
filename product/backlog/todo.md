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
