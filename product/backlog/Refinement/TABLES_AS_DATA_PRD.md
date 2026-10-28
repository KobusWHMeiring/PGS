# PRD: Tables as reviewed data — so the reader can display any table without new code

**Status:** **Refinement** — four questions in §7 need the product owner before a plan can be written.
The direction (a table is *data*, not a Python literal and not a parser heuristic) is agreed; the
**storage format** is not.
**Owner:** Product (what a table may claim) · Build (the format and the renderer)
**Opened:** 2026-10-28
**Origin:** two things from the same reading session. The reader now renders Appendix 2 as the paper's
table, and it is the **only** appendix that can: `TABLE_ROWS` is a hand-written tuple in
`knowledge/tables.py`, keyed `{"Appendix 2": …}`. Every other table in the standard still arrives as
run-together prose — measured in
`BugFixes/saoso_text_glyphs_and_boundaries.md` §5: Appendix 6a stores **20 animal classes and 20 values
on one page**, five values still attached and fifteen piled at the end. The product owner's question on
2026-10-28 was the right one: *"can we ingest tables as JSON/MD so that we can display them?"*
**Related:** `Done/READER_STRUCTURE_PRD.md` (D70.1/D70.2, the definition-list shape and the
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
2. **Does a four-column table render as a definition list too**, or does the reader need a second shape
   (a real grid) for Appendix 4 Table 1 and 6b's matrix? A grid at the 38 rem reading measure will not
   hold 6b's species columns without horizontal scroll.
3. **Is the vision-model draft in scope for the first table** (6a: 20 short rows) as a *draft* for a
   human to correct, or is every cell read by a person? D70.2 allows the former; it doubles the review
   discipline for one small table.
4. **Does Appendix 2 migrate now, or after 6a/6b prove the format?** Migrating first proves the format
   on a table whose output is already signed off — and risks churning the one thing that works.
