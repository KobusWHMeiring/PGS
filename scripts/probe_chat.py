"""Read-only probe: what the chatbot retrieves, what it answers, and why.

This is the measuring instrument for the D17 revision (2026-10-21). The unit tests
pin control flow with fake providers; this script is the live evidence — the shipped
corpus, the real embedding arm and the real Gemini model — and it writes no rows, so
it can be run repeatedly while tuning retrieval or the prompt.

Usage:
    python scripts/probe_chat.py                     # the fixed measurement suite
    python scripts/probe_chat.py "can I use straw?"  # one question
    python scripts/probe_chat.py --chunks-only       # skip the model call
    python scripts/probe_chat.py --limit 8           # compare retrieval budgets

Every question is printed as: the terms and any term the corpus does not contain, the
retrieved passages with the arm that found them, the model's reply, and the citation
audit's verdict. A refusal is printed with its escalation reason, because "refused" and
"the corpus cannot answer" are different findings and the suite exists to tell them
apart.

**The default `--limit` is `settings.CHAT_RETRIEVAL_LIMIT`, and retrieval goes through
`core.services._chatbot.default_retrieval`** — the same function the view calls. That is
deliberate: this script once hardcoded 8 while the product used 5 and reported a
grounded answer for a question `/ask/` refuses (G8, `testing_hazards.md` §2.7). An
instrument that measures a different path is worse than no instrument.

No Django rows are written; `ChatMessage`/`EscalatedQuery` are not touched. The probe
constructs `RetrievedChunk`s and calls the provider directly, which is exactly what
`answer_question` does between retrieval and the audit.

Skipped from the gate on purpose: it needs a corpus and a Gemini key, and
`scripts/verify.sh` must stay runnable without either.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")

#: The measurement suite. Each line is a question a member of the group could actually
#: ask; together they cover the four ways a question can fail: an unnamed material
#: (cardboard, borax), a named one (straw, horse manure), a cost question that spans
#: several OPP sections, and a paraphrase with no distinctive noun (seeds, sign-up).
SUITE = (
    "Do i need to know where my horse manure comes from?",
    "Can i use cardboard from my neighbour?",
    "can I use straw mulch?",
    "what is the yearly cost to get certified, including the farm visit?",
    "can I use borax for boron supplements?",
    "if my ducks aren't fed organic food and I make compost from their bedding, will I still pass?",
    "how do I sign up?",
    "if I save seeds from a non-organic seed, are those seeds organic?",
    "if a seed is not organic but I grow it organic will the crop be organic?",
)


def _print_chunks(question: str, chunks, result) -> None:
    print(f"  arms: lexical_only={result.lexical_only}")
    for warning in result.warnings:
        print(f"  warning: {warning}")
    for position, chunk in enumerate(chunks, start=1):
        locator = chunk.section_ref or chunk.anchor or f"p.{chunk.page}"
        arms = []
        if chunk.lexical_rank is not None:
            arms.append(f"lex{chunk.lexical_rank}")
        if chunk.vector_rank is not None:
            arms.append(f"vec{chunk.vector_rank}")
        label = ",".join(arms) or "?"
        text = " ".join((chunk.text or "").split())[:90]
        print(f"  {position}. {locator:<16} [{label:<8}] {text}")


def probe(question: str, *, chunks_only: bool = False, limit: int | None = None) -> None:
    from core.services._chatbot import (
        REFUSAL,
        GeminiChatModel,
        UpstreamModelError,
        audit_citations,
        chat_retrieval_limit,
        default_retrieval,
        default_standard_set,
        significant_terms,
    )
    from knowledge.services import document_frequency

    budget = chat_retrieval_limit() if limit is None else limit
    standard_set = default_standard_set()
    terms = significant_terms(question)
    frequencies = {
        term: document_frequency(term, standard_set=standard_set) for term in terms
    }
    unknown = [term for term, count in frequencies.items() if count == 0]

    print(f"\n{'=' * 78}\nQ: {question}")
    print(f"  limit: {budget} (the product's budget)" if limit is None else f"  limit: {budget}")
    print(f"  terms: {terms}")
    print(f"  df:    {frequencies}")
    if unknown:
        print(f"  not in the corpus: {unknown}")

    result = default_retrieval(question, standard_set, limit=budget)
    _print_chunks(question, result.chunks, result)

    if chunks_only or not result.chunks:
        if not result.chunks:
            print(f"  -> REFUSAL before the model: {REFUSAL}")
        return

    model = GeminiChatModel()
    try:
        reply = model.answer(question=question, chunks=result.chunks, history=[])
    except UpstreamModelError as error:
        print(f"  -> UPSTREAM ERROR, no answer invented: {error}")
        return

    citations, problems = audit_citations(
        reply.citations,
        result.chunks,
        standard_set_id=standard_set.pk,
    )

    print(f"\n  ANSWER: {reply.answer or '(empty)'}")
    print(f"  insufficient_context: {reply.insufficient_context}")
    print(f"  citations: {len(reply.citations)} raw, {len(citations)} audited")
    for raw in reply.citations:
        locator = raw.get("section_ref", "?") + (
            f" · {raw['sub_ref']}" if raw.get("sub_ref") else ""
        )
        quote = " ".join(str(raw.get("quote", "")).split())[:140]
        print(f"    raw {locator} | {quote}")
    for citation in citations:
        quote = " ".join(citation.quote.split())[:110]
        print(f"    ok  {citation.locator} | {quote}")
    if problems:
        print("  AUDIT: REFUSED")
        for problem in problems:
            print(f"    ! {problem}")
    elif reply.insufficient_context or not citations or not reply.answer.strip():
        print("  AUDIT: would refuse (insufficient_context / no citation / empty)")
    else:
        print("  AUDIT: grounded")


def _show_chunks(title, chunks, *, carried_ids):
    """Print one retrieval set, marking the passage the parent answer cited."""
    print(f"  {title} ({len(chunks)} passages)")
    present = {chunk.chunk_id for chunk in chunks}
    for position, chunk in enumerate(chunks, start=1):
        locator = chunk.section_ref or chunk.anchor or f"p.{chunk.page}"
        arms = []
        if chunk.lexical_rank is not None:
            arms.append(f"lex{chunk.lexical_rank}")
        if chunk.vector_rank is not None:
            arms.append(f"vec{chunk.vector_rank}")
        marker = "  <== the parent answer cited this" if chunk.chunk_id in carried_ids else ""
        label = ",".join(arms) or "?"
        text = " ".join((chunk.text or "").split())[:80]
        print(f"    {position}. {locator:<16} [{label:<8}] {text}{marker}")
    return present


def _answer(question, chunks, standard_set, model):
    """Ask the model, audit it, print it. Returns the accepted chunk ids."""
    from core.services._chatbot import UpstreamModelError, audit_citations

    try:
        reply = model.answer(question=question, chunks=chunks, history=[])
    except UpstreamModelError as error:
        print(f"  -> UPSTREAM ERROR, no answer invented: {error}")
        return ()
    citations, problems = audit_citations(
        reply.citations, chunks, standard_set_id=standard_set.pk
    )
    print(f"  ANSWER: {' '.join((reply.answer or '(empty)').split())[:400]}")
    print(f"  citations: {len(reply.citations)} raw, {len(citations)} audited")
    for citation in citations:
        print(f"    ok  {citation.locator} | {' '.join(citation.quote.split())[:100]}")
    if problems:
        print("  AUDIT: REFUSED")
        for problem in problems:
            print(f"    ! {problem}")
    elif reply.insufficient_context or not citations or not reply.answer.strip():
        print("  AUDIT: would refuse (insufficient_context / no citation / empty)")
    else:
        print("  AUDIT: grounded")
    return tuple(citation.chunk_id for citation in citations)


def probe_follow_up(parent: str, follow_up: str, *, limit: int | None = None) -> None:
    """Measure one follow-up twice: as the product answers it before stage 1, and after.

    The product's path is mirrored exactly, not approximated:
    `default_retrieval` for retrieval, `build_retrieval_query` for the context arm,
    `_with_carried_citations` for the inheritance, and `audit_citations` for the verdict.

    Writes no rows. The answer cache is bypassed by calling the provider directly, so
    two runs of the same pair are comparable.
    """
    from core.services._chatbot import (
        GeminiChatModel,
        _with_carried_citations,
        build_retrieval_query,
        chat_retrieval_limit,
        default_retrieval,
        default_standard_set,
    )

    budget = chat_retrieval_limit() if limit is None else limit
    standard_set = default_standard_set()
    model = GeminiChatModel()
    print()
    print("=" * 78)
    print(f"FOLLOW-UP PROBE  (budget {budget})")

    print()
    print(f"PARENT: {parent}")
    parent_result = default_retrieval(parent, standard_set, limit=budget)
    _show_chunks("parent retrieval", parent_result.chunks, carried_ids=())
    carried_ids = _answer(parent, parent_result.chunks, standard_set, model)
    unique_carried = sorted(set(carried_ids))
    print(f"  CARRIED into the follow-up: {len(unique_carried)} clause(s) {unique_carried}")

    print()
    print(f"FOLLOW-UP: {follow_up}")

    print()
    print("--- A. before stage 1: the fragment alone")
    plain = default_retrieval(follow_up, standard_set, limit=budget)
    present = _show_chunks("retrieval", plain.chunks, carried_ids=set(carried_ids))
    print(f"  parent's cited clause present: {'YES' if set(carried_ids) & present else 'NO'}")
    _answer(follow_up, plain.chunks, standard_set, model)

    print()
    print("--- B. stage 1: context arm + the parent's cited clause")
    context_query = build_retrieval_query(parent)
    print(f"  context query: {context_query!r}")
    stage = default_retrieval(
        follow_up, standard_set, limit=budget, context_query=context_query
    )
    from_context = {chunk.chunk_id for chunk in stage.chunks} & set(carried_ids)
    merged = _with_carried_citations(stage.chunks, carried_ids, standard_set, budget=budget)
    present = _show_chunks("retrieval", merged, carried_ids=set(carried_ids))
    print(f"  parent's cited clause present: {'YES' if set(carried_ids) & present else 'NO'}")
    if from_context:
        print("  supplied by the context arm (the parent's words matched the clause)")
    elif set(carried_ids) & present:
        print("  supplied by the carried citation (the parent's words did not match)")
    _answer(follow_up, merged, standard_set, model)


def build_parser() -> argparse.ArgumentParser:
    """The CLI. Built per call so `--limit`'s default is read when it is built.

    The default is the product's own budget, not a number typed here: a hardcoded 8 hid
    G8 by measuring a retrieval path the product does not use.
    """
    from core.services._chatbot import chat_retrieval_limit

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="*", help="one question; omit for the suite")
    parser.add_argument(
        "--chunks-only",
        action="store_true",
        help="retrieval only: never call the model",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=chat_retrieval_limit(),
        help="passages to retrieve (default: settings.CHAT_RETRIEVAL_LIMIT)",
    )
    parser.add_argument(
        "--follow-up",
        nargs=2,
        metavar=("PARENT", "FOLLOW_UP"),
        help=(
            "measure one follow-up before and after stage 1: the parent question, then "
            "the follow-up. Runs three model calls and writes no rows."
        ),
    )
    return parser


def main() -> int:
    import django

    # Before the parser: `--limit`'s default comes from the product's own helper, and
    # importing the service module needs the app registry ready.
    django.setup()

    args = build_parser().parse_args()

    if args.follow_up:
        parent, follow_up = args.follow_up
        probe_follow_up(parent, follow_up, limit=args.limit)
        return 0

    questions = [" ".join(args.question)] if args.question else list(SUITE)
    for question in questions:
        probe(question, chunks_only=args.chunks_only, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
