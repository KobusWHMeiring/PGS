"""`scripts/eval_extractors.py` — an instrument the gate must never need (requirement 10).

Three things are worth a test here, and only three:

* **It imports without the extractor.** `docling` is not a dependency of this project and never will
  be; if a top-level import crept in, the suite would fail on every machine that does not have a 1.5 GB
  venv, which is every machine including the deploy target.
* **It refuses an unknown shape** instead of silently scoring fewer than eight.
* **It refuses to run at all when the extractor is absent**, and says why — rather than reporting an
  empty document as a score, which is the failure mode this whole PRD exists to remove.

The rest of the instrument is measured by running it, and its output is committed:
`product/docs/evidence/2026-11-03_s2_docling_scores.json`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import scripts.eval_extractors as evaluator

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_it_imports_without_the_extractor():
    """A fresh interpreter, so a module already cached by another test cannot hide the import."""
    code = (
        "import sys, scripts.eval_extractors; "
        "assert 'docling' not in sys.modules, sorted(sys.modules); "
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout


def test_an_unknown_shape_is_refused_with_the_known_ones(capsys):
    assert evaluator.main(["--shape", "numeric_row,nonsense"]) == 2
    err = capsys.readouterr().err
    assert "nonsense" in err
    assert "numeric_row" in err, "the refusal names what does exist"


def test_without_the_extractor_it_stops_rather_than_scoring_nothing(monkeypatch):
    """`convert` must fail loudly: a missing extractor is not an empty document."""
    import builtins

    real_import = builtins.__import__

    def no_docling(name, *args, **kwargs):
        if name.startswith("docling"):
            raise ImportError("No module named 'docling'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_docling)
    with pytest.raises(SystemExit) as raised:
        evaluator.convert("pgs_docs/does-not-matter.pdf", (1,))
    assert "docling is not installed" in str(raised.value)
