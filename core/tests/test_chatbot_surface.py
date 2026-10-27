"""Task D5 — the chat surface at `/ask/`.

The surface has two jobs, and both are asserted here:

1. **It works without JavaScript.** A plain `<form method="post">` returns the whole
   page with the answer. HTMX is a progressive enhancement, not the only path — a
   public site used on a farm connection cannot require it.
2. **HTMX is loaded only where it is used.** A single vendored file on `/ask/`, and
   no page that does not need it pays for it (acceptance in `MVP0_PLAN_V2` D5).

The view is thin (`build_principles.md` §II): it selects the session, calls one
service, and renders. The service is monkeypatched here because D2–D4 already prove
its behaviour; what this file proves is the HTTP contract — 200, 429, 503, a fragment
for HTMX, the full document for a plain POST.
"""

from __future__ import annotations

import pytest
from django.test import override_settings
from django.urls import reverse

from core.models import ChatMessage, ChatSession, EscalatedQuery, REFUSAL_NOTES
from core.services._chatbot import (
    CONFIGURATION_MESSAGE,
    REFUSAL,
    TRUNCATED_MESSAGE,
    UNAVAILABLE_MESSAGE,
    AnswerTruncatedError,
    Citation,
    GroundedAnswer,
    RateLimitedError,
    UpstreamModelError,
)
from core.tests.test_public import PAGES
from core.views import _chatbot as chat_view

pytestmark = pytest.mark.django_db

URL = "/ask/"


def _fragment_for(session_uuid, question, *, refusal=False):
    """Write the rows the real service would write, and return its answer value."""
    session = ChatSession.objects.get(public_uuid=session_uuid)
    ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.USER, content=question
    )
    content = REFUSAL if refusal else "Records must let a product be traced."
    assistant = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content=content,
        # `_as_refusal` records the reason on the turn, and the template reads it: a
        # refusal written without it renders as an answer and loses the contact link
        # (the §1.32 hazard — a fixture that omits what the writer sets).
        refusal_reason=(
            EscalatedQuery.Reason.CITATION_AUDIT if refusal else ""
        ),
    )
    if refusal:
        return GroundedAnswer(
            text=REFUSAL,
            insufficient_context=True,
            escalated_query_id=1,
            message_id=assistant.pk,
        )
    return GroundedAnswer(
        text=content,
        citations=[
            Citation(
                section_ref="S20.1.1",
                quote="Traceability is required for every batch of organic product.",
                chunk_id=1,
                page=43,
                heading_path="Traceability",
                document="SAOSO Standard v2.1",
                document_code="saoso-standard-v2.1",
                reading_anchor="s20-1-1",
            )
        ],
        message_id=assistant.pk,
    )


@pytest.fixture
def answering(monkeypatch):
    """Patch the view's one service call with a grounded exchange."""
    monkeypatch.setattr(
        chat_view,
        "answer_question",
        lambda session_uuid, question, *, ip_hash="": _fragment_for(
            session_uuid, question
        ),
    )


@pytest.fixture
def refusing(monkeypatch):
    monkeypatch.setattr(
        chat_view,
        "answer_question",
        lambda session_uuid, question, *, ip_hash="": _fragment_for(
            session_uuid, question, refusal=True
        ),
    )


# --- The page ---------------------------------------------------------------


def test_the_ask_page_renders_a_real_form(client, chat_standard_set):
    response = client.get(URL)

    assert response.status_code == 200
    html = response.content.decode()
    assert "Ask the standard" in html
    assert 'name="question"' in html
    assert 'maxlength="500"' in html
    assert "csrfmiddlewaretoken" in html, "a state-changing endpoint without CSRF"
    assert f'hx-post="{URL}"' in html
    assert "htmx.min.js" in html
    assert "js/chat.js" in html


def test_the_first_get_does_not_create_a_session(client, chat_standard_set):
    """A page view is not a conversation; the row is created when a question is asked."""
    client.get(URL)
    assert ChatSession.objects.count() == 0


def test_htmx_is_loaded_only_on_the_chat_page(client, chat_standard_set):
    assert PAGES, "an empty page list would make this test vacuously green"
    for _name, url, _heading in PAGES:
        if url == URL:
            continue
        html = client.get(url).content.decode().lower()
        assert "htmx.min.js" not in html, f"HTMX is loaded on {url}, which does not use it"


# --- Graceful degradation ---------------------------------------------------


def test_a_plain_form_post_returns_a_whole_page(client, chat_standard_set, answering):
    """JavaScript disabled: the browser posts, the server answers, the page reloads."""
    response = client.post(URL, {"question": "What does the standard require for traceability?"})

    assert response.status_code == 200
    html = response.content.decode()
    assert "<!DOCTYPE html>" in html
    assert "Records must let a product be traced." in html
    assert ChatSession.objects.count() == 1


def test_an_htmx_post_returns_only_the_thread(client, chat_standard_set, answering):
    response = client.post(
        URL,
        {"question": "What does the standard require for traceability?"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    html = response.content.decode()
    assert "<!DOCTYPE html>" not in html, "HTMX received a whole document"
    assert "Records must let a product be traced." in html
    assert 'id="chat-thread"' not in html, "the fragment is swapped inside the container"


def test_the_same_conversation_is_reused_across_posts(client, chat_standard_set, answering):
    client.post(URL, {"question": "What does the standard require for traceability?"})
    client.post(URL, {"question": "What about records?"})

    assert ChatSession.objects.count() == 1
    assert ChatMessage.objects.filter(session=ChatSession.objects.get()).count() == 4


def test_the_history_is_rendered_on_a_later_get(client, chat_standard_set, answering):
    client.post(URL, {"question": "What does the standard require for traceability?"})
    html = client.get(URL).content.decode()

    assert "What does the standard require for traceability?" in html
    assert "Records must let a product be traced." in html


# --- Refusal ----------------------------------------------------------------


def test_a_refusal_renders_the_contact_link_and_the_boundary(client, chat_standard_set, refusing):
    response = client.post(URL, {"question": "Which fertiliser brand should I buy?"})
    html = response.content.decode()

    assert response.status_code == 200
    assert REFUSAL in html
    assert "administrator" in html.lower()
    assert reverse("core:contact") in html


def test_a_refusal_names_its_cause_and_does_not_blame_the_documents(
    client, chat_standard_set, refusing
):
    """D5: the fixed sentence plus one that says what happened.

    The refusal alone was read as a claim about the corpus — a visitor concluded "the
    standard doesn't define GM" when the audit had refused a correct answer for an
    address. `CITATION_AUDIT` must not say the documents are silent.
    """
    response = client.post(URL, {"question": "Which fertiliser brand should I buy?"})
    html = response.content.decode()

    assert REFUSAL_NOTES[EscalatedQuery.Reason.CITATION_AUDIT] in html
    assert REFUSAL_NOTES[EscalatedQuery.Reason.NO_RETRIEVAL] not in html, (
        "the wrong reason's sentence was rendered — the note is read from the turn"
    )
    assert "chat__bubble__note" in html, "the note is rendered as the explanation, not the refusal"


def test_a_citation_is_rendered_with_its_quote(client, chat_standard_set, answering):
    response = client.post(URL, {"question": "What does the standard require for traceability?"})
    html = response.content.decode()

    assert "S20.1.1" in html
    assert "Traceability is required for every batch" in html, (
        "the quote is the checkable part of a citation"
    )


def test_a_citation_opens_the_line_it_quotes_in_a_new_tab(client, chat_standard_set, answering):
    """D68 §7.2: "View this line" is a place, "Read it in SAOSO" is a file. The hidden suffix is
    the mitigation for a phone, where a new tab is otherwise invisible."""
    response = client.post(URL, {"question": "What does the standard require for traceability?"})
    html = response.content.decode()

    assert "View this line" in html
    assert 'target="_blank"' in html
    assert 'rel="noopener"' in html
    assert "(opens in a new tab)" in html
    assert (
        'href="/documents/saoso-standard-v2.1/read/?section=s20-1-1#s20-1-1"' in html
    ), "the branch must travel in the query string; the fragment only scrolls"


# --- Failure modes are honest ----------------------------------------------


def test_an_over_long_question_is_rejected_without_calling_the_service(
    client, chat_standard_set, monkeypatch
):
    def boom(*args, **kwargs):  # pragma: no cover - only when the guard fires
        raise AssertionError("the service was called for an invalid question")

    monkeypatch.setattr(chat_view, "answer_question", boom)

    response = client.post(URL, {"question": "x" * 600})

    assert response.status_code == 200
    assert "500" in response.content.decode()
    assert ChatSession.objects.count() == 0


def test_a_rate_limited_request_returns_429(client, chat_standard_set, monkeypatch):
    def limited(*args, **kwargs):
        raise RateLimitedError(retry_after=42)

    monkeypatch.setattr(chat_view, "answer_question", limited)

    response = client.post(URL, {"question": "What is the membership fee?"})

    assert response.status_code == 429
    assert response["Retry-After"] == "42"
    assert "try again" in response.content.decode().lower()


def test_an_upstream_failure_returns_503_and_never_a_guess(
    client, chat_standard_set, monkeypatch
):
    def down(*args, **kwargs):
        raise UpstreamModelError("Gemini is down")

    monkeypatch.setattr(chat_view, "answer_question", down)

    response = client.post(URL, {"question": "What is the membership fee?"})

    assert response.status_code == 503
    assert UNAVAILABLE_MESSAGE in response.content.decode()


def test_a_truncated_generation_says_so_instead_of_blaming_the_service(
    client, chat_standard_set, monkeypatch
):
    """The model was reachable and answered; it ran past the cap.

    Reporting that as 503 "try again later" is false and pointless — the same question
    will truncate again. The visitor gets something they can act on.
    """

    def cut_short(*args, **kwargs):
        raise AnswerTruncatedError("Gemini truncated the reply")

    monkeypatch.setattr(chat_view, "answer_question", cut_short)

    response = client.post(URL, {"question": "What is the membership fee?"})
    html = response.content.decode()

    assert response.status_code == 200, (
        "nothing is unavailable, so a 5xx would be a lie the JS has to work around"
    )
    assert TRUNCATED_MESSAGE in html
    assert UNAVAILABLE_MESSAGE not in html, "the model was reachable"
    assert REFUSAL not in html, "a fragment is not a refusal about the corpus"


def test_no_seeded_corpus_returns_503_not_an_empty_answer(client):
    """The deployment, not the visitor, is wrong. Say so without blaming them."""
    response = client.post(URL, {"question": "What is the membership fee?"})

    assert response.status_code == 503
    assert CONFIGURATION_MESSAGE in response.content.decode()


# --- Session identity -------------------------------------------------------


def test_an_anonymous_session_records_a_hash_not_an_ip(client, chat_standard_set, answering):
    client.post(
        URL,
        {"question": "What does the standard require for traceability?"},
        REMOTE_ADDR="203.0.113.9",
        HTTP_USER_AGENT="a real browser",
    )

    session = ChatSession.objects.get()
    assert session.user is None
    assert len(session.ip_hash) == 64
    assert "203.0.113.9" not in session.ip_hash
    assert session.user_agent == "a real browser"


def test_an_authenticated_visitor_is_attached_to_the_session(
    client, chat_standard_set, answering, user_factory
):
    user = user_factory()
    client.force_login(user)

    client.post(URL, {"question": "What does the standard require for traceability?"})

    assert ChatSession.objects.get().user == user


def test_the_header_links_to_the_ask_page(client):
    """The chat is reachable from every page, not only the home showcase and footer."""
    html = client.get("/").content.decode()
    nav = html.split('<nav class="site-nav"', 1)[1].split("</nav>", 1)[0]
    assert 'href="/ask/"' in nav
    assert ">Ask<" in nav


def test_the_ask_nav_link_marks_itself_current(client):
    import re

    html = client.get(URL).content.decode()
    nav = html.split('<nav class="site-nav"', 1)[1].split("</nav>", 1)[0]
    anchor = re.search(
        r'<a class="site-nav__link" href="/ask/"[^>]*>Ask</a>', nav, re.S
    )
    assert anchor, "the Ask nav link is missing or changed shape"
    assert 'aria-current="page"' in anchor.group(0)
