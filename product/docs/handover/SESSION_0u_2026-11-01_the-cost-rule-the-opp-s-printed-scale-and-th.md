<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0u. 2026-11-01 (session 7) — the cost rule, the OPP's printed scale, and the refusal located

**State: green, committed in five slices.** `01bfec3` is the cost rule; `37b682a` is the OPP
artefact; `c255882` is the chunker fix; `61b640c` is the reader's two joins; `821efae` is the docs.
`fast.sh` **1533 passed / 1 skipped**, `verify.sh` **1545 passed / 1 skipped**, `pytest tests/e2e`
**71 passed**.

### 0u.1 What the assistant does now

| Question | Before | After |
|---|---|---|
| *"what is the yearly cost of membership"* | R100 + R500, 2 citations | **complete** — R100, the scale, transport, catering, the licence; grounded |
| *"what is the yearly cost"* | complete, 1 run of 5 refused | complete, grounded |
| *"what does it cost to join"* | complete | complete, grounded |
| *"What is the yearly cost to get certified, including the farm visit?"* | complete | complete, grounded — and it now separates initial from renewal |

`COST_QUESTION_RULE` is rendered by `build_prompt` **only** when `looks_like_cost_question()` fires,
so every other question's prompt is unchanged (the two prompt tests pin both directions).
`cost_question_warnings()` writes an advisory `review_notes` entry when a cost answer states no
limit; it never refuses, because a refusal and "the corpus cannot answer" look the same to a
visitor — which is this gap's own second finding.

**The four phrasings were re-measured, not assumed.** Before the rule, the membership phrasing also
answered *"farms below R250 000 pay a **renewal** fee of R900"*: the R900 is the renewal column, and
the chunk had two bare numbers with no labels. That is the same defect one layer down, and §2.3's
reviewed table is what fixed it. The two items were one report, and they are one session.

### 0u.2 What the reader does now

`/documents/opp/read/?section=ii` renders §2.3 as the printed grid — three column headers, six
bands, one row per band, then the notes under the table as prose. **Two joins were missing and
neither was visible from the landscape**, whose sections are unnumbered and one per branch:

- the branch was matched by the **section anchor**, but a numbered clause's reading anchor is its
  reference (`2-3`), while the artefact's section carries a heading slug; so the OPP fell back to
  prose with no error anywhere;
- the OPP's `II. Membership fees` branch holds §2.1–§2.5, and the match took the **first** section —
  §2.1, which has no table. A branch now resolves to its first section that has one.

### 0u.3 The corpus format gained rule 6, because the conversion was silently lossy

The OPP is the only governed document whose citations go three levels deep — `4.5(1)`,
`4.5(2)(c)` — and an artefact had nowhere to put a sub-clause printed *inside* a section. Converting
without it dropped three of §4.5's five addresses and left `test_opp_sub_refs_survive_into_the_database`
as the only thing that noticed. So:

- `<!-- sub: 4.5(2)(c) -->` opens a slice at the next text line, depth from the address, end from
  the next marker at the same or shallower depth — `any_level_end`, the rule `OppParser` already
  used, so the artefact reproduces the parser's **spans**, not merely its words;
- **the generator writes the markers**, from the parse of the de-columned `-layout` rendering the
  ingest uses. Drafted from `-raw`, the OPP lost five of §4.5's nine, because the raw rendering
  resets the left margin that the letters `a.`–`c.` hang off. Measured: 24 markers, 24 spans, each
  quoting the same words the PDF path quoted.

Also fixed, because it was found in the same place: the prose after a table row started with the
newline that ended the row, so §2.3's notes — the sentences that qualify every amount above them —
began with a blank line. `_prose_chunks` now skips leading whitespace, offsets and all.

### 0u.4 G10's second finding: one space, at a line break

    passage: … from our membership
             fees set out in 1.
             o Currently R500
    quote  : … from our membership fees set out in 1.o Currently R500

`audit_citations` compares `flat()`-normalised text, so the passage's newline is a space and the
model's `1.o` has none. Whitespace-removed it is an exact substring. The model invented nothing and
the corpus is right; the audit's normal form met a line-wrapped passage, and the visitor was told
the documents were silent. **Not fixed** — the PRD requires the decision in §18.3 first, and both
options are now written beside the evidence. This is the session's most useful finding: the refusal
had been invisible for a day because nothing records *why* a quote failed except the operator's log.

### 0u.5 Guards

**+40 test functions** (+64 collected) in the gate, and the ones that matter are the ones that were
watched failing:
8 corpus-format refusals (`sub:` with no text, a duplicate address, a `sub:` that repeats the
section, inside a table, misspelt), 2 of the 3 reader tests (removing `_documents.py`'s two joins
turns them red), `test_every_sub_clause_survives_with_the_same_span` (24 spans compared to the PDF
path), `test_each_band_is_its_own_chunk_and_still_cites_the_scale`, and the two prompt tests that
pin the cost rule's *absence* on an ordinary question.

### 0u.6 Two hazards the session paid for

`testing_hazards.md` §3.24: **"corpus is current" compares the artefact's hash and the chunk count,
not the derived text.** The chunker fix changed two chunks and `corpus_refresh --apply` said
"nothing to refresh"; only `ingest_standard --force` + `relink_evidence` replaced the stored text.
§3.25: **`build_corpus.py --force` silently deletes a reviewed table block** — it happened here, to
`opp.md`, and was caught only by the shape assertions.

### 0u.7 What is deliberately not done

- **The audit is unchanged** (0u.4) and **G10 stays open**: its acceptance criterion was an
  answer-level sentence with no automated assertion behind it, and the rule plus the advisory note
  is as far as that goes without a decision.
- **pdf 11's §6.5 labelling table** is still prose — the second table P4 names.
- **The OPP's row anchors are truncated at 128 characters** with the band's distinguishing words
  last (`…-initial-certification-and-renewal-r-250`). They are unique today and `reading_anchor`
  prefers `section_ref`, but a future band could collide; `test_anchors.py` is the guard.
