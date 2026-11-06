"""Render the Crops template as a review table, for reading against the printed FORM.

Task B3's acceptance is *"a reviewer reads the JSON against the printed sheet and finds no omission"* —
and 700 lines of JSON is not a document anybody reads. This prints the same data in FORM order, one
row per printed line, so the reviewer works down the sheet and down the page together.

    python scripts/crops_template_review.py > /tmp/crops.md
    python scripts/crops_template_review.py --out product/docs/templates/crops_v1_review.md

It reads `core/templates_data/crops.v1.json` directly — no Django, no database — because the artefact
must be reproducible from the file the loader reads, not from a model somebody migrated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "core" / "templates_data" / "crops.v1.json"


def _cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def render(schema: dict) -> str:
    """The whole template as markdown: header, questions, verdicts, records, markers."""
    lines: list[str] = []
    lines.append(f"# {schema['category']} template {schema['version']} — review copy")
    lines.append("")
    lines.append(
        f"Standard: **{schema['standard_version']}** · source: `{schema.get('source', '—')}` · "
        f"declared gaps: {', '.join(schema.get('allowed_ref_gaps', [])) or 'none'}"
    )
    lines.append("")
    lines.append(
        "Generated from `core/templates_data/crops.v1.json` by "
        "`scripts/crops_template_review.py`. **Read it against FORM `6.B.1.Crops`**: one row here per "
        "printed line, in the sheet's order. The polarity column is the assessor's meaning of the "
        "answer (which answer is compliant), not a score."
    )
    lines.append("")

    for section in schema["sections"]:
        lines.append(f"## {section['title']}")
        lines.append("")
        lines.append("| Ref | Question (as the template stores it) | Type | By | Also |")
        lines.append("|---|---|---|---|---|")
        for question in section["questions"]:
            items = question.get("items") or [question]
            for item in items:
                extras = []
                if item.get("attachments"):
                    extras.append("attach: " + "; ".join(item["attachments"]))
                if item.get("links_to"):
                    extras.append(f"links to {item['links_to']}")
                if item.get("self_check"):
                    extras.append("**self-check**")
                lines.append(
                    f"| {_cell(item.get('ref') or question.get('ref'))} "
                    f"| {_cell(item.get('text') or '')} "
                    f"| {_cell(item.get('type') or '')} "
                    f"| {_cell(item.get('respondent') or '')} "
                    f"| {_cell('; '.join(extras))} |"
                )
        lines.append("")

    lines.append("## Verdicts")
    lines.append("")
    lines.append("| Verdict | Judges | The assessor's question | Polarity | Options |")
    lines.append("|---|---|---|---|---|")
    for verdict in schema["verdicts"]:
        lines.append(
            f"| {_cell(verdict['ref'])} (`{verdict['key']}`) "
            f"| Q{_cell(verdict.get('question_ref', ''))} "
            f"| {_cell(verdict['text'])} "
            f"| {verdict['polarity']} "
            f"| {'/'.join(verdict.get('options', []))} |"
        )
        for child in verdict.get("sub_questions", []):
            lines.append(
                f"| ↳ `{child['key']}` | — | {_cell(child['text'])} | {child['polarity']} "
                f"| {'/'.join(child.get('options', []))} |"
            )
        if verdict.get("guidance"):
            lines.append(f"| | | *{_cell(verdict['guidance'])}* | | |")
    lines.append("")

    lines.append("## Sheet I §2 records")
    lines.append("")
    lines.append("| Key | FORM ref | What the visit asks to see |")
    lines.append("|---|---|---|")
    for record in schema.get("records", []):
        lines.append(f"| `{record['key']}` | {_cell(record['ref'])} | {_cell(record['text'])} |")
    lines.append("")

    lines.append("## The self-check markers (D71)")
    lines.append("")
    lines.append("| Derived from | Why it is asked at the front door |")
    lines.append("|---|---|")
    for node in [*(i for s in schema["sections"] for q in s["questions"] for i in (q.get("items") or [q])),
                 *schema.get("records", [])]:
        marker = node.get("self_check")
        if marker:
            lines.append(f"| `{node['key']}` | {_cell(marker['why'])} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="write here instead of stdout")
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    options = parser.parse_args()

    schema = json.loads(options.template.read_text(encoding="utf-8"))
    text = render(schema)
    if options.out:
        options.out.parent.mkdir(parents=True, exist_ok=True)
        options.out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {options.out} ({len(text.splitlines())} lines)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
