"""The retrieval strategy: a question's terms in, a fused set of passages out.

Split out of `knowledge/services.py` (CONTEXT_CUTS_PRD step 8). `services.py` is the layer
below: how to score a *query* against a corpus (`lexical_search`, `vector_search`, `fuse`,
`chunks_by_id`, `document_frequency`, `lexical_key`). This module is the layer that decides
*which queries to ask and how to combine them* — rarest term first, then the OR fallback, the
context arm for a follow-up, the alias seats, the table rows that travel with a passage.

The two are separated because the second is the one that grows: every retrieval improvement
since 2026-10-19 has been a change to *strategy* (D49, D69, D79/E's seats) and none to the
scoring primitives. A file that mixes them makes the cheap change expensive to find.

**The PRD named this seam differently and got it backwards:** it called `search_terms` "term
analysis" and put `search` on the other side. `search_terms` reads the corpus (rarity, aliases,
seats) and returns a `RetrievalResult`; it *is* the retrieval proper. What stays behind is the
scoring. The public entry point `search` stays in `services.py` because `search_terms` calls it
and the arrow must point one way.
"""

from __future__ import annotations

from dataclasses import replace

from knowledge.aliases import ALIASES
from knowledge.models import StandardSet
from knowledge.services import (
    ALIAS_SEATS,
    CONTEXT_SEATS,
    DEFAULT_LIMIT,
    FILLER_TERMS,
    FUSED_CANDIDATES,
    SEMANTIC_SEATS,
    RetrievalResult,
    RetrievedChunk,
    _retrieved_from_row,
    document_frequency,
    is_heading_only,
    lexical_key,
    search,
)
from knowledge.table_context import (
    TABLE_ROW_SEATS,
    TableContext,
    reviewed_table_for_section,
    row_chunks_for,
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
    full lexical result set leaves the vector arm contributing nothing at all. Those
    seats are filled in the **semantic arm's own order** and never by a heading — see
    `is_heading_only` and the note in the body, where the fee band that the old fused
    order could not seat is the measurement.

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
    # Asked at **candidate depth**, not at `limit`: the seats below are filled from the
    # semantic arm's own ranking, and `fused[:limit]` does not contain that ranking — a
    # chunk only the vector arm found scores `1/(60+rank)` and sits below every chunk the
    # lexical arm matched too (measured 2026-11-02, D79's slice 1).
    fallback = search(
        " OR ".join(cleaned),
        standard_set=standard_set,
        limit=candidates,
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
    # The seats belong to the semantic arm, so its **own** order fills them. Filling them
    # in fused order let the lexical arm choose which semantic chunks got in, which is the
    # thing the reservation exists to prevent: on "what is the yearly cost of membership"
    # the OPP's fee band is the vector arm's 4th chunk and appears in no lexical ranking,
    # so it could not take a seat however well it ranked. A heading is not what a seat is
    # for (`is_heading_only`), so it does not consume one — the OPP's part heading takes
    # vector rank 1 for any fee question by naming every fee the document charges.
    semantic_added = 0
    for candidate in sorted(
        (chunk for chunk in fallback.chunks if chunk.vector_rank is not None),
        key=lambda chunk: chunk.vector_rank,
    ):
        if candidate.chunk_id in seen or is_heading_only(candidate):
            continue
        seen.add(candidate.chunk_id)
        merged.append(candidate)
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

    # The alias arm: a question word the corpus answers under another name. `cost` vs the
    # OPP's "Membership Fees" is the measured case (`knowledge/aliases.py`, G3). It runs
    # after the question's own words have been ranked, and it displaces the tail — the
    # visitor's vocabulary keeps its seats and the alias can only take what they did not
    # fill. One word, rarest first, for the same reason the primary arm is one word.
    alias_terms = [
        alias for term in cleaned for alias in ALIASES.get(term, ()) if alias not in cleaned
    ]
    if alias_terms:
        alias_frequency = {
            term: document_frequency(term, standard_set=standard_set)
            for term in alias_terms
        }
        alias_key = lexical_key(alias_terms, alias_frequency)
        if alias_key:
            aliased = search(
                alias_key,
                standard_set=standard_set,
                limit=ALIAS_SEATS,
                candidates=candidates,
                provider=provider,
                use_vector=False,
            )
            incoming = [
                chunk for chunk in aliased.chunks if chunk.chunk_id not in seen
            ][:ALIAS_SEATS]
            if incoming:
                merged = merged[: max(0, limit - len(incoming))] + incoming
                seen = {chunk.chunk_id for chunk in merged}
            warnings = tuple(dict.fromkeys((*warnings, *aliased.warnings)))

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

    merged = _with_their_tables(merged, standard_set=standard_set)

    return RetrievalResult(
        query=question or " OR ".join(cleaned),
        standard_set_id=getattr(standard_set, "pk", None),
        chunks=tuple(merged),
        lexical_only=primary.lexical_only and fallback.lexical_only,
        warnings=warnings,
        key=key,
    )


def _with_their_tables(
    chunks: list[RetrievedChunk], *, standard_set: StandardSet
) -> list[RetrievedChunk]:
    """Give each reviewed table's rows to a set that found one of its passages (D79/E).

    In:  the merged passages; the corpus boundary. Out: the same passages, in the same
         order, each carrying its `TableContext` when it belongs to a reviewed table, plus
         that table's rows appended **after** them, up to `TABLE_ROW_SEATS` in total.
    Fails: never. A document with no artefact, an unreadable one, or a row whose text does
         not match the artefact adds nothing and removes nothing.

    Why the rows are appended rather than given seats: the passages a question already
    retrieved keep their positions and their ranks, so a table arrives without displacing
    the evidence that found it — and the budget this module documents (`limit`) stays a
    budget for *retrieval*, which is what `eval_retrieval` measures.

    Why it is needed at all, measured on 2026-11-02: the OPP's six fee bands are within
    0.023 of each other in the vector arm, so their order is noise and a question's
    punctuation decides whether one is seated (slice 1). The table's introduction, which
    *is* retrieved reliably, names none of the numbers — so the rows have to come with it.
    """
    if not chunks:
        return chunks

    contexts: dict[int, TableContext] = {}
    additions: list[RetrievedChunk] = []
    seen = {chunk.chunk_id for chunk in chunks}
    seats = TABLE_ROW_SEATS
    for chunk in chunks:
        if seats <= 0:
            break
        table = reviewed_table_for_section(
            chunk.document_source_file, chunk.section_ref, chunk.heading_path
        )
        if table is None:
            continue
        rows = row_chunks_for(
            table, standard_set=standard_set, source_file=chunk.document_source_file
        )
        for row in rows:
            context = table.context_for(row.text)
            if row.pk in seen:
                contexts[row.pk] = context
                continue
            if seats <= 0:
                break
            seen.add(row.pk)
            contexts[row.pk] = context
            additions.append(
                replace(
                    _retrieved_from_row(
                        row,
                        score=0.0,
                        lexical_rank=None,
                        vector_rank=None,
                    ),
                    table=context,
                )
            )
            seats -= 1

    if not contexts:
        return chunks
    labelled = [
        replace(chunk, table=contexts[chunk.chunk_id])
        if chunk.chunk_id in contexts
        else chunk
        for chunk in chunks
    ]
    return labelled + additions
