"""The public document library - which files are published, and how they get there.

Two jobs, deliberately in one module because they are the same decision seen twice:
**what the group publishes** (`DOCUMENTS`, the data) and **how the served copy comes
to exist** (`publish_documents`, the deploy step). Splitting them invites the two to
disagree - a spec added here and never copied would 503 at request time, which is why
the copy and the row are written from the same tuple in one pass.

The **reader** - the page `/documents/<code>/read/` renders - lives in
`_document_reader.py` (its shapes in `_document_shapes.py`). It reads the corpus; nothing
here does.
"""

from __future__ import annotations


from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from django.conf import settings
from django.db import transaction
from django.urls import reverse

from core.models import PublicDocument
from core.services._document_reader import reader_for
from knowledge.models import DocumentChunk

logger = logging.getLogger(__name__)


#: The shipped documents. `PDF`s only: D22's workbook is not here until the committee
#: confirms it, and `content_inventory.md` §6.8's pledge downloads are not D22 items.
#:
#: Anchored to `BASE_DIR`, NOT a bare `Path("pgs_docs")`. A relative path resolves
#: against the process's working directory, and the two callers that matter do not
#: share one: systemd sets `WorkingDirectory` to the app dir, while a provisioning
#: script run as `sudo bash /home/carbonplanner/apps/pgs/deploy/first-install.sh`
#: inherits the caller's `~`. The first production install failed exactly here —
#: `CommandError: saoso-standard-v2.1: pgs_docs/saoso-version-2.1-2026.pdf is not in
#: the tree` — with all eight PDFs present in the checkout.
DOCS_SOURCE_DIR = Path(settings.BASE_DIR) / "pgs_docs"

#: Under MEDIA_ROOT. The `public/` segment is the boundary from PRIVATE_MEDIA_ROOT.
PUBLIC_SUBDIR = Path("public") / "documents"


@dataclass(frozen=True)
class DocumentSpec:
    """One document the group publishes.

    In: none. Out: a row and a served file. Side effects: none.
    Fails: nothing here — `publish_documents` fails if `source` is not on disk.

    `note` is the one-line description the design prints under the title. It is in
    Python rather than in a template for the same reason the fee figures are: one
    source, and a test can compare the two pages that show the same document.
    """

    code: str
    title: str
    note: str
    source: str
    download_name: str
    display_order: int
    is_published: bool = True


#: Order follows the documents page and the home page's band: the four governed
#: documents first (D16's corpus), then the working forms.
DOCUMENTS: tuple[DocumentSpec, ...] = (
    DocumentSpec(
        code="saoso-standard-v2.1",
        title="SAOSO Organic Standard v2.1",
        note="The standard we assess against · 2026",
        source="saoso-version-2.1-2026.pdf",
        download_name="SAOSO-Organic-Standard-v2.1.pdf",
        display_order=10,
    ),
    DocumentSpec(
        code="opp",
        title="Principles, Policies & Procedures",
        note="How our own PGS is governed",
        source="Outeniqua pgs principles, policies and procedures 2026.pdf",
        download_name="Outeniqua-PGS-Principles-Policies-Procedures.pdf",
        display_order=20,
    ),
    DocumentSpec(
        code="basic-production-principles",
        title="Basic Production Principles",
        note="Growing the organic sector in South Africa",
        source="Basic Production Principles_ENG_PRINT.pdf",
        download_name="Basic-Production-Principles.pdf",
        display_order=30,
    ),
    DocumentSpec(
        code="certification-landscape",
        title="Certification Landscape",
        note="Seals and recognition in the SA organic sector",
        source="PGS Certification landscape_Final.pdf",
        download_name="Certification-Landscape.pdf",
        display_order=40,
    ),
    DocumentSpec(
        code="farm-visit-preparation",
        title="Farm Visit Preparation List",
        note="What to have ready before the visit",
        source="5. PGS Farm Visit preparation list.pdf",
        download_name="PGS-Farm-Visit-Preparation-List.pdf",
        display_order=50,
    ),
    DocumentSpec(
        code="checklist-crops",
        title="Checklist — Crops",
        note="Blank participant checklist",
        source="7.a  PGS Farm Visit Checklist_ Crops.pdf",
        download_name="PGS-Farm-Visit-Checklist-Crops.pdf",
        display_order=60,
    ),
    DocumentSpec(
        code="checklist-crops-animals",
        title="Checklist — Crops & Animals",
        note="Blank participant checklist",
        source="7.b PGS Farm Visit Checklist - Crops _ Animals.pdf",
        download_name="PGS-Farm-Visit-Checklist-Crops-and-Animals.pdf",
        display_order=70,
    ),
    DocumentSpec(
        code="checklist-seed-production",
        title="Checklist — Seed Production",
        note="Blank participant checklist",
        source="7.c  PGS Farm Visit Checklist - Seed Production.pdf",
        download_name="PGS-Farm-Visit-Checklist-Seed-Production.pdf",
        display_order=80,
    ),
)


class PublishResult(NamedTuple):
    """What `publish_documents` did. Printed by the command, asserted by the tests."""

    created: int
    updated: int
    copied: int
    unchanged: int

    def __str__(self) -> str:
        return (
            f"created={self.created} updated={self.updated} "
            f"copied={self.copied} unchanged={self.unchanged}"
        )


class DocumentSourceMissing(RuntimeError):
    """A spec names a file the repository does not ship. Never silently skipped."""


def sha256_of(path: Path) -> str:
    """The digest both the copy step and the tests compare. Read in chunks: the BPP
    is 4.6 MB and reading several of those whole into memory buys nothing."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 256), b""):
            digest.update(block)
    return digest.hexdigest()


def absolute_path(document: PublicDocument) -> Path:
    """Where the served file lives, resolved **at call time**.

    Not a `FileField` — see `core/models/_public.py` for why a storage location is the
    wrong thing to cache here.
    """
    return Path(settings.MEDIA_ROOT) / document.file_path


def published_documents() -> list[PublicDocument]:
    """The documents a public page may show. One query, ordered by the seed."""
    return list(PublicDocument.objects.published())


@dataclass(frozen=True)
class DocumentRow:
    """One line of the public document list: the file, and where its text can be read.

    `read_url` is empty for a document whose text is not ingested. That is not a disabled
    control: a form is published as a file, and that is the whole truth about it
    (`DOCUMENTS_READER_LINK_PRD` D2). The row prints nothing rather than a promise the
    reader page would have to take back.
    """

    document: PublicDocument
    read_url: str = ""


def public_codes_by_source() -> dict[str, str]:
    """In: nothing. Out: `{source_file: code}` for the published documents. One query.

    The join that makes a citation clickable without a migration: `PublicDocument.source_path`
    and `StandardDocument.source_file` both hold `pgs_docs/<file>.pdf`, because the publish
    seed and the ingest read the same filenames — `source_path` exists precisely so a
    published file can be traced to the shipped document.

    A corpus document with no published twin is simply absent from the mapping, and a
    citation from it renders as text rather than as a link to nowhere. Only **published**
    documents are listed: `is_published` is the only gate, and a citation is not an exception
    to it.
    """
    return {
        document.source_path: document.code
        for document in PublicDocument.objects.published().exclude(source_path="")
    }


def documents_context() -> dict:
    """The context fragment every page that carries the list needs.

    In: none. Out: `{"documents": [DocumentRow, ...]}`. Side effects: two queries.
    Fails: never deliberately.

    Each row carries the reader's address **when the document's text is ingested**, and an
    empty string when it is not. The set is resolved once for the whole list rather than by
    asking `corpus_for()` per row: that function is a query, and a public page must not grow a
    query each time the group publishes a ninth document (`DOCUMENTS_READER_LINK_PRD` §4).
    """
    documents = published_documents()
    with_text = ingested_sources()
    return {
        "documents": [
            DocumentRow(
                document=document,
                read_url=(
                    reverse("core:document_reader", kwargs={"code": document.code})
                    if document.source_path in with_text
                    else ""
                ),
            )
            for document in documents
        ]
    }


def ingested_sources() -> set[str]:
    """In: nothing. Out: the `source_file` of every corpus document that holds text.

    One query, and the join is provenance: `PublicDocument.source_path` and
    `StandardDocument.source_file` both hold `pgs_docs/<file>.pdf`, because the publish seed
    and the ingest read the same filenames.

    Derived from `DocumentChunk`, not from `StandardDocument.chunk_count`: a denormalised
    counter is one interrupted ingest away from promising a reader a page with no text in it,
    and this is the value that decides whether the row prints the link at all.
    """
    return set(
        DocumentChunk.objects.values_list("document__source_file", flat=True).distinct()
    )


def _recorded_source(source: Path) -> str:
    """The path as `source_path` records it: repository-relative whenever it can be.

    Absolute would be wrong in two ways. It differs per machine, so the provenance column
    would say something different on every deployment; and it would never equal
    `StandardDocument.source_file`, which is the *join a citation uses* to find its public
    address (`public_codes_by_source`). The field's own help text has always promised
    `pgs_docs/<file>.pdf`, and that is what this returns — `ingest._relative_source` does the
    same thing for the corpus side, because the two must agree for a citation to be clickable.
    """
    try:
        return source.resolve().relative_to(Path(settings.BASE_DIR).resolve()).as_posix()
    except ValueError:  # a `--source-dir` outside the tree; keep the trace we can
        return source.resolve().as_posix()


def _destination(source: Path, destination: Path) -> bool:
    """Copy `source` to `destination` if the bytes differ. Returns True if copied.

    Written via a temporary file in the same directory and an atomic replace: a deploy
    interrupted mid-copy must not leave a truncated PDF that `publish_documents` then
    considers up to date because a path exists at all.
    """
    if destination.is_file() and sha256_of(destination) == sha256_of(source):
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f".{destination.name}.part")
    shutil.copyfile(source, staging)
    staging.replace(destination)
    return True


@transaction.atomic
def publish_documents(source_dir: Path | None = None) -> PublishResult:
    """Copy the shipped documents into the public media root and upsert the rows.

    In:      an optional directory to read from (defaults to `pgs_docs/`).
    Out:     `PublishResult(created, updated, copied, unchanged)`.
    Side effects: writes under `MEDIA_ROOT/public/documents/` and to `PublicDocument`.
    Fails:   `DocumentSourceMissing` if a spec names a file that is not shipped —
             loudly, because the alternative is a page linking to a 503.
    Idempotency: yes, on content. A second run copies nothing, creates nothing and
             updates nothing unless a spec actually changed.

    The rows are written in one transaction (§VI). The *files* cannot be — a
    filesystem has no rollback — so a crash between a copy and its row leaves an
    unreferenced file, never a row without a file. The sha256 comparison makes the
    next run's copy a no-op either way, which is why the atomicity here is about the
    rows and the idempotency is about both.
    """
    origin = Path(source_dir) if source_dir is not None else DOCS_SOURCE_DIR
    created = updated = copied = unchanged = 0

    for spec in DOCUMENTS:
        source = origin / spec.source
        if not source.is_file():
            raise DocumentSourceMissing(
                f"{spec.code}: {source.resolve()} is not in the tree. The published copy "
                f"would have nothing to serve, and /documents/{spec.code}/ would 503."
            )

        relative = (PUBLIC_SUBDIR / f"{spec.code}{source.suffix}").as_posix()
        destination = Path(settings.MEDIA_ROOT) / relative
        if _destination(source, destination):
            copied += 1
        else:
            unchanged += 1

        defaults = {
            "title": spec.title,
            "note": spec.note,
            "file_path": relative,
            "content_type": "application/pdf",
            "source_path": _recorded_source(source),
            "download_name": spec.download_name,
            "display_order": spec.display_order,
        }
        # D22 is group data: a *newly* seeded document is published as the spec says,
        # but a group that unpublishes one keeps it unpublished. `is_published` is
        # therefore applied on create only, exactly as `Seal.is_active` is — a release
        # must never silently republish a document the group took down.
        document, was_created = PublicDocument.objects.get_or_create(
            code=spec.code,
            defaults={**defaults, "is_published": spec.is_published},
        )
        if was_created:
            created += 1
            continue

        changed = [field for field, value in defaults.items() if getattr(document, field) != value]
        if changed:
            for field in changed:
                setattr(document, field, defaults[field])
            document.save(update_fields=changed)
            updated += 1

    # The keys are prefixed because `extra` may not shadow a LogRecord attribute:
    # `created` is the record's own timestamp, and passing it raises KeyError at log
    # time rather than at import — the seed is otherwise fine and the failure looks
    # like a test problem. Same family as `name`, `args`, `levelname`.
    logger.info(
        "public documents published",
        extra={
            "documents_created": created,
            "documents_updated": updated,
            "documents_copied": copied,
            "documents_unchanged": unchanged,
        },
    )
    return PublishResult(created, updated, copied, unchanged)
