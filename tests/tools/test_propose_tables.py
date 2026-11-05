"""`scripts/propose_tables.py` — the arm's structure, reduced to committed data.

Two things this file is guarding, and the first is the mistake §3.9 already made once:

* **The Layout Parser nests its tables.** `documentLayout.blocks[].textBlock.blocks[]…tableBlock`,
  cells as `blocks[].textBlock.text`, no `document.text`. The reducer reuses
  `eval_documentai.layout_tables`, so a second reader cannot re-introduce the bug that scored this
  arm 0 of 8.
* **Two structures are refusals, not flattenings.** A response with no table and a merged cell both
  end in an exit and a sentence: the block format cannot express a span yet, and an empty proposal
  would say "no table here" in the same file as "the emitter verified one".

It is also a requirement-10 guard in miniature: the module imports no credential, no rasteriser and
no network client, so a machine with neither can still produce and re-read a proposal.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.propose_tables as reducer

REPO_ROOT = Path(__file__).resolve().parents[2]


def block(texts, spans=None):
    """One row of the Layout Parser's shape: cells as `blocks[].textBlock.text`."""
    cells = []
    for index, text in enumerate(texts):
        cell = {"blocks": [{"textBlock": {"text": text}}]}
        if spans and index in spans:
            cell.update(spans[index])
        cells.append(cell)
    return {"cells": cells}


def response(header, body):
    return {
        "documentLayout": {
            "blocks": [
                {
                    "blockId": "1",
                    "textBlock": {
                        "text": "2.3 A heading",
                        "blocks": [
                            {"tableBlock": {"headerRows": [block(header)], "bodyRows": [block(r) for r in body]}}
                        ],
                    },
                }
            ]
        }
    }


def write(tmp_path, payload):
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_the_layout_parsers_grid_becomes_a_proposal(tmp_path):
    """The arm's shape, not ours: headerRows then bodyRows, one rectangle out."""
    path = write(tmp_path, response(["A", "B"], [["1", "2"], ["3", ""]]))
    tables = reducer.structure_from(path, "opp", (2,))
    assert tables[0]["columns"] == ["A", "B"]
    assert [row["cells"] for row in tables[0]["rows"]] == [["1", "2"], ["3", ""]]
    assert tables[0]["pdf_pages"] == [2], "the page that was sent, not the image index"


def test_a_second_table_on_the_second_page_is_filed_under_that_pdf_page(tmp_path):
    """A shape may send two images (the landscape's page-break row does); the proposal records the
    PDF page, not the image index, because everything downstream cites the PDF."""
    payload = response(["A"], [["1"]])
    payload["documentLayout"]["blocks"].append(
        {
            "blockId": "2",
            "tableBlock": {"headerRows": [block(["A"])], "bodyRows": [block(["2"])]},
            "pageSpan": {"pageStart": 2, "pageEnd": 2},
        }
    )
    tables = reducer.structure_from(write(tmp_path, payload), "landscape", (4, 5))
    assert [table["pdf_pages"] for table in tables] == [[4], [5]]


def test_a_merged_cell_is_refused_because_no_declaration_can_express_it_yet(tmp_path):
    path = write(tmp_path, response(["A", "B"], [["1", "2"]], ))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["documentLayout"]["blocks"][0]["textBlock"]["blocks"][0]["tableBlock"]["bodyRows"] = [
        {
            "cells": [
                {"blocks": [{"textBlock": {"text": "spans two rows"}}], "rowSpan": 2},
                {"blocks": [{"textBlock": {"text": "2"}}]},
            ]
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(reducer.ProposalError, match="covers 2x1 slots"):
        reducer.structure_from(path, "landscape", (4,))


def test_a_response_with_no_table_is_refused_rather_than_written_empty(tmp_path, capsys):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"documentLayout": {"blocks": []}}), encoding="utf-8")
    out = tmp_path / "proposal.json"
    code = reducer.main(
        [
            "--response", str(empty),
            "--doc", "opp", "--pages", "2", "--extraction", "layout",
            "--processor", "id@version", "--json", str(out),
        ]
    )
    assert code != 0, "an empty proposal must not be written"
    assert not out.exists()
    assert "no table" in capsys.readouterr().err


def test_the_written_proposal_carries_the_processor_and_the_cache_it_came_from(tmp_path):
    path = write(tmp_path, response(["A", "B"], [["1", "2"]]))
    out = tmp_path / "proposal.json"
    code = reducer.main(
        [
            "--response", str(path),
            "--doc", "opp", "--pages", "2", "--extraction", "layout",
            "--processor", "68e@pretrained-layout-parser-v1.6-pro-2025-12-01",
            "--project", "803140233794", "--json", str(out), "--captured", "2026-11-05",
        ]
    )
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["structure"] == reducer.DEFAULT_STRUCTURE
    assert payload["processor"].startswith("68e@pretrained-layout-parser")
    assert payload["captured"] == "2026-11-05"
    assert payload["reduced_from"].endswith("layout.json")
    assert payload["tables"][0]["extraction"] == "layout"
    assert len(payload["sha256"]) == 64


def test_an_extraction_mode_that_is_not_in_the_format_is_refused(tmp_path, capsys):
    path = write(tmp_path, response(["A"], [["1"]]))
    code = reducer.main(
        [
            "--response", str(path), "--doc", "opp", "--pages", "2",
            "--extraction", "ocr", "--processor", "id@v", "--json", str(tmp_path / "p.json"),
        ]
    )
    assert code != 0 and "not one of" in capsys.readouterr().err


def test_it_imports_without_a_credential_or_a_rasteriser():
    code = (
        "import sys, scripts.propose_tables; "
        "assert 'pypdfium2' not in sys.modules, sorted(sys.modules); "
        "assert 'google.auth' not in sys.modules, sorted(sys.modules); "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout
