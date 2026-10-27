# Bug: SAOSO's text — a lost superscript and a swallowed part title (the glyphs are closed)

**Status:** **§1 closed 2026-10-27** — the glyph loss was an encoding bug in the extraction, not a
lossy PDF, and all 83 replacement characters in the ingested corpus are real characters again.
**§2 and §3 open** — a superscript still splits one sentence, and `S1` still ends with the next
part's half-title; both are line-order and section-attribution problems, and neither is a view
concern.
**Severity:** was — a reader checking a quotation saw `360�` where the paper prints `360°`, and
`ros�` for `rosé` on a public page.
**Owner:** Corpus (D53 artefact review) · Build (the guards)
**Affected:** `DocumentChunk.text` for every ingested document; the reader, the search snippets and
the chatbot's quotes.
**Reference:** `testing_hazards.md` §1.34 (the trap, with the byte evidence) ·
`knowledge/extraction.py` (`-enc UTF-8`, strict decode) ·
`knowledge/tests/test_corpus_glyphs.py` (the guards) ·
`product/backlog/In Progress/PASSAGE_LAYOUT_PRD.md` §3 (display-only rule) ·
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

## 3. `S1` swallows the next part's half-title — **open**

The last `S1` chunk (page 22, 422 characters) ends with:

```
Wild Harvesting / Wild Harvested / Wild Crafted
Collecting products according to the requirements of these standards …

                     SECTION B

   DEFINITIONS, GENERAL PRINCIPLES, RECOMMENDATIONS AND STANDARDS
```

That half-title is the **start of printed p.30**, which the parser attributes to the preceding
section because the section heading it keys on (`2. ORGANIC ECOSYSTEMS`) comes *after* it. The
reader therefore ends the definitions branch with a second `SECTION B` heading and its subtitle.

This is attribution, not text loss: the strings are real. The fix belongs in the section parser or
in the reviewed artefact's block structure (D53), so a part title becomes a boundary marker rather
than a paragraph of the section before it. It is not a reader concern — suppressing it in the view
would hide text the corpus truly holds.

## 4. Why §2 and §3 are a separate follow-up

The passage-layout PRD is explicit: the stored text is untouched, the words are verbatim, and an
unrecognised shape is a paragraph. Correcting the superscript and the section boundary changes
`DocumentChunk` rows, needs `--force` (which drops `ChatMessage.retrieved_chunks` evidence links),
and requires a human looking at the page image. That is the SAOSO artefact conversion (D53 / P5),
not a view change. §1 was different: it needed no review, because the character was already in the
extraction — only the decode was throwing it away.

## 5. Definition of done

- [x] The corpus holds the characters the paper prints: **zero U+FFFD** in all four ingested
      documents, measured after re-ingest (2026-10-27).
- [x] `-enc UTF-8` in every extraction mode, a strict decode, and the fixtures regenerated from the
      shipped PDFs with the extractor banner and command recorded.
- [x] A guard asserting zero U+FFFD over the committed pages, the range fixtures and the ingested
      text, so a future extraction cannot reintroduce the loss silently.
- [x] The reader shows `360°`, `m²`, `45°C`, `rosé`, `Mèthode`, `Section B – Appendix 6` and
      `R 250,001 – R 500,000`; the chatbot can quote those sentences verbatim.
- [ ] A reviewed `CORPUS_EDITS` entry merges the *Factory farming* superscript (§2).
- [ ] The half-title page is a boundary, not the tail of `S1`; the `S1` branch ends at *Wild
      Harvesting*, and `SECTION B` is not reproduced inside it (§3).
- [ ] Re-ingest with `--force` after those reviews; the corpus check reports the document as
      rebuilt from the artefact.
