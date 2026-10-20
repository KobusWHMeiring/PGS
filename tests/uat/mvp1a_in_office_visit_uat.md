# MVP 1a UAT — In-Office Visit Flow

**Feature slug:** `mvp1a_in_office_visit`
**PRD:** `product/backlog/ready/MVP1A_PRD.md`
**Plan:** `product/backlog/ready/MVP1A_PLAN.md`
**Status:** Drafted **before** implementation (shift-left validation)
**Date:** 2026-10-20

---

## Purpose

Per `build_principles.md` §VIII, **UAT contains only checks a human must judge.** If pytest, a
script or a grep can prove it, it belongs in the automated suite. Every item below carries a
`Judgement:` clause naming the human-only call.

The question for every candidate is not *"does this need the app running?"* but **"could an
automated test assert this outcome?"** A status code, a stored row, a derived count and a rendered
string are all assertable. Whether a rendered questionnaire is *the same document* as the paper
form is not.

---

## Pre-test setup

1. `python manage.py seed_deployment && python manage.py load_template core/templates_data/crops.v1.json`
2. Have the source documents open: **FORM Sheet B.1 (Crops)** and **FORM Sheet B.2 (input suppliers)**,
   **FORM Sheet I (Conclusion)** and **OPP §3.1, §3.3, §4.1, §4.2**.
3. Create one real applicant with a real farm and turnover band — not a fixture.
4. Have a printed copy of the existing paper questionnaire beside the screen.
5. Run: `python manage.py runserver`

---

## Automated coverage (NOT UAT — asserted by the suite)

| What | Where |
|---|---|
| Polarity derivation for all eight value/polarity combinations | `core/tests/test_evaluation.py` |
| `is_compliant` is never authored by a view or form; stored value equals recomputation | `core/tests/test_evaluation.py` |
| Crops template: 38 questions, 37 verdicts, both `V32` keyed, `V15`/`V31` declared as gaps | `core/tests/test_crops_template.py` |
| A template edit after submit leaves the assessment's `template_schema` unchanged | `core/tests/test_questionnaire_submit.py` |
| `validate_assessment_team()` — one test per OPP §3.3/§4.1.2 clause | `core/tests/test_team_validation.py` |
| 5-day notice, 3-day questionnaire, 5-day conclusion window | `core/tests/test_previsit_rules.py` |
| A visit with an unpaid `AssessmentFee` cannot leave `DRAFT` | `core/tests/test_fees.py` |
| Only `respondent=FARMER` questions render in the portal | `core/tests/test_questionnaire.py` |
| Attachment-required questions unsatisfied until an `EvidenceDocument` exists | `core/tests/test_attachments.py` |
| The six sub-verdict groups are structured and total 13 children | `core/tests/test_crops_template.py` |
| A child answer never changes the parent's `value` or `is_compliant` | `core/tests/test_evaluation.py` |
| `SocialEquity` and `RecordCheck` are unique per visit; `MISSING` requires a note | `core/tests/test_conclusion.py` |
| Farmer evidence upload moves a corrective action to `SUBMITTED`; `OVERDUE` is derived | `core/tests/test_corrective_followup.py` |
| Prior open actions appear at the next visit; `NOT_MET` Critical escalates | `core/tests/test_prior_actions.py` |
| `finalise_visit` refuses each unmet item and returns the full list | `core/tests/test_finalise_gates.py` |
| Severity definitions are character-identical to FORM Sheet I | `core/tests/test_findings.py` |
| Replay of a `client_uuid` creates zero additional rows | `core/tests/test_sync.py` |
| No certification outcome, seal or certificate is reachable in 1a | `core/tests/test_scope_fence.py` |

---

## Scenario 1 — Is the digital questionnaire actually the same document?

**Category:** completeness
**Setup:** A real applicant on Crops. Open the questionnaire beside printed FORM Sheet B.1.

1. Read the digital questionnaire top to bottom against the paper form.
2. Ask the farmer to complete it as if for a real visit.

**Expected:** Every question on the paper form has a counterpart, in the same order, with the same
wording. The farmer's half (white cells) is visible to the farmer; the administrator's half (grey
cells) is not.

**Judgement:** Could a farmer who has filled in the paper form before complete this without asking
what a question means? Wording drift and silent omissions are invisible to any test — a question can
be present and still be unanswerable. Only someone who has sat with a farmer can tell.

---

## Scenario 2 — Do the severity definitions read as the group's own words?

**Category:** domain fidelity
**Setup:** Raise a finding on a real visit in the capture screen.

1. Read the helper text for Minor, Major and Critical.
2. Compare to FORM Sheet I's footnote and to how the committee actually talks about findings.

**Expected:** The three definitions appear verbatim, with the group's own interpretation available.

**Judgement:** Would the committee accept these as *their* definitions, or do they read as a software
team's paraphrase of a form? The spec records that the levels are to be discussed and interpreted at
annual meetings — so the wording is the group's to own, not ours to improve.

---

## Scenario 3 — Can an administrator run one visit without the spreadsheet?

**Category:** workflow
**Setup:** A scheduled visit with a valid team and a submitted questionnaire. Work with the
administrator on their own machine.

1. Open the visit, work through the questionnaire, record verdicts.
2. Raise two findings, assign corrective actions and due dates.
3. Capture the input register with the farmer's actual product list.
4. Collect the three signatures.
5. Generate the report.

**Expected:** The whole visit completes in one sitting, with no side-spreadsheet.

**Judgement:** Did the administrator reach for a spreadsheet, a notebook or a phone call at any point?
The measure of this feature is not that the screens work — it is that the paper workflow actually
stops. Whatever forced the fallback is the real backlog item.

---

## Scenario 4 — Does the team validation match what the OPP means?

**Category:** rules
**Setup:** Try to schedule four visits: (a) a real, valid team; (b) three people; (c) two peer farmers
and an administrator but no consumer; (d) a valid team plus two observers.

1. Read the error or warning for each.

**Expected:** (a) passes; (b) and (c) are refused with an explanation naming the OPP clause; (d) passes
with observers excluded from the count.

**Judgement:** Do the messages make sense to a committee member who has read the OPP, or do they read
as software rules? And is the *one-consumer warning* (OPP §3.1 says two "where feasible") an
acceptable nudge, or does it feel like nagging about something the group cannot always manage?

---

## Scenario 5 — Is the report something the committee would accept?

**Category:** output
**Setup:** A complete visit. Generate the PDF.

1. Read it as a committee reviewer would, having only this document.
2. Check the certification block at the end.

**Expected:** Farm details, participants and roles, the concerns table with severities and corrective
actions, and key knowledge captured. The certification outcome is clearly **pending**.

**Judgement:** Would this pass as a visit report at a committee meeting — and is *pending* unmistakably
a placeholder rather than a decision left blank by accident? A report that looks decided without a
decision is worse than an obviously incomplete one.

---

## Scenario 6 — Does the input register capture what a farmer actually brings?

**Category:** completeness
**Setup:** FORM Sheet B.2 beside the screen. Ask a real farmer for their input list — compost,
amendments, seed, feed.

1. Enter five real products, including one conventionally-treated seed and one product whose Act 36
registration status the farmer does not know.
2. Check how "not stated" is represented.

**Expected:** All nine columns are capturable; unknown Act 36 status is recordable as unknown rather
than forced to Yes/No.

**Judgement:** Is the register usable in the field with a farmer who does not know the answer to every
column — or does it demand information the farmer has never had? This is the register that substantiates
"no prohibited synthetic inputs", so a register that is skipped is a certification gap, not a UX issue.

---

## Scenario 7 — Can a member who cannot sign still join?

**Category:** inclusion
**Setup:** OPP §I.2 — *"Certain groups or individuals may be unable to read and sign the
documentation."* Work with the administrator.

1. Capture a pledge using a **distinctive mark**, with witness name, designation and signature.
2. Capture a pledge as **verbal, witnessed**, with a photographic record.

**Expected:** Both paths complete; neither is a workaround or an override.

**Judgement:** Would an administrator use this path with a member who cannot read, without
apologising for it? OPP §I.2 exists precisely for this, and a path that feels like an exception will
not be used — which means that member does not join.

---

## Scenario 8 — Does the pledge record the conflict honestly?

**Category:** integrity (D31)
**Setup:** Register a farmer who declares 12 months of clean annual land history.

1. Complete the pledge step.
2. Look at what the platform recorded and what it refused to conclude.

**Expected:** The declared period is recorded as declared; the conflict with OPP §V (18 months for
annuals) is flagged; no In-Conversion period is inferred and no seal-related state changes.

**Judgement:** Is the flag visible and comprehensible to an administrator, without inviting them to
resolve a question the group has not answered? The platform must not quietly adjudicate a
contradiction in the group's own documents.

---

## Scenario 9 — Are the sub-verdicts actually answerable?

**Category:** fidelity
**Setup:** FORM Sheet B.1 beside the screen, open at V4, V10, V11, V19, V21 and V35. A visit in capture.

1. Answer V4 "Yes", then leave one of its two children blank. Try to finalise.
2. Answer every child, including one `NA`.
3. Compare the nesting to the printed form.

**Expected:** Each printed child has its own control and key; a blank required child blocks finalise and
is named in the error; `NA` is accepted as an explicit answer. The parent's single value is unchanged by
the children.

**Judgement:** Would an assessor notice a skipped child before signing, or does one parent control invite
the Homtini blanks? Does the screen read like the paper's nested rows, or like a form that has been
flattened to save space?

---

## Scenario 10 — Does the conclusion survive the digital visit?

**Category:** completeness (D45)
**Setup:** FORM Sheet I beside the screen. A visit with findings and a farm that does not keep sales
records.

1. Capture social equity: staff, employment status, labour-law compliance, and the child-labour
   question with its activity description.
2. Work the records checklist: mark the sales record `MISSING` with a note, and the soil test `CHECKED`.
3. Generate the report.

**Expected:** Every Sheet I §1 field and §2 item appears in the PDF; `MISSING` is visibly recorded, not
blank; no worker or child-labour detail appears in any public output.

**Judgement:** Would the committee accept this as the conclusion page of the paper report? Is the
social-equity section usable in a real visit, or does it read as a compliance afterthought that an
administrator will skip?

---

## Scenario 11 — Can the farmer answer the Major action without email?

**Category:** workflow (D45)
**Setup:** A finalised visit with a Major finding — *"provide these documents for review in 2 weeks"* —
and a TDS, a non-GMO letter and an invoice to supply.

1. As the farmer, open the portal task list and upload the three documents.
2. As the administrator, verify the action.

**Expected:** The action shows its reason, recommendation and due date; the upload moves it to
`SUBMITTED`; the reviewer can move it to `VERIFIED`; after the due date it reads `OVERDUE`; the
documents remain private.

**Judgement:** Would a farmer who uses WhatsApp and email today understand what is being asked and by
when — without phoning the administrator? What still forces a fallback to email is the real backlog
item.

---

## Scenario 12 — Does the next visit remember the last one?

**Category:** continuity (D45)
**Setup:** A farm with an open Critical action (ducks not certifiable) and an open Major action
(documents outstanding) from the previous visit.

1. Start the next visit and look for the prior actions before walking the farm.
2. Record `VERIFIED` for the Major action and `NOT_MET` for the Critical one.
3. Try to finalise without reviewing one of them.

**Expected:** Both prior actions are visible at the start of capture; `NOT_MET` on the Critical action
escalates; finalise refuses an unreviewed action and names it.

**Judgement:** Does the assessor open the last visit's actions before the walkabout, as PREP requires?
Does the escalation read as the next step in the group's process, not as a software error?

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Product | Kobus Meiring | | |
| PGS administrator | | | |
| Committee reviewer | | | |
| Farmer member (Scenarios 1, 7, 11) | | | |

**Release gate:** all scenarios judged acceptable, or the exceptions recorded above with a decision to
proceed. Scenarios 3, 6, 9, 10 and 12 require the **administrator's own machine** — a developer's laptop
is not a valid setup for those. Scenario 11 needs a farmer's own device or account, not an
administrator impersonating them.
