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


# --- S5-b: the continuation act, and the locators it may promote ----------------------
#
# Appendix 2's pages 77–79 were never sent to an arm. The owner reviewed its 30 rows from the paper
# on 2026-10-21 and they lived in `knowledge/tables.py`; S5-b promoted them into the proposal as
# **locators**. The act is only defensible if every locator is a run of the page, which is what
# these two tests say — and if the entry cannot be mistaken for an arm reading, which is the third.

from knowledge.tests import page_fixtures  # noqa: E402

CONTINUED = REPO_ROOT / "knowledge" / "proposals" / "saoso.structure.json"
REVIEWED = REPO_ROOT / "knowledge" / "proposals" / "saoso.reviewed.json"


def _appendix_2():
    """`(the continued entry, its reviewed profile)` from the committed proposal."""
    structure = json.loads(CONTINUED.read_text(encoding="utf-8"))
    reviewed = json.loads(REVIEWED.read_text(encoding="utf-8"))
    entry = next(table for table in structure["tables"] if table.get("continued_from"))
    index = structure["tables"].index(entry)
    return entry, reviewed["tables"][index]


def test_a_continued_locator_is_a_run_of_the_pages_table_line():
    """Every cell the continuation promoted is the page's own words, in its own column.

    This is the difference between verifying a review and typing a table: the emitter refuses a
    cell it cannot find (`test_a_cell_the_page_does_not_print_is_refused...`), and this says the
    same thing *before* a build — over all 41 non-empty cells, band-sliced, against the committed
    `-table` pages. The one cell that is not a run of its page is the declared cross-page tail, and
    it is checked on the page it is printed on.
    """
    entry, profile = _appendix_2()
    pages = page_fixtures.pages("saoso", "table")
    offset = 1  # SAOSO prints `pdf - 1`
    bands = {int(page): int(cut) for page, cut in profile["band"].items()}
    tails = {(tail["row"], tail["column"]): tail for tail in profile.get("tails", ())}

    def squash(text):
        return " ".join(text.split())

    printed_pages = []
    for row_index, row in enumerate(entry["rows"]):
        printed = 0
        for column, cell in enumerate(row["cells"], 1):
            wanted = squash(cell)
            if not wanted:
                continue
            tail = tails.get((row_index, column))
            if tail is not None:
                assert wanted.endswith(squash(tail["text"]))
                wanted = wanted[: len(wanted) - len(squash(tail["text"]))].strip()
            found = None
            for number in entry["pdf_pages"]:
                printed = number - offset
                band = bands[printed]
                # The page's own hyphenation: a word split at a line break (`cobalt-` /`
                # sulphate`) is one printed word, which is the rule the harness has had since
                # 2026-11-03 and the emitter adopted in S5-b.
                stream = ""
                for line in pages[number - 1].splitlines():
                    view = squash(line[:band] if column == 1 else line[band:])
                    if not view:
                        continue
                    if stream.endswith("-") and view[:1].islower():
                        stream += view
                        continue
                    stream = f"{stream} {view}".strip()
                if wanted in squash(stream):
                    found = printed
                    break
            assert found is not None, (
                f"row {row_index + 1} column {column}: {wanted[:60]!r} is not a run of the "
                "band-sliced page it claims to come from — the review is a locator, not an "
                "authoring act"
            )
            if tail is not None:
                assert squash(tail["text"]) in squash(pages[tail["page"] + offset - 1])
        printed_pages.append(printed)


def test_a_continued_entry_never_claims_an_arm_read_it():
    """The banner is per file, and the file describes Document AI's read of Appendix 6a. A
    continued entry names the review it came from instead, so the structure file cannot say an
    arm read pages nobody sent it."""
    entry, profile = _appendix_2()
    assert entry["continued_from"].startswith("knowledge/tables.py::APPENDIX_2_ROWS")
    assert "owner" in entry["continued_from"]
    # The labels are reviewed wording, so the structure file omits them and the review supplies
    # them — `_tables` falls back to `reviewed.json` rather than inventing a string.
    assert "columns" not in entry
    assert len(profile["columns"]) == 2


def test_a_continuation_completes_a_proposal_or_refuses(tmp_path, capsys):
    """No proposal to complete is a refusal with a name: the banner it would need is not this
    script's to invent."""
    with pytest.raises(SystemExit) as raised:
        reducer.main(
            [
                "--continue", "--doc", "saoso",
                "--json", str(tmp_path / "nothing.structure.json"),
            ]
        )
    assert "no proposal to continue" in str(raised.value)
