# PRD: The concordance — the standard on one screen, and a citation that opens a line

**Status:** Ready — the eight questions in §7 were decided by the product owner on 2026-10-27
(`PGS_PLATFORM_SPEC.md` §18.3 **D68**), the argument is in
`product/design/d68_concordance_open_questions.html`, and the work is planned task-by-task in
`CONCORDANCE_PLAN.md` (11 tasks, its algorithm dry-run against the live corpus). **Nothing is built:**
nothing beyond the reader at `/documents/<code>/read/` exists yet.
**Owner:** Product (shape, publication), Build (the derivation in §5)
**Opened:** 2026-10-27
**Origin:** the ask-surface UAT, scenario *"Following a citation opens the document at the passage
it quotes"* — the reviewer's answer was that a citation should offer **"View this line"**, open the
concordance **in a new tab**, and land on the **section that was selected**.
**Related:** `ASK_SURFACE_PRD.md` §4a, `PGS_PLATFORM_SPEC.md` §18.3 D62 (option B) and D67 (a
citation links to text, not a PDF page), `product/design/d61_ask_interface_options.html` option B,
`CORPUS_CANONICAL_FORMAT_PRD.md` (D53), `knowledge/sections/registry.py`, `knowledge/tables.py`.
**Plan:** `CONCORDANCE_PLAN.md` · **UAT:** `tests/uat/concordance_uat.md`

---

## 1. What is being decided

Option B of the five shapes: **the corpus becomes the navigation**. The document's own structure is
a tree; choosing a branch shows that section's text; a citation opens the branch containing the line
it quotes, in a new tab, with the tree showing where the reader is.

The question this PRD answers — for the product owner and for whoever builds it — is threefold:

1. **Does this need its own ingestion pipeline?** No. §4 shows why, and what would have to be true
   for that answer to change.
2. **How are the different input formats handled?** They already are, upstream. §5 lists each shape,
   what parses it, and what the concordance can and cannot show for it.
3. **What format does the concordance read from?** `DocumentChunk` — the same rows retrieval and the
   chatbot use. §6 is the contract, and §6.3 is the one thing that is *derived* rather than stored.

## 2. What already exists, so the scope is honest

The reader shipped on 2026-10-27 at `/documents/<code>/read/` (D67): the ingested text of one
document, in document order, with a flat contents list, in-document full-text search, one anchor per
section reference, `:target` highlighting, and — since the same day — a `?section=` parameter that
opens the branch containing a passage.

So this is **not** "build a viewer". It is: **change the shape of an existing surface** from a single
column of all 319 SAOSO passages into a tree plus one open branch, and change the citation's link
accordingly. The spike in §9 exists precisely to price that change, and §10 lists what it found.

## 3. Why change the shape at all

The reviewer's finding was not cosmetic. A citation that says *"Read it in SAOSO v2.1"* is a link to
300 KB of text; a citation that says *"View this line"* is a link to a clause. The difference is the
product's central claim — for a standard, an answer *is* a locator — and the current surface buries
the locator in the document it belongs to.

Two measured facts support the change:

* The document is small enough for a tree to be the navigation: **4 documents, ~101 printed pages,
  366 chunks** at the time of writing.
* The current page is heavy precisely because it renders everything: **333,481 bytes raw / 61,647
  gzipped, 319 passages, 4 queries** for SAOSO, measured 2026-10-27. Rendering one branch is a
  fraction of that, which matters on the connection a farm office actually has.

## 4. Does the concordance need its own ingestion pipeline?

**No, and it must not have one.** The pipeline that produces the corpus is unchanged by this
feature; the concordance is a *reader* of its output, exactly as the chatbot is.

| Stage | Artifact | Where |
|---|---|---|
| Source of truth | the four governed PDFs in `pgs_docs/` | hashed (`sha256`) on ingest, so the bytes are pinned |
| Canonical text (D53) | reviewed markdown artefacts `knowledge/corpus/<doc_key>.md` | generated from the PDF by `scripts/build_corpus.py`, reviewed by a person, read by `ingest_standard --from-corpus` |
| Structure | a **section parser chosen by data**: `StandardDocument.section_scheme` → `saoso` / `opp` / `heading` | `knowledge/sections/registry.py`; a new standard is a new parser module + a row, never a migration |
| Tables | Appendix 2's **30 reviewed rows**, one chunk per substance | `knowledge/tables.py` |
| Vectors | Gemini embeddings, frozen width (D3/D20) | `knowledge/embedding.py` |
| Stored | `StandardDocument` + `DocumentChunk` | `knowledge/models.py` |
| Consumers | retrieval (chat), the reader/concordance, the citation audit | `knowledge/services.py`, `core/services/_documents.py` |

The concordance adds **no producer and no transform**. It adds **one field and one migration** —
`StandardDocument.toc`, because §7.5 was decided *include*: the printed table of contents is the
honest shape of the standard and the only place the two mis-derived titles are correct (§10.5). That
is the case this section predicted (*"if the product wanted structure the chunks do not carry — the
printed TOC's blank sections — that is new data, not a new pipeline"*), so the pipeline is unchanged
and the data is a nullable JSON column.

Everything else it needs that is not a column is a grouping (§6.3), and a grouping computed per
request cannot drift from the corpus the way a second store would.

*What would still change the pipeline answer:* if a future edition's structure could only be obtained
by parsing the PDF at request time. It cannot: the reviewed artefact and the TOC parse are both
build-time, and neither is on a request path.

## 5. The input formats, and how each reaches the reader

The corpus is not one format, and the concordance does not flatten it. Each shape is handled
upstream; the third column is what a reader sees.

| Shape | Example | Handled by | In the concordance |
|---|---|---|---|
| Numbered clauses | `S5.1.9`, `S20.1.1` | `SaosoParser` | one branch per top-level number (`S5`), titled from the printed heading |
| Dotted sections with sub-refs | `§2.1`, `§4.5(2)(c)` (offsets in `sub_refs`) | `OppParser` | one branch per section; roman heading stubs merge with their decimal body (§10.2) |
| Unnumbered headings | BPP, the certification landscape | `HeadingParser` | one branch per top-level heading — **and half the landscape's branches are misnamed today** (§10.5), which §7.3 sends back to the artefact |
| Printed tables | Appendix 2, 30 substance rows | `knowledge/tables.py` (replaces the auto-chunks) | one branch, one passage per row — a citation names the row's text |
| Printed page numbering | `page` is the number **in the document's footer**, not the PDF index (D42); the cover is unnumbered; BPP prints none at all | ingest | shown as "printed p. N" where it exists, omitted where it does not |
| Documents with no corpus text | the 4 forms/checklists of the 8 published documents (D41) | — | **no concordance**. The reader already says so honestly rather than 404ing |

Two consequences worth stating plainly:

* **A citation only ever names a chunk.** Every shape above ends as `DocumentChunk.text`, so the
  concordance cannot show a "line" that retrieval could not have cited. That is the property that
  makes "View this line" checkable rather than decorative.
* **The vocabulary problem stays.** A visitor who types "cardboard" cannot browse to Appendix 2 by
  reading headings — the word is not in one. That is why search is part of this surface and not an
  addition to it, and why Option B was not chosen to replace `/ask/`.

## 6. What the concordance reads from

### 6.1 The chunk contract (unchanged)

`DocumentChunk`: `text`, `section_ref`, `heading_path`, `page` (printed), `anchor` (content-derived
locator for blocks the source never numbered), `sub_refs`, `token_count`, `embedding`,
`search_vector`. Plus `document` → `StandardDocument` (title, version, source_file, scheme, set).

### 6.2 What a branch is

A branch is a **top-level printed reference**: `S5.1.9` → `S5`, `§4.5(2)(c)` → `§4`, `Appendix 2`
stays whole (the OPP's `§II` converts to `§2` because its body is numbered `2.1`–`2.5`). Documents
with no numbering group by the first component of `heading_path`.

### 6.3 The derivation: grouping, titles and anchors (computed per request)

* `reading_anchor()` — the fragment a citation carries, derived from `section_ref` — **plus a
disambiguator derived from the passage's own words when more than one passage shares that reference**
(§10.7, decided as §7.8). `section_ref` alone survives a `--force` re-ingest, unlike a chunk id; an
index-derived `-N` suffix does not, and §I forbids a sequential id on a public surface.
* `concordance_sections()` — the tree: branches in document order, each with its passages and the
  first passage's page.
* Titles: **the stored TOC's title for the branch when there is one**; otherwise the printed heading
  when it is unique to that branch; otherwise the reference. A heading shared by several branches is
  a **divider** (`APPENDICES`), not a title. Measured: heading-only titling misnames `S1` and
  `Appendix 2` (§10.5), which is why the TOC is stored (§7.5).
* Reserved numbers from the TOC (`10 to 19`) render as rows that carry no passages (§10.8).

Nothing about grouping is stored, so nothing about grouping can disagree with the corpus. The only
stored additions are the TOC snapshot and the revised anchor — one field each. The cost is one extra
pass over one document's chunks per request; measured in the spike as **4 queries** end to end.

### 6.4 Deep-linking, and why it needs a query parameter

A browser never sends the URL fragment to the server. So the branch must travel in the query string
and the fragment is what scrolls to the passage:

```
/documents/saoso-standard-v2.1/read/?section=s5-1-9#s5-1-9
```

`?section=` accepts a **branch anchor or any passage anchor**, because the tree navigates by branch
while a citation names a passage. An unknown value falls back to the first branch rather than 404ing
(a stale link should still show the document).

## 7. Decisions (taken 2026-10-27 — SPEC §18.3 **D68**)

All eight were answered by the product owner on 2026-10-27, each accepting the recommendation below.
The argument for every option — including the two rows of practice that point the other way — is in
`product/design/d68_concordance_open_questions.html`. The "Cost of each answer" column is kept
because the cost does not disappear when the answer is taken.

| # | Question | **Decided** | Cost of the answer taken |
|---|---|---|---|
| **7.1** | Does the concordance **replace** the reader's flat view, or is it a second route? | **Replace.** One surface, two states; a second route is two derivations over one document forever. | A template + service change, and the deletion of `contents()`/`ReadingEntry` from `knowledge/reading.py`. |
| **7.2** | Citation link **copy and behaviour** | **"View this line"**, `target="_blank" rel="noopener"`, with a visually-hidden "(opens in a new tab)". | A template change. A new tab is nearly invisible on a phone; the announcement is the mitigation, and the UAT is where it is judged. |
| **7.3** | Do **all four** documents get a concordance, or SAOSO + OPP first? | **All four**, which means fixing the certification-landscape artefact first (§10.5) and re-ingesting that one document. | One artefact edit + one re-ingest. The alternative was an allow-list nobody remembers; the reason it was needed is that two of that document's "titles" are a price line and a seal name. |
| **7.3a** | *(amendment, 2026-10-27 — found while writing the plan)* **There is no landscape artefact to fix.** | **The two titles are reviewed data, not a corpus edit.** `knowledge/corpus/` holds one file — `bpp.md`; D53/D55 record that OPP, SAOSO and landscape are not yet converted, so the landscape is still read by `HeadingParser` at ingest. The plan therefore corrects the two names with `REVIEWED_BRANCH_TITLES` (two entries, keyed by source file and branch, in the `TABLE_ROWS`/`CORPUS_EDITS` idiom, each proved to match a real branch by a test). | Two entries and a test, in the slice. **The alternative — build the landscape artefact properly (the D53 follow-up) — is deliberately out of scope;** if it is taken up later, the reviewed titles delete themselves: where a printed TOC exists it is the source of names, never a hand-written map. |
| **7.4** | Where does the tree live in the page — sticky left column, or above the pane? | **Sticky column ≥900 px; below that, collapsed to the current branch behind a disclosure.** | Visual, and the UAT's hardest judgement. At 390 px, 22 rows of 44 px is ~968 px of scroll before any clause text. |
| **7.5** | Do we show the **printed TOC's blank sections** and any appendix divider rows? | **Yes — store the TOC** (`StandardDocument.toc`, the slice's only migration), show the reserved range *10–19*, and **state on the page which printed sections the corpus does not hold** (§10.6). | One nullable field + the `parse_toc()` wiring at ingest, which is not wired today (§10.8). The omission note is not optional. |
| **7.6** | Does the concordance also become `/documents/<code>/`, or stay at `/read/`? | **Stay at `/read/`.** Citations already point there, and `/documents/<code>/` is a download with an established meaning. | None. A move would be a redirect, a new citation format and a broken-link audit. |
| **7.7** | Is a branch page `noindex`? | **Indexable**, with the document title and section in the `<title>`, and `rel="canonical"` to the `?section=` form. | A title tag and a canonical link. There is no `sitemap.xml` and no `robots.txt` in the project, so nothing else is at stake. |
| **7.8** | *(added by measurement — not in the original list)* How is a passage anchor made unique when 15.6% of passages share one? | **From content, not from position**: derive the disambiguator from the passage's own words, keep the bare anchor as an alias, and guard it with a test over all 366 passages. | §10.7. The stopgap — make citations use the reader's `-N` suffix — fixes the wrong-row landing but keeps an order-derived identifier on a public surface, which §I forbids. |

## 8. Non-goals

* **Cross-document concordance.** One document per page. A tree spanning four documents is a
  different navigation problem, and a citation already names its document.
* **Browsing as a substitute for asking.** `/ask/` stays the entry point; the vocabulary problem in
  §5 forbids the reverse.
* **Editing corpus text from the reader.** Text is reviewed in the artefact (D53), never in a view.
* **The worksheet (Option D).** Separate shape, separate decision.
* **The trace console and the wider-reading tier.** Still owned by `ASK_SURFACE_PRD` §4.

## 9. The spike, and what to do with it

A spike was built before this PRD to price the change: it groups chunks into branches, resolves
`?section=` to a branch, and rewrites the citation link. It is **not committed and not to be
resumed** — the tree it changed is shared with another session's work, so it was saved as a patch
and reverted: `_scratch/concordance/spike.patch` (gitignored; ask the product owner's machine, not
the repo). Read it as evidence for §10, not as a starting point.

What the spike proved, on the real corpus:

* the derivation runs on all four documents with no per-document branching: **SAOSO 22 branches /
  319 chunks, OPP 8 / 30, BPP 4 / 9, landscape 6 / 8** — every chunk accounted for;
* one branch rendered instead of all of them, which is where the weight reduction comes from;
* three shapes break naive grouping, and each is now a rule (§10.1–§10.3).

What the spike did **not** establish: the page's weight after the change (only the before-number,
§3), the mobile layout, or any of the UAT judgements in §11. Its test file also had three wrong
assertions (a placeholder string the fixture never contained) — proof that the assertions were
written from memory rather than read off the data, which is `testing_hazards.md` §1.6's shape.

**Superseded by measurement (2026-10-27).** The spike grouped correctly and titled incorrectly, and
it did not look at the anchors at all. Re-running its derivation over the live corpus produced four
findings it could not have made: branch titles are wrong on the branches that matter (§10.5), the
corpus is 22 of 28 printed sections (§10.6), 57 of 366 passages share a citation anchor (§10.7), and
the TOC parse the PRD leaned on has no production caller (§10.8). The spike remains evidence for the
*mechanics* of the change; it is not evidence that the change is correct.

## 10. Findings that must survive into the plan

These are the reason this PRD is not just a route rename. Each was found by running the derivation
over the shipped corpus, and each will silently produce a wrong contents list if it is not tested.

### 10.1 A section's opening chunk is the printed title, with no heading trail

SAOSO prints `1. DEFINITIONS` as a chunk that carries `section_ref=S1` and **no** `heading_path`;
the trail only begins at the sub-heading that follows (`2. ORGANIC ECOSYSTEMS > 2.1 …`). Grouping on
the heading therefore files the section's title page under the *next* section. Rule: grouping is by
reference first, heading second.

### 10.2 The OPP numbers its sections twice

It prints `§II` as the heading and numbers the body `2.1`–`2.5`. Without the roman→decimal
conversion the same section appears twice in the tree, once as a one-line stub. Rule: `§II` → `§2`
before grouping.

### 10.3 A heading shared by several branches is a divider, not a title

SAOSO prints `APPENDICES` above Appendices 1–7. Naming seven branches "APPENDICES" gives a reader no
way to choose one. Rule: a heading used by more than one branch falls back to the reference.

### 10.4 `?section=` and the fragment are two different mechanisms

The fragment scrolls; the query parameter selects. Sending only the fragment means the server
cannot know which branch to render, and the reader lands at the top of the document with the target
below it — which is exactly the "does the citation lead anywhere" complaint this feature answers.

### 10.5 The first heading in a branch is not the branch's title

Found by re-running the derivation over the live corpus on 2026-10-27 (the numbers in this section
and in §7 come from `_scratch/concordance/verify_branches.py`, a read-only copy of the spike's
derivation). Taking a branch's title from its first heading fails on exactly the branches a reader
consults most:

| Branch | Derived title today | The printed title (`parse_toc`) |
|---|---|---|
| SAOSO `S1` | `Section 1` (no chunk in the branch carries a heading) | `1 · Definitions · p.22` |
| SAOSO `Appendix 2` | `Appendix 2 – Farmyard manure, slurry and urine` (its first sub-table) | `Appendix 2 · Fertilizers Conditioners and Soil Conditioners · p.76` |
| Certification landscape | `R500`, `PGS SA.` | no TOC — these two lines are mis-detected as headings by `HeadingParser` |
| BPP | `INTRODUCTION`, `DEFINITION OF …`, `GENERAL PRINCIPLES`, `CONCLUSION` | no TOC — acceptable: 9 passages, 4 branches |

Rule: **title a branch from the stored TOC when there is one, and from the heading only when the
heading is unique to that branch** (§10.3). This is the second reason §7.5 was decided *include*: the
same field that shows the reserved range restores both titles.

### 10.6 The tree must say what the corpus does not hold

Measured 2026-10-27: SAOSO's stored pages run **22–88** while the printed standard's TOC has 29
entries covering pages **4–96**. The corpus is Section B plus Appendices 1–7; **Section A**
(Introduction, General, Minimum Inspection Requirements — printed pp. 4–11) and **Appendices A–C**
(pp. 93–96) were never ingested. The tree therefore shows **22 branches of the 28 printed sections
that carry text**, before the ten reserved numbers 10–19 are considered.

Rule: the page states which printed sections are absent. A tree presented as "the standard" claims
more than the corpus holds, which is the claim-discipline rule applied to structure instead of words.
This is not a corpus bug to fix in this slice — it is a boundary to publish.

### 10.7 15.6% of passages share an anchor, and the citation resolves to the first

Measured 2026-10-27: **57 of 366 passages** share their `reading_anchor()` with another passage —
`Appendix 2` ×30, `S1` ×8, `Appendix 1` ×6, BPP's `general-principles` ×6, and seven smaller groups.
`unique_anchors()` appends `-2`, `-3` … so the reader can tell them apart; `Citation.reading_anchor`
and `SearchHit.anchor` call `reading_anchor()` directly, so they cannot — a citation to 29 of
Appendix 2's 30 rows opens *Farmyard manure, slurry and urine*.

Two rules follow, and the second is the load-bearing one:

* the anchor must be unique **per passage**, derived from the passage's own words rather than from
  its index, because the index changes when the artefact is edited and re-ingested — an order-derived
  suffix is a sequential id on a public surface (`build_principles.md` §I);
* the guard is a test over the **real corpus**, asserting that every passage's own anchor resolves to
  that passage. A fixture cannot catch this: the fixture has three chunks and one duplicate.

The defect exists today, independently of this feature — a citation link shipped on 2026-10-27
already lands on the wrong row. It is tracked as `product/backlog/BugFixes/citation_anchor_collision.md`
and must not be closed by the concordance alone, because answer pages are wrong now.

### 10.8 `parse_toc()` has no production caller

§7.5's original note said the TOC parse "already understands the blank range". It does — and nothing
calls it. `knowledge/sections/toc.py` is referenced only by `test_toc_map.py` and
`test_section_parsers.py`, and `SaosoParser` explicitly *skips* TOC pages. Storing the TOC is
therefore parser-wiring plus a field, not reuse of a live path.

## 11. UAT impact

Scenario 3 of `tests/uat/ask_surface_uat.md` becomes the feature's acceptance test and its wording
must widen from the reader to the concordance. What a human must judge, and no test can:

* does following "View this line" leave the answer in place (a new tab) and arrive at **that line**,
  with the tree showing where the reader is;
* at 390 px, is the tree usable — can a reader with 22 branches find the one they are in, and does
  the pane still read;
* does an empty or missing branch read as honest rather than broken;
* does the tree make the standard's shape legible to someone who has never opened the PDF — **and
  does the page say plainly that Section A and Appendices A–C are not in the corpus** (§10.6), rather
  than implying the tree is the whole standard;
* does a branch read as correctly *named* — `Definitions`, not `Section 1`; `Fertilizers, conditioners
  and soil conditioners`, not `Farmyard manure` (§10.5).

The signed scenarios from the 2026-10-27 run remain valid for everything else: this PRD changes the
landing surface, not the answer page, the board or the citation audit.

## 12. Risks

| Risk | Why it bites | Guard |
|---|---|---|
| A new edition changes the numbering shape | §10.1–10.3 are data-shape assumptions; a reprint that drops the opener chunk or renumbers appendices silently re-sorts the tree | tests over the **real** corpus, not a fixture (§10's findings should be assertions) |
| The tree and the search disagree about which branch a hit is in | two ways to reach a passage, one of which selects a branch | one derivation function used by both (the spike did this; keep it) |
| A branch is titled from its first heading and misnames itself | §10.5: `Section 1` for *Definitions*, `Appendix 2 — Farmyard manure` for a 30-row table, `R500` for a price line | title from the stored TOC when present; a test that asserts the two known titles, not just the count |
| The page implies the tree is the whole standard | §10.6: Section A and Appendices A–C are not in the corpus, and the reserved range 10–19 is not text at all | the omission note is part of the template, and the UAT judges it (§11) |
| A citation opens the wrong passage | §10.7: the anchor is derived from `section_ref` alone, and 15.6% of passages share one | content-derived disambiguator + a guard test over all 366 passages; tracked in `BugFixes/citation_anchor_collision.md` |
| Claim discipline | the page reproduces the corpus verbatim, which contains "biodynamic" and "pasture raised" | the exemption and its proof already exist (`test_claim_discipline.py`); the page's own copy stays swept |
| "/read/" is now the wrong name for the surface | an address is a promise | §7.6 keeps it; a rename is a redirect and a new citation format |
| Scope creep into the printed TOC | §7.5 is the only part that needs new stored data | decide it explicitly or omit it; do not "just parse the PDF at request time" |
