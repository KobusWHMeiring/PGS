"""The review surface's look and behaviour: one stylesheet and one script, in full.

Kept apart from the markup (`scripts/shape_review_page.py`) for a boring reason with a real cost:
`build_principles.md` §II caps a file at 30 KB, and the two together are over it. The split is also
the honest one — everything a reviewer *sees as a claim* is server-rendered markup, and everything in
here only styles it or records a verdict. If JavaScript is off, the page still shows every page image,
every grid and every claim; it simply cannot save or export.

`CSS` is a full stylesheet: cream ground, green accent, ≥40 px targets, print rules. `SCRIPT` is an
IIFE with no imports and no network call: it restores from `localStorage`, fills the progress counts,
reveals a reason box for `No` and `Can't tell`, opens the page image at 100%, and builds the export
JSON. It refuses to export while any claim is unjudged, any `No`/`Can't tell` has no reason, or the
reviewer's name, seat or date is missing — a judgement surface that will emit a half-made signature is
a machine for false evidence.

`tests/e2e/test_shape_review_artefact.py` is the only check that executes this script; the structural
tests would all stay green if it did not parse (`testing_hazards.md` §1.30).
"""

from __future__ import annotations

CSS = """  :root {
    --bg:            #f4f6f2;
    --surface:       #ffffff;
    --surface-low:   #eaeee6;
    --surface-high:  #dfe5da;
    --accent:        #35604a;
    --accent-soft:   #e4efe7;
    --accent-line:   #b9cfc0;
    --text:          #1c2620;
    --muted:         #66756b;
    --warn:          #8a5a1c;
    --warn-soft:     #f7efe1;
    --bad:           #8a3b2c;
    --bad-soft:      #f7e7e3;
    --ok:            #2f6b48;
    --ok-soft:       #e8f2eb;
    --radius:        12px;
    --shadow:        0 1px 2px rgba(28,38,32,.06), 0 6px 20px -8px rgba(28,38,32,.14);
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body { margin: 0; font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.55; }
  .wrap { max-width: 1320px; margin: 0 auto; padding: 0 18px 150px; }

  header.hero { background: linear-gradient(160deg, var(--accent) 0%, #274936 100%); color: #fff; padding: 40px 18px 34px; }
  header.hero .inner { max-width: 1320px; margin: 0 auto; }
  header.hero .eyebrow { font-size: 11px; letter-spacing: .14em; text-transform: uppercase; opacity: .8; margin: 0 0 10px; font-weight: 600; }
  header.hero h1 { margin: 0 0 12px; font-size: 30px; line-height: 1.2; letter-spacing: -.01em; }
  header.hero .q { margin: 0; max-width: 74ch; font-size: 17px; line-height: 1.45; background: rgba(255,255,255,.10); border-left: 3px solid rgba(255,255,255,.55); padding: 12px 16px; border-radius: 0 10px 10px 0; }
  header.hero .meta { margin-top: 16px; font-size: 13px; opacity: .88; display: flex; flex-wrap: wrap; gap: 6px 22px; }
  header.hero code { font-family: var(--mono); font-size: 12px; }

  .card { background: var(--surface); border: 1px solid var(--surface-high); border-radius: var(--radius); box-shadow: var(--shadow); padding: 22px 24px; margin: 22px 0; }
  .card h2, .shape h2 { margin: 0 0 10px; font-size: 21px; letter-spacing: -.01em; }
  .card h3, .judge h3, .claims h3 { margin: 0 0 8px; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-weight: 700; }
  .lede { font-size: 16px; }
  .card p { max-width: 92ch; }
  .hint { color: var(--muted); font-size: 13px; }
  code { font-family: var(--mono); font-size: .92em; background: var(--surface-low); padding: 1px 5px; border-radius: 4px; }

  .callout { background: var(--accent-soft); border-left: 3px solid var(--accent-line); border-radius: 0 10px 10px 0; padding: 12px 16px; margin: 14px 0; }
  .callout .label { display: block; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--accent); font-weight: 700; margin-bottom: 4px; }
  .callout p { margin: 0; }

  .shape { background: var(--surface); border: 1px solid var(--surface-high); border-radius: 16px; box-shadow: var(--shadow); margin: 26px 0; overflow: hidden; }
  .shape-head { padding: 20px 24px 14px; border-bottom: 1px solid var(--surface-high); background: linear-gradient(180deg, #fbfcfa, #ffffff); }
  .shape-head .tag { display: inline-block; margin: 0 0 6px; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--accent); font-weight: 700; }
  .shape-head .src { margin: 0; font-size: 14px; }
  .shape-head .thin { margin: 8px 0 0; font-size: 13px; color: var(--muted); max-width: 100ch; }

  .panes { display: grid; grid-template-columns: minmax(320px, 46%) 1fr; gap: 22px; padding: 20px 24px 26px; }
  @media (max-width: 980px) { .panes { grid-template-columns: 1fr; } }

  figure.page { margin: 0; position: sticky; top: 14px; align-self: start; }
  .shot { width: 100%; aspect-ratio: 210 / 297; background-size: contain; background-repeat: no-repeat; background-position: top left; border: 1px solid var(--surface-high); border-radius: 8px; box-shadow: inset 0 0 0 1px #fff, 0 8px 24px -14px rgba(28,38,32,.4); cursor: zoom-in; background-color: #fff; }
  .shot.zoomed { cursor: default; background-size: auto; width: max-content; min-width: 100%; height: auto; }
  figure.page figcaption { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin-top: 8px; font-size: 12px; color: var(--muted); }

  .grid-wrap { overflow-x: auto; border: 1px solid var(--surface-high); border-radius: 10px; }
  table.expect { border-collapse: collapse; width: 100%; font-size: 13px; }
  table.expect thead th { background: var(--surface-low); text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--surface-high); font-size: 12px; vertical-align: bottom; }
  table.expect td { padding: 7px 10px; border-bottom: 1px solid var(--surface-low); vertical-align: top; line-height: 1.35; }
  table.expect th.gutter { width: 52px; background: var(--surface-low); text-align: left; padding: 6px 8px; font-weight: 600; border-bottom: 1px solid var(--surface-low); }
  table.expect .rn { display: block; font-size: 12px; }
  table.expect .pg { display: block; font-size: 10px; color: var(--muted); font-weight: 500; }
  table.expect td.claimed { background: #fff; }
  table.expect td.empty { color: var(--muted); font-style: italic; }
  table.expect td.unclaimed { color: #b3bdb5; text-align: center; }
  table.expect tr.divider td { background: var(--warn-soft); font-size: 12px; }
  table.expect tr.divider .kind { display: inline-block; font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--warn); font-weight: 700; margin-right: 6px; }
  .legend { font-size: 11.5px; color: var(--muted); margin: 8px 0 18px; }
  .claimed-key { display: inline-block; padding: 0 4px; border-radius: 3px; background: #fff; border: 1px solid var(--surface-high); }
  .unclaimed-key { color: #9aa79f; }

  ol.claim-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
  fieldset.claim { border: 1px solid var(--surface-high); border-radius: 10px; padding: 12px 14px; margin: 0; background: #fff; }
  fieldset.claim[data-verdict="yes"] { border-color: var(--accent-line); background: var(--ok-soft); }
  fieldset.claim[data-verdict="no"] { border-color: #d9b6ad; background: var(--bad-soft); }
  fieldset.claim[data-verdict="unsure"] { border-color: #dcc7a3; background: var(--warn-soft); }
  legend.cq { font-size: 14px; font-weight: 600; padding: 0 4px; max-width: 76ch; }
  .ca { margin: 4px 0 10px; font-size: 13.5px; color: var(--muted); }
  .vrow { display: flex; flex-wrap: wrap; gap: 8px; }
  .v { display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border: 1px solid var(--surface-high); border-radius: 999px; font-size: 13.5px; cursor: pointer; background: #fff; min-height: 40px; }
  .v:hover { border-color: var(--accent-line); }
  .v input { accent-color: var(--accent); }
  .v.no { color: var(--bad); }
  .v.unsure { color: var(--warn); }
  textarea { width: 100%; font: inherit; font-size: 13.5px; padding: 8px 10px; border: 1px solid var(--surface-high); border-radius: 8px; resize: vertical; background: #fff; color: var(--text); }
  textarea.cnote { margin-top: 8px; }
  textarea.cnote[hidden] { display: none; }
  .page-note { display: block; margin-top: 16px; font-size: 13px; color: var(--muted); }
  .page-note span { display: block; margin-bottom: 6px; }

  .toc { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 8px; margin: 22px 0 0; }
  .toc-item { display: flex; align-items: center; gap: 10px; text-align: left; border-radius: 10px; padding: 10px 12px; background: #fff; border: 1px solid var(--surface-high); box-shadow: var(--shadow); }
  .toc-item:hover { border-color: var(--accent-line); }
  .toc-item .n { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); font-size: 12px; font-weight: 700; flex: none; }
  .toc-item .nm { flex: 1; font-size: 13.5px; }
  .toc-item .sprog { font-size: 11.5px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .toc-item .sprog.done { color: var(--ok); font-weight: 700; }

  .who { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
  .who label { display: block; font-size: 12px; color: var(--muted); }
  .who input { width: 100%; margin-top: 4px; font: inherit; font-size: 14px; padding: 9px 10px; border: 1px solid var(--surface-high); border-radius: 8px; background: #fff; color: var(--text); }

  .bar { position: fixed; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,.96); backdrop-filter: blur(6px); border-top: 1px solid var(--surface-high); box-shadow: 0 -2px 12px rgba(28,38,32,.06); z-index: 20; }
  .bar .inner { max-width: 1320px; margin: 0 auto; padding: 10px 18px; display: flex; align-items: center; gap: 12px; }
  .bar .spacer { flex: 1; }
  .progress { font-size: 13.5px; }
  .progress b { font-variant-numeric: tabular-nums; }
  .saved { font-size: 12px; color: var(--accent); opacity: 0; transition: opacity .2s; }
  .saved.show { opacity: 1; }
  button { font: inherit; font-size: 14px; border-radius: 999px; padding: 9px 16px; cursor: pointer; border: 1px solid var(--surface-high); background: #fff; color: var(--text); min-height: 42px; }
  button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
  button.primary:hover { background: #2b4e3c; }
  button.ghost { background: transparent; color: var(--muted); }
  button.zoom { padding: 5px 11px; font-size: 12px; min-height: 34px; }

  dialog { border: none; border-radius: 14px; padding: 0; width: min(94vw, 1100px); box-shadow: 0 20px 60px -20px rgba(0,0,0,.5); }
  dialog::backdrop { background: rgba(20,28,24,.55); }
  .dlg-head { padding: 16px 20px 10px; border-bottom: 1px solid var(--surface-high); }
  .dlg-head h3 { margin: 0 0 4px; font-size: 17px; }
  .dlg-head p { margin: 0; font-size: 13px; color: var(--muted); }
  .zoom-wrap { max-height: 78vh; overflow: auto; padding: 14px; background: var(--surface-low); }
  .dlg-body { padding: 14px 20px; }
  .dlg-foot { display: flex; gap: 10px; justify-content: flex-end; padding: 12px 20px 16px; border-top: 1px solid var(--surface-high); }
  #outText { min-height: 240px; font-family: var(--mono); font-size: 12px; }
  ul.problems { margin: 0 0 10px; padding-left: 18px; font-size: 13.5px; max-height: 46vh; overflow: auto; }
  ul.problems:empty { display: none; }
  ul.problems li { margin-bottom: 4px; }
  ul.problems li.warn { color: var(--warn); }

  @media print {
    .bar, .shot, dialog, button, .who { display: none !important; }
    body { background: #fff; }
    .shape, .card { break-inside: avoid; box-shadow: none; }
  }"""

SCRIPT = """(function () {
  'use strict';
  var DATA = JSON.parse(document.getElementById('shape-data').textContent);
  var KEY = 'pgs.shape-key-review.v1';
  var state = { verdicts: {}, notes: {}, pages: {}, name: '', seat: '', date: '' };
  var saved = false;
  try {
    var prior = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (prior && typeof prior === 'object') {
      state.verdicts = prior.verdicts || {};
      state.notes = prior.notes || {};
      state.pages = prior.pages || {};
      state.name = prior.name || '';
      state.seat = prior.seat || '';
      state.date = prior.date || '';
    }
  } catch (e) { /* a corrupt save is not a reason to refuse the page */ }

  var claims = [];
  DATA.shapes.forEach(function (shape) {
    shape.claims.forEach(function (claim) { claims.push(claim); });
  });

  var els = {
    progress: document.getElementById('progress'),
    saved: document.getElementById('saved'),
    name: document.getElementById('rv-name'),
    seat: document.getElementById('rv-seat'),
    date: document.getElementById('rv-date'),
    outDlg: document.getElementById('outDlg'),
    outText: document.getElementById('outText'),
    outProblems: document.getElementById('outProblems'),
    outLead: document.getElementById('outLead'),
    dlgDl: document.getElementById('dlgDl'),
    dlgCopy: document.getElementById('dlgCopy'),
    dlgClose: document.getElementById('dlgClose'),
    zoomDlg: document.getElementById('zoomDlg'),
    zoomShot: document.getElementById('zoomShot'),
    zoomWhich: document.getElementById('zoomWhich')
  };

  if (!state.date) {
    var now = new Date();
    state.date = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') +
                 '-' + String(now.getDate()).padStart(2, '0');
  }

  function persist() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* private mode */ }
    els.saved.classList.add('show');
    clearTimeout(persist.timer);
    persist.timer = setTimeout(function () { els.saved.classList.remove('show'); }, 1200);
    render();
  }

  function judged() {
    return claims.filter(function (c) { return !!state.verdicts[c.id]; }).length;
  }

  function render() {
    var done = judged();
    els.progress.innerHTML = '<b>' + done + '</b> of <b>' + claims.length + '</b> claims judged' +
      (done === claims.length ? ' — ready to export' : '');
    els.name.value = state.name;
    els.seat.value = state.seat;
    els.date.value = state.date;
    claims.forEach(function (claim) {
      var verdict = state.verdicts[claim.id] || '';
      var card = document.querySelector('[data-claim="' + claim.id + '"]');
      if (card) { card.setAttribute('data-verdict', verdict); }
      var note = document.querySelector('[data-note="' + claim.id + '"]');
      if (note) {
        note.value = state.notes[claim.id] || '';
        note.hidden = !(verdict === 'no' || verdict === 'unsure');
      }
    });
    DATA.shapes.forEach(function (shape) {
      var box = document.querySelector('[data-page="' + shape.key + '"]');
      if (box) { box.value = state.pages[shape.key] || ''; }
      var doneHere = shape.claims.filter(function (c) { return !!state.verdicts[c.id]; }).length;
      var badge = document.querySelector('[data-progress="' + shape.key + '"]');
      if (badge) {
        badge.textContent = doneHere + '/' + shape.claims.length;
        badge.className = 'sprog' + (doneHere === shape.claims.length ? ' done' : '');
      }
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll('[data-goto]'), function (node) {
    node.addEventListener('click', function () {
      var target = document.getElementById(node.getAttribute('data-goto'));
      if (target) { target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
  });

  claims.forEach(function (claim) {
    var card = document.querySelector('[data-claim="' + claim.id + '"]');
    if (!card) { return; }
    Array.prototype.forEach.call(card.querySelectorAll('input[type=radio]'), function (input) {
      input.checked = state.verdicts[claim.id] === input.value;
      input.addEventListener('change', function () {
        state.verdicts[claim.id] = input.value;
        persist();
      });
    });
    var note = card.querySelector('[data-note]');
    if (note) {
      note.addEventListener('input', function () {
        state.notes[claim.id] = note.value;
        persist();
      });
    }
  });

  DATA.shapes.forEach(function (shape) {
    var box = document.querySelector('[data-page="' + shape.key + '"]');
    if (box) {
      box.addEventListener('input', function () {
        state.pages[shape.key] = box.value;
        persist();
      });
    }
  });

  els.name.addEventListener('input', function () { state.name = els.name.value; persist(); });
  els.seat.addEventListener('input', function () { state.seat = els.seat.value; persist(); });
  els.date.addEventListener('change', function () { state.date = els.date.value; persist(); });

  function problems() {
    var found = [];
    if (!state.name.trim()) { found.push('Your name is missing, at the bottom of the page.'); }
    if (!state.seat.trim()) { found.push('Your seat is missing (for example: Product owner).'); }
    if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(state.date)) { found.push('The date is missing.'); }
    claims.forEach(function (claim) {
      var verdict = state.verdicts[claim.id];
      if (!verdict) {
        found.push('Not judged: ' + claim.question);
      } else if ((verdict === 'no' || verdict === 'unsure') && !(state.notes[claim.id] || '').trim()) {
        found.push('A reason is needed for "' + claim.question + '" — what does the paper print?');
      }
    });
    if (!found.length) {
      var unsure = claims.filter(function (claim) { return state.verdicts[claim.id] === 'unsure'; });
      if (unsure.length) {
        found.push('Every claim is answered \u2014 but ' + unsure.length +
          ' read Can\u2019t tell, so the key stays unconfirmed there.');
      }
    }
    return found;
  }

  function payload() {
    var out = { kind: DATA.kind, version: DATA.version, artefact: DATA.artefact,
                reviewer: { name: state.name.trim(), seat: state.seat.trim() },
                reviewed_at: state.date, claims: {}, page_notes: {} };
    claims.forEach(function (claim) {
      out.claims[claim.id] = {
        verdict: state.verdicts[claim.id],
        expected: claim.expected,
        note: (state.notes[claim.id] || '').trim()
      };
    });
    DATA.shapes.forEach(function (shape) {
      var note = (state.pages[shape.key] || '').trim();
      if (note) { out.page_notes[shape.key] = note; }
    });
    return out;
  }

  function showExport() {
    var found = problems();
    var body = payload();
    var text = JSON.stringify(body, null, 2);
    els.outProblems.innerHTML = '';
    if (found.length) {
      found.forEach(function (problem) {
        var li = document.createElement('li');
        li.textContent = problem;
        if (problem.indexOf('Can\u2019t tell') !== -1) { li.className = 'warn'; }
        els.outProblems.appendChild(li);
      });
      els.outLead.textContent = 'These are not judgements yet. Finish them and export again.';
      els.outText.hidden = true;
      els.outText.value = '';
      els.dlgDl.hidden = true;
      els.dlgCopy.hidden = true;
    } else {
      els.outLead.textContent = 'Every claim is judged. Download this file and hand it over.';
      els.outText.hidden = false;
      els.outText.value = text;
      els.dlgDl.hidden = false;
      els.dlgCopy.hidden = false;
    }
    if (els.outDlg.showModal) { els.outDlg.showModal(); }
  }

  document.getElementById('export').addEventListener('click', showExport);

  els.dlgClose.addEventListener('click', function () { els.outDlg.close(); });

  els.dlgCopy.addEventListener('click', function () {
    els.outText.select();
    try {
      navigator.clipboard.writeText(els.outText.value);
    } catch (e) {
      document.execCommand('copy');
    }
    els.dlgCopy.textContent = 'Copied';
    setTimeout(function () { els.dlgCopy.textContent = 'Copy JSON'; }, 1400);
  });

  els.dlgDl.addEventListener('click', function () {
    var blob = new Blob([els.outText.value], { type: 'application/json' });
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'shape-key-review.json';
    link.click();
    URL.revokeObjectURL(link.href);
  });

  Array.prototype.forEach.call(document.querySelectorAll('[data-zoom]'), function (node) {
    node.addEventListener('click', function (event) {
      event.preventDefault();
      var className = node.getAttribute('data-zoom');
      els.zoomShot.className = 'shot zoomed ' + className;
      els.zoomWhich.textContent = className.replace('page-', '').replace('_p', ', PDF page ');
      if (els.zoomDlg.showModal) { els.zoomDlg.showModal(); }
    });
  });

  document.getElementById('zoomClose').addEventListener('click', function () { els.zoomDlg.close(); });

  document.getElementById('clear').addEventListener('click', function () {
    if (!confirm('Clear every verdict, note and name? This cannot be undone.')) { return; }
    state = { verdicts: {}, notes: {}, pages: {}, name: '', seat: '', date: '' };
    try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ }
    render();
  });

  render();
})();"""
