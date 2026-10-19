# Handover — MVP 0: A, B, C1 and C4 landed

**For:** the next agent.
**From:** the corpus-and-retrieval session, then the public-site session — both 2026-10-19.
**Repo state:** `main`, **48 commits**, clean tree except two untracked files (§7).
`verify.sh` green at **336 tests**; `python -m pytest tests/e2e -q` green at **25** more.
**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **configured but
never pushed.** No CI (see §3).

---

## 0. The one thing to know first

**The standards corpus and the public site both exist; the chatbot and the documents page
do not.** `knowledge/` is complete (four formats, TOC map, chunker, ingestion, hybrid
retrieval scoped to a `StandardSet`). The public site is built: six routes, semantic CSS,
self-hosted type, and the claim discipline that keeps it honest. What is missing is
narrow and known: **C2** (`/documents/` — the home page's rows say `Publishing soon`),
**C3** (the EN/AF pill is a disabled control, not a link) and **D** (the chatbot).

**Read `product/design/C1_BUILD_PLAN.md` before touching the site.** Its §3 is a
copy-provenance table — every published string names the OPP, SAOSO or LANDSCAPE passage
it came from — and its §6 lists **nine decisions still with the product owner**, each
currently shipping on a conservative default.

**Before your first commit, run the gate:**

```bash
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh
```

---

## 1. Read these first, in this order

| # | Artifact | Why | Time |
|---|---|---|---|
| 1 | `product/backlog/In Progress/MVP0_PLAN_V2.md` Task **C2**, **C3**, then D1–D5 | Your actual first work. | 20 min |
| 2 | `product/design/C1_BUILD_PLAN.md` | What C1 built, where every string came from, and the nine open decisions. | 20 min |
| 3 | `product/docs/context/testing_hazards.md` | **Read before writing any test.** Twelve entries now; §1.9–§1.12 and §3.8–§3.9 are from the C1 session. | 20 min |
| 4 | `product/design/DESIGN.md` + `product/design/content_inventory.md` | The design of record, and the 16 live-site items a rebuild silently drops. | 25 min |
| 5 | `PGS_PLATFORM_SPEC.md` §4.5 (corpus), §12 (public surface), §18.3 (D40–D43) | The decisions C1 rests on. | 30 min |
| 6 | `product/docs/context/build_principles.md` | Thin views, service ownership, 30 KB cap, integer cents, zero build pipeline. | 10 min |
| 7 | `pgs_docs/` | The authoritative documents. Spot-check claims here, never against a plan or a prototype. | as needed |

Do **not** read `prd.md` as the spec (superseded provenance). Do **not** execute
`product/backlog/Done/MVP0_PLAN.md` (v1 — its SAOSO parser matched nothing).

---

## 2. What exists

| Subsystem | State | Evidence |
|---|---|---|
| **A — foundation** | Complete | custom `User` first migration, `/health/` with four independent checks, Celery retry policies, `lint-imports` contract, `verify.sh` |
| **B — corpus** | Complete | 345 chunks from 4 documents, 30 sections, **0 duplicate `section_ref`s**, FTS + pgvector with RRF (k=60), scope before ranking |
| **C1 — public site** | Complete | six routes, `root.css`/`site.css`/`components.css`/`chat.css`, self-hosted Lora + Mulish, 336 + 25 tests |
| **C4 — claim discipline** | Complete | six forbidden terms, no seal rendered, no dead certificate link, pending documents are chips not anchors |
| **C2 — `/documents/`** | **Not started** | home page rows read `Publishing soon`; `test_claim_discipline` fails if they become links |
| **C3 — bilingual shell** | **Not started** | `LANGUAGES`/`LOCALE_PATHS` set; no `LocaleMiddleware`, no catalogue; AF pill is `aria-disabled` |
| **D — chatbot** | **Not started** | no `_chatbot.py`/`_chat.py` exists at all (verified 2026-10-19 — an earlier handover said "scaffold stubs") |

**The site's architecture, in one paragraph.** `core/services/_public.py` holds every
page's metadata, the nav table and the OPP fee schedule as integer cents;
`public_context(page)` is the only context any public view builds; templates render and
compute nothing; `pgs_extras.format_zar` is the only place money becomes a string. Section
partials carry **bodies**, and each page owns its own headings — a sub-page's `h1` and the
home page's summary of the same content must not share a tag level.

---

## 3. Gates

| Gate | Meaning |
|---|---|
| **A1–A5 migrated** | ✅ Passed. Custom `User` is the first migration |
| **`verify.sh` green** | ✅ 336 tests at HEAD. Before any commit |
| **Playwright green** | ✅ 25 tests: six routes, 390px, measured 44px targets, clean console. Outside the gate by design |
| **B3 needs a second reader** | ⚠️ **Not done.** The Crops template is 38 questions and 37 verdicts by hand |
| **0∥ spike complete** | ⚠️ **Not done.** Before `1∥` freezes `visitPack`/`VisitSyncEnvelope` |
| **A9's restore rehearsal, on the server** | ⚠️ **Not done.** The logged rehearsal was on the dev box; R11 requires it on the VPS |
| **C1's design implemented** | ✅ Verified in code *and* in a browser. UAT Scenarios 4, 6 and 8 are still **unsigned** |
| **UAT sign-off** | ⚠️ **Nothing** in `tests/uat/` is signed. By the local backlog rule, an unsigned UAT makes a human-judged item *partial* — so C1 is partial until Scenario 4/6/8 are judged |

---

## 4. Next steps, in order

1. **C2 — `/documents/`.** `PublicDocument` + seven published items (D22), files copied to
   `media/public/documents/`, stable URLs and content types. Then wire the home page's
   rows, the header's fifth nav link and the footer's Documents column **in the same
   commit** — the tests fail if a link appears before the route does, which is the point.
   Decide `"SOP's"` (§6 #6) before finalising the list.
2. **C3 — bilingual shell.** `LocaleMiddleware`, `af` catalogue, session-persisted
   switcher, `User.preferred_language` default. Translate the *shell* only (D18); assert
   the `.po` files carry **zero** `#, fuzzy` entries.
3. **D — the chatbot.** Models → `answer_question()` → citation validity → guardrails →
   the surface, which already has its two showcase windows waiting in
   `sections/_chat_windows.html` and `.cite` styling in `chat.css`.
4. **Then MVP 1a** (`ready/MVP1A_PRD.md`), gated on the 0∥ spike.

---

## 5. Traps that will bite

> **Extended, not duplicated.** Every trap found while building A, B and C1 — Django
> mutating settings under test, Celery's absent `autoretry_for`, an import-linter config
> that enforced nothing, a `GeneratedField` that had to be proven, **a multi-line `{# #}`
> template comment that is emitted as text and parsed as HTML**, **a media query placed
> above the rule it refines**, **an e2e suite that errors in fixture setup**, **a
> `--noreload` server serving stale templates**, and **a port owned by another project** —
> is recorded with evidence in `product/docs/context/testing_hazards.md`. **Read it before
> writing tests, and append the moment you lose time to something that will recur.**

1. **The polarity trap (R1a-2).** `V16` "risks of contamination of the water source?"
   answered *Yes* is **non-compliant**. `V3` is `INFORMATIONAL`; `V23` and Animal `V14` are
   `NEGATIVE`.
2. **An appendix is one section, deliberately.** Appendix 1 holds two lists that both start
   at `1.`. Evidence in `knowledge/sections/saoso.py`.
3. **`page` is the printed footer number, not the PDF index** (D42). The BPP prints none;
   `page` is NULL and the `anchor` is the only locator.
4. **`OVERDUE` is derived from `due_on`, never stored.**
5. **Never `except: pass`.** Sentry on every exception path, explicit `timeout=` on every
   external call.
6. **Fixtures are evidence.** Nine of them, extracted by `scripts/extract_fixtures.py`.
   Re-run the script rather than editing them.
7. **No fee figure, page title or route may be typed into a template.** They live in
   `core/services/_public.py`; tests fail the build otherwise. The same rule covers the
   chatbot showcase's own answer.
8. **`Publishing soon` must stay a chip.** A link to a route that does not exist raises
   `NoReverseMatch`; a link that goes nowhere is worse.
9. **The live WordPress site is the content baseline, not the design reference.** It
   publishes `pasture raised` and `GMO free` today — the exact claims
   `test_claim_discipline.py` forbids.
10. **Never pipe a schema-changing command into `head`.** Never trust a screenshot until you
    have confirmed which server answered it.

---

## 6. Open — not yours to resolve

**Content decisions for C1 (all currently on defaults; `C1_BUILD_PLAN.md` §6 has the
detail):**

| # | Decision | Shipping default |
|---|---|---|
| 1 | Contact details — the administrator's email and two cell numbers are on the live site | **Withheld**; visible `email`/`phone` chips |
| 2 | Bank details (`NU HORUS NPO`, ABSA, `9288670349`) | **Withheld**; a `bank details to confirm` chip |
| 3 | News in the nav | **Not present** |
| 4 | `/endorsed-farms/` has no honest MVP 0 target | **Not present** |
| 5 | Pledge downloads (farmer + consumer) | **Not present** |
| 6 | Is `"SOP's"` the OPP under another name? | **Assumed yes**; C2 lists eight items |
| 7 | ~~"Fees payable by end of February"~~ — **not in the OPP** | ✅ **Resolved 2026-10-19: withheld.** Removed from `/become-a-member/`; `test_no_unsourced_claim` guards it |
| 8 | Photography consent for four group photographs | **Published** with a consent chip |
| 9 | Six-elements wording: LANDSCAPE verbatim vs the prototype's paraphrase | **Verbatim** |

**Blocked on someone else:**

| Item | Blocked on | Affects |
|---|---|---|
| **Ratify the embedding default** — `gemini-embedding-001` at 768 dims replaced the retired `text-embedding-004`; the *dimension* did not move | The product owner | First real embedding run. One line in settings if wrong |
| **D31 — which land-history periods govern** (12/12/18 vs OPP §V 18/12/12) | **The group** | MVP 2 seal issuance |
| **POPIA consent** for ~31 consumer names, 13 farmer members and four photographs | **The group** | MVP 2 registry; blocks publishing any member list |
| **UAT sign-off seats** (administrator, committee reviewer, consumer member) | **The human** | C1 and 1a acceptance |
| **A reversed logo lockup, an SVG of the mark, a real favicon** | The designer | C1 polish; `logo_mark.png` is a stand-in favicon |
| Seal cardinality; `standard_ref` coverage for ~91 verdicts; hosting cutover; A9's rehearsal on the VPS | MVP 2 / authoring effort | later slices |
| **Push to `origin`?** | The product owner | every commit exists only on this machine |

---

## 7. Untracked files in the tree

Neither is mine to file; both were left untouched:

- `Homtini Assessment Report 22.10.03.docx.pdf` — in the repo root. Looks like a
  third-party farm report; it does not belong in a public repo, committed or otherwise.
- `product/design/f1_restack_fund_fit.html` — a 54 KB explainer on F1/NLnet ReStack fit,
  created at 17:59 during the C1 session. Unrelated to C1; `product/design/` is the right
  home for review artifacts if you want it tracked.

---

## 8. Commands

```bash
# The gate. Run before every commit.
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh

# Browser tests (outside the gate; needs `playwright install chromium` once).
python -m pytest tests/e2e -q

python manage.py check
.venv/Scripts/lint-imports.exe --no-cache --no-logo     # Windows; plain `lint-imports` on Linux
.venv/Scripts/python.exe -m pytest -q
python -m pytest core/tests/test_public.py -k fees      # any single slice

docker compose up -d            # Postgres+pgvector (host port 5433) and Redis. App runs natively (D19)
python manage.py migrate
python manage.py seed_deployment           # idempotent; creates the StandardSet and the seals
python manage.py runserver                 # DEBUG defaults to False — see the note below

# Corpus (the four governed documents, D16)
python manage.py ingest_standard --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf --no-embed
# (…) opp, bpp, landscape — see MVP0_PLAN_V2 §6. Re-running is a no-op: ingestion is
# idempotent on sha256. Drop --no-embed with GEMINI_API_KEY in .env to fill the vector arm.

python scripts/extract_fixtures.py         # regenerate the 9 fixtures (deterministic)
BACKUP_DIR=/tmp/drive scripts/backup.sh    # then: scripts/restore.sh /tmp/drive/db-<stamp>

python product/backlog.py                  # dry-run: drift + suggested moves
python product/backlog.py --write          # regenerate the index only
python product/backlog.py --apply          # move files to match Status: + regenerate
```

**Dev database state:** seeded and ingested — 1 `StandardSet`, 4 documents, 345 chunks,
**no embeddings**, so retrieval reports `lexical_only=True`.

**Windows specifics:** `bash` is git bash; `rsync` is absent (backup falls back to `tar`);
`lint-imports` is not on `PATH` under `python -m pytest`. Throwaway scripts belong in
`_scratch/` (git-ignored) — a stray `inspect.py` in `%TEMP%` shadows the stdlib.

**Two gotchas that cost real time this session, now in `testing_hazards.md` §3.8–§3.9:**
`runserver --noreload` with `DEBUG=False` serves **cached templates as well as stale
modules**, so run visual checks with `DJANGO_DEBUG=1`; and a port can belong to another
project, so assert a string from *your* page before believing a screenshot.

---

## 9. What the C1 session did

1. **C1a** — `root.css` (15 `brand-*` tokens, type scale, layout primitives),
   self-hosted Lora + Mulish as variable woff2, base template, header and footer, all six
   routes. Tailwind is out (D40), so the design became semantic CSS.
2. **C1b** — the home page's nine bands; fees as integer cents from OPP §2.1/§2.3 through
   `format_zar`, so no template can hold a figure; `Publishing soon` chips instead of dead
   links; a zero-JS mobile menu the prototype never had.
3. **C1c** — the five deep pages: four IFOAM principles (SAOSO §2.1–2.4), six basic
   elements (LANDSCAPE verbatim), first/second/third-party trust, the visit committee
   (OPP §3.3), the four outcomes, three member categories, fee conditions (OPP §2.2/§2.3),
   committee roles (OPP §3.1). **No member names** — POPIA.
4. **C4** — claim discipline on every route, each guard mutation-tested.
5. **C1e** — Playwright: six routes, 390px overflow, measured 44px targets, clean console.
6. **Close-out** — `C1_BUILD_PLAN.md` written and statused, `HANDOVER.md` rewritten, six new
   hazard entries, the plan's and PRD's stale `Status:` lines corrected, backlog index
   regenerated.

**The one thing to carry forward:** every defect found in these two sessions was found by
*running the thing* — the real PDFs, a mutation, a query, a browser — and none was visible
in review. Three C1 defects were found by looking at a rendered page. The plan's own code
snippets were wrong four times, and the design prototype's own rules were wrong twice.
