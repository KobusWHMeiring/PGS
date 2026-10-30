"""`product/backlog.py --board-json` — classification for the public board, and nothing else.

The generator (`scripts/board.py`) must not know `STATUS_RULES`. This mode is the seam: it
classifies with the *one* table that already exists, and emits JSON. It formats nothing and
writes no file, so `backlog.py` stays a backlog maintainer rather than a web tool.

Three failures here are silent in the product:

1. **A card appears without `**Public:** yes`.** The whole feature is "curated, not mirrored";
   a leak that starts here cannot be caught downstream, because downstream only sees what it
   is handed.
2. **An opted-in PRD is *dropped*** for a missing or oversized summary. A silent drop makes
   the board look complete while a maintained item is missing — `testing_hazards.md` §1.6 with
   a directory behind it. Hence `rejected`, and the generator treats one rejection as fatal.
3. **`Status:`, `Owner:` or `Last Updated:` reaches the card.** A board that prints how long an
   item has sat there invites a reader to judge velocity; the PRD's own status line is a note
   to ourselves and routinely says "superseded" or "blocking decisions".

Run:  python product/backlog.py --board-json
"""

from __future__ import annotations

import json

import pytest

from scripts.board import load_backlog_module


@pytest.fixture
def backlog(tmp_path, monkeypatch):
    """The real `product/backlog.py`, pointed at a throwaway tree.

    Loaded **by path**, never by import: `product/` holds both `backlog.py` and `backlog/`,
    and `sys.path.insert(0, "product"); import backlog` resolves to the module only by luck.
    Adding `product/backlog/__init__.py` would flip it to the package and the import would
    silently change meaning.
    """
    module = load_backlog_module()
    monkeypatch.setattr(module, "BACKLOG", tmp_path)
    monkeypatch.setattr(module, "INDEX", tmp_path / "backlog.md")
    monkeypatch.setattr(module, "TODO", tmp_path / "todo.md")
    return module


def _prd(backlog_root, rel, *, status="Ready", summary=None, public=True, updated="2026-10-01"):
    """Write one PRD under the fixture tree, in the shape `scan()` expects."""
    path = backlog_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# PRD: {path.stem.replace('_', ' ').title()}",
        "",
        f"**Status:** {status}",
        "**Owner:** Product",
        f"**Last Updated:** {updated}",
    ]
    if summary is not None:
        lines.append(f"**Summary:** {summary}")
    if public:
        lines.append("**Public:** yes")
    lines += ["", "---", "", "## 1. Problem Statement", "", "Body."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_only_opted_in_prds_become_cards(backlog):
    _prd(backlog.BACKLOG, "ready/opted_in.md", summary="One sentence a farmer can read.")
    _prd(backlog.BACKLOG, "ready/not_opted_in.md", summary="Never published.", public=False)

    payload = backlog.board_payload()

    assert [c["title"] for c in payload["cards"]] == ["Opted In"]
    assert payload["rejected"] == [], "an unopted PRD is not a rejection, it is just invisible"


def test_a_card_carries_no_status_owner_or_date_as_content(backlog):
    """The card is title, summary, column, and one date **for ordering only**."""
    _prd(
        backlog.BACKLOG,
        "In Progress/thing.md",
        status="In Progress — Marc says the seam is blocked",
        summary="Something is being built.",
        updated="2026-10-05",
    )

    card = backlog.board_payload()["cards"][0]

    assert set(card) == {"title", "summary", "column", "updated", "rel"}
    assert card["column"] == "in_progress"
    assert card["updated"] == "2026-10-05"
    assert "seam" not in json.dumps(card), "the status line leaked into the card"


def test_an_opted_in_prd_without_a_summary_is_rejected_not_dropped(backlog):
    """The distinction is the whole safety property: a drop is invisible, a rejection is not."""
    _prd(backlog.BACKLOG, "ready/no_summary.md", public=True)

    payload = backlog.board_payload()

    assert payload["cards"] == []
    assert len(payload["rejected"]) == 1
    assert payload["rejected"][0]["rel"].endswith("no_summary.md")
    assert "summary" in payload["rejected"][0]["reason"].lower()


def test_an_overlong_summary_is_rejected(backlog):
    _prd(backlog.BACKLOG, "ready/wordy.md", summary="x" * 181)
    _prd(backlog.BACKLOG, "ready/exactly.md", summary="y" * 180)
    payload = backlog.board_payload()

    assert [c["title"] for c in payload["cards"]] == ["Exactly"]
    assert [r["rel"] for r in payload["rejected"]] == ["ready/wordy.md"]


def test_a_bucket_with_no_column_is_rejected(backlog):
    """`spike/`, `BugFixes/` and `on_hold/` have no column. A `Public: yes` there is a mistake
    to fix, not a card to hide — the leakiest material in the tree lives in those directories."""
    _prd(backlog.BACKLOG, "spike/investigate.md", status="Spike", summary="A research task.")
    payload = backlog.board_payload()

    assert payload["cards"] == []
    assert "column" in payload["rejected"][0]["reason"].lower()


def test_the_digest_ignores_an_unpublished_prd_and_tracks_a_published_one(backlog):
    """The digest is what `--check` compares. It must move when a *card* changes, and only then:
    otherwise every internal PRD edit would force a board regeneration and the artefact would
    churn in unrelated commits."""
    _prd(backlog.BACKLOG, "ready/card.md", summary="A card.")
    baseline = backlog.board_payload()["digest"]

    _prd(backlog.BACKLOG, "ready/internal.md", summary="An internal note.", public=False)
    assert backlog.board_payload()["digest"] == baseline, "an unpublished edit moved the digest"

    _prd(backlog.BACKLOG, "ready/card.md", summary="A card, edited.")
    assert backlog.board_payload()["digest"] != baseline


def test_a_public_title_overrides_an_internal_heading(backlog):
    """`# PRD: MVP 1a — In-Office Visit Flow` is a heading, and a delivery-slice label is not
    something a farmer asked for. The override is the only reason the field exists."""
    path = _prd(backlog.BACKLOG, "ready/mvp_1a.md", summary="A card.")
    text = path.read_text(encoding="utf-8").replace(
        "**Summary:**", "**Public title:** Applying for assessment, online\n**Summary:**", 1
    )
    path.write_text(text, encoding="utf-8")

    assert backlog.board_payload()["cards"][0]["title"] == "Applying for assessment, online"


def test_the_payload_is_json_serialisable(backlog):
    """`--board-json` pipes through `json.dumps`; a `Path` in a card is a `TypeError` at the
    last possible moment."""
    _prd(backlog.BACKLOG, "ready/card.md", summary="A card.")
    payload = backlog.board_payload()
    assert json.loads(json.dumps(payload))["version"] == 1
