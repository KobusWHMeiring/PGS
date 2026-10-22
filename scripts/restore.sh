#!/usr/bin/env bash
#
# restore.sh — restore a backup into SCRATCH locations and verify it.
#
# This is a rehearsal tool, not a disaster tool. It deliberately cannot touch the
# live database or the live media roots:
#
#   * the target database is a NEW database named `<source>_restoretest`
#   * the target media roots are a temp directory
#   * it refuses if the target database already exists, rather than overwriting
#
# The reason for that constraint is the acceptance criterion:
#
#   "perform a restore on a clean machine or a fresh database, and record the date
#    and result in docs/RUNBOOK.md"
#
# A rehearsal that runs against production is not a rehearsal — it is an outage with
# extra steps. The only way to know a backup restores is to restore it somewhere
# that does not matter, which is exactly what this does.
#
# Verification is measurement, not opinion:
#
#   1. every artefact's sha256 is checked against the backup's own SHA256SUMS
#   2. `pg_restore` must exit 0 and produce no failed objects
#   3. row counts in the restored database are compared, table by table, against the
#      `rowcounts.txt` recorded at backup time
#   4. a sampled media file's sha256 is compared against the checksum list
#
# A restore that "worked" but brought back half the rows is the failure mode this
# exists to catch. `pg_restore` exiting 0 does not mean the data is there.
#
# Usage:
#   ./scripts/restore.sh /mnt/backup-drive/db-20261019T101500Z
#
# Exit codes: 0 = the backup is proven restorable, non-zero = it is not.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" >&2
}

die() {
    log "FATAL: $*"
    log "restore FAILED — this backup is NOT proven restorable"
    exit 1
}

# --- Arguments ---------------------------------------------------------------

BACKUP_SRC="${1:-}"
[ -n "$BACKUP_SRC" ] || die "usage: restore.sh <backup-dir>   (e.g. /mnt/backup-drive/db-20261019T101500Z)"
[ -d "$BACKUP_SRC" ] || die "backup directory not found: $BACKUP_SRC"

BACKUP_SRC="$(cd "$BACKUP_SRC" && pwd)"
[ -f "$BACKUP_SRC/MANIFEST.txt" ] || die "$BACKUP_SRC/MANIFEST.txt missing — not a backup directory produced by backup.sh."
[ -f "$BACKUP_SRC/SHA256SUMS" ] || die "$BACKUP_SRC/SHA256SUMS missing — cannot verify integrity."
[ -f "$BACKUP_SRC/rowcounts.txt" ] || die "$BACKUP_SRC/rowcounts.txt missing — cannot verify that rows came back."

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
[ -n "$DATABASE_URL" ] || die "DATABASE_URL is not set (needed to reach the server)."

# --- Parse URL ---------------------------------------------------------------

rest="${DATABASE_URL#*://}"
creds="${rest%@*}"; rest="${rest#*@}"
DB_USER="${creds%%:*}"; DB_PASS="${creds#*:}"
[ "$DB_PASS" = "$creds" ] && DB_PASS=""
DB_HOSTPORT="${rest%%/*}"; DB_NAME="${rest#*/}"; DB_NAME="${DB_NAME%%\?*}"
DB_HOST="${DB_HOSTPORT%%:*}"; DB_PORT="${DB_HOSTPORT#*:}"
# `if`, not `[ ... ] &&`: when the test is false it returns 1, and under `set -e`
# that aborts the script with no message (see the same fix in backup.sh).
if [ "$DB_PORT" = "$DB_HOSTPORT" ]; then
    DB_PORT="5432"
fi

export PGHOST="$DB_HOST" PGPORT="$DB_PORT" PGUSER="$DB_USER"
if [ -n "$DB_PASS" ]; then export PGPASSWORD="$DB_PASS"; fi

TARGET_DB="${DB_NAME}_restoretest"

log "restoring $BACKUP_SRC"
log "source database: $DB_NAME   target (scratch): $TARGET_DB"

# --- Refuse to clobber -------------------------------------------------------
#
# If the scratch database already exists it may hold the result of an earlier
# rehearsal someone is still looking at — or, if this were ever misconfigured, a
# database that matters. Either way: stop and let the operator decide.

exists="$(psql --no-psqlrc --tuples-only --no-align -d postgres \
    --command "SELECT 1 FROM pg_database WHERE datname = '$TARGET_DB';")"
if [ "$exists" = "1" ]; then
    die "scratch database '$TARGET_DB' already exists. Drop it first if you are sure: DROP DATABASE $TARGET_DB;"
fi

# --- 1. Verify artefact integrity -------------------------------------------

log "1/4  verifying sha256 of every artefact"
if ! (cd "$BACKUP_SRC" && sha256sum --check --quiet SHA256SUMS); then
    die "checksum verification failed — the backup is corrupt on disk. Do not restore it; check the drive."
fi
log "     $(wc -l < "$BACKUP_SRC/SHA256SUMS" | tr -d ' ') files verified"

# --- 2. Restore media to a scratch root -------------------------------------

SCRATCH_MEDIA="$(mktemp -d "${TMPDIR:-/tmp}/pgs-restore-media-XXXXXX")"
log "2/4  restoring media to scratch root $SCRATCH_MEDIA"

restore_tree() {
    local label="$1"
    if [ -f "$BACKUP_SRC/$label.absent" ]; then
        log "     $label was absent in the source — nothing to restore"
        return 0
    fi
    local src="$BACKUP_SRC/$label"
    local tarball="$BACKUP_SRC/$label.tar.gz"

    # The tarball wins when both are present. An earlier backup.sh created an empty
    # "$label/" directory before choosing tar, so the backup contained BOTH an empty
    # directory and a populated tarball — and preferring the directory restored zero
    # files while reporting success. Evidence beats a directory listing.
    mkdir -p "$SCRATCH_MEDIA/$label"
    if [ -f "$tarball" ]; then
        tar -xzf "$tarball" -C "$SCRATCH_MEDIA/$label"
    elif [ -d "$src" ]; then
        cp -a "$src/." "$SCRATCH_MEDIA/$label/"
    else
        log "     $label not present in backup"
        return 0
    fi

    local n
    n="$(find "$SCRATCH_MEDIA/$label" -type f | wc -l | tr -d ' ')"
    log "     $label restored: $n files"
    echo "$n" > "$SCRATCH_MEDIA/$label.filecount"

    # A media tree that existed in the source must not come back empty. This is the
    # check that would have caught the empty-directory bug immediately.
    if [ ! -f "$BACKUP_SRC/$label.absent" ] && [ "$n" -eq 0 ]; then
        die "$label restored 0 files, but the backup does not record it as absent. Refusing to call this a successful restore."
    fi
}

restore_tree "media"
restore_tree "private_media"

# --- 3. Restore the database into a scratch database ------------------------

# --- Restore client selection ------------------------------------------------
#
# The mirror of the trap in backup.sh: a pg_restore NEWER than the server emits
# `SET transaction_timeout = 0` (a PG 17 GUC) and PG 16 rejects it, so the restore
# dies on the preamble having restored nothing. `--exit-on-error` makes that an
# honest failure rather than a partial restore, but the fix is a matching client.
# Prefer the host client when its major matches the server, else borrow the
# database container's.
PG_RESTORE_MODE="${PG_RESTORE_MODE:-auto}"
DOCKER_SERVICE="${PG_DUMP_DOCKER_SERVICE:-db}"

server_major="$(psql --no-psqlrc --tuples-only --no-align -d postgres \
    --command 'SHOW server_version;' | cut -d. -f1 | tr -d '[:space:]')"
[ -n "$server_major" ] || die "could not determine the server version."

host_restore_major=""
if command -v pg_restore >/dev/null 2>&1; then
    host_restore_major="$(pg_restore --version | grep -oE '[0-9]+\.[0-9]+' | cut -d. -f1)"
fi

case "$PG_RESTORE_MODE" in
    host)
        [ -n "$host_restore_major" ] || die "PG_RESTORE_MODE=host, but no pg_restore is on PATH."
        RESTORE_MODE=host
        ;;
    docker)
        command -v docker >/dev/null 2>&1 || die "PG_RESTORE_MODE=docker, but docker is not on PATH."
        RESTORE_MODE=docker
        ;;
    auto)
        if [ -n "$host_restore_major" ] && [ "$host_restore_major" = "$server_major" ]; then
            RESTORE_MODE=host
        elif command -v docker >/dev/null 2>&1; then
            RESTORE_MODE=docker
        else
            die "no pg_restore matching server major $server_major on PATH, and docker is unavailable."
        fi
        ;;
    *)
        die "PG_RESTORE_MODE must be auto, host or docker."
        ;;
esac

log "3/4  creating scratch database $TARGET_DB and restoring"
if [ "$RESTORE_MODE" = docker ]; then
    log "     client: docker exec $DOCKER_SERVICE pg_restore (server major $server_major)"
else
    log "     client: $(pg_restore --version)"
fi
psql --no-psqlrc -d postgres --command "CREATE DATABASE $TARGET_DB;" >/dev/null \
    || die "could not create scratch database $TARGET_DB."

# `--exit-on-error` because pg_restore otherwise reports success while having
# skipped objects it could not create — the exact silent-partial-restore this whole
# script exists to detect.
RESTORE_FAILED=0
if [ "$RESTORE_MODE" = docker ]; then
    # The archive is piped in on stdin: the container cannot see the host's file.
    if ! docker compose exec -T "$DOCKER_SERVICE" \
            pg_restore --no-owner --no-acl --exit-on-error \
            -U "$DB_USER" -d "$TARGET_DB" < "$BACKUP_SRC/db.dump" \
            > "$SCRATCH_MEDIA/pg_restore.log" 2>&1; then
        RESTORE_FAILED=1
    fi
elif ! pg_restore --no-owner --no-acl --exit-on-error --dbname="$TARGET_DB" \
        "$BACKUP_SRC/db.dump" > "$SCRATCH_MEDIA/pg_restore.log" 2>&1; then
    RESTORE_FAILED=1
fi

if [ "$RESTORE_FAILED" = "1" ]; then
    tail -20 "$SCRATCH_MEDIA/pg_restore.log" >&2
    psql --no-psqlrc -d postgres --command "DROP DATABASE IF EXISTS $TARGET_DB;" >/dev/null 2>&1 || true
    die "pg_restore failed. See $SCRATCH_MEDIA/pg_restore.log"
fi
log "     pg_restore exited 0 with --exit-on-error"

# --- 4. Compare row counts, table by table ----------------------------------

log "4/4  comparing row counts against the manifest"
failures=0
checked=0

while read -r table expected; do
    # Tolerate a CRLF rowcounts.txt written on Windows (see backup.sh). A stray 
    # would otherwise become part of the table name in the count query.
    table="$(printf '%s' "${table:-}" | tr -d '')"
    expected="$(printf '%s' "${expected:-}" | tr -d '')"
    [ -n "${table:-}" ] || continue
    actual="$(psql --no-psqlrc --tuples-only --no-align -d "$TARGET_DB" \
        --command "SELECT count(*) FROM $table;" 2>/dev/null)" || {
        log "     MISSING TABLE $table (expected $expected rows)"
        failures=$((failures + 1))
        continue
    }
    checked=$((checked + 1))
    if [ "$actual" != "$expected" ]; then
        log "     ROW COUNT MISMATCH $table: expected $expected, restored $actual"
        failures=$((failures + 1))
    fi
done < "$BACKUP_SRC/rowcounts.txt"

log "     $checked tables compared, $failures mismatches"

# A zero-table comparison would otherwise "pass" vacuously — the same class of
# failure as an empty parametrized test (testing_hazards.md §1.6).
if [ "$checked" -eq 0 ]; then
    failures=$((failures + 1))
    log "     FAIL: zero tables were compared, so nothing was actually verified"
fi

# --- Media verification ------------------------------------------------------
#
# Every restored file is checked against the per-item manifest recorded from the
# SOURCE tree at backup time (`<label>.files.sha256`). This is R11's "per-item
# sha256 detects silent corruption", and it is the only check that proves the media
# came back as the same *bytes* rather than merely the same count.
#
# An earlier version spot-checked one file by grepping SHA256SUMS and, finding no
# match (the archive was checksummed, not its contents), printed "skipped" and passed
# anyway — a vacuous check reporting success, which is worse than none.

verify_media() {
    local label="$1"
    local manifest="$BACKUP_SRC/$label.files.sha256"

    if [ ! -f "$manifest" ]; then
        log "     $label: no per-item manifest in this backup (older format) — skipped"
        return 0
    fi

    local expected
    expected="$(wc -l < "$manifest" | tr -d ' ')"
    if [ "$expected" -eq 0 ]; then
        log "     $label: manifest lists 0 files — nothing to verify"
        return 0
    fi

    local restored_dir="$SCRATCH_MEDIA/$label"
    if [ ! -d "$restored_dir" ]; then
        log "     $label: MANIFEST LISTS $expected FILES BUT NOTHING WAS RESTORED"
        return 1
    fi

    if ! ( cd "$restored_dir" && sha256sum --check --quiet "$manifest" ); then
        log "     $label: PER-ITEM CHECKSUM MISMATCH — restored media differs from the source"
        return 1
    fi

    log "     $label: all $expected per-item checksums verified"
    return 0
}

verify_media "media" || failures=$((failures + 1))
verify_media "private_media" || failures=$((failures + 1))

# --- Verdict -----------------------------------------------------------------

if [ "$failures" -ne 0 ]; then
    log ""
    log "The scratch database $TARGET_DB has been LEFT IN PLACE for inspection."
    log "Drop it when done: psql -d postgres -c 'DROP DATABASE $TARGET_DB;'"
    die "$failures verification failure(s). This backup did not restore faithfully."
fi

# Success cleans up after itself: a rehearsal that leaves debris gets avoided.
psql --no-psqlrc -d postgres --command "DROP DATABASE $TARGET_DB;" >/dev/null 2>&1 \
    || log "WARNING: could not drop scratch database $TARGET_DB — drop it manually."
rm -rf "$SCRATCH_MEDIA"

log ""
log "✅ restore VERIFIED: $checked tables matched, media checksums matched"
log "   Record this rehearsal in docs/RUNBOOK.md (date, backup used, result)."
exit 0
