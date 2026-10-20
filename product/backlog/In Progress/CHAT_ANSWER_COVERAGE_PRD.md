# PRD: Chat answer coverage — governing rules, table rows, and the gaps left

**Status:** In Progress — built 2026-10-21; UAT Scenarios 1, 2, 3, 9 and 10 unsigned
**Owner:** Build — grounded chat (sub-plan D), corpus ingestion (sub-plan B)
**Last Updated:** 2026-10-21
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
- Chat `RETRIEVAL_LIMIT` 5 → 8. Measured: 4.4.4 lands at rank 6.

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
