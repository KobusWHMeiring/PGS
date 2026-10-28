# Testing time & test value — measured, staged plan

**Status:** Proposal — nothing in here is implemented yet except the two fixes noted in §8.
**Date:** 2026-10-28
**Evidence base:** 819 pytest invocations recovered from the pi session logs
(`~/.pi/agent/sessions/*pgs*`, 2026-10-18 → 2026-10-28), one instrumented coverage run of the
whole suite on the current tree, and one warm per-test profile (JUnit timings).

---

## 0. The four numbers that decide the plan

| # | Measurement | Value |
|---|---|---|
| 1 | pytest wall time consumed across 32 sessions | **8.1 h** (819 invocations) |
| 2 | of that, the 128 *near-full* runs (≥500 tests) | **4.5 h — 56 %** |
| 3 | warm full suite (1139 tests) on the current tree | **42.6 s** wall, 41.2 s in tests |
| 4 | the *same* tree, measured earlier the same day | **253 s** — the 6× cold-cache penalty |

The suite is not slow. **Running the whole suite, repeatedly, is what is slow** — and the first
runs of a session pay 4–6× the warm cost because of OS file-cache/AV state on this box.

---

## 1. Method, and why you must not trust a single timing

The same tree, same command, same day:

```
253.58s   1138 passed   (first run, cold disk/AV)
213.52s   1138 passed
174.30s   1138 passed   (fast password hasher, --create-db)
 93.62s   1139 passed   (coverage instrumentation, --reuse-db)
 66.81s   1139 passed
 48.00s   1139 passed
 42.64s   1139 passed   (warm, fast hasher, --reuse-db)
```

Two consequences, both load-bearing for the plan:

1. **Every earlier number in `HANDOVER.md` / `testing_hazards.md` about suite duration is a
   cold number.** Any budget we set must be stated cold *and* warm, or the gate will be
   "optimised" while nothing changes for the person waiting.
2. **A benchmark that is not repeated is not a benchmark.** A first A/B (37 tests: 65 s → 12 s
   with a fast password hasher) overstated that fix 4×: measured warm and repeated it is
   18–21 s → 5.7–6.5 s. The cold-cache penalty was inside the treatment.

Measurement protocol used below, and proposed for the repo:
`--reuse-db`, run twice, report the second; report the test-time sum from JUnit separately from
wall time, so a slow interpreter start cannot hide in a test's duration.

---

## 2. Where the time goes

### 2.1 Across a session — invocation count, not test duration

| run size | runs | time | share |
|---|---|---|---|
| 1–49 tests (targeted loops) | 545 | 1.7 h | 21 % |
| 50–499 | 146 | 2.0 h | 24 % |
| 500–999 | 90 | 2.9 h | 35 % |
| 1000+ | 38 | 1.6 h | 19 % |

128 runs of ≥500 tests cost 4.5 h. A warm full run is 42 s; the same run in a session averages
~2 min. The single largest lever is therefore **how often the full suite is run**, and second
**how much of the loop each targeted run re-collects** (≈4.4 s of interpreter + Django + collection
per invocation, measured: `pytest --co` = 4.9 s inside a 9.3 s process).

### 2.2 Within a run — warm per-test profile (1140 cases, 41.2 s)

```
knowledge.tests.test_ingest           6.6s   (49 tests)
core.tests.test_uat_console           5.5s   (13)
core.tests.test_tasks                 5.1s   (16)
core.tests.test_claim_discipline      3.6s   (46)
knowledge.tests.test_retrieval        2.2s   (41)
…
median 0.006s   p90 0.076s   p99 0.470s   max 1.94s
97.3 % of tests take <0.2 s and account for 57 % of test time
0.7 % of tests take >1 s   and account for 23.5 % of test time
```

Warm, the distribution is **flat**: there is no small set of pathological tests to kill. The time
is 1140 × ~36 ms of transaction/fixture work plus four modules that do real work per test.

### 2.3 Fixed costs, each measured in isolation

| cost | measured | notes |
|---|---|---|
| password hashing (default PBKDF2) | **18–21 s → 5.7 s** on 37 auth-heavy tests; **59–63 s → 44–50 s** full suite | two reps each, warm. Every `create_user(password=…)` in a fixture pays it; `test_uat_console` creates two users per test. |
| `--create-db` (schema rebuild) | ~1.2 s on 2 tests | **not** the 80 s the first comparison suggested — that was cache warmth. Migrations are cheap here; keep `--create-db` in the gate. |
| subprocess Python boot | ~1.1 s each | `test_tasks` boots 5 interpreters (~5.1 s), `test_uat_console` runs management commands as subprocesses. |
| `tests/e2e` (outside the gate) | 78.7 s for 43 passed + 34 errors | see §8.2. |

---

## 3. Where the value goes — is 1139 tests earning its keep?

Instrumented run: `--cov --cov-context=test` (branch coverage, `core` + `knowledge` + `pgs`).

**Baseline: 94.2 % statement+branch coverage.** 3894 statements, 1032 branches.

Per line executed, how many *different tests* execute it:

| witnesses | lines |
|---|---|
| exactly 1 test | 422 |
| 2–4 tests | 449 |
| 5–11 tests | 399 |
| 12+ tests | 2091 (62 %) |

Per test, how many lines it is the **sole** witness of (844 tests have a coverage context at
all):

* **743 tests are the sole witness of no line**, but between them execute 89 632 lines.
* **296 tests execute no project Python line at all** — they assert on *artefacts and data*:
  subprocess output (`test_tasks`, `test_architecture`, `tests/tools/*`), committed corpus
  fixtures, the HTML the UAT runner generates. Coverage cannot judge these; that is by design
  (`testing_hazards.md` §1.30 — a self-contained page passed 17 grep-based checks while its
  script did not parse).
* 828 test functions (1139 collected cases); 538 of the functions contain ≤2 assertions;
  11 contain none (they call a helper that asserts).

**The honest reading:** code-path overlap is *not* claim overlap. `test_ingest`'s 49 tests each
re-execute 400–600 lines of the same pipeline and assert 49 different properties of the result.
Deleting 40 of them would remove 40 claims while changing coverage by almost nothing. Coverage
*overlap* is a **review queue**, not a delete list; the instrument that answers "is this test
load-bearing for its own claim" is mutation testing, which we have not run yet.

What we can say without mutation testing:

* 422 lines are guarded by exactly one test — that set is the *irreplaceable* core, and every
  one of the 743 zero-unique tests may still own a claim the core does not make.
* 62 % of exercised lines are witnessed by 12+ tests. Any *new* test over those lines adds
  nothing unless it asserts a **new claim**.

---

## 4. The principles at play

This is the part of the question that decides what we are allowed to delete. Nine rules; the
first six are the general ones, the last three are this repo's own and are non-negotiable.

1. **Cost per signal.** A test should be the cheapest instrument that can fail for the reason it
   names. If a template assertion can be a service assertion, it should be — but see 2.
2. **Layer of last resort.** Assert at the lowest layer that can actually detect the defect.
   Browser-only facts: ≥44×44 px on both axes, a grid child count, a `:target` line landing
   under sticky chrome (`testing_hazards.md` §3.11–3.13). Everything else is cheap upstairs.
3. **Risk-weighted, not count-weighted.** Protect the 4.7 % of tests that carry the build's
   truth claims (`test_claim_discipline.py` alone is a build breaker) before touching the 88 %
   that cost 20 % of the time. Time savings live in the head; value lives in the tail.
4. **Coverage measures execution, not assertion.** Use it to find *where claims cluster*, and to
   prove a prune did not orphan a line. Use mutation testing to decide whether a test earns its
   keep. Two questions, two instruments (`testing_hazards.md` §1.29).
5. **One primary witness per invariant** — plus a mechanism test at each boundary where two
   writers must agree (`testing_hazards.md` §1.32: a join asserted with a literal on both sides
   agrees with itself and proves nothing).
6. **Two budgets, two commands.** The dev loop is a *feedback* decision (target <20 s, run it
   after every edit). The gate is a *release* decision (≤2 min, run once per commit). One
   command cannot serve both; today `scripts/verify.sh` serves only the second, so the loop
   borrows it.
7. **Determinism before measurement.** Cold vs warm is 6×. A performance claim without a stated
   warmth and a repeat is decoration — the same class as §2.1/§2.5's "the tool ran and enforced
   nothing".
8. **A guard is deletable only if its reason survives it.** Every test here exists because a
   recorded hazard happened. Deleting the second witness is fine; deleting the *last* test that
   cites a hazard is how `testing_hazards.md` becomes archaeology.
9. **Diminishing returns, stated as a rule.** The marginal test must add a **failure mode**, not
   a line. If 12 other tests already execute the line and none of them asserts the property,
   write the assertion — do not write a 13th walk through the same code.

---

## 5. The plan

Four stages, in order. Each has a measured acceptance criterion; none removes an assertion
except Stage 3, which has an explicit kill rule.

### Stage 0 — Make the loop measurable (½ day)

1. `scripts/bench.sh`: runs the suite twice with `--reuse-db`, prints cold, warm, and the JUnit
   test-time sum, and writes the numbers to a log file. No performance claim is accepted
   without a line in that log.
2. `scripts/verify.sh` keeps `--create-db` (proven cheap: ~1.2 s) and adds `--durations=15` so
   drift is visible on every gate run.
3. Add a `slow` marker to `pytest.ini`; `--strict-markers` is already on, so an unregistered
   marker fails loudly.

**Accept:** `bash scripts/bench.sh` prints two numbers and they are within 15 % of each other.

### Stage 1 — Delete fixed costs (no assertion changes) — target 42 s → ~30 s warm

| change | expected saving | why it is safe |
|---|---|---|
| `PASSWORD_HASHERS = [MD5…]` in a test-settings module (`pgs/settings_test.py`) referenced by `pytest.ini` | 12–15 s | measured twice; nothing in the repo asserts on hasher/output format (grepped: 0 hits for `PASSWORD_HASHERS\|pbkdf2\|make_password\|check_password`). Guard: a test asserts `identify_hasher` is not PBKDF2 *and* that `pgs/settings.py` declares no weak hasher, so the override cannot leak to a deployment. |
| `test_tasks`: one subprocess emitting a JSON report, five assertions over it | ~4 s | the tests already assert with `json.loads`; only the interpreter count changes |
| `test_uat_console`: one subprocess per *behaviour class*, not per test | ~2 s | same |
| `test_ingest`: module-scoped ingested corpus (`django_db_blocker` + `scope="module"`); keep **one** cold end-to-end ingest as the canary | ~4 s | keeps one test proving the real pipeline; the rest assert properties of its output. Must be verified with `--create-db` in the same run, so the fixture cannot hide a schema dependency. |

**Accept:** warm full suite ≤ 32 s and 1139 tests still collected and green; mutation score of
the unchanged code does not drop (Stage 3 gives the baseline).

### Stage 2 — Split the lanes (the 4.5 h lever)

1. `scripts/fast.sh` → `pytest -q -m "not slow" --reuse-db -x --ff` (last-failed first, stop at
   the first failure). Target: **< 20 s warm**.
2. Mark `slow` the 8 tests >1 s plus the modules that spawn subprocesses or drive
   `live_server`. Do not mark by module size — mark by measured cost.
3. Write the rule into `AGENTS.md`: the loop is `scripts/fast.sh`; the gate is
   `scripts/verify.sh`, once, before commit and always before deploy.
4. Keep `tests/e2e` out of both, exactly as today.

**Accept:** the loop is <20 s warm, catches a deliberately broken test (prove it can fail), and
`scripts/verify.sh` is unchanged in coverage.

### Stage 3 — The value audit (1–2 days)

1. Commit `scripts/test_inventory.py` (the throwaway prototype already exists in `_scratch/`):
   per-test sole-witness lines, shared-line counts, and the "no project line" list; output to
   `product/docs/context/test_inventory.md`, regenerated on demand.
2. Build the **invariant map** by hand, once: invariant → every test that asserts it → which one
   is the primary witness. Start with the ten that matter: no unsupported claims; membership ≠
   certification; noindex on unpublished; audit refusals; cache-only-after-audit; ingest
   idempotency on sha256; printed furniture never in chunks; retrieval budget agreement;
   knowledge ↛ core; 44 px. The first pass of this map was auto-generated and is too coarse to
   act on (a regex for "audit|grounded" matches 133 tests across 28 files) — the map must be
   hand-written per invariant, because the *claim* is what is being deduplicated.
3. Pilot mutation testing (`mutmut`, `cosmic-ray`, or a hand-rolled AST mutator) on two modules:
   `knowledge/retrieval.py` and `core/services/_chatbot*.py`. Record the killed/total score. A
   test that kills no mutant, asserts a property another test asserts, and owns no sole-witness
   line is a candidate.
4. **Kill rule — all three must hold before a test is deleted or merged:**
   * a-second-test-asserts-it: the invariant map shows an equivalent assertion at the same or a
     lower layer, and the survivor's docstring cites the hazard;
   * no-orphan-line: no line it uniquely executed becomes unexecuted (prove with
     `--cov-context=test` before/after);
   * no-surviving-mutant: mutation score of the module is unchanged by its removal (or the
     module is out of the pilot and the deletion is deferred).
5. **Merge, don't delete, where the claim is real.** `test_ingest`'s 49 claims become ~12 tests
   over one ingested corpus; `test_claim_discipline`'s 46 page-level scans become one
   parametrised scan over the public route list. Same claims, fewer pipeline runs.

**Accept:** invariant map covers the ten invariants with a named primary witness each; statement
+branch coverage **≥ 94 %** (baseline) and *zero new orphan lines*; mutation score on the two
pilot modules not lower than before.

### Stage 4 — Keep it (ratchet)

1. A single budget constant, asserted in `tests/tools/test_verify_gate.py`: if the warm gate
   exceeds it, the test fails with the measured number and the slowest three tests. A budget in
   prose is not a budget (§2.7: the setting that nothing reads).
2. Append to `testing_hazards.md`:
   * a cold vs warm run of the same tree differs 6× — quote warmth or the number is noise;
   * a corrupted source file (`scripts/uat_page.py`, §8.1) can sit in the tree while earlier runs
     are green — re-run collection after any in-place edit to a harness file.
3. Re-run `scripts/bench.sh` at each MVP milestone and record it; the number that matters is the
   *warm gate*, not the first run of the day.

---

## 6. What must not be cut, whatever the time pressure

* `core/tests/test_claim_discipline.py` — the only thing standing between the site and a
  "pasture raised" claim. It is build-breaking on purpose.
* The citation-audit and refusal tests (`test_chatbot_grounding`, `test_chatbot_guardrails`,
  `test_retrieval_scope`) — these encode "the product refuses rather than invents".
* Corpus invariants: glyphs/U+FFFD, printed footer, page attribution, ingest idempotency,
  de-column permutation.
* `core/tests/test_architecture.py` + `lint-imports` — the `knowledge ↛ core` contract.
* `core/tests/test_settings.py`, `test_health.py`, `test_tasks.py` — the three "a green run for
  the wrong reason" defences (hazards §2.1/§2.5/§2.7).
* `tests/tools/*` — they decide what a human signs.
* `tests/e2e` layout, target-size and anchor-landing tests — the three defects that shipped and
  that only a browser could see.

---

## 7. How we prove the 80 % claim

"Keep 80 % of our coverage" is only meaningful with a definition, so:

1. **Orphan lines = 0.** After every prune, the set of lines executed by *no* test must not grow.
   Measured mechanically from `--cov-context=test`, not argued.
2. **Line + branch coverage ≥ 94 %** (today's baseline) on `core`, `knowledge`, `pgs`.
3. **Mutation score per module does not fall** — the real test of whether an assertion was
   load-bearing. Pilot on the two modules above first; extend only if the tooling is bearable.
4. **Every hazard in `testing_hazards.md` still has a witness.** One row per hazard entry,
   naming the test that would catch a regression of it. That is the 20 % we are protecting.

---

## 8. Findings that are not about speed (found while measuring)

### 8.1 A broken source file was in the tree while full runs were still green

`scripts/uat_page.py:150` — an uncommitted edit had written `"\n".join(...)` as a **literal
newline inside the string** (`status = "` ⏎ `".join(`), so the module does not parse:

```
$ python -m pytest tests/tools/test_uat_runner.py
E   File "scripts\uat_page.py", line 150
E     status = "
E              ^
E   SyntaxError: unterminated string literal
```

It was repaired by hand (one escape: the intent of the surrounding docstring is unambiguous), and
the collection error disappeared. Two lessons: (a) it is the same class as
`testing_hazards.md` §1.27 — a write that mangles `\n` is not a rare event in this repo; (b) on
this box a batch of runs can be green and then a later run fails on a file nobody edited
between them — re-run collection after touching a harness file, and do not trust one green run
of a subset.

### 8.2 `pytest tests/e2e` is not green at HEAD

```
$ python -m pytest tests/e2e -q
43 passed, 34 errors in 78.74s
$ python -m pytest tests/e2e/test_public_site.py -q
37 passed in 65.02s
```

Each file passes alone; the whole suite errors at setup with
`django.db.backends.postgresql InterfaceError` while setting `autocommit` — a dropped
connection under `live_server` when several modules run in one session. This is
`testing_hazards.md` §3.11 again (a suite outside the gate drifts), and it means the 78 s the
e2e run costs currently buys 34 false alarms. Fix before the next deploy; it is a prerequisite
for the `--reuse-db` recommendation, since a stale connection is also what produced
`database "test_pgs_verify" is being accessed by other users` during this investigation.

### 8.3 Measurement tooling is not in `requirements.txt`

`pytest-cov` 7.1.0 was installed into `.venv` for this investigation only. Stage 0/3 need it
(or `coverage` directly) as a declared dev dependency, or the inventory script cannot run in CI.
