## 0x. 2026-11-02 (session 10) — G11 answered, and two of its three slices landed

**What was asked.** Three things in sequence, each from the previous session's queue: choose between
G11's options, build the chosen option's first slice, then its second.

**What was decided.** **D79 = E** — show the table as structure, quote cells only, render the row's
context from the artefact at cite time. Recorded in `PGS_PLATFORM_SPEC.md` §18.3 in 1 437 bytes
(inside the 1.5 KB row budget, so it does not join the 14 rows cut 4.2 still has to shrink). **A was
not built**, so its repetition never has to be deleted later. The mechanism is taught in
`product/design/g11_option_e_explainer.html` — built because the owner said, of the one-line
description, *"i'm not following"*, and it turned out the explanation needed six frames and three
layers, not a paragraph.

**What the explainer found that the decision page had not.** The reader already resolves a clause to
its reviewed table: `artefact_grid_for` + `align_artefact_grid`, and `_documents.py:640`'s own
comment records that **§2.3 already works through that path**. So E's infrastructure mostly existed;
what was missing was the prompt shape, a row identity, and a difference the UI could show.

### Slice 1 — the reserved seat (`9608656`)

Two defects, both measured before the code was touched:

1. **The seats were filled from the fused head**, and `search_terms` asked the fused arm for `limit`
   chunks. A chunk only the vector arm found scores `1/(60+rank)`, so it lost to every chunk the
   lexical arm also matched: the OPP's fee band (vector rank 4, in no lexical ranking) ranked 15th
   fused and could never be seated. Filling in fused order is the same defect one step later — the
   lexical arm, which the seat exists to bypass, still chose.
2. **A heading could take a seat.** `II. Membership fees, farm assessment fees, licensing fees` is
   57 characters with no body and takes vector rank 1 for any fee question by naming every fee the
   document charges. 60 of 401 chunks are this shape. `is_heading_only` disqualifies them — on
   text-equals-its-own-heading **and** no terminal punctuation, because text equality alone would
   have disqualified 56 real SAOSO one-sentence rules.

Measured on one corpus, before/after (`RETRIEVAL_EVAL_SPIKE.md` §8b): R@8 **0.812 → 0.812**, MRR
0.387 → 0.385, R@5 0.688 → 0.719; `curated-unannounced-visit` **not found → rank 3**, and
`curated-conversion-period` **rank 7 → not found**. A third design (vector-only chunks first) scored
R@8 0.750 and is recorded as **rejected**, so it is not re-proposed as an obvious improvement.

**The correction that mattered.** The first commit said the fee band "is in the eight passages for the
first time". The live probe said otherwise: without the `?` the band is rank 8; *with* it the lead-in
takes vector rank 4 and the band is out; on a third phrasing the ranks reorder entirely. `16c2b2a`
corrects it. The capability claim survived (before the fix no rule could have seated a band); the
product claim did not — and it changed slice 2's design, from "a bigger reservation" to "the unit is
the table". This is `g11` Part 4's warning — *no similarity ranking chooses a band* — confirmed
empirically.

### Slice 2 — the table, and the row's label (`64f70ae`)

- `knowledge/table_context.py` (new): a passage learns its reviewed table — a **row** by its cells, the
  **introduction** by its section. The introduction is the trigger, because it is the passage
  retrieval actually finds and it names none of the numbers.
- `search_terms` appends the table's rows **after** the hits (`TABLE_ROW_SEATS = 8`), so no rank moves
  and `eval_retrieval` is unchanged — verified identical. `layout: process` tables are excluded: their
  rows are already readable passages (`D77`), and including the landscape's step table grew the fee
  prompt to 11 969 characters and made three of eight added rows puzzles.
- `build_prompt` renders each table once: `TABLE:` line, the printed headings, rows one cell per line.
  The headings are never inside a row's text, so **the audit needed no new rule**.
- `Citation.row_label`, rendered as **context** (dashed rule, muted) in both citation templates.

**Measured live**, on the two phrasings slice 1 could not answer: *"…below R250,000 would pay a
renewal fee of **R900**"* and *"…an initial certification fee of **R1,500** or a renewal fee of
**R900**"*. Both grounded, quoting single cells.

**The refusal that earned `d79-2`.** The first live run quoted `Below R 250,000 900` — label and
renewal fee, skipping the initial fee between them — and the audit refused the whole answer,
correctly, for a rule the prompt had not stated. The rule now states it: cells are quotable together
only when consecutive. Worth remembering the shape: **a prompt that shows structure creates new ways
to quote wrongly**, and the audit is the only thing that catches it.

### What this session cost, and what it should be remembered for

Roughly two thirds of the tool calls were measurement, not editing — and three of those measurements
changed a decision that looked settled (the `?` flipping the band, the process table polluting the
prompt, the non-contiguous quote). The pattern worth keeping: **implement, then measure the thing the
implementation claims, on the surface the claim is about**; two of the three findings came from
`probe_chat.py`, not from the suite.

### What is left

- **Slice 3** — the *context, not quotation* distinction as a design pass (`DESIGN.md` governs). The
  dashed "Table row:" line shipped is the minimum that stops a bare `900` reading as a non-answer.
  UAT scenario 8 of `tests/uat/ask_surface_uat.md` is written for exactly this judgement, and D79's
  fallback to A is on record if the distinction cannot be made legible.
- **`g12`/D80** — starting with the eight-shape fixture set, which is D80's first commit.
- The landscape UAT sign-off, still the only thing keeping `LANDSCAPE_TABLES_PRD` out of `Done/`.

### Gate

`scripts/verify.sh` **1580 passed, 1 skipped in 73.57 s** (`--create-db`,
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify`, idle box). `scripts/fast.sh`
**1565 passed, 1 skipped in 103 s** warm; `--critical` **213 passed, 4 deselected in 18.4 s**;
`pytest tests/e2e` **71 passed in 135 s**. Five new guards, each proved by breaking it and watching
it go red — the two seat tests, the table-travel tests, and the prompt-shape test.
