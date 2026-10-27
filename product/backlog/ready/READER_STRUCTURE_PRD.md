# PRD: The reader's structure — a table reads as a table, and a reference goes somewhere

**Status:** **Draft** — the design is agreed in session on 2026-10-27 (product owner: definition-list
shape first, a vision-model extraction only as a fallback; cross-references open in a new tab;
glossary links in scope). This file is for review **before** `READER_STRUCTURE_PLAN.md` is written.
**Owner:** Product (what the reader may claim) · Build (the two derivations)
**Opened:** 2026-10-27
**Origin:** reading `/documents/saoso-standard-v2.1/read/?section=appendix-2` after the glyph fix
(D69) — the appendix rendered as a bare list of substances ("why is there a list of standalone
inputs? I don't understand the context"), Appendix 2's `See Section B – Appendix 6` pointed nowhere,
and `ACB` / `Habitat` / `Extensive Farming` in the definitions were plain text.
**Related:** `CONCORDANCE_PRD.md` §2/§6.3/§10.6–10.7 (the reader and its anchors), D67 (text, not
PDF), D68 (the tree), D69 (the corpus keeps its glyphs), `PASSAGE_LAYOUT_PRD.md` §3–§4 (**§4's "Not
tables" is superseded here**), `knowledge/tables.py`, `knowledge/passages.py`, `knowledge/concordance.py`.
**Plan:** `READER_STRUCTURE_PLAN.md` (not yet written) · **UAT:** `tests/uat/concordance_uat.md` gains
Scenarios 9–11.

---

## 1. The problem, measured

Three separate defects, one page. All numbers below were measured on 2026-10-27 against the corpus
as re-ingested after D69, by `scripts/probe_reader_structure.py` (in the tree; see §8).

### 1.1 Appendix 2 reads as a list of standalone inputs

The paper prints Appendix 2 as a **two-column table**: `SUBSTANCES DESCRIPTION, COMPOSITIONAL
REQUIREMENTS` beside `CONDITIONS FOR USE`, divided by four part headings and three centred
qualifiers. `knowledge/tables.py` stores 30 reviewed rows — one `DocumentChunk` per row — and
deliberately drops the rest of that structure, because a heading is not a permission and the prompt
keeps *silence is not permission*:

| Printed structure | Stored? | Why |
|---|---|---|
| 30 substance rows + their conditions | **yes** — 30 chunks under one `section_ref` | the unit of permission |
| `I. PLANT AND ANIMAL ORIGIN`, `II. MINERAL ORIGIN`, `III. MICROBIOLOGICAL`, `IV. OTHERS` | **no** | not permissions |
| `South African specific` ×3 | **no** | page furniture for pairing |
| `SUBSTANCES …` / `CONDITIONS FOR USE` | **no** | column headers |

So the reader renders 30 substance lines with no skeleton:

| Fact | Number |
|---|---:|
| Appendix 2 passages | **30** |
| …whose condition cell is **empty** on the paper (`Guano`, `Vermicastings`, `Sulphur`, …) | **19** |
| …that print the same locator as the row above (`Appendix 2 · printed p. 76`) | **27** |
| Rows per printed page (76 / 77 / 78) | 11 / 16 / 3 |
| Distinct locators in the whole branch | **3** |

Two further consequences of the same gap:

* **The substance repeats with no explanation.** Rows 0 and 1 are both *Farmyard manure, slurry and
  urine* — the paper prints the substance again for a second condition block, with a `South African
  specific` divider between them. Without the divider the reader sees a duplicate.
* **A row with no condition renders as body text, not as an entry.** Row 0's substance is a `Term`
  (short line, followed by prose); `Guano` alone is not, because `_is_term` needs a longer line after
  it. The same table therefore renders its entries at two different weights.

### 1.2 The locator repeats once per passage, in every branch

`passage__locator` prints `section_ref · printed p. N` above every passage. That is right for a
clause (`S5.1.3 · printed p. 41`), and wrong wherever a branch's chunks share one reference:

| Document | Passages | Locator lines today | …printed once per run |
|---|---:|---:|---:|
| SAOSO v2.1 | 319 | 319 | **273** (−46) |
| OPP | 30 | 30 | 28 |
| Certification landscape | 8 | 8 | 6 |
| BPP | 9 | 9 | 4 |
| **All four** | 366 | 366 | **311** (−55) |

Appendix 1 (6 passages, 1 locator), Appendix 7 (4, 1) and `S1` (8, 1) are the worst cases after
Appendix 2; `S5` loses 2 of 52. The `id`s stay on every passage regardless — only the printed line
is suppressed (HANDOVER §0e item 1, decided here).

### 1.3 A reference is dead text

The corpus names its own parts, sections, appendices and glossary terms. None of it is clickable.
Measured inventory in SAOSO v2.1 (the probe prints it all). **Ten section references**, in two
printer's shapes:

| Printed reference | Occurrences | Resolves to | Ambiguous? |
|---|---:|---|---|
| `Section B – 5 Animal Husbandry 5.3, 5.5, 5.6` | 1 | `S5` | no |
| `Section B – 1 Definitions` | 1 | `S1` | no |
| `Section A – 2.3` | 1 | **Part A, not in the corpus** | no |
| `Section 4.6.2` | 1 | `S4` | no |
| `Section 4` | 1 | `S4` | no |
| `Section 2` | 1 | `S2` | no |
| `section 5.6`, `section 5.7` | 1 + 1 | `S5` | no |
| `Section 22 Labelling, clause 22.1.3.` | 2 | `S22` (the trailing clause number stays text) | no |

**29 appendix mentions**, of which 9 cannot be decided by number alone:

| Printed reference | Occurrences | Resolves to | Ambiguous? |
|---|---:|---|---|
| `Appendix 2` (and `Appendices 2`) | 6 | `Appendix 2` | no |
| `Appendix 3` | 5 | `Appendix 3` | no |
| `Appendix 5` (and `Appendix 5 Substances for…`) | 2 | `Appendix 5` | no |
| `Appendix 7` | 3 | `Appendix 7` | no |
| `Appendix 6a` / `Appendix 6b` | 1 + 1 | themselves | no |
| `Appendix 6 Minimum Surface Areas Indoors and…` | 1 | `Appendix 6b` **by its printed words** | number alone is |
| `Appendix 6` (no title words after it) | 1 | — | **yes: 6a or 6b** |
| `Appendix 4` | 8 | — | **yes: Table 1 or Table 2** |
| `Appendix 4 Table 1 and…` | 1 | `Appendix 4. Table 1` by its printed words | — |

So SAOSO yields **30 links** (10 section + 20 appendix) and leaves 9 appendix mentions as plain text.
The other documents contribute one reference each and no target: the BPP prints `Appendix 5`, the
landscape prints `Appendix 9`, and neither has such a branch — so on those two documents this whole
feature produces **no links at all**, which is the correct behaviour and a useful negative control.

**Two traps, both measured.**

1. **The part letter.** `Section A – 2.3` is Part A's clause 2.3, which the corpus does not hold. A
   naive `S<n>` mapping sends it to `S2` — *Organic Ecosystems*, a different part entirely. The
   `StandardDocument.toc` rows carry `part` (`A`/`B`) beside `label` (`1`…`23`), so the mapping is
   data-driven: **part B + label n → branch `S<n>`; part A + label n → a printed section the corpus
   does not hold** (§4.4), which the page already names under the tree.
2. **The unqualified `Section n`.** Seven of the ten section references print **no part letter**
   (`Section 4.6.2`, `section 5.7`). They are not ambiguous in practice — they are printed inside
   Part B, where "Section" means a section of the part the passage sits in — so the part is taken
   from the branch's TOC entry, never assumed. A document with no TOC has no part, so there an
   unqualified `Section n` stays text rather than being guessed at.

### 1.4 Glossary terms are dead text too

`S1` renders as a glossary (PASSAGE_LAYOUT §3 rule 6) — `ACB`, `Habitat`, `Extensive Farming` and
their definitions — and none of those terms links anywhere. Measured on the candidate list the
*display heuristic* produces (78 `Term` blocks in `S1`): **196 word-boundary occurrences** elsewhere
in the four documents, led by `Soil` ×19, `Breeding` ×15 (the corpus prints that headword twice),
`Synthetic` ×12, `Certification` ×8 and `Accredited` ×6, with **33 of the 78 never occurring again**.
Most of those are prose the heuristic mistook for a headword. So the term list is **not** derivable
from the layout: it has to be reviewed data (§5.1), or the reader links `Soil` nineteen times.

---

## 2. What is decided

**All three fixes are display-only.** No `DocumentChunk` changes, no migration, no re-ingest, and the
citation audit, retrieval, anchors and `flatten()` are untouched. The words remain the document's
words: this slice adds *structure* and *targets*, never text.

| # | Decision | By |
|---|---|---|
| **D70.1** | An appendix that the corpus stores as reviewed rows renders in a **definition-list shape**: each row's substance is its own heading, its condition follows as paragraphs, and the printed part headings / qualifiers / column headers are restored **from reviewed data** — not as a literal two-column grid (the 38 rem measure cannot hold the paper's columns; the trace-elements row's substance cell alone is 490 characters). | product owner, 2026-10-27 |
| **D70.2** | A **vision-model extraction of the printed table is the fallback**, not the plan: if the shape is judged insufficient at UAT, the model drafts the table and a human reviews it into `knowledge/tables.py`. Either way it is reviewed data — a model's output cannot become a `DocumentChunk` unreviewed, for the same reason `TABLE_ROWS` was reviewed. | product owner, 2026-10-27 |
| **D70.3** | An in-text reference to a section, an appendix or a glossary term is a **link that opens in a new tab** (`target="_blank" rel="noopener"`, with a visually-hidden "opens in a new tab"), exactly like a citation's "View this line" — the reader keeps the passage they were reading. | product owner, 2026-10-27 |
| **D70.4** | **Glossary links are in this slice**, from a reviewed term list, at most one link per term per passage. | product owner, 2026-10-27 |
| **D70.5** | The locator prints **once per run** — when it differs from the passage above it — and every passage keeps its `id`, so a citation still lands. | proposed here; §10 Q4 |

---

## 3. The table branch

### 3.1 Reviewed structure data

A new record in `knowledge/tables.py`, beside `TABLE_ROWS` and keyed the same way (a section
reference maps to structure; **another appendix needs data, not code**):

```python
@dataclass(frozen=True)
class TableDivider:
    before_row: int      # index into TABLE_ROWS[section_ref]
    text: str            # as printed: "II. MINERAL ORIGIN" -> shown as "II. Mineral origin"
    kind: str            # "part" | "qualifier"

@dataclass(frozen=True)
class TableSection:
    columns: tuple[str, str]     # the printed headers
    legend: str                  # one sentence, see §3.3
    dividers: tuple[TableDivider, ...]
```

Appendix 2's dividers, measured against the `-table` extraction on PDF pp. 77–79 (each is the line
immediately above the row it precedes — verified, not assumed: `scripts/probe_reader_structure.py`
walks the committed `-table` pages line by line and reports that every one of the seven is followed,
on the same page, by the row it names):

| before row | divider | kind |
|---:|---|---|
| 0 | `I. PLANT AND ANIMAL ORIGIN` | part |
| 1 | `South African specific` | qualifier |
| 3 | `South African specific` | qualifier |
| 14 | `South African specific` | qualifier |
| 15 | `II. MINERAL ORIGIN` | part |
| 26 | `III. MICROBIOLOGICAL` | part |
| 28 | `IV. OTHERS` | part |

A test asserts each divider string appears **on the printed page that holds the row it precedes** (in
the `layout` or `table` extraction), and that the row index it names holds the substance printed
below it — the same "necessary and applied" idiom as `CORPUS_EDITS`, so a reprint fails loudly rather
than drifting.

### 3.2 The blocks

`passage_blocks()` is untouched. A **new function** in the same module, for a chunk that is a
reviewed row:

| Function | In | Out |
|---|---|---|
| `row_blocks(text)` | one row's stored text (`substance\ncondition`, paragraphs of the condition separated by a blank line — `TableRow.text`) | `(RowHeading, Paragraph…)` |

* the first line is a **`RowHeading`** (new block kind, `kind="row"`), so a substance reads as an
  entry whether or not it has a condition — which fixes `Guano` rendering at body weight;
* the condition is split on **blank lines only in a row**, because `TableRow.text` puts them there on
  purpose; the double-spaced-body rule that keeps `passage_blocks` from splitting SAOSO's prose never
  applies to a curated row;
* an empty condition yields **no paragraph at all** (silence is not permission — the reader may not
  invent a condition);
* `flatten()` already includes any block with `.text`, so the lossless guard covers it unchanged. A
  guard asserts `flatten(row_blocks(text)) == text` over all 30 rows of the real corpus.

`RowHeading` is deliberately *not* a `Term`: a term is a glossary headword, a row heading is a table
entry, and they need different weight in the design system.

### 3.3 What the branch renders

Above the rows, once:

* the printed column headers, joined as a caption: *"Substances — description, compositional
  requirements · Conditions for use"*;
* one legend sentence, the sentence that answers "why is this a list of inputs": *"The standard prints
  this appendix as a table: each entry is a substance and the condition printed beside it. Where it
  prints no condition, nothing is permitted by its silence."*

Then, per row: the divider when one precedes it (a printed part heading renders at the `passage__heading`
weight, a qualifier at the term weight — both are quoted text with a shape, not page headings), then
the row's `RowHeading`, then its condition paragraphs, and — where the paper's condition cell is
empty — a **muted inline label** `no condition printed`, in the row's own meta line rather than as a
sentence (19 sentences would be noise; 19 labels are scannable).

No `id` on a divider: it carries no text the standard numbers, so it is not citable.

### 3.4 What this does not do

* **It does not re-split the table into columns.** A two-column grid at 38 rem cannot hold these
  cells; the definition-list shape is the reading order the paper implies.
* **It does not touch Appendices 1, 3, 4.1, 4.2, 5, 6a, 6b or 7.** They are not curated rows, they
  have no reviewed structure, and inventing one from `-table` output would be unreviewed data. The
  accessor returns nothing for them and the reader behaves exactly as today.
* **It does not change the tree.** Appendix 2 stays one branch; its sub-tables are not child rows.

---

## 4. References

### 4.1 The index — derived, not stored

A new module, `knowledge/references.py`, builds an index from what the document already says about
itself:

* **part aliases** from `StandardDocument.toc`: `(part, label)` → the branch the TOC entry matched
  (`build_concordance` already does that join for the tree);
* **section aliases** from each branch's key and printed title (`S5` → `Section 5`, `5. Animal
  Husbandry`);
* **appendix aliases** from each branch's key and printed title (`Appendix 6b` → *Minimum Surface
  Areas Indoors and Outdoors…*).

Nothing is added to the database, and nothing is guessed. A document with **no TOC has no parts**, so
an unqualified `Section n` is undecidable there and stays text; the BPP's and the landscape's only
references (`Appendix 5`, `Appendix 9`) name branches neither document has, so those two documents
produce **no links at all** — the correct behaviour, and a useful negative control.

### 4.2 Resolution rules

| Printed shape | Rule | Example |
|---|---|---|
| `Section <part>` + separator + `n` | **part B** → branch `S<n>`; **part A** → the tree's "printed sections not in the corpus" note; any other letter → no link | `Section B – 5` → `S5` |
| `Section n` with **no** part letter | the part of the branch the passage is printed in (from its TOC entry); no TOC, or a part with no corpus → no link | `Section 4.6.2` → `S4` |
| `Appendix n` + letter | that branch, if it exists | `Appendix 6a` → `Appendix 6a` |
| `Appendix n`, one branch | that branch | `Appendix 3` |
| `Appendix n`, several branches | match the words printed after the number against the branches' titles; still ambiguous → **no link** | `Appendix 6 Minimum Surface Areas…` → `6b`; bare `Appendix 4` → none |
| a reference to the **open** branch | no link (it is a no-op) | measured by the probe: **0 today** |

The separator between `Section B` and its number is whatever the paper prints — an en dash today
(D69), a hyphen in the OPP, possibly a colon in a reprint — so the pattern accepts punctuation
rather than a literal. Every rule therefore resolves to a **branch that exists in the tree**, or to
nothing: the index is built from the concordance, so a link cannot point at a branch the page does
not render.

### 4.3 Segments, not HTML

A reference is a **segment**, built at the display layer:

```python
@dataclass(frozen=True)
class Segment:
    text: str
    href: str = ""       # "" -> plain text, never a dead link
    title: str = ""      # the branch title, for the tooltip
```

`with_references(blocks, index)` returns the same block types with their `segments` filled, so
`_passage_blocks.html` renders `{% for segment in block.segments %}` and escapes each part itself —
the same reason `SearchHit` carries `before`/`hit`/`after` rather than markup. `flatten()` keeps
reading `.text`, so the quote is untouched; a test asserts that joining a block's segments
reproduces its text exactly.

No reference is looked for inside a `Term` or a `Heading`: a glossary headword is not a sentence, and
a printed heading (`1. DEFINITIONS`) is the document naming itself.

### 4.4 The missing-section target

`Section A – 2.3` must go somewhere. The tree already prints *"Printed sections not in the corpus,
and so not shown here: 1. Introduction…, Appendix A…"*; that note gets `id="not-in-corpus"`, and a
Part A reference links to it with the title *"Section A is printed but not in this corpus"*. A link
that explains itself beats a dead span, and it is the same claim-discipline rule the page already
follows.

---

## 5. Glossary links

### 5.1 The term list is reviewed data

`knowledge/glossary.py` (new, the same idiom as `tables.py` and `REVIEWED_BRANCH_TITLES`):

```python
GLOSSARY: dict[str, tuple[str, ...]] = {
    "saoso-version-2.1-2026.pdf": ("ACB", "Buffer Zone", "Conversion Period", …),
}
```

Populated **once** by a probe over `S1`'s `Term` blocks, then read and corrected by a human — because
the measured heuristic list contains `Soil`, `Breeding` and `Synthetic`, and a wrong entry is a
wrong link on every page. A test pins the ratio: every entry must occur as a `Term` in `S1`, and
every term's definition paragraph must be found in `S1`'s text (so a stale entry fails).

### 5.2 Matching

* case-insensitive, whole words (`(?<![A-Za-z])…(?![A-Za-z])`), longest term first so `Conversion
  Period` wins over `Conversion`;
* **at most one link per term per passage** — the first occurrence — so `Soil` ×19 in a branch
  cannot become nineteen links;
* paragraphs and list items only (never a `RowHeading`, `Term` or `Heading`);
* the target is the passage in `S1` whose text begins with that term, resolved through the reader's
  own anchors, so a definition link lands on the definition and never on the branch's top.

---

## 6. Non-goals

* **Not an ingest change.** No `DocumentChunk` edit, no artefact edit, no `--force` re-ingest. The
  `\ufffd` class of problem is D69's; this slice must not create a second place where text is
  repaired.
* **Not bare clause numbers.** `5.3, 5.5, 5.6` inside the `Section B – 5 Animal Husbandry` sentence,
  and `clause 22.1.3.` after `Section 22 Labelling`, stay plain text. A number with no section word
  has no target that can be decided, and a guessed clause is worse than a dead one. (`Section n`
  *with* the word is decided — §4.2.)
* **Not a PDF page link.** D67 stands: the served file is an attachment, so `#page=` has nowhere to
  land.
* **Not a tooltip library, no JavaScript.** `title` and a visually-hidden suffix only
  (`build_principles.md` §IV).
* **Not the tree's shape.** No sub-branches, no collapse state, no per-row entries in the contents
  list (D68's tree is the printed table of contents).

---

## 7. Risks

| Risk | Guard |
|---|---|
| A restored divider is wrong or stale after a reprint | A test asserts each divider is on the printed page above the row it names, both ways |
| A row's substance is swallowed into its condition | `flatten(row_blocks(text)) == text` over all 30 real rows, in the gate |
| The reader invents a condition for an empty cell | `row_blocks` emits no paragraph; the page prints a label, and a test pins the label's wording to the legend's claim |
| A reference sends a reader to the wrong part | `Section A – 2.3` is a pinned test: it must resolve to the missing note, never to `S2` |
| A wrong link appears in a document we did not review | The index is built from the concordance and the TOC only; measured: BPP and landscape produce none |
| A quote stops being quotable | Segments are display-only; joining them reproduces the text; the audit reads `DocumentChunk` |
| The appendix page gets heavier | Measured before/after in the plan: Appendix 2 renders 30 rows of already-fetched chunks, one query |
| A glossary entry is wrong on every page | Reviewed data with a "must be a `Term` in `S1`" test, and one link per term per passage |

---

## 8. Test surface

| New test | What it proves |
|---|---|
| `knowledge/tests/test_table_sections.py` | dividers are printed on their pages, in order, above the right rows; the column headers are the page's; the legend's claim and the empty-cell label agree |
| `knowledge/tests/test_row_blocks.py` | row shape (heading + paragraphs), empty condition, lossless over the 30 real rows |
| `knowledge/tests/test_references.py` | the inventory above; the part-letter trap; the unqualified `Section 4.6.2` → `S4`, and no link for it in a document with no TOC; `Appendix 6` → `6b` by title; bare `Appendix 4` → no link; a reference to the open branch → no link; segments reproduce the text; no link without a target |
| `knowledge/tests/test_glossary.py` | every entry is a `Term` in `S1`; first-occurrence-only; longest-first; no link inside a heading |
| `core/tests/test_document_reader.py` (extend) | one locator per run; dividers and legend render on Appendix 2; a cross-reference is an `<a target="_blank" rel="noopener">` whose `href` is a branch in the tree |
| `scripts/probe_reader_structure.py` | prints the three measurements above before Task 1 and after it lands: the table's rows, empty cells, locator runs and divider adjacency against the printed pages; the reference inventory with its resolution and ambiguity; the glossary candidates with their frequency. It is **in the tree already** — every number in this PRD is its output, so the plan's numbers are the corpus's and not a recollection. |

## 9. UAT impact

`tests/uat/concordance_uat.md` gains three scenarios, each a judgement and not a check:

* **Scenario 9 — the appendix reads as the paper's table.** Open Appendix 2: does each substance
  read as an entry with its condition, do the four parts and the `South African specific` dividers
  put the repeated *Farmyard manure* row in context, and does a row with no condition read as the
  paper's silence rather than as a permission?
* **Scenario 10 — a reference goes somewhere.** Follow `See Section B – Appendix 6` from Appendix 2
  and `Section B – 1 Definitions` from Appendix 1 (new tab each time), then `Section A – 2.3` from
  `S22.1.7` and the unqualified `Section 4.6.2` from `S6.1`: does each land on what the sentence
  meant, and does the Part A one explain itself?
* **Scenario 11 — a definition is a click away.** From a clause that uses `ACB`, `Habitat`,
  `Extensive Farming` or `Conversion Period`, follow the term: does it land on the definition, and
  does the page read normally with the links in it (not link-studded)?

## 10. Open, to settle in review

1. **The empty-condition label.** Recommend a muted `no condition printed` in the row's meta line
   (scannable, 19 of them) plus the legend sentence, rather than 19 sentences. Is the label's wording
   acceptable on a public page?
2. **Bare `Appendix 4` (8 mentions).** Recommend **plain text with a `title` naming both tables**
   ("Appendix 4 has two tables: …") rather than guessing Table 1. Agreed?
3. **Glossary scope.** The list will be short (probably 25–45 terms). Do you want to review it in this
   slice, or ship §3–§4 now and glossary links as a follow-up?
4. **Once-per-run locators** (D70.5). The `id` stays, so nothing breaks; the visible cost is that a
   reader who scrolls into the middle of `S5` no longer sees `S5 · printed p. 41` above every clause.
   Acceptable?
