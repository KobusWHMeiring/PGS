"""Hybrid retrieval over a corpus — FTS and pgvector, fused by rank (B7).

SPEC §4.5's rule is the whole point of this module:

    "Retrieval is **scoped to the session's `StandardSet`**, and the scope is applied
    *before* ranking — so the corpus boundary is not a rule the model has to remember,
    it is a filter it cannot escape."

Both arms therefore begin with `document__standard_set=...`. Applying it afterwards
would be a different thing entirely: a foreign chunk could win the ranking, be filtered
out, and leave a short result set while in-scope chunks existed — which looks like a
corpus with poor recall rather than a scoping bug. `test_the_scope_is_applied_before_ranking_not_after`
gives an out-of-set chunk the closest possible vector and fails if that happens.

**Fusion is Reciprocal Rank Fusion, not score addition.** `ts_rank_cd` is an unbounded
relevance figure and pgvector returns a cosine distance; they are not comparable, and
normalising them is a research project. RRF works on *ranks* — `1 / (k + rank)` summed
over the arms a chunk appears in, with `k = 60` from the spec — which needs no
calibration and cannot be gamed by one arm's scale. A consequence worth knowing: 1st+3rd
scores marginally above 2nd+2nd, because RRF rewards a strong showing in one arm as well
as consistency across both. Ties break on `chunk_id` so the same query never reorders.

**The lexical arm never depends on an API key.** FTS is the floor: with no key, or with
a corpus ingested `--no-embed`, results still come back and `lexical_only=True` says so.
An embedding failure during a query degrades to lexical rather than raising, because a
chatbot that refuses to answer because the embedding service hiccuped is worse than one
that answers from the standard and says which arm it used — but the degradation is
recorded in `warnings` and logged, never silent.

Read-only by design: nothing here writes, so it is safe to call from a public request.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from pgvector.django import CosineDistance

from knowledge.embedding import EmbeddingError, EmbeddingUnavailable, embed_texts
from knowledge.models import DocumentChunk, StandardSet

logger = logging.getLogger(__name__)

#: RRF's smoothing constant, per SPEC §4.5. Larger k flattens the contribution of the
#: top ranks; 60 is the value the spec fixes, so it is not tuned here.
RRF_K = 60

#: How many candidates each arm contributes before fusion. Generous on purpose: RRF can
#: only promote what an arm returned, so this bounds recall.
FUSED_CANDIDATES = 20

#: Chunks returned to the caller (and, in D, to the model as context).
DEFAULT_LIMIT = 5

#: How many of a caller's chunks may come from the semantic arm before the rare-term
#: arm fills the rest. Measured 2026-10-21: with five lexical chunks returned first, the
#: vector arm contributed *nothing* whenever the lexical arm reached the limit — the
#: hybrid retrieval the chatbot advertises was lexical in practice. Three seats is
#: enough for the semantic arm's best clauses and leaves the rare-term arm five.
SEMANTIC_SEATS = 3

#: The generated `search_vector` was built with `config="english"` (B1). The query must
#: use the same configuration or the tsquery lexemes will not match the stored ones.
SEARCH_CONFIG = "english"


@dataclass(frozen=True)
class Retained:
    """A fused candidate and the ranks that got it there. `None` = absent from an arm."""

    chunk_id: int
    lexical_rank: int | None = None
    vector_rank: int | None = None
    score: float = 0.0


@dataclass(frozen=True)
class RetrievedChunk:
    """One chunk as the caller sees it. Carries what a citation needs."""

    chunk_id: int
    document_title: str
    document_version: str
    section_ref: str | None
    heading_path: str
    page: int | None
    anchor: str
    text: str
    score: float
    lexical_rank: int | None = None
    vector_rank: int | None = None
    #: The corpus this chunk belongs to. Carried so a caller can re-assert the
    #: scope after retrieval (D3) without a second query, and so a citation audit
    #: cannot accept a foreign chunk from a buggy retriever.
    standard_set_id: int | None = None
    #: `[{"ref", "start", "end"}]` as stored. A citation's `sub_ref` must appear here;
    #: depth is never inferred (D15/D43).
    sub_refs: tuple[dict, ...] = ()

    def as_citation(self) -> dict:
        """The shape D's chat contract consumes: `{section_ref, quote, …}`.

        `quote` is the stored chunk text, unmodified — a citation that re-extracts or
        re-formats its own text cannot be checked against the file it points at.
        """
        return {
            "section_ref": self.section_ref,
            "quote": self.text,
            "page": self.page,
            "anchor": self.anchor,
            "heading_path": self.heading_path,
            "document": (
                self.document_title
                + (f" v{self.document_version}" if self.document_version else "")
            ),
        }


@dataclass(frozen=True)
class RetrievalResult:
    """What a query returned, and which arms answered it."""

    query: str
    standard_set_id: int | None
    chunks: tuple[RetrievedChunk, ...] = ()
    lexical_only: bool = False
    warnings: tuple[str, ...] = field(default=())

    @property
    def citations(self) -> list[dict]:
        return [chunk.as_citation() for chunk in self.chunks]


def fuse(rankings: list[list[int]], *, k: int = RRF_K) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion of ranked id lists.

    In:  `rankings` — one list of chunk ids per arm, best first. Ranks are positional, so
         a caller must pass them in order; duplicates inside one arm are ignored after
         their first (best) appearance, because an arm that listed a chunk twice would
         otherwise score it twice.
    Out: `[(chunk_id, score)]`, best first, ties broken by ascending id for
         determinism.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        seen: set[int] = set()
        for position, chunk_id in enumerate(ranking, start=1):
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + position)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def lexical_search(query: str, *, standard_set: StandardSet, limit: int) -> list[tuple[int, float]]:
    """Full-text search, scoped to the set.

    In:  `query` — raw user text; `standard_set` — the corpus boundary; `limit` — depth.
    Out: `[(chunk_id, rank_value)]`, best first. `websearch_to_tsquery` is used (Django's
        `search_type="websearch"`) because it parses what people actually type —
        quotes, `-`, `or` — and never raises on syntax it does not understand.
    """
    tsquery = SearchQuery(query, config=SEARCH_CONFIG, search_type="websearch")
    return list(
        DocumentChunk.objects.filter(document__standard_set=standard_set)
        .filter(search_vector=tsquery)
        .annotate(relevance=SearchRank(F("search_vector"), tsquery))
        .order_by("-relevance", "id")
        .values_list("id", "relevance")[:limit]
    )


def vector_search(vector: list[float], *, standard_set: StandardSet, limit: int) -> list[tuple[int, float]]:
    """Cosine nearest neighbours, scoped to the set.

    In:  `vector` — an embedding of the query; `standard_set`; `limit`.
    Out: `[(chunk_id, distance)]`, nearest first — distance, not similarity, because
        that is what `pgvector` orders by. Chunks with no vector are skipped rather than
        ranked last: a NULL cannot be a bad match, it is not a match.
    """
    return list(
        DocumentChunk.objects.filter(
            document__standard_set=standard_set, embedding__isnull=False
        )
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance", "id")
        .values_list("id", "distance")[:limit]
    )


def search(
    query: str,
    *,
    standard_set: StandardSet,
    limit: int = DEFAULT_LIMIT,
    candidates: int = FUSED_CANDIDATES,
    provider=None,
    use_vector: bool = True,
    vector_query: str | None = None,
) -> RetrievalResult:
    """Answer a query from one corpus, lexically and (when possible) semantically.

    In:  `query` — raw user text, used by the lexical arm; `standard_set` — the
         boundary that cannot be escaped; `limit`; `candidates` — per-arm depth before
         fusion; `provider` — an `EmbeddingProvider`, for tests; `use_vector` — set
         false to run the lexical arm alone (the rare-term arm of `search_terms` does
         this deliberately: a single word is a lexical key, not a semantic question);
         `vector_query` — what the semantic arm embeds, defaulting to `query`. It is
         separate because a token-joined string is a good lexical query and a bad
         sentence: the 2026-10-20 measurement in `search_terms` found the natural
         question retrieves the inputs clause while its OR form retrieves labelling.
    Out: a `RetrievalResult`. `lexical_only=True` means the vector arm did not run.
    Side Effects: embeds the query over the network when a vector is requested, a key
         is configured, and the corpus has vectors.
    Fails: nothing on the read path. A missing key, an unembedded corpus, or a provider
         error all degrade to lexical results with a warning recorded.
    """
    warnings: list[str] = []
    if not query or not query.strip():
        return RetrievalResult(
            query=query,
            standard_set_id=getattr(standard_set, "pk", None),
            warnings=("the query is empty, so nothing was searched",),
        )

    lexical = lexical_search(query, standard_set=standard_set, limit=candidates)

    vector: list[tuple[int, float]] = []
    if use_vector:
        has_vectors = DocumentChunk.objects.filter(
            document__standard_set=standard_set, embedding__isnull=False
        ).exists()
        has_key = _has_credentials(provider)
        if not has_key:
            warnings.append(
                "GEMINI_API_KEY is not set: retrieval is lexical only, so paraphrases that "
                "share no words with the standard will not be found."
            )
        if not has_vectors:
            warnings.append(
                "no chunks in this StandardSet carry embeddings: retrieval is lexical only. "
                "Re-ingest with embeddings to enable the vector arm."
            )

        if has_vectors and has_key:
            try:
                vector = vector_search(
                    embed_texts([vector_query or query], provider=provider)[0],
                    standard_set=standard_set,
                    limit=candidates,
                )
            except EmbeddingError as error:
                # Degrade, do not raise: a lexical answer is better than no answer, and the
                # caller can see which arms were used. Never silent (see the docstring).
                logger.warning("retrieval: query embedding failed, lexical only: %s", error)
                warnings.append(f"query embedding failed, so the vector arm was skipped: {error}")

    lexical_only = not vector
    fused = fuse(
        [[chunk_id for chunk_id, _ in lexical], [chunk_id for chunk_id, _ in vector]],
        k=RRF_K,
    )
    lex_ranks = {chunk_id: position for position, (chunk_id, _) in enumerate(lexical, 1)}
    vec_ranks = {chunk_id: position for position, (chunk_id, _) in enumerate(vector, 1)}

    top = fused[:limit]
    rows = {
        chunk.pk: chunk
        for chunk in DocumentChunk.objects.filter(pk__in=[chunk_id for chunk_id, _ in top])
        .select_related("document")   # §VI: one query, not one per citation
    }
    chunks = tuple(
        RetrievedChunk(
            chunk_id=chunk_id,
            document_title=rows[chunk_id].document.title,
            document_version=rows[chunk_id].document.version,
            section_ref=rows[chunk_id].section_ref,
            heading_path=rows[chunk_id].heading_path,
            page=rows[chunk_id].page,
            anchor=rows[chunk_id].anchor,
            text=rows[chunk_id].text,
            score=score,
            lexical_rank=lex_ranks.get(chunk_id),
            vector_rank=vec_ranks.get(chunk_id),
            standard_set_id=rows[chunk_id].document.standard_set_id,
            sub_refs=tuple(rows[chunk_id].sub_refs or ()),
        )
        for chunk_id, score in top
        if chunk_id in rows
    )

    return RetrievalResult(
        query=query,
        standard_set_id=getattr(standard_set, "pk", None),
        chunks=chunks,
        lexical_only=lexical_only,
        warnings=tuple(warnings),
    )


def document_frequency(term: str, *, standard_set: StandardSet) -> int:
    """How many chunks in the set contain `term`, using the same FTS configuration.

    In:  one already-tokenised term; the corpus.
    Out: a count. Used to find the most discriminative word in a question: "standard"
        occurs in dozens of chunks, "traceability" in four, and "Traceability" alone is
        a better retrieval query than their AND or a plain OR.
    Fails: never for a non-empty term; `websearch_to_tsquery` tolerates raw input.
    """
    if not term:
        return 0
    tsquery = SearchQuery(term, config=SEARCH_CONFIG, search_type="websearch")
    return (
        DocumentChunk.objects.filter(document__standard_set=standard_set)
        .filter(search_vector=tsquery)
        .count()
    )


def search_terms(
    terms: list[str],
    *,
    standard_set: StandardSet,
    limit: int = DEFAULT_LIMIT,
    candidates: int = FUSED_CANDIDATES,
    provider=None,
    question: str = "",
) -> RetrievalResult:
    """Search a question's significant terms, rarest first, then the OR fallback.

    In:  `terms` — already-normalised, de-duplicated question words; `standard_set`;
         `limit`; `candidates`; `provider`; `question` — the visitor's wording, when the
         caller has it. It is embedded for the semantic arm, and it is the *only* query
         used when the corpus does not contain one of the terms (see below).
    Out: a `RetrievalResult` whose chunks are the rare-term results first, then the
         broader OR results, de-duplicated and truncated to `limit`.

    Why two arms instead of one query: Postgres's `ts_rank` rewards a chunk that
    matches *any* of the weighted terms, and common words dominate. Measured against
    the shipped corpus on 2026-10-19, "standard OR traceability" ranked a landscape
    paragraph above the SAOSO clause that actually contains the requirement, because
    the paragraph also contained "standard". The rarest term is the one that carries
    the question: searching it alone puts the clause back in the set, and the OR arm
    keeps the recall for questions whose terms are all common.

    The rare-term arm is **lexical only**; the vector arm runs once, on the question.
    Measured 2026-10-20 with the corpus embedded: embedding the rare word as a semantic
    query retrieved S5/Appendix 6b and pushed SAOSO Appendix 2 out of the top 8, so the
    manure question refused again despite a good corpus. A single word is a lexical
    key, not a semantic question. This also spends one query embedding per question
    instead of two.

    **An unknown word is the subject, not noise.** When a term does not occur in the
    corpus at all, the lexical arms can only search a proxy: for "can I use cardboard
    from my neighbours?" the rarest known word is "neighbours", and searching it
    returned the wild-harvest and child-labour clauses while the inputs clause
    (SAOSO 4.4.4) never reached the model. Measured 2026-10-21: embedding the *question*
    puts 4.4.4 in the top 8; embedding `use OR cardboard OR neighbours` does not. So
    when a question has an unknown term, the lexical arm keeps only its top two chunks
    as a hedge and the semantic arm takes the rest of the budget: the visitor's own
    words are the only description of the subject, and five proxy matches must not crowd
    out of the one clause that governs it. When every term is known, the rare-term arm
    still leads (that decision is separately measured and pinned), but only for
    `limit - SEMANTIC_SEATS` chunks: the semantic arm gets the rest, because otherwise a
    full lexical result set leaves the vector arm contributing nothing at all.

    The hedge is also the offline path: with no embedding key the semantic arm returns
    nothing, and the two lexical chunks are still better than an empty result set.
    """
    cleaned = [term.strip() for term in terms if term and term.strip()]
    if not cleaned:
        return RetrievalResult(
            query="",
            standard_set_id=getattr(standard_set, "pk", None),
            warnings=("the question had no searchable terms",),
        )

    frequencies = {
        term: document_frequency(term, standard_set=standard_set) for term in cleaned
    }
    positive = [term for term in cleaned if frequencies[term] > 0]
    unknown = [term for term in cleaned if frequencies[term] == 0]
    # The first occurrence breaks a frequency tie, so the same question is deterministic.
    ordered = sorted(
        positive or cleaned,
        key=lambda term: (frequencies.get(term, 0), cleaned.index(term)),
    )

    if question and unknown:
        hedge = search(
            ordered[0],
            standard_set=standard_set,
            limit=min(2, limit),
            candidates=candidates,
            provider=provider,
            use_vector=False,
        )
        semantic = search(
            question,
            standard_set=standard_set,
            limit=limit,
            candidates=candidates,
            provider=provider,
        )
        merged: list[RetrievedChunk] = []
        seen: set[int] = set()
        for chunk in (*hedge.chunks, *semantic.chunks):
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            merged.append(chunk)
            if len(merged) >= limit:
                break
        return RetrievalResult(
            query=question,
            standard_set_id=getattr(standard_set, "pk", None),
            chunks=tuple(merged),
            lexical_only=hedge.lexical_only and semantic.lexical_only,
            warnings=tuple(
                dict.fromkeys(
                    (
                        f"the corpus does not contain {', '.join(unknown)!r}: the "
                        "question was answered from its meaning, not its words",
                        *hedge.warnings,
                        *semantic.warnings,
                    )
                )
            ),
        )

    primary = search(
        ordered[0],
        standard_set=standard_set,
        limit=limit,
        candidates=candidates,
        provider=provider,
        # The rare word is a lexical key. The semantic query is the fallback below.
        use_vector=False,
    )
    fallback = search(
        " OR ".join(cleaned),
        standard_set=standard_set,
        limit=limit,
        candidates=candidates,
        provider=provider,
        vector_query=question or None,
    )

    merged: list[RetrievedChunk] = []
    seen: set[int] = set()
    # The rare-term arm leads, but it does not own the whole budget: three seats are
    # reserved for the semantic arm, which is otherwise empty whenever the lexical arm
    # returns a full limit (the shipped five-chunk default did exactly that).
    for chunk in primary.chunks[: max(0, limit - SEMANTIC_SEATS)]:
        if chunk.chunk_id not in seen:
            seen.add(chunk.chunk_id)
            merged.append(chunk)
    semantic_added = 0
    for chunk in fallback.chunks:
        if chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        merged.append(chunk)
        semantic_added += 1
        if semantic_added >= SEMANTIC_SEATS:
            break
    for chunk in (*primary.chunks, *fallback.chunks):
        if len(merged) >= limit:
            break
        if chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        merged.append(chunk)

    warnings = tuple(dict.fromkeys((*primary.warnings, *fallback.warnings)))
    return RetrievalResult(
        query=question or " OR ".join(cleaned),
        standard_set_id=getattr(standard_set, "pk", None),
        chunks=tuple(merged),
        lexical_only=primary.lexical_only and fallback.lexical_only,
        warnings=warnings,
    )


def _has_credentials(provider) -> bool:
    """Whether the vector arm *could* run: an injected provider, or a configured key.

    Importing settings lazily keeps this module importable without Django configured,
    which the migration graph and `lint-imports` both do.
    """
    if provider is not None:
        return True
    from django.conf import settings

    return bool(getattr(settings, "GEMINI_API_KEY", ""))


__all__ = [
    "DEFAULT_LIMIT",
    "FUSED_CANDIDATES",
    "RRF_K",
    "SEMANTIC_SEATS",
    "Retained",
    "RetrievalResult",
    "RetrievedChunk",
    "document_frequency",
    "fuse",
    "lexical_search",
    "search",
    "search_terms",
    "vector_search",
]
