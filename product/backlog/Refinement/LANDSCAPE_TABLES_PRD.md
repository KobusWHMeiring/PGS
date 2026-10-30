# PRD: The certification landscape's tables — reviewed rows, and the rule for every other table

**Status:** Refinement — **all seven decisions taken 2026-10-29** (D72.1–D72.7, §6); nothing built.
**Resolved 2026-10-29:** the rows live in the **corpus artefact**, not in `tables.py` (§5.2a), so step 2
is dropped and the landscape's conversion moves ahead of its PRD's own place in the rollout.
Decision artifact: `product/design/d72_landscape_tables_questions.html`.
Finding §1.4 (pages 1–3 are not in the corpus at all) was found while verifying §1.3 and is **larger
than the tables**; it is in this PRD because it is the same document and the same re-ingest.
**Owner:** Corpus (D53 artefact review) · Build (the guards)
**Last Updated:** 2026-10-29
**MVP:** MVP 0 — the landscape is published on the public site *and* is in the chat corpus today, so
this is a live defect on two surfaces, not a future one.
**Scope:** The five table pages of `pgs_docs/PGS Certification landscape_Final.pdf` (PDF 4–8) and the
`knowledge/tables.py` key change that lets a document with no section numbering hold reviewed rows.
**Not** in scope: the reader's column width, OPP PDF 4 and 11, SAOSO Appendices 3/4/6b/7 (that is
G4 in `CORPUS_CANONICAL_FORMAT_PLAN.md`), and the landscape's artefact conversion (P5).
**Reference:** `knowledge/tables.py` · `knowledge/ingest.py::chunks_for_sections` ·
`core/services/_documents.py::structure_for` call site · `knowledge/columns.py::PAGE_LAYOUT_EXCLUSIONS` ·
`CORPUS_COLUMN_EXTRACTION_PRD.md` §3.5 · `CORPUS_CANONICAL_FORMAT_PLAN.md` step 4 Q4 ·
`BugFixes/saoso_text_glyphs_and_boundaries.md` §5 and D70.1–D70.2 · `READER_STRUCTURE_PRD.md` D70 ·
`DESIGN.md` (only §5.4's mock needs it).

Evidence for every number below: `_scratch/lscheck/variants_p4.txt` (git-ignored), plus the commands
in §9 step 0, which reproduce it.

---

## 1. Problem Statement

A reader looking at **Certification Landscape › establishing-a-pgs-group** sees this:

> ESTABLISHING A PGS GROUP · The table below outlines the steps … · Key steps · Resource documents,
> Use of seals and logos · Seals and logos **Fee** · guidelines and requirements · Local PGS group
> determines the **Step 1** · Farmers who are already producing • **PGS group** · a surplus of organic
> produce and • **Annual membership fee (paid** …

and the passage **stops mid-cell**, after `Association (OFO), and wanting to`.

Three separate defects are stacked here, and only the third is hard.

### 1.1 The page is a table, and `de_column` treats it as two columns of prose

`apply_layout` transforms **8 of the landscape's 10 pages**:

| PDF page | Bands detected | What the page actually is |
|---|---|---|
| 2 | `(63,65)` | two columns of prose — correct |
| 3 | `(64,65)`, `(67,69)` | two columns of prose — correct |
| **4** | `(32,40)`, `(65,66)`, `(99,100)`, `(108,110)` | **a 5-column table** |
| **5** | `(34,35)`, `(36,38)`, `(48,49)`, `(64,66)`, `(110,112)` | **a 5-column table** (header repeated) |
| **6** | `(29,36)`, `(40,43)`, `(44,46)`, `(47,49)`, `(51,63)` | **a 5-column table** |
| **7** | `(29,35)`, `(60,68)`, …, `(99,127)` | **a 5-column table** |
| **8** | `(31,33)`, `(41,42)`, `(44,45)`, `(48,57)`, `(97,99)` | **a 5-column table** |
| 9 | `(51,52)`, `(59,61)` | two columns of prose — correct |

`de_column` re-emits a page **column-block by column-block**, which is column-major *by construction*.
That is the exact defect class this repo already excludes for SAOSO PDF 82–83 (Appendix 4 Table 1:
"column-major order leaves the INS numbers in one block … no row can be located or quoted") and for
OPP PDF 4 and 11 — but **there is no `landscape` entry in `PAGE_LAYOUT_EXCLUSIONS`**, even though
`columns.py`'s own docstring records *"landscape pdf 4 gains bands and reorders further"*.

### 1.2 The damage reaches the concordance, not just the text

Column-major output puts `R500` alone at the start of a line; `HeadingParser` reads it as a heading.
Measured on the live corpus (`concordance_sections()`), the document's 8 chunks present as **6
branches**, two of them invented:

| Branch key | Title shown | Passages |
|---|---|---|
| `ESTABLISHING A PGS GROUP` | same | **1** — the first third of the table, cut mid-cell |
| `R500` | "Cost of joining a PGS group" | 2 — the rest of the same table, plus p5 |
| `PGS SEALS AND THEIR USE` | same | 1 |
| `SAOSO ORGANIC CERTIFICATION` | same | 1 |
| `PGS SA.` | "Working with PGS South Africa" | 2 |
| `SAOSO` | same | 1 |

`CONCORDANCE_PRD` §10.5 records `R500` and `PGS SA.` as "lines mis-detected as headings by
`HeadingParser`" and patches the *title*. It did not remove the cause, and it did not notice that the
cut falls **inside a table row**.

### 1.3 No extraction mode makes a cell quotable — this is the load-bearing finding

Five sentences that are verbatim contiguous on the paper, checked as `flat(sentence) in flat(chunk)`
over all chunks, for three renderings:

| Rendering | Paper sentences quotable |
|---|---|
| A. raw `-layout` | **1 / 5** |
| B. `de_column` (shipped today) | **2 / 5** |
| C. `-table` for PDF 4–8 | **0 / 5** |

And `-table` **is** loss-free: the non-space character multiset is *identical* to `-layout` on every
page 2–9 (measured), so it cannot lose a glyph. It still scores 0/5, for two reasons worth keeping:

1. **A table row's cells share a visual line in every mode.** `de_column` keeps a spanning line whole
   (rule 2), and `-table` aligns *rows* but still puts `Key steps` and `Fee` on one line. So a cell's
   sentence is never a contiguous substring — no extraction mode can fix this, and no amount of
   tuning `MIN_COVERAGE` will either.
2. **`-table` breaks the running-header suppression.** `_repeated_headings` matches *exact* text, and
   `-table` splits `PGS SA - SOUTH AFRICAN ORGANIC CERTIFICATION LANDSCAPE` into `PGS SA -` and
   `…LANDSCAP  E`. Furniture then becomes headings and splits chunks — chunk count rises 8 → 12 with
   branches like `PGS SA -` and `south-african-…-landscap-e`.

**Conclusion:** the shipped ingest is not doing something wrong that a flag can undo. `CORPUS_COLUMN_
EXTRACTION_PRD` said it plainly — *"Not in scope: … table row reconstruction"*. This PRD is that
scope, arriving.

### 1.4 Pages 1–3 are not in the corpus at all

Measured on the live corpus (2026-10-29) and reproduced from a fresh in-process build:

| Probe | Chunks containing it |
|---|---|
| `Participatory Guarantee Systems` (PDF 2) | **0** |
| `six basic elements` (PDF 2) | **0** |
| `First-Party` (PDF 3) | **0** |
| `Third-Party` (PDF 3) | **0** |

The document's 8 chunks cover PDF 4–9 only. `HeadingParser` opens a section at a heading, and pages
1–3 print none that survive: the running header is suppressed **by repetition** (§1.2, and it is the
same line that becomes a false heading when the mode changes), and `First-Party Claim` / `Third-Party
Certification` are **Title case**, which the parser's docstring records as a deliberate miss
("UPPERCASE only … a false heading is a worse citation than a missing one"). Page 1 is a cover; page
10 is blank.

**Consequence, and why it is bigger than the table defect.** The plain-language answer to *"what is a
PGS?"*, the six basic elements, and the three certification routes are exactly the content a
smallholder asks about, and **none of it is citable** — not because the text is scrambled but because
there is no row in `DocumentChunk`. A retrieval failure here looks identical to a corpus gap. Two of
the three routes (first-party and third-party) are also the subject of the claim-discipline rules on
the public site.

**It is not fixable by extraction.** The text is extracted fine; the *parser* has no section to put it
in. Either a heading is added by the reviewer (an artefact decision, P5) or the heading scheme learns
what a document's front matter is. That is Q6, and it must not be silently bundled into the rows work.

---

## 2. Not a vision pipeline, and not a function per table

Both framings were asked, and both are already answered by decisions in this repo. Recording them
here so the answer stops being re-litigated:

### 2.1 A model may draft; a human must review — D70.2 (2026-10-27)

> *"A **vision-model extraction of the printed table is the fallback**, not the plan: if the shape is
> judged insufficient at UAT, the model drafts the table and a human reviews it into
> `knowledge/tables.py`. Either way it is reviewed data — a model's output cannot become a
> `DocumentChunk` unreviewed, for the same reason `TABLE_ROWS` was reviewed."*

So the door is open to a model **drafting**, and shut to a model **deciding**. The rejection is not
"models are bad at tables" (they are not); it is that the corpus contract is *traceable*: every block
must be a contiguous slice of the pages its page marker names, and an unreviewed model output is not a
slice of anything. A hallucinated fee inside `R500` would be invisible to every existing guard and
quotable by the chatbot.

**Also measured:** `-table` is a character-for-character permutation of `-layout` (identical
multiset, pages 2–9). That means an extraction-mode draft is *verifiably* non-lossy, which is why the
drafting step is cheap and the review step is the only expensive one.

### 2.2 The mechanism is data plus a guard — never a parser

There is no `parse_appendix_2()`. There is:

| Part | Where | What it is |
|---|---|---|
| the rows | `TABLE_ROWS: dict[str, tuple[TableRow, ...]]` | reviewed cells, in printed order, in Python |
| the printed structure | `TABLE_SECTIONS` (`columns`, `legend`, `dividers`) | reviewed: part headings, qualifiers, column labels |
| the verification | `TABLE_BANDS: dict[int, int]` + `test_tables.py` | the column offset of each cell in `-table` output — **this** is the only per-table code, and it exists so a reprint fails a test instead of silently re-pairing a substance with the wrong condition |
| the substitution | `ingest.py::chunks_for_sections` | a section whose ref is in `TABLE_ROWS` has its auto-chunks **replaced** by one chunk per row |

The reason a guard per table is unavoidable: a *presence* check passes on the broken pairing. From
Appendix 6a's implementation — *"`test_tables.py` pins each class to the value on its own printed
line — a presence check would pass on the broken `-layout` pairing."*

---

## 3. How the corpus manages tables today (measured inventory)

Three tiers, plus one layer that owns the *text* rather than the *pairing*:

| Tier | Mechanism | Covers today | Open |
|---|---|---|---|
| **Prose in columns** | `columns.py::de_column` (D46) | BPP 3–10, OPP 12, landscape 2/3/9 | — |
| **Rows that must pair** | `tables.py` reviewed rows (D51, D70.1) | `Appendix 2` — **30 rows**; `Appendix 6a` — **20 rows** | SAOSO Appendices 3, 4 Tables, 6b, 7; **landscape PDF 4–8**; OPP PDF 4, 11 |
| **Anything else** | shipped as extracted, read in the artefact diff (D53) | BPP + SAOSO artefacts | OPP, landscape artefacts (P4/P5) |
| **Text of record** | `knowledge/corpus/*.md`, sha256-pinned to the PDF, reviewed as a diff | `bpp.md`, `saoso.md` | `opp.md`, `landscape.md` |

The two layers are **not** alternatives, and the plan of record already says so
(`CORPUS_CANONICAL_FORMAT_PLAN.md` step 4, answer 4):

> *"Appendices 1–7: **the reviewed rows in `knowledge/tables.py` keep owning substance↔condition
> pairing; the artefact owns the page text.** Extend `TABLE_ROWS` for Appendices 3, 4 Table 1, 6a/6b
> and 7 inside this task (G4), using the committed `-table` pages so the verification needs no
> extractor."*

So "how do we manage other tables?" has a one-line answer: **a human decides what a row is, the row is
data, and a test pins each cell to the line it is printed on.** What is missing is not a better
extractor — it is a *decision about what a row is* for the four pages where the question is genuinely
open (Appendix 6b, OPP 4, OPP 11, and landscape 6).

---

## 4. Measured inventory of the landscape's tables

| PDF page | Printed title | Shape | Rows | What a "cell" actually is |
|---|---|---|---|---|
| 4–5 | `ESTABLISHING A PGS GROUP` | 5 columns | **3** (Step 1, 2, 3) | Step 1–2 on p4, the row numbering restarts on p5 after a repeated header. Cells are 60–400-character prose paragraphs |
| 6 | `PGS SEALS AND THEIR USE` | 5 columns | **2** (one per seal) | **two of the five columns are seal artwork**, not text; the adjacent column repeats the seal's name (`PGS Organic In-Conversion`, `PGS Organic`); "Use of seals and logos" is a prose column, not a cell |
| 7–8 | `SAOSO ORGANIC CERTIFICATION` | 5 columns | **3** (Step 1, Step 2, direct 3rd-party) | row 3 (`For farmers wanting direct 3rd party certification…`) opens on p8 under a repeated header |
| 2, 3, 9 | prose | 2 columns | — | `de_column` is **correct** here; must stay |
| 1, 10 | cover, blank | — | — | no text |

Totals: **3 tables, 5 columns, 8 rows** across 5 pages. Two of the thirty-five cells are images.

Two facts fall out that shape §6:

* **The row count is a judgement, not an extraction.** `Step 1/2/3` and the two seals are visible
  boundaries. "Is the fee its own row?" and "is a seal artwork cell a cell?" are not.
* **p6 is the Appendix 6b problem in miniature.** `saoso_text_glyphs_and_boundaries.md` §5b stays open
  because *"a 'row' has to be decided before it can be curated"*. Landscape p6 is the same shape of
  question with an image in it, and the PRD must not pretend otherwise by curating it silently.

---

## 5. Proposed solution

### 5.1 The row becomes N cells, without churning the two-cell tables

`TableRow(substance, condition)` is hardcoded at two cells. Generalise:

```python
@dataclass(frozen=True)
class TableRow:
    page: int
    cells: tuple[str, ...]          # 1..N, in printed column order
    section_ref: str = ""           # "" for a document with no numbering
    #: Kept as the 2-cell reading so Appendix 2/6a, `structure_for` and the reader do not churn.
    substance = property(lambda self: self.cells[0])
    condition = property(lambda self: self.cells[1] if len(self.cells) > 1 else "")
```

`text` stays "the cells, in reading order, joined by a line break" — which is already the documented
exception to *"a chunk is always `section.text[start:end]`"* (`chunking.py`, `tables.py` assumption 3)
and is what makes either cell quotable on its own.

**Open:** whether the join is a newline or a blank line. Propose newline: the chunk is a row, and a
blank line would make `passages.py` build two paragraph blocks for one row.

### 5.2 Reviewed rows keyed by `(doc_key, branch)` — the real code change

`rows_for("Appendix 2")` is a **global** key. The landscape prints no numbering at all, so its
chunks carry `section_ref = None` — a deliberate, CHECK-enforced design (`section_scheme="heading"`).
Giving it synthetic refs would break the citation scheme, so the key has to grow instead:

```python
TABLE_ROWS: dict[tuple[str | None, str], tuple[TableRow, ...]]
```

where the second element is `section_ref` when the document numbers its sections, and the branch's
**anchor** (`establishing-a-pgs-group`, `pgs-seals-and-their-use`, `saoso-organic-certification`)
otherwise — because the anchor is the locator the reader and the chatbot already use.

Consequences, all mechanical:

| File | Change |
|---|---|
| `knowledge/ingest.py::chunks_for_sections` | takes `doc_key`; `corpus_check` (P2.2) calls it too, so the expected count comes from the same code |
| `knowledge/tables.py::rows_for` / `structure_for` | key takes the document |
| `core/services/_documents.py` | the reader already has the document; pass it |
| `knowledge/tests/test_tables.py`, `test_table_sections.py`, `test_corpus_saoso.py` | key literals; **18 + N tests**, values unchanged |

### 5.3 What each row becomes

One `DocumentChunk` per row: `section_ref=None`, `heading_path` = the printed table title,
`page` = the printed page, `text` = the row's cells. This is `TableRow.as_chunk()` today. The rows
will therefore also fix §1.2 as a side effect: one chunk per step, no `R500` line to mistake for a
heading, and `ESTABLISHING A PGS GROUP` stops being a fragment.

### 5.2a Resolved 2026-10-29: the rows live in the artefact (§5.1 and §5.2 are superseded)

`Refinement/TABLES_AS_DATA_PRD.md` §7 Q1 asked whether a row is stored as a `tables.py` literal or in
the reviewed artefact. **The product owner answered: the artefact** — because the requirement is not
"fix this document" but "manage tables efficiently in every upcoming document", and one reviewed text
of record per document is the only shape that scales to the corpus still to come.

So the mechanism changes, and this PRD's §5.1 (N-cell `TableRow`) and §5.2 (`(doc_key, section_ref)`
key) are **not** the plan. What replaces them:

| | Python literals (superseded) | The artefact (decided) |
|---|---|---|
| where rows live | `knowledge/tables.py` | `knowledge/corpus/<doc>.md` |
| who reviews | a reviewer diffing Python | the same reviewer diffing the document |
| what a new table costs | a tuple, an import, a test file | typing it in the file it belongs to |
| the guard | `TABLE_BANDS` + `test_tables.py` | the same, driven by the block's declared columns |
| key | `(doc_key, ref)` | the artefact's own structure — a table block belongs to its section |

The syntax, the two parser restrictions it has to respect, and the retrieval consequence are in
`TABLES_AS_DATA_PRD.md` §3a. **This PRD now supplies that PRD's first real table** — three of them,
plus the front matter that has no table at all.

### 5.4 The reader renders the printed grid (D72.3) — and the grid does not fit as-is

The product owner chose the printed grid over the labelled-cells proposal, which also answers
`TABLES_AS_DATA_PRD` §7 Q2. Taken literally, it costs more than a template branch, and this is
measured, not argued:

| Measurement | Value |
|---|---|
| Widest row in `-layout`, PDF 4 / 5 / 7 / 8 | **323 characters** (PDF 6: 186) |
| The reader's reading measure (`core/static/css/reader.css`) | **38 rem ≈ 85 characters** at 16 px |
| The reader's outer working column | **72 rem ≈ 160 characters** |
| Where the **Fee** column starts, per page | **127 / 129 / 149 / 127 / 116** |

Read the last two rows together: the Fee column — the one holding `R500`, the thing the reader
reported — starts **beyond the measure on every page**, so at the current shape every row scrolls
sideways to reach the answer. At full working width (160 characters) the arrow is still ~2× too
wide. So "render the printed grid" needs one more answer, and there are four honest ways:

1. **Break the grid out to the 72 rem working column**, overflowing the reading measure on purpose.
   Still scrolls at 323 characters, but only ~2×, and only for tables.
2. **A scroll region with a sticky first column**, so the step label stays visible while the fee
   scrolls in. The `<table>` is real; the measure is a viewport into it.
3. **Stack below a breakpoint**: grid above ~900 px, one labelled block per row below it. This is
   option A again for phones, which is where most readers are.
4. **Reduce the table's type size** — at 13 px the 38 rem measure holds ~105 characters. Not enough
   on its own; a useful multiplier on 1 or 2.

A mock in `product/design/` decides between them (`DESIGN.md` §measure, ≥44 px targets); it is step 5
because it is the only part of this slice whose shape is a design question rather than a data one.

### 5.5 The guard, and the thing it must fail on

Per §2.2, one `TABLE_BANDS` entry per page for PDF 4–8, measured from `-table`. The measurement is
per page and per **cell**, not per header: the printed header offsets are already unstable across the
five pages (`Resource documents` starts at **37 / 38 / 34 / 32 / 33** on PDF 4 / 5 / 6 / 7 / 8), and a
cell's text does not begin where its header does. That instability is the reason Appendix 2 has four
entries for three pages (`76, 77, 78, 85`) rather than one. `test_landscape_tables.py` then pins **each cell to its own printed line**. A presence check is not
enough — that is the lesson Appendix 6a recorded. Break the guard deliberately (swap two cells) and
watch it go red before trusting it green (`testing_hazards.md`).

Also a corpus-level guard: **every table page in the four governed documents either has reviewed rows
or a recorded exclusion reason.** That is what stops this class from recurring in the next edition.

### 5.6 Sequencing with the landscape artefact (P5)
No dependency in either direction: the rows work today under `--from-pdf`, and the artefact (P5) will
own the *page text* while the rows keep owning the *pairing* (§3). Doing the rows **first** makes P5
reviewable — the reviewer sees a 10-page diff whose table pages are already decided, instead of being
asked to decide rows *and* diff pages at once.

### 5.7 Stop the mangling first, independently — and be honest about what it does

Whether or not any of the above lands this week, `PAGE_LAYOUT_EXCLUSIONS["landscape"] = {4,5,6,7,8}`
plus `EXPECTED_TRANSFORMED_PAGES["landscape"] = {2,3,9}` is three lines of data, an existing golden,
and one re-ingest.

**Measured, so the expectation is exact** — with the pages excluded and nothing else changed, the
document still produces **8 chunks** with **the same 6 branches**, and `ESTABLISHING A PGS GROUP` is
still cut mid-cell:

> … *Local PGS group determines the membership fee for farmers/ · **Step 1** · IFOAM PGS tool kit ·
> consumers/traders that are · PGS SA: How to set up a · part of the PGS group. · Farmers who are
> already producing • · **PGS group** · a surplus of organic produce and • …*

because raw `-layout` also puts `R500` at the start of a column segment, and `HeadingParser` still
reads it as a heading. Two honest gains, and no more: the fragments are in **reading order** instead
of being reordered into four column blocks, and the printed grid is visible to a human. Quotability
stays at 1/5 (§1.3).

So this is explicitly **not** the fix. Its only job is to stop the reordering while the rows are
designed — and if it cannot ship on its own, it should ship with step 3, not instead of it.

### 5.8 Pages 1–3 enter the same way (§1.4, Q6)

A reviewed front-matter entry — text plus a heading the reviewer adds, keyed by `(doc_key, branch)`
exactly as the rows are — needs no new mechanism and works under `--from-pdf` today. It is the same
trade as `TableRow`: the heading is not printed, the review is declared, and a test pins the passage
to its page. The alternative (teach the heading scheme to treat "text before the first heading" as a
section) changes the anchor scheme for every document and belongs with P5's artefact, not here.

---

## 6. Decisions needed — **all seven taken 2026-10-29**

| # | Question | Answer |
|---|---|---|
| D72.1 | What is a row on PDF 6? | **A** — a seal is a row; the artwork cell is its printed label |
| D72.2 | Is a fee a cell or a derived fact? | **A** — cell only; no `Fee` field, no number in the glossary |
| D72.3 | Reader shape? | **C** — render the printed grid (and see §5.4: it does not fit as-is) |
| D72.4 | Do OPP PDF 4/11 join this slice? | **A** — wait for the OPP artefact (P4) |
| D72.5 | Is PDF 5's continuation a row of the same table? | **A** — one table, three rows, page = where the row starts |
| D72.6 | Where do pages 1–3 come from? | **A** — reviewed front-matter passages, working under `--from-pdf` |
| D72.7 | Does the exclusion ship alone? | **A** — with the rows; one re-ingest |

Recorded in `PGS_PLATFORM_SPEC.md` §18.3. The table below is the reasoning each answer rests on,
kept because the costs are what a future reader needs — and because Q3's answer is the one whose
cost was **not** visible when the question was asked (§5.4).

The seven, as they were put to the product owner:

| # | Decision | Proposal | Why it cannot be settled by code |
|---|---|---|---|
| **Q1** | What is a row on p6, where **two of five columns are seal artwork**? | A row is a seal; the artwork cell is represented by its printed label; the corpus records that the image itself is not stored | The image is content the corpus cannot hold. Whether a seal's *picture* is citable is a product decision |
| **Q2** | Is the fee a cell, or also a derived fact (`R500`, `R1 000`, `R350`, `R2 500`)? | Cell only — no derived facts, no `Fee` model field | Design principle §"data encodes the group"; also `test_claim_discipline.py`'s neighbourhood: a fee lifted out of its conditions is a claim |
| **Q3** | Does the reader get labelled cells in this slice, or is "quotable, one chunk per row" enough? | In this slice — the reader is the surface the defect was reported on | Cost is a `DESIGN.md` mock + one template; leaving it means the public page still shows a soup |
| **Q4** | Do OPP PDF 4 and 11 join this slice, or wait for their artefact (P4)? | Wait — they have an artefact coming and are already excluded; this slice is the landscape | Scope discipline; but PP's p11 is also "a row must be decided" |
| **Q5** | Does the landscape's **p5 continuation** (Step 3 opens on a page whose header is repeated) belong to the `ESTABLISHING A PGS GROUP` rows or to a page-scoped second table? | One table with three rows, `page` = the page each step *starts* on | `DocumentChunk.page` is a single number (D42); a row spanning a page break has to pick one |
| **Q6** | **How do PDF 1–3 enter the corpus?** (§1.4) — they print no heading the parser opens a section for, so the answer to "what is a PGS?" and the three certification routes are not stored at all | **Reviewed front-matter passages** (§5.8) — text plus a reviewer-added heading, keyed by `(doc_key, branch)`, working today under `--from-pdf`. Alternative: do it inside the artefact conversion (P5) | The alternative (teach the heading scheme to treat "text before the first heading" as a section) puts unheadable prose into every document's branch list and changes the anchor scheme. Either way it is a decision about what the document *has*, which is the product owner's |
| **Q7** | **Does the page exclusion ship on its own re-ingest, or with the rows?** (not in the original six) | With the rows, unless they are more than ~a week out | Every `--force` re-ingest drops `ChatMessage.retrieved_chunks`, so the cost is not zero and the measured gain of the exclusion alone is reading order only (§5.7) |

Q1 and Q3 are the two that change the shape of the build. Q6 is the one that changes the product. Q2
and Q4 are scope. Q5 is a data detail with an existing precedent (`TableRow`'s seaweed row merges a
cross-page continuation "by hand and recorded"). Q7 is sequencing, and its answer decides how long a
public page stays wrong — it was added after the artifact was drafted, so it is the one question the
PRD did not start with.

---

## 7. Alternatives considered

| # | Alternative | Why not |
|---|---|---|
| A | **Vision model → JSON at ingest, no review** | D70.2. Unreviewed model output cannot be a `DocumentChunk`: it is not a slice of the pages its marker names, so the traceability contract (and `test_corpus_*`) stops meaning anything, and a wrong fee is quotable. Model *drafting* into a reviewed diff is allowed and cheap (§2.1) |
| B | **Switch PDF 4–8 to `-table` and stop there** | Measured: 0/5 sentences quotable, because cells share a line in every mode (§1.3). Plus it un-suppresses the running header, raising chunks 8 → 12 with furniture branches |
| C | **A layout library (`pdfplumber`, `camelot`) or a per-table parser** | It infers the pairing. §2.2's rule: a human reading 8 rows is cheaper *and* provable. Also `requirements.txt` carries no layout dependency and the extractor stays a single call (`extraction.py`'s whole reason for existing) |
| D | **Markdown tables in the canonical artefact (D53 v3)** | The right long-term home *if the number of tables grows*; today the plan of record assigns pairing to `tables.py` (Q4, §3) and it would cost a format version, a generator change and a new equivalence test before the landscape has an artefact at all (P5) |
| E | **Drop the landscape from the chat corpus** (keep it as the reader document) | The fee and seal facts are what the chatbot is actually asked. Dropping it turns a corruptible answer into a permanent "the standard does not cover this" |
| F | **Tune `MIN_COVERAGE` / add a band width cap so tables aren't detected** | Detection is a *geometry* judgement and works as designed; tables and prose columns look the same to it. The repo's answer to "detection is right but the transform is wrong" is `PAGE_LAYOUT_EXCLUSIONS` — data with a measured reason. That is §5.7 |

---

## 8. Requirements

1. **One chunk per reviewed row.** For each of the landscape's 3 tables, `DocumentChunk.text` is the
   row's cells in printed column order. Measured baseline: **8 chunks today, none of them pages 1–3**.
   With 8 rows and Q6 answered as proposed, the document is **11**: 3 + 2 + 3 rows, three front-matter
   passages (p2 intro, p3 routes, p9 colophon). The count is asserted in `test_ingest`, not estimated —
   and it is asserted *after* the front matter lands, so the two changes are separable.
2. **Every table page has rows or a recorded reason.** A test over the four governed documents fails
   naming the page when a table-shaped page is neither curated nor excluded.
3. **Each cell is a verbatim substring of `-table` output for its page** (whitespace-normalised), and
   `TABLE_BANDS` verification pins it to **its own printed line**, not merely to the page.
4. **No character invented.** The union of a row's cells is a subset of the page's non-space characters;
   a test asserts the whole-document multiset is unchanged apart from the reviews actually declared.
5. **`section_ref` stays `None`** for every landscape chunk (D42 / heading scheme). No synthetic refs.
6. **The key is document-scoped.** `rows_for`/`structure_for` cannot return one document's rows for
   another document's identically-named branch; a test with two documents sharing a branch key proves it.
7. **The reader is not mislabelled.** `structure_for` returns `None` whenever the corpus and the
   reviewed rows disagree — mislabelled rows are worse than no structure (existing rule, now exercised
   by 5 cells). The render itself is the printed grid (D72.3), with the fit decided in §5.4.
8. **A reprint fails loudly.** Moving a column on any of PDF 4–8 fails `test_landscape_tables.py`.
9. **`corpus_check` reports the same count** as an ingest would, from the same function (P2.2).
10. **Evidence links survive.** `--force` drops `ChatMessage.retrieved_chunks`; run
    `manage.py relink_evidence --apply` after the re-ingest and record the three numbers it reports.
11. **Pages 1–3 are stored** (Q6): the intro, the six basic elements and the three certification routes
    are quotable from one chunk each, and each is pinned to its printed page.

---

## 9. Execution steps

0. **Reproduce, before touching anything** — the numbers in §1 come from:
   `extract_pages` → `apply_layout(doc_key="landscape")` for the bands; `de_column` vs
   `pdftotext -table` for the three renderings; `concordance_sections()` for the 6 branches;
   the loss-free multiset check for the permutation claim. A session that skips this will re-derive a
   different story.
1. **The table block lands in the artefact format** (`TABLES_AS_DATA_PRD` §3a): parse-time structure,
   one chunk per row from the table code, and a *failing* guard on a malformed table annotation. Ship
   it against **one** table — this document's p4–p5 — because that is the table a person has already
   read and complained about.
2. **Convert the landscape: 10 pages.** The smallest of the four documents (OPP 15, SAOSO 101) and
   already "next" in the P5 rollout, so pulling it forward costs the least. It is also the only
   document whose *front matter* needs a reviewer's heading, which is the second thing this slice is
   for (D72.6). Reviewed diff, `sha256` pinned, `CORPUS_EDITS` for anything the generator cannot
do.
3. **Curate p4–p5 (`ESTABLISHING A PGS GROUP`, 3 rows)** — the page the reader reported. The review is
a human reading the page image; `-table` output is a drafting aid, per D70.2. Add the measured column
offsets and the line-pinned test. `EXPECTED_TRANSFORMED_PAGES["landscape"] == {2,3,9}` lands here, with
D72.7's single re-ingest and `relink_evidence`.
4. **Curate p7–p8 and p6** — with D72.1 (the seal row) and D72.5 (the page break) settled.
5. **Front matter (D72.6)** — the intro, the six elements and the three routes, as reviewed passages
   with reviewer-added headings in the same artefact. Independently testable: four probes that return
   **0** today must return 1 chunk each afterwards.
6. **The reader** (§5.4): mock in `product/design/` for the printed grid and its fit, `DESIGN.md`
   conformance, `css-alignment`.
7. **Close the loop**: `tests/uat/` scenario for the fee question, backlog move, spec §4.5 update, and
   the §5.7 exclusion verified as *reading order restored, nothing more*.

**Dropped from the plan:** step 2 of the previous version (the `(doc_key, ref)` key refactor). It only
existed because the rows were going to live in Python; §5.2a retires it.

---

## 10. Risks & hazards

| Risk | Mitigation |
|---|---|
| **A presence check passes on a broken pairing** — the 6a lesson | Pin each cell to its own printed line; deliberately swap two cells and watch the test fail |
| **A row is asserted where the paper has no row** (p6's artwork, p5's restart) | Q1 and Q5 must be answered *before* curation, and the answer recorded as a `TABLE_*` comment the way Appendix 2's assumptions are |
| **`TABLE_BANDS` is Xpdf-4-only** (`-table` does not exist in poppler, `exit 99`) | Unchanged constraint from D51; the guard runs off the **committed** page fixture, so the gate needs no extractor |
| **Re-ingest destroys answer evidence** | `relink_evidence --apply`, report the three numbers (P2.5a) |
| **The document-scoped key silently re-keys SAOSO** | Step 2 is a refactor with a fixed expectation: SAOSO **338 chunks**, anchors/pages unchanged |
| **Fixing 8 table rows is mistaken for "the landscape is fixed"** | The reader still renders the paper's 5 columns into a 38 rem measure; §5.4 is a design problem and is not implied by quotability |
| **The tables are fixed while the introduction stays missing** (§1.4) — the more useful half | Q6 is answered before step 3, and the DoD asserts the front-matter passages by *content*, not by count |
| **A single `TABLE_BANDS` offset for all five pages** — measured header offsets already differ page to page: column 2 starts at **37 / 38 / 34 / 32 / 33** on PDF 4 / 5 / 6 / 7 / 8, and the header offset is not the cell offset | One `TABLE_BANDS` entry per page, as Appendix 2 has (76, 77, 78, 85), and the guard measures the **cell** start, not the header's |

---

## 11. Definition of done

- [ ] `de_column` no longer transforms PDF 4–8; `EXPECTED_TRANSFORMED_PAGES["landscape"] == {2,3,9}`
- [ ] 8 reviewed rows across 3 tables, each cell pinned to its printed line
- [ ] `ESTABLISHING A PGS GROUP` is one branch containing all three steps, and no branch is `R500`
- [ ] *"Participatory Guarantee Systems are locally focused quality assurance systems"* and *"First-Party
      Claim"* are quotable from the corpus (they are in **0** chunks today, §1.4)
- [ ] "what does it cost to join a PGS group?" is quotable from one chunk, verbatim, and passes
      `audit_citations`
- [ ] the reader shows the printed grid (D72.3), and the Fee column is reachable without a scroll
      longer than the table itself (§5.4's four options, one of them chosen in a mock)
- [ ] the corpus-level guard fails on a newly-added uncurated table page
- [ ] `knowledge/tables.py`'s docstring assumption 7 (*"This covers Appendix 2 only"*) is rewritten —
      it has been false since 6a; it must not stay false for a third table
- [ ] UAT scenario signed; backlog moved; `PGS_PLATFORM_SPEC.md` §4.5 updated

---

## 12. Deferred, deliberately

* OPP PDF 4 and 11 (Q4) — their artefact arrives at P4.
* SAOSO Appendices 3, 4 Table 1/2, 6b, 7 — G4, already scheduled.
* Whether `tables.py` should eventually become part of the canonical artefact (Alternative D). The
  trigger to revisit is **more than ~6 curated tables**; below that, data-in-Python with a pinned guard
  is cheaper to review than a format version. **Note (2026-10-29):** this is no longer hypothetical —
  `TABLES_AS_DATA_PRD` §7 Q1 is the same question and is open, and it now gates step 3 here (§5.2a).

---

## Pre-Flight Checklist

- [x] No `core/models.py` change, no new app — this is chunk *content*, not schema (**no migration**)
- [x] No views/forms/URLs added
- [x] Service change confined to `core/services/_documents.py` (one call site: pass the document)
- [x] Tests: `knowledge/tests/test_landscape_tables.py` (new), `test_tables.py`, `test_table_sections.py`,
      `test_corpus_saoso.py`, `test_columns.py`, `knowledge/tests/test_ingest.py`
- [x] No migration; `--force` re-ingest only, with `relink_evidence`
- [x] No template logic; the reader shape comes from `structure_for`
- [x] Front-end touched only in §5.4, per `DESIGN.md`
