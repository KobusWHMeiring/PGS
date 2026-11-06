# PRD: The ingestion engine — from "a person reviewed this document" to "a suite checks every document"

**Status:** In Progress — **S0 and S1 landed 2026-11-03 (session `1e`); S2 is measured for three arms
(Docling §3.5/§3.8, the OpenRouter VLM §3.7, Document AI §3.9). §3.10 is the open item that gates the
choice: the eight-shape answer key is agent-authored and unreviewed, so the arms' ranking is not
established until the owner judges the cells. The surface that judgement happens on is built (§3.11,
session `1n`); it is waiting for the signature.** S3–S5 are open.
**Owner:** Corpus ingestion (sub-plan B), grounded chat (sub-plan D)
**Last Updated:** 2026-11-05
**Scope:** How a table becomes reviewed data when no human has reviewed it. In: extraction, its
verification, and the generator. Out: the reader's rendering (D70.1–D72), retrieval ranking (D79),
and the chatbot's answer shape (G11).
**Reference:** `product/design/g12_ingestion_generalisation.html` (the explored decision);
`PGS_PLATFORM_SPEC.md` §18.3 **D80** and **D75**; `product/backlog/In Progress/CORPUS_CANONICAL_FORMAT_PLAN.md`
(P4, D75); `knowledge/corpus.py` rules 1–6; `knowledge/tables.py`; `knowledge/table_chunks.py`;
`product/docs/context/testing_hazards.md` §3.25; `product/backlog/Done/LANDSCAPE_TABLES_PRD.md` §12.

---

## 1. Problem Statement

The corpus is defensible because a human typed every table into it. That is also why it cannot
grow: the engine's table coverage is *however many tables a person has transcribed*.

Measured on this tree, 2026-11-03 (no PDF, no database — artefacts and literals only):

| Fact | Value |
|---|---|
| Reviewed table rows carrying column meaning | **44** — OPP §2.3 **6** (artefact block, PDF 2), landscape **8** (three blocks, PDF 4–8), SAOSO Appendix 2 **30** (Python literals, printed pp. 76–78) |
| Reviewed rows that carry **no** column meaning | **20** — SAOSO Appendix 6a, held as `TableRow(substance=…, condition=…)` literals but chunked as `"Equines over six months old\n2"` with **empty** `embedding_text` |
| `<!-- table -->` blocks in the four artefacts | **4** — OPP 1, landscape 3, SAOSO 0, BPP 0 |
| Appendix 7's chunks | **4**, in `-layout` reading order: `"7 Use of sulphur dioxide, Sulphur dioxide,\n\npotassium bisulphite or …"` |
| Modules that assert a table shape | **10** (not 4) — of which `test_corpus_tables` (52 tests), `test_tables` (18), `test_landscape_table_block` (14), `test_row_blocks` (9) are the shape-level ones |
| Generator | `build_corpus.py --force` **destroys** a table block and exits 0 (`testing_hazards.md` §3.25) |

Two of those rows are live defects, not history: **Appendix 6a ships 20 chunks with no column
meaning** and **Appendix 7 is still interleaved**. Neither is caught by a test, because every test
asserts what a human already fixed. That sentence is the problem: **our coverage is a review, not a
mechanism.**

## 2. Strategic Goal

A document we have never seen can be ingested with its tables intact, and the corpus can *prove* the
cells it holds are the cells the paper printed — without a person typing the table. Concretely:
a new document's review is a diff over an extraction, not a transcription; the verification that
today exists only where a human worked exists for every table; and the two live defects close as a
side effect of that harness rather than as another hand review.

## 3. Proposed Solution

The decision is recorded (**D80**, product owner, 2026-11-02): **X2 now — a structure extractor emits
the artefact IR we already parse — and X3 (cite a region) when a document demands it.** X1 (generator
plus review) is not wasted: repairing the generator is X2's first slice. X4 (vision retrieval) breaks
the claim that a quote is characters we verified, so it is D70.2's fallback, never the plan.

Three concerns are welded together in today's design and must be separated (exploration Part 2):

| Concern | Today | Under X2 |
|---|---|---|
| **Extraction** — getting structure out of a page | a human, per table | a structure model drafts; a human reviews a diff |
| **Verification** — proving the structure is the page's | the same human, by eye | asserted: cell fidelity, row count, header association, spans |
| **Citation** — what a quote is | a substring of the artefact text | unchanged; a quote is still characters we verified |

That is why X2 is the recommendation: it is the only option that needs no new claim. The quote stays
checkable characters.

**The artefact IR is already the right shape for an extractor's output.** `<!-- table cols: … -->`,
`<!-- row: … -->`, `<!-- cell -->`, `<!-- row-divider: … -->` already carry columns, rows, cells,
empty cells and qualifiers, and rule 5 already **raises** rather than guessing. X2 writes that block
from an extraction; it does not invent a second format.

### 3.1 The eight shapes, and which of them already have a test — measured, not inherited

Every shape is already in our corpus (exploration Part 1). "Test?" is an **existing** assertion, and
"input" is what that assertion reads: a *review* (a human's fix, already applied) or the *shape*
(the page as it arrives).

| # | Shape | Where | Test today? | Its input | What the engine must learn |
|---|---|---|---|---|---|
| 1 | Numeric row, no labels | OPP §2.3, 6 bands | **yes** — `test_corpus_tables.py::test_a_row_is_embedded_from_its_column_labels_not_its_cells`, `test_ingest.py:246` | reviewed block | nothing structural; the `embedding_text` rendition exists. It must survive X2 *by construction* |
| 2 | Header lost entirely | SAOSO Appendix 6a, 20 rows | **no** | — | associate a printed header with the values beneath it. Today the chunk is `"Equines over six months old\n2"`, embedding empty, and `test_corpus_saoso.py:265` asserts the *values* are present |
| 3 | Column-major interleaving | SAOSO Appendix 7, rows 1–6b | **no** | — | de-interleave a `-layout` page into rows. `test_ingest_transforms.py:106` proves only that a *reviewed* row set replaces an interleaved chunk |
| 4 | Very long cell | landscape Step 3, **1,112** characters | **yes** — `test_landscape_table_block.py::test_every_cell_line_is_a_verbatim_run_of_its_own_printed_table`, `::test_the_picture_column_holds_a_label_and_never_prose` | reviewed artefact | a cell is a paragraph: keep it whole, and never let it become a column |
| 5 | Deliberate empty cell | landscape, **12** empty cells | **yes** — `test_corpus_tables.py::test_an_empty_cell_is_recorded_as_empty_never_as_missing`, `::test_a_row_with_an_empty_cell_does_not_label_the_silence`, `test_row_blocks.py` (a row with no condition gains no paragraph) | reviewed block / literals | distinguish *absent* from *empty*, and never fill from the cell above |
| 6 | Row across a page break | landscape Steps 1–2 on PDF 4, Step 3 on PDF 5 | **yes** — `test_landscape_table_block.py::test_a_row_belongs_to_the_page_it_starts_on`, `test_tables.py::test_the_seaweed_condition_crosses_the_page_break` | reviewed artefact / page text | one row, two pages: no half-rows, no row on the wrong page |
| 7 | Two-level qualifier | Appendix 2, "South African specific" between rows; `I. PLANT AND ANIMAL ORIGIN` | **yes** — `test_corpus_tables.py::test_a_row_divider_is_recorded_against_the_row_beneath_it`, `core/tests/test_document_reader_curated.py` | hand-authored `TableDivider` | derive a divider from a page: it is not a row and not a heading |
| 8 | Picture in a cell | landscape seals table | **yes** — `test_landscape_table_block.py::test_the_seal_cell_carries_the_printed_label_not_the_picture` | reviewed artefact | detect non-text in a cell; record the printed label and *say* the artwork is not stored |

**Six of eight have a test. Zero of eight has a test whose input is the shape.** The two that have
none are exactly the two live defects. That is the whole generalisation problem stated as a
measurement, and it is what S0 makes machine-checkable.

### 3.2 What S0 landed (2026-11-03): the fixture set

- `knowledge/tests/shape_fixtures.py` — eight `ShapeCase`s. Each names its **source** (governed doc,
  PDF page, printed page), an **anchor** (verbatim lines that prove the page is the page), the
  **expectation** (columns, rows, pages, empty cells, dividers, artwork note) and the **gap** (what
  the engine must learn). The page text is **not copied**: it is read from the committed page
  fixtures (`knowledge/tests/page_fixtures.py`), whose extractor banner and PDF sha256 are pinned in
  `MANIFEST.json`. One copy of the paper, one provenance chain.
- `knowledge/tests/test_ingestion_shapes.py` — provenance and audit tests (green) plus one
  **strict-xfail** target test per shape, so the gap is counted in every run (`8 xfailed`) and a
  shape that starts passing fails the suite (`XPASS(strict)`) until the marker is removed.
- The audit is asserted, not narrated: a test fails if the set of shapes without a shape-level test
  stops being exactly `{headerless_values, column_major}`, so a later claim of coverage has to be
  earned.

### 3.3 What S1 landed (2026-11-03): the generator's table-block guard

`build_corpus.py --force` on a document whose artefact carries a table block now **refuses** before
writing, naming the block count and the sections, instead of replacing the review with column soup
and exiting 0 (`testing_hazards.md` §3.25). `--discard-tables` is the explicit, named override; it is
not spelled `--force`, because the whole point is that `--force` may not mean "delete the review".

### 3.4 What S4 landed (2026-11-03): the harness, and the two things it cannot infer

`knowledge/table_harness.py` implements requirements 2-7 as one check over a parsed document:
`check_table()` per table, `check_document()` over a whole artefact, returning named `Violation`s
(`R2`-`R7`). `scripts/check_tables.py` is the gate, and `knowledge/tests/test_table_harness.py`
is the proof: **the four reviewed tables (14 rows) pass every requirement that can be checked**, and
there is **one mutation per requirement** that the harness names (a table with no columns, a cell
that is not on its page, a cell whose lines are out of order, a wrong and an undeclared row count, a
fabricated cell, an omitted cell, a divider claimed twice, a lost glyph, an annotation that reached a
cell). Two guards were broken and watched go red before being trusted.

**Two things the harness refuses to guess, and both are declarations:**

- **The row count.** A page cannot say how many rows it prints in machine-readable form, so R4 takes
  `--rows` (`check_tables.py`) or `expected_rows` (`check_document`). A count that was not declared
  is reported as a violation, not as a pass — and `expected_tables` makes a document whose block
  went missing fail instead of passing with nothing to check.
- **The extraction mode the cells came from.** Measured: the landscape's tables pass against
  `-table` pages and fail 10 ways against `-layout`, so the mode is real information, not a
  preference. Today it is a flag; **S3 is where the generator records it on the artefact**.

**R3 was generalised by measurement, not by preference.** The strict reading — a cell's line is a
contiguous run of *one printed line* — is right for a single-column page and fails on the
landscape's `-table` output, where two cells share a printed line, and on a word the paper hyphenates
across the break (`self-` / `assessment`). Measured 2026-11-03: the strict rule reported 3 cells, all
wraps, none a lost or reordered word. So a cell line is matched inside one printed line, and if that
fails it is split at its own hyphen and **both halves must be printed lines, in order**. Joining
every line instead would weaken R3 to "the words appear somewhere", which is what it exists not to
be. A shared cursor across a row's cells was also measured and dropped (171 false violations): the
landscape's fee box is one printed box filed under the row it starts beside.

**What the harness cannot see, and says so.** A table that is not a `<!-- table … -->` block is not
checked at all — Appendix 6a's 20 rows and Appendix 7's interleaved chunks are invisible to it, which
is why `expected_tables` exists and why S5 is still the work that closes them. The harness asserts
requirements, not shapes: the eight `read_table()` targets in `test_ingestion_shapes.py` still
wait for S2's reader.

### 3.5 What S2 measured (2026-11-03): Docling scores 0 of 8 as extracted (1 of 8 with a header
convention), and the gaps are the ones the requirements predicted

Run: `scripts/eval_extractors.py` against the eight shapes, **docling 2.146.0** on Python 3.13.3, on a
laptop CPU, at Docling's own defaults — measured, not assumed: `TableFormerMode.ACCURATE` with
`do_cell_matching=True`, i.e. its high-quality path, not its fast one. Instrument and output are
committed: `product/docs/evidence/2026-11-03_s2_docling_scores.json`.

Every shape is scored twice, because the tool marks no cell as a column header on any page we gave it:
`as extracted` (the strict reading) and `once row 0 is taken as the header` (a one-line convention).
Both columns are published; a tool that needs a convention is a different finding from one that cannot
pass.

| Shape | Table found | Grid | Strict | With row 0 as header | The failure, named |
|---|---|---|---|---|---|
| Numeric row, no labels (OPP) | yes | 7x3 | fail | **pass** | none in the grid: it is exact, and only the header is unmarked |
| Header lost entirely (6a) | yes | 21x2 | fail | fail | the two printed header labels **merged into one cell**; and `Other bov ine animals` — a word split inside itself |
| Column-major interleaving (App 7) | yes | 8x5 | fail | fail | an extra leading column (the paper's row numbers, useful) and a condition cell lost |
| Very long cell (landscape p5) | **no** | — | — | — | **no table detected**: the page's text comes back as headings and 2 pictures |
| Deliberate empty cell (p4) | yes | 3x6 | fail | fail | the five-column grid split into six; the fee `R500` and `Proud member of` are lost |
| Row across a page break (p4-5) | partly | 3x6 on p4 | fail | fail | the rows that continue on p5 are a second table and were not returned |
| Two-level qualifiers (App 2) | yes | 14x2 | fail | fail | both divider labels became **rows** (2 extra); nothing marks a divider as a divider |
| A picture in a cell (p6) | **no** | — | — | — | **no table detected**: 2 pictures, text as headings |

**0 of 8 pass as extracted; 1 of 8 passes once row 0 is taken as the header; 2 of 8 tables are not
detected at all.** Rows and columns are usually *found* (6a: 20 of 20 rows, 2 of 2 columns), so this is
not a tool that cannot see — it is a tool whose structure loses exactly what requirements 2, 4 and 6
name: **header association, spanning/merged cells, dividers, page-break rows, and non-text**.

Speed, quoted as the range because it was measured twice on the same box with the same verdicts:
**163 s total** on a quiet run, **330 s** on a busy one — 7-14 s per SAOSO page, 19-58 s per landscape
page, 45-108 s for the two-page shape. The runner reuses one converter, because the first version built
one per shape and the model load landed inside every timing.

**What this triggers.** D81's threshold was "Document AI only if Docling loses spans, qualifiers or
header association on three or more of the eight". It loses all three, on more than three. So the next
step is **Document AI — which needs a Google Cloud project, billing, a processor and a service-account
key, and therefore the owner**, not an agent. That is where S2 stops until those exist.

**What this does not say.** One version, one laptop, one run per shape. A newer Docling, a different
pipeline (OCR off, `fast` table mode), or a page-range quirk could move a cell or two — and none of it
would change the shape of the result: the failures are structural, not marginal.

### 3.6 S2b (run 2026-11-04): the other arms, and what each actually needs

Docling is one arm. §3.5 says "not good enough", not "give up", and the field has more than one
candidate. What each needs, verified on this box on 2026-11-04:

| Arm | What it is | What it needs |
|---|---|---|
| **Local open-source parsers** — Unstructured (`hi_res`), Marker, MinerU, PaddleOCR PP-Structure | pip install, layout + table models, no account | nothing but disk and time |
| **VLM via OpenRouter** — its public catalogue listed **455 models today, 310 accepting image input and 188 accepting a PDF/file** (read from the API, not from memory) | a generative model asked for the table as JSON | the existing `OPENROUTER_API_KEY` |
| **VLM via Gemini** — `gemini-2.5-flash` and family answered **HTTP 200** with the key in this session | the same | the existing `GEMINI_API_KEY` |
| **Azure Document Intelligence, AWS Textract, hosted OCR (e.g. Mistral OCR)** | the extractive class Document AI belongs to | a subscription and a key each; free tiers exist but were **not read here** |
| **Document AI** | the ceiling candidate D81 names | GCP project + billing + processor + **service-account key** |
| **None — hand-review the 24 chunks** | closes the two live defects, generalises nothing | nothing |

**A Gemini API key is not a GCP credential.** Verified in one minute: the key answers **200** on
`generativelanguage.googleapis.com/v1beta/models`, and the *same* key gets **401** on
`documentai.googleapis.com/.../processors` — *"API keys are not supported by this API. Expected OAuth2
access token or other authentication credentials that assert a principal."* A key is a bearer token for
one API; a Cloud API wants a principal with IAM roles. They can share a billing account and still be
different doors.

**This repo's state is subtler than "we have no credentials":** `.env` holds only `DJANGO_SECRET_KEY`,
while the *session environment* holds `GEMINI_API_KEY` and `OPENROUTER_API_KEY`. Django scripts see the
first; an agent shell sees both. Say which one is meant.

**The rule that governs every generative arm.** A VLM writes the text it believes it read, so a wrong
digit looks identical to a right one. R3 is the answer and it is already built: a cell that is not a
contiguous run of the page is a violation. A VLM arm is therefore admissible **when its cell text is
taken from an extraction pass rather than from the model's prose** — the model proposes the grid, the
characters come from somewhere checkable. That hybrid is the only form in which a generative model
enters a corpus whose claim is that a quote is characters we verified.

**What S2b must produce:** the same table as §3.5, for each arm, scored by the same `mismatches()`.
None of this is a reason to adopt; it is a reason to measure.

### 3.7 What S2b measured (2026-11-04): the OpenRouter VLM arm scores 2 of 8, and the failures move

Run: `scripts/eval_openrouter.py` — committed, and the gate never needs it. Instrument and output:
`product/docs/evidence/2026-11-04_s2b_openrouter_scores.json`. Two models, three prompt forms, all
eight shapes: **48 calls, $0.55 total** (priced by the provider per call, not from a price list).
`google/gemini-3.1-flash-lite` and `anthropic/claude-sonnet-5.5`, at `temperature: 0`, 200 dpi page
images, one image per printed page of the shape.

**The catalogue is a moving list, so it is quoted with its timestamp.** Read from
`/api/v1/models` on 2026-11-04 at 11:24: **419 models, 276 accepting image input, 154 accepting a
file/PDF** — §3.6's 455/310/188 was the same endpoint earlier the same day. The key was live
($50 limit, $0 spent) and the arm needed nothing else: no account, no venv, no download.

**The rule, implemented three ways, because the rule has three readings.** All three send the page
image; what changes is who supplies the characters.

| Form | What the model returns | Where the characters come from |
|---|---|---|
| `lines` | each cell's printed lines, copied verbatim | the **page**, checked line by line (a paraphrase is a violation) |
| `anchors` | each cell's first and last words | the **page**, sliced between the anchors — the faithful reading of §3.6's rule |
| `indices` | line numbers only | the **page**, by construction: the model never emits a character |

| Model | Form | Pass | Grid only (quotes unresolved) | Tables found | Rows right | Columns right | Cost | Wall |
|---|---|---|---|---|---|---|---|
| gemini-3.1-flash-lite | `lines` | **1/8** | 2 | 8/8 | 7/8 | 8/8 | $0.012 | 39 s |
| gemini-3.1-flash-lite | `anchors` | **2/8** | 0 | 8/8 | 8/8 | 8/8 | $0.012 | 40 s |
| gemini-3.1-flash-lite | `indices` | 0/8 | 0 | 8/8 | 7/8 | 8/8 | $0.011 | 38 s |
| claude-sonnet-5.5 | `lines` | **2/8** | 1 | 8/8 | 7/8 | 7/8 | $0.164 | 64 s |
| claude-sonnet-5.5 | `anchors` | **1/8** | 0 | 8/8 | 7/8 | 7/8 | $0.148 | 55 s |
| claude-sonnet-5.5 | `indices` | 0/8 | 0 | 7/8 | 7/8 | 7/8 | $0.199 | 84 s |

**The best VLM cell is 2 of 8; Docling was 0 of 8 as extracted (1 of 8 with a header convention).**
Up to sixteen times the price bought nothing — the expensive model is not better than the cheap one, and no
form dominates — so this is a finding about the *task*, not about a vendor. The arm is **4–8× faster**
than Docling on the same box (5 s/shape vs 20–40 s), which is the one axis where it clearly wins.

| Shape | Docling | Best VLM | The failure, named |
|---|---|---|---|
| Numeric row, no labels (OPP) | pass* | **pass** (3 forms) | none — and `indices` fails it, see below |
| Header lost entirely (6a) | fail | fail | the two printed header labels merged into one column's label (`Maximum number of animals per ha Class or species`); the letter-spaced row is reported, not silently rejoined |
| Column-major interleaving (App 7) | fail | fail | the paper's row number becomes an **extra leading column** and every cell shifts right — Docling's exact failure, from a completely different mechanism |
| Very long cell (landscape p5) | **not detected** | fail | the model **over-includes** ('Step 3 The group conducts farm visits…') and re-wraps the 1,112-character cell at its own width (4–11 quote violations) |
| Deliberate empty cell (p4) | fail | fail | the merged fee box is **replicated into the row below**, and `Proud member of` — the label printed beside the seal — is lost |
| Row across a page break (p4-5) | partly | **grid only** | 3 rows on pages 4, 4, 5 and 5 columns are right; the quotes do not resolve, so the characters would have been the model's |
| Two-level qualifiers (App 2) | fail | **pass** (`anchors`, flash-lite) | none — 11 rows and all 3 dividers, which is the one shape where the arm **beats** Docling outright |
| A picture in a cell (p6) | **not detected** | **pass** (`lines`, sonnet) | none |

**What this says, and it is not "try another vendor".** The arm **finds every table** (8/8, against
Docling's 6/8) and gets **header association right on 7–8 of 8 shapes** — the requirement Docling lost
completely, because Docling marks no cell as a column header on any page. It also proposes **dividers**,
which no layout model returns. So the failure has moved: it is no longer "the tool cannot see" but
**"the tool cannot be trusted with characters, or with where a cell ends"**. Those are exactly the two
things requirement 3 and requirement 9 exist to refuse, and the arm's three forms measure them
directly: transcription fails on wrapped cells, anchors fix the characters but leave the boundary to
the model, and line numbers cannot separate cells at all.

**The blocking finding is about our extraction pass, not the model.** The `indices` form scores 0 of 8
because a printed line in `-layout`/`-table` text **is a whole row**: `Below R 250,000 1,500 900` is
one line, so no set of line numbers can ever produce three cells from it. The arm is therefore
admissible only once the engine has a pass with **cell granularity** — which is the thing the engine
is being built to produce. In `anchors` mode the same defect appears from the other side: on Appendix
7, where the pass interleaves four columns, **no cell has a contiguous run on the page**, so every
cell is a violation whatever the model does. A VLM cannot repair an interleaved pass; it needs a
row-structured one. **(Corrected 2026-11-04, §3.8: that last sentence is too strong — the `lines`
form resolves per printed line, which *is* contiguous on an interleaved page, and its Appendix 7 grid
is right once the row-number gutter is declared.)**

**Speed and cost, quoted as measured.** 5 s and $0.0015 per shape for the cheap model, 7–10 s and
$0.019 for the expensive one, against Docling's 20–40 s per shape. Cheap enough that cost is not the
argument either way; the score is.

**What this does not say.** One run per shape per cell, one day, one key. `temperature: 0` is not a
guarantee of identical output across providers, so the instrument **caches the raw response** per
(model, shape, dpi, form) and can re-score without buying a new sample — every number above was
re-scored from that cache, unchanged, after the resolver was fixed and after the instrument was split
in two. The cache is 332 KB and is not committed (it lives in `_scratch/`); a fresh clone re-runs the
48 calls for about $0.55. And a shape failing here is not proof
that no VLM can pass it: three prompt forms is a small space, and the two failures that look most like
model judgement (`Proud member of`, `Step 3`) are boundary calls a human reviewer made in the fixtures
and could reasonably make differently.

### 3.8 What §3.7 got wrong (2026-11-04, same session): the pass was the smaller half, and one mapping convention was the bigger one

Three follow-up measurements, all from the **cached** model answers — no new call, so nothing here was
bought:

**1. A different pass does not rescue anything.** `scripts/eval_openrouter.py --text-mode other`
re-scores the same answer against the pass the shape does *not* declare. It never improves a verdict,
and it makes three shapes worse: `empty_cells` 0 → 11 quote violations (sonnet, `lines`),
`page_break_row` 6 → 17, and flash-lite's `qualifier` `anchors` pass demotes to grid-only. **The
declared pass is already the better of the two available passes for every shape**, which is the same
thing S4 found from the other direction (the landscape passes against `-table` and fails 10 ways
against `-layout`).

**2. A row-structured pass cannot be built from the committed text at all.** Looking at Appendix 7's
`-layout` page is decisive: the gap between two columns **collapses to a single space when a cell
overflows**, so line 9 prints `1 Aeration or oxygenation Air,` — there is no gutter to split on, and
no character-offset de-interleaver can recover the cells. De-interleaving needs **per-word geometry**,
which neither committed pass carries. So "re-score `anchors` against a row-structured pass" is **not a
performable experiment with what is committed**; it needs a pass with word boxes (Document AI supplies
them; Docling supplies them and our mapping discarded them).

**3. One declared normalisation flips Appendix 7 — and it was our defect, not the tools'.** The paper
prints a bare row number (`1`, `6b`) beside each row. Both arms read it as a fifth, leading column,
which shifted every cell. `--row-number-gutter` drops a bare leading row number from a row that
carries exactly one cell more than the header (a real first column, `1 Aeration or oxygenation…`, is
never touched — the rule is narrow and tested). With it declared:

| Arm | Before | After | What is left |
|---|---|---|---|
| VLM, flash-lite, `lines` | fail, 5 mismatches | **grid correct** (7×4, cells exact) | **one** quote violation: the model wrote `70°C` where the page prints `70oC` — R3 doing exactly its job |
| VLM, sonnet, `lines` | fail, 6 mismatches | **pass** | nothing |
| **Docling 2.146.0** | "extra leading column, a condition cell lost" | **pass** | nothing — `rows 7/7, cols 5/4`, gutter took out 7 rows |

**Both arms are now scored with the same instrument and the same declared normalisation**
(`scripts/eval_extractors.py` carries it too; evidence
`product/docs/evidence/2026-11-04_s2_docling_gutter_scores.json`, 281.7 s on this box). Docling's
Appendix 7 grid was **right all along** — its geometry de-interleaved the four columns correctly, and
the only defect was our counting the paper's row-number furniture as data.

**4. The two arms pass *different* shapes, and the union is 4 of 8.** With every reading published:

| Arm | Full passes | Which |
|---|---|---|
| Docling 2.146.0 | **2/8** | numeric_row (row-0 convention), column_major (gutter) |
| VLM flash-lite `lines` | 1/8 (+3 grid-only) | numeric_row |
| VLM flash-lite `anchors` | **2/8** | numeric_row, qualifier |
| VLM sonnet `lines` | **3/8** | numeric_row, column_major (gutter), artwork_cell |
| VLM sonnet `anchors` | 1/8 | numeric_row |

Union of everything any arm passes: **numeric_row, column_major, qualifier, artwork_cell — 4 of 8.**
**(Corrected 2026-11-05, §3.12: the re-score against the signed key makes it **5 of 8** — the Layout
Parser reads the long cell end to end, and that shape was our key's defect, not the tools'.)**
Never passed by any arm, under any convention: **headerless_values** (the header is printed once,
split across four lines, with the second column's continuation printed beneath it), **long_cell** (a
1,112-character cell whose boundary no reader agrees on), **empty_cells** (a merged fee box plus a
label printed beside a seal), and **page_break_row** (right grid, characters not verified).

**What this changes.** The best arm is the VLM at 3 of 8 and the failures that remain are **semantic,
not structural**: which printed lines are one header, where a paragraph-sized cell ends, and whether a
label belongs to the artwork beside it. Those are judgements a human reviewer made in the fixtures.
So the extractor choice is now clearly *not* the load-bearing decision: **a credential would have to
beat a union of four, and the three it would still lose are the three no general extractor returns.**
**(Corrected 2026-11-05, §3.12: it is a union of five, and only three are left — one of which is our
key and one our pass. The credential argument itself stands unchanged.)**
The order of work is S3 (emit the blocks, record the extraction mode) and S5 (re-review 6a and 7
through the harness), with the arm's `lines` form as a **proposer** whose output the harness checks —
not as an authority.

### 3.9 What S2 measured (2026-11-04): Document AI, on the owner's project — and the credential bought the answer

The owner created a project with a **Form Parser** and a **Layout Parser** in `us`; authentication is
**Application Default Credentials** (a user credential from `gcloud auth application-default login`),
so **no service-account key exists and nothing entered the repo**. `scripts/eval_documentai.py` scores
it with the same `mismatches()`, publishing `as_extracted` and `with_row_number_gutter` like the other
two arms, and caching every raw response so a key fix re-scores for free.

**The default versions are old, and that matters.** The Form Parser defaulted to
`pretrained-form-parser-v2.0-2022-11-10` and the Layout Parser to
`pretrained-layout-parser-v1.0-2024-06-03`. Both were re-run on the current deployed versions
(`v2.1-2023-06-26`, `v1.6-pro-2025-12-01`) because **a score without its version is not evidence** —
the same rule that made the Docling arm record `2.146.0`.

| Processor | Pass | What it does with the eight shapes |
|---|---|---|
| **Form Parser v2.1** | **1/8** (numeric_row) | Appendix 7 comes back as **17 ragged cells in one row** — it does not de-interleave. Landscape p4 returns **no table at all** (28 blocks, 1,928 characters of text, no table). Appendix 2's dividers become rows (21 rows for 11). Landscape p5: 29 columns. |
| **Layout Parser v1.6-pro** | **2/8** (numeric_row, artwork_cell) | **8 of 8 tables found** — the best structure of any arm — but 30–75 s per page (495 s for the eight). Its failures are *near misses*: Appendix 6a 20 rows/2 cols with **one** mismatch, the long cell 1 row/5 cols with **one**, and Appendix 7 right once the gutter is declared. |

**Its characters are not ours, and that is a finding about "extractive".** The Form Parser re-OCRs the
page rather than reading the embedded text layer: on Appendix 7 it returned
`No more than 1~g/|` where the paper prints `1 g/l`, and `0,6~mg/l` for `0,6 mg/l`. **57 cells across
the eight shapes do not resolve against our committed page pass.** So the argument that an extractive
tool's characters are safe by construction is **wrong** — it does not *invent* text, but it *misreads*
it. R3 catches this, which is the instrument earning its keep.

**A wrong result, recorded as a hazard.** The first Layout Parser run scored **0 of 8, "no table found"
on every page**. That was **our bug**: the Layout Parser returns a *hierarchy* (`textBlock.blocks[]`
nested under its heading, `tableBlock` inside, cells as `blocks[].textBlock.text`) and **no
`document.text` at all**, while the Form Parser returns `pages[].tables[]` with text anchors. Reading
one shape scored the other processor as blind. Corrected, the Layout Parser's numeric_row is a clean
pass. *Read the response before believing the score.*

**The three arms agree with each other and disagree with our key, on the same shapes.** That is the
strongest evidence yet that the key, not the tools, is the open question:

| Shape | Docling | VLM (sonnet, `lines`) | Layout Parser v1.6-pro | Our key |
|---|---|---|---|---|
| Appendix 6a header | merged the two labels | merged them the same way | **merged them the same way** (`Maximum number of animals per ha Class or species`) | two labels: `Class or species` \| `Maximum number of animals per ha equivalent…` |
| Long cell, p5 | not detected | `Step 3 The group conducts farm visits…` | **the same `Step 3` prefix** | cell starts `The group conducts farm visits` |
| Page-break row | one page only | 3 rows, characters unverified | **4 rows** — the repeated header counted as a row | 3 rows, pages 4, 4, 5 |

Three readers of the same paper, built on completely different principles, making the **same** call
against us is a reason to re-read the key — not to mark them all wrong. The page-break case has a third
explanation (the page restarts the table with its header, which is a normalisation like the gutter), and
that is exactly the kind of rule a reviewer should decide rather than an agent.

**Cost and speed, measured:** 9 pages per processor, 18 pages total, well under a dollar; Form Parser
7–14 s/page, Layout Parser 30–40 s/page. One long run died mid-flight with `WinError 10053` after 10 of
16 calls, so the runner now retries and caches.

### 3.10 The finding that outranks all three arms: **the answer key is agent-authored and unreviewed**

Asked, mid-session, whether any human had ever validated a table, the owner said no. Checked:

* **`knowledge/tests/shape_fixtures.py`** — the expected columns, cells, row counts and dividers for all
  eight shapes — was written by commit `5c45550` *"D80 S0: the eight-shape fixture set"*, i.e. **by an
  agent**. Its expectations are *anchored* (every string is proved to be on the page) but the
  **groupings are one agent's reading**.
* **`tests/uat/landscape_tables_uat.md` is genuinely signed** (Kobus, 2026-11-01, re-signed 2026-11-03,
  6 PASS) — but its six scenarios are *the fee question, a card you can scan, the fork reads as a fork,
  the comparison as a spreadsheet, a real phone in daylight, what the pages refuse to claim*. **Every
  one judges how it reads. None asks whether a cell's characters are what the paper prints.** The
  cell-verbatim check that exists is listed as *automated coverage* — explicitly "not shown to the
  reviewer as work".

**So a "pass" means "agrees with our grouping", not "matches the paper".** The two halves separate
cleanly:

* **Characters are verified.** R3 checks every cell against `pdftotext`'s output of the actual PDF, so
  "not a contiguous run of the page" is a fact. That is why `1~g/|` and `70°C` are real findings.
* **Groupings are not.** Whether the paper's bare row numbers are a column, whether `Proud member of`
  belongs in column 3, whether a seal's label sits in column 2 while column 3 stays empty, whether
  `Step 3` belongs inside the long cell, and how Appendix 6a's four printed header lines group into two
  labels — **all five are decisions the fixtures encode that no human made.**

**And we have already seen it change an answer.** Appendix 7 was a failure for *both* arms until the
row-number convention was declared — after which both passed. That was the key being a convention, not
a fact. The four shapes no arm passes are exactly the judgement ones, so "never passed by any arm" may
mean **"no arm guessed the reviewer's call"**. **(Confirmed 2026-11-05, §3.12: the reviewer's one
amended claim moved a shape for two arms, so "never passed" now covers three — one a real tool failure,
one our key, one our committed pass.)**

**What this changes.** The ranking between the arms (VLM 3/8, Docling 2/8, Document AI Layout 2/8 with 8/8 tables found,
Form 1/8) is **not established**, because the thing they are ranked against is unreviewed. Requirement 1 of this PRD says
*no unreviewed table reaches the corpus*; the same standard has to apply to the key that judges them.
The order of work is therefore: **build the verification surface** (page image beside the expected grid,
cell by cell, judged by the owner — **built 2026-11-05, §3.11**), **then re-score all three arms from
cache** — which costs nothing, because every arm's raw answer is now stored.

**Where a non-developer should start:** `product/design/d82_table_extraction_what_we_learned.html` —
the same three investigations, the scoreboard, the four options and a §18.3 export, written for the
product owner to decide D82 (which extractor, and whether to buy a credential). It is a review surface,
not a plan; the numbers in it are the numbers above.

**D81's consequence, reversed.** §3.5 said Document AI was the ceiling candidate because the gap was
in *structure*. That is no longer the finding: both arms now read Appendix 7 correctly, the best arm
passes 3 of 8, and what is left is **semantic** — a header printed once across four lines, a
1,112-character cell, a merged box beside a seal. Document AI is the same class as Docling, so it would
inherit those three and add geometry Docling already has. **The credential is now the least promising
next spend on this problem**, and it should be reconsidered only if S5's re-review shows the semantic
shapes are cheaper to buy than to review. The cheaper interim is the `lines` form as a **proposer**
(the model says which printed lines are a cell; the page supplies the characters; the S4 harness
checks the result) — which needs no credential, and whose remaining failures are visible as named
mismatches rather than as trust.

### 3.11 The verification surface is built (2026-11-05): 68 claims, 41 cells, and a signature that cannot outlive the key

§3.10 set the order — review the key, then re-score. **The surface is built and no cell has been judged
yet.** `scripts/shape_review.py` regenerates `product/design/uat/shape_key_review.html`: one
self-contained file (no CDN, no font, no network — the page images are `data:` URIs) in which each of
the eight shapes is **the page, rendered from the committed PDF, beside the grid the key expects**,
with one verdict per claim — *yes*, *no*, *can't tell*, and a reason for the last two. Nothing is
pre-filled and nothing is scored; the owner's call is the key (`pgs-presenting-uat`, hard rule 1).

**The instrument counts what the key claims, not what the page prints.** 8 shapes, **68 claims**, of
which **41 are cells** — while those eight pages print ~60 cells in the shapes' own columns. Every
cell the key does not assert says **`not claimed`** in words — not a dash, whose first reader took it
for "the paper is blank" — and the legend says that is not a claim of blankness, so the reviewer can
see the key's thinness as well as its errors. The claims are: per shape a header
grouping, a row count and the page each row starts on; 3 divider claims on Appendix 2; and the 41 cell
claims, each carrying the paper's text, its emptiness, its prefix/suffix, or its length.

| Piece | What it is |
|---|---|
| `scripts/render_shape_pages.py` | renders the seven pages the shapes name from the committed PDFs and pins both hashes (the PDF and the JPEG) in `knowledge/tests/fixtures/shape_pages/MANIFEST.json`. `pypdfium2` is imported **there and nowhere else** — requirement 10 stays true |
| `knowledge/tests/shape_pages.py` | the read side: proves the PDF and the image still hash to the pin, then returns the bytes. A hand-cropped screenshot fails |
| `scripts/shape_review.py` | the CLI and the contract (`KIND`/`ARTEFACT_NAME`); `--check` fails when the committed file drifts from the key |
| `scripts/shape_claims.py`, `shape_review_page.py`, `shape_review_template.py` | the same generator split by what fails differently — a claim in a review, the markup, the stylesheet and script — each under the 30 KB cap (`build_principles.md` §II) |
| `scripts/shape_review_signoff.py` | validates an export, writes `knowledge/tests/shape_review.json` with **every claim pinned to the text it judged**, and `--check` names every claim that has changed since — a signature cannot outlive what it signed |
| 16 tooling tests + 6 browser tests | claim coverage and uniqueness, no network, claimed-vs-unclaimed honesty, **the drift guard broken and watched red by changing one expected value**, and the page's script executed in Chromium (the §1.30 hazard) |

**A `No` does not edit the key.** This verb is *verify*: the record is evidence, and amending
`shape_fixtures.py` is a deliberate edit with its own diff, made after reading the record. The
re-score in §3.10 waits for the signature, but it no longer waits on a missing instrument.

**The first signature (2026-11-05, Kobus, seat Product): 68 of 68 claims Yes, three page notes.**
`knowledge/tests/shape_review.json` records it with every claim pinned to the text he judged; the
summary reports **5 shapes confirmed and 3 carrying an open question**, because a page note is a
finding and a shape whose reviewer asked "is this expected?" is not settled.

| Note | What it was | Outcome |
|---|---|---|
| `long_cell` — "the first column has a bolded **Step 3** that doesn't appear on the right" | **A defect in the key.** `long_cell.cell.0.0` asserted the cell *starts* with "The group conducts farm visits and"; the page and **our own reviewed landscape block** both start it with `Step 3` | **Applied and re-signed.** The claim is now `Cell(0, 0, starts="Step 3", contains="The group conducts farm visits and")`. Because that changes `expected`, the re-sign travels as an **amendment**: `{claim, from, to, basis}`, where `from` is the text the owner actually judged. `knowledge/tests/shape_review.json` keeps both texts and the basis, and `summary.claims_amended_under_review` names it |
| `empty_cells` — "the pdf states 'Local PGS group determines the membership fee' … not sure where the R500 comes from" | **The surface's fault, not the claim's.** `R500` is printed in the same merged Fee box, under "Annual membership fee (paid by the PGS group to PGS SA): R500". The grid rendered a `contains` claim as if it were the whole cell | Fixed: a partial claim is drawn with `…` where the cell goes on, and the legend says so |
| `page_break_row` — "we're missing loads of text, the cells don't just say the step name" | **The surface's fault.** The claims are prefixes (`starts=Step 1`), and the grid showed them as bare values | Fixed as above, with a test that no partial claim is ever drawn as a whole cell |

Two of three notes were the instrument lying about the claim, which is the second time this page's
presentation produced a wrong reading (the first was `—` read as "the paper is blank"). The lesson is
in the session record: **a rendered claim is not the claim** — a prefix, an inner phrase or an
unasserted cell must look like what it is.

**D85 is answered: eight of eight shapes confirmed, one claim amended under review**
(`claims_amended_under_review: ["long_cell.cell.0.0"]`), and the three page notes kept in the record
as `notes_resolved`. The re-sign was applied on the owner's explicit instruction the same day, through
the amendment path rather than by editing `expected` — so the record still says what he read.

**What S2 owes next is the re-score, and it is free.** Every arm's raw answer is cached
(`_scratch/or/responses/`, `_scratch/adc/responses/`); `scripts/table_reads.py` +
`scripts/eval_*.py` score them again against the corrected key. Only after that is D82 (which
extractor) a decision with evidence under it.

### 3.12 The re-score (2026-11-05): one claim on the key was worth a whole shape

Run against the **signed** key (`knowledge/tests/shape_review.json`, 68 of 68 Yes, `long_cell.cell.0.0`
amended to `starts="Step 3"`). Two arms replayed from cache — no network call, no credential, no spend.
Docling has no response cache, so that arm was re-run in its venv (**545 s**; `long_cell` is 85.8 s of
it). Evidence: `2026-11-05_s2_rescore_docling.json`, `2026-11-05_s2_rescore_documentai.json`,
`2026-11-05_s2b_rescore_openrouter.json`.

| Arm | Before | After | What moved |
|---|---|---|---|
| Docling 2.146.0 | 0/8 extracted, 2/8 with conventions | **identical — 0 of 8 shapes changed** | nothing: it returns *no table* on that page, so the amended cell is never consulted |
| Document AI Form Parser v2.1 | 1/8 | **1/8** | same verdict, sharper reason — it reads the cell as the bare label `Step 3`, so it now fails `contains` where it used to fail `starts` |
| Document AI Layout Parser v1.6-pro | 2/8 | **3/8** | **`long_cell` passes outright** — grid right *and* every character confirmed against our pass |
| VLM `claude-sonnet-5.5`, `lines` | 2 pass + 1 gutter + 1 grid-only (=3/8) | 2 pass + 1 gutter + **2 grid-only** | `long_cell` 1 mismatch → **0**, with 11 cells whose characters our committed pass does not confirm |
| VLM `gemini-3.1-flash-lite`, `lines` | 1 pass + 3 grid-only | 1 pass + **4** grid-only | the same shift, 4 unconfirmed cells |

The diff is confined to `long_cell`: **6 of the 72 combos** (8 Docling + 16 Document AI + 48 VLM)
changed, one line each, and no other shape moved at all — the rest is byte-identical to 2026-11-04.

**One claim, one shape, two arms.** `Cell(0,0, starts="The group conducts farm visits and")` became
`starts="Step 3", contains="The group conducts…"`, and that alone moved the Layout Parser a shape and
the two `lines` arms off "structurally wrong" onto "grid right, characters unverified". So:

* **The union of shapes any arm passes is 4 → 5 of 8.** Never passed by any arm is now
  `headerless_values`, `empty_cells`, `page_break_row` — **three**, and §3.8's "union of four" is
  superseded.
* **§3.8's closing claim is now partly false.** It said the shapes the arms "would still lose are the
  three no general extractor returns". The long cell was not a tool failure; it was ours. **The
  scoreboard is a property of the key as much as of the arms**, and §3.10's suspicion now has a
  measurement: 1 of 8 reviewed-claim defects cost an arm a shape.
* **The arms now disagree usefully on one shape** — Docling finds no table, the VLMs get the grid and
  lose characters, the Layout Parser reads it end to end. A flat 3/8 hid a tiered answer.

**Then the thread: the three remaining "no arm passes" shapes are three different problems**, which is
why they cannot be read as one number. Arbitrated against `knowledge/corpus/landscape.md` (our reviewed
artefact) and the committed page passes:

| Shape | Diagnosis | What settles it |
|---|---|---|
| `headerless_values` (Appendix 6a) | **Our key looked wrong and is not** — corrected 2026-11-05, §3.13. The paper prints four header lines (`Maximum number of animals per ha` / `Class or species`, then `Maximum number of animals per ha equivalent` / `to 170 kg N/ha/year`); our `columns` claim keeps both of column 1's lines and only the second of column 0's, and our own anchor admits that geometry, so all four arms read column 0 with both lines. **The owner kept the claim**: the paper does print two column labels, so the arms' merge is a tool failure | settled — it is more evidence that no general extractor associates a two-line header, and the union stays 5 of 8 |
| `empty_cells` (landscape p4) | **The key is right; the arms genuinely fail.** The artefact's legend says the fee box spans Steps 1–2 and is filed under Step 1, so `R500` is in cell 0,4, cell 1,3 is exactly `Proud member of` and cell 1,4 is genuinely empty. Every arm splits the spanning box or duplicates the two-line header | nothing — this shape earns its place |
| `page_break_row` (landscape p4→p5) | **The key is right and the *instrument* is what fails.** Both VLMs score **0 mismatches** and are demoted by quotes that are "out of printed order on page 5". Page 5's committed `-table` pass is interleaved: line 10 reads `its farmer members in the relevant   •  Farm visit checklist` and line 14 carries three columns' fragments, so **no cell's quotes can appear in read order**. §3.8's second finding, biting again | a wording and verdict fix in R3 — "our pass cannot order this page" is not "the model's characters are unverified" |

**What this changes for D82.** Still not answerable, and now for a better-understood reason: of the
three shapes no arm passes, one is our key, one is the tools, and one is our pass. **Not one is "no
extractor can do this."** The order stays: arbitrate the 6a header claim (one verdict, on the surface),
fix R3's order verdict, re-score, then decide. The credential argument is unchanged by all of this —
the Layout Parser is now level with the best VLM on passes and owns the one shape nobody had, while
re-OCR'ing 43 cells our pass does not confirm and costing 60–85 s/page against the VLM's 5–12 s.

**A hazard this produced:** the evidence JSON stores four sampled rows and clips cells at 200
characters, so a probe that reads *it* as the read will conclude things that are false of the arms
(`testing_hazards.md` §3.31). Score from the cache; read claims from the `mismatches` lines.

### 3.13 The first arbitration (2026-11-05): it settled the key and found four defects in the surface

The owner judged all eleven cards on `product/design/uat/arbitrate_shapes.html`; the export is
committed verbatim as `product/docs/evidence/2026-11-05_shape_arbitration_first_pass.json` (4 keeps,
5 unsure, 2 amend).

**What it settled, and it contradicts §3.12's guess.** `headerless_values.header` is **kept**: the
paper does print `Class or species` and `Maximum number of animals per ha equivalent to 170 kg N/ha/year`
as two column labels, and the fact that four independent readers merge column 0's two printed lines is
**a tool failure, not a key defect**. So the union stays **5 of 8**, §3.12's "correcting it would take
two arms to 4/8" is withdrawn, and Appendix 6a joins the "semantics no general extractor returns" pile
with `empty_cells`. Three keeps (`page_break_row.header`, `.rows`, `.pages`) confirm the row model and
the page split. **Nothing was amended, so nothing changed in the key and no re-score is owed.**

**What it found in the surface: four defects, all mine, all of them changing a verdict.**

| Defect | Evidence in the export | Why it mattered |
|---|---|---|
| **Only the first page of a shape was shown** | `page_break_row.cell.2.0`: “I can't see `Step 3` on the displayed pdf above”; `cell.2.4`: “can't see row 3” | `page_break_row` prints its third row on page 5, and the page rendered page 4. Two `unsure` verdicts are artefacts of the missing page |
| **The claim's cell was never shown, only the whole page image** | `empty_cells.cell.0.4`: “Column 4 is empty, column 5, under `fee` says `Local PGS group determines…`” | `R500` is printed further down inside the same merged box and is unreadable at page scale. The card now quotes the committed line that carries the claim's words |
| **Decisions the record already made were not stated on the card** | `empty_cells.cell.1.3` (“it's part of the seal, not standalone text”), `empty_cells.cell.1.4` (“the amount is 500 not 50”), `page_break_row.cell.1.0` (“step 2's cell starts with `The PGS group agrees on`”) | All three are answered by the landscape artefact's own legend (the fee box spans Steps 1–2 and is filed under Step 1; a seal's printed name is the cell) and by the `Step 3` amendment (a printed step label stays inside the cell). The page now carries an **Already decided** note per shape |
| **The amendment box accepted an arm's report as claim text** | both `amendments[].to` values are mismatch lines (`empty_cells: row 1 cell 4 must be empty, the read says …`) | Neither is applicable: `to` must be claim text (`empty`, `text=…`, `starts=…`). The card now states the form and the export refuses a pasted report |

**Two more lessons for the instrument.** A claim id is not a question: the card must say *printed row
N, page P, column “Fee”* and quote the line, because a reviewer reading a 200-dpi page cannot count
columns from a screenshot. And **a keep needs no record change** — the 68-claim signature from session
`1n` already says `yes` for these, so an arbitration that amends nothing writes nothing; only an
amendment travels through `shape_review_signoff.py --amend`.

**State after this pass:** 61 of 68 claims stand as signed; **7 are open** — the five `unsure` and the
two `amend` verdicts whose cause is a surface defect, to be re-judged on the corrected page. The page
was regenerated (10 cards, both pages, quoted lines, decided notes, form hint) and the settled claim is
listed as answered rather than asked twice.

### 3.14 D82 answered as a **composite** (2026-11-05, owner's call): best role from each arm, no winner

The owner stopped the claim-by-claim arbitration — *"we take our best options from each"* — and that is
the decision. It is what the numbers have been pointing at since §3.8: the arms do not compete on one
axis, they are each best at a different role, and the roles are separable because requirement 10 keeps
characters and structure apart.

| Role | What supplies it | The evidence for that choice |
|---|---|---|
| **Structure** — where the tables are, how many rows, how many columns | **Document AI Layout Parser v1.6-pro** | **8 of 8 tables found**, the best of any arm; 3/8 shapes pass outright; the only arm that reads the 1,112-character cell end to end (§3.12) |
| **Characters** — every character in a cell | **the page's own text layer**, verified per cell by R3 | Every extractive arm is imperfect: Document AI re-OCRs (`1~g/|` for `1 g/l`, 43 cells unconfirmed), Docling drops letter-spacing (`bov ine`), a VLM writes `70°C` for `70oC`. The committed pass plus R3 is the only thing that has never been wrong about a character |
| **De-interleaving the worst page** (Appendix 7's four columns) | **Docling 2.146.0**, free and local | Its grid was right all along — `rows 7/7, cols 5/4` once the row-number gutter is declared — while it finds *no table at all* on the landscape's merged-cell pages. It earns a role, not the job |
| **A cheap proposer** where no structure is needed | **the VLM `lines` form**, 5–12 s/page | 3/8 shapes, faster than Docling by 4–8×, and its failures are named as mismatches rather than trusted |
| **The verdict** | **S4's harness**, on every table | 14 reviewed rows, 0 violations, one mutation per requirement |

**So D82 is not "which extractor".** It is: Layout Parser proposes, the page supplies the characters,
the harness verifies, and a human reviews only the shapes where the question is semantic — Appendix 6a's
header association and the merged/empty cells (S5). **No credential buys the semantic half**, which is
why the four arms' union stops at 5 of 8 whatever is spent.

**What is deliberately left open.** Seven claims are unjudged (§3.13) and they no longer gate anything:
the two that matter — 6a's header (kept, so the arms are wrong) and the merged fee box (the artefact's
legend already answers it) — are settled for the purposes of building. S5 reviews those two shapes
*through the harness*, with the page beside the transcription, and any claim that review contradicts
becomes an amendment then.

**The interface lesson, which cost this session its last hour.** The judgement surface that worked
(§3.11, 68 of 68 judged without a single "can't tell") put **the page beside the grid** — one decision
per row, both sides visible. The surface built for the arbitration **stacked** the evidence above the
question and showed only a shape's *first* page; the owner's notes reduced to *"I can't figure out what
you need from me"*, and four of his eleven verdicts were caused by the layout rather than by the paper.
Judging a cell is a comparison, so **the comparison has to be on the screen at the same time** — recorded
as a hard rule in `pgs-presenting-uat`, and the page is now side-by-side with the full-size page one
click away.

### 3.15 What S3 landed (2026-11-05): the generator writes the block, and the page supplies the characters

§3.14 decided *who proposes the structure*. §3.15 is the slice that makes the decision operative, and
it changed three things about how a table reaches the corpus.

**The block is emitted, not typed.** `scripts/table_blocks.py` takes a proposed structure — the arm's
grid, committed under `knowledge/proposals/` — resolves every cell against the body's *printed lines*,
and writes the `<!-- table … -->` block itself, splicing the page's own characters, line breaks and
blank lines included. Three rules, each proved by a guard that was broken and watched red:

1. **A cell's characters are the page's.** The proposal's text is a *locator*, never a source: it is
   matched exactly, or with spaces set aside **only where the page letter-spaces a word** (6a's
   `b o v i n e`), at a word boundary — because `1,500` occurs inside `11,5000` as a run, and that
   slice would put a number the paper does not print into a row with R3 still green.
2. **One forward-only cursor, on the pages the proposal names.** A cell cannot stitch a line from above
   the table into a row, and a table whose cells print out of order is refused rather than re-ordered.
   The page filter is load-bearing: the landscape prints the same five column labels on *every* table
   page, so a page-blind search resolves a header to the wrong table (`testing_hazards.md` §3.33).
3. **The region is claimed.** Every printed line between the first and last a cell claimed must belong
   to a cell, or the block would delete it (`testing_hazards.md` §3.25). Blank lines and page markers
   are the only things allowed to go unclaimed.

What it cannot verify, it **refuses by name**, and the draft keeps the page's prose: a cell the paper
does not print, a sub-clause marker inside the table, a printed line nobody claims. That is the
difference between a generator and a transcriber, and it is why the landscape's two refusals are the
right outcome rather than a failure to finish.

**The structure is data, found by bytes.** `knowledge/proposals/<doc>.structure.json` is an arm's read,
reduced by `scripts/propose_tables.py` from a cached response and carrying its banner (`structure`,
`processor`, `project`, `captured`, `reduced_from`). `<doc>.reviewed.json` holds the fields **no
extractor produces** — the legend, the shape, the titles, the fee labels, the fork — so regenerating a
reviewed artefact does not drop a person's sentence. Lookup is by the PDF's **sha256**, not by
`CORPUS_DOCUMENTS`: a renamed or reprinted document finds no proposal, which is the truth, and a new
standard needs no registry entry, enum or migration.

**The extraction is recorded on the block** (requirement 1, R1). `extraction: layout|raw|table` is a
validated block field, `check_tables.py` judges the artefact against the pass the artefact names, and
the command line's `--pages-mode` is demoted to the draft-only escape — refused when it contradicts
what the artefact records. The four reviewed blocks now declare theirs (four added lines in `opp.md`
and `landscape.md`, nothing else).

**Measured.** `python scripts/build_corpus.py --doc opp --force` reproduces `opp.md` **byte for byte**
(660 lines, no diff): the emitter's block *is* the block a reviewer signed, and the test that says so
builds its body from the committed page fixtures, so it needs no PDF and no extractor
(`tests/tools/test_table_blocks.py`). The landscape's committed proposal is refused at
`proposal 1, column 1` (its page-4 table's rows are printed before the heading the de-columned page
found) and `proposal 2, row 2, column 3` (the arm splits a merged box, and the seal artwork cell) —
S5's four declarations, written down rather than guessed.

### 3.16 What S5 landed (2026-11-05): Appendix 6a is a block, and a body is the pass its block declares

S5 is one PRD slice with four tables in it. This session landed the **first** of them and the two
capabilities all four need, and wrote `INGESTION_ENGINE_S5_PLAN.md` for the rest. The plan is the
honest artefact here: three of the four tables need a review with the paper in front of them, and
landing half of one in a commit is how a block becomes a hand-tidied copy of a page.

**The missing capability, and it was not cosmetic.** A block records `extraction: table|layout|raw`
and the gate judges its cells against *that pass* — but the generator sliced every section from the
de-columned geometry stream regardless. So a `-table` block was assembled from `-layout` text and
judged against `-table` text: one of the two was always wrong. `scripts/corpus_pages.substitute_pass`
is the fix, and it is declarative: a proposal's `pdf_pages` + `extraction` say which pages to take
from which pass, and `build_corpus.build()` takes exactly those, sliced through the document's own
`body_lines` rule (a parser that owns its furniture judgement keeps owning it). Measured on the
landscape, which is why S3 could not emit it: its tables' pages are taken from `-raw`, so the page-4
header was not a run of any printed line and the emitter refused at `column 1`. With the rule in
place that refusal moves on to `column 2` — the multi-line column label, which is S5-d's declaration.

**The reviewed label (requirement 2's other half).** Appendix 6a prints its header once, as two
levels of type across four lines with a merged cell; all four arms flattened the two labels into one
string (`Maximum number of animals per ha Class or species`), and the owner arbitrated the two labels
on 2026-11-05. A one-line `cols:` field cannot be a slice of a multi-line header, so the labels are
**reviewed data** in `knowledge/proposals/saoso.reviewed.json` — the same status
`TABLE_SECTIONS["Appendix 2"].columns` already had. The cells are untouched by that declaration: a
cell the page does not print is still refused (`test_a_reviewed_label_never_makes_a_cell_the_reviewers`).

**The one declared normalisation, now declared where it is used.** The paper letter-spaces part of
the class column (`Other b o v i n e a n i m a l s less t h a n o n e year old`); `CORPUS_EDITS` already
rejoins it, with a page number and a reason, and `test_corpus_saoso` proves that edit was necessary
and applied. R3 now accepts the review's spelling **only** on a printed line that itself carries a
spaced run, and refuses a page that glues its letters — the guard on the guard.

**Measured.**

* `python scripts/build_corpus.py --doc saoso --force` → **the diff is the review**: Appendix 6a's
  interleaved page becomes a 20-row block, `101 insertions(+), 25 deletions(-)` in one section. The
  diff also *corrects* the page: the old artefact paired `Equines over six months old` with `5`
  (its neighbour's value); the block pairs it with `2`. That is the defect the PRD opened with,
  visible in one hunk.
* `python scripts/check_tables.py --doc saoso --rows 20` → `ok — 1 tables, 20 rows, 0 violations
  (table pages, recorded on the artefact)`.
* `python scripts/build_corpus.py --doc opp --force` leaves `opp.md` **byte for byte** unchanged —
  S3's regression still holds.
* `APPENDIX_6A_ROWS` and `TABLE_ROWS["Appendix 6a"]` are **deleted**; the artefacts 6a section is a
  block and the ingest reads it through `chunks_for_parsed_section`. `APPENDIX_2_ROWS` stays for now
  and is S5-b's.
* Full suite `--create-db`-equivalent (`--reuse-db`, this box, 2026-11-05): **1831 passed / 1 skipped
  / 8 xfailed in 79 s warm**; `scripts/fast.sh --critical` **182 passed / 4 deselected in 18 s**.
* Three guards were broken and watched red before being trusted: the reviewed label, the pass
  substitution, and R3's letter-spacing fallback (`3 failed` mutated, `3 passed` restored).

**A human read the page, and caught what no guard could (2026-11-05).** The owner reviewed the
rendered Appendix 2 pages (`product/design/s5b_appendix_2_pages.html`) and found that the seaweed
row's tail is printed as **`(iii) fermentation.`** — with a bracket the reviewed cell had dropped.
The cell had been transcribed from **printed 79**, where Appendix 3 prints `iii) fermentation.`
beside `Coffee grounds`, and the test guarding that row could not tell the two apart:
`"iii) fermentation." in "(iii) fermentation."` is true because the shorter string is a substring of
the longer one (`testing_hazards.md` §3.39). One character corrected in `knowledge/tables.py`; the
assertion is now character-level and fails on the old data (verified). He also confirmed rows
27–29 on printed 78 as printed. **This is the argument for S5 in miniature:** the review was a
person's reading, no machine check could contradict it, and the only thing that did was the page
beside the claim.

**What is left, with the reason each is a review rather than a chore.** Appendix 2 needs 30 rows and
no arm read exists for printed 77–78 (the cached `qualifier` response is the shape page), so its
locators have to come from the owner's 2026-10-21 review, declared and recorded — or the block is 11
rows and `APPENDIX_2_ROWS` stays, which deletes nothing. Appendix 7 needs a cell that wraps *inside*
a column (`Aeration or oxygenation` / `using gaseous oxygen`, with `Air,` beside it on the same line),
which `_resolve`'s continuation branch cannot express; Docling's grid is the evidence for the column
boundary. The landscape needs the four declarations §3.15 named, and its artefact cannot be
regenerated wholesale — pages 2–3 and 9 are the **reviewer's** front matter (commit `8674d7a`), so
S5-d emits blocks and splices them in place of the current table region.

### 3.17 What S5-b landed (2026-11-05): Appendix 2 is a block, and a band is a declared boundary

The second of S5's four tables, and the expensive one: Appendix 2 is **30 rows printed across three
pages** (76–78), and no arm ever read pages 77–78 — the cached `qualifier` response is the shape page
(the eleven rows on printed 76). The plan's §4 named the two honest routes and forbade the third (a
fresh arm run). The route taken is the exploration's recommendation, and it is a **review promoted to
locators**, not authorship: the owner's 2026-10-21 pairing enters the proposal as cell text the emitter
must *find* on the page, and the emitter refuses anything it cannot find.

**Four declarations, each refused first, then declared.** They are the plan's §5 steps, in order:

* **`band: {"76": 60}`** — where the second column starts, per printed page, from the measured
  `TABLE_BANDS` (2026-10-21). Without it the left cell's first line reads `Biodegradable Free of
  contaminants`, i.e. the neighbour's words in the middle of a cell, and the emitter refuses; with it,
  each column is its own stream and each keeps its own forward cursor. `test_the_declared_band_is_the_measured_one`
  keeps the declaration and the measurement from drifting apart.
* **The hyphen across the line break** — the harness has split a cell line at its hyphen and required
  both halves as printed lines since 2026-11-03; the emitter refused it, which is why the
  trace-elements row could not be emitted. It is now the same narrow rule on the emitter's side, and
  the emitted cell keeps the page's two lines (`cobalt-` / `sulphate`), not the review's one word.
* **`dividers: [{before, text, kind}]`** — the seven printed headings (`I. PLANT AND ANIMAL ORIGIN`,
  three `South African specific`, three more parts) are located on lines of their own and written as
  `<!-- row-divider: … -->`, so the block carries them and the reader draws them. `TABLE_SECTIONS` is
  deleted; the reader reads the block's dividers.
* **`tails: [{row, column, page, text}]`** — the seaweed row's condition ends **`(iii) fermentation.`**
  at the top of printed 77. The declaration names the words and the page; the emitter verifies the
  words are that page's *first* printed line, then writes a page marker **inside** the cell. That is
  the one place a block records a cross-page continuation, and it is what lets R3 judge each cell line
  against the page the block says printed it (the parser now stores one page per cell line).

**The generator could not run at all, and the suite was green.** `build_corpus.build()` called
`corpus_pages.pass_texts(...)` while importing only names from that module, so `--doc saoso` died with
`NameError` before writing a section — and no test calls `build()`, only the emitter under it
(`testing_hazards.md` §3.40). Two more defects surfaced from the same run and are recorded there: the
"is this table here at all?" pre-check answering yes in `S8.1` (twenty pages early) and marking the
proposal attempted before its own section (§3.41), and R6's "the paper prints it once" being a claim
about uniqueness that Appendix 2's three `South African specific` labels falsify (§3.42).

**Buckets and ordering.** The emitter resolved Appendix 2's two-column rows with a single forward
cursor, which cannot express it: both cells of a row share every printed line, so the condition's
first line sits *above* the substance's last one. The band made two streams of each line; the cursor
follows the stream, and a row's floor keeps a column from resuming above where the row starts.

**Measured.**

* `python scripts/build_corpus.py --doc saoso --force` → `204 insertions(+), 104 deletions(-)` in one
  section: Appendix 2's interleaved `-layout` prose becomes a 30-row block with its seven dividers,
  and the row that reads `See Section B – Appendix 6` in the block carries the en dash the
  `-layout` pass had lost.
* `python scripts/check_tables.py --doc saoso --rows 30,20` → `ok — 2 tables, 50 rows, 0 violations
  (table pages, recorded on the artefact)`. `--doc opp --rows 6` and `--doc landscape --rows 3,2,3`
  are unchanged: `build_corpus --doc opp --force` leaves `opp.md` **byte for byte** unchanged.
* `APPENDIX_2_ROWS`, `TABLE_ROWS`, `TABLE_SECTIONS`, `rows_for`, `structure_for`, `section_for`,
  `chunks_for_rows`, `NO_CONDITION_LABEL`, `TableRow`, `TableSection` and `row_blocks` are **deleted**;
  the ingest has one table path (`chunks_for_parsed_section`), and the reader one grid.
  `knowledge/tables.py` is now 181 lines: the grid, its alignment, and the measured band.
* The branch has **31 chunks, not 30**: the header prose above the grid is a chunk again, as it never
  was while Python rows replaced the section's chunks. Corpus total 340 → 341.
* Full suite: **1776 passed / 1 skipped / 8 xfailed in 100–223 s warm** on four runs (100.44,
  135.24, 177.16, 223.31 s; `--reuse-db`, this box, 2026-11-05 — quote the range, `testing_hazards.md`
  §3.17). Nine tests fewer than S5-a's 1831 after the deletions, and 60
  of the 66 are `test_row_blocks.py`'s two parametrisations over 30 rows — in the grid, cells are
  laid out by `passage_blocks`, and the losslessness claim is carried by
  `test_the_real_corpus_survives_the_layout_and_produces_lists`.
* Four guards broken and watched red: the band (`_column_view` ignoring it), the tail (declared →
  inferred), R3's per-line page, and R6's counting (the last was proved by the failure before the fix).

**What is left.** Appendix 7 needs a cell that wraps *inside* a column and a row-number gutter
(`--gutter 1`), with Docling's grid as the declaration's evidence (S5-c). The landscape needs its four
declarations and a splice that does not rewrite the reviewer's front matter (S5-d). Then the shape
markers come off (S5-e) and the last of the bespoke path goes (S5-f).

## 4. Requirements

1. **No unreviewed table reaches the corpus.** Every table row in `DocumentChunk` is either reviewed
   or carries the marker of the extraction it came from, and the marker is checkable against the
   page.
2. **Header association is asserted per row.** A chunk's `embedding_text` names each printed column
   that has a value — for every table, not only for artefact blocks (this is what Appendix 6a lacks).
3. **Cell fidelity is asserted against the page**, per printed line, in printed order (the landscape
   rule, generalised): every line a cell carries is a contiguous run inside one printed line, and a
   cell's lines appear in order.
4. **Row count is asserted** — the extracted rows equal the rows the page prints, including a row
   whose later half is on the next page.
5. **Empty is data.** An empty cell is recorded as empty, never dropped, never filled from the cell
   above or the row before.
6. **Spans stay whole.** A merged cell (the landscape fee box) or a qualifier that governs several
   rows is never split across the row boundary it crosses.
7. **Non-text in a cell is named, never quoted.** Artwork is recorded as not stored plus its printed
   label; it never becomes a chunk.
8. **The generator cannot silently lose a review** (S1, done) — and from S3 it emits the block
   itself.
9. **No new claim.** A quote remains a substring of the stored artefact text. An extractor that can
   only cite a region is X3, and it is not this PRD.
10. **The gate needs no extractor.** A shape fixture reads committed text; running an extractor is a
    build-time act with a recorded banner, like `pdftotext` (P1's rule).

## 5. Execution Steps

| # | Slice | State |
|---|---|---|
| **S0** | The eight-shape fixture set — registry, provenance guards, the audit test, eight strict-xfail targets | **landed 2026-11-03** |
| **S1** | `build_corpus.py` refuses to overwrite a table block; `--discard-tables` is the named override | **landed 2026-11-03** |
| **S2** | Evaluate extractors against S0's eight pages: cells, headers, spans, speed. The output is a table in this PRD's §6, not a preference | **Closed 2026-11-05. Six measurements (§3.5–§3.9), the key reviewed and signed (§3.11, D85), all three arms re-scored against it at no cost (§3.12), and D82 answered as a composite — Layout Parser for structure, the page's text layer for characters, Docling for Appendix 7's columns, the harness for the verdict (§3.14). The credential bought its own answer: no arm beats the free ones, and the union stops at 5 of 8 because the rest is semantic. S3 and S5 are what is left.** |
| **S3** | The generator emits `<!-- table … -->` blocks from the winner of S2, guarded by rule 5's parser | **Landed 2026-11-05 (§3.15).** `scripts/table_blocks.py` resolves a proposed structure against the body's printed lines and writes the block, splicing the page's own characters per cell; the structure is committed data found by the PDF's **sha256** (`knowledge/proposals/`, reduced from the cached arm response by `scripts/propose_tables.py`). `python scripts/build_corpus.py --doc opp --force` reproduces `opp.md` **byte for byte**, and the block carries `extraction:` so the gate judges it against the pass it came from (R1). The landscape's proposal is committed and refused on two cells — its page order and merged fee box are S5's. |
| **S4** | The verification harness (requirements 2–7) as the gate for any new document | **landed 2026-11-03** — `knowledge/table_harness.py`, `scripts/check_tables.py`, 27 tests; the four reviewed tables pass |
| **S5** | Re-review Appendix 6a (20 rows) and Appendix 7 through the harness; delete their bespoke handling | **Partly landed 2026-11-05 (§3.16, §3.17).** Appendix 2's thirty rows are a block too (`check_tables --doc saoso --rows 30,20` → ok) and `APPENDIX_2_ROWS` is deleted; the declarations it needed are `band`, `dividers` and `tails`. The earlier note:  Appendix 6a is a `<!-- table -->` block of 20 rows emitted from its page (`check_tables --doc saoso --rows 20` → ok) and `APPENDIX_6A_ROWS` is deleted. The two capabilities all four tables need are in: **the body is the pass the block declares** (`corpus_pages.substitute_pass`) and **the reviewed column labels** (`reviewed.json`'s `columns`). Appendix 2 (30 rows, no arm read for printed 77–78), Appendix 7 (a cell that wraps inside a column) and the landscape's four declarations carry a plan each — `INGESTION_ENGINE_S5_PLAN.md` §5. |

**What would change this order** (from the exploration, kept here because it is the decision's own
falsifier): if S2 shows extractors lose spans or qualifiers on more than two of the eight shapes,
X3 moves first — a region citation needs the structure to be locatable, not perfect. If a deployment
must ingest a document this week, X1 plus G11-E (context rendered, never quoted) is the honest
answer, with the review written down as debt.

## 6. Success Criteria

- [ ] A document not in `CORPUS_DOCUMENTS` can be ingested and its tables chunked with column
      meaning, with no hand-authored table block. **Proved at the seam (S3, 2026-11-05):**
      `tests/tools/test_new_document_ingest.py` emits the block from committed structure data, writes
      an artefact under a `doc_key` the registry does not have, ingests it through the explicit-
      metadata path with `embed=False`, and asserts the row chunk's `embedding_text` names each
      printed column. **Not proved:** that a genuinely new *standard's* paper has a structure — no
      arm response exists for any document outside the eight shape pages, and S3 may not re-run the
      arms. The first real ingestion runs `scripts/propose_tables.py --pdf <new> --pages …` once.
- [ ] All eight shape targets pass, and the strict-xfail markers are gone (the audit test then
      reports zero uncovered shapes).
- [ ] Appendix 6a's 20 chunks carry their column meaning; Appendix 7's chunks are rows, not
      interleaved text. **Two halves, one tick: the tick waits for the second half.**
      **Appendix 6a: proved (S5-a, 2026-11-05).** Its twenty row chunks each carry
      `Class or species: … · Maximum number of animals per ha equivalent to 170 kg N/ha/year: …`
      (`knowledge/tests/test_tables.py::test_one_chunk_per_six_a_row_and_none_of_them_invented`), and
      the pairing in the block is the paper's — the diff corrected `Equines over six months old 5` to
      `2`. **Appendix 7: not yet** — its cells wrap inside a column, which the emitter cannot bound.
- [ ] Cell fidelity, row count, header association and empty-cell preservation are asserted for every
      table in the corpus, not for the reviewed ones only. **Partly (S5-b, 2026-11-05):** asserted for
      every table that *is* a block — **6 tables, 64 rows, 0 violations** (`landscape` 3+2+3, `opp` 6,
      `saoso` Appendix 2 30 + Appendix 6a 20; `tests/tools/test_check_tables.py` pins the counts and
      `knowledge/tests/test_table_harness.py` the checker). **Still outside any block:** Appendix 7's
      4 interleaved chunks — S5-c.
- [ ] Appendix 2's dividers survive as block data, and the reader still draws them. **Proved (S5-b,
      2026-11-05):** the seven printed headings are `row-divider` annotations in the block, R6 claims
      each one as often as the page prints it, and `test_the_dividers_render_above_the_rows_they_name`
      asserts the rendered grid puts each above the row it names.
- [ ] `scripts/verify.sh` is green with `PDFTOTEXT_BIN` poisoned, and no fixture needs a PDF or a
      network call to run.

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| An extractor is adopted without a harness, making verification worse | S0 exists first, and it is the evaluation instrument; R9 forbids a new claim |
| The fixture set becomes a second corpus that drifts from the paper | page text is *read* from the committed page fixtures, which are sha256-pinned; anchors are asserted verbatim |
| Strict xfail becomes a place gaps go to die | `XPASS(strict)` fails the suite when a shape starts working, and the audit test pins the uncovered set |
| `--force` keeps being run out of habit | S1 refuses before writing and names the override; the hazard entry (§3.25) points at the guard |
| Appendix 6a/7 are "fixed" by another hand review | S5 requires them to close *through the harness*; the audit test keeps naming them until it does |
| A vision path gets adopted for convenience | D70.2 and R9: a quote is characters we verified; page images are a fallback with a written claim. **Measured 2026-11-04 (§3.7–§3.8):** the VLM arm's best is 3/8, every cell is checked against the page per printed line, and unresolved quotes are named rather than trusted |

## Pre-Flight Checklist

- [x] No models or migrations: this is ingestion over existing `StandardDocument`/`DocumentChunk`
- [x] No views, forms or URLs
- [x] Tests in `knowledge/tests/` (the corpus library's own suite) and `tests/tools/` (the generator)
- [x] Fixtures read committed text; the gate keeps `PDFTOTEXT_BIN` poisoned
- [x] No template logic, no money, no new palettes
- [x] `knowledge` still imports nothing from `core`

---

## Appendix A — Where S0's expectations come from

Every number in the registry is measured, not assumed: `Expect` values were read off the artefacts
and the page fixtures on 2026-11-03 (long cell **1,112** characters — the exploration says 1,107,
which is the same cell with the paper's line breaks counted differently; 12 empty cells; Step 3 on
PDF 5; Appendix 2's dividers before rows 0, 1, 3, 14, 15, 26, 28; Appendix 7's rows 1–6b on printed
page 88). Where the exploration's number and this tree's number differ, this tree's number is used
and the difference is named in the fixture's docstring.
