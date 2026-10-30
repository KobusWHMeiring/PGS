# UAT — Building in the open (the public board)

**Feature slug:** `public_board`
**PRD:** `product/backlog/In Progress/PUBLIC_BOARD_PRD.md` (D74)
**Plan:** `product/backlog/In Progress/PUBLIC_BOARD_PLAN.md`
**Status:** Drafted after implementation — **unsigned**
**Date:** 2026-10-29

---

## Purpose of this document

Per `build_principles.md` §VIII and the `writing-uat-tests` skill, **UAT contains only checks a
human must judge.** If pytest, Playwright, a script or a grep can prove it, it belongs in the
automated suite — not here.

This page has an unusually small machine-checkable surface and an unusually large judgement
surface, which is why the list below is short and every item is about *reading*, not *render*.
The board's whole risk is tone: a curated roadmap of six sentences can be true card by card and
still read as a promise.

---

## Pre-test setup

1. The board must match the tree, or you are reviewing a stale page:
   `python scripts/board.py --check` → must print `matches the tree (6 card(s))`.
   If it says *stale*, run `python scripts/board.py` and re-check before going further.
2. `python manage.py seed_deployment && python manage.py publish_documents` (the page renders
   the footer and header, which read seeded data).
3. `python manage.py runserver`, then open `http://127.0.0.1:8000/building/`.
4. Have a **real phone** in hand, and a desktop browser. Most of these scenarios are about
   reading on a phone in daylight.

---

## Automated coverage (NOT UAT — asserted by the suite)

Recorded here so the manual list is not padded with machine-provable work.

| What | Where |
|------|-------|
| The route returns 200, has its own `<title>`, `lang`, one `<main>`, no unrendered template syntax, no CDN asset, no dead internal link, no missing static file | `core/tests/test_public.py` (`building` is in `PAGES`) |
| No forbidden certification claim on the page — swept with **no exemption** | `core/tests/test_claim_discipline.py` |
| Every artefact card appears on the page; column titles come from one place; no `Status:`/`Owner:`/`Last Updated:`/ordering date is rendered; an empty board renders a sentence instead of an empty grid; no card is a link | `core/tests/test_board.py` |
| The artefact is a subset of the curated set, carries no repo paths, is deterministic, and `--check` fails on a stale tree | `tests/tools/test_board.py` |
| A `Public: yes` PRD with no summary, an over-long summary, a claim term or a directory with no column stops the generator | `tests/tools/test_board.py`, `tests/tools/test_backlog_board_json.py` |
| Phone (390 px): no sideways scroll; desktop: no header overflow at 768/1024/1280; stylesheet and fonts really load; console clean | `tests/e2e/test_public_site.py` (`/building/` is in `ROUTES`) |

---

## Scenario 1 — Is every card readable by a farmer?

**Category:** content
**Setup:** Pre-test setup complete. Read the six cards on a phone, in daylight, standing up.

1. Read each card's title, then its sentence, without scrolling back.
2. For any card you did not understand at first reading, note which word stopped you.

**Expected:** Every card is understood on one reading, by someone who has not read the PRDs.

**Judgement:** The summaries were written by a developer from the PRDs, and the vocabulary that
survives that process is the vocabulary of the notebook — "concordance", "corpus", "escalation",
"in-office", "pre-visit". A card can pass every test and still need a second reading, and a
second reading is the whole failure. Judge each card alone: *would a farmer who has never heard
of this platform know what work it describes?*
**Result:**

---

## Scenario 2 — Does any card read as a promise?

**Category:** claim discipline / tone (the half no sweep can see)
**Setup:** As Scenario 1. Read the board, then read the footer's *"Membership is not
certification"* line, then read the board again.

1. For each card, ask: if I were a farmer reading this in a hurry, would I take this as a
   commitment with a date, or as work in progress?
2. Read the standpoint line above the columns: *"A development log, not a statement about any
   farm's certification status. No dates are promised, and nothing here is a commitment."*

**Expected:** No card reads as a delivery date, a guarantee, or a certification status for any
farm.

**Judgement:** `test_claim_discipline.py` forbids named terms; it cannot see *implication*. The
Shipped column is the risk: "Every document can be opened and read" beside a certificate is a
weaker claim than it looks, and a reader filling in the gaps can produce an overclaim the page
never made. Judge the board as a whole, not card by card.
**Result:**

---

## Scenario 3 — Does the board read as a board on a phone?

**Category:** layout
**Setup:** A real phone at 390 px width or narrower, and a desktop browser.

1. Open `/building/` on the phone and scroll the whole page.
2. On desktop, look at all four columns at once.

**Expected:** On the phone the columns stack and each card is fully readable without sideways
scrolling; on desktop the four columns line up and the Shipped column reads as history, not as
a prize.

**Judgement:** Playwright proves there is no horizontal overflow and that the page fits 390 px.
It cannot tell you whether a stacked board is *comfortable* or whether four columns of uneven
height look like a queue that has stalled. Compare the two viewports and say which one you would
put in front of a farmer, and whether the answer is the same for both.
**Result:**

---

## Scenario 4 — Is the board honest about how much is built?

**Category:** editorial honesty
**Setup:** As Scenario 1, plus `product/backlog/` open on the desktop.

1. Count the cards in each column.
2. Compare that with the number of PRDs in `ready/`, `In Progress/`, `Refinement/` and `Done/`.

**Expected:** The Shipped column has three cards; eleven PRDs live in `In Progress/` and eight
in `Done/`. That gap is deliberate — the board publishes only what carries `**Public:** yes`.

**Judgement:** A six-card board beside a 38-PRD backlog is either honest curation or a
shop-window that hides the work, and no test can decide which. Judge whether the *ratio* reads
as a young platform being candid, or as a brochure. If it reads as a brochure, the fix is to
publish more summaries — not to add cards the curation would not defend.
**Result:**

---

## Scenario 5 — Did you find the board the way a visitor would?

**Category:** navigation
**Setup:** Close the tab. Open `http://127.0.0.1:8000/` and navigate to `/building/` without
using the address bar.

1. Scroll to the footer and find the link.
2. Repeat on the phone, using the menu toggle to check the page is not in the main nav.

**Expected:** A footer link reading *Building in the open* under **The Group**.

**Judgement:** The board is deliberately absent from the header nav: six links plus the CTA
already fill one line at 768 px, and a roadmap is not why a farmer came. Whether the footer is
*discoverable enough* is a judgement — a page nobody finds is a page that does not exist, and a
page in the nav is a page that claims to be one of the site's six main things.
**Result:**

---

## Sign-off

| Field | Value |
|-------|-------|
| Reviewer | |
| Seat | |
| Commit | |
| Date | |
| Board artefact digest | |
| Verdict | |
| Notes | |

Apply the signature with `python scripts/uat_signoff.py` rather than by hand — a hand-written
signature is not evidence that the run happened.
