"""Fixtures for the UAT tooling tests.

Deliberately thin: two file-writing helpers and the real paths. A complex fixture here
would be the thing that fails first and hides the test (`testing_hazards.md` §1.12), and
every synthetic UAT below is written out in full at its test so the input is readable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_UAT = REPO_ROOT / "tests/uat/mvp0_standards_and_public_site_uat.md"
REAL_SPEC = REPO_ROOT / "product/backlog/Refinement/PGS_PLATFORM_SPEC.md"


@pytest.fixture
def write_uat(tmp_path):
    """Return `write(text, name="uat.md") -> Path`, writing a UAT file into `tmp_path`."""

    def _write(text: str, name: str = "uat.md") -> Path:
        path = tmp_path / name
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    return _write


@pytest.fixture
def write_json(tmp_path):
    """Return `write(payload, name="export.json") -> Path`."""

    def _write(payload: dict, name: str = "export.json") -> Path:
        path = tmp_path / name
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8", newline="\n")
        return path

    return _write
