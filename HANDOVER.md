# Handover — D79's three slices and the landscape UAT are signed; the context cuts are next

> ## START HERE — the landscape is signed and in `Done/`; the context cuts are next
>
> **Where the work stands (2026-11-03, session 12).** Two sign-offs are in: G11's **Scenario 8**
> (2026-11-02) and the **landscape tables, 6 PASS · 0 FAIL · 0 N/A** (2026-11-01, applied
> 2026-11-03 against `ecd3c8d`), so `LANDSCAPE_TABLES_PRD` has moved to `Done/` with `TABLE_BANDS`
> and the corpus-level table-page guard **named and carried forward** into D80. The sign-off's one
> finding — a Fee cell reading "As above" with nothing above it on a deep link — is the **paper's**
> wording, faithfully reproduced, and the legend already explains it; what is ours is that the
> referent is unreachable, filed as `BugFixes/landscape_fee_as_above_referent.md`. The session
> record is `product/docs/handover/SESSION_0z_2026-11-03_the-landscape-is-signed-and-the-as-above.md`;
> this block is state only.
>
> 1. **Cost-question rule — built** (`d78-2`, D78). The assistant separates the *member's* fee from
>    the *group's*, names the assessment as unavoidable, and may state one floor (membership + one
>    named band), which is the shape `/costs/` publishes. Measured after: all four phrasings
>    complete and grounded, suite 9 of 9.
> 2. **P4 — the OPP artefact, §2.3 as a grid** (`37b682a`…`61b640c`). All four governed documents
>    are artefact-backed; corpus **401 chunks, all current**. The conversion needed corpus-format
>    **rule 6** (`<!-- sub: … -->`) or 24 sub-clause addresses would have vanished.
> 3. **G10's refusal is located and is one space** — a quote across a line break (`1.` / `o`). Not
>    fixed: the decision is written up and belongs to the owner.
> 4. **G11 is answered: D79 = E** (2026-11-02). Show the table as structure, quote cells only, render
>    the row's context from the artefact at cite time; `product/design/g11_option_e_explainer.html`
>    teaches the mechanism. **All three slices are built.** Slice 1 (`9608656`): the seats are filled
>    in the vector arm's own order and a heading cannot take one. Slice 2 (`64f70ae`, `16c2b2a`): a
>    reviewed table's rows travel with any passage of it (`knowledge/table_context.py`), the prompt
>    shows the table once with its printed headings (`d79-2`), and `Citation.row_label` reaches the
>    templates as context. Slice 3 (session 11): **the frame is a row *and a column*** —
>    `Citation.column_label` from `column_label_for`, stored in the snapshot (the answer page had
>    silently rendered no context before this), one shared context line and **one legend per answer**
>    (`chatbot/_citation_context.html`, `_citation_legend.html`), and the reader counterpart —
>    `&quote=` on the link, the row washed and the quoted cell marked in the printed grid. **The G10
>    fees answer works:** *"…below R250,000 would pay a renewal fee of R900"*, *"…initial
>    certification fee of R1,500 or a renewal fee of R900"*. **Scenario 8 signed 2026-11-02:** the
>    dashed row/column line reads as context around the paper's own cell, so slice 3 is closed and
>    the fallback to option A is **not** taken. R@8 unchanged at 0.812.
> 5. **Context budget measured, the handover split, and the loop measured**
>    (`product/docs/context/CONTEXT_BUDGET.md`): the six files this repo told every session to read
>    totalled **509 KB ≈ 144k tokens**; `HANDOVER.md` was 2,553 lines of which 72 were state. **This
>    file is now state (~100 lines)** and the **24** session narratives are in
>    `product/docs/handover/` (content verified byte-for-byte: 173,325 in, 173,325 out), with
>    `tests/tools/test_handover.py` holding the budget. `python scripts/context.py --task
>    <chat|corpus|reader|public|backlog>` prints what to read and what to grep. **The read-set was
>    not the whole bill:** 47 session logs measured **1.70 B tokens processed**, median **26 M per
>    session**, **26 API requests per user message** — thinking and tool-call arguments are 60% of
>    retained context, and no PGS session ever compacted. `AGENTS.md` now carries the **Context
>    discipline** block; §7 of `CONTEXT_BUDGET.md` has the numbers. The reasoning is in
>    `SESSION_0w_2026-11-02_…md`; the split itself is `SESSION_0v_2026-11-02_…md`. This block is
>    only state.
>
> **What is next, in order:**
>
> 1. **Context cuts 4.2 and 4.3** (`CONTEXT_BUDGET.md`) — and they are bigger than they were: all
>    three slices grew `core/services/_chatbot.py` to **~99 KB (3× the §II cap)** and
>    `knowledge/services.py` to **~40 KB**, with `_documents.py` at 48 KB. `knowledge/table_context.py`
>    was deliberately created instead of adding to either. 4.2: a §18.3 row becomes a sentence plus a
>    link — `--check` names the rows over 1.5 KB (**14 today**, `D68` the largest at 3.6 KB). 4.4: wire
>    `scripts/context.py --check` into the gate **once the tree is inside budget** — 25 breaches
>    today (11 source files, 14 rows).
> 2. **G12/X2** starting with the **eight-shape fixture set** (that is D80's first commit).
>
> **The landscape is closed.** The reader's two follow-ups landed 2026-11-03 — the seals legend
> names its referent (§12h) and the folds moved to the prose (§12i, amending D77) — and the UAT was
> **re-signed against `c4c362e`: 6 PASS**, Scenarios 2 and 4 re-judged on the rebuilt artefact.
> `LANDSCAPE_TABLES_PRD` is in `Done/`; `TABLE_BANDS` and the corpus-level table-page guard are
> carried into D80 by name.
>
> **Do not run `scripts/build_corpus.py --force` on a document with a table block** — the generator
> has no table-block rule and replaces the review with column soup while every guard stays green
> (`testing_hazards.md` §3.25).
>
> **"corpus is current" does not mean "rebuilt"** — drift compares the artefact's hash and the
> chunk count, not the derived text (`testing_hazards.md` §3.24). After a chunker or parser change,
> `ingest_standard --doc <x> --force` then `relink_evidence --apply`.
>
> **Deploy note:** the live box is still `8d2839d` and misses **14 sessions (`0m`–`0z`), 57 commits**.
> A deploy pulls the artefacts but never re-ingests; the OPP's 30 → 37 chunks is a corpus change,
> not a code change.
> **The deploy also needs `d79-1`/`d79-2` to have run**: the entries are keyed on `PROMPT_VERSION`, so
> old cached answers are not served under the new contract — but a visitor mid-conversation keeps
> their thread. Slice 3 adds no migration and no corpus change; the changed templates and CSS are
> shipped by `collectstatic`, and old cards keep the page they had.

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4, context-budget, context-frame and
landscape-sign-off sessions
**Repo state:** `main`, **46 commits ahead of `origin/main`**. On this tree (2026-11-03, after the
landscape sign-off — docs and the regenerated board only, so no code moved):
`scripts/verify.sh` **green at 1593 passed / 1 skipped in 72.76 s** with `--create-db`, run as
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify` (the gate defaults to 5432 and this box
serves 5433, `testing_hazards.md` §3.1). `scripts/fast.sh` and `--critical` were **not** re-run
this session; the previous tree measured 1578 passed / 1 skipped in 42.40 s and 217 passed /
4 deselected in 11.28 s. `pytest tests/e2e` was **not** re-run this session — nothing in
`core/templates`, the URL assembly or the CSS moved; 71 passed in 135 s on the previous tree. The
gate ran on an idle box with a warm page cache, so quote it beside the earlier runs of the same
command (`testing_hazards.md` §3.17).

The suite gained **ten** guards in session 11 — the column-resolution pair, the snapshot/citation
pair, the reader-link pair, the thread's context+legend pair, the answer page's context+legend
pair and the reader's mark/no-mark pair — each proved by breaking it and watching it go red.

**The dev box is current.** All four documents re-ingested from their artefacts, **401 chunks, 0
unembedded**, `corpus_check` says *current* — and `relink_evidence` reports 73 linked with 31 left
unlinked on purpose (same locator, different text: the transition off the PDF parses).

**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **46 commits unpushed**.
**Live:** `https://organicguarantee.africa` on the homtini VPS at **`8d2839d`**, deployed
2026-10-30 — **14 sessions and 57 commits behind**, with the old PDF-built corpus. A deploy pulls
the artefacts but
never runs `ingest_standard`, so the box will show drift on all four until someone runs
`corpus_refresh --apply` there deliberately.

## Session archive

History, verbatim, one file per session. **Read only the session a task sends you to.**
A new session writes its narrative to `product/docs/handover/SESSION_<tag>_<date>_<slug>.md`
and adds one line here; this file stays state.

- `0z` 2026-11-03 (session 12) — the landscape is signed, and "As above" is the paper's word — [`SESSION_0z_2026-11-03_the-landscape-is-signed-and-the-as-above.md`](product/docs/handover/SESSION_0z_2026-11-03_the-landscape-is-signed-and-the-as-above.md)
- `0y` 2026-11-02 (session 11) — slice 3: the context is a row and a column, both surfaces say so, and Scenario 8 is signed — [`SESSION_0y_2026-11-02_slice-3-the-context-is-a-row-and-a-column.md`](product/docs/handover/SESSION_0y_2026-11-02_slice-3-the-context-is-a-row-and-a-column.md)
- `0x` 2026-11-02 (session 10) — G11 answered, and two of its three slices landed — [`SESSION_0x_2026-11-02_g11-answered-and-two-slices-landed.md`](product/docs/handover/SESSION_0x_2026-11-02_g11-answered-and-two-slices-landed.md)
- `0w` 2026-11-02 (session 9) — the context balloon is the loop, not the handover — [`SESSION_0w_2026-11-02_the-context-balloon-is-the-loop-not-the-handover.md`](product/docs/handover/SESSION_0w_2026-11-02_the-context-balloon-is-the-loop-not-the-handover.md)
- `0v` 2026-11-02 (session 8) — the cost rule, P4's printed scale, two decision pages, and the handover becomes state — [`SESSION_0v_2026-11-02_the-cost-rule-p4-two-decisions-and-the-handover-b.md`](product/docs/handover/SESSION_0v_2026-11-02_the-cost-rule-p4-two-decisions-and-the-handover-b.md)
- `0u` 2026-11-01 (session 7) — the cost rule, the OPP's printed scale, and the refusal located — [`SESSION_0u_2026-11-01_the-cost-rule-the-opp-s-printed-scale-and-th.md`](product/docs/handover/SESSION_0u_2026-11-01_the-cost-rule-the-opp-s-printed-scale-and-th.md)
- `0t` 2026-11-01 (session 6) — the two shapes are built, and one number the design did not decide — [`SESSION_0t_2026-11-01_the-two-shapes-are-built-and-one-number-the.md`](product/docs/handover/SESSION_0t_2026-11-01_the-two-shapes-are-built-and-one-number-the.md)
- `0s` 2026-10-31 (session 5) — the display model settled: C3, the split, the spreadsheet — [`SESSION_0s_2026-10-31_the-display-model-settled-c3-the-split-the-s.md`](product/docs/handover/SESSION_0s_2026-10-31_the-display-model-settled-c3-the-split-the-s.md)
- `0r` 2026-10-31 — step 6: the reader draws the printed grid, and the fit was measured wrong — [`SESSION_0r_2026-10-31_step-6-the-reader-draws-the-printed-grid-and.md`](product/docs/handover/SESSION_0r_2026-10-31_step-6-the-reader-draws-the-printed-grid-and.md)
- `0q` 2026-10-30 (session 4) — step 5: the front matter, and four probes that were zero — [`SESSION_0q_2026-10-30_step-5-the-front-matter-and-four-probes-that.md`](product/docs/handover/SESSION_0q_2026-10-30_step-5-the-front-matter-and-four-probes-that.md)
- `0p` 2026-10-30 (session 3) — the landscape is a reviewed artefact, and the false headings are gone — [`SESSION_0p_2026-10-30_the-landscape-is-a-reviewed-artefact-and-the.md`](product/docs/handover/SESSION_0p_2026-10-30_the-landscape-is-a-reviewed-artefact-and-the.md)
- `0o` 2026-10-30 (session 2) — the two preconditions for step 2, and a corruption in the review path — [`SESSION_0o_2026-10-30_the-two-preconditions-for-step-2-and-a-corru.md`](product/docs/handover/SESSION_0o_2026-10-30_the-two-preconditions-for-step-2-and-a-corru.md)
- `0n` 2026-10-30 — the table block landed, and step 1 is mechanism only — [`SESSION_0n_2026-10-30_the-table-block-landed-and-step-1-is-mechani.md`](product/docs/handover/SESSION_0n_2026-10-30_the-table-block-landed-and-step-1-is-mechani.md)
- `0m` 2026-10-29/30 — the backlog gets a public page, and it is six sentences, not a mirror — [`SESSION_0m_2026-10-29_the-backlog-gets-a-public-page-and-it-is-six.md`](product/docs/handover/SESSION_0m_2026-10-29_the-backlog-gets-a-public-page-and-it-is-six.md)
- `0l` 2026-10-30 — session close: deployed, verified, and a clean slate for the table block — [`SESSION_0l_2026-10-30_session-close-deployed-verified-and-a-clean.md`](product/docs/handover/SESSION_0l_2026-10-30_session-close-deployed-verified-and-a-clean.md)
- `0k` 2026-10-30 — the baseline got measured, the whole price got published, and the tree got committed — [`SESSION_0k_2026-10-30_the-baseline-got-measured-the-whole-price-go.md`](product/docs/handover/SESSION_0k_2026-10-30_the-baseline-got-measured-the-whole-price-go.md)
- `0j` 2026-10-29 — the landscape's tables are decided; retrieval gets a brief for the instrument it lacks — [`SESSION_0j_2026-10-29_the-landscape-s-tables-are-decided-retrieval.md`](product/docs/handover/SESSION_0j_2026-10-29_the-landscape-s-tables-are-decided-retrieval.md)
- `0i` 2026-10-28 — the corpus can say whether it is current, and the ingest fails closed — [`SESSION_0i_2026-10-28_the-corpus-can-say-whether-it-is-current-and.md`](product/docs/handover/SESSION_0i_2026-10-28_the-corpus-can-say-whether-it-is-current-and.md)
- `0a` 2026-10-23 — `/ask/` became a board of answer pages, and citations became clickable — [`SESSION_0a_2026-10-23_ask-became-a-board-of-answer-pages-and-citat.md`](product/docs/handover/SESSION_0a_2026-10-23_ask-became-a-board-of-answer-pages-and-citat.md)
- `0b` 2026-10-27 — the concordance is decided and planned; nothing is built — [`SESSION_0b_2026-10-27_the-concordance-is-decided-and-planned-nothi.md`](product/docs/handover/SESSION_0b_2026-10-27_the-concordance-is-decided-and-planned-nothi.md)
- `0c` 2026-10-27 — the concordance is built; the reader is the document's tree — [`SESSION_0c_2026-10-27_the-concordance-is-built-the-reader-is-the-d.md`](product/docs/handover/SESSION_0c_2026-10-27_the-concordance-is-built-the-reader-is-the-d.md)
- `0d` 2026-10-27 — a passage is laid out as the document prints it — [`SESSION_0d_2026-10-27_a-passage-is-laid-out-as-the-document-prints.md`](product/docs/handover/SESSION_0d_2026-10-27_a-passage-is-laid-out-as-the-document-prints.md)
- `0e` 2026-10-27 — the reader is refined; what is left is judged, not built — [`SESSION_0e_2026-10-27_the-reader-is-refined-what-is-left-is-judged.md`](product/docs/handover/SESSION_0e_2026-10-27_the-reader-is-refined-what-is-left-is-judged.md)
- `0f` 2026-10-27 — the corpus keeps its glyphs: `-enc UTF-8`, and the U+FFFD mystery is closed — [`SESSION_0f_2026-10-27_the-corpus-keeps-its-glyphs-enc-utf-8-and-th.md`](product/docs/handover/SESSION_0f_2026-10-27_the-corpus-keeps-its-glyphs-enc-utf-8-and-th.md)
- `0g` 2026-10-27 — the reader is the document: a table, references that go somewhere, and a glossary — [`SESSION_0g_2026-10-27_the-reader-is-the-document-a-table-reference.md`](product/docs/handover/SESSION_0g_2026-10-27_the-reader-is-the-document-a-table-reference.md)
- `0h` 2026-10-28 — SAOSO is a reviewed artefact, and three bugs the draft found — [`SESSION_0h_2026-10-28_saoso-is-a-reviewed-artefact-and-three-bugs.md`](product/docs/handover/SESSION_0h_2026-10-28_saoso-is-a-reviewed-artefact-and-three-bugs.md)
- `0` The one thing to know first — [`SESSION_0_undated_the-one-thing-to-know-first.md`](product/docs/handover/SESSION_0_undated_the-one-thing-to-know-first.md)
