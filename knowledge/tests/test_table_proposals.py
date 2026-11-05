"""The proposals loader — found by sha256, and loud about every way a proposal can be wrong.

The interesting assertions are not "it loads the OPP's table" (the emitter's tests would fail
immediately if it did not). They are the four refusals, because each of them is a silent default in
a version of this module that "just" loads JSON:

* a row with the wrong number of cells — padding it invents a cell nobody read;
* a review that names more tables than the structure has — pairing by index then attaches one
  table's legend to another;
* two files claiming one digest — the tree can no longer say which structure built the artefact;
* a review naming an index past the end — the same defect one table further in.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge.corpus import parse_blocks
from knowledge.table_proposals import PROPOSAL_DIR, ProposalError, proposals_for

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The digest the artefact header records. Read from the artefact rather than copied, so the test
#: fails on a reprint instead of pointing at nothing — the same rule `page_fixtures` applies.
OPP_ARTEFACT = REPO_ROOT / "knowledge" / "corpus" / "opp.md"


def opp_sha() -> str:
    for line in OPP_ARTEFACT.read_text(encoding="utf-8").splitlines():
        if line.startswith("sha256:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("the OPP artefact has no sha256 line")


STRUCTURE = {
    "doc_key": "opp",
    "sha256": "a" * 64,
    "structure": "documentai-layout-v1.6-pro",
    "processor": "id@version",
    "tables": [
        {
            "pdf_pages": [2],
            "extraction": "layout",
            "columns": ["A", "B"],
            "rows": [{"cells": ["1", "2"]}, {"cells": ["3", "4"]}],
        }
    ],
}


def write(directory: Path, payload: dict, name: str = "x.structure.json") -> Path:
    path = directory / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --- the real proposal ---------------------------------------------------------------


def test_the_opp_proposal_is_found_by_the_documents_sha256_and_not_by_its_key():
    """Retargeting is the whole point: a document's structure is found by the bytes it describes, so
    a new standard needs no registry entry, no enum value and no migration."""
    tables = proposals_for(opp_sha())
    assert len(tables) == 1
    table = tables[0]
    assert table.columns == (
        "Annual farm turnover (gross sales)",
        "Initial certification fee (R)",
        "Renewal fee (R)",
    )
    assert len(table.rows) == 6
    assert table.rows[0].cells == ("Below R 250,000", "1,500", "900")
    assert table.rows[5].cells == ("Above R 5,000,000", "8,000", "8,000")
    assert table.extraction == "layout" and table.pdf_pages == (2,)


def test_the_proposal_records_the_arm_that_proposed_it():
    table = proposals_for(opp_sha())[0]
    assert table.structure == "documentai-layout-v1.6-pro"
    assert "pretrained-layout-parser-v1.6-pro" in table.processor


def test_the_reviewed_fields_no_extractor_produces_come_through():
    """The OPP's legend is the review's, not the arm's — and it must survive a regeneration, or
    `--force` silently drops a person's sentence."""
    table = proposals_for(opp_sha())[0]
    assert table.profile.legend.startswith("One row per turnover band")
    assert table.profile.layout == "grid"


def test_a_document_nobody_has_proposed_is_empty_and_not_an_error():
    assert proposals_for("0" * 64) == ()


def test_the_committed_proposal_agrees_with_the_engineers_artefact():
    """Two records of the same document — the artefact and the proposal — must not drift apart in
    the one place the emitter trusts: the printed column labels."""
    artefact = parse_blocks(OPP_ARTEFACT.read_text(encoding="utf-8"))
    table = next(table for section in artefact.sections for table in section.tables)
    proposal = proposals_for(opp_sha())[0]
    assert proposal.columns == table.columns
    assert table.extraction == proposal.extraction


# --- the refusals --------------------------------------------------------------------


def test_a_row_whose_cell_count_disagrees_with_the_columns_is_refused(tmp_path):
    payload = json.loads(json.dumps(STRUCTURE))
    payload["tables"][0]["rows"][1]["cells"] = ["only one"]
    write(tmp_path, payload)
    with pytest.raises(ProposalError, match="row 2: 1 cells for 2 columns"):
        proposals_for("a" * 64, directory=tmp_path)


def test_a_review_that_names_a_different_number_of_tables_is_refused(tmp_path):
    write(tmp_path, STRUCTURE)
    (tmp_path / "x.reviewed.json").write_text(
        json.dumps({"tables": [{"legend": "one"}, {"legend": "two"}]}), encoding="utf-8"
    )
    with pytest.raises(ProposalError, match="review names 2"):
        proposals_for("a" * 64, directory=tmp_path)


def test_a_review_title_list_that_is_not_one_per_row_is_refused(tmp_path):
    write(tmp_path, STRUCTURE)
    (tmp_path / "x.reviewed.json").write_text(
        json.dumps({"tables": [{"titles": ["only the first"]}]}), encoding="utf-8"
    )
    with pytest.raises(ProposalError, match="1 titles for 2 rows"):
        proposals_for("a" * 64, directory=tmp_path)


def test_a_branch_that_names_no_row_is_refused(tmp_path):
    write(tmp_path, STRUCTURE)
    (tmp_path / "x.reviewed.json").write_text(
        json.dumps({"tables": [{"branch": 5}]}), encoding="utf-8"
    )
    with pytest.raises(ProposalError, match="branch: 5"):
        proposals_for("a" * 64, directory=tmp_path)


def test_two_structures_claiming_one_document_are_refused(tmp_path):
    write(tmp_path, STRUCTURE, name="one.structure.json")
    write(tmp_path, STRUCTURE, name="two.structure.json")
    with pytest.raises(ProposalError, match="2 proposals claim"):
        proposals_for("a" * 64, directory=tmp_path)


def test_a_proposal_without_its_arm_is_refused(tmp_path):
    payload = json.loads(json.dumps(STRUCTURE))
    del payload["processor"]
    write(tmp_path, payload)
    with pytest.raises(ProposalError, match="banner"):
        proposals_for("a" * 64, directory=tmp_path)


def test_a_proposal_that_leaves_out_the_extraction_mode_is_refused(tmp_path):
    """The gate judges every cell against a rendering; a proposal that does not name one would let
    the emitter write a block whose pass nobody declared."""
    payload = json.loads(json.dumps(STRUCTURE))
    del payload["tables"][0]["extraction"]
    write(tmp_path, payload)
    with pytest.raises(ProposalError, match="extraction"):
        proposals_for("a" * 64, directory=tmp_path)


def test_the_committed_directory_holds_one_proposal_and_the_readme():
    names = {path.name for path in PROPOSAL_DIR.iterdir()}
    assert "README.md" in names
    assert "opp.structure.json" in names and "opp.reviewed.json" in names


# --- S5: the reviewed column labels ----------------------------------------------------


def test_a_reviewed_column_count_that_disagrees_is_refused(tmp_path):
    """A label list is paired with the columns one-to-one. Short or long, it moves a value under
    the wrong heading — R2 with a human's signature on it."""
    payload = json.loads(json.dumps(STRUCTURE))
    write(tmp_path, payload, "a.structure.json")
    write(tmp_path, {"tables": [{"columns": ["Only one"]}]}, "a.reviewed.json")
    with pytest.raises(ProposalError, match="reviewed column labels"):
        proposals_for("a" * 64, directory=tmp_path)


def test_a_reviewed_column_label_that_is_blank_is_refused(tmp_path):
    payload = json.loads(json.dumps(STRUCTURE))
    write(tmp_path, payload, "a.structure.json")
    write(tmp_path, {"tables": [{"columns": ["A", "  "]}]}, "a.reviewed.json")
    with pytest.raises(ProposalError, match="blank"):
        proposals_for("a" * 64, directory=tmp_path)


def test_the_saoso_proposal_carries_the_arbitrated_two_label_header():
    """The owner's arbitration of 2026-11-05, as data: the standard prints the header once and every
    reader merged the two labels into one. The proposal is found by the PDF's sha256 like the OPP's,
    so a reprint finds nothing rather than a stale structure."""
    sha = next(
        line.split(":", 1)[1].strip()
        for line in (REPO_ROOT / "knowledge" / "corpus" / "saoso.md")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.startswith("sha256:")
    )
    table = proposals_for(sha)[0]
    assert table.profile.columns == (
        "Class or species",
        "Maximum number of animals per ha equivalent to 170 kg N/ha/year",
    )
    assert len(table.rows) == 20 and table.extraction == "table"
