"""The arbitration surface, driven in a real browser.

Same reason as `test_shape_review_artefact.py`: every check in `tests/tools/` passes even if the
page's script throws, and a page that throws is a page whose export button does nothing
(`testing_hazards.md` §1.30). So this file asserts only what the **script** produces — that a card
takes a verdict, that the export refuses an unfinished page and names what is missing, and that a
finished export is a file `shape_review_signoff.py --amend` recognises.

Run explicitly (outside the gate — `verify.sh` has no browser):

    python -m pytest tests/e2e/test_shape_arbitration_artefact.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import shape_arbitration, shape_review_signoff

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def artefact(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("arbitrate") / "arbitrate_shapes.html"
    assert shape_arbitration.main(["--out", str(out)]) == 0
    return out


@pytest.fixture
def page(browser, artefact):
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(artefact.resolve().as_uri())
    page.wait_for_timeout(150)
    yield page
    assert errors == [], f"the page's script threw: {errors}"
    context.close()


def claim_ids(page) -> list[str]:
    return page.evaluate(
        """() => {
            const data = JSON.parse(document.getElementById('arb-data').textContent);
            return data.claims.map(claim => claim.id);
        }"""
    )


def fill_identity(page) -> None:
    page.fill("#name", "Kobus")
    page.fill("#seat", "Product")
    page.fill("#date", "2026-11-06")


def answer_every_card(page, verdict: str = "keep") -> None:
    for card in page.locator("article.card").all():
        card.locator(f"input[value={verdict}]").check()


def export(page) -> str:
    page.click("#export")
    return page.input_value("#outText")


def test_the_page_shows_every_claim_the_tool_does(page):
    ids = claim_ids(page)
    assert ids, "the page carries no claims"
    assert page.locator("article.card").count() == len(ids)
    for claim_id in ids:
        assert page.locator(f'[data-claim="{claim_id}"]').count() == 1


def test_a_verdict_is_kept_across_a_reload(page, artefact):
    claim_id = claim_ids(page)[0]
    page.locator(f'[data-claim="{claim_id}"] input[value=unsure]').check()
    page.reload()
    page.wait_for_timeout(150)
    assert page.locator(f'[data-claim="{claim_id}"] input[value=unsure]').is_checked()


def test_the_export_refuses_an_unanswered_page_and_names_it(page):
    fill_identity(page)
    text = export(page)
    assert text == "", "an unfinished arbitration produced JSON"
    problems = page.inner_text("#outProblems")
    assert "is not answered yet" in problems
    assert page.locator("#outText").is_hidden()


def test_a_cant_tell_without_a_reason_is_refused(page):
    fill_identity(page)
    answer_every_card(page)
    claim_id = claim_ids(page)[0]
    page.locator(f'[data-claim="{claim_id}"] input[value=unsure]').check()
    text = export(page)
    assert text == ""
    assert "without a reason" in page.inner_text("#outProblems")


def test_a_finished_export_is_a_file_the_signoff_recognises(page):
    fill_identity(page)
    answer_every_card(page)
    payload = json.loads(export(page))
    assert payload["kind"] == shape_arbitration.KIND
    assert payload["artefact"] == shape_arbitration.ARTEFACT_NAME
    assert set(payload["claims"]) == set(claim_ids(page))
    assert payload["amendments"] == [], "a page of keeps must not amend anything"


def test_an_amendment_that_the_fixture_does_not_say_yet_is_refused_on_the_way_in(page):
    """The page lets a reviewer type anything; the record only accepts what the key now says."""
    fill_identity(page)
    answer_every_card(page)
    claim_id = claim_ids(page)[0]
    card = page.locator(f'[data-claim="{claim_id}"]')
    card.locator("input[value=amend]").check()
    card.locator(".newtext").fill("a grouping the key does not currently make")
    card.locator("textarea").fill("the paper prints four header lines, not two")
    payload = json.loads(export(page))

    export_doc, problems = shape_review_signoff.arbitration_export(
        {"claims": {claim_id: {"expected": payload["claims"][claim_id]["expected"],
                              "verdict": "yes", "note": ""}},
         "reviewer": {"name": "Kobus", "seat": "Product"}, "reviewed_at": "2026-11-05",
         "page_notes": {}, "notes_resolved": {}, "amendments": []},
        payload,
    )
    assert export_doc is None
    assert any("is not what the key says now" in problem for problem in problems)


def test_an_arms_report_pasted_into_the_amendment_box_is_refused(page):
    """The first real export put a mismatch line in `to`, which is not a claim in any form."""
    fill_identity(page)
    answer_every_card(page)
    claim_id = claim_ids(page)[0]
    card = page.locator(f'[data-claim="{claim_id}"]')
    card.locator("input[value=amend]").check()
    card.locator(".newtext").fill(
        f"{claim_id.split('.')[0]}: row 1 cell 4 must be empty, the read says 'R500'"
    )
    card.locator("textarea").fill("the paper prints the amount in this cell")
    assert export(page) == ""
    assert "report, not a claim" in page.inner_text("#outProblems")


def test_a_page_prints_every_page_of_a_two_page_shape(page):
    section = page.locator('section.shape[data-shape="page_break_row"]')
    assert section.locator("figure img").count() == 2
    assert "printed page 5" in section.inner_text()
