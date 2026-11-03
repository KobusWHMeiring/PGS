# Session 1a — 2026-11-03 — the chat split lands, and `_chatbot.py` is 23 KB

**Task:** slice 1 of `CONTEXT_CUTS_PRD` — split `core/services/_chatbot.py` (97 KB against a
30 KB cap), the file a chat task opens on every session.

**Outcome:** the split is done. Seven modules, `_chatbot.py` at **23,760 bytes**, every
behaviour unchanged, and **24 breaches remain** in `context.py --check` (all PRD steps 6–11).
The PRD's own module table was provably wrong and is amended in the record; the reason is
below, because the next person will otherwise re-derive it.

---

## 1. The PRD's first table could not close

It proposed four modules and gave `_chatbot.py` "≈ 35 KB" — against the 30 KB cap the split
exists to satisfy. Measured from the real sections, three moves left **~36 KB**.

Worse, step 2 as written could not be built: `audit_citations` constructs a `Citation`, and
`Citation` lived in `_chatbot`. The audit importing the contract while the contract imported
the audit is a cycle; the value types had to leave first.

The amended table (in `CONTEXT_CUTS_PRD`, "Amended 2026-11-03") names seven modules and
quotes the section sizes it was derived from, so the remaining arithmetic is checkable:
errors+values 6.3 KB · audit 12.4 · generation 7.6 · lifecycle+guardrails 10.7 · contract
18.1 · cache 6.8.

## 2. What landed, in dependency order

| commit | module | from → to |
|---|---|---|
| `8fff5bf` | `_chat_text.py` (8 KB): tokens, `locator_of`, `text_sha`, `_normalise_ref` | 97 → 88 KB |
| `5344d83` | `_chat_prompt.py` (21 KB): `PROMPT_VERSION`, `SYSTEM_PROMPT`, `COST_QUESTION_RULE`, `looks_like_cost_question`, `significant_terms`, `build_prompt` | 88 → 69 KB |
| `6f6e1ff` | `_chat_values.py` (7 KB): errors, `Citation`, `ModelReply`, `GroundedAnswer`, `ChatModel` | 69 → 62 KB |
| `137edbf` | `_chat_audit.py` (14 KB): the audit, the two warning lists, `_address_book`, `_reader_anchors` | 62 → 50 KB |
| `e0203e2` | `_chat_provider.py` (10 KB): `ANSWER_SCHEMA`, `GeminiChatModel`, truncation, the output caps | 50 → 41 KB |
| `bcd4a45` | `_chat_guard.py` (13 KB) + `_chat_cache.py` (8 KB) | 41 → 23 KB |

Two ordering facts, both forced and both worth keeping:

- **text before prompt.** `build_prompt` renders `locator_of(chunk)`, so the leaf has to exist
  before the module that reads it. Step 1 is therefore two commits, not one.
- **values before audit, cache after guard.** The values are the floor (no `_chat_*` import at
  all). The cache was not in the plan's guard step; it moved because the guard slice alone
  measured **30,616 bytes against a 30,720 cap — 104 bytes**. A cap met by 0.3% is a cap the
  next comment breaks, which is exactly the "29.5 and hoping" outcome the PRD named as a risk.

Everything is re-imported through `_chatbot`, so no external import site changed: views,
forms, `_ask`, `_evidence`, the eval scripts, `__all__`, and
`test_chatbot_provider.py`'s `_chatbot.MAX_OUTPUT_TOKENS` drift guard all still work.

## 3. The proofs

- **The prompt is byte-identical.** `_scratch/probe_prompt_hash.py` hashes `SYSTEM_PROMPT`,
  `COST_QUESTION_RULE`, `ANSWER_SCHEMA` and **five rendered prompts** (plain, reviewed table,
  cost question, follow-up, table + history). Run before the first move and after every
  commit: identical every time, `PROMPT_VERSION` still `d79-2`. This is the guard against the
  silent failure that matters — the answer cache is keyed on the prompt version, so one
  changed space invalidates every cached answer without a single test going red.
- **The lint can still fail.** A `from core.models import ...` dropped into `knowledge/`
  exited `lint-imports` non-zero and named the contract; removed, 1 kept 0 broken.
- **One test had to follow the code.** `test_default_retrieval_passes_the_shipped_budget`
  monkeypatched `_chatbot.search_terms`, which `default_retrieval` no longer reads. Left
  alone it would have installed the spy where nothing looks — green, and proving nothing. It
  now patches `_chat_guard.search_terms`, with the reason in the test.

## 4. Numbers

Gate (`scripts/verify.sh`, `5433/pgs_verify`, `--create-db`), run once per commit:
**1598 passed / 1 skipped** every time; wall times **141.25 s, 223.41 s, 187.26 s, 126.50 s,
154.87 s** — the same tree inside one session varies by 97 s, so quote the range, never the
best run (`testing_hazards.md` §3.17). Critical lane: **217 passed / 4 deselected**, 36–57 s.
`lint-imports` green after every slice.

## 5. What is left

PRD steps 6–11: `knowledge/corpus_tables.py` (49 KB file), `_documents.py` (48), the
`services.py`/`tables.py` pair, the five over-cap test files (split by scenario), the §18.3
rows, then wiring `--check` into the gate **only at zero breaches**.

The chat split is the largest single read-set win: `_chatbot.py` was the file a chat task
always opened, and the recipe now opens a 23 KB contract, a 21 KB prompt, a 14 KB audit or a
10 KB provider depending on the question.
