"""`/building/` — the roadmap (D74).

The route is in `core/tests/test_public.PAGES`, so the generic public sweeps already cover it:
200, its own `<title>`, `lang`, no unrendered template syntax, no CDN, no dead internal link,
unresolvable static asset. **And `test_claim_discipline.py` sweeps it with no exemption** — the
claim list is the reason a curated board is safe, and an exemption entry would be the way to
lose that.

What only this file can assert is that the page is a **subset of the curated set** and that it
is not a window into the notebook. Three failures are silent in a browser:

1. **A field that is not a card.** `**Status:**` routinely says "superseded" or "blocking
   decisions", and a date beside every item invites a reader to judge velocity. Both render
   perfectly and are wrong.
2. **A card that came from nowhere.** The board may only show what `product/backlog.py`
   classified as public — a hardcoded card in a template would be a lie with no PRD behind it.
3. **An empty board that renders as a broken layout.** Deleting every `**Public:** yes` is a
   supported state; it must produce a sentence, not four empty headings.
"""

from __future__ import annotations

import re

import pytest
from django.test import Client
from django.utils.html import escape

from core.services import _board
from core.services._board_data import CURATED

pytestmark = pytest.mark.django_db


def test_every_published_card_is_on_the_page(client: Client):
    """The page shows the artefact, all of it. If this fails, the deploy is stale."""
    html = client.get("/building/").content.decode()

    assert CURATED, "no PRD carries `Public: yes` — this test would otherwise assert nothing"
    for row in CURATED:
        assert row["title"] in html, f"card {row['title']!r} is missing from /building/"
        assert row["summary"] in html, f"summary for {row['title']!r} is missing"


def test_the_page_renders_the_column_titles_from_the_service(client: Client):
    """Titles come from `COLUMN_TITLES`, so there is one place to rename a column."""
    html = client.get("/building/").content.decode()
    rendered = re.findall(r'<h2 class="board__title"[^>]*>([^<]+)</h2>', html)

    occupied = [row["column"] for row in CURATED]
    expected = [_board.COLUMN_TITLES[key] for key in _board.COLUMN_ORDER if key in occupied]
    assert expected, "no column to check"
    assert rendered == expected
    assert rendered == sorted(rendered, key=expected.index), "columns are out of board order"


def test_no_prd_header_field_reaches_the_page(client: Client):
    """`Status`, `Owner` and `Last Updated` are notes to ourselves, and one of them is a date.

    Asserted on the artefact rather than by grepping the tree: the artefact is what the page
    reads, so this also fails if a future generator change starts copying header fields into it.
    """
    html = client.get("/building/").content.decode()

    for row in CURATED:
        assert set(row) == {"title", "summary", "column", "updated"}, (
            "the artefact carries a field a card must not have"
        )
        assert row["updated"] not in html, f"the ordering date {row['updated']} is rendered"

    for field in ("Status:", "Owner:", "Last Updated:", "Public:"):
        assert field not in html, f"{field!r} leaked into /building/"


def test_the_page_states_what_it_is_not(client: Client):
    """A roadmap beside a certificate is an easy thing to over-read, so the page says so.

    The OPP's "membership is not certification" rule applied to a new surface: a card is not a
    promise about any farm.
    """
    html = client.get("/building/").content.decode()
    assert 'class="board__standpoint"' in html
    # Escaped, because the sentence carries an apostrophe: `"farm's"` renders as `&#x27;`, so a
    # raw substring comparison fails on a page that is correct (found by this test failing).
    assert escape(_board.STANDPOINT) in html


def test_an_empty_board_says_so_instead_of_rendering_nothing(client: Client, monkeypatch):
    """Deleting every `**Public:** yes` and regenerating is a supported state.

    Without the branch the page would render its head, a standpoint line and then nothing —
    which reads as a broken template rather than as "nothing is published yet".
    """
    monkeypatch.setattr(_board, "CURATED", ())

    html = client.get("/building/").content.decode()

    assert _board.EMPTY_MESSAGE in html
    assert 'class="board"' not in html, "an empty board still rendered the grid"
    assert "board__title" not in html


def test_a_card_is_not_a_link(client: Client):
    """No card is clickable: the only honest target would be a public explainer per item,
    which does not exist, and a card that opened a PRD would put the notebook on the site."""
    html = client.get("/building/").content.decode()
    cards = re.findall(r'<li class="board__card">.*?</li>', html, re.S)

    assert cards, "no cards rendered — this test would otherwise pass vacuously"
    for card in cards:
        assert "<a " not in card, f"a card contains a link: {card[:120]}"
