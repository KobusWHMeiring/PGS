"""The Crops review artefact is generated, and it must not go stale.

Task B3's acceptance is a human reading the template against the printed FORM. That is only possible if
the artefact a reviewer opens is the template we ship — so this file asserts that the committed file is
exactly what `scripts/crops_template_review.py` renders from the JSON, byte for byte. A schema edit
without regenerating fails here, which is the same rule as `board.md`: a generated document that is
edited by hand is a second source of truth.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.crops_template_review import TEMPLATE, render  # noqa: E402

ARTEFACT = REPO_ROOT / "product" / "docs" / "templates" / "crops_v1_review.md"


def _schema() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def test_the_committed_review_copy_matches_the_template():
    assert ARTEFACT.is_file(), "run: python scripts/crops_template_review.py --out " + str(ARTEFACT)
    assert ARTEFACT.read_text(encoding="utf-8") == render(_schema()), (
        "the review copy is stale — regenerate it with "
        "`python scripts/crops_template_review.py --out product/docs/templates/crops_v1_review.md`"
    )


def test_every_printed_question_verdict_and_record_appears():
    text = render(_schema())
    schema = _schema()
    for section in schema["sections"]:
        for question in section["questions"]:
            for item in question.get("items") or [question]:
                assert item["ref"] in text, item["key"]
    for verdict in schema["verdicts"]:
        assert verdict["key"] in text, verdict["key"]
    for record in schema["records"]:
        assert record["key"] in text, record["key"]


def test_the_marker_table_holds_every_marker_and_no_other():
    text = render(_schema())
    table = text.split("## The self-check markers (D71)")[1]
    marker_rows = [line for line in table.splitlines() if line.startswith("| `crops.")]
    assert len(marker_rows) == 11, marker_rows
