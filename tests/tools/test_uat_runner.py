"""The artefact: self-contained, verbatim, and free of anything a machine already proves.

The three guarantees here are the ones that fail **silently** if they break:

* a remote asset or a `fetch` would still render on this machine and only fail in the
  room the reviewer is actually in — so the test greps the output, not the intent;
* a dropped `Judgement:` still renders a card that looks fine, so the test compares the
  page's words against the file's words, independently of the parser;
* the file's "Automated coverage (NOT UAT)" table reappearing would ask a human to confirm
  what pytest proves — the exact failure the `writing-uat-tests` skill exists to prevent.
"""

from __future__ import annotations

import html as htmllib
import json
import re

import pytest

from scripts.uat_parse import parse_decisions, parse_uat
from scripts.uat_page import environment, render_inline, render_prose
from scripts.uat_runner import build_html, main

from .conftest import REAL_SPEC, REAL_UAT

ENV = {
    "commit": "deadbee",
    "working_tree": "modified",
    "database": "pgs_uat",
    "generated_on": "2026-10-22",
}


def _build(uat_path=REAL_UAT, preflight: str = "") -> str:
    uat = parse_uat(uat_path)
    decisions = parse_decisions(REAL_SPEC.read_text(encoding="utf-8"))
    return build_html(uat, ENV, preflight, decisions)


def payload(markup: str) -> dict:
    match = re.search(
        r'<script type="application/json" id="uat-data">(.*?)</script>', markup, re.DOTALL
    )
    assert match, "the artefact carries no uat-data payload"
    return json.loads(match.group(1))


def without_payload(markup: str) -> str:
    return re.sub(
        r'<script type="application/json" id="uat-data">.*?</script>', "", markup, flags=re.DOTALL
    )


def visible_text(markup: str) -> str:
    """What a reader sees: no scripts, no styles, no tags, entities resolved."""
    body = re.sub(r"<script.*?</script>", " ", markup, flags=re.DOTALL)
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.DOTALL)
    body = re.sub(r"<[^>]+>", " ", body)
    return " ".join(htmllib.unescape(body).split())


def _plain(text: str) -> str:
    """Strip the markdown marks the renderer consumes, leaving the words."""
    return " ".join(text.replace("*", "").replace("`", "").split())


# ------------------------------------------------------------------- self-contained


def test_the_artefact_makes_no_network_request():
    markup = _build()

    assert "http://" not in markup
    assert "https://" not in markup
    assert "src=" not in markup
    assert "href=" not in markup
    # No `fetch`, no `XMLHttpRequest`, no `sendBeacon`: "nothing leaves the machine" is
    # a property of the file, not a promise in a readme.
    for call in ("fetch(", "XMLHttpRequest", "sendBeacon", "new WebSocket"):
        assert call not in markup


def test_the_artefact_renders_nothing_from_a_link_or_an_image():
    """The renderer must not turn reviewer-visible prose into an anchor or an image."""
    rendered = render_prose(
        'See [the standard](https://example.org/x) and <img src="x.png"> and <script>x</script>'
    )

    assert "<a " not in rendered and "<img" not in rendered and "<script" not in rendered
    # Link syntax stays literal text: converting it would be the only way a URL could
    # reach a document that must make no requests.
    assert "[the standard](https://example.org/x)" in rendered
    assert "&lt;img" in rendered
    assert "&lt;script" in rendered


# ------------------------------------------------------------------------- verbatim


def test_every_judgement_reaches_the_page_verbatim():
    """Compared against the *file*, not against the parser that also produced the page."""
    markup = _build()
    visible = _plain(visible_text(markup))
    raw = REAL_UAT.read_text(encoding="utf-8").splitlines()

    checked = 0
    for index, line in enumerate(raw):
        if not line.startswith("**Judgement:**"):
            continue
        following = " ".join(raw[index : index + 4])
        excerpt = following.split("**Judgement:**", 1)[1].strip()
        if not excerpt:
            continue
        probe = _plain(excerpt)[:60].strip()
        if len(probe) < 20:
            continue
        assert probe in visible, f"a judgement was not rendered: {probe!r}"
        checked += 1

    assert checked == 10, f"expected to check 10 judgements, checked {checked}"


def test_the_payload_carries_the_parsed_judgement_character_for_character():
    markup = _build()
    carried = {entry["n"]: entry["judgement"] for entry in payload(markup)["scenarios"]}

    for scenario in parse_uat(REAL_UAT).scenarios:
        assert carried[scenario.number] == scenario.judgement


def test_markdown_is_rendered_rather_than_printed():
    """A card full of `**asterisks**` stops a reviewer reading the question as a question."""
    markup = without_payload(_build())

    assert "**" not in markup
    assert "<strong>" in markup
    assert "<em>" in markup


# --------------------------------------------------------------- the wrong content


def test_the_automated_coverage_table_is_not_presented():
    markup = _build()
    visible = visible_text(markup)

    assert "Automated coverage" not in visible
    assert "test_claim_discipline.py" not in markup
    assert "test_public.py" not in markup
    assert "asserted by the suite" not in visible


def test_one_card_per_scenario_and_the_na_scenario_is_marked():
    markup = _build()

    assert len(re.findall(r'<article class="card', markup)) == 10
    assert len(re.findall(r'<article class="card na"', markup)) == 1
    assert 'id="scenario-5"' in markup
    # The exclusion must be visible *and* explained: a greyed-out card with no reason reads
    # to the next reviewer as a check that failed.
    visible = visible_text(markup)
    assert "Not applicable to MVP 0" in visible
    assert "D44" in visible


def test_the_na_card_carries_the_decision_that_caused_it():
    """The reason must survive into the card, or the greyed-out scenario looks like a failure."""
    markup = _build()
    entry = next(e for e in payload(markup)["scenarios"] if e["n"] == 5)

    assert entry["not_applicable"] is True
    assert entry["na_reason"].startswith("D44:")


def test_the_header_carries_the_commit_and_the_database():
    """A signature on a build nobody can identify is not evidence (PRD §7)."""
    markup = _build()

    assert "deadbee" in markup
    assert "pgs_uat" in markup
    assert "modified" in markup


def test_the_preflight_is_shown_when_it_is_given_and_its_absence_is_admitted():
    with_preflight = _build(preflight="[ok  ] corpus present  366 chunks")
    assert "corpus present  366 chunks" in with_preflight

    without = _build()
    assert "No preflight output was pasted in" in without


# ------------------------------------------------------------------- reproducible


def test_the_same_inputs_produce_the_same_bytes_and_no_carriage_returns(tmp_path):
    """`write_text` emits CRLF on Windows, which would make the artefact differ by
    platform and every regeneration a whole-file diff (`testing_hazards.md` §1.27)."""
    out = tmp_path / "uat.html"
    args = ["--file", str(REAL_UAT), "--out", str(out), "--database", "pgs_uat"]

    assert main(args) == 0
    first = out.read_bytes()
    assert b"\r\n" not in first

    assert main(args) == 0
    assert out.read_bytes() == first

    assert _build() == _build()


# ---------------------------------------------------------------- the runner refuses


def test_the_runner_exits_non_zero_when_a_scenario_has_no_judgement(write_uat):
    path = write_uat(
        "**Feature slug:** `x`\n\n## Scenario 1 — A thing\n\n**Setup:** Open.\n\n"
        "**Expected:** Something.\n"
    )

    assert main(["--file", str(path), "--out", str(path.with_suffix(".html"))]) == 1


def test_the_runner_exits_non_zero_when_the_applicability_scan_fails(write_uat):
    path = write_uat(
        "**Feature slug:** `x`\n\n## Scenario 1 — A thing\n\n"
        "**Status:** Not applicable. decision **D9999**.\n\n"
        "**Setup:** Open.\n\n**Judgement:** Does it read right?\n"
    )

    assert main(["--file", str(path), "--out", str(path.with_suffix(".html"))]) == 1


def test_the_runner_exits_2_when_the_file_does_not_exist(tmp_path):
    assert main(["--file", str(tmp_path / "nope.md"), "--out", str(tmp_path / "o.html")]) == 2


def test_the_runner_writes_the_file_and_names_the_counts(tmp_path, capsys):
    out = tmp_path / "uat.html"

    assert main(["--file", str(REAL_UAT), "--out", str(out), "--database", "pgs_uat"]) == 0

    printed = capsys.readouterr().out
    assert "10 scenarios (9 applicable, 1 N/A)" in printed
    assert out.exists()


# --------------------------------------------------------------------- environment()


def test_environment_records_an_unknown_commit_rather_than_guessing(monkeypatch):
    monkeypatch.setattr("scripts.uat_page._git", lambda *args: "")

    env = environment("pgs_uat")

    assert env["commit"] == "unknown"
    assert env["working_tree"] == "clean"


def test_render_inline_escapes_before_it_emphasises():
    assert render_inline("<b>**bold**</b>") == "&lt;b&gt;<strong>bold</strong>&lt;/b&gt;"
    # A backticked asterisk is code, not an unclosed `<em>`.
    assert render_inline("`a * b`") == "<code>a * b</code>"


def test_environment_ignores_the_artefact_it_is_writing(monkeypatch):
    """Regenerating the page always leaves it differing from HEAD; that is not a dirty tree.

    Found on the 2026-10-28 concordance sign-off: the export said `working_tree: modified`
    while the only dirty file was the artefact itself, so a clean signature was impossible.
    """
    from pathlib import Path

    from scripts import uat_page

    rel = "product/design/uat/concordance.html"

    def fake_git(*args: str) -> str:
        if args == ("rev-parse", "--short", "HEAD"):
            return "abc1234"
        return f" M {rel}\n?? something-else.txt"

    monkeypatch.setattr(uat_page, "_git", fake_git)

    with_own = uat_page.environment("pgs", out_path=uat_page.REPO_ROOT / rel)
    without = uat_page.environment("pgs")

    assert with_own["working_tree"] == "modified", "the other untracked file still counts"
    assert without["working_tree"] == "modified"

    monkeypatch.setattr(
        uat_page, "_git", lambda *a: "abc1234" if a[:1] == ("rev-parse",) else f" M {rel}"
    )

    assert uat_page.environment("pgs", out_path=uat_page.REPO_ROOT / rel)["working_tree"] == "clean"
    assert uat_page.environment("pgs")["working_tree"] == "modified"
