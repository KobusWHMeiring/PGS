# Session `1b` (2026-11-03) — deployed, and the deploy verified one commit and installed another

**Task:** deploy the site, then close the loop.

**Outcome:** `organicguarantee.africa` is live at `06bb11a` with a current corpus, and the deploy
path now installs the commit its gate actually verified.

---

## 1. What was blocking the deploy, and what was not

`main` was **67 commits ahead of `origin/main`**, and the box pulls from origin, so nothing could
be deployed until the push landed. The push was clean (`35051e1..7b22423`).

Pre-flight, all measured rather than assumed:

| Check | Result |
|---|---|
| Shell scripts executable **in the index** (skill trap: `git archive` writes the index mode) | `100755` on all six |
| New migrations in the 67 commits | one: `knowledge.0005_documentchunk_embedding_text` |
| `makemigrations --check --dry-run` | "No changes detected" |
| The migration's shape | an additive `AddField(default="")` — no rewrite, no lock window |
| `PROMPT_VERSION` | `d79-2`, untouched; cache is keyed on it, so no stale answer can be served under the new contract |
| Corpus artefacts present | all four (`saoso.md`, `bpp.md`, `opp.md`, `landscape.md`) |

That last row mattered: `deploy/README.md` §4 says "opp and landscape have no artefact yet and
parse their PDFs", which is **stale since session `0z`**. Because all four now have artefacts, the
repair reads reviewed text and **`pdftotext` is not needed** — one risk removed before it was run
into.

## 2. The deploy itself

`sudo ./deploy.sh` on the box. Gate **green at 1598 passed / 1 skipped in 82.03 s**, running
`check` + `makemigrations --check` + `lint-imports` (1 contract kept) + `pytest --create-db` against
`pgs_verify`. Backup taken and verified: 188 archive entries, 22 tables, 12 file checksums, 10M.
`knowledge.0005` applied. `check --deploy` clean with 1 silenced (HSTS preload, by id).
`/health/` needed two of six retries on `celery_worker: error` — the expected worker-registration
lag, absorbed by the retry loop, so that design decision earned its keep.

The box was at `c0ee0ca`, not the `8d2839d` in the previous handover; the "live" line had gone
stale between sessions without anyone deploying.

## 3. The defect: verified `7b22423`, installed `06bb11a`, logged `7b22423`

The `big push` commit (`06bb11a`, the `f2_funding_landscape.html` artefact) landed on origin
**during** the 82-second gate. Three lines in the deploy log, read together, name the bug:

```
==> 1/8  Verifying origin/main     ->  7b2242343192b6fcbebfe48cd9a6a82d91b64492
==> 2/8  Pulling origin/main       ->  7b22423..06bb11a  main -> origin/main
✅ Deploy complete — 7b2242343192b6... is live
```

- L118 captures `VERIFY_COMMIT` from `rev-parse FETCH_HEAD`;
- L191 ran `git pull --ff-only origin main`, which **fetches again**;
- L295 printed the captured variable.

So the gate's contract — the comment at L100–103 literally says *"what is tested is exactly what
the pull below installs"* — was broken by the step two lines below it. The delta was one HTML file,
which is precisely why it would have gone unnoticed when the delta is a migration.

**Fix (structural, not a warning):** fast-forward to `$VERIFY_COMMIT`, which step 1/8 already
fetched, so the tested object *is* the installed object and the window does not exist. A checkout
that cannot fast-forward now aborts with both shas printed. Then a `HEAD == VERIFY_COMMIT`
assertion before the first irreversible step, so any later edit that moves `HEAD` fails loudly
instead of shipping untested code behind a verified sha.

**Proof it can fail** (`_scratch/probe_deploy_guards.py`, restoring `deploy.sh` byte-identical
afterwards):

| Probe | Result |
|---|---|
| old `pull --ff-only origin "$GIT_BRANCH"` restored | **3 failed**, 3 passed |
| `HEAD == VERIFY_COMMIT` assertion removed | **1 failed**, 5 passed |
| restored | `restored identical: True`, `bash -n` OK |

`git ls-files --eol` shows `i/lf w/crlf` — pre-existing on every `.sh` here under
`core.autocrlf=true`. The index is LF, which is what the box checks out, so no `bad interpreter`;
the worktree CRLF is cosmetic and identical to the other five scripts.

## 4. The corpus repair, and the 16 links

`corpus_refresh` (report) predicted `landscape` 8 → 17 and `opp` 29 → 37 chunks, dropping **16**
citation links (4 landscape, 12 opp). `--apply` re-ingested both with `embedded=True`. Then:

```
7 assistant turn(s) examined; 7 with no grounding snapshot (nothing to relink)
0 passage(s) relinkable; 0 already linked
```

Identical to the 2026-10-30 refresh, and that identity is the finding: **all 7 assistant turns on
this box predate `core.0006`, so no chat turn has been recorded since 2026-10-28.** The 16 links
are gone, not recoverable, and `relink_evidence --apply` was correctly skipped. Cumulative over
both refreshes: **56 links lost, all on the same 7 historical answers.** Nothing user-facing broke;
the next turn recorded carries a snapshot.

Final state: `corpus_check` exit 0, all four current; chunks **9 + 37 + 338 + 17 = 401**; home 200;
`/documents/opp/read/` 200; `/health/` `{"status": "ok"}` with all four checks `ok`.

## 5. The number that turned out to be two numbers

The live label counts — landscape **8 of 17**, opp **6 of 37**, saoso and bpp 0 — were checked
against the dev box for parity, and the dev box disagreed on exactly one document:

```
live:  landscape 17 chunks, 8 labelled
dev:   landscape 17 chunks, 0 labelled   → corpus_check: "drift"
```

Total chunks matched at 401, so a count-only comparison would have declared parity. The dev box's
`landscape` is a build behind, which `corpus_check` catches and which **contradicts session `1a`'s
claim that the dev box was current**. Live is ahead of the reference DB.

The repair cannot be run here: the dev `.env` holds only `DJANGO_SECRET_KEY`, and
`deploy/README.md` §4's trap is exact — a refresh without the key **writes 17 NULL vectors**, then
the artefact hash matches and every later run reports "already ingested". So: add the key, then
`corpus_refresh --apply`, and only then compare labels again.

## 6. What was learned that generalises

1. **A gate is only as good as the gap between fetching and installing.** If those are two network
   calls, the gap is the gate's whole runtime, and the log will happily name the wrong commit.
   Detect-and-warn is not a fix here; shrink the window to zero.
2. **"The dev box is current" is a claim with a date and a measurement.** Here it was false within
   the same day, and the totals (401 chunks) still matched, so only a per-document field exposed it.
   Fingerprint the derived thing, not its count — the same lesson as §3.26 and §3.24, arriving from
   a third direction.
3. **The stale documentation was the deploy risk, not the code.** `deploy/README.md` §4's "no
   artefact yet" would have sent the next agent to check `pdftotext` and reason about PDF parsing
   that no longer happens.

## 7. Next

`product/backlog/ready/CONTEXT_CUTS_PRD.md` steps 9–12, unchanged: the five over-cap test files
(**279 tests collected across them — that is the fingerprint a split must not change**), then
`build_corpus.py` (508 bytes over), then the 14 §18.3 rows, then wire `--check` at zero breaches.
`--check` still says **20 breaches**. After that, G12/X2 starting with D80's eight-shape fixture
set.
