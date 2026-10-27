"""The generated UAT sign-off artefact, driven in a real browser.

This is the one guard the gate cannot hold. The artefact is **server-rendered** — cards,
judgement text, payload and counts are all in the HTML — so every structural assertion in
`tests/tools/test_uat_runner.py` stays green even when the page's script does not parse.
That exact defect happened once: extracting the script left the IIFE's closing `})();` in
the body *and* wrapped it again, Chromium threw `Unexpected token '}'`, the page was inert,
and 17 passing checks said nothing (`testing_hazards.md` §1.30).

So this file asserts only things the **script** produces:

* `#progress` is filled in (it is empty in the HTML);
* a card's status changes when PASS is pressed;
* the export button downloads a JSON file that `uat_signoff.py` will accept.

Run explicitly (outside the gate — `verify.sh` has no browser):

    python -m pytest tests/e2e/test_uat_artefact.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.uat_runner import main as run_runner

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[2]
UAT = REPO_ROOT / "tests/uat/mvp0_standards_and_public_site_uat.md"
ASK_UAT = REPO_ROOT / "tests/uat/ask_surface_uat.md"


@pytest.fixture
def artefact(tmp_path):
    """Generate the artefact the way an operator would, into a throwaway directory."""
    out = tmp_path / "uat.html"
    code = run_runner(["--file", str(UAT), "--out", str(out), "--database", "uat_e2e"])
    assert code == 0, "the runner refused the real UAT file"
    return out


def test_the_artefact_script_runs_and_the_page_is_usable(artefact, page, console_errors):
    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url))

    page.goto(artefact.as_uri())

    assert page.locator(".card").count() == 10
    assert page.locator(".judgement").count() == 10
    assert page.locator(".card.na").count() == 1

    # `#progress` is empty in the HTML; only the script fills it.
    assert page.locator("#progress").inner_text() == "1 of 10 judged"
    assert "D44" in page.locator("#scenario-5").inner_text()

    # Nothing but the file itself was requested: no CDN, no font, no analytics.
    assert [url for url in requests if not url.startswith("file://")] == []
    assert console_errors == []


def test_a_reviewer_can_judge_and_export_a_sign_off(artefact, page, tmp_path):
    page.goto(artefact.as_uri())

    page.fill("#me-name", "Kobus Meiring")
    page.select_option("#me-role", label="Product")
    page.fill("#me-date", "2026-10-22")
    page.click("#applyAll")

    for index in range(page.locator(".card").count()):
        card = page.locator(".card").nth(index)
        if "na" in (card.get_attribute("class") or ""):
            continue
        card.locator('.choice[data-v="PASS"]').click()
        card.locator('[data-k="note"]').fill("Checked against the printed page.")

    assert page.locator("#progress").inner_text() == "10 of 10 judged"
    assert page.locator(".status").first.inner_text().startswith("PASS · Kobus Meiring")

    with page.expect_download() as download_info:
        page.click("#exportBtn")
    path = tmp_path / "signoff.json"
    download_info.value.save_as(str(path))

    export = json.loads(path.read_text(encoding="utf-8"))
    assert export["kind"] == "pgs-uat-signoff"
    assert export["version"] == 1
    assert export["slug"] == "mvp0_standards_and_public_site"
    assert len(export["results"]) == 10
    assert export["environment"]["database"] == "uat_e2e"
    assert {entry["result"] for entry in export["results"]} == {"PASS", "N/A"}

    # The write-back must accept what the page produced. A shape change on either side
    # that the unit tests cannot see — because each is internally consistent — fails here.
    from scripts.uat_parse import parse_uat
    from scripts.uat_signoff import validate

    assert validate(parse_uat(UAT), export) == []


def test_the_export_is_refused_until_every_scenario_is_judged(artefact, page):
    page.goto(artefact.as_uri())

    # No name, no date, nine scenarios untouched: the guard must say so and not download.
    page.click("#exportBtn")

    assert page.locator("#clip").is_visible()
    assert "Before exporting" in page.locator("#clip").inner_text()
    assert page.locator("#progress").inner_text() == "1 of 10 judged"


def test_the_artefact_does_not_overflow_a_phone(artefact, phone_page):
    phone_page.goto(artefact.as_uri())

    overflow = phone_page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert overflow is False


# --- A second artefact, and the same script guard ---------------------------
#
# The tests above pin one file's *content* (ten cards, one N/A, D44). This one pins the thing
# that scales: whatever UAT file is next, the page's script must run and the export must be
# accepted by the write-back. Without it, the §1.30 defect can return the first time a new
# scenario shape (a table, a nested list, a code block) reaches the markdown renderer.


@pytest.fixture
def ask_artefact(tmp_path):
    out = tmp_path / "ask.html"
    code = run_runner(["--file", str(ASK_UAT), "--out", str(out), "--database", "uat_e2e"])
    assert code == 0, "the runner refused the ask-surface UAT file"
    return out


def test_a_new_uat_file_renders_a_usable_page(ask_artefact, page, console_errors):
    requests: list[str] = []
    page.on("request", lambda request: requests.append(request.url))

    page.goto(ask_artefact.as_uri())

    assert page.locator(".card").count() == 7
    assert page.locator(".judgement").count() == 7
    assert page.locator("#progress").inner_text() == "0 of 7 judged"
    assert [url for url in requests if not url.startswith("file://")] == []
    assert console_errors == []


def test_the_ask_uat_exports_a_sign_off_the_writer_accepts(ask_artefact, page, tmp_path):
    """A judgeable page is not enough: the export must round-trip into the markdown.

    Every scenario gets a result, a name and a date — because the page refuses to export
    otherwise, and a signature nobody made is worse than no signature.
    """
    page.goto(ask_artefact.as_uri())

    page.fill("#me-name", "Kobus Meiring")
    page.select_option("#me-role", label="Product")
    page.fill("#me-date", "2026-10-23")
    page.click("#applyAll")

    for index in range(page.locator(".card").count()):
        card = page.locator(".card").nth(index)
        card.locator('.choice[data-v="PASS"]').click()
        card.locator('[data-k="note"]').fill("Judged on the dev instance.")

    with page.expect_download() as download_info:
        page.click("#exportBtn")
    path = tmp_path / "signoff.json"
    download_info.value.save_as(str(path))

    export = json.loads(path.read_text(encoding="utf-8"))
    assert export["slug"] == "ask_surface"
    assert len(export["results"]) == 7

    from scripts.uat_parse import parse_uat
    from scripts.uat_signoff import validate

    assert validate(parse_uat(ASK_UAT), export) == []
