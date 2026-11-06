"""Build the public site's copy deck: every string a visitor reads, in reading order.

    python scripts/copy_deck.py                    # write product/design/COPY_DECK.md
    python scripts/copy_deck.py --check            # report drift only, no write
    python scripts/copy_deck.py --apply --dry-run  # show the diff, write nothing
    python scripts/copy_deck.py --apply            # write the deck's `new:` blocks back

**Why a deck, and why this format.** The deck exists to be handed to a writing pass (a
human, or a model told to rewrite and not to add facts) and to come back unambiguously.
Markdown prose is what a writer reads; JSON is what a program reads. So each row is:

    ### WHY-JOIN-004 - p.element-card__body
    `core/templates/public/sections/_why_join.html` line 29 - mode: `auto`

    old: |
      The committee records one of four outcomes against the SAOSO standard. ...

    new: |
      (left blank for the rewrite)

`old:` is the string as the file holds it today. A writer never edits it: it is the
staleness guard, and `--apply` refuses any row whose `old:` no longer matches the source.
`new:` is the only thing a rewrite touches, and a blank `new:` means "unchanged".

**How `--apply` writes.** It replaces the *exact source region* the run occupies and
nothing else - the `<p class="...">` before it and the `</p>` after it are not touched. So
indentation, attributes and surrounding markup survive a rewrite by construction. When one
file needs several rewrites they are spliced back to front, so offsets cannot drift.

**Three modes, because not every string is safe to rewrite.**

* `auto` - one contiguous run of plain text. Rewritable in place.
* `manual` - the run contains inline markup (`<strong>`, `<a>`) or a `{{ }}` expression, so
  a plain-text replacement would eat it. `--apply` skips these; edit the file by hand.
* `locked` - a citation chip (`OPP §3.3`), a step label, or a fee-table cell. These are
  facts, not prose. Rewriting one would break the claim it cites.

**What this tool does not decide.** Nothing here judges whether a sentence is *true* - only
whether it sounds like a person wrote it. `core/tests/test_claim_discipline.py` still guards
the seven forbidden claims and the membership-is-not-certification sentence, and a rewrite
must keep every `OPP §x` cite honest. The brief that says so is
`product/design/COPY_VOICE.md`; paste it above the deck when you hand it over.

**This tool edits source files, so it proves it did not break them.** After splicing a file,
`--apply` re-extracts the candidate and compares it row by row: the strings you edited must
read as your new text, every other string on the page must be unchanged, and the page must
still have the same number of strings. A failure is reported and the file is not written.
`python scripts/copy_deck_selftest.py` exercises those properties on a throwaway copy.

**Reading order is a hand-written list, not a filesystem walk**, because the deck's first job
is to be read straight through. A template the list does not cover is reported as a gap, so
copy can never go missing quietly. A partial included by two pages appears once, with
`also:` naming the other page - it is one string, and editing it twice is how two pages
drift apart.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# `python scripts/copy_deck.py` puts `scripts/` on sys.path, not the repo root, so the sibling
# import below needs the root adding explicitly.
sys.path.insert(0, str(ROOT))

from scripts.copy_deck_extract import (  # noqa: E402  (see the sys.path insert above)
    NL,
    Row,
    _unescape,
    template_rows_from,
)
PUBLIC = Path("core/templates/public")
PUBLIC_PY = Path("core/services/_public.py")
DECK = Path("product/design/COPY_DECK.md")

#: Reading order, not file order. The same partial may appear in several groups; the deck
#: shows it once and names the other pages in `also:`.
GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Chrome", ("_header.html", "_footer.html")),
    ("Home", (
        "home.html",
        "sections/_hero.html",
        "sections/_key_facts.html",
        "sections/_why_join.html",
        "sections/_element_cards.html",
        "sections/_steps.html",
        "sections/_recognition.html",
        "sections/_chat_windows.html",
        "sections/_doc_rows.html",
        "sections/_disclaimer.html",
    )),
    ("Organics", ("organics.html",)),
    ("How it works", ("how_it_works.html", "sections/_steps.html")),
    # A8's public self-check. It carries no nav entry of its own - the home hero links it - but
    # it is a page a visitor reads, so it belongs in the deck. Its absence was why every run
    # printed "1 template(s) outside the deck".
    ("Before you apply", ("before_you_apply.html",)),
    ("Members", ("members.html",)),
    ("Documents", ("documents.html", "sections/_doc_rows.html")),
    ("Become a member", (
        "become_a_member.html",
        "sections/_why_join.html",
        "sections/_fee_panel.html",
        "sections/_fee_tables.html",
        "sections/_steps.html",
    )),
    ("Contact", ("contact.html",)),
    ("Building in the open", ("building.html",)),
    ("Document reader (demo surface)", (
        "document_reader.html",
        "_page_head.html",
        "_reader_process.html",
        "_passage_blocks.html",
        "_segment.html",
    )),
)

# Extraction - template text to rows with exact source spans - is
# `scripts/copy_deck_extract.py`, split out on 2026-11-06 because a source file may not exceed
# 30 KB (build_principles.md II) and this one was 32 KB. Everything below reads the tree,
# writes it, or decides.

def template_rows(rel: str) -> list[Row]:
    path = PUBLIC / rel
    return template_rows_from((ROOT / path).read_text(encoding="utf-8"),
                              str(path).replace("\\", "/"))


def pages_rows() -> list[Row]:
    """Every string inside a `Page(...)` in PAGES, one row per field."""
    src = (ROOT / PUBLIC_PY).read_text(encoding="utf-8")
    tree = ast.parse(src)
    target = None
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "PAGES":
            target = node
    if target is None or not isinstance(target.value, ast.Dict):
        raise SystemExit("copy_deck: PAGES dict not found in _public.py")

    rows: list[Row] = []
    for v in target.value.values:
        if not isinstance(v, ast.Call):
            continue
        page_key = ""
        for kw in v.keywords:
            if kw.arg == "key" and isinstance(kw.value, ast.Constant):
                page_key = str(kw.value.value)
        for kw in v.keywords:
            if kw.arg in (None, "key") or not isinstance(kw.value, ast.Constant):
                continue
            if not isinstance(kw.value.value, str):
                continue
            rows.append(Row(
                source=str(PUBLIC_PY).replace("\\", "/"),
                label=f"pages[{page_key}].{kw.arg}",
                lines=(kw.lineno, kw.value.end_lineno or kw.value.lineno),
                cols=(0, 0),
                mode="auto",
                text=kw.value.value,
                py_field=kw.arg,
            ))
    return rows


# ------------------------------------------------------------------------ assembly


def _file_order() -> list[str]:
    seen: list[str] = []
    for _, files in GROUPS:
        for f in files:
            if f not in seen:
                seen.append(f)
    return seen


def coverage_gap() -> list[str]:
    listed = set(_file_order())
    on_disk = {
        str(p.relative_to(PUBLIC)).replace("\\", "/")
        for p in PUBLIC.rglob("*.html")
        if p.name != "base.html"
    }
    return sorted(on_disk - listed)


def build() -> list[Row]:
    rows: list[Row] = []

    for r in pages_rows():
        r.group = "Page metadata"
        rows.append(r)

    seen: dict[tuple[str, int, int], Row] = {}
    for group, files in GROUPS:
        for rel in files:
            for r in template_rows(rel):
                k = (r.source, r.lines[0], r.cols[0])
                if k in seen:
                    if group != seen[k].group:
                        seen[k].also.append(group)
                    continue
                r.group = group
                seen[k] = r
                rows.append(r)
    return rows


def assign_ids(rows: list[Row]) -> None:
    """IDs are per source file, in file order, so a partial has one ID wherever it appears."""
    counts: dict[str, int] = {}
    for r in rows:
        if r.source.endswith(".py"):
            stem = "PAGES"
        else:
            stem = Path(r.source).stem.lstrip("_").upper().replace("_", "-")
        counts[r.source] = counts.get(r.source, 0) + 1
        r.id = f"{stem}-{counts[r.source]:03d}"


# ------------------------------------------------------------------------ deck I/O


def render(rows: list[Row], previous: dict[str, tuple[str, str]]) -> str:
    words = sum(len(re.findall(r"[A-Za-z'\u2019]+", r.text)) for r in rows)
    count = {m: sum(1 for r in rows if r.mode == m) for m in ("auto", "manual", "locked")}

    out = [
        "# Copy deck - Outeniqua PGS public site",
        "",
        "**Generated. Do not hand-edit anything except the `new:` blocks.**",
        "Regenerate with `python scripts/copy_deck.py`; apply with",
        "`python scripts/copy_deck.py --apply --dry-run`, then `--apply`.",
        "",
        "Paste `product/design/COPY_VOICE.md` above this file when you hand it to a writing",
        "pass. The one rule that outranks every other rule: **rewrite, never add a fact.** No",
        "new anecdotes, no new colour about land or produce, and every sentence carrying an",
        "`OPP` cite must still be true of that section after the rewrite.",
        "",
        "| | |",
        "|---|---|",
        f"| strings | {len(rows)} |",
        f"| words | {words} |",
        f"| `auto` - rewrite in place | {count['auto']} |",
        f"| `manual` - inline markup or `{{{{ }}}}`; edit by hand | {count['manual']} |",
        f"| `locked` - cites, labels, fee data; facts, not prose | {count['locked']} |",
        "",
        "Set `new:` to the rewritten string, or leave it blank to keep the current one. To",
        "cut a string write `new: -`; `--apply` reports it instead of deleting it, because a",
        "removed sentence usually needs its container removed too, which is a human call.",
        "",
        "`old:` is the guard, not an instruction. `--apply` refuses any row whose `old:` no",
        "longer matches the file, so a deck that went stale while another session edited a",
        "template fails loudly instead of writing over someone's work.",
        "",
        "---",
        "",
    ]

    group = None
    for r in rows:
        if r.group != group:
            group = r.group
            out.append(f"\n## {group}\n")
        span = (f"line {r.lines[0]}" if r.lines[0] == r.lines[1]
                else f"lines {r.lines[0]}-{r.lines[1]}")
        out.append(f"### {r.id} - {r.label}")
        out.append(f"`{r.source}` {span} - mode: `{r.mode}`"
                   + (f" - {r.note}" if r.note else ""))
        if r.also:
            out.append(f"also included by: {', '.join(r.also)}")
        out.append("")
        out.append("old: |")
        for line in textwrap.wrap(r.text, 88, break_long_words=False,
                                  break_on_hyphens=False) or [""]:
            out.append(f"  {line}")
        out.append("")
        out.append("new: |")
        prev = previous.get(r.id, ("", ""))[1].strip()
        # a rewrite that already landed is not a rewrite waiting to apply
        if re.sub(r"\s+", " ", prev) == re.sub(r"\s+", " ", r.text):
            prev = ""
        for line in (textwrap.wrap(prev, 88, break_long_words=False,
                                    break_on_hyphens=False) if prev else []):
            out.append(f"  {line}")
        out.append("")
    return "\n".join(out) + "\n"


def parse_deck(text: str) -> dict[str, tuple[str, str]]:
    """id -> (old, new), so a regenerate never loses a rewrite already written."""
    found: dict[str, tuple[str, str]] = {}
    current: str | None = None
    which: str | None = None
    buf: list[str] = []

    def close() -> None:
        if current and which in ("old", "new"):
            old, new = found.get(current, ("", ""))
            body = " ".join(x.strip() for x in buf).strip()
            found[current] = (body, new) if which == "old" else (old, body)

    for line in text.splitlines():
        if m := re.match(r"^### ([A-Z0-9-]+) ", line):
            close()
            buf, which, current = [], None, m.group(1)
            found.setdefault(current, ("", ""))
            continue
        if line.startswith("## "):
            close()
            buf, which, current = [], None, None
            continue
        if m := re.match(r"^(old|new): \|\s*$", line):
            close()
            buf, which = [], m.group(1)
            continue
        if which:
            buf.append(line)
    close()
    return found


# ------------------------------------------------------------------------ apply


def _escape_html(text: str) -> str:
    out, i = [], 0
    while i < len(text):
        m = re.compile(r"&(?:amp|lt|gt|quot|#\d+|#x[0-9a-fA-F]+|nbsp|mdash|ndash|rsquo|lsquo"
                       r"|ldquo|rdquo);").match(text, i)
        if text[i] == "&":
            out.append(m.group(0) if m else "&amp;")
            i += len(m.group(0)) if m else 1
            continue
        out.append({"<": "&lt;", ">": "&gt;"}.get(text[i], text[i]))
        i += 1
    return "".join(out)


def _escape_python(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _py_replacement(row: Row, lines: list[str], new: str) -> tuple[int, int, str]:
    """Swap one `Page(...)` field. Returns (start_line, end_line_inclusive, text)."""
    start, end = row.lines
    indent = len(lines[start - 1]) - len(lines[start - 1].lstrip())
    pad = " " * indent
    one_line = f'{pad}{row.py_field}="{_escape_python(new)}",'
    if start == end and len(one_line) <= 96:
        return start, end, one_line + "\n"

    inner = " " * (indent + 4)
    chunks = textwrap.wrap(new, 88 - indent - 4, break_long_words=False,
                           break_on_hyphens=False) or [new]
    body = [f'{inner}"{_escape_python(c)}{" " if i < len(chunks) - 1 else ""}"'
            for i, c in enumerate(chunks)]
    block = [f"{pad}{row.py_field}=(", *body, f"{pad}),"]
    last = end
    if end + 1 <= len(lines) and lines[end].strip() == "),":
        last = end + 1
    return start, last, "\n".join(block) + "\n"


def _diff_lines(text: str) -> list[str]:
    """Split for difflib, which needs every line to end in a newline or runs them together."""
    return [ln if ln.endswith(NL) else ln + NL for ln in text.splitlines()]


def apply_deck(rows: list[Row], edits: dict[str, tuple[str, str]], dry_run: bool) -> int:
    """Rewrite the `new:` blocks back into the source.

    Two splice mechanisms, because the sources are two different things. A template row is
    a character region inside a file - replacing exactly that region cannot disturb the
    markup around it. A `PAGES` row is a keyword argument inside a Python expression -
    there the unit is the line span, because the string is written as implicit concatenation
    and wrapping changes how many lines it occupies.
    """
    by_id = {r.id: r for r in rows}
    problems: list[str] = []
    template: dict[str, list[tuple[int, int, str, str]]] = {}
    python: dict[str, list[tuple[int, int, str, str]]] = {}

    for rid, (old, new) in edits.items():
        if not new.strip():
            continue
        row = by_id.get(rid)
        if row is None:
            problems.append(f"{rid}: not in the current tree - the deck is stale, regenerate")
            continue
        if row.mode == "locked":
            problems.append(f"{rid}: locked, not prose: {row.text[:60]!r}")
            continue
        if row.mode == "manual":
            problems.append(f"{rid}: {row.note or 'inline markup'}, edit by hand: "
                            f"{row.text[:60]!r}")
            continue
        if re.sub(r"\s+", " ", old).strip() != re.sub(r"\s+", " ", row.text).strip():
            problems.append(f"{rid}: old: has drifted from the file\n"
                            f"    deck: {old[:88]}\n    file: {row.text[:88]}")
            continue
        if new.strip() == "-":
            problems.append(f"{rid}: marked for cut - remove the container by hand")
            continue

        source = ROOT / row.source
        text = source.read_text(encoding="utf-8")
        if row.py_field:
            lines = text.splitlines(keepends=True)
            lo, hi, block = _py_replacement(row, lines, new.strip())
            python.setdefault(row.source, []).append((lo, hi, block, rid))
        else:
            starts = [0]
            for ln in text.splitlines(keepends=True):
                starts.append(starts[-1] + len(ln))
            a = starts[row.lines[0] - 1] + row.cols[0]
            b = starts[row.lines[1] - 1] + row.cols[1]
            indent = len(text[starts[row.lines[0] - 1]:]) - len(
                text[starts[row.lines[0] - 1]:].lstrip(" 	"))
            wrapped = textwrap.fill(
                _escape_html(new.strip()), 84, subsequent_indent=" " * indent,
                break_long_words=False, break_on_hyphens=False,
            )
            template.setdefault(row.source, []).append((a, b, wrapped, rid))

    changed = 0

    for source, items in template.items():
        path = ROOT / source
        text = original = path.read_text(encoding="utf-8")
        # the new text is written escaped, so compare what a reader would see
        expected = {rid: _unescape(re.sub(r"\s+", " ", new)).strip()
                    for a, b, new, rid in items}
        for a, b, replacement, rid in sorted(items, key=lambda it: it[0], reverse=True):
            seg = text[a:b]
            if dry_run:
                sys.stdout.writelines(difflib.unified_diff(
                    _diff_lines(seg), _diff_lines(replacement),
                    fromfile=f"{source}:{rid}:old", tofile=f"{source}:{rid}:new"))
            text = text[:a] + replacement + text[b:]
            changed += 1

        # Re-extract the candidate and compare row by row. A rewrite may change one
        # string's words; it may not change any other string on the page, and it may not
        # change how many strings the page has. This is what turns an off-by-one offset
        # into a refusal instead of a corrupted template.
        want = [r.text for r in rows if r.source == source]
        got = [r.text for r in template_rows_from(text, source)]
        was = [r.id for r in rows if r.source == source]
        broken: list[str] = []
        if len(got) != len(want):
            broken.append(f"row count {len(want)} -> {len(got)}")
        for i, (w, g) in enumerate(zip(want, got)):
            rid = was[i] if i < len(was) else "?"
            if rid in expected:
                if g != expected[rid]:
                    broken.append(f"{rid} did not land: {g[:70]!r}")
            elif g != w:
                broken.append(f"{rid} collateral: {w[:50]!r} -> {g[:50]!r}")
        if broken:
            problems.extend(f"{source}: {b}" for b in broken)
            changed -= len(items)
            continue
        if not dry_run and text != original:
            path.write_text(text, encoding="utf-8", newline="\n")

    for source, items in python.items():
        path = ROOT / source
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        for lo, hi, block, rid in sorted(items, key=lambda it: it[0], reverse=True):
            if dry_run:
                sys.stdout.writelines(difflib.unified_diff(
                    _diff_lines("".join(lines[lo - 1:hi])), _diff_lines(block),
                    fromfile=f"{source}:{rid}:old", tofile=f"{source}:{rid}:new"))
            lines[lo - 1:hi] = [block]
            changed += 1
        if not dry_run:
            candidate = "".join(lines)
            if candidate != path.read_text(encoding="utf-8"):
                try:
                    ast.parse(candidate)
                except SyntaxError as exc:  # never leave the module unparseable
                    problems.append(f"{source}: rewrite would break the file: {exc}")
                    continue
                path.write_text(candidate, encoding="utf-8", newline="\n")

    for p in problems:
        print(f"  skip  {p}")
    verb = "would rewrite" if dry_run else "rewrote"
    print(f"copy_deck: {verb} {changed} string(s), {len(problems)} skipped")
    return 1 if problems else 0


# ------------------------------------------------------------------------ main


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the deck's new: blocks back")
    ap.add_argument("--dry-run", action="store_true", help="with --apply: print diffs only")
    ap.add_argument("--check", action="store_true", help="report drift and gaps, no write")
    ap.add_argument("--out", default=str(DECK))
    args = ap.parse_args(argv)

    out = ROOT / args.out
    previous = parse_deck(out.read_text(encoding="utf-8")) if out.exists() else {}

    rows = build()
    assign_ids(rows)
    gaps = coverage_gap()
    for g in gaps:
        print(f"copy_deck: template not in GROUPS, its copy is not in the deck: {g}")

    if args.apply:
        return apply_deck(rows, previous, dry_run=args.dry_run)

    if args.check:
        live = {r.id: re.sub(r"\s+", " ", r.text).strip() for r in rows}
        stale = [i for i, (old, _) in previous.items()
                 if i in live and re.sub(r"\s+", " ", old).strip() != live[i]]
        unseen = [r for r in rows if r.id not in previous]
        pending = [i for i, (_, new) in previous.items() if new.strip()]
        print(f"copy_deck: {len(rows)} strings on the site, {len(previous)} in the deck")
        print(f"  {len(unseen)} not yet in the deck, {len(stale)} whose old: has drifted, "
              f"{len(pending)} with a rewrite waiting to apply")
        print(f"  {len(gaps)} template(s) outside the deck")
        return 1 if (unseen or stale or gaps) else 0

    out.write_text(render(rows, previous), encoding="utf-8", newline="\n")
    words = sum(len(re.findall(r"[A-Za-z'\u2019]+", r.text)) for r in rows)
    mode = {m: sum(1 for r in rows if r.mode == m) for m in ("auto", "manual", "locked")}
    print(f"copy_deck: wrote {args.out} - {len(rows)} strings, {words} words")
    print(f"  auto={mode['auto']} manual={mode['manual']} locked={mode['locked']}")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
