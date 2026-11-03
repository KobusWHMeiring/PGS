# Session `1d` — the state said what was not true, the rows were cut, and the check became the gate

**2026-11-03 · session 16 · from `669c56e` to `f4ae42c` (+19 ahead of `origin/main`)**

The handover sent this session to "steps 11 and 12" of `CONTEXT_CUTS_PRD`. Both landed. The
session's actual finding is that the *premise* of step 11 was false — the rows did not carry
links — and that the file's own state block was three sessions out of date.

## 0. The state block was stale below its own START HERE block

Asked to read `HANDOVER.md` and talk through next steps, the first hour was spent verifying
rather than repeating. Three lines disagreed with the file's own top block:

| the file said | git and the box said |
|---|---|
| `Live: 8d2839d`, 2026-10-30, "15 sessions and 70 commits behind, with the old PDF corpus" | `06bb11a`, deployed 2026-11-03, corpus current at 401 chunks (the START HERE block, correctly) |
| "**59 commits unpushed**" | 9 (and "8 commits ahead of `origin/main`" in the block above — actually 9) |
| "**The dev box is current**" | `corpus_check` reports `landscape` **drift**; its 17 landscape chunks carry 0 labelled renditions against live's 8 |

Neither claim could be tested in CI: the ahead-count moves after the handover is written, so a
test would be red for a reason that is not a defect. The fix is a reading obligation, recorded in
`1793a1e` — and the START HERE block now states what is true and says which lines it corrected.

**While in there:** the §3.27 deploy window was recorded as debt ("the box still runs the old
`deploy.sh`"). It is not. `06bb11a`'s script still `pull`s origin's tip, but it already carries
the re-exec, so the next deploy re-runs the fixed script, which verifies origin's tip afresh and
fast-forwards to *that* before the backup and the first migration (`deploy/README.md`). Checked
by reading `git show 06bb11a:deploy/deploy.sh`, not by trusting either handover line.

## 1. Step 11 — the 14 rows, and the two defects under them

`--check` went **14 → 0 breaches** in five commits (`85d0f0b`, `b11ac90`, `50d9b92`, `43792d4`,
`f7daa60`), 3/3/3/3/2, each row kept at decision + owner + date + one measurement + a link.

The method that mattered: **confirm the argument is present at the link before cutting the row.**
`_scratch/rows/probe.py` (written once, re-run nine times) resolved every link and checked every
numeric measurement against the linked file's text. That is how three rows were caught about to
lose content that existed nowhere else:

- **D70** — seven sub-ids, cited by id in `_document_reader.py`, `reader-tables.css`,
  `document_reader.html`, `knowledge/{tables,passages,glossary}.py` and five tests. All seven
  kept; only their arguments moved.
- **D71** — "the register changed on fifteen of the twenty" exists only in the row. The
  exploration page has the per-control judgement; the PRD has "twenty of twenty decided"; the
  15/20 count is the row's. It stayed, which is exactly what §4.2 says a row is for.
- **D47** — "no stitching". Its only other home is the prompt text (`_chat_prompt.py:95`) and
  `test_chatbot_prompt.py`, so the clause stayed and the link now names the contract.

**Defect 1 — a row's link was not a link.** 12 of the 14 pointed at paths that do not exist from
the spec's own directory (bare basenames for PRDs in `In Progress/`; `Refinement/` for one that
had moved to `Done/`), and **D47 had no link at all**. Cutting to "a sentence and a link" would
have made the spec smaller and worse. 11 further rows carried the same defect, so all 81 rows are
repo-root-relative now and `tests/tools/test_context.py` fails on any unresolvable token —
watched red (one row reverted → 1 failed, naming D78 → restored → 11 passed). Recorded as
`testing_hazards.md` §3.29: a budget check that measures bytes and is trusted for "the evidence is
reachable" is the `lint-imports`-exits-0 shape again.

**Defect 2 — D53 was stale in the direction that matters.** The row said the OPP, SAOSO and
landscape were "not yet converted" to reviewed artefacts. True on 2026-10-22; false since
2026-11-02, when all four became the text of record. A row that keeps its arguments is also a row
whose arguments rot — the cut is what found it.

## 2. Step 12 — the check is the gate's first step

`scripts/verify.sh` now runs `scripts/context.py --check` as **step 1/4**, before the Django
checks, guarded with `if !` rather than leaning on `set -e` — the failure has to name the budget
and where the argument belongs, or the next person deletes the step.

Two things had to be true first, and the second was not obviously one of them:

1. **Zero breaches.** §4.4's condition, and `testing_hazards.md` §3.11's reason: a gate wired red
   trains people to skip it.
2. **A missing file must not read as a small one.** `size_of()` returns `(0, 0)` for a path that
   is not there, so a deleted `HANDOVER.md` or spec was "comfortably inside its budget" and the
   gate would have gone green on an artefact's absence. `check()` now reports absence as a breach,
   which also covers the `git archive` tree `deploy.sh` gates.

`tests/tools/test_verify_gate.py` (already the file that proves the gate needs no PDF reader) now
holds both halves: the wiring asserted as text *and* that it is guarded, and `check()` run against
a scratch tree deliberately over budget (exit 1, file named) and against a clean one (exit 0), so
a check that always fails cannot pass for the right reason.

**Watched red three ways:** the guard replaced with `if false` (1 failed), the missing-file loop
emptied (1 failed), and one row's link reverted (1 failed, naming D78). Restored, green.

## 3. Where the numbers stand

- `scripts/verify.sh`: **1610 passed / 1 skipped**, **183.57 s cold** and **59.97 s warm** on this
  box (the two runs differ by the DB and caches; quote the range, §3.17). Step 1/4 prints
  `every budget holds` — the check proves itself on every run.
- `scripts/fast.sh --critical`: **172 passed / 4 deselected in 46.53 s**, and `scripts/fast.sh` is
  not in the diff at all — the lane still names the same eight files.
- `--check`: **0 breaches**; the largest decision row is 1499 bytes (was 3689).
- No model, migration, prompt or corpus file is in the diff — `git diff --name-only 669c56e..HEAD`
  is eight files, all docs, scripts and tests.

## 4. What is next

1. **G12/X2 — starting with the eight-shape fixture set.** D80's row now says so in one sentence,
   and `todo.md` says the PRD comes before the build. The eight are named in Part 1 of the
   exploration; the spec's measured starting point is 44 reviewed rows, four bespoke test files and
   two tables still mangled — **shape-by-shape test coverage is the first thing the fixture set
   establishes, and this session did not measure it.** (An earlier draft of this record and of
   `HANDOVER.md` claimed "four of the eight have no test today"; that was an inference from the four
   bespoke files, not a reading, and it was corrected in `c1f…` before either was acted on.)
2. **`product/design/f3_saoso_outreach_and_role.html` is untracked** (24 KB, "F3 — SAOSO outreach
   and the digital systems role", dated today, referenced by no PRD). Commit it with a backlog line
   or delete it; it should not sit unversioned.

## 5. Method note, for the next session's budget

The 14 rows cost ~14 `_scratch/rows/*.md` drafts, one probe, and one apply script that refuses a
draft over budget and requires the id to appear exactly once. Each served nine times. The
alternative — retyping a 3 KB row into an `edit` call, and re-sending it on every later request —
is what the context discipline in `AGENTS.md` is about.
