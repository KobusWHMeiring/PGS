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

#: Real laptop and phone viewports. The composer is the page's only control: if the
#: visitor has to scroll to reach it, the page has failed before the product starts.
#: Measured in the browser rather than reasoned about from the stylesheet, because a
#: page can be 40 px too tall without any test or linter noticing.
FOLD_VIEWPORTS = [
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 800},
    {"width": 390, "height": 844},
]


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


@pytest.mark.parametrize(
    "viewport",
    FOLD_VIEWPORTS,
    ids=[f"{v['width']}x{v['height']}" for v in FOLD_VIEWPORTS],
)
def test_the_composer_is_above_the_fold(browser, live_server, viewport):
    """The question box and its button are wholly visible without scrolling.

    `/ask/` opened with a four-sentence head band under the header, and the explainer
    below the header said the same thing as the aside beside the window. The band is
    now one line, so the whole window — thread, textarea and button — fits a 768 px
    laptop. That is a layout claim, and this is the only place it can be checked: the
    CSS reads correctly at every height, including the ones where it does not fit.
    """
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    page.goto(live_server.url + URL, wait_until="networkidle")

    box = page.locator("#chat-send").bounding_box()
    assert box is not None, "the Ask button is not laid out"
    bottom = box["y"] + box["height"]
    assert bottom <= viewport["height"], (
        f"the Ask button ends at {bottom:.0f} px on a {viewport['height']} px viewport — "
        "the visitor must scroll to ask a question"
    )
    context.close()


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


def test_the_waiting_state_is_visible_while_the_answer_is_generated(composer):
    """A grounded answer is a model call: measured median ~6 s, tail to ~41 s.

    A visitor who sees a dimmed button and nothing else for forty seconds concludes the page
    is broken. The thread therefore says what is happening, and the send button cannot be
    pressed twice while it does.
    """
    page, posts = composer
    question = page.locator("#id_question")

    question.fill(QUESTION)
    question.press("Enter")

    pending = page.locator(".chat__bubble--pending")
    expect(pending).to_be_visible()
    expect(pending).to_contain_text("Reading the documents")
    expect(pending).to_have_attribute("role", "status")
    assert page.locator("#chat-send").is_disabled(), "a second submit is still possible"

    _fulfil_ok(posts[0])

    expect(page.locator("#fake-answer")).to_be_visible()
    expect(page.locator(".chat__bubble--pending")).to_have_count(0)
    assert not page.locator("#chat-send").is_disabled(), "the button stayed disabled"


def test_the_waiting_state_admits_how_long_a_long_answer_takes(composer):
    """The slow path is not a spinner pretending to be progress — it says the number.

    The threshold is read from the form (`data-slow-after`), so this test shortens it rather
    than sleeping for eight seconds. The copy is the product's own claim about its latency;
    if the median ever changes, this sentence and `CHAT_TIMEOUT_MS` change together.
    """
    page, posts = composer
    page.eval_on_selector(".chat-form", "el => el.setAttribute('data-slow-after', '150')")
    question = page.locator("#id_question")

    question.fill(QUESTION)
    question.press("Enter")

    expect(page.locator(".chat__pending-text")).to_contain_text(
        "A long answer can take up to a minute", timeout=5000
    )

    _fulfil_ok(posts[0])
    expect(page.locator("#fake-answer")).to_be_visible()
