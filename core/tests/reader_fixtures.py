"""The join every reader test depends on, built once.

`seeded_documents` publishes a `PublicDocument` and ingests a `StandardDocument` from the
same `source_path`/`source_file`, because that equality **is** the join the reader makes: a
fixture that faked it would prove nothing about the thing that can silently break.

It was module-level in `test_document_reader.py` until that file split; the curated-branch
tests need the same corpus, so it lives here and is imported.
"""

from __future__ import annotations

import pytest

from core.models import PublicDocument
from knowledge.models import DocumentChunk, StandardDocument, StandardSet


CORPUS_SOURCE = "pgs_docs/saoso-version-2.1-2026.pdf"

APPENDIX = (
    "Biodegradable processing by-products, plant or animal origin. Condition: free of "
    "significant contaminants; or composted before bringing onto organic land."
)


@pytest.fixture
def seeded_documents(db):
    """A published row and an ingested corpus document that trace to the same file.

    The equality of `source_path` and `source_file` is the join the reader depends on, so the
    fixture builds both from one constant. A fixture that faked the join would prove nothing
    about the thing that can silently break.
    """
    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    document = StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard for Organic Production and Processing",
        version="2.1",
        source_file=CORPUS_SOURCE,
        sha256="a" * 64,
        section_scheme="saoso",
    )
    DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2",
        heading_path="APPENDICES > Appendix 2",
        page=76,
        text=APPENDIX,
    )
    DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2.1",
        heading_path="APPENDICES > Appendix 2",
        page=77,
        text="Wood, bark and sawdust, only if not chemically treated.",
    )
    document.chunk_count = 2
    document.save(update_fields=["chunk_count"])

    rows = {
        "saoso": PublicDocument.objects.create(
            code="saoso-standard-v2.1",
            title="SAOSO Organic Standard v2.1",
            file_path="public/documents/saoso-standard-v2.1.pdf",
            source_path=CORPUS_SOURCE,
            is_published=True,
        ),
        "opp": PublicDocument.objects.create(
            code="opp",
            title="Principles, Policies & Procedures",
            file_path="public/documents/opp.pdf",
            source_path="pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf",
            is_published=True,
        ),
    }
    return rows


