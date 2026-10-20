# Deployment: organicguarantee.africa on the homtini VPS

**Status:** In Progress — live and serving; admin user, verification pass and UAT sign-off outstanding
**Owner:** Deployment (the D19 cutover, pulled forward)
**Last Updated:** 2026-10-20
**MVP:** Deploys the **MVP 0 surface** — public site, `/documents/`, grounded `/ask/` —
to the VPS that D19 had scheduled for MVP 2.
**Reference:** `deploy/README.md` (the runbook), `deploy/first-install.sh`,
`deploy/deploy.sh`, `deploy/pgs_web.service`, `deploy/pgs_celery.service`,
`deploy/nginx.conf`, `deploy/psql_setup.sql`, `pgs/settings.py` (the TLS block),
`scripts/verify.sh`.
**Live:** <https://organicguarantee.africa> and `www`, commit `3a46b1a` at first install.

---

## 1. What is live, and the evidence for it

| Thing | State |
|---|---|
| First install | Completed end to end: `[1/9]`–`[9/9]`. `check --deploy --fail-level WARNING` clean (one warning silenced by id). |
| Schema | `migrate` applied 25 migrations to an empty `pgs_db`. |
| Seed data | `seed_deployment`: 1 standard set, 3 seals, 7 categories. |
| Documents | `publish_documents`: 8 rows, 8 files copied; `/documents/<code>/` streams them. |
| Static | `collectstatic`: 146 files to `staticfiles/`. |
| TLS | certbot, both names, `/etc/letsencrypt/live/organicguarantee.africa/`, expires **2027-01-18**. |
| Corpus | 4 governed documents ingested, every one `embedded=True`: SAOSO 288 + OPP 29 + BPP 16 + landscape 7 = **340 chunks**. |
| Processes | `pgs_web` (gunicorn, 3 workers, unix socket) and `pgs_celery` (2 concurrency). |
| Database | `pgs_db` / `pgs_verify`, role `pgs_user` (with `CREATEDB` for the test gate), pgvector 0.6.0. |
| Redis | logical DBs **7/8/9** reserved for this app. |

## 2. What had to be fixed to get there

Each of these stopped an install or a deploy, and each is now fixed in the repo and
recorded in the `deploy-vps` skill so the next app does not rediscover it:

1. `mktemp` + `sudo -u postgres psql -f` — the file was root-owned 0600, so postgres
   could not read it. Now the SQL is piped into psql (7864eb6).
2. `DOCS_SOURCE_DIR = Path("pgs_docs")` resolved against the process CWD; systemd's
   working directory is not the `~` that `sudo bash …first-install.sh` inherits. Now
   anchored to `settings.BASE_DIR`, and `run_manage` chdirs (148f7e2).
3. `http2 on;` is nginx 1.25.1+; the box runs 1.24. Now `listen 443 ssl http2` (85ef8af).
4. `pdftotext` (poppler-utils) is not installed on the box and nothing declared it. Now
   a pre-flight check in `first-install.sh` (3a46b1a).
5. `manage.py check --deploy` exits 0 by default (`--fail-level` is `ERROR`; every
   security check is a warning). Both scripts now pass `--fail-level WARNING`;
   `security.W021` is declined and silenced **by id**. Recorded as
   `testing_hazards.md` §2.5 — this one is a class of bug, not an incident.
6. Gating the TLS settings on `not DEBUG` broke 86 tests under Django's forced
   `DEBUG=False`, and passed only because a dev shell exported `DJANGO_DEBUG=True`.
   Now an explicit `DJANGO_TLS=1` deployment fact, and `check --deploy` fails closed
   without it.

## 3. Why this is not in `Done/`

- **No superuser yet.** `createsuperuser` has not been run on the box, so `/admin/`
  has no account (it does correctly answer `302 → /login/`).
- **The verification pass has not been run**: the eight public routes over TLS, the
  `/health/` body, a `/static/` asset, and `scripts/probe_chat.py` against the live
  corpus. Without those, "the site works" is inferred from the install script's own
  socket health check, which is necessary but not sufficient.
- **The redeploy path is unexercised.** `deploy/deploy.sh` — gate → backup → migrate →
  sync → restart → health — has never run on the box. Two things in it are untested
  there: `pytest --create-db` needs `vector` creatable in `test_pgs_verify` (pgvector
  0.6.0 is trusted or it is not; `grep '^trusted' …/vector.control` decides), and the
  backup step needs `/home/carbonplanner/backups/pgs` outside the checkout.
- **D's UAT scenarios 1, 2, 3, 9 and 10 are unsigned**, and C1 and D were both already
  partial. The MVP 0 completion criteria are not met.
- **The decision log entry is missing** (see §4).

## 4. The decision this makes, recorded here because the spec was busy

`PGS_PLATFORM_SPEC.md` §18.3 was being edited in another session while this deployment
landed, so the decision is recorded here rather than half-merged into it. **This must
be moved into §18.3 as D54, verbatim or amended:**

> **D54 — the VPS cutover happens now, not at MVP 2.**
>
> D19 records MVP 0 as "a local preview with no public host" and moves the VPS cutover
> to MVP 2. On 2026-10-20 the MVP 0 surface — public site, `/documents/`, grounded
> `/ask/` — was deployed to the homtini VPS at `organicguarantee.africa`, so the
> product owner can show the group a real address rather than a local preview.
>
> Consequences, recorded rather than absorbed: the public surface is reachable by
> anyone from 2026-10-20, so the claim discipline that `test_claim_discipline.py`
> enforces now protects a live site, not a demo; `/ask/` spends real Gemini budget on
> real visitors and its per-IP limit is a production setting; a deployment bug is an
> outage rather than a failed preview; and D19's "no public host" premise is
> superseded — MVP 2's remaining content is the PWA and the cutover of the old
> WordPress redirects onto this host, not standing the host up.

## 5. Operating notes

- **Redeploy:** `sudo bash /home/carbonplanner/apps/pgs/deploy/deploy.sh`. The gate runs
  on a clean tree of `origin/main` before anything is touched.
- **Logs:** `journalctl -u pgs_web`, `journalctl -u pgs_celery`,
  `/var/log/gunicorn/pgs_{access,error}.log`.
- **Health:** <https://organicguarantee.africa/health/> — 503 when the database, Redis
  or a Celery worker is down. `celery_worker` and `celery_broker` are separate on
  purpose; Redis answers `PING` with no workers consuming.
- **Backups:** `/home/carbonplanner/backups/pgs`, pre-migration, outside the checkout.
- **Corpus:** ingestion is a documented manual step, idempotent on each PDF's sha256,
  and must not be run before `GEMINI_API_KEY` is set — an unkeyed run still writes the
  chunks, with `embedding = NULL`, and the next run then reports "already ingested".
  `--force` is the only way back.
