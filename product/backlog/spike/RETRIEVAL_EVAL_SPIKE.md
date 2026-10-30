# Spike: an instrument for retrieval quality — the eval set we do not have

**Status:** Spike — **S1 done 2026-10-30: the set, the runner, the integrity tests and the
baseline numbers are in the repo** (`knowledge/tests/data/retrieval_eval.json`,
`scripts/eval_retrieval.py`, `scripts/eval_set.py`, `tests/tools/test_eval_retrieval.py`).
**S2 — the D73 `context` comparison and Q1 — is not started** and cannot be: there is no
`embedding_text` column yet. See §8a for the numbers and §9 for what S1 closed.
**Runs in two passes (§0):** **S1 records the baseline** — eval set, runner, `bare`/`lexical`/`vector` — and
**S2 answers Q1** after D73's column exists. S1 is the whole of the next session; do not answer Q1 in it.
**Owner:** Build (whoever runs the day) · Decision owner: Kobus Meiring (Product)
**Last Updated:** 2026-10-30
**Scope:** Throwaway-plus-one-artefact: a committed **eval set** (data), a **runner** (read-only script),
and a table of numbers. **No production tables, no migrations, no gates.** The deliverable is a
*measurement* and a durable instrument, not a feature.
**Reference:** `Refinement/PGS_PLATFORM_SPEC.md` §18.3 **D73** (the change this must price) ·
`Refinement/TABLES_AS_DATA_PRD.md` **§7 Q6** (where this was raised) ·
`knowledge/tests/test_retrieval.py` (the floors) · `knowledge/services.py` (`search`, `search_terms`,
`fuse`, `RRF_K`) · `scripts/probe_chat.py` · `scripts/why_refused.py` ·
`In Progress/CHAT_ANSWER_COVERAGE_PRD.md` (D49) · `docs/context/testing_hazards.md` §2.4, §2.7

---

## 0. Two sessions, and why the first one cannot answer Q1

**Baseline first, comparison second.** The `context` variant needs D73's stored column, which does not
exist until the artefact holds table rows. So the spike runs in two passes, and only the first is
available today:

| Pass | When | Produces |
|---|---|---|
| **S1 — baseline** | now, on today's corpus | the graded eval set, the runner, and recall/MRR for `bare`, `lexical`, `vector` |
| **S2 — the D73 comparison** | after the table block + landscape conversion + the column | the same numbers for `context`, and **Q1 answered A/B/C** |

Recording the baseline *before* the corpus moves is the point: after D73, `bare` no longer exists as a
state, so a comparison begun then has nothing to compare against. **Do not answer Q1 in S1** — and do
not let S2 quietly re-baseline.

**S1 was run on 2026-10-30 and its output is §8a.** The corpus was still the pre-D73 one: 385 chunks,
`sha256:dd90ea793953`, with all twenty Appendix 6a rows still 3–4 tokens in their stored text.

### S1, first commands

```bash
# 1. the real questions, newest first — the half that matters most (35 rows, 2026-10-29)
python manage.py shell -c "from core.models import EscalatedQuery; \
  [print(q.reason, '|', q.question) for q in EscalatedQuery.objects.order_by('-created_at')]"

# 2. the nine that already exist, as the regression floor
sed -n '/^SUITE = (/,/^)/p' scripts/probe_chat.py

# 3. the corpus as it stands — record this in the numbers table
python manage.py shell -c "from knowledge.models import DocumentChunk; \
  print(DocumentChunk.objects.count())"   # 385 on 2026-10-29: SAOSO 338, OPP 30, BPP 9, landscape 8
```

**Facts the next reader needs, measured 2026-10-29:**

- Only **SAOSO and BPP have artefacts** (`knowledge/corpus/saoso.md`, `bpp.md`). The landscape and the
  OPP are parsed from the PDF, so their expected locators must be a passage **anchor** or
  `p.<printed page>` — there is no `ref:` to cite. SAOSO uses `section_ref` (`S20.1`), BPP uses
  headings.
- The view's retrieval entry point is **`core.services._chatbot.default_retrieval`**; the knowledge-layer
  functions are `knowledge.services.search` (raw phrase) and `search_terms` (rare-term first, D49).
  `scripts/probe_chat.py` already imports the former — copy its plumbing rather than writing new.
- `EscalatedQuery` rows carry `reason` (`corpus*0`, `NO_RETRIEVAL`, `INSUFFICIENT_CONTEXT`,
  `CITATION_AUDIT`, `NO_CITATIONS`, …), so a question can be **pre-classified** before grading: a
  `corpus*0` question whose word is genuinely absent belongs in the set with `expected: []`, not with a
  guessed locator.
- `ChatMessage.retrieved_chunks` is emptied by a `--force` re-ingest; `relink_evidence --apply`
  restores what it can. Do not build the eval set out of `retrieved_chunks` — §3.1 rule 1.

---

## 1. Why this exists

**Every retrieval argument in this repo is currently settled by reasoning.** That is not a rhetorical
claim; it is the measured state of the tests:

| What exists | What it asserts | What it cannot tell you |
|---|---|---|
| `knowledge/tests/test_retrieval.py` | **floors** — "some `S20.` clause comes back", "`traceability` does not return the glossary first" | whether the *right* passage came back, or how often, or whether anything else would have been better |
| `scripts/probe_chat.py::SUITE` | 9 questions, printed with the arm that found each chunk | there is **no expected answer** attached, so nothing is scored |
| `EscalatedQuery` (35 rows) | the reason a turn refused | nothing about the turns that *succeeded*, which are the ones to protect |
| `ChatMessage` (129 rows) | the passages each turn retrieved | — |

So when D73 changes what a vector *represents* for ~50 row-chunks (`Ewes / 13,3` → `Appendix 6a ·
Maximum number of animals per ha … — Ewes: 13,3`), nobody can say whether it helps. The honest
position recorded in `TABLES_AS_DATA_PRD.md` is "assumed improvement". This spike replaces that
sentence with a number, and then keeps the instrument for every future table and document.

**Why a spike and not a feature.** The instrument is not on any user path, it must be allowed to fail,
and its output is a *decision* — `spike/` is where this repo already keeps that shape
(`OFFLINE_SPIKE_PRD.md`).

## 2. The questions, and the answers that would matter

Three questions. Q1 is the trigger; Q2 and Q3 fall out of the same run and are worth having.

| # | Question | Answers |
|---|---|---|
| **Q1** | Does embedding a **context-bearing rendition** (D73) retrieve the right row more often than embedding the bare cells? | **A** materially better · **B** no measurable change · **C** worse |
| **Q2** | Which arm earns each result — lexical, vector, or both? Is the vector arm paying for itself on short chunks? | per-arm recall; `lexical_only` rate; the blend's contribution |
| **Q3** | What is the **ranking floor** for "the corpus contains this"? | the number a refusal decision can cite, instead of "nothing came back" |

And the consequence each answer carries — the same discipline `OFFLINE_SPIKE_PRD.md` uses:

| Answer | Consequence |
|---|---|
| **Q1 = A** | Adopt the context column for every curated row; **and** measure the same change for prose chunks before applying it there |
| **Q1 = B** | Keep it for tables only — it is cheap, reversible and semantically right — and record that the gain was not measurable, so nobody re-argues it from taste |
| **Q1 = C** | Revert D73's embed text and record the negative result. A measured "no" is worth more than an unmeasured "yes" |
| **Q2 = the vector arm adds nothing** | The honest response is to price it: embedding 385 chunks costs an API call per ingest and a 768-float column, and D3/D20 freeze the dimension for that reason. Not this spike's decision, but this spike is the only thing that could produce the evidence |
| **Q3 answered** | `CHAT_ANSWER_COVERAGE_PRD` gets a defensible threshold instead of a hand-set limit; refusals become distinguishable from ranking failures **by number** |

**What would kill the spike** (§6) is the eval set itself being untrustworthy. If grading 30 questions
takes more than half a day, or two people cannot agree on what "correct" means for more than one in
five, the set is not reproducible enough to keep and the spike stops there.

## 3. The instrument — three parts, in the order they must be built

### 3.1 The eval set (data — the load-bearing part)

One committed file, `knowledge/tests/data/retrieval_eval.yaml` (or `.json`; either, but **in the repo**,
reviewable in a diff, not in a scratch directory).

```yaml
- id: fee-membership
  question: "what does it cost to join a PGS group?"
  asked_by: uat            # uat | escalation | probe | curated | design
  expected:                # ordered by usefulness; grade 2 answers, 1 relevant
    - {doc: certification-landscape, locator: "establishing-a-pgs-group", grade: 2}
    - {doc: certification-landscape, locator: "p.5", grade: 1}
  note: "D72.2 — the fee must stay inside the row that qualifies it"
- id: species-stocking
  question: "how many sheep can I run per hectare?"
  expected:
    - {doc: saoso, locator: "Appendix 6a", grade: 2}   # `Ewes / 13,3` — the row D73 re-embeds
- id: genuinely-not-covered
  question: "do I need a permit to sell raw milk?"
  expected: []             # a refusal IS the correct answer; without these, refusal is untestable
```

**Four rules, each of which is a way this instrument fails silently:**

1. **Expected passages are chosen from the printed document, not from what retrieval currently
   returns.** Reading the current top-5 and writing them down grades the system against itself — and
   the instrument will then report 100% for a corpus with the wrong passages in it. This is
   `testing_hazards.md` §2.7 in a new costume.
2. **Determined against the paper, in the same way a `TABLE_ROWS` cell is**: a human reads the
   document, or greps the artefact. The work is the same work as curation, and it is why the set must
   stay small (30–40 items, not 300).
3. **`grade: 0` and `expected: []` are members, not omissions.** A set of only answerable questions
   cannot measure over-retrieval, which is the failure that produces a confident wrong citation.
4. **Locators must resolve.** `section_ref` when the document numbers its sections, else the passage
   anchor, else `p.<printed page>`. The runner fails loudly on an unresolvable locator rather than
   scoring it as a miss — otherwise re-ingesting a document silently deletes questions from the set.

**Sources, in order of honesty** (target: 30–40 items across all four documents):

| Source | Available now | Use |
|---|---|---|
| `EscalatedQuery.question` (35) | real questions a person actually asked and the system refused | the half that matters most: these are the near-misses |
| `scripts/probe_chat.py::SUITE` (9) | manure, cardboard, straw, borax, seed, cost | already known-good, so they are the **regression floor** |
| `tests/uat/*.md` | the signed UAT scripts' questions | the questions the product owner has already judged |
| The new tables' questions | fee, seals, SAOSO logo, stocking rates | the questions this slice exists to make answerable; 3 per table is enough |

### 3.2 The runner (read-only, one screen of output)

`scripts/eval_retrieval.py`:

```
python scripts/eval_retrieval.py                       # the set, current corpus
python scripts/eval_retrieval.py --variant bare|context|lexical|vector
python scripts/eval_retrieval.py --k 5 --json          # machine-readable
```

Reports, per question: rank of the first grade-2 passage, which arm found it, and pass/fail per metric.
Aggregates:

| Metric | Why this one |
|---|---|
| **recall@1 / @3 / @5 / @8** | the product's budget is `CHAT_RETRIEVAL_LIMIT`; @5 is the number that changes an answer |
| **MRR** | one right passage at rank 1 is worth more than four at rank 8, because the model reads the top |
| **citation-audit pass rate** on the retrieved set | the repo's real success criterion is not "found" but **quotable**: a passage that cannot be quoted is a refusal with extra steps |
| per-arm recall | Q2; `probe_chat` already prints `lex`/`vec` ranks per chunk — reuse that shape |

**One hard requirement, and it is the whole point of the runner:** it must call the **same**
`core.services._chatbot.default_retrieval` / `knowledge.services.search` the view calls. An instrument
that re-implements retrieval measures a system nobody uses — the exact defect `probe_chat.py` records
fixing when it once hardcoded `limit=8` while the product used 5. A test asserts the import, so a
future refactor cannot quietly fork it.

### 3.3 The variants

| Variant | What it isolates |
|---|---|
| `bare` | today: the chunk text as stored |
| `context` | D73: `title · column: value` per cell, from the stored column |
| `lexical` / `vector` | the arms separately, on the same set — the only way to know which one is carrying a result |

Nothing else. No query rewriting, no re-ranker, no chunk-size sweep — those are separate questions and
this spike's job is to price *one* change and leave a usable instrument behind.

## 4. What success is **not**

- **Not a pytest gate on a number.** Ranking metrics move with the corpus, the embedding model and the
  eval set itself; a hard threshold would either be trivially true or block an honest change with a
  red build. The measured numbers go in this file and in the PRD that asked for them.
- **Not "improve MRR".** The spike can legitimately conclude "no change" (Q1=B) or "the vector arm is
  not earning its cost" — both are results.
- **Not a benchmark against other systems.** This corpus is four documents with a claim-discipline
  requirement; external SOTA numbers are irrelevant to whether `Ewes / 13,3` is findable.

**What does become a permanent test is the instrument's own integrity**, three cheap assertions:

1. the eval set parses, and every locator resolves against the ingested corpus;
2. the runner imports `default_retrieval` rather than re-implementing it (§3.2);
3. at least one `expected: []` item exists, so refusals stay measurable.

## 5. Cost, and the timebox

| Step | Effort | Pass |
|---|---|---|
| Choose 30–40 questions from the four sources; read the paper for each | **½ day** | S1 |
| The runner + aggregates, reusing `probe_chat`'s plumbing | **½ day** | S1 |
| Baseline run, numbers table | **2 h** | S1 |
| `context` variant, same set | **2 h** | S2 |

**Timebox: one day, one session.** If the set is not graded by the halfway mark, stop and report the
set as the deliverable — a half-built runner with no ground truth is the expensive outcome, and the
graded questions are the part everything else depends on.

## 6. Kill criteria (recorded, not assumed)

| Condition | Consequence |
|---|---|
| Grading takes > ½ day for 30 questions | The set is too expensive to grow with the corpus. Cap it at 15, or stop |
| Two reviewers disagree on grade-2 vs grade-1 for > 1 in 5 items | The grading scheme is not reproducible; simplify to binary (answers / does not) or stop |
| The eval set cannot be seeded with ≥ 10 real `EscalatedQuery` questions | Build the set purely from UAT + curated questions, and say so — do not pass curated questions off as real usage |
| Adding the instrument changes any user-facing behaviour | It is not an instrument any more; revert |
| The runner and the view disagree on one result | Stop and fix the runner's import before recording any number (§3.2) |

## 7. Risks & hazards

| Risk | Mitigation |
|---|---|
| **Grading the system against itself** — expected passages copied from current retrieval | §3.1 rule 1. A reviewer checks every `grade: 2` locator against the artefact, not against the output |
| **Overfitting to 30 questions** — tuning `search_terms` until the set is green | The set is a *report*, not a gate (§4). Improvements must also be argued from a mechanism, and the set is re-run after a corpus change rather than during tuning |
| **Set rot** — a re-ingest changes anchors or splits a chunk, and questions silently stop matching | §3.1 rule 4: unresolvable locators fail loudly. Anchors are content-derived (`unique_anchors`), so this should be rare; the guard is what catches the exception |
| **A metric that rewards volume** — recall@8 looks fine while the top-1 is wrong | Report recall@1 and MRR alongside; the model reads the top of the list, not the bottom |
| **The instrument outlives the question** — one 40-question set reused for every retrieval change until it means nothing | Each new document or table adds 2–3 questions, in the same commit that adds it, and every table-curating task in `TABLES_AS_DATA_PRD` carries that line |
| **Numbers quoted without provenance** — "MRR improved" with no commit, corpus digest or variant name | Every recorded result carries the corpus `sha256`/`chunk_count`, the variant, and the date, so a later reader can tell whether the corpus has moved since |

## 8. What this produces

1. `knowledge/tests/data/retrieval_eval.json` — **35 graded questions**, committed, the first real
   ground truth for retrieval in this repo. (JSON rather than the `.yaml` sketched in §3.1: the gate
   must run on a bare install and PyYAML is not a dependency here; §3.1 permits either.)
2. `scripts/eval_retrieval.py` + `scripts/eval_set.py` — read-only, same retrieval path as the view,
   four variants (`context` refuses until S2), human and JSON output.
3. **A numbers table in this file**: recall@1/@3/@5/@8, MRR and citation-audit pass rate, per variant,
   with the corpus digest — **§8a**.
4. **The answer to Q1**, which is the sentence currently written as "assumed improvement" in
   `TABLES_AS_DATA_PRD.md` §7 Q5. **Still open — S2.**
5. Three integrity tests (§4) in `tests/tools/test_eval_retrieval.py`, and a line in
   `TABLES_AS_DATA_PRD`: *every new table adds its questions to the set.*

---

## 8a. S1 measured — the baseline, 2026-10-30

```bash
python scripts/eval_retrieval.py --variant all          # the run that produced this table
python scripts/eval_retrieval.py --variant vector --show   # what came back, per question
```

Provenance, so a later reader can tell whether the corpus has moved:

| | |
|---|---|
| Date | 2026-10-30 |
| Corpus | **385 chunks** · `sha256:dd90ea793953` · saoso 338, opp 30, bpp 9, landscape 8 |
| Embeddings | `gemini-embedding-001`, 768 d, all 385 chunks carrying a vector |
| Product budget | `CHAT_RETRIEVAL_LIMIT=8` (so `k=8` is the product's own depth, not a wider one) |
| Set | 35 questions — 32 answerable, 3 refusals; 13 of the 14 distinct `EscalatedQuery` wordings |

**The numbers.** Recall and MRR are over the **32 answerable** questions; the three refusal items are
excluded, because a refusal has nothing to find and counting it as a permanent miss would make the
aggregate lie in the other direction. `grade-0` counts show over-retrieval: a *plausible but wrong*
passage, such as Appendix 2's wood row for a straw question.

| Variant | R@1 | R@3 | R@5 | R@8 | MRR | citation audit | g0 @1 | g0 anywhere | lexical-only |
|---|---|---|---|---|---|---|---|---|---|
| `bare` — the product | **0.188** | 0.594 | 0.719 | 0.812 | 0.388 | 1.000 (280) | 0 | 1 | 0/35 |
| `lexical` — no embedding key | 0.188 | 0.375 | 0.438 | 0.500 | 0.284 | 1.000 (184) | 0 | 0 | 35/35 |
| `vector` — the arm alone | **0.531** | 0.688 | 0.812 | 0.875 | 0.647 | 1.000 (280) | 0 | 2 | 0/35 |

Per-arm attribution on `bare`, over the 32 answerable questions: **lexical 11, vector 7, both 8,
none 6**. Two consecutive runs of `bare` produced identical numbers.

**One caveat for whoever re-runs this, and it bites:** the seat split inside `search_terms` is a
function of `limit` (`primary[: limit - SEMANTIC_SEATS]`, then up to three semantic seats), so a
`--k 5` run is a **different list**, not a shorter one — measured live, `--k 5` reports R@5 0.781
against 0.719 at `k=8` because a fifth of the budget moved from the rare-term arm to the semantic
one. Quote the product's own depth (`k=8` here), and never compare a `--k 5` row with a `--k 8` row.

### What the baseline says

1. **The product finds the answering passage at rank 1 for six questions in thirty-two.** That is the
   number `CHAT_ANSWER_COVERAGE_PRD` has been missing: not "nothing came back" but "the right clause
   arrived eighth". Recall@8 is 0.812, so the corpus usually *contains* the answer and the ordering
   usually buries it. A refusal that says "the standard does not say" is, on this evidence, more often
   a ranking failure than a coverage gap — which is exactly the distinction **Q3** exists to make.
2. **The semantic arm is the stronger arm, and the pipeline hides it.** `vector` alone beats `bare` at
   every cut-off (R@1 0.531 vs 0.188; MRR 0.647 vs 0.388). The mechanism is structural, not
   mysterious: `search_terms` gives the rare-term arm `limit - SEMANTIC_SEATS` = five of the eight
   seats **first**, then fills the last three from the semantic arm, so the semantic arm's best clause
   is rarely above rank 6. This is **Q2's** shape — but it is a *finding to be argued from a mechanism*,
   not licence to re-tune `search_terms` against this set (§4, §7). Recorded, not acted on.
3. **Q1's target row is unreachable today, by either arm.** `how many sheep can I run per hectare?`
   returns no Appendix 6a passage at all on `bare`, and on `vector` returns S2.2.4 and Appendix 6b but
   not `Ewes / 13,3`. `how many laying hens per hectare?` reaches the row at rank 3 on `bare` (rank 1 on
   `vector`). So D73 has a *measured* gap to close, and — importantly for S2 — `vector`-only already
   fails it, which means the improvement D73 is supposed to buy cannot be dismissed as "the arm was
   never going to find it".
4. **The floor test in `knowledge/tests/test_retrieval.py` passes on a question this set marks as a
   miss.** `escalated-gmo-seed-saving` retrieves `S1`-Habitat and §4.8 but never the *Genetically
   Modified Organism* definition; the floor test asserts only "some `S1` chunk came back", so it is
   green. That is §1's argument in one example, and it is why the set grades `contains` and not just
   `locator`.
5. **Unknown-subject questions fail on the proxy word, not on the corpus.** `cardboard` is absent, so
   the rare-term arm searches `boxes` and returns §22.1.6 ("vegetable boxes"); `silica` searches
   `supplementation` and returns the *animal* supplement clause §5.5.6; `without warning` searches
   `warning` and returns the discipline procedure §4.5. All three are plausible-looking wrong answers —
   the failure mode the citation audit cannot catch, because every quote is verbatim.
6. **Quotability is not the baseline problem.** The citation audit accepted **280 of 280** passages on
   `bare` and `vector` (184 of 184 on `lexical`), with no problems at all — so §3.2's "not found but
   quotable" concern is, today, not what is costing answers. Ranking is. (This is a *negative* result
   worth having: it means the next retrieval change does not need to fear the audit.)
7. **Refusals must not be triggered by an empty set.** All **3 of 3** refusal items returned a full
   eight passages — the fertiliser-brand question, the zebra-zoning question and the raw-milk permit
   question. Every one of them is a refusal the *model or the audit* has to make; retrieval will never
   make it. **Q3** answered in the direction that matters: the floor for "the corpus contains this"
   cannot be "something came back", because something always comes back.

### What it does not say

* **It does not answer Q1.** `context` refuses (`--variant context` exits with "needs D73") rather than
  reporting a number for a corpus that does not exist. That is S2's job.
* **The gap in finding 2 is not a tuning target.** Fourteen of the thirty-five items are questions the
  product *refused*, so the set deliberately over-samples the hybrid's failures; a variant that scores
  well on it is being tested on its own preferred ground. Re-tuning `search_terms` until `bare` closes
  the gap would be §7's "overfitting to 30 questions" in its purest form.
* **One `EscalatedQuery` wording is not in the set** — `can I use cardboard from my enighbours?`, a
  typo variant of an item already present. Thirteen of the fourteen distinct wordings is well past the
  §9 threshold of ten; padding the set with near-duplicates would make a small corpus of questions look
  bigger than it is.

### Kill criteria (§6), as they applied

| Condition | What happened |
|---|---|
| Grading > ½ day for 30 questions | Not reached. 35 items graded in a single session, ~25 of them from the corpus artefacts and `locator`s already in `knowledge/`; the spine is `contains` on one locator, not prose judgement |
| Two reviewers disagree on grade 2 vs 1 for > 1 in 5 | Not measurable from one session — recorded as **not yet reviewed by a second person**. The set is committed for exactly that review |
| Fewer than 10 real `EscalatedQuery` questions | Not fired: 13 |
| Adding the instrument changes user-facing behaviour | Not fired: no production module was touched. `knowledge/` gained a data file, `scripts/` two read-only modules, `tests/tools/` one test file |
| The runner and the view disagree | Not fired: `bare` **is** `default_retrieval` (asserted by `test_the_bare_variant_is_the_product_call`), and a source test forbids the runner from calling `search_terms` directly |

## 9. Definition of done

**S1 — baseline (done 2026-10-30):**

- [x] The eval set is committed, graded, and contains ≥ 10 real `EscalatedQuery` questions plus ≥ 1
      `expected: []` item — **35 items; 13 escalations (3 `expected: []`, plus 3 `grade: 0` distractors)**
- [x] Every locator resolves against the ingested corpus, and the runner fails loudly when one does not
      — `resolve()` raises with the item id and the locator; `test_every_locator_resolves_against_the_ingested_corpus`
      ingests all four documents, and was **proved red** by breaking one locator before it was trusted green
- [x] The runner imports the view's retrieval function (asserted by a test), and prints which arm found
      each passage — `test_the_runner_uses_the_product_retrieval_function` and
      `test_the_bare_variant_is_the_product_call`; the report prints `lex1,vec2` per hit and `--show`
      prints every retrieved locator
- [x] **The baseline numbers table is in this file** — §8a, with the corpus digest and the date
- [x] If the set was capped or a kill criterion fired, that is recorded here rather than quietly dropped
      — §8a, "Kill criteria, as they applied" and "What it does not say"

**S2 — the D73 comparison (after the table block lands):**

- [ ] `context` is run on the same set, against the same corpus apart from the intended change
- [ ] Q1 is answered as **A / B / C** with the numbers that produced it
- [ ] The consequence for D73 is applied in `TABLES_AS_DATA_PRD.md` in the same session

---

## Appendix — the nine questions that already exist, and what they miss

`scripts/probe_chat.py::SUITE` is the D17 revision's suite: horse manure, cardboard, straw mulch, the
yearly cost, borax, duck bedding, sign-up, seed saving (×2). It exercises the *input* questions the
group actually receives, which is exactly right — and it has three gaps this spike closes:

1. **No expected answer**, so a change that moves a chunk from rank 2 to rank 7 is invisible.
2. **One table question in nine** ("the yearly cost"), and none about seals, the SAOSO logo, or
   stocking rates — i.e. nothing that exercises a 3-token curated row.
3. **No unanswerable question**, so over-retrieval is unmeasurable.

**All three are now closed, and the suite is still there** — all nine questions were carried into
`knowledge/tests/data/retrieval_eval.json` under `asked_by: probe` (minus the four that are already
`escalation` items, so the set does not double-count a question). `probe_chat.py` keeps its job: it
prints *why* a turn was refused, from the live model. The two instruments answer different questions —
"what did the product do on this question" versus "how is retrieval doing across the set" — and
`tests/tools/test_eval_retrieval.py` asserts that neither re-implements the other's path.
