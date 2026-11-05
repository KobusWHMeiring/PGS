"""The arbitration surface: it presents only what a human can arbitrate, and nothing it decides.

The page is generated from the key plus the committed arm evidence, so every test here is about a
property that could silently stop being true: a claim the owner already settled reappearing, the
committed file drifting from the key, a verdict arriving pre-filled, or the page reaching the network.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from knowledge.tests.shape_fixtures import BY_KEY, SHAPES  # noqa: E402
from scripts import shape_arbitration, shape_disputes  # noqa: E402
from scripts.shape_claims import all_claims  # noqa: E402
from scripts.shape_review_signoff import (  # noqa: E402
    ARBITRATION_ARTEFACT,
    arbitration_export,
    current_claims,
)

COMMITTED = REPO_ROOT / shape_arbitration.ARTEFACT_NAME


def build() -> tuple[str, tuple]:
    arms = shape_disputes.load_arms()
    items = tuple(
        item
        for item in shape_disputes.disagreements(arms)
        if item.claim_id.split(".")[0] not in shape_arbitration.PASSED_ELSEWHERE
    )
    return shape_arbitration.build_html(arms, items), items


def payload(text: str) -> dict:
    """The `arb-data` JSON, unescaped from the script tag the page carries it in."""
    found = re.search(r'<script type="application/json" id="arb-data">(.*?)</script>', text, re.S)
    assert found, "the page carries no data payload"
    return json.loads(html.unescape(found.group(1)))


# --- the artefact ----------------------------------------------------------------


def test_the_committed_page_is_the_one_the_key_generates():
    text, _ = build()
    assert COMMITTED.read_text(encoding="utf-8") == text, (
        "product/design/uat/arbitrate_shapes.html is stale - regenerate with "
        "scripts/shape_arbitration.py"
    )


def test_the_page_reaches_no_network():
    text, _ = build()
    for needle in ("http://", "https://", "//cdn", "@import"):
        assert needle not in text, f"the artefact must open with the wifi off; found {needle!r}"


def test_no_verdict_is_pre_filled():
    """Nothing is decided before the reviewer decides it (pgs-presenting-uat, hard rule 1)."""
    text, _ = build()
    inputs = re.findall(r"<input[^>]*>", text)
    assert inputs, "the page has no controls"
    assert not [tag for tag in inputs if "checked" in tag], "a control arrives pre-checked"


def test_every_card_is_a_claim_the_key_makes():
    _, items = build()
    known = {claim.id for claim in all_claims()}
    assert items, "the arbitration surface has nothing to present"
    assert {item.claim_id for item in items} <= known


def test_a_shape_some_arm_passes_is_not_put_in_front_of_the_owner():
    """`long_cell` was the last key defect; it now passes for the Layout Parser."""
    _, items = build()
    keys = {item.claim_id.split(".")[0] for item in items}
    assert "long_cell" not in keys
    assert "qualifier" not in keys, "qualifier is passed by flash-lite `anchors` - not a key question"


def test_the_six_a_header_is_present_and_names_the_grouping():
    text, items = build()
    ids = {item.claim_id for item in items}
    assert "headerless_values.header" in ids
    claim = next(c for c in payload(text)["claims"] if c["id"] == "headerless_values.header")
    assert claim["expected"] == " | ".join(BY_KEY["headerless_values"].columns)
    assert len(claim["arms"]) >= 2, "a claim presented for arbitration must show why"
    assert all(arm["line"] for arm in claim["arms"])


def test_the_page_shows_the_keys_own_anchors_as_evidence():
    """The 6a defect was found by comparing the claim with the anchor beside it."""
    text, _ = build()
    anchor = BY_KEY["headerless_values"].anchors[1][1]
    assert anchor in html.escape(text)


# --- the attribution rule --------------------------------------------------------


@pytest.mark.parametrize(
    "shape,line,expected",
    [
        ("x", "x: row 3 cell 1 is 'a', expected 'b'", ("x.cell.3.1",)),
        ("x", "x: row 0 cell 4 must be empty, the read says 'a'", ("x.cell.0.4",)),
        ("x", "x: 20 rows, the page prints 19", ("x.rows",)),
        ("x", "x: row pages (4, 4) != (4, 4, 5)", ("x.pages",)),
        ("x", "x: columns ('a',) != ('b',)", ("x.header",)),
        (
            "x",
            "x: dividers () != ((0, 'A', 'part'), (3, 'B', 'qualifier'))",
            ("x.divider.0.part", "x.divider.3.qualifier"),
        ),
        ("x", "x: the extractor returned no table on pages [5] (0 table(s) found on those pages)", ()),
        ("x", "y: row 3 cell 1 is 'a'", ()),
    ],
)
def test_a_mismatch_line_names_the_claim_it_is_about(shape, line, expected):
    assert shape_disputes.attribute(shape, line) == expected


def test_the_gutter_convention_is_not_reported_as_a_disagreement_by_the_arms_it_repairs():
    """Appendix 7's leading `1`/`6b` column is a declared normalisation, not an arm defect.

    An arm whose *guttered* reading passes must contribute no Appendix 7 claim, because the gutter is
    declared on both sides. (First run of this module attributed `as_extracted`, and reported five
    arms disagreeing with the key on a shape two of them pass.)
    """
    arms = shape_disputes.load_arms()
    items = shape_disputes.disagreements(arms, threshold=2, unsatisfied_only=False)
    repaired = {
        arm.name for arm in arms if "column_major" in arm.passed
    }
    assert repaired, "the premise: some arms pass Appendix 7 once the gutter is declared"
    for item in items:
        if not item.claim_id.startswith("column_major."):
            continue
        culprits = {name for name, _ in item.arms} & repaired
        assert not culprits, f"{item.claim_id}: {culprits} pass this shape yet are counted against it"


def test_a_full_pass_is_only_counted_when_the_characters_are_verified():
    """`pass (grid only, quotes unresolved)` is not a pass — that is §3.12's whole point."""
    arms = {arm.name: arm for arm in shape_disputes.load_arms()}
    assert "page_break_row" not in arms["vlm claude-sonnet-5.5 lines"].passed
    assert "long_cell" in arms["documentai layout16pro"].passed
    assert "column_major" in arms["docling 2.146.0"].passed


# --- the amendment path ----------------------------------------------------------


def record_stub(claim_id: str) -> dict:
    return {
        "claims": {claim_id: {"kind": "header", "expected": current_claims()[claim_id]["expected"],
                              "verdict": "yes", "note": ""}},
        "reviewer": {"name": "Kobus", "seat": "Product"},
        "reviewed_at": "2026-11-05",
        "page_notes": {},
        "notes_resolved": {},
        "amendments": [],
    }


def arbitration_stub(claim_id: str, *, verdict="amend", to=None, basis="the paper prints it",
                     reviewed_at="2026-11-06") -> dict:
    return {
        "kind": shape_arbitration.KIND,
        "version": shape_arbitration.VERSION,
        "artefact": ARBITRATION_ARTEFACT,
        "reviewer": {"name": "Kobus", "seat": "Product"},
        "reviewed_at": reviewed_at,
        "claims": {claim_id: {"verdict": verdict, "expected": current_claims()[claim_id]["expected"],
                              "note": basis}},
        "amendments": [{"claim": claim_id, "from": current_claims()[claim_id]["expected"],
                        "to": to, "basis": basis}] if verdict == "amend" else [],
    }


def test_an_arbitration_is_refused_when_the_key_has_not_been_edited_yet():
    claim = "headerless_values.header"
    export, problems = arbitration_export(record_stub(claim), arbitration_stub(claim, to="something else"))
    assert export is None
    assert any("is not what the key says now" in problem for problem in problems)


def test_an_arbitration_is_refused_when_it_judges_nothing():
    claim = "headerless_values.header"
    export, problems = arbitration_export(record_stub(claim), arbitration_stub(claim, verdict="keep"))
    assert export is None
    assert any("changes nothing" in problem for problem in problems)


def test_an_amendment_to_the_text_the_key_now_says_is_applied():
    """The real shape of the `Step 3` fix, replayed: from = what he judged, to = what the key says."""
    claim = "headerless_values.header"
    record = record_stub(claim)
    arbitration = arbitration_stub(claim, to=current_claims()[claim]["expected"])
    # Pretend the reviewer judged a different text, so `from` differs from `to`.
    record["claims"][claim]["expected"] = "the older text"
    arbitration["claims"][claim]["expected"] = "the older text"
    arbitration["amendments"][0]["from"] = "the older text"
    export, problems = arbitration_export(record, arbitration)
    assert problems == []
    assert export["amendments"][0]["from"] == "the older text"
    assert export["amendments"][0]["to"] == current_claims()[claim]["expected"]
    assert export["claims"][claim]["expected"] == "the older text"
    assert export["claims"][claim]["note"] == arbitration["amendments"][0]["basis"]


def test_an_amendment_to_a_claim_already_amended_is_refused():
    claim = "long_cell.cell.0.0"
    record = record_stub(claim)
    record["claims"][claim]["reviewed_expected"] = "the text he judged"
    export, problems = arbitration_export(record, arbitration_stub(claim, to=current_claims()[claim]["expected"]))
    assert export is None
    assert any("already amended under review" in problem for problem in problems)


def test_the_arbitration_must_come_from_the_arbitration_surface():
    claim = "headerless_values.header"
    arbitration = arbitration_stub(claim, to=current_claims()[claim]["expected"])
    arbitration["artefact"] = "product/design/uat/shape_key_review.html"
    export, problems = arbitration_export(record_stub(claim), arbitration)
    assert export is None
    assert any("arbitrate_shapes.html" in problem for problem in problems)


def test_every_shape_in_the_key_is_either_arbitrable_or_set_aside():
    """No shape may be silently absent from both the page and the set-aside list."""
    arms = shape_disputes.load_arms()
    items = shape_disputes.disagreements(arms)
    arbitrable = {item.claim_id.split(".")[0] for item in items}
    passing = {shape for arm in arms for shape in arm.passed}
    for case in SHAPES:
        assert case.key in arbitrable | passing | set(shape_arbitration.PASSED_ELSEWHERE), (
            f"{case.key} is neither passed by an arm nor presented for arbitration"
        )
