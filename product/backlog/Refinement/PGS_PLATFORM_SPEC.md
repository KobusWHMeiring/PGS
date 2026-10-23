# Outeniqua PGS Digital Platform — Aimed Design Spec (Target State)

**Status:** Refinement — final PRD review completed 2026-10-18. Findings F1–F5 applied; decisions D14–D24 recorded in §18.3. MVP 0 is specified in `MVP0_PRD.md` and `MVP0_PLAN_V2.md`; it awaits one system brainstorm (`MVP0_PRD.md` §9) before implementation.
**Owner:** Kobus Meiring (Product)
**Last Updated:** 2026-10-18
**Supersedes:** `prd.md` (2026-10-18, "Outeniqua PGS Digital Platform — Design")
**Scope:** The complete desired system. MVPs will be cut from this document in a later pass; this document deliberately describes the ideal, not the first release.
**References:**
- `pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf` — the authoritative governance document (cited as **OPP** below)
- `pgs_docs/saoso-version-2.1-2026.pdf` — SAOSO Standard for Organic Production and Processing v2.1 2026 (**SAOSO**)
- `pgs_docs/6. PGS Farm visit assessment form ... .xlsx` — the assessment workbook, Sheets A–J (**FORM**)
- `pgs_docs/5. PGS Farm Visit preparation list.pdf` (**PREP**)
- `pgs_docs/7.a–7.c` — participant checklists (paper, out of scope)
- `pgs_docs/PGS Certification landscape_Final.pdf` (**LANDSCAPE**)
- `pgs_docs/Basic Production Principles_ENG_PRINT.pdf` (**BPP**)

---

## 0. Governing Conventions

We adopt the **Harvester** build principles as the baseline for this project, grafted with the **Homtini** structural constraints that `prd.md` already assumes. Three source conflicts are resolved explicitly below.

| # | Conflict | Resolution |
|---|----------|------------|
| C1 | `prd.md` cites "views < 20 lines", "30KB file cap", "Data Flow Contract docstrings" — these exist only in Homtini's `build_principles.md` §1.1–1.3, not Harvester's. | **Adopt both.** Harvester BP is the baseline; Homtini §1.1 (Thin Views, Service Layer Ownership, 30KB cap, No Logic in Templates), §1.2 (Data Flow Contracts), §1.3 (strict type hints + `@dataclass(frozen=True)`) are imported verbatim. |
| C2 | `prd.md` proposes three Django apps (`_core`, `_assessment`, `_chatbot`); Harvester BP mandates a **Monolithic Core** (one `core/` app, domain-sliced subpackages). | **Partly deferred to O4 (§18.2).** `_assessment` is rejected as a separate app in every option: certification is a single aggregate rooted at `FarmVisit`, and splitting assessment from certification is a *subdomain* boundary, not a *context* boundary. Whether the genuinely-independent knowledge slice becomes a sibling `knowledge/` app is the open question. |
| C3 | Harvester mandates a single `core/models.py`; Homtini's 30KB cap makes that impossible at this domain size (Harvester's own `models.py` is already 1,630 lines). | **`core/models/` becomes a package** with domain modules and an `__init__.py` re-export, preserving `from core.models import Farm`. Under O4 Option B the knowledge slice instead gets its own `knowledge/models.py`. This is a deliberate, documented deviation from Harvester BP §Architectural Layout. |

**Explicitly not adopted:** Homtini BP §4 ("Asynchronous Pi Decoupling"). This platform is not a farm-appliance integration; it has no Pi counterpart.

**Decision review — 2026-10-18.** Every item in §18 is now resolved. Three resolutions materially changed the design and are called out where they land: **HTMX is permitted** (§5); **storage is filesystem `media/`, not S3** (§15, R11); and **voice notes** are designed in now but their recorder UI and transcription pipeline are deferred to post-MVP (§17.2). O5 was agreed and *extended*: roles are plural per user (§3). O4 was refined during review — the split line is now the **standards library**, not "the chatbot" (§18.2).

**Addendum — 2026-10-20 (D45).** A worked read of the 2022 Homtini assessment report exposed five omissions in the visit flow: the Sheet I conclusion (social equity and the documentation/records checklist), structured sub-verdicts, a farmer-facing corrective-action follow-up, finalise completeness gates, and the prior-visit action review. All five are assessment evidence and land in `1a`; the four certification outcomes remain MVP 2 (D33). The 2026 FORM is the authority where the 2022 paper differs.

**Adopted from Harvester BP and mandatory in every slice:** `/health/` endpoint; Sentry on all exceptions (no bare `except: pass`); `X-Request-ID` structured logging (`django-structlog`); explicit `timeout=` on every external call; retry policies on every Celery task; `transaction.atomic()` on all multi-table writes; `select_related`/`prefetch_related` on every relational query; domain query logic in custom QuerySets/Managers; `.env` via `python-dotenv` as the sole config source; no secrets in source.

---

## 1. Problem & Strategic Goal

**Problem.** Outeniqua PGS runs on paper clipboards. The assessment workbook (FORM, 13 sheets) is filled in by hand across Crops, Animal Husbandry, Seed Production and Agro-processing; evidence photos live on someone's phone; corrective actions, committee decisions, certificates and the public-facing record are all assembled manually. Concurrently, the group's public presence is a WordPress site that cannot verify a claim.

**Goal.** A single zero-build Django monolith that:
1. Digitises the *whole* assessment lifecycle — application → pre-visit questionnaire → offline farm walkabout → review → decision → certificate → public verification — with no paper reconciliation step.
2. Makes every certification claim **independently verifiable** by a consumer via QR code.
3. Answers SAOSO v2.1 and Outeniqua SOP questions **strictly from source**, with citations, and escalates rather than hallucinating.

**Success looks like:** an assessor with no signal completes a 2-hour walkabout entirely on a phone, and by the time they drive back into reception the visit, photos, signatures and Sheet J PDF are on the server, the corrective actions are queued, and the farm's public status has moved — with zero retyping by the administrator.

---

## 2. Ubiquitous Language

These terms are load-bearing. Code, templates, URLs and admin copy must use them exactly.

| Term | Definition | Source |
|------|-----------|--------|
| **Farm Visit** | The event: one assessment of one farm on one date, with a committee of participants. | OPP §4.2 |
| **Assessment** | One category's body of questions within a Farm Visit (Crops, Animal Husbandry, Seed Production, Agro-processing). A visit holds 1..n. | FORM A |
| **Assessment Team / Farm Visit Committee** | Minimum 4 people: 1 administrator, ≥2 peer farmers, ≥1 consumer/public member. Retailers attend all visits they source from. | OPP §3.3, §4.1 |
| **Peer Member** | A farmer/producer who is a member of a PGS with knowledge of the production being assessed. | OPP §4.1 |
| **Administrator** | The committee member who drives the visit and completes the assessment report (the grey cells of FORM). | FORM A |
| **Verdict** | An assessor's compliance determination attached to a question — the `V#` rows of FORM (e.g. `V1a (S20.1.1)`). | FORM |
| **Finding / Concern** | A recorded non-conformity, graded **Minor**, **Major** or **Critical**. | FORM Sheet I/J |
| **Corrective Action** | The remedy recommended by the group for a Finding, with a due date. | FORM Sheet I |
| **Minor** | *"The farmer is to address the issue for continual improvement of organic practices."* | FORM Sheet I (verbatim) |
| **Major** | *"The committee would like focused attention on the issue with report back in a defined time period."* | FORM Sheet I (verbatim) |
| **Critical** | *"The concern will have an impact on certification if not corrected within a defined time period."* | FORM Sheet I (verbatim) |
| **Notifiable Exception** | An exemption the group **grants** against a specific requirement of the standard, which must be documented and reported to PGS-SA. It is *not* a non-conformity — a Finding is. | FORM Sheet I §3 (*"notifiable exception as allowed in the organic standards **granted**"*); OPP §V (*"the authority to **grant** notifiable exemptions"*); BPP Introduction |
| **Outcome** | One of four decisions: `Certified Organic`, `Organic - pending corrective action`, `Organic In-conversion`, `Not endorsed/reschedule`. | FORM Sheet I/J |
| **In-Conversion** | Production follows organic principles but the land has been under organic management for less than 18 months (annual), 12 months (pasture/meadow), or 12 months (other perennials). | OPP §V |
| **Seal** | One of the marks OPP §V authorises: **"PGS Organic Certified"**, **"PGS Organic In-Conversion"** (both active), and **"PGS pasture-raised"** (inactive — see §4.3). | OPP §V |
| **Endorsed Product** | A product affirmed as grown according to organic principles for the next 12 months, per category. | FORM Sheet J |
| **Voice Note** | An audio recording captured in the field in place of typing — a dictated finding, risk assessment or note. Transcribed server-side into a reviewable draft. *Designed now, built post-MVP (§17.2).* | (new — D6) |
| **Value chain actor** | The group's own term for a market, distributor or retailer member (Wild Oats Farmers' Market, Farm Fresh Direct). Preferred over "retailer". | OPP §3.3; live site `/members-2/` |
| **Pasture raised** | OPP §V lists a third issuable mark, "PGS pasture-raised", whose criteria it states are *"forthcoming"*. **Deferred** — modelled as a `Seal` row seeded **inactive**, so enabling it later is a data change, not a migration. | OPP §V; live site `/organics/` |
| **PGS-SA** | The national body the group pays membership to and reports notifiable exceptions to. | LANDSCAPE |

---

## 3. Actors, Roles & Membership

`prd.md` listed `User` as (Admin, Peer Assessor, Consumer). That is insufficient on two counts: a peer member *is* a farmer, and one person is routinely several of these at once — a farmer can also be a peer assessor and a consumer, and a value chain actor can also sit on the committee. Role is therefore **plural and contextual**, modelled on two axes (agreed and extended in review, O5).

**Axis 1 — account roles** (`UserRole`: users ↔ roles, zero or more per user). A person is not "a Farmer"; they **hold** the Farmer role.

| Role | Grants | Notes |
|------|--------|-------|
| `FARMER` | Farmer portal; application and questionnaire submission | Requires a `Member` record and a `Farm`. |
| `ASSESSOR` | Access to the offline assessor PWA | Set when a farmer member is activated as a peer assessor (OPP §4.1). |
| `CONSUMER` | Public-member standing; visit participation | |
| `VALUE_CHAIN_ACTOR` | Market, distributor or retailer representative standing | The group's own term is "value chain actor". OPP §3.3: expected to attend all visits they source from. |
| `ACADEMIC` | Academic representative standing | |
| `ADMIN` | Staff: drives visits, compiles reports, administers records | Also implies `ASSESSOR`. |
| `COMMITTEE` | Reviews and decides; committee reporting | |

Capabilities are derived from the role set (`user.has_role('ASSESSOR', 'ADMIN')`) and never checked ad hoc in views. A user holding no roles is a plain public visitor.

**Axis 2 — role in visit** (`VisitParticipant.role`, per visit, drawn from OPP §3.3): `ADMINISTRATOR`, `PEER_FARMER`, `HOST_FARMER`, `CONSUMER`, `VALUE_CHAIN_ACTOR`, `ACADEMIC`, `TRAINEE`, `OBSERVER`. This records what the person actually did on that visit, which is distinct from what they are entitled to do. The host farmer is always a `VisitParticipant` even though they are the subject of the visit, because OPP §3.3 counts them among attendees and FORM Sheet J records them as the person who hosted.

### 3.1 How assessors are appointed

There is **no assessor qualification or certification process** in any governing document. A peer assessor is not accredited; they are **assigned per visit, by competency match**. The whole mechanism comes from OPP:

- **Steering committee** — elected by members at the AGM, composition renewed at each AGM, farmers holding no less than 50% of seats (OPP §3.1). OPP §VII publishes the current roster with named holders and positions.
- **Farm visit committee (the assessment team)** — assembled for each visit by the administrator, and valid only if it satisfies OPP §4.1.2 and §3.3:
  - exactly one committee member **responsible for administration** of the visit;
  - **at least two peer members**, a peer member being *"a farmer/producer who is a member of a PGS and has knowledge or understanding of the production on the farm/production being assessed"*;
  - **at least one public member** — a consumer or independent retailer who would normally consume or purchase from the assessed farm;
  - a **technical expert** where no group member holds the specific knowledge required;
  - **at least four people** in total (administrator + 1 consumer + 2 farmers);
  - **observers** permitted up to a maximum set by the host farm, who *"shall not disrupt the assessment process"*;
  - farm visits are open to members **and non-members** alike.

Two consequences the platform must carry:

1. **Eligibility is competence plus standing, not a credential.** The gate is active and paid-up membership, attendance obligations met (annual group meeting; farmers attend ≥2 other farm visits annually — OPP §3.2), and knowledge of the production type under assessment. So `Member.expertise` records production-type knowledge drawn from the same `Category` rows as `FarmCategory` (§4.1), and the `ASSESSOR` role means *eligible to be assigned*, not *qualified*.
2. **Composition is a server-side validation, not a guideline.** A `VisitPlan` cannot be confirmed unless the participant set satisfies every clause above, enforced by `validate_assessment_team()` in `_assessment.py`. The three numeric pre-visit rules — ≥5 days' notice, questionnaire to the team ≥3 days ahead, conclusion within 5 days — are the same class of check.

### 3.2 Committee positions

OPP §3.1 defines the positions and OPP §VII lists the 2026 holders. Holding a committee *position* is not the same as holding the `COMMITTEE` account role, and positions are term-scoped because composition is renewed at every AGM:

`CommitteePosition` ∈ `CHAIRPERSON`, `VICE_CHAIRPERSON`, `SECRETARY`, `TREASURER`, `FARM_VISIT_ADMINISTRATION`, `TECHNICAL_FARMING_SUPPORT`, `COMMUNICATIONS`, `EVENTS_COORDINATION`, `CONSUMER_REPRESENTATIVE`, `RETAIL_MARKET_REPRESENTATIVE`, `ACADEMIC_REPRESENTATIVE`.

The published 2026 roster (OPP §VII) seeds these records — Chairperson, Vice-Chairperson, Secretary, Treasurer, farm visit administration and reporting, technical farming support, communications, consumer representative, retail and market representatives. **Events coordination and academic representation are both vacant**, advertised as a call for expressions of interest, so vacancy is a representable state rather than a missing row.

**Membership** governs eligibility, independent of login:

- `Member.status`: `APPLICANT`, `ACTIVE`, `PROBATION`, `LAPSED`, `TERMINATED`.
- Eligibility gate (OPP §2.3): *"Only fully paid-up members will be eligible for farm assessments and receive certificates."* `Member.is_paid_up` is a derived property over `MembershipFee` records, and is asserted in `certification_service` before any certificate is issued.

  **Precise definition (D39):** `is_paid_up = MembershipFee.objects.filter(member=m, paid_on__isnull=False, period_start__lte=today, period_end__gte=today).exists()`. Explicit `period_start`/`period_end` on the row, so the OPP's *"payable by end of February"* rule never hardcodes a calendar-year boundary in code.
- Pledge (OPP §I.1–I.2). The OPP contains **two distinct pledges**, so `Pledge.kind` ∈ `FARMER` | `CONSUMER`.
  - `method` ∈ `SIGNATURE` | `DISTINCTIVE_MARK` | `VERBAL_WITNESSED`. The farmer pledge is signed with a *"Signature(s)/distinctive marks"* line — the OPP §I.2 path for members who cannot sign — and it carries a witness block requiring **name, designation and signature**.
  - The farmer pledge also carries a **land-history attestation** (12 months before sowing/planting for annuals, 12 months before grazing/harvest for pasture, 18 months before harvest for other perennials) **or** an explicit **in-conversion declaration** with a 12-or-18-month selection. Both are recorded, because they are the basis of the In-Conversion seal decision.

**Public visitor → member progression.** A visitor can use the public site and chatbot without an account; an account is created when they engage further, and `User.graduated_from_public_at` records when a public user became a member. Roles are added to the same `User` — a consumer who buys a farm gains `FARMER` and a `Member`; a farmer member activated as a peer assessor gains `ASSESSOR` — rather than a new person being created. This is why identity lives in `core` rather than in the knowledge app (§5, §18.2).

**Fees tracked** (OPP §II) — *tracking only; no payment-gateway integration in scope*:
Annual farmer/consumer membership R100; PGS-SA membership R500; assessment fee on a 6-band turnover sliding scale (R1,500–R8,000 initial, R900–R8,000 renewal); participant catering R30 member / R50 non-member; seal licensing R500 per annum per farm; administrator transport at AA rate. Turnover is *self-declared by the farmer and subject to peer review* (OPP §2.3), so `AssessmentFee.turnover_band` is a declared field, not a computed one.

---

## 4. Domain Model

`core/models/` package, split by context. Integer PKs internally; `UUIDField` for every public surface (Harvester BP: *"Sequential IDs must never be leaked to the public"*).

### 4.1 Core & Membership — `core/models/_core.py`

```
Category            code, label, display_order, is_active, standard_ref   # data, see §4.8
User                phone, email, email_verified_at, popia_consent_at, preferred_language,
                    graduated_from_public_at          # public visitor -> member (§3.1)
UserRole            user, role                     # zero or more per user (§3, axis 1)
Member              user(1:1), membership_no, joined_on, status, probation_until(nullable),
                    is_paid_up(derived), expertise(M2M -> Category)
                    # drives peer-assessor assignment (§3.1). membership_no is human-facing
                    # and printed on certificates, so it is PUBLIC: "OUT-<year>-<seq:04d>",
                    # never a bare autoincrement (D39).
CommitteeTerm       user, position, agm_year, elected_on, vacated_on    # OPP §3.1, §VII
Pledge              member, kind, method, signed_on, place, declared_land_history_ok,
                    in_conversion_declared, in_conversion_months, recorded_by,
                    witness_name, witness_designation, witness_signature, evidence_photo
MembershipFee       member, kind, period_start, period_end, amount_cents, paid_on, receipt_no
AssessmentFee       member, farm_visit(nullable), kind(INITIAL|RENEWAL), turnover_band,
                    band_label, amount_cents, due_on, paid_on, receipt_no,
                    is_significant_change(bool)
                    # D29. OPP §2.3 six-band sliding scale. Turnover is DECLARED by the
                    # farmer and peer-reviewed — never inferred from sales records.
                    # Payable BEFORE the visit (D32). Major changes to land, production
                    # system or inputs => initial rate, not renewal.
PriorCertification  farm, kind(PGS|THIRD_PARTY), body_name, certificate_ref,
                    outcome(GRANTED|DENIED), expires_on, denial_reason
                    # D30. FORM Sheet A: prior PGS and third-party certification, and
                    # prior DENIAL of certification with reasons. A denial is materially
                    # relevant to a certification decision; OPP §4.5 also makes misuse of
                    # a third-party logo serious misconduct.
Farm                member, name, slug, physical_address, nearest_town, latitude, longitude,
                    total_hectares, public_uuid, publish_consent, publish_consent_at,
                    first_certified_on
                    # D34: NO PostGIS. GPS is optional, never published and never spatially
                    # queried, so it is DecimalField(max_digits=9, decimal_places=6) x2 — not a
                    # geometry column, which would drag in django.contrib.gis + GDAL (and the
                    # pgvector image has no PostGIS). Migrate to PostGIS only if a real spatial
                    # query ever needs it.
                    # D35: current_status is deferred to MVP 2 — it derives from Certificate,
                    # which does not exist in 1a. A stub that always answers "no certificate"
                    # would be a lie-shaped value someone will trust.
                    # D39: nearest_town is plain text, not an enum — towns are group data (§4.8).
FarmAlias           farm, name, source                        # historical/external name variants
FarmCategory        farm, category(FK), status, first_assessed_on   # 1..n per farm
                    # D36: status ∈ APPLIED | FOR_ASSESSMENT | ASSESSED | INACTIVE — an
                    # application lifecycle for 1a. Certification state per category is
                    # ProductOutcome.status (MVP 2), which supersedes this for that purpose.
FarmContact         farm, name, role, phone, email                    # incl. hosting contact
```

`Category` is a **table, not an enum** (§4.8). The deployed set for Outeniqua is `CROPS`, `ANIMAL_HUSBANDRY`, `SEED_PRODUCTION`, `AGRO_PROCESSING`, `AQUACULTURE`, `WINE`, `INPUT_SUPPLIER`; the last three are marked *in development* in FORM Sheets F/G/H and are seeded **inactive** rather than omitted, so publishing them later is a data change and the schema never needs a migration for a new category.

Census fields (FORM A: gender, age group, demographic group) live on `Member` as `census_gender`, `census_age_band`, `census_demographic_group`, flagged `sensitive=True` and excluded from every public serializer.

**Farm identity.** The existing public records spell the same farm several ways — "Chillin Out Farm" / "CHILLOUT FARM", "Diepflook Farm" / "DIEPKLOOF FARM", "Hamel en Harden" / "HAMEL & AARDEN BOERDERY", "Well I Am" / "WELL-I-AM". `FarmAlias` exists so the migration and every future spelling resolves to one canonical farm, and so a verification lookup by an old name still lands. Public location is `nearest_town` only (Elandskraal, Homtini Pass, Groot Brak, Rheenendal, Hoekwill); precise GPS is optional and never published.

**Catchment is a deployment setting, not a field (D37).** The group's range — *"roughly from Mossel Bay to the Crags"* — is one string for the whole deployment, and belongs with group identity in seed/settings (§4.8). Earlier drafts put `catchment` on `Member` and, separately, on `Farm`; both are withdrawn. A member's locality is already `Farm.nearest_town`.

### 4.2 Assessment & Evidence — `core/models/_assessment.py`

```
AssessmentTemplate      category, version, standard_version, schema(JSON), effective_from,
                        is_active
FarmVisit               farm, administrator, scheduled_for, visited_on, status, next_visit_due,
                        background_narrative, knowledge_exchange_narrative, general_notes, risk_assessment, client_uuid(unique), device_id, synced_at, decided_at
VisitParticipant        farm_visit, user(nullable), guest_name, role, is_member, attended,
                        catering_fee_cents, catering_paid
Assessment              farm_visit, category, template, template_schema(JSON snapshot),
                        standard_version, status
AssessmentAnswer        assessment, question_key, value(JSON), notes
AssessmentVerdict       assessment, question_key, ref, value(YES|NO|NA|NULL), polarity,
                        is_compliant(bool|null), standard_ref, notes, sub_answers(JSON)
                        # D27. polarity is snapshotted from the frozen template at capture
                        # time; is_compliant is DERIVED from (value, polarity) and materialised
                        # for querying. Neither is ever authored by a user. See §4.2.1.
InputSupply             farm, farm_visit(nullable, first recorded), product_name,
                        manufacturer, is_organic_certified(bool|null), certifier_name,
                        ingredients, purchased_on, amount, use_of_product,
                        act36_registered(bool|null), input_kind(SEED|COMPOST|AMENDMENT|FEED|OTHER),
                        seed_status(ORGANIC|CONVENTIONAL_UNTREATED|
                        CONVENTIONAL_TREATED|UNKNOWN|NA|null), approval_status(PENDING|APPROVED|
                        REJECTED), approval_rationale, approved_by
                        # D30. FORM Sheet B.2 — the farm's INPUT register (compost, seed,
                        # amendments, feed), a required part of the Crops category. B.1 Q4.3
                        # directs the farmer to it. Act 36 of 1947 registration is the
                        # primary evidence that an input is not a prohibited substance.
                        # D45: seed_status makes the "conventional, untreated seeds"
                        # notifiable exception queryable; approval_status records the
                        # assessor's V5/V25 judgment instead of a notes-column promise.
                        # NOT the same thing as aggregation produce (OPP §VI, §4.4).
Finding                 farm_visit, assessment, question_key, severity, description, raised_by
NotifiableExemption     farm_visit, standard_ref, requirement_exempted, rationale,
                        granted_by, granted_on, reported_to_pgs_sa_on, evidence_doc
                        # An exemption GRANTED under the standard and reported to
                        # PGS-SA. Not a non-conformity — see §2, FORM Sheet I §3.
CorrectiveAction        finding, recommended_action, due_on, status, submitted_on,
                        verified_by, verified_on, closed_on
                        # D45: after the visit this is the farmer's task. Evidence is
                        # an EvidenceDocument with corrective_action set; SUBMITTED
                        # means the farmer has answered, VERIFIED/CLOSED the reviewer.
SocialEquity            farm_visit(unique), employs_staff(bool|null), worker_count(int|null),
                        employment_status(PERMANENT|CASUAL|SUBCONTRACTOR|MIXED|NA),
                        labour_law_compliant(bool|null), staff_live_on_premises(bool|null),
                        children_under_15(bool|null), children_activities, notes,
                        recorded_by, recorded_at
                        # D45. FORM Sheet I §1. Worker and child-labour fields are
                        # sensitive and never serialised publicly.
RecordCheck             farm_visit, kind, status(CHECKED|MISSING|NOT_APPLICABLE),
                        notes, evidence_doc(nullable), checked_by, checked_at
                        # D45. FORM Sheet I §2 a–i: farm sketch, field diagrams, farm
                        # diary, input purchase records, sales records, input/output
                        # reconciliation, soil/water tests, agro-processing documents.
                        # This is the assessor's verification, not a questionnaire
                        # attachment; MISSING is a recorded fact, not an omission.
                        # evidence_doc may point at the questionnaire's EvidenceDocument
                        # rather than duplicating the file.
PriorActionReview       farm_visit, corrective_action, outcome(VERIFIED|PARTIAL|NOT_MET),
                        notes, reviewed_by, reviewed_on
                        # D45. One per prior open action, per visit. PREP requires the
                        # last visit's actions at the start of the next; NOT_MET on a
                        # Critical action sets CorrectiveAction.ESCALATED.
EvidenceDocument        farm_visit(nullable), assessment(nullable), member(nullable),
                        corrective_action(nullable), input_supply(nullable),
                        kind, title, file, sha256, uploaded_by, uploaded_at, is_private
                        # D29. D29 defines what was previously a dangling reference (§8, §12).
                        # Questionnaire attachments (soil tests, farm sketch, agro-processing
                        # flow diagrams — FORM Sheet I §2) and, later, historical dossiers.
                        # D45 adds the two follow-up links: a farmer's answer to a
                        # corrective action, and an input's supplier TDS/letter/invoice.
EvidencePhoto           farm_visit, answer(nullable), photo, caption, captured_at,
                        exif_gps, consent_given, client_media_uuid(unique), sha256,
                        derivative_url, uploaded_at
VoiceNote               farm_visit, answer(nullable), question_key, audio, mime_type,
                        duration_ms, captured_at, consent_given, transcript,
                        transcript_source, transcript_reviewed_by,
                        client_media_uuid(unique), sha256, uploaded_at
                        # VoiceNote is migrated with the schema now; its recorder UI and
                        # transcription pipeline are post-MVP (§17.2).
Signature               farm_visit, role, signer_name, image, signed_at, ip_hash,
                        declined(bool), decline_reason
                        # D45: a declined signature with a reason is not the same as
                        # a missing one; finalise refuses only the latter.
SyncReceipt             client_uuid(unique), device_id, farm_visit, payload_sha256,
                        raw_payload(JSON), received_at, status
```

**`FarmVisit.status`**: `DRAFT` → `SCHEDULED` → `IN_FIELD` → `SYNCING` → `SYNCED` → `UNDER_REVIEW` → `DECIDED` → `CLOSED`, plus `ABANDONED`.
**`Assessment.status`**: `PENDING`, `QUESTIONNAIRE_SUBMITTED`, `IN_FIELD`, `SYNCED`, `REVIEWED`.
**`CorrectiveAction.status`**: `OPEN`, `SUBMITTED`, `VERIFIED`, `OVERDUE`, `ESCALATED`, `CLOSED`. `ESCALATED` is reached when a **Critical** action lapses; per OPP §4.5 that is grounds for membership termination, so the state machine must be able to represent it and hand off to the discipline workflow.
**`RecordCheck.status`**: `CHECKED`, `MISSING`, `NOT_APPLICABLE`; `MISSING` requires a note. **`SocialEquity.employment_status`**: `PERMANENT`, `CASUAL`, `SUBCONTRACTOR`, `MIXED`, `NA`. **`PriorActionReview.outcome`**: `VERIFIED`, `PARTIAL`, `NOT_MET`. `SocialEquity` is unique per visit; `RecordCheck` is unique on `(farm_visit, kind)`; `PriorActionReview` is unique on `(farm_visit, corrective_action)`.

### 4.2.1 Verdict polarity and key namespacing (D27)

Every `V#` in the FORM is a Yes/No question, but **the meaning of "Yes" is not uniform**, and a single
`is_compliant: bool` records the wrong answer for several of them:

| Ref | Question (verbatim, FORM) | "Yes" means | Polarity |
|---|---|---|---|
| Crops V1 | "Are you satisfied that the farmer is/can produce the listed crops?" | compliant | `POSITIVE` |
| Crops V3 | "Is there need for a transition period?" | **needs In-Conversion** — a legitimate state, not a failure | `INFORMATIONAL` |
| Crops V16 | "Are there any risks of contamination of the water source?" | **non-compliant** | `NEGATIVE` |
| Crops V23 | "Do you see evidence of pests or pest damage?" | **non-compliant** | `NEGATIVE` |
| Animal V14 | "Does the transport method raise any concerns?" | **non-compliant** | `NEGATIVE` |
| Crops V29 | "Are containment methods acceptable? *(if applicable)*" | third state: not applicable | `POSITIVE` |

**Model.** Polarity lives in the **template** (`AssessmentTemplate.schema`), never in code, because it is a
property of the standard's question wording — which is data (§4.8). `AssessmentVerdict.polarity` is
snapshotted onto the row at capture time so a historical assessment remains self-contained after a
template edit, exactly like `template_schema`.

`value` is tri-state — `YES` | `NO` | `NA` | `NULL` — and `is_compliant` is **derived**:

```
is_compliant =
    NULL            if value is NULL or NA
    value == YES    if polarity == POSITIVE
    value == NO     if polarity == NEGATIVE
    NULL            if polarity == INFORMATIONAL   # carries meaning, not compliance
```

It is materialised as a nullable column at write time rather than computed on read, because §14's
cross-farm queries (`every farm non-compliant on …`) must not join the template. A test asserts the
stored value always equals a fresh recomputation.

**Key namespacing.** `V#` alone is unusable as a query key: it is category-scoped (Crops `V4` is
on-farm composting, Seed Production `V4` is compost quality, Animal Husbandry `V4` is animal living
conditions), and the source numbering is defective — **Crops contains two rows both printed `V32`**, and
has **no `V15` and no `V31`**. Keys are therefore `question_key = "<category>.<ref>"`, lowercase
category and zero-padded two-digit ref, e.g. `crops.V04`. Where the paper form repeats a ref, the second
occurrence takes a letter suffix (`crops.V32a`, `crops.V32b`) and the printed `ref` is preserved on both
rows. Gaps are **declared in the template file** (`allowed_ref_gaps: ["V15", "V31"]`) so validation warns
on a new gap without failing on a known one.

> Note on immutable history: `Assessment.template_schema` stores a *full copy* of the template JSON at visit creation. Editing `AssessmentTemplate` must never alter a historical assessment. This is the single most important data-integrity rule in the system.

**Sub-verdicts (D45).** The FORM prints several verdicts with child Yes/No rows — Crops V4 (2),
V10 (2), V11 (2), V19 (3), V21 (2), V35 (2) — and assessors do leave them blank. A child is structured:
`{"key": "crops.V04.a", "text": "…", "polarity": "POSITIVE", "options": ["YES","NO","NA"], "required": true}`.
The answer lives on the parent row's `sub_answers` as `{"<sub_key>": "YES|NO|NA"}` and is never folded
into the parent's single `value`. Children are not top-level `AssessmentVerdict` rows: 37 printed rows
is a completeness invariant, and the parent is the queryable unit. If a cross-farm query ever needs a
child in SQL, promote it deliberately rather than duplicating it silently. `NULL` is an omission;
`NA` is an answer; `finalise_visit` refuses a required child left `NULL`.

### 4.3 Certification & Registry — `core/models/_certification.py`

```
CertificationDecision   farm_visit, outcome, rationale, decided_by, decided_at
                        # exemptions are NotifiableExemption rows, not a field
ProductOutcome          decision, category, product_name, status, reason
                        # ORGANIC | IN_CONVERSION | NOT_ENDORSED
                        # NOT_ENDORSED carries a reason: not proposed for certification,
                        # treated seed, visit to be rescheduled, etc.
Certificate             farm, decision, seal(FK -> Seal), issued_on, expires_on,
                        public_uuid(unique), status, pdf, licence_fee_due_on
CertificateProduct      certificate, product_outcome
PublicVerificationEvent certificate, viewed_at, ip_hash, referrer   # audit of QR scans
```

`Certificate.seal` is a **foreign key to `Seal`, not an enum** (§4.8). A seal belongs to the *standard*, and standards change:

```
Seal                code, label, standard_ref, is_active, criteria_defined, display_note
```

Seeded for Outeniqua from OPP §V: `PGS_ORGANIC_CERTIFIED` and `PGS_ORGANIC_IN_CONVERSION` **active**; `PGS_PASTURE_RAISED` **inactive**.

**Deferred: the pasture-raised seal.** OPP §V lists a third mark — *"PGS pasture-raised"*, for *"farmers who are fully compliant with pasture raised as defined by the national working group"* — while stating in the same table that *"pasture raised is not defined by the SAOSO standard – details on this forthcoming"*. It is a real seal with undefined criteria, and **it is not being shipped**. Because seals are data, it exists as an **inactive row**: when the national working group publishes criteria, enabling it is a seed change, not a migration or a code release. `criteria_defined` stays on `Seal` for the general case in which a deployment activates a seal whose criteria cannot be machine-checked; while it is `False`, issuance requires an administrator override with a recorded rationale and the public page renders a *"criteria forthcoming"* note rather than an unqualified claim.

**Two rules keep the deferred seal out of the public surface (D11, F3).** (1) `is_active=False` blocks issuance **unconditionally** — no administrator override — because a seal with no published criteria is a claim that cannot be substantiated. (2) An inactive seal is **never rendered** on a public page. It is a dormant row awaiting the national working group, not content.
`Certificate.status` ∈ `ACTIVE`, `EXPIRED`, `SUSPENDED`, `REVOKED`. Suspension is reachable from the discipline workflow (OPP §4.6: termination forfeits the right to market under the logo).
Endorsement is *"for the next 12 months"* (FORM Sheet J) — `expires_on = issued_on + 1 year`.

### 4.4 Aggregation of produce — `core/models/_aggregation.py`

OPP §VI is a whole certification sub-domain missing from the first draft, and FORM Sheet A already asks applicants about it (*"Do you (farmer) buy in produce from other farmers for selling to your consumer?... does it include conventionally grown produce?... do you label the produce accordingly?"*).

```
AggregationApproval     farm_visit, aggregating_farm, approved_on, is_case_by_case,
                        includes_conventional, separation_measures_ok, rationale
SupplyingFarm           producer_name, is_certified, certification_ref, declaration_on_file
                        # declaration: no prohibited synthetics; producing to organic intent;
                        # commits to PGS certification within 6 months
AggregationTraceability approval, invoice_ref, delivery_note_ref, line_items(JSON)
AggregationLabel        approval, label_category, applied_from, applied_to
```

`AggregationLabel.label_category` ∈ `SELF_CLAIM_ORGANIC`, `CONVENTIONAL`, `FREE_RANGE` — the three labelling categories OPP §6.5 defines for retail and market settings, with their hard rules: **no PGS claim may be made** under any of them, and a self-claim organic label is permitted **only for 6 months** from notification, after which a PGS assessment is required.

Two consequences: aggregation is approved **case by case**, and only for an aggregating farm that is itself a participating, paid-up member with its own assessment and compliance history (OPP §6.1); and **physical separation** is mandatory where conventional produce is aggregated, declared by the aggregating farm and itemised in invoices and records (OPP §6.4).

### 4.5 Standards corpus — `knowledge/models.py`

```
StandardSet         code, label, description, is_default
StandardDocument    standard_set, kind, issuing_body, title, version, effective_from,
                    superseded_by, source_file, sha256, chunk_count, section_scheme
DocumentChunk       document, section_ref, sub_refs(JSONB), anchor, heading_path, page,
                    text, token_count, embedding(VectorField),
                    search_vector(GeneratedField tsvector)
                    # sub_refs: [{ref, start, end}] character offsets into text, so an
                    # enumerated clause can be quoted without splitting the chunk.
```

This is the whole of `knowledge/`: a **library over documents**. No users, no sessions, no views — which is what makes it independently testable and extractable.

Three things make it standard-agnostic rather than SAOSO-shaped:

- **`StandardSet` groups a corpus.** Outeniqua's set is SAOSO v2.1 + the OPP + the Basic Production Principles + the certification landscape. **Retrieval is always scoped to a set**, so a chatbot answering about SAOSO can never cite EU text, and two corpora can coexist — which is also how a version transition (SAOSO 2.1 → 2.2) is handled without deleting history.
- **`kind`** distinguishes `STANDARD` | `SOP` | `PRINCIPLES` | `GUIDANCE` | `LANDSCAPE`, because a citation must name what it came from.
- **`section_scheme` selects a pluggable section-reference parser.** The three source formats are genuinely different, and each must be read as it is printed — never as one wishes it were:

  | Document | As printed | Cited as | Notes |
  |---|---|---|---|
  | SAOSO | `20.1.1.` under a separate `SECTION B` part heading | `S20.1.1` | The FORM's convention, so every verdict reference is locatable on paper. The `S` is a **constant**, not the part letter — all 33 references in the FORM workbook are `S20.x` / `S22.x`. MVP 0 ingests Section B only (D41), so the part letter is not stored. |
  | OPP | `V. Seals…`, `4.2 Assessment:`, `1)` … `12)` | `§V`, `§4.2`, `§4.2(5)` | Roman-numeral top level; three different item markers (`1.`, `1)`, `a.`). |
  | LANDSCAPE / BPP | headings only | page + heading | No clause numbering. |

  **Verified against the shipped PDFs, 2026-10-18.** A throwaway parser was run over both documents before any code was written; it invalidated several assumptions that read plausibly in review. These are the realities Sub-plan B must be written against:

  1. **SAOSO part letters are running page headers, not body headings.** `SECTION A` never appears as a body heading — only in the table of contents. `SECTION B` is a running header on **22 body pages** (p23–p89) and `SECTION C` on **3** (p94, p95, p97, above each of its appendices). All are indented ~30–63 columns. The letter must be read from the page header and **carried forward**, because only 22 of 98 body pages carry one — the letter is printed on one side of each spread only. *Corrected 2026-10-19 by measurement: the earlier claim that `SECTION C` never appears in the body was wrong; it heads Section C's three appendices.*
  2. **The TOC matches the clause pattern** (`1.         Introduction - …    4`). Page-aware extraction must exclude the TOC pages explicitly, or the TOC is ingested as 60+ duplicate clauses.
  3. **The part letter is mandatory, not decorative.** 30 distinct clause numbers occur in more than one part — `1.1`, `1.1.1`, `2`, `3`, `4` among them. A bare `1.1.1` is ambiguous between Section A and Section B. This is why `S20.1.1` carries the part and a bare `20.1.1` cannot.
  4. **Appendix boundaries are detectable in the body; their canonical labels are not.** All twelve appendix headings **do** appear in the body in UPPERCASE — `APPENDIX 1` (p71), `APPENDIX 2` (p77), `APPENDIX 3` (p80), `APPENDIX 4, TABLE 1` (p82), `APPENDIX 4 TABLE 2:` (p84), `APPENDIX 5:` (p85), `APPENDIX 6a:` (p86), `APPENDIX 6b:` (p87), `APPENDIX 7:` (p89), `APPENDIX A.` (p94), `APPENDIX B.` (p95), `APPENDIX C.` (p97) — but across four separator shapes (`, ` / `:` / `.` / none) and indentation 0–62 columns, so one tolerant regex is required. The TOC supplies the **canonical label** (`Appendix 4. Table 2`, where the body prints `APPENDIX 4 TABLE 2:`) and the page, so it is a normaliser and cross-check rather than the only boundary source. Two traps: a title-case `Appendix \d+` regex matches nothing in the body but **false-positives on p63**, where `Appendix 4.` begins a mid-sentence line; and the body refers twice to appendices that do not exist — `Appendix 9` (p11, a typo in the standard) and `Appendix 6` (p44, where only 6a and 6b exist). *Corrected 2026-10-19 by measurement; A10's `MANIFEST.json` had already observed the uppercase body heading.*
  5. **OPP headings are indented 0–7 spaces** (`VI.` at 6, `4.5` at 4). A column-0 regex misses §VI and §4.5 — the two sections the review added. Item markers also vary: `1.` in §4.1, `1)` in §4.2, `a.` in §4.5(2).
  6. **Depth 3 is achievable and depth 4 is not.** `§4.5(2)(c)` parses correctly. Nothing deeper exists to parse (see the bound above).

  Every one of these was found by running the parser, not by reading the documents — which is the argument for building the 20-minute verification script before Task B2 rather than after it.

  Extracting citations is the one genuinely standard-specific step in ingestion, so it is a strategy selected by data rather than hard-coded: adding a standard means adding a parser, not rewriting the pipeline.

  **Reference depth is bounded at three levels.** `section_ref` is always present and always reliable. `sub_ref` is emitted **only where the source actually enumerates a clause** — `§4.1(1)` (5 days' notice), `§4.1(2)` (questionnaire 3 days ahead), `§4.2(5)` (conclusion within 5 days), `§4.2(12)` (traceability), `§4.5(2)(c)` (the minuted meeting). It is never inferred. **Depth four does not exist in the source documents and must never be synthesised:** OPP §4.5 has no item 3 (numbering runs 1, 2, 4, 5), the §4.5(2)(c) attendee list is half-numbered and split by a page footer, and the warnings regime and serious-misconduct examples carry no numbers at all. Those unnumbered blocks get a content-derived `anchor` (`4.5#action-first-warning`) instead of a fabricated reference.

`DocumentChunk.section_ref` is mandatory and human-meaningful because it is the citation shown to the user — a chunk the user cannot locate in the standard is not a citation. `sub_refs` holds character offsets rather than separate chunks: splitting at every enumerated item would fragment the OPP into several hundred context-poor chunks and degrade retrieval, so the chunk stays section-level and a citation slices the text it needs. A citation whose `sub_ref` is absent from the chunk's `sub_refs` is invalid, which makes "the bot cited something that does not exist" a test failure rather than a production surprise.

### 4.6 Chat — `core/models/_chat.py`

```
ChatSession         public_uuid, user(nullable FK), standard_set(FK), created_at,
                    ip_hash, user_agent
ChatMessage         session, role, content, latency_ms, model, prompt_tokens,
                    completion_tokens, retrieved_chunks(M2M -> DocumentChunk)
EscalatedQuery      message, question, reason, status, answered_by, answer, answered_at
```

Chat lives in `core`, not `knowledge`, because it is user-facing and user-owned: `ChatSession.user` is nullable, so anonymous public chat works, and a session **attaches to a `User` the moment that visitor creates an account** — which is how public engagement graduates into membership (§3.1). Retrieval is a call into `knowledge`; chat history is not knowledge's business. A session is pinned to the `StandardSet` it was started against (§4.5), so answers stay coherent even if the deployed corpus later changes underneath it.

`EscalatedQuery.reason` ∈ `INSUFFICIENT_CONTEXT`, `NO_CITATIONS`, `CITATION_AUDIT`,
`USER_REQUESTED` (D54).

### 4.7 Answer storage strategy

`prd.md` specified a single `AssessmentResponse.answers` JSON blob. **That is rejected for the queryable layer.** A versioned template with ~60 questions × 1–3 verdicts per category can be answered in JSON, but the committee's core jobs are inherently *cross-farm queries*: "every Critical finding this quarter", "every farm non-compliant on `V4` (on-farm composting)", "which farms need a soil test", "gap analysis against SAOSO §20". A JSON blob cannot serve these without per-row deserialisation.

**Resolution — write both:**
- **Normalised** `AssessmentAnswer` / `AssessmentVerdict` rows → reporting, gap analysis, queries, dashboards.
- **Raw** `SyncReceipt.raw_payload` (immutable) → audit, replay, and re-parsing if a normalisation bug is found.

Total row volume is trivial (~1,000 rows/visit for Postgres) and this preserves Harvester's Relational Integrity and Encapsulated Query Logic principles.

### 4.8 Extensibility — code versus data

The platform has to be retargetable: a different standard, or a different PGS group, with as little code change as possible. One rule makes that achievable, and everything else follows from it:

> **Code encodes the PGS process. Data encodes the standard and the group.**

The process — visits, committees, verdicts, findings, corrective actions, decisions, In-Conversion, aggregation, discipline — is what IFOAM means by a Participatory Guarantee System, and it is common to every PGS group. It belongs in code. The standard being assessed against, the seals issued, the document corpus, the categories, and the questions are all data, seeded per deployment.

**Data — swap without touching code:**

| Concern | Where | What changes |
|---------|-------|--------------|
| The standard corpus | `StandardDocument` + `DocumentChunk` | Ingest a different PDF; `section_scheme` selects the section-reference parser. SAOSO v2.1 → EU 2018/848 → IFOAM COROS is a data change. |
| Which documents the chatbot answers from | `StandardSet` | Retrieval is scoped to a set, so corpora coexist and switch per session. |
| Seals issued | `Seal` | Rows, seeded active or inactive. Adding or retiring a seal is data. |
| Assessment categories | `Category` | Rows. The current set is Outeniqua/SAOSO data, not a code enum. |
| Questions and verdicts | `AssessmentTemplate.schema` (JSON) | Imported from a file via `load_template`. A new standard's questionnaire is a new template file. |
| Member expertise | `Member.expertise` → `Category` | Follows the categories above. |
| Severity *wording* | per-deployment setting | FORM states the three levels *"are to be discussed and interpreted at annual meetings"*, so the group's own wording is configuration. The three levels themselves are PGS-universal and stay in code. |
| Group identity, fee bands, catchment, pledge text, committee roster | per-deployment seed + settings | Content, not logic. |

**Code — PGS-process semantics, deliberately not configurable:** the four certification outcomes; the finding and corrective-action lifecycle including escalation to membership termination; In-Conversion periods; aggregation rules; visit composition and the numeric pre-visit rules; and the offline capture and sync protocol. Making these configurable would let a deployment define a process that is no longer a PGS.

**Retargeting checklist — what an agent must do to stand up a new group or standard:**

1. `seed_deployment` — `StandardSet`, `Seal` and `Category` rows, group identity and settings.
2. `ingest_standard` — once per document; confirm section references parsed correctly.
3. `load_template` — one questionnaire JSON per category.
4. Set deployment settings: group name, catchment, fee bands, pledge text, severity wording, language.
5. Swap design tokens and content pages.

Steps 1–3 are data and management commands; 4–5 are content. **No model changes, no migrations, no new services.** That is the acceptance test for this section: a retarget must not require a migration. It also makes the corpus genuinely portable — swapping documents in and out is the whole of the `knowledge` app's surface area.

---

## 5. Bounded Contexts & File Map

O4 is resolved (§18.2): **the standards corpus is a library in `knowledge/`, and everything user-facing is in `core/`.** The boundary is one-directional — `core` may import `knowledge`; `knowledge` must never import `core`.

| Layer | Modules |
|-------|---------|
| `core/models/` | `_core.py`, `_assessment.py`, `_certification.py`, `_aggregation.py`, `_chat.py` (+ `__init__.py` re-exports) |
| `knowledge/models.py` | `StandardDocument`, `DocumentChunk` — the entire app |
| `core/views/` | `_public.py` (marketing, registry, farm profile), `_verify.py` (QR verification), `_chatbot.py` (chat UI — in `core`, see §4.6), `_portal.py` (farmer account), `_assessor.py` (PWA shell + JSON API), `_committee.py`, `_admin.py` |
| `core/forms/` | `_application.py`, `_questionnaire.py`, `_committee.py`, `_decision.py`, `_membership.py` |
| `core/services/` | `_assessment.py`, `_sync.py`, `_media.py`, `_certification.py`, `_aggregation.py`, `_registry.py`, `_membership.py`, `_pdf.py`, `_reporting.py`, `_notifications.py`, `_storage.py`, `_evaluation.py`, `_chatbot.py` |
| `knowledge/services.py` | hybrid retrieval (FTS + pgvector fused by RRF), optional rerank, chunking, embedding |
| `core/tasks/` | `_sync.py`, `_media.py`, `_transcribe.py`, `_pdf.py`, `_notifications.py`, `_maintenance.py` |
| `knowledge/tasks.py` | `ingest_standard` |
| `core/tests/` | `test_<domain>.py` mirroring services |
| `core/templates/` | `pwa/`, `public/`, `portal/`, `committee/`, `pdf/` |
| `core/static/pwa/` | `app.js` (+ `modules/`), `sw.js`, `styles.css`, `vendor/` |
| `core/templatetags/` | `pgs_extras.py` |
| `core/management/commands/` | `load_template` (import an `AssessmentTemplate` JSON), `seed_deployment` (categories, seals, standard sets, committee roster) |
| `knowledge/management/commands/` | `ingest_standard` |

**Static vendor set** (self-hosted, no bundler): `localforage.min.js`, `signature_pad.umd.min.js`, `htmx.min.js`, `qrcode.min.js`. HTMX is vendored as a single file, so permitting it (D1) does not introduce a build step; it is used on the public site, farmer portal and registry filters, and deliberately **not** in the offline assessor PWA, which stays plain ES modules so the cached shell remains small and auditable.

---

## 6. Service Layer & Data Flow Contracts

Illustrative contracts for the load-bearing services. Every public service method carries one (Homtini §1.2); every signature is type-hinted and returns `@dataclass(frozen=True)` where a compound value is returned (Homtini §1.3).

```python
def sync_visit_text(envelope: VisitSyncEnvelope) -> SyncResult:
    """
    In:
        envelope: VisitSyncEnvelope (client_uuid, farm_id, device_id, template_versions,
            answers, verdicts, findings, signatures, participants) — all already validated
            client-side against the frozen template schema.
    Out:
        SyncResult (farm_visit_id, assessment_ids, accepted_verdict_count, rejected: list[Rejection])
    Side Effects:
        Writes FarmVisit, Assessment, AssessmentAnswer, AssessmentVerdict, Finding,
        Signature, SyncReceipt; enqueues finalise_visit.
    Idempotency:
        Keyed on envelope.client_uuid. A replay returns the original SyncResult unchanged.
    Fails:
        UnknownTemplateVersionError: no active AssessmentTemplate for the category/version.
        SchemaValidationError: payload does not conform to the frozen template schema.
        MembershipNotEligibleError: farm's member is not fully paid up.
    """

def store_media_item(visit_id: int, client_media_uuid: UUID, kind: MediaKind,
                     blob: BinaryIO, metadata: MediaMetadata) -> EvidencePhoto | VoiceNote:
    """
    In:
        visit_id: int; client_media_uuid: UUID (idempotency key);
        kind: MediaKind (PHOTO | VOICE);
        blob: BinaryIO;
        metadata: MediaMetadata (caption, captured_at, exif_gps, consent_given,
            mime_type, duration_ms, sha256)
    Out:
        EvidencePhoto (id, url, derivative_url) | VoiceNote (id, url, transcript_pending)
    Side Effects:
        Validates magic bytes and the per-kind size cap, stores the original in the
        private media root, generates a public derivative when kind is PHOTO, writes
        the row, and enqueues transcribe_voice_note when kind is VOICE.
    Idempotency:
        Keyed on client_media_uuid; a replay returns the existing row.
    Fails:
        UnsupportedMediaError, MediaTooLargeError, ConsentRequiredError,
        VisitNotSyncedError.
    """

def finalise_visit(visit_id: int) -> VisitFinalisation:
    """
    In:
        visit_id: int
    Out:
        VisitFinalisation (pdf_path, certificate_preview, notifications_queued)
    Side Effects:
        Compiles Sheet J PDF via WeasyPrint, sets status SYNCED -> UNDER_REVIEW,
        queues committee notification. Idempotent on visit_id.
    Fails:
        IncompletePhotoQueueError: photos still outstanding; retried by task policy.
    """

def decide_certification(visit_id: int, decision: DecisionInput) -> CertificationOutcome:
    """
    In:
        visit_id: int; decision: DecisionInput (outcome, rationale, product_outcomes,
            notifiable_exceptions, decided_by)
    Out:
        CertificationOutcome (decision, certificate | None, actions_created)
    Side Effects:
        Writes CertificationDecision, ProductOutcome rows, CorrectiveAction rows,
        optionally issues Certificate + pdf; bumps Farm.current_status.
    Fails:
        MembershipNotEligibleError: member is not fully paid up (OPP 2.3).
        OpenCriticalFindingError: outcome CERTIFIED blocked while a Critical action is open.
        NotFinalisedError: visit is not yet SYNCED/UNDER_REVIEW.
    """

def answer_question(session_uuid: UUID, question: str) -> GroundedAnswer:
    """
    In:
        session_uuid: UUID; question: str (validated: non-empty, <= 500 chars)
    Out:
        GroundedAnswer (text, citations: list[Citation], insufficient_context: bool,
            escalated_query_id | None)
    Side Effects:
        Writes ChatMessage rows and, when ungrounded, an EscalatedQuery.
    Fails:
        RateLimitedError: caller exceeded the per-IP question budget.
        UpstreamModelError: Gemini unavailable (no fabricated fallback answer).
    """

def compile_outcome_pdf(visit_id: int, kind: PdfKind) -> Path:
    """
    In:
        visit_id: int; kind: PdfKind (SHEET_J | FULL_REPORT | CERTIFICATE)
    Out:
        Path to the rendered PDF in the configured storage backend.
    Side Effects:
        Renders a WeasyPrint template with a frozen context; writes a file.
    Fails:
        WeasyPrintRenderError (never returns a partially written PDF).
    """
```

---

## 7. Flow A — Membership & Application

1. Prospective farmer self-registers (`FARMER`), creating `User` + `Member{status: APPLICANT}`.
2. POPIA consent captured explicitly at registration (`popia_consent_at`), with purpose-specific consent recorded separately for: assessment processing, public farm profile, and photographic publication.
3. Applicant signs the **farmer member pledge** — `WRITTEN`, or `VERBAL_RECORDED` with witness + evidence photo for members unable to read/sign (OPP §I.2).
4. Applicant ticks the categories sought (FORM A) → creates one `FarmCategory` per tick.
5. Applicant declares annual turnover → determines `AssessmentFee.turnover_band` on the OPP §2.3 scale.
6. Applicant completes the **Basic Production Principles** and **SAOSO** familiarisation attestation (FORM 7.a header: *"I am aware of/have read the Basic Production Principles YES/NO"*).
7. Membership fee recorded; on payment, `Member.status → ACTIVE` and `is_paid_up → True`.
8. Administrator schedules a `FarmVisit`; system enforces OPP §4.1 notice: **≥5 days** between scheduling and visit date, and the completed questionnaire must be available to the team **≥3 days** before.

**Rule enforced in `_membership.py`:** no assessment may be scheduled for a member who is not `ACTIVE` and `is_paid_up`.

---

## 8. Flow B — Pre-Visit Questionnaire (farmer account)

**Decision taken: farmers have accounts** (Q3-A), superseding `prd.md`'s silence on this flow. Sheet 6 is a two-role document — *"The administrator on the farm visit will complete the sections in grey as the farm assessment report"* — and the white half is inherently farmer-supplied.

1. From the farmer portal, the applicant opens the questionnaire for each `FarmCategory` on their application. This resolves to the **frozen** `AssessmentTemplate.schema` for that category, rendered server-side, with only `respondent == FARMER` questions visible.
2. Answers autosave (`AssessmentAnswer`), keyed by `question_key`, so a farmer on a poor connection never loses work. This is an online-first form — it is *not* part of the offline PWA.
3. The portal shows readiness as a checklist: attachment-required questions (soil test results, farm sketch, flow diagrams for agro-processing — FORM Sheet I §2) are visibly unsatisfied until an `EvidenceDocument` is uploaded. The farmer is also told what records the assessor will verify at the visit (sales records, input purchases, input/output reconciliation), so the visit is not the first time they hear it.
4. Status → `QUESTIONNAIRE_SUBMITTED`. Administrator notified; template snapshot frozen onto the `Assessment` at this point.
5. Administrator reviews 3 days out and may request clarifications, which loop back to the farmer as a task list.
6. `PREP` stage — participants, roles and guest list are assembled into `VisitParticipant` rows before the visit.
7. **Offline pack download:** admin triggers "Prepare visit pack", which bundles the frozen template schemas, farm metadata, prior visit findings and open corrective actions into an IndexedDB payload for the assessor device (`§9`).

Prior-visit corrective actions are surfaced in the pack because PREP explicitly requires *"Last visit — list any corrective actions (if applicable)"* to be opened at the start of the visit. D45 makes the same list available to the **connected** capture in `1a` (a server-side fetch, not the pack), so the review is not an offline-only feature.

---

## 9. Flow C — Offline-First Farm Visit (PWA)

**Confirmed: full offline-first (Q2-A).** This is the hardest and highest-value part of the system.

**Shell.** Service Worker registers on first visit. Install prompt encourages "Add to Home Screen" — this matters both for UX and because it improves storage durability on iOS. The SW caches the app shell, `styles.css`, vendored JS and fonts under a **versioned cache name** (`pgs-shell-v{N}`). Navigation requests are stale-while-revalidate; API routes are never cached. When a new SW is waiting, the UI shows a non-blocking "Update available — sync first" affordance rather than `skipWaiting()`-ing mid-visit.

**Storage.** IndexedDB via `localforage` with explicit stores: `visitPacks`, `visitDrafts`, `photoQueue`, `mediaQueue`, `signatureQueue`, `outbox`. On pack preparation the app calls `navigator.storage.persist()` and `navigator.storage.estimate()`, and displays free-space headroom.

**Capture.**
- Questions render from `visitPacks`. Taps, choices, notes and verdicts write to `visitDrafts` with a debounced (≈500 ms) flush.
- Verdicts are captured per `V#` field with an explicit compliant / non-compliant control and an optional note — mirrors the FORM exactly.
- A Finding is raised inline: severity (`Minor`/`Major`/`Critical`, with the verbatim FORM definitions shown as helper text), description, recommended action, due date.
- Photos are captured as **`Blob`s, not Base64** (rejecting `prd.md`'s stated approach: Base64 inflates storage ~33%, spikes phone memory, and requires a decode step server-side). Originals are retained at full resolution for evidence integrity; a ≤2048px derivative is generated for the public site.
- **Voice notes (D6) — post-MVP.** *(Designed here; recorder UI and transcription built after the MVP, §17.2.)* Risk assessments, findings and free-text notes can be dictated instead of typed, via `MediaRecorder`. Recordings are `Blob`s in a `mediaQueue` store and upload exactly like photos. Output format differs by platform — Safari emits `audio/mp4`, Chromium `audio/webm;codecs=opus` — so the server accepts both and stores `mime_type` verbatim rather than attempting on-device transcoding. The recorder will not arm until the assessor acknowledges *"all present consented to being recorded"*, stored as `VoiceNote.consent_given`: a voice is personal data under POPIA, and PREP's photograph-consent requirement extends directly to audio. A voice note is available for **any** text field, not only the risk assessment.
- Signatures via `signature_pad`: assessor, host farmer applicant declaration, and PGS group representative (`§4.2`). Small PNGs, so they travel in the text payload rather than the photo queue.

**Quota safety.** If `estimate().quota - usage` falls below a threshold, the app warns before capture and offers an immediate sync attempt. If `QuotaExceededError` is thrown on write, capture halts with an explicit, non-dismissable message — a lost assessment is worse than a stopped one.

**Sync affordance.** An always-visible sync chip reports one of: offline / N items queued / syncing / synced. `navigator.onLine` triggers an *attempt*, never a *guarantee* — it is unreliable on iOS Safari. A manual "Sync now" button is always present, and the app attempts sync on `online`, on visibility regain, and on a 60s timer while anything is queued.

---

## 10. Flow D — Split-Sync Protocol

Supersedes `prd.md` §4's "Split-Sync Protocol", adding the idempotency and partial-failure semantics it omitted.

1. **Client identity.** A `client_uuid` (uuid4) is minted when the visit is opened in the field and persisted in `visitDrafts`. It is the idempotency key for the entire visit.
2. **Phase 1 — text.** `POST /api/v1/visits/sync/` with the full text envelope: answers, verdicts, findings, signatures, participants. Server validates against `Assessment.template_schema`, and in one `transaction.atomic()` writes `SyncReceipt`, `FarmVisit`, `Assessment*`, `Finding`, `Signature`. Returns `{farm_visit_id, assessment_ids}`.
   - Replay of the same `client_uuid` returns the original result and writes nothing (unique constraint on `SyncReceipt.client_uuid`). **This is what prevents duplicate audits on flaky rural networks.**
3. **Phase 2 — binary media.** A background queue iterates `photoQueue` and `mediaQueue` and `POST`s each item individually as `multipart/form-data` to `/api/v1/visits/<id>/media/`, each carrying its own `client_media_uuid`. Rationale (from `prd.md`, retained, and it applies equally to audio): per-item requests avoid HTTP timeouts on a 15-photo submission.
   - Per-item state (`pending` / `uploading` / `uploaded` / `failed`) means a dropped connection resumes rather than restarts. Exponential backoff with jitter; an item that fails 5× is flagged for the assessor to retry manually rather than being silently dropped.
   - Media queued **before** Phase 1 completes is held; the server rejects an item whose `visit_id` does not exist yet. Voice notes are small enough (~1 MB/minute compressed) to share the photo queue without special handling.
4. **Phase 3 — finalisation.** When the outbox and photo queue are both drained, the client fires `POST /api/v1/visits/<id>/finalise/`, which enqueues `finalise_visit` (Celery): compile Sheet J PDF → notify committee → set `UNDER_REVIEW`. Idempotent on `visit_id`.
5. **Ordering guarantee.** Text always precedes photos; finalisation always follows both. The client enforces this; the server independently enforces it by rejecting out-of-order calls.

---

## 11. Flow E — Review, Decision & Certification

1. **Prior actions first.** Every open corrective action from the farm's previous visits is opened at the start of capture (PREP: *"Last visit — list any corrective actions"*). One `PriorActionReview` records `VERIFIED | PARTIAL | NOT_MET` with a note; a `NOT_MET` Critical action sets `ESCALATED`. `finalise_visit` refuses while a prior open action has no review (D45).
2. **Conclusion captured.** `SocialEquity` (Sheet I §1) and one `RecordCheck` per Sheet I §2 item are recorded with the findings. `MISSING` requires a note and may support a Finding; it is a recorded fact, not an omission, and does not auto-create a finding (D45).
3. `finalise_visit` produces the Sheet J PDF; the committee receives it and the structured findings. Visit is `UNDER_REVIEW`.
4. If members cannot conclude on the day, OPP §4.2(5) allows up to **5 days** after the visit — modelled as `FarmVisit.review_due_on`.
5. `decide_certification` records one of the four outcomes and, per OPP §4.2(9), the peer-review knowledge-exchange narrative is captured in `knowledge_exchange_narrative` (FORM Sheet J: *"Key knowledge captured during the farm visit"*).
6. **Outcome rule.** `CERTIFIED_ORGANIC` requires no `MAJOR` or `CRITICAL` action still `OPEN`, `OVERDUE` or `ESCALATED`. If one exists, the only positive outcome is `PENDING_CORRECTIVE_ACTION`; a product that fails on its own is `NOT_ENDORSED` with a reason. Homtini 2022 — a Critical (ducks not certifiable) and a Major (documents outstanding) — is exactly this case. Minor actions do not block certification; they are continual improvement.
7. **Corrective-action follow-up.** Every action appears in the farmer's portal with its due date. The farmer uploads the requested evidence (TDS, non-GMO letter, invoice, compost ingredients list); the upload is an `EvidenceDocument` linked to the action and sets `SUBMITTED`. The reviewer moves it to `VERIFIED`/`CLOSED`; `OVERDUE` is derived from `due_on` (D45).
8. **Gating rules enforced server-side:**
   - `CERTIFIED` is blocked while any **Critical** corrective action is `OPEN`/`OVERDUE` (§2 definitions), and by the outcome rule in step 6.
   - Any certificate issuance is blocked unless `Member.is_paid_up` (OPP §2.3).
   - A Critical action that lapses → `ESCALATED`, surfaced to the discipline workflow (OPP §4.5), which can reach `REVOKED` certificate status and `TERMINATED` membership (OPP §4.6).
   - `finalise_visit` refuses an unanswered verdict or required sub-verdict, a missing required signature (unless a recorded refusal with a reason exists), an unset `RecordCheck`, or an unreviewed prior action — and returns **every** unmet item, not the first (D45).
9. On `CERTIFIED`, a `Certificate` is issued with `seal=PGS_ORGANIC_CERTIFIED`, `expires_on = +12 months`, a `public_uuid`, and a PDF bearing the QR code. `IN_CONVERSION` issues the other seal. `NOT_ENDORSED_RESCHEDULE` issues nothing and sets `next_visit_due`.
10. Any granted notifiable exemption is recorded as a `NotifiableExemption` against its `standard_ref`, with rationale, grantor and date, and appears in the committee reporting export **with a `reported_to_pgs_sa_on` field that must be filled before the visit can be `CLOSED`** — the OPP requires the grant to be documented *and* reported, and an unrecorded notification is the failure mode.
11. Products are recorded as `ProductOutcome` rows per category, **including products that were not endorsed** with a reason. The live records already carry exclusions — *"Excluded: pork production (reschedule farm visit), chicken production (not proposed for certification), chard (treated seed)"* — so "not endorsed" is a first-class state with a reason, not an absence of a row. A single visit may also produce different product sets across two visits in one year (The Red Barn was visited twice in October 2025, once for macadamia and once for vegetables and fruit), so outcomes belong to the visit, not the farm.
12. `Farm.current_status` and `next_visit_due` update; annual reassessment is scheduled (OPP §4.3: *"All producers will be assessed annually"*).

---

## 12. Flow F — Public Registry, Verification & QR

**Verification page** — `GET /verify/<certificate.public_uuid>/`. This is the trust surface. It shows: farm name and nearest town; the seal (exact OPP §V wording); validity window; the four-outcome decision with date; products endorsed per category with `ORGANIC` / `IN_CONVERSION` status; the last assessment date; and an explicit statement of what the certificate does **not** claim. **`NOT_ENDORSED` products are never shown publicly.** Every scan writes a `PublicVerificationEvent` so the group can see whether the QR is actually being used.

**Claim discipline.** The public surface may only reproduce language the standard actually supports: the four outcomes from FORM Sheet I/J, and the seals from OPP §V — of which there are **three**, not two. It must not invent claims. The live site describes Favour Farm's chickens as *"certified pasture raised on certified organic pasture, GMO free"*: "pasture raised" is the third OPP seal, whose criteria the standard itself says are *"forthcoming"*, and "GMO free" is not a PGS certification outcome at all. The platform **does not render it at all**: the seal ships inactive (§4.3, D11) and is never published, because a mark whose criteria the standard itself calls *"forthcoming"* cannot be substantiated to a consumer. "GMO free" is treated as a producer statement, never as a PGS endorsement. This is the difference between a verification page and a marketing page.

A verification page must never expose: cell numbers, email addresses, GPS, census data, findings detail, or corrective actions. It is a status surface, not a case file.

**Registry** — searchable, filterable farm directory (by product, category, region), showing only `publish_consent=True` farms with a valid or in-conversion certificate. Indexable for SEO.

**Farm profile** — the public-facing half of Sheet J: *"Background/previous history"*, *"Key knowledge captured during the farm visit"*, and a **committee-curated** subset of *"Concerns raised during the visit & recommendations"*. Concerns are published only when a committee member explicitly marks them public — an unredacted finding must never leak automatically.

**Marketing surface** — this application **is** the PGS Outeniqua public website (D8); the WordPress site is retired, not run alongside it, and **the chatbot lives on the same site** rather than as a separate property. It carries home, about the PGS and its six basic elements (LANDSCAPE), the Basic Production Principles, how to join, fee schedule, member/committee info, news, and contact. Existing WordPress content is copied across and restyled — a content and design task, not a data migration — so it does not gate the platform build. A redirect map from the old URLs is maintained so existing links and search rankings survive the cutover.

**Document hosting.** The live `/forms/` page currently links the Basic Production Principles, the SOPs, the certification landscape and the three paper checklists to permission-gated Google Drive files, and the assessment workbook to a Google Sheet. The platform hosts these itself under a public `/documents/` page with stable URLs, retiring the Drive dependency. Historical application dossiers and farm visit reports (also behind Drive, granted on request) are attached to their `FarmVisit` as `EvidenceDocument` records with the same permission model.

### 12.1 Migrating the existing registry

The live WordPress site is already a de-facto registry, and it is detailed enough to seed the platform with **real** records rather than placeholders — which is what makes MVP 0 (§19) a real product rather than a brochure. What it contains:

- **Members by year.** 2026 farmer members (4) and 2024 farmer members (9); 2026 consumer members (about 24 named people) and 2024 consumer members (12). Membership is annual, consistent with the fee cycle and the "payable by end of February" rule.
- **Endorsed farms with dates and full product lists**, back to 2020 (Favour Farm 2026; The Red Barn, Homtini Farm 2025; Well I Am, Homtini 2022; Chillin Out, Well I Am, Homtini, Diepflook 2020–21), **including exclusions**.
- **Pending visits**, listed as date-TBC: Organic Valley (broilers), La Route du Paradis, Hamel en Harden. These become `FarmVisit` rows in `SCHEDULED` state.
- **An input certification** (Diepflook: fish/kelp hydrolysate), which confirms the Input Supplier category is real rather than speculative even though FORM Sheet F is marked "in development".

Three consequences for the migration:

1. **The member/certificate distinction is already understood and must be preserved.** The live farmer-members page carries the disclaimer: *"membership does not mean that a farm has been certified by the PGS... Endorsed farmers are listed in the 'farm status' section."* The registry must never conflate `Member` with `Certificate` — that is a trust claim, not a display nicety.
2. **Consent must be captured for already-published personal data.** Farmer and consumer *names* are published today, and the platform will carry them forward. Migration records explicit `publish_consent` per farm and per consumer member rather than assuming the WordPress publication was consent, and `PublicVerificationEvent`-style allow-list serialisation keeps census and contact fields out.
3. **Farm identity must be reconciled, not copied.** See `FarmAlias` (§4.1). Copying the inconsistent historical spellings verbatim would fork farms and silently break verification lookups.

---

## 13. Flow G — Grounded RAG Chatbot

Replaces `prd.md` §4's substring-detection contract with a structured one. The chatbot is a surface *within* the main public site (§12), sharing its session, styling and navigation — it is not a separate deployment or a separate property.

**Ingestion.** `python manage.py ingest_standard --doc saoso --version 2.1 --file <pdf>` → Celery `ingest_standard`: page-aware text extraction, section-reference detection per the scheme in §4.5 (`S20.1.1` for SAOSO, `§V` / `§4.2(5)` for the OPP, `Appendix 1` / `Appendix 4. Table 2` / `Appendix 6a` for appendices, segmented from the TOC page map because the body carries no appendix headings), `sub_refs` offset mapping, chunking on heading boundaries with ~800-token targets and overlap, `tsvector` population, and embedding via Gemini. Re-ingestion is versioned and idempotent on `sha256`; `superseded_by` links v2.1 → v2.2 without deleting history, because assessments cite the version in force at the time.

**Retrieval — hybrid, fused.** Postgres full-text (`websearch_to_tsquery` over `search_vector`, ranked with `ts_rank_cd`) and `pgvector` cosine similarity run independently; results are fused with Reciprocal Rank Fusion (k=60) so neither lexical nor semantic recall dominates. Optional Gemini rerank over the fused top-20 → top-5. Retrieval is **scoped to the session's `StandardSet`** (§4.5), and the scope is applied *before* ranking — so the corpus boundary is not a rule the model has to remember, it is a filter it cannot escape.

**Generation.** Gemini (Harvester precedent — `google-generativeai`) with `response_mime_type="application/json"` and a strict schema:

```
{ "answer": str, "citations": [{"section_ref": str, "quote": str}], "insufficient_context": bool }
```

The system prompt forbids outside knowledge and requires every assertion to be traceable to a supplied chunk.

**Escalation.** The UI renders `"I cannot find a definitive answer in the SAOSO standards."` — the exact string from `prd.md`, preserved for UX stability — whenever `insufficient_context` is true **or** `citations` is empty **or** a cited `section_ref` was not in the retrieved set. Detection is on the structured flag, not on scraping the model's prose. This is the fix for the brittle contract. The escalation control creates an `EscalatedQuery` for administrative follow-up.

**Guardrails.** Per-IP rate limiting on the public endpoint; 500-character question cap; conversation-window cap; token-usage logging per message; refusal to answer off-topic (out-of-scope) questions rather than using general knowledge; no farmer-identifying data ever included in a prompt. Answers are cached by normalised question hash to contain cost.

**Standards scope.** SAOSO v2.1 2026 (101 pages) and the Outeniqua SOPs / OPP / BPP, each ingested as its own `StandardDocument` so a citation names its source.

---

## 14. Flow H — Reporting & Committee Administration

The PRD's stated purpose is to *reduce administrative overhead*; `prd.md` does not model the reporting this implies. Included:

- **Farm visit log** for committee review (PREP, Committee Actions): farm details, outcome, participant count, other PGS farms visited, risk assessment, notifiable exceptions.
- **Committee reporting template** export for PGS-SA (XLSX via `openpyxl` / `django-import-export`).
- **Census report** — gender / age band / demographic group aggregates, which FORM A states are collected *"for census purposes (PGS SA & SAOSO collect this data to profile small-scale organic farmers in South Africa for advocacy & support purposes)"*.
- **Corrective action register** — all open/overdue findings across farms, the operational heart of following up (OPP §4.2(8)).
- **Standard gap analysis** — which SAOSO clauses produce the most findings, via `AssessmentVerdict.standard_ref` aggregation. This is the payoff of the normalised answer model (§4.5) and is directly useful to the group's own advocacy work.

---

## 15. Non-Functional Requirements

**POPIA / privacy.** Lawful basis recorded per processing purpose; separate consent for public profile, photographic publication, and **audio recording** — a voice is personal data, and third parties recorded during a visit have not consented merely by attending; census fields flagged sensitive and never serialised publicly; data-subject access and deletion paths; retention schedule (assessment records retained for the certification period plus the statutory window, with voice notes and transcripts following the assessment record); no sequential IDs on any public URL.

**Security.** CSRF on all state-changing endpoints; private evidence served **only** through authorised views handing off to nginx via `X-Accel-Redirect` (there are no signed URLs, because there is no S3 — D2); upload validation by magic bytes and per-kind size cap; `sha256` recorded per media item for chain-of-custody; rate limiting on the public chatbot and on authentication and account-recovery flows; no secrets in source (`.env` only).

**Observability.** `/health/` verifying DB, Redis, Celery broker and worker liveness, returning 503 on failure; Sentry on every exception path; `django-structlog` with `X-Request-ID` propagated from request → Celery task so a single assessor sync can be traced end to end.

**Reliability.** Every Celery task declares `autoretry_for` / `max_retries` / `default_retry_delay`; non-idempotent tasks opt out explicitly. Explicit `timeout=` on every external call (Gemini, SMTP).

**Performance.** `select_related` / `prefetch_related` on every relational access; cached registry and public profile reads; paginated listings; Sheet J compilation is always async.

**Compatibility.** Mobile Safari ≥16 and Android Chrome — they are the assessor's only tools. Touch targets ≥44×44 px; high contrast and large type for outdoor sunlight (an assessor reading a checklist in the Garden Route sun is the real design constraint). `MediaRecorder` output differs by platform (Safari `audio/mp4`, Chromium `audio/webm;codecs=opus`); both are accepted and the recorded MIME type is preserved. Offline behaviour verified on a real iOS device, not just a desktop emulator.

**Bilingual (D7).** English and Afrikaans are both **first-class**, not a later translation pass. `User.preferred_language` sets the default, every user-facing string is translated from the start, and the translation catalogues are part of the cached PWA app shell so the assessor's language works offline.

**Storage.** Filesystem `media/` mounted as a Docker volume and served by nginx — **no S3** (D2, aligning with Harvester BP). Because filenames are guessable, evidence originals live under a **private media root** and are never served directly: Django authorises the request and hands off to nginx via `X-Accel-Redirect` against an `internal` location. Public derivatives (≤2048px photos) live under a separate public root served directly. Filesystem storage makes **backup the single point of failure**: a scheduled backup of both the database and the media volume to an external local hard drive is a launch requirement, not a nice-to-have (R11). Local-drive backup protects against disk failure and bad deploys but **not** theft, fire or flood — accepted for a single-site community group, and the residual risk is recorded in R11.

---

## 16. Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | iOS Safari evicts IndexedDB, losing an in-progress visit. | High | `navigator.storage.persist()`, headroom checks, Add-to-Home-Screen prompt, aggressive sync-on-any-signal, and a visible queued-item count so the assessor always knows exposure. Accept residual risk; document it in the assessor SOP. |
| R2 | Duplicate assessments from sync retries. | High | `SyncReceipt.client_uuid` unique constraint; replay returns the original result. Verified by an explicit test. |
| R3 | Template edits corrupt historical assessments. | High | Full `template_schema` snapshot on the `Assessment` at freeze time; template edits create new versions; no assessment ever reads a live template. |
| R4 | RAG hallucination damages trust in the standards. | High | Strict JSON contract, mandatory citations, structured `insufficient_context`, escalation path, no-answer rather than guess. |
| R5 | POPIA breach via the public registry. | High | Allow-list serialisation on every public view; census fields hard-excluded; committee-marked public concerns only; verification page limited to status. |
| R6 | Photo and audio volume exhausts device storage. | Medium | Per-item upload with resume, ≥2048px derivative for public use, quota headroom display, server-side lifecycle policy. Note audio is far smaller than photos (~1 MB/minute), so voice notes do not materially add quota pressure. |
| R7 | Assessor device/browser incompatibility in the field. | Medium | Explicit compatibility target; test on a real device; degrade to a simple capture form when SW/IDB unavailable. |
| R8 | 30KB cap forces service fragmentation that obscures flows. | Medium | Vertical slicing on domain boundary; Data Flow Contracts make cross-module intent legible. |
| R9 | Public chatbot endpoint abuse / cost blowout. | Medium | Per-IP rate limits, question caps, answer caching, token accounting, spend alerting. |
| R10 | WordPress content copied across and restyled (D8) takes longer than expected, or the redirect map is neglected and the group loses search visibility. | Low | It does not gate the build; the redirect map is a launch checklist item; content is edited in place rather than mechanically ported. |
| R11 | Filesystem media is the only copy of evidentiary photos and PDFs; disk failure, a botched deploy, or silent backup failure destroys certification evidence. | **High** | Scheduled backup of the database **and** media volume to an external local hard drive. Critically: **the backup job must report failure** — a cron that dies quietly is worse than no cron, so success/failure is logged, alerted and surfaced, and the job is verified by a rehearsed restore before launch. Per-item `sha256` detects silent corruption. **Residual, accepted:** a local drive does not survive theft, fire or flood, so a second copy at another physical site is a known gap rather than an unconsidered one. |
| R12 | *(Post-MVP, when voice ships.)* Voice notes capture identifiable third parties without consent, or are recorded and never transcribed — useless as evidence and a POPIA liability. | Low *(rises to Medium when voice ships)* | Consent acknowledgement gates the recorder and is stored per note; automatic server-side transcription; a human-review flag on every transcript; notes that fail to transcribe are surfaced for attention rather than silently retained. |

---

## 17. Scope Boundaries

### 17.1 Out of scope (permanently)

Stated rather than silently omitted, so the exclusions are reviewable:

- **Payment gateway integration.** Fees are *tracked*; money is collected off-system.
- **Complaints, hearings and discipline workflow.** OPP §4.5–4.7 is a substantial legal-procedural domain. Represented only to the extent of `Certificate.REVOKED`, `Member.TERMINATED`, and `CorrectiveAction.ESCALATED`.
- **Digitising the participant checklists (7.a–7.c).** Participants continue on paper; the administrator's digital report is the record.
- **Aquaculture, Wine and Input Supplier Attestation.** Marked *in development* in FORM Sheets F/G/H. Schema exists behind a feature flag; forms and workflow do not. Note that **input supplier certification has nevertheless already happened** — Diepflook had fish/kelp hydrolysate certified in 2021 (§12.1) — so this is the most likely of the three to be needed first.
- **Native mobile apps.** PWA only.
- **Multi-tenant / multi-group operation.** Single-tenant blueprint per Harvester's Software Factory law. One deployment, one PGS group.
- **Offline operation of the farmer portal and chatbot.** Offline-first applies to the assessor field flow only.

### 17.2 Deferred to post-MVP

The schema and service interfaces for these are built and migrated **now**, so deferring them costs nothing structural — only the UI and background pipeline are postponed.

- **Voice notes (D6).** `VoiceNote`, the `mediaQueue` store, `store_media_item(kind=VOICE)`, the consent gate and the `transcribe_voice_note` task all remain in the design and ship in the initial migration. Deferred is the recorder UI in the PWA and the Gemini transcription pipeline. Free-text risk assessment and notes are in the MVP; dictation follows. This is the single largest deferral in the document, and it was chosen because voice adds a capture surface, a second binary queue, a transcription pipeline, a human-review step and a POPIA consent gate — the most expensive thing in the design to get wrong, and the least essential to proving the offline story.
- **The "PGS pasture-raised" seal (D11).** Not shipped. Seeded as an **inactive `Seal` row** (§4.3), so enabling it when the national working group publishes criteria is a data change. The two active seals are unaffected.

---

## 18. Decision Log

### 18.1 Architectural overrides (reviewed 2026-10-18)

| # | Override | Verdict |
|---|----------|---------|
| O1 | Normalised `AssessmentAnswer` / `AssessmentVerdict` rows alongside an immutable raw payload, instead of one JSON blob. | **Agreed** |
| O2 | Photos stored as `Blob`s in IndexedDB, not Base64. | **Agreed** |
| O3 | Escalation triggered by a structured `insufficient_context` flag, not substring detection. | **Agreed** |
| O4 | App structure: `knowledge/` as a one-way standards library, `core/` for everything user-facing. | **Resolved** — refined in response to user graduation; see 18.2 |
| O5 | Roles split into account roles and role-in-visit. | **Agreed, extended** — roles are *plural* per user; see §3 |
| O6 | Added missing models and sign-off gates (pledge, certificate, sync receipt, escalation reasons, fees, eligibility and Critical-action gates). | **Agreed** |
| O7 | *(found in review)* Students of the source documents surfaced three gaps closed in this revision: the **third seal** "PGS pasture-raised" (§4.3), the **aggregation of produce** sub-domain (OPP §VI, §4.4), and **committee positions** distinct from the `COMMITTEE` role (§3.2). | **Applied** |

### 18.2 O4 — App structure (resolved 2026-10-18)

**Resolved: the standards corpus becomes a library in `knowledge/`; everything user-facing stays in `core/`.** The dependency is **one-directional** — `core` may import `knowledge`; `knowledge` must never import `core` — enforced by an `import-linter` rule in CI.

The split line moved during review, in response to two requirements rather than to preference:

- **Public users graduate into members and assessors** (§3.1), so identity must be a single `User` in `core`. Chat sessions therefore belong to `core` as well, because they are user-owned and must attach to a person the moment a visitor creates an account.
- **`knowledge` shrinks to what is genuinely independent**: `StandardDocument`, `DocumentChunk`, and the retrieval and ingestion services. It has no users, no sessions, no views.

Explicitly **not** in `knowledge`: chat, chat history, escalations, and the chatbot view. All of those are `core`.

The first draft claimed "zero foreign keys in either direction". That was stronger than required and is withdrawn: the correct rule is a **directed** dependency, not mutual isolation.

`_assessment` was rejected as a separate app in every option: certification is a single aggregate rooted at `FarmVisit`, so splitting assessment from certification is a *subdomain* boundary, not a *context* boundary.

**Honest note on the trade-off (revised — D24).** The two reasons given above are weak, and this revision withdraws them. *"The retrieval engine may be swapped"* does not require a separate app — a model change is a model change wherever it lives. *"A one-way rule is worth enforcing with tooling"* does not either, because `import-linter` contracts operate on **module paths**, so `core/knowledge/` plus an `independence` contract would enforce exactly the same rule with the same tool.

The reason that does justify the split is mechanical and was missing from the first draft: **a Django app is a migration namespace.** The corpus has a lifecycle independent of every certification table — re-ingestion, `sha256` idempotency, `superseded_by` version chains, and the embedding dimension frozen by D3 (*"changing it later requires re-embedding the whole corpus"*). Those migrations have nothing to do with farm visits, and entangling them means a re-ingest requires reasoning about assessment history, while a certification hotfix rides on a corpus migration.

So Option B stands, on that ground rather than the original two. It is also cheapest **now**: MVP 0 is the knowledge app plus a site, so the boundary costs nothing today and would cost a refactor later. The residual argument for Option A is real but narrower than stated — it saves an `AppConfig` and a migration tree, at the price of the seam. **Option A remains defensible**; it is no longer the default.

Whichever is chosen, **app boundaries are Python module boundaries and do not constrain URLs.** The public site, farmer portal, assessor PWA, verification pages and JSON API are separate URL prefixes routed from the root URLconf:

```
/                    public site + chatbot
/portal/             farmer account
/assess/             offline assessor PWA
/verify/<uuid>/      certificate verification
/api/v1/             sync + media API
/admin/              staff
```

These may later be split across subdomains (`app.` vs `www.`) via `ALLOWED_HOSTS` and settings — still independent of app structure.

### 18.3 Resolved decisions

| # | Decision | Resolution |
|---|----------|-----------|
| D1 | HTMX permitted? | **Yes.** Vendored single file, no build step. Used on the public site, farmer portal and registry filters; **not** used in the offline assessor PWA, which stays plain ES modules. |
| D2 | Storage backend. | **Filesystem `media/` + Docker volume, served by nginx. No S3.** Separate private and public media roots; `X-Accel-Redirect` for protected evidence. **Backup target: an external local hard drive**, scheduled, with failure alerting and a rehearsed restore — a silent backup failure is the main risk (R11). |
| D3 | LLM and embedding provider. | **Gemini**, matching Harvester. Embedding model and dimension frozen in the migration; changing it later requires re-embedding the whole corpus. |
| D4 | Committee review cadence. | **Both.** Per-visit review is the default; the quarterly roll-up and committee report are a separate view over the same data, so batch is never assumed by the schema. |
| D5 | Farmer authentication. | **Password accounts**, with email verification and self-service reset. |
| D6 | Risk assessment field. | **Free text.** The proposed structured enum is dropped — reportability comes from search over the text, not from forcing a band. Voice notes were agreed in principle but **deferred to post-MVP** (§17.2); the schema ships now, the recorder UI does not. |
| D7 | Bilingual UI. | **English and Afrikaans are both first-class**, driven by `User.preferred_language`. Translated from the start; PWA catalogues cached in the app shell. |
| D8 | WordPress migration. | **This application is the PGS Outeniqua website, with the chatbot on the same site.** Content is copied and restyled rather than mechanically migrated; a redirect map preserves existing links. Does not gate the build. |
| D9 | Full-resolution originals. | **Retained.** The public surface serves a ≤2048px derivative. |
| D10 | Notification channel. | **Email** (Django SMTP). *The review answer was truncated at "email please, w" — recorded as email-only. Flag if something else was intended.* |
| D11 | The "PGS pasture-raised" seal. | **Deferred.** Modelled as a `Seal` row seeded **inactive**; enabling it later is a data change, not a migration. See §4.3. |
| D12 | Retargetability to another standard or PGS group. | **Required.** Code encodes the PGS process; data encodes the standard and the group (§4.8). Seals, categories, corpora and questionnaires are all data. **Acceptance test: a retarget must not require a migration.** |
| D13 | Aggregation (OPP §VI) — when? | **Data from MVP 1, workflow post-MVP.** The pre-visit questionnaire already asks every applicant whether they buy in produce and how they label it, so the fields must exist or the form cannot store its own answers. The case-by-case approval workflow — supplying-farm declarations, 6-month self-claim expiry, physical-separation checks — is deferred. |
| D14 | Canonical SAOSO citation format. | **`S20.1.1`** — the FORM's own convention, so a committee member can locate every verdict reference on paper. The section letter is stored separately to disambiguate (`1.1.1` occurs in both Section A and Section B). SAOSO's body prints `20.1.1.`; the earlier `B-20.1.1` was invented and is withdrawn. |
| D15 | OPP citation depth. | **`section_ref` + `sub_ref`, bounded at depth 3**, plus a content-derived `anchor` for unnumbered blocks. `sub_ref` is emitted only where the source actually enumerates: `§4.1(1)`, `§4.2(5)`, `§4.5(2)(c)`. §4.5 has **no item 3**, the `(c)` attendee list is half-numbered, and the warnings regime is unnumbered — so depth 4 does not exist and must never be synthesised. Chunks stay section-level with a `sub_refs` offset map (§4.5), so quoting never fragments retrieval. |
| D16 | Chatbot corpus. | **Four documents** — SAOSO v2.1, OPP, BPP, LANDSCAPE — in one `StandardSet`. The FORM workbook and the three participant checklists are `/documents/` downloads only, not corpus: the workbook is a questionnaire, and ingesting it would let the chatbot cite its own form. New documents are a `StandardDocument` row plus a re-ingest (D12), so the set may grow without a code change. |
| D17 | Chatbot scope and refusal wording. | **Wide corpus, group-naming refusal.** The bot answers from all four documents — the OPP answers questions SAOSO does not (fees, joining) — so the refusal becomes *"I cannot find a definitive answer in the SAOSO standard or the Outeniqua PGS documents."* The original SAOSO-only string reflected a PRD scope that no longer holds. |
| D18 | Afrikaans in MVP 0. | **Mechanism and shell, not content.** `preferred_language`, the catalogue plumbing and a human-translated app shell ship; page content and chatbot answers stay English until a named Afrikaans-speaking member reviews them. UAT Scenario 5 is judged against that human translation, never against a machine one. |
| D19 | Hosting for MVP 0. | **Local.** MVP 0 is a preview (D21) and needs no public host. Postgres+pgvector and Redis run under Docker Compose locally for parity; the application runs natively. Media backups go to an attached external drive — exactly R11's assumption — and the restore is rehearsed there. `docker-compose.yml` and the nginx config are written as the **reference deployment** and carried to a VPS at MVP 2. §15's "Docker volume" describes that reference deployment, not a commitment about any particular host. |
| D20 | Gemini account for MVP 0. | **Developer key via `.env`.** `.env` is git-ignored and remains the sole config source. The embedding model and dimension are frozen in the migration (D3), so the model is chosen deliberately now, not by default. A group-owned account with a hard cap and 50% alerting is a MVP 2 item, before the chatbot takes public traffic. |
| D21 | WordPress: preview or replacement. | **Preview at MVP 0; cut over at MVP 2.** D8 still holds — this application *is* the website — but retiring WordPress before the registry exists would remove the farm-status pages the group publishes today. MVP 0 ships on a staging surface; the redirect map becomes a MVP 2 launch-checklist item. |
| D22 | Public hosting of documents. | **Split.** The standard, BPP, OPP, landscape, prep list and the three blank checklists are published on `/documents/`. Historical application dossiers and farm visit reports stay permission-gated behind the farmer account (MVP 1), never on a public URL — they contain farmer personal data. |
| D23 | UAT sign-off for MVP 0. | **Product signs; three scenarios provisional.** Scenarios 1, 3 and 8 (does the bot quote, does the refusal convince, does the site overclaim) are judgements about the group's trust and must be signed by the PGS administrator and the consumer representative. Absent that availability they are recorded **provisional** and re-run at MVP 1 kickoff. Signing them on the product owner's word alone would make the UAT self-certification. |
| D24 | `knowledge/` as a separate app. | **Kept, for a different reason than §18.2 originally gave.** A Django app is a *migration namespace*: the corpus has an independent lifecycle (re-ingestion, `sha256` idempotency, version chains, a frozen embedding dimension) that must never entangle with certification migrations. The original reasons — swappability and tooling — do not require an app, because `import-linter` works on module paths. |
| D25 | Shape of MVP 1 — one slice or two? | **Two increments, one ship gate.** `1a` is the in-office visit flow (breadth: 16 tables, flows A/B/part-E, Sheet J PDF, the `visitPack` producer, the sync API). `1b` is the in-field offline walkabout (depth: zero new tables, service worker, IndexedDB, three-phase sync, the `visitPack` consumer). They are built separately with a frozen seam contract (`1∥`) and a single MVP 1 claim that attaches to **1b**. Rationale in `product/design/d1_mvp1_shape_exploration.html`: all irreversible risk (the template schema) sits in 1a while all unknowable risk (browser storage on real devices) sits in 1b, and a bundled slice has no cut line for the half nobody can estimate. Rejected: **A** (one slice) loses on thickness — a walking skeleton must be thin, and this one is not; **B** (two releases) makes a claim that is not yet true and needs a degraded-capture scope it does not budget. |
| D26 | Does the offline spike gate the seam contract? | **Yes.** The spike's outcome determines what `VisitSyncEnvelope` must carry: if persisted storage holds, the design stands; if eviction or quota kills long sessions, the envelope needs checkpointing or a file-export fallback (envelope v2); if offline is not viable on the target devices at all, `1b` is re-planned and only `1a` ships. Freezing a contract before that answer is known is the most expensive sequencing error available in this slice. |
| D27 | Verdict polarity and key namespacing. | **Polarity is template data** (`POSITIVE` \| `NEGATIVE` \| `INFORMATIONAL`), `value` is tri-state (`YES`/`NO`/`NA`/`NULL`), and `is_compliant` is **derived and materialised**, never authored. Keys are namespaced `crops.V04`. Rationale and the six inspected counter-examples are in §4.2.1. Required because `is_compliant(bool)` would record "yes, there are contamination risks" (V16) as *compliant*, and because `V4` means three different questions across three categories. |
| D28 | Are the assessment templates extracted from the FORM workbook, or hand-authored? | **Hand-authored**, Crops only, in `1a`. The workbook is merged-cell, two-role, 38-question material; an extractor is a form-parsing project in its own right, and only one category is needed to prove the schema. An extractor becomes worth building when a second category is required. |
| D29 | `AssessmentFee` and `EvidenceDocument` were referenced but undefined. | **Both defined** in §4.1 and §4.2. `AssessmentFee.turnover_band` is a declared field (OPP §2.3). `EvidenceDocument` carries questionnaire attachments (FORM Sheet I §2) and later historical dossiers. |
| D30 | Input register and prior certification history — in `1a` or later? | **Both in `1a`.** They are *on the forms `1a` digitises*: Sheet B.1 Q4.3 routes the farmer to the B.2 input list, and Sheet A asks about prior PGS/third-party certification and prior **denial** with reasons. Omitting them means the questionnaire cannot store what the paper form asks for. `InputSupply` and `PriorCertification` are modelled in §4.2/§4.1. |
| D31 | The pledge's land-history periods contradict OPP §V. | **Record as written; flag; do not infer a seal.** The pledge says 12 months (annuals) / 12 / 18 (other perennials); OPP §V says 18 / 12 / 12. The platform stores what the pledge actually attests and marks the declaration `land_history_conflict=True` rather than resolving it in code. Seals are MVP 2, so nothing is issued on the wrong basis in the meantime. **Awaiting a group decision.** |
| D32 | Assessment fee gate (OPP §2.3: "Fees are payable prior to the farm assessment visit"). | **Gated before the visit**, in addition to the existing paid-up gate at certification. A `FarmVisit` cannot leave `DRAFT` while the assessment fee for that visit is unpaid. |
| D33 | Where does `1a` stop? | **Before the certification decision.** `1a` records answers, verdicts, findings, corrective actions and signatures, and advances the visit to `UNDER_REVIEW`. The four outcomes, seals, certificates and the registry are MVP 2. `1a` also ships the **connected capture form** — the same templates rendered server-side — which makes the slice usable where there is signal and doubles as the R7 degrade path that `1b` falls back to. |
| D34 | How is farm GPS stored? | **Two decimal fields, not a geometry column.** `latitude` / `longitude` as `DecimalField(max_digits=9, decimal_places=6)`, nullable. `django.contrib.gis` would require GDAL/GEOS (an OSGeo4W install on Windows) and a PostGIS-enabled database — which the `pgvector/pgvector` image is not — to store a coordinate that the spec itself calls optional, never published and never spatially queried. Migrate to PostGIS only if a real spatial query needs it. |
| D35 | `Farm.current_status` in 1a? | **No — MVP 2.** It derives from `Certificate` (§11.9), which does not exist in 1a. A stub returning "no certificate" for every farm is a value someone will eventually trust. `first_certified_on` stays (a plain nullable date, no derivation). |
| D36 | What is `FarmCategory.status`? | **An application lifecycle:** `APPLIED` | `FOR_ASSESSMENT` | `ASSESSED` | `INACTIVE`. It is not the certification state — that is `ProductOutcome.status ∈ ORGANIC \| IN_CONVERSION \| NOT_ENDORSED` in MVP 2, which supersedes this for that purpose. |
| D37 | Where does "catchment" live? | **A deployment setting, not a field.** §4.1 previously carried `Member.catchment` while the prose referred to a non-existent `Farm.catchment`, and §4.8's retarget checklist correctly treated catchment as per-deployment configuration. The group's range is one string for the whole deployment; both field references are withdrawn. A member's locality is `Farm.nearest_town`. |
| D38 | `Member.status.PROBATION` has no end date. | **Add `probation_until` (nullable date).** OPP §4.6 makes probation *one calendar year*; the discipline workflow is out of scope (§17.1) so nothing else sets or clears the state, and a status that can be entered but never exited is a data trap. The warnings record itself stays out of scope. |
| D39 | Identifier and derivation conventions for `1a`. | `membership_no` is **human-facing and public** — `OUT-<year>-<seq:04d>`, never a bare autoincrement. `nearest_town` is **plain text, not an enum** (towns are group data, §4.8 — an enum would need a migration to add a town). `is_paid_up` is **defined as** `MembershipFee(paid_on not null, period_start <= today <= period_end).exists()`, with explicit periods on the row so the OPP's "payable by end of February" never becomes a hardcoded calendar boundary. |

| D40 | Front-end design language, and the Tailwind question. | **Tailwind is out.** The public-site design (`product/design/final_home.html`) was authored with Tailwind utilities via `cdn.tailwindcss.com`, which ships a CSS compiler to the browser and conflicts with `build_principles.md` §IV ("No Tailwind build step"). It is adopted as a **visual specification, not a code asset**: C1 implements it as `root.css` plus a semantic `site.css`, per the `implementing-redesigns` route. The palette is fixed as the **17 `brand-*` tokens** (forest `#323E2A` / cream `#FDFBF7` / ochre `#B87B2E`); type is **Lora** (display, kept at `font-normal`) + **Mulish** (body). Both are recorded in **`product/design/DESIGN.md`**, which is scoped to front-end design and is the only permitted source of tokens — a new colour family is a bug, not a preference. Known scale: 317 unique utility classes across 2038 tokens on that page alone. Three prior palettes explored in `product/design/visual_language/` are superseded; do not copy their tokens. |
| D41 | Corpus scope within the SAOSO PDF. | **Section B and its appendices (p23–p89).** Measured 2026-10-19: SAOSO's numbering is **part-local**, and Section A **collides with itself** — `1.` is both PREAMBLE (p5) and BASIS OF THE SAOSO STANDARDS (p8), and Section A's item 3 reproduces a regulation that restarts at `1.` inside it (p15–p21) — while Section C restarts at `1.` (p97). A globally unique `section_ref` for the whole PDF therefore does not exist, and every verdict reference in the FORM is a Section B clause (`S20.x`, `S22.x`). Sections A (principles, definitions, the regulatory minimum) and C (logos, PGS approval) are a **recorded gap** for a later slice, not silently mangled references. Consequence: D14's "the section letter is kept separately" is not implemented in MVP 0, because nothing outside Section B is stored. Adding A or C later requires a `part` field on `DocumentChunk` **and** a Section A sub-document discriminator. |
| D42 | `DocumentChunk.page` semantics. | **The number printed in the document's own footer — the reader's page — never the PDF viewer's index.** The two differ by one, because the cover is unnumbered: the TOC says `Appendix 1 → 70`, the PDF page is 71; PDF p21 prints `Page \| 20`. The TOC page map, the equivalence matrix and a human checking a citation against the paper standard all speak printed numbers, so printed is the only convention verifiable at the point of use. B3's TOC map converts TOC→PDF with an explicit `+1` and records it. A10's fixture `MANIFEST.json` records PDF indices, which is correct for extraction code and must not be confused with `page`. |
| D43 | Citation strings, and where the scheme prefix lives. | **`section_ref` stores the citation as a human reads it:** `S20.1.1` for SAOSO (the FORM's own convention — all 33 references in `6. …summary_2026.xlsx` take that shape) and `§V` / `§4.2(5)` for the OPP, even though the OPP prints `V.` and `4.2` and **never prints `§`** (0 occurrences across A10's four fixtures). `sub_refs` stay plain (`4.5(2)(c)`). The withdrawn `B.20.1.1` is not a citation: the only `B-20` in the FORM is the sheet heading `PART B - Compliance with Section B-20 : Processing & Handling`. Consequence: `MVP0_PLAN_V2.md` B6/B7's `section_ref__startswith="B.20.1"` and `{"V","VI"}` assertions were stale and are corrected in place. |

| D44 | C3 (bilingual shell) — in MVP 0 or not? | **Deferred out of MVP 0 by the product owner (2026-10-19, this session).** No human Afrikaans translator is available, and a machine translation would pass every test except the one about honesty (`#, fuzzy` count = 0 is a proxy for review, not review itself). Consequence, recorded rather than absorbed: the header's AF control stays `aria-disabled` — the same honest-control pattern as C2's former `Publishing soon` chips, and it must **not** become a link that reloads the same English page. UAT Scenario 5 ("Afrikaans quality") is **not applicable**, not failed. `build_principles.md` §IV ("Bilingual by default — strings are translated from the start rather than retrofitted") is therefore **unmet for MVP 0**; the cost lands on whoever first retargets the blueprint to an Afrikaans-speaking group, because every string added between now and then is a retrofit. `LANGUAGES`, `LOCALE_PATHS` and `User.preferred_language` stay in place so C3 remains a catalogue-and-middleware job, not a schema change. |
| D45 | The Homtini 2022 report exposed five omissions in the visit flow. What changes, and where? | **All five are in `1a`; none touches D33.** (1) Sheet I's conclusion is assessment evidence, not a decision: `SocialEquity` (Sheet I §1) and `RecordCheck` (Sheet I §2 a–i) are captured and reported, while the four outcomes stay in MVP 2. (2) Sub-verdicts become structured `sub_questions` with answers in `sub_answers`; a required child left `NULL` blocks finalise. (3) Corrective actions become a farmer-facing task list with evidence upload (`EvidenceDocument.corrective_action`), not an assessor-only note. (4) `finalise_visit` gates on unanswered verdicts/children, signatures, unset records and unreviewed prior actions, returning every gap. (5) Prior open actions are opened at the start of the next visit (`PriorActionReview`), not only in the `1b` offline pack. Also: `InputSupply.seed_status`/`approval_status` and `EvidenceDocument.input_supply` make the supplier-document and conventional-seed findings queryable. Evidence: the 2022 Homtini report left V5, V11's supplier child and V25 blank, had no applicant signature, and recorded a Major "documents outstanding" action with no follow-up path. |
| D46 | Corpus layout handling: how do we stop two-column PDFs producing unquotable text? | **Every page is passed through a column-aware transform at ingest, selected by measurement rather than by document.** `knowledge/columns.py` detects vertical whitespace bands (coverage >= 0.70, >= 6 crossing lines, >= 12% of characters on each side) and re-emits the page in reading order, or returns it byte-identical when no band qualifies. Loss-free: the non-space, non-newline character multiset is preserved on every page. The pages it transforms are pinned by a golden expectation per document in `knowledge/tests/test_columns.py` (29 transformed of 33 detected); a page that is column-laid-out but must not be transformed lives in `PAGE_LAYOUT_EXCLUSIONS` with its measured reason — SAOSO PDF 2 (its page-number column is the TOC's content), SAOSO PDF 82-83 (Appendix 4 Table 1: 4-column single-line rows are already coherent), OPP PDF 11 (3-column labelling table). Consequence: `layout` is **not** a field on `StandardDocument` and not a `CORPUS_DOCUMENTS` flag, so a retarget to another standard needs no migration; a new edition that mis-detects fails a test rather than silently degrading citations. Alternative rejected: a per-document `layout: two-column` flag, which would have missed the OPP's three table pages. A page whose *maximal* band starts inside an overflowing left-column line can carry a **measured band override** in `PAGE_LAYOUT_BANDS` (BPP PDF 4: `(40, 42)`, because its left list item reaches column 40 and the default `(38, 42)` split the raw-manure 60-day rule). Recorded 2026-10-20; evidence and build outcome in `product/backlog/In Progress/CORPUS_COLUMN_EXTRACTION_PRD.md`. |
| D47 | Where should the model-side citation refusals be fixed? | **Tighten the prompt/citation contract (option A), never the audit.** Two live turns on 2026-10-20 were refused after the corpus fix: one invented `sub_ref: "FERTILIZERS AND SOIL CONDITIONERS"` from a heading, the other joined two passages with `...`. Both are uncheckable citations, so the audit was correct. `SYSTEM_PROMPT` now requires a character-for-character quote (no paraphrase, no ellipsis), and allows `sub_ref` only when the passage lists that exact sub-clause under "Numbered sub-clauses available"; `build_prompt()` makes that line explicit for every passage — `none — omit sub_ref for this passage` when the chunk has no stored sub-refs. `PROMPT_VERSION` is `d47-4` (the `d47-1` contract, the retrieval invalidation in D48, and two further prompt iterations after live tests: one-passage quotes and no stitching), so the cache cannot serve an answer produced under the old contract. Consequence: retry the live manure turn; if two prompt revisions still produce invented sub-refs, a narrow repair (drop an unknown `sub_ref`, never a quote) is the fallback. Rejected: fuzzy/elided quote matching, which would accept a passage the reader cannot find on paper. Verified live 2026-10-20: the manure question returned a grounded answer with three verbatim Appendix 2 citations and `sub_ref=None`; it cited no BPP passage, which is a model-selection choice, not a corpus failure. A later `can i use horse manure?` turn was refused for a stitched BPP quote; `d47-3`/`d47-4` made the one-numbered-passage rule explicit, and the D46 band override made the raw-manure 60-day sentence contiguous. The re-run was accepted with six citations. Recorded 2026-10-20. |
| D48 | Embedding model, dimension and the vector arm. | **`gemini-embedding-001` at 768 dimensions, with the current corpus embedded and the vector arm live.** Ratified by the product owner 2026-10-20. `text-embedding-004` is retired; the replacement does not move the frozen dimension (`DocumentChunk.embedding` is `vector(768)`) because the request asks for `output_dimensionality=768` explicitly. The four documents were force-re-ingested without `--no-embed` (idempotency on sha256 makes a plain re-run a no-op): 340/340 chunks carry a vector, `search()` reports `lexical_only=False`, and the developer key (D20) is used until a group-owned account lands in MVP 2. Enabling the arm exposed a retrieval interaction that would otherwise have been a regression: `search_terms` embedded the rare word *and* the OR query, and the rare-word vector pushed SAOSO Appendix 2 out of the top 8, so the manure question refused again. The rare-term arm is now **lexical only**; the vector arm runs once, on the OR query, which restores Appendix 2 at #2 and BPP at #4 and halves query embeddings per question from two to one. `PROMPT_VERSION` is `d47-4` after the later prompt iterations, so no cached reply outlives the change. Verified live 2026-10-20: grounded answer, two verbatim Appendix 2 citations, `sub_ref=None`; the run cited no BPP passage, which is model selection, not a corpus failure. |
| D49 | How does retrieval find a clause when the question's subject is a word the corpus does not contain? | **Embed the visitor's question, and give the semantic arm seats the rare-term arm cannot take.** Measured 2026-10-21 on *"can I use cardboard from my neighbours?"*: `search_terms` embedded the OR-joined tokens (`use OR cardboard OR neighbours`) and searched the rarest *known* word (`neighbours` → wild harvest, child labour); the unknown subject `cardboard` was discarded and SAOSO 4.4.4 never reached the model. Embedding the sentence puts 4.4.4 at rank 6; the OR form does not retrieve it at all. Fix: `search(vector_query=)` embeds the question while the lexical arm keeps the rare-term query; `SEMANTIC_SEATS = 3` reserves the vector arm's share (with five lexical chunks first it contributed **nothing**); a term with document frequency 0 marks an unknown subject, so the lexical proxy is capped at two chunks and the semantic arm takes the rest — the two-chunk hedge is also the no-key offline path. Chat `RETRIEVAL_LIMIT` 5 → 8. Rejected: a classifier or alias table to map `cardboard → inputs`; it would not fix any measured failure and a wrong label hides the right passage (reopen trigger in `CHAT_ANSWER_COVERAGE_PRD.md` G5). |
| D50 | D17 allows only a *definitive* answer. Is a rule that governs an unnamed item an answer? | **Yes — name the gap, state the rule, cite it. D17's refusal wording is unchanged.** Cardboard is not named in SAOSO, but 4.4.4 requires material applied to land to comply with Appendix 2; refusing that is a false refusal, and the corpus contains the rule. `SYSTEM_PROMPT` rule 4 now answers with the governing rule, says plainly that the document does not name the item, and forbids two things: inventing the missing detail and reading permission into silence (*"Silence is not permission"*). `insufficient_context` keeps its meaning — no supplied passage bears on the question — and the citation audit is unchanged. `PROMPT_VERSION` is `d49-1`, so no cached reply outlives the contract. Consequence: the assistant is allowed to be useful about unnamed inputs; it is not allowed to infer that something is permitted. Verified live 2026-10-21: cardboard returned *"The SAOSO Standard does not specifically name cardboard…"* with the biodegradable by-products row and its contaminants condition. UAT Scenario 10 asks the human whether that reads as an answer or as permission. |
| D51 | Appendix 2's conditions cannot be quoted because `-layout` interleaves the table's columns. Reconstruct rows? | **Yes, as reviewed data — one chunk per printed row — and the extraction mode is the finding, not a pairing algorithm.** `pdftotext -table` aligns the appendix's rows (measured on SAOSO pdf 77–79: wood ↔ "Only if not chemically treated", by-products ↔ contaminants condition); `-layout` cannot, because the rows overflow the gutter and `de_column` keeps a spanning line whole by design. `knowledge/tables.py` holds 30 reviewed rows (printed pp. 76–78) and the measured `TABLE_BANDS`; ingest replaces the section's auto-chunks with one chunk per row, so a substance and its condition are one quotable passage. Assumptions recorded in the module and the PRD: the pairing is the product owner's review, a row with no condition is not permission, each cell is verbatim but the join is not on the paper (the single exception to "a chunk is a slice of the section"), cross-page continuations are merged by hand, sub-headings are not rows, and only Appendix 2 is covered. `ingest_standard(force=True)` / `--force` exists because the sha256 guard otherwise makes a corpus-built-here change unreachable; deletion happens inside the transaction after embedding. Verified live: borax now grounded (was an audit refusal), straw no longer carries wood's condition. Appendices 3/4/6/7 remain on the interleaved path (`CHAT_ANSWER_COVERAGE_PRD.md` G4). |
| D52 | Two correct answers were refused for a quote the page cannot produce. Fix the chunker, or the prompt? | **Neither: the extracted page was the defect, so the page is repaired at ingest. The audit stays strict.** Measured 2026-10-22 on the two refusals `CHAT_ANSWER_COVERAGE_PRD.md` recorded as G1/G2: `pdftotext -layout` breaks a line inside a hyphenated word — `… 15% dry matter per non-` / `ruminant …` (S5.5.1) and `post-` / `harvest` (S4.1.1) — so a whitespace-normalised quote had to contain `non- ruminant`, a spelling no reader writes; the model elided the word with `...` and the audit refused a substantively correct answer. `knowledge/reflow.py` rejoins a line that ends in letter-hyphen when the next non-blank line starts lowercase, **keeping the printed hyphen**; it runs after `de_column` (line adjacency is reading adjacency only then) and before the parser, in both `ingest_standard` and `scripts/extract_fixtures.py`. Measured on the four governed documents: **20 joins**, every one a genuine compound, and **no page ends inside such a word**, which is why a per-page pass is complete — `knowledge/tests/test_reflow.py` pins both counts. Second defect, same class: the printed footer `P a g e | 47` was not furniture, so it was emitted *inside* a clause that continues onto the next page — **65 of 368 chunks** carried one; `PAGE_FOOTER` is now in `FURNITURE`, and the page number is still read from the page before any line is classified. Rejected: accepting a quote modulo hyphenation in `_normalise_text`, which would admit text a reader cannot find on paper (D47's rule, and `testing_hazards.md` §1.22). Consequence: both live questions are grounded with **no prompt change** — the region was the corpus, not the model — `reflow_pages` is reported by the ingest and the fixture manifest (`pipeline … + reflow v2`), and the answer cache self-invalidates through `_corpus_fingerprint`, so `PROMPT_VERSION` stays `d49-1`. Recorded and **not** fixed: a *spanning* line in the BPP general principles is still emitted as consecutive fragments (`(agro-` / `and thereafter …`), which no line-join can repair (`CHAT_ANSWER_COVERAGE_PRD.md` G7). |
| D53 | Four sessions in a row were spent repairing PDF extraction. Should the corpus be derived from a reviewed artefact instead? | **Yes — the reviewed artefact is the text of record; extraction becomes a per-edition build step.** The extraction heuristics (D46 columns, D51 tables, D52 reflow, G7 spans) were on the *runtime* path, so every layout irregularity became a wrong or refused chatbot answer. `knowledge/corpus/<doc>.md` is Markdown with machine annotations: a `<!-- page: N printed: M -->` marker before every block (PDF page for provenance, printed page for D42), `##` headings for `heading_path`, `<!-- ref: … -->` for the citation, and text that is otherwise verbatim, blank lines included. `scripts/build_corpus.py` drafts it from the PDF; a human reviews the draft against the paper; `ingest_standard --from-corpus` reads the reviewed file. **Freezing happens at the section level, not the chunk level** — chunking, `sub_ref` offsets and embeddings stay derived, because they are retrieval tuning. Reviewed corrections are *data* (`knowledge.corpus.CORPUS_EDITS`), not comments, so a test proves each was necessary (its `original` is in the PDF-derived text) and applied (its `replacement` is in the file). Guards: the character multiset equals the PDF path's sections minus the declared edits; every `(section_ref, anchor, page, heading_path)` is identical between the two paths; every block is traceable to its page; the sentences the chat tests depend on are contiguous. The BPP spike (13 pages) needed **5** corrections and produced **3** permanent generator improvements — bands narrowed to the columns no line writes into (BPP's uncuttable lines 66 → 13, losslessly, SAOSO/OPP unchanged), a per-page `-raw` fallback (measured: `-raw` is a character-for-character permutation of `-layout` on all 139 pages; the fallback fires only where, after repairing its glued runs with `-layout`'s word boundaries, the word multiset is identical — 11 of 13 BPP pages), and `page_stamp` shared with the parser so a printed page is read from the de-columned rendering. G7 is closed by it (the agro-chemical prohibition answers live, grounded). `--from-pdf` stays available and tested; the equivalence test makes the migration reversible. OPP, SAOSO and landscape are not yet converted; the open follow-ups (corpus digest idempotency, moving `CORPUS_DOCUMENTS` out of the Django-coupled module) are in `CORPUS_CANONICAL_FORMAT_PRD.md` §7. Recorded 2026-10-22. |
| D54 | Is a citation-audit refusal a distinct escalation reason? | **Yes — `CITATION_AUDIT`, a fourth value.** D17's refusal string is unchanged and the user-visible behaviour is identical, so this is a change to the *record*, not to the product. It exists because the three reasons conflated three different findings: "the model cited nothing" (`NO_CITATIONS`), "the corpus cannot ground it" (`INSUFFICIENT_CONTEXT`) and "the model cited something the audit could not verify" — the last recorded as `NO_CITATIONS`, which reads as a thin corpus and sent a live diagnosis down the wrong path on 2026-10-20 (`testing_hazards.md` §1.31). The audit is right to refuse; the reason must say which failure it was. |
| D59 | How long are public chat transcripts kept? | **Indefinitely, until the group sets a schedule** (product owner, 2026-10-22). The record is already kept — every turn stores the question, the answer or refusal, the model, the token counts and the `retrieved_chunks` the model was given — and that record is what makes a refusal a corpus-gap queue rather than an anecdote. Retaining it is also a POPIA obligation to *decide*, because this is a public form: `ChatSession` stores a sha256 of the client IP, a user agent, and whatever the visitor typed, which can contain personal data about a third party ("my neighbour's farm"). No purge job is built while the decision is "keep"; a purge must be explicit when the group adopts a schedule, because deleting a `ChatSession` cascades its messages while an `EscalatedQuery` deliberately survives via `SET_NULL`. Revisit trigger: the group's POPIA retention schedule (it already has one for assessment records), or the MVP 2 registry work, whichever comes first. Companion telemetry (attribution fields, `chat_review`, a staff flag) is plan P2.5–P2.8 in `CORPUS_CANONICAL_FORMAT_PLAN.md`. |
| D55 | Should `ingest_standard` read the reviewed artefact by default, or keep the PDF path as the default? | **The artefact, and fail closed.** D53 made `--from-corpus` opt-in, so the PDF path stayed the default and the VPS — which never set the flag — kept extracting at ingest time. For the four governed documents a missing `knowledge/corpus/<doc>.md` is now an **error naming `scripts/build_corpus.py`**, not a fallback: a silent fallback is how the runtime keeps a reader nobody noticed. `--from-pdf` stays available and tested as the diagnostic and the equivalence oracle, and is the only way to ingest a document whose artefact does not exist yet. Recorded 2026-10-22. |
| D56 | How does a deployment know its corpus matches the committed artefacts? | **Store the digest, report drift, never auto-refresh.** `StandardDocument.corpus_digest` records the sha256 of the artefact each document was built from (additive migration; the PDF's `sha256` remains the source identity). `corpus_check` is read-only and prints what differs — it belongs in `deploy.sh`, because a deploy that silently re-ingests destroys every `ChatMessage.retrieved_chunks` link. `corpus_refresh --apply` (which is `ingest_standard --force --from-corpus`) stays a deliberate operator command. Recorded 2026-10-22. |
| D57 | The goldens are calibrated to Xpdf 4.00 and the deploy target has poppler. Pin the binary, or stop depending on it? | **Stop depending on it in the gate; pin it only to build.** The first real deployment gate (poppler 24.02) failed 15 tests and 61 errors, all extraction: `-table` does not exist in poppler, and the column and wrap detectors disagree with Xpdf's. So the gate reads **committed page fixtures** (`knowledge/tests/fixtures/pages/<doc>.<mode>.txt`, recorded with mode, page count, sha256 and the extractor banner in `MANIFEST.json`), and `verify.sh` runs pytest with `PDFTOTEXT_BIN` pointed at a path that cannot exist — the gate proves on every run that no test needs a reader. The extractor becomes a **build-time** tool: `PDFTOTEXT_BIN` pins it, and the artefact header and fixture manifest record which build produced the text. `-table` remains Xpdf-4-only, which is now a property of the artefact build, not of the deployment. Recorded 2026-10-22 (`testing_hazards.md` §2.9). |
| D58 | How is a 101-page SAOSO artefact reviewed, and do the appendices convert inside this slice? | **Mechanically first, human second, and yes.** Acceptance is mechanical where it can be: every block traceable to its marked page, identity (`section_ref`, `anchor`, `page`, `heading_path`) identical between the two paths, character multiset equal minus declared edits. Human review reads the **flagged delta** — the blocks the generator could not place — not the whole document; that is the queue the BPP review proved works. The kill criterion from D53 stands: more than ~10% of blocks needing edits means the artefact is not cheaper than the extractor. Appendices 1–7 convert inside this slice, absorbing G4: the reviewed `knowledge/tables.py` rows keep owning the substance↔condition pairing, and the artefact owns the page text. Recorded 2026-10-22. |
| D60 | Is the committee's confirmation of no-claims part of MVP 0's definition of done, or a project-level gate? | **Project-level.** The first half — *no certification claim anywhere on the public surface* — is machine-enforced by `test_claim_discipline.py` and stands unchanged. The second half — *confirmed by the committee* — cannot be discharged until the platform is presented to the committee, which is a project milestone after MVP 0, not a build gate. It is tracked in `todo.md` §Project and linked from `MVP0_PLAN_V2.md` §4.1 item 5. Keeping it as an MVP 0 blocker would stall MVP 0 indefinitely on a meeting; deleting it would silently weaken the claim the feature exists to protect. The grep is the standing guarantee until the committee signs. |
| D61 | May the citation audit accept a `section_ref` that carries the document label (`Appendix 2 — SAOSO Standard … v2.1`)? | **Yes — the label is decoration, the locator is the address.** `build_prompt` used to print them joined by an em dash, rule 2 said to cite *the exact locator printed for that passage*, and the model dutifully cited the whole header: the audit answered "not present in the retrieved set" and a correct, properly quoted answer became "I cannot find a definitive answer" on the live site (2026-10-22, `G9`). Two changes, in this order: the prompt now prints `LOCATOR:` on its own line with `Document:` beneath, and `_normalise_ref` discards everything from a dash on. This is **format tolerance, not a relaxed audit** — D47 still forbids trimming citations, the key must still resolve to exactly one stored locator, the quote must still be a substring of that chunk, and `sub_ref` must still exist; a key produced by two different locators still refuses. `PROMPT_VERSION` is `d49-3`. |
| D62 | What shape should `/ask/` be — a chat window, or something else? | **A question-first board with answer pages, not a chat window** (product owner, 2026-10-23). The composer is the primary element on the page and `Questions we have answered` sits below it; asking adds to that library once an administrator has read it, and a question the documents cannot answer stays visible as a **Waiting** card rather than disappearing. Each answer has a permalink (`C`) carrying the clause in full, what the answer does *not* cover, and a copyable citation. The visitor's four governing documents are pre-ticked as the source scope, with an optional **wider reading** tier (KNF, JADAM, JMF, INF, Japanese Natural Farming) that is marked *not assessed against* wherever it contributes. The worksheet shape (`D`) is reused in the apply/prepare flows, where the group's own Farm Visit Preparation List already is the outline. Five shapes were prototyped and compared (`product/design/d61_ask_interface_options.html`); the chat window survives as the *composer*, not as the archive. The one-hour answer cache is not a content store: a board is a table with a publish flag, and publishing visitor text is a POPIA decision that has not been taken. |
| D63 | How does a follow-up reach retrieval, and does it need a model call? | **Stage 1 first: a context arm, the parent answer's carried citations, and one prompt line. The rewrite is deferred until a measurement justifies a model call** (product owner, 2026-10-23). A follow-up is detected deterministically (`looks_like_follow_up`, which fails closed to today's behaviour), its previous question is fused in as a lexically-searched arm capped at two passages, and the clauses the parent answer was *allowed* to cite are carried into this turn's set — the last is load-bearing, because the standard does not contain the word that was asked about, so the parent's words are in no clause either. `PROMPT_VERSION` is `d49-4`: a conversation is not evidence. Measured on the live corpus 2026-10-23 over four parent/follow-up pairs: three lost the parent's cited clause when the fragment was searched alone, stage 1 restored it in all three, one answer changed from grounded-but-off-topic to correct, one improved, and one (straw) was unaffected because its defect is in the prompt, not the retriever. The instruction-only alternative (&ldquo;the latest message is a follow-up&rdquo;) was rejected: it makes the model likelier to cite a passage the all-or-nothing audit never saw. |

---

## 19. Delivery Sequence

Ordered by **risk retired per unit of effort**, not by ease of building. Two facts drive the order: the standards corpus is shared work (the assessment templates are *derived from* SAOSO clauses, see FORM `V1a (S20.1.1)`), and the public site is the feedback surface the group needs before it will trust the platform with certification records.

Slice 1 is **two increments with one ship gate** (D25). The split is between breadth and depth, not between online and offline: the sync protocol spans both tiers, and the pre-visit questionnaire is deliberately online-only (§8).

| # | Slice | What it proves | Depends on |
|---|-------|----------------|-----------|
| **0** | **Standards foundation + shop window.** Ingest SAOSO 2.1 / OPP / BPP into the clause model; public marketing pages; the grounded chatbot on them; `/documents/` hosting. | That the chatbot can be trusted to say "I don't know", **and** that the clause model the templates depend on actually works. | — |
| **0∥** | **Offline spike — 2 days, throwaway code.** Capture a visit on a real iPhone in a real low-signal location. | That offline-first is feasible at all on the assessor's actual device. **Gates the 1∥ seam contract** (D26), not merely parallel to it. | — |
| **1∥** | **Seam contract.** `visitPack` schema and `VisitSyncEnvelope` v1, written and contract-tested against both sides. | That the pack format suits both a server-side renderer and an offline consumer *before* either is built against a guess. | 0 (template schema), 0∥ |
| **1a** | **In-office visit flow.** Application → membership and pledge → pre-visit questionnaire → scheduling with committee validation → assessment capture (connected) → Sheet J PDF. Ships the `visitPack` **producer** and the sync API. | That the assessment domain model holds up against FORM: that 91 verdicts, four categories and the grey/white two-role split can be represented without distorting the paper form. | Domain and flows: **0** only. Pack producer + sync API: **1∥**. |
| **1b** | **In-field offline walkabout.** Service worker + IndexedDB client, three-phase split-sync, photo and signature capture, quota handling. Ships the `visitPack` **consumer**. | That offline-first works on the assessor's real device in a real dead zone. **This is what makes MVP 1's claim true.** | 1a (pack producer, sync API), 0∥ |
| **2** | **Decision, certificate, registry, QR verification**, seeded from the existing records in §12.1. | That a consumer can verify a claim end to end. | 1b |
| **3** | **Reporting.** Visit log, corrective-action register, census, standard gap analysis. | That administrative overhead actually falls. | 2 |
| **post** | Voice notes (§17.2). | — | 1b |

**MVP 0 is deliberately *not* the registry.** Publishing certification status before the machinery that substantiates it exists is the one move that could damage the group's credibility — precisely the problem the PGS was founded to solve. The registry therefore lands in MVP 2, once there is real certificate data behind it, seeded from §12.1. MVP 0 ships the marketing surface and the chatbot, which make no certification claim.

**The spike is not optional, and it is not merely parallel.** It costs two days and retires the project's only existential risk. D26 additionally makes its result a **precondition for freezing the seam contract**: if storage does not survive on the target devices, the envelope needs checkpointing or a file-export fallback, and that is a contract change — the one artefact most expensive to revise after both increments are built against it. Running it during MVP 0 is fine as scheduling; freezing the contract before it finishes is not.

**The claim attaches to 1b, not 1a.** 1a delivers real value in a connected setting, but it does not make the group's field work paperless — on its own it means paper in the field and digital re-entry afterwards, which is *more* work than today. MVP 1 is not declared done until an assessor completes a visit with no signal, which is why the split is two increments and one gate rather than two releases.

---

## Appendix A — Source Traceability

| Spec area | Primary source |
|-----------|---------------|
| Two-role form, `V#` verdicts, grey/white cells | FORM Sheet A preamble; Sheets B.1, C, D, E |
| Categories and in-development sections | FORM Sheet A; Sheets F, G, H |
| Finding severities (verbatim) | FORM Sheet I |
| Outcome enum, product outcomes (incl. exclusions), 12-month term | FORM Sheet I §3; Sheet J; live site `/endorsed-farms/` |
| Participant composition and roles | OPP §3.3, §4.1 |
| Membership procedure, pledge, verbal pledge for non-literate members | OPP §I |
| Fee schedule and paid-up eligibility gate | OPP §II |
| 5-day notice, 3-day questionnaire, 5-day conclusion window | OPP §4.1, §4.2(5) |
| Annual assessment, random/unannounced visits | OPP §4.3, §4.4 |
| Corrective action escalation to termination | OPP §4.5, §4.6, §4.7 |
| Seals and in-conversion periods | OPP §V |
| Visit stages and committee log fields | PREP |
| Documentation/records checklist | FORM Sheet I §2 |
| Social equity and justice | FORM Sheet I §1 |
| Census reporting purpose | FORM Sheet A |
| Six basic elements of PGS | LANDSCAPE |
| Standard structure, section refs, appendices | SAOSO table of contents |
| Aggregation of produce, supplying-farm declarations, labelling categories | OPP §VI.1–6.5; FORM Sheet A |
| Committee positions and the 2026 roster | OPP §3.1, §VII |
| Farmer pledge, consumer pledge, distinctive marks, land-history attestation | OPP §I, and the pledge forms annexed to the OPP |
| The three seals and the undefined "pasture-raised" criteria | OPP §V |
| Extensibility: standards, seals and categories as data | (new — review D12) |
| Voice notes as a first-class capture type | (new — review D6) |
| Filesystem media, private/public roots, mandatory backup | (new — review D2, R11) |
| English/Afrikaans bilingual requirement | (new — review D7, local catchment) |
