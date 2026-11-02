<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0m. 2026-10-29/30 — the backlog gets a public page, and it is six sentences, not a mirror

**State: built, gated, UAT unsigned.** This is the work §0l.4 found uncommitted in the tree. It
is now finished rather than half-written; the section stays open until the sign-off.

- **What the feature is.** `/building/` — a four-column board (In design / Up next / Building /
  Shipped) of cards that are one title and one 180-character sentence. Footer link, not a nav
  link: six nav links plus the CTA already fill one line at 768 px. Decision **D74** in
  `PGS_PLATFORM_SPEC.md` §18.3; PRD and plan in `In Progress/PUBLIC_BOARD_{PRD,PLAN}.md`.
- **Why it is not a rendering of `product/backlog/`.** Measured: **10 of 36 PRDs contain a term
  `test_claim_discipline.py` forbids**, and the sentences around them are notes about the live
  WordPress site's own overclaims (*"the live site's Favour Farm description is the source of the
  'pasture raised' phrase, and it must not be copied here"*). Publishing that text would put a
  named farm's unsupported claim on the group's own site. So the board is **curated**: a card
  exists only where a PRD carries `**Public:** yes` plus a `**Summary:**`; six do.
- **The data path.** `product/backlog.py --board-json` classifies (reusing the one
  `STATUS_RULES` table) → `scripts/board.py` validates and writes the committed artefact
  `core/services/_board_data.py` with a `SOURCE_DIGEST` → `core/services/_board.py` shapes it.
  **Zero database, zero request-time file reads**, so a PRD edit cannot change the live site
  without a deploy. `scripts/board.py --check` runs in `deploy/deploy.sh` *before* the backup —
  a stale board aborts the deploy with the fix command.
- **Three refusals, each proved by breaking it:** a `Public: yes` PRD with no summary, with a
  summary over 180 characters, with a claim term, or in a directory with no column
  (`spike/`, `BugFixes/`, `on_hold/`, `systems/`) stops the generator with the file named. A
  hand-edited artefact containing "pasture raised" made
  `test_claim_discipline.py::test_no_unsupported_claim[building]` go red — both layers fail, as
  they must.
- **`FORBIDDEN_CLAIMS` moved.** The canonical claim list now lives in `core/services/_public.py`
  and `core/tests/test_claim_discipline.py` imports it, because the generator needs the same list
  and two copies that agree today are two copies that disagree tomorrow. The test's
  non-empty/lowercase guard is unchanged.
- **Two plan deviations, recorded in the plan's §0.3:** a third header field `**Public title:**`
  (the `h1` of two candidates is internal vocabulary — *"MVP 1a — In-Office Visit Flow"*), and the
  phone layout **stacks** instead of using the planned `overflow-x` rail (the rail passes the
  `documentElement.scrollWidth` guard and asks a phone user to swipe sideways; stacking passes
  the same guard and reads better).
- **Left undone, deliberately:** the UAT (`tests/uat/public_board_uat.md`, five judgement
  scenarios, unsigned — so the backlog item stays in `In Progress/`, not `Done/`), and
  `tests/tools/test_board.py` is **not** in `scripts/fast.sh --critical`: the invariant that
  matters (a claim must not reach the page) is already carried there by
  `test_claim_discipline.py`, so the lane did not need a ninth file.

---
