"""`manage.py ingest_standard` — the thin command over `knowledge.ingest` (B6).

Routing only: resolve the corpus set, call the service, print its report. The logic
lives in `knowledge/ingest.py` because a management command is a view onto the service
layer, and the service is what has to be testable without invoking Django's command
machinery (`build_principles.md` §II).

    python manage.py ingest_standard --doc saoso --file pgs_docs/saoso-version-2.1-2026.pdf

Re-running is safe: re-ingestion is idempotent on the file's sha256 within a
`StandardSet`, so a second run reports "already ingested" and writes nothing.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from knowledge.ingest import (
    CORPUS_DOCUMENTS,
    IngestError,
    ingest_standard,
    resolve_standard_set,
)
from knowledge.sections.registry import schemes


class Command(BaseCommand):
    help = "Ingest a governed document into a StandardSet (idempotent on sha256)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--doc",
            choices=sorted(CORPUS_DOCUMENTS),
            help="A known corpus document (D16); sets kind/title/scheme defaults.",
        )
        parser.add_argument("--file", required=True, help="Path to the PDF.")
        parser.add_argument(
            "--set",
            dest="set_code",
            help="StandardSet code. Defaults to the single is_default set.",
        )
        parser.add_argument("--title", help="Override the document title.")
        parser.add_argument("--kind", help="Override the document kind, e.g. STANDARD.")
        parser.add_argument("--issuing-body", dest="issuing_body", help="Override.")
        parser.add_argument(
            "--doc-version",
            dest="version",
            help=(
                "Override the printed version, e.g. 2.1. Named `--doc-version` rather "
                "than the plan's `--version` because Django's BaseCommand already "
                "reserves `--version` and argparse refuses the duplicate."
            ),
        )
        parser.add_argument(
            "--scheme",
            dest="section_scheme",
            choices=sorted(schemes()),
            help="Override the section-reference parser selected for this document.",
        )
        parser.add_argument(
            "--no-embed",
            dest="embed",
            action="store_false",
            help="Skip embeddings (chunks are written; retrieval stays lexical).",
        )

    def handle(self, *args, **options) -> None:
        try:
            standard_set = resolve_standard_set(options.get("set_code"))
            report = ingest_standard(
                pdf_path=Path(options["file"]),
                standard_set=standard_set,
                doc_key=options.get("doc"),
                kind=options.get("kind"),
                issuing_body=options.get("issuing_body"),
                title=options.get("title"),
                version=options.get("version"),
                section_scheme=options.get("section_scheme"),
                embed=options["embed"],
            )
        except IngestError as error:
            # `CommandError` is what makes the exit status non-zero: a failed ingest
            # must not be mistaken for a successful no-op by a script or a deploy.
            raise CommandError(str(error)) from error

        state = "created" if report.created else "already present"
        self.stdout.write(
            f"document #{report.document_id} {state}: {report.chunk_count} chunks, "
            f"embedded={report.embedded}"
        )
        if report.duplicate_refs:
            self.stdout.write(
                self.style.WARNING(f"duplicate section refs: {report.duplicate_refs}")
            )
        for warning in report.warnings:
            self.stdout.write(self.style.WARNING(f"warning: {warning}"))
