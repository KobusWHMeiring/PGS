# Content inventory — the live WordPress site → the new public site

**Status:** Findings + open decisions. Not a plan.
**Last Updated:** 2026-10-19
**Serves:** MVP 0 sub-plan C (`MVP0_PLAN_V2.md` Task C1, C2), the redirect map required by
`PGS_PLATFORM_SPEC.md` §681, and `product/design/DESIGN.md`.
**Source of record:** `https://pgsouteniqua.wordpress.com/`

---

## 1. Method — so these claims can be checked

Nothing below is recalled or inferred from the PRD. It was read off the live site:

```bash
curl https://pgsouteniqua.wordpress.com/sitemap.xml
curl "https://public-api.wordpress.com/wp/v2/sites/pgsouteniqua.wordpress.com/pages?per_page=50"
curl https://pgsouteniqua.wordpress.com/        # to extract the real nav order
```

**13 URLs** in the sitemap, **12 published pages** returned by the API, plus the bare root.
Page word counts below are computed from `content.rendered`, tags stripped.

Method limits worth stating: this is the *published* surface. Drafts, private pages, media
library items not referenced by a page, and anything behind the Google Drive permission wall
are **not** in scope and are **not** counted here. The Drive dossiers are a separate question —
see §6.

---

## 2. The live surface

**Site title:** *Outeniqua Participatory Guarantee System (PGS) — Local organic certification
for farmers and consumers*

**The real navigation, in order** (11 items — every one a top-level click):

`Home` · `How it works` → `/about-2/` · `Certification` → `/organics/` · `Members` → `/members-2/`
· `Consumer Members` → `/consumers/` · `Farmer Members` → `/farmer-members/` ·
`Become a member` → `/become-a-member/` · `Certified farms` → `/endorsed-farms/` ·
`Contact` → `/contact/` · `Forms` → `/forms/` · `News` → `/news-2/`

| URL | Page title | Words | What it actually holds |
|---|---|---|---|
| `/` | Background | 478 | Launch date **21 Oct 2018**; the *three ways trust is established* (1st-party face-to-face/self-claim, 2nd-party PGS, 3rd-party certification); PGS SA as national body; link to `saoso.org/about-pgs` |
| `/about-2/` | How it works | **1167** | The process: pledge → visit → outcome (*organic* / *organic in conversion* / *not certified*, rescheduled); certificates for **explicitly identified** crops or animal produce; seed production, input-making, agro-processing (soon). Membership fees + benefits. **Farm-visit committee composition: at least two farmers, one technical adviser, one consumer**, plus observers |
| `/organics/` | Certification | 342 | IFOAM definition of organic agriculture; **the four principles — health, ecology, fairness, care**; the SAOSO adoption statement ("approved for inclusion in the IFOAM Family of Standards"); the certification landscape. 1 Drive link |
| `/become-a-member/` | Become a member | 244 | Fees payable **by end of February**; the full turnover fee table; benefits; consumer fee R100; what the proceeds fund; **two pledge downloads**; **bank details — `NU HORUS NPO`, ABSA savings, `9288670349`**; the payment-reference format |
| `/forms/` | Forms | 58 | Nine items, **eight of them Google Drive links**: Basic Production Principles, "SOP's", Certification Landscape form, SAOSO standards, Prep list, the assessment workbook (`.xlsx`), and checklists 7a/7b/7c |
| `/farmer-members/` | Farmer Members | 144 | **13 member entries** — 2026 (4 farms), 2024 (9 farms) — each naming **owner names and localities**. Carries a disclaimer: *"membership does not mean that a farm has been certified by the PGS… Endorsed farmers are listed in the 'farm status' section."* |
| `/consumers/` | Consumer Members | 101 | **33 name entries, 31 unique individuals** — 2026 (21), 2024 (12); Alison Evans and Raymond Auerbach appear in both years, and "Favour Farm" is listed among the consumers. Plus an appeal for new consumer members |
| `/members-2/` | Members | 209 | The best positioning copy on the site: **"Any farmer growing food organically along the Outeniqua mountain range (roughly from Mossel Bay to the Crags) is welcome"**; pledge + fee + two farm visits a year; *"At least one consumer must be part of the visiting committee"*; a **third member category — value chain actors** (Farm Fresh Direct, Wild Oats Farmers' Market) |
| `/endorsed-farms/` | **Certified farms** | 546 | 2026 + 2025 visit outcomes, **per-product** ("certified as organic: Baby Spinach, Green Beans, Beetroot…"). Contact: Rebecca Dixon, `079 391 1162`. 1 Drive **folder** |
| `/contact/` | Contact | 207 | Admin team: Sasha Mentz `pgsouteniqua@gmail.com` `+27 64 922 3532`; Rebecca Dixon `+27 79 391 1162`. Executive committee **elected Aug 2025** (AGM 16 Aug 2025) with named role assignments |
| `/news/` | News | **0** | **Empty page** |
| `/news-2/` | News | 292 | Event content: *"Change of season" talks and seed sharing*; a Prof. Raymond Auerbach talk on soil science. Links a Facebook event, the FB profile, and Instagram |

**Drive dependency, counted:** 8 links on `/forms/`, 1 on `/organics/`, 1 folder on
`/endorsed-farms/` — **10 in total**. `PGS_PLATFORM_SPEC.md` §683 describes this as the
dependency MVP 0 exists to retire.

**Duplicate/near-duplicate pages:** `/news/` and `/news-2/` (both titled "News"; one empty);
`/members-2/` + `/farmer-members/` + `/consumers/` (three pages all answering "who is in the
group"). `/news/` was last modified 2019, `/members-2/` in 2019.

---

## 3. What the current design would drop

`vl_a_home_v2.html` was built from the PRD's marketing list. Against the live site it is missing
**sixteen items**, three of which are not cosmetic. Marked:

- **[GAP]** genuinely missing content
- **[DECISION]** missing on purpose or not — needs the group
- **[SCHEMA]** live content that MVP 0 has no model for

| # | Live content | Where it lives now | Status in the prototype |
|---|---|---|---|
| 1 | **The four IFOAM principles** — health, ecology, fairness, care | `/organics/` | **[GAP]** The prototype shows the *six basic elements of PGS* and presents them as the "Organics" section. The site actually carries **two different taxonomies** — 4 principles of organic agriculture **and** 6 elements of PGS. They are not interchangeable and should not be merged. |
| 2 | **Three ways trust is established** (1st/2nd/3rd party) | `/` | **[GAP]** The single best explanatory passage on the site. It answers "why does a PGS exist" before asking anyone to care about membership. |
| 3 | **Value chain actor members** — a third membership category | `/members-2/` | **[GAP]** Prototype has farmer + consumer only. |
| 4 | **News / events** | `/news-2/` | **[DECISION]** Live nav has News (11 items); the prototype nav has 5 + CTA and no News. |
| 5 | **Legal entity `NU HORUS NPO`** + bank details + reference format | `/become-a-member/` | **[DECISION]** Absent from the prototype. Someone must rule on whether bank details belong on a public page. |
| 6 | **Committee structure and elected roles** (Aug 2025) | `/contact/` | **[GAP]** Real governance content that substantiates "horizontality". |
| 7 | **Contact people and numbers** | `/contact/`, `/endorsed-farms/` | **[GAP]** The prototype shows `[email]` / `[phone]` placeholders. Real, published values exist. |
| 8 | **Pledge downloads** (farmer + consumer) | `/become-a-member/` | **[GAP]** Not in the prototype's 8-item document list, and not obviously in D22's seven. |
| 9 | **Geography: "roughly from Mossel Bay to the Crags"** | `/members-2/` | **[GAP]** Concrete, localising copy. The prototype's hero says only "Western Cape". |
| 10 | **Membership benefits lists** (farmer / consumer) | `/about-2/`, `/become-a-member/` | **[GAP]** |
| 11 | **"Membership is a requirement for any farmer wishing to be PGS endorsed"** | `/become-a-member/` | **[GAP]** States the relationship between membership and endorsement more precisely than the prototype does. |
| 12 | **Fee deadline — end of February** | `/become-a-member/` | **[GAP]** Prototype says "payable before the visit" (also true) but not the annual deadline. |
| 13 | **Farm-visit committee composition** (2 farmers, 1 technical adviser, 1 consumer) | `/about-2/` | **[GAP]** Concrete governance that belongs in "How it works". |
| 14 | **Launch date, 21 October 2018** | `/` | **[GAP]** |
| 15 | **"SOP's"** as a published document | `/forms/` | **[GAP]** Possibly the OPP under another name — needs checking before the document list is finalised. |
| 16 | **Per-product certification outcomes** | `/endorsed-farms/` | **[SCHEMA]** No MVP 0 model. `ProductOutcome` is MVP 2. |

**The 16-item count is the answer to "are we removing data": yes, unintentionally, in 11 places.**
None of them are hard — they are copy and list edits — but three of them (#1, #2, #3) change the
*shape* of a section rather than adding a line to it.

---

## 4. Redirect map

`PGS_PLATFORM_SPEC.md` §681 already requires this. Draft, with the group's decisions flagged:

| Live URL | New URL | Note |
|---|---|---|
| `/` | `/` | Front page is titled *"Background"* — the word is WordPress's, not a content choice |
| `/about-2/` | `/how-it-works/` | Slug is an accident; the page title is already "How it works" |
| `/organics/` | `/organics/` | **Keep the URL, change the content** — live `/organics/` is "Certification"; the new page is the PGS + the four principles. This URL has ranking and its meaning shifts. |
| `/become-a-member/` | `/become-a-member/` | Unchanged |
| `/forms/` | `/documents/` | **Rename.** 8 Drive links point here; highest-value redirect on the map |
| `/members-2/` | `/members/` | Merge — 3 → 1 |
| `/farmer-members/` | `/members/` | Merge |
| `/consumers/` | `/members/` | Merge |
| `/endorsed-farms/` | **?** | **[DECISION]** Live page is *"Certified farms"* and publishes per-product outcomes. MVP 0 publishes **none** of it (MVP 2 registry). Until then this URL has no honest target. |
| `/contact/` | `/contact/` | Unchanged |
| `/news/` | `/news/` or `410` | Empty since 2019 — **[DECISION]** retire or redirect to `/news-2/` |
| `/news-2/` | `/news/` | Merge — 2 → 1 |

---

## 5. Content that must NOT be ported

Read off the live page, quoted precisely:

> `/endorsed-farms/` — *"Also their cattle and sheep with their chickens being **certified
> pasture raised** on certified organic pasture, **GMO free**."*

`pasture raised` and `GMO free` are two of the six terms in `test_claim_discipline.py`'s
`FORBIDDEN` list, and the pasture-raised seal is inactive (D11), never rendered. **This page is
the concrete instance of the problem the PRD was written about** — it is not hypothetical, it is
live right now, and it is why D11 carries a hard block with no override.

Also not to be ported in MVP 0:

- The **per-product organic lists** on `/endorsed-farms/` — 30 items for Favour Farm alone.
  These are `ProductOutcome` rows; MVP 2.
- The framing of `/farmer-members/`'s disclaimer is **right and must be kept**: *"membership does
  not mean that a farm has been certified by the PGS"*. The prototype's disclaimer is a stronger
  version of the same statement. Keep both.

---

## 6. Open decisions — for the group, not for the developer

| # | Decision | Why it is not ours |
|---|---|---|
| 1 | **`/endorsed-farms/`** — 2026 and 2025 outcomes, per-product, currently live. MVP 0 publishes none. What happens to the URL and to that content in the interim? | Publishing nothing is correct for MVP 0 (D33) but it is a **visible content loss** on a page people may be actively using. That is a group call. |
| 2 | **POPIA** — **31 unique consumer names** and **13 farmer members** (with owner names and localities) are already published, without a recorded consent basis. The handover lists this as MVP 2. Does the new `/members/` page reproduce them? | Named individuals' personal data. Already flagged in `HANDOVER.md` §8 — but **that entry says "~24 named consumer members", which undercounts by roughly 30%.** Use 31. |
| 3 | **Photography** — `/endorsed-farms/` carries real farm photographs and there is active Instagram content. Does the public site use them? | Consent, and the same question as #2 in a different medium. |
| 4 | **Bank details** — `NU HORUS NPO` / ABSA / `9288670349` are published today. Republish? | Nobody asked for this to be public; nobody has asked for it to be removed either. |
| 5 | **News** — in the nav or not? Live has it; the prototype does not. | Scope call for sub-plan C. |
| 6 | **The Drive dossiers** — `/endorsed-farms/` grants permission on request. D22 says dossiers become farmer-account-gated in MVP 1, never public. Who tells the current requesters? | Operational, and touches the MVP 0 → MVP 1 boundary. |
| 7 | **Is "SOP's" the OPP?** | Determines whether `/documents/` lists 7 items (D22) or 9 as the live `/forms/` does. |
