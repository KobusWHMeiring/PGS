"""The verification surface's markup: the page image, the grid, and one verdict card per claim.

One shape per section, and inside it the two things a judgement needs — **the paper** (a committed
render of the page, hash-pinned to the PDF) and **what the key says it prints** (the header, the row
count, the row pages, any dividers, and each asserted cell in its place). The grid draws every cell
the key does *not* assert as `—`, because the difference between "the key says this" and "the key says
nothing here" is the whole finding: those eight pages print about sixty cells and the key asserts
41 of them.

Everything here is server-rendered, so the page is complete with JavaScript off — the script in
`scripts/shape_review_template.py` only adds state. `build_html()` is the single entry point;
`scripts/shape_review.py` writes it, and `tests/tools/test_shape_review.py` regenerates it to prove the
committed artefact has not been hand-edited.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from knowledge.tests import shape_pages
from knowledge.tests.shape_fixtures import SHAPES, Cell, ShapeCase
from scripts.shape_claims import all_claims, claims
from scripts.shape_review_template import CSS, SCRIPT

REPO_ROOT = Path(__file__).resolve().parents[1]
KEY_FILE = REPO_ROOT / "knowledge/tests/shape_fixtures.py"


def escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def asserted(case: ShapeCase) -> dict[tuple[int, int], Cell]:
    return {(cell.row, cell.column): cell for cell in case.cells}


def cell_display(cell: Cell) -> str:
    """How a claimed cell reads inside the grid — its value, or what kind of claim it is."""
    if cell.empty:
        return "(prints nothing)"
    text = cell.text or cell.starts or cell.contains or cell.ends or ""
    if len(text) > 96:
        return text[:93] + "…"
    return text


def divider_rows(case: ShapeCase) -> dict[int, list[tuple[str, str]]]:
    """Dividers by the body row they sit above, in printed order."""
    grouped: dict[int, list[tuple[str, str]]] = {}
    for row, text, kind in case.dividers:
        grouped.setdefault(row, []).append((text, kind))
    return grouped


def mode_note(case: ShapeCase) -> str:
    return f"read from the committed <code>-{case.mode}</code> text pass"


def shape_header(index: int, case: ShapeCase) -> str:
    printed = case.row_count * len(case.columns)
    pages = ", ".join(str(page) for page in case.pdf_pages)
    printed_pages = ", ".join(str(page) for page in case.printed_pages)
    return f"""
  <header class="shape-head">
    <p class="tag">Shape {index} of {len(SHAPES)}</p>
    <h2>{escape(case.shape)}</h2>
    <p class="src">
      <strong>{escape(case.doc)}</strong> · PDF page {pages} · printed page {printed_pages} · {mode_note(case)}
    </p>
    <p class="thin">
      The key asserts <strong>{len(case.cells)} of the {printed}</strong> cells on this page, plus the
      header, the row count and which page each row starts on. Cells it does not assert are marked
      <span class="unclaimed-key">not claimed</span> in the grid. That is not a claim that the paper
      is blank: the page prints values there, the key simply does not assert them, so there is
      nothing for you to judge in those cells.
    </p>
  </header>"""


def grid(case: ShapeCase) -> str:
    """The grid the key expects, beside the page — claimed cells filled, the rest marked unclaimed."""
    claimed = asserted(case)
    dividers = divider_rows(case)
    head = "".join(f"<th>{escape(column)}</th>" for column in case.columns)
    body: list[str] = []
    for row in range(case.row_count):
        for text, kind in dividers.get(row, ()):
            body.append(
                f'<tr class="divider"><th class="gutter"></th>'
                f'<td colspan="{len(case.columns)}"><span class="kind">{escape(kind)}</span> '
                f"{escape(text)}</td></tr>"
            )
        page = case.row_pages[row] if row < len(case.row_pages) else ""
        cells = []
        for column in range(len(case.columns)):
            cell = claimed.get((row, column))
            if cell is None:
                cells.append(
                    '<td class="unclaimed" title="the key asserts nothing here — '
                    'not that the paper is blank">not claimed</td>'
                )
            elif cell.empty:
                cells.append('<td class="claimed empty">(prints nothing)</td>')
            else:
                cells.append(f'<td class="claimed">{escape(cell_display(cell))}</td>')
        body.append(
            f'<tr><th class="gutter"><span class="rn">{row + 1}</span>'
            f'<span class="pg">{("p" + str(page)) if page else ""}</span></th>'
            + "".join(cells)
            + "</tr>"
        )
    return f"""
    <div class="grid-wrap">
      <table class="expect">
        <thead><tr><th class="gutter"><span class="rn">row</span><span class="pg">page</span></th>{head}</tr></thead>
        <tbody>{''.join(body)}</tbody>
      </table>
    </div>"""


def claim_cards(case: ShapeCase) -> str:
    items = []
    for claim in claims(case):
        items.append(
            f"""
        <fieldset class="claim" data-claim="{escape(claim.id)}">
          <legend class="cq">{escape(claim.question)}</legend>
          <p class="ca">{escape(claim.answer)}</p>
          <div class="vrow">
            <label class="v yes"><input type="radio" name="c:{escape(claim.id)}" value="yes"> Yes</label>
            <label class="v no"><input type="radio" name="c:{escape(claim.id)}" value="no"> No</label>
            <label class="v unsure"><input type="radio" name="c:{escape(claim.id)}" value="unsure"> Can’t tell</label>
          </div>
          <textarea class="cnote" data-note="{escape(claim.id)}" rows="2"
            placeholder="What does the paper print instead? (needed for No and Can’t tell)"></textarea>
        </fieldset>"""
        )
    return f"""
    <div class="claims">
      <h3>The key’s claims, one verdict each</h3>
      <div class="claim-list">{''.join(items)}
      </div>
      <label class="page-note">
        <span>Anything else on this page the key gets wrong?</span>
        <textarea data-page="{escape(case.key)}" rows="2"
          placeholder="Not required — but a cell the key does not assert is exactly the kind of thing this page exists to find."></textarea>
      </label>
    </div>"""


def page_figure(case: ShapeCase, page: int) -> str:
    """One page of the shape, at fit width, with a way to see it at 100%."""
    css = shape_pages.css_class(case.doc_key, page)
    label = f"PDF page {page} of {case.doc}, rendered from the committed PDF"
    return f"""
        <figure class="page">
          <div class="shot {css}" role="img" aria-label="{escape(label)}" data-zoom="{css}"></div>
          <figcaption>
            <span>PDF page {page}</span>
            <button type="button" class="ghost zoom" data-zoom="{css}">Open at full size</button>
          </figcaption>
        </figure>"""


def page_css(doc: str, page: int) -> str:
    """One page's image and its shape, so a landscape page is not laid out as an A4 portrait."""
    record = shape_pages.record(doc, page)
    css = shape_pages.css_class(doc, page)
    return (
        f'.{css}{{background-image:url("{shape_pages.data_uri(doc, page)}");'
        f"aspect-ratio:{record['width']}/{record['height']}}}"
        f".{css}.zoomed{{width:{record['width']}px;height:{record['height']}px}}"
    )


def shape(index: int, case: ShapeCase) -> str:
    return f"""
  <section class="shape" id="shape-{escape(case.key)}">
    {shape_header(index, case)}
    <div class="panes">
      <div class="pages">{''.join(page_figure(case, page) for page in case.pdf_pages)}</div>
      <div class="judge">
        <h3>What the key expects this page to read as</h3>
        {grid(case)}
        <p class="legend">
          <span class="claimed-key">filled</span> a cell the key asserts ·
          <span class="unclaimed-key">not claimed</span> <strong>the key makes no assertion about
          that cell — it is not a claim that the paper is blank</strong>, so there is no verdict to
          give · <span class="kind">qualifier</span> a divider between rows
        </p>
        {claim_cards(case)}
      </div>
    </div>
  </section>"""


def pages_needed() -> list[tuple[str, int]]:
    """Every (document, PDF page) a shape names, in registry order, without duplicates."""
    found: list[tuple[str, int]] = []
    for case in SHAPES:
        for page in case.pdf_pages:
            if (case.doc_key, page) not in found:
                found.append((case.doc_key, page))
    return found


def hero() -> str:
    total = len(all_claims())
    cells = sum(1 for claim in all_claims() if claim.kind == "cell")
    return _HERO.format(total=total, cells=cells, shapes=len(SHAPES))


def toc() -> str:
    """A jump list with a per-shape progress badge, so a long review can be resumed."""
    items = "".join(
        f'<button type="button" class="toc-item" data-goto="shape-{escape(case.key)}">'
        f'<span class="n">{index}</span>'
        f'<span class="nm">{escape(case.shape)}</span>'
        f'<span class="sprog" data-progress="{escape(case.key)}"></span></button>'
        for index, case in enumerate(SHAPES, start=1)
    )
    return f'<nav class="toc" id="toc">{items}</nav>'


def payload(artefact: str, kind: str, version: int) -> str:
    """The claims, embedded verbatim so an export can be validated against what was on the page."""
    return json.dumps(
        {
            "kind": kind,
            "version": version,
            "artefact": artefact,
            "key": "knowledge/tests/shape_fixtures.py",
            "key_sha256": hashlib.sha256(KEY_FILE.read_bytes()).hexdigest(),
            "shapes": [
                {
                    "key": case.key,
                    "shape": case.shape,
                    "doc": case.doc,
                    "pdf_pages": list(case.pdf_pages),
                    "claims": [
                        {
                            "id": claim.id,
                            "kind": claim.kind,
                            "question": claim.question,
                            "expected": claim.expected,
                        }
                        for claim in claims(case)
                    ],
                }
                for case in SHAPES
            ],
        },
        indent=2,
    ).replace("</", "<\\/")


def build_html(artefact: str, kind: str, version: int) -> str:
    pages_css = "\n".join(page_css(doc, page) for doc, page in pages_needed())
    shapes_html = "".join(shape(index, case) for index, case in enumerate(SHAPES, start=1))
    return (
        _HTML_HEAD
        + f"\n<style>\n{CSS}\n{pages_css}\n</style>\n</head>\n<body>\n"
        + hero()
        + '<div class="wrap">'
        + toc()
        + shapes_html
        + "\n"
        + _TAIL.replace("__PAYLOAD__", payload(artefact, kind, version))
        + "\n<script>\n"
        + SCRIPT
        + "\n</script>\n</body>\n</html>\n"
    )


_HTML_HEAD = """<!DOCTYPE html>
<!-- GENERATED FILE — do not hand-edit. `python scripts/shape_review.py` rebuilds it.
     REVIEW SURFACE (not a production template) | Outeniqua PGS — D83, the eight-shape answer key
     Companion to INGESTION_ENGINE_PRD.md §3.10 and PGS_PLATFORM_SPEC.md §18.3 D83.
     Self-contained on purpose: no CDN, no font, no build, no network request. The page images are
     `data:` URIs from knowledge/tests/fixtures/shape_pages/, hash-pinned to the committed PDFs. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Outeniqua PGS — Is the eight-shape answer key right? (D83)</title>"""

_HERO = """<header class="hero">
  <div class="inner">
    <p class="eyebrow">D83 · the gate before any extractor decision</p>
    <h1>Is the answer key right?</h1>
    <p class="q">Eight pages of the OPP and the SAOSO standard, each beside the grid our key says
      they print. One verdict per claim. Nothing here is scored — your call <em>is</em> the key.</p>
    <p class="meta">
      <span><strong>{shapes}</strong> shapes</span>
      <span><strong>{total}</strong> claims</span>
      <span><strong>{cells}</strong> of them cells</span>
      <span>No network · autosaves on this device</span>
    </p>
  </div>
</header>

<section class="card why">
    <h2>Why you are being asked</h2>
    <p class="lede">The key that scores every extractor arm was written by an agent
      (<code>knowledge/tests/shape_fixtures.py</code>, commit <code>5c45550</code>). Characters are
      already checked: every cell is proved to be a contiguous run of the committed page text. What
      is <strong>not</strong> checked is the grouping — whether the paper's bare row numbers are a
      column, whether <code>Proud member of</code> belongs in column 3, whether <code>Step 3</code>
      sits inside the 1,112-character cell, and how Appendix 6a's four printed header lines become
      two labels.</p>
    <p>Three independent readers (Docling, a vision model, Google's Document AI) disagree with the
      key on the same three or four shapes. That is either three tools failing or one unreviewed
      key — this page is how we find out which. The signed landscape UAT judged how the tables
      <em>read</em>; it never asked whether a cell's characters are what the paper prints.</p>
    <div class="callout">
      <span class="label">How to judge</span>
      <p>Open the page — the <em>Open at full size</em> button gives you the page at 100% so small
      print is legible. For each claim, answer <strong>Yes</strong> if the paper prints that,
      <strong>No</strong> if it does not (say what it prints instead), and
      <strong>Can’t tell</strong> if the scan is genuinely unreadable. Nothing is pre-filled and
      nothing is marked for you.</p>
    </div>
    <p class="hint">Your answers autosave in this browser. When every claim has a verdict, name,
      seat and date, the export button downloads one JSON file —
      <code>python scripts/shape_review_signoff.py --from &lt;that file&gt; --dry-run</code> turns it
      into a review of record, and every later change to the key is checked against it.</p>
  </section>
"""

_TAIL = """  <div class="card sign">
    <h2>Who is judging</h2>
    <div class="who">
      <label><span>Name</span><input id="rv-name" autocomplete="off" placeholder="Kobus Meiring"></label>
      <label><span>Seat</span><input id="rv-seat" autocomplete="off" placeholder="Product owner"></label>
      <label><span>Date</span><input id="rv-date" type="date"></label>
    </div>
    <p class="hint">One seat per signature. This is recorded next to the claims it judged, so a
      later reader can tell who called a grouping and when.</p>
  </div>
</div>

<div class="bar">
  <div class="inner">
    <span class="progress" id="progress"></span>
    <span class="spacer"></span>
    <span class="saved" id="saved">Saved</span>
    <button type="button" class="ghost" id="clear">Clear</button>
    <button type="button" class="primary" id="export">Export the review</button>
  </div>
</div>

<dialog id="zoomDlg">
  <div class="dlg-head">
    <h3>Page at 100%</h3>
    <p>Scroll to read. <span id="zoomWhich"></span></p>
  </div>
  <div class="zoom-wrap"><div class="shot zoomed" id="zoomShot"></div></div>
  <div class="dlg-foot">
    <button type="button" class="ghost" id="zoomClose">Close</button>
  </div>
</dialog>

<dialog id="outDlg">
  <div class="dlg-head">
    <h3>Your review</h3>
    <p id="outLead">Hand this file to the developer. Nothing leaves your machine unless you do.</p>
  </div>
  <div class="dlg-body">
    <ul class="problems" id="outProblems"></ul>
    <textarea id="outText" readonly hidden></textarea>
  </div>
  <div class="dlg-foot">
    <button type="button" class="primary" id="dlgDl" hidden>Download JSON</button>
    <button type="button" id="dlgCopy" hidden>Copy JSON</button>
    <button type="button" class="ghost" id="dlgClose">Close</button>
  </div>
</dialog>

<script type="application/json" id="shape-data">__PAYLOAD__</script>"""
