-- PostgreSQL role + database for __APP_NAME__ on the shared homtini VPS.
--
-- deploy/first-install.sh substitutes the __TOKENS__ and runs this as the postgres
-- superuser. Idempotent: safe to re-run. The password is generated on the server
-- and written to the app's .env; it is never committed.
--
-- The password is `openssl rand -hex 16`, so it contains no quote and needs no
-- escaping here. If you must use another generator, escape a single quote as ''.

-- --- Role ---------------------------------------------------------------------

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', '__DB_USER__', '__DB_PASSWORD__')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '__DB_USER__') \gexec

-- Re-set the password every run: this file is the single source of truth for the
-- role, and a re-run after a password rotation must not leave the old one working.
ALTER ROLE "__DB_USER__" WITH LOGIN PASSWORD '__DB_PASSWORD__';

-- CREATEDB is required by the deploy gate, not by the app. `scripts/verify.sh`
-- runs pytest with `--create-db`, which drops and recreates `test_<db>` on every
-- deploy; a role without CREATEDB makes the gate fail with "permission denied to
-- create database" before a single test runs. It is scoped to this role and grants
-- no visibility into any other app's database.
ALTER ROLE "__DB_USER__" WITH CREATEDB;

-- --- Databases ----------------------------------------------------------------

SELECT format('CREATE DATABASE %I OWNER %I', '__DB_NAME__', '__DB_USER__')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '__DB_NAME__') \gexec

-- The gate's own database. Deliberately separate from __DB_NAME__: verify.sh
-- migrates an empty schema and the tests write rows, and doing that against the
-- live database would be a destructive deploy step wearing a test's clothes.
SELECT format('CREATE DATABASE %I OWNER %I', '__DB_VERIFY_NAME__', '__DB_USER__')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '__DB_VERIFY_NAME__') \gexec

-- --- Extension ----------------------------------------------------------------
--
-- knowledge/0001_initial.py runs VectorExtension(), i.e. `CREATE EXTENSION vector`
-- — hence the `pgvector.django` app must precede the vector column. It is created
-- here as the superuser so the first migrate cannot fail on privileges, and the
-- extension is a prerequisite of the schema rather than something an app role is
-- trusted to install.
--
-- first-install.sh checks `pg_available_extensions` first; when the SQL statement
-- below fails, the package is missing, not the code:
--     sudo apt-get install -y postgresql-<major>-pgvector

\connect __DB_NAME__
CREATE EXTENSION IF NOT EXISTS vector;

GRANT ALL ON SCHEMA public TO "__DB_USER__";
ALTER SCHEMA public OWNER TO "__DB_USER__";

\connect __DB_VERIFY_NAME__
CREATE EXTENSION IF NOT EXISTS vector;

GRANT ALL ON SCHEMA public TO "__DB_USER__";
ALTER SCHEMA public OWNER TO "__DB_USER__";

\q
