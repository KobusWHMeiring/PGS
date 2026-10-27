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
   document. Expected: SAOSO 319 / OPP 30 / BPP 9 / landscape 8.
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

---

## Scenario 4 — The shape of the standard

**Setup:** hand the screen to someone who has never opened the SAOSO PDF. **Action:** ask them to
find the rule about bee keeping, using only the tree.

**Expected:** they reach section 7 without help, and afterwards can say roughly what the standard
covers — numbered sections, appendices of permitted substances, and a reserved gap in the numbering.

**Judgement:** *Judged by the second person: does the contents list read as the shape of a standard,
or as a list of headings someone extracted?* If they cannot say what section 5 or Appendix 2 is
**for** after using it, the tree is a table of contents in name only.

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

---

## Scenario 6 — Two branch names

**Setup:** the SAOSO tree. **Action:** read the first row and the Appendix 2 row.

**Expected:** the first row is named *Definitions* (not "Section 1"), and Appendix 2 is named for
fertilizers and soil conditioners (not "Farmyard manure, slurry and urine").

**Judgement:** *Can you tell, from the name alone, whether this is the branch you want?* A name that
describes the first thing inside the branch rather than the branch is worse than no name: it teaches
the reader to distrust the whole list.

---

## Scenario 7 — A document with no text, and a link that is stale

**Setup:** open one of the four published documents that has no ingested corpus (a form or
checklist). Then open a citation whose `?section=` value you have edited to nonsense.

**Expected:** the first says the text has not been ingested and offers the file; the second still
shows the document, starting at its first branch.

**Judgement:** *Do both read as honest states rather than as failures of the site?* A citation that
404s tells a reader the document is gone; a citation that lands on a wall of text tells them nobody
was thinking. Both of those are worse than an explanation.

---

## Sign-off

| Role | Name | Date | Result | Notes |
|---|---|---|---|---|
| Product owner | | | | |
| PGS administrator | | | | |
| Second person (Scenario 4) | | | | |
