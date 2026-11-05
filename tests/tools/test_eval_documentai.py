"""`scripts/eval_documentai.py` — the third arm's instrument, and the two things that can go wrong.

The lessons this file encodes were both learned the hard way on 2026-11-04:

* **It imports with no credential, no `pypdfium2` and no `google-auth`** — the gate must never need an
  extractor or a secret (requirement 10), so both are imported lazily inside the functions that use
  them.
* **The two processors do not agree about where a table lives.** The Form Parser returns
  `pages[].tables[]` with cells anchored into `document.text`; the Layout Parser returns a *block
  hierarchy* (`textBlock.blocks[].tableBlock`) with cells as `blocks[].textBlock.text` and **no
  `document.text` at all**. Reading only the first shape scored the Layout Parser **0 of 8, "no table
  found" on every page** — our bug reported as the tool's result. `tables_from` handles both, and the
  test below is the guard.
* **A merged cell is filed under the first cell it covers**, and the slots it covers are empty — the
  fixtures' convention, not Docling's replication.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import scripts.eval_documentai as evaluator

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_it_imports_without_a_credential_or_a_rasteriser():
    code = (
        "import sys, scripts.eval_documentai; "
        "assert 'pypdfium2' not in sys.modules, sorted(sys.modules); "
        "assert 'google.auth' not in sys.modules, sorted(sys.modules); "
        "print('ok')"
    )
    result = subprocess_result(code)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout


def subprocess_result(code: str):
    import subprocess

    return subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True
    )


def test_an_unknown_shape_is_refused_with_the_known_ones(capsys):
    assert (
        evaluator.main(
            ["--processor", "form=x", "--project", "p", "--shape", "numeric_row,nonsense"]
        )
        == 2
    )
    err = capsys.readouterr().err
    assert "nonsense" in err and "numeric_row" in err


def test_a_processor_without_an_id_is_refused(capsys):
    assert evaluator.main(["--processor", "form=", "--project", "p"]) == 2
    assert "name=id" in capsys.readouterr().err


# --- the two response shapes ------------------------------------------------------------------

def anchor(start: int, end: int) -> dict:
    return {"layout": {"textAnchor": {"textSegments": [{"startIndex": start, "endIndex": end}]}}}


def text_cell(text: str) -> dict:
    return {"blocks": [{"textBlock": {"text": text, "type": "paragraph"}}], "rowSpan": 1, "colSpan": 1}


def anchor(start: int, end: int) -> dict:
    return {"layout": {"textAnchor": {"textSegments": [{"startIndex": start, "endIndex": end}]}}}


def text_cell(text: str) -> dict:
    return {"blocks": [{"textBlock": {"text": text, "type": "paragraph"}}], "rowSpan": 1, "colSpan": 1}

FORM_TEXT = "Annual farm turnover Initial fee Below R 250,000 1,500"


def anchor_at(phrase: str) -> dict:
    """A text anchor pointing at a phrase — computed, so the fixture cannot drift off by one."""
    start = FORM_TEXT.index(phrase)
    return anchor(start, start + len(phrase))


FORM = {
    "text": FORM_TEXT,
    "pages": [
        {
            "tables": [
                {
                    "headerRows": [
                        {"cells": [anchor_at("Annual farm turnover"), anchor_at("Initial fee")]}
                    ],
                    "bodyRows": [
                        {"cells": [anchor_at("Below R 250,000"), anchor_at("1,500")]}
                    ],
                }
            ]
        }
    ],
}
LAYOUT = {
    "documentLayout": {
        "blocks": [
            {
                "pageSpan": {"pageStart": 1},
                "textBlock": {
                    "type": "heading-2",
                    "text": "2.3 Fees",
                    "blocks": [
                        {
                            "tableBlock": {
                                "headerRows": [{"cells": [text_cell("Annual farm turnover"), text_cell("Initial fee")]}],
                                "bodyRows": [{"cells": [text_cell("Below R 250,000"), text_cell("1,500")]}],
                            }
                        }
                    ],
                },
            }
        ]
    }
}


def test_the_form_parsers_anchored_cells_are_read():
    tables = evaluator.tables_from(FORM, (2,))
    assert len(tables) == 1
    assert tables[0]["columns"] == ("Annual farm turnover", "Initial fee")
    assert tables[0]["rows"] == [["Below R 250,000", "1,500"]]
    assert tables[0]["page"] == 2, "the printed page, not the pdf page"


def test_the_layout_parsers_nested_blocks_are_read():
    """The guard for the bug: a table nested under its heading, with no `document.text` at all."""
    tables = evaluator.tables_from(LAYOUT, (2,))
    assert len(tables) == 1, "the table is inside textBlock.blocks[], not pages[].tables[]"
    assert tables[0]["columns"] == ("Annual farm turnover", "Initial fee")
    assert tables[0]["rows"] == [["Below R 250,000", "1,500"]]
    assert tables[0]["page"] == 2


def test_reading_only_one_shape_would_have_found_nothing():
    """Proves the two readers are not the same reader: the layout response has no `pages`."""
    assert not LAYOUT.get("pages")
    assert not FORM.get("documentLayout")


def test_a_merged_cell_is_filed_under_its_first_slot():
    table = {
        "headerRows": [{"cells": [text_cell("Key steps"), text_cell("Fee")]}],
        "bodyRows": [
            {
                "cells": [
                    text_cell("Step 1"),
                    {"blocks": [{"textBlock": {"text": "R500"}}], "rowSpan": 2, "colSpan": 1},
                ]
            },
            {"cells": [text_cell("Step 2")]},
        ],
    }
    built = evaluator._rectangular(table, {})
    assert built["rows"] == [["Step 1", "R500"], ["Step 2", ""]], "the covered slot is empty, not filled"


def test_a_table_with_no_cells_is_not_a_table():
    assert evaluator._rectangular({"headerRows": [], "bodyRows": []}, {}) is None
