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
from typing import Mapping

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from pgvector.django import CosineDistance

from knowledge.embedding import EmbeddingError, EmbeddingUnavailable, embed_texts
from knowledge.models import DocumentChunk, StandardSet

logger = logging.getLogger(__name__)

#: RRF's smoothing constant, per SPEC §4.5. Larger k flattens the contribution of the
#: top ranks; 60 is the value the spec fixes, so it is not tuned here.
RRF_K = 60

#: How many passages a follow-up's *context* arm may carry into the set. Two is enough to
#: restore the clause the previous turn found; more would let the old subject crowd out
#: the new one. It is also capped at a quarter of the budget, and never used below four.
CONTEXT_SEATS = 2

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

#: Words that name the *asking* rather than the subject: the verbs and furniture of an
#: everyday question ("can I **use**…", "does it **count** as…", "will I **pass**?").
#: Document frequency makes them look rare and therefore topical — `count` occurs in one
#: chunk, so it beat `genetically modified` on 2026-10-27 and the definitions page never
#: reached the model. They stay in the query (the OR arm keeps every word for recall);
#: they are never chosen as *the* lexical key, which is a claim about what the question
#: is about. Same insight as `_chatbot.FOLLOW_UP_MIN_SHARED`, applied to the chooser.
FILLER_TERMS = frozenset(
    """apply applied buy buys count counts get gets got grow grows growing keep keeps
    know knows make makes making need needs pass passes purchase purchased use used
    using want wants""".split()
)

#: The generated `search_vector` was built with `config="english"` (B1). The query must
#: use the same configuration or the tsquery lexemes will not match the stored ones.
SEARCH_CONFIG = "english"


def lexical_key(terms: list[str], frequencies: Mapping[str, int]) -> str:
    """The word the rare-term arm searches: the rarest word that names the subject.

    In:  the question's terms, in the order asked; each term's document frequency.
    Out: one term to search, or "" when nothing in the question occurs in the corpus.
    Fails: never.

    Two rules, both measured, and they are the whole of the chooser:

    1. **A filler is not a subject.** `FILLER_TERMS` is excluded from the choice; the
       first term breaks a frequency tie so the same question is deterministic.
    2. **When every known word is a filler, the old behaviour stands** (`subject or
       known`) rather than returning nothing: a question made entirely of filler words
       still has to search for something.

    One chooser, four call sites — the primary arm, the unknown-term hedge's first bet,
    the follow-up context arm, and `scripts/probe_chat.py`. A private rule in each would
    drift, and `testing_hazards.md` §2.7 is the receipt for what a drifting instrument
    costs.
    """
    known = [term for term in terms if term and frequencies.get(term, 0) > 0]
    subject = [term for term in known if term not in FILLER_TERMS] or known
    if not subject:
        return ""
    return sorted(subject, key=lambda term: (frequencies[term], terms.index(term)))[0]


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
    #: The file the corpus was ingested from, e.g. `pgs_docs/saoso-version-2.1-2026.pdf`.
    #: Carried so a *caller* can map a chunk to whatever public address that document has —
    #: `knowledge` does not know what a URL is, and must not learn (`build_principles.md` §I).
    document_source_file: str = ""
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
    #: The word the rare-term arm actually searched (`lexical_key`), or "" when the
    #: question had nothing searchable. Recorded so the probe prints what the product
    #: did rather than re-deriving it — the §2.7 defect is an instrument that computes
    #: its own answer.
    key: str = ""

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


def _retrieved_from_row(
    chunk,
    *,
    score: float = 0.0,
    lexical_rank: int | None = None,
    vector_rank: int | None = None,
) -> RetrievedChunk:
    """One stored chunk as the caller sees it.

    The single place the mapping lives: `search()` and `chunks_by_id()` both build
    `RetrievedChunk`s, and a second copy of these eight fields is a citation that renders
    differently depending on which path produced it.
    """
    return RetrievedChunk(
        chunk_id=chunk.pk,
        document_title=chunk.document.title,
        document_version=chunk.document.version,
        section_ref=chunk.section_ref,
        heading_path=chunk.heading_path,
        page=chunk.page,
        anchor=chunk.anchor,
        text=chunk.text,
        score=score,
        lexical_rank=lexical_rank,
        vector_rank=vector_rank,
        standard_set_id=chunk.document.standard_set_id,
        document_source_file=chunk.document.source_file,
        sub_refs=tuple(chunk.sub_refs or ()),
    )


def chunks_by_id(ids, *, standard_set: StandardSet) -> list[RetrievedChunk]:
    """Fetch stored chunks by id, in the order asked for, scoped to one set.

    In:  `ids` — chunk ids, in the order the caller wants them; `standard_set` — the
         corpus boundary.
    Out: the passages that exist **and belong to that set**, in the requested order.
         Unknown ids and foreign ids are dropped silently; a carried citation that does
         not exist cannot be cited, and one from another standard must never be.
    Side Effects: one query.
    Fails: never; an empty list is the answer to an empty request.

    `score` is 0.0 by construction: these passages were not ranked this turn, they were
    carried, so a score would invite a comparison that means nothing.
    """
    wanted = list(dict.fromkeys(cid for cid in ids if isinstance(cid, int)))
    if not wanted:
        return []
    rows = {
        chunk.pk: chunk
        for chunk in DocumentChunk.objects.filter(
            pk__in=wanted, document__standard_set=standard_set
        ).select_related("document")
    }
    return [_retrieved_from_row(rows[cid]) for cid in wanted if cid in rows]


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
        _retrieved_from_row(
            rows[chunk_id],
            score=score,
            lexical_rank=lex_ranks.get(chunk_id),
            vector_rank=vec_ranks.get(chunk_id),
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
    context_query: str = "",
) -> RetrievalResult:
    """Search a question's significant terms, rarest first, then the OR fallback.

    In:  `terms` — already-normalised, de-duplicated question words; `standard_set`;
         `limit`; `candidates`; `provider`; `question` — the visitor's wording, when the
         caller has it. It is embedded for the semantic arm, and it is the *only* query
         used when the corpus does not contain one of the terms (see below).
         `context_query` — a **lexical query** (terms joined by OR, not a sentence; the
         caller builds it with `build_retrieval_query`) from the previous question, when
         it has decided this turn is a follow-up. It is searched lexically and fused in
         last, so a follow-up keeps the new subject's ranking and regains the old one's
         clause. Handing it a natural question would AND its words and match nothing.
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

    **The hedge is two bets, one seat each** (2026-10-27). A single proxy word is only
    right while the unknown word is the subject. When it is incidental — `does selective
    seed *saving* count as GM?` — the words that name the subject are all in the corpus,
    and searching the rarest one (`count`) instead of them lost the definitions page that
    answers the question. So the first seat is `lexical_key` (the rarest word that names
    the subject) and the second is the OR of those words. The proxy bet is unchanged, so
    the cardboard measurement above still holds.
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
    key = lexical_key(cleaned, frequencies) or ordered[0]

    if question and unknown:
        # Two seats, two bets about what the unknown word is.
        #
        # The hedge used to search one word: the rarest known one, on the theory that it
        # is the proxy for the subject the corpus cannot name (cardboard -> neighbours).
        # That holds when the unknown word *is* the subject. It inverts when the unknown
        # word is incidental and a different word carries the question: on 2026-10-27
        # `what is the definition of genetically modified? does selective seed saving
        # count as GM?` lost `saving`, the hedge searched `count` (df 1) and returned the
        # biodiversity clause, and the definitions page that answers the question was one
        # OR-query away. So: the rarest known word as one seat, and the OR of the words
        # that name the subject as the other. Measured on the four unknown-term questions
        # that exist in the suite: this adds the definitions page and loses nothing.
        subject_terms = [
            term
            for term in cleaned
            if frequencies[term] > 0 and term not in FILLER_TERMS
        ]
        widest = " OR ".join(subject_terms)
        bets = [key] if not widest or widest == key else [key, widest]
        seats_each = max(1, min(2, limit) // len(bets))
        hedge_chunks: list[RetrievedChunk] = []
        hedge_only = True
        hedge_warnings: list[str] = []
        for bet in bets:
            found = search(
                bet,
                standard_set=standard_set,
                limit=seats_each,
                candidates=candidates,
                provider=provider,
                use_vector=False,
            )
            hedge_only = hedge_only and found.lexical_only
            hedge_warnings.extend(found.warnings)
            hedge_chunks.extend(found.chunks)
        semantic = search(
            question,
            standard_set=standard_set,
            limit=limit,
            candidates=candidates,
            provider=provider,
        )
        merged: list[RetrievedChunk] = []
        seen: set[int] = set()
        for chunk in (*hedge_chunks, *semantic.chunks):
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
            lexical_only=hedge_only and semantic.lexical_only,
            warnings=tuple(
                dict.fromkeys(
                    (
                        f"the corpus does not contain {', '.join(unknown)!r}: the "
                        "question was answered from its meaning, not its words",
                        *hedge_warnings,
                        *semantic.warnings,
                    )
                )
            ),
            key=key,
        )

    primary = search(
        key,
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

    # The context arm, when the caller says this turn continues the last one. It runs
    # *after* the new question has been ranked, and it displaces the weakest fragment
    # match rather than splitting the budget: the new subject keeps its seats, and the
    # previous turn can only take back what the new turn could not fill. Measured need:
    # a follow-up is searched as its fragment, so the clause the previous answer cited
    # is usually absent, and the audit then refuses the model's faithful citation.
    context = context_query.strip()
    if context and context != (question or "").strip():
        seats = min(CONTEXT_SEATS, max(0, limit // 4))
        if seats:
            # The same rule this module already applies to a question: the rarest known
            # word carries it. Measured 2026-10-23 on the shipped corpus: OR-ing the
            # previous question ran `use` and pulled Appendix 1's "natural non-renewable
            # resources" into a compost follow-up. One rare term cannot do that.
            context_terms = [term.strip() for term in context.split(" OR ") if term.strip()]
            context_frequency = {
                term: document_frequency(term, standard_set=standard_set)
                for term in context_terms
            }
            rarest = lexical_key(context_terms, context_frequency)
            carried = search(
                rarest,
                standard_set=standard_set,
                limit=seats,
                candidates=candidates,
                provider=provider,
                use_vector=False,
            ) if rarest else RetrievalResult(
                query=context,
                standard_set_id=getattr(standard_set, "pk", None),
                warnings=(
                    "the previous question's terms are all absent from the corpus, so "
                    "the context arm searched nothing",
                ),
            )
            incoming = [c for c in carried.chunks if c.chunk_id not in seen][:seats]
            if incoming:
                merged = merged[: max(0, limit - len(incoming))]
                seen = {chunk.chunk_id for chunk in merged}
                merged.extend(c for c in incoming if c.chunk_id not in seen)
            warnings = tuple(dict.fromkeys((*warnings, *carried.warnings)))

    return RetrievalResult(
        query=question or " OR ".join(cleaned),
        standard_set_id=getattr(standard_set, "pk", None),
        chunks=tuple(merged),
        lexical_only=primary.lexical_only and fallback.lexical_only,
        warnings=warnings,
        key=key,
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
    "CONTEXT_SEATS",
    "DEFAULT_LIMIT",
    "FUSED_CANDIDATES",
    "RRF_K",
    "SEMANTIC_SEATS",
    "Retained",
    "RetrievalResult",
    "RetrievedChunk",
    "chunks_by_id",
    "document_frequency",
    "fuse",
    "lexical_search",
    "search",
    "search_terms",
    "vector_search",
]
