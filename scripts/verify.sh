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
"$PYTHON" -m pytest -q --create-db

echo ""
echo "✅ verify passed — this tree is shippable"
