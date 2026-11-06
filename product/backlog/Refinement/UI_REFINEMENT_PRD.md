# UI refinement — the headers are too big, and the back buttons are missing

**Status:** **Refinement** — the owner named three things on 2026-11-06 (`66bc6c1`) and this record
stages them; **nothing has been measured, designed or built**, and §3's four questions are open.
**Owner:** Kobus Meiring (Product) — what is "too big", and the sign-off · build — the CSS and
templates
**Reference:** `product/design/DESIGN.md` §4 (the type scale) and §7.1 (the header) ·
`product/design/content_inventory.md` · `core/tests/test_claim_discipline.py` ·
`.agents/skills/` (four local `pgs-*` skills, none of them about the browser)
**Baseline commit:** `66bc6c1` — dev DB migrated and seeded, dev server on `127.0.0.1:8000`

---

## 1. What the owner said

> "It's mostly about header sizes being too big, placing relevant back buttons where they are
> needed. Basic UI improvements." — product owner, 2026-11-06

That is the whole brief. It is three kinds of act, and they are not the same size:

1. **Type scale** — the display headings read too large on the pages they were judged on.
2. **Navigation** — a page that is one step into a flow has no way back other than the browser.
3. **"Basic UI improvements"** — deliberately open, and the reason §4 below is a measurement pass
   rather than a list.

**Nothing here is allowed to change what the site claims.** `DESIGN.md` §1 puts claim discipline
before aesthetics, and `core/tests/test_claim_discipline.py` still fails the build on a forbidden
phrase. A refinement that touches copy goes through `COPY_VOICE.md` ("rewrite, never add a fact"),
not through this PRD.

## 2. The first hypothesis, from the spec itself

`DESIGN.md` §4 fixes the scale, so "too big" has a number to argue against:

| Role | Classes as specified | Suspect |
|---|---|---|
| Hero `h1` | `text-4xl sm:text-5xl md:text-6xl` | 60 px at `md` is a landing-page size, and three pages reuse it |
| Section `h2` | `text-3xl sm:text-4xl` | 36 px in a cream band is the "too big" the owner most likely means |
| Card `h3` / micro-heading | `text-lg` / `text-[11px]` | not suspects — they carry the hierarchy |

**Lora is deliberately at `font-normal`, not bold** (§4: "that is most of the design's character").
So the fix is very unlikely to be "make them bold instead": it is the size, the measure (line
length), or where the scale jumps at a breakpoint. Measure before choosing.

Back buttons: `DESIGN.md` §7 already carries one — **the self-check wizard** (`/before-you-apply/`)
— and the applicant flow (`register → consent → pledge → categories → turnover → summary`) is the
obvious place a browser-back is currently the only way out. A marketing page (`/organics/`) does
not want a back button; a *step* does.

## 3. Open questions — the owner's answers, not the builder's guesses

1. **Which "header"?** The page `h1`/hero title, the section `h2`s inside the cream bands, or the
   sticky `_header.html` bar with the wordmark and nav? `DESIGN.md` covers all three and they are
   fixed in different places.
2. **Which surfaces first** — the nine public pages, the applicant portal, or both? The demo is
   public-first, but the portal is where a farmer gets lost.
3. **"Relevant back buttons"** — the applicant flow's steps, the document reader, or the wizard?
   Does a step get "back to the previous step" or "back to the application"?
4. **Which screen is being judged?** "Too big" depends on it. Measure at **375, 768 and 1440** and
   say which one the complaint came from.

## 4. The measurement pass — do this before any CSS

The repo's own habits apply (`AGENTS.md` "Context discipline"): **one screenshot, one read**; a new
session per design pass; and no opinion about a page that has not been looked at.

1. Capture `/`, `/organics/`, `/how-it-works/`, `/before-you-apply/`, `/members/`, `/documents/`,
   `/become-a-member/`, `/contact/`, `/building/` at 375 / 768 / 1440 into `_scratch/` (not into the
   repo), and the applicant flow's six screens at the same widths.
2. Record, per page: the rendered `h1`/`h2` px and the words-per-line measure at 1440 and 768. A
   heading is "too big" when it is over ~1.6× the body scale *and* the line it sits on wraps to one
   or two words.
3. Write the findings as a table in this PRD (§6), with the page, the size, the proposed size, and
   what it costs — then the owner picks from the table instead of reading the whole site again.
4. Only then change `DESIGN.md` §4 (the spec) and the templates (the implementation), in that order,
   so the next reader finds one scale and not two.

Ratchet: `tests/e2e/test_public_site.py` measures the header holding one line at 768 px — a smaller
scale must not be paid for by breaking that.

## 5. The skill: a short investigation, then `pgs-refining-ui`

The owner asked for this explicitly, and it is a **separate, smaller act** — an investigation
first, a skill second:

- **Read before writing:** `DESIGN.md` (already the repo's design system) and
  `product/design/content_inventory.md`; then the practice outside — a public-UI refinement pass is
  mostly *measurement and small reversals*, not a redesign, and there are well-known instruments for
  it (WCAG 2.2's 24 px minimum target size — this repo wants **44 px** — and contrast ratios; the
  heuristic-audit lists; the type-scale ratio systems). Use them as *checklists to measure against*,
  not as things to rebuild the site from.
- **What the skill must encode is this repo's loop, not a theory:** measure in the browser, judge
  against `DESIGN.md`'s tokens, change the spec before the template, one palette (`brand-*`), no
  build pipeline, no fourth test lane, and photograph once per pass.
- **Where it lives:** `.agents/skills/pgs-refining-ui/SKILL.md`, alongside the five existing
  `pgs-*` skills, with the front-matter format the others use. Do **not** reach for the global
  `designing-in-html` (it prototypes with CDNs and another token set) or `css-alignment` alone (it
  checks utility classes are defined, which is a different question).

The investigation is a `spike` if it grows past one session; today it is a section of this PRD.

## 6. Findings

_(empty — filled by the measurement pass in §4)_

## 7. Definition of done

- The measurement table in §6 exists, and the owner has picked from it.
- `DESIGN.md` §4 (and §7.1, if the site header moves) records the scale that shipped — **the spec is
  updated, not just the CSS**.
- `tests/e2e/test_public_site.py` still passes its header-on-one-line check at 768 px.
- A `tests/uat/ui_refinement_uat.md` is signed: this is a surface a human judges, so per
  `build_principles.md` §VIII "tests pass" is not completion.
- Offers no unsupported certification claim, and does not touch a `locked` row in the copy deck.
