# Handover — MVP 0: A, B, C1, C2, C4 and D landed; UAT signed; G8 closed

> ## START HERE — the owner's order is: context first, then the table work
>
> **Where the work stands (2026-11-02).** Session 7 landed two slices and then produced the
> evidence for the next two; the owner has since fixed the order.
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
> 4. **Two decision pages, neither answered:** `product/design/g11_row_labels_exploration.html`
>    (how a printed column header reaches a row's quotable text — five options, **E recommended**)
>    and `product/design/g12_ingestion_generalisation.html` (does the engine survive an unseen
>    document — **X2 now, X3 when demanded**, decided as **D80**).
> 5. **Context budget measured and the first cut taken** (`product/docs/context/CONTEXT_BUDGET.md`):
>    the six files this repo told every session to read total **509 KB ≈ 144k tokens**;
>    `HANDOVER.md` was 2,553 lines of which 72 were state. **This file is now 138 lines** and the
>    22 session narratives are in `product/docs/handover/`. `python scripts/context.py --task
>    <chat|corpus|reader|public|backlog>` prints what to read and what to grep.
>
> **What is next, in the owner's order:**
>
> 1. **Context cuts 4.2 and 4.3** (`CONTEXT_BUDGET.md`). 4.2: a §18.3 row becomes a sentence plus a
>    link — **nine rows are over 1.5 KB** (`D71` is 3.7 KB) and the evidence already exists in
>    `product/design/` and the PRDs. 4.3: split `core/services/_chatbot.py` (**91 KB, 3× the §II
>    cap**) along its own four headings, then `knowledge/corpus.py` (49 KB). 4.4: wire
>    `scripts/context.py --check` into the gate **once the tree is inside budget** — it reports 12
>    breaches today.
> 2. **The table work, in this order:** answer **G11** (D79 — A as a stopgap or E as the target),
>    then **G12/X2** starting with the **eight-shape fixture set** (that is D80's first commit).
> 3. **The landscape UAT sign-off** — still unsigned, still unblocked, still the only thing keeping
>    `LANDSCAPE_TABLES_PRD` out of `Done/`.
>
> **Do not run `scripts/build_corpus.py --force` on a document with a table block** — the generator
> has no table-block rule and replaces the review with column soup while every guard stays green
> (`testing_hazards.md` §3.25).
>
> **"corpus is current" does not mean "rebuilt"** — drift compares the artefact's hash and the
> chunk count, not the derived text (`testing_hazards.md` §3.24). After a chunker or parser change,
> `ingest_standard --doc <x> --force` then `relink_evidence --apply`.
>
> **Deploy note:** the live box is still `8d2839d` and misses three sessions. A deploy pulls the
> artefacts but never re-ingests; the OPP's 30 → 37 chunks is a corpus change, not a code change.

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4 and context-budget sessions
**Repo state:** `main`, **33 commits ahead of `origin/main`** (`35051e1`); the last code commit is
`18a8523` and this documentation commit follows it. On that tree: `scripts/fast.sh` green (whole
suite minus `slow`) and `verify.sh` green at **1558 passed / 1 skipped in 67.2 s** cold, run as
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify` (the gate defaults to 5432 and this box
serves 5433, `testing_hazards.md` §3.1). `pytest tests/e2e` **71 passed** (not in the gate: needs a
browser). The suite is fast today because the database was warm; quote the cold and warm pair, not
one number (`testing_hazards.md` §3.17).

**The dev box is current.** All four documents re-ingested from their artefacts, **401 chunks, 0
unembedded**, `corpus_check` says *current* — and `relink_evidence` reports 73 linked with 31 left
unlinked on purpose (same locator, different text: the transition off the PDF parses).

**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **33 commits unpushed**.
**Live:** `https://organicguarantee.africa` on the homtini VPS at **`8d2839d`**, deployed
2026-10-30 — three sessions behind, with the old PDF-built corpus. A deploy pulls the artefacts but
never runs `ingest_standard`, so the box will show drift on all four until someone runs
`corpus_refresh --apply` there deliberately.

## Session archive

History, verbatim, one file per session. **Read only the session a task sends you to.**
A new session writes its narrative to `product/docs/handover/SESSION_<tag>_<date>_<slug>.md`
and adds one line here; this file stays state.

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
