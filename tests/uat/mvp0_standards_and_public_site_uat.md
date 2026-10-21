# MVP 0 UAT — Standards Foundation & Public Shop Window

**Feature slug:** `mvp0_standards_and_public_site`
**Plan:** `product/backlog/In Progress/MVP0_PLAN_V2.md`
**PRD:** `product/backlog/In Progress/MVP0_PRD.md`
**Status:** Drafted **before** implementation (shift-left validation)
**Date:** 2026-10-18

---

## Purpose of this document

Per `build_principles.md` §VIII and the `writing-uat-tests` skill, **UAT contains only checks a human must judge.** If pytest, Playwright, a script or a grep can prove it, it belongs in the automated suite — not here.

The question for every candidate item is not *"does this need the app running?"* but **"could an automated test assert this outcome?"** A rendered page, a status code, a DB row and a derived count are all assertable. Every item below therefore carries a `Judgement:` clause naming the human-only call.

---

## Pre-test setup

Required before any scenario:

1. Seed the real corpus: `python manage.py seed_deployment && python manage.py publish_documents`, then ingest the four governed documents with the commands in `HANDOVER.md` §8 (`saoso`, `opp`, `bpp`, `landscape`).
2. Confirm the corpus is loaded: `python manage.py shell -c "from knowledge.models import DocumentChunk; print(DocumentChunk.objects.count())"` — expect several hundred chunks, not zero.
3. Have the source PDF open alongside: `pgs_docs/saoso-version-2.1-2026.pdf` and `pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf`.
4. Run: `python manage.py runserver`
5. Have a real phone available, plus a desktop browser.

---

## Automated coverage (NOT UAT — asserted by the suite)

Recorded here so the manual list is not padded with machine-provable work.

| What | Where |
|------|-------|
| Every public route returns 200 and contains its expected heading | `core/tests/test_public.py`, Playwright `tests/e2e/test_public_site.py` |
| `/health/` returns 200 with `db`, `redis`, `celery_broker`, `celery_worker` all `ok`; returns 503 when a dependency is down | `core/tests/test_health.py` |
| Each document on `/documents/` downloads with the correct content type, non-zero body, `%PDF-` header and the seeded download name; the served bytes are sha256-identical to `pgs_docs/` | `core/tests/test_documents.py` |
| A grounded question returns an answer whose every citation's `section_ref` exists in the retrieved chunk set | `core/tests/test_chatbot_grounding.py` |
| An ungrounded question returns **exactly** `"I cannot find a definitive answer in the SAOSO standard or the Outeniqua PGS documents."` (D17) and creates one `EscalatedQuery` | `core/tests/test_chatbot_grounding.py` |
| The model is never called when retrieval returns no chunks | `core/tests/test_chatbot_grounding.py` |
| No answer can cite a chunk outside the session's `StandardSet`; every citation's `section_ref` is in the retrieved set, every `sub_ref` is in the chunk, and every quote is a substring of the chunk | `core/tests/test_retrieval_scope.py` |
| The chat page works with JavaScript disabled, and HTMX is loaded on no other public page | `core/tests/test_chatbot_surface.py` |
| Repeated questions hit the answer cache; the history window and 500-character cap hold; token usage is stored per message | `core/tests/test_chatbot_guardrails.py` |
| The public surface contains no claim outside the four outcomes and the active seals — forbidding `pasture-raised`, `pasture raised`, `GMO free`, `biodynamic`, `chemical-free`, `spray-free` | `core/tests/test_claim_discipline.py` (grep-style assertion over rendered public HTML) |
| Rate limiting returns 429 past the per-IP budget | `core/tests/test_chatbot_guardrails.py` |
| Section-reference parsers extract `S20.1.1` (SAOSO) and `§V` / `§4.2(5)` (OPP) correctly, from **verbatim extracts of the shipped PDFs** | `knowledge/tests/test_section_parsers.py` |
| Ingesting each real document yields more than zero sections **with a non-empty `section_ref`**, and `sub_refs` offsets are non-overlapping and within bounds | `knowledge/tests/test_ingest.py` |
| Ingestion is idempotent on `sha256` — a second run adds zero chunks | `knowledge/tests/test_ingest.py` |
| Retrieval returns the SAOSO clause for a known query (recall floor) | `knowledge/tests/test_retrieval.py` |
| The column-laid-out pages are re-emitted in reading order, 107 single-column pages stay byte-identical, and no non-space character is lost on any of the 139 pages | `knowledge/tests/test_columns.py` |
| The BPP manure sentence and the SAOSO Appendix 2 condition are contiguous in **one stored chunk** after a real ingest | `knowledge/tests/test_ingest.py`, `core/tests/test_chatbot_grounding.py` |
| The verbatim corpus sentence is accepted by `audit_citations`; the model's recorded 2026-10-19 paraphrase is still refused | `core/tests/test_chatbot_grounding.py` |
| The landscape keeps its printed page numbers after de-columning; SAOSO/OPP/BPP `(section_ref, anchor, page)` sets are unchanged | `knowledge/tests/test_section_parsers.py` |
| A fixture is only evidence if the manifest records its pipeline and pre-transform page hashes | `knowledge/tests/test_section_parsers.py` |
| `knowledge` never imports `core` | `import-linter` contract, run in CI |
| Every seeded `Seal` other than the two active ones is `is_active=False` | `core/tests/test_seed_deployment.py` |

---

## Scenario 1 — Does the chatbot answer *from the standard*, or from general knowledge?

**Category:** grounding
**Setup:** Corpus seeded (pre-test setup complete). Open `/ask/` on the public site.

1. Ask: *"What does the standard say about the minimum rest period for laying hens without artificial light?"*
2. Read the answer and its citations.

**Expected:** An answer with one or more citations naming a document and a section reference.

**Judgement:** Does the answer read as a *quotation of the standard* rather than a plausible-sounding summary of general poultry knowledge? A model answering from memory can produce something that reads correctly and is confidently wrong — only a person who knows the standard can tell the difference, and that is the whole purpose of this feature.
**Result:** PASS · Kobus (Product) · 2026-10-21 — Didn't refuse, it gave both references which looks irght

**Observed 2026-10-20 (dev box, live provider):** this question currently **refuses** —
reproducibly, five attempts out of five, with `cached=False` on every one. The cause is
recorded as **G8** in `product/backlog/In Progress/CHAT_ANSWER_COVERAGE_PRD.md` §7: the
model cites the correct sentence from `S5.1.9` and then cites the *same* sentence again, as
a paraphrase, against a BPP passage with an invented `sub_ref`; the all-or-nothing audit
refuses the pair, which is the product working. The corpus, the retrieval, the cache and the
audit were each excluded by measurement. **This is an observation, not a result** — judge the
scenario as you find it, and record FAIL with this cause if the refusal is still what you
see. A fix is expected before the next sign-off attempt.

---

## Scenario 2 — Do the citations actually lead somewhere?

**Category:** citations
**Setup:** As Scenario 1, with `pgs_docs/saoso-version-2.1-2026.pdf` open beside you.

1. Take the section reference from the answer (e.g. `S20.1.1`) and find it in the PDF.

**Expected:** The cited clause exists, and its text supports the claim made.

**Judgement:** Is the cited passage actually *about* the question asked, or merely in the same neighbourhood? Topical-but-wrong citations are the failure mode that survives every automated check, because the reference does resolve — it just does not say what the answer implies.
**Result:** PASS · Kobus (Product) · 2026-10-21 — The clause opens but maybe good here to also have a link to that relevant pdf on th epage

---

## Scenario 3 — Does the fallback feel trustworthy or evasive?

**Category:** honesty
**Setup:** As Scenario 1.

1. Ask something the standard genuinely does not cover, e.g. *"Which fertiliser brand should I buy for tomatoes in George?"*
2. Repeat with *"Is my neighbour's farm organic?"*

**Expected:** The exact string `"I cannot find a definitive answer in the SAOSO standard or the Outeniqua PGS documents."` (D17, wide corpus) and an escalation action offered. The action should not promise more than it does: it must say the question was recorded, and clicking it must lead somewhere a person can actually be reached (`/contact/` currently shows `contact details to confirm` chips — see `ESCALATION_ANSWER_PATH_PRD.md`).

**Judgement:** Does the refusal read as a confident boundary rather than a malfunction? This is the moment the group's trust in the tool is either won or lost — a bot that hedges here will be assumed to invent answers elsewhere. And: does the follow-up leave you believing a person will answer — or that the promise is hollow?
**Result:** PASS · Kobus (Product) · 2026-10-21

---

## Scenario 4 — Does the public site read as *the group's* site?

**Category:** identity / aesthetics
**Setup:** Open `/`, `/organics/`, `/how-it-works/`, `/members/`, `/become-a-member/`, `/contact/` side by side with the existing WordPress site.

1. Read the home page top to bottom.

**Expected:** The group's own voice, principles, members, fees and contact details are present and current.

**Judgement:** Does this read as Outeniqua PGS's site, or as a generic template with the group's name inserted? The existing site has years of accumulated voice in it — losing that in a rebuild would be a real regression that no test can catch.
**Result:** PASS · Kobus (Product) · 2026-10-21

---

## Scenario 5 — Afrikaans quality — **NOT APPLICABLE (C3 deferred, D44)**

**Status:** ⏭️ **Not applicable to MVP 0.** The product owner deferred the bilingual shell on
2026-10-19 (decision **D44**): no human Afrikaans translator is available, and a machine
translation would undercut the site's credibility here more than English-only does. The AF
control in the header is `aria-disabled` by design and must stay that way.

**When C3 is picked up, this scenario applies unchanged:**

**Category:** language
**Setup:** Set `preferred_language` to Afrikaans; browse the public site and ask the chatbot one question in Afrikaans.

1. Read the home page, the join page and one chatbot answer in Afrikaans.

**Expected:** Content is present in Afrikaans rather than falling back to English.

**Judgement:** Does it read as written by an Afrikaans speaker, or as a translation? Machine-translated Afrikaans is recognisable to every member of this group, and it would undercut the site's credibility more than leaving it in English would.
**Result:** N/A · Kobus (Product) · 2026-10-21 — D44: Deferred out of MVP 0 by the product owner (2026-10-19, this session).

---

## Scenario 6 — Is the chat usable on a real phone?

**Category:** mobile
**Setup:** Open the public site on a real phone (iOS Safari and Android Chrome if available).

1. Ask a question that produces a long answer with three or four citations.
2. Try to read the whole answer and tap a citation.
3. Try typing with the on-screen keyboard open. Press **Enter** to send, then type a
   two-line question using **Shift+Enter** for the line break.
4. Send a question and watch the thread while the answer is still being written. Start
   typing the next question during the wait.
5. Press Enter on an empty box: the browser should block the send (required field), not
   post an empty question.

**Expected:** The answer is readable; the keyboard does not permanently obscure the input or the last part of the answer; citations are tappable. Enter sends without a page reload; Shift+Enter inserts a newline; the hint under the composer is visible and honest. The question appears in the thread immediately and the box clears while the answer is being generated; the response does not erase a question you started typing during the wait.

**Judgement:** Is this genuinely comfortable for a farmer standing in a market, or does it merely pass a 390 px layout check? Touch-target size and scroll behaviour after the keyboard opens are only truly judgeable on the device. On a phone keyboard, Enter may be labelled Send or Return — check that the behaviour the label promises is the behaviour that happens.
**Result:** PASS · Kobus (Product) · 2026-10-21

---

## Scenario 7 — Do the documents replace Google Drive?

**Category:** documents
**Setup:** Open `/documents/` on a desktop browser **and on a real phone**. Have the
`/forms/` page of the live WordPress site open beside it.

1. Download all eight: SAOSO v2.1, the OPP, Basic Production Principles, the certification
   landscape, the visit preparation list, and the three participant checklists.
2. Open at least the SAOSO standard and one checklist in the phone's own PDF viewer.
3. Read back the filename each download saved as.
4. Try to reach the workbook, a farm visit report or an application dossier by guessing a
   URL under `/documents/`.

**Expected:** each opens or downloads directly, with no Google sign-in and no "request
permission" prompt; the gated row offers `Request access` and leads to `/contact/`.

**Judgement:**

* **Completeness against what the group actually distributes.** The site publishes eight.
  The live `/forms/` page and the group's own filing will settle whether that is the right
  eight — and specifically whether `"SOP's"` is the OPP under another name (it is
  **assumed** yes; if not, a ninth document is missing).
* **The workbook's absence.** It is deliberately held back pending committee confirmation
  (D22). Is that still the group's decision, or should it be public?
* **Do the files open on a real phone?** Attachment headers, viewport-sized PDFs and iOS
  Safari's share sheet are device behaviours no test client can judge.
* **Are the filenames ones the group recognises?** `PGS-Farm-Visit-Checklist-Crops.pdf` is
  a decision, not a derivation — the right names come from the people who file them.
**Result:** PASS · Kobus (Product) · 2026-10-21

---

## Scenario 8 — Does the site still make no certification claim?

**Category:** claim discipline
**Setup:** Browse every public page, including `/members/`.

**Expected:** Member names appear with the explicit disclaimer that membership is not certification.

**Judgement:** Does the site avoid implying that a member is certified? The automated claim-discipline check bans specific forbidden terms, but *tone* — a member list under a heading like "Our certified farms" — is exactly the kind of overclaim a grep cannot see. The OPP is explicit that the group's credibility depends on not doing this.
**Result:** PASS · Kobus (Product) · 2026-10-21

---

## Scenario 9 — Is the column-laid-out corpus actually quotable on paper?

**Category:** corpus integrity (D46)
**Setup:** The four governed documents re-ingested **after** the column transform
(`python manage.py ingest_standard …`, which prints `N layout pages`). Keep
`pgs_docs/Basic Production Principles_ENG_PRINT.pdf` and
`pgs_docs/saoso-version-2.1-2026.pdf` open beside you.

1. Ask `/ask/`: *"Do I need to know where horse manure comes from before I can use it?"*
2. Read the answer and each citation. Find every quote on the paper page.
3. Ask the same question again in a **fresh conversation**.
4. Ask about the OPP labelling categories (§6.5): *"What does the OPP say about the
   'Self-claim organic' labelling category?"*

**Expected:**
- Step 1 is grounded (not a refusal), with at least one Basic Production Principles
  citation whose quote can be found on the printed manure page ("2. Soil Management",
  PDF p4, printed p2), and at least one SAOSO Appendix 2 citation whose quote is the
  condition attached to "Farmyard manure, slurry and urine" in the printed table.
- Step 3 still answers (not a cache artefact).
- Step 4 either answers with a readable quote or refuses — and the refusal is **not**
  caused by a mangled table. OPP PDF 11 is deliberately excluded (3-column table), so
  the expected outcome is a refusal that can quote the §6.5 **prose** (top of the page)
  and names the table as not queried — never a sentence assembled across its cells.

**Judgement:** For each citation, can you put your finger on the quoted words on the
printed page? A quote that only exists in the database is the defect this scenario
exists to catch.
**Result:** PASS · Kobus (Product) · 2026-10-21

**Observed 2026-10-20 (dev box, live provider):** the corpus gate passes — the stored
BPP chunk carries the whole sentence, the Appendix 2 condition is contiguous, and the
verbatim sentence is accepted by `audit_citations`. Two live turns were nevertheless
refused, for **model-side** reasons unrelated to the corpus: one returned a fabricated
`sub_ref` (`"FERTILIZERS AND SOIL CONDITIONERS"`, a heading, not a stored sub-ref), the
other inserted an ellipsis (`"…"`) into an otherwise verbatim quote. Both are the audit
correctly refusing an uncheckable citation; both are filed as a separate prompt/model
follow-up. **D47 (2026-10-20) implements option A of that follow-up:** the prompt now
requires a character-for-character quote, forbids an ellipsis, and tells the model to omit
`sub_ref` unless the passage lists it. **Re-run under `PROMPT_VERSION = "d47-4"`:** the
manure question returned a grounded answer with three Appendix 2 citations, all verbatim and
all `sub_ref=None`. That run cited **no BPP passage** — the model preferred Appendix 2's more
specific conditions — so the "at least one BPP citation" sub-check above is still for the
human to judge; it is not evidence that the BPP page is unquotable (the stored-chunk test
proves it is). With the vector arm live (D48) the re-run returned a grounded answer with two
verbatim Appendix 2 citations (`sub_ref=None`); BPP was retrieved at rank 4, so the same
sub-check still applies. A second check — *"can i use horse manure?"* — was accepted under
`d47-4` with six verbatim citations, after the BPP PDF 4 band override made the raw-manure
60-day rule contiguous. That is the corpus fix working on a second sentence; it still does
not produce a BPP citation.

---

## Scenario 10 — Does the assistant answer everyday input questions, and admit what it does not name?

**Category:** grounding / governing rules (D49, D50, D51)
**Setup:** Corpus re-ingested **after** the Appendix 2 table work, with embeddings:

```bash
python manage.py ingest_standard --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf --force
```

Keep `pgs_docs/saoso-version-2.1-2026.pdf` open at Appendix 2 (printed pp. 76–78).
`python scripts/probe_chat.py` prints the same suite with the passages and raw quotes,
which is faster than retyping them into `/ask/`; judge the answers here, in the UI, because
what the reader sees is the product.

1. *"Can I use cardboard from my neighbour?"* — expected: an answer that says the standard
   does not name cardboard, states the rule that governs it (Appendix 2 / 4.4.4 or the
   biodegradable by-products row), and cites it. It must **not** say cardboard is allowed.
2. *"Can I use straw mulch?"* — expected: permitted as a plant material, with **no**
   "only if not chemically treated" condition. That condition belongs to wood.
3. *"Can I use borax for boron supplements?"* — expected: cites the trace-elements row and
   the documented-deficiency restriction.
4. *"Do I need to know where my horse manure comes from?"* — expected: grounded, with the
   Appendix 2 farmyard-manure conditions; no regression from 2026-10-20.
5. *"What is the yearly cost to get certified, including the farm visit?"* — **known gap
   (G3):** the answer covers the assessment fee, transport, catering and the seal licence
   but omits the R100 annual membership fee (OPP §2.1). Record the omission; do not sign
   this item as passed until it is fixed.
6. *"If my ducks aren't fed organic food and I make compost from their bedding, will I still
   pass?"* and *"If a seed is not organic but I grow it organic will the crop be organic?"*
   — **known gaps (G1/G2):** currently refused for an unquotable enumeration. Record the
   refusal; these are the next corpus/prompt items.
7. *"How do I sign up?"* and *"If I save seeds from a non-organic seed, are those seeds
   organic?"* — expected: grounded (OPP §I; SAOSO 4.1.2).

**Judgement:** For 1–4, put your finger on every quoted word on the printed page. Then the
human-only question: does the cardboard answer read as *"here is what the standard requires
of this material"* or as *"cardboard is fine"*? A farmer will read it as the second unless
the wording is careful. For 5–6, is the gap visible to the reader, or does the answer look
complete when it is not?
**Result:** PASS · Kobus (Product) · 2026-10-21

**Re-checked 2026-10-21 (agent, dev box):** item 5 — *"What is the yearly cost to get
certified, including the farm visit?"* — currently **refuses** (`CITATION_AUDIT`, the same
cause as **G8**), and the R100 annual membership fee is still the open gap **G3**. Recorded
because this scenario's own text says not to sign that item as passed until it is fixed: the
PASS above is the reviewer's judgement of items 1–4, 6 and 7.

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Product | Kobus Meiring | 2026-10-21 | Accepted with G8 and G3 recorded (see the decision below) |
| PGS administrator | | | |
| Committee reviewer | | | |
| Consumer member | | | |

**Release gate:** all scenarios judged acceptable, or the exceptions recorded above with a decision to proceed.

**Decision to proceed (product owner, 2026-10-21):** MVP 0 is accepted with two defects
**recorded rather than absorbed** — **G8** (the model cites one sentence twice, so the chat
refuses on a re-run; `CHAT_ANSWER_COVERAGE_PRD.md` §7) and **G3** (the cost answer omits the
R100 annual membership fee). Both carry into MVP 1a. The record is not permission to weaken
`audit_citations`: a citation nobody can verify is the failure this feature exists to prevent.
**Seats:** the product owner has signed; the **PGS administrator**, **committee reviewer** and
**consumer member** rows above are still empty, so the OPP's three-voice requirement (D4) is
not yet met.

### Per-scenario results

| Scenario | Category | Result | Reviewer | Role | Date |
|---|---|---|---|---|---|
| 1. Does the chatbot answer *from the standard*, or from general knowle… | grounding | PASS | Kobus | Product | 2026-10-21 |
| 2. Do the citations actually lead somewhere? | citations | PASS | Kobus | Product | 2026-10-21 |
| 3. Does the fallback feel trustworthy or evasive? | honesty | PASS | Kobus | Product | 2026-10-21 |
| 4. Does the public site read as *the group's* site? | identity / aesthetics | PASS | Kobus | Product | 2026-10-21 |
| 5. Afrikaans quality — **NOT APPLICABLE (C3 deferred, D44)** | language | N/A | Kobus | Product | 2026-10-21 |
| 6. Is the chat usable on a real phone? | mobile | PASS | Kobus | Product | 2026-10-21 |
| 7. Do the documents replace Google Drive? | documents | PASS | Kobus | Product | 2026-10-21 |
| 8. Does the site still make no certification claim? | claim discipline | PASS | Kobus | Product | 2026-10-21 |
| 9. Is the column-laid-out corpus actually quotable on paper? | corpus integrity (D46) | PASS | Kobus | Product | 2026-10-21 |
| 10. Does the assistant answer everyday input questions, and admit what … | grounding / governing rules (D49, D50, D51) | PASS | Kobus | Product | 2026-10-21 |

**Results:** 9 PASS · 0 FAIL · 1 N/A — signed by Kobus (Product).

**Signed against:** commit `59f5e93` (clean), database `pgs`, generated 2026-10-21.
