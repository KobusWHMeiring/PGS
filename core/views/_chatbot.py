"""The chat surface — `/ask/`.

Thin by rule (`build_principles.md` §II): choose the session, validate one form, call
one service, render. Every refusal string and limit comes from
`core.services._chatbot`; no template or view holds a second copy that can drift.

Two response shapes from one view:

* a **plain form POST** returns the whole page, so the feature works with JavaScript
  disabled — a farm connection is not a reason for a broken page;
* an **HTMX POST** returns only the thread fragment, swapped inside `#chat-thread`.

The session is created on the first question, not on a page view. A visitor who reads
the page and leaves should not leave a row (or consume an IP budget) behind.
"""

from __future__ import annotations

import hashlib
import logging

from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from ipware import get_client_ip

from core.forms._chatbot import QuestionForm
from core.models import ChatSession
from core.services._chatbot import (
    CONFIGURATION_MESSAGE,
    RATE_LIMIT_MESSAGE,
    REFUSAL,
    TRUNCATED_MESSAGE,
    UNAVAILABLE_MESSAGE,
    AnswerTruncatedError,
    ChatConfigurationError,
    InvalidQuestionError,
    RateLimitedError,
    SessionNotFoundError,
    UpstreamModelError,
    answer_question,
    attach_user,
    get_session,
    start_session,
)
from core.services._public import public_context

logger = logging.getLogger(__name__)

#: The Django session key holding the conversation's public UUID. The UUID is what a
#: browser sees; the integer PK never leaves the database.
CHAT_SESSION_KEY = "chat_session_uuid"


def client_ip_hash(request) -> str:
    """In: a request. Out: sha256 of the client IP, or "" when it cannot be read.

    The raw address is never stored. The hash exists only to scope the rate limit, so
    a missing IP degrades to "not limited" rather than to a shared global bucket that
    would let one visitor exhaust everyone's budget.
    """
    ip, _routable = get_client_ip(request)
    if not ip:
        return ""
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def _session_from_request(request) -> ChatSession | None:
    """The conversation this browser already owns, or None. Never creates one."""
    raw = request.session.get(CHAT_SESSION_KEY)
    if not raw:
        return None
    try:
        return get_session(raw)
    except SessionNotFoundError:
        # A stale cookie after a database restore, or an edited value. A missing
        # conversation is not an error; it is a new one on the next question.
        request.session.pop(CHAT_SESSION_KEY, None)
        return None


def _start_session(request) -> ChatSession:
    session = start_session(
        user=request.user if request.user.is_authenticated else None,
        ip_hash=client_ip_hash(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    request.session[CHAT_SESSION_KEY] = str(session.public_uuid)
    return session


@require_http_methods(["GET", "POST"])
def ask(request):
    """GET the panel, or POST one question and render the exchange."""
    session = _session_from_request(request)
    answer = None
    error = ""
    status = 200
    retry_after: int | None = None
    form = QuestionForm(request.POST or None)

    if request.method == "POST":
        if not form.is_valid():
            # The form cap is the same 500 as the service; show Django's own message
            # rather than duplicating its wording here.
            error = " ".join(form.errors.get("question", ["Please ask a question."]))
        else:
            try:
                if session is None:
                    session = _start_session(request)
                elif request.user.is_authenticated and session.user_id is None:
                    session = attach_user(session.public_uuid, request.user)

                answer = answer_question(
                    session.public_uuid,
                    form.cleaned_data["question"],
                    ip_hash=session.ip_hash,
                )
            except ChatConfigurationError:
                logger.error("chatbot: no default StandardSet is seeded")
                error, status = CONFIGURATION_MESSAGE, 503
            except RateLimitedError as exc:
                error, status = RATE_LIMIT_MESSAGE.format(seconds=exc.retry_after), 429
                retry_after = exc.retry_after
            except AnswerTruncatedError:
                # The model answered and was cut at the output cap. Nothing is down, so
                # "try again later" would be false; the visitor can act on this one.
                logger.warning("chatbot: answer truncated at the output cap")
                error = TRUNCATED_MESSAGE
            except UpstreamModelError:
                # Never a fabricated answer. The question may have been recorded
                # before the call failed; `messages` below shows what did happen.
                logger.exception("chatbot: generation provider failed")
                error, status = UNAVAILABLE_MESSAGE, 503
            except InvalidQuestionError as exc:
                error = str(exc)
            except SessionNotFoundError:
                # The row disappeared between the cookie lookup and the service call
                # (a restore, an admin cleanup). A stale conversation is not a 500.
                error = "This conversation has expired. Please ask the question again."

    messages = list(session.messages.all()) if session is not None else []
    context = public_context("ask") | {
        "form": form,
        "session": session,
        "messages": messages,
        "answer": answer,
        "error": error,
        "refusal": REFUSAL,
    }

    template = (
        "chatbot/_thread.html"
        if request.headers.get("HX-Request") == "true"
        else "chatbot/panel.html"
    )
    response = render(request, template, context, status=status)
    if retry_after is not None:
        response["Retry-After"] = str(retry_after)
    return response
