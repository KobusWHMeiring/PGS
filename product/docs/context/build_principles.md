# Build Principles: Outeniqua PGS Digital Platform

**Status:** Active — Non-Negotiable
**Last Updated:** 2026-10-18
**Authority:** Reconciled from Urban Harvest Platform (Harvester) `product/docs/context/build_principles.md` and Homtini Blueberry `product/context/build_principles.md`.
**Companion spec:** `product/backlog/Refinement/PGS_PLATFORM_SPEC.md`

## 0. Provenance & Reconciliation

This document is derived from two prior projects. The derivation is explicit so it can be audited:

- **Harvester** is the baseline. Its conventions, stack (Django 5.2, PostgreSQL, Redis, Celery, WeasyPrint, Gemini, Sentry, `python-dotenv`) and production-hardening rules are adopted wholesale.
- **Homtini §1.1–1.3** are grafted in: Thin Views, Service Layer Ownership, the 30KB file cap, No Logic in Templates, Data Flow Contracts, and strict type hints with frozen dataclasses. `prd.md` already assumed these rules; they did not exist in the Harvester baseline.
- **Homtini §4** ("Asynchronous Pi Decoupling") is **not adopted**. This platform has no farm-appliance counterpart; its offline story is a browser PWA, covered by `PGS_PLATFORM_SPEC.md §9–10`.
- **Harvester's single-file `core/models.py`** is superseded by a `core/models/` package, because the 30KB cap and this domain's schema size cannot both hold. Harvester's own `models.py` already exceeds the cap. This is a deliberate, documented deviation — the only structural one.

Financial rules from Homtini §2.1 (integer cents, `_cents` suffix, no floats for money) **are** adopted: this system tracks membership, assessment, catering, licensing and transport fees.

---

## I. Architectural Layout

- **Monolithic Core, plus one library.** Bounded contexts are *modules*, not apps. Membership, assessment, certification, aggregation, the registry, chat, and the public site all belong to **one** `core/` app: they share the `FarmVisit` aggregate and the `Farm`/`User` tables, so separating them would create circular imports and cross-app FK sprawl for no benefit. The one exception is the **standards corpus**, which shares nothing with any of it — no farm, no member, no user — and lives in a sibling `knowledge/` app.
- **The `knowledge` dependency is one-directional.** `core` may import `knowledge`; `knowledge` must **never** import `core`. Enforced by an `import-linter` rule in CI, not by convention. `knowledge` contains only `StandardDocument`, `DocumentChunk`, and the retrieval and ingestion services — no views, no sessions, no user references. Chat, chat history and escalations are `core` concerns, because they are user-owned.
- **Code encodes the PGS process; data encodes the standard and the group.** The process — visits, committees, verdicts, findings, corrective actions, decisions, In-Conversion, aggregation, discipline — is what IFOAM means by a PGS and is common to every group: it belongs in code. The standard assessed against, the seals issued, the document corpus, the assessment categories and the questions are **data**, seeded per deployment. Concretely: `Seal`, `Category` and `StandardSet` are tables, not enums; `AssessmentTemplate.schema` is imported from a JSON file by `load_template`; documents are ingested by `ingest_standard`. **Acceptance test: retargeting to another standard or PGS group must not require a migration.** See `PGS_PLATFORM_SPEC.md §4.8`.
- **App boundaries are not URL boundaries.** Django apps are Python module namespaces. Public site, farmer portal, assessor PWA, verification pages and the JSON API are separate URL prefixes routed from the root URLconf, regardless of how many apps exist.
- **Domain-Based Packages:**
  - `core/models/` — `_core.py`, `_assessment.py`, `_certification.py`, `_aggregation.py`, `_chat.py`, with `__init__.py` re-exports so `from core.models import Farm` still works.
  - `knowledge/` — `models.py`, `services.py`, `tasks.py`, `tests.py`. The standards corpus and retrieval only.
  - `core/views/_<domain>.py`
  - `core/forms/_<domain>.py`
  - `core/services/_<domain>.py`
  - `core/tasks/_<domain>.py`
  - `core/tests/test_<domain>.py`
- **Where To Put New Code.** Follow the domain map. A farm-visit-verification service goes in `core/services/_assessment.py`, its view in `core/views/_committee.py`, its form in `core/forms/_committee.py`, its tests in `core/tests/test_assessment.py`. Each module carries a docstring listing its conventions.
- **Encapsulated Query Logic.** Common filters (`.active()`, `.paid_up()`, `.overdue()`, `.public()`, `.current()`) live in custom QuerySets/Managers. Never repeat complex `.filter()` chains across views.
- **No Logic in Templates.** Templates display only. Formatting and conditionals live in template tags (`core/templatetags/pgs_extras.py`), model properties, or service-prepared context.
- **Relational Integrity & Public Identifiers.** Standard integer PKs internally. Every public surface (verification pages, farm profiles, chat sessions, sync idempotency keys) uses `UUIDField`. **Sequential IDs must never leak to the public.**
- **Immutable History.** Farm assessments are evidentiary. `Assessment.template_schema` is a frozen snapshot; template edits never mutate history. No destructive deletes on `CertificationDecision`, `Certificate`, `EvidencePhoto`, `SyncReceipt`, or `AssessmentVerdict` — use status enumerations.
- **Migration Safety.** New fields are nullable or have sensible defaults. No destructive operations without a verified backup. `AlterField` nullable → non-nullable requires a default. `RunPython` provides `reverse_code`.

## II. Service Layer & Data Flow Contracts

- **Service Layer Ownership.** All business logic lives in `core/services/_<domain>.py`. Views route and serialise; models define schema and trivial properties; services own operations.
- **Thin Views (< 20 Lines).** A view may parse a request, call one domain service, and return a response or template. Never business calculations, fee maths, or direct multi-table mutation.
- **Data Flow Contract.** Every public service method documents `In:`, `Out:`, `Side Effects:`, `Fails:` — and `Idempotency:` where the operation is reachable from the offline sync queue, where idempotency is a correctness requirement, not a nicety. See `PGS_PLATFORM_SPEC.md §6` for the canonical examples.
- **Strict Type Hinting.** All service signatures use strict hints (`int`, `str`, `UUID`, `Optional[...]`, `list[...]`). Compound return values are `@dataclass(frozen=True)`.
- **File Size Cap (30 KB).** No source file exceeds 30 KB. When a service approaches the limit, vertically slice it by domain responsibility (`_sync.py`, `_photos.py`, `_finalise.py`).
- **Schema Before Logic.** No view or UI code is written before the `core/models/` change is approved and migrated.

## III. Financial Integrity

- **Integer Money Rule.** Monetary values are stored and calculated as integer cents (`Int`). Field names end in `_cents` (`membership_fee_cents`, `assessment_fee_cents`, `catering_fee_cents`, `licence_fee_cents`, `transport_fee_cents`). Never `FloatField` for money.
- **Formatting at the boundary only.** `format_zar(cents: int) -> str` in `core/templatetags/pgs_extras.py`.
- **Declared, not computed.** Assessment fees follow the OPP §2.3 turnover sliding scale, but turnover is *self-declared by the farmer and subject to peer review*. Store the declared band; never infer it.

## IV. Frontend & UX

- **Zero Build Pipeline.** No npm, Vite or Webpack in CI/CD or Docker. No Tailwind build step. Static assets ship via `python manage.py collectstatic`. All JS dependencies are vendored in `core/static/pwa/vendor/`.
- **Native ES Modules.** The assessor PWA uses `<script type="module">` and browser-native APIs. No SPA framework — no React, Vue or Svelte.
- **HTMX Permitted** for the public site, farmer portal and registry filters (single vendored file, no build step). The offline assessor PWA does **not** use HTMX.
- **Touch-First.** ≥44×44 px targets. Inputs carry correct mobile keyboard hints (`type="tel"`, `inputmode="numeric"`, `autocomplete`).
- **Legible Outdoors.** High contrast and large type. The assessor reads this in direct sunlight; that is the design constraint, not a preference.
- **Context Preservation.** Filters, date ranges and dashboard toggles persist via URL parameters and `localStorage`.
- **Bilingual by default.** English and Afrikaans are both first-class. `User.preferred_language` sets the default, strings are translated from the start rather than retrofitted, and the PWA translation catalogues ship inside the cached app shell so the assessor's language works offline.
- **Voice is a first-class input.** Any text field can be dictated via `MediaRecorder`; recordings upload through the same resumable queue as photos and are transcribed server-side into a human-reviewable draft (§II, Human-in-the-Loop). Recording is gated on an explicit consent acknowledgement stored per recording: a voice is personal data, and bystanders recorded at a visit have not consented by attending.

## V. Testing & Quality

- **Golden Flow Coverage.** The critical path is protected by integration and E2E tests:
  `Prepare Visit Pack → Offline Capture → Sync Text → Sync Media → Finalise → Decide → Certificate → Verify QR`.
- **Playwright E2E** for the offline PWA, the sync protocol, and the public verification page — including a simulated offline session and a duplicated-sync replay.
- **The sync protocol is proven by test, not by inspection.** A test must assert that replaying an identical `client_uuid` payload creates zero additional rows.
- **Mobile Responsiveness.** Validate UI changes against the mobile suite using iPhone metrics.
- **Institutional Memory.** Major architectural decisions go in `product/docs/context/` or an ADR under `docs/adr/`. Run `python summarise.py` to regenerate the context buffet.
- **Pre-Flight Checklist.** Before implementing any feature, run the checklist in `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` (or the feature PRD's pre-flight section).

## VI. Performance & Data Integrity

- **Aggressive N+1 Prevention.** Every relational query declares `select_related` (single FKs) or `prefetch_related` (reverse/M2M). Audit new views for query efficiency.
- **Atomic Transactions.** Every multi-table write is wrapped in `transaction.atomic()`. The offline text-sync write path is the highest-risk example; partial writes there are catastrophic.
- **Media is filesystem, not object storage.** No S3. Evidence originals live under a **private media root** and are never served directly — Django authorises and hands off to nginx via `X-Accel-Redirect` against an `internal` location. Public derivatives live under a separate public root. Because the media volume becomes the single copy of evidentiary photos and audio, **a scheduled off-box backup of both the database and media volume is a launch requirement**, and a restore is rehearsed rather than assumed.
- **Environment-Specific Config.** Secrets never hardcoded. `.env` via `python-dotenv` is the sole source of instance configuration.

## VII. Production Hardening

1. **Health Check Endpoint.** `/health/` verifies DB (`SELECT 1`), Redis (`PING`), Celery broker, and Celery worker liveness. Returns JSON; any failed dependency returns HTTP 503.
2. **Explicit Timeouts.** Every `requests` call declares `timeout=`. SDK clients (Gemini, SMTP, S3) configure timeouts at initialisation. A hung external call blocks a Celery worker indefinitely.
3. **Celery Retry Policies.** Every `@shared_task` declares `autoretry_for`, `max_retries`, `default_retry_delay`. Non-idempotent tasks opt out explicitly with `autoretry_for=()`.
4. **Structured Logging with Request IDs.** `X-Request-ID` is generated per request, propagated into Celery tasks, and included on all log lines. Use `django-structlog`.
5. **Fail Loudly.** No silent exception blocks. Never `except: pass`. Log with context and re-raise, or report to Sentry.

## VIII. Developer Velocity & Observability

- **Test Factories.** New tests use `factory_boy` factories in `core/tests/factories.py`.
- **Cache Expensive Reads.** Public registry listings, farm profiles and chatbot answer lookups use the Django cache with appropriate TTLs. Use a separate Redis database number for cache versus the Celery broker.
- **Log at the I/O Boundary.** Service methods performing external I/O or multi-table transactions use the `@log_boundary` decorator (entry, exit, duration, outcomes).
- **UAT Scope.** UAT checklists contain only checks a human must judge in a running app instance (legibility, layout, wording, a real phone, a real offline walkabout). If a test, linter or grep can prove it, it belongs in the automated suite. Every surviving UAT item carries a `Judgement:` clause. See the `writing-uat-tests` skill.

## IX. Single-Tenant Blueprint

The application is a **blueprint**, cloned and deployed as a separate instance per PGS group rather than offered as multi-tenant SaaS. Keep code readable and modular so a group can customise it. No runtime tenancy logic, no tenant-scoped queries, no shared database.
