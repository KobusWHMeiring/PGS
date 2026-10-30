#!/usr/bin/env bash
#
# verify.sh — the gate. "Is this tree shippable?"
#
# Runs the three checks from MVP0_PLAN_V2.md Task A8, in order, and stops at the
# first failure:
#
#   1. manage.py check        — Django's system checks (config, models, admin)
#   2. lint-imports           — knowledge must never import core (A7)
#   3. pytest                 — the suite, against a real Postgres and Redis
#
# This script is the SINGLE source of truth for "is this good". `deploy.sh` calls
# it on the server before touching the live tree, and a `.github/workflows/ci.yml`
# can call it later without duplicating the steps — so the two can never drift.
#
# Deliberately NOT a CI-only script: it is expected to run on a Windows dev box
# (git bash) as well as the Linux VPS. That divergence is the point — the same
# checks against the real target OS is what GitHub's ubuntu-latest could only
# approximate.
#
# Usage:
#   ./scripts/verify.sh
#   DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh
#
# Exit codes: 0 = shippable, non-zero = not shippable.
#
set -euo pipefail

# --- Locate the interpreter --------------------------------------------------
# The venv differs by platform: Scripts/ on Windows, bin/ elsewhere. Resolve rather
# than assume, or this script silently uses a system Python with no dependencies
# installed — which fails confusingly at the first import.
if [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    PYTHON="python"
fi

# `lint-imports` lives beside the interpreter. It is NOT on PATH when invoked as
# `python -m pytest` (A7, and product/docs/context/testing_hazards.md §2).
BIN_DIR="$(dirname "$PYTHON")"
LINT_IMPORTS="$BIN_DIR/lint-imports"
[ -x "$LINT_IMPORTS" ] || LINT_IMPORTS="$BIN_DIR/lint-imports.exe"
[ -x "$LINT_IMPORTS" ] || LINT_IMPORTS="$(command -v lint-imports || true)"

echo "==> verify.sh"
echo "    python:        $PYTHON"
echo "    lint-imports:  ${LINT_IMPORTS:-<not found>}"

# --- Scripts must be executable ----------------------------------------------
#
# `git archive` — how deploy/deploy.sh materialises the commit it gates — preserves
# the mode recorded in the commit. Three scripts were committed 100644, so the first
# real redeploy died at step 1/8 with `./scripts/verify.sh: Permission denied`, and
# the same defect would have stopped `scripts/backup.sh` at step 3/8 — after the pull,
# before the migration.
#
# This belongs here rather than on the box: a `chmod` on a server cannot fix a mode
# that is not in the commit, and the next archive would be broken again.
#
# Two records, because the gate runs in two places. In a checkout (CI, a dev box) the
# **index** is the authority — and it is the only form of this check that can fail on
# Windows, where msys reports every file as executable. In the `git archive` tree that
# deploy.sh builds there is no `.git`, and the committed mode has become the file's
# mode, so the filesystem is then the same fact.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
missing=""
if [ -d "$REPO_ROOT/.git" ]; then
    # `awk` rather than a bash loop: a path with a space stays one path.
    missing="$(git -C "$REPO_ROOT" ls-files -s -- '*.sh' | awk '$1 != "100755" { print $4 }')"
else
    for script in "$REPO_ROOT"/*.sh "$REPO_ROOT"/scripts/*.sh "$REPO_ROOT"/deploy/*.sh; do
        [ -e "$script" ] || continue
        if [ ! -x "$script" ]; then
            missing="${missing}${script#"$REPO_ROOT"/}"$'\n'
        fi
    done
fi
if [ -n "$missing" ]; then
    {
        echo ""
        echo "ERROR: these scripts are not executable in the commit:"
        printf '  %s\n' $missing
        echo "  Fix the index, not just the disk:"
        echo "    git update-index --chmod=+x <path>"
        echo "  Their sibling scripts run them directly, and git archive keeps 644."
    } >&2
    exit 2
fi

# --- Preconditions -----------------------------------------------------------

# A2 makes a missing SECRET_KEY an error on purpose. Say so here rather than
# letting Django raise a traceback 200 lines into the run.
if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
    echo ""
    echo "ERROR: DJANGO_SECRET_KEY is not set." >&2
    echo "  PGS settings deliberately have no default key: a shared or committed" >&2
    echo "  key is a vulnerability no test can see." >&2
    echo "  Set it for this run only, e.g.:" >&2
    echo "    export DJANGO_SECRET_KEY=\$(\"\$PYTHON\" -c 'from django.core.management.utils import get_random_secret_key as k; print(k())')" >&2
    echo "    ./scripts/verify.sh" >&2
    exit 2
fi

if [ -z "${LINT_IMPORTS:-}" ] || [ ! -x "$LINT_IMPORTS" ]; then
    echo "" >&2
    echo "ERROR: lint-imports not found next to $PYTHON." >&2
    echo "  It is in the A1 dependency list. A missing linter must not read as a passing" >&2
    echo "  architecture check (testing_hazards.md §2.1)." >&2
    exit 2
fi

# --- Database ----------------------------------------------------------------
#
# Defaults to the STANDARD Postgres port 5432, not this dev box's 5433. The point of
# the gate is to prove the app works with a normal Postgres, which is what the VPS
# runs. Locally, override with DATABASE_URL=...5433/... — see the header.
#
# A scratch database name, and `--create-db` below, means migrations are exercised
# against an empty schema every run. That is what "green on a clean checkout" means.
if [ -z "${DATABASE_URL:-}" ]; then
    export DATABASE_URL="postgres://pgs:pgs@localhost:5432/pgs_verify"
    echo "    database:      $DATABASE_URL (default)"
else
    echo "    database:      $DATABASE_URL"
fi

# `load_dotenv` in pgs/settings.py reads `.env` relative to the settings module, not
# the working directory, so it cannot be dodged from here — warn instead of
# pretending this run is clean.
if [ -f .env ]; then
    echo ""
    echo "    NOTE: .env exists, so this is an IN-PLACE run and settings may be"
    echo "          influenced by it. The authoritative clean-environment run is a"
    echo "          fresh clone with no .env (which is what deploy.sh does)."
fi

# --- 1. Django system checks -------------------------------------------------
echo ""
echo "==> 1/3  manage.py check"
"$PYTHON" manage.py check

# A model change with no migration is invisible on the dev box and prints a warning on
# every deploy (`migrate`: "your models have changes that are not yet reflected in a
# migration"). Found on the VPS 2026-10-22: `EscalatedQuery.reason` gained D54's
# `CITATION_AUDIT` choice and no migration followed. `--check` exits non-zero, and needs
# no database, so it belongs beside `check`.
echo "==> 1/3  makemigrations --check (no model change without a migration)"
if ! "$PYTHON" manage.py makemigrations --check --dry-run; then
    echo "" >&2
    echo "ERROR: a model changed without a migration. Run:" >&2
    echo "    python manage.py makemigrations" >&2
    echo "  A schema change that never reaches the server is worse than a missing field:" >&2
    echo "  the code expects a column the deployment does not have." >&2
    exit 1
fi

# --- 2. Architecture contract ------------------------------------------------
# `--no-cache`: Grimp's cached module graph can outlive a deleted file and report a
# stale result (testing_hazards.md §2.2).
echo ""
echo "==> 2/3  lint-imports (knowledge must never import core)"
"$LINT_IMPORTS" --no-cache --no-logo

# --- 3. The suite ------------------------------------------------------------
echo ""
echo "==> 3/3  pytest"
# `--create-db` forces the test database to be dropped and rebuilt, so migrations
# are proven to apply to an empty schema on every run rather than reusing yesterday's.
#
# `PDFTOTEXT_BIN` is pointed at a path that cannot exist, and an inherited value is
# DISCARDED (D57). Poppler and Xpdf wrap lines and detect columns differently, and
# `-table` is Xpdf-only, so the first deployment gate on the VPS failed 15 tests and 61
# errors on extraction alone (`testing_hazards.md` §2.9). The parsers' goldens now read
# committed page fixtures (`knowledge/tests/page_fixtures.py`), and this line proves it
# on every run, on every machine: the gate passes by not needing a reader, not by having
# one. Regenerating the fixtures is `scripts/extract_fixtures.py`; checking whether a new
# extractor build would change them is `scripts/check_extraction.py`.
export PDFTOTEXT_BIN="$REPO_ROOT/scripts/_no_extractor"

# Drop a leftover test database first. `--create-db` sets `autoclobber=False`, so when a run is
# interrupted (Ctrl-C, or a `| tail` that closes the pipe and SIGPIPEs pytest) its test database
# survives — and every following run then fails ~700 tests with
# `DuplicateDatabase: database "test_…" already exists` before the first assertion
# (`testing_hazards.md` §3.15–§3.16). Dropping it is what `--create-db` was asking for anyway.
"$PYTHON" - "$DATABASE_URL" <<'DROP'
import sys
from urllib.parse import urlsplit

import psycopg2

url = urlsplit(sys.argv[1])
name = f"test_{url.path.lstrip('/')}"
admin = url._replace(path="/postgres").geturl()
# Not `with psycopg2.connect(...)`: that context manager wraps the statements in a transaction,
# and `DROP DATABASE` cannot run inside one (`ActiveSqlTransaction`) — measured 2026-10-28.
conn = psycopg2.connect(admin)
conn.autocommit = True
try:
    with conn.cursor() as cur:
        cur.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity where datname = %s", (name,)
        )
        cur.execute(f'drop database if exists "{name}"')
finally:
    conn.close()
print(f"    dropped any leftover {name}")
DROP

# `--durations=15` is not decoration: the gate's wall time is what a session spends waiting,
# and with no durations printed a suite drifting from 42s to 4 minutes has no signal until
# someone measures it by hand (product/docs/context/TESTING_TIME_PLAN.md).
"$PYTHON" -m pytest -q --create-db --durations=15

echo ""
echo "✅ verify passed — this tree is shippable"
