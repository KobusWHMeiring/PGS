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

from knowledge.tests.shape_fixtures import BY_KEY, SHAPES, flat  # noqa: E402
from knowledge.tests.shape_pages import data_uri  # noqa: E402
from scripts.shape_claims import claims as case_claims  # noqa: E402
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


def shapes_in_play(items: tuple[Disagreement, ...]) -> list[str]:
    """The shape keys the disputes touch, in registry order."""
    keys = {item.claim_id.split(".")[0] for item in items}
    return [case.key for case in SHAPES if case.key in keys]


def _arm_rows(item: Disagreement) -> str:
    rows = []
    for arm_name, line in item.arms:
        rows.append(
            "<tr><th>{arm}</th><td><code>{line}</code></td></tr>".format(
                arm=escape(arm_name), line=escape(line)
            )
        )
    return "".join(rows)


def _card(item: Disagreement, claim) -> str:
    return f"""
    <article class="card" data-claim="{escape(item.claim_id)}">
      <h3 id="{escape(item.claim_id)}"><code>{escape(item.claim_id)}</code>
        <span class="count">{item.count} of 5 arms</span></h3>
      <p class="question">{escape(claim.question)}</p>
      <p class="key">The key says: <strong>{escape(claim.expected)}</strong></p>
      <table class="arms"><caption>What each measured arm said, in its own words</caption>
        <tbody>{_arm_rows(item)}</tbody></table>
      <div class="verdict">
        <label><input type="radio" name="{escape(item.claim_id)}" value="keep"> Keep it — the paper
          says this</label>
        <label><input type="radio" name="{escape(item.claim_id)}" value="amend"> Amend it — the paper
          says</label>
        <input class="newtext" type="text" value="{escape(claim.expected)}"
               aria-label="The corrected claim text">
        <label><input type="radio" name="{escape(item.claim_id)}" value="unsure"> Can’t tell</label>
      </div>
      <label class="note">Note <em>(required unless you keep it)</em>
        <textarea rows="2" aria-label="Why"></textarea></label>
    </article>"""


def _shape_section(shape: str, items: list[Disagreement]) -> str:
    case = BY_KEY[shape]
    by_id = {claim.id: claim for claim in case_claims(case)}
    page = case.pdf_pages[0]
    anchors = "".join(
        f"<li><code>{escape(text)}</code></li>" for _, text in case.anchors
    )
    card_html = "".join(_card(item, by_id[item.claim_id]) for item in items if item.claim_id in by_id)
    elsewhere = PASSED_ELSEWHERE.get(shape)
    note = f'<p class="elsewhere">{escape(elsewhere)}</p>' if elsewhere else ""
    return f"""
  <section class="shape" data-shape="{escape(shape)}">
    <h2>{escape(case.shape)} <span class="where">{escape(case.doc)} · PDF page {page}</span></h2>
    {note}
    <figure><img src="{data_uri(case.doc_key, page)}" alt="The page as the PDF prints it">
      <figcaption>The page, rendered from the committed PDF. Zoom your browser if it is small.</figcaption>
    </figure>
    <div class="printed">
      <h3>What our own key proves is printed on this page</h3>
      <ul>{anchors}</ul>
      <p class="fine">These are the shape’s anchors: strings the key asserts are on the page. If a
        claim below contradicts them, the claim is the likelier defect.</p>
    </div>
    {card_html}
  </section>"""


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
        arms=_arm_table(arms),
        body=body,
        count=len(items),
        set_aside=", ".join(f"<code>{escape(key)}</code>" for key in set_aside),
    )


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Arbitrate the claims our arms contradict</title>
<style>
  :root {{ --ink:#221f1a; --paper:#faf6ec; --card:#fffdf7; --line:#d9cfba; --accent:#6b4f2a;
          --warn:#8a2f12; --ok:#2f5d33; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
         font-family:Georgia,'Times New Roman',serif; line-height:1.5; }}
  main {{ max-width:60rem; margin:0 auto; padding:1.5rem 1.25rem 4rem; }}
  h1 {{ font-size:1.75rem; line-height:1.2; margin:.5rem 0 .25rem; }}
  h2 {{ font-size:1.3rem; margin:2.5rem 0 .5rem; border-bottom:2px solid var(--line); padding-bottom:.35rem; }}
  h3 {{ font-size:1rem; margin:1.25rem 0 .35rem; }}
  p, li {{ font-size:1rem; }}
  .lead {{ background:var(--card); border:1px solid var(--line); border-left:6px solid var(--accent);
           padding:1rem 1.15rem; margin:1rem 0 1.5rem; }}
  .lead ol {{ margin:.5rem 0 0 1.1rem; padding:0; }}
  .where, .fine, figcaption {{ font-size:.85rem; color:#5c5347; font-family:system-ui,sans-serif; }}
  figure {{ margin:1rem 0; }}
  figure img {{ width:100%; max-width:46rem; border:1px solid var(--line); background:#fff; display:block; }}
  .printed {{ background:var(--card); border:1px solid var(--line); padding:.75rem 1rem; margin:1rem 0; }}
  .printed ul {{ margin:.4rem 0; padding-left:1.1rem; }}
  .printed code {{ font-size:.85rem; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:6px;
           padding:.9rem 1.1rem 1.1rem; margin:1rem 0; }}
  .card h3 {{ display:flex; gap:.6rem; align-items:baseline; flex-wrap:wrap; }}
  .count {{ font-family:system-ui,sans-serif; font-size:.75rem; text-transform:uppercase;
            letter-spacing:.04em; background:#efe6d2; border-radius:99px; padding:.15rem .5rem; }}
  .question {{ font-weight:bold; margin:.35rem 0; }}
  .key strong {{ background:#f3ead6; padding:.1rem .3rem; }}
  table {{ border-collapse:collapse; width:100%; margin:.6rem 0; font-family:system-ui,sans-serif;
           font-size:.85rem; }}
  table caption {{ text-align:left; font-size:.8rem; color:#5c5347; padding-bottom:.3rem; }}
  th, td {{ border-top:1px solid var(--line); padding:.35rem .45rem; text-align:left; vertical-align:top; }}
  tbody th {{ width:12rem; font-weight:600; }}
  code {{ font-family:ui-monospace,Consolas,monospace; font-size:.82rem; word-break:break-word; }}
  .verdict {{ display:flex; flex-direction:column; gap:.4rem; margin-top:.7rem;
              font-family:system-ui,sans-serif; font-size:.9rem; }}
  .verdict label {{ display:flex; gap:.5rem; align-items:center; }}
  .verdict input[type=radio] {{ width:1.1rem; height:1.1rem; }}
  .newtext {{ width:100%; padding:.4rem; border:1px solid var(--line); border-radius:4px;
              font-family:ui-monospace,Consolas,monospace; font-size:.85rem; }}
  .note {{ display:block; margin-top:.6rem; font-family:system-ui,sans-serif; font-size:.85rem; }}
  .note textarea {{ width:100%; padding:.4rem; border:1px solid var(--line); border-radius:4px;
                    font-family:inherit; font-size:.9rem; }}
  .chosen {{ border-color:var(--accent); box-shadow:0 0 0 2px #e6dcc6 inset; }}
  footer {{ margin-top:3rem; border-top:2px solid var(--line); padding-top:1rem; }}
  footer label {{ display:block; font-family:system-ui,sans-serif; font-size:.9rem; margin:.5rem 0; }}
  footer input {{ padding:.4rem; border:1px solid var(--line); border-radius:4px; min-width:16rem; }}
  button {{ font-family:system-ui,sans-serif; font-size:1rem; padding:.7rem 1.2rem; min-height:44px;
            border-radius:6px; border:1px solid var(--accent); background:var(--accent); color:#fff;
            cursor:pointer; }}
  button.secondary {{ background:transparent; color:var(--accent); }}
  dialog {{ border:1px solid var(--line); border-radius:8px; max-width:46rem; width:92%; }}
  dialog::backdrop {{ background:rgba(34,31,26,.45); }}
  #outProblems {{ color:var(--warn); }}
  #outText {{ width:100%; height:14rem; font-family:ui-monospace,Consolas,monospace; font-size:.8rem; }}
  .elsewhere {{ background:#eef3ea; border-left:4px solid var(--ok); padding:.5rem .75rem;
                font-family:system-ui,sans-serif; font-size:.9rem; }}
</style>
</head>
<body>
<main>
  <h1>Arbitrate the claims our own arms contradict</h1>
  {arms}
  <div class="lead">
    <p><strong>{count} claims need you.</strong> Each is a claim the eight-shape key makes that
    <em>at least two measured arms</em> contradict, on a shape <strong>no arm passes at all</strong>.
    The rest of the key is set aside: {set_aside} are passed under a declared convention, so their
    remaining failures are tool findings, not questions about the paper.</p>
    <ol>
      <li>Read the page and the words our own key proves are printed on it.</li>
      <li>For each claim: <strong>keep</strong> it, <strong>amend</strong> it (type what the paper
        says), or say <strong>can’t tell</strong>.</li>
      <li>Fill in your name, seat and date, export, and hand the file back. Nothing you do here
        leaves this machine.</li>
    </ol>
    <p class="fine">An <em>amend</em> is not applied by this page. Your answer is recorded, the key
    is edited in its own commit, and <code>scripts/shape_review_signoff.py --amend</code> pins the
    record to both texts.</p>
  </div>
  {body}
  <footer>
    <h2>Your call</h2>
    <label>Name <input id="name" autocomplete="name"></label>
    <label>Seat <input id="seat" placeholder="Product / Technical / Member"></label>
    <label>Date <input id="date" type="date"></label>
    <p><button id="export">Export the arbitration</button>
       <button id="clear" class="secondary">Clear everything</button></p>
    <p class="fine">Every card needs an answer before the export is written: <em>keep</em> needs
      nothing else, <em>amend</em> needs the corrected text, and <em>can’t tell</em> needs a
      reason.</p>
  </footer>
  <dialog id="outDlg">
    <h2>Arbitration export</h2>
    <p id="outLead"></p>
    <ul id="outProblems"></ul>
    <textarea id="outText" readonly hidden></textarea>
    <p><button id="dlgDl" hidden>Download JSON</button>
       <button id="dlgCopy" class="secondary" hidden>Copy JSON</button>
       <button id="dlgClose" class="secondary">Close</button></p>
  </dialog>
</main>
<script type="application/json" id="arb-data">{data}</script>
<script>
(function () {{
  var DATA = JSON.parse(document.getElementById('arb-data').textContent);
  var KEY = 'pgs-shape-arbitration-v1';
  var claims = DATA.claims;
  var state = {{ verdicts: {{}}, notes: {{}}, newtext: {{}}, name: '', seat: '', date: '' }};

  try {{
    var saved = localStorage.getItem(KEY);
    if (saved) {{ state = JSON.parse(saved); }}
  }} catch (e) {{ /* private mode: judge again */ }}

  function save() {{
    try {{ localStorage.setItem(KEY, JSON.stringify(state)); }} catch (e) {{ /* ignore */ }}
  }}

  function card(id) {{ return document.querySelector('[data-claim="' + id + '"]'); }}

  function paint() {{
    claims.forEach(function (claim) {{
      var node = card(claim.id);
      if (!node) {{ return; }}
      node.classList.toggle('chosen', Boolean(state.verdicts[claim.id]));
      var radios = node.querySelectorAll('input[type=radio]');
      Array.prototype.forEach.call(radios, function (radio) {{
        radio.checked = state.verdicts[claim.id] === radio.value;
      }});
      var text = node.querySelector('.newtext');
      if (state.newtext[claim.id] !== undefined) {{ text.value = state.newtext[claim.id]; }}
      var note = node.querySelector('.note textarea');
      if (state.notes[claim.id] !== undefined) {{ note.value = state.notes[claim.id]; }}
    }});
    document.getElementById('name').value = state.name || '';
    document.getElementById('seat').value = state.seat || '';
    document.getElementById('date').value = state.date || '';
  }}

  document.addEventListener('change', function (event) {{
    var node = event.target;
    var parent = node.closest ? node.closest('[data-claim]') : null;
    if (parent && node.type === 'radio') {{
      state.verdicts[parent.getAttribute('data-claim')] = node.value;
    }}
    if (parent && node.type === 'text') {{
      state.newtext[parent.getAttribute('data-claim')] = node.value;
    }}
    if (parent && node.tagName === 'TEXTAREA') {{
      state.notes[parent.getAttribute('data-claim')] = node.value;
    }}
    if (node.id === 'name') {{ state.name = node.value; }}
    if (node.id === 'seat') {{ state.seat = node.value; }}
    if (node.id === 'date') {{ state.date = node.value; }}
    save(); paint();
  }});

  document.addEventListener('input', function (event) {{
    var node = event.target;
    var parent = node.closest ? node.closest('[data-claim]') : null;
    if (parent && node.tagName === 'TEXTAREA') {{
      state.notes[parent.getAttribute('data-claim')] = node.value;
    }}
    if (parent && node.type === 'text') {{
      state.newtext[parent.getAttribute('data-claim')] = node.value;
    }}
    if (node.id === 'name') {{ state.name = node.value; }}
    if (node.id === 'seat') {{ state.seat = node.value; }}
    if (node.id === 'date') {{ state.date = node.value; }}
    save();
  }});

  function problems() {{
    var found = [];
    claims.forEach(function (claim) {{
      var verdict = state.verdicts[claim.id];
      var note = (state.notes[claim.id] || '').trim();
      if (!verdict) {{ found.push('“' + claim.id + '” is not answered yet.'); return; }}
      if (verdict === 'amend') {{
        var text = (state.newtext[claim.id] || claim.expected).trim();
        if (!text) {{ found.push('“' + claim.id + '” is amended to nothing — say what the paper prints.'); }}
        else if (text === claim.expected) {{ found.push('“' + claim.id + '” is amended to the text it already has.'); }}
        if (!note) {{ found.push('“' + claim.id + '” is amended without a reason.'); }}
      }}
      if (verdict === 'unsure' && !note) {{ found.push('“' + claim.id + '” reads can’t tell without a reason.'); }}
    }});
    if (!state.name.trim()) {{ found.push('Your name is missing.'); }}
    if (!state.seat.trim()) {{ found.push('Your seat is missing.'); }}
    if (!/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(state.date || '')) {{ found.push('The date is missing.'); }}
    return found;
  }}

  function payload() {{
    var out = {{ kind: DATA.kind, version: DATA.version, artefact: DATA.artefact,
                 reviewer: {{ name: state.name.trim(), seat: state.seat.trim() }},
                 reviewed_at: state.date, claims: {{}}, amendments: [], page_notes: {{}} }};
    claims.forEach(function (claim) {{
      var verdict = state.verdicts[claim.id];
      var note = (state.notes[claim.id] || '').trim();
      out.claims[claim.id] = {{ verdict: verdict, expected: claim.expected, note: note }};
      if (verdict === 'amend') {{
        out.amendments.push({{ claim: claim.id, from: claim.expected,
                             to: (state.newtext[claim.id] || '').trim(), basis: note }});
      }}
    }});
    return out;
  }}

  var dlg = document.getElementById('outDlg');
  document.getElementById('export').addEventListener('click', function () {{
    var found = problems();
    var list = document.getElementById('outProblems');
    list.innerHTML = '';
    found.forEach(function (problem) {{
      var li = document.createElement('li');
      li.textContent = problem;
      list.appendChild(li);
    }});
    var text = document.getElementById('outText');
    var lead = document.getElementById('outLead');
    if (found.length) {{
      lead.textContent = 'These are not answers yet. Finish them and export again.';
      text.hidden = true; text.value = '';
      document.getElementById('dlgDl').hidden = true;
      document.getElementById('dlgCopy').hidden = true;
    }} else {{
      lead.textContent = 'Every claim is answered. Download this file and hand it over.';
      text.hidden = false;
      text.value = JSON.stringify(payload(), null, 2);
      document.getElementById('dlgDl').hidden = false;
      document.getElementById('dlgCopy').hidden = false;
    }}
    if (dlg.showModal) {{ dlg.showModal(); }}
  }});

  document.getElementById('dlgClose').addEventListener('click', function () {{ dlg.close(); }});
  document.getElementById('dlgCopy').addEventListener('click', function () {{
    var text = document.getElementById('outText');
    text.select();
    try {{ navigator.clipboard.writeText(text.value); }} catch (e) {{ document.execCommand('copy'); }}
    this.textContent = 'Copied';
    var self = this;
    setTimeout(function () {{ self.textContent = 'Copy JSON'; }}, 1400);
  }});
  document.getElementById('dlgDl').addEventListener('click', function () {{
    var blob = new Blob([document.getElementById('outText').value], {{ type: 'application/json' }});
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'shape-arbitration.json';
    link.click();
    URL.revokeObjectURL(link.href);
  }});
  document.getElementById('clear').addEventListener('click', function () {{
    if (!confirm('Clear every answer, note and name? This cannot be undone.')) {{ return; }}
    state = {{ verdicts: {{}}, notes: {{}}, newtext: {{}}, name: '', seat: '', date: '' }};
    try {{ localStorage.removeItem(KEY); }} catch (e) {{ /* ignore */ }}
    paint();
  }});

  paint();
}})();
</script>
</body>
</html>
"""


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
    items = tuple(
        item
        for item in disagreements(arms)
        if item.claim_id.split(".")[0] not in PASSED_ELSEWHERE
    )
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
