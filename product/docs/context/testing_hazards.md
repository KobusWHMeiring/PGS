# Testing Hazards & Verification Lessons

**Status:** Living document — append as you learn.
**Owner:** whoever is building.
**Why this exists:** every entry below cost real time to find, and each one is a
**silent** failure — a green test that proves nothing, or a tool that reports success
while enforcing nothing. The codebase has comments at each site, and the commit
messages carry the full reasoning, but both are unfindable when you are stuck at
midnight. This file is the index.

**How to use it:** read §1 before writing a test. Skim §2 when a tool says "OK" and
you do not believe it. §3 is about this machine, not the code. Add an entry the
moment you lose more than a few minutes to something that will happen again — with
the **evidence**, not the theory.

**Rule for entries:** state the trap, the evidence that it is real, and the rule that
follows. An entry without evidence is a rumour and will be deleted.

---

## 0. The one that generalises

> **A test that passes for the wrong reason is worse than no test**, because it
> removes the reason to look.

Every entry in §1 is a specific instance. The general defence, used throughout
A1–A7, is **mutation testing**: deliberately break the thing the test claims to
guard, confirm the test fails, then restore. If reverting the fix does not fail a
test, that test is decoration.

Two worked examples from this build:

- A6's registry test passed while a real Celery worker had an **empty** registry.
  Reverting the production fix failed **no** tests. After the fix it fails **two**.
- A7's config test would have passed against a config that enforced nothing, because
  `lint-imports` exits 0 whether the contract is kept or absent.

---

## 1. A test can pass for the wrong reason

### 1.1 Django mutates settings under test

Django appends `testserver` to `ALLOWED_HOSTS` for the duration of a test run.

```python
# Inside pytest:
settings.ALLOWED_HOSTS  ->  ['localhost', '127.0.0.1', 'testserver']
# Outside:
settings.ALLOWED_HOSTS  ->  ['localhost', '127.0.0.1']
```

**Consequence:** `assert settings.ALLOWED_HOSTS` is truthy even when the configured
list is empty. Such a test passes no matter how wrong the settings are — and it did,
during A2, against a stock `ALLOWED_HOSTS = []`.

**Rule:** assert on the *parser* (`env_list(...)`), and compare
`[h for h in settings.ALLOWED_HOSTS if h != "testserver"]`.

### 1.2 pytest-django prefixes the test database name

```python
settings.DATABASES["default"]["NAME"]  ->  'test_pgs'   # not 'pgs'
```

**Consequence:** `MVP0_PLAN_V2.md` A2's own assertion
`assert settings.DATABASES["default"]["NAME"] == "pgs"` **can never pass**. It was
written against a plan, not against a run.

**Rule:** compare `.removeprefix("test_")`, and pin the configured URL separately.
Same class of trap as 1.1 — the runner changes the value under test.

### 1.3 Patching the function under test proves nothing

A5's first tests monkeypatched `_redis_ping` itself, which **bypasses its own
`except` block** — so it raised instead of returning `"error"`.

**Rule:** patch at the *boundary* the code calls (`redis.from_url`,
`connection.cursor`), never the code being tested. If you replace it, you have not
tested it.

### 1.4 Importing the module under test can mask the bug

A6's meta-test imported `core.tests.test_tasks`, which imported
`core.tasks._maintenance` as a side effect — so the task registry *looked* populated
even when importing `pgs.celery` alone registered **nothing**.

```python
# Real worker (imports only pgs.celery):  tasks -> []
# Test (imports the test module first):   tasks -> ['core.tasks.heartbeat']
```

**Rule:** a probe of module-loading behaviour must run in a **fresh interpreter**
that imports only what a real process would. Import the *rule*, not the test module.

### 1.5 Celery's registry is not what you think

Two separate traps, both measured on Celery 5.6:

```python
@shared_task
def naked(): pass

hasattr(naked_task, "autoretry_for")  ->  False   # not an attribute AT ALL
naked_task.max_retries                ->  3       # Celery's silent default
naked_task.default_retry_delay        ->  180     # Celery's silent default
```

**Consequence 1:** `MVP0_PLAN_V2.md` A6's meta-test
`assert task.autoretry_for is not None` raises `AttributeError` on the exact task it
exists to catch. The traceback points at Celery internals, not the missing argument.

**Consequence 2:** `app.finalize()` does **not** flush autodiscovery. Discovery is
deferred into `_pending_tasks` and flushed by `loader.import_default_modules()` —
which is what a `WorkController` calls after `django.setup()`. Probing with
`finalize()` alone returns `[]` for a healthy project, i.e. a misleading red, and a
test written that way can be "fixed" into a misleading green.

**Rule:** a task in `core/tasks/_maintenance.py` is invisible unless
`core/tasks/__init__.py` imports it — `autodiscover_tasks()` imports the app's
`tasks` *package* and nothing deeper. Same pattern as `core/models/__init__.py`.
Probe with `import_default_modules()`.

### 1.6 An empty parametrize list passes vacuously

`test_claim_discipline.py` (Task C4) is parametrised over `PUBLIC_URLS`. Building it
before the views exist would mean an empty list — a test that runs zero cases and
reports success.

**Rule:** a parametrised test needs `assert PUBLIC_URLS` (non-empty) as its first
line. Defer the test until its data exists rather than shipping a no-op.

### 1.7 `blank=False` is not a database constraint

```python
User(username="").save()      # succeeds — Postgres stores ""
User(username="").full_clean() # raises ValidationError
```

`unique=True` only forbids a *second* empty string. A3's first test asserted
`IntegrityError` and failed.

**Rule:** know whether you are asserting validation or integrity. Test `full_clean()`
for the former, `IntegrityError` for the latter.

---

## 2. A tool can report success while doing nothing

### 2.1 Import Linter reads `.importlinter` as **INI**, not TOML

`MVP0_PLAN_V2.md` A7 shows TOML (`[[importlinter.contracts]]`) in a file named
`.importlinter`. Import Linter's INI reader claims `setup.cfg` and `.importlinter`;
only `pyproject.toml` gets the TOML reader. Parsed as INI, the TOML snippet has no
`[importlinter]` section.

**Evidence:**

```
$ lint-imports          # with the plan's config verbatim
Contracts: 0 kept, 0 broken.
exit=0
```

It exits **0** and enforces **nothing** — and a test that only checks the exit code
passes. A7's config test now parses the file and asserts the fields, which is the
only check that catches an inert config.

**Also:** `root_package = pgs` fails with `Module 'knowledge' does not exist`,
because module names resolve relative to it and `core`/`knowledge` are **siblings** at
the repo root. Use `root_packages` (plural). Multi-value keys are
**newline**-separated; the INI reader does not split on commas.

### 2.2 Grimp caches its module graph

`lint-imports` writes `.import_linter_cache/`. During A7 a cached module list briefly
outlived a deleted file and reported `BROKEN` for a violation that no longer existed.

**Rule:** run `lint-imports --no-cache`. A flaky architecture test gets disabled, so
the speed is not worth it. (I first misdiagnosed this as caching when it was
batched-write filesystem lag — see 3.3. The `--no-cache` remains correct either way.)

### 2.3 A health check that only pings the broker cannot see a dead worker

Redis answers `PING` with zero workers consuming. A5 therefore checks
`celery_broker` and `celery_worker` **separately**; the latter uses
`control.ping()`, which returns `[]` when nothing responds.

**Evidence (live, not mocked):** with no worker, `/health/` returns **503** with
`celery_broker: ok, celery_worker: error`. A broker-only check would have said
healthy while every queued task sat undrained.

**Related:** a worker with an **empty registry** still answers pings, so
`celery_worker: ok` does not mean tasks will run — see 1.5.

---

## 3. This machine (Windows, Docker Desktop)

Not code bugs, but they cost time and they will recur.

### 3.1 Docker binds 5432 alongside a native PostgreSQL service

A native `postgresql-x64-17` service owns `0.0.0.0:5432`; Docker binds the same port
alongside it rather than failing to start. A native `localhost:5432` connection
therefore reaches the **native** server and fails with

```
FATAL: password authentication failed for user "pgs"
```

— an error that points nowhere near the cause.

**Rule:** the Compose Postgres is published on **5433**. CI has no competing service,
so A8 uses 5432 internally. Do not "correct" this back.

### 3.2 A stray `inspect.py` in the working directory shadows the stdlib

Documented in `HANDOVER.md` §7, and it **saved time during A1** — I hit it and
recognised it immediately. `packaging` fails with
`module 'inspect' has no attribute 'iscoroutinefunction'`.

**Rule:** run throwaway scripts from a clean directory (`_scratch/` inside the repo,
never `%TEMP%`, which has accumulated junk).

### 3.3 Batched write-then-run gives a stale filesystem view

Writing a file and immediately running a subprocess that reads it can observe the
**previous** state on this box. During A7 this produced four consecutive bogus
`exit=1` results and sent me chasing a cache bug that did not exist.

**Rule:** after writing a probe, `assert path.exists()` and re-run to confirm
determinism before believing a single result. Do not batch write-and-verify.

### 3.4 Process cleanup is unreliable

- `wmic process get CommandLine` did **not** list a running Celery worker.
- A lingering handle made a scratch directory undeletable; had to kill by PID twice.
- A stale pre-fix worker on broker DB 1 answered a task and produced a misleading
  `NotRegistered`; a `DuplicateNodenameWarning` was the only clue.

**Rule:** when verifying anything Celery-related, **isolate onto separate Redis DBs**
(`CELERY_BROKER_URL=redis://localhost:6379/5`) so a stale worker cannot pollute the
result. Kill by PID from `netstat -ano`, not by image name.

### 3.5 Do not pipe a migration into `head`

`manage.py migrate | head -6` sends SIGPIPE, killing the migration **midway** and
leaving a partial database that then reports `migrate --check` exit 1.

**Rule:** never pipe a schema-changing command into anything that can close early.

---

## 4. Domain hazards already in `HANDOVER.md` §6

Not duplicated here — read that section. It covers the polarity trap (R1a-2), the
SAOSO/OPP section-format realities, `GeneratedField(SearchVector(...))`,
`OVERDUE` derivation, `except: pass`, hand-written fixtures (the parser that matched
zero lines of the real PDF), markdown-escaped HTML, dead Tailwind classes, and the
non-public WordPress media API.

**The two that apply to every task below:** *run the thing before you believe it*, and
*fixtures must be verbatim extracts from `pgs_docs/`*.

---

## 5. Template for a new entry

```markdown
### N.M Short name of the trap

What the code or tool appears to do, and what it actually does.

Evidence:
    <command + actual output, not a paraphrase>

Consequence: what silently goes wrong if you do not know this.

Rule: the specific thing to do instead.
```
