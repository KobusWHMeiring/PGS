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


def unique_anchors(chunks: list[DocumentChunk]) -> list[tuple[DocumentChunk, str]]:
    """In: chunks in order. Out: `(chunk, anchor)` with collisions suffixed `-2`, `-3`…

    A suffix is a local disambiguator, not an identity: the *first* chunk with a reference
    keeps the plain anchor, so a citation's link lands on the passage a reader searching for
    that reference expects first.
    """
    seen: dict[str, int] = {}
    pairs: list[tuple[DocumentChunk, str]] = []
    for chunk in chunks:
        base = reading_anchor(chunk.section_ref, chunk.anchor, chunk.heading_path)
        count = seen.get(base, 0) + 1
        seen[base] = count
        pairs.append((chunk, base if count == 1 else f"{base}-{count}"))
    return pairs


@dataclass(frozen=True)
class ReadingEntry:
    """One line of the reader's contents list."""

    anchor: str
    locator: str
    page: int | None
    heading_path: str


def contents(document: StandardDocument) -> list[ReadingEntry]:
    """In: a document. Out: one entry per chunk, in order. Side effects: one query."""
    return [
        ReadingEntry(
            anchor=anchor,
            locator=chunk.section_ref or chunk.anchor or chunk.heading_path or f"p{chunk.page}",
            page=chunk.page,
            heading_path=chunk.heading_path,
        )
        for chunk, anchor in unique_anchors(reading_chunks(document))
    ]


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
    document: StandardDocument, query: str, *, limit: int = 20
) -> list[SearchHit]:
    """In: a document and what a person typed. Out: matching passages, best first.

    In:  `query` — free text from the reader's box; `limit` — how many passages.
    Out: `SearchHit` rows; empty when the query is empty or nothing matches.
    Side effects: none (read-only).
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
        hits = [_hit(chunk, words) for chunk in ranked]
        if hits:
            return hits
    return []


def _hit(chunk: DocumentChunk, words: list[str]) -> SearchHit:
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
        anchor=reading_anchor(chunk.section_ref, chunk.anchor, chunk.heading_path),
        locator=chunk.section_ref or chunk.anchor or chunk.heading_path or f"p{chunk.page}",
        page=chunk.page,
        before=window[:word_at],
        hit=hit,
        after=window[word_at + len(hit) :],
    )


__all__ = [
    "MAX_ANCHOR_CHARS",
    "ReadingEntry",
    "SNIPPET_CHARS",
    "SearchHit",
    "contents",
    "reading_anchor",
    "reading_chunks",
    "search_in_document",
    "unique_anchors",
]
