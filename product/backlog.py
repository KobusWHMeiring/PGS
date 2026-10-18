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
        })
    return items


def effective_bucket(item):
    db = item["dir_bucket"]
    if db in TERMINAL_DIR_BUCKETS:
        return db  # directory wins for done/on_hold/system
    return item["status_bucket"] or db


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
            it["path"].write_text(new_text, encoding="utf-8")
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
    args = ap.parse_args()

    items = scan()

    if args.fix_statuses:
        print("Fixing stale Status lines...")
        fixed = fix_statuses(items)
        print(f"Fixed {fixed} status line(s).")
        items = scan()
        INDEX.write_text(build_index(items), encoding="utf-8")
        print(f"Regenerated {INDEX}")
    elif args.apply:
        print("Moving files to match Status buckets...")
        moved, skipped = apply_moves(items)
        print(f"Moved {moved}, skipped {skipped}.")
        items = scan()
        INDEX.write_text(build_index(items), encoding="utf-8")
        print(f"Regenerated {INDEX}")
    elif args.write:
        INDEX.write_text(build_index(items), encoding="utf-8")
        print(f"Regenerated {INDEX}")
    else:
        report(items)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
