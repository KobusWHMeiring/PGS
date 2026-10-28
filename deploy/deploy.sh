#!/usr/bin/env bash
# Everyday redeploy of Outeniqua PGS on the shared homtini VPS.
#
#   sudo bash /home/carbonplanner/apps/pgs/deploy/deploy.sh
#
# Root-run because it syncs nginx and systemd; application commands run as
# carbonplanner. Aborts on the first error, and every step is safe to re-run.
#
# The order IS the safety, and it is the one thing this script does that a plain
# `git pull && migrate && restart` cannot:
#
#   1. materialise origin/main into a scratch directory
#   2. install its requirements, run scripts/verify.sh there, with no .env
#   3. only then back up, pull, migrate, collect static, sync config, restart
#   4. prove the app answers /health/ through the socket nginx uses
#
# A test that runs after the pull cannot block anything: by then the code is on
# the server and the schema has already changed.
set -euo pipefail

# ----------------------------- CONFIG ---------------------------------------
APP_NAME="pgs"
DOMAIN="organicguarantee.africa"
ALT_DOMAIN="www.organicguarantee.africa"
APP_USER="carbonplanner"
APP_DIR="/home/$APP_USER/apps/$APP_NAME"
MANAGE_DIR="$APP_DIR"
SERVICE="${APP_NAME}_web"
CELERY_SERVICE="${APP_NAME}_celery"
GIT_BRANCH="main"
DB_VERIFY_NAME="pgs_verify"
SOCKET="$APP_DIR/$APP_NAME.sock"
BACKUP_DIR="/home/$APP_USER/backups/$APP_NAME"
KEEP_BACKUPS=10
ENV_FILE="$APP_DIR/.env"
NGINX_FILE="$APP_DIR/deploy/nginx.conf"
# ----------------------------------------------------------------------------

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: run as root (sudo bash $0)" >&2
    exit 1
fi
if [[ ! -d "$APP_DIR/.git" ]]; then
    echo "ERROR: $APP_DIR is not a git checkout — run deploy/first-install.sh first." >&2
    exit 1
fi
if [[ -f /etc/systemd/system/${SERVICE}.service ]] && \
   systemctl list-unit-files "${SERVICE}.service" >/dev/null 2>&1; then
    :
else
    echo "ERROR: ${SERVICE}.service is not installed. Run deploy/first-install.sh." >&2
    exit 1
fi

cd "$APP_DIR"
# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a
: "${DATABASE_URL:?DATABASE_URL missing from $ENV_FILE}"

run_manage() {
    # Same `cd` as first-install.sh: this script already `cd`s to APP_DIR, but the
    # helper must not depend on that. `publish_documents` resolves `pgs_docs/`
    # relative to the process CWD.
    sudo -u "$APP_USER" bash -c \
        'set -a; . "$1"; set +a; cd "$2" || exit 1; exec "$3" "$2/manage.py" "${@:4}"' _ \
        "$ENV_FILE" "$MANAGE_DIR" "$APP_DIR/venv/bin/python" "$@"
}

# /health/ through the unix socket, with the headers nginx sends. 200 AND a body
# that says ok: with DEBUG=False and SECURE_SSL_REDIRECT on, a request without
# X-Forwarded-Proto is a 301, and `curl --fail` calls a 301 a success.
health_ok() {
    local out code
    out="$(curl --silent --show-error --max-time 10 \
        --unix-socket "$SOCKET" \
        -H "Host: $DOMAIN" \
        -H 'X-Forwarded-Proto: https' \
        -w '\n%{http_code}' \
        "http://localhost/health/" 2>&1)" || return 1
    code="$(printf '%s' "$out" | tail -n1)"
    if [[ "$code" != "200" ]]; then
        echo "    HTTP $code"
        printf '%s\n' "$out" | head -c 400
        return 1
    fi
    printf '%s' "$out" | grep -q '"status": *"ok"' && return 0
    echo "    body is not ok: $(printf '%s' "$out" | head -c 300)"
    return 1
}

echo "=== Redeploying $APP_NAME ($DOMAIN) ==="

# 1. Hash ourselves before the pull. If the pull changes this file, bash is still
#    reading the OLD body and the new steps would never run — so re-exec.
SELF_PATH="$(readlink -f "$0")"
SELF_BEFORE="$(sha256sum "$SELF_PATH" | cut -d' ' -f1)"

# 2. The deploy gate: verify origin/main in a clean tree -----------------------
#
# `git archive FETCH_HEAD` rather than `git clone $APP_DIR`: a local clone copies
# the local branch, which is not necessarily origin/main, and a --depth 1 clone of
# a local path still carries the *committed* HEAD — neither is the thing that will
# be deployed. Fetch first, archive the fetched commit, and what is tested is
# exactly what the pull below installs.
echo ""
echo "==> 1/8  Verifying origin/$GIT_BRANCH in a clean tree"
# Never `--depth 1` here. This fetch runs against the LIVE checkout, and a depth-limited
# fetch writes a shallow graft into it: `origin/main` arrives with no ancestors, so the
# `--ff-only` pull at step 2/8 can never find a merge base and reports a bogus divergence
# ("have diverged, and have 57 and 1 different commits each") — measured on the VPS
# 2026-10-22, after the first deploy run had already made the clone shallow. A deploy must
# not damage the repository it is deploying.
if [[ -f "$APP_DIR/.git/shallow" ]]; then
    echo "        repo is shallow (a previous deploy fetched with --depth 1) — unshallowing"
    sudo -u "$APP_USER" git -C "$APP_DIR" fetch --quiet --unshallow origin "$GIT_BRANCH"
fi
sudo -u "$APP_USER" git -C "$APP_DIR" fetch --quiet origin "$GIT_BRANCH"
VERIFY_COMMIT="$(sudo -u "$APP_USER" git -C "$APP_DIR" rev-parse FETCH_HEAD)"
SCRATCH="$(sudo -u "$APP_USER" mktemp -d /tmp/${APP_NAME}-verify-XXXXXX)"
cleanup() {
    local rc=$?
    [[ -n "${SCRATCH:-}" ]] && rm -rf "$SCRATCH"
    exit $rc
}
trap cleanup EXIT INT TERM

sudo -u "$APP_USER" bash -c "git -C '$APP_DIR' archive FETCH_HEAD | tar -x -C '$SCRATCH'"
# verify.sh resolves `.venv/bin/python`, then falls back to system python3 — which
# on this Ubuntu has no Django (PEP 668) and would fail at the first import. The
# symlink makes the scratch tree use the deployment's own dependency set.
sudo -u "$APP_USER" ln -s "$APP_DIR/venv" "$SCRATCH/.venv"

# Install the requirements OF THE COMMIT BEING VERIFIED before verifying it. Doing
# this first is what lets a release that adds a dependency pass its own gate; the
# old code is still serving, and pip installing is not the irreversible step here
# (the migration is).
echo "        installing requirements of $VERIFY_COMMIT"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --quiet -r "$SCRATCH/requirements.txt"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --quiet gunicorn

# The gate's own database, so verification never touches live rows. `--create-db`
# inside verify.sh drops and rebuilds `test_$DB_VERIFY_NAME` every run.
VERIFY_DATABASE_URL="${DATABASE_URL%/*}/$DB_VERIFY_NAME"
VERIFY_SECRET="$(openssl rand -hex 32)"
# `PDFTOTEXT_BIN` travels with the gate: the parsers' golden page/wrap tables match
# one extractor implementation, so a deployment that pins Xpdf must be verified with
# Xpdf. `sudo -u` resets the environment, so it is named explicitly like the two above.
echo "        verify.sh (check + lint-imports + pytest --create-db)"
if ! sudo -u "$APP_USER" env \
        DJANGO_SECRET_KEY="$VERIFY_SECRET" \
        DATABASE_URL="$VERIFY_DATABASE_URL" \
        PDFTOTEXT_BIN="${PDFTOTEXT_BIN:-}" \
        bash -c "cd '$SCRATCH' && ./scripts/verify.sh"; then
    echo "" >&2
    echo "❌ The gate FAILED on origin/$GIT_BRANCH ($VERIFY_COMMIT)." >&2
    echo "   Nothing was deployed. The live tree and the schema are untouched." >&2
    echo "   Fix, push, and re-run." >&2
    exit 1
fi
rm -rf "$SCRATCH"; SCRATCH=""
echo "        gate passed"
trap - EXIT INT TERM

# 3. Pull ---------------------------------------------------------------------
echo ""
echo "==> 2/8  Pulling origin/$GIT_BRANCH"
sudo -u "$APP_USER" git -C "$APP_DIR" checkout "$GIT_BRANCH"
sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only origin "$GIT_BRANCH"

if [[ -z "${DEPLOY_REEXEC:-}" && \
      "$SELF_BEFORE" != "$(sha256sum "$SELF_PATH" | cut -d' ' -f1)" ]]; then
    echo "==> deploy.sh changed in this pull — re-executing the new version"
    export DEPLOY_REEXEC=1
    exec bash "$SELF_PATH" "$@"
fi

# 4. Backup BEFORE migrating --------------------------------------------------
#
# A migration without a verified backup is the one irreversible step. This calls
# the REAL scripts/backup.sh rather than a hand-rolled pg_dump: that script picks a
# client whose major version matches the server (a newer pg_dump writes syntax the
# server cannot restore) and verifies the archive before declaring success. A
# failed backup aborts — migrating without one is not a risk worth taking to keep
# a deploy moving.
echo ""
echo "==> 3/8  Backing up the database (pre-migration)"
sudo -u "$APP_USER" install -d "$BACKUP_DIR"
if ! sudo -u "$APP_USER" env BACKUP_DIR="$BACKUP_DIR" "$APP_DIR/scripts/backup.sh"; then
    echo "" >&2
    echo "❌ Pre-migration backup FAILED. Refusing to migrate without one." >&2
    echo "   The site is still running the previous code; nothing has changed." >&2
    exit 1
fi
# Keep only the most recent sets. The scheduled off-box backup is the durability
# story; these are the rollback point for the migration about to run.
find "$BACKUP_DIR" -maxdepth 1 -type d -name 'db-*' -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | tail -n +"$((KEEP_BACKUPS + 1))" | cut -d' ' -f2- | xargs -r rm -rf

# 5. Migrate, seed, publish, report the corpus, collect static ------------------
echo ""
echo "==> 4/8  migrate, seed, publish documents, corpus report, collectstatic"
run_manage migrate --noinput
# Seals and categories are DATA (A4), idempotent by design, and never reactivate a
# seal the group has retired.
run_manage seed_deployment
# The eight published documents (C2). Data too, and the step whose absence leaves
# /documents/ linking eight 503s that /health/ cannot see.
run_manage publish_documents
# Is this box serving the corpus its reviewed artefacts describe? (D56, plan P2.4)
# **Reported, never enforced and never repaired.** A first install has an empty corpus
# and a box deployed before D53 serves a PDF-built one; refusing to deploy over either
# is worse than saying so. The refresh is deliberately not run here: it re-embeds four
# documents and drops every chat turn's citation links, which is a decision for a person
# with a terminal. `tests/tools/test_deploy_corpus_check.py` holds both halves of that.
if ! run_manage corpus_check; then
    echo ""
    echo "⚠️  corpus_check: the corpus is not current (above). The site is up on what it has."
    echo "   Refresh it deliberately, when someone can watch it run:"
    echo "     sudo -u $APP_USER bash -c 'set -a; . $ENV_FILE; set +a; cd $APP_DIR && venv/bin/python manage.py corpus_refresh --apply'"
fi
run_manage collectstatic --noinput

echo ""
echo "==> 5/8  manage.py check --deploy"
# `--fail-level WARNING`, because the default fail level is ERROR and every
# security check is a warning: `check --deploy` on its own exits 0 with DEBUG=True
# still set. A gate whose exit code cannot go red is not a gate.
if ! run_manage check --deploy --fail-level WARNING; then
    echo "" >&2
    echo "❌ check --deploy reported issues. The previous code is still serving;" >&2
    echo "   fix the setting and re-run. Do not expose a site that fails this." >&2
    exit 1
fi

# 6. Sync server config from the repo ----------------------------------------
# A committed nginx/unit change that no deploy copies never reaches the box, and
# the failure mode is a config that looks right in git and is stale on disk.
echo ""
echo "==> 6/8  Syncing nginx site and systemd units"
SITE="/etc/nginx/sites-available/$APP_NAME"
if [[ -f "$SITE" ]] && ! diff -q "$NGINX_FILE" "$SITE" >/dev/null 2>&1; then
    cp "$SITE" "$SITE.bak"
    install -m 644 "$NGINX_FILE" "$SITE"
    ln -sf "$SITE" "/etc/nginx/sites-enabled/$APP_NAME"
    if nginx -t; then
        systemctl reload nginx
    else
        install -m 644 "$SITE.bak" "$SITE"
        rm -f "$SITE.bak"
        nginx -t && systemctl reload nginx
        echo "❌ nginx rejected the new config — rolled back to the previous site." >&2
        exit 1
    fi
    rm -f "$SITE.bak"
fi

for unit in "$SERVICE" "$CELERY_SERVICE"; do
    src="$APP_DIR/deploy/${unit}.service"
    dst="/etc/systemd/system/${unit}.service"
    if [[ -f "$src" ]] && ! diff -q "$src" "$dst" >/dev/null 2>&1; then
        install -m 644 "$src" "$dst"
        systemctl daemon-reload
    fi
    systemctl enable "$unit" >/dev/null 2>&1 || true
done

# 7. Restart and prove it came up --------------------------------------------
# The worker first: /health/ is a readiness probe and returns 503 until a Celery
# worker answers `control.ping()`, so restarting the web unit first guarantees one
# failed health check on every deploy and hides a real failure in the retries.
echo ""
echo "==> 7/8  Restarting $CELERY_SERVICE and $SERVICE"
systemctl restart "$CELERY_SERVICE"
systemctl restart "$SERVICE"

echo ""
echo "==> 8/8  Checking /health/ through the socket nginx uses"
for attempt in 1 2 3 4 5 6; do
    if health_ok; then
        echo ""
        echo "✅ Deploy complete — $VERIFY_COMMIT is live"
        echo "   https://$DOMAIN/health/ reports ok"
        # Informational, and deliberately not fatal: a failure here is DNS,
        # hairpin routing or the certificate, not the code that was just deployed.
        # The socket check above is the authoritative one.
        if ! curl -sS --fail --max-time 8 "https://$DOMAIN/health/" >/dev/null 2>&1; then
            echo "   NOTE: https://$DOMAIN/health/ did not answer from this box."
            echo "         Check DNS, the firewall, or run: certbot certificates"
        fi
        exit 0
    fi
    echo "    health check $attempt/6 failed; retrying in ${attempt}s"
    sleep "$attempt"
done

echo "" >&2
echo "❌ Service restarted but /health/ is NOT ok." >&2
echo "   The deploy is incomplete; the app may be rolling back on start." >&2
echo "   journalctl -u $SERVICE -n 80 --no-pager" >&2
echo "   journalctl -u $CELERY_SERVICE -n 80 --no-pager" >&2
exit 1
