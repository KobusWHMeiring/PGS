<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0a. 2026-10-23 — `/ask/` became a board of answer pages, and citations became clickable

**This is the most recent slice, and it is not deployed.** D62 chose the shape on 2026-10-23;
this session built it (`product/backlog/In Progress/ASK_SURFACE_PLAN.md`, PRD §4a).

- **The board** (`PublicQuestion`, migration `core/0007`) is a content table with a publish flag,
  not the one-hour cache. A consenting question lands `AWAITING`; a consenting refusal lands
  `WAITING` and points at its `EscalatedQuery`. Only an administrator publishes, and the slug is
  generated from the **edited** question at that moment — the edit is the redaction.
- **The answer page** is `/ask/<slug>/`: the clause in full, *what this answer does not cover*
  (required, enforced by a test), the questions next to it, a copyable citation, `checked
  <date>`, and `noindex` on a gap page.
- **Citations are clickable for the first time.** `Citation` carries `document_code` and
  `reading_anchor`, and `/documents/<code>/read/` renders the ingested text with a contents
  list, in-document search and one anchor per section reference. **It is not a PDF page link**:
  the PDF is streamed as an attachment, and D67 records why the text is the better surface.
- **Two guards were proven by breaking them**, and one pre-existing defect was found:
  `publish_documents` wrote an absolute `source_path`, so the citation→document join could never
  match on a second machine (`testing_hazards.md` §1.32).
- **Not built, deliberately:** the trace console (needs arm/rank on `grounding`), the
  wider-reading tier (no documents behind it), the stage-2 follow-up rewrite.
- **UAT is drafted and unsigned:** `tests/uat/ask_surface_uat.md` — seven judgement scenarios.
- **The reader is measured, not assumed:** on the real SAOSO corpus it renders 333 KB raw /
  **61.6 KB gzipped** in 4 queries (319 passages); the PDF is 192 KB. Raw, the page is *bigger*
  than the file — on the wire, with nginx gzip on text/html, it is ~3× lighter. A search adds
  one query.

---
