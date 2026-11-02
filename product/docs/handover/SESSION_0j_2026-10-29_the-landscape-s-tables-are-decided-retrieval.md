<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0j. 2026-10-29 — the landscape's tables are decided; retrieval gets a brief for the instrument it lacks

**Nothing was built in this session.** No migration, no code change, no test added, no corpus
re-ingested: **docs and decisions only** (`product/backlog/`, `product/design/`). The tree's only new
files are one PRD, one spike brief and one decision artifact; the only edits are to `PGS_PLATFORM_SPEC.md`
§18.3, two existing PRDs, `HANDOVER.md` and the generated index.

**The tree also carries work that is not from this session** — `core/services/_public.py`,
`core/static/css/{components,site}.css`, `core/templates/public/{home,become_a_member}.html`,
`sections/_fee_tables.html`, `sections/_key_facts.html`, the new `sections/_recognition.html`,
`sections/_why_join.html`, `core/tests/test_public_costs.py`, `product/design/DESIGN.md` and
`C1_BUILD_PLAN.md`, plus `product/backlog/todo.md` and the test-lane files (`scripts/fast.sh`,
`pgs/settings_test.py`, `pytest.ini`, `scripts/verify.sh`, `product/docs/context/*`). It appeared
**during** this session, so another instance was working in the same tree — attribute it before staging
anything, and stage this session's paths by hand rather than `git add -A`.

**What was asked.** A reader reported that *Certification Landscape › establishing-a-pgs-group* showed
the printed table as column-major soup, cut mid-cell. The diagnosis is in
`Refinement/LANDSCAPE_TABLES_PRD.md` §1 with the commands that reproduce it. Three findings, in
descending order of size:

- **Pages 1–3 of that document are not in the corpus at all** (measured: `0` chunks contain
  "Participatory Guarantee Systems", the six basic elements or the three certification routes). The
  text extracts fine; `HeadingParser` opens a section only at a CAPS line, page 2's only capitals line
  is the running header (suppressed by repetition) and page 3's are Title case (a documented miss).
  So "what is a PGS?" is uncitable, and the miss is indistinguishable from a corpus gap.
- **`de_column` fires on 8 of the landscape's 10 pages**, five of which are 5-column tables. This repo
  already excludes five such pages elsewhere (SAOSO 2/82/83, OPP 4/11); landscape had no entry.
- **No extraction mode makes a cell quotable** — measured 1/5 (raw `-layout`), 2/5 (`de_column`,
  shipped), 0/5 (`-table`, which *is* loss-free: identical non-space character multiset). A table row is
  two-dimensional and a chunk is one; the flattening has to be eliminated, not tuned.

**Decided** (spec §18.3 **D72.1–D72.7**, argued on a decision page the product owner answered
2026-10-29: `product/design/d72_landscape_tables_questions.html`): a row on PDF 6 is a seal and the
artwork cell is its printed label; a fee is a cell, never a derived fact; **the reader renders the
printed grid**; the OPP's two table pages wait for their artefact; the page-break row belongs to one
table; **pages 1–3 enter as reviewed front-matter passages**; the exclusion ships with the rows in
**one** re-ingest.

**Decided, and this one relocated work** — spec §18.3 **D73**: table rows are stored in the **reviewed
corpus artefact**, not in `knowledge/tables.py`, and the vector is computed from a **stored context
column** (`title · column: value`), never from the bare cells. Consequences:
`LANDSCAPE_TABLES_PRD.md` §5.1/§5.2 (an N-cell `TableRow` and a `(doc_key, ref)` key) are **superseded**
and its step 2 — a key refactor — is **dropped**; the landscape's artefact conversion (P5) moves ahead of
its place in the rollout, because 10 pages is the cheapest of the four and it lets the front matter land
as a reviewer-added heading.

**Measured, and it constrains the artefact syntax** (`Refinement/TABLES_AS_DATA_PRD.md` §3a): a GFM pipe
table chunks as **one** chunk (rows are one paragraph); blank lines between rows **still** produce one
chunk (the chunker packs to ~800 tokens); and `<!-- cell -->` is **silently dropped** today because
`ANNOTATION` matches only `corpus|page|ref`. So a table's structure must be parsed *as structure* (like
`sub_refs`), one chunk per row must come from the table code, and a malformed table annotation must
**raise**.

**Also measured — a live retrieval defect, unfixed** (`TABLES_AS_DATA_PRD.md` §7 Q5): Appendix 6a's
twenty curated rows are **3–4 tokens** each (`Ewes / 13,3`) and they are *all twenty* of the corpus's
3–4-token chunks (Appendix 2 runs 5 chars `Guano` → 769). All 385 chunks carry a vector, fused by RRF
(k=60). `"laying hens"` retrieves page 85; `"how many laying hens per hectare"` returns **no hits** — the
row is reachable only by its own words. D73's context column is the fix; whether it helps is unmeasured.

**A correction the repo should keep.** Four questions were put to the product owner as preferences and
only three were product decisions. "Pure function vs stored column" is **engineering**, and the tell is
in `TABLES_AS_DATA_PRD.md` above §7: a product decision changes *what the product claims*; an engineering
decision changes *how a claim is served and checked*.

**Why nothing was built, and what is next.** Every remaining step depends on a decision now taken but not
yet implemented, and the corpus work is gated on the artefact's table syntax. The next session starts
with **`spike/RETRIEVAL_EVAL_SPIKE.md`**, and it is deliberately first: it records the **baseline on
today's corpus** before the table work changes anything, which is the only way the D73 comparison can
mean something. Its first command is in that file's §0. Then: the table block in `corpus.py` with a
failing guard on a malformed annotation, proven on landscape p4–p5.

---
