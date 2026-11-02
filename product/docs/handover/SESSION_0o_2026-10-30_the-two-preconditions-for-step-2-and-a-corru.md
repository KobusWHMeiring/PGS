<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0o. 2026-10-30 (session 2) — the two preconditions for step 2, and a corruption in the review path

**State: green, committed, nothing re-ingested.** `fast.sh` **1393 passed / 1 skipped in 29 s**
(warm) and `verify.sh` **1407 passed / 1 skipped in 46.2 s** (`--create-db`; quote both, and the
range — `testing_hazards.md` §3.17). No landscape artefact, no `TABLE_BANDS`, no `--force`, no
`relink_evidence`: no `DocumentChunk` was written, so the live corpus is untouched and **no evidence
link was dropped**.

### 0o.1 Task 3, and it was two one-liners plus an exclusion

| Landed | Evidence |
|---|---|
| `landscape` `-table` fixture | `PAGE_MODES` in `scripts/extract_fixtures.py`; `pages/landscape.table.txt`, 10 pages, 30 494 bytes. **Every other page fixture byte-identical** (md5 before/after), so this is not a re-baseline |
| D72.7's exclusion | `PAGE_LAYOUT_EXCLUSIONS["landscape"]`, pdf 4–8, one entry per page because the gutters differ page to page. `apply_layout` now changes **{2, 3, 9}** and `EXPECTED_TRANSFORMED_PAGES` says so |
| a cell guard that means something | `test_landscape_table_block.py`: per-printed-**line** runs, plus order. 14 tests, proved red four ways |

**§8 requirement 3 was false as written** and the fixture is what proved it. A *cell* is not a
substring of `-table` output — `-table` renders row-lines, so one output line carries the current line
of every column at once and the Step 1 description is interrupted twice. Each cell **line** is a run of
one printed line, and a cell's lines appear in order; that is the guard, and it catches all four
breaks including the two the existing word-presence test passes (a line swap and a reversal).

### 0o.2 Task 2 found the review path corrupting the artefact

Making `bpp.md` regenerable took the diff from **57 lines to 32, every one of them whitespace** — the
non-space character multiset and the sequence of non-blank lines are identical. Three findings, and the
first is the one to read:

1. **`apply_review` was mangling page 4's most-quoted passage.** The footnote-2 correction was
   `kind="move"`, and a move is not a text substitution: applying it *deleted* `must be preferably
   composted` and reprinted `land available will not be allowed.` at the foot of page 4. Nothing
   caught it because the traceability test compares `flat()` strings and `flat` joins lines. Now a lift
   plus a place, and `apply_review` keeps a replacement's own line breaks. `MAX_EDITS` 7 → 8 with the
   reason recorded (one review decision, two mechanical edits).
2. **`apply_review`'s multiplicity guard was dead** — `subn(..., count=1)` reports one substitution
   whenever the pattern matches at all, so "fails when an edit matches more than once" could never
   fire. Fixed red-first. The function had **no test at all** before this session.
3. **The furniture had to be data.** The inferential rule was measured and it destroys SAOSO
   (`General Principle` on 26 pages, `Requirements:` on 25, `South African specific` on 18 — all
   content; and one poultry derogation is printed verbatim on pages 45–47). So `BODY_FURNITURE` names
   the BPP's four labels, and the filter keeps the block on the page that first carries it. Also: PUA
   codepoints stripped, and a page whose only kept line is blank gets no marker.

**Residual, not chased:** the 32 whitespace lines. Two causes, neither a generator defect — the BPP's
reviewer removed blank lines before page markers and SAOSO's kept them (so a rule would have to be per
document), and the artefact keeps one leading space where it dropped a glyph.

### 0o.3 A window trap that cost ten minutes

`scripts/build_corpus.py --stdout` dies on this box with `UnicodeEncodeError` on `\uf06e` — and it is
`--file` that works, so the crash is in the console, not the artefact. `PYTHONIOENCODING=utf-8` fixes it;
`--stdout` also emits **CRLF** where the writer emits LF, so diff against an artefact with
`--strip-trailing-cr` or the real 32 lines hide inside 583 (`testing_hazards.md` §3.21, extended).

### 0o.4 How it was committed, and the one thing that must still travel with the rows

Two attributed commits, split by concern rather than by file count, because `corpus.py` and
`build_corpus.py` carry both halves of §0o.2 and splitting a file across commits is not something a
reviewer can read:

- `bfe64ed` — the review path and the furniture: `knowledge/corpus.py`, `scripts/build_corpus.py`,
  `tests/tools/test_build_corpus.py`, `knowledge/tests/test_corpus_bpp.py`, and the §3.21 addendum.
- `d1cd8a2` — the landscape's fixture and exclusion: `scripts/extract_fixtures.py`, the new
  `pages/landscape.table.txt` + manifest entry, `knowledge/columns.py`, and the three test files.
- the documentation commit after them: the two PRDs, the spec's D72.7 row, this file, the index.

**D72.7 still governs the exclusion.** It is inert until something re-ingests — no `DocumentChunk` was
written this session — so committing it now costs nothing, and it must not be *deployed* as a "corpus
fix": the live box's `landscape` chunks are built from whatever ran on 2026-10-22, and `corpus_check`
cannot see them (`todo.md`, `drift.py` short-circuits at `no artefact`). The exclusion reaches the box
only with the rows and the one re-ingest, in step 2. Until then the only way it can cause trouble is
if somebody runs `corpus_refresh` and not `relink_evidence`.

---
