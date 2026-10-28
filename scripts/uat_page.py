"""The artefact's shell: its CSS, its script, and the markdown renderer that feeds it.

Split out of `uat_runner.py` because that file crossed `build_principles.md` §II's 30 KB
cap once the page existed — the cap is on source size, and a shell is source.

Nothing here decides anything. `STYLE` and `SCRIPT` are plain strings so they need no
f-string brace-doubling (which is what made the single-file version tiring to edit), and
`page()` interpolates only the values.

**No link, no `src`, no `href`, no `fetch`.** The artefact must make zero requests: a
reviewer opens it from `file://` in a room with no wifi, and their notes must not leave
the machine. `tests/tools/test_uat_runner.py` greps the output for all four.
"""

from __future__ import annotations

import html
import re
import subprocess
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)
CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
EM_RE = re.compile(r"\*([^*\n]+?)\*")
TOKEN_RE = re.compile("\x00(\\d+)\x00")
STEP_RE = re.compile(r"^\d+\.\s")


# ------------------------------------------------------------------ prose to html


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def render_inline(text: str) -> str:
    """Escape, then apply the three inline marks the UAT files actually use.

    Code spans are stashed before emphasis runs, so a backticked `*` stays a `*` rather
    than opening an `<em>` that never closes. No link syntax is supported on purpose —
    an anchor is the one tag that could carry a URL into an artefact that must make no
    requests.
    """
    escaped = _escape(text)
    stash: list[str] = []

    def _keep(match: re.Match[str]) -> str:
        stash.append(match.group(1))
        return f"\x00{len(stash) - 1}\x00"

    escaped = CODE_RE.sub(_keep, escaped)
    escaped = BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = EM_RE.sub(r"<em>\1</em>", escaped)

    def _restore(match: re.Match[str]) -> str:
        return f"<code>{_escape(stash[int(match.group(1))])}</code>"

    return TOKEN_RE.sub(_restore, escaped)


def _block(chunk: str) -> str:
    lines = [line for line in chunk.splitlines() if line.strip()]
    if not lines:
        return ""
    if all(line.lstrip().startswith(("* ", "- ")) for line in lines):
        items = "".join(f"<li>{render_inline(line.lstrip()[2:])}</li>" for line in lines)
        return f"<ul>{items}</ul>"
    if STEP_RE.match(lines[0]):
        items: list[str] = []
        for line in lines:
            match = re.match(r"^\d+\.\s+(.*)$", line)
            if match:
                items.append(match.group(1))
            else:
                items[-1] = f"{items[-1]} {line.strip()}"
        return "<ol>" + "".join(f"<li>{render_inline(i)}</li>" for i in items) + "</ol>"
    return f"<p>{render_inline(' '.join(line.strip() for line in lines))}</p>"


def _render_paragraphs(chunk: str) -> str:
    return "".join(_block(block) for block in re.split(r"\n\s*\n", chunk))


def render_prose(text: str) -> str:
    """Render the UAT file's own markdown to HTML: paragraphs, lists, fenced commands.

    In: a scenario's prose — judgement, setup, expected, a note.
    Out: escaped HTML. Never a link, never a remote asset.
    Side Effects: none.
    Fails: never.
    """
    out: list[str] = []
    position = 0
    for match in FENCE_RE.finditer(text):
        out.append(_render_paragraphs(text[position : match.start()]))
        out.append(f'<pre class="cmd"><code>{_escape(match.group(1).rstrip())}</code></pre>')
        position = match.end()
    out.append(_render_paragraphs(text[position:]))
    return "".join(out)


# ------------------------------------------------------------------- environment


def _git(*args: str) -> str:
    """Best-effort `git` output. An unknown commit is recorded as unknown, never guessed."""
    try:
        result = subprocess.run(
            ("git", *args),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def environment(database: str, out_path: Path | None = None) -> dict[str, object]:
    """What this artefact was generated against — commit, working-tree state, database.

    A signature on a build nobody can identify is not evidence (PRD §7), so these three
    travel in the header and in the export.

    In:  `database` — the instance the reviewer will judge; `out_path` — the artefact this
         generation is writing, which is excluded from the dirty check.
    Out: `{commit, working_tree, database, generated_on}`.
    Side effects: two `git` calls.
    Fails: never — an unknown commit is recorded as unknown.

    Why `out_path` is excluded: regenerating the artefact *always* leaves it differing from the
    commit it was generated on, so without this every signature says `working_tree: modified` while
    the only difference is the output itself — which makes a clean signature impossible and teaches
    reviewers to ignore the field (found on the 2026-10-28 concordance sign-off).
    """
    commit = _git("rev-parse", "--short", "HEAD") or "unknown"
    status = _git("status", "--porcelain")
    if out_path is not None and status:
        try:
            own = out_path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:  # an artefact written outside the repo cannot be the reason it is dirty
            own = ""
        if own:
            status = "\n".join(
                line for line in status.splitlines() if own not in line
            )
    dirty = bool(status.strip())
    return {
        "commit": commit,
        "working_tree": "modified" if dirty else "clean",
        "database": database or "not stated",
        "generated_on": date.today().isoformat(),
    }


STYLE = """
  :root {
    --bg: #f4f6f2; --surface: #ffffff; --surface-low: #eaeee6; --surface-high: #dfe5da;
    --accent: #35604a; --accent-soft: #e4efe7; --accent-line: #b9cfc0;
    --text: #1c2620; --muted: #66756b; --warn: #8a5a1c; --warn-soft: #f7efe1;
    --bad: #8c2f24; --bad-soft: #fbeeec;
    --radius-lg: 14px; --radius-xl: 20px;
    --shadow: 0 1px 2px rgba(28,38,32,.06), 0 6px 20px -8px rgba(28,38,32,.14);
    --shadow-sticky: 0 2px 10px rgba(28,38,32,.10);
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: var(--font); background: var(--bg); color: var(--text);
         line-height: 1.55; -webkit-font-smoothing: antialiased; }
  .wrap { max-width: 900px; margin: 0 auto; padding: 0 20px 170px; }
  header.hero { background: linear-gradient(160deg, var(--accent) 0%, #274936 100%);
    color: #fff; padding: 40px 20px 34px; margin-bottom: 26px; }
  header.hero .inner { max-width: 900px; margin: 0 auto; }
  header.hero .eyebrow { font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
    opacity: .78; margin: 0 0 10px; font-weight: 600; }
  header.hero h1 { margin: 0 0 10px; font-size: 27px; line-height: 1.22; letter-spacing: -.01em; }
  header.hero p { margin: 0; max-width: 64ch; opacity: .92; font-size: 15px; }
  header.hero .meta { margin-top: 16px; font-size: 13px; opacity: .85;
    display: flex; flex-wrap: wrap; gap: 8px 18px; }
  header.hero .meta code { font-family: var(--mono); font-size: 12px;
    background: rgba(255,255,255,.14); padding: 2px 7px; border-radius: 6px; }
  .panel { background: var(--surface); border-radius: var(--radius-xl); padding: 20px 22px;
    box-shadow: var(--shadow); margin-bottom: 22px; }
  .panel h2 { margin: 0 0 6px; font-size: 16px; }
  .panel p { margin: 0 0 10px; font-size: 14.5px; color: var(--muted); }
  .panel ol, .panel ul { margin: 8px 0 0; padding-left: 20px; font-size: 14.5px; color: var(--muted); }
  .panel li { margin-bottom: 5px; }
  .who-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
  .who-row label { font-size: 12px; color: var(--muted); display: block; margin-bottom: 4px; }
  input[type=text], input[type=date], select, textarea {
    font: inherit; color: inherit; background: var(--surface-low); border: 1px solid var(--surface-high);
    border-radius: 10px; padding: 9px 11px; min-height: 44px; width: 100%; }
  textarea { resize: vertical; }
  input:focus, select:focus, textarea:focus { outline: 2px solid var(--accent-line); outline-offset: 1px; }
  .hint { font-size: 12.5px; color: var(--muted); margin: 6px 0 0; }
  pre { font-family: var(--mono); font-size: 12.5px; background: #1c2620; color: #e6eee8;
    border-radius: 12px; padding: 13px 15px; overflow-x: auto; }
  pre.preflight { background: var(--surface-low); color: var(--text); border: 1px solid var(--surface-high); }
  .prose p, .judgement-body p { margin: 0 0 9px; font-size: 14.5px; }
  .prose li, .judgement-body li { font-size: 14.5px; margin-bottom: 6px; }
  .prose code, .judgement-body code, .steps code { font-family: var(--mono); font-size: 12.8px;
    background: var(--surface-low); padding: 1px 5px; border-radius: 5px; }
  .cmd code { background: none; padding: 0; font-size: 12.5px; }

  /* ---------- card ---------- */
  .card { background: var(--surface); border-radius: var(--radius-xl); padding: 22px 24px 20px;
    box-shadow: var(--shadow); margin-bottom: 26px; }
  .card.na { background: var(--surface-low); }
  .card-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
    border-bottom: 1px solid var(--surface-high); padding-bottom: 12px; margin-bottom: 16px; }
  .card-head .num { font-size: 12px; font-weight: 700; letter-spacing: .08em;
    background: var(--accent); color: #fff; border-radius: 7px; padding: 3px 8px; }
  .card.na .card-head .num { background: var(--muted); }
  .card-head h2 { margin: 0; font-size: 19px; line-height: 1.3; flex: 1 1 320px; }
  .tag { font-size: 11.5px; color: var(--muted); background: var(--surface-low);
    border: 1px solid var(--surface-high); border-radius: 999px; padding: 3px 10px; }
  .banner { border-radius: 12px; padding: 12px 14px; font-size: 14px; margin-bottom: 16px; }
  .banner.not-applicable { background: var(--warn-soft); color: var(--warn);
    border: 1px solid #e8d4b3; }
  .judgement { background: var(--accent-soft); border-left: 4px solid var(--accent);
    border-radius: 0 14px 14px 0; padding: 15px 18px; margin-bottom: 18px; }
  .judgement .label { color: var(--accent); }
  .judgement-body p:last-child { margin-bottom: 0; }
  .field { margin-bottom: 16px; }
  .label { margin: 0 0 6px; font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
    font-weight: 700; color: var(--muted); }
  .steps { margin: 0; padding-left: 22px; }
  .steps li { font-size: 14.5px; margin-bottom: 7px; }
  .note .prose { font-size: 13.5px; color: var(--muted); }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .file { padding: 8px; background: var(--surface-low); border: 1px solid var(--surface-high);
    border-radius: 10px; font: inherit; font-size: 13px; min-height: 44px; }
  button { font: inherit; cursor: pointer; border: 1px solid var(--surface-high);
    background: var(--surface-low); color: var(--text); border-radius: 10px;
    padding: 10px 16px; min-height: 44px; }
  button:hover { background: var(--surface-high); }
  button.tiny { font-size: 12.5px; padding: 6px 11px; min-height: 36px; }
  button.ghost { background: transparent; color: var(--muted); }
  button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
  button.primary:hover { background: #2b5039; }
  button:disabled { opacity: .45; cursor: not-allowed; }

  /* ---------- result ---------- */
  .result { border-top: 1px solid var(--surface-high); padding-top: 15px; margin-top: 4px; }
  .choices { display: flex; gap: 9px; flex-wrap: wrap; margin-bottom: 12px; }
  .choice { flex: 1 1 110px; font-weight: 700; letter-spacing: .04em; }
  .choice.pass[aria-pressed=true] { background: var(--accent); color: #fff; border-color: var(--accent); }
  .choice.fail[aria-pressed=true] { background: var(--bad); color: #fff; border-color: var(--bad); }
  .choice.na[aria-pressed=true] { background: var(--warn); color: #fff; border-color: var(--warn); }
  .who { display: flex; gap: 9px; flex-wrap: wrap; }
  .who input[type=text] { flex: 2 1 160px; }
  .who select { flex: 1 1 150px; }
  .who input[type=date] { flex: 1 1 140px; }
  .status { margin: 10px 0 0; font-size: 12.5px; color: var(--muted); }
  .status.ok { color: var(--accent); }
  .status.bad { color: var(--bad); }
  .reason { background: var(--warn-soft); border-radius: 12px; padding: 12px 14px; }

  /* ---------- bar ---------- */
  .bar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 20;
    background: rgba(255,255,255,.94); backdrop-filter: blur(10px);
    box-shadow: var(--shadow-sticky); padding: 11px 20px; }
  .bar .inner { max-width: 900px; margin: 0 auto; display: flex; align-items: center;
    gap: 12px; flex-wrap: wrap; }
  .progress { font-size: 13.5px; color: var(--muted); font-variant-numeric: tabular-nums; }
  .progress b { color: var(--text); }
  .bar .spacer { flex: 1; }
  .saved { font-size: 12.5px; color: var(--accent); opacity: 0; transition: opacity .3s; }
  .saved.show { opacity: 1; }
  .clip { background: var(--bad-soft); color: var(--bad); border: 1px solid #f0cfca;
    border-radius: 12px; padding: 10px 14px; font-size: 13px; margin-bottom: 16px; }

  @media print {
    body { background: #fff; }
    header.hero { background: #fff; color: #000; padding: 0 0 14px; }
    header.hero .eyebrow, header.hero .meta { opacity: 1; }
    header.hero .meta code { background: none; padding: 0; }
    .bar, .choices, .who, dialog { display: none; }
    .card, .panel { box-shadow: none; break-inside: avoid; border: 1px solid #ddd; }
    .wrap { padding-bottom: 0; }
    textarea { min-height: 48px; background: #fff; }
  }
  @media (max-width: 560px) {
    header.hero h1 { font-size: 22px; }
    .card { padding: 17px 16px 16px; }
    .wrap { padding: 0 14px 180px; }
    .choice { flex: 1 1 30%; }
  }
"""


SCRIPT = """
  "use strict";
  var DATA = JSON.parse(document.getElementById("uat-data").textContent);
  var KEY = "pgs-uat:" + DATA.slug;
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  var state = {};

  try { state = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; }
  catch (e) { state = {}; }
  state.results = state.results || {};
  state.me = state.me || {};

  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
      var flag = document.getElementById("saved");
      flag.classList.add("show");
      setTimeout(function () { flag.classList.remove("show"); }, 900);
    } catch (e) {
      // A full or blocked localStorage must not stop a reviewer recording what they saw.
      showClip("This browser will not save progress (" + e.name + "). Export before you close the tab.");
    }
  }

  function showClip(message) {
    var el = document.getElementById("clip");
    el.textContent = message;
    el.hidden = false;
  }

  function result(n) {
    state.results[n] = state.results[n] || {};
    return state.results[n];
  }

  function paint(card) {
    var n = card.getAttribute("data-n");
    var r = result(n);
    var value = r.result || "";
    Array.prototype.forEach.call(card.querySelectorAll(".choice"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-v") === value ? "true" : "false");
    });
    card.querySelector(".reason").hidden = !(value === "FAIL" || value === "N/A");
    var status = card.querySelector(".status");
    if (!value) {
      status.textContent = "Not yet judged";
      status.className = "status";
    } else {
      var who = r.reviewer ? " · " + r.reviewer : "";
      status.textContent = value + who;
      status.className = "status " + (value === "PASS" ? "ok" : "bad");
    }
  }

  function progress() {
    var judged = DATA.scenarios.filter(function (s) {
      return (state.results[s.n] || {}).result;
    }).length;
    document.getElementById("progress").innerHTML =
      "<b>" + judged + "</b> of " + DATA.scenarios.length + " judged";
  }

  function fill(card) {
    var n = card.getAttribute("data-n");
    var r = result(n);
    card.querySelectorAll("[data-k]").forEach(function (el) {
      var key = el.getAttribute("data-k");
      if (key === "status" || key === "evidence-name") return;
      if (key === "evidence") return;
      if (r[key] !== undefined && r[key] !== null) el.value = r[key];
    });
    paint(card);
  }

  cards.forEach(function (card) {
    var n = card.getAttribute("data-n");
    var r = result(n);
    var meta = DATA.scenarios.filter(function (s) { return String(s.n) === n; })[0];
    if (meta && meta.not_applicable && !r.result) {
      r.result = "N/A";
      r.reason = r.reason || meta.na_reason;
    }
    fill(card);

    card.addEventListener("click", function (event) {
      var choice = event.target.closest(".choice");
      if (choice) {
        // A judged result is the reviewer's call. This only records it.
        r.result = choice.getAttribute("data-v");
        if (r.result === "FAIL" || r.result === "N/A") {
          var box = card.querySelector('[data-k="reason"]');
          box.focus();
        }
        paint(card); progress(); save();
        return;
      }
      if (event.target.getAttribute("data-act") === "clear-evidence") {
        r.evidence = null;
        r.evidence_name = "";
        card.querySelector('[data-k="evidence"]').value = "";
        card.querySelector('[data-k="evidence-name"]').textContent = "";
        event.target.hidden = true;
        save();
      }
    });

    card.addEventListener("input", function (event) {
      var key = event.target.getAttribute("data-k");
      if (!key || key === "evidence" || key === "status" || key === "evidence-name") return;
      r[key] = event.target.value;
      save();
      if (key === "reviewer") paint(card);
    });

    card.addEventListener("change", function (event) {
      if (event.target.getAttribute("data-k") !== "evidence") return;
      var file = event.target.files && event.target.files[0];
      var clear = card.querySelector('[data-act="clear-evidence"]');
      var name = card.querySelector('[data-k="evidence-name"]');
      if (!file) { r.evidence = null; clear.hidden = true; name.textContent = ""; save(); return; }
      if (file.size > 4 * 1024 * 1024) {
        showClip("That image is over 4 MB. The sign-off file has to stay sendable by email.");
        event.target.value = "";
        return;
      }
      var reader = new FileReader();
      reader.onload = function () {
        r.evidence = reader.result;
        r.evidence_name = file.name;
        name.textContent = file.name;
        clear.hidden = false;
        save();
      };
      reader.onerror = function () { showClip("That file could not be read."); };
      reader.readAsDataURL(file);
    });
  });

  ["reviewer", "role", "date"].forEach(function (key) {
    var el = document.querySelector('#me-' + (key === "reviewer" ? "name" : key));
    if (!el) return;
    if (state.me[key]) el.value = state.me[key];
    el.addEventListener("input", function () {
      state.me[key] = el.value;
      save();
    });
  });

  document.getElementById("applyAll").addEventListener("click", function () {
    cards.forEach(function (card) {
      var n = card.getAttribute("data-n");
      var r = result(n);
      ["reviewer", "role", "date"].forEach(function (key) {
        if (state.me[key]) {
          r[key] = state.me[key];
          card.querySelector('[data-k="' + key + '"]').value = state.me[key];
        }
      });
      paint(card);
    });
    save();
  });

  document.getElementById("printBtn").addEventListener("click", function () { window.print(); });

  document.getElementById("clearBtn").addEventListener("click", function () {
    if (!window.confirm("Clear every judgement on this page? This cannot be undone.")) return;
    state = { results: {}, me: {} };
    try { localStorage.removeItem(KEY); } catch (e) {}
    window.location.reload();
  });

  document.getElementById("exportBtn").addEventListener("click", function () {
    var problems = [];
    DATA.scenarios.forEach(function (s) {
      var r = state.results[s.n] || {};
      if (!r.result) { problems.push("Scenario " + s.n + " has no result."); return; }
      if ((r.result === "FAIL" || r.result === "N/A") && !(r.reason || "").trim()) {
        problems.push("Scenario " + s.n + " is " + r.result + " but has no reason.");
      }
      if (!(r.reviewer || "").trim()) { problems.push("Scenario " + s.n + " has no reviewer name."); }
      if (!(r.date || "").trim()) { problems.push("Scenario " + s.n + " has no date."); }
    });
    if (problems.length) {
      showClip("Before exporting: " + problems.slice(0, 4).join(" ") +
               (problems.length > 4 ? " (and " + (problems.length - 4) + " more)" : ""));
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    document.getElementById("clip").hidden = true;

    var byName = {};
    DATA.scenarios.forEach(function (s) {
      var r = state.results[s.n];
      var seat = (r.reviewer || "").trim() + "|" + (r.role || "");
      byName[seat] = (byName[seat] || 0) + 1;
    });

    var out = {
      kind: "pgs-uat-signoff", version: 1,
      file: DATA.file, slug: DATA.slug, title: DATA.title,
      environment: DATA.environment,
      results: DATA.scenarios.map(function (s) {
        var r = state.results[s.n];
        return {
          number: s.n, title: s.title,
          result: r.result,
          reason: (r.reason || "").trim(),
          note: (r.note || "").trim(),
          reviewer: (r.reviewer || "").trim(),
          role: r.role || "",
          date: r.date || "",
          evidence: r.evidence || null,
          evidence_name: r.evidence_name || ""
        };
      })
    };

    var text = JSON.stringify(out, null, 2);
    var blob = new Blob([text], { type: "application/json" });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "uat-" + DATA.slug + "-signoff.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
  });

  progress();
"""


# --------------------------------------------------------------------- the shell


def page(
    *,
    title: str,
    slug: str,
    source_name: str,
    header: str,
    counts: str,
    meta: str,
    preflight_html: str,
    setup_html: str,
    cards: str,
    payload: str,
) -> str:
    """Assemble the whole document from already-rendered parts. Pure."""
    return PAGE.format(
        slug=slug,
        source_name=source_name,
        title=title,
        header=header,
        counts=counts,
        meta=meta,
        preflight_html=preflight_html,
        setup_html=setup_html,
        cards=cards,
        payload=payload,
        style=STYLE,
        script=SCRIPT,
    )


PAGE = """<!DOCTYPE html>
<!-- REVIEW ARTIFACT (not a production template) | Outeniqua PGS UAT | {slug}
     Generated by scripts/uat_runner.py from {source_name}.
     Self-contained: no CDN, no build step, no network. Judgements autosave to localStorage. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UAT - {title}</title>
<style>{style}</style>
</head>
<body>

<header class="hero">
  <div class="inner">
    <p class="eyebrow">Outeniqua PGS - user acceptance testing</p>
    <h1>{header}</h1>
    <p>{counts}</p>
    <div class="meta">{meta}</div>
  </div>
</header>

<div class="wrap">

  <div class="panel">
    <h2>How to use this page</h2>
    <p>This page does not check anything. It records <em>your</em> judgement - that is the
       whole point of a UAT item, and why the question comes before the steps.</p>
    <ol>
      <li>Run the preflight below. If a blocking row fails, stop and fix the instance.</li>
      <li>Fill in your name and role once, then use <b>Use these details on every scenario</b>.</li>
      <li>Run each scenario in the app, then choose <b>PASS</b>, <b>FAIL</b> or <b>N/A</b>.
          FAIL and N/A require a reason.</li>
      <li>Press <b>Export sign-off</b> and send the file to whoever writes it back.</li>
    </ol>
    <p class="hint">Everything autosaves in this browser. Nothing is sent anywhere: no
       network request is made by this page.</p>
  </div>

  <div class="panel">
    <h2>Preflight - is the instance ready?</h2>
    <p>Observed against expected. To run a setup command or re-check, use the staff console at
       <code>/uat/</code> on this instance - it has them as buttons, so nothing here has to be
       copied. This panel is the snapshot taken when the page was built.</p>
    {preflight_html}
  </div>

  <div class="panel">
    <h2>Your details</h2>
    <p>One seat per signature. The product owner may co-sign.</p>
    <div class="who-row">
      <div style="flex:2 1 200px"><label for="me-name">Name</label>
        <input type="text" id="me-name" data-k="reviewer" autocomplete="name" placeholder="Full name"></div>
      <div style="flex:1 1 170px"><label for="me-role">Role</label>
        <select id="me-role" data-k="role"><option value="">Role...</option>
          <option>Product</option><option>PGS administrator</option>
          <option>Committee reviewer</option><option>Consumer member</option></select></div>
      <div style="flex:1 1 150px"><label for="me-date">Date</label>
        <input type="date" id="me-date" data-k="date"></div>
      <div><button type="button" class="tiny" id="applyAll">Use these details on every scenario</button></div>
    </div>
  </div>

  <div class="panel">
    <h2>Pre-test setup</h2>
    {setup_html}
  </div>

  <div id="clip" class="clip" hidden></div>

  {cards}

</div>

<div class="bar">
  <div class="inner">
    <span class="progress" id="progress"></span>
    <span class="saved" id="saved">Saved</span>
    <span class="spacer"></span>
    <button class="ghost tiny" id="printBtn">Print</button>
    <button class="ghost tiny" id="clearBtn">Start over</button>
    <button class="primary" id="exportBtn">Export sign-off</button>
  </div>
</div>

<script type="application/json" id="uat-data">
{payload}
</script>
<script>
(function () {{
{script}
}})();
</script>
</body>
</html>
"""
