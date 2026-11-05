"""What a reviewed artefact keeps: the corrections, and the refusal to lose a review.

Split out of `scripts/build_corpus.py` when that file crossed the 30 KB cap (`build_principles.md`
§II), and the split is by responsibility rather than by size: `build_corpus.py` decides **what the
draft says**, this module decides **what the review has already decided** — the reviewed corrections
applied to a fresh draft, and the guard that refuses to write a draft which would drop a reviewed
table block.

Both exist because a reprint regenerates the artefact: a correction that lives only in the working
tree is lost the first time somebody runs `--force`, and a table block nobody re-typed is lost the
same way, silently, with every character-level guard still green (`testing_hazards.md` §3.25).
"""

from __future__ import annotations

import re

from knowledge.corpus import flat


def apply_review(text: str, edits) -> str:
    """Apply the reviewed corrections (`CORPUS_EDITS`) to a freshly generated artefact.

    In: the draft text and the document's reviewed edits. Out: the text with each edit's
    `replacement` in place of its `original`.
    Fails: `SystemExit` when an edit matches nothing or matches more than once — a review
    that no longer applies is a review of a different document, and regenerating on a reprint
    must fail loudly rather than quietly drop a correction a person made.

    Why here and not as a hand edit: a reprint regenerates this file, and a correction that
    only lives in the working tree is lost the first time somebody runs `--force`. The edits
    are data (`knowledge/corpus.py`), the generator applies them, and
    `knowledge/tests/test_corpus_saoso.py` still proves each one was necessary and applied.

    The match is **whitespace-tolerant**, because a correction can join lines: the `m²`
    superscript sits on its own line, so the edit names the sentence by its words.

    The **replacement keeps its own line breaks** (2026-10-30). It used to be `flat()`tened, which
    is fine for a one-line correction and wrong for the only kind that needs two edits: a footnote
    that has to sit three printed lines below the point where the extraction glued it. Collapsed
    onto one line it is the same words in a different paragraph, and `flat()` comparison in
    `test_corpus_bpp` cannot tell the difference — which is how a corrupting `move` shipped.

    **The multiplicity guard was dead** (fixed 2026-10-30). It read `subn(..., count=1)` and
    checked the substituted count, which is 1 whenever the pattern matches at all — so an edit
    whose anchor occurred twice applied silently to the first. The count is now taken before the
    substitution, which is the only place it can be taken.
    """
    for edit in edits:
        if not edit.replacement:
            continue
        pattern = re.compile(
            r"\s+".join(re.escape(word) for word in flat(edit.original).split())
        )
        found = len(pattern.findall(text))
        if found != edit.occurrences:
            raise SystemExit(
                f"the reviewed edit for PDF page {edit.page} matched {found} times in the "
                f"draft, and it declares {edit.occurrences}: {edit.original[:60]!r}. A reprint has "
                "moved the text — re-review it rather than deleting the edit."
            )
        text = pattern.sub(edit.replacement, text, count=edit.occurrences)
    return text


def table_block_counts(text: str) -> dict[str, int]:
    """How many of each table-format marker a text carries.

    The five are the whole vocabulary of corpus format rule 5, so a block that is lost loses a
    count here as well as every boundary it held. `-- /table` is deliberately not counted: it
    pairs with `<!-- table`, and a doubled count would hide a lost block behind a gained closer.
    """
    return {
        "table": text.count("<!-- table"),
        "row": text.count("<!-- row:"),
        "cell": text.count("<!-- cell"),
        "divider": text.count("<!-- row-divider:"),
    }


def table_loss_refusal(existing: str, generated: str) -> str | None:
    """In: the artefact on disk and the draft about to replace it. Out: a refusal, or None.

    Returns a message when the draft would leave fewer table markers of any kind than the artefact
    already carries. The draft having *more* is not a loss: that is the day the generator learns to
    emit the block (D80's S3), and it must not be blocked by the guard that protects today's
    reviews.

    Out is a string rather than an exception so the decision is testable without a PDF or an
    extractor — the same seam `body_filter()` exists for (`testing_hazards.md` §2.9).
    """
    before = table_block_counts(existing)
    after = table_block_counts(generated)
    lost = {name: (before[name], after[name]) for name in before if after[name] < before[name]}
    if not lost:
        return None
    loss = ", ".join(f"{count} {name} marker(s) → {kept}" for name, (count, kept) in lost.items())
    return (
        f"the artefact on disk carries {before['table']} table block(s) and the draft carries "
        f"{after['table']} ({loss}). build_corpus.py has no rule that emits a `<!-- table -->` "
        "block, so writing this draft would replace a human's transcription with the PDF's "
        "column soup — and every guard that compares characters would still pass "
        "(testing_hazards.md §3.25). Nothing was written. Draft elsewhere with `--stdout`, or "
        "pass `--discard-tables` to accept the loss and expect to retype the review."
    )


