# Handover — MVP 0, sub-plan A complete

**For:** the next agent.
**From:** the foundation build session, 2026-10-19.
**Repo state:** `main`, **23 commits**. Sub-plan **A (A1–A10) is complete**: 50 Python
files, **74 tests passing**, `manage.py check` clean, `lint-imports` KEPT.
**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **configured but never
pushed.** No CI.
**Supersedes:** the 2026-10-19 design-session handover (`a245fb7`), which said
"10 commits, no application code yet". That is no longer true.

---

## 0. The one thing to know first

**There is now code, and the foundation is done.** The custom `User` model is migrated
and is the first migration; `core_user` exists and `auth_user` was never created.

**Your next task is B1** (`knowledge/models.py` — corpus models). Sub-plan A is
complete and gates nothing further. B is where HANDOVER's original §2 says the real
technical risk lives, and **A10's fixtures are the ground you build it on** — read
§4 below before writing a single regex.

**Before your first commit, run the gate:**

```bash
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify \
    ./scripts/verify.sh
```

---

## 1. Read these first, in this order

| # | Artifact | Why | Time |
|---|---|---|---|
| 1 | `product/backlog/ready/MVP0_PLAN_V2.md` Tasks **B1–B7** | **Your actual first work.** | 30 min |
| 2 | `product/docs/context/testing_hazards.md` | **Read before writing any test.** Every silent failure found so far, with evidence. | 15 min |
| 3 | `PGS_PLATFORM_SPEC.md` **§4.5** (corpus + the six verified realities) | The parser realities. **Read this before B2.** | 25 min |
| 4 | `PGS_PLATFORM_SPEC.md` §18.3 | 40 decisions (D1–D40). Most "obvious improvements" were considered and rejected. | 30 min |
| 5 | `product/docs/context/build_principles.md` | Non-negotiable: thin views, service ownership, 30 KB cap, integer cents. | 10 min |
| 6 | `docs/RUNBOOK.md` | Backups, restore rehearsal, the client-version trap. | 10 min |
| 7 | `pgs_docs/` | The authoritative source documents. **Spot-check domain claims here, never against a plan.** | as needed |

Do **not** read `prd.md` as the spec (superseded provenance). Do **not** execute
`product/backlog/Done/MVP0_PLAN.md` (superseded — its SAOSO parser matched nothing).

---

## 2. What exists, and what it proved

| Task | Delivered | The finding that mattered |
|---|---|---|
| **A1** | Scaffold, `requirements.txt`, Compose (pgvector+redis) | Host port is **5433**, not 5432 — a native PG17 service owns 5432 and Docker binds alongside it, so `localhost:5432` silently reached the *wrong* server |
| **A2** | Env-driven settings, `pytest.ini` | Django injects `testserver` into `ALLOWED_HOSTS` under test; pytest renames the DB to `test_pgs`. Two plan assertions **could never pass** |
| **A3** | Custom `User`, `UserRole`, `Role`, `Language`; `AUTH_USER_MODEL` | `AUTH_USER_MODEL` cannot be set before the model exists; `blank=False` is validation, not a DB constraint |
| **A4** | `Seal`, `Category` as **data**; `seed_deployment`; issuance guard | `is_active=False` blocks issuance **unconditionally**; the seed does not resurrect a retired seal |
| **A5** | `/health/` — db, redis, broker, **worker** | Broker up + worker down is invisible to a broker-only check |
| **A6** | `pgs/celery.py`, `heartbeat`, retry-policy rule | A real worker had an **empty task registry** and would discard every queued task; the test was masking it |
| **A7** | `.importlinter` + 5 architecture tests | The plan's config was **INI-vs-TOML wrong and enforced nothing while exiting 0** |
| **A8** | `scripts/verify.sh` gate; `deploy.sh` staged | No CI, by decision — see §3 |
| **A9** | `backup.sh`, `restore.sh`, `docs/RUNBOOK.md` | Five bugs, each producing a backup that looked perfect; media restored as **zero files** |
| **A10** | `extract_fixtures.py` + 7 verbatim fixtures + `MANIFEST.json` | **The plan's page numbers were all wrong** — see §4 |

---

## 3. Decisions taken this session

**No CI. Use `scripts/verify.sh`.** GitHub Actions was assessed and rejected: every
check already runs locally, so CI's only real contribution is a different environment —
and that is obtained more strongly on the actual VPS. Evidence: `harvester`, `river`,
`elands`, `plot` and `homtini_store` all have `deploy.sh`, and **none of them run
tests**; harvester's workflow was never fully set up. The gap CI would close is "a
broken commit sits on `main` until the next deploy" — accepted, revisitable at the VPS
cutover as a 10-line wrapper around `verify.sh`.

**`deploy.sh` is staged and guarded** (refuses to run off-server). It verifies **before**
touching the live tree, unlike the established `git pull → migrate → restart` pattern,
which has no position where a test could gate anything.

**`google-generativeai` → `google-genai`** (`970a0b0`). The former is end-of-life and
says so on import. 67 pins.

**MVP 0 before MVP 1a** — decided by the product owner (the previous handover left this
open).

**Sub-plan A's `deviation` from the plan's compose snippet**: host port 5433. Recorded
in `docker-compose.yml` and `MVP0_PLAN_V2.md` A1. **Do not "correct" it.**

---

## 4. Read this before writing any parser (B2) — A10's findings

A10's whole purpose is the guard against v1's failure: a parser written against an
*assumed* format that matched zero lines of the real document, **and whose tests passed
because the fixtures were hand-written.**

**The plan's own page numbers were wrong.** `saoso_part_b` "pp. 60–62" starts one page
early, in the tail of §9.6 (*aquaculture*) — extracting on trust would have grafted
unrelated text onto a processing fixture, reproducing v1 exactly. `saoso_toc` is p2 (p1
is the cover), `APPENDIX 1` is p71. The extractor now verifies an **anchor** on each
start page and fails if it is absent.

**Fixtures are verbatim and must never be hand-edited.** Re-run
`python scripts/extract_fixtures.py`; it is deterministic and its `MANIFEST.json` records
each PDF's `sha256`.

**Two traps already measured, both recorded in `MANIFEST.json`:**

1. **The body prints `APPENDIX 1` in UPPERCASE at ~62 columns; the TOC uses title case.**
   B2's title-case `APPX` regex matches **nothing** in the body (SPEC §4.5 reality 4 is
   correct) but **false-positives on p63**, where `Appendix 4.` begins a mid-sentence
   line. Both cases are in the fixtures.
2. **Some glyphs do not map to Unicode** (byte `0xFF`; `-enc Latin1` yields `0xFF`,
   `-enc ASCII7` yields `-`). So fixtures contain **U+FFFD**. The OPP's pasture-raised
   line carries an en-dash in SPEC §4.3 that **no extractor produces**. Do not "fix" it
   by editing — a hand-corrected fixture stops being evidence.

Confirmed against the fixtures: 28 clauses match `CLAUSE`; the `SECTION B` running header
matches `HDR`; `V`/`VI` match an indent-tolerant `ROMAN`; §4.5's heading sits at **indent
4** and matches `SUB`; and all three item markers (`1.`, `1)`, `a.`) appear across
`opp_4_1`/`4_2`/`4_5`. The outer §4.5 sequence really is **1, 2, 4, 5** — item 3 is
absent, as SPEC §4.5 claims.

---

## 5. Gates

| Gate | Meaning |
|---|---|
| **A1–A5 migrated** | ✅ **Passed.** Custom `User` is the first migration; `auth_user` never created |
| **`verify.sh` green** | Before any commit. It is the single source of truth for "shippable" |
| **B3 needs a second reader** | The Crops template is 38 questions and 37 verdicts by hand. **A template that is 80% complete looks complete** — have someone read the JSON against printed FORM Sheet B.1 |
| **0∥ spike complete** | Before `1∥` freezes `visitPack`/`VisitSyncEnvelope`. **MVP 1a sub-plan G does not start first** |
| **A9's restore rehearsal, on the server** | ⚠️ **Not done.** The logged rehearsal was on the dev box and proves the *scripts*, not the VPS's drive or permissions. R11 requires it before launch |
| **C1's design approved** | `product/design/final_home.html` is approved as *design*. It has never been built, so nothing about it is verified in code |

---

## 6. Traps that will bite

> **Extended, not duplicated:** the traps found while *building* A1–A10 (Django mutating
> settings under test, Celery's absent `autoretry_for`, an import-linter config that
> enforces nothing, the Docker/native-Postgres port collision, five backup bugs, stale
> fixture page numbers) are recorded with evidence in
> **`product/docs/context/testing_hazards.md`**. **Read that before writing tests.** The
> list below is the pre-code, design-and-spec set.

1. **The polarity trap (R1a-2).** Mis-assigning polarity does not crash — it produces
   plausible, wrong data. `V16` "Are there any risks of contamination of the water
   source?" answered *Yes* means **non-compliant**; with the naive
   `is_compliant = (value == YES)` it stores as compliant and looks fine until someone
   queries it in MVP 3. `V3` is `INFORMATIONAL`; `V23` and Animal `V14` are `NEGATIVE`.
2. **Section formats are not what they look like.** Read SPEC §4.5's six verified
   realities before touching ingestion: SAOSO prints `20.1.1.` (**never** `B-20.1.1`),
   part letters are running page headers present on only 22 of 98 pages, the TOC matches
   the clause pattern, and appendix headings do not exist in the body.
3. **`GeneratedField(SearchVector(...))`** may not cooperate with the Postgres version in
   Compose. Fall back to a trigger and say so in the module docstring.
4. **`OVERDUE` is derived from `due_on`, never stored.** Otherwise a nightly job becomes
   load-bearing for correctness, and it will eventually not run.
5. **Never `except: pass`.** Sentry on every exception path, explicit `timeout=` on every
   external call.
6. **Run the thing before you believe it.** See §4. Fixtures come from `pgs_docs/`, and
   **prove a guard can fail** (break it, watch it go red, restore) before trusting green.
7. **Delivered HTML may be markdown-escaped — and that silently breaks it.** Both design
   source files arrived with `\&`, `\[`, `\*` and `&#x20;` escaping. `fontFamily: \['Lora'…\]`
   is a JS `SyntaxError` that killed the whole `tailwind.config` (so *no* colour
   resolved). **A token can be silently absent rather than visibly wrong.**
8. **A Tailwind class may do nothing.** `shadow-xs`/`shadow-2xs` are **v4** names; the CDN
   serves **v3**. 36 of 48 shadow usages are dead, silently.
9. **The WordPress media API is not public** — `/wp/v2/.../media` returns **401**. Asset
   inventory must come from `sitemap.xml`, which means it is **incomplete**.
10. **Never pipe a schema-changing command into `head`.** It sends SIGPIPE, killing the
    migration midway and leaving a partial database.

---

## 7. Commands

```bash
# The gate. Run before every commit.
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh

python manage.py check
.venv/Scripts/lint-imports.exe --no-cache --no-logo     # Windows; plain `lint-imports` on Linux
.venv/Scripts/python.exe -m pytest -q

docker compose up -d            # Postgres+pgvector (host port 5433) and Redis. App runs natively (D19)
python manage.py migrate
python manage.py seed_deployment           # idempotent; data, not migrations (A4)

python scripts/extract_fixtures.py         # regenerate A10 fixtures (deterministic)
BACKUP_DIR=/tmp/drive scripts/backup.sh    # then:
scripts/restore.sh /tmp/drive/db-<stamp>

python product/backlog.py                  # dry-run: drift + suggested moves
python product/backlog.py --apply          # move files to match Status: + regenerate index
```

Use the **local** skills `.agents/skills/pgs-reading-the-backlog`,
`pgs-maintaining-the-backlog`, `pgs-writing-explorations` — not their generically-named
counterparts, which assume other layouts.

**Windows specifics:** `bash` is git bash; `rsync` is **absent** (backup falls back to
`tar` and says so); `lint-imports` is **not on `PATH`** under `python -m pytest`, so it is
located next to `sys.executable`. Run throwaway scripts from a clean directory — a stray
`inspect.py` in `%TEMP%` shadows the stdlib.

---

## 8. Open — not yours to resolve

| Item | Blocked on | Affects |
|---|---|---|
| **D31 — which land-history periods govern** (pledge 12/12/18 vs OPP §V 18/12/12) | **The group** | MVP 2 seal issuance. A certification-integrity question, not a software one |
| **POPIA consent** for the ~31 published consumer names, 13 farmer members, and the photographs | **The group** | MVP 2 registry |
| **The 16 content gaps** in `product/design/content_inventory.md` §3 | A design/writing task | C1 |
| **`/endorsed-farms/`** — 2026/2025 outcomes are live; MVP 0 publishes none | **The group** | The redirect map. Correct for MVP 0, but a visible content loss |
| **Bank details** (`NU HORUS NPO`, ABSA) published today, absent from the design | Someone who knows the intent | C1 |
| **News** in the nav or not; the live site has two News pages | Product decision | C1 scope |
| **Seal cardinality**; which seal applies to "Organic - pending corrective action" | MVP 2 modelling | MVP 2 |
| **`standard_ref` coverage** — clause mappings for the ~91 non-agro-processing verdicts | Authoring effort | MVP 3 gap analysis |
| **Hosting cutover to the VPS** | MVP 2 | D19 still records MVP 0 as a local preview |
| **A9's restore rehearsal on the server** | Whoever has the VPS and the external drive | R11. `docs/RUNBOOK.md` §2.1 has the row waiting |
| **UAT sign-off seats** (administrator, committee reviewer, consumer member) | **The human** | 1a acceptance |
| **A reversed logo lockup and an SVG of the mark** | The designer | C1 |
| **Push to `origin`?** | The product owner | `origin` is configured; nothing has been pushed |

---

## 9. What happened in the earlier sessions

1. **Full review of the target-state spec against the source PDFs** (`F1`–`F5`, `D14`–`D24`).
   Found the MVP 0 SAOSO parser matched **nothing** in the real document (`B-20.1.1` was
   invented), and that "notifiable exception" was defined backwards.
2. **A parser was run over the shipped PDFs** before any plan was rewritten — six
   realities now in SPEC §4.5.
3. **MVP 0 re-planned**; v1 retired to `Done/`.
4. **MVP 1's shape decided** (`D25`/`D26`).
5. **MVP 1a specified** (`D27`–`D33`).
6. **`D34`–`D39`** — 1a field decisions.
7. **The public-site design session** — `product/design/final_home.html`,
   `DESIGN.md`, `content_inventory.md`, `D40` (Tailwind is out).
8. **This session** — **sub-plan A built end to end (A1–A10)**, `testing_hazards.md`
   created, `verify.sh`/`deploy.sh`/`backup.sh`/`restore.sh` delivered, and A10's
   fixtures extracted with the plan's page numbers corrected by measurement.
