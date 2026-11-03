"""Task B7 — hybrid retrieval, fused and scoped.

SPEC §4.5 and the plan fix four properties, and each has a test that would fail if it
were merely *intended*:

1. **The corpus boundary is a filter, not a rule.** Retrieval is scoped to the
   session's `StandardSet` **before ranking**, so a chatbot answering about SAOSO cannot
   cite the OPP even when the OPP is a *better* vector match. That is asserted with a
   deliberately closer out-of-set chunk.
2. **Fusion is Reciprocal Rank Fusion** with `k=60` — ranks, not scores, because a
   `ts_rank_cd` value and a cosine distance are not comparable. The unit test asserts
   the arithmetic, so a future "improvement" to score addition fails here.
3. **The lexical arm works with no Gemini key.** Embeddings are an enhancement; a
   corpus is useful without them, and the result says `lexical_only=True` rather than
   pretending hybrid happened.
4. **An empty corpus returns nothing, not an exception.** The chatbot's refusal path
   depends on it.

The recall-floor test ingests the **real** SAOSO PDF and asks a real question about
traceability. Its assertion is deliberately structural (`S20.` and not `B.20.`, D43)
rather than a hard-coded chunk id, so re-chunking cannot make it pass for the wrong
reason.

`knowledge/tests/test_retrieval_strategy.py` holds the other half: `search_terms`, the
lexical key, the seats and the rare-term bet. This file is the search and the fusion that
`search_terms` chose the query for.
"""

from __future__ import annotations

import pytest

from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.retrieval import search_terms
from knowledge.services import (
    DEFAULT_LIMIT,
    chunks_by_id,
    FUSED_CANDIDATES,
    RRF_K,
    Retained,
    RetrievalResult,
    fuse,
    search,
    vector_search,
)
from knowledge.tests.retrieval_fixtures import (  # noqa: F401 - pytest discovers fixtures by name
    FakeProvider,
    make_chunk,
    no_live_embeddings,
    saoso_ingested,
    saoso_set,
    two_sets,
    vec,
)

pytestmark = pytest.mark.django_db


# --- 1. The corpus boundary is a filter -------------------------------------


def test_results_never_come_from_outside_the_set(two_sets):
    first, second, in_set, out_of_set = two_sets
    result = search("alpha traceability", standard_set=first)
    assert [chunk.chunk_id for chunk in result.chunks] == [in_set.pk]
    assert out_of_set.pk not in [chunk.chunk_id for chunk in result.chunks]


def test_the_scope_is_applied_before_ranking_not_after(two_sets):
    """An out-of-set chunk with the *closest possible* vector must still not appear.

    If scoping happened after ranking, this is the test that fails: the foreign chunk
    would be ranked first and then filtered, leaving fewer results than the limit even
    though in-scope chunks existed.
    """
    first, second, in_set, out_of_set = two_sets
    DocumentChunk.objects.filter(pk=out_of_set.pk).update(embedding=vec(1.0))
    DocumentChunk.objects.filter(pk=in_set.pk).update(embedding=vec(0.9, 0.1))

    ranked = vector_search(vec(1.0), standard_set=first, limit=10)
    assert [chunk_id for chunk_id, _ in ranked] == [in_set.pk]
    assert out_of_set.pk not in [chunk_id for chunk_id, _ in ranked]


def test_the_fused_path_is_scoped_end_to_end(two_sets):
    """Both arms live, and the out-of-set chunk is the better vector match.

    This is the plan's rule in full: scope is a filter applied *before* ranking, so a
    foreign chunk can never win a place and then be filtered out of the top N. The
    provider makes the query's vector match the out-of-set chunk more closely, so if
    scoping slipped to after fusion the assertion below fails on content, not on count.
    """
    first, second, in_set, out_of_set = two_sets
    DocumentChunk.objects.filter(pk=in_set.pk).update(embedding=vec(0.2, 0.9))
    DocumentChunk.objects.filter(pk=out_of_set.pk).update(embedding=vec(0.9, 0.2))

    result = search("alpha traceability", standard_set=first, provider=FakeProvider())

    assert result.lexical_only is False, "the vector arm did not run, so this proves nothing"
    assert result.chunks
    assert {chunk.document_title for chunk in result.chunks} == {"Alpha standard"}


def test_a_second_set_answers_from_its_own_corpus(two_sets):
    first, second, in_set, out_of_set = two_sets
    result = search("alpha traceability", standard_set=second)
    assert [chunk.chunk_id for chunk in result.chunks] == [out_of_set.pk]


def test_an_empty_corpus_returns_nothing_rather_than_raising(db):
    empty = StandardSet.objects.create(code="empty", label="Empty", is_default=True)
    result = search("anything at all", standard_set=empty)
    assert isinstance(result, RetrievalResult)
    assert result.chunks == ()


def test_a_blank_query_is_not_run(db):
    """A blank query would match the whole corpus and rank it arbitrarily."""
    empty = StandardSet.objects.create(code="blank", label="Blank", is_default=True)
    result = search("   ", standard_set=empty)
    assert result.chunks == ()
    assert any("empty" in warning.lower() for warning in result.warnings)


# --- 2. RRF arithmetic -------------------------------------------------------


def test_rrf_uses_rank_not_score():
    """The unit test for the fusion rule, isolated from any database.

    Scores are `1/(60+rank)` summed over the arms a chunk appears in. Note what this
    example demonstrates: chunk 8 (2nd in both) beats chunk 3 (1st in one arm only),
    which is RRF working as designed — consistency across arms is worth more than a
    single strong showing. The plan's wording ("neither lexical nor semantic recall
    dominates") is exactly this property.
    """
    rankings = [
        [7, 8, 9],             # lexical
        [3, 7, 8],             # vector
    ]
    fused = fuse(rankings, k=60)
    scores = dict(fused)
    assert scores[7] == pytest.approx(1 / 61 + 1 / 62)   # 1st, then 2nd
    assert scores[8] == pytest.approx(1 / 62 + 1 / 63)   # 2nd in both
    assert scores[3] == pytest.approx(1 / 61)            # one arm only
    assert scores[9] == pytest.approx(1 / 63)
    assert [item for item, _ in fused] == [7, 8, 3, 9]


def test_rrf_k_is_the_documented_sixty():
    assert RRF_K == 60
    assert FUSED_CANDIDATES == 20
    assert DEFAULT_LIMIT == 5


def test_fusion_is_deterministic_for_ties():
    """Two runs of the same query must not reorder the answer."""
    fused_once = fuse([[7, 8, 9], [9, 8, 7]], k=60)
    fused_twice = fuse([[7, 8, 9], [9, 8, 7]], k=60)
    assert fused_once == fused_twice
    # 7 and 9 are exactly tied (1st+3rd and 3rd+1st), so the id breaks it; 8 is
    # marginally behind both, because 1st+3rd beats 2nd+2nd under RRF.
    assert [item for item, _ in fused_once] == [7, 9, 8]
    assert dict(fused_once)[7] == pytest.approx(dict(fused_once)[9])


def test_fuse_ignores_duplicate_items_within_one_ranking():
    """An arm lists a chunk once; a bug that listed it twice must not double its score."""
    fused = dict(fuse([[5, 5, 6]], k=60))
    assert fused[5] == pytest.approx(1 / 61)


def test_retained_is_a_plain_pair():
    assert Retained(chunk_id=3, lexical_rank=1, vector_rank=None).chunk_id == 3


# --- 3. The lexical arm without a key ---------------------------------------


def test_lexical_only_when_there_is_no_key(saoso_ingested, saoso_set, settings):
    settings.GEMINI_API_KEY = ""
    result = search("traceability", standard_set=saoso_set)
    assert result.chunks, "the lexical arm returned nothing"
    assert result.lexical_only is True
    assert any("GEMINI_API_KEY" in warning for warning in result.warnings)


def test_a_key_with_no_stored_vectors_still_works_lexically(saoso_ingested, saoso_set, settings):
    """The corpus was ingested with `--no-embed`, so the vector arm has nothing to do."""
    settings.GEMINI_API_KEY = "pretend-key"
    result = search("traceability", standard_set=saoso_set)
    assert result.chunks
    assert result.lexical_only is True


# --- The recall floor, on the real document ---------------------------------


def test_a_traceability_question_returns_a_saoso_clause(saoso_ingested, saoso_set):
    result = search(
        "traceability of organic processing and handling", standard_set=saoso_set
    )
    assert result.chunks
    refs = [chunk.section_ref for chunk in result.chunks if chunk.section_ref]
    assert any(ref.startswith("S20.") for ref in refs), refs
    assert not [ref for ref in refs if ref.startswith("B.20")], "D43: never B.20"


def test_a_natural_question_reaches_the_traceability_clause(saoso_ingested, saoso_set):
    """A chatbot question, not a phrase from the document.

    `websearch_to_tsquery` ANDs the words, so the raw question retrieves nothing (see
    `testing_hazards.md` §2.4). `search_terms` searches the rarest word first, which is
    what puts the actual clause back in front of the model.
    """
    result = search_terms(
        ["standard", "require", "traceability"], standard_set=saoso_set
    )
    refs = [chunk.section_ref for chunk in result.chunks if chunk.section_ref]
    assert any(ref.startswith("S20.1") for ref in refs), refs


def test_a_labelling_question_reaches_section_22(saoso_ingested, saoso_set):
    result = search("labelling of organic products", standard_set=saoso_set)
    refs = [chunk.section_ref for chunk in result.chunks if chunk.section_ref]
    assert any(ref.startswith("S22") for ref in refs), refs


def test_the_lexical_arm_is_ordered_by_relevance(saoso_ingested, saoso_set):
    """The glossary of §1 must not outrank a clause that is entirely about the term."""
    result = search("traceability", standard_set=saoso_set)
    assert result.chunks
    first = result.chunks[0]
    assert "traceab" in first.text.lower()


def test_odd_user_input_does_not_raise(saoso_ingested, saoso_set):
    """`websearch_to_tsquery` is chosen precisely because it tolerates raw user input.

    Quoted phrases, a `-` exclusion and stray operators are all things people type; the
    parser must not raise on any of them, or the chatbot 500s on a real question.
    """
    quoted = search('"organic processing"', standard_set=saoso_set)
    excluded = search("traceability -GMO", standard_set=saoso_set)
    stray = search("organic & OR (weird", standard_set=saoso_set)
    for result in (quoted, excluded, stray):
        assert isinstance(result, RetrievalResult)


def test_limit_and_candidates_are_respected(saoso_ingested, saoso_set):
    result = search("organic", standard_set=saoso_set, limit=3)
    assert len(result.chunks) <= 3
    assert len(search("organic", standard_set=saoso_set, limit=1).chunks) == 1


# --- Citations ---------------------------------------------------------------


def test_a_result_can_be_rendered_as_a_citation(saoso_ingested, saoso_set):
    result = search("traceability of organic processing", standard_set=saoso_set)
    citation = result.chunks[0].as_citation()
    assert citation["section_ref"]
    assert citation["quote"]
    assert citation["page"] == result.chunks[0].page
    assert citation["document"].startswith("SAOSO Standard")


def test_the_text_is_returned_unchanged_from_the_chunk(saoso_ingested, saoso_set):
    """Citations quote the stored chunk; nothing is re-extracted for display."""
    result = search("traceability", standard_set=saoso_set)
    for chunk in result.chunks:
        stored = DocumentChunk.objects.get(pk=chunk.chunk_id)
        assert chunk.text == stored.text


# --- The vector arm, with hand-built vectors ---------------------------------


def test_vector_search_orders_by_cosine_distance(two_sets):
    first, second, in_set, out_of_set = two_sets
    DocumentChunk.objects.filter(pk=in_set.pk).update(embedding=vec(1.0, 0.0))
    DocumentChunk.objects.filter(pk=out_of_set.pk).update(embedding=vec(0.0, 1.0))
    ranked = vector_search(vec(1.0, 0.0), standard_set=first, limit=5)
    assert ranked[0][0] == in_set.pk
    assert ranked[0][1] < (ranked[1][1] if len(ranked) > 1 else float("inf"))


def test_vector_search_skips_chunks_without_vectors(two_sets):
    first, second, in_set, out_of_set = two_sets
    DocumentChunk.objects.filter(pk=in_set.pk).update(embedding=vec(1.0))
    ranked = vector_search(vec(1.0), standard_set=first, limit=5)
    assert [chunk_id for chunk_id, _ in ranked] == [in_set.pk]


# --- Stage 1 of the follow-up decision: the context arm ---------------------
#
# Two mechanisms, for two different failures, and both are tested here or in
# `core/tests/test_follow_up.py`:
#
#   * The **context arm** below. The parent's *words* reach the clause the fragment
#     missed. "what if I compost it first?" loses "manure"; the parent question has it.
#   * The **carried citation** (`chunks_by_id`). The parent's words are *not* in the
#     clause either — the standard never says "cardboard" — so the only thing that can
#     put that row back is the passage the previous answer was allowed to cite.


@pytest.fixture
def follow_up_corpus(db):
    """A corpus where the fragment alone cannot reach the clause the parent found.

    `compost` occurs in both distractor chunks and nowhere in the substance row; the
    fragment is searched as `compost` alone, so the row that governs it is not returned.
    The parent question says `manure`, which the row does contain — which is exactly the
    case the arm exists for.
    """
    corpus = StandardSet.objects.create(code="follow-up", label="Follow-up", is_default=True)
    document = StandardDocument.objects.create(
        standard_set=corpus, kind="STANDARD", issuing_body="SAOSO",
        title="SAOSO Standard", version="2.1", source_file="saoso.pdf",
        sha256="3" * 64, section_scheme="saoso",
    )
    distractor_a = make_chunk(document, ref="S4", text="Compost compost compost.", page=34)
    distractor_b = make_chunk(
        document, ref="S23", text="Compost and social justice.", page=67
    )
    manure = make_chunk(
        document,
        ref="Appendix 2",
        text=(
            "Farmyard manure, slurry and urine — shall not constitute the main source of "
            "nitrogen in the absence of complimentary and additional nitrogen generating "
            "practices on farm and shall not be from conventional intensive livestock "
            "production systems without prior permission from the control body"
        ),
        page=76,
    )
    return corpus, manure, (distractor_a, distractor_b)


def test_the_context_arm_finds_the_clause_the_fragment_lost(follow_up_corpus):
    corpus, manure, _ = follow_up_corpus
    fragment = search_terms(["compost"], standard_set=corpus, question="compost", limit=1)
    assert manure.pk not in [chunk.chunk_id for chunk in fragment.chunks]

    carried = search_terms(
        ["compost"],
        standard_set=corpus,
        question="what if I compost it first?",
        limit=8,
        context_query="horse OR manure",
    )

    assert manure.pk in [chunk.chunk_id for chunk in carried.chunks]


def test_the_context_arm_never_exceeds_the_budget(follow_up_corpus):
    corpus = follow_up_corpus[0]
    result = search_terms(
        ["compost"],
        standard_set=corpus,
        question="what if I compost it first?",
        limit=4,
        context_query="horse OR manure",
    )
    assert len(result.chunks) <= 4


def test_no_context_query_changes_nothing(follow_up_corpus):
    """A new question must retrieve exactly what it retrieved before stage 1."""
    corpus = follow_up_corpus[0]
    plain = search_terms(["compost"], standard_set=corpus, question="compost", limit=4)
    blank = search_terms(
        ["compost"], standard_set=corpus, question="compost", limit=4, context_query=""
    )
    assert [c.chunk_id for c in plain.chunks] == [c.chunk_id for c in blank.chunks]


# --- Carrying a parent's cited passages -------------------------------------


def test_carrying_a_citation_is_scoped_to_the_set(follow_up_corpus):
    corpus, manure, _ = follow_up_corpus
    other = StandardSet.objects.create(code="other-set", label="Other")
    other_document = StandardDocument.objects.create(
        standard_set=other, kind="SOP", issuing_body="Other", title="Other procedures",
        version="1", source_file="other.pdf", sha256="4" * 64, section_scheme="opp",
    )
    foreign = make_chunk(
        other_document, ref="§4.2", text="Farmyard manure, slurry and urine"
    )

    carried = chunks_by_id([manure.pk, foreign.pk], standard_set=corpus)

    assert [chunk.chunk_id for chunk in carried] == [manure.pk], (
        "a carried passage from another corpus must be dropped, not trusted"
    )


def test_carrying_returns_the_passages_in_the_order_asked_for(follow_up_corpus):
    corpus, manure, distractors = follow_up_corpus
    ordered = [distractors[1].pk, manure.pk]
    carried = chunks_by_id(ordered, standard_set=corpus)
    assert [chunk.chunk_id for chunk in carried] == ordered


def test_carrying_a_missing_id_returns_nothing_for_it(follow_up_corpus):
    corpus, manure, _ = follow_up_corpus
    carried = chunks_by_id([manure.pk, 999999], standard_set=corpus)
    assert [chunk.chunk_id for chunk in carried] == [manure.pk]

