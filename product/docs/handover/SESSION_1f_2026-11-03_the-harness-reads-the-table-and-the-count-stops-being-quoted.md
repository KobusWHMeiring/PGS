# Session `1f` — 2026-11-03 — the harness reads the table, and the count stops being quoted

**Where this session started.** `HANDOVER.md` said "19 commits unpushed" while
`git rev-list --count origin/main..HEAD` printed **28**; the same file says "count it, do not quote
it". So the first act was the loop, not the feature: push, correct the number to a form that cannot
go stale, and leave the deploy in the operator's hands (the dev box has no SSH key).

**What it built.** D80's **S4** — the verification harness — out of the PRD's requirements 2–7, the
one slice that needs no extractor and no new dependency, chosen over the PRD's own next slice (S2)
because S2 is a measurement that needs Docling installed (torch, layout models) and GCP credentials
the dev `.env` does not hold.

## 1. The loop closed first

- **Pushed**: `ae09891..9adee7a`, 28 commits that had been sitting on one laptop since `06bb11a`.
- **The stale number fixed at its cause.** Both places now say "`git rev-list --count
  origin/main..HEAD` must print `0`" instead of a count. The file already carried the instruction
  ("count it, do not quote it") and still carried a quoted number — twice wrong (19 vs 28), which is
  the argument for the command and against the number.
- **The deploy is named as owed, not done.** Live is at `06bb11a`; the operator's one command is in
  the handover with what to read back. Nothing about it was narrated as done.

## 2. S4, and the three things that were wrong with the obvious version

`knowledge/table_harness.py` (+ `scripts/check_tables.py`, `knowledge/tests/test_table_harness.py`,
`tests/tools/test_check_tables.py`) implements `R2` header association, `R3` cell fidelity, `R4` row
count, `R5` empty-is-data, `R6` spans-whole and `R7` non-text-is-never-quoted, returning named
violations. **27 tests; the four reviewed tables (14 rows) pass; one mutation per requirement is
named; two guards were broken and watched red** before being trusted.

The design was not obvious, and each of the three corrections came from a measurement, not a
preference:

1. **A cursor shared across a row's cells is wrong.** It reported **171** violations across the
   landscape's three tables, and every one was the *fee box's position*: the paper prints one fee box
   spanning Steps 1 and 2 and files it under Step 1, so its text sits above the row it belongs to.
   Per-cell cursors only.
2. **"A contiguous run inside one printed line" is not the rule the paper allows.** The strict
   reading reported 3 landscape cells, all of them **wraps** (`self-` / `assessment`), none a lost or
   reordered word. The rule now matches inside one printed line, and failing that splits the cell's
   line at its own hyphen and requires **both halves to be printed lines, in order**. The alternative
   — joining every line — would have made R3 mean "the words appear somewhere on the page".
3. **The extraction mode is information, not a default.** The landscape's cells came from
   `pdftotext -table`; against `-layout` pages the same cells report 10 violations. The mode is now
   an explicit declaration (`--pages-mode`) and the corpus test pins it *and* proves the check is not
   vacuous by running the wrong mode and watching it fail.

**What it refuses to guess**, because a guess is how a gate stops being one: **the row count**
(a page cannot state it in machine-readable form, so `--rows`/`expected_rows` is a declaration and an
undeclared count is a *violation*, not a pass), and **how many tables the document has**
(`expected_tables`, so a block that went missing fails instead of passing with nothing to check —
the other half of S1's generator guard).

## 3. Verified, not assumed

- `scripts/verify.sh` → **1671 passed / 1 skipped / 8 xfailed in 68.61 s**, `every budget holds` on
  step 1/4. Same tree, cold, in `1e`: 219.16 s. Both quoted (`testing_hazards.md` §3.17).
- `scripts/fast.sh` → 1656 passed / 15 deselected / 8 xfailed in 46.66 s; `--critical` → 172 passed /
  4 deselected in 10.64 s.
- `scripts/check_tables.py` on the corpus: `landscape: ok — 3 tables, 8 rows, 0 violations (table
  pages)`, `opp: ok — 1 tables, 6 rows, 0 violations (layout pages)`; without `--rows`, exit 2 and no
  pass printed.
- The guard proofs were run, not claimed: `NOT_TEXT` neutered → the two R7 tests red; the R5 slice
  check neutered → `test_a_fabricated_cell_is_named` red; both restored, green again.

## 4. What the harness still cannot see

A table that is not a `<!-- table … -->` block is invisible to it. That is exactly Appendix 6a's 20
rows and Appendix 7's 4 interleaved chunks — the two live defects the PRD measured — so **S5 is
unchanged as work**, and the success criterion for "every table in the corpus" is recorded as
**partly** met (4 tables, 14 rows) rather than ticked. The harness asserts *requirements*, not
*shapes*: the eight `read_table()` targets still wait for S2, and `UNCOVERED` in S0's registry was
left alone deliberately.

## 5. What is next

**S2**, with its two frictions now known in advance: `docling` is not installed (torch + layout
models) and Document AI needs GCP credentials. If neither can be adopted, S3 does not follow, and the
PRD's own falsifier applies — S5's rows stay unasserted and that is written down, not absorbed.

**S4's own remaining debt, named here so it is not forgotten:** the **extraction mode per document**
is the last bespoke datum in the path (a flag today). S3 must record it on the artefact, or the gate
for a *new* document is a flag somebody has to remember.

## 6. Later in the same session: the owner asked what S2 even is, and decided it

The question was two questions: *what is Document AI, what are GCP credentials* — and then, when the
page was written, *why Document AI instead of a vision model, and what does the industry do now?*

- **The explainer** is `product/design/d80_s2_extractor_evaluation.html` (self-contained, no external
  request, exports a §18.3 row; mobile and desktop both checked for horizontal scroll in a real
  browser, and the JS parse-checked). Its verified facts come from this machine, not from a blog:
  `python 3.13.3`, `docling` and `torch` absent, `.env` holding only `DJANGO_SECRET_KEY`.
- **The decision is D81 (owner, 2026-11-03): A — Docling first**, graded by S0's expectations and S4's
  checker, with Document AI gated on a threshold (three or more of the eight shapes losing spans,
  qualifiers or header association) rather than on mood.
- **The answer to "why not a vision model", recorded as Addendum A**, is a distinction worth keeping:
  Document AI is **extractive** vision — text with geometry — while a vision *language* model
  **writes** the text it believes it read, so a wrong digit is indistinguishable from a right one.
  What D80 rejected was **X4, answering from page images**, which breaks R9/D70.2's claim that a quote
  is characters we verified. A generative VLM used as a *drafting* extractor is not rejected by
  principle — it is admitted by the harness, because R3 refuses any cell that is not a contiguous run
  of the page, and the cell text must come from an extraction pass, not from the model's prose.
- **The field, marked as inferred rather than verified:** extractive parser plus a human diff review
  (ours), VLM-for-structure with OCR-for-text (the hybrid that our R3 string-match already implements),
  end-to-end VLM for scans and handwriting (solving a problem our PDFs do not have — they carry text),
  and region citation as the industry's own output shape (which is our X3, so adopting an extractor
  later is cheaper than it looks).

## 7. Session `1g` — Docling, measured, and it does not pass

The owner said "let's walk the Docling route", so S2 was run rather than argued.

**Setup, and what it cost.** Docling 2.146.0 into a throwaway venv (`_scratch/docling/venv`, not a
project dependency): **1.5 GB** installed, plus model weights. Its defaults were checked rather than
assumed — `TableFormerMode.ACCURATE`, `do_cell_matching=True`, `do_ocr=True` — so this is its
high-quality path, not a fast one. Python 3.13.3, CPU only.

**The instrument is `scripts/eval_extractors.py`**: convert only the pages a shape is printed on
(`page_range`), pick the table that best overlaps the shape's anchors (the choice is printed, so it can
be audited), map the extractor's table onto `TableRead`, and score with S0's own `mismatches()` — twice:
*as extracted*, and *once row 0 is taken as the header*. The second reading exists because Docling
**marks no cell as a column header on any page we gave it**, and a tool that needs a convention is a
different finding from a tool that cannot pass.

**The result (PRD §3.5, `product/docs/evidence/2026-11-03_s2_docling_scores.json`):**

| | |
|---|---|
| as extracted | **0 of 8** |
| with row 0 as the header | **1 of 8** (the OPP's fee table, whose grid is exact) |
| tables not detected | **2 of 8** — landscape p5 and p6 come back as 2 pictures and headings |
| rows and columns usually found | yes — 6a returns 20 of 20 rows and 2 of 2 columns |

So it is not a tool that cannot see. It is a tool whose structure loses exactly what requirements 2, 4
and 6 name: header association (8/8), spans (6a's two header labels merged into one cell; p4's five
columns split into six), dividers (App 2's two divider labels became rows), page-break rows (p5's
continuation is a second table and was not returned), and non-text (two undetected tables).

**Three bugs were mine, and each is now measured rather than remembered:** the `*_offset_idx` fields are
half-open (a cell printed `r0-1` is row 0) and the first mapping indexed one past the grid; `TableRead.pages`
is the *printed* page, so SAOSO pdf 86 is 85 and the mapping must be read from the case, not inferred; and
building a `DocumentConverter` per shape put the model load inside every timing, so one converter is
shared now.

**What it triggers.** D81's threshold — "Document AI only if Docling loses spans, qualifiers or header
association on three or more of the eight" — has fired on all three. **The next step needs the owner**: a
Google Cloud project with billing, the API enabled, a processor, and a service-account key. That is where
S2 stops, and the handover says so instead of leaving a plan that cannot run.

**Speed, quoted as a range because it was measured twice** on the same box with the same verdicts:
**163 s** total on a quiet run, **330 s** on a busy one. 7–14 s per SAOSO page, 19–58 s per landscape
page. A laptop under load is not a benchmark, and one number would have been fiction.

## 8. Then the owner asked whether a Gemini key is a GCP key, and what else could be measured

Two answers, both verified rather than asserted, and both now in PRD §3.6:

- **A Gemini API key is not a GCP credential.** One key, two doors, measured in the same minute:
  `200` on `generativelanguage.googleapis.com/v1beta/models` and `401` on
  `documentai.googleapis.com/.../processors`, with Google's own words — *"API keys are not supported by
  this API. Expected OAuth2 access token or other authentication credentials that assert a principal."*
  A key is a bearer token for one API; a Cloud API wants a principal with IAM roles.
- **The repo's credential state is subtler than the handover said.** `.env` holds
  `DJANGO_SECRET_KEY` only — true, and what Django scripts see — while the *session shell* holds
  `GEMINI_API_KEY` and `OPENROUTER_API_KEY`. "We have no credentials" and "Django has no `.env` keys" are
  different sentences, and the first one was wrong.
- **OpenRouter's public catalogue today: 455 models, 310 accepting image input, 188 accepting a
  PDF/file.** So a VLM arm needs no new account at all — which moves the next experiment away from
  Google Cloud and onto an instrument that already exists.

**Deliberately stopped there.** The multi-arm evaluation is a new investigation with its own prompt
design, schema validation and retries — not a tail on this session. The brief is PRD §3.6, the ruler is
`scripts/eval_extractors.py` + S0's `mismatches()`, and the gate to clear is R3: a cell that is not a
contiguous run of the page is a violation, whoever proposed it.
