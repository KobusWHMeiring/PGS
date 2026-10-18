# AGENTS.md — Outeniqua PGS Digital Platform

## What this repo is

A greenfield Django 5.2 monolith digitising the Outeniqua PGS organic certification
process, plus the public PGS Outeniqua website and a strictly grounded chatbot over
the SAOSO standard.

## Read these first

| Purpose | File |
|---------|------|
| **Handover — start here** | `HANDOVER.md` |
| **The product spec (target state)** | `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` |
| Build rules — non-negotiable | `product/docs/context/build_principles.md` |
| MVP 0 PRD | `product/backlog/Refinement/MVP0_PRD.md` |
| MVP 0 implementation plan | `product/backlog/Refinement/MVP0_PLAN_V2.md` |
| MVP 0 UAT checklist | `tests/uat/mvp0_standards_and_public_site_uat.md` |
| Source documents (authoritative) | `pgs_docs/*.pdf`, `pgs_docs/*.xlsx` |

`pgs_docs/` holds the governing documents: the Outeniqua PGS Principles, Policies and
Procedures (the OPP — cited throughout the spec), SAOSO Standard v2.1 2026, the
assessment workbook, the checklists, and the certification landscape. **These are the
source of truth for domain language.** Cite them rather than inventing terminology.

## Architecture at a glance

- **`core/`** — the application: accounts, member, farm, visit, assessment,
  certificate, aggregation, chat, public site.
- **`knowledge/`** — the standards corpus and retrieval engine. A library: no users,
  no views, no sessions.
- **The dependency is one-directional.** `core` may import `knowledge`;
  `knowledge` must **never** import `core`. Enforced by `lint-imports` in CI.
- **Zero build pipeline.** No npm, no bundler, no Tailwind build step. All JS is
  vendored in `core/static/`.
- **Code encodes the PGS process; data encodes the standard and the group.**
  Seals, categories, document corpora and questionnaires are data. A retarget to
  another standard or PGS group **must not require a migration**.

## Backlog

This repo uses the **Harvester backlog convention** (see `product/backlog/CONVENTION.md`).

- For reading or maintaining the backlog, use the **local** skills
  `pgs-reading-the-backlog` and `pgs-maintaining-the-backlog` under `.agents/skills/`.
  Do **not** use the generic `reading-the-backlog` / `maintaining-the-backlog` skills —
  those assume a different (River-style) layout.
- `product/backlog/backlog.md` is a **generated index** — never hand-edit it.
- Commands:
  - `python product/backlog.py` — dry-run: report drift + suggested moves
  - `python product/backlog.py --write` — regenerate the index only
  - `python product/backlog.py --apply` — move files to match `Status:` + regenerate
- The directory a PRD lives in is the **source of truth**; its `Status:` line is advisory.
- HTML mockups and review artifacts live in `product/design/`, not in the backlog.

## Conventions that bite people

- **No unsupported certification claims.** The public surface may reproduce only the
  four FORM outcomes and the *active* seals. Never publish "pasture raised", "GMO free",
  "biodynamic" or similar. `core/tests/test_claim_discipline.py` will fail the build.
- **Membership is not certification.** Any member list must say so. The OPP requires it.
- **Never trust a PRD's own status.** Verify against git and the working tree.
- **Offline-first applies to the assessor PWA only** — not the portal or the chatbot.
