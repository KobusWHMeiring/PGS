# Corpus Canonical Format — Implementation Plan

**Status:** In Progress — P0 settled (D55–D59); **P1 landed 2026-10-22**; **P2.1–P2.4 landed
2026-10-28** (`corpus_digest` on the row, `corpus_check`, `corpus_refresh`, the deploy report);
**P2.5 and P2.5a landed 2026-10-22** (migration `core/0006`, read side `scripts/why_refused.py`);
**P6 landed 2026-10-28 for SAOSO** (`knowledge/corpus/saoso.md`, 271 sections / 291 artefact chunks
/ 338 ingested, Appendix 6b open); **P7.1 landed 2026-10-28** (ingest fails closed, with one
amendment — §P7.1).
**Remaining:** P2.6–P2.8 (`chat_review`, the staff flag, retention), P4 (OPP), P5 (landscape),
P6's step 4 for Appendices 3, 4 Table 1, 6b and 7, P7.3 (docs) and P7.4 (the box, from artefacts).
**Owner:** Corpus ingestion (sub-plan B), grounded chat (sub-plan D), deployment
**Last Updated:** 2026-10-28
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
| P2 | `knowledge/management/commands/corpus_check.py`, `corpus_refresh.py`, `core/management/commands/chat_review.py`; `knowledge/migrations/0003_*.py`, `core/migrations/0006_*.py` | `knowledge/models.py`, `core/models/_chat.py`, `core/services/_chatbot.py`, `core/admin.py`, `knowledge/ingest.py`, `deploy/deploy.sh` |
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

**Built 2026-10-22 — measured, not assumed.**

| Check | Result |
|---|---|
| `./scripts/verify.sh` | **800 tests**, `lint-imports` kept, **38 s** (was 89 s — the suite no longer shells out to `pdftotext`) |
| `PDFTOTEXT_BIN=<inherited bogus value> ./scripts/verify.sh` | green — the export discards it |
| Mutation: remove the export from `verify.sh` | `tests/tools/test_verify_gate.py` fails |
| Mutation: hand-edit one page fixture | `page_fixtures.pages()` fails, naming the digest |
| Mutation: set a different extractor banner in `MANIFEST.json`, run the generator | `extract_fixtures.py` refuses, naming both banners |
| `scripts/check_extraction.py` on this box | `no drift` across 9 fixtures, 139 pages |

Nine page fixtures (4 × `layout`, 4 × `raw`, SAOSO × `table`), ~1 MB, with the extractor
banner and the source PDF's sha256 in `MANIFEST.json`. Six modules changed their *input*,
not one assertion: `test_columns`, `test_reflow`, `test_section_parsers`,
`test_corpus_bpp`, `test_tables`, and `test_ingest` (via
`page_fixtures.stub_ingest_extraction`, which also has to serve `test_retrieval`'s and
`core/tests/test_chatbot_grounding.py`'s ingest-from-PDF fixtures — two more than the plan
predicted, found by running the gate with the poison in place).

One test changed subject rather than input:
`test_a_file_that_is_not_a_pdf_is_a_loud_extraction_error` became
`test_an_unreadable_file_is_a_loud_extraction_error` — the ingest must not swallow an
extraction failure, and *what `pdftotext` does with a corrupt file* is not the suite's
subject. The stub raises for it.

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

**P2.5 — Answers become attributable.** *(Built 2026-10-22 with P2.5a, migration `core/0006`; the read side is `scripts/why_refused.py`.)* Two fields on `ChatMessage`, written with the
assistant row: `prompt_version` (the `PROMPT_VERSION` under which it was produced) and
`corpus_fingerprint` (the same fingerprint the answer cache uses, so a stored answer can be
tied to the exact corpus that produced it). Additive migration `core/0006`.

*Why:* after P7.4 re-ingests the corpus, old and new answers sit in one table. Without
these fields a refusal cannot be attributed to a corpus gap, a retrieval budget or a prompt
contract that no longer exists — which is the difference between a fix and a guess.

*Fails if:* a stored assistant row has an empty `prompt_version`; or two corpora produce
rows indistinguishable by `corpus_fingerprint`.

**P2.5a — store what was *claimed*, not only what was supplied.** *(built 2026-10-22;
added from G9 — `CHAT_ANSWER_COVERAGE_PRD.md`. P2.5 makes an answer attributable; this makes it
auditable.)* Three additions, one migration (`core/0006`, together with P2.5):

1. **`citations` JSON on the assistant row** — the raw citations the model returned *and*
   the audited subset that was accepted, each with locator, page, quote and document.
   Without it the visible claim is not stored at all: `ChatMessage` keeps the answer text,
   so "it said sodium borate is permitted, and here is the quote it used" cannot be
   re-checked later. It also makes P2.6's own metric — *"answers whose citations all come
   from one document"* — computable, which it currently is not: `retrieved_chunks` is
   every chunk **supplied**, not the ones cited.
2. **`refusal_checks` JSON on the refusal path** — the `problems` tuple from
   `audit_citations`, not just the coarse `reason`. G9 turned on exactly this distinction:
   `not present in the retrieved set` is a **prompt-contract** defect, while `the quote is
   not in the cited chunk` is a **corpus/extraction** defect. `CITATION_AUDIT` alone cannot
   tell them apart, and a reviewer who cannot tell them apart fixes the wrong layer.
3. **A grounding snapshot that survives re-ingest.** The `retrieved_chunks` M2M cascades
   when `--force` re-ingests a document (that is what the flag documents itself as doing),
   so rebuilding the corpus erases what every past answer stood on — which contradicts
   D59's "keep transcripts indefinitely": the question survives, the answer survives, and
   the grounds for it are gone. Store a JSON snapshot beside the M2M (locator, page,
   heading_path, chunk sha and a quote sha), so the FK serves joins while the chunks exist
   and the snapshot serves the record when they do not. **We destroyed today's evidence
   ourselves** by rebuilding the corpus before this existed.

*Deliberately not stored:* the rendered prompt (reproducible from `prompt_version` +
`question` + chunks, and storing it invites reading a template as a historical fact), and
chunk text (the corpus owns that; a copy under `ChatMessage` would go stale in a second
place). Cost: ≤6 KB per turn. No new personal data — the question, `ip_hash` and
`user_agent` are already there, and D59/P2.8 already owns the retention question.

*Fails if:* a `CITATION_AUDIT` refusal has an empty `refusal_checks`; a `--force` re-ingest
leaves an assistant row whose grounding snapshot is empty; or `chat_review` reports a
citation metric that had to fall back to `retrieved_chunks` to compute.

**P2.6 — `manage.py chat_review`: read-only, weekly.** A window (default 30 days), markdown
out, no writes:

- refusal counts by `reason`, and OPEN escalations older than the window;
- the most-asked questions, normalised (the same key the answer cache uses) — repetition is
  the strongest signal that something should be answered;
- answers whose citations all come from one document, and `CITATION_AUDIT` clusters (the
  model-contract metric, not the corpus metric);
- cache-hit share (`model` is blank on a cache hit), so the volume being analysed is real.

The loop it serves: refusal → review the stored `retrieved_chunks` → fix the artefact
(P3–P6) **or** add the question to `SUITE` in `scripts/probe_chat.py`, so the fix is measured
forever. That is how G1, G2 and G7 were found and closed.

*Fails if:* the command writes a row (assert before/after counts); or a refusal with no
retrieved chunks is reported as a corpus gap rather than as a retrieval failure.

**P2.7 — A staff flag for the wrong-but-grounded answer.** Append-only fields on
`ChatMessage` (`flagged_at`, `flagged_by`, `flag_note`) plus an admin action. **No public
surface** — a public thumbs-down is a spam vector and a support queue nobody staffs yet.
`chat_review` lists flagged rows first.

*Fails if:* a non-staff user can flag; or flagging makes the message content editable
(history is evidence).

**P2.8 — Retention (D59).** The decision is **keep every transcript until the group sets a
schedule**. Consequence recorded, not deferred: this is a public form, `ip_hash` and
`user_agent` are stored, and a question can contain personal data ("my neighbour's farm on
the N2"), so the group's schedule is a POPIA obligation rather than a preference. No purge
job is built today; the documented path is deliberate, because deleting a `ChatSession`
cascades its messages while an `EscalatedQuery` survives via `SET_NULL` — which is exactly
right for the gap record and therefore must be answered explicitly by whoever writes the
purge.

*Fails if:* a doc claims a retention schedule that does not exist.

### P2.1–P2.4 — outcome, 2026-10-28

Built as one slice, because the four are one idea: **drift is visible, and repairing it is a
decision rather than a side effect.**

| Task | Landed as |
|---|---|
| P2.1 | `StandardDocument.corpus_digest` (migration `knowledge/0004`), written by `ingest_standard`. Empty means "parsed from the PDF" — a fact, not a missing value. |
| P2.2 | `knowledge/drift.py` (`corpus_states()`) + `manage.py corpus_check` — read-only, one row per governed document, exit 1 on drift, naming the fix and never running it. |
| P2.3 | `manage.py corpus_refresh [--apply]` — a dry run until told otherwise, and it counts the `ChatMessage.retrieved_chunks` rows the re-ingest will drop **before** it drops them. |
| P2.4 | `deploy/deploy.sh` runs `corpus_check` after `publish_documents`, guarded with `if !` so `set -e` cannot turn a stale corpus into a failed deploy; it never refreshes. `tests/tools/test_deploy_corpus_check.py` holds both halves. |

Two things the task text did not settle, and how they were settled:

1. **A document with no artefact is not drift.** `opp` and `landscape` report `no artefact`
   and do not change the exit status: they are a recorded gap (P4, P5), and a check that
   went red for work nobody has done would be ignored by the second person who saw it. The
   three states that *are* drift say which they are, because the fixes differ.
2. **The citation-link count is structural.** `citation_links()` walks Django's relation
   metadata instead of naming `ChatMessage`, because `knowledge` must not import `core`
   (`build_principles.md` §I). Its only honest test needs a real citation table, so it lives
   in `core/tests/test_corpus_refresh_links.py`.

`chunks_for_sections()` moved out of `ingest_standard` (both the chunking and the reviewed
`TABLE_ROWS` replacement) so the expected count in `corpus_check` comes from the code that
writes chunks. A second implementation of that rule would have been a second answer to "is
this box current?", and the two would have drifted apart silently.

**Re-measured on this machine, 2026-10-28** (`manage.py corpus_check`, corpus of 2026-10-27):
`bpp 9/9 drift (built from the PDF)`, `saoso 338/338 drift (built from the PDF)`,
`opp`/`landscape` `no artefact` — which is the exact state the plan predicted for a corpus
ingested before P2.1, and the exit status was 1. The local corpus was deliberately **not**
refreshed: this machine has no `GEMINI_API_KEY`, so an `--apply` here would have silently
downgraded 385 embedded chunks to lexical-only. That is P7.4's job on the box.

---

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

### P6 — SAOSO, 101 pages, and the appendices (absorbs G4) — **landed 2026-10-28, 6b open**

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

**Outcome, 2026-10-28.** `knowledge/corpus/saoso.md` exists (271 sections, 71 page markers), the
ingest reads it (`source=corpus`, 338 chunks, all embedded) and the delta is **three reviewed edits**
— the *Factory farming* superscript (`m²`), and two letterspaced Appendix 6a/`S5.5.7` lines. Step 3's
kill criterion was never approached: 3 of 1 537 blocks, not ~10%.

What the draft forced, because each was a defect the artefact exposed rather than a preference:

| found | fixed in |
|---|---|
| the generator sliced *every* page, so `S1` carried dropped pages and `Appendix 7` repeated Section C three times | `SaosoParser.body_lines()` is the one body definition; the generator slices it |
| `-raw` fallback parses this document to **zero sections** (one double-spaced column) | `RAW_FALLBACK_OFF = {"saoso"}` in the generator |
| a `ref:`-annotated heading carried its `#` marker into the text, so every clause rendered at heading weight and its wrapped continuation split off again | `corpus._heading_text()` |
| `heading_path` named the parent in one path and the section in the other | `SaosoParser` includes the section, per the format's own rule |
| a clause heading's slug overran `anchor` (128), so the first ingest died `value too long` | `corpus.section_anchor()` truncates at a word boundary |
| the artefact's Markdown/whitespace made **230 of 291** passages read as changed text, so evidence stopped relinking | `text_sha()` hashes a passage's words, not its layout |

**Step 4 done for 6a only.** `TABLE_ROWS["Appendix 6a"]` is twenty reviewed rows (class → stocking
rate), verified against `-table` **and** against EU 2092/91, which the appendix cites: the two agree
row for row, and `test_tables.py` pins each class to the value on its own printed line — a presence
check would pass on the broken `-layout` pairing. `TABLE_BANDS[85] = 88`.

**Appendices 3, 4 Table 1, 6b and 7 remain**, and they are a different kind of work: 6b alone is
three pages of species × live weight × indoor/outdoor measures, where `TableRow` (one substance, one
condition cell) does not describe what the paper prints. 6a could be curated without inventing a
column label; 6b cannot, so it needs a product decision first
(`BugFixes/saoso_text_glyphs_and_boundaries.md` §8). Appendices 3, 4 and 7 are single-column lists
and are the same shape as 6a.

### P7 — Close the loop: ingest, deploy, and the box

**P7.1 — Ingest fails closed (D55).** For a `CORPUS_DOCUMENTS` key with a reviewed artefact, the
default is the artefact. Missing artefact → `CommandError` naming `scripts/build_corpus.py` and
`--from-pdf`. `--from-pdf` remains, and remains tested.

**Landing note, 2026-10-28 — one amendment, made because P7.1 is being built before P4/P5.**
"With a reviewed artefact" is read as **a declaration, not a file-exists probe**:
`CORPUS_DOCUMENTS[doc_key]["corpus_artefact"]` names the file, and only `saoso` and `bpp`
declare one today. A probe answers "is there a file lying around?"; the question D55 asks is
"is this document *supposed* to come from a review?" — and the two disagree exactly when the
file is missing, which is the failure worth catching. `opp` and `landscape` therefore keep
parsing their PDFs until P4 and P5 declare theirs, which is a recorded gap rather than a
silent fallback.

What that changed in the suite is worth recording, because it is the point: ~10 tests that
ingest `saoso`/`bpp` from the PDF now say `from_pdf=True`. They were always about the
extraction path; until now nothing distinguished it from the text of record. One measurement
moved with the corpus — `test_the_shipped_corpus_resolves_as_measured` (39/30/9 → 41/30/11):
SAOSO's artefact carries each section's printed heading in the body, so `Appendix 4. Table 1`
and `Table 2` (pp. 81, 83) read as mentions of `Appendix 4`, which names two tables and so
resolves to neither. No link was lost (`EXPECTED_LINKS` unchanged at 30) and losslessness is
still asserted per passage.

**P7.2 — `CORPUS_DOCUMENTS` moves to a Django-free module** (PRD section 7.2), so the generator needs
no settings.

**P7.3 — Docs.** `HANDOVER.md` section 8, `deploy/README.md`, `uat_seed --check`'s extraction row
(advisory, and now tells the operator it is a *build-time* tool).

**P7.4 — The VPS, from artefacts.** Deploy, `corpus_check` (expect drift: the box's corpus predates
D52/D53), `corpus_refresh --apply`, `corpus_check` clean, three probe questions. The box needs **no
`pdftotext`** for any of it. Record the run in `VPS_DEPLOYMENT.md`.

**Pre-condition found 2026-10-28, while building P2.1–P2.4 — this gate cannot pass as written.**
`ingest_standard`'s artefact branch still calls `extract_pages(path)` for **one** field: the printed
`toc` (`knowledge/ingest.py`, "the artefact carries no printed TOC, and `--from-corpus` has no
pages: the PDF is read again for this one purpose", D68 §7.5). So `corpus_refresh --apply` — the
command this task runs on the box — needs a PDF reader even though the *text* comes from a reviewed
artefact. Two honest fixes, and the choice is a decision, not a preference:

1. **carry the TOC in the artefact** (`<!-- toc -->` block in `knowledge/corpus/*.md`), so the file
   really is the whole text of record; or
2. **preserve the stored `toc` across a refresh** (`corpus_refresh` reads the old row's `toc` and
   passes it to `ingest_standard`), since the PDF's sha256 is unchanged and the TOC is a property of
   the printed pages, not of the extraction.

(2) is smaller and loses nothing; (1) is the one that makes the artefact self-contained, which is
what D53 says it is. Until one lands, the box's gate is "`corpus_refresh --apply` succeeds on a
machine that has poppler", not "needs no reader at all".

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
