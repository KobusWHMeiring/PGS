<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0e. 2026-10-27 — the reader is refined; what is left is judged, not built

**What landed this session** (committed; gate **983 passed / 1 skipped**, Playwright **53**):

- The concordance's **CSS pass**: a **72 rem** working column, a **38 rem** reading measure (~85
  characters at 16 px), one hairline per printed clause, a sticky search **and** tree, tabular page
  numbers, muted locators, a target highlight that bleeds to the pane edge, and a one-row search on a
  phone. **The citation scroll offset now clears the sticky search** — before this, following a
  citation put the passage *behind* the search (measured: target top 67 px, search bottom 191 px).
- **Passage layout** (`PASSAGE_LAYOUT_PRD.md`/`_PLAN.md`, both in `In Progress/`): paragraphs with
  hard wraps joined, printed headings, real lists (`a.`–`f.`, roman nested in `S8.1`), and glossary
  terms (`ACB`, `Habitat`, `Extensive Farming`) above their definitions.
- **`S1` (Definitions)** — the report that started this: the chunk overlap is **no longer printed
  twice** (`strip_overlap`; 21–57 repeated words at five boundaries) and terms are no longer glued to
  their definitions. The page reads as a glossary.

**The one thing left to do is the UAT.** `tests/uat/concordance_uat.md` has eight scenarios and none
is signed; **Scenario 8** is the passage layout. The tooling is the same as §18: `uat_seed --check`,
`scripts/uat_runner.py`, `scripts/uat_signoff.py`. Nothing below blocks it.

### Final refinements deliberately left for the next agent (each is a judgement, not a TODO)

1. **Repeated passage locators inside one branch.** `S1` prints `S1 · printed p. 22` above each of its
   eight chunks; `S5` repeats a locator 52 times. They mark the ids a citation can land on. Decide:
   keep them (honest, and useful when a citation lands mid-branch) or print the branch's locator once
   and keep only the `id`s. Scenarios 1 and 3 are where it shows.
2. **Desktop search width.** The input is ~941 px inside the 1088 px panel at 1280 px. Capping the row
   (~40 rem) reads better but leaves a large empty panel; the alternative is a narrower search panel.
   Judge on a 1440 px screen as well as 1280.
3. **Phone search is not pinned** (111 px + 80 px header ≈ 25% of an 844 px screen); the tree is a
   disclosure instead. If the reviewer wants both pinned, make the phone search one compact row or a
   single field with an icon button.
4. **The tree has no scroll affordance** when 23 rows exceed the viewport on desktop. A subtle
   top/bottom edge may help; the scrollbar appears on hover only.
5. **Term vs heading weight** is two steps (`--text-lg` vs body, both bold forest). Judge at 390 px
   whether `ACB` reads as a term rather than as a section.
6. **The corpus artefacts are filed, not fixed** — `BugFixes/saoso_text_glyphs_and_boundaries.md`:
   30 of 366 chunks hold U+FFFD where the paper prints `°`, `²`, `≥`, a bullet, an en dash or `ü`; a
   superscript `2` splits the *Factory farming* sentence; `S1`'s last chunk carries the `SECTION B`
   half-title of printed p.30. These need the reviewed SAOSO artefact and `--force`; the reader must
   **not** substitute characters (the citation audit checks quotes against the stored text).

**Backlog state.** `Done/` gained **three** features on 2026-10-28 — CONCORDANCE, PASSAGE_LAYOUT and
READER_STRUCTURE (PRD + plan each). `In Progress/`: ASK_SURFACE, VPS_DEPLOYMENT,
CORPUS_CANONICAL_FORMAT, CORPUS_COLUMN_EXTRACTION, MVP0. `ready/`: only the MVP 1a pair.
`BugFixes/`: `citation_anchor_collision` **closed**; `saoso_text_glyphs_and_boundaries` — §1 closed
(the glyph loss), **§2–§5 open** (the `m²` superscript, the `S1` half-title, three letterspaced
lines, and Appendices 6a/6b's lost table rows — the last is G4's shape and its mechanism already
exists as `TABLE_ROWS`).

**Repo state.** `main`, tree clean, **42 commits ahead of `origin/main`**, nothing pushed or deployed.
The live site is still `206f35f`, and its corpus predates D52/D53 — §18's two operational items are
open and now further behind (the reader's layout is not deployed either).
