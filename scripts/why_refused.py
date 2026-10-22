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

Reading it:

    corpus*0        the live text does not contain the word at all — a corpus defect,
                    and the extractor is the first suspect (poppler vs Xpdf)
    INSUFFICIENT_CONTEXT  it was retrieved, and the model still judged the set unusable
    CITATION_AUDIT  the model answered, and its quote did not verify against the text
    NO_CITATIONS    the model answered without citing — grounding, not retrieval
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import django

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")
django.setup()

from core.models import ChatMessage, EscalatedQuery  # noqa: E402
from knowledge.models import DocumentChunk  # noqa: E402

REFUSALS = 5
TURNS = 5


def _refs(message: ChatMessage) -> list[str]:
    return [
        chunk.section_ref or chunk.anchor or f"p{chunk.page}"
        for chunk in message.retrieved_chunks.all()
    ]


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
        refs = _refs(message)
        print(f"        retrieved({len(refs)}): {refs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
