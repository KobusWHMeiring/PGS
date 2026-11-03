# Session `1c` — the six remaining cuts, and every file is inside its cap

**Date:** 2026-11-03 · **PRD:** `product/backlog/In Progress/CONTEXT_CUTS_PRD.md` steps 9–10 (of 12)
**Gate:** `scripts/verify.sh` green, **1604 passed / 1 skipped in 56.97 s** · `--check` **20 → 14 breaches**

## What this session was for

Steps 1–8 of `CONTEXT_CUTS_PRD` were already landed: the chat split, and the five source-module
splits measured in the PRD. `python scripts/context.py --check` said **20 breaches** — five test
files, the corpus generator, and 14 §18.3 rows. This session took the six files. Every one is now
inside the 30 KB cap; the 14 rows are what is left.

## The method, and why it is not "split by line count"

Each file already says where its seams are, in headings the author wrote:

| file | seam the file itself named | before → after |
|---|---|---|
| `test_chatbot_grounding.py` | the answer path / the prompt contract / the turn / the artefact | 51 KB → 21 + 14 + 15 + 4 |
| `test_ingest.py` | the ingest / the corpus fixes / the reviewed artefact | 40 KB → 18 + 10 + 11 |
| `test_retrieval.py` | the search and its fusion / `search_terms` the strategy | 38 KB → 17 + 19 |
| `test_document_reader.py` | the reader page / the curated table branch | 36 KB → 21 + 15 |
| `test_section_parsers.py` | the parsers on fixtures / the parsers on a shipped page | 32 KB → 22 + 10 |
| `build_corpus.py` | what the artefact says / what its pages are | 31 KB → 25 + 7 |

Two rules held throughout:

- **The bodies are byte-identical.** `_scratch/split_*.py` slices the original by line range and
  asserts the reassembled bodies equal the source, in and out, as bytes. Nothing was reformatted,
  so every test name, docstring and comment is the same text it was.
- **A guard that would have to exist twice was not created.** The shared fixtures moved to one
  imported module per area — `chat_helpers`, `ingest_fixtures`, `retrieval_fixtures`,
  `reader_fixtures`, `section_fixtures` — rather than being copied into each new file. Imported
  autouse fixtures still fire (proved by §2.9 below).

Every file's test-definition count is unchanged (55, 52, 43, 46, 45), checked with a script rather
than by eye.

## The critical lane did not shrink by accident

`scripts/fast.sh --critical` names eight files for stated reasons. Two of them were split here, and
the rule applied was **the reason stays with the file it names**:

- `test_chatbot_grounding.py` is named for "the answer is grounded in retrieved passages, not
  memory". The refusal, the grounded answer, validation **and D46/D52** — the two live refusals
  whose cause was the corpus — stayed in it. What left is the prompt contract, the storage and the
  display. The critical lane now runs 24 of that file's 55 guards instead of 55; the property it
  is named for is untouched.
- `test_retrieval.py` is named for "the retrieval floors that pin `search_terms`' behaviour". The
  floors stayed; `search_terms`' own behaviour moved to `test_retrieval_strategy.py`.

This is recorded because the alternative — adding two files to the lane — would have changed the
eight-file budget the PRD holds fixed, and because the count drop is otherwise invisible.

## Two defects found by doing the work

**1. `test_table_context.py` imported fixtures from another test module.** It did
`from knowledge.tests.test_retrieval import opp_ingested, saoso_set`. Splitting
`test_retrieval.py` broke collection, loudly — but the import is invisible to a grep for the
file's path, which is how it survived the plan. It now imports
`knowledge.tests.retrieval_fixtures`. A split that introduces a shared fixture module should look
for these first.

**2. A wall-clock flake in `test_ask_board.py`** (`e4ee9f5`, `testing_hazards.md` §3.28).
`test_recording_is_idempotent_at_the_service_boundary` compared `last_asked_at` — written by the
call — with `timezone.now()` read *after* it. True only while both land in the same second: the
lane failed on it once, the test passed alone, and the lane passed twice after. The bound is now
captured before the call; watched red by adding five seconds to it.

## Evidence

- Bodies byte-identical: `_scratch/split_grounding.py` (48,984 bytes in/out),
  `split_ingest.py` (34,743), `split_retrieval.py` (33,233), `split_reader.py` (33,792),
  `split_section_parsers.py` (29,308), `split_generator.py`.
- Generator unchanged: `--doc landscape --stdout` and `--doc bpp --stdout` hash the same before and
  after (`965cede4…`, `2fab852f…`) — the same fingerprint method steps 6–8 used.
- `python scripts/context.py --check`: **20 breaches → 14**, and every remaining one is a §18.3 row.
- `scripts/fast.sh`: 1589 passed / 1 skipped / 15 deselected in **41.45 s** warm, twice.
- `scripts/verify.sh`: **1604 passed / 1 skipped in 56.97 s** cold (`--create-db`).

## What is left, and why it stopped here

**Step 11 — the 14 §18.3 rows.** Each row keeps its decision, date, owner, the one measurement and
a link; each row's argument has to be **confirmed present at that link** before it is cut. Three
already have a `product/design/` page (`d46_…`, `d68_…`, `d71_…`); the rest need the owning PRD's
"landed" section or evidence table. That is a reading task over artifacts, not a mechanical edit,
and 14 of them in one pass would be the exact "read the whole shelf" cost this PRD exists to
remove.

**Step 12 — wire `--check` into `verify.sh`, at zero breaches only** (§3.11), with
`tests/tools/test_verify_gate.py` proving a breach fails the gate.
