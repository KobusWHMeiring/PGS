<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0h. 2026-10-28 — SAOSO is a reviewed artefact, and three bugs the draft found

**This is the most recent slice, and it is not deployed.** Plan `CORPUS_CANONICAL_FORMAT_PLAN.md`
**P6** is done for SAOSO: `knowledge/corpus/saoso.md` is the text of record (271 sections, 71 page
markers, 3 reviewed edits in 1 537 blocks), and the ingest reads it —
`source=corpus`, **338 chunks, all embedded**. `uat_seed --check` expects **385** now
(SAOSO 338 + OPP 30 + BPP 9 + landscape 8). Gate green at **1160**; Playwright **60**.

- **What the artefact fixed** (`BugFixes/saoso_text_glyphs_and_boundaries.md` §2–§5a, all closed):
  the `m²` superscript no longer splits *Factory farming*; the `SECTION B` page banner no longer ends
  twelve branches with a part title and nothing after it; three letterspaced lines are words again;
  and Appendix 6a is **twenty reviewed rows** — *Laying hens → 230* — instead of twenty classes
  followed by twenty unrelated numbers.
- **The generator was the real defect, five times.** It sliced *every* page rather than the parser's
  body stream (so `Appendix 7` reproduced Section C three times); its `-raw` fallback parses this
  document to **zero sections**; a `ref:`-annotated heading carried its `#` into the text, so every
  clause rendered at heading weight *and* its wrapped continuation split off again; `heading_path`
  named the parent in one path and the section in the other; and a clause heading's slug overran
  `anchor`'s 128 characters, so the first ingest died with `value too long`. Each is fixed where it
  belonged, and `test_corpus_saoso.py` (20 guards) proves the two paths agree.
- **Appendix 6b is deliberately still open.** Three pages of species × live weight × indoor/outdoor
  measures, where `TableRow` (one substance, one condition cell) does not describe what the paper
  prints. Curating it means deciding what a row *is* — a product call, not a parser one (§8 there).
- **Evidence survived, and the tool to do it is new.** `manage.py relink_evidence --apply`
  (commit `a67ee5d`) rebuilds `ChatMessage.retrieved_chunks` from the `grounding` snapshot wherever
  the passage's text is unchanged. Both `--force` rebuilds in this session ran it: **57 links
  restored**, 30 left unlinked because a *previous* rebuild had genuinely rewritten those passages.
  `text_sha` now hashes a passage's **words**, not its layout — before that the artefact made
  **230 of 291** passages read as changed text and evidence stopped relinking.
- **The concordance UAT is signed 13/13 PASS** (`tests/uat/concordance_uat.md`, Kobus/Product,
  against `e6f4464`, 385 chunks): the eleven scenes of 2026-10-28 plus the clause case re-judged,
  Scenario 12 (the documents page offers the concordance) and Scenario 13 (Appendix 6a's stocking
  rates). Scenarios 8's clause case, 12 and 13 were judged at sign-off from the implementation and
  its guards, and their result lines say so — a hands-on pass is still owed before the P7.4 deploy.
  `DOCUMENTS_READER_LINK_PRD.md` moved to `Done/` on that sign-off.
- **`scripts/fast.sh` and `pgs.settings_test` are the other agent's session**, in the same tree:
  the two test lanes, the fast password hasher, and the `slow` marker. Not this slice's work, and not
  committed with it.
