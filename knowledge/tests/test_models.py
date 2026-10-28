"""Task B1 — the corpus schema (spec §4.5).

These tests are written against the **invariants the corpus cannot survive without**,
not against the field list. The field list is in `knowledge/models.py`; what is
asserted here is what breaks silently if it is wrong:

1. **A chunk with no section reference is not a citation.** SPEC §4.5: "a chunk the
   user cannot locate in the standard is not a citation". `blank=False` does not
   enforce this (testing_hazards.md §1.7 — Postgres happily stores `""`), so this is
   asserted as an `IntegrityError`, i.e. a real database constraint.
2. **`sub_refs` offsets point inside `text`.** They exist so a citation can slice
   the clause it needs without splitting the chunk (D15). An out-of-range offset is
   a citation that renders half a sentence or an `IndexError` in production.
3. **The generated `search_vector` tracks `text`.** If it does not, retrieval silently
   returns stale or empty results forever, and only a test that *changes* the text can
   see it. (Hazard #3 in HANDOVER §6: `GeneratedField(SearchVector(...))` is the thing
   to prove, not assume.)
4. **The embedding dimension is frozen.** D3/D20: changing it later requires
   re-embedding the whole corpus. The dimension is therefore asserted at the
   database level, where a mismatch is a `DataError` rather than a cosine-similarity
   computation between two different spaces.
5. **`sha256` is the idempotency key for re-ingestion** (B6), and **one standard set
   is the default**, because retrieval scoped to "the default set" must be
   unambiguous.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, transaction
from django.db.models import ProtectedError

from knowledge.models import DocumentChunk, StandardDocument, StandardSet

pytestmark = pytest.mark.django_db


# --- Helpers -----------------------------------------------------------------
# `MVP0_PLAN_V2.md` §2 lists no `knowledge/tests/factories.py`, so these are plain
# builders rather than `factory_boy` factories. They are local on purpose: the
# corpus is a library with three models, and a shared factory package would be the
# start of a fixture layer nobody asked for.


def make_set(**kwargs) -> StandardSet:
    data = {"code": "outeniqua", "label": "Outeniqua PGS corpus"}
    data.update(kwargs)
    return StandardSet.objects.create(**data)


def make_document(standard_set: StandardSet | None = None, **kwargs) -> StandardDocument:
    data = {
        "standard_set": standard_set or make_set(),
        "kind": StandardDocument.Kind.STANDARD,
        "issuing_body": "SAOSO",
        "title": "SAOSO Standard v2.1 2026",
        "version": "2.1",
        "source_file": "pgs_docs/saoso.pdf",
        "sha256": "a" * 64,
        "section_scheme": "saoso",
    }
    data.update(kwargs)
    return StandardDocument.objects.create(**data)


def make_chunk(document: StandardDocument | None = None, **kwargs) -> DocumentChunk:
    data = {
        "document": document or make_document(),
        "section_ref": "S20.1.1",
        "heading_path": "SECTION B > 20 Processing and handling > 20.1 General",
        "page": 60,
        "text": "Traceability of organic produce must be maintained at all times.",
    }
    data.update(kwargs)
    return DocumentChunk.objects.create(**data)


# --- 1. A citation must be locatable -----------------------------------------


def test_chunk_with_empty_section_ref_cannot_be_saved():
    """`""` is not a citation, and the database must refuse it.

    This is the exact failure that invalidated MVP 0 v1: chunks were produced with
    no reference at all and every test still passed. `blank=False` alone would let
    this through — see testing_hazards.md §1.7.
    """
    doc = make_document()
    with pytest.raises(IntegrityError), transaction.atomic():
        DocumentChunk.objects.create(
            document=doc,
            section_ref="",
            heading_path="x",
            text="A chunk that cannot be located on paper.",
        )


def test_heading_only_documents_may_have_no_section_ref():
    """LANDSCAPE and BPP have no clause numbering (SPEC §4.5 reality table).

    Their locator is `page` + `heading_path`, so `section_ref` is NULL — not `""`.
    The constraint forbids the empty string specifically, because `""` is what a
    parser emits when it *thinks* it found a reference and did not; NULL is a
    document that never had one. B2 decides whether the heading parser emits NULL
    or an anchor-as-ref; both are permitted here, and only `""` is not.
    """
    chunk = make_chunk(
        document=make_document(
            kind=StandardDocument.Kind.LANDSCAPE,
            title="Certification landscape",
            section_scheme="heading",
            sha256="b" * 64,
        ),
        section_ref=None,
        page=12,
        heading_path="The South African certification landscape",
    )
    chunk.refresh_from_db()
    assert chunk.section_ref is None
    assert chunk.page == 12


# --- 2. sub_refs offsets point inside text -----------------------------------


def test_sub_refs_inside_text_are_accepted():
    text = "The assessment must be concluded within 5 days of the visit."
    start = text.index("within 5 days")
    chunk = make_chunk(
        text=text,
        sub_refs=[{"ref": "4.2(5)", "start": start, "end": start + len("within 5 days")}],
    )
    chunk.full_clean()
    chunk.save()
    assert chunk.sub_refs[0]["ref"] == "4.2(5)"
    assert text[chunk.sub_refs[0]["start"] : chunk.sub_refs[0]["end"]] == "within 5 days"


@pytest.mark.parametrize(
    "sub_ref",
    [
        {"ref": "4.2(5)", "start": 5, "end": 5},  # empty span
        {"ref": "4.2(5)", "start": 9, "end": 4},  # reversed
        {"ref": "4.2(5)", "start": -1, "end": 4},  # negative
        {"ref": "", "start": 0, "end": 4},  # unnameable
        {"ref": "4.2(5)", "start": 0, "end": 10_000},  # past the end of text
    ],
)
def test_sub_refs_outside_text_are_rejected(sub_ref):
    """`full_clean()` must reject offsets a citation could not slice."""
    chunk = make_chunk(text="short text", sub_refs=[sub_ref])
    with pytest.raises(ValidationError):
        chunk.full_clean()


def test_sub_refs_must_be_the_documented_shape():
    """Only `ref`/`start`/`end` — a typo'd key would silently lose the reference."""
    chunk = make_chunk(text="short text", sub_refs=[{"ref": "4.2(5)", "start": 0, "stop": 4}])
    with pytest.raises(ValidationError):
        chunk.full_clean()


# --- 3. The generated search vector tracks text ------------------------------


def test_search_vector_is_populated_on_insert():
    chunk = make_chunk(text="Traceability of organic produce must be maintained.")
    chunk.refresh_from_db()
    assert "traceab" in chunk.search_vector


def test_search_vector_updates_when_text_changes():
    """A generated column, not a signal — so an `update()` must move it too.

    A `pre_save` signal would pass the insert test above and fail this one, and the
    difference is invisible until retrieval starts returning yesterday's corpus.
    """
    chunk = make_chunk(text="Traceability of organic produce must be maintained.")
    chunk.refresh_from_db()
    assert "quantum" not in chunk.search_vector

    DocumentChunk.objects.filter(pk=chunk.pk).update(text="Quantum entanglement in compost.")
    chunk.refresh_from_db()
    assert "quantum" in chunk.search_vector
    assert "traceab" not in chunk.search_vector


# --- 4. The embedding dimension is frozen ------------------------------------


def test_embedding_dimension_matches_settings():
    """D3/D20: the dimension is frozen in the migration, deliberately.

    Asserted against `settings.EMBEDDING_DIM` so that changing `.env` without a new
    migration is a red test rather than a corpus that needs re-embedding silently.
    """
    field = DocumentChunk._meta.get_field("embedding")
    assert field.dimensions == settings.EMBEDDING_DIM == 768


def test_embedding_of_the_wrong_dimension_is_refused_by_the_database():
    """The DB enforces `vector(768)`; a 3-D vector is a `DataError`, not a bad answer."""
    chunk = make_chunk()
    with pytest.raises(DataError), transaction.atomic():
        DocumentChunk.objects.filter(pk=chunk.pk).update(embedding=[0.1, 0.2, 0.3])


# --- 5. Idempotency and the default set --------------------------------------


def test_sha256_identifies_a_document_within_its_set():
    """B6's idempotency key: the same bytes re-ingested add nothing.

    Scoped to the set, not global, so the same PDF may belong to two coexisting
    corpora (SPEC §4.5) without a second, duplicate corpus of chunks.
    """
    standard_set = make_set()
    make_document(standard_set=standard_set, sha256="c" * 64)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_document(standard_set=standard_set, sha256="c" * 64)

    other = make_set(code="other", label="Another group")
    assert make_document(standard_set=other, sha256="c" * 64).pk


def test_only_one_standard_set_may_be_the_default():
    make_set(code="one", label="One", is_default=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_set(code="two", label="Two", is_default=True)


def test_a_superseded_document_cannot_be_deleted_out_from_under_its_successor():
    """Version chains are history (D3): v2.1 → v2.2 must not leave a dangling link."""
    standard_set = make_set()
    old = make_document(standard_set=standard_set, version="2.1", sha256="d" * 64)
    new = make_document(standard_set=standard_set, version="2.2", sha256="e" * 64)
    old.superseded_by = new
    old.save(update_fields=["superseded_by"])

    with pytest.raises(ProtectedError), transaction.atomic():
        new.delete()


# --- 6. The printed TOC is data (D68) ----------------------------------------


def test_a_document_starts_with_no_stored_toc():
    """The field is additive: every document ingested before today has no TOC, and the
    concordance must fall back to headings rather than fail on a missing key."""
    document = make_document()

    assert document.toc == []
    assert StandardDocument.objects.get(pk=document.pk).toc == []


def test_the_toc_survives_a_round_trip_as_json():
    """JSONB, not a string: the concordance reads entry["label"], and a serialised blob
    would make the page's structure a parsing problem."""
    document = make_document()
    entry = {
        "part": None,
        "kind": "RANGE",
        "label": "10 to 19",
        "title": "Left blank to facilitate future enterprises",
        "printed_page": None,
    }
    document.toc = [entry]
    document.save(update_fields=["toc"])

    assert StandardDocument.objects.get(pk=document.pk).toc == [entry]


# --- 7. Drift is visible from the row, not only from a report (D56, P2.1) ----


def test_a_document_starts_with_no_artefact_digest():
    """Empty means "this corpus was parsed from the PDF", which is a fact the column has
    to be able to state. Null would make it indistinguishable from "unknown", and every
    row written before the column existed holds the same fact."""
    document = make_document()

    assert document.corpus_digest == ""
    assert StandardDocument.objects.get(pk=document.pk).corpus_digest == ""
