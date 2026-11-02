<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0g. 2026-10-27 — the reader is the document: a table, references that go somewhere, and a glossary

**All ten tasks of `In Progress/READER_STRUCTURE_PLAN.md` landed.** Gate **1138 passed / 1 skipped**,
Playwright **53**, `lint-imports` kept, `manage.py check` clean, `uat_seed --check` **ready** (366
chunks, 0 without a vector, 8 published, Xpdf 4.00). **Nothing pushed, nothing deployed.**

- **Appendix 2 renders as the paper's table** (D70.1): a caption quoting the two printed columns, one
  legend sentence, four part headings, three `South African specific` qualifiers, and 30 rows whose
  substance is its own entry — so `Guano` no longer renders at body weight. The 19 rows whose
  condition cell the paper leaves empty carry a muted `no condition printed`, and no row reads as
  permission. The structure is reviewed data beside `TABLE_ROWS` (`TABLE_SECTIONS`), and a test proves
  each of the seven dividers still sits, on the printed page, immediately above the row it names.
- **A reference goes somewhere, or it says why not** (D70.3): `Appendix 6 Minimum Surface Areas…`
  opens Appendix 6b in a new tab; `Section 4.6.2` opens `S4`; **`Section A – 2.3` opens the page's own
  note that Part A is printed and not in the corpus**, never `S2` — a different part. Measured: **39
  mentions, 30 resolved, 9 left as text**, and all 9 (8 × `Appendix 4`, 1 × bare `Appendix 6`) carry a
  tooltip naming the parts they could be. The BPP and the landscape resolve nothing, which is correct.
- **A defined word is a click away** (D70.4/D70.7): the term list is **derived** from `S1`'s rendered
  blocks minus a reviewed rejection list, so it cannot stale. **69 headwords and 69 ids** on the real
  corpus; one link per term per passage, and none inside the glossary itself.
- **One locator per run** (D70.5): **366 → 311** lines (319→273, 30→28, 8→6, 9→4), every passage keeps
  its `id`, so a citation still lands.
- **The missing-sections note moved out of the phone disclosure** and carries `id="not-in-corpus"`
  (D70.6) — a fragment inside a closed `<details>` cannot be scrolled to.

**Page weight, measured the same way before and after** (dev corpus, Django test client, gzip level
6): Appendix 2 **33 309 → 37 664 B raw (+13.1 %), 5 941 → 6 521 B gzip (+9.8 %)**; `S1` 47 935 →
49 979 raw (+4.3 %). The PDF of the same appendix is 192 KB. **No new query**: the reader was 3
queries before this slice and is 3 after it.

**Corrected while building (recorded, not absorbed):** the plan expected **71** glossary headwords and
the page anchors **69**. `Buffer Zone` and `Homeopathic Treatment` are each the tail of one chunk and
the head of the next, so the reader's overlap trimming prints them as the last *paragraph* of a
passage, where the layout finds no following line and does not call them terms. They are not linkable;
the test asserts their absence. Making them linkable needs the corpus artefact, not view work.
`READER_STRUCTURE_PLAN.md` §12 has the six signature changes and the three findings.

**Two further corpus findings were filed the same day**, both found by reading the rendered appendix
and the glossary: `BugFixes/saoso_text_glyphs_and_boundaries.md` **§4** — three lines were extracted
letter by letter (`p u r c h a s e d` in `S5.5.7`, `b o v i n e a n i m a l s` and `t h a n o n e`
in Appendix 6a), which search cannot match; and **§5** — Appendices **6a and 6b** lost the rows of
their tables (20 animal classes and 20 values, 5 attached and 15 piled at the end), which is the
Appendix 2 defect still live for the two appendices nobody curated, and is what **G4** means. Both
are reviewed-artefact work (D53), and §5's mechanism already exists: two new keys in `TABLE_ROWS`.

**The UAT is signed, and it closed three features.** `tests/uat/concordance_uat.md` carries eleven
**PASS** results, signed by **Kobus (Product) on 2026-10-28** against commit `4e02d71` and the dev
corpus (366 chunks, Xpdf 4.00), applied by `scripts/uat_signoff.py`. The export's environment says
`working_tree: modified` — the only dirty file at generation was the artefact itself; `uat_page.
environment()` now excludes it (`fix(uat)`), and the signed artefact is deliberately not regenerated
because it must keep naming `4e02d71`. That signature closes **CONCORDANCE** (D68),
**PASSAGE_LAYOUT** (Scenario 8) and **READER_STRUCTURE** (Scenarios 9–11); all six documents are in
`Done/`. **The PGS administrator, committee reviewer and consumer-member seats are still empty** —
the OPP wants three voices (D4) — and the file says so.

**Four follow-ups are filed, separately, because they are four different kinds of work** (the
product owner's 2026-10-28 reading session):

| Item | Where | Size |
|---|---|---|
| `/documents/` links to the concordance (four of eight have text) | `ready/DOCUMENTS_READER_LINK_PRD.md` | one task, decided |
| A wrapped clause renders as two paragraphs (25 of 319 chunks; `S23.3`) | `BugFixes/reader_clause_line_breaks.md` | one display rule + guards |
| The `SECTION B` banner at the end of **twelve** branches | `BugFixes/saoso_text_glyphs_and_boundaries.md` **§3, re-measured** | artefact/parser (D53) |
| Tables as reviewed data (JSON/MD) so any table can be displayed — absorbs **G4** | `Refinement/TABLES_AS_DATA_PRD.md`, four questions open | the big one |

**One defect shipped in this slice and was found by the product owner, not by the suite** — worth
reading before trusting a green gate on a layout change. Moving the missing-sections note out of the
phone `<details>` made it a **third child** of the two-column `.reader__body` grid: the passages
wrapped to the next row and the *sticky* tree sat on top of the text, so following a citation landed
on a page whose quoted line was behind the contents list. Markup valid, every string present, anchors
resolving, console clean, 1138 tests green, no 390 px overflow. Fixed by wrapping the tree and the
note in `.reader__tree-column` and moving the sticky rule there (the CSS comment had always said the
sticky box must be the grid item), and guarded by `tests/e2e/test_reader_layout.py` — three browser
assertions, proven by reverting the fix. **The e2e suite is outside `verify.sh`; run it whenever a
template or stylesheet changes** (`testing_hazards.md` §3.12).

---
