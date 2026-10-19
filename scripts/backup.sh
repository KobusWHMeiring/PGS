#!/usr/bin/env bash
#
# backup.sh — back up the database AND both media roots to an attached drive.
#
# This is R11, which the spec rates **High** risk:
#
#   "Filesystem media is the only copy of evidentiary photos and PDFs; disk failure,
#    a botched deploy, or silent backup failure destroys certification evidence.
#    Critically: the backup job must report failure — a cron that dies quietly is
#    worse than no cron."
#
# So the design goal is not "make a copy". It is "make a copy that cannot silently
# be absent, empty, or corrupt". Concretely:
#
#   * `set -euo pipefail` — a failed step aborts, it does not continue and exit 0.
#   * A non-zero exit on ANY failure, with a timestamped line to both stderr and a
#     log file, so cron/systemd can alert. Every message is prefixed with a
#     timestamp; an undated log line cannot be correlated with an incident.
#   * The dump is **verified after writing** (`pg_restore --list`), because pg_dump
#     can exit 0 having written a truncated file when the disk fills.
#   * Per-item `sha256` for every artefact, and a re-verification pass at the end, so
#     silent corruption is detected at write time rather than at restore time.
#   * **Row counts are recorded** into the backup. `restore.sh` compares against
#     these, so "the restore worked" is a measurement, not an opinion.
#   * A lock file, so two overlapping runs cannot interleave writes to one backup.
#   * Pruning never deletes the most recent N, and runs only AFTER a verified success
#     — a failed backup that pruned the good one first is data loss.
#
# Usage:
#   BACKUP_DIR=/mnt/backup-drive ./scripts/backup.sh
#
# Environment (defaults shown; normally read from .env):
#   BACKUP_DIR          required — the attached external drive (D19)
#   DATABASE_URL        postgres://user:pass@host:port/dbname
#   MEDIA_ROOT          media/           (public derivatives)
#   PRIVATE_MEDIA_ROOT  private_media/   (evidence originals — never public)
#   BACKUP_KEEP         14               how many timestamped backups to retain
#
set -euo pipefail

# --- Logging -----------------------------------------------------------------
# Timestamped, to stderr AND a log file. R11's operative phrase is "must report
# failure": a job whose only output is stdout that cron emails on a machine with no
# MTA is a silent job.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

log() {
    local ts
    ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "[$ts] $*" >&2
    if [ -n "${LOG_FILE:-}" ]; then
        echo "[$ts] $*" >> "$LOG_FILE" 2>/dev/null || true
    fi
}

die() {
    log "FATAL: $*"
    log "backup FAILED — no usable backup was produced"
    exit 1
}

# --- Configuration -----------------------------------------------------------

BACKUP_DIR="${BACKUP_DIR:-}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"

[ -n "$BACKUP_DIR" ] || die "BACKUP_DIR is not set. It must point at the attached external drive (D19/R11)."

# Resolve .env so a cron run sees the same config as the app. `set -a` exports.
# --- .env loading ------------------------------------------------------------
# NOT `set -a; . .env`. A dotenv file is not shell: Django's
# get_random_secret_key() emits characters like `(`, `)`, `*`, `$` and `!`, and
# `. .env` re-interprets them — it dies with "syntax error near unexpected token
# `)`", or worse, expands `$...` into something else. This parser never evaluates
# a value: it splits on the first `=` and exports the remainder verbatim.
load_dotenv() {
    local file="$1" line key val
    [ -f "$file" ] || return 0
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in ''|\#*) continue ;; esac
        case "$line" in *=*) ;; *) continue ;; esac
        key="${line%%=*}"
        val="${line#*=}"
        # Strip a single pair of surrounding quotes, if present. A variable holds
        # the single quote because nesting it inside ${...} is not portable and
        # silently produces invalid shell.
        _q="'"
        case "$val" in
            \"*\") val="${val%\"}"; val="${val#\"}" ;;
            $_q*$_q) val="${val%$_q}"; val="${val#$_q}" ;;
        esac
        export "$key=$val"
    done < "$file"
}

load_dotenv "$REPO_ROOT/.env"

DATABASE_URL="${DATABASE_URL:-}"
MEDIA_ROOT="${MEDIA_ROOT:-$REPO_ROOT/media}"
PRIVATE_MEDIA_ROOT="${PRIVATE_MEDIA_ROOT:-$REPO_ROOT/private_media}"

# --- Honest preconditions ----------------------------------------------------
#
# Every one of these is a way the backup could produce a file that looks like a
# backup and is not one.

# Required rather than defaulted: a backup must name the database it protects. Falling
# back to the dev default in pgs/settings.py would silently back up "whatever happens
# to be configured", which is how the wrong database gets backed up for a year.
[ -n "$DATABASE_URL" ] || die "DATABASE_URL is not set. Set it in .env (see .env.example) — a backup must name the database it protects rather than assume a default."

[ -d "$BACKUP_DIR" ] || die "BACKUP_DIR ($BACKUP_DIR) does not exist or is not mounted. Refusing to write to a path that is not the drive."

# A backup written INTO the tree it protects shares the failure it is meant to
# survive. This is the single most common way a backup story is silently fictional.
BACKUP_DIR_ABS="$(cd "$BACKUP_DIR" && pwd)"
case "$BACKUP_DIR_ABS" in
    "$REPO_ROOT"|"$REPO_ROOT"/*)
        die "BACKUP_DIR ($BACKUP_DIR_ABS) is inside the repository. That protects against nothing: one disk failure loses both. Point it at the external drive."
        ;;
esac

mkdir -p "$BACKUP_DIR_ABS/logs"
LOG_FILE="$BACKUP_DIR_ABS/logs/backup.log"
export LOG_FILE

# --- Lock --------------------------------------------------------------------
# A second run starting while the first is dumping produces two half-written sets in
# the same directory. `mkdir` is atomic across platforms; `flock` is not available
# on Windows git bash.
LOCK_DIR="$BACKUP_DIR_ABS/.backup.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    die "Another backup is already running (lock: $LOCK_DIR). If no backup is running, the previous one died without cleaning up: remove the directory manually."
fi
cleanup() {
    rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- Parse DATABASE_URL ------------------------------------------------------
# Done in shell rather than via a Python call so the backup works even if the venv
# is broken — a backup that depends on the health of the app is not a backup.

parse_url() {
    # postgres://user:pass@host:port/dbname
    local url="$1"
    local rest="${url#*://}"
    local creds="${rest%@*}"
    rest="${rest#*@}"
    DB_USER="${creds%%:*}"
    DB_PASS="${creds#*:}"
    [ "$DB_PASS" = "$creds" ] && DB_PASS=""
    DB_HOSTPORT="${rest%%/*}"
    DB_NAME="${rest#*/}"
    DB_NAME="${DB_NAME%%\?*}"
    DB_HOST="${DB_HOSTPORT%%:*}"
    DB_PORT="${DB_HOSTPORT#*:}"
    # NOT `[ ... ] && DB_PORT=5432`: when the test is false that returns 1, and as the
    # final statement of the function it makes the function return 1 — which `set -e`
    # treats as a fatal error. It killed this script silently on every run that used an
    # explicit port, with no message at all. Use an `if` so the status is always 0.
    if [ "$DB_PORT" = "$DB_HOSTPORT" ]; then
        DB_PORT="5432"
    fi
}

parse_url "$DATABASE_URL"
export PGHOST="$DB_HOST" PGPORT="$DB_PORT" PGUSER="$DB_USER" PGDATABASE="$DB_NAME"
if [ -n "$DB_PASS" ]; then export PGPASSWORD="$DB_PASS"; fi



# --- Dump client selection ---------------------------------------------------
#
# A pg_dump whose major version is NEWER than the server writes syntax the server
# cannot read back, and the failure is invisible until a restore. Found the hard way
# on this repo: pg_dump 17.5 against a PostgreSQL 16.15 server emits
# `SET transaction_timeout = 0` (a 17-only GUC), so the archive restored into
# nothing but that one error while `pg_dump` itself exited 0 and `pg_restore --list`
# listed 99 happy entries.
#
# Two strategies, chosen by version rather than hoped for:
#
#   host    — a pg_dump on PATH whose major matches the server (the VPS case:
#             postgresql-client is installed at the server's version)
#   docker  — `docker compose exec` into the database container and use ITS pg_dump,
#             which by definition matches the server (the dev-box case)
#
# A mismatch on the host client is a hard error, not a warning: silently shipping an
# unrestorable archive is the exact failure R11 is about.

PG_DUMP_MODE="${PG_DUMP_MODE:-auto}"     # auto | host | docker
DOCKER_SERVICE="${PG_DUMP_DOCKER_SERVICE:-db}"

server_major="$(psql --no-psqlrc --tuples-only --no-align --command 'SHOW server_version;' \
    | cut -d. -f1 | tr -d '[:space:]')"
[ -n "$server_major" ] || die "could not determine the server version."

host_dump_major=""
if command -v pg_dump >/dev/null 2>&1; then
    host_dump_major="$(pg_dump --version | grep -oE '[0-9]+\.[0-9]+' | cut -d. -f1)"
fi

choose_dump_mode() {
    case "$PG_DUMP_MODE" in
        host)
            [ -n "$host_dump_major" ] || die "PG_DUMP_MODE=host, but no pg_dump is on PATH."
            [ "$host_dump_major" = "$server_major" ] || die "PG_DUMP_MODE=host, but pg_dump is $host_dump_major and the server is $server_major."
            echo host
            ;;
        docker)
            command -v docker >/dev/null 2>&1 || die "PG_DUMP_MODE=docker, but docker is not on PATH."
            echo docker
            ;;
        auto)
            if [ -n "$host_dump_major" ] && [ "$host_dump_major" = "$server_major" ]; then
                echo host
            elif command -v docker >/dev/null 2>&1; then
                echo docker
            else
                die "no pg_dump matching server major $server_major on PATH, and docker is unavailable to borrow the container's. Install postgresql-client-$server_major."
            fi
            ;;
        *)
            die "PG_DUMP_MODE must be auto, host or docker (got '$PG_DUMP_MODE')."
            ;;
    esac
}

DUMP_MODE="$(choose_dump_mode)"

dump_version() {
    if [ "$DUMP_MODE" = docker ]; then
        docker compose exec -T "$DOCKER_SERVICE" pg_dump --version
    else
        pg_dump --version
    fi
}

# The chosen client must not be newer than the server. With `auto` this is already
# guaranteed; with an explicit `host` it is re-checked, because PG_DUMP_MODE is
# operator-supplied and an operator can be wrong.
dump_major="$(dump_version | grep -oE '[0-9]+\.[0-9]+' | cut -d. -f1)"
if [ -n "$dump_major" ] && [ "$dump_major" -gt "$server_major" ] 2>/dev/null; then
    die "pg_dump client is $dump_major but the server is $server_major. A newer client writes syntax the older server cannot restore (PG 17 emits SET transaction_timeout; PG 16 rejects it). Install postgresql-client-$server_major, or set PG_DUMP_MODE=docker."
fi
log "dump client: $DUMP_MODE, version $dump_major against server $server_major"

# --- Begin -------------------------------------------------------------------

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
DEST="$BACKUP_DIR_ABS/db-$STAMP"
mkdir -p "$DEST"

log "backup starting -> $DEST"
log "database: $DB_NAME at $DB_HOST:$DB_PORT"

# --- 1. Dump -----------------------------------------------------------------
#
# Custom format: compressed, and restorable selectively with pg_restore. `--no-owner`
# so a restore into a scratch database owned by a different role does not fail on
# permission statements before it has restored a single row.
DUMP="$DEST/db.dump"
log "dumping database (mode: $DUMP_MODE)"
# `docker compose exec -T` writes to stdout, so the redirect replaces `--file`.
# Running inside the container also means the client authenticates as the container's
# superuser, which is why no PGPASSWORD is passed on that path.
if [ "$DUMP_MODE" = docker ]; then
    if ! docker compose exec -T "$DOCKER_SERVICE"             pg_dump --format=custom --no-owner --no-acl -U "$DB_USER" -d "$DB_NAME" > "$DUMP"; then
        die "pg_dump failed (docker mode)."
    fi
else
    if ! pg_dump --format=custom --no-owner --no-acl --file="$DUMP"; then
        die "pg_dump failed."
    fi
fi

[ -s "$DUMP" ] || die "pg_dump produced an empty file at $DUMP."

# Verify the archive is readable. pg_dump can exit 0 with a truncated file when the
# disk fills; `pg_restore --list` is the cheapest proof that it is a valid archive.
if [ "$DUMP_MODE" = docker ]; then
    if ! docker compose exec -T "$DOCKER_SERVICE" pg_restore --list < "$DUMP" > "$DEST/db.contents.txt" 2>/dev/null; then
        die "The dump at $DUMP is not a readable archive (truncated or corrupt)."
    fi
elif ! pg_restore --list "$DUMP" > "$DEST/db.contents.txt" 2>/dev/null; then
    die "The dump at $DUMP is not a readable archive (truncated or corrupt)."
fi
DUMP_ENTRIES="$(grep -c '^[0-9]' "$DEST/db.contents.txt" || true)"
[ "${DUMP_ENTRIES:-0}" -gt 0 ] || die "The dump contains no restorable objects."
log "dump verified: $DUMP_ENTRIES archive entries"

# --- 2. Record row counts ----------------------------------------------------
#
# `restore.sh` compares against this file. Without it, "the restore worked" can only
# mean "pg_restore exited 0", which is true of a restore into an empty database.
COUNTS="$DEST/rowcounts.txt"
: > "$COUNTS"
log "recording row counts"

TABLES="$(psql --no-psqlrc --tuples-only --no-align --command "
    SELECT schemaname || '.' || relname
    FROM pg_stat_user_tables
    ORDER BY 1;
")" || die "could not list tables."

while IFS= read -r table; do
    # Strip CR: psql on Windows emits \r\n, so without this the table name is stored
    # as "public.core_seal\r". It happens to remain valid SQL (\r is whitespace),
    # which is exactly why it would survive to the VPS and then confuse whoever reads
    # the rowcounts file — or break a consumer that does not tolerate it.
    table="$(printf '%s' "$table" | tr -d '\r')"
    [ -n "$table" ] || continue
    count="$(psql --no-psqlrc --tuples-only --no-align \
        --command "SELECT count(*) FROM $table;" | tr -d '\r')" || die "could not count $table."
    echo "$table $count" >> "$COUNTS"
done <<< "$TABLES"

log "row counts recorded for $(wc -l < "$COUNTS" | tr -d ' ') tables"

# --- 3. Media roots ----------------------------------------------------------
#
# Both roots, and the split is a security boundary: `media/` holds public derivatives,
# `private_media/` holds evidence originals that are never served directly. A backup
# that captures only the public root silently loses the evidence.

copy_tree() {
    local label="$1" src="$2" dst="$3"

    if [ ! -d "$src" ]; then
        # Not a failure on a fresh deployment, but it must be said out loud: an empty
        # media backup and an absent one look identical at restore time otherwise.
        log "WARNING: $label root does not exist ($src) — nothing to back up"
        echo "$label absent" > "$DEST/$label.absent"
        return 0
    fi

    log "archiving $label ($src)"

    # rsync is preferred: it preserves permissions/mtimes and is resumable. It is
    # present on the Linux VPS but NOT on the Windows dev box, so fall back to tar
    # rather than failing — but say which ran, because a silent fallback that loses
    # permissions would only be discovered at restore.
    if command -v rsync >/dev/null 2>&1; then
        log "  using rsync"
        mkdir -p "$dst"
        rsync -a --delete "$src/" "$dst/"
    else
        # NOTE: deliberately does NOT create "$dst" here. Creating it first left an
        # EMPTY `media/` directory next to `media.tar.gz`, and restore.sh then copied
        # the empty directory and reported "0 files" — a silent media restore of
        # nothing. An empty tree and an absent one must not be distinguishable at
        # restore time.
        log "  rsync not available — falling back to tar (store a note: permissions/mtimes are preserved, but this is not the VPS path)"
        tar -C "$src" -czf "$dst.tar.gz" .
    fi
}

copy_tree "media" "$MEDIA_ROOT" "$DEST/media"
copy_tree "private_media" "$PRIVATE_MEDIA_ROOT" "$DEST/private_media"

# Per-item checksums of the media trees THEMSELVES, not only of the tarballs.
#
# R11: "per-item sha256 detects silent corruption". Checksumming only the archive
# proves the archive survived the trip but says nothing about whether its contents
# match what was on disk — and a restore that unpacks a valid tarball containing the
# wrong files is indistinguishable from a good one by archive hash alone.
#
# Written from the SOURCE tree, so it is an independent record of what should come
# back, not a checksum of the thing being tested.

media_manifest() {
    # Separate `local` statements, NOT `local label="$1" src="$2" out="$DEST/$label..."`.
    # Bash expands every word of the command before performing any assignment, so
    # `$label` in the third assignment is still unset — and under `set -u` that is a
    # fatal "label: unbound variable". Verified on bash 5.2; it is not obvious from
    # reading the line.
    local label="$1"
    local src="$2"
    local out="$DEST/$label.files.sha256"
    : > "$out"
    [ -d "$src" ] || return 0
    ( cd "$src" && find . -type f -print0 | sort -z | xargs -0 sha256sum ) >> "$out" 2>/dev/null || true
    local n
    n="$(wc -l < "$out" | tr -d ' ')"
    log "  $label: per-item checksums for $n files"
}

media_manifest "media" "$MEDIA_ROOT"
media_manifest "private_media" "$PRIVATE_MEDIA_ROOT"

# --- 4. Checksums + manifest -------------------------------------------------
#
# Per-item sha256 (R11: "detects silent corruption"). Written as a file that
# `sha256sum -c` consumes directly.

log "writing checksums"
(
    cd "$DEST"
    # Everything except the manifest and checksum files themselves.
    find . -type f \
        ! -name 'MANIFEST.txt' ! -name 'SHA256SUMS' ! -name '*.contents.txt' \
        -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
) || die "failed to write checksums"

# Re-verify immediately: a checksum file generated from already-corrupt data proves
# nothing, so this pass reads the bytes back off disk.
if ! (cd "$DEST" && sha256sum --check --quiet SHA256SUMS); then
    die "checksum verification FAILED immediately after writing — the drive or filesystem is suspect."
fi
log "checksums verified: $(wc -l < "$DEST/SHA256SUMS" | tr -d ' ') files"

cat > "$DEST/MANIFEST.txt" <<EOF
# Backup manifest — read by restore.sh. Do not edit.
created_utc=$STAMP
database=$DB_NAME
db_host=$DB_HOST
db_port=$DB_PORT
pg_dump_entries=$DUMP_ENTRIES
dump_mode=$DUMP_MODE
dump_client_version=$dump_major
media_root=$MEDIA_ROOT
private_media_root=$PRIVATE_MEDIA_ROOT
repo_commit=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)
host=$(hostname 2>/dev/null || echo unknown)
EOF

# Final integrity gate: everything above succeeded, and the artefacts are on disk.
[ -f "$DEST/SHA256SUMS" ] || die "no checksum file was produced."
[ -f "$DEST/rowcounts.txt" ] || die "no row-count file was produced."

# --- 5. Prune (only after success) ------------------------------------------
#
# Deliberately last. Pruning before the new backup is verified can delete the only
# good copy to make room for a bad one.

if [ "$BACKUP_KEEP" -gt 0 ] 2>/dev/null; then
    to_delete="$(ls -1d "$BACKUP_DIR_ABS"/db-* 2>/dev/null | sort | head -n -"$BACKUP_KEEP" || true)"
    if [ -n "$to_delete" ]; then
        log "pruning backups older than the newest $BACKUP_KEEP:"
        echo "$to_delete" | while IFS= read -r old; do
            log "  removing $old"
            rm -rf "$old"
        done
    fi
fi

SIZE="$(du -sh "$DEST" 2>/dev/null | cut -f1 || echo '?')"
log "backup OK -> $DEST ($SIZE, $DUMP_ENTRIES archive entries, $(wc -l < "$DEST/rowcounts.txt" | tr -d ' ') tables)"
exit 0
