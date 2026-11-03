# Bug: a Fee cell reads "As above", and on a deep link there is nothing above

**Status:** **Open** — found by the product owner while signing the landscape UAT, 2026-11-01
(`tests/uat/landscape_tables_uat.md` Scenario 4). The page was **accepted as is**; this records the
defect so it is carried by name rather than in chat. Fix is a **legend** edit in the artefact
header, not a cell edit, and needs **no re-ingest**.
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

## 4. The repair to make, when it is scheduled

- Name the referent in the legend: the branch (`ESTABLISHING A PGS GROUP`) and what the fee buys
  (the recommended annual sticker fee, paid per farmer, split 30% PGS SA / 70% group) — still
  inside the paper's own sentence, so D72.2 holds.
- Make it reachable: a link to `?section=establishing-a-pgs-group` if the legend renderer allows
  markup, or an anchor name the reader can search. If neither is possible without new rendering,
  say so and stop — a legend that names the branch is still a large improvement on "the previous
  table".
- Re-present Scenario 4 and re-judge only that card; do not re-sign the other five.

## 5. The UAT gap this exposed

No scenario asked this question. Scenario 1 is the fee question, scoped to the *establishing a PGS
group* branch; Scenario 4 is legibility and resizing; Scenario 6 is claims. The seals table's Fee
column sat between all three. When this is fixed, the re-judged card should ask it directly: *does
every fee cell on every branch either state what the money buys, or point somewhere you can get
to?* — and `writing-uat-tests` should decide whether that belongs to Scenario 1 or 4 rather than
adding a seventh.
