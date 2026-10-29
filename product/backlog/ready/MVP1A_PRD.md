# PRD: MVP 1a — In-Office Visit Flow

**Status:** Ready — all blocking decisions closed (spec §18.3 D27–D39, D45). **Prerequisite satisfied:** MVP 0 sub-plan A (A1–A10) landed 2026-10-19; the custom `User` is migrated and first. See `MVP1A_PLAN.md` §0.2.
**Owner:** Kobus Meiring (Product)
**Last Updated:** 2026-10-20
**MVP:** 1a of 2 within slice 1 (spec §19, D25)
**Scope:** Application → membership and pledge → pre-visit questionnaire → scheduling with committee
validation → assessment capture (connected) → Sheet I conclusion → visit report PDF. **Stops at
`UNDER_REVIEW`.**
**Reference:**
- Target-state spec — `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` §3, §4.1–§4.2, §7, §8, §11
- Plan — `product/backlog/ready/MVP1A_PLAN.md`
- Shape decision — `product/design/d1_mvp1_shape_exploration.html` (D25, D26)
- Build rules — `product/docs/context/build_principles.md`
- Source documents — OPP §I, §II, §3.1, §3.3, §4.1, §4.2; FORM Sheets A, B.1, B.2, I §§1–3, J; PREP

---

## 1. Problem Statement

**What 1a solves.** The assessment lifecycle is the group's core work, and its first half is entirely
on paper: a farmer applies with a handwritten form, signs a pledge, declares turnover on a sliding
scale; the questionnaire is photocopied and posted to the assessment team three days before a visit;
the administrator writes the report from notes afterwards. None of it is queryable, and the paper is
the record.

1a digitises that half. It does **not** make the field work paperless — that is 1b, and 1a's own
claim stops short of it (D25, D33).

**Why now, and why this half first.** Two reasons:

1. **The irreversible risk is here.** `Assessment.template_schema` is frozen as evidentiary history at
the first visit. Every decision about how a FORM verdict is represented — polarity, key namespacing,
sub-questions, the grey/white two-role split — becomes permanent the moment a real visit is captured.
Getting it right is worth one deliberate pass; discovering it after 1b exists means migrating
evidence.
2. **The knowable risk is not here.** Browser storage on real devices is 1b's problem and cannot be
resolved by inspection (D26). Building the determinable half first is the whole point of the split.

**Why not wait for the spike.** 1a's domain models, flows and templates depend only on MVP 0's
template schema. Only the `visitPack` producer and the sync API are gated on the seam contract
(`1∥`). Domain work starts immediately.

---

## 2. Strategic Goal

> **A farmer applies, signs, declares turnover and completes the pre-visit questionnaire online; an
> administrator assembles a legally-valid assessment team, runs the visit on a connected device,
> records verdicts, findings and corrective actions against the frozen template, and exports the visit
> report — with no retyping and no paper reconciliation.**

**Success looks like:** the administrator runs one complete visit from the portal and hands the
committee a PDF that matches what the paper process would have produced — and the data behind it can
answer "which Crops farms were not compliant on on-farm composting?" without opening a spreadsheet.

---

## 3. The Fence

| In 1a | Not in 1a | When |
|---|---|---|
| Application, membership status, pledge, fees | Offline capture, service worker, IndexedDB | 1b |
| `AssessmentTemplate` + hand-authored **Crops** template | Templates for Animal Husbandry, Seed Production, Agro-processing | 1b or later (D28) |
| Pre-visit questionnaire with autosave and attachments | Split-sync, media queues, quota handling | 1b |
| Scheduling + `validate_assessment_team()` + notice rules | Voice notes (recorder, transcription) | post-MVP |
| Connected assessment capture (the degrade path) | **Certification decision, outcomes, seals** | **MVP 2** |
| Verdicts with polarity and structured **sub-verdicts**, findings, corrective actions | Certificates, QR, public registry | MVP 2 |
| Signatures (3 signatories), evidence photos | Aggregation approval workflow | post-MVP |
| Input register (FORM B.2), prior certification (Sheet A) | Reporting dashboard, gap analysis, census exports | MVP 3 |
| **Sheet I conclusion**: social equity (§1) + documentation/records checklist (§2) | — | 1a |
| **Farmer corrective-action follow-up** + prior-action review at the next visit | — | 1a |
| Visit report PDF (Sheet I report portion, decision block pending) | Discipline workflow, unannounced visits | out of scope (§17.1) |
| **Public self-check** at `/before-you-apply/` — 20 controls, to-do list, declared fee band, and a consented aggregate (D71) | Reporting on it (a management command only) | MVP 3 |
| `visitPack` producer + sync API — **gated on `1∥`** | Translated content | post-MVP |

**Three deliberate limitations, stated rather than discovered:**

1. **1a requires connectivity.** The connected capture form degrades to nothing without signal. This is
   the honest consequence of the split (D25) and the reason the MVP 1 claim attaches to 1b.
2. **The PDF has no decision block.** Sheet J's certification section stays visibly pending until MVP 2.
   A report that looks decided but is not would be worse than an obviously incomplete one.
3. **Sheet I is not the same thing as Sheet J.** 1a captures the conclusion's social-equity and
   records-checklist sections because they are assessment evidence; it does **not** select one of the
   four outcomes. D45 makes that distinction explicit so neither half is silently dropped.

**Added after the Homtini 2022 report review (D45).** 1a also captures the Sheet I conclusion
(§1 social equity, §2 documentation and records), structured sub-verdicts, a farmer corrective-action
task list, a prior-action review at the next visit, and the finalise gates that make a blank field
impossible to sign. These are assessment records, not certification decisions: D33 is unchanged.

---

## 4. Proposed Solution

Seven sub-plans. B is the irreversible one and is sequenced before anything that consumes it.

| Sub-plan | What it delivers | Proves |
|---|---|---|
| **A — Membership & application** | `Member`, `Farm`, `FarmAlias`, `FarmCategory`, `FarmContact`, `CommitteeTerm`, `Pledge`, `MembershipFee`, `AssessmentFee`, `PriorCertification`; application flow; eligibility gates; **A8 — the public self-check that leads into it (D71)** | The membership rules from OPP §I–§II can be enforced rather than described, and a farmer who is not ready yet is told what to gather instead of being turned away |
| **B — Templates** | `AssessmentTemplate`, the v1 schema format, `load_template`, the hand-authored **Crops** template, freeze semantics | That 38 questions and 37 verdicts can be represented without distorting the paper form |
| **C — Questionnaire** | `Assessment`, `AssessmentAnswer`, `EvidenceDocument`; farmer-facing render, autosave, attachment readiness, submit and snapshot; **corrective-action follow-up task list** | That the two-role (grey/white) form works when only half of it is farmer-visible, and the farmer can answer a finding after the visit |
| **D — Scheduling & committee** | `FarmVisit`, `VisitParticipant`; `validate_assessment_team()`; the numeric pre-visit rules; fee gate | That OPP §3.3/§4.1 composition is a server-side validation, not a guideline |
| **E — Capture & findings** | `AssessmentVerdict` with polarity and sub-answers, `Finding`, `NotifiableExemption`, `CorrectiveAction`, `Signature`, `EvidencePhoto`, `InputSupply`; **Sheet I conclusion** (`SocialEquity`, `RecordCheck`), `PriorActionReview` | That the polarity model survives contact with real verdicts, and the conclusion is captured with the evidence |
| **F — Visit report** | `finalise_visit`, WeasyPrint Sheet I report, **completeness and signature gates** | That the administrator's report is generated, not typed, and cannot be finalised around a blank |
| **G — Seam** | `visitPack` producer, `sync_visit_text`, `store_media_item`, finalise endpoint | That the contract is real on the server side before 1b is built against it |

---

## 5. Technical Requirements

The parts an implementer must not improvise. Everything else is in the spec.

### 5.1 Template schema v1

The frozen JSON is the contract between the FORM, the questionnaire renderer, the capture UI, the
`visitPack` and 1b. Its shape is fixed here.

```jsonc
{
  "schema_version": 1,
  "category": "CROPS",
  "label": "Crops",
  "standard_version": "SAOSO v2.1 2026",
  "source": "FORM Sheet B.1 (Crops), 2026 workbook",
  "allowed_ref_gaps": ["V15", "V31"],          // declared, not ignored — see §4.2.1
  "sections": [
    { "key": "B1.1", "label": "Fertility Management", "part": "Crop Production",
      "questions": [
        { "key": "crops.Q4.1", "ref": "4.1", "respondent": "FARMER", "type": "TEXT",
          "text": "Describe your soil fertility plan…", "required": true, "attachments": [] },
        { "key": "crops.Q4.3", "ref": "4.3", "respondent": "FARMER", "type": "TEXT",
          "text": "List your compost ingredients, their sources, as well as supplier details.",
          "required": true, "attachments": [], "links_to": "INPUT_REGISTER" }
      ] }
  ],
  "verdicts": [
    { "key": "crops.V04", "ref": "V4", "respondent": "ADMINISTRATOR",
      "polarity": "POSITIVE", "options": ["YES", "NO", "NA"],
      "text": "Is there adequate on-farm composting (on farm composting is a key requirement of organic principles)",
      "standard_ref": null,
      "sub_questions": [
        { "key": "crops.V04.a", "text": "Is the compost of a good quality? (decomposed, friable, organisms/biological life visible, etc.)",
          "polarity": "POSITIVE", "options": ["YES", "NO", "NA"], "required": true },
        { "key": "crops.V04.b", "text": "Is the source of all ingredients, including manure, acceptable?",
          "polarity": "POSITIVE", "options": ["YES", "NO", "NA"], "required": true }
      ] },
    { "key": "crops.V03", "ref": "V3", "respondent": "ADMINISTRATOR",
      "polarity": "INFORMATIONAL", "options": ["YES", "NO"],
      "text": "Is there need for a transition period?", "standard_ref": null }
  ]
}
```

Rules:
- `key` = `<category>.<ref>`, lowercase, ref zero-padded to two digits (`crops.V04`). A repeated printed
  ref takes a letter suffix (`crops.V32a`, `crops.V32b`) and keeps the printed `ref` on both rows.
- `respondent ∈ {FARMER, ADMINISTRATOR}` — this *is* the FORM's grey/white split.
- `polarity ∈ {POSITIVE, NEGATIVE, INFORMATIONAL}`. Never inferred, always declared.
- `standard_ref` is nullable. Only the agro-processing sheet carries clause references in the source;
  Crops leaves it `null` rather than inventing one.
- `allowed_ref_gaps` documents the source's own numbering defects so validation warns on **new** gaps
  without failing on known ones.
- A question may carry an optional `self_check: {"tier": 1, "why": "..."}` block (**D71**). It marks
  a question the public `/before-you-apply/` page asks, and carries the sentence that names its clause.
  Twelve controls carry it — Q4.2, Q5.1, Q11.1, Q11.2 and the seven Sheet I §2 records — so the front
  door and the visit cannot drift apart in wording. An unknown key inside the block is rejected.
- `sub_questions` are **structured**, not prose: each child has its own `key`, `polarity`, options and
  `required` flag. They are stored on the parent verdict's `sub_answers` JSON as
  `{"<sub_key>": "YES|NO|NA"}` and are never folded into the parent's single value. The FORM prints
  six such groups in Crops (V4, V10, V11, V19, V21, V35).

### 5.2 Polarity is derived, not authored

Per §4.2.1: `value ∈ {YES, NO, NA, NULL}`, and

```
is_compliant = NULL             if value in (NULL, NA)
             = (value == YES)   if polarity == POSITIVE
             = (value == NO)    if polarity == NEGATIVE
             = NULL             if polarity == INFORMATIONAL
```

`is_compliant` is materialised at write time and asserted against a recomputation in tests. **No view,
form or admin may set it directly.**

### 5.3 Freeze semantics

`Assessment.template_schema` is a full copy taken when the questionnaire is submitted (Flow B step 4).
Capture reads **only** from the snapshot. Editing `AssessmentTemplate` afterwards must have no effect
on any existing assessment — this is the spec's stated "single most important data-integrity rule", and
it gets an explicit test.

### 5.4 `validate_assessment_team()`

Enforced server-side, no override without an `ADMIN` role and a recorded rationale:

| Rule | Source |
|---|---|
| Exactly one participant with role `ADMINISTRATOR` | OPP §3.3, §4.1.2 |
| ≥ 2 `PEER_FARMER` participants | OPP §4.1.2 |
| ≥ 1 public member (`CONSUMER` or `VALUE_CHAIN_ACTOR`) | OPP §3.3 |
| ≥ 4 attending participants in total | OPP §3.3 |
| `OBSERVER` participants do not count toward the four | OPP §3.3 |
| Observers ≤ the host farm's declared maximum | OPP §3.3 |
| If no participant's `Member.expertise` covers the assessed `Category`, a `TECHNICAL` expert is required | OPP §4.1.2 |
| The administrator holds `ADMIN` role or the `FARM_VISIT_ADMINISTRATION` committee position | OPP §3.1 |

**Two consumer representatives** (OPP §3.1: "where feasible") is modelled as a **non-blocking warning**,
not a hard rule — §3.3's one-consumer minimum is the enforceable clause. Recorded here because the two
sections disagree and the choice should not be invisible.

**Numeric pre-visit rules:** scheduling requires `scheduled_for - today ≥ 5 days` (OPP §4.1(1));
the frozen questionnaire must be available to the team `≥ 3 days` before (OPP §4.1(2)); the conclusion
window is 5 days after the visit (OPP §4.2(5)) — stored as `review_due_on`, enforced in MVP 2.

### 5.5 Fee gate (D32)

`FarmVisit` cannot leave `DRAFT` unless, for that visit: `Member.status == ACTIVE`, `is_paid_up`, **and**
the `AssessmentFee` for that visit is paid (OPP §2.3, "Fees are payable prior to the farm assessment
visit"). Turnover band is **declared** and peer-reviewed, never computed from sales data.

### 5.6 Seam contract (gated on `1∥`)

`visitPack` v1 and `VisitSyncEnvelope` v1 are written down and contract-tested before the producer and
the sync API are implemented. They are **not** designed until the 0∥ spike finishes (D26). Nothing in
sub-plan G starts before that.

### 5.7 Pledge attestation (D31)

The pledge's land-history periods contradict OPP §V (annuals: 12 months in the pledge, 18 in §V;
other perennials the reverse). The platform records exactly what was attested and sets
`land_history_conflict=True`; it does **not** resolve the conflict or infer a seal. Seals are MVP 2.

### 5.8 Sheet I conclusion (D45)

`finalise_visit` is not the whole of Sheet I. The paper conclusion has two sections the visit report
must reproduce:

- **§1 Social equity and justice** — one `SocialEquity` row per visit: whether staff are employed,
  worker count, employment status, labour-law compliance, whether staff live on the premises, and the
  child-labour question with its activity description. Worker and child-labour fields are sensitive;
  they are never serialised publicly.
- **§2 Documentation and records** — one `RecordCheck` per printed item: farm sketch, field diagrams,
  farm diary, input purchase/donation records, sales records, input/output reconciliation, soil test,
  water test, and the three agro-processing items. `status ∈ CHECKED | MISSING | NOT_APPLICABLE`;
  `MISSING` requires a note and may support a Finding but does **not** auto-create one. This is the
  assessor's verification, not a second upload: `evidence_doc` may point at the questionnaire's
  `EvidenceDocument`.

A visit cannot be finalised with an unset `RecordCheck` or without a `SocialEquity` row. A `MISSING`
record is a recorded fact, not a blocker — Homtini's missing sales records did not stop the visit;
blank did.

### 5.9 Sub-verdicts and completeness (D45)

The FORM prints several verdicts with child Yes/No rows (Crops: V4 ×2, V10 ×2, V11 ×2, V19 ×3,
V21 ×2, V35 ×2). `AssessmentVerdict.sub_answers` is `{"<sub_key>": "YES|NO|NA"}`. A child is
answered independently of its parent, but `finalise_visit` refuses while any required child is `NULL`;
`NA` is an explicit answer, `NULL` is an omission. The capture UI renders one control per child and
never folds them into the parent's value.

This is the Homtini failure made impossible: V11's supplier-information child and V25 were left blank
on a report that was nevertheless signed, and V5 was left blank beside them.

### 5.10 Corrective-action follow-up and prior actions (D45)

- **After the visit**, every `CorrectiveAction` appears in the farmer's portal as a task with its due
  date. The farmer uploads the requested evidence (TDS, non-GMO letter, invoice, compost ingredients
  list); the upload is an `EvidenceDocument` linked to the action and sets `SUBMITTED`. The reviewer
  moves it to `VERIFIED`/`CLOSED`; `OVERDUE` is derived from `due_on`.
- **At the next visit**, every open action from prior visits is opened at the start of capture (PREP
  requires it). One `PriorActionReview` records `VERIFIED | PARTIAL | NOT_MET` with a note. A
  `NOT_MET` Critical action → `ESCALATED`. `finalise_visit` refuses while any prior open action has no
  review.

The Homtini Major action — *"provide these documents for review in 2 weeks"* — is exactly this loop.
A report that records the action but gives the farmer no way to answer it is a paper process with a
database behind it.

### 5.11 Input traceability (D45)

`InputSupply` gains `input_kind ∈ SEED | COMPOST | AMENDMENT | FEED | OTHER`,
`seed_status ∈ ORGANIC | CONVENTIONAL_UNTREATED | CONVENTIONAL_TREATED | UNKNOWN | NA`
and `approval_status ∈ PENDING | APPROVED | REJECTED` with `approval_rationale` and `approved_by`.
Supplier documents attach through `EvidenceDocument.input_supply`, not through free-text ingredients.
Seed status is what makes the *"conventional, untreated seeds"* notifiable exception queryable instead
of buried in a notes column.

---

## 6. Execution Steps

Task order, acceptance tests and schema details: `MVP1A_PLAN.md`.

1. **A1–A7** — membership, farms, pledge, fees, prior certification, application flow, eligibility gates.
   **A8** — the public self-check (D71), after A6 because the application is its only exit.
2. **B1–B4** — template model, schema validation, the hand-authored Crops template, freeze semantics.
3. **C1–C6** — assessment and answers, questionnaire render + autosave, attachments, submit/snapshot, clarifications, corrective-action follow-up. **C2a** carries the self-check's answers into the questionnaire as drafts.
4. **D1–D4** — visit and participants, team validation, notice rules, scheduling UI.
5. **E1–E9** — verdict capture with polarity and sub-answers, findings, exemptions, corrective actions, signatures, photos, input register, Sheet I conclusion, prior-action review.
6. **F1–F3** — WeasyPrint report, `finalise_visit`, completeness gates.
7. **G1–G5** — **only after `1∥` freezes**: pack producer, sync, media, finalise endpoint.

---

## 7. Success Criteria

**Machine-checkable**

- [ ] Polarity derivation is correct for all six inspected counter-examples (V1, V3, V16, V23, Animal V14, V29)
- [ ] No view/form/admin can write `is_compliant` directly; stored value always equals recomputation
- [ ] Crops template validates: 38 questions, 37 verdict rows, both `V32` occurrences keyed, `V15`/`V31` declared as gaps
- [ ] Editing an `AssessmentTemplate` after a visit changes nothing about that visit's questionnaire or capture
- [ ] `validate_assessment_team()` rejects: 3 people; 1 peer farmer; 0 public members; 2 administrators
- [ ] `validate_assessment_team()` accepts a valid four; observers excluded from the count
- [ ] Scheduling 4 days out is rejected; questionnaire available 2 days out is rejected
- [ ] A visit with an unpaid `AssessmentFee` cannot leave `DRAFT`
- [ ] The questionnaire renders `respondent=FARMER` questions and no `ADMINISTRATOR` ones
- [ ] Attachment-required questions are visibly unsatisfied until an `EvidenceDocument` exists
- [ ] The Crops template declares the six sub-verdict groups; a parent with an unanswered required child cannot be finalised
- [ ] `finalise_visit` refuses an unanswered verdict, an unanswered required sub-verdict, a missing signature, an unset `RecordCheck`, an unreviewed prior action, and an unreported exemption
- [ ] A `MISSING` `RecordCheck` is recordable and renders in the report
- [ ] The report renders Sheet I §1 and §2 alongside the findings and pending decision block
- [ ] A farmer can submit evidence against a corrective action; it moves to `SUBMITTED`; `OVERDUE` is derived
- [ ] Prior open actions appear at the next visit; a `NOT_MET` Critical action escalates
- [ ] Replaying a `client_uuid` creates zero additional rows (contract test, sub-plan G)

**Human-judged (UAT)**

- [ ] The rendered questionnaire is recognisably the same document as FORM Sheet B.1 — nothing silently dropped (committee)
- [ ] The severity definitions read verbatim as the group's own wording (committee)
- [ ] An administrator can run one complete visit without touching the spreadsheet (administrator)
- [ ] The report PDF is something the committee would accept as a visit report (committee)
- [ ] The conclusion reads as the paper Sheet I — social equity and the records checklist intact (committee)
- [ ] An administrator can answer a "last visit" action without leaving the capture screen (administrator)
- [ ] The next visit opens the last visit's actions before the walkabout (administrator)
- [ ] The input register (B.2) captures what a farmer actually brings — Act 36 answers included (administrator)

---

## 8. Risks & Mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1a-1 | **The template schema is wrong and becomes evidence.** | Freeze only after a full dry run of one visit against the paper form; the schema's `schema_version` allows a v2 for *new* templates while v1 assessments stay intact. |
| R1a-2 | **Polarity mis-assigned during authoring** — the quiet failure: it looks like data. | Inverse-polarity fixtures in the test suite for every `NEGATIVE` verdict; a seed list of the six known inversions asserted explicitly. |
| R1a-3 | **Hand-authoring 38 questions is tedious and gets skipped** — a partial template looks like a working one. | A completeness test asserting question and verdict counts against constants derived from the workbook; `allowed_ref_gaps` makes an omission explicit rather than silent. |
| R1a-4 | **WeasyPrint on Windows** needs GTK system libraries and will cost a morning. | Deferred from MVP 0 deliberately (D19); install it as the first action of sub-plan F, not last. Fallback: render inside the Compose Postgres container's sibling image, or a Linux dev container. |
| R1a-5 | **1a has no offline path**, so a visit in a dead zone cannot be captured at all. | Stated in §3; 1b is the fix and the MVP 1 claim is attached to it. The administrator is told plainly. |
| R1a-6 | **Seeding the committee roster stores named individuals.** | The roster is published in OPP §VII, so the processing is already public; keep it to name + position + term, nothing else. |
| R1a-7 | **`verify_pending`**: sub-plan G is built before any client exists, so the sync API is exercised only by contract tests. | Explicit `contract test` task; the envelope is validated against the JSON Schema on both directions. Accept that real traffic arrives in 1b. |
| R1a-8 | **Sheet I's conclusion is mistaken for the decision block and dropped.** The outcome is legally significant, so it is easy to hear "no decision in 1a" as "no conclusion in 1a". | D45 separates the two: `SocialEquity` and `RecordCheck` are assessment evidence and ship now; the four outcomes stay in MVP 2. The report renders both, and the UAT asks the committee to read the conclusion. |
| R1a-9 | **Sub-verdicts are flattened into the parent** and the evidence disappears. | Structured `sub_questions` in the template, `sub_answers` on the row, one control per child, and a finalise gate. Homtini's blank V11 supplier child and V25 are the regression fixture. |

---

## 9. Still Open (not blocking 1a)

| # | Question | Blocked on | Affects |
|---|---|---|---|
| D31 | The pledge vs OPP §V land-history conflict | **Group decision** | MVP 2 seal issuance |
| C1 | Seal cardinality; which seal for "Organic - pending corrective action" | MVP 2 modelling | MVP 2 |
| A1 | `standard_ref` coverage — clause mappings for Crops/Animal/Seed verdicts | Authoring effort | MVP 3 gap analysis |
| — | Templates for the other three categories | After 1a proves the schema | 1b / later |
| D3 | Afrikaans in the offline PWA shell | 1b | 1b |

---

## 10. Pre-Flight Checklist

- [ ] Models in `core/models/_<domain>.py`, re-exported from `__init__.py`
- [ ] Views in `core/views/_<domain>.py`; forms in `core/forms/_<domain>.py`
- [ ] Services in `core/services/_<domain>.py` with `In/Out/Side Effects/Fails/Idempotency` contracts
- [ ] URLs under the right prefix (`/portal/`, `/committee/`, `/api/v1/`)
- [ ] Tests in `core/tests/test_<domain>.py`; `factory_boy` factories in `factories.py`
- [ ] Migrations backwards-compatible; `RunPython` has `reverse_code`
- [ ] `select_related` / `prefetch_related` on every relational query
- [ ] `transaction.atomic()` on every multi-table write
- [ ] No logic in templates; formatting in `pgs_extras.py`
- [ ] Integer cents (`_cents`), never floats — `MembershipFee`, `AssessmentFee`, `catering_fee_cents`
- [ ] No file over 30 KB
- [ ] Void/deactivate instead of delete on `AssessmentVerdict`, `EvidencePhoto`, `SyncReceipt`, `CorrectiveAction`
- [ ] `SocialEquity`, `RecordCheck` and `PriorActionReview` migrated and re-exported
- [ ] Sub-verdicts stored in `sub_answers`, never folded into the parent value
- [ ] Finalise gates return an enumerated list of unmet items, not a generic "incomplete" error
- [ ] UAT items carry a `Judgement:` clause; machine-provable checks live in the suite
