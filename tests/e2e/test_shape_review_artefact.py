"""The generated shape-key review surface, driven in a real browser.

This is the one guard the gate cannot hold. The artefact is server-rendered — every claim, grid and
page image is in the HTML — so all of `tests/tools/test_shape_review.py` stays green even if the
page's script does not parse. That exact defect happened once on the UAT artefact: an extracted
script left a brace behind, Chromium threw, the page was inert, and seventeen passing checks said
nothing (`testing_hazards.md` §1.30).

So this file asserts only what the **script** produces:

* `#progress` and the per-shape badges are empty in the HTML and filled at load;
* a verdict updates the count, reveals its reason box, and survives a reload (autosave);
* the export refuses a page with blanks, naming them, and emits no JSON;
* a complete review exports JSON that covers every claim and `shape_review_signoff.py` accepts.

Run explicitly (outside the gate — `verify.sh` has no browser):

    python -m pytest tests/e2e/test_shape_review_artefact.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import shape_review, shape_review_signoff

pytestmark = pytest.mark.e2e

STORE_KEY = "pgs.shape-key-review.v1"


@pytest.fixture(scope="module")
def artefact(tmp_path_factory) -> Path:
    """Generate the surface the way an operator would, into a throwaway file."""
    out = tmp_path_factory.mktemp("shape-review") / "shape_key_review.html"
    assert shape_review.main(["--out", str(out)]) == 0
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
            const data = JSON.parse(document.getElementById('shape-data').textContent);
            return data.shapes.flatMap(shape => shape.claims.map(claim => claim.id));
        }"""
    )


def test_the_script_fills_the_progress_it_left_empty(page):
    assert page.inner_text("#progress").startswith("0 of ")
    assert page.locator("[data-progress]").first.inner_text().endswith("/8")
    assert page.input_value("#rv-date"), "the date field arrives pre-filled with today"


def test_a_verdict_updates_the_count_and_reveals_its_reason(page):
    card = page.locator("fieldset.claim").first
    card.locator("input[value=no]").check()
    card.locator("textarea").fill("the page prints something else")

    assert not page.inner_text("#progress").startswith("0 of ")
    assert card.get_attribute("data-verdict") == "no"
    assert card.locator("textarea").is_visible()


def test_the_verdict_survives_a_reload(page, artefact):
    card = page.locator("fieldset.claim").first
    claim_id = card.get_attribute("data-claim")
    card.locator("input[value=yes]").check()

    page.reload()
    page.wait_for_timeout(150)
    assert page.locator("fieldset.claim").first.get_attribute("data-claim") == claim_id
    assert page.locator("fieldset.claim").first.locator("input[value=yes]").is_checked()


def test_the_export_refuses_a_page_with_blanks(page):
    page.click("#export")
    page.wait_for_timeout(150)

    problems = page.locator("#outProblems li")
    assert problems.count() > 1
    assert page.locator("#outText").is_hidden()
    assert page.locator("#dlgDl").is_hidden()


def test_a_complete_review_exports_json_the_signoff_accepts(page):
    ids = claim_ids(page)
    state = {
        "verdicts": {claim_id: "yes" for claim_id in ids},
        "notes": {},
        "pages": {},
        "name": "Probe Reviewer",
        "seat": "Product owner",
        "date": "2026-11-05",
    }
    page.evaluate(
        "(state) => localStorage.setItem('pgs.shape-key-review.v1', JSON.stringify(state))", state
    )
    page.reload()
    page.wait_for_timeout(150)
    page.click("#export")
    page.wait_for_timeout(150)

    assert page.locator("#outProblems li").count() == 0
    exported = json.loads(page.input_value("#outText"))
    assert sorted(exported["claims"]) == sorted(ids)
    assert exported["reviewer"] == {"name": "Probe Reviewer", "seat": "Product owner"}

    assert shape_review_signoff.validate(exported) == []
    record = shape_review_signoff.build_record(exported)
    assert record["summary"]["claims"] == len(ids)
    assert record["summary"]["shapes_confirmed"] == [case.key for case in shape_review.SHAPES]
