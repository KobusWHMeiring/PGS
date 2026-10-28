"""`manage.py corpus_check` — is this box serving the corpus its artefacts describe? (P2.2)

Read-only. Prints one row per governed document and exits non-zero when the corpus is not
current, naming the command that fixes it. It never runs that command: refreshing a corpus
drops every chat turn's `retrieved_chunks` links and re-embeds four documents, which is a
decision for a person (D56).

    python manage.py corpus_check

A deploy runs this and **warns** (`deploy/deploy.sh`, P2.4) — it never blocks. A first
install has an empty corpus, and refusing to deploy over a stale corpus is worse than
reporting one.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from knowledge.drift import NO_ARTEFACT, corpus_states
from knowledge.ingest import IngestError, resolve_standard_set


class Command(BaseCommand):
    help = "Report whether the stored corpus matches its reviewed artefacts (read-only)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--set",
            dest="set_code",
            help="StandardSet code. Defaults to the single is_default set.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Print only the state rows, not the summary and the fix.",
        )

    def handle(self, *args, **options) -> None:
        try:
            standard_set = resolve_standard_set(options.get("set_code"))
        except IngestError as error:
            raise CommandError(str(error)) from error

        states = corpus_states(standard_set)
        self.stdout.write(
            f"corpus set: {standard_set.code} ({len(states)} governed document(s))"
        )
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"{'document':<10} {'state':<18} {'chunks':>13}  artefact"
            )
        )
        for state in states:
            chunks = (
                f"{state.stored_chunks} / {state.expected_chunks}"
                if state.expected_chunks is not None
                else "-"
            )
            artefact = "-" if state.artefact is None else state.artefact.name
            line = f"{state.doc_key:<10} {state.state:<18} {chunks:>13}  {artefact}"
            if state.is_broken:
                self.stdout.write(self.style.ERROR(line))
            elif state.state == NO_ARTEFACT:
                self.stdout.write(self.style.WARNING(line))
            else:
                self.stdout.write(line)
            if state.detail:
                self.stdout.write(f"{'':<10} {state.detail}")

        broken = [state for state in states if state.is_broken]
        if not options["quiet"]:
            self.stdout.write("")
            if broken:
                self.stdout.write(
                    self.style.ERROR(
                        f"corpus is NOT current: {', '.join(s.doc_key for s in broken)}"
                    )
                )
                self.stdout.write(
                    "Fix: python manage.py corpus_refresh --apply "
                    "(re-ingests from the artefacts and re-embeds)"
                )
            else:
                self.stdout.write(self.style.SUCCESS("corpus is current"))
        if broken:
            # Non-zero is the whole point: a deploy script can only see an exit status.
            raise CommandError(
                f"{len(broken)} document(s) not current: "
                + ", ".join(state.doc_key for state in broken)
            )
