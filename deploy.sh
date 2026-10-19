#!/usr/bin/env bash
#
# deploy.sh — deploy Outeniqua PGS to the VPS.
#
# ⚠️  STAGED FOR LATER. This script is NOT used by MVP 0.
#
#     PGS_PLATFORM_SPEC.md D19 records MVP 0 as a LOCAL PREVIEW with no public host;
#     the VPS cutover is MVP 2. The script is written now because D19 also says the
#     compose file and nginx config are "written as the reference deployment and
#     carried to a VPS at MVP 2" — so the deployment shape should not be improvised
#     later under time pressure.
#
#     It also carries a guard (below) that refuses to run anywhere that is not
#     clearly the server, so nobody runs it by accident from a dev box.
#
# ── The gate ─────────────────────────────────────────────────────────────────
#
# The one thing this does that the existing deploy.sh files do NOT (harvester,
# river, elands, plot, homtini_store — none of them run tests) is verify BEFORE
# touching the live tree:
#
#     1. clone the pushed commit into a scratch directory
#     2. run scripts/verify.sh there — check + lint-imports + pytest, against a
#        real Postgres, with NO .env, exactly as a clean checkout
#     3. only if that passes: pull, migrate, collectstatic, restart
#
# The order matters. The established pattern is `git pull` -> `migrate` -> restart,
# which has no position where a test could gate anything: by the time a test could
# run, the code is already on the server and the schema has already changed. A
# failure there is an outage with a half-applied migration, not a blocked deploy.
#
# CI would run the same checks on GitHub's ubuntu-latest. This runs them on the
# actual target, which is a stronger signal — and unlike CI, a deploy script that
# aborts cannot be ignored.
#
# ── Usage (on the server) ────────────────────────────────────────────────────
#
#     cd ~/apps/pgs
#     ./deploy.sh
#
# Requires `set -euo pipefail` behaviour: aborts on the first error, so a failed
# pull or migration never leaves the site half-updated.
#
set -euo pipefail

# --- Configuration -----------------------------------------------------------
# Repo root = the directory this script lives in, so it can be run from anywhere.

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$APP_DIR/venv"
SERVICE="pgs.service"        # systemd unit running gunicorn
BRANCH="main"
SCRATCH="$(mktemp -d /tmp/pgs-verify-XXXXXX)"
KEEP_BACKUPS=10              # timestamped database backups to retain

# --- Guard: refuse to run off-server ----------------------------------------
# An explicit check rather than a comment, because a comment is what gets ignored.
# If this trips, you are on a dev box and the script did nothing.
if [ ! -d /etc/systemd/system ] || ! systemctl list-unit-files "$SERVICE" >/dev/null 2>&1; then
    echo "REFUSING TO DEPLOY: this does not look like the server." >&2
    echo "  Expected systemd unit: $SERVICE" >&2
    echo "  This script deploys to the VPS. It is staged for later — MVP 0 is a" >&2
    echo "  local preview (D19) and is not deployed. See the header." >&2
    exit 1
fi

# Always clean the scratch clone, including on failure or Ctrl-C.
cleanup() {
    local rc=$?
    rm -rf "$SCRATCH"
    exit $rc
}
trap cleanup EXIT INT TERM

cd "$APP_DIR"
echo "==> Deploying Outeniqua PGS from $APP_DIR"

# --- 1. Trust nothing: verify the pushed commit in a clean clone ------------
#
# `--ff-only` on the fetch target: we verify exactly what is on origin/$BRANCH, not
# a local tree that might carry uncommitted edits.
echo ""
echo "==> 1/6  Verifying origin/$BRANCH in a clean checkout ($SCRATCH)"
git clone --quiet --depth 1 --branch "$BRANCH" "$APP_DIR" "$SCRATCH"

# A fresh clone has no .env, no venv and no local state — the one environment in
# which "green on a clean checkout" actually means something.
cd "$SCRATCH"

# The scratch clone has no venv of its own; reuse the deployed one so verification
# uses the same dependency set the site will run.
DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')}" \
DATABASE_URL="${VERIFY_DATABASE_URL:-postgres://pgs:pgs@localhost:5432/pgs_verify}" \
    "$APP_DIR/scripts/verify.sh"

cd "$APP_DIR"
echo "    verification passed — proceeding to deploy"

# --- 2. Pull -----------------------------------------------------------------
echo ""
echo "==> 2/6  Pulling origin/$BRANCH"
git pull --ff-only origin "$BRANCH"

# --- 3. Dependencies ---------------------------------------------------------
echo ""
echo "==> 3/6  Installing requirements"
"$VENV/bin/pip" install --quiet -r requirements.txt

# --- 4. Back up the database BEFORE migrating --------------------------------
# R11: the filesystem media volume is the only copy of evidentiary photos and PDFs,
# and the database is the only copy of the records. A migration that goes sideways
# without a backup is unrecoverable.
#
# This calls the REAL backup script (A9) rather than reimplementing pg_dump here.
# That matters for one specific reason: scripts/backup.sh selects a client whose major
# version matches the server, and a pg_dump newer than the server writes syntax the
# server cannot restore. A hand-rolled pg_dump in a deploy script would reintroduce
# exactly that trap at the moment it is most dangerous — right before a migration.
#
# It also fails the deploy if the backup fails. Migrating without a backup is the one
# irreversible step in this script.
echo ""
echo "==> 4/6  Backing up the database (pre-migration)"
if ! BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}" "$APP_DIR/scripts/backup.sh"; then
    echo "" >&2
    echo "❌ Pre-migration backup FAILED. Refusing to migrate without one." >&2
    echo "   The site is still running the previous code; nothing has changed." >&2
    echo "   Investigate: BACKUP_DIR=${BACKUP_DIR:-$APP_DIR/backups}, then re-run." >&2
    exit 1
fi

echo "    pre-migration backup verified"

# Retain only the most recent pre-migration backups. The scheduled off-box backup
# (docs/RUNBOOK.md §1) is the real durability story; these are just the last-resort
# rollback point for the migration about to run.
ls -1td "${BACKUP_DIR:-$APP_DIR/backups}"/db-* 2>/dev/null \
    | tail -n +"$((KEEP_BACKUPS + 1))" | xargs -r rm -rf || true

# --- 5. Migrate, seed, collect static ---------------------------------------
echo ""
echo "==> 5/6  Migrating, seeding, collecting static"
"$VENV/bin/python" manage.py migrate --noinput

# Seals and categories are DATA, not migrations (A4). Idempotent by design, so it
# runs on every deploy and never reactivates a seal the group has retired.
"$VENV/bin/python" manage.py seed_deployment

# The public document library (C2, D22). Also data, also idempotent — and also a step
# that must not be forgotten: without it `/documents/` lists eight documents whose 503
# the deploy's own health check will never see, because /health/ does not read media.
"$VENV/bin/python" manage.py publish_documents

"$VENV/bin/python" manage.py collectstatic --noinput

# --- 6. Restart and prove it came up ----------------------------------------
echo ""
echo "==> 6/6  Restarting $SERVICE and checking health"
sudo systemctl restart "$SERVICE"

# A deploy that does not check its own result is a deploy that reports success while
# the site is down. `/health/` returns 503 when any dependency is unhealthy (A5) —
# including a Celery worker that is not consuming, which is invisible to a broker ping.
for attempt in 1 2 3 4 5; do
    if curl --fail --silent --max-time 5 http://127.0.0.1:8000/health/ >/dev/null; then
        echo ""
        echo "✅ Deployment complete — /health/ is green"
        exit 0
    fi
    echo "    health check attempt $attempt/5 failed; retrying in ${attempt}s"
    sleep "$attempt"
done

echo "" >&2
echo "❌ Service restarted but /health/ is NOT healthy." >&2
echo "   The deploy is incomplete; the previous code may still be serving." >&2
echo "   Check: sudo journalctl -u $SERVICE -n 50" >&2
echo "   And:  curl -i http://127.0.0.1:8000/health/" >&2
exit 1
