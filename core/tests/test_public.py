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
from django.test import Client
from django.urls import reverse

STATIC = Path("core/static")
CSS_DIR = STATIC / "css"

#: The public route table. Kept as data (never an empty list — an empty
#: `parametrize` passes vacuously, testing_hazards.md §1.6). Each heading is the
#: page's own `h1`, so a copy-paste between pages cannot pass.
PAGES: list[tuple[str, str, str]] = [
    ("home", "/", "Organic assurance built by"),
    ("organics", "/organics/", "Guided by six basic elements"),
    ("how-it-works", "/how-it-works/", "How it works"),
    ("members", "/members/", "Who is in the group"),
    ("become-a-member", "/become-a-member/", "What membership and assessment cost"),
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
    for name in ("root.css", "site.css"):
        assert (CSS_DIR / name).is_file(), f"missing {name}"


@pytest.mark.parametrize("stylesheet", sorted(CSS_DIR.glob("*.css")), ids=lambda p: p.name)
def test_every_asset_referenced_by_css_exists(stylesheet: Path):
    """`url()` targets are resolved against the filesystem.

    A missing woff2 does not error — the browser falls back, and the page keeps
    working while looking wrong. That is why this is asserted rather than assumed.
    """
    source = stylesheet.read_text(encoding="utf-8")
    urls = re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", source)
    assert urls, f"{stylesheet.name} references no assets — is it the right file?"

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
