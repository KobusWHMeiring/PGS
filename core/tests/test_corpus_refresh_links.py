"""P2.3 — the refresh says what it will destroy, before it destroys it.

`--force` deletes a document's chunks and every `ChatMessage.retrieved_chunks` row that
pointed at them (`HANDOVER.md` §17, `core/services/_evidence.py`). The stored grounding
snapshot survives (P2.5a); the join does not. So `corpus_refresh` counts those rows and says
the number in its dry run.

Two things are being proved here, and the second is the interesting one:

1. the count is right;
2. it is derived from **Django's relation metadata**, not from a hardcoded `ChatMessage` —
   `knowledge` may not import `core` (`build_principles.md` §I), so the count has to work
   for whatever table points at a chunk. This test is the only place that claim can be
   checked against a real citation table, which is why it lives in `core/tests/`.
"""

from __future__ import annotations

import hashlib
import shutil
from io import StringIO

import pytest
from django.core.management import call_command

from core.models import ChatMessage, ChatSession
from knowledge.drift import citation_links, corpus_states
from knowledge.ingest import CORPUS_DIR
from knowledge.models import DocumentChunk, StandardDocument, StandardSet

pytestmark = pytest.mark.django_db

BPP_PDF = "pgs_docs/Basic Production Principles_ENG_PRINT.pdf"


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)


def _document(standard_set):
    """A document holding the artefact's bytes, built from the PDF path (so: drift).

    Its `sha256` is the one the artefact header names, which is what makes
    `corpus_states()` find it — the drift is `corpus_digest == ""`, exactly as on the box
    this plan is written for.
    """
    declared = (CORPUS_DIR / "bpp.md").read_text(encoding="utf-8")
    sha256 = declared.split("sha256: ")[1].split()[0]
    return StandardDocument.objects.create(
        standard_set=standard_set,
        kind=StandardDocument.Kind.PRINCIPLES,
        title="Basic Production Principles",
        version="",
        source_file=BPP_PDF,
        sha256=sha256,
        section_scheme="heading",
        chunk_count=2,
    )


def _cited(document, texts):
    """Two chunks and one assistant turn that quoted them — the rows `--force` cascades."""
    chunks = [
        DocumentChunk.objects.create(document=document, text=text, heading_path="Principles")
        for text in texts
    ]
    session = ChatSession.objects.create(standard_set=document.standard_set)
    message = ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.ASSISTANT, content="See the principles."
    )
    message.retrieved_chunks.set(chunks)
    return chunks, message


def test_the_count_is_the_rows_the_force_will_cascade(standard_set):
    document = _document(standard_set)
    chunks, _message = _cited(document, ["one.", "two."])

    assert citation_links(document) == 2

    chunks[0].delete()

    assert citation_links(document) == 1, "a deleted chunk's link is not a link"


def test_the_dry_run_names_the_cost_of_applying(standard_set):
    """The operator's decision is 'is this worth it?', so the number must be in the report
    that precedes `--apply` — not in the log of the run that already did it."""
    document = _document(standard_set)
    _cited(document, ["one.", "two."])

    out = StringIO()
    call_command("corpus_refresh", "--no-embed", stdout=out)

    assert "2 chat citation link(s) will be dropped" in out.getvalue(), out.getvalue()
    assert "Dry run. Nothing was written." in out.getvalue()
    assert ChatMessage.objects.get(role=ChatMessage.Role.ASSISTANT).retrieved_chunks.count() == 2


def test_the_refresh_says_nothing_about_links_it_does_not_drop(standard_set, tmp_path, monkeypatch):
    """A current corpus has no `--force` in front of it, so there is no cost to report."""
    copy = tmp_path / "bpp.md"
    shutil.copyfile(CORPUS_DIR / "bpp.md", copy)
    document = _document(standard_set)
    document.corpus_digest = hashlib.sha256(copy.read_bytes()).hexdigest()
    document.save(update_fields=["corpus_digest"])
    _cited(document, ["one."])
    monkeypatch.setattr("knowledge.ingest.CORPUS_DIR", tmp_path)
    # `chunk_count` is denormalised and this fixture built two chunks by hand; take the
    # number the artefact produces so the document is genuinely current.
    document.chunk_count = {
        state.doc_key: state for state in corpus_states(standard_set)
    }["bpp"].expected_chunks
    document.save(update_fields=["chunk_count"])

    out = StringIO()
    call_command("corpus_refresh", "--no-embed", stdout=out)

    assert "nothing to refresh" in out.getvalue(), out.getvalue()
    assert "citation link" not in out.getvalue()
