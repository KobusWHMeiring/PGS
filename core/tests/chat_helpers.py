"""Builders shared by the `answer_question()` test modules.

Three helpers, and they are here rather than in `conftest.py` because they are plain
builders with no fixture lifecycle: a stored `RetrievedChunk` read back off a real
ingested chunk, a `ModelReply` that is grounded by construction, and the one call that
goes through the answer path.

They live in one place because three modules now ask the audit about the same shape of
input (`test_chatbot_audit`, `test_chatbot_prompt`, `test_chatbot_turns`). A builder
copied three times is a builder that drifts — and a drifted builder would make one of
those files assert something the others do not.
"""

from __future__ import annotations

from core.services._chatbot import ModelReply, answer_question


def retrieved_from_stored(chunk, standard_set):
    """The `RetrievedChunk` a real stored chunk becomes, without touching retrieval."""
    from knowledge.services import RetrievedChunk

    return RetrievedChunk(
        chunk_id=chunk.pk,
        document_title=chunk.document.title,
        document_version=chunk.document.version,
        section_ref=chunk.section_ref,
        heading_path=chunk.heading_path,
        page=chunk.page,
        anchor=chunk.anchor,
        text=chunk.text,
        score=1.0,
        standard_set_id=standard_set.pk,
        sub_refs=tuple(chunk.sub_refs or ()),
    )


def grounded_reply(**overrides):
    """A model reply whose only citation is a real sentence from the SAOSO corpus."""
    fields = {
        "answer": "Records must let a product be traced from farm to buyer.",
        "citations": (
            {
                "section_ref": "S20.1.1",
                "quote": "Traceability is required for every batch of organic product",
            },
        ),
        "insufficient_context": False,
        "model": "fake-model",
        "prompt_tokens": 140,
        "completion_tokens": 36,
    }
    fields.update(overrides)
    return ModelReply(**fields)


def ask(session, question, provider, **kwargs):
    """One turn through the answer path, with no IP to hash."""
    return answer_question(
        session.public_uuid, question, provider=provider, ip_hash="", **kwargs
    )
