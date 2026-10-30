#!/usr/bin/env python3
"""backlog.py — Outeniqua PGS backlog maintainer.

Scans product/backlog/ for PRD .md files, extracts each PRD's `Status:` field,
classifies it into a bucket, and compares it to the directory it lives in.

Modes:
  (default)   dry-run: report drift + suggested moves (no writes)
  --write     regenerate product/backlog/backlog.md (no file moves)
  --apply     move files to match their Status bucket + regenerate index

Rules:
  - The directory is the source of truth; the `Status:` field is advisory.
  - done/on_hold/systems are TERMINAL: their files are never moved, and their
    directory always wins (a Done PRD with stale "Ready" status stays Done).
  - Everywhere else, a `Status:` that implies a different bucket suggests a move.
See product/backlog/CONVENTION.md.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BACKLOG = Path(__file__).resolve().parent / "backlog"
INDEX = BACKLOG / "backlog.md"
TODO = BACKLOG / "todo.md"

# Bucket -> directory name under product/backlog/
BUCKET_DIR = {
    "ready": "ready",
    "refinement": "Refinement",
    "in_progress": "In Progress",
    "on_hold": "on_hold",
    "spike": "spike",
    "bugfix": "BugFixes",
    "done": "Done",
    "system": "systems",
}
DIR_BUCKET = {v: k for k, v in BUCKET_DIR.items()}
DIR_BUCKET_CI = {k.lower(): v for k, v in DIR_BUCKET.items()}

# Terminal buckets: directory is authoritative, never move files out of them.
# spike = research tasks (kept separate), bugfix = kept in place for now.
TERMINAL_DIR_BUCKETS = {"done", "on_hold", "system", "spike", "bugfix"}

# Ordered status rules — first match wins (case-insensitive). Order matters:
# investigation/spike/refinement/draft precede "complete"/"ready" so that
# "Investigation Complete" -> spike and "Draft - Ready for Review" -> refinement.
STATUS_RULES = [
    (r"\binvestigation\b", "spike"),
    (r"\bspike\b", "spike"),
    (r"\bon hold\b", "on_hold"),
    (r"\brefinement\b", "refinement"),
    (r"\bdraft\b", "refinement"),
    (r"\bmaster prd\b", "refinement"),
    (r"\bawaiting\b", "refinement"),
    (r"\bdesign approved\b", "ready"),
    (r"\bdesign validated\b", "ready"),
    (r"\bsuperseded\b", "done"),
    (r"\bresolved\b", "done"),
    (r"\bimplemented\b", "done"),
    (r"\bcomplete\b", "done"),
    (r"\bshipped\b", "done"),
    (r"\bdone\b", "done"),
    (r"\bin progress\b", "in_progress"),
    (r"\bready\b", "ready"),
]

SKIP_NAMES = {"backlog.md", "todo.md", "PRD_TEMPLATE.md", "CONVENTION.md", "README.md"}
SKIP_TOP_DIRS = {"systems"}  # system docs are not backlog items

# --- The public board (`--board-json`) -------------------------------------
#
# Classification only. This mode emits JSON and writes nothing: the *artefact* the public
# page reads is `scripts/board.py`'s job, because a maintainer tool should not know the
# shape of a Django module. Reusing `STATUS_RULES` here rather than writing a second
# status table is the entire reason the seam exists.
#
# A card exists only where a person wrote `**Public:** yes`. The directory then chooses the
# column; it does not choose visibility.
BOARD_COLUMNS: tuple[tuple[str, str], ...] = (
    ("refinement", "In design"),
    ("ready", "Up next"),
    ("in_progress", "Building"),
    ("done", "Shipped"),
)
BOARD_BUCKETS = frozenset(bucket for bucket, _ in BOARD_COLUMNS)

#: A card is one sentence. Past this it is a paragraph, and a column of paragraphs is a
#: document nobody reads (`PUBLIC_BOARD_PRD.md` §4).
SUMMARY_MAX = 180

#: `# PRD: The concordance` is a heading; `The concordance` is a title. Cards print the
#: second. A PRD whose *own* title is internal vocabulary ("MVP 1a — In-Office Visit Flow")
#: carries a `**Public title:**` line instead, and that is the only reason the field exists.
TITLE_PREFIX = re.compile(
    r"^(?:PRD|Implementation Plan|Plan)\s*[:\u2014\u2013-]\s*", re.IGNORECASE
)

BUCKET_LABEL = {
    "ready": "Ready (up next)",
    "in_progress": "In Progress",
    "refinement": "Refinement",
    "on_hold": "On Hold",
    "spike": "Spikes",
    "bugfix": "Bug Fixes",
    "done": "Done",
}


def extract_status(text):
    for line in text.splitlines():
        m = re.search(r"status\s*[:：]\s*(.+)", line, re.IGNORECASE)
        if m:
            return m.group(1).strip().strip("*").strip()
    return None


def classify_status(status):
    if not status:
        return None
    # Ignore backtick-quoted text (e.g. "Superseded by `...Refinement...`" paths).
    s = re.sub(r"`[^`]*`", "", status.lower())
    for pat, bucket in STATUS_RULES:
        if re.search(pat, s):
            return bucket
    return None


def title_of(text, path):
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return path.stem.replace("_", " ").replace("-", " ")


def scan():
    items = []
    for path in sorted(BACKLOG.rglob("*.md")):
        rel = path.relative_to(BACKLOG)
        if path.name in SKIP_NAMES:
            continue
        if rel.parts and rel.parts[0] in SKIP_TOP_DIRS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        status = extract_status(text)
        status_bucket = classify_status(status)
        parts = rel.parts
        if len(parts) == 1:
            dir_bucket = None  # loose file in backlog root
        else:
            dir_bucket = DIR_BUCKET_CI.get(parts[0].lower())
        items.append({
            "path": path,
            "rel": rel,
            "title": title_of(text, path),
            "status": status,
            "status_bucket": status_bucket,
            "dir_bucket": dir_bucket,
            # Kept so `board_payload()` does not re-read 36 files to find a `Summary:` line.
            "text": text,
        })
    return items


def effective_bucket(item):
    db = item["dir_bucket"]
    if db in TERMINAL_DIR_BUCKETS:
        return db  # directory wins for done/on_hold/system
    return item["status_bucket"] or db


def extract_field(text, name):
    """The value of a `**Name:** value` header line, or None. Case-insensitive on the name."""
    pattern = re.compile(
        r"^\*\*" + re.escape(name) + r":\*\*\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE
    )
    match = pattern.search(text)
    return match.group(1) if match else None


def is_public(text):
    """Opted in only by an explicit `**Public:** yes`. Absent is not consent."""
    value = extract_field(text, "Public")
    return bool(value) and value.strip().strip("`*").lower() == "yes"


def public_title(item):
    """The card's title: `**Public title:**` if given, else the `h1` minus its `PRD:` prefix."""
    override = extract_field(item["text"], "Public title")
    if override:
        return override.strip()
    stripped = TITLE_PREFIX.sub("", item["title"]).strip()
    return stripped or item["title"]


def date_of(text):
    """The date a card is ordered by, from the file itself — never from the filesystem.

    A checkout's mtime is the clone time, so a `Done` column ordered by mtime reorders
    itself on every deploy. Falls back to the first ISO date in the header block, which is
    where `**Opened:**` and `Built 2026-10-27` both live.
    """
    for name in ("Last Updated", "Opened", "Opened date"):
        value = extract_field(text, name)
        if value:
            match = re.search(r"\d{4}-\d{2}-\d{2}", value)
            if match:
                return match.group(0)
    match = re.search(r"\d{4}-\d{2}-\d{2}", "\n".join(text.splitlines()[:12]))
    return match.group(0) if match else ""


def board_digest(cards):
    """A fingerprint of the *published* set, so a stale artefact is a loud state.

    Deliberately blind to unpublished PRDs: an internal edit must not force a board
    regeneration, or the artefact churns in every unrelated commit.
    """
    blob = json.dumps(cards, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def board_payload(items=None):
    """The published set as plain JSON-ready data, plus every opt-in that could not be one.

    In:  `items` from `scan()` (or None to scan).
    Out: {version, cards, rejected, digest}. A `rejected` entry is a **mistake to fix**, not
         a state to record: `scripts/board.py` refuses to write an artefact while one exists.
         Dropping such an item silently would make the board look complete while a
         maintained PRD was missing.
    Side effects: none.
    Fails: never — a malformed PRD is reported, not raised, because this runs in tooling.
    """
    items = scan() if items is None else items
    cards, rejected = [], []

    for item in items:
        if not is_public(item["text"]):
            continue
        bucket = effective_bucket(item)
        rel = str(item["rel"]).replace("\\", "/")
        if bucket not in BOARD_BUCKETS:
            columns = ", ".join(sorted(BOARD_BUCKETS))
            rejected.append({
                "rel": rel,
                "reason": (
                    f"no board column for bucket {bucket!r} ({columns} only). Move the file to "
                    f"a directory with a column, or drop its `Public:` line."
                ),
            })
            continue
        summary = (extract_field(item["text"], "Summary") or "").strip()
        if not summary:
            rejected.append({
                "rel": rel,
                "reason": "marked public but has no `**Summary:**` line; a card is a title and one sentence",
            })
            continue
        if len(summary) > SUMMARY_MAX:
            rejected.append({
                "rel": rel,
                "reason": f"summary is {len(summary)} characters; the board allows {SUMMARY_MAX}",
            })
            continue
        cards.append({
            "title": public_title(item),
            "summary": summary,
            "column": bucket,
            "updated": date_of(item["text"]),
            "rel": rel,
        })

    # Deterministic before the generator sorts: two runs over the same tree must produce the
    # same digest, or `--check` fails on a tree nobody touched.
    cards.sort(key=lambda card: (card["column"], card["title"].lower(), card["rel"]))
    rejected.sort(key=lambda entry: entry["rel"])
    return {
        "version": 1,
        "cards": cards,
        "rejected": rejected,
        "digest": board_digest(cards),
    }


def suggest_move(item):
    """Return (src_rel, dst_dir) if the file should move, else None."""
    db = item["dir_bucket"]
    sb = item["status_bucket"]
    if db in TERMINAL_DIR_BUCKETS:
        return None  # done/on_hold/system are authoritative
    if sb is None or sb == db:
        return None
    target = BUCKET_DIR.get(sb)
    if target is None:
        return None
    parts = item["rel"].parts
    # Flatten intermediate "done" subfolders (e.g. health_audit/done/*) into the bucket root.
    if len(parts) > 2 and any(p.lower() == "done" for p in parts[1:-1]):
        dest = Path(target) / item["rel"].name
    # Otherwise preserve sub-directory structure below the top-level dir.
    elif len(parts) > 1:
        dest = Path(target) / Path(*parts[1:])
    else:
        dest = Path(target) / item["rel"].name
    return str(item["rel"]), str(dest)


def stale_status_items(items):
    """Shipped/parked files whose Status field contradicts the directory (informational)."""
    out = []
    for it in items:
        db = it["dir_bucket"]
        sb = it["status_bucket"]
        if db in {"done", "on_hold"} and sb is not None and sb != db:
            out.append(it)
    return out


STATUS_FIX = {"done": "Done", "on_hold": "On Hold"}


def rewrite_status(text, new_status):
    """Replace the value of the first `Status:` line with new_status (preserves prefix + bold markers)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.search(r"status\s*[:：]", line, re.IGNORECASE)
        if m:
            j = m.end()
            # Preserve any '*' and whitespace immediately after the colon (bold markers + spacing).
            while j < len(line) and line[j] in "* \t":
                j += 1
            lines[i] = line[:j] + new_status
            break
    result = "\n".join(lines)
    if text.endswith("\n"):
        result += "\n"
    return result


def fix_statuses(items):
    fixed = 0
    for it in stale_status_items(items):
        new_status = STATUS_FIX.get(it["dir_bucket"])
        if not new_status:
            continue
        try:
            text = it["path"].read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        new_text = rewrite_status(text, new_status)
        if new_text != text:
            it["path"].write_text(new_text, encoding="utf-8", newline="\n")
            print(f"  FIXED: {it['rel']} -> Status: {new_status}")
            fixed += 1
    return fixed


def load_todo():
    if TODO.exists():
        return TODO.read_text(encoding="utf-8", errors="replace")
    return ""


def fmt(it):
    status = it["status"] if it["status"] else "no status"
    return f"- **{it['title']}** - `{it['rel']}` - Status: {status}"


def build_index(items):
    by_bucket = defaultdict(list)
    for it in items:
        by_bucket[effective_bucket(it)].append(it)

    moves = [m for m in (suggest_move(it) for it in items) if m]
    loose = [it for it in items if it["dir_bucket"] is None]
    stale = stale_status_items(items)

    lines = []
    lines.append("# Outeniqua PGS Product Backlog")
    lines.append("")
    lines.append("> **Generated index** - do not edit by hand. Regenerate with `python product/backlog.py --write`.")
    lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    order = ["ready", "in_progress", "refinement", "on_hold", "spike", "bugfix", "done"]
    for bucket in order:
        bucket_items = by_bucket.get(bucket, [])
        if bucket == "done":
            bucket_items = bucket_items[-20:]  # recent only
        lines.append(f"## {BUCKET_LABEL[bucket]}")
        lines.append("")
        if not bucket_items:
            lines.append("_none_")
            lines.append("")
            continue
        for it in bucket_items:
            lines.append(fmt(it))
        lines.append("")

    unknown = [it for it in items if effective_bucket(it) not in order]
    if unknown:
        lines.append("## Other / Unclassified")
        lines.append("")
        for it in unknown:
            lines.append(fmt(it))
        lines.append("")

    todo = load_todo().strip()
    lines.append("## To Do (ideas without a PRD yet)")
    lines.append("")
    lines.append(todo if todo else "_none_")
    lines.append("")

    lines.append("## Drift (suggested moves)")
    lines.append("")
    if not moves:
        lines.append("_none_")
    else:
        for src, dst in moves:
            lines.append(f"- `{src}` -> `{dst}`")
    lines.append("")

    if stale:
        lines.append("## Stale Status metadata (directory wins; update the Status line)")
        lines.append("")
        for it in stale:
            lines.append(f"- `{it['rel']}` (dir: {it['dir_bucket']}, Status: {it['status']})")
        lines.append("")

    if loose:
        lines.append("## Loose files in backlog root")
        lines.append("")
        for it in loose:
            lines.append(fmt(it))
        lines.append("")

    return "\n".join(lines)


def report(items):
    by_bucket = defaultdict(list)
    for it in items:
        by_bucket[effective_bucket(it)].append(it)
    moves = [m for m in (suggest_move(it) for it in items) if m]
    loose = [it for it in items if it["dir_bucket"] is None]
    stale = stale_status_items(items)

    print("=" * 70)
    print("PGS BACKLOG - DRY RUN (no changes written)")
    print(f"Scanned {len(items)} PRD files under product/backlog/")
    print("=" * 70)

    print("\nEffective counts by bucket:")
    order = ["ready", "in_progress", "refinement", "on_hold", "spike", "bugfix", "done"]
    for b in order:
        print(f"  {BUCKET_LABEL[b]:<18} {len(by_bucket.get(b, []))}")
    unknown = [it for it in items if effective_bucket(it) not in order]
    if unknown:
        print(f"  {'unclassified':<18} {len(unknown)}")

    print("\n" + "-" * 70)
    print("READY (up next) - approved to build, not yet shipped:")
    ready = by_bucket.get("ready", [])
    if not ready:
        print("  _none_")
    for it in ready:
        print("  " + fmt(it))

    print("\n" + "-" * 70)
    print(f"DRIFT - {len(moves)} file(s) to move so directory matches Status:")
    if not moves:
        print("  _none_")
    for src, dst in moves:
        print(f"  {src}  ->  {dst}")

    print("\n" + "-" * 70)
    print(f"STALE STATUS - {len(stale)} shipped/parked file(s) with an outdated Status line (directory wins, no move):")
    if not stale:
        print("  _none_")
    for it in stale[:25]:
        print(f"  {it['rel']}  (dir: {it['dir_bucket']}, Status: {it['status']})")
    if len(stale) > 25:
        print(f"  ... and {len(stale) - 25} more")

    print("\n" + "-" * 70)
    print(f"LOOSE files in backlog root ({len(loose)}):")
    if not loose:
        print("  _none_")
    for it in loose:
        print("  " + fmt(it))

    todo = load_todo().strip()
    n_todo = len([l for l in todo.splitlines() if l.strip().startswith("-")]) if todo else 0
    print("\n" + "-" * 70)
    print(f"To Do (todo.md): {n_todo} item(s) preserved into the index's To Do section.")
    print("=" * 70)
    print("Apply moves + regenerate:  python product/backlog.py --apply")
    print("Regenerate index only:    python product/backlog.py --write")


def apply_moves(items):
    moved, skipped = 0, 0
    for it in items:
        m = suggest_move(it)
        if not m:
            continue
        src_rel, dst_rel = m
        src = BACKLOG / src_rel
        dst = BACKLOG / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            print(f"  SKIP (dest exists): {src_rel} -> {dst_rel}")
            skipped += 1
            continue
        src.rename(dst)
        print(f"  MOVED: {src_rel} -> {dst_rel}")
        moved += 1
    return moved, skipped


def main():
    ap = argparse.ArgumentParser(description="Outeniqua PGS backlog maintainer (dry-run by default).")
    ap.add_argument("--write", action="store_true", help="regenerate backlog.md (no moves)")
    ap.add_argument("--apply", action="store_true", help="move files to match status + regenerate index")
    ap.add_argument("--fix-statuses", action="store_true", help="rewrite stale Status lines in Done/ and on_hold/ to match the directory")
    ap.add_argument(
        "--board-json",
        action="store_true",
        help="print the public board's reviewed set as JSON (no writes; see scripts/board.py)",
    )
    args = ap.parse_args()

    if args.board_json:
        json.dump(board_payload(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    items = scan()

    if args.fix_statuses:
        print("Fixing stale Status lines...")
        fixed = fix_statuses(items)
        print(f"Fixed {fixed} status line(s).")
        items = scan()
        INDEX.write_text(build_index(items), encoding="utf-8", newline="\n")
        print(f"Regenerated {INDEX}")
    elif args.apply:
        print("Moving files to match Status buckets...")
        moved, skipped = apply_moves(items)
        print(f"Moved {moved}, skipped {skipped}.")
        items = scan()
        INDEX.write_text(build_index(items), encoding="utf-8", newline="\n")
        print(f"Regenerated {INDEX}")
    elif args.write:
        INDEX.write_text(build_index(items), encoding="utf-8", newline="\n")
        print(f"Regenerated {INDEX}")
    else:
        report(items)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
