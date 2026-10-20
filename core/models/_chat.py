"""Chat history and escalation — the user-owned side of the grounded assistant.

`knowledge/` owns the corpus and retrieval; this module owns what a **person** asked
and what the assistant answered. The split is deliberate (SPEC §4.6):
`knowledge` has no users, sessions or views, and chat has no idea how retrieval
works — it consumes a scoped result and records it.

Three models, and each carries a decision rather than a default:

- **`ChatSession`** is pinned to a `StandardSet`. The corpus boundary is therefore a
  property of the conversation, not a rule the model has to remember: a session that
  started against SAOSO v2.1 keeps answering from that set even after the deployment
  ingests v2.2. `user` is nullable so an anonymous visitor can chat; the same row is
  kept when that visitor creates an account (SPEC §3.1 — a public visitor graduates,
  they do not start over).
- **`ChatMessage`** stores both sides of every exchange, what it cost (`tokens`,
  `latency_ms`, `model`) and the chunks it was grounded on. The M2M is **all** the
  retrieved chunks, not only the cited ones: when a refusal is reviewed, the useful
  question is "what did the retriever give the model?", and storing only citations
  hides it.
- **`EscalatedQuery`** is the refusal made followable. A refusal is not an error
  state — it is the product's central claim (SPEC §13) — so it produces a row an
  administrator can answer, with the question preserved even if the message is
  later deleted.

`public_uuid`, never the integer PK, is the value a browser sees. `§I` forbids a
sequential id on a public surface, and a chat session id appears in a cookie, a form
and a log line.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    """One conversation, scoped to one corpus.

    `standard_set` is `PROTECT`, not `CASCADE`: a corpus that a live conversation was
    started against must not be deletable while its citations are still part of the
    record. Retiring a corpus is a data decision, not a cascade.
    """

    public_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text="The identifier the browser sees. Never the sequential primary key.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_sessions",
        help_text="Null for an anonymous public visitor; attached when they sign up.",
    )
    standard_set = models.ForeignKey(
        "knowledge.StandardSet",
        on_delete=models.PROTECT,
        related_name="chat_sessions",
        help_text="The corpus this conversation is pinned to (SPEC §4.5/§4.6).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ip_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=(
            "sha256 of the client IP — never the raw address. Used only for the "
            "per-IP rate limit, so a blank value is a session with no limit."
        ),
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Truncated for support; not a security signal.",
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"chat {self.public_uuid}"

    @property
    def uuid(self) -> uuid.UUID:
        """Alias used by service callers: `answer_question(session.uuid, …)`."""
        return self.public_uuid


class ChatMessage(models.Model):
    """One turn. Assistant messages carry their cost and their evidence."""

    class Role(models.TextChoices):
        USER = "USER", "User"
        ASSISTANT = "ASSISTANT", "Assistant"

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    latency_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Retrieval + generation time. Null on a user message.",
    )
    model = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="The generation model, blank on a user message or a cache hit.",
    )
    prompt_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Provider-reported prompt tokens; null when unknown.",
    )
    completion_tokens = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Provider-reported completion tokens; null when unknown.",
    )
    retrieved_chunks = models.ManyToManyField(
        "knowledge.DocumentChunk",
        blank=True,
        related_name="chat_messages",
        help_text="Everything the retriever supplied, cited or not.",
    )

    class Meta:
        # `created_at` alone is not a stable order: two rows written in the same
        # millisecond would render in an arbitrary order. The id breaks the tie.
        ordering = ["created_at", "id"]

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.role}: {self.content[:48]}"

    @property
    def is_user(self) -> bool:
        return self.role == self.Role.USER


class EscalatedQuery(models.Model):
    """A question the assistant would not answer, preserved for a human.

    `message` is `SET_NULL` rather than `CASCADE`: the escalation is the record of a
    gap in the corpus, and deleting a conversation must not erase the evidence that
    the gap exists. `question` therefore stands on its own.
    """

    class Reason(models.TextChoices):
        INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT", "Insufficient context"
        NO_CITATIONS = "NO_CITATIONS", "No valid citations"
        USER_REQUESTED = "USER_REQUESTED", "User requested"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ANSWERED = "ANSWERED", "Answered"
        CLOSED = "CLOSED", "Closed"

    message = models.ForeignKey(
        ChatMessage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="escalations",
    )
    question = models.TextField(
        help_text="The question as asked. Survives deletion of the message.",
    )
    reason = models.CharField(max_length=32, choices=Reason.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
    )
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="answered_escalations",
    )
    answer = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "escalated query"
        verbose_name_plural = "escalated queries"

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.reason}: {self.question[:48]}"

    @property
    def is_open(self) -> bool:
        return self.status == self.Status.OPEN
