# Session `1t` — the merge: three conflicts, two strands, and one tree

**Date:** 2026-11-06 · **From:** the merge session · **For:** whoever reads the tree next

## 1. What this session was

`feat/mvp1a-visit` (`22b2aab`, 36 commits, MVP 1a sub-plans A and B) had been sitting in a second
worktree since session `1i`, and `main` had moved 35 commits the other way (D80/D82 and S5-a/b/c).
The previous session measured the merge from `bacaeeb` in a throwaway worktree and left two
preconditions: **the target tree must be clean**, and `verify.sh` would still fail step 1 on another
session's `scripts/copy_deck.py`. This session did the merge, and the measurement held exactly.

## 2. Push first, merge second

The strand had **no upstream** — `22b2aab` was local-only, in a worktree a second agent shares the
repo with. Pushing was the first act, not the last:

    $ git push -u origin feat/mvp1a-visit
     * [new branch]      feat/mvp1a-visit -> feat/mvp1a-visit

A merge that goes wrong is now a `git reset`. The order matters: insurance before surgery.

## 3. The precondition, and the work that was not mine

The main worktree carried another session's uncommitted copy-deck work — four modified files,
including `core/services/_public.py`, **which the visit branch also changes** (21 insertions, 2
deletions in the home `Page`). That is the one overlap that makes git refuse the merge rather than
merge it, and it is not this session's work to commit. The previous handover sanctioned either
"commits (or stashes)". Stash was the honest one — committing another session's half-finished copy
under the merge's name would misattribute it.

Three copies existed before anything moved:

1. `git diff --binary > tracked.patch` (all four modified files, binary-safe);
2. the six untracked files, copied verbatim;
3. the base commit, written down.

...all in `../pgs-dirty-backup-2026-11-06/`, outside the repo, so nothing in the merge path could
touch them. Then `git stash push -u` — and the tree was clean for the first time in two sessions.
The stash was restored after the merge committed and is no longer listed in `git stash list`.

**The backup earned its keep, and not for the reason expected.** `git stash pop` returned the six
untracked files **normalized to LF** — `scripts/copy_deck.py` came back 32,312 bytes where it left
33,106, with 794 CRLF gone and the text identical. The instinct on a size mismatch is "the merge ate
their edits"; the real cause is the stash round-trip through the index. The six were copied back from
the backup verbatim (`cmp -s` clean), the four tracked files were already byte-identical (the only
patch difference was the merge's new base blob in the `index` line), and the public and
claim-discipline guards are green on the result: **153 passed in 7.92 s**. Recorded as **§3.47**.

## 4. The three conflicts, and why each rule is a rule

The measured surface was three files; the merge produced exactly those three and no fourth.

- **`HANDOVER.md`** — both strands had rewritten the START HERE block, by design: both are state
  files. There is no correct side. The resolution is a new block that carries both positions — the
  corpus strand's (S5-c landed, Appendix 7's rows 7–25 next) and the application strand's (A 8/8,
  B 4/4, C1 designed and held) — with the session index as the union of both.
- **`product/docs/context/testing_hazards.md`** — **the numbering collided in section 3**, because
  both strands appended entries at the end of the same file: `main` had grown §3.31–§3.44, and the
  strand had its own §3.31 (`verify.sh` in a second worktree) and §3.32 (a scripted slice move).
  The strand had written the rule down in advance — *main's numbers win* — so its two moved to
  **§3.45/§3.46** with a "was §3.31/§3.32" line each, and its seven §1.35–§1.41 entries kept their
  numbers because `main` stops at §1.34. Counted afterwards: **98 entries = 89 + 9**, none lost,
  none duplicated. The renumbering was done by a probe (`_scratch/merge_hazards.py`), not by hand,
  because the block is ~260 lines and a hand merge of it is a bet.
- **`product/backlog/backlog.md`** — **generated**, and the conflict was its `Generated:` timestamp
  and nothing else. `python product/backlog.py --write`; then `python product/backlog.py` reports
  **0 drift** and 46 To Do items preserved. `todo.md` auto-merged and still holds both strands'
  items (`MISSING_FEE_SURFACE`, `C1_HELD_FOR_GROUP`).

**No migration collision, as measured:** `main` stopped at `0009`, the strand adds `0010`–`0018`.
The graph stays linear.

## 5. Measured after the merge

- `python -m pytest -q --reuse-db` — **2090 passed / 1 skipped / 8 xfailed in 76.57 s** (warm,
  5433). The two sides measured 1790 and 1971 before the merge; a warm run is what the tree got,
  and §3.17 says quote it as warm.
- `scripts/fast.sh --critical` — **187 passed / 4 deselected in 11.34 s**. `main` alone was 182, so
  the strand brought five critical-lane tests with it: the count moving is the merge working.
- `scripts/verify.sh` — step 1 red on `scripts/copy_deck.py` (**32 KB** over a 30 KB cap, and it was
  restored from the stash after the merge, so the breach is the other session's, unchanged by this
  one); steps 2–4 green: `manage.py check` clean, `makemigrations --check` no changes, `lint-imports`
  `knowledge must never import core KEPT`.

**The tree still shows nothing end to end.** `showmigrations core` reports the last **applied**
migration as **`0009`**, so `0010`–`0018` are unapplied and every A and B table is absent. Three data
acts, not code: `migrate`, `seed_deployment`, `load_template core/templates_data/crops.v1.json
--activate`.

## 6. What the next session inherits

The merge closes the split; `../pgs-visit` is merged and removable. Two queues are open and they do
not share files: **the demo to PGS/SAOSO and then C1** (held for the group on two OPP questions), and
**Appendix 7's rows 7–25 then S5-d/e/f** on the corpus side. **The deploy is owed** for sessions
`1f`–`1s` and this merge; it moves the live corpus 401 → 408.

Do not commit the copy-deck session's files under anything but its own name. Do not merge the
backlog index by hand. Do not renumber an archived session doc.

## 7. The data acts, so the flow could be judged in a browser

The owner asked for a full frontend clickthrough, which the merge alone could not give: the merge
commit still had `0009` as the last applied migration. Dumped the dev DB first
(`../pgs-db-backup-2026-11-06.dump`, 1.7 MB, `-Fc`; rollback is `pg_restore -c`), then ran the three
acts from the previous handover's list, and they were exactly three:

    $ python manage.py migrate
      Applying core.0010_mvp1a_a1_farms_and_members ... core.0018_mvp1a_a4_prior_certification  OK
    $ python manage.py seed_deployment
      standard_sets: 0 created, 1 updated   seals: 0 created, 3 updated
      categories: 0 created, 7 updated      turnover_bands: 6 created, 0 updated
      committee_terms: 15 created, 0 updated  consent_texts: 3 created, 0 updated
    $ python manage.py load_template core/templates_data/crops.v1.json --activate
      created CROPS:v1 / activated CROPS:v1

`showmigrations` then reports **0 pending**. The seed is idempotent and leaves `is_active` alone on
existing rows, which is why the two live seals stayed live and the third stayed retired.

**What the clickthrough can and cannot show, measured rather than assumed.** All 8 public documents
reach `/documents/<code>/read/` with 200 (`saoso-standard-v2.1` is the one to judge for S5's tables).
The application flow is `/before-you-apply/` → `/apply/` → `/apply/pledge/` → `/apply/categories/` →
`/apply/turnover/` → `/apply/summary/`, gated server-side by `_step`, and the pledge's default
`SIGNATURE` path needs **no upload** — witness name, designation and a photo are only required for a
*verbal* or *mark* pledge, which is the trap that would have stalled a clickthrough.

**There is no gate screen, and that is not a defect.** `grep` over `core/views/` finds no reader of
`is_paid_up` or eligibility: A5's unpaid refusal and A7's standing refusal are service rules with
tests behind them, and the flow ends at the summary. Say that to the owner before they look for it,
because the screen they expect is the one `MISSING_FEE_SURFACE` is about.

**Two environment facts that would otherwise read as breakage.** `/health/` answers **503** because
`celery_worker` is `error` while `db`, `redis` and `celery_broker` are `ok` — no worker is running,
and no request path enqueues work (`core.tasks.heartbeat` is the only task), so a clickthrough is
unaffected. And `corpus_check` reports `bpp` current but `landscape`/`opp` drift, `saoso` at
**338/348** chunks: the dev corpus is one build behind, so the reader and `/ask/` serve pre-S5-c text
until a refresh. **The refresh was deliberately not run** — `GEMINI_API_KEY` is in the shell but not
in the repo `.env`, and the documented failure is 17 NULL vectors that report "already ingested"
forever (`deploy/README.md` §4).

**Left running, deliberately, and named here so the next session can kill or reuse it:**
`python manage.py runserver 8000 --noreload`, log at `_scratch/runserver.log`. It holds the merged
Python in memory, so a `.py` edit needs a restart before it can be judged (§3.23).
