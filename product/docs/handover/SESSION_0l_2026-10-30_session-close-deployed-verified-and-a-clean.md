<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0l. 2026-10-30 — session close: deployed, verified, and a clean slate for the table block

**State: green, pushed, deployed, and the next slice named in the block at the top of this file.**
Nothing below is a proposal; each line is something that was run.

### 0l.1 What shipped

| | |
|---|---|
| `ce59e83` | **C1f** — the whole price (OPP §2.4/§2.5), why join, where it is recognised, `SAOSO_LOGO_LICENSED = False` |
| `acf79aa` | the test lane — three budgets, fast hasher, measured `slow` marker |
| `5ac2944` | the retrieval instrument + the baseline (R@1 **0.188** bare, **0.531** vector) |
| `8d2839d` | D72/D73 — table rows are reviewed data, the vector is not the cells |
| `c0ee0ca`, `c4eaadd`, `3696f81` | `relink_evidence --apply` (not `--write`); relink only saves turns after 2026-10-28; 384≠385 and why |

**The deploy found one thing the gate could not:** `scripts/fast.sh` was `100644` in the index, and
`verify.sh` refused to run — *"these scripts are not executable in the commit"*. Fail-safe, and
still a wasted cycle had it reached the box. Fixed in the commit that added the file (history was
rewritten before the push, so published history never carried the broken mode). **Windows cannot
see a file mode; `git update-index --chmod=+x` is the only fix, and the gate is the only thing that
will tell you** (`testing_hazards.md` §2.8).

### 0l.2 What the box proved

`corpus_check` → **`corpus is current`** for the first time since D56 landed; **384 chunks, 0
unembedded**; `check --deploy` clean; `/health/` ok. The refresh rebuilt `bpp 16 → 9` (the box's 16
predated the column transform) and `saoso 311 → 338` from the reviewed artefacts.

### 0l.3 What is left, and is not this slice

- **P7.4 cannot pass as written.** The artefact ingest still reads the PDF for the printed `toc`, so
  "remove poppler-utils and refresh still works" is false. Two fixes recorded, neither built
  (§0i). Fix it before trying to close P7.4, or the session will rediscover it.
- **The 0∥ offline spike is still "not started"**, and D26 makes it a precondition for freezing
  `visitPack`/`VisitSyncEnvelope`. It gates MVP 1a **sub-plan G** only; A–F can start.
- **MVP 1a** is `ready/` and unbuilt (9 migrations, none of them a `Member`, `Farm` or `Visit`). Its
  PRD predates D64/D71 — re-read it against §18.3 before writing the first model.
- **Human gates**: the three empty UAT seats (D4), the restore rehearsal on the VPS (A9), and the
  committee's no-claims confirmation (D60). None is a commit.

### 0l.4 ⚠ The tree carried another session's work when this handover was written

`core/services/_board.py`, `_board_data.py`, `core/templates/public/building.html`,
`core/tests/test_board.py`, `tests/tools/test_board.py`, `scripts/board.py`,
`Refinement/PUBLIC_BOARD_{PRD,PLAN}.md`, plus edits to `product/backlog.py` (+155 lines),
`CONVENTION.md` (the `/building/` publishing rules), `deploy/deploy.sh` (+14 — **the next deploy
will run `scripts/board.py` and a stale board will abort it**), `_public.py`, `urls.py`,
`_footer.html`, and `Public title:`/`Summary:`/`Public:` headers added to nine PRDs.

**It is uncommitted, it is not this session's, and it is green** — `fast.sh` reports **1331 passed
/ 1 skipped** with it in the tree (1291 without), so it looks finished rather than half-written.
It was **not staged**: this session staged its own paths by hand, and discarded its own
regeneration of `backlog.md` because the index had begun listing two PRDs that are not committed.

**So: if `git status` is not clean when you arrive, that is why.** Get it committed (or stashed) and
attributed before you start the table block, and re-run `backlog.py --write` afterwards — an index
that names untracked files is worse than a stale one.

---
