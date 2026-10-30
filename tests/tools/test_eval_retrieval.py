"""The retrieval eval instrument must not be able to lie about what it measured.

The spike (`product/backlog/spike/RETRIEVAL_EVAL_SPIKE.md` §4) makes exactly three things
permanent tests, because they are the three ways this instrument fails *silently*:

1. **The set parses and every locator resolves.** A re-ingest re-splits chunks; a question
   whose locator stops resolving would delete itself from the measurement while the run
   stayed green (spike §3.1 rule 4).
2. **The runner uses the product's retrieval path.** An instrument that re-implements
   retrieval measures a system nobody uses — `probe_chat.py` hid G8 exactly that way
   (`testing_hazards.md` §2.7).
3. **A refusal item exists**, so over-retrieval stays measurable (spike §3.1 rule 3).

Everything else here protects a *number* rather than a feature: recall is divided by the
answerable items alone, a grade-0 passage is never counted as a hit, and a run in which the
vector arm never ran says so. Each of those, got wrong, produces a plausible figure that
calls for the opposite decision — the expensive kind of defect.

`test_every_locator_resolves_against_the_ingested_corpus` is marked `slow`: it ingests all
four governed documents. The gate runs it; `scripts/fast.sh` does not.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import eval_retrieval, eval_set
from scripts.eval_set import (
    DEFAULT_SET,
    EvalItem,
    EvalSet,
    EvalSetError,
    Expected,
    corpus_info,
    load_eval_set,
    resolve,
)

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
PDFS = {
    "saoso": REPO_ROOT / "pgs_docs" / "saoso-version-2.1-2026.pdf",
    "opp": REPO_ROOT / "pgs_docs" / "Outeniqua pgs principles, policies and procedures 2026.pdf",
    "bpp": REPO_ROOT / "pgs_docs" / "Basic Production Principles_ENG_PRINT.pdf",
    "landscape": REPO_ROOT / "pgs_docs" / "PGS Certification landscape_Final.pdf",
}


def _write_set(tmp_path: Path, items: list[dict]) -> Path:
    path = tmp_path / "eval.json"
    path.write_text(json.dumps({"items": items}), encoding="utf-8")
    return path


def _chunk(chunk_id: int, *, locator="S1", text="text", lexical=None, vector=None):
    """The four attributes scoring reads off a retrieved passage."""
    return SimpleNamespace(
        chunk_id=chunk_id,
        section_ref=locator,
        anchor="",
        page=1,
        text=text,
        lexical_rank=lexical,
        vector_rank=vector,
        standard_set_id=None,
    )


# --- 1. The set is real ground truth, not a snapshot of the output ----------


def test_the_set_parses_and_carries_the_shape_the_spike_asks_for():
    """30–40 items, ≥10 real escalations, ≥1 refusal, and a recorded judgement each."""
    eval_set_ = load_eval_set()

    assert 30 <= len(eval_set_.items) <= 40, "spike §3.1: small enough to grade by hand"
    assert len({item.id for item in eval_set_.items}) == len(eval_set_.items)

    escalations = [i for i in eval_set_.items if i.asked_by == "escalation"]
    assert len(escalations) >= 10, (
        "spike §6 kill criterion: without ten real questions the set is not evidence of "
        "anything a person asked"
    )
    assert eval_set_.refusals, "spike §4.3: an unanswerable question must be a member"
    assert any(
        any(entry.grade == 0 for entry in item.expected) for item in eval_set_.items
    ), "a grade-0 distractor is how over-retrieval gets measured (spike §3.1 rule 3)"
    assert all(item.note for item in eval_set_.items), (
        "every item records the judgement behind its grading; an unexplained expectation "
        "is the one a later reader cannot check against the paper"
    )
    assert all(item.asked_by in eval_set.SOURCES for item in eval_set_.items)


def test_a_typo_in_a_graded_item_fails_loudly(tmp_path):
    """Mutation: dropping the unknown-key check turns this question into a refusal item.

    A refusal item scores better than a miss, so a silently ignored `"expect"` would
    *improve* the reported numbers. That is the failure this guard exists for.
    """
    path = _write_set(
        tmp_path,
        [
            {
                "id": "typo",
                "asked_by": "curated",
                "question": "q?",
                "expect": [{"doc": "saoso", "locator": "S1", "grade": 2}],
            }
        ],
    )
    with pytest.raises(EvalSetError, match="unknown key"):
        load_eval_set(path)


def test_an_unknown_provenance_is_refused(tmp_path):
    path = _write_set(
        tmp_path, [{"id": "x", "asked_by": "vibes", "question": "q?", "expected": []}]
    )
    with pytest.raises(EvalSetError, match="asked_by"):
        load_eval_set(path)


def test_a_grade_outside_zero_two_is_refused(tmp_path):
    path = _write_set(
        tmp_path,
        [
            {
                "id": "x",
                "asked_by": "curated",
                "question": "q?",
                "expected": [{"doc": "saoso", "locator": "S1", "grade": 3}],
            }
        ],
    )
    with pytest.raises(EvalSetError, match="grade"):
        load_eval_set(path)


# --- 2. Locators resolve, or the run stops ---------------------------------


@pytest.fixture
def tiny_corpus(db):
    """One document whose title is a governed key, with three chunk locators."""
    from knowledge.models import DocumentChunk, StandardDocument, StandardSet

    standard_set = StandardSet.objects.create(code="tiny", label="Tiny", is_default=True)
    document = StandardDocument.objects.create(
        standard_set=standard_set,
        kind="STANDARD",
        issuing_body="SAOSO",
        title="SAOSO Standard for Organic Production and Processing",
        version="2.1",
        source_file="saoso.pdf",
        sha256="a" * 64,
        section_scheme="saoso",
    )
    for ref, text in (
        ("S20.1", "20.1 General"),
        ("S20.1.2", "20.1.2 traceability"),
        ("Appendix 6a", "Ewes 13,3"),
    ):
        DocumentChunk.objects.create(
            document=document, section_ref=ref, text=text, heading_path=ref, page=85
        )
    return standard_set


def test_an_unresolvable_locator_stops_the_run(tiny_corpus):
    """Mutation: skipping an empty match instead of raising makes this test red."""
    item = EvalItem(
        id="bogus",
        question="q?",
        asked_by="curated",
        expected=(Expected(doc="saoso", locator="S99.9", grade=2),),
    )

    with pytest.raises(EvalSetError, match="S99.9"):
        resolve([item], tiny_corpus)


def test_a_contains_that_matches_nothing_is_an_error_not_a_miss(tiny_corpus):
    """The row-level tie-breaker must fail loudly too, or 'the ewes row' becomes 'any row'."""
    item = EvalItem(
        id="ewes",
        question="how many sheep?",
        asked_by="design",
        expected=(
            Expected(doc="saoso", locator="Appendix 6a", grade=2, contains="goats"),
        ),
    )

    with pytest.raises(EvalSetError, match="goats"):
        resolve([item], tiny_corpus)


def test_a_section_locator_covers_its_own_clauses(tiny_corpus):
    """`S20.1` must resolve: a clause split across chunks is one clause to a reader."""
    item = EvalItem(
        id="section",
        question="q?",
        asked_by="curated",
        expected=(Expected(doc="saoso", locator="S20.1", grade=2),),
    )
    resolved = resolve([item], tiny_corpus)[item.id]
    assert len(resolved[0]) == 2, "the prefix must match S20.1 and S20.1.2, and nothing else"


def test_a_section_locator_does_not_swallow_a_longer_number(tiny_corpus):
    """`S2` must not match `S20.1`: a short locator would otherwise resolve to everything."""
    item = EvalItem(
        id="short",
        question="q?",
        asked_by="curated",
        expected=(Expected(doc="saoso", locator="S2", grade=2),),
    )
    with pytest.raises(EvalSetError):
        resolve([item], tiny_corpus)


def test_the_corpus_digest_notices_a_new_chunk(tiny_corpus):
    """A recorded number is worthless if the digest it carries never moves."""
    from knowledge.models import DocumentChunk

    before = corpus_info(tiny_corpus)
    DocumentChunk.objects.create(
        document=tiny_corpus.documents.get(), section_ref="S20.1.3", text="more"
    )
    after = corpus_info(tiny_corpus)

    assert (before.chunk_count, before.digest) != (after.chunk_count, after.digest)


@pytest.mark.slow
def test_every_locator_resolves_against_the_ingested_corpus(db, settings, monkeypatch):
    """The whole committed set, against the four documents as they are ingested today.

    This is the assertion that keeps the set from rotting: if a re-ingest re-splits a
    chunk, `resolve` raises here by name rather than quietly lowering a recall number.
    """
    from knowledge.ingest import ingest_standard
    from knowledge.models import StandardSet
    from knowledge.tests.page_fixtures import stub_ingest_extraction

    settings.GEMINI_API_KEY = ""
    stub_ingest_extraction(monkeypatch)
    standard_set = StandardSet.objects.create(
        code="outeniqua", label="Outeniqua PGS corpus", is_default=True
    )
    for key, path in PDFS.items():
        ingest_standard(pdf_path=path, standard_set=standard_set, doc_key=key, embed=False)

    eval_set_ = load_eval_set()

    resolved = resolve(eval_set_.items, standard_set)

    assert len(resolved) == len(eval_set_.items)
    assert all(
        all(chunk_ids for chunk_ids in per_item.values())
        for per_item in resolved.values()
    ), "an expectation resolved to no chunks; resolve() should have raised"


# --- 3. The runner measures the product, not a copy of it ------------------


def test_the_runner_uses_the_product_retrieval_function():
    """One retrieval path. Mutation: calling `search_terms(...)` here makes this red.

    The same guard `tests/tools/test_probe_chat.py` carries, for the same reason: the eval
    runner and the view must not be able to drift apart while both stay green.
    """
    source = Path(eval_retrieval.__file__).read_text(encoding="utf-8")

    assert "default_retrieval(" in source
    assert "search_terms(" not in source
    assert "lexical_search(" not in source


def test_the_bare_variant_is_the_product_call(monkeypatch):
    """`bare` must *be* `default_retrieval`, not a wrapper that happens to agree."""
    from core.services import _chatbot

    seen: dict[str, object] = {}

    def spy(question, standard_set, *, limit=None):
        seen.update(question=question, limit=limit)
        return SimpleNamespace(chunks=(), lexical_only=False, warnings=())

    monkeypatch.setattr(_chatbot, "default_retrieval", spy)
    eval_retrieval.retrieve("bare", "a question", object(), limit=7)

    assert seen == {"question": "a question", "limit": 7}


def test_the_lexical_variant_removes_the_key_and_puts_it_back(settings):
    """The variant is the real no-key deployment state, and it must not leak.

    `search()` decides on `settings.GEMINI_API_KEY`, so blanking it is exactly how an
    instance without a key behaves — including the warning it records. A leaked empty
    setting would silently turn every later run into a lexical one.
    """
    settings.GEMINI_API_KEY = "a-real-key"

    with eval_retrieval.no_embedding_key():
        assert settings.GEMINI_API_KEY == ""

    assert settings.GEMINI_API_KEY == "a-real-key"

    with pytest.raises(RuntimeError):
        with eval_retrieval.no_embedding_key():
            raise RuntimeError("boom")
    assert settings.GEMINI_API_KEY == "a-real-key", "the key must survive an exception"


def test_the_context_variant_refuses_rather_than_guessing(settings):
    """S2 has not been built. A number here would describe a corpus that does not exist."""
    with pytest.raises(eval_retrieval.VariantUnavailable, match="D73"):
        eval_retrieval.retrieve("context", "a question", object(), limit=8)


# --- 4. The metrics cannot flatter the system ------------------------------


def _report(results, *, variant="bare"):
    return eval_retrieval.Report(
        variant=variant,
        k=8,
        corpus=eval_set.CorpusInfo(chunk_count=0, digest="", documents=()),
        model="",
        dimension=0,
        results=tuple(results),
    )


def _result(*, item_id="x", answerable=True, rank=1, distractor=(), lexical_only=False,
            found_by="lex1"):
    return eval_retrieval.QuestionResult(
        item_id=item_id,
        question="q?",
        asked_by="curated",
        answerable=answerable,
        first_hit_rank=rank,
        found_by=found_by if rank else "",
        recall=tuple((c, rank is not None and rank <= c) for c in eval_retrieval.CUTOFFS),
        reciprocal_rank=(1.0 / rank) if rank else 0.0,
        distractor_ranks=tuple(distractor),
        passages=(),
        retrieved=8,
        lexical_only=lexical_only,
        citations_accepted=0,
        citations_audited=0,
    )


def test_recall_and_mrr_ignore_the_refusal_items():
    """Metrics are over the answerable items only.

    Dividing by every question would let three refusals move recall by 9 points each in
    the direction that looks like a retrieval failure, which is the opposite of what a
    refusal item is asking.
    """
    aggregates = _report(
        [_result(rank=2), _result(item_id="r", answerable=False, rank=None)]
    ).aggregates()

    assert aggregates["answerable"] == 1
    assert aggregates["refusals"] == 1
    assert aggregates["recall"]["1"] == 0.0
    assert aggregates["recall"]["3"] == 1.0
    assert aggregates["mrr"] == 0.5


def test_only_a_grade_2_passage_is_the_answer():
    """Mutation: counting grade-0 or grade-1 entries as hits makes this test red.

    The retrieved order is distractor, supporting passage, answer — so a grader that reads
    "any expected entry is a hit" reports rank 1 for a question whose answer arrived third,
    and an over-retrieval (the straw/wood trap) is scored as a success.

    `audit` is off: this is the grading arithmetic, and it must not need a database.
    """
    item = EvalItem(
        id="straw",
        question="can I use straw mulch?",
        asked_by="probe",
        expected=(
            Expected(doc="saoso", locator="Appendix 2", grade=2),
            Expected(doc="saoso", locator="S4.4.4", grade=1),
            Expected(doc="saoso", locator="Appendix 2", grade=0),
        ),
    )
    result = eval_retrieval.score_item(
        item,
        {0: {1}, 1: {3}, 2: {2}},
        [_chunk(2), _chunk(3), _chunk(1)],
        k=8,
        lexical_only=False,
        audit=False,
    )

    assert result.first_hit_rank == 3, "a grade-0 or grade-1 passage was counted as the answer"
    assert result.distractor_ranks == (1,)
    assert [hit for cutoff, hit in result.recall if cutoff <= 1] == [False]


def test_a_run_where_the_vector_arm_never_ran_says_so(monkeypatch):
    """The most dangerous aggregate in the tool: a silent lexical-only 'bare' run.

    Reported as 0 recall, a vector arm that never executed is indistinguishable from a
    useless one, and the two call for opposite decisions (spike §2 Q2). So a run in which
    every question is lexical-only carries a note saying what it did *not* measure.
    """
    results = [_result(lexical_only=True), _result(item_id="y", lexical_only=True)]

    with monkeypatch.context() as patch:
        patch.setattr(eval_retrieval, "resolve", lambda items, standard_set: {
            item.id: {0: {1}} for item in items
        })
        patch.setattr(
            eval_retrieval,
            "retrieve",
            lambda *a, **k: SimpleNamespace(
                chunks=[_chunk(1)], lexical_only=True, warnings=()
            ),
        )
        patch.setattr(eval_retrieval, "corpus_info", lambda standard_set: eval_set.CorpusInfo(
            chunk_count=0, digest="", documents=()
        ))
        report = eval_retrieval.run(
            "bare",
            EvalSet(
                name="tiny",
                items=(
                    EvalItem(id="a", question="q1?", asked_by="curated",
                             expected=(Expected(doc="saoso", locator="S1", grade=2),)),
                    EvalItem(id="b", question="q2?", asked_by="curated",
                             expected=(Expected(doc="saoso", locator="S1", grade=2),)),
                ),
            ),
            object(),
            k=8,
            audit=False,
        )

    assert len(report.results) == 2  # the fakes were used, so the run is real to the code
    assert report.notes, "a 100%-lexical 'bare' run must announce that it measured no vectors"
    assert "vector arm never ran" in report.notes[0]


def test_the_json_output_carries_the_provenance_the_spike_demands(tmp_path):
    """Variant, corpus digest, model and date-free determinism: a re-checkable number."""
    report = _report([_result(rank=1)])
    payload = report.as_dict()

    assert payload["variant"] == "bare"
    assert set(payload["corpus"]) == {"chunk_count", "sha256", "documents"}
    assert payload["questions"][0]["first_hit_rank"] == 1
    assert "aggregates" in payload


def test_the_committed_set_is_where_the_runner_looks_by_default():
    """A set the runner does not read by default would be a set that never runs."""
    assert DEFAULT_SET.exists()
    assert DEFAULT_SET == Path(eval_set.__file__).resolve().parents[1] / (
        "knowledge/tests/data/retrieval_eval.json"
    )
