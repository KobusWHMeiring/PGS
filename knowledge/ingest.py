"""Standard-document ingestion — B6.

`python manage.py ingest_standard --doc saoso --version 2.1 --file <pdf>` →
page-aware extraction, section parsing by scheme, chunking, `tsvector` population and
(optionally) embeddings, then one `StandardDocument` row and its `DocumentChunk`s.

Four rules shape this module.

**Idempotent on `sha256`.** Re-ingesting the same bytes into the same `StandardSet`
writes nothing and returns `created=False`. That is the property B6 tests, and it is
what makes the command safe to re-run — a corpus that grows duplicate chunks degrades
retrieval silently, because near-identical hits crowd out the real ones.

**Embedding is optional; failure to embed is not failure.** With no `GEMINI_API_KEY`
the chunks are still written and the report warns, because FTS-only retrieval works and
a corpus with no vectors is far more useful than no corpus. But an embedding *error*
raises: half-embedded corpora are the thing B5 refused to produce, and a document whose
vectors are missing for some chunks looks entirely normal.

**The report is data, not logging.** Duplicate `section_ref`s, the embedded flag and
the warnings come back as a frozen dataclass so the command can print them and the
tests can assert them. A duplicate reference is reported, never repaired: a parser that
silently renamed one of two colliding refs would be inventing citations.

**`--doc` names a built-in corpus document (D16), and every field is overridable.**
The descriptor supplies `kind`/`issuing_body`/`title`/`section_scheme` for the four
governed documents so the common case is one command; `--title`, `--kind`, `--scheme`
and friends let a new standard be ingested with no code change, which is what
`build_principles.md` §I requires.

Corpus scope is D41: the SAOSO parser is given the whole PDF and emits Section B and
its appendices only, because Section A's numbering collides within itself.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Count

from knowledge.chunking import chunk_sections
from knowledge.columns import apply_layout
from knowledge.corpus import load_document
from knowledge.reflow import reflow_pages
from knowledge.embedding import embed_texts
from knowledge.extraction import extract_pages, sha256_of
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.sections import registry
from knowledge.sections.toc import toc_from_pages
from knowledge.tables import chunks_for_rows, rows_for

logger = logging.getLogger(__name__)


class IngestError(RuntimeError):
    """Ingestion cannot proceed. Never swallowed: an empty corpus looks like success."""


#: The four governed corpus documents (D16). `section_scheme` is what selects the
#: parser, so adding a standard is a data change plus a parser module — not a migration.
CORPUS_DOCUMENTS: dict[str, dict[str, str]] = {
    "saoso": {
        "kind": StandardDocument.Kind.STANDARD,
        "issuing_body": "SAOSO",
        "title": "SAOSO Standard for Organic Production and Processing",
        "version": "2.1",
        "section_scheme": "saoso",
    },
    "opp": {
        "kind": StandardDocument.Kind.SOP,
        "issuing_body": "Outeniqua PGS",
        "title": "Outeniqua PGS Principles, Policies and Procedures",
        "version": "2026",
        "section_scheme": "opp",
    },
    "bpp": {
        "kind": StandardDocument.Kind.PRINCIPLES,
        "issuing_body": "SAOSO",
        "title": "Basic Production Principles",
        # The document prints no version; an empty string is the honest value.
        "version": "",
        "section_scheme": "heading",
    },
    "landscape": {
        "kind": StandardDocument.Kind.LANDSCAPE,
        "issuing_body": "SAOSO",
        "title": "The South African Organic Certification Landscape",
        "version": "",
        "section_scheme": "heading",
    },
}


@dataclass(frozen=True)
class IngestReport:
    """What an ingest did. Assertable, not just printable."""

    document_id: int
    created: bool
    chunk_count: int
    embedded: bool
    duplicate_refs: dict[str, int] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    layout_pages: tuple[int, ...] = ()
    reflow_pages: tuple[int, ...] = ()
    #: sha256 of the reviewed corpus artefact this corpus was built from (D53), or "" when
    #: the PDF was parsed at ingest. It is the only record of *which* review produced the
    #: chunks, because the artefact is not a database row.
    corpus_digest: str = ""

    @property
    def has_duplicates(self) -> bool:
        return bool(self.duplicate_refs)

    @property
    def duplicate_ref_count(self) -> int:
        """Extra occurrences beyond the first, which is what a ratchet counts."""
        return sum(count - 1 for count in self.duplicate_refs.values())


def resolve_standard_set(code: str | None = None) -> StandardSet:
    """In:  `code` or None.
    Out: the named set, or the single `is_default=True` set.
    Fails: `IngestError` when no code is given and the default is missing or ambiguous —
        retrieval is always scoped to a set (§4.5), so guessing one would put another
        standard's text behind the chatbot's answers.
    """
    if code:
        try:
            return StandardSet.objects.get(code=code)
        except StandardSet.DoesNotExist as error:
            raise IngestError(
                f"No StandardSet with code {code!r}. Known: "
                f"{', '.join(StandardSet.objects.values_list('code', flat=True)) or '(none)'}."
            ) from error

    defaults = StandardSet.objects.filter(is_default=True)
    if defaults.count() != 1:
        raise IngestError(
            f"Expected exactly one default StandardSet, found {defaults.count()}. "
            "Run `manage.py seed_deployment`, or pass --set <code>."
        )
    return defaults.get()


def duplicate_section_refs(sections: list) -> dict[str, int]:
    """`section_ref` -> occurrences, only where more than one **section** shares it.

    The ratchet's measurement, and the distinction matters: `S1` is the glossary and
    spans eight *chunks*, all legitimately cited `S1`. Counting chunks instead of
    sections reported those eight as duplicates and made the ratchet meaningless. What
    must never happen is two different sections — two paragraphs a reader would look up
    in different places — claiming one citation.

    In:  `sections` — from a `knowledge.sections` parser, before chunking.
    Out: `{ref: count}` for refs used by more than one section.
    """
    counts: dict[str, int] = {}
    for section in sections:
        if section.section_ref:
            counts[section.section_ref] = counts.get(section.section_ref, 0) + 1
    return {ref: count for ref, count in counts.items() if count > 1}


def chunks_per_section_ref(document: StandardDocument) -> dict[str, int]:
    """How many chunks carry each citation. A size diagnostic, not the ratchet.

    A value above one is expected and healthy: a long clause is split by B4 and every
    piece keeps the clause's citation, which is the point of section-level chunking.
    """
    rows = (
        DocumentChunk.objects.filter(document=document, section_ref__isnull=False)
        .values("section_ref")
        .annotate(occurrences=Count("id"))
        .filter(occurrences__gt=1)
    )
    return {row["section_ref"]: row["occurrences"] for row in rows}


def ingest_standard(
    *,
    pdf_path: str | Path,
    standard_set: StandardSet,
    doc_key: str | None = None,
    kind: str | None = None,
    issuing_body: str | None = None,
    title: str | None = None,
    version: str | None = None,
    section_scheme: str | None = None,
    embed: bool = True,
    provider=None,
    force: bool = False,
    corpus_path: str | Path | None = None,
) -> IngestReport:
    """Ingest one PDF into one `StandardSet`.

    In:  `pdf_path` — the document; `standard_set` — the corpus it belongs to (§4.5);
         `doc_key` — a `CORPUS_DOCUMENTS` name, or explicit metadata fields instead;
         `embed` — request embeddings (skipped with a warning when no key is present);
         `provider` — an `EmbeddingProvider`, for tests; `force` — replace an already
         ingested document (same sha256) instead of returning the no-op report;
         `corpus_path` — a reviewed artefact (`knowledge/corpus/<doc>.md`) whose text is
         used instead of parsing the PDF (D53). The PDF is still hashed, still the source
         of truth, and must match the artefact's recorded sha256.
    Out: an `IngestReport`. `created=False` means the bytes were already ingested.
         `layout_pages` names the PDF pages the column transform changed, so the
         operator's log and the tests can see the transform ran rather than inferring
         it from better answers.
    Side Effects: writes `StandardDocument` + `DocumentChunk` rows; embeds over the
         network unless embeddings are skipped. With `force`, the previous document
         and its chunks are deleted inside the same transaction as the new write.
    Idempotency: keyed on `(standard_set, sha256)`; `force` is the deliberate escape
         hatch for a corpus-built-here change (a curated table, a parser fix) whose
         source bytes are unchanged. It drops the old chunks' `retrieved_chunks` links,
         so run it deliberately rather than as part of a deploy.
    Fails: `IngestError` for missing metadata or an unknown scheme;
        `ExtractionError` when the PDF cannot be read;
        `EmbeddingError` when embeddings were requested and failed. Embedding happens
        **before** the transaction, so a failure writes nothing at all — including no
        deletion under `force`.
    """
    descriptor = dict(CORPUS_DOCUMENTS.get(doc_key, {})) if doc_key else {}
    if doc_key and doc_key not in CORPUS_DOCUMENTS and not any(
        (kind, title, section_scheme)
    ):
        raise IngestError(
            f"Unknown --doc {doc_key!r}. Known: {', '.join(sorted(CORPUS_DOCUMENTS))}, "
            "or pass --kind/--title/--scheme for a new standard."
        )
    for name, value in (
        ("kind", kind),
        ("issuing_body", issuing_body),
        ("title", title),
        ("version", version),
        ("section_scheme", section_scheme),
    ):
        if value is not None:
            descriptor[name] = value

    for required in ("kind", "title", "section_scheme"):
        if not descriptor.get(required):
            raise IngestError(
                f"Missing {required!r}. Pass --doc for a known corpus document, or "
                f"--{required.replace('_', '-')} explicitly."
            )

    path = Path(pdf_path)
    if not path.exists():
        raise IngestError(f"No such PDF: {path}")

    digest = sha256_of(path)
    existing = StandardDocument.objects.filter(
        standard_set=standard_set, sha256=digest
    ).first()
    if existing is not None and not force:
        return IngestReport(
            document_id=existing.pk,
            created=False,
            chunk_count=existing.chunk_count,
            embedded=existing.chunks.exclude(embedding__isnull=True).exists(),
            duplicate_refs={},   # nothing was parsed on this path
            warnings=(f"already ingested as document #{existing.pk}; nothing written",),
        )

    parser = registry.get(descriptor["section_scheme"])
    corpus_digest = ""
    corpus_sections = None
    if corpus_path is not None:
        # The reviewed artefact is the text of record (D53). Everything downstream —
        # chunking, embeddings, retrieval — is unchanged; only the source of the sections
        # moves from a heuristic to a reviewed file. The PDF is still hashed, and the
        # artefact must name these exact bytes.
        document_corpus = load_document(corpus_path)
        if document_corpus.sha256 != digest:
            raise IngestError(
                f"{Path(corpus_path).name} was built from a different PDF "
                f"(artefact {document_corpus.sha256[:12]}, file {digest[:12]}). "
                "Regenerate the artefact first: a transcription that is not traceable "
                "to these bytes is not this document."
            )
        if doc_key and document_corpus.doc_key != doc_key:
            raise IngestError(
                f"{Path(corpus_path).name} is the artefact for "
                f"{document_corpus.doc_key!r}, not {doc_key!r}."
            )
        corpus_sections = list(document_corpus.sections)
        corpus_digest = document_corpus.digest

    if corpus_sections is not None:
        sections = corpus_sections
        # Nothing is transformed here: the artefact was built (and reviewed) earlier, so
        # the report has no layout or reflow pages to name.
        layout_pages: tuple[int, ...] = ()
        rejoined_pages: tuple[int, ...] = ()
        # The artefact carries no printed TOC, and `--from-corpus` has no pages: the PDF
        # is read again for this one purpose, because the TOC is a property of the
        # *printed* document rather than of the reviewed text (D68 §7.5).
        toc_pages = extract_pages(path)
    else:
        # The TOC is read from the **raw** pages, before de-columning and reflow: it is a
        # record of what the document prints, not of how we read the body. Its own page
        # is a `PAGE_LAYOUT_EXCLUSIONS` entry for SAOSO, so this is also the rendering a
        # reader can check against the paper copy.
        raw_pages = extract_pages(path)
        toc_pages = raw_pages
        # The page is de-columned *before* the parser sees it (D46). Layout is a measured
        # property of a page, not a flag on the document: a new standard ingested with
        # explicit metadata has no exclusion table and gets generic detection (D16).
        pages, layout_pages = apply_layout(raw_pages, doc_key=doc_key)
        # Hyphenated words the PDF wrapped are rejoined *after* the columns are ordered,
        # so line adjacency is reading adjacency (D52). Before this, `non-` /
        # `P a g e | 47` / `ruminant` was one stored sentence and no quote could pass.
        pages, rejoined_pages = reflow_pages(pages)
        sections = parser.parse("\f".join(pages))
    if not sections:
        raise IngestError(
            f"{path.name} produced zero sections"
            + (
                f" from {Path(corpus_path).name}"
                if corpus_path is not None
                else f" with scheme {descriptor['section_scheme']!r}"
            )
            + ". Refusing to write an empty document — this is the failure mode that "
            "invalidated MVP 0 v1."
        )
    chunks = chunk_sections(sections)
    # `knowledge/tables.py` replaces a printed table's auto-chunks with one chunk per
    # reviewed row (Appendix 2 is the first). The rows are a reconstruction — the single
    # documented exception to "a chunk is a slice of the section" — because the `-layout`
    # text interleaves the condition column into the substance column. Data, not a
    # branch: a reviewed section is looked up in `TABLE_ROWS`.
    reviewed: set[str] = set()
    table_chunks: list = []
    for chunk in chunks:
        ref = chunk.section_ref
        if rows_for(ref):
            if ref in reviewed:
                continue  # the section's auto-chunks are replaced once, in order
            reviewed.add(ref)
            table_chunks.extend(chunks_for_rows(ref))
            continue
        table_chunks.append(chunk)
    chunks = table_chunks

    # Stored once per document (D68 §7.5). It is the only source of a branch's *name*:
    # SAOSO's `S1` opener carries no heading, and Appendix 2's first heading names its
    # first sub-table (CONCORDANCE_PRD §10.1, §10.5).
    toc = [entry.as_dict() for entry in toc_from_pages(toc_pages)]

    warnings: list[str] = []
    vectors: list[list[float]] | None = None
    if embed:
        if provider is None and not settings.GEMINI_API_KEY:
            warnings.append(
                "GEMINI_API_KEY is not set: chunks were written without embeddings. "
                "Retrieval is lexical only until the corpus is re-embedded."
            )
        else:
            vectors = embed_texts([chunk.text for chunk in chunks], provider=provider)

    source_file = _relative_source(path)

    with transaction.atomic():
        if existing is not None:
            # `force`: the bytes are unchanged but what we derive from them changed
            # (a curated table, a parser fix). Delete inside the transaction, after the
            # embedding call, so a failed embed leaves the old corpus intact.
            existing.delete()
        document = StandardDocument.objects.create(
            standard_set=standard_set,
            kind=descriptor["kind"],
            issuing_body=descriptor.get("issuing_body", ""),
            title=descriptor["title"],
            version=descriptor.get("version", ""),
            source_file=source_file,
            sha256=digest,
            section_scheme=descriptor["section_scheme"],
            chunk_count=len(chunks),
            toc=toc,
        )
        DocumentChunk.objects.bulk_create(
            [
                DocumentChunk(
                    document=document,
                    section_ref=chunk.section_ref,
                    text=chunk.text,
                    heading_path=chunk.heading_path,
                    page=chunk.page,
                    anchor=chunk.anchor,
                    sub_refs=[ref.as_dict() for ref in chunk.sub_refs],
                    token_count=chunk.token_count,
                    embedding=vectors[index] if vectors else None,
                )
                for index, chunk in enumerate(chunks)
            ]
        )
        # `chunk_count` is written here rather than left at zero: it is a denormalised
        # convenience, so it must at least be right at the moment of writing.
        document.chunk_count = len(chunks)
        document.save(update_fields=["chunk_count"])

    duplicate_refs = duplicate_section_refs(sections)
    if duplicate_refs:
        # Reported, never repaired: renaming one of two colliding refs would invent a
        # citation. The test suite holds a ratchet on this number.
        logger.warning(
            "ingest_standard: duplicate section_refs in %s: %s",
            path.name,
            duplicate_refs,
        )

    return IngestReport(
        document_id=document.pk,
        created=True,
        chunk_count=len(chunks),
        embedded=vectors is not None,
        duplicate_refs=duplicate_refs,
        warnings=tuple(warnings),
        layout_pages=layout_pages,
        reflow_pages=rejoined_pages,
        corpus_digest=corpus_digest,
    )


def _relative_source(path: Path) -> str:
    """The path as stored on `StandardDocument.source_file`, using POSIX separators.

    `as_posix()` rather than `str()`: this repo is developed on Windows and deployed on
    the VPS, and a stored `pgs_docs\\file.pdf` would not match a Linux path.
    """
    try:
        return path.resolve().relative_to(Path(settings.BASE_DIR).resolve()).as_posix()
    except ValueError:
        return path.name


__all__ = [
    "CORPUS_DOCUMENTS",
    "IngestError",
    "IngestReport",
    "chunks_per_section_ref",
    "duplicate_section_refs",
    "ingest_standard",
    "resolve_standard_set",
]
