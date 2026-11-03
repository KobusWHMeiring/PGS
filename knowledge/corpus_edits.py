"""The reviewed-edit ledger: every correction to an artefact, and why it was necessary.

Split out of `knowledge/corpus.py` (CONTEXT_CUTS_PRD step 6, second half). The format
module says what the artefact *is*; this says which lines a human had to change to make it
faithful, and carries the evidence that the change was necessary (`original` is on that
page) and applied (`replacement` is in the file). An edit nobody can justify is a failing
test, not a comment -- which is why this is data in a module and not notes in the Markdown.

`knowledge.corpus` re-exports both names, so `from knowledge.corpus import CORPUS_EDITS`
keeps working in `scripts/build_corpus.py` and the corpus tests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorpusEdit:
    """One reviewed correction, and the evidence that it was necessary.

    In:  `page` — the PDF page; `original` — the text the *PDF* produces there (the
         defact being repaired); `replacement` — what the artefact now says;
         `reason` — how the defect arose, in one sentence, so the generator can be
         improved rather than the symptom patched forever.
    Out: data consumed by the traceability test. `original` must be found on `page`, and
         `replacement` must be found in the artefact, which is what stops this table
         becoming a place to hide text nobody checked.
    """

    page: int
    original: str
    replacement: str
    reason: str
    #: `replace` (a correction), `drop` (furniture removed) or `move` (the same text at a
    #: new position). The distinction matters to the coverage test: a move changes no
    #: character, so counting it as a substitution would invent text.
    #:
    #: **`move` cannot be regenerated, and must not be used for one (2026-10-30).**
    #: `scripts/build_corpus.apply_review` is a text *substitution*: it has an `original` and a
    #: `replacement` and no notion of a source and a destination. The BPP's footnote-2 entry was
    #: a `move` for a day and applying it deleted `must be preferably composted` and reprinted
    #: `land available will not be allowed.` at the foot of page 4 — and no test failed, because
    #: the traceability test compares `flat()` strings and `flat` joins lines, so a corruption
    #: that reintroduces the line above reads as a faithful move. Express a move as **a lift and
    #: a place**: a `replace` that removes the text from where the extraction glued it, and a
    #: `replace` anchored on the text it belongs beside (`LANDSCAPE_TABLES_PRD` §12b.2).
    kind: str = "replace"


#: Reviewed corrections, per corpus document. **Every entry is a generator defect that
#: was found by reading the artefact.** Keeping them here rather than as comments in the
#: Markdown is deliberate: a comment cannot fail a test, and this table can.
CORPUS_EDITS: dict[str, tuple[CorpusEdit, ...]] = {
    "saoso": (
        CorpusEdit(
            page=25,
            original="fattening of chickens with more 2 than 25kg weight/m .",
            replacement="fattening of chickens with more than 25kg weight/m².",
            reason=(
                "The `²` of `m²` is drawn as a superscript, so `pdftotext` puts the digit "
                "on its own line *between* `more` and `than` and leaves the base line as "
                "`m .` — the sentence read `…with more / 2 / than 25kg weight/m .` and could "
                "not be quoted. Read from the page image: one sentence, `weight/m²`. The "
                "lone digit is the superscript, not a page stamp, so it is merged rather "
                "than dropped (`BugFixes/saoso_text_glyphs_and_boundaries.md` §2)."
            ),
        ),
        CorpusEdit(
            page=50,
            original="p u r c h a s e d",
            replacement="purchased",
            reason=(
                "A tracked (letterspaced) word in a heading run: the text layer emits one "
                "token per letter, so `purchased` matched nothing in search or retrieval. "
                "Read from the page image, the word is set in tracking, not spelled out "
                "(ibid. §4)."
            ),
        ),
        CorpusEdit(
            page=86,
            original="Other b o v i n e a n i m a l s less t h a n o n e year old",
            replacement="Other bovine animals less than one year old",
            reason=(
                "Two letterspaced runs inside one Appendix 6a row (`bovine animals`, "
                "`than one`). Recorded as one edit because both are on the same printed "
                "line and the same cell; `bovine` has to be findable, since the appendix "
                "is where a farmer looks up a stocking rate (ibid. §4–§5)."
            ),
        ),
    ),
    "bpp": (
        CorpusEdit(
            kind="drop",
            page=3,
            original="02",
            replacement="",
            reason=(
                "The printed page number is furniture. `-raw` puts it on its own line "
                "before the body and `-layout` glues it to the footnote's last line; "
                "either way it is not text."
            ),
        ),
        # Two edits, not one `move` (2026-10-30). A `move` says "the same characters at a new
        # position", and `apply_review` is a single text **substitution** — so the one `move`
        # entry this replaced silently deleted `must be preferably composted` and printed
        # `land available will not be allowed.` a second time, at the foot of page 4. Nothing
        # caught it: the traceability test asserts `flat(original)` on the page and
        # `flat(replacement)` in the artefact, and `flat` joins lines, so a corruption that
        # reintroduces a line from two lines above reads as a faithful move. The review's
        # decision is unchanged — the footnote belongs with the bullet that carries its
        # marker — but it now takes a lift and a place, so regeneration reproduces the
        # reviewed artefact instead of mangling it.
        CorpusEdit(
            page=4,
            original=(
                "must be preferably composted 2 Sustainable means: meeting the needs of "
                "the present without compromising the ability of future generations to "
                "meet their own needs; conserving an ecological balance by avoiding "
                "depletion or destruction of natural resources.(IFOAM: Organics "
                "International 3.0)"
            ),
            replacement="must be preferably composted",
            reason=(
                "`-raw` emits footnote 2 at the end of page 4, which is inside the "
                "manure sentence (`must be preferably composted` / footnote / `prior to "
                "application`), so the BPP's most-quoted sentence was unquotable. This "
                "lifts the footnote out; the next edit puts it back on its bullet."
            ),
        ),
        CorpusEdit(
            page=4,
            original="land available will not be allowed.",
            replacement=(
                "land available will not be allowed.\n"
                "2 Sustainable means: meeting the needs of the present without compromising "
                "the ability of future\n"
                "generations to meet their own needs; conserving an ecological balance by "
                "avoiding depletion or\n"
                "destruction of natural resources.(IFOAM: Organics International 3.0)"
            ),
            reason=(
                "The other half of the pair above: footnote 2 is printed at the foot of "
                "page 4 but belongs to the marker it follows on `a. Sustainable land "
                "management2`. Anchored on the bullet's own sentence, which occurs once "
                "on the page, so the insert cannot land in the manure rule instead."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=8,
            original="ii. Preventativemethods(disruption,",
            replacement="ii. Preventative methods (disruption,",
            reason=(
                "The PDF's text layer has no spaces in this line, so no extractor can "
                "recover them; read from the page, it is two words and a parenthesis."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=8,
            original=(
                "The Principle Of Health. The Principle Of Ecology. The Principle Of "
                "Fairness. The Principle Of Care."
            ),
            replacement="",
            reason=(
                "The brochure prints the four-principle strip on pages 1, 6, 8 and 10. "
                "The first occurrence (page 6) carries the content and sits at a "
                "paragraph boundary; the repeats interrupt numbered lists, so they are "
                "dropped rather than moved."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=10,
            original=(
                "The Principle Of Health. The Principle Of Ecology. The Principle Of "
                "Fairness. The Principle Of Care."
            ),
            replacement="",
            reason="The same repeated strip; see the page-8 entry.",
        ),
        CorpusEdit(
            kind="drop",
            page=5,
            original="\uf06e",
            replacement="",
            reason=(
                "A private-use glyph (U+F06E): the producer's Dingbats bullet before "
                "`Planting:`. Nothing in Unicode names it — pdftotext can emit only the "
                "code the embedded font assigns — so keeping it would put a character in "
                "the corpus that no reader can see, no search can match and no audit can "
                "quote. Only the glyph is dropped: `Planting:` is the list item it marks. "
                "It reached the artefact on 2026-10-27, because before `-enc UTF-8` the "
                "extraction dropped such glyphs silently and the artefact never held one."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=6,
            original="\uf06e",
            replacement="",
            reason="The second private-use bullet, the same shape; see the page-5 entry.",
        ),
    ),
}
