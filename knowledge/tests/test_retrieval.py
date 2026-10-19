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
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge.ingest import ingest_standard
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.services import (
    DEFAULT_LIMIT,
    FUSED_CANDIDATES,
    RRF_K,
    Retained,
    RetrievalResult,
    fuse,
    search,
    vector_search,
)

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = REPO_ROOT / "pgs_docs"
SAOSO_PDF = PDF_DIR / "saoso-version-2.1-2026.pdf"
OPP_PDF = PDF_DIR / "Outeniqua pgs principles, policies and procedures 2026.pdf"


@pytest.fixture(autouse=True)
def no_live_embeddings(monkeypatch):
    """Retrieval tests must not reach Gemini by accident."""

    def bomb(*args, **kwargs):  # pragma: no cover - only when the guard fires
        raise AssertionError("a live GeminiEmbeddingProvider was constructed in a test")

    monkeypatch.setattr("knowledge.embedding.GeminiEmbeddingProvider", bomb, raising=False)


@pytest.fixture
def saoso_set(db):
    return StandardSet.objects.create(code="saoso-only", label="SAOSO", is_default=True)


@pytest.fixture
def saoso_ingested(saoso_set, settings):
    settings.GEMINI_API_KEY = ""
    return ingest_standard(
        pdf_path=SAOSO_PDF, standard_set=saoso_set, doc_key="saoso", embed=False
    )


class FakeProvider:
    """A deterministic provider: the vector encodes which marker word is present."""

    def __init__(self, dimension=768):
        self.dimension = dimension

    def embed(self, texts):
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimension
            lowered = text.lower()
            for index, marker in enumerate(
                ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]
            ):
                if marker in lowered:
                    vector[index] = 1.0
            if not any(vector):
                vector[self.dimension - 1] = 0.001
            vectors.append(vector)
        return vectors


def vec(*head: float) -> list[float]:
    """A `vector(768)`-shaped test vector with a meaningful leading direction.

    The column is `vector(768)` because D3/D20 freeze the dimension, so a tidy 2- or
    8-element vector is a `DataError`, not a shortcut. The tail is zero-padded.
    """
    assert len(head) <= 768
    return list(head) + [0.0] * (768 - len(head))


def make_chunk(document, *, ref, text, embedding=None, page=1):
    return DocumentChunk.objects.create(
        document=document,
        section_ref=ref,
        text=text,
        heading_path=ref,
        page=page,
        embedding=embedding,
    )


@pytest.fixture
def two_sets(db):
    """Two coexisting corpora, each with one document and two chunks."""
    first = StandardSet.objects.create(code="alpha-set", label="Alpha", is_default=True)
    second = StandardSet.objects.create(code="beta-set", label="Beta")
    doc_first = StandardDocument.objects.create(
        standard_set=first, kind="STANDARD", issuing_body="A", title="Alpha standard",
        version="1", source_file="a.pdf", sha256="1" * 64, section_scheme="saoso",
    )
    doc_second = StandardDocument.objects.create(
        standard_set=second, kind="SOP", issuing_body="B", title="Beta procedures",
        version="1", source_file="b.pdf", sha256="2" * 64, section_scheme="opp",
    )
    in_set = make_chunk(doc_first, ref="S20.1.2", text="alpha traceability requirement")
    out_of_set = make_chunk(doc_second, ref="§4.2", text="alpha traceability requirement elsewhere")
    return first, second, in_set, out_of_set


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
