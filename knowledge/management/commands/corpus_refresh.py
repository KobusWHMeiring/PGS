"""`manage.py corpus_refresh [--apply]` — re-ingest the documents that drifted (P2.3)

Exactly `ingest_standard --force` per drifted document, from that document's reviewed
artefact. **Read-only without `--apply`**: it prints what it would do, and — before
anything is destroyed — how many chat citation links the re-ingest will drop. `--force`
deletes the old chunks and every `retrieved_chunks` row that pointed at them; the chat
turn's stored grounding snapshot survives (P2.5a), the join does not.

    python manage.py corpus_refresh            # what would happen
    python manage.py corpus_refresh --apply    # do it

Deliberate, never automatic. `deploy/deploy.sh` runs `corpus_check` and warns; it does not
run this, because a deploy that re-embeds four documents and drops citation links is not a
deploy step (D56). Run it as the operator, once, when the report says to.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from knowledge.drift import citation_links, corpus_states, pdf_path_for
from knowledge.ingest import IngestError, ingest_standard, resolve_standard_set


class Command(BaseCommand):
    help = "Re-ingest drifted documents from their reviewed artefacts (dry run by default)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--set",
            dest="set_code",
            help="StandardSet code. Defaults to the single is_default set.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually re-ingest. Without it the command only reports.",
        )
        parser.add_argument(
            "--no-embed",
            dest="embed",
            action="store_false",
            help="Skip embeddings. The corpus stays lexical until it is re-embedded.",
        )

    def handle(self, *args, **options) -> None:
        try:
            standard_set = resolve_standard_set(options.get("set_code"))
        except IngestError as error:
            raise CommandError(str(error)) from error

        states = corpus_states(standard_set)
        todo = [state for state in states if state.needs_refresh]
        blocked = [state for state in states if state.is_broken and not state.needs_refresh]

        if not todo:
            self.stdout.write(self.style.SUCCESS("nothing to refresh"))
            for state in states:
                self.stdout.write(f"  {state.doc_key}: {state.state}")
        else:
            self._report(todo)

        if blocked:
            # Named rather than attempted: a document nobody ingested has no PDF path to
            # refresh from, and inventing one here would be the command guessing.
            for state in blocked:
                self.stdout.write(
                    self.style.ERROR(f"cannot refresh {state.doc_key}: {state.detail}")
                )
                self.stdout.write(
                    f"  fix: python manage.py ingest_standard --doc {state.doc_key} "
                    "--file <pdf>"
                )

        if not options["apply"]:
            if todo:
                self.stdout.write("")
                self.stdout.write("Dry run. Nothing was written. Re-run with --apply.")
            return

        failures = []
        for state in todo:
            if self._refresh(state, standard_set, options["embed"]):
                continue
            failures.append(state.doc_key)
        if failures or blocked:
            raise CommandError(
                "corpus is still not current: "
                + ", ".join(failures + [state.doc_key for state in blocked])
            )
        self.stdout.write(self.style.SUCCESS("corpus refreshed from artefacts"))

    def _report(self, todo) -> None:
        """Say what would change, including the cost — before `--apply` can spend it."""
        self.stdout.write("would re-ingest:")
        for state in todo:
            cost = citation_links(state.document) if state.document is not None else 0
            self.stdout.write(
                f"  {state.doc_key}: {state.detail}\n"
                f"    {state.stored_chunks} -> {state.expected_chunks} chunks, "
                f"{cost} chat citation link(s) will be dropped, from {state.artefact.name}"
            )

    def _refresh(self, state, standard_set, embed: bool) -> bool:
        """Re-ingest one document. Out: True on success. Raises nothing: the caller
        collects the failures so one bad document does not hide the rest."""
        pdf_path = pdf_path_for(state.document)
        if not pdf_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"cannot refresh {state.doc_key}: the PDF it was ingested from is not "
                    f"here ({pdf_path}). Ingest it first with --from-pdf on a machine that "
                    "has the file."
                )
            )
            return False
        try:
            report = ingest_standard(
                pdf_path=pdf_path,
                standard_set=standard_set,
                doc_key=state.doc_key,
                embed=embed,
                force=True,
                corpus_path=state.artefact,
            )
        except IngestError as error:
            self.stdout.write(self.style.ERROR(f"{state.doc_key}: {error}"))
            return False
        for warning in report.warnings:
            self.stdout.write(self.style.WARNING(f"{state.doc_key}: {warning}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"  {state.doc_key}: re-ingested {report.chunk_count} chunks "
                f"(embedded={report.embedded})"
            )
        )
        return True
