"""`scripts/check_tables.py` — the corpus gate, and the declarations it refuses to invent.

The harness (`knowledge/table_harness.py`) is proved by its own tests; this file pins the *gate*:
the four reviewed artefacts pass it, a wrong row count fails it, and a run with no declaration
refuses instead of printing a pass. The counts live here rather than in the script for the same
reason the S0 registry does: a count is reviewed data, and a test that fails when the artefact's
table changes shape is the point — a stale count that still passed would be the silent default
this repo's hazard log is full of.

**The extraction mode is not in this file's data any more** (S3). It lives on the artefact
(`extraction:` in each block), because it is the one per-document datum nothing can guess: the
landscape's reviewed cells pass against `-table` and fail ten ways against `-layout`. The gate
reads it, refuses an artefact that does not say, and refuses a `--pages-mode` that contradicts one
that does.
"""

from __future__ import annotations

import pytest

import scripts.check_tables as check_tables

#: `doc_key -> row count per table in document order`. Measured from the artefacts on 2026-11-03
#: (landscape 3+2+3, opp 6), 2026-11-05 (saoso's Appendix 2, 30, and Appendix 6a, 20 — S5's first
#: two emitted tables) and 2026-11-06 (Appendix 7, 7 — S5-c's grid). Same numbers as
#: `knowledge/tests/test_table_harness.py`, pinned twice on purpose — the harness's copy proves the
#: checker, this one proves the command.
CORPUS = {
    "landscape": "3,2,3",
    "opp": "6",
    "saoso": "30,20,7",
}

HEADER = """<!-- corpus
doc_key: opp
source: pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf
sha256: 0000000000000000000000000000000000000000000000000000000000000000
generator: knowledge corpusgen v2
-->"""

#: One block, no `extraction:` — the artefact every document written before S3 looks like.
BLOCK_WITHOUT_MODE = """
<!-- page: 2 printed: 2 -->
## 2.3 A heading
<!-- table
cols: A | B
-->
<!-- row: one -->
<!-- cell -->
one
<!-- cell -->
two
<!-- /table -->
"""


def artefact(block: str = BLOCK_WITHOUT_MODE) -> str:
    return HEADER + block


def test_every_reviewed_artefact_passes_the_gate(capsys):
    for doc_key, rows in CORPUS.items():
        code = check_tables.main(["--doc", doc_key, "--rows", rows])
        out = capsys.readouterr().out
        assert code == 0, out
        assert "ok" in out and "0 violations" in out, out


def test_the_mode_is_read_from_the_artefact_and_not_from_a_flag(capsys):
    assert check_tables.main(["--doc", "landscape", "--rows", "3,2,3"]) == 0
    assert "recorded on the artefact" in capsys.readouterr().out


def test_a_flag_that_disagrees_with_the_artefact_is_refused(capsys):
    code = check_tables.main(["--doc", "landscape", "--rows", "3,2,3", "--pages-mode", "layout"])
    captured = capsys.readouterr()
    assert code == 2, captured.out
    assert "records `table`" in captured.err and "layout" in captured.err
    assert "ok" not in captured.out


def test_an_artefact_that_records_no_mode_is_refused_and_not_judged(tmp_path, monkeypatch, capsys):
    """The guess this removes: the old default was `layout`, so a `-table` artefact was judged
    against the wrong paper and the failure looked like the transcription's."""
    plain = tmp_path / "opp.md"
    plain.write_text(artefact(), encoding="utf-8")
    monkeypatch.setattr(check_tables, "corpus_artifact", lambda _key: plain)
    code = check_tables.main(["--doc", "opp", "--rows", "1"])
    captured = capsys.readouterr()
    assert code == 2 and "no block in this artefact records" in captured.err
    assert "ok" not in captured.out


def test_two_modes_in_one_artefact_are_refused_by_name(tmp_path, monkeypatch, capsys):
    """One run has one `pages` sequence, so two passes is a gate about to read one paper and
    report on another — `recorded_extraction` names the pair."""
    mixed = tmp_path / "opp.md"
    mixed.write_text(
        artefact(
            BLOCK_WITHOUT_MODE.replace("cols: A | B", "cols: A | B\nextraction: table")
            + BLOCK_WITHOUT_MODE.replace("cols: A | B", "cols: A | B\nextraction: layout")
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(check_tables, "corpus_artifact", lambda _key: mixed)
    code = check_tables.main(["--doc", "opp", "--rows", "1"])
    captured = capsys.readouterr()
    assert code == 2 and "table" in captured.err and "layout" in captured.err


def test_a_draft_without_a_recorded_mode_may_be_judged_with_the_flag(tmp_path, monkeypatch, capsys):
    """`--pages-mode` is the draft-only escape: S3's generator records the mode, but a draft
    written before it did can still be checked, deliberately and on the record."""
    plain = tmp_path / "opp.md"
    plain.write_text(artefact(), encoding="utf-8")
    monkeypatch.setattr(check_tables, "corpus_artifact", lambda _key: plain)
    code = check_tables.main(["--doc", "landscape", "--rows", "1", "--pages-mode", "table"])
    captured = capsys.readouterr()
    assert code == 1, captured.out          # R3 says the cells are not on that page
    assert "no block in this artefact records" not in captured.err
    assert "--pages-mode" in captured.out   # and the report says the datum was supplied by hand


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
    with pytest.raises(SystemExit):
        check_tables.main(["--doc", "opp", "--rows", "six"])
