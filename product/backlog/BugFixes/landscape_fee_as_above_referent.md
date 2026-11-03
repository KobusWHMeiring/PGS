# Bug: a Fee cell reads "As above", and on a deep link there is nothing above

**Status:** **Fixed 2026-11-03** — the legend now names the branch and the step instead of saying
"the previous table", so the pointer is followable from the contents tree. Two guards hold it
(`knowledge/tests/test_landscape_table_block.py::test_the_seals_fee_legend_says_where_as_above_points`,
`core/tests/test_document_reader_grid.py::test_the_seals_legend_names_where_as_above_points`), each
watched failing against the old wording first. **No re-ingest:** all **17 of 17** landscape chunk
texts are byte-identical before and after (measured, `_scratch` probe), because the legend is a table
*header* field and never enters a chunk — `corpus_check` reports landscape drift on the file hash
alone, which is the same state `LANDSCAPE_TABLES_PRD` §12f left it in and is cleared by a deliberate
`corpus_refresh --apply`, not by this fix.
**Severity:** **misleading, not wrong.** The transcription is faithful to the paper and the legend
already explains the cell; the failure is that on `?section=pgs-seals-and-their-use` the referent
is off-page and unreachable, so a reader arriving by deep link is told to look at something they
cannot see.
**Owner:** Build (the legend line in `knowledge/corpus/landscape.md` + the reader's legend
rendering) · Product (whether the page may name a fee the paper does not print *in that table*)
**Affected:** the landscape reader, `PGS SEALS AND THEIR USE` only — two Fee cells, both rows.
Retrieval, the chunk text, anchors, the citation audit and the stored artefact are untouched.
**Reference:** `knowledge/corpus/landscape.md` (the table's `legend:` line, `knowledge/tables.py`
legend parsing) · `core/templates/public/document_reader.html` (`p.reader__grid-legend`) ·
`product/backlog/Done/LANDSCAPE_TABLES_PRD.md` §12h · `PGS_PLATFORM_SPEC.md` §18.3 **D72.2**
(an amount is never published on its own)

---

## 1. What the paper prints

Printed p. 6, the `PGS SEALS AND THEIR USE` table, Fee column — `pdftotext -layout`:

```
PGS Organic In-Conversion   …   As above
PGS Organic                 …   As above
```

Both cells say `As above`, and there is no row above them *in that table*. The referent is the
previous table in the paper — the `ESTABLISHING A PGS GROUP` process table (`layout: process`),
whose **Step 3** fee cell prints:

> A newly established PGS group will have the following seals customised in the name of its PGS:
> • PGS Organic In-Conversion • PGS Organic
>
> Printing of seals is at own cost.
>
> Recommended annual fee for the use of stickers (paid by individual farmers):
> R350 [to be divided between PGS SA (30%) and PGS groups (70%) — the portion of the fee
> accruing to PGS SA should be paid when the PGS group renews its membership]

So the paper's own wording is the defect. **The artefact reproduces it faithfully** and declares
it in the table header:

```
legend: Each row is one seal. This table's “Seals and logos” column holds the seal's picture and
no text: … Both rows' Fee cell reads “As above”, which is the fee stated on the previous table.
```

## 2. What the reader does with it

The legend renders as `<p class="reader__grid-legend">`, immediately above
`div.reader__grid-wrap` — verified on the running instance, not inferred from the template. So the
page is not silent: a reader scrolling the document is told what "As above" means.

The gap is reach. `?section=pgs-seals-and-their-use` is a **deep link to that one branch**. On it:

- the previous table is not in view;
- "the previous table" is not a link and names no heading;
- and the reader has no way to know it is the `ESTABLISHING A PGS GROUP` branch's Step 3 fee cell.

A reader who arrived from the chatbot's citation or a search result hits exactly this case.

## 3. Why the fix is a legend, not a cell

Writing the amount into the cell is the obvious repair and is **forbidden twice over**:

1. **D72.2** — an amount is never published on its own. `R350` in a Fee cell, detached from the
   paper's sentence about stickers and the 30/70 split, is the exact failure that decision names.
2. **Scenario 6** — the page may not print a word the paper does not print. The cell text is the
   paper's; the legend is the artefact's declared, reviewer-visible voice, which is where a
   cross-reference belongs.

The legend is also the cheap surface: it lives in the artefact header, so changing it does not
alter the chunk text and needs **no re-ingest** — though it does move the artefact hash, which
`corpus_check` will report as landscape drift until the next `corpus_refresh --apply`.

## 4. The repair that was made

The legend now reads:

> … Both rows' Fee cell reads "As above", **and the fee it points at is not on this page**: it is
the one printed in **ESTABLISHING A PGS GROUP — Step 3's fee cell** — the recommended annual fee
for the use of stickers, paid by individual farmers and divided between PGS SA and the group.
**That branch is in the contents.**

What that does and does not do:

- **Names the branch and the step**, in the same words the contents tree prints, so a reader on the
deep link can find it. Verified on the running instance: `ESTABLISHING A PGS GROUP` appears twice
on the seals page — once in the tree, once in the legend.
- **Does not restate the amount.** `R350` would be an amount published on its own (D72.2) and a
number detached from the paper's sentence about stickers and the 30/70 split. The legend says what
the fee *buys* and who pays instead, which is what makes it findable rather than quotable.
- **Does not link.** The legend renders as `{{ reader.grid.legend }}` — autoescaped plain text, no
markup — so a link would need a renderer change. Naming the branch is enough: the tree is one
`<details>` away on the same page, and the name matches.

**What is left: the re-judge.** Scenario 4 must be judged again against this page — the card's
`Judgement:` clause is legibility and resizing, and the legend changed under it. Only that card;
the other five were signed on a page whose legend is unchanged elsewhere.

## 5. The UAT gap this exposed

No scenario asked this question. Scenario 1 is the fee question, scoped to the *establishing a PGS
group* branch; Scenario 4 is legibility and resizing; Scenario 6 is claims. The seals table's Fee
column sat between all three. The re-judged card should ask it directly: *does every fee cell on
every branch either state what the money buys, or point somewhere you can get to?* — and
`writing-uat-tests` should decide whether that belongs to Scenario 1 or 4 rather than adding a
seventh.
