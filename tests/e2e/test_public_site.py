"""Playwright — the seven public routes, at desktop and at 390 px.

These tests do not duplicate `core/tests/test_public.py`; they cover what only a real
browser can see: that the stylesheet actually loaded, that nothing overflows a phone,
that a control is physically big enough to tap, and that the page console is clean.

`build_principles.md` §V (Playwright E2E, mobile responsiveness) and DESIGN.md rules 5
and 6 are what is being proved.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

ROUTES = [
    ("/", "Organic assurance built by"),
    ("/organics/", "Organic agriculture, and what a PGS adds"),
    ("/how-it-works/", "How it works"),
    ("/members/", "Who is in the group"),
    # C2. The row action `a.doc-row__action` is already in the 44px selector list,
    # because the home page's band carried those chips before the documents existed.
    ("/documents/", "What we publish"),
    ("/become-a-member/", "What membership and assessment cost"),
    ("/ask/", "Ask the standard"),
    ("/contact/", "Who to talk to"),
]

PHONE_WIDTH = 390


@pytest.mark.parametrize(("path", "heading"), ROUTES, ids=[p.strip("/") or "home" for p, _ in ROUTES])
def test_route_renders_in_a_browser(page, live_server, console_errors, path, heading):
    """200, its own h1, a styled page, and a clean console."""
    response = page.goto(live_server.url + path, wait_until="networkidle")
    assert response.status == 200

    h1 = page.locator("h1")
    assert h1.count() == 1, f"{path} has {h1.count()} h1 elements"
    assert heading in h1.inner_text()

    # The stylesheet really loaded. `document.styleSheets` is empty when a <link> 404s,
    # and an unstyled page still passes every Django assertion.
    sheet_count = page.evaluate("() => document.styleSheets.length")
    assert sheet_count >= 4, f"only {sheet_count} stylesheets on {path}"

    # The webfont really loaded: a silent fallback to Georgia changes the design and
    # raises no error anywhere (DESIGN.md §10).
    fonts = page.evaluate("() => [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family)")
    assert "Lora" in fonts and "Mulish" in fonts, f"fonts not loaded on {path}: {fonts}"

    assert console_errors == [], f"console errors on {path}: {console_errors}"


@pytest.mark.parametrize("path", [p for p, _ in ROUTES], ids=[p.strip("/") or "home" for p, _ in ROUTES])
def test_no_horizontal_overflow_on_a_phone(phone_page, live_server, path):
    """A 390px viewport must not scroll sideways.

    UAT Scenario 6 asks whether the site is comfortable on a real phone; this is the half
    of that question a machine can answer. The other half — thumb reach, keyboard
    behaviour, sunlight — stays human.
    """
    phone_page.goto(live_server.url + path, wait_until="networkidle")
    width = phone_page.evaluate("() => document.documentElement.scrollWidth")
    assert width <= PHONE_WIDTH, f"{path} scrolls to {width}px on a {PHONE_WIDTH}px viewport"


@pytest.mark.parametrize("path", [p for p, _ in ROUTES], ids=[p.strip("/") or "home" for p, _ in ROUTES])
def test_controls_are_at_least_44px(page, live_server, path):
    """DESIGN rule 5 / build_principles §IV: touch targets ≥ 44×44 px.

    The prototype's own buttons were 32px tall, so this is not a rule the design already
    met — it is one the implementation had to earn. Asserted on **measured boxes**, never
    on the CSS, because `min-height` can be lost to a later rule and nothing warns.
    """
    page.goto(live_server.url + path, wait_until="networkidle")

    measured = page.evaluate(
        """() => {
            const selectors = [
              '.btn', '.site-nav__link', '.site-menu__toggle', '.lang-switch',
              '.footer__social-link', '.footer__list a', '.footer__ask',
              '.chat__link', '.chat__send', '.chat-form__input', '.cite--reference',
              '.link-more', 'a.doc-row__action'
            ];
            return selectors.flatMap(sel => [...document.querySelectorAll(sel)].map(el => {
                const r = el.getBoundingClientRect();
                return {sel, text: (el.textContent || '').trim().slice(0, 30),
                        w: Math.round(r.width), h: Math.round(r.height)};
            }));
        }"""
    )
    assert measured, "no controls found — the selector list has gone stale"

    # A control that is `display: none` at this viewport (the phone menu on desktop) has
    # a 0×0 box and no target size to judge. Filtered on the *measured* box, not on the
    # CSS, so a control that is meant to be visible and collapsed to zero still fails.
    rendered = [m for m in measured if m["w"] or m["h"]]
    assert rendered, "every control measured 0×0 — something is hiding the page"

    too_small = [m for m in rendered if m["w"] < 44 or m["h"] < 44]
    assert not too_small, f"targets under 44px on {path}: {too_small}"


@pytest.mark.parametrize("path", [p for p, _ in ROUTES], ids=[p.strip("/") or "home" for p, _ in ROUTES])
def test_text_links_clear_the_wcag_target_size(page, live_server, path):
    """Text links reach WCAG 2.2 AA's 24×24 px, which the 44px control rule cannot.

    Inline links inside a sentence are exempt by the guideline itself and by common
    sense; everything laid out as its own box is not exempt, and a 15px-tall standalone
    "Request access" link is a real miss on a phone.
    """
    page.goto(live_server.url + path, wait_until="networkidle")

    small = page.evaluate(
        """() => [...document.querySelectorAll('a')]
            .filter(a => getComputedStyle(a).display !== 'inline')
            .filter(a => { const r = a.getBoundingClientRect(); return r.height > 0 && (r.height < 24 || r.width < 24); })
            .map(a => ({text: (a.textContent || '').trim().slice(0, 30),
                        h: Math.round(a.getBoundingClientRect().height),
                        w: Math.round(a.getBoundingClientRect().width)}))"""
    )
    assert not small, f"links under 24px on {path}: {small}"


def test_the_documents_page_offers_eight_downloads(page, live_server):
    """C2: eight rows, eight real links, in a browser.

    Also the guard for the `published_documents` fixture in `conftest.py`. Without that
    fixture the page renders zero rows and every assertion in this file still passes —
    measuring an empty list, which is `testing_hazards.md` §1.6 in a browser.
    """
    page.goto(live_server.url + "/documents/", wait_until="networkidle")

    links = page.locator("a.doc-row__action:not(.doc-row__action--secondary)[href^='/documents/']")
    assert links.count() == 8, f"{links.count()} download links — the rows did not render"
    assert page.locator(".doc-row__action--pending").count() == 0, "a pending chip survived"

    # The download is a streamed attachment, not a media path. Clicking it is the only
    # way to prove the link resolves to real bytes in a browser.
    with page.expect_download() as download_info:
        links.first.click()
    download = download_info.value
    assert download.suggested_filename.endswith(".pdf"), download.suggested_filename


def test_a_row_with_text_offers_the_reader_as_a_real_link(phone_page, live_server, reader_corpus):
    """PRD D1: the four documents with text gain `Read the text` beside Download — on a phone.

    `reader_corpus` ingests only the SAOSO's twin, so exactly one of the eight rows may
    carry the second verb: the four forms have no text, and D2 says they print nothing
    rather than a disabled control. Measured on the phone, because the row is a flex line
    that now holds two verbs and a 44px target is the thing that breaks first.
    """
    phone_page.goto(live_server.url + "/documents/", wait_until="networkidle")

    read = phone_page.locator("a.doc-row__action--secondary")
    assert read.count() == 1, f"{read.count()} reader links — only the ingested document has one"
    assert read.first.inner_text().strip() == "Read the text"

    box = read.first.bounding_box()
    assert box and box["height"] >= 44, f"the reader link is {box} — under the 44px target"
    overflow = phone_page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0, f"two actions on a row overflow the phone by {overflow}px"

    read.first.click()
    phone_page.wait_for_load_state("networkidle")
    assert phone_page.url.endswith("/documents/saoso-standard-v2.1/read/"), phone_page.url
    assert "passage__text" in phone_page.content(), "the reader link did not open the text"


@pytest.mark.parametrize("width", [768, 1024, 1280])
def test_the_header_holds_the_ask_link_without_overflow(page, live_server, width):
    """Six links + the CTA must stay on one line once the nav is visible.

    The nav turns on at 768 px; that is the width where one more link is most likely
    to push the header past the viewport. Measured, not assumed.
    """
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(live_server.url + "/", wait_until="networkidle")

    assert page.locator('.site-nav a[href="/ask/"]').is_visible()
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0, f"the header overflows at {width}px by {overflow}px"


def test_the_phone_menu_opens_fully_on_screen(phone_page, live_server):
    """The disclosure panel must be reachable and unclipped.

    It was anchored to its 44px toggle, which put it at a negative x and cut every label
    to its last four letters. Nothing errored: the links were in the DOM and clickable in
    a test client.
    """
    phone_page.goto(live_server.url + "/", wait_until="networkidle")
    phone_page.click(".site-menu__toggle")

    panel = phone_page.locator(".site-menu__panel")
    assert panel.is_visible()
    box = panel.bounding_box()
    assert box["x"] >= 0, f"menu panel starts at x={box['x']}"
    assert box["x"] + box["width"] <= PHONE_WIDTH, "menu panel overflows the viewport"

    assert panel.locator('a[href="/ask/"]').count() == 1, "Ask is not in the phone menu"
    for link in panel.locator("a").all():
        assert link.is_visible()
        assert link.inner_text().strip() != ""
