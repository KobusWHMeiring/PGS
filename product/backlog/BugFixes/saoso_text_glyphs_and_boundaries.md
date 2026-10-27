# Bug: SAOSO's extracted text loses glyphs, and one page boundary swallows a part title

**Status:** Open — found 2026-10-27 while reading the definitions branch after the concordance and
passage-layout work (SPEC §18.3 **D68**; `PASSAGE_LAYOUT_PLAN.md` §7.9).
**Severity:** A reader checking a quotation sees `360\ufffd` where the paper prints `360°`; a
superscript `2` splits the *Factory farming* sentence with a stray line; the last chunk of `S1`
carries the *next* part's half-title, so the definitions end with a second `SECTION B` heading.
**Owner:** Corpus (D53 artefact review) · Build (the guard)
**Affected:** `DocumentChunk.text` for SAOSO v2.1 (30 of 366 chunks carry U+FFFD); the
section boundary between `S1` and `S2`; every surface that reproduces the text — the reader, the
search snippets, the chatbot's quotes.
**Reference:** `CORPUS_CANONICAL_FORMAT_PRD.md` (D53, `CORPUS_EDITS`) ·
`knowledge/sections/toc.py` / `saoso.py` (section attribution) ·
`product/backlog/In Progress/PASSAGE_LAYOUT_PRD.md` §3 (display-only rule) ·
`scripts/build_corpus.py` (the artefact generator)

---

## 1. Lost glyphs (U+FFFD)

**Measured 2026-10-27 on the shipped corpus: 30 of 366 chunks contain U+FFFD.** The PDF's text layer
does not map several glyphs, and `pdftotext` emits the replacement character. Examples:

| Chunk | Stored text | What the paper prints |
|---|---|---|
| `S1` | `moving freely around 360\ufffd, or kept in` | `360°` |
| `S1` | `more` / `2` / `than 25kg weight/m .` | `more than 25 kg weight/m².` (the superscript is a separate line) |
| `S5.1.7` | `100 m\ufffd of the house/building` | `100 m²` |
| `S5.2.1` | `dairy \ufffd 90 days; eggs … \ufffd 42 days` | `dairy ≥ 90 days` (an inequality sign) |
| `S7.5.3`, `S21.5` | `45\ufffdC`, `70 \ufffdC` | `45 °C`, `70 °C` |
| `S22.1.10` | `\ufffd PGS certified` | a bullet or `©`-style mark |
| `Appendix 4. Table 1` | `\ufffd organic flavouring extracts` | a bullet |
| `Appendix 6b` | `1 m\ufffd/100`, `Outdoor \ufffd runs` | `m²`, a bullet |
| `OPP` fee table | `R 250,001 \ufffd R 500,000` | `–` (an en dash) |
| `landscape` | `GIZ` credit: `Gesellschaft f\ufffdr …` | `für` (a `ü`) |

The same codepoint covers at least six different characters, so **a mapping cannot be guessed**.
D53 says the text of record is a reviewed artefact: the fix is a reviewed `CORPUS_EDITS` entry per
occurrence (or a reviewed per-glyph mapping after a human reads the page image), then
`ingest_standard --force`.

A display fix is forbidden: substituting `°` or `²` in the reader would put a character in the
document that the corpus does not hold, and the chatbot's citation audit checks quotes against the
stored text — the reader and the audit would then disagree about what the document says.

## 2. A superscript splits a sentence

The *Factory farming* definition stores:

```
… fattening of chickens with more

                                        2

than 25kg weight/m .
```

The `2` is the superscript of `m²` on its own extracted line. The reader renders it as its own
paragraph, so the sentence reads "…with more / 2 / than 25 kg weight/m ." — visibly broken. This is
the same glyph problem as §1 plus a line-order one; a corpus edit merges it to `m²`.

Measured: 5 of 366 chunks contain a lone-digit line, but four are table cells in Appendix 6a/6b
(where a lone number is correct). `S1` is the only sentence-splitting case today.

## 3. `S1` swallows the next part's half-title

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

## 4. Why this is a separate follow-up, not part of the layout slice

The passage-layout PRD is explicit: the stored text is untouched, the words are verbatim, and an
unrecognised shape is a paragraph. Correcting glyphs and section boundaries changes `DocumentChunk`
rows, needs `--force` (which drops `ChatMessage.retrieved_chunks` evidence links), and requires a
human looking at the page image. That is the SAOSO artefact conversion (D53 / P5), not a view change.

## 5. Definition of done

- [ ] A reviewed SAOSO artefact (`knowledge/corpus/saoso.md`) whose `CORPUS_EDITS` carry the glyph
      corrections, with each edit proved necessary and applied (`test_corpus_format.py`'s idiom).
- [ ] The half-title page is a boundary, not the tail of `S1`; the `S1` branch ends at *Wild
      Harvesting*, and `SECTION B` is not reproduced inside it.
- [ ] Re-ingest with `--force`; the corpus check reports the document as rebuilt from the artefact.
- [ ] A guard asserting **zero U+FFFD in the ingested corpus** (or an explicit allow-list with a
      reason per entry), so a future extraction cannot reintroduce the loss silently.
- [ ] The reader shows `360°`, `m²`, `45 °C` and `R 250,001 – R 500,000`; the chatbot can quote
      those sentences verbatim and the audit accepts them.
