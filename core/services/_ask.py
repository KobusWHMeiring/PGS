"""The ask board — the questions a person allowed us to publish (D62, D64–D66).

`_chatbot.py` owns answering; this module owns *keeping*. The split is the PRD's own
requirement: **the cache is not the archive.** A cache entry is keyed on a normalised question
and dies in an hour; a card is asked many times, checked on a date, approved by a named person,
and reachable at a permalink.

**Nothing a visitor reaches publishes anything.** `record_public_question` writes an `AWAITING`
row — or, for a refusal, a `WAITING` one — and `approve` is reachable only from the admin. That
asymmetry is the consent label's entire meaning: the control says *an administrator reads it
before it appears*, so the code path a visitor can reach must never set `APPROVED`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core.models import PublicQuestion
from core.services._chatbot import GroundedAnswer, citation_records, normalise_question

#: How many cards one answer page offers as "questions next to this one".
NEIGHBOURS = 3


def asked_key_for(question: str) -> str:
    """The dedupe key: the visitor's wording, normalised. Case and spacing only.

    Deliberately *not* the published wording: an administrator edits that one, and two
    visitors asking the same thing must not queue two cards because a redaction changed the
    text of the first.
    """
    return hashlib.sha256(normalise_question(question).encode("utf-8")).hexdigest()


def _refused(answer: GroundedAnswer) -> bool:
    """A refusal is a state, not an error: no verified citation means no grounded answer."""
    return answer.insufficient_context or not answer.citations


@transaction.atomic
def record_public_question(*, question: str, answer: GroundedAnswer) -> PublicQuestion | None:
    """Keep a question the visitor consented to publish, without publishing it.

    In:  `question` — as the visitor typed it; `answer` — the `GroundedAnswer` the chat
         service just produced (its text, citations, refusal flag and escalation id).
    Out: the card, or None when nothing was recorded (an empty question).
    Side effects: creates or updates one `PublicQuestion` row.
    Fails: never deliberately — a board failure must not break a visitor's answer.
    Idempotency: on the normalised question. A repeat increments `ask_count`; it does not
        queue a second card, and it never re-publishes one an administrator rejected.

    The four states, and why each is what it is:

    * grounded + consent → `AWAITING`. A person must read it (D64).
    * refusal + consent  → `WAITING`, pointing at its `EscalatedQuery`. The gap becomes
      visible and counted instead of disappearing with the session.
    * already on the board → `ask_count += 1` and `last_asked_at` moves. A `REJECTED` card is
      **not** resurrected: the decision was a person's, and the count is how the next reviewer
      sees the demand behind it.
    * a `WAITING` card asked again, now answerable → the answer is stored and the card returns
      to `AWAITING`. The corpus changed; a person still decides whether to publish.
    """
    question = " ".join(question.split())
    if not question:
        return None
    key = asked_key_for(question)
    refused = _refused(answer)
    now = timezone.now()

    card = (
        PublicQuestion.objects.select_for_update()
        .filter(asked_key=key)
        .exclude(status=PublicQuestion.Status.REJECTED)
        .first()
    )
    if card is not None:
        card.ask_count += 1
        card.last_asked_at = now
        fields = ["ask_count", "last_asked_at"]
        if refused and card.status == PublicQuestion.Status.AWAITING:
            card.status = PublicQuestion.Status.WAITING
            fields.append("status")
        if not refused and card.status == PublicQuestion.Status.WAITING:
            card.answer = answer.text
            card.citations = citation_records(answer.citations)
            card.status = PublicQuestion.Status.AWAITING
            fields += ["answer", "citations", "status"]
        if answer.escalated_query_id and card.escalated_query_id is None:
            card.escalated_query_id = answer.escalated_query_id
            fields.append("escalated_query")
        card.save(update_fields=fields)
        return card

    rejected = PublicQuestion.objects.select_for_update().filter(asked_key=key).first()
    if rejected is not None:
        # The demand is still evidence, and it is the only thing that changes: the card stays
        # unpublished, and the count keeps the decision honest for the next reviewer.
        rejected.ask_count += 1
        rejected.last_asked_at = now
        rejected.save(update_fields=["ask_count", "last_asked_at"])
        return rejected

    return PublicQuestion.objects.create(
        asked_key=key,
        question=question,
        answer="" if refused else answer.text,
        citations=[] if refused else citation_records(answer.citations),
        status=PublicQuestion.Status.WAITING if refused else PublicQuestion.Status.AWAITING,
        last_asked_at=now,
        escalated_query_id=answer.escalated_query_id,
    )


def _slug_for(question: str) -> str:
    """A public address from the published wording, suffixed rather than reused."""
    base = slugify(question)[:100].strip("-") or "question"
    candidate, n = base, 2
    while PublicQuestion.objects.filter(slug=candidate).exists():
        candidate, n = f"{base}-{n}", n + 1
    return candidate


@transaction.atomic
def approve(
    card_id: int,
    *,
    user,
    question: str | None = None,
    topic: str | None = None,
    covers: str | None = None,
    answer: str | None = None,
) -> PublicQuestion:
    """Publish a card. The only path to `APPROVED`, and it requires a person.

    In:  the card id; the administrator; optionally the edited wording, topic, *what this does
         not cover*, and answer text.
    Out: the updated card, now with a slug and a `checked_at` date.
    Side effects: one row.
    Fails: `PublicQuestion.DoesNotExist` for an unknown id.
    Idempotency: yes — re-approving keeps the slug and `approved_at`, and merely bumps
        `checked_at` (D66: re-checking a card is an explicit act with a date on it).
    """
    card = PublicQuestion.objects.select_for_update().get(pk=card_id)
    for field, value in (
        ("question", question),
        ("topic", topic),
        ("covers", covers),
        ("answer", answer),
    ):
        if value is not None:
            setattr(card, field, value)
    if not card.slug:
        card.slug = _slug_for(card.question)
    # Publishing is one act; *answering* is a different one. A card the documents cannot answer
    # is published as a gap page (noindex) rather than held back: the PRD's argument is that a
    # visible gap is the product's honesty, and a reviewed gap is as publishable as a reviewed
    # answer.
    card.status = (
        PublicQuestion.Status.APPROVED
        if card.answer.strip()
        else PublicQuestion.Status.WAITING
    )
    card.approved_by = user
    card.approved_at = card.approved_at or timezone.now()
    card.checked_at = timezone.localdate()
    card.save()
    return card


@transaction.atomic
def reject(card_id: int, *, user) -> PublicQuestion:
    """Stop publishing a card. Hidden, never deleted — the decision stays answerable."""
    card = PublicQuestion.objects.select_for_update().get(pk=card_id)
    card.status = PublicQuestion.Status.REJECTED
    card.save(update_fields=["status"])
    return card


def board_context(topic: str = "") -> dict:
    """In: an optional topic. Out: the board's context. Three queries.

    Only `APPROVED` cards are cards; the others are *counted* so the page can say how many
    questions are waiting on a person — the number that makes the Waiting state credible
    rather than decorative.
    """
    published = PublicQuestion.objects.published()
    shown = published.filter(topic=topic) if topic else published
    return {
        "cards": list(shown[:24]),
        "topics": list(
            published.exclude(topic="")
            .order_by("topic")
            .values_list("topic", flat=True)
            .distinct()
        ),
        "topic": topic,
        "card_count": published.count(),
        "waiting_count": PublicQuestion.objects.filter(
            status=PublicQuestion.Status.WAITING
        ).count(),
    }


@dataclass(frozen=True)
class AnswerPage:
    """One card as a page. `gap` is true for a Waiting card, which renders boundary copy."""

    card: PublicQuestion
    citations: tuple[dict, ...]
    neighbours: tuple[PublicQuestion, ...]
    cite_text: str
    gap: bool


def _cite_text(card: PublicQuestion) -> str:
    """The citation as it should read pasted into a message, a FORM, or to a neighbour.

    Built from the stored snapshot, never from the corpus: the page must still be able to say
    what it claimed after a re-ingest, and a citation that silently re-resolves is a citation
    nobody can audit.
    """
    parts = []
    for citation in card.citations or ():
        if not isinstance(citation, dict):
            continue
        locator = citation.get("sub_ref") or citation.get("section_ref") or ""
        page = f" (p.{citation['page']})" if citation.get("page") else ""
        parts.append(
            f"{citation.get('document', '')}, {locator}{page}: "
            f"\u201c{citation.get('quote', '')}\u201d"
        )
    return "\n".join(parts)


def answer_page(slug: str) -> AnswerPage | None:
    """In: a slug. Out: the page, or None when there is nothing to show.

    In:  `slug` — the public address generated at approval.
    Out: an `AnswerPage` for an `APPROVED` card, a `gap=True` page for a `WAITING` one, and
        **None** for `AWAITING`/`REJECTED`/unknown — the caller 404s.
    Side effects: at most two queries.
    Fails: never deliberately.
    """
    card = PublicQuestion.objects.filter(
        slug=slug,
        status__in=[PublicQuestion.Status.APPROVED, PublicQuestion.Status.WAITING],
    ).first()
    if card is None:
        return None
    others = PublicQuestion.objects.published().exclude(pk=card.pk)
    neighbours = list((others.filter(topic=card.topic) if card.topic else others)[:NEIGHBOURS])
    return AnswerPage(
        card=card,
        citations=tuple(card.citations or ()),
        neighbours=tuple(neighbours),
        cite_text=_cite_text(card),
        gap=card.status == PublicQuestion.Status.WAITING,
    )


__all__ = [
    "AnswerPage",
    "asked_key_for",
    "approve",
    "answer_page",
    "board_context",
    "record_public_question",
    "reject",
]
