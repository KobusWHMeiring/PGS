"""A document as a reader sees it: ordered passages, stable anchors, and a search box.

`/documents/<code>/read/` is where a citation lands. It cannot be the PDF: the file is
served as an attachment, so a `#page=` fragment has no viewer to land in. It is also the
*cheaper* surface — the text is already in `DocumentChunk`, and a quote can be found on a
rendered page in a way it cannot be found by hoping a PDF viewer scrolls to a number.

**The anchor is derived, never stored.** `section_ref` survives a `--force` re-ingest; a
chunk id does not, and `build_principles.md` §I forbids a sequential id on a public surface.
The duplicate-`section_ref` ratchet is held at zero (`tests/test_ingest.py`), which is what
makes a section reference a usable anchor rather than a collision.

No `core` import, ever (`build_principles.md` §I). This module knows about documents and
chunks; it does not know what a URL is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.utils.text import slugify

from knowledge.models import DocumentChunk, StandardDocument
from knowledge.services import SEARCH_CONFIG

#: How much of a passage a search result shows. Wide enough to read a rule, narrow enough
#: to scan a list of them.
SNIPPET_CHARS = 240

#: The longest anchor a citation may carry. `section_ref` is 128 chars in the database and
#: a heading trail can be 512; an anchor beyond this is truncated, not rejected, because a
#: truncated anchor still lands on the right passage — the passages below it are unaffected.
MAX_ANCHOR_CHARS = 64

#: How much of a passage's own words may appear in its anchor: the first few words, so the anchor
#: reads like a locator a person can check in the URL (`#appendix-2-wood-bark-and-sawdust`) rather
#: than a hash, and stays short enough to be one.
DISAMBIGUATOR_WORDS = 4
MAX_DISAMBIGUATOR_CHARS = 40

#: A slug that ends on one of these reads like a typo (`…slurry-and`). Dropped from the anchor,
#: which is a thing a person may read in the address bar.
TRAILING_CONNECTIVES = {"and", "or", "of", "the", "with", "for", "to"}


def reading_chunks(document: StandardDocument) -> list[DocumentChunk]:
    """In: a document. Out: its chunks in document order. Side effects: one query.

    Ordered by primary key, not by page: `bulk_create` writes chunks in document order, and
    `Meta.ordering` is deliberately empty ("B7 fuses ranked queries, it does not page").
    Page order alone would interleave chunks inside one printed page arbitrarily.
    """
    return list(document.chunks.order_by("id"))


def _slugify_locator(text: str) -> str:
    """A locator as a fragment: `S20.1.1` → `s20-1-1`, `§4.5(2)(c)` → `4-5-2-c`.

    Django's `slugify` *deletes* a dot rather than replacing it, so a bare pass would turn
    `S20.1.1` into `s2011` — unreadable in a URL a reader may edit by hand, and colliding with
    `S20.11`. Punctuation that separates parts of a reference becomes a hyphen; everything else
    goes through `slugify` as usual.
    """
    separated = re.sub(r"[.()\[\]/\\]+", "-", text)
    separated = separated.replace("§", "")
    return slugify(separated, allow_unicode=False)[:MAX_ANCHOR_CHARS].strip("-_")


def reading_anchor(
    section_ref: str | None, anchor: str = "", heading_path: str = ""
) -> str:
    """In: a chunk's locators. Out: a URL fragment, stable across re-ingest.

    `section_ref` first because it is what a citation quotes and what survives a rebuild.
    Falls back to the content-derived `anchor` and then to the last heading of the trail, so
    no chunk is unreachable — the ingest only guarantees one of the three is set.
    """
    for candidate in (section_ref, anchor, heading_path.split(" > ")[-1]):
        if candidate and candidate.strip():
            slug = _slugify_locator(candidate)
            if slug:
                return slug
    return "passage"


def _content_slug(chunk: DocumentChunk) -> str:
    """A slug of the passage's own words: its content anchor, else its first line, else its heading.

    The order is deliberate. `anchor` is already content-derived (the ingest sets it for a block the
    source never numbered), then the printed first line, then the last heading — so the
    disambiguator is a property of the text in every case, and of the file only when the text is
    empty. Words, not characters: a 40-character cut leaves `…only-if-not-chemica`, which reads as
    a typo rather than a locator.
    """
    for candidate in (
        chunk.anchor,
        (chunk.text or "").split("\n", 1)[0],
        chunk.heading_path.split(" > ")[-1],
    ):
        slug = _slugify_locator(candidate) if candidate and candidate.strip() else ""
        if slug:
            words = slug.split("-")[:DISAMBIGUATOR_WORDS]
            while len(words) > 1 and words[-1] in TRAILING_CONNECTIVES:
                words.pop()
            return "-".join(words)[:MAX_DISAMBIGUATOR_CHARS].strip("-")
    return "passage"


def unique_anchors(chunks: list[DocumentChunk]) -> list[tuple[DocumentChunk, str]]:
    """In: chunks in order. Out: `(chunk, anchor)` with the anchor unique within the document.

    The **first** passage of a shared reference keeps the bare anchor, because that is the anchor
    every citation shipped before 2026-10-27 carries (`#appendix-2`); later ones are suffixed with
    a slug of their own words (`#appendix-2-wood-bark-and-sawdust`). The old `-2`, `-3` suffix is
    gone: it was ingest order wearing a locator's clothes (`build_principles.md` §I).

    A numeric suffix survives only as a last resort, when two passages begin with the same words —
    and then the anchor is still stable for unchanged text.
    """
    used: set[str] = set()
    pairs: list[tuple[DocumentChunk, str]] = []
    for chunk in chunks:
        base = reading_anchor(chunk.section_ref, chunk.anchor, chunk.heading_path)
        if base not in used:
            used.add(base)
            pairs.append((chunk, base))
            continue
        candidate = f"{base}-{_content_slug(chunk)}"
        attempt = 1
        while candidate in used:
            attempt += 1
            candidate = f"{base}-{attempt}"
        used.add(candidate)
        pairs.append((chunk, candidate))
    return pairs


def reader_anchor_map(document: StandardDocument) -> dict[int, str]:
    """`{chunk pk: anchor}` exactly as the reader renders them, suffixes included.

    A citation's fragment must be the *reader's* id for the chunk it quotes, and
    `reading_anchor` alone cannot produce it: eight SAOSO §1 chunks share `S1`, so the
    reader disambiguates them (`s1`, `s1-2`, … `s1-8`) and a GMO citation that linked to
    `#s1` landed at the top of a 21 000-character definitions section instead of on the
    definition it quoted (2026-10-27, `CHAT_TRUTHFULNESS_PRD.md` F7).

    One query, and the map is per document: the suffix is positional, so it must be
    computed from the same ordered chunk list the reader uses (`reading_chunks`).
    """
    return {
        chunk.pk: anchor
        for chunk, anchor in unique_anchors(reading_chunks(document))
    }


@dataclass(frozen=True)
class SearchHit:
    """One in-document search result.

    Split into `before`/`hit`/`after` rather than carrying HTML: the template escapes each
    part and wraps `hit` in `<mark>`, so a passage can never inject markup into the page and
    the highlight cannot be built by string replacement inside the template.
    """

    anchor: str
    locator: str
    page: int | None
    before: str
    hit: str
    after: str


def _words(query: str) -> list[str]:
    """The words a person typed, minus punctuation and one-letter noise."""
    return [word for word in re.split(r"[^\w§.-]+", query) if len(word) > 1]


def search_in_document(
    document: StandardDocument,
    query: str,
    *,
    limit: int = 20,
    anchors: dict[int, str] | None = None,
) -> list[SearchHit]:
    """In: a document and what a person typed. Out: matching passages, best first.

    In:  `query` — free text from the reader's box; `limit` — how many passages; `anchors` —
         `{chunk id: anchor}` as the reader renders them, so a hit links to its own passage
         rather than to the first one sharing its reference (`CONCORDANCE_PRD` §10.7).
         Defaults to computing the map from this document.
    Out: `SearchHit` rows; empty when the query is empty or nothing matches.
    Side effects: at most one extra query when `anchors` is None (read-only).
    Fails: never deliberately. A search box that raises is worse than one that finds
        nothing, and the reader page has no error surface for it.

    Two passes, because a search box is not a query language. `websearch_to_tsquery` ANDs
    its terms, so "cardboard neighbour" finds only a passage containing both — a real
    question typed into a search box usually means *any* of its words
    (`testing_hazards.md` §2.4). The first pass keeps phrase behaviour honest ("free of
    significant contaminants"); the second ORs the words and runs only when the first found
    nothing.
    """
    words = _words(query)
    if not words:
        return []
    if anchors is None:
        anchors = {chunk.pk: anchor for chunk, anchor in unique_anchors(reading_chunks(document))}

    base = document.chunks.all()
    for search_query in (
        SearchQuery(query, config=SEARCH_CONFIG, search_type="websearch"),
        SearchQuery(" | ".join(words), config=SEARCH_CONFIG, search_type="raw"),
    ):
        ranked = (
            base.filter(search_vector=search_query)
            .annotate(rank=SearchRank("search_vector", search_query))
            .order_by("-rank", "id")[:limit]
        )
        hits = [_hit(chunk, words, anchors) for chunk in ranked]
        if hits:
            return hits
    return []


def _hit(chunk: DocumentChunk, words: list[str], anchors: dict[int, str]) -> SearchHit:
    """The passage, sliced around the first word the reader typed."""
    text = chunk.text or ""
    lowered = text.lower()
    positions = [pos for pos in (lowered.find(word.lower()) for word in words) if pos >= 0]
    at = min(positions) if positions else 0

    start = max(0, at - SNIPPET_CHARS // 3)
    end = min(len(text), start + SNIPPET_CHARS)
    window = text[start:end]

    word_at = max(0, at - start)
    typed = next((word for word in words if lowered.find(word.lower()) == at), "")
    hit = window[word_at : word_at + len(typed)] or window[word_at : word_at + 1]
    return SearchHit(
        anchor=anchors.get(chunk.pk)
        or reading_anchor(chunk.section_ref, chunk.anchor, chunk.heading_path),
        locator=chunk.section_ref or chunk.anchor or chunk.heading_path or f"p{chunk.page}",
        page=chunk.page,
        before=window[:word_at],
        hit=hit,
        after=window[word_at + len(hit) :],
    )


__all__ = [
    "MAX_ANCHOR_CHARS",
    "SNIPPET_CHARS",
    "SearchHit",
    "reader_anchor_map",
    "reading_anchor",
    "reading_chunks",
    "search_in_document",
    "unique_anchors",
]
