# PRD: The certification landscape's tables — reviewed rows, and the rule for every other table

**Status:** In Progress — **all seven decisions taken 2026-10-29** (D72.1–D72.7, §6); **step 0 and step 1 built 2026-10-30** (§12a): the format, the guard and one-chunk-per-row land, and the measurements in §1 were reproduced exactly. Not built: the landscape artefact (step 2), curation with `TABLE_BANDS` (steps 3–4), front matter (step 5), the reader's grid (step 6).
**Resolved 2026-10-29:** the rows live in the **corpus artefact**, not in `tables.py` (§5.2a), so step 2
is dropped and the landscape's conversion moves ahead of its PRD's own place in the rollout.
Decision artifact: `product/design/d72_landscape_tables_questions.html`.
Finding §1.4 (pages 1–3 are not in the corpus at all) was found while verifying §1.3 and is **larger
than the tables**; it is in this PRD because it is the same document and the same re-ingest.
**Owner:** Corpus (D53 artefact review) · Build (the guards)
**Public title:** Readable tables in the certification landscape
**Summary:** Five table pages in the certification landscape document become readable rows, instead of text flattened into a paragraph.
**Public:** yes
**Last Updated:** 2026-10-30
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
| Widest row in `-layout`, PDF 4 / 5 / 7 / 8 | **323 characters** (PDF 6: 186) — **the page's blank padding line, not a row**: corrected below |
| Printed row **content**, PDF 4 / 5 / 6 / 7 / 8 | **157 / 162 / 157 / 169 / 153** characters (last printed character) |
| The reader's reading measure (`core/static/css/reader.css`) | **38 rem ≈ 85 characters** at 16 px |
| The reader's outer working column | **72 rem ≈ 160 characters** |
| The **passages pane** the grid actually gets | **52.5 rem ≈ 117–134 characters** (72 − 17 tree − 2.5 gap) |
| Where the **Fee** column starts, per page | **127 / 129 / 149 / 127 / 116** |

**Corrected 2026-10-31.** The 323 figure is `max(len(line))` on the page, which is the blank
padding line; the printed row's last non-space character sits at **153–169**. The problem is one
column's worth, not two. And the grid cannot use 72 rem: it lives in the passages pane, 52.5 rem,
because the tree takes 17 rem and the gap 2.5. At 14 px that pane holds ~134 characters, so the
Fee column starts at the edge and finishes **25–40 characters past it** — a short scroll, not a
voyage. The full argument and live mocks are `product/design/d76_reader_table_fit.html` (D76).

Read the last two rows together: the Fee column — the one holding `R500`, the thing the reader
reported — starts **beyond the 38 rem measure on every page**, so at the current shape every row
scrolls sideways to reach the answer. At the passages pane's full width (52.5 rem at 14 px) the
fee starts at the edge and only its last **25–40 characters** scroll.

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

0. **Reproduce, before touching anything** — ✅ **done 2026-10-30**, every number matched (§12a). The numbers in §1 come from:
   `extract_pages` → `apply_layout(doc_key="landscape")` for the bands; `de_column` vs
   `pdftotext -table` for the three renderings; `concordance_sections()` for the 6 branches;
   the loss-free multiset check for the permutation claim. A session that skips this will re-derive a
   different story.
1. **The table block lands in the artefact format** (`TABLES_AS_DATA_PRD` §3a): parse-time structure,
   one chunk per row from the table code, and a *failing* guard on a malformed table annotation.
   ✅ **Mechanism done 2026-10-30, and proved red first.** ✅ **Now proved against a shipped table**
   (2026-10-30): all 8 landscape rows live in `knowledge/corpus/landscape.md` and
   `test_landscape_table_block.py` pins 286 cell lines to their printed lines. Three deviations
   from §3a's draft syntax, all recorded in §12a.
2. **Convert the landscape: 10 pages.** The smallest of the four documents (OPP 15, SAOSO 101) and
   already "next" in the P5 rollout, so pulling it forward costs the least. It is also the only
   document whose *front matter* needs a reviewer's heading, which is the second thing this slice is
   for (D72.6). Reviewed diff, `sha256` pinned, `CORPUS_EDITS` for anything the generator cannot
   do.
   ✅ **The three tables landed 2026-10-30** (`knowledge/corpus/landscape.md`, pdf 4–8; §12c).
   **Front matter (pdf 1–3) and the colophon (p9) are still step 5**, so the artefact deliberately
   starts at p4 and `test_the_front_matter_is_still_absent` records the gap.
3. **Curate p4–p5 (`ESTABLISHING A PGS GROUP`, 3 rows)** — the page the reader reported. The review is
   a human reading the page image; `-table` output is a drafting aid, per D70.2. Add the measured column
   offsets and the line-pinned test. `EXPECTED_TRANSFORMED_PAGES["landscape"] == {2,3,9}` lands here, with
   D72.7's single re-ingest and `relink_evidence`.
   ⚠ **Partially done 2026-10-30** (§12c): three rows, the per-line/order guard, D72.7's one re-ingest
   (8 → 11 chunks) and `relink_evidence`. **`TABLE_BANDS` — the measured column offsets — is not
   built**, so a transposition *inside one printed row-line* is still unpinned; it is deferred to the
   reader (step 6), which is the surface that measures the columns.
4. **Curate p7–p8 and p6** — with D72.1 (the seal row) and D72.5 (the page break) settled.
   ✅ **Done 2026-10-30** (§12c): p6 is 2 seal rows; p7–p8 is one table of 3 rows (the third has no
   printed step number).
5. **Front matter (D72.6)** — the intro, the six elements and the three routes, as reviewed passages
   with reviewer-added headings in the same artefact. Independently testable: four probes that return
   **0** today must return 1 chunk each afterwards.
   ✅ **Done 2026-10-30** (§12d): four probes, each 1 chunk; the colophon (p9) came with it. p1 is a
   cover and p10 is blank, so neither contributes a chunk.
6. **The reader** (§5.4): mock in `product/design/` for the printed grid and its fit, `DESIGN.md`
   conformance, `css-alignment`.
   ✅ **Built 2026-10-31** (§12e): `product/design/d76_reader_table_fit.html` decides the fit (D76);
   the reader renders a real `<table>` with a sticky first column, a scroll region and a stacked
   phone layout. It also corrected §5.4's 323-character measurement (the page's blank line, not the
   row). The decision is the product owner's to confirm in the artifact; the implementation follows
   the recommendation (A + B + C, with 14 px as the multiplier).
7. **Close the loop**: `tests/uat/` scenario for the fee question, backlog move, spec §4.5 update, and
   the §5.7 exclusion verified as *reading order restored, nothing more*.

**Dropped from the plan:** step 2 of the previous version (the `(doc_key, ref)` key refactor). It only
existed because the rows were going to live in Python; §5.2a retires it.


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

- [x] `de_column` no longer transforms PDF 4–8; `EXPECTED_TRANSFORMED_PAGES["landscape"] == {2,3,9}`
      — **done 2026-10-30** (§12b)
- [x] 8 reviewed rows across 3 tables, each cell **line** pinned to its printed line — **done
      2026-10-30** (§12c). `TABLE_BANDS`' column pin is still open (step 3's ⚠), so a transposition
      *within one printed row-line* is not yet caught
- [x] `ESTABLISHING A PGS GROUP` is one branch containing all three steps, and no branch is `R500`
      — **done 2026-10-30** (`test_a_tables_rows_are_passages_of_their_branch`)
- [x] *"Participatory Guarantee Systems are locally focused quality assurance systems"* and *"First-Party
      Claim"* are quotable from the corpus (they are in **0** chunks today, §1.4) — **done 2026-10-30**
      (§12d): the four probes each resolve to one chunk, and `First-Party Claim` is its own branch
- [x] "what does it cost to join a PGS group?" is quotable from one chunk, verbatim, and passes
      `audit_citations` — **proved on the artefact 2026-10-30**
      (`test_the_landscape_fee_is_quotable_from_its_reviewed_row`)
- [x] the reader shows the printed grid (D72.3), and the Fee column is reachable without a scroll
      longer than the table itself — **done 2026-10-31** (§12e): `d76_reader_table_fit.html` chose
      the fit, and the reader renders the grid with a sticky first column and a stacked phone
      layout. The fee is in view at the pane's full width; only its last 25–40 characters scroll.
      **The D76 choice itself is the product owner's to confirm in the artifact.**
- [ ] the corpus-level guard fails on a newly-added uncurated table page — **open**: it needs a
      cross-document definition of "table-shaped page", and the landscape's pages are the only ones
      curated so far

- [x] `knowledge/tables.py`'s docstring assumption 7 (*"This covers Appendix 2 only"*) is rewritten —
      it has been false since 6a; it must not stay false for a third table. **Done 2026-10-30**: it
      now names both storages (Python literals and the artefact block) and which appendices remain
      uncurated
- [ ] UAT scenario signed; backlog moved; `PGS_PLATFORM_SPEC.md` §4.5 updated — **§4.5 updated
      2026-10-30**; the `tests/uat/` fee scenario and the sign-off are **step 7**

---

## 12. Deferred, deliberately

* OPP PDF 4 and 11 (Q4) — their artefact arrives at P4.
* SAOSO Appendices 3, 4 Table 1/2, 6b, 7 — G4, already scheduled.
* Whether `tables.py` should eventually become part of the canonical artefact (Alternative D). The
  trigger to revisit is **more than ~6 curated tables**; below that, data-in-Python with a pinned guard
  is cheaper to review than a format version. **Note (2026-10-29):** this is no longer hypothetical —
  `TABLES_AS_DATA_PRD` §7 Q1 is the same question and is open, and it now gates step 3 here (§5.2a).

---

---

## 12a. Built 2026-10-30 — steps 0 and 1, and what they cost the plan

**Step 0 reproduced §1 exactly.** `_scratch/step0_landscape.py` prints, from a fresh in-process
build: the eight transformed pages with the band lists of §1.1; **8 chunks and 6 branches**
including `R500` and `PGS SA.`; **1 / 2 / 0 of 5** paper sentences quotable in raw, `de_column` and
`-table`; the non-space multiset identical on **every** page 2–9; **0 chunks** containing
`Participatory Guarantee Systems`, `six basic elements`, `First-Party` or `Third-Party`; and the
§5.7 simulation confirming the exclusion alone leaves the document at 8 chunks / 6 branches. No
number in §1 needed correcting.

**Step 1 shipped the mechanism** — `<!-- table` … `<!-- /table -->`, parsed as structure:

| Where | What |
|---|---|
| `knowledge/sections/__init__.py` | `TableCell` (a slice of the section), `ParsedTableRow` (cells, label, page, dividers), `ParsedTable` (columns, rows, legend), and `ParsedSection.tables` |
| `knowledge/corpus.py` | the block parser, the annotation vocabulary, and the refusals (§7) |
| `knowledge/tables.py` | `chunks_for_parsed_section` — prose chunked by the chunker, **one chunk per row** from the table code — and `row_chunk` |
| `knowledge/ingest.py` | `chunks_for_sections` now walks **sections**, so a table section cannot be substituted by a same-ref section elsewhere |
| `knowledge/tests/test_corpus_tables.py` | 29 tests: 19 refusals, 10 structure/chunk assertions |
| `knowledge/tests/test_landscape_table_block.py` | 13 tests over **p4's real rows** (fixture, not corpus): five columns, 400-character cells, two cells the paper leaves empty, the seal's printed label, and the fee sentence quotable from one chunk |

**Proved red first, as §9's preamble asks.** `<!-- cell -->` outside a block, `<!-- cells -->` inside
one, a `table` with no `cols:`, an unclosed block, a heading inside a block, a row with more cells
than columns, a row that never closes, a dangling divider — each fails with the file and line named.
The word-pin guard was also broken deliberately (`aggregate` → `agregate`) and went red before being
restored.

**Three deviations from §3a's proposed block, all deliberate:**

1. **The block closes explicitly** with `<!-- /table -->`. §3a's sketch showed no close. Without one,
   the table ends by inference, and the last row silently owns every paragraph after it — the same
   class of defect as the dropped `cell`, one layer up. A table that is never closed **raises**.
2. **A `row-divider`'s kind trails the text** (`<!-- row-divider: South African specific qualifier -->`),
   which is how §3a writes it. It becomes `TableRowDivider(text, kind)` because `TableDivider` already
   renders the two kinds differently.
3. **Prose outside the rows becomes its own chunk.** §8's requirement 1 predicts **11 chunks** for
   the document (8 rows + 3 front-matter passages). Measured on p4's draft, the table's lead-in
   sentence (`The table below outlines the steps …`) is prose in the section and chunks on its own, so
   the count will be **12, not 11**, unless the reviewer folds each lead-in into a row. Silent text
   deletion to hit a predicted number is the worse trade. **The count is asserted after the artefact
   lands (step 2), as measured — not before.**

**Two things the build found that change steps 2–3:**

- **The generator was emptying every draft but SAOSO's — fixed the same day.** `--doc landscape`
  produced five headings and the page numbers with no body text, because the generic branch set
  `keep = is_page_furniture` and that helper returns what the artefact must *not* carry. The
  predicate is now `body_filter(parser)` (`tests/tools/test_build_corpus.py`, red first) and the
  draft carries **316 lines** — which are the §1.2 soup on p4–8, exactly as expected, and missing
  p1–3 because no heading opens there. **Direction recorded as D75:** repair the generator, then
  review as a verification pass. Two small steps remain before step 2 is a diff rather than a
  transcription: the BPP body-furniture rule (regenerating `bpp.md` now differs by 57 lines) and a
  regeneration test that runs under `PDFTOTEXT_BIN=/usr/bin/true`. Step 2 still needs D72.7's page
  exclusion landed first, or the generated p4–8 is the mangled text rather than the printed grid.
- **There is no `landscape` `-table` page fixture** (`knowledge/tests/fixtures/pages/` carries
  `layout` and `raw` only), so §8's requirement 3 — "each cell is a verbatim substring of `-table`
  output" — cannot be asserted yet. Step 3 must add `landscape.table` via
  `scripts/extract_fixtures.py` and pin each cell to its printed column (`TABLE_BANDS`), or the guard
  is a word-presence check, which Appendix 6a already proved insufficient.

---

## 12b. Built 2026-10-30, session 2 — the two preconditions, and §8 requirement 3 corrected

**Steps 2 and 3 are still not done. Both of their preconditions now are.** No artefact exists for the
landscape, and nothing was re-ingested, so no evidence link was dropped and the live corpus is
untouched.

| Landed | Where | Evidence |
|---|---|---|
| the `landscape` `-table` page fixture | `scripts/extract_fixtures.py` `PAGE_MODES`, `pages/landscape.table.txt` | 10 pages, 30 494 bytes, `pdftotext version 4.00`; **every other page fixture byte-identical** (md5 checked before/after) |
| D72.7's page exclusion | `knowledge/columns.py` `PAGE_LAYOUT_EXCLUSIONS["landscape"]` (pdf 4–8, one entry per page) | `apply_layout` now changes **{2, 3, 9}**, and `EXPECTED_TRANSFORMED_PAGES["landscape"]` says so |
| a per-line cell guard | `knowledge/tests/test_landscape_table_block.py` | 14 tests; proved red four ways (below) |
| the BPP body-furniture rule | `scripts/build_corpus.py` `BODY_FURNITURE` + `drop_body_furniture` | regenerating `bpp.md`: **57 → 32 diff lines, and every remaining line is whitespace** |

### 12b.1 §8 requirement 3 is false as written, and the truth is what `TABLE_BANDS` was for

Requirement 3 says *"each cell is a verbatim substring of `-table` output for its page"*. Measured
2026-10-30 on p4: **no whole cell is contiguous in it.** `-table` renders row-*lines*, not cells — one
output line carries the current line of every column at once:

```text
Farmers who are already producing    •  IFOAM PGS tool kit    …    Local PGS group determines the
```

So the Step 1 description is interrupted by two other columns' text. What is true, and what the
requirement is reaching for, is **per printed line**: every line a cell carries is a contiguous run
inside one line of the `-table` rendering, and a cell's lines appear on the page in order. That guard
is now in `test_landscape_table_block.py`, and it was **proved red four ways**: `R500` → `R5OO` in the
fee cell (4 tests fail), the seal label `Proud member of` → `Proud member for`, two Step 1 lines
swapped, and a cell's lines reversed. The swap and the reversal are caught **only** by the order
check — the word-presence test passes both, which is the Appendix 6a lesson repeating.

The fixture's one declared join (`self-assessment`, hyphenated across a printed line break, with the
continuation two interleaved rows later) is named in the test as data rather than cleaned out of the
draft, so every other line stays literal.

**Still not pinned, and it is step 3's job:** that two lines on the *same* printed row belong to the
columns they are filed under. A transposition inside one row-line keeps its position, so it passes.

### 12b.2 The generator is now a reviewable diff for the BPP — and it was corrupting the text

Three things came out of making `bpp.md` regenerable, in descending order of seriousness:

1. **`apply_review` was mangling the artefact's most important passage.** The footnote-2 entry was
   `kind="move"`, and a move is not a substitution, so applying it deleted `must be preferably
   composted` and printed `land available will not be allowed.` a second time at the foot of page 4.
   Nothing caught it, because the traceability test compares `flat()` strings and `flat` joins lines —
   a corruption that reintroduces the line above reads as a faithful move. Split into a lift and a
   place (two edits, `MAX_EDITS` 7 → 8), and `apply_review` now preserves a replacement's own line
   breaks so a moved paragraph keeps its shape.
2. **Its multiplicity guard was dead.** The docstring promised `SystemExit` when an edit "matches more
   than once"; the code called `subn(..., count=1)` and checked the *substituted* count, which is 1
   whenever the pattern matches at all. The count is now taken before the substitution. Both fixed
   red-first; `apply_review` had no test at all before this session.
3. **The furniture is data, because inference was measured and it destroys SAOSO.** "A line printed
   on N pages is furniture" — `General Principle` is on 26 pages of SAOSO, `Requirements:` on 25,
   `South African specific` on 18, and all three are content. "A repeated block is furniture" —
   SAOSO prints one poultry derogation verbatim on pages 45, 46 and 47. So `BODY_FURNITURE` names the
   BPP's four `The Principle / Of X.` pairs and the filter keeps the block on the page that first
   carries it. Same shape as `PAGE_LAYOUT_EXCLUSIONS` and `PAGE_LAYOUT_BANDS`.
   Also here: private-use-area codepoints (U+F06E) are stripped — not quotable text, both shipped
   artefacts carry none, and it is the character that kills `--stdout` on Windows
   (`testing_hazards.md` §3.21); and a page whose only surviving line is blank no longer gets a page
   marker (the BPP ended with `<!-- page: 13 printed: none -->` and nothing after it).

**Residual, and deliberately not chased:** 32 diff lines for `bpp.md`, every one of them whitespace —
the non-space character multiset and the sequence of non-blank lines are **identical**. Two causes,
neither a generator defect: the reviewer removed blank lines before page markers (SAOSO's reviewer
kept them, so a rule here would have to be per document), and the artefact keeps one leading space
where it dropped a glyph. Chasing those would mean a per-document blank policy for no product gain.

**What this session did not do:** no landscape artefact, no `TABLE_BANDS`, no front matter, no
re-ingest, no `relink_evidence`. `fast.sh` **1393 passed / 1 skipped in 29 s** (warm; quote the range,
`testing_hazards.md` §3.17).

**The next act is unchanged and is step 2** — and one thing the draft now shows that it could not
before: with p4–8 in printed order the parser opens **three false headings**, `## R500`, `## PGS SA.`
and `## SAOSO`, because a fee cell and a seal caption are CAPS lines. The DoD already forbids them
("no branch is `R500`"); they are the first thing the reviewer must remove, and their removal is what
makes `ESTABLISHING A PGS GROUP` one branch of three rows.

---

## 12c. Built 2026-10-30, session 3 — steps 2–4: the landscape is a reviewed artefact

**State: green, re-ingested, and the landscape is current.** `fast.sh` **1407 passed / 1 skipped**
(78 s warm) and `verify.sh` **1421 passed / 1 skipped in 92.6 s** (`--create-db`, port 5433). The
artefact covers **PDF 4–8**; front matter (1–3), the colophon (9), `TABLE_BANDS` and the reader are
not built.

| Landed | Where | Evidence |
|---|---|---|
| the artefact | `knowledge/corpus/landscape.md` | 3 sections, 3 tables, **8 rows**, sha256 pinned; each cell is a slice of its section |
| the declaration | `CORPUS_DOCUMENTS["landscape"]["corpus_artefact"]` | `corpus_check`: `landscape 11 / 11 current` |
| the three false headings gone | the artefact | `R500`, `PGS SA.` and `SAOSO` are a fee cell and two seal captions; `REVIEWED_BRANCH_TITLES` is empty |
| the rows guard | `test_landscape_table_block.py` | **286 cell lines**, each a verbatim *ordered* run of a printed `-table` line; proved red four ways |
| the traceability guard | `test_corpus_landscape.py` | identity, no invented character, prose contiguity, the measured count, the recorded front-matter gap |
| the count | **11 chunks** | 8 rows + 3 prose blocks (p4 lead-in, p6 trailing, p7 lead-in). §12a's 11/12 was 8 rows + 3 front matter + the lead-in; front matter is step 5 |
| D72.7's single re-ingest | dev box | **8 → 11 chunks**, all embedded, **0 evidence links dropped**; `relink_evidence --apply`: **0 relinked / 0 no-longer-has** |

### 12c.1 What the review found that the draft could not

1. **The Fee column is one merged box.** `-table` renders `Annual membership fee … R500` level with
   `Step 2`, and `Local PGS group determines…` a line above `Step 1`. The paper prints no row rule in
   that column, so the cell cannot be split: it is filed under **Step 1**, where it starts, and the
   table's legend says so. The reader's fee question is therefore answerable from one chunk.
2. **A table section with no lead-in produced a heading-only chunk.** `PGS SEALS AND THEIR USE` opens
   straight into its rows, and `_prose_chunks` chunked the pre-cell gap as `## PGS SEALS AND THEIR
   USE` — retrievable, citable, and saying nothing. `_prose_chunks` now drops a chunk that is only
   the section's heading. Proved red by reverting it: the count goes 11 → 12 and both guards fail.
3. **`row_chunk`'s em-dash label was becoming a branch.** `heading_path` is
   `ESTABLISHING A PGS GROUP — Step 1` and `_branch_key` split only on ` > `, so the concordance
   would have listed eight branches instead of three. `_branch_of` strips the row label; no printed
   heading in the four governed documents contains an em dash, so the split cannot take a real
   heading apart. Proved red by reverting it.
4. **The eval set named a locator this fix deletes.** `uat-saoso-logo` expected `pgs-sa`, the false
   branch anchor. It now names `saoso-organic-certification-step-2`, which contains the phrase the
   item asks for; `test_every_locator_resolves_against_the_ingested_corpus` is what caught it.

### 12c.2 Regeneration is still manual, and `--force` is hazardous

`scripts/build_corpus.py --doc landscape` still emits the **soup**, not a `<!-- table -->` block: the
generator has no rule that produces one and `CORPUS_EDITS` is a text substitution. So
`--force --doc landscape` would overwrite the review with the p4–8 column interleave. The per-line
guard fails immediately if that happens (the cells are gone), so it cannot ship silently — but do not
run it to "refresh" this file. The generator's table-block emission is a separate piece of work
(`TABLES_AS_DATA_PRD`), and until it exists the landscape is reviewed by hand and protected by
`--force`'s own refusal.

**Not built, and named rather than hidden:** `TABLE_BANDS` (a transposition inside one printed
row-line is unpinned), the corpus-level table-page guard, front matter (p1–3, p9), the printed-grid
reader, and the UAT scenario. Steps 5–7 of §9.

---

## 12d. Built 2026-10-30, session 4 — step 5: the front matter, and four probes that were zero

**State: green, re-ingested, and the landscape is current at 17 chunks.** `fast.sh` **1419 passed /
1 skipped in 38.6 s** (warm) and `verify.sh` **1433 passed / 1 skipped in 53.3 s** (`--create-db`,
port 5433; the same tree measured 92.6 s an hour earlier — quote the range,
`testing_hazards.md` §3.17).

| Landed | Evidence |
|---|---|
| the intro (p2) | `## INTRODUCTION`; `Participatory Guarantee Systems` resolves to **1 chunk** |
| the six elements (p2) | `## SIX BASIC ELEMENTS` (reviewer-added, because the paper says `6`); the probe `six basic elements` resolves to **1 chunk** |
| the three routes (p3) | `## First-Party Claim`, `## Second-Party Certification`, `## Third-Party Certification` — the paper's own Title-case headings, which the PDF parser deliberately ignores |
| the colophon (p9) | `## COLOPHON`; funders, copyright and disclaimer, pinned to PDF 9 |
| the count | **17 chunks**: 8 rows + 3 table-prose + 6 front-matter sections |
| D72.7's second re-ingest | dev box: **11 → 17 chunks**, all embedded, **0 evidence links dropped**, `relink_evidence --apply` **0 relinked / 0 no-longer-has**; **394 chunks, 0 unembedded** |

### 12d.1 What the front matter cost, and what it found

1. **Three headings are the reviewer's, three are the paper's.** `INTRODUCTION`, `SIX BASIC
   ELEMENTS` and `COLOPHON` are not printed; `test_the_reviewer_added_headings_are_not_printed`
   asserts that on the page, and the three route headings are Title case and *are* printed — which
   is exactly why `HeadingParser` (UPPERCASE only) opened no section on p3.
2. **Page 1 is a cover and page 10 is blank.** Page 1's only line is the running header (furniture),
   so it contributes no chunk; `COVERED` in `test_corpus_landscape.py` says so.
3. **The no-invention guard caught a glyph the extraction lost.** The paper's text layer has
   `which is “owned’` — a double open quote closed by a *single* quote (U+2019), on both
   renderings. The artefact first typed `”`, and `test_it_invents_no_character` failed on exactly one
   character. It now reproduces the page rather than correcting it; whether that is the paper's
   typo or the extractor's is a `CORPUS_EDITS` decision, not a silent fix.
4. **The routes are three sections, not one.** The paper prints three headings, so they are three
   branches; folding them into one would have required a fourth, unprinted `##` heading with no body
   — the heading-only chunk `PGS SEALS` already taught us to avoid.

**Not built, and named:** `TABLE_BANDS` (step 3's ⚠ — a transposition inside one printed row-line),
the corpus-level table-page guard, the printed-grid reader (step 6), and the UAT scenario/backlog
move (step 7).

---

## 12e. Built 2026-10-31 — step 6: the reader draws the printed grid, and the fit is measured

**State: green, committed, and the dev box's reader is live.** `fast.sh` **1434 passed / 1 skipped**
(36.6 s warm) and `verify.sh` **1448 passed / 1 skipped in 49.7 s** (`--create-db`, 5433; quote the
range, `testing_hazards.md` §3.17). The D76 decision is **recommended and implemented**, but the
choice is the product owner's: the artifact is the decision surface, not a ratification.

| Landed | Where | Evidence |
|---|---|---|
| the decision artifact | `product/design/d76_reader_table_fit.html` | four options with live mocks from the real Step 1/Step 2 rows; recommendation; radio + notes + export |
| the artefact grid | `knowledge/tables.ArtefactGrid`, `artefact_grid_for`, `align_artefact_grid` | columns + cells from the reviewed artefact, aligned to the passages the reader has; `None` on any disagreement |
| the reader grid | `core/services/_documents.py` (`_artefact_grid`, `ReaderGrid`) | five columns, 3/2/3 rows, per-row anchors and pages |
| the markup | `document_reader.html` | one `<table class="reader__grid">`, sticky `<th scope="row">`, `data-label` per cell, prose outside the grid |
| the CSS | `reader.css` | full passages-pane width, 14 px, scroll + sticky, stacked below 900 px, no raw hex |
| `DESIGN.md` | §7.13 | the component, its rules and the measured fit |
| the guards | `core/tests/test_document_reader_grid.py` (12), `test_corpus_tables.py` (3), `tests/e2e/test_reader_layout.py` (+2 browser) | five column names, fee in the grid, lead-in outside it, each row's anchor, the seals table, the fallback; 1280 px no scroll, 390 px restack |

### 12e.1 §5.4's 323-character measurement was the page, not the row

The decision artifact's Part 1 re-ran the measurement (its command is quoted there). `max(len(line))`
on a `-layout` page returns the **blank padding line** (323 on PDF 4/5/7/8, 186 on PDF 6), not the
printed row. The row's last non-space character sits at **153–169**. And the grid's real pane is
**52.5 rem**, not 72: the tree takes 17 rem and the gap 2.5. So the fit is **one column's worth**,
not two — the fee starts at the pane's edge and only its last 25–40 characters scroll. The PRD's
§5.4 is corrected in place.

### 12e.2 The recommendation, and what would change it

**A + B + C, with D as the multiplier:** a real `<table>` at the passages pane's full width, a
14 px grid; a scroll region with a sticky first column for the remainder and for zoom; the same
markup stacked below 900 px with `data-label` column names. What would change it: if the fee wraps
so far that the amount is not visible with a short scroll (check the mock at 840 px), the grid
should go full-bleed below the tree; if the reading measure must be inviolable, stack everywhere.

### 12e.3 What is still open

- **D76's confirmation** — the product owner reads `d76_reader_table_fit.html` and picks; the
  implementation is one CSS/template change away from any of A–D.
- **`TABLE_BANDS`** — a transposition *inside one printed row-line* is still unpinned. It is a
  corpus guard, not a reader feature; it was step 3's ⚠ and is still open.
- **The corpus-level table-page guard** — still needs a cross-document definition of “table-shaped”.
- **Step 7** — the `tests/uat/` fee scenario, the backlog move, and the §5.7 exclusion verified as
  “reading order restored, nothing more”.

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
