# PRD: Building in the open — the public backlog board

**Status:** In Progress — built 2026-10-29 (D74a–c); every guard green, **UAT signature
outstanding** (`PUBLIC_BOARD_PLAN.md` §B7).
**Owner:** Kobus Meiring (Product · Build)
**Last Updated:** 2026-10-29
**MVP:** 0 — an addition to the public surface the MVP 0 sub-plan C shipped, not a new slice.
**Scope:** One new public route rendering a **generated, committed** board of *curated* backlog
cards: a column per lifecycle bucket, a one-line summary per card, no PRD body, no editing, no
JavaScript. It publishes **nothing** that has not been marked publishable by a person. It builds no
reader for a PRD, no filters, no search, no RSS, no per-card permalink and no "progress" metric.
**Reference:**
- Backlog convention — `../CONVENTION.md` ("the directory is the source of truth")
- Generator brief this echoes — `CODE_ATLAS_PRD.md` (generated, gated, never hand-written)
- Build rules — `../../docs/context/build_principles.md` §I (layout), §II (services), §IV (front end), §V (guarding)
- Design system — `../../design/DESIGN.md` §1 (claim discipline), §6 (rules), §7 (components)
- Content decision that makes this hard — `core/tests/test_claim_discipline.py`

---

## 1. Problem Statement

**The group's public site says what it publishes, and nothing about what it is building.** A visitor
who wants to know whether the thing they asked for is coming — a member registry, a certificate
lookup, the farmer portal — has no answer: the six public pages describe the PGS process as it is
today, and the roadmap exists only in `product/backlog/`, which is an engineering notebook.

**The naive version of this feature is a disclosure incident.** The backlog is *not* publishable
text. Measured 2026-10-29:

| What is in `product/backlog/` | Count | Why it cannot ship |
|---|---|---|
| Files containing a claim-discipline term (`pasture raised`, `biodynamic`, `GMO free`, …) | **10 of 36**, 35 lines | `test_claim_discipline.py` forbids all of them on a public route |
| … and the sentences around them | — | e.g. `Done/MVP0_PLAN.md:2898` says *"The live site's Favour Farm description is the source of the 'pasture raised' phrase, and it must not be copied here"* — publishing that tells the world our current site overclaims about a named farm |
| Host, path and credential-shaped lines | `In Progress/VPS_DEPLOYMENT.md` | infrastructure disclosure |
| POPIA, fee-arrears and risk-register prose | most PRDs | commercial and personal information |
| Words that read as failure to a farmer | titles like *Chat truthfulness*, *Readiness*, *Self check* | reputational, not technical |

So the board **cannot** be a mirror of the backlog. It is a **curated subset**, and curation is a
content decision a person makes one PRD at a time — which is why the product of this PRD is a
publishing *mechanism*, not a rendering of everything.

**Prose rots; this repo has the receipts** (`CODE_ATLAS_PRD.md` §1). A board that refreshes itself
from the working tree at request time would change the live site with every PRD edit, with no gate
between the edit and the public. That is the opposite of what this repo does with anything that
reaches a visitor.

---

## 2. Strategic Goal

> **A visitor can see, in one screen, what the group is building next — in language a farmer can
> read — without any internal note, term or figure reaching them; and a maintainer can publish one
> more item by writing two lines into a PRD and running one command.**

**Success looks like:** the page is true on the day of a deploy and is *provably* a subset of what
was curated. Deleting every `**Public:** yes` line empties the board and no test goes red for the
wrong reason.

---

## 3. Closed decisions

Recorded as **D74** in `PGS_PLATFORM_SPEC.md` §18.3.

| # | Question | Decision |
|---|---|---|
| D74a | Who is the audience? | **Genuinely public** — a "Building in the open" page for farmers, consumers and adjacent groups. Not a mirror of the notebook. Curated summaries only. |
| D74b | Where does the board's data come from? | **A generated artefact committed to the repo**, refreshed deliberately before a deploy push. Not read from `product/backlog/` at request time, and not a database table: a `BacklogItem` model would be a migration for repo knowledge, which §I's "data encodes the standard **and the group**" does not cover. |
| D74c | Where does a card's summary come from? | **A new `**Summary:**` line in the PRD itself**, plus a `**Public:** yes` opt-in. No summarisation of §1 Problem Statement: it is 200 words of internal decision-making and its first sentence is often about a defect. |

**Why the artefact is generated before a deploy and not on every edit.** Classification already has
exactly one implementation — `product/backlog.py`'s `STATUS_RULES` — and a second one would drift
silently. Regenerating on every PRD edit would put board churn into unrelated commits. The
compromise is a **digest**: the artefact records the digest of the inputs it was built from, and a
test recomputes it. A stale artefact fails `scripts/fast.sh` in under a second with the exact command
to run, and the deploy gate (`git archive FETCH_HEAD` → `scripts/verify.sh`) refuses a tree whose
board does not match its source. Publishing is therefore one deliberate act per release, and drift is
caught at the cheapest possible moment.

---

## 4. What is published, and what is not

**The gate is the `**Public:** yes` line, not the directory.** The directory only decides the column.
A PRD without the line is invisible, whatever it says and wherever it lives.

| Directory | Column | Publishes |
|---|---|---|
| `Refinement/` | **In design** | only with `Public: yes` |
| `ready/` | **Up next** | only with `Public: yes` |
| `In Progress/` | **Building** | only with `Public: yes` |
| `Done/` | **Shipped** | only with `Public: yes`, newest first, capped at 6 |
| `spike/`, `BugFixes/`, `on_hold/`, `systems/` | *no column* | never — the leakiest material lives here |

**Never rendered, whatever the PRD says:** `**Status:**` (it is a note to ourselves and routinely
contains "blocking decisions", "superseded", "four of seven criteria"), `**Owner:**`, `**Last
Updated:**` (a board that shows the date each item last moved invites a reader to judge velocity and
abandonment), `**MVP:**`, the PRD body, and any path.

**Never accepted by the generator:** a `Public: yes` PRD that (a) has no `**Summary:**`, (b) contains
a term in `test_claim_discipline.FORBIDDEN`, or (c) has a summary longer than 180 characters. The
generator **exits non-zero** naming the file and the reason. A publishable item is checked before it
can be published, not after.

**Page copy** must say what the board is not: *"This is a development log, not a statement about any
farm's certification status."* Membership is not certification (OPP), and a roadmap card is not a
certification either — the sentence is the same rule applied to a new surface.

---

## 5. Technical requirements

1. **Three new PRD header fields**, added to `PRD_TEMPLATE.md`: `**Public title:**` (optional,
   only when the PRD's own title is internal vocabulary such as "MVP 1a"), `**Summary:**`
   (≤180 chars, plain English, no internal identifiers) and `**Public:**` (`yes` / absent).
   Absent means **not published** — a PRD that predates this feature stays invisible until a
   person opts it in. The third field was added on 2026-10-29 while writing the summaries;
   `PUBLIC_BOARD_PLAN.md` §0.3 records why the first two were not enough.
2. **`product/backlog.py` gains `--board-json`**: classification only, JSON on stdout, reusing
   `scan()` / `effective_bucket()`. It owns no formatting and writes no file, so `backlog.py` stays a
   backlog maintainer rather than a web tool.
3. **`scripts/board.py`** owns the artefact: reads that JSON, validates the three rules in §4, and
   writes `core/services/_board_data.py` — a generated module of frozen tuples, headed by
   `GENERATED — do not edit by hand` and carrying `SOURCE_DIGEST`. **No generated-at timestamp**:
   it would make `--check` fail on a tree nobody touched. `--check` rebuilds in memory and compares
   bytes; a failure prints the command to fix it.
4. **`core/services/_board.py`** shapes the data into `Board(columns=(Column(title, cards), …))`
   (§II: the template displays and does not hold a column title). Empty columns are dropped, so a
   board with nothing shipped does not render an empty "Shipped" heading.
5. **`core/views/_public.py:building()`** — three lines, thin.
6. **Route `/building/`**, added to `core/urls.py`'s public block and to `core/services/_public.py`'s
   `PAGES` as one `Page` entry with its own `title`, `description`, `heading` and `heading_accent`.
7. **A footer link, not a header link.** `tests/e2e/test_public_site.py` measures six nav links plus
   the CTA on one line at 768 px; a seventh is the most likely way to break it and the least likely
   thing a farmer came for.
8. **`core/templates/public/building.html`** and one new component in `components.css`
   (`board`, `board__column`, `board__card`). Cream grounds, `brand-*` tokens only, no JS, and the
   phone layout **stacks** — one column, two at 768 px, four at 1024 px, with `minmax(0, 1fr)`.
   `test_no_horizontal_overflow_on_a_phone` measures `documentElement.scrollWidth`; a stacked grid
   and an inner scroll rail both pass it, and stacking is the one a phone user can read
   (`PUBLIC_BOARD_PLAN.md` §0.3).
9. **CSS budget:** `site.css` is 22.4 KB against `test_public.py`'s 30 KB cap. The board is a new
   component and belongs in `components.css` (21.1 KB) to keep each file under its own cap.
10. **Tests** (§V, and `testing_hazards.md` before writing any of them):
    - `tests/tools/test_board.py` — the generator: a `Public: yes` PRD without a summary exits
      non-zero; a forbidden term exits non-zero; `--check` fails on a stale digest; **the artefact is
      a subset of the curated set**, asserted on the generated module.
    - `core/tests/test_public.py` — the route joins `PAGES`, so the eight existing parametrised tests
      (200, own `<title>`, `lang`, no unrendered template syntax, …) cover it for free.
    - `core/tests/test_claim_discipline.py` — covers it **automatically** the moment the route is in
      `PAGES`. This is the load-bearing guard and it must *not* be given an exemption:
      `test_the_exemption_list_has_a_reason_per_route` forbids exempting a route that is also swept,
      which is the rule that makes "publish a summary, not a mirror" enforceable rather than optional.
    - `tests/e2e/test_public_site.py` — the route joins `ROUTES`: renders in a browser, no sideways
      scroll at 390 px, 44 px targets on the card's links.
    - A guard-the-guard test: put a `FORBIDDEN` term into a `Public: yes` summary and watch the
      generator refuse it (prove the check can fail, then restore).

---

## 6. Execution steps

See `PUBLIC_BOARD_PLAN.md`. Content curation (§7) is B0 and gates everything: building the page
before the summaries exist produces a board that is empty or wrong.

---

## 7. Content work — the part that is not code

Eight of 36 PRDs are candidate cards. Each needs a summary written **for a farmer**, and each needs
its `Public:` line decided individually. Draft the summaries first and review them as copy; they are
the entire product of this feature.

| Candidate | Column | Summary must avoid |
|---|---|---|
| `MVP1A_PRD.md` — in-office visit flow | In design | "seam contract", "template_schema", "CONDUCT" |
| `MVP0_PRD.md` — standards and public site | Shipped | the section that discusses forbidden terms |
| `DOCUMENTS_READER_LINK_PRD.md` | Shipped | — |
| `PASSAGE_LAYOUT_PRD.md` | Shipped | — |
| `CODE_ATLAS_PRD.md` | In design | — |
| `LANDSCAPE_TABLES_PRD.md` | In design | — |
| `self-check` / `CHAT_*` items | **no** | internal quality language reads as product failure |
| `VPS_DEPLOYMENT.md`, `OFFLINE_SPIKE_PRD.md` | **no** | infrastructure, personal data |

The board's honesty comes from the ratio: three or four "Shipped" cards beside two "In design" is a
true picture of a young platform. Padding it to twenty would be the first lie on the page.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| A PRD is edited after a deploy and the live board disagrees with the repo | `SOURCE_DIGEST` + `--check` in the suite and in the deploy gate; the failure names the command |
| Someone publishes a PRD whose body is safe but whose *summary* overclaims | The generator sweeps the summary against `FORBIDDEN`; the route is in `PAGES`, so the page is swept too |
| The board rots because nobody regenerates it between releases | Accepted: it is a release artefact. The digest makes "stale" a loud state, not a silent one |
| A curated item is un-published by deleting `Public: yes`, and a test asserts the old card | No test names a specific card — the generator tests use fixture PRDs in `tmp_path`, never real ones |
| The page becomes a de-facto commitment ("you promised the registry") | Page copy states there are no dates and no order beyond the column; no percentages, no ETAs, no counts |
| A card's `<title>`/permalink leaks a sequential id (a public identifier must be a UUID, §I) | Cards have **no** permalink and no id. There is nothing to enumerate |

---

## 9. Success criteria

- [ ] `/building/` renders, added to `PAGES` and `ROUTES`, and all existing parametrised public tests pass on it unchanged.
- [ ] `test_claim_discipline.py` sweeps it with **no** exemption entry.
- [ ] No PRD body, path, status, owner or date reaches the HTML (asserted on rendered HTML, not the template).
- [ ] `python scripts/board.py` exits non-zero on a forbidden term, a missing summary, or a summary over 180 characters — each proved by breaking it.
- [ ] `python scripts/board.py --check` fails on a stale artefact and the message names the fix.
- [ ] 390 px: no sideways scroll on the document; the rail scrolls, the page does not.
- [ ] Nav is unchanged and `test_the_header_holds_the_ask_link_without_overflow` passes at 768/1024/1280.
- [ ] UAT in `tests/uat/` signed by the product owner — this has a user-facing surface, so tests passing is not completion.
- [ ] `body` measured: `components.css` and `site.css` both still under 30 KB.

---

## 10. The fence

**In:** one route, one generated module, one service, one template, one CSS component, two PRD header
fields, the generator and its tests.

**Out:** a PRD reader or viewer; per-card pages; filters, search, sorting or a "board" URL state;
comments; email/feed subscriptions; anything reading `product/` at request time; a Django model; a
`spike/` or `BugFixes/` column; publishing anything that was not opted in; and any date, percentage or
count that would read as a delivery commitment.

---

## Pre-Flight Checklist

- [ ] Models added to `core/models.py` or new app? — **no model; a generated module** (§I)
- [ ] Views added to correct `core/views/_<domain>.py`? — `_public.py`
- [ ] Forms — none.
- [ ] Services added to correct `core/services/_<domain>.py`? — `_board.py` + generated `_board_data.py`
- [ ] URLs added to `core/urls.py` in the public block, after the existing public routes.
- [ ] Tests added to `core/tests/test_public.py` (route) and `tests/tools/test_board.py` (generator).
- [ ] Migrations — none.
- [ ] `select_related`/`prefetch_related` — no query at all; the page touches no database.
- [ ] `transaction.atomic()` — no writes.
- [ ] No logic in templates — column titles and card copy arrive in the context.
