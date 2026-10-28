# PRD: The code atlas — one generated view of the application as built

**Status:** Refinement — a requirement from the product owner (2026-10-28); two decisions (§4) and a plan before it can be built. Supersedes the `CONVENTION.md` note that a state doc was "premature until there is code" — there is code now.
**Owner:** Kobus Meiring (Product) · Build
**Last Updated:** 2026-10-28
**MVP:** Cross-cutting developer tooling, not a product surface. Serves the MVP 0 close-out and every
session after it.
**Scope:** One generated, committed document set in `product/docs/state/` that answers *what is
built* — schema, services, views and routes, async/schedulers, the corpus pipeline, the seams. It
answers nothing about *why* (that is `PGS_PLATFORM_SPEC.md` §18.3) and nothing about *whether it is
good* (that is UAT).
**Reference:**
- `product/backlog/CONVENTION.md` — the "Files" section names `product/docs/state/` and `summarise.py`
- `product/docs/context/build_principles.md` §I (module map), §II (service contracts), §V (guarding)
- `product/docs/context/testing_hazards.md` §2.6 (a test outside the gate is a test nobody runs)
- `HANDOVER.md` §0i — this session's record

---

## 1. Problem Statement

**The product owner cannot see the application's shape without reading it.**

Measured 2026-10-28 on `main` at `2467e6a`:

| Thing | Count | Where it lives |
|---|---|---|
| Python in `core/` + `knowledge/` | **30,744 lines** in 139 files | two apps, 30-odd modules |
| Models | **12 classes**, **87 model fields** | `core/models/` (6 modules), `knowledge/models.py` |
| Services | **11 modules**, **46 public functions**, 20 frozen dataclasses | `core/services/_<domain>.py` |
| Views | **17 view functions** | `core/views/_<domain>.py` (6 modules) |
| Routes | **14 `path()` entries** | `core/urls.py` |
| Celery tasks | **1** (`core.tasks.heartbeat`); **no beat schedule at all** | `core/tasks/_maintenance.py` |
| Management commands | **7** (4 in `core`, 3 in `knowledge`) | `*/management/commands/` |
| Migrations | **36** | `core`, `knowledge` |
| Templates / stylesheets | **28 / 6** | `core/templates/`, `core/static/css/` |
| Test modules | **59** | `core/tests/`, `knowledge/tests/`, `tests/tools/` |

That table is the answer to five ordinary questions — *what tables are there; what does asking a
question do; where do citations come from; does anything run on a schedule; what is ingested and from
what* — and it took a script to produce. Today each of those is a `grep` and a memory.

**Prose rots, and this repo has the receipts.** In the last two days alone:

- `HANDOVER.md`'s header claimed **68** commits ahead and **1237** tests; the tree measured **84** and
  **1265**. (Corrected on 2026-10-28 while writing this.)
- `tests/uat/concordance_uat.md` still says **"unsigned"** in its header while its own table records
  **13 PASS, signed by Kobus (Product)**.
- The most expensive one: `scripts/build_corpus.py`'s generic branch has been dropping every
  document's body since `e6f4464`, and nothing noticed for a day, because no view of the system said
  *which documents the generator can actually produce*. That is a `grep` nobody ran
  (`CORPUS_CANONICAL_FORMAT_PLAN.md`, P4's landing note; `product/design/d71_p4_and_the_generator.html`).

A handover tells you what changed. Nothing tells you **what exists**.

## 2. Requirement

> "I need to view the state of the application development: database structures, key functions and
> views, main services, any schedulers."

In the product owner's terms: **one page I can open, and one file I can diff**, that is true because
it is generated from the code rather than written by hand.

## 3. What it must contain

Every section is derived; none is typed by a human.

| Section | Answers | Derived from |
|---|---|---|
| **Schema** | Every table, its purpose, its columns, its FKs and M2M links, its indexes and constraints, which are status enumerations | `_meta` introspection over `django.apps` (`get_fields`, `get_constraints`, `related_objects`) |
| **Services** | What operations exist, which domain owns them, and each one's `In: / Out: / Side Effects: / Fails:` contract | the module tree plus each function's docstring (first line + the contract block) |
| **Views and routes** | Every URL, the view that serves it, the template it renders, whether it is public | `core/urls.py` + the view modules |
| **Async and schedulers** | Every `@shared_task`, its retry policy, and **whether anything is periodic** (today: no) | `@shared_task` decorators, `CELERY_BEAT_SCHEDULE` presence |
| **The corpus pipeline** | ingest → artefact or PDF → parse → chunk → reviewed table rows → embed → retrieve → cite, with the module for each step and which are build-time | `knowledge/` module map |
| **Commands and seams** | Management commands and what each is for; the settings that switch behaviour (TLS, embeddings, the extractor) | `*/management/commands/*.py`, `pgs/settings.py` |
| **Tests** | One line per test module: what it guards, and the module count — not every test name | test module docstrings |
| **History** | Migrations in order, newest first, so a schema change is traceable to a date | `migrations/0*.py` |

## 4. The two decisions

**D-a — where it lives and in what shape.** Recommendation: `product/docs/state/`, two files —
`atlas.md` (greppable, diffable, reviewable in a PR) and `atlas.html` (self-contained, opens from the
filesystem, prints, uses the design system's tokens). The convention already names this directory.
Rejected: HTML only (invisible in a diff and unfindable by `grep`); `product/design/` (that directory
holds **decisions**, and an artifact there implies a contestable choice).

**D-b — how it stays true.** Recommendation: generate, **commit**, and gate — a test in
`tests/tools/` regenerates the atlas and fails on any difference, and a second test proves that guard
can fail. This is the `knowledge/corpus/bpp.md` idiom applied to documentation
(`CORPUS_CANONICAL_FORMAT_PLAN.md` P3.1), and it is the only version that cannot rot.
Rejected: generate on demand and never commit (then it is not viewable in the repo, and the answer
depends on the reader having run something); commit without a gate (that is the handover problem
again, with better formatting).

Both decisions are cheap to reverse. Neither needs a migration and neither touches the product.

## 5. What it must not be

- **Not a second source of truth.** If a fact can be derived, it is derived. The only hand-written
  text is a preamble ("what this is, how to regenerate it") and the section titles.
- **Not a design artifact and not a backlog item.** It does not go in `product/design/` and it is not
  a PRD after it ships.
- **Not a substitute for the spec, the handover or UAT.** It may *link* to a `D<n>` and never restate
  a decision.
- **Not deployable.** It is build-time tooling: no new runtime dependency, no new app, no model, no
  migration. It must run **without a database, without `pdftotext` and without a network** — the same
  rule the gate already lives under (D57), so it works in `deploy.sh`'s scratch tree.
- **Not a source dump.** One line per function is a map; pasting source is a second repository.

## 6. Success criteria

- [ ] `python scripts/atlas.py` regenerates both files; a second run is a no-op diff.
- [ ] `tests/tools/test_atlas.py` fails when the committed atlas differs from a fresh generation,
      and is proven by breaking it (the guard is mutation-tested, per `AGENTS.md`).
- [ ] It runs with no database, `PDFTOTEXT_BIN=/usr/bin/true`, and no network, in under two seconds.
- [ ] A reader who has never seen the repo answers these six questions from `atlas.html` alone:
      *what tables exist and what they hold*; *what happens when a visitor asks a question*; *where a
      citation's text comes from*; *what runs on a schedule*; *which documents are ingested, and from
      what text of record*; *what the two test lanes are*.
- [ ] Legible at 390 px and printable; no horizontal scroll (the same bar as
      `product/design/d71_p4_and_the_generator.html`).
- [ ] The schema section names all **12** models and **87** fields; the scheduler section says
      **one task, no beat schedule** — because that is the truth today, and a section that cannot be
      wrong is not evidence.

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| It rots like the handover did | D-b: a gate test that regenerates and diffs. A doc with a test is a claim with a proof. |
| It becomes a wall of noise nobody reads | Cap it: one line per function, first sentence of the docstring, no source, no test names. Target ≤ ~300 KB HTML. If a section cannot fit, it becomes a link to the file, not a copy of it. |
| Auto-generated ER diagrams look like a bowl of spaghetti | Start with a **table** of tables plus textual FK arrows; add SVG only if a first reader says it helps. Do not pretend a naive layout is a diagram. |
| Introspection drifts from what a human would say | Derive relationships from `_meta` (`get_fields`, `related_objects`), never from regex over source. Reverse relations and M2M are exactly where a regex lies. |
| It leaks into a public surface | The repo is public; the atlas is schema and signatures only — no secrets, no personal data, no sample rows. Assert that in the generator: it reads no `.env`, no database, no user data. |
| It becomes the place design is argued | It may link to `D<n>`; it may not introduce a term the OPP or SAOSO already names. |

## 8. Open questions

1. **Do we draw the schema as SVG?** Recommend: no, not in v1. A generated diagram of 12 tables is
   usually worse than a table with a "points at" column; revisit when the model count passes ~20.
2. **Should the atlas list every UAT scenario?** Recommend: link to `tests/uat/` and say how many are
   signed. The signatures are the interesting fact, not the scenario text.
3. **Should it include the front-end?** Recommend: a one-paragraph map (which stylesheet owns what,
   which templates exist) and no more — the design surface is `product/design/DESIGN.md`'s subject.
4. **Where does the regeneration command live** — `scripts/atlas.py` (like `build_corpus.py`, a build
   tool) or a `manage.py` command (needs Django settings)? The atlas needs `django.setup()` but no
   database, so either works; a script keeps the app's command surface for operators.

## 9. Execution steps (one session, when approved)

1. Settle D-a and D-b (accept the recommendations, or say otherwise).
2. `scripts/atlas.py` — walk `django.apps`, the module tree and `core/urls.py`; write
   `product/docs/state/atlas.md` and `atlas.html`.
3. `tests/tools/test_atlas.py` — regenerate into a temp directory, compare, and a second test that
   proves the comparison can fail.
4. Point `HANDOVER.md` §0 and `product/backlog/CONVENTION.md` at it, and delete the "premature"
   sentence.
5. Commit the generator **and** the first generated pair together, so the first atlas is not a
   hand-written baseline.

## 10. Does not replace

The handover (what changed), the spec §18.3 (why), UAT (whether it is good), or the backlog (what is
next). The atlas answers one question well: **what exists, right now, in this tree.**

---

## Pre-Flight Checklist

- [ ] No model, no migration, no new app — this ships as a script and two generated files
- [ ] No logic in templates: the HTML is produced by one template string in the generator
- [ ] No `select_related`/`prefetch_related` concerns: the generator issues **no queries**
- [ ] No `transaction.atomic()`: nothing is written outside `product/docs/state/`
- [ ] Runs with the extractor poisoned and no database (D57), like the gate
- [ ] The freshness guard is proven by breaking it, then restored
- [ ] `scripts/verify.sh` stays green, and the atlas test joins the gate via `testpaths`
