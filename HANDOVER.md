# Handover — MVP 0, sub-plans A and B complete

**For:** the next agent.
**From:** the corpus-and-retrieval session, 2026-10-19.
**Repo state:** `main`, **39 commits**. Sub-plan **A (A1–A10)** and sub-plan **B
(B1–B7)** are complete: 245 tests passing, `manage.py check` clean, `lint-imports`
KEPT. The standards corpus ingests all four governed documents (**345 chunks**) with
**zero duplicate section references**, and hybrid retrieval answers from it, scoped to
a `StandardSet`.
**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **configured but
never pushed.** No CI (see §3).

---

## 0. Update — C1 session (2026-10-19, later the same day)

**The public site exists.** Sub-plan C1 landed in five commits: `root.css` + `site.css` +
`components.css` + `chat.css` as semantic CSS (Tailwind is out, D40), self-hosted Lora and
Mulish, all ten designed bands on `/`, and five real routes — `/organics/`,
`/how-it-works/`, `/members/`, `/become-a-member/`, `/contact/`. Claim discipline (C4)
landed early because C1 wrote the copy it guards.

- **Next: C2** (`/documents/`). The home page's document rows are chips reading
  `Publishing soon` — `core/tests/test_claim_discipline.py` fails the build if one becomes
  a link before the route exists. Then C3 (the EN/AF pill is a disabled control, not a
  link) and sub-plan D.
- **Read `product/design/C1_BUILD_PLAN.md`** — its §3 is a copy-provenance table (every
  published string names its source document) and its §6 lists the nine decisions still
  with the product owner: contact details, bank details, News, pledge downloads, the
  February fee deadline, photography consent, and the six-elements wording.
- **The gate is green at 336 tests**, and `python -m pytest tests/e2e -q` adds 25 browser
  tests (needs `playwright install chromium`; deliberately outside `testpaths`).
- **Four new entries in `testing_hazards.md`** — §1.9 (a multi-line `{# #}` is emitted as
  text *and* parsed as HTML: it restructured the header), §1.10 (a media query above the
  rule it refines loses), §1.11 (a sibling margin inside a grid track shrinks the card),
  §3.8 (a `--noreload` server with `DEBUG=False` serves stale templates *and* modules).

---

## 0. The one thing to know first

**The corpus is done; the surface is not.** `knowledge/` is complete and tested:
parsers for three document formats, a TOC page map, a chunker, ingestion, and hybrid
retrieval. **What does not exist is any way for a person to see it** — there are still
zero HTML templates in the repo. `pgs/urls.py` routes `/health/` and `/admin/` and
nothing else.

**Your next task is C1** (`MVP0_PLAN_V2.md`, sub-plan C): implement the approved public
site from `product/design/final_home.html` per `product/design/DESIGN.md`. D (the
chatbot) then sits inside that surface. C1 is a design-implementation task, not a
backend one — read `product/design/DESIGN.md` and the `implementing-redesigns` skill
before touching a template, and note D40: **Tailwind is out**, the design is a visual
specification, not a code asset.

The dev database is already seeded and ingested (§7), so retrieval can be exercised
the moment there is a page to exercise it from.

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
| 1 | `product/backlog/In Progress/MVP0_PLAN_V2.md` Tasks **C1–C4**, then D1–D5 | **Your actual first work.** B's tasks are historical now. | 30 min |
| 2 | `product/docs/context/testing_hazards.md` | **Read before writing any test.** Every silent failure so far, with evidence. §1.8 is new and cost this session an hour. | 15 min |
| 3 | `product/design/DESIGN.md` + `final_home.html` | The only permitted source of tokens. Four palettes exist in `product/design/`; only one is the design system. | 20 min |
| 4 | `product/design/content_inventory.md` §3 | The 16 items the live site has that a rebuild would silently drop. | 10 min |
| 5 | `PGS_PLATFORM_SPEC.md` §4.5 and §18.3 | §4.5 now carries **corrected** parser realities; D41–D43 are new and load-bearing. | 30 min |
| 6 | `product/docs/context/build_principles.md` | Thin views, service ownership, 30 KB cap, integer cents. | 10 min |
| 7 | `pgs_docs/` | The authoritative source documents. Spot-check claims here, never against a plan. | as needed |

Do **not** read `prd.md` as the spec (superseded provenance). Do **not** execute
`product/backlog/Done/MVP0_PLAN.md` (v1 — its SAOSO parser matched nothing).

---

## 2. What exists, and what this session proved

Sub-plan A (A1–A10) is unchanged — see git history and the previous handover in that
range. Sub-plan B, built this session:

| Task | Delivered | The finding that mattered |
|---|---|---|
| **B1** | `StandardSet`, `StandardDocument`, `DocumentChunk`; `vector(768)` + generated `tsvector` | `GeneratedField(SearchVector(...))` **works** on PG 16.15 — HANDOVER §6's warned fallback is not needed. A `section_ref` CHECK forbids `""` but permits NULL, so heading-only documents are storable and a parser bug is not |
| **B2** | `sections/` — `saoso`, `opp`, `heading`, `registry`; 2 new fixtures (`bpp_intro`, `landscape_seals`) | The plan's own OPP item regex **drops §4.5's items 4 and 5** and **invents `4.5(3)`**; its appendix regex is title-case and matches nothing real |
| **B3** | `sections/toc.py` — page map, appendix spans, printed↔PDF coordinates | The plan's `segment_appendix(page=71)` is the PDF index; D42 stores the printed page (70). A test on page 71 alone is insensitive to that offset — it sits inside a span |
| **B4** | `chunking.py` — section-level chunks, paragraph splitting, overlap, re-based `sub_refs` | "sub_refs never overlap" cannot hold literally; nested refs nest by design. Measured: OPP 13 sections → 14 chunks |
| **B5** | `embedding.py` — batched, explicit timeout, retries, no zeros | `text-embedding-004` is **retired**; the default is now `gemini-embedding-001` with `output_dimensionality=768`, so B1's frozen column survives (**ratify this — §8**) |
| **B6** | `extraction.py`, `ingest.py`, `ingest_standard` command | **Appendix 1 contains two independently numbered criteria lists** (printed pp. 71–72 and 73–75), both running `1.`–`6.`. Splitting on those lines emitted `S1.2` twice. An appendix is now one section, and the duplicate-ref ratchet is **0**, not "~50" |
| **B7** | `services.py` — FTS + pgvector, RRF k=60, scoped before ranking | RRF is not a mean: 1st+3rd beats 2nd+2nd. Two vector-space scores are not comparable, which is why fusion is on ranks |

**Measured corpus** (dev DB, ingested): SAOSO 298 chunks, OPP 30, BPP 9, landscape 8 —
345 in total, from 30 sections (SAOSO 271 sections, OPP 28, BPP 4, landscape 6).

**Retrieval, as a developer sees it today** (lexical only — no embeddings ingested):

```
Q: traceability of organic processing
   S20.1.2   p60  '20.1.2. Handlers and processers shall ensure traceability…'
Q: labelling of organic products
   S22.1.3   p65  '22.1.3. Processed products shall be labelled according to…'
   S1        p22  'Nanomaterials …'        ← the glossary, a topical-but-wrong neighbour
Q: poultry manure
   (nothing)
```

That last pair is the honest state of the world: FTS finds the right clause and also
the glossary, and misses paraphrases entirely. **That is what the vector arm is for, and
what UAT Scenario 2 exists to judge** — the automated suite pins structure, not
usefulness.

---

## 3. Decisions taken this session

Recorded in `PGS_PLATFORM_SPEC.md` §18.3 — read them there, not here:

- **D41 — corpus scope: SAOSO Section B and its appendices only.** Section A collides
  with *itself* (`1.` is both PREAMBLE p5 and BASIS p8), and Section C restarts at `1.`.
  A globally unique `section_ref` for the whole PDF does not exist.
- **D42 — `page` is the printed number in the document's footer**, not the PDF index.
  They differ by one (SAOSO prints `P a g e | 60` on PDF p61); the OPP and the
  landscape stamp numbers equal to their PDF index; the BPP stamps none.
- **D43 — `section_ref` stores the citation a human reads**: `S20.1.1`, `§V`,
  `§4.2(5)`; `sub_refs` stay plain. `B.20.1.1` is withdrawn — it appears nowhere.
- **No CI. Use `scripts/verify.sh`.** Unchanged from the previous session, and it
  remains the single source of truth for "shippable".
- **`google-genai`, `text-embedding-004` → `gemini-embedding-001`** (see §8).

Two parser realities in SPEC §4.5 were **wrong** and are corrected there with
measurements: `SECTION C` does appear in the body (p94/95/97, above its appendices), and
all twelve appendix headings *do* exist in the body in UPPERCASE — across four separator
shapes and indentation 0–62.

---

## 4. Gates

| Gate | Meaning |
|---|---|
| **A1–A5 migrated** | ✅ Passed. Custom `User` is the first migration |
| **`verify.sh` green** | ✅ 245 tests at HEAD. Before any commit |
| **B3 needs a second reader** | ⚠️ **Not done.** The Crops template is 38 questions and 37 verdicts by hand. A template that is 80% complete looks complete |
| **0∥ spike complete** | ⚠️ **Not done.** Before `1∥` freezes `visitPack`/`VisitSyncEnvelope`. MVP 1a sub-plan G does not start first |
| **A9's restore rehearsal, on the server** | ⚠️ **Not done.** The logged rehearsal was on the dev box; R11 requires it on the VPS |
| **C1's design approved** | ✅ As *design*. Nothing about it is verified in code |
| **UAT sign-off** | ⚠️ **Nothing** in `tests/uat/` is signed. Sub-plan B has no human-judgement items (the parser/retrieval rows are automated), so B is complete without one; C and D are not |

---

## 5. Traps that will bite

> **Extended, not duplicated:** every trap found while building A and B — Django
> mutating settings under test, Celery's absent `autoretry_for`, an import-linter config
> that enforces nothing, the Docker/native-Postgres port collision, five backup bugs,
> stale fixture page numbers, a `GeneratedField` that had to be proven, and (new, §1.8)
> a one-letter fixture-name typo that pytest reports as an impossible-looking error —
> are recorded with evidence in **`product/docs/context/testing_hazards.md`**. **Read it
> before writing tests.**

1. **The polarity trap (R1a-2).** Mis-assigning polarity produces plausible, wrong data.
   `V16` "risks of contamination of the water source?" answered *Yes* is
   **non-compliant**. `V3` is `INFORMATIONAL`; `V23` and Animal `V14` are `NEGATIVE`.
2. **An appendix is one section, deliberately.** Appendix 1 holds two lists that both
   start at `1.`. Do not "improve" this into `Appendix 1(1.2)` — it resolves to two
   different paragraphs. The evidence is in `knowledge/sections/saoso.py`.
3. **`page` is not the PDF index.** If a new document prints no page number (the BPP
   does not), `page` is NULL and the `anchor` is the only locator. Do not invent one.
4. **`OVERDUE` is derived from `due_on`, never stored.**
5. **Never `except: pass`.** Sentry on every exception path, explicit `timeout=` on every
   external call. `EmbeddingError` on a batch is raised, not smoothed over.
6. **Fixtures are evidence.** Nine of them, extracted by `scripts/extract_fixtures.py`,
   hashed in `MANIFEST.json`, anchors verified. Re-run the script rather than editing
   them. `knowledge/extraction.py` is now the *only* `pdftotext` call, shared with that
   script, so ingest and fixtures cannot drift.
7. **A Tailwind class may do nothing**, and delivered HTML may be markdown-escaped.
   Both cost the design session hours. A token can be silently absent.
8. **The WordPress media API is not public** — asset inventory from `sitemap.xml` is
   incomplete.
9. **Never pipe a schema-changing command into `head`** (SIGPIPE mid-migration).
10. **Write-then-run in one shell call can read a stale file.** There is a documented
    instance in `testing_hazards.md` §3.3. Separate the write from the run.

---

## 6. Commands

```bash
# The gate. Run before every commit.
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh

python manage.py check
.venv/Scripts/lint-imports.exe --no-cache --no-logo     # Windows; plain `lint-imports` on Linux
.venv/Scripts/python.exe -m pytest -q

docker compose up -d            # Postgres+pgvector (host port 5433) and Redis. App runs natively (D19)
python manage.py migrate
python manage.py seed_deployment           # idempotent; now also creates the StandardSet (B6 needs it)

# Corpus (the four governed documents, D16)
python manage.py ingest_standard --doc saoso     --file pgs_docs/saoso-version-2.1-2026.pdf --no-embed
python manage.py ingest_standard --doc opp       --file "pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf" --no-embed
python manage.py ingest_standard --doc bpp       --file "pgs_docs/Basic Production Principles_ENG_PRINT.pdf" --no-embed
python manage.py ingest_standard --doc landscape --file "pgs_docs/PGS Certification landscape_Final.pdf" --no-embed
# Drop --no-embed (with GEMINI_API_KEY in .env) to populate the vector arm.
# NOTE: the version flag is --doc-version, not --version: Django reserves --version.
# Re-running any of these is a no-op — ingestion is idempotent on sha256.

python scripts/extract_fixtures.py         # regenerate the 9 fixtures (deterministic)
BACKUP_DIR=/tmp/drive scripts/backup.sh    # then:
scripts/restore.sh /tmp/drive/db-<stamp>

python product/backlog.py                  # dry-run: drift + suggested moves
python product/backlog.py --apply          # move files to match Status: + regenerate index
```

**Dev database state:** seeded and ingested — 1 `StandardSet`, 4 documents, 345 chunks,
**no embeddings**. Retrieval therefore reports `lexical_only=True`. To exercise the
vector arm, re-ingest one document without `--no-embed` and with a key.

**Windows specifics:** `bash` is git bash; `rsync` is absent (backup falls back to
`tar`); `lint-imports` is not on `PATH` under `python -m pytest`. Run throwaway scripts
from `_scratch/` (now git-ignored) — a stray `inspect.py` in `%TEMP%` shadows the stdlib.

---

## 7. Open — not yours to resolve

| Item | Blocked on | Affects |
|---|---|---|
| **Ratify the embedding model default** — `gemini-embedding-001` at 768 dims replaced the retired `text-embedding-004`; the *dimension* did not move | The product owner | First real embedding run. One line in settings if wrong |
| **D31 — which land-history periods govern** (12/12/18 vs OPP §V 18/12/12) | **The group** | MVP 2 seal issuance |
| **POPIA consent** for the ~31 consumer names, 13 farmer members and photographs | **The group** | MVP 2 registry |
| **The 16 content gaps** in `content_inventory.md` §3 | A design/writing task | C1 |
| **`/endorsed-farms/`** — 2026/2025 outcomes are live; MVP 0 publishes none | **The group** | The redirect map |
| **Bank details** (`NU HORUS NPO`, ABSA) published today, absent from the design | Someone who knows the intent | C1 |
| **News** in the nav or not; the live site has two News pages | Product decision | C1 scope |
| **Seal cardinality**; which seal applies to "Organic - pending corrective action" | MVP 2 modelling | MVP 2 |
| **`standard_ref` coverage** — clause mappings for the ~91 non-agro-processing verdicts | Authoring effort | MVP 3 gap analysis |
| **Hosting cutover to the VPS** | MVP 2 | D19 records MVP 0 as a local preview |
| **A9's restore rehearsal on the server** | Whoever has the VPS and drive | R11 |
| **UAT sign-off seats** (administrator, committee reviewer, consumer member) | **The human** | 1a acceptance |
| **A reversed logo lockup and an SVG of the mark** | The designer | C1 |
| **Push to `origin`?** | The product owner | 39 commits exist only on this machine |
| `knowledge/views.py` is an empty Django scaffold stub, in an app that must never have views | Anyone, in passing | A misleading file, not a bug |

---

## 8. What happened this session

1. **B1** — corpus models, with the `section_ref` NULL-vs-`""` decision and a proven
   `GeneratedField`.
2. **A conversation with the product owner** that resolved the `S20.1.1` vs `B.20.1.1`
   contradiction from the FORM workbook, and produced **D41–D43** plus two corrected
   SPEC §4.5 realities.
3. **B2** — three parsers written against verbatim fixtures, with two new fixtures for
   the heading-only documents. Mutation-tested: every guard was broken and restored.
4. **B3** — the TOC page map, where a test that passed while ignoring the page offset
   was caught by mutation and rewritten to sit on a span boundary.
5. **B4** — the chunker, where "sub_refs never overlap" had to be interpreted rather
   than obeyed, and recorded as such.
6. **B5** — embeddings; the retired model found and replaced while keeping the frozen
   dimension; the switch to a lazily-constructed client so importing `knowledge` never
   needs a key.
7. **B6** — ingestion, which found the appendix double-numbering defect that made the
   plan's "~50 duplicate refs" a parser artefact, and reduced the ratchet to zero.
8. **B7** — retrieval; scope-before-ranking proven on both arms, RRF arithmetic pinned,
   and the lexical floor kept independent of any API key.
9. **Close-out** — `seed_deployment` now creates the `StandardSet` (without it the first
   ingest was a dead end), the dev database seeded and ingested, the backlog index
   regenerated, and this document rewritten against git rather than its predecessor.

**The one thing to carry forward:** every defect found this session was found by
*running the thing* — the real PDFs, a mutation, a query — and none of them was visible
in review. The plan's own code snippets were wrong four times.
