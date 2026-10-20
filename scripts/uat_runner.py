"""Turn one UAT markdown file into one self-contained HTML judgement surface.

    python scripts/uat_runner.py --file tests/uat/mvp0_standards_and_public_site_uat.md

Output: `product/design/uat/<slug>.html`. One file. No CDN, no fonts to fetch, no
network at all — it opens from `file://` on a laptop with the wifi off, which is where
these get read and where a reviewer's data must stay. The shell (CSS, script, markdown
renderer) is `scripts/uat_page.py`; this module assembles it and runs the checks.

**What this is not.** It never decides PASS or FAIL. It shows each scenario's
`Judgement:` clause — the largest thing on the card — collects the reviewer's call, and
exports it. A runner that scored anything would be the failure the `writing-uat-tests`
skill exists to prevent: a checklist of machine checks shown to a human as though the
human's judgement had been used.

**Three guarantees the tests hold it to**, because each one fails silently otherwise:

* Every `Judgement:` clause appears **verbatim** in the file (`uat-data` payload), so a
  reviewer reading the export and a grep over the artefact see the same words.
* Nothing from the file's "Automated coverage (NOT UAT)" table appears anywhere. That
  table lists what pytest already proves; rendering it would pad the reviewer's work with
  checks they must not be asked to make. It is excluded structurally — only
  `## Scenario N — …` sections become cards.
* No `http://`, `https://`, `src=` or `href=` exists in the output. A reviewer's browser
  makes zero requests, and "nothing leaves the machine" stays a fact.

**Refuses rather than presents.** A scenario with no `Judgement:` clause, a duplicate
scenario number, or an N/A whose cited decision no longer defers stops the run with every
problem named. A card built from a guess is worse than no card: it is a judgement nobody
was asked to make, on a form that will be signed.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# `python scripts/uat_runner.py` puts `scripts/` on sys.path, not the repo root, so the
# sibling imports below need the root adding explicitly.
sys.path.insert(0, str(REPO_ROOT))

from scripts.uat_page import environment, page, render_inline, render_prose  # noqa: E402
from scripts.uat_parse import (  # noqa: E402  (see the sys.path insert above)
    Scenario,
    UatFile,
    UatFormatError,
    parse_decisions,
    parse_uat,
    scan_applicability,
)

SPEC_PATH = REPO_ROOT / "product/backlog/Refinement/PGS_PLATFORM_SPEC.md"
OUT_DIR = REPO_ROOT / "product/design/uat"


# ------------------------------------------------------------------------- cards


def _card(scenario: Scenario) -> str:
    """One scenario card. The judgement is first and largest; the result controls last."""
    category = (
        f'<span class="tag">{render_inline(scenario.category)}</span>' if scenario.category else ""
    )
    not_applicable = scenario.not_applicable

    parts: list[str] = [
        f'<article class="card{" na" if not_applicable else ""}" '
        f'id="scenario-{scenario.number}" data-n="{scenario.number}">',
        '<div class="card-head">',
        f'<span class="num">{scenario.number}</span>',
        f'<h2>{render_inline(scenario.title)}</h2>',
        category,
        "</div>",
    ]

    if not_applicable:
        # The status text usually opens with "Not applicable" already; repeating it in the
        # banner reads like two separate exclusions.
        lead = (
            ""
            if "not applicable" in scenario.status.lower()
            else '<b>Not applicable.</b> '
        )
        parts.append(
            f'<div class="banner not-applicable">{lead}{render_prose(scenario.status)}</div>'
        )

    if scenario.judgement:
        parts.append(
            '<div class="judgement"><p class="label">The judgement — the question you are '
            f'answering</p><div class="judgement-body">{render_prose(scenario.judgement)}</div></div>'
        )

    if scenario.setup:
        parts.append(
            '<div class="field"><p class="label">Setup — do this first</p>'
            f'<div class="prose">{render_prose(scenario.setup)}</div></div>'
        )

    if scenario.steps:
        items = "".join(f"<li>{render_inline(step)}</li>" for step in scenario.steps)
        parts.append(f'<div class="field"><p class="label">Steps</p><ol class="steps">{items}</ol></div>')

    if scenario.expected:
        parts.append(
            '<div class="field"><p class="label">Expected</p>'
            f'<div class="prose">{render_prose(scenario.expected)}</div></div>'
        )

    for label, body in scenario.notes:
        parts.append(
            f'<div class="field note"><p class="label">{render_inline(label)}</p>'
            f'<div class="prose">{render_prose(body)}</div></div>'
        )

    parts.append(
        '<div class="field"><p class="label">Your note (optional)</p>'
        '<textarea class="note" rows="2" data-k="note" placeholder="What you saw, in your own '
        'words" autocomplete="off"></textarea></div>'
    )
    parts.append(
        '<div class="field"><p class="label">Evidence — a screenshot is optional</p>'
        '<div class="row"><input type="file" accept="image/*" data-k="evidence" '
        'class="file"><button type="button" class="tiny ghost" data-act="clear-evidence" '
        'hidden>Remove image</button><span class="hint" data-k="evidence-name"></span></div>'
        '<p class="hint">An image stays inside this page and the file you export. Nothing '
        "is uploaded.</p></div>"
    )
    parts.append(
        '<div class="field reason" hidden><p class="label">Reason — required for FAIL and '
        'N/A</p><textarea rows="2" data-k="reason" placeholder="One sentence a committee '
        'can read out" autocomplete="off"></textarea></div>'
    )
    parts.append(
        '<div class="result"><div class="choices" role="group" '
        f'aria-label="Result for scenario {scenario.number}">'
        '<button type="button" class="choice pass" data-v="PASS">PASS</button>'
        '<button type="button" class="choice fail" data-v="FAIL">FAIL</button>'
        '<button type="button" class="choice na" data-v="N/A">N/A</button></div>'
        '<div class="who">'
        '<input type="text" data-k="reviewer" placeholder="Your name" autocomplete="name">'
        '<select data-k="role"><option value="">Role…</option>'
        "<option>Product</option><option>PGS administrator</option>"
        "<option>Committee reviewer</option><option>Consumer member</option></select>"
        '<input type="date" data-k="date">'
        "</div>"
        '<p class="status" data-k="status">Not yet judged</p></div>'
    )
    parts.append("</article>")
    return "".join(parts)


def _json_payload(uat: UatFile, env: dict[str, object], na_reasons: dict[int, str]) -> str:
    """The verbatim payload the page and the export are both built from.

    It carries the raw markdown, not the rendered HTML: a test can then assert the
    `Judgement:` clause is present character-for-character, and the reviewer sees the
    rendered form of the same string.
    """
    payload = {
        "kind": "pgs-uat",
        "version": 1,
        "file": uat.path.as_posix(),
        "slug": uat.slug,
        "title": uat.title,
        "environment": env,
        "scenarios": [
            {
                "n": s.number,
                "title": s.title,
                "category": s.category,
                "not_applicable": s.not_applicable,
                "na_reason": na_reasons.get(s.number, ""),
                "judgement": s.judgement,
                "setup": s.setup,
                "steps": list(s.steps),
                "expected": s.expected,
                "notes": [{"label": label, "body": body} for label, body in s.notes],
            }
            for s in uat.scenarios
        ],
    }
    # `</script>` inside a JSON string would close the tag early. Escaping the slash is
    # the one substitution that keeps the payload both valid JSON and valid HTML.
    return json.dumps(payload, ensure_ascii=False, indent=1).replace("</", "<\\/")


def na_reason(scenario: Scenario, decisions: dict[str, str]) -> str:
    """The default N/A reason, taken from the decision that caused it.

    Scenario 5 must arrive already marked N/A with D44's reason, because the reason is the
    point: a reviewer new to the group has no way to know why the Afrikaans scenario is
    greyed out, and an unexplained N/A looks like a failed check.
    """
    if not scenario.not_applicable:
        return ""
    cited = scenario.cited_decisions
    decision = cited[0] if cited else ""
    resolution = decisions.get(decision, "")
    detail = re.sub(r"\*\*|`", "", resolution).strip()
    detail = re.split(r"(?<=\.)\s", detail, maxsplit=1)[0]
    return f"{decision}: {detail}" if decision else detail


# ------------------------------------------------------------------------ build


def build_html(
    uat: UatFile,
    env: dict[str, object],
    preflight: str,
    decisions: dict[str, str] | None = None,
) -> str:
    """Assemble the whole artefact. Pure: same inputs, byte-identical output."""
    if decisions is None:
        spec_text = SPEC_PATH.read_text(encoding="utf-8") if SPEC_PATH.exists() else ""
        decisions = parse_decisions(spec_text)
    reasons = {s.number: na_reason(s, decisions) for s in uat.scenarios}
    cards = "".join(_card(s) for s in uat.scenarios)
    payload = _json_payload(uat, env, reasons)
    applicable = len(uat.applicable)
    na = len(uat.not_applicable)

    preflight_html = (
        f'<pre class="preflight">{html.escape(preflight.rstrip(), quote=False)}</pre>'
        if preflight.strip()
        else '<p class="hint">No preflight output was pasted in. Generate this file with '
        '<code>--preflight preflight.txt</code> after running <code>python manage.py '
        "uat_seed --check</code>, so the reviewer can see what the instance looked like "
        "when the UAT ran.</p>"
    )

    setup_html = (
        f'<div class="prose">{render_prose(uat.pre_test_setup)}</div>'
        if uat.pre_test_setup
        else ""
    )

    counts = f"{applicable} scenarios to judge" + (
        f", {na} marked not applicable" if na else ""
    )
    counts += (
        ". Read the judgement question, run the scenario in the app, then record what you saw."
    )
    meta = "".join(
        f"<span>{label} <code>{value}</code></span>"
        for label, value in (
            ("Slug", uat.slug),
            ("Commit", f"{env['commit']} ({env['working_tree']})"),
            ("Database", env["database"]),
            ("Generated", env["generated_on"]),
            ("Source", uat.path.name),
        )
    )

    return page(
        title=uat.title,
        slug=uat.slug,
        source_name=uat.path.as_posix(),
        header=render_inline(uat.title),
        counts=counts,
        meta=meta,
        preflight_html=preflight_html,
        setup_html=setup_html,
        cards=cards,
        payload=payload,
    )


# -------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--file", required=True, help="Path to tests/uat/<slug>.md")
    parser.add_argument("--out", default=None, help="Output HTML (default product/design/uat/<slug>.html)")
    parser.add_argument("--spec", default=str(SPEC_PATH), help="PGS_PLATFORM_SPEC.md, for the decision table")
    parser.add_argument("--preflight", default=None, help="Text file holding `uat_seed --check` output")
    parser.add_argument("--database", default=None, help="The database this UAT runs against")
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 2

    try:
        uat = parse_uat(path)
    except UatFormatError as exc:
        print("error: this UAT file cannot be presented:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"error: {spec_path} does not exist, so decisions cannot be checked", file=sys.stderr)
        return 2
    problems = scan_applicability(uat, parse_decisions(spec_path.read_text(encoding="utf-8")))
    if problems:
        print("error: the applicability scan failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    preflight = ""
    if args.preflight:
        try:
            preflight = Path(args.preflight).read_text(encoding="utf-8")
        except OSError as exc:
            # A missing preflight must not produce a traceback: the operator can fix this
            # one, and the panel it would produce is the evidence the reviewer relies on.
            print(f"error: could not read the preflight: {exc}", file=sys.stderr)
            return 2
    out = Path(args.out) if args.out else OUT_DIR / f"{uat.slug}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    env = environment(args.database or "")
    # `newline="\n"` on purpose: the default write emits CRLF on Windows, so the artefact
    # would differ by platform and a regeneration would show a whole-file diff
    # (testing_hazards.md §1.27).
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(build_html(uat, env, preflight))

    print(f"uat:    {uat.slug} - {len(uat.scenarios)} scenarios "
          f"({len(uat.applicable)} applicable, {len(uat.not_applicable)} N/A)")
    print(f"commit: {env['commit']} ({env['working_tree']})")
    print(f"wrote:  {out.as_posix()} ({out.stat().st_size} bytes)")
    if not preflight:
        print("note:   no --preflight given, so the preflight panel will be empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
