# UAT — The concordance (the reader becomes the document's own tree)

**Feature slug:** `concordance`
**PRD:** `product/backlog/In Progress/CONCORDANCE_PRD.md` · **Plan:** `CONCORDANCE_PLAN.md`
**Decision:** `PGS_PLATFORM_SPEC.md` §18.3 **D68** (eight answers, 2026-10-27)
**Argument:** `product/design/d68_concordance_open_questions.html`
**Status:** Drafted **before** implementation (shift-left); **unsigned** — the feature is built
and the gate is green, and this file is what a human still has to judge
**Date:** 2026-10-27

---

## Purpose

Per `build_principles.md` §VIII, **UAT holds only checks a human must judge.** Every scenario below
carries a `Judgement:` clause naming the human-only call. Anything a test, a grep or a query can
prove is in *Automated coverage* and is **not** shown to the reviewer: the tree's branch count, a
branch's title string, `aria-current`, the anchor a citation carries, the omission list, a 200 vs
404, and the page's weight are all asserted by the suite.

The surface is one page. It is judged on one thing: **does a reader who is not us arrive at the line
a citation quotes, know where they are, and see the document's real shape — including what the
corpus does not hold?**

---

## Pre-test setup

1. **Fix the local join first.** On this machine the `PublicDocument` rows hold absolute paths, so
   no citation resolves and the reader says "not published the text" for every document. Run
   `python manage.py publish_documents` before anything else. If the reader still shows no text,
   stop — a judgement against a half-seeded instance is not evidence.
2. Confirm the corpus: `python manage.py uat_seed --check`. It reports chunks and vectors per
   document. Expected: **SAOSO 338 / OPP 30 / BPP 9 / landscape 8 = 385**. SAOSO rose from 319 on
   2026-10-28 because the standard is now ingested from its reviewed artefact and Appendix 6a's
   twenty classes are twenty chunks; a different number means a different corpus, so check
   before judging anything below.
3. `python manage.py runserver`, then open `/documents/saoso-standard-v2.1/read/`.
4. Have an answer page with at least one citation to a substance row in **Appendix 2** — ask
   *"Can I use cardboard from my neighbour?"* if there is not one (needs `GEMINI_API_KEY`).
5. For Scenario 3: a real phone, or a browser narrowed to 390 px with a throttled connection.

---

## Automated coverage (NOT UAT — asserted by the suite)

| What | Where |
|---|---|
| The tree is one branch per printed section, passages accounted for, in document order | `knowledge/tests/test_concordance.py` |
| The three grouping rules: opening chunk, roman/double numbering, shared heading | `knowledge/tests/test_concordance.py` |
| A branch's title comes from the printed TOC, so `S1` is *Definitions* and Appendix 2 is *Fertilizers…* | `knowledge/tests/test_concordance.py` |
| The reserved range 10–19 renders as a row with no passages | `knowledge/tests/test_concordance.py` |
| The printed sections the corpus does not hold are reported, not guessed | `knowledge/tests/test_concordance.py` |
| Every passage's own anchor resolves to **that** passage, over all 366 real passages | `knowledge/tests/test_anchors.py` |
| A stored citation to a non-first Appendix 2 row opens that row | `core/tests/test_document_reader.py` |
| `?section=` accepts a branch anchor, a passage anchor, and an unknown value | `core/tests/test_document_reader.py` |
| Only the selected branch is rendered; a closed branch is not in the page | `core/tests/test_document_reader.py` |
| The citation says "View this line", opens a new tab, and announces it | `core/tests/test_document_reader.py` |
| Appendix 2's 19 empty conditions print the muted label, and the legend is one sentence | `knowledge/tests/test_table_sections.py`, `core/tests/test_document_reader.py` |
| Every row reads as an entry: a substance heading, then its condition paragraphs | `knowledge/tests/test_row_blocks.py`, `core/tests/test_document_reader.py` |
| The seven dividers sit above the rows the paper prints them above | `knowledge/tests/test_table_sections.py` |
| `Section A – 2.3` resolves to the missing-sections note and never to `S2`; bare `Appendix 4` and bare `Appendix 6` stay text | `knowledge/tests/test_references.py`, `core/tests/test_document_reader.py` |
| A reference is an `<a target="_blank" rel="noopener">` whose `href` is a branch in the tree, and the BPP and landscape render none | `core/tests/test_document_reader.py` |
| One locator per run (366 → 311), and every passage keeps its `id` | `knowledge/tests/test_reading.py`, `core/tests/test_document_reader.py` |
| A definition link lands on the definition's own `id`, once per term per passage | `knowledge/tests/test_glossary.py` |
| Per-branch `<title>` and `rel=canonical` | `core/tests/test_document_reader.py` |
| `<title>`/copy carries no forbidden claim term; the reader stays exempt for its recorded reason | `core/tests/test_claim_discipline.py` |
| Touch targets ≥44 px; the tree is not a horizontal scroll at 390 px | `core/tests/test_public.py`, `tests/e2e` |

---

## Scenario 1 — Arriving at the line

**Setup:** an approved answer page whose citation you have not yet followed. **Action:** follow
**View this line**.

**Expected:** the reader opens in a new tab, on the branch containing the quoted clause, with the
passage visibly marked, the tree showing that branch as the one you are in, and the answer page
still open behind it.

**Judgement:** *Does following the link feel like arriving at the clause itself — can you put your
finger on the sentence you just read in the answer — or does it feel like being dropped near it?*
And, with the tab open: *is it obvious the answer is still there, or did opening a tab lose the
reader's place?* A yes to the first and a no to the second is a pass.
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 2 — A substance row, not the first row

**Setup:** the cardboard answer, whose citation is a row deep inside Appendix 2.
**Action:** follow **View this line**.

**Expected:** the Appendix 2 branch, and the passage that carries the quoted row — *not* the
appendix's first row ("Farmyard manure, slurry and urine").

**Judgement:** *Without scrolling away from the quoted text, can you confirm the quote on the page
in front of you?* This is the check that separates a real locator from a link that lands in the right
neighbourhood; a reader who has to hunt through 30 rows to find the row they were quoted will not
trust the next citation.
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 3 — 390 px, in a farm office

**Setup:** 390 px wide, slow connection. **Action:** open the SAOSO concordance with no `?section=`,
then open it again from a citation.

**Expected:** the text of a clause is on screen first, with the tree collapsed to the current branch
behind a control; tapping that control shows all 22 branches; choosing one loads that branch.

**Judgement:** *On a phone, is the clause the first thing you can read, and is finding another
section an obvious action rather than a hunt?* Then, throttled: *does a branch arrive quickly enough
that a reader would wait for a second one?* Layout and speed at width are judgements; the absence of
a horizontal scroll is measured and not your problem.
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 4 — The shape of the standard

**Setup:** hand the screen to someone who has never opened the SAOSO PDF. **Action:** ask them to
find the rule about bee keeping, using only the tree.

**Expected:** they reach section 7 without help, and afterwards can say roughly what the standard
covers — numbered sections, appendices of permitted substances, and a reserved gap in the numbering.

**Judgement:** *Judged by the second person: does the contents list read as the shape of a standard,
or as a list of headings someone extracted?* If they cannot say what section 5 or Appendix 2 is
**for** after using it, the tree is a table of contents in name only.
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 5 — The page is honest about what it does not hold

**Setup:** the same SAOSO concordance. **Action:** read the page's own statement about what the
corpus contains; scroll to the end of the tree.

**Expected:** the reserved range 10–19 appears as a row that is obviously not text, and the page says
plainly that some printed sections (the standard's opening Section A, and the closing Appendices A–C)
are not in the corpus.

**Judgement:** *Does that read as a boundary the group is drawing deliberately, or as an apology for
an unfinished page?* This is the same test as a Waiting card: the group must be able to say what it
does not have without sounding broken.
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 6 — Two branch names

**Setup:** the SAOSO tree. **Action:** read the first row and the Appendix 2 row.

**Expected:** the first row is named *Definitions* (not "Section 1"), and Appendix 2 is named for
fertilizers and soil conditioners (not "Farmyard manure, slurry and urine").

**Judgement:** *Can you tell, from the name alone, whether this is the branch you want?* A name that
describes the first thing inside the branch rather than the branch is worse than no name: it teaches
the reader to distrust the whole list.
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 7 — A document with no text, and a link that is stale

**Setup:** open one of the four published documents that has no ingested corpus (a form or
checklist). Then open a citation whose `?section=` value you have edited to nonsense.

**Expected:** the first says the text has not been ingested and offers the file; the second still
shows the document, starting at its first branch.

**Judgement:** *Do both read as honest states rather than as failures of the site?* A citation that
404s tells a reader the document is gone; a citation that lands on a wall of text tells them nobody
was thinking. Both of those are worse than an explanation.
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 8 — A clause reads as the document prints it

**Setup:** open `/documents/saoso-standard-v2.1/read/?section=s5-1-3` (Animal Husbandry, the
conditions in 5.1.3). Then open `?section=s8-1` (Mushroom Production), which has a list inside a
list.

**Expected:** 5.1.3's conditions read as a lettered list — `a.` to `f.`, each condition a row, a
wrapped condition continuing under its own marker — and the sentences before and after read as
paragraphs rather than as a ladder of lines. In 8.1, the roman `i.`/`ii.` sits *inside* item `a`.
The page's note at the foot says the words and punctuation are the document's and that line breaks
are reflowed.

**Also, since 2026-10-28 — the wrapped clause** (`reader_clause_line_breaks.md`): open
`?section=s23-3` (forced and involuntary labour) and `?section=s23-1`. Each clause is printed across
two lines, the second on a hanging indent. Each must read as **one paragraph, one sentence**, and
selecting it with the mouse must give the whole sentence — `…retaining part of the workers' wages,
property or documents.` — with no second clause dragged in behind it.

**Judgement:** *Does this read as a reproduction of the paper, or as a machine's attempt at one?*
The markers are the browser's list markers, not characters added to the text — the corpus prints a
bare `a` — and whether that reads as honest is a human call. A reader who has the PDF open should be
able to follow the same clause in both without losing their place. For the clause case: *would you
quote this clause to someone by copying it off the page?*
**Result:** PASS · Kobus (Product) · 2026-10-28 — the list rendering was signed on 2026-10-28 against 4e02d71; the clause case added with the artefact rebuild is approved at sign-off from the implementation and its automated guards; a hands-on pass is still owed before the P7.4 deploy
**Added 2026-10-28:** the clause case. Judged at sign-off the same day, from the implementation and
its guards rather than from a hands-on read — the note on the result says so, because a signature
that claims a run nobody made is not evidence.

---

## Scenario 9 — The appendix reads as the paper's table

**Setup:** open `/documents/saoso-standard-v2.1/read/?section=appendix-2`. Have the PDF open at
printed p. 76 beside it.

**Action:** read the branch top to bottom, as a reader looking for whether a substance may be used.

**Expected:** a caption naming the paper's two columns, one sentence saying what the appendix is, then
30 entries — each a substance on its own line with its condition below it. Four part headings
(`I. Plant and animal origin` … `IV. Others`) and three `South African specific` qualifiers break the
list where the paper breaks it, so the **Farmyard manure** row that appears twice does so under
different conditions rather than as a duplicate. The 19 rows whose condition cell the paper leaves
empty carry a muted `no condition printed` rather than silence, and no row reads as permission.

**Judgement:** *Does a substance read as an entry with a condition attached to it — the thing a
farmer looks up — or as a list of standalone inputs?* And specifically: *does a row with no condition
read as the paper declining to permit something, or does it read as a blank the site forgot to
fill?* If the second, the label or the legend is wrong, not the data.
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 10 — A reference goes somewhere

**Setup:** four open pages — Appendix 2, `?section=s5` (5.1.7), `?section=s22` (22.1.7) and
`?section=s6` (6.1) — and the PDF beside them.

**Action:** follow, each in a new tab:

1. from Appendix 2, `Appendix 6 Minimum Surface Areas Indoors and Outdoors` in the seaweed row's
   sentence;
2. from 5.1.7, `Appendix 6b` in `(defined in Section B Appendix 6b)`;
3. from 22.1.7, `Section A – 2.3`;
4. from 6.1, `Section 4.6.2`.

**Expected:** (1) and (2) open Appendix 6b with the cited appendix in the tree; (4) opens Section 4
with the citing passage in view; (3) **does not** open a section at all — it scrolls to the page's own
note that Section A is printed and not in the corpus, and says so in its tooltip. The page you came
from stays open behind each new tab.

**Judgement:** *Does each link land on what the sentence meant — and where it cannot, does it say so
rather than guessing?* The Part A case is the one to judge hardest: a reader who lands on *Organic
Ecosystems* (Section 2) instead of an explanation has been told something false by a link. Then:
*are there so many links that the clause is now hard to read?*
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 11 — A definition is a click away

**Setup:** `?section=s22` at 22.1.7, which uses `ACB`; and `?section=s4` at 4.2, which uses
`Conversion Period`. The glossary (`?section=s1`) open in another tab.

**Action:** follow `ACB` from 22.1.7, then `Conversion Period` from 4.2; then scroll the glossary and
read the definitions of `ACB`, `Habitat` and `Extensive Farming` in place.

**Expected:** each term opens the glossary in a new tab, **at the definition itself** — not at the top
of the branch — with the definition visible without scrolling. Within the glossary, terms are not
linked to themselves. Elsewhere, each term is linked once per passage at most, not on every
occurrence.

**Judgement:** *Does following a term answer the question the reader had — "what does this word mean
here?" — without losing the clause they were reading?* And: *does the clause still read as a clause
with the links in it, or is it now link-studded?* This is the judgement that decides whether the
feature stays.
**Result:** PASS · Kobus (Product) · 2026-10-28

---

## Scenario 12 — Finding the text from the documents page

**Setup:** open `/documents/`, as someone who has never used this site and has not seen a citation.
The four checklists and the visit preparation list are on the same page.

**Action:** without using the site's search or the chatbot, find the SAOSO standard's text from this
page, and then say why the crops checklist has no such option.

**Expected:** eight rows. Four of them — SAOSO v2.1, the OPP, Basic Production Principles and the
Certification Landscape — carry two actions, `Download` then `Read the text`, and the second opens
that document's concordance. The other four carry only `Download`: no greyed link, no tooltip, no
chip explaining an absence. Two clicks to the standard's text, and the difference between the rows
reads as a difference between the documents rather than as something half-built.

**Judgement:** *Does the page read as eight documents you can read, four of which you can also read
as text — or as an inconsistent list where something is missing?* The second reading is a fail, and
the fix is the copy or the page, not the data.
**Result:** PASS · Kobus (Product) · 2026-10-28 — the documents page offers the concordance on the four rows with text; approved at sign-off from the implementation and its automated guards; a hands-on pass is still owed before the P7.4 deploy

---

## Scenario 13 — The stocking-rate appendix answers its own question

**Setup:** open `?section=appendix-6a` (Number of animals per ha equivalent to 170 kg N/ha/year).
Have the PDF open at printed p. 85 beside it.

**Action:** answer one question from the page alone, without searching: *how many laying hens may I
run per hectare at the 170 kg N/ha limit?* Then check two more rows at random against the paper.

**Expected:** twenty rows — a class of animal on its own line with its number beneath it, in the
paper's order (`Equines over six months old` → 2 … `Laying hens` → 230). A caption naming the two
columns and one sentence saying what the table is. No pile of numbers at the end, and no number
attached to the class above it.

**Judgement:** *Does this read as a table you could act on — class → stocking rate — or as two lists
printed next to each other?* And: *is it obvious that the number belongs to the class above it and
not the one below?* That is the judgement the appendix exists for; a farmer asking for a stocking
rate must not have to count rows.
**Result:** PASS · Kobus (Product) · 2026-10-28 — Appendix 6a's twenty reviewed rows replace the pile of numbers; Appendix 6b is still prose by decision (saoso_text_glyphs_and_boundaries.md section 8); approved at sign-off from the implementation and its automated guards; a hands-on pass is still owed before the P7.4 deploy

---

## Sign-off

| Role | Name | Date | Result | Notes |
|---|---|---|---|---|
| Product owner | | | | |
| PGS administrator | | | | |
| Second person (Scenario 4) | | | | |

### Per-scenario results

| Scenario | Category | Result | Reviewer | Role | Date |
|---|---|---|---|---|---|
| 1. Arriving at the line |  | PASS | Kobus | Product | 2026-10-28 |
| 2. A substance row, not the first row |  | PASS | Kobus | Product | 2026-10-28 |
| 3. 390 px, in a farm office |  | PASS | Kobus | Product | 2026-10-28 |
| 4. The shape of the standard |  | PASS | Kobus | Product | 2026-10-28 |
| 5. The page is honest about what it does not hold |  | PASS | Kobus | Product | 2026-10-28 |
| 6. Two branch names |  | PASS | Kobus | Product | 2026-10-28 |
| 7. A document with no text, and a link that is stale |  | PASS | Kobus | Product | 2026-10-28 |
| 8. A clause reads as the document prints it |  | PASS | Kobus | Product | 2026-10-28 |
| 9. The appendix reads as the paper's table |  | PASS | Kobus | Product | 2026-10-28 |
| 10. A reference goes somewhere |  | PASS | Kobus | Product | 2026-10-28 |
| 11. A definition is a click away |  | PASS | Kobus | Product | 2026-10-28 |
| 12. Finding the text from the documents page |  | PASS | Kobus | Product | 2026-10-28 |
| 13. The stocking-rate appendix answers its own question |  | PASS | Kobus | Product | 2026-10-28 |

**Results:** 13 PASS · 0 FAIL · 0 N/A — signed by Kobus (Product).

**Signed against:** commit `e6f4464` (modified), database `pgs (dev), 385 chunks, Xpdf 4.00`, generated 2026-10-28.
