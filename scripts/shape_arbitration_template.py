"""The arbitration page's markup, stylesheet and script — one file, because it fails here.

Split from `scripts/shape_arbitration.py` for `build_principles.md` §II's 30 KB cap, not for a
different reason: a claim is wrong in a review, and the markup is wrong in a browser. Nothing here
is imported by the gate; `scripts/shape_arbitration.py` formats it and a tooling test asserts the
committed artefact equals the result.

The placeholders are `{artefact}`, `{data}`, `{arms}`, `{settled}`, `{body}`, `{count}` and
`{set_aside}`; every literal brace in the CSS and the script is doubled.
"""

from __future__ import annotations

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
  .decided {{ background:#efe6d2; border-left:4px solid var(--accent); padding:.55rem .8rem;
               font-family:system-ui,sans-serif; font-size:.9rem; margin:.6rem 0; }}
  .settled {{ background:var(--card); border:1px solid var(--line); border-radius:6px;
              padding:.6rem 1rem; margin:1rem 0; }}
  .settled h2 {{ font-size:1rem; margin:.2rem 0 .4rem; border:0; padding:0; }}
  .settled ul {{ margin:0; padding-left:1.1rem; }}
  .settled li {{ font-size:.9rem; font-family:system-ui,sans-serif; }}
  .page {{ font-family:system-ui,sans-serif; font-size:.72rem; letter-spacing:.04em;
           text-transform:uppercase; color:#5c5347; }}
  pre.paper {{ background:#f2ede0; border:1px solid var(--line); border-radius:4px;
               padding:.5rem .6rem; overflow-x:auto; font-size:.78rem; line-height:1.45; }}
  pre.paper span {{ display:block; white-space:pre; }}
  pre.paper .hit {{ font-weight:bold; background:#e6dcc6; }}
  pre.paper .ctx {{ color:#6b6459; }}
  .elsewhere {{ background:#eef3ea; border-left:4px solid var(--ok); padding:.5rem .75rem;
                font-family:system-ui,sans-serif; font-size:.9rem; }}
</style>
</head>
<body>
<main>
  <h1>Arbitrate the claims our own arms contradict</h1>
  {arms}
  {settled}
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
        else if (/^[a-z_]+:/.test(text) || /^(row \\d+ cell|columns |row pages|\\d+ rows, the page prints)/.test(text)) {{
          found.push('“' + claim.id + '” holds an arm’s report, not a claim — write it as ' +
            'empty, text=…, starts=…, ends=…, contains=… or at_least=N.');
        }}
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
