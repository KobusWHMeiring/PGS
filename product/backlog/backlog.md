# Outeniqua PGS Product Backlog

> **Generated index** - do not edit by hand. Regenerate with `python product/backlog.py --write`.
> Generated: 2026-10-19 09:44

## Ready (up next)

- **MVP 0 Implementation Plan (v2) — Standards Foundation & Public Shop Window** - `ready\MVP0_PLAN_V2.md` - Status: Ready — the §9 group-A gate closed as D27 (verdict polarity is template data) and D14–D15 (citation depth, `sub_ref`, `anchor`). Sub-plan A is in build.
- **PRD: MVP 0 — Standards Foundation & Public Shop Window** - `ready\MVP0_PRD.md` - Status: Ready — §9 group A closed as D27 and D14–D15. Groups B and C stay open: they are MVP 1 and MVP 2 scope decisions, not MVP 0 blockers.
- **MVP 1a Implementation Plan — In-Office Visit Flow** - `ready\MVP1A_PLAN.md` - Status: Ready
- **PRD: MVP 1a — In-Office Visit Flow** - `ready\MVP1A_PRD.md` - Status: Ready — all blocking decisions closed (spec §18.3 D27–D39). **Prerequisite:** MVP 0 sub-plan A is not yet built — see `MVP1A_PLAN.md` §0.2.

## In Progress

_none_

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
