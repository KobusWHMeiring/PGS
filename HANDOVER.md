# Handover — MVP 0: A, B, C1, C2, C4 and D landed; chat answer coverage revised

**For:** the next agent.
**From:** the corpus-and-retrieval session, the public-site session, the
documents session, the chatbot session, the column session, the embedding session,
and the answer-coverage session — **2026-10-21**.
**Repo state:** `main`, **51 commits**. **The working tree is NOT clean**: D, the
column-transform work and the 2026-10-21 answer-coverage work are uncommitted (see §7).
`verify.sh` green at **705 tests** (619 before D52, 652 before D53); `python -m pytest tests/e2e -q` green at 34 more.
**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **pushed**. It was
"configured but never pushed" until 2026-10-20; `main` is now on GitHub and the VPS
clones from it. No CI (see §3).
**Live:** `https://organicguarantee.africa` on the homtini VPS (the MVP 0 surface:
site, `/documents/`, grounded `/ask/`, 340 embedded chunks). The install, the five
defects it exposed and everything still outstanding are recorded in
`product/backlog/In Progress/VPS_DEPLOYMENT.md`. Read that before touching
`deploy/` or redeploying.

---

## 0. The one thing to know first

**The standards corpus, the public site and the grounded chatbot all exist.** `knowledge/`
is complete (four formats, TOC map, chunker, ingestion, hybrid retrieval scoped to a
`StandardSet`). The public site is built: **eight** routes, semantic CSS,
self-hosted type, the claim discipline that keeps it honest, and the eight published
documents behind `/documents/<code>/`. Sub-plan **D** now adds `/ask/`: a real form,
a citation audit that refuses on any invented reference, per-IP rate limiting, an answer
cache and an `EscalatedQuery` an administrator can answer. **C3 was deferred out of MVP 0
by the product owner (D44)** — no Afrikaans translator exists, so the AF pill stays a
disabled control and that is deliberate, not a regression.

**D is implemented, not accepted.** D's UAT scenarios — grounding (1), citation relevance
(2) and phone comfort (6) — are unsigned. By the local backlog rule that makes D partial,
exactly as C1 is partial.

**2026-10-21 — the answer-coverage revision is built and measured, not accepted.**
`CHAT_ANSWER_COVERAGE_PRD.md` records it: the assistant now embeds the visitor's *question*
(not the OR-joined tokens), reserves seats for the semantic arm, and may answer with a
**governing rule** when the document does not name the item (“The standard does not name
cardboard…”). Appendix 2 is stored as **30 reviewed table rows**, so a substance and its
condition are one citable passage. Live round 3: cardboard, straw, borax and manure are
grounded; the straw answer no longer borrows wood's condition. **UAT Scenarios 1, 2, 3, 9
and the new 10 are unsigned**, so the feature is partial. The next gaps are listed in §4 and
in the PRD's §7 (G3, G4, G6 and the new G7; **G1, G2 closed by D52 on 2026-10-22**).

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
| 1 | `product/backlog/In Progress/MVP0_PLAN_V2.md` **Sub-plan D (D1–D5)** | What D built and the implementation notes that are not obvious from the code. Skim C3's struck-out task so you do not reopen it. | 20 min |
| 2 | `product/design/C1_BUILD_PLAN.md` | What C1 built, where every string came from, and the nine open decisions. | 20 min |
| 3 | `product/docs/context/testing_hazards.md` | **Read before writing any test.** Eighteen entries now; §1.13–§1.15 are from C2 (a data-driven route the sweeps silently skipped, a `logging` `extra=` collision, a URL segment that is not a slug) and **§2.4 is from D** — `websearch_to_tsquery` ANDs a natural question into zero results. | 20 min |
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
| **B — corpus** | Complete | 340 chunks from 4 documents, 30 sections, **0 duplicate `section_ref`s**, **340/340 embedded** (D48, `lexical_only=False`), FTS + pgvector with RRF (k=60), scope before ranking; pages de-columned at ingest (D46) — 29 transformed, 4 documented exclusions |
| **C1 — public site** | Complete | six routes, `root.css`/`site.css`/`components.css`/`chat.css`, self-hosted Lora + Mulish (C2 added the seventh route and 37 tests) |
| **C4 — claim discipline** | Complete | six forbidden terms, no seal rendered, no dead certificate link, no `Publishing soon` left anywhere; `test_nothing_is_pending_on_a_public_route` runs over all eight routes |
| **C2 — `/documents/`** | Complete | `PublicDocument` + `publish_documents` (idempotent on sha256), eight documents at `/documents/<code>/`, streamed through a view so `is_published` is per request; 379 + 30 tests |
| **C3 — bilingual shell** | **Deferred (D44)** | No Afrikaans translator. `LANGUAGES`/`LOCALE_PATHS`/`User.preferred_language` stay in place; no `LocaleMiddleware`, no catalogue; AF pill is `aria-disabled` — honest, and it must not become a link |
| **D — chatbot** | **Built; UAT unsigned** | `/ask/`, `_chat.py` + migration 0004, `_chatbot.py` (refusal + citation audit + guardrails), vendored HTMX on that page only, 74 tests across `test_chat_models`/`test_chatbot_grounding`/`test_retrieval_scope`/`test_chatbot_guardrails`/`test_chatbot_surface` |

**The site's architecture, in one paragraph.** `core/services/_public.py` holds every
page's metadata, the nav table and the OPP fee schedule as integer cents;
`public_context(page)` is the only context any public view builds — plus
`documents_context()` on the two pages that carry the list; templates render and compute
nothing; the document list lives in `core/services/_documents.py` as *data*: `DOCUMENTS`
is the tuple the deploy copies, the rows render and the tests assert against; `pgs_extras.format_zar` is the only place money becomes a string. Section
partials carry **bodies**, and each page owns its own headings — a sub-page's `h1` and the
home page's summary of the same content must not share a tag level.

---

## 3. Gates

| Gate | Meaning |
|---|---|
| **A1–A5 migrated** | ✅ Passed. Custom `User` is the first migration |
| **`verify.sh` green** | ✅ **768 tests at HEAD** (705 + 63 for the UAT sign-off tooling). Before any commit |
| **Playwright green** | ✅ 34 tests: eight routes, 390px, measured 44px targets, clean console, and a real download click. Outside the gate by design |
| **B3 needs a second reader** | ⚠️ **Not done.** The Crops template is 38 questions and 37 verdicts by hand |
| **0∥ spike complete** | ⚠️ **Not done.** Before `1∥` freezes `visitPack`/`VisitSyncEnvelope` |
| **A9's restore rehearsal, on the server** | ⚠️ **Not done.** The logged rehearsal was on the dev box; R11 requires it on the VPS |
| **C1 + C2 + D built** | ✅ Verified in code, in a browser and with screenshots. UAT Scenarios 4, 6, 8 and 9 (documents) and D's Scenarios 1, 2 and 6 are still **unsigned** |
| **UAT sign-off** | ⚠️ **Nothing** in `tests/uat/` is signed. By the local backlog rule, an unsigned UAT makes a human-judged item *partial* — so C1 and D are partial until their scenarios are judged |

---

## 4. Next steps, in order

1. **Get the UAT signed** — the reasoning and the tooling are in
   `product/backlog/Refinement/UAT_SIGN_OFF_TOOLING_PRD.md` (four decisions needed: where UAT runs,
   screenshot policy, sign-off granularity, who may sign). Nothing in `tests/uat/` is signed, which
   is what makes C1 and D *partial*; the PRD's slice 1 needs no new data and no new rows.
2. **Judge the answer-coverage work.** UAT Scenarios 1, 2, 3, 9 and 10
   (`tests/uat/mvp0_standards_and_public_site_uat.md`). Scenario 10 carries the 2026-10-21
   question suite. Use `python scripts/probe_chat.py` for the raw passages and quotes, then
   judge the UI. The human question is whether *“the standard does not name cardboard”* reads
   as a rule or as permission.
3. ~~**Close the two refusal gaps (G1, G2)** — `S5.5.1` and `S4.1.1` enumerations cannot be
   quoted whole, so the ducks and seed questions refuse. Measure before changing the chunker
   or the prompt.~~ **Closed 2026-10-22 (D52)** — the cause was the extracted page, not the
   chunker or the prompt: a hyphenated word wrapped across a line break, plus the printed
   page footer inside the clause. Both questions are grounded; see §16. **G7** is the
   residual of the same class (a spanning BPP line) and is still open.
3. **Sibling-section retrieval for the cost question (G3)** — the answer omits the R100
   annual membership fee because §2.1 is never retrieved.
6. **Appendices 3, 4, 6a/6b and 7 (G4)** — same reviewed-row mechanism as Appendix 2, starting
   with Appendix 3 and Appendix 4 Table 1.
7. **The escalation answer path (G6)** — `Refinement/ESCALATION_ANSWER_PATH_PRD.md`. The
   refusal currently links to `/contact/`, whose contact details are placeholder chips.
8. **Then MVP 1a** (`ready/MVP1A_PRD.md`), gated on the 0∥ spike.

**Do not add a classifier (G5).** It would not have fixed any 2026-10-21 failure. Reopen only
if a suite question retrieves the **wrong section**, and then prefer a seeded alias table to
an ungrounded model call.

**Two external constraints around D, both still real:**

* **Embeddings are live (D48, 2026-10-20).** `gemini-embedding-001` at 768 dims is ratified,
  and the four documents were force-re-ingested without `--no-embed`: **340/340 chunks carry
  a vector**, `search()` reports `lexical_only=False`. Enabling the arm exposed a retrieval
  interaction — the rare-word vector pushed Appendix 2 out of the top 8 — so the rare-term
  arm is now lexical-only and the vector arm runs once on the OR query (Appendix 2 back at
  #2, BPP at #4, one query embedding per question). `PROMPT_VERSION` is `d47-4` after two
  further prompt iterations. The manure question answers; so does the informal
  `can i use horse manure?` (six verbatim citations), after the BPP page-4 band override.
* **The refusal string is fixed by D17** and is now the shipped constant `REFUSAL` in
  `core/services/_chatbot.py`: *"I cannot find a definitive answer in the SAOSO standard or
  the Outeniqua PGS documents."* Not SAOSO-only: the OPP answers questions the standard does
  not (fees, joining). `test_the_refusal_is_the_d17_wording` keeps the exact string.

**Corpus column defect closed (2026-10-20, D46).** The four governed documents are
de-columned at ingest by `knowledge/columns.py`; SAOSO re-ingests to 293 chunks (was 298),
OPP 30, BPP 9, landscape 8 — **340** in total, and the answer cache invalidated itself via
`_corpus_fingerprint()`. The BPP manure sentence and the SAOSO Appendix 2 condition are now
contiguous in one stored chunk, and the verbatim sentence is accepted by `audit_citations`
while the recorded paraphrase is still refused. Four pages are asserted exclusions with
reasons in `PAGE_LAYOUT_EXCLUSIONS`: SAOSO PDF 2 (TOC — its page-number column is the
content), SAOSO PDF 82–83 (Appendix 4 Table 1 — 4-column rows already coherent), OPP PDF
11 (§6.5 — 3-column table). **UAT Scenario 9 is unsigned.** Two live manure turns on
2026-10-20 were refused for model-side reasons, not corpus corruption: one fabricated a
`sub_ref` from a heading, the other elided a quote with `…`. Both are filed in
`product/backlog/todo.md` as a prompt/model follow-up; the audit is right to refuse them.

**Done since the last handover (D, 2026-10-19).** `/ask/` and the D1–D5 contract: chat
models + migration `0004`; `answer_question()` with the all-or-nothing citation audit;
per-IP fixed-window rate limiting, the 500-char cap, the history window, the answer cache
and token accounting; a vendored HTMX surface that still works as a plain form POST. Two
retrieval facts had to be fixed to make it answer real questions: `websearch_to_tsquery`
ANDs a natural question into zero results, and a common word ("standard") outranks the rare
word that carries the question — `significant_terms` + `search_terms` solve both. See the
plan's “Built 2026-10-19” notes and `testing_hazards.md` §2.4.

**Deferred, do not reopen without the product owner: C3.** The product owner deferred the
bilingual shell on 2026-10-19 (decision **D44**). The AF control stays `aria-disabled` and
must not become a link that reloads the same English page; UAT Scenario 5 is *not
applicable*, not failed. `build_principles.md` §IV is therefore unmet for MVP 0 — every
string added in D is a retrofit when C3 is eventually picked up.

**C2, earlier on 2026-10-19.** `PublicDocument` +
`publish_documents` (idempotent on sha256, wired into `deploy.sh`), eight documents at
`/documents/<code>/` served through a view so `is_published` is checked per request and a
missing file answers 503 rather than 404. The home page's eight `Publishing soon` chips,
the header's fifth nav link and the footer's Documents column all landed in one commit.
Two corrections are recorded in the plan rather than hidden: the list is **eight**, not
the plan's "seven" (D22's enumeration was miscounted), and the model went to
`core/models/_public.py` rather than `_core.py`, which is identity.

**Still open from C2:** the `"SOP's"` question (§6 #6) is answered *by assumption* — if it
turns out to be a separate document, the ninth is one more tuple entry and one more PDF in
`pgs_docs/`, with no migration. The workbook stays unpublished until the committee says
otherwise (D22).

**The chatbot's own open items:** D's UAT is unsigned; retrieval ranking is still open
(Appendix 6b ranks first for "horse", before the rare-term merge); and `PROMPT_VERSION`
in `_chatbot.py` must be bumped whenever the prompt or retrieval changes, or Redis will
serve an answer produced under the old contract. The `/ask/` page is now in the header
nav — six links plus the CTA, added 2026-10-20 — and is still linked from the home
showcase and the footer.

---

## 5. Traps that will bite

> **Extended, not duplicated.** Every trap found while building A, B, C1, C2 and D — Django
> mutating settings under test, Celery's absent `autoretry_for`, an import-linter config
> that enforced nothing, a `GeneratedField` that had to be proven, **a multi-line `{# #}`
> template comment that is emitted as text and parsed as HTML**, **a media query placed
> above the rule it refines**, **an e2e suite that errors in fixture setup**, **a
> `--noreload` server serving stale templates**, **a port owned by another project**, and
> **a natural question that FTS silently matches nothing** — is recorded with evidence in
> `product/docs/context/testing_hazards.md`. **Read it before writing tests, and append the
> moment you lose time to something that will recur.**

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
8. **Documents are served through a view, never from `/media/`.** `is_published` is
   checked on every request, so a document withdrawn in the admin stops downloading for
   the person who bookmarked it — and `DEBUG=True` cannot serve a file the database says
   is private. A published row whose file is missing answers **503**, not 404: the
   document exists, the deployment is wrong.
9. **A retired chip is not a finished feature.** C2's chips became real links in one
   commit, and `test_nothing_is_pending_on_a_public_route` now asserts *no* `Publishing
   soon` survives on any route. If anything is ever pending again, DESIGN rule 8 still
   applies: a tinted chip, never a link to nowhere.
10. **The live WordPress site is the content baseline, not the design reference.** It
    publishes `pasture raised` and `GMO free` today — the exact claims
    `test_claim_discipline.py` forbids.
11. **Never pipe a schema-changing command into `head`.** Never trust a screenshot until you
    have confirmed which server answered it.
12. **A natural question is not a search phrase.** `websearch_to_tsquery` ANDs it into zero
    results (`testing_hazards.md` §2.4). `build_retrieval_query` strips function words and
    `search_terms` searches the rarest term first; do not "simplify" either back to one
    query without running a real question through `/ask/`.
13. **Bump `PROMPT_VERSION` when the prompt or retrieval changes.** The answer cache is
    keyed on it; without a bump, a cached answer produced under the old contract is served
    as though nothing changed.
14. **A model's citation is a claim, not evidence.** Every section ref, sub-ref and quote
    is audited against the retrieved chunk; anything that cannot be checked refuses the
    whole answer. Do not trim a bad citation and keep the rest.

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
| 6 | Is `"SOP's"` the OPP under another name? | **Assumed yes** — that assumption is what makes the list **eight**. If it is a separate document, C2's ninth is one tuple entry and one PDF, no migration |
| 7 | ~~"Fees payable by end of February"~~ — **not in the OPP** | ✅ **Resolved 2026-10-19: withheld.** Removed from `/become-a-member/`; `test_no_unsourced_claim` guards it |
| 8 | Photography consent for four group photographs | **Published** with a consent chip |
| 9 | Six-elements wording: LANDSCAPE verbatim vs the prototype's paraphrase | **Verbatim** |

**Blocked on someone else:**

| Item | Blocked on | Affects |
|---|---|---|
| **An Afrikaans translator** (C3, deferred as D44) | The group | MVP 0 ships English-only. Every string added from here is a retrofit |
| ~~Ratify the embedding default~~ | ✅ **Resolved 2026-10-20 (D48)** — `gemini-embedding-001` @ 768; 340/340 chunks embedded, vector arm live | — |
| **D31 — which land-history periods govern** (12/12/18 vs OPP §V 18/12/12) | **The group** | MVP 2 seal issuance |
| **POPIA consent** for ~31 consumer names, 13 farmer members and four photographs | **The group** | MVP 2 registry; blocks publishing any member list |
| **UAT sign-off seats** (administrator, committee reviewer, consumer member) | **The human** | C1 and 1a acceptance |
| **A reversed logo lockup, an SVG of the mark, a real favicon** | The designer | C1 polish; `logo_mark.png` is a stand-in favicon |
| Seal cardinality; `standard_ref` coverage for ~91 verdicts; hosting cutover; A9's rehearsal on the VPS | MVP 2 / authoring effort | later slices |
| **Push to `origin`?** | The product owner | every commit exists only on this machine |

---

## 7. Untracked files in the tree

**The tree is not clean, and that matters more than any single file.** Uncommitted work
now includes the whole of sub-plan D (`core/services/_chatbot.py`, the chatbot models and
migration 0004, templates, six test files), the column-transform work
(`knowledge/columns.py`, `tests/test_columns.py`, regenerated fixtures), the 2026-10-21
answer-coverage work (`knowledge/tables.py`, `tests/test_tables.py`, `scripts/probe_chat.py`),
and edits to the spec, backlog, handover and UAT. **Commit it before handing off** — the next
agent cannot tell your work from theirs in `git status`.

`Homtini Assessment Report 22.10.03.docx.pdf` is still in the repo root, but it is now
**gitignored** (`.gitignore:25`), so it can no longer be committed by accident. That item is
closed; the file itself is the owner's to delete.

`product/design/f1_restack_fund_fit.html`, the F1/NLnet ReStack explainer, is now tracked;
it is a review artifact, not product code.

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
python manage.py publish_documents         # idempotent (sha256); copies the 8 PDFs into
                                           # media/public/documents/ and upserts the rows.
                                           # Runs in deploy.sh beside seed_deployment — skip it
                                           # and /documents/ links to eight 503s.
python manage.py runserver                 # DEBUG defaults to False — see the note below

# Corpus (the four governed documents, D16)
python manage.py ingest_standard --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf
# (…) opp, bpp, landscape — see MVP0_PLAN_V2 §6. Re-running is a no-op: ingestion is
# idempotent on sha256. Drop --no-embed only if you are intentionally re-embedding; the
# 2026-10-20 corpus is already embedded (D48). --no-embed still works for tests/offline.

# After a corpus change that does NOT touch the PDF (a reviewed table, a parser fix), the
# sha256 guard makes a plain re-run a no-op. Use --force once, deliberately: it deletes the
# old document (and the old chunks' retrieved_chunks links) inside the transaction, after
# embedding. This is what the 2026-10-21 Appendix 2 rows required.
python manage.py ingest_standard --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf --force

# What did the assistant actually retrieve and answer? Read-only, writes no rows, needs a
# key and a corpus. Prints terms, document frequency, the passages with the arm that found
# them, the raw and audited citations. `--chunks-only` skips the model call.
python scripts/probe_chat.py                      # the fixed measurement suite
python scripts/probe_chat.py "can I use straw?"   # one question
python scripts/probe_chat.py --chunks-only        # retrieval only

python scripts/extract_fixtures.py         # regenerate the 9 fixtures (deterministic)
BACKUP_DIR=/tmp/drive scripts/backup.sh    # then: scripts/restore.sh /tmp/drive/db-<stamp>

python product/backlog.py                  # dry-run: drift + suggested moves
python product/backlog.py --write          # regenerate the index only
python product/backlog.py --apply          # move files to match Status: + regenerate
```

**Dev database state:** seeded, ingested and published — 1 `StandardSet`, 4 documents, 340
chunks (SAOSO 293, OPP 30, BPP 9, landscape 8), **all 340 carrying a `gemini-embedding-001`
vector at 768 dims** (D48), 8 `PublicDocument` rows with their files in
`media/public/documents/`. Retrieval reports `lexical_only=False`. Re-ingesting required
deleting the four `StandardDocument` rows first: `ingest_standard` is idempotent on sha256, so
a re-run is otherwise a no-op that leaves the old chunks in place. Migration `core.0004` has been
applied, so the three chat tables exist; a few local sessions were created while verifying
`/ask/` and can be cleared with `ChatSession.objects.all().delete()`.

**Chat configuration** lives in `.env.example` under “Grounded chat”: `CHAT_MODEL`,
`CHAT_TIMEOUT_MS`, `CHAT_RATE_LIMIT`, `CHAT_RATE_LIMIT_WINDOW_SECONDS`,
`CHAT_MAX_QUESTION_CHARS`, `CHAT_HISTORY_MESSAGES`, `CHAT_RETRIEVAL_LIMIT` and
`CHAT_ANSWER_CACHE_TTL`. `GEMINI_API_KEY` is the same key the embedding path uses; with no
key, `/ask/` answers **503**, never a canned answer.

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

---

## 10. What the C2 session did (2026-10-19, later the same day)

1. **Withheld the February fee deadline** — the first thing asked for, and a product
   decision, not a code one: `pdftotext -layout` over the whole OPP contains no month name,
   so the live site's "payable by end of February" was unsourced. Removed; guarded by
   `test_no_unsourced_claim` over all routes, mutation-tested.
2. **C2** — `PublicDocument` (`core/models/_public.py`), `publish_documents`
   (`core/services/_documents.py`) idempotent on sha256, `core/views/_documents.py`
   streaming `/documents/<code>/`, the `/documents/` page, and the home band + header nav +
   footer column rewired in the same commit. `deploy.sh` runs the command.
3. **Playwright** — the seventh route, plus a fixture that publishes the documents (without
   it the suite measured an empty list) and a test that asserts eight download links exist
   so a broken fixture cannot pass as a working page.
4. **Three new hazards** (§1.13–§1.15) and a corrected test elsewhere: C4's sweep was
   silently skipping the new data-driven route, and `test_pending_documents_are_not_links`
   became `test_nothing_is_pending_on_a_public_route`.
5. **Two plan corrections, recorded rather than hidden:** the list is **eight**, not
   "seven" (D22's enumeration was miscounted in three documents), and `PublicDocument`
   belongs in `_public.py`, not `_core.py` as the plan said.

**What the tests could not see, again:** the `logging` `extra={"created": …}` collision, the
octet-stream and rewrite-every-deploy mutations on their first attempt, and the empty-rows
sweep would all have shipped green. Two of the document guards had to be re-broken properly
before their mutation failed.

---

## 11. Session close — the deferral (2026-10-19)

Two product-owner decisions were taken and recorded, not absorbed:

1. **`"Fees payable by end of February"` withheld** — commit `edda927`. The live site's
   claim, absent from the OPP; `test_no_unsourced_claim` refuses it on every route.
2. **C3 deferred out of MVP 0** — `PGS_PLATFORM_SPEC.md` **D44**, `MVP0_PLAN_V2.md` C3
   struck with the reason, UAT Scenario 5 marked *not applicable*, the AF control left
   `aria-disabled`. No Afrikaans translator; a machine translation would pass every test
   except the one about honesty.

**State at the C2 close (historical; D has since landed — see §12):** 50 commits (plus this
one), tree clean apart from the two untracked files in §7, `verify.sh` green at **387**,
Playwright **30**. That session closed with MVP 0 one sub-plan from done; D is now built,
and only its UAT is outstanding.


---

## 12. What the D session did (2026-10-19, later again)

1. **D1 — models.** `core/models/_chat.py` + migration `0004`: `ChatSession` pinned to a
   `StandardSet` and keyed by `public_uuid`, `ChatMessage` with cost and retrieved evidence,
   `EscalatedQuery` with `OPEN`/`ANSWERED`/`CLOSED`. Anonymous sessions are first-class;
   `attach_user()` graduates a visitor without starting a new conversation.
2. **D2 — `answer_question()`.** The exact D17 refusal; a refusal is written for the model's
   flag, empty citations, an invalid citation, an empty answer or no retrieved chunks.
   `UpstreamModelError` propagates — the view says “unavailable” and never guesses.
3. **D3 — the citation audit.** Every `section_ref`/`anchor` must be in the retrieved set,
   every `sub_ref` in the chunk's offset map (a bare item number is resolved only when
   unambiguous), every quote a whitespace-normalised substring. One failure refuses all.
4. **D4 — guardrails.** Fixed-window per-IP limit (429), 500-char cap, bounded history,
   answer cache keyed on a normalised question and `PROMPT_VERSION`, token accounting.
5. **D5 — the surface.** `/ask/` with a plain form POST and an HTMX fragment path; HTMX
   2.0.4 vendored and loaded only there; citations open to show the quote and source; the
   refusal offers `/contact/`. The home showcase and the footer link to it.
6. **Two retrieval corrections, both found by running a real question.** `websearch_to_tsquery`
   ANDs the words and returned **zero** chunks for “What does the standard say about
   traceability?”; a plain OR let “standard” outrank “traceability”. `significant_terms()` +
   `search_terms()` search the rarest term first, then the OR fallback. Without this the
   chatbot would have refused every real question while the phrase-shaped suite was green.
7. **Hazards added:** `testing_hazards.md` §2.4. Plan implementation notes added to
   `MVP0_PLAN_V2.md`; UAT table and Scenario 1 setup corrected to `/ask/` and D17.
8. **Tests:** 65 chat tests (465 total), Playwright 34. `verify.sh`, `manage.py check` and
   `lint-imports` green. The browser was used to verify a real grounded answer, a citation
   opening, the 429/503 notices, the phone scroll position and the no-JavaScript POST.
9. **Explainer artifact:** `product/design/d5_chat_interface_explainer.html` is a
   self-contained walkthrough of the pipeline, the stops, and the session/history model. No
   CDN, no external font, no network; it opens from the filesystem and has a local-notes box.

**What the tests still cannot see:** whether a citation that resolves is *topically* the
right passage. The first live answer on 2026-10-19 cited a landscape paragraph for a
question about the standard's traceability requirement; the prompt now prefers governing
documents, but only UAT Scenario 2 can judge whether that is enough.


---

## 13. What the corpus-column session did (2026-10-20)

The PRD is `product/backlog/ready/CORPUS_COLUMN_EXTRACTION_PRD.md` and the plan beside it;
both were moved to `In Progress/` (build complete, UAT unsigned) by this session.

1. **`knowledge/columns.py`** (new, pure, no Django): `column_bands()` detects vertical
   whitespace bands by coverage (≥0.70, ≥6 crossing lines, ≥12% of characters on each side);
   `de_column()` re-emits a page column 1 top-to-bottom, then column 2, never cutting a
   line that has text across the band; no band returns the *same object*.
   `de_column(bands=…)` is kept for tests and a future per-page override.
2. **`apply_layout(pages, doc_key=…)`** is the pipeline entry point: it consults
   `PAGE_LAYOUT_EXCLUSIONS` (data, not a `layout` flag) and returns the transformed pages
   plus the 1-based **PDF** page numbers that changed. 33 pages are detected; 29 are
   transformed; the four exclusions are SAOSO PDF 2, 82, 83 and OPP PDF 11.
3. **Ingest wiring.** `ingest_standard` applies the transform between `extract_pages()` and
   the parser, and `IngestReport.layout_pages` reports what it touched; the management
   command prints `N layout pages`. A standard ingested with explicit metadata and no
   `doc_key` gets generic detection — no special case, no migration (D16).
4. **`heading.py::_page_stamp` rescued.** It read the *last* non-blank line, which the
   reordering moves to the middle of a landscape page, silently nulling every landscape
   `page`. It now searches anywhere for the last bare-number line. Measured page sets:
   SAOSO/OPP unchanged, BPP `[None, None, None, 10]`, landscape `[4, 4, 6, 7, 7, 9]`.
5. **Fixtures** are produced by the same pipeline (`pdftotext -layout` then
   `apply_layout`) and the manifest records `pipeline`, `layout_pages` and per-page
   **pre-transform** hashes. Regenerating changed exactly `bpp_intro`, `landscape_seals`,
   `opp_4_1` and `MANIFEST.json`; `saoso_toc` came out byte-identical because PDF 2 is
   excluded — the negative control.
6. **Tests added:** `knowledge/tests/test_columns.py` (21), ingest layout tests,
   parser page-attribution pins, and two audit tests in
   `core/tests/test_chatbot_grounding.py` (verbatim accepted, recorded paraphrase
   refused). Full gate: **526 passed**, `lint-imports` kept. Each guard was also observed
   failing by disabling the transform.
7. **D47 (2026-10-20) — the model-side citation contract.** The product owner chose option A:
   `SYSTEM_PROMPT` now requires a character-for-character quote (no paraphrase, no ellipsis),
   and `build_prompt()` tells the model to omit `sub_ref` unless the passage lists that exact
   sub-clause (`none — omit sub_ref for this passage` when it has none). `PROMPT_VERSION` is
   `d47-4` after the retrieval fix and the later prompt iterations in §14, invalidating the
   cache; the audit was not changed. **Verified live 2026-10-20:**
   the manure question returned a grounded answer with three Appendix 2 citations, all
   verbatim and all with `sub_ref=None`. The run cited no BPP passage (it preferred the more
   specific Appendix 2 conditions), so UAT Scenario 9's "at least one BPP citation" sub-check
   is still a human judgement, not a corpus defect.
8. **What is *not* done:** UAT Scenario 9 is unsigned (the BPP-citation sub-check is the open
   part). Table row association is still not reconstructed; the two excluded Appendix 4
   Table 1 pages and OPP §6.5 need a multi-gutter treatment.


---

## 14. What the embedding session did (2026-10-20)

1. **D48 ratified** by the product owner: `gemini-embedding-001` at 768 dims. One live call
   validated the model and the width before anything was deleted.
2. **Forced re-ingest with embeddings.** The four `StandardDocument` rows were deleted (a
   plain re-ingest is a no-op on sha256), then ingested without `--no-embed`: SAOSO 293, OPP
   30, BPP 9, landscape 8 — **340/340 embedded**, `embedded=True` in every report.
3. **A retrieval regression, found by running the question.** With the vector arm on,
   `search_terms` embedded the rare word *and* the OR query. The rare-word vector retrieved
   S5/Appendix 6b and pushed SAOSO Appendix 2 out of the top 8, so the manure question refused
   again. Fixed structurally: the rare-term arm is lexical-only, the vector arm runs once on
   the OR query. Appendix 2 returns at #2 and BPP at #4, and a question now spends **one**
   query embedding instead of two. Tests: `use_vector=False` spends no call; `search_terms`
   makes exactly one embedding call, on the OR query.
4. **`PROMPT_VERSION` moved to `d47-4`**: `d47-2` for the retrieval change, then `d47-3`
   and `d47-4` after two more live refusals on `can i use horse manure?`. The model stitched
   quotes with `...`, then without an ellipsis across two numbered passages; the contract now
   says one citation = one contiguous excerpt from one numbered passage, with a separate
   citation per excerpt. The schema description says the same. The audit was never changed.
5. **Live result (long question):** grounded answer, two verbatim Appendix 2 citations,
   `sub_ref=None`, under `d47-2`. No BPP citation in that run (BPP was retrieved at #4; the
   model preferred Appendix 2's conditions).
6. **A second corpus split, on the same page.** The short question exposed that BPP PDF 4's
   default band `(38, 42)` started inside the left list item `a. Sustainable land management2 ?`,
   so rule 2 kept that line whole and the right column's `harvesting a crop…` was stranded:
   the raw-manure 60-day rule was not contiguous. A measured override — `PAGE_LAYOUT_BANDS`
   `bpp: {4: [(40, 42)]}` — makes it contiguous, and also `the addition of animal manure
   (composted)`. Pinned by two tests in `knowledge/tests/test_columns.py`; both fail if the
   override is removed. BPP was re-ingested with embeddings (9 chunks, `embedded=True`).
7. **Live result (short question):** `can i use horse manure?` now answers with six verbatim
   citations (`Appendix 2` × 5, `S1`), no `sub_ref`. Still no BPP citation in that run.
8. **Composer (same session).** Enter sends, Shift+Enter inserts a newline, and the hint
   under the textarea says so. It clicks the real Ask button, so required-field validation
   and HTMX's submit interception still apply; an in-flight request is not duplicated. The
   composer is also **optimistic**: `htmx:beforeRequest` appends the visitor's bubble and
   clears the box after the form has been serialised, so the turn appears immediately. The
   response no longer resets the form, so a question typed during the wait survives; a 429
   puts the text back, and a network failure removes the optimistic bubble and restores it.
   Verified by `tests/e2e/test_chat_composer.py` (four browser tests, POST held so no Gemini
   call).
9. **Still open:** UAT Scenario 9's BPP sub-check and human sign-off; the broader retrieval
   ranking defect (Appendix 6b still ranks #1 for "horse" before the rare-term merge).

---

## 15. What the answer-coverage session did (2026-10-21)

**The question that started it:** *"Can I use cardboard from my neighbours?"* refused, while
SAOSO 4.4.4 (material applied to land must comply with Appendix 2) sat in the corpus.
Reproduced against the shipped corpus, not guessed: retrieval gave the model S2.4, S23.9
(child labour), Appendix 1 ×2 and the BPP general principles. `cardboard` has document
frequency 0, so `search_terms` dropped it and searched the rarest *known* word,
`neighbours`.

1. **D49 — retrieval embeds the question.** `search(vector_query=)`; `SEMANTIC_SEATS = 3`;
   an out-of-vocabulary term caps the lexical proxy at two chunks and gives the semantic arm
   the rest; chat `RETRIEVAL_LIMIT` 5 → 8. Measured: embedding the sentence puts 4.4.4 at
   rank 6; the OR string does not retrieve it.
2. **D50 — the governing-rule answer mode.** Rule 4 answers with the rule that governs an
   unnamed item, says plainly that the document does not name it, and forbids inferring
   permission from silence. `PROMPT_VERSION` `d49-1`. D17's refusal string is unchanged.
3. **D51 — Appendix 2 as 30 reviewed rows.** `pdftotext -table` aligns the table's rows
   where `-layout` cannot (rows overflow the gutter). `knowledge/tables.py` holds the cells
   and the measured `TABLE_BANDS`; ingest substitutes one chunk per row.
   `ingest_standard(force=True)` / `--force` re-ingests unchanged bytes, deleting inside the
   transaction after embedding. Assumptions are in the module docstring and the PRD.
4. **Round 3 (live, after a forced re-ingest: 321 SAOSO chunks, embedded).** Cardboard,
   straw, borax and manure grounded; straw no longer says it must be untreated; borax quotes
   the trace-elements row. **Still refused:** ducks/bedding compost (`S5.5.1`) and seed grown
   organic (`S4.1.1`) — the enumerations cannot be quoted whole. **Still missing:** the R100
   annual membership fee in the cost answer (§2.1 not retrieved).
5. **Diagnosis worth keeping.** I first assumed the Appendix 2 chunks were stale. They were
   not: rebuilding every chunk in memory found 0 of 340 different. The pipeline really does
   produce the interleaved text. `testing_hazards.md` §1.24 records the rule — diff the
   stored rows against the pipeline before proposing a re-ingest.
6. **Gate:** 619 tests green, `lint-imports` kept. `scripts/probe_chat.py` is the measuring
   instrument for the next round: read-only, writes no rows, prints the passages, the raw
   quotes and the audit verdict.

---

## 16. What the refusal-gap session did (2026-10-22)

**The two refusals the last handover queued as G1/G2 were not model failures — they were
the extracted page.** That is the whole finding, and it is the same lesson as D46, D47 and
`testing_hazards.md` §1.24: measure the corpus before touching the chunker or the prompt.

1. **Reproduced both, then read the stored text.** The ducks question refused with
   `S5.5.1: the quote is not in the cited chunk` and `sub_ref 'a' does not exist in the
   chunk`; the seed question refused with `S4.1.1: the quote is not in the cited chunk`.
   The chunk text was
   `… 15% dry matter per non-` / `P a g e | 47` / `ruminant calculated …` — i.e.
   `pdftotext -layout` broke a line inside `non-ruminant` and the printed page footer was
   not furniture, so it landed *inside* a clause that continues onto the next page.
   `post-harvest` in `S4.1.1` had the same line-break defect. No quote of either printed
   sentence could be a whitespace-normalised substring, so the model elided with `...` and
   the audit — correctly — refused.
2. **`knowledge/reflow.py` (D52).** A line ending in letter-hyphen is rejoined with the next
   non-blank line when that line starts lowercase, **keeping the printed hyphen**; blank
   lines are crossed because SAOSO prints double-spaced. It runs after `de_column` (line
   adjacency is reading adjacency only then) and before the parser, in `ingest_standard`
   **and** in `scripts/extract_fixtures.py` (manifest pipeline is now
   `pdftotext -layout + de_column + reflow v2`, with `reflow_pages` recorded separately from
   `layout_pages`). Measured on the four governed documents: **20 joins** (SAOSO 12, OPP 4,
   BPP 3, landscape 1), every one a genuine compound, and **no page ends inside such a
   word** — which is why a per-page pass is complete.
3. **`PAGE_FOOTER` is now furniture.** `is_furniture()` already dropped the registration and
   contact block; the `P a g e | 47` line was not included, so **65 of 368 chunks** carried
   one. `page_number()` still reads the footer from the page *before* any line is
   classified, so no section lost its page.
4. **Re-ingested all four with `--force`** (the sha256 guard makes a corpus change
   unreachable otherwise): SAOSO 319, OPP 30, BPP 9, landscape 8 = **366 chunks, 366
   embedded**. `report.reflow_pages` prints `N reflow pages` beside `N layout pages`.
5. **Measured result, `scripts/probe_chat.py`, no prompt change and no audit relaxation:**
   - ducks / bedding compost → **grounded**, 4 citations (S5.5.1, Appendix 2 ×2), no
     `sub_ref`;
   - seed grown organic → **grounded**, 2 citations (S4.1.1, S4.1), the paragraph quoted
     verbatim.
   `PROMPT_VERSION` stays `d49-1`: the answer cache already keys on
   `_corpus_fingerprint()`, which moved when the chunks did.
6. **Tests: 652 green** (was 619), `lint-imports` kept. New:
   `knowledge/tests/test_reflow.py` (20 — synthetic contract, pinned per-document join
   counts, the "no wrap crosses a page" measurement, and the two live sentences quotable
   from one chunk), three furniture/parser tests in `test_section_parsers.py`, seven ingest
   tests in `test_ingest.py`, and three in `core/tests/test_chatbot_grounding.py` that run
   the **real** audit over really ingested bytes: the repaired sentence accepted, the
   recorded elision still refused, a lettered item still not a `sub_ref`. Each guard was
   observed failing (reflow disabled, footer un-furnished) before being trusted.
7. **Fixtures regenerated** — 6 of 9 changed. Four of those changes are the reflow itself
   (`bpp_intro`, `opp_4_1`, `opp_4_5`, `saoso_appendices`); the other two were already
   modified in the working tree by the previous session. Verified by rebuilding the
   fixtures *without* reflow and diffing: the only delta is the joined words.
8. **Recorded, not fixed: G7.** One BPP general-principles line spans the gutter
   (`… fertilisers (agro-` / `and thereafter …`), so `de_column` keeps it whole and
   `HeadingParser` splits it into two body lines; the left column's prohibition is still not
   contiguous. Same class as Appendix 2 — it needs a reviewed line or a measured band
   override, not a line join.

**Nothing is committed.** The tree now holds three sessions' work: D, the column transform,
the answer-coverage work and this one. `git add` by path if you want this isolated — note
that `knowledge/tests/fixtures/` also carries the previous session's uncommitted
regeneration, so committing the fixtures commits both.

---

## 17. What the canonical-corpus session did (2026-10-22)

**The finding:** four consecutive sessions had been repairing *extraction* rather than the
product (D46 columns, D51 tables, D52 reflow, G7 spans), because the extractor sat on the
ingest path — every layout irregularity became a wrong or refused chatbot answer. The fix
is architectural, and it is recorded as **D53**: the text of record is a **reviewed
artefact** per document, extraction runs per *edition*, and a layout defect becomes a line
in a diff. Freezing happens at the **section** level; chunking and embeddings stay derived.

1. **`knowledge/corpus.py` (new, pure)** — the format and its reader. Markdown with
   `<!-- page: N printed: M -->` markers, `##` headings, `<!-- ref: … -->`, text verbatim.
   A block with no page marker is an error. `CORPUS_EDITS` holds reviewed corrections as
   **data**, so a test can prove each was necessary and applied. 14 tests
   (`test_corpus_format.py`).
2. **`knowledge/corpus/bpp.md`** — the BPP, 13 pages, reviewed, 5 corrections. Frozen at
   `generator: knowledge corpusgen v2` with `raw_pages` recorded in the header.
3. **`scripts/build_corpus.py` (new)** — drafts the artefact: `extract_pages` →
   `apply_layout` → `reflow_pages` → the section parser for *which headings exist*, then
   page-by-page body text with page markers. Refuses to overwrite an existing artefact
   without `--force`, because only the operator knows whether it was reviewed.
4. **Three generator improvements the review produced** (the "prefill" work):
   - **`columns.py`: bands narrowed to the columns no line writes into.** The detected
     gutter started inside the left column (long lines overflow into it), so those lines
     were kept whole and the right column was emitted inside them. Measured: BPP's
     uncuttable lines **66 → 13**, losslessly, on 6 pages; SAOSO/OPP unchanged by
     construction. **G7's cause disappeared entirely** — no span-cut code was needed.
   - **Per-page `-raw` fallback in the generator.** Measured: `-raw` is a
     character-for-character **permutation** of `-layout` on all **139** pages, so its
     order is trustworthy; it glues words, which is repairable by splitting each glued
     token into the run of `-layout` words that concatenates to it. A page is drafted from
     `-raw` only when, after that repair, its word multiset is identical — **11 of BPP's
     13 pages**, including 3, 6 and 9, the pages geometry cannot handle.
   - **`page_stamp()` shared** with `HeadingParser` — the printed page is read from the
     de-columned rendering, because the two renderings disagree where a stamp shares a
     line with body text (the BPP's `02`).
5. **`ingest_standard(..., corpus_path=)` + `--from-corpus`** — the artefact's sections are
   used instead of parsing the PDF; the PDF is still hashed and must match the artefact's
   recorded sha256; a mismatch, or another document's artefact, is refused.
   `IngestReport.corpus_digest` records which review produced the corpus.
   `--from-pdf` still works and is still tested.
6. **Tests: 705 green** (was 652), `lint-imports` kept. The guards are the point: character
   multiset coverage, section-identity equality between the two paths, per-block
   traceability, edit necessity/application, and the four sentences the product quotes.
7. **G7 closed, live.** Re-ingested the BPP from the artefact (9 chunks, embedded) and
   probed: *"can I use synthetic fertilisers or agro-chemicals?"* → **grounded**, 4
   citations, the BPP's prohibition quoted verbatim. The manure question still cites
   "Animal manure must be preferably composted prior to application…" verbatim, which is
   why the page-4 footnote had to move.
8. **Ten more examples, generated and tested** (the request that closed the session):
   ten BPP requirements — GM seed, organic-seed sourcing, landless husbandry, daily
   pasture access, hen rest hours, breeding-stock 10%, approved cleaning agents, feed from
   the farm, and the two already cited — each asserted to be quotable from **exactly one
   chunk** (`knowledge`) and accepted by the **real audit** (`core`). A paraphrase is still
   refused. One candidate was rejected because it had been quoted from memory and the
   document prints "Employment **practice** should be", singular: every example is copied
   from the artefact. Live probes for two of them cited SAOSO (S5.1.9, S5.5.3) rather than
   the BPP, which is the "prefer the governing document" rule working.
9. **What a human still fixes** (5 corrections): the page-4 footnote interrupting the
   manure sentence, the glued `Preventativemethods(`, and the repeated four-principle
   strip on pages 8 and 10 (kept on page 6). The bare page stamp is now a generator rule.

**Not done:** the OPP, landscape and SAOSO are still on the PDF path. Two follow-ups are
recorded in the PRD §7 and matter: a reviewed edit needs `--force` because idempotency is
keyed on the PDF's sha256 (nothing compares the stored `corpus_digest`), and
`CORPUS_DOCUMENTS` lives beside the models so the generator needs Django settings.

**Uncommitted, again.** This session added `knowledge/corpus.py`, `knowledge/corpus/bpp.md`,
`scripts/build_corpus.py`, `knowledge/tests/test_corpus_*.py`, the ingest/command/columns
changes and the docs. The fixture/column changes from D52 are still uncommitted beneath it.

---

## 18. NEXT UP — **judge the UAT and sign it** (the tooling is built)

**Nothing in `tests/uat/` is signed.** That is still the single fact keeping C1 (public site) and D
(chatbot) *partial*, and it stands between MVP 0 and done. **The tooling that makes it possible
landed on 2026-10-22** — see §19. What remains is a human sitting down and judging, which is the
one thing no session can do for itself.

**The three commands, in order:**

```bash
# 1. Is the instance ready? Keep the output: the reviewer sees it.
python manage.py uat_seed --check > preflight.txt

# 2. One self-contained HTML at product/design/uat/<slug>.html
python scripts/uat_runner.py --file tests/uat/mvp0_standards_and_public_site_uat.md \
                             --preflight preflight.txt --database <the DB being signed>

# 3. The reviewer judges every card and downloads uat-<slug>-signoff.json. Then:
python scripts/uat_signoff.py --file tests/uat/mvp0_standards_and_public_site_uat.md \
                              --from <the export> --dry-run
```

| Piece | File | What it does |
|---|---|---|
| Skill | `.agents/skills/pgs-presenting-uat/SKILL.md` | the three moves, the hard rules, the anti-patterns |
| Format + gate + scan | `scripts/uat_parse.py` | parses the UAT format; refuses a scenario with no `Judgement:`; the applicability scan |
| Shell | `scripts/uat_page.py` | CSS, script, markdown renderer, `environment()` |
| Runner | `scripts/uat_runner.py` | one self-contained HTML; no CDN, no network, `file://` |
| Write-back | `scripts/uat_signoff.py` | `--dry-run` diff; `**Result:**` per scenario + `### Per-scenario results`; idempotent |
| Preflight | `core/services/_uat.py`, `manage.py uat_seed --check` | **366 chunks**, 0 unembedded, **8 published documents**, settings, health, `pdftotext` |

**D1–D4 are settled** (PRD §9, confirmed 2026-10-22): staging for anything that writes and production
for read-only scenarios; screenshots optional; one sign-off row per scenario; one seat each, product
may co-sign.

**Definition of done:** scenarios 1, 2, 3, 6, 9, 10 and C1's 4, 6, 8 carry a result and a signature
in `tests/uat/mvp0_standards_and_public_site_uat.md`, applied by `uat_signoff.py` and committed. That
flips C1 and D from partial to done.

### Two operational items that outrank it, and are cheap

1. **The deployed corpus predates D52 and D53.** `deploy/deploy.sh` migrates, seeds, publishes and
   collects static — it **never runs `ingest_standard`** — so the live chatbot is answering from
   text without the hyphen reflow, the page-footer fix or the BPP artefact. Refresh the four
   documents once on the box, deliberately (`--force` each), confirm **366 chunks** and
   `lexical_only=False`, then ask three questions through `/ask/`. Also check `pdftotext -v`: if the
   server runs poppler and this box runs Xpdf 4.00, the extraction differs from every fixture.
2. **`--force` must not go into `deploy.sh`.** It re-embeds on every deploy, changes every chunk id,
   and cascades through `ChatMessage.retrieved_chunks` — every historical answer loses its evidence
   trail. The recommended replacement is `corpus_check` (read-only diff, no API calls) in the deploy
   plus `corpus_refresh --apply` as a deliberate operator command; `deploy.sh` may fill an **empty**
   corpus but must only *report* drift on a non-empty one. Written up in
   `CORPUS_CANONICAL_FORMAT_PRD.md` §7 item 1, awaiting a yes/no.

### Then, in order

`0∥` spike (the real gate for intake flows, `MVP1A_PLAN` §D26) → MVP 1a → the OPP/SAOSO artefact
conversion (absorbs G4) → G3 (the cost answer omits the R100 membership fee) → G6 (the refusal
promises a person who cannot be reached).

### Session close, 2026-10-22

`verify.sh` green at **705 tests**, `lint-imports` kept, backlog index clean (`product/backlog.py`
reports no drift). **The tree is uncommitted**: 12 modified files plus 6 new ones — the corpus
artefact and reader (`knowledge/corpus.py`, `knowledge/corpus/bpp.md`), the generator
(`scripts/build_corpus.py`), two test modules, `CORPUS_CANONICAL_FORMAT_PRD.md`, and the
`UAT_SIGN_OFF_TOOLING_PRD.md` this section is about. `HEAD == origin/main` (`91cec12`, the ops
commit), so **none of this session's work is deployed** — it needs one commit and a push before the
deployed corpus can be refreshed from it.

---

## 19. What the sign-off-tooling session did (2026-10-22)

**The blocker was never the scenarios — it was that signing one took a developer.** Slice 1 of
`UAT_SIGN_OFF_TOOLING_PRD.md` is built: a reviewer opens one HTML file, runs the preflight, judges,
and exports a file that writes the results into the UAT markdown. **Nothing is signed yet** — that
is a human act, and it is now the only thing left.

1. **`scripts/uat_parse.py` (new, pure).** The only code that knows the UAT file's shape: front
   matter, `## Scenario N — …` sections, labelled fields, numbered steps, notes, and the line spans
   the write-back needs. It **refuses** rather than copes — a scenario with no `Judgement:` clause,
   a duplicate scenario number, or a missing `feature slug` is an error naming the scenario, because
   a card built from a guess is a judgement nobody was asked to make.
2. **The applicability scan — the thing this session exists for.** An N/A scenario outlives the
   decision that caused it unless something checks. `scan_applicability()` requires every N/A to
   cite a `D<n>` in its `**Status:**`, requires the id to exist in `PGS_PLATFORM_SPEC.md` §18.3, and
   requires that decision's resolution to **still read as a deferral**. Edit D44 to say C3 is picked
   up and the runner exits non-zero naming Scenario 5, instead of printing a greyed-out card for a
   scenario that has become deliverable. Pinned by test at **10 scenarios / 9 applicable / 1 N/A**,
   and by §2.5 of the tests (`mvp1a`'s twelve).
   *No model decides this.* The product owner asked whether an LLM (via OpenRouter) should; the
   answer recorded is no — the artefact must make **zero network requests** (its own acceptance
   criterion), a signature has to be reproducible from the commit, and HANDOVER §4 already settled
   the same shape of question ("prefer a seeded alias table to an ungrounded model call").
3. **`scripts/uat_page.py` + `scripts/uat_runner.py`.** The runner was 37 KB in one file and broke
   the 30 KB cap, so the shell (CSS, script, markdown renderer, `environment()`) is its own module.
   The artefact embeds the raw markdown in a `uat-data` payload *and* renders it server-side, so it
   works with JavaScript off and a test can check the words the reviewer read.
4. **`scripts/uat_signoff.py`.** Two things change and nothing else: a `**Result:**` line after each
   `Judgement:` paragraph, and a `### Per-scenario results` table plus a `**Signed against:**` line
   carrying the commit and database. `--dry-run` prints the diff, a second application changes
   nothing, and a malformed export is refused whole rather than half-applied.
5. **`core/services/_uat.py` + `manage.py uat_seed --check`.** Six rows, observed beside expected:
   settings, dependencies, **366 chunks**, 0 unembedded, **8 published documents**, `pdftotext`.
   The corpus blocks; health and `pdftotext` advise, because `celery_worker` is legitimately absent
   on a dev box and a row that is always red is a row nobody reads. **Measured on this box: 366
   chunks, 0 without a vector, 8 published, Xpdf 4.00** — so the dev DB matches §17 exactly.
   Slice 1 has no `--scenario` seeder: MVP 0 needs no new rows, and a bare `uat_seed` exits 2 rather
   than pretending.
6. **63 tests in `tests/tools/` plus 4 browser tests in `tests/e2e/test_uat_artefact.py`**, and `pytest.ini`'s `testpaths` now includes `tests/tools` — a test outside
   `testpaths` is a test the gate never runs (`testing_hazards.md` §2.6). Gate green at **768**,
   `lint-imports` kept. Eight guards were mutation-tested: the steps split, the deferral check, the
   judgement gate, the insertion point, the reason requirement, the CRLF guard, HTML escaping and the
   blocking corpus row each failed a test when broken.
7. **Two defects, both invisible to a green suite.** (a) Extracting the script left the IIFE's
   closing `})();` inside the body *and* wrapped it again, so Chromium threw `Unexpected token '}'`
   and the page was inert — every structural assertion stayed green because the cards are
   server-rendered. Found only by loading it in Playwright and reading the console
   (`testing_hazards.md` §1.30). (b) `write_text` emits CRLF on Windows (§1.27, already recorded).
   **Verified in a real browser:** ten cards, ten judgement blocks, the N/A card carrying D44's
   reason, progress `1 of 10` → `10 of 10`, a downloaded export that `uat_signoff.py --dry-run`
   accepts, one request (the file itself), a clean console, and no horizontal overflow at 390 px.
   **Mutation-tested:** re-introduce the defect and all 63 gate tests stay green while three of
   the four browser tests go red — which is the whole argument for keeping them.
8. **Also recorded:** §1.29 — a string "present" in a JSON payload is not present in the file, because
   `json.dumps` escapes the newlines; and §3.10 — Xpdf's `pdftotext -v` prints its version and exits
   **1**, which made the preflight row permanently red until the check became "a banner was printed".

**The artefact is committed at `product/design/uat/mvp0_standards_and_public_site.html`.** It records
`Generated <date>` from the machine that built it, so **regenerate it on the box whose commit it
claims** before handing it to a reviewer.

**Next, in order:** judge the UAT (§18) → slice 2's `uat-setup` format and the
`manage.py <command>` existence lint (which is what catches `mvp1a`'s `load_template`) → the two
operational items in §18 → MVP 1a.
