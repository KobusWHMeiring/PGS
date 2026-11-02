# PRD: Chat answer coverage — governing rules, table rows, and the gaps left

**Status:** In Progress — built 2026-10-21. **UAT signed 2026-10-21 (product owner):** Scenarios 1, 2, 3, 9 and 10 carry a result, with **G8** recorded as an open defect rather than absorbed (see §7). The remaining seats (PGS administrator, committee reviewer, consumer member) are unsigned.
**2026-10-22:** **G8 is closed by measurement**, and the retrieval budget it depended on was wrong in a way nobody had measured — the product was retrieving five passages, not eight (§7 G8, `testing_hazards.md` §2.7). G3, G4, G6 and G7 remain open.
**Owner:** Build — grounded chat (sub-plan D), corpus ingestion (sub-plan B)
**Last Updated:** 2026-11-01
**MVP:** MVP 0 — defect fix and a deliberate widening of D17.
**Scope:** What the assistant may answer, and the corpus behind it. Retrieval query
construction, the answer-mode prompt, and Appendix 2 as reviewed rows. **Not** in scope:
the escalation/contact path (separate Refinement PRD), the classifier, appendices 3–7.
**Reference:** `PGS_PLATFORM_SPEC.md` §18.3 D17/D49/D50/D51;
`knowledge/tables.py`; `CORPUS_COLUMN_EXTRACTION_PRD.md` (2026-10-21 section);
`scripts/probe_chat.py`; `tests/uat/mvp0_standards_and_public_site_uat.md` Scenario 10.

---

## 1. Problem Statement

The assistant refused questions the documents govern. *"Can I use cardboard from my
neighbours?"* returned the D17 refusal while SAOSO 4.4.4 — material applied to land must
comply with Appendix 2 — sat in the corpus. Two independent causes:

1. **Retrieval searched a proxy.** `search_terms` embedded the OR-joined token string
   (`use OR cardboard OR neighbours`), not the question, and the rare-term arm is
   lexical-only, so it searched `neighbours` → wild harvest and child labour. The one
   word that carried the question — `cardboard`, document frequency 0 — was discarded.
   The five chunks that reached the model were S2.4, S23.9, Appendix 1 ×2 and the BPP
   general principles.
2. **The answer mode forbade a governing rule.** Rule 4 allowed only a *definitive*
   answer. A passage that states the rule which governs an unnamed item was refused.

A third defect was found while measuring: Appendix 2's `-layout` text interleaves the
condition column into the substance column, so a faithful quote of the trace-element row
failed the citation audit; and the proximity of the wood condition to the wrong row made a
grounded straw answer say straw must be untreated.

## 2. Strategic Goal

A farmer's everyday question about a named or unnamed input gets either a cited answer
from the documents or a refusal that is true — never an answer that is grounded and wrong.

## 3. Proposed Solution (built)

### 3.1 Retrieval embeds the question (D49)

- `knowledge/services.py`: `search(..., vector_query=)` — the lexical arm keeps the
  rare-term query, the semantic arm embeds the visitor's sentence. One embedding per
  question, unchanged.
- `SEMANTIC_SEATS = 3`: the rare-term arm may not fill the whole budget. Measured: with
  five lexical chunks first, the vector arm contributed **nothing**.
- An out-of-vocabulary term is treated as the subject, not noise: the lexical proxy is
  capped at two chunks and the semantic arm takes the rest. This is the offline-safe
  hedge — with no key, the two lexical chunks still return.
- Chat retrieval budget 5 → 8 — **but this line was wrong until 2026-10-22.** It raised
  `_chatbot.RETRIEVAL_LIMIT`, a fallback that is never read because `settings` always defines
  `CHAT_RETRIEVAL_LIMIT`; the product kept five passages. The live setting is now eight, and
  the cardboard question that motivated the change answers at eight and refuses at five
  (measured 2026-10-22; `testing_hazards.md` §2.7).

### 3.2 The governing-rule answer mode (D50, revises D17)

Rule 4 now: if a passage states a rule that governs the question, answer with it, say
plainly that the document does not name the item, and cite. It still forbids inventing the
missing detail and reasoning from silence; "silence is not permission" is a separate
sentence. Schema unchanged; `PROMPT_VERSION` `d49-1`.

### 3.3 Appendix 2 as reviewed rows (D51)

`pdftotext -table` aligns the appendix's rows where `-layout` cannot (rows overflow the
gutter). `knowledge/tables.py` holds 30 reviewed rows, one chunk each, so a substance and
its condition are one quotable passage. `ingest_standard(force=True)` /
`--force` re-ingests unchanged bytes, deleting inside the transaction after embedding.
Assumptions are listed in `knowledge/tables.py` and in the PRD's 2026-10-21 section.

## 4. Technical Requirements

1. No migration. Rows are ordinary `DocumentChunk`s with `section_ref="Appendix 2"`.
2. `knowledge` still never imports `core`; `scripts/probe_chat.py` is developer tooling.
3. A quote covering a whole row is accepted; the audit is unchanged.
4. The two lexical decisions remain measured and pinned: rare-term-first for known
   questions, semantic-first when the subject is unknown.
5. A reprint of Appendix 2 fails `knowledge/tests/test_tables.py`, not silently.

## 5. Evidence (live, round 3)

`scripts/probe_chat.py`, after a forced re-ingest (321 SAOSO chunks, embedded):

| Question | Result |
|---|---|
| horse manure | grounded, row-level Appendix 2 citations |
| cardboard | grounded; cites the biodegradable by-products row and its contaminants condition |
| straw mulch | grounded and correct (was mispaired with wood's condition) |
| borax | grounded (was an audit refusal) |
| cost incl. visit | grounded; **omits the R100 annual membership fee** — §2.1 not retrieved |
| ducks / bedding compost | **refused** — S5.5.1 enumeration |
| how do I sign up | grounded |
| seeds saved from non-organic seed | grounded |
| seed grown organic | **refused** — S4.1.1 paraphrase |

**Round 4 (2026-10-22, after D52).** The two refusals above were the *corpus's* fault,
not the chunker's: `pdftotext -layout` had broken a line inside a hyphenated word, so the
stored sentence was `per non-` / footer / `ruminant` and no quote of the printed sentence
could pass the audit. `knowledge/reflow.py` rejoins the word and the printed page footer
is now furniture; re-ingested (366 chunks, all embedded) and re-probed:

| Question | Round 3 | Round 4 (D52) |
|---|---|---|
| ducks / bedding compost | refused (quote + `sub_ref a`) | **grounded**, 4 citations (S5.5.1, Appendix 2 ×2) |
| seed grown organic | refused (paraphrase) | **grounded**, 2 citations (S4.1.1, S4.1) |

The prompt was not changed, and the audit was not relaxed. `PROMPT_VERSION` stays
`d49-1` because the cache key already carries `_corpus_fingerprint()`.

## 6. Success Criteria

- [x] Cardboard answers with a governing rule and a citation, or refuses for a true reason.
- [x] Straw is not given wood's condition.
- [x] Borax quotes the trace-elements row.
- [x] A whole row is one citable passage; `Audit: grounded`.
- [x] The ducks question (`S5.5.1`) and the seed question (`S4.1.1`) are grounded, with
      every quote found on the page (D52, round 4).
- [x] `verify.sh` green (619), `lint-imports` kept.
- [ ] **UAT Scenarios 1, 2, 3, 9 and 10 signed.** Unsigned ⇒ this PRD is partial.
- [ ] The corpus is re-ingested with `--force` on the deployment (see §8).

## 7. Remaining gaps — the queue for the next agent

Each is independent; do not bundle them into one change.

### G1. An enumerated clause cannot be quoted whole (`S5.5.1`)

**Closed 2026-10-22 (D52). Measured cause was the corpus, not the chunker.** The section
is one 326-token chunk that already carries the lead-in and items a–d; what it did *not*
carry was the printed sentence. `pdftotext -layout` had wrapped `non-ruminant` across a
line break and the page footer `P a g e | 47` sat inside the clause, so the stored text was
`… per non-` / `P a g e | 47` / `ruminant …`. The model could not quote it without writing
`non- ruminant`, and it elided with `...` instead — which the audit refused, correctly.
`knowledge/reflow.py` rejoins the word and `PAGE_FOOTER` is now furniture. Re-probed:
grounded, 4 citations. Pinned by `knowledge/tests/test_reflow.py`,
`knowledge/tests/test_ingest.py` and two live-reply tests in
`core/tests/test_chatbot_grounding.py` (the verbatim sentence accepted, the recorded
elision still refused). *Original diagnosis, kept for provenance:*

**Symptom.** *"If my ducks aren't fed organic food and I make compost from their bedding,
will I still pass?"* → audit refused: the model wrote *"…under specific conditions in
a, b and c below"* and cited `sub_ref: a` / `b`, which are in other chunks. The answer was
substantively right and was refused for an uncheckable citation.

**Why.** The chunker splits `a`, `b`, `c` into separate chunks; the lead-in sentence stays
with item `a`; the prompt's "one contiguous excerpt" rule then makes any summary
uncitable.

**Acceptance:** the ducks question is grounded, every citation's quote is found on the
page, and a test pins the `S5.5.1` chunk that carries the lead-in plus its first item.
Measure before choosing between (a) chunking the enumeration with its lead-in and (b) a
prompt rule that forbids summarising an enumeration.

### G2. A paraphrase of a long enumeration (`S4.1.1`)

**Closed 2026-10-22 (D52) — same corpus cause, not a long-chunk problem.** The chunk is
178 tokens and fits the target comfortably; the defect was `post-` / `harvest` wrapped
across a line break, which made the printed sentence unquotable. After the reflow the
model quoted the paragraph verbatim and the audit grounded it (2 citations). No prompt
rule was needed, so none was added. *Original diagnosis, kept for provenance:*

**Symptom.** *"If a seed is not organic but I grow it organic will the crop be organic?"*
→ audit refused; the model paraphrased the conventional-seed exception instead of quoting
it. Same class as G1, different section. Check whether the `S4.1.1` chunk is too long to
quote, or whether the prompt needs the enumeration rule from G1.

### G3. A multi-part cost question misses a sibling section (`§2.1`)

**Symptom.** *"What is the yearly cost to get certified, including the farm visit?"* is
grounded with §2.2, §2.3 (sliding scale + transport), §2.4 (R30 catering) and §2.5 (R500
licence) — but **not** §2.1, the R100 annual membership fee. Six seats went to the visit
and licensing text.

**Why.** Retrieval has no notion of a section family. The question names "cost" and
"certified"; §2.1 says "Membership Fees", which shares no rare term.

**Acceptance:** the answer names the membership fee and the assessment/visit fees together,
each cited. Options to measure: a sibling-section expansion (if a §2.x chunk is retrieved,
add its siblings) vs. a prompt-side "cost question" checklist. Do not widen the retrieval
limit blindly; that trades this defect for noise.

**Re-measured 2026-10-22 at the corrected budget (8):** still open, and now with clean
evidence — the answer is grounded with five citations (§2.3 ×4, §2.5) and never mentions
§2.1's R100 annual membership fee. Retrieval returns `r500`, §2.3, §2.4, §2.2, `pgs-sa`,
`saoso-organic-certification`, §2.5 and §4.1; §2.1 is not in the set at eight either.

**Closed 2026-10-27 — and the diagnosis above was wrong twice.** The measurement was made
through `default_retrieval`, whose lexical key for this question was `get` (document
frequency 1), so the retrieval set was one chunk of `r500` plus the OR arm; and §2.1 shares
**no word** with the question at all — the OPP calls it *Membership Fees*, while the
question says *cost*. So the gap was never "no sibling-section expansion": it was a bad key
(F1 in `CHAT_TRUTHFULNESS_PRD.md`) plus a missing alias (`cost -> fee`). Both are now in
`knowledge/services.py` and `knowledge/aliases.py`; the alias arm searches `fee` alone,
because `cost OR fee` loses §2.1 again (measured). After: §2.1 is seat 8 of 8, and the
answer opens with *"an annual farmer and consumer membership fee of R100"*, then the
assessment and licensing fees — **5 citations, 5 audited, grounded**. That is this gap's
acceptance criterion, met without the sibling-section expansion.

**The lesson worth keeping:** a re-measurement taken through a retrieval path whose key is
wrong produces an architectural conclusion ("add siblings") for a lexical defect. Check the
key before believing the shape of a gap.

### G4. Appendices 3, 4, 6a/6b and 7 are still on the interleaved path

**Symptom.** The same class of defect as Appendix 2 — a condition or limit printed in a
second column — is unaddressed for crop protectants (Appendix 3), additives (Appendix 4
Table 1), stocking densities (6a/6b) and winemaking (7).

**Acceptance:** each appendix that carries a condition gets a reviewed `TABLE_ROWS` entry
and golden tests, same mechanism and the same assumptions as `knowledge/tables.py`. Start
with Appendix 3 and Appendix 4 Table 1: they answer input questions. Update
`CORPUS_COLUMN_EXTRACTION_PRD.md §3.5`, which currently says table rows are not
reconstructed (true only for the appendices not yet reviewed).

### G5. The classifier stays deferred — with a written trigger to reopen

Do **not** add an OpenRouter/LLM router on current evidence. It would not have fixed any
round-3 failure: all three original refusals were corpus/chunking, and the one wrong answer
was a row pairing. Reopen only when a suite question retrieves the **wrong section** (not
an audit refusal), and then decide between expansion terms from the corpus vocabulary and a
seeded alias table (`cardboard → mulch, plant material, contamination`) before a model
call. A label such as `inputs` re-encodes the standard's structure in code (§I forbids it)
and a wrong label hides the right passage.

### G6. The human answer path is still a dead end

`EscalatedQuery` is written on every refusal, but *"Send this question to the
administrator"* goes to `/contact/`, which renders `email`, `phone` and
`contact details to confirm` chips — placeholders with no address, no form, and no way to
track or receive an answer. This is **not** part of the machine-answer work; it is
`product/backlog/Refinement/ESCALATION_ANSWER_PATH_PRD.md`. Do not close the refusal
feature without it: the refusal currently promises a person who cannot be reached.

### G7. A spanning line is still emitted as consecutive fragments (BPP)

**Found 2026-10-22 while closing G1/G2.** The BPP general-principles page has one line
that carries text on both sides of the gutter — `The use of synthetic fertilisers (agro-
            and thereafter further tests may be` — so `de_column` keeps it whole (by
design, D46) and `HeadingParser` then splits it at `COLUMN_GAP` into two body lines. The
stored chunk reads `… (agro-` / `and thereafter further tests may be` / `chemicals) is
expressly prohibited.`, which is the left and right columns interleaved. A quote of the
left column's real sentence therefore still fails the audit. Three chunks carry this
shape today; no line-join can repair it, because the two halves are different sentences.

**Acceptance:** a question about synthetic fertilisers quotes the prohibition contiguously.
This is the same class as Appendix 2 (a spanning line needs row/cell reconstruction), so
the likely fix is a reviewed line or a narrower band override for that page — measure
before adding either.

### G8. The model cites one sentence twice, and the second citation is a paraphrase

**Found 2026-10-20 while bringing the MVP 0 UAT up for sign-off. This one blocks the
sign-off itself**, because it makes UAT Scenario 1 (*"Does the chatbot answer from the
standard?"*) refuse on its own question, reproducibly.

**Symptom.** Through `/ask/` and through `answer_question()` directly, five consecutive
attempts on *"What does the standard say about the minimum rest period for laying hens
without artificial light?"* return D17's refusal. `cached=False` on every attempt, so this
is not the answer cache (that defect is fixed and pinned — see `testing_hazards.md` §1.31).

**Measured cause.** The model returns two citations for **one** sentence:

```
S5.1.9              "For laying hens, a minimum daily rest period of 8 continuous hours …"   audit: ACCEPTED
general-principles  "For laying hens, a minimum daily rest period of eight continuous hours …"  audit: REJECTED
                    ^ a paraphrase of the sentence above, and: sub_ref 'd.ii.' does not exist in the chunk
```

The all-or-nothing audit refuses the pair — correctly; trimming the bad one is exactly what
D47 forbids. So the refusal is the product working. The defect is the model's citation.

**What it is *not* — each excluded by measurement, not by inspection:**

| Suspect | Evidence it is innocent |
|---|---|
| The corpus | `S5.1.9` is in the retrieved set (rank 2) and its sentence is quoted **verbatim** by the accepted citation |
| Retrieval | the `general-principles` chunk *the model chose to cite* is in the five passages it was given, and in the stored `retrieved_chunks` |
| The cache | every attempt shows `cached=False`; deleting the key changes nothing |
| The audit | it accepted the correct citation and named the invented `sub_ref` exactly |
| The chunker / D53 artefact | no quote is mangled; the failing quote is a *paraphrase the model wrote*, not text from the file |

**The likely trigger is prompt rule 7.** It says the Basic Production Principles are
guidance and *"When both answer, prefer the governing document for a question about a
requirement or procedure, and **name the document you are citing**"*. The model reads that
as "cite both", and adds a BPP citation for a sentence it took from SAOSO. Note that
`build_prompt` already tells it, for that very passage, `Numbered sub-clauses available:
none — omit sub_ref for this passage`, and rule 5 already forbids inventing one. The
instruction is present and the model overrides it, so the fix is wording that removes the
*invitation*, not another prohibition.

**Candidate fix A (preferred): prompt wording + `PROMPT_VERSION` bump.** One citation per
statement; never cite a passage whose words you did not take verbatim; if naming a second
document helps the reader, name it **in the answer text**, not as a citation. Bump
`PROMPT_VERSION` (the answer cache is keyed on it) and re-measure.

**Candidate fixes rejected:**

- *Drop a duplicate citation after the fact.* That is "trim a bad citation and keep the
  rest" — D47 exists to forbid it, and it would let a paraphrased quote through whenever it
  happens to be first.
- *Relax the `sub_ref` check.* The audit is the product; a citation nobody can verify is
  the failure mode the whole design is built around.
- *Add a classifier or a repair model call.* Same answer as G5.

**The instrument needs fixing too.** `scripts/probe_chat.py` **looks fine** on this question
— it prints a grounded answer with one audited citation — because it retrieves with its own
limit (8), and the failing `general-principles` citation only appears in the product's
`CHAT_RETRIEVAL_LIMIT` (5). A probe that measures a different retrieval path than the
product is the "test passes for the wrong reason" pattern. Give the probe the chat limit (a
`--limit` flag defaulting to `settings.CHAT_RETRIEVAL_LIMIT`) **before** tuning the prompt,
or the measurement will say the fix worked when it did not.

**Acceptance:**

1. `python scripts/probe_chat.py` with the chat limit reproduces all five refusals *now*.
2. After the change, that question answers with at least one verbatim citation through
   `/ask/`, **five consecutive fresh sessions** (the model is stochastic; one green run is
   not evidence).
3. The nine-question suite has no new refusals, and no already-grounded question regresses
   (G1/G2's ducks and seed questions, `can i use straw mulch?`, the manure question).
4. `PROMPT_VERSION` is bumped, and the diff contains **no** change to `audit_citations`.

### G8 — closed by measurement, 2026-10-22

**The refusal no longer reproduces, and the reason is not a prompt edit.** Three things were
done, in this order, because the diagnosis could not be trusted until the instrument was.

1. **The instrument was fixed first.** `scripts/probe_chat.py` now takes `--limit`, defaulting
   to `chat_retrieval_limit()`, and retrieves through `core.services._chatbot.default_retrieval`
   — the function `answer_question()` calls. It has no retrieval call of its own, and
   `tests/tools/test_probe_chat.py` fails if one comes back.
2. **The budget was measured, and it was wrong.** `settings.CHAT_RETRIEVAL_LIMIT` was **5**,
   not the 8 this PRD recorded: the 2026-10-21 change landed on `RETRIEVAL_LIMIT`, a
   `getattr` fallback that `settings` always shadows. At 5 the Scenario 1 question retrieves
   *two* `general-principles` chunks, and the model cites the hen sentence from both; at 8 it
   cites `S5.1.9` once. The same defect refused **cardboard** in production (no inputs clause
   in a five-chunk set) — the question §3.1 raised the budget for in the first place.
   The live setting is now 8 and `PROMPT_VERSION` is `d49-2`, because every cached answer had
   been produced against a five-passage set (`testing_hazards.md` §2.7).
3. **Then it was measured, not assumed.** With the corrected budget, five consecutive fresh
   runs of Scenario 1's question each returned a grounded answer with **one** verbatim
   `S5.1.9` citation, and the nine-question suite returned **9/9 grounded** (limit 5, before
   the fix: 7 grounded, cardboard refused, the cost question truncated). No prompt rule was
   changed: rule 7 is unmeasured churn once the failing case is gone, and the acceptance
   tests above now pass as written.

**Residual, recorded rather than absorbed.** At limit 5 the model's second citation was
*accepted* — it quotes `general-principles` with "eight" spelled out, and the D53 BPP
artefact happens to spell it that way. That is corpus luck, not a looser audit; if the BPP
said "8" the same paraphrase would refuse again. If the duplicate citation returns, candidate
fix A (one citation per statement; name a second document in the answer text) is the remedy,
measured against the five-run rule above.

**Blocks:** MVP 0 sign-off (`tests/uat/mvp0_standards_and_public_site_uat.md` Scenario 1),
and by the same rule likely Scenarios 2, 3, 9 and 10 — all five are chat scenarios and all
five are unsigned.

### G9. The model cites the passage header, and the audit refuses a correct answer

**Found 2026-10-22 on the live site**, the day the corpus was rebuilt: *"can i use borax
powder?"* answered *"I cannot find a definitive answer in the SAOSO standard or the Outeniqua
PGS documents."* The answer exists — SAOSO Appendix 2 lists **sodium borate** as a trace
element, restricted to documented deficiency — and the product had found it.

**Located with `scripts/why_refused.py` (written for this), not by guessing:**

```
corpus*1  'borate'        -> the live corpus has the row, in full
retrieved(8): 6 of 8 are Appendix 2   -> retrieval reached it
#1/#2  CITATION_AUDIT     -> the model answered, the audit refused the citation
```

Then `probe_chat.py` on the box named the refusal exactly:

```
citations: 1 raw, 0 audited
  raw  Appendix 2 — SAOSO Standard for Organic Production and Processing v2.1 | Trace elements, …
AUDIT: REFUSED
  ! Appendix 2 — SAOSO Standard … v2.1: not present in the retrieved set
```

**Cause, and it is not the model's.** `build_prompt` printed each passage as
`[6] Appendix 2 — SAOSO Standard for Organic Production and Processing v2.1, page 77`, gluing
locator and document label together with an em dash while rule 2 said *"cite the exact locator
printed for that passage"*. The model copied the header; the audit had never been given that
string. Not corpus, not retrieval, not the cache (the key carries a corpus fingerprint, so no
pre-refresh reply can be served — and the count moved 363 → 364 anyway). Non-deterministic
too: the dev box answered the same question with 2 audited citations on the same day.

**Fixed on both sides, because the formatting must not be able to hide an answer again.**
`d49-3`: each passage prints `LOCATOR:` on its own line with `Document:` beneath, rule 2 says
`section_ref` is the value after `LOCATOR:` and *nothing else*, and `_normalise_ref` treats
everything from a dash on as decoration. That last part is format tolerance, **not** a looser
audit: the key must still resolve to exactly one stored locator, the quote must still be a
substring of that chunk, and `sub_ref` must still exist — `test_a_decorated_locator_that_is_
ambiguous_still_refuses` pins that a two-locator key still refuses. Guards were broken and
watched go red before being trusted: removing the decoration strip fails both audit tests,
removing `LOCATOR:` fails the prompt test.

**Verified:** gate 808 green; `probe_chat "can i use borax powder?"` now returns *"sodium
borate, which is chemically known as borax, can be used as a trace element… restricted to
where a deficiency is documented"* with **2 raw, 2 audited, `AUDIT: grounded`**.

**Verified live, 2026-10-22.** After deploying `70ae120` the product owner reports `/ask/`
answering the borax question as expected (sodium borate, restricted to a documented
deficiency, citing Appendix 2). The refusal that started this — identical sentence to a coverage gap — is gone.

**Residual risk, recorded rather than absorbed.** The model is stochastic, so one green run
proves the format is no longer an obstacle, not that the class is gone. A different decoration
(the page number instead of the title, the version alone) would still refuse until the
`LOCATOR:` line is the habit — five fresh sessions on the box is the acceptance test, the same
rule G8's closure used.

**Feeds:** `CORPUS_CANONICAL_FORMAT_PLAN.md` **P2.5a** — the three records this
investigation had to reconstruct by re-asking the model (`citations`, `refusal_checks`,
and a grounding snapshot that survives `--force`).

**Blocks:** nothing now. It refused a correct answer on a live public surface for as long as
the box held the refreshed corpus — hours, not days, because the corpus only reached the box
today. It would have been invisible forever without `why_refused.py`.

### G10. The same fee question is answered three ways, and one answer in five is refused — **found 2026-11-01**

**Reported by the product owner**, reading `/ask/` and then the citation it gave: *"when I ask what
the yearly cost is it only mentions the R100"*, and §2.3 — which they then opened — *"looks like
there should be a table involved, it doesn't read great"*.

**Measured**: five runs through `scripts/probe_chat.py` (the product's own path), dev box, 394
chunks, 2026-11-01.

| Question | Answer | Citations |
|---|---|---|
| *"What is the yearly cost to get certified, including the farm visit?"* — the eval set's own wording | complete: membership, assessment (all six bands), transport, licence | 5 audited, **grounded, 3 of 3 runs** |
| *"what does it cost to join"* | complete: §2.1, §2.3, §2.4 | 5 audited, grounded |
| *"what is the yearly cost of membership"* | **membership only** — R100 + R500 | 3 audited, grounded |
| *"what is the yearly cost"* | run A **REFUSED** (7 raw / 6 audited); run B complete (10 raw / 8 audited) | — |

**Retrieval is not the cause, and that is the part worth keeping.** For the question the top eight
clauses are §2.3 (rank 1), §2.4 (2), §2.2 (3), §2.5 (4), §2.6, §4.7, **§2.1 (7)**, §4.6 — every
locator `escalated-yearly-cost` grades is in the set. So **G3's acceptance criterion holds only when
the question names certification or the visit**, and fails when it names membership alone. That is
faithful to the question rather than a retrieval defect, which is a different thing from G3 and
should not be closed as a re-open of it.

**Second finding, and it is not located.** One of the two *"yearly cost"* runs produced ten
citations of which two failed verification, and the product **refused a correct answer** — the
user-visible outcome G9 describes, from a cause I did not capture before the session ended. It is
not the G9 header-decoration cause (that fix holds; every audited citation in the good runs is a
`§2.x` locator with no decoration). Reproduce with `scripts/why_refused.py "what is the yearly
cost"` and `scripts/probe_chat.py "<the same>"`, which is how G9 was named — do not guess at it.

### G11. The owner read the cost answer and two more defects fell out — **found 2026-11-01**

The product owner read the *fixed* cost answer and said two things, and both were right:

1. *"the R500 was what PGS Outeniqua pays to SAOSA yearly, not what the individual members
   pay"* — §2.1 says so in its own words: *"PGS South Africa membership fee: the group will
   pay the annual membership fee to SAOSO. The funds for this national membership will be
   secured from our membership fees set out in 1."* The R100 is the member's; the R500 is the
   **group's**, funded out of the members' fees. The first rule listed it inside "the yearly
   cost of membership" anyway, so a reader could not tell whose money it was.
2. *"a user needs to have a farm visit to be certified, so that fee should be included in the
   yearly cost calc"* — and the public page already publishes that shape:
   `FIRST_YEAR_FROM_CENTS` = **R1 600** (R100 membership + the R1 500 lowest assessment band),
   *"a floor, not a total"*, with its three exclusions named. The assistant said neither that
   the assessment fee is unavoidable nor any floor, and the first version of the rule had
   **forbidden every total** — so the site and the assistant disagreed in the one place the
   owner had asked them to agree.

**Fixed the same day (`d78-2`).** The rule is now three parts, in order: **whose** amount it
is (a member's vs the group's, never presented as an extra charge), the **unavoidable** part
(the assessment fee applies to every farm entering or renewing, so the membership fee alone is
not the cost of being certified), and the **conditional** part (travel, catering, the licence).
It also permits **one** sum: the membership fee plus one named band, *called a floor*, with
what it leaves out named. Measured after: *"…which is secured from the group's collected
membership fees and **is not an additional charge to the individual member**"*, and the
assessment fee named as applying to every farm entering or renewing.

**Two blockers remain, and they are linked — both measured, neither fixed.**

- **A table row can never be retrieved.** `Below R 250,000 / 1,500 / 900` shares no word with
  any question, so the row is **vector-only by construction**. `SEMANTIC_SEATS = 3` exists for
  exactly that, but the seats are taken from the *fused head* (chunks the lexical arm already
  ranked) and the alias arm (`cost → fee`, G3's fix) then truncates the tail, so the
  reservation is spent and lost. Measured: the six bands rank **4th–13th in the vector arm and
  nowhere in the top eight**, and `/ask/` answers *"the specific scale is not provided"* for a
  scale the document prints next to it. **Fixed in the vector, not yet in the seat** — see the
  next bullet.
- **A row's labels cannot be quoted.** D73's vector half was built in this session (a table
  row is embedded from a `column: value` rendition, stored on the chunk), and with the seats
  enforced by hand the model *did* read a band correctly (*"a farmer with an annual farm
  turnover between R 500,001 and R 1,000,000 pays a renewal fee of R 2,500"*). But the labels
  are metadata the paper does not print, so the model quoted **them**, and the audit refused —
  correctly. A label line in the prompt is a quote trap; the same lesson as D50-1's passage
  number.

**Generalisation explored 2026-11-02 — `product/design/g12_ingestion_generalisation.html`.** The
engine's coverage today is *however many tables a person has typed*: 44 reviewed rows across four
documents, four bespoke test files, and **two tables still mangled** (SAOSO Appendix 6a ships 20
chunks with no column meaning; Appendix 7 is interleaved). That page's Part 1 is an eight-shape
test set built from our own corpus, Part 6 recommends a structure extractor emitting the same
artefact IR plus an automated verification harness, and G11's **option E** comes out of it.

**Explored 2026-11-02 — `product/design/g11_row_labels_exploration.html`.** Four options with their
evidence and costs, the recommendation (A: the printed header line becomes part of each row's chunk
text, plus the reserved seat), and the literature that disagrees with A. **Undecided**; the page
exports the §18.3 row when it is answered.

**What the next slice has to decide, therefore, is one thing:** how a printed header reaches a
row's *quotable* text. The candidates are (a) the printed column-header line becomes part of
each row's chunk text — it is the paper's own words, printed once above the table, and Appendix
2 already restores printed part headings from reviewed data; (b) the reader/answer cites the
whole table section instead of a row; (c) the assistant does not attempt the band and says the
scale is in the OPP, which is what it does today and is honest but unhelpful. **With (a), the
reserved seat and the floor both work**; without one of them, P4's table is a reader feature and
not a chat feature, and G10's "align the two" stays half done.

**Also measured, and worth keeping:** D73's rendition is for rows whose cells are **numbers**.
Applying it to Appendix 2's reviewed literals — whose cells are already prose — took the probe
suite from 9 of 9 grounded to **6 of 9** (horse manure, cardboard and ducks all refused), so
`TableRow.as_chunk()` deliberately sets no rendition. One shape for both storages would have
been tidier and worse.

**The second finding is located, 2026-11-01 — and it is one space, not a paraphrase.** Reproduced
twice on the same question (`probe_chat`, 401-chunk corpus, after both fixes): the answer was
complete and correct, one citation failed, and the product refused it. The failing quote:

```
passage: … from our membership
         fees set out in 1.
         o Currently R500
quote  : … from our membership fees set out in 1.o Currently R500
                                             ^ one space missing, at the line break
```

`audit_citations` compares `flat()`-normalised text, so the passage's newline is a **space** and
the model's `1.o` is not. Whitespace-*removed*, the quote is an exact substring — the model copied
the words and joined a line break without a space, which is what a line starting with the `o`
bullet invites. So **G10's second finding is not the model inventing anything and not the corpus**:
it is the audit's normal form meeting a line-wrapped passage.

Two candidate answers, and the choice is the third item below, not a build decision:

- **Compare whitespace-insensitively** (`squash`, as the corpus traceability tests already do).
  Catches paraphrase and invention exactly as now — the words and their order are still compared —
  and stops refusing an answer for a missing space. The cost: a quote could also match with spaces
  removed *between* words, which is a display defect, not a grounding one.
- **Leave the audit alone and improve the passage**, if a narrower corpus-side cause is found. None
  was: the two lines are printed on two lines, so joining them in the artefact would be a
  transcription error, not a repair.

Do **not** change either without writing the answer in §18.3 first (the rule this PRD already
sets). Note the ordering that matters: the refusal costs the visitor a correct answer, and the
`EscalatedQuery` it writes says `CITATION_AUDIT`, which reads to an operator as "the model made
something up".

**The instrument cannot see either.** `eval_retrieval` grades **locators**: on this question it is
green while the answer narrows and while one run in five is refused. G3's acceptance criterion is an
answer-level sentence with no automated assertion behind it — the same residual-risk shape as G8 and
G9, and the reason this is filed here rather than closed.

**Neither fix is "more corpus."** Two changes, in this order:

1. **A cost-question answer rule.** When a cost question does not name a component, state the
   components and say what cannot be totalled. The **public page already publishes this shape** —
   C1f's `FIRST_YEAR_FROM_CENTS` is *"a floor, not a total"*, with its three exclusions named — so
   the site and the assistant currently disagree in spirit, and this aligns them. Testable at
   answer level across the four phrasings above; do **not** widen the retrieval limit to chase it
   (G3's own warning: that trades this defect for noise).

   **Landed 2026-11-01 — D78, `PROMPT_VERSION` `d78-1`.** A rule rendered **only for a cost
   question**: the model is told to state every component the passages supply and what they leave
   out, and never to present one component as the price of the whole. Two choices are worth keeping:

   - **The rule names no section reference and no amount.** A rule that volunteered `§2.3` or
     `R100` would invite a citation retrieval did not supply, and the audit refuses the whole
     answer for one of those — F3's lesson, and the shape of this gap's own unlocated refusal. The
     components are the documents' categories; the money belongs to the passages.
   - **The rule is conditional, not in `SYSTEM_PROMPT`.** On every other question it is prompt
     tokens paying for a disclaimer nobody asked for.

   `cost_question_warnings()` is the tripwire for when the prompt stops working: a cost answer whose
   text contains no limit phrase is written to `ChatMessage.review_notes`. It **never refuses** —
   advisory, exactly like `outcome_claim_warnings`, because G10's second finding is that a refusal
   and "the corpus cannot answer" look the same to the visitor.

   **Re-measured 2026-11-01, same corpus (394 chunks), after the rule:**

   | Question | Before | After |
   |---|---|---|
   | *"what is the yearly cost of membership"* | membership only, 2 citations | **complete** — R100, the scale, transport, catering, the licence; 6 audited, grounded |
   | *"what is the yearly cost"* | complete (1 run of 5 refused) | complete, 8 audited, grounded |
   | *"what does it cost to join"* | complete | complete, 7 audited, grounded |
   | *"What is the yearly cost to get certified, including the farm visit?"* | complete | complete, 8 audited, grounded |

   The default probe suite is **9 of 9 grounded** afterwards, including cardboard and the rest-period
   question, so the added rule cost no other question its answer. **The second finding is still
   open and still not located** — one run in five refused on *"what is the yearly cost"* and it did
   not reproduce in this session's runs; reproduce with `scripts/why_refused.py`, do not guess.

   **The R900 the old answer gave was this same defect, one layer down.** Before the rule, the
   membership phrasing answered "farms with an annual turnover below R250,000 pay a renewal fee of
   R900" — the model was guessing which of two unlabelled numbers in the column soup was the
   initial fee. §2.3's reviewed table (below) is what fixes that, which is why the two changes are
   one report rather than two.
2. **P4 — the OPP artefact with §2.3 as a `layout: grid` table.** The reader-side half of the same
   report: the sliding scale is one **1,613-character** PDF-parsed chunk whose columns are spaces,
   and HTML collapses them, so six turnover bands render as prose. `CORPUS_CANONICAL_FORMAT_PLAN.md`
   P4; the parser, both layouts and the resizable spreadsheet are built (`LANDSCAPE_TABLES_PRD`
   §12g), so what is missing is the artefact and one hand-written table block.

   **Landed 2026-11-01, the same day.** `knowledge/corpus/opp.md` is the OPP's text of record and
   §2.3 is a reviewed grid — three printed columns, six bands, one chunk per band (OPP **30 → 37**
   chunks, all four governed documents now artefact-backed). The format needed a **`<!-- sub: … -->`
   marker** on the way: without it the conversion silently dropped `4.5(1)`, `4.5(2)(c)` and
   `4.5(4)`, and 24 sub-clause spans are now asserted to quote the same words the PDF path quoted.
   **The ambiguity this PRD opened with is gone at its cause:** before, the model answered "farms
   with an annual turnover below R250,000 pay a **renewal** fee of R900" — the R900 is the renewal
   column, and the two numbers had no labels in the chunk. After, it answers "initial certification
   … ranging from R1,500 to R8,000, and for renewal … R900 to R8,000", grounded.
   `CORPUS_CANONICAL_FORMAT_PLAN.md` P4 carries the full record.

**Third, a decision rather than code.** When one citation of ten fails, the product refuses the
whole answer. That is deliberate (a claim must be grounded), but the user experience is
indistinguishable from "the corpus cannot answer this", and G9 showed how expensive that confusion
is. Decide: refuse everything, or drop the unverified sentence and answer. Write the answer down in
§18.3 before changing the behaviour.

## 8. Deployment note

`ingest_standard` is a no-op when the PDF's sha256 is already stored, so **shipping this
code does not update a deployed corpus.** After deploy, run once per governed document,
deliberately (it drops `retrieved_chunks` links and re-embeds). D52 touched **all four**,
not only SAOSO: the hyphen reflow applies to every page, so a partial re-ingest leaves the
OPP's `inter-member`, the BPP's `on-farm` and the landscape's `self-assessment` mangled.

```bash
python manage.py ingest_standard --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf --force
python manage.py ingest_standard --doc opp --file "pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf" --force
python manage.py ingest_standard --doc bpp --file "pgs_docs/Basic Production Principles_ENG_PRINT.pdf" --force
python manage.py ingest_standard --doc landscape --file "pgs_docs/PGS Certification landscape_Final.pdf" --force
```

The answer cache needs no manual invalidation: its key carries `_corpus_fingerprint()`
(chunk count, max id, document sha list), so a re-ingest cannot leave a stale grounded
answer behind. That is also why `PROMPT_VERSION` did not change for D52.

Do **not** add `--force` to `deploy.sh`: a re-embed of the whole corpus on every deploy is
neither free nor necessary.

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| The governing-rule mode sounds permissive | "Silence is not permission" in the prompt; UAT asks the human whether the answer reads as permission |
| A curated table drifts from a reprinted standard | `test_tables.py` checks every cell against `-table`; `TABLE_BANDS` is measured data |
| A row chunk is not a page slice | Documented exception with the reader check ("find the row"); audit still requires a substring |
| Force re-ingest is used casually | Command help states the `retrieved_chunks` cost; not in `deploy.sh` |
| The classifier is added as a reflex | G5 states the trigger and the measurement that must precede it |

---

## Pre-Flight Checklist

- [x] Models changed? **No** — no migration.
- [x] Services in the correct module? `knowledge/services.py`, `knowledge/tables.py`, `core/services/_chatbot.py`.
- [x] Views touched? **No** — the chat view is unchanged.
- [x] Tests added to the correct files? `knowledge/tests/test_retrieval.py`, `test_tables.py`, `test_ingest.py`, `core/tests/test_chatbot_grounding.py`.
- [x] Migrations? **None.**
- [x] `select_related` / `prefetch_related`? Unchanged retrieval already uses `select_related("document")`.
- [x] `transaction.atomic()` for multi-table writes? Ingest already wraps the write; `force` deletes inside it.
- [x] No logic in templates.
