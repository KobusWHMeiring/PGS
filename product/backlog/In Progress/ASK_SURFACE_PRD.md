# PRD — The ask surface, second shape (board + answer pages)

**Status:** In Progress — shape decided (**D62**); follow-up stage 1 landed (**D63**);
**the board, the answer pages and the citation's document reader are built (2026-10-23)**;
the trace console and the wider-reading tier are not.
**Opened:** 2026-10-23
**Decision record:** `PGS_PLATFORM_SPEC.md` §18.3 D62 and D63.
**Prototypes:** `product/design/d61_ask_interface_options.html` (five shapes),
`d61a_ask_board_refinement.html` (question-first board),
`d61b_ask_page.html` (the page as it would ship),
`d61c_follow_up.html` (follow-up versus new question),
`d61d_rewrite_and_trace.html` (the alternatives to a rewrite, and the trace console).

---

## 1. Why this exists

`/ask/` is a chat window. It grounds answers, refuses rather than guesses, and passes its
tests — but a conversation asserts four things about the product, and three of them are
wrong here (D62):

1. **That the conversation is the unit of value.** Our unit is a grounded *passage*. The
   thread scrolls it out of view at the next question.
2. **That the answer is unique to the asker.** It is not: everybody's question is retrieved
   from the same four documents. The tenth visitor asking about cardboard cannot see that
   nine others did, and leaves nothing behind.
3. **That the answer is finished when the bubble ends.** For a standard, an answer is a
   *locator*. Our citations expand into a quote and then go nowhere.
4. **That a refusal is a legitimate answer.** This one *is* true, and it is the property the
   new shape must keep — it is why refusal must remain a state, never an error.

The measured case that decides it: *"What is the yearly cost to get certified, including the
farm visit?"* needs four OPP sections (…§2.1–§2.5, three printed pages) and the live answer
omits §2.1 — the R100 — because it was never retrieved (G3). A bubble cannot show a reader
what it did not fetch.

## 2. What is decided (D62)

| Decision | Consequence |
|---|---|
| The composer is the primary element; the board sits below it | A visitor with a question does not scroll past six cards to find the box |
| Asking adds to the board, **after an administrator reads it** | The consent label promises review, so the card lands as *awaiting review*, not live |
| A refusal becomes a **Waiting** card | The gap in what we publish is visible and counted, not lost in a session |
| Each answer has a **permalink** with the clause in full, what it does not cover, and a copyable citation | An answer becomes shareable and findable, which is how the group's members actually communicate |
| The four governing documents are **pre-ticked**; wider reading is **opt-in** | The corpus is the default; context is a deliberate act, and it is marked wherever it contributes |
| The worksheet (`D`) is reused in the **apply / prepare** flows | The group already publishes a Farm Visit Preparation List; it is the outline, not an invention |
| The chat window survives as the **composer** | The unexpected question is still answerable, and the 94 existing tests keep their subject |

**Not decided:** whether visitor questions may be published at all (POPIA — a question is
free text and *"my neighbour's farm"* is a third party), and what the wider-reading tier
points at (there are no documents behind it yet).

## 3. What stage 1 of the follow-up work landed (D63)

Implemented, tested and measured on 2026-10-23. **No model call was added.**

| Change | Where |
|---|---|
| `looks_like_follow_up()` — deterministic, **fails closed** to today's behaviour | `core/services/_chatbot.py` |
| `search_terms(context_query=…)` — a context arm over the previous question's rarest term, capped at 2 passages and a quarter of the budget | `knowledge/services.py` |
| `chunks_by_id()` — a scoped fetch, so a carried citation cannot come from another corpus | `knowledge/services.py` |
| Carried citations — the previous answer's *audited* clauses re-enter this turn's set, displacing the tail | `core/services/_chatbot.py` |
| `citations.accepted[].chunk_id` — a citation now records which chunk it named | `_citation_record` |
| A conversation is not evidence — one prompt line, `PROMPT_VERSION` `d49-4` | `build_prompt` |
| The cache key includes a history digest **for a follow-up only** | `_cache_key` |
| `probe_chat.py --follow-up "parent" "follow-up"` — three model calls, writes no rows | `scripts/probe_chat.py` |

### Evidence

`verify.sh`-equivalent gate: **845 tests pass**, `lint-imports` kept (1 contract, 0 broken).
New: `core/tests/test_follow_up.py` (27), six in `knowledge/tests/test_retrieval.py`.

Live measurement, shipped corpus (366 chunks), four parent → follow-up pairs:

| Pair | Parent's cited clause before | After | Outcome |
|---|---|---|---|
| cardboard → *what if I compost it first?* | present (rank 8) | present | no change needed |
| horse manure → *what if it comes from a feedlot?* | **absent** — grounded answer about *animal feed* | present (carried) | **fixed**: correct answer about manure sourcing |
| ducks/bedding → *what if I stop composting?* | **absent** — grounded, partial | present (carried) | **improved** |
| straw mulch → *does it have to be untreated?* | **absent** — refused | present (context arm) | **not fixed** — the model still answers about *wood*; a prompt defect, not retrieval |

The second row is the argument: the answer was **grounded and wrong**. The audit passes a
faithful citation to the wrong clause. That is the class a retrieval-only fix cannot catch.

## 4a. What landed on 2026-10-23

Built, tested and measured in one slice (`ASK_SURFACE_PLAN.md`). **The citation does not link
to a PDF page** — the product owner's decision: `document_file()` streams with
`as_attachment=True`, so a `#page=76` fragment has no viewer to land in, and the text is
already in `DocumentChunk`. A citation now opens a rendered, searchable **reader** of the
ingested document, anchored on the section reference the citation already carries.

| # | Was "not built" | Now |
|---|---|---|
| 1 | The board | `PublicQuestion` (a table with a publish flag, not the cache), the composer-first layout, the topic filter, the Waiting state and the admin publish/reject actions |
| 2 | The answer page | `/ask/<slug>/` with the clause in full, *what this answer does not cover* (required), *questions next to this one*, a copyable citation and `noindex` on a gap page |
| 3 | The consent control | `publish` on the question form, unticked by default, with the promise the `AWAITING` state keeps |
| 4 | The two prerequisites | `Citation.document_code` + `reading_anchor` (resolved through `source_path == source_file`, no migration) and `/documents/<code>/read/` — search, contents, anchors, `:target` highlight |
| 5 | The trace console | **still not built** (it needs arm/rank/score on `grounding`; see §4) |
| 6 | The wider-reading tier | **still not built** — no documents behind it |
| 7 | The stage-2 rewrite | **still not bought** |

Two findings that changed the work:

* **`publish_documents` recorded an absolute path** in `PublicDocument.source_path`, so it could
  never equal `StandardDocument.source_file` and no citation would have been clickable on a
  second machine. It records the repository-relative path, and a test asserts the join.
* **Verbatim corpus text cannot satisfy the claim sweep, and must not be made to.** SAOSO prints
  "biodynamic" five times and the OPP prints "pasture raised" — both in `FORBIDDEN`. The reader
  (and an answer page's clause block) are therefore outside `PUBLIC_URLS`, with the reason
  recorded and three tests keeping the exemption honest, including one that proves the
  exemption is necessary.

### 4b. Found in UAT, 2026-10-27 — the wait was invisible

A real question ("can i use purchased silica for supplementation?") took **40.7 s** and the
page showed only a dimmed button. The audit then refused the answer, correctly — the model
invented `Appendix 1` sub-refs `2.2`, `2.3`, `3`, `4`, `5`, `6`, and the all-or-nothing audit
will not pass a citation it cannot verify.

Two separate findings, and only the first is fixed:

| # | Finding | State |
|---|---|---|
| 1 | **Nothing said the assistant was working.** The optimistic user bubble and a 0.6-opacity button were the whole indication. | **Fixed.** The thread now carries a `role="status"` row ("Reading the documents", animated dots that yield to `prefers-reduced-motion`), the send button is `disabled`/`aria-busy` in flight, and after 8 s the row says a long answer can take up to a minute. The aside states the expected latency before the wait rather than after. |
| 2 | **The model invented sub-clause numbers for Appendix 1.** The audit caught it, but the visitor paid 40 s for a refusal. | **Open**, and it belongs to `CHAT_ANSWER_COVERAGE_PRD` (next to G9): the prompt lists the sub-clauses each passage actually has, so this is a contract violation rather than a corpus gap. |

Measured latency, from `ChatMessage.latency_ms` on the dev instance (n=51): **median 6.3 s,
mean 7.1 s, max 40.7 s**. The tail is one long generation plus, when the first attempt is cut
at `CHAT_MAX_OUTPUT_TOKENS`, a single retry at double the cap — two calls, each with a 30 s
`CHAT_TIMEOUT_MS`, so the honest worst case is about a minute. That is the number the waiting
row quotes.

### 4c. The cap was one budget for two jobs (2026-10-27)

Chasing the 41 s tail found the real mechanism: **`gemini-2.5-flash`'s thinking tokens are
counted against `max_output_tokens`.** Attempts on the silica question, measured per call
(`_scratch/answer_probe.py`, three runs each):

| Run | Thinking | Output | Finish | Turn |
|---|---|---|---|---|
| cap 2048 | 842 | 600 | STOP | 9–10 s |
| cap 2048 | **1962** | **72** | **MAX_TOKENS** → retry at 4096 | **18 s** |
| cap 4096 | 842 | 600 | STOP | 8.5 s |
| cap 4096 | **2383** | 651 | STOP | 14.9 s |

At 2048 a heavy think (2383) cannot fit *at all*: the JSON is guaranteed to be cut, so the
turn always pays for a second call. At 4096 the same thinking fits and the answer arrives in
one call — and run 3 shows what the old cap was costing in *content*: 10 citations and 1133
characters at 4096, against 6 citations and 1001 characters after a truncation-retry.

Successful-call latency is unchanged by the cap (8.5–11 s measured at 2048, 4096 and 8192), so
raising it trades nothing for the normal case. Shipped defaults are now **4096 / ceiling
8192** (`CHAT_MAX_OUTPUT_TOKENS`, `CHAT_MAX_OUTPUT_TOKENS_CEILING`), in `settings.py` and
`.env.example`, with a test that pins the floor and the reason. A deployment that never set
either variable picks the new defaults up on its next deploy.

## 4. What is not built

1. **The board** — a publishable-question table (question, answer, citations, category,
   ask-count, approved-by), an admin action, the Waiting state, and the filter.
   `EscalatedQuery` already carries question, reason, status, answer and answered-by.
2. **The answer page** — a slugged route, the clause block, *what this does not cover*,
   *questions next to this one*, and `noindex` for a gap page.
3. **The consent control** — *"Add this question to the public questions database"*, opt-in,
   with the review promise the card then has to keep.
4. **The two prerequisites every shape needs** — a document `code` on a citation (today a
   citation carries a *title*, so nothing is clickable) and a way to open a document at its
   printed page (`document_file()` serves `as_attachment=True`, so a `#page=76` fragment
   downloads instead of landing).
5. **The trace console** — `/console/ask/`, staff-only, outside `_public.PAGES` like `/uat/`:
   question, retrieval with arms and ranks, the prompt **rebuilt** from stored data and
   diffed against today's builder, and the response with the audit's verdict. Cheap: 
   `grounding`, `citations`, `refusal_checks`, `prompt_version` and `corpus_fingerprint` are
   already stored. Gaps: `grounding` keeps no arm/rank/score, and `cached` is not recorded.
6. **The wider-reading tier** — no documents behind it. It cannot ship as a checklist of
   names that do nothing.
7. **The rewrite (stage 2)** — deliberately not bought. It is what a follow-up needs in
   order to become a *public card* (a composite question is not a title), not what it needs
   in order to be answered.

## 5. Requirements

1. **No new claim.** Wider reading is never a certification claim; it is labelled *not
   assessed against* wherever it contributes. `test_claim_discipline.py` must keep passing.
2. **Membership is not certification** on any surface that lists questions or answers.
3. **Refusal stays warm and is never an error**, including on a card and on a page.
4. **Nothing is published without a person.** The consent label says an administrator reads
   it, so the code must make that true: a card is invisible until approved.
5. **The cache is not the archive.** A board needs a table; a one-hour cache entry is not a
   record.
6. **`knowledge` never imports `core`.** The follow-up *policy* lives in `core`; the arm is
   generic and takes a lexical query.

## 6. Open questions

| # | Question | Blocks |
|---|---|---|
| 1 | **May a visitor's question be published?** A question is free text from a public form, and D59 only settles retaining it. What is the consent wording, and what happens to a question naming a third party? | **Shipped on the conservative default (D64), awaiting confirmation:** opt-in, unticked, `AWAITING` until a person edits and approves. The edit is the redaction mechanism. |
| 2 | **What is the wider-reading tier pointed at?** KNF, JADAM, JMF, INF and Japanese Natural Farming have no documents in this repo. A tier that lists names with nothing behind them is decoration. | The source scope control |
| 3 | **Who curates, and how often is a card re-checked?** A card is a claim; a stale one is a claim we have stopped checking. | **Shipped on the default (D66):** the administrator, on re-approval, which bumps `checked_at`; the date is printed on every page. No automatic re-check. |
| 4 | **Does the answer page publish generated prose at a permanent URL?** If yes, the *"what this does not cover"* block is mandatory, not optional. | **Shipped on the default (D65):** yes, only for an approved card, with the block required by a test, `checked <date>` on the page and `noindex` on a gap page. |
| 5 | **Is the straw follow-up a prompt defect or a corpus one?** The model answers about wood because *"untreated"* is the wood row's condition. | The next prompt iteration |

## 7. Definition of done

- [x] The board ships with approved-only cards, and a Waiting list that is visible.
- [x] An answer page exists with a stable slug, the clause in full, and a copyable citation.
- [x] Following a citation opens the document at the passage it quotes (the ingested text,
      not a PDF page — see §4a).
- [ ] The trace console rebuilds a stored turn's prompt and shows the audit's reason.
- [ ] UAT signed by the product owner (`tests/uat/ask_surface_uat.md`). **Tests passing is
      not completion for a surface a human must judge.** Seven scenarios are drafted; none is
      signed.
- [x] The claim-discipline sweep still passes on every new route — and the two routes it is
      right not to cover carry a recorded reason and their own sweeps.
