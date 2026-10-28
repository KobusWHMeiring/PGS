"""Is this box serving the corpus its reviewed artefacts describe? (D56, P2)

Two commands read this module and nothing else, so they cannot disagree about what
"current" means:

- `manage.py corpus_check` — read-only, prints one row per governed document, exits
  non-zero on drift. A deploy runs it and **warns**; it never refreshes (P2.4).
- `manage.py corpus_refresh [--apply]` — prints what it would re-ingest and how many chat
  citations that drops, and does nothing without `--apply` (P2.3).

**Drift is three different things and the operator needs to tell them apart.** A document
whose chunks were built from the PDF, a document whose artefact has changed since, and a
document nobody ingested are all "not current", but the fixes differ: the first and second
are `corpus_refresh --apply`, the third is an `ingest_standard` that has never run. The
report says which.

**A document with no reviewed artefact is not drift** (P4/P5 have not converted `opp` and
`landscape` yet). It is a recorded gap: the corpus is parsed from the PDF, the ingest says
so in its report, and no exit status should nag about work that has not been done.

`knowledge` must not import `core` (`build_principles.md` §I), so the citation-link count
below walks Django's relation metadata rather than naming `ChatMessage`: the corpus is
extractable to a project whose citation table is called something else.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from knowledge.corpus import CorpusFormatError, load_document
from knowledge.ingest import (
    CORPUS_DOCUMENTS,
    chunks_for_sections,
    corpus_artifact,
    resolve_standard_set,
)
from knowledge.models import DocumentChunk, StandardDocument, StandardSet

#: One state per document, and each has exactly one fix. Strings, not an enum: the value
#: is printed in a table an operator reads, and "CURRENT" is not a better word than
#: "current".
CURRENT = "current"
DRIFT = "drift"
NOT_INGESTED = "not ingested"
NO_ARTEFACT = "no artefact"
MISSING = "artefact missing"
MALFORMED = "artefact malformed"

#: The states that mean the box is not serving what the review says it should.
BROKEN = frozenset({DRIFT, NOT_INGESTED, MISSING, MALFORMED})


@dataclass(frozen=True)
class CorpusState:
    """One governed document, as this box has it and as its artefact describes it."""

    doc_key: str
    state: str
    #: `None` when the document declares no reviewed artefact (P4/P5 have not converted it).
    artefact: Path | None = None
    #: The stored document, when one holds the artefact's bytes.
    document: StandardDocument | None = None
    stored_chunks: int = 0
    expected_chunks: int | None = None
    detail: str = ""

    @property
    def is_broken(self) -> bool:
        return self.state in BROKEN

    @property
    def needs_refresh(self) -> bool:
        """True when `corpus_refresh --apply` is the fix. Not the same as `is_broken`:
        a document nobody has ingested has nothing to refresh."""
        return self.state in {DRIFT, NOT_INGESTED} and self.document is not None


def corpus_states(standard_set: StandardSet | None = None) -> list[CorpusState]:
    """One `CorpusState` per governed document (P2.2), in doc-key order.

    In: `standard_set` — the corpus to check; defaults to the single `is_default` set.
    Out: the states, whether or not the box is current.
    Side Effects: none. Read-only, by construction — every write in this feature is behind
        `corpus_refresh --apply`.
    Fails: `IngestError` from `resolve_standard_set` when no default set exists.
    """
    standard_set = standard_set or resolve_standard_set()
    states = []
    for doc_key in sorted(CORPUS_DOCUMENTS):
        artefact = corpus_artifact(doc_key)
        if artefact is None:
            states.append(
                CorpusState(
                    doc_key=doc_key,
                    state=NO_ARTEFACT,
                    detail="no reviewed artefact yet, so the corpus is parsed from the PDF",
                )
            )
            continue
        try:
            reviewed = load_document(artefact)
        except FileNotFoundError:
            states.append(
                CorpusState(
                    doc_key=doc_key,
                    state=MISSING,
                    artefact=artefact,
                    detail=(
                        f"{artefact.name} is declared but not on disk; the ingest will "
                        "refuse until it is generated"
                    ),
                )
            )
            continue
        except CorpusFormatError as error:
            states.append(
                CorpusState(
                    doc_key=doc_key,
                    state=MALFORMED,
                    artefact=artefact,
                    detail=f"{artefact.name} does not parse: {error}",
                )
            )
            continue

        document = StandardDocument.objects.filter(
            standard_set=standard_set, sha256=reviewed.sha256
        ).first()
        expected = len(chunks_for_sections(reviewed.sections))
        if document is None:
            states.append(
                CorpusState(
                    doc_key=doc_key,
                    state=NOT_INGESTED,
                    artefact=artefact,
                    expected_chunks=expected,
                    detail="these bytes are not ingested in this corpus",
                )
            )
            continue
        if document.corpus_digest != reviewed.digest:
            states.append(
                CorpusState(
                    doc_key=doc_key,
                    state=DRIFT,
                    artefact=artefact,
                    document=document,
                    stored_chunks=document.chunk_count,
                    expected_chunks=expected,
                    detail=(
                        "these chunks were built from the PDF"
                        if not document.corpus_digest
                        else "the reviewed artefact has changed since this corpus was built"
                    ),
                )
            )
            continue
        if document.chunk_count != expected:
            states.append(
                CorpusState(
                    doc_key=doc_key,
                    state=DRIFT,
                    artefact=artefact,
                    document=document,
                    stored_chunks=document.chunk_count,
                    expected_chunks=expected,
                    detail="the same artefact now produces a different number of chunks",
                )
            )
            continue
        states.append(
            CorpusState(
                doc_key=doc_key,
                state=CURRENT,
                artefact=artefact,
                document=document,
                stored_chunks=document.chunk_count,
                expected_chunks=expected,
            )
        )
    return states


def citation_links(document: StandardDocument) -> int:
    """How many many-to-many rows point at this document's chunks.

    In: `document` — an ingested `StandardDocument`.
    Out: the number of rows `--force` will drop when it deletes those chunks. A chat turn's
        stored grounding snapshot survives (P2.5a), but the join rows do not, so the
        operator is told how many before it happens.

    Structural, not nominal: `knowledge` may not import `core`, and a hardcoded
    `ChatMessage` would make this library only work in this project.
    """
    total = 0
    for relation in DocumentChunk._meta.related_objects:
        through = getattr(relation, "through", None)
        if through is None:  # a reverse FK is not a citation link
            continue
        for field in through._meta.fields:
            if field.is_relation and field.related_model is DocumentChunk:
                total += through._default_manager.filter(
                    **{f"{field.name}__document": document}
                ).count()
                break
    return total


def pdf_path_for(document: StandardDocument) -> Path:
    """The PDF this document was ingested from, resolved against the repo root.

    In: `document`.
    Out: a `Path`, which may not exist on this machine.
    """
    stored = Path(document.source_file)
    return stored if stored.is_absolute() else Path(settings.BASE_DIR) / stored


__all__ = [
    "BROKEN",
    "CURRENT",
    "DRIFT",
    "MALFORMED",
    "MISSING",
    "NO_ARTEFACT",
    "NOT_INGESTED",
    "CorpusState",
    "citation_links",
    "corpus_states",
    "pdf_path_for",
]
