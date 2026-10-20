"""The chat composer's keyboard and optimistic-turn contract, in a real browser.

The composer is a `<textarea>`, whose default Enter inserts a newline. The product
wants Enter to send (Shift+Enter for a new line), and it wants the visitor's message to
appear immediately while the answer is still being generated.

The POST is held by the route fixture rather than fulfilled at once: that is what makes
"the message appears before the response" testable. No request reaches Gemini.

Run explicitly (outside the gate):

    python -m pytest tests/e2e/test_chat_composer.py -q
"""

from __future__ import annotations

from urllib.parse import parse_qs

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

URL = "/ask/"
QUESTION = "can i use horse manure?"


@pytest.fixture
def composer(page, live_server):
    """The ask page with POSTs held; returns (page, held routes).

    A GET still reaches the live server, so the real template and both scripts load.
    A test fulfils the held route itself, which is how it can assert the optimistic
    bubble *before* the response exists.
    """
    posts = []

    def handle(route):
        if route.request.method == "POST":
            posts.append(route)
        else:
            route.continue_()

    page.route("**/ask/", handle)
    page.goto(live_server.url + URL, wait_until="networkidle")
    return page, posts


def _fulfil_ok(route):
    route.fulfill(
        status=200,
        content_type="text/html",
        body="<p id='fake-answer'>sent</p>",
    )


def test_enter_sends_and_shows_the_message_before_the_answer(composer):
    page, posts = composer
    question = page.locator("#id_question")

    question.fill(QUESTION)
    question.press("Enter")

    # The optimistic turn: the bubble is in the thread and the textarea is empty while
    # the request is still pending. The server fragment has not arrived yet.
    expect(page.locator(".chat__row--user .chat__bubble--user")).to_have_text(QUESTION)
    expect(question).to_have_value("")
    assert len(posts) == 1

    assert posts[0].request.post_data
    assert parse_qs(posts[0].request.post_data)["question"] == [QUESTION]

    _fulfil_ok(posts[0])
    expect(page.locator("#fake-answer")).to_be_visible()


def test_shift_enter_inserts_a_newline_instead_of_sending(composer):
    page, posts = composer
    question = page.locator("#id_question")

    question.fill("first line")
    question.press("Shift+Enter")

    expect(question).to_have_value("first line\n")
    assert posts == [], "Shift+Enter must not submit"

    question.press("Enter")
    expect(page.locator(".chat__row--user .chat__bubble--user")).to_have_text("first line")
    assert len(posts) == 1

    _fulfil_ok(posts[0])
    expect(page.locator("#fake-answer")).to_be_visible()


def test_a_rate_limited_question_is_put_back_in_the_box(composer):
    """A 429 rejects before the question is stored, so the thread cannot show it.

    Losing the typed question on a transient rate limit is the failure this guards.
    """
    page, posts = composer
    question = page.locator("#id_question")

    question.fill(QUESTION)
    question.press("Enter")
    expect(question).to_have_value("")

    posts[0].fulfill(
        status=429,
        content_type="text/html",
        body="<div class='chat__row'><div class='chat__bubble chat__bubble--refusal'>Too many questions. Try again in a minute.</div></div>",
    )

    expect(question).to_have_value(QUESTION)
    expect(page.get_by_text("Too many questions")).to_be_visible()


def test_a_question_typed_while_waiting_is_not_erased(composer):
    """The response must not clear the next question the visitor has started.

    The old `afterSwap` reset the form unconditionally. That was harmless while the
    text stayed in the box until the answer arrived; now the box is cleared on send, so
    a reset would delete a question typed during the wait.
    """
    page, posts = composer
    question = page.locator("#id_question")

    question.fill(QUESTION)
    question.press("Enter")
    expect(question).to_have_value("")

    question.fill("what about compost?")
    _fulfil_ok(posts[0])

    expect(page.locator("#fake-answer")).to_be_visible()
    expect(question).to_have_value("what about compost?")
