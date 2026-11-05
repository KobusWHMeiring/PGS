"""Playwright — the public self-check's stepped shape and its no-JavaScript fallback (A8).

`core/tests/test_selfcheck.py` proves the rules. This file proves the two things only a browser can
see, and both are the kind that pass every Django test while being broken for a farmer:

  * **the wizard actually steps.** `selfcheck.js` is navigation, and a page whose "Next" button does
    nothing looks finished in `client.get()`. The product owner approved a stepped shape (§11.5), so
    this is the shape, not a nicety.
  * **the no-JavaScript fallback is reachable.** With JS off the five sections must all be visible
    and one submit button must submit them — a farm connection on a tired phone is the case the
    fallback exists for, and `hidden` attributes set by a template would silently close it.

Also measured at 390 px, because the records step holds seven controls and §11.5's contrast note is
about exactly that: `DESIGN` §6 rule 5 (≥44 px) and the "no scrolling was a measurement, not an
aspiration" claim.
"""

from __future__ import annotations

import pytest

from core.tests.test_selfcheck import TEMPLATE_FILE

pytestmark = pytest.mark.e2e

URL = "/before-you-apply/"
PHONE = {"width": 390, "height": 844}


@pytest.fixture
def check_page(db, live_server):
    """The seeded deployment with the Crops questionnaire live — eleven derived controls."""
    from django.core.management import call_command

    call_command("seed_deployment", verbosity=0)
    call_command("load_template", str(TEMPLATE_FILE), "--activate", verbosity=0)
    return live_server


def test_the_first_step_is_the_only_one_showing(page, check_page, console_errors):
    page.goto(check_page.url + URL, wait_until="networkidle")
    assert page.locator(".wiz__step[data-current]").count() == 1
    assert page.locator("#q-A1").is_visible()
    assert not page.locator("#q-B1").is_visible()
    assert console_errors == []


def test_next_and_back_move_between_steps(page, check_page):
    page.goto(check_page.url + URL, wait_until="networkidle")
    page.get_by_role("button", name="Next").first.click()
    assert page.locator("#wiz-B-title").is_visible()
    assert page.locator("#q-B1").is_visible()
    page.get_by_role("button", name="Back").first.click()
    assert page.locator("#q-A1").is_visible()


def test_a_step_can_be_left_unanswered_and_the_nav_says_so(page, check_page):
    """§11.5: step boundaries are not validation. A blank step must still let you move on."""
    page.goto(check_page.url + URL, wait_until="networkidle")
    page.get_by_role("button", name="Next").first.click()
    assert page.locator("#q-B1").is_visible()
    assert page.locator('[data-step="2"] [data-counter]').inner_text() == "0 of 7 answered"


def test_the_phone_shape_does_not_overflow(page, check_page, phone_page, console_errors):
    phone_page.goto(check_page.url + URL, wait_until="networkidle")
    overflow = phone_page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0, f"the self-check overflows a 390px phone by {overflow}px"
    assert console_errors == []


def test_every_answer_chip_is_a_44px_target(page, check_page, phone_page):
    """DESIGN §6 rule 5, measured step by step — a hidden step measures 0 px, so loop the steps."""
    phone_page.goto(check_page.url + URL, wait_until="networkidle")
    for step in range(1, 6):
        phone_page.locator(f'.wiz__nav [data-goto="{step}"]').click()
        sizes = phone_page.eval_on_selector_all(
            '.wiz__step[data-current] .wiz__opt, .wiz__step[data-current] .consent__tick',
            "els => els.map(el => [el.className, Math.round(el.getBoundingClientRect().height)])",
        )
        assert sizes, f"step {step} has no tappable answer — the assertion would pass vacuously"
        smallest = min(sizes, key=lambda pair: pair[1])
        assert smallest[1] >= 44, f"step {step}: {smallest[0]} is {smallest[1]}px"


def test_the_honeypot_is_not_reachable_by_keyboard_or_eye(page, check_page):
    """A honeypot a person can reach and a bot skips is not a trap.

    Playwright's `is_visible()` is true for a 1×1 element, which is the point: the field has to be
    *in the form and fillable* to catch a form-filler. What is asserted is that it sits off the
    viewport and out of the tab order.
    """
    page.goto(check_page.url + URL, wait_until="networkidle")
    field = page.locator('input[name="website"]')
    assert field.count() == 1
    assert field.get_attribute("tabindex") == "-1"
    assert field.bounding_box()["x"] < -1000


def test_without_javascript_every_step_is_reachable(page, check_page):
    """The fallback: no `data-selfcheck-js`, so nothing is hidden and one submit does the work."""
    page.add_init_script("Object.defineProperty(window, 'IntersectionObserver', {value: undefined});")
    page.add_init_script(
        "HTMLScriptElement.prototype.setAttribute = HTMLScriptElement.prototype.setAttribute;"
    )
    # Block the wizard's own script; everything else loads normally.
    page.route("**/js/selfcheck.js", lambda route: route.abort())
    page.goto(check_page.url + URL, wait_until="networkidle")
    assert page.locator("html[data-selfcheck-js]").count() == 0
    for key in ("A1", "B1", "C1", "D1", "E1"):
        assert page.locator(f"#q-{key}, [data-consent='{key}']").first.is_visible(), key
    assert page.get_by_role("button", name="Show me what this means").first.is_visible()
