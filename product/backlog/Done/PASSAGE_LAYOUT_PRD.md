# PRD: Passage layout — the document's lists, rendered as lists

**Status:** **Done** — built 2026-10-27 (the display-only option A, chosen by the product owner
after the concordance shipped), and **UAT Scenario 8 signed PASS** on 2026-10-28 as part of the
concordance signature (`tests/uat/concordance_uat.md` carries eleven **PASS** results, signed by Kobus (Product) against commit `4e02d71`; applied by `scripts/uat_signoff.py`. The PGS administrator, committee reviewer and consumer-member seats are still empty (D4).)
**Owner:** Product (the verbatim rule) · Build (the formatter)
**Public title:** Lists in the standard read as lists
**Summary:** Lists inside the standard now read as lists: lettered conditions and definitions no longer run together as one block of text.
**Public:** yes
**Opened:** 2026-10-27
**Origin:** reviewing `/documents/saoso-standard-v2.1/read/` at `S5.1.3` — lettered conditions render
inline as `a Sufficient free movement…`, with the hard wraps and double spacing of the extracted page.
**Related:** `CONCORDANCE_PRD.md` §2/§6.3 (the reader), D67 (text, not PDF), D53 (the corpus artefact),
`knowledge/reading.py`, `knowledge/reflow.py`, `knowledge/corpus.py`.
**Plan:** `PASSAGE_LAYOUT_PLAN.md` · **UAT:** `CONCORDANCE_PLAN`'s `tests/uat/concordance_uat.md` gains
one scenario (`passage layout`).

---

## 1. The problem, measured

The reader renders `DocumentChunk.text` with `linebreaksbr`. That text is the **extracted page**:
`pdftotext -layout` preserves the paper's line breaks, the paper's indentation as literal spaces, and
— for SAOSO, which is printed double-spaced — a blank line between every printed line.

Measured on the shipped corpus, 2026-10-27:

| Fact | Number |
|---|---:|
| Chunks containing a list marker | **77 of 366** |
| Lettered items (`a`, `b`, … — no punctuation printed) | 272 |
| Numbered items (`1.`, `2.`) | 70 |
| Roman items (`i.`, `ii.`) | 69 |
| Non-blank lines that are mid-sentence wraps (long, no terminal punctuation) | **25%** |

`S1` — Definitions — shows a fourth problem, and it is the worst of them. The chunker overlaps
adjacent chunks on purpose so retrieval can see both sides of a boundary; `S1` is **eight chunks and
five of its boundaries repeat 21–57 words** (measured 2026-10-27). The reader printed chunks as
separate passages, so the definitions page repeated the previous chunk's last paragraph before
continuing — and every term (`ACB`, `Habitat`, `Extensive Farming`) was glued to its definition.

Three consequences, all visible in one clause (`S5.1.3`):

1. **HTML collapses the hanging indent** (15 literal spaces) to one, so the marker runs into the
   sentence: `a Sufficient free movement…`.
2. **Every printed line becomes its own line on the page**, because a blank line separates them —
   prose reads as a ladder, not a paragraph.
3. **The markers carry no punctuation.** The text layer prints a bare `a` (both `-layout` and
   `-raw`); whether the paper prints `a`, `a.` or `a)` is not recoverable from the text. Adding a
   period to the *text* would be inventing a character the corpus does not hold.

## 2. What is decided

**The stored text does not change.** This is a **display-only** transform: `passage_blocks(text)`
turns one chunk into blocks (paragraphs, headings, lists). Nothing is written back; retrieval,
chunking, embeddings, anchors and the citation audit are untouched.

Three rules make it honest:

* **The words, their order and their punctuation are unchanged.** Only whitespace between words is
  normalised, and hard-wrapped lines are joined. The one other change is the **`## ` prefix** the BPP
  artefact carries as markdown heading syntax — it is removed for display and the guard accounts for
  it.
* **Markers are presentation.** A lettered item renders inside `<ol>` with a CSS marker (`a.`), so
  the period is the browser's list marker, not a character added to the document. The printed marker
  is kept in the block's `marker` field, so a future corpus artefact that *does* print `a.` needs no
  change here.
* **Lossless by construction, and guarded.** `flatten(blocks)` reproduces the chunk's text
  (whitespace-normalised). A test asserts that over **every chunk of the real SAOSO ingest**, so the
  formatter cannot silently drop a line, duplicate one, or swallow a marker.

The reader's provenance sentence changes from "reproduced without editing" to the narrower, true
claim: *"the words and punctuation are unchanged; line breaks are reflowed for reading."*

## 3. The blocks

| Block | Fields | Rendered as |
|---|---|---|
| `Paragraph` | `text` | `<p class="passage__text">` |
| `Heading` | `text` | `<p class="passage__heading">` (the document's own heading, not a page heading) |
| `Term` | `text` | `<p class="passage__term">` — a glossary term or a printed sub-heading |
| `ListBlock` | `style` (`lower-alpha`, `decimal`, `upper-alpha`, `lower-roman`, `disc`), `start`, `items` | `<ol class="passage__list passage__list--…">` with `start` when it does not begin at 1 |
| `ListItem` | `marker` (as printed), `text`, `children` (lists only) | `<li>` plus a nested list when present |

**Grouping rules**, each found by reading real clauses:

1. **Sequence decides the list, not indentation.** SAOSO's indents are unreliable (`S5.6` prints its
   first item at column 8 and the rest at 0); `a, b, c …` is one list because the letters continue.
   A marker that does **not** continue the sequence starts a new list — which is how `S2.1.4`'s second
   `a…h` list is kept separate from its first `a…c`.
2. **A change of marker family at a greater indent nests.** `S8.1` is `a` → `i.`/`ii.` → `b`; OPP
   `§4.5` is `1.`/`2.` → `a.`/`b.` → `1.` again (the restart ends the outer list and starts a new
   one).
3. **Continuation lines belong to the item above them** when their indent is between the marker's
   indent and the body column + 4. This keeps `pigs: … for poultry: …` inside `S5.1.3`'s item `f`,
   and SAOSO's glossary definitions (body column 3, text at column 0) inside their `a` item. A line
   indented far past the body column (a centred heading such as *South African specific*) ends the
   list and becomes a paragraph.
4. **A printed heading is not a list item.** `1. DEFINITIONS` and `21. WINE MAKING` are headings: a
   numeric marker whose body is on the chunk's first line and is all capitals. A *lettered* marker
   whose body is all capitals (`a  ACB`) is still an item — that is SAOSO's glossary.
5. **A centred line is a heading.** SAOSO centres `Regional or other exception` and
   `SOUTH AFRICAN specific` inside a clause; a short line indented far past the body column cannot
   be body text, so it renders as the document's heading. `SECTION B` and its part title are a
   two-line centred block and render the same way.
6. **A short standalone line followed by prose is a term.** `ACB`, `Habitat`, `General Principle`,
   `Buffer Zones`: one to eight words, no terminal punctuation, followed by a longer line that
   starts with a capital. That is what turns the definitions page from a wall of text into a
   glossary. A wrapped sentence fails the test because its continuation starts lowercase.
   "South African specific" is centred, so it is a heading, not a term.
7. **The chunk overlap is removed for display.** `strip_overlap()` trims the words a passage's
   first line shares with the passage above it (at least six words, same printed section), so a
   retrieval feature does not leak into the reading surface. The stored text is untouched; only
   `S1`'s five boundaries are affected today.
8. **Anything that does not parse is a paragraph.** The formatter never raises and never drops text;
   an unrecognised shape is prose.

## 4. Non-goals

* **Not an ingest change.** `DocumentChunk.text` is the citation evidence; reflowing it at ingest
  would break the audit's verbatim property, move anchors, and require `--force` (which drops
  `ChatMessage.retrieved_chunks`). D53's artefact is the place structural fidelity ultimately lives.
* **Not punctuation recovery.** If the paper prints `a)` and the text layer lost it, that is a corpus
  review question for the SAOSO artefact (D53), not something a view may invent.
* **Not typography.** No drop caps, no justification, no hyphenation changes; the design system
  already governs the type.
* **Not tables.** Appendices 1–7 are prose chunks, and Appendix 2 is already one chunk per reviewed
  row (`knowledge/tables.py`); a table renderer is a different decision. **Superseded 2026-10-27:**
  `ready/READER_STRUCTURE_PRD.md` makes that decision (D70.1) — Appendix 2 renders as the paper's
  table from reviewed structure data. This line is kept as the record of what was out of scope here.

## 5. Risks

| Risk | Guard |
|---|---|
| A line is dropped, duplicated or re-ordered | `flatten()` equality over every chunk of the real SAOSO ingest, in the gate |
| A list is invented where the page prints prose | Sequence + family rules, and the fallback-to-paragraph rule; a unit test pins `a ` (one space) as prose |
| A heading is swallowed into the item above it | The body-column tolerance; `S2.1.4` and `S5.1.3` are pinned tests |
| A quotation no longer reads contiguously on the page | Quotes are matched whitespace-normalised by the audit; the reader's own guard asserts the lossless property, and the UAT checks a citation landing on a rendered list item |
| The page's indexable text changes shape (SEO) | Same words; paragraphs and lists only |

## 6. UAT impact

`tests/uat/concordance_uat.md` gains **Scenario 8 — a clause reads as the document prints it**: open
`S5.1.3`, and judge whether the six conditions read as a list (indented markers, hanging
continuations) and whether the paragraph above them reads as a paragraph. What no test can decide:
whether a reader trusts the page as a reproduction of the paper.
