# PRD: Corpus column-aware extraction (all four governed documents)

**Status:** In Progress — built 2026-10-20; UAT Scenario 9 unsigned
**Owner:** Build — knowledge ingestion (sub-plan B), grounded chat (sub-plan D)
**Last Updated:** 2026-10-19 — errata folded in (see “2026-10-19 Errata” at the end)
**Plan:** `CORPUS_COLUMN_EXTRACTION_PLAN.md` (tasks C1–C9; it supersedes §5 where they disagree,
and both were reconciled on 2026-10-19)
**MVP:** MVP 0 — defect fix. Blocks the UAT scenario 1 judgement ("does the bot quote?",
D23) and must land before MVP 1a starts.
**Scope:** The stored text of all four governed documents. The generic per-page transform,
its fixtures, its golden page expectations, and the re-ingest. **Not** in scope: retrieval
ranking, the citation audit's rules, embeddings, table row reconstruction, OCR.
**Reference:** `PGS_PLATFORM_SPEC.md` §4.5, D15, D41, D42, D43, D44 (and D46, proposed
below); `MVP0_PLAN_V2.md` A10/B2/B6/B7; `knowledge/extraction.py`;
`knowledge/sections/heading.py`; `product/docs/context/testing_hazards.md` §1.17;
live evidence recorded 2026-10-19.

---

## 1. Problem Statement

**32 of the corpus's 139 pages are laid out in columns, and their text is stored
column-interleaved.** `pdftotext -layout` keeps both columns on one visual line, so reading
the page line by line alternates columns:

```
The organic farm is an element
a. Mechanisms and practices to
within an environment or ecosystem.
increase levels of organic matter in
```

A human can read that page. The database cannot be quoted from it, because
`audit_citations` accepts a citation only when the quote is a **verbatim, whitespace-
normalised substring** of one retrieved chunk. Interleaved text makes that impossible for
any sentence that spans the column.

**Observed, live, on 2026-10-19.** The question *"Do i need to know where horse manure
comes from before I can use it?"* was refused twice. The corpus answers it — BPP "2. Soil
Management", SAOSO Appendix 2 ("Farmyard manure, slurry and urine"), SAOSO §4.4 — and the
model produced the correct answer with the correct quote both times:

```
answer: "Yes, you need to know where horse manure comes from before you can use it.
         Animal manure must preferably be composted and sourced from farms under
         organic management or extensive farming practices…"
PROBLEMS: ('general-principles: the quote is not in the cited chunk',
           'Appendix 2: the quote is not in the cited chunk')
```

Both failures are the same defect: the sentence exists on the paper page and not in
`DocumentChunk.text`. The model was punished for a faithful render of a Passage we
corrupted at ingest.

**Why this is a product defect, not a data nuisance.** The refusal is identical to the one
used when the standard genuinely does not answer a question, so every affected question
becomes an `EscalatedQuery` that reads like a corpus gap (`testing_hazards.md` §1.17). The
BPP is the guidance layer; the appendices are where "may I use this input?" is answered.
Failing there is failing the questions the group actually receives.

**It is not:** a prompt problem, a retrieval problem, or an audit problem. Two earlier
fixes (locator normalisation; output-cap truncation) removed the *other* causes of the same
refusal; after them the manure question still fails, and the audit's reason now names the
chunk and the quote. Nothing downstream of the corpus can repair a passage that was
scrambled before it was stored.

## 2. Strategic Goal

Every passage a reader can locate on the printed page is quotable verbatim from the stored
corpus — in all four governed documents, not only the two that are obviously two-column.

## 3. Proposed Solution

### 3.1 Measured inventory (this is the scope)

Measured against the shipped PDFs on 2026-10-19 by a full-page scan for stable vertical
whitespace bands. "Column page" = a page where the detector finds at least one column
boundary (see §3.2).

| Document | Pages | Column pages | Which (page numbers as the reader sees them) |
|---|---|---|---|
| SAOSO Standard | 101 | **13** | printed 76, 77, 79, 81, 82, 83, 85, 86, 87, 88, 89, 90, 91 — Appendix 2 (fertilisers), 3, 4 Table 1, 4 Table 2, 6a, 6b, 7 |
| Basic Production Principles | 13 | **8** | PDF 3–10 — every body page, including the manure page (4) |
| The SA Organic Certification Landscape | 10 | **8** | PDF 2–9 |
| Outeniqua PGS OPP | 15 | **3** | page 4 (§3.1 committee roles table), 11 (§6.5 labelling categories), 12 |
| **Total** | **139** | **32** | **107 pages must remain byte-identical** (108 if §3.4's review excludes OPP PDF 11) |

The OPP result is the reason this PRD is not "BPP + landscape". The OPP contains **tables**,
and §6.5 is the labelling-categories table ("Self-claim organic", "Free range",
"Conventional") — a real farmer question, and exactly the content the public site is
forbidden to overclaim about (D17, `test_claim_discipline.py`).

Single-column control pages measured unchanged: SAOSO printed 40 and 60, OPP pages 1, 6 and
8, BPP PDF 1 and 2. The two populations separate cleanly on the detector's score (0.70–1.0
for column pages, 0.16–0.17 for prose), so no per-document allow-list is needed to *detect*.

The detector in fact flags **33** pages — one more than the 32 in scope. SAOSO **PDF page 2**
(printed 1) is the table of contents, whose right-hand column *is* the printed page numbers;
transforming it detaches every entry from its page and takes `parse_toc` from 29 entries to 8
(§3.4). It is a **measured exclusion**, not an omission.

**Numbering.** SAOSO prints `PDF page − 1`; the other three print `PDF page` or nothing. The
detector sees PDF pages (`extract_pages()[n - 1]`), so §3.4's golden table is stated in **PDF
page numbers**, which is the only form the code and the tests can assert against.

### 3.2 The transform contract

New module **`knowledge/columns.py`**, pure Python, no Django, no PDF library, deterministic:

```python
def column_bands(page: str) -> list[tuple[int, int]]:
    """Maximal vertical whitespace bands: (start, end) column indices."""

def de_column(page: str, *, bands: list[tuple[int, int]] | None = None) -> str:
    """The page in reading order — column 1 top-to-bottom, then column 2, ….
    A page with no qualifying band is returned byte-identical."""
```

Algorithm, with the parameters the prototype proved on the real PDFs:

1. **Band detection.** For each column index `i`, the *coverage* is the fraction of lines
   that cross `i` (non-space both sides) and are blank at `i`. A band is a maximal run of
   indices with coverage ≥ **0.70**, requiring ≥ **6** crossing lines and ≥ **12%** of the
   page's non-space characters on each side. One boundary per band, at the band start.
   - No band width cap: the landscape's gutters are 16+ characters wide, and pruning wide
     bands loses entire pages (measured).
2. **Split only where the line is blank across the band.** A line that has text at the band
   positions (a spanning footnote, a full-width heading, a table row that overflows its
   cell) is **not** cut; it stays one fragment and is assigned by its own start position.
3. **Assign fragments by their own start position**, not by their index in the cut list.
   This is the bug that made the first prototype reorder the OPP labelling table: a line
   that ends before a band has fewer fragments, and index-based assignment puts them in the
   wrong column.
4. **Emit columns left to right**, preserving blank runs within each column.
5. **No band ⇒ return the page unchanged.** The fallback is a no-op, never a guess.

Prototype evidence (a throwaway implementation run during refinement on 2026-10-19;
`_scratch/` is git-ignored, so the measurements are recorded here rather than linked):

```
BPP p4+p5 (the section spans a page break): quote_contiguous=True  chars_preserved=True
SAOSO p77 (Appendix 2 conditions cell):     quote_contiguous=True  chars_preserved=True
SAOSO printed p40 (single-column control):  byte-identical=True
OPP p1/p6/p8, BPP p1/p2 (controls):         byte-identical=True
```

### 3.3 Where it plugs in

- **Ingest:** `knowledge/ingest.py` applies `de_column` to every page after
  `extract_pages()` and before the section parser. No `CORPUS_DOCUMENTS` change, no
  `layout` flag, no migration: the layout is a property of the page, and detection is code.
- **`IngestReport` gains `layout_pages: tuple[int, ...]`** — the PDF page numbers that were
  transformed. No schema change; it exists so the operator's log and the tests can see the
  transform happened, rather than inferring it.
- **Exclusions:** `knowledge/columns.py` carries a module-level data table
  `PAGE_LAYOUT_EXCLUSIONS: dict[str, dict[int, str]]` (document → PDF page → measured reason)
  that `apply_layout()` consults, and `de_column()` stays a pure function of a page string.
  This is the mechanism §3.4 assumes: once a band is found, a pure function has no way to
  decline, so "stays byte-identical" needs a hook. Data, not a `layout` field — a retarget to
  another standard needs no migration, and a page that is column-laid-out but must not be
  transformed carries its reason next to its page number.
- **Fixtures:** `scripts/extract_fixtures.py` runs the identical pipeline
  (`pdftotext -layout` **then** `apply_layout`) for every fixture whose page range contains a
  column page. Measured: **`bpp_intro` (PDF 3–4), `landscape_seals` (6–8), `opp_4_1` (4)**.
  `saoso_appendices` (71–73) is **not** affected — its pages carry no band. `saoso_toc` (2–3)
  would be affected, but SAOSO PDF 2 is excluded (§3.4), so that fixture must come out
  byte-identical: a useful negative control. `MANIFEST.json` records the pipeline
  (`pdftotext -layout` + `de_column v1`) and the **raw page hash**, so a fixture remains
  checkable evidence rather than a hand edit.
- **`knowledge/sections/heading.py`:** delete the two paragraphs claiming body attribution
  is "approximate" and that "a column-aware extractor is deferred". They will be false.
  Keep `COLUMN_GAP` segment splitting: harmless, and still needed for any line that keeps
  two headings side by side. The same file also needs `_page_stamp` fixed — it reads the
  *last* non-blank line, and reordering moves the landscape's bare page number into the
  middle of the page, silently nulling every landscape citation (requirement 10). Also
  correct its claim that "the BPP stamps none": measured, the BPP stamps on some pages.

### 3.4 The golden-page rule (the guard against silent mangling)

The transform is generic; **which pages it transforms is pinned by a data expectation in
the tests**, one row per document, with the reason for every excluded page that is
column-laid-out but not transformed.

```python
# PDF page numbers — `extract_pages()[n - 1]`. SAOSO prints pdf - 1, so printed 76-91 is
# pdf 77-92. The first draft of this table used printed numbers and could not be asserted.
EXPECTED_COLUMN_PAGES = {
    "saoso":     set(range(77, 93)) - {79, 81, 85},  # printed 76-91 minus 78, 80, 84
    "bpp":       {3, 4, 5, 6, 7, 8, 9, 10},
    "landscape": {2, 3, 4, 5, 6, 7, 8, 9},
    "opp":       {4, 11, 12},                       # 11 only if the review accepts it
}

# Column-laid-out pages that must NOT be transformed, with the measured reason.
PAGE_LAYOUT_EXCLUSIONS = {
    "saoso": {
        2: "table of contents: its right-hand column IS the printed page numbers; "
           "de-columning takes parse_toc from 29 entries to 8 and puts Appendix 1's "
           "end on p.80 instead of p.75 (measured 2026-10-19)",
    },
}
```

A page that is column-laid-out but fails a golden check is **listed as not transformed, with
its reason**, and stays byte-identical. That is how this repo already records the SAOSO/OPP
parsing realities (D41, `heading.py`'s known gaps), and it means coverage can be widened
later by changing a row, not by redesigning the detector. A third test asserts that every
detected page is **either** transformed **or** excluded, so no page can fall between the two
lists — which is the silent failure this section exists to prevent.

**Known hard case — 3-column tables.** The OPP §6.5 table has a narrow first column. The
prototype preserves every character there but gets the reading order wrong:

```
Self-claim    Applies where there is no organic
organic       certification and the organic claim is self-  label or seal.
declared.
```

Character-multiset tests pass on that. Therefore: OPP page 11 and SAOSO Appendix 4 pages are
**in scope only if their golden expectation shows a correct reading order during the build**;
if not, they are recorded as not transformed (byte-identical), with the follow-up named.
The PRD's success gate is the manure question, which needs BPP and Appendix 2 — both proven
above.

### 3.5 What this does not do

- It does not reconstruct **table rows**: after de-columning, a row's cells are separated,
  not associated. A quote is checkable on paper (the reader can find the condition), but a
  reader/model must not assume the cell above it is its row. Recorded as a risk, and the
  reason the corpus is guidance, not an assessable verdict, for the appendices.
- It does not change the citation audit, retrieval, prompts or the answer cache.
- It does not embed the corpus (separate defect: 0 of 345 chunks carry a vector).

## 4. Technical Requirements

1. `knowledge/columns.py` imports nothing from `core` and nothing from Django; it is a pure
   function of a page string. `lint-imports` untouched.
2. **Not idempotent, and not assumed to be.** It runs once, at ingest, on `-layout` output.
   Measured: a second pass is a no-op on BPP p4 and OPP p11 (their bands vanish), but
   **landscape p4 gains three new bands and reorders further**. The tests therefore assert
   what is true: a re-run still preserves the non-space multiset, and the pipeline applies the
   transform exactly once.
3. **Loss-free:** for every page, the multiset of **non-space, non-newline** characters is
   identical before and after. Newlines are excluded deliberately: reordering changes them by
   definition, so counting them reports all 32 transformed pages as total data loss. This is
   the guard against a dropped footnote, header or column — and it is only a guard beside the
   golden page set, because it passes happily when the transform never runs.
4. **Deterministic:** same bytes in, same bytes out; no environment, locale or clock input.
5. **No model or migration change.** `DocumentChunk`, `StandardDocument`, `StandardSet`
   schemas are untouched. `_corpus_fingerprint()` (chunk count / max id) invalidates the
   answer cache automatically on re-ingest.
6. **Parser compatibility:** after the transform, each parser must produce the *same*
   `section_ref`/`anchor`/`page` set as today. A test asserts the sets are equal; any
   difference is a documented exclusion, not a silent change. Measured: SAOSO (271 sections),
   OPP (28) and BPP (4) are identical, and `parse_toc` is unchanged because PDF 2 is excluded.
   **The landscape is not** — see requirement 10.
7. **Fixtures stay evidence:** regenerated through the recorded pipeline; the manifest
   records the pipeline string and the raw page hashes; no fixture is hand-edited.
8. **Idempotent re-ingest:** `ingest_standard` keeps its `created=False` no-op on sha256;
   a forced re-ingest replaces chunks and drops the old `retrieved_chunks` rows (recorded
   risk, not a blocker — historical turns render from `ChatMessage.content`).
9. `IngestReport.layout_pages` is populated per document and asserted in tests (BPP = 8
   pages, SAOSO = 13, OPP = 3 or 2, landscape = 8), so a detection regression fails loudly.
   The values must come from the golden table, with one literal (`BPP = 8`) pinned separately:
   otherwise a detector that regresses to zero takes the golden set with it and both agree.
10. **The landscape's page attribution must be rescued, not dropped.** `heading.py::_page_stamp`
    finds a bare page number by reading the *last* non-blank line. That is the raw page's
    furniture, and reordering moves it to roughly line 50 of 90 — so after the transform every
    landscape section loses its `page` (all `None`, D42 violated). Fix: search for the last
    bare-number line **anywhere** on the page. Verified to restore `[4, 4, 6, 7, 7, 9]` and to
    leave SAOSO, OPP and BPP output identical (BPP stays `[None, None, None, 10]`). A test pins
    all four sets.

## 5. Execution Steps

1. **Write the failing tests first** (`knowledge/tests/test_columns.py`):
   - the BPP quote is contiguous across PDF pages 4–5 (fails today);
   - the Appendix 2 conditions cell is contiguous on SAOSO PDF page 77, printed 76 (fails
     today);
   - non-space, non-newline character multiset preserved on every page of all four PDFs;
   - single-column controls are byte-identical;
   - no band ⇒ unchanged page (the same object, not merely an equal string);
   - every detected page is either transformed or in `PAGE_LAYOUT_EXCLUSIONS`.
2. **Implement `knowledge/columns.py`** until those tests pass. No other file changes yet.
   Checkpoint: review the module and the golden table before ingestion is touched.
3. **Add the golden expectation per document** and the parser-compatibility test
   (`section_ref`/`anchor`/`page` sets unchanged). Any page that fails is recorded as not
   transformed, with its reason.
4. **Regenerate the affected fixtures** through `scripts/extract_fixtures.py` — `bpp_intro`,
   `landscape_seals`, `opp_4_1` (measured; `saoso_appendices` is *not* affected, and
   `saoso_toc` must come out unchanged because SAOSO PDF 2 is excluded); update
   `MANIFEST.json`; confirm the anchor checks still pass; restore `heading.py`'s docstring
   to the truth.
5. **Wire `de_column` into `ingest_standard`** and add `IngestReport.layout_pages`.
   Checkpoint: re-run the full suite.
6. **Re-ingest the corpus locally** (`--no-embed`), record `layout_pages` per document and
   the new chunk count; assert the BPP chunk that carries "2. Soil Management" now contains
   the full sentence.
7. **End-to-end proof, on the verbatim sentence — not on the recorded reply.** A test feeds
   the **corpus sentence** (the exact quote in §6) to `audit_citations` against the
   re-ingested chunk and asserts it is accepted. A second test feeds the model's actual
   2026-10-19 reply and asserts it is **refused**: that reply paraphrased the standard
   ("must preferably be composted and sourced from farms under organic management or
   extensive farming practices"), so a perfect corpus does not make it verbatim. Pinning the
   refusal is what stops a later session loosening the audit to make a recorded answer pass.
   Then one manual live call for the same question, whose quote must be verbatim.
8. **UAT draft + close the loop:** add the human check to
   `tests/uat/mvp0_standards_and_public_site_uat.md`, append any new hazard to
   `testing_hazards.md`, and run `python product/backlog.py --write`.

## 6. Success Criteria

All measured checks were ticked on 2026-10-20; the two live UAT checks were not, and the
build outcome below names why. The "107" in the fifth box was measured against the PRD's
32-page scope; the detector finds 33 (including the TOC), so the actual figures are 29
transformed + 4 excluded + 106 single-column pages.

- [x] `de_column` returns the BPP sentence *"Animal manure must be preferably composted
      prior to application, and must be sourced from farms under organic management, or from
      extensive farming practice."* as one contiguous run inside a single stored chunk.
- [x] The Appendix 2 condition *"Shall not constitute the main source of nitrogen in the
      absence of complimentary and additional nitrogen generating practices on farm and shall
      not be from conventional intensive livestock production systems without prior
      permission from the control body"* is contiguous in the stored Appendix 2 chunk.
- [x] The **verbatim corpus sentence** for the manure question (quoted in the first bullet) is
      accepted by `audit_citations` against the re-ingested chunk, and the paraphrased
      2026-10-19 reply is still refused (the audit is not loosened to fit a bad quote).
- [x] Character multiset (non-space, non-newline) preserved on all 139 pages of all four PDFs.
- [x] The pages in `EXPECTED_TRANSFORMED_PAGES` are transformed exactly (29), the four
      exclusions are byte-identical with their reasons (SAOSO PDF 2, 82, 83; OPP PDF 11), and
      the remaining 106 single-column pages are byte-identical.
- [x] SAOSO/OPP/BPP/landscape parsers yield the same `section_ref`/`anchor`/`page` sets —
      including the landscape's page numbers, which requirement 10 had to restore.
- [x] Fixtures regenerated via the recorded pipeline; `MANIFEST.json` carries the pipeline
      and raw page hashes; no hand edits.
- [x] Full suite green (526), `lint-imports --no-cache` kept.
- [ ] Live re-run: the manure question returns a grounded answer with a BPP citation and an
      Appendix 2 citation that both render a quote the reader can find on paper. **Not met
      2026-10-20:** the corpus half is met (stored sentence and audit tests). Two earlier live
      turns were refused because the model fabricated a `sub_ref` or elided a quote with `…`;
      D47 fixed that contract and a re-run on 2026-10-20 returned a grounded answer with three
      verbatim Appendix 2 citations. A later informal question (`can i use horse manure?`)
      exposed one more split sentence on BPP PDF 4 — a left-column list item overflows the
      detected band — fixed by the measured `PAGE_LAYOUT_BANDS` override `(40, 42)`, and the
      same question then answered with six verbatim citations. Neither run cited a BPP
      passage, so the BPP half of this box remains for the human UAT. See "2026-10-20 Build
      outcome".

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| A badly-split page silently loses text (the classic failure: it looks like a corpus gap) | Per-page character-multiset test over all four PDFs; no-op fallback |
| A false-positive split mangles single-column prose | Measured separation (0.70–1.0 vs 0.16–0.17); byte-identical control tests per document |
| 3-column tables reordered (proven on OPP §6.5) | Golden page expectation; those pages stay untransformed and are listed as follow-ups |
| A parser stops finding headings/appendices after the transform | Parser-compatibility test on `section_ref`/`anchor`/`page` sets, before re-ingest |
| Fixtures stop being evidence | Same pipeline as ingest, pipeline + raw hash in `MANIFEST.json`, no hand edits |
| Chunk ids churn, breaking history | `_corpus_fingerprint()` invalidates the cache; turns re-render from content; noted in the PRD and release note |
| A new edition of a PDF changes layout and detection drifts | Golden test fails loudly; the expectation is data, not inference |
| Table row association is lost in reading order | Recorded in §3.5; the corpus is guidance for appendices; the reader checks the page |
| **Reordering moves page furniture, so a parser that reads a stamp by position loses it** (measured: `heading.py::_page_stamp` returns `None` for every landscape page) | Requirement 10: search for the bare-number line anywhere; a test pins each document's `page` set before and after |
| **De-columning a table of contents destroys its page-number column** (measured: `parse_toc` 29 → 8 entries, Appendix 1's span end moves p.75 → p.80) | SAOSO PDF 2 is an exclusion with its reason; the TOC-map test asserts `parse_toc` is unchanged |
| **A test written against the recorded model reply can never pass** — that quote is a paraphrase | §5 step 7 and §6 assert the verbatim sentence is accepted and the paraphrase is refused, so the audit's strictness is pinned rather than relaxed |
| A loss-free test passes for the wrong reason because the transform never runs | Paired with the golden page set, plus one pinned literal count (BPP = 8) that the golden set cannot drag along
| Scope creep into retrieval | Non-goals list; the retrieval defect (rarest-term arm) gets its own PRD |

## 8. Non-goals

- Re-embedding the corpus, or the vector arm (separate defect: 0/345 chunks embedded).
- Retrieval ranking (`search_terms`'s rarest-term arm returning Appendix 6b for "horse").
- Loosening the citation audit (a reordered quote is not a quote).
- Table row reconstruction, multi-page table models, or OCR.
- Changes to the OPP/SAOSO citation schemes (D15, D42, D43, D41).

## 9. Decision required — proposed D46

Recorded as **D46** in `PGS_PLATFORM_SPEC.md` §18.3 on 2026-10-20. The PRD's first
number (D45) was already the Homtini visit-flow decision; this section's "D46" is the
recorded decision.

> **D46 | Corpus layout handling. | Every page is passed through a column-aware transform
> at ingest, selected by measurement rather than by document. The transform is loss-free
> (non-space, non-newline character multiset preserved) or a no-op, and the set of pages it
> transforms is pinned by a golden expectation per document in the tests.** A page that is
> column-laid-out but not transformed is an asserted, documented exclusion with a reason,
> held in a data table (`PAGE_LAYOUT_EXCLUSIONS`) rather than in a flag — a pure function
> cannot decline once a band is found, so the exclusion needs a home. Consequence: `layout`
> is not a field on `StandardDocument` and not a `CORPUS_DOCUMENTS` flag — a retarget to
> another standard needs no migration, and a new edition that mis-detects fails a test rather
> than silently degrading citations. Alternative rejected: a per-document `layout: two-column`
> flag, which would have missed the OPP's three table pages (measured) and reintroduced the
> "retarget requires code" cost. Measured consequences of taking this decision are in
> "2026-10-19 Errata" below.

## 10. UAT (human-judged only)

Added to `tests/uat/mvp0_standards_and_public_site_uat.md`:

1. Ask `/ask/`: *"Do I need to know where horse manure comes from before I can use it?"*
   - the answer is grounded (not a refusal);
   - at least one citation is the Basic Production Principles, and its quote can be found
     on page 2 of the printed document;
   - at least one citation is SAOSO Appendix 2, and its quote is the condition attached to
     "Farmyard manure, slurry and urine" in the printed table.
2. Confirm the same question in a fresh conversation still answers (not a cache artefact).
3. Confirm a question about the OPP labelling categories (§6.5) either answers with a
   readable quote or refuses — and that its refusal is not caused by a mangled table. OPP
   PDF 11 is expected to be **excluded** (§3.4), so the expected outcome is a refusal that
   quotes the §6.5 *prose* (pdf 11, top of page) and names the table as not queried — never a
   sentence assembled across the table's cells.

## Pre-Flight Checklist

- [x] No models added — no migration, by requirement 5.
- [x] Views unchanged (`knowledge` has no user-facing views for this path).
- [x] Forms unchanged.
- [x] Service/module home: `knowledge/columns.py` (new, pure); `knowledge/ingest.py` (wire);
      `scripts/extract_fixtures.py` (pipeline).
- [x] URLs unchanged.
- [x] Tests: `knowledge/tests/test_columns.py` (new), `test_ingest.py`,
      `test_section_parsers.py`, `test_chunking.py` (regression only).
- [x] Migrations: none. Backwards-compatible by construction.
- [x] Queries: no new queries in a request path; ingest is a management command.
- [x] `transaction.atomic()`: unchanged — ingest already owns its transaction.
- [x] No template changes, no design tokens, no claim language added.

---

## 2026-10-19 Design — validated in session

**What was measured, not assumed.**

- A full-page band scan of all four PDFs: 32 of 139 pages are column-laid-out, and the
  per-document sets are in §3.1. The original proposal ("BPP and landscape; the appendices
  come free") was **wrong** — the appendices only partly come free, and the OPP has three
  table pages nobody had counted.
- The BPP sentence the chatbot could not cite **spans PDF pages 4→5**. It lives inside one
  stored chunk (chunk 331 already joins both pages), so the acceptance test must run on
  **post-ingest chunk text**, not on a single page. Verifying one page would have been a
  test that passes for the wrong reason.
- A throwaway prototype made both target sentences contiguous with the character multiset
  intact, and left every measured single-column control byte-identical.
- The first prototype **reordered the OPP §6.5 table** while preserving every character.
  That is why the golden-page rule exists and why the multiset test alone is not sufficient.

**Alternatives considered and rejected.**

1. *Relax quote matching (fuzzy/ordered-token).* Makes the symptom disappear by weakening
   the only check that makes a citation checkable; a reordered quote cannot be found on
   paper. The corpus is fixable; the rule should not bend around a data defect.
2. *Drop the BPP and the landscape from the corpus.* Cheapest, and it deletes exactly the
   guidance layer that answers "may I use this input?" — and still leaves the appendices.
3. *Ask the model for chunk ids + character offsets instead of quotes.* A contract change
   that removes the human's ability to verify and leaves the stored text scrambled.
4. *A per-document `layout` flag.* Measured to miss the OPP's three table pages, and it
   makes layout a code property of a document rather than a measured property of a page.

**Decisions taken with the product owner in this session.**

- Bucket **`ready/`** (not `BugFixes/`, which is terminal and would hide the item from
  "up next"); the PRD states plainly that it is a defect.
- Scope covers **all four documents**, with per-page coverage pinned by the golden table
  and per-page exclusions recorded rather than silently skipped.
- Fixture policy **accepted**: regenerated fixtures change bytes, the pipeline and raw page
  hashes go in `MANIFEST.json`, and no fixture is ever hand-edited.
- The success gate is the failure the product owner reported: the manure question, answered
  with a BPP and an Appendix 2 citation whose quotes a human can find on paper.

---

## 2026-10-19 Errata — re-measured before planning (folded in above)

Before the plan was written (`CORPUS_COLUMN_EXTRACTION_PLAN.md`), every measurement this PRD
depends on was re-run from `extract_pages()` on the shipped PDFs (probes in the git-ignored
`_scratch/`). Seven statements above were corrected in place. They are listed here so the
correction is visible rather than archaeology.

| # | Was | Measured | Now in |
|---|---|---|---|
| E1 | "312 pages must remain byte-identical" | 139 − 32 = **107** | §3.1, §6 |
| E2 | Golden table `range(76, 92) - {78, 80, 84}` (printed numbers) | Code sees **PDF** pages (`extract_pages()[n-1]`); SAOSO prints `pdf − 1`. Correct table: `set(range(77, 93)) - {79, 81, 85}` | §3.4 |
| E3 | "13 SAOSO column pages", total 32 detected | The detector also flags **SAOSO PDF 2** (the TOC): 33 detected, 32 in scope | §3.1, §3.4 |
| E4 | "A page that is column-laid-out but fails a golden check … stays byte-identical" | A pure `de_column` has no way to decline once a band is found — blocked until the TOC was measured | §3.3 (`PAGE_LAYOUT_EXCLUSIONS`), §9 (D46) |
| E5 | Requirement 2: "a page whose bands vanish is a no-op" | True for BPP p4 and OPP p11; **false for landscape PDF 4** (3 new bands, reorders further on a second pass) | §4 req 2 |
| E6 | Affected fixtures: `bpp_intro`, `landscape_seals`, `saoso_appendices`, `opp_4_1` | `saoso_appendices` (71–73) is **not** affected; **`saoso_toc`** is the one that would change, and now must not | §3.3, §5 step 4 |
| E7 | Success criterion: "the model's real 2026-10-19 reply … passes `audit_citations`" | That reply **paraphrased** the standard ("must preferably be composted and sourced from farms under organic management or extensive farming practices"), so an exact substring match refuses it against a perfect corpus. Unachievable as written | §5 step 7, §6 |

**Two new facts this session added, not corrections.**

1. **The landscape loses its page numbers after the transform.** `heading.py::_page_stamp`
   reads the last non-blank line; the bare page number is page furniture that reordering moves
   to roughly line 50 of 90. Fix verified: search for the last bare-number line anywhere. It
   restores landscape `[4, 4, 6, 7, 7, 9]` and leaves SAOSO/OPP/BPP output identical (BPP stays
   `[None, None, None, 10]`). This is requirement 10.
2. **SAOSO PDF 2 must be excluded, measured twice.** De-columning the TOC takes `parse_toc`
   from 29 entries to 8 and makes `appendix_spans` report Appendix 1 ending on p.80 instead of
   p.75 — and Appendix 2 is the page range the whole success gate depends on.

**Also confirmed, which E7 nearly obscured.** The defect itself is real and the fix works:
the two success-gate sentences are *not* contiguous in today's corpus and *are* contiguous
after the transform, in chunk text — BPP in one chunk with `anchor="general-principles"`, the
Appendix 2 condition in a chunk with `section_ref="Appendix 2"`, `page=76`. The recorded model
reply failed for **two independent reasons** (corrupted passage *and* paraphrase), which is
why a test written against it could never have passed and why the success gate is now stated
against the verbatim sentence.


---

## 2026-10-20 Build outcome

The work landed as planned; the measurement this PRD depends on held. What a reader should
know before judging the UAT:

- **33 detected, 29 transformed, 4 documented exclusions.** SAOSO PDF 2 (TOC, §3.4) and
  OPP PDF 11 (§6.5, expected) as designed, **plus SAOSO PDF 82–83** (Appendix 4 Table 1).
  The C4 reading-order review found Table 1's 4-column cells are one line each: every
  character survives de-columning, but the INS numbers, product names and `X` markers end
  up in separate blocks and no row can be located. The raw page is already row-coherent, so
  those two pages stay byte-identical with the reason recorded in `PAGE_LAYOUT_EXCLUSIONS`.
  Appendix 4 Table 2 (PDF 84) is accepted: it is a 2-column product/limitation list, the
  same shape as Appendix 2, and §3.5's row-association caveat applies.
- **Counts:** BPP 8, landscape 8, OPP 2 (pdf 4, 12), SAOSO 11 — 29 transformed; 4 excluded;
  106 single-column pages byte-identical, so 110 of 139 pages are unchanged by the pipeline.
- **Chunks after re-ingest:** SAOSO 293 (was 298), OPP 30, BPP 9, landscape 8 — 340 total.
  `_corpus_fingerprint()` invalidated the answer cache, as designed.
- **The success gate is met on stored bytes:** the BPP manure sentence and the Appendix 2
  condition are contiguous in one `DocumentChunk`, the verbatim sentence is accepted by
  `audit_citations`, and the recorded paraphrase is still refused.
- **UAT Scenario 9's live half is not yet met, for a reason outside this PRD's scope.** Two
  live turns on 2026-10-20 were refused by the audit because the model invented a `sub_ref`
  from a heading in one, and inserted an ellipsis into an otherwise verbatim quote in the
  other. The corpus was not the cause; the follow-up is filed in
  `product/backlog/todo.md`, and this PRD's non-goal "loosening the citation audit" still
  stands.

---

## 2026-10-21 Appendix 2 table rows — Design (supersedes §3.5 for this appendix)

**Status:** built and measured; UAT Scenario 2 (citation relevance) still needs a human.
**Trigger:** the chatbot refused *"can I use borax for boron supplements?"* and gave a
grounded but wrong answer to *"can I use straw mulch?"* — it said straw must be untreated,
which is the condition printed for **wood**.

### The finding

`pdftotext -layout` leaves Appendix 2's condition column vertically offset and splices it
into the substance column (`Trace elements … calcium Use restricted …`). `de_column` cannot
fix it: the rows overflow the gutter, so rule 2 keeps a spanning line whole by design.
`pdftotext -table` **aligns the rows correctly** — measured on SAOSO pdf 77–79. So the defect
is the extraction mode for a table page, not a missing pairing algorithm.

Diagnosis note: the stored chunks were first assumed stale. They are not — rebuilding all
340 chunks in memory found 0 differences. See `testing_hazards.md` §1.24.

### The change

- `knowledge/extraction.py` gains `mode="table"` (`pdftotext -table`). It is the *oracle*
  for the golden test, not the ingest path: the parsers were written against `-layout` and
  must not silently change rendering.
- `knowledge/tables.py` holds the reviewed rows for Appendix 2 (30 rows, printed pp. 76–78)
  and `TABLE_BANDS` (the measured right-column start per page).
- `knowledge/ingest.py` replaces Appendix 2's auto-chunks with one chunk per reviewed row.
  Everything else is untouched.
- `ingest_standard(..., force=True)` / `manage.py ingest_standard --force` replaces a
  document whose bytes are unchanged — the sha256 guard otherwise makes a corpus-built-here
  change unreachable. Deletion happens inside the transaction, **after** embedding.

### Assumptions (product decisions, not code-visible facts)

1. The pairing is the printed table's, reviewed by the product owner 2026-10-21. Where the
   text is ambiguous (`Free of significant contaminants` sits beside three unconditioned
   rows), the reviewed pairing wins; the code does not infer one.
2. A row is the unit of permission. A row with no condition is still an Appendix 2 entry;
   an empty condition is **not** permission ("silence is not permission" stays in the prompt).
3. Each cell is verbatim (whitespace-normalised) from the `-table` page. The **join** between
   the two cells is not on the paper; a quote may cover either cell or the whole row, and a
   reader checks it by finding the row. This is the single documented exception to
   `chunking.py`'s "a chunk is a slice of the section".
4. Cross-page continuations are merged by hand and recorded: seaweed's `iii) fermentation.`
   is printed at the top of the next page and belongs to it.
5. Centred sub-headings ("South African specific") and Roman-numeral group headings are page
   furniture, not rows, and cannot be quoted as a permission.
6. Only Appendix 2 is covered. Appendices 3, 4, 6a/6b and 7 keep the current pipeline and its
   documented limitations.
7. A changed standard is a changed table: a reprint is re-reviewed, and
   `knowledge/tests/test_tables.py` fails if a cell drifts from the 101-page extraction.
8. Hyphenation at a line break (`cobalt-` / `sulphate`) is one word in the reconstruction;
   the golden test applies the same rule to the page, and nowhere else.

### Round 3 evidence (live, after re-ingest; 321 SAOSO chunks, embedded)

| Question | Before | After |
|---|---|---|
| horse manure | grounded | grounded, row-level Appendix 2 citations |
| cardboard | grounded, governing clause only | grounded; cites the **biodegradable by-products** row and its contaminants condition |
| straw mulch | grounded, **mispaired with wood's condition** | grounded, correct — no condition on plant materials |
| borax | **audit refused** (interleaved chunk) | grounded; trace-elements row + deficiency restriction + S4.4.8 |
| cost incl. visit | grounded; no §2.1 membership fee | unchanged — §2.1 still not retrieved |
| ducks / bedding compost | audit refused | **unchanged** — S5.5.1 sub-clauses are separate chunks |
| seed grown organic | audit refused | **unchanged** — S4.1.1 paraphrase |

7 of 9 grounded. The two refusals are not appendix-table problems: `S5.5.1`'s sub-clauses
and `S4.1.1`'s enumeration need their own chunking decision. The cost answer still omits the
annual membership fee because §2.1 is not retrieved — a sibling-section retrieval question.

### Gate

`verify.sh` green at **619 tests**; `lint-imports` kept. `knowledge/tests/test_tables.py`
(72) is the golden guard; `test_ingest.py` proves the corpus gets the rows; the chatbot test
proves a row is one citable passage.
