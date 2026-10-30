# Handover — MVP 0: A, B, C1, C2, C4 and D landed; UAT signed; G8 closed

> ## START HERE — the table block, half landed
>
> **Step 0 and step 1 are built** (§0n). The artefact format now has a table block: structure parsed,
> one chunk per row, and a malformed annotation **raises** (proved red first). What is left is the
> document, not the mechanism.
>
> Read, in this order — nothing else:
> 1. `In Progress/LANDSCAPE_TABLES_PRD.md` **§12a** (what landed, and the three deviations) then
>    **§9** (the seven steps, with 0 and 1 marked done).
> 2. `Refinement/TABLES_AS_DATA_PRD.md` **§3a** — the syntax as built, and the measurements behind it.
> 3. `Refinement/PGS_PLATFORM_SPEC.md` §18.3 **D72.1–D72.7** and **D73** — all decided; nothing to ask.
>
> **The next act is step 2, and it is a review, not a build.** `scripts/build_corpus.py --doc
> landscape` produces **five headings and the page numbers, no body text** (measured 2026-10-30), so
> the 10-page artefact is hand-typed from the page and reviewed as a diff. Do not run the generator
> and call it done, and do not "fix" the generator first — the landscape is the smallest document and
> the page a reader complained about.
>
> **Before you curate p4–p5 (step 3):** add the `landscape` `-table` page fixture
> (`scripts/extract_fixtures.py`), because §8's "each cell is a verbatim substring of `-table`" cannot
> be asserted without it, and a presence check is the guard Appendix 6a already proved insufficient.
>
> **Two numbers must be measured, not assumed:** the document's chunk count (§8 predicts **11**; the
> lead-in prose makes it **12**, §12a) and `relink_evidence`'s three figures after the one re-ingest
> D72.7 groups here.
>
> **Not this slice:** the OPP (P4) is blocked on the generator repair in
> `design/d71_p4_and_the_generator.html`; SAOSO's appendices (G4) sit behind the same mechanism and
> the same repair. Do not start them first.
>
> **The tree is clean as of this handover** (`git status` empty at `a3f0d1e`), so the board work §0l.4
> warned about is committed (§0n.1).

**For:** the next agent.
**From:** the corpus-and-retrieval session, the public-site session, the
documents session, the chatbot session, the column session, the embedding session,
the answer-coverage session, the budget-and-instrument session, the deployment session,
the reader-structure session, the corpus-artefact session, the corpus-drift session, the
retrieval-baseline session and the deploy-and-close session — **2026-10-30**.
**Repo state:** `main`; `verify.sh` green at **1387 passed / 1 skipped** (110.7 s, measured
2026-10-30 on this box with `--durations=15`); `scripts/fast.sh` at **1373 passed / 1 skipped**
(64 s warm). The board work §0l.4 found uncommitted is committed (§0n.1), so the tree is clean. `tests/e2e/test_public_site.py` green at **38**. The test lane's work
(`scripts/fast.sh`, `pgs.settings_test`, the `slow` marker) is **committed**, which is where
the wall time went from ~4 min to 65 s.

**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **in sync** (pushed 2026-10-30).
**Live:** `https://organicguarantee.africa` on the homtini VPS at **`8d2839d`**, deployed
2026-10-30 — and **its corpus is now current for the first time**: `corpus_check` reports
`bpp current 9/9`, `saoso current 338/338`, `opp`/`landscape` `no artefact`, **384 chunks, 0
unembedded**. It carries **no `CHAT_*` overrides** in `.env` (first-install never writes them), so
the code defaults — 4096 output tokens, ceiling 8192, retrieval limit 8 — are what runs. Two
gaps the box still has, both recorded: the 40 citation links the refresh dropped are
**unrecoverable** (§0k.4), and `opp` + `landscape` hold 37 chunks where the dev box has 38 (§0k.4).

## 0n. 2026-10-30 — the table block landed, and step 1 is mechanism only

**State: green, and the artefact format can hold a table.** Step 0 reproduced §1 of the landscape
PRD exactly, and step 1 shipped the block. Nothing of the landscape itself is curated yet — the
fixture that proves the format holds p4's real rows is a *draft*, and says so.

### 0n.1 The board work got committed, in two attributed commits

`c7a7df8` (the feature: `_board.py`, `_board_data.py`, `building.html`, `scripts/board.py`,
`test_board.py`, the `Public:`/`Summary:`/`Public title:` headers, the deploy pre-check, the CSS and
`DESIGN.md` §7.12) and `7678880` (D74, the regenerated `backlog.md`, §0m). Green before and after:
`fast.sh` **1331 passed / 1 skipped** with the work in the tree, which is how §0l.4 described it.
`backlog.py --write` was re-run **after** the PRDs were committed, so the index no longer names
untracked files.

### 0n.2 Step 0: every number in the landscape PRD reproduced, none corrected

`_scratch/step0_landscape.py` (git-ignored) prints them all from one in-process build: 8 transformed
pages with the band lists, **8 chunks / 6 branches** (`R500`, `PGS SA.` and the four real ones),
**1 / 2 / 0 of 5** sentences quotable in raw / `de_column` / `-table`, the non-space multiset
identical on **every** page 2–9, **0** chunks holding `Participatory Guarantee Systems`, `six basic
elements`, `First-Party` or `Third-Party`, and the §5.7 simulation (exclusion alone → same 8 chunks,
same 6 branches). **Xpdf 4.00 is on this box**, so `-table` works; the box's `pdftotext` is the same
build the fixtures were made from.

### 0n.3 Step 1: the block, the guard, and one chunk per row

| File | What it now does |
|---|---|
| `knowledge/corpus.py` | parses `<!-- table` / `<!-- row: … -->` / `<!-- cell -->` / `<!-- row-divider: … -->` / `<!-- /table -->`; a cell is a **slice** of `section.text`; every malformed form raises with the line named |
| `knowledge/sections/__init__.py` | `TableCell`, `ParsedTableRow`, `ParsedTable`, and `ParsedSection.tables` |
| `knowledge/tables.py` | `chunks_for_parsed_section` (prose by the chunker, **one chunk per row** by the table code) and `row_chunk` (text = cells, heading_path and anchor from the row label, page = where the row starts) |
| `knowledge/ingest.py` | `chunks_for_sections` walks **sections** now, not chunks — a table section can no longer be substituted by a same-ref section elsewhere |
| `knowledge/tests/test_corpus_tables.py` | 29 tests: 19 refusals, 10 structure/chunk assertions |
| `knowledge/tests/test_landscape_table_block.py` | 13 tests over **p4's real rows**: five columns, 400-character cells, two cells the paper leaves empty, the seal's printed label, and *"Annual membership fee (paid by the PGS group to PGS SA): R500"* quotable from **one** chunk |

**The guard was written first and proved red** — that is the one instruction §0l's block insisted on.
`<!-- cell -->` outside a block, `<!-- cells -->` inside one, `cols:` missing, a block never closed, a
heading inside a block, a row with more cells than columns, a row that never closes, a divider with no
row beneath it: each fails, naming the line. The word-pin guard was broken deliberately
(`aggregate` → `agregate`) and went red before being restored.

**Three deviations from §3a, all recorded in the PRD's §12a:** the block closes **explicitly** with
`<!-- /table -->` (a table that ends by inference lets its last row own the prose after it); a
divider's **kind trails** its text, as §3a writes it; and **prose outside the rows is its own chunk**,
so §8's predicted **11** will be **12** unless a reviewer folds the lead-in in. The count gets
measured at step 2 — deleting text to hit a predicted number is the worse trade.

### 0n.4 Two findings that change the next session

- **The generator cannot draft this document.** `scripts/build_corpus.py --doc landscape` emits five
  headings and the page numbers, **no body text** (`## R500`, `## PGS SA.`, `## SAOSO` — §1.2's false
  headings, now with the text missing rather than scrambled). Step 2 is a hand-typed reviewed pass.
  That is also the generator repair `design/d71_p4_and_the_generator.html` describes, which the OPP
  and SAOSO's appendices are blocked on.
- **There is no `landscape` `-table` page fixture.** `knowledge/tests/fixtures/pages/` carries
  `layout` and `raw` only, so §8's "each cell is a verbatim substring of `-table`" is not assertable
  yet; step 3 must add it via `scripts/extract_fixtures.py`, or the guard degrades to a presence check
  that Appendix 6a already proved insufficient.

### 0n.5 What was deliberately not done

No artefact for `landscape` or `opp` (P4/P5), no `TABLE_BANDS`, no front matter (D72.6), no reader
grid (D72.3/step 6), no re-ingest and therefore **no `relink_evidence` run** — nothing this session
wrote a `DocumentChunk`, so no evidence link was dropped and the live corpus is untouched. The two
pytest counts above are the whole of the evidence.


---

## 0m. 2026-10-29/30 — the backlog gets a public page, and it is six sentences, not a mirror

**State: built, gated, UAT unsigned.** This is the work §0l.4 found uncommitted in the tree. It
is now finished rather than half-written; the section stays open until the sign-off.

- **What the feature is.** `/building/` — a four-column board (In design / Up next / Building /
  Shipped) of cards that are one title and one 180-character sentence. Footer link, not a nav
  link: six nav links plus the CTA already fill one line at 768 px. Decision **D74** in
  `PGS_PLATFORM_SPEC.md` §18.3; PRD and plan in `In Progress/PUBLIC_BOARD_{PRD,PLAN}.md`.
- **Why it is not a rendering of `product/backlog/`.** Measured: **10 of 36 PRDs contain a term
  `test_claim_discipline.py` forbids**, and the sentences around them are notes about the live
  WordPress site's own overclaims (*"the live site's Favour Farm description is the source of the
  'pasture raised' phrase, and it must not be copied here"*). Publishing that text would put a
  named farm's unsupported claim on the group's own site. So the board is **curated**: a card
  exists only where a PRD carries `**Public:** yes` plus a `**Summary:**`; six do.
- **The data path.** `product/backlog.py --board-json` classifies (reusing the one
  `STATUS_RULES` table) → `scripts/board.py` validates and writes the committed artefact
  `core/services/_board_data.py` with a `SOURCE_DIGEST` → `core/services/_board.py` shapes it.
  **Zero database, zero request-time file reads**, so a PRD edit cannot change the live site
  without a deploy. `scripts/board.py --check` runs in `deploy/deploy.sh` *before* the backup —
  a stale board aborts the deploy with the fix command.
- **Three refusals, each proved by breaking it:** a `Public: yes` PRD with no summary, with a
  summary over 180 characters, with a claim term, or in a directory with no column
  (`spike/`, `BugFixes/`, `on_hold/`, `systems/`) stops the generator with the file named. A
  hand-edited artefact containing "pasture raised" made
  `test_claim_discipline.py::test_no_unsupported_claim[building]` go red — both layers fail, as
  they must.
- **`FORBIDDEN_CLAIMS` moved.** The canonical claim list now lives in `core/services/_public.py`
  and `core/tests/test_claim_discipline.py` imports it, because the generator needs the same list
  and two copies that agree today are two copies that disagree tomorrow. The test's
  non-empty/lowercase guard is unchanged.
- **Two plan deviations, recorded in the plan's §0.3:** a third header field `**Public title:**`
  (the `h1` of two candidates is internal vocabulary — *"MVP 1a — In-Office Visit Flow"*), and the
  phone layout **stacks** instead of using the planned `overflow-x` rail (the rail passes the
  `documentElement.scrollWidth` guard and asks a phone user to swipe sideways; stacking passes
  the same guard and reads better).
- **Left undone, deliberately:** the UAT (`tests/uat/public_board_uat.md`, five judgement
  scenarios, unsigned — so the backlog item stays in `In Progress/`, not `Done/`), and
  `tests/tools/test_board.py` is **not** in `scripts/fast.sh --critical`: the invariant that
  matters (a claim must not reach the page) is already carried there by
  `test_claim_discipline.py`, so the lane did not need a ninth file.

---

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

## 0j. 2026-10-29 — the landscape's tables are decided; retrieval gets a brief for the instrument it lacks

**Nothing was built in this session.** No migration, no code change, no test added, no corpus
re-ingested: **docs and decisions only** (`product/backlog/`, `product/design/`). The tree's only new
files are one PRD, one spike brief and one decision artifact; the only edits are to `PGS_PLATFORM_SPEC.md`
§18.3, two existing PRDs, `HANDOVER.md` and the generated index.

**The tree also carries work that is not from this session** — `core/services/_public.py`,
`core/static/css/{components,site}.css`, `core/templates/public/{home,become_a_member}.html`,
`sections/_fee_tables.html`, `sections/_key_facts.html`, the new `sections/_recognition.html`,
`sections/_why_join.html`, `core/tests/test_public_costs.py`, `product/design/DESIGN.md` and
`C1_BUILD_PLAN.md`, plus `product/backlog/todo.md` and the test-lane files (`scripts/fast.sh`,
`pgs/settings_test.py`, `pytest.ini`, `scripts/verify.sh`, `product/docs/context/*`). It appeared
**during** this session, so another instance was working in the same tree — attribute it before staging
anything, and stage this session's paths by hand rather than `git add -A`.

**What was asked.** A reader reported that *Certification Landscape › establishing-a-pgs-group* showed
the printed table as column-major soup, cut mid-cell. The diagnosis is in
`Refinement/LANDSCAPE_TABLES_PRD.md` §1 with the commands that reproduce it. Three findings, in
descending order of size:

- **Pages 1–3 of that document are not in the corpus at all** (measured: `0` chunks contain
  "Participatory Guarantee Systems", the six basic elements or the three certification routes). The
  text extracts fine; `HeadingParser` opens a section only at a CAPS line, page 2's only capitals line
  is the running header (suppressed by repetition) and page 3's are Title case (a documented miss).
  So "what is a PGS?" is uncitable, and the miss is indistinguishable from a corpus gap.
- **`de_column` fires on 8 of the landscape's 10 pages**, five of which are 5-column tables. This repo
  already excludes five such pages elsewhere (SAOSO 2/82/83, OPP 4/11); landscape had no entry.
- **No extraction mode makes a cell quotable** — measured 1/5 (raw `-layout`), 2/5 (`de_column`,
  shipped), 0/5 (`-table`, which *is* loss-free: identical non-space character multiset). A table row is
  two-dimensional and a chunk is one; the flattening has to be eliminated, not tuned.

**Decided** (spec §18.3 **D72.1–D72.7**, argued on a decision page the product owner answered
2026-10-29: `product/design/d72_landscape_tables_questions.html`): a row on PDF 6 is a seal and the
artwork cell is its printed label; a fee is a cell, never a derived fact; **the reader renders the
printed grid**; the OPP's two table pages wait for their artefact; the page-break row belongs to one
table; **pages 1–3 enter as reviewed front-matter passages**; the exclusion ships with the rows in
**one** re-ingest.

**Decided, and this one relocated work** — spec §18.3 **D73**: table rows are stored in the **reviewed
corpus artefact**, not in `knowledge/tables.py`, and the vector is computed from a **stored context
column** (`title · column: value`), never from the bare cells. Consequences:
`LANDSCAPE_TABLES_PRD.md` §5.1/§5.2 (an N-cell `TableRow` and a `(doc_key, ref)` key) are **superseded**
and its step 2 — a key refactor — is **dropped**; the landscape's artefact conversion (P5) moves ahead of
its place in the rollout, because 10 pages is the cheapest of the four and it lets the front matter land
as a reviewer-added heading.

**Measured, and it constrains the artefact syntax** (`Refinement/TABLES_AS_DATA_PRD.md` §3a): a GFM pipe
table chunks as **one** chunk (rows are one paragraph); blank lines between rows **still** produce one
chunk (the chunker packs to ~800 tokens); and `<!-- cell -->` is **silently dropped** today because
`ANNOTATION` matches only `corpus|page|ref`. So a table's structure must be parsed *as structure* (like
`sub_refs`), one chunk per row must come from the table code, and a malformed table annotation must
**raise**.

**Also measured — a live retrieval defect, unfixed** (`TABLES_AS_DATA_PRD.md` §7 Q5): Appendix 6a's
twenty curated rows are **3–4 tokens** each (`Ewes / 13,3`) and they are *all twenty* of the corpus's
3–4-token chunks (Appendix 2 runs 5 chars `Guano` → 769). All 385 chunks carry a vector, fused by RRF
(k=60). `"laying hens"` retrieves page 85; `"how many laying hens per hectare"` returns **no hits** — the
row is reachable only by its own words. D73's context column is the fix; whether it helps is unmeasured.

**A correction the repo should keep.** Four questions were put to the product owner as preferences and
only three were product decisions. "Pure function vs stored column" is **engineering**, and the tell is
in `TABLES_AS_DATA_PRD.md` above §7: a product decision changes *what the product claims*; an engineering
decision changes *how a claim is served and checked*.

**Why nothing was built, and what is next.** Every remaining step depends on a decision now taken but not
yet implemented, and the corpus work is gated on the artefact's table syntax. The next session starts
with **`spike/RETRIEVAL_EVAL_SPIKE.md`**, and it is deliberately first: it records the **baseline on
today's corpus** before the table work changes anything, which is the only way the D73 comparison can
mean something. Its first command is in that file's §0. Then: the table block in `corpus.py` with a
failing guard on a malformed annotation, proven on landscape p4–p5.

---

## 0i. 2026-10-28 — the corpus can say whether it is current, and the ingest fails closed

**This is the most recent slice.** Plan tasks **P2.1–P2.4** and **P7.1** of
`product/backlog/In Progress/CORPUS_CANONICAL_FORMAT_PLAN.md`, built as one idea: *drift is
visible, and repairing it is a decision rather than a side effect.* Nothing about retrieval,
the reader or a public page changed.

- **`StandardDocument.corpus_digest`** (migration `knowledge/0004`) records the sha256 of the
  reviewed artefact a corpus was built from, or `""` when the PDF was parsed. Until now that
  value existed only on `IngestReport` — printed and thrown away — so nothing could compare a
  box with its review.
- **`manage.py corpus_check`** — read-only, one row per governed document, exit 1 on drift, and
  it names the fix instead of running it. Three states are drift and it says which: *built from
  the PDF*, *the artefact changed since*, *nobody ingested it*. **No artefact is not drift**
  (`opp`, `landscape` until P4/P5) — a check that went red for work nobody has done gets ignored.
- **`manage.py corpus_refresh [--apply]`** — a dry run until told otherwise. `--force` deletes
  the join rows every chat turn stood on, so it counts them first (`citation_links()` walks
  Django's relation metadata, because `knowledge` may not import `core`) and says the number
  before `--apply` can spend it.
- **`deploy/deploy.sh`** runs `corpus_check` after `publish_documents`, guarded with `if !` so
  `set -e` cannot turn a stale corpus into a failed deploy, and it **never refreshes**: a
  re-embed of four documents is a decision for a person with a terminal.
- **The ingest fails closed (D55).** A document that *declares* a reviewed artefact
  (`CORPUS_DOCUMENTS[key]["corpus_artefact"]` — `saoso`, `bpp`) now reads that file by default;
  if it is missing the command exits non-zero and writes nothing, naming
  `scripts/build_corpus.py` and `--from-pdf`. A declaration, not a file-exists probe: the two
  disagree exactly when the file is gone, which is the failure worth catching.
- **What moved in the suite:** ~10 tests that ingest `saoso`/`bpp` from the PDF now pass
  `from_pdf=True` — they were always about the extraction. `test_the_shipped_corpus_resolves_as_measured`
  re-measured 39/30/9 → **41/30/11**: the artefact carries each section's printed heading in the
  body, so `Appendix 4. Table 1`/`Table 2` read as mentions of `Appendix 4` (two tables, one name,
  no single target). No link was lost; `EXPECTED_LINKS` is unchanged at 30.
- **Judged, not built:** nothing here needs a UAT table of its own. The operator-facing judgement
  — *do these three commands read clearly on a real box, and does the deploy's warning tell
  someone what to do?* — is carried by **P7.4**, which runs all of it against the live corpus.
- **This machine is (correctly) reported as drifting:** `bpp 9/9 · built from the PDF`,
  `saoso 338/338 · built from the PDF`, `opp`/`landscape` `no artefact`, exit 1. It was **not**
  refreshed: there is no `GEMINI_API_KEY` here, so `--apply` would have downgraded 385 embedded
  chunks to lexical-only. That is the box's job, not the laptop's.
- **Known gap, unchanged:** `knowledge/tests/test_anchors.py::test_every_passage_of_the_real_corpus_resolves_to_itself`
  skips in both lanes ("no corpus ingested on this instance"), so the D68 anchor guard is not
  actually in the gate. Worth closing before P7.4.
- **New finding, blocking P7.4's own gate:** the artefact ingest still reads the PDF for **one**
  field — the printed `toc` (`knowledge/ingest.py`, the `toc_pages = extract_pages(path)` line in
  the artefact branch, D68 §7.5). So `corpus_refresh --apply` needs `pdftotext` even though the text
  comes from a reviewed artefact, and P7.4's "the box needs no reader for any of it" / "remove
  poppler-utils and refresh still works" cannot pass as written. The plan records both fixes
  (carry the TOC in the artefact, or preserve the stored `toc` across a refresh); neither is built.
- **Also filed this session, nothing built:** **`Refinement/CODE_ATLAS_PRD.md`** — the product
  owner's requirement for one generated, committed view of the application as built (schema,
  services, views and routes, async/schedulers, the corpus pipeline), in `product/docs/state/`, with
  a gate that regenerates and diffs so it cannot rot. It answers "what exists" and is deliberately
  not a handover, a spec or a UAT. Today's numbers are in its §1 and they are the reason it exists:
  30,744 Python lines, 12 models / 87 fields, 46 service functions, 17 view functions, **one**
  Celery task and **no beat schedule**, 36 migrations, 59 test modules.
- **Awaiting one decision, D71** (`product/design/d71_p4_and_the_generator.html`): what the next
  corpus slice is, now that P4's first step is measured broken. Recommendation: repair the generator,
  make P3.1's regeneration gate real, teach `OppParser` the `heading_path` rule, then review the OPP
  as a verification pass (`product/backlog/In Progress/CORPUS_CANONICAL_FORMAT_PLAN.md`, P4's
  landing note).
- **Not committed by this session:** the test-lane work (`scripts/fast.sh`, `pgs/settings_test.py`,
  the `slow` marker, `tests/tools/test_test_harness.py`, `product/docs/context/TEST_COST_PLAYBOOK.md`)
  arrived uncommitted and was deliberately left uncommitted — it is another session's, and the gate
  is green with it in the tree (1265 passed / 1 skipped).
- **⚠ Two artifacts claim D71.** This session filed `product/design/d71_p4_and_the_generator.html`
  ("what is the next corpus slice") and its export emits a `D71` row for SPEC §18.3. A later
  uncommitted artifact, `product/design/d71_self_check_questions.html` ("the front door: 19 questions
  before a farmer applies", `/before-you-apply/`), claims the same number. **Recommendation:** the
  front-door page keeps **D71** — it is a product-and-copy decision, which is what §18.3 is for — and
  the corpus page becomes an unnumbered execution decision or **D72**; the clear-conversation
  decision in `Refinement/ASK_PANEL_REFINEMENTS_PRD.md` §2 then becomes D73. Nothing is renamed yet,
  because both files belong to different sessions and the owner should choose.

---

## 0a. 2026-10-23 — `/ask/` became a board of answer pages, and citations became clickable

**This is the most recent slice, and it is not deployed.** D62 chose the shape on 2026-10-23;
this session built it (`product/backlog/In Progress/ASK_SURFACE_PLAN.md`, PRD §4a).

- **The board** (`PublicQuestion`, migration `core/0007`) is a content table with a publish flag,
  not the one-hour cache. A consenting question lands `AWAITING`; a consenting refusal lands
  `WAITING` and points at its `EscalatedQuery`. Only an administrator publishes, and the slug is
  generated from the **edited** question at that moment — the edit is the redaction.
- **The answer page** is `/ask/<slug>/`: the clause in full, *what this answer does not cover*
  (required, enforced by a test), the questions next to it, a copyable citation, `checked
  <date>`, and `noindex` on a gap page.
- **Citations are clickable for the first time.** `Citation` carries `document_code` and
  `reading_anchor`, and `/documents/<code>/read/` renders the ingested text with a contents
  list, in-document search and one anchor per section reference. **It is not a PDF page link**:
  the PDF is streamed as an attachment, and D67 records why the text is the better surface.
- **Two guards were proven by breaking them**, and one pre-existing defect was found:
  `publish_documents` wrote an absolute `source_path`, so the citation→document join could never
  match on a second machine (`testing_hazards.md` §1.32).
- **Not built, deliberately:** the trace console (needs arm/rank on `grounding`), the
  wider-reading tier (no documents behind it), the stage-2 follow-up rewrite.
- **UAT is drafted and unsigned:** `tests/uat/ask_surface_uat.md` — seven judgement scenarios.
- **The reader is measured, not assumed:** on the real SAOSO corpus it renders 333 KB raw /
  **61.6 KB gzipped** in 4 queries (319 passages); the PDF is 192 KB. Raw, the page is *bigger*
  than the file — on the wire, with nginx gzip on text/html, it is ~3× lighter. A search adds
  one query.

---

## 0b. 2026-10-27 — the concordance is decided and planned; nothing is built

**Read `product/backlog/ready/CONCORDANCE_PLAN.md` before touching `/documents/`.** Eleven tasks,
77 steps, each test-first. The reader that shipped on 2026-10-23 is being replaced in place.

- **The decision is `PGS_PLATFORM_SPEC.md` §18.3 D68** — eight answers, all logged. The argument,
  the options and the rejected alternatives are in
  `product/design/d68_concordance_open_questions.html`; `ready/CONCORDANCE_PRD.md` §7 is the
  decision table, and §10.5–10.8 are the findings the plan inherits.
- **What changes:** `/documents/<code>/read/` renders the document's own printed structure as a
  tree with one open branch; a citation reads "View this line", opens a new tab, and lands on the
  passage it quotes; the page states which printed sections the corpus does not hold.
- **Three things were measured first and they are not in the PRD's original story** (all in
  `ready/CONCORDANCE_PRD.md` §10): the corpus is **22 of 28** printed SAOSO sections (Section A,
  pp. 4–11, and Appendices A–C, pp. 93–96, were never ingested); branch titles taken from headings
  misname `S1` and `Appendix 2`; and **57 of 366 passages share a citation anchor**, so today a
  citation to 29 of the 30 Appendix 2 rows opens the first one. That last one is filed as
  `product/backlog/BugFixes/citation_anchor_collision.md` — it is a live defect, not only a
  prerequisite.
- **`scripts/probe_concordance.py`** (read-only) prints the tree, the titles, the missing sections
  and the anchor ambiguity count for the corpus in the database. Run it before Task 1; the plan's
  §0.4 records what it printed when the plan was written (0 ambiguous anchors, 6 missing sections).
- **Do not measure anything before `python manage.py publish_documents`.** On a machine whose
  `PublicDocument` rows predate `4c94c09` they hold absolute paths, `corpus_for()` returns `None`,
  and the reader says "not published the text" for every document (§0.2 of the plan).
- **UAT is drafted and unsigned:** `tests/uat/concordance_uat.md`, seven judgement scenarios. This
  feature is not done without names in that table.
- **One amendment to a decision, recorded as §7.3a:** the landscape has no reviewed corpus
  artefact (`knowledge/corpus/` holds only `bpp.md`; D53/D55 say OPP/SAOSO/landscape are not yet
  converted), so its two wrong branch names are corrected with reviewed data
  (`REVIEWED_BRANCH_TITLES`) rather than a corpus edit.

---

## 0c. 2026-10-27 — the concordance is built; the reader is the document's tree

`/documents/<code>/read/` now renders the printed table of contents as its navigation, with one
branch open; a citation reads **"View this line"**, opens in a new tab, and lands on
`?section=<passage anchor>#<passage anchor>`; and the page names the printed sections the corpus does
not hold (Section A, Appendices A–C). The anchor defect is closed — 57 of 366 passages shared one, and
later passages in a group are now named for their own words (`appendix-2-wood-bark-and-sawdust`) —
with `StandardDocument.toc` (`knowledge/0003`) as the only new field. Gate **954**, Playwright **53**.
**The UAT is unsigned** (`tests/uat/concordance_uat.md`): the feature is not done without names in
that table.

---

## 0d. 2026-10-27 — a passage is laid out as the document prints it

The reader now renders each passage as blocks: paragraphs with their hard wraps joined, the
printed headings, **real lists** — `a.`–`f.` for SAOSO's conditions, with the roman sub-list nested
inside its item (`S8.1`) — and **glossary terms** (`ACB`, `Habitat`, `Extensive Farming`) above
their definitions. `S1`'s eight chunks overlap by 21–57 words on purpose (retrieval); the reader now
trims that overlap for display, so the definitions page no longer prints the previous chunk's last
paragraph again. The marker is a CSS list marker, never text: the corpus prints a bare `a`, and
`flatten(blocks)` reproduces every chunk of the shipped SAOSO exactly (a guard in
`knowledge/tests/test_passages.py`). Stored text, retrieval, anchors and the citation audit are
untouched — this is display-only (`PASSAGE_LAYOUT_PRD.md`). The concordance's own spacing was
refined in the same pass: a 72 rem working column, a 38 rem reading measure (~85 characters), one
hairline per printed clause, sticky search and tree. **UAT Scenario 8 is unsigned.**

---

## 0e. 2026-10-27 — the reader is refined; what is left is judged, not built

**What landed this session** (committed; gate **983 passed / 1 skipped**, Playwright **53**):

- The concordance's **CSS pass**: a **72 rem** working column, a **38 rem** reading measure (~85
  characters at 16 px), one hairline per printed clause, a sticky search **and** tree, tabular page
  numbers, muted locators, a target highlight that bleeds to the pane edge, and a one-row search on a
  phone. **The citation scroll offset now clears the sticky search** — before this, following a
  citation put the passage *behind* the search (measured: target top 67 px, search bottom 191 px).
- **Passage layout** (`PASSAGE_LAYOUT_PRD.md`/`_PLAN.md`, both in `In Progress/`): paragraphs with
  hard wraps joined, printed headings, real lists (`a.`–`f.`, roman nested in `S8.1`), and glossary
  terms (`ACB`, `Habitat`, `Extensive Farming`) above their definitions.
- **`S1` (Definitions)** — the report that started this: the chunk overlap is **no longer printed
  twice** (`strip_overlap`; 21–57 repeated words at five boundaries) and terms are no longer glued to
  their definitions. The page reads as a glossary.

**The one thing left to do is the UAT.** `tests/uat/concordance_uat.md` has eight scenarios and none
is signed; **Scenario 8** is the passage layout. The tooling is the same as §18: `uat_seed --check`,
`scripts/uat_runner.py`, `scripts/uat_signoff.py`. Nothing below blocks it.

### Final refinements deliberately left for the next agent (each is a judgement, not a TODO)

1. **Repeated passage locators inside one branch.** `S1` prints `S1 · printed p. 22` above each of its
   eight chunks; `S5` repeats a locator 52 times. They mark the ids a citation can land on. Decide:
   keep them (honest, and useful when a citation lands mid-branch) or print the branch's locator once
   and keep only the `id`s. Scenarios 1 and 3 are where it shows.
2. **Desktop search width.** The input is ~941 px inside the 1088 px panel at 1280 px. Capping the row
   (~40 rem) reads better but leaves a large empty panel; the alternative is a narrower search panel.
   Judge on a 1440 px screen as well as 1280.
3. **Phone search is not pinned** (111 px + 80 px header ≈ 25% of an 844 px screen); the tree is a
   disclosure instead. If the reviewer wants both pinned, make the phone search one compact row or a
   single field with an icon button.
4. **The tree has no scroll affordance** when 23 rows exceed the viewport on desktop. A subtle
   top/bottom edge may help; the scrollbar appears on hover only.
5. **Term vs heading weight** is two steps (`--text-lg` vs body, both bold forest). Judge at 390 px
   whether `ACB` reads as a term rather than as a section.
6. **The corpus artefacts are filed, not fixed** — `BugFixes/saoso_text_glyphs_and_boundaries.md`:
   30 of 366 chunks hold U+FFFD where the paper prints `°`, `²`, `≥`, a bullet, an en dash or `ü`; a
   superscript `2` splits the *Factory farming* sentence; `S1`'s last chunk carries the `SECTION B`
   half-title of printed p.30. These need the reviewed SAOSO artefact and `--force`; the reader must
   **not** substitute characters (the citation audit checks quotes against the stored text).

**Backlog state.** `Done/` gained **three** features on 2026-10-28 — CONCORDANCE, PASSAGE_LAYOUT and
READER_STRUCTURE (PRD + plan each). `In Progress/`: ASK_SURFACE, VPS_DEPLOYMENT,
CORPUS_CANONICAL_FORMAT, CORPUS_COLUMN_EXTRACTION, MVP0. `ready/`: only the MVP 1a pair.
`BugFixes/`: `citation_anchor_collision` **closed**; `saoso_text_glyphs_and_boundaries` — §1 closed
(the glyph loss), **§2–§5 open** (the `m²` superscript, the `S1` half-title, three letterspaced
lines, and Appendices 6a/6b's lost table rows — the last is G4's shape and its mechanism already
exists as `TABLE_ROWS`).

**Repo state.** `main`, tree clean, **42 commits ahead of `origin/main`**, nothing pushed or deployed.
The live site is still `206f35f`, and its corpus predates D52/D53 — §18's two operational items are
open and now further behind (the reader's layout is not deployed either).

## 0f. 2026-10-27 — the corpus keeps its glyphs: `-enc UTF-8`, and the U+FFFD mystery is closed

**This is the most recent slice.** D69, plus the reader-structure PRD that came out of the same
reading session (last part of this section, and where the next agent starts).
`BugFixes/saoso_text_glyphs_and_boundaries.md` §1 is **closed** — and its diagnosis was wrong, which
is why it stayed open for a week.

- **The `�` was never the PDF.** `knowledge/extraction.py` decoded `pdftotext`'s stdout as UTF-8
  with `errors="replace"`; the `pdftotext` on this machine is **Xpdf 4.00**, whose default output
  encoding is **Latin-1**. Measured on the eight shipped PDFs: **275 of 433 154 bytes are 8-bit and
  none of them is valid UTF-8** — and `pdftotext -enc UTF-8` extracts all eight with **zero**
  U+FFFD. The old claim ("no encoding recovers the real character") came from that Latin-1 path and
  is retracted; the en dash and the `≥` are *different glyphs* (they only collapsed to one byte on
  the lossy path).
- **83 characters in the four ingested documents were affected**, all recovered: `360°`, `100 m²`,
  `45°C`, `rosé`, `Mèthode` (the document's own spelling), `Section B – Appendix 6`,
  `R 250,001 – R 500,000`, `für`. **Plus 66 OPP `●` bullets that had been dropped outright**, so its
  lists were ingested as prose; `●` is now a list marker.
- **Two "measured" constants moved**, and both moves are improvements: the OPP's PDF 4 is now an
  explicit layout exclusion — it was only de-columned *because* §3.2's bullets were missing, and a
  two-band split of its 3-column table orphaned `Members will be invited to take part` from its
  predicate. `test_columns`/`test_reflow`/`test_ingest` are updated with the reason beside them.
- **The BPP artefact was regenerated** and its five reviewed edits re-applied; two private-use
  Dingbats bullets (U+F06E) are now recorded `CORPUS_EDITS` drops, because no extractor can name
  them and no reader can see them. `MAX_EDITS` ratchets 5 → 7.
- **Guards, proven by breaking them:** `test_corpus_glyphs.py` (every committed page and range
  fixture: zero U+FFFD; ten named characters must survive; the manifest must name `-enc UTF-8`),
  `test_passages` (the ingested text, end to end), and `test_extraction` (the command asks for UTF-8;
  a Latin-1 stream raises `ExtractionError` naming the file instead of becoming U+FFFD).
  `testing_hazards.md` **§1.34** records the trap with the byte evidence.
- **Still open in that bug file:** §2 the *Factory farming* superscript still splits its sentence
  (`m .` is missing the `²` — a line-order problem, not this one), and §3 `S1` still ends with the
  next part's half-title. Both are D53 artefact reviews, not view work.

**Local state.** The dev corpus was re-ingested with `--force` and embeddings (319/30/8/9 chunks,
**0 U+FFFD**); that dropped the old `ChatMessage.retrieved_chunks` evidence links, as `--force` does.
Gate **1004 passed / 1 skipped**; **45 commits ahead of `origin/main`**, nothing pushed. The live
site is still `206f35f` and needs the same re-ingest (P7.4) before any of this is visible there —
`uat_seed --check` will keep blocking on the corpus check until it is done.

### Where the next agent starts: judge the UAT (§0g)

**This was the previous handover's "next start" and it is now built.** The four questions in
`ready/READER_STRUCTURE_PRD.md` §10 were answered by the product owner on 2026-10-27, the plan in
`In Progress/READER_STRUCTURE_PLAN.md` was executed the same day, and **the reader is the document's
own structure** (§0g). What is left is the human judgement: `tests/uat/concordance_uat.md` carries
eleven scenarios and **none is signed**. Scenarios 9–11 are the ones this slice added.

The rest of this section is kept because its measurements are still the numbers the UAT is judged
against — run `python scripts/probe_reader_structure.py` and it prints them from the shipped code.

**The measurements are already made, so do not re-litigate them.** `scripts/probe_reader_structure.py`
is committed and read-only: run it and it prints what the PRD claims. Three findings it produced:
**19 of Appendix 2's 30 rows print no condition at all** (that is the reviewer's "list of standalone
inputs" — the paper's silence, rendered as body text); SAOSO has **10 section references and 29
appendix mentions**, of which **9** cannot be decided by number alone; and the corpus also prints
**seven unqualified `Section n`** references (`Section 4.6.2`, `section 5.7`), which resolve only
inside the part they are printed in. `Section A – 2.3` is the trap: it must go to the page's
"printed sections not in the corpus" note and **never** to `S2`.

Nothing in that slice needs a migration or a re-ingest: it is display-only, which is why it can
follow the corpus work so cheaply. See also §0e items 1–5 for the rest of the judgement list —
item 6 closed for the glyph half in §0f.

---

## 0g. 2026-10-27 — the reader is the document: a table, references that go somewhere, and a glossary

**All ten tasks of `In Progress/READER_STRUCTURE_PLAN.md` landed.** Gate **1138 passed / 1 skipped**,
Playwright **53**, `lint-imports` kept, `manage.py check` clean, `uat_seed --check` **ready** (366
chunks, 0 without a vector, 8 published, Xpdf 4.00). **Nothing pushed, nothing deployed.**

- **Appendix 2 renders as the paper's table** (D70.1): a caption quoting the two printed columns, one
  legend sentence, four part headings, three `South African specific` qualifiers, and 30 rows whose
  substance is its own entry — so `Guano` no longer renders at body weight. The 19 rows whose
  condition cell the paper leaves empty carry a muted `no condition printed`, and no row reads as
  permission. The structure is reviewed data beside `TABLE_ROWS` (`TABLE_SECTIONS`), and a test proves
  each of the seven dividers still sits, on the printed page, immediately above the row it names.
- **A reference goes somewhere, or it says why not** (D70.3): `Appendix 6 Minimum Surface Areas…`
  opens Appendix 6b in a new tab; `Section 4.6.2` opens `S4`; **`Section A – 2.3` opens the page's own
  note that Part A is printed and not in the corpus**, never `S2` — a different part. Measured: **39
  mentions, 30 resolved, 9 left as text**, and all 9 (8 × `Appendix 4`, 1 × bare `Appendix 6`) carry a
  tooltip naming the parts they could be. The BPP and the landscape resolve nothing, which is correct.
- **A defined word is a click away** (D70.4/D70.7): the term list is **derived** from `S1`'s rendered
  blocks minus a reviewed rejection list, so it cannot stale. **69 headwords and 69 ids** on the real
  corpus; one link per term per passage, and none inside the glossary itself.
- **One locator per run** (D70.5): **366 → 311** lines (319→273, 30→28, 8→6, 9→4), every passage keeps
  its `id`, so a citation still lands.
- **The missing-sections note moved out of the phone disclosure** and carries `id="not-in-corpus"`
  (D70.6) — a fragment inside a closed `<details>` cannot be scrolled to.

**Page weight, measured the same way before and after** (dev corpus, Django test client, gzip level
6): Appendix 2 **33 309 → 37 664 B raw (+13.1 %), 5 941 → 6 521 B gzip (+9.8 %)**; `S1` 47 935 →
49 979 raw (+4.3 %). The PDF of the same appendix is 192 KB. **No new query**: the reader was 3
queries before this slice and is 3 after it.

**Corrected while building (recorded, not absorbed):** the plan expected **71** glossary headwords and
the page anchors **69**. `Buffer Zone` and `Homeopathic Treatment` are each the tail of one chunk and
the head of the next, so the reader's overlap trimming prints them as the last *paragraph* of a
passage, where the layout finds no following line and does not call them terms. They are not linkable;
the test asserts their absence. Making them linkable needs the corpus artefact, not view work.
`READER_STRUCTURE_PLAN.md` §12 has the six signature changes and the three findings.

**Two further corpus findings were filed the same day**, both found by reading the rendered appendix
and the glossary: `BugFixes/saoso_text_glyphs_and_boundaries.md` **§4** — three lines were extracted
letter by letter (`p u r c h a s e d` in `S5.5.7`, `b o v i n e a n i m a l s` and `t h a n o n e`
in Appendix 6a), which search cannot match; and **§5** — Appendices **6a and 6b** lost the rows of
their tables (20 animal classes and 20 values, 5 attached and 15 piled at the end), which is the
Appendix 2 defect still live for the two appendices nobody curated, and is what **G4** means. Both
are reviewed-artefact work (D53), and §5's mechanism already exists: two new keys in `TABLE_ROWS`.

**The UAT is signed, and it closed three features.** `tests/uat/concordance_uat.md` carries eleven
**PASS** results, signed by **Kobus (Product) on 2026-10-28** against commit `4e02d71` and the dev
corpus (366 chunks, Xpdf 4.00), applied by `scripts/uat_signoff.py`. The export's environment says
`working_tree: modified` — the only dirty file at generation was the artefact itself; `uat_page.
environment()` now excludes it (`fix(uat)`), and the signed artefact is deliberately not regenerated
because it must keep naming `4e02d71`. That signature closes **CONCORDANCE** (D68),
**PASSAGE_LAYOUT** (Scenario 8) and **READER_STRUCTURE** (Scenarios 9–11); all six documents are in
`Done/`. **The PGS administrator, committee reviewer and consumer-member seats are still empty** —
the OPP wants three voices (D4) — and the file says so.

**Four follow-ups are filed, separately, because they are four different kinds of work** (the
product owner's 2026-10-28 reading session):

| Item | Where | Size |
|---|---|---|
| `/documents/` links to the concordance (four of eight have text) | `ready/DOCUMENTS_READER_LINK_PRD.md` | one task, decided |
| A wrapped clause renders as two paragraphs (25 of 319 chunks; `S23.3`) | `BugFixes/reader_clause_line_breaks.md` | one display rule + guards |
| The `SECTION B` banner at the end of **twelve** branches | `BugFixes/saoso_text_glyphs_and_boundaries.md` **§3, re-measured** | artefact/parser (D53) |
| Tables as reviewed data (JSON/MD) so any table can be displayed — absorbs **G4** | `Refinement/TABLES_AS_DATA_PRD.md`, four questions open | the big one |

**One defect shipped in this slice and was found by the product owner, not by the suite** — worth
reading before trusting a green gate on a layout change. Moving the missing-sections note out of the
phone `<details>` made it a **third child** of the two-column `.reader__body` grid: the passages
wrapped to the next row and the *sticky* tree sat on top of the text, so following a citation landed
on a page whose quoted line was behind the contents list. Markup valid, every string present, anchors
resolving, console clean, 1138 tests green, no 390 px overflow. Fixed by wrapping the tree and the
note in `.reader__tree-column` and moving the sticky rule there (the CSS comment had always said the
sticky box must be the grid item), and guarded by `tests/e2e/test_reader_layout.py` — three browser
assertions, proven by reverting the fix. **The e2e suite is outside `verify.sh`; run it whenever a
template or stylesheet changes** (`testing_hazards.md` §3.12).

---

## 0h. 2026-10-28 — SAOSO is a reviewed artefact, and three bugs the draft found

**This is the most recent slice, and it is not deployed.** Plan `CORPUS_CANONICAL_FORMAT_PLAN.md`
**P6** is done for SAOSO: `knowledge/corpus/saoso.md` is the text of record (271 sections, 71 page
markers, 3 reviewed edits in 1 537 blocks), and the ingest reads it —
`source=corpus`, **338 chunks, all embedded**. `uat_seed --check` expects **385** now
(SAOSO 338 + OPP 30 + BPP 9 + landscape 8). Gate green at **1160**; Playwright **60**.

- **What the artefact fixed** (`BugFixes/saoso_text_glyphs_and_boundaries.md` §2–§5a, all closed):
  the `m²` superscript no longer splits *Factory farming*; the `SECTION B` page banner no longer ends
  twelve branches with a part title and nothing after it; three letterspaced lines are words again;
  and Appendix 6a is **twenty reviewed rows** — *Laying hens → 230* — instead of twenty classes
  followed by twenty unrelated numbers.
- **The generator was the real defect, five times.** It sliced *every* page rather than the parser's
  body stream (so `Appendix 7` reproduced Section C three times); its `-raw` fallback parses this
  document to **zero sections**; a `ref:`-annotated heading carried its `#` into the text, so every
  clause rendered at heading weight *and* its wrapped continuation split off again; `heading_path`
  named the parent in one path and the section in the other; and a clause heading's slug overran
  `anchor`'s 128 characters, so the first ingest died with `value too long`. Each is fixed where it
  belonged, and `test_corpus_saoso.py` (20 guards) proves the two paths agree.
- **Appendix 6b is deliberately still open.** Three pages of species × live weight × indoor/outdoor
  measures, where `TableRow` (one substance, one condition cell) does not describe what the paper
  prints. Curating it means deciding what a row *is* — a product call, not a parser one (§8 there).
- **Evidence survived, and the tool to do it is new.** `manage.py relink_evidence --apply`
  (commit `a67ee5d`) rebuilds `ChatMessage.retrieved_chunks` from the `grounding` snapshot wherever
  the passage's text is unchanged. Both `--force` rebuilds in this session ran it: **57 links
  restored**, 30 left unlinked because a *previous* rebuild had genuinely rewritten those passages.
  `text_sha` now hashes a passage's **words**, not its layout — before that the artefact made
  **230 of 291** passages read as changed text and evidence stopped relinking.
- **The concordance UAT is signed 13/13 PASS** (`tests/uat/concordance_uat.md`, Kobus/Product,
  against `e6f4464`, 385 chunks): the eleven scenes of 2026-10-28 plus the clause case re-judged,
  Scenario 12 (the documents page offers the concordance) and Scenario 13 (Appendix 6a's stocking
  rates). Scenarios 8's clause case, 12 and 13 were judged at sign-off from the implementation and
  its guards, and their result lines say so — a hands-on pass is still owed before the P7.4 deploy.
  `DOCUMENTS_READER_LINK_PRD.md` moved to `Done/` on that sign-off.
- **`scripts/fast.sh` and `pgs.settings_test` are the other agent's session**, in the same tree:
  the two test lanes, the fast password hasher, and the `slow` marker. Not this slice's work, and not
  committed with it.

## 0. The one thing to know first

**The standards corpus, the public site and the grounded chatbot all exist.** `knowledge/`
is complete (four formats, TOC map, chunker, ingestion, hybrid retrieval scoped to a
`StandardSet`). The public site is built: **eight** routes, semantic CSS,
self-hosted type, the claim discipline that keeps it honest, and the eight published
documents behind `/documents/<code>/`. Sub-plan **D** now adds `/ask/`: a real form,
a citation audit that refuses on any invented reference, per-IP rate limiting, an answer
cache and an `EscalatedQuery` an administrator can answer. **C3 was deferred out of MVP 0
by the product owner (D44)** — no Afrikaans translator exists, so the AF pill stays a
disabled control and that is deliberate, not a regression.

**MVP 0's UAT is signed — by one of the three seats.** `tests/uat/mvp0_standards_and_public_site_uat.md`
now carries ten results: nine **PASS** and Scenario 5 **N/A** (D44), signed by the product
owner on 2026-10-21, with a recorded **decision to proceed** that names **G3** as an open
defect rather than absorbing it (**G8 is closed, below**). The PGS administrator, committee
reviewer and consumer member rows are still empty, so the OPP's three-voice requirement
(D4) is not met and that is stated in the file. `tests/uat/mvp1a_*` is still unsigned — 1a
is not built.

**The answer-coverage revision (D49–D51) is what makes the chat worth signing.** The
assistant embeds the visitor's *question*, reserves seats for the semantic arm, and may
answer with a **governing rule** when the document does not name the item (“The standard
does not name cardboard…”). Appendix 2 is **30 reviewed table rows**, so a substance and
its condition are one citable passage. The remaining gaps are G3, G4, G6 and G7
(`CHAT_ANSWER_COVERAGE_PRD.md` §7); **G1, G2 closed by D52**, **G8 closed by §21**.

**2026-10-22 — G8 is closed, and the reason was a budget nobody was reading.**
`settings.CHAT_RETRIEVAL_LIMIT` was **5**, not the 8 D49 recorded: the change landed on
`_chatbot.RETRIEVAL_LIMIT`, a `getattr` fallback `settings` always shadows, and
`probe_chat.py` hardcoded 8 — so the instrument measured a path the product did not have.
Cardboard (the question the budget was raised for) refused on the live site. One accessor
(`chat_retrieval_limit()`) and one path (`default_retrieval()`) now serve both the view and
the probe; the setting is 8 and `PROMPT_VERSION` is `d49-2`. Measured: cardboard refuses at
five and answers at eight, Scenario 1's question grounds **5/5** fresh runs with one
verbatim `S5.1.9` citation, suite **9/9** grounded. **No prompt rule changed** — G8's
refusal was the audit working, and rule 7 is unmeasured churn once the case is gone. Full
record: §21, `CHAT_ANSWER_COVERAGE_PRD.md` §7 G8, `testing_hazards.md` §2.7.

**Read `product/design/C1_BUILD_PLAN.md` before touching the site.** Its §3 is a
copy-provenance table — every published string names the OPP, SAOSO or LANDSCAPE passage
it came from — and its §6 lists **nine decisions still with the product owner**, each
currently shipping on a conservative default.

**Before your first commit, run the gate:**

```bash
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh
```

---

## 1. Read these first, in this order

| # | Artifact | Why | Time |
|---|---|---|---|
| 1 | `product/backlog/In Progress/MVP0_PLAN_V2.md` **Sub-plan D (D1–D5)** | What D built and the implementation notes that are not obvious from the code. Skim C3's struck-out task so you do not reopen it. | 20 min |
| 2 | `product/design/C1_BUILD_PLAN.md` | What C1 built, where every string came from, and the nine open decisions. | 20 min |
| 3 | `product/docs/context/testing_hazards.md` | **Read before writing any test.** Eighteen entries now; §1.13–§1.15 are from C2 (a data-driven route the sweeps silently skipped, a `logging` `extra=` collision, a URL segment that is not a slug) and **§2.4 is from D** — `websearch_to_tsquery` ANDs a natural question into zero results. | 20 min |
| 4 | `product/design/DESIGN.md` + `product/design/content_inventory.md` | The design of record, and the 16 live-site items a rebuild silently drops. | 25 min |
| 5 | `PGS_PLATFORM_SPEC.md` §4.5 (corpus), §12 (public surface), §18.3 (D40–D43) | The decisions C1 rests on. | 30 min |
| 6 | `product/docs/context/build_principles.md` | Thin views, service ownership, 30 KB cap, integer cents, zero build pipeline. | 10 min |
| 7 | `pgs_docs/` | The authoritative documents. Spot-check claims here, never against a plan or a prototype. | as needed |

Do **not** read `prd.md` as the spec (superseded provenance). Do **not** execute
`product/backlog/Done/MVP0_PLAN.md` (v1 — its SAOSO parser matched nothing).

---

## 2. What exists

| Subsystem | State | Evidence |
|---|---|---|
| **A — foundation** | Complete | custom `User` first migration, `/health/` with four independent checks, Celery retry policies, `lint-imports` contract, `verify.sh` |
| **B — corpus** | Complete | 340 chunks from 4 documents, 30 sections, **0 duplicate `section_ref`s**, **340/340 embedded** (D48, `lexical_only=False`), FTS + pgvector with RRF (k=60), scope before ranking; pages de-columned at ingest (D46) — 29 transformed, 4 documented exclusions |
| **C1 — public site** | **Accepted** (product owner, 2026-10-21; scenarios 4, 6, 8 PASS) | six routes, `root.css`/`site.css`/`components.css`/`chat.css`, self-hosted Lora + Mulish (C2 added the seventh route and 37 tests) |
| **C4 — claim discipline** | Complete | six forbidden terms, no seal rendered, no dead certificate link, no `Publishing soon` left anywhere; `test_nothing_is_pending_on_a_public_route` runs over all eight routes |
| **C2 — `/documents/`** | Complete | `PublicDocument` + `publish_documents` (idempotent on sha256), eight documents at `/documents/<code>/`, streamed through a view so `is_published` is per request; 379 + 30 tests |
| **C3 — bilingual shell** | **Deferred (D44)** | No Afrikaans translator. `LANGUAGES`/`LOCALE_PATHS`/`User.preferred_language` stay in place; no `LocaleMiddleware`, no catalogue; AF pill is `aria-disabled` — honest, and it must not become a link |
| **D — chatbot** | **Accepted with G8 open** (2026-10-21) | `/ask/`, `_chat.py` + migration 0004, `_chatbot.py` (refusal + citation audit + guardrails), vendored HTMX on that page only, 74 tests across `test_chat_models`/`test_chatbot_grounding`/`test_retrieval_scope`/`test_chatbot_guardrails`/`test_chatbot_surface` |

**The site's architecture, in one paragraph.** `core/services/_public.py` holds every
page's metadata, the nav table and the OPP fee schedule as integer cents;
`public_context(page)` is the only context any public view builds — plus
`documents_context()` on the two pages that carry the list; templates render and compute
nothing; the document list lives in `core/services/_documents.py` as *data*: `DOCUMENTS`
is the tuple the deploy copies, the rows render and the tests assert against; `pgs_extras.format_zar` is the only place money becomes a string. Section
partials carry **bodies**, and each page owns its own headings — a sub-page's `h1` and the
home page's summary of the same content must not share a tag level.

---

## 3. Gates

| Gate | Meaning |
|---|---|
| **A1–A5 migrated** | ✅ Passed. Custom `User` is the first migration |
| **`verify.sh` green** | ✅ **794 tests at HEAD** (788 + 4 probe-tooling + 2 budget tests, §21). Before any commit |
| **Playwright green** | ✅ 34 tests: eight routes, 390px, measured 44px targets, clean console, and a real download click. Outside the gate by design |
| **B3 needs a second reader** | ⚠️ **Not done.** The Crops template is 38 questions and 37 verdicts by hand |
| **0∥ spike complete** | ⚠️ **Not done.** Before `1∥` freezes `visitPack`/`VisitSyncEnvelope` |
| **A9's restore rehearsal, on the server** | ⚠️ **Not done.** The logged rehearsal was on the dev box; R11 requires it on the VPS |
| **C1 + C2 + D built** | ✅ Verified in code, in a browser and with screenshots. All ten MVP 0 scenarios carry a result (9 PASS · 1 N/A) |
| **UAT sign-off** | ✅ **Signed by the product owner, 2026-10-21** (9 PASS · 1 N/A, with the decision to proceed recorded in the file). ⚠️ The **PGS administrator, committee reviewer and consumer member** seats are unsigned — the OPP wants three voices (D4). ⚠️ `tests/uat/mvp1a_*` is unsigned |

---

## 4. Next steps, in order

1. ~~**Get the UAT signed.**~~ **Signed 2026-10-21** by the product owner, applied by
   `scripts/uat_signoff.py` (slice 1 of `UAT_SIGN_OFF_TOOLING_PRD.md`). The remaining two
   seats — PGS administrator, committee reviewer, consumer member — are a *human* step; the
   tooling is built and worked once.
2. **The deployed corpus and chat budget predate D52/D53 and §21.** `deploy.sh` never runs
   `ingest_standard`, so the box answers from pre-reflow text, and its `.env` may still pin
   `CHAT_RETRIEVAL_LIMIT=5`. Refresh the four documents once with `--force`, confirm **385**
   chunks (SAOSO is 338 since the artefact, §0h) and `lexical_only=False`, check the setting, and ask three questions through
   `/ask/`. `--force` must **not** enter `deploy.sh` (it destroys every
   `ChatMessage.retrieved_chunks` trail); `corpus_check`/`corpus_refresh` is the pending
   yes/no in `CORPUS_CANONICAL_FORMAT_PRD.md` §7 item 1.
3. ~~**Judge the answer-coverage work.**~~ Done with the sign-off on 2026-10-21; **G8 closed
   by measurement on 2026-10-22** (§21) — the question was a five-passage budget, not the
   prompt. The human question — whether *“the standard does not name cardboard”* reads as a
   rule or as permission — is recorded as PASS in Scenario 10.
3. ~~**Close the two refusal gaps (G1, G2)** — `S5.5.1` and `S4.1.1` enumerations cannot be
   quoted whole, so the ducks and seed questions refuse. Measure before changing the chunker
   or the prompt.~~ **Closed 2026-10-22 (D52)** — the cause was the extracted page, not the
   chunker or the prompt: a hyphenated word wrapped across a line break, plus the printed
   page footer inside the clause. Both questions are grounded; see §16. **G7** is the
   residual of the same class (a spanning BPP line) and is still open.
4. **Sibling-section retrieval for the cost question (G3)** — the answer omits the R100
   annual membership fee because §2.1 is never retrieved. Re-measured at the corrected
   budget on 2026-10-22: still open (five citations, none §2.1).
5. **Appendices 3, 4, 6a/6b and 7 (G4)** — same reviewed-row mechanism as Appendix 2, starting
   with Appendix 3 and Appendix 4 Table 1.
6. **The escalation answer path (G6)** — `Refinement/ESCALATION_ANSWER_PATH_PRD.md`. The
   refusal currently links to `/contact/`, whose contact details are placeholder chips.
7. **Then MVP 1a** (`ready/MVP1A_PRD.md`), gated on the 0∥ spike.

Queued behind those: UAT tooling slice 2 (`uat-setup` format + the `manage.py <command>`
existence lint that would have caught `mvp1a`'s `load_template`), and the OPP/SAOSO/landscape
artefact conversion (`CORPUS_CANONICAL_FORMAT_PRD.md`, which absorbs G4).

**G8 was the last chat blocker, and it is closed (§21).** The refusal was the audit doing its
job: the model cited one sentence twice, the second time as a paraphrase, and the
all-or-nothing audit refused the pair. What made it reproducible was a **budget nobody was
reading** — `settings.CHAT_RETRIEVAL_LIMIT` was 5 while the PRD, the constant's comment and
the probe all said 8 — so the failing `general-principles` citation was in the product's set
and not in the probe's. Cardboard refused on the live site for the same reason. The fix is
one accessor, one retrieval path and the setting at 8; **do not relax `audit_citations`**, and
do not "fix" a citation problem by trimming citations (D47).

**Do not add a classifier (G5).** It would not have fixed any 2026-10-21 failure. Reopen only
if a suite question retrieves the **wrong section**, and then prefer a seeded alias table to
an ungrounded model call.

**Two external constraints around D, both still real:**

* **Embeddings are live (D48, 2026-10-20).** `gemini-embedding-001` at 768 dims is ratified,
  and the four documents were force-re-ingested without `--no-embed`: **340/340 chunks carry
  a vector**, `search()` reports `lexical_only=False`. Enabling the arm exposed a retrieval
  interaction — the rare-word vector pushed Appendix 2 out of the top 8 — so the rare-term
  arm is now lexical-only and the vector arm runs once on the OR query (Appendix 2 back at
  #2, BPP at #4, one query embedding per question). `PROMPT_VERSION` is `d47-4` after two
  further prompt iterations. The manure question answers; so does the informal
  `can i use horse manure?` (six verbatim citations), after the BPP page-4 band override.
* **The refusal string is fixed by D17** and is now the shipped constant `REFUSAL` in
  `core/services/_chatbot.py`: *"I cannot find a definitive answer in the SAOSO standard or
  the Outeniqua PGS documents."* Not SAOSO-only: the OPP answers questions the standard does
  not (fees, joining). `test_the_refusal_is_the_d17_wording` keeps the exact string.

**Corpus column defect closed (2026-10-20, D46).** The four governed documents are
de-columned at ingest by `knowledge/columns.py`; SAOSO re-ingests to 293 chunks (was 298),
OPP 30, BPP 9, landscape 8 — **340** in total, and the answer cache invalidated itself via
`_corpus_fingerprint()`. The BPP manure sentence and the SAOSO Appendix 2 condition are now
contiguous in one stored chunk, and the verbatim sentence is accepted by `audit_citations`
while the recorded paraphrase is still refused. Four pages are asserted exclusions with
reasons in `PAGE_LAYOUT_EXCLUSIONS`: SAOSO PDF 2 (TOC — its page-number column is the
content), SAOSO PDF 82–83 (Appendix 4 Table 1 — 4-column rows already coherent), OPP PDF
11 (§6.5 — 3-column table). **UAT Scenario 9 is unsigned.** Two live manure turns on
2026-10-20 were refused for model-side reasons, not corpus corruption: one fabricated a
`sub_ref` from a heading, the other elided a quote with `…`. Both are filed in
`product/backlog/todo.md` as a prompt/model follow-up; the audit is right to refuse them.

**Done since the last handover (D, 2026-10-19).** `/ask/` and the D1–D5 contract: chat
models + migration `0004`; `answer_question()` with the all-or-nothing citation audit;
per-IP fixed-window rate limiting, the 500-char cap, the history window, the answer cache
and token accounting; a vendored HTMX surface that still works as a plain form POST. Two
retrieval facts had to be fixed to make it answer real questions: `websearch_to_tsquery`
ANDs a natural question into zero results, and a common word ("standard") outranks the rare
word that carries the question — `significant_terms` + `search_terms` solve both. See the
plan's “Built 2026-10-19” notes and `testing_hazards.md` §2.4.

**Deferred, do not reopen without the product owner: C3.** The product owner deferred the
bilingual shell on 2026-10-19 (decision **D44**). The AF control stays `aria-disabled` and
must not become a link that reloads the same English page; UAT Scenario 5 is *not
applicable*, not failed. `build_principles.md` §IV is therefore unmet for MVP 0 — every
string added in D is a retrofit when C3 is eventually picked up.

**C2, earlier on 2026-10-19.** `PublicDocument` +
`publish_documents` (idempotent on sha256, wired into `deploy.sh`), eight documents at
`/documents/<code>/` served through a view so `is_published` is checked per request and a
missing file answers 503 rather than 404. The home page's eight `Publishing soon` chips,
the header's fifth nav link and the footer's Documents column all landed in one commit.
Two corrections are recorded in the plan rather than hidden: the list is **eight**, not
the plan's "seven" (D22's enumeration was miscounted), and the model went to
`core/models/_public.py` rather than `_core.py`, which is identity.

**Still open from C2:** the `"SOP's"` question (§6 #6) is answered *by assumption* — if it
turns out to be a separate document, the ninth is one more tuple entry and one more PDF in
`pgs_docs/`, with no migration. The workbook stays unpublished until the committee says
otherwise (D22).

**The chatbot's own open items:** D's UAT is unsigned; retrieval ranking is still open
(Appendix 6b ranks first for "horse", before the rare-term merge); and `PROMPT_VERSION`
in `_chatbot.py` must be bumped whenever the prompt or retrieval changes, or Redis will
serve an answer produced under the old contract. The `/ask/` page is now in the header
nav — six links plus the CTA, added 2026-10-20 — and is still linked from the home
showcase and the footer.

---

## 5. Traps that will bite

> **Extended, not duplicated.** Every trap found while building A, B, C1, C2 and D — Django
> mutating settings under test, Celery's absent `autoretry_for`, an import-linter config
> that enforced nothing, a `GeneratedField` that had to be proven, **a multi-line `{# #}`
> template comment that is emitted as text and parsed as HTML**, **a media query placed
> above the rule it refines**, **an e2e suite that errors in fixture setup**, **a
> `--noreload` server serving stale templates**, **a port owned by another project**, and
> **a natural question that FTS silently matches nothing** — is recorded with evidence in
> `product/docs/context/testing_hazards.md`. **Read it before writing tests, and append the
> moment you lose time to something that will recur.**

1. **The polarity trap (R1a-2).** `V16` "risks of contamination of the water source?"
   answered *Yes* is **non-compliant**. `V3` is `INFORMATIONAL`; `V23` and Animal `V14` are
   `NEGATIVE`.
2. **An appendix is one section, deliberately.** Appendix 1 holds two lists that both start
   at `1.`. Evidence in `knowledge/sections/saoso.py`.
3. **`page` is the printed footer number, not the PDF index** (D42). The BPP prints none;
   `page` is NULL and the `anchor` is the only locator.
4. **`OVERDUE` is derived from `due_on`, never stored.**
5. **Never `except: pass`.** Sentry on every exception path, explicit `timeout=` on every
   external call.
6. **Fixtures are evidence.** Nine of them, extracted by `scripts/extract_fixtures.py`.
   Re-run the script rather than editing them.
7. **No fee figure, page title or route may be typed into a template.** They live in
   `core/services/_public.py`; tests fail the build otherwise. The same rule covers the
   chatbot showcase's own answer.
8. **Documents are served through a view, never from `/media/`.** `is_published` is
   checked on every request, so a document withdrawn in the admin stops downloading for
   the person who bookmarked it — and `DEBUG=True` cannot serve a file the database says
   is private. A published row whose file is missing answers **503**, not 404: the
   document exists, the deployment is wrong.
9. **A retired chip is not a finished feature.** C2's chips became real links in one
   commit, and `test_nothing_is_pending_on_a_public_route` now asserts *no* `Publishing
   soon` survives on any route. If anything is ever pending again, DESIGN rule 8 still
   applies: a tinted chip, never a link to nowhere.
10. **The live WordPress site is the content baseline, not the design reference.** It
    publishes `pasture raised` and `GMO free` today — the exact claims
    `test_claim_discipline.py` forbids.
11. **Never pipe a schema-changing command into `head`.** Never trust a screenshot until you
    have confirmed which server answered it.
12. **A natural question is not a search phrase.** `websearch_to_tsquery` ANDs it into zero
    results (`testing_hazards.md` §2.4). `build_retrieval_query` strips function words and
    `search_terms` searches the rarest term first; do not "simplify" either back to one
    query without running a real question through `/ask/`.
13. **Bump `PROMPT_VERSION` when the prompt or retrieval changes.** The answer cache is
    keyed on it; without a bump, a cached answer produced under the old contract is served
    as though nothing changed.
14. **A model's citation is a claim, not evidence.** Every section ref, sub-ref and quote
    is audited against the retrieved chunk; anything that cannot be checked refuses the
    whole answer. Do not trim a bad citation and keep the rest.

---

## 6. Open — not yours to resolve

**Content decisions for C1 (all currently on defaults; `C1_BUILD_PLAN.md` §6 has the
detail):**

| # | Decision | Shipping default |
|---|---|---|
| 1 | Contact details — the administrator's email and two cell numbers are on the live site | **Withheld**; visible `email`/`phone` chips |
| 2 | Bank details (`NU HORUS NPO`, ABSA, `9288670349`) | **Withheld**; a `bank details to confirm` chip |
| 3 | News in the nav | **Not present** |
| 4 | `/endorsed-farms/` has no honest MVP 0 target | **Not present** |
| 5 | Pledge downloads (farmer + consumer) | **Not present** |
| 6 | Is `"SOP's"` the OPP under another name? | **Assumed yes** — that assumption is what makes the list **eight**. If it is a separate document, C2's ninth is one tuple entry and one PDF, no migration |
| 7 | ~~"Fees payable by end of February"~~ — **not in the OPP** | ✅ **Resolved 2026-10-19: withheld.** Removed from `/become-a-member/`; `test_no_unsourced_claim` guards it |
| 8 | Photography consent for four group photographs | **Published** with a consent chip |
| 9 | Six-elements wording: LANDSCAPE verbatim vs the prototype's paraphrase | **Verbatim** |

**Blocked on someone else:**

| Item | Blocked on | Affects |
|---|---|---|
| **An Afrikaans translator** (C3, deferred as D44) | The group | MVP 0 ships English-only. Every string added from here is a retrofit |
| ~~Ratify the embedding default~~ | ✅ **Resolved 2026-10-20 (D48)** — `gemini-embedding-001` @ 768; 340/340 chunks embedded, vector arm live | — |
| **D31 — which land-history periods govern** (12/12/18 vs OPP §V 18/12/12) | **The group** | MVP 2 seal issuance |
| **POPIA consent** for ~31 consumer names, 13 farmer members and four photographs | **The group** | MVP 2 registry; blocks publishing any member list |
| **UAT sign-off seats** (administrator, committee reviewer, consumer member) | **The human** | C1 and 1a acceptance |
| **A reversed logo lockup, an SVG of the mark, a real favicon** | The designer | C1 polish; `logo_mark.png` is a stand-in favicon |
| Seal cardinality; `standard_ref` coverage for ~91 verdicts; hosting cutover; A9's rehearsal on the VPS | MVP 2 / authoring effort | later slices |
| **Push to `origin`?** | The product owner | every commit exists only on this machine |

---

## 7. Untracked files in the tree

**The tree is not clean, and that matters more than any single file.** Uncommitted work
now includes the whole of sub-plan D (`core/services/_chatbot.py`, the chatbot models and
migration 0004, templates, six test files), the column-transform work
(`knowledge/columns.py`, `tests/test_columns.py`, regenerated fixtures), the 2026-10-21
answer-coverage work (`knowledge/tables.py`, `tests/test_tables.py`, `scripts/probe_chat.py`),
and edits to the spec, backlog, handover and UAT. **Commit it before handing off** — the next
agent cannot tell your work from theirs in `git status`.

`Homtini Assessment Report 22.10.03.docx.pdf` is still in the repo root, but it is now
**gitignored** (`.gitignore:25`), so it can no longer be committed by accident. That item is
closed; the file itself is the owner's to delete.

`product/design/f1_restack_fund_fit.html`, the F1/NLnet ReStack explainer, is now tracked;
it is a review artifact, not product code.

---

## 8. Commands

```bash
# The gate. Run before every commit.
DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key as k; print(k())") \
DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh

# Browser tests (outside the gate; needs `playwright install chromium` once).
python -m pytest tests/e2e -q

python manage.py check
.venv/Scripts/lint-imports.exe --no-cache --no-logo     # Windows; plain `lint-imports` on Linux
.venv/Scripts/python.exe -m pytest -q
python -m pytest core/tests/test_public.py -k fees      # any single slice

docker compose up -d            # Postgres+pgvector (host port 5433) and Redis. App runs natively (D19)
python manage.py migrate
python manage.py seed_deployment           # idempotent; creates the StandardSet and the seals
python manage.py publish_documents         # idempotent (sha256); copies the 8 PDFs into
                                           # media/public/documents/ and upserts the rows.
                                           # Runs in deploy.sh beside seed_deployment — skip it
                                           # and /documents/ links to eight 503s.
python manage.py runserver                 # DEBUG defaults to False — see the note below

# Corpus (the four governed documents, D16)
# SAOSO and the BPP read a REVIEWED ARTEFACT (D53): the text of record is
# knowledge/corpus/<doc>.md, and the PDF is hashed only to prove the artefact is still the
# text of that file. `--from-corpus` is what selects it; without it the PDF is re-parsed
# by layout heuristics, which is the path D53 replaced.
python manage.py ingest_standard --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf \
    --from-corpus knowledge/corpus/saoso.md
python manage.py ingest_standard --doc bpp --file "pgs_docs/Basic Production Principles_ENG_PRINT.pdf" \
    --from-corpus knowledge/corpus/bpp.md
# (…) opp, landscape have no artefact yet — see MVP0_PLAN_V2 §6. Re-running is a no-op:
# ingestion is idempotent on sha256. Drop --no-embed only if you are intentionally
# re-embedding; the 2026-10-28 corpus is embedded (338/30/9/8 = 385).

# Regenerate an artefact after a reprint. The generator drafts it, applies the reviewed
# edits from CORPUS_EDITS (knowledge/corpus.py), and refuses to rewrite a file without
# --force because a human reviewed it. The diff IS the review queue.
python scripts/build_corpus.py --doc saoso --stdout > /tmp/draft.md   # look before writing
python scripts/build_corpus.py --doc saoso --force                    # overwrite the artefact
# SAOSO needs no `-raw` fallback (one double-spaced column: the fallback parses to zero
# sections) and the generator defaults it off for that document (RAW_FALLBACK_OFF).

# After a corpus change that does NOT touch the PDF (a reviewed table, a parser fix), the
# sha256 guard makes a plain re-run a no-op. Use --force once, deliberately: it deletes the
# old document (and the old chunks' retrieved_chunks links) inside the transaction, after
# embedding. This is what the 2026-10-21 Appendix 2 rows required.
python manage.py ingest_standard --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf --force

# Then put the evidence links back. The grounding snapshot (P2.5a) records what every
# answer stood on, so `relink_evidence` restores the retrieved_chunks rows for every
# passage whose text the rebuild did not change, and names the ones it cannot ("same
# locator, different text" is deliberate: a link that resolves to different words is a
# citation that lies). No --apply, no writes.
python manage.py relink_evidence             # what would be restored, and what cannot be
python manage.py relink_evidence --apply     # restore them

# What did the assistant actually retrieve and answer? Read-only, writes no rows, needs a
# key and a corpus. Prints terms, document frequency, the passages with the arm that found
# them, the raw and audited citations. `--chunks-only` skips the model call.
python scripts/probe_chat.py                      # the fixed measurement suite
python scripts/probe_chat.py "can I use straw?"   # one question
python scripts/probe_chat.py --chunks-only        # retrieval only

python scripts/extract_fixtures.py         # regenerate the 9 fixtures (deterministic)
BACKUP_DIR=/tmp/drive scripts/backup.sh    # then: scripts/restore.sh /tmp/drive/db-<stamp>

python product/backlog.py                  # dry-run: drift + suggested moves
python product/backlog.py --write          # regenerate the index only
python product/backlog.py --apply          # move files to match Status: + regenerate
```

**Dev database state:** seeded, ingested and published — 1 `StandardSet`, 4 documents, 340
chunks (SAOSO 293, OPP 30, BPP 9, landscape 8), **all 340 carrying a `gemini-embedding-001`
vector at 768 dims** (D48), 8 `PublicDocument` rows with their files in
`media/public/documents/`. Retrieval reports `lexical_only=False`. Re-ingesting required
deleting the four `StandardDocument` rows first: `ingest_standard` is idempotent on sha256, so
a re-run is otherwise a no-op that leaves the old chunks in place. Migration `core.0004` has been
applied, so the three chat tables exist; a few local sessions were created while verifying
`/ask/` and can be cleared with `ChatSession.objects.all().delete()`.

**Chat configuration** lives in `.env.example` under “Grounded chat”: `CHAT_MODEL`,
`CHAT_TIMEOUT_MS`, `CHAT_RATE_LIMIT`, `CHAT_RATE_LIMIT_WINDOW_SECONDS`,
`CHAT_MAX_QUESTION_CHARS`, `CHAT_HISTORY_MESSAGES`, `CHAT_RETRIEVAL_LIMIT` and
`CHAT_ANSWER_CACHE_TTL`. `GEMINI_API_KEY` is the same key the embedding path uses; with no
key, `/ask/` answers **503**, never a canned answer.

**Windows specifics:** `bash` is git bash; `rsync` is absent (backup falls back to `tar`);
`lint-imports` is not on `PATH` under `python -m pytest`. Throwaway scripts belong in
`_scratch/` (git-ignored) — a stray `inspect.py` in `%TEMP%` shadows the stdlib.

**Two gotchas that cost real time this session, now in `testing_hazards.md` §3.8–§3.9:**
`runserver --noreload` with `DEBUG=False` serves **cached templates as well as stale
modules**, so run visual checks with `DJANGO_DEBUG=1`; and a port can belong to another
project, so assert a string from *your* page before believing a screenshot.

---

## 9. What the C1 session did

1. **C1a** — `root.css` (15 `brand-*` tokens, type scale, layout primitives),
   self-hosted Lora + Mulish as variable woff2, base template, header and footer, all six
   routes. Tailwind is out (D40), so the design became semantic CSS.
2. **C1b** — the home page's nine bands; fees as integer cents from OPP §2.1/§2.3 through
   `format_zar`, so no template can hold a figure; `Publishing soon` chips instead of dead
   links; a zero-JS mobile menu the prototype never had.
3. **C1c** — the five deep pages: four IFOAM principles (SAOSO §2.1–2.4), six basic
   elements (LANDSCAPE verbatim), first/second/third-party trust, the visit committee
   (OPP §3.3), the four outcomes, three member categories, fee conditions (OPP §2.2/§2.3),
   committee roles (OPP §3.1). **No member names** — POPIA.
4. **C4** — claim discipline on every route, each guard mutation-tested.
5. **C1e** — Playwright: six routes, 390px overflow, measured 44px targets, clean console.
6. **Close-out** — `C1_BUILD_PLAN.md` written and statused, `HANDOVER.md` rewritten, six new
   hazard entries, the plan's and PRD's stale `Status:` lines corrected, backlog index
   regenerated.

**The one thing to carry forward:** every defect found in these two sessions was found by
*running the thing* — the real PDFs, a mutation, a query, a browser — and none was visible
in review. Three C1 defects were found by looking at a rendered page. The plan's own code
snippets were wrong four times, and the design prototype's own rules were wrong twice.

---

## 10. What the C2 session did (2026-10-19, later the same day)

1. **Withheld the February fee deadline** — the first thing asked for, and a product
   decision, not a code one: `pdftotext -layout` over the whole OPP contains no month name,
   so the live site's "payable by end of February" was unsourced. Removed; guarded by
   `test_no_unsourced_claim` over all routes, mutation-tested.
2. **C2** — `PublicDocument` (`core/models/_public.py`), `publish_documents`
   (`core/services/_documents.py`) idempotent on sha256, `core/views/_documents.py`
   streaming `/documents/<code>/`, the `/documents/` page, and the home band + header nav +
   footer column rewired in the same commit. `deploy.sh` runs the command.
3. **Playwright** — the seventh route, plus a fixture that publishes the documents (without
   it the suite measured an empty list) and a test that asserts eight download links exist
   so a broken fixture cannot pass as a working page.
4. **Three new hazards** (§1.13–§1.15) and a corrected test elsewhere: C4's sweep was
   silently skipping the new data-driven route, and `test_pending_documents_are_not_links`
   became `test_nothing_is_pending_on_a_public_route`.
5. **Two plan corrections, recorded rather than hidden:** the list is **eight**, not
   "seven" (D22's enumeration was miscounted in three documents), and `PublicDocument`
   belongs in `_public.py`, not `_core.py` as the plan said.

**What the tests could not see, again:** the `logging` `extra={"created": …}` collision, the
octet-stream and rewrite-every-deploy mutations on their first attempt, and the empty-rows
sweep would all have shipped green. Two of the document guards had to be re-broken properly
before their mutation failed.

---

## 11. Session close — the deferral (2026-10-19)

Two product-owner decisions were taken and recorded, not absorbed:

1. **`"Fees payable by end of February"` withheld** — commit `edda927`. The live site's
   claim, absent from the OPP; `test_no_unsourced_claim` refuses it on every route.
2. **C3 deferred out of MVP 0** — `PGS_PLATFORM_SPEC.md` **D44**, `MVP0_PLAN_V2.md` C3
   struck with the reason, UAT Scenario 5 marked *not applicable*, the AF control left
   `aria-disabled`. No Afrikaans translator; a machine translation would pass every test
   except the one about honesty.

**State at the C2 close (historical; D has since landed — see §12):** 50 commits (plus this
one), tree clean apart from the two untracked files in §7, `verify.sh` green at **387**,
Playwright **30**. That session closed with MVP 0 one sub-plan from done; D is now built,
and only its UAT is outstanding.


---

## 12. What the D session did (2026-10-19, later again)

1. **D1 — models.** `core/models/_chat.py` + migration `0004`: `ChatSession` pinned to a
   `StandardSet` and keyed by `public_uuid`, `ChatMessage` with cost and retrieved evidence,
   `EscalatedQuery` with `OPEN`/`ANSWERED`/`CLOSED`. Anonymous sessions are first-class;
   `attach_user()` graduates a visitor without starting a new conversation.
2. **D2 — `answer_question()`.** The exact D17 refusal; a refusal is written for the model's
   flag, empty citations, an invalid citation, an empty answer or no retrieved chunks.
   `UpstreamModelError` propagates — the view says “unavailable” and never guesses.
3. **D3 — the citation audit.** Every `section_ref`/`anchor` must be in the retrieved set,
   every `sub_ref` in the chunk's offset map (a bare item number is resolved only when
   unambiguous), every quote a whitespace-normalised substring. One failure refuses all.
4. **D4 — guardrails.** Fixed-window per-IP limit (429), 500-char cap, bounded history,
   answer cache keyed on a normalised question and `PROMPT_VERSION`, token accounting.
5. **D5 — the surface.** `/ask/` with a plain form POST and an HTMX fragment path; HTMX
   2.0.4 vendored and loaded only there; citations open to show the quote and source; the
   refusal offers `/contact/`. The home showcase and the footer link to it.
6. **Two retrieval corrections, both found by running a real question.** `websearch_to_tsquery`
   ANDs the words and returned **zero** chunks for “What does the standard say about
   traceability?”; a plain OR let “standard” outrank “traceability”. `significant_terms()` +
   `search_terms()` search the rarest term first, then the OR fallback. Without this the
   chatbot would have refused every real question while the phrase-shaped suite was green.
7. **Hazards added:** `testing_hazards.md` §2.4. Plan implementation notes added to
   `MVP0_PLAN_V2.md`; UAT table and Scenario 1 setup corrected to `/ask/` and D17.
8. **Tests:** 65 chat tests (465 total), Playwright 34. `verify.sh`, `manage.py check` and
   `lint-imports` green. The browser was used to verify a real grounded answer, a citation
   opening, the 429/503 notices, the phone scroll position and the no-JavaScript POST.
9. **Explainer artifact:** `product/design/d5_chat_interface_explainer.html` is a
   self-contained walkthrough of the pipeline, the stops, and the session/history model. No
   CDN, no external font, no network; it opens from the filesystem and has a local-notes box.

**What the tests still cannot see:** whether a citation that resolves is *topically* the
right passage. The first live answer on 2026-10-19 cited a landscape paragraph for a
question about the standard's traceability requirement; the prompt now prefers governing
documents, but only UAT Scenario 2 can judge whether that is enough.


---

## 13. What the corpus-column session did (2026-10-20)

The PRD is `product/backlog/ready/CORPUS_COLUMN_EXTRACTION_PRD.md` and the plan beside it;
both were moved to `In Progress/` (build complete, UAT unsigned) by this session.

1. **`knowledge/columns.py`** (new, pure, no Django): `column_bands()` detects vertical
   whitespace bands by coverage (≥0.70, ≥6 crossing lines, ≥12% of characters on each side);
   `de_column()` re-emits a page column 1 top-to-bottom, then column 2, never cutting a
   line that has text across the band; no band returns the *same object*.
   `de_column(bands=…)` is kept for tests and a future per-page override.
2. **`apply_layout(pages, doc_key=…)`** is the pipeline entry point: it consults
   `PAGE_LAYOUT_EXCLUSIONS` (data, not a `layout` flag) and returns the transformed pages
   plus the 1-based **PDF** page numbers that changed. 33 pages are detected; 29 are
   transformed; the four exclusions are SAOSO PDF 2, 82, 83 and OPP PDF 11.
3. **Ingest wiring.** `ingest_standard` applies the transform between `extract_pages()` and
   the parser, and `IngestReport.layout_pages` reports what it touched; the management
   command prints `N layout pages`. A standard ingested with explicit metadata and no
   `doc_key` gets generic detection — no special case, no migration (D16).
4. **`heading.py::_page_stamp` rescued.** It read the *last* non-blank line, which the
   reordering moves to the middle of a landscape page, silently nulling every landscape
   `page`. It now searches anywhere for the last bare-number line. Measured page sets:
   SAOSO/OPP unchanged, BPP `[None, None, None, 10]`, landscape `[4, 4, 6, 7, 7, 9]`.
5. **Fixtures** are produced by the same pipeline (`pdftotext -layout` then
   `apply_layout`) and the manifest records `pipeline`, `layout_pages` and per-page
   **pre-transform** hashes. Regenerating changed exactly `bpp_intro`, `landscape_seals`,
   `opp_4_1` and `MANIFEST.json`; `saoso_toc` came out byte-identical because PDF 2 is
   excluded — the negative control.
6. **Tests added:** `knowledge/tests/test_columns.py` (21), ingest layout tests,
   parser page-attribution pins, and two audit tests in
   `core/tests/test_chatbot_grounding.py` (verbatim accepted, recorded paraphrase
   refused). Full gate: **526 passed**, `lint-imports` kept. Each guard was also observed
   failing by disabling the transform.
7. **D47 (2026-10-20) — the model-side citation contract.** The product owner chose option A:
   `SYSTEM_PROMPT` now requires a character-for-character quote (no paraphrase, no ellipsis),
   and `build_prompt()` tells the model to omit `sub_ref` unless the passage lists that exact
   sub-clause (`none — omit sub_ref for this passage` when it has none). `PROMPT_VERSION` is
   `d47-4` after the retrieval fix and the later prompt iterations in §14, invalidating the
   cache; the audit was not changed. **Verified live 2026-10-20:**
   the manure question returned a grounded answer with three Appendix 2 citations, all
   verbatim and all with `sub_ref=None`. The run cited no BPP passage (it preferred the more
   specific Appendix 2 conditions), so UAT Scenario 9's "at least one BPP citation" sub-check
   is still a human judgement, not a corpus defect.
8. **What is *not* done:** UAT Scenario 9 is unsigned (the BPP-citation sub-check is the open
   part). Table row association is still not reconstructed; the two excluded Appendix 4
   Table 1 pages and OPP §6.5 need a multi-gutter treatment.


---

## 14. What the embedding session did (2026-10-20)

1. **D48 ratified** by the product owner: `gemini-embedding-001` at 768 dims. One live call
   validated the model and the width before anything was deleted.
2. **Forced re-ingest with embeddings.** The four `StandardDocument` rows were deleted (a
   plain re-ingest is a no-op on sha256), then ingested without `--no-embed`: SAOSO 293, OPP
   30, BPP 9, landscape 8 — **340/340 embedded**, `embedded=True` in every report.
3. **A retrieval regression, found by running the question.** With the vector arm on,
   `search_terms` embedded the rare word *and* the OR query. The rare-word vector retrieved
   S5/Appendix 6b and pushed SAOSO Appendix 2 out of the top 8, so the manure question refused
   again. Fixed structurally: the rare-term arm is lexical-only, the vector arm runs once on
   the OR query. Appendix 2 returns at #2 and BPP at #4, and a question now spends **one**
   query embedding instead of two. Tests: `use_vector=False` spends no call; `search_terms`
   makes exactly one embedding call, on the OR query.
4. **`PROMPT_VERSION` moved to `d47-4`**: `d47-2` for the retrieval change, then `d47-3`
   and `d47-4` after two more live refusals on `can i use horse manure?`. The model stitched
   quotes with `...`, then without an ellipsis across two numbered passages; the contract now
   says one citation = one contiguous excerpt from one numbered passage, with a separate
   citation per excerpt. The schema description says the same. The audit was never changed.
5. **Live result (long question):** grounded answer, two verbatim Appendix 2 citations,
   `sub_ref=None`, under `d47-2`. No BPP citation in that run (BPP was retrieved at #4; the
   model preferred Appendix 2's conditions).
6. **A second corpus split, on the same page.** The short question exposed that BPP PDF 4's
   default band `(38, 42)` started inside the left list item `a. Sustainable land management2 ?`,
   so rule 2 kept that line whole and the right column's `harvesting a crop…` was stranded:
   the raw-manure 60-day rule was not contiguous. A measured override — `PAGE_LAYOUT_BANDS`
   `bpp: {4: [(40, 42)]}` — makes it contiguous, and also `the addition of animal manure
   (composted)`. Pinned by two tests in `knowledge/tests/test_columns.py`; both fail if the
   override is removed. BPP was re-ingested with embeddings (9 chunks, `embedded=True`).
7. **Live result (short question):** `can i use horse manure?` now answers with six verbatim
   citations (`Appendix 2` × 5, `S1`), no `sub_ref`. Still no BPP citation in that run.
8. **Composer (same session).** Enter sends, Shift+Enter inserts a newline, and the hint
   under the textarea says so. It clicks the real Ask button, so required-field validation
   and HTMX's submit interception still apply; an in-flight request is not duplicated. The
   composer is also **optimistic**: `htmx:beforeRequest` appends the visitor's bubble and
   clears the box after the form has been serialised, so the turn appears immediately. The
   response no longer resets the form, so a question typed during the wait survives; a 429
   puts the text back, and a network failure removes the optimistic bubble and restores it.
   Verified by `tests/e2e/test_chat_composer.py` (four browser tests, POST held so no Gemini
   call).
9. **Still open:** UAT Scenario 9's BPP sub-check and human sign-off; the broader retrieval
   ranking defect (Appendix 6b still ranks #1 for "horse" before the rare-term merge).

---

## 15. What the answer-coverage session did (2026-10-21)

**The question that started it:** *"Can I use cardboard from my neighbours?"* refused, while
SAOSO 4.4.4 (material applied to land must comply with Appendix 2) sat in the corpus.
Reproduced against the shipped corpus, not guessed: retrieval gave the model S2.4, S23.9
(child labour), Appendix 1 ×2 and the BPP general principles. `cardboard` has document
frequency 0, so `search_terms` dropped it and searched the rarest *known* word,
`neighbours`.

1. **D49 — retrieval embeds the question.** `search(vector_query=)`; `SEMANTIC_SEATS = 3`;
   an out-of-vocabulary term caps the lexical proxy at two chunks and gives the semantic arm
   the rest; chat `RETRIEVAL_LIMIT` 5 → 8. Measured: embedding the sentence puts 4.4.4 at
   rank 6; the OR string does not retrieve it.
2. **D50 — the governing-rule answer mode.** Rule 4 answers with the rule that governs an
   unnamed item, says plainly that the document does not name it, and forbids inferring
   permission from silence. `PROMPT_VERSION` `d49-1`. D17's refusal string is unchanged.
3. **D51 — Appendix 2 as 30 reviewed rows.** `pdftotext -table` aligns the table's rows
   where `-layout` cannot (rows overflow the gutter). `knowledge/tables.py` holds the cells
   and the measured `TABLE_BANDS`; ingest substitutes one chunk per row.
   `ingest_standard(force=True)` / `--force` re-ingests unchanged bytes, deleting inside the
   transaction after embedding. Assumptions are in the module docstring and the PRD.
4. **Round 3 (live, after a forced re-ingest: 321 SAOSO chunks, embedded).** Cardboard,
   straw, borax and manure grounded; straw no longer says it must be untreated; borax quotes
   the trace-elements row. **Still refused:** ducks/bedding compost (`S5.5.1`) and seed grown
   organic (`S4.1.1`) — the enumerations cannot be quoted whole. **Still missing:** the R100
   annual membership fee in the cost answer (§2.1 not retrieved).
5. **Diagnosis worth keeping.** I first assumed the Appendix 2 chunks were stale. They were
   not: rebuilding every chunk in memory found 0 of 340 different. The pipeline really does
   produce the interleaved text. `testing_hazards.md` §1.24 records the rule — diff the
   stored rows against the pipeline before proposing a re-ingest.
6. **Gate:** 619 tests green, `lint-imports` kept. `scripts/probe_chat.py` is the measuring
   instrument for the next round: read-only, writes no rows, prints the passages, the raw
   quotes and the audit verdict.

---

## 16. What the refusal-gap session did (2026-10-22)

**The two refusals the last handover queued as G1/G2 were not model failures — they were
the extracted page.** That is the whole finding, and it is the same lesson as D46, D47 and
`testing_hazards.md` §1.24: measure the corpus before touching the chunker or the prompt.

1. **Reproduced both, then read the stored text.** The ducks question refused with
   `S5.5.1: the quote is not in the cited chunk` and `sub_ref 'a' does not exist in the
   chunk`; the seed question refused with `S4.1.1: the quote is not in the cited chunk`.
   The chunk text was
   `… 15% dry matter per non-` / `P a g e | 47` / `ruminant calculated …` — i.e.
   `pdftotext -layout` broke a line inside `non-ruminant` and the printed page footer was
   not furniture, so it landed *inside* a clause that continues onto the next page.
   `post-harvest` in `S4.1.1` had the same line-break defect. No quote of either printed
   sentence could be a whitespace-normalised substring, so the model elided with `...` and
   the audit — correctly — refused.
2. **`knowledge/reflow.py` (D52).** A line ending in letter-hyphen is rejoined with the next
   non-blank line when that line starts lowercase, **keeping the printed hyphen**; blank
   lines are crossed because SAOSO prints double-spaced. It runs after `de_column` (line
   adjacency is reading adjacency only then) and before the parser, in `ingest_standard`
   **and** in `scripts/extract_fixtures.py` (manifest pipeline is now
   `pdftotext -layout + de_column + reflow v2`, with `reflow_pages` recorded separately from
   `layout_pages`). Measured on the four governed documents: **20 joins** (SAOSO 12, OPP 4,
   BPP 3, landscape 1), every one a genuine compound, and **no page ends inside such a
   word** — which is why a per-page pass is complete.
3. **`PAGE_FOOTER` is now furniture.** `is_furniture()` already dropped the registration and
   contact block; the `P a g e | 47` line was not included, so **65 of 368 chunks** carried
   one. `page_number()` still reads the footer from the page *before* any line is
   classified, so no section lost its page.
4. **Re-ingested all four with `--force`** (the sha256 guard makes a corpus change
   unreachable otherwise): SAOSO 319, OPP 30, BPP 9, landscape 8 = **366 chunks, 366
   embedded**. `report.reflow_pages` prints `N reflow pages` beside `N layout pages`.
5. **Measured result, `scripts/probe_chat.py`, no prompt change and no audit relaxation:**
   - ducks / bedding compost → **grounded**, 4 citations (S5.5.1, Appendix 2 ×2), no
     `sub_ref`;
   - seed grown organic → **grounded**, 2 citations (S4.1.1, S4.1), the paragraph quoted
     verbatim.
   `PROMPT_VERSION` stays `d49-1`: the answer cache already keys on
   `_corpus_fingerprint()`, which moved when the chunks did.
6. **Tests: 652 green** (was 619), `lint-imports` kept. New:
   `knowledge/tests/test_reflow.py` (20 — synthetic contract, pinned per-document join
   counts, the "no wrap crosses a page" measurement, and the two live sentences quotable
   from one chunk), three furniture/parser tests in `test_section_parsers.py`, seven ingest
   tests in `test_ingest.py`, and three in `core/tests/test_chatbot_grounding.py` that run
   the **real** audit over really ingested bytes: the repaired sentence accepted, the
   recorded elision still refused, a lettered item still not a `sub_ref`. Each guard was
   observed failing (reflow disabled, footer un-furnished) before being trusted.
7. **Fixtures regenerated** — 6 of 9 changed. Four of those changes are the reflow itself
   (`bpp_intro`, `opp_4_1`, `opp_4_5`, `saoso_appendices`); the other two were already
   modified in the working tree by the previous session. Verified by rebuilding the
   fixtures *without* reflow and diffing: the only delta is the joined words.
8. **Recorded, not fixed: G7.** One BPP general-principles line spans the gutter
   (`… fertilisers (agro-` / `and thereafter …`), so `de_column` keeps it whole and
   `HeadingParser` splits it into two body lines; the left column's prohibition is still not
   contiguous. Same class as Appendix 2 — it needs a reviewed line or a measured band
   override, not a line join.

**Nothing is committed.** The tree now holds three sessions' work: D, the column transform,
the answer-coverage work and this one. `git add` by path if you want this isolated — note
that `knowledge/tests/fixtures/` also carries the previous session's uncommitted
regeneration, so committing the fixtures commits both.

---

## 17. What the canonical-corpus session did (2026-10-22)

**The finding:** four consecutive sessions had been repairing *extraction* rather than the
product (D46 columns, D51 tables, D52 reflow, G7 spans), because the extractor sat on the
ingest path — every layout irregularity became a wrong or refused chatbot answer. The fix
is architectural, and it is recorded as **D53**: the text of record is a **reviewed
artefact** per document, extraction runs per *edition*, and a layout defect becomes a line
in a diff. Freezing happens at the **section** level; chunking and embeddings stay derived.

1. **`knowledge/corpus.py` (new, pure)** — the format and its reader. Markdown with
   `<!-- page: N printed: M -->` markers, `##` headings, `<!-- ref: … -->`, text verbatim.
   A block with no page marker is an error. `CORPUS_EDITS` holds reviewed corrections as
   **data**, so a test can prove each was necessary and applied. 14 tests
   (`test_corpus_format.py`).
2. **`knowledge/corpus/bpp.md`** — the BPP, 13 pages, reviewed, 5 corrections. Frozen at
   `generator: knowledge corpusgen v2` with `raw_pages` recorded in the header.
3. **`scripts/build_corpus.py` (new)** — drafts the artefact: `extract_pages` →
   `apply_layout` → `reflow_pages` → the section parser for *which headings exist*, then
   page-by-page body text with page markers. Refuses to overwrite an existing artefact
   without `--force`, because only the operator knows whether it was reviewed.
4. **Three generator improvements the review produced** (the "prefill" work):
   - **`columns.py`: bands narrowed to the columns no line writes into.** The detected
     gutter started inside the left column (long lines overflow into it), so those lines
     were kept whole and the right column was emitted inside them. Measured: BPP's
     uncuttable lines **66 → 13**, losslessly, on 6 pages; SAOSO/OPP unchanged by
     construction. **G7's cause disappeared entirely** — no span-cut code was needed.
   - **Per-page `-raw` fallback in the generator.** Measured: `-raw` is a
     character-for-character **permutation** of `-layout` on all **139** pages, so its
     order is trustworthy; it glues words, which is repairable by splitting each glued
     token into the run of `-layout` words that concatenates to it. A page is drafted from
     `-raw` only when, after that repair, its word multiset is identical — **11 of BPP's
     13 pages**, including 3, 6 and 9, the pages geometry cannot handle.
   - **`page_stamp()` shared** with `HeadingParser` — the printed page is read from the
     de-columned rendering, because the two renderings disagree where a stamp shares a
     line with body text (the BPP's `02`).
5. **`ingest_standard(..., corpus_path=)` + `--from-corpus`** — the artefact's sections are
   used instead of parsing the PDF; the PDF is still hashed and must match the artefact's
   recorded sha256; a mismatch, or another document's artefact, is refused.
   `IngestReport.corpus_digest` records which review produced the corpus.
   `--from-pdf` still works and is still tested.
6. **Tests: 705 green** (was 652), `lint-imports` kept. The guards are the point: character
   multiset coverage, section-identity equality between the two paths, per-block
   traceability, edit necessity/application, and the four sentences the product quotes.
7. **G7 closed, live.** Re-ingested the BPP from the artefact (9 chunks, embedded) and
   probed: *"can I use synthetic fertilisers or agro-chemicals?"* → **grounded**, 4
   citations, the BPP's prohibition quoted verbatim. The manure question still cites
   "Animal manure must be preferably composted prior to application…" verbatim, which is
   why the page-4 footnote had to move.
8. **Ten more examples, generated and tested** (the request that closed the session):
   ten BPP requirements — GM seed, organic-seed sourcing, landless husbandry, daily
   pasture access, hen rest hours, breeding-stock 10%, approved cleaning agents, feed from
   the farm, and the two already cited — each asserted to be quotable from **exactly one
   chunk** (`knowledge`) and accepted by the **real audit** (`core`). A paraphrase is still
   refused. One candidate was rejected because it had been quoted from memory and the
   document prints "Employment **practice** should be", singular: every example is copied
   from the artefact. Live probes for two of them cited SAOSO (S5.1.9, S5.5.3) rather than
   the BPP, which is the "prefer the governing document" rule working.
9. **What a human still fixes** (5 corrections): the page-4 footnote interrupting the
   manure sentence, the glued `Preventativemethods(`, and the repeated four-principle
   strip on pages 8 and 10 (kept on page 6). The bare page stamp is now a generator rule.

**Not done:** the OPP, landscape and SAOSO are still on the PDF path. Two follow-ups are
recorded in the PRD §7 and matter: a reviewed edit needs `--force` because idempotency is
keyed on the PDF's sha256 (nothing compares the stored `corpus_digest`), and
`CORPUS_DOCUMENTS` lives beside the models so the generator needs Django settings.

**Uncommitted, again.** This session added `knowledge/corpus.py`, `knowledge/corpus/bpp.md`,
`scripts/build_corpus.py`, `knowledge/tests/test_corpus_*.py`, the ingest/command/columns
changes and the docs. The fixture/column changes from D52 are still uncommitted beneath it.

---

## 18. NEXT UP — **judge the UAT and sign it** (the tooling is built)

**Nothing in `tests/uat/` is signed.** That is still the single fact keeping C1 (public site) and D
(chatbot) *partial*, and it stands between MVP 0 and done. **The tooling that makes it possible
landed on 2026-10-22** — see §19. What remains is a human sitting down and judging, which is the
one thing no session can do for itself.

**The three commands, in order:**

```bash
# 1. Is the instance ready? Keep the output: the reviewer sees it.
python manage.py uat_seed --check > preflight.txt

# 2. One self-contained HTML at product/design/uat/<slug>.html
python scripts/uat_runner.py --file tests/uat/mvp0_standards_and_public_site_uat.md \
                             --preflight preflight.txt --database <the DB being signed>

# 3. The reviewer judges every card and downloads uat-<slug>-signoff.json. Then:
python scripts/uat_signoff.py --file tests/uat/mvp0_standards_and_public_site_uat.md \
                              --from <the export> --dry-run
```

| Piece | File | What it does |
|---|---|---|
| Skill | `.agents/skills/pgs-presenting-uat/SKILL.md` | the three moves, the hard rules, the anti-patterns |
| Format + gate + scan | `scripts/uat_parse.py` | parses the UAT format; refuses a scenario with no `Judgement:`; the applicability scan |
| Shell | `scripts/uat_page.py` | CSS, script, markdown renderer, `environment()` |
| Runner | `scripts/uat_runner.py` | one self-contained HTML; no CDN, no network, `file://` |
| Write-back | `scripts/uat_signoff.py` | `--dry-run` diff; `**Result:**` per scenario + `### Per-scenario results`; idempotent |
| Preflight | `core/services/_uat.py`, `manage.py uat_seed --check` | **385 chunks** (SAOSO 338 + OPP 30 + BPP 9 + landscape 8), 0 unembedded, **8 published documents**, settings, health, `pdftotext` |

**D1–D4 are settled** (PRD §9, confirmed 2026-10-22): staging for anything that writes and production
for read-only scenarios; screenshots optional; one sign-off row per scenario; one seat each, product
may co-sign.

**Read G8 before judging.** Scenario 1 refuses today, for a measured reason that is not the
reviewer's to fix; Scenarios 2, 3, 9 and 10 are the same class of surface and may refuse the same
way. Judge what you see and record it — the scenarios still have to be judged, and a recorded
FAIL with a cause is worth more than a blank.

**Definition of done:** scenarios 1, 2, 3, 6, 9, 10 and C1's 4, 6, 8 carry a result and a signature
in `tests/uat/mvp0_standards_and_public_site_uat.md`, applied by `uat_signoff.py` and committed. That
flips C1 and D from partial to done.

### Two operational items that outrank it, and are cheap

1. **The deployed corpus predates D52 and D53.** `deploy/deploy.sh` migrates, seeds, publishes and
   collects static — it **never runs `ingest_standard`** — so the live chatbot is answering from
   text without the hyphen reflow, the page-footer fix or the BPP artefact. Refresh the four
   documents once on the box, deliberately (`--force` each), confirm **385 chunks** and
   `lexical_only=False`, then ask three questions through `/ask/`. Also check `pdftotext -v`: if the
   server runs poppler and this box runs Xpdf 4.00, the extraction differs from every fixture.
2. **`--force` must not go into `deploy.sh`.** It re-embeds on every deploy, changes every chunk id,
   and cascades through `ChatMessage.retrieved_chunks` — every historical answer loses its evidence
   trail. **Since 2026-10-28 the trail can be rebuilt**: `manage.py relink_evidence --apply`
   restores the links from the `grounding` snapshot wherever the passage's text is unchanged, and
   reports the ones it cannot (a passage the rebuild rewrote). Run it after every deliberate
   `--force`, before anything else touches the corpus. The recommended replacement is still
   `corpus_check` (read-only diff, no API calls) in the deploy plus `corpus_refresh --apply` as a
   deliberate operator command; `deploy.sh` may fill an **empty** corpus but must only *report*
   drift on a non-empty one. Written up in `CORPUS_CANONICAL_FORMAT_PRD.md` §7 item 1, awaiting a
   yes/no.

### Then, in order

`0∥` spike (the real gate for intake flows, `MVP1A_PLAN` §D26) → MVP 1a → the OPP/SAOSO artefact
conversion (absorbs G4) → G3 (the cost answer omits the R100 membership fee) → G6 (the refusal
promises a person who cannot be reached).

### Session close, 2026-10-22

`verify.sh` green at **705 tests**, `lint-imports` kept, backlog index clean (`product/backlog.py`
reports no drift). **The tree is uncommitted**: 12 modified files plus 6 new ones — the corpus
artefact and reader (`knowledge/corpus.py`, `knowledge/corpus/bpp.md`), the generator
(`scripts/build_corpus.py`), two test modules, `CORPUS_CANONICAL_FORMAT_PRD.md`, and the
`UAT_SIGN_OFF_TOOLING_PRD.md` this section is about. `HEAD == origin/main` (`91cec12`, the ops
commit), so **none of this session's work is deployed** — it needs one commit and a push before the
deployed corpus can be refreshed from it.

---

## 19. What the sign-off-tooling session did (2026-10-22)

**The blocker was never the scenarios — it was that signing one took a developer.** Slice 1 of
`UAT_SIGN_OFF_TOOLING_PRD.md` is built: a reviewer opens one HTML file, runs the preflight, judges,
and exports a file that writes the results into the UAT markdown. **Nothing is signed yet** — that
is a human act, and it is now the only thing left.

1. **`scripts/uat_parse.py` (new, pure).** The only code that knows the UAT file's shape: front
   matter, `## Scenario N — …` sections, labelled fields, numbered steps, notes, and the line spans
   the write-back needs. It **refuses** rather than copes — a scenario with no `Judgement:` clause,
   a duplicate scenario number, or a missing `feature slug` is an error naming the scenario, because
   a card built from a guess is a judgement nobody was asked to make.
2. **The applicability scan — the thing this session exists for.** An N/A scenario outlives the
   decision that caused it unless something checks. `scan_applicability()` requires every N/A to
   cite a `D<n>` in its `**Status:**`, requires the id to exist in `PGS_PLATFORM_SPEC.md` §18.3, and
   requires that decision's resolution to **still read as a deferral**. Edit D44 to say C3 is picked
   up and the runner exits non-zero naming Scenario 5, instead of printing a greyed-out card for a
   scenario that has become deliverable. Pinned by test at **10 scenarios / 9 applicable / 1 N/A**,
   and by §2.5 of the tests (`mvp1a`'s twelve).
   *No model decides this.* The product owner asked whether an LLM (via OpenRouter) should; the
   answer recorded is no — the artefact must make **zero network requests** (its own acceptance
   criterion), a signature has to be reproducible from the commit, and HANDOVER §4 already settled
   the same shape of question ("prefer a seeded alias table to an ungrounded model call").
3. **`scripts/uat_page.py` + `scripts/uat_runner.py`.** The runner was 37 KB in one file and broke
   the 30 KB cap, so the shell (CSS, script, markdown renderer, `environment()`) is its own module.
   The artefact embeds the raw markdown in a `uat-data` payload *and* renders it server-side, so it
   works with JavaScript off and a test can check the words the reviewer read.
4. **`scripts/uat_signoff.py`.** Two things change and nothing else: a `**Result:**` line after each
   `Judgement:` paragraph, and a `### Per-scenario results` table plus a `**Signed against:**` line
   carrying the commit and database. `--dry-run` prints the diff, a second application changes
   nothing, and a malformed export is refused whole rather than half-applied.
5. **`core/services/_uat.py` + `manage.py uat_seed --check`.** Six rows, observed beside expected:
   settings, dependencies, **385 chunks**, 0 unembedded, **8 published documents**, `pdftotext`.
   The corpus blocks; health and `pdftotext` advise, because `celery_worker` is legitimately absent
   on a dev box and a row that is always red is a row nobody reads. **Measured on this box: 385
   chunks, 0 without a vector, 8 published, Xpdf 4.00** (338 SAOSO since §0h).
   Slice 1 has no `--scenario` seeder: MVP 0 needs no new rows, and a bare `uat_seed` exits 2 rather
   than pretending.
6. **63 tests in `tests/tools/` plus 4 browser tests in `tests/e2e/test_uat_artefact.py`**, and `pytest.ini`'s `testpaths` now includes `tests/tools` — a test outside
   `testpaths` is a test the gate never runs (`testing_hazards.md` §2.6). Gate green at **768**,
   `lint-imports` kept. Eight guards were mutation-tested: the steps split, the deferral check, the
   judgement gate, the insertion point, the reason requirement, the CRLF guard, HTML escaping and the
   blocking corpus row each failed a test when broken.
7. **Two defects, both invisible to a green suite.** (a) Extracting the script left the IIFE's
   closing `})();` inside the body *and* wrapped it again, so Chromium threw `Unexpected token '}'`
   and the page was inert — every structural assertion stayed green because the cards are
   server-rendered. Found only by loading it in Playwright and reading the console
   (`testing_hazards.md` §1.30). (b) `write_text` emits CRLF on Windows (§1.27, already recorded).
   **Verified in a real browser:** ten cards, ten judgement blocks, the N/A card carrying D44's
   reason, progress `1 of 10` → `10 of 10`, a downloaded export that `uat_signoff.py --dry-run`
   accepts, one request (the file itself), a clean console, and no horizontal overflow at 390 px.
   **Mutation-tested:** re-introduce the defect and all 63 gate tests stay green while three of
   the four browser tests go red — which is the whole argument for keeping them.
8. **Also recorded:** §1.29 — a string "present" in a JSON payload is not present in the file, because
   `json.dumps` escapes the newlines; and §3.10 — Xpdf's `pdftotext -v` prints its version and exits
   **1**, which made the preflight row permanently red until the check became "a banner was printed".

**The artefact is committed at `product/design/uat/mvp0_standards_and_public_site.html`.** It records
`Generated <date>` from the machine that built it, so **regenerate it on the box whose commit it
claims** before handing it to a reviewer.

**Two more landed the same day, both prompted by bringing the UAT up:**

* **`/uat/` — the setup commands as buttons** (staff-only, POST + CSRF, whitelist). The
  artefact stays a `file://` document with zero network requests; a browser cannot run
  `manage.py` from one, so the buttons live on a served page beside it. `--force` is
  *shown with its reason, never clickable*. One `render_preflight()` feeds the console, the
  management command and the artefact, so they cannot disagree.
* **The chat cache and the audit** — `answer_question()` cached the model's reply *before*
  auditing it, so a reply the audit rejected was re-served for the whole TTL and Scenario 1
  refused reproducibly. Only an accepted answer is cached now, and an audit rejection is its
  own escalation reason (`CITATION_AUDIT`, **D54**) instead of `NO_CITATIONS`. Gate **788**.

**Next, in order:** judge the UAT (§18) → slice 2's `uat-setup` format and the
`manage.py <command>` existence lint (which is what catches `mvp1a`'s `load_template`) → the two
operational items in §18 → MVP 1a.

---

## 20. Session close, 2026-10-21 — MVP 0 signed

**The sign-off that four sessions deferred is in the file.** `tests/uat/mvp0_standards_and_public_site_uat.md`
carries ten results — nine **PASS**, Scenario 5 **N/A** (D44) — signed by the product owner,
applied by `scripts/uat_signoff.py` and committed. The diff was exactly what the tool promises:
ten `**Result:**` lines, the `### Per-scenario results` table, the `**Signed against:**` line,
and nothing else.

1. **The tooling paid for itself on its first use.** The reviewer judged in the HTML artefact,
   exported JSON, and the write-back landed it with `--dry-run` reviewed first. No markdown was
   hand-edited.
2. **The console earned its place.** `/uat/` ran the preflight and rebuilt the artefact from
   buttons, which is what the product owner asked for; a `file://` page cannot run `manage.py`,
   so the commands live on a served page and the artefact stays offline.
3. **Two defects were found by bringing the UAT up, and both are recorded, not absorbed.**
   `answer_question()` cached the model's reply *before* auditing it (fixed; §1.31, five tests),
   and the model still cites one sentence twice on Scenario 1's question (**G8**, open — the
   refusal is the audit doing its job). The cost question (Scenario 10 item 5) refuses for the
   same reason, so **G3** is not merely "omits the R100 fee" any more.
4. **What the signature does and does not mean.** It means the product owner judged all ten and
   accepted MVP 0 with G8 and G3 written down. It does **not** mean the OPP's three voices have
   spoken: the PGS administrator, committee reviewer and consumer member rows are empty, and the
   file says so. `mvp1a`'s UAT is unsigned because 1a is not built.
5. **A test that was passing for the wrong reason is fixed.** `test_the_result_lands_after_the_
   judgement_and_before_what_follows` anchored on a line number (`i > 220`) and broke the moment
   a note was added above it; it now anchors on Scenario 9's heading.

**For the next agent, in order:** **G8** (prompt rule 7 + `PROMPT_VERSION`, measured against the
probe *with the chat retrieval limit* — the probe currently measures a different path and looks
green) → the two operational items in §18 (the deployed corpus predates D52/D53; `--force` must
not enter `deploy.sh`) → the remaining two seats → the `0∥` spike → MVP 1a.

**State:** gate green at **788**, `lint-imports` kept, backlog no drift, tree clean, everything
pushed. The dev instance from the sign-off session is stopped; `manage.py changepassword admin`
is the way into `/uat/` and `/admin/` if the password is not to hand.

---

## 21. What the budget-and-instrument session did (2026-10-22)

**G8 was a measurement failure before it was a model failure.** The session opened with
"fix G8's prompt" and ended with **no prompt change at all**, because the first thing the
PRD demanded — a trustworthy instrument — showed that the product had been retrieving five
passages for a day while four documents said eight.

1. **The probe now measures the product.** `scripts/probe_chat.py` takes `--limit`
   (default `chat_retrieval_limit()`) and retrieves through `core.services._chatbot.
   default_retrieval()` — the function `answer_question()` calls. It has no retrieval call
   of its own; `tests/tools/test_probe_chat.py` fails if one returns. Before this, the probe
   hardcoded `limit=8` and printed a grounded answer for a question `/ask/` refuses.
2. **The budget defect.** D49 recorded "Chat `RETRIEVAL_LIMIT` 5 → 8" and edited the module
   constant. `answer_question()` read `getattr(settings, "CHAT_RETRIEVAL_LIMIT",
   RETRIEVAL_LIMIT)`, and `settings` always defines that attribute (default `"5"`), so the
   constant was never read: **production ran at five.** Measured: at five, *"Can i use
   cardboard from my neighbour?"* retrieves no inputs clause and refuses — the exact
   question the budget was raised for — and Scenario 1's question retrieves **two**
   `general-principles` chunks, which is what invited the duplicate citation. At eight,
   cardboard answers from Appendix 2 and Scenario 1 cites `S5.1.9` once.
3. **The fix is one accessor and one path.** `chat_retrieval_limit()` is the only reader of
   the setting; `default_retrieval()` is the only retrieval path. `CHAT_RETRIEVAL_LIMIT` is 8
   in `pgs/settings.py` and `.env.example`; `PROMPT_VERSION` is `d49-2`, because every cached
   answer had been produced against a five-passage set. `RETRIEVAL_LIMIT` is now documented
   as what it is — a fallback — and a test fails if the two disagree.
4. **Measured after the change, five runs as the PRD requires.** Scenario 1's question:
   **5/5** grounded, one verbatim `S5.1.9` citation each. The nine-question suite: **9/9**
   grounded (at five it was 7/9 — cardboard refused, the cost question truncated). The cost
   question still omits §2.1's R100 membership fee, so **G3 is unchanged and re-measured**.
5. **Why rule 7 was left alone.** Once the failing case is gone, rewording the prompt is
   unmeasured churn, and `audit_citations` was never the problem. The residual is recorded:
   at five, the duplicate BPP citation was *accepted* only because the D53 artefact spells
   "eight" — corpus luck, not a looser audit. If it returns, candidate fix A in the PRD is
   the remedy, measured against the same five-run rule.
6. **Five guards, mutation-checked** (break it, watch it go red, restore): the parser's
   default limit, an explicit `--limit`, "no retrieval call of its own", the limit reaching
   the shared helper, and the setting/fallback agreement. Gate **794**, `lint-imports` kept,
   backlog no drift.

**Traps recorded:** `testing_hazards.md` **§2.7** — a `getattr(settings, ...)` default is
dead code when `pgs/settings.py` defines the name, so the "fix" changes nothing and the
instrument that agrees with the fix is the one that hides it.

**Next, in order:** the two operational items in §4 item 2 (the deployed corpus and the box's
`CHAT_RETRIEVAL_LIMIT` both predate this commit) → the remaining two UAT seats → `0∥` spike →
MVP 1a. Then G3, G4, G6, G7 and UAT-tooling slice 2.

---

## 22. Session close, 2026-10-22 — the deploy that found six bugs, and the plan that ends the extractor

**This session started with "fix G8's prompt" and ended with a deployed site, a gate that no
longer needs a PDF reader, and a plan that takes the extractor out of the runtime entirely.**

### What shipped

1. **G8 closed by measurement — and the cause was a budget nobody was reading.** See §21. The
   fix is `chat_retrieval_limit()` + `default_retrieval()`, `CHAT_RETRIEVAL_LIMIT` at 8, and
   `PROMPT_VERSION` `d49-2`. No prompt change; `audit_citations` untouched.
2. **D55–D59 recorded** in `PGS_PLATFORM_SPEC.md` §18.3: fail-closed artefact ingest; stored
   corpus digest with drift reporting; the gate reads committed pages and the extractor
   becomes a build-time tool; SAOSO review is mechanical-first; **chat transcripts are kept
   indefinitely until the group sets a schedule** (POPIA decision, revisit trigger named).
3. **`CORPUS_CANONICAL_FORMAT_PLAN.md`** — P0–P7, the plan that makes "which PDF reader" stop
   being a runtime question. **P1 is built**: nine committed page fixtures, provenance checked
   both ways, `verify.sh` runs pytest with `PDFTOTEXT_BIN` pointed at a path that cannot exist,
   and `scripts/check_extraction.py` is the build-time drift check that replaces what the gate
   gave up. 800→804 tests, and the suite dropped from 89 s to 38 s.
4. **The site is live and redeployable.** Six runs of `deploy.sh`; six defects, each now fixed
   with the guard that fails if it returns: exec bits (§2.8), the shallow fetch that broke its
   own pull (§2.10), the extractor calibration (§2.9), the `pg_dump` version parse (§2.11), a
   missing migration + `makemigrations --check` in the gate, and a duplicated static directory.

### What the next agent should do, in order

1. **Deploy the two pending commits.** `fb41a47` adds migration `core/0005` (choices-only) and
   the `makemigrations --check` gate step; `54ef082` fixes the poppler attribution label. One
   deploy applies both. Expect `Apply all migrations: … core.0005`, no static warnings, and
   `uat_seed --check` reporting `pdftotext version 24.02.0 (poppler)`.
2. **P2** — `corpus_digest` + `corpus_check`/`corpus_refresh`, **plus P2.5–P2.8**: attribution
   fields on `ChatMessage`, `manage.py chat_review`, a staff flag for the wrong-but-grounded
   answer, and the retention record (D59). This is what turns "the corpus is 363, is that
   right?" into a command, and a refusal into a corpus-gap queue.
3. **P3** (replayable edits), then **P4 → P5 → P6** (OPP 15 pp, landscape 10 pp, SAOSO 101 pp +
   appendices, absorbing G4), then **P7** (fail-closed ingest, docs, and the VPS refresh from
   artefacts — after which the box needs no `pdftotext` at all).

### Traps recorded this session (all in `testing_hazards.md`)

`§2.8` a file mode is part of the commit and Windows cannot see it · `§2.9` the gate was
calibrated to one `pdftotext` implementation · `§2.10` `git fetch --depth 1` in a deploy makes
the next `--ff-only` pull impossible · `§2.11` `grep -oE` prints every match and `-m1` is not a
fix, plus two harness traps that made a test fail for its own reasons.

**The theme worth carrying forward:** four of those six deploy defects were invisible to 800
green tests, and every one was found by *running the thing that had never been run*. The gate is
stronger than it was, but its strength now comes from the deploy having been exercised.

**State:** gate green at **804**, `lint-imports` kept, backlog no drift, tree clean, everything
pushed. Live `206f35f`; `/health/` ok; corpus 363 chunks with 0 unembedded; MVP 0's UAT signed by the product owner only (three seats still empty).
