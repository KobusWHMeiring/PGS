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
  `latency_ms`, `model`), the chunks it was grounded on, and — since P2.5a — what it
  **claimed** (`citations`), which check refused it (`refusal_checks`) and a grounding
  **snapshot** that outlives the chunks. The M2M is **all** the retrieved chunks, not only
  the cited ones: when a refusal is reviewed, one useful question is "what did the
  retriever give the model?", and storing only citations hides it. The other useful
  question is "what did the model say it cited, and which check rejected it?" — G9 was
  that question, and nothing could answer it (`CHAT_ANSWER_COVERAGE_PRD.md` §G9).
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


class EscalationReason(models.TextChoices):
    """Why a turn was not answered. One value names one finding.

    Module level, not nested in `EscalatedQuery`, because `ChatMessage` records it too
    (a turn's own reason, without a join) and that class is defined first.

    Two of these used to cover more than one thing, and the record could not attribute
    the refusal it exists to attribute: `NO_CITATIONS` fired on four branches (no
    citations, empty answer, over `MAX_ANSWER_CHARS`, all duplicates) and
    `INSUFFICIENT_CONTEXT` on two (nothing retrieved, and the model judging the passages
    unusable). Split 2026-10-27 — `CHAT_TRUTHFULNESS_PRD.md` §4.1 and §5.9.
    """

    #: Nothing was retrieved, so the model was never called. A retrieval/key or corpus
    #: defect — not a coverage gap, which is what it used to imply.
    NO_RETRIEVAL = "NO_RETRIEVAL", "Nothing retrieved"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT", "Insufficient context"
    NO_CITATIONS = "NO_CITATIONS", "No valid citations"
    #: The model cited something the audit could not verify — a section that was not
    #: retrieved, a quote that is not a substring, or an invented `sub_ref`. Kept
    #: apart from `NO_CITATIONS` because they are different findings: one is a corpus
    #: gap, the other is a contract violation (`testing_hazards.md` §1.31).
    CITATION_AUDIT = "CITATION_AUDIT", "Citation audit refused"
    #: The citations verified and the answer text was blank.
    EMPTY_ANSWER = "EMPTY_ANSWER", "Empty answer"
    #: The answer ran past `MAX_ANSWER_CHARS` and was refused rather than truncated.
    ANSWER_TOO_LONG = "ANSWER_TOO_LONG", "Answer over the length cap"
    USER_REQUESTED = "USER_REQUESTED", "User requested"


#: What the visitor is told *after* the D17 refusal sentence, one line per reason.
#:
#: The refusal is fixed wording (D17), and on 2026-10-27 it was read exactly as written:
#: a visitor concluded "the standard doesn't define GM" when the cause was a citation
#: address, so the sentence was true about the assistant and misleading about the
#: documents. D5 approved a second sentence naming the cause; these are those sentences,
#: and the rule they follow is that **none of them claims the documents are silent unless
#: that is what happened**. They live on the model because they are the reason enum's own
#: copy and the thread renders them per message — not a service, not a template.
REFUSAL_NOTES = {
    EscalationReason.NO_RETRIEVAL: (
        "Nothing in the published documents matched this question, so it was not answered."
    ),
    EscalationReason.INSUFFICIENT_CONTEXT: (
        "Passages were found, but none of them answers this question as asked."
    ),
    EscalationReason.NO_CITATIONS: (
        "An answer came back with no passage to check it against, so it was not shown."
    ),
    EscalationReason.CITATION_AUDIT: (
        "Wording that may apply was found, but the citation could not be checked against "
        "the document, so the answer was not shown."
    ),
    EscalationReason.EMPTY_ANSWER: "The answer came back empty, so there was nothing to show.",
    EscalationReason.ANSWER_TOO_LONG: (
        "The answer ran longer than the assistant can check, so it was not shown."
    ),
    EscalationReason.USER_REQUESTED: "",
}


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

    # --- P2.5 + P2.5a: the answer becomes attributable *and* auditable ---------
    #
    # P2.5 records which contract and which corpus produced a row. P2.5a records what
    # the row claimed and which check refused it. Without the first, a stored answer
    # cannot be attributed after a re-ingest; without the second, a refusal on the live
    # surface is indistinguishable from a gap in the corpus — which is what G9 was, and
    # why it took a re-ask of the model to diagnose.

    prompt_version = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="The `PROMPT_VERSION` this turn was produced under.",
    )
    corpus_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text=(
            "The corpus it was grounded on — the same fingerprint the answer cache "
            "uses, so two corpora cannot produce indistinguishable rows."
        ),
    )
    citations = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "`{'raw': [...], 'accepted': [...]}`. `raw` is what the model returned, "
            "verbatim and in order; `accepted` is what the audit verified and the "
            "visitor was shown. Empty on a user message."
        ),
    )
    refusal_checks = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "The citation audit's `problems` — empty unless it refused. The distinction "
            "that matters: 'not present in the retrieved set' is a prompt-contract "
            "defect, 'the quote is not in the cited chunk' is a corpus defect."
        ),
    )
    grounding = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "A snapshot of the supplied passages (locator, page, heading, text sha). "
            "`--force` re-ingest drops the `retrieved_chunks` links, so the M2M cannot "
            "be the record of what an answer stood on."
        ),
    )
    refusal_reason = models.CharField(
        max_length=32,
        choices=EscalationReason.choices,
        blank=True,
        default="",
        help_text=(
            "Why this turn refused; empty when it answered. Denormalised from the "
            "escalation on purpose: the thread must not join per message, and the "
            "refusal sweeps group by this field (`CHAT_TRUTHFULNESS_PRD.md` §4)."
        ),
    )
    review_notes = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Advisory findings a person should read — never a reason to refuse. The "
            "first is a claim that states an outcome the verified quotes do not state "
            "(`outcome_claim_warnings`), which the audit cannot see: it checks quotes, "
            "not entailment (D-3)."
        ),
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

    @property
    def refusal_note(self) -> str:
        """The sentence that follows the D17 refusal, or "" when this turn answered.

        A property rather than a template conditional: the thread renders a turn, and the
        mapping from reason to words belongs with the reason (D5, 2026-10-27).
        """
        return REFUSAL_NOTES.get(self.refusal_reason, "")


class EscalatedQuery(models.Model):
    """A question the assistant would not answer, preserved for a human.

    `message` is `SET_NULL` rather than `CASCADE`: the escalation is the record of a
    gap in the corpus, and deleting a conversation must not erase the evidence that
    the gap exists. `question` therefore stands on its own.
    """

    #: The refusal reasons. The enum is module level because `ChatMessage` records the
    #: same value; this name is the one the rest of the code reads. An alias, not a
    #: re-declaration: assigning the members again would regenerate their labels and
    #: produce an `AlterField` that changes nothing a person should see.
    Reason = EscalationReason

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


class PublicQuestionQuerySet(models.QuerySet):
    """`published()` is the only filter a public view may use.

    Published means **a person published this question** — a slug exists and an administrator
    approved it. That is deliberately wider than "answered": a refusal the group is willing to
    show is the most honest row on the board, and it is published by the same act, with the same
    review, as an answer (D62/D64).
    """

    def published(self) -> PublicQuestionQuerySet:
        return self.filter(
            slug__isnull=False,
            status__in=[PublicQuestion.Status.APPROVED, PublicQuestion.Status.WAITING],
        )


class PublicQuestion(models.Model):
    """A question and its answer, kept because a person approved publishing it (D62).

    This is the board's **content store**, and it is not the answer cache: a cache entry is
    keyed on a normalised question, lives an hour and is not a record. A card is asked many
    times, checked on a date, approved by a named person, and reachable at a permalink.

    **`question` is the published wording, not the visitor's.** The administrator edits it
    before approving — that edit is where a third party's name comes out (D64). The original
    stays in `ChatMessage`, where D59 already governs its retention.

    `status` starts at `AWAITING` and only a person moves it. `REJECTED` hides rather than
    deletes, so "we decided not to publish this" stays answerable later; the `ask_count` on a
    rejected card keeps the demand behind that decision visible.

    The slug is **NULL until approval**, and generated from the *edited* question at that
    moment: a slug built at ask time would carry the third party's name into a public URL even
    after the administrator removed it from the text.
    """

    class Status(models.TextChoices):
        AWAITING = "AWAITING", "Awaiting review"
        APPROVED = "APPROVED", "Published"
        WAITING = "WAITING", "Waiting on a person"
        REJECTED = "REJECTED", "Not published"

    slug = models.SlugField(
        max_length=120,
        unique=True,
        null=True,
        blank=True,
        help_text="The public address, generated at approval from the edited question.",
    )
    question = models.TextField(help_text="The published wording, edited before approval.")
    asked_key = models.CharField(
        max_length=64,
        db_index=True,
        help_text=(
            "sha256 of the normalised question as the visitor typed it — the dedupe key. "
            "Separate from `question` because an administrator edits that one, and two "
            "visitors asking the same thing must not diverge when the wording is redacted."
        ),
    )
    answer = models.TextField(blank=True, default="")
    covers = models.TextField(
        blank=True,
        default="",
        help_text=(
            "What this answer does not cover, one item per line. The answer page requires it: "
            "an answer that states its boundary is the honest counterpart to a grounded quote."
        ),
    )
    citations = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "The accepted citations as they were shown — document_code, reading_anchor, "
            "section_ref, sub_ref, page, quote, document. A snapshot, not a lookup: the corpus "
            "can be re-ingested and this page must still say what was claimed."
        ),
    )
    topic = models.CharField(
        max_length=60,
        blank=True,
        default="",
        help_text=(
            "The board's filter chip, e.g. 'Inputs', 'Animals', 'Money'. Free text, not a "
            "choice list: adding a topic must not require a migration (build_principles §I)."
        ),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AWAITING,
        help_text="Only a person moves this. The public board reads APPROVED only.",
    )
    ask_count = models.PositiveIntegerField(
        default=1,
        help_text="How many times this question has been asked. Incremented, never recomputed.",
    )
    #: `auto_now` is deliberately not used: it would bump on an approval edit and report a false
    #: "last asked" date. The service writes it when a visitor actually asks.
    first_asked_at = models.DateTimeField(auto_now_add=True)
    last_asked_at = models.DateTimeField(db_index=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_questions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    checked_at = models.DateField(
        null=True,
        blank=True,
        help_text="When a person last verified the answer against the documents (D66).",
    )
    escalated_query = models.ForeignKey(
        EscalatedQuery,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="published_questions",
        help_text="Set on a Waiting card: the gap this question exposed.",
    )

    objects = PublicQuestionQuerySet.as_manager()

    class Meta:
        ordering = ["-last_asked_at", "-id"]
        indexes = [
            models.Index(fields=["status", "-last_asked_at"], name="ask_card_status_recent"),
            models.Index(fields=["topic"], name="ask_card_topic"),
        ]
        verbose_name = "public question"
        verbose_name_plural = "public questions"

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.question[:56]} ({self.status})"

    @property
    def is_published(self) -> bool:
        """True when a person published this question — answered or not.

        A `WAITING` card with a slug is a *gap page*: the group publishes the question and says
        the documents do not answer it. Without a slug it is still only a queue entry, visible
        to the administrator and to nobody else.
        """
        return self.slug is not None and self.status in {self.Status.APPROVED, self.Status.WAITING}

    @property
    def noindex(self) -> bool:
        """True unless the page is a published *answer*.

        A gap page stays reachable — it is where a Waiting card points — but it must not be
        indexed: a search result for a question the documents cannot answer is a promise we
        break.
        """
        return self.status != self.Status.APPROVED

    @property
    def summary(self) -> str:
        """The card's one-line summary: the answer's first sentence, capped.

        A property rather than a template filter chain: the board shows it and the answer page
        does not, and "everything up to the first full stop" is a boundary rule that belongs
        with the data (build_principles.md §II — no logic in templates).
        """
        text = " ".join((self.answer or "").split())
        if not text:
            return ""
        stop = text.find(". ")
        if 0 < stop < 160:
            return text[: stop + 1]
        if len(text) <= 160:
            return text
        return text[:157].rstrip() + "…"

    @property
    def covers_items(self) -> list[str]:
        """`covers` as the list the page renders. A template never splits a string."""
        return [line.strip() for line in (self.covers or "").splitlines() if line.strip()]
