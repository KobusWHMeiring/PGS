# DESIGN.md — Outeniqua PGS Digital Platform

**Status:** Active — decided.
**Scope:** **front-end design only** — new views, new components, restyling existing ones. This
document does **not** govern data modelling, service shape or template logic; that is
`product/docs/context/build_principles.md`. Do not read it to build a model.
**Applies to:** the public site, the farmer portal, the assessor PWA, the registry, the chat surface.
**Last Updated:** 2026-10-19
**Derived from:** `product/design/final_home.html` — every value below was measured from that file,
not chosen in the abstract.
**Companion docs:** `assets/README.md` (image provenance and constraints), `content_inventory.md`
(what the design must carry), `product/docs/context/build_principles.md` (architecture).

---

## 0. What this is, and what it replaces

There was no design system in this repo. Three HTML artifacts in `product/design/` used a third,
unrelated palette. This file exists so that MVP 0 sub-plan C **implements** a design rather than
inventing one, and so a fourth palette never happens.

**Read this section if you are about to disagree with something below.**

| Stage | Outcome |
|---|---|
| `vl_a_home_v2.html` — Modern Pastoralist `--m-*` tokens, Inter + Playfair, warm cream | **Superseded.** Explored and abandoned. Do not copy its tokens. |
| `vl_b_home.html` — institutional palette, system fonts | **Rejected.** Two of its ideas survived into §7. |
| `vl_c_home.html` — literal Organo clone | **Rejected**, but its warmth informed the cream base. |
| `redesign1.html` / `redesign2.html` — Tailwind, Lora + Mulish, `brand-*` palette | The direction. |
| **`final_home.html`** — the composition | **This is the design of record.** |

**One palette, and it is this one.** `brand-*` tokens only (§2). A new colour family is a bug, not
a preference.

---

## 1. Claim discipline comes before aesthetics

A design constraint, not a legal footnote. It shapes copy, imagery and components.

> The public surface may reproduce only the four FORM outcomes and the **active** seals. The
> pasture-raised seal is inactive and is **never rendered**. "GMO free", "biodynamic",
> "chemical-free" and "spray-free" are producer statements, never PGS endorsements. Membership is
> never implied to be certification.

`core/tests/test_claim_discipline.py` greps rendered HTML for the six forbidden terms. It does
**not** catch tone — UAT Scenario 8 does, and no prototype can satisfy it alone.

**Concretely, for design:** the live `/endorsed-farms/` page publishes *"certified pasture raised …
GMO free"* **in prose while displaying no seal image at all**. The claim is text, not artwork —
which is why a grep test catches it and an image review would not. Read
`content_inventory.md` §5 before writing copy for any members or status surface.

**No seals in MVP 0.** `MVP0_PRD.md` §3: *"…while publishing no farm status, no certificate, no
seal and no QR code."* Seals are MVP 2. The group's *logo* is not a seal and is fine.

---

## 2. Tokens

All 17 are declared in `final_home.html`'s inline `tailwind.config`. Usage counts are measured
across that file.

### 2.1 Surfaces

| Token | Value | Uses | Role |
|---|---|---|---|
| `brand-cream` | `#FDFBF7` | 27 | **Page ground.** Also `<body>` background. |
| `brand-creamWarm` | `#F6F1E7` | 10 | Alternating section band |
| `brand-sageLight` | `#F3ECE0` | 7 | Trust-ribbon ground |
| `brand-sand` | `#E6DECE` | 50 | Dividers, hairlines, inactive tracks, chip borders |
| `brand-badgeBorder` | `#D8CEBA` | **0** | **Dead — see §9** |

### 2.2 Ink

| Token | Value | Uses | Role |
|---|---|---|---|
| `brand-charcoal` | `#282622` | 25 | Primary body text |
| `brand-muted` | `#6B665D` | 51 | Secondary text, captions, notes — **the most-used token** |
| `brand-forestDark` | `#242D1E` | 29 | Headings on light |
| `brand-forest` | `#323E2A` | 13 | Dark band ground, primary buttons, header |
| `brand-forestDeep` | `#1A2116` | 1 | Footer ground |

### 2.3 Accent

| Token | Value | Uses | Role |
|---|---|---|---|
| `brand-ochre` | `#B87B2E` | 44 | **The accent.** Links, hover, eyebrows, key figures, dots |
| `brand-ochreDark` | `#9C641E` | 17 | Accent hover / pressed |
| `brand-ochreLight` | `#F9F1E2` | **0** | **Dead — see §9** |
| `brand-moss` | `#425337` | 4 | Rare mid-green |
| `brand-sage` | `#8A6828` | 5 | **Misnamed** — this is a brown-gold, not a sage green. Rename or use `ochreDark`. |
| `brand-tagGreen` | `#EFE6CE` | **0** | **Dead** |
| `brand-tagGreenText` | `#785012` | **0** | **Dead** |

**Naming is inconsistent** (`sage` is gold; `tagGreen` is cream) and four tokens are unused. That
is tolerated for now but should not spread — see §9.

---

## 3. Surfaces and the band rhythm

Depth comes from **alternating grounds**, not borders. In document order:

| # | Section | Ground |
|---|---|---|
| 1 | Hero | `.hero-contour-bg` — **photograph** under a dark radial gradient (§7.2) |
| 2 | Key-facts ribbon | `brand-sageLight` |
| 3 | Six elements | *(none → page ground)* |
| 4 | How it works | `brand-creamWarm` |
| 5 | Farm gallery | *(none → page ground)* — **added 2026-10-19** |
| 6 | Why join | `brand-creamWarm` — **added 2026-10-29** |
| 7 | Fees | *(none → page ground)* |
| 8 | Documents | `brand-creamWarm` |
| 9 | Ask the standard | `brand-forest` — the dark beat |
| 10 | Members | *(none → page ground)* |
| 11 | Footer | `brand-forestDeep` |

**The rule:** a band either carries one of the four grounds above or is unset. Never invent a fifth.
Only **one** dark band exists (#9) — a second would flatten the contrast that makes it read as a
moment.

---

## 4. Type

Two families, both from Google Fonts. **Lora** (transitional serif) for display; **Mulish**
(humanist sans) for everything else.

| Role | Classes | Family |
|---|---|---|
| Hero `h1` | `serif-title text-4xl sm:text-5xl md:text-6xl leading-[1.12] tracking-tight` | Lora |
| Section `h2` | `serif-title text-3xl sm:text-4xl tracking-tight` | Lora |
| Card `h3` | `serif-title text-lg font-bold` | Lora |
| Micro-heading `h4`/`h5` | `text-[11px] font-bold uppercase tracking-wider` | Mulish |
| Body | `text-xs` – `text-base` | Mulish |
| Eyebrow | `text-[11px] font-semibold uppercase tracking-widest` | Mulish |

**Lora is used at `font-normal` for `h1` and `h2` — not bold.** That is deliberate and is most of
the design's character: literary, calm, unhurried. Bold serif headings would make it a different
site. Body sizes are small (`text-xs` is common) because the palette carries the hierarchy.

A `.serif-title` utility applies `letter-spacing: -0.015em`. `body` sets
`font-feature-settings: "cv02","cv03","cv04","cv11"` and antialiasing.

---

## 5. Radii, shadows, motion

**Radii** — measured distribution: `rounded-full` ×24 (buttons, pills, dots, chips),
`rounded-lg` ×21, `rounded-xl` ×12, `rounded-2xl` ×8 (the ribbon tag cards), `rounded-md` ×2.
There is **no** "minimum radius for a card" rule here; the design uses `lg`/`xl` for small
surfaces and `2xl` for the ribbon cards. Match the local pattern rather than imposing one.

**Shadows** — measured: `shadow-xs` ×31, `shadow-md` ×7, `shadow-2xs` ×5, `shadow-sm` ×2,
`shadow-lg` ×1, `shadow-2xl` ×2.

> **36 of 48 shadow usages (75%) are dead.** `shadow-xs` and `shadow-2xs` are Tailwind **v4**
> names; the CDN serves **v3**, where they do not exist and are silently dropped. The design
> therefore has almost no depth. See §9.

**Motion** — `transition-colors` on links and chips, `transition-transform` +
`group-hover:scale-105` on the header mark, `transition-all` on buttons. Nothing else animates.
Duration is Tailwind's default (150 ms).

---

## 6. Rules

1. **One palette.** `brand-*` only. No raw hex in a class (§9 has three to fix).
2. **Bands alternate grounds** (§3). Do not separate sections with a 1px border; `border-sand` is
   for hairlines *within* a surface, and `border-white/10` for dividers on dark.
3. **Lora for display, Mulish for everything else.** No third family. Lora stays `font-normal` at
   `h1`/`h2`.
4. **`brand-ochre` is the only accent.** If two things on a screen are ochre, one of them is wrong.
5. **Touch targets ≥44×44 px.** Buttons, nav, the language switch, chat send.
6. **`:focus-visible` on every focusable element.** Never `outline: none`.
7. **Bilingual by default.** EN/AF is a first-class header control, not a footer afterthought.
   MVP 0 ships a translated *shell* only (D18); no page content is machine-translated.
8. **Placeholders stay visible.** Unresolved data is a tinted chip — the footer's `email` / `phone`
   chips are exactly this. Never a plausible-looking fake: a fake phone number in a mockup is a
   real number in production.
9. **No logic in templates.** Formatting lives in `pgs_extras.py` or service-prepared context.
10. **30 KB applies to source files, not prototypes.** `final_home.html` is 51 KB and that is fine
    *for a prototype*. It confirms the production split — `root.css` + `site.css` + templates.

---

## 7. Components

### 7.1 Header

Sticky, `brand-cream` ground, hairline `border-sand` bottom. Left: **the real sprout mark**
(`assets/logo_mark.png`, 40 px) + `OUTENIQUA PGS` / `NATURAL & ORGANIC` as HTML text. Centre: six
nav links in `text-xs uppercase tracking-wider`. Right: EN/AF pill + `Become a member` button
(`rounded-full`, forest ground).

- **The wordmark is HTML text, not an image.** It stays crisp at every size, is translatable, and
  is readable to a screen reader. The raster lockup is not used here — see §8.
- Nav is **6 links + 1 CTA**. `Become a member` is a button, never a seventh link. `Ask`
  (to `/ask/`) joined on 2026-10-20; the header must still hold one line at 768 px and up.

### 7.2 Hero

`.hero-contour-bg`: a **photograph ground** (`assets/mountain_scene.jpg`) with a dark radial
gradient stacked **over** it — `rgba(65,81,54,.78) → rgba(48,60,40,.86) → rgba(32,40,27,.94)`,
top to bottom — plus a `::before` layer of three ochre/moss ellipses for the warm glow.

**The photo must live in the element's own `background` stack, not as a child `<img>`.** An
element's background paints *below* its positioned children, so a child `<img>` covers the
gradient instead of being covered by it — which put the photograph's pale sky directly behind the
headline and dropped contrast to **1.05:1**. Measured after the fix: **8.17:1** median, **4.93:1**
worst case behind the `h1` (needs 3:1 as large text). If you refactor this, re-measure — do not
assume.

Order: region pill → `h1` (two lines, the second in *italic ochre*) → lede → two CTAs →
hairline-separated IFOAM definition. Exactly two CTAs.

**Structural note for implementers:** in `redesign1` the hero wrapper *also* contained the ribbon,
so its closing `</div>` lived inside the ribbon block. In `final_home.html` the wrapper is closed
early so the ribbon is a sibling. **Do not re-nest.**

### 7.3 Key-facts ribbon — the "tags"

`brand-sageLight` band, four cards in a `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5`:
`bg-brand-cream/80 border border-brand-sand/80 rounded-2xl`, each with a 2.5px ochre dot, a Lora
`h4` figure and a `text-xs` muted caption.

Content is fixed: `PGS South Africa / Member group`, `SAOSO v2.1 (2026) / The standard we assess
against`, `6 basic elements / The PGS way of working`, `R100 / year / Farmer & consumer membership`.

### 7.4 Six elements

Page ground, 3×2 grid. Each card: an ochre-tinted icon plate, a Lora `h3`, and a `text-sm` muted
definition. Copy is **verbatim from `pgs_docs/PGS Certification landscape_Final.pdf`** — the six
basic elements of a PGS. Do not paraphrase them.

### 7.5 How it works

`brand-creamWarm` band, six numbered steps (Apply → Pledge → Share → Prepare → Visit → Review),
from OPP §I. Include the recorded-verbal-pledge provision.

### 7.6 Farm gallery — **added 2026-10-19**

Page ground, three photographs in a `sm:grid-cols-3` row, each `rounded-2xl` with a bottom-up
`forestDeep` gradient scrim and a `text-xs` caption. Images are `h-64 sm:h-80 object-cover` and
lift `scale-105` on hover.

**This section is an addition** — it is not in `redesign1`/`redesign2`. It exists because the page
had photography nowhere, and a certification group's credibility rests on farms being real.

**Captions describe only what is visible.** No farm is named, because attribution is not yet
confirmed — an invented farm name in a caption is a factual claim about a real business. The
section carries a visible `farm attribution & consent to confirm` chip for the same reason.

### 7.7 Fees

Page ground. **The "Which band are you in?" panel comes first**, full width, on a cream card with
two buttons; the two tables follow beneath. Turnover is **self-declared** — state that; never
compute a band for the user. Real figures from OPP §II.

**Four cards, not two** (2026-10-29). The fee section showed the membership and the assessment
and omitted OPP §2.4 (visit catering, R30 member / R50 non-member) and §2.5 (R500 seal licence
per farm per annum) — so a reader could budget twice and still be surprised. Catering and the
seal licence are their own cards beneath the first two, never clauses inside them: both are
conditional (a host must offer catering; the farm must be certified and labelling) and neither
may inherit the standing of a fee the OPP sets for everyone.

Closing the band is one **floor** paragraph, `{{ first_year_from_cents|zar }}`, which is
arithmetic on two published figures — the membership plus the lowest assessment band — and
names what it leaves out (transport at the AA rate, catering, the seal licence). It is a
paragraph and not a fifth card, because it is a sum, not a fee.

The **key-facts ribbon** may carry a fee, but never as the only price on the page: its fourth
card reads `R100 / year` with the caption *"Membership, per member — assessment from R1 500"*.
`R100 / year` beside "Farmer & consumer membership" read as the whole cost of joining, and was
technically true — the worst kind of incomplete.

### 7.7a Why join, and where it stands — **added 2026-10-29**

`brand-creamWarm` band between the farm gallery and the fees. Two blocks under one band, because
they are one argument: **why** a member pays, then **whether** the assurance stands up.

- **Four reasons**, 2 × 2 (`.element-grid--pair` — four cards in a three-column grid leave a
  ragged orphan on its own row), each with its OPP citation: farm visit committee, the recorded
  decision, knowledge exchange, and the retailer/market presence on visits. No reason claims a
  farm is certified.
- **“Where this is recognised”** as a `.section__subtitle` (one step down from the band `h2`)
  over a two-column `.role-list`: PGS South Africa membership and its status as the PGS control
  body, SAOSO v2.1 in the IFOAM family, the standing of the PGS seals, and the DALRRD labelling
  rule for animal products. It closes with a **“What we do not claim”** callout, because the two
  things a reader may assume from "recognised" are the two the group cannot claim: the SAOSO
  "Organic PGS Certified" logo (18 months + assessment + a licensing agreement) and
  certification itself.

**Seal names are never written.** Naming a seal's label is rendering the seal as far as
`test_claim_discipline.py` is concerned, and MVP 0 publishes no seal. "The PGS seals" is a
category; a label is a mark.

### 7.8 Documents

`brand-creamWarm` band. Rows of icon tag → title + subtitle → action. The **gated** variant is
visually distinct and its action reads `Request access`, never `Download` (D22).

### 7.9 Ask the standard — the centrepiece

`brand-forest` dark band. **Two chat windows side by side, and both are mandatory:**

- **Answered** — light bubble, `.cite` chips reading `OPP §2.1` / `Fees`, plus a named state badge.
- **Refusal** — a *tinted, warm* bubble (never an error red), and the copy **names the four
  documents the group publishes** (D17), offering the administrator as the next step.

A refusal is a boundary being drawn confidently, not a malfunction (UAT Scenario 3). **Never style
it as an error.** Always show both states together — the contrast is the product's argument.

### 7.10 Members

Page ground, `.disclaimer` card: *"Membership is not certification"* verbatim, plus the sentence
that certification is a separate committee judgement against SAOSO. **Mandatory on any page that
lists or implies members** (OPP requirement; asserted by `test_claim_discipline.py`).

### 7.11 Footer

`brand-forestDeep`. Four columns: brand (mark + name + blurb + **social icons**), The Group,
Documents, Contact. Bottom bar: copyright + *"Membership is not certification. No certification
status is published on this page."*

Social icons use the real published accounts — `instagram.com/pgs_outeniqua`,
`facebook.com/profile.php?id=61579994608416`.

---

## 8. Assets

Full provenance, sizes and constraints: **`assets/README.md`**.

**In use:** the sprout mark (header 40 px, footer 48 px); Instagram and Facebook glyphs (footer);
`mountain_scene.jpg` (hero ground); `farm_maize.jpg`, `farm_goats.jpg`, `farm_greens.jpg` (farm
gallery).

The two constraints that shape design work:

1. **The logo lockup is light-background-only.** The `PGS | SOUTH AFRICA` wordmark is solid black
   and vanishes on dark. Use the **mark** on dark, HTML text for the wordmark. A reversed lockup
   must be **requested from the designer**, not recoloured by us.
2. **The lockup needs ≥400 px to be legible.** It is a two-line letterspaced wordmark; at the
   ~190 px a header would give it, `SOUTH AFRICA` renders about 5 px tall. So it is deliberately
   unplaced rather than squeezed in.

**Not used:** `gourmet-mushroom.jpg` — a phone snapshot with a cluttered background (a wall, a
hand, fabric). Not design-grade; listed here so nobody adds it later thinking it was overlooked.

Also needed: an **SVG** of the mark (flat four-colour art; the PNG is 17.8 KB of alpha) and a
**favicon** generated from it — the page currently declares none.

---

## 9. Known defects to fix in implementation

Measured, not guessed. None are aesthetic opinions.

| # | Defect | Scale | Fix |
|---|---|---|---|
| 1 | `shadow-xs` / `shadow-2xs` are Tailwind v4 names on a v3 CDN → silently dropped | **36 of 48 shadow usages (75%)** | Either upgrade to Tailwind v4 or rename to v3 equivalents. Verify by computed `boxShadow`, not by reading the class. |
| 2 | Raw hex inside class utilities | 3 values: `#F3ECE0` (= `brand-sageLight`), plus `#1C2317`, `#2B2319` which are **off-palette** | Replace with tokens; decide whether the two off-palette darks become `forestDeep` or a new token |
| 3 | Declared-but-unused tokens | 4: `tagGreen`, `tagGreenText`, `badgeBorder`, `ochreLight` | Delete, or use — do not leave them to accumulate |
| 4 | `brand-sage` is a brown-gold, not a sage green | 1 misnamed token, 5 uses | Rename to reflect its value |
| 5 | No favicon | — | Generate from `logo_mark.png` |
| 6 | Tailwind via `cdn.tailwindcss.com` | 1 CDN script | **Blocked on a decision — see §11.1** |

---

## 10. Prototype-only machinery

`final_home.html` was assembled from two design files and carries review scaffolding. **None of it
may reach `core/templates/`.**

- A **`BASE / Cool / Warm`** toggle was present in the footer of `redesign1`; it was removed from
  `final_home.html`. If you see one reappear, it is a regression.
- Both source files were **markdown-escaped** when delivered (`\&`, `\[`, `\*`, `&#x20;`). That
  escaping had broken the page: `fontFamily: \['Lora', …\]` is a JS `SyntaxError` that kills the
  whole `tailwind.config`, and `/\* … \*/` is not a CSS comment. **If a token is new to you, check
  it renders** — an escaped class is a silently missing style, not an error message.
- No `id="fees"` exists, so the fees section is unreachable from the nav. Worth adding.

---

## 11. Open — not decided here

| # | Question | Blocks |
|---|---|---|
| **11.1** | **Tailwind is OUT — decided 2026-10-19.** The design must become semantic CSS. `cdn.tailwindcss.com` is rejected (it ships a CSS compiler to users and Tailwind warns against it). `build_principles.md` §IV forbids a build step, so the path is the `implementing-redesigns` one: extract composition, write `root.css` + `site.css` with **semantic component classes** named after what they are. **Scope: 317 unique utility classes across 2038 tokens on this page alone.** Not yet started. | Sub-plan C; the whole handoff |
| **11.2** | **Photography consent.** Four photographs are now in the design, all the group's own published assets. They include no identifiable people (the greens photo includes a hand). **Consent is still unrecorded**, and POPIA already blocks the member names. | `content_inventory.md` §6 |
| **11.3** | **The 16 content gaps** — 11 are unintentional copy omissions, 3 change a section's shape (the four IFOAM principles beside the six PGS elements; the "three ways trust is established" passage; the value-chain-actor member category). | `content_inventory.md` §3 |
| **11.4** | **News** in the nav or not; **`/endorsed-farms/`** has no honest MVP 0 target; **bank details** and the `NU HORUS NPO` legal entity are on the live site and absent here. | `content_inventory.md` §6 |
| **11.5** | **A reversed logo lockup + SVG** from the designer. | §8 |
| **11.6** | **Hero photo intensity.** The gradient overlay suppresses the photograph heavily — it reads as atmosphere rather than image. Contrast currently has headroom (4.93:1 worst case against a 3:1 requirement), so the wash could be lightened. A judgement call, not a defect. | §7.2 |
