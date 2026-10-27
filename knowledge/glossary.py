"""The document's glossary: which words it defines, and where each definition is.

`S1` renders as a glossary (`knowledge/passages.py` rule 5 finds the terms from the shape of the
lines) and none of those words linked anywhere. This module answers two questions and no more —
*which words are defined* and *what id the definition carries* — and leaves the matching to
`knowledge.references`, so there is one scan over a paragraph, not two.

**Why the list is derived rather than typed in (D70.7).** The first reading of the measurement
(`READER_STRUCTURE_PRD` §1.4, since corrected) concluded the heuristic's list was mostly prose, and
planned a reviewed list of 25–45 hand-typed strings. Measured properly: `S1` holds 78 `Term` blocks
and **71 distinct headwords**, and they are the glossary — `Soil`, `Breeding` and `Synthetic` are
defined terms; the seven repeats are the chunk overlap the reader already trims. So the human
judgement is recorded the other way round, as **removals**:

* `GLOSSARY_BRANCH` names the branch per document — "which section defines this document's words" is
  a fact about the document, and no heuristic should guess it;
* `REJECTED` lists headwords to drop, and each entry must still exist as a `Term` there, so a
  rejection that no longer matches anything fails loudly instead of rotting (`CORPUS_EDITS`'s
  *necessary and applied* idiom).

Deriving also means a reprint cannot leave the list stale, and the ids cannot collide: the entries
come from the same rendered, overlap-trimmed blocks the page shows.

No Django import, no `core` import (`build_principles.md` §I).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from knowledge.passages import Block, Term

#: Which branch is the glossary, per document. Reviewed data, keyed by `StandardDocument.source_file`
#: the same way `concordance.REVIEWED_BRANCH_TITLES` is.
GLOSSARY_BRANCH: dict[str, str] = {
    "pgs_docs/saoso-version-2.1-2026.pdf": "S1",
}

#: Headwords the layout finds in the glossary branch that are **not** defined terms. Empty today, and
#: that is a measured result rather than an oversight: all 71 distinct headwords are entries in the
#: document's own glossary. Each entry must still exist as a `Term` (`_reviewed`).
REJECTED: dict[str, tuple[str, ...]] = {
    "pgs_docs/saoso-version-2.1-2026.pdf": (),
}

#: The id prefix a definition carries (`term-acb`). A display anchor, never a citation anchor: only
#: the corpus may be cited, and `knowledge.reading.reading_anchor` does not know this prefix.
TERM_PREFIX = "term-"


@dataclass(frozen=True)
class GlossaryEntry:
    """One defined word: as printed, its slug, and where a link to it lands."""

    term: str
    slug: str
    branch_anchor: str
    fragment: str


def _reviewed(terms: Sequence[str], rejected: Sequence[str]) -> tuple[str, ...]:
    """In: the derived terms and the reviewed rejections. Out: the terms that survive.

    Fails: `ValueError` naming a rejection that matches no term — a stale review is a review nobody
        re-read, and silently ignoring it would let the data drift from the document.
    """
    unknown = [term for term in rejected if term not in terms]
    if unknown:
        raise ValueError(
            f"REJECTED names {unknown!r}, which is not a term in the glossary branch: "
            "the review is stale (the document or the layout changed)"
        )
    return tuple(term for term in terms if term not in rejected)


def glossary_entries(
    source_file: str, blocks: Sequence[Block], branch_anchor: str
) -> tuple[GlossaryEntry, ...]:
    """In: a document's `source_file`, its glossary branch's blocks, and that branch's anchor.

    In:  `blocks` — the branch's rendered blocks, **already overlap-trimmed** (the reader trims them,
        so a headword the chunker repeated is not repeated here); `branch_anchor` — the anchor of
        the branch the links must open (`s1`).
    Out: one entry per distinct `Term`, in printed order; `()` for a document with no
        `GLOSSARY_BRANCH`.
    Side effects: none.
    Fails: `ValueError` from `_reviewed` when a rejection matches nothing.
    """
    key = GLOSSARY_BRANCH.get(source_file)
    if key is None:
        return ()

    found: list[str] = []
    for block in blocks:
        term = block.text if isinstance(block, Term) else ""
        if term and term not in found:
            found.append(term)

    terms = _reviewed(found, REJECTED.get(source_file, ()))
    return tuple(
        GlossaryEntry(
            term=term,
            slug=_slug(term),
            branch_anchor=branch_anchor,
            fragment=f"{TERM_PREFIX}{_slug(term)}",
        )
        for term in terms
    )


def _slug(term: str) -> str:
    """`Conversion Period` → `conversion-period`; `(GMO)` keeps its acronym, punctuation goes."""
    cleaned = "".join(
        char if char.isalnum() or char in " -/" else " " for char in term.lower()
    )
    return "-".join(part for part in cleaned.replace("/", " ").split() if part)


def with_term_anchors(blocks: Sequence[Block], seen: set[str] | None = None) -> tuple[Block, ...]:
    """Out: the blocks with each `Term` carrying `term-<slug>`, so a link can land on it.

    In:  `seen` — the terms already anchored, when the caller walks a branch passage by passage; the
         second occurrence of a headword gets no id, which is what keeps the page's ids unique.
    Side effects: adds the anchored terms to `seen` when given.
    Fails: never.
    """
    from dataclasses import replace

    seen = set() if seen is None else seen
    out: list[Block] = []
    for block in blocks:
        if isinstance(block, Term):
            slug = _slug(block.text)
            if slug in seen:
                out.append(block)
                continue
            seen.add(slug)
            out.append(replace(block, anchor=f"{TERM_PREFIX}{slug}"))
        else:
            out.append(block)
    return tuple(out)


__all__ = [
    "GLOSSARY_BRANCH",
    "REJECTED",
    "TERM_PREFIX",
    "GlossaryEntry",
    "glossary_entries",
    "with_term_anchors",
]
