"""Django settings for the Outeniqua PGS platform.

Config comes from the environment and nothing else. `.env` (via `python-dotenv`)
is the sole source of instance configuration — `build_principles.md` §VI — so
there is exactly one way to configure a deployment and it is not this file.

Reading order, highest priority first:

1. A real environment variable (what Docker, CI and the VPS use).
2. `.env` in the repository root, which `load_dotenv` does **not** overwrite.
3. The dev default in `env()`/`env_list()` calls below, where one is safe.

A dev default exists only for values that are not secrets and whose absence
would make a fresh clone unusable. `DJANGO_SECRET_KEY` has no default: a missing
key is an error, because the alternative — a constant shared by every deployment
— is a vulnerability that no test can see (see `require_env`).

Deliberately absent: `weasyprint` settings mention (MVP 1), any S3/storage
configuration (media is filesystem, §VI), and any tenancy configuration
(`build_principles.md` §IX — this is a single-tenant blueprint, not SaaS).
"""

from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
import structlog
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# `override=False` (the default) is load-bearing: on the VPS and in CI the real
# environment must win over a stale `.env` left on disk. Explicit here so nobody
# "improves" it into override=True.
load_dotenv(BASE_DIR / ".env", override=False)


def env(name: str, default: str | None = None, *, required: bool = False) -> str:
    """Read a string from the environment.

    In:  `name`; `default` used when unset (ignored when `required`).
    Out: the value, stripped.
    Fails: `ImproperlyConfigured` naming the variable when `required` and unset.
    """
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        if required:
            raise ImproperlyConfigured(
                f"{name} is not set. Add it to .env (see .env.example) or the "
                f"process environment."
            )
        return default or ""
    return value.strip()


def require_env(name: str) -> str:
    """Read a mandatory value. Public so A2's tests can assert the failure mode."""
    return env(name, required=True)


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated list, dropping blanks.

    In:  `name`; `default` as a comma-separated string.
    Out: list of stripped non-empty strings.
    """
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        raw = default
    return [part.strip() for part in raw.split(",") if part.strip()]


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean from the environment; only explicit truthy strings are True."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- Core -------------------------------------------------------------------

# No default. A deployment with a shared or committed key is compromised in a way
# that produces no error message.
SECRET_KEY = require_env("DJANGO_SECRET_KEY")

# Defaults to False: forgetting to set it in production must fail closed, not
# serve debug pages with settings and tracebacks exposed.
DEBUG = env_bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1")

# CSRF's Origin check needs the scheme to match. Behind nginx the request reaches
# Django over plain HTTP on a unix socket, so the origin the browser sends
# (`https://…`) matches no host Django can infer. Without this list every POST —
# the chatbot form, admin logins — is rejected with "Origin checking failed" while
# GETs work, which reads as a broken form rather than a missing setting.
#
# Empty is correct for a dev box: same-origin requests match the Host header.
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", default="")

WSGI_APPLICATION = "pgs.wsgi.application"
ASGI_APPLICATION = "pgs.asgi.application"

ROOT_URLCONF = "pgs.urls"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # `pgvector` is an app so its migrations can create the extension before
    # B1's vector column (VectorExtension() must precede the column).
    "pgvector.django",
    # Local apps. `core` may import `knowledge`; never the reverse (A7, CI-enforced).
    "core",
    "knowledge",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Structured logging with a request id on every line (§VII.4). Placed last so
    # it sees the fully-populated request and times the whole middleware chain.
    "django_structlog.middlewares.RequestMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "core" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# --- Database ---------------------------------------------------------------
#
# The dev default points at the Compose container on host port 5433, not 5432 —
# a native PostgreSQL service on the primary dev box owns 5432, and Docker binds
# alongside it rather than failing (see docker-compose.yml). The password is not
# a secret: it is the throwaway credential baked into the checked-in Compose
# file, and it only ever protects a local container.
DATABASE_URL = env("DATABASE_URL", "postgres://pgs:pgs@localhost:5433/pgs")

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        # Never leave a transaction open on a dropped connection; the assessor
        # sync path writes across many tables and a silent rollback there is
        # data loss, not a failed request.
        conn_health_checks=True,
    )
}


# --- Redis, cache and Celery ------------------------------------------------
#
# Separate logical database numbers for the broker and the cache (§VIII). Sharing
# one means a `cache.clear()` can drop queued Celery work, and the symptom appears
# hours later as a task that never ran.

CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://localhost:6379/3")
CACHE_URL = env("CACHE_URL", "redis://localhost:6379/2")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CACHE_URL,
    }
}

CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", default=False)


# --- Standards corpus -------------------------------------------------------
#
# D3/D20: the embedding model and its dimension are **frozen in the migration**,
# because changing either later means re-embedding the whole corpus and every
# stored vector becomes meaningless rather than merely stale. `DocumentChunk.embedding`
# is a `vector(768)` column, so `EMBEDDING_DIM` is not a tunable dev setting — the
# value here and the column width must move together in one migration. The
# 768-dimension choice is deliberate: `gemini-embedding` supports
# `output_dimensionality=768`, and pgvector 0.5.x `HNSW` indexes only support up to
# 2000 dimensions, so 768 keeps the option of an ANN index later without a corpus
# rebuild. `knowledge/tests/test_models.py` asserts the two agree.
#
# Read by B5 (embedding) and B1 (the column width). Nothing else.

# D20: a developer key via `.env`, never a production key in the repo. Blank is a
# supported state (B5 raises `EmbeddingUnavailable`), because FTS-only retrieval and
# a full ingest must both work without embeddings.
GEMINI_API_KEY = env("GEMINI_API_KEY")

# The model is `gemini-embedding-001`, not the `text-embedding-004` that `.env.example`
# originally named: Google has retired the latter. The *dimension* is what D3/D20
# freeze (`DocumentChunk.embedding` is `vector(768)`), and B5 requests 768 explicitly
# via `output_dimensionality`, so the frozen column survives a model change.
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = int(env("EMBEDDING_DIM", "768"))


# --- Grounded chat (sub-plan D) ---------------------------------------------
#
# The chatbot is a public endpoint in front of a paid API, so every limit is a
# deployment setting rather than a literal in the service: a group with a larger
# budget can raise the per-IP allowance without a code release. The defaults are
# deliberately conservative. `CHAT_MODEL` is the generation model, not the embedding
# model above — changing it does not touch the frozen vector column.

CHAT_MODEL = env("CHAT_MODEL", "gemini-2.5-flash")
# Milliseconds, matching `google.genai.types.HttpOptions.timeout`. A hung call must
# not pin a web worker; §VII.2 requires an explicit timeout on every external call.
CHAT_TIMEOUT_MS = int(env("CHAT_TIMEOUT_MS", "30000"))
CHAT_RATE_LIMIT = int(env("CHAT_RATE_LIMIT", "20"))
CHAT_RATE_LIMIT_WINDOW_SECONDS = int(env("CHAT_RATE_LIMIT_WINDOW_SECONDS", "3600"))
CHAT_MAX_QUESTION_CHARS = int(env("CHAT_MAX_QUESTION_CHARS", "500"))
CHAT_HISTORY_MESSAGES = int(env("CHAT_HISTORY_MESSAGES", "8"))
# How many passages the model is given. Eight, not five: at five the cardboard question
# retrieves no inputs clause and refuses, at eight it answers from Appendix 2 (measured
# 2026-10-22, `testing_hazards.md` §2.7). The 2026-10-21 change raised
# `_chatbot.RETRIEVAL_LIMIT` instead of this setting, and that constant is only a
# fallback — so the product ran at five for a day while the plan believed eight.
CHAT_RETRIEVAL_LIMIT = int(env("CHAT_RETRIEVAL_LIMIT", "8"))
CHAT_ANSWER_CACHE_TTL = int(env("CHAT_ANSWER_CACHE_TTL", "3600"))
# Output tokens per generation attempt. 1024 truncated a four-citation answer mid-JSON
# on 2026-10-19, which surfaced to the visitor as "the service is unavailable".
CHAT_MAX_OUTPUT_TOKENS = int(env("CHAT_MAX_OUTPUT_TOKENS", "2048"))
# One retry is allowed at this cap when Gemini reports MAX_TOKENS; a second truncation
# is reported, not retried again.
CHAT_MAX_OUTPUT_TOKENS_CEILING = int(env("CHAT_MAX_OUTPUT_TOKENS_CEILING", "4096"))


# --- Media ------------------------------------------------------------------
#
# Two roots, and the difference is a security boundary, not tidiness (§VI).
# Evidence photos and voice notes are personal data and live under the private
# root; Django authorises each request and hands off to nginx via
# X-Accel-Redirect. Only derivatives meant for the public site (logo, photos)
# live under the public root. Serving PRIVATE_MEDIA_ROOT directly would publish
# the group's evidence.

MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))
PRIVATE_MEDIA_ROOT = Path(env("PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media")))
MEDIA_URL = "/media/"


# --- Auth -------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# A3 owns this: the custom user model. It is set in the same commit that defines
# `core.User`, because setting it earlier makes `manage.py check` fail outright —
# django.contrib.auth imports the user model and raises ImproperlyConfigured if it
# does not exist yet. This must remain the **first** migration applied to a new
# database; see the A3 gate in HANDOVER.md §5.
AUTH_USER_MODEL = "core.User"

LANGUAGE_CODE = "en-za"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

# Bilingual by default (§IV): English and Afrikaans are both first-class, and
# the PWA ships its catalogues inside the cached app shell.
LANGUAGES = [("en", "English"), ("af", "Afrikaans")]
LOCALE_PATHS = [BASE_DIR / "locale"]


# --- Static -----------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = Path(env("STATIC_ROOT", str(BASE_DIR / "staticfiles")))
# Zero build pipeline (§IV): assets ship via collectstatic, JS is vendored.
STATICFILES_DIRS = [BASE_DIR / "core" / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- TLS, cookies and proxy trust -------------------------------------------
#
# Gated on `DJANGO_TLS`, NOT on `not DEBUG`, and the difference is not pedantry.
# Django's test runner forces `DEBUG=False` while the suite runs, so a `not DEBUG`
# block switches `SECURE_SSL_REDIRECT` on underneath pytest: every test-client GET
# becomes a 301 and 86 tests fail on a status code rather than on their subject.
# The first version of this block did exactly that, and passed only because a
# developer's shell happened to export `DJANGO_DEBUG=True` — a green run for the
# wrong reason.
#
# So TLS is named as a property of the *deployment*, written into `.env` by
# deploy/first-install.sh. Forgetting it fails closed: with TLS off, `manage.py
# check --deploy --fail-level WARNING` reports W004/W008/W012/W016 and the deploy
# aborts before it restarts anything.
#
# `SECURE_PROXY_SSL_HEADER` is the load-bearing one. nginx terminates TLS and
# forwards the request over a unix socket, so without it Django believes every
# request is insecure; with `SECURE_SSL_REDIRECT` on, that produces an infinite
# 301 loop. A loop looks *alive* to a proxy check that only asks "did something
# answer", which is why this is a settings bug that presents as a healthy site.

DJANGO_TLS = env_bool("DJANGO_TLS", default=False)

if DJANGO_TLS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # One year. `PRELOAD` stays False deliberately: submitting the domain to the
    # browser preload list is effectively irreversible, and organicguarantee.africa
    # is not yet the group's forever host. Include-subdomains is on because the
    # certificate covers `www` and nothing else is served over plain HTTP here.
    SECURE_HSTS_SECONDS = 31_536_000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False

    # W021 asks for PRELOAD once HSTS is on. Declined deliberately, above, so the
    # warning is silenced BY ID rather than by relaxing the gate: deploy.sh runs
    # `check --deploy --fail-level WARNING`, and that flag is the only reason a
    # warning can block a deploy at all. Silence one by name and every other
    # security warning — W004 HSTS off, W008 no HTTPS redirect, W012/W016 insecure
    # cookies, W018 DEBUG still True — keeps failing the build.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]


# --- Observability ----------------------------------------------------------

SENTRY_DSN = env("SENTRY_DSN")
LOG_LEVEL = env("DJANGO_LOG_LEVEL", "INFO")

# django-structlog renders a request id onto every line (§VII.4).
DJANGO_STRUCTLOG_CELERY_ENABLED = True

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Human-readable in dev, JSON in production so the VPS log shipper can
        # parse it. A single format for both would make one of them unusable.
        structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}

# Sentry is optional on purpose. A blank DSN must leave a dev box fully working,
# so this is an `if`, not a `require_env`. Traces are sampled at zero until there
# is a reason to pay for them.
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=float(env("SENTRY_TRACES_SAMPLE_RATE", "0")),
        # Personal data: never attach request bodies or user identifiers by
        # default. POPIA exposure in this project is real (31 consumer names),
        # and Sentry is a third-party processor.
        send_default_pii=False,
        environment=env("SENTRY_ENVIRONMENT", "development"),
    )
