# Session 1o — 2026-11-05 — the re-score, and a judgement surface that taught us to put both sides on screen

**Task.** Re-score the three extractor arms against the answer key the owner had just signed, then
take it from there.

**Outcome.** S2 is **closed**. D82 is answered — not as "which extractor", but as a **composite**:
Layout Parser for structure, the page's own text layer for characters, Docling for Appendix 7's four
columns, the VLM `lines` form as a cheap proposer, S4's harness for the verdict. Three commits.

## 1. The re-score: one claim was worth a shape (PRD §3.12)

Two arms replayed from the committed raw responses — **no credential, no network, no spend**. Docling
has no response cache, so it was re-run in its venv (**545 s**, `long_cell` 85.8 s of it).

| Arm | Before | After |
|---|---|---|
| Docling 2.146.0 | 0/8 + 2 conventions | **identical, 0 of 8 shapes changed** |
| Document AI Form Parser v2.1 | 1/8 | 1/8, same verdict, sharper reason (fails `contains`, not `starts`) |
| Document AI Layout Parser v1.6-pro | 2/8 | **3/8** — `long_cell` passes outright |
| VLM sonnet `lines` | 2 + gutter + 1 grid-only | 2 + gutter + **2** grid-only (11 cells unconfirmed) |
| VLM flash-lite `lines` | 1 + 3 grid-only | 1 + **4** grid-only |

`6 of 72` combos moved, all on `long_cell`, one line each. The cause was the owner's own amendment in
session `1n`: `Cell(0,0, starts="Step 3")`. So the scoreboard is a property of the key as much as of the
arms, and **§3.8's "the three it would still lose are the three no general extractor returns" was wrong
about the long cell** — that one was ours. The union of shapes any arm passes went **4 → 5 of 8**.

## 2. The thread: three shapes, three causes, and one of them was the instrument

Arbitrated against `knowledge/corpus/landscape.md` (our reviewed artefact) and the committed passes:

* `headerless_values` — the four printed header lines, all four arms merging column 0's two labels;
  our key keeping only the second. **Looked like our defect** — and the owner kept the claim (§3.13),
  so it is **the tools'**. §3.12's guess is withdrawn; the union stays 5 of 8.
* `empty_cells` — **genuinely the tools**: the artefact's legend says the fee box spans Steps 1–2 and
  is filed under Step 1, so `R500` is in cell 0,4 and cell 1,4 is empty. Every arm splits the box.
* `page_break_row` — **our committed pass**: both VLMs score 0 mismatches and are demoted by quotes
  "out of printed order on page 5", because page 5's `-table` pass interleaves three columns per line.
  "Our pass cannot order this page" is not "the model's characters are unverified" — still open.

## 3. The arbitration instrument, and the hour it cost

Built `scripts/shape_disputes.py` (attributes each arm's mismatch line to the claim it is about, on the
guttered reading, never counting a passing arm as disagreeing) and `scripts/shape_arbitration.py`
(10–11 cards, page image, the key's anchors, every arm's line, keep/amend/can't tell, export →
`shape_review_signoff.py --amend`, which refuses unless the fixture already says the text judged).

Two defects in it were mine and both were caught by my own guards rather than by the reviewer:

* the data payload was HTML-escaped, so the page's script **threw on load** and every tooling test
  stayed green — `testing_hazards.md` §1.30 exactly. Six browser tests now drive the page.
* the first attribution read `as_extracted` and reported **five arms disagreeing on Appendix 7**, a
  shape two of them pass, because the gutter is a declared normalisation. Fixed and tested.

**Then the real finding, which is not about code.** The owner's eleven verdicts came back and **four
were caused by the layout**: the page showed only a shape's *first* page (so `page_break_row`'s third
row, printed on page 5, was simply absent), it never showed the claim's own cell (`R500` is far down
inside a tall merged box at page scale), it did not state decisions the record already made (the fee
box rule, the seal-label rule, the step-label rule), and its amendment box accepted a pasted **arm
report** as claim text. His words: *"I can't figure out what you need from me"* — now **hard rule 9**
in `pgs-presenting-uat`: a judgement is a comparison, so both sides share the screen, every page the
item is printed on, and a full-size view one click away.

## 4. The decision, in the owner's words

*"We take our best options from each."* Recorded as §3.14: the arms do not compete on one axis.
Structure from the Layout Parser (8/8 tables found, the only arm that reads the long cell), characters
from the page's text layer (every extractor misreads something), Appendix 7's de-interleaving from
Docling (free, local, and right all along), a cheap proposer from the VLM, and the verdict from S4's
harness. **No credential buys the semantic half** — which is why the union stops at 5 of 8 whatever is
spent, and why S5 (review 6a and 7 through the harness) is what is left, with S3 emitting the blocks.

## 5. Hazards written down

* **`testing_hazards.md` §3.31** — an evidence file's clip is not the read: four sampled rows, cells
  clipped at 200 characters. A probe that read it as the read accused all five arms of dropping the
  last row; the arms had `rows_found: 20`.
* The gate's first step scans the **working tree**, so another session's 31 KB `scripts/copy_deck.py`
  fails it while a clean checkout of HEAD reports 0 breaches. Check before believing a red gate.

## 6. What is next

S3 (emit the blocks, record the extraction mode on the artefact) and S5 (re-review Appendix 6a's 20
rows and Appendix 7 through the harness). Seven arbitration claims are unjudged and **no longer gate
anything**; the two that mattered are settled. R3's verdict wording still needs the fix that stops "our
pass cannot order this page" being scored as "the model is wrong".
