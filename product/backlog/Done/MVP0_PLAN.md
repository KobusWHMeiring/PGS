# MVP 0 Implementation Plan — Standards Foundation & Public Shop Window

> **SUPERSEDED 2026-10-18 by `MVP0_PLAN_V2.md`. Kept for provenance only — do not execute.**
>
> Three of this plan's core assumptions were falsified by running a parser over the shipped
> PDFs: the SAOSO section parser matches **nothing** in the real file (`B-20.1.1` is invented;
> the source prints `20.1.1.`), the OPP parser cannot reach `§V` (seals) or `§VI` (aggregation),
> and the appendix parser fails on `Appendix 1.` / `Appendix 6a`. Its tests would have passed
> against hand-written fixtures while ingestion produced zero citable sections.
> See `MVP0_PRD.md` appendix (F1–F5) and `PGS_PLATFORM_SPEC.md` §4.5.

**Status:** Superseded — do not execute; see `MVP0_PLAN_V2.md`

**Goal:** Ship the SAOSO/OPP corpus as a queryable, citable library, and the PGS Outeniqua public website with a strictly grounded chatbot on it — making **no certification claim** of any kind.

**Architecture:** Django 5.2 monolith with a zero build pipeline. Two apps: `knowledge` (standards corpus plus retrieval — a one-way library, no users, no views) and `core` (everything user-facing). PostgreSQL with `pgvector` for embeddings and `tsvector` for lexical search, fused by Reciprocal Rank Fusion. Gemini for embeddings and generation. Celery + Redis for ingestion. Filesystem media; no S3.

**Tech Stack:** Python 3.13, Django 5.2, PostgreSQL 16 + pgvector, Redis 7, Celery 5.5, `google-generativeai`, `python-dotenv`, `django-structlog`, `sentry-sdk`, `pytest` + `factory-boy` + `pytest-playwright`, `import-linter`.

**UAT:** `tests/uat/mvp0_standards_and_public_site_uat.md` — drafted before implementation.

**Spec:** `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` §4.5–4.8, §12, §13, §19.

---

## Scope check: four sub-plans

MVP 0 is four independently testable subsystems. Each sub-plan produces working, testable software on its own, so they can be executed in separate sessions without dragging the whole plan into context.

| Sub-plan | Produces | Depends on |
|----------|----------|------------|
| **A — Foundation** | A deployable, empty, health-checked Django monolith with CI, backup and the `knowledge`↛`core` rule enforced | — |
| **B — Standards corpus & retrieval** | `ingest_standard` loads the four real PDFs; retrieval returns citable chunks scoped to a `StandardSet` | A |
| **C — Public site & documents** | The marketing site, `/documents/` hosting, bilingual scaffolding | A |
| **D — Grounded chatbot** | `answer_question()` with a strict JSON contract, citations, and escalation | B, C |

**Out of scope for MVP 0:** authentication beyond the `User` model itself, the farmer portal, the assessor PWA, assessments, certificates, the registry, QR verification, reporting, aggregation workflow, voice notes.

---

## File structure created across MVP 0

```
manage.py
requirements.txt
pytest.ini
.importlinter
Makefile
.env.example
docker-compose.yml
Dockerfile
.github/workflows/ci.yml
scripts/{backup.sh,restore.sh}
docs/RUNBOOK.md

pgs/
  settings.py  urls.py  celery.py  wsgi.py  asgi.py
  middleware.py

knowledge/                        # the library — never imports core
  models.py                       # StandardSet, StandardDocument, DocumentChunk
  services.py                     # retrieval, chunking, embedding, RRF fusion
  sections/                       # pluggable section-reference parsers
    __init__.py  registry.py  saoso.py  opp.py  eu.py
  tasks.py                        # ingest_standard
  management/commands/ingest_standard.py
  migrations/
  tests/

core/
  models/
    __init__.py _core.py _chat.py _certification.py
  services/
    _health.py _seed.py _documents.py _chatbot.py _retrieval_adapter.py
  views/
    _health.py _public.py _documents.py _chatbot.py
  forms/ _chatbot.py
  tasks/ _maintenance.py
  management/commands/seed_deployment.py
  templates/
    base.html
    public/{_nav,_footer,page,home,organics,how-it-works,members,join,contact}.html
    documents/index.html
    chatbot/{panel,_answer}.html
    committee/escalations.html
  static/{css/styles.css,js/vendor/htmx.min.js}
  tests/
  migrations/

tests/
  uat/mvp0_standards_and_public_site_uat.md
  e2e/{test_public_site.py,test_chatbot.py}
  conftest.py

locale/{en,af}/LC_MESSAGES/
content/                          # markdown/HTML ported from WordPress
  home.md organics.md how-it-works.md members.md join.md contact.md
```

---

# Sub-plan A — Foundation

Produces a deployable, empty monolith: settings, health check, structured logging, Celery, CI, the import rule, and backup scripts. Nothing user-facing yet.

---

### Task A1: Repository scaffold and dependency manifest

**Files:**
- Create: `requirements.txt`, `.env.example`, `.gitignore`
- Create (generated): `manage.py`, `pgs/settings.py`, `core/`, `knowledge/`

- [ ] **Step 1: Initialise the repository and virtualenv**

```bash
cd ~/Documents/Dev/pgs
git init
python -m venv .venv
source .venv/Scripts/activate     # Windows Git Bash
python -m pip install --upgrade pip
```

- [ ] **Step 2: Install dependencies and freeze**

```bash
pip install "Django==5.2.*" psycopg2-binary dj-database-url python-dotenv \
  celery redis django-structlog sentry-sdk pgvector \
  google-generativeai weasyprint openpyxl \
  pytest pytest-django pytest-playwright factory-boy faker \
  django-import-export import-linter
pip freeze > requirements.txt
```

- [ ] **Step 3: Create the project and both apps**

```bash
django-admin startproject pgs .
python manage.py startapp core
python manage.py startapp knowledge
mkdir -p core/models core/services core/views core/forms core/tasks
touch core/models/__init__.py core/services/__init__.py core/views/__init__.py \
      core/forms/__init__.py core/tasks/__init__.py
```

- [ ] **Step 4: Write `.gitignore`**

```
.venv/
__pycache__/
*.py[cod]
.env
db.sqlite3
media/
private_media/
staticfiles/
.pytest_cache/
backups/
```

- [ ] **Step 5: Write `.env.example`**

```
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=True
DATABASE_URL=postgres://pgs:pgs@localhost:5432/pgs
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
GEMINI_API_KEY=
SENTRY_DSN=
ALLOWED_HOSTS=localhost,127.0.0.1
MEDIA_ROOT=media
PRIVATE_MEDIA_ROOT=private_media
BACKUP_DIR=/mnt/pgs-backup
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: scaffold Django project with core and knowledge apps"
```

---

### Task A2: Environment-driven settings and app registration

**Files:**
- Modify: `pgs/settings.py`
- Test: `core/tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_settings.py
from django.conf import settings
from django.test import SimpleTestCase


class SettingsContractTests(SimpleTestCase):
    def test_custom_user_model_is_core_user(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "core.User")

    def test_pgvector_installed(self):
        self.assertIn("pgvector.django", settings.INSTALLED_APPS)

    def test_postgres_backend(self):
        self.assertEqual(
            settings.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql"
        )

    def test_private_media_root_is_separate_from_media_root(self):
        self.assertNotEqual(settings.MEDIA_ROOT, settings.PRIVATE_MEDIA_ROOT)

    def test_secret_key_comes_from_environment(self):
        self.assertNotIn("replace-me", settings.SECRET_KEY)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_settings.py -v`
Expected: FAIL — `AUTH_USER_MODEL` is `auth.User`; `pgvector.django` not installed.

- [ ] **Step 3: Implement the settings**

```python
# pgs/settings.py  (replace the generated file)
import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "pgvector.django",
    "django_structlog",
    "core",
    "knowledge",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pgs.urls"
WSGI_APPLICATION = "pgs.wsgi.application"
AUTH_USER_MODEL = "core.User"

DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"])}

MEDIA_ROOT = BASE_DIR / os.environ.get("MEDIA_ROOT", "media")
PRIVATE_MEDIA_ROOT = BASE_DIR / os.environ.get("PRIVATE_MEDIA_ROOT", "private_media")
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "core" / "static"]

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("af", "Afrikaans")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-flash-latest"
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768          # frozen — see PGS_PLATFORM_SPEC D3
EXTERNAL_HTTP_TIMEOUT = 20   # never omit a timeout on an external call

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = DEBUG

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "core" / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest core/tests/test_settings.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add pgs/settings.py core/tests/test_settings.py
git commit -m "feat: environment-driven settings with custom user model and pgvector"
```

---

### Task A3: The custom `User` model and plural roles

Needed before the *first* migration — changing `AUTH_USER_MODEL` later is painful.

**Files:**
- Create: `core/models/_core.py`, `core/models/__init__.py`
- Modify: `core/apps.py`
- Test: `core/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model

from core.models import UserRole

User = get_user_model()


@pytest.mark.django_db
def test_user_can_hold_several_roles():
    user = User.objects.create_user(email="sasha@example.com", password="x")
    UserRole.objects.create(user=user, role=UserRole.FARMER)
    UserRole.objects.create(user=user, role=UserRole.ASSESSOR)
    UserRole.objects.create(user=user, role=UserRole.CONSUMER)

    assert user.has_role("FARMER", "ASSESSOR") is True
    assert user.has_role("ADMIN") is False
    assert sorted(user.role_codes()) == ["ASSESSOR", "CONSUMER", "FARMER"]


@pytest.mark.django_db
def test_duplicate_role_is_rejected():
    user = User.objects.create_user(email="dup@example.com", password="x")
    UserRole.objects.create(user=user, role=UserRole.FARMER)
    with pytest.raises(Exception):
        UserRole.objects.create(user=user, role=UserRole.FARMER)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'UserRole' from 'core.models'`

- [ ] **Step 3: Implement the models**

```python
# core/models/_core.py
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("email is required")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """In: none. Out: an account that may hold zero or more roles.
    Side Effects: none. Fails: none."""

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, blank=True)
    preferred_language = models.CharField(max_length=5, default="en")
    popia_consent_at = models.DateTimeField(null=True, blank=True)
    graduated_from_public_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def has_role(self, *codes) -> bool:
        return self.roles.filter(role__in=codes).exists()

    def role_codes(self) -> list[str]:
        return sorted(self.roles.values_list("role", flat=True))

    def __str__(self):
        return self.email


class UserRole(models.Model):
    """Axis 1 of §3: what a person is entitled to do. Zero or more per user."""

    FARMER = "FARMER"
    ASSESSOR = "ASSESSOR"
    CONSUMER = "CONSUMER"
    VALUE_CHAIN_ACTOR = "VALUE_CHAIN_ACTOR"
    ACADEMIC = "ACADEMIC"
    ADMIN = "ADMIN"
    COMMITTEE = "COMMITTEE"
    CHOICES = [(v, v.replace("_", " ").title()) for v in
               (FARMER, ASSESSOR, CONSUMER, VALUE_CHAIN_ACTOR, ACADEMIC, ADMIN, COMMITTEE)]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.CharField(max_length=24, choices=CHOICES)
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "role"], name="uniq_user_role")]

    def __str__(self):
        return f"{self.user.email}:{self.role}"
```

```python
# core/models/__init__.py
from core.models._core import User, UserRole

__all__ = ["User", "UserRole"]
```

```python
# core/apps.py
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
```

- [ ] **Step 4: Add `django.contrib.postgres` requirement and migrate**

Run: `python manage.py makemigrations core && python manage.py migrate`
Expected: migration `0001_initial` created; `auth` tables created; no error about a swapped user model.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest core/tests/test_models.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add core/models core/apps.py core/migrations core/tests/test_models.py
git commit -m "feat: custom User with plural UserRole"
```

---

### Task A4: `Category` and `Seal` as data, plus `seed_deployment`

Implements PGS_PLATFORM_SPEC §4.8 — the extensibility rule. Seals and categories are tables, not enums, so retargeting never needs a migration.

**Files:**
- Modify: `core/models/_core.py` (add `Category`), `core/models/_certification.py` (new)
- Create: `core/services/_seed.py`, `core/management/commands/seed_deployment.py`
- Modify: `core/models/__init__.py`
- Test: `core/tests/test_seed_deployment.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_seed_deployment.py
import pytest
from django.core.management import call_command

from core.models import Category, Seal


@pytest.mark.django_db
def test_seed_creates_categories_and_seals():
    call_command("seed_deployment")

    assert Category.objects.filter(is_active=True).count() == 4
    assert Category.objects.filter(code="AQUACULTURE", is_active=False).count() == 1

    assert Seal.objects.filter(is_active=True).count() == 2
    assert Seal.objects.get(code="PGS_PASTURE_RAISED").is_active is False


@pytest.mark.django_db
def test_seed_is_idempotent():
    call_command("seed_deployment")
    before = (Category.objects.count(), Seal.objects.count())

    call_command("seed_deployment")

    assert (Category.objects.count(), Seal.objects.count()) == before
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_seed_deployment.py -v`
Expected: FAIL — no `Category` / `Seal` models.

- [ ] **Step 3: Implement the models**

```python
# appended to core/models/_core.py

class Category(models.Model):
    """Assessment category. Data, not an enum — see PGS_PLATFORM_SPEC §4.8."""

    code = models.CharField(max_length=32, unique=True)
    label = models.CharField(max_length=64)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    standard_ref = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["display_order", "code"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.label
```

```python
# core/models/_certification.py
from django.db import models


class Seal(models.Model):
    """An issuable mark. Data, not an enum — seals belong to the standard (§4.8)."""

    code = models.CharField(max_length=48, unique=True)
    label = models.CharField(max_length=64)
    standard_ref = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    criteria_defined = models.BooleanField(default=True)
    display_note = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.label
```

```python
# core/models/__init__.py
from core.models._certification import Seal
from core.models._core import Category, User, UserRole

__all__ = ["Category", "Seal", "User", "UserRole"]
```

- [ ] **Step 4: Implement the seeding service and command**

```python
# core/services/_seed.py
from dataclasses import dataclass

from django.db import transaction

from core.models import Category, Seal

CATEGORIES = [
    ("CROPS", "Crops", True, 1),
    ("ANIMAL_HUSBANDRY", "Animal Husbandry", True, 2),
    ("SEED_PRODUCTION", "Seed Production", True, 3),
    ("AGRO_PROCESSING", "Agro-Processing", True, 4),
    ("AQUACULTURE", "Aquaculture (in development)", False, 5),
    ("WINE", "Wine (in development)", False, 6),
    ("INPUT_SUPPLIER", "Input Supplier (in development)", False, 7),
]

SEALS = [
    ("PGS_ORGANIC_CERTIFIED", "PGS Organic Certified", "OPP V", True, True, ""),
    ("PGS_ORGANIC_IN_CONVERSION", "PGS Organic In-Conversion", "OPP V", True, True, ""),
    ("PGS_PASTURE_RAISED", "PGS pasture-raised", "OPP V", False, False,
     "Criteria forthcoming — not issued."),
]


@dataclass(frozen=True)
class SeedReport:
    """In: none. Out: counts written. Side Effects: writes Category and Seal.
    Fails: ValidationError on a malformed constant."""

    categories_created: int
    seals_created: int


def seed_deployment() -> SeedReport:
    """
    In:
        None.
    Out:
        SeedReport (categories_created, seals_created) — zero on a repeat run.
    Side Effects:
        Idempotently upserts Category and Seal rows. Never deletes.
    Idempotency:
        Keyed on `code`; safe to run on every deploy.
    Fails:
        django.core.exceptions.ValidationError if a constant is malformed.
    """
    created_c, created_s = 0, 0
    with transaction.atomic():
        for code, label, active, order in CATEGORIES:
            _, made = Category.objects.update_or_create(
                code=code,
                defaults={"label": label, "is_active": active, "display_order": order},
            )
            created_c += int(made)
        for code, label, ref, active, defined, note in SEALS:
            _, made = Seal.objects.update_or_create(
                code=code,
                defaults={"label": label, "standard_ref": ref, "is_active": active,
                          "criteria_defined": defined, "display_note": note},
            )
            created_s += int(made)
    return SeedReport(categories_created=created_c, seals_created=created_s)
```

```python
# core/management/commands/seed_deployment.py
from django.core.management.base import BaseCommand

from core.services._seed import seed_deployment


class Command(BaseCommand):
    help = "Idempotently seed deployment data (categories, seals)."

    def handle(self, *args, **options):
        report = seed_deployment()
        self.stdout.write(self.style.SUCCESS(
            f"categories created: {report.categories_created}; "
            f"seals created: {report.seals_created}"
        ))
```

- [ ] **Step 5: Migrate and run the tests**

```bash
python manage.py makemigrations core && python manage.py migrate
pytest core/tests/test_seed_deployment.py -v
```
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add core/models core/services/_seed.py core/management \
        core/migrations core/tests/test_seed_deployment.py
git commit -m "feat: Category and Seal as data, with idempotent seed_deployment"
```

---

### Task A5: `/health/` endpoint

Mandatory per `build_principles.md` §VII.1.

**Files:**
- Create: `core/services/_health.py`, `core/views/_health.py`
- Create: `core/urls.py`, `pgs/urls.py`
- Test: `core/tests/test_health.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_health.py
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_ok(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {
        "db": "ok", "redis": "ok", "celery_broker": "ok", "celery_worker": "ok",
    }


@pytest.mark.django_db
def test_health_returns_503_when_redis_is_down(client, monkeypatch):
    monkeypatch.setattr("core.services._health._redis_ping", lambda: False)
    response = client.get(reverse("health"))
    assert response.status_code == 503
    assert response.json()["redis"] == "fail"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_health.py -v`
Expected: FAIL — `NoReverseMatch: Reverse for 'health' not found`

- [ ] **Step 3: Implement the service**

```python
# core/services/_health.py
from dataclasses import dataclass

from django.db import connection


@dataclass(frozen=True)
class HealthReport:
    """In: none. Out: per-dependency status strings. Side Effects: one SELECT 1.
    Fails: never — a failure is reported as a status, not raised."""

    db: str
    redis: str
    celery_broker: str
    celery_worker: str

    @property
    def healthy(self) -> bool:
        return all(v == "ok" for v in (self.db, self.redis,
                                       self.celery_broker, self.celery_worker))

    def as_dict(self) -> dict:
        return {"db": self.db, "redis": self.redis,
                "celery_broker": self.celery_broker, "celery_worker": self.celery_worker}


def _redis_ping() -> bool:
    import redis
    from django.conf import settings
    client = redis.from_url(settings.REDIS_URL_FOR_HEALTH, socket_connect_timeout=2)
    return bool(client.ping())


def check_dependencies() -> HealthReport:
    """
    In:
        None.
    Out:
        HealthReport — each field "ok" or "fail".
    Side Effects:
        Issues SELECT 1, a Redis PING, and a Celery inspect ping with a 3s timeout.
    Fails:
        Never raises. Any dependency error is captured as "fail".
    """
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        db = "ok"
    except Exception:
        db = "fail"

    try:
        redis_ok = "ok" if _redis_ping() else "fail"
    except Exception:
        redis_ok = "fail"

    try:
        from pgs.celery import app
        broker = "ok" if app.connection_for_read().ensure_connection(max_retries=0) is None else "ok"
    except Exception:
        broker = "fail"

    try:
        from pgs.celery import app
        worker = "ok" if app.control.ping(timeout=3) else "fail"
    except Exception:
        worker = "fail"

    return HealthReport(db=db, redis=redis_ok, celery_broker=broker, celery_worker=worker)
```

> Add `REDIS_URL_FOR_HEALTH = os.environ.get("REDIS_URL", "redis://localhost:6379/0")` to settings in this step.

- [ ] **Step 4: Implement the view and URLs**

```python
# core/views/_health.py
from django.http import JsonResponse

from core.services._health import check_dependencies


def health(request):
    report = check_dependencies()
    return JsonResponse(report.as_dict(), status=200 if report.healthy else 503)
```

```python
# core/urls.py
from django.urls import path

from core.views._health import health

urlpatterns = [path("health/", health, name="health")]
```

```python
# pgs/urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest core/tests/test_health.py -v`
Expected: PASS (2 passed). Requires Redis running: `docker compose up -d redis`.

- [ ] **Step 6: Commit**

```bash
git add core/services/_health.py core/views/_health.py core/urls.py pgs/urls.py \
        core/tests/test_health.py pgs/settings.py
git commit -m "feat: /health/ endpoint checking db, redis, celery broker and worker"
```

---

### Task A6: Celery application with a retry-policied task

Mandatory per `build_principles.md` §VII.3.

**Files:**
- Create: `pgs/celery.py`, `core/tasks/_maintenance.py`
- Modify: `pgs/__init__.py`
- Test: `core/tests/test_tasks.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_tasks.py
from core.tasks._maintenance import ping


def test_ping_task_declares_a_retry_policy():
    assert ping.autoretry_for == ()
    assert ping.max_retries == 0


def test_ping_returns_pong():
    assert ping() == "pong"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_tasks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.tasks._maintenance'`

- [ ] **Step 3: Implement the Celery app and task**

```python
# pgs/celery.py
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")
app = Celery("pgs")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

```python
# pgs/__init__.py
from pgs.celery import app as celery_app

__all__ = ("celery_app",)
```

```python
# core/tasks/_maintenance.py
from celery import shared_task


@shared_task(autoretry_for=(), max_retries=0)
def ping() -> str:
    """Liveness probe used by /health/. Non-idempotent-safe, so it must not retry."""
    return "pong"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest core/tests/test_tasks.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Wire the worker liveness check to the real task**

Replace the `app.control.ping` call in `core/services/_health.py` with `app.control.inspect().ping()`, and assert on the `ping` task above being importable.

- [ ] **Step 6: Commit**

```bash
git add pgs/celery.py pgs/__init__.py core/tasks core/tests/test_tasks.py
git commit -m "feat: Celery app with explicit retry policies"
```

---

### Task A7: The `knowledge` ↛ `core` import contract

This is the O4 decision (§18.2) made executable.

**Files:**
- Create: `.importlinter`

- [ ] **Step 1: Write the contract**

```ini
# .importlinter
[importlinter]
root_package = pgs
include_external_packages = False

[importlinter:contract:knowledge-is-a-leaf]
name = knowledge must never import core
type = forbidden
source_modules =
    knowledge
forbidden_modules =
    core
```

- [ ] **Step 2: Run it**

Run: `lint-imports`
Expected: `Contracts: 1 kept, 0 broken.`

- [ ] **Step 3: Prove the contract can actually fail**

Temporarily add `from core.models import User` to `knowledge/models.py`, run `lint-imports`, and confirm it reports the broken contract. **Then remove the import.**

- [ ] **Step 4: Commit**

```bash
git add .importlinter
git commit -m "chore: enforce the one-way knowledge -> core dependency rule"
```

---

### Task A8: Test, lint and CI tooling

**Files:**
- Create: `pytest.ini`, `Makefile`, `.github/workflows/ci.yml`

- [ ] **Step 1: Write `pytest.ini`**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = pgs.settings
python_files = test_*.py
testpaths = core knowledge tests
addopts = -q --strict-markers
markers =
    e2e: Playwright end-to-end tests
```

- [ ] **Step 2: Write the `Makefile`**

```make
.PHONY: up down test lint imports check migrate seed

up:            ; docker compose up -d db redis
down:          ; docker compose down
migrate:       ; python manage.py migrate
seed:          ; python manage.py seed_deployment
test:          ; pytest
lint:          ; ruff check . && black --check .
imports:       ; lint-imports
check:         test imports lint
```

- [ ] **Step 3: Write the CI workflow**

```yaml
# .github/workflows/ci.yml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      db:
        image: pgvector/pgvector:pg16
        env: { POSTGRES_DB: pgs, POSTGRES_USER: pgs, POSTGRES_PASSWORD: pgs }
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    env:
      DJANGO_SECRET_KEY: ci-secret-not-for-production
      DJANGO_DEBUG: "False"
      DATABASE_URL: postgres://pgs:pgs@localhost:5432/pgs
      REDIS_URL: redis://localhost:6379/0
      CELERY_BROKER_URL: redis://localhost:6379/1
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: pip install -r requirements.txt
      - run: lint-imports
      - run: python manage.py migrate
      - run: pytest
```

- [ ] **Step 4: Run the full gate locally**

Run: `make check`
Expected: tests pass, imports contract kept, lint clean.

- [ ] **Step 5: Commit**

```bash
git add pytest.ini Makefile .github
git commit -m "chore: pytest, make targets and CI running tests, lint and import contracts"
```

---

### Task A9: Backup and restore for the media volume

R11 is the highest-severity risk in the spec: with filesystem media and no S3, the backup **is** the safety net, and a silent backup failure is worse than no backup.

**Files:**
- Create: `scripts/backup.sh`, `scripts/restore.sh`, `docs/RUNBOOK.md`

- [ ] **Step 1: Write the backup script**

```bash
#!/usr/bin/env bash
# scripts/backup.sh — database + media to an external drive. Fails loudly.
set -euo pipefail
: "${BACKUP_DIR:?BACKUP_DIR must be set}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${BACKUP_DIR}/pgs/${STAMP}"
mkdir -p "${DEST}"

pg_dump --format=custom --file="${DEST}/db.dump" "${DATABASE_URL}"
rsync -a --delete "${MEDIA_ROOT}/"    "${DEST}/media/"
rsync -a --delete "${PRIVATE_MEDIA_ROOT}/" "${DEST}/private_media/"
sha256sum "${DEST}/db.dump" > "${DEST}/db.dump.sha256"

# Retention: keep 30 days
find "${BACKUP_DIR}/pgs" -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +

echo "backup ok: ${DEST}"
```

> Every failure path here exits non-zero and prints nothing to stdout, so a scheduler that only alerts on success output will catch a dead job.

- [ ] **Step 2: Write the restore script**

```bash
#!/usr/bin/env bash
# scripts/restore.sh <backup-dir> — rehearsed before launch, not assumed.
set -euo pipefail
SRC="${1:?usage: restore.sh <backup-dir>}"
sha256sum -c "${SRC}/db.dump.sha256"
pg_restore --clean --if-exists --dbname "${DATABASE_URL}" "${SRC}/db.dump"
rsync -a --delete "${SRC}/media/" "${MEDIA_ROOT}/"
rsync -a --delete "${SRC}/private_media/" "${PRIVATE_MEDIA_ROOT}/"
echo "restore ok"
```

- [ ] **Step 3: Rehearse the restore against a scratch database**

```bash
chmod +x scripts/*.sh
docker compose up -d db
DATABASE_URL=postgres://pgs:pgs@localhost:5432/pgs BACKUP_DIR=/tmp/pgsb \
  MEDIA_ROOT=media PRIVATE_MEDIA_ROOT=private_media ./scripts/backup.sh
DATABASE_URL=postgres://pgs:pgs@localhost:5432/pgs_restore_rehearsal \
  MEDIA_ROOT=/tmp/m PRIVATE_MEDIA_ROOT=/tmp/pm ./scripts/restore.sh "$(ls -d /tmp/pgsb/pgs/*/ | tail -1)"
```
Expected: `restore ok`. Record the observed output in `docs/RUNBOOK.md` as launch evidence.

- [ ] **Step 4: Document the runbook**

```markdown
# docs/RUNBOOK.md
## Backup
`scripts/backup.sh` runs nightly via cron to `$BACKUP_DIR` (external drive).
**A backup job that fails silently is worse than no backup.** Alerting is on the
*absence* of the nightly `backup ok` line, not only on a non-zero exit.
## Restore
Rehearsed on <date> against a scratch database; output recorded below.
## Residual risk (accepted, R11)
A local drive does not survive theft, fire or flood. There is no second copy at
another site. This is a known gap.
```

- [ ] **Step 5: Commit**

```bash
git add scripts docs/RUNBOOK.md
chmod +x scripts/*.sh
git commit -m "feat: loud-failing backup and rehearsed restore for db and media"
```

---

**End of Sub-plan A.** The result is deployable and verifiable: `/health/` reports all four dependencies, CI enforces the import contract, and the backup path is rehearsed rather than assumed.

**Sub-plans B, C and D are appended below.**

---

# Sub-plan B — Standards corpus & retrieval

Produces a `knowledge` app that ingests the four real PDFs and answers retrieval queries with citable chunks, scoped to a `StandardSet`. Implements PGS_PLATFORM_SPEC §4.5 and §13.

Add `pypdf` to `requirements.txt` before starting.

---

### Task B1: Corpus models with pgvector and a generated tsvector

**Files:**
- Create: `knowledge/models.py`, `knowledge/apps.py`
- Create: `knowledge/migrations/0001_initial.py` (via `makemigrations`)
- Test: `knowledge/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# knowledge/tests/test_models.py
import pytest
from django.conf import settings

from knowledge.models import DocumentChunk, StandardDocument, StandardSet


@pytest.mark.django_db
def test_search_vector_is_populated_on_insert():
    s = StandardSet.objects.create(code="outeniqua-2026", label="Outeniqua PGS 2026")
    d = StandardDocument.objects.create(
        standard_set=s, kind="STANDARD", title="SAOSO v2.1",
        source_file="standards/saoso.pdf", sha256="a" * 64,
    )
    chunk = DocumentChunk.objects.create(
        document=d, ordinal=1, section_ref="B-20.1.1",
        text="Handlers shall not co-mingle organic products with non-organic products.",
    )

    from django.contrib.postgres.search import SearchQuery
    hit = DocumentChunk.objects.filter(search_vector=SearchQuery("co-mingle"))
    assert list(hit) == [chunk]


@pytest.mark.django_db
def test_embedding_dimension_matches_settings():
    field = DocumentChunk._meta.get_field("embedding")
    assert field.dimensions == settings.EMBEDDING_DIM


@pytest.mark.django_db
def test_chunk_ordinal_is_unique_per_document():
    s = StandardSet.objects.create(code="x", label="X")
    d = StandardDocument.objects.create(
        standard_set=s, kind="STANDARD", title="T",
        source_file="standards/t.pdf", sha256="b" * 64,
    )
    DocumentChunk.objects.create(document=d, ordinal=1, section_ref="A", text="one")
    with pytest.raises(Exception):
        DocumentChunk.objects.create(document=d, ordinal=1, section_ref="A", text="two")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest knowledge/tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'knowledge.models'`

- [ ] **Step 3: Implement the models**

```python
# knowledge/models.py
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import models
from pgvector.django import VectorField


class StandardSet(models.Model):
    """A corpus that retrieval is scoped to. Outeniqua's set is
    SAOSO 2.1 + the OPP + the Basic Production Principles + the landscape doc."""

    code = models.SlugField(max_length=64, unique=True)
    label = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.label


class StandardDocument(models.Model):
    KIND_CHOICES = [
        ("STANDARD", "Standard"),
        ("SOP", "SOP"),
        ("PRINCIPLES", "Principles"),
        ("GUIDANCE", "Guidance"),
        ("LANDSCAPE", "Landscape"),
    ]

    standard_set = models.ForeignKey(
        StandardSet, on_delete=models.CASCADE, related_name="documents"
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    issuing_body = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=40, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    superseded_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="supersedes"
    )
    source_file = models.FileField(upload_to="standards/")
    sha256 = models.CharField(max_length=64, unique=True)
    chunk_count = models.PositiveIntegerField(default=0)
    section_scheme = models.CharField(max_length=24, default="saoso")

    def __str__(self):
        return f"{self.title} {self.version}".strip()


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        StandardDocument, on_delete=models.CASCADE, related_name="chunks"
    )
    ordinal = models.PositiveIntegerField()
    section_ref = models.CharField(max_length=64)
    heading_path = models.CharField(max_length=300, blank=True)
    page = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True)
    search_vector = models.GeneratedField(
        expression=SearchVector("text", config="english"),
        output_field=SearchVectorField(),
        db_persist=True,
    )

    class Meta:
        ordering = ["document_id", "ordinal"]
        constraints = [
            models.UniqueConstraint(fields=["document", "ordinal"], name="uniq_doc_ordinal"),
        ]
        indexes = [GinIndex(fields=["search_vector"])]

    def __str__(self):
        return f"{self.document_id}#{self.ordinal} ({self.section_ref})"
```

```python
# knowledge/apps.py
from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "knowledge"
```

- [ ] **Step 4: Enable the vector extension in the migration**

```bash
python manage.py makemigrations knowledge
```

Then edit the generated migration to add the extension as the **first** operation:

```python
from pgvector.django import VectorExtension

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        VectorExtension(),          # must precede the VectorField
        # ...generated operations...
    ]
```

- [ ] **Step 5: Migrate and run the tests**

```bash
python manage.py migrate
pytest knowledge/tests/test_models.py -v
```
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add knowledge requirements.txt
python manage.py makemigrations knowledge --check
```

---

### Task B2: Pluggable section-reference parsers

This is the change that makes “swap documents in and out” real (§4.5): citation extraction is the only genuinely standard-specific step in ingestion, so it is a strategy selected by data.

**Files:**
- Create: `knowledge/sections/{__init__.py,registry.py,saoso.py,opp.py,eu.py}`
- Test: `knowledge/tests/test_section_parsers.py`

- [ ] **Step 1: Write the failing test**

```python
# knowledge/tests/test_section_parsers.py
from knowledge.sections.registry import get_parser, UnknownSectionScheme

SAOSO_SAMPLE = """\
3. Minimum Inspection Requirements

B-20.1.1 Handlers and processors shall not co-mingle organic products.
B-20.1.2 Traceability shall be ensured in the processing chain.

Appendix 2 Fertilizers Conditioners and Soil Conditioners
"""

OPP_SAMPLE = """\
4.1 Preparation for the assessment:
The assessment team must consist of at least the following:

4.2 Assessment:
The committee member responsible for administration will drive the process.
"""


def test_saoso_parser_extracts_clause_refs():
    sections = get_parser("saoso").parse(SAOSO_SAMPLE)
    refs = [s.section_ref for s in sections]
    assert "B-20.1.1" in refs
    assert "B-20.1.2" in refs
    assert "Appendix 2" in refs
    assert sections[1].text.startswith("Handlers and processors shall not")


def test_opp_parser_extracts_numbered_refs():
    sections = get_parser("opp").parse(OPP_SAMPLE)
    assert [s.section_ref for s in sections] == ["4.1", "4.2"]


def test_unknown_scheme_raises():
    import pytest
    with pytest.raises(UnknownSectionScheme):
        get_parser("nope")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest knowledge/tests/test_section_parsers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'knowledge.sections'`

- [ ] **Step 3: Implement the parser interface and registry**

```python
# knowledge/sections/__init__.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedSection:
    """In: none. Out: one citable unit of a standard.
    Side Effects: none. Fails: none."""

    section_ref: str
    heading_path: str
    text: str
    page: int | None = None
```

```python
# knowledge/sections/registry.py
from typing import Protocol

from knowledge.sections import ParsedSection


class UnknownSectionScheme(LookupError):
    pass


class SectionParser(Protocol):
    def parse(self, text: str) -> list[ParsedSection]: ...


def get_parser(scheme: str) -> SectionParser:
    """
    In:
        scheme: str (one of 'saoso', 'opp', 'eu').
    Out:
        SectionParser for that standard's citation format.
    Side Effects:
        None.
    Fails:
        UnknownSectionScheme: if the scheme is not registered.
    """
    from knowledge.sections.eu import EuArticleParser
    from knowledge.sections.opp import OppNumberedParser
    from knowledge.sections.saoso import SaosoClauseParser

    registry: dict[str, SectionParser] = {
        "saoso": SaosoClauseParser(),
        "opp": OppNumberedParser(),
        "eu": EuArticleParser(),
    }
    try:
        return registry[scheme]
    except KeyError as exc:
        raise UnknownSectionScheme(
            f"unknown section scheme {scheme!r}; known: {sorted(registry)}"
        ) from exc
```

- [ ] **Step 4: Implement the three parsers**

```python
# knowledge/sections/saoso.py
import re

from knowledge.sections import ParsedSection

# "B-20.1.1 text…" or "Appendix 2 Title"
_CLAUSE = re.compile(r"^(?P<ref>[A-Z]-\d+(?:\.\d+)*)\s+(?P<body>.*)$")
_APPENDIX = re.compile(r"^(?P<ref>Appendix\s+\d+)\s+(?P<body>.*)$")


class SaosoClauseParser:
    """SAOSO cites as B-20.1.1, and appendices as 'Appendix 2'."""

    def parse(self, text: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        current: dict | None = None

        def flush():
            if current and current["body"].strip():
                sections.append(ParsedSection(
                    section_ref=current["ref"],
                    heading_path=current["ref"],
                    text=current["body"].strip(),
                ))

        for raw in text.splitlines():
            line = raw.strip()
            match = _CLAUSE.match(line) or _APPENDIX.match(line)
            if match:
                flush()
                current = {"ref": match.group("ref"), "body": match.group("body")}
            elif current is not None:
                current["body"] += "\n" + raw
        flush()
        return sections
```

```python
# knowledge/sections/opp.py
import re

from knowledge.sections import ParsedSection

_HEADING = re.compile(r"^(?P<ref>\d+(?:\.\d+)*)\s+(?P<body>[A-Z].*)$")


class OppNumberedParser:
    """The Outeniqua OPP cites as 4.1, 4.2, 6.5."""

    def parse(self, text: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        current: dict | None = None

        def flush():
            if current and current["body"].strip():
                sections.append(ParsedSection(
                    section_ref=current["ref"],
                    heading_path=current["heading"],
                    text=current["body"].strip(),
                ))

        for raw in text.splitlines():
            line = raw.strip()
            match = _HEADING.match(line)
            if match:
                flush()
                current = {"ref": match.group("ref"), "heading": match.group("body"),
                           "body": match.group("body")}
            elif current is not None:
                current["body"] += "\n" + raw
        flush()
        return sections
```

```python
# knowledge/sections/eu.py
import re

from knowledge.sections import ParsedSection

_ARTICLE = re.compile(r"^Article\s+(?P<num>\d+)\s*$", re.IGNORECASE)


class EuArticleParser:
    """EU 2018/848 cites as 'Article 9'. Proves the registry is not SAOSO-shaped."""

    def parse(self, text: str) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        current: dict | None = None

        def flush():
            if current and current["body"].strip():
                sections.append(ParsedSection(
                    section_ref=f"Article {current['num']}",
                    heading_path=f"Article {current['num']}",
                    text=current["body"].strip(),
                ))

        for raw in text.splitlines():
            match = _ARTICLE.match(raw.strip())
            if match:
                flush()
                current = {"num": match.group("num"), "body": ""}
            elif current is not None:
                current["body"] += "\n" + raw
        flush()
        return sections
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest knowledge/tests/test_section_parsers.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add knowledge/sections knowledge/tests/test_section_parsers.py
git commit -m "feat: pluggable section-reference parsers selected by data"
```

---

### Task B3: Chunker

**Files:**
- Create: `knowledge/services.py` (chunking portion)
- Test: `knowledge/tests/test_chunking.py`

- [ ] **Step 1: Write the failing test**

```python
# knowledge/tests/test_chunking.py
from knowledge.sections import ParsedSection
from knowledge.services import chunk_sections


def _section(ref: str, sentences: int) -> ParsedSection:
    return ParsedSection(section_ref=ref, heading_path=ref,
                         text=" ".join(f"Sentence {i} about organic handling."
                                      for i in range(sentences)))


def test_short_section_becomes_one_chunk():
    chunks = chunk_sections([_section("B-20.1.1", 3)], target_tokens=800)
    assert len(chunks) == 1
    assert chunks[0].section_ref == "B-20.1.1"


def test_long_section_is_split_with_overlap_and_keeps_its_ref():
    chunks = chunk_sections([_section("B-20.1.1", 400)], target_tokens=200, overlap_tokens=40)
    assert len(chunks) > 1
    assert {c.section_ref for c in chunks} == {"B-20.1.1"}
    assert all(c.token_count <= 260 for c in chunks)


def test_ordinals_are_sequential_across_sections():
    chunks = chunk_sections([_section("A-1", 3), _section("A-2", 3)], target_tokens=800)
    assert [c.ordinal for c in chunks] == [1, 2]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest knowledge/tests/test_chunking.py -v`
Expected: FAIL — `ImportError: cannot import name 'chunk_sections'`

- [ ] **Step 3: Implement the chunker**

```python
# knowledge/services.py  (chunking portion; retrieval is added in Task B6)
from dataclasses import dataclass

from knowledge.sections import ParsedSection

# Cheap, dependency-free approximation. 4 characters per token is close enough for
# chunk sizing, and avoids pulling a tokeniser into the request path.
_CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class Chunk:
    """In: none. Out: one embeddable unit. Side Effects: none. Fails: none."""

    ordinal: int
    section_ref: str
    heading_path: str
    text: str
    token_count: int


def _split(text: str, target_tokens: int, overlap_tokens: int) -> list[str]:
    target = target_tokens * _CHARS_PER_TOKEN
    overlap = overlap_tokens * _CHARS_PER_TOKEN
    if len(text) <= target:
        return [text]

    pieces, start = [], 0
    while start < len(text):
        end = min(start + target, len(text))
        # Prefer ending on a sentence boundary, but never return a tiny fragment.
        if end < len(text):
            boundary = text.rfind(". ", start + target // 2, end)
            if boundary != -1:
                end = boundary + 1
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [p for p in pieces if p]


def chunk_sections(
    sections: list[ParsedSection],
    target_tokens: int = 800,
    overlap_tokens: int = 100,
) -> list[Chunk]:
    """
    In:
        sections: list[ParsedSection] from a section parser.
        target_tokens: int, approximate target size per chunk.
        overlap_tokens: int, approximate overlap between consecutive chunks.
    Out:
        list[Chunk] with sequential ordinals and each chunk retaining its section_ref.
    Side Effects:
        None (pure).
    Fails:
        ValueError: if target_tokens <= 0 or overlap_tokens >= target_tokens.
    """
    if target_tokens <= 0:
        raise ValueError("target_tokens must be positive")
    if overlap_tokens >= target_tokens:
        raise ValueError("overlap_tokens must be smaller than target_tokens")

    chunks: list[Chunk] = []
    ordinal = 0
    for section in sections:
        for piece in _split(section.text, target_tokens, overlap_tokens):
            ordinal += 1
            chunks.append(Chunk(
                ordinal=ordinal,
                section_ref=section.section_ref,
                heading_path=section.heading_path,
                text=piece,
                token_count=len(piece) // _CHARS_PER_TOKEN,
            ))
    return chunks
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest knowledge/tests/test_chunking.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add knowledge/services.py knowledge/tests/test_chunking.py
git commit -m "feat: heading-scoped chunker with overlap"
```

---

### Task B4: Gemini embedding client with an explicit timeout

Mandatory per `build_principles.md` §VII.2.

**Files:**
- Create: `knowledge/embedding.py`
- Test: `knowledge/tests/test_embedding.py`

- [ ] **Step 1: Write the failing test**

```python
# knowledge/tests/test_embedding.py
import pytest

from knowledge import embedding


def test_embed_texts_returns_one_vector_per_input(monkeypatch):
    monkeypatch.setattr(embedding, "_call_embedding_api",
                        lambda texts, *, timeout: [[0.1] * 768 for _ in texts])
    vectors = embedding.embed_texts(["alpha", "beta"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 768


def test_empty_input_returns_empty_without_calling_the_api(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not call the API for empty input")
    monkeypatch.setattr(embedding, "_call_embedding_api", boom)
    assert embedding.embed_texts([]) == []


def test_dimension_mismatch_raises(monkeypatch):
    monkeypatch.setattr(embedding, "_call_embedding_api",
                        lambda texts, *, timeout: [[0.1] * 10 for _ in texts])
    with pytest.raises(embedding.EmbeddingDimensionError):
        embedding.embed_texts(["alpha"])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest knowledge/tests/test_embedding.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'knowledge.embedding'`

- [ ] **Step 3: Implement the client**

```python
# knowledge/embedding.py
from django.conf import settings


class EmbeddingDimensionError(ValueError):
    pass


def _call_embedding_api(texts: list[str], *, timeout: int) -> list[list[float]]:
    """Thin wrapper so tests can replace it. Never call google.generativeai elsewhere."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    out: list[list[float]] = []
    for text in texts:
        result = genai.embed_content(
            model=f"models/{settings.EMBEDDING_MODEL}",
            content=text,
            request_options={"timeout": timeout},
        )
        out.append(list(result["embedding"]))
    return out


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    In:
        texts: list[str] — the chunks to embed. May be empty.
    Out:
        list[list[float]] — one vector of settings.EMBEDDING_DIM per input, same order.
    Side Effects:
        Calls the Gemini embedding API once per text with an explicit timeout.
    Fails:
        EmbeddingDimensionError: if a returned vector's length != EMBEDDING_DIM.
        google.api_core.exceptions.*: propagated — never swallowed (BP §VII.5).
    """
    if not texts:
        return []
    vectors = _call_embedding_api(texts, timeout=settings.EXTERNAL_HTTP_TIMEOUT)
    expected = settings.EMBEDDING_DIM
    for vector in vectors:
        if len(vector) != expected:
            raise EmbeddingDimensionError(
                f"expected {expected} dims, got {len(vector)}; "
                "the embedding model changed — re-embed the whole corpus"
            )
    return vectors
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest knowledge/tests/test_embedding.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add knowledge/embedding.py knowledge/tests/test_embedding.py
git commit -m "feat: Gemini embedding client with timeout and dimension guard"
```

---

### Task B5: `ingest_standard` — idempotent ingestion

**Files:**
- Create: `knowledge/ingest.py`, `knowledge/tasks.py`,
  `knowledge/management/commands/ingest_standard.py`
- Test: `knowledge/tests/test_ingest.py`

- [ ] **Step 1: Write the failing test**

```python
# knowledge/tests/test_ingest.py
import pytest
from django.core.files.base import ContentFile

from knowledge import ingest
from knowledge.models import DocumentChunk, StandardDocument, StandardSet

SAOSO_TEXT = """\
B-20.1.1 Handlers shall not co-mingle organic products with non-organic products.
B-20.1.2 Traceability shall be ensured in the processing and handling chain.
"""


@pytest.fixture
def corpus(db):
    return StandardSet.objects.create(code="outeniqua-2026", label="Outeniqua PGS 2026")


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    monkeypatch.setattr(ingest, "embed_texts", lambda texts: [[0.0] * 768 for _ in texts])
    monkeypatch.setattr(ingest, "extract_pages", lambda path: [(1, SAOSO_TEXT)])


@pytest.mark.django_db
def test_first_ingest_creates_document_and_chunks(corpus, tmp_path):
    path = tmp_path / "saoso.pdf"
    path.write_bytes(b"%PDF-1.4 fake")

    report = ingest.ingest_document(
        standard_set=corpus, kind="STANDARD", title="SAOSO v2.1",
        version="2.1", section_scheme="saoso", path=str(path),
    )

    assert report.created is True
    assert DocumentChunk.objects.count() == 2
    document = StandardDocument.objects.get()
    assert document.chunk_count == 2
    assert document.sha256 == ingest.file_sha256(str(path))


@pytest.mark.django_db
def test_reingest_is_idempotent_on_sha256(corpus, tmp_path):
    path = tmp_path / "saoso.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    ingest.ingest_document(standard_set=corpus, kind="STANDARD", title="SAOSO v2.1",
                           version="2.1", section_scheme="saoso", path=str(path))

    report = ingest.ingest_document(standard_set=corpus, kind="STANDARD", title="SAOSO v2.1",
                                    version="2.1", section_scheme="saoso", path=str(path))

    assert report.created is False
    assert DocumentChunk.objects.count() == 2
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest knowledge/tests/test_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'knowledge.ingest'`

- [ ] **Step 3: Implement the ingestion service**

```python
# knowledge/ingest.py
import hashlib
from dataclasses import dataclass
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import transaction

from knowledge.embedding import embed_texts
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.sections.registry import get_parser
from knowledge.services import chunk_sections


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pages(path: str) -> list[tuple[int, str]]:
    """In: path. Out: [(page_number, page_text)]. Side Effects: reads the file on disk.
    Fails: pypdf.errors.PdfReadError."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    return [(i + 1, (page.extract_text() or "")) for i, page in enumerate(reader.pages)]


@dataclass(frozen=True)
class IngestionReport:
    """In: none. Out: what the run did. Side Effects: none. Fails: none."""

    document_id: int | None
    sha256: str
    chunks_written: int
    created: bool


def ingest_document(*, standard_set: StandardSet, kind: str, title: str, version: str,
                    section_scheme: str, path: str) -> IngestionReport:
    """
    In:
        standard_set: StandardSet — the corpus this document belongs to.
        kind: str (STANDARD | SOP | PRINCIPLES | GUIDANCE | LANDSCAPE).
        title, version: str — citation-facing identity.
        section_scheme: str — selects the section-reference parser.
        path: str — absolute path to the source PDF.
    Out:
        IngestionReport (document_id, sha256, chunks_written, created).
    Side Effects:
        Writes StandardDocument and DocumentChunk rows in one transaction, calls the
        embedding API, and stores the source file.
    Idempotency:
        Keyed on the file's sha256. A re-run of an already-ingested file writes nothing
        and returns created=False.
    Fails:
        UnknownSectionScheme: if section_scheme is not registered.
        EmbeddingDimensionError: if the embedding model no longer matches EMBEDDING_DIM.
    """
    sha = file_sha256(path)
    existing = StandardDocument.objects.filter(sha256=sha).first()
    if existing is not None:
        return IngestionReport(document_id=existing.id, sha256=sha,
                               chunks_written=0, created=False)

    pages = extract_pages(path)
    parser = get_parser(section_scheme)          # raises UnknownSectionScheme early
    sections = parser.parse("\n".join(text for _, text in pages))
    chunks = chunk_sections(sections)
    vectors = embed_texts([c.text for c in chunks])

    with transaction.atomic():
        document = StandardDocument(
            standard_set=standard_set, kind=kind, title=title, version=version,
            section_scheme=section_scheme, sha256=sha, chunk_count=len(chunks),
        )
        document.source_file.save(Path(path).name, ContentFile(Path(path).read_bytes()))
        DocumentChunk.objects.bulk_create([
            DocumentChunk(
                document=document, ordinal=c.ordinal, section_ref=c.section_ref,
                heading_path=c.heading_path, text=c.text, token_count=c.token_count,
                embedding=vector,
            )
            for c, vector in zip(chunks, vectors)
        ])

    return IngestionReport(document_id=document.id, sha256=sha,
                           chunks_written=len(chunks), created=True)
```

- [ ] **Step 4: Add the Celery task and management command**

```python
# knowledge/tasks.py
from celery import shared_task

from knowledge.ingest import ingest_document
from knowledge.models import StandardSet


@shared_task(autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def ingest_standard_task(standard_set_id: int, kind: str, title: str, version: str,
                         section_scheme: str, path: str) -> dict:
    report = ingest_document(
        standard_set=StandardSet.objects.get(pk=standard_set_id), kind=kind, title=title,
        version=version, section_scheme=section_scheme, path=path,
    )
    return {"document_id": report.document_id, "chunks": report.chunks_written,
            "created": report.created}
```

```python
# knowledge/management/commands/ingest_standard.py
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from knowledge.ingest import ingest_document
from knowledge.models import StandardSet

# The four real documents, mapped to their citation identity.
SOURCES = [
    ("saoso-version-2.1-2026.pdf", "STANDARD", "SAOSO Standard for Organic Production and", "2.1", "saoso"),
    ("Outeniqua pgs principles, policies and procedures 2026.pdf", "SOP", "Outeniqua PGS Principles, Policies and Procedures", "2026", "opp"),
    ("Basic Production Principles_ENG_PRINT.pdf", "PRINCIPLES", "Basic Production Principles", "2026", "opp"),
    ("PGS Certification landscape_Final.pdf", "LANDSCAPE", "South African Organic Certification Landscape", "", "opp"),
]


class Command(BaseCommand):
    help = "Ingest the source PDFs into a StandardSet. Idempotent on file sha256."

    def add_arguments(self, parser):
        parser.add_argument("--set", default="outeniqua-2026")
        parser.add_argument("--source-dir", default=str(Path(settings.BASE_DIR) / "pgs_docs"))
        parser.add_argument("--only", default=None, help="Ingest a single filename")

    def handle(self, *args, **options):
        try:
            standard_set = StandardSet.objects.get(code=options["set"])
        except StandardSet.DoesNotExist as exc:
            raise CommandError("run `manage.py seed_deployment` first") from exc

        source_dir = Path(options["source_dir"])
        for filename, kind, title, version, scheme in SOURCES:
            if options["only"] and filename != options["only"]:
                continue
            path = source_dir / filename
            if not path.exists():
                raise CommandError(f"missing source file: {path}")
            report = ingest_document(
                standard_set=standard_set, kind=kind, title=title, version=version,
                section_scheme=scheme, path=str(path),
            )
            state = "ingested" if report.created else "already present"
            self.stdout.write(f"{filename}: {state}, {report.chunks_written} chunks")
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest knowledge/tests/test_ingest.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add knowledge/ingest.py knowledge/tasks.py knowledge/management
        knowledge/tests/test_ingest.py
git commit -m "feat: idempotent standards ingestion via service, task and command"
```

---

### Task B6: Retrieval with RRF fusion, scoped to a `StandardSet`

**Files:**
- Modify: `knowledge/services.py` (append retrieval)
- Test: `knowledge/tests/test_retrieval.py`, `knowledge/tests/test_retrieval_scope.py`

- [ ] **Step 1: Write the failing tests**

```python
# knowledge/tests/test_retrieval_scope.py
import pytest

from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.services import retrieve


def _doc(corpus, title, sha):
    return StandardDocument.objects.create(
        standard_set=corpus, kind="STANDARD", title=title,
        source_file=f"standards/{sha}.pdf", sha256=sha * 64, section_scheme="saoso",
    )


@pytest.mark.django_db
def test_retrieval_never_returns_chunks_from_another_standard_set(monkeypatch):
    from knowledge import services

    outeniqua = StandardSet.objects.create(code="outeniqua-2026", label="Outeniqua")
    eu = StandardSet.objects.create(code="eu-2018-848", label="EU")

    _ = DocumentChunk.objects.create(
        document=_doc(outeniqua, "SAOSO", "a"), ordinal=1, section_ref="B-20.1.1",
        text="Handlers shall not co-mingle organic products.", embedding=[0.0] * 768,
    )
    DocumentChunk.objects.create(
        document=_doc(eu, "EU 2018/848", "b"), ordinal=1, section_ref="Article 9",
        text="Handlers shall not co-mingle organic products.", embedding=[0.0] * 768,
    )
    monkeypatch.setattr(services, "embed_query", lambda q: [0.0] * 768)

    results = retrieve("co-mingle organic products", standard_set=outeniqua, limit=10)

    assert results
    assert {r.section_ref for r in results} == {"B-20.1.1"}


@pytest.mark.django_db
def test_retrieval_returns_citable_section_refs(monkeypatch):
    from knowledge import services

    corpus = StandardSet.objects.create(code="c", label="C")
    DocumentChunk.objects.create(
        document=_doc(corpus, "SAOSO", "c"), ordinal=1, section_ref="B-20.1.1",
        text="Handlers shall not co-mingle organic products with non-organic products.",
        embedding=[0.0] * 768,
    )
    monkeypatch.setattr(services, "embed_query", lambda q: [0.0] * 768)

    results = retrieve("co-mingle organic products", standard_set=corpus, limit=5)

    assert results[0].section_ref == "B-20.1.1"
    assert results[0].document_title == "SAOSO"
    assert results[0].text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest knowledge/tests/test_retrieval_scope.py -v`
Expected: FAIL — `ImportError: cannot import name 'retrieve'`

- [ ] **Step 3: Implement retrieval**

```python
# appended to knowledge/services.py
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from pgvector.django import CosineDistance

from knowledge.models import DocumentChunk, StandardSet

RRF_K = 60  # standard reciprocal-rank-fusion constant


@dataclass(frozen=True)
class RetrievedChunk:
    """In: none. Out: a citable result. Side Effects: none. Fails: none."""

    chunk_id: int
    section_ref: str
    document_title: str
    document_version: str
    page: int | None
    text: str
    fused_score: float


def embed_query(question: str) -> list[float]:
    """Separate from embed_texts so retrieval can be tested without the API."""
    from knowledge.embedding import embed_texts
    return embed_texts([question])[0]


def _lexical_ids(question: str, document_ids: list[int], limit: int) -> list[int]:
    query = SearchQuery(question, search_type="websearch", config="english")
    rows = (
        DocumentChunk.objects.filter(document_id__in=document_ids, search_vector=query)
        .annotate(rank=SearchRank(F("search_vector"), query))
        .order_by("-rank")
        .values_list("id", flat=True)[:limit]
    )
    return list(rows)


def _semantic_ids(vector: list[float], document_ids: list[int], limit: int) -> list[int]:
    rows = (
        DocumentChunk.objects.filter(document_id__in=document_ids, embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance")
        .values_list("id", flat=True)[:limit]
    )
    return list(rows)


def retrieve(question: str, *, standard_set: StandardSet, limit: int = 5,
             candidate_pool: int = 20) -> list[RetrievedChunk]:
    """
    In:
        question: str — the user's question, already length-validated by the caller.
        standard_set: StandardSet — the corpus scope. Applied BEFORE ranking.
        limit: int — how many fused results to return.
        candidate_pool: int — how many candidates each retriever contributes.
    Out:
        list[RetrievedChunk] ordered by fused score descending, each carrying a
        section_ref that can be shown to the user as a citation.
    Side Effects:
        One embedding API call; two read-only queries.
    Fails:
        EmbeddingDimensionError: propagated from embed_query.
        ValueError: if question is empty.
    """
    if not question.strip():
        raise ValueError("question must not be empty")

    document_ids = list(
        standard_set.documents.values_list("id", flat=True)
    )  # scope first: the corpus boundary is a filter, not an instruction
    if not document_ids:
        return []

    lexical = _lexical_ids(question, document_ids, candidate_pool)
    semantic = _semantic_ids(embed_query(question), document_ids, candidate_pool)

    scores: dict[int, float] = {}
    for ranking in (lexical, semantic):
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)

    top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    if not top:
        return []

    chunks = {
        c.id: c for c in DocumentChunk.objects
        .filter(id__in=[cid for cid, _ in top])
        .select_related("document")
    }
    return [
        RetrievedChunk(
            chunk_id=cid,
            section_ref=chunks[cid].section_ref,
            document_title=chunks[cid].document.title,
            document_version=chunks[cid].document.version,
            page=chunks[cid].page,
            text=chunks[cid].text,
            fused_score=score,
        )
        for cid, score in top
        if cid in chunks
    ]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest knowledge/tests/test_retrieval_scope.py knowledge/tests/test_retrieval.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge/services.py knowledge/tests/test_retrieval_scope.py
        knowledge/tests/test_retrieval.py
git commit -m "feat: hybrid retrieval with RRF fusion, scoped to a StandardSet"
```

---

### Task B7: Seed the real corpus and prove it works

The first moment the project is demonstrably useful. Uses the real documents in `pgs_docs/`.

**Files:**
- Modify: `core/services/_seed.py` (add the `StandardSet`)
- Test: `knowledge/tests/test_real_corpus.py`

- [ ] **Step 1: Add the standard set to the seed**

```python
# appended in core/services/_seed.py — inside seed_deployment(), before the return
StandardSet.objects.update_or_create(
    code="outeniqua-2026",
    defaults={"label": "Outeniqua PGS 2026", "is_default": True,
              "description": "SAOSO 2.1, the OPP, the Basic Production Principles "
                             "and the certification landscape."},
)
```

> This import is inside `core`, which may import `knowledge`. The reverse is forbidden — see Task A7.

- [ ] **Step 2: Write the real-corpus test**

```python
# knowledge/tests/test_real_corpus.py
import pytest
from django.conf import settings
from django.core.management import call_command

from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.services import retrieve

pytestmark = pytest.mark.slow


@pytest.fixture
def corpus(db):
    return StandardSet.objects.create(code="outeniqua-2026", label="Outeniqua PGS 2026")


@pytest.mark.django_db
def test_ingesting_the_real_saoso_standard_yields_citable_clauses(corpus, monkeypatch):
    """Requires an API key; skipped in CI by marker."""
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not configured")

    call_command("ingest_standard", "--only", "saoso-version-2.1-2026.pdf", "--set", corpus.code)

    document = StandardDocument.objects.get()
    assert document.kind == "STANDARD"
    assert document.chunk_count > 100

    # The clause FORM 6.E references must be findable and citable.
    hits = DocumentChunk.objects.filter(section_ref__startswith="B-20")
    assert hits.exists()

    monkeypatch.setattr("knowledge.services.embed_query", lambda q: [0.0] * 768)
    results = retrieve("organic products not co-mingled with non-organic",
                       standard_set=corpus, limit=5)
    assert any(r.section_ref.startswith("B-20") for r in results)


@pytest.mark.django_db
def test_ingesting_the_opp_produces_numbered_sections(corpus, monkeypatch):
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not configured")

    call_command("ingest_standard", "--only",
                 "Outeniqua pgs principles, policies and procedures 2026.pdf",
                 "--set", corpus.code)

    refs = set(DocumentChunk.objects.values_list("section_ref", flat=True))
    assert {"4.1", "4.2", "6.5"} <= refs
```

- [ ] **Step 3: Run ingestion for real**

```bash
python manage.py migrate
python manage.py seed_deployment
python manage.py ingest_standard
python manage.py shell -c "from knowledge.models import DocumentChunk as C; print(C.objects.count())"
```
Expected: four documents, several hundred chunks, no errors. Re-running prints `already present` for all four and writes nothing.

- [ ] **Step 4: Run the tests**

Run: `pytest knowledge/tests -v -m "not slow"` then `pytest knowledge/tests -v -m slow`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/_seed.py knowledge/tests/test_real_corpus.py pytest.ini
git commit -m "feat: ingest the real SAOSO/OPP corpus and assert citable clauses"
```

---

**End of Sub-plan B.** Retrieval is real, scoped, idempotent, and cites the actual standard — which is what MVP 0 exists to prove.

**Sub-plans C and D follow.**

---

# Sub-plan C — Public site & documents

Produces the PGS Outeniqua public website, its content ported from WordPress, and local hosting of the standards and forms. Implements PGS_PLATFORM_SPEC §12 and D8. **Makes no certification claim** — the registry and verification pages are MVP 2.

Add `markdown` to `requirements.txt` before starting.

---

### Task C1: Base layout and design tokens

**Files:**
- Create: `core/templates/base.html`
- Create: `core/static/css/styles.css`
- Test: `core/tests/test_base_layout.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_base_layout.py
import pytest
from django.template.loader import render_to_string


@pytest.mark.django_db
def test_base_layout_has_nav_footer_and_language_switch():
    html = render_to_string("base.html", {"page_title": "Home"})

    assert "<nav" in html
    assert "How it works" in html
    assert "Members" in html
    assert "Documents" in html
    assert "<footer" in html


@pytest.mark.django_db
def test_base_layout_loads_the_single_stylesheet():
    html = render_to_string("base.html", {"page_title": "Home"})
    assert "css/styles.css" in html
    assert "cdn.tailwindcss.com" not in html       # zero build pipeline
    assert "<script type=\"module\"" not in html
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_base_layout.py -v`
Expected: FAIL — `TemplateDoesNotExist: base.html`

- [ ] **Step 3: Implement the layout**

```html
{# core/templates/base.html #}
{% load i18n static %}<!DOCTYPE html>
<html lang="{{ LANGUAGE_CODE|default:'en' }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}{{ page_title }}{% endblock %} — Outeniqua PGS</title>
  <meta name="description" content="{% trans 'Local organic certification for farmers and consumers' %}">
  <link rel="stylesheet" href="{% static 'css/styles.css' %}">
</head>
<body>
  {% include "public/_nav.html" %}
  <main id="main">{% block content %}{% endblock %}</main>
  {% include "public/_footer.html" %}

  {# Language switch: GET /i18n/setlang/ with a `language` field #}
  <form action="{% url 'set_language' %}" method="post" class="lang-switch">
    {% csrf_token %}
    <input type="hidden" name="next" value="{{ request.path }}">
    <button name="language" value="en" type="submit">EN</button>
    <button name="language" value="af" type="submit">AF</button>
  </form>
</body>
</html>
```

```html
{# core/templates/public/_nav.html #}
{% load i18n %}<nav aria-label="{% trans 'Main' %}">
  <a href="{% url 'home' %}" class="brand">Outeniqua PGS</a>
  <ul>
    <li><a href="{% url 'how_it_works' %}">{% trans "How it works" %}</a></li>
    <li><a href="{% url 'organics' %}">{% trans "What is organic" %}</a></li>
    <li><a href="{% url 'members' %}">{% trans "Members" %}</a></li>
    <li><a href="{% url 'join' %}">{% trans "Become a member" %}</a></li>
    <li><a href="{% url 'documents' %}">{% trans "Documents" %}</a></li>
    <li><a href="{% url 'chatbot' %}">{% trans "Ask a question" %}</a></li>
    <li><a href="{% url 'contact' %}">{% trans "Contact" %}</a></li>
  </ul>
</nav>
```

- [ ] **Step 4: Write `styles.css`**

A single hand-maintained stylesheet with utility-like classes and CSS custom properties. No Tailwind, no bundler (BP §IV). Include the offline-friendly basics: system font stack, `--m-`-style tokens, 44 px minimum touch targets, high contrast for outdoor reading.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest core/tests/test_base_layout.py -v`
Expected: PASS (2 passed) — requires `public/_nav.html`, `public/_footer.html` and stub URL names from Task C2.

- [ ] **Step 6: Commit**

```bash
git add core/templates core/static core/tests/test_base_layout.py requirements.txt
git commit -m "feat: public base layout with a single no-build stylesheet"
```

---

### Task C2: Content pages, ported from WordPress

Content lives as markdown in `content/`, rendered by a service — so the group can edit wording without touching templates or Python.

**Files:**
- Create: `content/{home,organics,how-it-works,members,join,contact}.md`
- Create: `core/services/_documents.py` (markdown loading)
- Create: `core/views/_public.py`, modify `core/urls.py`
- Test: `core/tests/test_public.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_public.py
import pytest
from django.urls import reverse


@pytest.mark.parametrize("name,heading", [
    ("home", "Local organic certification"),
    ("organics", "What does Organic mean"),
    ("how_it_works", "How it works"),
    ("members", "Members"),
    ("join", "Become a member"),
    ("contact", "Contact"),
])
@pytest.mark.django_db
def test_public_page_renders_with_its_heading(client, name, heading):
    response = client.get(reverse(name))
    assert response.status_code == 200
    assert heading.lower() in response.content.decode().lower()


@pytest.mark.django_db
def test_members_page_carries_the_membership_disclaimer(client):
    """The live site is explicit that membership is not certification. Ours must be too."""
    body = client.get(reverse("members")).content.decode().lower()
    assert "membership does not mean" in body
    assert "certified" in body


@pytest.mark.django_db
def test_join_page_shows_the_turnover_fee_bands(client):
    body = client.get(reverse("join")).content.decode()
    for band in ["250,000", "500,000", "1,000,000", "2,500,000", "5,000,000"]:
        assert band in body
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_public.py -v`
Expected: FAIL — `NoReverseMatch` for `home`

- [ ] **Step 3: Implement the content service**

```python
# core/services/_documents.py
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import markdown
from django.conf import settings


@dataclass(frozen=True)
class RenderedContent:
    """In: none. Out: a page body. Side Effects: none. Fails: none."""

    slug: str
    title: str
    html: str


@lru_cache(maxsize=64)
def load_content(slug: str) -> RenderedContent:
    """
    In:
        slug: str — filename stem under content/, e.g. "how-it-works".
    Out:
        RenderedContent (slug, title from the first `# ` heading, html body).
    Side Effects:
        Reads a file from disk; result is memoised in-process.
    Fails:
        FileNotFoundError: if content/<slug>.md does not exist.
    """
    path = Path(settings.BASE_DIR) / "content" / f"{slug}.md"
    raw = path.read_text(encoding="utf-8")
    title = next((line[2:].strip() for line in raw.splitlines()
                  if line.startswith("# ")), slug.replace("-", " ").title())
    html = markdown.markdown(raw, extensions=["extra", "sane_lists", "tables"])
    return RenderedContent(slug=slug, title=title, html=html)
```

- [ ] **Step 4: Implement the views and URLs**

Each view is under 20 lines (BP §II) and contains no logic beyond calling the service.

```python
# core/views/_public.py
from django.shortcuts import render

from core.services._documents import load_content


def _page(request, slug: str, template: str = "public/page.html"):
    content = load_content(slug)
    return render(request, template, {"content": content, "page_title": content.title})


def home(request):        return _page(request, "home", "public/home.html")
def organics(request):    return _page(request, "organics")
def how_it_works(request):return _page(request, "how-it-works")
def members(request):     return _page(request, "members")
def join(request):        return _page(request, "join")
def contact(request):     return _page(request, "contact")
```

```python
# appended to core/urls.py
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path

from core.views import _public

urlpatterns += i18n_patterns(
    path("", _public.home, name="home"),
    path("organics/", _public.organics, name="organics"),
    path("how-it-works/", _public.how_it_works, name="how_it_works"),
    path("members/", _public.members, name="members"),
    path("become-a-member/", _public.join, name="join"),
    path("contact/", _public.contact, name="contact"),
    prefix_default_language=False,
)
urlpatterns += [path("i18n/", include("django.conf.urls.i18n"))]
```

- [ ] **Step 5: Port the content**

Copy the text from the live WordPress pages into `content/*.md`, restyled rather than pasted verbatim (D8): `/` → `home.md`, `/organics/` → `organics.md`, `/about-2/` and the PGS explanation → `how-it-works.md`, `/members-2/` and `/farmer-members/` plus `/consumers/` → `members.md` (**keeping the membership-is-not-certification disclaimer verbatim**), `/become-a-member/` → `join.md` (including the six turnover bands), `/contact/` → `contact.md`.

Keep the redirect map in `docs/REDIRECTS.md`:

```markdown
| Old WordPress URL | New URL |
|---|---|
| /about-2/            | /how-it-works/     |
| /endorsed-farms/     | (MVP 2 — registry) |
| /farmer-members/     | /members/          |
| /consumers/          | /members/          |
| /members-2/          | /members/          |
| /forms/              | /documents/        |
| /organics/           | /organics/         |
| /become-a-member/    | /become-a-member/  |
| /news-2/             | /news/             |
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pytest core/tests/test_public.py -v`
Expected: PASS (8 passed)

- [ ] **Step 7: Commit**

```bash
git add content core/services/_documents.py core/views/_public.py core/urls.py \
        core/templates/public core/tests/test_public.py docs/REDIRECTS.md
git commit -m "feat: public content pages ported from WordPress with a redirect map"
```

---

### Task C3: `/documents/` replaces the Google Drive links

The live `/forms/` page links the standards and forms to permission-gated Drive files. This hosts them locally with stable URLs (spec §12).

**Files:**
- Create: `core/services/_documents.py` (append the catalogue)
- Create: `core/views/_documents.py`, `core/templates/documents/index.html`
- Modify: `core/urls.py`
- Test: `core/tests/test_documents.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_documents.py
import pytest
from django.urls import reverse

from core.services._documents import DOCUMENT_CATALOGUE


@pytest.mark.django_db
def test_documents_page_lists_every_source_document(client):
    body = client.get(reverse("documents")).content.decode()
    for entry in DOCUMENT_CATALOGUE:
        assert entry.title in body


@pytest.mark.django_db
def test_no_google_drive_link_remains(client):
    body = client.get(reverse("documents")).content.decode()
    assert "drive.google.com" not in body
    assert "docs.google.com" not in body


@pytest.mark.parametrize("index", range(6))
@pytest.mark.django_db
def test_each_document_is_served_locally(client, index):
    entry = DOCUMENT_CATALOGUE[index]
    response = client.get(reverse("document_file", args=[entry.slug]))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_documents.py -v`
Expected: FAIL — `ImportError: cannot import name 'DOCUMENT_CATALOGUE'`

- [ ] **Step 3: Implement the catalogue and file serving**

```python
# appended to core/services/_documents.py
from django.http import FileResponse


@dataclass(frozen=True)
class DocumentEntry:
    """In: none. Out: one published document. Side Effects: none. Fails: none."""

    slug: str
    title: str
    filename: str
    category: str


# The documents the live /forms/ page distributes, now hosted here.
DOCUMENT_CATALOGUE = [
    DocumentEntry("saoso-standard", "SAOSO Standard for Organic Production and Processing v2.1",
                  "saoso-version-2.1-2026.pdf", "Standards"),
    DocumentEntry("opp", "Outeniqua PGS Principles, Policies and Procedures",
                  "Outeniqua pgs principles, policies and procedures 2026.pdf", "Standards"),
    DocumentEntry("basic-production-principles", "Basic Production Principles",
                  "Basic Production Principles_ENG_PRINT.pdf", "Standards"),
    DocumentEntry("certification-landscape", "South African Organic Certification Landscape",
                  "PGS Certification landscape_Final.pdf", "Standards"),
    DocumentEntry("farm-visit-prep", "PGS Farm Visit Preparation List",
                  "5. PGS Farm Visit preparation list.pdf", "Forms"),
    DocumentEntry("assessment-form", "PGS Farm Visit Assessment Form (Crops, Animals, Seeds, "
                  "Agro-processing, Summary)",
                  "6. PGS Farm visit assessment form - Crops, Animals, Seeds, agro-processing, "
                  "summary_2026.xlsx", "Forms"),
    DocumentEntry("checklist-crops", "PGS Farm Visit Checklist: Crops",
                  "7.a  PGS Farm Visit Checklist_ Crops.pdf", "Checklists"),
    DocumentEntry("checklist-crops-animals", "PGS Farm Visit Checklist: Crops and Animals",
                  "7.b PGS Farm Visit Checklist - Crops _ Animals.pdf", "Checklists"),
    DocumentEntry("checklist-seed", "PGS Farm Visit Checklist: Seed Production",
                  "7.c  PGS Farm Visit Checklist - Seed Production.pdf", "Checklists"),
]


def resolve_document(slug: str) -> Path:
    """
    In:
        slug: str — a slug present in DOCUMENT_CATALOGUE.
    Out:
        Path to the document inside pgs_docs/.
    Side Effects:
        None.
    Fails:
        KeyError: if the slug is not in the catalogue (never resolves arbitrary paths).
    """
    entry = next(e for e in DOCUMENT_CATALOGUE if e.slug == slug)
    return Path(settings.BASE_DIR) / "pgs_docs" / entry.filename
```

```python
# core/views/_documents.py
from django.http import FileResponse, Http404
from django.shortcuts import render

from core.services._documents import DOCUMENT_CATALOGUE, resolve_document


def documents(request):
    by_category: dict[str, list] = {}
    for entry in DOCUMENT_CATALOGUE:
        by_category.setdefault(entry.category, []).append(entry)
    return render(request, "documents/index.html",
                  {"by_category": by_category, "page_title": "Documents"})


def document_file(request, slug: str):
    try:
        path = resolve_document(slug)
    except KeyError as exc:
        raise Http404(slug) from exc
    if not path.exists():
        raise Http404(slug)
    return FileResponse(path.open("rb"), content_type="application/pdf",
                        as_attachment=False, filename=path.name)
```

Add `path("documents/", ...)` and `path("documents/<slug:slug>/", ...)` to `core/urls.py`, named `documents` and `document_file`.

> `resolve_document` looks the slug up in a fixed catalogue rather than joining user input onto a path — so a crafted slug cannot read arbitrary files.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest core/tests/test_documents.py -v`
Expected: PASS (11 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/_documents.py core/views/_documents.py core/urls.py \
        core/templates/documents core/tests/test_documents.py
git commit -m "feat: host the standards and forms locally, retiring the Drive links"
```

---

### Task C4: Afrikaans as a first-class language

D7 requires translation from the start, not a retrofit. English must be the un-prefixed default.

**Files:**
- Create: `locale/af/LC_MESSAGES/django.po` (via `makemessages`)
- Modify: `pgs/settings.py` (already has `LANGUAGES`, `LOCALE_PATHS`, `LocaleMiddleware`)
- Test: `core/tests/test_i18n.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_i18n.py
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_english_is_the_unprefixed_default(client):
    assert client.get("/").status_code == 200
    assert "How it works" in client.get("/").content.decode()


@pytest.mark.django_db
def test_nav_renders_in_afrikaans_when_requested(client):
    response = client.get("/af/") if False else client.get("/", HTTP_ACCEPT_LANGUAGE="af")
    body = response.content.decode()
    assert "Hoe dit werk" in body
    assert "Word 'n lid" in body
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_i18n.py -v`
Expected: FAIL — nav is still English.

- [ ] **Step 3: Extract messages and translate the navigation**

```bash
python manage.py makemessages -l af
python manage.py compilemessages
```

Fill `msgstr` for every string in `public/_nav.html` and `_footer.html`, plus the page headings. Leave anything else as an empty `msgstr` — an empty translation falls back to English, which is correct behaviour and better than a bad translation.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest core/tests/test_i18n.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add locale pgs/settings.py core/tests/test_i18n.py core/templates
git commit -m "feat: Afrikaans translations for navigation and headings"
```

---

### Task C5: Claim-discipline guard and Playwright E2E

The automated half of the UAT's claim-discipline scenario. The PGS's credibility rests on not overclaiming (OPP §V, LANDSCAPE).

**Files:**
- Test: `core/tests/test_claim_discipline.py`, `tests/e2e/test_public_site.py`
- Create: `tests/conftest.py` (playwright fixtures)

- [ ] **Step 1: Write the claim-discipline test**

```python
# core/tests/test_claim_discipline.py
import pytest
from django.urls import reverse

# Terms the platform has no basis to publish (spec §12).
FORBIDDEN = ["pasture-raised", "pasture raised", "GMO free", "biodynamic",
             "chemical-free", "spray-free", "certified organic farm"]


@pytest.mark.parametrize("name", ["home", "organics", "how_it_works", "members",
                                 "join", "contact", "documents"])
@pytest.mark.django_db
def test_public_pages_make_no_unsupported_claim(client, name):
    body = client.get(reverse(name)).content.decode().lower()
    for term in FORBIDDEN:
        assert term.lower() not in body, f"{name} publishes the unsupported claim {term!r}"
```

- [ ] **Step 2: Run it**

Run: `pytest core/tests/test_claim_discipline.py -v`
Expected: PASS on a clean port. **If it fails, fix the content — not the test.** The live site's Favour Farm description is the source of the "pasture raised" phrase, and it must not be copied here.

- [ ] **Step 3: Write the Playwright E2E test**

```python
# tests/e2e/test_public_site.py
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

PAGES = [("/", "Local organic certification"), ("/organics/", "What does Organic mean"),
         ("/how-it-works/", "How it works"), ("/members/", "Members"),
         ("/become-a-member/", "Become a member"), ("/documents/", "Documents"),
         ("/contact/", "Contact")]


def test_every_public_page_loads_with_its_heading(live_server, page: Page):
    for route, heading in PAGES:
        page.goto(f"{live_server.url}{route}")
        expect(page.locator("h1")).to_contain_text(heading)


def test_navigation_reaches_documents(live_server, page: Page):
    page.goto(f"{live_server.url}/")
    page.get_by_role("link", name="Documents").click()
    expect(page).to_have_url(f"{live_server.url}/documents/")


def test_a_document_downloads_without_a_google_login(live_server, page: Page):
    page.goto(f"{live_server.url}/documents/")
    with page.expect_download() as download_info:
        page.get_by_role("link", name="SAOSO Standard").click()
    assert download_info.value.suggested_filename.endswith(".pdf")


def test_mobile_viewport_has_no_horizontal_overflow(live_server, page: Page):
    page.set_viewport_size({"width": 390, "height": 844})
    for route, _ in PAGES:
        page.goto(f"{live_server.url}{route}")
        overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        assert overflow is False, f"horizontal overflow on {route}"
```

- [ ] **Step 4: Run the E2E suite**

```bash
playwright install chromium
pytest tests/e2e -v -m e2e
```
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add core/tests/test_claim_discipline.py tests/e2e tests/conftest.py
git commit -m "test: claim-discipline guard and public-site E2E"
```

---

**End of Sub-plan C.** The public site is live-capable, bilingual, hosts its own documents, and is machine-guarded against publishing a claim the group cannot substantiate.

**Sub-plan D follows.**

---

# Sub-plan D — Grounded chatbot

Produces the strictly grounded assistant over the corpus from Sub-plan B, on the site from Sub-plan C. Implements PGS_PLATFORM_SPEC §4.6, §13 and D3. Finalises the pre-implementation UAT.

---

### Task D1: Chat models in `core`

Chat lives in `core`, not `knowledge`, because it is user-owned (§4.6) — so it may reference `User` and `DocumentChunk` without violating the one-way rule.

**Files:**
- Create: `core/models/_chat.py`
- Modify: `core/models/__init__.py`
- Test: `core/tests/test_chat_models.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_chat_models.py
import pytest

from core.models import ChatMessage, ChatSession, EscalatedQuery


@pytest.mark.django_db
def test_anonymous_session_has_no_user():
    session = ChatSession.objects.create()
    assert session.user is None
    assert session.public_uuid is not None


@pytest.mark.django_db
def test_message_records_citations_and_token_usage():
    session = ChatSession.objects.create()
    message = ChatMessage.objects.create(
        session=session, role=ChatMessage.ASSISTANT, content="An answer.",
        latency_ms=820, model="gemini-flash-latest", prompt_tokens=1500,
        completion_tokens=120,
    )
    assert message.retrieved_chunks.count() == 0
    assert message.prompt_tokens == 1500


@pytest.mark.django_db
def test_escalation_reasons_are_constrained():
    session = ChatSession.objects.create()
    message = ChatMessage.objects.create(session=session, role=ChatMessage.USER,
                                         content="Which fertiliser brand?")
    escalation = EscalatedQuery.objects.create(
        message=message, question="Which fertiliser brand?",
        reason=EscalatedQuery.INSUFFICIENT_CONTEXT,
    )
    assert escalation.status == EscalatedQuery.OPEN
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_chat_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'ChatSession'`

- [ ] **Step 3: Implement the models**

```python
# core/models/_chat.py
import uuid

from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    """A conversation. Anonymous until the visitor creates an account."""

    public_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="chat_sessions")
    # Pinned so answers stay coherent if the deployed corpus changes underneath.
    standard_set = models.ForeignKey("knowledge.StandardSet", null=True,
                                     on_delete=models.SET_NULL, related_name="chat_sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return str(self.public_uuid)


class ChatMessage(models.Model):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    ROLE_CHOICES = [(USER, "User"), (ASSISTANT, "Assistant")]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    model = models.CharField(max_length=64, blank=True)
    prompt_tokens = models.PositiveIntegerField(null=True, blank=True)
    completion_tokens = models.PositiveIntegerField(null=True, blank=True)
    retrieved_chunks = models.ManyToManyField("knowledge.DocumentChunk", blank=True,
                                              related_name="cited_in")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class EscalatedQuery(models.Model):
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    NO_CITATIONS = "NO_CITATIONS"
    USER_REQUESTED = "USER_REQUESTED"
    REASON_CHOICES = [(INSUFFICIENT_CONTEXT, "Insufficient context"),
                      (NO_CITATIONS, "No citations"), (USER_REQUESTED, "User requested")]
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"

    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE,
                               related_name="escalations")
    question = models.TextField()
    reason = models.CharField(max_length=32, choices=REASON_CHOICES)
    status = models.CharField(max_length=16, default=OPEN)
    answered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="answered_queries")
    answer = models.TextField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

- [ ] **Step 4: Migrate and run the tests**

```bash
python manage.py makemigrations core && python manage.py migrate
pytest core/tests/test_chat_models.py -v
```
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/models core/migrations core/tests/test_chat_models.py
git commit -m "feat: chat session, message and escalation models in core"
```

---

### Task D2: `answer_question()` — the strict contract

This is the heart of MVP 0 and the fix for the brittle substring contract in the original PRD (O3).

**Files:**
- Create: `core/services/_chatbot.py`
- Test: `core/tests/test_chatbot_grounding.py`

- [ ] **Step 1: Write the failing tests**

```python
# core/tests/test_chatbot_grounding.py
import json

import pytest
from django.conf import settings

from core.models import ChatSession, EscalatedQuery
from core.services import _chatbot
from core.services._chatbot import FALLBACK_TEXT, answer_question
from knowledge.models import StandardSet
from knowledge.services import RetrievedChunk


def _chunk(ref="B-20.1.1"):
    return RetrievedChunk(chunk_id=1, section_ref=ref, document_title="SAOSO v2.1",
                          document_version="2.1", page=60, text="Handlers shall not...",
                          fused_score=0.5)


@pytest.fixture
def session(db):
    return ChatSession.objects.create(
        standard_set=StandardSet.objects.create(code="c", label="C")
    )


@pytest.mark.django_db
def test_grounded_answer_returns_text_and_valid_citations(session, monkeypatch):
    monkeypatch.setattr(_chatbot, "retrieve", lambda q, **k: [_chunk()])
    monkeypatch.setattr(_chatbot, "_call_model", lambda *a, **k: {
        "answer": "Handlers must not co-mingle organic products.",
        "citations": [{"section_ref": "B-20.1.1"}],
        "insufficient_context": False,
    })

    result = answer_question(session, "Can handlers mix organic and non-organic?")

    assert result.insufficient_context is False
    assert result.text == "Handlers must not co-mingle organic products."
    assert [c.section_ref for c in result.citations] == ["B-20.1.1"]
    assert EscalatedQuery.objects.count() == 0


@pytest.mark.django_db
def test_model_says_insufficient_context(session, monkeypatch):
    monkeypatch.setattr(_chatbot, "retrieve", lambda q, **k: [_chunk()])
    monkeypatch.setattr(_chatbot, "_call_model", lambda *a, **k: {
        "answer": "Anything at all.", "citations": [], "insufficient_context": True,
    })

    result = answer_question(session, "Which fertiliser brand should I buy?")

    assert result.text == FALLBACK_TEXT
    assert result.insufficient_context is True
    assert EscalatedQuery.objects.get().reason == EscalatedQuery.INSUFFICIENT_CONTEXT


@pytest.mark.django_db
def test_citation_not_in_the_retrieved_set_is_treated_as_ungrounded(session, monkeypatch):
    """The model must not be able to invent a reference that was never retrieved."""
    monkeypatch.setattr(_chatbot, "retrieve", lambda q, **k: [_chunk("B-20.1.1")])
    monkeypatch.setattr(_chatbot, "_call_model", lambda *a, **k: {
        "answer": "See B-99.9.9.", "citations": [{"section_ref": "B-99.9.9"}],
        "insufficient_context": False,
    })

    result = answer_question(session, "Something")

    assert result.text == FALLBACK_TEXT
    assert EscalatedQuery.objects.get().reason == EscalatedQuery.NO_CITATIONS


@pytest.mark.django_db
def test_empty_retrieval_short_circuits_without_calling_the_model(session, monkeypatch):
    monkeypatch.setattr(_chatbot, "retrieve", lambda q, **k: [])

    def boom(*a, **k):
        raise AssertionError("must not call the model when nothing was retrieved")
    monkeypatch.setattr(_chatbot, "_call_model", boom)

    result = answer_question(session, "Anything")
    assert result.text == FALLBACK_TEXT


@pytest.mark.django_db
def test_fallback_text_is_exactly_the_agreed_string():
    assert FALLBACK_TEXT == "I cannot find a definitive answer in the SAOSO standards."
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_chatbot_grounding.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.services._chatbot'`

- [ ] **Step 3: Implement the service**

```python
# core/services/_chatbot.py
import hashlib
import logging
import time
from dataclasses import dataclass, field

from django.conf import settings
from django.db import transaction

from core.models import ChatMessage, ChatSession, EscalatedQuery
from knowledge.services import RetrievedChunk, retrieve

logger = logging.getLogger(__name__)

# The user-visible fallback string. Preserved verbatim from the original PRD for UX
# stability, but the *trigger* is the structured flag below, never string matching (O3).
FALLBACK_TEXT = "I cannot find a definitive answer in the SAOSO standards."

MIN_QUESTION_CHARS = 3
MAX_QUESTION_CHARS = 500

SYSTEM_PROMPT = """You answer questions about the SAOSO Standard for Organic Production \
and Processing and the Outeniqua PGS procedures, using ONLY the numbered context \
passages supplied. You must not use outside knowledge, and you must not generalise \
beyond the passages. Every assertion must be traceable to a supplied passage.

If the passages do not contain a definitive answer, set insufficient_context to true. \
Prefer admitting you do not know over inferring.

Return JSON only, matching the supplied schema. Cite by the section reference exactly \
as it appears in the passage, and never invent a reference."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section_ref": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["section_ref"],
            },
        },
        "insufficient_context": {"type": "boolean"},
    },
    "required": ["answer", "citations", "insufficient_context"],
}


@dataclass(frozen=True)
class Answer:
    """In: none. Out: a grounded reply. Side Effects: none. Fails: none."""

    text: str
    citations: list[RetrievedChunk] = field(default_factory=list)
    insufficient_context: bool = False
    escalation_id: int | None = None
    message_id: int | None = None


def _call_model(question: str, chunks: list[RetrievedChunk], *, timeout: int) -> dict:
    """Thin, replaceable boundary around Gemini. Returns parsed JSON."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL, system_instruction=SYSTEM_PROMPT)

    context = "\n\n".join(
        f"[{c.section_ref}] ({c.document_title} {c.document_version})\n{c.text}"
        for c in chunks
    )
    response = model.generate_content(
        f"Context passages:\n{context}\n\nQuestion: {question}",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=ANSWER_SCHEMA,
            temperature=0.0,
        ),
        request_options={"timeout": timeout},
    )
    import json
    return json.loads(response.text)


def _ip_hash(request) -> str:
    """Not reversible: we never store a raw IP."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = (forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", ""))
    return hashlib.sha256(ip.encode()).hexdigest()[:64]


def answer_question(session: ChatSession, question: str) -> Answer:
    """
    In:
        session: ChatSession — carries the StandardSet scope and, optionally, a user.
        question: str — the user's question.
    Out:
        Answer (text, citations, insufficient_context, escalation_id, message_id).
        `text` is either a grounded answer or exactly FALLBACK_TEXT.
    Side Effects:
        Writes a USER ChatMessage and an ASSISTANT ChatMessage; on an ungrounded
        result also writes an EscalatedQuery. One embedding call, two reads, one
        generation call.
    Fails:
        ValueError: if the question is empty or longer than MAX_QUESTION_CHARS.
        UpstreamModelError: propagated — we never fabricate an answer on failure.
    """
    question = question.strip()
    if len(question) < MIN_QUESTION_CHARS:
        raise ValueError("question is too short")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError("question is too long")

    user_message = ChatMessage.objects.create(session=session, role=ChatMessage.USER,
                                              content=question)

    chunks = retrieve(question, standard_set=session.standard_set, limit=5) if session.standard_set else []

    payload = None
    started = time.monotonic()
    if chunks:  # nothing retrieved ⇒ nothing to ground on ⇒ never call the model
        payload = _call_model(question, chunks, timeout=settings.EXTERNAL_HTTP_TIMEOUT)
    latency_ms = int((time.monotonic() - started) * 1000)

    retrieved_refs = {c.section_ref: c for c in chunks}
    cited_refs = [c.get("section_ref", "") for c in (payload or {}).get("citations", [])]
    citations = [retrieved_refs[ref] for ref in cited_refs if ref in retrieved_refs]
    # A citation the retriever never returned, or none at all, is ungrounded —
    # regardless of how confident the model sounded.
    ungrounded = (
        payload is None
        or payload.get("insufficient_context") is True
        or not citations
        or len(citations) != len([r for r in cited_refs if r])
    )

    with transaction.atomic():
        if ungrounded:
            reason = (EscalatedQuery.INSUFFICIENT_CONTEXT
                      if payload is None or payload.get("insufficient_context")
                      else EscalatedQuery.NO_CITATIONS)
            escalation = EscalatedQuery.objects.create(
                message=user_message, question=question, reason=reason,
            )
            assistant = ChatMessage.objects.create(
                session=session, role=ChatMessage.ASSISTANT, content=FALLBACK_TEXT,
                latency_ms=latency_ms, model=settings.GEMINI_MODEL if payload else "",
            )
            logger.info("chatbot escalated", extra={"reason": reason,
                                                    "session": str(session.public_uuid)})
            return Answer(text=FALLBACK_TEXT, citations=[], insufficient_context=True,
                          escalation_id=escalation.id, message_id=assistant.id)

        assistant = ChatMessage.objects.create(
            session=session, role=ChatMessage.ASSISTANT,
            content=payload["answer"], latency_ms=latency_ms, model=settings.GEMINI_MODEL,
        )
        assistant.retrieved_chunks.set([c.chunk_id for c in citations])
        return Answer(text=payload["answer"], citations=citations,
                      insufficient_context=False, message_id=assistant.id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest core/tests/test_chatbot_grounding.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/_chatbot.py core/tests/test_chatbot_grounding.py
git commit -m "feat: grounded answer_question with citation validation and structured escalation"
```

---

### Task D3: Chatbot view and HTMX partial

**Files:**
- Create: `core/forms/_chatbot.py`, `core/views/_chatbot.py`,
  `core/templates/chatbot/{panel.html,_answer.html}`
- Modify: `core/urls.py`
- Test: `core/tests/test_chatbot_view.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_chatbot_view.py
import pytest
from django.urls import reverse

from core.models import ChatSession


@pytest.mark.django_db
def test_get_creates_an_anonymous_session_and_renders_the_panel(client):
    response = client.get(reverse("chatbot"))
    assert response.status_code == 200
    assert "Ask a question" in response.content.decode()
    assert ChatSession.objects.count() == 1
    assert ChatSession.objects.get().user is None


@pytest.mark.django_db
def test_the_second_get_reuses_the_same_session(client):
    client.get(reverse("chatbot"))
    client.get(reverse("chatbot"))
    assert ChatSession.objects.count() == 1


@pytest.mark.django_db
def test_an_over_long_question_is_rejected_without_calling_the_model(client, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not reach the model")
    monkeypatch.setattr("core.services._chatbot._call_model", boom)

    response = client.post(reverse("chatbot"), {"question": "x" * 600})
    assert response.status_code == 200
    assert "too long" in response.content.decode().lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_chatbot_view.py -v`
Expected: FAIL — `NoReverseMatch: Reverse for 'chatbot' not found`

- [ ] **Step 3: Implement the form, view and templates**

```python
# core/forms/_chatbot.py
from django import forms


class QuestionForm(forms.Form):
    question = forms.CharField(
        max_length=500, min_length=3, strip=True,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ask about the organic standard…",
                                     "aria-label": "Your question"}),
    )
```

```python
# core/views/_chatbot.py
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from core.forms._chatbot import QuestionForm
from core.models import ChatSession
from core.services._chatbot import answer_question

SESSION_KEY = "chat_session_uuid"


def _get_or_create_session(request):
    from core.services._chatbot import _ip_hash
    uuid = request.session.get(SESSION_KEY)
    session = ChatSession.objects.filter(public_uuid=uuid).first() if uuid else None
    if session is None:
        session = ChatSession.objects.create(ip_hash=_ip_hash(request),
                                             user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
                                             user=request.user if request.user.is_authenticated else None)
        request.session[SESSION_KEY] = str(session.public_uuid)
    return session


@require_http_methods(["GET", "POST"])
def chatbot(request):
    session = _get_or_create_session(request)
    form, answer, error = QuestionForm(request.POST or None), None, None
    if request.method == "POST" and form.is_valid():
        try:
            answer = answer_question(session, form.cleaned_data["question"])
        except ValueError as exc:
            error = str(exc)
    context = {"form": form, "answer": answer, "error": error, "session": session,
               "page_title": "Ask a question"}
    template = "chatbot/_answer.html" if request.headers.get("HX-Request") else "chatbot/panel.html"
    return render(request, template, context)
```

```html
{# core/templates/chatbot/_answer.html — swapped in by HTMX #}
{% if error %}<p class="chat-error">{{ error }}</p>{% endif %}
{% if answer %}
  <div class="chat-answer {% if answer.insufficient_context %}ungrounded{% endif %}">
    <p>{{ answer.text }}</p>
    {% if answer.citations %}
      <ul class="citations">
        {% for c in answer.citations %}
          <li><strong>{{ c.section_ref }}</strong>
              <span class="muted">{{ c.document_title }} {{ c.document_version }}{% if c.page %}, p.{{ c.page }}{% endif %}</span>
          </li>
        {% endfor %}
      </ul>
    {% endif %}
    {% if answer.insufficient_context %}
      <form hx-post="{% url 'chatbot' %}" hx-target="#chat-thread" hx-swap="beforeend">
        {% csrf_token %}<input type="hidden" name="escalate" value="1">
        <button type="submit">Escalate to PGS committee</button>
      </form>
    {% endif %}
  </div>
{% endif %}
```

`panel.html` extends `base.html`, renders the form with `hx-post`, and targets `#chat-thread`. Add `htmx.min.js` to `core/static/js/vendor/` and include it from `base.html` with `defer` — it is one vendored file, not a build step (D1).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest core/tests/test_chatbot_view.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/forms core/views/_chatbot.py core/templates/chatbot core/static/js \
        core/urls.py core/tests/test_chatbot_view.py
git commit -m "feat: chatbot panel with HTMX partial and anonymous sessions"
```

---

### Task D4: Guardrails — rate limit, cache, token accounting

The endpoint is public and calls a paid API. R9 (abuse and cost) is a Medium risk with a cheap mitigation.

**Files:**
- Modify: `core/services/_chatbot.py`
- Test: `core/tests/test_chatbot_guardrails.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_chatbot_guardrails.py
import pytest
from django.core.cache import cache

from core.services._chatbot import RateLimited, check_rate_limit


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_requests_within_the_budget_are_allowed():
    for _ in range(20):
        check_rate_limit("abc123")


def test_the_21st_request_in_an_hour_is_rejected():
    for _ in range(20):
        check_rate_limit("abc123")
    with pytest.raises(RateLimited):
        check_rate_limit("abc123")


def test_a_different_client_has_its_own_budget():
    for _ in range(20):
        check_rate_limit("abc123")
    check_rate_limit("different")      # must not raise
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_chatbot_guardrails.py -v`
Expected: FAIL — `ImportError: cannot import name 'check_rate_limit'`

- [ ] **Step 3: Implement the guardrails**

```python
# appended to core/services/_chatbot.py
from django.core.cache import cache

RATE_LIMIT_PER_HOUR = 20
RATE_LIMIT_WINDOW = 3600


class RateLimited(Exception):
    pass


def check_rate_limit(client_key: str) -> int:
    """
    In:
        client_key: str — a hashed client identifier (never a raw IP).
    Out:
        int — remaining budget after this request.
    Side Effects:
        Increments a cache counter with a one-hour TTL.
    Fails:
        RateLimited: when the hourly budget is exhausted.
    """
    key = f"chatbot:rl:{client_key}"
    used = cache.get(key, 0)
    if used >= RATE_LIMIT_PER_HOUR:
        raise RateLimited("too many questions from this connection; try again later")
    cache.set(key, used + 1, RATE_LIMIT_WINDOW)
    return RATE_LIMIT_PER_HOUR - (used + 1)
```

Then, in `answer_question`, before writing the user message:

```python
    cached = cache.get(_cache_key(session.standard_set_id, question))
    if cached is not None:
        assistant = ChatMessage.objects.create(
            session=session, role=ChatMessage.ASSISTANT, content=cached["text"],
            model="cache",
        )
        return Answer(text=cached["text"], insufficient_context=cached["insufficient"],
                      message_id=assistant.id)
```

with:

```python
ANSWER_CACHE_TTL = 60 * 60 * 24 * 7


def _cache_key(standard_set_id: int | None, question: str) -> str:
    digest = hashlib.sha256(f"{standard_set_id}:{question.lower()}".encode()).hexdigest()
    return f"chatbot:answer:{digest}"
```

and store the result via `cache.set(_cache_key(...), {"text": ..., "insufficient": ...}, ANSWER_CACHE_TTL)` on both the grounded and the fallback paths. Call `check_rate_limit(session.ip_hash)` in the view before `answer_question`, and render the rate-limit message on `RateLimited`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest core/tests/test_chatbot_guardrails.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/_chatbot.py core/views/_chatbot.py core/tests/test_chatbot_guardrails.py
git commit -m "feat: chatbot rate limiting and answer caching"
```

---

### Task D5: Escalation queue for the committee

An escalation that nobody ever sees is worse than no escalation at all — it silently swallows the questions the chatbot could not answer.

**Files:**
- Create: `core/views/_committee.py`, `core/templates/committee/escalations.html`
- Modify: `core/urls.py`
- Test: `core/tests/test_escalation_queue.py`

- [ ] **Step 1: Write the failing test**

```python
# core/tests/test_escalation_queue.py
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import ChatMessage, ChatSession, EscalatedQuery, UserRole

User = get_user_model()


@pytest.fixture
def committee_client(client, db):
    user = User.objects.create_user(email="c@example.com", password="x")
    UserRole.objects.create(user=user, role=UserRole.COMMITTEE)
    client.force_login(user)
    return client


@pytest.fixture
def escalation(db):
    session = ChatSession.objects.create()
    message = ChatMessage.objects.create(session=session, role=ChatMessage.USER,
                                         content="Which fertiliser brand?")
    return EscalatedQuery.objects.create(message=message, question="Which fertiliser brand?",
                                         reason=EscalatedQuery.INSUFFICIENT_CONTEXT)


@pytest.mark.django_db
def test_committee_member_sees_the_open_escalation(committee_client, escalation):
    body = committee_client.get(reverse("escalations")).content.decode()
    assert "Which fertiliser brand?" in body


@pytest.mark.django_db
def test_anonymous_user_is_redirected_to_login(client, escalation):
    response = client.get(reverse("escalations"))
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_member_without_the_role_is_forbidden(client, escalation):
    user = User.objects.create_user(email="f@example.com", password="x")
    UserRole.objects.create(user=user, role=UserRole.FARMER)
    client.force_login(user)
    assert client.get(reverse("escalations")).status_code == 403
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest core/tests/test_escalation_queue.py -v`
Expected: FAIL — `NoReverseMatch: Reverse for 'escalations' not found`

- [ ] **Step 3: Implement the view and template**

```python
# core/views/_committee.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import render

from core.models import EscalatedQuery


def _is_committee(user) -> bool:
    return user.has_role("COMMITTEE", "ADMIN")


@login_required
def escalations(request):
    if not _is_committee(request.user):
        return HttpResponseForbidden()
    rows = (EscalatedQuery.objects.filter(status=EscalatedQuery.OPEN)
            .select_related("message__session").order_by("created_at"))
    return render(request, "committee/escalations.html",
                  {"rows": rows, "page_title": "Unanswered questions"})
```

Register `path("committee/questions/", escalations, name="escalations")` in `core/urls.py`, **outside** `i18n_patterns` so the URL stays stable.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest core/tests/test_escalation_queue.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/views/_committee.py core/templates/committee core/urls.py \
        core/tests/test_escalation_queue.py
git commit -m "feat: committee escalation queue for unanswered questions"
```

---

### Task D6: Chatbot E2E, then run the UAT

**Files:**
- Create: `tests/e2e/test_chatbot.py`

- [ ] **Step 1: Write the E2E test**

```python
# tests/e2e/test_chatbot.py
import pytest
from playwright.sync_api import Page, expect

from core.services._chatbot import FALLBACK_TEXT

pytestmark = pytest.mark.e2e


def test_asking_a_question_returns_an_answer_with_a_citation(live_server, page: Page,
                                                             seeded_corpus):
    page.goto(f"{live_server.url}/ask/")
    page.get_by_label("Your question").fill(
        "What does the standard say about co-mingling organic and non-organic products?"
    )
    page.get_by_role("button", name="Ask").click()

    expect(page.locator(".chat-answer, .chat-error")).to_be_visible(timeout=30_000)


def test_an_out_of_scope_question_offers_escalation(live_server, page: Page, seeded_corpus):
    page.goto(f"{live_server.url}/ask/")
    page.get_by_label("Your question").fill("Which fertiliser brand should I buy in George?")
    page.get_by_role("button", name="Ask").click()

    expect(page.get_by_text(FALLBACK_TEXT)).to_be_visible(timeout=30_000)
    expect(page.get_by_role("button", name="Escalate to PGS committee")).to_be_visible()
```

- [ ] **Step 2: Run the E2E suite**

```bash
pytest tests/e2e -v -m e2e
```
Expected: PASS

- [ ] **Step 3: Run the full gate**

```bash
make check            # tests + import contracts + lint
pytest -m "not slow"
```
Expected: all green.

- [ ] **Step 4: Run the UAT checklist**

Hand `tests/uat/mvp0_standards_and_public_site_uat.md` to the human partner. Every scenario is a judgement call a machine cannot make — grounding plausibility, citation accuracy against the real PDF, the tone of the refusal, Afrikaans quality, and usability on a real phone.

**Do not proceed to the next MVP until the sign-off table is filled in or exceptions are recorded with a decision to proceed.**

- [ ] **Step 5: Commit and tag**

```bash
git add tests/e2e/test_chatbot.py
git commit -m "test: chatbot E2E for grounded answers and escalation"
git tag -a mvp0 -m "MVP 0: standards foundation and public shop window"
```

---

**End of Sub-plan D — and of MVP 0.**

## MVP 0 completion criteria

- [ ] `make check` green: tests, `lint-imports`, lint.
- [ ] `python manage.py ingest_standard` ingests all four real documents; a second run writes nothing.
- [ ] `/health/` reports all four dependencies `ok`.
- [ ] Every public page loads in English and (for navigation at least) in Afrikaans, with no horizontal overflow at 390 px.
- [ ] `/documents/` serves every source document locally with no Drive link remaining.
- [ ] An out-of-scope question returns exactly `FALLBACK_TEXT` and creates one `EscalatedQuery`.
- [ ] No citation can reference a chunk outside the session's `StandardSet`.
- [ ] The claim-discipline test passes — no unsupported claim on any public page.
- [ ] Backup runs to the external drive; a restore has been rehearsed and its output recorded in `docs/RUNBOOK.md`.
- [ ] `tests/uat/mvp0_standards_and_public_site_uat.md` sign-off table complete.
- [ ] **No migration was required to add a document, a seal or a category** — the D12 acceptance test.

## Handoff

The plan is complete and appended to `product/backlog/Refinement/MVP0_PLAN.md`.

Execute with the `executing-plans` skill: one sub-plan per session, stopping at each checkpoint for review. Sub-plan A must be executed first; B and C are independent of each other and can be taken in either order; D depends on both.
