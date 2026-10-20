# Refinement: The Regenerative Add-On — architecture findings, and what to decide before MVP 2

**Status:** Refinement — target shape agreed (A, §2); implementation paused until the standard itself exists. Three decisions are nonetheless time-sensitive (§8), because MVP 1a and MVP 2 will otherwise freeze them by accident.
**Owner:** Kobus Meiring (Product)
**Last Updated:** 2026-10-19
**Scope:** How a second, add-on certification **scheme** sits on top of the base PGS organic
certification for the same farm. **Not in scope:** the add-on's criteria, its questionnaire
content, its fee, or its launch — none of which can be written yet.
**Reference:**
- `PGS_PLATFORM_SPEC.md` §4.2, §4.2.1 (D27 keys), §4.3 (Seal), §4.8 (code vs data), D11/F3
- `ready/MVP1A_PRD.md` §1 (the template schema freezes at the first captured visit) and §9
  ("C1 — seal cardinality" is open, deferred to MVP 2 modelling)
- `core/models/_certification.py`, `core/services/_certification.py`,
  `core/services/_seed.py`, `core/tests/test_claim_discipline.py`
- Companion: `REGENERATIVE_ADDON_ARCHITECTURE.md` sits beside
  `SAOSA_MULTI_BRANCH_READINESS.md` — §5 L2 (`Seal.issuer`) is shared between the two

> **Written with another agent live in the tree.** This file is new and touches nothing else.
> As in the companion document: `backlog.md` is generated, and **`D45` is allocated twice**
> (`ready/CORPUS_COLUMN_EXTRACTION_PRD.md` §9 and `ready/MVP1A_PRD.md` §5.8). This document
> proposes **D47**, leaving D45 to its owners.

---

## 1. The idea, and why it is not being built yet

A farm is certified to the base PGS organic standard. A **Regenerative Add-On** would let that
same farm additionally be assessed against regenerative criteria, and be endorsed or refused on
that basis independently of the base outcome — without a second membership, a second farm
record, or a second visit necessarily.

Two things are true at once:

- **The shape is clear enough to design** (§4–§7). It is one dimension the model does not have,
  and the gaps are enumerable.
- **Nothing can be built.** The group has not written the criteria, so there is no questionnaire,
  no seal with `criteria_defined=True`, and no defensible wording. Building the schema before
  the standard is exactly the mistake D11/F3 already recorded for `PGS_PASTURE_RAISED` — a real
  mark whose criteria the OPP itself calls *"forthcoming"*, shipped as an **inactive row** and
  blocked from issuance **unconditionally**.

So: design now, build later, and protect the three things that would be expensive to change
after evidence exists (§8).

## 2. Agreed shape

Product owner, 2026-10-19: **shape A — a group-defined add-on.** Outeniqua writes the
regenerative criteria, the questionnaire and the seal, as its own instrument layered on the base
certificate; the aspiration is that SAOSA/PGS SA recognises it broadly.

Rejected shapes, recorded so they are not re-proposed:

| Shape | Why not |
|---|---|
| **B** — an external scheme the platform only *records* (like `PriorCertification`, FORM Sheet A) | Needs no model change at all, but yields no endorsement. It is the correct interim state (a farm may hold an external regenerative certificate and PGS may record the reference), not the target |
| **C** — a ladder assessed on its own visit | Legitimate, and the simplest schema (a `programme` FK on `FarmVisit`/`Assessment`). It is a *process* choice, not an architectural one; revisit only if the criteria demand a separate visit |
| **D** — a market-facing badge with no assessment behind it | This is the pasture-raised failure with a different adjective. Do not |

## 3. Why it cannot be faked with what exists

There are two shortcuts available today, and both are wrong in ways that are hard to undo:

**Not a `Category`.** `Category` is FORM Sheets A–H (`_seed.py:132` `CATEGORIES`:
`CROPS`, `ANIMAL_HUSBANDRY`, `SEED_PRODUCTION`, `AGRO_PROCESSING`, plus three inactive). It is
the axis a visit is assessed *on*, and it owns the key namespace:
`question_key = "<category>.<ref>"`, zero-padded, e.g. `crops.V04` (§4.2.1, D27). An
`ADDON`/`REGENERATIVE` category row would:

- pollute the FORM-derived namespace that 1a is about to freeze permanently;
- break the completeness tests that assert question and verdict counts against the workbook
  (`MVP1A_PRD.md` R1a-3);
- appear in `ProductOutcome.category`, implying the add-on is a *production category* like
  Crops, which it is not;
- make "which categories does this farm apply for?" ambiguous in the questionnaire (Sheet A).

**Not a second seal on the same certificate.** That is precisely the unresolved question:
`MVP1A_PRD.md` §9 **C1 — "Seal cardinality; which seal for 'Organic - pending corrective
action'"**, deferred to MVP 2 modelling. The modeled shape (§4.3) is
`Certificate.decision` + `Certificate.seal` (a single FK) + `ProductOutcome.decision` — one
decision, one certificate, one seal. A split outcome (base passes, add-on deferred; base fails,
add-on moot) cannot be represented by two seals on one certificate, because the certificate
would then be asserting a claim whose own decision does not exist.

## 4. What is free today

| Need | Status | Evidence |
|---|---|---|
| A new mark with no `choices=` change | ✅ free | `Seal` is a row; its docstring refuses `choices=` explicitly |
| An "authorised but unsubstantiated" claim state | ✅ free | `is_active=False` + `criteria_defined=False` + `assert_seal_issuable()` + never rendered publicly. The `PGS_PASTURE_RAISED` pattern (`_seed.py`) is exactly this |
| A separate corpus for the add-on standard | ✅ free | `StandardSet` is a row; retrieval is scoped to a set; `ChatSession` is pinned to one (`_chat.py:63`) |
| Add-on questions as data | ✅ free | `AssessmentTemplate.schema` + `schema_version` |
| A claim guard | ✅ free | `test_claim_discipline.py` — and note the terms list is where the add-on's claim must be gated (§7) |

Three of five needs cost nothing. That is the return on §4.8, and it is why the remaining work
is small and structural rather than large and speculative.

## 5. The five gaps

| # | Gap | Consequence if unaddressed |
|---|---|---|
| **G1** | **No scheme/programme dimension.** One deployment = one implicit scheme. `Seal` has no FK to anything; `Category` has no FK to `StandardSet`; nothing records *which standard authorises which mark* | An add-on can only be faked as a category or a second seal — §3 |
| **G2** | **`Category` is the only scoring axis**, and it owns `question_key` | Add-on keys have nowhere to live that is not the FORM's namespace |
| **G3** | **Seal cardinality is undecided (C1)** | MVP 2 will model `Certificate` with a single `seal` FK by default, and the add-on then needs a data migration over issued certificates |
| **G4** | **`CertificationDecision` is one-per-visit, one outcome** | Split outcomes are unrepresentable |
| **G5** | **`Seal` has no issuing authority** (shared with `SAOSA_MULTI_BRANCH_READINESS.md` §5 L2) | "Outeniqua endorses this" and "SAOSO endorses this" are the same row shape, and the add-on's whole value proposition is that it may be recognised nationally |

## 6. Proposed shape — one dimension, one join, one namespace rule

Sketch only; **no migration until the standard exists** (§9).

```text
Programme            code, label, standard_set(FK -> knowledge.StandardSet),
                     authorising_body, standard_ref, is_active, criteria_defined,
                     display_note, requires_seal(FK -> Seal, nullable)
                     # a row, no choices= — same rule as Seal.code and Category.code

Assessment.programme (nullable FK; NULL = the base programme)
Assessment.category  (made nullable)
                     # CheckConstraint: exactly one of category / programme is set

CertificationDecision.programme   (nullable FK; NULL = the base programme)

CertificateSeal      certificate, seal
                     # replaces Certificate.seal. Closes C1 permanently.
```

**The namespace rule, and it is the only line that must be agreed now:**

> `question_key` stays `<scope>.<ref>`, where `scope` is the **Category code** for the base
> programme (`crops.V04`) and the **Programme code** for an add-on (`regenerative.R01`).

Existing keys are untouched, so no reconciliation migration over `AssessmentVerdict` is ever
needed, and the add-on's numbering can never collide with a FORM `V#`.

**Why `Programme` is not `Category` and not `StandardSet`:** it is the thing that *binds* them
— a second standard, a second seal set and a second questionnaire, applied to the same farm.
`StandardSet` alone is only the corpus (chat can already use it); `Category` alone is only the
FORM axis. The binding is what does not exist.

**Deliberately not added:** any tenant/group key. The add-on is a second scheme inside **one**
deployment. Multi-branch is a separate question with a separate answer
(`SAOSA_MULTI_BRANCH_READINESS.md` §8) — conflating them would drag §IX's single-tenant
blueprint into a design it does not need.

**Reuse when the tables are first built.** `Assessment.programme` and
`CertificationDecision.programme` are nullable FKs with a `NULL = base` meaning. Added at
creation they are cheap; added over live evidence they are a `RunPython` with a backfill. This
is the entire argument for deciding now and building later.

## 7. The claim gate — this is the part that protects the group

`SAOSO v2.1` uses **"regenerative" as an adjective**, never as a mark: *"Organic production and
processing systems are based on the use of natural, biological, renewable, and regenerative
resources"* (principles), and §2.2.3 on returning nutrients *"through the recycling, regeneration
and addition of organic materials"*. **OPP §V authorises three marks, and "regenerative" is not
one of them.**  Occurrence count: `regenerat*` appears in the SAOSO standard only; zero in the
OPP, zero in the Certification Landscape, zero in the FORM, zero in the checklists.

Therefore, until the group publishes criteria:

1. The `Programme` row ships `is_active=False`, `criteria_defined=False`.
2. The seal, if seeded at all, is seeded **inactive** — `assert_seal_issuable()` blocks issuance
   unconditionally, no administrator override (D11/F3).
3. `"regenerative"` is added to `FORBIDDEN` in `test_claim_discipline.py` **the moment** the
   first string mentioning it lands on a public page, and removed only when an active,
   criteria-defined programme exists and a UAT scenario has signed the wording.
4. If SAOSA later endorses the add-on, that is an Appendix C–style approval with a validity
   window — not a sentence on a marketing page. `Seal.issuer` (G5 / L2) is what makes the
   difference expressible.

Point 3 is the cheap, test-enforced version of the honest position, and it is the same
mechanism that already keeps pasture-raised off the site.

## 8. Three decisions that are time-sensitive despite the pause

The pause is on *building*. These three are about not letting future work foreclose the design.
Each is one sentence to whoever is doing that work.

| # | Decision | Owner of the freezing change | Cost of missing it |
|---|---|---|---|
| **P1** | **`question_key` may begin with something that is not a `Category` code.** Nothing in 1a may assume `question_key.split(".")[0]` is a `Category` | MVP 1a — `Assessment.template_schema` is frozen as evidentiary history at the **first captured visit** (`MVP1A_PRD.md` §1, §4.2) | A namespace retrofit over real evidence. This is the single most expensive item in this document |
| **P2** | **C1 is resolved as `CertificateSeal` (M2M), not `Certificate.seal` (FK)** | MVP 2 modelling — `Certificate` does not exist yet | A data migration over issued certificates, or an add-on that can never be issued alongside a base seal |
| **P3** | **`Seal.issuer` exists before the first seal is seeded from a second authority** | Whoever does `SAOSA_MULTI_BRANCH_READINESS.md` §9 step 3 | A group mark and a national mark become indistinguishable rows; claim discipline can no longer tell them apart |

**Proposed D47** — the decision this document asks for, and the only one it needs:

> **The Regenerative Add-On is a `Programme` row, not a `Category` and not a second seal on one
> certificate. `question_key` is `<scope>.<ref>` where `scope` is a Category code for the base
> programme and a Programme code for an add-on. Certificate-to-seal cardinality is many-to-many
> (`CertificateSeal`), resolving C1. No `Programme` row ships active until the group publishes
> criteria, and `assert_seal_issuable` remains the unconditional gate. No tenant dimension is
> introduced: an add-on is a second scheme in one deployment.**

## 9. When the standard arrives — the build path

Nothing below starts until §10 is satisfied. When it is, this is the order, and only step 1 is
a migration:

1. **Schema, before content.** `Programme`, nullable `Assessment.programme`,
   nullable `CertificationDecision.programme`, `CertificateSeal`. All nullable or new; per §I of
   `build_principles.md` this is migration-safe. Existing rows read as the base programme.
2. **Seed.** The `Programme` row (`is_active=False` until criteria are published), its
   `StandardSet`, its seal(s) with `issuer`.
3. **Template.** One JSON file for the add-on's questions, `load_template`. No code change.
4. **Assessment path.** Wherever `Assessment` is created, `programme` is chosen; the finalise
   gates and `validate_assessment_team()` apply unchanged — the add-on does not get a weaker
   process.
5. **Decision path.** A second `CertificationDecision` row per visit, scoped to the programme.
   `FarmVisit.status` and the committee workflow are unchanged; a visit may carry two decisions.
6. **Certificate.** `CertificateSeal` rows; the verification page renders each seal with its
   `issuer` and its own decision, never as an aggregate claim.
7. **Chat.** A second `StandardSet` — already supported — plus a decision about **which corpus a
   session answers from**. `default_standard_set()` assumes exactly one default
   (`core/services/_chatbot.py:285`), so a two-corpus deployment needs an explicit scope choice
   or an attributed combined answer. The D17 refusal wording names *"the SAOSO standard or the
   Outeniqua PGS documents"* and must not silently start covering documents it does not name.
8. **UAT.** A human judges whether an add-on endorsement reads as a claim the group can defend.
   No test replaces that.

An important distinction in step 5: **the add-on's outcome vocabulary is an open question.** §4.8
lists "the four certification outcomes" as **code**, because they are the PGS process. If an
add-on has its own outcome set, then either (a) it reuses the four and stays code, or (b) outcome
vocabulary becomes *data per programme*, which is a genuine bend in the code/data line and needs
to be stated as such rather than discovered mid-build. **Recommendation: (a)** — reuse the four
outcomes until the group's criteria demonstrate that they do not fit.

## 10. What must exist to leave this folder

- [ ] The regenerative standard text, written by the group (the whole blocker)
- [ ] Criteria published and machine-checkable, or an explicit `criteria_defined=False` override
      policy with a recorded rationale
- [ ] A named seal with an `issuer` and a `standard_ref`
- [ ] The questionnaire (a JSON file, per `load_template`)
- [ ] SAOSA/PGS SA's position on the **naming** — "regenerative" as a group mark is a claim, and
      if SAOSA recognises it broadly that is an approval with a validity window, not a sentence
      on a page
- [ ] C1 resolved (P2), and P1 honoured by 1a
- [ ] A UAT scenario drafted for the claim's wording

## 11. Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | **It gets built before the criteria exist**, because the schema is easy and interesting | §10 is the gate. The pasture-raised row is the precedent: `is_active=False` and no override |
| 2 | **The add-on is claimed publicly before it is substantiated** | §7 point 3: `FORBIDDEN` gains the term the moment any public string uses it |
| 3 | **`question_key` is assumed Category-scoped in 1a code**, discovered after evidence exists | P1 — one sentence, now, to the 1a implementer |
| 4 | **`Certificate.seal` gets built as an FK** and C1 is "resolved" by default | P2 — C1 is an MVP 2 modelling input, not a detail |
| 5 | **An add-on is treated as a separate scheme *deployment***, splitting a farm across two databases | §6: one deployment, one farm, two programmes. The branch question is separate |
| 6 | **The add-on dilutes the base claim** — a consumer reads "regenerative" as stronger than "organic" | UAT step 8; the verification page renders each seal with its own decision and issuer, and never an aggregate |
| 7 | **A group-defined add-on is presented as SAOSA-endorsed** before any approval exists | `Seal.issuer` + the Appendix C approval record; until then the issuer is Outeniqua and the page says so |

## 12. Explicit non-goals

- Building anything (§1).
- Deciding the criteria, the fee, the visit model, or the launch date.
- Multi-branch/multi-tenant support — see `SAOSA_MULTI_BRANCH_READINESS.md` §8.
- Replacing or superseding C1; this document *resolves* it as `CertificateSeal` and records why.
