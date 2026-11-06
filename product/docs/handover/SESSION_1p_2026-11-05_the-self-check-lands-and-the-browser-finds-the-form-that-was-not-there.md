# Session 1p — 2026-11-05 — the self-check lands, and the browser finds the form that was not there

**Tag:** `1p` (after `1o`).
**Worktree:** `../pgs-visit`, branch `feat/mvp1a-visit`. `main` was never touched.
**Commit:** `5369809` (A8) plus this doc close.
**Gate:** 1944 passed / 1 skipped / 8 xfailed (`--create-db`, test database dropped first) — measured
**300.08 s** and then **348.41 s** on the same suite an hour apart, which is §3.17 in one line and why
both numbers are quoted. `tests/e2e/test_selfcheck_wizard.py`: 7 passed, run separately because the gate
has no browser.

---

## 1. What landed

**A8 — the public self-check, `/before-you-apply/`.** Sub-plan A is now **six of eight**; B is four
of four.

| Piece | Where | Size |
|---|---|---|
| Two tables, one migration, **no FK to `Member`, `Farm` or `User`** | `core/models/_selfcheck.py`, `0017` | 5 KB |
| The rules: `build_check`, `evaluate` (never writes), `submit` (consent-gated, atomic), `withdraw`, the per-IP budget | `core/services/_selfcheck.py` | 23 KB |
| The reviewed wording: 9 own controls from the D71 ledger, 11 derived specs, bands, caveats, land notes | `core/services/_selfcheck_items.py` | 19 KB |
| The answer form, built from the controls | `core/forms/_selfcheck.py` | 6 KB |
| The view (two POSTs, one route), URL, `PAGES` entry | `core/views/_public.py`, `core/urls.py`, `core/services/_public.py` | +60 lines |
| The stepped wizard, its CSS and its JavaScript | `core/templates/public/before_you_apply.html`, `selfcheck.css`, `selfcheck.js` | 13 + 9 + 7 KB |
| The aggregate, with `--min-count` and `--demographics` | `core/management/commands/report_self_check.py` | 6 KB |
| The two consents A6 did not seed, as drafts | `core/services/_seed.py` | +50 lines |
| Tests | `core/tests/test_selfcheck.py` (45), `tests/e2e/test_selfcheck_wizard.py` (7), `tests/tools/test_uat_parse.py` (1 pinned) | — |
| UAT, judgement only | `tests/uat/self_check_uat.md` | 6 scenarios |

**Why the service is two files:** `_selfcheck.py` passed the 30 KB cap at 40 KB with the wording in
it, so the seam the PRD itself draws was cut — §3.4 says the wording lives "in two places, and neither
is a migration", and this module is the code half. Nothing else changed; `_selfcheck.py` re-exports
every name, so no caller knows the slice exists.

**Mutations:** 15, in `_scratch/a8/mutate.py`, **all caught**. Three of them failed to catch on the
first run and each exposed a weak test rather than a missing guard:

- "rather not say is counted as missing" stayed green because
  `test_rather_not_say_produces_no_todo_item_and_is_not_counted_missing` asserted `records_not_said`
  but never `records_missing`. The test was named for the rule and did not check it. Fixed by
  asserting the count (`== 3`), which is exactly what the mirror's denominator depends on.
- "no research wording" and "a non-Crops visitor gets no caveat" were anchored on strings that no
  longer existed where the mutation looked, and one mutation applied but was tested against a test
  that could not see it (the marker-missing branch is only reached when a marker is genuinely absent,
  so `test_the_eleven_derived_controls_resolve_from_the_active_template` can never exercise it).
  That missing test now exists: `test_a_live_template_missing_a_marker_is_a_loud_failure` strips
  `crops.Q4.2`'s marker from a live template and demands `MarkerMissingError`.

## 2. The defect the browser caught, and no Django test could

Every single-choice control rendered **nothing**. A `ChoiceField` left on its default `Select` yields
one subwidget holding the whole `<select>`, so a template that loops `{{ choice.tag }}` per option
draws no inputs at all. The page returned 200, the form validated (every field is optional by design),
a result rendered, `test_claim_discipline` swept it, and 1944 tests were green.

The browser test found it through the answered-counter ("0 of 0 answered"), and a one-off probe
printed the DOM facts that three guesses had not:

```
step 1 inputs: 26 radios: 22     # after adding RadioSelect to SINGLE/RECORD fields
step 2 inputs: 28 radios: 28     # before: step 2 inputs: 0
```

Written up as `testing_hazards.md` §1.40. Two more design defects came out of the same screenshots:
`.btn--ghost` is cream-on-transparent and invisible on a cream ground (use `.btn--outline`), and the
step nav clipped "Two consents" mid-word at 1280 px because it was a scroller at every width.

## 3. Four plan corrections, each amended in place

1. **`SELF_CHECK_PRD` §3.4 — a derived control's question wording.** A template marker carries the
   `why`, not the front-door title or the answer set (Q11.1 is a `TEXTAREA` in the FORM; the reviewed
   front door asks "Where do your seeds come from?" with five chips). So the eleven keep title, help,
   options and source in code, take only `why` from the marker, and render the template's own `text`
   on the card as *"The farm visit asks this as: …"*. Both sentences are then on one card, which is a
   stronger promise than either copy alone. Pinned by
   `test_the_service_carries_no_copy_for_a_derived_control` (a derived `why` must stay empty in code).
2. **§3.6 — the consent act cannot be a `ConsentRecord`.** That model has a non-null `User` FK; a
   visitor has no account and must not get one by answering a questionnaire. The act is
   `research_consent_at` + `consent_text_version` on the report — a version, never a copy of the text.
3. **§4.5 — the aggregate leaked the cell it protects.** The first version printed "Female: too few
   to report (1 of a minimum 5)". In a catchment of a few dozen farms, "Female: 1" *is* the person.
   The refusal now names neither the value nor the count, and a test asserts both.
4. **The two public consents are drafts with no retention answer.** Seeded from the ledger verbatim
   (`research-2026-11-05`, `demographics-2026-11-05`), `approved_at` null, rendered with the draft
   banner. The retention period is the same `[DECIDE]` §11.6 owes, and it is now in `todo.md` for
   these two as well.

**Not built, and recorded rather than dropped:** `SELF_CHECK_PRD` §4.3 asks for a link to the check
from an `/ask/` refusal "when the question is about the visitor's own eligibility". The refusal path
has no eligibility classification to hang it on, and inventing one is a chat change judged on its own.
`todo.md` carries it.

## 4. What the next agent gets

- **Next: A7 — the eligibility gates**, which still needs the payment-recording surface named in
  `todo.md`; then **A4**. **C1/E's finalise gate imports `MISSING_RECORD_BLOCKS_FINALISE` from
  `core.services._selfcheck`** — the plan's §3.2 promise now has one home, and the public page and the
  gate read the same constant.
- **The demo needs three data acts**, and the dev database has none of them: `migrate` (it is at
  `0014`; `0015`–`0017` are unapplied), `seed_deployment`, then
  `load_template core/templates_data/crops.v1.json --activate`. Without the template the page is
  honest — nine own controls and a caveat — but eleven of the twenty controls do not exist.
- **A8 is the first consumer that needs the template live.** The `1o` line "load it when C1/E needs
  it" was written before this page existed; the page needs it to be worth demoing.
- **Run `_scratch/a8/mutate.py`** after touching `_selfcheck.py`, `_selfcheck_items.py`, the form, the
  view or the command.
- **Screenshots** for a design pass are in `_scratch/a8/` (gitignored): `step1-desktop`,
  `step2-phone`, `step5-desktop`, `result-desktop`. Read one, not four.
- `_scratch/a8/probe_wizard.py` prints the wizard's DOM facts (inputs and radios per step) without a
  browser — the cheapest way to answer "did the widgets render at all?".
- A merge will still conflict in `HANDOVER.md` by design — keep both strands' state.
