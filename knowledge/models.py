"""The standards corpus: a **library over documents** (spec §4.5).

`knowledge` has no users, no sessions and no views, and it must never import
`core` (A7, CI-enforced). That is what makes it independently testable and
extractable: a chatbot over the SAOSO standard is useful to any PGS group with
zero farm data.

Three models, and each exists to keep the pipeline **standard-agnostic**:

- `StandardSet` groups a corpus, and retrieval is always scoped to a set. Outeniqua's
  set is SAOSO v2.1 + the OPP + the BPP + the certification landscape. Two sets may
  coexist, which is how a version transition (2.1 → 2.2) happens without deleting
  history.
- `StandardDocument.kind` says *what a citation came from*, and `section_scheme`
  selects the parser from **data**, not code. Adding a standard therefore means
  adding a parser module (B2) and a `StandardDocument` row — never a migration.
- `DocumentChunk` is the unit of retrieval and citation.

Field widths and nullability carry two decisions worth stating, because both were
argued over in the spec rather than chosen by default:

**`section_ref` is mandatory — but `NULL`, not `""`, is how a heading-only document
says so.** SPEC §4.5: "a chunk the user cannot locate in the standard is not a
citation." SAOSO and the OPP always print a reference (`S20.1.1`, `§4.2(5)`), and a
chunk from either with an empty reference is a parser bug. The LANDSCAPE and BPP
documents print **no clause numbers at all** (SPEC §4.5, reality table), so their
locator is `page` + `heading_path`; B2's `heading.py` emits no `section_ref` for
them. The database therefore forbids the empty string and permits NULL, which
separates "the parser found nothing" (a bug, refused) from "this document has no
such thing" (a fact, stored). `blank=False` alone would enforce neither — Postgres
stores `""` happily (testing_hazards.md §1.7) — so this is a `CheckConstraint`.

    Open for B2: the parser for heading-only documents may emit an anchor-shaped
    reference (`certification-landscape#the-sa-context`) instead of NULL. Both are
    accepted here; the constraint only rules out the silent empty string.

**`sub_refs` holds character offsets, not separate chunks** (D15). Splitting at every
enumerated item would fragment the OPP into several hundred context-poor chunks and
degrade retrieval, so a chunk stays section-level and a citation slices the text it
needs. `sub_refs` is therefore `[{"ref", "start", "end"}]` with
`0 <= start < end <= len(text)`, validated in `clean()` because it is a property of
the payload rather than of a column.

**`search_vector` is a real `GeneratedField`, not a `pre_save` signal.** HANDOVER §6
warns that `GeneratedField(SearchVector(...))` may not cooperate with the Postgres in
Compose; measured on this stack (Postgres 16.15, server extension pgvector 0.8.7 from
`pgvector/pgvector:pg16`, Python client `pgvector==0.5.1`), it works — the expression
is `to_tsvector(regconfig, …)`, which is immutable and therefore legal in a generated
column. A signal was rejected because it is invisible to `QuerySet.update()`, and a
bulk re-ingest that updates text in place would leave every chunk searchable by its
*previous* text with nothing failing. `knowledge/tests/test_models.py` asserts both
the insert and the update path.

Note for whoever changes `search_vector`: Django refuses `AlterField` on a
`GeneratedField` ("must be removed and re-added"). A changed expression is a
`RemoveField` + `AddField` migration, not an `AlterField`.

**No HNSW index on `embedding` yet.** At the shipped corpus size (four documents,
~101 pages) a sequential cosine scan is measured in milliseconds, and an HNSW index
on the `vector` type caps at 2000 dimensions and costs build time on every ingest.
Add it when B7's retrieval is measured against a corpus large enough to need it — not
before, because an unused index is a maintenance obligation with no evidence behind
it. The GIN index on `search_vector` *is* created now: it is free to maintain and
B7's lexical arm uses it from its first query.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.core.exceptions import ValidationError
from django.db import models
from pgvector.django import VectorField

# The only keys a `sub_refs` entry may carry. A typo'd key (`stop` for `end`) would
# otherwise be stored happily and the citation would silently lose its offset.
SUB_REF_KEYS = frozenset({"ref", "start", "end"})


def validate_sub_refs(sub_refs: list[dict], text: str) -> None:
    """Check that every `sub_ref` names a slice that actually exists inside `text`.

    In:  `sub_refs` — `[{"ref", "start", "end"}]`; `text` — the chunk body.
    Out: None.
    Fails: `ValidationError` on a malformed entry, an empty `ref`, a non-integer or
        negative offset, `start >= end`, or `end` beyond the end of `text`.

    This is the single place the offset rule lives, so B2's parsers can be written
    against it and B6 can validate a whole page before writing any chunk.
    """
    for entry in sub_refs:
        if not isinstance(entry, dict) or set(entry) != SUB_REF_KEYS:
            raise ValidationError(
                f"sub_refs entries must be exactly {sorted(SUB_REF_KEYS)}, got {entry!r}."
            )
        if not isinstance(entry["ref"], str) or not entry["ref"].strip():
            raise ValidationError(f"sub_ref {entry!r} has no usable 'ref'.")
        start, end = entry["start"], entry["end"]
        # `bool` is an `int` in Python; `True` is not a character offset.
        if not isinstance(start, int) or not isinstance(end, int) or isinstance(start, bool):
            raise ValidationError(f"sub_ref {entry!r} offsets must be integers.")
        if start < 0 or start >= end:
            raise ValidationError(
                f"sub_ref {entry!r} has an empty or reversed span (need 0 <= start < end)."
            )
        if end > len(text):
            raise ValidationError(
                f"sub_ref {entry['ref']!r} ends at {end}, past the end of the chunk "
                f"({len(text)} characters)."
            )


class StandardSet(models.Model):
    """A corpus that retrieval is scoped to (D16, §4.5).

    `code` has **no `choices=`** — a choice list would make adding a corpus a code
    change plus a migration, which is the thing `build_principles.md` §I forbids.
    """

    code = models.SlugField(
        max_length=64,
        unique=True,
        help_text="Stable identifier, e.g. 'outeniqua'. Not a choice field.",
    )
    label = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(
        default=False,
        help_text=(
            "The set a session or an ingest gets when none is named. At most one — "
            "enforced by a partial unique constraint, because two defaults would make "
            "the default ambiguous."
        ),
    )

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"],
                condition=models.Q(is_default=True),
                name="unique_default_standard_set",
            ),
        ]
        verbose_name = "standard set"
        verbose_name_plural = "standard sets"

    def __str__(self) -> str:
        return self.label


class StandardDocument(models.Model):
    """One ingested document, versioned and content-addressed (§4.5, D12).

    `sha256` is the idempotency key for re-ingestion (B6): the same bytes in the same
    set must add nothing. It is scoped to the set rather than global so one PDF may
    belong to two coexisting corpora without duplicating its chunks — retrieval is
    scoped through `standard_set`, so a shared document would be invisible to the
    second set's FK.

    `superseded_by` points *forward*: v2.1 names v2.2. `PROTECT` is deliberate —
    deleting a document that a successor names would leave an assessment's citation
    pointing at nothing, and assessments cite the version in force at the time.
    """

    class Kind(models.TextChoices):
        """What the document *is*, because a citation must say what it came from."""

        STANDARD = "STANDARD", "Standard"
        SOP = "SOP", "Procedure"
        PRINCIPLES = "PRINCIPLES", "Principles"
        GUIDANCE = "GUIDANCE", "Guidance"
        LANDSCAPE = "LANDSCAPE", "Certification landscape"

    standard_set = models.ForeignKey(
        StandardSet,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    issuing_body = models.CharField(max_length=128)
    title = models.CharField(max_length=255)
    version = models.CharField(
        max_length=32,
        help_text="As the document prints it, e.g. '2.1'. Cited in verdicts.",
    )
    effective_from = models.DateField(
        null=True,
        blank=True,
        help_text="When this version took force, if the document states it.",
    )
    superseded_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="supersedes",
        help_text="The version that replaced this one. Set forward: v2.1 → v2.2.",
    )
    source_file = models.CharField(
        max_length=255,
        help_text="Path of the ingested file relative to the repository root.",
    )
    sha256 = models.CharField(
        max_length=64,
        help_text="sha256 of the ingested bytes — the re-ingestion idempotency key.",
    )
    chunk_count = models.PositiveIntegerField(
        default=0,
        help_text="Denormalised count maintained by ingest; never a source of truth.",
    )
    section_scheme = models.CharField(
        max_length=32,
        help_text=(
            "Selects the section-reference parser, e.g. 'saoso', 'opp', 'heading'. "
            "Data, not code: adding a standard means adding a parser, not a migration."
        ),
    )

    class Meta:
        ordering = ["standard_set__code", "kind", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["standard_set", "sha256"],
                name="unique_document_sha256_per_set",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.version})"

    @property
    def is_current(self) -> bool:
        """True when nothing newer has replaced this version.

        Retrieval should prefer current documents, but must still be able to cite a
        superseded one that an assessment was decided against.
        """
        return self.superseded_by_id is None


class DocumentChunk(models.Model):
    """The unit of retrieval and citation (§4.5).

    See the module docstring for why `section_ref` is nullable-but-never-empty, why
    `sub_refs` carries offsets, and why `search_vector` is generated.
    """

    document = models.ForeignKey(
        StandardDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    section_ref = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text=(
            "Human-meaningful citation, exactly as printed: 'S20.1.1', '§4.2(5)'. "
            "NULL only for documents that print no numbering (LANDSCAPE, BPP); "
            "the empty string is refused by a database constraint."
        ),
    )
    sub_refs = models.JSONField(
        default=list,
        blank=True,
        help_text="[{'ref', 'start', 'end'}] character offsets into `text` (D15).",
    )
    anchor = models.CharField(
        max_length=128,
        blank=True,
        help_text="Content-derived locator for a block the source never numbered.",
    )
    heading_path = models.CharField(
        max_length=512,
        blank=True,
        help_text="Heading trail as printed, ' > '-joined; also indexed for FTS.",
    )
    page = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="PDF page the chunk starts on. One-based, as a reader would count.",
    )
    text = models.TextField()
    token_count = models.PositiveIntegerField(
        default=0,
        help_text="Rough token count, used to hold the ~800-token chunk target (B4).",
    )
    embedding = VectorField(
        dimensions=settings.EMBEDDING_DIM,
        null=True,
        blank=True,
        help_text=(
            f"Gemini embedding, {settings.EMBEDDING_DIM} dimensions — frozen by D3/D20. "
            "Changing the model or width means re-embedding the whole corpus."
        ),
    )
    search_vector = models.GeneratedField(
        expression=SearchVector("text", "heading_path", config="english"),
        output_field=SearchVectorField(),
        db_persist=True,
        editable=False,
    )

    class Meta:
        ordering = []  # deliberately none: B7 fuses ranked queries, it does not page.
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(section_ref=""),
                name="chunk_section_ref_is_never_blank",
            ),
        ]
        indexes = [
            # B7's lexical arm. GIN, not GiST: the queries are `@@` containment.
            GinIndex(
                fields=["search_vector"],
                name="chunk_search_vector_gin",
            ),
            # B6's duplicate-reference ratchet groups by document and ref.
            models.Index(
                fields=["document", "section_ref"],
                name="chunk_document_section_idx",
            ),
        ]

    def __str__(self) -> str:
        locator = self.section_ref or self.anchor or f"p{self.page}"
        return f"{locator} — {self.text[:48]}"

    def clean(self) -> None:
        super().clean()
        validate_sub_refs(self.sub_refs or [], self.text)
