"""D85's verification surface: the page, its claims, and the record a signature leaves behind.

What is guarded here, and why each guard exists:

* **The artefact is generated, never hand-edited** (`--check`). A review surface that drifts from
  the key it shows is a second, unversioned copy of the key — the failure §3.10 is about.
* **Every claim the key makes is on the page, once** — a claim dropped from the page is a claim the
  owner cannot refute, and a duplicated one is two verdicts for one fact.
* **No network, ever** — the artefact opens from disk with the wifi off. Images are `data:` URIs
  from the committed, hash-pinned page renders, not files beside the HTML and not a CDN.
* **The record is pinned to the claim text it judged** — mutate one expected value and the drift
  check must name that claim. This is the guard that stops a signature outliving its subject, and
  it is exercised both ways here rather than trusted.
* **The export refuses blanks and reasons** — an unexplained `No` is a finding nobody can act on.

The page's *script* is not covered here; `tests/e2e/test_shape_review_artefact.py` drives it in a
real browser, because a page whose script does not parse leaves every structural assertion green
(`testing_hazards.md` §1.30).
"""

from __future__ import annotations

import json

import pytest

from knowledge.tests import shape_pages
from knowledge.tests.shape_fixtures import SHAPES, flat
from scripts import shape_review, shape_review_signoff

REPO_ROOT = shape_review.REPO_ROOT
ARTEFACT = shape_review.DEFAULT_OUT


@pytest.fixture(scope="module")
def html() -> str:
    """The committed artefact, read once. Regenerating it per test would hash 9 MB of PDFs each time."""
    return ARTEFACT.read_text(encoding="utf-8")


@pytest.fixture
def export() -> dict:
    """A complete all-Yes export, built from the key as it stands — the simplest valid signature."""
    return {
        "kind": shape_review.KIND,
        "version": shape_review.VERSION,
        "artefact": shape_review.ARTEFACT_NAME,
        "reviewer": {"name": "Probe Reviewer", "seat": "Product owner"},
        "reviewed_at": "2026-11-05",
        "claims": {
            claim.id: {"verdict": "yes", "expected": claim.expected, "note": ""}
            for claim in shape_review.all_claims()
        },
        "page_notes": {},
    }


def test_the_committed_artefact_is_current(capsys):
    """`--check` regenerates in memory and compares. A hand-edit is a fail, not a diff to read."""
    assert shape_review.main(["--check"]) == 0, capsys.readouterr().out


def test_every_claim_the_key_makes_is_on_the_page_once(html):
    ids = shape_review.claim_ids()
    assert len(ids) == len(set(ids)), "a claim id is not unique"

    for claim in shape_review.all_claims():
        assert html.count(f'data-claim="{claim.id}"') >= 1, claim.id
        assert shape_review.escape(claim.question) in html, claim.question
        assert shape_review.escape(claim.answer) in html, claim.answer

    fieldsets = html.count('<fieldset class="claim" data-claim=')
    assert fieldsets == len(ids), f"{fieldsets} verdict cards for {len(ids)} claims"


def test_the_page_carries_the_key_it_judges(html):
    """The payload a reviewer's export is built from, and the pin that makes it reproducible."""
    payload = json.loads(
        html.split('<script type="application/json" id="shape-data">', 1)[1].split("</script>", 1)[0]
    )
    assert payload["kind"] == shape_review.KIND
    assert payload["artefact"] == shape_review.ARTEFACT_NAME
    assert payload["key"] == "knowledge/tests/shape_fixtures.py"
    assert payload["key_sha256"] == shape_review_signoff.key_sha256()
    assert [s["key"] for s in payload["shapes"]] == [case.key for case in SHAPES]
    assert [c["id"] for s in payload["shapes"] for c in s["claims"]] == shape_review.claim_ids()


def test_no_claim_is_made_twice_by_claim_kind():
    """Every shape asserts its header and row count; a cell is asserted once, dividers in order."""
    for case in SHAPES:
        claims = shape_review.claims(case)
        kinds = [claim.kind for claim in claims]
        assert kinds.count("header") == 1 and kinds.count("rows") == 1
        assert kinds.count("cell") == len(case.cells)
        cells = [(claim.row, claim.column) for claim in claims if claim.kind == "cell"]
        assert len(cells) == len(set(cells)), case.key


def test_the_page_cannot_reach_the_network(html):
    """A review of the paper must not need the network — and must not silently leak one."""
    for forbidden in ("http://", "https://", "<link", "@import", "src=", "href="):
        assert forbidden not in html, f"the artefact contains {forbidden!r}"


def test_every_page_image_is_the_pinned_paper(html):
    """Images are read through the hash-checking accessor, so this fails on edited bytes."""
    for case in SHAPES:
        for page in case.pdf_pages:
            data = shape_pages.image(case.doc_key, page)
            assert data.startswith(b"\xff\xd8"), "the committed page is not a JPEG"
            css = shape_pages.css_class(case.doc_key, page)
            assert f'class="shot {css}"' in html, css
            assert f".{css}{{background-image:url(\"data:image/jpeg;base64," in html, css


def test_every_asserted_cell_is_filled_and_every_other_cell_says_it_is_unclaimed(html):
    """The grid's honesty: `—` is "not claimed", and it is never mistaken for "wrong"."""
    for case in SHAPES:
        section = html.split(f'id="shape-{case.key}"', 1)[1].split("<section", 1)[0]
        cells = section.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
        printed = case.row_count * len(case.columns)
        assert cells.count('class="claimed"') + cells.count('class="claimed empty"') == len(
            case.cells
        ), case.key
        assert cells.count('class="unclaimed"') == printed - len(case.cells), case.key


def test_an_unclaimed_cell_says_so_in_words(html):
    """A dash reads as "the paper is blank" — which is the opposite of what it means.

    The first reader of this page asked whether rows 2-5 of the fee table were *expected* to be
    empty. They are not: the paper prints 2,500 / 3,000 / 3,700 / 5,000 there and the key simply
    asserts none of it. So the word is "not claimed", the legend says it is not a claim of
    blankness, and no cell may be drawn as a bare dash again.
    """
    unclaimed = sum(
        case.row_count * len(case.columns) - len(case.cells) for case in SHAPES
    )
    assert html.count(">not claimed</td>") == unclaimed
    assert "it is not a claim that the paper is blank" in html
    assert "—</td>" not in html, "an unclaimed cell is still drawn as a dash"


def test_a_claimed_cell_shows_the_text_the_paper_must_print(html):
    """A cell claim without its text would ask the reviewer to judge a memory."""
    for case in SHAPES:
        for cell in case.cells:
            text = cell.text or cell.starts or cell.contains or cell.ends
            if text and len(text) <= 96:
                assert html.count(shape_review.escape(flat(text))) >= 1, f"{case.key}: {text[:40]}"


def test_the_record_pins_every_claim_to_the_text_it_judged(export):
    record = shape_review_signoff.build_record(export)
    assert shape_review_signoff.drift(record) == []
    assert record["summary"]["claims"] == len(shape_review.claim_ids())
    assert record["summary"]["yes"] == len(shape_review.claim_ids())
    assert record["summary"]["shapes_amended"] == []
    assert record["key_sha256"] == shape_review_signoff.key_sha256()


def test_a_changed_claim_makes_the_record_stale_and_names_it(export):
    """The signature must not outlive what it signed: change one cell, watch the guard go red."""
    record = shape_review_signoff.build_record(export)
    claim_id = shape_review.claim_ids()[-1]
    record["claims"][claim_id]["expected"] = "text=something the paper does not print"

    problems = shape_review_signoff.drift(record)
    assert any(claim_id in problem and "stale" in problem for problem in problems), problems


def test_a_claim_dropped_from_the_key_is_reported(export):
    record = shape_review_signoff.build_record(export)
    removed = shape_review.claim_ids()[0]
    del record["claims"][removed]

    problems = shape_review_signoff.drift(record)
    assert any(removed in problem for problem in problems), problems


def test_a_no_without_a_reason_is_refused(export):
    claim_id = shape_review.claim_ids()[0]
    export["claims"][claim_id]["verdict"] = "no"

    problems = shape_review_signoff.validate(export)
    assert any(claim_id in problem and "reason" in problem for problem in problems), problems


def test_an_unjudged_claim_is_refused(export):
    claim_id = shape_review.claim_ids()[3]
    del export["claims"][claim_id]

    problems = shape_review_signoff.validate(export)
    assert any(claim_id in problem for problem in problems), problems


def test_an_export_from_a_page_built_against_older_claims_is_refused(export):
    """A page left open while the key changed must not become a signature of the new key."""
    claim_id = shape_review.claim_ids()[1]
    export["claims"][claim_id]["expected"] = "an older reading"

    problems = shape_review_signoff.validate(export)
    assert any(claim_id in problem and "rebuild the surface" in problem for problem in problems)


def test_an_export_from_another_surface_is_refused(export):
    export["artefact"] = "product/design/uat/something_else.html"
    export["reviewer"]["name"] = " "

    problems = shape_review_signoff.validate(export)
    assert any("review surface" in problem for problem in problems), problems
    assert any("name" in problem for problem in problems), problems


def test_the_dry_run_writes_nothing_and_the_write_is_idempotent(tmp_path, monkeypatch, export):
    record = tmp_path / "shape_review.json"
    monkeypatch.setattr(shape_review_signoff, "RECORD_PATH", record)
    source = tmp_path / "export.json"
    source.write_text(json.dumps(export), encoding="utf-8")

    assert shape_review_signoff.main(["--from", str(source), "--dry-run"]) == 0
    assert not record.exists(), "a dry run wrote the record"

    assert shape_review_signoff.main(["--from", str(source)]) == 0
    first = record.read_text(encoding="utf-8")
    assert shape_review_signoff.main(["--from", str(source)]) == 0
    assert record.read_text(encoding="utf-8") == first, "re-applying the same export changed it"


def test_the_committed_record_describes_the_key_or_there_is_none():
    """If an owner has signed, the gate keeps that review true. No record yet is not a failure."""
    if not shape_review_signoff.RECORD_PATH.exists():
        pytest.skip("no review of record yet - D85 is unsigned")
    record = json.loads(shape_review_signoff.RECORD_PATH.read_text(encoding="utf-8"))
    assert shape_review_signoff.drift(record) == []

def test_a_partial_cell_claim_is_drawn_as_partial(html):
    """`starts`/`contains`/`ends` are fragments. The grid must not show one as a whole cell.

    The first reviewer read "Step 1" in this grid and said "we're missing loads of text — the cells
    in the pdf don't just say the step name". The paper is right and the claim is a prefix, but the
    grid said otherwise. Every partial claim now carries an ellipsis where the cell goes on.
    """
    for case in SHAPES:
        section = html.split(f'id="shape-{case.key}"', 1)[1].split("<section", 1)[0]
        cells = section.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
        for cell in case.cells:
            if cell.text is not None or cell.empty:
                continue
            fragment = cell.starts or cell.contains or cell.ends
            assert fragment, case.key
            assert f"{shape_review.escape(fragment)} …" in cells or (
                f"… {shape_review.escape(fragment)}" in cells
            ), f"{case.key}: the grid draws {fragment!r} as if it were the whole cell"


def test_a_page_note_keeps_a_shape_out_of_confirmed(export):
    """Every claim Yes, but the reviewer wrote "is this expected?" — that shape is not settled."""
    export["page_notes"] = {"long_cell": "The first column has a bolded Step 3 that is missing here."}
    record = shape_review_signoff.build_record(export)

    summary = record["summary"]
    assert summary["yes"] == summary["claims"]
    assert "long_cell" in summary["shapes_with_open_questions"]
    assert "long_cell" not in summary["shapes_confirmed"]
    assert "numeric_row" in summary["shapes_confirmed"]
    assert record["page_notes"]["long_cell"].startswith("The first column")

def test_an_amended_claim_must_name_what_the_reviewer_saw(export):
    """`long_cell`'s first cell was corrected after the owner judged it. Both texts must be pinned.

    The amendment is the only way an `expected` may differ from the key: `from` is what the reviewer
    actually read, `to` is what the key says now, and `basis` is the finding that justifies it. A
    record that silently pins the new text to the old signature is a lie about the signature.
    """
    claim_id = "long_cell.cell.0.0"
    claim = next(c for c in shape_review.all_claims() if c.id == claim_id)
    seen = "starts=The group conducts farm visits and"
    assert claim.expected != seen, "the fixture no longer differs from the text the owner reviewed"

    export["claims"][claim_id]["expected"] = seen
    assert any(claim_id in p and "rebuild the surface" in p for p in shape_review_signoff.validate(export))

    export["amendments"] = [
        {"claim": claim_id, "from": seen, "to": claim.expected, "basis": "the owner's page note"}
    ]
    assert shape_review_signoff.validate(export) == []

    record = shape_review_signoff.build_record(export)
    entry = record["claims"][claim_id]
    assert entry["expected"] == claim.expected
    assert entry["reviewed_expected"] == seen
    assert entry["amendment_basis"].startswith("the owner")
    assert record["summary"]["claims_amended_under_review"] == [claim_id]
    assert shape_review_signoff.drift(record) == []


def test_a_wrongly_specified_amendment_is_refused(export):
    claim_id = "long_cell.cell.0.0"
    export["claims"][claim_id]["expected"] = "an older reading"
    export["amendments"] = [
        {"claim": claim_id, "from": "something else", "to": "x", "basis": "b"}
    ]
    problems = shape_review_signoff.validate(export)
    assert any("must say from=" in problem for problem in problems), problems


def test_an_amendment_without_a_basis_is_refused(export):
    claim_id = "long_cell.cell.0.0"
    claim = next(c for c in shape_review.all_claims() if c.id == claim_id)
    export["claims"][claim_id]["expected"] = "an older reading"
    export["amendments"] = [{"claim": claim_id, "from": "an older reading", "to": claim.expected}]
    problems = shape_review_signoff.validate(export)
    assert any("basis" in problem for problem in problems), problems


def test_the_committed_record_pins_the_amended_claim(html):
    """The real record: 68 yes, eight shapes confirmed, one claim amended under review."""
    record = json.loads(shape_review_signoff.RECORD_PATH.read_text(encoding="utf-8"))
    summary = record["summary"]
    assert summary["claims"] == len(shape_review.claim_ids())
    assert summary["shapes_confirmed"] == [case.key for case in SHAPES]
    assert summary["claims_amended_under_review"] == ["long_cell.cell.0.0"]
    entry = record["claims"]["long_cell.cell.0.0"]
    assert entry["expected"].startswith("starts=Step 3")
    assert entry["reviewed_expected"] == "starts=The group conducts farm visits and"
    # and the page shows the corrected claim, with the prose still asserted
    section = html.split('id="shape-long_cell"', 1)[1].split("<section", 1)[0]
    assert "Step 3" in section and "The group conducts farm visits and" in section
