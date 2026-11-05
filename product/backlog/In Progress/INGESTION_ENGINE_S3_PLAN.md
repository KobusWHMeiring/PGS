# S3 — the generator emits the table block (INGESTION_ENGINE_PRD.md §5, S3)

**Goal:** `scripts/build_corpus.py` writes `<!-- table … -->` blocks itself — structure from the
composite §3.14 chose, characters from the page's own text layer verified per cell — and every block
it writes records the extraction that produced it, so the gate judges the artefact without a flag.

**Architecture:** the arm proposes, the page supplies, the parser parses, the harness judges.
Three new units, one field, no migration:

| Unit | Responsibility |
|---|---|
| `knowledge/corpus_tables.py` | the block format grows one reviewed field, `extraction:` — `layout` / `raw` / `table`, validated, never guessed |
| `knowledge/table_proposals.py` | the arm's structure as committed data: a frozen dataclass per table, loaded by the document's **sha256** (not by a registry key) |
| `knowledge/proposals/<doc>.structure.json` | what the arm returned, written by the reducer, never hand-edited |
| `knowledge/proposals/<doc>.reviewed.json` | the block fields **no extractor produces** — `legend`, `layout`, `title`, `fee_label`, `branch` |
| `scripts/propose_tables.py` | build-time act: a cached Document AI response → a structure JSON. Imports no extractor; needs no key |
| `scripts/table_blocks.py` | the emitter: resolve every cell against the body's printed lines, slice the page's characters, emit or refuse **by name** |
| `scripts/build_corpus.py` | calls the emitter per section; a refusal is loud and leaves the prose |
| `knowledge/table_harness.py` | **R1** — a block that does not record its extraction is a violation |
| `scripts/check_tables.py` | reads each block's recorded mode; refuses on none, on two, or on a flag that disagrees |

**Tech stack:** Django 5.2, pytest, no new dependency, no network, no credential, no extractor in the
gate (requirement 10).

---

## The decision this plan implements, and what it deliberately does not

§3.14's composite is the owner's call and is not re-litigated here: **structure from Document AI Layout
Parser v1.6-pro, characters from the page's text layer verified per cell (R3), Docling for Appendix 7's
four columns, the harness for the verdict.**

Three things follow, and each is a scope boundary rather than a preference:

1. **The extraction mode is the datum nothing can guess.** `check_tables.py --pages-mode` is the last
   per-document fact on the command line; the landscape passes against `-table` and fails ten ways
   against `-layout`. S3 moves it onto the artefact, where the reviewer can see it and the gate cannot
   default it.
2. **The arm is build-time provenance, not a block field.** The proposal JSON records the processor id,
   the version and the cache path it was reduced from. A block field no consumer can check is a
   comment; `extraction:` is the one the gate must read.
3. **What the emitter cannot verify, it refuses — by name.** A cell whose characters are not a
   contiguous run of a printed line, a printed line inside the table no cell claims, an annotation
   inside the region: each is a refusal quoting the cell, not a guess. `--force` on a reviewed
   artefact is already refused by S1's `table_loss_refusal`; the emitter is the half that makes that
   refusal unnecessary.

**Measured before this plan was written** (`_scratch/s3_cellmatch.py`, 2026-11-05, on this box):

- The OPP's §2.3 fee table resolves **end to end**: 1 header row + 6 body rows, every cell a
  contiguous run of a printed line, resolved from the arm's `layout16pro__numeric_row` response against
  the body stream `build()` drafts — and the six rows are **byte-identical to the reviewed block**
  (14 cells, no differences).
- `python scripts/build_corpus.py --doc opp --stdout | diff - knowledge/corpus/opp.md` differs in
  **exactly the table block** and nowhere else (57 diff lines: the block out, the column soup in).
  So regeneration after S3 must be silent except for the one `extraction:` line — that is the
  regression, and it needs no PDF in the gate (the body is built from committed page fixtures).
- The landscape's page-4/5 table resolves **partially**: bullets (the arm's `listBlock` has no `•`),
  the merged fee box (the arm splits one printed box across two rows), the seal artwork (the arm reads
  the seal's own text) and the page-break row (the arm returns `Step 3` alone, then its cells) are
  four **declared** structures, and the de-columned stream puts page 4's table *before* its heading.
  That is S5's shape, not S3's: a proposal that needs a `span`, a `join` or an `art` declaration is
  refused by name here, and the paper in front of the reviewer is what adds it.

---

## File structure

**Create**

- `knowledge/table_proposals.py` — `ProposedTable` / `ProposedRow` / `ProposedProfile`, `proposals_for()`,
  `reviewed_for()`, and the refusals a malformed proposal earns.
- `knowledge/proposals/README.md` — what belongs here, what does not, and how each file is made.
- `knowledge/proposals/opp.structure.json` — the arm's grid for the OPP's §2.3 table.
- `knowledge/proposals/opp.reviewed.json` — the block fields no extractor produces (the legend).
- `scripts/propose_tables.py` — the reducer (cached response → structure JSON, with the banner).
- `scripts/table_blocks.py` — the emitter.
- `tests/tools/test_propose_tables.py` — the reducer's guards.
- `tests/tools/test_table_blocks.py` — the emitter's guards, one per requirement it can break.
- `knowledge/tests/test_table_proposals.py` — the loader's guards (sha256, spans, agreement with the
  reviewed file).
- `knowledge/tests/test_ingest_new_document.py` — the DoD's seam: a document the registry does not
  know, its rows chunked with column meaning.
- `tests/uat/` — **nothing.** S3 has no surface a human judges in a browser: every criterion below is
  a command with an output. A UAT item a grep can prove is not a UAT item (`writing-uat-tests`), and
  the operator's run is specified in *Operator verification* instead.

**Modify**

- `knowledge/sections/__init__.py` — `ParsedTable.extraction: str = ""`.
- `knowledge/corpus_tables.py` — `EXTRACTION_MODES`, `extraction` in `TABLE_FIELD`, validation, pass-through.
- `knowledge/table_harness.py` — R1, and `recorded_extraction()` for the document-level agreement.
- `scripts/check_tables.py` — the mode comes from the artefact; refusals for none / two / a conflicting flag.
- `scripts/corpus_pages.py` — `choose_pages()` split out of `pages_of()`, so a test can build the exact
  body stream from committed fixtures (`testing_hazards.md` §2.9's seam).
- `scripts/build_corpus.py` — call the emitter; print a refusal; no other change.
- `knowledge/corpus/opp.md` — regenerated: one added `extraction:` line and nothing else.
- `knowledge/corpus/landscape.md` — three blocks gain `extraction: table` (a two-word edit each).
- `tests/tools/test_build_corpus.py`, `tests/tools/test_check_tables.py`, `knowledge/tests/test_corpus_tables.py`,
  `knowledge/tests/test_table_harness.py` — the guards named below.
- `product/backlog/In Progress/INGESTION_ENGINE_PRD.md` — §5's S3 row, and the DoD note.
- `product/docs/context/testing_hazards.md` — whatever this session loses time to, appended the moment it does.
- `HANDOVER.md` + `product/docs/handover/SESSION_1p_2026-11-05_s3-the-generator-writes-the-block.md`.

**Budgets:** `scripts/table_blocks.py` must stay under 30 KB and under ~300 lines, or it splits by
responsibility (resolution vs. writing the block) the way `shape_arbitration_template.py` did.

---

## Task 1: The block format records the extraction it came from (requirement 1)

**Files:**
- Modify: `knowledge/corpus_tables.py`, `knowledge/sections/__init__.py`
- Test: `knowledge/tests/test_corpus_tables.py`

**Step 1: Write the failing tests**

```python
def test_a_block_records_the_extraction_its_cells_came_from():
    """Requirement 1's marker. The landscape passes against `-table` and fails ten ways
    against `-layout` (D80), so the pass is a fact the block has to carry."""
    text = artefact(page(TABLE.replace("cols: Key steps | Fee", "cols: Key steps | Fee\nextraction: table")))
    table = parse_blocks(text).sections[0].tables[0]
    assert table.extraction == "table"


def test_an_unknown_extraction_mode_is_an_error_not_a_silent_default():
    """A typo (`extraction: tbael`) must not read as "unknown pass, judge it anyway"."""
    with pytest.raises(CorpusFormatError, match="is not an extraction mode"):
        parse_blocks(artefact(page(TABLE.replace("cols:", "extraction: tbael\ncols:"))))


def test_a_block_with_no_extraction_field_parses_and_says_so():
    """Backwards compatible: the field is absent on every artefact written before S3, and
    `check_table` turns the empty string into R1 rather than this parser inventing one."""
    assert parse_blocks(artefact(page(TABLE))).sections[0].tables[0].extraction == ""
```

**Step 2: Run them — expected: FAIL** (`extraction` is an unknown header field today, so the
first raises `CorpusFormatError: ... not one of cols:, legend:, ...`).

Run: `python -m pytest knowledge/tests/test_corpus_tables.py -q --tb=line -x -k extraction`

**Step 3: Implement**

- `knowledge/corpus_tables.py`: `EXTRACTION_MODES = ("layout", "raw", "table")` beside
  `TABLE_LAYOUTS`, with a docstring saying why it lives here and not in `page_fixtures` (the
  library may not import a test module; `knowledge/tests/page_fixtures.py`'s `MODES` is asserted
  equal to it in Task 1's last test instead).
- add `extraction` to `TABLE_FIELD`'s alternation, and validate it in `read_header_line` the way
  `layout` is validated (same message shape: name the value, list the allowed ones).
- `read_header_line` passes the value through `self.fields`; `TableBlock.close()` is unchanged;
  `parsed_tables()` passes `extraction=raw["fields"].get("extraction", "")` into `ParsedTable`.
- `knowledge/sections/__init__.py`: `ParsedTable.extraction: str = ""` last, so every existing
  construction site keeps working.

**Step 4: Prove the guard can fail** — change `"extraction"` to `"extractio"` in `TABLE_FIELD`,
watch the first test go red, restore it.

**Step 5:** `python scripts/fast.sh --critical`

**Step 6: Commit** — `knowledge/`, the two test files, explicit paths only.

---

## Task 2: R1 — a block that does not record its extraction is a violation

**Files:** Modify `knowledge/table_harness.py`; Test `knowledge/tests/test_table_harness.py`.

**Step 1: Write the failing tests**

```python
def test_a_block_with_no_extraction_mode_is_an_r1_violation():
    """The marker the harness refuses to guess. `check_tables.py --pages-mode` defaulted it;
    from S3 the artefact carries it, and a block that does not is *named*, not defaulted."""
    report = check_document(parse_blocks(artefact_without_extraction()), pages=..., expected_rows=(2,))
    assert any(v.requirement == "R1" for v in report.violations)


def test_a_document_whose_blocks_disagree_about_the_pass_is_named():
    """Two passes are two fixture sets: R3 against `-layout` pages while the cells came from
    `-table` is a gate reporting on paper it did not read."""
    modes, violations = recorded_extraction(document_with_modes("table", "layout"))
    assert modes == {"table", "layout"} and violations and "table" in violations[0].detail
```

**Step 2: Run — FAIL.**

**Step 3: Implement**

- `REQUIREMENTS["R1"] = "the block records the extraction its cells came from"`, and in
  `check_table`, before the row loop: `if not table.extraction: Violation("R1", where, ...)`.
- `recorded_extraction(document) -> tuple[set[str], list[Violation]]` — the modes the document's
  blocks declare, and one R1 violation per *mode pair* that disagrees, naming both and the
  fixture sets they imply. `check_table` is not the place for a document-level fact.
- The module docstring's "What it checks" list gains R1 with the same "why" style as R2–R7.

**Step 4:** break it (drop the `if not table.extraction` branch), watch it red, restore.

**Step 5:** `python scripts/fast.sh --critical`

---

## Task 3: The gate reads the mode from the artefact (`check_tables.py`)

**Files:** Modify `scripts/check_tables.py`, `knowledge/corpus/opp.md`,
`knowledge/corpus/landscape.md`, `tests/tools/test_check_tables.py`.

**Step 1: Write the failing tests first** (in `tests/tools/test_check_tables.py`)

```python
# The mode column is gone: the artefact says it now, which is the whole point of S3.
CORPUS = {"landscape": "3,2,3", "opp": "6"}


def test_every_reviewed_artefact_passes_the_gate(capsys):  # unchanged body, no --pages-mode
    ...


def test_the_mode_is_read_from_the_artefact_not_from_a_flag(capsys):
    assert check_tables.main(["--doc", "landscape", "--rows", "3,2,3"]) == 0
    assert "table pages" in capsys.readouterr().out


def test_a_flag_that_disagrees_with_the_artefact_is_refused(capsys):
    code = check_tables.main(["--doc", "landscape", "--rows", "3,2,3", "--pages-mode", "layout"])
    captured = capsys.readouterr()
    assert code == 2 and "records" in captured.err and "table" in captured.err


def test_an_artefact_that_records_no_mode_is_refused_and_not_judged(tmp_path, monkeypatch, capsys):
    ...  # a tmp artefact with a block that has no `extraction:` → exit 2, "no block records"
```

**Step 2: Run — FAIL** (the first call still uses the default `--pages-mode layout`, so the
landscape fails R3 on ten cells).

**Step 3: Implement `resolve_mode(document, override)`** in `scripts/check_tables.py`:

- `modes, violations = recorded_extraction(document)`
- one mode → use it; print `({mode} pages, recorded on the artefact)`.
- no mode and no override → exit 2: "no block in this artefact records the extraction its cells came
  from … add `extraction: <mode>` (S3), or pass `--pages-mode` to judge a draft."
- more than one → exit 2, naming each mode and its fixture key.
- override present and different from the recorded mode → exit 2: "the artefact records `table` and
  `--pages-mode` says `layout`. One of the two is wrong; the artefact is the one a reviewer signed."
- `--pages-mode` stays in the help text as the draft-only escape, and its docstring paragraph
  ("S3's generator is where it stops being a command-line flag") is rewritten in the past tense.

**Step 4: The artefact edit** — `knowledge/corpus/opp.md`'s block gains `extraction: layout` after its
`legend:` line; `knowledge/corpus/landscape.md`'s three blocks gain `extraction: table`. Nothing else
in either file changes; `git diff` shows four added lines.

**Step 5:** `python scripts/check_tables.py --doc opp --rows 6` and
`python scripts/check_tables.py --doc landscape --rows 3,2,3` — both `ok`, 0 violations.

**Step 6:** break the guard (delete `extraction: table` from one landscape block), watch
`test_the_mode_is_read_from_the_artefact_not_from_a_flag` go red, restore.

**Step 7:** `python scripts/fast.sh --critical`

---
## Task 4: The body stream becomes testable without an extractor

**Why this task exists.** The gate runs with `PDFTOTEXT_BIN=/usr/bin/true` (`testing_hazards.md`
§2.9), so no test may call `build()`. But the emitter's input is `build()`'s body stream, and the
regression that matters is "the emitter reproduces the reviewed fee table". `pages_of()` is the only
part of that path that needs a PDF; the *choice* between the two renderings is pure, and it is where
the artefact's `raw_pages:` header comes from.

**Files:** Modify `scripts/corpus_pages.py`; Test `tests/tools/test_build_corpus.py`.

**Step 1: Write the failing tests**

```python
def test_the_raw_rendering_is_chosen_only_when_its_word_multiset_matches():
    laid = ["a b c", "d e"]
    raw = ["abc", "e d"]
    chosen, used = corpus_pages.choose_pages(laid, raw)
    assert chosen == ["a b c", "d e"] and used == ()      # neither repairs to a match


def test_a_page_chosen_from_raw_is_named_in_the_header_field():
    chosen, used = corpus_pages.choose_pages(["Sourced locally"], ["Sourcedlocally"])
    assert chosen == ["Sourced locally"] and used == (1,)


def test_the_committed_fixtures_reproduce_the_artefacts_raw_pages():
    """`raw_pages:` in the artefact header is the generator's own record of which pages it took
    from the content stream. If this drifts, every regenerated artefact drifts with it."""
    laid = reflow_pages(apply_layout(page_fixtures.pages("opp", "layout")))[0]
    raw = reflow_pages(page_fixtures.pages("opp", "raw"))[0]
    _chosen, used = corpus_pages.choose_pages(laid, raw)
    assert ",".join(map(str, used)) == "1,2,3,4,5,6,8,9,10,12,13,14,15"
```

**Step 2: Run — FAIL** (`choose_pages` does not exist).

**Step 3: Implement** — lift `pages_of`'s loop into `choose_pages(laid, raw) -> (list[str], tuple[int, ...])`
with the "raw is used only where its word multiset equals the geometry page's" docstring moved with
it; `pages_of` keeps extraction, `apply_layout`, `reflow_pages` and `stamps`, then delegates. Keep
`len(raw) != len(laid)`'s fallback inside `choose_pages` (it is the same decision).

**Step 4:** `python scripts/fast.sh --critical`; then
`python scripts/build_corpus.py --doc opp --stdout >/dev/null` still exits 0.

---

## Task 5: The arm's structure as committed data

**Files:**
- Create: `knowledge/table_proposals.py`, `knowledge/proposals/README.md`,
  `knowledge/proposals/opp.structure.json`, `knowledge/proposals/opp.reviewed.json`
- Test: `knowledge/tests/test_table_proposals.py`

**Step 1: Write the failing tests**

```python
OPP_SHA = "…"  # read from knowledge/corpus/opp.md's header at implementation time


def test_the_opp_proposal_is_found_by_the_documents_sha256_and_not_by_its_key():
    """Retargeting is the reason: a new standard's proposal is found by the bytes it describes,
    so no registry entry, no migration and no `CORPUS_DOCUMENTS` edit stands in the way."""
    tables = proposals_for(OPP_SHA)
    assert len(tables) == 1
    assert tables[0].columns == (
        "Annual farm turnover (gross sales)",
        "Initial certification fee (R)",
        "Renewal fee (R)",
    )
    assert len(tables[0].rows) == 6 and tables[0].extraction == "layout"


def test_the_proposal_records_the_arm_that_proposed_it():
    table = proposals_for(OPP_SHA)[0]
    assert table.structure == "documentai-layout-v1.6-pro"
    assert "pretrained-layout-parser-v1.6-pro" in table.processor


def test_a_row_whose_cell_count_disagrees_with_the_columns_is_refused():
    ...  # a tmp proposals dir, one row short → CorpusFormatError naming the row


def test_a_reviewed_entry_that_names_no_table_is_refused():
    ...  # opp.reviewed.json with three tables → refused, "1 table, the review names 3"


def test_two_structures_claiming_one_document_are_refused():
    ...  # a second file with the same sha256 → error naming both files
```

**Step 2: Run — FAIL.**

**Step 3: Implement**

- Frozen dataclasses `ProposedRow(cells)`, `ProposedTable(index, pdf_pages, columns, rows,
  extraction, structure, processor, profile)`, `ProposedProfile(legend, layout, titles, fee_labels, branch)`.
- `proposals_for(sha256, directory=None) -> tuple[ProposedTable, ...]`: scan
  `knowledge/proposals/*.structure.json`, match on the `sha256` field (**not** the filename), merge
  the sibling `<stem>.reviewed.json` by table index, validate (extraction in `EXTRACTION_MODES`,
  rectangular rows, non-empty rows/pages, review length), raise `ProposalError` (a `ValueError`
  subclass) naming the file and the row. `directory` exists for the tests and defaults to the
  committed one.
- The two JSON files. `opp.structure.json` is **written by Task 6's reducer**, never by hand; the
  JSON in this task's commit is whatever the reducer produced from the cached response.
- `README.md`: what belongs here (an arm's structure, a review's block fields), what does not (cells
  anyone typed), and the command that regenerates each file.

**Step 4:** `python scripts/fast.sh --critical`

---

## Task 6: The reducer — a cached arm response becomes a proposal

**Files:** Create `scripts/propose_tables.py`; Test `tests/tools/test_propose_tables.py`.

**Step 1: Write the failing tests**

```python
def test_the_layout_parsers_grid_becomes_a_proposal(tmp_path):
    """The arm's shape, not ours: headerRows then bodyRows, cells as `blocks[].textBlock.text`,
    no `document.text` (reading it the Form Parser's way scored this arm 0 of 8 — §3.9)."""
    response = {"documentLayout": {"blocks": [{"tableBlock": {
        "headerRows": [{"cells": [{"blocks": [{"textBlock": {"text": "A"}}]}]}],
        "bodyRows": [{"cells": [{"blocks": [{"textBlock": {"text": "1"}}]}]}],
    }}]}}
    table = reducer.structure_from(response, pages=(2,))[0]
    assert table["columns"] == ["A"] and table["rows"] == [{"cells": ["1"]}]


def test_a_response_with_no_table_is_refused_rather_than_written_empty(tmp_path):
    assert reducer.main(["--response", str(no_table), "--json", str(out), ...]) == 2
    assert not out.exists() and "no table" in capsys.readouterr().err


def test_the_written_proposal_carries_the_processor_and_the_cache_it_came_from(tmp_path):
    ...
    assert data["processor"] == "…@pretrained-layout-parser-v1.6-pro-2025-12-01"
    assert data["reduced_from"].endswith("layout16pro__numeric_row.json")
```

**Step 2: Run — FAIL.**

**Step 3: Implement**

```
python scripts/propose_tables.py \
    --response _scratch/adc/responses/layout16pro__numeric_row.json \
    --processor 68e47c3bc90cc6ab@pretrained-layout-parser-v1.6-pro-2025-12-01 \
    --project 803140233794 --shape numeric_row --doc opp \
    --json knowledge/proposals/opp.structure.json
```

- `--shape` supplies the PDF pages (via `shape_fixtures.SHAPES`) and `--doc` the PDF whose sha256 is
  recorded. No credential, no network, no rasteriser: it reads a cached response and writes JSON.
  The module docstring says so, in `check_extraction.py`'s voice.
- `structure_from(document, pages)` reuses `scripts.eval_documentai`'s `tables_from` (one reader of
  the arm's block tree, not two) and refuses any cell with `rowSpan`/`colSpan` != 1 by name — a
  merged cell needs a declaration nobody has written yet (S5).
- The banner written into the JSON: `doc_key`, `sha256`, `structure`, `processor`, `project`,
  `captured`, `reduced_from`, `shape`.
- A pre-existing `reviewed` sibling is **not** touched (it is a human's file).

**Step 4: Run it for real** — commit `knowledge/proposals/opp.structure.json` as produced.

**Step 5:** `python scripts/fast.sh --critical`

---
## Task 7: The emitter — the arm's structure, the page's characters, a refusal by name

**Files:** Create `scripts/table_blocks.py`; Test `tests/tools/test_table_blocks.py`.

**The rule the module is built around**, and it is three sentences long:

1. A cell's characters are **a run of the body's printed lines** — exact first, then with every space
   dropped (letter-spacing is the paper's, not a licence), and the *page's* characters are what get
   written. The arm proposes the boundary; it never supplies a character.
2. The cells resolve **in order inside one cursor that only moves forward**, so a cell cannot stitch a
   line from above the table into a row, and a table whose cells are printed out of order is refused
   rather than silently re-ordered.
3. Everything the table's region holds must be claimed by a cell. A printed line nobody claims is a
   line the corpus loses, and `--force` would then have deleted text while every character guard
   stayed green (`testing_hazards.md` §3.25).

**API**

```python
@dataclass(frozen=True)
class Emitted:
    index: int
    columns: tuple[str, ...]
    rows: int

@dataclass(frozen=True)
class Refusal:
    index: int
    where: str        # "row 3, column 2", or "table"
    detail: str
    def __str__(self) -> str: ...   # "proposal 1, row 3, column 2: ..."

def emit(proposals, body: Sequence[str]) -> tuple[list[str], tuple[Emitted, ...], tuple[Refusal, ...]]
```

`emit` is a pure function over strings: no PDF, no extractor, no Django. It returns the body with
each resolved table replaced by its block, in place, and leaves the prose of every refused table
exactly as it arrived.

**Step 1: Write the failing tests** — one per rule above, on a synthetic body (no fixture needed):

```python
BODY = [
    "<!-- page: 2 printed: 2 -->",
    "Annual farm turnover (gross sales) Initial certification fee (R) Renewal fee (R)",
    "Below R 250,000 1,500 900",
    "Above R 5,000,000 8,000 8,000",
    "● Fees are per farm assessment visit.",
]

def proposal(rows, columns=FEE_COLUMNS, **profile):
    return ProposedTable(index=0, pdf_pages=(2,), columns=columns,
                         rows=tuple(ProposedRow(tuple(r)) for r in rows),
                         extraction="layout", structure="documentai-layout-v1.6-pro",
                         processor="x@y", profile=ProposedProfile(**profile))


def test_a_cell_is_the_pages_characters_not_the_arms_spelling():
    """R3's rule read backwards: the arm may propose `bovine` for a page that prints `b o v i n e`,
    and what reaches the artefact is the page's run, because that is what the harness can locate."""
    body = ["<!-- page: 2 printed: 2 -->", "b o v i n e   Cattle", "1,500  900"]
    lines, emitted, refused = emit([proposal([["bovine", "Cattle"]])], body)
    assert not refused
    assert "b o v i n e" in lines        # the arm's characters are not what is written


def test_a_cell_the_page_does_not_print_is_refused_and_its_prose_is_left_alone():
    body = ["<!-- page: 2 printed: 2 -->", "70oC for 30 minutes"]
    lines, emitted, refused = emit([proposal([["70°C"]])], body)
    assert lines == body
    assert refused[0].where == "row 1, column 1" and "70°C" in refused[0].detail


def test_a_printed_line_inside_the_table_that_no_cell_claims_is_refused():
    """The row the proposal skipped: the page prints three bands and the arm returned two."""
    ...   # refusal names the line; body unchanged


def test_an_empty_cell_is_recorded_empty_and_never_filled():
    lines, *_ = emit([proposal([["Below R 250,000", "", "900"]])], BODY)
    parsed = first_table(lines)
    assert [cell.text for cell in parsed.rows[0].cells] == ["Below R 250,000", "", "900"]


def test_a_row_is_labelled_from_the_first_printed_line_of_its_first_cell():
    lines, *_ = emit([proposal([["Section A\n\n1,500", "900"]])], BODY_WITH_TWO_COLUMNS)
    assert "<!-- row: Section A -->" in lines


def test_a_row_that_starts_on_a_new_page_carries_its_page_marker():
    """D72.5: a row has one page, and the paper prints this row's first cell on the next page."""
    ...   # <!-- page: 3 printed: 3 --> between rows; parse and assert rows[1].page == 3


def test_the_emitted_block_records_the_extraction_it_was_emitted_from():
    lines, *_ = emit([proposal([...])], BODY)
    assert "extraction: layout" in lines
    assert first_table(lines).extraction == "layout"


def test_the_reviewed_fields_no_extractor_produces_travel_into_the_header():
    lines, *_ = emit([proposal([...], legend="One row per band.", layout="grid")], BODY)
    assert "legend: One row per band." in lines and "layout: grid" in lines


def test_a_sub_clause_marker_inside_the_region_is_refused():
    """The parser raises on `<!-- sub: … -->` inside a block; the emitter must not write it."""
    ...


def test_the_emitted_block_passes_the_harness():
    """R2-R7 on the emitted block, with the page text supplied — the gate's own judge, on the
    generator's own output, with no PDF anywhere near it."""
    lines, *_ = emit([proposal([...])], BODY)
    report = check_document(artefact_of(lines), pages=["..."], expected_rows=(2,), expected_tables=1)
    assert report.ok, report.lines()
```

**Step 2: Run — FAIL.**

**Step 3: Implement** in one file, ~250 lines, two responsibilities kept apart by function:
*resolution* (`resolve`, `slice_run`, `index_map` — the same space-free coordinate trick
`table_reads.resolve` uses, re-implemented here rather than imported because `scripts/table_reads.py`
is an evaluation instrument over `ShapeCase`s) and *writing* (`block_lines`, `profile_lines`).

The header is written in the artefact's existing order — `cols:`, then the reviewed fields, then
`extraction:` last — so the diff against a reviewed block is one added line and nothing else.

**Step 4: prove each guard can fail** — delete the "unclaimed line" check and watch its test go red;
delete the despaced fallback and watch the first; restore both.

**Step 5:** `python scripts/fast.sh --critical`; `wc -c scripts/table_blocks.py` under 30 000.

---

## Task 8: `build_corpus.py` emits the block (and says so when it cannot)

**Files:** Modify `scripts/build_corpus.py`; Test `tests/tools/test_table_blocks.py` (the
fixture-built reproduction) and `tests/tools/test_build_corpus.py` (the warning).

**Step 1: Write the failing tests**

```python
def test_the_generator_reproduces_the_reviewed_fee_table_from_the_committed_pages():
    """The first regression test of S3, and it needs no PDF: the body is built from
    `page_fixtures` exactly as `build()` builds it, the proposal is the committed one, and the
    block that comes out is the block a reviewer signed — byte for byte, plus the new field."""
    body = [line for _page, line in flatten(choose_pages(laid, raw))[0]]
    lines, emitted, refused = table_blocks.emit(proposals_for(sha256_of(OPP_PDF)), body)
    assert not refused and len(emitted) == 1
    assert block_text(lines) == block_text(ARTEFACT) + "extraction: layout\n"
    # and the prose either side of the block is untouched
    assert lines[:first_line] == body[:first_line]


def test_a_table_that_cannot_be_emitted_is_named_on_stderr_and_not_dropped(capsys, ...):
    """A document whose proposal does not resolve: the draft keeps the page's prose and the
    operator is told which cell failed. Silence here is `--force` deleting text."""
    ...
    assert "was not emitted" in capsys.readouterr().err
```

**Step 2: Run — FAIL.**

**Step 3: Implement** — in `build()`: compute `digest = sha256_of(pdf_path)` once (it is already
computed for the header), and after `insert_sub_refs`:

```python
body, emitted, refused = table_blocks.emit(proposals_for(digest), body)
for refusal in refused:
    print(f"{doc_key}: {refusal}; the draft keeps the page's prose for it", file=sys.stderr)
```

`GENERATOR` stays `v2`: the field is additive, and a bump would claim v2's column-soup draft for the
landscape was produced by a generator that can now emit blocks it cannot emit there. That reasoning
goes in the module docstring (rule 6's paragraph grows a rule 7).

**Step 4: The operator's act, once, by hand**

```bash
python scripts/build_corpus.py --doc opp --force
git diff --stat knowledge/corpus/opp.md       # 1 insertion, 0 deletions
python scripts/build_corpus.py --doc landscape --stdout | git diff --no-index - knowledge/corpus/landscape.md | head -20
```

The first must show exactly the `extraction: layout` line. The second must still show the column
soup *and* print four refusals naming the landscape's cells — S5's work, written down, not silently
dropped.

**Step 5:** `python scripts/fast.sh --critical`

**Step 6: Commit.**

---

## Task 9: The DoD's seam — a document the registry has never heard of

**Files:** Create `knowledge/tests/test_ingest_new_document.py`.

**What this can and cannot prove, said plainly.** The PRD's first success criterion is *"a document
not in `CORPUS_DOCUMENTS` can be ingested and its tables chunked with column meaning, with no
hand-authored table block."* The composite's structure arm is Document AI, and **no arm response
exists for any document outside the eight shape pages** — producing one means re-running the arm,
which this slice may not do. So this test proves the *seam*: the bytes are the OPP's, the registry
entry is one the registry does not have, and nothing in the path knows either fact.

**Step 1: Write the failing test**

```python
def test_a_document_the_registry_does_not_know_is_chunked_with_column_meaning(db):
    assert "opp-newstandard" not in CORPUS_DOCUMENTS
    artefact = tmp_path / "newstandard.md"
    artefact.write_text(
        header(sha256=sha256_of(OPP_PDF), doc_key="opp-newstandard") + emitted_section_text(),
        encoding="utf-8",
    )
    report = ingest_standard(
        pdf_path=OPP_PDF,
        standard_set=StandardSet.objects.create(code="pgs", label="PGS"),
        doc_key="opp-newstandard",
        kind="standard",
        title="A standard the registry does not know",
        section_scheme="heading",
        corpus_path=artefact,
        embed=False,
    )
    chunk = DocumentChunk.objects.get(
        document_id=report.document_id, heading_path__contains="Above R 5,000,000"
    )
    assert "Initial certification fee (R): 8,000" in chunk.embedding_text
    assert "<!-- table" not in chunk.text          # the annotations never become text
```

**Step 2: Run — FAIL** (nothing emits the block yet, so the section is one prose chunk).

**Step 3: Implement** the helpers (fixture-built body → emitted lines → artefact text). No production
code should be needed; if it is, that is the finding, and it goes in the handover.

**Step 4:** `python scripts/fast.sh --critical`

---

## Task 10: Close the loop

- [ ] `python scripts/check_tables.py --doc opp --rows 6` → `ok — 1 tables, 6 rows, 0 violations`
- [ ] `python scripts/check_tables.py --doc landscape --rows 3,2,3` → `ok`
- [ ] `python -m pytest knowledge/tests/test_ingestion_shapes.py -q` → the **eight strict-xfail
      markers unchanged** (`git diff` on that file: empty)
- [ ] `DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify bash scripts/verify.sh` — once, cold
- [ ] `scripts/fast.sh --critical` warm timing recorded; add `tests/tools/test_check_tables.py` to
      `CRITICAL_TESTS` **only if** the lane stays under ~30 s, and record the measurement in the commit
- [ ] `product/backlog/In Progress/INGESTION_ENGINE_PRD.md`: §5's S3 row → done, with S5 next; §6's
      first criterion annotated with what Task 9 proves and what it does not
- [ ] `product/docs/context/testing_hazards.md`: every entry this session earned, appended the moment
      it did
- [ ] `product/docs/handover/SESSION_1p_2026-11-05_s3-the-generator-writes-the-block.md` + one index
      line; `HANDOVER.md`'s START HERE rewritten as state (≤ 250 lines, guarded)
- [ ] `python product/backlog.py --write`
- [ ] commit with **explicit paths** (never `git add -A` — another session's copy-deck work is in this
      tree); `git push`; `git rev-list --count origin/main..HEAD` answered by the command, not by prose

---

## Left open, deliberately, and where each one goes

| Open | Why not here | Closes in |
|---|---|---|
| The landscape's four declared structures (bullets, the merged fee box, seal artwork, the page-break row) and its page-order problem | Each needs a declaration the harness cannot infer, and the de-columned page puts the table before its heading | S5 |
| Appendix 6a's 20 rows and Appendix 7's four columns | S5's stated scope; Docling's role is recorded in the proposal banner when it lands | S5 |
| A proposal for a document outside the eight shape pages | Needs an arm run; this slice may not re-open the key | the first real ingestion (`scripts/propose_tables.py` is the command) |
| `DocumentChunk` carrying the extraction mode itself | Requirement 1 is satisfied by the block that produced the row, and a chunk field is a migration for a marker | only if retrieval ever needs it |
