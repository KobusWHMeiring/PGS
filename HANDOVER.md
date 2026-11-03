# Handover — deployed and current on the live box; the corpus cuts are next

> ## START HERE — the live site is deployed with a current corpus; the corpus cuts are next
>
> **Deployed 2026-11-03 (session `1b`).** Live is `06bb11a`: **401 chunks** (saoso 338, opp 37,
> landscape 17, bpp 9), `corpus_check` exit 0, `/health/` `ok` through the socket, home and the
> OPP reader both 200, 8 of landscape's 17 and 6 of opp's 37 chunks carrying a column-labelled
> rendition. The refresh cost **16 citation links** and `relink_evidence` recovered **0**: 7
> assistant turns examined, all 7 predating the grounding snapshot, so this box has recorded **no
> chat turn since 2026-10-28**. Cumulative over both refreshes: **56 links gone**, all on the same
> 7 historical answers. The next turn recorded carries a snapshot.
>
> **The dev box is NOT current, and says so.** `corpus_check` here reports `landscape` **drift**
> ("the reviewed artefact has changed since this corpus was built") and its 17 chunks carry **0**
> labelled renditions against live's 8 — so **live is ahead of the reference DB**. Do not refresh it
> until `GEMINI_API_KEY` is in the dev `.env`: it holds only `DJANGO_SECRET_KEY`, and a refresh
> without the key writes 17 NULL vectors that then report "already ingested" forever
> (`deploy/README.md` §4). This corrects session `1a`'s claim that the dev box was current.
>
> **A deploy verified one commit and installed another, then logged the verified one**
> (`testing_hazards.md` §3.27): step 1/8 verified `7b22423`, step 2/8's `pull --ff-only` re-fetched
> and landed `06bb11a`, step 8/8 printed "7b22423 is live". Fixed by fast-forwarding to
> `$VERIFY_COMMIT` — which step 1/8 already fetched — and asserting `HEAD` matches it before the
> first irreversible step. `tests/tools/test_deploy_verified_commit.py` guards it, watched red two
> ways: 3 failures with the old `pull` restored, 1 with the HEAD assertion removed. **The fix takes
> effect on the next deploy** — the live box is still running the old script.
>
> **Where the work stands (2026-11-03, session 14 `1c`).** `CONTEXT_CUTS_PRD` steps 1–10 are
> **landed**: the chat split (`_chatbot.py` 97 → 23 KB, seven modules, prompt byte-identical,
> `PROMPT_VERSION` still `d79-2`) and then, this session, the six remaining file cuts —
> `test_chatbot_grounding.py` 51 → 21+14+15+4, `test_ingest.py` 40 → 18+10+11,
> `test_retrieval.py` 38 → 17+19, `test_document_reader.py` 36 → 21+15,
> `test_section_parsers.py` 32 → 22+10, `build_corpus.py` 31 → 25+7. **Every file is now inside
> its 30 KB cap**; `--check` went 20 → 14 breaches and the 14 left are §18.3 rows.
> **No behaviour changed:** every moved body is byte-identical to its original (asserted by
> `_scratch/split_*.py`), every test count is unchanged, and the generator's `--stdout` output
> hashes identically (`965cede4…` landscape, `2fab852f…` bpp).
>
> **The critical lane did not shrink by accident.** `scripts/fast.sh --critical` still names the
> same eight files, and the guards each entry is named for stayed in the file it names — the
> refusal/grounding guards plus D46/D52 in `test_chatbot_grounding.py`, the recall floors in
> `test_retrieval.py`. What left those files is display, storage and strategy.
>
> **What is next, in order:**
>
> 0. **Nothing is deployed-pending: live is at `06bb11a` and its corpus is current.** The box's
>    `deploy.sh` is still the pre-`3c2c39d` one, but it carries the re-exec, so the next deploy
>    closes the §3.27 window by itself — **nothing is owed** (see the state block below).
> 1. **`product/backlog/In Progress/CONTEXT_CUTS_PRD.md` step 11 — the 14 §18.3 rows**
>    (`D46 D47 D52 D53 D68 D69 D70 D71 D72 D73 D74 D75 D78 D80`, 1.7–3.7 KB against a 1.5 KB
>    budget). Each row must keep decision + date + owner + **the one measurement** + a link, and
>    its argument must be **confirmed present** at that link first — three already have an
>    exploration page (`product/design/d46_…`, `d71_…`, `d68_…`); the rest need the owning PRD's
>    "landed" section or evidence table. `D44` is **not** among them and must keep its deferral
>    marker (`scripts/uat_parse.py` refuses the UAT otherwise).
> 2. **Step 12 — wire `scripts/context.py --check` into `verify.sh`, at zero breaches only**
>    (`testing_hazards.md` §3.11), with `tests/tools/test_verify_gate.py` proving a breach fails
>    the gate.
> 3. **G12/X2** starting with the **eight-shape fixture set** (that is D80's first commit).
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

**For:** the next agent.
**From:** the corpus-and-retrieval, public-site, documents, chatbot, column, embedding,
answer-coverage, budget-and-instrument, deployment, reader-structure, corpus-artefact,
corpus-drift, retrieval-baseline, deploy-and-close, generator-and-fixture, landscape-artefact,
display-model, shapes-build, cost-rule-and-P4, context-budget, context-frame,
landscape-sign-off, chat-split and handover-truth-up sessions
**Repo state:** `main`, **9 commits ahead of `origin/main`** — `06bb11a` is pushed and live; the
licence commit, the chat-split follow-ups, the six test/generator cuts, the flake fix and `1c`'s
close are the rest. On this tree (2026-11-03, session `1c`): `scripts/verify.sh` **green at 1604
passed / 1 skipped in 56.97 s**, run as
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify` (the gate defaults to 5432 and this
box serves 5433, `testing_hazards.md` §3.1). Quote that run as the number for this tree — every
commit since it is docs. Cold runs on near-identical trees have measured **126–223 s** in one
session — quote the range, never the best run (§3.17). `scripts/fast.sh` (the lane) measured
**1589 passed / 1 skipped / 15 deselected in 41.45 s warm**.

**Remote:** `origin` = `https://github.com/KobusWHMeiring/PGS.git` — **9 commits unpushed**.
**Live:** `https://organicguarantee.africa` on the homtini VPS at **`06bb11a`**, deployed
2026-11-03 with a **current** corpus (401 chunks) — START HERE has the detail. Its `deploy.sh` on
disk is the pre-`3c2c39d` one, and **the §3.27 window is self-closing, not debt**: that script
still `pull`s origin's tip, but it already carries the re-exec, so the next deploy re-runs the
fixed script, which verifies origin's tip afresh and fast-forwards to *that* — before the backup
and the first migration (`deploy/README.md`: "re-executes itself if the pull changed it"). No
manual fix is owed.
**The dev box is NOT current — it is behind live**, and says so: `corpus_check` reports
`landscape` **drift**, and its 17 landscape chunks carry **0** labelled renditions against live's
8. Do not refresh it until `GEMINI_API_KEY` is in the dev `.env` (it holds only
`DJANGO_SECRET_KEY`), or the refresh writes 17 NULL vectors that then report "already ingested"
forever (`deploy/README.md` §4). Live is the reference DB. Three lines here said otherwise
(`8d2839d`, "70 commits behind", "59 commits unpushed", "the dev box is current") — corrected
this session against git and `corpus_check`.

## Session archive

History, verbatim, one file per session. **Read only the session a task sends you to.**
A new session writes its narrative to `product/docs/handover/SESSION_<tag>_<date>_<slug>.md`
and adds one line here; this file stays state.

- `1c` 2026-11-03 (session 15) — the six remaining cuts, and every file is inside its cap — [`SESSION_1c_2026-11-03_the-six-remaining-cuts.md`](product/docs/handover/SESSION_1c_2026-11-03_the-six-remaining-cuts.md)
- `1b` 2026-11-03 (session 14) — deployed, and the deploy verified one commit and installed another — [`SESSION_1b_2026-11-03_deployed-and-the-deploy-verified-one-commit.md`](product/docs/handover/SESSION_1b_2026-11-03_deployed-and-the-deploy-verified-one-commit.md)
- `1a` 2026-11-03 (session 13) — five splits: the chat split lands, and `_chatbot.py` is 23 KB — [`SESSION_1a_2026-11-03_the-chat-split-lands-in-seven-modules.md`](product/docs/handover/SESSION_1a_2026-11-03_the-chat-split-lands-in-seven-modules.md)
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
