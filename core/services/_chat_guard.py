"""The guards and the session: who may ask, what a question is, and which corpus answers.

Split out of `_chatbot.py` (CONTEXT_CUTS_PRD step 5). Two jobs share a module because they
share a question -- *is this turn allowed to happen at all?* Rate limiting, validation and
the follow-up decision decide that before retrieval; `default_retrieval`, `default_standard_set`
and the session helpers decide *against what* it happens. None of it judges an answer, and
none of it talks to a model.

`looks_like_follow_up` **fails closed**: anything it cannot recognise is a new question,
which is the behaviour before stage 1 -- a miss costs nothing, and carrying a stale subject
into retrieval is the failure with a price.
"""

from __future__ import annotations

import time
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError

from core.models import ChatSession, User
from core.services._chat_prompt import significant_terms
from core.services._chat_text import _content_words, _words, normalise_question
from core.services._chat_values import (
    ChatConfigurationError,
    InvalidQuestionError,
    RateLimitedError,
    SessionNotFoundError,
)
from knowledge.models import StandardSet
from knowledge.retrieval import search_terms
from knowledge.services import RetrievalResult, chunks_by_id

#: Defaults. Every one is read through `getattr(settings, ...)` at call time, so a test or
#: a deployment can override it with `override_settings`/an environment variable.
MAX_QUESTION_CHARS = 500
#: How many passages the model is given, when the setting is absent. **`settings` always
#: defines `CHAT_RETRIEVAL_LIMIT`**, so this value is a fallback and not the live budget --
#: see `chat_retrieval_limit()`. The 2026-10-21 answer-coverage work raised this constant
#: from 5 to 8 believing it was the budget; the product kept running at 5
#: (`testing_hazards.md` §2.7). Read the limit through the function, never from here.
RETRIEVAL_LIMIT = 8
RATE_LIMIT = 20
RATE_LIMIT_WINDOW_SECONDS = 3600


# --- Session lifecycle ------------------------------------------------------


def chat_retrieval_limit() -> int:
    """The one retrieval budget: the setting, falling back to `RETRIEVAL_LIMIT`.

    In:  nothing.
    Out: how many passages the model is given.

    A function rather than a constant so that the view path and every measuring
    instrument read the *same* number. `scripts/probe_chat.py` used to hardcode 8 while
    the product used 5, and printed a grounded answer for a question `/ask/` refuses —
    the instrument measured a path the product does not have (`testing_hazards.md` §2.7).
    """
    return int(getattr(settings, "CHAT_RETRIEVAL_LIMIT", RETRIEVAL_LIMIT))


def default_retrieval(
    question: str,
    standard_set: StandardSet,
    *,
    limit: int | None = None,
    context_query: str = "",
) -> RetrievalResult:
    """Retrieve the passages a question is answered from.

    In:  the visitor's question; the corpus to search; optionally an explicit `limit`
         (used by the probe's `--limit` when comparing budgets); `context_query` — the
         previous question, when this turn continues it. The caller decides that
         (`answer_question` uses `looks_like_follow_up`); retrieval does not guess.
    Out: a `RetrievalResult`; `limit` defaults to `chat_retrieval_limit()`.

    This is the single retrieval path: `answer_question()` calls it, and
    `scripts/probe_chat.py` calls it too, so a measurement cannot drift from the product.
    """
    return search_terms(
        significant_terms(question),
        standard_set=standard_set,
        question=question,
        limit=chat_retrieval_limit() if limit is None else limit,
        context_query=context_query,
    )


def default_standard_set() -> StandardSet:
    """The corpus a new conversation starts against.

    In:  nothing.
    Out: the single `is_default=True` set.
    Fails: `ChatConfigurationError` when it is missing or ambiguous. Guessing would
        put another standard's text behind the assistant's answers (SPEC Â§4.5).
    """
    defaults = StandardSet.objects.filter(is_default=True)
    count = defaults.count()
    if count != 1:
        raise ChatConfigurationError(
            f"Expected exactly one default StandardSet, found {count}. "
            "Run `python manage.py seed_deployment` before serving the chat."
        )
    return defaults.get()


def start_session(
    *,
    user: User | None = None,
    standard_set: StandardSet | None = None,
    ip_hash: str = "",
    user_agent: str = "",
) -> ChatSession:
    """Create a conversation pinned to a corpus.

    In:  `user` (or None), `standard_set` (defaults to the deployed corpus),
         `ip_hash` (sha256 of the client IP, never the address), `user_agent`.
    Out: a persisted `ChatSession`.
    Fails: `ChatConfigurationError` when no default set is seeded.
    """
    return ChatSession.objects.create(
        user=user,
        standard_set=standard_set or default_standard_set(),
        ip_hash=ip_hash[:64],
        user_agent=user_agent[:255],
    )


def get_session(session_uuid: uuid.UUID | str) -> ChatSession:
    """Resolve a public UUID or raise the service's own error.

    A malformed UUID is a missing session, not a 500: the value comes from a cookie
    and a stale or edited one must fall back to "no conversation".
    """
    try:
        return ChatSession.objects.select_related("standard_set").get(
            public_uuid=session_uuid
        )
    except (ChatSession.DoesNotExist, ValueError, TypeError, ValidationError) as error:
        raise SessionNotFoundError(f"No chat session {session_uuid!r}.") from error


def attach_user(session_uuid: uuid.UUID | str, user: User) -> ChatSession:
    """Attach a signed-in user to an existing (usually anonymous) conversation.

    In:  `session_uuid`; `user`.
    Out: the same `ChatSession`, with `user` set.
    Side Effects: one `UPDATE` when the session had no user.
    Fails: `SessionNotFoundError`.
    Idempotency: yes â€” attaching the same user twice changes nothing, and a session
        that already has a different user is left alone rather than reassigned.
    """
    session = get_session(session_uuid)
    if session.user_id is None:
        session.user = user
        session.save(update_fields=["user"])
    return session


# --- Guardrails -------------------------------------------------------------


def _now() -> float:
    """The clock, isolated so a rate-limit test can hand it a fixed time."""
    return time.time()


def _rate_limit() -> int:
    return int(getattr(settings, "CHAT_RATE_LIMIT", RATE_LIMIT))


def _rate_window() -> int:
    return int(getattr(settings, "CHAT_RATE_LIMIT_WINDOW_SECONDS", RATE_LIMIT_WINDOW_SECONDS))


def check_rate_limit(ip_hash: str, *, now: float | None = None) -> None:
    """Count one question against the client's fixed window.

    In:  `ip_hash` â€” sha256 of the IP; `now` â€” injectable clock.
    Out: None.
    Side Effects: one cache increment.
    Fails: `RateLimitedError` when the count exceeds `CHAT_RATE_LIMIT`.

    A blank `ip_hash` is not rate-limited: it means the caller is not a public
    request (a test, a management command). The public view always supplies one.
    """
    if not ip_hash:
        return

    limit = _rate_limit()
    window = _rate_window()
    timestamp = _now() if now is None else now
    bucket = int(timestamp // window)
    key = f"chat:rate:{ip_hash}:{bucket}"

    # `add` is atomic and gives us the first count; `incr` is atomic thereafter. A
    # key that expires between the two raises ValueError, which is a new window, not
    # an error.
    if cache.add(key, 1, timeout=window):
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=window)
            count = 1

    if count > limit:
        retry_after = int(window - (timestamp % window)) or window
        raise RateLimitedError(retry_after)


def validate_question(question: str) -> str:
    """In: raw question text. Out: the stripped question.
    Fails: `InvalidQuestionError` when blank or over `CHAT_MAX_QUESTION_CHARS`."""
    text = (question or "").strip()
    cap = int(getattr(settings, "CHAT_MAX_QUESTION_CHARS", MAX_QUESTION_CHARS))
    if not text:
        raise InvalidQuestionError("Please ask a question.")
    if len(text) > cap:
        raise InvalidQuestionError(
            f"Please keep the question to {cap} characters or fewer."
        )
    return text


#: Openers that only make sense as a continuation. Matched against the question's
#: leading words with punctuation removed, so `why?` and `and for goats?` both land.
FOLLOW_UP_OPENERS = (
    "and ",
    "also ",
    "but ",
    "then ",
    "so ",
    "why ",
    "what about",
    "what if",
    "how about",
    "does that",
    "does it",
    "do that",
    "is that",
    "is it",
    "can that",
    "can it",
    "would that",
    "will that",
    "should that",
)

#: Pronouns and demonstratives. A short question containing one of these is pointing at
#: the previous answer; a long one has its own subject and merely uses the word.
FOLLOW_UP_ANAPHORS = frozenset(
    {"it", "its", "that", "this", "they", "them", "those", "these", "same"}
)

#: An anaphor is only evidence while the question is short. Twelve words is a sentence.
FOLLOW_UP_MAX_WORDS = 12

#: "Short" for the shared-term rule. Six content words is a noun phrase with a verb.
FOLLOW_UP_MAX_TERMS = 6

#: A shared word shorter than this is a verb or a preposition-like filler ("use", "get"),
#: not the subject of the question. Without it "Can I use KNF preparations?" reads as a
#: follow-up of "Can I use cardboard?" purely on the word "use".
FOLLOW_UP_MIN_SHARED = 4


def looks_like_follow_up(question: str, parent_question: str) -> bool:
    """Does `question` continue `parent_question`, or is it a new question?

    In:  the question just typed; the previous *user* question in the conversation
         (empty when there is none).
    Out: True when the question cannot stand on its own.
    Fails: never. **It fails closed** — anything it cannot recognise is a new question,
         which is exactly the behaviour before stage 1, so a wrong answer costs nothing
         and a right one is the only way to gain.

    Why a heuristic instead of the visitor's choice: they know least about what they are
    asking at the moment they would have to choose. Two mistakes are possible here and
    they are not equal. A missed follow-up falls back to today's behaviour. A false
    positive carries one stale subject into retrieval, which is why the context arm
    `search_terms` adds is capped at two passages and displaces the weakest match
    rather than splitting the budget.

    The three signals, in order, and the reasons for each:

    1. **An opener** — `what if`, `and`, `why`. The strongest single signal, because the
       phrase is incomplete by construction.
    2. **An anaphor in a short question** — `it`, `that`, `those`. Something outside the
       sentence is the subject.
    3. **Short and sharing a distinctive word** — "does manure apply to goats too?".
       Length is part of the test: a long question has enough of its own subject that
       overlap is topical, not referential.
    """
    normalised = normalise_question(question)
    if not parent_question or not normalised:
        return False

    # Asking the same question twice is not a follow-up: it is the same question, and
    # treating it as a follow-up would key it to its own history and miss the cache the
    # repeat exists to hit. A follow-up has to add something.
    if normalised == normalise_question(parent_question):
        return False

    words = _words(normalised)
    if not words:
        return False

    if (" ".join(words) + " ").startswith(FOLLOW_UP_OPENERS):
        return True

    if len(words) <= FOLLOW_UP_MAX_WORDS and any(word in FOLLOW_UP_ANAPHORS for word in words):
        return True

    content = _content_words(normalised)
    if len(content) > FOLLOW_UP_MAX_TERMS:
        return False

    parent_words = set(_content_words(parent_question))
    return any(
        word in parent_words and len(word) >= FOLLOW_UP_MIN_SHARED for word in content
    )


def build_retrieval_query(question: str) -> str:
    """Turn a natural-language question into a lexical OR query.

    In:  the user's question.
    Out: `"term OR term OR …"`. Falls back to the raw question when every token is a
         stopword, so a query like "the why" still does something rather than
         silently retrieving nothing.
    Fails: never.

    The default retrieval path uses `significant_terms` directly (see
    `search_terms`); this string is kept for diagnostics and for the narrow case where
    a single OR query is the right tool.
    """
    tokens = significant_terms(question)
    if not tokens:
        return question
    return " OR ".join(tokens)
