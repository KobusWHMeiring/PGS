"""A document as a reader sees it — the model behind `/documents/<code>/read/`.

The fixture builds chunks directly instead of ingesting a PDF: this module tests ordering,
anchors and search, and none of those depend on extraction. The corpus and the reader are
joined by one integration test in `core/tests/test_document_reader.py`, which drives the real
route against a real `StandardDocument`.
"""

from __future__ import annotations

import pytest

from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.reading import (
    SearchHit,
    reader_anchor_map,
    reading_anchor,
    reading_chunks,
    search_in_document,
    unique_anchors,
)

pytestmark = pytest.mark.django_db

CHUNKS = [
    (
        "Appendix 2",
        "",
        "APPENDICES > Appendix 2",
        76,
        "Biodegradable processing by-products, plant or animal origin. Condition: free of "
        "significant contaminants; or composted before bringing onto organic land.",
    ),
    ("Appendix 2.1", "", "APPENDICES > Appendix 2", 77,
     "Wood, bark and sawdust, only if not chemically treated."),
    (
        None,
        "straw-mulch",
        "APPENDICES > Appendix 3",
        80,
        "Straw is listed with crop residues and plant materials, with no condition attached.",
    ),
]


@pytest.fixture
def document(db) -> StandardDocument:
    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    doc = StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.1",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="0" * 64,
        section_scheme="saoso",
    )
    for section_ref, anchor, heading_path, page, text in CHUNKS:
        DocumentChunk.objects.create(
            document=doc,
            section_ref=section_ref,
            anchor=anchor,
            heading_path=heading_path,
            page=page,
            text=text,
        )
    doc.chunk_count = len(CHUNKS)
    doc.save(update_fields=["chunk_count"])
    return doc


def test_anchors_are_stable_unique_and_url_safe(document):
    anchors = [anchor for _chunk, anchor in unique_anchors(reading_chunks(document))]
    assert anchors == ["appendix-2", "appendix-2-1", "straw-mulch"]
    assert len(anchors) == len(set(anchors)), "two chunks share an anchor"
    assert all(anchor == anchor.lower() for anchor in anchors)


def test_a_repeated_reference_keeps_the_plain_anchor_first(document):
    """A section reference is a citation's target, so the first passage keeps the name.

    Duplicate `section_ref`s are held at zero by the ingest ratchet, but a heading-scheme
    document can repeat a heading across pages, and a citation must still land on the first
    occurrence rather than on a suffixed one nobody can guess. Later passages are named for
    their own words, not for their position (`CONCORDANCE_PRD` §10.7).
    """
    chunk = document.chunks.get(anchor="straw-mulch")
    chunk.section_ref = None
    chunk.anchor = ""
    chunk.heading_path = "APPENDICES > Appendix 2"
    chunk.save(update_fields=["section_ref", "anchor", "heading_path"])

    anchors = [anchor for _chunk, anchor in unique_anchors(reading_chunks(document))]
    assert anchors[:2] == ["appendix-2", "appendix-2-1"]
    assert anchors[2] == "appendix-2-straw-is-listed"
    assert reading_anchor(None, "", "APPENDICES > Appendix 2") == "appendix-2"


def test_the_reader_anchor_map_is_what_the_reader_renders(document):
    """The map a citation uses and the ids the page renders come from one computation."""
    assert reader_anchor_map(document) == {
        chunk.pk: anchor
        for chunk, anchor in unique_anchors(reading_chunks(document))
    }


def test_reading_chunks_are_in_document_order(document):
    chunks = reading_chunks(document)
    assert [chunk.pk for chunk in chunks] == sorted(chunk.pk for chunk in chunks)
    assert len(chunks) == document.chunk_count


def test_search_finds_a_stored_clause(document):
    hits = search_in_document(document, "contaminants")
    assert hits, "the FTS config and the generated column disagree, or nothing was indexed"
    hit = hits[0]
    assert isinstance(hit, SearchHit)
    assert "contaminants" in hit.hit.lower()
    assert hit.anchor == "appendix-2"
    assert hit.before + hit.hit + hit.after, "an empty snippet is not a result"


def test_search_falls_back_to_any_of_the_words(document):
    """`websearch_to_tsquery` ANDs its terms into zero rows (testing_hazards.md §2.4).

    The box is a search box, not a query language: a two-word query must find the passage
    that has one of the words rather than render "no matches" for a query a person typed.
    Neither word alone is a phrase in the corpus, so the AND pass finds nothing and the OR
    pass has to run for this to pass.
    """
    from django.contrib.postgres.search import SearchQuery

    from knowledge.services import SEARCH_CONFIG

    assert not document.chunks.filter(
        search_vector=SearchQuery(
            "cardboard sawdust", config=SEARCH_CONFIG, search_type="websearch"
        )
    ).exists(), "the AND pass found a row, so this test would not prove the fallback ran"
    assert search_in_document(document, "cardboard sawdust")
    assert search_in_document(document, "cardboard sawdust")[0].anchor == "appendix-2-1"


def test_an_empty_query_searches_nothing(document):
    """Guarded explicitly: an empty query that matched everything would render the whole
    document as a result, and the page would look broken while passing `!= []`."""
    assert search_in_document(document, "   ") == []


def test_a_search_hit_carries_the_anchor_that_names_its_own_passage(document):
    """The hit list links to the passage it quotes. Before 2026-10-27 every hit on a shared
    reference linked to the group's first passage (`CONCORDANCE_PRD` §10.7)."""
    document.chunks.all().delete()
    DocumentChunk.objects.create(
        document=document, section_ref="Appendix 2", page=76, text="Farmyard manure, slurry and urine"
    )
    DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2",
        page=77,
        text="Wood, bark and sawdust, only if not chemically treated.",
    )

    hits = search_in_document(document, "sawdust")

    assert [hit.anchor for hit in hits] == ["appendix-2-wood-bark-and-sawdust"]


# --- Chunk overlap is a retrieval feature, not something to read twice ------


def test_the_reader_strips_the_overlap_the_chunker_added():
    """Retrieval wants a shared tail on both chunks; a reader does not.

    `S1` is eight chunks and five of the boundaries repeat 21–57 words, so the definitions
    rendered as a page where every chunk began with the previous chunk's last paragraph.
    """
    from knowledge.reading import strip_overlap

    previous = "one two three four five six seven eight alpha beta"
    current = "four five six seven eight alpha beta kappa lambda"

    assert strip_overlap(previous, current) == "kappa lambda"


def test_a_short_coincidence_is_not_stripped():
    """Two clauses may both say `must be kept`; six words of agreement is the floor."""
    from knowledge.reading import strip_overlap

    assert strip_overlap("records must be kept", "must be kept for five years") == (
        "must be kept for five years"
    )


def test_no_previous_passage_leaves_the_text_alone():
    from knowledge.reading import strip_overlap

    assert strip_overlap(None, "a  One;") == "a  One;"
    assert strip_overlap("a  One;", "b  Two;") == "b  Two;"
