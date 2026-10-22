# Corpus Canonical Format — Implementation Plan

**Status:** In Progress — P0 (decisions D55–D58) settled; P1 (the gate) is the current task
**Owner:** Corpus ingestion (sub-plan B), grounded chat (sub-plan D), deployment
**Last Updated:** 2026-10-22
**PRD:** `CORPUS_CANONICAL_FORMAT_PRD.md` (D53, extended by section 8)
**Decisions:** `PGS_PLATFORM_SPEC.md` section 18.3 **D55–D58**
**Reference:** `knowledge/corpus.py`; `knowledge/corpus/bpp.md`; `scripts/build_corpus.py`;
`knowledge/extraction.py`; `product/docs/context/testing_hazards.md` section 2.9

---

## 0. How to execute this plan

Work one task at a time. Every task ends with the gate green **and** with the specific proof
it names. Nothing here is a migration except **P2.1**, which is additive.

### 0.1 Baseline re-measured for this plan (2026-10-22, this machine)

| Fact | Value |
|---|---|
| `verify.sh` | **798 tests**, `lint-imports` kept |
| Pages per document | SAOSO **101**, OPP **15**, BPP **13**, landscape **10** — 139 total |
| `pdftotext -layout` text | SAOSO 294,706 chars, OPP 33,708, BPP 26,530, landscape 31,102 (~386 KB, ~772 KB with `-raw`) |
| Tests in the six extractor-dependent modules | **265** (`test_columns`, `test_reflow`, `test_section_parsers`, `test_corpus_bpp`, `test_tables`, `test_ingest`) |
| Extractor on this box | **Xpdf 4.00** (`/mingw64/bin/pdftotext`) — the build the goldens were measured on |
| Extractor on the VPS | poppler 24.02 — the deployment target |
| Artefacts converted | **BPP only** (`knowledge/corpus/bpp.md`, 5 reviewed edits) |

### 0.2 PRD errata — correct these; do not build around them

1. The PRD numbers two different items **"5."** in section 7. They are renumbered in the plan as
   P3 (replayable edits) and P3.2 (the edit table is not self-cleaning).
2. The PRD's section 6 table says SAOSO is **101** pages, not 92 (measured above). The 92 in
   `kg`-era notes was the PDF page count minus the cover and TOC; `extract_pages` returns 101.
3. `CORPUS_COLUMN_EXTRACTION_PRD.md` section 3.5 still says table rows are not reconstructed.
   True only for the appendices not yet reviewed; Appendix 2 has been reviewed rows since D51.
   Update it in P6.
4. The plan's P1 changes what "green" means for six test modules that are currently listed in
   the PRD's section 4.4 as PDF-derived. Their assertions do not change; their **input** becomes
   a committed file. Record that in the PRD after P1.

### 0.3 Decisions frozen for this plan

| # | Decision | Consequence for the plan |
|---|---|---|
| **D55** | Ingest reads the artefact; a missing artefact for a governed document is an **error**, not a PDF fallback. `--from-pdf` stays as the diagnostic and equivalence oracle. | P7.1 is a behaviour change with a red test first |
| **D56** | `StandardDocument.corpus_digest` + read-only `corpus_check`; deploys report drift, never refresh. | P2 is one additive migration and one management command |
| **D57** | The gate reads committed page fixtures and runs with a **poisoned** `PDFTOTEXT_BIN`; the extractor is build-time only and is recorded in the manifest and artefact header. | P1 is the unblocking task; nothing else can deploy until it lands |
| **D58** | SAOSO review = mechanical acceptance + human review of the flagged delta; appendices convert in this slice (absorbs G4). | P6 is the long pole and is review-bound, not code-bound |

### 0.4 Files touched (by task)

| Task | New | Changed |
|---|---|---|
| P1 | `knowledge/tests/page_fixtures.py`; `knowledge/tests/fixtures/pages/*.txt` | `scripts/extract_fixtures.py`, `scripts/verify.sh`, `knowledge/tests/{test_columns,test_reflow,test_section_parsers,test_corpus_bpp,test_tables,test_ingest}.py`, `knowledge/tests/fixtures/MANIFEST.json` |
| P2 | `knowledge/management/commands/corpus_check.py`, `corpus_refresh.py`; `knowledge/migrations/0003_*.py` | `knowledge/models.py`, `knowledge/ingest.py`, `deploy/deploy.sh` |
| P3 | — | `knowledge/corpus.py`, `scripts/build_corpus.py`, `knowledge/tests/test_corpus_format.py` |
| P4–P6 | `knowledge/corpus/{opp,landscape,saoso}.md`; tests per document | `knowledge/corpus.py` (`CORPUS_EDITS`), `knowledge/tables.py` (P6 only) |
| P7 | — | `knowledge/management/commands/ingest_standard.py`, `knowledge/ingest.py`, `deploy/deploy.sh`, `HANDOVER.md` |

---

## 1. The shape

Today, two paths exist and only one of them is reviewed:

```
PDF ──pdftotext -layout──► de_column ──► reflow ──► parser ──► chunks ──► DB
  └───────────────────────── runtime, extractor-dependent, 4 sessions of defects

PDF ──build_corpus──► draft ──human review──► knowledge/corpus/<doc>.md ──► ingest_standard
  └── build-time, once per edition                          └── runtime, reviewable data
```

The plan moves the second arrow to be the **only** runtime path for the four governed
documents, and takes the extractor off the **gate** as well:

```
gate:      committed page fixtures ──► transform + parser tests      (no binary at all)
build:     PDF ──pdftotext (pinned)──► draft ──review──► artefact ──► committed
runtime:   artefact ──► ingest_standard ──► chunks ──► DB             (no binary at all)
```

The gate's copy of the pages is *evidence*, not a second source of truth: it is the same
`pdftotext -layout` output the goldens were measured on, committed once, with its extractor
banner and sha256 in `MANIFEST.json`. A new extractor build is compared by a **script**, run by
the person building artefacts — never silently by the gate.

---

## 2. Tasks

### P1 — The gate stops extracting (unblocks the deployment)

**Why first.** Nothing can deploy until the gate runs on the target, and the target has poppler.
This task also makes the failure impossible to repeat: the gate proves on every run that no test
needs a reader.

**P1.1 — Page fixtures, generated and attributed.**
`scripts/extract_fixtures.py` gains a second output: `knowledge/tests/fixtures/pages/<doc>.layout.txt`
and `<doc>.raw.txt` for all four documents, plus `<doc>.table.txt` for SAOSO. Pages are joined by
`\f` exactly as `extract_pages` returns them. `MANIFEST.json` records, per file: mode, page count,
sha256, and the extractor banner (`pdftotext version 4.00`, Glyph & Cog). The script **refuses to
overwrite** a page fixture when the banner differs from the recorded one unless `--force`, naming
both banners — the same rule `build_corpus.py` already uses for reviewed artefacts.

*Fails if:* a page file is written without its manifest entry, or the banner check is absent.

**P1.2 — One reader, provenance-checked.**
`knowledge/tests/page_fixtures.py` exposes `pages(doc_key, mode="layout")` and asserts the shipped
PDF's sha256 equals the one recorded in `MANIFEST.json` before returning anything. A swapped or
re-generated PDF fails loudly instead of silently testing different bytes.

**P1.3 — Re-point the six modules.**
`test_columns`, `test_reflow`, `test_section_parsers`, `test_corpus_bpp`, `test_tables` read
`pages(...)`. `test_ingest`'s two extractor-dependent tests (`test_the_ingest_reports_the_pages_it_transformed`,
`test_the_artefact_and_the_pdf_produce_the_same_document`) get the committed pages by
monkeypatching `knowledge.ingest.extract_pages` — **no production API change for tests**. Golden
values do not move: same bytes, read from a file.

**P1.4 — The gate poisons the extractor.**
`scripts/verify.sh` runs pytest with `PDFTOTEXT_BIN="$REPO_ROOT/_no_extractor"` — a path that
cannot exist — and ignores any inherited value. The deploy therefore cannot pass by *having* an
extractor; it passes by not needing one. An error message from a test that tried to extract names
the variable and the reason.

*Proof (the headline acceptance):* `./scripts/verify.sh` green, and
`PDFTOTEXT_BIN=/usr/bin/true ./scripts/verify.sh` also green. Before this task, the second command
fails 61 tests; after it, it cannot matter.

**P1.5 — A new build check replaces what the gate gave up.**
`scripts/check_extraction.py` (new, not in the gate): re-extracts each PDF with the configured
binary and diffs against the committed page fixtures, printing the first differing page and line
per document. Run by the person building artefacts, and after any `pdftotext` upgrade. Exit
non-zero on drift. This is the honest replacement for "the gate would have caught it": the gate
cannot, because the gate must run where no reader exists.

**Gate:** 798 + new tests; `PDFTOTEXT_BIN=/usr/bin/true ./scripts/verify.sh` green; the golden
page/wrap/table assertions unchanged in value.

---

### P2 — The deployment can tell whether its corpus is current

**P2.1 — `corpus_digest`.** Additive field on `StandardDocument`: sha256 of the artefact text (empty
for a PDF-path ingest). Migration `knowledge/0003`. `ingest_standard` writes it; `IngestReport`
already carries it.

*Fails if:* a digest is stored for a PDF-path ingest, or an artefact ingest leaves it empty.

**P2.2 — `corpus_check`.** Read-only. For each governed document: is the artefact on disk, does the
stored `corpus_digest` equal its sha256, is the chunk count what the artefacts produce. Prints a
table and exits non-zero on drift. It names the command that fixes it; it never runs it.

**P2.3 — `corpus_refresh --apply`.** Exactly `ingest_standard --force --from-corpus` over the
documents that drifted. Deliberate, never automatic, and it says how many `retrieved_chunks` links
it will drop before it does.

**P2.4 — Deploy reports.** `deploy.sh` runs `corpus_check` after `publish_documents` and **warns**,
never blocks and never refreshes: a first install has an empty corpus, and a blocked deploy over a
stale corpus is worse than a reported one. Records the outcome in the deploy output.

**Gate:** stale fixture → `corpus_check` exits 1 naming the document; `--apply` makes it exit 0;
`deploy.sh` unchanged in exit status when `corpus_check` fails.

---

### P3 — Edits become replayable (prerequisite for a 101-page review)

**P3.1 — `draft + CORPUS_EDITS = reviewed artefact`.** `scripts/build_corpus.py` applies the
document's declared edits itself, so regeneration reproduces the reviewed file byte-for-byte. The
git-ignored `_scratch/apply_bpp_edits.py` stops being part of the record. `--force` no longer
risks an unrecoverable review.

*Fails if:* generating BPP then applying no manual step differs from the committed `bpp.md`.

**P3.2 — The edit table is self-cleaning.** A test asserts each entry's `replacement` differs from
`original`; when the generator learns a correction, the stale entry must be deleted and the test
says so.

**P3.3 — Extractor attribution in the artefact header.** The `<!-- corpus -->` block records the
extractor banner beside `generator:`.

**Gate:** regeneration is a no-op diff for BPP; both new tests fail when broken.

---

### P4 — OPP, 15 pages (the rehearsal)

Generate the draft, review it, declare the edits. Exercises `sub_ref` offset maps, the `§V` seals,
and the 3-column table on pdf 11 (currently in `PAGE_LAYOUT_EXCLUSIONS`). Guards are the BPP set,
parameterised: same identity, character multiset minus edits, every block traceable, reviewed
quotes contiguous and audited. `MAX_EDITS` set from the review, not guessed.

**Gate:** `ingest_standard --doc opp --from-corpus` produces the **same** `(section_ref, anchor,
page, heading_path)` set as `--from-pdf`, and the cardinality test still passes.

---

### P5 — Landscape, 10 pages

Same shape; exercises heading-only structure, bare page stamps, the six-element diagram. Cheapest
of the three — do it second to keep P4's momentum while the review habits are fresh.

**Gate:** as P4.

---

### P6 — SAOSO, 101 pages, and the appendices (absorbs G4)

The long pole, and review-bound. Sequence:

1. Generate the draft; run the mechanical guards first (traceability, identity, character multiset).
2. Produce the **flagged delta**: pages/blocks the generator could not place, plus every block whose
   text differs from the PDF path's. That list is the human review queue (D58) — not the whole
   document.
3. Review, declare edits, and keep the kill criterion in view: **> ~10% of blocks needing edits
   means stop** and reconsider (PRD section 5).
4. Appendices 1–7: the reviewed rows in `knowledge/tables.py` keep owning substance↔condition
   pairing; the artefact owns the page text. Extend `TABLE_ROWS` for Appendices 3, 4 Table 1, 6a/6b
   and 7 **inside this task** (G4), using the committed `-table` pages so the verification needs no
   reader.
5. Update `CORPUS_COLUMN_EXTRACTION_PRD.md` section 3.5.

**Gate:** identity and traceability green for 101 pages; the ten-plus reviewed quotes audited; the
G4 appendix questions (borax, crop protectants, additives) grounded live; no chunk count regression
in retrieval tests.

---

### P7 — Close the loop: ingest, deploy, and the box

**P7.1 — Ingest fails closed (D55).** For a `CORPUS_DOCUMENTS` key with a reviewed artefact, the
default is the artefact. Missing artefact → `CommandError` naming `scripts/build_corpus.py` and
`--from-pdf`. `--from-pdf` remains, and remains tested.

**P7.2 — `CORPUS_DOCUMENTS` moves to a Django-free module** (PRD section 7.2), so the generator needs
no settings.

**P7.3 — Docs.** `HANDOVER.md` section 8, `deploy/README.md`, `uat_seed --check`'s extraction row
(advisory, and now tells the operator it is a *build-time* tool).

**P7.4 — The VPS, from artefacts.** Deploy, `corpus_check` (expect drift: the box's corpus predates
D52/D53), `corpus_refresh --apply`, `corpus_check` clean, three probe questions. The box needs **no
`pdftotext`** for any of it. Record the run in `VPS_DEPLOYMENT.md`.

**Gate:** on the box, `deploy.sh` green with `PDFTOTEXT_BIN` unset **and poppler still installed**;
then, to prove the claim, `apt remove poppler-utils` on a staging check (or `PATH` without it) and
`corpus_refresh --apply` still works.

---

## 3. Verification gates

| Gate | Command | Must show |
|---|---|---|
| The suite | `./scripts/verify.sh` | green, `lint-imports` kept |
| **No reader in the gate** | `PDFTOTEXT_BIN=/usr/bin/true ./scripts/verify.sh` | green — poisoned value ignored by design |
| Fixture provenance | `knowledge/tests/test_section_parsers.py::test_the_fixtures_are_still_the_fixtures` | manifest sha256 matches |
| Extraction drift (build machine) | `python scripts/check_extraction.py` | `no drift` on the build machine; names the page when it drifts |
| Corpus drift | `python manage.py corpus_check` | exit 0 on a current box, 1 naming documents otherwise |
| Deploy on the target | `sudo bash deploy/deploy.sh` | `✅ Deploy complete`; a `corpus_check` warning is allowed and reported |
| Grounding, live | `probe_chat.py` (three questions) | cardboard, hens and straw grounded |

**Proof rule.** Every new guard is mutation-tested: break it, watch the named test go red,
restore. The poisoned-extractor gate is the mutation test for P1 as a whole.

---

## 4. Follow-ups (named, not fixed here)

1. **A single command that owns "regenerate → diff → verify".** P1.5's script and P3's replay are
   two halves; a `corpus_build` command joining them is worth doing once, not twice.
2. **`-table` is still Xpdf-only.** If Xpdf ever becomes unavailable, the `-table` fixtures are the
   fallback (they are committed), but *regenerating* them would need a replacement (`-tsv`/`-bbox`).
3. **Retrieval ranking (G3)** and the **escalation path (G6)** are untouched by this plan.
4. **The workbook** stays unpublished until the committee says otherwise (D22).

---

## 5. What "done" looks like

1. `PDFTOTEXT_BIN=/usr/bin/true ./scripts/verify.sh` is green, and stays green — the gate cannot
   regress to needing a reader.
2. All four governed documents ingest from reviewed artefacts by default, and a missing artefact
   stops the ingest with a message naming the generator.
3. The VPS is rebuilt from artefacts with **no PDF reader involved**, and `corpus_check` reports it
   as current.
4. A `pdftotext` upgrade can no longer change what the product answers — only what a *build* would
   produce, which `check_extraction.py` reports to a human.

**Effort:** P1 ~half a session; P2 ~half; P3 ~half; P4+P5 ~1 session including review; P6 1–2
sessions plus human review; P7 ~half. The critical path is the SAOSO review, not the code.
