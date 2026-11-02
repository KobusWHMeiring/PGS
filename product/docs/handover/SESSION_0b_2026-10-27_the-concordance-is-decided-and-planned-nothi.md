<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0b. 2026-10-27 — the concordance is decided and planned; nothing is built

**Read `product/backlog/ready/CONCORDANCE_PLAN.md` before touching `/documents/`.** Eleven tasks,
77 steps, each test-first. The reader that shipped on 2026-10-23 is being replaced in place.

- **The decision is `PGS_PLATFORM_SPEC.md` §18.3 D68** — eight answers, all logged. The argument,
  the options and the rejected alternatives are in
  `product/design/d68_concordance_open_questions.html`; `ready/CONCORDANCE_PRD.md` §7 is the
  decision table, and §10.5–10.8 are the findings the plan inherits.
- **What changes:** `/documents/<code>/read/` renders the document's own printed structure as a
  tree with one open branch; a citation reads "View this line", opens a new tab, and lands on the
  passage it quotes; the page states which printed sections the corpus does not hold.
- **Three things were measured first and they are not in the PRD's original story** (all in
  `ready/CONCORDANCE_PRD.md` §10): the corpus is **22 of 28** printed SAOSO sections (Section A,
  pp. 4–11, and Appendices A–C, pp. 93–96, were never ingested); branch titles taken from headings
  misname `S1` and `Appendix 2`; and **57 of 366 passages share a citation anchor**, so today a
  citation to 29 of the 30 Appendix 2 rows opens the first one. That last one is filed as
  `product/backlog/BugFixes/citation_anchor_collision.md` — it is a live defect, not only a
  prerequisite.
- **`scripts/probe_concordance.py`** (read-only) prints the tree, the titles, the missing sections
  and the anchor ambiguity count for the corpus in the database. Run it before Task 1; the plan's
  §0.4 records what it printed when the plan was written (0 ambiguous anchors, 6 missing sections).
- **Do not measure anything before `python manage.py publish_documents`.** On a machine whose
  `PublicDocument` rows predate `4c94c09` they hold absolute paths, `corpus_for()` returns `None`,
  and the reader says "not published the text" for every document (§0.2 of the plan).
- **UAT is drafted and unsigned:** `tests/uat/concordance_uat.md`, seven judgement scenarios. This
  feature is not done without names in that table.
- **One amendment to a decision, recorded as §7.3a:** the landscape has no reviewed corpus
  artefact (`knowledge/corpus/` holds only `bpp.md`; D53/D55 say OPP/SAOSO/landscape are not yet
  converted), so its two wrong branch names are corrected with reviewed data
  (`REVIEWED_BRANCH_TITLES`) rather than a corpus edit.

---
