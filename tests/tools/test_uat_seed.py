"""The preflight: observed vs expected, and a blocking failure that actually blocks.

The row that matters is the corpus count. A reviewer who cannot tell `366 chunks` from
`0 chunks` signs a chatbot that answers nothing, and the signature looks like evidence —
so the count is compared against a pinned expectation rather than reported on its own.

The advisory rows matter for a different reason: a row that is always red is a row nobody
reads. `celery_worker` is legitimately absent on a dev box, so it informs and does not
block; the corpus does block.
"""

from __future__ import annotations

import subprocess

import pytest
from django.core.management import call_command

from core.services import _uat
from core.services._uat import EXPECTED_CHUNKS, EXPECTED_DOCUMENTS, preflight

pytestmark = pytest.mark.django_db


def test_the_expected_counts_are_pinned():
    """If the corpus changes, this test should be the thing that says so.

    385 = SAOSO 338 + OPP 30 + BPP 9 + landscape 8, after D52's reflow, D53's BPP
    artefact (HANDOVER §17). Eight published documents is C2's list (D22).
    """
    assert EXPECTED_CHUNKS == 385
    assert EXPECTED_DOCUMENTS == 8


def test_preflight_reports_every_row_and_marks_which_block(monkeypatch):
    monkeypatch.setattr(_uat, "check_health", lambda: _ok_health())

    report = preflight()

    assert [row.name for row in report.rows] == [
        "settings and app",
        "dependencies",
        "corpus present",
        "corpus embedded",
        "documents published",
        "extraction tool",
    ]
    blocking = {row.name for row in report.rows if row.blocking}
    assert blocking == {
        "settings and app",
        "corpus present",
        "corpus embedded",
        "documents published",
    }


def test_an_empty_corpus_is_a_blocking_failure(monkeypatch):
    """The test database has no corpus, which is exactly the state this row exists for."""
    monkeypatch.setattr(_uat, "check_health", lambda: _ok_health())

    report = preflight()

    corpus = next(row for row in report.rows if row.name == "corpus present")
    assert corpus.observed == "0 chunks"
    assert corpus.expected == "385 chunks"
    assert corpus.ok is False
    assert corpus.blocking is True
    assert report.is_ready is False
    assert "corpus present" in {row.name for row in report.blocking_failures}


def test_the_expectation_can_be_stated_so_the_row_can_pass(monkeypatch):
    monkeypatch.setattr(_uat, "check_health", lambda: _ok_health())

    report = preflight(expected_chunks=0)

    corpus = next(row for row in report.rows if row.name == "corpus present")
    assert corpus.ok is True


def test_an_unhealthy_dependency_warns_without_blocking(monkeypatch):
    monkeypatch.setattr(_uat, "check_health", lambda: _bad_health())

    report = preflight(expected_chunks=0)

    health = next(row for row in report.rows if row.name == "dependencies")
    assert health.ok is False
    assert health.blocking is False
    assert "must be ok on the instance being signed" in health.note
    # Unpublished documents still block, so readiness is False for a different reason.
    assert "dependencies" not in {row.name for row in report.blocking_failures}


def test_a_missing_pdftotext_is_advisory(monkeypatch):
    # The gate exports a deliberately dead `PDFTOTEXT_BIN` (D57); this test is about the
    # default binary's absence, so it must not inherit that.
    monkeypatch.delenv("PDFTOTEXT_BIN", raising=False)
    monkeypatch.setattr(_uat, "check_health", lambda: _ok_health())

    def _no_binary(*args, **kwargs):
        raise OSError("pdftotext not found")

    monkeypatch.setattr(subprocess, "run", _no_binary)

    row = next(row for row in preflight(expected_chunks=0).rows if row.name == "extraction tool")

    assert row.ok is False
    assert row.blocking is False
    # The binary the app would actually run — pinned or resolved from PATH — so the row
    # cannot report `pdftotext` when the deployment set `PDFTOTEXT_BIN`.
    assert row.observed == "pdftotext: not found"
    assert row.command == "pdftotext -v"


def test_the_extraction_row_names_the_implementation(monkeypatch):
    """Poppler and Xpdf word-wrap differently, and Scenario 9 compares against paper."""
    monkeypatch.setattr(_uat, "check_health", lambda: _ok_health())
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "pdftotext version 4.00"),
    )

    row = next(row for row in preflight(expected_chunks=0).rows if row.name == "extraction tool")

    assert row.ok is True
    assert row.observed == "pdftotext version 4.00 (Xpdf)"


def test_the_extraction_row_names_poppler_from_its_copyright_line(monkeypatch):
    """The real poppler banner, verbatim from the VPS (`pdftotext -v`, exit 1).

    Mutation: reading only the version line prints `(unknown)` — which is what the live
    box reported for a correct install, because poppler's first line never says "poppler".
    """
    banner = (
        "pdftotext version 24.02.0\n"
        "Copyright 2005-2024 The Poppler Developers - http://poppler.freedesktop.org\n"
        "Copyright 1996-2011, 2022 Glyph & Cog, LLC"
    )
    monkeypatch.setattr(_uat, "check_health", lambda: _ok_health())
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 99, "", banner),
    )

    row = next(row for row in preflight(expected_chunks=0).rows if row.name == "extraction tool")

    assert row.ok is True
    assert row.observed == "pdftotext version 24.02.0 (poppler)"


def test_the_command_exits_non_zero_on_a_blocking_failure(monkeypatch, capsys):
    monkeypatch.setattr(_uat, "check_health", lambda: _ok_health())

    with pytest.raises(SystemExit) as raised:
        call_command("uat_seed", "--check", "--expect-chunks", "12345")

    assert raised.value.code == 1
    printed = capsys.readouterr().out
    assert "preflight: NOT ready" in printed
    assert "corpus present" in printed


def test_the_command_exits_zero_when_nothing_blocking_fails(monkeypatch, capsys):
    monkeypatch.setattr(_uat, "check_health", lambda: _ok_health())

    # The test database has no chunks and no published documents, so both are wrong; this
    # asserts the *mechanism*, with the two expectations lowered to what is actually here.
    monkeypatch.setattr(_uat, "EXPECTED_DOCUMENTS", 0)
    call_command("uat_seed", "--check", "--expect-chunks", "0")

    assert "preflight: ready" in capsys.readouterr().out


def test_the_command_refuses_to_pretend_without_check(capsys):
    with pytest.raises(SystemExit) as raised:
        call_command("uat_seed")

    assert raised.value.code == 2
    assert "nothing to do" in capsys.readouterr().err


def _ok_health():
    from core.services._health import HealthReport

    return HealthReport(
        status="ok",
        checks={
            "db": "ok",
            "redis": "ok",
            "celery_broker": "ok",
            "celery_worker": "ok",
        },
    )


def _bad_health():
    from core.services._health import HealthReport

    return HealthReport(
        status="error",
        checks={
            "db": "ok",
            "redis": "ok",
            "celery_broker": "ok",
            "celery_worker": "error",
        },
    )
