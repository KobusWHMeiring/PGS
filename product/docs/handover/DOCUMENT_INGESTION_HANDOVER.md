# Document Ingestion Handover — PDFs/books/papers → markdown, and why you probably don't need RAG

**Status:** transferable artefact. Written for the plant health / plant nutrition poster
project (corpus of books + journal papers + PDFs, compiled into printed posters).
**Source of the learnings:** the Outeniqua PGS `knowledge/` package — a working corpus
pipeline over four governed PDFs, with every defect recorded in
`product/docs/context/testing_hazards.md`. That repo needed what this document describes;
it did **not** need most of what it built.

**Read this whole file before touching the corpus folder.** The first three sections are
the decision; section 5 onwards is the machinery. If you only read one section, read §4
(the canonical artefact format) and §7 (the hazards catalogue).

---

## 1. The decision, stated plainly

| Question | Answer |
|---|---|
| Do we need RAG (chunk → embed → vector search) for this corpus? | **No.** Start with structured markdown + an index + agentic `rg`. |
| Is the ingestion flow (PDF → markdown) worth it? | **Yes — it is the entire job.** It is the only part you cannot skip. |

These are two different questions and they get opposite answers. The reason is that
"retrieval" is really two problems:

1. **Can the text be searched at all?** A PDF's raw bytes cannot be grepped for
   "blossom end rot". Extraction answers this. Without it the agent has nothing.
2. **Can the agent find the right 2 pages out of 400?** This is where grep vs. RAG is a
   real choice — and for this workflow grep wins.

**This task is compilation, not question-answering.** You are reading 40 sources once to
synthesise a poster, not serving thousands of ad-hoc queries. A compilation workflow
favours grep:

- **Exact match is a feature, not a limitation.** "2.5 mmol/L", "Ca:Mg 4:1", "Table 3",
  "cv. Hass", "NH₄⁺", "EC 1.8 dS/m" — embeddings are bad at these and `rg` is perfect.
- **Recall you can audit.** `rg -l` either finds it or doesn't. You can see *why* a source
  was chosen. A vector hit gives you a ranked list you cannot argue with, and on a poster
  you will have to defend every claim.
- **The agent reads a lot anyway.** Compilation means whole-source passes with notes,
  which is agentic reading — the thing RAG exists to avoid.

Grep loses in exactly three places. Check whether they apply to you before building
anything:

| Grep weakness | Applies here? | Mitigation |
|---|---|---|
| **Synonym drift** — same fact as "calcium deficiency", "tipburn", "blossom end rot", "BER", "Ca-related necrosis" | **Yes, badly** | `GLOSSARY.md` with synonym lists per concept. One cheap file, huge recall gain, fully greppable. |
| **Aggregation** — "which papers disagree on K:Mg ratios?" | Sometimes | Answer it from your notes files, not from retrieval. |
| **Scale** — 5,000 files with weekly additions | No, for now | Escalate per §10 when it becomes true. |

**Do not build:** chunking, embeddings, vector search, RRF fusion, a chunk-level citation
audit, an answer cache. All of that exists in `pgs/knowledge/` (~1,900 lines) and none of it
is needed to write posters. **Do build:** §3–§6 below (~1,000 lines of pure functions plus
one script).

---

## 2. Scale, so you can sanity-check the plan

Measured in the PGS corpus:

| Thing | Number |
|---|---|
| Governed PDFs | 4 (13–101 pages) |
| Pages processed | 139 |
| Final chunks (had we needed them) | 364 |
| Pure extraction/format code that matters | `extraction.py` 157 + `columns.py` 288 + `reflow.py` 116 + `corpus.py` 430 ≈ **1,000 lines** |

Token arithmetic, so you know what "doesn't fit in context" actually means. **Fill in your own
counts** — the shape of the conclusion does not change:

- ~500 words/page → 400 pages ≈ 200,000 words ≈ **260,000–300,000 tokens** per book.
- A journal paper of 8,000 words ≈ **11,000 tokens**.
- 3 books + 40 papers ≈ **1.3–1.5M tokens**.

So: you cannot summon the corpus, but an agent *can* traverse it in 30–80 tool calls if
each call is precise. That is what §8 (the map) is for. Without a map, the agent reads
whole papers to decide whether to read them, and burns its budget before writing anything.

---

## 3. The pipeline, in the order that works

Each step is a pure function over a page string. Keep them in that shape: no Django, no
PDF library, no clock, no locale. It is what makes them testable and re-runnable.

```
PDF ──▶ [1 extract -layout] ──▶ [2 de-column] ──▶ [3 rejoin hyphen wraps]
                                                          │
                          ┌───────────────────────────────┘
                          ▼
              [4 tables: separate -table pass] ──▶ [5 draft markdown with page markers]
                                                          │
                                                    [6 HUMAN REVIEW]
                                                          │
                                                          ▼
                                              corpus/<slug>.md  (text of record)
                                                          │
                                    [7 map: INDEX.md + GLOSSARY.md]
                                                          │
                                            [8 agent: rg → read → notes/ ]
```

**Step order is not arbitrary.** De-column *before* dehyphenating, because reflow assumes
line adjacency is reading adjacency. And both happen *before* the section parser, because
a parser that reads a stamp by position breaks the moment the layout changes (hazard 7.4).

### 3.1 Extract — one tool, one flag, one pinned build

```bash
pdftotext -layout input.pdf -        # the corpus contract
pdftotext -table  input.pdf -        # row-aligned, for verifying printed tables
pdftotext -raw    input.pdf -        # producer order, for the column fallback
```

`-layout` is not decoration: without it two-column pages interleave differently and any
footer-based page number moves. **Pin the build.** Poppler and Xpdf are both called
`pdftotext` and produce *different bytes* — different wrapping, different column
detection — and `-table` does not exist in poppler at all (it exits 99). Measured on a
VPS whose poppler 24.02.0 differed from the dev box's Xpdf 4.00: 15 failures and 61 errors,
every one an extraction difference.

```python
PDFTOTEXT_BIN = os.environ.get("PDFTOTEXT_BIN") or "pdftotext"   # read per call, not at import
```

Record the extractor name+version in every artefact's header. A green build on one machine
is not evidence the other machine reads the same document.

Fixtures (committed page text) beat live extraction: after the first extraction, tests read
the committed pages, so no gate assertion depends on a binary. `check_extraction.py`-style
script answers the separate, deliberate question "what would a new extractor build change?"
— and its answer is a **re-baseline**, not a refresh.

### 3.2 De-column two-column pages

`-layout` keeps both columns of a two-column page on one visual line:

```
The organic farm is an element
a. Mechanisms and practices to
within an environment or ecosystem.
increase levels of organic matter in
```

A human reads that. Grep cannot: no sentence spanning the gutter exists as a substring, so
a search for "levels of organic matter in the soil" returns **nothing** and the agent
concludes the source does not say it. That is the failure mode that matters — not a wrong
answer, a silent false negative.

Detect by geometry, not by document:

- A gutter column qualifies when ≥70% of the lines that *cross* it are blank at it, crossed
  by ≥6 lines, with each side holding ≥12% of the page's non-space characters.
- Measured: coverage 0.70–1.0 on column pages vs 0.16–0.17 on prose. The gap is wide enough
  that **no per-document allow-list is needed** — this is the property that makes it
  portable to your corpus.
- **Narrow the band to the columns no line writes into.** A long left-column line can
  overflow the gutter and still leave coverage >0.70, so the *maximal* band starts inside
  the left column and uncuttable lines pile up. Measured on one brochure: maximal band
  produced 66 lines that could not be cut; narrowed, **13** — losslessly.
- Re-emit as column 1 top-to-bottom, then column 2. A line with text *at* the band
  positions (a spanning heading, a footnote, a table row overflowing) is never cut; assign
  it to a column by its own start position.
- **Fallback is a no-op, never a guess.** No qualifying band → return the same string object.

Then record the pages that must NOT be transformed, as *data* with the measured reason:
a table of contents whose right column *is* the page numbers (de-columning detaches every
entry from its page — 29 entries → 8); 3- and 4-column tables whose cells are one line each
(every character survives but row association is destroyed). Discovery is generic; the
exceptions are a measured table, and a new edition that starts mis-detecting fails a test.

### 3.3 Rejoin hyphenated words the page wrapped

```
The percentage of non-organic feed may not exceed 10% dry matter per ruminant
and 15% dry matter per non-

ruminant calculated on an annual basis.
```

Whitespace-normalised, that is `non- ruminant` — which no reader writes and no citation
check can match. Measured 22 wraps across 139 pages (SAOSO 12, OPP 4, BPP 5, landscape 1),
every one a genuine compound: `post-harvest`, `in-conversion`, `non-organic`,
`cross-pollination`, `semi-sparkling`. Fixing this took a chatbot from refusing correct
answers to answering them, with no model change.

Rules that worked:

- **Keep the hyphen.** `post-harvest` → `postharvest` invents a spelling.
- **Cross blank lines.** Body text may be double-spaced, so the two halves are often a blank
  line apart. Requiring strict adjacency repairs almost nothing.
- **No dictionary.** Join only when a line ends `letter-hyphen` and the next non-blank line
  starts with a lowercase letter. That is decided by the page, not a word list — so it
  retargets to a new corpus with no data.
- Repair the *page*, never the search or the checker. Loosening the matcher accepts quotes
  that are not substrings of the document.

**Strip page furniture first.** The printed footer (`P a g e | 47`, a bare page number)
lands at every page boundary, so a clause continuing across a page had it injected
mid-sentence. Measured: **65 of 368 chunks** carried a footer inside a sentence. Read the
page number *before* you drop the line, or you lose the page.

### 3.4 Tables — the step that changes your answers, not just your text

This is the one that will bite a plant-nutrition poster hardest, because the payload of
your posters *is* tables: nutrient ranges, antagonism matrices, deficiency symptom keys,
application rates.

`pdftotext -layout` renders a two-column table on one line grid with the second column
**vertically offset**. De-columning cannot fix a table whose rows overflow the gutter, so a
spanning line is kept whole and you get:

```
Trace elements, e.g.: boric acid, sodium borate, calcium Use restricted to cases where…
```

The paper is correct. The chunk is not quotable — and worse, the *proximity* of a
condition to the wrong item made a grounded answer say straw must be untreated, a condition
the standard attaches to **wood**. A confident, cited, wrong claim. On a printed poster
that is the difference between a correction and a reprint.

What worked:

1. Use `pdftotext -table` **for tables only**. Row alignment is a property of the extraction
   *mode*, not something you can invent. (Xpdf 4.x only.)
2. **The pairing is reviewed data, not inferred.** Where the text is genuinely ambiguous —
   one condition printed beside three unconditioned rows — the reviewed pairing wins and
   the code does not guess.
3. **A row is the unit**, not a cell: one substance and its condition, left to right, top to
   bottom. An **empty condition is not permission** — say so explicitly in your notes.
4. **Cells are verbatim** substrings of the `-table` output of that page; the row text is a
   join that is not literally on the paper. State that exception and keep the row's page.
5. **Cross-page continuations are merged by hand and recorded**, never inferred. A sentence
   printed at the top of the next page belongs to the row above.
6. **Sub-headings are not rows.** "South African specific", "I. MINERAL ORIGIN" organise the
   table; they are not entries.
7. **A changed edition is a changed table.** Pin the reviewed rows with a golden test that
   checks every cell against the page, and fail loudly on a reprint.

For your project, prefer `marker`/`docling`/`pdfplumber` for table-bearing pages and
*verify* against `-table`, but understand the trade: any library is a different rendering,
and if your parsers were measured on `-layout` you now have two contracts. One extractor
per corpus, pinned, recorded.

### 3.5 Then draft, then review

Do not hand-type the markdown: a hand-typed corpus encodes the same assumption as its
reviewer and has zero provenance. Generate a first draft mechanically (§4), then have a
human read the **flagged delta** — the blocks the generator could not place — not the whole
document. That is the review queue the PGS spike proved works: 13 pages needed **5**
corrections, and those 5 produced **3** permanent generator improvements.

---

## 4. The canonical artefact format

This is the most transferable idea in the whole repo, and it was reached the hard way: four
sessions in a row were spent repairing extraction heuristics (columns, tables, hyphen wraps,
spans) because **the extractor was on the runtime path**, so every layout irregularity became
a production defect. The fix was to invert it — the extractor becomes a per-*edition* build
step, and the reviewed artefact is the **text of record**.

Apply it from day one. You will not regret it.

```markdown
<!-- corpus
doc_key: knott-manual
source: sources/Knott's Handbook for Vegetable Growers 5e.pdf
sha256: 2565e28b2cdbe11f7b97d0aa226ab07126949872e95186fece856156ff0cc775
generator: corpusgen v1
extractor: Xpdf 4.00 pdftotext -layout
-->
<!-- page: 3 printed: none -->
## Soil reaction and pH

Text here is verbatim. Blank lines included, because they are the
paragraph boundaries everything downstream relies on.

<!-- page: 4 printed: 2 -->
## Liming materials
```

Rules the reader enforces — each one is a silent corruption otherwise:

1. **A page marker before any text.** `<!-- page: N printed: M -->` — `N` is the **PDF index**
   (provenance: what any verification checks against), `M` is the number **printed on the page**
   the reader sees, or `none`. A block with no page is a block whose claim cannot be traced to
   paper. Make that an **error**, not a default.
2. **The printed number is not the PDF index.** Measured: one document's cover is unnumbered,
   so printed `70` is PDF `71`, and its TOC quotes the *printed* number. Confusing them is
   how a citation points at the wrong page. Store both, name which is which, and make
   functions take the coordinate explicitly (`appendix_for_page(71, coordinate="pdf")`) so a
   caller cannot guess wrong.
3. **Provenance is per block, not per section.** A section may span pages; the page marker in
   force when a block starts is that block's page. But a **block's provenance is a page
   *range*, not one page** — a paragraph can cross a page break, and splitting it at the break
   inserts a boundary into the middle of your most-quoted sentence.
4. **A heading is `#`-level markdown.** Depth builds the heading path; it is never part of a
   citation. Put the citation in an annotation (`<!-- ref: 4.5(2) -->`) immediately before the
   heading.
5. **Everything else is text, verbatim.** Do not "tidy" whitespace. A tidier that collapses
   blank lines changes every downstream boundary.
6. **Furniture never reaches the artefact.** Footers, registration blocks, running heads and
   printed page numbers are dropped at generation, exactly as the parser drops them.

### 4.1 Corrections are data, not comments

Every reviewed correction goes in a table beside the generator — **not** as a comment in the
markdown. A comment cannot fail a test; this table can:

```python
@dataclass(frozen=True)
class CorpusEdit:
    page: int          # PDF page
    original: str      # what the PDF produces there — proof the defect was real
    replacement: str   # what the artefact now says
    reason: str        # how it arose, so the generator improves rather than the symptom
    kind: str = "replace"   # replace | drop | move
```

The test then proves three things per edit: `original` **is** in the PDF-derived text for that
page (so you did not invent a defect), `replacement` **is** in the artefact (so the fix landed),
and a `drop` with no replacement is actually gone. Count them as a **ratchet**: the number may
only go down without a recorded reason.

That table is also where you discover generator bugs. Real entries from the PGS corpus, all
found by reading the artefact:

- The printed page number appears on its own line before the body in one rendering and glued to
  a footnote's last line in another. Furniture either way.
- A footnote is emitted at the end of the page, inside the sentence that carries its marker —
  so the most-quoted sentence in the document was unquotable. **Move** the footnote to the
  bullet holding the marker.
- The PDF's text layer has no spaces in one line (`Preventativemethods(`) — no extractor can
  recover them; only a human reading the page can.
- A four-principle strip repeats on four pages; the first occurrence carries the content, the
  repeats interrupt numbered lists.

### 4.2 Kill criterion

If **more than ~10% of blocks need edits**, the artefact is not cheaper than the extractor.
Stop, fix the generator, regenerate. Recorded because a review queue that never shrinks is a
sign you are hand-transcribing, not reviewing.

---

## 5. The generator + review loop

```
scripts/build_corpus.py --doc knott
    → corpus/knott.md (draft)
    → report: blocks the generator could not place, pages it fell back on
human reads corpus/knott.md against the paper, edits it
    → record each edit in CORPUS_EDITS
    → regenerate: byte-identical unless the PDF or generator version changed
```

Four rules that matter:

1. **Never overwrite a reviewed artefact without `--force`.** The generator cannot tell a fresh
   draft from a file a human corrected; only the operator can, so the default is to refuse
   rather than quietly undo a review.
2. **No timestamps in the output.** Output is a function of the PDF + generator version, so
   re-running is byte-identical and a new edition produces a reviewable diff. The review date
   belongs in git.
3. **Write with `newline=""`.** `Path.write_text()` writes CRLF on Windows, so the artefact —
   and its sha256 — differs between your dev box and a Linux box, which defeats the digest.
   Assert `"\r\n" not in text` if the digest is trusted.
4. **Anchors are verified, not trusted.** The generator declares an anchor that must be present
   on a page and **fails rather than writing** if it isn't, showing the actual page content in
   the error. Every page range written in a plan by hand was wrong in the PGS project: one
   started one page early, in the tail of the previous section, and would have grafted unrelated
   text onto a fixture. A fixture that does not match the document it describes is the failure
   that invalidates the entire build.

### 5.1 The `-raw` order oracle (use only if geometry fails)

`pdftotext -raw` keeps the producer's content-stream order — the only *order* oracle available
without a layout library — but drops spaces between text-show operations, so
`Sourced locally from neighbouring` becomes `Sourcedlocallyfromneighbouring`.

Measured on 139 pages: every page of every document is a **character-for-character permutation**
of its `-layout` rendering (multiset of non-space characters, per page). `-raw` invents and loses
nothing; only spacing and order differ. And the glue is repairable — split each glued token into
the run of consecutive `-layout` words that concatenates to exactly it. After repair, 11 of 13
pages of one brochure had *identical word multisets*, and those were exactly the pages whose
columns defeat the band detector.

**Gate it mechanically:** draft a page from `-raw` only when, after glue repair, its word
multiset equals `-layout`'s. An unrepairable token means the page is not clean → fall back to
geometry.

---

## 6. Verification worth porting

Every one of these exists because a guard was green while the thing it guarded was broken.
The repo's rule: **prove a guard can fail — break it, watch it go red, restore** — before
trusting it.

| Guard | What it proves | How it fails silently |
|---|---|---|
| **Traceability** | Every block is a contiguous slice of the pages from its marker onward | Asserting "contained in one page" fails a paragraph crossing a page break; asserting "starts on this page" is enough |
| **Character multiset equality** | Artefact == PDF-derived text, minus declared edits, and nothing else | Passes when the transform never ran (a no-op is also loss-free) |
| **Identity equality** | `(ref, anchor, printed_page, heading_path)` identical between artefact path and PDF path | Makes the migration reversible; without it you cannot tell which path produced a corpus |
| **Pinned page set that MUST change** | The transform actually transformed | Pair with the multiset test; pin one literal count so a detector regressing to zero cannot drag the set with it |
| **Loss-free, by construction** | coverage 1.00 ⇒ nothing dropped but spaces no line writes | A synthetic page whose text overflows the gutter looks like a bug while the code is right — build synthetic pages that *respect* the band, and test detection against real bytes |
| **No `\r\n`** | Byte-identical artefacts across platforms | Reader regexes tolerate `\n`, so both pass and the digest lies |
| **Extractor version recorded** | You know which build the goldens describe | `-v` prints the banner and **exits 1** in Xpdf, so `returncode == 0` is a permanently red row nobody reads |
| **Edit ratchet** | Every correction was necessary and applied | A `drop` with no replacement must actually be gone, or the table becomes a place to hide text nobody checked |
| **Contiguity of key sentences** | "must be preferably composted prior to application" is in one block | If you don't pin it, a later reflow can split the sentence your posters quote |

One more, learned expensively: **a refusal whose quote differs only at a line break is a corpus
defect, not a model defect.** Before blaming the agent, print
`" ".join(block.split())` and search for the sentence *as the page prints it*. If it is absent
but the block looks right, look for `letter-` at a line end, and for a footer inside the clause.

### 6.1 Removing text is a positional operation

`text.replace("02", "")` to drop a bare page stamp also mangles `2020` and `2022`. Remove
occurrences **by position** (`re.finditer` + slice), or your test starts asserting against text
the document never had.

---

## 7. Hazards catalogue (portable, each cost someone a day)

1. **A page number in a plan is a claim, not evidence.** Verify anchors; fail rather than write.
   PGS: every hand-written page range was wrong.
2. **Two `pdftotext` builds are two different documents.** Pin per deployment; record which one
   built the corpus.
3. **`-table` is Xpdf-only.** Poppler exits 99. If tables matter (they do), this decides your
   extractor.
4. **A parser that reads a stamp by position is coupled to page layout.** Reading the *last*
   non-blank line to find a page number works raw and fails after de-columning, silently losing
   the page of every section. Search for the stamp anywhere; never at the tail.
5. **Column-major order destroys table rows while preserving every character.** A loss-free
   transform can still make a table unreadable. Exclude table pages explicitly, as measured data.
6. **A mispaired table row produces a confident wrong claim.** Wood's "only if not chemically
   treated" attached to straw. On a poster this is a reprint.
7. **The failure mode of bad extraction is a false negative.** The agent says "the source does not
   mention this" and you believe it.
8. **Glyphs the PDF fails to map to Unicode become U+FFFD** and no encoding recovers them (`0xFF`
   in Latin1, `-` in ASCII7 — measured on an en-dash). Record the count; never hand-edit a
   fixture to hide it — a hand-corrected fixture stops being evidence.
9. **UPPERCASE in the body, title case in the TOC.** A title-case, column-0 regex matches nothing
   in the body and false-positives on a mid-sentence line. Test both shapes.
10. **Numbering collisions are real and must be recorded, not repaired.** One standard's Section A
    collides with itself (item `1.` is two different sections); one appendix holds **two
    independently numbered lists** (`1.`–`6.` twice). Citing `Appendix 1(1.2)` *looks* precise and
    resolves to two different paragraphs. Scope it out, or cite at the level that is unambiguous.
11. **Nested lists share indentation.** Marker numbers alone cannot separate an outer list from a
    nested one that restarts at `1.`. What separated them was a *layout* fact (a page break reset
    the left margin). Calibrate to the document, and assert both "3 is absent" and "4 and 5 are
    present" — otherwise you manufacture items.
12. **Renaming one of two colliding references invents a citation.** Report duplicates, never repair.
13. **`write_text` writes CRLF on Windows.** Use `newline=""`.
14. **A chunk that looks pre-transform may be exactly what the transform produces.** If ingestion
    is idempotent on a hash, a transform fix never reaches the store — re-ingest with `--force`
    deliberately, or you will debug the code while the data is stale.
15. **A string "present" in a JSON payload is not present in the file.** `json.dumps` escapes
    newlines; compare against the source file, then check the payload separately after
    `json.loads`. Two tests, two questions.

---

## 8. The map — what makes grep work at 1.5M tokens

Grep is only fast when the agent knows *what* to grep. Generate three index files, and keep
them regenerable from the corpus (they are derived, never hand-maintained).

### 8.1 `INDEX.md` — one card per source

```markdown
## Knott's Handbook for Vegetable Growers, 5e
`corpus/knott.md` · 546 pages · sha256 2565e28b · 14 sections
**Covers:** soil pH and liming, N/P/K schedules, micronutrient deficiency keys, harvest
intervals, planting densities.
**Coordinate system:** printed page = PDF index − 1 (cover unnumbered).
**Best for:** nutrient rates and deficiency symptom tables.
**Watch:** tables on pp. 120–133 are two-column with conditions offset — read the reviewed
rows in `tables/knott.md`, not the page text.
```

That card is the single highest-leverage artefact in the project. It stops the agent opening a
400-page book to find out whether it is relevant.

### 8.2 `GLOSSARY.md` — synonyms and abbreviations

The mitigation for grep's one real weakness. One section per concept, each listing every form
that appears in the corpus:

```markdown
### Calcium
calcium · Ca · Ca²⁺ · lime · calcitic · blossom end rot · BER · tipburn · bitter pit
### Potassium
potassium · K · K⁺ · potash · muriate of potash · sulphate of potash · K:Mg ratio
### Mycorrhiza
mycorrhiza · mycorrhizae · AMF · arbuscular · VAM · endomycorrhiza
```

Then every search is `rg -i 'blossom end rot|BER|tipburn|bitter pit' sources/` instead of one
literal. Grow it every time a search misses; it is a one-line edit, not a pipeline change.

### 8.3 `notes/<slug>.md` — one note file per source, written as you read

Notes, not summaries, and every claim carries a locator:

```markdown
<!-- source: knott, PDF 187 / printed 186 -->
- Ca is immobile; deficiency shows in new growth first. (p.186)
- BER tied to Ca transport, not soil Ca alone; water stress is a co-factor. (p.186)
- Contradicts [smith2019] on Mg:Ca ratio threshold — see claims.csv #14.
```

### 8.4 `claims.csv` — the real product

The poster is built from claims, so make the claim the unit of record:

```csv
id,claim,source,printed_page,quote,confidence,contradicts
14,"Ca:Mg ratio above 4:1 reduces K uptake",knott,186,"...",high,smith2019
```

Greppable, sortable, and every poster element traces to a page you can check on paper. If a
claim cannot fill the `quote` column with a verbatim substring of `corpus/<slug>.md`, it is not
ready for the poster.

---

## 9. Grep recipes that actually work on a corpus like this

```bash
# Which sources mention a concept at all (cheap, no context burn)
rg -l -i 'blossom end rot|BER|tipburn' corpus/

# A number with its unit, tolerating PDF spacing
rg -n '2[.,]5\s*mmol' corpus/

# Tables you reviewed (rather than page text)
rg -n -i 'deficiency|toxicity' corpus/ --glob '*.md' -C 2

# Everything about one nutrient, with a page marker for citation
rg -n -B4 -i 'magnesium deficiency' corpus/knott.md | rg 'page:|magnesium'

# Which note files already covered this
rg -l -i 'magnesium' notes/

# The claims table, which is what you actually cite from
rg -n -i 'magnesium|mg:ca|k:mg' claims.csv
```

Two habits: always `-n` so you get a line number, and always keep the `<!-- page: -->` marker
within `-B4` so a hit is instantly citable. If you find yourself typing the same four-way
`rg` twenty times, that is the glossary telling you it needs an entry.

---

## 10. If you later decide you need retrieval

Don't. Not yet. But when the corpus grows or a *repeated-question* surface appears (a chatbot
someone else uses, a weekly intake of new papers), escalate in this order and stop as soon as
you can:

1. **`rg` + `INDEX.md` + `GLOSSARY.md`.** Current state. Free.
2. **SQLite FTS5** (BM25, no API key, no vectors). This is the floor: it never depends on a
   network call, and it is one table. PGS's retrieval engine is deliberately FTS-first with
   embeddings as a second arm, for exactly this reason.
3. **Hybrid, fused by rank** — FTS + vectors, combined with Reciprocal Rank Fusion (`k=60`),
   **not** score addition. `ts_rank_cd` is unbounded and a cosine distance is not comparable;
   normalising them is a research project, and rank fusion needs no calibration.
4. Chunk only now, and only at this point: ~800-token targets, section-level, blank-line
   paragraphs first, lines only when a paragraph is itself too big, ~100-token overlap. A
   chunk boundary inside a paragraph is the last resort, because a quote that starts
   mid-sentence is a poor citation.

**Decide empirically, cheaply.** Write down the 20 questions you actually need answered to
draw the posters. Run them with `rg` + the map for one afternoon.

- All 20 found → you saved yourself the RAG.
- A third fail on synonym drift → extend `GLOSSARY.md`. Still not a vector store.
- Failures that survive a good glossary are semantic paraphrases across sources → now
  consider step 2, and only step 2.

---

## 11. What NOT to copy from the PGS build

Nothing here is wrong — it is wrong *for this job*.

| Don't port | Why it exists there | Why not here |
|---|---|---|
| `chunking.py`, `models.py`, migrations | Retrieval plumbing over Postgres | No repeated queries to serve |
| `embedding.py`, `services.py` (RRF/FTS) | A public chatbot with a fixed corpus | Compilation, not Q&A |
| Chunk-level citation audit | Regulatory: a published claim must be verbatim | Use §8.4 `claims.csv` instead — same discipline, no infrastructure |
| Answer cache | Cost + determinism on a public surface | Nothing is being served |
| `sub_ref` character offsets per clause | Citing a clause inside a chunk | Your locator is a printed page |
| The UAT harness | A sign-off surface for a compliance product | Posters get reviewed by looking at them |

**Do port:** `extraction.py` (pinned single extractor), `columns.py` (generic gutter
detection + measured exclusions), `reflow.py` (hyphen repair, furniture stripping),
`corpus.py` (the artefact format + `CorpusEdit` as data), `build_corpus.py` (draft →
review → ratchet), and the verification table in §6.

---

## 12. Open questions for this project

Record the answers here rather than in a chat log:

1. **Which extractor is the contract** for `corpus/` — Xpdf 4 (`-table` available) or poppler?
   Pin it, record the version in every artefact header.
2. **Are the books in print-page or PDF-page coordinates?** A 400-page book with roman front
   matter will have an offset that is *not* constant across the book.
3. **Which sources' tables are load-bearing for the posters?** Those get the `-table` +
   reviewed-rows treatment; the rest can stay page text. Buy the effort where the poster
   payload is.
4. **What is the poster's atomic unit of claim**, so `claims.csv` has a stable schema before
   the first note file is written?
5. **Is any source a scanned image?** If so the pipeline is different (OCR, ground truth,
   no text layer to verify against) and it needs its own decision before ingestion.
