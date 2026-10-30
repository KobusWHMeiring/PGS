"""Task A7 — `knowledge` must never import `core`.

`build_principles.md` §I: "The `knowledge` dependency is one-directional. `core` may
import `knowledge`; `knowledge` must **never** import `core`. Enforced by an
`import-linter` rule in CI, not by convention."

The rule matters for a specific reason rather than tidiness: a `knowledge` module
that reaches into `core.models` cannot be tested without a database, cannot be
reused for another PGS group, and makes the standards corpus a function of the
group's data instead of the standard. That is the separation `PGS_PLATFORM_SPEC.md`
§4.8 and §I exist to preserve.

This file runs the linter as well as CI does, because the plan is right that "one of
them will be skipped by a human". Three tests, each guarding a different way the
rule could be silently absent:

1. the config *declares* the contract — a typo or wrong file format makes
   `lint-imports` exit 0 while enforcing nothing;
2. the contract *bites* — a real violation is detected;
3. the contract is *one-directional* — `core` importing `knowledge` is still fine,
   because a blanket ban would be a different (and wrong) rule.
"""

from __future__ import annotations

import configparser
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".importlinter"

# Underscore-prefixed so pytest never collects them, and named identically so the
# cleanup below can be unconditional.
PROBE_IN_KNOWLEDGE = REPO_ROOT / "knowledge" / "_arch_probe.py"
PROBE_IN_CORE = REPO_ROOT / "core" / "_arch_probe.py"


def _remove_probes() -> None:
    for probe in (PROBE_IN_KNOWLEDGE, PROBE_IN_CORE):
        probe.unlink(missing_ok=True)


# Self-healing: a probe left behind by an interrupted run would break every later
# suite run with a confusing "BROKEN" nobody can explain. Clean at import time.
_remove_probes()


def _linter_argv() -> list[str]:
    """Locate the `lint-imports` entry point.

    Not left to `PATH`: the venv's Scripts directory is not on `PATH` when pytest is
    invoked as `python -m pytest`, so `shutil.which` alone would fail in exactly the
    environment A8's CI uses.
    """
    scripts_dir = Path(sys.executable).parent
    for name in ("lint-imports.exe", "lint-imports"):
        candidate = scripts_dir / name
        if candidate.exists():
            return [str(candidate)]
    found = shutil.which("lint-imports")
    if found:
        return [found]
    pytest.fail(
        "lint-imports not found next to the interpreter or on PATH. It is in the A1 "
        "dependency list; a missing linter must not read as a passing architecture test."
    )


def _run_linter() -> subprocess.CompletedProcess:
    """Run Import Linter over the repository.

    `--no-cache` because Grimp caches a per-root-package module list, and a cached
    module list survived a deleted file during A7's manual verification, briefly
    reporting BROKEN for a violation that no longer existed. A flaky architecture
    test gets disabled, so the cache is not worth its speed here.
    """
    return subprocess.run(
        [*_linter_argv(), "--no-cache", "--no-logo"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )


class _Probe:
    """Write a throwaway module, then remove it — even if the assertion fails."""

    def __init__(self, path: Path, source: str) -> None:
        self.path = path
        self.source = source

    def __enter__(self) -> Path:
        self.path.write_text(self.source, encoding="utf-8")
        # Assert the file is really there: on Windows a batched write+lint excited a
        # stale filesystem view during A7, which produced four bogus results before
        # the cause was found. Never infer the write happened.
        assert self.path.exists(), f"probe was not written: {self.path}"
        return self.path

    def __exit__(self, *exc_info) -> None:
        self.path.unlink(missing_ok=True)
        assert not self.path.exists(), f"probe was not removed: {self.path}"


def test_the_linter_is_installed():
    """Fail here, clearly, rather than erroring obscurely in the tests below."""
    assert _linter_argv()


def test_the_config_declares_the_contract_exactly():
    """Parse `.importlinter` and assert the rule is actually declared.

    This is the guard against the config being *inert*. Import Linter reads
    `.importlinter` and `setup.cfg` as **INI**, and `pyproject.toml` as TOML. A
    TOML-shaped snippet in `.importlinter` — which is what MVP0_PLAN_V2.md A7 shows —
    is parsed as INI, finds no `[importlinter]` section, and enforces nothing while
    exiting 0. Asserting the parsed contents catches that; asserting only the exit
    code cannot.
    """
    config = configparser.ConfigParser()
    config.read_string(CONFIG_PATH.read_text(encoding="utf-8"))

    assert "importlinter" in config.sections(), (
        ".importlinter has no [importlinter] section, so Import Linter reads nothing "
        "from it and the contract is inert."
    )

    contract_sections = [s for s in config.sections() if s.startswith("importlinter:")]
    assert len(contract_sections) == 1, f"expected exactly one contract, got {contract_sections}"

    contract = config[contract_sections[0]]
    assert contract["type"] == "forbidden"
    assert contract["source_modules"].strip() == "knowledge"
    assert contract["forbidden_modules"].strip() == "core"

    # One-directional: `core` must not appear as a source, or the contract would
    # forbid the dependency in both directions and break `core`'s legitimate use.
    assert "core" not in contract["source_modules"]


@pytest.mark.slow  # measured >=0.6s warm: spawns a process (see pytest.ini `slow`)
def test_knowledge_does_not_import_core():
    """The rule itself, run exactly as CI runs it (A8)."""
    result = _run_linter()
    assert result.returncode == 0, (
        "knowledge is importing core. The dependency is one-directional — core may "
        f"import knowledge, never the reverse.\n\n{result.stdout}\n{result.stderr}"
    )


@pytest.mark.slow  # measured >=0.6s warm: spawns a process (see pytest.ini `slow`)
def test_the_contract_actually_detects_a_violation():
    """The contract must be able to fail, or the green above means nothing.

    A config that is inert, or whose `source_modules` names a package with no
    imports in it, exits 0 forever. This proves the analysed graph contains
    `knowledge` and that a real import in it is caught.
    """
    with _Probe(PROBE_IN_KNOWLEDGE, "from core.models import Farm\n\nvalue = Farm\n"):
        result = _run_linter()

    assert result.returncode != 0, (
        "a deliberate `from core.models import Farm` in knowledge was NOT detected, so "
        f"the architecture test is vacuous.\n\n{result.stdout}"
    )
    assert "BROKEN" in result.stdout

    # And the tree is clean again, so the next run is honest.
    assert _run_linter().returncode == 0


@pytest.mark.slow  # measured >=0.6s warm: spawns a process (see pytest.ini `slow`)
def test_core_may_import_knowledge():
    """Directionality, asserted rather than assumed.

    `core` importing `knowledge` is the *intended* design: the corpus is a library
    the application uses. If the contract ever became a blanket ban between the two
    packages, the tests above would still pass while the architecture broke.
    """
    with _Probe(PROBE_IN_CORE, "import knowledge.models  # noqa: F401\n"):
        result = _run_linter()

    assert result.returncode == 0, (
        "core importing knowledge must be allowed — the dependency is one-directional, "
        f"not absent.\n\n{result.stdout}\n{result.stderr}"
    )
