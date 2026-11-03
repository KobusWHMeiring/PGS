"""D53 — the reviewed corpus artefact, audited end to end.

The BPP is ingested from `knowledge/corpus/bpp.md`, the artefact the box actually serves,
and every one of its ten reviewed examples is quoted through `audit_citations`. A
hand-built chunk would prove the audit, not the artefact; so both halves are asserted:
every reviewed example is accepted, and a paraphrase of one is still refused.

The corpus-side refusals whose cause was the corpus (D46, D52) live in
`test_chatbot_grounding.py`, beside the answer path they broke.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.services._chatbot import audit_citations
from core.tests.chat_helpers import retrieved_from_stored as _retrieved_from_stored

#: `ingest_standard` still takes the source PDF path when the reviewed artefact is what it
#: reads; the artefact is the truth, the PDF only names the document.
PDF_DIR = Path(__file__).resolve().parents[2] / "pgs_docs"
BPP_PDF = PDF_DIR / "Basic Production Principles_ENG_PRINT.pdf"


@pytest.fixture(autouse=True)
def committed_extraction(monkeypatch):
    """Ingest from the committed pages, not through a PDF reader (D57).

    `ingest_standard` still reads `pdf_path` even when `corpus_path` is the reviewed
    artefact, so without this the test needs a live `pdftotext` — and the gate runs with
    `PDFTOTEXT_BIN` pointed at a path that cannot exist (`testing_hazards.md` §2.9).
    """
    from knowledge.tests.page_fixtures import stub_ingest_extraction

    stub_ingest_extraction(monkeypatch)


pytestmark = pytest.mark.django_db


# --- The corpus artefact (D53): ten reviewed examples, audited end to end -----
#
# The BPP is ingested from its reviewed artefact (`knowledge/corpus/bpp.md`), then each
# example is put through the *real* audit. The knowledge-side test proves each sentence
# survives chunking; this proves the audit accepts a citation of it against the rows the
# artefact actually produced. Two halves of one claim, on the correct side of the
# knowledge/core boundary.

def _bpp_from_artefact(standard_set):
    from pathlib import Path

    from knowledge.ingest import ingest_standard

    artefact = (
        Path(__file__).resolve().parents[2] / "knowledge" / "corpus" / "bpp.md"
    )
    ingest_standard(
        pdf_path=BPP_PDF,
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        corpus_path=artefact,
    )
    return artefact


def test_every_reviewed_example_is_accepted_by_the_audit(chat_standard_set):
    from knowledge.models import DocumentChunk
    from knowledge.tests.test_corpus_bpp import REVIEWED_QUOTES

    _bpp_from_artefact(chat_standard_set)
    retrieved = [
        _retrieved_from_stored(chunk, chat_standard_set)
        for chunk in DocumentChunk.objects.filter(
            document__standard_set=chat_standard_set, anchor="general-principles"
        )
    ]
    assert retrieved, "the artefact produced no general-principles chunks"

    refused = {}
    for label, sentence in REVIEWED_QUOTES:
        citations, problems = audit_citations(
            [{"section_ref": "general-principles", "quote": sentence}],
            retrieved,
            standard_set_id=chat_standard_set.pk,
        )
        if problems or not citations:
            refused[label] = problems
    assert refused == {}


def test_a_paraphrase_of_a_reviewed_example_is_still_refused(chat_standard_set):
    """The corpus does not make a paraphrase verbatim — the guard on the guard."""
    from knowledge.models import DocumentChunk
    from knowledge.tests.test_corpus_bpp import REVIEWED_QUOTES

    _bpp_from_artefact(chat_standard_set)
    retrieved = [
        _retrieved_from_stored(chunk, chat_standard_set)
        for chunk in DocumentChunk.objects.filter(
            document__standard_set=chat_standard_set, anchor="general-principles"
        )
    ]
    original = dict(REVIEWED_QUOTES)["daily-pasture-access"]
    paraphrased = original.replace("All animals shall have", "Every animal must have")

    citations, problems = audit_citations(
        [{"section_ref": "general-principles", "quote": paraphrased}],
        retrieved,
        standard_set_id=chat_standard_set.pk,
    )
    assert citations == []
    assert problems == ("general-principles: the quote is not in the cited chunk",)


