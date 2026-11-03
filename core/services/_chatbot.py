"""The grounded chatbot â€” retrieval-grounded answering, refusal, and guardrails.

This module owns the contract in SPEC Â§6 and Â§13:

    In:  session_uuid, question (non-empty, <= 500 chars)
    Out: GroundedAnswer(text, citations, insufficient_context, escalated_query_id)
    Side Effects: writes ChatMessage rows; writes EscalatedQuery when ungrounded
    Fails: RateLimitedError, UpstreamModelError â€” never a fabricated fallback

**The refusal is the product.** A model that answers plausibly from its own training
is worse than useless here: the group's credibility rests on every sentence being
traceable to SAOSO, the OPP, the Basic Production Principles or the certification
landscape. So a result is grounded only when *all* of the following hold:

1. retrieval returned at least one chunk from the session's `StandardSet`;
2. the model did not set `insufficient_context`;
3. it returned at least one citation;
4. every citation names a `section_ref` (or heading-only `anchor`) that is present in
   the retrieved set;
5. every `sub_ref` exists in that chunk's stored offset map;
6. every quote is a whitespace-normalised substring of the cited chunk's own text.

Any failure produces exactly `REFUSAL` and one `EscalatedQuery`. The trigger is the
structured flag and the citation audit â€” never string-matching the model's prose.

**Nothing here invents a fallback.** If Gemini is unreachable or no key is
configured, `UpstreamModelError` propagates and the view renders an honest
"unavailable" notice. A friendly-sounding canned answer would be the one failure the
whole feature exists to prevent.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from typing import Callable, Sequence

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from core.models import ChatMessage, ChatSession, EscalatedQuery, User
from core.services._chat_audit import (
    MAX_CITATIONS,
    audit_citations,
    cost_question_warnings,
    outcome_claim_warnings,
)
from core.services._chat_prompt import (
    COST_QUESTION_RULE,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_prompt,
    looks_like_cost_question,
    significant_terms,
)
from core.services._chat_guard import (
    MAX_QUESTION_CHARS,
    RETRIEVAL_LIMIT,
    attach_user,
    build_retrieval_query,
    chat_retrieval_limit,
    check_rate_limit,
    default_retrieval,
    default_standard_set,
    get_session,
    looks_like_follow_up,
    start_session,
    validate_question,
)
from core.services._chat_provider import (
    ANSWER_SCHEMA,
    MAX_OUTPUT_TOKENS,
    GeminiChatModel,
)
from core.services._chat_cache import (
    ANSWER_CACHE_TTL,
    _cache_key,
    _citation_record,
    _corpus_fingerprint,
    _grounding_snapshot,
    _reply_from_json,
    _reply_to_json,
    citation_records,
)
from core.services._chat_text import locator_of, normalise_question, text_sha
from core.services._chat_values import (
    AnswerTruncatedError,
    ChatConfigurationError,
    ChatError,
    ChatModel,
    Citation,
    GroundedAnswer,
    InvalidQuestionError,
    ModelReply,
    RateLimitedError,
    SessionNotFoundError,
    UpstreamModelError,
)
from core.services._documents import public_codes_by_source
from knowledge.models import StandardSet
from knowledge.reading import reading_anchor
from knowledge.services import RetrievedChunk, RetrievalResult, chunks_by_id

logger = logging.getLogger(__name__)

#: D17. Not the old SAOSO-only string: the OPP answers questions the standard does
#: not (fees, joining, committee procedure), so a refusal that named only SAOSO would
#: be a lie about the corpus.
REFUSAL = (
    "I cannot find a definitive answer in the SAOSO standard or the Outeniqua PGS "
    "documents."
)

#: The public-facing messages around failures. None of them is an answer.
UNAVAILABLE_MESSAGE = (
    "The assistant cannot reach the answering service right now. Nothing has been "
    "guessed. Please try again later, or contact the administrator."
)
CONFIGURATION_MESSAGE = (
    "The standard corpus is not loaded on this deployment, so the assistant cannot "
    "answer yet. Please contact the administrator."
)
RATE_LIMIT_MESSAGE = (
    "You have asked a lot of questions in a short time. Please try again in about "
    "{seconds} seconds."
)
#: A generation the provider cut at the output cap. This is **not** an outage and
#: must not be reported as one: the model answered, we could not see all of it, and
#: showing the fragment would be the silent truncation the contract forbids. The
#: visitor gets an actionable sentence instead of "try again later".
TRUNCATED_MESSAGE = (
    "That answer ran longer than the assistant can check, so it was not shown. "
    "Please ask a narrower question, or contact the administrator."
)

#: Defaults. Every one is read through `getattr(settings, â€¦)` at call time, so a test
#: or a deployment can override it with `override_settings`/an environment variable.
HISTORY_MESSAGES = 8
MAX_ANSWER_CHARS = 6000
#: How many of the previous answer's clauses a follow-up may carry back into
#: retrieval. The audited citations, not the eight supplied passages.
CARRIED_CITATIONS = 2


# --- The contract -----------------------------------------------------------


def _history_for(session: ChatSession) -> list[ChatMessage]:
    limit = int(getattr(settings, "CHAT_HISTORY_MESSAGES", HISTORY_MESSAGES))
    if limit <= 0:
        return []
    return list(
        session.messages.order_by("-created_at", "-id")[:limit]
    )[::-1]


def _last_user_question(history: Sequence[ChatMessage]) -> str:
    """The previous question in this conversation, or "".

    `history` is ordered oldest first and excludes the question being asked (it is read
    before the user message is written), so the last USER row is the parent turn.
    """
    for message in reversed(list(history)):
        if message.role == ChatMessage.Role.USER:
            return message.content
    return ""


def _last_assistant_message(history: Sequence[ChatMessage]) -> ChatMessage | None:
    """The previous answer, or None. This is what a follow-up inherits citations from."""
    for message in reversed(list(history)):
        if message.role == ChatMessage.Role.ASSISTANT:
            return message
    return None


def _carried_chunk_ids(message: ChatMessage | None) -> tuple[int, ...]:
    """The chunks the previous answer actually cited, in order.

    Read from `citations.accepted`, which is the audited subset — not `retrieved_chunks`,
    which is everything the retriever supplied. Carrying all eight would be the "seeded
    retrieval" mistake: the previous subject would take the budget back. Rows written
    before `chunk_id` was recorded simply carry nothing.
    """
    if message is None:
        return ()
    accepted = (message.citations or {}).get("accepted") or []
    ids = [entry.get("chunk_id") for entry in accepted if isinstance(entry, dict)]
    return tuple(cid for cid in ids if isinstance(cid, int))[:CARRIED_CITATIONS]


def _with_carried_citations(
    chunks: Sequence[RetrievedChunk],
    carried_ids: Sequence[int],
    standard_set: StandardSet,
    *,
    budget: int | None = None,
) -> tuple[RetrievedChunk, ...]:
    """Add the previous answer's clauses to this turn's set, displacing the tail.

    In:  the passages this turn's question retrieved; chunk ids carried from the parent
         answer; the corpus boundary; `budget` — the passage count to hold to, defaulting
         to the product's own. The probe passes its `--limit` so the instrument measures
         the budget it claims to measure (`testing_hazards.md` §2.7).
    Out: a tuple of at most `chat_retrieval_limit()` passages.
    Side Effects: one query, and only when a carried id is genuinely missing.

    The tail is displaced rather than the budget split, for the same reason the context
    arm is capped: the new question has already been ranked on its own merits, and the
    previous turn may only take seats the new turn could not fill. The common case costs
    nothing — the parent's clause is usually already in the set.
    """
    present = {chunk.chunk_id for chunk in chunks}
    wanted = [cid for cid in carried_ids if cid not in present]
    if not wanted:
        return tuple(chunks)
    extra = chunks_by_id(wanted, standard_set=standard_set)
    if not extra:
        return tuple(chunks)
    keep = max(0, (chat_retrieval_limit() if budget is None else budget) - len(extra))
    return tuple(chunks)[:keep] + tuple(extra)


def _history_digest(history: Sequence[ChatMessage]) -> str:
    """A short, stable description of the conversation a reply was produced under.

    Part of the answer-cache key. The prompt has carried history since D2, so two
    visitors asking the same question with different conversations were already sharing
    one cached reply; once a follow-up's answer *depends* on its parent, that is a
    cross-conversation leak rather than a stale answer. Empty for a first question, so
    the common case keeps its cache.
    """
    if not history:
        return ""
    joined = "\n".join(f"{message.role}:{message.content}" for message in history)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _as_refusal(
    *,
    session: ChatSession,
    user_message: ChatMessage,
    question: str,
    chunks: Sequence[RetrievedChunk],
    reason: str,
    latency_ms: int,
    reply: ModelReply | None,
    cached: bool,
    fingerprint: str = "",
    problems: Sequence[str] = (),
) -> GroundedAnswer:
    """Write the refusal and its escalation in one transaction."""
    with transaction.atomic():
        assistant = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=REFUSAL,
            latency_ms=latency_ms,
            model=(reply.model if reply else ""),
            prompt_tokens=(0 if cached else (reply.prompt_tokens if reply else None)),
            completion_tokens=(
                0 if cached else (reply.completion_tokens if reply else None)
            ),
            prompt_version=PROMPT_VERSION,
            corpus_fingerprint=fingerprint,
            # Kept on a refusal: a refused citation is the evidence for *which* check
            # fired, and `CITATION_AUDIT` alone cannot tell a prompt defect from a
            # corpus one (G9). `accepted` is empty by definition here.
            citations=_citation_record(reply.citations if reply else (), ()),
            refusal_checks=list(problems)[:20],
            refusal_reason=reason,
            grounding=_grounding_snapshot(chunks),
        )
        assistant.retrieved_chunks.set([chunk.chunk_id for chunk in chunks])
        escalation = EscalatedQuery.objects.create(
            message=user_message,
            question=question,
            reason=reason,
        )

    logger.info(
        "chatbot escalated",
        extra={
            "chat_session": str(session.public_uuid),
            "chat_reason": reason,
            "chat_retrieved": len(chunks),
        },
    )
    return GroundedAnswer(
        text=REFUSAL,
        citations=[],
        insufficient_context=True,
        escalated_query_id=escalation.pk,
        message_id=assistant.pk,
        cached=cached,
    )


def answer_question(
    session_uuid: uuid.UUID | str,
    question: str,
    *,
    ip_hash: str = "",
    provider: ChatModel | None = None,
    retrieval: Callable[..., RetrievalResult] | None = None,
    now: float | None = None,
) -> GroundedAnswer:
    """Answer one question from the session's corpus, or refuse.

    In:  `session_uuid`; `question` (non-empty, <= `CHAT_MAX_QUESTION_CHARS`);
         `ip_hash` for the per-IP budget; `provider`/`retrieval` for tests; `now` for
         the rate-limit clock. A `retrieval` stand-in must accept the keyword
         `context_query` — it is `""` for a standalone question and the previous
         question's lexical query for a follow-up, and a fake that ignores it is
         testing a path the product no longer has (`testing_hazards.md` §2.7).
    Out: a `GroundedAnswer`. `text` is a grounded answer or exactly `REFUSAL`.
    Side Effects: writes a USER and an ASSISTANT `ChatMessage`; on an ungrounded
         result writes one `EscalatedQuery`; may call Gemini once.
    Fails: `InvalidQuestionError`, `SessionNotFoundError`, `RateLimitedError`,
         `UpstreamModelError`. Never returns a fabricated fallback.
    Idempotency: not idempotent by design (each question is a new turn); the answer
         cache removes the repeated Gemini call for a question that was **answered**, and
         only for one that was answered — a refusal is never cached, so a bad generation
         cannot poison the question (`testing_hazards.md` §1.31).
    """
    text = validate_question(question)
    check_rate_limit(ip_hash, now=now)

    session = get_session(session_uuid)
    # Read once, before anything can return: a refusal has to record the corpus it was
    # grounded on too, and the `not chunks` branch returns before the cache key exists.
    fingerprint = _corpus_fingerprint(session.standard_set)
    history = _history_for(session)
    # Stage 1 of the follow-up decision. Two things travel from the previous turn into
    # this one, and both are opt-in on evidence rather than assumed:
    #   * `context_query` — the previous question, fused in by `search_terms` so the
    #     fragment's own words are not the only description of the subject;
    #   * `carried_ids` — the clauses the previous answer was *allowed* to cite, so the
    #     audit can accept a follow-up quoting the passage the visitor just read.
    # A standalone question gets neither, and is answered exactly as it was before.
    parent_question = _last_user_question(history)
    parent_answer = _last_assistant_message(history)
    follows_on = bool(parent_question) and looks_like_follow_up(text, parent_question)
    # A *lexical* query, not a sentence: `search_terms` hands it to
    # `websearch_to_tsquery`, which ANDs words, so a natural question would match
    # nothing. `build_retrieval_query` is the existing OR-joiner for this case.
    context_query = build_retrieval_query(parent_question) if follows_on else ""
    carried_ids = _carried_chunk_ids(parent_answer) if follows_on else ()
    user_message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.USER,
        content=text,
    )

    started = time.monotonic()
    retrieve = retrieval or default_retrieval
    result: RetrievalResult = retrieve(
        text, session.standard_set, context_query=context_query
    )
    chunks = _with_carried_citations(result.chunks, carried_ids, session.standard_set)

    # Nothing retrieved means there is nothing to ground on. Calling the model here
    # would invite it to answer from memory â€” the exact failure the feature forbids.
    if not chunks:
        latency_ms = int((time.monotonic() - started) * 1000)
        return _as_refusal(
            session=session,
            user_message=user_message,
            fingerprint=fingerprint,
            question=text,
            chunks=chunks,
            reason=EscalatedQuery.Reason.NO_RETRIEVAL,
            latency_ms=latency_ms,
            reply=None,
            cached=False,
        )

    # Keyed on the conversation *only when the answer was derived from it*. A
    # standalone question keeps its plain key, so re-asking it in the same session (or
    # in any other) is still a cache hit — a product property three tests pin. The
    # residual is stated where it belongs, in `_cache_key`'s docstring.
    cache_key = _cache_key(
        text,
        session.standard_set,
        fingerprint,
        _history_digest(history) if follows_on else "",
    )
    cached_payload = cache.get(cache_key)
    cached = cached_payload is not None
    reply: ModelReply
    if cached:
        reply = _reply_from_json(cached_payload)
    else:
        model = provider or GeminiChatModel()
        reply = model.answer(question=text, chunks=chunks, history=history)
        if not isinstance(reply, ModelReply):
            raise UpstreamModelError(
                "The generation provider returned something other than a ModelReply."
            )

    latency_ms = int((time.monotonic() - started) * 1000)
    citations, problems = audit_citations(
        reply.citations,
        chunks,
        standard_set_id=session.standard_set_id,
        # Resolved once per turn: `is_published` is consulted, so a citation can only link to
        # a document the group actually publishes.
        document_codes=public_codes_by_source(),
    )

    # Every branch below is a refusal. The flags are deliberately separate so the
    # escalation reason says which one fired; the user-visible text is identical.
    if reply.insufficient_context:
        return _as_refusal(
            session=session,
            user_message=user_message,
            fingerprint=fingerprint,
            problems=problems,
            question=text,
            chunks=chunks,
            reason=EscalatedQuery.Reason.INSUFFICIENT_CONTEXT,
            latency_ms=latency_ms,
            reply=reply,
            cached=cached,
        )
    if not reply.citations:
        # The model cited nothing at all. `NO_CITATIONS` is the honest reason here; the
        # audit reports it as a problem, but "cited nothing" and "cited something wrong"
        # are different findings and the record must not blur them.
        return _as_refusal(
            session=session,
            user_message=user_message,
            fingerprint=fingerprint,
            problems=problems,
            question=text,
            chunks=chunks,
            reason=EscalatedQuery.Reason.NO_CITATIONS,
            latency_ms=latency_ms,
            reply=reply,
            cached=cached,
        )
    if problems:
        # A distinct reason from `NO_CITATIONS`: the model *did* cite, and the citations
        # were wrong. Recording both as "no valid citations" hides a contract violation
        # behind a reason that suggests the corpus is thin (testing_hazards.md §1.31).
        logger.warning(
            "chatbot citation audit refused an answer",
            extra={
                "chat_session": str(session.public_uuid),
                "chat_problems": "; ".join(problems)[:500],
            },
        )
        return _as_refusal(
            session=session,
            user_message=user_message,
            fingerprint=fingerprint,
            problems=problems,
            question=text,
            chunks=chunks,
            reason=EscalatedQuery.Reason.CITATION_AUDIT,
            latency_ms=latency_ms,
            reply=reply,
            cached=cached,
        )
    if not citations or not reply.answer.strip():
        # The citations verified and the answer said nothing. This branch used to be
        # recorded as `NO_CITATIONS`, which is a lie in the record: the citations were
        # there. It is reachable only after `problems` is empty, so `not citations` here
        # means every citation was a duplicate, and the honest reason is the empty text.
        return _as_refusal(
            session=session,
            user_message=user_message,
            fingerprint=fingerprint,
            problems=problems,
            question=text,
            chunks=chunks,
            reason=EscalatedQuery.Reason.EMPTY_ANSWER,
            latency_ms=latency_ms,
            reply=reply,
            cached=cached,
        )

    answer_text = reply.answer.strip()
    if len(answer_text) > MAX_ANSWER_CHARS:
        # A runaway answer is not a grounded one, and truncating it would silently
        # change what the model said. Refuse and record it for review instead — as
        # `ANSWER_TOO_LONG`, never `NO_CITATIONS`: the citations verified, the generation
        # ran on, and a reviewer needs to see *that* rather than a thin-corpus story.
        return _as_refusal(
            session=session,
            user_message=user_message,
            fingerprint=fingerprint,
            problems=problems,
            question=text,
            chunks=chunks,
            reason=EscalatedQuery.Reason.ANSWER_TOO_LONG,
            latency_ms=latency_ms,
            reply=reply,
            cached=cached,
        )

    # **Cache only what passed.** The write used to happen immediately after the model
    # replied, so a reply the audit would reject was cached anyway and re-served for the
    # whole TTL: one bad generation turned into a refusal that reproduced exactly, and
    # read like a gap in the corpus (testing_hazards.md §1.31). A refusal is therefore
    # never cached — including a genuine one — which costs one model call when the same
    # unanswerable question is repeated and is the correct trade.
    if not cached:
        cache.set(
            cache_key,
            _reply_to_json(reply),
            timeout=int(getattr(settings, "CHAT_ANSWER_CACHE_TTL", ANSWER_CACHE_TTL)),
        )

    # D-3 and D78: the audit verified the quotes, not the claims built on them. An outcome
    # verdict the quotes do not state, and a cost answer that states no limit, are recorded
    # for a person, never used to refuse — the refusal would punish the visitor for a limit
    # of the audit (`§5.5`, G10).
    review_notes = outcome_claim_warnings(answer_text, citations) + cost_question_warnings(
        text, answer_text
    )
    if review_notes:
        logger.warning(
            "chatbot answer needs a person to read it",
            extra={
                "chat_session": str(session.public_uuid),
                "chat_review_notes": len(review_notes),
            },
        )

    with transaction.atomic():
        assistant = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=answer_text,
            latency_ms=latency_ms,
            model=reply.model,
            prompt_tokens=(0 if cached else reply.prompt_tokens),
            completion_tokens=(0 if cached else reply.completion_tokens),
            prompt_version=PROMPT_VERSION,
            corpus_fingerprint=fingerprint,
            citations=_citation_record(reply.citations, citations),
            refusal_checks=[],
            review_notes=list(review_notes),
            grounding=_grounding_snapshot(chunks),
        )
        assistant.retrieved_chunks.set([chunk.chunk_id for chunk in chunks])

    return GroundedAnswer(
        text=answer_text,
        citations=citations,
        insufficient_context=False,
        message_id=assistant.pk,
        cached=cached,
        lexical_only=bool(result.lexical_only),
    )


__all__ = [
    "ANSWER_SCHEMA",
    "CONFIGURATION_MESSAGE",
    "COST_QUESTION_RULE",
    "COST_LIMIT_PHRASES",
    "Citation",
    "AnswerTruncatedError",
    "ChatConfigurationError",
    "ChatError",
    "ChatModel",
    "GeminiChatModel",
    "GroundedAnswer",
    "InvalidQuestionError",
    "ModelReply",
    "OUTCOME_PHRASES",
    "RATE_LIMIT_MESSAGE",
    "REFUSAL",
    "RateLimitedError",
    "SessionNotFoundError",
    "TRUNCATED_MESSAGE",
    "UNAVAILABLE_MESSAGE",
    "answer_question",
    "attach_user",
    "audit_citations",
    "cost_question_warnings",
    "outcome_claim_warnings",
    "build_prompt",
    "build_retrieval_query",
    "check_rate_limit",
    "default_standard_set",
    "get_session",
    "locator_of",
    "normalise_question",
    "significant_terms",
    "start_session",
    "validate_question",
]
