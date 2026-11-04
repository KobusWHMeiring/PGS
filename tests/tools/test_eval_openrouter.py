"""`scripts/eval_openrouter.py` and `scripts/vlm_grid.py` — the VLM arm's instrument.

The runner is the network half; `vlm_grid` is the half that decides whether the model's JSON becomes
a `TableRead` the page can vouch for. That second half is where the three guards live.

The arm's whole claim is that **the model proposes the grid and the page supplies the characters**
(`INGESTION_ENGINE_PRD.md` §3.6). That claim is only worth as much as the resolver, so the tests here
are mostly about the resolver refusing things:

* it **imports with no rasteriser and no key**, because the gate must never need either (requirement
  10, and the same test the Docling instrument carries);
* it refuses an unknown shape rather than silently scoring fewer than eight;
* it refuses to run when the rasteriser is absent, rather than reporting an empty page as a score;
* **a quote that is not a contiguous run of its page is a violation**, and one that is printed *later*
  on the page than the cell it sits in is a different violation;
* a cell built from anchors is **the page's characters**, and an anchor the page does not print is a
  violation — not a quietly-empty cell;
* a line number the page does not have is a violation;
* the one declared normalisation is declared: letter-spaced page text is reported, never silently
  rejoined.

Every one of these was watched failing before it was trusted (`testing_hazards.md` §1.5).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import scripts.eval_openrouter as evaluator
import scripts.vlm_grid as grid

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_it_imports_without_the_rasteriser_or_a_key():
    """A fresh interpreter, with the key removed: importing must not need either."""
    code = (
        "import os, sys; os.environ.pop('OPENROUTER_API_KEY', None); "
        "import scripts.eval_openrouter; "
        "assert 'pypdfium2' not in sys.modules, sorted(sys.modules); "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout


def test_an_unknown_shape_is_refused_with_the_known_ones(capsys):
    assert evaluator.main(["--shape", "numeric_row,nonsense", "--mode", "lines"]) == 2
    err = capsys.readouterr().err
    assert "nonsense" in err
    assert "numeric_row" in err, "the refusal names what does exist"


def test_without_the_rasteriser_it_stops_rather_than_scoring_nothing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_pdfium(name, *args, **kwargs):
        if name.startswith("pypdfium2"):
            raise ImportError("No module named 'pypdfium2'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_pdfium)
    with pytest.raises(SystemExit) as raised:
        evaluator.render("pgs_docs/does-not-matter.pdf", (1,))
    assert "pypdfium2 is not installed" in str(raised.value)


def test_without_a_key_it_says_which_key_and_where_it_lives(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(SystemExit) as raised:
        evaluator._api_key()
    assert "OPENROUTER_API_KEY" in str(raised.value)


# --- the resolver -------------------------------------------------------------------------------

PAGE = (
    "Class or species Maximum number of animals per ha "
    "Equines over six months old 2 "
    "Other b o v i n e a n i m a l s less t h a n o n e year old 1 "
    "Laying hens 230"
)
RUNS = {85: grid.flat(PAGE)}


def test_a_verbatim_line_resolves_to_the_page_characters():
    found = grid.resolve("Equines over six months old", RUNS, {})
    assert found["ok"]
    assert found["text"] == "Equines over six months old"
    assert found["normalisation"] == []


def test_a_paraphrase_is_a_violation_not_a_quiet_cell():
    """The guard must be able to fail: 'bovine' is not on this page, 'b o v i n e' is."""
    found = grid.resolve("Equines over 6 months old", RUNS, {})
    assert not found["ok"]
    assert found["reason"] == "not a contiguous run of any page"


def test_a_line_printed_earlier_on_the_page_is_its_own_violation():
    """Order is half of requirement 3: a cell cannot reach back up the page."""
    cursor = {85: grid.flat(PAGE).find("Laying hens")}
    found = grid.resolve("Equines over six months old", RUNS, cursor)
    assert not found["ok"]
    assert "out of printed order" in found["reason"]


def test_the_letter_spacing_normalisation_is_declared_not_silent():
    found = grid.resolve("Other bovine animals less than one year old", RUNS, {})
    assert found["ok"]
    assert found["normalisation"] == ["letter_spacing"], "a normalisation applied silently is the bug"
    assert found["text"] == "Other bovine animals less than one year old"


def test_despacing_only_removes_spaces():
    """Measured 2026-11-04: a first version ate the space in 'R 5,000,000' and scored a right answer
    wrong. The comparison is whole-string and cannot touch a character."""
    assert grid.despace("Above R 5,000,000") == "AboveR5,000,000"
    assert grid.despace("t h a n") == "than"


def test_a_letter_spaced_cell_is_reported_beside_the_score():
    assert grid.has_letter_spacing("Other b o v i n e a n i m a l s")
    assert not grid.has_letter_spacing("Above R 5,000,000")


# --- the anchor slice ---------------------------------------------------------------------------

MAPPED = grid.index_map(RUNS[85])


def test_a_cell_built_from_anchors_is_the_pages_own_characters():
    found = grid.slice_span("Equines over", "months old", RUNS[85], MAPPED)
    assert found["ok"]
    assert found["text"] in RUNS[85], "every character came from the page"


def test_an_anchor_the_page_does_not_print_is_a_violation():
    found = grid.slice_span("Equines over", "six years old", RUNS[85], MAPPED)
    assert not found["ok"]
    assert "last words are not on the page" in found["reason"]


def test_an_empty_cell_is_an_empty_cell_not_a_guess():
    found = grid.slice_span("", "", RUNS[85], MAPPED)
    assert found["ok"] and found["text"] == ""


# --- the line-number form -----------------------------------------------------------------------

NUMBERED = {85: ["Class or species Maximum number of animals per ha", "Equines over six months old 2"]}


def _proposal(cells, **extra):
    return {"columns": [], "rows": [{"page": 1, "cells": cells}], "dividers": [], **extra}


def test_a_line_number_is_joined_from_the_page():
    read, violations = grid.read_from_indices(
        _proposal([[2], [1]]), _case(), {}, NUMBERED
    )
    assert read.rows == (("Equines over six months old 2", "Class or species Maximum number of animals per ha"),)
    assert violations == []


def test_a_line_the_page_does_not_have_is_a_violation():
    read, violations = grid.read_from_indices(_proposal([[9]]), _case(), {}, NUMBERED)
    assert read.rows == (("",),)
    assert violations and violations[0]["reason"] == "the page prints 2 lines"


def test_a_line_above_the_row_band_is_a_violation():
    proposal = {
        "columns": [],
        "rows": [
            {"page": 1, "cells": [[2]]},
            {"page": 1, "cells": [[1]]},
        ],
        "dividers": [],
    }
    _, violations = grid.read_from_indices(proposal, _case(), {}, NUMBERED)
    assert violations and "above the row band" in violations[0]["reason"]


# --- the model's answer -------------------------------------------------------------------------


def test_a_fenced_object_is_read_and_prose_is_not():
    assert evaluator.parse_json('```json\n{"rows": []}\n```') == {"rows": []}
    assert evaluator.parse_json("I could not read the table.") is None
    assert evaluator.parse_json('{"rows": [') is None


def _case():
    """The case the line-number fixtures above are keyed to: PDF 86 is printed page 85."""
    from knowledge.tests.shape_fixtures import BY_KEY

    return BY_KEY["headerless_values"]
