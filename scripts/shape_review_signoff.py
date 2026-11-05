#!/usr/bin/env python
"""Turn a reviewer's exported judgement of the eight-shape key into a review of record.

    # the owner opens product/design/uat/shape_key_review.html, judges every claim, exports
    python scripts/shape_review_signoff.py --from ~/Downloads/shape-key-review.json --dry-run
    python scripts/shape_review_signoff.py --from ~/Downloads/shape-key-review.json
    python scripts/shape_review_signoff.py --check        # is the recorded review still true?

**Why a record and not a sentence in a PRD.** `INGESTION_ENGINE_PRD.md` §3.10: the key that scores
every extractor arm is agent-authored and no human has ever validated a cell, so the arms are
ranked against a convention. A signature that lives only in a downloaded JSON file is a signature
the next session cannot check. This writes **one** file — `knowledge/tests/shape_review.json` —
which pins every claim's text as it was when it was judged, so the moment `shape_fixtures.py`
changes under a signed claim, `--check` (and the gate's test) fails and names the claim. A
signature cannot outlive what it signed.

**It refuses rather than guesses.** An unjudged claim, a `No` with no reason, a missing name or
date, an export from a different surface, an export whose claim text no longer matches the key:
each is named and nothing is written. A half-applied review is worse than none, because the record
would then claim judgements nobody made.

**It does not touch the fixtures.** A `No` is evidence; amending the key is a deliberate edit with
its own diff, made after reading the record. This script records the finding, never acts on it.

Re-running the same export changes nothing (idempotent) apart from the `signed_against` commit.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from knowledge.tests.shape_fixtures import SHAPES  # noqa: E402
from scripts.shape_review import (  # noqa: E402
    ARTEFACT_NAME,
    KIND as EXPORT_KIND,
    VERSION as EXPORT_VERSION,
    all_claims,
    claims as case_claims,
)

KIND = "pgs-shape-key-review-record"
VERSION = 1
RECORD_PATH = REPO_ROOT / "knowledge/tests/shape_review.json"
KEY_PATH = REPO_ROOT / "knowledge/tests/shape_fixtures.py"
VALID_VERDICTS = ("yes", "no", "unsure")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def key_sha256() -> str:
    return hashlib.sha256(KEY_PATH.read_bytes()).hexdigest()


def current_claims() -> dict[str, dict]:
    """What the key asserts right now, by claim id — the text a verdict is pinned to."""
    return {
        claim.id: {"kind": claim.kind, "expected": claim.expected}
        for claim in all_claims()
    }


def validate(export: dict) -> list[str]:
    """Everything wrong with an export, named. An empty list is a signature that can be applied."""
    problems: list[str] = []
    if not isinstance(export, dict):
        return ["the export is not a JSON object"]
    if export.get("kind") != EXPORT_KIND:
        problems.append(
            f"this is not a shape-key review export (kind {export.get('kind')!r}, "
            f"expected {EXPORT_KIND!r})"
        )
    if export.get("version") != EXPORT_VERSION:
        problems.append(
            f"export format {export.get('version')!r} is not version {EXPORT_VERSION}"
        )
    if export.get("artefact") != ARTEFACT_NAME:
        problems.append(
            f"the export names {export.get('artefact')!r}, not the review surface "
            f"{ARTEFACT_NAME!r}"
        )

    reviewer = export.get("reviewer") or {}
    for field in ("name", "seat"):
        if not str(reviewer.get(field, "")).strip():
            problems.append(f"the reviewer's {field} is missing")
    if not DATE_RE.match(str(export.get("reviewed_at", ""))):
        problems.append("the review date is missing or not YYYY-MM-DD")

    key = current_claims()
    judged = export.get("claims")
    if not isinstance(judged, dict):
        return problems + ["the export has no claims — export from the review surface"]
    unknown = sorted(set(judged) - set(key))
    missing = sorted(set(key) - set(judged))
    problems.extend(f"{claim} is not a claim this key makes" for claim in unknown)
    problems.extend(f"{claim} is not judged" for claim in missing)

    for claim_id in sorted(set(judged) & set(key)):
        entry = judged[claim_id] or {}
        verdict = entry.get("verdict")
        if verdict not in VALID_VERDICTS:
            problems.append(f"{claim_id}: {verdict!r} is not one of {VALID_VERDICTS}")
        if verdict in ("no", "unsure") and not str(entry.get("note", "")).strip():
            problems.append(f"{claim_id}: a {verdict} needs a reason")
        expected = entry.get("expected")
        if expected != key[claim_id]["expected"]:
            problems.append(
                f"{claim_id}: the page was built when the key said {expected!r}, it now says "
                f"{key[claim_id]['expected']!r} - rebuild the surface and judge it again"
            )

    notes = export.get("page_notes") or {}
    if not isinstance(notes, dict):
        problems.append("page_notes is not an object")
    else:
        for shape_key in sorted(set(notes) - {claim.split(".")[0] for claim in key}):
            problems.append(f"page_notes names an unknown shape {shape_key!r}")
    return problems


def build_record(export: dict) -> dict:
    """The review of record: the export's judgements, pinned to the key text they judged."""
    key = current_claims()
    claims: dict[str, dict] = {}
    amended_claims: list[str] = []
    unsure_claims: list[str] = []
    for claim in all_claims():
        entry = export["claims"][claim.id]
        verdict = entry["verdict"]
        claims[claim.id] = {
            "kind": claim.kind,
            "expected": key[claim.id]["expected"],
            "verdict": verdict,
            "note": str(entry.get("note", "")).strip(),
        }
        if verdict == "no":
            amended_claims.append(claim.id)
        elif verdict == "unsure":
            unsure_claims.append(claim.id)

    page_notes = {
        key_: str(value).strip()
        for key_, value in (export.get("page_notes") or {}).items()
        if str(value).strip()
    }

    # A page note is a finding. A shape whose reviewer wrote "is this expected?" is not
    # "confirmed" even when every claim was answered Yes — the first signature proved why: one
    # note said the paper prints "Step 3" where the key's claim starts after it.
    confirmed: list[str] = []
    amended: list[str] = []
    unsure: list[str] = []
    open_questions: list[str] = []
    for case in SHAPES:
        verdicts = {claims[claim.id]["verdict"] for claim in case_claims(case)}
        if "no" in verdicts:
            amended.append(case.key)
        elif "unsure" in verdicts:
            unsure.append(case.key)
        elif case.key in page_notes:
            open_questions.append(case.key)
        else:
            confirmed.append(case.key)

    return {
        "kind": KIND,
        "version": VERSION,
        "artefact": ARTEFACT_NAME,
        "key": "knowledge/tests/shape_fixtures.py",
        "key_sha256": key_sha256(),
        "reviewed_at": export["reviewed_at"],
        "reviewer": {
            "name": export["reviewer"]["name"].strip(),
            "seat": export["reviewer"]["seat"].strip(),
        },
        "signed_against": {"commit": head_commit()},
        "claims": claims,
        "page_notes": page_notes,
        "summary": {
            "claims": len(claims),
            "yes": sum(1 for c in claims.values() if c["verdict"] == "yes"),
            "no": len(amended_claims),
            "unsure": len(unsure_claims),
            "shapes_confirmed": confirmed,
            "shapes_amended": amended,
            "shapes_unsure": unsure,
            "shapes_with_open_questions": open_questions,
            "amended_claims": amended_claims,
            "unsure_claims": unsure_claims,
        },
    }


def head_commit() -> str:
    """The commit the review was signed on, or '' outside a checkout (a clone of an export)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:  # pragma: no cover - git is not installed
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def drift(record: dict) -> list[str]:
    """Every way a recorded review no longer describes the key it judged."""
    if not isinstance(record, dict) or record.get("kind") != KIND:
        return [f"not a shape-key review record (kind {record.get('kind') if isinstance(record, dict) else record!r})"]
    problems: list[str] = []
    key = current_claims()
    recorded = record.get("claims") or {}
    for claim_id in sorted(set(key) - set(recorded)):
        problems.append(f"{claim_id}: the key makes this claim and the record does not judge it")
    for claim_id in sorted(set(recorded) - set(key)):
        problems.append(f"{claim_id}: the record judges a claim the key no longer makes")
    for claim_id in sorted(set(key) & set(recorded)):
        was = (recorded[claim_id] or {}).get("expected")
        if was != key[claim_id]["expected"]:
            problems.append(
                f"{claim_id}: judged as {was!r}, the key now says {key[claim_id]['expected']!r} "
                "- the review is stale, rebuild the surface and judge it again"
            )
    if not problems and record.get("key_sha256") != key_sha256():
        problems.append(
            "knowledge/tests/shape_fixtures.py changed since the review was signed "
            f"({str(record.get('key_sha256'))[:12]} -> {key_sha256()[:12]}) without changing a "
            "claim's text - a note or a comment moved, so re-read the diff before trusting the "
            "record"
        )
    return problems


def _display(path: Path) -> str:
    """The record's path, short when it is inside the tree and absolute when a test moved it."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def diff(before: str, after: str) -> str:
    name = _display(RECORD_PATH)
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
            n=3,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--from", dest="source", type=Path, help="the exported review JSON")
    parser.add_argument("--dry-run", action="store_true", help="print the diff; write nothing")
    parser.add_argument("--check", action="store_true", help="verify the recorded review")
    args = parser.parse_args(argv)

    if args.check:
        if not RECORD_PATH.exists():
            print(f"no review of record yet ({_display(RECORD_PATH)} is absent)")
            return 0
        record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
        problems = drift(record)
        for problem in problems:
            print(f"STALE {problem}")
        print(f"{len(record.get('claims') or {})} judged claims, {len(problems)} problem(s)")
        return 1 if problems else 0

    if not args.source:
        parser.error("--from <export.json> is required unless --check is given")
    if not args.source.exists():
        print(f"{args.source} does not exist", file=sys.stderr)
        return 2
    export = json.loads(args.source.read_text(encoding="utf-8"))

    problems = validate(export)
    if problems:
        print(f"refused: {len(problems)} problem(s) with this export", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    record = build_record(export)
    after = json.dumps(record, indent=2) + "\n"
    before = RECORD_PATH.read_text(encoding="utf-8") if RECORD_PATH.exists() else ""
    head = record["signed_against"]["commit"] or "(no git)"

    if args.dry_run:
        change = diff(before, after)
        print(change if change else "no change")
        print(
            f"\n{record['summary']['yes']} yes / {record['summary']['no']} no / "
            f"{record['summary']['unsure']} unsure across {record['summary']['claims']} claims, "
            f"signed by {record['reviewer']['name']} on {record['reviewed_at']} ({head})."
        )
        if record["summary"]["amended_claims"]:
            print("\nClaims the owner says the paper contradicts:")
            for claim_id in record["summary"]["amended_claims"]:
                print(f"  - {claim_id}: {record['claims'][claim_id]['note']}")
        return 0

    RECORD_PATH.write_text(after, encoding="utf-8", newline="\n")
    print(
        f"wrote {_display(RECORD_PATH)} - "
        f"{record['summary']['yes']} yes / {record['summary']['no']} no / "
        f"{record['summary']['unsure']} unsure across {record['summary']['claims']} claims"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
