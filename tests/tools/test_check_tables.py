"""`scripts/check_tables.py` — the corpus gate, and the declaration it refuses to invent.

The harness (`knowledge/table_harness.py`) is proved by its own tests; this file pins the *gate*:
the four reviewed artefacts pass it, a wrong row count fails it, and a run with no declaration
refuses instead of printing a pass. The counts live here rather than in the script for the same
reason the S0 registry does: a count is reviewed data, and a test that fails when the artefact's
table changes shape is the point — a stale count that still passed would be the silent default
this repo's hazard log is full of.
"""

from __future__ import annotations

import scripts.check_tables as check_tables

#: `doc_key -> (pages mode, row count per table in document order)`. Measured from the artefacts on
#: 2026-11-03: landscape 3+2+3, opp 6. Same numbers as `knowledge/tests/test_table_harness.py`,
#: pinned twice on purpose — the harness's copy proves the checker, this one proves the command.
CORPUS = {
    "landscape": ("table", "3,2,3"),
    "opp": ("layout", "6"),
}


def test_every_reviewed_artefact_passes_the_gate(capsys):
    for doc_key, (mode, rows) in CORPUS.items():
        code = check_tables.main(["--doc", doc_key, "--rows", rows, "--pages-mode", mode])
        out = capsys.readouterr().out
        assert code == 0, out
        assert "ok" in out and "0 violations" in out, out


def test_a_wrong_row_count_fails_the_gate(capsys):
    code = check_tables.main(["--doc", "opp", "--rows", "7"])
    out = capsys.readouterr().out
    assert code == 1, out
    assert "FAIL" in out and "R4" in out, out


def test_no_declaration_is_a_refusal_and_not_a_pass(capsys):
    code = check_tables.main(["--doc", "opp"])
    captured = capsys.readouterr()
    assert code == 2, captured.out
    assert "refusing" in captured.err
    assert "ok" not in captured.out


def test_an_unknown_document_is_named(tmp_path, capsys):
    code = check_tables.main(["--doc", "not-a-standard", "--rows", "1"])
    assert code == 2
    assert "no reviewed artefact is declared" in capsys.readouterr().err


def test_a_malformed_row_declaration_is_an_error():
    import pytest

    with pytest.raises(SystemExit):
        check_tables.main(["--doc", "opp", "--rows", "six"])
