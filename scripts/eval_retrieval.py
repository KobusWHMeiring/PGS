"""Read-only instrument: how well does retrieval find the passage that answers a question?

This is the runner half of `product/backlog/spike/RETRIEVAL_EVAL_SPIKE.md` (S1). It scores
retrieval against `knowledge/tests/data/retrieval_eval.json` — a committed set of graded
questions whose expected passages were read off the *documents*, not off retrieval's own
output (`testing_hazards.md` §2.7).

Usage:

    python scripts/eval_retrieval.py                       # the set, `bare`, recall@1…8
    python scripts/eval_retrieval.py --variant lexical     # the lexical arm alone
    python scripts/eval_retrieval.py --variant vector      # the semantic arm alone
    python scripts/eval_retrieval.py --variant all         # bare + lexical + vector, one run
    python scripts/eval_retrieval.py --k 5 --json          # machine-readable
    python scripts/eval_retrieval.py --set path/to/set.json

**It calls the product's own retrieval path.** `bare` is
`core.services._chatbot.default_retrieval`, the function `answer_question()` calls, at the
product's own budget. An instrument that re-implements retrieval measures a system nobody
uses — the defect `probe_chat.py` records fixing when it once hardcoded `limit=8` while the
product used 5. `tests/tools/test_eval_retrieval.py` asserts the import.

What each variant is, precisely — including where it is *not* a product path:

    bare     the product, unchanged: rare-term arm, semantic arm, alias arm, fusion.
    lexical  the product with no embedding key configured (`GEMINI_API_KEY=""`), which is
             a state the app really runs in (`deploy/README.md`): the vector arm degrades
             to lexical inside `search()` itself, so this is the same code path.
    vector   **not a product path.** `knowledge.services.vector_search` on the embedded
             question, i.e. the semantic arm in isolation. It exists to price the arm
             (spike §2 Q2); nothing in the product retrieves this way.
    context  D73's context-bearing embed text. Not available until the table block lands
             and the stored column exists — S2 of the spike. This variant refuses rather
             than reporting a number for something that has not been built.

Nothing is written: no rows, no cache, no files. Safe to re-run while tuning.

**The one thing this must never do is report a vector result it did not measure.** If the
query embedding cannot run (no key, no stored vectors), the `vector` variant fails loudly
and `bare` says so in its aggregates — because "the vector arm scored 0" and "the vector
arm never ran" call for opposite conclusions, and the second one is the truth.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")

from scripts.eval_set import (  # noqa: E402  (path first: the script runs from anywhere)
    DEFAULT_SET,
    EvalSet,
    EvalSetError,
    EvalItem,
    corpus_info,
    load_eval_set,
    resolve,
)

#: The variants `--variant` accepts beyond the three `all` runs.
UNAVAILABLE = {"context": "D73"}

#: The three variants that exist today, and what `--variant all` runs.
VARIANTS = ("bare", "lexical", "vector")
ALL = VARIANTS

#: The recall cut-offs reported. @5 is the product's shipped budget and the one that changes
#: an answer; @8 is the deepest the chat's citation ceiling can use (`MAX_CITATIONS`).
CUTOFFS = (1, 3, 5, 8)


class VariantUnavailable(RuntimeError):
    """This variant has not been built, so there is no number to report for it."""


# --- Retrieval, per variant -------------------------------------------------


@contextlib.contextmanager
def no_embedding_key():
    """The corpus as an instance with no Gemini key sees it: the vector arm cannot run.

    This is a real deployment state (`deploy/first-install.sh` writes an empty key and
    `deploy/README.md` explains the consequence), not a harness fiction — `search()`
    itself records the degradation in `warnings` and `lexical_only`. The setting is
    restored on the way out, including on an exception.
    """
    from django.conf import settings

    original = getattr(settings, "GEMINI_API_KEY", "")
    settings.GEMINI_API_KEY = ""
    try:
        yield
    finally:
        settings.GEMINI_API_KEY = original


def retrieve(variant: str, question: str, standard_set, *, limit: int):
    """Run one variant's retrieval and return a `RetrievalResult`.

    In:  the variant name; the question; the corpus; how many passages to keep.
    Out: the result, exactly as the product would produce it for `bare`/`lexical`.
    Side Effects: embeds the query over the network for `bare` and `vector`.
    Fails: `VariantUnavailable` for `context` (not built); `EvalSetError` when `vector`
        cannot embed, rather than scoring zero for a measurement that did not happen.
    """
    from core.services._chatbot import default_retrieval

    if variant == "context":
        raise VariantUnavailable(
            "the `context` variant needs D73's stored `embedding_text` column, which does "
            "not exist until the table block lands. That is S2 of the spike; reporting a "
            "number for it now would be reporting a different corpus."
        )
    if variant == "bare":
        return default_retrieval(question, standard_set, limit=limit)
    if variant == "lexical":
        with no_embedding_key():
            return default_retrieval(question, standard_set, limit=limit)
    if variant == "vector":
        return _vector_only(question, standard_set, limit=limit)
    raise SystemExit(f"unknown variant {variant!r}; expected {VARIANTS}")


def _vector_only(question: str, standard_set, *, limit: int):
    """The semantic arm alone — the only variant with no product path behind it.

    Both pieces are the library's own: `knowledge.services.vector_search` for the ranking
    and `chunks_by_id` for the passages, so the citations this produces render exactly as
    the product's do. What is *not* the product's is the fusion: nothing in the app
    retrieves vector-only, and a number from here describes the arm, never the chatbot.
    """
    from knowledge.embedding import EmbeddingError, embed_texts
    from knowledge.services import RetrievalResult, chunks_by_id, vector_search

    try:
        vector = embed_texts([question])[0]
    except EmbeddingError as error:  # pragma: no cover - needs a broken provider
        raise EvalSetError(
            "the `vector` variant could not embed the question, so there is no vector "
            f"number to report: {error}"
        ) from error
    ranked = vector_search(vector, standard_set=standard_set, limit=limit)
    chunks = chunks_by_id([chunk_id for chunk_id, _ in ranked], standard_set=standard_set)
    return RetrievalResult(
        query=question,
        standard_set_id=getattr(standard_set, "pk", None),
        # `chunks_by_id` deliberately reports no rank (a carried passage was not ranked),
        # but here the position *is* the vector arm's rank, and the report's per-arm column
        # would otherwise read "none" for every hit.
        chunks=tuple(
            replace(chunk, vector_rank=position)
            for position, chunk in enumerate(chunks, start=1)
        ),
    )


# --- Scoring ----------------------------------------------------------------


@dataclass(frozen=True)
class QuestionResult:
    item_id: str
    question: str
    asked_by: str
    answerable: bool
    first_hit_rank: int | None
    found_by: str
    #: `{cutoff: hit}` for recall. Only meaningful for an answerable item.
    recall: tuple[tuple[int, bool], ...]
    reciprocal_rank: float
    distractor_ranks: tuple[int, ...]
    #: The locator of every passage that came back, best first. Carried so a reader can
    #: ask "what came back instead?" without re-running anything — the first question a
    #: miss provokes, and the one that catches a wrong expectation.
    passages: tuple[str, ...]
    retrieved: int
    lexical_only: bool
    citations_accepted: int
    citations_audited: int
    problems: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "id": self.item_id,
            "question": self.question,
            "asked_by": self.asked_by,
            "answerable": self.answerable,
            "first_hit_rank": self.first_hit_rank,
            "found_by": self.found_by,
            "recall": {str(cutoff): hit for cutoff, hit in self.recall},
            "reciprocal_rank": round(self.reciprocal_rank, 4),
            "distractor_ranks": list(self.distractor_ranks),
            "passages": list(self.passages),
            "retrieved": self.retrieved,
            "lexical_only": self.lexical_only,
            "citations_accepted": self.citations_accepted,
            "citations_audited": self.citations_audited,
            "problems": list(self.problems),
        }


def _arm_label(chunk) -> str:
    """Which arm(s) supplied this passage, in `probe_chat`'s own notation."""
    arms = []
    if getattr(chunk, "lexical_rank", None) is not None:
        arms.append(f"lex{chunk.lexical_rank}")
    if getattr(chunk, "vector_rank", None) is not None:
        arms.append(f"vec{chunk.vector_rank}")
    return ",".join(arms)


def score_item(
    item: EvalItem,
    resolved: dict[int, set[int]],
    chunks,
    *,
    k: int,
    lexical_only: bool,
    audit: bool = True,
) -> QuestionResult:
    """Grade one question's retrieved set.

    In:  the item; its resolved expectations — `{index into item.expected: chunk ids}`;
         the passages retrieval returned (best first); `k` — how deep to look;
         `lexical_only` — what retrieval reported about its arms.
    Out: a `QuestionResult`. `first_hit_rank` is the rank of the earliest **grade-2**
         passage, which is the metric that matters: the top of the list is what the model
         reads, so one right passage at rank 1 beats four at rank 8.
    """
    from core.services._chatbot import locator_of

    top = list(chunks)[:k]
    answers: list[int] = []
    distractor_ranks: list[int] = []
    for position, chunk in enumerate(top, start=1):
        chunk_id = getattr(chunk, "chunk_id", None)
        for index, chunk_ids in resolved.items():
            if chunk_id not in chunk_ids:
                continue
            if item.expected[index].grade == 0:
                distractor_ranks.append(position)
            elif item.expected[index].grade == 2:
                answers.append(position)
    first = min(answers) if answers else None
    found_by = ""
    if first is not None:
        found_by = _arm_label(top[first - 1])

    accepted, audited, problems = _audit(top) if audit else (0, 0, ())
    return QuestionResult(
        item_id=item.id,
        question=item.question,
        asked_by=item.asked_by,
        answerable=item.answerable,
        first_hit_rank=first,
        found_by=found_by,
        recall=tuple(
            (cutoff, first is not None and first <= cutoff) for cutoff in CUTOFFS
        ),
        reciprocal_rank=(1.0 / first) if first else 0.0,
        distractor_ranks=tuple(sorted(distractor_ranks)),
        passages=tuple(locator_of(chunk) for chunk in top),
        retrieved=len(top),
        lexical_only=lexical_only,
        citations_accepted=accepted,
        citations_audited=audited,
        problems=problems,
    )


def _audit(chunks) -> tuple[int, int, tuple[str, ...]]:
    """Would the citation audit accept each retrieved passage, quoted verbatim?

    In:  the retrieved passages.
    Out: `(accepted, audited, problems)` — a citation is built from the passage's own
         locator and full text, exactly what a faithful model would emit, and run through
         `audit_citations`. The real success criterion is not "found" but **quotable**: a
         passage whose locator is missing or ambiguous is a refusal with extra steps, and
         that is invisible in every ranking metric (spike §3.2).

    The passages are audited as one set, not one call each, because the audit's ambiguity
    rule is intra-set: two stored locators that normalise to the same key are ambiguous
    *within the set the model was given*.
    """
    from core.services._chatbot import MAX_CITATIONS, audit_citations, locator_of

    audited_chunks = list(chunks)[:MAX_CITATIONS]
    if not audited_chunks:
        return 0, 0, ()
    standard_set_id = getattr(audited_chunks[0], "standard_set_id", None)
    raw = [
        {"section_ref": locator_of(chunk), "quote": chunk.text}
        for chunk in audited_chunks
        if locator_of(chunk)
    ]
    if not raw:
        return 0, len(audited_chunks), ("no retrieved passage had a locator",)
    citations, problems = audit_citations(
        raw, audited_chunks, standard_set_id=standard_set_id
    )
    return len(citations), len(audited_chunks), tuple(problems)


# --- The run, and its aggregates -------------------------------------------


@dataclass(frozen=True)
class Report:
    variant: str
    k: int
    corpus: CorpusInfo
    model: str
    dimension: int
    results: tuple[QuestionResult, ...] = ()
    notes: tuple[str, ...] = field(default=())

    @property
    def answerable(self) -> tuple[QuestionResult, ...]:
        return tuple(result for result in self.results if result.answerable)

    def aggregates(self) -> dict:
        """The numbers the spike's table needs, per variant (spike §3.2)."""
        answerable = self.answerable
        count = len(answerable)
        recall = {
            cutoff: (
                sum(1 for result in answerable if dict(result.recall)[cutoff]) / count
                if count
                else 0.0
            )
            for cutoff in CUTOFFS
        }
        mrr = (sum(result.reciprocal_rank for result in answerable) / count) if count else 0.0
        audited = sum(result.citations_audited for result in self.results)
        accepted = sum(result.citations_accepted for result in self.results)
        refusals = tuple(result for result in self.results if not result.answerable)
        by_arm = {"lexical": 0, "vector": 0, "both": 0, "none": 0}
        for result in answerable:
            if result.first_hit_rank is None:
                by_arm["none"] += 1
                continue
            lex = "lex" in result.found_by
            vec = "vec" in result.found_by
            by_arm["both" if lex and vec else "vector" if vec else "lexical" if lex else "none"] += 1
        return {
            "questions": len(self.results),
            "answerable": count,
            "refusals": len(refusals),
            "recall": {str(cutoff): round(value, 4) for cutoff, value in recall.items()},
            "mrr": round(mrr, 4),
            "citation_pass_rate": round(accepted / audited, 4) if audited else None,
            "citations_audited": audited,
            "distractor_at_1": sum(1 for r in self.results if 1 in r.distractor_ranks),
            "distractor_in_set": sum(1 for r in self.results if r.distractor_ranks),
            "found_by_arm": by_arm,
            # The one aggregate that can invalidate the whole run, so it is a number and
            # not a footnote: if every question is lexical-only, the vector arm never ran
            # and nothing here prices it.
            "lexical_only_questions": sum(1 for r in self.results if r.lexical_only),
            "refusals_returning_a_set": sum(1 for r in refusals if r.retrieved),
            "audit_problems": sorted(
                {problem for r in self.results for problem in r.problems}
            ),
            "notes": list(self.notes),
        }

    def as_dict(self) -> dict:
        return {
            "variant": self.variant,
            "k": self.k,
            "corpus": self.corpus.as_dict(),
            "embedding_model": self.model,
            "embedding_dimension": self.dimension,
            "aggregates": self.aggregates(),
            "questions": [result.as_dict() for result in self.results],
        }


def run(
    variant: str,
    eval_set: EvalSet,
    standard_set,
    *,
    k: int,
    audit: bool = True,
) -> Report:
    """Retrieve every question once, in one variant, and score it.

    In:  the variant; the set; the corpus; `k` — retrieval depth; `audit` — run the
         citation audit on the retrieved set (off is faster, and measures nothing else).
    Out: a `Report`.
    Side Effects: embeds queries over the network for `bare`/`vector`; writes nothing.
    """
    from django.conf import settings

    resolved = resolve(eval_set.items, standard_set)
    results = []
    for item in eval_set.items:
        result = retrieve(variant, item.question, standard_set, limit=k)
        results.append(
            score_item(
                item,
                resolved[item.id],
                result.chunks,
                k=k,
                lexical_only=result.lexical_only,
                audit=audit,
            )
        )

    notes: list[str] = []
    if variant in ("bare", "lexical") and all(r.lexical_only for r in results):
        notes.append(
            "the vector arm never ran in this run, so these numbers describe the lexical "
            "path only. A `bare` run that is 100% lexical is NOT evidence about the "
            "semantic arm — check GEMINI_API_KEY and that the corpus carries embeddings."
        )
    return Report(
        variant=variant,
        k=k,
        corpus=corpus_info(standard_set),
        model=str(getattr(settings, "EMBEDDING_MODEL", "")),
        dimension=int(getattr(settings, "EMBEDDING_DIM", 0) or 0),
        results=tuple(results),
        notes=tuple(notes),
    )


# --- Output -----------------------------------------------------------------


def print_report(report: Report, *, product_limit: int, show: bool = False) -> None:
    """One screen: the per-question verdicts, then the aggregates.

    `show` prints the passages that actually came back, in one line per question. It is
    deliberately off by default: reading the retrieved set before writing an expectation is
    how a set gets graded against the system instead of the document (spike §3.1 rule 1).
    It belongs here for the *second* reader, the one asking why a question missed.
    """
    aggregates = report.aggregates()
    print()
    print("=" * 100)
    print(
        f"retrieval eval | variant `{report.variant}` | k {report.k} | "
        f"product budget {product_limit} | {len(report.results)} questions"
    )
    print(f"corpus: {report.corpus.line()}")
    print(f"embedding: {report.model} ({report.dimension}d)")
    print("-" * 100)
    for result in report.results:
        marks = " ".join(
            f"@{cutoff}{'y' if hit else '.'}" for cutoff, hit in result.recall
        )
        if result.answerable:
            rank = result.first_hit_rank
            verdict = (
                f"rank {rank:<2} {result.found_by or '-':<12}"
                if rank
                else "NOT FOUND       "
            )
            grade_0 = (
                f" | distractor@{','.join(map(str, result.distractor_ranks))}"
                if result.distractor_ranks
                else ""
            )
        else:
            verdict = f"{result.retrieved} passages returned (a refusal was correct)"
            grade_0 = ""
        audit = (
            f"audit {result.citations_accepted}/{result.citations_audited}"
            if result.citations_audited
            else "audit -"
        )
        print(f"{result.item_id:<38} {verdict} {marks} {audit}{grade_0}")
        print(f"    {result.question}")
        if show:
            print(f"    -> {', '.join(result.passages) or '(nothing)'}")
        for problem in result.problems:
            print(f"    ! {problem}")
    print("-" * 100)
    recall = "  ".join(
        f"R@{cutoff} {aggregates['recall'][str(cutoff)]:.3f}" for cutoff in CUTOFFS
    )
    print(f"  {recall}   MRR {aggregates['mrr']:.3f}")
    print(
        f"  citation audit pass rate {aggregates['citation_pass_rate']}"
        f"  ({aggregates['citations_audited']} passages audited)"
    )
    print(
        f"  found by: {aggregates['found_by_arm']}   "
        f"distractors: @1 {aggregates['distractor_at_1']}, "
        f"anywhere {aggregates['distractor_in_set']}"
    )
    print(
        f"  refusal items returning a set: {aggregates['refusals_returning_a_set']}"
        f"/{aggregates['refusals']}   lexical-only questions: "
        f"{aggregates['lexical_only_questions']}/{aggregates['questions']}"
    )
    if report.k < product_limit:
        print(
            f"  NOTE: k={report.k} is shallower than the product's own budget of "
            f"{product_limit} passages; nothing deeper was measured."
        )
    if report.k < max(CUTOFFS):
        beyond = ", ".join(f"@{cutoff}" for cutoff in CUTOFFS if cutoff > report.k)
        print(
            f"  NOTE: k={report.k} is shallower than those cut-offs ({beyond}); they are not "
            f"measured and are reported equal to recall@{report.k}."
        )
    for note in report.notes:
        print(f"  !! {note}")
    for problem in aggregates["audit_problems"]:
        print(f"  ! audit: {problem}")


def comparison(reports: list[Report]) -> None:
    """The table the spike's §8.3 asks for: one row per variant, same set, same corpus."""
    print()
    print("=" * 100)
    print("comparison")
    print(f"{'variant':<10}{'R@1':>7}{'R@3':>7}{'R@5':>7}{'R@8':>7}{'MRR':>7}"
          f"{'audit':>8}{'g0@1':>6}{'lex-only':>10}")
    for report in reports:
        aggregates = report.aggregates()
        audit = aggregates["citation_pass_rate"]
        print(
            f"{report.variant:<10}"
            f"{aggregates['recall']['1']:>7.3f}"
            f"{aggregates['recall']['3']:>7.3f}"
            f"{aggregates['recall']['5']:>7.3f}"
            f"{aggregates['recall']['8']:>7.3f}"
            f"{aggregates['mrr']:>7.3f}"
            f"{(f'{audit:.3f}' if audit is not None else '-'):>8}"
            f"{aggregates['distractor_at_1']:>6}"
            f"{aggregates['lexical_only_questions']:>7}/{len(report.results):<3}"
        )
    print()
    print("g0@1 = questions whose top passage is a grade-0 distractor (over-retrieval).")
    print("lex-only = questions on which the vector arm did not contribute at all.")


def _make_stdout_printable() -> None:
    """Do not crash the instrument because a document prints an unprintable glyph.

    A Windows dev box hands this script a cp1252 stdout, and the OPP's own text carries
    U+25CF. A measurement that dies on a character, after spending the embedding calls,
    is a tool people stop running — the same lesson as §2.9's extraction fixtures. The
    statistics are ASCII; only echoed corpus text can be odd, so replacing an
    unencodable character in the report costs nothing and losing the run costs everything.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:  # pragma: no cover - depends on the console
            continue
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):  # a captured or closed stream is not an error here
            pass


def build_parser() -> argparse.ArgumentParser:
    """The CLI. `--k`'s default is read when the parser is built, from the product."""
    from core.services._chatbot import chat_retrieval_limit

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--variant",
        choices=(*VARIANTS, "all", *UNAVAILABLE),
        default="bare",
        help="which retrieval path to measure (default: bare — the product's own)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help=(
            "passages to retrieve (default: the deeper of 8 and "
            f"CHAT_RETRIEVAL_LIMIT={chat_retrieval_limit()})"
        ),
    )
    parser.add_argument("--set", default=str(DEFAULT_SET), help="the eval set to run")
    parser.add_argument(
        "--json", action="store_true", help="machine-readable output instead of a report"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="print the passages each question retrieved, best first",
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="skip the citation-audit pass (faster; reports no pass rate)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import django

    _make_stdout_printable()
    django.setup()

    from core.services._chatbot import chat_retrieval_limit, default_standard_set

    args = build_parser().parse_args(argv)
    product_limit = chat_retrieval_limit()
    # Never measure shallower than the product actually retrieves: an @8 column filled
    # from a 5-passage set is a number that looks measured and is not (§2.7).
    k = args.k if args.k else max(max(CUTOFFS), product_limit)

    if args.variant in UNAVAILABLE:
        raise VariantUnavailable(
            f"`--variant {args.variant}` is not available yet: it needs D73's stored "
            "embedding text (spike §0, S2). Nothing was measured."
        )
    eval_set = load_eval_set(args.set)
    standard_set = default_standard_set()
    variants = list(ALL) if args.variant == "all" else [args.variant]

    reports = []
    for variant in variants:
        report = run(
            variant, eval_set, standard_set, k=k, audit=not args.no_audit
        )
        reports.append(report)
        if not args.json:
            print_report(report, product_limit=product_limit, show=args.show)

    if args.json:
        payload = {
            "set": eval_set.name,
            "product_limit": product_limit,
            "reports": [report.as_dict() for report in reports],
        }
        print(json.dumps(payload, indent=2, sort_keys=False))
    elif len(reports) > 1:
        comparison(reports)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (VariantUnavailable, EvalSetError) as error:
        # A measurement that cannot be made says so in one line and exits non-zero. A
        # traceback here reads like a bug in the corpus, and the next reader would spend
        # an hour on it before discovering that the variant was never built.
        print(f"eval_retrieval: {error}", file=sys.stderr)
        raise SystemExit(2) from error
