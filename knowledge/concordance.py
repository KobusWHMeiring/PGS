"""The document's own structure, as the reader's navigation (D68).

A branch is a **printed division**: the top-level reference a chunk carries (`S5.1.9` →
`S5`, `§4.5(2)(c)` → `§4`, `Appendix 2` whole), or — for a document that prints no
numbering — the first component of its heading trail. Nothing here is stored: the grouping
is computed from `DocumentChunk` per request, so it cannot drift from the corpus the way a
second store would.

Three rules come from measurement, not taste (`CONCORDANCE_PRD` §10.1–10.3) and each is a
test in `knowledge/tests/test_concordance.py`:

1. grouping is by **reference first**, because a section's opening chunk carries the
   reference and no heading (`1. DEFINITIONS`);
2. a roman section heading converts to its decimal body (`§II` covers `2.1`–`2.5`);
3. a heading used by more than one branch is a **divider** (`APPENDICES`), never a title.

What a branch is *called* comes from the document's printed TOC when it has one (D68 §7.5),
because the alternative misnames the two branches a reader consults most (§10.5).

No `core` import (`build_principles.md` §I): this module knows documents and chunks, not URLs.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from django.utils.text import slugify

from knowledge.models import DocumentChunk, StandardDocument
from knowledge.reading import reading_chunks, unique_anchors

#: Roman section numbers the OPP prints beside decimal body numbering (`§II` covers `2.1`).
_ROMAN = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
}

#: Where a chunk with neither a reference nor a heading goes. Guessing instead would file a
#: document's front matter inside section 1, which is worse than naming it for what it is.
PRELIMINARY = "Preliminary pages"


def _ref_key(section_ref: str) -> str:
    """`S5.1.9` → `S5`, `§4.5(2)(c)` → `§4`, `§II` → `§2`, `Appendix 2` unchanged."""
    ref = section_ref.strip()
    for prefix in ("S", "§"):
        if ref.startswith(prefix):
            head = ref.split(".", 1)[0].strip()[len(prefix) :]
            if head.upper() in _ROMAN:
                return f"{prefix}{_ROMAN[head.upper()]}"
            return f"{prefix}{head}"
    return ref


def _branch_key(at: DocumentChunk) -> str:
    """Which branch a chunk belongs to: its reference, else its first heading, else the front."""
    if at.section_ref:
        return _ref_key(at.section_ref)
    if at.heading_path:
        return at.heading_path.split(" > ", 1)[0].strip()
    return PRELIMINARY


def _first_heading(chunks: list[DocumentChunk]) -> str | None:
    for at in chunks:
        if at.heading_path:
            return at.heading_path.split(" > ", 1)[0].strip()
    return None


@dataclass(frozen=True)
class ConcordanceSection:
    """One branch: a printed division, its passages, and — when the text has one — its name."""

    key: str
    title: str
    anchor: str
    page: int | None
    passages: tuple[tuple[DocumentChunk, str], ...] = ()
    #: True for a number the printed standard reserves and does not use (`10 to 19`).
    #: A reserved row is a row with no passages: the standard says these do not exist yet.
    reserved: bool = False

    @property
    def chunk_count(self) -> int:
        return len(self.passages)


def _match_key(label: str) -> str:
    """The key a TOC label and a branch key can be compared on.

    The TOC prints a clause as `5. …` and the body cites it as `S5.1.9`; the OPP prints `II.` and
    numbers `2.1`. Both name the same printed division, so the prefix has to come off or nothing
    ever matches. `Appendix 2` keeps its word: that is how both the TOC and the body print it.
    """
    ref = label.strip()
    if len(ref) > 1 and ref[0] in "S§" and ref[1].isdigit():
        return ref[1:]
    return ref


def _toc_title(entry: dict) -> str:
    """`1` + `Definitions` → `1. Definitions`; a range keeps its own wording."""
    label = entry["label"].strip()
    title = (entry.get("title") or "").strip()
    return f"{label}. {title}" if title else label


def _reference_title(key: str, chunks: list[DocumentChunk]) -> str:
    """The branch's own reference, made readable: `S1` → `Section 1`, `§I` stays `§I`."""
    section_ref = chunks[0].section_ref if chunks else None
    if section_ref and re.fullmatch(r"S\d+", section_ref):
        return f"Section {section_ref[1:]}"
    return section_ref or key


@dataclass(frozen=True)
class Concordance:
    """The tree, plus the printed sections the corpus does not hold."""

    sections: tuple[ConcordanceSection, ...]
    #: Printed sections with text that no branch covers — SAOSO's Section A (pp. 4–11) and
    #: Appendices A–C (pp. 93–96), measured 2026-10-27 (§10.6). The page states these; a
    #: tree of 22 branches presented as "the standard" would claim more than the corpus has.
    missing: tuple[str, ...] = ()


#: Branch titles that the document's own printed heading gets wrong. Reviewed data, keyed by
#: `(source_file, branch key)` in the same idiom as `knowledge.tables.TABLE_ROWS`: the
#: correction lives beside the corpus that needs it, and a test proves each entry both matches
#: a real branch and is used. Only entries for a document with *no* TOC belong here — where a
#: printed TOC exists it is the source of names, never a hand-written map (D68 §7.5).
REVIEWED_BRANCH_TITLES: dict[tuple[str, str], str] = {
    ("pgs_docs/PGS Certification landscape_Final.pdf", "R500"): "Cost of joining a PGS group",
    ("pgs_docs/PGS Certification landscape_Final.pdf", "PGS SA."): "Working with PGS South Africa",
}


def build_concordance(document: StandardDocument) -> Concordance:
    """In: a document. Out: its printed structure, one branch per division, in printed order.

    In:  nothing beyond the document.
    Out: `Concordance` — branches (with reserved rows interleaved where the printed TOC puts
         them) and the printed sections the corpus does not hold.
    Side effects: one query for the chunks.
    Fails: never deliberately. A document with no TOC and no headings is one branch.
    """
    pairs = unique_anchors(reading_chunks(document))
    order: list[str] = []
    grouped: dict[str, list[DocumentChunk]] = {}
    anchored: dict[str, list[tuple[DocumentChunk, str]]] = {}
    for at, anchor in pairs:
        key = _branch_key(at)
        if key not in grouped:
            order.append(key)
            grouped[key] = []
            anchored[key] = []
        grouped[key].append(at)
        anchored[key].append((at, anchor))

    headings = {key: _first_heading(grouped[key]) for key in order}
    shared = Counter(heading for heading in headings.values() if heading)
    toc: list[dict] = list(document.toc or [])
    reviewed = {
        key: title
        for (source, key), title in REVIEWED_BRANCH_TITLES.items()
        if source == document.source_file
    }

    def first_page(key: str) -> int | None:
        pages = [at.page for at in grouped[key] if at.page is not None]
        return min(pages) if pages else None

    #: TOC label → the branches that could answer to it. Section A prints `1. Introduction` on
    #: p4 and Section B prints `1. Definitions` on p22, so a label alone is not a match.
    by_label: dict[str, list[str]] = {}
    for key in order:
        by_label.setdefault(_match_key(key), []).append(key)

    matched: set[str] = set()

    def branch_for(entry: dict) -> str | None:
        """The branch this TOC entry names, or None when the corpus does not hold it.

        Label **and** printed page must agree, which is a measurement rather than a guess: every
        section the corpus holds matches its TOC entry's printed page exactly (22, 30, 33 … 76,
        70), and the two entries that share a label differ only in page (4 vs 22). A page-less
        entry falls back to the label, because a reserved row or a reprint may omit it.
        """
        keys = [key for key in by_label.get(_match_key(entry["label"]), []) if key not in matched]
        if not keys:
            return None
        page = entry.get("printed_page")
        if page is None:
            return keys[0]
        exact = [key for key in keys if first_page(key) == page]
        return exact[0] if exact else None

    def render(key: str, entry: dict | None = None) -> ConcordanceSection:
        passages = tuple(anchored[key])
        heading = headings[key]
        if entry is not None:
            title = _toc_title(entry)
        elif key in reviewed:
            title = reviewed[key]
        elif heading and shared[heading] == 1:
            title = heading
        else:
            title = _reference_title(key, grouped[key])
        return ConcordanceSection(
            key=key, title=title, anchor=passages[0][1], page=first_page(key), passages=passages
        )

    # Printed order: walk the TOC so a reserved row lands between §9 and §20 where the standard
    # prints it, then append any branch the TOC does not mention (a document with no TOC, or a
    # section the TOC omits) in document order.
    sections: list[ConcordanceSection] = []
    missing: list[str] = []
    for entry in toc:
        if entry.get("kind") == "RANGE":
            sections.append(
                ConcordanceSection(
                    key=_match_key(entry["label"]),
                    title=_toc_title(entry),
                    anchor=slugify(entry["label"]),
                    page=entry.get("printed_page"),
                    reserved=True,
                )
            )
            continue
        key = branch_for(entry)
        if key is None:
            # Printed, and not in the corpus. Not an error: Section A and Appendices A–C are
            # absent today (§10.6), and the page says so instead of pretending they are not there.
            missing.append(_toc_title(entry))
            continue
        matched.add(key)
        sections.append(render(key, entry))

    for key in order:
        if key not in matched:
            sections.append(render(key))

    return Concordance(sections=tuple(sections), missing=tuple(missing))


def concordance_sections(document: StandardDocument) -> list[ConcordanceSection]:
    """The branches alone. A thin alias, so a test can name what it is asserting."""
    return list(build_concordance(document).sections)


__all__ = [
    "Concordance",
    "ConcordanceSection",
    "PRELIMINARY",
    "REVIEWED_BRANCH_TITLES",
    "build_concordance",
    "concordance_sections",
]
