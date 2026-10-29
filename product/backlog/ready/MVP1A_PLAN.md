# MVP 1a Implementation Plan — In-Office Visit Flow

**Status:** Ready
**Owner:** Kobus Meiring (Product)
**Last Updated:** 2026-10-20
**MVP:** 1a of 2 within slice 1 (spec §19, D25)
**PRD:** `MVP1A_PRD.md` · **Spec:** `PGS_PLATFORM_SPEC.md` §3, §4.1–§4.2, §7, §8, §11
**Reference:** `../../docs/context/build_principles.md` · `../Done/MVP0_PLAN.md` (superseded, for pattern only)

---

## 0. How to execute

- **TDD order.** Every task states its failing test first. A task is done when the test passes.
- **One commit per task**, message prefixed with the task id (`feat(a3): pledge capture`).
- **Schema before logic.** Models land in `core/models/` and migrate before the views that use them.
- **No view may write a derived field.** `is_compliant` is computed; see Task E1.
- **Sub-plan G does not start** until the `1∥` seam contract is frozen (D26). A hard gate, not a
  preference. The spike that `1∥` waits on is its own backlog item —
  `../spike/OFFLINE_SPIKE_PRD.md` (`0∥`). It blocks G only; **A–F start immediately**.

### 0.1 Frozen decisions

| # | Decision |
|---|---|
| D25 | 1a is breadth; 1b is depth; the MVP 1 claim attaches to 1b |
| D27 | Polarity is template data; `value` is tri-state; `is_compliant` derived and materialised |
| D28 | Templates hand-authored, Crops only |
| D29 | `AssessmentFee` and `EvidenceDocument` defined and built here |
| D30 | `InputSupply` (FORM B.2) and `PriorCertification` (Sheet A) are in 1a |
| D31 | Pledge recorded as written, `land_history_conflict` flagged, no seal inference |
| D32 | Assessment fee gated before the visit |
| D33 | 1a stops at `UNDER_REVIEW`; ships connected capture; no decision, no certificate |
| D34 | GPS as two decimals — **no PostGIS, no GDAL** |
| D35 | `Farm.current_status` deferred to MVP 2 |
| D36 | `FarmCategory.status ∈ APPLIED | FOR_ASSESSMENT | ASSESSED | INACTIVE` |
| D37 | `catchment` is a deployment setting; no `Member.catchment`, no `Farm.catchment` |
| D38 | `Member.probation_until` added |
| D39 | `membership_no` = `OUT-<year>-<seq>`; `nearest_town` plain text; `is_paid_up` row-period definition |

### 0.2 Hard prerequisite — MVP 0 sub-plan A is **complete**

**Sub-plan A (A1–A10) landed on 2026-10-19.** The scaffold, environment-driven settings,
the **custom `User` model** (migrated, and the first migration — `core_user` exists and
`auth_user` was never created), `Category`/`Seal` as data with `seed_deployment`,
`/health/`, Celery with retry policies, the `knowledge` ↛ `core` import contract, the
`scripts/verify.sh` gate, and backup/restore with a rehearsed restore.

So the prerequisite for every task below **is met** — this section previously read
"there is no application code in this repository", which was true when 1a was written
and is not any more.

Two corrections to the deliverable list as it was written:

- **There is no CI** (A8 was reassessed and rejected; see `HANDOVER.md` §3). The gate is
  `scripts/verify.sh`, run locally and on the server before a deploy.
- **Start from B1, not from A.** Sub-plan A needs no further work; MVP 0's remaining
  increments are B (corpus), C (public site) and D (chatbot).

Confirm the foundation is healthy before building on it:

```bash
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh
```

---

## 1. Model map

`core/models/_assessment.py` roughly doubles in size — split it if it approaches 30 KB
(`build_principles.md` §II), vertically:

```
core/models/_core.py            Member CommitteeTerm Pledge MembershipFee AssessmentFee
                                Farm FarmAlias FarmCategory FarmContact PriorCertification
core/models/_assessment.py      AssessmentTemplate FarmVisit VisitParticipant
                                Assessment AssessmentAnswer AssessmentVerdict
                                Finding NotifiableExemption CorrectiveAction
                                EvidenceDocument EvidencePhoto VoiceNote Signature
                                InputSupply SyncReceipt
                                SocialEquity RecordCheck PriorActionReview
```

`SocialEquity`, `RecordCheck` and `PriorActionReview` are the Sheet I conclusion (D45). `SocialEquity`
is one row per visit; `RecordCheck` is one row per Sheet I §2 item; `PriorActionReview` is one row per
prior open action, per visit.

`VoiceNote` ships as **schema only** (spec §17.2 — recorder UI and transcription are post-MVP). It is
migrated now so deferring costs nothing structural.

`CertificationDecision`, `ProductOutcome`, `Certificate`, `CertificateProduct`,
`PublicVerificationEvent` and `_aggregation.py` are **MVP 2**. Do not create them.

---

# Sub-plan A — Membership & application (Flow A)

### Task A1: Farms and members

**Files:** `core/models/_core.py`, `core/models/__init__.py`, `core/tests/test_membership.py`,
`core/tests/factories.py`

**Tests first**

```python
def test_member_is_paid_up_is_derived_not_stored(member):
    assert not member.is_paid_up
    MembershipFee.objects.create(member=member, amount_cents=10000, paid_on=date(2026, 2, 1),
                                 period_start=date(2026, 1, 1), period_end=date(2026, 12, 31))
    assert Member.objects.get(pk=member.pk).is_paid_up is True

def test_is_paid_up_uses_the_row_period_not_the_calendar_year(member):
    # D39: periods are explicit on the row, so "payable by end of February" is never hardcoded
    MembershipFee.objects.create(member=member, amount_cents=10000, paid_on=date(2025, 3, 1),
                                 period_start=date(2025, 3, 1), period_end=date(2026, 2, 28))
    assert member.is_paid_up is True        # covers today, despite a 2025 payment

def test_probation_has_an_end_date(member):
    # D38: OPP §4.6 — one calendar year. A status you cannot exit is a data trap.
    member.status = "PROBATION"
    member.probation_until = date(2027, 3, 1)
    member.save()
    assert Member.objects.get(pk=member.pk).probation_until == date(2027, 3, 1)

def test_farm_has_no_catchment_and_no_postgis_field(farm):
    # D37, D34
    assert not hasattr(farm, "catchment")
    assert farm.latitude is None and farm.longitude is None
    assert "location" not in {f.name for f in Farm._meta.get_fields()}

def test_farm_aliases_resolve_to_one_canonical_farm(farm):
    # §4.1: "Chillin Out Farm" / "CHILLOUT FARM" must never fork a farm
    FarmAlias.objects.create(farm=farm, name="CHILLOUT FARM", source="live site")
    assert Farm.resolve("chillout farm") == farm

def test_farm_public_uuid_is_not_sequential(farm):
    assert isinstance(farm.public_uuid, uuid.UUID)
    assert farm.public_uuid.int > 10**20
```

**Then** implement `Member` (`status ∈ APPLICANT | ACTIVE | PROBATION | LAPSED | TERMINATED`,
`probation_until` nullable — D38, `membership_no` formatted `OUT-<year>-<seq:04d>` — D39,
and `is_paid_up` **defined as** `MembershipFee(paid_on not null, period_start <= today <= period_end).exists()`
— D39), `Farm` (`public_uuid`, `publish_consent`, `nearest_town` **plain text** — D39,
optional `latitude`/`longitude` **decimals, not a geometry column** — D34; **no `current_status`**,
which is MVP 2 — D35), `FarmAlias`, `FarmCategory` (FK to `Category`, `status ∈ APPLIED |
FOR_ASSESSMENT | ASSESSED | INACTIVE` — D36), `FarmContact`. **No `catchment` field** on either
`Member` or `Farm` — it is a deployment setting (D37).
Census fields (`census_gender`, `census_age_band`, `census_demographic_group`) are `sensitive` and
**excluded from every serializer** — add a test asserting they never appear in public output.

**Acceptance:** migrations apply on an empty DB; the resolve test passes with three spelling variants.

---

### Task A2: Committee terms and the 2026 roster

**Files:** `core/models/_core.py` (`CommitteeTerm`), `core/services/_seed.py`,
`core/tests/test_seed_committee.py`

**Tests first:** seeding twice creates no duplicates; `EventsCoordination` and
`AcademicRepresentative` exist as **vacant** (a representable state, not a missing row);
`position` accepts exactly the eleven OPP §3.1 values and rejects anything else.

**Then** implement `CommitteePosition` choices from spec §3.2 and seed the OPP §VII roster —
names, position, `agm_year=2026`, `elected_on`, `vacated_on=None`. Keep only name + position + term;
no contact details.

**Acceptance:** `seed_deployment` seeds categories, seals *and* committee terms idempotently.

---

### Task A3: The pledge

**Files:** `core/models/_core.py` (`Pledge`), `core/forms/_membership.py`,
`core/services/_membership.py`, `core/tests/test_pledge.py`

**Tests first**

```python
def test_verbal_pledge_requires_witness_and_evidence(member):
    with pytest.raises(WitnessRequiredError):
        record_pledge(member, kind="FARMER", method="VERBAL_WITNESSED")

def test_distinctive_mark_is_a_valid_pledge_method(member):
    # OPP §I.2 — members who cannot sign
    p = record_pledge(member, kind="FARMER", method="DISTINCTIVE_MARK",
                      witness_name="S. Mentz", witness_designation="Administrator",
                      evidence_document=doc)
    assert p.method == "DISTINCTIVE_MARK"

def test_land_history_conflict_is_flagged_not_resolved(member):
    # D31: pledge says 12 months for annuals, OPP §V says 18. Record, don't adjudicate.
    p = record_pledge(member, kind="FARMER", method="SIGNATURE",
                      declared_annual_clear_months=12)
    assert p.land_history_conflict is True
    assert p.resolved_in_conversion_months is None
```

**Then** `Pledge(member, kind, method, signed_on, place, declared_land_history_ok,
in_conversion_declared, in_conversion_months, declared_annual_clear_months,
declared_perennial_clear_months, land_history_conflict, recorded_by, witness_name,
witness_designation, witness_signature, evidence_document)`.

`land_history_conflict` is set by the service when a declared period disagrees with OPP §V
(annuals 18, pasture 12, other perennials 12). Nothing is reconciled (D31).

**Acceptance:** all three tests pass; the consumer pledge has no witness requirement and no land history.

---

### Task A4: Prior certification history

**Files:** `core/models/_core.py` (`PriorCertification`), `core/tests/test_prior_certification.py`

**Tests first:** a `DENIED` record requires a reason; `body_name` is required for both kinds; a farm
may hold several rows (prior PGS group *and* a third-party certifier *and* a prior denial).

**Then** implement `PriorCertification(farm, kind ∈ PGS|THIRD_PARTY, body_name, certificate_ref,
outcome ∈ GRANTED|DENIED, expires_on, denial_reason)` — FORM Sheet A (D30).

**Acceptance:** a denial without `denial_reason` raises on save.

---

### Task A5: Fees and the assessment fee gate

**Files:** `core/models/_core.py` (`MembershipFee`, `AssessmentFee`),
`core/services/_membership.py`, `core/tests/test_fees.py`

**Tests first**

```python
@pytest.mark.parametrize("turnover,band,initial,renewal", [
    (200_000,  "B1", 150_000,  90_000),
    (400_000,  "B2", 250_000, 200_000),
    (900_000,  "B3", 300_000, 250_000),
    (2_000_000,"B4", 370_000, 320_000),
    (4_000_000,"B5", 500_000, 500_000),
    (6_000_000,"B6", 800_000, 800_000),
])
def test_turnover_band_matches_opp_2_3(turnover, band, initial, renewal):
    assert band_for(turnover) == band
    assert fee_cents_for(turnover, kind="INITIAL") == initial
    assert fee_cents_for(turnover, kind="RENEWAL") == renewal

def test_fee_is_declared_not_computed(member):
    # D29: turnover is self-declared and peer-reviewed, never inferred
    fee = declare_assessment_fee(member, declared_turnover=200_000, kind="INITIAL")
    assert fee.turnover_band == "B1"
    assert fee.declared_turnover_cents == 20_000_000

def test_visit_cannot_be_scheduled_with_unpaid_assessment_fee(member, visit):
    with pytest.raises(AssessmentFeeUnpaidError):
        confirm_visit(visit)                      # D32 / OPP §2.3
```

**Then** implement both fee models (**integer cents only**, `_cents` suffix), the OPP §2.3 six-band
table as data, and `confirm_visit()` asserting `is_paid_up` **and** the assessment fee paid (D32).

**Acceptance:** all six bands pass; gate rejects both unpaid-membership and unpaid-assessment-fee.

---

### Task A6: Application flow

**Files:** `core/views/_portal.py`, `core/forms/_application.py`, `core/services/_membership.py`,
`core/templates/portal/apply*.html`, `core/tests/test_application.py`

Flow (§7): self-register (`FARMER` role + `Member{status: APPLICANT}`) → POPIA consent captured with
**separate purposes** (assessment, public profile, photographic publication) → pledge → pick categories
(creates `FarmCategory` rows) → declare turnover (creates `AssessmentFee`) → attest BPP + SAOSO
familiarisation → record membership fee.

**Tests first:** registration without POPIA consent is refused; ticking two categories creates two
`FarmCategory` rows; the turnover step creates exactly one `AssessmentFee`; a `POST` cannot set
`Member.status` (the service owns transitions).

**Acceptance:** a full application completes in one test; no view over 20 lines.

---

### Task A7: Eligibility gates

**Files:** `core/services/_membership.py`, `core/tests/test_eligibility.py`

**Tests first:** `assert_eligible_for_assessment(member)` raises for `APPLICANT`, `LAPSED`,
`TERMINATED`, and for unpaid membership; passes for `ACTIVE` + paid up. `PROBATION` passes with a
warning flag (OPP §4.6: probation does not forfeit the logo).

**Acceptance:** four rejection cases and one pass, each a named exception.

---

### Task A8: The public self-check

**Files:** `core/models/_selfcheck.py`, `core/services/_selfcheck.py`, `core/forms/_selfcheck.py`,
`core/views/_public.py`, `core/templates/public/before_you_apply.html`,
`core/management/commands/report_self_check.py`, `core/tests/test_selfcheck.py`,
`tests/uat/self_check_uat.md`

**PRD:** `../Refinement/SELF_CHECK_PRD.md` · **Decision:** D71 · **Design and wording:**
`product/design/d71_self_check_questions.html`

**Depends on A6** — the page's only exit is the application flow, and a quiz whose only exit is the
`contact details to confirm` chips is a deeper dead end than the one it replaces. **Does not depend
on C2**: the prefill handoff is `C2a`, so A8 is never blocked on the questionnaire renderer.

**Tests first**

```python
def test_nothing_is_stored_without_consent(client, payload):
    client.post(reverse("core:before_you_apply"), payload)          # neither consent ticked
    assert SelfCheckReport.objects.count() == 0
    assert not SelfCheckDemographic.objects.exists()

def test_research_consent_writes_one_row_and_stores_no_identifier(client, payload):
    client.post(reverse("core:before_you_apply"), {**payload, "research_consent": "on"})
    report = SelfCheckReport.objects.get()
    assert not report.member_id and not report.farm_id        # there is no such field to set

def test_demographic_consent_is_refused_without_research_consent(client, payload):
    r = client.post(reverse("core:before_you_apply"),
                    {**payload, "demographic_consent": "on", "census_gender": "F"})
    assert r.status_code == 200 and not SelfCheckDemographic.objects.exists()

def test_withdraw_deletes_both_rows(client, consented_report):
    withdraw(consented_report.public_uuid)
    assert not SelfCheckReport.objects.exists() and not SelfCheckDemographic.objects.exists()

def test_the_two_fixed_lines_come_from_the_finalise_gate_constant():
    # §5.8: a MISSING record is a record, not a blocker. The public promise and the gate
    # use one constant, so changing one cannot leave the other behind.
    assert MISSING_RECORD_BLOCKS_FINALISE is False
    assert evaluate({}).fixed_lines["missing_record"] == MISSING_RECORD_IS_A_RECORD_NOT_A_BLOCKER

def test_the_land_history_note_prints_both_thresholds(result_html):
    assert "12 months" in result_html and "18 months" in result_html
    assert "not yet settled" in result_html          # D31 is shown, never resolved

def test_rather_not_say_produces_no_todo_item_and_is_not_counted_missing(result):
    assert all(item.key != "B5" for item in result.todo)
    assert result.records_missing == 0

def test_a_non_crops_category_gets_a_caveat_not_an_empty_form(client):
    r = client.post(reverse("core:before_you_apply"), {"success": "on", "categories": ["ANIMAL"]})
    assert "still being written" in r.content.decode()

def test_the_page_states_no_eligibility_claim(client):
    html = client.get(reverse("core:before_you_apply")).content.decode().lower()
    for term in ("you are ready", "you qualify", "you are eligible", "approved"):
        assert term not in html

def test_every_todo_citation_resolves_or_is_declared_text_only():
    for item in evaluate(ALL_NO).todo:
        if item.citation.kind == "TEXT_ONLY":
            assert item.citation.label in TEXT_ONLY_CITATIONS   # a reviewed list, not a shrug
        else:
            assert item.citation.anchor in corpus_anchors()      # D68's rule, enforced
```

**Then** implement in this order: models + migration; `SELF_CHECK_ITEMS` and `build_check`; `evaluate`
(a frozen `SelfCheckResult`, no writes); `submit` (atomic, two tables, consent-gated); `withdraw`;
the form, view, template and `Page` entry; `report_self_check` with `--min-count` (default 5) and
`--demographics`. Per-IP throttle via the `/ask/` mechanism plus a honeypot. The route joins
`PAGES`, so the existing claim-discipline sweep covers it from the first render.

**Acceptance:** every guard above passes **and was proved by breaking it**; nothing is written with no
consent; the page has no advice copy of its own; `report_self_check` refuses a cell under the
threshold. UAT (judgement only): does the result read as a mirror or a verdict, is the land-history
note comprehensible to someone who has never read the OPP, does "Rather not say" feel like a real
answer, does the consent read as a real choice, and does it work one-handed in sunlight.

---

# Sub-plan B — Templates (the irreversible core)

### Task B1: The template model and the v1 schema

**Files:** `core/models/_assessment.py` (`AssessmentTemplate`), `core/services/_templates.py`,
`core/tests/test_template_schema.py`

**Tests first:** a template with a duplicate `key` is rejected; a `key` not matching
`^[a-z_]+\.(V\d{2}[a-z]?|Q\d+(\.\d+)?)$` is rejected; a verdict with `polarity` missing is rejected;
`standard_ref` may be null; a schema with `schema_version != 1` is rejected; a question's optional
`self_check` block (`{"tier": 1, "why": "..."}`) is accepted, and an unknown key inside it is not
(**D71** — the public self-check derives twelve of its controls from this schema, so the wording has
one home; see `../Refinement/SELF_CHECK_PRD.md` §4.6).

**Then** implement `AssessmentTemplate(category, version, standard_version, schema, effective_from,
is_active)` plus `validate_schema(dict) -> list[str]` returning human-readable problems rather than
raising on the first one — an author needs the whole list.

**Acceptance:** validation returns every problem in one pass; a valid Crops schema returns `[]`.

---

### Task B2: Versioning rules

**Files:** `core/services/_templates.py`, `core/tests/test_template_versioning.py`

**Tests first:** activating a template for a category deactivates the previous one for that category
only; an inactive template cannot be used to start an assessment; two active templates for one category
is an error.

**Acceptance:** only one active template per category at any time.

---

### Task B3: Author the Crops template

**Files:** `core/templates_data/crops.v1.json`, `core/tests/test_crops_template.py`

Hand-authored from FORM Sheet B.1 (D28). **This is the task that must not be rushed.**

**Tests first — completeness and the known defects:**

```python
def test_crops_template_matches_the_workbook():
    s = load_crops_schema()
    assert len([q for sec in s["sections"] for q in sec["questions"]]) == 38
    assert len(s["verdicts"]) == 37

def test_the_duplicate_v32_is_keyed_twice_but_printed_once():
    refs = [v["key"] for v in load_crops_schema()["verdicts"]]
    assert "crops.V32a" in refs and "crops.V32b" in refs
    assert {v["ref"] for v in load_crops_schema()["verdicts"] if v["key"].startswith("crops.V32")} == {"V32"}

def test_known_gaps_are_declared_not_silent():
    s = load_crops_schema()
    assert s["allowed_ref_gaps"] == ["V15", "V31"]
    assert not any(v["ref"] in ("V15", "V31") for v in s["verdicts"])

@pytest.mark.parametrize("key", ["crops.V03", "crops.V16", "crops.V23"])
def test_inverted_and_informational_verdicts_carry_the_right_polarity(key):
    pol = {v["key"]: v["polarity"] for v in load_crops_schema()["verdicts"]}
    assert pol[key] != "POSITIVE"
```

**Also author the twelve `self_check` markers** (D71): Q4.2, Q5.1, Q11.1, Q11.2, and the seven
Sheet I §2 records, each with a `why` sentence naming its clause. The public page renders these
questions from the schema, not from a copy — so a wording change at the visit reaches the front door,
and `test_selfcheck.py::test_every_derived_control_resolves` fails if a marker points at a question
that does not exist. The count is asserted: **twelve**.

**Then** author all 38 questions across PART A (general information) and PART B (crop production),
marking `respondent` per the FORM's grey/white cells, `attachments` for the documents Sheet I §2
requires, and `links_to: "INPUT_REGISTER"` on B.1 Q4.3.

**Sub-verdicts are structured, not prose.** Six verdicts carry printed child rows: V4 (2), V10 (2),
V11 (2), V19 (3), V21 (2), V35 (2) = 13 children. Each child is
`{"key": "crops.V04.a", "text": "…", "polarity": "POSITIVE", "options": ["YES","NO","NA"], "required": true}`.
A child key is the parent key plus `.a`/`.b`/`.c`; a child never gets its own top-level verdict row
(the 37-row count is the completeness invariant).

```python
def test_the_six_sub_verdict_groups_are_structured():
    subs = {v["key"]: v.get("sub_questions", []) for v in load_crops_schema()["verdicts"]}
    assert {k for k, v in subs.items() if v} == {
        "crops.V04", "crops.V10", "crops.V11", "crops.V19", "crops.V21", "crops.V35"
    }
    assert all(isinstance(q, dict) and q.get("key") for group in subs.values() for q in group)
    assert sum(len(group) for group in subs.values()) == 13
```

**Polarity assignment — get these right or the data lies:**

| Verdict | Polarity |
|---|---|
| V3 "Is there need for a transition period?" | `INFORMATIONAL` |
| V16 "Are there any risks of contamination of the water source?" | `NEGATIVE` |
| V23 "Do you see evidence of pests or pest damage?" | `NEGATIVE` |
| all others | `POSITIVE` |

**Acceptance:** the template tests pass; a reviewer reads the JSON against the printed sheet and finds
no omission. **This is the one task worth a second pair of eyes.**

---

### Task B4: `load_template`

**Files:** `core/management/commands/load_template.py`, `core/tests/test_load_template.py`

**Tests first:** loads `crops.v1.json` and creates one `AssessmentTemplate`; running twice is
idempotent on `(category, version)`; an invalid schema prints every problem and exits non-zero without
writing.

**Acceptance:** `python manage.py load_template core/templates_data/crops.v1.json` is re-runnable.

---

# Sub-plan C — Pre-visit questionnaire (Flow B)

### Task C1: Assessment and answers

**Files:** `core/models/_assessment.py` (`Assessment`, `AssessmentAnswer`),
`core/tests/test_assessment.py`

**Tests first:** `Assessment.template_schema` is a **copy**, not a reference — mutating the
`AssessmentTemplate` afterwards must not change it (`copy.deepcopy`); `AssessmentAnswer` is unique on
`(assessment, question_key)`; saving an answer twice updates rather than duplicates.

---

### Task C2: Questionnaire render and autosave

**Files:** `core/views/_portal.py`, `core/forms/_questionnaire.py`,
`core/templates/portal/questionnaire.html`, `core/tests/test_questionnaire.py`

**Tests first:** only `respondent == "FARMER"` questions render; an `ADMINISTRATOR`-only verdict never
appears; a `POST` to the autosave endpoint returns 204 and persists one answer; autosave is
`transaction.atomic()` and keyed by `question_key`; an invalid `question_key` for that template is 400.

HTMX for autosave (already permitted, D1) — one vendored file, no build step.

**Acceptance:** render test passes for Crops; autosave survives a simulated browser refresh.

---

### Task C2a: Carry the self-check answers into the questionnaire

**Files:** `core/services/_selfcheck.py`, `core/views/_portal.py`, `core/tests/test_selfcheck_prefill.py`

**Deliberately after A8 and C2, and A8 is not blocked on it.** The public self-check (A8, D71) asks
twelve questions that are also questions on the frozen Crops template. A farmer who completed the
check should not answer them twice.

**Tests first:** an applicant who completes the check and then registers sees the questionnaire's
matching questions pre-filled; a pre-filled answer is a **draft** (`AssessmentAnswer` with the
answer's own provenance), never a submitted one; editing the questionnaire changes nothing about the
`SelfCheckReport`; a farmer who never did the check sees an empty form and no error.

**Then** match on `question_key` against the template's `self_check` markers, copy the farmer's
declared answers into drafts, and mark each pre-filled row with its source. Nothing is inferred: a
`RATHER_NOT_SAY` answer arrives **unanswered**, not as a "no".

**Acceptance:** the twelve matching answers arrive as drafts; a `RATHER_NOT_SAY` answer leaves its
question blank; the report is never mutated by the portal.

---

### Task C3: Attachments and readiness

**Files:** `core/models/_assessment.py` (`EvidenceDocument`), `core/services/_assessment.py`,
`core/tests/test_attachments.py`

**Tests first:** a question declaring `attachments: ["SOIL_TEST"]` is unsatisfied until an
`EvidenceDocument` of that `kind` exists for the assessment; the readiness checklist counts
unsatisfied required attachments; unlisted kinds are rejected.

**Then** implement `EvidenceDocument(farm_visit?, assessment?, member?, kind, title, file, sha256,
uploaded_by, uploaded_at, is_private)`. `is_private=True` by default; dossiers stay private (§12, D22).

**Acceptance:** readiness is a single service call returning a frozen dataclass, not template logic.

---

### Task C4: Submit, snapshot, notify

**Files:** `core/services/_assessment.py`, `core/tests/test_questionnaire_submit.py`

**Tests first — the spec's "single most important data-integrity rule":**

```python
def test_template_edit_after_submit_does_not_touch_the_assessment(assessment):
    before = assessment.template_schema
    tpl = assessment.template
    tpl.schema["verdicts"][0]["text"] = "EDITED"
    tpl.save()
    assessment.refresh_from_db()
    assert assessment.template_schema == before
```

Also: submit sets `QUESTIONNAIRE_SUBMITTED`; submit with an unsatisfied required attachment is refused;
submit snapshots `template_schema` exactly once (a second submit does not re-snapshot).

---

### Task C5: Clarification loop

**Files:** `core/services/_assessment.py`, `core/views/_committee.py`,
`core/tests/test_clarifications.py`

**Tests first:** an administrator can raise a clarification on a specific `question_key`; it appears in
the farmer's task list; resolving it returns the assessment to `QUESTIONNAIRE_SUBMITTED`; a
clarification cannot be raised after the snapshot is frozen.

Modelled as `ClarificationRequest(assessment, question_key, text, raised_by, raised_at, resolved_at)`.

---

### Task C6: Corrective-action follow-up (farmer portal)

**Files:** `core/views/_portal.py`, `core/services/_corrective.py`,
`core/templates/portal/tasks.html`, `core/tests/test_corrective_followup.py`

**Tests first:** a farmer sees only corrective actions belonging to their own farms; each row shows the
reason, recommended action and `due_on`; `OVERDUE` is derived from `due_on` on read, never stored; an
upload creates an `EvidenceDocument` with `corrective_action` set and moves the action to `SUBMITTED`
with `submitted_on`; a farmer cannot move an action to `VERIFIED`; a deleted document does not delete
the action (void/deactivate, never delete).

The upload is the same `EvidenceDocument` pipeline as C3, with one extra nullable FK. No new storage
code.

**Acceptance:** the Homtini Major action — *"provide these documents for review in 2 weeks"* — can be
answered by the farmer and verified by the administrator without email.

---

# Sub-plan D — Scheduling and committee validation

### Task D1: Visit and participants

**Files:** `core/models/_assessment.py` (`FarmVisit`, `VisitParticipant`),
`core/tests/test_visit.py`

**Tests first:** the status machine rejects `DRAFT → IN_FIELD`; a visit carries a unique
`client_uuid`; `VisitParticipant.role` accepts exactly the eight OPP §3.3 roles; the host farmer is
always a participant; `review_due_on` defaults to `visited_on + 5 days` (OPP §4.2(5)).

Status path in 1a: `DRAFT → SCHEDULED → IN_FIELD → SYNCED → UNDER_REVIEW`. `DECIDED`, `CLOSED` are
MVP 2; `ABANDONED` is reachable from any non-terminal state.

---

### Task D2: `validate_assessment_team()`

**Files:** `core/services/_assessment.py`, `core/tests/test_team_validation.py`

**Tests first — one test per OPP clause:**

```python
def test_minimum_four_people(visit):            # OPP §3.3
    add(visit, PEER_FARMER, PEER_FARMER, CONSUMER)
    with pytest.raises(TeamCompositionError): validate_assessment_team(visit)

def test_two_peer_farmers_required(visit):      # OPP §4.1.2
    add(visit, ADMINISTRATOR, PEER_FARMER, CONSUMER, CONSUMER)
    with pytest.raises(TeamCompositionError): validate_assessment_team(visit)

def test_observers_do_not_count_toward_the_four(visit):
    add(visit, ADMINISTRATOR, PEER_FARMER, PEER_FARMER, OBSERVER)
    with pytest.raises(TeamCompositionError): validate_assessment_team(visit)

def test_single_consumer_rep_passes_but_warns(visit):   # OPP §3.3 vs §3.1
    add(visit, ADMINISTRATOR, PEER_FARMER, PEER_FARMER, CONSUMER)
    result = validate_assessment_team(visit)
    assert result.ok
    assert any("two consumer representatives" in w for w in result.warnings)
```

Plus: exactly one administrator; observers ≤ farm maximum; technical expert required when no
participant's `Member.expertise` covers the assessed category; administrator holds `ADMIN` or the
`FARM_VISIT_ADMINISTRATION` position.

**Return a frozen dataclass** `TeamValidation(ok: bool, errors: list[str], warnings: list[str])` — the
two-consumer rule is a warning, never an error (PRD §5.4).

---

### Task D3: Notice rules and the fee gate

**Files:** `core/services/_assessment.py`, `core/tests/test_previsit_rules.py`

**Tests first:** scheduling 4 days ahead fails, 5 days passes (OPP §4.1(1)); freezing the questionnaire
2 days before the visit fails, 3 days passes (OPP §4.1(2)); `confirm_visit` fails while the
`AssessmentFee` is unpaid (D32) or the member is not paid up (OPP §2.3).

---

### Task D4: Scheduling UI

**Files:** `core/views/_committee.py`, `core/forms/_committee.py`,
`core/templates/committee/schedule_visit.html`, `core/tests/test_schedule_view.py`

**Tests first:** the form refuses to submit with an invalid team and shows every error at once;
successful scheduling writes the visit, participants and a notification.

**Acceptance:** a committee member can schedule a valid visit end to end in one test.

---

# Sub-plan E — Connected capture and findings

### Task E1: Verdicts and polarity

**Files:** `core/models/_assessment.py` (`AssessmentVerdict`), `core/services/_evaluation.py`,
`core/tests/test_evaluation.py`

**Tests first — the derivation table, exhaustively:**

```python
@pytest.mark.parametrize("value,polarity,expected", [
    ("YES", "POSITIVE", True), ("NO", "POSITIVE", False),
    ("YES", "NEGATIVE", False), ("NO", "NEGATIVE", True),
    ("YES", "INFORMATIONAL", None), ("NO", "INFORMATIONAL", None),
    ("NA",  "POSITIVE", None),  (None, "POSITIVE", None),
])
def test_compliance_derivation(value, polarity, expected):
    assert derive_compliance(value, polarity) is expected

def test_no_view_can_write_is_compliant(client, ...):
    # is_compliant is not in any ModelForm's fields
    assert "is_compliant" not in RecordVerdictForm().fields

def test_stored_value_matches_recomputation(recorded_verdicts):
    for v in recorded_verdicts:
        assert v.is_compliant is derive_compliance(v.value, v.polarity)

def test_sub_answers_are_kept_separate_from_the_parent(recorded_verdict):
    v = recorded_verdict
    v.sub_answers = {"crops.V04.a": "NO", "crops.V04.b": "YES"}
    v.save()
    v.refresh_from_db()
    assert v.value == "YES"                       # parent untouched
    assert v.sub_answers["crops.V04.a"] == "NO"   # child preserved
```

`derive_compliance` lives in `core/services/_evaluation.py`; the model's `save()` materialises it from
the snapshotted `polarity`. `AssessmentVerdict(assessment, question_key, ref, value, polarity,
is_compliant, standard_ref, notes, sub_answers)`.

**Acceptance:** all eight parameter cases pass; no form exposes `is_compliant`; a child answer never
changes the parent's `value` or `is_compliant`.

---

### Task E2: Findings and notifiable exemptions

**Files:** `core/models/_assessment.py` (`Finding`, `NotifiableExemption`),
`core/services/_evaluation.py`, `core/tests/test_findings.py`

**Tests first:** severity is exactly `MINOR | MAJOR | CRITICAL`; the three definitions are returned
**verbatim** from FORM Sheet I and asserted character-for-character in a test; a `Critical` finding
requires a corrective action; a `NotifiableExemption` requires `standard_ref`, `granted_by` and
`rationale`; `reported_to_pgs_sa_on` may be null at creation but **blocks visit closure** later (F4).

**Acceptance:** the verbatim-wording test is the guard against paraphrase drifting into the UI.

---

### Task E3: Corrective actions

**Files:** `core/models/_assessment.py` (`CorrectiveAction`), `core/tests/test_corrective_actions.py`

**Tests first:** status transitions `OPEN → SUBMITTED → VERIFIED`; `OVERDUE` is derived from `due_on`
(never stored as a manual state); an action cannot be deleted, only closed (immutable history); a
lapsed Critical action sets `ESCALATED`.

---

### Task E4: Signatures

**Files:** `core/models/_assessment.py` (`Signature`), `core/services/_storage.py`,
`core/tests/test_signatures.py`

**Tests first:** three roles are expected (`ASSESSOR`, `HOST_FARMER`, `PGS_REPRESENTATIVE`); the
signature is stored under the **private** media root; `ip_hash` is stored, never the raw IP; a
signature cannot be deleted; a `declined` signature requires `decline_reason` and is distinguishable
from a missing one.

---

### Task E5: Evidence photos

**Files:** `core/models/_assessment.py` (`EvidencePhoto`), `core/services/_media.py`,
`core/tests/test_evidence_photos.py`

**Tests first:** magic-byte validation rejects a `.jpg` that is a PDF; the size cap applies; `sha256`
is recorded; original retained and a ≤2048px derivative generated; `client_media_uuid` is unique so a
replay returns the existing row (this is the seam's behaviour, exercised here directly).

Adapted from MVP 0's `store_media_item` contract; keep the same idempotency semantics.

---

### Task E6: Input register (FORM B.2)

**Files:** `core/models/_assessment.py` (`InputSupply`), `core/forms/_assessment.py`,
`core/templates/committee/input_register.html`, `core/tests/test_input_register.py`

**Tests first:** a row requires `product_name`; `act36_registered` is tri-state (`True`/`False`/`null`
= not stated) because the form asks but does not guarantee an answer; `input_kind` is required and
drives `seed_status` (a `SEED` row must have `ORGANIC | CONVENTIONAL_UNTREATED | CONVENTIONAL_TREATED |
UNKNOWN | NA`; a non-seed row leaves it null); `ingredients` is required when `is_organic_certified` is
`False`; rows persist across visits for the same farm.

**Acceptance:** the register opens from B.1 Q4.3 (`links_to: "INPUT_REGISTER"`) and round-trips a row
with all nine Sheet B.2 columns. Supplier documents attach to the row through
`EvidenceDocument.input_supply`; the assessor can mark the row `APPROVED`/`REJECTED` with a rationale
(the paper form's *"check with Fabian if the planned product is acceptable"*).

---

### Task E7: Capture UI

**Files:** `core/views/_committee.py`, `core/forms/_assessment.py`,
`core/templates/committee/capture.html`, `core/tests/test_capture_view.py`

Renders the frozen snapshot: questions for the administrator (the FORM's grey cells) beside the
farmer's answers (white cells), a verdict control per `V#` with the helper text and the polarity's
implied meaning, and inline finding creation with the verbatim severity definitions.

**Tests first:** the capture view reads **only** `assessment.template_schema` (a test replaces the live
template with a different one and asserts the page is unchanged); the verdict control offers exactly
`options` from the template; a `NEGATIVE` verdict is labelled so "Yes" does not read as praise; a
parent with `sub_questions` renders one control per child, each with its own key; the conclusion
sections render beside the findings (social equity, records checklist, prior actions).

**Acceptance:** one connected visit can be captured end to end in a test, reaching `SYNCED`, with every
sub-verdict and every Sheet I §1–2 item recorded.

---

### Task E8: Sheet I conclusion — social equity and records

**Files:** `core/models/_assessment.py` (`SocialEquity`, `RecordCheck`),
`core/forms/_assessment.py`, `core/templates/committee/conclusion.html`,
`core/tests/test_conclusion.py`

**Tests first:** `SocialEquity` is unique per visit; `children_under_15=True` requires
`children_activities`; the worker and child-labour fields are flagged sensitive and excluded from every
public serialiser; `RecordCheck` is unique on `(farm_visit, kind)`; every printed Sheet I §2 kind is
created when the visit enters capture (missing is `MISSING`, not absent); `MISSING` requires a note;
`NOT_APPLICABLE` is allowed for the agro-processing items when the category is not assessed.

**Acceptance:** a visit cannot be finalised with an unset `RecordCheck` or no `SocialEquity` row; a
`MISSING` sales-record row is recorded and rendered, and does not itself block the visit.

---

### Task E9: Prior-action review

**Files:** `core/models/_assessment.py` (`PriorActionReview`), `core/views/_committee.py`,
`core/tests/test_prior_actions.py`

**Tests first:** the capture screen lists every `OPEN`/`OVERDUE`/`ESCALATED` action from the farm's
previous visits; one `PriorActionReview` per `(farm_visit, corrective_action)`; outcome is exactly
`VERIFIED | PARTIAL | NOT_MET`; a `NOT_MET` Critical action sets `ESCALATED`; a review cannot be
recorded against another farm's action.

**Acceptance:** the Homtini Critical action (ducks not certifiable) and Major action (documents
outstanding) both appear at the next visit and must be closed or escalated before finalise.

---

# Sub-plan F — Visit report

### Task F1: WeasyPrint and the report template

**Files:** `core/templates/pdf/visit_report.html`, `core/static/css/pdf.css`,
`core/tests/test_pdf.py`

**First action of this sub-plan: install WeasyPrint and confirm it renders on this machine.** It was
deliberately deferred from MVP 0 (D19) because of GTK system libraries on Windows; discovering that at
the end of 1a is avoidable pain.

**Tests first:** the rendered HTML contains every finding with its description and severity; every
answered sub-verdict with its child text; a `MISSING` `RecordCheck` with its note; the social-equity
section; and the prior-action review table. Citations of the four outcome options appear as
**pending**, not selected (D33); no cell number, email, GPS or child-labour detail appears; the PDF is
generated without a partially-written file on failure.

---

### Task F2: `finalise_visit`

**Files:** `core/services/_pdf.py`, `core/tasks/_pdf.py`, `core/tests/test_finalise.py`

**Tests first:** idempotent on `visit_id` (a second call produces no second PDF row); sets
`SYNCED → UNDER_REVIEW`; refuses when the photo queue is outstanding; refuses while a
`NotifiableExemption` lacks `reported_to_pgs_sa_on`.

**Acceptance:** finalise twice → one PDF, status `UNDER_REVIEW`.

---

### Task F3: Completeness and signature gates

**Files:** `core/services/_pdf.py`, `core/tests/test_finalise_gates.py`

`finalise_visit` returns **every** unmet item, not the first, so the administrator can fix the visit in
one pass. Refuse when:

- a required `AssessmentVerdict.value` is `NULL`;
- a required `sub_questions` child is `NULL` in `sub_answers` (`NA` is an answer);
- a required `Signature` is missing and no refusal with a reason is recorded;
- a `RecordCheck` has no `status`, or a `MISSING` one has no note;
- a `SocialEquity` row is absent;
- a prior open `CorrectiveAction` has no `PriorActionReview` for this visit;
- the photo queue is outstanding or a `NotifiableExemption` is unreported (existing F2 rules).

**Acceptance:** a Homtini-shaped visit — blank V5, V11's supplier child and V25, missing applicant
signature, missing sales record, unreviewed prior action — is refused with every gap named, not a
generic error. The suite asserts the list, not a boolean.

---

# Sub-plan G — Seam: pack producer and sync API

> **GATED (D26).** Do not start until `0∥` completes and `1∥` freezes `visitPack` v1 and
> `VisitSyncEnvelope` v1. These tasks are listed so the plan is complete, not so they can be
> reordered. Nothing in A–F depends on them.

### Task G1: Contract schemas and contract tests

**Files:** `contracts/visit_pack.v1.json`, `contracts/visit_sync_envelope.v1.json`,
`core/tests/test_contracts.py`

**Tests first:** the producer's output validates against the pack schema; a valid envelope validates
and an envelope missing `client_uuid` does not; a round-trip through the schema is lossless.

---

### Task G2: `visitPack` producer

**Files:** `core/services/_assessment.py`, `core/views/_committee.py`

Emits: frozen template snapshots, farm metadata, prior-visit findings and open corrective actions
(PREP requires these at the start of a visit), participants, and the farm's input register.

**Tests first:** the pack contains only `respondent`-relevant data and **no** census fields; a pack
built from a frozen assessment carries the snapshot, not the live template.

---

### Task G3: `sync_visit_text`

**Files:** `core/services/_sync.py`, `core/views/_api.py`, `core/tests/test_sync.py`

**Tests first:** the spec's headline guarantee —

```python
def test_replay_creates_zero_additional_rows(envelope):
    r1 = sync_visit_text(envelope)
    before = count_all_rows()
    r2 = sync_visit_text(envelope)          # same client_uuid
    assert count_all_rows() == before
    assert r2 == r1
```

Plus: writes `SyncReceipt` · `FarmVisit` · `Assessment*` · `Finding` · `Signature` in **one**
`transaction.atomic()`; an unknown template version raises `UnknownTemplateVersionError`; a payload
violating the frozen schema raises `SchemaValidationError`; a non-paid-up member raises
`MembershipNotEligibleError`.

---

### Task G4: `store_media_item`

**Files:** `core/services/_media.py`, `core/views/_api.py`, `core/tests/test_media_sync.py`

**Tests first:** replay on `client_media_uuid` returns the existing row and writes nothing; media for a
visit that does not exist yet is rejected (ordering guarantee, spec §10.5); magic-byte and size checks
reuse E5's validators rather than duplicating them.

---

### Task G5: Finalise endpoint

**Files:** `core/views/_api.py`, `core/tests/test_api_finalise.py`

**Tests first:** out-of-order finalisation (before text) is rejected; a second finalise is idempotent;
`X-Request-ID` propagates into the enqueued task.

---

## 2. Order of execution

| Step | Tasks | Gate |
|---|---|---|
| 1 | A1 → A2 → A3 → A4 → A5 | `pytest` green; fees and gates correct |
| 2 | A6 → A7 | Application completes end to end |
| 3 | B1 → B2 → B3 → B4 | Crops template validates; **B3 reviewed against the printed sheet** |
| 4 | C1 → C2 → C3 → C4 → C5 → C6 | Questionnaire completes; snapshot immutability proven; farmer can answer a finding |
| 5 | D1 → D2 → D3 → D4 | Team validation passes one test per OPP clause |
| 6 | E1 → E2 → E3 → E4 → E5 → E6 → E7 → E8 → E9 | A connected visit reaches `SYNCED` with the conclusion and prior actions |
| 7 | F1 → F2 → F3 | Report PDF renders; visit reaches `UNDER_REVIEW`; incomplete visits are refused |
| 8 | **UAT** | The PRD §7 human judgements signed (all scenarios) |
| — | G1 → G5 | **Blocked on `1∥`** |

**In parallel:** sub-plan A can begin immediately; the 0∥ spike runs alongside and must complete before
`1∥`. Sub-plan G is the only part that waits.

---

## 3. Definition of done

- [ ] An application completes: register → consent → pledge → categories → turnover → attestations → fees
- [ ] A visit cannot be scheduled with an invalid team, inside 5 days, or with unpaid fees
- [ ] The questionnaire renders only farmer questions, autosaves, and freezes its snapshot on submit
- [ ] A connected visit captures verdicts (with correct polarity and sub-answers), findings, corrective
      actions, signatures, photos, the input register, the Sheet I conclusion and prior-action reviews,
      reaching `SYNCED`
- [ ] A farmer can submit evidence against a corrective action; the reviewer can verify it
- [ ] `finalise_visit` produces the visit report PDF, refuses an incomplete visit by naming every gap,
      and reaches `UNDER_REVIEW`
- [ ] No certification outcome, seal or certificate exists anywhere in 1a
- [ ] The UAT judgements in PRD §7 are signed
- [ ] `lint-imports` green; `/health/` 200; full suite green

## 4. Not built here

| Not built | Why | Arrives |
|---|---|---|
| Service worker, IndexedDB, offline capture | 1b (D25) | MVP 1b |
| Templates for Animal Husbandry, Seed, Agro-processing | Prove one category first (D28) | 1b+ |
| Certification decision, outcomes, seals, certificates | 1a stops at `UNDER_REVIEW` (D33) | MVP 2 |
| Registry, QR, verification | Nothing to verify yet | MVP 2 |
| Voice notes (recorder, transcription) | Schema ships; pipeline deferred (§17.2) | post-MVP |
| Reporting, gap analysis, census exports | No accumulated data yet | MVP 3 |
| Aggregation workflow, discipline workflow | §17.1 / D13 | out of scope |
