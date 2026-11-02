<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0k. 2026-10-30 — the baseline got measured, the whole price got published, and the tree got committed

**This session committed four clusters of work that between them had sat uncommitted in the tree
for up to three days, and pushed.** It built two of the four itself (§0k.3, §0k.4); the other two
were finished by earlier sessions that ran out before `git commit`. Nothing about retrieval, the
reader or the public site changed after the tests below were run.

**Why this mattered more than any single file:** `git status` held **four sessions' work at once**
and the eval instrument was **untracked**, so the next agent could not tell whose work was whose —
the exact failure §0j warned about, one session later. The tree is clean as of this handover.

### 0k.1 `ce59e83` — C1f: the whole price, why join, and what we do not claim

The product owner read the rendered home page and said `R100 / year` could not be the price. Right
in substance, wrong about the number: `R100` **is** the annual membership (OPP §2.1), but it is one
of **five** amounts the OPP allows, and the fee section published two and omitted **two**.

- **OPP §2.4** (visit catering, R30/R50) and **§2.5** (seal licence, R500/farm/year) now have
  cards of their own — both conditional, so neither may inherit the standing of a fee the OPP sets
  for everyone.
- **A floor, not a total:** `FIRST_YEAR_FROM_CENTS` is arithmetic on two published figures and the
  paragraph names its three exclusions. A total is impossible without the farm's distance.
- **`SAOSO_LOGO_LICENSED = False`.** The owner believes the group holds the SAOSO "Organic PGS
  Certified" logo licence (a sticker was seen); LANDSCAPE p7 makes that a separate route (18
  months, a PGS SA assessment, a licensing agreement), and a sticker is evidence of the seals
  OPP §V lets our own committee issue. **Open: produce the agreement and the flip is one commit.**
- `core/tests/test_public_costs.py` (new, 21 tests) asserts **completeness and framing, not
  figures** — `test_public.py` already pins those. Two drafts tripped the existing guards (a typed
  fee, a seal label) and were rewritten, which is the guards working.
- **No new UAT scenario, deliberately:** adding an unsigned eleventh would reopen a signed MVP 0
  and break `test_uat_parse.py`. The five things a human should judge are `C1_BUILD_PLAN.md` §C1g.

### 0k.2 `e57ce78` — the test lane, committed

819 pytest invocations across five repos, 49 h of waiting, 8.1 h of it here. Three budgets and one
eval-free inner loop: `--critical` (22 s warm), `fast.sh` (whole suite minus `slow`), `verify.sh`
(the gate, now with `--durations=15`). `pgs/settings_test.py` swaps in a fast hasher for pytest
only, guarded by `tests/tools/test_test_harness.py`. **The `slow` marker is measured, not guessed.**
`testing_hazards.md` §3.17 is the entry that makes the numbers meaningful: same tree, same command,
253 s and 42 s in one afternoon — so quote cold **and** warm.

### 0k.3 `d54219d` — the retrieval instrument and the baseline it changes

S1 of `spike/RETRIEVAL_EVAL_SPIKE.md`. 35 graded questions, 32 answerable, on 385 chunks
(`sha256:dd90ea793953`), at the product's own `k=8`:

| variant | R@1 | R@3 | R@8 | MRR | citation audit |
|---|---|---|---|---|---|
| `bare` — the product | **0.188** | 0.594 | 0.812 | 0.388 | 280/280 |
| `lexical` only | 0.188 | 0.375 | 0.500 | 0.284 | 184/184 |
| `vector` only | **0.531** | 0.688 | 0.875 | 0.647 | 280/280 |

**Read the first row twice.** The product finds the answering clause at rank 1 for **six
questions in thirty-two**, while recall@8 is 0.81 — so a refusal is more often a **ranking**
failure than a coverage gap. That is the number `CHAT_ANSWER_COVERAGE_PRD` has been missing, and it
is the reason not to answer a refusal question by adding more corpus.

The semantic arm is the stronger arm (R@1 0.531 vs 0.188) and the pipeline hides it: `search_terms`
gives the rare-term arm five of the eight seats first. **Recorded, not acted on** — fourteen items
are questions the product *refused*, so the set over-samples the hybrid's failures. Do not re-tune
`search_terms` against this set.

**Q1 is not answered and the doc says so.** `--variant context` refuses loudly until D73's
`embedding_text` column exists. That is S2.

### 0k.4 The deploy that made the box current — and the 40 links it could not keep

`8d2839d` deployed to the VPS the same day and is the **first time that box has ever been
current**: its corpus was the pre-D52 poppler build, 311 SAOSO / 16 BPP chunks, and
`corpus_check` had been reporting drift since D56 landed.

What the deploy did, in its own words: the gate ran **twice** (the script changed in the pull,
so it re-executed — expected, ~2× 72 s), the pre-migration backup verified 172 archive entries
across 21 tables, migrations `core.0006`–`0009` and `knowledge.0003`–`0004` applied, and
`/health/` answered 503 on the **first** poll with `celery_worker: error` before going green on
the second — which is the restart order working, not a fault.

`corpus_refresh --apply` then rebuilt from the artefacts: **bpp 16 → 9** (the box's 16 predated
the column transform and the page-4 band override) and **saoso 311 → 338**, both `embedded=True`,
so the corpus is now **385 chunks** — the first time the box has matched the reviewed text.

**The finding worth carrying forward: the relink path only protects turns recorded after
2026-10-28.** `manage.py relink_evidence` reported **7 turns examined, 7 with no grounding
snapshot, 0 relinkable**. The snapshot lives on a column added by `core.0006`, so every turn that
predates it has nothing to rebuild from and the **40 citation links the refresh dropped (5 bpp,
35 saoso) are gone**. Nothing user-facing broke; the historical evidence trail for those seven
answers did. `deploy/README.md` §4 now says so, because "relink exists" was being read as making a
`--force` free on any install — it does not, on an old one.

**`384`, not `385`, and the difference is a blind spot worth knowing.** `corpus_check` now says
`corpus is current` and all 384 chunks are embedded, but `corpus_refresh --apply` only re-ingested
the two documents that have artefacts. `opp` and `landscape` still hold **37** chunks (dev box:
**38**) built by whatever code ran on 2026-10-22, and `corpus_check` cannot see them: `drift.py`
short-circuits at `if artefact is None → NO_ARTEFACT; continue`, printing the same line whether
those documents hold stale chunks or **none at all**. That is why the number differs and why the
report is silent about it. P4/P5 close it — once both have artefacts, they are compared like the
two that do — so it is filed in `todo.md` rather than fixed now.

**Consequence for the instrument:** the eval baseline's "385 chunks, `sha256:dd90ea793953`" is the
**dev box's** corpus. Do not run `scripts/eval_retrieval.py` on the VPS and compare it to §8a; the
two corpora differ by a chunk in text that has no artefact. S2's comparison has to happen on one
machine.

**Also corrected here:** `DESIGN.md` still said "only one dark band exists (#7)" after the band
rhythm grew to eleven rows — it is #9; `backlog.md` was regenerated (`--write`) rather than
hand-edited; and `deploy/README.md` told the operator `relink_evidence --write`, a flag that does
not exist (`c0ee0ca`). A wrong flag in a runbook fails exactly when the operator is holding a
corpus that has just dropped links.

### 0k.5 what this session did *not* build

Nothing in the corpus pipeline. The next slice is unchanged and still starts where §0j said:
the **table block in the artefact format** with a guard that fails on a malformed annotation,
proved on landscape p4–p5 (`LANDSCAPE_TABLES_PRD.md` §9). Then landscape 10 pages + front matter,
then D73's column, then S2's A/B/C.

---
