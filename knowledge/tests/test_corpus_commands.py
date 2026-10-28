"""P2.2 and P2.3 — can this box tell whether its corpus is current, and refresh it?

D56 splits the two: a **report** that anyone can run and a **refresh** that a person has to
ask for. That split is only worth anything if the report can actually go red, so every test
below builds a corpus that is wrong on purpose — from the PDF, from an older review, with a
lost artefact, or with a chunk count that no longer matches. A `corpus_check` that passes
against a fixture nobody ingested would be the decoration `testing_hazards.md` §0 warns
about.

The count of chat citations a refresh destroys needs a real citation table, so that test
lives in `core/tests/test_corpus_refresh_links.py` (core may import knowledge; the reverse
is forbidden).
"""

from __future__ import annotations

import hashlib
import shutil
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from knowledge.drift import (
    CURRENT,
    DRIFT,
    MISSING,
    NO_ARTEFACT,
    NOT_INGESTED,
    corpus_states,
)
from knowledge.ingest import CORPUS_DIR, ingest_standard
from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.tests.page_fixtures import stub_ingest_extraction

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
PDFS = {
    "saoso": REPO_ROOT / "pgs_docs" / "saoso-version-2.1-2026.pdf",
    "opp": REPO_ROOT / "pgs_docs" / "Outeniqua pgs principles, policies and procedures 2026.pdf",
    "bpp": REPO_ROOT / "pgs_docs" / "Basic Production Principles_ENG_PRINT.pdf",
    "landscape": REPO_ROOT / "pgs_docs" / "PGS Certification landscape_Final.pdf",
}
ARTEFACTS = {"saoso": CORPUS_DIR / "saoso.md", "bpp": CORPUS_DIR / "bpp.md"}


@pytest.fixture(autouse=True)
def committed_extraction(monkeypatch):
    """The gate must run where no PDF reader exists (D57) — see `test_ingest.py`."""
    stub_ingest_extraction(monkeypatch)


@pytest.fixture(autouse=True)
def no_live_embeddings(monkeypatch):
    def bomb(*args, **kwargs):  # pragma: no cover - only runs when the guard fires
        raise AssertionError("a live embedding provider was built in a test; pass embed=False")

    monkeypatch.setattr("knowledge.embedding.GeminiEmbeddingProvider", bomb, raising=False)


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(
        code="outeniqua", label="Outeniqua PGS corpus", is_default=True
    )


def states_by_key(standard_set):
    return {state.doc_key: state for state in corpus_states(standard_set)}


def check(*args):
    """Run `corpus_check` and return (stdout, the exception it raised or None)."""
    out = StringIO()
    try:
        call_command("corpus_check", *args, stdout=out)
    except CommandError as error:
        return out.getvalue(), error
    return out.getvalue(), None


def drift_bpp(standard_set):
    """A corpus that is wrong in the way the plan says is worst: parsed from the PDF."""
    return ingest_standard(
        pdf_path=PDFS["bpp"],
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        from_pdf=True,
    )


# --- P2.2: the report --------------------------------------------------------


def test_an_empty_box_reports_every_governed_document_and_fails(standard_set):
    """A first install has an empty corpus. It must *say so*, in a way a deploy logs and a
    person can read — not pass quietly because there is nothing to compare."""
    output, error = check()

    assert error is not None, "an empty corpus must not be reported as current"
    for doc_key in PDFS:
        assert doc_key in output
    states = states_by_key(standard_set)
    assert states["saoso"].state == NOT_INGESTED
    assert states["bpp"].state == NOT_INGESTED
    # Not converted yet (P4, P5): a recorded gap, never drift.
    assert states["opp"].state == NO_ARTEFACT
    assert states["landscape"].state == NO_ARTEFACT
    assert not states["opp"].is_broken


def test_a_corpus_built_from_the_pdf_is_drift_and_says_so(standard_set):
    """The state P7.1 makes impossible going forward, and the one a box deployed before it
    is in today. The message must name the cause, because the fix differs from "changed"."""
    drift_bpp(standard_set)

    output, error = check()

    assert error is not None
    state = states_by_key(standard_set)["bpp"]
    assert state.state == DRIFT
    assert "built from the PDF" in state.detail
    assert "bpp" in output and "corpus is NOT current" in output
    assert "corpus_refresh --apply" in output, "the report must name the fix"


def test_a_corpus_built_from_its_artefact_is_current(standard_set):
    ingest_standard(
        pdf_path=PDFS["bpp"],
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        corpus_path=ARTEFACTS["bpp"],
    )

    state = states_by_key(standard_set)["bpp"]

    assert state.state == CURRENT
    assert state.stored_chunks == state.expected_chunks
    document = StandardDocument.objects.get(pk=state.document.pk)
    assert document.corpus_digest == hashlib.sha256(state.artefact.read_bytes()).hexdigest()


def test_the_check_writes_nothing(standard_set):
    """Read-only is the whole contract with a deploy (P2.4). Asserted on the ids, not the
    counts: a `--force` refresh that rebuilt identical chunks would pass a count check."""
    drift_bpp(standard_set)
    before = list(DocumentChunk.objects.order_by("pk").values_list("pk", "text"))
    documents_before = list(
        StandardDocument.objects.order_by("pk").values_list("pk", "corpus_digest", "toc")
    )

    check()

    assert list(DocumentChunk.objects.order_by("pk").values_list("pk", "text")) == before
    assert (
        list(
            StandardDocument.objects.order_by("pk").values_list("pk", "corpus_digest", "toc")
        )
        == documents_before
    )


def test_a_changed_artefact_is_drift_even_though_the_pdf_is_the_same(
    standard_set, tmp_path, monkeypatch
):
    """The review changed its mind; the PDF did not. That is exactly what `corpus_digest`
    exists to see, and a chunk-count check alone would miss it."""
    copy = tmp_path / "bpp.md"
    shutil.copyfile(ARTEFACTS["bpp"], copy)
    ingest_standard(
        pdf_path=PDFS["bpp"],
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        corpus_path=copy,
    )
    # The module resolves the declaration against `CORPUS_DIR` on every call, so pointing
    # the directory at the copy is enough — the code path is the shipped one.
    monkeypatch.setattr("knowledge.ingest.CORPUS_DIR", tmp_path)
    assert states_by_key(standard_set)["bpp"].state == CURRENT

    copy.write_text(copy.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    state = states_by_key(standard_set)["bpp"]
    assert state.state == DRIFT
    assert "has changed since" in state.detail


def test_a_chunk_count_that_no_longer_matches_is_drift(standard_set):
    """`chunk_count` is denormalised (the model says so). A stale one must be caught here
    rather than trusted, because every reader of that column is a reader of this check."""
    ingest_standard(
        pdf_path=PDFS["bpp"],
        standard_set=standard_set,
        doc_key="bpp",
        embed=False,
        corpus_path=ARTEFACTS["bpp"],
    )
    assert states_by_key(standard_set)["bpp"].state == CURRENT
    StandardDocument.objects.update(chunk_count=1)

    state = states_by_key(standard_set)["bpp"]

    assert state.state == DRIFT
    assert "different number of chunks" in state.detail


def test_a_declared_artefact_that_is_gone_is_drift(standard_set, monkeypatch, tmp_path):
    """The machine that lost `knowledge/corpus/`. The ingest refuses (D55); the report has
    to say why, or the operator sees a failing deploy with no cause."""
    monkeypatch.setattr("knowledge.ingest.CORPUS_DIR", tmp_path)

    output, error = check()

    assert error is not None
    states = states_by_key(standard_set)
    assert states["bpp"].state == MISSING
    assert states["bpp"].artefact.name == "bpp.md"
    assert "bpp" in output


# --- P2.3: the refresh -------------------------------------------------------


def test_the_refresh_is_a_dry_run_until_it_is_told_otherwise(standard_set):
    """`--apply` is the only way anything is written, and `--force` destroys citation
    links — so the default must be a report."""
    drift_bpp(standard_set)
    before = list(DocumentChunk.objects.order_by("pk").values_list("pk", "text"))

    out = StringIO()
    call_command("corpus_refresh", "--no-embed", stdout=out)

    assert "Dry run. Nothing was written." in out.getvalue()
    assert "would re-ingest" in out.getvalue()
    assert "bpp" in out.getvalue()
    assert "chat citation link(s) will be dropped" in out.getvalue()
    assert list(DocumentChunk.objects.order_by("pk").values_list("pk", "text")) == before


def test_the_refresh_rebuilds_the_drifted_document_from_its_artefact(standard_set):
    """End to end: drift, `--apply`, current. Both halves through the real commands.

    The command still exits non-zero afterwards — `saoso` has never been ingested on this
    box, and a fixer that cannot make the corpus current must not report success. That is
    asserted here too, on purpose: the exit status is about the box, not about the work
    this run happened to do.
    """
    drift_bpp(standard_set)
    assert states_by_key(standard_set)["bpp"].state == DRIFT

    out = StringIO()
    with pytest.raises(CommandError, match="saoso"):
        call_command("corpus_refresh", "--apply", "--no-embed", stdout=out)

    state = states_by_key(standard_set)["bpp"]
    assert state.state == CURRENT, out.getvalue()
    document = StandardDocument.objects.get(pk=state.document.pk)
    assert document.corpus_digest == hashlib.sha256(state.artefact.read_bytes()).hexdigest()
    assert document.chunk_count == state.expected_chunks
    assert "re-ingested" in out.getvalue()


def test_the_refresh_does_not_invent_a_pdf_for_a_document_nobody_ingested(standard_set):
    """A document with no row has no PDF path, and guessing one would be the command
    pretending to know something it does not. It names the command instead."""
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("corpus_refresh", "--apply", "--no-embed", stdout=out)

    assert "cannot refresh saoso" in out.getvalue()
    assert "ingest_standard --doc saoso" in out.getvalue()
    assert DocumentChunk.objects.count() == 0
