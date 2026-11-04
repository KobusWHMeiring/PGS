# PRD: The ingestion engine — from "a person reviewed this document" to "a suite checks every document"

**Status:** In Progress — **S0 (the eight-shape fixture set) and S1 (the generator's table-block
guard) landed 2026-11-03, session `1e`; S2 is measured for two arms (Docling §3.5, the OpenRouter VLM
§3.7).** S3–S5 (generator emits table blocks, re-review of Appendices 6a and 7) are open, and
Document AI needs the owner's GCP credential.
**Owner:** Corpus ingestion (sub-plan B), grounded chat (sub-plan D)
**Last Updated:** 2026-11-04
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
row-structured one.

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

**D81's consequence, unchanged in direction.** Document AI remains the ceiling candidate and still
needs the owner's four things; this result adds one more reason to spend that money rather than less,
because it shows the gap is in *structure*, which is the class Document AI is in. It also adds a
cheaper interim: **the `anchors` form is the only shape in which a generative model may enter the
corpus** (boundaries from the model, characters from a checkable pass), and it needs a row-structured
extraction pass before it can be scored fairly.

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
| **S2** | Evaluate extractors (Docling, the OpenRouter VLM arm, Document AI) against S0's eight pages: cells, headers, spans, speed. The output is a table in this PRD's §6, not a preference | **Docling measured 2026-11-03 (§3.5): 0/8 as extracted, 1/8 with a header convention, 2/8 tables not detected. The OpenRouter VLM arm measured 2026-11-04 (§3.7): 2/8 at best, 8/8 tables found, header association 7–8/8, and `indices` form blocked by our pass having no cell granularity.** Document AI is next and **needs the owner's GCP project, billing, processor and key**. Why, and what that costs: `product/design/d80_s2_extractor_evaluation.html` |
| **S3** | The generator emits `<!-- table … -->` blocks from the winner of S2, guarded by rule 5's parser | open |
| **S4** | The verification harness (requirements 2–7) as the gate for any new document | **landed 2026-11-03** — `knowledge/table_harness.py`, `scripts/check_tables.py`, 27 tests; the four reviewed tables pass |
| **S5** | Re-review Appendix 6a (20 rows) and Appendix 7 through the harness; delete their bespoke handling | open |

**What would change this order** (from the exploration, kept here because it is the decision's own
falsifier): if S2 shows extractors lose spans or qualifiers on more than two of the eight shapes,
X3 moves first — a region citation needs the structure to be locatable, not perfect. If a deployment
must ingest a document this week, X1 plus G11-E (context rendered, never quoted) is the honest
answer, with the review written down as debt.

## 6. Success Criteria

- [ ] A document not in `CORPUS_DOCUMENTS` can be ingested and its tables chunked with column
      meaning, with no hand-authored table block.
- [ ] All eight shape targets pass, and the strict-xfail markers are gone (the audit test then
      reports zero uncovered shapes).
- [ ] Appendix 6a's 20 chunks carry their column meaning; Appendix 7's chunks are rows, not
      interleaved text.
- [ ] Cell fidelity, row count, header association and empty-cell preservation are asserted for every
      table in the corpus, not for the reviewed ones only. **Partly (S4, 2026-11-03):** asserted for
      every table that *is* a block — 4 tables, 14 rows, 0 violations — and the rows outside any
      block (Appendix 6a's 20, Appendix 7's 4 chunks) are exactly what S5 closes.
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
| A vision path gets adopted for convenience | D70.2 and R9: a quote is characters we verified; page images are a fallback with a written claim. **Measured 2026-11-04 (§3.7):** the VLM arm scores 2/8, and the only admissible form is `anchors` — boundaries from the model, characters from the extraction pass |

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
