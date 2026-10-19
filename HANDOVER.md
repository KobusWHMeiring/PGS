# Handover — MVP 0 Implementation

**For:** the next agent.
**From:** the design session, 2026-10-19.
**Repo state:** `main`, **10 commits**, **no application code yet**. Spec, two PRDs, two plans, two
UATs, and now a complete public-site design with its evidence.
**Supersedes:** the 2026-10-18 handover (`git show 8df2a41:HANDOVER.md`).

---

## 0. The one thing to know first

**There is still no code in this repository.** No `manage.py`, no `core/`, no `knowledge/`. Every
plan here is a plan.

The `MVP1A_PLAN.md` §0.2 heading used to imply MVP 0 already existed. It has been corrected:
**MVP 0 sub-plan A (Tasks A1–A10) is a hard prerequisite for MVP 1a.** It delivers the scaffold,
the environment-driven settings, and — critically — the **custom `User` model, which must be the
first migration in the database.** You cannot swap it later without pain.

Nothing else from MVP 0 (corpus, public site, chatbot) is a prerequisite for 1a.

**What changed in this session:** the public site now has a *design* (not a build). §8 is the
detail. It does not change the answer to "what do I build first" — that is still Task A1.

---

## 1. Read these first, in this order

| # | Artifact | Why | Time |
|---|---|---|---|
| 1 | `product/backlog/ready/MVP0_PLAN_V2.md` §0–§2 + Tasks A1–A10 | **Your actual first work.** | 25 min |
| 2 | `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` **§18.3 first**, then §4.1–§4.5 | 40 decisions. **Read §18.3 before questioning anything** — most "obvious improvements" were considered and rejected. | 45 min |
| 3 | `product/docs/context/build_principles.md` | Non-negotiable. Thin views, service ownership, 30 KB cap, integer cents, no logic in templates. | 10 min |
| 4 | `product/backlog/ready/MVP1A_PLAN.md` + `MVP1A_PRD.md` | The 1a task list and its fence. | 45 min |
| 5 | `product/design/DESIGN.md` | **Only when you are designing or changing a front-end view.** Front-end scope only. | 15 min |
| 6 | `tests/uat/mvp1a_in_office_visit_uat.md` | What humans will judge. Read the `Judgement:` clauses. | 10 min |
| 7 | `pgs_docs/` | The authoritative source documents. **Spot-check domain claims against these, never against a plan.** | as needed |

Do **not** read `prd.md` as the spec (superseded provenance), and do **not** execute
`product/backlog/Done/MVP0_PLAN.md` (superseded — its SAOSO parser matched nothing in the real PDF).

---

## 2. Build order — the answer to "website first, then the chatbot?"

The plan's dependency graph (`MVP0_PLAN_V2.md` §1) is explicit:

```
A (foundation) ──┬─► B (corpus) ──► D (chatbot)
                 └─► C (site) ────►
```

**"A gates everything. B and C can run in parallel once A is green. D needs B (retrieval) and C
(the surface it sits in)."**

So it is **not** "website, then RAG". The corpus (B: ingest → chunk → embed → hybrid retrieve) is
the *RAG core*, and it is a **prerequisite for the chatbot**, running **alongside** the site rather
than after it. Linearly, `MVP0_PRD.md` §6 gives A1–A10 → B1–B7 → C1–C4 → D1–D4.

Two consequences worth internalising:

- **B is where the real technical risk lives** (PRD risk R-A: a parser that passes a hand-written
  fixture and fails on the shipped PDF). It is also what both C's citations and D's answers depend
  on. Do not defer it behind the site because the site feels more visible.
- **C needs only B's *citation format*** (D14/D15: `S20.1.1`, `sub_ref` depth ≤ 3, `anchor`), not
  its retrieval. So C can largely be built in parallel — the one deferred piece is wiring citation
  chips and `/documents/` deep-links.

**The public site's design is already done** (§8) — that is a head start on C1, not a reordering.

**Also resolved this session:** the previous handover left open whether MVP 0's B/C/D or MVP 1a
comes first, and said "ask before assuming". **The answer is MVP 0 first**, decided by the product
owner.

---

## 3. Decided — do not re-litigate

`PGS_PLATFORM_SPEC.md` §18.3 holds **D1–D40**. The ones most likely to tempt a re-open:

- **D25 — MVP 1 is two increments, one ship gate.** 1a = in-office breadth; 1b = in-field depth.
  Rationale: `product/design/d1_mvp1_shape_exploration.html`.
- **D26 — the 0∥ spike gates the `1∥` seam contract.** Sub-plan G of the 1a plan must not start first.
- **D11 / D22 — the pasture-raised seal is inactive and is *never rendered*.** Issuance is
  hard-blocked when `is_active=False`, with no override. `test_claim_discipline.py` fails the build
  on `pasture raised`, `GMO free`, `biodynamic`, `chemical-free`, `spray-free`.
- **D27 — verdict polarity is template data.** `is_compliant` is derived, never authored.
- **D31 — the pledge's land-history periods conflict with OPP §V and are NOT resolved in code.**
  Record what was attested, set `land_history_conflict`, infer nothing. Awaiting a group decision.
- **D33 — 1a stops at `UNDER_REVIEW`.** No outcomes, no seals, no certificates.
- **D40 — Tailwind is out.** The site design is a *visual specification*, not a code asset. C1
  implements it as `root.css` + a semantic `site.css`. Palette and type are fixed in
  `product/design/DESIGN.md`. **Details in §8.3.**

---

## 4. Do not build these

- **Any MVP 2 model**: `CertificationDecision`, `ProductOutcome`, `Certificate`,
  `CertificateProduct`, `PublicVerificationEvent`, anything in `_aggregation.py`.
- **The registry, QR or verification pages** — they publish certification status, and 1a produces none.
- **Voice-note UI or transcription.** `VoiceNote` *is* migrated now (schema only) per §17.2.
- **Templates for Animal Husbandry, Seed Production or Agro-processing** — Crops only (D28).
- **Anything in MVP 0's C or D sub-plans**, unless you have been asked to reorder to it (§2).

---

## 5. Gates

| Gate | What it means |
|---|---|
| **MVP 0 A1–A5 migrated** | Before any 1a model. The custom `User` must be first. |
| **0∥ spike complete** | Before `1∥` freezes `visitPack` / `VisitSyncEnvelope`. **Sub-plan G (1a) does not start until then.** |
| **Task B3 needs a second reader** | Authoring the Crops template is 38 questions and 37 verdicts by hand. A template that is 80% complete looks complete. Have someone read the JSON against printed FORM Sheet B.1. |
| **1a UAT** | Eight human-judged scenarios. Scenarios 3 and 6 need the *administrator's own machine*. |
| **C1's design is approved** | The design in §8 is approved as *design*. It has never been built, so nothing about it is verified in code. |

---

## 6. Traps that will bite

1. **The polarity trap (R1a-2).** Mis-assigning polarity does not crash — it produces plausible,
   wrong data. `V16` "Are there any risks of contamination of the water source?" answered *Yes*
   means **non-compliant**; with the naive `is_compliant = (value == YES)` it stores as compliant and
   looks fine until someone queries it in MVP 3. `V3` is `INFORMATIONAL`; `V23` and Animal `V14` are
   `NEGATIVE`. The tests assert these explicitly.
2. **Section formats are not what they look like.** If you touch ingestion (sub-plan B), read spec
   §4.5's six verified realities first: SAOSO prints `20.1.1.` (**never** `B-20.1.1`), part letters
   are running page headers present on only 22 of 98 pages, the TOC matches the clause pattern, and
   appendix headings exist only in the TOC.
3. **`GeneratedField(SearchVector(...))`** may not cooperate with the Postgres version in Compose.
   Fall back to a trigger and say so in the module docstring.
4. **`OVERDUE` is derived from `due_on`, never stored.** Otherwise a nightly job becomes load-bearing
   for correctness, and it will eventually not run.
5. **Never `except: pass`.** Sentry on every exception path, explicit `timeout=` on every external call.
6. **Run the thing before you believe it.** The most expensive error in this project's history was a
   parser written against an assumed format that matched zero lines of the real document — *and whose
   tests passed, because the fixtures were hand-written.* Fixtures must be verbatim extracts.
7. **Delivered HTML may be markdown-escaped — and that silently breaks it.** Both design source files
   arrived with `\&`, `\[`, `\*` and `&#x20;` escaping. `fontFamily: \['Lora', …\]` is a JS
   `SyntaxError` that killed the whole `tailwind.config` (so *no* colour resolved), and `/\* … \*/` is
   not a CSS comment, so it discarded the rule that followed. **A new token can be silently absent
   rather than visibly wrong.** If something looks unstyled, check computed style — do not read the class.
8. **A Tailwind class may do nothing.** `shadow-xs` and `shadow-2xs` are **v4** names; the CDN serves
   **v3**. 36 of 48 shadow usages on the design page are dead, silently. Same lesson as 7.
9. **The WordPress media API is not public** — `/wp/v2/.../media` returns **401**. Asset inventory
   must come from `sitemap.xml` (`<image:loc>`) and page markup, which means it is **incomplete**.
10. **`.gitignore`-adjacent:** none — but note `git config core.autocrlf=true` on this machine. Fixed
    this session by `.gitattributes` (§9), so do not re-add line-ending rules.

---

## 7. Commands

```bash
python product/backlog.py            # dry-run: drift + suggested moves
python product/backlog.py --write    # regenerate the index (never hand-edit backlog.md)
python product/backlog.py --apply    # move files to match Status: + regenerate

pytest -q                            # after the foundation exists
lint-imports                         # knowledge must never import core

docker compose up -d                 # Postgres+pgvector and Redis only; the app runs natively
```

Use the **local** skills `.agents/skills/pgs-reading-the-backlog`, `pgs-maintaining-the-backlog`,
`pgs-writing-explorations` — not their generically-named counterparts, which assume other layouts.

**To render a design page and check it for real** (Playwright and system Chrome are installed):

```python
from playwright.sync_api import sync_playwright
import pathlib
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")          # system Chrome, no browser download
    pg = b.new_page(viewport={"width": 1440, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(pathlib.Path("product/design/final_home.html").resolve().as_uri(), wait_until="networkidle")
    ...
```

Run such a script from a **clean directory**: a stray `inspect.py` in the temp dir shadows the
stdlib module and Playwright fails with a confusing `AttributeError`.

---

## 8. What the design session produced (2026-10-19)

Committed as `7b16846`. No application code — this is design and evidence only.

### 8.1 The artefact

**`product/design/final_home.html`** — the design of record for the MVP 0 public home page, 54 KB,
self-contained apart from the Tailwind CDN and Google Fonts. Composition chosen by the product owner:
header / hero / six elements / how it works / documents / ask the standard / members / footer from
`redesign1`; key-facts ribbon and fees schedule from `redesign2`.

All body copy is **quoted from `pgs_docs/`** — the six basic elements verbatim from the certification
landscape, the fees table from OPP §II, the procedure from OPP §I. Nothing is invented prose. No
certification claim is made.

Supporting: `DESIGN.md` (the design system), `content_inventory.md` (the live site), `assets/`
(logo, social, photographs, with provenance), `visual_language/` (three superseded explorations).

### 8.2 The evidence, not just the artefact

`content_inventory.md` inventories the **live WordPress site** from its sitemap and REST API —
**13 URLs**, page by page, with word counts. It found **16 items the new design would drop**, 11 of
them unintentional. Three change a section's *shape*:

1. The live site carries **two different taxonomies** — the **four IFOAM principles** (health,
   ecology, fairness, care) on `/organics/`, and the **six basic elements of PGS**. The design shows
   the six and calls the section "Organics". They are not interchangeable.
2. The best explanatory passage on the site (*"three manners by which trust is established"* —
   first-party, PGS, third-party) is absent from the design.
3. There is a **third membership category**: value chain actors.

It also proves the claim problem is **live, not hypothetical**: `/endorsed-farms/` says *"certified
pasture raised … GMO free"* right now, in **prose while displaying no seal image** — which is why a
grep test catches it and an image review never would.

**And it corrects a number in the previous handover:** POPIA exposure is **31 unique consumer names**
and **13 farmer members**, not "~24". The old figure undercounted by about 30%.

### 8.3 Decisions made

**D40 (spec §18.3): Tailwind is out.** The design was authored with Tailwind utilities via
`cdn.tailwindcss.com`, which ships a CSS compiler to the browser and collides with
`build_principles.md` §IV (*"No Tailwind build step"*). It is a **visual specification, not a code
asset** — C1 implements it as `root.css` + a semantic `site.css`, per the `implementing-redesigns`
route.

Fixed and recorded in `DESIGN.md`: the **17 `brand-*` tokens**, **Lora** (display, kept at
`font-normal` — that is most of the design's character) + **Mulish** (body), and the section band
rhythm. `DESIGN.md` is scoped to front-end design and is the **only permitted source of tokens**.

**Scale of the C1 conversion: 317 unique utility classes across 2038 tokens on this page alone.**
Not started. It is not a find-and-replace.

### 8.4 Defects found — all measured, none guessed

In the delivered source designs (fixed):

| Defect | Effect |
|---|---|
| `fontFamily: \['Lora', …\]` | JS `SyntaxError` → the **entire `tailwind.config` died**, so no `brand-*` colour resolved at all |
| `/\* … \*/` | Not a CSS comment → discarded the hero background rule |
| 68 × escaped `\[` | 52 dead arbitrary-value utility classes |
| `redesign1`'s hero wrapper contained its own ribbon | Swapping in `redesign2`'s ribbon left the wrapper unclosed |

Still present, to fix during the C1 rewrite (`DESIGN.md` §9): **36 of 48 shadow usages are dead**
(v4 names on a v3 CDN); **3 raw hex values in classes**, two of them off-palette; **4 declared-but-unused
tokens**; `brand-sage` is a brown-gold; no favicon; no `id="fees"` so the fees section is unreachable
from the nav; the footer's `email`/`phone` chips have no real data.

### 8.5 One finding worth carrying forward

Adding the hero photograph introduced an accessibility defect that **looked fine**: as a child `<img>`,
the photo painted *over* the gradient overlay (an element's background paints below its positioned
children), leaving the pale mountain sky behind the headline at **1.05:1** contrast. Moved into the
element's own `background` stack: **8.17:1** median, **4.93:1** worst case.

The method is the point — sample the **rendered** backdrop and compute the ratio. It is in `DESIGN.md`
§7.2 so a future refactor re-measures instead of assuming.

### 8.6 Assets

`product/design/assets/README.md` has full provenance. Two constraints that shape design work:

- **The logo lockup is light-background-only.** The `PGS | SOUTH AFRICA` wordmark is solid black and
  vanishes on dark. Use the **mark** on dark and HTML text for the wordmark. A reversed lockup must be
  **requested from the designer, not recoloured by us**.
- **The lockup needs ≥400 px to be legible** — at a header's ~190 px, `SOUTH AFRICA` is ~5 px tall. So
  it is deliberately unplaced rather than squeezed in.

`assets/_source/` holds the untouched originals (3.3 MB). They are committed **because the WordPress
site is slated for retirement and these would otherwise be lost.** Prunable if the repo must shrink.

---

## 9. Done this session, outside the design

- **`.gitattributes`** (`d673371`) — `* text=auto eol=lf` plus explicit binary rules. Task A1 asked
  for this and it was missing; every text file was emitting a CRLF warning. The binary rules matter:
  `pgs_docs/*.pdf` and `*.xlsx` are the group's evidence and the design assets are their artwork —
  normalising either as text is not recoverable from the repository. `git add --renormalize .` staged
  no content change.
- **`AGENTS.md`** — the design doc is now in "Read these first", scoped to designing or changing a
  view, plus two conventions that bite.
- **Spec §18.3 D40** and the regenerated `backlog.md`. `python product/backlog.py` reports **0 drift**.

---

## 10. Open — not yours to resolve

| Item | Blocked on | Affects |
|---|---|---|
| **D31 — which land-history periods govern** (pledge 12/12/18 vs OPP §V 18/12/12) | **The group** | MVP 2 seal issuance. A certification-integrity question, not a software one. |
| **POPIA consent** for the already-published ~31 consumer names, 13 farmer members, and the new photographs | **The group** | MVP 2 registry; whether `/members/` reproduces them |
| **The 16 content gaps** in `content_inventory.md` §3 | A design/writing task | C1 |
| **`/endorsed-farms/`** — 2026 and 2025 per-product outcomes are live; MVP 0 publishes none | **The group** | The redirect map. Publishing nothing is correct for MVP 0 but is a visible content loss. |
| **Bank details** (`NU HORUS NPO`, ABSA) are published today and absent from the design | Someone who knows the intent | C1 |
| **News** in the nav or not; the live site has two News pages | Product decision | C1 scope |
| **Seal cardinality**; which seal applies to "Organic - pending corrective action" | MVP 2 modelling | MVP 2 |
| **`standard_ref` coverage** — clause mappings for the ~91 non-agro-processing verdicts | Authoring effort | MVP 3 gap analysis |
| **Hosting cutover to the VPS** | MVP 2 | Docker on a shared box vs native gunicorn |
| **UAT sign-off seats** (administrator, committee reviewer, consumer member) | **The human** | 1a acceptance |
| **A reversed logo lockup and an SVG of the mark** | The designer | C1 |

---

## 11. What happened in the earlier sessions

Compressed, so the state can be trusted without reading the history.

1. **Full review of the target-state spec against the source PDFs.** Found that the MVP 0 SAOSO
   parser matched **nothing** in the real document (`B-20.1.1` was invented), that the OPP parser
   could not reach §V or §VI, that "notifiable exception" was defined backwards, and that the
   pasture-raised seal was specified as both active and not-shipped. Applied as **F1–F5**, recorded
   as **D14–D24**.
2. **A parser was run over the shipped PDFs** before any plan was rewritten. Six further realities
   are now in spec §4.5 — the most useful being that part letters come from running page headers.
3. **MVP 0 re-planned**; v1 retired to `Done/` as superseded.
4. **MVP 1's shape decided** (D25/D26) via `product/design/d1_mvp1_shape_exploration.html`.
5. **MVP 1a specified**: PRD, 32-task plan, UAT, plus **D27–D33**.
6. **D34–D39** — 1a field decisions (geo fields, `current_status`, `FarmCategory.status`, catchment,
   `probation_until`, identifier conventions).
7. **This session** — the public-site design, the live-site content inventory, the design system,
   `.gitattributes`, and **D40**.
