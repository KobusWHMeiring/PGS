# UAT — The public self-check, `/before-you-apply/`

**Feature slug:** `self_check`
**PRD:** `product/backlog/Refinement/SELF_CHECK_PRD.md`
**Plan:** `product/backlog/ready/MVP1A_PLAN.md` Task A8
**Decision:** D71 (the wording), D83 (the pledge placement), D31 (the land-history disagreement)
**Prototype:** `product/design/before_you_apply_prototype.html` (approved 2026-11-04, stepped wizard)
**Date:** 2026-11-05

---

## Purpose

Per `build_principles.md` §VIII, **UAT holds only checks a human must judge.** Everything a test can
prove — that nothing is stored without research consent, that the eleven derived controls resolve
from the frozen template, that the demographic consent is refused without the research one, that no
eligibility word appears in the HTML — is asserted by `core/tests/test_selfcheck.py` and is listed
below only so a reviewer can see it was covered.

This slice is judged on four things a test cannot see:

1. **Mirror or verdict.** The result has to read as *"this is what your answers show"*, not as a
   mark out of ten. The numbers are right by construction; the tone is the judgement.
2. **The land-history note.** Two thresholds and "the group has not settled which applies" is a hard
   sentence to make comprehensible. If it reads as evasion, the honesty buys nothing.
3. **"Rather not say" as a real answer.** A privacy answer that still feels like a refusal is worse
   than no option, because it collects a false "no".
4. **The consents as real choices.** Both drafts name the recipients, promise totals only, and offer
   withdrawal without an account. Whether a farmer believes them is the only test that matters.

---

## Pre-test setup

1. A **fresh** database, seeded: `python manage.py migrate` then `python manage.py seed_deployment`.
2. Load and activate the Crops questionnaire — the eleven derived controls come from it and the page
   is a caveat without it:
   `python manage.py load_template core/templates_data/crops.v1.json --activate`
3. `python manage.py runserver`, then open `/before-you-apply/` **on a phone**, and again at 1280 px.
4. Have one person who has **never read the OPP or the FORM** available for Scenario 3. A developer
   cannot judge whether the land-history note is comprehensible — they know the answer.
5. Before starting, open `/admin/` → *Self check reports* and note the count. You will end at the
   same number if you answer "no" to both consents, which is itself a check.

---

## Automated coverage (NOT UAT — asserted by the suite)

| What | Where |
|---|---|
| With neither consent ticked, no `SelfCheckReport` and no `SelfCheckDemographic` exists | `core/tests/test_selfcheck.py::test_nothing_is_stored_without_consent` |
| The report has no `member`/`farm`/`user` field to set | `…::test_research_consent_writes_one_row_and_stores_no_identifier` |
| Demographic consent without research consent is refused, and writes nothing | `…::test_demographic_consent_is_refused_without_research_consent` |
| Withdrawal deletes both rows, and a second withdrawal is a named error | `…::test_withdraw_deletes_both_rows`, `…::test_withdraw_refuses_an_unknown_reference` |
| A changed consent version is refused rather than recorded | `…::test_a_stale_consent_version_is_refused` |
| The eleven derived controls resolve from the active template, both directions | `…::test_the_eleven_derived_controls_resolve_from_the_active_template`, `…::test_every_template_marker_is_named_and_every_name_has_a_marker` |
| Every to-do citation is a declared FORM text-only citation | `…::test_every_todo_citation_is_declared_text_only` |
| "Rather not say" produces no to-do item and is not counted missing | `…::test_rather_not_say_produces_no_todo_item_and_is_not_counted_missing` |
| The page carries no eligibility claim, and the sweep covers the route | `…::test_the_page_states_no_claim`, `core/tests/test_claim_discipline.py` |
| The account step creates A6's account and **no** `FarmCategory` row | `…::test_the_account_step_creates_the_account_and_no_farm_category` |
| The aggregate refuses a census cell under `--min-count` | `…::test_the_report_refuses_a_cell_under_the_threshold` |
| The two fixed lines come from `MISSING_RECORD_BLOCKS_FINALISE` | `…::test_the_two_fixed_lines_come_from_the_finalise_gate_constant` |

---

## Scenario 1 — A farmer with records, on a phone, in sunlight

**Setup:** phone, outdoors if the weather allows.

1. Answer step 1: Crops, 1–5 ha, less than 1 ha pasture, 12–17 months, the second fee band.
2. On step 2 answer **yes** to the sketch, the field diagrams, the diary, the input records and the
   sales records, and leave the rest untouched.
3. Leave **both** consent boxes unticked and submit.

**Expected:** the result says how many records are in place, out of seven. Nothing is stored (check
the `/admin/` count). The fee band is named with the OPP figure.

**Judgement:** *Read it as the farmer. Does it read as a mirror — "this is what your answers show" —
or as a mark, a pass, or a warning?* Also: *could you do this one-handed, and did any tap miss?*

---

## Scenario 2 — A farmer with nothing, and the honesty of the to-do list

**Setup:** the same page.

1. On step 2 answer **no** to all seven records, except the last, which you answer **Rather not say**.
2. Submit without either consent.

**Expected:** seven-minus-one to-do items, each naming what will satisfy a visit and citing FORM
Sheet I §2; the "rather not say" item is absent from the list and named in one line instead.

**Judgement:** *Does the to-do list read as help or as homework?* And: *does the "rather not say"
line make the fourth answer feel like a real answer, or like a note that you refused?*

---

## Scenario 3 — The land-history note, read by someone who has never read the OPP

**Setup:** the person from the setup list, who has not read the source documents.

1. Answer step 1 with **12–17 months** and submit.
source documents and ask them to explain back what will happen to their land.

**Expected:** they say something like *"I am past twelve months and short of eighteen, the group has
not settled which number applies, and the visit will work it out"*. **Do not prompt.**

**Judgement:** *Did they get the disagreement without being told it exists?* If they concluded "so I
am fine" or "so I am not eligible", the note failed even though every threshold is printed — rewrite
the sentence, not the test.

---

## Scenario 4 — Both consents, and what the group can then see

**Setup:** the seeded instance, with the Crops questionnaire live.

1. Answer the check again, tick **both** consent boxes, and fill the three census selects.
2. Submit, then run `python manage.py report_self_check --demographics`.
3. Run it again with `--min-count 1`.

**Expected:** the run without `--min-count 1` refuses the census cell ("not shown — fewer than 5")
and prints the bands and the per-record uptake. With `--min-count 1` the cell appears.

**Judgement:** *Standing in the group's shoes: is this report something you would be comfortable
sharing with PGS South Africa and SAOSO — and does it say nothing a single farm could be identified
from?* This is the one output that could become a public claim (DESIGN §1), so it is judged as if it
would be published.

---

## Scenario 5 — The consents, read aloud

**Setup:** the person from Scenario 3, seated beside you.

1. Open step 5 and read the research consent **aloud**, then the census one.
2. Try to tick the census box before the research box.

**Expected:** both are visible as DRAFT until the group adopts them, and the census box cannot be
ticked before the research box.

**Judgement:** *Would you tick them?* Specifically: does the text name who receives the answers, say
"totals, never farm by farm", and give a withdrawal route that does not need an account? And does
the census question make it clear that funding applications are **not** covered? If any of those
reads as legal boilerplate, the wording is not finished — and the retention period is still the
group's unanswered question, so the draft banner must stay.

---

## Scenario 6 — From the check to the account, without becoming an application

**Setup:** a result page from Scenario 1.

1. Press **Save my details** and complete the account: farm name, nearest town, contact, email,
   password, and the Q8 consent.
2. Sign in if you were not signed in already.

**Expected:** you land on the application's next step — the **pledge** — not on a summary and not on
a categories step with ticks pre-filled from the check. In `/admin/`, the farm has **no** category
rows.

**Judgement:** *Does it feel like one flow, or like being handed to a different website?* And: *is it
obvious that the account is not an application, and that the pledge is what makes it one?*
