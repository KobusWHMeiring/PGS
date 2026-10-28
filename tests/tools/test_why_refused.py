"""`why_refused.py` must not report a retrieval failure after a corpus rebuild.

After `ingest_standard --force` the chunks are deleted, `ChatMessage.retrieved_chunks`
cascades with them, and the probe printed `retrieved(0)` on a turn that had retrieved five
passages — a corpus defect where the truth was "a rebuild removed the links". The operator
reading that log would go looking in the retriever.

So the probe falls back to the `grounding` snapshot (P2.5a) and **names which source it
read**, because "5 passages" from a snapshot and "5 rows" from the join are not the same
evidence: one can be followed to the word, the other cannot.

`_refs` is where the choice is made, so it is what this file tests. A whole-script
assertion on printed text would pass on the day the fallback was deleted and the snapshot
was printed by some other line (`testing_hazards.md` §1.6).
"""

from __future__ import annotations

import pytest

from core.models import ChatMessage, ChatSession
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from scripts.why_refused import _refs

pytestmark = pytest.mark.django_db


@pytest.fixture
def message(db):
    standard_set = StandardSet.objects.create(
        code="outeniqua", label="Outeniqua", is_default=True
    )
    document = StandardDocument.objects.create(
        standard_set=standard_set,
        kind=StandardDocument.Kind.STANDARD,
        title="SAOSO Standard",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="a" * 64,
        section_scheme="saoso",
    )
    chunk = DocumentChunk.objects.create(
        document=document, section_ref="S23.3", page=67, text="A clause about forced labour."
    )
    session = ChatSession.objects.create(standard_set=standard_set)
    turn = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content="Operators shall not use forced or involuntary labour.",
        grounding=[
            {
                "locator": "S23.3",
                "page": 67,
                "heading_path": "23. HUMAN RIGHTS",
                "document": "SAOSO Standard",
                "text_sha": "0123456789abcdef",
            }
        ],
    )
    turn.retrieved_chunks.add(chunk)
    return turn


def test_the_links_are_read_first_and_named_as_retrieved(message):
    refs, source = _refs(message)

    assert refs == ["S23.3"]
    assert source == "retrieved"


def test_a_rebuilt_corpus_falls_back_to_the_snapshot_and_says_so(message):
    """The defect: after a rebuild the probe said `retrieved(0)` and hid five passages."""
    DocumentChunk.objects.all().delete()
    message.refresh_from_db()
    assert message.retrieved_chunks.count() == 0, "the fixture did not simulate a rebuild"

    refs, source = _refs(message)

    assert refs == ["S23.3"], "the snapshot's passages were not read"
    assert source == "snapshot", "the probe must not present a snapshot as the join"


def test_a_turn_with_neither_is_empty_and_does_not_raise(message):
    """Fifty of this instance's turns predate the snapshot; the probe still has to run."""
    DocumentChunk.objects.all().delete()
    message.refresh_from_db()
    message.grounding = []
    message.save(update_fields=["grounding"])

    refs, source = _refs(message)

    assert refs == []
    assert source in {"retrieved", "snapshot"}
