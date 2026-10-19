# RUNBOOK — Outeniqua PGS operations

**Status:** Living document. Update it when you run a rehearsal or a deploy.
**Audience:** whoever is on the server. Assume they did not write the code.

---

## 1. Backups (R11 — High risk)

R11, verbatim from the spec:

> Filesystem media is the only copy of evidentiary photos and PDFs; disk failure, a
> botched deploy, or silent backup failure destroys certification evidence.
> **Critically: the backup job must report failure** — a cron that dies quietly is
> worse than no cron.

### 1.1 What is backed up

| Item | Source | Why it matters |
|---|---|---|
| Database | `pg_dump` (custom format) | Every record: farms, visits, verdicts, members |
| `media/` | public derivatives | Public site images |
| `private_media/` | evidence originals | **The photographs and documents that justify a certificate.** Never served directly. |
| Row counts | recorded per table | So a restore can be *verified*, not assumed |
| `sha256` per item | both the artefacts and each media file | Detects silent corruption |

The two media roots are a security boundary, not tidiness: a backup that captures
only `media/` silently loses the evidence.

### 1.2 Running a backup by hand

```bash
cd ~/apps/pgs
DATABASE_URL=... BACKUP_DIR=/mnt/backup-drive ./scripts/backup.sh
```

`BACKUP_DIR` **must** be the attached external drive. The script refuses to run if it
is unset, missing, or inside the repository — a backup on the same disk as the data
protects against nothing.

The script exits non-zero on any failure and writes a timestamped line to both stderr
and `$BACKUP_DIR/logs/backup.log`.

### 1.3 Scheduling it — and making failure visible

`cron` alone is not enough: a failing job mails root, and on a box with no MTA that
mail goes nowhere. **The failure has to be surfaced somewhere a human looks.**

Preferred: a systemd timer, so `OnFailure` can alert.

```ini
# /etc/systemd/system/pgs-backup.service
[Unit]
Description=PGS backup to external drive
OnFailure=pgs-alert@%n.service

[Service]
Type=oneshot
User=pgs
WorkingDirectory=/home/pgs/apps/pgs
EnvironmentFile=/home/pgs/apps/pgs/.env
Environment=BACKUP_DIR=/mnt/backup-drive
ExecStart=/home/pgs/apps/pgs/scripts/backup.sh
```

```ini
# /etc/systemd/system/pgs-backup.timer
[Unit]
Description=Nightly PGS backup

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with `systemctl enable --now pgs-backup.timer`.

**Verify the timer actually fires** (`systemctl list-timers pgs-backup`) and that a
failed run produces a visible alert. An untested alert path is the same as no alert.

### 1.4 Retention

`BACKUP_KEEP` (default **14**) backups are retained. Pruning runs **only after a
verified success**, so a failed backup cannot delete the last good one to make room
for itself.

### 1.5 The PostgreSQL client version trap

A `pg_dump` client **newer** than the server writes syntax the server cannot read back.
Concretely: `pg_dump` 17 against a PostgreSQL 16 server emits
`SET transaction_timeout = 0`, a 17-only GUC, so the archive restores into nothing but
that error — while `pg_dump` exits 0 and `pg_restore --list` lists every entry.

Both scripts handle this by selecting a client whose major version matches the server:

| `PG_DUMP_MODE` / `PG_RESTORE_MODE` | Behaviour |
|---|---|
| `auto` (default) | host client if its major matches the server, else `docker compose exec` into the `db` container and use **its** client |
| `host` | require a matching host client, fail otherwise |
| `docker` | always borrow the container's client |

Install `postgresql-client-<server major>` on the VPS so `auto` picks the host path and
the backup does not depend on Docker running.

---

## 2. Restoring (the rehearsal)

`restore.sh` is a **rehearsal** tool. It never writes to the live database or the live
media roots: it restores into a scratch database named `<source>_restoretest` and a
temporary media directory, verifies, then cleans up. A rehearsal that runs against
production is not a rehearsal.

```bash
./scripts/restore.sh /mnt/backup-drive/db-20261019T104811Z
```

It verifies, in order:

1. **Every artefact's `sha256`** against the backup's own `SHA256SUMS`.
2. **`pg_restore --exit-on-error`** — without that flag, `pg_restore` reports success
   while having skipped objects it could not create.
3. **Row counts, table by table**, against the `rowcounts.txt` recorded at backup time.
   This is the check that catches a restore that "worked" and brought back half the rows.
4. **Every media file's `sha256`** against the per-item manifest recorded from the
   source tree.

Exit 0 means the backup is *proven* restorable. Non-zero means it is not — and the
scratch database is deliberately left in place for inspection.

### 2.1 Rehearsal log

**This section is A9's acceptance criterion. Append a row every time you rehearse.**

| Date (UTC) | Operator | Backup used | Tables | Media files | Result | Notes |
|---|---|---|---|---|---|---|
| 2026-10-19 | pi (agent) | `db-20261019T104811Z` | 13/13 matched | 3/3 checksums | ✅ **PASS** | Dev box, compose Postgres 16.15 on host port 5433, `PG_RESTORE_MODE=auto` → docker client. Full cycle: backup → mutate → restore → verified. |

> **Note on the first entry:** it was performed on the development box against the
> Compose database, not on the VPS against the production database. That proves the
> *scripts* work and that the verification gates fire. It does **not** prove the VPS's
> drive, permissions, or `postgresql-client` version are correct. **A rehearsal must be
> repeated on the server before launch** — R11 calls for it, and the failure modes that
> only appear there (mount not present, wrong client major, permissions on the external
> drive) are exactly the ones worth finding early.

### 2.2 What was proven by mutation

The gates were tested by deliberately breaking backups, because an unrestorable backup
is the failure R11 exists to prevent and a check that has never failed is not a check:

| Mutation | Caught by | Result |
|---|---|---|
| Corrupt bytes appended to `media.tar.gz` | artefact `sha256` (gate 1) | ✅ failed, exit 1 |
| `rowcounts.txt` altered to expect 999 seals (checksums recomputed, so gate 1 passes) | row-count comparison (gate 3) | ✅ `ROW COUNT MISMATCH public.core_seal: expected 999, restored 3`, exit 1 |

Bugs found while building this, each of which silently produced an unusable backup:

1. **Media restored as zero files.** `backup.sh` created an empty `media/` directory
   before choosing tar, so the backup contained *both* an empty directory and a
   populated `media.tar.gz`; `restore.sh` preferred the directory. Media was backed up
   and then silently not restored.
2. **`pg_dump` 17 vs server 16.** The archive was unreadable by the server, with a
   completely healthy-looking dump. Now detected up front.
3. **`set -e` + `[ cond ] && assignment`.** When the test was false, that returned 1,
   and as the function's last statement it aborted the script **silently, with no
   output**. Both scripts use `if` blocks now.
4. **CRLF in `rowcounts.txt`.** psql on Windows emits `\r`, so table names were stored
   as `public.core_seal\r`. It stayed valid SQL by accident, which is why it would
   have reached the VPS unnoticed.
5. **`local a="$1" b="$2" c="$a"`** — bash expands every word before assigning, so `$a`
   is unset and `set -u` aborts. Separate `local` statements.

---

## 3. Deploying

`deploy.sh` is **staged for later**: MVP 0 is a local preview (D19) and the VPS cutover
is MVP 2. The script refuses to run anywhere it does not recognise as the server.

When it does run, it verifies **before touching the live tree**: it clones the pushed
commit into a scratch directory, runs `scripts/verify.sh` there with no `.env`, and
only then pulls, migrates, collects static and restarts. It checks `/health/` afterwards
and fails the deploy if the site is not healthy.

---

## 4. Health checks

`GET /health/` returns `200` when everything is up and `503` when anything is not.

```json
{"status": "ok", "checks": {"db": "ok", "redis": "ok",
                            "celery_broker": "ok", "celery_worker": "ok"}}
```

`celery_broker` and `celery_worker` are **different checks on purpose**: Redis answers
`PING` with zero workers consuming, so a broker-only check reports a healthy system
while every background task sits in a queue nobody drains.

A worker with an **empty task registry** still answers pings — see
`product/docs/context/testing_hazards.md` §1.5. If `celery_worker` is `ok` but tasks
never run, check the worker's `[tasks]` banner at startup.

---

## 5. Test hazard index

Before debugging anything that "should work", read
`product/docs/context/testing_hazards.md`. Every silent failure found so far — green
tests that proved nothing, tools that report success while enforcing nothing, and
four of this box's own quirks — is recorded there with evidence.
