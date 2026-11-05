# Session 1o — 2026-11-05 — sub-plan B lands, and the printed FORM corrects the plan three times

**Tag:** `1o` (after `1n`).
**Worktree:** `../pgs-visit`, branch `feat/mvp1a-visit`. `main` was never touched.
**Commits:** `36eedfe` (B1, B2, B4) and `93a5cac` (B3).

---

## 1. What landed

**Sub-plan B is complete: four of four tasks.** The questionnaire is now data with a validator, a
versioning rule and a loader, and the Crops sheet is authored.

| Task | What | Where |
|---|---|---|
| **B1** | `AssessmentTemplate` + `validate_schema` (every problem, with its path) | `core/models/_assessment.py`, `core/services/_templates.py`, migration `0015`, 31 tests |
| **B2** | One live template per category, enforced twice; `assert_template_usable` | `_templates.py`, migration `0016`, 9 tests |
| **B4** | `load_template` — validates, never overwrites a version, `--activate` | `core/management/commands/load_template.py`, 9 tests |
| **B3** | `crops.v1.json` from FORM `6.B.1.Crops`, and its review copy | `core/templates_data/`, `scripts/crops_template_review.py`, `product/docs/templates/`, 24 + 3 tests |

**Gate:** 1883 passed / 1 skipped / 8 xfailed in **204.69 s** (one run at HEAD; the pre-B3 tree measured
233.18 s in an earlier run of the same session — a different tree, so not a spread measurement, and
§3.17 still says a single wall-clock number is not a benchmark).

**Mutations:** 14, in `_scratch/b1/mutate.py`, all caught — six on the validator, two on activation, three
on the loader, three on the template and its review artefact.

## 2. The FORM corrected the plan three times, and the corrections are pinned

`MVP1A_PLAN.md` Task B3's numbers do not all survive contact with the sheet. Each correction is in
`test_crops_template.py`'s docstring **and** as an assertion, so a later reader cannot "fix" the JSON
back to the plan without going red:

1. **Eleven self-check markers, not twelve.** D71 and `SELF_CHECK_PRD` §3.4 give the twelve as the
   seven Sheet I §2 records plus five practices (C1–C5). But C5 — *"Do you buy in produce from other
   farmers to sell on?"* — is **FORM Sheet A, Aggregation**; the other four (Q4.2, Q5.1, Q11.1, Q11.2)
   are on the Crops sheet. So the template carries eleven, and C5 becomes an own control in
   `SELF_CHECK_ITEMS`. Both documents are amended in place with the date, and my first attempt to say
   so in the D71 row **broke the context budget** (1,567 of 1,500 bytes) — the budget is right, the
   evidence belongs in §3.4, and the row now says "eleven" in the same space.
2. **Nine printed child rows, not thirteen.** The plan lists V4(2), V10(2), V11(2), V19(3), V21(2),
   V35(2). The sheet's grey blocks hold rows 30–31 (V4), 42 (V6), 64 (V10), 79 (V11), 122–123 (V19),
   136 (V21), 213 (V35) — nine, and the plan omits V6's while counting parents for the rest.
3. **A "Question N" is a container, and its sub-items are what is answered.** The plan's own marker
   example is `crops.Q4.2`, so the 38 questions are headings and there are **79** answerable lines. The
   validator now validates both levels, and gained `records` (`crops.R01`…) and a verdict's
   `question_ref` because the FORM's data needed them.

The plan's other numbers held exactly: 37 verdicts, the V15/V31 gaps, the four polarities it names,
`links_to: INPUT_REGISTER` on Q4.3.

## 3. What was read off the sheet rather than assumed

`respondent` came from the cells' **fills**, not from a guess: every question row in `6.B.1.Crops` is
unfilled (farmer-supplied, spec §8), every verdict row is grey (`FFD8D8D8`, and `FFD9D9D9` for V35's
second line). So all 79 items are `FARMER` and no verdict carries a respondent — a verdict is the
assessor's. The probe is `_scratch/b3/fill_probe.py`.

The `why` copy for the eleven markers was **not written this session**: it is D71's reviewed ledger
(`product/design/d71_self_check_questions.html`), extracted by `_scratch/b3/ledger_why.py` and pasted
verbatim. That is why the artefact exists — the wording was judged once, in a session with the product
owner, and re-writing it here would be a second opinion nobody asked for.

## 4. Two defects found while authoring, both recorded not fixed

- **Five of the seven record "why" sentences name no source.** §3.3 asks every control's why to name
  its clause; R02–R04, R06 and R07 explain what the record is for and cite nothing. Pinned in
  `test_crops_template.py::NO_CITED_CLAUSE`, so a *new* uncited marker fails and the list cannot grow.
  A8 is where the clause is added or the group says the explanation is enough.
- **The FORM prints "(Yes/No)" on a percentage question** — V21's child, *"What percentage of the farm
  is dedicated to biodiversity? (Yes/No)"*. Transcribed as printed with YES/NO/NA options so a visit
  can still record an answer; the choice is the group's. In `todo.md`.

## 5. The bug the tests caught

`activate_template` branched on the **in-memory** `is_active` of the row it was handed. So
re-activating a superseded version — a rollback, which is a normal act — was a silent no-op, because
the object still believed it was active. `test_reactivating_a_superseded_version_moves_the_flag_back`
went red on the first run. Two unconditional UPDATEs now. This is the same family as `testing_hazards`
§1.37 (a guard that reads a stale value is not a guard): the fix is to let the database answer.

## 6. What the next agent gets

- **Next: A8 — the public self-check.** It is now unblocked on every count it needed: eleven derived
  controls sit in the frozen Crops template, the thirteenth (C5) is an own control, and the approved
  stepped-wizard prototype (`product/design/before_you_apply_prototype.html`) is the build target.
  **Then A7** (eligibility gates) and **A4**; A7 still needs the payment surface named in `todo.md`.
- **The commit count in the state file had been drifting, and this session found it.** `1m` said 18 and
  the branch had 19; `1n` said 19 and it had 22; this block first said 21 and it has **25**. Each
  session had added to the previous session's *written* number instead of measuring it. `HANDOVER.md`
  now quotes the command as well as the number (`git log --oneline 781cf37..HEAD | wc -l`), which is
  the same lesson as §3.17 in a cheaper place: quote the measurement, not the arithmetic.
- **The template is live-able but not live:** nothing on this deployment has run
  `load_template core/templates_data/crops.v1.json --activate`, and no view starts an assessment yet
  (C1/E). Loading it is a data act, not a deploy requirement until then.
- **Read the review copy, not the JSON**, to check B3 against the sheet:
  `product/docs/templates/crops_v1_review.md` (generated; a test fails if it goes stale).
- **`_scratch/b1/mutate.py`** is the mutation harness for this sub-plan; re-run it after touching
  `_templates.py` or the template.
- A merge will still conflict in `HANDOVER.md` by design — keep both strands' state.
