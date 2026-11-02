# Context budget — what a session reads, and why it is getting too big

**Status:** measured 2026-11-02; four cuts proposed, none taken yet.
**Instrument:** `python scripts/context.py` (sizes and recipes), `--check` (every breach).
**Read this when** you are starting a session, adding to `HANDOVER.md`, writing a §18.3 row, or
wondering why a "quick" task needed half a day.

---

## 1. The measurement

`AGENTS.md` said *read these first* and named six files. Their cost **before the 2026-11-02 split**
(the first row is fixed; the rest is the work still to do):

| lines | KB | ≈ tokens | file |
|---:|---:|---:|---|
| 2,553 | 180 | 50,000 | `HANDOVER.md` |
| 103 | 13 | 4,000 | `product/docs/context/build_principles.md` |
| 1,791 | 93 | 27,000 | `product/docs/context/testing_hazards.md` |
| 1,067 | 172 | 49,000 | `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` |
| 424 | 25 | 7,000 | `product/backlog/In Progress/MVP0_PRD.md` |
| 391 | 26 | 7,000 | `product/backlog/ready/MVP1A_PRD.md` |
| | **509** | **≈ 144,000** | total before the split |

After §4.1 the `HANDOVER.md` row is **101 lines / 13 KB / ≈4,000 tokens**, and the read-set total
is **342 KB ≈ 95,000 tokens** — still too much, because the spec's decision table (172 KB) and
`testing_hazards.md` (93 KB) are the next two items, and both are read by *searching* rather than
linearly.

A session that follows that instruction has spent its budget before running a test. This is not
a style complaint: it is the reason sessions start by reading history instead of by reading
code, and the reason a one-line fix arrives with a summary of what the previous agent thought.

**`python summarise.py` does not exist.** `build_principles.md` §V still says "run it to
regenerate the context buffet". The instruction has been dead for as long as anyone has looked.

## 2. Where the bytes actually are

Three different causes, and they need three different answers:

1. **`HANDOVER.md` was a log, not a state** (fixed 2026-11-02, §4.1). 22 session sections; the
   *current state* was 72 lines. Every session appends; nothing is ever retired. It has grown monotonically and will
   keep growing — the one file every session reads is the one file that never shrinks.
2. **The spec's decision table is a research record.** §18.3 is 72 KB of the file's 172 KB:
   78 rows, the largest 3.7 KB (`D71`), and the pattern is that each new decision is argued in
   full *in the row*. The evidence already exists in `product/design/` and the PRDs; the row
   repeats it.
3. **Source files are over the cap the repo already claims.** §II says no source file exceeds
   30 KB. Eleven Python files do:

   | KB | file |
   |---:|---|
   | 91 | `core/services/_chatbot.py` |
   | 49 | `knowledge/corpus.py` |
   | 44 | `core/tests/test_chatbot_grounding.py` |
   | 43 | `core/services/_documents.py` |
   | 40 | `knowledge/tests/test_ingest.py` |
   | 36 | `core/tests/test_document_reader.py` |
   | 35 | `knowledge/tables.py` |
   | 34 | `knowledge/tests/test_retrieval.py` |
   | 33 | `knowledge/services.py` |
   | 32 | `knowledge/tests/test_section_parsers.py` |
   | 30 | `scripts/build_corpus.py` |

   The cap was never enforced for Python (it is, for CSS — `test_public.py:183`). So the rule
   is aspirational and the growth was invisible.

## 3. The budgets

| File | Budget | Why |
|---|---|---|
| `HANDOVER.md` | **250 lines** | it is the file every session loads; history belongs in `product/docs/handover/` |
| any source file | **30 KB** (§II, unchanged) | already the rule; needs enforcing |
| one §18.3 row | **1,500 bytes** | a decision is a sentence and a link; the argument lives in the artifact |
| a task recipe | **~20k tokens** | above that, the session is reading instead of working |

## 4. The four cuts

### 4.1 `HANDOVER.md` becomes state; history moves to `product/docs/handover/` — **DONE 2026-11-02**

The top block (`START HERE` → repo state) is already the right shape — 72 lines: what landed,
what is next, what not to do. Everything below it is a session narrative.

- Keep in `HANDOVER.md`: the START HERE block, the repo-state block, the "do not run this"
  list, and a one-line-per-session index linking to archives.
- Move each `## 0x.` section verbatim to `product/docs/handover/SESSION_<date>_<slug>.md`.
  The directory already exists (it holds `DOCUMENT_INGESTION_HANDOVER.md`), so this is a move,
  not a new convention.
- From then on: **a session's narrative goes to its own file first**; `HANDOVER.md` gets a line
  in the index and an updated state block. The file stops growing.

Cost: one mechanical commit (22 moves + an index). Nothing is lost; `git log` still has it, and
the archive is one hop away.

**Done, and measured.** `HANDOVER.md` went **2,553 → 139 lines**; 22 sessions moved verbatim to
`product/docs/handover/SESSION_<tag>_<date>_<slug>.md`. The move asserted that every moved section's
bytes appear exactly once in the archive: **173,325 bytes in, 173,325 bytes out**. The file now
holds the START HERE block, the repo state, and a one-line-per-session index; the rule from here is
*state in `HANDOVER.md`, narrative in its own file*. `tests/tools/test_handover.py` holds the
budget at 250 lines and checks every index link resolves.

**Found while doing it:** several modules cite `HANDOVER.md §17`, `§1.7`, `§6.5` and `§6` —
sections that have not existed for weeks, because the file was reorganised under them. They are
harmless but wrong, and they are the clearest evidence that a growing log is not just expensive but
unreliable. Fix them to name the archive file when you next touch those modules; do not do a
sweep for their own sake.

### 4.2 A §18.3 row is a sentence and a link

The row keeps: the decision, the date, the owner, the *one* measurement that settles it, and a
link to the artifact that argues it. Everything else already lives somewhere better:

- exploration artifacts → `product/design/` (they are written to be read, and they are);
- implementation record → the PRD's "landed" section;
- the measurement → the PRD's evidence table.

Cost: rewriting nine long rows (`D46`, `D47`, `D52`, `D53`, `D68`, `D69`, `D70`, `D71`, `D72`,
`D73`, `D74`, plus today's `D78`). Do it one row per commit, when you next touch that decision —
a big-bang rewrite of the spec is exactly the kind of work that costs a session and returns
nothing a reader can see.

### 4.3 Split `_chatbot.py` (and the rest) by responsibility

`core/services/_chatbot.py` is 91 KB — three times the cap — and it is the file a chat task
always opens. It has four responsibilities already, and the seams are named in its own headings:

| new module | takes | ≈ size |
|---|---|---|
| `_chat_prompt.py` | `SYSTEM_PROMPT`, `COST_QUESTION_RULE`, `build_prompt`, `significant_terms` | 15 KB |
| `_chat_audit.py` | `audit_citations`, `outcome_claim_warnings`, `cost_question_warnings`, locators | 20 KB |
| `_chat_provider.py` | `GeminiChatModel`, schemas, truncation handling | 15 KB |
| `_chatbot.py` | `answer_question`, the cache, refusals — the contract | 35 KB |

`knowledge/corpus.py` (49 KB) splits the same way: the header/format rules vs the table block
(`corpus_tables.py`). The four over-cap test files split by scenario, not by line count.

Cost: mechanical, but it touches imports across the tree, and every split must keep
`tests/tools/test_architecture.py` and `lint-imports` green. Do one file per slice, with the
suite green before and after.

### 4.4 Enforce it, or it grows back

- Wire `scripts/context.py --check` into `scripts/verify.sh` **once the tree is inside the
  budgets** — a gate that is red on day one trains people to skip it (`testing_hazards.md`
  §3.11). Until then it reports.
- Keep the `HANDOVER.md` check in `tests/tools/` rather than only in the script, so it runs in
  the gate like every other rule.
- Update `AGENTS.md`'s read table to name **recipes**, not files: "read these first" becomes
  "`python scripts/context.py --task <task>`", and the table loses its six-file list.

## 5. The recipes (the part that helps today)

Until the cuts land, `python scripts/context.py --task <task>` prints a per-task read set with a
`READ`/`SEARCH` mode per file. `SEARCH` means: find the section, stop, and name it in your
handover note. Current recipes: `chat`, `corpus`, `reader`, `public`, `backlog`.

The read budget for the `chat` recipe is **63 KB ≈ 18k tokens** — but only because three of its
six entries are `SEARCH`. Read whole, the same recipe is 427 KB. **That gap is the entire
argument for this document**: the files are not too big to exist, they are too big to be read
linearly, and the instructions currently say to do exactly that.

## 6. What this session cost, as evidence

The session that wrote the cost rule and P4 read roughly: the top block of `HANDOVER.md`, three
PRD sections, four modules, and `testing_hazards` §3.21/§3.23. About 45k tokens of reading for
about 6,000 lines of edits — and it still had to search `HANDOVER.md` twice for numbers that
turned out to be stale (the commit count, the test count). **A 2,553-line handover is not only
expensive; it is unreliable, because its numbers rot at different rates from its narrative.**

That is the argument for 4.1 in one line: **state is short and checked; history is long and
archived.**
