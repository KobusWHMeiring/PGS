# Session `1h` — the VLM arm scores 2 of 8, and the failures move

**Date:** 2026-11-04
**PRD:** `product/backlog/In Progress/INGESTION_ENGINE_PRD.md` — S2b, the OpenRouter arm of §3.6
**Evidence:** `product/docs/evidence/2026-11-04_s2b_openrouter_scores.json`
**Instrument:** `scripts/eval_openrouter.py`, `tests/tools/test_eval_openrouter.py`

## 1. The question, and the rule that answers it

S2's first arm (Docling) scored **0 of 8** as extracted and triggered D81's threshold. §3.6 listed six
arms; the two cheapest need no new account. This session walked the OpenRouter one, because the
session shell already holds `OPENROUTER_API_KEY` and the instrument that scores an arm already
existed (`mismatches()`, S0's own).

The rule that makes a generative arm admissible at all is in §3.6: **a VLM writes the text it believes
it read**, so a cell must not be the model's prose. Requirement 3 is the gate — a cell that is not a
contiguous run of the page is a violation — and the model proposes the grid while the characters come
from an extraction pass.

That sentence has three readings, and the instrument implements all three rather than picking one:

| Form | The model returns | The characters come from |
|---|---|---|
| `lines` | each cell's printed lines, verbatim | the page, checked line by line |
| `anchors` | each cell's first and last words | the page, sliced between the anchors |
| `indices` | line numbers only | the page, by construction |

## 2. What was measured

Two models — `google/gemini-3.1-flash-lite` and `anthropic/claude-sonnet-5.5` — at `temperature: 0`,
200 dpi page images, one image per printed page of each shape. **48 calls, $0.55**, priced by the
provider per call rather than from a price list.

| Model | Form | Pass | Grid only | Tables found | Rows right | Columns right | Cost | Wall |
|---|---|---|---|---|---|---|---|---|
| flash-lite | `lines` | 1/8 | 2 | 8/8 | 7/8 | 8/8 | $0.012 | 39 s |
| flash-lite | `anchors` | **2/8** | 0 | 8/8 | 8/8 | 8/8 | $0.012 | 40 s |
| flash-lite | `indices` | 0/8 | 0 | 8/8 | 7/8 | 8/8 | $0.011 | 38 s |
| sonnet-5.5 | `lines` | **2/8** | 1 | 8/8 | 7/8 | 7/8 | $0.164 | 64 s |
| sonnet-5.5 | `anchors` | 1/8 | 0 | 8/8 | 7/8 | 7/8 | $0.148 | 55 s |
| sonnet-5.5 | `indices` | 0/8 | 0 | 7/8 | 7/8 | 7/8 | $0.199 | 84 s |

Against Docling: **0/8** as extracted, 1/8 with the row-0 convention, **6/8 tables found**, **0/8**
header association, 163–330 s. The VLM arm is **4–8× faster**, finds **every** table, and gets header
association right on nearly every shape. It is also **not better on the pass count** — 2 of 8 — and
the expensive model is not better than the cheap one.

Per shape, the best VLM cell against Docling:

| Shape | Docling | Best VLM | The failure |
|---|---|---|---|
| Numeric row (OPP) | pass* | pass | none — but `indices` fails it, see §3 |
| Header lost entirely (6a) | fail | fail | the two header labels merge into one column's label |
| Column-major (App 7) | fail | fail | the row number becomes an extra leading column; every cell shifts right |
| Very long cell (p5) | not detected | fail | over-includes 'Step 3', re-wraps the 1,112-char cell |
| Deliberate empty cell (p4) | fail | fail | the merged fee box is replicated into the row below; the seal's label is lost |
| Row across a page break | partly | grid only | 3 rows on pages 4/4/5 and 5 columns are right; the quotes do not resolve |
| Two-level qualifiers (App 2) | fail | **pass** | none — 11 rows and all three dividers |
| A picture in a cell (p6) | not detected | **pass** | none |

## 3. The finding that matters more than the score

**The arm's failures are no longer "the tool cannot see".** It sees: every table found, headers
associated, dividers proposed (which no layout model returns). What it cannot do is be trusted with
**characters** or with **where a cell ends** — and those are precisely the two things requirements 3
and 9 exist to refuse.

**And the blocking defect is ours, not the model's.** The `indices` form scores 0 of 8 because in
`-layout`/`-table` text **a printed line is a whole row**: `Below R 250,000 1,500 900` is one line, so
no set of line numbers can produce three cells from it. In `anchors` form the same defect shows from
the other side: on Appendix 7, where the pass interleaves four columns, **no cell has a contiguous run
on the page**, so every cell is a violation whatever the model does.

> **A VLM cannot repair an interleaved pass. It needs a row-structured one.**

So the only admissible form (`anchors`: boundaries from the model, characters from a checkable pass)
cannot be scored fairly until the engine has a pass with cell granularity — which is what S3 has to
build. That dependency was not visible from the PRD's prose; it is now measured.

## 4. Three instrument bugs, found by running it

Recorded because each one would have produced a false finding about the model:

1. **The de-spacing normalisation ate a space the page prints.** The first version collapsed every
   space between two single-character words, which turned `Above R 5,000,000` into `AboveR5,000,000`
   and scored a *correct* quote as a mismatch. Fixed by comparing whole strings with every space
   dropped on both sides (`despace`), which also made the letter-spaced Appendix 6a cell resolvable —
   and the normalisation is **reported per cell**, never applied silently.
2. **A global printed-order cursor failed 65 cells on Appendix 7.** A tall row's cells are interleaved
   in the extraction: the page prints line 1 of every column, then line 2 of every column, so a cell's
   second line comes *after* its neighbour's first. The rule that survives the paper is that every
   character of row *k* precedes every character of row *k+1* — **row bands**, with each cell's own
   lines ordered within the band.
3. **`indices` was designed before the pass was looked at.** It assumes a cell is a line range; it is
   not. The mode is kept, because its 0/8 *is* the finding in §3.

A fourth, false lead: `R 250,001 � R 500,000` looked like a U+FFFD in the committed page text. It was
the Windows console failing to encode the en dash. The page text is clean (`U+FFFD count on OPP p2:
0`); nothing was reported as a defect.

## 5. What was built

- `scripts/eval_openrouter.py` — three prompt forms, a per-cell contiguity resolver that declares its
  one normalisation, row-band ordering, a raw-response cache keyed by (model, shape, dpi, form) so a
  re-score needs no network call, and a JSON writer whose rows are sampled and clipped so the evidence
  file is 189 KB rather than 405 KB. It imports with **no key and no rasteriser**; `pypdfium2` lives in
  a throwaway venv, exactly as `docling` did — requirement 10 stays true.
- `tests/tools/test_eval_openrouter.py` — 17 tests. Three guards were broken and watched red: accept
  any quote (the paraphrase test fails), slice from the anchors instead of the page (the
  characters-came-from-the-page test fails), and drop the row banding (the above-the-band test fails).
- `product/docs/evidence/2026-11-04_s2b_openrouter_scores.json`, and its row in the evidence README.

## 6. What this does not say

One run per shape per cell, one day, one key. `temperature: 0` is not a promise of identical output
across providers, which is why the raw responses are cached and the numbers are regenerable offline.
Three prompt forms is a small space, and two of the failures that look most like model judgement
(`Proud member of`, `Step 3`) are boundary calls a human made in the fixtures and could reasonably make
differently.

## 7. Next

**Document AI** remains the ceiling candidate and still needs the owner's four things (GCP project,
billing, a processor, a service-account key) — a Gemini API key is not one of them. The cheap options
that need no account are a second local parser, and **`anchors` re-scored against a row-structured
pass**. Then S3, then S5. If no arm is wanted, D — hand-review the 24 chunks and write the debt down —
is the honest fallback.
