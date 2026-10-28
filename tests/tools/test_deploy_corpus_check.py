"""The deploy reports a stale corpus and never repairs it (D56, plan P2.4).

Two halves, and each fails in the opposite direction:

* remove the `corpus_check` call, and a deploy lands code that expects a corpus the box
  does not have — green gate, wrong answers, and nothing in the log to explain either;
* run it unguarded, and `set -euo pipefail` turns "this box is behind on a review" into a
  failed deploy — which is worse than the state it reports, because the *previous* code is
  still serving and nobody can ship a fix.

The refresh must never appear here at all. It re-embeds four documents and drops every
chat turn's citation links; `core/services/_evidence.py` and `HANDOVER.md` §17 both record
that `--force` stays out of a deploy, so this asserts the *command* is not run, not that
the words are absent (the warning tells the operator what to type).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY = REPO_ROOT / "deploy" / "deploy.sh"


def read() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def test_the_deploy_reports_the_corpus():
    assert "run_manage corpus_check" in read()


def test_the_report_cannot_abort_the_deploy():
    """Guarded with `if !`, which is the only reason `set -e` does not act on it."""
    assert "if ! run_manage corpus_check; then" in read()


def test_the_report_runs_after_the_documents_are_published():
    """`corpus_check` compares a corpus with files `publish_documents` does not touch, but
    the order still matters to a reader: documents first, then what was built from them."""
    text = read()
    assert text.index("run_manage publish_documents") < text.index(
        "run_manage corpus_check"
    )


def test_the_deploy_never_refreshes_the_corpus():
    assert "run_manage corpus_refresh" not in read()
    assert "run_manage ingest_standard" not in read()
