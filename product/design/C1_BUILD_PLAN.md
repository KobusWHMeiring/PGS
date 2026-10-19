# C1 — Public site: build plan

> **Status 2026-10-19 — C1a, C1b, C1c, C4 and C1e landed.** Six routes render, 336 tests
> pass in the gate, 25 Playwright tests pass. What is *not* done: **C2** (`/documents/` —
> the document band carries `Publishing soon` chips until it exists), **C3** (the AF pill
> is a disabled control, not a link), and sub-plan **D**. The nine open questions in §6
> are still open; the defaults in that table are what shipped. **§2** below was resolved
> differently from the plan as written: all six routes exist from C1a, each page owns its
> own headings, and the section partials carry only bodies — see the note under §2.

**Goal:** implement the approved public site (`final_home.html`) as Django templates and semantic
CSS, with the five public routes the redirect map requires, no build step, no CDN, and no claim
the group cannot support.

**Architecture:** `root.css` (tokens, reset, type) + `site.css` (semantic component classes named
after what they are) + `core/templates/public/*.html`. Content constants live in
`core/services/_public.py` and are formatted at the boundary by `pgs_extras.format_zar`, so no fee
figure is typed into a template twice. No JS ships in C1 at all — the only interactive element is
the language pill (C3) and the mobile nav, which is a `<details>` element.

**Inputs (all read before writing this plan):** `MVP0_PLAN_V2.md` C1–C4 · `product/design/DESIGN.md`
· `final_home.html` · `content_inventory.md` · `assets/README.md` · `build_principles.md` ·
`testing_hazards.md` §1.1/§1.6 · SPEC §12, §18.3 (D40) · the OPP, SAOSO and LANDSCAPE PDFs
(verified by `pdftotext -layout`, not by a plan).

**UAT:** `tests/uat/mvp0_standards_and_public_site_uat.md` Scenarios 4, 6, 8 are the human checks
this plan must make judgeable. Nothing in this plan is UAT; it is all assertable.

---

## 1. What is already decided, and what this plan must not re-open

D40 (Tailwind out; `brand-*` only; Lora + Mulish), D21 (preview, not replacement), D22 (seven
documents public), D11 (pasture-raised seal never rendered), D17 (refusal names the four documents),
D18 (translated *shell* only). Read them; do not argue with them here.

## 2. The IA problem this plan resolves

The approved design is a **one-page site with anchor navigation**. `MVP0_PLAN_V2` C1 and the
redirect map (`content_inventory.md` §4) require **five real routes**, because the WordPress URLs
they replace must resolve. Both are binding, so:

- **Nav and CTAs link to real routes.** A one-page site with real pages behind it is the only shape
  in which `/organics/` can return 200 *and* the home page still show its four bands.
- **The home page keeps its ten bands, in the designed order, with the designed grounds.** No
  content moves off it.
- **A sub-page renders the same section partials as the home page, plus the detail that has nowhere
  to live on a single page** (the four IFOAM principles, the committee composition, the member
  categories). The markup is not duplicated; the partial is included by both.
- **Superseded in implementation:** the six routes were built in C1a rather than C1c
  (a link to a route that does not exist raises `NoReverseMatch`, so routes had to exist
  before the header could link to them), and the shared partials carry *bodies* while each
  page owns its own heading — a sub-page's `h1` and the home page's summary of it must not
  share a tag level.
- **`/documents/` does not exist yet.** It is C2. So in C1 the nav carries **4 links + the CTA**,
  the documents rows render a visible `Publishing soon` chip instead of a `Download` link, and the
  footer's Documents column points at `/#documents`. C2 adds the route and wires all three in one
  commit. A link to a route that does not exist is a `NoReverseMatch` — it cannot be shipped
  "temporarily".

## 3. Copy provenance — every string has a source

The rule in this repo is that a claim is checked against `pgs_docs/`, never against a plan. Applied
to copy:

| Copy | Source | Verified |
|---|---|---|
| Six basic elements | `PGS Certification landscape_Final.pdf` p2 — **verbatim**, not the prototype's paraphrase (DESIGN §7.4 says verbatim; the prototype is not) | `pdftotext -layout` |
| IFOAM definition | LANDSCAPE p2, verbatim block quote | ✅ |
| First/Second/Third-party trust | LANDSCAPE p2–3, verbatim, condensed to one line each | ✅ |
| Four IFOAM principles | SAOSO §2.1–2.4 — the opening statement of each principle, verbatim, cited `S2.1`–`S2.4` | ✅ |
| Membership fee R100; PGS SA R500 | OPP §2.1 — "Annual Farmer & consumer Membership fee: R 100", "Currently R500" | ✅ |
| Assessment bands 1 500 / 900 … 8 000 / 8 000 | OPP §2.3 table — matches the design row for row | ✅ |
| "Self-declared, subject to peer review", "payable prior to the visit", "only fully paid-up members eligible", renewal-conditions | OPP §2.3, verbatim | ✅ |
| Visit committee = administrator + 1 consumer + 2 farmers | OPP §3.3 — **not** the live site's "one technical adviser" | ✅ |
| "Farm visits are open to all members and non-members" | OPP §3.3 | ✅ |
| Committee roles | OPP §3.1 table | ✅ |
| Six membership steps | The design's synthesis of OPP §I + §3.3 + §4 | design (approved) |
| Recorded verbal pledge | OPP §I.2, verbatim | ✅ |
| "Roughly from Mossel Bay to the Crags" | live `/members-2/` | live site |
| "Fees payable by end of February" | live `/become-a-member/` — **not in the OPP**. Ships flagged in §6 below | live site |
| Launch date 21 Oct 2018 | live `/` | live site |
| Members: **no names** | POPIA consent unrecorded (`content_inventory.md` §6.2) | — |

## 4. Decisions this plan takes (and why)

| # | Decision | Reason |
|---|---|---|
| P1 | **Fonts are self-hosted woff2** in `core/static/fonts/`, two variable files per family (roman + italic), latin subset only | No CDN, no third-party request on page load (the `implementing-redesigns` Faraday rule and `build_principles` §IV). Latin covers Afrikaans' `ë ê ô û` — verified against the unicode-range block. |
| P2 | **Token set = 15**, not the prototype's 17. Drop `badgeBorder`, `tagGreen` (both 0 uses); fold `tagGreenText`'s single use into `--brand-muted`; rename `brand-sage` → `--brand-ochreInk` (DESIGN §9 #4); **revive `ochreLight` as the accent-on-dark** and **promote `#2B2319` to `--brand-warmDark`** (DESIGN §9 #2 explicitly allows one new token for it). The Tailwind `amber-*` family (used 11× for chips, badges and text-on-dark) collapses into `ochreLight`/`ochreInk`/`sageLight`/`sand`. | §9 defects 2–4, and "a new colour family is a bug". `amber-200` on `forest` was a second palette; `ochreLight` at 10:1 on `forest` replaces it. |
| P3 | **Buttons and nav links get `min-height: 44px`.** The prototype's `px-4 py-2 text-xs` button is 32 px tall | DESIGN rule 5 and `build_principles` §IV are non-negotiable. This is the one visual change from the approved mock. |
| P4 | **A CSS-only mobile menu** (`<details>`) below `md`. The prototype hides the nav on phones and offers no alternative | A phone with no navigation fails UAT Scenario 6 before the chatbot exists. |
| P5 | **No chat input bar in C1.** The two showcase windows ship; the fake "Ask about the standard…" bar does not | A non-functional input is a visible lie. D5 adds the real one. |
| P6 | **Fee figures live in `core/services/_public.py` as integer cents**, rendered through `format_zar` | `build_principles` §III: integer cents, `_cents` suffix, formatting at the boundary. Makes one test able to prove no template hardcodes a fee. |
| P7 | **The documents band ships with a `Publishing soon` chip**, not a dead link | DESIGN rule 8: "unresolved data is a tinted chip… never a plausible-looking fake". |
| P8 | **`id="fees"`, and the footer's broken `Fees → #organics` link is fixed** to `/become-a-member/` | DESIGN §10 records both as defects. |
| P9 | **No favicon artwork is invented.** `logo_mark.png` is copied to `/static/img/favicon.png` and linked as `type="image/png"` | No PIL/ImageMagick on this box; the real SVG favicon is an open designer item (§8). |

## 5. File map

```
core/static/css/root.css          tokens, reset, type, layout primitives  (~180 lines)
core/static/css/site.css          semantic components                     (~700 lines)
core/static/fonts/*.woff2         lora-roman, lora-italic, mulish-roman, mulish-italic
core/static/img/                  logo_mark, social_instagram, social_facebook,
                                  mountain_scene, farm_maize, farm_goats, farm_greens, favicon
core/templates/base.html
core/templates/public/_header.html
core/templates/public/_footer.html
core/templates/public/home.html
core/templates/public/organics.html
core/templates/public/how_it_works.html
core/templates/public/members.html
core/templates/public/become_a_member.html
core/templates/public/contact.html
core/templates/public/sections/_hero.html
core/templates/public/sections/_ribbon.html
core/templates/public/sections/_elements.html
core/templates/public/sections/_how_it_works.html
core/templates/public/sections/_gallery.html
core/templates/public/sections/_fees.html
core/templates/public/sections/_documents.html
core/templates/public/sections/_chat_showcase.html
core/templates/public/sections/_members.html
core/views/_public.py
core/services/_public.py
core/templatetags/pgs_extras.py
core/urls.py                      + 5 routes
core/tests/test_public.py
core/tests/test_pgs_extras.py
tests/e2e/test_public_site.py     (C1e)
```

Both CSS files stay under the 30 KB cap; `site.css` is the one to watch.

---

## Task C1a — Static foundation, base template, `/`

**Files:** `core/static/css/root.css`, `core/static/css/site.css`, `core/static/fonts/*`,
`core/static/img/*`, `core/templates/base.html`, `core/templates/public/_header.html`,
`core/templates/public/_footer.html`, `core/views/_public.py`, `core/urls.py`,
`core/tests/test_public.py`

- [ ] **Step 1 — write the failing tests** in `core/tests/test_public.py`:

```python
PUBLIC_PAGES = [  # never an empty list: an empty parametrize passes vacuously (§1.6)
    ("core:home", "/", "Organic assurance built by"),
    ("core:organics", "/organics/", "Guided by six basic elements"),
    ("core:how_it_works", "/how-it-works/", "How it works"),
    ("core:members", "/members/", "Membership is not certification"),
    ("core:become_a_member", "/become-a-member/", "What membership and assessment cost"),
    ("core:contact", "/contact/", "Who to talk to"),
]
```
  - `test_route_returns_200` — parametrized over `PUBLIC_PAGES`.
  - `test_route_has_its_own_title` — `<title>` differs per page (catches a copy-pasted `<title>`).
  - `test_html_has_lang_attribute` — `<html lang="en">`, not a hardcoded `af`.
  - `test_css_comes_from_static_not_a_cdn` — no `http` in any `<link href>`/`<script src>`.
  - `test_static_files_exist` — every `url()` in `root.css`'s `@font-face` resolves to a file on
    disk. (A missing font file is silent: the browser falls back and the design quietly changes —
    the class of defect DESIGN §10 warns about.)
- [ ] **Step 2 — run them, watch them fail** (`NoReverseMatch` / 404).
- [ ] **Step 3 — build it:** download the four woff2 files and write `@font-face` with
  `font-display: swap`; write `root.css` (15 tokens, reset, `.serif-title`, `.container`,
  `.section`, `.eyebrow`, focus-visible, `prefers-reduced-motion`); copy the seven images from
  `product/design/assets/` (not `_source/`); write `base.html` + header + footer + a home
  skeleton with an `h1`.
- [ ] **Step 4 — run the tests.** PASS.
- [ ] **Step 5 — mutation check:** delete one `@font-face` src file and confirm
  `test_static_files_exist` goes red; restore. Remove `lang` from `<html>`; restore.
- [ ] **Step 6 — commit:** `feat(c1a): public site foundation — tokens, fonts, base template`

## Task C1b — The home page's ten bands

**Files:** `core/templates/public/home.html`, `core/templates/public/sections/_*.html`,
`core/static/css/site.css`, `core/services/_public.py`, `core/templatetags/pgs_extras.py`,
`core/tests/test_public.py`, `core/tests/test_pgs_extras.py`

- [ ] **Step 1 — failing tests:**

```python
def test_format_zar_uses_sa_convention():
    assert format_zar(10_000) == "R100"      # R100, not R100.00
    assert format_zar(150_000) == "R1 500"   # thin space, not a comma
    assert format_zar(280_000) == "R2 800"

def test_no_fee_figure_is_hardcoded_in_a_template():
    """Every figure must arrive via format_zar, or the ribbon and the fee table drift."""
    for path in TEMPLATES.rglob("*.html"):
        source = path.read_text(encoding="utf-8")
        for literal in ("R100", "1 500", "8 000"):
            assert literal not in source, f"{literal!r} typed into {path.name}"

def test_ribbon_figure_matches_the_fee_table(): ...   # both from MEMBERSHIP_FEES
def test_band_grounds_alternate(): ...               # DESIGN §3: the 10 bands carry
                                                      # sageLight / creamWarm / forest / none
def test_members_band_carries_the_disclaimer(client): ...
def test_every_internal_href_reverses(client):
    """A dead link is not a visual defect a UAT reviewer should have to find."""
```

- [ ] **Step 2 — run, watch fail.**
- [ ] **Step 3 — write `core/services/_public.py`:**

```python
@dataclass(frozen=True)
class FeeBand:
    label: str            # "Below R250 000"
    initial_cents: int
    renewal_cents: int

@dataclass(frozen=True)
class PublicContent:
    nav: tuple[NavLink, ...]
    membership_farmer_cents: int
    membership_pgs_sa_cents: int
    fee_bands: tuple[FeeBand, ...]
```
  Figures verbatim from OPP §2.3. One `public_context(page)` helper returns the frozen content plus
  the active page key — so a template never computes anything.
- [ ] **Step 4 — build the nine section partials** in DESIGN §3's order and grounds:
  hero (photo *in the background stack*, never a child `<img>` — DESIGN §7.2), ribbon,
  six elements, how-it-works stepper, gallery, fees, documents (`Publishing soon` chips),
  chat showcase (two windows, no input bar), members (disclaimer). Then the footer.
- [ ] **Step 5 — tests pass.**
- [ ] **Step 6 — mutation check:** type `R100` into `_ribbon.html` and confirm
  `test_no_fee_figure_is_hardcoded_in_a_template` goes red; restore. Remove the disclaimer and
  confirm its test goes red; restore.
- [ ] **Step 7 — commit:** `feat(c1b): home page — ten bands, fees from OPP §2.3, no claim beyond OPP`

## Task C1c — The five routes

**Files:** `core/templates/public/{organics,how_it_works,members,become_a_member,contact}.html`,
`core/views/_public.py`, `core/urls.py`, `core/tests/test_public.py`

- [ ] **Step 1 — failing tests:** the `PUBLIC_PAGES` 200s (already written in C1a), plus
  `test_no_dead_internal_links` extended across all five, and:
  `test_views_are_thin` — every view function is ≤ 20 lines (mirrors `test_health.py`;
  §II "thin views").
- [ ] **Step 2 — run, watch fail.**
- [ ] **Step 3 — build the five pages** as page-header + reused section partials + the detail that
  will not fit on the home page:
  - `/organics/` — six elements (shared partial) + **the four IFOAM principles** (SAOSO §2.1–2.4,
    cited) + the IFOAM definition + **first/second/third-party trust** (LANDSCAPE).
  - `/how-it-works/` — the stepper (shared) + visit committee composition (OPP §3.3) + "visits are
    open to members and non-members" + "fees are payable before the visit".
  - `/members/` — disclaimer (shared partial) + catchment ("roughly from Mossel Bay to the
    Crags") + the three member categories + the `names & consent — POPIA` chip. **No names.**
  - `/become-a-member/` — the "Which band are you in?" panel **first** (DESIGN §7.7) + both tables
    + OPP §2.3's conditions.
  - `/contact/` — contact placeholder chips + OPP §3.1 committee roles + socials.
- [ ] **Step 4 — tests pass.**
- [ ] **Step 5 — commit:** `feat(c1c): /organics/ /how-it-works/ /members/ /become-a-member/ /contact/`

## Task C1d — Claim discipline (C4, pulled forward because C1 writes the copy)

**Files:** `core/tests/test_claim_discipline.py`

- [ ] **Step 1 — write the test** exactly as `MVP0_PLAN_V2` C4 specifies, over all six routes:

```python
FORBIDDEN = ["pasture raised", "pasture-raised", "GMO free", "biodynamic",
             "chemical-free", "spray-free"]
```
  plus: no active seal name appears with wording that differs from OPP §V; the members page carries
  the disclaimer; `Publishing soon` is not a link.
- [ ] **Step 2 — prove it can fail:** add "pasture raised" to a template, watch it go red, restore.
  Then remove the test's `FORBIDDEN` list contents and watch it pass vacuously — that is the trap
  it must not have, so assert `FORBIDDEN` is non-empty **and** each term is actually absent.
- [ ] **Step 3 — commit:** `test(c4): no unsupported certification claim on any public route`

## Task C1e — Playwright

**Files:** `tests/e2e/test_public_site.py`, `tests/e2e/conftest.py`, `pytest.ini`,
`requirements.txt`

- [ ] **Step 1 — add `pytest-playwright`, install Chromium, register a marker** in `pytest.ini`
  (`e2e`) and keep `tests/e2e` outside `testpaths`, so `verify.sh` stays fast and green offline.
  Document the invocation: `python -m pytest tests/e2e -q`.
- [ ] **Step 2 — one test per route** with `live_server`: 200, the expected `h1`, the `EXPECTED`
  heading, and no console error.
- [ ] **Step 3 — the 390 px check** per route: `scrollWidth <= viewport width` (no horizontal
  overflow — the actual phone failure mode, not a screenshot).
- [ ] **Step 4 — the touch-target check:** every `.btn`, every `nav a` and the language pill has a
  bounding box ≥ 44 px in at least one dimension and ≥ 24 px in the other (WCAG 2.2 AA target
  size). **This is the check that proves P3.**
- [ ] **Step 5 — commit:** `test(c1e): Playwright — six routes, 390px, 44px targets`

---

## 6. Open — needs the product owner, not the code

Recorded rather than guessed. Each ships with a visible placeholder chip until answered.

| # | Question | Default this plan takes |
|---|---|---|
| 1 | **Contact details** — publish Sasha Mentz / Rebecca Dixon's real email and cell numbers (they are on the live site today), or keep the visible `email`/`phone` chips? | **Chips.** Publishing a personal cell number is a decision about a named person, not a design detail. |
| 2 | **Bank details** — `NU HORUS NPO`, ABSA, `9288670349`, reference format. On `/become-a-member/` or not? | **Omitted**, with a chip. |
| 3 | **News** in the nav? The live site has two News pages (one empty since 2019). | **Not in C1.** No route, no nav link. |
| 4 | **`/endorsed-farms/`** — no honest MVP 0 target. Redirect target or 410? | **Not in C1** (redirect map is MVP 2). |
| 5 | **Pledge downloads** (farmer + consumer) — D22's seven excludes them; `content_inventory` gap #8 says they are missing. | **Not in C1.** `Publishing soon` chip on the documents band. |
| 6 | **"SOP's"** — is it the OPP under another name? (`content_inventory` §6.7) | **Assumed yes**; C2 lists seven items, not nine. |
| 7 | **"Fees payable by end of February"** — on the live site, **not in the OPP**. Publish it? | **Published**, sourced to the live site and flagged here. Say if it should go. |
| 8 | **Photography consent** — four of the group's own photographs, no identifiable people, consent unrecorded. | **Published** with the `farm attribution & consent to confirm` chip, exactly as the design has it. |
| 9 | **Six-elements copy** — verbatim from LANDSCAPE (DESIGN §7.4's instruction) versus the prototype's paraphrase. | **Verbatim.** Say if the paraphrase was deliberate. |

## 7. Verification

```bash
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh

python -m pytest tests/e2e -q          # C1e only; needs Chromium
python manage.py runserver             # then judge UAT scenarios 4, 6, 8 by eye
```

## 8. Deliberately not in C1

Documents download (`/documents/`, C2) · the language switch (C3 — the pill renders, `AF` is
inert) · the chatbot's behaviour (D) · seals, QR, registry (MVP 2) · an SVG of the mark and a real
favicon (designer) · a reversed logo lockup (designer).
