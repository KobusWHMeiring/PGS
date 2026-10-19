# Outeniqua PGS Product Backlog

> **Generated index** - do not edit by hand. Regenerate with `python product/backlog.py --write`.
> Generated: 2026-10-19 20:19

## Ready (up next)

- **MVP 1a Implementation Plan — In-Office Visit Flow** - `ready\MVP1A_PLAN.md` - Status: Ready
- **PRD: MVP 1a — In-Office Visit Flow** - `ready\MVP1A_PRD.md` - Status: Ready — all blocking decisions closed (spec §18.3 D27–D39). **Prerequisite satisfied:** MVP 0 sub-plan A (A1–A10) landed 2026-10-19; the custom `User` is migrated and first. See `MVP1A_PLAN.md` §0.2.

## In Progress

- **MVP 0 Implementation Plan (v2) — Standards Foundation & Public Shop Window** - `In Progress\MVP0_PLAN_V2.md` - Status: In Progress — sub-plan **A (A1–A10)**, **B (B1–B7)**, **C1 (C1a–C1e, public pages)**, **C2 (`/documents/`)** and **C4 (claim discipline)** landed 2026-10-19; **C3 (bilingual shell)** is deferred to a later slice (D44, no Afrikaans translator) and **D (chatbot)** remains. Corpus measured end to end: all four documents ingest to **345 chunks** (SAOSO 298, OPP 30, BPP 9, landscape 8), **0 duplicate section refs**. `verify.sh` is green at **387 tests**, plus **30 Playwright tests** that run outside the gate. The §9 group-A gate closed as D27 (verdict polarity is template data) and D14–D15 (citation depth, `sub_ref`, `anchor`); D41–D44 were added while building B and C. C1's implementation notes and its open content decisions live in `product/design/C1_BUILD_PLAN.md` — #7 (the February fee deadline) was **withheld** while building C2.
- **PRD: MVP 0 — Standards Foundation & Public Shop Window** - `In Progress\MVP0_PRD.md` - Status: In Progress — sub-plan A (A1–A10), B (B1–B7), C1 (public site), C2 (`/documents/`) and C4 (claim discipline) landed 2026-10-19; D (chatbot) remains. C3 (bilingual shell) is **deferred out of MVP 0** (spec D44 — no Afrikaans translator). §9 group A closed as D27 and D14–D15. Groups B and C stay open: they are MVP 1 and MVP 2 scope decisions, not MVP 0 blockers. C1's open content decisions are listed in `product/design/C1_BUILD_PLAN.md` §6.

## Refinement

- **Outeniqua PGS Digital Platform — Aimed Design Spec (Target State)** - `Refinement\PGS_PLATFORM_SPEC.md` - Status: Refinement — final PRD review completed 2026-10-18. Findings F1–F5 applied; decisions D14–D24 recorded in §18.3. MVP 0 is specified in `MVP0_PRD.md` and `MVP0_PLAN_V2.md`; it awaits one system brainstorm (`MVP0_PRD.md` §9) before implementation.

## On Hold

_none_

## Spikes

_none_

## Bug Fixes

_none_

## Done

- **MVP 0 Implementation Plan — Standards Foundation & Public Shop Window** - `Done\MVP0_PLAN.md` - Status: Superseded — do not execute; see `MVP0_PLAN_V2.md`

## To Do (ideas without a PRD yet)

# To Do

Ideas that have no PRD file yet. `python product/backlog.py --write` pulls this into
the generated index's "To Do" section.

## Platform

- [ ] Set up `summarise.py` to generate `product/docs/state/` once there is code to summarise.
- [ ] `docker-compose.yml` + `Dockerfile` (MVP 0, sub-plan A).
- [ ] Decide the production host for the platform (the group currently has no server).
- [ ] Add a second physical backup copy — currently a single local external drive (R11, accepted gap).

## Product, deferred from the aimed spec

- [ ] Voice notes — recorder UI and Gemini transcription (`PGS_PLATFORM_SPEC.md` §17.2).
- [ ] "PGS pasture-raised" seal — seeded inactive; enable when the national working
      group publishes criteria (`Seal`, §4.3 / D11).
- [ ] Aggregation approval workflow — case-by-case sign-off, supplying-farm
      declarations, 6-month self-claim expiry, separation checks (§4.4 / D13).
- [ ] Aquaculture, Wine and Input Supplier Attestation — forms and workflow (§17.1).
- [ ] Complaints, hearings and discipline workflow (OPP §4.5–4.7).
- [ ] Membership fee *collection* (fees are tracked only; no gateway).

## Content

- [ ] Confirm plain-language wording for the membership-is-not-certification disclaimer.
- [ ] Afrikaans: decide whether to translate the full site or navigation and headings only.

## Drift (suggested moves)

_none_
