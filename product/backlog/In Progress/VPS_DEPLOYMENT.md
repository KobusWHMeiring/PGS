# Deployment: organicguarantee.africa on the homtini VPS

**Status:** In Progress — **redeploy path exercised 2026-10-22** (six runs; four deploy-blocking defects found and
fixed, listed below). Live at `206f35f`; two commits ahead pending one more deploy. Admin user and the
corpus refresh from artefacts (plan P7.4) outstanding.
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
- ~~**D's UAT scenarios 1, 2, 3, 9 and 10 are unsigned**~~ — **signed 2026-10-21** by the
  product owner (9 PASS · 1 N/A, applied by `uat_signoff.py`). The PGS administrator,
  committee reviewer and consumer member seats are still empty, so the OPP's three-voice
  requirement is not met and C1 and D stay *partial* on that count alone.
- **The deployed corpus and the deployed chat budget both predate the 2026-10-22 fixes.**
  `deploy.sh` never runs `ingest_standard`, so the live corpus is the pre-D52/D53 text (366
  chunks locally, fewer on the box), and the box's `.env` — if it sets
  `CHAT_RETRIEVAL_LIMIT` at all — still carries the old value. Check it after the next
  deploy: `sudo grep CHAT_RETRIEVAL_LIMIT /home/carbonplanner/apps/pgs/.env`. Eight is the
  live budget (`testing_hazards.md` §2.7); at five the cardboard question refuses.
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

## 4a. First real redeploy, 2026-10-22 — what it cost, and what it proved

Six runs of `deploy.sh` before a green one. Every failure was in the *deploy path*, not the
app, and every one had been invisible because the script had never run:

| # | Failure | Fix |
|---|---|---|
| 1 | `./scripts/verify.sh: Permission denied` | three scripts committed `100644`; `git archive` uses the index mode. Fixed in the index; `verify.sh` now checks it (hazard §2.8) |
| 2 | `git pull --ff-only` refused — "have diverged, 57 and 1" | the deploy's own `git fetch --depth 1` wrote a shallow graft into the live checkout. Fetch full, unshallow first (hazard §2.10) |
| 3 | gate failed: 15 failed, 61 errors | poppler 24.02 vs the Xpdf 4.00 the goldens were measured on. The gate now reads committed page fixtures and runs with a poisoned `PDFTOTEXT_BIN` (plan P1, hazard §2.9) |
| 4 | `no pg_dump matching server major 16 on PATH` (client 16.15 was on PATH) | the version parse took every `grep -oE` match on Ubuntu's four-number banner, so the comparison never matched (hazard §2.11) |
| 5 | `migrate` warned "models have changes not yet reflected in a migration" | D54's `CITATION_AUDIT` choice had no migration. `core/0005` added; `verify.sh` now runs `makemigrations --check` |
| 6 | twenty `collectstatic` duplicate-destination warnings per deploy | `STATICFILES_DIRS` listed `core/static`, which is already an app directory. Removed; 147 files either way |

**Result:** gate green on the box at **803 tests / 63 s**, backup verified (172 archive
entries, 21 tables, media + private_media checksums), migrate/seed/publish/static/`check
--deploy`/restart, and `/health/` `ok` on the second attempt (the worker is restarted first;
the first check is expected to 503).

**State after it:** live `206f35f`; `fb41a47` (migration `0005` + static) and `54ef082`
(poppler attribution) are pushed and **not yet deployed**. The corpus is the pre-D52/D53
poppler build: **363 chunks**, 316 of them SAOSO where Xpdf builds 319 — so `uat_seed --check`
*correctly* reports `corpus present` as blocking until plan P7.4 rebuilds it from artefacts.

## 4b. Second redeploy and the corpus refresh, 2026-10-22 — clean, and one doc claim disproved

`f4e8907` deployed with no failures. What it proved, and the one surprise:

| Step | Result |
|---|---|
| Gate on the box (clean scratch tree) | **804 passed / 67 s** — matches the dev box exactly |
| Pull | `fb41a47..f4e8907`, **five** commits |
| migrate | **"No migrations to apply."** — see below |
| collectstatic | 2 copied, 145 unmodified, **no duplicate-destination warnings** (§4a item 6 holding) |
| backup | 172 archive entries, 21 tables, 12 files checksummed |
| `check --deploy` | no issues, 1 silenced |
| `/health/` | 503 once (`celery_worker: error` — the worker restarts first), `ok` on retry |

**The surprise, recorded because the docs caused it:** §4a above said live was `206f35f` and
`fb41a47` was undeployed. It was not — the pull was `fb41a47..f4e8907`, so a deploy had already
landed `fb41a47` and `core.0005` with it, and `migrate` correctly had nothing to do. The lesson is
the ordinary one: a handover's "state after it" line is true at the moment it is written and is not
maintained by anything.

### 4b.1 Corpus rebuilt from the current pipeline (D52/D53) — `--force`, once

`ingest_standard --doc <doc> --file <pdf> --force` for all four, run as `carbonplanner` with
`deploy.sh`'s environment. Every document re-embedded; the old chunks and their
`retrieved_chunks` links were destroyed in the same transaction.

| Document | Box (poppler 24.02) | Dev box (Xpdf 4.00) |
|---|---|---|
| SAOSO | 311 | 319 |
| OPP | 29 | 30 |
| BPP | 16 | 9 |
| landscape | 8 | 8 |
| **total** | **364** | **366** |

All four report `embedded=True`, `source=pdf`; `probe_chat --chunks-only` reports
`limit: 8` and `arms: lexical_only=False`. The pre-refresh build was 363/316 — so the deltas are
the reflow (13 reflow pages on SAOSO), not a regression.

**The count is not the check; the extractor is.** 364 vs 366 is the poppler/Xpdf split already
recorded in hazard §3.10, and **366 would have been the alarming answer** — it would mean the box
was reading Xpdf while the gate's committed page fixtures are poppler-calibrated. BPP's 16-vs-9
reads worse than it is: the box reported 16 at first install, before any reviewed artefact existed,
so it is page splitting, not a different text of record.

**Still outstanding, unchanged:** P2–P7 convert the remaining documents to reviewed artefacts. Until
P7.4 the box serves the PDF extraction for all four, so `uat_seed --check` still reports
`corpus present` as blocking.

## 4c. Third redeploy, 2026-10-22 — the chat fix (`70ae120`)

Deployed `f4e8907` → `6993a1b`. The product owner reports `/ask/` answering the borax
question as expected: sodium borate as a trace element, restricted to a documented
deficiency, citing Appendix 2.

**Why this one needed a live check rather than a green gate.** G9's refusal was
indistinguishable from a coverage gap on the screen — same sentence, same escalation link —
because the model *found* the answer and the citation was rejected. No test in the gate
could have caught it (it was the prompt's own formatting), and the gate was green at 808
throughout. The only proof is the live surface answering.

**Not yet proven, and recorded rather than assumed:**

- The **five fresh sessions** G9 sets as its acceptance test. One green run shows the
  format is no longer an obstacle; it does not show the class is gone, because a citation
  carrying a different decoration (the page number rather than the document title) would
  still be refused.
- The two **regression questions**: `can i use cardboard as mulch?` (must say the standard
  does not name it, not refuse) and the horse-manure question (must still answer).
- Both are hard to run today for an unrelated reason: `/ask/` has no way to start a new
  conversation, so each "fresh" question needs the cookie cleared. That is `todo.md`.


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
