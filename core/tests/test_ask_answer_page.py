"""The answer page — one question, one URL, and the boundary stated on it.

The page exists to make an answer quotable. Four properties are asserted here because each is
a decision rather than a rendering detail:

* only a **published** card has a page (`AWAITING`/`REJECTED` are 404 even with a slug, because
  a guessable URL is not a review);
* a **gap page** is reachable and `noindex` (a search result for a question we cannot answer is
  a promise we break, a 404 at the end of a visible card is a dead end we created);
* **"what this answer does not cover"** is rendered — D65 makes it required;
* the **citation is text**, so it survives a phone with JavaScript disabled.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from core.models import PublicQuestion
from core.services._ask import approve, reject

pytestmark = pytest.mark.django_db

QUESTION = "Can I use cardboard from my neighbour?"
QUOTE = "Biodegradable processing by-products, plant or animal origin."


def citation(**overrides) -> dict:
    record = {
        "section_ref": "Appendix 2",
        "sub_ref": None,
        "page": 76,
        "document": "SAOSO Standard v2.1",
        "quote": QUOTE,
        "chunk_id": 1,
        "document_code": "saoso-standard-v2.1",
        "reading_anchor": "appendix-2",
    }
    record.update(overrides)
    return record


@pytest.fixture
def administrator(django_user_model):
    return django_user_model.objects.create_user(username="administrator", password="x")


@pytest.fixture
def published_card(db, administrator) -> PublicQuestion:
    from django.utils import timezone

    card = PublicQuestion.objects.create(
        question=QUESTION,
        asked_key="k-cardboard",
        answer="The standard does not name cardboard; it governs it as a by-product.",
        covers="Whether your supply is contaminated.\nRecord keeping for inputs.",
        citations=[citation()],
        topic="Inputs",
        last_asked_at=timezone.now(),
    )
    return approve(card.pk, user=administrator, topic="Inputs")


@pytest.fixture
def waiting_card(db, administrator) -> PublicQuestion:
    from django.utils import timezone

    card = PublicQuestion.objects.create(
        question="Do I need EU organic certification to export to Germany?",
        asked_key="k-export",
        status=PublicQuestion.Status.WAITING,
        last_asked_at=timezone.now(),
    )
    return approve(card.pk, user=administrator)


def page_url(card: PublicQuestion) -> str:
    return reverse("core:ask_answer", kwargs={"slug": card.slug})


def test_a_published_card_has_a_page_with_its_clauses(client, published_card):
    body = client.get(page_url(published_card)).content.decode()

    assert published_card.question in body
    assert QUOTE in body
    assert "Read it in the document" in body
    assert "/documents/saoso-standard-v2.1/read/#appendix-2" in body


def test_the_page_states_what_the_answer_does_not_cover(client, published_card):
    """D65: mandatory, not optional. A grounded quote with no boundary is half an answer."""
    body = client.get(page_url(published_card)).content.decode()

    assert "What this answer does not cover" in body
    assert "Whether your supply is contaminated." in body


def test_an_awaiting_card_has_no_page_even_with_a_slug(client, db):
    """`AWAITING` is not a page with a notice; it is not a page.

    A 200 would put unread visitor text at a public URL the moment someone guessed the slug,
    and the consent label says an administrator reads it first.
    """
    from django.utils import timezone

    card = PublicQuestion.objects.create(
        question="An unapproved question",
        asked_key="k-awaiting",
        slug="an-unapproved-question",
        last_asked_at=timezone.now(),
    )

    assert client.get("/ask/an-unapproved-question/").status_code == 404
    assert card.status == PublicQuestion.Status.AWAITING


def test_a_rejected_card_has_no_page(client, db, administrator):
    from django.utils import timezone

    card = PublicQuestion.objects.create(
        question="A rejected question",
        asked_key="k-rejected",
        answer="Something.",
        last_asked_at=timezone.now(),
    )
    approved = approve(card.pk, user=administrator)
    reject(approved.pk, user=administrator)

    assert client.get(page_url(card)).status_code == 404


def test_a_waiting_card_has_a_page_that_is_not_indexed(client, waiting_card):
    response = client.get(page_url(waiting_card))
    body = response.content.decode()

    assert response.status_code == 200
    assert 'name="robots" content="noindex' in body
    assert "administrator" in body.lower()
    assert "do not answer this" in body


def test_a_published_answer_is_indexable(client, published_card):
    body = client.get(page_url(published_card)).content.decode()

    assert 'name="robots"' not in body


def test_the_page_carries_membership_is_not_certification(client, published_card):
    """OPP requirement: the statement appears wherever questions or answers are listed."""
    body = client.get(page_url(published_card)).content.decode()

    assert "Membership is not certification" in body


def test_the_citation_is_selectable_without_javascript(client, published_card):
    """The copy button is a convenience; the citation text is the feature.

    A page that kept the citation in a `data-` attribute or a JS template would be uncopyable
    without JavaScript — a shape farms actually use.
    """
    body = client.get(page_url(published_card)).content.decode()

    assert QUOTE in body
    assert 'id="cite-text"' in body
    assert "data-copy-target" in body


def test_the_page_offers_the_questions_next_to_it(client, published_card, db, administrator):
    from django.utils import timezone

    sibling = PublicQuestion.objects.create(
        question="Can I use straw mulch?",
        asked_key="k-straw",
        answer="Straw is listed with crop residues.",
        topic="Inputs",
        last_asked_at=timezone.now(),
    )
    approve(sibling.pk, user=administrator, topic="Inputs")

    body = client.get(page_url(published_card)).content.decode()

    assert "Questions next to this one" in body
    assert "Can I use straw mulch?" in body
    assert sibling.question not in published_card.question
