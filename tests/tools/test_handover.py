"""`HANDOVER.md` is state; the history is an archive (CONTEXT_BUDGET.md §4.1).

**The rule this holds.** `HANDOVER.md` is the one file every session loads, and until 2026-11-02 it
was also the file every session appended to: 2,553 lines, of which 72 were the current state and
2,300 were 22 sessions of history. A log that only grows is expensive to read and unreliable to
trust — its numbers rot at different rates from its narrative, which is how a handover came to
claim "16 commits ahead" when the tree was 27.

So: state is short and checked; history is long and archived. These two tests make that a rule
rather than an intention.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOVER = REPO_ROOT / "HANDOVER.md"
ARCHIVE = REPO_ROOT / "product" / "docs" / "handover"

#: Measured 2,553 lines before the split. 250 is the budget, not the current size (139) — the room
#: is for a session or two of state growth before the next split is due.
BUDGET_LINES = 250

#: A session narrative's heading, `## 0u. …`. None may live in the state file: the moment one
#: does, this file starts growing again.
SESSION_HEADING = re.compile(r"^## 0[a-z]?\.\s", re.M)

#: The index line for an archived session: ``- `0u` … — [`SESSION_…md`](product/docs/handover/…)``.
INDEX_LINK = re.compile(r"\]\((product/docs/handover/[^)]+\.md)\)")


def test_the_state_file_is_within_its_budget():
    lines = HANDOVER.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= BUDGET_LINES, (
        f"HANDOVER.md is {len(lines)} lines (budget {BUDGET_LINES}). A session's narrative goes to "
        "product/docs/handover/ and gets one line in the index — see CONTEXT_BUDGET.md §4.1."
    )


def test_no_session_narrative_is_back_in_the_state_file():
    """The failure mode this guards: the next agent pastes its session into the top file."""
    text = HANDOVER.read_text(encoding="utf-8")
    found = SESSION_HEADING.findall(text)
    assert not found, (
        f"{len(found)} session section(s) are in HANDOVER.md again. Move them to the archive and "
        "leave one index line."
    )


def test_every_index_entry_resolves():
    """A dead link in the index is worse than no index: it sends the reader nowhere."""
    text = HANDOVER.read_text(encoding="utf-8")
    links = INDEX_LINK.findall(text)
    assert links, "the session index is empty — was the archive wiped?"
    missing = [link for link in links if not (REPO_ROOT / link).is_file()]
    assert not missing, missing


def test_every_archived_session_is_in_the_index():
    """The other direction: an archive file nobody links to is a session nobody will find."""
    text = HANDOVER.read_text(encoding="utf-8")
    linked = set(INDEX_LINK.findall(text))
    archived = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in ARCHIVE.glob("SESSION_*.md")
    }
    assert archived - linked == set(), sorted(archived - linked)
    assert linked - archived == set(), sorted(linked - archived)
