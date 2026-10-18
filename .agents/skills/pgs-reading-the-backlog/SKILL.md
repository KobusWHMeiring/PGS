---
name: pgs-reading-the-backlog
description: Use when asked what is in the Outeniqua PGS product backlog, what is up next, or what is ready to build, and before planning new work — to check what is already queued and whether the backlog matches the code.
---

# Reading the Outeniqua PGS Backlog

## Overview

Report the current state of the backlog and what is "up next", treating the
`product/backlog/` directories as source of truth and **verifying against git and the
working tree — never trusting the generated index alone**.

Full directory and status semantics live in `product/backlog/CONVENTION.md`.

This is the **local** skill. Do not use the generic `reading-the-backlog` skill — it
assumes a River-style layout (`product/ready/`, `product/refinement/`, root-level
`backlog.py` + `summarise.py`) that this repo does not have.

## When to Use

- "What's up next?" / "What's in the backlog?" / "What should I work on?"
- Starting a session and needing orientation on queued work.
- Checking whether the backlog matches reality before planning.

## Process

1. **Regenerate the index** so it is fresh: `python product/backlog.py --write`.
2. **Verify, don't just read.** For each item in `ready/` (the authoritative "up next"),
   confirm it is *not yet built*:
   - `git log --oneline -20` — is there a commit?
   - `git status --porcelain` — is work in progress uncommitted?
   - `grep -rn "<marker>" core/ knowledge/ tests/` — does the code or test already exist?
   - A `ready/` PRD whose code is already committed is **stale** — flag it.
3. **Report in this order:**
   - **Up next** — `ready/` items, one line each.
   - **In refinement** — `Refinement/` items, and what decision each is blocked on.
   - **In progress** — `In Progress/` items.
   - **Recently shipped** — `Done/`, last few only, not the archive.
   - **Drift** — directory vs `Status:` disagreements from `python product/backlog.py`,
     plus any `ready/` item already implemented.
4. **Offer the fix.** If anything is stale, offer to run `pgs-maintaining-the-backlog`.

## Quick Reference

| Question | Answer source |
|----------|---------------|
| What should I build next? | `product/backlog/ready/` (verified against git/code) |
| What is blocked or undecided? | `product/backlog/Refinement/` |
| What is the delivery order? | `PGS_PLATFORM_SPEC.md` §19 |
| What just shipped? | `product/backlog/Done/` + recent `git log` |
| Is the index trustworthy? | Only after `--write` *and* code verification |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Trusting `backlog.md` without regenerating | Run `python product/backlog.py --write` first |
| Reporting `ready/` as "up next" without checking code | Verify each against git/grep |
| Reading a PRD's `Status:` as fact | The directory is the truth; verify in git/code |
| Using the generic reading skill | Use this one; the layouts differ |

## Red Flags

- "The index says it's ready" — verify before recommending it.
- A `ready/` PRD whose code is already committed — stale, not up next.
- A user-facing item in `Done/` with no UAT sign-off — it is not actually done.
