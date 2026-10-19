# PRD: MVP 0 — Standards Foundation & Public Shop Window

**Status:** In Progress — MVP 0 sub-plan A (A1–A10) landed 2026-10-19; sub-plans B, C and D remain. §9 group A closed as D27 and D14–D15. Groups B and C stay open: they are MVP 1 and MVP 2 scope decisions, not MVP 0 blockers.
**Owner:** Kobus Meiring (Product)
**Last Updated:** 2026-10-18
**MVP:** 0 of 0 → 1 → 2 → 3 (`PGS_PLATFORM_SPEC.md` §19)
**Scope:** The public site, the standards corpus, and the grounded chatbot. **No certification claim of any kind.**
**Reference:**
- Target-state spec — `product/backlog/Refinement/PGS_PLATFORM_SPEC.md`
- Implementation plan — `product/backlog/In Progress/MVP0_PLAN_V2.md`
- UAT — `tests/uat/mvp0_standards_and_public_site_uat.md`
- Review artifact — `product/design/mvp0_scope_and_open_questions.html`
- Build rules — `product/docs/context/build_principles.md`
- Source documents — `pgs_docs/` (OPP, SAOSO v2.1, FORM workbook, PREP, checklists, LANDSCAPE, BPP)

---

## 1. Problem Statement

**The general problem.** Outeniqua PGS runs a certification scheme on paper clipboards. The
assessment workbook spans eleven substantive sheets across Crops, Animal Husbandry, Seed
Production and Agro-processing; evidence photos live on someone's phone; corrective actions,
committee decisions and certificates are assembled by hand. Meanwhile the group's public
presence is a WordPress site that *cannot verify a claim it makes* — it currently publishes
"certified pasture raised … GMO free" for a farm whose actual seal does not include either.

**The problem MVP 0 solves is narrower and more urgent than the general problem.** Two
irreducible uncertainties sit underneath every later slice, and both are cheap to test now and
expensive to discover later:

1. **Can the standard be turned into a machine-citable clause model?** The assessment
   templates are *derived from* SAOSO clauses — the FORM's verdicts reference them directly
   (`V1a (S20.1.1)`). If ingestion cannot produce reliable, locatable clause references from
   the real shipped PDFs, then MVP 1's frozen template snapshots and MVP 3's standard gap
   analysis are both built on sand. A 20-minute parser run in review already invalidated
   several plausible assumptions (§9, A-theme), which is the whole argument for doing it first.
2. **Can a chatbot be trusted to refuse?** The group's credibility is staked on a tool that
   says *"I cannot find a definitive answer"* rather than inventing a standard. That is a
   judgement no automated test can make, and it must be tested before the platform holds
   certification data.

**Why now.** The group is being asked to hand over certification records to software. Before
they do, they need to see something they can use and critique, and something that makes no
claim they would have to defend. That is MVP 0.

---

## 2. Strategic Goal

> **Ship a public site and a standards chatbot that answer only from the four governing
> documents, cite them locatably, and refuse when they do not cover the question — while
> publishing no farm status, no certificate, no seal and no QR code.**

**Success looks like:** a committee member opens the site, asks the chatbot about a rest period
for laying hens, gets an answer with a citation they can find in the paper standard, then asks
something the standard does not cover and gets a clean, confident refusal — and concludes the
tool can be trusted with a certification decision later.

---

## 3. What MVP 0 Is Not

Stated as a fence, not an omission. The credibility argument depends on it.

| In MVP 0 | Not in MVP 0 | When |
|---|---|---|
| Public marketing site in the group's own voice | Farm registry, verification pages | MVP 2 |
| Grounded chatbot with citations and structured refusal | Certificates, seals, QR codes | MVP 2 |
| `/documents/` self-hosted governing documents | Farmer accounts, application, pre-questionnaire | MVP 1 |
| Standards corpus: ingest, chunk, embed, retrieve | Offline assessor PWA, split-sync, Sheet J PDF | MVP 1 |
| Bilingual **mechanism** + translated shell | Translated **content** (needs a named reviewer, D18) | post-MVP 0 |
| Foundation: custom `User`, plural roles, `Category`/`Seal` as data, `/health/`, CI, backup + rehearsed restore, import-linter | Reporting, gap analysis, census exports | MVP 3 |
| — | Aggregation workflow, voice notes | post-MVP |

**The credibility rule.** Publishing certification status before the machinery that
substantiates it exists is the one move that could damage the group. MVP 0 therefore makes no
claim, so it cannot make a false one. `core/tests/test_claim_discipline.py` enforces this at the
level of rendered HTML; UAT Scenario 8 enforces it at the level of tone.

---

## 4. Proposed Solution

Four sub-plans. The dependency is real: D needs the corpus, C needs the corpus's citation
format, A gates everything.

### A — Foundation

A deployable, empty, health-checked Django 5.2 monolith: custom `User` with plural `UserRole`,
`Category` and `Seal` as **data** (`seed_deployment`), `/health/` over DB/Redis/broker/worker,
Celery with retry policies, `.importlinter` enforcing `knowledge` ↛ `core`, pytest + Playwright
CI, and backup/restore scripts with a **rehearsed** restore.

**Proves:** the deploy target exists and a restore is real, not assumed (R11).

### B — Standards corpus & retrieval

`ingest_standard` loads the four real PDFs into `StandardDocument` / `DocumentChunk` with
`pgvector` embeddings and a generated `tsvector`; a pluggable section parser per document; a
heading-boundary chunker with `sub_refs` offset mapping; idempotent re-ingest on `sha256`;
hybrid FTS + vector retrieval fused by RRF, scoped to a `StandardSet` **before** ranking.

**Proves:** the clause model works on the documents that exist.

### C — Public site & documents

The group's own public surface: home, the six basic elements (LANDSCAPE), Basic Production
Principles, how to join, fee schedule (OPP §II), members with the "membership is not
certification" disclaimer, contact. `/documents/` with stable URLs, retiring the Google Drive
dependency. Bilingual scaffolding. Vendored HTMX only where it earns its place.

**Proves:** WordPress can be retired and the Drive dependency with it.

### D — Grounded chatbot

`answer_question()` → Gemini with a strict JSON contract (`answer`, `citations[]`,
`insufficient_context`), a citation-validity check against the retrieved set, refusal on the
*flag* rather than on prose, `EscalatedQuery` for follow-up, per-IP rate limiting, 500-char cap,
answer caching, token accounting.

**Proves:** the bot answers from the standard, cites something findable, and refuses convicingly.

### Architectural decisions this PRD introduces (recorded in spec §18.3)

| # | Decision | Consequence for MVP 0 |
|---|---|---|
| D14 | SAOSO cited as `S20.1.1` | Parser targets `20.1.1.` and reads the part letter from running page headers |
| D15 | Citation depth bounded at 3; `sub_ref` + `anchor` | `DocumentChunk.sub_refs` offset map; chunks stay section-level |
| D16 | Corpus = four documents | Workbook and checklists are `/documents/` downloads, not corpus |
| D17 | Wide corpus, group-naming refusal | Refusal string names the group, not just SAOSO |
| D18 | Afrikaans: mechanism + shell | Content waits for a named reviewer |
| D19 | Hosting local; reference deployment is Compose | `docker-compose.yml` for Postgres+pgvector and Redis only |
| D20 | Developer Gemini key via `.env` | Embedding dimension frozen now |
| D21 | Preview, not replacement | WordPress stays live until MVP 2 |
| D22 | Blank forms public; dossiers gated | `/documents/` publishes 7 items, not dossiers |
| D24 | `knowledge/` stays a separate app | Migration namespace argument, not swappability |

---

## 5. Technical Requirements

The load-bearing specifics. Everything else is in the spec; these are the parts an implementer
must not improvise.

### 5.1 Citation model — three layers, never inferred

| Layer | Always present | Examples | Rule |
|---|---|---|---|
| `section_ref` | yes | `V`, `4.2`, `S20.1.1` | Must resolve to text the user can find in the PDF |
| `sub_ref` | no | `§4.1(1)`, `§4.2(5)`, `§4.5(2)(c)` | Emitted **only** where the source enumerates |
| `anchor` | no | `4.5#action-first-warning` | For unnumbered blocks; never a fabricated number |

**Depth is bounded at 3.** Depth 4 does not exist in the source documents and must never be
synthesised — OPP §4.5 has no item 3, its `(c)` attendee list is half-numbered, and the warnings
regime carries no numbers at all.

A citation whose `sub_ref` is absent from its chunk's `sub_refs` map is **invalid**, and that is
a test failure, not a production surprise.

### 5.2 Ingestion must be written against the PDFs, not against expectation

Six realities established by running a parser over the shipped files (spec §4.5 records them in
full):

1. SAOSO part letters are **running page headers**, present on only 22 of 98 body pages, and must
   be carried forward.
2. The **TOC matches the clause pattern** and must be excluded or it ingests as duplicate clauses.
3. The part letter is **mandatory** — 30 clause numbers occur in more than one part.
4. **Appendix headings do not exist in the body**; boundaries come from the TOC page map.
5. OPP headings are indented **0–7 spaces**; item markers vary (`1.`, `1)`, `a.`).
6. Test fixtures must be **verbatim extracts of the shipped PDFs**, never hand-written strings.

### 5.3 Corpus scope

One `StandardSet`: SAOSO v2.1 2026 · OPP 2026 · Basic Production Principles · Certification
Landscape. Chunks carry `section_ref`, `sub_refs`, `anchor`, `page`, `token_count`. Re-ingest is
idempotent on `sha256`; `superseded_by` links versions without deleting history.

### 5.4 Generation contract

```json
{ "answer": str, "citations": [{"section_ref": str, "quote": str}], "insufficient_context": bool }
```

Refusal triggers on `insufficient_context` **or** empty `citations` **or** a cited `section_ref`
absent from the retrieved set. Never on scraping the model's prose.

### 5.5 Claim discipline

Public surface may reproduce only the four FORM outcomes and the **active** seals. The
pasture-raised seal is inactive (D11) and is **never rendered**; issuance is hard-blocked when
`is_active=False` with no override. "GMO free", "biodynamic", "chemical-free" and "spray-free"
are treated as producer statements, never as PGS endorsements. Membership is never implied to be
certification.

### 5.6 Storage and hosting

Filesystem media, private/public roots, `X-Accel-Redirect` in the reference deployment. For MVP 0
the app runs locally with Postgres+pgvector and Redis under Compose, media backed up to an
**attached external drive**, and the restore rehearsed there. No S3.

### 5.7 Observability and hardening

`/health/` returning 503 on any failed dependency; Sentry on every exception path; `django-structlog`
with `X-Request-ID` propagated into Celery; explicit `timeout=` on every external call; retry
policies on every task; no `except: pass`.

---

## 6. Execution Steps

Detailed task order, acceptance tests and code shapes live in `MVP0_PLAN_V2.md`. Sequence:

1. **A1–A10** — foundation, including the parser-verification harness.
2. **B1–B7** — corpus models, parsers, chunker, embeddings, ingestion, retrieval, appendix segmentation.
3. **C1–C4** — public site, documents, bilingual scaffolding, claim-discipline test.
4. **D1–D4** — chatbot models, service, grounding tests, guardrails.
5. **UAT** — eight scenarios; Scenarios 1, 3 and 8 provisional (D23) if the administrator and
   consumer representative are unavailable at MVP 0 sign-off.

---

## 7. Success Criteria

**Machine-checkable**

- [ ] Every one of the four documents ingests with **non-zero sections and non-empty `section_ref`**.
- [ ] `sub_refs` offsets are non-overlapping and within chunk bounds.
- [ ] A grounded question returns citations whose `section_ref` exists in the retrieved set.
- [ ] An ungrounded question returns the refusal string **and** creates one `EscalatedQuery`.
- [ ] No answer can cite a chunk outside the session's `StandardSet`.
- [ ] Rendered public HTML contains none of: `pasture raised`, `pasture-raised`, `GMO free`,
      `biodynamic`, `chemical-free`, `spray-free`.
- [ ] Re-ingest adds zero chunks (idempotent on `sha256`).
- [ ] `knowledge` never imports `core` (import-linter).
- [ ] `/health/` returns 503 when any dependency is down.
- [ ] Rate limiting returns 429 past the per-IP budget.

**Human-judged (UAT)**

- [ ] The chatbot reads as a *quotation of the standard*, not a plausible summary (Scenario 1).
- [ ] Citations resolve to passages that actually support the claim (Scenario 2).
- [ ] The refusal reads as a confident boundary, not a malfunction (Scenario 3).
- [ ] The site reads as Outeniqua PGS's own, not a template with a name inserted (Scenario 4).
- [ ] Afrikaans reads as written, not translated (Scenario 5).
- [ ] Usable on a real phone at a market (Scenario 6).
- [ ] `/documents/` replaces Google Drive completely (Scenario 7).
- [ ] The member list does not imply certification (Scenario 8).
- [ ] **A restore from the backup drive has been performed on a clean machine.**

---

## 8. Risks & Mitigations

| # | Risk | Mitigation |
|---|---|---|
| R-A | **Parser correctness** — the class of bug that passes a hand-written fixture and fails on the real PDF. | Fixtures are verbatim extracts; ingestion asserts non-zero `section_ref`; the harness ships in CI. |
| R-B | **Refusal quality** — a bot that hedges once is assumed to invent elsewhere. | Structured flag, not prose; Scenario 3 judged by a committee member. |
| R-C | **Claim drift** — a marketing page implying certification. | Grep test + Scenario 8 judged by the committee, because tone is not greppable. |
| R-D | **Corpus scope creep** — ingesting the workbook, so the bot can cite its own questionnaire. | D16: four documents, explicitly listed. |
| R-E | **Translation gap** — D18 ships a shell, not content; Scenario 5 cannot pass until a reviewer is named. | Scenario 5 marked provisional with a named re-run point. |
| R-F | **Sign-off availability** — three of four UAT seats unfilled. | D23: provisional, re-run at MVP 1 kickoff. Never self-certified. |
| R-G | **Cost** — corpus embedding is one-off; chatbot traffic is per-query. | Dev key with caps; group-owned account and alerting before public traffic (D20). |
| R-H | **WordPress drift** — two sites publishing divergent facts during the preview. | D21: WordPress stays authoritative for farm status until MVP 2 cutover. |

---

## 9. Open for Brainstorming

These are the system-level questions this PRD deliberately does **not** answer. They are grouped
so one session can cover them. The first group is a prerequisite for MVP 1 planning; the rest can
be settled in any order.

### A. The citation and standards model — *must close before MVP 1*

**A1. `standard_ref` coverage.** §14 promises "which SAOSO clauses produce the most findings" by
aggregating `AssessmentVerdict.standard_ref`. In the workbook, clause references exist in
**exactly one sheet** — Agro-processing (`S20.1.1` … `S20.6.3`). Crops (37 verdicts), Animal
Husbandry (18) and Seed Production (36) carry none. So gap analysis currently works for one of
four categories. *Who authors ~91 clause mappings, and when?* Options: author them during
template creation in MVP 1; ship gap analysis for agro-processing only; or drop the feature.

**A2. Verdict polarity and key namespacing.** `AssessmentVerdict.is_compliant(bool)` assumes
"yes = compliant". It is false for several FORM verdicts — `V3` "Is there need for a transition
period?" (yes ⇒ In-Conversion, a legitimate state), `V16` "Are there any risks of contamination
of the water source?" (yes ⇒ non-compliant), Animal `V14` "Does the transport method raise any
concerns?" (yes ⇒ bad), and `V29` "(if applicable)" needs a third state. Separately, `V#` is
category-scoped — Crops `V4` is on-farm composting, Seed `V4` is compost quality, Animal `V4` is
living conditions — and Crops contains **two rows both labelled `V32`** with `V15`/`V31` absent.
*Does polarity move into the template schema as data, and do keys become `crops.V04`?* This must
be settled before the first template is frozen.

**A3. Is the workbook a template source?** `load_template` imports questionnaire JSON. The FORM
workbook is the only authoritative source of the questions and their grey/white split. *Do we
author the templates by hand from the workbook, or build a one-off extractor?* The extractor is a
form-parsing problem with merged cells and a two-role layout.

### B. Assessment-domain gaps — *MVP 1 scope decisions*

**B1. Farm input register (FORM Sheet B.2).** The workbook requires an input register — product,
manufacturer, organic certification, certifier, ingredients, **registered under Act 36** — and
Sheet B.1 directs farmers to it. The spec models `SupplyingFarm` for *aggregation produce*, not
for *inputs*. Act 36 appears zero times in the spec. *Is the input register MVP 1 or later?*
It is the evidentiary backbone of "no prohibited synthetic chemicals".

**B2. Prior certification history and prior denial.** FORM Sheet A asks about prior PGS and
third-party certification (group, certifier, expiry) and **denial** of certification; Sheet J
publishes previous certification history. Neither is modelled. *In or out of MVP 1?*

**B3. Disciplinary record.** OPP §4.5–4.7 is excluded as a *workflow*, but it is a time-based
rules engine: first warning active one calendar year, second similar transgression cancels
membership, non-critical termination ⇒ one year probation, reinstatement after one calendar year.
`Member.status.PROBATION` exists with no warning record, no expiry and no reinstatement
eligibility. *Record-only in MVP 1, or fully deferred?*

**B4. Unannounced and complaint-triggered visits (OPP §4.4).** The spec's appendix claims
traceability to this section, but `FarmVisit` has no `visit_type`, and the composition rule
differs — a complaint visit needs the administrator, a committee member and **one unaffected
member**, not the usual four. *Add `visit_type` now, or defer?*

**B5. Traceability for all sellers (OPP §4.2(12)).** The obligation — an invoicing/delivery-note
audit trail accessible to the committee — applies to *every farmer member selling their own
produce*, not just aggregating farms. The spec models it only inside aggregation. *Narrow
deliberately, or add the general check?*

### C. Certification semantics — *blocks the MVP 2 data model*

**C1. Seal cardinality and the fourth outcome.** `Certificate.seal` is a single FK, but OPP §2.5
refers to the farmer receiving "seal(s)" and FORM Sheet J has two product columns — organic
assured and in-conversion — on one outcome summary. And the outcome `Organic - pending corrective
action` has **no seal mapped**, while OPP §V says the In-Conversion seal "can also be used in
instances when corrective action is required following a deviation". *Single seal, M2M, or
per-product seal?*

**C2. The pledge contradicts OPP §V on in-conversion periods — needs a group decision.**
OPP §V: annuals 18 months, pasture 12, other perennials 12. The annexed Farmer Pledge: annuals
**12**, pasture 12, other perennials **18** — annuals and perennials are swapped. The platform
records the pledge as the attestation and infers the seal from it, so a 12-month annual
attestation could produce *Certified* where §V requires *In-Conversion*. *Which figure governs,
and does the pledge form get corrected?* This is a certification-integrity question, not a
software one.

**C3. Registry seeding policy.** §12.1 proposes seeding from the live site, where 2023/24
outcomes are missing and only one certificate is current. *Do migrated records carry
`provenance` + `evidence_status`, with the public surface rendering only `VERIFIED`?* And do the
~24 named consumer members migrate at all, given no consent basis?

### D. The offline slice — *the hardest part, untouched by MVP 0*

> **D1 and D2 are resolved** — spec §18.3 D25/D26, exploration in
> `product/design/d1_mvp1_shape_exploration.html`. MVP 1 is two increments with one ship gate
> (`1a` in-office breadth, `1b` in-field depth); the spike gates the seam contract rather than
> running merely parallel. Retained below for context.

**D1. ~~Does MVP 1 include the PWA?~~ → resolved as `1a` + `1b`.** §19 bundled “offline visit”
into one slice: application → questionnaire → offline walkabout → split-sync → Sheet J. That is
two different projects — a conventional Django form flow and a service-worker/IndexedDB client —
sharing a template schema. Split into two increments with a frozen seam contract at `1∥`, and a
single MVP 1 claim attaching to `1b`.

**D2. ~~The two-day spike.~~ → resolved: it gates the contract.** Runs on a real iPhone in a real
low-signal location. Its outcome decides what `VisitSyncEnvelope` must carry, so it must finish
before `1∥` freezes — not before `1a` merely starts.

**D3. Afrikaans in the offline shell.** D7 requires both languages first-class and the PWA caches
its catalogues. *Does `1b` need translated PWA strings before the assessor ever uses it offline?*
Now a `1b` question rather than a `1` question.

### E. Operations

**E1. Assessment fee gate.** OPP §2.3: "Fees are payable **prior to** the farm assessment visit."
The spec gates only at certificate issuance. *Add the pre-visit gate?*

**E2. Two dangling models.** `AssessmentFee` (referenced in §3, §7) and `EvidenceDocument`
(referenced in §8, §12) are used but never defined in §4. *Define, or fold into existing models?*

**E3. Hosting cutover.** MVP 0 runs local (D19). *What has to be true before the VPS move at
MVP 2 — Docker on a shared box, or native gunicorn + systemd?*

---

## 10. Pre-Flight Checklist

Adapted from `PRD_TEMPLATE.md`. The template's `core/models.py` reference is superseded by this
project's `core/models/` package (`build_principles.md` §0, deviation C3).

- [ ] Models in `core/models/_<domain>.py` (or `knowledge/models.py`), re-exported from `__init__.py`
- [ ] Views in `core/views/_<domain>.py`
- [ ] Forms in `core/forms/_<domain>.py`
- [ ] Services in `core/services/_<domain>.py`, each with an `In/Out/Side Effects/Fails` contract
- [ ] URLs in `core/urls.py` under the correct prefix (`/`, `/portal/`, `/assess/`, `/verify/`, `/api/v1/`)
- [ ] Tests in `core/tests/test_<domain>.py` or `knowledge/tests/`
- [ ] Migrations backwards-compatible; nullable or defaulted on add
- [ ] `select_related` / `prefetch_related` on every relational query
- [ ] `transaction.atomic()` on every multi-table write
- [ ] No logic in templates
- [ ] No file over 30 KB
- [ ] `knowledge` does not import `core`
- [ ] UAT items carry a `Judgement:` clause; machine-provable checks live in the suite
- [ ] Spec §18 updated if a decision moved

---

## Appendix — What changed since the first plan

The first implementation pass (`MVP0_PLAN.md`, now superseded) was written against assumptions
that the shipped PDFs contradict. Five fixes and eleven decisions came out of review:

**Fixes**

| # | Was | Now |
|---|---|---|
| F1 | SAOSO cited as `B-20.1.1`; parser matched **nothing** | `20.1.1.` + part from running page headers; citation `S20.1.1` |
| F2 | OPP Roman-numeral sections unreachable — including `§V` (seals) and `§VI` (aggregation) | Roman top level + `sub_ref` to depth 3 |
| F3 | §12 said the pasture-raised seal is rendered with a caveat, contradicting D11 and failing the claim-discipline test | Never rendered; issuance hard-blocked |
| F4 | "Notifiable exception" defined as a *deviation* | A **granted**, documented, reported exemption; `NotifiableExemption` model |
| F5 | `pgs/` untracked inside a 30-project parent repo with no `.gitignore` | Own repo; parent ignores `pgs/` |

**Decisions** — D14–D24, recorded in `PGS_PLATFORM_SPEC.md` §18.3.

**Still outstanding from the review, deliberately not applied** — the §9 brainstorm list above:
verdict polarity, `standard_ref` coverage, six missing domain areas, seal cardinality, the
pledge conflict, registry seeding policy, and the offline slice's shape.
