# Session `1p` — 2026-11-05 — S3: the generator writes the block, and the page supplies the characters

**For:** the next agent.
**From:** the ingestion-engine S3 session (after `1o`'s composite, `1n`'s verification surface, `1h`'s
three arms).
**Tree:** `main`, two commits (`b26609a` the extraction field, `665b1fb` the emitter), plus this close.
**Branch state:** `git rev-list --count origin/main..HEAD` answered **2** before this session's commits;
everything before `1p` was pushed.

---

## 1. What the slice was, in one sentence

`INGESTION_ENGINE_PRD.md` S3: `scripts/build_corpus.py` must emit `<!-- table … -->` blocks itself,
from the composite §3.14 chose, guarded by rule 5's parser — and record the extraction mode on every
block it emits.

## 2. What landed

| Unit | What it does |
|---|---|
| `knowledge/proposals/` + `knowledge/table_proposals.py` | the arm's structure as committed data, found by the PDF's **sha256**; `reviewed.json` holds the fields no extractor produces |
| `scripts/propose_tables.py` | build-time reducer: cached Layout Parser response → structure JSON, with the banner; no credential, no rasteriser |
| `scripts/table_blocks.py` | the emitter: proposed structure → the body's printed lines → the page's characters → the block, or a refusal **by name** |
| `scripts/corpus_review.py` | the 30 KB-cap split: `apply_review`, `table_block_counts`, `table_loss_refusal` out of the generator |
| `scripts/corpus_pages.choose_pages` | the rendering choice as a pure function, so a test can build the generator's body from committed pages |
| `extraction:` on the block + **R1** | the mode is data on the artefact; `check_tables.py` judges the pass the artefact names, and `--pages-mode` is the draft-only escape |
| `tests/tools/test_new_document_ingest.py` | the DoD's seam: a `doc_key` the registry does not have, chunked with column meaning |

## 3. The measurements, quoted

- `python scripts/build_corpus.py --doc opp --force` → **`knowledge/corpus/opp.md` is byte-identical**
  (660 lines, `git status` clean). The block the emitter writes *is* the block a reviewer signed.
- `tests/tools/test_table_blocks.py::test_the_generator_reproduces_the_reviewed_fee_table_from_the_committed_pages`
  proves the same thing **without a PDF**: the body is built from `page_fixtures` through
  `choose_pages` + `assemble_body`, the proposal is the committed one, and the block equals the
  artefact's block line for line.
- `python scripts/check_tables.py --doc opp --rows 6` → `ok — 1 tables, 6 rows, 0 violations (layout
  pages, recorded on the artefact)`; `--doc landscape --rows 3,2,3` → `ok — 3 tables, 8 rows, 0
  violations (table pages, recorded on the artefact)`. **The mode is read from the artefact**, not
  from a flag.
- `python scripts/build_corpus.py --doc landscape --stdout` refuses two cells and keeps the prose:
  - `proposal 1, column 1: the printed column 'Key steps' is not a contiguous run of one of the page's printed lines`
  - `proposal 2, row 2, column 3: 'These two seals were developed by PGS SA …' is not a contiguous run of any printed line after the cell before it`
  Both are S5's: the landscape's page-4 table's rows are printed **before** the heading the
  de-columned page found, and the arm splits the merged fee box and reads the seal artwork.
- `scripts/fast.sh --critical` → **182 passed, 4 deselected in 45.33 s** (cold-ish on this box; the
  lane was 172 in ~40 s before `test_check_tables.py` joined it, and that file costs ~1 s).
- `python -m pytest -q --create-db` (the gate's own step, `DATABASE_URL=…5433/pgs_verify`) →
  **1820 passed, 1 skipped, 8 xfailed in 240.27 s**. The eight strict-xfail shape targets are byte
  unchanged (`git status` on `knowledge/tests/test_ingestion_shapes.py`: empty).
- `scripts/verify.sh` **cannot be quoted green from this tree**: step 1 fails on **another session's**
  `scripts/copy_deck.py` (32 KB). Steps 2–4 were run by hand and pass:
  `manage.py check` clean, `makemigrations --check` "No changes detected", `lint-imports`
  `knowledge must never import core KEPT` (185 files), then the suite above.

## 4. The decisions this session made, and why

1. **The extraction mode is a block field; the arm is build-time provenance.** Requirement 1 says the
   marker must be *checkable against the page*, and the pass is: R3 finds every cell line in the
   rendering the block names. The arm (`documentai-layout-v1.6-pro`) is not checkable by anything the
   gate can run, so it lives in the proposal's banner — a block field no consumer can verify is a
   comment. `EXTRACTION_MODES` is declared in `knowledge/corpus_tables.py` (a library may not import a
   test module) and `page_fixtures.MODES` is *asserted equal* to it.
2. **`GENERATOR` stays `v2`.** The field is additive, and a bump would mark the three artefacts a v3
   run cannot regenerate (the landscape's draft is the column soup by design) as stale — which is a
   different lie from the one the marker exists to prevent.
3. **Proposals are found by sha256, not by `doc_key`.** A reprint or rename finds nothing, which is
   the truth; a new standard needs no registry entry, enum or migration. This is the retarget rule
   (`build_principles.md` §I) made literal.
4. **A refusal is a warning, not an exit.** A document with one unemittable table is still worth
   drafting, and the operator's next command is the diff. The failure that must be fatal — a reviewed
   block disappearing — is already fatal in `main()` via S1's `table_loss_refusal`.
5. **The body's page comes from `build()`, not from the body.** A section's own page marker is emitted
   *before* its heading (`assemble_body(after=…)`), so a per-section consumer must be told the page
   (`testing_hazards.md` §3.32).

## 5. What is deliberately not done, and where each goes

| Open | Why not here | Closes in |
|---|---|---|
| The landscape's four declared structures: bullets (`•` the arm's `listBlock` drops), the merged fee box (the arm splits it across two rows), seal artwork (the arm reads the seal's text), the page-break row (the arm returns `Step 3` alone) | Each needs a declaration the harness cannot infer, and the de-columned page puts the table before its heading | **S5** |
| Appendix 6a's 20 rows and Appendix 7's four columns (Docling's role) | S5's stated scope | **S5** |
| A structure for a document outside the eight shape pages | Needs an arm run; this session may not re-open the key. The command is `scripts/propose_tables.py --pdf <new> --pages …` | the first real ingestion |
| `DocumentChunk` carrying the extraction mode itself | Requirement 1 is satisfied by the block that produced the row; a chunk field is a migration for a marker | only if retrieval ever needs it |
| The dev corpus refresh | `GEMINI_API_KEY` is in the shell, not in the repo `.env` — a refresh without it writes 17 NULL vectors (`deploy/README.md` §4) | whoever owns the key |

## 6. What this session lost time to (all four are in `testing_hazards.md`)

- **§3.32** a section body does not carry its own page marker → a per-section emitter refuses every
  row for a page it was never told.
- **§3.33** the landscape prints the same five column labels on every table page → a page-blind search
  resolves a header to the wrong table and blames the transcription.
- **§3.34** a guard proved red on an input that never reached the guard → the `attempted` test's input
  had none of the table's words, so the `absent` short-circuit fired first and the mutation stayed
  green.
- **Not in the hazard log, because it is this agent's shell, not the repo**: writing Python snippets
  through a heredoc twice collapsed `\n` escapes into real newlines inside test source. The fix is to
  put probes in `_scratch/` as files (`AGENTS.md` says so) and to edit test literals with the file
  tools, which carry text literally. Related: slicing `build_corpus.py` by **character offsets**
  computed before the file changed duplicated four functions; slice by **anchors**.

## 7. If you pick this up next

1. `python scripts/context.py --task corpus` and `--task backlog` (it will name S5).
2. Read `INGESTION_ENGINE_PRD.md` §3.15 (what S3 landed) and §5's S5 row.
3. S5 needs, in this order: the landscape's `page_break_row` proposal + four reviewed declarations,
   then Appendix 6a (20 rows) and Appendix 7 (Docling's four columns) through the harness.
4. Do **not** re-run the arms and do not re-open the key: the two claims that mattered are settled
   (§3.14) and the seven unjudged ones gate nothing.
5. `scripts/fast.sh --critical` after each edit; the gate's pytest step is
   `DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify .venv/Scripts/python.exe -m pytest -q --create-db`.
