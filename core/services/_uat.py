"""Preflight for a UAT session: is this instance the one the reviewer is about to sign?

A reviewer who cannot tell `366 chunks` from `0 chunks` will sign a chatbot that answers
nothing, and the signature will look like evidence. This service answers the six
questions that decide whether the instance is ready, with the **expected** value printed
beside the observed one — a number with no expectation beside it is not a check.

Two design points:

* **`blocking` is per row, and it is honest.** The corpus, the embeddings, the published
  documents and the settings are blocking: without them the scenarios cannot be run. The
  health probe is advisory, because `celery_worker` is legitimately absent on a dev box —
  it must be `ok` on the environment being signed, and the row says so rather than
  failing a reviewer for the machine they happen to be sitting at.
* **Read-only.** Nothing here writes, seeds or repairs. The seeding half of `uat_seed`
  lands with MVP 1a's scenarios, which are the first that need rows (MPV 0's data is the
  seeded corpus and the published documents).

The `pdftotext` row exists because Scenario 9 asks a reviewer to put their finger on a
quoted word **on the printed page**: if the server extracts with poppler and this box with
Xpdf, every quote was produced by a tool the reviewer is not holding.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from core.models import PublicDocument
from core.services._health import check_health
from django.core.checks import run_checks
from knowledge.models import DocumentChunk

#: The shipped corpus: SAOSO 319 + OPP 30 + BPP 9 + landscape 8, after D52's reflow and
#: D53's BPP artefact (HANDOVER §17). Deliberately a constant rather than a query: the
#: point of the row is to compare against a number somebody decided, and a test pins it
#: so a corpus change shows up as a failing expectation rather than a silent pass.
EXPECTED_CHUNKS = 385

#: The eight documents C2 publishes (D22). "SOP's" is assumed to be the OPP (C1 §6 #6);
#: if it turns out to be a ninth document, this number moves with the tuple.
EXPECTED_DOCUMENTS = 8


@dataclass(frozen=True)
class PreflightRow:
    """One check: what a human would run, what to expect, and what is actually true."""

    name: str
    command: str
    expected: str
    observed: str
    ok: bool
    blocking: bool
    note: str = ""


@dataclass(frozen=True)
class PreflightReport:
    """The whole preflight. Frozen: a report is a fact, not a draft."""

    rows: tuple[PreflightRow, ...]

    @property
    def failures(self) -> tuple[PreflightRow, ...]:
        return tuple(row for row in self.rows if not row.ok)

    @property
    def blocking_failures(self) -> tuple[PreflightRow, ...]:
        return tuple(row for row in self.rows if not row.ok and row.blocking)

    @property
    def is_ready(self) -> bool:
        return not self.blocking_failures


def _settings_row() -> PreflightRow:
    messages = run_checks()
    observed = "no issues" if not messages else f"{len(messages)} issue(s): " + "; ".join(
        message.msg for message in messages[:3]
    )
    return PreflightRow(
        name="settings and app",
        command="python manage.py check",
        expected="no issues",
        observed=observed,
        ok=not messages,
        blocking=True,
    )


def _health_row() -> PreflightRow:
    report = check_health()
    observed = " ".join(f"{key}={value}" for key, value in report.checks.items())
    return PreflightRow(
        name="dependencies",
        command="curl -s localhost:8000/health/",
        expected="db, redis, celery_broker, celery_worker all ok",
        observed=observed,
        ok=report.is_ok,
        blocking=False,
        note="a dev box often has no Celery worker; it must be ok on the instance being signed",
    )


def _corpus_row(expected_chunks: int) -> PreflightRow:
    count = DocumentChunk.objects.count()
    return PreflightRow(
        name="corpus present",
        command="python manage.py shell -c \"from knowledge.models import DocumentChunk; "
        'print(DocumentChunk.objects.count())"',
        expected=f"{expected_chunks} chunks",
        observed=f"{count} chunks",
        ok=count == expected_chunks,
        blocking=True,
    )


def _embedded_row() -> PreflightRow:
    missing = DocumentChunk.objects.filter(embedding__isnull=True).count()
    return PreflightRow(
        name="corpus embedded",
        command='python manage.py shell -c "from knowledge.models import DocumentChunk; print(DocumentChunk.objects.filter(embedding__isnull=True).count())"',
        expected="0 chunks without a vector",
        observed=f"{missing} chunk(s) without a vector",
        ok=missing == 0,
        blocking=True,
        note="a corpus ingested with --no-embed answers from the lexical arm only (D48)",
    )


def _documents_row() -> PreflightRow:
    published = PublicDocument.objects.filter(is_published=True).count()
    return PreflightRow(
        name="documents published",
        command="python manage.py publish_documents",
        expected=f"{EXPECTED_DOCUMENTS} published",
        observed=f"{published} published",
        ok=published == EXPECTED_DOCUMENTS,
        blocking=True,
    )


def _extraction_row() -> PreflightRow:
    # The binary the *app* will use, not whatever `pdftotext` resolves to first: a
    # deployment can pin one with `PDFTOTEXT_BIN` (poppler and Xpdf wrap differently, and
    # `-table` is Xpdf-only — `testing_hazards.md` §2.9).
    from knowledge.extraction import pdftotext_bin

    binary = pdftotext_bin()
    try:
        result = subprocess.run(
            (binary, "-v"),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return PreflightRow(
            name="extraction tool",
            command=f"{binary} -v",
            expected="installed; the same implementation the fixtures pin",
            observed=f"{binary}: not found",
            ok=False,
            blocking=False,
            note="needed to re-extract a document, not to judge a scenario",
        )
    banner = (result.stderr or result.stdout or "").strip().splitlines()
    observed = banner[0] if banner else "no version banner"
    # `ok` is "a version was printed", not "the exit code was 0": Xpdf's `-v` exits 1
    # while printing its banner (measured: `pdftotext version 4.00`, exit 1). Failing the
    # row for that would make a correct installation read as a broken one, and a warning
    # that is always on is a warning nobody reads.
    # Attribution reads the WHOLE banner, not just the version line. Poppler's first line
    # is `pdftotext version 24.02.0`; the word "poppler" appears only on its copyright
    # line, so the version-line-only check printed `(unknown)` for a perfectly good poppler
    # install on the VPS (2026-10-22) — and this row exists to tell a reviewer which
    # extractor built the corpus, so "unknown" defeats it. Check poppler first: both
    # banners carry a Glyph & Cog copyright line.
    lowered = observed.lower()
    banner_text = "\n".join(banner).lower()
    if "poppler" in banner_text:
        kind = "poppler"
    elif "glyph & cog" in banner_text or lowered.startswith("pdftotext version 4."):
        kind = "Xpdf"
    else:
        kind = "unknown"
    return PreflightRow(
        name="extraction tool",
        command=f"{binary} -v",
        expected="installed; the same implementation the fixtures pin",
        observed=f"{observed} ({kind})",
        ok=bool(banner),
        blocking=False,
        note=(
            "poppler and Xpdf 4.00 wrap lines differently: the live corpus holds 316 "
            "SAOSO chunks where Xpdf builds 319 (measured 2026-10-22). Scenario 9 compares "
            "against paper, so the reader must be the one the corpus was built with."
        ),
    )


def preflight(expected_chunks: int = EXPECTED_CHUNKS) -> PreflightReport:
    """Run every preflight check and report. Never raises: a check is a fact, not a failure.

    In: `expected_chunks` — the corpus size this instance should hold.
    Out: `PreflightReport`, every row present, `blocking` marked per row.
    Side Effects: reads the database, opens a Redis/Celery probe, runs `pdftotext -v`.
    Fails: never — an exception here would deny the reviewer the other five answers.
    """
    return PreflightReport(
        rows=(
            _settings_row(),
            _health_row(),
            _corpus_row(expected_chunks),
            _embedded_row(),
            _documents_row(),
            _extraction_row(),
        )
    )
