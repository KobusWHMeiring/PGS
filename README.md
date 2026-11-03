# Outeniqua PGS Digital Platform

Software for a **Participatory Guarantee System** — the peer-review route by which small
producer groups guarantee organic integrity without paying a third-party certifier.

Outeniqua PGS has certified its members on paper clipboards since 2018. This is the system
that replaces the clipboards: the assessment record, the standard as a queryable corpus, and
a public site that can show what it actually knows.

> **Membership is not certification.** A member of the group is not thereby certified, and
> nothing here may imply otherwise. Only a completed assessment, a committee decision and a
> current certificate establish a certification outcome. `core/tests/test_claim_discipline.py`
> fails the build if the public surface suggests more.

Live: <https://organicguarantee.africa/>

## What it does today

| | |
|---|---|
| **Public site** | Home, the organic guarantee explained, how the process works, member list, joining, contact. |
| **Document library** | The governing documents served directly — no Google Drive, no sign-in — with a reader that reproduces the printed page, including tables and multi-column layout. |
| **Grounded assistant** | A question-answering surface over the standard. Every answer cites a passage that is checked character-for-character against the stored corpus; a citation that cannot be verified refuses the whole answer rather than being shown. Where the standard is silent, it says so and escalates to a person. |
| **Standards as data** | The standard, the assessment template and the certification outcomes are ingested artefacts, not code. |
| **Review tooling** | A UAT console for recording human sign-off against a running instance. |

## What it does not do yet

Stated plainly, because a reviewer should not have to discover it:

- **The assessment lifecycle is not built.** There is no `FarmVisit`, `Assessment` or
  `Certificate` model yet. `core/models/_certification.py` defines only `Seal` and `Category`.
  This is the next milestone, not a regression.
- **There is no offline client.** The assessor-in-the-field PWA — no signal, two-hour
  walkabout, sync on reconnect — is designed but unimplemented. No service worker exists.
- **The assistant degrades without an API key.** Retrieval is hybrid (lexical + vector) and
  the lexical arm has no API-key dependency; with no key the vector arm is skipped and the
  result is flagged `lexical_only=True` rather than silently degraded. The embeddings use a
  hosted provider.

## Why the design looks like this

**Code encodes the process; data encodes the standard and the group.** A retarget to a second
standard or a second producer group must not require a migration. Everything that differs
between schemes — sections, references, versions, seals, categories, questionnaires — is
ingested or seeded data.

This is enforced structurally rather than by convention: `knowledge/` owns the standards
corpus and its own migration namespace, and **must never import `core/`**. `lint-imports`
fails the build if it does.

The practical consequence is the interesting one: this is not "an app for one farm group". It
is a conformity engine whose first instance happens to be Outeniqua PGS.

## Requirements

- Python 3.13, Django 5.2
- PostgreSQL 16 with `pgvector` (the compose file pins `pgvector/pgvector:pg16`)
- Redis (cache, Celery broker; `/health/` asserts a live `PING`)
- `pdftotext` from Xpdf or poppler, only if you are (re)building the corpus

## Running it

```bash
docker compose up -d                 # Postgres on host port 5433 + Redis

python -m venv .venv
. .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# pgs.settings deliberately has no default secret key:
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
# put that value in .env as DJANGO_SECRET_KEY

python manage.py migrate
python manage.py runserver           # http://127.0.0.1:8000/
```

The database port is **5433, not 5432** — see the comment in `docker-compose.yml`. It is a
deliberate collision-avoidance choice on the development machine, not a mistake.

## The standard's documents are not included

This repository ships **the engine, not the corpus.**

`pgs_docs/` holds the governing documents for Outeniqua PGS and the SAOSO standard. They are
third-party works with their own terms, and this project has no right to redistribute them:
the SAOSO standard and the group's procedures carry no rights notice, and the certification
landscape document is explicitly limited to non-commercial use. See [`NOTICE`](NOTICE).

So an operator brings their own copy of the standard they are certified against:

```bash
python manage.py ingest_standard --doc saoso --file path/to/your/standard.pdf
```

That is also the mechanism that makes the engine retargetable: swap the documents, keep the
code.

## Tests

One suite, three budgets. Measured on 2026-11-03, warm:

```bash
./scripts/fast.sh --critical    # 217 tests,  ~24 s   the invariants that must never break
./scripts/fast.sh               # whole suite minus `slow`,  ~2.5 min
./scripts/verify.sh             # the gate: 1 598 passed, 1 skipped,  ~74 s
```

`verify.sh` is the single source of truth for "is this tree shippable" and is what the deploy
script runs before touching the live tree. Tests run against a real Postgres and Redis, with
`--create-db`, so migrations are exercised against an empty schema every time.

`tests/e2e` needs a browser and is deliberately outside the gate:
`python -m pytest tests/e2e -q` after `playwright install chromium`.

## Layout

```
core/          the application — accounts, members, public site, documents, chat, review tooling
knowledge/     the standards corpus and retrieval engine (a library: no users, no views, no sessions)
pgs_docs/      source documents (not redistributed — see NOTICE)
product/       spec, backlog, design artefacts, session handovers
tests/         cross-app tests and developer tooling
```

## Licence

**GNU Affero General Public License v3.0 or later** — see [`LICENSE`](LICENSE). AGPL
deliberately: the point is that a hosted deployment of this software must remain open.

The licence covers the source code. It does not cover the standards documents, the group's
photographs or its marks, or the vendored font and JavaScript files, each of which is
recorded in [`NOTICE`](NOTICE).

## About

Built for **Outeniqua PGS**, a participatory guarantee system operating along the Outeniqua
mountain range in the Western Cape, South Africa, in partnership with the standards owned by
SAOSO and PGS South Africa. The group's banking is handled by **NU HORUS NPO**.

Issues and questions are welcome. If you are a PGS group with a different standard and you
think the engine should fit yours, that is precisely the case this design was built to test.
