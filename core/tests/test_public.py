"""Sub-plan C1a — the public site's static foundation and its first page.

`build_principles.md` §IV is the constraint this file protects: **zero build
pipeline, no CDN**. The prototype (`product/design/final_home.html`) loads Tailwind
from `cdn.tailwindcss.com` and both fonts from `fonts.googleapis.com`; D40 rejects
that. Everything the page needs must live in `core/static/` and ship through
`collectstatic`, because this deployment runs on a local box and later a VPS with no
asset pipeline at all.

Two failures this file exists to catch, both of which are **silent**:

1. **A missing font file.** `@font-face` pointing at a file that is not there raises
   no error anywhere — the browser quietly falls back to Georgia or a system sans and
   the whole design changes character. DESIGN.md §10 records the same class of defect
   ("a token can be silently absent") costing the design session hours. So the
   `url()`s in `root.css` are resolved against the filesystem rather than trusted.
2. **A CDN creeping back in.** One `<link>` to Google Fonts looks harmless and puts a
   third-party request on every page load of a group whose entire premise is
   local, face-to-face trust. Asserted on rendered HTML, not on a template grep.

The 30 KB cap (§II) is asserted here too, because `site.css` is the file most likely
to breach it and nobody notices a stylesheet growing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

STATIC = Path("core/static")
CSS_DIR = STATIC / "css"

#: The public pages read data now that C2 made the document list rows rather than
#: hardcoded chips: `/` and `/documents/` each issue one query. A test that renders a
#: page without database access would fail with Django's own "Database access not
#: allowed" — which reads as a broken fixture, not as the missing marker it is.
pytestmark = pytest.mark.django_db

#: The public route table. Kept as data (never an empty list — an empty
#: `parametrize` passes vacuously, testing_hazards.md §1.6). Each heading is the
#: page's own `h1`, so a copy-paste between pages cannot pass.
PAGES: list[tuple[str, str, str]] = [
    ("home", "/", "Organic assurance built by"),
    ("organics", "/organics/", "Organic agriculture, and what a PGS adds"),
    ("how-it-works", "/how-it-works/", "How it works"),
    ("members", "/members/", "Who is in the group"),
    ("documents", "/documents/", "What we publish"),
    ("become-a-member", "/become-a-member/", "What membership and assessment cost"),
    ("ask", "/ask/", "Ask the standard"),
    ("contact", "/contact/", "Who to talk to"),
]

MAX_SOURCE_BYTES = 30 * 1024


# --- The page renders -------------------------------------------------------


@pytest.mark.parametrize(("name", "url", "heading"), PAGES, ids=[p[0] for p in PAGES])
def test_route_returns_200(client: Client, name: str, url: str, heading: str):
    """Each route is reachable at its public path and shows its own heading."""
    response = client.get(url)
    assert response.status_code == 200, f"{url} -> {response.status_code}"
    assert heading in response.content.decode()


@pytest.mark.parametrize(("name", "url", "heading"), PAGES, ids=[p[0] for p in PAGES])
def test_route_has_its_own_title(client: Client, name: str, url: str, heading: str):
    """A copy-pasted `<title>` is the most common rebuild defect, and it is invisible
    in the browser tab of the person who built it."""
    html = client.get(url).content.decode()
    match = re.search(r"<title>(.*?)</title>", html, re.S)
    assert match, f"{url} has no <title>"
    title = match.group(1).strip()
    assert "Outeniqua" in title
    assert title != "", "empty title"


@pytest.mark.parametrize(("name", "url", "heading"), PAGES, ids=[p[0] for p in PAGES])
def test_html_declares_a_language(client: Client, name: str, url: str, heading: str):
    """The language attribute drives hyphenation, screen-reader pronunciation and
    Google's language detection. It is also what C3 will flip per session (D18)."""
    html = client.get(url).content.decode()
    assert re.search(r'<html[^>]*\blang="[a-z]{2}', html), "no lang attribute on <html>"


@pytest.mark.parametrize(("name", "url", "heading"), PAGES, ids=[p[0] for p in PAGES])
def test_no_unrendered_template_syntax_reaches_the_browser(
    client: Client, name: str, url: str, heading: str
):
    """A template comment that is not a comment is rendered text — and worse, its
    contents are parsed as HTML.

    This is not hypothetical. Django's `{# ... #}` form is **single-line only**; the
    first build of this page used it across several lines. The comments were emitted
    verbatim, and one of them contained the word `<details>` in prose, which the
    browser then treated as a real element — nesting the navigation inside a stray
    disclosure widget and hiding the header's links and CTA. Nothing errored: the
    page returned 200 and looked *almost* right.

    So: no template delimiters in output, and the document keeps the landmarks it
    was designed to have.
    """
    html = client.get(url).content.decode()
    for token in ("{#", "#}", "{{ ", "{{{", "{%"):
        assert token not in html, f"unrendered {token!r} on {url}"

    assert html.count("<main") == 1, f"{url} has {html.count('<main')} <main> elements"
    assert html.count("<details") == 1, f"{url} has a stray <details>"


# --- Nothing is loaded from a third-party origin ---------------------------


@pytest.mark.parametrize(("name", "url", "heading"), PAGES, ids=[p[0] for p in PAGES])
def test_page_loads_nothing_from_a_cdn(client: Client, name: str, url: str, heading: str):
    """No stylesheet, script, font or image may come from another origin.

    Catches the Tailwind CDN and the Google Fonts `<link>` specifically: both were
    in the approved prototype and both are rejected (D40, §IV).
    """
    html = client.get(url).content.decode()
    for match in re.findall(r'<(?:link|script|img)[^>]+(?:href|src)="([^"]+)"', html):
        assert not match.startswith(("http://", "https://", "//")), (
            f"third-party asset on {url}: {match}"
        )


# --- The assets the CSS refers to actually exist ---------------------------


def test_both_stylesheets_are_present():
    """Guards the two `glob()` parameters below.

    `parametrize` over a file glob yields an empty set if the glob matches nothing,
    and pytest reports that as SKIPPED — a green-looking run that checked no CSS at
    all (testing_hazards.md §1.6). This test makes the missing file a failure first.
    """
    for name in ("root.css", "site.css", "components.css", "chat.css"):
        assert (CSS_DIR / name).is_file(), f"missing {name}"


@pytest.mark.parametrize("stylesheet", sorted(CSS_DIR.glob("*.css")), ids=lambda p: p.name)
def test_every_asset_referenced_by_css_exists(stylesheet: Path):
    """`url()` targets are resolved against the filesystem.

    A missing woff2 does not error — the browser falls back, and the page keeps
    working while looking wrong. That is why this is asserted rather than assumed.
    """
    source = stylesheet.read_text(encoding="utf-8")
    urls = re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", source)

    for url in urls:
        assert not url.startswith(("http://", "https://", "//", "data:")), (
            f"remote asset in {stylesheet.name}: {url}"
        )
        target = (stylesheet.parent / url).resolve()
        assert target.is_file(), f"{stylesheet.name} -> {url} is missing on disk"


def test_all_four_font_files_are_present():
    """Two families × roman + italic. Asserted by name so a partial re-download (a
    failed second run of the fetch script) cannot pass as complete."""
    for name in ("lora-normal", "lora-italic", "mulish-normal", "mulish-italic"):
        assert (STATIC / "fonts" / f"{name}.woff2").is_file(), f"missing {name}.woff2"


# --- The file-size cap ------------------------------------------------------


@pytest.mark.parametrize("path", sorted(CSS_DIR.glob("*.css")), ids=lambda p: p.name)
def test_css_is_under_the_source_size_cap(path: Path):
    """§II: no source file exceeds 30 KB. A stylesheet is a source file."""
    size = path.stat().st_size
    assert size <= MAX_SOURCE_BYTES, (
        f"{path.name} is {size:,} bytes, over the {MAX_SOURCE_BYTES:,} cap — "
        "slice it by domain (e.g. chat.css) rather than letting it grow"
    )


# --- The band rhythm (DESIGN.md §3) ----------------------------------------


#: The home page's bands, in document order. DESIGN §3 fixes this sequence and the
#: ground each band carries; `test_band_grounds_alternate` proves the grounds, this
#: list proves the order and that nothing was quietly added or lost.
BAND_IDS = [
    "hero",
    "key-facts",
    "organics",
    "how-it-works",
    "farm-gallery",
    "why-join",
    "fees",
    "documents",
    "ask-standard",
    "members",
]


def test_home_has_every_band_in_design_order(client: Client):
    html = client.get("/").content.decode()
    positions = []
    for band in BAND_IDS:
        index = html.find(f'id="{band}"')
        assert index != -1, f"home is missing the {band!r} band"
        positions.append(index)
    assert positions == sorted(positions), "bands are out of DESIGN §3 order"


def test_home_has_exactly_one_dark_band(client: Client):
    """"Only one dark band exists — a second would flatten the contrast that makes
    it read as a moment" (DESIGN §3)."""
    html = client.get("/").content.decode()
    assert html.count("section--dark") == 1


# --- Fees come from one place ---------------------------------------------


def test_no_fee_figure_is_typed_into_a_template():
    """Every figure must arrive as cents and go through `format_zar`.

    Two renderings of the same fee exist (the ribbon's `R100 / year` and the
    membership table's `R100`). Typed twice, they drift; typed once in
    `core/services/_public.py`, they cannot. Asserted on template source because a
    rendered-HTML assertion cannot tell a good `R100` from a bad one.
    """
    literals = ("R100", "R500", "R1 500", "R8 000", "1 500", "8 000")
    for path in sorted(Path("core/templates").rglob("*.html")):
        source = path.read_text(encoding="utf-8")
        for literal in literals:
            assert literal not in source, f"{literal!r} typed into {path.name}"


def test_ribbon_figure_matches_the_membership_fee(client: Client):
    from core.services._public import MEMBERSHIP_FARMER_CENTS
    from core.templatetags.pgs_extras import format_zar

    html = client.get("/").content.decode()
    figure = format_zar(MEMBERSHIP_FARMER_CENTS)
    assert f"{figure} / year" in html


def test_fee_table_renders_every_band(client: Client):
    from core.services._public import FEE_BANDS
    from core.templatetags.pgs_extras import format_zar

    html = client.get("/").content.decode()
    for band in FEE_BANDS:
        assert band.label in html, f"band {band.label!r} is not on the fees section"
        assert format_zar(band.initial_cents) in html
        assert format_zar(band.renewal_cents) in html


# --- The claim discipline the OPP requires, asserted from day one ----------


def test_home_carries_the_membership_is_not_certification_disclaimer(client: Client):
    """The disclaimer **card**, not the string.

    The footer's bottom bar also says "Membership is not certification", so a bare
    substring assertion stayed green after the card's heading was replaced with lorem
    ipsum — a test passing for the wrong reason, caught by mutation and fixed here
    (testing_hazards.md §0). The OPP requires the statement *on the page that lists or
    implies members*; a footer line is not that.
    """
    html = client.get("/").content.decode()
    assert 'class="disclaimer__title">Membership is not certification<' in html
    assert "certification committee" in html
    assert "id=\"disclaimer\"" in html


# --- No dead links --------------------------------------------------------


def _internal_targets(html: str) -> set[tuple[str, str]]:
    """(path, fragment) for every internal href in a page."""
    targets: set[tuple[str, str]] = set()
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith(("http://", "https://", "//", "mailto:", "tel:")):
            continue
        # Static assets are not served by the test client; they are checked
        # against the filesystem by `test_every_static_asset_exists` instead.
        if href.startswith(settings.STATIC_URL):
            continue
        path, _, fragment = href.partition("#")
        targets.add((path or "", fragment))
    return targets


@pytest.mark.parametrize(("name", "url", "heading"), PAGES, ids=[p[0] for p in PAGES])
def test_every_internal_link_resolves(client: Client, name: str, url: str, heading: str):
    """A dead link is not something a UAT reviewer should have to find.

    Both halves matter: the **path** must return 200, and the **fragment** must
    exist as an `id` on the page it points at. A `#fees` anchor with no `id="fees"`
    scrolls nowhere and looks like a broken button — DESIGN §10 records exactly that
    defect in the prototype.
    """
    html = client.get(url).content.decode()
    cache: dict[str, str] = {url: html}

    for path, fragment in _internal_targets(html):
        target = path or url
        if target not in cache:
            response = client.get(target)
            assert response.status_code == 200, f"{url} links to dead {target}"
            body = _html_of(response)
            if body is None:
                # A published document: 200 is the whole contract here. Its bytes are
                # asserted in `test_documents.py`, which knows what they should be.
                continue
            cache[target] = body
        if fragment:
            assert f'id="{fragment}"' in cache[target], (
                f"{url} links to {target}#{fragment}, which has no such id"
            )


def _html_of(response) -> str | None:
    """The body if this is an HTML page, else None.

    C2 added links to PDFs. `response.content.decode()` on a PDF raises a
    `UnicodeDecodeError` from inside the helper, which reads as a broken link test
    rather than as "this one is a file, and 200 is all it owes us". A non-HTML
    response is also never cached: re-downloading a 4.6 MB standard into a string per
    page would make this suite the slowest thing in the gate.
    """
    if "text/html" not in response.headers.get("Content-Type", ""):
        return None
    return response.content.decode()


@pytest.mark.parametrize(("name", "url", "heading"), PAGES, ids=[p[0] for p in PAGES])
def test_every_static_asset_exists(client: Client, name: str, url: str, heading: str):
    """Every `/static/...` the page references is on disk.

    The test client does not serve static files, so a missing image returns 404 to a
    browser and 404 to nobody in CI. Resolving the URL against `core/static/` turns a
    silently broken image into a failed build — the same class of defect as a missing
    font file, and just as invisible.
    """
    html = client.get(url).content.decode()
    for asset in re.findall(r'(?:src|href)="(/static/[^"]+)"', html):
        relative = asset[len(settings.STATIC_URL) :]
        assert (Path("core/static") / relative).is_file(), f"{url} -> missing {asset}"


def test_no_template_uses_a_multiline_hash_comment():
    """`{# ... #}` is single-line only in Django; a multi-line one is renderable text.

    Checked at the source rather than in the output, because the output test only sees
    a page that already rendered — and the failure mode (a `<details>` in prose becoming
    a real element) is silent. There is no multi-line form other than
    `{% comment %}`, so any newline inside `{#...#}` is a defect by construction.
    """
    offenders = []
    for path in sorted(Path("core/templates").rglob("*.html")):
        source = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\{#(.*?)#\}", source, re.S):
            if "\n" in match.group(1):
                offenders.append(f"{path.name}: {match.group(1).strip()[:60]}…")
    assert not offenders, "multi-line {# #} comments (use {% comment %}):\n" + "\n".join(offenders)
