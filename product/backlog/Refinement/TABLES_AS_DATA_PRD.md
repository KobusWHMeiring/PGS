# PRD: Tables as reviewed data — so the reader can display any table without new code

**Status:** **Refinement** — **§7 Q1 answered 2026-10-29: option 2, the corpus artefact.**
**§7 Q2 answered the same day (D72.3): the printed grid.** **§7 Q5 answered 2026-10-29: a stored context
column** (D73). Q3 and Q4 can be answered inside the plan. **A plan can be written.**
**Owner:** Product (what a table may claim) · Build (the format, the renderer, the vector)

> **Who decides what — a correction, 2026-10-29.** Q5 was put to the product owner as a preference and
> should not have been: whether the embedded rendition is a pure function or a stored column is an
> engineering choice with an auditable answer. The tell is what the answer *changes*: a product decision
> changes **what the product claims** (is a fee a fact? may a seal's picture be cited? is a row one
> seal or three cells?). An engineering decision changes **how a claim is served and checked**. Only the
> first belongs on a decision page. The genuinely research-shaped part is the *effect size* — does
> contextual embedding text improve retrieval on this corpus? — and that is measurable (§7 Q6), which
> is what makes it research rather than taste.
**Opened:** 2026-10-28
**Origin:** two things from the same reading session. The reader now renders Appendix 2 as the paper's
table, and it is the **only** appendix that can: `TABLE_ROWS` is a hand-written tuple in
`knowledge/tables.py`, keyed `{"Appendix 2": …}`. Every other table in the standard still arrives as
run-together prose — measured in
`BugFixes/saoso_text_glyphs_and_boundaries.md` §5: Appendix 6a stores **20 animal classes and 20 values
on one page**, five values still attached and fifteen piled at the end. The product owner's question on
2026-10-28 was the right one: *"can we ingest tables as JSON/MD so that we can display them?"*
**Related:** `spike/RETRIEVAL_EVAL_SPIKE.md` (the instrument that prices Q6; **S1 done
2026-10-30**), `Done/READER_STRUCTURE_PRD.md` (D70.1/D70.2, the definition-list shape and the
vision-model fallback), `knowledge/tables.py` (the mechanism), `knowledge/corpus.py` (the reviewed
artefact format), `CORPUS_CANONICAL_FORMAT_PRD.md` (D53), `CHAT_ANSWER_COVERAGE_PRD.md` **G4**
(Appendices 3, 4, 6a/6b, 7 — the same work, seen from the chatbot's side)
**Plan:** not written

---

## 1. The state today, measured

| Where a table lives now | What it is | What it costs |
|---|---|---|
| `knowledge/tables.py::TABLE_ROWS` | A Python literal: `TableRow(page, substance, condition)`, reviewed 2026-10-21 | **Code, per table.** A new appendix is a new tuple, a new import, a new test file |
| `knowledge/tables.py::TABLE_SECTIONS` | A second literal: columns, legend, dividers | another literal, keyed the same way |
| `knowledge/corpus.py` (D53) | A reviewed **Markdown artefact** per document, with `<!-- page: N printed: M -->` markers, `##` headings and `CORPUS_EDITS` as data | the human review already happens here; it has no table syntax |
| the extraction (`pdftotext`) | whatever the reader's columns do | the values and their labels separate (§5 of the corpus bug) |

Only **one** of SAOSO's eight tables is curated. The other seven (`Appendix 3`, `4. Table 1`,
`4. Table 2`, `5`, `6a`, `6b`, `7`) are unquotable as rows, which is why **G4** exists and why the
chatbot answers table questions from prose or not at all.

## 2. What is agreed

**A. A table is data, and the data is reviewed.** Unchanged from D70.1/D70.2: no parser may infer a
row pairing, and a model's draft cannot become a `DocumentChunk` without a human reading it.

**B. The renderer must not know any table by name.** The reader's job is "a section whose data is rows
renders as a definition list"; today it does that, and it does it because `structure_for()` is generic.
The gap is on the *ingest* side: adding a table means editing a Python literal.

**C. Rows stay the unit of citation.** One `DocumentChunk` per row, so a quote may cover a cell or the
whole row and `audit_citations` keeps working exactly as it does for Appendix 2. Any format must be
able to produce that.

## 3. Options, with the cost each carries

| # | Format | Ingest | Review | Citation | Display | Verdict |
|---|---|---|---|---|---|---|
| **1** | **Keep the Python literals** (`TABLE_ROWS`) | a new key per table | read a diff of Python | 1 chunk per row, already proven | already proven | the status quo: correct, but **seven tables of code** |
| **2** | **Markdown tables inside the corpus artefact** (`knowledge/corpus/`, D53) | the artefact builder writes them out of the page; ingest reads them | the artefact **is** the review surface — a table is a table in a diff | rows become chunks; a cell is a substring | reader renders any table | **most consistent with D53**: one reviewed artefact per document, tables in it |
| **3** | **A JSON sidecar per document** (`knowledge/tables/*.json`) | a build step writes draft JSON; ingest reads it | review a JSON diff, plus the page | same | same | good structure, a second review surface to explain to a human |
| **4** | A Markdown table *in the PDF extraction path* | no build step | none — the extractor's pairing is unreviewed | — | — | rejected: unreviewed data (D70.2) |

Option **2** is the recommendation: it puts the table where the human already looks, and it makes
"reviewed artefact" mean one thing instead of two. Option **3** is the honest alternative if the
artefact format cannot express header rows, spans or the `South African specific` qualifiers that sit
*between* rows (the reason `TABLE_SECTIONS` exists separately today).

### 3a. Decided 2026-10-29: option 2 — and two measurements that constrain its syntax

**The product owner chose option 2** (tables in the artefact) after reading the pipeline question
below, so §7 Q1 is closed. Two things were then measured on the **shipped parser**, and both change
how the syntax has to look:

| Measured, on `knowledge/corpus.py` + `knowledge/chunking.py` | Result |
|---|---|
| A GFM pipe table (3 rows, no blank lines between rows), parsed then chunked | **1 chunk for the whole table** — the rows are a single paragraph, so no row can ever be cited |
| The same table with a blank line between every row | **still 1 chunk** — the chunker *packs* paragraphs to ~800 tokens, so a small table is one paragraph bundle |
| `<!-- cell -->` inside a row | **silently dropped** — `ANNOTATION` is `^(corpus\|page\|ref)\b`, so anything else is treated as a reviewer's note. The cell boundary is unrecoverable from the text afterwards |

So three rules follow, and they are requirements, not preferences:

1. **A table's structure is parsed as structure, never recovered from text** — the same treatment
   `sub_refs` already gets. `section.text` keeps the cells as ordinary lines so it stays a slice;
   the column labels and the row/cell boundaries travel beside it, exactly as `sub_refs` carries
   offsets rather than re-finding text.
2. **One chunk per row is produced by the table code, not by the chunker** — the substitution point
   exists: `ingest.py::chunks_for_sections` already replaces a section's auto-chunks with one chunk
   per reviewed row. Measured above, nothing in the chunker can do it.
3. **A table annotation that does not parse must fail.** Today `<!-- cell -->` is a comment and a
   typo (`<!-- cells -->`, `<!-- col: … -->`) is a *silent* no-op: the table loses its structure and
   every other guard stays green. That is the failure mode this repo's hazard log exists for.

**The proposed block** — the page marker already in force when a row starts is that row's page
(format rule 2), so a cross-page row needs no new annotation:

```markdown
<!-- table
cols: Key steps | Resource documents, guidelines and requirements | Use of seals and logos | Seals and logos | Fee
-->
<!-- row: Step 1 -->
<!-- cell -->
Farmers who are already producing • a surplus of organic produce and • organized as …
<!-- cell -->
- IFOAM PGS tool kit
- PGS SA: How to set up a PGS group
<!-- cell -->
Once formally established and paid-up members of PGS SA …
```

A row with no explicit label (Appendix 2, where the first cell *is* the label) takes the first cell as
its label and reuses `section_anchor()` for the anchor — which is what `TableRow.heading_path` already
does in Python (`f"{section_ref} — {label[:80]}"`). A cell may hold blank lines and lists, because the
`<!-- cell -->` delimiter is structural rather than a paragraph break — which is what Appendix 2's
five-paragraph conditions require.

**What this does to `TABLE_SECTIONS`:** the `dividers` (`I. PLANT AND ANIMAL ORIGIN`, `South African
specific`) become `<!-- row-divider: … kind -->` annotations between rows, and the `legend` becomes
the table block's `legend:` field. The reader keeps calling `structure_for()`; only its source changes.

## 4. What a table needs to express (so the format is chosen against a real shape, not a guess)

From Appendix 2 and the two appendices measured in §5 of the corpus bug:

1. **Two columns, named** (`Substances — description, compositional requirements` / `Conditions for
   use`) — Appendix 6a: `Class or species` / `Number per ha`.
2. **Dividers between rows** — `I. PLANT AND ANIMAL ORIGIN`, `South African specific` (a qualifier that
   applies to the row beneath it).
3. **An empty cell that means silence**, distinguishable from "no data captured" (19 rows today).
4. **Cells that carry their own columns** — Appendix 4 Table 1 is a 4-column list, Appendix 6b is a
   species × space matrix. The format must not assume two.
5. **A page marker per row or per group**, because a locator is the reader's only provenance.

## 5. Scope

**In:** Appendix 6a and 6b first (they are broken today and they are what G4 names first), then
Appendix 3, 4 Tables 1–2, 5 and 7 on the same mechanism. Appendix 2 migrates to the chosen format
rather than living in two places.

**Out:** the review itself (a human reading pages), the vision-model draft (D70.2 stays a *drafting*
aid), and any change to the citation audit, the chunker or retrieval.

## 6. What this closes

* **G4** — Appendices 3, 4, 6a/6b and 7 become quotable rows.
* **`BugFixes/…` §5** — 6a's 20 classes and 20 detached values; 6b's rabbit table.
* The chatbot's table answers stop depending on prose that happens to survive extraction.

## 7. Open — to settle before a plan

1. **Format: markdown in the corpus artefact (option 2) or a JSON sidecar (option 3)?** The
   recommendation is 2, because the artefact is already the review surface and D53's whole argument is
   one reviewed text of record per document. Confirm.
   **Now also gates a second task:** `LANDSCAPE_TABLES_PRD.md` step 3 (the certification landscape's 8
   rows) is blocked on this answer — typing them into `TABLE_ROWS` first and migrating later pays twice.
   Its content decisions are already taken (D72.1–D72.7) and are format-independent; only the storage is
   waiting.
2. **Does a four-column table render as a definition list too**, or does the reader need a second shape
   (a real grid) for Appendix 4 Table 1 and 6b's matrix? A grid at the 38 rem reading measure will not
   hold 6b's species columns without horizontal scroll.
   **Answered 2026-10-29 (D72.3):** the reader renders the **printed grid**, not a definition list, for
   a table whose rows are wider than two cells. The question was asked against Appendix 4/6b and it was
   answered against the certification landscape's five-column tables, which is the same shape. The
   measurement above is the live cost and is now the open part of the answer: a landscape row is **323
   characters** wide in `-layout` against a **38 rem (~85 character)** measure — the Fee column starts at
   character 116–149, i.e. beyond the measure on every page — so "the grid" still needs its fit decided
   (working column, scroll region with a sticky first column, stack below a breakpoint, or a smaller table
   type size). That fit applies to 6b too. See `LANDSCAPE_TABLES_PRD.md` §5.4.
3. **Is the vision-model draft in scope for the first table** (6a: 20 short rows) as a *draft* for a
   human to correct, or is every cell read by a person? D70.2 allows the former; it doubles the review
   discipline for one small table.
4. **Does Appendix 2 migrate now, or after 6a/6b prove the format?** Migrating first proves the format
   on a table whose output is already signed off — and risks churning the one thing that works.

5. **What does the vector represent for a row that is three tokens long?**
   *Found 2026-10-29, measured. **Answered 2026-10-29: a stored context column** (D73).*
   Curated rows are the smallest chunks in the corpus by an order of magnitude: Appendix 6a's twenty
   rows are **3–4 tokens** each (`Ewes / 13,3`), and **all twenty of the corpus's 3–4-token chunks are
   6a rows**; Appendix 2 ranges from **5 characters** (`Guano`) to 769. All 385 chunks carry a vector,
   and retrieval fuses the lexical and vector arms by rank (RRF, k=60). A vector for `13,3` carries no
   signal — so for a row whose words the query does not share (`"sheep"` vs `"ewes"`, `"how many birds
   per hectare"` vs `"Laying hens / 230"`) the vector arm contributes noise where it is the only hope.
   The visible symptom measured: `"laying hens"` and `"laying hens 230"` **do** retrieve page 85 (the
   lexical arm), while `"how many laying hens per hectare"` returns **no hits at all** — the query is
   fused by AND over its terms, so the row is reachable only by its own words.
   **Recommendation:** embed a *context string* — the table's title, the column label and the cell —
   while the chunk keeps only the cells, so quotes and the reader are unchanged:
   `"Appendix 6a · Maximum number of animals per ha equivalent to 170 kg N/ha/year — Ewes: 13,3"`.
   **Decided: a stored column**, not a pure function. A function would be cheaper, but it puts the
   vector space in a code path: change the string and every existing vector silently belongs to a
   different space, with nothing failing — the same class of defect the `-enc UTF-8` decode cost this
   repo 83 characters to learn. Stored, the deploy gate can compare `embedding_text` digests and
   `corpus_check` can say "this box's vectors are from an older rendition", which is the property that
   makes a second embedding change safe. The column is derived and re-derivable, so storing it costs
   storage, not truth. The separation itself is not a preference: embedding a context-rich rendition
   while citing the verbatim source is established practice (contextual retrieval, contextual chunk
   headers, column-prefixed table serialisation); only the *effect size here* is unmeasured — Q6.

6. **What is the retrieval effect size, and how would we know?** *Research — needs an instrument this
   repo does not have.* `knowledge/tests/test_retrieval.py` asserts **floors** ("some `S20` clause comes
   back"), not rankings: there is no recall@k, no MRR, no set of questions with expected chunks. So
   every argument about embedding shape — this one included — is currently settled by reasoning, not
   measurement. Asking for 10–20 real farmer questions with their expected passage, run through each
   candidate (bare row, context row, lexical only, vector only), would turn all of them into a number
   and would also price the earlier D49 `search_terms` work. **Proposed as a `spike/` item** rather than
   folded in here, because it is an instrument, not a feature: it should exist before the *next* table
   with 200 rows arrives, not after. Until it exists, adopt the practice and say the improvement is
   assumed, not measured.

   **The instrument now exists (2026-10-30).** `spike/RETRIEVAL_EVAL_SPIKE.md` S1 landed:
   `knowledge/tests/data/retrieval_eval.json` (35 graded questions), `scripts/eval_retrieval.py`
   (`bare` / `lexical` / `vector` today, `context` refusing until the column exists), and the baseline
   in that file's §8a. Two things it already says about **this** decision, before the column is built:
   `how many sheep can I run per hectare?` retrieves **no** Appendix 6a row on either the product path
   or the semantic arm alone, and the product finds the answering passage at rank 1 on **6 of 32**
   answerable questions. So D73 still stands as *assumed* improvement — and the assumption is now
   falsifiable in one command rather than in an argument.

   **Standing rule for the plan when it is written** (§8.5 of the spike): **every new table adds 2–3
   questions to the set in the same commit**, with `asked_by: design`, graded from the paper. A table
   that arrives without them has no evidence that it is retrievable at all, and the set rots back into
   a snapshot of whatever was measured once.
