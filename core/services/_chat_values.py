"""The chatbot's vocabulary: what it returns, what it raises, what a provider must be.

Split out of `_chatbot.py` (CONTEXT_CUTS_PRD step 2, amended 2026-11-03). The audit
constructs a `Citation` and the provider returns a `ModelReply`, so if either module had
imported `_chatbot` for them the audit, the provider and the contract would import each
other in a circle. These types are the floor the rest stands on: no queries, no prompt
text, no policy.

`_chatbot` re-imports every name, so `from core.services._chatbot import Citation` keeps
working everywhere it already does -- views, forms, `_ask`, the eval scripts, the tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence
from urllib.parse import quote_plus

from django.urls import reverse

from core.models import ChatMessage
from knowledge.services import RetrievedChunk


# --- Errors -----------------------------------------------------------------


class ChatError(RuntimeError):
    """Base class: a caller can catch the family without catching a bug."""


class InvalidQuestionError(ChatError, ValueError):
    """The question is blank or over the cap. No model call, no rows."""


class SessionNotFoundError(ChatError):
    """The session UUID does not name a session â€” never a silent new conversation."""


class ChatConfigurationError(ChatError):
    """The deployment has no default `StandardSet`; the corpus was never seeded."""


class RateLimitedError(ChatError):
    """The per-IP budget is exhausted. Carries the seconds a caller should wait."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, int(retry_after))
        super().__init__(
            f"rate limit reached; retry after {self.retry_after} seconds"
        )


class UpstreamModelError(ChatError):
    """Gemini failed. Never converted into an answer."""


class AnswerTruncatedError(UpstreamModelError):
    """The provider stopped at the output cap, so the reply is a fragment.

    A subclass because every caller that already refuses to invent a fallback on
    `UpstreamModelError` must keep doing so; the distinct name exists so the view can
    say *what* happened instead of telling the visitor the service is down.
    """


# --- Values -----------------------------------------------------------------


@dataclass(frozen=True)
class Citation:
    """One verified citation. Every field came from the retrieved chunk, not the model.

    The model supplies only `section_ref`, an optional `sub_ref`, and the quote. The
    rest is attached from the stored chunk so a template cannot render a document
    title or page number the model made up.
    """

    section_ref: str
    quote: str
    chunk_id: int
    sub_ref: str | None = None
    page: int | None = None
    anchor: str = ""
    heading_path: str = ""
    document: str = ""
    #: The public document's URL code (`PublicDocument.code`), resolved by the caller through
    #: provenance rather than guessed from the title. Empty when the group does not publish the
    #: document the clause came from — and then a template renders text, never a dead link.
    document_code: str = ""
    #: The fragment the reader lands on. The first passage of a shared reference keeps the
    #: reference itself; later ones are named for their own words, so the anchor is a property
    #: of the text and survives a `--force` re-ingest (`CONCORDANCE_PRD` §10.7).
    reading_anchor: str = ""
    #: The printed label of the row this citation quotes, when the passage is a row of a
    #: reviewed table (`D79` option E). It is **not** part of the quote: the page prints it
    #: in the row's first column, and a citation that shows it shows context, which is how a
    #: reader learns that `900` is a renewal fee without the corpus repeating a heading.
    row_label: str = ""
    #: The printed heading of the column the quoted cell sits under, resolved from the same
    #: reviewed table (`column_label_for`). Empty when the quote spans several cells, or when
    #: the passage is not a reviewed row: a heading the reader cannot reconcile with the
    #: quoted text is the failure mode `D79` falls back to option A for.
    column_label: str = ""

    @property
    def read_url(self) -> str:
        """The reader URL this citation lands on, or "" when its document is not published.

        A property rather than a `reverse()` in a template: `_thread.html` and the answer page
        both render a citation, and two call sites assembling one URL is two things to keep
        in step. The failure mode is silent — a link that 200s on the wrong document.
        """
        if not self.document_code:
            return ""
        # `?section=` **and** the fragment: a browser never sends the fragment to the server, so
        # the branch has to be chosen by a query parameter, and the fragment is what scrolls the
        # reader to the passage itself.
        #
        # `quote=` rides along only when the citation has a row context (`D79` option E). The
        # reader then marks the row and the cell the quote occupies, and names the column — the
        # counterpart of the context line beside the quote here, from the same printed table.
        url = (
            reverse("core:document_reader", kwargs={"code": self.document_code})
            + f"?section={self.reading_anchor}"
        )
        if self.row_label and self.quote:
            url += f"&quote={quote_plus(self.quote)}"
        return f"{url}#{self.reading_anchor}"

    @property
    def locator(self) -> str:
        """What the reader can look up: the sub-ref when present, else the section."""
        return self.sub_ref or self.section_ref


@dataclass(frozen=True)
class ModelReply:
    """What a generation provider must return. No Django objects, so it is cacheable."""

    answer: str
    citations: tuple[dict, ...] = ()
    insufficient_context: bool = False
    model: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True)
class GroundedAnswer:
    """The service contract. `text` is either a grounded answer or exactly `REFUSAL`."""

    text: str
    citations: list[Citation] = field(default_factory=list)
    insufficient_context: bool = False
    escalated_query_id: int | None = None
    message_id: int | None = None
    cached: bool = False
    lexical_only: bool = False

    @property
    def has_row_context(self) -> bool:
        """True when at least one citation carries a reviewed row (`D79` option E).

        The legend that separates context from quotation is printed **once per answer**, not
        once per citation: a citation chip is already dense, and a reader who has read the
        sentence does not need it again above the next quote. Done here rather than in the
        template because `any()` is logic, and templates display (`build_principles.md` §II).
        """
        return any(citation.row_label for citation in self.citations)


class ChatModel(Protocol):
    """What `answer_question` needs from a generation provider. Tests supply a fake."""

    name: str

    def answer(
        self,
        *,
        question: str,
        chunks: Sequence[RetrievedChunk],
        history: Sequence[ChatMessage],
    ) -> ModelReply:  # pragma: no cover - structural protocol
        ...
