# AGENTS.md — Outeniqua PGS Digital Platform

## What this repo is

A greenfield Django 5.2 monolith digitising the Outeniqua PGS organic certification
process, plus the public PGS Outeniqua website and a strictly grounded chatbot over
the SAOSO standard.

## Start here - the recipe, not the shelf

`python scripts/context.py --task <chat|corpus|reader|public|backlog>` prints what to read for
the task, in order, with a **READ** or **SEARCH** mode per file and a read budget. Follow it, and
stop when the question is answered. `--check` names every breach; the measurements and the four
proposed cuts are in `product/docs/context/CONTEXT_BUDGET.md`.

The shelf below is what exists, not a reading list. Nothing is read whole unless the recipe says
READ.

| Purpose | Where |
|---------|-------|
| **Current state - START HERE block only** | `HANDOVER.md`; history is one file per session in `product/docs/handover/` |
| **The product spec (target state)** | `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` - SEARCH section 18.3 for a decision |
| Build rules - non-negotiable | `product/docs/context/build_principles.md` |
| **Testing hazards - search before writing a test** | `product/docs/context/testing_hazards.md` |
| **Front-end design - only when designing or changing a view** | `product/design/DESIGN.md` |
| PRDs, plans and UAT | `product/backlog/<bucket>/` (the directory is the status), `tests/uat/` |
| Source documents (authoritative) | `pgs_docs/*.pdf`, `pgs_docs/*.xlsx` |

`pgs_docs/` holds the governing documents: the Outeniqua PGS Principles, Policies and
Procedures (the OPP — cited throughout the spec), SAOSO Standard v2.1 2026, the
assessment workbook, the checklists, and the certification landscape. **These are the
source of truth for domain language.** Cite them rather than inventing terminology.

## Context discipline

Measured 2026-11-02 over the 47 PGS session logs: **1.70 billion tokens processed cumulatively**,
a median of **26 M cumulative per session**, and **26 API requests per user message**. Each tool
call re-sends the whole conversation, so cost grows with the number of tool calls, not with the
number of prompts. The habits that cost the most, and the rule for each:

- **Grep first, then read a range.** `cat`/`sed`/`head`/`tail` was 3,769 calls returning 8.5 MB.
  Use `rg -n`, then `read` with `offset`/`limit`; never dump a whole file to answer a question.
- **Write a probe once.** 1,492 `python - <<'PY'` heredocs put the whole script in the transcript
  and re-send it on every later request. Put it in `_scratch/` and re-run it.
- **Bound every output.** `pytest -q --tb=line -x 2>&1 | tail -40`, `git diff --stat`, `rg -m`.
  A full log is read once by you and hundreds of times by the context.
- **One screenshot, one read.** 189 image reads / 51.6 MB; `home-desktop.png` was read 10 times.
  Read a shot once, and start a new session for a new design pass.
- **End at a task boundary.** The 100 M-token sessions are the 300-450-request ones. When the
  task's gate is green, write the session record and start a new session; don't keep the context
  alive for the next question.
- **State is short; narrative is archived.** `HANDOVER.md` stays within 250 lines
  (`tests/tools/test_handover.py`), and a session's story goes to
  `product/docs/handover/SESSION_<tag>_<date>_<slug>.md`.

## Architecture at a glance

- **`core/`** — the application: accounts, member, farm, visit, assessment,
  certificate, aggregation, chat, public site.
- **`knowledge/`** — the standards corpus and retrieval engine. A library: no users,
  no views, no sessions.
- **The dependency is one-directional.** `core` may import `knowledge`;
  `knowledge` must **never** import `core`. Enforced by `lint-imports` in CI.
- **Zero build pipeline.** No npm, no bundler, no Tailwind build step. All JS is
  vendored in `core/static/`.
- **Code encodes the PGS process; data encodes the standard and the group.**
  Seals, categories, document corpora and questionnaires are data. A retarget to
  another standard or PGS group **must not require a migration**.

## Backlog

This repo uses the **Harvester backlog convention** (see `product/backlog/CONVENTION.md`).

- For reading or maintaining the backlog, use the **local** skills
  `pgs-reading-the-backlog` and `pgs-maintaining-the-backlog` under `.agents/skills/`.
  Do **not** use the generic `reading-the-backlog` / `maintaining-the-backlog` skills —
  those assume a different (River-style) layout.
- `product/backlog/backlog.md` is a **generated index** — never hand-edit it.
- Commands:
  - `python product/backlog.py` — dry-run: report drift + suggested moves
  - `python product/backlog.py --write` — regenerate the index only
  - `python product/backlog.py --apply` — move files to match `Status:` + regenerate
- The directory a PRD lives in is the **source of truth**; its `Status:` line is advisory.
- HTML mockups and review artifacts live in `product/design/`, not in the backlog.
- To explore or explain a decision as a shareable HTML page, use the **local** skill
  `pgs-writing-explorations` under `.agents/skills/`. Do **not** use `designing-in-html` for
  this — that one prototypes production UI with CDNs and a different token set.

## Conventions that bite people

- **Three budgets, one loop, and a hard cap.** `scripts/fast.sh --critical` is the after-edit check:
  the eight files that guard what this repo cannot get wrong (claim discipline, the `knowledge`→`core`
  boundary, the citation audit, retrieval scope and floors, the eval instrument's own integrity, the
  test harness) — **measured 22 s warm, 48 s in tests cold (55 s wall)** on 2026-10-30. It is a *subset of files the
  gate already runs*: no test lives only there, and nothing was removed from the gate to make it fit.
  `scripts/fast.sh` is the whole suite minus the `slow` marker (`--reuse-db`, `-x --ff`; target ≤60 s
  warm, measured 155 s cold here). `scripts/verify.sh` is the gate: `--create-db`, `--durations=15`,
  run once per commit and always before a deploy (measured 197 s cold on 2026-10-30). **No edit waits
  more than three minutes on tests** — if a budget is missed, move a file between the budgets; never
  invent a fourth lane and never delete a test to make a number. Running the gate after every edit is
  what cost 4.5 h of full-suite runs in 32 sessions (`product/docs/context/TESTING_TIME_PLAN.md`).
  pytest runs `pgs.settings_test`, which swaps in a fast password hasher — every
  `create_user(password=…)` otherwise pays ~0.5 s of PBKDF2, and it was 2× the whole suite.
  `tests/tools/test_test_harness.py` guards that the override cannot reach `manage.py`, WSGI or the
  gate.
- **Do not benchmark a suite once.** The same tree, same command, measured 253 s → 42 s on one day
  (`testing_hazards.md` §3.17). Quote cold and warm, or measure nothing.

- **A test that passes for the wrong reason is worse than no test.** Every silent failure
  found during A1–A7 — Django injecting `testserver` into `ALLOWED_HOSTS`, pytest
  renaming the test database, Celery's `autoretry_for` being absent rather than `None`, an
  import-linter config that enforces nothing while exiting 0 — is recorded with evidence in
  `product/docs/context/testing_hazards.md`. **Read it before writing tests, and append to it**
  the moment you lose time to something that will recur. Prove a guard can fail (break it,
  watch the test go red, restore) before trusting it green.
- **One palette, and it is `brand-*`.** Any new or changed front-end view follows
  `product/design/DESIGN.md` — cream grounds, Lora + Mulish, the `brand-*` tokens, ≥44 px
  targets. That document is scoped to front-end design; do not read it to build a model. A new
  colour family is a bug, not a preference: this repo carries four palettes in `product/design/`
  and only one of them is the design system.
- **The live WordPress site is the content baseline, not the design reference.**
  `product/design/content_inventory.md` inventories its 13 URLs and the 16 items the current
  design would silently drop. It also publishes `pasture raised` and `GMO free` today — the
  exact claims `test_claim_discipline.py` forbids. Read the inventory before writing sub-plan C.
- **No unsupported certification claims.** The public surface may reproduce only the
  four FORM outcomes and the *active* seals. Never publish "pasture raised", "GMO free",
  "biodynamic" or similar. `core/tests/test_claim_discipline.py` will fail the build.
- **Membership is not certification.** Any member list must say so. The OPP requires it.
- **Never trust a PRD's own status.** Verify against git and the working tree.
- **Offline-first applies to the assessor PWA only** — not the portal or the chatbot.
