#!/usr/bin/env python
"""The claims our own measured arms contradict, put in front of the owner one card at a time.

    python scripts/shape_arbitration.py            # write product/design/uat/arbitrate_shapes.html
    python scripts/shape_arbitration.py --check    # is the committed artefact current?

**Why this exists.** `INGESTION_ENGINE_PRD.md` §3.12: the re-score against the signed key moved an
arm a whole shape, because one claim on the key was wrong. Three shapes are still passed by no arm,
and they are three different problems — so "no arm passes it" cannot be read as "the tools cannot".
This page isolates the claims a human can actually arbitrate: **the claims at least two measured
arms contradict, on shapes no arm passes at all.** Everything else is named and set aside, because a
claim one arm satisfies is a tool finding, not a question about the paper.

**What the reviewer sees, per claim:** the page image from the committed PDF, the words our own key
proves are on that page (its anchors), the claim as the key states it today, and one line per arm —
the instrument's own mismatch line, not a re-reading. A line is exact: it is produced by
`shape_fixtures.mismatches()` against the arm's whole read.

**The verdict is the owner's.** Three answers: *keep* (the paper says what the key says), *amend*
(the paper says something else — type it), *can't tell*. Nothing here scores, computes or decides.
The export is JSON; `scripts/shape_review_signoff.py --amend` validates it and writes the amendment
into `knowledge/tests/shape_review.json` — after the fixture itself has been changed, so the record
keeps both the text the owner judged and the text the key now says.

Self-contained: no CDN, no font, no network. The page images are `data:` URIs of hash-pinned
renders (`knowledge/tests/shape_pages.py`), so a hand-cropped screenshot fails rather than helps.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge.tests.shape_fixtures import BY_KEY, SHAPES, flat, page_text  # noqa: E402
from knowledge.tests.shape_pages import data_uri  # noqa: E402
from scripts.shape_claims import claims as case_claims  # noqa: E402
from scripts.shape_arbitration_template import TEMPLATE  # noqa: E402
from scripts.shape_disputes import Arm, Disagreement, disagreements, load_arms  # noqa: E402
from scripts.shape_review_page import escape  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "product/design/uat/arbitrate_shapes.html"
ARTEFACT_NAME = "product/design/uat/arbitrate_shapes.html"
KIND = "pgs-shape-arbitration"
VERSION = 1
VERDICTS = ("keep", "amend", "unsure")

#: Where a claim is asserted elsewhere in the record. `qualifier` is passed by
#: `gemini-3.1-flash-lite` in the `anchors` form (§3.8), which is not one of the arms this page
#: reads from the re-score — so the page must say so, or it would read as unsatisfiable.
PASSED_ELSEWHERE = {
    "qualifier": "gemini-3.1-flash-lite, `anchors` form — §3.8. Satisfiable, so not a key question.",
}

#: Claims the owner has already arbitrated, so they are not asked again. Kept here rather than in a
#: record because an arbitration that changes nothing has nothing to write: `keep` agrees with the
#: signed review, and the export is committed beside this as evidence
#: (`product/docs/evidence/2026-11-05_shape_arbitration_first_pass.json`).
SETTLED = {
    "headerless_values.header": "kept — the paper does print the two labels as two columns, so the "
    "arms' merged read is a tool failure, not a key defect",
}

#: What the record already decided about a shape, shown above its claims. Every line here is a
#: decision a human made and signed elsewhere — the landscape artefact's own legend, and the
#: `Step 3` amendment — because three of the first pass's four "unsure" notes were asking a question
#: the record already answers, and the page never said so.
ALREADY_DECIDED = {
    "empty_cells": "The landscape artefact's legend: “The Fee column is one printed box spanning the "
    "Step 1 and Step 2 rows, and it is filed under Step 1, the row it starts beside. Two cells on "
    "Step 1 are printed empty: the paper is silent, and silence is not permission. A seal is a "
    "picture; where the paper prints its name beside it that name is the cell, and the artwork "
    "itself is not stored.”",
    "page_break_row": "The landscape artefact keeps each printed step label inside its row's first "
    "cell — that is the same convention the `long_cell` amendment settled on 2026-11-05 — and a row "
    "whose later half is printed on the next page is still one row (requirement 4).",
    "headerless_values": "The owner confirmed on 2026-11-05 that the paper's four printed header "
    "lines group into these two column labels; four arms merging them is the finding, not a defect.",
    "long_cell": "Amended 2026-11-05: the cell starts with the printed label `Step 3`.",
}

#: What a corrected claim looks like. The first export put an arm's report in here, which is not a
#: claim at all — so the form is stated on the card and checked before the export is written.
AMEND_HINT = "empty · text=… · starts=… · ends=… · contains=… · at_least=N"


def arbitrable(arms: tuple[Arm, ...]) -> tuple[Disagreement, ...]:
    """The claims this page presents: contradicted by two arms, on a shape nobody passes, unsettled."""
    return tuple(
        item
        for item in disagreements(arms)
        if item.claim_id.split(".")[0] not in PASSED_ELSEWHERE
        and item.claim_id not in SETTLED
    )


def shapes_in_play(items: tuple[Disagreement, ...]) -> list[str]:
    """The shape keys the disputes touch, in registry order."""
    keys = {item.claim_id.split(".")[0] for item in items}
    return [case.key for case in SHAPES if case.key in keys]


def _token(expected: str) -> str:
    """The words a claim asserts, for finding the paper's own line. `empty` asserts nothing."""
    for prefix in ("text=", "starts=", "ends=", "contains="):
        if expected.startswith(prefix):
            return expected[len(prefix) :].strip()
    return ""


def _printed_page(case, claim) -> tuple[int, int]:
    """The PDF page and the printed page a claim's row is on. `row_pages` are printed pages."""
    printed = claim.row if claim.row >= 0 and claim.row < len(case.row_pages) else None
    page = case.row_pages[printed] if printed is not None else case.printed_pages[0]
    try:
        pdf = case.pdf_pages[case.printed_pages.index(page)]
    except ValueError:
        pdf = case.pdf_pages[0]
    return pdf, page


def _paper_lines(case, claim, span: int = 2) -> tuple[int, list[tuple[int, str, bool]]]:
    """The committed page's own lines around the claim, on the page the claim is printed on.

    This is deliberately the *committed extraction*, not a re-reading: a reviewer deciding whether a
    cell holds `R500` needs the line that carries it, and the first pass could not find it because
    the page image was too small to read. A hit line is marked so it is not mistaken for context.
    """
    pdf, printed = _printed_page(case, claim)
    token = flat(_token(claim.expected))
    if not token:
        return printed, []
    lines = page_text(case, pdf).splitlines()
    hits = [index for index, line in enumerate(lines) if token in flat(line)]
    if not hits:
        # The claim normalises something the page does not print as one run — letter-spaced words
        # are the usual case (Appendix 6a prints "Other b o v i n e"). Fall back to the first word,
        # so the reviewer sees the line that made us write the claim that way.
        first = token.split(" ")[0]
        hits = [index for index, line in enumerate(lines) if first and first in flat(line)]
        if not hits:
            return printed, []
    first = hits[0]
    start = max(first - span, 0)
    end = min(first + span + 1, len(lines))
    return printed, [(index, lines[index], index in hits) for index in range(start, end)]


def _evidence_html(case, claim) -> str:
    if claim.kind != "cell":
        return ""
    printed, window = _paper_lines(case, claim)
    if not _token(claim.expected):
        return (
            '<p class="fine">The key asserts this cell prints nothing; a blank is not something a '
            "line of text can show. Judge it against the page image and the note above.</p>"
        )
    if not window:
        return (
            '<p class="fine">Our committed text does not carry these words at all on this page, so '
            "the claim is doing normalisation the page does not show. Judge it against the image.</p>"
        )
    rows = "".join(
        f'<span class="{"hit" if hit else "ctx"}">{escape(line.rstrip() or "·")}</span>'
        for _, line, hit in window
    )
    return (
        f'<p class="fine">Our committed text for this page, around the words the claim asserts '
        f"(printed page {printed}). The bold line carries them. This pass prints the page's columns "
        "side by side, so one line can hold fragments of several cells — the words are what matter, "
        "and the page image above is the authority:</p>"
        f'<pre class="paper">{rows}</pre>'
    )


def _arm_rows(item: Disagreement) -> str:
    rows = []
    for arm_name, line in item.arms:
        rows.append(
            "<tr><th>{arm}</th><td><code>{line}</code></td></tr>".format(
                arm=escape(arm_name), line=escape(line)
            )
        )
    return "".join(rows)


def _card(item: Disagreement, claim, case=None) -> str:
    page_line = ""
    evidence = ""
    if case is not None:
        _, printed = _printed_page(case, claim)
        page_line = f'<span class="page">printed page {printed}</span>'
        evidence = _evidence_html(case, claim)
    return f"""
    <article class="card" data-claim="{escape(item.claim_id)}">
      <h3 id="{escape(item.claim_id)}"><code>{escape(item.claim_id)}</code>
        <span class="count">{item.count} of 5 arms</span>{page_line}</h3>
      <p class="question">{escape(claim.question)}</p>
      <p class="key">The key says: <strong>{escape(claim.expected)}</strong></p>
      {evidence}
      <table class="arms"><caption>What each measured arm said, in its own words</caption>
        <tbody>{_arm_rows(item)}</tbody></table>
      <div class="verdict">
        <label><input type="radio" name="{escape(item.claim_id)}" value="keep"> Keep it — the paper
          says this</label>
        <label><input type="radio" name="{escape(item.claim_id)}" value="amend"> Amend it — the paper
          says</label>
        <input class="newtext" type="text" value="{escape(claim.expected)}"
               aria-label="The corrected claim text" data-shape="{escape(item.claim_id.split('.')[0])}">
        <span class="fine">Write the claim in the key's own form: {escape(AMEND_HINT)}. An arm's
          report is not a claim.</span>
        <label><input type="radio" name="{escape(item.claim_id)}" value="unsure"> Can’t tell</label>
      </div>
      <label class="note">Note <em>(required unless you keep it)</em>
        <textarea rows="2" aria-label="Why"></textarea></label>
    </article>"""


def _shape_section(shape: str, items: list[Disagreement]) -> str:
    case = BY_KEY[shape]
    by_id = {claim.id: claim for claim in case_claims(case)}
    pages = ", ".join(str(page) for page in case.pdf_pages)
    anchors = "".join(
        f"<li><code>{escape(text)}</code></li>" for _, text in case.anchors
    )
    figures = "".join(
        f'<figure><img class="zoomable" src="{data_uri(case.doc_key, page)}" '
        f'alt="The page as the PDF prints it" title="Click for full size">'
        f"<figcaption>PDF page {page}"
        + (
            f" (printed page {case.printed_pages[case.pdf_pages.index(page)]})"
            if page in case.pdf_pages
            else ""
        )
        + "</figcaption></figure>"
        for page in case.pdf_pages
    )
    card_html = "".join(
        _card(item, by_id[item.claim_id], case) for item in items if item.claim_id in by_id
    )
    elsewhere = PASSED_ELSEWHERE.get(shape)
    note = f'<p class="elsewhere">{escape(elsewhere)}</p>' if elsewhere else ""
    decided = ALREADY_DECIDED.get(shape)
    if decided:
        note += f'<p class="decided"><strong>Already decided.</strong> {escape(decided)}</p>'
    return f"""
  <section class="shape" data-shape="{escape(shape)}">
    <h2>{escape(case.shape)} <span class="where">{escape(case.doc)} · pages {pages}</span></h2>
    <div class="side">
      <div class="evidence">
        {note}
        {figures}
        <div class="printed">
          <h3>What our own key proves is printed on this page</h3>
          <ul>{anchors}</ul>
          <p class="fine">The shape’s anchors: strings the key asserts are on the page. If a claim
            contradicts them, the claim is the likelier defect. Click a page to see it full size.</p>
        </div>
      </div>
      <div class="cards">{card_html}</div>
    </div>
  </section>"""


def _settled_html() -> str:
    """Claims already arbitrated, listed so the reviewer can see what is not being asked again."""
    if not SETTLED:
        return ""
    items = "".join(
        f"<li><code>{escape(claim_id)}</code> — {escape(note)}</li>"
        for claim_id, note in sorted(SETTLED.items())
    )
    return f'<div class="settled"><h2>Already answered</h2><ul>{items}</ul></div>'


def _arm_table(arms: tuple[Arm, ...]) -> str:
    rows = "".join(
        f"<tr><th>{escape(arm.name)}</th><td>{escape(', '.join(sorted(arm.passed))or '—')}</td>"
        f"<td>{len(arm.blind)}</td></tr>"
        for arm in arms
    )
    return (
        "<table class=\"summary\"><caption>Which arms read the eight shapes, and which they pass</caption>"
        "<thead><tr><th>Arm</th><th>Passes</th><th>Blind on</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def build_data(arms: tuple[Arm, ...], items: tuple[Disagreement, ...]) -> dict:
    """The payload the page's script reads: one entry per arbitrable claim."""
    expected = {claim.id: claim.expected for case in SHAPES for claim in case_claims(case)}
    return {
        "kind": KIND,
        "version": VERSION,
        "artefact": ARTEFACT_NAME,
        "verdicts": list(VERDICTS),
        "claims": [
            {
                "id": item.claim_id,
                "expected": expected[item.claim_id],
                "arms": [{"arm": name, "line": line} for name, line in item.arms],
            }
            for item in items
        ],
    }


def build_html(arms: tuple[Arm, ...], items: tuple[Disagreement, ...]) -> str:
    # Raw JSON, not HTML-escaped: a `<script type="application/json">` element holds text, not
    # markup, so `&quot;` would reach JSON.parse literally (the page's script threw on exactly
    # that the first time this ran in Chromium — `testing_hazards.md` §1.30). Only `<` needs
    # escaping, and as a JSON escape so it parses back unchanged.
    data = json.dumps(build_data(arms, items), sort_keys=True).replace("<", "\u003c")
    passing = {shape for arm in arms for shape in arm.passed} | set(PASSED_ELSEWHERE)
    set_aside = [case.key for case in SHAPES if case.key in passing]
    body = "".join(
        _shape_section(shape, [item for item in items if item.claim_id.startswith(shape + ".")])
        for shape in shapes_in_play(items)
    )
    return TEMPLATE.format(
        artefact=escape(ARTEFACT_NAME),
        data=data,
        settled=_settled_html(),
        arms=_arm_table(arms),
        body=body,
        count=len(items),
        set_aside=", ".join(f"<code>{escape(key)}</code>" for key in set_aside),
    )




def _display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    arms = load_arms()
    items = arbitrable(arms)
    html = build_html(arms, items)
    out = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    if args.check:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != html:
            print(f"STALE {_display(out)} - regenerate with scripts/shape_arbitration.py")
            return 1
        print(f"current: {_display(out)} ({len(html) / 1024:.0f} KB, {len(items)} claims)")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    print(f"wrote {_display(out)} - {len(items)} claims, {len(html) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
