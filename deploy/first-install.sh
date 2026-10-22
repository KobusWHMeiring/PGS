#!/usr/bin/env bash
# First-time install of Outeniqua PGS on the shared homtini VPS.
#
#   sudo bash /home/carbonplanner/apps/pgs/deploy/first-install.sh
#
# Root-run and idempotent: every step is safe to re-run, so an interrupted first
# install is fixed by running it again rather than by hand-repairing half a box.
# Everyday releases use deploy/deploy.sh — this script is provisioning only.
#
# "First time" is NOT detected here. It is detected by whether
# /etc/systemd/system/pgs_web.service exists (see deploy/README.md).
set -euo pipefail

# ----------------------------- CONFIG ---------------------------------------
APP_NAME="pgs"
DOMAIN="organicguarantee.africa"
ALT_DOMAIN="www.organicguarantee.africa"
GIT_URL="https://github.com/KobusWHMeiring/PGS.git"
GIT_BRANCH="main"
APP_USER="carbonplanner"
APP_DIR="/home/$APP_USER/apps/$APP_NAME"
PYTHON_BIN="python3.12"                  # Ubuntu 24.04 default; >= 3.12 required
WSGI_MODULE="pgs.wsgi:application"
MANAGE_DIR="$APP_DIR"
SOCKET="$APP_DIR/$APP_NAME.sock"
DB_NAME="pgs_db"
DB_USER="pgs_user"
DB_VERIFY_NAME="pgs_verify"
# Backups live OUTSIDE the checkout on purpose: scripts/backup.sh refuses a
# BACKUP_DIR inside the repository, because a backup on the same tree it protects
# survives exactly the failures it exists to survive (R11).
BACKUP_DIR="/home/$APP_USER/backups/$APP_NAME"
CERTBOT_EMAIL="kobussax@gmail.com"
CERT_DOMAINS="$DOMAIN $ALT_DOMAIN"
# Optional superuser. Left blank by default: a password passed through a shell
# argument lands in bash history and in this script's own transcript. Run
# `createsuperuser` interactively instead (printed at the end) unless you have set
# all three.
ADMIN_USER="${ADMIN_USER:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
# ----------------------------------------------------------------------------

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: run as root (sudo bash $0)" >&2
    exit 1
fi

echo "=== First-time install: $APP_NAME ($DOMAIN) ==="

run_manage() {
    # `cd "$MANAGE_DIR"` is not cosmetic. `publish_documents` resolves its source
    # directory relative to the process CWD, and systemd sets WorkingDirectory to
    # the app dir while `sudo bash /home/.../first-install.sh` inherits the
    # caller's `~`. Without this line the first install failed at publish_documents
    # with "pgs_docs/... is not in the tree" while all eight PDFs sat in the checkout.
    sudo -u "$APP_USER" bash -c \
        'set -a; . "$1"; set +a; cd "$2" || exit 1; exec "$3" "$2/manage.py" "${@:4}"' _ \
        "$APP_DIR/.env" "$MANAGE_DIR" "$APP_DIR/venv/bin/python" "$@"
}

# /health/ must be reached the way nginx reaches it: over the unix socket, with the
# Host and X-Forwarded-Proto headers nginx would send. Without those two headers
# DEBUG=False plus SECURE_SSL_REDIRECT turns this into a 301, and `curl --fail`
# treats a 301 as success — a check that passes while the app is unreachable. So
# assert the status code is 200 AND the body says "ok".
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
        return 1
    fi
    printf '%s' "$out" | grep -q '"status": *"ok"' && return 0
    echo "    body is not ok: $(printf '%s' "$out" | head -c 300)"
    return 1
}

# 0. Backup client ------------------------------------------------------------
# `scripts/backup.sh` refuses a pg_dump whose major differs from the server, and
# `deploy.sh` refuses to migrate without a verified backup. A box provisioned with the
# *server* package can still lack a matching client on PATH, and the deploy then dies at
# step 3/8 on a site that otherwise looks healthy (VPS, 2026-10-22).
if ! command -v pg_dump >/dev/null 2>&1; then
    echo "ERROR: pg_dump not found. The deploy backs up before migrating and refuses to" >&2
    echo "  migrate without one." >&2
    echo "      sudo apt-get install -y postgresql-client-16   # match the server's major" >&2
    exit 1
fi

# 1. Python gate -------------------------------------------------------------
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: $PYTHON_BIN not found." >&2
    echo "  sudo apt-get install -y python3.12 python3.12-venv python3.12-dev" >&2
    exit 1
fi
PY_VER="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$(printf '%s\n3.12\n' "$PY_VER" | sort -V | head -n1)" != "3.12" ]]; then
    echo "ERROR: need Python >= 3.12, found $PY_VER" >&2
    exit 1
fi

# poppler's `pdftotext` is the corpus's only reader. `knowledge/extraction.py`
# shells out to `pdftotext -layout` for every governed PDF, so a box without it
# installs, migrates and serves pages perfectly — and cannot ingest the standard,
# which means /ask/ refuses every question while the site looks finished. Checked
# here rather than at ingest time, where the operator has no reason to be looking.
if ! command -v pdftotext >/dev/null 2>&1; then
    echo "ERROR: pdftotext not found (package poppler-utils)." >&2
    echo "  knowledge/extraction.py reads the governing PDFs with 'pdftotext -layout'." >&2
    echo "  Without it the corpus cannot be ingested and /ask/ answers nothing." >&2
    echo "" >&2
    echo "      sudo apt-get install -y poppler-utils" >&2
    exit 1
fi
echo "[1/9] Python $PY_VER + pdftotext $(pdftotext -v 2>&1 | head -n1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo '')"

# 2. Checkout ----------------------------------------------------------------
echo "[2/9] Checkout at $APP_DIR"
install -d -o "$APP_USER" -g "$APP_USER" "$(dirname "$APP_DIR")"
if [[ -d "$APP_DIR/.git" ]]; then
    echo "      existing clone — pulling"
    sudo -u "$APP_USER" git -C "$APP_DIR" fetch origin "$GIT_BRANCH"
    sudo -u "$APP_USER" git -C "$APP_DIR" checkout "$GIT_BRANCH"
    sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only origin "$GIT_BRANCH"
elif [[ -e "$APP_DIR" ]]; then
    echo "ERROR: $APP_DIR exists but is not a git checkout; move it aside." >&2
    exit 1
else
    sudo -u "$APP_USER" git clone --branch "$GIT_BRANCH" "$GIT_URL" "$APP_DIR"
fi

# 3. venv --------------------------------------------------------------------
echo "[3/9] venv"
if [[ ! -x "$APP_DIR/venv/bin/python" ]]; then
    sudo -u "$APP_USER" "$PYTHON_BIN" -m venv "$APP_DIR/venv"
fi

# 4. .env (generated once, never overwritten) --------------------------------
ENV_FILE="$APP_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
    echo "[4/9] .env exists — keeping existing secrets"
else
    echo "[4/9] writing $ENV_FILE"
    # hex, not base64: this file is sourced as shell by this script, by deploy.sh
    # and by the systemd EnvironmentFile parser, and it is parsed by hand in
    # scripts/backup.sh. Hex has no character any of those four treat specially.
    SECRET="$(openssl rand -hex 32)"      # 64 chars: Django's W009 needs >= 50
    DB_PASS="$(openssl rand -hex 16)"     # no ':' '@' or '/', so the URL parses
    {
        echo "# Generated by deploy/first-install.sh on $(date -u '+%Y-%m-%dT%H:%M:%SZ')."
        echo "# This file is the sole configuration source and is never committed."
        echo ""
        echo "DJANGO_SECRET_KEY=$SECRET"
        echo "DJANGO_DEBUG=0"
        echo "DJANGO_ALLOWED_HOSTS=$DOMAIN,$ALT_DOMAIN,127.0.0.1,localhost"
        echo "CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://$ALT_DOMAIN"
        # Turns on SECURE_SSL_REDIRECT, secure cookies, HSTS and the
        # X-Forwarded-Proto trust. Without it `check --deploy` fails and this
        # script aborts — deliberately, because a site answering plain HTTP with
        # DEBUG=0 is the configuration the block exists to prevent.
        echo "DJANGO_TLS=1"
        echo ""
        echo "DATABASE_URL=postgres://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
        echo ""
        echo "# 7/8/9 are reserved for pgs on the shared Redis (see .env.example)."
        echo "CELERY_BROKER_URL=redis://localhost:6379/7"
        echo "CELERY_RESULT_BACKEND=redis://localhost:6379/8"
        echo "CACHE_URL=redis://localhost:6379/9"
        echo ""
        echo "SENTRY_DSN="
        echo "SENTRY_ENVIRONMENT=production"
        echo "DJANGO_LOG_LEVEL=INFO"
        echo ""
        echo "# Fill this in on the server; /ask/ stays degraded-but-honest without it."
        echo "GEMINI_API_KEY="
    } | sudo -u "$APP_USER" tee "$ENV_FILE" >/dev/null
    chmod 600 "$ENV_FILE"
fi
# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a
: "${DATABASE_URL:?DATABASE_URL missing from .env}"

# 5. PostgreSQL + pgvector ---------------------------------------------------
echo "[5/9] PostgreSQL role, databases and the vector extension"
PG_MAJOR="$(sudo -u postgres psql -tAc 'SHOW server_version_num' | tr -d '[:space:]' | cut -c1-2)"
if [[ -z "$PG_MAJOR" ]]; then
    echo "ERROR: could not reach the local PostgreSQL server as the postgres role." >&2
    exit 1
fi
if [[ "$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")" != "1" ]]; then
    echo "ERROR: the pgvector extension is not available on this PostgreSQL $PG_MAJOR." >&2
    echo "  knowledge/0001_initial.py runs CREATE EXTENSION vector before it can" >&2
    echo "  create the embedding column, so migrate cannot proceed without it." >&2
    echo "" >&2
    echo "  Install it, then re-run this script:" >&2
    echo "      sudo apt-get update && sudo apt-get install -y postgresql-$PG_MAJOR-pgvector" >&2
    exit 1
fi

# The password comes from .env (generated above, or an existing file). Read it back
# from the URL rather than regenerating: a re-run must not desynchronise the role
# password from the value the app uses.
DB_PASS_FROM_URL="${DATABASE_URL#*://}"
DB_PASS_FROM_URL="${DB_PASS_FROM_URL#*:}"
DB_PASS_FROM_URL="${DB_PASS_FROM_URL%%@*}"
# The SQL carries the generated password, so it is piped into psql rather than
# written to a file. `mktemp` creates a 0600 file owned by root; `sudo -u postgres`
# then cannot read it, and the install dies with
#     psql: error: /tmp/tmp.XXXX: Permission denied
# before the role or either database exists. Streaming keeps the password out of
# /tmp as well. `\connect` works from stdin: psql processes it as it reads.
sed -e "s|__APP_NAME__|$APP_NAME|g" \
    -e "s|__DB_NAME__|$DB_NAME|g" \
    -e "s|__DB_VERIFY_NAME__|$DB_VERIFY_NAME|g" \
    -e "s|__DB_USER__|$DB_USER|g" \
    -e "s|__DB_PASSWORD__|$DB_PASS_FROM_URL|g" \
    "$APP_DIR/deploy/psql_setup.sql" \
    | sudo -u postgres psql -v ON_ERROR_STOP=1 -q

# 6. Dependencies ------------------------------------------------------------
echo "[6/9] Installing dependencies"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
# gunicorn is deliberately NOT in requirements.txt: it is the VPS's process
# manager, not an import. Celery IS there, because tasks import it.
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --quiet gunicorn

# 7. Schema, data, static ----------------------------------------------------
echo "[7/9] migrate, seed, publish documents, collectstatic"
sudo -u "$APP_USER" install -d "$APP_DIR/media" "$APP_DIR/private_media"
run_manage migrate --noinput
# Seals and categories are DATA, not migrations (A4) — idempotent by design.
run_manage seed_deployment
# The eight published documents (C2). Also data, also idempotent — and the step
# whose absence leaves /documents/ linking eight 503s that /health/ cannot see.
run_manage publish_documents
run_manage collectstatic --noinput

echo "      manage.py check --deploy"
# `--fail-level WARNING` is not decoration: the default fail level is ERROR, and
# every security check here is a *warning*, so a plain `check --deploy` exits 0
# with `DEBUG=True` still on. Without the flag this guard cannot fail.
if ! run_manage check --deploy --fail-level WARNING; then
    echo "" >&2
    echo "ERROR: check --deploy reported issues. Fix them before exposing the site." >&2
    exit 1
fi

# The corpus itself is NOT ingested here: it makes ~340 paid embedding calls and is
# idempotent on the PDF's sha256. See deploy/README.md §4.

# 8. systemd + nginx ---------------------------------------------------------
echo "[8/9] systemd units, nginx site, certificate"
install -d -o "$APP_USER" -g "$APP_USER" /var/log/gunicorn "$BACKUP_DIR"

install -m 644 "$APP_DIR/deploy/pgs_web.service"    "/etc/systemd/system/${APP_NAME}_web.service"
install -m 644 "$APP_DIR/deploy/pgs_celery.service" "/etc/systemd/system/${APP_NAME}_celery.service"
systemctl daemon-reload
systemctl enable --now "${APP_NAME}_web"
systemctl enable --now "${APP_NAME}_celery"

# A temporary HTTP-only site first: the committed nginx.conf references
# /etc/letsencrypt/live/... which does not exist yet, so installing it now would
# fail `nginx -t` and take down whatever else is being reloaded with it.
SITE="/etc/nginx/sites-available/$APP_NAME"
cat > "$SITE" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN $ALT_DOMAIN;
    location / { return 200 "provisioning $APP_NAME\n"; }
}
EOF
ln -sf "$SITE" "/etc/nginx/sites-enabled/$APP_NAME"
nginx -t && systemctl reload nginx

install -d /var/www/certbot

CERT_ARGS=()
for d in $CERT_DOMAINS; do CERT_ARGS+=(-d "$d"); done
# `certonly`, not `--nginx` install mode: it obtains the certificate without
# rewriting the site, so the file installed below is the one in this repository.
# certbot's later renewals keep working because the renewal conf records the nginx
# authenticator.
if ! certbot certonly --nginx "${CERT_ARGS[@]}" \
        --cert-name "$DOMAIN" \
        --agree-tos --non-interactive --email "$CERTBOT_EMAIL"; then
    echo "" >&2
    echo "WARNING: certbot failed. Check that $DOMAIN resolves to this box and that" >&2
    echo "         port 80 is open, then re-run this script." >&2
    echo "         nginx is serving the HTTP placeholder for now." >&2
    exit 1
fi

cp "$SITE" "$SITE.http"
install -m 644 "$APP_DIR/deploy/nginx.conf" "$SITE"
if nginx -t; then
    systemctl reload nginx
    rm -f "$SITE.http"
else
    install -m 644 "$SITE.http" "$SITE"
    rm -f "$SITE.http"
    nginx -t && systemctl reload nginx
    echo "ERROR: the committed nginx.conf was rejected — restored the HTTP-only site." >&2
    exit 1
fi

# 9. Optional superuser + smoke test ----------------------------------------
echo "[9/9] superuser + smoke test"
if [[ -n "$ADMIN_USER" && -n "$ADMIN_PASSWORD" ]]; then
    run_manage shell -c "
from django.contrib.auth import get_user_model
U = get_user_model()
u, created = U.objects.get_or_create(username='$ADMIN_USER',
    defaults={'email': '$ADMIN_EMAIL', 'is_staff': True, 'is_superuser': True})
if created:
    u.set_password('$ADMIN_PASSWORD')
    u.save()
print('superuser', 'created' if created else 'kept')
"
fi

for attempt in 1 2 3 4 5 6 7 8; do
    if health_ok; then
        echo ""
        echo "✅ $APP_NAME is up — https://$DOMAIN/ is serving"
        echo ""
        echo "Remaining manual steps (deploy/README.md):"
        echo "  1. put GEMINI_API_KEY in $ENV_FILE, then restart ${APP_NAME}_web"
        echo "  2. create an admin:  sudo -u $APP_USER bash -c 'set -a; . $ENV_FILE; set +a; cd $APP_DIR && venv/bin/python manage.py createsuperuser'"
        echo "  3. ingest the corpus (340 embedding calls):"
        echo "       sudo -u $APP_USER bash -c 'set -a; . $ENV_FILE; set +a; cd $APP_DIR && venv/bin/python manage.py ingest_standard --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf'"
        echo "       (and --doc opp, bpp, landscape — see deploy/README.md §4)"
        exit 0
    fi
    echo "    health check $attempt/8 failed; retrying in ${attempt}s"
    sleep "$attempt"
done

echo "" >&2
echo "❌ The app was installed but /health/ is NOT ok." >&2
echo "   journalctl -u ${APP_NAME}_web -n 80 --no-pager" >&2
echo "   journalctl -u ${APP_NAME}_celery -n 80 --no-pager" >&2
curl -s --unix-socket "$SOCKET" -H "Host: $DOMAIN" -H 'X-Forwarded-Proto: https' \
    "http://localhost/health/" || true
exit 1
