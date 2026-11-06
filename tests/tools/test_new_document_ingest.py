"""The DoD's first criterion, at the seam it can be proved at: a document the registry does not know.

`INGESTION_ENGINE_PRD.md` §6 asks for *"a document not in `CORPUS_DOCUMENTS` ingested and its tables
chunked with column meaning, with no hand-authored table block."*

**What this proves.** The block is emitted by the generator from committed structure data, found by
the PDF's sha256 rather than by a registry key; the artefact is assembled with a `doc_key` the registry
has never heard of; `ingest_standard` takes it through the explicit-metadata path
(`kind`/`title`/`scheme`), which is the retarget seam `build_principles.md` §I requires; and the row
that comes out is a chunk whose `embedding_text` names the printed columns — the property a numeric
row needs to be retrievable at all (`CHAT_ANSWER_COVERAGE_PRD` G10).

**What it does not prove, said plainly.** The bytes are the OPP's. No arm response exists for any
document outside the eight shape pages, and S3 may not re-run the arms — so the *structure* of a
genuinely new standard's paper is not measured here. What is measured is that nothing in the path
needs a registry entry, a migration or a human's block: a new PDF is `scripts/propose_tables.py` once,
then the generator and the ingest as usual.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from knowledge.extraction import PDFTOTEXT, PDFTOTEXT_ENV, sha256_of
from knowledge.ingest import CORPUS_DOCUMENTS, ingest_standard
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.table_proposals import proposals_for
from scripts.table_blocks import emit
from tests.tools.draft_fixtures import fixture_body

REPO_ROOT = Path(__file__).resolve().parents[2]
OPP_PDF = REPO_ROOT / "pgs_docs" / "Outeniqua pgs principles, policies and procedures 2026.pdf"


@pytest.fixture(autouse=True)
def a_real_reader(monkeypatch):
    """Point the ingest at an extractor that exists, or skip - and never inherit the poison.

    `ingest_standard` reads the PDF's printed table of contents even when a reviewed artefact
    supplies the text (D68 §7.5: the TOC is a property of the *printed* document, and it is the
    only source of a branch's name), so these two tests need a reader. `scripts/verify.sh`
    poisons `PDFTOTEXT_BIN` on purpose and `tests/tools/test_verify_gate.py` asserts the poison
    stays - which is how this file sat red in the gate, unseen, from the commit that added it
    (`testing_hazards.md` §3.48).

    Naming the reader here rather than inheriting one keeps both properties: the gate stays
    green on a box with no poppler, and the tests still run wherever a reader exists. Skip,
    never silently narrow: the reason is printed in the gate's output.
    """
    binary = shutil.which(PDFTOTEXT)
    if binary is None:
        pytest.skip(
            f"no `{PDFTOTEXT}` on PATH: the ingest reads the printed TOC (D68 §7.5), and "
            f"{PDFTOTEXT_ENV} is deliberately poisoned by scripts/verify.sh"
        )
    monkeypatch.setenv(PDFTOTEXT_ENV, binary)


HEADER = """<!-- corpus
doc_key: {doc_key}
source: {source}
sha256: {sha256}
generator: knowledge corpusgen v2
-->
"""


def emitted_section(doc_key: str, digest: str, heading: str) -> str:
    """One section: a page marker, a heading, the emitted block, and the prose around it."""
    body = fixture_body("opp")
    lines, emitted, refused = emit(proposals_for(digest), body)
    assert refused == (), [str(refusal) for refusal in refused]
    assert len(emitted) == 1
    start = lines.index("<!-- table")
    end = lines.index("<!-- /table -->")
    # The page in force where the table starts — not the document's first marker, which is page 1.
    page_marker = next(
        line for line in reversed(lines[:start]) if line.startswith("<!-- page:")
    )
    return "\n".join([page_marker, f"## {heading}"] + lines[start : end + 1]) + "\n"


@pytest.mark.django_db
def test_a_document_the_registry_does_not_know_is_chunked_with_column_meaning(tmp_path):
    digest = sha256_of(OPP_PDF)
    doc_key = "opp-newstandard"
    assert doc_key not in CORPUS_DOCUMENTS, "pick a key the registry does not have"

    artefact = tmp_path / f"{doc_key}.md"
    artefact.write_text(
        HEADER.format(
            doc_key=doc_key,
            source=OPP_PDF.relative_to(REPO_ROOT).as_posix(),
            sha256=digest,
        )
        + emitted_section(doc_key, digest, "2.3 A fee structure the registry does not know"),
        encoding="utf-8",
        newline="\n",
    )

    standard_set = StandardSet.objects.create(code="pgs", label="PGS")
    report = ingest_standard(
        pdf_path=OPP_PDF,
        standard_set=standard_set,
        doc_key=doc_key,
        kind=StandardDocument.Kind.STANDARD,
        title="A standard the registry has never heard of",
        section_scheme="heading",
        corpus_path=artefact,
        embed=False,
    )

    chunks = DocumentChunk.objects.filter(document_id=report.document_id)
    rows = chunks.filter(heading_path__contains="Above R 5,000,000")
    assert rows.count() == 1, list(chunks.values_list("heading_path", flat=True))
    chunk = rows.get()
    assert "Initial certification fee (R): 8,000" in chunk.embedding_text
    assert "Renewal fee (R): 8,000" in chunk.embedding_text
    assert "Annual farm turnover (gross sales): Above R 5,000,000" in chunk.embedding_text
    assert chunk.text.strip() == "Above R 5,000,000\n8,000\n8,000"
    assert "<!-- table" not in chunk.text, "an annotation reached the corpus text"
    assert chunk.page == 2


@pytest.mark.django_db
def test_the_same_document_may_be_ingested_twice_under_two_keys(tmp_path):
    """The retarget rule in one assertion: the corpus is per `StandardSet`, and nothing about the
    document's identity is baked into a registry entry."""
    digest = sha256_of(OPP_PDF)
    first = StandardSet.objects.create(code="pgs-one", label="PGS One")
    second = StandardSet.objects.create(code="pgs-two", label="PGS Two")
    for name, standard_set in (("opp-newstandard", first), ("opp-othergroup", second)):
        artefact = tmp_path / f"{name}.md"
        artefact.write_text(
            HEADER.format(
                doc_key=name,
                source=OPP_PDF.relative_to(REPO_ROOT).as_posix(),
                sha256=digest,
            )
            + emitted_section(name, digest, f"2.3 Fee structure for {name}"),
            encoding="utf-8",
            newline="\n",
        )
        report = ingest_standard(
            pdf_path=OPP_PDF,
            standard_set=standard_set,
            doc_key=name,
            kind=StandardDocument.Kind.SOP,
            title=f"A procedure for {name}",
            section_scheme="heading",
            corpus_path=artefact,
            embed=False,
        )
        assert report.created and report.chunk_count >= 1
