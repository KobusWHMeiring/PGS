# Session `1i` — the verification surface, and 68 claims the owner has not judged yet

**Date:** 2026-11-05
**PRD:** `product/backlog/In Progress/INGESTION_ENGINE_PRD.md` — §3.10's gate, now §3.11
**Artefact:** `product/design/uat/shape_key_review.html` (generated; 2.3 MB, seven page images inline)
**Instruments:** `scripts/shape_review.py` (CLI), `scripts/shape_claims.py` (the model),
`scripts/shape_review_page.py` (markup), `scripts/shape_review_template.py` (CSS + script),
`scripts/shape_review_signoff.py`, `scripts/render_shape_pages.py`, `knowledge/tests/shape_pages.py`
**Tests:** `tests/tools/test_shape_review.py` (16), `tests/e2e/test_shape_review_artefact.py` (6)

## 1. The question this session was handed

§3.10 ended with an order of work: **build the verification surface** — each shape's page image
beside the expected grid, cell by cell, judged by the owner — and only then re-score the three arms,
which is free because every raw answer is cached. The reason was blunt: the key that scores every
extractor (`knowledge/tests/shape_fixtures.py`, commit `5c45550`) was written by an agent, the one
signed UAT judged how tables *read* rather than whether a cell's characters are what the paper prints,
and three independent readers disagree with the key on the same judgement shapes. A ranking built on
an unreviewed key is a ranking of the arms against our own convention.

So this session built the instrument, and did not judge a single cell. The signature is the owner's;
that is the whole point of the page.

## 2. What was built, and the four decisions in it

**The paper, not a redrawing of it.** Each shape shows the page rendered from the committed PDF at
170 dpi (a 9 pt table line is ~21 px, legible at fit width and at 100% in the zoom dialog), beside the
grid the key expects. The renders are committed and pinned twice — the PDF's sha256 and the JPEG's —
in `knowledge/tests/fixtures/shape_pages/MANIFEST.json`, and read through
`knowledge/tests/shape_pages.py`, which refuses a swapped PDF *and* an edited image. `pypdfium2` is
imported inside `scripts/render_shape_pages.py` and nowhere else, so requirement 10 stays true: the
gate needs no rasterizer.

**One self-contained file, with the images inline as `data:` URIs.** The UAT skill's rule is that the
artefact opens from disk with the wifi off; a page image that is a file beside the HTML is a page image
that goes missing the first time someone emails it. The cost is a 2.3 MB HTML file, which is smaller
than the PDFs it was rendered from.

**A claim per thing the key asserts, not per cell on the page.** 8 shapes, **68 claims**, of which
**41 are cells**. The eight pages print roughly 60 cells inside the shapes' own columns, so the grid
draws the cells the key does not assert as `—` and says so in words. That asymmetry is a finding in
itself and it belongs on the page, not in a footnote: a reviewer who cannot see how thin the key is
cannot judge it.

**The claim's text is what a signature pins.** `scripts/shape_review_signoff.py` writes
`knowledge/tests/shape_review.json` with, for every claim, the `expected` line it was judged against.
Change `shape_fixtures.py` afterwards and `--check` — and the gate's test — names the claim and says
the review is stale. A signature that survives the thing it signed is worse than no signature.

The `No` verb does not touch the fixtures. The record is evidence; amending the key is a separate,
reviewable edit made after reading it.

## 3. What is measured, and what is not

| Fact | Value |
|---|---|
| Shapes on the surface | 8 |
| Claims | **68** — 8 headers, 8 row counts, 8 row-page claims, 3 dividers, **41 cells** |
| Cells the eight pages print in those columns | ~60 |
| Page images | 7, 1.6 MB total, both hashes pinned |
| Artefact | 2.3 MB, no network, no external file |
| Cells judged | **0** |
| Arms re-scored | none — deliberately, see §3.10 |

The surface itself also counts claims per shape, which is the first honest answer to "how much of the
paper does the key actually assert?" — it is 41 cells over eight pages, not every cell.

## 4. Guards, and the proof each one can fail

Every guard was broken and watched red before it was trusted:

| Guard | How it was broken | Result |
|---|---|---|
| Claim coverage on the page | generator emits only the first two cell claims per shape | red — count mismatch, and `--check` names the artefact stale |
| Artefact is generated, never hand-edited | same mutation | red — `--check` |
| Drift: a signature cannot outlive its key | `drift()` returns `[]` | red — the stale-record test |
| An export cannot carry a bare `No` | validator's reason check disabled | red — the refusal test |
| Images are the pinned paper | one byte flipped inside `opp_p2.jpg` | red — provenance assertion |
| The page's script parses and runs | the IIFE's closing brace removed | red — the browser test, `errors != []` |
| The page is complete without JavaScript | counted with `java_script_enabled=False` | green — 68 claims, 9 figures |

Timings on this box: `tests/tools` **233 passed / 1 skipped in 16.8 s** (the skip is the "no record
yet" guard), the six browser tests **16.4 s**, `render_shape_pages.py --check` **0 problems**.

## 5. What the next session does

1. **The owner judges** `product/design/uat/shape_key_review.html` — 68 verdicts, autosaved, export
   one JSON file.
2. `python scripts/shape_review_signoff.py --from <export> --dry-run`, read the diff, then run it
   without `--dry-run`.
3. Read the `No`s: each is a claim the paper contradicts, with the reviewer's words. Amending
   `shape_fixtures.py` is then a deliberate edit; the four arms are re-scored from cache after it.
4. Only then D82 (which extractor) has evidence under it.

## 6. What this session changed its mind about

Nothing was overturned. Two things were sharper than the plan:

- **The surface had to show what the key leaves out.** The brief said "the expected grid"; the key
  has no row text for most rows, so a grid drawn only from claims would have looked like a nearly
  empty table and implied the key was wrong everywhere. Drawing the unclaimed cells as unclaimed is
  the honest form, and it is the same distinction requirement 5 makes about empty cells: silence is
  data, not absence.
- **And "unclaimed" had to be said in words.** The first version drew it as `—`, and the owner's
  first reading of the page was *"am I expecting the cells below 'Below R 250,000' to be empty?"* —
  the paper prints 2,500 / 3,000 / 3,700 / 5,000 there; the key asserts none of it. A glyph that can
  be read as "blank" on a page whose whole job is teaching the difference between blank and unasserted
  is a defect, not a style choice. The cells now say `not claimed`, hatched, with the legend spelling
  it out, and a test pins the wording (broken by hand-editing the artefact back to a dash, watched
  red).
- **`pgs-presenting-uat` is the right discipline but not the right file format.** Its console,
  runner and sign-off all assume one scenario per judgement, with a `Judgement:` clause; this page
  needs 68 cell-level verdicts against images, and the runner cannot carry an image without an
  `src=`. So the disciplines were carried over (no network, autosave, refuse a blank, refuse a
  reasonless `No`, record what it was signed against, prove the script runs in a browser) and the
  artefact is generated the way the UAT artefacts are — not a `tests/uat/<slug>.md`, which would have
  been a second, weaker copy.

**Owed, unchanged:** the deploy from `HANDOVER.md` (five commits from session `1h`, plus this one),
and the arms' re-score after the signature.

## 7. The first signature, and the three notes it left

Kobus judged the page the same day (seat *Product*): **68 of 68 claims Yes**, three page notes.
`scripts/shape_review_signoff.py` wrote `knowledge/tests/shape_review.json` — every claim pinned to
the text he judged — and the summary reports **5 shapes confirmed, 3 with an open question**, because
"every claim Yes but the reviewer asked *is this expected?*" is not a settled shape. That rule was
added after the fact: the first draft of `build_record()` would have printed "8 shapes confirmed" and
buried the only real finding.

| Note | Finding | Disposition |
|---|---|---|
| `long_cell`: "the first column does have a bolded **Step 3** … that doesn't appear on the right" | **The key is wrong.** The page *and* our reviewed `landscape.md` block both start that cell with `Step 3`; the fixture asserts it starts with "The group conducts farm visits and" | Amendment owed: `starts="Step 3", contains="The group conducts farm visits and"`. One line; it changes `expected`, so the signature must be re-signed in the same act |
| `empty_cells`: "not sure where the R500 comes from" | The claim is right — `R500` is in the same merged Fee box, under "Annual membership fee (paid by the PGS group to PGS SA)". The grid drew a `contains` claim as if it were the whole cell | Fixed: partial claims are drawn `… R500 …` |
| `page_break_row`: "we're missing loads of text … the cells don't just say the step name" | Right about the paper, wrong about the claim: they are `starts` prefixes. The grid showed `Step 1` as a bare value | Fixed: `Step 1 …`, plus a test that no partial claim is drawn as a whole cell |

**The lesson, stated once and worth carrying:** *a rendered claim is not the claim.* Three of this
page's first four defects were presentation — `—` read as "blank", a `contains` fragment read as the
cell, a prefix read as the cell — and each one produced a wrong judgement about correct data. What
made the difference was not a better glyph but a sentence: "not claimed", "the key makes no assertion
about that cell", "…" where the cell goes on. A judgement surface has to be read by someone who was
not in the room, so its ambiguity is a bug with a test, not a style choice.

Owed at close: the `Step 3` amendment + re-sign, then the three-arm re-score from cache (§3.10). The
gate is green with the signature in place (`--check`: 68 judged claims, 0 problems); the amendment is
deliberately *not* made here, because a key edit under a live signature is the owner's act, not the
agent's.
