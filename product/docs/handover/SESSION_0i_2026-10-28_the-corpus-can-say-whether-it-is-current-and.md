<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0i. 2026-10-28 — the corpus can say whether it is current, and the ingest fails closed

**This is the most recent slice.** Plan tasks **P2.1–P2.4** and **P7.1** of
`product/backlog/In Progress/CORPUS_CANONICAL_FORMAT_PLAN.md`, built as one idea: *drift is
visible, and repairing it is a decision rather than a side effect.* Nothing about retrieval,
the reader or a public page changed.

- **`StandardDocument.corpus_digest`** (migration `knowledge/0004`) records the sha256 of the
  reviewed artefact a corpus was built from, or `""` when the PDF was parsed. Until now that
  value existed only on `IngestReport` — printed and thrown away — so nothing could compare a
  box with its review.
- **`manage.py corpus_check`** — read-only, one row per governed document, exit 1 on drift, and
  it names the fix instead of running it. Three states are drift and it says which: *built from
  the PDF*, *the artefact changed since*, *nobody ingested it*. **No artefact is not drift**
  (`opp`, `landscape` until P4/P5) — a check that went red for work nobody has done gets ignored.
- **`manage.py corpus_refresh [--apply]`** — a dry run until told otherwise. `--force` deletes
  the join rows every chat turn stood on, so it counts them first (`citation_links()` walks
  Django's relation metadata, because `knowledge` may not import `core`) and says the number
  before `--apply` can spend it.
- **`deploy/deploy.sh`** runs `corpus_check` after `publish_documents`, guarded with `if !` so
  `set -e` cannot turn a stale corpus into a failed deploy, and it **never refreshes**: a
  re-embed of four documents is a decision for a person with a terminal.
- **The ingest fails closed (D55).** A document that *declares* a reviewed artefact
  (`CORPUS_DOCUMENTS[key]["corpus_artefact"]` — `saoso`, `bpp`) now reads that file by default;
  if it is missing the command exits non-zero and writes nothing, naming
  `scripts/build_corpus.py` and `--from-pdf`. A declaration, not a file-exists probe: the two
  disagree exactly when the file is gone, which is the failure worth catching.
- **What moved in the suite:** ~10 tests that ingest `saoso`/`bpp` from the PDF now pass
  `from_pdf=True` — they were always about the extraction. `test_the_shipped_corpus_resolves_as_measured`
  re-measured 39/30/9 → **41/30/11**: the artefact carries each section's printed heading in the
  body, so `Appendix 4. Table 1`/`Table 2` read as mentions of `Appendix 4` (two tables, one name,
  no single target). No link was lost; `EXPECTED_LINKS` is unchanged at 30.
- **Judged, not built:** nothing here needs a UAT table of its own. The operator-facing judgement
  — *do these three commands read clearly on a real box, and does the deploy's warning tell
  someone what to do?* — is carried by **P7.4**, which runs all of it against the live corpus.
- **This machine is (correctly) reported as drifting:** `bpp 9/9 · built from the PDF`,
  `saoso 338/338 · built from the PDF`, `opp`/`landscape` `no artefact`, exit 1. It was **not**
  refreshed: there is no `GEMINI_API_KEY` here, so `--apply` would have downgraded 385 embedded
  chunks to lexical-only. That is the box's job, not the laptop's.
- **Known gap, unchanged:** `knowledge/tests/test_anchors.py::test_every_passage_of_the_real_corpus_resolves_to_itself`
  skips in both lanes ("no corpus ingested on this instance"), so the D68 anchor guard is not
  actually in the gate. Worth closing before P7.4.
- **New finding, blocking P7.4's own gate:** the artefact ingest still reads the PDF for **one**
  field — the printed `toc` (`knowledge/ingest.py`, the `toc_pages = extract_pages(path)` line in
  the artefact branch, D68 §7.5). So `corpus_refresh --apply` needs `pdftotext` even though the text
  comes from a reviewed artefact, and P7.4's "the box needs no reader for any of it" / "remove
  poppler-utils and refresh still works" cannot pass as written. The plan records both fixes
  (carry the TOC in the artefact, or preserve the stored `toc` across a refresh); neither is built.
- **Also filed this session, nothing built:** **`Refinement/CODE_ATLAS_PRD.md`** — the product
  owner's requirement for one generated, committed view of the application as built (schema,
  services, views and routes, async/schedulers, the corpus pipeline), in `product/docs/state/`, with
  a gate that regenerates and diffs so it cannot rot. It answers "what exists" and is deliberately
  not a handover, a spec or a UAT. Today's numbers are in its §1 and they are the reason it exists:
  30,744 Python lines, 12 models / 87 fields, 46 service functions, 17 view functions, **one**
  Celery task and **no beat schedule**, 36 migrations, 59 test modules.
- **Awaiting one decision, D71** (`product/design/d71_p4_and_the_generator.html`): what the next
  corpus slice is, now that P4's first step is measured broken. Recommendation: repair the generator,
  make P3.1's regeneration gate real, teach `OppParser` the `heading_path` rule, then review the OPP
  as a verification pass (`product/backlog/In Progress/CORPUS_CANONICAL_FORMAT_PLAN.md`, P4's
  landing note).
- **Not committed by this session:** the test-lane work (`scripts/fast.sh`, `pgs/settings_test.py`,
  the `slow` marker, `tests/tools/test_test_harness.py`, `product/docs/context/TEST_COST_PLAYBOOK.md`)
  arrived uncommitted and was deliberately left uncommitted — it is another session's, and the gate
  is green with it in the tree (1265 passed / 1 skipped).
- **⚠ Two artifacts claim D71.** This session filed `product/design/d71_p4_and_the_generator.html`
  ("what is the next corpus slice") and its export emits a `D71` row for SPEC §18.3. A later
  uncommitted artifact, `product/design/d71_self_check_questions.html` ("the front door: 19 questions
  before a farmer applies", `/before-you-apply/`), claims the same number. **Recommendation:** the
  front-door page keeps **D71** — it is a product-and-copy decision, which is what §18.3 is for — and
  the corpus page becomes an unnumbered execution decision or **D72**; the clear-conversation
  decision in `Refinement/ASK_PANEL_REFINEMENTS_PRD.md` §2 then becomes D73. Nothing is renamed yet,
  because both files belong to different sessions and the owner should choose.

---
