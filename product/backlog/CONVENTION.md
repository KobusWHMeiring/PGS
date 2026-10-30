# Outeniqua PGS Backlog Convention

The `product/backlog/` tree is the single source of truth for backlog state.
`product/backlog/backlog.md` is a **generated index** — never hand-edit it.

Adopted from the Urban Harvest (Harvester) convention, which this repo follows for
build principles as well. See `product/docs/context/build_principles.md` §0.

## Bucket directories (source of truth)

| Directory | Meaning |
|-----------|---------|
| `product/backlog/ready/` | Approved, ready to build — authoritative "up next" |
| `product/backlog/In Progress/` | Actively being built |
| `product/backlog/Refinement/` | In design / needs a decision |
| `product/backlog/on_hold/` | Parked / deferred |
| `product/backlog/spike/` | Research / investigation tasks — kept separate (never auto-moved) |
| `product/backlog/BugFixes/` | Bug-fix PRDs — kept in place for now (not auto-moved) |
| `product/backlog/Done/` | Shipped |
| `product/backlog/systems/` | System-level docs (not backlog items) |
| `product/design/` | HTML mockups and review artifacts (not backlog items) |

## Status → bucket mapping

A PRD's `Status:` field is **advisory**; the directory it lives in is the truth.
`product/backlog.py` flags any PRD whose status implies a different bucket than
its directory.

| `Status:` contains (case-insensitive) | Implies bucket |
|---|---|
| `ready`, `design approved`, `design validated` | `ready/` |
| `refinement`, `draft`, `master prd`, `awaiting` | `Refinement/` |
| `in progress` | `In Progress/` |
| `on hold` | `on_hold/` |
| `investigation`, `spike` | `spike/` |
| `done`, `complete`, `implemented`, `shipped`, `resolved`, `superseded` | `Done/` |

Matching order matters (e.g. "Draft - Ready for Review" → refinement;
"Investigation Complete" → spike). The executable source of truth is
`STATUS_RULES` in `product/backlog.py`.

**The match is a `\b` word-boundary search anywhere in the `Status:` line, so a status word
buried inside a hyphenated compound still fires.** Written on 2026-10-22: a plan whose status line
said *"four of the seven definition-of-done criteria are proved"* was classified **Done** by
`\bdone\b`, because `-` is a word boundary. Write **DoD**, not *definition-of-done*, in a `Status:`
line. The same applies to "shipped date", "not yet complete", and any incidental use of the
terminal words while describing what is *left* to do.

`Done/`, `on_hold/`, `systems/`, `spike/` and `BugFixes/` are **terminal**: their
files are never auto-moved. The directory is the human decision; a `Status:` line
that disagrees is only flagged as stale.

When a file is moved, intermediate subfolders named `done` are flattened — e.g.
`Refinement/health_audit/done/foo.md` → `ready/foo.md`.

## Files

- `product/backlog/backlog.md` — generated index (do not edit).
- `product/backlog/todo.md` — "To Do" ideas that have no PRD file yet; feeds the index's To Do section.
- `product/backlog/PRD_TEMPLATE.md` — the pre-flight checklist every PRD must carry, and the
  three fields that can publish one (`Public title:`, `Summary:`, `Public:`).
- `product/backlog.py` — scans the tree, flags drift, regenerates the index, and (with `--apply`) moves files.

## Workflow

1. `python product/backlog.py` — dry-run: report drift + suggested moves (no writes).
2. `python product/backlog.py --write` — regenerate `backlog.md` only.
3. `python product/backlog.py --apply` — move files to match status + regenerate index.
4. `python scripts/board.py` — **regenerate the public board** before a push that will be
   deployed. `--check` verifies the committed artefact; `deploy/deploy.sh` runs it, so a stale
   board aborts a deploy rather than shipping.

## Publishing a PRD to `/building/`

The board is **curated, never mirrored**: a card exists only where a person opted the PRD in.
Add two lines to the PRD header (three if its own title is internal vocabulary):

```
**Public title:** Applying for assessment, online      ← optional, when the h1 is jargon
**Summary:** One sentence, 180 characters or fewer, written for a farmer.
**Public:** yes
```

Delete `**Public:** yes` to withdraw a card; nothing else removes one. `scripts/board.py`
refuses to build while a `Public: yes` PRD has no summary, an over-long summary, a term from
`core/services/_public.py` `FORBIDDEN_CLAIMS`, or a directory with no column (`spike/`,
`BugFixes/`, `on_hold/`, `systems/`). A refusal is a mistake to fix, never a card to hide.

Why the board reads an artefact and not this directory: `PUBLIC_BOARD_PRD.md` (D74). Short
version — 10 of 36 PRDs contain a term the public surface may not carry, and the sentences
around them are notes about the live WordPress site's own overclaims. The backlog is not
publishable text.

## pgs-specific notes

- **The OPP and SAOSO are the domain vocabulary.** A PRD that invents a term for
  something the OPP already names (e.g. "value chain actor", not "retailer") should
  be corrected, not accommodated.
- **A PRD must state which MVP it belongs to.** The delivery sequence lives in
  `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` §19.
- **Nothing may be marked done without a UAT sign-off** where the change has a
  user-facing surface. UAT checklists live in `tests/uat/` and contain only items a
  human must judge (see `product/docs/context/build_principles.md` §VIII).
- **The code atlas** (`product/docs/state/atlas.md` + `atlas.html`, generated by
  `scripts/atlas.py`) is the answer to "what is built" — schema, services, views, routes,
  async/schedulers, the corpus pipeline. It is **not yet built**: it is specified in
  `Refinement/CODE_ATLAS_PRD.md` (a product-owner requirement, 2026-10-28), which supersedes
  the earlier note that a state doc was "premature until there is code". When it lands it is
  generated and gated — never hand-written, never in `product/design/`, and not a backlog item.
