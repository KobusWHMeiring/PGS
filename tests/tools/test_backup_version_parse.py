"""`backup.sh`'s version parse, against the banners that actually exist.

The VPS deploy died at step 3/8 with *"no pg_dump matching server major 16 on PATH"* while
`pg_dump 16.15` was on PATH. The cause was `grep -oE`, which prints **every** match: Ubuntu's
banner is `pg_dump (PostgreSQL) 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)`, so the parse produced
four lines (`16`, `16`, `0`, `04`) and the equality test against `"16"` failed. Nothing was
wrong with the box.

`grep -m1` is not the fix either — it stops after one matching *line*, and every match is on
that line. The pipe is `head -n1`.

The test extracts the **shipped** `version_major()` out of `scripts/backup.sh` and feeds it
real banners, so a rewrite that loses `head -n1` fails here. The first version of the script
was broken on every Debian/Ubuntu box and never on the dev box, which uses docker mode and so
never parses a host banner at all (`testing_hazards.md` §2.11).

Two harness traps, both hit while writing this: the script goes in on **stdin** (`bash -s`),
because msys bash resolves neither a backslashed Windows path nor the 8.3 short name
`TemporaryDirectory` hands out; and stdin is fed **bytes**, because `text=True` translates
LF to CRLF on the way in on Windows, which makes bash fail on a trailing carriage return.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP = REPO_ROOT / "scripts" / "backup.sh"

FUNCTION = re.compile(r"^version_major\(\) \{.*?^\}", re.MULTILINE | re.DOTALL)

UBUNTU_PG_DUMP = "pg_dump (PostgreSQL) 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)"


def _major(banner: str) -> str:
    match = FUNCTION.search(BACKUP.read_text(encoding="utf-8"))
    assert match, "version_major() is missing from scripts/backup.sh"
    body = match.group(0) + '\nprintf "%s\\n" "$1" | version_major\n'
    done = subprocess.run(
        ["bash", "-s", "--", banner],
        input=body.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return done.stdout.decode("utf-8", "replace").strip()


def test_the_ubuntu_banner_yields_one_major():
    """Mutation: dropping `head -n1` yields four lines and this fails."""
    assert _major(UBUNTU_PG_DUMP) == "16"


def test_a_plain_banner_yields_its_major():
    assert _major("pg_dump (PostgreSQL) 17.5") == "17"


def test_a_psql_style_banner_yields_its_major():
    assert _major("psql (PostgreSQL) 15.12 (Ubuntu 15.12-0ubuntu0.24.04.1)") == "15"
