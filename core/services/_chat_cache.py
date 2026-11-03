"""The answer cache: what a cached reply is keyed on, and the snapshot that proves it.

Split out of `_chatbot.py` (CONTEXT_CUTS_PRD step 5, second half -- the guardrails left in
the first). A cached answer claims that *this* corpus, question and prompt produced *this*
reply, so the key is a fingerprint of all three (`PROMPT_VERSION` among them) and the
snapshot records the passages it was grounded on. Get that wrong and the cache serves an
answer from a corpus that no longer exists, which is why `text_sha` matches a passage by
its words rather than its layout.

**Only answered questions are cached.** A refusal is never written here: a bad generation
must not outlive the turn that produced it (`testing_hazards.md` §1.31).
"""

from __future__ import annotations

import hashlib
import json

from django.conf import settings
from django.db.models import Count, Max

from core.services._chat_prompt import PROMPT_VERSION
from core.services._chat_text import locator_of, normalise_question, text_sha
from core.services._chat_values import Citation, ModelReply
from knowledge.models import DocumentChunk, StandardSet
from knowledge.services import RetrievedChunk

#: How long an answered question stays cached, in seconds. Read through
#: `getattr(settings, ...)`, so a deployment can change it without a release.
ANSWER_CACHE_TTL = 3600


# --- The answer cache -------------------------------------------------------


def _corpus_fingerprint(standard_set: StandardSet) -> str:
    """A cheap description of the corpus a cached reply was produced from.

    Count + max id catches an ingest or a re-chunk; the document sha list catches the
    same bytes being re-ingested under a new version. It is not a content hash of
    every chunk â€” that would cost more than the Gemini call it saves â€” but it is
    enough that a corpus change cannot silently reuse yesterday's citations.
    """
    aggregate = (
        DocumentChunk.objects.filter(document__standard_set=standard_set).aggregate(
            count=Count("id"), max_id=Max("id")
        )
    )
    shas = "|".join(
        standard_set.documents.order_by("id").values_list("sha256", flat=True)
    )
    return hashlib.sha256(
        f"{aggregate['count']}:{aggregate['max_id']}:{shas}".encode()
    ).hexdigest()[:32]


def _cache_key(
    question: str,
    standard_set: StandardSet,
    fingerprint: str | None = None,
    history_digest: str = "",
) -> str:
    """The cache key: contract, corpus, question, and the conversation that shaped it.

    `history_digest` is set for a **follow-up** — a turn whose retrieval and prompt both
    depend on the previous exchange — and empty otherwise. That is deliberately narrower
    than "history exists":

    * A first question has no history at all, which is the case the cache exists for:
      many visitors, one question.
    * A standalone question in an existing conversation still receives the bounded
      history in its prompt (D2, `CHAT_HISTORY_MESSAGES`), so its reply *may* differ from
      another visitor's. That residual predates stage 1 and is not made worse by it: the
      prompt now says the earlier turns resolve references and may not be cited, and a
      standalone turn inherits no passages. Keying it on the history would remove the
      cache hit for the common "ask it again to re-read it" case and break three tests
      that pin the property deliberately.
    * A follow-up's answer genuinely *is* derived from its parent, so it cannot be shared
      with a different conversation. That is the leak this closes.
    """
    material = normalise_question(question)
    if history_digest:
        material = f"{history_digest}\x00{material}"
    digest = hashlib.sha256(material.encode()).hexdigest()[:32]
    return (
        f"chat:answer:{PROMPT_VERSION}:{standard_set.pk}:"
        f"{fingerprint or _corpus_fingerprint(standard_set)}:{digest}"
    )


def _grounding_snapshot(chunks: Sequence[RetrievedChunk]) -> list[dict]:
    """What an answer stood on, in a form that outlives the chunks themselves.

    `retrieved_chunks` is the joinable record while the corpus exists; `--force`
    re-ingest deletes the chunks and takes the M2M rows with them, so a corpus rebuild
    erases the evidence for every answer already given. The transcript is kept
    indefinitely (D59), so the grounds for it must be too.

    The text sha is what makes this a record rather than a label: it lets a reviewer
    tell "the same locator, text changed" from "the same passage" without storing the
    passage a second time (the corpus owns the text).
    """
    return [
        {
            "locator": locator_of(chunk),
            "page": chunk.page,
            "heading_path": chunk.heading_path,
            "document": chunk.document_title,
            "text_sha": text_sha(chunk.text),
        }
        for chunk in chunks
    ]


def citation_records(citations: Sequence[Citation]) -> list[dict]:
    """The accepted citations in the shape `_citation_record` stores them.

    One shape, two callers: the transcript's evidence trail and the board's card. A card and a
    turn must not disagree about what was cited, and two list comprehensions that drift apart
    would disagree silently.

    `document_code` and `reading_anchor` are stored **in** the snapshot rather than resolved at
    render time: a card outlives a `--force` re-ingest, and a page that silently re-resolved a
    citation after the corpus changed would be a claim nobody could audit.
    """
    return [
        {
            "section_ref": citation.section_ref,
            "sub_ref": citation.sub_ref,
            "page": citation.page,
            "document": citation.document,
            "quote": citation.quote,
            # Recorded so a follow-up can carry the previous answer's clauses back into
            # retrieval, and so the trace console can show which passage an accepted
            # citation actually named. Rows written before this carry no `chunk_id`, and a
            # follow-up simply inherits nothing from them.
            "chunk_id": citation.chunk_id,
            "document_code": citation.document_code,
            "reading_anchor": citation.reading_anchor,
            # `D79` option E: the row and column frame the quote, and a card outlives the corpus
            # the same way its quote does. Without these the answer page silently renders no
            # context while the transcript renders it — two surfaces disagreeing about one
            # citation (found while building slice 3).
            "row_label": citation.row_label,
            "column_label": citation.column_label,
        }
        for citation in citations
    ]


def _citation_record(
    raw_citations: Sequence[object], accepted: Sequence[Citation]
) -> dict:
    """The citations as returned, and as shown — in one field, with no guesswork.

    `raw` is kept verbatim, unsanitised: it is the model's output and the evidence of
    what it did. `accepted` is the audited subset, carrying the document and page that
    the audit attached from the chunk rather than from the model.

    Deliberately *not* matched pairwise. The audit normalises a locator before lookup
    (`§4.2` vs `4.2`), so deciding which raw citation corresponds to which accepted one
    would be a heuristic — and a heuristic in the evidence trail is worse than two lists.
    """
    return {
        "raw": [item for item in raw_citations if isinstance(item, dict)][:20],
        "accepted": citation_records(accepted),
    }


def _reply_to_json(reply: ModelReply) -> dict:
    return {
        "answer": reply.answer,
        "citations": list(reply.citations),
        "insufficient_context": reply.insufficient_context,
        "model": reply.model,
        "prompt_tokens": reply.prompt_tokens,
        "completion_tokens": reply.completion_tokens,
    }


def _reply_from_json(payload: dict) -> ModelReply:
    return ModelReply(
        answer=str(payload.get("answer", "")),
        citations=tuple(payload.get("citations") or ()),
        insufficient_context=bool(payload.get("insufficient_context")),
        model=str(payload.get("model", "")),
        prompt_tokens=payload.get("prompt_tokens"),
        completion_tokens=payload.get("completion_tokens"),
    )
