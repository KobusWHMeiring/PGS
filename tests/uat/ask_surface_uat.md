# UAT — The ask board, the answer page and the document reader

**Feature slug:** `ask_surface`
**PRD:** `product/backlog/In Progress/ASK_SURFACE_PRD.md`
**Plan:** `product/backlog/In Progress/ASK_SURFACE_PLAN.md`
**Decision:** `PGS_PLATFORM_SPEC.md` §18.3 D62 (shape), D63 (follow-ups), D64–D66 (this slice)
**Status:** Drafted **before** implementation (shift-left validation)
**Date:** 2026-10-23

---

## Purpose

Per `build_principles.md` §VIII, **UAT holds only checks a human must judge.** Every item below
carries a `Judgement:` clause naming the human-only call. Anything a test, a grep or a database
query can prove is listed in *Automated coverage* and is **not** shown to the reviewer as work:
a rendered card, a status code, an anchor target and a `noindex` tag are all asserted by the suite.

This slice ships three surfaces — the board on `/ask/`, the answer page at `/ask/<slug>/`, and the
document reader at `/documents/<code>/read/` — and they are judged on the same thing: **does a
reader who is not us get from a question to a quotable clause, and does the page remain honest
about what it does not answer?**

---

## Pre-test setup

1. Confirm the instance can be judged at all: open **`/uat/`** (staff login) and press the
   buttons, or run `python manage.py uat_seed --check`. It reports the corpus (chunks and
   vectors), the published documents and the extraction tool. **If it blocks, stop** — a
   judgement made against a half-seeded instance is not evidence.
   (An empty corpus is rebuilt per document, e.g.
   `python manage.py ingest_standard --doc saoso --file "pgs_docs/saoso-version-2.1-2026.pdf"`;
   there is no `--all` flag. `GEMINI_API_KEY` must be set, because a grounded answer is what
   produces a real card.)
2. Start the instance: `python manage.py runserver`, or use the deployed
   `https://organicguarantee.africa` after it has this commit.
3. Log in to `/admin/` as a user holding **PGS administrator** — the approval step is the point
   of the board and must be judged by the person who does it.
4. Have **one** other person available for Scenario 4 (a second reader, not a developer).

---

## Automated coverage (NOT UAT — asserted by the suite)

| What | Where |
|---|---|
| A consenting grounded question lands as `AWAITING`, never live | `core/tests/test_ask_board.py` |
| A consenting refusal lands as a `WAITING` card; an unticked box lands nothing | `core/tests/test_ask_board.py` |
| A duplicate question increments `ask_count` and creates no second card | `core/tests/test_ask_board.py` |
| Only `APPROVED` cards render on the board, and only they have a 200 answer page | `core/tests/test_ask_board.py` |
| An `AWAITING` or `REJECTED` card's page is 404; a `WAITING` page carries `noindex` | `core/tests/test_ask_answer_page.py` |
| Every viewer chunk is verbatim from the stored corpus, and no sequential id appears | `core/tests/test_document_reader.py` |
| A citation's `document_code` resolves to a published document; no code → no link | `core/tests/test_chat_grounding.py` |
| The reader route is exempt from the claim sweep **for a documented reason**, and the sweep can still fail | `core/tests/test_claim_discipline.py` |
| Touch targets ≥44 px, and no raw hex outside `root.css` | `core/tests/test_public.py`, `tests/e2e` |

---

## Scenario 1 — A card a stranger can read

**Setup:** ask *"Can I use cardboard from my neighbour?"* on `/ask/` with the consent box ticked.
In `/admin/`, open the card. **Action:** read the question and the answer as they would appear, then
approve. Open `/ask/` and the card's page.

**Expected:** the card's question reads as a question a person typed, and its page answers it in
sentences you would repeat to a farmer.

**Judgement:** *Is the question safe to publish as it stands — no third party named, no farm
identified, no personal detail — and is the answer text something this group is willing to stand
behind at a permanent URL?* A concise "yes, publish" is the call; per-farm detail gets edited out
before approval, not explained afterwards.

---

## Scenario 2 — The refusal stays a boundary

**Setup:** from the same instance, ask a question the corpus cannot answer (e.g. *"Do I need EU
organic certification to export to Germany?"*), consent box ticked.

**Expected:** the refusal is styled warm, not red, and it appears on the board as a **Waiting**
card that names the administrator as the next step. Its page explains that the document does not
answer it.

**Judgement:** *Does the Waiting card read as the group drawing a boundary confidently, or as
something having gone wrong?* This is the product's central claim (SPEC §13); a page that reads as
a malfunction fails even though every test passes.

---

## Scenario 3 — Landing on the clause

**Setup:** open an approved card's page. **Action:** follow one citation.

**Expected:** the document reader opens at the clause, the passage is visually marked, and its
printed page and section reference are visible without scrolling far.

**Judgement:** *Does the landing feel like arriving at the clause in its context, or like being
dropped into the middle of a wall of text?* The anchor can be asserted; whether a reader can tell
where they are and what surrounds the rule cannot.

The surface changed on 2026-10-27: the reader is now the concordance (the document's printed tree,
one open branch, a citation that says **"View this line"** and opens in a new tab). The widened
judgement — the tree, the phone disclosure, and what the page says the corpus does not hold — is
**`tests/uat/concordance_uat.md` Scenario 3**, and that file is unsigned. Judge the landing there.
This scenario still holds for the arrival itself.

---

## Scenario 4 — The citation survives leaving the site

**Setup:** hand the screen to the second person (not a developer). Ask them to copy the citation
block from an answer page and paste it into a message to a colleague.

**Expected:** the pasted text names the document, the section and the page, and quotes the clause
verbatim.

**Judgement:** *Judged by the second person alone: could they file this in a FORM, or repeat it to
a neighbour, without the page being open?* If they have to add a caveat or ask what a section
number means, the citation is not finished.

---

## Scenario 5 — 390 px, and a slow connection

**Setup:** browser at 390 px wide, throttled to slow 3G. Open `/ask/`, an answer page, and the
SAOSO reader.

**Expected:** the composer is the first thing on `/ask/`; cards stack one per row; the reader's
contents list is reachable without a horizontal scroll; the clause text is legible at that width.

**Judgement:** *On a phone in a farm office, is the composer the obvious next action, and is any
text clipped, cramped or pushed below the fold?* Layout at width is a judgement; overflow can be
measured, legibility cannot.

---

## Scenario 6 — The empty board

**Setup:** on a clean instance (no cards), open `/ask/`.

**Expected:** the composer, and under it, an honest statement that no questions have been
published yet.

**Judgement:** *Does an empty board read as "nobody has asked yet" rather than as a broken page or
an unfinished one?*

---

## Scenario 7 — What the page refuses to claim

**Setup:** read an answer page and the reader, looking for certification language.

**Expected:** no page claims a farm, a product or a person is certified; the reader labels its
text as the document's own words; "membership is not certification" appears wherever questions or
answers are listed.

**Judgement:** *Would the committee be comfortable with this page as a public statement of what
the group says?* `test_claim_discipline.py` catches the six forbidden terms and nothing about tone
(DESIGN §1); that residue is this scenario.

---

## Sign-off

| Role | Name | Date | Result | Notes |
|---|---|---|---|---|
| Product owner | | | | |
| PGS administrator | | | | |
| Committee reviewer | | | | |
| Second reader (Scenario 4) | | | | |
