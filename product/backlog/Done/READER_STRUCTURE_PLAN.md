# The reader's structure — Implementation Plan

**Status:** **Done** — all ten tasks built 2026-10-27 (gate 1139 passed / 1 skipped, Playwright 58). **UAT SIGNED 2026-10-28** — `tests/uat/concordance_uat.md` carries eleven **PASS** results, signed by Kobus (Product) against commit `4e02d71`; applied by `scripts/uat_signoff.py`. The PGS administrator, committee reviewer and consumer-member seats are still empty (D4). What differs from the plan — one corrected
number, six changed signatures and three findings — is in **§12**, at the end.
**Read first:** §12's corrected glossary count and §0.1's numbers; everything else held.
**The precondition was satisfied** before Task 1: the four answers are recorded in the PRD (§2
D70.5–D70.7, §10), the spec's D70 row is updated, and the PRD was moved to `ready/`.
**Owner:** Kobus Meiring (Product) · Build
**PRD:** `product/backlog/ready/READER_STRUCTURE_PRD.md` (decisions §2, findings §1, answers §10)
**Decision record:** `PGS_PLATFORM_SPEC.md` §18.3 **D70** (D70.1–D70.7)
**UAT:** `tests/uat/concordance_uat.md` — **Scenarios 9–11, drafted in Task 0, before any code**
**Reference:** `build_principles.md` §I, §II, §V, §VIII · `testing_hazards.md` §1.32, §1.33, §2.7
**Baseline commit:** `5ac5128` (tree clean, 46 ahead of `origin/main`, gate 1004/1 skipped)

````yaml
plan_meta:
  feature: reader-structure
  prd: product/backlog/ready/READER_STRUCTURE_PRD.md
  format: contract            # interface + assertions; no bodies, no template markup
  tasks: 10                   # Task 0 (UAT) .. Task 9 (close)
  prewritten_code_lines: 0
  tdd_split: true             # test: commit, then feat: commit, per task
  uat: tests/uat/concordance_uat.md
````

*This repo has no `plan_metrics.py`, so the block above is the record rather than a tool's input. If
that tool lands, these are the fields it reads.*

---

**Goal:** `/documents/<code>/read/` renders Appendix 2 as the table the paper prints — parts,
qualifiers, column headers, each substance its own entry, silence marked as silence — and every
reference the document makes to itself (a section, an appendix, a defined term) becomes a link that
lands on what the reference names.

**Architecture:** three **derivations**, all display-only, all in `knowledge/` so `core` stays thin
and `knowledge` stays free of URLs. `knowledge/tables.py` gains reviewed structure data beside
`TABLE_ROWS` (a divider is quoted text with a position; a legend is one reviewed sentence).
`knowledge/passages.py` gains one block kind and one function — `RowHeading` and `row_blocks()` —
leaving `passage_blocks()` untouched. `knowledge/references.py` (new) derives an index from the
concordance and the printed TOC, and turns a string into `Segment`s; `knowledge/glossary.py` (new)
derives the term list from the glossary branch and gives each definition an `id`.
`core/services/_documents.py` assembles: rows instead of passages for a curated branch, segments
instead of text for a paragraph, one locator per run. No migration, no re-ingest, no chunk, no
anchor, no retrieval, no citation-audit change.

**Tech stack:** Django 5.2, server-rendered templates, one stylesheet, zero JavaScript.

---

## 0. How to execute

- **TDD, always, in two commits.** Step 1 writes the failing test, Step 5 commits it (`test(rN): …`),
  Step 6 writes the body and commits that (`feat(rN): …`). Both commits carry `Plan-Task: N`. A test
  that has never failed is decoration (`testing_hazards.md` §0).
- **Contract mode.** The plan gives the **interface** and the **assertions**, never the body, never
  markup, never CSS. If a step's expectation is wrong, the step is wrong — measure the corpus rather
  than pasting the plan's guess.
- **Every guard is proven by breaking it.** Before a task is committed, break the thing it guards,
  watch the named test go red, restore. Record the one-liner in the commit body.
- **Schema before logic:** there is no schema. Tasks 1–2 are data and pure functions; Task 3 is the
  first one a browser can see.
- **Verify against the real corpus for every number the PRD measured** (`testing_hazards.md` §1.33:
  the committed fixtures are not the deployed corpus). The corpus-level guard in Tasks 2, 4 and 6
  ingests the shipped SAOSO from the committed pages (`stub_ingest_extraction`), about 6 s, **once**.

### 0.1 The numbers this plan inherits (measured 2026-10-27, `scripts/probe_reader_structure.py`)

| Fact | Number |
|---|---:|
| Appendix 2 reviewed rows / with no printed condition | **30 / 19** |
| Appendix 2 printed pages (reader `page`) | 76, 77, 78 |
| Locator lines today → printed once per run, SAOSO | 319 → **273** (−46) |
| … OPP / landscape / BPP | 30→28, 8→6, 9→**4** (−2, −2, −5) |
| … all four documents | 366 → **311** (−55) |
| Section references printed in SAOSO (10) → links | 9 → `S1`×1, `S5`×3, `S4`×2, `S2`×1, `S22`×2 |
| … Part A (`Section A – 2.3`) | **1**, and it must go to `#not-in-corpus`, never `S2` |
| Appendix mentions (29) → links | **20**; 8 × `Appendix 4` and 1 × bare `Appendix 6` stay text |
| Links total / plain mentions total | **30 / 9** |
| BPP (`Appendix 5`) and landscape (`Appendix 9`) | 1 mention each, **0 links** (negative control) |
| `Term` blocks in `S1` / distinct headwords | 78 / **71** (the 7 repeats are chunk overlap) |
| References to the branch they are printed in, today | **0** (rule is synthetic-tested only) |

### 0.2 The file map (and the 30 KB cap)

| File | Action | Bytes now |
|---|---|---:|
| `knowledge/tables.py` | modify — structure data + `structure_for()` | 13 044 |
| `knowledge/passages.py` | modify — `RowHeading`, `row_blocks()` | 18 395 |
| `knowledge/references.py` | **create** — index, `Segment`, `segments_for()` | — |
| `knowledge/glossary.py` | **create** — `GLOSSARY_BRANCH`, `REJECTED`, entries, anchors | — |
| `knowledge/reading.py` | modify — `printed_locators()` | 307 lines |
| `core/services/_documents.py` | modify — assembly (rows, segments, locators) | 21 020 |
| `core/templates/public/_passage_blocks.html` | modify — `row` block, segments, definition `id` | 1 263 |
| `core/templates/public/document_reader.html` | modify — caption/legend, dividers, label, note | 7 932 |
| `core/static/css/reader.css` | modify — row weight, divider, caption, label | 13 339 |
| `scripts/probe_reader_structure.py` | modify — measure the shipped data, not a copy | 365 lines |
| `knowledge/tests/test_table_sections.py` | **create** | — |
| `knowledge/tests/test_row_blocks.py` | **create** | — |
| `knowledge/tests/test_references.py` | **create** | — |
| `knowledge/tests/test_glossary.py` | **create** | — |
| `core/tests/test_document_reader.py` | extend | — |
| `tests/uat/concordance_uat.md` | extend — Scenarios 9–11 | — |

`_documents.py` ends around **23 KB** (the cap is 30 720 B). If it does not, the table assembly moves
to `knowledge/tables.py` as a pure function before anything is split into `_reader.py` — `_documents`
is already the right name for what it does.

### 0.3 What is *not* in this plan

Non-goals carry over from the PRD §6 verbatim: no post-processing of a clause to produce blocks;
`passage_blocks()` keeps its behaviour exactly; `S1` stays one branch and "not in corpus" is never a
branch.

---

## Task 0: The UAT is drafted before the code

**Files:**
- Modify: `tests/uat/concordance_uat.md`
- Verify with: `scripts/uat_parse.py` (the format gate — it refuses a scenario with no `Judgement:`)

**Contract.** Three scenarios appended after Scenario 8 and before `## Sign-off`, each carrying every
labelled field the parser requires (`**Setup:**`, `**Action:**`, `**Expected:**`, `**Judgement:**`) —
Scenario 9 is the table, 10 the references, 11 the glossary. The `## Automated coverage (NOT UAT)`
table gains these rows, because each is asserted by a task below and must **not** be shown to the
reviewer:

| Row to add | Task that asserts it |
|---|---|
| 19 empty conditions print the muted label, and the legend is the page's own claim | 1, 3 |
| Each row reads as an entry: substance heading, then its condition paragraphs | 2, 3 |
| `Section A – 2.3` links to the missing note; bare `Appendix 4` and bare `Appendix 6` are not links | 4, 5 |
| A reference opens in a new tab and announces it; the BPP and the landscape render none | 5 |
| One locator per run, and every passage keeps its `id` (366 → 311) | 6 |
| A definition link lands on the definition, not the branch's top | 7 |

Judgement clauses stay judgement: Scenario 9 asks whether a row with no condition reads as *the
paper's silence rather than as a permission*; Scenario 10 whether each link lands on what the sentence
meant; Scenario 11 whether the page still reads normally with the links in it. A scenario whose
`Judgement:` a query could answer belongs in the table above instead.

**One correction to PRD §9's Scenario 10 wording, measured before writing it.** PRD §9 says "follow
`See Section B – Appendix 6` from Appendix 2" — the sentence is real, but `Section B –` there is
followed by `Appendix`, not by a number, so it is **not** a section reference and carries no link (by
design: §4.2 requires a number). The links in that sentence are
`Appendix 6 Minimum Surface Areas Indoors and Outdoors`. Write the scenario against the anchor that
exists, and use `Section B Appendix 6b` (in `S5.1.7`) as the second example. If the reviewer is told
to follow a link that is deliberately plain text, the FAIL is the scenario's, not the product's.

- [ ] **Step 1: Write the three scenarios** — PRD §9 is the wording. Do not re-invent the judgements.

- [ ] **Step 2: Run the format gate**

Run: `python -c "from pathlib import Path; from scripts.uat_parse import parse_uat; u = parse_uat(Path('tests/uat/concordance_uat.md')); print(len(u.scenarios))"`
Expected **before**: `8`. Expected **after**: `11`. Then the strict gate:
`python scripts/uat_runner.py --file tests/uat/concordance_uat.md --database <the dev DB>` → exit 0,
`product/design/uat/concordance.html` written with eleven cards.
Observe both failure modes once while writing: a card with no `Judgement:` raises `UatFormatError`
naming the scenario, and a duplicated number raises too.

- [ ] **Step 3: Commit**

```bash
git add tests/uat/concordance_uat.md
git commit -m "test(uat): three judgement scenarios for the reader's structure

Plan-Task: 0"
```

*(Tasks 0 and 9 are documentation; they commit once. `tdd_split` applies to Tasks 1–8.)*

---

## Task 1: Appendix 2's structure is reviewed data, beside its rows

**Files:**
- Modify: `knowledge/tables.py`
- Test: `knowledge/tests/test_table_sections.py` (create)

**Contract — the interface.**

```python
NO_CONDITION_LABEL = "no condition printed"          # the muted label, D70.4 answer 1

@dataclass(frozen=True)
class TableDivider:
    before_row: int      # index into TABLE_ROWS[section_ref]
    text: str            # as printed: "II. MINERAL ORIGIN"
    kind: str            # "part" | "qualifier"

@dataclass(frozen=True)
class TableSection:
    columns: tuple[str, str]        # the printed headers, sentence-cased
    legend: str                     # one reviewed sentence — the page's own claim
    dividers: tuple[TableDivider, ...]

@dataclass(frozen=True)
class TableStructure:
    section: TableSection
    dividers: tuple[tuple[TableDivider, ...], ...]   # one tuple per row, in row order
    labels: tuple[str, ...]                          # "" or NO_CONDITION_LABEL, per row

TABLE_SECTIONS: dict[str, TableSection] = {"Appendix 2": ...}

def section_for(section_ref: str | None) -> TableSection | None
def structure_for(section_ref: str | None, texts: tuple[str, ...]) -> TableStructure | None
```

`structure_for()` returns **None** unless `rows_for(section_ref)` is non-empty, its length equals
`len(texts)`, and every text equals its row's `text` whitespace-normalised — a corpus that disagrees
with the reviewed data renders today's plain page rather than mislabelled rows. Pure: no Django
import, no query, no PDF read.

**The data** (the probe's output; each divider is the line immediately above the row it precedes):

| before_row | text | kind |
|---:|---|---|
| 0 | `I. PLANT AND ANIMAL ORIGIN` | part |
| 1 | `South African specific` | qualifier |
| 3 | `South African specific` | qualifier |
| 14 | `South African specific` | qualifier |
| 15 | `II. MINERAL ORIGIN` | part |
| 26 | `III. MICROBIOLOGICAL` | part |
| 28 | `IV. OTHERS` | part |

**The assertions.**

1. `len(sections["Appendix 2"].dividers) == 7`, and the `(before_row, text, kind)` triples equal the
   table above in that order.
2. **Necessary and applied.** For every divider `d`, on the printed page of `rows[d.before_row]`
   (the `table` extraction, `pages("saoso", "table")`): `d.text` occurs **before** that row's
   substance cell, and the text between them holds **no other row's substance cell**. This is the
   guard that fails on a reprint (the `CORPUS_EDITS` idiom).
3. The column headers are the page's: on the printed page carrying the table's header (PDF 77 /
   printed 76) assert `"SUBSTANCES" in page and "CONDITIONS FOR USE" in page`, and assert
   `section.columns[1] == "Conditions for use"` — sentence case is the review's, the capitals are
   the paper's.
4. `section.legend` equals the reviewed sentence **verbatim** (a golden string in the test). Its last
   clause is *"Where it prints no condition, nothing is permitted by its silence."* — the claim the
   label must not contradict. (`test_claim_discipline.py` sweeps the legend as the group's own words;
   this test may not import it — `knowledge` never imports `core`.)
5. `NO_CONDITION_LABEL == "no condition printed"`; it is a label, not a sentence (no capital, no full
   stop); and `structure_for("Appendix 2", texts).labels.count(NO_CONDITION_LABEL) == 19`.
6. `structure_for("Appendix 2", texts)` → 30 `labels`, `dividers[0] ==
   (TableDivider(0, "I. PLANT AND ANIMAL ORIGIN", "part"),)`, `dividers[2] == ()`; wrong length →
   `None`; one altered text → `None`; `structure_for("Appendix 3", ...)` → `None`.
7. `section_for("Appendix 3") is None`, `section_for(None) is None`, and `section_for("Appendix 2")`
   is `TABLE_SECTIONS["Appendix 2"]` (identity — the accessor does not rebuild the data per call).

- [ ] **Step 1: Write the failing tests** — the seven assertions, reading `APPENDIX_2_ROWS` for the
  texts and `pages("saoso", "table")` for the printed pages.

- [ ] **Step 2: Run them**

Run: `python -m pytest knowledge/tests/test_table_sections.py -q`
Expected: collection error — `ImportError: cannot import name 'TableDivider' from 'knowledge.tables'`.

- [ ] **Step 3: Write the data and the two accessors.**

- [ ] **Step 4: Run them**

Run: `python -m pytest knowledge/tests/test_table_sections.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Prove the guard can fail.** Set `before_row=26` to `25` → assertion 2 names
  `III. MICROBIOLOGICAL`. Change the legend's last clause to *"nothing is forbidden by its silence."*
  → assertion 4 fails naming the string. Restore both.

- [ ] **Step 6: Commit (two commits)**

```bash
git add knowledge/tests/test_table_sections.py
git commit -m "test(tables): the printed table's parts, headers and silence

Plan-Task: 1"
git add knowledge/tables.py
git commit -m "feat(tables): Appendix 2's structure as reviewed data

Plan-Task: 1"
```

---

## Task 2: a reviewed row has blocks of its own

**Files:**
- Modify: `knowledge/passages.py`
- Test: `knowledge/tests/test_row_blocks.py` (create)

**Contract — the interface.**

```python
@dataclass(frozen=True)
class RowHeading:
    """A table row's substance cell. Not a Term: a term is a glossary headword, a row heading is a
    table entry, and they must not weigh the same on the page."""
    text: str
    kind: str = "row"

Block = Paragraph | Heading | Term | RowHeading | ListBlock

def row_blocks(text: str) -> tuple[Block, ...]:
    """In: one reviewed row's stored text (`TableRow.text`). Out: the blocks the reader renders.

    In:  `text` — the substance line, then the condition, its paragraphs separated by a blank line.
    Out: `RowHeading(substance)`, then one `Paragraph` per non-empty condition paragraph; `()` for
         empty input; **no paragraph at all** when the condition is empty.
    Side effects: none.
    Fails: never. `passage_blocks()` is neither called nor changed.
    """
```

`flatten()` needs no change — `RowHeading.text` is picked up by its existing `else: block.text`
branch. Assert that rather than assume it.

**The assertions.**

1. `flatten(row_blocks(row.text)) == normalise(row.text)` for **all 30** of `APPENDIX_2_ROWS`.
2. `row_blocks("Guano") == (RowHeading("Guano"),)` — one block, no paragraph.
3. The wood row: `blocks[0].text == "Wood, bark, sawdust and sawmill off-cuts"` (the whole substance
   cell, commas and all), `len(blocks) == 2`, and the paragraph holds
   `"Only if not chemically treated"`.
4. The farmyard-manure row (index 0): `len(blocks) == 5` — one heading and **four** paragraphs; the
   first starts `"Shall not constitute the main source of nitrogen"`, the last is
   `"Forbidden if from factory farming origin."`.
5. `row_blocks("Blood meal, meat meal, bone, bone meal")` → a single `RowHeading`, no paragraph.
6. `row_blocks("")` and `row_blocks("   \n\n ")` → `()`.
7. No block returned for any real row has `kind in {"term", "list"}` — a curated row is never
   re-interpreted as prose structure.
8. `RowHeading("X").kind == "row"`, and `passage_blocks("Guano")` still returns a `Paragraph`
   (the old function is unchanged).

- [ ] **Step 1: Write the failing tests.**

- [ ] **Step 2: Run them**

Run: `python -m pytest knowledge/tests/test_row_blocks.py -q`
Expected: collection error — `ImportError: cannot import name 'row_blocks'`.

- [ ] **Step 3: Add `RowHeading`, widen the `Block` union, write `row_blocks()`.** Do not touch
  `passage_blocks()`.

- [ ] **Step 4: Run them**

Run: `python -m pytest knowledge/tests/test_row_blocks.py knowledge/tests/test_passages.py -q`
Expected: the new file green **and** `test_passages.py` unchanged and green — the old layout still
holds.

- [ ] **Step 5: Prove the guard can fail.** Emit a paragraph for the empty condition → assertion 2
  fails. Split the condition on single newlines instead of blank lines → assertion 4 fails with
  eight blocks. Restore both.

- [ ] **Step 6: Commit (two commits)**

```bash
git add knowledge/tests/test_row_blocks.py
git commit -m "test(passages): a table row renders as a heading and its condition

Plan-Task: 2"
git add knowledge/passages.py
git commit -m "feat(passages): RowHeading and row_blocks for curated rows

Plan-Task: 2"
```

---

## Task 3: the appendix renders as the paper's table

**Files:**
- Modify: `core/services/_documents.py`, `core/templates/public/_passage_blocks.html`,
  `core/templates/public/document_reader.html`, `core/static/css/reader.css`
- Test: `core/tests/test_document_reader.py` (extend)

**Contract — the interface.**

```python
@dataclass(frozen=True)
class ReaderPassage:
    ...                                          # unchanged fields
    dividers: tuple[TableDivider, ...] = ()      # the printed divider(s) immediately above this row
    note: str = ""                               # NO_CONDITION_LABEL, or ""

@dataclass(frozen=True)
class Reader:
    ...                                          # unchanged fields
    table: TableStructure | None = None          # the branch's reviewed structure, when it has one
```

Assembly order in `reader_for()`: build each row's **rendered text** (the `strip_overlap`-trimmed
one, exactly what is displayed), take `texts = tuple(...)`, call
`structure_for(first_chunk.section_ref, texts)`, then build each `ReaderPassage` with
`row_blocks(text)` when a structure came back and `passage_blocks(text)` when it did not. The
dividers' `before_row` becomes that passage's `dividers`; `labels[i]` becomes `passages[i].note`.
No new query — the texts are already in hand.

**The assertions** (a fixture that publishes a document and ingests 30 chunks from
`chunks_for_rows("Appendix 2")`, plus one non-curated branch):

1. `reader.table is not None` on the Appendix 2 branch, and the legend appears **once** in the page.
2. The caption renders both printed headers, and it renders **above** the first row.
3. All 30 passages have `blocks[0].kind == "row"`; no passage returns a block of kind `term`.
4. `sum(1 for p in reader.passages if p.note) == 19` and the page contains the string
   `"no condition printed"` exactly **19** times.
5. `reader.passages[15].dividers == (TableDivider(15, "II. MINERAL ORIGIN", "part"),)`, and in the
   HTML `"II. MINERAL ORIGIN"` appears **before** `"Calcareous and magnesium amendments"`.
   `"South African specific"` appears **3** times; `reader.passages[2].dividers == ()`.
6. The branch without reviewed rows renders exactly as today: `reader.table is None`, every block
   comes from `passage_blocks`, and the string `"no condition printed"` is absent.
7. No words lost: the farmyard-manure condition's first sentence appears verbatim in the page.
8. `django_assert_num_queries` unchanged from the baseline measured on `5ac5128` for the same branch
   (record the number in the test's docstring; a new query means the table assembly went to the DB).
9. `core/tests/test_claim_discipline.py::test_the_reader_adds_no_claim_of_its_own` stays green — the
   legend is now the group's own words and is swept.

**Design (no new colour, no new font):** `.passage__row` sits between `.passage__term` and
`.passage__heading` — one step up from body, one below a printed heading, `--brand-forestDark`. A
`part` divider renders at `.passage__heading` weight, a `qualifier` at `.passage__term` weight; both
are quoted text, neither is an `<h*>`. The caption and legend use `--text-micro` / `--brand-muted`
above a hairline. The label is `--brand-muted`, `--text-micro`, inline in the passage's meta line.
No divider gets an `id` — it carries no text the standard numbers, so it is not citable.

- [ ] **Step 0: Measure the page before touching it** (this number is the "before" in Task 9's
  HANDOVER section; there is no other way to recover it once the template changes):

```bash
python manage.py runserver            # DEBUG=False serves cached templates — see §3.8 of the hazards
curl -s "http://127.0.0.1:8000/documents/saoso-standard-v2.1/read/?section=appendix-2" | wc -c
curl -s -H 'Accept-Encoding: gzip' "http://127.0.0.1:8000/documents/saoso-standard-v2.1/read/?section=appendix-2" | wc -c
```

Record both in the commit body. The PDF is 192 KB; the branch page must stay under it raw, and the
gzip figure is the one that matters on the wire.

- [ ] **Step 1: Write the failing tests** (1–9 above).

- [ ] **Step 2: Run them**

Run: `python -m pytest core/tests/test_document_reader.py -q`
Expected: `TypeError: 'Reader' object has no attribute 'table'` (and `dividers`), or
`AttributeError` on `reader.passages[0].note` — one collection of failures, not a page mismatch.

- [ ] **Step 3: Write the assembly, the two template branches and the CSS.**

- [ ] **Step 4: Run them**

Run: `python -m pytest core/tests/test_document_reader.py core/tests/test_claim_discipline.py -q`
Expected: all green.

- [ ] **Step 5: Prove the guards can fail.** Return `passage_blocks()` for curated rows → assertion 3
  fails on the `Guano` row (a `Paragraph`, because the paper prints no condition). Drop the
  `note=` assignment → assertion 4 fails with `0 != 19`. Render the legend twice → assertion 1 fails.
  Restore all three.

- [ ] **Step 6: Commit (two commits)**

```bash
git add core/tests/test_document_reader.py
git commit -m "test(reader): Appendix 2 renders as the table the paper prints

Plan-Task: 3"
git add core/services/_documents.py core/templates/public core/static/css/reader.css
git commit -m "feat(reader): a curated branch renders as its table

Plan-Task: 3"
```

---

## Task 4: a reference resolves, or it stays text

**Files:**
- Create: `knowledge/references.py`
- Test: `knowledge/tests/test_references.py` (create)

**Contract — the interface.** No URLs here: a `Segment` names a **branch anchor** and a **fragment**,
and the template builds `?section=…` (`build_principles.md` §I — `knowledge` knows documents and
chunks, not routes).

```python
@dataclass(frozen=True)
class Target:
    key: str          # "S5", "Appendix 6b"
    anchor: str       # "s5", "appendix-6b" — a branch the page renders
    title: str        # the branch's printed title, for the tooltip

@dataclass(frozen=True)
class Match:
    start: int        # offset in the string
    end: int
    text: str         # what the paper prints — the link's own words
    branch: str = ""  # a branch anchor; "" -> not a branch link
    fragment: str = ""  # where to land: the branch's own anchor, "not-in-corpus", or a term id (Task 7)
    title: str = ""

@dataclass(frozen=True)
class Segment:
    text: str
    branch: str = ""
    fragment: str = ""
    title: str = ""

@dataclass(frozen=True)
class ReferenceIndex:
    branches: Mapping[str, Target]        # branch key -> target
    parts: Mapping[str, str | None]       # branch key -> its printed part letter (TOC), else None

def build_reference_index(document: StandardDocument) -> ReferenceIndex

def matches(text: str, index: ReferenceIndex, *, open_branch: str = "") -> list[Match]

def segments_for(text: str, index: ReferenceIndex, *, open_branch: str = "") -> tuple[Segment, ...]

def annotate(blocks: Sequence[Block], index: ReferenceIndex, *, open_branch: str = "") -> tuple[Block, ...]
```

The index is built from the concordance and the TOC only — **never** from the text. `parts` comes
from `StandardDocument.toc`: for each branch, the TOC entry it was matched to carries `part`
(`A`/`B`); a document with no TOC has an empty `parts`, so an unqualified `Section n` is undecidable
there. `segments_for()` returns the whole string as segments (`"".join(s.text …) == text`), scanning
three printer's shapes (part-qualified section, bare section, appendix) and dropping any match that
overlaps an earlier one.

**Task 7 widens `segments_for` and `annotate` with `terms: Mapping[str, GlossaryEntry] | None = None`**
— a new optional parameter, so every assertion below stays true unchanged.

**The assertions.** The corpus ones ingest the shipped SAOSO once from the committed pages (~6 s).

1. **Inventory.** Over every chunk of the real SAOSO — each one scanned with **its own branch** as
   `open_branch`, because that is how the reader calls it and because an unqualified `Section n`
   resolves only inside a part — the raw match count is **39**: 10 section references and 29 appendix
   mentions. **30** carry a branch; **9** do not (8 × `Appendix 4`, 1 × bare `Appendix 6`). The one
   Part A reference carries `fragment="not-in-corpus"` and no branch.
2. **Resolution table** — `input → expected`:

| printed input | `Match.text` | `branch` |
|---|---|---|
| `Section B – 5 Animal Husbandry 5.3, 5.5, 5.6` | `Section B – 5` | `s5` (fragment `s5`) |
| `Section B – 1 Definitions` | `Section B – 1` | `s1` |
| `Section A – 2.3` | `Section A – 2.3` | `""`, `fragment="not-in-corpus"`, `title` says Section A is printed and not in the corpus |
| `Section 4.6.2` (in a part-B branch) | `Section 4.6.2` | `s4` |
| `Section 22 Labelling, clause 22.1.3.` | `Section 22` | `s22` (the printed label and the detached clause stay text) |
| `Appendices 2` / `Appendix 2` | as printed | `appendix-2` |
| `Appendix 6 Minimum Surface Areas Indoors and Outdoors` | as printed | `appendix-6b` (by its printed words) |
| `Appendix 6a` / `Appendix 6b` | as printed | `appendix-6a` / `appendix-6b` |
| bare `Appendix 6` | `Appendix 6` | `""` — 6a or 6b is undecidable |
| bare `Appendix 4` | `Appendix 4` | `""`, `title` names **both** tables |
| `Appendix 4 Table 1 and…` | `Appendix 4 Table 1` | `appendix-4-table-1` |
| `Section B Appendix 6b` | `Appendix 6b` | `appendix-6b` — `Section B` has no number, so it is not a section reference |

3. **The two traps.** `Section A – 2.3` never resolves to `s2` (assert the resolved value is not
   `s2` under any input); and the same string with **no TOC** on the document yields **no** section
   match at all (a hand-built document, `toc=[]`).
4. **The open branch.** `matches("Appendix 2", index, open_branch="Appendix 2")` → one match with
   `branch == ""`. The real corpus contains **0** such references today, so this is a synthetic guard
   and the docstring says so.
5. **Negative control.** A hand-built document holding `Appendix 5` and no such branch, and one
   holding `Appendix 9`: **0** matches with a branch. (The probe measures the real BPP and landscape
   mentions; this test proves the rule that makes them plain.)
6. **Lossless.** For every chunk of the real SAOSO, scanned with its own branch as `open_branch`,
   `"".join(s.text for s in segments_for(...))` equals the chunk's whitespace-collapsed text — the
   reader may add targets, never words.
7. **No links in structure.** `annotate()` never segments a `Heading`, `Term` or `RowHeading` (a
   printed heading is the document naming itself; a headword is not a sentence).
8. **Empty index.** `segments_for("Section 4.6.2", ReferenceIndex({}, {}))` → exactly
   `(Segment("Section 4.6.2"),)` — one plain segment.
9. **Order and non-overlap.** Matches are sorted by `start`, and no two overlap; a part-qualified
   section wins over the bare shape it contains.

- [ ] **Step 1: Write the failing tests** (1–9).

- [ ] **Step 2: Run them**

Run: `python -m pytest knowledge/tests/test_references.py -q`
Expected: `ModuleNotFoundError: No module named 'knowledge.references'`.

- [ ] **Step 3: Write the module** — index from `build_concordance()` + `document.toc`; three
  patterns; overlap resolution; `Segment`s. No `core` import, no `reverse()`, no URL string.

- [ ] **Step 4: Run them**

Run: `python -m pytest knowledge/tests/test_references.py -q`
Expected: `9 passed` — and assertion 1's numbers are the probe's, so a mismatch means the corpus or
 the rule moved, not that the test is wrong.

- [ ] **Step 5: Prove the guards can fail.** Map Part A to the section's number (drop `missing`) →
  assertion 3 fails with `s2`. Let a bare `Appendix 4` resolve to its first branch → assertion 1's
  `9` becomes `1`. Remove the open-branch check → assertion 4 fails with `appendix-2`. Restore.

- [ ] **Step 6: Commit (two commits)**

```bash
git add knowledge/tests/test_references.py
git commit -m "test(references): the document's own references resolve or stay text

Plan-Task: 4"
git add knowledge/references.py
git commit -m "feat(references): an index from the concordance and the printed TOC

Plan-Task: 4"
```

---

## Task 5: the page makes its own references clickable

**Files:**
- Modify: `core/services/_documents.py`, `core/templates/public/_passage_blocks.html`,
  `core/templates/public/document_reader.html`, `core/static/css/reader.css`
- Test: `core/tests/test_document_reader.py` (extend)

**Contract.** `Paragraph` and `ListItem` gain `segments: tuple[Segment, ...] = ()`; `annotate()`
returns the same block types, the same `text`, with `segments` filled where a reference was found
(empty tuple → the template prints `{{ block.text }}` as today). `reader_for()` builds the index once
per request and calls `annotate(blocks, index, open_branch=selected.key)`.

The template renders one `<a>` shape for both kinds of target:

```html
<a href="{% if segment.branch %}?section={{ segment.branch }}#{{ segment.fragment }}{% else %}#{{ segment.fragment }}{% endif %}"
   target="_blank" rel="noopener"{% if segment.title %} title="{{ segment.title }}"{% endif %}>
  {{ segment.text }}<span class="visually-hidden"> (opens in a new tab)</span>
</a>
```

A segment with **no** target and a `title` renders as `<span title=…>` (bare `Appendix 4` names both
tables); with neither, as plain text. `rel="noopener"` is not optional — a new tab that can reach
back is the one thing a citation surface must not allow.

**D70.6 (the note moves):** the `reader.missing` paragraph leaves the `<details>` tree and sits
immediately after it, carrying `id="not-in-corpus"`. Reason: `Section A – 2.3` links to it, and a
fragment inside a closed `<details>` cannot be scrolled to on a phone.

**The assertions.**

1. The Appendix 2 page renders, for the seaweed row's sentence, exactly one anchor whose text is
   `Appendix 6 Minimum Surface Areas Indoors and Outdoors`, whose `href` is
   `?section=appendix-6b#appendix-6b`, and which carries `target="_blank"` **and** `rel="noopener"`.
2. `Section A – 2.3` (in `S22.1.7` — open `/read/?section=s22`) renders as
   `href="#not-in-corpus"`, the page contains `id="not-in-corpus"`, and in the HTML that `id`
   appears **after** `</details>` (the note is not inside the phone disclosure).
3. Every reference anchor carries the visually-hidden suffix `(opens in a new tab)` — count anchors
   with `target="_blank"` in the page and compare with the number of links the reader produced.
4. Bare `Appendix 4` renders as a `<span title=…>` naming **both** tables, with no `href` and no
   `target`; bare `Appendix 6` renders as plain text.
5. A document with a reference to a branch it does not have (a hand-built `Appendix 5` document)
   renders **no** reference anchor at all.
6. The words are untouched end to end: `core/tests/test_chatbot_grounding.py` stays green over the
   real corpus (the audit reads chunks, the page reads segments).
7. `django_assert_num_queries` is unchanged (the TOC rides on the document row already loaded).
8. `test_the_reader_adds_no_claim_of_its_own` stays green.

**Design:** a reference link is `--brand-forest` with a hairline underline and no colour change on
hover beyond `--brand-forestDark`; it must not read as a button. No icon, no external-link glyph
(the visually-hidden text is the announcement — one mechanism, not three).

- [ ] **Step 1: Write the failing tests** (1–8). Test 2 needs a branch that prints `Section A – 2.3`;
  use the real corpus or the chunk `S22.1.7` from it, whichever the fixture already has.

- [ ] **Step 2: Run them**

Run: `python -m pytest core/tests/test_document_reader.py -q`
Expected: the reference assertions fail on `AssertionError: 'Appendix 6 Minimum Surface Areas' not in
…` (the text is there, the anchor is not) and test 2 fails on `id="not-in-corpus"` being absent.

- [ ] **Step 3: Write the wiring, the template branch and the CSS.**

- [ ] **Step 4: Run them**

Run: `python -m pytest core/tests/test_document_reader.py core/tests/test_chatbot_grounding.py core/tests/test_claim_discipline.py -q`
Expected: all green.

- [ ] **Step 5: Prove the guards can fail.** Drop `rel="noopener"` → assertion 1 fails. Move the note
  back inside `<details>` → assertion 2 fails. Render the bare `Appendix 4` as an anchor → assertion 4
  fails. Restore all three.

- [ ] **Step 6: Commit (two commits)**

```bash
git add core/tests/test_document_reader.py
git commit -m "test(reader): a reference on the page goes somewhere

Plan-Task: 5"
git add core/services/_documents.py core/templates/public core/static/css/reader.css
git commit -m "feat(reader): references are links that open in a new tab

Plan-Task: 5"
```

---

## Task 6: one locator per run

**Files:**
- Modify: `knowledge/reading.py`, `core/services/_documents.py`,
  `core/templates/public/document_reader.html`
- Test: `knowledge/tests/test_reading.py` (extend), `core/tests/test_document_reader.py` (extend)

**Contract — the interface.** A pure display rule, beside `strip_overlap()` because it is the same
kind of thing:

```python
def passage_locator(chunk: DocumentChunk) -> str:
    """The one expression for what a passage prints as its locator — `section_ref`, else `anchor`,
    else `heading_path`, else `p<n>`. It lives here because the reader and `probe_reader_structure`
    must not each hold a copy: a copy is how the probe came to measure a limit the product did not
    have (§21, G8)."""

def printed_locators(locators: Sequence[str]) -> list[bool]:
    """In: one branch's locator strings, in order. Out: whether each one prints.

    True for the first, and wherever it differs from the locator above it. Same length as the input.
    The `id` is not affected: every passage keeps its anchor, so a citation still lands.
    """
```

`ReaderPassage` gains `show_locator: bool = True`, set from that list; the template wraps the
`.passage__locator` paragraph in `{% if passage.show_locator %}`.

**The assertions.**

1. Pure: `[]` → `[]`; `["a"]` → `[True]`; `["a","a","a"]` → `[True, False, False]`;
   `["a","a","b","b"]` → `[True, False, True, False]`; `len(out) == len(in)` always.
2. Reader-level: a branch whose 8 passages share one locator prints **one** `.passage__locator`
   element, and all **8** `id="…"` anchors are still in the HTML.
3. Reader-level: a branch where passage 3 changes page prints a second locator at passage 3, and it
   is the same string as before (`S5 · printed p. 41`), not a shortened form.
4. The corpus numbers are the probe's (Task 8): 319 → **273**, 30 → **28**, 8 → **6**, 9 → **4**,
   366 → **311**. Hardcode them in the probe's expectations, not in a test that cannot see the
   corpus — the rule is tested here, the measurement there.
5. `reader_for()` builds each `ReaderPassage.locator` with `passage_locator(chunk)` — no inline copy
   of the expression remains in `_documents.py` (Task 8's probe test asserts the probe uses the same
   two functions).
6. `core/tests/test_document_reader.py`'s existing anchor tests stay green (they assert ids, which do
   not move).

- [ ] **Step 1: Write the failing tests** (1–3, 5–6).

- [ ] **Step 2: Run them**

Run: `python -m pytest knowledge/tests/test_reading.py core/tests/test_document_reader.py -q`
Expected: `ImportError: cannot import name 'printed_locators'`, and the reader-level assertion failing
with `8 != 1` locator paragraphs.

- [ ] **Step 3: Add the rule, the field and the template condition.**

- [ ] **Step 4: Run them**

Run: `python -m pytest knowledge/tests/test_reading.py core/tests/test_document_reader.py -q`
Expected: all green.

- [ ] **Step 5: Prove the guard can fail.** Print every locator → assertion 2 fails with `8 != 1`.
  Suppress the locator when the page differs but the reference does not → assertion 3 fails. Restore.

- [ ] **Step 6: Commit (two commits)**

```bash
git add knowledge/tests/test_reading.py core/tests/test_document_reader.py
git commit -m "test(reading): a locator prints once per run

Plan-Task: 6"
git add knowledge/reading.py core/services/_documents.py core/templates/public/document_reader.html
git commit -m "feat(reading): the locator prints once, and the id stays

Plan-Task: 6"
```

---

## Task 7: a defined word is a click away

**Files:**
- Create: `knowledge/glossary.py`
- Modify: `knowledge/passages.py` (`Term.anchor`), `knowledge/references.py` (the `terms` parameter),
  `core/services/_documents.py`, `core/templates/public/_passage_blocks.html`
- Test: `knowledge/tests/test_glossary.py` (create), `core/tests/test_document_reader.py` (extend)

**Contract — the interface.** Derived, with the review recorded as removals (D70.7):

```python
#: Which branch is the glossary. Reviewed data: which section defines a document's words is a fact
#: about the document, not something a heuristic may guess.
GLOSSARY_BRANCH: dict[str, str] = {"pgs_docs/saoso-version-2.1-2026.pdf": "S1"}

#: Headwords the display heuristic finds there that are NOT defined terms. Each must still exist as a
#: `Term` in the branch — a rejection that matches nothing is a stale review (`CORPUS_EDITS` idiom).
REJECTED: dict[str, tuple[str, ...]] = {"pgs_docs/saoso-version-2.1-2026.pdf": ()}

TERM_PREFIX = "term-"

@dataclass(frozen=True)
class GlossaryEntry:
    term: str        # "ACB"
    slug: str        # "acb"
    branch: str      # "s1" — the anchor of GLOSSARY_BRANCH[source_file]
    fragment: str    # "term-acb"

def glossary_entries(source_file: str, blocks: Sequence[Block]) -> tuple[GlossaryEntry, ...]:
    """In: a document's `source_file` and its glossary branch's rendered blocks (already
    overlap-trimmed by the reader). Out: one entry per distinct `Term`, in printed order; `()` for a
    document with no `GLOSSARY_BRANCH`."""

def with_term_anchors(blocks: Sequence[Block]) -> tuple[Block, ...]:
    """Out: the same blocks with `Term.anchor = "term-<slug>"`; every other block untouched."""
```

`Term` gains `anchor: str = ""`. `segments_for()` and `annotate()` gain
`terms: Mapping[str, GlossaryEntry] | None = None` and `seen: set[str] | None = None`; a term links
**once per `annotate()` call**, and the reader calls `annotate()` **once per passage**, which is what
makes the rule "one link per term per passage" a property of the caller rather than a counter inside
the scan. Matching is case-insensitive, whole-word, longest term first.

**The assertions.**

1. On the shipped SAOSO, `glossary_entries(...)` returns **71 − len(REJECTED[…])** entries (71 with an
   empty rejection list), every slug distinct, and the first is `acb` → `ACB`. `Breeding` appears
   **once** (the seventh repeat was the chunk overlap, which `strip_overlap` already trims).
2. **Provenance:** every entry's term is a `Term` block of that branch — by construction, plus a test
   that fails if a term is invented. **The rejection guard is proven, not assumed:** a helper
   `_reviewed(terms, rejected)` raises `ValueError` naming a rejection that matches no term; the test
   calls it with `("Not A Term",)` and expects that error. With today's empty list this is the only
   way the guard stays alive, and the docstring says so.
3. `with_term_anchors()` gives the `ACB` block `anchor == "term-acb"`, leaves every other block's
   `anchor == ""`, and produces no duplicate anchors across the branch (71 terms → 71 ids).
4. **One link per term per passage:** a passage of `Soil texture improves Soil structure` yields
   exactly one `Soil` link, the first. `Conversion Period` links as a whole and `Conversion` alone
   does not; a lowercase `habitat` links; `nail` does not link `Soil`-like inside a word.
5. **No self-links:** `segments_for("ACB", index, terms=…, open_branch="S1")` → no link.
6. **The target is the definition:** on the `S6` branch a paragraph naming `ACB` renders
   `href="?section=s1#term-acb"`, and the `S1` page contains `id="term-acb"`.
7. No term link inside a `Term`, `Heading` or `RowHeading` block.
8. Lossless with terms: joining a paragraph's segments still reproduces its text over every chunk of
   the real SAOSO.
9. `/read/?section=s1` renders 71 `id="term-…"` elements and **no** internal glossary anchors (rule 5).

- [ ] **Step 1: Write the failing tests** (1–9).

- [ ] **Step 2: Run them**

Run: `python -m pytest knowledge/tests/test_glossary.py -q`
Expected: `ModuleNotFoundError: No module named 'knowledge.glossary'`.

- [ ] **Step 3: Write the module, the field, the widening and the wiring.**

- [ ] **Step 4: Run them**

Run: `python -m pytest knowledge/tests/test_glossary.py knowledge/tests/test_references.py core/tests/test_document_reader.py -q`
Expected: all green; Task 4's assertions unchanged (the new parameter is optional).

- [ ] **Step 5: Prove the guards can fail.** Remove the per-call `seen` set → assertion 4 fails with
  `2` links for `Soil`. Drop the `open_branch` check → assertion 5 fails. Build the entries from the
  raw (untrimmed) text → assertion 1 fails with 78 entries and a duplicate `breeding` anchor.

- [ ] **Step 6: Commit (two commits)**

```bash
git add knowledge/tests/test_glossary.py core/tests/test_document_reader.py
git commit -m "test(glossary): a defined word links to its definition, once per passage

Plan-Task: 7"
git add knowledge/glossary.py knowledge/passages.py knowledge/references.py core/services/_documents.py core/templates/public/_passage_blocks.html
git commit -m "feat(glossary): the term list is derived, the review is the rejections

Plan-Task: 7"
```

---

## Task 8: the instrument measures the shipped data, not a copy of it

**Files:**
- Modify: `scripts/probe_reader_structure.py`
- Test: `tests/tools/test_probe_reader_structure.py` (create)

**Why this is a task and not a footnote.** `probe_chat.py` hardcoded the retrieval limit that
`settings` overrode, so it reported a grounded answer for a question the product refused (§21, G8).
This probe has the same defect waiting: `PROPOSED_DIVIDERS` and `COLUMN_HEADERS` are **copies** of
data that now lives in `knowledge/tables.py`, and a copy is free to stay right while the product goes
wrong.

**Contract.** Delete `PROPOSED_DIVIDERS` and `COLUMN_HEADERS`. The probe imports `TABLE_SECTIONS`,
`structure_for`, `APPENDIX_2_ROWS`, `build_reference_index`, `segments_for`, `glossary_entries` and
reports:

| Section | What it prints | Expected on the shipped corpus |
|---|---|---|
| The table | rows, empty cells, pages, dividers with the line above them, header pages | `30`, `19`, `[76, 77, 78]`, `7` dividers all `immediately above`, headers on PDF 77 |
| Locator runs | passages / printed today / printed after / suppressed, via `printed_locators()` and `passage_locator()` | `319 / 273 / 46`, and `30/28`, `8/6`, `9/4` (the “after” column becomes the actual behaviour) |
| References | every mention, its resolution, ambiguous ones named | `39 mentions: 30 linked, 9 plain`; `Section A – 2.3 → NOT IN CORPUS (not S2)` |
| Glossary | entries, duplicates, the branch | `71 entries, 0 duplicate slugs, S1` |

**The assertions** (`tests/tools/` — the gate runs this because `pytest.ini`'s `testpaths` includes
it, `testing_hazards.md` §2.6):

1. `importlib.import_module("scripts.probe_reader_structure")` has **no** `PROPOSED_DIVIDERS` and no
   `COLUMN_HEADERS` attribute — a copied constant cannot come back.
2. The probe's module-level imports include `knowledge.tables`, `knowledge.references`,
   `knowledge.reading.printed_locators` **and** `passage_locator` (grep the source, the way
   `test_probe_chat.py` proves the chat probe makes no retrieval call of its own). Its own
   `chunk.page`-plus-`section_ref` comparison must be gone — that was a second copy of Task 6's rule.
3. `main([ "--doc", "saoso"])` on a seeded corpus exits `0` (a smoke test on the fixture corpus, not
   the dev database).

- [ ] **Step 1: Write the failing tests.**

- [ ] **Step 2: Run them**

Run: `python -m pytest tests/tools/test_probe_reader_structure.py -q`
Expected: `AssertionError: the probe still holds a copy of the data`.

- [ ] **Step 3: Rewrite the probe's four sections to read the shipped data.**

- [ ] **Step 4: Run it on the dev corpus and compare with §0.1**

Run: `python scripts/probe_reader_structure.py`
Expected: every number in §0.1 prints; `Section A – 2.3` prints `NOT IN CORPUS`; the BPP and the
landscape print their single mention with **no** target.

- [ ] **Step 5: Prove the guard can fail.** Re-add `PROPOSED_DIVIDERS = {}` → assertion 1 fails.
  Change a divider in `TABLE_SECTIONS` to a string that is not on the page → the probe prints
  `NOT immediately above` (the probe is the instrument; the *test* that fails is Task 1's).

- [ ] **Step 6: Commit (two commits)**

```bash
git add tests/tools/test_probe_reader_structure.py
git commit -m "test(tools): the reader probe measures the shipped data

Plan-Task: 8"
git add scripts/probe_reader_structure.py
git commit -m "feat(tools): the probe imports the table and the index it reports on

Plan-Task: 8"
```

---

## Task 9: close — the docs, the gate, and the one thing left is judged

**Files:**
- Modify: `product/backlog/In Progress/PASSAGE_LAYOUT_PRD.md`, `HANDOVER.md`, `tests/uat/concordance_uat.md`
- Regenerate: `product/design/uat/concordance.html` (if `uat_seed --check` is clean)

**Contract.**

1. `PASSAGE_LAYOUT_PRD.md` §4's **“Not tables”** note gets one line pointing at
   `READER_STRUCTURE_PRD.md` — it is superseded, and a future session must not read it as current.
2. `HANDOVER.md` gains a `## 0g.` section at the top of the same shape as §0f: what landed, the gate
   number, Playwright, the page weight **before and after**, the probe's output, that the UAT is
   drafted and **unsigned**, and that nothing is pushed or deployed.
3. The UAT artefact is rebuilt on the box whose commit it claims, with its preflight captured first
   (§19's rule: a `file://` page cannot run `manage.py`, and a stale date is a lie).
4. Backlog: `python product/backlog.py --apply` then `--write`; expect **no moves** and a regenerated
   index. The READER_STRUCTURE pair stays in `In Progress/` until the UAT carries names — the
   `CONCORDANCE` precedent.

**The verification, in this order** (evidence before assertions):

```bash
# 1. The page weight, measured the same way on both sides of this slice
#    (before: taken at Task 3 Step 0, commit 5ac5128)
curl -s "http://127.0.0.1:8000/documents/saoso-standard-v2.1/read/?section=appendix-2" | wc -c
curl -s -H 'Accept-Encoding: gzip' "http://127.0.0.1:8000/documents/saoso-standard-v2.1/read/?section=appendix-2" | wc -c

# 2. The whole gate, with the extractor pointed at nothing (D57)
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh

# 3. The browser suite (outside the gate by design)
python -m pytest tests/e2e -q

# 4. The two contracts that do not live in pytest
.venv/Scripts/lint-imports.exe --no-cache --no-logo    # `knowledge` must not import `core`
python manage.py check
```

**Expected:** gate green at **1004 + the new tests** with 1 skipped, `lint-imports` kept,
Playwright at 53 + any new scenario, `manage.py check` clean, and the Appendix 2 page weight still
under the PDF's 192 KB raw while the gzip figure moves by the caption and legend only.

- [ ] **Step 1: Write the two documentation edits and the HANDOVER section.**
- [ ] **Step 2: Run the four verifications above; paste the numbers into HANDOVER §0g.**
- [ ] **Step 3: Regenerate the UAT artefact and the backlog index.**

Run: `python manage.py uat_seed --check > preflight.txt` → expected: SAOSO **319**, 0 unembedded,
8 published; then `python scripts/uat_runner.py --file tests/uat/concordance_uat.md --preflight preflight.txt --database <the DB being signed>` → `product/design/uat/concordance.html`, eleven cards.

- [ ] **Step 4: Commit**

```bash
git add HANDOVER.md product/backlog product/design/uat tests/uat/concordance_uat.md
git commit -m "docs(r9): the reader's structure lands, and the UAT is what is left

Plan-Task: 9"
```

---

## What a green suite cannot see (read before the UAT)

1. **Whether 30 entries under four headings read as a table or as a list with labels.** Scenario 9.
2. **Whether the *Farmyard manure* row now reads as a second condition block rather than as a
duplicate**, because the `South African specific` qualifier sits between the two rows. Scenario 9.
3. **Whether the reference links make the page link-studded.** Scenarios 10 and 11.
4. **Whether a link lands on what the sentence meant** — every rule here resolves a *number*, and
  `Appendix 6 Minimum Surface Areas…` is the one place the words decided it. Scenario 10.
5. **Whether one locator per run leaves a reader lost** in the middle of `S5`'s 52 clauses. Scenario
  1 and Scenario 3 are where it shows, and it is the decision most likely to be reversed after
  someone reads with it (D70.5).

## Definition of done

Gate green; Playwright green; the probe's numbers equal §0.1; `tests/uat/concordance_uat.md` carries
**eleven** scenarios, of which 9, 10 and 11 are new, and **none is signed**. The feature is not done
without names in that table — the same line `CONCORDANCE_PLAN.md` and `ASK_SURFACE_PLAN.md` carry.

## Open questions this plan does not answer

* **Does a divider belong to its row or to the space above it?** It is attached to the row (one
  `<p>` before the heading), so a citation that lands mid-table shows the divider only when it lands
  on that row. The alternative — print the divider above the *preceding* row's gap — reads better
  when scrolling but puts quoted text where the paper does not. Judge it in Scenario 9.
* **Should `S1`'s 71 ids be citable?** `#term-acb` is a display anchor, not a `reading_anchor`, so a
  chat citation can never use it. That is deliberate: only the corpus may be cited.


---

## §12. Built 2026-10-27 — what differs from this plan

All ten tasks landed. Gate **1138 passed / 1 skipped**, Playwright **53**, `lint-imports` kept,
`manage.py check` clean, `uat_seed --check` ready (366 chunks, 0 unembedded, 8 published, Xpdf 4.00).
**The UAT is unsigned** (`tests/uat/concordance_uat.md`, eleven scenarios), so the feature is not done.

**Every number the plan inherited held** — with one correction and one addition:

| Claim | Measured after | Note |
|---|---:|---|
| 30 rows, 19 with no condition, pages 76–78 | 30 / 19 / `[76, 77, 78]` | unchanged |
| 7 dividers, each immediately above its row | 7 / 7 | unchanged |
| Locators 366 → 311 | 366 → **311** (319→273, 30→28, 8→6, 9→4) | unchanged, now through `printed_locators()` |
| 39 mentions → 30 links, 9 plain | 39 / 30 / 9 | unchanged |
| **71 glossary headwords** | **69 rendered, 69 ids** | *corrected*: see below |
| BPP and landscape: 0 links | 0 | unchanged |

**The glossary count was 71 and the page anchors 69.** `S1` holds 78 `Term` blocks and 71 distinct
headwords; the reader's overlap trimming removes two of them entirely — `Buffer Zone` and
`Homeopathic Treatment` are each the *tail* of one chunk and the *head* of the next, so the trimmed
page prints them as the last paragraph of a passage, where the layout finds no following line and
does not call them terms. They are therefore not linkable. The test asserts the absence explicitly
rather than letting the count drift. Making them linkable needs the corpus artefact, not this slice.

**Signatures that changed while building** (each for a reason the code states):

* `printed_locators(rows: Sequence[tuple[str, int | None]])` — the run key is the locator **and its
  page**, because a clause continuing onto the next printed page is a new line to a reader. The plan's
  string-only version could not see that.
* `glossary_entries(source_file, blocks, branch_anchor)` — the third argument is needed to build the
  link; the plan's two-argument sketch would have had to look it up again.
* `branch_texts(pairs)` lives in `knowledge.reading` (not `_documents.py`), so the probe measures the
  same trimmed text the page renders.
* `build_reference_index(document, sections=None)` — takes the tree when the caller has it, so the
  reader stays at **3 queries** (it was 3 before this slice; a second `build_concordance()` would
  have made it 4).
* `Segment(text, branch, fragment, title)` carries an anchor, never a URL: `knowledge` does not know
  routes, so the template builds `?section=…`.
* `with_term_anchors(blocks, seen)` — the `seen` set spans a branch, so a repeated headword cannot
  produce a duplicate `id`.

**One deliberate extension of D70's answer 2.** Bare `Appendix 6` (1 mention) gets the same treatment
as bare `Appendix 4`: no link, and a tooltip naming `Appendix 6a` / `Appendix 6b`. The decision named
only `Appendix 4` because that was the measured example; applying the rule to the other undecidable
appendix is the same claim, and it means **every** one of the 9 undecided mentions explains itself.

**Three things the slice found that were not in the plan:**

1. **`Section B – Appendix 6 Minimum Surface Areas…`** is one sentence with a part letter that is not
   a section number. The appendix is the target and `Section B –` stays text; UAT Scenario 10 was
   rewritten before it was drafted to test the anchor that exists.
2. **The probe was a second implementation.** It held three resolvers, its own divider constants and
   its own locator comparison; all of it is now imported from `knowledge`, and
   `tests/tools/test_probe_reader_structure.py` fails if a resolver or a copy comes back.
3. **The reader page costs ~0.4 s and it is not this slice's doing.** One request loads all 319
   chunks *with their 768-float embeddings* (`pgvector._from_text` is ~40 % of the profile). That is
   D68's one-query design, unchanged here; a `defer("embedding")` on the reading path is the obvious
   next win and is **not** taken, because it is the citation and concordance path's query.

**And one defect the suite did not catch (2026-10-27, found by the product owner).** Task 5 moved the
missing-sections note out of the phone `<details>` (D70.6) — correctly — but appended it as a **third
child** of the two-column `.reader__body` grid. The grid put the note in row 1 column 2, wrapped
`.reader__passages` to row 2, and left the *sticky* tree sitting on top of the passage text: following
a citation landed on a page whose quoted line was behind the contents list. Every server-side test
passed (markup valid, strings present, anchors resolving, 3 queries, no 390 px overflow) and so did
the 1138-test gate. The fix wraps the `<details>` and the note in `.reader__tree-column` and moves the
sticky rule onto that column — which is what the CSS comment already said the sticky box must be.
The guard is `tests/e2e/test_reader_layout.py` (three browser assertions, proven by reverting the
fix), and the trap is `testing_hazards.md` **§3.12**. **The lesson for the next template change: the
e2e suite is outside `verify.sh`, so a stylesheet or template edit is not verified by the gate.**
