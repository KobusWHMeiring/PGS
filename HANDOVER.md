# Handover — the chat split is done, `_chatbot.py` is 23 KB; the corpus cuts are next

> ## START HERE — the chat split is done and `_chatbot.py` is 23 KB; the corpus cuts are next
>
> **Where the work stands (2026-11-03, session 13).** `CONTEXT_CUTS_PRD` slice 1 is closed in
> eight commits: `_chatbot.py` went **97 KB → 23 KB** against a 30 KB cap, into seven modules —
> `_chat_text` (tokens, locators, digests), `_chat_prompt`, `_chat_values`, `_chat_audit`,
> `_chat_provider`, `_chat_guard` (rate limit, validation, follow-up, retrieval, sessions) and
> `_chat_cache`. **No behaviour changed:** the prompt's sha256 and five rendered prompts are
> byte-identical, `PROMPT_VERSION` is still `d79-2`, no migration, no corpus change, and every
> module is re-imported through `_chatbot` so no import site outside the package changed. The
> session record is `product/docs/handover/SESSION_1a_2026-11-03_the-chat-split-lands-in-seven-modules.md`;
> this block is state only.
>
> **What the plan got wrong, now amended in the PRD and not remembered in chat:** the four-module
> table left `_chatbot.py` at 36 KB — over the cap the split exists to satisfy — and step 2 could
> not be built at all, because `audit_citations` constructs a `Citation`, so the audit and the
> contract would have imported each other. The values therefore move before the audit. And the
> guard slice alone measured **30,616 bytes against a 30,720 cap — 104 bytes** — so the answer
> cache left in the same commit; `_chatbot.py` now has **~7 KB of headroom**, not 0.3%.
>
> **What is next, in order:**
>
> 1. **`product/backlog/ready/CONTEXT_CUTS_PRD.md` steps 9–11** — the five over-cap test files
>    (`test_chatbot_grounding.py` 51 KB, `test_ingest.py` 40, `test_retrieval.py` 38,
>    `test_document_reader.py` 36, `test_section_parsers.py` 32), **split by scenario and never by
>    line count** — a guard that has to exist twice was never needed; then the 14 §18.3 rows; then
>    wire `scripts/context.py --check` into `verify.sh` **only at zero breaches**
>    (`testing_hazards.md` §3.11). `--check` says **20 breaches** now.
>    **Every code move is done** (steps 6–8): `corpus.py` 50 → 28 KB, `_documents.py` 48 → 15 KB,
>    `services.py` 39 → 21 KB, `tables.py` 35 → 28 KB. Each is byte-identical by fingerprint, not
>    by test: `_scratch/probe_corpus_parse.py`, `probe_reader.py`, `probe_terms.py`,
>    `probe_table_chunks.py`. Step 8 also corrected the PRD: `search_terms` is the retrieval
>    *strategy*, not term analysis.
>    **The method that keeps paying:** fingerprint what the moved code *produces*, then diff the
>    digests — and prove the move byte-identical against `git show HEAD:`, decoded as UTF-8
>    (§3.26; `text=True` is cp1252 here and mojibaked a page title).
> 2. **G12/X2** starting with the **eight-shape fixture set** (that is D80's first commit).
>
> **The landscape is closed** (session `0z`): UAT re-signed against `c4c362e`, 6 PASS;
> `LANDSCAPE_TABLES_PRD` in `Done/`; `TABLE_BANDS` and the corpus-level table-page guard carried
> into D80 by name.
>
> **Do not run `scripts/build_corpus.py --force` on a document with a table block** — the generator
> has no table-block rule and replaces the review with column soup while every guard stays green
> (`testing_hazards.md` §3.25).
>
> **"corpus is current" does not mean "rebuilt"** — drift compares the artefact's hash and the
> chunk count, not the derived text (`testing_hazards.md` §3.24). After a chunker or parser change,
> `ingest_standard --doc <x> --force` then `relink_evidence --apply`.
>
> **Deploy note:** the live box is still `8d2839d` and misses **15 sessions (`0m`–`0z`, `1a`),
> 70 commits**. A deploy pulls the artefacts but never re-ingests; the OPP's 30 → 37 chunks is a
> corpus change, not a code change. **The deploy also needs `d79-1`/`d79-2` to have run**: the
> cache entries are keyed on `PROMPT_VERSION`, so old cached answers are not served under the new
> contract — but a visitor mid-conversation keeps their thread. This session adds no template and
> no corpus change, so it needs nothing beyond the deploy.

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4, context-budget, context-frame,
landscape-sign-off and chat-split sessions
**Repo state:** `main`, **59 commits ahead of `origin/main`**. On this tree (2026-11-03, after the
chat split — services only, no template, no migration): `scripts/verify.sh` **green at 1598 passed /
1 skipped**, run as `DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify` (the gate defaults to
5432 and this box serves 5433, `testing_hazards.md` §3.1). Five cold runs this session measured
**126.50 s, 141.25 s, 154.87 s, 187.26 s and 223.41 s** on near-identical trees — quote the range,
not the best run (`testing_hazards.md` §3.17). `scripts/fast.sh --critical` measured **217 passed /
4 deselected** in 36–57 s. The suite gained **no new guard** this session: it is a move, and the
proof is byte-identity, not a test.

**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **59 commits unpushed**.
**Live:** `https://organicguarantee.africa` on the homtini VPS at **`8d2839d`**, deployed
2026-10-30 — **15 sessions and 70 commits behind**, with the old PDF-built corpus.
**The dev box is current:** all four documents re-ingested from their artefacts, **401 chunks, 0
unembedded**, `corpus_check` says *current* — and `relink_evidence` reports 73 linked with 31 left
unlinked on purpose (same locator, different text: the transition off the PDF parses).

## Session archive

History, verbatim, one file per session. **Read only the session a task sends you to.**
A new session writes its narrative to `product/docs/handover/SESSION_<tag>_<date>_<slug>.md`
and adds one line here; this file stays state.

- `1a` 2026-11-03 (session 13) — the chat split lands, and `_chatbot.py` is 23 KB — [`SESSION_1a_2026-11-03_the-chat-split-lands-in-seven-modules.md`](product/docs/handover/SESSION_1a_2026-11-03_the-chat-split-lands-in-seven-modules.md)
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
