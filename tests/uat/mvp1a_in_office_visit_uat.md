# MVP 1a UAT — In-Office Visit Flow

**Feature slug:** `mvp1a_in_office_visit`
**PRD:** `product/backlog/ready/MVP1A_PRD.md`
**Plan:** `product/backlog/ready/MVP1A_PLAN.md`
**Status:** Drafted **before** implementation (shift-left validation)
**Date:** 2026-10-18

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
   and **OPP §3.1, §3.3, §4.1, §4.2**.
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

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Product | Kobus Meiring | | |
| PGS administrator | | | |
| Committee reviewer | | | |
| Farmer member (Scenarios 1, 7) | | | |

**Release gate:** all scenarios judged acceptable, or the exceptions recorded above with a decision to
proceed. Scenario 3 and Scenario 6 require the **administrator's own machine** — a developer's laptop
is not a valid setup for those.
