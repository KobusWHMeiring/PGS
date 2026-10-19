"""The project's Celery app.

One app, imported by the worker (`celery -A pgs`) and by the health check. Two apps
would be worse than none: `/health/` would report on a broker connection the worker
does not use, so it could report `celery_worker: ok` while the deployment's real
worker was dead — a check that passes while the thing it checks is broken.

`namespace="CELERY"` makes Celery read `CELERY_BROKER_URL` and friends from Django
settings, which is what `pgs/settings.py` already defines. Without it, Celery would
fall back to `BROKER_URL` and quietly ignore every setting A2 wrote.
"""

from __future__ import annotations

import os

from celery import Celery

# `DJANGO_SETTINGS_MODULE` must be set before the app reads settings, and the worker
# process does not run `manage.py`, so it cannot rely on the manage.py default.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")

app = Celery("pgs", namespace="CELERY")

# Read config from Django settings, upper-cased, using `CELERY_` as the prefix —
# so `CELERY_BROKER_URL` in settings becomes `app.conf.broker_url`.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover `@shared_task`s in every installed app. Without this the worker starts
# with an empty registry and silently discards every queued task it receives.
app.autodiscover_tasks()
