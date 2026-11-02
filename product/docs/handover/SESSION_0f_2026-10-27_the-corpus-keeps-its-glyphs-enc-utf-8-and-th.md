<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0f. 2026-10-27 — the corpus keeps its glyphs: `-enc UTF-8`, and the U+FFFD mystery is closed

**This is the most recent slice.** D69, plus the reader-structure PRD that came out of the same
reading session (last part of this section, and where the next agent starts).
`BugFixes/saoso_text_glyphs_and_boundaries.md` §1 is **closed** — and its diagnosis was wrong, which
is why it stayed open for a week.

- **The `�` was never the PDF.** `knowledge/extraction.py` decoded `pdftotext`'s stdout as UTF-8
  with `errors="replace"`; the `pdftotext` on this machine is **Xpdf 4.00**, whose default output
  encoding is **Latin-1**. Measured on the eight shipped PDFs: **275 of 433 154 bytes are 8-bit and
  none of them is valid UTF-8** — and `pdftotext -enc UTF-8` extracts all eight with **zero**
  U+FFFD. The old claim ("no encoding recovers the real character") came from that Latin-1 path and
  is retracted; the en dash and the `≥` are *different glyphs* (they only collapsed to one byte on
  the lossy path).
- **83 characters in the four ingested documents were affected**, all recovered: `360°`, `100 m²`,
  `45°C`, `rosé`, `Mèthode` (the document's own spelling), `Section B – Appendix 6`,
  `R 250,001 – R 500,000`, `für`. **Plus 66 OPP `●` bullets that had been dropped outright**, so its
  lists were ingested as prose; `●` is now a list marker.
- **Two "measured" constants moved**, and both moves are improvements: the OPP's PDF 4 is now an
  explicit layout exclusion — it was only de-columned *because* §3.2's bullets were missing, and a
  two-band split of its 3-column table orphaned `Members will be invited to take part` from its
  predicate. `test_columns`/`test_reflow`/`test_ingest` are updated with the reason beside them.
- **The BPP artefact was regenerated** and its five reviewed edits re-applied; two private-use
  Dingbats bullets (U+F06E) are now recorded `CORPUS_EDITS` drops, because no extractor can name
  them and no reader can see them. `MAX_EDITS` ratchets 5 → 7.
- **Guards, proven by breaking them:** `test_corpus_glyphs.py` (every committed page and range
  fixture: zero U+FFFD; ten named characters must survive; the manifest must name `-enc UTF-8`),
  `test_passages` (the ingested text, end to end), and `test_extraction` (the command asks for UTF-8;
  a Latin-1 stream raises `ExtractionError` naming the file instead of becoming U+FFFD).
  `testing_hazards.md` **§1.34** records the trap with the byte evidence.
- **Still open in that bug file:** §2 the *Factory farming* superscript still splits its sentence
  (`m .` is missing the `²` — a line-order problem, not this one), and §3 `S1` still ends with the
  next part's half-title. Both are D53 artefact reviews, not view work.

**Local state.** The dev corpus was re-ingested with `--force` and embeddings (319/30/8/9 chunks,
**0 U+FFFD**); that dropped the old `ChatMessage.retrieved_chunks` evidence links, as `--force` does.
Gate **1004 passed / 1 skipped**; **45 commits ahead of `origin/main`**, nothing pushed. The live
site is still `206f35f` and needs the same re-ingest (P7.4) before any of this is visible there —
`uat_seed --check` will keep blocking on the corpus check until it is done.

### Where the next agent starts: judge the UAT (§0g)

**This was the previous handover's "next start" and it is now built.** The four questions in
`ready/READER_STRUCTURE_PRD.md` §10 were answered by the product owner on 2026-10-27, the plan in
`In Progress/READER_STRUCTURE_PLAN.md` was executed the same day, and **the reader is the document's
own structure** (§0g). What is left is the human judgement: `tests/uat/concordance_uat.md` carries
eleven scenarios and **none is signed**. Scenarios 9–11 are the ones this slice added.

The rest of this section is kept because its measurements are still the numbers the UAT is judged
against — run `python scripts/probe_reader_structure.py` and it prints them from the shipped code.

**The measurements are already made, so do not re-litigate them.** `scripts/probe_reader_structure.py`
is committed and read-only: run it and it prints what the PRD claims. Three findings it produced:
**19 of Appendix 2's 30 rows print no condition at all** (that is the reviewer's "list of standalone
inputs" — the paper's silence, rendered as body text); SAOSO has **10 section references and 29
appendix mentions**, of which **9** cannot be decided by number alone; and the corpus also prints
**seven unqualified `Section n`** references (`Section 4.6.2`, `section 5.7`), which resolve only
inside the part they are printed in. `Section A – 2.3` is the trap: it must go to the page's
"printed sections not in the corpus" note and **never** to `S2`.

Nothing in that slice needs a migration or a re-ingest: it is display-only, which is why it can
follow the corpus work so cheaply. See also §0e items 1–5 for the rest of the judgement list —
item 6 closed for the glyph half in §0f.

---
