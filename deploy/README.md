# Deploying Outeniqua PGS to the homtini VPS

Target: `organicguarantee.africa` on `carbonplanner@169.239.182.221`
(Ubuntu 24.04, Python 3.12, one systemd unit + one nginx site per app).

| Thing | Value |
|---|---|
| App dir | `/home/carbonplanner/apps/pgs` |
| Units | `pgs_web` (gunicorn) and `pgs_celery` (worker) |
| Bind | unix socket `/home/carbonplanner/apps/pgs/pgs.sock` |
| nginx | `/etc/nginx/sites-available/pgs` |
| DB | Postgres `pgs_db` / `pgs_user`, plus `pgs_verify` for the test gate |
| Redis | logical DBs **7/8/9** (broker / results / cache) |
| Backups | `/home/carbonplanner/backups/pgs` — deliberately **outside** the checkout |
| Cert | `/etc/letsencrypt/live/organicguarantee.africa/` (covers `www`) |

**Every command below runs on the server as the user with the SSH key.** This
machine has no key for that box, so it cannot run them for you.

## 0. Before you start

Two system packages are required on the box — Debian/Ubuntu does not pull either in
with Python, and both fail in ways that look like a code problem:

```bash
sudo apt-get install -y postgresql-16-pgvector   # CREATE EXTENSION vector (migrate)
sudo apt-get install -y postgresql-client-16     # pg_dump 16 (pre-migration backup)
sudo apt-get install -y poppler-utils           # pdftotext (corpus ingest)
```

- **pgvector** — without it `migrate` dies on `CREATE EXTENSION vector`.
- **postgresql-client-16** — `scripts/backup.sh` refuses a `pg_dump` whose major version
  differs from the server, and `deploy.sh` refuses to migrate without a verified backup.
  The client is easy to miss: a box provisioned with the *server* package can still have
  no matching client on `PATH`, and the deploy then dies at step 3/8 ("no pg_dump matching
  server major 16") on a site that otherwise looks healthy. Install the client named after
  the server's major, not whatever `apt` suggests.
- **poppler-utils** — without it the site installs and serves perfectly but the
  corpus can never be ingested, so `/ask/` refuses every question. (Since D57 the *gate*
  no longer needs it; the artefact build and a PDF-path ingest still do.) `first-install.sh`
  checks for both before doing any work and names the missing package.

DNS must already resolve, or certbot fails at step 6 of the install:

```bash
dig +short organicguarantee.africa      # must print 169.239.182.221
dig +short www.organicguarantee.africa  # must print 169.239.182.221
```

## 1. Is this a first install or a redeploy?

```bash
ls /etc/systemd/system/pgs_web.service
```

- **Not found** → first install (§2).
- **Found** → redeploy (§3).

## 2. First install

One command. Root-run, idempotent — if it stops halfway, fix what it names and
run it again.

```bash
sudo bash /home/carbonplanner/apps/pgs/deploy/first-install.sh
```

If `/home/carbonplanner/apps/pgs` does not exist yet, get the code there first:

```bash
sudo -u carbonplanner git clone --branch main \
    https://github.com/KobusWHMeiring/PGS.git /home/carbonplanner/apps/pgs
sudo bash /home/carbonplanner/apps/pgs/deploy/first-install.sh
```

It does, in order: Python gate → clone/pull → venv → generate `.env` with fresh
secrets → Postgres role + databases + the `vector` extension → dependencies →
`migrate`, `seed_deployment`, `publish_documents`, `collectstatic` →
`check --deploy` (fatal) → both systemd units → HTTP placeholder site →
`certbot certonly` → the committed nginx site → health check.

Expected end: `✅ pgs is up — https://organicguarantee.africa/ is serving`.

**If it stops with `pgvector extension is not available`**, install it and re-run:

```bash
sudo apt-get update && sudo apt-get install -y postgresql-16-pgvector
```

### What `.env` looks like (it is generated for you)

```bash
sudo cat /home/carbonplanner/apps/pgs/.env     # mode 600
```

Contains `DJANGO_SECRET_KEY` (64 hex chars), `DJANGO_DEBUG=0`,
`DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, **`DJANGO_TLS=1`**,
`DATABASE_URL`, `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` / `CACHE_URL` on
Redis 7/8/9, and an empty `GEMINI_API_KEY`. The file is never overwritten by a
re-run, so adding secrets to it is safe.

`DJANGO_TLS=1` is not optional: it is what turns on `SECURE_SSL_REDIRECT`, secure
cookies, HSTS and the `X-Forwarded-Proto` trust. Remove it and `check --deploy`
fails, which aborts the deploy before anything restarts — deliberately.

## 3. Redeploy (every release after the first)

```bash
sudo bash /home/carbonplanner/apps/pgs/deploy/deploy.sh
```

Order, and why the order is the safety:

1. fetch `origin/main`, materialise **that commit** into `/tmp`, install its
   requirements, run `scripts/verify.sh` (check + lint-imports + `pytest
   --create-db`) against the `pgs_verify` database with **no `.env`** — the only
   environment where "green" means anything;
2. only then `git pull --ff-only`, `scripts/backup.sh` (a failed backup aborts),
   `migrate`, `seed_deployment`, `publish_documents`, `collectstatic`,
   `check --deploy`;
3. sync the nginx site and both units from the repo, `nginx -t` with rollback;
4. restart `pgs_celery` **then** `pgs_web`, then poll `/health/` through the
   socket until it reports `"status": "ok"`.

If the gate fails it prints the failing step and **nothing is deployed** — the old
code is still serving and the schema is untouched.

`deploy.sh` re-executes itself if the pull changed it, so new steps in a newer
script actually run.

## 4. Ingest the corpus — once, not per deploy

`/ask/` answers only from an ingested corpus, and ingestion makes embedding calls
(340 chunks at the time of writing), so it is a deliberate step rather than part of
every deploy. It is idempotent on each PDF's sha256.

**Set `GEMINI_API_KEY` first.** Ingesting without it still writes all 340 chunks —
with `embedding = NULL` — and because the sha256 then matches, a later run reports
"already ingested" and writes nothing. Retrieval stays lexical-only until you
re-ingest with `--force`, which is a full re-embed. Check the key is present before
the first ingest:

```bash
sudo grep -c '^GEMINI_API_KEY=.' /home/carbonplanner/apps/pgs/.env   # must print 1
```

```bash
sudo -u carbonplanner bash -c 'set -a; . /home/carbonplanner/apps/pgs/.env; set +a; \
  cd /home/carbonplanner/apps/pgs && venv/bin/python manage.py ingest_standard \
  --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf'

# then, one per document:
#   --doc opp       --file "pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf"
#   --doc bpp       --file "pgs_docs/Basic Production Principles_ENG_PRINT.pdf"
#   --doc landscape --file "pgs_docs/PGS Certification landscape_Final.pdf"
```

Confirm afterwards (expect `340 chunks`, `0 duplicate section_refs`,
`lexical_only=False`):

```bash
sudo -u carbonplanner bash -c 'set -a; . /home/carbonplanner/apps/pgs/.env; set +a; \
  cd /home/carbonplanner/apps/pgs && venv/bin/python manage.py shell -c "
from knowledge.models import DocumentChunk as C
print(C.objects.count(), C.objects.filter(embedding__isnull=True).count())"'
```

Re-run with `--force` only when the corpus itself changed (a parser fix, a curated
table). Without `--force` a second run reports "already ingested" and writes
nothing.

## 5. The API key and the admin user

```bash
# 1. key
sudo -u carbonplanner sed -i 's/^GEMINI_API_KEY=.*/GEMINI_API_KEY=<your key>/' \
    /home/carbonplanner/apps/pgs/.env
sudo systemctl restart pgs_web pgs_celery

# 2. admin (interactive)
sudo -u carbonplanner bash -c 'set -a; . /home/carbonplanner/apps/pgs/.env; set +a; \
  cd /home/carbonplanner/apps/pgs && venv/bin/python manage.py createsuperuser'
```

Without the key `/ask/` degrades honestly (it does not invent an answer); it is not
a 500.

## 6. Pre-exposure gate — run before telling anyone the site is live

```bash
cd /home/carbonplanner/apps/pgs
sudo -u carbonplanner bash -c 'set -a; . .env; set +a; venv/bin/python manage.py check --deploy'
curl -sI https://organicguarantee.africa/ | head -5      # 200, HSTS, no redirect loop
curl -s  https://organicguarantee.africa/health/         # {"status":"ok",...}
curl -sI https://organicguarantee.africa/static/css/site.css | head -3   # 200, not 404
sudo certbot certificates                                 # both names, not expired
```

The site is public by design: `/`, `/organics/`, `/how-it-works/`, `/members/`,
`/documents/`, `/become-a-member/`, `/contact/`, `/ask/`, `/health/`. There is no
login wall to test — but `/admin/` must require one.

## 7. When it breaks

| Symptom | First thing to check |
|---|---|
| `502` from nginx | `systemctl status pgs_web`, then `tail /var/log/gunicorn/pgs_error.log` |
| `400 Bad Request` naming the host | `DJANGO_ALLOWED_HOSTS` in `.env` is missing the name you used (`www.` counts) |
| `400` on a POST only, GETs fine | `CSRF_TRUSTED_ORIGINS` — the origin's scheme must match |
| Infinite redirect / `ERR_TOO_MANY_REDIRECTS` | `SECURE_PROXY_SSL_HEADER` missing while `SECURE_SSL_REDIRECT` is on; nginx must send `X-Forwarded-Proto` |
| `/health/` 503 with `celery_worker: error` | `systemctl status pgs_celery` — the readiness probe needs a responding worker |
| `/health/` 503 with `db: error` | `DATABASE_URL` in `.env`; `sudo -u postgres psql -l` |
| `/static/…` 404 | `collectstatic` did not run, or the nginx alias points at `static/` instead of `staticfiles/` |
| `502` immediately after a deploy | stale `pgs.sock`: `systemctl restart pgs_web` (the unit removes it before binding) |
| certbot says `unauthorized` | DNS not resolving to this box yet, or port 80 blocked |

Logs: `journalctl -u pgs_web -n 100 --no-pager`,
`journalctl -u pgs_celery -n 100 --no-pager`,
`/var/log/gunicorn/pgs_{access,error}.log`.

## 8. Rollback

```bash
# previous code
sudo -u carbonplanner git -C /home/carbonplanner/apps/pgs log --oneline -5
sudo -u carbonplanner git -C /home/carbonplanner/apps/pgs reset --hard <sha>
sudo bash /home/carbonplanner/apps/pgs/deploy/deploy.sh   # re-runs the gate + restarts

# previous database (only alongside a code rollback)
ls /home/carbonplanner/backups/pgs/
DATABASE_URL=... BACKUP_DIR=/home/carbonplanner/backups/pgs \
  sudo -u carbonplanner /home/carbonplanner/apps/pgs/scripts/restore.sh <set-dir>
```

A rollback that reverts code without the schema is fine only when the migration
was additive. Read `restore.sh`'s output — it compares row counts, so "the restore
worked" is a measurement rather than an opinion.

## 9. Why the scripts are shaped this way

- **`DATABASE_URL`, not `DB_NAME`/`DB_PASSWORD`.** `pgs/settings.py` parses one URL
  through `dj-database-url`; four separate variables would be four things to keep in
  sync with a file nobody re-reads. The password is `openssl rand -hex`, so it needs
  no URL-encoding — and `scripts/backup.sh` parses that same URL in shell.
- **Unix socket, not a port.** The box already has other apps' ports; a socket in
  the app dir cannot collide with a neighbour, and nginx is the only client.
- **`pgs_celery` is a real unit, not an afterthought.** `/health/` is a *readiness*
  probe: it returns 503 unless a worker answers `control.ping()`. Redis answering
  `PING` with zero workers consuming is exactly the failure the two checks exist to
  separate.
- **The backup lives outside the checkout**, because `scripts/backup.sh` refuses a
  `BACKUP_DIR` inside the repository — a backup on the disk it protects survives
  nothing.
- **Verification runs before the pull, from `git archive FETCH_HEAD`.** A test that
  runs after `git pull` cannot block a deploy; by then the code is already live.
- **nginx config is in the repo and synced by the deploy.** A committed config that
  nothing copies is a config that exists only in git.
