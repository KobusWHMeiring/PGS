# Test-cost playbook — principles and tooling that generalise across our repos

**Status:** Proposal. Nothing here is implemented in `ngo-finance`, `homitini`,
`homtini_store` or `harvester` — this document is the design, and it was written only after
measuring all five repos.
**Companion:** `product/docs/context/TESTING_TIME_PLAN.md` (the pgs-specific plan this grew out of).
**Date:** 2026-10-28

---

## 1. Why this exists

Five Django repos, five test suites, the same complaint. Session-log analysis of
`~/.pi/agent/sessions/*` (every pytest summary line ever printed, 2026-10-18 → 2026-10-28):

| repo | test files | test LOC | pytest runs | **hours in pytest** | runs ≥500 tests |
|---|---|---|---|---|---|
| homitini | 285 | 68 333 | 2 759 | **29.0 h** | 24 |
| pgs | 65 | 16 758 | 831 | **8.3 h** | 132 |
| harvester | 93 | 20 842 | 612 | **6.5 h** | **0** |
| ngo-finance | 88 | 14 240 | 617 | **4.0 h** | 22 |
| homtini_store | 55 | 14 439 | 397 | **0.8 h** | 44 |

49 h of waiting, and **the shapes are different**:

* **pgs is gate-bound** — 4.5 h of its 8.3 h is 132 near-full runs.
* **homitini and harvester are loop-bound** — 93 % / 100 % of their time is scoped runs,
  because a full run is either too slow or broken.
* **homtini_store is fine** — 7.6 s per run. It is the control group, and the proof that this
  is not "Django suites are slow".

So the prescription cannot be one set of flags. It has to be a *diagnosis* first.

---

## 2. The five laws

Each one is stated so it can be tested on a repo in minutes, and each has the measurement that
falsifies it recorded below.

### Law 1 — Total cost = invocations × floor, and the floor is what you think is the test

A pytest invocation costs `interpreter start + collection + Django/DB setup` **before the first
assertion runs**. That floor is paid by every run, including the 545 single-file runs.

Measured floors on this box (walls, warm):

| repo | `pytest --co` (whole suite) | one node |
|---|---|---|
| pgs | 0.9 s (3 s wall) | 2.9 s |
| ngo-finance | 1.1 s (3 s wall) | ~3 s |
| homitini | **14.0 s (18 s wall)** | 2.1 s |
| harvester | collection **errors** | 4.4 s |

`homitini`'s 2 759 runs × 18 s of collection alone is ~13.8 h — half its measured cost, before a
single test runs. **Collection is proportional to imports, not to test count**; a repo can have
4 312 tests and a 2 s scoped floor.

### Law 2 — Per-test fixed costs are multiplicative, and password hashing is the tax nobody sees

`create_user(password=…)` runs PBKDF2 at production iterations: **~0.5 s per hash**, and each
`force_login`/`login` hashes again. It is invisible in the code review because it looks like
setup, and invisible in the coverage report because it is not code under test.

Static count vs measured session cost:

| repo | `create_user(…password=…)` sites | test hasher override | hours in pytest |
|---|---|---|---|
| homitini | **215** | **none** | **29.0 h** |
| ngo-finance | 62 | fast PBKDF2 (documented in `conftest.py`) | 4.0 h |
| harvester | 17 | MD5 in `core/tests/test_settings.py` | 6.5 h |
| pgs | 4 | none | 8.3 h |
| homtini_store | 3 | none | 0.8 h |

**A/B on homitini, alternated, warm, two reps** (`tests/core/test_cashbook.py` +
`tests/core/test_audit_trail.py`, 41 tests):

```
baseline  99.91s → 73.73s      # 2.4 s of hashing per test
MD5        7.72s →  3.00s      # same 41 tests, same assertions
```

10–25× on an auth-heavy subset. `ngo-finance` and `harvester` already fixed this — and their
`create_user` counts drop by an order of magnitude with it. **This is the first thing to check in
any repo, and it is a 10-second grep.**

### Law 3 — Cold is 4–6× warm, so a single timing is not a measurement

pgs, same tree, same command, one day:

```
253 s → 213 s → 174 s → 93 s → 66 s → 48 s → 42 s
```

Two consequences. (a) Any duration in a handover or a plan must state cold *and* warm, or the
number means nothing. (b) Optimising a cold run is mostly optimising Windows file cache and
Defender; optimising the *number of runs* is the lever that survives.

My own first A/B in this investigation was wrong by 4× because the first arm was cold. **Every
claim in this playbook was measured twice, alternated, after warm-up.**

### Law 4 — The slow tests are few, visible, and not where the time is

Warm pgs profile (1 140 cases, 41.2 s): median **6 ms**, p90 **76 ms**, p99 **470 ms**,
max 1.9 s. 97.3 % of tests are under 0.2 s. Deleting every test over 1 s saves 23 % of one run
and nothing at all across a session.

Corollary: **pruning tests is the last lever, not the first.** Fixed costs and invocation count
come first, by a factor of ten.

### Law 5 — Coverage overlap is not claim overlap

pgs, per-test coverage contexts: 422 lines are executed by exactly one test, 2 091 (62 %) by
twelve or more. 743 tests are the sole witness of no line — and between them assert 743 distinct
properties. `test_ingest`'s 49 tests each walk 400–600 lines of the same pipeline and assert 49
different things.

So: **coverage answers "did this line run", mutation answers "is this assertion load-bearing",
and neither answers "is this claim still true".** Use coverage to find where claims cluster and
to prove a prune orphaned nothing; use mutation to decide if a test earns its keep; use the
hazard registry (Law 6) to decide whether a claim may be dropped at all.

### Law 6 — The hazard registry *is* the definition of coverage

Every repo here already has one, under a different name: `product/docs/context/testing_hazards.md`
(pgs), `LEARNINGS.md` §67 (homitini), the numbered notes in harvester's `docs/`. Those entries
are the only record of *why* a test exists — and "80 % coverage" measured in lines has no
relationship to them.

A test whose hazard entry is gone gets deleted by the next agent; a test whose hazard is cited
can be defended in one line. Where a repo has no registry, it can be mined:
`git log --diff-filter=A --name-only -- '*test_*'` crossed with the fix commits that added them.

---

## 3. The ten-minute triage (portable protocol)

Run this before proposing any change, in any repo. Five measurements, five decisions.

| # | Measurement | Command | Decision it drives |
|---|---|---|---|
| 1 | **The tax** | `grep -rn "create_user(" --include="*.py" . \| grep -c password=` + `grep -rn PASSWORD_HASHERS` | If ≥10 sites and no override → fix the hasher first. Expect 5–20×. |
| 2 | **The floor** | `time pytest --co -q` and `time pytest <one node> -q` | If collection > 3 s → attack imports before anything else (Law 1). |
| 3 | **The shape** | count runs and hours from the session logs (script provided) | gate-bound (like pgs) → lane split; loop-bound (like homitini) → floor + fixed costs. |
| 4 | **The profile** | one warm run with `--junitxml` | median/p90, `% tests >1 s`, top modules. Confirms Law 4. |
| 5 | **The witnesses** | one run with `--cov --cov-context=test` | sole-witness lines, shared-line histogram, zero-unique tests. Builds the review queue. |

Then, and only then, the prescription — in this order, because the effect sizes are ordered:

1. **Remove per-test fixed costs** (hasher, subprocess boots, `--create-db` in the loop).
2. **Cut invocations** (fast lane + `--ff -x` + a rule that the gate runs once).
3. **Consolidate fixtures** (module-scoped corpus/DB setup where each test re-runs a pipeline).
4. **Prune or merge tests** (three-condition kill rule, §5).

---

## 4. The shared tooling: `testcost.py`

One file, stdlib + optional `coverage`, no Django imports, no repo-specific paths. Copied (or
vendored as `scripts/testcost.py`) into each repo. Deliberately *not* a pytest plugin: it must be
runnable against a repo whose suite does not collect.

```
python scripts/testcost.py floor      # laws 1–2: collection, one-node, hasher sites, subprocess sites
python scripts/testcost.py config     # cheap-win audit: reuse-db, lanes, markers, e2e in testpaths
python scripts/testcost.py profile    # law 4: warm run, JUnit profile, lane candidate list
python scripts/testcost.py inventory  # law 5: coverage contexts → sole witnesses, shared lines
python scripts/testcost.py report     # writes the markdown block into the repo's own doc
```

Design constraints, each learned the hard way here:

* **`floor` and `config` must never run the suite.** A repo whose bare `pytest` errors (harvester,
  today: three collection errors and therefore *zero* full runs in 612 invocations) still needs
  a diagnostic.
* **`profile` runs twice and reports the second**, and prints cold and warm side by side. A tool
  that reports one run teaches the reader to trust noise (Law 3).
* **`inventory` takes a coverage data file**, not a coverage run, so it can be produced in CI
  once and analysed anywhere. It prints *diagnostics*, never a delete list — the words
  "redundant" and "unnecessary" must not appear in its output (Law 5).
* **`report` writes into the repo's own hazards/learnings document**, not a central dashboard:
  the number has to sit next to the reason those tests exist.
* Exit codes: `floor`/`config` exit 0 always (they are advisory). A CI gate uses **one** number
  from `profile` (warm full-suite seconds) against a constant stored in the repo — a budget in
  prose is not a budget (pgs `testing_hazards.md` §2.7).

Reference implementation already prototyped during this investigation (in pgs `_scratch/`):
`profile_tests.py` (JUnit → per-module, percentiles, lane split), `redundancy3.py` (coverage
contexts → sole witnesses), `all_repos_cost.py` (session logs → per-repo runs/hours/shape).

---

## 5. The shared contract every repo should carry

Five artefacts, identical in intent, named per repo conventions:

1. **`pytest.ini` declares its lanes.** Markers `slow` and `e2e` defined and *used*; `testpaths`
   set (a test outside `testpaths` is a test nobody runs — pgs §2.6); e2e out of the default run.
2. **A fast lane and a gate**, as two named commands (`scripts/fast.sh` / `scripts/verify.sh`,
   `make test` / `make test-all`). The loop targets **< 20 s**; the gate targets a stated number
   and is run once per commit. harvester is the model here — its Makefile even records that xdist
   was measured and rejected.
3. **A recorded budget**, asserted by a test, in the repo, with the slowest three tests printed
   on failure.
4. **A hazard registry** (Law 6) with, for each entry, the test that would catch its regression.
5. **A regenerable inventory** (`testcost.py inventory` output committed) so pruning decisions
   are reviewable in a diff.

### The kill rule (identical in every repo)

A test may be deleted or merged only when **all three** hold:

* **same claim, lower layer** — the invariant map shows an equivalent assertion at the same or a
  cheaper layer, and the survivor cites the hazard;
* **no orphan line** — nothing it uniquely executed becomes unexecuted (prove with
  `--cov-context=test` before/after);
* **no surviving mutant** — mutation score of the module is unchanged by its removal.

Merge before you delete: 49 ingest claims over one corpus become 12 tests over one ingested
corpus. Same claims, fewer pipeline runs.

---

## 6. What does **not** generalise

Each of these is a pgs-specific answer that would be wrong to copy:

* **`--create-db` in the gate.** Cheap in pgs (~1.2 s of migrations). Do not assume it: a repo
  with a large migration history pays 30–60 s and should gate it weekly, not per commit.
* **pytest-xdist.** harvester measured it and found no speedup (single local Postgres is the
  bottleneck, recorded in its Makefile). Parallelism helps import-bound and CPU-bound suites; it
  does not help DB-bound ones, and it can multiply DB setup costs.
* **`--reuse-db`.** Already in harvester and homitini; it is the right default *only* once a
  stale `test_` database cannot wedge the gate (pgs hit
  `database "test_pgs_verify" is being accessed by other users` twice during this investigation).
* **Deleting the many cheap tests.** Warm median is 6 ms. It saves nothing and costs claims.
* **Copying pgs's `slow`-marker list.** Mark by measured cost in that repo, not by module name.

---

## 7. Rollout, in the order the measurements justify

| repo | diagnosis | first move | expected effect |
|---|---|---|---|
| **homitini** | 215 `create_user(password=)` sites, no hasher override; 29 h — the worst in the fleet | fast test hasher (and a test proving `pgs`-style: production settings unchanged) | 41-test subset measured **10–25× faster**; full-suite effect must be re-measured after |
| **harvester** | zero full runs ever; bare `pytest` has 3 collection errors | make bare `pytest` collect; then a single gate command | a gate that exists is worth more than any micro-optimisation |
| **pgs** | gate-bound: 4.5 h of 8.3 h is near-full runs; hasher tax 12–15 s/run | `TESTING_TIME_PLAN.md` stages 0–2 | 42 s → ~30 s warm; gate runs once per commit |
| **ngo-finance** | hasher already fixed and documented; 4.0 h, 22 full runs | `floor`/`profile` to find its actual floor; likely fixture scoping | unknown until measured — do not guess |
| **homtini_store** | 7.6 s/run, 0.8 h total | leave it alone; use it as the control | — |

Cross-repo rule of thumb from the five: **a healthy loop is ≤ 20 s, a healthy gate ≤ 2 min, and a
session should contain ≤ 10 gate runs.** pgs currently runs 132 near-full runs in ~32 sessions —
4 per session, each paying the cold penalty. homitini runs 2 759 scoped runs — 86 per session,
which is not a testing strategy, it is a reflex.

---

## 8. Two meta-lessons worth writing down on their own

1. **The instrument and the product must be measured together.** In pgs, the probe hardcoded a
   retrieval budget the product did not read (§2.7). Here: the same failure shape appeared in the
   *benchmark* — my first A/B put a 4× cold-cache effect inside the "hasher fix". A benchmark is
   an instrument; it needs the same scepticism as production code.
2. **A tool that reports a number will be trusted.** So `testcost.py` must print warmth, reps and
   the scope it measured on every line — otherwise the next agent will quote a cold 253 s as
   "the suite takes four minutes" and optimise the wrong thing, which is exactly the state this
   investigation started from.
