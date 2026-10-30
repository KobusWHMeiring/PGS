# Implementation Plan — Building in the open (public board)

**Status:** In Progress — B0–B6 landed 2026-10-29; **B7 (UAT) outstanding**, so the item stays
here rather than in `Done/` (`CONVENTION.md`: nothing is finished without a sign-off). PRD:
`PUBLIC_BOARD_PRD.md`, decision D74.
**Owner:** Kobus Meiring (Product · Build)
**Last Updated:** 2026-10-29
**MVP:** 0 public surface, post-close-out addition.
**Reference:** `../../docs/context/build_principles.md` · `../../docs/context/testing_hazards.md` · `../../design/DESIGN.md` §6–§7

---

## 0. How to execute

- **TDD order.** Every task states its failing test first. A task is done when that test passes.
- **One commit per task**, prefixed with the task id (`feat(b3): the board route`).
- **B0 gates everything.** No view is written before the summaries exist; the board is a content
  product with a rendering attached, not the reverse.
- **`scripts/fast.sh --critical` after each code task**; `scripts/fast.sh` at the end of the session.
  The board touches a public route and `test_claim_discipline.py` is in the critical lane.

### 0.1 Frozen decisions

| # | Decision |
|---|---|
| D74a | Public "Building in the open" page, curated summaries only — not a mirror of the notebook |
| D74b | Generated + committed artefact, refreshed before a deploy push; never read from `product/` at request time, never a model |
| D74c | `**Summary:**` + `**Public:** yes` in the PRD header; no automatic summarisation |
| — | The `Public:` line gates inclusion; the directory only picks the column |
| — | Footer link only — the header already holds six links plus the CTA at 768 px |
| — | Phone layout **stacks** — one column, two at 768 px, four at 1024 px. See §0.3 (it replaced the planned rail) |
| — | Cards have no permalink and no id — nothing to enumerate (§I: no sequential ids on a public surface) |

### 0.3 What changed while building

Two things this plan got wrong, corrected in the code rather than in a note somewhere else:

1. **A third header field: `**Public title:**`.** B0 assumed the card's title could be the PRD's
   own `h1` minus its `PRD:` prefix. It cannot: `# PRD: MVP 1a — In-Office Visit Flow` strips to
   *"MVP 1a — In-Office Visit Flow"*, and a delivery-slice label is not something a farmer asked
   for. Two of the six candidates have internal titles. The override is optional and falls back
   to the cleaned `h1`, so nothing else changed.
2. **The phone layout stacks; there is no rail.** The plan chose an inner `overflow-x: auto`
   container because the e2e guard measures `documentElement.scrollWidth`, so a wide flex row
   would fail it while a scroll container would pass. That is true and it is also the worse
   answer: it makes a phone user swipe sideways to read four columns of two cards each. Stacking
   passes the same guard and reads better, so the guard's *reason* survived and its workaround
   did not. `DESIGN.md` §7.12 records the stacking as the rule, not the fallback.
3. **No `GENERATED_AT` in the artefact.** The plan had one. It makes `--check` fail on a tree
   nobody touched, and the obvious fix — ignore that line — is a comparison with a hole in it.
   The digest identifies the content; git identifies when.

---

## B0 — Content (gates B1)

**No test.** This is copy, and it is reviewed as copy.

1. Add `**Summary:**` and `**Public:**` to `product/backlog/PRD_TEMPLATE.md`, above `**Scope:**`,
   with a one-line rule printed beside them: *180 characters, plain English, written for a farmer,
   no internal identifiers.*
2. Draft a `**Summary:**` and decide `**Public:**` for each of the candidates in `PUBLIC_BOARD_PRD.md`
   §7. Expect **5–7 cards**, of which 2–3 are "Shipped".
3. Read each summary against `core/tests/test_claim_discipline.FORBIDDEN` by hand. The generator will
   enforce it, but a reviewer's eye is what catches *"our certified farms"* — tone is not greppable.
4. Confirm the ratio is honest: a young platform with four shipped items and two in design tells the
   truth. Twenty cards would be the first lie on the page.

**Exit:** `grep -rn "^\*\*Public:\*\* yes" product/backlog` returns the intended set, each with a summary.

---

## B1 — `product/backlog.py --board-json`

**Test first** (`tests/tools/test_backlog_board_json.py`):

- a fixture `product/backlog/` in `tmp_path` with three PRDs (one `Public: yes` with a summary, one
  without the line, one in `Done/`) returns **only** the opted-in item;
- the item carries `title`, `summary`, `bucket`, `rel` — and **no** `status`, `owner`, `updated`;
- an opted-in PRD with no `**Summary:**` is reported in a `rejected` list with a reason, not dropped
  silently (a silent drop is `testing_hazards.md` §1.6 with a directory behind it).

**Implementation.** `--board-json` reuses `scan()` and `effective_bucket()` and prints
`{"items": [...], "rejected": [...], "digest": "..."}`. No formatting, no file writes: this mode
classifies, `scripts/board.py` renders.

**Hazard, recorded while writing this plan:** `product/` contains both `backlog.py` and `backlog/`.
`sys.path.insert(0, "product"); import backlog` resolves to the **module** today, but adding
`product/backlog/__init__.py` would flip it to the package and the import would silently change
meaning. `scripts/board.py` must load the file by path
(`importlib.util.spec_from_file_location("pgs_backlog", REPO_ROOT / "product" / "backlog.py")`) and
a test asserts the loaded `__file__` ends in `backlog.py`.

---

## B2 — `scripts/board.py`

**Test first** (`tests/tools/test_board.py`, following `tests/tools/test_uat_runner.py`'s pattern of
importing the script module directly):

1. `forbidden summary` → exit non-zero, stderr names the file and the term.
2. `missing summary` on a `Public: yes` PRD → exit non-zero.
3. `181-character summary` → exit non-zero.
4. `--check` against an artefact generated from different inputs → exit non-zero, message contains
   `python scripts/board.py`.
5. **The artefact is a subset of the curated set**: every card title in the emitted module exists in
   the input JSON, and no card exists in the module that is not in the JSON. This is the test that
   makes the feature safe rather than convenient.
6. `Done` is capped at 6 and ordered newest-first by the PRD's `Last Updated`, and a bucket with no
   opted-in items emits **no** column at all.

**Implementation.** Validate → sort → cap → emit `core/services/_board_data.py`:

```python
"""GENERATED by scripts/board.py — do not edit by hand.
Regenerate before a deploy push:  python scripts/board.py
"""
GENERATED_AT = "2026-10-29T10:00"
SOURCE_DIGEST = "sha256:…"
CURATED = ({"title": …, "summary": …, "column": "building"}, …)
```

The module holds **plain tuples of dicts**, not dataclasses: a generated file must not need an
import to be read, and `core/services/_board.py` is where the typed shape lives (§II).

---

## B3 — service, view, route

**Test first** (`core/tests/test_public.py`, one entry added to `PAGES`):

```python
("building", "/building/", "Building in the open"),
```

and a test that the page renders a card whose title came from the artefact, plus a test that **no**
`Status:`, owner name or `Last Updated` date string from any PRD appears in the HTML.

**Implementation.**

- `core/services/_public.py` — one `Page` in `PAGES` (`key="building"`, heading/accent split per
  DESIGN §7.2) and one `NavLink` **in the footer tuple**, not `NAV`.
- `core/services/_board.py` — `board_context()` → `Board(columns=(Column(title, cards), …))`, dropping
  empty columns, with the "development log, not a statement about any farm's certification status"
  line as a field so the template holds no copy.
- `core/views/_public.py:building()` — `render(request, "public/building.html", public_context("building") | board_context())`.
- `core/urls.py` — `path("building/", building, name="building")` in the public block, after `contact/`.

---

## B4 — template and CSS

**Test first.** `tests/e2e/test_public_site.py`: add `("/building/", "Building in the open")` to
`ROUTES` — this immediately turns on the browser render, the 390 px overflow check, the 44 px target
check, the text-link target check and the console-error check.

**Implementation.**

- `core/templates/public/building.html` — extends `base.html`, uses `_page_head.html`, then
  `<section class="board">` → `.board__column` → `.board__card` (`h3` + `p`, no link).
- `core/static/css/components.css` — `.board` (grid, one column on phone), `.board__column`,
  `.board__card`, `.board__rail`. **The rail is the scroll container**:
  `overflow-x: auto` on `.board__rail`, `scroll-snap-type: x mandatory` if it costs nothing, and
  `min-width: min(80vw, 22rem)` per column — measured against the `documentElement.scrollWidth`
  guard, not assumed.
- `product/design/DESIGN.md` — a new §7.12 recording the component, its tokens and its phone state.
  A new component that is not in DESIGN.md is how this repo got four palettes.
- `core/static/css/site.css` must not grow: it is 22.4 KB against a 30 KB cap asserted by
  `test_public.py`.

---

## B5 — the claim sweep, with no exemption

No code. Add the route to `PAGES` (B3 did) and **run** `test_claim_discipline.py` unmodified:

```
pytest core/tests/test_claim_discipline.py -q
```

Four sweeps × the new page: forbidden terms, no seal label from the database, no unsourced claim
(`february`), nothing pending. **If any of them fails, fix the summary — never add a
`VERBATIM_ROUTES` entry.** `test_the_exemption_list_has_a_reason_per_route` refuses an exemption for a
route that is also in `PUBLIC_URLS`, and that refusal is the mechanism that keeps this a curated page.

Then prove the guard can fail: put `pasture raised` into a `Public: yes` summary, watch B2's generator
and B5's sweep both go red, restore.

---

## B6 — the deploy path

1. `deploy/deploy.sh` gains one pre-pull step next to the existing gate logic:
   `python scripts/board.py --check` — before the backup, so a stale board aborts the deploy rather
   than shipping.
2. `product/backlog/CONVENTION.md` §Workflow gains a fourth command: `python scripts/board.py`, run
   **before a push that will be deployed**, and the note that the board is a release artefact.
3. `HANDOVER.md` §0i records it.

---

## B7 — UAT

1. `tests/uat/public_board_uat.md` — human-judged items only (`writing-uat-tests` skill):
   does the phone board feel like a board; is every card readable by a farmer; does any card read as a
   promise; is the "not a statement about certification" line present and unmissable.
2. Present it with the `pgs-presenting-uat` skill, get the signature, then move
   `PUBLIC_BOARD_PRD.md` + this plan to `Done/` via `python product/backlog.py --apply`.

---

## Budgets

| Task | Estimate |
|---|---|
| B0 content | **the long pole** — 5–7 summaries written for a farmer, one review pass |
| B1 + B2 | one session; the generator is ~150 lines and 6 tests |
| B3 + B4 | one session; the CSS is the risk (phone rail under the measured guard) |
| B5 | minutes, plus the mutation proof |
| B6 + B7 | half a session each, and B7 waits on a human |

Targets unchanged: `--critical` ≤ 60 s warm, `scripts/fast.sh` ≤ 60 s warm, `scripts/verify.sh` once
before the commit. `tests/e2e` stays outside both lanes — run it explicitly for B4, because a board
layout is exactly what only a browser can judge.

---

## Open question carried into B0

**Does a card ever link anywhere?** This plan says no — a summary and a title, no permalink. If a card
should open something, the only honest target is a public "what this means for you" page, not the
PRD, and that is a second feature. Decide it in B0, because it changes B4's markup.
