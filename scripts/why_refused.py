#!/usr/bin/env python
"""Why did the chat refuse? Read the answer the database already recorded.

    venv/bin/python scripts/why_refused.py            # the last five refusals
    venv/bin/python scripts/why_refused.py borax      # and does the corpus know it
    venv/bin/python scripts/why_refused.py borax powder

Every refusal writes an `EscalatedQuery` with a **reason**, and every turn keeps the
chunks it retrieved in `ChatMessage.retrieved_chunks`. So "the bot said it could not
find that" is answerable without guessing, and without a model call.

This exists because `/ask/` is live and a refusal is invisible from the outside: the
visitor sees one sentence and the operator sees nothing. `chat_review` (plan P2.5) will
supersede it; until then this is the read-only probe.

Run it on the box with the deployment environment sourced:

    set -a; . ./.env; set +a
    venv/bin/python scripts/why_refused.py borax

Run `manage.py migrate` first on a dev box: the gate migrates `pgs_verify`, so `pgs` can
sit a migration behind and this will fail with `UndefinedColumn` after a model change.

Reading it — one reason names one finding, since the 2026-10-27 split:

    corpus*0        the live text does not contain the word at all — a corpus defect,
                    and the extractor is the first suspect (poppler vs Xpdf)
    NO_RETRIEVAL    nothing was retrieved, so the model was never asked — the defect is
                    in the key `search_terms` chose or in the corpus, not in the answer
    INSUFFICIENT_CONTEXT  it was retrieved, and the model still judged the set unusable
    CITATION_AUDIT  the model answered, and a quote or an address did not verify
    NO_CITATIONS    the model answered without citing — grounding, not retrieval
    EMPTY_ANSWER    the citations verified and the text was blank
    ANSWER_TOO_LONG the generation ran past `MAX_ANSWER_CHARS` and was refused, not cut

`NO_CITATIONS` used to cover the last four of those, so "group the refusals by reason"
grouped a runaway generation with a thin corpus. If you are reading a database written
before 2026-10-27, treat that value as "one of four" and read `refusal_checks`.

Since P2.5a the turn itself carries the evidence, so the `!` lines below are the failing
checks verbatim: `not present in the retrieved set` is a prompt-contract defect, `the
quote is not in the cited chunk` is a corpus defect. Before P2.5a that distinction was
thrown away, and G9 had to be diagnosed by re-asking the model.

**A `--force` re-ingest empties `retrieved_chunks` and the snapshot is what is left.** The
`retrieved(...)` line therefore falls back to the `grounding` snapshot's locators when the
M2M is empty, and says so — otherwise a probe run after a rebuild prints `retrieved(0)` on
a turn that retrieved five passages, which reads as a retrieval failure and is not one.
`manage.py relink_evidence` restores the links where the text is unchanged.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import django

REPO_ROOT = Path(__file__).resolve().parents[1]
if not (REPO_ROOT / "manage.py").exists():
    # Copied out of the tree to run on the box (`git show origin/main:... > /tmp/x.py`):
    # `parents[1]` is then `/tmp`'s parent, not the project. Fall back to the working
    # directory, which is what `cd ~/apps/pgs` establishes.
    REPO_ROOT = Path.cwd()
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")
django.setup()

from core.models import ChatMessage, EscalatedQuery  # noqa: E402
from knowledge.models import DocumentChunk  # noqa: E402

REFUSALS = 5
TURNS = 5


def _refs(message: ChatMessage) -> tuple[list[str], str]:
    """Out: the locators this turn was given, and where they were read from.

    The M2M first — it is the joinable record, and a link can be followed to the word. The
    `grounding` snapshot second, because a `--force` re-ingest cascades the links away and
    "retrieved(0)" on a turn that retrieved five passages is a lie the operator would act
    on. Never silent about which: the caller prints the source.
    """
    linked = [
        chunk.section_ref or chunk.anchor or f"p{chunk.page}"
        for chunk in message.retrieved_chunks.all()
    ]
    if linked:
        return linked, "retrieved"
    snapshot = [entry.get("locator", "") for entry in (message.grounding or [])]
    return [locator for locator in snapshot if locator], "snapshot"


def main(argv: list[str]) -> int:
    terms = [term for term in argv if term.strip()]
    if terms:
        print(f"== corpus: {len(terms)} term(s)")
        for term in terms:
            hits = DocumentChunk.objects.filter(text__icontains=term)
            print(f"   corpus*{hits.count():<3} {term!r}")
            for chunk in hits[:3]:
                body = chunk.text.replace("\n", " ")[:220]
                print(f"        {chunk.section_ref} | {body}")
        print()

    print(f"== last {REFUSALS} refusals")
    for escalated in EscalatedQuery.objects.order_by("-id")[:REFUSALS]:
        print(f"   #{escalated.id} {escalated.reason:<22} {escalated.question[:70]!r}")
    print()

    print(f"== last {TURNS} assistant turns")
    turns = ChatMessage.objects.filter(role=ChatMessage.Role.ASSISTANT).order_by("-id")
    for message in turns[:TURNS]:
        print(f"   #{message.id} {message.content[:70]!r}")
        refs, source = _refs(message)
        print(f"        {source}({len(refs)}): {refs}")
        raw = [entry.get("section_ref") for entry in (message.citations or {}).get("raw", [])]
        audited = [
            entry.get("section_ref") for entry in (message.citations or {}).get("accepted", [])
        ]
        if raw:
            print(f"        cited raw: {raw}")
        if raw and audited != raw:
            print(f"        audited:   {audited}")
        for problem in message.refusal_checks or []:
            print(f"        ! {problem}")
        if message.prompt_version:
            print(
                f"        {message.prompt_version} / corpus "
                f"{(message.corpus_fingerprint or '?')[:8]} / snapshot "
                f"{len(message.grounding or [])}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
