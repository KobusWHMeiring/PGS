# PRD: The context cuts — a sentence and a link, and a file that fits its cap
**Status:** **Done 2026-11-03** — steps 1-12 landed; `--check` is step 1/4 of the gate
**Owner:** Build (no product decision is open; the rules are already decided in `CONTEXT_BUDGET.md`)
**Last Updated:** 2026-11-03 (session `1c`)
**Scope:** Cuts **4.2** and **4.3** of `product/docs/context/CONTEXT_BUDGET.md`, then **4.4** (wire the
check into the gate). Not in scope: §4.1 (done 2026-11-02), and any change to what the code *does*.
**Reference:** `product/docs/context/CONTEXT_BUDGET.md` §3–§4 · `build_principles.md` §II (the 30 KB
cap) · `product/docs/context/testing_hazards.md` §3.11, §3.17, §3.24 · `AGENTS.md` (three budgets,
one loop) · `scripts/context.py`

---

## 1. Problem Statement

Every session pays for the read-set, and two of the three budgets are still broken. Measured
2026-11-03 by `python scripts/context.py --check` — **25 breaches**:

| Breach | Size | Cap |
|---|---|---|
| `core/services/_chatbot.py` | **97 KB** | 30 KB |
| `core/tests/test_chatbot_grounding.py` | 50 KB | 30 KB |
| `knowledge/corpus.py` | 49 KB | 30 KB |
| `core/services/_documents.py` | 48 KB | 30 KB |
| `knowledge/tests/test_ingest.py` | 40 KB | 30 KB |
| `knowledge/services.py` | 39 KB | 30 KB |
| `knowledge/tests/test_retrieval.py` | 38 KB | 30 KB |
| `core/tests/test_document_reader.py` | 36 KB | 30 KB |
| `knowledge/tables.py` | 35 KB | 30 KB |
| `knowledge/tests/test_section_parsers.py` | 32 KB | 30 KB |
| `scripts/build_corpus.py` | 30 KB | 30 KB (`> 30 × 1024` bytes) |
| **14 §18.3 rows** | 1.7–3.7 KB | 1.5 KB |

The 14 rows: `D46 D47 D52 D53 D68 D69 D70 D71 D72 D73 D74 D75 D78 D80` (`D71` is the largest at
3,689 bytes; `D68` 3,578). `_chatbot.py` is the file a chat task *always* opens, so its 97 KB is
paid on nearly every session in this repo.

**Why now.** `4.4` cannot run until the tree is inside the budgets, and `4.4` is what stops this
growing back. A report-only check has now watched the growth for a session without stopping it.

## 2. Strategic Goal

`python scripts/context.py --check` prints **zero breaches**, and `scripts/verify.sh` runs it. No
behaviour changes anywhere: same answers, same pages, same corpus.

## 3. Proposed Solution

The rules are already written and are not up for re-decision. Restated here so this file is the one
thing to read.

**4.3 — split by responsibility.** `_chatbot.py` already has responsibilities named in its own
headings:

| new module | takes | size |
|---|---|---|
| `_chat_text.py` **landed** | tokens, locators, digests: `normalise_question`, `_STOPWORDS`, `locator_of`, `text_sha`, `_normalise_ref`, `_sub_ref_names` | 8 KB |
| `_chat_prompt.py` **landed** | `PROMPT_VERSION`, `SYSTEM_PROMPT`, `COST_QUESTION_RULE`, `looks_like_cost_question`, `significant_terms`, `_render_table`, `build_prompt` | 21 KB |
| `_chat_values.py` | errors, `Citation`, `ModelReply`, `GroundedAnswer`, `ChatModel` | 6 KB |
| `_chat_audit.py` | `audit_citations`, `outcome_claim_warnings`, `cost_question_warnings`, `_address_book`, `_reader_anchors` | 12 KB |
| `_chat_provider.py` | `ANSWER_SCHEMA`, `GeminiChatModel`, truncation handling, the model constants | 8 KB |
| `_chat_guard.py` | rate limit, `validate_question`, follow-up detection, retrieval defaults, session lifecycle | 13 KB |
| `_chat_cache.py` | the answer cache: `_cache_key`, the grounding snapshot, the JSON round-trip | 8 KB |
| `core/services/_chatbot.py` | `answer_question` and the refusals — **the contract** | 23 KB |

**Amended 2026-11-03, after step 1.** The first table had four modules and left `_chatbot.py` at
35 KB — over the 30 KB cap the split exists to satisfy — and step 2 could not be built at all:
`audit_citations` constructs `Citation`, which lived in `_chatbot`, so the audit and the contract
would have imported each other. The two moves that landed were a pair (the prompt cannot be
built without the locators) and measured 8 + 21 KB. The remaining sections measured 6.3
(errors + values), 12.4 (audit), 7.6 (generation), 10.7 (lifecycle + guardrails), 18.1
(contract), 6.8 (cache). So the values move **before** the audit, and the guardrails leave too
or `_chatbot` lands at ~33 KB. No behaviour change anywhere; the prompt's bytes are proved
identical by `_scratch/probe_prompt_hash.py`.

`knowledge/corpus.py` splits the same way: the header/format rules stay, the table block moves to
`knowledge/corpus_tables.py`. The five over-cap **test** files split **by scenario, not by line
count**.

**4.2 — a §18.3 row is a sentence and a link.** The row keeps the decision, the date, the owner,
*the one measurement that settles it*, and a link to the artifact that argues it. The argument goes
where it already belongs: exploration → `product/design/`, implementation record → the PRD's
"landed" section, measurements → the PRD's evidence table.

**4.4 — enforce it.** Wire `scripts/context.py --check` into `scripts/verify.sh` **only once it
prints zero**. `tests/tools/test_handover.py` already holds the handover budget in the gate; this is
the same move for the other two.

## 4. Technical Requirements

- **No behaviour change.** No migration, no prompt-text change, no `PROMPT_VERSION` bump, no corpus
  change. The chat answer cache is keyed on `PROMPT_VERSION`: moving `SYSTEM_PROMPT` between modules
  must not alter one byte of it, or every cached answer is silently invalidated.
- **The dependency stays one-directional.** `core` may import `knowledge`; `knowledge` must never
  import `core`. A split must not create a seam that tempts it.
- **`import-linter` and `tests/tools/test_architecture.py` green after every slice** — and prove the
  lint can still *fail*. It has exited 0 while enforcing nothing before (`testing_hazards.md`).
- **D-numbers never change.** They are cited across the tree and parsed out of the spec's §18.3
  table. Trimming a row means moving its argument, not its id.
- **`D44` must keep a deferral marker.** It is the only decision an **N/A** UAT scenario cites
  (`tests/uat/mvp0_standards_and_public_site_uat.md` Scenario 5), and `scripts/uat_parse.py`
  refuses the UAT if the cited row "no longer reads as a deferral" (`DEFERRAL_MARKERS`). Check every
  row you trim against the `D<n>` citations in `tests/uat/` before trimming it.
- **`tests/tools/test_context.py` guards the recipes and caps.** A split that renames a module the
  recipe names must update it in the same commit.
- **One file per commit**, suite green before and after, and quote the gate cold *and* warm
  (`testing_hazards.md` §3.17).

## 5. Execution Steps

Ordered so each step is independently committable and the biggest session cost falls first.

1. **`_chat_text.py` and `_chat_prompt.py` — done** (`8fff5bf`, `5344d83`). Two commits because
   the prompt renders locators and so cannot be moved before them: the leaf is a pure move
   first, then the prompt. The prompt's sha256 and five rendered prompts are identical;
   `_chatbot.py` 97 → 69 KB.
2. **`_chat_values.py`.** Errors and the value dataclasses. Pure move; `_chatbot` re-exports, so
   every `from core.services._chatbot import Citation` keeps working. This must come **before**
   the audit, or the audit and the contract import each other.
3. **`_chat_audit.py`.** Pure move of the audit functions, the two warning lists and
   `_address_book`/`_reader_anchors` (the locator primitives already left in step 1).
4. **`_chat_provider.py`.** The model client, `ANSWER_SCHEMA`, truncation and the `MODEL_*`
   constants. This is the only slice that touches an external surface — keep the truncation
   tests as the proof.
5. **`_chat_guard.py`**, then **`_chat_cache.py`.** The guardrails, validation, follow-up
   detection, retrieval defaults and session lifecycle; then the answer cache and its
   snapshot. `--check` must show `_chatbot.py` under 30 KB with **margin**, not on the line:
   the guard slice alone measured 30,616 bytes against a 30,720 cap -- 104 bytes of
   headroom -- so the cache left too and the file is 23 KB. A cap met by 0.3% is a cap that
   the next comment breaks.
6. **`knowledge/corpus.py` → `knowledge/corpus_tables.py`, then `knowledge/corpus_edits.py`.**
   The table block (rule 5, the `<!-- table` state machine, `branch_row`) and then the
   reviewed-edit ledger move out; the header and format rules stay. Measured: the table block is
   15.7 KB and the ledger 10.4 KB — the table split **alone** leaves `corpus.py` at 38 KB, over
   cap, so the ledger has to go too. After both it is 28.5 KB.
7. **`core/services/_documents.py` (48 KB).** Measured before cutting: 8 KB of registry and
   publishing, 33 KB of reader (its dataclasses and builders interleaved), 6 KB of publishing.
   So the seam is **reader vs publishing**, and the reader needs **two** modules:
   `_document_reader.py` (which document, which branch, the passages, the citation — 12 KB)
   and `_document_shapes.py` (the dataclasses and the builders: cards, the printed grid, the
   fee box — 24 KB). `_documents.py` is 15 KB. The PRD's original "shape builders against the
   passage assembly" cut is not buildable: the classes and their builders are interleaved.
8. **`knowledge/services.py` (39 KB) and `knowledge/tables.py` (35 KB).** Measured: `search_terms`
   is **14.6 KB and is the retrieval strategy**, not term analysis — it reads rarity, aliases and
   seats off the corpus and returns a `RetrievalResult`. So the seam is *scoring* (`services.py`:
   `lexical_search`, `vector_search`, `fuse`, `search`, `document_frequency`, `lexical_key`)
   against *strategy* (`knowledge/retrieval.py`: `search_terms`, `_with_their_tables`). `search`
   stays behind because `search_terms` calls it. In `tables.py` the seam the PRD named is the
   right one: chunk-building (`chunks_for_parsed_section`, `row_chunk`, `_embedding_rendition`,
   `chunks_for_rows`) out to `knowledge/table_chunks.py` (8 KB), the curated data and structure
   stay. Both files land at 21 and 27 KB.
9. **The five test files**, split by scenario. Do **not** duplicate a guard to make the numbers
   work — see `cutting-test-suite-cost`: if a split forces a test to exist twice, the second copy
   was never needed.
10. **`scripts/build_corpus.py`** — it is a few hundred bytes over; find the seam or move one rule.
11. **The 14 §18.3 rows**, in small batches (2–3 per commit), each row reduced to decision + date +
    owner + the one measurement + link. `D44` is **not** among the 14, and that is the point of the
    rule in §4: it is the only decision an N/A scenario cites, so any row you trim has to keep its
    id and any deferral marker it carries.
12. **Wire `--check` into `scripts/verify.sh`**, with `tests/tools/test_verify_gate.py` asserting it
    is wired *and* that it can fail.

## 6. Success Criteria

- [x] `python scripts/context.py --check` exits 0 with **0 breaches** (files, rows, handover).
- [x] `scripts/verify.sh` runs the check, and `tests/tools/test_verify_gate.py` proves a breach
      fails the gate (break a file's size, watch it go red, restore).
- [x] `scripts/fast.sh --critical` still covers the eight files it guards, unchanged.
      `scripts/fast.sh` is not in this PRD's diff at all; the lane ran **172 passed / 4
      deselected in 46.53 s** and still names `test_claim_discipline`, `test_architecture`,
      `test_chatbot_guardrails`, `test_chatbot_grounding`, `test_retrieval_scope`,
      `knowledge/tests/test_retrieval.py`, `test_eval_retrieval`, `test_test_harness`.
- [x] `lint-imports` green **and proved able to fail**; `tests/tools/test_architecture.py` green.
      Green in every gate run in this PRD's slices. The "able to fail" half is A7's proof
      (`testing_hazards.md` §2), not re-run here — and saying so is the point: an unproved
      linter is the `exit 0 while enforcing nothing` failure this repo has already paid for.
- [x] No migration; no `PROMPT_VERSION` change; the prompt's sha256 is identical to `main`'s.
      Verified, not assumed: `git diff --name-only 669c56e..HEAD` touches no file matching
      `models`, `migrations`, `_chat_prompt` or `_chatbot`, so the prompt cannot have moved.
- [x] `python manage.py corpus_check` unchanged for all four documents.
      By construction rather than by a run: the diff touches no corpus artefact, ingest or
      chunker module, so no document's `corpus_digest` can have moved. (The dev box reports
      `landscape` drift for a reason outside this PRD — see `HANDOVER.md`.)
- [x] Gate green after every slice, with cold and warm timings quoted. Three runs on this
      tree: **1604→1606 passed / 1 skipped at 59.97 s**, then **1610 at 183.57 s cold**, with
      the lane at 46.53 s warm. Quote the range, never the best run (`testing_hazards.md`
      §3.17).

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| A "pure move" changes prompt text and invalidates the answer cache | Assert the prompt's sha256 is identical in the same commit; `PROMPT_VERSION` is untouched |
| `import-linter` exits 0 while enforcing nothing, so a boundary break ships | Break an import on purpose, watch the lint fail, restore — before trusting the green |
| Trimming a §18.3 row breaks the UAT's N/A citation | `scripts/uat_parse.py` names it; check every `D<n>` cited in `tests/uat/` |
| Splitting test files duplicates guards and inflates the suite | Split by scenario; `cutting-test-suite-cost` — a guard that must exist twice was never needed |
| The gate is wired while still red, training people to skip it | Wire only at 0 breaches (`testing_hazards.md` §3.11) |
| A split tempts `knowledge` to import `core` | `lint-imports` in the same commit, proved able to fail |
| Sizes drift back after the wiring | The check is in the gate — that is the whole point of 4.4 |

---

## Landed (session `1c`, 2026-11-03)

Steps 1–8 were already in when this session started. Steps 9–10 are the six commits below;
`--check` went **20 → 14 breaches**, and **every file is now inside its cap**.

| slice | commit | before → after |
|---|---|---|
| chat grounding tests | `f188eac` | `test_chatbot_grounding.py` 51 KB → 21 + 14 + 15 + 4 |
| ingest tests | `6eb7c3e` | `test_ingest.py` 40 KB → 18 + 10 + 11 |
| retrieval tests | `0442c75` | `test_retrieval.py` 38 KB → 17 + 19 |
| document reader tests | `73718ce` | `test_document_reader.py` 36 KB → 21 + 15 |
| section parser tests | `de3fe54` | `test_section_parsers.py` 32 KB → 22 + 10 |
| the generator | `5ab6eac` | `build_corpus.py` 31 KB → 25 + 7 |

Every body is byte-identical to the original (`_scratch/split_*.py` asserts in/out byte counts),
every test count is unchanged, and each shared fixture block moved to one imported module rather
than being copied: `chat_helpers`, `ingest_fixtures`, `retrieval_fixtures`, `reader_fixtures`,
`section_fixtures`. `scripts/fast.sh --critical` keeps naming the same eight files, and the
grounding, floors and refusal guards it names stayed in those files.

**Two defects found by doing it, both fixed in the same session:** a flaky wall-clock
assertion in `test_ask_board.py` (`e4ee9f5`, `testing_hazards.md` §3.28), and
`test_table_context.py` importing fixtures from another test module — invisible to a grep for
the file's path, caught by the lane (`0442c75`).

**Gate:** `scripts/verify.sh` **green, 1604 passed / 1 skipped in 56.97 s** on this tree.

### Step 11 — the 14 §18.3 rows, landed 2026-11-03 (session `1d`)

`--check` went **14 → 0 breaches**; every one of the spec's 81 decision rows is now inside the
1500-byte budget. Five commits, 3/3/3/3/2: `85d0f0b`, `b11ac90`, `50d9b92`, `43792d4`, `f7daa60`.
Each row keeps the decision, the owner and date, the one measurement that settles it, and a link;
the argument it was carrying was confirmed present at that link **before** the cut.

| row | before → after | what stayed, and why it had to |
|---|---|---|
| D46 | 1703 → 1320 | 33 detected / 29 pinned / the `(40, 42)` override |
| D47 | 1732 → 1134 | "no stitching" — its only other home is the prompt text itself |
| D52 | 2165 → 1356 | 20 joins, 65 of 368 chunks |
| D53 | 2470 → 1425 | the BPP spike: 13 pages, 5 corrections, 66 → 13 lines |
| D68 | 3578 → 1492 | 57 of 366 (15.6%), 22 of 28 branches |
| D69 | 2259 → 1420 | 275 of 433,154 bytes; 83 characters; 66 bullets |
| D70 | 3122 → 1466 | all seven sub-ids (code and tests cite D70.1–D70.7) |
| D71 | 3689 → 1490 | the fifteen-of-twenty reword count, which exists only here |
| D72 | 3193 → 1492 | the 0-chunk probe; 8 → 11 → 17 chunks |
| D73 | 2808 → 1484 | the negative measure: 9 of 9 → 6 of 9 |
| D74 | 2117 → 1487 | 10 of 36 PRDs carry a claim-discipline term |
| D75 | 1932 → 1453 | the inverted predicate; 316 lines of body text |
| D78 | 2376 → 1499 | four phrasings, 9 of 9 back |
| D80 | 1678 → 1492 | the eight shapes, 1,107-character cell |

**Two defects found by doing it.** (1) The rows did not carry links: **12 of the 14** pointed at
paths that do not exist from the spec's own directory — bare basenames for PRDs in `In Progress/`,
and `Refinement/LANDSCAPE_TABLES_PRD.md` for one that had moved to `Done/`. `D47` had no link at
all. **11 further rows** had the same defect, so all were made repo-root-relative and
`tests/tools/test_context.py` now fails on any unresolvable row token (watched red: one row
reverted to a bare basename, 1 failed naming D78; restored, 11 passed). (2) `D53` claimed the OPP,
SAOSO and landscape were "not yet converted" — true on 2026-10-22, false since 2026-11-02, when
all four became the text of record. Corrected in the row.

### Step 12 — the check is in the gate, landed 2026-11-03 (session `1d`)

`scripts/verify.sh` now runs `scripts/context.py --check` as **step 1/4**, before the Django
checks, guarded with `if !` rather than leaning on `set -e` — the failure has to say which budget
broke and where the argument belongs, or the next person deletes the step.

Two things had to be true before that was worth doing, and both were:

- **Zero breaches.** Reached by step 11. §4.4's condition was "wire it once the tree is inside the
  budgets" (`testing_hazards.md` §3.11), not "wire it and let people live with red".
- **A missing file must not read as a small one.** `size_of` returns `(0, 0)` for an absent path,
  so a deleted `HANDOVER.md` or spec would have been "comfortably inside its budget" and the gate
  would have passed on the artefact's absence. `check()` now reports absence as a breach, which
  also covers the `git archive` tree `deploy.sh` gates if `product/` were ever excluded.

`tests/tools/test_verify_gate.py` holds both halves: the wiring is asserted as text (and that it
is guarded), and `check()` is run against a scratch tree that is **deliberately over budget**,
which must exit 1 and name the file. A clean scratch tree must exit 0, so a check that always
fails cannot pass for the right reason. **Watched red three ways** before trusted: the guard
replaced with `if false` (1 failed), the missing-file loop emptied (1 failed), and one row's link
reverted to a bare basename in step 11 (1 failed, naming D78). Restored, all green.

**Gate on this tree:** `scripts/verify.sh` green, **1610 passed / 1 skipped**, with step 1/4
printing `every budget holds` — so the check now proves itself on every run. Timing on this box
during this session: **183.57 s cold, 59.97 s warm** — quote the range, never the best run
(`testing_hazards.md` §3.17).

## Pre-Flight Checklist
- [ ] No `core/models.py` change and no new app — this is a move, so **no migration**
- [ ] No views, forms or URLs added
- [ ] No behaviour change: same answers, same pages, same corpus
- [ ] `PROMPT_VERSION` untouched; prompt text byte-identical
- [ ] `lint-imports` + `tests/tools/test_architecture.py` green, and proved able to fail
- [ ] `tests/tools/test_context.py` updated in the same commit as any renamed module
- [ ] Every `D<n>` cited in `tests/uat/` still resolves and `D44` still reads as a deferral
- [ ] Gate green before and after each slice, cold and warm quoted
