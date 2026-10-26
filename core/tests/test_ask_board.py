"""The ask board — consent, the four states, and the one path that publishes.

The prototype pinned the contract (`d61a_ask_board_refinement.html`, *What the checkbox does*),
so the states are tested as states rather than through one happy path. The rule underneath all
of them is D64: **a visitor can create a card and cannot publish one.**
"""

from __future__ import annotations

from datetime import date

import pytest

from core.models import ChatMessage, ChatSession, EscalatedQuery, PublicQuestion
from core.services._ask import (
    approve,
    asked_key_for,
    board_context,
    record_public_question,
    reject,
)
from core.services._chatbot import REFUSAL, Citation, GroundedAnswer
from core.views import _chatbot as chat_view

pytestmark = pytest.mark.django_db

URL = "/ask/"

GROUNDED = "The standard does not name cardboard; it governs it as a by-product."
QUOTE = "Biodegradable processing by-products, plant or animal origin."


def _citation(**overrides) -> Citation:
    fields = {
        "section_ref": "Appendix 2",
        "quote": QUOTE,
        "chunk_id": 1,
        "page": 76,
        "heading_path": "APPENDICES > Appendix 2",
        "document": "SAOSO Standard v2.1",
        "document_code": "saoso-standard-v2.1",
        "reading_anchor": "appendix-2",
    }
    fields.update(overrides)
    return Citation(**fields)


def _grounded(session_uuid, question, *, ip_hash="") -> GroundedAnswer:
    session = ChatSession.objects.get(public_uuid=session_uuid)
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content=question)
    assistant = ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.ASSISTANT, content=GROUNDED
    )
    return GroundedAnswer(
        text=GROUNDED, citations=[_citation()], message_id=assistant.pk
    )


def _refusal(session_uuid, question, *, ip_hash="") -> GroundedAnswer:
    session = ChatSession.objects.get(public_uuid=session_uuid)
    ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content=question)
    assistant = ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.ASSISTANT, content=REFUSAL
    )
    # A real row, because `record_public_question` sets the FK and the database checks it: a
    # made-up id would fail here for the right reason but prove nothing about the link.
    escalation = EscalatedQuery.objects.create(
        message=assistant,
        question=question,
        reason=EscalatedQuery.Reason.CITATION_AUDIT,
    )
    return GroundedAnswer(
        text=REFUSAL,
        insufficient_context=True,
        escalated_query_id=escalation.pk,
        message_id=assistant.pk,
    )


@pytest.fixture
def grounded(monkeypatch):
    monkeypatch.setattr(chat_view, "answer_question", _grounded)


@pytest.fixture
def refused(monkeypatch):
    monkeypatch.setattr(chat_view, "answer_question", _refusal)


@pytest.fixture
def administrator(django_user_model):
    """The person who publishes. A role grant is asserted where the admin checks it."""
    return django_user_model.objects.create_user(username="administrator", password="x")


@pytest.fixture
def card(db) -> PublicQuestion:
    from django.utils import timezone

    return PublicQuestion.objects.create(
        question="Can I use cardboard?",
        asked_key=asked_key_for("Can I use cardboard?"),
        answer=GROUNDED,
        citations=[_citation().__dict__],
        last_asked_at=timezone.now(),
    )


def post_question(client, question: str, *, publish: bool):
    payload = {"question": question}
    if publish:
        payload["publish"] = "on"
    return client.post(URL, payload)


# --- The model's most important default -------------------------------------


def test_a_card_defaults_to_unpublished(db):
    """The one default that carries the consent promise.

    Asserted directly, because every board test below approves its own fixture first — a
    migration that flipped this default would leave them all green (testing_hazards.md §1.6).
    """
    from django.utils import timezone

    card = PublicQuestion.objects.create(
        question="Can I use cardboard?", asked_key="k", last_asked_at=timezone.now()
    )

    assert card.status == PublicQuestion.Status.AWAITING
    assert card.slug is None, "an unpublished card has no public address"
    assert not card.is_published
    assert card.noindex


# --- The four states --------------------------------------------------------


def test_a_consenting_grounded_question_waits_for_a_person(client, chat_standard_set, grounded):
    """The label promises an administrator reads it, so the code has to keep that promise."""
    post_question(client, "Can I use cardboard from my neighbour?", publish=True)

    card = PublicQuestion.objects.get()
    assert card.status == PublicQuestion.Status.AWAITING
    assert card.citations, "the card must carry the clauses it was approved on"
    assert card.slug is None


def test_a_consenting_refusal_becomes_a_waiting_card(client, chat_standard_set, refused):
    """A refusal is a *state*, never an error (SPEC §13) — and on the board it is the most
    valuable row there is: the visible list of what the documents do not settle."""
    post_question(client, "Do I need EU certification to export to Germany?", publish=True)

    card = PublicQuestion.objects.get()
    assert card.status == PublicQuestion.Status.WAITING
    assert card.escalated_query_id, "a Waiting card must point at the escalation it records"


def test_an_unticked_box_publishes_nothing(client, chat_standard_set, grounded):
    post_question(client, "Can I use cardboard from my neighbour?", publish=False)

    assert PublicQuestion.objects.count() == 0


def test_the_same_question_twice_is_one_card_asked_twice(client, chat_standard_set, grounded):
    """Dedupe on the *visitor's* wording, not the published wording.

    An administrator may redact a question before approving it; a second visitor asking the
    same thing must still find that card, and a redaction must not orphan the count.
    """
    post_question(client, "Can I use cardboard?", publish=True)
    post_question(client, "can i use   CARDBOARD?", publish=True)

    assert PublicQuestion.objects.count() == 1
    assert PublicQuestion.objects.get().ask_count == 2


# --- The board --------------------------------------------------------------


@pytest.fixture
def cards(card, administrator):
    """One card per status, each with a name that only its own state can produce."""
    card.question = "Do I need to know where my horse manure comes from?"
    card.topic = "Animals"
    card.save(update_fields=["question", "topic"])
    publish(card, administrator)

    money = PublicQuestion.objects.create(
        question="What is the yearly cost to get certified?",
        asked_key="k-money",
        answer=GROUNDED,
        topic="Money",
        last_asked_at=card.last_asked_at,
    )
    publish(money, administrator)

    awaiting = PublicQuestion.objects.create(
        question="Awaiting question", asked_key="k-awaiting", last_asked_at=card.last_asked_at
    )
    rejected = PublicQuestion.objects.create(
        question="Rejected question", asked_key="k-rejected", last_asked_at=card.last_asked_at
    )
    reject(rejected.pk, user=administrator)

    waiting = PublicQuestion.objects.create(
        question="Waiting question",
        asked_key="k-waiting",
        status=PublicQuestion.Status.WAITING,
        last_asked_at=card.last_asked_at,
    )
    publish(waiting, administrator)
    return {"manure": card, "money": money, "awaiting": awaiting, "waiting": waiting}


def publish(card: PublicQuestion, user) -> PublicQuestion:
    return approve(card.pk, user=user, topic=card.topic or "Inputs")


def test_the_board_shows_published_cards_and_no_others(client, cards):
    body = client.get(URL).content.decode()

    assert "Do I need to know where my horse manure comes from?" in body
    assert "Waiting question" in body, "a published gap stays visible — that is the shape"
    for hidden in ("Awaiting question", "Rejected question"):
        assert hidden not in body


def test_the_composer_comes_first(client, cards):
    """D62: the page is called *ask*, so the box precedes the library."""
    body = client.get(URL).content.decode()

    assert body.index('id="id_question"') < body.index("Questions we have answered")


def test_the_filter_is_a_url_parameter(client, cards):
    """`build_principles.md` §IV — context preservation: a filter is state in the URL."""
    body = client.get(f"{URL}?topic=Animals").content.decode()

    assert "Do I need to know where my horse manure comes from?" in body
    assert "What is the yearly cost to get certified?" not in body


def test_an_empty_board_says_so_honestly(client, chat_standard_set):
    body = client.get(URL).content.decode()

    assert "No questions have been published yet" in body


# --- Only a person publishes ------------------------------------------------


def test_approval_generates_the_slug_from_the_edited_question(card, administrator):
    """The slug follows the *published* wording — that is what redaction is for."""
    approved = approve(
        card.pk,
        user=administrator,
        question="Can I use a neighbour's cardboard?",
        topic="Inputs",
        covers="Whether your supply is contaminated.",
    )

    assert approved.slug == "can-i-use-a-neighbours-cardboard"
    assert approved.status == PublicQuestion.Status.APPROVED
    assert approved.checked_at == date.today()


def test_re_approval_bumps_the_checked_date_and_changes_nothing_else(card, administrator):
    """D66: a re-check is an act with a date on it, and the URL does not move."""
    first = publish(card, administrator)
    slug, approved_at = first.slug, first.approved_at
    PublicQuestion.objects.filter(pk=card.pk).update(checked_at=date(2020, 1, 1))

    again = approve(card.pk, user=administrator)

    assert again.slug == slug, "a permalink that moves is not a permalink"
    assert again.approved_at == approved_at
    assert again.checked_at == date.today()


def test_a_rejected_card_stays_hidden_and_keeps_the_demand(
    client, chat_standard_set, grounded, card, administrator
):
    reject(card.pk, user=administrator)

    assert card.question not in client.get(URL).content.decode()

    post_question(client, card.question, publish=True)

    card.refresh_from_db()
    assert card.status == PublicQuestion.Status.REJECTED
    assert card.ask_count == 2, "the demand behind a rejection is evidence too"


def test_no_visitor_reachable_route_publishes(client, chat_standard_set, grounded):
    """The consent label's promise, asserted structurally.

    Every POST a visitor can reach goes through `record_public_question`, so the assertion is
    that after a consenting ask nothing is published and nothing has a slug.
    """
    post_question(client, "Can I use cardboard from my neighbour?", publish=True)
    post_question(client, "What does the standard say about manure?", publish=True)

    assert not PublicQuestion.objects.published().exists()
    assert not PublicQuestion.objects.exclude(slug=None).exists()
    # Belt and braces: a card may not even claim `APPROVED`. `published()` needs a slug, so a
    # status leak alone would still render nothing — which is why the status is asserted
    # directly rather than inferred from the absence of a page.
    assert not PublicQuestion.objects.filter(
        status=PublicQuestion.Status.APPROVED
    ).exists()


def test_board_context_counts_what_is_waiting_on_a_person(cards):
    context = board_context()

    assert context["card_count"] == 3  # two answers and one published gap
    assert context["waiting_count"] == 1
    assert set(context["topics"]) == {"Animals", "Money", "Inputs"}


def test_recording_is_idempotent_at_the_service_boundary(chat_session):
    """A repeat inside one session is one card, asked twice — the same rule as two visitors."""
    from django.utils import timezone

    session = chat_session
    message = ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.ASSISTANT, content=GROUNDED
    )
    answer = GroundedAnswer(
        text=GROUNDED, citations=[_citation()], message_id=message.pk
    )
    first = record_public_question(question="Can I use cardboard?", answer=answer)
    second = record_public_question(question="Can I use cardboard?", answer=answer)

    assert first.pk == second.pk
    assert second.ask_count == 2
    assert PublicQuestion.objects.count() == 1
    assert second.last_asked_at >= timezone.now().replace(microsecond=0)
