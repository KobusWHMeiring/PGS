# PRD: Chat truthfulness — a refusal that names its cause, and an answer that claims no more than it cites

**Status:** Refinement — findings recorded 2026-10-27 from a four-turn live conversation. **5.1, 5.2, 5.3, 5.5, 5.7, 5.8, 5.9 and 5.10 landed the same day** (gate green at 920): every refusal in that conversation answers, the two GM-outcome turns state the rule instead of the verdict, G3 is closed, and a definition citation lands on the definition. Remaining: D-2's re-measure on the box, 5.6 (the follow-up window, needs S6), and the box sweeps.
**Owner:** Build — grounded chat (sub-plan D)
**Last Updated:** 2026-10-27
**MVP:** MVP 0 — defect fix. No new surface, no migration.
**Scope:** The refusal's *attribution* (why the visitor is told the documents are silent) and the answer's *scope* (what a grounded answer may claim beyond its quote). Retrieval key selection, passage-header formatting, `sub_ref` discipline, the claim-scope rule, and the follow-up inheritance that widens it. **Not** in scope: the escalation/contact path (G6), the appendices (G4), the classifier (G5), the output-token cap (in flight elsewhere, §7), and any corpus rebuild.
**Reference:** `CHAT_ANSWER_COVERAGE_PRD.md` (G1–G9; this PRD adds G10–G13), `ASK_SURFACE_PRD.md` §7 item 2, `PGS_PLATFORM_SPEC.md` §18.3 (D17, D47, D49–D51, D61, D67), `product/docs/context/testing_hazards.md` §1.31/§2.7, `scripts/probe_chat.py`, `scripts/why_refused.py`, `tests/uat/ask_surface_uat.md`.

---

## 1. Problem Statement

A four-turn conversation on the public `/ask/` surface produced two statements that are
not true of the corpus, in opposite directions:

| Turn | Visitor's question | What the assistant said | True or false? |
|---|---|---|---|
| 1 | *can i use purchased silica for supplementation?* | *"I cannot find a definitive answer in the SAOSO standard or the Outeniqua PGS documents."* | **False as a claim about the documents.** S4.4.7, S4.4.8, Appendix 1 §2.2/2.3 and two Appendix 2 rows govern minerals and mined inputs. The model *did* answer them; the audit refused the citations. |
| 2 | *if my seeds were GMO but I grow the plants organically will the fruit be organic* | *"No … the resulting fruit would not be considered organic."* | **Not stated by any passage**, and the quote came from the Basic Production Principles — the *guidance* document (rule 7) — not the SAOSO standard. |
| 3 | *will the seeds of a gm seed that was grown organically be organic* | *"No … GM seeds and genetically engineered organisms or their derivatives are expressly forbidden."* | Same: a verbatim quote, an inference on top of it, and a certification outcome no passage states. |
| 4 | *what is the definition of genetically modified? does selective seed saving count as GM?* | *"I cannot find a definitive answer …"* | **False about the corpus.** SAOSO §1 *Definitions*, page 22, defines both **Genetically Modified Organism (GMO)** and **Genetic Engineering**, and the second definition says genetic engineering *does not include* organisms from natural hybridization — which is the answer to the second half of the question. |

The visitor drew the only conclusion the surface allows: *"how can we say GM is not allowed
but the standard doesn't define GM?"* The standard does define GM. The refusal string does
not distinguish "the documents are silent" from "I found the clause and could not verify the
address", and it says the first one every time.

**The asymmetry this conversation exposes.** The audit (`audit_citations`) is strict about
*addresses* and silent about *claims*: a correct answer dies on a `sub_ref` typo (turn 1) or
a glued locator (turn 4), while an over-generalisation one inference beyond its quote passes
cleanly (turns 2 and 3). The product is currently harder on a citation's spelling than on what
the answer asserts.

---

## 2. Strategic Goal

Every refusal is attributable — the operator can say *which* check fired, and the visitor is
never told the documents are silent when they are not — and every answer states no more than
its verified quotes state.

---

## 3. What the investigation found

All measurements below are from this working tree (commit `fe133fb` + the uncommitted
output-token work), the shipped 366-chunk corpus, and `probe_chat.py`. They are reproducible
with the commands quoted; no model call is needed except where stated.

### F1. The rare-term arm can choose a verb, and then the whole lexical arm is worthless
**Landed 2026-10-27 (`lexical_key` + `FILLER_TERMS` + a two-bet hedge).**

`search_terms` sorts the question's known terms by document frequency and searches
`ordered[0]` alone as the lexical arm. Nothing excludes filler.

| Question | Chosen key | df | What the key retrieves |
|---|---|---|---|
| what is the yearly cost to get certified, including the farm visit? | **`get`** | 1 | `r500`, and nothing else |
| if my ducks aren't fed organic food and I make compost from their bedding, will I still pass? | **`pass`** | 1 | (a one-chunk arm) |
| if a seed is not organic but I grow it organic will the crop be organic? | **`grow`** | 14 | a broad OR-shaped set |
| what is the definition of genetically modified? does selective seed saving count as GM? | **`count`** | 1 | §2.1.4 *Biodiversity reserve* |

4 of the 13 questions measured (the four in §1 plus `probe_chat.SUITE`, where three of its
nine pick one) choose a verb or filler as the sole lexical key. `FOLLOW_UP_MIN_SHARED` already encodes the same
insight for the follow-up rule (*"use", "get"* are not the subject); the rare-term chooser
has no equivalent.

**Measured consequence, turn 4.** `saving` is out of vocabulary, so the unknown-term path
runs its lexical hedge and gives the rest of the budget to the semantic arm, which prefers
§4.8 (plant breeding) to the definitions page. The definitions chunk was **one query
away**:

```
$ python -c "…search('genetically modified', use_vector=False)…"
   lex=1 S1 p22  Culture / Microorganisms, tissue, or organ …      <- chunk 1358, holds both definitions
   lex=2 Appendix 1 p70
```

and handed that chunk, the same prompt answers the refused question and **passes the audit**:

> *"A Genetically Modified Organism (GMO) is defined as an organism produced through techniques
> where the genetic material has been altered in a way that does not occur naturally by mating
> or through natural recombination… Selective seed saving does not count as genetic modification
> because genetic engineering, by definition, does not include organisms resulting from
> techniques such as natural hybridization…"* — 2 raw, 2 audited, `grounding: grounded`.

**The filler guard alone does not fix it.** Measured on 2026-10-27, three variants of the
unknown-term hedge (which supplies two seats; the semantic arm takes the other six):

| Hedge | Key searched | Definitions page in the set? |
|---|---|---|
| today: rarest known word | `count` | **no** — §2.1.4 biodiversity reserve |
| filler guard only | `gm` | **no** — the BPP seed paragraph (a *right* match, wrong page) |
| rarest subject word **+ OR of all subject words** | `gm`, then `definition OR … OR gm` | **yes** — `S1` twice, seats 1–2 |

The same two-bet hedge was measured against the three other unknown-term questions in the
suite: borax and silica are unchanged (Appendix 2 / §4.4.x still reachable), and cardboard
keeps its proxy seat while gaining Appendix 1 in place of the child-labour clause. So the
fix is one chooser used in four places **plus** a second bet in the hedge — not a rare-term
guard, which changes the key and still refuses.

**This also re-opens the evidence behind an accepted gap.** G3's 2026-10-22 re-measurement
(*"§2.1 is not in the set at eight either"*) was made through `default_retrieval`, whose key
for the cost question is `get`. The observation is right; the conclusion drawn from it is
not. `cost` retrieves §2.3, §2.4, §2.2, §2.5 and `r500` — and `fee`, the word the OPP
actually uses, retrieves **§2.1 at rank 2**. §2.1 is missing because the question says
"cost" and the OPP says "membership fees" *and* because the chooser threw the topic away.
G3 is therefore two defects, one of which is F1; the term-expansion half is a separate
decision (§6 D-4, built as 5.10). Do not build sibling-section expansion on the strength of
that measurement — it was closed without it.

### F2. `sub_ref` is supplied for passages that have no sub-clauses, and a good answer is refused
**Landed 2026-10-27 (rule 5).** With one sentence added to the rule list — *a number the
passage prints in its own text is not one of its stored sub-clauses* — the silica question
returns **6 citations, 6 audited, `grounding: grounded`**. The prompt fixed the observed
case, which makes the audit-tolerance half of `D-2` a *smaller* question than it was (§6).

Turn 1 was refused, not answered:

```
ANSWER: The SAOSO Standard does not explicitly name silica. However, minerals may be used for
supplementation if they are applied in their naturally composed and extracted form … [4 more
sentences, all correct]
citations: 6 raw, 4 audited
  ! Appendix 1: sub_ref '2.2' does not exist in the chunk
  ! Appendix 1: sub_ref '2.3' does not exist in the chunk
```

The model read Appendix 1's own item numbering (`2.2. Natural non-renewable resources…`,
`2.3. Synthetic substances…`) and used it as `sub_ref`. The chunk's offset map has no
sub-clauses, so the audit refused — twice — and the visitor got the refusal sentence.
`ASK_SURFACE_PRD.md` §7 item 2 already records this as open and assigns it here.

**The silica question is answerable today.** Nothing about it is a coverage gap.

### F3. `[{index}] ` sitting on the `LOCATOR:` line gets glued into the citation

Turn 4's first live-style attempt (this tree) returned `section_ref: "S6.2.3.1"` for a
passage printed as `[6] LOCATOR: S2.3.1`. Passage index **6** + locator **`S2.3.1`**. The
audit answered `not present in the retrieved set` and the answer became the refusal.

This is the G9 class one layer down. D61/G9 moved the *document label* off the locator
because the model copied the printed header; the index was still printed on that line, and
the model copied it too. **Measured three times, and moving it was not enough:**

| Prompt shape | Locator | What the model cited | Runs |
|---|---|---|---|
| `[6] LOCATOR: S2.3.1` | `S2.3.1` | `S6.2.3.1` | 1/1 |
| `[2] LOCATOR: S1` | `S1` | `S2` | **3/3** |
| `PASSAGE 5` on its own line | `S4.8` | `S5` | 2/3 |
| **no number at all** | `S4.8` | `S4.8` | **0/3 wrong, 7/7 citations audited, 3/3 grounded** |

So 5.2 is *remove the number*, not *move it*: any number printed near an address will be
appended to that address, and the audit then refuses a correct, properly quoted answer —
which the visitor reads as "the documents are silent". The prompt keeps `LOCATOR:`,
`Document:` and the sub-clause line; the blank line already separates passages.

### F4. A verbatim quote can authorise a claim the passage does not make

Turns 2 and 3 passed, and here is exactly why:

* the Basic Production Principles chunk `general-principles` contains the sentence *"Any GM
  seeds or seedlings are expressly forbidden in organic agriculture."* — verbatim, so the
  audit has nothing to object to;
* SAOSO 2.3.1 contains *"the deliberate use or negligent introduction of genetically
  engineered organisms or their derivatives is prohibited. This shall include animals, seed,
  propagation material, feed…"* — also verbatim.

Neither says *the fruit is not organic* or *seeds from a GM plant are not organic*. Those are
consequences the model supplied. `audit_citations` checks four things — the locator exists,
it is unambiguous, the quote is a substring, the sub-ref exists — and **not one of them is
about entailment**. Rule 4 ("answer with the governing rule even when the passages do not
name the item") invites exactly this reasoning; its guard is *"do not reason from silence"*,
which does not cover reasoning *from an adjacent prohibition*.

Two aggravating details, both product-level:

1. **The wrong document was cited as the authority.** Rule 7 makes SAOSO/OPP governing and
   the BPP guidance. The "expressly forbidden" sentence is the BPP's. The SAOSO clause that
   governs (2.3.1) was in the set for turn 2 and unused.
2. **It is a certification verdict.** *"Will not be considered organic"* is the outcome the
   OPP reserves to the administrator and the committee (`pgs_docs/… OPP …2026.pdf` §2.2
   "certification decision-making carried out by the PGS administrator"; §3 committee
   functions). `test_claim_discipline.py` guards the *public site* against publishing such
   outcomes; the chat currently publishes them for a hypothetical farm.

Turn 3's claim may well be defensible on 2.3.1's "derivatives" — that is not the point. The
point is that **the product cannot tell**, and the surface states it as settled.

### F5. The follow-up path inherits the parent's *prose*, not only its citations

Turn 3 was detected as a follow-up (`seeds`, `gm`, `organic` shared with turn 2) and therefore:

* `context_query` = turn 2's OR-query, fused in last;
* `carried_ids` = the clauses turn 2 was allowed to cite (the BPP chunk and S2.3.1);
* `history` = the last 8 messages, including **turn 2's answer text**, whose claims are not
  audited — only its citations were.

The prompt's `d49-4` wording says *"Do not cite a passage that is not supplied below"*. It
says nothing about restating the parent answer's claim as fact. So each follow-up starts one
inference further out, and the audit sees only verbatim quotes. This is how a conversation
drifts from "the standard prohibits GE seed" to "the fruit is not organic" in two turns while
every turn is `grounded`.

### F6. One refusal string, four causes

`EscalatedQuery.Reason` has four values — `INSUFFICIENT_CONTEXT`, `CITATION_AUDIT`,
`NO_CITATIONS`, and the pre-model empty-retrieval branch — and the visitor sees `REFUSAL`
(D17) for all of them: *"I cannot find a definitive answer in the SAOSO standard or the
Outeniqua PGS documents."* For `CITATION_AUDIT` that sentence is **false**. It is the sentence
that produced the user's belief that the standard does not define GM.

The reasons *are* recorded (`ChatMessage.refusal_checks`, `EscalatedQuery.reason`) and
`scripts/why_refused.py` prints them — for the operator. Nothing on the public surface, and
nothing in the answer-page/escalation flow, distinguishes the two.

### F7. One address, eight definitions: the citation link lands at the top of the section
**Landed 2026-10-27 (5.8).** A GMO citation now links to `#s1-3` — the reader's id for that
chunk — instead of `#s1`, which is the top of a 21 000-character section. The suffix is
positional, so the citation and the page must compute it from one ordered chunk list
(`knowledge.reading.reader_anchor_map`), not from the locator alone.

Every chunk of SAOSO §1 carries `section_ref="S1"` (8 chunks, ~21 000 characters, all
`reading_anchor='s1'`). A GMO citation therefore links to `/documents/saoso/read/#s1` — the
top of the definitions, not the definition quoted. `ASK_SURFACE_PRD` §0a advertises
clickable citations; on this section the click landed several thousand characters early.
Severity is low (right document, right page); it is listed because the fix is cheap and
because it is the same "an address is not an identity" mistake as F3.

---

## 4. Similar failures to hunt (the sweep this PRD owes)

Each sweep is read-only, run against the **box** where it can be (the deployment holds the
conversations), and produces a count the decision can rest on. Do not fix by guess.

| # | Sweep | Instrument | Output that matters |
|---|---|---|---|
| **S1** | Every question whose rare-term key is a verb/filler | Extend `probe_chat.py` to print the chosen key and df, run it over `SUITE` plus the 20 most recent `ChatMessage` user rows from the box | A list of questions answered from a proxy word. Feeds `D-1`; the size of the list decides whether the guard is a stop-list or a phrase-preference rule |
| **S2** | "What is the definition of X?" for glossary terms | Fixture test + one probe run per term: GMO, genetic engineering, buffer zone, in-conversion, split production, nanomaterial, homeopathic, wild harvested, producer, processing aid | **Retrievability**, not answers: is one of the eight `S1` chunks in the top 8? Any "no" is turn 4 again |
| **S3** | Locator glue | Query `ChatMessage.citations` + `refusal_checks` for refs matching `^S?\d+\.` whose leading integer is ≤ 8, and re-probe the definition question 5× | Whether F3 reproduced on the live copy. Decides fix-now vs record-only |
| **S4** | `sub_ref` on chunks that have none | Query `refusal_checks` for `does not exist in the chunk`; count by chunk | The number of turns where a correct answer was refused for an address. Feeds `D-2` and `ASK_SURFACE_PRD` §7 item 2 |
| **S5** | Claims wider than their quotes | **Human** review of the last 20 accepted answers on the box, quote beside claim, one line each | The false-answer rate of the current contract. Feeds `D-3`; without it, the claim-scope rule is churn |
| **S6** | Follow-up drift | Same review over sessions with ≥ 3 turns, comparing each answer's claims to its parent's | Whether F5 is a pattern or one conversation |
| **S7** | Anchor collisions | `section_ref` values with more than one chunk; compare `reading_anchor` | F7's size. If only §1, the fix is an anchor derived from the chunk's own first definition headword |

**Only S5 needs a model call, and only S5 needs a human.** S1–S4, S6, S7 are queries and
probes already in the tree.

### 4.1 What the dev database answered first (2026-10-27, 34 recorded turns)

Before writing any sweep, the local deployment's own record was read
(`ChatMessage`, `EscalatedQuery`, `refusal_checks`). It settles four of the seven and
weakens a fifth:

| Sweep | Result | Consequence |
|---|---|---|
| **S3** (locator glue) | The two recorded `not present in the retrieved set` refusals name **`S8`**, not a glued index. `session 44`'s `citations.rejected` is **empty**, so the row cannot say *why* it refused | F3 stays a hypothesis. The glue was observed once, on a freshly probed turn; it is not in the recorded history. The refusal record cannot reconstruct its own reasons — a P2.5a coverage gap |
| **S4** (sub_ref) | **6 refusals, all Appendix 1** — `2.2`, `2.3`, `3`, `4`, `5`, `6`, all `d49-4` | D-2 has its number, and it is one chunk and one model habit |
| — (turn 1 and 4's reason) | The silica question and the GM-definition question are both recorded as **`CITATION_AUDIT`** | Neither was a corpus gap, and neither was `INSUFFICIENT_CONTEXT`. F6 is a recorded fact, not an inference |
| **S5/S6** (claim scope) | **3 accepted answers exist, all from the conversation under review**; 2 of the 3 state a certification outcome no passage states ("the fruit … will not be considered organic"). The third is careful — *"There is no provision **in the provided passages**…"* | D-3's sample is the transcript itself. The extract is `_scratch/claim_review_2026-10-27.md`; regenerate it with the S5 query. The third answer proves the hedge is reachable without a rule |

**And the reason field is lossier than the sweeps assume.** 16 of 34 refusals are
`NO_CITATIONS`, a label that fired on four different branches in `answer_question()` — no
citations, an empty answer, `len(answer) > MAX_ANSWER_CHARS`, and every citation a
duplicate. One of those was a runaway answer wearing a grounding label. **Split on
2026-10-27** (see §5.9): the enum is now `NO_RETRIEVAL`, `INSUFFICIENT_CONTEXT`,
`NO_CITATIONS`, `CITATION_AUDIT`, `EMPTY_ANSWER`, `ANSWER_TOO_LONG`, `USER_REQUESTED` —
one value per finding, migration `0008`, no data change. The box sweeps (S3, S4, S6) can
group on it now.

---

## 5. Proposed solution

Ordered so that the two refusals this PRD exists for are fixed by the cheapest changes first,
and so that nothing which changes *wording* ships before its sweep.

### 5.1 Choose the lexical key by subject, and hedge two bets (F1) — **landed 2026-10-27**

`knowledge/services.py`:

* one `lexical_key()` chooser — the rarest word that names the subject — used by the primary
  arm, the unknown-term hedge, the follow-up context arm and `probe_chat.py`. A private rule
  in each is the §2.7 defect by construction;
* `FILLER_TERMS`, a frozen list of the verbs and furniture that document frequency makes
  look rare (`count`, `get`, `pass`, `use`, `grow`, `purchase`, …), with `subject or known`
  so an all-filler question still searches something;
* the unknown-term hedge is **two seats and two bets**: the rarest subject word, and the OR
  of the subject's words. Measured in §3 F1 — the guard alone still refuses turn 4;
* `RetrievalResult.key` records the word actually searched, so the probe prints the
  product's decision instead of re-deriving it.

Acceptance: `test_a_verb_is_never_the_lexical_key`,
`test_an_unknown_word_hedges_two_bets` and
`test_the_definition_question_reaches_the_definitions_section` (knowledge), the 13-question
suite re-run, and the definition question grounded 5/5 on the box.

### 5.2 Remove the passage number (F3) — **landed 2026-10-27**

The index is gone from `build_prompt`; `PASSAGE n` on its own line was measured and was not
enough (§3 F3 has the table). The prompt now prints `LOCATOR:`, `Document:`, the sub-clause
line and the text, separated by blank lines. `PROMPT_VERSION` is `d50-1`, and the two
`SYSTEM_PROMPT` rules that said "numbered passages" now say "supplied passages".
Measured: the definition question, which refused every time before, is **3/3 grounded with
7/7 citations audited**.

### 5.3 `sub_ref`: state that the passage's own numbering is not the map (F2) — **landed 2026-10-27**

Rule 5 gained one sentence. Measured on the silica question: **6 raw, 6 audited, grounded**
(it was 6 raw / 4 audited / refused). `ASK_SURFACE_PRD` §7 item 2 assigned this here; the
prompt had the mechanism (`sub_line` prints "none — omit `sub_ref`") and the model overrode
it, so the rule had to be in the rule list.

### 5.4 `sub_ref` tolerance — decision (`D-2`), **smaller than it was**, then build

The prompt rule answered the observed case, so this is now a *residual* question rather
than a fix: S4's six recorded refusals were all Appendix 1 and all `d49-4`, i.e. before the
rule. Re-run S4 on the box after the deploy. If the class is gone, close D-2 unanswered —
an audit that tolerates what the prompt prevents is a second path nobody needs.

The measurement did surface one option worth recording, though, because it is the same
shape as the four transcript failures: **when a model's locator is unresolvable but its
quote is an exact substring of exactly one retrieved chunk, the citation *is* verifiable** —
the address added nothing that the quote did not. Accepting that is stricter than trusting
the locator (it requires a unique match, and still refuses ambiguity and invention), but it
is looser than today, and D47 forbids trimming citations. Record it as `D-2b`; do not build
it without the product owner.

### 5.5 Claim scope (F4) — **landed 2026-10-27**

Rule 4b: *state the rule the passages supply, and say plainly that they do not state the
outcome; never answer whether anything is, becomes or remains organic or certified — that
decision belongs to the certification body.* The last clause is the one that mattered: with
only the first two sentences, the model answered *"No, any GM seeds … are expressly
forbidden"* — a bare verdict word in front of a correct rule, in 2 of 2 runs. With
*"a leading 'No' or 'Yes' to such a question is that verdict"* added, both questions open with
the rule, 3 of 3.

Measured after, on the two turns from the transcript:

> *"… The passages do not explicitly state whether the fruit from GM seeds grown organically
> would be considered organic, but they do prohibit the use of GM seeds."* — grounded.

**The server-side signal is narrower than planned, and for a measured reason.** The plan was
"every answer sentence must share a content word with an accepted quote". It was measured and
it **passes the exact answer it was written for**: *"the fruit would not be considered
organic"* shares `organic` with *"Any GM seeds or seedlings are expressly forbidden in
organic agriculture."* So the check looks for an **outcome phrase** instead
(`considered organic`, `is organic`, `certified as organic`, …) that no accepted quote
contains, and records it in `ChatMessage.review_notes` — never a refusal. Its blind spot is
recorded here: a bare *"No, …"* carries no outcome phrase, so it is rule 4b's job, and that
is the residual stochastic risk.

### 5.6 Follow-up inheritance (F5) — decision (`D-3`), then measure

Options, to be measured with `probe_follow_up`:

1. **Prompt-only:** the history block says the earlier turns are not evidence *and* that an
   earlier answer's claims must not be restated (keeps the full window, cheapest).
2. **Narrow the window:** keep the parent question and the parent's accepted *citations*, drop
   the parent's answer prose. Answers cannot drift off prose they were never shown.
3. Both.

Recommendation: measure 1, and 2 if S6 shows drift in more than a handful of sessions.

### 5.7 Refusal attribution (F6) — **landed 2026-10-27**

`REFUSAL` stays (D17) and the turn carries one more sentence, per reason, from
`core/models/_chat.py::REFUSAL_NOTES`. The rule those sentences follow: **none claims the
documents are silent unless that is what happened** — `CITATION_AUDIT` says *"wording that may
apply was found, but the citation could not be checked"*, and only `NO_RETRIEVAL` says nothing
matched. This is the fix that would have stopped the visitor concluding "the standard doesn't
define GM".

Implementation detail worth keeping: the sentence is read from the turn's new
`refusal_reason`, not by comparing `message.content` to `REFUSAL` in the template. The old
comparison is how a copy change would have silently removed the contact link and the refusal
styling — and the surface fixture had to be corrected for exactly that reason (§1.32 shape).

### 5.10 The alias arm — D-4, and G3 closes — **landed 2026-10-27**

`knowledge/aliases.py` holds a reviewed `question word -> the word the corpus uses` table
(`cost -> fee`), and `search_terms` runs an **alias arm**: the rarest alias word searched
**alone**, capped at `ALIAS_SEATS = 2`, displacing the tail so the visitor's own vocabulary
keeps its seats. Alone matters, and it is measured:

```
search("cost")          -> §2.3, §2.4, pgs-sa, §2.2, §2.5     (§2.1 absent)
search("fee")           -> §2.3, §2.1, §2.2, §2.4, §2.5      (§2.1 at rank 2)
search("cost OR fee")   -> §2.3, §2.4, pgs-sa, §2.2, §2.5     (§2.1 absent again)
```

**G3 is closed by measurement.** The cost question now seats §2.1 and the answer opens with
it — *"…includes an annual farmer and consumer membership fee of R100, a renewal farm
assessment visit fee … a licensing fee of R500 …"*, **5 citations, 5 audited, grounded** —
which is G3's own acceptance criterion, met without the sibling-section expansion that the
2026-10-22 evidence pointed at. `CHAT_ANSWER_COVERAGE_PRD.md` G3 carries the closure note.

Three tests: the real OPP (a new `opp_ingested` fixture), the synthetic clause the question
word cannot reach, and a negative case proving an unrelated question gains nothing. The arm
disabled → two red; restored → green.

### 5.9 One refusal reason names one finding — **landed 2026-10-27**

`NO_CITATIONS` covered four branches and `INSUFFICIENT_CONTEXT` covered two, so the record
could not attribute the refusal it exists to attribute. Split into `NO_RETRIEVAL`,
`INSUFFICIENT_CONTEXT`, `NO_CITATIONS`, `CITATION_AUDIT`, `EMPTY_ANSWER`, `ANSWER_TOO_LONG`
(plus the visitor-initiated `USER_REQUESTED`), with migration `0008`, no data change and no
`PROMPT_VERSION` bump — an enum is not a contract the cache depends on. `why_refused.py`
now explains each value and says what a pre-split database means. Four new tests, one per
branch, each proved red by reverting the branch; the old test that asserted the wrong
reason for the empty-retrieval case was corrected rather than deleted, and it now also
proves the model is never called.

### 5.8 A citation that lands on the quoted definition (F7) — **landed 2026-10-27**

`knowledge.reading.reader_anchor_map(document)` returns `{chunk pk: anchor}` from the same
`unique_anchors(reading_chunks(document))` the reader renders, and `audit_citations` uses it
for `Citation.reading_anchor` (one query per distinct document, falling back to the section
anchor for a chunk that is not a stored row). Verified on the shipped corpus: the GMO
definition cites `S1` and now links to **`#s1-3`**, which is the id the page renders for that
chunk; before, all eight §1 chunks linked to `#s1`.

The test is a property, not a string: two chunks share `S1`, the audit must give them `s1` and
`s1-2`, and the reader page must render both ids with the quoted text under the second. Put
the citation back on the section anchor and it goes red.

**The residual:** the suffix is positional, so a re-ingest that inserts a chunk renumbers the
later ones — the same property `unique_anchors` already had, and why an anchor is stored in
the answer record rather than only resolved live.

---

## 6. Decisions needed

| # | Decision | Recommendation |
|---|---|---|
| **D-1** | Is the rare-term chooser's filler-guard a stop-list, a phrase-preference rule, or both? | **Both, but the phrase rule is not what fixed turn 4** (measured in §3 F1). The stop-list plus the two-bet hedge is landed; the adjacent-bigram preference is *dropped* — it was measured and it loses on the cost question (`farm visit` displaces `cost`, which is where §2.1 would have come from). Keep the list ≤ 15 words, each justified by a measured question |
| **D-2** | May the audit drop a `sub_ref` (never the citation) when the chunk has no sub-clause map and the value is an item marker in the chunk's own text? | **Re-measure first** — the prompt rule answered the six recorded cases. If any remain: yes, same shape as D61 (decoration, not identity) |
| **D-2b** | May an unresolvable locator be replaced by the chunk its quote uniquely matches? | **Record, do not build.** It would have saved three of this PRD's four refusals, and it is stricter than it looks (unique match required) — but it is a relaxation of the address contract and belongs to the product owner, after D-3 |
| **D-3** | Does the prompt forbid deciding an outcome (organic / not organic), and may a follow-up see its parent's answer prose? | **Approved and built 2026-10-27** (§5.5) — rule 4b, plus a leading-verdict clause after the first version was dodged. Follow-up window (5.6) still wants S6 before narrowing |
| **D-4** | Does G3 get a seeded alias table (`cost → fee, membership fee`), now that its evidence is shown to rest on a bad key? | **Approved and built 2026-10-27** (§5.10) — it closed G3 without sibling-section expansion. An alias table is data, and G5's "no classifier" still holds |
| **D-5** | May the refusal surface carry a second sentence naming the cause, given D17 fixes the wording? | **Approved 2026-10-27 and built** (§5.7) — one sentence per reason, from the split enum |

---

## 7. Coordination with in-flight work

**Another session changed the chatbot at `811ac3d` (2026-10-27), minutes before this PRD was
written:** `CHAT_MAX_OUTPUT_TOKENS` 2048 → 4096 and the ceiling 4096 → 8192, because
`gemini-2.5-flash` counts **thinking tokens** against the output cap — a measured attempt
thought 1962 and was cut with 72 tokens left. That commit touched `pgs/settings.py`,
`core/services/_chatbot.py` (constants + comments), `.env.example` and
`core/tests/test_chatbot_provider.py`, and its probe `_scratch/answer_probe.py` also
measured **the silica question**. It left `PROMPT_VERSION` at `d49-4`. The other agent may
still be active — treat the tree as shared.

Therefore:

1. **Do not touch** `MAX_OUTPUT_TOKENS`, `MAX_OUTPUT_TOKENS_CEILING`, their settings or
   `.env.example` entries in this slice. A truncation is a *fifth* refusal cause and it is
   that session's.
2. **One `PROMPT_VERSION` bump, not two.** Bump once, after the last prompt change lands,
   and say in the comment which changes it covers (`d50-1`: the passage header, the sub_ref
   rule and rule 4b). Two concurrent bumps produce a comment that describes neither. (`811ac3d`
   changed no prompt text, so this PRD owns the bump.)
3. **Rebase, don't merge around it.** 5.1 edits key selection in
   `knowledge/services.py` (not touched by `811ac3d`); 5.2/5.3/5.5 edit `SYSTEM_PROMPT` and
   `build_prompt` in `_chatbot.py` (touched, now committed). Land 5.1 first.
4. The silica question is the shared failure: coordinate on one probe run rather than two
   investigations of the same refusal.
5. **`product/backlog/backlog.md` regenerated on 2026-10-27** after this file landed
   (`python product/backlog.py --write`). If the other session adds a PRD, regenerate again —
   never hand-edit the index.

---

## 8. Technical requirements

1. No migration. No new model. No new route. `knowledge` still never imports `core`.
2. `search_terms`' signature does not change; the chooser is internal. `probe_chat.py` must
   read the *same* chooser (testing_hazards §2.7 — the instrument-measures-another-path
   defect has already cost this repo G8).
3. Every prompt change bumps `PROMPT_VERSION`, or the answer cache serves replies produced
   under the old contract.
4. A grounded answer may never be converted into a refusal by a *new* warning; warnings go
   to `ChatMessage.refusal_checks` and are reviewed, not enforced.
5. `tests/e2e` and `verify.sh` stay green. `test_claim_discipline.py` must not need
   widening for a chat string that only appears in a transcript.
6. **Prove each guard by breaking it** and watching the test go red (repo rule).

## 9. Execution steps

1. ~~Land **5.1** (rare-term chooser) with `probe_chat --terms-only` extended to print the key.~~
   **Done 2026-10-27.** The probe prints `key: 'gm' — the word the rare-term arm searched`,
   read from `RetrievalResult.key` rather than re-derived. Suite unchanged; the four
   verb-key questions re-probed and recorded.
2. **S1 and S2** sweeps. The probe now prints the key, so S1 is a run; S2 is a fixture test
   (`test_the_definition_question_reaches_the_definitions_section` proves one term).
3. ~~**Split the `NO_CITATIONS` reason** into the four branches it currently covers, so S3,
   S4 and S6 group on a field that means one thing.~~ **Done 2026-10-27** (§5.9), gate green
   at 907. No prompt change, no `PROMPT_VERSION` bump.
4. ~~Land **5.2** and **5.3**; one `PROMPT_VERSION` bump.~~ **Done 2026-10-27,** `d50-1`,
   gate green at 903. Re-probed: definition **3/3 grounded, 7/7 audited**; silica **6/6
   audited, grounded**; the two GM-outcome turns unchanged (they are D-3, not a bug to
   patch silently).
5. **S3 and S4 on the box**, after the deploy and one `ingest`-free restart: the prompt
   changed, the corpus did not, so the only thing to check is the live reply. Close D-2 if
   the six Appendix-1 refusals are gone; do not build `D-2b` without the product owner.
6. ~~**S5 and S6**: settle D-3 on the extract; land 5.5 and 5.6~~ **5.5 landed 2026-10-27**
   (§5.5). 5.6 (the follow-up window) is **not** landed: the extract is three answers from
   one session, which is enough to settle the *rule* and not enough to justify narrowing
   what a follow-up may see — run S6 on the box first.
7. ~~Settle `D-5`; land 5.7; update `tests/uat/ask_surface_uat.md`.~~ **5.7 landed** (§5.7),
   gate green at 915. **Still to do:** the UAT scenario that reads a `CITATION_AUDIT` refusal
   and a corpus-silent refusal side by side — the two now carry different second sentences,
   which is exactly what a reviewer should judge.
8. ~~Land 5.8 (anchor) and settle `D-4`~~ **Both landed 2026-10-27** — D-4 as §5.10 (G3
   closed) and 5.8 as §5.8, gate green at 920. The PRD's own work is done; what is left is
   the list below and the box.
9. Append whatever cost time to `product/docs/context/testing_hazards.md` — three candidates
   from this slice: *a probe that measures a key the product does not choose* (§2.7's
   sibling); *a refusal reason that covers four branches* is how a sweep mislabels its own
   finding; and *a number printed near an address is read as part of the address* — measured
   twice, on two different layouts, before the number was removed.

## 10. Success criteria

- [x] The four questions in §1 are re-probed: **silica answers** (6/6 audited), **the GM
      definition answers** (3/3 grounded), and the two GM-outcome turns **state the rule and
      decline the verdict** (3/3 after the leading-verdict clause).
- [x] `probe_chat.py` prints the chosen lexical key and its df on every run, and no suite
      question's key is a filler word.
- [ ] The four questions are grounded in **5/5 fresh sessions on the box** (the G8/G9 rule:
      one green run proves the obstacle is gone, not the class).
- [x] No recorded citation ref in a fresh probe contains the passage index.
- [x] The gate is green (915 tests); every new guard was broken and watched go red — the
      filler list, the second hedge bet, the passage number, each new refusal reason, rule
      4b, the outcome advisory, and the per-reason note.
- [x] S1, S4, S5 and S6 are run and their counts recorded in §4.1. S2, S3 and S7 remain.

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| The filler list grows into a hand-maintained part-of-speech tagger | Keep the phrase-preference rule as the general fix; the list is a stop-gap and must stay ≤ 15 words, with each entry justified by a measured question |
| Dropping a `sub_ref` weakens the audit (D47) | It never drops the citation or the quote; invention and ambiguity still refuse; two tests pin both directions |
| Rule 4b turns governing-rule answers back into refusals — the failure `CHAT_ANSWER_COVERAGE_PRD` exists to prevent | Rule 4b forbids *outcomes*, not *rules*; measure the suite before and after; revert if the grounded count falls |
| An entailment check becomes a second model call and doubles cost | The server-side signal is lexical (shared content word), advisory only, and lives in the review record |
| Two sessions editing `_chatbot.py` | §7: 5.1 first (different file), then one `PROMPT_VERSION` bump, no touching the token constants |
| The live copy runs a pre-D52 corpus at a 5-passage budget, so the conversation may not reproduce | Run S3/S4/S5 **on the box**; record the corpus chunk count and `CHAT_RETRIEVAL_LIMIT` with the findings before claiming a cause |

## 12. Not in scope

- The escalation answer path (**G6**) — the refusal still promises a person who cannot be
  reached; that is `ESCALATION_ANSWER_PATH_PRD.md`.
- Appendices 3/4/6/7 (**G4**), the classifier (**G5**), the BPP spanning line (**G7**).
- The output-token/thinking-token work (§7) — a truncation is that session's refusal cause.
- Any corpus rebuild or `--force` re-ingest. F1's counterfactual was measured on the shipped
  corpus: no re-ingest is needed to fix turn 4.

---

## Pre-Flight Checklist

- [ ] Models added to `core/models.py` or new app? — **No.**
- [ ] Views added to correct `core/views/_<domain>.py`? — **No.**
- [ ] Forms added to correct `core/forms/_<domain>.py`? — **No** (5.7's copy is view context).
- [ ] Services added to correct `core/services/_<domain>.py`? — `_chatbot.py` only.
- [ ] URLs added to `core/urls.py` in the correct section? — **No.**
- [ ] Tests added to `core/tests/test_<domain>.py`? — `test_chatbot_grounding.py`,
      `test_chatbot_guardrails.py`, `knowledge/tests/test_retrieval.py`.
- [ ] Migrations generated and backwards-compatible? — **None.**
- [ ] `select_related` / `prefetch_related` used in new queries? — n/a; 5.1 adds no query.
- [ ] `transaction.atomic()` used for multi-table writes? — unchanged (`_as_refusal`).
- [ ] No logic in templates? — unchanged.
- [ ] `PROMPT_VERSION` bumped once, covering every prompt change in the slice? — **Required.**
- [ ] `probe_chat.py` reads the same retrieval chooser and budget as the view? — **Required.**
- [ ] Every guard broken and watched go red before being trusted? — **Required.**
- [ ] `testing_hazards.md` appended with whatever cost time? — **Required.**
