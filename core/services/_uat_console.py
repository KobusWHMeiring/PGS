"""The UAT console: the setup commands as buttons, on the instance being signed.

**Why this exists at all.** The judgement surface (`product/design/uat/<slug>.html`) is a
`file://` document and stays one: it makes **no network request**, so a reviewer's notes
never leave their machine, and it works in a room with no wifi. A browser cannot run
`manage.py` from a `file://` page, so "the setup commands as buttons" has to mean a
second, *served* page — this one. The split is deliberate:

| | runs commands | makes requests | who uses it |
|---|---|---|---|
| `/uat/` (this module) | yes | same origin only | whoever prepares the instance |
| the artefact | no | none | the reviewer |

**The whitelist is the security boundary.** A button posts an action *key*; `ACTIONS` maps
keys to commands, and a key that is not in it is refused. Nothing in a request is ever
executed. Every action is idempotent or read-only, and none deletes anything — the corpus
re-ingest lives in `MANUAL_ONLY`, shown with the reason it is not clickable, because
`--force` deletes and re-embeds the corpus, costs money, and detaches every historical
`ChatMessage` from its evidence.

Owner: `core/views/_uat.py` renders these; `core/templates/uat/console.html` shows them.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from core.services._uat import PreflightReport, preflight
from django.core.management import call_command
from django.db import connection

REPO_ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class UatFileRef:
    """One UAT this console can prepare.

    A **registry, not a path from the request.** The page offers these; a slug outside it is a
    400 before anything runs, which is the same rule the action keys follow and for the same
    reason: a request must never be able to name a file for a rebuild.
    """

    slug: str
    path: str
    label: str
    prepares: str


#: Every UAT the console knows. Adding a `tests/uat/<slug>.md` is this one entry — the buttons
#: themselves are generic (check, seed, publish, rebuild), because every reviewer's setup is the
#: same four questions about the same instance.
UATS: tuple[UatFileRef, ...] = (
    UatFileRef(
        slug="mvp0_standards_and_public_site",
        path="tests/uat/mvp0_standards_and_public_site_uat.md",
        label="MVP 0 — the standards reader and the public site",
        prepares="the reader, the site's pages and the grounded answers those pages cite",
    ),
    UatFileRef(
        slug="landscape_tables",
        path="tests/uat/landscape_tables_uat.md",
        label="The certification landscape's tables — cards, a fork, a spreadsheet",
        prepares="the landscape reader's three branches; no re-ingest is needed for it",
    ),
)


def uat_files() -> tuple[UatFileRef, ...]:
    """Every UAT in the registry, whether or not its file exists on this checkout."""
    return UATS


def uat_for(slug: str | None) -> UatFileRef:
    """The UAT a request names, or the first one when it names none.

    Fails: `KeyError` for a slug outside the registry — the view turns that into a 400, so a
        stale page or a hand-made request cannot name an arbitrary file to rebuild.
    """
    if not slug:
        return UATS[0]
    for candidate in UATS:
        if candidate.slug == slug:
            return candidate
    raise KeyError(slug)


def links_in(uat: UatFileRef) -> tuple[str, ...]:
    """The same-instance addresses a UAT's setup tells the reviewer to open.

    Read from the file, not restated here: the reviewer's "open these three branches" list is
    the UAT author's, and a second copy would drift. Only absolute in-site paths are returned —
    a `#fragment`, a relative path or an `http(s)://` URL is not a link this console offers.
    """
    path = REPO_ROOT / uat.path
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ()
    found: list[str] = []
    for token in text.replace("`", " ").split():
        address = token.strip("()[]<>,.")
        if not address.startswith("/") or address.startswith("//"):
            continue
        if "://" in address or not address[1:2].isalpha():
            continue
        if address not in found:
            found.append(address)
    return tuple(found)


@dataclass(frozen=True)
class UatAction:
    """One button: what it runs, whether it writes, and why it is safe to click."""

    key: str
    label: str
    command: str
    description: str
    writes: bool


@dataclass(frozen=True)
class ManualCommand:
    """A command the console shows but will not run, and why it will not."""

    label: str
    command: str
    reason: str


@dataclass(frozen=True)
class ActionOutcome:
    """What one button did: the command's own output, and whether it succeeded."""

    key: str
    label: str
    ok: bool
    output: str
    duration_ms: int
    #: The UAT the action ran for — the page keeps showing that one afterwards.
    uat: str = ""


#: Buttons. Each runs a command that is idempotent or read-only.
ACTIONS: tuple[UatAction, ...] = (
    UatAction(
        key="check",
        label="Re-check the instance",
        command="python manage.py uat_seed --check",
        description="Runs the six preflight checks again and shows what changed.",
        writes=False,
    ),
    UatAction(
        key="publish_documents",
        label="Publish the documents",
        command="python manage.py publish_documents",
        description=(
            "Copies the eight PDFs into media and upserts the rows. Idempotent on sha256, "
            "so it is safe to press twice."
        ),
        writes=True,
    ),
    UatAction(
        key="seed_deployment",
        label="Seed the deployment",
        command="python manage.py seed_deployment",
        description="Creates the StandardSet and the seals if they are missing. Idempotent.",
        writes=True,
    ),
    UatAction(
        key="regenerate",
        label="Rebuild the UAT page",
        command="python scripts/uat_runner.py --file {uat}",
        description=(
            "Regenerates the artefact for the UAT selected above, with this instance's commit, "
            "database name and preflight — so the page a reviewer judges is the page this "
            "instance produced."
        ),
        writes=True,
    ),
)

#: Shown, never clicked: destructive, expensive, or needs a file only the reviewer has.
MANUAL_ONLY: tuple[ManualCommand, ...] = (
    ManualCommand(
        label="Re-ingest a document",
        command=(
            "python manage.py ingest_standard --doc saoso "
            "--file pgs_docs/saoso-version-2.1-2026.pdf --force"
        ),
        reason=(
            "--force deletes the document and re-embeds every chunk: API cost, minutes of "
            "work, and every historical ChatMessage detaches from its evidence. An operator "
            "decision, not a click."
        ),
    ),
    ManualCommand(
        label="Apply a sign-off export",
        command=(
            "python scripts/uat_signoff.py "
            "--file {uat} --from <the export>.json --dry-run"
        ),
        reason="It needs the JSON the reviewer downloaded, which lives on their machine.",
    ),
)


def database_name() -> str:
    """The database this process is writing to, named for the artefact's header.

    Read from the connection rather than the env var: the env var is what was asked for,
    the connection is what actually answered. A reviewer signs a build *and* a database
    (PRD §7), so "signed something" must not be possible.
    """
    try:
        return str(connection.settings_dict.get("NAME") or "not stated")
    except Exception:  # noqa: BLE001 - a missing name must not break the console
        return "not stated"


def render_preflight(report: PreflightReport) -> str:
    """The preflight as the text a human reads: observed beside expected, one block.

    Shared by `manage.py uat_seed --check`, the console and the artefact, so the three
    cannot show different numbers for the same instance.
    """
    lines: list[str] = []
    width = max(len(row.name) for row in report.rows)
    for row in report.rows:
        marker = "ok" if row.ok else ("FAIL" if row.blocking else "warn")
        lines.append(f"[{marker:<4}] {row.name.ljust(width)}  {row.observed}")
        lines.append(f"{' ' * 7}expected: {row.expected}")
        if row.note:
            lines.append(f"{' ' * 7}note: {row.note}")
    lines.append("")
    lines.append(
        "preflight: ready - no blocking failure"
        if report.is_ready
        else "preflight: NOT ready - " + ", ".join(row.name for row in report.blocking_failures)
    )
    return "\n".join(lines)


def _call(command: str) -> tuple[bool, str]:
    """Run one management command in-process and capture its output.

    In: a whitelisted command name. No arguments — nothing from a request reaches this.
    Out: `(ok, output)`. `ok` is False when it raised, and the exception text *is* the
         output, because an operator needs to read the failure where they clicked.
    Side Effects: whatever the command does.
    Fails: never — a failure is reported, not raised, so the page still renders.
    """
    from io import StringIO

    buffer = StringIO()
    try:
        call_command(command, stdout=buffer, stderr=buffer, verbosity=1)
    except Exception as exc:  # noqa: BLE001 - the output is the report
        return False, f"{type(exc).__name__}: {exc}\n{buffer.getvalue()}".strip()
    return True, buffer.getvalue().strip() or "(the command produced no output)"


def _regenerate(uat: UatFileRef) -> tuple[bool, str]:
    """Rebuild the *selected* UAT's artefact by running the runner exactly as an operator would.

    A **subprocess**, not an import: `scripts/` is developer tooling and product code must
    not depend on it, and running the real command means this button cannot drift from the
    CLI. The preflight is written to a temp file and passed in, so the artefact carries the
    values observed at the moment it was built.
    """
    uat_path = REPO_ROOT / uat.path
    if not uat_path.exists():
        return False, f"{uat.path} does not exist"

    preflight_text = render_preflight(preflight())
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8", newline="\n"
    )
    try:
        handle.write(preflight_text)
        handle.close()
        completed = subprocess.run(
            (
                sys.executable,
                "scripts/uat_runner.py",
                "--file",
                uat.path,
                "--preflight",
                handle.name,
                "--database",
                database_name(),
            ),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        Path(handle.name).unlink(missing_ok=True)

    return completed.returncode == 0, (
        completed.stdout + completed.stderr
    ).strip() or "(the runner produced no output)"


def run_action(key: str, uat: UatFileRef | None = None) -> ActionOutcome:
    """Run one whitelisted action, for one registered UAT, and report what it did.

    In: `key` — one of `ACTIONS`' keys, refused otherwise; `uat` — the UAT selected on the
         console, defaulting to the first.
    Out: `ActionOutcome` carrying the command's own output.
    Side Effects: per action; see `ACTIONS` and `MANUAL_ONLY`.
    Fails: `KeyError` for a key outside the whitelist. The view turns that into a 400,
         because a request must never be able to name a command.
    """
    action = next((candidate for candidate in ACTIONS if candidate.key == key), None)
    if action is None:
        raise KeyError(key)
    selected = uat or uat_for(None)

    started = time.monotonic()
    if key == "check":
        ok, output = True, render_preflight(preflight())
    elif key == "regenerate":
        ok, output = _regenerate(selected)
    else:
        ok, output = _call(key)

    return ActionOutcome(
        key=action.key,
        label=action.label,
        uat=selected.slug,
        ok=ok,
        output=output,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
