"""`manage.py publish_documents` — put the shipped documents at their public addresses.

Thin command, per `build_principles.md` §II: it parses options and calls one service.
Every rule lives in `core/services/_documents.py`.

It belongs in the deploy script beside `seed_deployment`, for the same reason: it is
idempotent, so the alternative is a runbook step that someone forgets on the one
machine that matters. A deployment that skips it serves `/documents/` with no rows —
and, if it has rows but no files, 503s loudly rather than 404ing quietly.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.services._documents import DocumentSourceMissing, publish_documents


class Command(BaseCommand):
    help = "Copy the group's documents into MEDIA_ROOT/public/documents/ and upsert rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=None,
            help="Directory to read the shipped documents from (default: pgs_docs/).",
        )

    def handle(self, *args, **options):
        try:
            result = publish_documents(
                Path(options["source"]) if options["source"] else None
            )
        except DocumentSourceMissing as exc:
            # A CommandError, not a traceback: the operator can act on this one.
            raise CommandError(str(exc)) from exc

        self.stdout.write(f"documents: {result}")
        self.stdout.write(self.style.SUCCESS("publish_documents complete"))
        # Returned as well as printed: `call_command` hands this back to the tests,
        # which is how the idempotency assertion reads the counts.
        return f"documents: {result}"
