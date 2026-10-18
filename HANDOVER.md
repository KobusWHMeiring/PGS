# Handover — MVP 1a Implementation

**For:** the next agent, starting implementation.
**From:** planning session, 2026-10-18.
**Repo state:** `main`, 7 commits, **no application code**. Spec, two PRDs, two plans, two UATs and
four design artifacts are complete.

> The previous handover (a review of the target-state spec) is superseded and its findings are applied.
> Retrieve it if you need the provenance: `git show 719df9a:HANDOVER.md`.

---

## 0. The one thing to know first

**There is no code in this repository.** No `manage.py`, no `core/`, no `knowledge/`. Every plan here
is a plan.

The `MVP1A_PLAN.md` §0.2 heading used to imply MVP 0 already existed. It has been corrected: **MVP 0
sub-plan A (Tasks A1–A10) is a hard prerequisite for MVP 1a.** It delivers the scaffold, the
environment-driven settings, and — critically — the **custom `User` model, which must be the first
migration in the database.** You cannot swap it later without pain.

Nothing else from MVP 0 (the standards corpus, the public site, the chatbot) is a prerequisite for 1a.

---

## 1. Read these first, in this order

| # | Artifact | Why | Time |
|---|---|---|---|
| 1 | `product/backlog/Refinement/MVP0_PLAN_V2.md` §0–§2 + Tasks A1–A10 | **Your actual first work.** The foundation 1a stands on. | 25 min |
| 2 | `product/backlog/ready/MVP1A_PLAN.md` | The 1a task list. Sub-plan A is where you start after the foundation. | 30 min |
| 3 | `product/backlog/ready/MVP1A_PRD.md` | Scope, the fence, success criteria, risks. | 15 min |
| 4 | `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` **§18.3 first**, then §4.1–§4.2 and §4.2.1 | 39 decisions. **Read §18.3 before questioning anything** — most "obvious improvements" were considered and rejected. | 40 min |
| 5 | `product/docs/context/build_principles.md` | Non-negotiable. Thin views, service ownership, 30 KB cap, integer cents, no logic in templates. | 10 min |
| 6 | `tests/uat/mvp1a_in_office_visit_uat.md` | What humans will judge. Read the `Judgement:` clauses. | 10 min |
| 7 | `pgs_docs/` | The authoritative source documents. **Spot-check domain claims against these, never against a plan.** | as needed |

Do **not** read `prd.md` as the spec (it is superseded provenance), and do **not** execute
`product/backlog/Done/MVP0_PLAN.md` (superseded — its SAOSO parser matched nothing in the real PDF).

---

## 2. Your first two pieces of work

### First — MVP 0 foundation, Tasks A1 → A5

`MVP0_PLAN_V2.md`. In order: scaffold + Compose (Postgres+pgvector, Redis), settings, **custom `User`
with plural `UserRole`**, `Category`/`Seal` + `seed_deployment`, `/health/`. Then A6–A10 (Celery,
import-linter, CI, backup/restore, fixture extraction) before or alongside.

Two things in A1 that will otherwise cost you an afternoon:

- **`weasyprint` must not be installed yet.** It needs GTK system libraries on Windows. It is deferred
  to 1a sub-plan F, whose *first action* is to install and verify it.
- **`.gitattributes` with `* text=auto eol=lf`** — the repo is on Windows and line endings churn in
  every diff otherwise.

### Second — MVP 1a, Task A1: Farms and members

Five models, no views, `core/tests/test_membership.py`. The five tests are written out in the plan.
The field decisions are frozen as **D34–D39** and must not be re-opened:

| # | Decision | Trap if ignored |
|---|---|---|
| D34 | GPS = `DecimalField(9,6)` ×2 — **no `PointField`** | `django.contrib.gis` needs GDAL/GEOS (OSGeo4W on Windows), and the `pgvector` image has no PostGIS |
| D35 | **No `Farm.current_status`** in 1a | It derives from `Certificate`, which is MVP 2. A stub saying "no certificate" is a value someone will trust |
| D36 | `FarmCategory.status ∈ APPLIED \| FOR_ASSESSMENT \| ASSESSED \| INACTIVE` | Previously undefined in the spec |
| D37 | **No `catchment` field** on `Member` or `Farm` | It is a deployment setting; the spec contradicted itself three ways |
| D38 | `Member.probation_until` (nullable date) | OPP §4.6 makes probation one year; without a date the status can be entered and never exited |
| D39 | `membership_no` = `OUT-<year>-<seq:04d>`; `nearest_town` plain text; `is_paid_up` uses the **row's** period | A bare autoincrement leaks a count and is guessable across years |

---

## 3. Decided — do not re-litigate

`PGS_PLATFORM_SPEC.md` §18.3 holds D1–D39. The ones most likely to tempt a re-open:

- **D25 — MVP 1 is two increments, one ship gate.** 1a = in-office breadth; 1b = in-field depth; the
  MVP 1 *claim* attaches to 1b. Rationale and rejected alternatives:
  `product/design/d1_mvp1_shape_exploration.html`.
- **D26 — the 0∥ spike gates the `1∥` seam contract.** Sub-plan G of the 1a plan must not start first.
- **D11 / D22 — the pasture-raised seal is inactive and is *never rendered*.** Issuance is hard-blocked
  when `is_active=False`, with no override. `test_claim_discipline.py` will fail the build on
  `pasture raised`, `GMO free`, `biodynamic`, `chemical-free`, `spray-free`.
- **D27 — verdict polarity is template data.** `is_compliant` is derived, never authored. Details and
  the six inspected counter-examples are in §4.2.1.
- **D31 — the pledge's land-history periods conflict with OPP §V and are NOT resolved in code.** Record
  what was attested, set `land_history_conflict`, infer nothing. Awaiting a group decision.
- **D33 — 1a stops at `UNDER_REVIEW`.** No outcomes, no seals, no certificates.

---

## 4. Do not build these

- **Any MVP 2 model**: `CertificationDecision`, `ProductOutcome`, `Certificate`, `CertificateProduct`,
  `PublicVerificationEvent`, anything in `_aggregation.py`.
- **The registry, QR or verification pages** — they publish certification status, and 1a produces none.
- **Voice-note UI or transcription.** `VoiceNote` *is* migrated now (schema only) per §17.2.
- **Templates for Animal Husbandry, Seed Production or Agro-processing** — Crops only (D28) until the
  schema is proven.
- **Anything in the MVP 0 site/corpus/chatbot** unless you have been asked to reorder to it (see §10).

---

## 5. Gates

| Gate | What it means |
|---|---|
| **MVP 0 A1–A5 migrated** | Before any 1a model. The custom `User` must be first. |
| **0∥ spike complete** | Before `1∥` freezes `visitPack` / `VisitSyncEnvelope`. **Sub-plan G (1a) does not start until then.** |
| **Task B3 needs a second reader** | Authoring the Crops template is 38 questions and 37 verdicts by hand, and a template that is 80% complete looks like a complete one. Have someone read the JSON against printed FORM Sheet B.1. |
| **1a UAT** | Eight human-judged scenarios. Scenarios 3 and 6 require the *administrator's own machine*. |

---

## 6. Traps that will bite

1. **The polarity trap (R1a-2).** Mis-assigning polarity does not crash — it produces plausible, wrong
   data. `V16` "Are there any risks of contamination of the water source?" answered *Yes* means
   **non-compliant**; with the naive `is_compliant = (value == YES)` it stores as compliant and looks
   fine until someone queries it in MVP 3. `V3` is `INFORMATIONAL`, `V23` and Animal `V14` are
   `NEGATIVE`. The tests assert these explicitly so a future tidy-up of the JSON breaks the build.
2. **Section formats are not what they look like.** If you touch ingestion (MVP 0 sub-plan B), read
   spec §4.5's six verified realities first: SAOSO prints `20.1.1.` (**never** `B-20.1.1`), part letters
   are running page headers present on only 22 of 98 pages, the TOC matches the clause pattern, and
   appendix headings exist only in the TOC.
3. **`GeneratedField(SearchVector(...))`** may not cooperate with the Postgres version in Compose. Fall
   back to a trigger and say so in the module docstring.
4. **`OVERDUE` is derived from `due_on`, never stored.** Otherwise a nightly job becomes load-bearing
   for correctness, and it will eventually not run.
5. **Never `except: pass`.** Sentry on every exception path, explicit `timeout=` on every external call.
6. **Run the thing before you believe it.** The single most expensive error in this project's history was
   a parser written against an assumed format that matched zero lines of the real document — and whose
   tests passed, because the fixtures were hand-written. Fixtures must be verbatim extracts of the
   shipped PDFs.

---

## 7. Commands

```bash
python product/backlog.py            # dry-run: drift + suggested moves
python product/backlog.py --write    # regenerate the index (never hand-edit backlog.md)
python product/backlog.py --apply    # move files to match Status: + regenerate

pytest -q                            # after the foundation exists
lint-imports                         # knowledge must never import core

docker compose up -d                 # Postgres+pgvector and Redis only; the app runs natively
```

Use the **local** skills `.agents/skills/pgs-reading-the-backlog`, `pgs-maintaining-the-backlog`,
`pgs-writing-explorations` — not their generically-named counterparts, which assume other layouts.

---

## 8. Open — not yours to resolve

| Item | Blocked on | Affects |
|---|---|---|
| **D31 — which land-history periods govern** (pledge 12/12/18 vs OPP §V 18/12/12) | **The group** | MVP 2 seal issuance. This is a certification-integrity question, not a software one. |
| Seal cardinality; which seal applies to "Organic - pending corrective action" | MVP 2 modelling (OPP §V says In-Conversion) | MVP 2 |
| `standard_ref` coverage — clause mappings for the ~91 non-agro-processing verdicts | Authoring effort | MVP 3 gap analysis |
| Hosting cutover to the VPS | MVP 2 | Docker on a shared box vs native gunicorn |
| UAT sign-off seats (administrator, committee reviewer, consumer member) | **The human** | 1a acceptance |
| POPIA consent for already-published farmer/consumer names | MVP 2 seeding | MVP 2 registry |
| Existing certificate data — 2023/24 outcomes missing from the live site | **The group** | MVP 2 seeding |

---

## 9. Design artifacts (`product/design/`)

| File | Serves |
|---|---|
| `d1_mvp1_shape_exploration.html` | The D25/D26 decision, with diagrams and the architecture-principles table |
| `mvp0_scope_and_open_questions.html` | The eleven MVP 0 decisions, with fix cards for F1–F5 |
| `decisions_review.html`, `o4_app_structure.html` | The earlier override and O4 reviews |

To produce another one, use `.agents/skills/pgs-writing-explorations/SKILL.md` — self-contained, house
palette, decision recorded + exportable, diagrams with labelled edges.

---

## 10. What happened in the planning session

Compressed, so you can trust the state without reading the whole history:

1. **Full review of the target-state spec against the source PDFs.** Found that the MVP 0 SAOSO parser
   matched **nothing** in the real document (`B-20.1.1` was invented), that the OPP parser could not
   reach §V or §VI, that "notifiable exception" was defined backwards, and that the pasture-raised seal
   was specified as both active and not-shipped. Applied as **F1–F5** and recorded as **D14–D24**.
2. **A parser was run over the shipped PDFs** before any plan was rewritten. It produced six further
   realities now recorded in spec §4.5 — the most useful being that part letters come from running page
   headers, and that appendix headings do not exist in the body at all.
3. **MVP 0 re-planned** as `MVP0_PRD.md` + `MVP0_PLAN_V2.md`; v1 retired to `Done/` as superseded.
4. **MVP 1's shape decided** (D25/D26) via a full exploration artifact: two increments, one ship gate,
   the spike gating the seam contract.
5. **MVP 1a specified**: PRD, 32-task plan, UAT, plus **D27–D33** (polarity model, template authoring,
   the two dangling models, input register + prior certification, the pledge conflict, the fee gate,
   the fence) and **D34–D39** (geo fields, `current_status`, `FarmCategory.status`, catchment,
   `probation_until`, identifier conventions).

### One sequencing question left for the human

§19 orders MVP 0 fully before slice 1, on the grounds that "the assessment templates are derived from
SAOSO clauses". **D28 hand-authors the Crops template with `standard_ref: null`, which severs that
dependency.** So the ordering is now open:

- **MVP 0 sub-plan A is unconditional** — nothing works without the scaffold and the custom `User`.
- After that, the choice is MVP 0's **B/C/D** (corpus, public site, chatbot) or **1a**.

§19's own justification for MVP 0 first also included the public site being "the feedback surface the
group needs before it will trust the platform with certification records" — which is an argument that
still stands, and is a product decision rather than a technical one. **Ask before assuming.** The
session's last stated direction was to start 1a.
