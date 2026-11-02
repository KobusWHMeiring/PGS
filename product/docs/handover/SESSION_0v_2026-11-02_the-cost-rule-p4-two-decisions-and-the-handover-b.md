## 0v. 2026-11-01/02 (session 8) — the cost rule, P4, two decision pages, and the handover becomes state

**State: green, 34 commits ahead of `origin/main`, tree clean.** Commits in order: `01bfec3` cost
rule · `37b682a` OPP artefact · `c255882` chunker fix · `61b640c` reader joins · `9d8cf62` +
`a30581e` handover · `18a8523` cost rule `d78-2` + D73's vector half · `c7472ac` G11 exploration ·
`5013225` retrieval explainer · `561185d` G12 + context budget · `2e80b66` D80 + the handover split.
`verify.sh` **1558 passed / 1 skipped**; `pytest tests/e2e` 71 passed.

### 0v.1 The owner reported a fee answer that was wrong, twice

The session opened by reading the handover and was asked to do "the answer rule and the table
block". The first fix (`d78-1`) named the components of a cost answer. The owner then read it and
was right twice: **the R500 is the group's annual fee to SAOSO, secured from the members' fees**,
not a second charge to a farmer; and **a farm cannot be certified without a visit**, so the
assessment fee is unavoidable. `d78-2` re-cut the rule into three parts — whose amount, the
unavoidable part, the conditional part — and permitted **one** sum (membership + one named band,
called a floor), which is the shape `/costs/` already publishes (`FIRST_YEAR_FROM_CENTS`, R1 600).
Measured after: *"…secured from the group's collected membership fees and is not an additional
charge to the individual member"*; suite 9 of 9 grounded.

**The lesson worth keeping:** the first rule was faithful to the question and useless to the
reader. "Answer the question asked" is not the same as "answer the question people have".

### 0v.2 P4: the OPP became the fourth reviewed artefact

`knowledge/corpus/opp.md`, 37 chunks (30 → 37: §2.3's one chunk became a lead-in, six reviewed
bands and the notes), and **§2.3 is a `layout: grid` table** — three printed columns, six bands,
one chunk per band. All four governed documents are artefact-backed; `corpus_check` says *current*
for the first time; corpus 401 chunks, 0 unembedded.

Three things had to be fixed on the way, and each was a silent failure:

1. **`OppParser`'s `heading_path`** excluded the section itself, so the artefact and the PDF path
   compared a breadcrumb to a sentence, and the generator gave every subsection its parent's `#`
   depth. D75's third remaining item; one word.
2. **The corpus format had nowhere to put a sub-clause printed inside a section**, so converting
   the OPP dropped `4.5(1)`, `4.5(2)(c)` and `4.5(4)` — 24 addresses to 3. Rule 6
   (`<!-- sub: … -->`) fixed it, and the generator writes the markers from the **de-columned
   layout** rendering the ingest parses (drafted from `-raw`, the OPP lost five of §4.5's nine,
   because the raw rendering resets the left margin the letters hang off).
3. **The reader had two joins it had never needed**: a numbered clause's reading anchor is its
   *reference* (`2-3`), not the artefact's heading slug, so the branch match failed silently and
   the OPP rendered as prose; and the OPP's `II. Membership fees` branch holds §2.1–§2.5, so the
   match took the first section, which has no table.

Also fixed: `_prose_chunks` kept the newline that ended a table row, so §2.3's qualifying notes
began with a blank line.

### 0v.3 Why the fee amounts still cannot be said (G11), measured in stages

1. A band row is `Below R 250,000 / 1,500 / 900` — **no word in common with any question**, so it
   is vector-only by construction. It embedded as bare numbers; **D73's vector half had never been
   built**, so the bands ranked nowhere and `/ask/` answered *"the document does not specify the
   exact assessment fee"* for a fee it prints. Built it (`DocumentChunk.embedding_text`, migration
   `knowledge/0005`): the bands now rank **4th–13th in the vector arm**.
2. They still never reach the top eight, because **`SEMANTIC_SEATS` is spent on the fused head**
   (chunks the lexical arm already ranked) and the alias arm (`cost → fee`, G3's fix) then
   truncates the tail, throwing the reservation away. Two experiments were run and **reverted**
   without committing: reserving the seat last, and printing a `ROW LABELS` line in the prompt.
   Both are written up in G11 rather than left as half-changes.
3. With the seat forced by hand, the model **read the band correctly** (*"between R 500,001 and
   R 1,000,000 pays a renewal fee of R 2,500"*) and then **quoted the label line**, which the audit
   refused — correctly. A label in the prompt is a quote trap.

**Two negatives that changed the design:**

- Applying D73's rendition to Appendix 2's **prose** rows took the suite 9 of 9 → 6 of 9, so
  `TableRow.as_chunk()` sets none. **But that verdict is not established** (see 0v.4).
- The rendition lowers absolute cosine for every prose question while it *changes which row is
  top* — for manure it puts the right row first at **0.617, tied** with the wrong one. "The
  rendition fixed it" was over-claimed; the explainer corrects it.

### 0v.4 Measurements that corrected this session's own claims

- **The suite is stochastic.** Ducks refuses about **one run in two** in the *same* configuration
  (`sub_ref 'a' does not exist in the chunk` — G1's class). Any "X moved the suite from 9 to 6"
  needs five runs per question. The experiment that would settle the prose rows is specified in
  G11 Part 1.4 and has not been run.
- **Six bands sit within 0.023 cosine of each other** and their order flips when the rows are
  labelled — so **similarity cannot choose a band**; the band is the farmer's declared turnover.
  That is why G11's options are judged on *quotability*, not ranking.
- **A 2,553-line handover is unreliable, not just expensive**: its commit count said 16 when the
  tree was 27, and several modules cite `HANDOVER §17`/`§1.7`/`§6.5` — sections that have not
  existed for weeks.

### 0v.5 Deliverables that are decisions, not code

- `product/design/g11_row_labels_exploration.html` — five options (A header-in-row, B one chunk
  per table, C leave it to the page, D fee panel, **E render context at cite time**), evidence,
  recommendation **E with A as a stopgap**, and the §18.3 export. **Unanswered (D79).**
- `product/design/g12_ingestion_generalisation.html` — the eight-shape test set taken from our own
  corpus, four architectures, recommendation **X2 now / X3 when demanded**; **answered as D80**.
- `product/design/retrieval_scores_explainer.html` — how to read cosine, rank and RRF, with the
  tie correction.
- `product/docs/context/CONTEXT_BUDGET.md` + `scripts/context.py` — the read-set was **509 KB ≈
  144k tokens**; cut 4.1 took `HANDOVER.md` from 2,553 to 101 lines with the content verified
  byte-for-byte (173,325 in / 173,325 out); `tests/tools/test_handover.py` now holds the budget and
  the links.

### 0v.6 What the next session should know that is easy to get wrong

- **`build_corpus.py --force` deletes a reviewed table block** (`testing_hazards.md` §3.25). It
  happened here, to `opp.md`, and only the shape assertions caught it.
- **"corpus is current" ≠ "rebuilt"** (§3.24): drift compares the artefact hash and the chunk
  count, so a chunker/parser change needs `ingest_standard --force` + `relink_evidence --apply`.
- **Two tables in the shipped corpus are still mangled** — Appendix 6a (20 chunks with no column
  meaning) and Appendix 7 (interleaved). Neither has a test. That is D80's motivation.
