# Bug: SAOSO's text — a lost superscript, a swallowed part title, letterspaced words and two tables that lost their rows

**Status:** **§1 closed 2026-10-27** — the glyph loss was an encoding bug in the extraction, not a
lossy PDF, and all 83 replacement characters in the ingested corpus are real characters again.
**§2–§5 closed 2026-10-28** — fixed by the SAOSO artefact (`knowledge/corpus/saoso.md`, plan P6),
not by display rules. §2 and §4 are three reviewed `CORPUS_EDITS`; §3 is a measured parser rule
(the part banner is the page's running head); §5a is twenty reviewed rows in `TABLE_ROWS`.
**§5b (Appendix 6b) stays open** — its table is three pages of multi-column measures and a “row”
has to be decided before it can be curated; see §5 and §8.
**Severity:** was — a reader checking a quotation saw `360�` where the paper prints `360°`, and
`ros�` for `rosé` on a public page. §4 and §5 were severity *readability*: a definition read
"…with more / 2 / than 25kg weight/m .", and Appendix 6a's twenty animal classes were followed by
twenty numbers with nothing tying them together.
**UAT:** Appendix 6a's new shape is **Scenario 13, SIGNED PASS 2026-10-28** by Kobus (Product) in
`tests/uat/concordance_uat.md` (13/13, against `e6f4464`).
**Owner:** Corpus (D53 artefact review) · Build (the guards)
**Affected:** `DocumentChunk.text` for every ingested document; the reader, the search snippets and
the chatbot's quotes.
**Opened:** 2026-10-27 · **Last measured:** 2026-10-28, on the corpus rebuilt from the artefact
(SAOSO **338 chunks**, all embedded; the four documents **385**)
**Reference:** `testing_hazards.md` §1.34 (the trap, with the byte evidence) ·
`knowledge/extraction.py` (`-enc UTF-8`, strict decode) ·
`knowledge/tests/test_corpus_glyphs.py` (the guards) ·
`product/backlog/In Progress/PASSAGE_LAYOUT_PRD.md` §3 (display-only rule) ·
`knowledge/tables.py` (the mechanism §5 needs) ·
`scripts/extract_fixtures.py` (the artefact generator)

---

## 1. Lost glyphs (U+FFFD) — **closed 2026-10-27**

**The earlier diagnosis on this page was wrong**, and the error is worth keeping in view: it said
the loss was "in the SOURCE documents, not in the extraction", that "no encoding recovers the real
character", and that "the same codepoint covers at least six different characters". All three were
artefacts of the *decode*, not of the PDFs.

`knowledge/extraction.py` decoded `pdftotext`'s stdout as UTF-8 with `errors="replace"`. Xpdf 4.00
— the build on the machine whose fixtures and corpus this project measures — writes **Latin-1**
unless it is asked for UTF-8. Every 8-bit byte it emitted therefore arrived as U+FFFD, and
`errors="replace"` made sure nothing complained.

Measured on the eight shipped PDFs (2026-10-27):

| | |
|---|---|
| bytes extracted | 433 154 |
| non-ASCII bytes | **275** |
| of those, valid UTF-8 | **0** |
| U+FFFD in the four ingested documents | **83** (SAOSO 37, landscape 31, OPP 10, BPP 5) |
| U+FFFD with `pdftotext -enc UTF-8` | **0, in all eight documents** |

What the corpus now says instead:

| Was | Now | Where |
|---|---|---|
| `moving freely around 360�` | `360°` | `S1` |
| `100 m� of the house/building` | `100 m²` | `S5.1.7`, `Appendix 6b` |
| `not exceed 45�C` | `45°C` | `S7.5.3` |
| `For white and ros� wines` | `rosé` | `Appendix 7` |
| `Quality wines (M�thode` | `Mèthode` — **the document's own spelling** | `Appendix 7` |
| `Section B � Appendix 6` | `Section B – Appendix 6` | `Appendix 2` |
| `R 250,001 � R 500,000` | `R 250,001 – R 500,000` | OPP fee table |
| `Gesellschaft f�r` | `für` | landscape |
| *(dropped entirely)* | 66 × `●` — the OPP's list bullets | OPP |
| *(dropped entirely)* | 101 × `©`, 37 × `•`, 32 × `–`, 4 × `‘’“”` families | all |

Two things this taught us that a per-character mapping table would not have:

1. **The en dash and the `≥` are different glyphs.** On the lossy path both arrived as the single
   byte `0xAD`, which is why the old note concluded one codepoint covered six characters. Xpdf
   resolves them separately: `32 × –` (cross-references, conversion periods) and `3 × ≥` (the GE
   isolation distances: `soybeans ≥ 10 m`). Nothing had to be guessed.
2. **Some glyphs were being dropped, not replaced.** In the OPP, Xpdf's Latin-1 output had no byte
   for `●` at all, so the bullet vanished and 66 list items were ingested as prose. That is a
   second, quieter class of loss that no U+FFFD count would ever have shown.

**Fixed by:** `-enc UTF-8` in all three extraction modes, a strict decode that raises
`ExtractionError` naming the file, regenerated fixtures (`scripts/extract_fixtures.py --force`),
the BPP artefact regenerated with its reviewed edits re-applied, and re-ingestion with `--force`.
Guards: `knowledge/tests/test_corpus_glyphs.py` (no committed page and no range fixture may hold
U+FFFD, and ten named characters must survive) and `test_passages` (the ingested text, end to end).

**One character is still not recoverable, and it is not a loss:** the BPP prints a Dingbats bullet
before `Planting:` and `Seed/seedling Management:` that the font maps to the private-use code
U+F06E. No Unicode value names it, so it is a recorded `drop` in `CORPUS_EDITS` — keeping it would
put a character in the corpus that no reader can see and no audit can quote.

## 2. A superscript splits a sentence — **open**

The *Factory farming* definition stores:

```
… fattening of chickens with more

                                        2

than 25kg weight/m .
```

The `2` is the superscript of `m²` on its own extracted line, and `m .` is missing the `²`
entirely: this is a *line-order* problem, not the encoding one (§1 fixed `100 m²` in `S5.1.7`,
where the superscript is drawn inline). The reader renders the `2` as its own paragraph, so the
sentence reads "…with more / 2 / than 25kg weight/m ." — visibly broken.

Measured: 5 of 366 chunks contain a lone-digit line, but four are table cells in Appendix 6a/6b
(where a lone number is correct). `S1` is the only sentence-splitting case today. The fix is a
corpus edit that merges the superscript into `m²` (D53), with the page image read to confirm.

## 3. A part banner is ingested into the end of a section — **open** (re-measured 2026-10-28)

**This section previously said "`S1` swallows the next part's half-title". That was the visible case,
not the defect.** Measured 2026-10-28: the block is printed **twelve** times — at the tail of one chunk
in *every* section of Part B — and the reader therefore ends twelve branches with a second part title.
The product owner found it on 2026-10-28 reading the definitions page ("…appearing at the end of every
page").

| chunk | printed p. | chunk | printed p. |
|---|---:|---|---:|
| `S1` | 22 | `S7.5.3` | 55 |
| `S2.4.5` | 32 | `S8.2` | 56 |
| `S3.2.1` | 33 | `S9.7.5` | 59 |
| `S4.8.6` | 40 | `S20.6.3` | 63 |
| `S5.7.9` | 51 | `S21.6` | 64 |
| `S6.1` | 52 | `S22.1.11` | 66 |

```
… with the EU 2018-848 in order to derive guidance for those

                                              certifiers using this standard.

                                                               SECTION B

                      DEFINITIONS, GENERAL PRINCIPLES, RECOMMENDATIONS AND STANDARDS
```

Not one of these is a section's last sentence: the `SECTION B` block is the **page-run banner** that
SAOSO prints above Part B's contents, and the parser attributes it to whichever section was open when
the page arrived. Twelve chunks, twelve branches, one cause.

**Consequence:** the definitions branch ends with `SECTION B` and its subtitle as if they were the last
thing the standard says about definitions; `S6`, `S7`, `S8`, `S9`, `S20`, `S21` and `S22` end the same
way. A reader scrolling to the end of any of them is told a new part starts, and then nothing follows.

**Fix:** the banner is a **structural marker**, not prose: a part title closes the section above it and
opens nothing. That is a parser/artefact decision (D53) — in the reviewed artefact the banner becomes a
boundary line (the corpus format already has headings and page markers), and the parser must not
append a heading that precedes a section's own heading into the previous section's text. Suppressing
it in the view would hide text the corpus truly holds, so the reader is not the place.

**Guard:** after the artefact lands, a corpus test asserts that **no chunk in any document contains
`SECTION <LETTER>` followed by a title line** — the measurement above, as one regex over the
ingested text.

## 4. Three lines were extracted letter by letter — **open**

A tracked (letterspaced) line in the PDF comes out of `pdftotext` with a space between every letter,
so a word stops being a word. Measured over the ingested SAOSO: **3 runs**, all short:

| Where | Page | Stored text | Printed |
|---|---:|---|---|
| `S5.5.7` | 49 | `p u r c h a s e d` | *purchased*, set in tracking in a heading run |
| `Appendix 6a` | 85 | `b o v i n e a n i m a l s` | *bovine animals* |
| `Appendix 6a` | 85 | `t h a n o n e` | *than one* (in "less than one year old") |

**Consequence:** search and retrieval cannot match them — `bovine` finds nothing in Appendix 6a,
and a reader searching *purchased* misses `S5.5.7`. The reader prints the letters as they are, which
is correct: the words are the document's and the citation audit compares quotes against this text,
so substituting a character in the view is not an option.

**Fix:** a reviewed `CORPUS_EDITS` entry in the SAOSO artefact (D53) — the same mechanism that
repaired the BPP's five corrections, and the same "necessary and applied" idiom: each edit names the
stored text, the printed text, and the page image that settles it. Cheap (three lines), and it
should ride along with §2 and §3's review.

**Guard:** after the artefact lands, `knowledge/tests/test_corpus_glyphs.py`'s family of character
assertions is the wrong shape for this; the right one is a corpus-level test that no chunk contains a
run of three or more single-letter tokens (`(?<!\w)\w( \w){3,}`), which is what this measurement
was. One line, and it also catches the next letterspaced line a reprint introduces.

## 5. Appendices 6a and 6b lost the rows of their tables — **open**

This is the **Appendix 2 defect**, still live for the two appendices nobody curated. The paper prints
them as two-column tables (`Class or species` beside `Number per ha`); `pdftotext -layout` keeps the
two columns' lines out of step, so the values separate from their labels. `knowledge/tables.py`'s
module docstring describes the failure and the measurement that fixed Appendix 2; these are the same
pages' neighbours, untouched because `TABLE_ROWS` has one key.

Appendix 6a, printed p.85, one chunk of 757 characters — **20 classes, 20 values, 5 values still
attached, 15 piled at the end, and the next part's half-title on the tail**:

```
… Equines over six months old 5
   Calves for fattening
   Other b o v i n e   a n i m a l s less t h a n o n e year old 3,3
   Male bovine animals from one to less than two years old 3,3
   Female bovine animals from one to less than two years old 2
   Male bovine animals two years old or over 2,5
   Breeding heifers  Heifers for fattening  Dairy cows  Cull dairy cows  Other cows
   Female breeding rabbits  Ewes  Goats  Piglets  Breeding sows  Pigs for fattening
   Other pigs  Table chickens  Laying hens
  2 5 2,5 2 2 2,5 100 13,3 13,3 74 6,5 14 14 580 230
  SECTION B  SOUTH AFRICAN specific
```

Appendix 6b (p.86) has the same shape in its rabbit table, and it also carries the half-title
defect of §3 — a trailing `MINIMUM INDOOR AND OUTDOOR SPACE REQUIREMENTS FOR RABBITS` block.

**Consequence:** a reader cannot answer "how many laying hens per hectare?" from this branch. The
numbers are present, the classes are present, and no pairing survives. A citation of any cell is
unquotable as a table row, exactly as Appendix 2's were before 2026-10-21 — which is also how a
grounded answer once attached `Free of significant contaminants` to the wrong substance.

**Fix:** two new keys in `TABLE_ROWS`/`TABLE_SECTIONS` (`"Appendix 6a"`, `"Appendix 6b"`) with
reviewed cells, in printed order, using the mechanism Appendix 2 already has: 20 rows for 6a, and
6b's rows per species. Nothing in the reader changes — `structure_for()` picks up a new key and the
page renders the same definition-list shape. The `TABLE_BANDS` measurement will need 6a's and 6b's
column offsets added.

**Prerequisite, and the reason it is not done in the view:** the cells must be read off the page by
a human (or drafted by a vision model and **reviewed**, D70.2). A parser that guessed the pairing
would be inventing the document's meaning — the same mistake the Table 1 "four-column rows already
coherent" exclusion was there to avoid.

This is also what **G4** means ("Appendices 3, 4, 6a/6b and 7"), so the work is already scheduled
by `CORPUS_CANONICAL_FORMAT_PLAN`'s artefact conversion rather than invented here.

## 6. Why §2–§5 are a separate follow-up

The passage-layout PRD is explicit: the stored text is untouched, the words are verbatim, and an
unrecognised shape is a paragraph. Correcting the superscript, the section boundary, the
letterspaced lines and the two tables changes `DocumentChunk` rows, needs `--force` (which drops
`ChatMessage.retrieved_chunks` evidence links), and requires a human looking at the page image. That
is the SAOSO artefact conversion (D53 / P5), not a view change. §1 was different: it needed no
review, because the character was already in the extraction — only the decode was throwing it away.

**The evidence-link cost is now recoverable (2026-10-28).** `manage.py relink_evidence --apply`
rebuilds `ChatMessage.retrieved_chunks` from the P2.5a `grounding` snapshot for every passage whose
text the rebuild did not change, and reports the rest as *same locator, different text* rather than
re-pointing them at words no answer ever quoted. Run it after each `--force`. Measured on the dev
instance before any of §2–§5: 54 passages restorable, 16 already linked, 10 not (they were answered
before the 2026-10-27 rebuild, whose reflow changed their text). So the review below is no longer
blocked by the cost of destroying evidence it is about to rewrite anyway.

## 7. Definition of done

- [x] The corpus holds the characters the paper prints: **zero U+FFFD** in all four ingested
      documents, measured after re-ingest (2026-10-27).
- [x] `-enc UTF-8` in every extraction mode, a strict decode, and the fixtures regenerated from the
      shipped PDFs with the extractor banner and command recorded.
- [x] A guard asserting zero U+FFFD over the committed pages, the range fixtures and the ingested
      text, so a future extraction cannot reintroduce the loss silently.
- [x] The reader shows `360°`, `m²`, `45°C`, `rosé`, `Mèthode`, `Section B – Appendix 6` and
      `R 250,001 – R 500,000`; the chatbot can quote those sentences verbatim.
- [x] A reviewed `CORPUS_EDITS` entry merges the *Factory farming* superscript (§2).
- [x] The part banner is a boundary, not the tail of twelve branches; no chunk in the ingested
      corpus contains `SECTION <LETTER>` followed by the part title (§3).
- [x] One `CORPUS_EDITS` entry per letterspaced *line* (three runs, two lines, one edit each), and a
      corpus-level guard refuses a run of three or more single-letter tokens (§4).
- [x] `TABLE_ROWS` gains `Appendix 6a` — **20 reviewed rows**, each class paired with its stocking
      rate, with `TABLE_BANDS[85]` for the guard — so the appendix renders as a table and its cells
      are quotable (§5a).
- [ ] `Appendix 6b`: three pages of multi-column measures; needs a decision on what a row is (§8).
- [x] Re-ingest with `--force` from the reviewed artefact; the corpus reports `source=corpus`
      (`document #28`, 338 chunks, all embedded), and the evidence links were relinked (§6).

## 8. Resolution (2026-10-28) — the SAOSO artefact, and what it cost

The four defects were fixed by **converting SAOSO to a reviewed artefact** (plan
`CORPUS_CANONICAL_FORMAT_PLAN.md` P6): `scripts/build_corpus.py --doc saoso` drafts
`knowledge/corpus/saoso.md` from the PDF, the review is a diff, and `ingest_standard --from-corpus`
reads the artefact instead of re-deriving layout on every ingest.

**The fixed outcome, measured on the ingested corpus (338 chunks, all embedded):**

| | before | after |
|---|---|---|
| chunks holding a part banner (`SECTION B` + title) | 12 | **0** |
| chunks holding a letterspaced run (3+ single-letter tokens) | 2 | **0** |
| chunks whose last paragraph is a dangling continuation | 13 | **1** (`S4.8.6`, the centred note) |
| Appendix 6a | 20 classes, 5 values attached, 15 piled at the foot | **20 rows**, `Laying hens → 230` |
| chunks | 319 (PDF path) | 338 (19 more: 6a's reviewed rows replace 1 auto chunk) |

**What the draft exposed that the bug had not** — each fixed where it belonged, not in the reader:

1. **The artefact generator sliced every page, not the parser's body stream.** The draft's `S1`
   carried pages the parser drops, and `Appendix 7` reproduced Section C three times, because a
   section's body ran to the next heading *anywhere in the PDF*. `SaosoParser.body_lines()` is now
   the one definition of the document's body, and the generator slices it (`scripts/build_corpus.py`).
2. **`-raw` is unusable for this document.** SAOSO is one double-spaced column, so Xpdf's
   content-stream order is word-for-word identical but line-broken so no heading can be found: the
   generator parsed **zero sections**. `RAW_FALLBACK_OFF = {“saoso”}` makes that a measured default.
3. **A `ref:` annotation forced the heading to carry a `#` marker into the text.** Every clause then
   rendered at heading weight *and* its wrapped continuation split off again — the defect
   `reader_clause_line_breaks.md` had just fixed from the other side. An annotated heading is now
   stored as text (its marker dropped); BPP's headings, which have no refs, keep theirs.
4. **`heading_path` disagreed between the two paths.** The parser named a section's *parent*, the
   artefact its own heading. The parser now includes the section itself, which is the corpus
   format's stated rule and the only form useful alone.
5. **A clause heading's slug overran `anchor` (128 chars)** and the first ingest died with
   `value too long for character varying(128)`. Truncated at a word boundary — it only ever shortens
   a fallback locator.
6. **The two-column `-table` extraction was needed, not a guess.** Appendix 6a's twenty pairings come
   from `pdftotext -table` (the mode the repo measured for Appendix 2) and agree row for row with the
   EU regulation the appendix cites; `test_tables.py` pins each class to the value on its own printed
   line.

**The evidence cost, and the fix that made it visible.** `--force` drops
`ChatMessage.retrieved_chunks`, so the rebuild was preceded by `manage.py relink_evidence`
(commit `a67ee5d`). Two things surfaced:

* the first artefact rebuild reported **70 of 80** snapshot passages as *text changed* for
  presentation reasons only — the artefact states a heading as `## 4.1.` where the PDF path stated
  `4.1.`, and collapses blank-line runs. `text_sha` now hashes a passage's **words** (heading marker
  stripped, whitespace collapsed), the same normalisation the citation audit uses;
* snapshots written *before* that change carry the old digest, so 40 of them were re-keyed from the
  PDF path (which is still derivable) and then relinked. **57 links restored**; 30 left unlinked
  because a *previous* rebuild (2026-10-27) had genuinely rewritten those passages. The snapshot is
  still the record for them.

**Guards** — `knowledge/tests/test_corpus_saoso.py` (20 tests: header/sha, monotonic pages, identity,
body text equality with the PDF path, character multiset, per-block traceability, each edit necessary
and applied, edit ratchet, and the five defects above), plus
`knowledge/tests/test_section_parsers.py` (the body stream, the banner at a page top, a banner printed
mid-page, a page opening with a label), `knowledge/tests/test_corpus_format.py` (`ref:` before a
heading with no body, a `ref:` mid-body, two refs in a row, the anchor limit, an unannotated heading
keeping its marker) and `knowledge/tests/test_tables.py` (6a's twenty pairings).

**§5b, Appendix 6b, is deliberately not done.** It is three printed pages (86–88) of a multi-column
table — species × live weight × indoor/outdoor area, then poultry, poultry barns and rabbits — and
`TableRow` models *one* substance and *one* condition cell. Curating it means deciding whether a row
is a species (measures joined across three columns, with labels the paper prints only in the header)
or a printed line (which splits a species across four rows). That is a product decision about what a
reader can quote, so it is left open rather than invented here: the artefact holds the page text, and
the appendix renders as prose exactly as it did before.
