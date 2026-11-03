# PRD: The context cuts — a sentence and a link, and a file that fits its cap
**Status:** Ready
**Owner:** Build (no product decision is open; the rules are already decided in `CONTEXT_BUDGET.md`)
**Last Updated:** 2026-11-03
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
| `_chat_guard.py` | rate limit, `validate_question`, follow-up detection, retrieval defaults, session lifecycle | 11 KB |
| `core/services/_chatbot.py` | `answer_question`, the cache, refusals — **the contract** | ~27 KB |

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
5. **`_chat_guard.py`.** Rate limiting, `validate_question`, follow-up detection, retrieval
   defaults and session lifecycle. **`--check` must show `_chatbot.py` under 30 KB after this
   one**, with margin — 27 KB measured, not 29.5 and hoping.
6. **`knowledge/corpus.py` → `knowledge/corpus_tables.py`.** The table block moves; the header and
   format rules stay. `--check` must show both files under cap.
7. **`core/services/_documents.py` (48 KB).** No section headings, so name the seam first: the
   reader-shape builders (`_cards_for`, `_artefact_grid`, the fee-box derivation) are one
   responsibility, the passage/document assembly around them the other.
8. **`knowledge/services.py` (39 KB) and `knowledge/tables.py` (35 KB).** Neither has section
   headings either. The seams their own top-level names give: in `services.py`, retrieval proper
   (`lexical_search`, `vector_search`, `fuse`, `search`) against term analysis (`search_terms`,
   `document_frequency`, `lexical_key`); in `tables.py`, chunk-building from rows
   (`chunks_for_parsed_section`, `row_chunk`, `_embedding_rendition`) against the curated structure
   (`TableSection`, `ArtefactGrid`, `align_artefact_grid`). Both are only just over the line —
   prefer the smallest honest seam to a perfect taxonomy.
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

- [ ] `python scripts/context.py --check` exits 0 with **0 breaches** (files, rows, handover).
- [ ] `scripts/verify.sh` runs the check, and `tests/tools/test_verify_gate.py` proves a breach
      fails the gate (break a file's size, watch it go red, restore).
- [ ] `scripts/fast.sh --critical` still covers the eight files it guards, unchanged.
- [ ] `lint-imports` green **and proved able to fail**; `tests/tools/test_architecture.py` green.
- [ ] No migration; no `PROMPT_VERSION` change; the prompt's sha256 is identical to `main`'s.
- [ ] `python manage.py corpus_check` unchanged for all four documents.
- [ ] Gate green after every slice, with cold and warm timings quoted.

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

## Pre-Flight Checklist
- [ ] No `core/models.py` change and no new app — this is a move, so **no migration**
- [ ] No views, forms or URLs added
- [ ] No behaviour change: same answers, same pages, same corpus
- [ ] `PROMPT_VERSION` untouched; prompt text byte-identical
- [ ] `lint-imports` + `tests/tools/test_architecture.py` green, and proved able to fail
- [ ] `tests/tools/test_context.py` updated in the same commit as any renamed module
- [ ] Every `D<n>` cited in `tests/uat/` still resolves and `D44` still reads as a deferral
- [ ] Gate green before and after each slice, cold and warm quoted
