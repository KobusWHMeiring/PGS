<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0n. 2026-10-30 — the table block landed, and step 1 is mechanism only

**State: green, and the artefact format can hold a table.** Step 0 reproduced §1 of the landscape
PRD exactly, and step 1 shipped the block. Nothing of the landscape itself is curated yet — the
fixture that proves the format holds p4's real rows is a *draft*, and says so.

### 0n.1 The board work got committed, in two attributed commits

`c7a7df8` (the feature: `_board.py`, `_board_data.py`, `building.html`, `scripts/board.py`,
`test_board.py`, the `Public:`/`Summary:`/`Public title:` headers, the deploy pre-check, the CSS and
`DESIGN.md` §7.12) and `7678880` (D74, the regenerated `backlog.md`, §0m). Green before and after:
`fast.sh` **1331 passed / 1 skipped** with the work in the tree, which is how §0l.4 described it.
`backlog.py --write` was re-run **after** the PRDs were committed, so the index no longer names
untracked files.

### 0n.2 Step 0: every number in the landscape PRD reproduced, none corrected

`_scratch/step0_landscape.py` (git-ignored) prints them all from one in-process build: 8 transformed
pages with the band lists, **8 chunks / 6 branches** (`R500`, `PGS SA.` and the four real ones),
**1 / 2 / 0 of 5** sentences quotable in raw / `de_column` / `-table`, the non-space multiset
identical on **every** page 2–9, **0** chunks holding `Participatory Guarantee Systems`, `six basic
elements`, `First-Party` or `Third-Party`, and the §5.7 simulation (exclusion alone → same 8 chunks,
same 6 branches). **Xpdf 4.00 is on this box**, so `-table` works; the box's `pdftotext` is the same
build the fixtures were made from.

### 0n.3 Step 1: the block, the guard, and one chunk per row

| File | What it now does |
|---|---|
| `knowledge/corpus.py` | parses `<!-- table` / `<!-- row: … -->` / `<!-- cell -->` / `<!-- row-divider: … -->` / `<!-- /table -->`; a cell is a **slice** of `section.text`; every malformed form raises with the line named |
| `knowledge/sections/__init__.py` | `TableCell`, `ParsedTableRow`, `ParsedTable`, and `ParsedSection.tables` |
| `knowledge/tables.py` | `chunks_for_parsed_section` (prose by the chunker, **one chunk per row** by the table code) and `row_chunk` (text = cells, heading_path and anchor from the row label, page = where the row starts) |
| `knowledge/ingest.py` | `chunks_for_sections` walks **sections** now, not chunks — a table section can no longer be substituted by a same-ref section elsewhere |
| `knowledge/tests/test_corpus_tables.py` | 29 tests: 19 refusals, 10 structure/chunk assertions |
| `knowledge/tests/test_landscape_table_block.py` | 13 tests over **p4's real rows**: five columns, 400-character cells, two cells the paper leaves empty, the seal's printed label, and *"Annual membership fee (paid by the PGS group to PGS SA): R500"* quotable from **one** chunk |

**The guard was written first and proved red** — that is the one instruction §0l's block insisted on.
`<!-- cell -->` outside a block, `<!-- cells -->` inside one, `cols:` missing, a block never closed, a
heading inside a block, a row with more cells than columns, a row that never closes, a divider with no
row beneath it: each fails, naming the line. The word-pin guard was broken deliberately
(`aggregate` → `agregate`) and went red before being restored.

**Three deviations from §3a, all recorded in the PRD's §12a:** the block closes **explicitly** with
`<!-- /table -->` (a table that ends by inference lets its last row own the prose after it); a
divider's **kind trails** its text, as §3a writes it; and **prose outside the rows is its own chunk**,
so §8's predicted **11** will be **12** unless a reviewer folds the lead-in in. The count gets
measured at step 2 — deleting text to hit a predicted number is the worse trade.

### 0n.4 Two findings that change the next session

- **The generator was emptying every draft but SAOSO's — and that is fixed (D75).** The generic
  branch set `keep = is_page_furniture`, a helper whose docstring begins *"Content the artefact must
  not carry"*: the predicate was inverted, so `--doc landscape` wrote five headings and the page
  stamps with no body, and `--doc opp` (P4) would have done the same. `body_filter(parser)` replaces
  it, five assertions in `tests/tools/test_build_corpus.py` (red first), and the landscape draft now
  carries **316 lines**. Two small steps still stand between step 2 and a reviewable diff: the BPP
  body-furniture rule (regenerating `bpp.md` differs by **57 lines** — the repeated *The Principle Of
  Health.* labels, blank-line collapse, one space from a dropped glyph) and a regeneration test that
  runs under `PDFTOTEXT_BIN=/usr/bin/true`. Land D72.7's page exclusion first, or the generated
  p4–8 is the frozen `de_column` soup rather than the printed grid.
- **There is no `landscape` `-table` page fixture.** `knowledge/tests/fixtures/pages/` carries
  `layout` and `raw` only, so §8's "each cell is a verbatim substring of `-table`" is not assertable
  yet; step 3 must add it via `scripts/extract_fixtures.py`, or the guard degrades to a presence check
  that Appendix 6a already proved insufficient.

### 0n.5 What was deliberately not done

No artefact for `landscape` or `opp` (P4/P5), no `TABLE_BANDS`, no front matter (D72.6), no reader
grid (D72.3/step 6), no re-ingest and therefore **no `relink_evidence` run** — nothing this session
wrote a `DocumentChunk`, so no evidence link was dropped and the live corpus is untouched. The two
pytest counts above are the whole of the evidence.


---
