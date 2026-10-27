"""The anchor a citation carries must identify the passage it quotes.

Measured 2026-10-27: 57 of 366 passages share their reference (Appendix 2 ×30, `S1` ×8,
`Appendix 1` ×6 …), so a reference alone is not an identifier. The disambiguator is derived from
the passage's own words, never from its index: an index-derived suffix repoints at a different
substance when a row is inserted into the reviewed artefact and the document is re-ingested
(`testing_hazards.md` §0 — a wrong answer that still resolves).
"""

from __future__ import annotations

import pytest

from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.reading import unique_anchors

pytestmark = pytest.mark.django_db


@pytest.fixture
def document(db) -> StandardDocument:
    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    return StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.1",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="0" * 64,
        section_scheme="saoso",
    )


def test_the_first_passage_of_a_group_keeps_the_bare_anchor(document):
    """Backwards compatibility: links shipped on 2026-10-27 carry `#appendix-2` and they must
    keep landing on the passage they land on today."""
    DocumentChunk.objects.create(
        document=document, section_ref="Appendix 2", page=76, text="Farmyard manure, slurry and urine"
    )
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=76, text="Guano")

    anchors = [anchor for _chunk, anchor in unique_anchors(list(document.chunks.order_by("id")))]

    assert anchors[0] == "appendix-2"


def test_a_shared_reference_is_disambiguated_by_the_passage_itself(document):
    DocumentChunk.objects.create(
        document=document, section_ref="Appendix 2", page=76, text="Farmyard manure, slurry and urine"
    )
    DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2",
        page=77,
        text="Wood, bark and sawdust, only if not chemically treated.",
    )

    anchors = [anchor for _chunk, anchor in unique_anchors(list(document.chunks.order_by("id")))]

    assert anchors[1] == "appendix-2-wood-bark-and-sawdust", (
        "an index-derived suffix is not a locator"
    )


def test_the_suffix_does_not_move_when_an_earlier_row_is_inserted(document):
    """The property the numeric suffix cannot have: inserting a passage before an existing one
    must not rename the existing one."""
    DocumentChunk.objects.create(
        document=document, section_ref="Appendix 2", page=76, text="Farmyard manure, slurry and urine"
    )
    wood = DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2",
        page=77,
        text="Wood, bark and sawdust, only if not chemically treated.",
    )
    before = {
        chunk.pk: anchor
        for chunk, anchor in unique_anchors(list(document.chunks.order_by("id")))
    }

    # A row is reviewed into the middle of the appendix: new chunk, lower id is impossible, but
    # a re-ingest rebuilds the whole table, so order it as the artefact now prints it.
    document.chunks.all().delete()
    DocumentChunk.objects.create(
        document=document, section_ref="Appendix 2", page=76, text="Farmyard manure, slurry and urine"
    )
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=76, text="Guano")
    wood_after = DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2",
        page=77,
        text="Wood, bark and sawdust, only if not chemically treated.",
    )
    after = {
        chunk.pk: anchor
        for chunk, anchor in unique_anchors(list(document.chunks.order_by("id")))
    }

    assert after[wood_after.pk] == before[wood.pk] == "appendix-2-wood-bark-and-sawdust"


def test_a_whole_table_of_shared_references_still_resolves_one_to_one(document):
    """Appendix 2 is 30 passages under one reference. The derivation must give 30 anchors, not
    29 duplicates and a suffix nobody can read."""
    DocumentChunk.objects.bulk_create(
        [
            DocumentChunk(
                document=document,
                section_ref="Appendix 2",
                page=76 + index // 10,
                text=f"Substance number {index} from the printed table.",
            )
            for index in range(30)
        ]
    )

    pairs = unique_anchors(list(document.chunks.order_by("id")))
    anchors = [anchor for _chunk, anchor in pairs]

    assert len(set(anchors)) == 30
    assert anchors[0] == "appendix-2"
    assert all(anchor.startswith("appendix-2") for anchor in anchors)


def test_every_passage_of_the_real_corpus_resolves_to_itself():
    """The guard D68 asks for, and the one that would have caught the defect.

    A fixture of three chunks with one duplicate passes while 57 real passages are wrong
    (`testing_hazards.md` §1.33). This walks the ingested corpus: for every passage, the anchor
    a citation would carry must resolve to that passage and to no other.

    Skips (loudly) when no corpus is ingested — run it on a machine with the corpus:
        python manage.py ingest_standard --doc saoso --file 'pgs_docs/saoso-version-2.1-2026.pdf'
    """
    from knowledge.concordance import build_concordance

    documents = list(StandardDocument.objects.all())
    if not documents:
        pytest.skip("no corpus ingested on this instance — this guard needs the real corpus")

    #: anchor → the passages that anchor names. Exactly one is the only correct answer.
    resolved: dict[str, set[int]] = {}
    for item in documents:
        for section in build_concordance(item).sections:
            for chunk, anchor in section.passages:
                resolved.setdefault(anchor, set()).add(chunk.pk)

    ambiguous = {anchor: pks for anchor, pks in resolved.items() if len(pks) > 1}

    assert ambiguous == {}, (
        f"{len(ambiguous)} anchors name more than one passage: {list(ambiguous)[:5]}"
    )
