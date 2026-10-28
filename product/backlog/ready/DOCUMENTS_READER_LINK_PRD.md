# PRD: The documents page offers the concordance

**Status:** **Ready** — small, decided, and independent of every open PRD. Build it in one task.
**Owner:** Product (what a reader is promised) · Build (one row action)
**Opened:** 2026-10-28
**Origin:** found while closing the reader-structure slice — the concordance is reachable from a chat
citation and from nothing else. A reader who lands on `/documents/` sees eight downloads and no way to
read any of them as text.
**Related:** `Done/CONCORDANCE_PRD.md` (the reader), `Done/READER_STRUCTURE_PRD.md` (its structure),
C2 (`PublicDocument`, `publish_documents`), DESIGN rule 8 ("a retired chip is not a finished feature"),
`core/tests/test_claim_discipline.py`
**Plan:** not written — one task, three steps (see §5)

---

## 1. The problem, measured

`/documents/` lists **eight** published documents. **Four** of them have ingested text, so their
concordance renders; **four** are forms and checklists with no text, so `/documents/<code>/read/`
answers "we have not published the text of this document yet" (an honest page, verified by UAT
Scenario 7).

| Published code | Text ingested | Concordance |
|---|---|---|
| `saoso-standard-v2.1` | yes — 319 passages | renders |
| `opp` | yes — 30 | renders |
| `basic-production-principles` | yes — 9 | renders |
| `certification-landscape` | yes — 8 | renders |
| `farm-visit-preparation` | no | "not published the text" |
| `checklist-crops` | no | "not published the text" |
| `checklist-crops-animals` | no | "not published the text" |
| `checklist-seed-production` | no | "not published the text" |

Nothing on `/documents/` links to `/documents/<code>/read/`. The page has one action per row —
**Download** — and the concordance is discoverable only by following a chatbot citation.

## 2. What is decided

**D1. A row with ingested text gains a "Read the text" action beside its download.** Same row, same
weight, no new page: the documents page stays a list, it just stops hiding half of what each document
is. The link is `core:document_reader` for that code.

**D2. A row with no ingested text gains nothing.** Not a disabled control, not a tinted chip, not a
tooltip. A form is published as a file; that is the whole truth about it, and DESIGN rule 8's chip
exists for a *pending* feature, not for an absent one. The reader page already explains the state for
anyone who arrives from a stale citation.

**D3. The order is one decision, not two choices per row:** Download first (it always exists), then
Read the text (when it exists). Consistency beats proximity.

## 3. Why not something bigger

* **Not a "preview" of the PDF.** D67 stands: the served file is an attachment, and the text view is
  the reading surface.
* **Not a doc-list redesign.** The eight-row list is right; it is missing one verb.
* **Not a per-document banner on the reader.** A citation must land on a line, not on a masthead.

## 4. What it touches

| File | Change |
|---|---|
| `core/services/_documents.py` | the row data gains the reader's URL when `corpus_for()` finds text — one field, computed once per row |
| `core/templates/public/documents.html` | one action link, conditional on that field |
| `core/tests/test_documents.py` | four rows have it, four do not, and no row links to a 404 |
| `tests/e2e/test_public_site.py` | the download click test's class already covers the row; assert the new action is a ≥44 px target |
| `tests/uat/concordance_uat.md` | Scenario 12 (see §5) |

`corpus_for()` is a query per row today; the page already calls `published_documents()` once, so the
implementation must **not** add eight queries — resolve the ingested set in one query
(`StandardDocument.objects.values_list("source_file", flat=True)`) and match in Python.

## 5. Acceptance — one task

1. Test first: `/documents/` renders a link to `/documents/saoso-standard-v2.1/read/` for the four
   ingested documents and **no** such link for the four that are not.
2. Guard the query count: the page stays at its current count (measure before, assert after).
3. Browser: the action is a real link, 44 px on a phone, and lands on the concordance.
4. **UAT Scenario 12** (append to `tests/uat/concordance_uat.md`, judged with the others):
   *From `/documents/`, a reader who has never used the site finds the SAOSO standard's text in two
   clicks, and knows why the checklist has no such link.* Judgement: does the page read as eight
   documents *you can read*, four of which you can also read as text — or as an inconsistent list?

## 6. Non-goals

* No search across documents (the reader searches one document; a corpus search is a different PRD).
* No "recently cited" or popular passages.
* No change to `/documents/<code>/` (the 503-on-missing-file rule stays).
