"""`manage.py seed_deployment` — apply the group's data to this deployment.

Thin command, per `build_principles.md` §II: it parses options and calls one
service. All the rules live in `core/services/_seed.py`.

Idempotent by design, so it belongs in the deploy script rather than in a manual
runbook step someone will forget. It never reactivates a seal a deployment has
deliberately retired.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from core.services._seed import seed_deployment


class Command(BaseCommand):
    help = "Seed the deployment's seals and assessment categories (idempotent)."

    def handle(self, *args, **options):
        result = seed_deployment()
        for kind, (created, updated) in result.items():
            self.stdout.write(
                f"{kind}: {created} created, {updated} updated"
                + (" (is_active left untouched on existing rows)" if updated else "")
            )
        self.stdout.write(self.style.SUCCESS("seed_deployment complete"))
