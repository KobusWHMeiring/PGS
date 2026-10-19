# MVP 0 Implementation Plan (v2) — Standards Foundation & Public Shop Window

**Status:** Ready — the §9 group-A gate closed as D27 (verdict polarity is template data) and D14–D15 (citation depth, `sub_ref`, `anchor`). Sub-plan A is in build.
**Owner:** Kobus Meiring (Product)
**Last Updated:** 2026-10-18
**MVP:** 0 (spec §19)
**Supersedes:** `MVP0_PLAN.md` (v1). v1 was written against assumptions the shipped PDFs
contradict — its SAOSO parser matched nothing in the real file. See `MVP0_PRD.md` appendix.
**Reference:** `PGS_PLATFORM_SPEC.md` · `MVP0_PRD.md` · `../tests/uat/mvp0_standards_and_public_site_uat.md`
· `../../docs/context/build_principles.md`

---

## 0. How to execute this plan

- **TDD order is not optional.** Each task lists a failing test first. A task is done when its
  test passes, not when the file exists.
- **One commit per task.** Commit messages name the task id (`feat(b2): ...`).
- **30 KB file cap.** If a module approaches it, slice vertically.
- **Do not re-litigate §1.** Those decisions were made with evidence and are recorded in the
  spec's decision log.
- **Fixtures come from the PDFs, never from imagination.** This is the specific failure that
  invalidated v1 (§B2).

### 0.1 Frozen decisions

| # | Decision | Why it matters here |
|---|---|---|
| D14 | SAOSO cited as `S20.1.1` | Parser reads `20.1.1.` and the part letter separately |
| D15 | Depth ≤ 3; `sub_ref` + `anchor`; chunks stay section-level | `DocumentChunk.sub_refs` offset map |
| D16 | Corpus = SAOSO, OPP, BPP, LANDSCAPE | Workbook is a download, never corpus |
| D17 | Wide corpus; refusal names the group | Not the SAOSO-only string |
| D18 | Afrikaans = mechanism + shell | No machine translation, ever |
| D19 | Local hosting; Compose for pgvector + redis only | No `weasyprint` in MVP 0 |
| D20 | Dev Gemini key via `.env`; embedding dim frozen now | Choose the model deliberately |
| D21 | Preview, not WordPress replacement | No farm status published |
| D22 | Blank forms public, dossiers gated | `/documents/` publishes 7 items |
| D24 | `knowledge/` separate app | Migration namespace |

Fixes already applied in the spec: **F1** SAOSO parser, **F2** OPP parser + `sub_ref`,
**F3** pasture-raised never rendered, **F4** notifiable exemption, **F5** repo initialised.

---

## 1. Scope and dependency graph

```
A (foundation) ──┬─► B (corpus) ──► D (chatbot)
                 └─► C (site) ────►
```

A gates everything. B and C can run in parallel once A is green. D needs B (retrieval) and C
(the surface it sits in).

**Out of scope, and stays out:** registry, certificates, QR, farmer accounts, assessor PWA,
offline sync, Sheet J PDF, reporting, aggregation workflow, voice notes, translated content.

---

## 2. Files created across MVP 0

```
manage.py
pgs/settings.py  pgs/urls.py  pgs/celery.py  pgs/__init__.py
docker-compose.yml            # postgres+pgvector, redis — NOT the app (D19)
requirements.txt  .env.example  .gitattributes

core/models/      __init__.py _core.py _certification.py _chat.py
core/views/       __init__.py _public.py _documents.py _chatbot.py _health.py
core/forms/       __init__.py
core/services/    __init__.py _seed.py _health.py _chatbot.py
core/tasks/       __init__.py _maintenance.py
core/tests/       __init__.py test_models.py test_settings.py test_seed_deployment.py
                  test_health.py test_tasks.py test_public.py test_documents.py
                  test_chatbot_grounding.py test_chatbot_guardrails.py
                  test_claim_discipline.py test_retrieval_scope.py  factories.py
core/templatetags/pgs_extras.py
core/templates/   base.html public/ documents/ chatbot/
core/static/      css/site.css  js/chat.js  vendor/htmx.min.js
core/services/_seed.py

knowledge/models.py  apps.py  services.py  embedding.py  chunking.py
knowledge/sections/  __init__.py registry.py saoso.py opp.py heading.py toc.py
knowledge/management/commands/ingest_standard.py
knowledge/tests/     __init__.py test_models.py test_section_parsers.py
                     test_toc_map.py test_chunking.py test_ingest.py
                     test_retrieval.py  fixtures/

scripts/backup.sh  scripts/restore.sh  scripts/extract_fixtures.py
docs/RUNBOOK.md
.github/workflows/ci.yml
.importlinter
```

---

# Sub-plan A — Foundation

### Task A1: Scaffold, dependency manifest, Compose

**Files:** `requirements.txt`, `docker-compose.yml`, `.env.example`, `.gitattributes`, `.gitignore` (exists)

The repository is already initialised (F5). Do **not** re-run `git init`.

```yaml
# docker-compose.yml — infrastructure only. The app runs natively in a venv (D19).
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: pgs
      POSTGRES_USER: pgs
      POSTGRES_PASSWORD: pgs
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
volumes:
  pgdata:
```

**Steps**

1. `docker compose up -d` — verify `psql` connects and `SELECT * FROM pg_available_extensions WHERE name='vector';` returns a row.
2. Create the venv and install **only** these:

```bash
pip install "Django==5.2.*" psycopg2-binary dj-database-url python-dotenv \
  celery redis django-structlog sentry-sdk pgvector \
  google-genai \
  pytest pytest-django factory-boy faker import-linter
pip freeze > requirements.txt
```

   **Deliberately absent:** `weasyprint` (MVP 1 — it drags GTK into a Windows dev box for zero
   MVP 0 value), `openpyxl` and `django-import-export` (MVP 3), `pytest-playwright` (added in C1
   when there is a page to drive).
3. `django-admin startproject pgs .` then `startapp core` and `startapp knowledge`; create the
   domain subpackages listed in §2.
4. Write `.gitattributes` with `* text=auto eol=lf` — Windows CRLF churn will otherwise pollute
   every diff. (Already present in the repo as of the initial commit.)

**Applied deviations, found by running it:**

- **`google-genai`, not `google-generativeai`.** The latter is end-of-life and says so on import
  (*"All support for the `google.generativeai` package has ended"*), while dragging in
  `google-api-python-client`, `grpcio` and `protobuf<6`. Sub-plan D builds the embedding and chat
  clients on this, so the swap is cheap now and expensive later. Adopting it removes 11 packages.
- **Host port 5433, not 5432.** A native Windows PostgreSQL service already owns `0.0.0.0:5432`,
  and Docker binds the same port alongside it instead of failing — so a native connection
  silently reached the *native* server and failed with "password authentication failed for user
  pgs". CI has no competing service, so A8 is unaffected.

**Acceptance:** `docker compose ps` healthy; `python -c "import django, pgvector, celery"` clean.
Verified 2026-10-19: both services healthy, pgvector 0.8.7 available in Postgres 16.15, Redis
PONG, `manage.py check` clean.

---

### Task A2: Environment-driven settings

**Files:** `pgs/settings.py`, `core/tests/test_settings.py`

**Test first** — assert config comes from env and nothing is hardcoded:

```python
def test_required_settings_come_from_env(settings):
    assert settings.DATABASES["default"]["NAME"] == "pgs"
    assert settings.PRIVATE_MEDIA_ROOT != settings.MEDIA_ROOT

def test_no_secret_is_literal_in_source():
    src = Path("pgs/settings.py").read_text()
    assert "django-insecure" not in src
```

**Then** implement: `python-dotenv` load, `dj-database-url`, structlog, Sentry (DSN optional so
dev runs without it), cache on Redis DB 2 (Celery broker on 1 — separate DBs per
`build_principles.md` §VIII), `MEDIA_ROOT` / `PRIVATE_MEDIA_ROOT`, `ALLOWED_HOSTS` from env,
`pgvector` in `INSTALLED_APPS`, `core` + `knowledge`.

**Acceptance:** `manage.py check` clean with an empty `.env` except `DJANGO_SECRET_KEY`.

---

### Task A3: Custom `User` and plural roles

**Files:** `core/models/_core.py`, `core/models/__init__.py`, `core/tests/test_models.py`

**Test first:**

```python
def test_user_holds_zero_or_more_roles(user_factory):
    u = user_factory()
    assert not u.has_role("ASSESSOR")
    u.roles.create(role="ASSESSOR")
    u.roles.create(role="FARMER")
    assert u.has_role("ASSESSOR", "FARMER")     # any-of semantics
    assert not u.has_role("ADMIN")

def test_capability_never_implies_role_storage(user_factory):
    u = user_factory()
    u.roles.create(role="ADMIN")
    assert u.has_role("ASSESSOR") is False      # ADMIN implies it via has_role(), not rows
```

**Then** implement `User(AbstractUser)` with `phone`, `email_verified_at`, `popia_consent_at`,
`preferred_language`, `graduated_from_public_at`; `UserRole(user, role)`; and `has_role(*roles)`
that treats `ADMIN` as implying `ASSESSOR` (§3 of the spec). **This must be the first migration**
— a custom user model cannot be swapped later without pain.

**Acceptance:** migration applies to an empty DB; tests pass.

---

### Task A4: `Category` and `Seal` as data, plus `seed_deployment`

**Files:** `core/models/_core.py` (`Category`), `core/models/_certification.py` (`Seal`),
`core/services/_seed.py`, `core/management/commands/seed_deployment.py`,
`core/tests/test_seed_deployment.py`

**Test first:**

```python
def test_only_two_seals_are_active():
    call_command("seed_deployment")
    active = set(Seal.objects.filter(is_active=True).values_list("code", flat=True))
    assert active == {"PGS_ORGANIC_CERTIFIED", "PGS_ORGANIC_IN_CONVERSION"}
    assert Seal.objects.get(code="PGS_PASTURE_RAISED").is_active is False
    assert Seal.objects.get(code="PGS_PASTURE_RAISED").criteria_defined is False

def test_seeding_is_idempotent():
    call_command("seed_deployment"); call_command("seed_deployment")
    assert Category.objects.filter(code="CROPS").count() == 1

def test_inactive_seal_cannot_be_issued(certificate_factory):
    with pytest.raises(InactiveSealError):
        certificate_factory(seal=Seal.objects.get(code="PGS_PASTURE_RAISED"))
```

`Category`: `CROPS`, `ANIMAL_HUSBANDRY`, `SEED_PRODUCTION`, `AGRO_PROCESSING` active;
`AQUACULTURE`, `WINE`, `INPUT_SUPPLIER` seeded **inactive** (FORM Sheets F/G/H are
"in development"). `Seal`: `code, label, standard_ref, is_active, criteria_defined, display_note`.

**Acceptance:** all three tests pass; seed is re-runnable.

---

### Task A5: `/health/`

**Files:** `core/services/_health.py`, `core/views/_health.py`, `core/urls.py`, `pgs/urls.py`,
`core/tests/test_health.py`

**Test first:** 200 with all four `ok`; 503 when Redis is down (monkeypatch the client to raise).

Response shape:

```json
{"status": "ok", "checks": {"db": "ok", "redis": "ok",
                            "celery_broker": "ok", "celery_worker": "ok"}}
```

**Acceptance:** both tests pass; view is under 20 lines and calls one service.

---

### Task A6: Celery with retry policies

**Files:** `pgs/celery.py`, `pgs/__init__.py`, `core/tasks/_maintenance.py`,
`core/tests/test_tasks.py`

**Test first:** assert every registered task declares `autoretry_for`, `max_retries` and
`default_retry_delay` — a meta-test that protects the rule rather than one task:

```python
def test_every_task_declares_a_retry_policy():
    for name, task in current_app.tasks.items():
        if name.startswith("celery."):
            continue
        assert task.autoretry_for is not None or task.max_retries == 0, name
```

**Acceptance:** a `heartbeat` task exists and the meta-test passes.

---

### Task A7: The `knowledge` ↛ `core` contract

**Files:** `.importlinter`, `core/tests/test_architecture.py`

```toml
[importlinter]
root_package = pgs

[[importlinter.contracts]]
name = knowledge must never import core
type = forbidden
source_modules = knowledge
forbidden_modules = core
```

**Test first:** write a test that shells `lint-imports` and asserts exit code 0, so the rule is
enforced by `pytest` as well as CI (one of them will be skipped by a human).

**Acceptance:** `lint-imports` passes; introduce `from core.models import Farm` into
`knowledge/services.py` temporarily and confirm both the linter and the test fail.

---

### Task A8: CI

**Files:** `.github/workflows/ci.yml`

Postgres service using `pgvector/pgvector:pg16`, Redis service, then:
`python manage.py check` → `lint-imports` → `pytest -q`. No npm, no bundler, no build step —
`build_principles.md` §IV forbids it and this workflow must not quietly add one.

**Acceptance:** green on a clean checkout.

---

### Task A9: Backup, restore, and a rehearsed rehearsal

**Files:** `scripts/backup.sh`, `scripts/restore.sh`, `docs/RUNBOOK.md`

`backup.sh`: `pg_dump` **and** `rsync` of both media roots to `${BACKUP_DIR}` (an attached
external drive — D19, and exactly R11's assumption). It **must fail loudly**: non-zero exit,
a timestamped log line, and a `set -euo pipefail` header. A cron that dies quietly is worse than
no cron.

`restore.sh <backup-dir>`: restore into a scratch database and scratch media root, then verify
row counts match and a known file's `sha256` matches.

**Acceptance (this one is human, not automated):** perform a restore on a clean machine or a
fresh database, and record the date and result in `docs/RUNBOOK.md`. UAT DoD requires this.

---

### Task A10: Fixture extraction — the guard against v1's failure

**Files:** `scripts/extract_fixtures.py`, `knowledge/tests/fixtures/*.txt`

A script that runs `pdftotext -layout` over the four shipped PDFs and writes **verbatim
excerpts** into `knowledge/tests/fixtures/`, plus a `MANIFEST.json` recording each source file's
`sha256` and the byte range taken:

| Fixture | Taken from |
|---|---|
| `saoso_part_b.txt` | pp. 61–63 — `SECTION B` header, `20.1.`/`20.1.1.`/`20.1.2.` |
| `saoso_toc.txt` | pp. 2–3 — the table of contents (proves TOC exclusion) |
| `saoso_appendices.txt` | pp. 71–73 — appendix content |
| `opp_4_1.txt` | `4.1 Preparation` + items `1.`–`3.` |
| `opp_4_2.txt` | `4.2 Assessment` + items `1)`–`12)` |
| `opp_4_5.txt` | `4.5 Non-compliance` incl. missing item 3 and `(c)`'s half-numbered list |
| `opp_seals.txt` | `V. Seals` and `VI. Aggregation` |

**Corrected 2026-10-19 after running the extractor — the page numbers above were wrong.** This
plan originally said `saoso_part_b` pp. 60–62, `saoso_toc` p. 1, and appendices pp. 70–73. Measured
against the shipped PDFs: page 60 is the tail of §9.6 (*aquaculture*), so the range would have
grafted unrelated text onto a processing-and-handling fixture; p1 is the cover, not the TOC; and
`APPENDIX 1` begins on p71. Taking the original numbers at their word would have reproduced v1's
exact failure — a fixture that does not match the document it claims to describe — so the extractor
now declares an `anchor` that must be present on each fixture's start page and **fails** if it is
not. The anchor is the evidence; a page number copied from a plan is a claim.

Also worth knowing before B2: the body prints `APPENDIX 1` in **UPPERCASE** at ~62 columns of
indent, so B2's title-case `APPX` regex matches nothing in the body (SPEC §4.5 reality 4 is right)
but **false-positives on p63**, where `Appendix 4.` starts a mid-sentence line. And the PDFs fail
to map some glyphs to Unicode (`0xFF` in the source), so fixtures contain U+FFFD — the OPP's
pasture-raised line carries an en-dash in SPEC §4.3 that no extractor can produce. Both are recorded
in `MANIFEST.json`; neither should be hand-edited.

**Acceptance:** the script is deterministic (re-running produces byte-identical fixtures), and
`MANIFEST.json` sha256 values match the PDFs in `pgs_docs/`. B2's tests read only from these files.

---

# Sub-plan B — Standards corpus and retrieval

### Task B1: Corpus models

**Files:** `knowledge/models.py`, `knowledge/tests/test_models.py`

```python
StandardSet       code, label, description, is_default
StandardDocument  standard_set, kind, issuing_body, title, version, effective_from,
                  superseded_by, source_file, sha256, chunk_count, section_scheme
DocumentChunk     document, section_ref, sub_refs (JSONB), anchor, heading_path, page,
                  text, token_count, embedding (VectorField), search_vector (GeneratedField)
```

**Tests first:**
- A chunk with an empty `section_ref` cannot be saved (it is not a citation — spec §4.5).
- `sub_refs` entries are `{"ref", "start", "end"}` with `0 <= start < end <= len(text)`.
- Re-saving a document with an identical `sha256` is a no-op (checked in B6).
- The generated `search_vector` updates when `text` changes.

**Note:** if `GeneratedField` with `SearchVector("text", config="english")` proves awkward
against the Postgres version in Compose, fall back to a trigger, and record the reason in the
module docstring rather than leaving the reader guessing.

**Acceptance:** migration applies; `VectorExtension()` is created before the vector column.

---

### Task B2: Section parsers, written against the fixtures

**Files:** `knowledge/sections/__init__.py` (`ParsedSection`, `SubRef`), `registry.py`,
`saoso.py`, `opp.py`, `heading.py`, `knowledge/tests/test_section_parsers.py`

The v1 regexes appear below because their exact shape is the point — they were wrong in a way
that silently produced zero sections.

```python
# knowledge/sections/saoso.py — verified against the shipped PDF (D14, F1)
CLAUSE = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)\.\s+(\S.*)$")   # "20.1.1. text" at column 0
APPX   = re.compile(r"^Appendix\s+\d+[a-z]?(?:\.\s+Table\s+\d+)?\.?\s*$")
HDR    = re.compile(r"^\s{8,}SECTION ([A-C])\s*$", re.M)        # running page header
```

```python
# knowledge/sections/opp.py — verified (D15, F2)
ROMAN = re.compile(r"^\s{0,7}([IVX]+)\.\s+(\S.*)$")             # "V.", "VI."  — indented!
SUB   = re.compile(r"^\s{0,7}(\d+\.\d+)\s+(\S.*)$")             # "4.5 Non-compliance…"
ITEM  = re.compile(r"^\s{2,}(\d+)[.)]\s+(\S.*)$")               # "5)" §4.2 / "1." §4.1
LET   = re.compile(r"^\s{8,}([a-z])\.\s+(\S.*)$")               # "c." §4.5(2)
```

**Tests first — these are the assertions v1 lacked:**

```python
def test_saoso_yields_sections_with_refs(saoso_fixture):
    secs = SaosoParser().parse(saoso_fixture, part="B")
    assert len(secs) > 0                                   # v1 returned []
    assert all(s.section_ref for s in secs)
    assert "S20.1.1" in {s.section_ref for s in secs}

def test_toc_is_excluded(saoso_toc_fixture):
    assert SaosoParser().parse(saoso_toc_fixture, part=None) == []

def test_opp_roman_sections_are_reachable(opp_seals_fixture):
    refs = {s.section_ref for s in OppParser().parse(opp_seals_fixture)}
    assert {"V", "VI"} <= refs                            # v1 missed both

def test_depth_three_resolves(opp_4_5_fixture):
    subs = {r.ref for s in OppParser().parse(opp_4_5_fixture) for r in s.sub_refs}
    assert "4.5(2)(c)" in subs

def test_depth_four_is_never_synthesised(opp_4_5_fixture):
    for s in OppParser().parse(opp_4_5_fixture):
        assert all(r.ref.count("(") <= 2 for r in s.sub_refs)

def test_missing_item_number_is_reported_not_invented(opp_4_5_fixture):
    # §4.5 runs 1, 2, 4, 5 — item 3 does not exist
    refs = {r.ref for s in OppParser().parse(opp_4_5_fixture) for r in s.sub_refs}
    assert "4.5(3)" not in refs
```

**Then** implement. `opp.py` carries state: current Roman → current `x.y` → current item →
current letter, emitting a `SubRef(ref, start, end)` for each enumerated level. `heading.py`
handles BPP/LANDSCAPE: `section_ref = None`, `anchor` from the heading slug, and `page` only.

**Acceptance:** all six tests pass; `registry.get("saoso")` returns the parser from
`StandardDocument.section_scheme` alone, with no code change.

---

### Task B3: TOC page map and appendix segmentation

**Files:** `knowledge/sections/toc.py`, `knowledge/tests/test_toc_map.py`

The SAOSO body carries **no appendix headings** — they exist only in the TOC and the equivalence
matrix. So appendix boundaries are derived from the TOC's page numbers.

**Test first:** parse `saoso_toc.txt`, assert the map contains
`{"Appendix 1": 70, "Appendix 4. Table 2": 83, "Appendix 6a": 85}` (from the TOC as shipped),
and that `segment_appendix(page=71)` returns `"Appendix 1"`.

**Acceptance:** appendix content is attributed to its appendix, not to the preceding clause.

---

### Task B4: Chunker with `sub_refs` offsets

**Files:** `knowledge/chunking.py`, `knowledge/tests/test_chunking.py`

**Decision carried from D15:** chunks stay **section-level**. Sub-item boundaries do not split
chunks; they produce offsets.

**Tests first:**
- A section shorter than ~800 tokens is one chunk carrying all its `sub_refs`.
- A long section splits on paragraph boundaries; every `sub_ref` lands in exactly one chunk, and
  its `start`/`end` are relative to that chunk's `text`.
- `sub_refs` never overlap and always satisfy `0 <= start < end <= len(text)`.
- Token estimate uses 4 chars/token (no tokeniser in the request path).

**Acceptance:** the OPP produces a chunk count in the low tens, not the low hundreds — if it
produces hundreds, sub-items are being split and retrieval will degrade.

---

### Task B5: Gemini embeddings with an explicit timeout

**Files:** `knowledge/embedding.py`, `knowledge/tests/test_embedding.py`

Tests use a fake client: assert `timeout=` is passed on every call, the batch size is bounded,
and a transient failure retries then raises rather than returning zeros. **Record the model name
and dimension in the migration** — D3/D20: changing it later means re-embedding the whole corpus.

**Acceptance:** tests pass with no network access.

---

### Task B6: `ingest_standard`

**Files:** `knowledge/management/commands/ingest_standard.py`, `knowledge/tests/test_ingest.py`

**Tests first:**

```python
def test_ingest_produces_citable_chunks(real_saoso_pdf):
    call_command("ingest_standard", "--doc", "saoso", "--file", real_saoso_pdf)
    chunks = DocumentChunk.objects.all()
    assert chunks.count() > 0
    assert not chunks.filter(section_ref="").exists()        # v1's silent failure
    assert chunks.filter(section_ref__startswith="B.20.1").exists()

def test_ingest_is_idempotent_on_sha256(real_saoso_pdf):
    call_command("ingest_standard", "--doc", "saoso", "--file", real_saoso_pdf)
    n = DocumentChunk.objects.count()
    call_command("ingest_standard", "--doc", "saoso", "--file", real_saoso_pdf)
    assert DocumentChunk.objects.count() == n

def test_duplicate_refs_are_reported(real_saoso_pdf):
    call_command("ingest_standard", "--doc", "saoso", "--file", real_saoso_pdf)
    assert duplicate_ref_count() <= KNOWN_SAOSO_DUPLICATES
```

The third test exists because ~50 duplicate refs remain in SAOSO (clause numbers repeating within
a part, or appendix content absorbed). It is a **ratchet**, not a pass: the number may only go
down. Investigate them during B3/B4; do not silence the check.

**Then** implement, page-aware: extract per page, skip TOC pages, carry the part letter forward,
segment appendices from the TOC map, then chunk and embed.

**Acceptance:** all four documents ingest; the ratchet holds; re-ingest adds nothing.

---

### Task B7: Hybrid retrieval, fused and scoped

**Files:** `knowledge/services.py`, `knowledge/tests/test_retrieval.py`

- FTS: `websearch_to_tsquery` over `search_vector`, ranked `ts_rank_cd`.
- Vector: `pgvector` cosine over `embedding`.
- Fuse with RRF k=60. Optional rerank over fused top-20 → top-5.
- **Scope to `StandardSet` before ranking** — the corpus boundary is a filter the model cannot
  escape, not a rule it must remember.

**Tests first:** a query returns SAOSO clause `B.20.1.1` for a traceability question (recall
floor); no result ever comes from outside the session's set; an empty corpus returns `[]` rather
than raising.

**Acceptance:** tests pass; retrieval works with the Gemini key absent when only FTS is exercised.

---

# Sub-plan C — Public site and documents

### Task C1: Public pages

**Files:** `core/views/_public.py`, `core/urls.py`, `core/templates/public/*.html`,
`core/static/css/site.css`, `core/tests/test_public.py`

Routes: `/` · `/organics/` · `/how-it-works/` · `/members/` · `/become-a-member/` · `/contact/`.
Content from the spec's §12 marketing list: the **six basic elements** (LANDSCAPE — shared vision,
trust, horizontality, transparency, participatory, learning process), the Basic Production
Principles summary, and the **fee schedule from OPP §II** (R100 membership, R500 PGS-SA,
assessment bands R1,500–R8,000).

**Tests first:** every route 200 with its expected heading; `/members/` renders the disclaimer
that membership is not certification (an OPP requirement, not a nicety).

**Then** Playwright (`pytest-playwright` is added here, not in A1): one test per route, plus a
390 px viewport check.

**Acceptance:** 200s; disclaimer present; no template contains business logic.

---

### Task C2: `/documents/`

**Files:** `core/views/_documents.py`, `core/models/_core.py` (`PublicDocument`),
`core/tests/test_documents.py`

Publishes exactly seven items (D22): SAOSO v2.1, OPP, Basic Production Principles, Certification
Landscape, prep list, and the three participant checklists. The assessment workbook is included
only after the committee confirms (D22). **Dossiers are never public.**

Copy the files into `media/public/documents/` at deploy; serve with stable URLs and correct
content types. **Tests first:** each document downloads with a non-zero length and the right
`Content-Type`; dossiers are not reachable by any public URL.

---

### Task C3: Bilingual scaffolding

**Files:** `pgs/settings.py` (i18n), `locale/af/LC_MESSAGES/`, `core/tests/test_i18n.py`

`LANGUAGES = [("en", …), ("af", …)]`, `LocaleMiddleware`, `User.preferred_language` drives the
default, a language switcher persisted in the session. Ship a **human-translated shell** —
navigation, form labels, chatbot frame, footer — and nothing else (D18).

**Tests first:** `preferred_language="af"` renders the Afrikaans shell; `{% translate %}` keys
exist in both catalogues; **no page content string is machine-translated** (assert the `.po`
files' `#, fuzzy` count is zero — a fuzzy entry is an unreviewed translation).

---

### Task C4: Claim discipline

**Files:** `core/tests/test_claim_discipline.py`

```python
FORBIDDEN = ["pasture raised", "pasture-raised", "GMO free", "biodynamic",
             "chemical-free", "spray-free"]

@pytest.mark.parametrize("url", PUBLIC_URLS)
def test_no_unsupported_claim(client, url):
    html = client.get(url).content.decode().lower()
    for term in FORBIDDEN:
        assert term not in html, f"{term!r} on {url}"
```

Also assert the member list carries the disclaimer, and that no active seal appears with wording
that differs from OPP §V.

**Acceptance:** test passes on every public route; adding "pasture raised" to a template fails it.

---

# Sub-plan D — Grounded chatbot

### Task D1: Chat models

**Files:** `core/models/_chat.py`, `core/tests/test_chat_models.py`

`ChatSession(public_uuid, user?)`, `ChatMessage(session, role, content, latency_ms, model,
prompt_tokens, completion_tokens, retrieved_chunks M2M)`,
`EscalatedQuery(message, question, reason, status, answered_by, answer, answered_at)`.

**Tests first:** an anonymous session may exist with `user=None`; attaching a user later is
allowed (that is how a public visitor graduates — spec §3.1); `public_uuid` is never a sequential
id.

---

### Task D2: `answer_question()`

**Files:** `core/services/_chatbot.py`, `core/tests/test_chatbot_grounding.py`

Contract from spec §6, with the D17 wording:

```
In:  session_uuid: UUID, question: str (non-empty, <= 500 chars)
Out: GroundedAnswer(text, citations: list[Citation], insufficient_context: bool,
                    escalated_query_id | None)
Side Effects: writes ChatMessage rows; writes EscalatedQuery when ungrounded
Fails: RateLimitedError, UpstreamModelError (never a fabricated fallback)
```

Gemini call uses `response_mime_type="application/json"` and the schema
`{answer, citations[{section_ref, quote}], insufficient_context}`.

**Tests first:**

```python
def test_ungrounded_question_refuses_and_escalates(fake_gemini_insufficient):
    out = answer_question(session.uuid, "Which fertiliser brand should I buy in George?")
    assert out.text == REFUSAL                      # exact string, see §D17
    assert out.insufficient_context is True
    assert EscalatedQuery.objects.count() == 1

def test_refusal_fires_on_empty_citations_even_if_flag_is_false(fake_gemini_confident_no_cites):
    ...
```

`REFUSAL = "I cannot find a definitive answer in the SAOSO standard or the Outeniqua PGS documents."`
(D17 — the original SAOSO-only string reflected a scope that no longer holds.)

---

### Task D3: Citation validity

**Files:** `core/tests/test_retrieval_scope.py`, additions to `_chatbot.py`

**Tests first:**
- Every returned citation's `section_ref` exists in the retrieved set; a citation naming an
  un-retrieved ref is dropped and forces `insufficient_context`.
- A `sub_ref`, when present, exists in that chunk's `sub_refs` map — an invented `§4.5(2)(c)(4)`
  is rejected.
- No answer can cite a chunk outside the session's `StandardSet`.
- The `quote` is a substring of the cited chunk's text (after whitespace normalisation).

**Acceptance:** all four pass; a hallucinated section reference fails the suite.

---

### Task D4: Guardrails

**Files:** `core/services/_chatbot.py`, `core/tests/test_chatbot_guardrails.py`

Per-IP rate limit → 429; 500-char cap; conversation-window cap; answer cache keyed on a
normalised question hash; token accounting per message. Tests use `override_settings` for limits
and a fake clock.

---

### Task D5: Chat surface

**Files:** `core/views/_chatbot.py`, `core/templates/chatbot/*.html`, `core/static/js/chat.js`

HTMX for the exchange (single vendored file — no build step). Renders answer, citations as
tappable references, and the escalation action on refusal. Mobile-first: the keyboard must not
obscure the last line (UAT Scenario 6).

**Acceptance:** works with JS disabled to a plain form POST (graceful degradation), and HTMX is
not loaded on any other page that does not use it.

---

## 3. Order of execution

| # | Tasks | Gate |
|---|---|---|
| 1 | A1 → A2 → A3 → A4 → A5 → A6 → A7 | `pytest` green, DB migrates, `/health/` 200 |
| 2 | A8, A10 | CI green; fixtures extracted and `sha256`-verified |
| 3 | A9 | Restore rehearsed (human) |
| 4 | B1 → B2 → B3 → B4 | Parser + chunker tests green; OPP chunk count in the low tens |
| 5 | B5 → B6 → B7 | Four documents ingest; ratchet holds; retrieval recall floor met |
| 6 | C1 → C4 (parallel with 5 once B7 lands) | Public routes 200; claim discipline green |
| 7 | D1 → D5 | Grounding and guardrail tests green; refusal exact |
| 8 | UAT | Eight scenarios judged; 1, 3, 8 provisional if D23 applies |

**Run the two-day offline spike in parallel with step 1.** It is not MVP 0 work, but if it fails,
MVP 1 is a rewrite — better to know before six weeks of chatbot work.

---

## 4. Definition of done

- [ ] Every document ingests with non-zero sections and non-empty `section_ref`
- [ ] `sub_refs` offsets valid; duplicate-ref ratchet not exceeded
- [ ] Full suite green, including claim discipline, retrieval scope, grounding, idempotency, import-linter
- [ ] `/health/` returns 503 when a dependency is down
- [ ] A restore has been performed from the backup drive and recorded in `docs/RUNBOOK.md`
- [ ] All eight UAT scenarios judged acceptable, signed by the seats D23 requires
- [ ] No certification claim anywhere on the public surface — confirmed by the committee, not just the grep

---

## 5. Deliberate omissions

| Not built | Why | Arrives |
|---|---|---|
| `weasyprint`, Sheet J PDF | GTK on Windows for zero MVP 0 value; it is MVP 1's job | MVP 1 |
| `openpyxl`, `django-import-export`, reports | No data to report yet | MVP 3 |
| Playwright suite | No page to drive until C1 | C1 |
| Any farm, assessment or certificate model | MVP 0 makes no claim | MVP 1–2 |
| Translated page content | Needs a named Afrikaans reviewer (D18) | post-MVP 0 |
| Registry seeding | Nothing to verify against yet | MVP 2 |
| Voice notes, aggregation workflow | Spec §17.2, D13 | post-MVP |
