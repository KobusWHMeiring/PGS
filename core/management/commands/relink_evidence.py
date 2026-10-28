"""`manage.py relink_evidence` — restore a turn's evidence links after a `--force` re-ingest.

Thin command, per `build_principles.md` §II: every rule lives in
`core/services/_evidence.py`.

    python manage.py relink_evidence            # what would be restored, and what cannot be
    python manage.py relink_evidence --apply    # restore the links

Run it **after** `ingest_standard --force` and before anything else touches the corpus.
The links are restored only where the passage's text is byte-identical to what the answer
stood on; a passage the rebuild changed is reported and left unlinked, because a link that
resolves to different words is a citation that lies (`HANDOVER.md` §17, D68 Q8).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core.services._evidence import NothingToRelink, relink_evidence, render_relink_report


class Command(BaseCommand):
    help = (
        "Rebuild ChatMessage.retrieved_chunks from the grounding snapshot after a "
        "--force re-ingest. Report-only unless --apply."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the links. Without it the command only reports what it would do.",
        )

    def handle(self, *args, **options):
        try:
            report = relink_evidence(write=options["apply"])
        except NothingToRelink as error:
            raise CommandError(str(error)) from error
        self.stdout.write(render_relink_report(report))
