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

### 1.8 A near-identical identifier produces an unreadable error

Two of B7's tests asked for `saaso_ingested`. The fixture is `saoso_ingested` — one
letter different, in the middle of a word, in a file where both spellings surround it.
pytest's message is actively misleading:

```
E       fixture 'saaso_ingested' not found
>       available fixtures: ..., saaso_ingested, saoso_set, settings, ...
```

It **lists the fixture as available** — because `saoso_ingested` exists — while failing
to find the name that was asked for. Reading that twice, I concluded the test file was
stale, cleared `__pycache__` and `.pytest_cache`, renamed the fixture, rewrote the test
under a different name, and blamed this box's filesystem (3.3). All four were wrong;
the suite went green the moment the typo was fixed.

**Evidence that ends the argument in one command:**

```python
data = Path("knowledge/tests/test_retrieval.py").read_bytes()
data.count(b"saaso_ingested")   # 2   <- the typos
 data.count(b"saoso_ingested")  # 9   <- the real fixture and its users
```

**Rule:** when pytest says a fixture is missing but lists it, compare the two
identifiers **byte for byte** — a count of occurrences, not a visual diff — before
suspecting the runner, the cache or the filesystem. `saaso`/`saoso` are one letter apart
and both look right. The same applies to `sub_refs`/`subrefs`, `standard_set`/
`StandardSet`, and any other pair the domain forces on you.

**Corollary:** do not let a diagnostic become a rewrite. The three changes I made while
chasing this (clearing caches, renaming a fixture, rewriting a test) all had to be
undone, and one of them left the file in a state where the typo existed in a *second*
place — which is why the failure count grew from one to two and looked like progress
being undone.

### 1.9 A template comment that is not a comment rewrites the page

Django's `{# ... #}` comment is **single-line only**. A multi-line one is not a syntax
error: the whole block is emitted as ordinary text. That alone would be embarrassing —
but the real damage is that its contents are then parsed as HTML. One of C1's comments
contained the word `<details>` in prose, to explain why a `<details>` element was used.
The browser read that word as a start tag, nested everything after it inside a stray
disclosure widget, and swallowed the header's navigation and its call-to-action button.

The page still returned **200**, the tests still passed, and the first screenshot looked
*almost* right. Nothing anywhere reported a problem.

```html
<!-- rendered output, before the fix -->
{# Phones: the prototype simply hid the nav below `md` … A <details> element is …
   what the zero-build-pipeline rule requires. #}
<details class="site-menu"> …          <!-- this one got a stray parent -->
```

**Rule:** use `{% comment %}…{% endcomment %}` for anything longer than one line, and
assert on the **source**, not only the output:

```python
for match in re.finditer(r"\{#(.*?)#\}", source, re.S):
    assert "
" not in match.group(1), "multi-line {# #} — use {% comment %}"
```

C1 now has both guards (`test_no_template_uses_a_multiline_hash_comment` and
`test_no_unrendered_template_syntax_reaches_the_browser`), and the second one also counts
`<main>` and `<details>` in the output so a structural mutation fails loudly.

### 1.10 A media query placed above the rule it refines loses

The hero's two call-to-action buttons rendered **stacked and full-width on desktop**,
while the CSS read exactly as intended:

```css
@media (min-width: 640px) { .hero__cta { width: auto; } }

.hero__cta { width: 100%; }        /* later in the file — and therefore the winner */
```

A media query adds **no specificity**. Both selectors are one class, so the later
declaration wins and the breakpoint is dead. Nothing warns; the desktop screenshot simply
shows the mobile layout stretched.

**Rule:** in a component block, write base rules first and breakpoints after, in one
place. (`core/static/css/site.css` says so in a comment at the sites where it bit.)
Mutation-test a breakpoint the same way as a Python guard: change the base value and
confirm the wide viewport changes.

### 1.11 A sibling margin inside a grid track shrinks the card

Two cards side by side in a grid looked "slightly off": the second sat 24px lower and was
24px shorter than the first. The cause was a **stacking** rule that the side-by-side case
inherited:

```css
.callout + .callout { margin-top: 1.5rem; }   /* for stacked callouts */
```

In CSS Grid, an item's margins are honoured *inside* its stretched track: 24px of top
margin pushed the box down 24px and reduced its height by 24px. The two boxes were still
"the same size" as far as the grid was concerned.

**Evidence, in one measurement** (the reason this was diagnosed in minutes rather than by
eye):

```python
[{top: 446.5, height: 206.25}, {top: 470.5, height: 182.25}]   # before
[{top: 446.5, height: 206.25}, {top: 446.5, height: 206.25}]   # after `.element-grid > .callout { margin-top: 0 }`
```

**Rule:** when two boxes in a grid disagree about size, measure their boxes before reading
the CSS. A stacking sibling rule is the usual suspect, and it never looks like one.

### 1.12 An error before the first test is a fixture problem, not a test problem

The Playwright suite (C1e) reported **25 errors and 0 passes**. Nothing was wrong with a
single test; the whole run died during fixture setup, before any page loaded:

```
E   django.core.exceptions.SynchronousOnlyOperation:
    You cannot call this from an async context - use a thread or sync_to_async.
During handling of the above exception, another exception occurred:
request = <SubRequest '_live_server_helper' for <Function test_the_phone_menu_opens_fully_on_screen>>
```

Two libraries want the same thread. `pytest-django`'s `live_server` sets up a
transactional database synchronously; `pytest-playwright` already has an asyncio loop
running (it drives the sync API through a greenlet). Django sees a live event loop and
refuses ORM access. One environment variable fixes it:

```python
# tests/e2e/conftest.py — here, never in pgs/settings.py
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")
```

It is safe in that file and nowhere else: those tests never touch the ORM themselves —
every database read happens inside the live server's own thread, answering an HTTP
request. In `settings.py` it would switch the protection off for the gate as well.

**The diagnostic cost was not the bug, it was the shape of the output.** 25 errors read as
"the tests are broken", and the honest first instinct — rewrite a test — is the wrong
move. The tell is `errors` rather than `failures`, and a traceback naming a `SubRequest`
fixture instead of a test line.

**Rules:**

* **`errors` + a fixture name in the traceback = setup, not assertions.** Fix the
  fixture wiring; do not touch the test until a test body has actually run.
* **A dependency combination is a suspect in its own right.** `pytest-django` +
  `pytest-playwright` is a known pair; check the fixture layer before the code.
* **Prove the suite can run at all** (`pytest tests/e2e -k one_route`) before judging a
  failing assertion. And mutation-test the first guard you write there — the 44px test
  failed for a genuine reason (a 26px-wide "Fees" link) *and* for a false one (a
  `display:none` menu measuring 0×0), which is only visible once the suite runs.

### 1.13 The page exists, the rows do not — and the sweep still passes

C4's claim-discipline sweep is parametrised over the public URLs, which is the right
shape: every route, every forbidden term. C2 made `/documents/` render its eight rows
from the database — and `test_claim_discipline.py` seeded no documents, so on that
route the `{% for %}` loop ran zero times.

**Evidence.** A mutation that put `Publishing soon` back inside a document row — the
exact regression the suite exists to catch, on the page it was just added to — left
**all 36 tests green**:

```
$ pytest core/tests/test_claim_discipline.py -q
36 passed in 1.57s          # with the chip restored in the template
```

After adding a `public_surface` fixture (`seed_deployment` + `publish_documents`, a
tmp `MEDIA_ROOT`) the same mutation fails on **two** routes and no others:

```
FAILED test_claim_discipline.py::test_nothing_is_pending_on_a_public_route[home]
FAILED test_claim_discipline.py::test_nothing_is_pending_on_a_public_route[documents]
2 failed, 34 passed
```

**Rule:** a route that renders **data** is only covered once the fixture seeds that
data. §1.6 is the empty `parametrize`; this is its subtler sibling — a non-empty
`parametrize` over a page that renders an empty list, where the URL looks covered and
the content is not. Whenever a page's body comes from a table, the browser and sweep
suites need a fixture that populates it, *and* a test that asserts the row count so a
broken fixture cannot pass as a working page.

### 1.14 `logging`'s `extra=` may not shadow a `LogRecord` attribute

`logger.info("published", extra={"created": n})` raises **`KeyError: "Attempt to
overwrite 'created' in LogRecord"`** at log time — not at import, not at the call site,
and not with a useful traceback. `created` is the record's own timestamp, so the
message is about a field you never wrote and the stack points into
`logging/__init__.py`:

```
File ".../logging/__init__.py", line 1636, in makeRecord
    raise KeyError("Attempt to overwrite %r in LogRecord" % key)
KeyError: "Attempt to overwrite 'created' in LogRecord"
```

Here it surfaced as **19 collection-time errors** in `test_documents.py` — every test
that used the fixture — while the feature itself was correct.

**Rule:** prefix `extra` keys with the domain (`documents_created`, not `created`). The
reserved set is `LogRecord`'s own attributes: `name`, `msg`, `args`, `levelname`,
`levelno`, `pathname`, `filename`, `module`, `exc_info`, `exc_text`, `stack_info`,
`lineno`, `funcName`, `created`, `msecs`, `relativeCreated`, `thread`, `threadName`,
`processName`, `process`, `taskName`, `message`, `asctime`.

### 1.15 A URL segment is not a Django slug

`<slug:code>` compiles to `[-a-zA-Z0-9_]+` — **no dots** — and `SlugField`'s
`validate_slug` uses the same pattern. A document code of `saoso-standard-v2.1` is a
perfectly good URL segment (`/documents/saoso-standard-v2.1/`) and a bad Django slug:

```
NoReverseMatch: Reverse for 'document_file' with arguments ('saoso-standard-v2.1',) not found.
1 pattern(s) tried: ['documents/(?P<code>[-a-zA-Z0-9_]+)/\\Z']
```

And because `validation` is not a `constraint` (§1.7), `PublicDocument.objects.create()`
accepts the dot happily — so the failure appears at **render** time, on a template, for
a row that saved without complaint.

**Rule:** when a field is a URL segment, say so with a `CharField` plus an explicit
`RegexValidator` and route it with `<str:code>`. Do not use `SlugField` for anything
whose valid values you have not checked against `validate_slug`, and version numbers in
public addresses are the usual offender.

### 1.16 The backlog classifier reads the whole `Status:` line

`product/backlog.py` classifies a PRD by pattern-matching its **entire** `Status:` line, first
match wins, and `\bresolved\b`, `\bimplemented\b`, `\bcomplete\b`, `\bshipped\b` and
`\bdone\b` all mean *Done*. Those are exactly the words you reach for when describing a
**sub-decision** inside a plan that is still in progress:

```
Status: In Progress — … C1's open content decisions live in `C1_BUILD_PLAN.md` — #7 (the
February fee deadline) was **resolved: withheld** while building C2.

$ python product/backlog.py
DRIFT - 1 file(s) to move so directory matches Status:
  In Progress\MVP0_PLAN_V2.md  ->  Done\MVP0_PLAN_V2.md
```

The heading still said *In Progress* and the file still had three unbuilt tasks; one verb
in a subordinate clause was enough to queue an `--apply` that moves a live plan to Done.

**Rule:** keep `Status:` to the plan's own state. Record sub-decisions in the plan body or in
the build plan, never in the status line — and after editing a `Status:` line, run
`python product/backlog.py` and read the **DRIFT** section before running `--write`.

### 1.17 An `EscalatedQuery` is not evidence the corpus lacks an answer

The chatbot writes the **same** refusal and the same escalation for three unrelated
things: the passages really do not answer the question, the model's citation could not
be verified, and the *provider cut its reply at the output cap*. All three were observed
live on 2026-10-19 against the shipped corpus, and only the first is about the standard.

The manure question is the one that exposed it. It was refused twice, which reads as a
corpus gap — but the corpus answers it (BPP "2. Soil Management", SAOSO 4.4, Appendix 2)
and the model produced the right answer both times. Two separate mechanisms refused it:

```python
# 1. `sub_ref` spelling. Stored refs are `4.2(12)`; the model returned the printed
#    item marker, with the brackets. The audit's suffix check built `((12))`.
>>> audit_citations([{"section_ref": "§4.2", "sub_ref": "(12)", ...}], chunks, ...)
PROBLEMS: ("§4.2: sub_ref '(12)' does not exist in the chunk",)

# 2. Output cap. 1024 tokens cut a four-citation answer mid-string, and the JSON
#    error was re-raised as an outage:
json.decoder.JSONDecodeError: Unterminated string starting at: line 2 column 13 (char 14)
core.services._chatbot.UpstreamModelError: Gemini returned text that is not the
    requested JSON schema: Unterminated string ...
# -> POST /ask/ 503, "The assistant cannot reach the answering service right now."
```

Both are ours, and both looked to the operator like "the standard doesn't cover this".
The traceability canary — a question the corpus answers verbatim — was refused by
mechanism 1 alone, which is the cheapest possible proof that a `NO_CITATIONS`
escalation is not a corpus finding.

**The diagnostic trap inside the trap:** the citation audit's reasons live in
`extra={"chat_problems": ...}`, and the project's log format does not render `extra`
fields. The log said only `chatbot citation audit refused an answer`, so the first
reproduction had to be done by calling the provider by hand. Until fix 6 (a distinct
escalation reason per mechanism) lands, put the problems in the message, not only in
the extras.

**Rules:**

* **Never read a refusal as a corpus finding without the audit's `problems`.** Reproduce
  with `GeminiChatModel().answer(...)` + `audit_citations(...)` against real chunks —
  that costs one call and names the mechanism.
* **`finish_reason` is the authority on truncation, never the JSON parser.** A reply cut
  after a complete citation array parses perfectly and is still half an answer, so
  check the reason *before* `json.loads` and retry once at a larger cap.
* **A spelling is not a fabrication.** Resolve `§4.2`/`4.2`, `Section 6.3`/`§6.3`,
  `4.2(12)`/`12`/`(12)` — but only through a key that names **exactly one** stored
  locator, and report the *stored* locator in the `Citation` so the reader can look it
  up. Never strip the `S` prefix: D14 stores it because `1.1.1` exists in both Section
  A and Section B.
* **A cap that is too low is a logic bug with a transport error's face.**

Guards: `core/tests/test_chatbot_provider.py` (cap from settings, retry once, truncation
named) and the `_manure_chunk` tests in `core/tests/test_retrieval_scope.py`. Both were
mutation-tested — reverting the normalisation fails three audit tests, restoring
`max_output_tokens=1024` with no `finish_reason` check fails five provider tests.

### 1.18 A non-space multiset check that counts newlines reports total data loss

The loss-free invariant for the column transform (`knowledge/columns.py`) is "every
non-space, non-newline character survives". Newlines are excluded **deliberately**:
reordering a page changes them by definition, so counting them flags all 29 transformed
pages as catastrophic corruption and buries the real question (did a footnote vanish?).

Evidence (the guard working honestly before newlines were excluded):

```
Counter(page) != Counter(de_column(page))   # on every column page
# but the difference is only '
'
```

**Rule:** define the invariant you actually mean. For reordering, it is the character
multiset modulo whitespace structure; strip `" "` and `"
"` before comparing.

### 1.19 A raw `in` substring assertion fails on a contiguous sentence

`pdftotext` breaks lines inside a sentence, so the BPP manure sentence is contiguous
*modulo line breaks*: `"Animal manure
must be preferably composted
…"`. A raw
substring test fails on text that `audit_citations` accepts, which looks like the corpus
fix not working.

**Rule:** normalise exactly as the audit does — `" ".join(text.split())` — before
asserting a sentence is present. Never "fix" the corpus to satisfy a naive `in`.

### 1.20 A loss-free test passes for the wrong reason when the transform never runs

The multiset test is green when `de_column` returns the page unchanged, and green when
it is not called at all. It is only a guard **beside the golden page set**. Measured:
disabling the transform turned 8 column tests red and left the multiset test green.

**Rule:** pair a loss-free test with a pinned set of pages that must change, and pin one
literal count (BPP = 8) that the golden set cannot drag along when the detector regresses
to zero.

### 1.21 Reordering page furniture invalidates any parser that reads a stamp by position

`heading.py::_page_stamp` read the **last** non-blank line to find a bare page number.
That works on the raw landscape page and fails after de-columning, because the stamp is
page furniture and reordering moves it to roughly line 50 of 90 — so every landscape
section silently lost its `page` (all `None`, violating D42) while every other test
stayed green.

**Rule:** a parser that reads a stamp by position is coupled to the page layout. After
any layout transform, pin `(section_ref, anchor, page)` sets per document before trusting
it; then search for the stamp anywhere rather than at the tail.

### 1.22 A recorded "correct quote" may be a paraphrase, and chasing it weakens the audit

The 2026-10-19 model reply quoted the BPP as "must preferably be composted and sourced
from farms under organic management or extensive farming practices". The standard prints
"must be preferably composted **prior to application, and** must be sourced from farms
under organic management, **or from extensive farming practice**". It is a paraphrase;
an exact substring audit refuses it against a *perfect* corpus.

**Rule:** state the success gate against the verbatim corpus sentence, and add a second
test asserting the recorded paraphrase is still refused. That pins the audit's strictness
rather than relaxing it to make a recorded answer pass.

### 1.23 A synthetic two-column page whose lines overflow the gutter looks like a bug

A test page built with `f"{left:<28}{right}"` and a 22-28 band is only cut where a line
is blank across the whole band. If the left text overflows past column 22, the line has
text at the band positions, rule 2 keeps it whole, and the output looks misordered —
while the implementation is correct.

**Rule:** build synthetic pages with gutters the text respects (pad to the band, do not
merely exceed it), and test detection against the real PDF bytes. `test_columns.py`
does both.

### 1.24 A chunk that looks pre-transform may be exactly what the transform produces

On 2026-10-21 the Appendix 2 chunk held
`Trace elements, e.g.: boric acid, sodium borate, calcium Use restricted to cases where soil/plant nutrient`.
The obvious reading is "the corpus predates `de_column`" — `ingest_standard` is a no-op
when the PDF's sha256 is already stored, so a transform fix never reaches the database
on its own. That reading was wrong. Rebuilding every document's chunks in memory and
diffing them against the stored rows found **0 of 340 different**: the pipeline really
does produce that text, because the table's rows overflow the column gutter and
`de_column` keeps a spanning line whole by design.

So a re-ingest would have changed nothing, and the actual defect is the one
`CORPUS_COLUMN_EXTRACTION_PRD.md §3.5` records as out of scope: **table rows are not
reconstructed** after de-columning. A substance and its condition end up in different
places, and a model quoting a substance that spans the boundary is refused by the audit
for a reason that looks like hallucination.

**Rule:** before proposing a re-ingest for a corpus defect, rebuild the chunks in memory
and diff them against the stored rows. That is the only way to tell "stale" from "as
good as the transform gets". Test the *symptom a reader sees* — a substance paired with
its condition — not merely that a sentence inside one cell is contiguous.

### 1.25 A word the extractor hyphenated is not a quote, and the model looks guilty

On 2026-10-21 two correct answers were refused and both were filed as model failures: one
elided a word with `...`, the other paraphrased. Neither was the model's fault. The stored
text was
`The percentage of non-organic feed may not exceed 10% dry matter per ruminant and 15% dry matter per non-`
+ a page footer + `ruminant calculated on an annual basis.` — because `pdftotext -layout`
breaks lines where the *page* breaks them, and SAOSO prints its body double-spaced, so the
halves of a hyphenated word end up two lines apart. Whitespace normalisation turns that
into `non- ruminant`, which no reader writes. The model could only quote it by writing a
non-word, so it elided; the audit then refused, correctly. Same class in `S4.1.1`
(`post-` / `harvest`).

**Evidence that it is the corpus, not the model:** print `" ".join(chunk.text.split())`
and search for the sentence as the page prints it. If it is absent but the chunk *looks*
right, look for `letter-` at a line end — and for the printed footer (`P a g e | 47`) inside
the clause, which is the same page-boundary defect and hit 65 of 368 chunks.

**Rule:** a refusal whose quote differs only at a line break is a corpus defect — repair
the page (`knowledge/reflow.py`, and `PAGE_FOOTER` in `FURNITURE`), never the audit, and
not the prompt first. Measure the corpus before blaming the model, then verify the fix
with `scripts/probe_chat.py` on the question that failed.

### 1.26 `-raw` glues words, but it is a pure permutation of `-layout`

`pdftotext -raw` keeps the producer's content-stream order — the only order oracle
available without a layout library — and drops the spaces between text-show operations,
so `Sourced locally from neighbouring` becomes `Sourcedlocallyfromneighbouring`. Two
measurements (2026-10-22) turn that from a curiosity into a usable tool:

- **All 139 pages** of the four governed documents are **character-for-character
  permutations** of their `-layout` rendering (multiset of non-space characters, equality
  per page). `-raw` invents and loses nothing; only spacing and order differ.
- The glue is **repairable**: split each glued token into the run of consecutive
  `-layout` words that concatenates to exactly that token. On BPP, 11 of 13 pages then have
  *identical word multisets*, and those are the pages whose columns defeat the band
  detector (pdf 3, 6, 9).

**Rule:** use `-raw` as an *order* oracle and gate it mechanically — a page may be drafted
from `-raw` only when, after glue repair, its word multiset equals `-layout`'s. Never ship
`-raw` text unrepaired, and never repair a glue the `-layout` words do not contain: an
unrepairable token means the page is not clean, so fall back to geometry.

### 1.27 `write_text` writes CRLF on Windows, so the artefact differs per platform

`Path.write_text(text)` opens the file in text mode, and on Windows that translates every
`
` to `
`. A corpus artefact generated on the dev box therefore has different bytes
— and a different sha256 — from the same artefact generated on the VPS, which defeats the
whole point of recording the digest. It went unnoticed at first because the *reader*'s
regexes tolerate `
` and the tests pass on either.

**Rule:** write generated text with `open(..., newline="")`, exactly as
`scripts/extract_fixtures.py` already did for the fixtures. Assert `"
" not in text`
in a test if the artefact's digest is ever trusted.

### 1.28 A paragraph crosses the page break, and "remove this text" is not `str.replace`

Two small traps met while building the D53 traceability guard:

1. **A block's page is a *start* page.** The BPP manure sentence spans PDF pages 4→5, and
   `test_the_bpp_manure_sentence_is_quotable_from_one_chunk` requires one chunk. Splitting
   the paragraph at the page break would insert the chunker's favourite boundary into the
   middle of the most-quoted sentence in the corpus. So the provenance check is "a
   contiguous slice of the pages from here on", not "contained in one page".
2. **`str.replace` for a dropped token eats the wrong occurrence.** Removing the bare page
   stamp `02` from a page with `text.replace("02", "")` also mangles `2020` and `2022`.
   Remove *occurrences by position* (`re.finditer` + slice), or the test starts asserting
   against text the PDF never had.

**Rule:** a generated artefact's provenance is a page **range**, and any character removal
in a guard is done at a known position, never by plain substring replacement.

### 1.29 A string "present" in a JSON payload is not present in the file

The UAT runner embeds each scenario's raw markdown in a `<script type="application/json">`
payload, and a test asserted every `Judgement:` clause appeared *verbatim* in the artefact.
Three scenarios failed that check while the page was perfectly correct: `json.dumps` escapes a
newline as the two characters `\` `n`, and those judgements contain bullet lists, so the
multi-line string is not a substring of the file at all.

Evidence:
    judgments missing: [7, 8, 10]
    # scenario 7's judgement is prose followed by four `* ` bullets

**Consequence:** the obvious repair is to weaken the assertion until it passes, which is how a
verbatim guarantee becomes a decoration. The mirror-image trap is asserting against a payload
that the *same parser* produced, which proves only that the parser is deterministic.

**Rule:** compare against the **source file**, not against the payload — take the judgement's
lines out of the raw markdown, strip the marks the renderer consumes, and assert the words
appear in the page's visible text. Check the payload separately, after `json.loads`, for the
character-for-character equality. Two tests, two different questions.

### 1.30 A self-contained HTML whose script does not parse passes every grep-based check

The UAT artefact is **server-rendered**: the cards, the judgement text, the payload and the
counts are all in the HTML before any script runs. So when extracting the page's JavaScript into
`scripts/uat_page.py` left the original IIFE's closing `})(`/`})();` inside the script body *and*
wrapped it a second time, seventeen tests — including "no network", "every judgement is
rendered", "no markdown left", "one card per scenario" — stayed green. The page was completely
inert: no autosave, no PASS button, no export.

Evidence:
    pageerror: Unexpected token '}'
    DATA type: undefined          # the payload script never executed
    progress html: ''             # progress() never ran
    # 17 structural assertions green throughout

**Consequence:** a file that "opens" proves nothing. Every assertion about a generated page's
*content* can hold while the page does nothing, and the reviewer discovers it as a dead button
with no error on screen.

**Rule:** load the artefact in a real browser and assert something that only the script can
produce — a console with no `pageerror`, a computed progress line, an export that downloads. In
this repo that is Playwright against the `file://` URL. If the browser check cannot live in the
gate (it cannot — no browser on the VPS), then run it manually and record it, and never describe
a generated page as "verified" on the strength of a grep.

### 1.31 A reply the audit will reject is cached *before* it is audited

`answer_question()` writes the model's reply to the answer cache immediately after the
model returns, and runs `audit_citations()` afterwards. A reply whose citations fail the
audit is therefore cached anyway, and every later question with the same normalised text
is served that same rejected reply for the whole TTL. A refusal that was one bad model
turn becomes a refusal that reproduces exactly, which reads like a corpus gap.

Evidence (dev box, 2026-10-20, live provider, the UAT's own Scenario 1 question):

    attempt 1: cached=False citations=0 -> I cannot find a definitive answer in the SAOSO …
    attempt 2: cached=True  citations=0 -> I cannot find a definitive answer in the SAOSO …
    # and the audit's own complaint, replayed from the cache:
    #   general-principles: sub_ref 'd.ii' does not exist in the chunk
    # the escalation reason was NO_CITATIONS in both cases

The model had produced two citations for one sentence: the real one (`S5.1.9`, quote
"… **8** continuous hours …") and a paraphrase of it under `general-principles` with an
invented `sub_ref` ("… **eight** continuous hours …"). The all-or-nothing audit refused
the pair — correctly; that is the product working. The cache is what made it stick.

**Consequence:** three things are indistinguishable in the record, and only one of them is
true: "the model cited nothing", "the model cited something wrong", and "a wrong answer
was cached an hour ago". The first two also hide a model-contract violation behind a
reason that suggests the corpus is thin.

**Rule:** cache only a reply that passed the audit, and give an audit rejection its own
`EscalatedQuery` reason. When a grounded question refuses, read the logged
`chat_problems` (the structlog `extra=` field) before believing the escalation reason —
and before touching retrieval, the corpus or the prompt.

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

### 2.4 `websearch_to_tsquery` ANDs a natural question into zero results

A chatbot question is not a search-box query. Postgres's `websearch_to_tsquery` joins
space-separated words with **AND**, so

```sql
websearch_to_tsquery('english', 'What does the standard require for traceability?')
-- 'standard' & 'requir' & 'traceabl'
```

matches only a chunk containing *all three* lexemes. The SAOSO traceability clause
says "Handlers and processers shall ensure traceability…" and contains neither
"standard" nor "require" as a form that survives stemming in that sentence. Retrieval
returns **nothing**, the chatbot refuses, and every unit test that uses a
phrase-shaped query (`"traceability of organic processing"`) still passes.

Evidence, against the shipped corpus on 2026-10-19:

```text
search('What does the standard require for traceability?')  -> []
search('traceability OR standard')                          -> chunks
```

**Consequence:** a grounded chatbot that answers only from retrieved passages refuses
everything a real person types, while the retrieval suite is green — the classic
"test the phrase, not the question" failure.

**Rule:** build the lexical query from the question's significant terms, and do not
trust a single OR either: common words ("standard") can outrank the rare word that
carries the question. `core/services/_chatbot.build_retrieval_query` strips function
words; `knowledge.services.search_terms` searches the **rarest** term first and the OR
fallback second, then de-duplicates. Test both with a natural question, not only with
the phrases the standard happens to contain.

### 2.5 `manage.py check --deploy` exits 0 while the deployment is unsafe

Django's `check` command has a `--fail-level` option whose default is **ERROR**.
Every deployment security check — W004 (no HSTS), W008 (no SSL redirect), W012/W016
(insecure cookies), **W018 (`DEBUG=True` in deployment)** — is a *warning*, so the
command prints a page of warnings and exits **0**.

Evidence (`Django==5.2.18`):

```
$ DJANGO_DEBUG=1 manage.py check --deploy;                     echo $?
System check identified 5 issues (0 silenced).                0
$ DJANGO_DEBUG=1 manage.py check --deploy --fail-level WARNING; echo $?
System check identified 5 issues (0 silenced).                1
```

**Consequence:** a deploy script written as `if ! manage.py check --deploy; then
abort; fi` is a gate that can never go red. It reports "checked" in every log while
the exact misconfiguration it exists to catch — a production site serving tracebacks
with `DEBUG=True` — passes straight through. This is the same class as §2.1: the
tool ran, exited successfully, and enforced nothing.

**Rule:** pass `--fail-level WARNING` wherever `check --deploy` gates a release
(`deploy/first-install.sh`, `deploy/deploy.sh`). If you deliberately decline one
warning — this project declines `security.W021` (HSTS preload is irreversible and
this is not yet the group's forever host) — silence it **by id** in
`SILENCED_SYSTEM_CHECKS`, never by raising the fail level. Then prove the guard can
fail: set `DJANGO_DEBUG=1`, watch the command exit non-zero, and put it back.

### 2.6 A test outside `testpaths` is a test nobody runs

`pytest.ini` sets `testpaths = core knowledge`, so a new `tests/tools/` directory full of
passing tests is not collected by `pytest` at all. The gate stays green, the coverage looks
higher than it is, and the guard the new tests were written for is decoration.

Evidence:
    # pytest.ini, before:
    testpaths = core knowledge
    $ python -m pytest -q          # 705 passed  — tests/tools/ never mentioned
    $ python -m pytest tests/tools -q
    63 passed                      # the directory was fine; it was simply not in the gate

**Consequence:** `verify.sh` reports "this tree is shippable" while the checks that decide what
a human signs have never run on it. Same class as §2.1 and §2.5: the tool ran, said OK, and
examined nothing.

**Rule:** when you add a test directory, add it to `testpaths` in the same commit, and prove
collection — break one of the new tests and watch `pytest -q` (not the directory-scoped run) go
red. `tests/e2e` stays out on purpose: it needs a browser the VPS does not have.

### 2.7 A `getattr(settings, ...)` fallback is dead code, so the "fix" changes nothing

`answer_question()` read its retrieval budget as
`int(getattr(settings, "CHAT_RETRIEVAL_LIMIT", RETRIEVAL_LIMIT))`. `settings` **always**
defines `CHAT_RETRIEVAL_LIMIT` (its own default is `"5"`), so the second argument could never
be used. The 2026-10-21 answer-coverage work recorded *"Chat `RETRIEVAL_LIMIT` 5 → 8"* and
changed the module constant — the product kept retrieving five passages, and the plan, the
constant's comment and the PRD all said eight. Nobody noticed because the **probe** hardcoded
`limit=8`: the instrument and the product disagreed, and the instrument is what the session
measured.

Evidence, 2026-10-22, against the shipped corpus (366 chunks, embedded):

```text
settings.CHAT_RETRIEVAL_LIMIT = 5      # the live budget
_chatbot.RETRIEVAL_LIMIT      = 8      # the fallback: never read

$ python scripts/probe_chat.py "Can i use cardboard from my neighbour?"          # limit 5
  ... no inputs clause retrieved; ANSWER: (empty); insufficient_context: True
  AUDIT: REFUSED
$ python scripts/probe_chat.py --limit 8 "Can i use cardboard from my neighbour?"
  ANSWER: The SAOSO Standard does not specifically name cardboard. However, for
          biodegradable processing by-products of plant origin ...
  AUDIT: grounded
```

A real visitor question was refused in production for a day while the suite, the probe and the
PRD were green — the "passes for the wrong reason" pattern applied to a *deployment* setting.

**Consequence:** any setting read through `getattr(settings, NAME, DEFAULT)` is only a default
for a settings module that does not define it. If `pgs/settings.py` defines it, the module
constant is documentation, not configuration.

**Rule:** one accessor, no duplicated numbers. The budget is now `chat_retrieval_limit()` and
retrieval is `default_retrieval()`; the view and `scripts/probe_chat.py` both call them, and
`test_the_shipped_retrieval_budget_and_the_fallback_agree` fails if the setting and the
fallback disagree. When you change a budget, change it in `pgs/settings.py` **and**
`.env.example`, then bump `PROMPT_VERSION` — the answer cache is keyed on the prompt contract,
not on the retrieval budget.

---

## 3. This machine (Windows, Docker Desktop) — and shell traps

Not code bugs, but they cost time and they will recur. §3.6 is not Windows-specific:
those four bash traps silently produced unrestorable backups.

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

### 3.6 Shell scripting traps that fail *silently*

Four bugs in `scripts/backup.sh` / `scripts/restore.sh`, every one of which produced a
backup that looked fine and could not be restored. They are generic bash traps, not
project-specific.

**`set -e` + `[ cond ] && assignment` aborts with no output.**

```bash
set -euo pipefail
parse() { ...; [ "$DB_PORT" = "$DB_HOSTPORT" ] && DB_PORT="5432"; }
parse    # false condition -> function returns 1 -> set -e kills the script
```

The script died with **zero output**, which is indistinguishable from a crash. Use
`if`, so the status is always 0.

**`local a="$1" b="$2" c="$a"`** — bash expands every word of the command *before*
performing any assignment, so `$a` is still unset and `set -u` aborts with
`label: unbound variable`. Use one `local` per line.

**`set -a; . .env; set +a` is not a dotenv parser.** Django's
`get_random_secret_key()` emits `(`, `)`, `*`, `$` and `!`:

```
.env: line 1: syntax error near unexpected token `)'
```

Parse it: split on the first `=`, export the remainder verbatim, never evaluate it.

**`if [ -d "$dst" ]` after `mkdir -p "$dst"` restored 0 files and reported success.**
A backup that creates a directory before deciding between `rsync` and `tar` contains
*both* an empty directory and a populated tarball; a restore that prefers the
directory copies nothing. **An empty tree and an absent one must not be
distinguishable at restore time** — write an explicit `<label>.absent` marker, and
treat "recorded as present, restored as empty" as a failure.

**Also: `pg_dump` newer than the server.** Client 17 → server 16 emits
`SET transaction_timeout = 0` (a 17-only GUC). `pg_dump` exits 0, `pg_restore --list`
lists every entry, and the restore fails on the preamble having restored nothing.
Compare major versions and choose a matching client (or borrow the container's).

## 3.7 Fixtures extracted from documents

**A page number in a plan is a claim, not evidence.** A10's stated page ranges were all
wrong: `saoso_part_b` "pp. 60–62" starts one page early, in the tail of §9.6
(*aquaculture*), which would have grafted unrelated text onto a processing fixture;
the TOC is p2, not p1; `APPENDIX 1` starts on p71, not p70. Extracting on trust
reproduces v1's failure exactly — a fixture that does not match the document it
describes, so the parser's tests pass while the parser matches nothing.

**Rule:** an extraction script declares an `anchor` that must be present on the
fixture's start page, verifies it, and **fails** rather than writing the fixture. Show
the actual page content in the error, so the cause is diagnosable.

**Two things to check before trusting a regex against a real document:**

- `APPENDIX 1` appears in the body in **UPPERCASE** at ~62 columns, while the TOC uses
  title case `Appendix 1`. A title-case, column-0 regex matches nothing in the body but
  **false-positives** on p63, where `Appendix 4.` begins a mid-sentence line. Test both.
- **Glyphs the PDF fails to map to Unicode become U+FFFD.** The OPP's pasture-raised
  line carries an en-dash in the spec that no extractor produces: `pdftotext -enc
  Latin1` yields byte `0xFF`, `-enc ASCII7` yields `-`. The byte is not valid UTF-8 and
  no encoding recovers it. Do **not** hand-edit the fixture — a hand-corrected fixture
  stops being evidence. Record the count in the manifest and assert on text that
  survives extraction.

**On determinism:** open files with `newline=""` when writing fixtures. Python
otherwise translates `
` to `os.linesep`, so fixtures differ between Windows and the
VPS — the determinism check passes locally and fails in CI.

---

### 3.8 A long-lived dev server serves stale code, and the screenshot proves nothing

`manage.py runserver --noreload` (which `_scratch` scripts use to avoid the autoreloader
forking twice) keeps **Python modules** in memory forever. With `DEBUG=False` — this
project's default — Django also uses the **cached template loader**, so template changes
are invisible too. `--noreload` means "do not restart when files change", not "reload
templates anyway".

Three rounds of screenshots showed the old page while `pytest` showed the new one,
because the test client starts a fresh process per run. The page looked broken; it was
merely old.

**Rule:** when a browser and the test client disagree, believe the test client and
restart the server. For visual work, run the dev server with both:

```bash
DJANGO_DEBUG=1 python manage.py runserver 127.0.0.1:8931 --noreload
```

and confirm what you are looking at before judging it:

```bash
curl -s http://127.0.0.1:8931/ | grep -c "key-facts"    # 0 means: not your code
```

### 3.9 The port you chose may already belong to another project

Port 8123 answered `200 OK` immediately, so the screenshot step "worked" — and produced a
dashboard for **Tenderly**, a different repository whose dev server was still running.
Playwright reported a clean load, `document.fonts` listed Inter and Playfair Display, and
the only clue was that the fonts were two families this project never declares.

**Rule:** start the server on a port you own, bind it explicitly (`127.0.0.1:PORT`), and
assert one string from *your* page before trusting a screenshot:

```python
page.goto(BASE + path)
assert "Outeniqua" in page.title()
```

Better still, let Playwright use `live_server`, whose URL it cannot confuse.

### 3.10 Xpdf's `pdftotext -v` prints its version and exits **1**

`deploy/` now installs poppler, this dev box runs Xpdf 4.00, and the two report themselves
identically at first glance. The preflight row was written as `ok = returncode == 0 and banner`,
so a correctly installed Xpdf — which prints `pdftotext version 4.00` to stderr and exits 1 —
read as a permanently red row.

Evidence:
    $ pdftotext -v; echo $?
    pdftotext version 4.00
    1

**Consequence:** a warning that is always on is a warning nobody reads, and the row exists to
tell a reviewer whether their quotes came from the same extractor as the corpus. One permanent
red trains them to ignore all six rows.

**Rule:** treat "a version banner was printed" as the check, and name the implementation
(`poppler` / `Xpdf 4.00`) explicitly — the version is the fact that matters, not the exit code.
Keep the row advisory: it is needed to re-extract a document, not to judge a scenario.

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
