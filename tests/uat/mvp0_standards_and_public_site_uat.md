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

1. Seed the real corpus: `python manage.py seed_deployment && python manage.py publish_documents && python manage.py ingest_standard --all`
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
| An ungrounded question returns **exactly** `"I cannot find a definitive answer in the SAOSO standards."` and creates one `EscalatedQuery` with reason `INSUFFICIENT_CONTEXT` | `core/tests/test_chatbot_grounding.py` |
| No answer can cite a chunk outside the session's `StandardSet` | `core/tests/test_retrieval_scope.py` |
| The public surface contains no claim outside the four outcomes and the active seals — forbidding `pasture-raised`, `pasture raised`, `GMO free`, `biodynamic`, `chemical-free`, `spray-free` | `core/tests/test_claim_discipline.py` (grep-style assertion over rendered public HTML) |
| Rate limiting returns 429 past the per-IP budget | `core/tests/test_chatbot_guardrails.py` |
| Section-reference parsers extract `S20.1.1` (SAOSO) and `§V` / `§4.2(5)` (OPP) correctly, from **verbatim extracts of the shipped PDFs** | `knowledge/tests/test_section_parsers.py` |
| Ingesting each real document yields more than zero sections **with a non-empty `section_ref`**, and `sub_refs` offsets are non-overlapping and within bounds | `knowledge/tests/test_ingest.py` |
| Ingestion is idempotent on `sha256` — a second run adds zero chunks | `knowledge/tests/test_ingest.py` |
| Retrieval returns the SAOSO clause for a known query (recall floor) | `knowledge/tests/test_retrieval.py` |
| `knowledge` never imports `core` | `import-linter` contract, run in CI |
| Every seeded `Seal` other than the two active ones is `is_active=False` | `core/tests/test_seed_deployment.py` |

---

## Scenario 1 — Does the chatbot answer *from the standard*, or from general knowledge?

**Category:** grounding
**Setup:** Corpus seeded (pre-test setup complete). Open the chatbot on the public site.

1. Ask: *"What does the standard say about the minimum rest period for laying hens without artificial light?"*
2. Read the answer and its citations.

**Expected:** An answer with one or more citations naming a document and a section reference.

**Judgement:** Does the answer read as a *quotation of the standard* rather than a plausible-sounding summary of general poultry knowledge? A model answering from memory can produce something that reads correctly and is confidently wrong — only a person who knows the standard can tell the difference, and that is the whole purpose of this feature.

---

## Scenario 2 — Do the citations actually lead somewhere?

**Category:** citations
**Setup:** As Scenario 1, with `pgs_docs/saoso-version-2.1-2026.pdf` open beside you.

1. Take the section reference from the answer (e.g. `S20.1.1`) and find it in the PDF.

**Expected:** The cited clause exists, and its text supports the claim made.

**Judgement:** Is the cited passage actually *about* the question asked, or merely in the same neighbourhood? Topical-but-wrong citations are the failure mode that survives every automated check, because the reference does resolve — it just does not say what the answer implies.

---

## Scenario 3 — Does the fallback feel trustworthy or evasive?

**Category:** honesty
**Setup:** As Scenario 1.

1. Ask something the standard genuinely does not cover, e.g. *"Which fertiliser brand should I buy for tomatoes in George?"*
2. Repeat with *"Is my neighbour's farm organic?"*

**Expected:** The exact string `"I cannot find a definitive answer in the SAOSO standards."` with an escalation action offered.

**Judgement:** Does the refusal read as a confident boundary rather than a malfunction? This is the moment the group's trust in the tool is either won or lost — a bot that hedges here will be assumed to invent answers elsewhere.

---

## Scenario 4 — Does the public site read as *the group's* site?

**Category:** identity / aesthetics
**Setup:** Open `/`, `/organics/`, `/how-it-works/`, `/members/`, `/become-a-member/`, `/contact/` side by side with the existing WordPress site.

1. Read the home page top to bottom.

**Expected:** The group's own voice, principles, members, fees and contact details are present and current.

**Judgement:** Does this read as Outeniqua PGS's site, or as a generic template with the group's name inserted? The existing site has years of accumulated voice in it — losing that in a rebuild would be a real regression that no test can catch.

---

## Scenario 5 — Afrikaans quality

**Category:** language
**Setup:** Set `preferred_language` to Afrikaans; browse the public site and ask the chatbot one question in Afrikaans.

1. Read the home page, the join page and one chatbot answer in Afrikaans.

**Expected:** Content is present in Afrikaans rather than falling back to English.

**Judgement:** Does it read as written by an Afrikaans speaker, or as a translation? Machine-translated Afrikaans is recognisable to every member of this group, and it would undercut the site's credibility more than leaving it in English would.

---

## Scenario 6 — Is the chat usable on a real phone?

**Category:** mobile
**Setup:** Open the public site on a real phone (iOS Safari and Android Chrome if available).

1. Ask a question that produces a long answer with three or four citations.
2. Try to read the whole answer and tap a citation.
3. Try typing with the on-screen keyboard open.

**Expected:** The answer is readable; the keyboard does not permanently obscure the input or the last part of the answer; citations are tappable.

**Judgement:** Is this genuinely comfortable for a farmer standing in a market, or does it merely pass a 390 px layout check? Touch-target size and scroll behaviour after the keyboard opens are only truly judgeable on the device.

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

---

## Scenario 8 — Does the site still make no certification claim?

**Category:** claim discipline
**Setup:** Browse every public page, including `/members/`.

**Expected:** Member names appear with the explicit disclaimer that membership is not certification.

**Judgement:** Does the site avoid implying that a member is certified? The automated claim-discipline check bans specific forbidden terms, but *tone* — a member list under a heading like "Our certified farms" — is exactly the kind of overclaim a grep cannot see. The OPP is explicit that the group's credibility depends on not doing this.

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Product | Kobus Meiring | | |
| PGS administrator | | | |
| Committee reviewer | | | |
| Consumer member | | | |

**Release gate:** all scenarios judged acceptable, or the exceptions recorded above with a decision to proceed.
