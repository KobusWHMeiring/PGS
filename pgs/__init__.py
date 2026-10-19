"""`pgs` project package.

`celery_app` is exported here because `celery -A pgs` looks for it on the package,
and because Celery's shared-task registry attaches to *the current app* — so the
worker and `@shared_task` must agree on which app that is. Exporting it is what makes
`@shared_task` in `core.tasks` register into the same registry the worker reads.

Imported lazily-ish: `pgs/celery.py` sets `DJANGO_SETTINGS_MODULE` before reading
settings, so this import is safe from the worker, which does not run `manage.py`.
"""

from pgs.celery import app as celery_app

__all__ = ["celery_app"]
