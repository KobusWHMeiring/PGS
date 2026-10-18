---
name: pgs-maintaining-the-backlog
description: Use when finishing a feature in the Outeniqua PGS repo, at the end of a coding session (before /new or exit), when asked to "close the loop" or "update the backlog", or when the backlog tree no longer matches what is actually implemented (including uncommitted working-tree changes). The product/backlog/ directories are the source of truth.
---

# Maintaining the Outeniqua PGS Backlog

## Overview

The `product/backlog/` directories are the single source of truth for backlog state.
`product/backlog/backlog.md` is a generated index, never hand-edited. **Git is the only
reliable evidence of what is actually done — never trust a PRD's own `Status:` line.**

This repo follows the Harvester convention. Full semantics live in
`product/backlog/CONVENTION.md`.

This is the **local** skill. Do not use the generic `maintaining-the-backlog` skill —
it assumes a River-style `product/ready/` + `product/refinement/` layout that this repo
does not have.

## When to Use

- A feature just shipped and needs recording as complete.
- Docs drifted from code (a PRD says "ready" but the feature is committed).
- **End of a coding session** — before `/new` or exit — to summarize what changed.
- Asked to "close the loop", "update the backlog", or "confirm what's done".
- Work was done but **not committed** — uncommitted working-tree changes are still work.
- New feature requests need placing in the backlog.

## Directory semantics

| Directory | Meaning |
|-----------|---------|
| `product/backlog/ready/` | Approved, ready to build — authoritative "up next" |
| `product/backlog/In Progress/` | Actively being built |
| `product/backlog/Refinement/` | In design / needs a decision |
| `product/backlog/on_hold/` | Parked / deferred |
| `product/backlog/spike/` | Research tasks (never auto-moved) |
| `product/backlog/BugFixes/` | Bug-fix PRDs (never auto-moved) |
| `product/backlog/Done/` | Shipped |
| `product/backlog/systems/` | System docs, not backlog items |
| `product/design/` | HTML mockups and review artifacts, not backlog items |

## Workflow

1. **Verify against git and the working tree, never the docs.**
   For each item in `ready/` and `Refinement/`, check `git log --oneline` **and**
   `git status --porcelain` (uncommitted work is real work), then grep the code and
   tests for markers. Classify each as done / partial / not-done.
2. **Move files.** Done → `Done/`. Refined and approved → `ready/`. HTML mockups and
   review artifacts → `product/design/`. Use `python product/backlog.py --apply`
   where the move is purely status-driven; move by hand where judgement is involved.
3. **Regenerate.** `python product/backlog.py --write` rebuilds the index.
4. **Update `product/backlog/todo.md`** if an idea was captured that has no PRD yet.
5. **Update the spec if a decision changed.** The aimed spec is
   `product/backlog/Refinement/PGS_PLATFORM_SPEC.md`; a decision that moves the design
   belongs in its §18 Decision Log, not only in chat.
6. **Report.** What moved, what is still pending, and any orphaned or uncommitted work.

## Verification technique

For each candidate item, gather concrete evidence:

- `git log --oneline -20` — is there a commit for it?
- `git status --porcelain` — is there uncommitted work?
- `grep -rn "<marker>" core/ knowledge/ tests/` — does the code, template or test exist?

**Never classify an item done on the PRD's own word.** Code + tests are the evidence.

For anything user-facing, a UAT sign-off is also required: check
`tests/uat/<feature>_uat.md` for a completed sign-off table. "Tests pass" is not
completion for a feature a human must judge.

## pgs-specific rules

- **Nothing is done without a UAT sign-off** where a human must judge the result
  (`build_principles.md` §VIII). An unsigned UAT means the item is *partial*.
- **Domain language comes from the OPP and SAOSO.** If a PRD invented a term the OPP
  already names, fix the PRD.
- **A retarget must not require a migration** (§4.8 / D12). If a change added a
  migration to add a seal, a category or a document, that is a regression against the
  spec, not just a design choice.
- **The MVP 0 plan is sub-plan structured.** `MVP0_PLAN.md` holds sub-plans A–D;
  "MVP 0 done" means all four plus the completion-criteria checklist.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Trusting a PRD's `Status:` line | Verify in git and the working tree first |
| Using the generic `maintaining-the-backlog` skill | Use this one; the layouts differ |
| Hand-editing `backlog.md` | Regenerate with `--write` |
| Leaving HTML artifacts in `Refinement/` | Move to `product/design/` |
| Marking a user-facing feature done with no UAT sign-off | Mark it partial |
| Recording a decision only in chat | Add it to `PGS_PLATFORM_SPEC.md` §18 |

## Red Flags

- "The PRD says it's done" — verify against git/code.
- "I'll update the backlog later" — do it now, in the same session.
- "I didn't commit, so there's nothing to record" — uncommitted changes are work too.
- "Tests pass, so it's done" — not for anything a human must judge.
