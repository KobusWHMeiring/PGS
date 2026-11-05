# To Do

Ideas that have no PRD file yet. `python product/backlog.py --write` pulls this into
the generated index's "To Do" section.

## Platform

- [ ] Set up `summarise.py` to generate `product/docs/state/` once there is code to summarise.
- [ ] `docker-compose.yml` + `Dockerfile` (MVP 0, sub-plan A).
- [ ] Decide the production host for the platform (the group currently has no server).
- [ ] **SMTP for the platform.** Deferred past the PGS demo by **D84** (2026-11-05): 1a ships with
      no mail and says so in the interface, so the account step shows "verification is not available
      yet" rather than a fake checkmark. Nothing in dev sends mail: there is no transactional
      provider, no sender domain and no `.env` key for one (measured 2026-11-05: the dev `.env`
      holds `DJANGO_SECRET_KEY` only). It gates three things at once — **email verification** at
      account creation (`User.email_verified_at` exists and nothing sets it), **password reset**, and
      the administrator's escalation path (`Refinement/ESCALATION_ANSWER_PATH_PRD.md`, which is
      still waiting on a published contact). When it is picked up: choose the provider, publish the
      administrator's address (it is also the `Reply-To`, because a `no-reply` sender silently
      loses every escalation reply), and set SPF/DKIM/DMARC on the group's domain.
- [ ] Add a second physical backup copy — currently a single local external drive (R11, accepted gap).

## Decided, not yet queued (2026-11-02)

- [ ] **Context budget cuts 4.2–4.4** (`product/docs/context/CONTEXT_BUDGET.md`): a §18.3 row
      becomes a sentence + a link (14 rows are over 1.5 KB), split `core/services/_chatbot.py`
      (91 KB, 3× the §II cap) and `knowledge/corpus.py` (49 KB), then wire
      `scripts/context.py --check` into the gate. 4.1 (the HANDOVER split) and the
      `AGENTS.md` context-discipline block are done; `--check` reports 25 breaches today (11
      source files, 14 decision rows).
- [ ] **Ingestion engine generalisation** (**D80**: X2 now, X3 when a document demands it) —
      **has a PRD and three of its six slices** (2026-11-03): `product/backlog/In Progress/INGESTION_ENGINE_PRD.md`.
      S0 is the **eight-shape fixture set** (`knowledge/tests/shape_fixtures.py`, 8 xfailed targets);
      S1 is `build_corpus.py` refusing to overwrite a reviewed `<!-- table -->` block; S4 is the
      **verification harness** (`knowledge/table_harness.py` + `scripts/check_tables.py`) — the four
      reviewed tables, 14 rows, pass requirements 2-7 with one mutation proved per requirement.
      Open: S2 the extractor evaluation (Docling / Document AI) against the eight — it needs an
      install and GCP credentials, so it is a session with a preamble — S3 the generator emitting
      table blocks (and recording the extraction mode, the harness's last per-document datum), and
      S5 re-reviewing Appendix 6a and Appendix 7 through the harness: the two live defects the PRD
      measures, and the two the harness **cannot see** because they are not table blocks at all.
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
- [ ] **A surface that records a membership fee and its payment.** A6 (2026-11-05) built and
      tested `record_membership_fee()` and `record_membership_payment()` (the APPLICANT → ACTIVE
      transition, which OPP §2.3 and spec §7.7 tie to payment) and **no view calls them**: the
      fee year is the group's (D39) and a self-registration must not write a `paid_on` it never
      received. Until this exists, every applicant stays `APPLICANT` and unpaid, so A7's
      eligibility gate passes for nobody in a running instance. It belongs with the committee's
      work (A7 / C1) or a one-screen administrator page — decide which before the pilot.
- [ ] **Approve the Q8 consent wording** (SELF_CHECK_PRD §11.6). A6 ships it as a **seeded draft**
      with its two `[DECIDE]` markers, renders it as a DRAFT on the account step, and takes
      consent against the exact version shown. Setting `ConsentText.approved_at` removes the
      banner and changes nothing else; consents taken under a draft stay queryable
      (`ConsentRecord.text.approved_at__isnull=True`). The retention period and the withdrawal
      address are still the group's answers, and the address is also blocked on publishing the
      administrator's contact details (below).
- [ ] **A8 needs two more `ConsentText` rows before it can take a consent.** A6 seeded only the
      `ACCOUNT` purpose (Q8's draft); the self-check's research and demographic consents (§3.6, D64's
      rule twice) have reviewed wording in the D71 ledger (`product/design/d71_self_check_questions.html`,
      the E1 and E2 `consent` strings) and no row. Seed them as `RESEARCH` and `DEMOGRAPHICS`, with
      `approved_at` null and rendered as DRAFT in the same honest way as the account step, or decide in
      writing not to — but the page must not offer a checkbox with no text behind it (`ConsentRequiredError`
      already refuses the account without one).
- [ ] **UAT for the application flow.** A6 has 32 automated tests and no `tests/uat/` checklist:
      the judgements left are the ones a person must make in a browser — does the four-step flow
      read as one thing on a phone, is the consent block readable before it is ticked, and does
      "Your part is done" leave a farmer with the right expectation about paying.
- [ ] **Five of the seven record "why" sentences name no source** (task B3, 2026-11-05). R02–R04, R06
      and R07 explain what the record is *for* without citing a clause or the FORM, and
      `SELF_CHECK_PRD` §3.3 asks every control's why to name its source. The wording is D71's reviewed
      copy, so it was transcribed rather than rewritten and pinned in
      `test_crops_template.py::NO_CITED_CLAUSE`. A8 is where a clause is added or the group says the
      explanation is enough.
- [ ] **The FORM prints "(Yes/No)" on a question that asks for a percentage** — V21's child, *"What
      percentage of the farm is dedicated to biodiversity? (Yes/No)"*. B3 transcribed it as printed
      with YES/NO/NA options so the visit can still record an answer; the group should decide whether
      the child wants a number instead. Found while authoring the template, 2026-11-05.

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
- [ ] **The two public consents have no retention answer** (found building A8, 2026-11-05). The
      research and demographic texts are seeded as **drafts** from the D71 ledger: they name the
      recipients, promise totals only and offer withdrawal without an account, but neither says how
      long the answers are kept. That is the same `[DECIDE]` `SELF_CHECK_PRD` §11.6 leaves for the
      account consent, and it matters more here because these rows are research data. The drafts
      render with the banner until `approved_at` is set — one data edit, no migration.
- [ ] **An `/ask/` refusal does not point at the self-check** (A8, `SELF_CHECK_PRD` §4.3, deferred).
      The PRD asks for the link "when the question is about the visitor's own eligibility", and the
      refusal path has no eligibility classification to hang it on. Adding one means either an
      intent test over the question or a second refusal string — a chat change, judged on its own,
      not a front-door one slipped in with A8.
- [ ] **A derived control's FORM text is long on the front door** (A8, seen in the browser). The
      eleven markers render the template's own `text` in the disclosure ("The farm visit asks this
      as: …"); Q11.1's is a two-hundred-word FORM cell. It is honest and it is unread on a phone —
      the group may prefer the first sentence only, which is a template edit (a new version), not a
      code change.
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
