# PRD: A canonical corpus — reviewed text as data, extraction as a build step

**Status:** In Progress — **SAOSO and BPP** are built, reviewed and are the text of record (`knowledge/corpus/saoso.md`, `bpp.md`); the OPP and landscape are not converted (P4, P5). **2026-10-28:** the ingest fails closed on a declared review (P7.1) and a deployment can tell whether its corpus is current (P2.1–P2.4).
**2026-10-22:** scope extended by §8 — the deployment gate proved the *runtime* still depends on the extractor (`testing_hazards.md` §2.9). Decisions **D55–D58** are recorded in `PGS_PLATFORM_SPEC.md` §18.3, and the work is scheduled in `CORPUS_CANONICAL_FORMAT_PLAN.md`.
**Owner:** Corpus ingestion (sub-plan B), grounded chat (sub-plan D)
**Last Updated:** 2026-10-28
**MVP:** MVP 0 — architecture change to how the corpus is produced. **No migration.**
**Scope:** Where the text of a governed document comes from, and how it is reviewed.
**Not** in scope: retrieval ranking (G3), the prompt contract, the escalation path.
**Reference:** `PGS_PLATFORM_SPEC.md` §18.3 D53; `knowledge/corpus.py`;
`knowledge/corpus/bpp.md`; `scripts/build_corpus.py`; `CORPUS_COLUMN_EXTRACTION_PRD.md`.

---

## 1. Problem

Four consecutive sessions spent on **extraction** rather than on the product:

| Decision | What it repaired |
|---|---|
| D46 | two-column pages: `knowledge/columns.py` |
| D51 | Appendix 2's table rows: `knowledge/tables.py` |
| D52 | hyphenated wraps and the printed page footer: `knowledge/reflow.py` |
| G7 | a spanning line on one BPP page — still open before this PRD |

Every one was a runtime defect: the extractor sat on the ingest path, so a layout
irregularity became a wrong or refused answer in the chatbot. The defect surface is
~1,100 lines in `knowledge/sections/` (three format parsers + a TOC map) plus ~750 lines
of layout heuristics, and it grows with each PDF quirk.

The corpus is four fixed documents. A human can read them once. What is missing is a
**reviewable artefact between the PDF and the database** — so extraction runs per
*edition*, not per ingest, and a layout defect is a line in a diff rather than a bug in
an answer.

## 2. Decision (D53)

**The text of record is a reviewed Markdown artefact per document.** The PDF stays the
source of truth and is still hashed; `scripts/build_corpus.py` drafts the artefact from
it; a human reviews the draft against the paper; `ingest_standard --from-corpus` reads
the reviewed file. Chunking, `sub_ref` offsets and embeddings stay **derived** — those
are tuned for retrieval and will keep changing.

Freezing at the **section** level, not the chunk level, is the design decision that makes
this safe: the artefact fixes what the document says and where it says it; it does not
freeze how the text is sliced for retrieval.

## 3. The format

Markdown with machine annotations, because the two audiences are a human with a red pen
and a parser with no opinions (`knowledge/corpus.py` is the contract):

```markdown
<!-- corpus
doc_key: bpp
source: pgs_docs/Basic Production Principles_ENG_PRINT.pdf
sha256: 2565e28b…
generator: knowledge corpusgen v2
raw_pages: 2,3,4,5,6,7,8,9,10,11,13
-->
<!-- page: 3 printed: none -->
## INTRODUCTION

The terms of reference for these principles …
```

- `<!-- page: N printed: M -->` — **PDF** page for provenance and the **printed** page for
  citations (D42). A block with no page marker is an error, because a quote nobody can
  find on paper is exactly what the audit exists to prevent.
- `##` depth builds `heading_path`; `<!-- ref: S20.1.1 -->` carries the citation, so the
  reader needs no per-document scheme.
- Everything else is text, verbatim, blank lines included — they are the chunker's
  paragraph boundaries.
- **Reviewed corrections are not annotations.** They are data in
  `knowledge.corpus.CORPUS_EDITS`, so a test can prove the correction was necessary (its
  `original` is in the PDF-derived text) and applied (its `replacement` is in the file).

## 3a. OCR: where it would sit, and why it has no job in this corpus (measured 2026-10-29)

Asked directly, so answered with a measurement rather than a position. **Every page of all four
governed documents carries a text layer**, so there is nothing to OCR:

| Document | Pages | Characters per page (median) | Pages with no text |
|---|---|---|---|
| SAOSO v2.1 | 101 | 2 063 | 1 (the last, blank) |
| Outeniqua OPP | 15 | 1 441 | 1 |
| Basic Production Principles | 13 | 1 629 | 1 |
| Certification landscape | 10 | 1 721 | 1 |

`tesseract` is not installed and should not be. When a document *does* arrive as a scan, OCR's place is
as a **third drafting input to the artefact build**, beside `pdftotext` and the fixture generator —
never at runtime, and never as text of record:

```
PDF ->  pdftotext -layout       (the normal case: a text layer exists)
    ->  OCR                     (only for pages where the text layer is empty or short)
    ->  vision model, cells     (only for tables and figures, drafted and then reviewed, D70.2)
                              \\-> one reviewed artefact -> chunks -> lexical index + vectors
```

Two rules make that safe, and the second is the one that matters:

1. **All three are drafts.** The artefact is the text of record and a human reviews the diff
   (unchanged from D53); an OCR line is exactly as reviewable as a `pdftotext` line.
2. **OCR is the wrong tool for a table.** It reproduces precisely the defect this repo has spent four
decisions fixing: a text stream with no cell structure, from which row association cannot be
recovered (see `TABLES_AS_DATA_PRD.md` §3a's measurements). For a scanned table, a vision model that
returns *cells* is the drafting tool (D70.2), and a human still reviews it. And for a page whose
meaning is a picture — the landscape's two seal artworks — OCR would read `PGS ORGANIC` and lose the
thing that was there.

**Worth adding regardless of OCR:** a per-page text-layer coverage check in the artefact build, so a
scanned standard fails loudly with a page number instead of ingesting as an empty or half-empty
document. Today the ingest refuses **zero** sections; a document that is 40% scans would pass.

---

## 4. The spike: BPP, 13 pages

### 4.1 Result

| | Before | After |
|---|---|---|
| Chunks | 9 (PDF path) | 9 (artefact) |
| Reviewed corrections | — | **5** |
| G7 (synthetic fertilisers) | unquotable | **grounded live**, 4 citations |
| Manure sentence | quotable | **still quotable** (checked live) |
| `verify.sh` | 652 | **705** |

### 4.2 The three generator improvements the review produced

Each was found by reading the artefact, and each is now code rather than a hand edit:

1. **Bands narrowed to the untouched run** (`columns.py`). The detected gutter started
   *inside* the left column because long lines overflow into it, so `de_column` kept
   those lines whole. Narrowing each band to the columns no line writes into cut the
   corpus's uncuttable lines from **66 to 13**, losslessly, on 6 BPP pages — and removed
   G7's cause entirely. SAOSO and OPP are unchanged by construction (their bands already
   had an untouched core), so no table page moved.
2. **Per-page `-raw` fallback** (`build_corpus.py`). `-raw` keeps the producer's order,
   which is correct where geometry fails, but it glues words (`Sourcedlocallyfrom…`).
   Measured: every page of all four documents is a **character-for-character permutation**
   of `-layout` (139/139 pages), and the glue is repairable by splitting each glued token
   into the run of `-layout` words that concatenates to it. A page is drafted from `-raw`
   only when, after that repair, its word multiset is identical. 11 of BPP's 13 pages
   qualify, including 3, 6 and 9 — the pages the band detector cannot handle at all.
3. **The printed page comes from the de-columned page** (`page_stamp`, now shared with
   `HeadingParser`). The two renderings disagree where the stamp shares a line with body
   text: `-raw` puts `02` alone, `-layout` glues it to the footnote. Reading it from the
   de-columned page is what D42 was measured on, and it is what keeps the CONCLUSION's
   `page=10` and the INTRODUCTION's `page=None`.

### 4.3 The five corrections a human still makes

| Page | Correction | Why not a generator rule |
|---|---|---|
| 3 | drop the bare page stamp `02` | **now a generator rule** — kept as an edit only for the coverage accounting |
| 4 | footnote 2 moved out of the manure sentence | footnote placement is a reading judgement; the generator cannot know it interrupts a sentence that continues on the next page |
| 8 | `Preventativemethods(` → `Preventative methods (` | the PDF's own text layer has no spaces; no extractor can recover them |
| 8, 10 | the four-principle strip dropped (kept on page 6) | the strip repeats on 1, 6, 8 and 10; which occurrence carries the content is a judgement. A blanket "drop repeated lines" rule would delete SAOSO's repeated *"Regional or other exception"*, which is content |

### 4.4 The guards (31 tests in `test_corpus_bpp.py`, 2 in `test_chatbot_grounding.py`)

1. **Same document:** header sha256 is the PDF's; character multiset equals the PDF path's
   sections *minus the declared edits* — no silent loss, no invention.
2. **Same identity:** every `(section_ref, anchor, page, heading_path)` matches the PDF
   path exactly. Text may differ where reviewed; identity may not, because that is what a
   citation resolves through.
3. **Traceable:** every block is a contiguous slice of the pages from its marked page
   (allowing one page break for a paragraph, and declared re-spacing). Untraceable blocks:
   **0**.
4. **The page is the only one it could be:** a block that fits entirely on exactly one
   page must name that page. Added because the 3-page span allowance made a *deleted page
   marker* invisible — found by mutating the artefact, not by review.
5. **Edits are evidence:** necessary (the `original` is on the page) and applied (the
   `replacement` is in the file; a dropped original is gone from *that page*).
6. **Contiguous where it matters:** the manure sentence, the raw-manure rule, the
   agro-chemical prohibition and the re-spaced item are asserted contiguous.

Plus `test_ingest.py`: the artefact and the PDF produce the same section identity and the
same chunk count; an artefact built from another PDF, or for another document, is refused.

### 4.5 Ten reviewed examples, quotable from exactly one chunk and audited

Ten substantive BPP requirements, each of which a farmer would actually ask about, are
asserted twice: in `knowledge` that the sentence survives **chunking** in exactly one
chunk, and in `core` that the **citation audit** accepts a quote of it against the rows
the artefact produced (`REVIEWED_QUOTES` in `test_corpus_bpp.py` is the single source).

| # | Example | Chunks carrying it | Audit |
|---|---|---|---|
| 1 | synthetic fertilisers (agro-chemicals) prohibited | 1 | accepted |
| 2 | GM seeds/seedlings expressly forbidden | 1 | accepted |
| 3 | purchase organic seed from a verifiable source | 1 | accepted |
| 4 | conventional seed allowed with PGS approval | 1 | accepted |
| 5 | landless animal husbandry prohibited | 1 | accepted |
| 6 | unrestricted daily access to pasture | 1 | accepted |
| 7 | laying hens: 8 continuous hours without artificial light | 1 | accepted |
| 8 | breeding stock: 10% yearly maximum | 1 | accepted |
| 9 | only approved cleaning/disinfecting agents | 1 | accepted |
| 10 | more than 50% of feed from the farm unit | 1 | accepted |

A paraphrase of #6 is asserted **refused**, so the corpus does not soften the audit. The
guards were proved by mutation: breaking one sentence in the artefact fails the specific
example, the coverage check, the traceability check and the end-to-end audit.

**Two lessons from generating the list.** The twelfth candidate — *"Employment practices
should be in accordance with the South African Labour legislation…"* — was quoted from
memory and does not exist: the BPP prints **"Employment practice should be"**, singular.
Every example is therefore copied from the artefact, not recollected, which is the same
rule the fixtures follow. And every example is *shadowed* by SAOSO — live probes for the
hen-rest and feed-from-farm questions both cited `S5.1.9` and `S5.5.3` rather than the
BPP — which is the prompt's "prefer the governing document" rule working as designed. The
BPP is what answers when the standard is silent or when the question uses the BPP's own
wording (the agro-chemicals probe cited `general-principles`).

## 5. Kill criteria (recorded, not assumed)

- **Edit count.** `MAX_EDITS = 5` for BPP. The ratchet may only go down without a reason.
- **Traceability.** Any untraceable block fails the build. If a document needs edits in
  more than ~10% of its blocks, the artefact is not cheaper than the extractor — stop.
- **Identity drift.** A changed anchor, page or ref between the two paths fails the build,
  so the two can never silently diverge.

## 6. Rollout

| Step | Document | Pages | What it exercises |
|---|---|---|---|
| ✅ done | BPP | 13 | prose, footnotes, a graphic strip, a glued word, both renderings |
| next | OPP | 15 | `sub_ref` offsets, `§V` seals, a 3-column table (pdf 11) |
| next | landscape | 10 | heading-only, bare page stamps, a 6-element diagram |
| last | SAOSO | 101 | appendices 1–7: this is where `tables.py` (G4) is absorbed |

`--from-pdf` stays available and stays tested throughout; the equivalence test is what
makes the migration reversible. A new standard edition means regenerate → **diff the
artefact** → review only what changed, which is a better story than the current re-ingest.

## 7. Open questions / follow-ups

**All six were answered on 2026-10-22 while scoping the deployment failure — see §8 and `PGS_PLATFORM_SPEC.md`
§18.3 D55–D58. The answers, in order:**

1. **Idempotency.** A `corpus_digest` column on `StandardDocument` plus a read-only `corpus_check`; deploys *report*
   drift and never refresh (D56). No silent `--force` in `deploy.sh`.
2. **`CORPUS_DOCUMENTS` beside the models.** Still to do, folded into the plan (P7): move the descriptors into a
   Django-free module so the generator needs no settings.
3. **Artefact carries sections, not chunk_sections.** Confirmed, unchanged: chunking stays code.
4. **Regenerating overwrites the review.** Fixed by making edits replayable (plan P3): the generator applies
   `CORPUS_EDITS` itself, so `draft + declared edits = reviewed artefact`, proven by a test. The git-ignored
   `_scratch/apply_bpp_edits.py` must not be part of the record.
5. **The edit table is not self-cleaning.** A test asserts each edit's `replacement` still differs from its
   `original`; when the generator learns a correction, the entry must be deleted by hand and the test fails until it is.
6. **SAOSO review at 101 pages.** Diff-based, with mechanical acceptance first and human review of the flagged delta
   (D58).

---

## 8. Taking the reader out of the runtime (2026-10-22)

**Trigger.** The first real run of `deploy/deploy.sh` on the VPS failed its gate: *15 failed, 718 passed, 61 errors*.
Every failure was extraction — poppler 24.02 versus the Xpdf 4.00 the goldens were measured on. `-table` does not
exist in poppler at all (exit 99), poppler detects a different set of column-laid-out pages, and it rejoins a
different number of hyphen wraps. Nothing was deployed, and that is the gate working. But it proved D53 was only
**half** done: the artefact existed, and the runtime still had a reader on the path.

### 8.1 What "out of the runtime" means — three requirements

| # | Requirement | Decision |
|---|---|---|
| 1 | **Ingest cannot fall back to the PDF** for a governed document. A missing artefact is an error naming the generator, not a silent extract. | D55 |
| 2 | **The gate needs no reader.** The parsers' goldens read committed page fixtures; `verify.sh` runs pytest with `PDFTOTEXT_BIN` pointed at a path that cannot exist, so extractor-independence is proved on every run, on every machine. | D57 |
| 3 | **A deployment can tell whether its corpus is the committed one.** `corpus_digest` stored, `corpus_check` reports drift, `corpus_refresh --apply` is deliberate. | D56 |

### 8.2 What stays dependent, deliberately

- `scripts/build_corpus.py` and `scripts/extract_fixtures.py` still run `pdftotext`. They are **build-time** tools:
  they run on the machine that produces artefacts, and their output is reviewed and committed. The artefact header
  and `MANIFEST.json` record the extractor banner, so a regeneration under a different build is attributable.
- `--from-pdf` stays available and tested: it is the equivalence oracle that makes the migration reversible
  (section 4.4, guards 1 and 2) and the only way to ingest a document whose artefact does not exist yet.
- `-table` remains Xpdf-4-only. That is now a constraint on the *artefact build*, not on the deployment.

### 8.3 Acceptance for this scope extension

1. ✅ **Met 2026-10-22 (plan P1).** `./scripts/verify.sh` is green at 800 tests with `PDFTOTEXT_BIN`
   pointed at a path that cannot exist, and an inherited value is discarded by the gate itself.
2. On a box with no `pdftotext` at all: `deploy.sh` passes its gate, and `corpus_refresh --apply` rebuilds the corpus
   from the committed artefacts.
3. `corpus_check` on a stale deployment exits non-zero and names the documents whose digest differs.
4. ✅ **Met 2026-10-22 (plan P1).** The same bytes, read from nine committed page fixtures; no assertion
   changed. `scripts/check_extraction.py` is the build-time diff that replaces what the gate gave up.
   A re-extraction diff script reports when a new extractor build would change them, and is run only by the person
   building artefacts.

### 8.4 The rollout this adds

The document order in section 6 is unchanged (OPP, landscape, SAOSO). Two tasks move **ahead** of it, because they
are what makes a deployment possible at all: the gate fixtures (plan P1) and drift reporting (P2). The per-document
conversion follows, and the last task is the VPS refresh from artefacts — which is the proof that the box needs no
reader.

---

### 8.5 Chat telemetry and retention (D59)

The record the assistant already keeps is the input to this PRD's later tasks: every turn
stores the question, the answer **or the refusal**, the model, latency, token counts, and the
`retrieved_chunks` the model was given; every refusal also writes an `EscalatedQuery` with a
reason (`INSUFFICIENT_CONTEXT`, `NO_CITATIONS`, `CITATION_AUDIT`, `USER_REQUESTED`). A refused
question is therefore a corpus gap with its retrieval evidence attached.

Two things were missing for that record to be usable, and neither is a change to what the
product does. Both are plan tasks, not this PRD's decision:

- **Attribution** (P2.5): a stored answer does not say which `PROMPT_VERSION` or corpus
  produced it, so after a re-ingest old and new rows are indistinguishable.
- **A review loop** (P2.6/P2.7): only refusals have a queue. A grounded-looking wrong answer
  has nowhere to go, and there is no bulk way to read the record.

**Retention is D59: keep every transcript until the group sets a schedule.** Recorded rather
than assumed, because this is a public form and the question text can contain personal data
about a third party; the decision to keep is a POPIA decision, not an absence of one. No purge
is built, and the eventual purge must be explicit about `EscalatedQuery`, which survives
message deletion on purpose.

---

## Pre-Flight Checklist

- [x] Models changed? **No** — no migration.
- [x] Services in the correct module? `knowledge/corpus.py` (pure), `knowledge/ingest.py`,
      `scripts/build_corpus.py` (developer tool).
- [x] Views touched? **No.**
- [x] Tests added? `knowledge/tests/test_corpus_format.py`, `test_corpus_bpp.py`,
      `test_ingest.py` (6 new), `test_columns.py`/`test_reflow.py` counts re-measured.
- [x] `knowledge` still never imports `core`; `lint-imports` kept.
- [x] No logic in templates. No new runtime dependency.
