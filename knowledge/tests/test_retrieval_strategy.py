"""`search_terms` — the retrieval strategy: the key, the seats, the rare-term bet.

`knowledge/retrieval.py` is the strategy module: it reads rarity, aliases and seats off
the corpus and returns a `RetrievalResult`. The tests here are the behaviour of that
choice — which word becomes the lexical key, how many seats the semantic arm keeps, and
what happens when the question names nothing in the corpus.

They were the second half of `test_retrieval.py` until that file crossed the 30 KB cap.
`scripts/fast.sh --critical` keeps naming `test_retrieval.py` for the retrieval floors,
which stay there; these assert the strategy above them.
"""

from __future__ import annotations

import pytest

from knowledge.models import DocumentChunk
from knowledge.retrieval import search_terms
from knowledge.services import FILLER_TERMS, lexical_key, search
from knowledge.tests.retrieval_fixtures import (  # noqa: F401 - pytest discovers fixtures by name
    FakeProvider,
    make_chunk,
    no_live_embeddings,
    opp_ingested,
    saoso_ingested,
    saoso_set,
    two_sets,
    vec,
)

pytestmark = pytest.mark.django_db


# --- The rare term is a lexical key, the OR query is the semantic question ---
#
# Measured 2026-10-20, after the corpus was embedded: `search_terms` used to run the
# vector arm on the rare word as well as on the OR query. A single word is a lexical
# key, not a semantic question — embedding it retrieved semantically adjacent passages
# (S5, Appendix 6b) that pushed SAOSO Appendix 2 out of the top 8, and the manure
# question refused again despite a good corpus. The fix is structural: the rare-term
# arm stays lexical; the vector arm runs once, on the broader OR query. It also halves
# the query embeddings per question from two to one.


def test_the_rare_term_arm_can_be_kept_lexical(two_sets):
    first, second, in_set, out_of_set = two_sets
    DocumentChunk.objects.filter(pk=in_set.pk).update(embedding=vec(1.0))
    provider = FakeProvider()

    result = search(
        "alpha", standard_set=first, provider=provider, use_vector=False
    )

    assert result.lexical_only is True
    assert provider.calls == 0, "a lexical-only arm must not spend an embedding call"
    assert [chunk.chunk_id for chunk in result.chunks] == [in_set.pk]


def test_search_terms_embeds_the_question_when_it_has_one(two_sets):
    """The semantic query is the visitor's sentence, not the OR-joined token string.

    Measured 2026-10-21 against the shipped corpus: "can I use cardboard from my
    neighbours?" embedded as a sentence puts SAOSO 4.4.4 in the top 8; embedded as
    `use OR cardboard OR neighbours` it retrieves labelling, construction materials and
    buffers instead. A token string is a lexical query; a question is a semantic one.

    One embedding per question either way — the cost does not change, only the text.
    """
    first, second, in_set, out_of_set = two_sets
    DocumentChunk.objects.filter(pk=in_set.pk).update(embedding=vec(1.0))
    provider = FakeProvider()

    result = search_terms(
        ["alpha", "traceability"],
        standard_set=first,
        provider=provider,
        question="what does alpha traceability mean?",
    )

    assert result.lexical_only is False, "the vector arm did not run, so this proves nothing"
    assert provider.calls == 1
    assert provider.queries == ["what does alpha traceability mean?"]
    assert in_set.pk in [chunk.chunk_id for chunk in result.chunks]


def test_the_semantic_arm_is_not_crowded_out_by_a_full_lexical_limit(two_sets):
    """A full lexical result set used to leave the vector arm with nothing to add.

    Measured 2026-10-21: with the caller's limit reached by the rare-term arm, the merged
    result was identical to a lexical-only result — the "hybrid" retrieval the page
    describes never ran. `SEMANTIC_SEATS` reserves the semantic arm's share, and this
    test makes the lexical arm deliberately fill the budget first.
    """
    first, second, in_set, out_of_set = two_sets
    semantic = make_chunk(
        in_set.document,
        ref="S4.4.4",
        text="Material applied to the land or crop shall be in accordance with Appendix 2",
        embedding=vec(0.0, 0.0, 1.0),
    )
    for index in range(6):
        make_chunk(
            in_set.document,
            ref=f"S9.{index}",
            text=f"alpha requirement number {index}",
        )
    provider = FakeProvider()

    result = search_terms(
        ["alpha"],
        question="what does gamma require?",
        standard_set=first,
        provider=provider,
        limit=4,
    )

    ids = [chunk.chunk_id for chunk in result.chunks]
    assert len(ids) == 4
    assert semantic.pk in ids, "the lexical arm filled every seat and the vector arm was ignored"


def test_a_seat_is_filled_from_the_semantic_arms_own_ranking(two_sets):
    """The reservation exists for the vector arm, so the vector arm's order must fill it.

    Measured 2026-11-02 on the dev corpus (*"what is the yearly cost of membership"*):
    the OPP's fee-band row is the semantic arm's 4th chunk and appears in **no** lexical
    ranking, so its fused score is a single `1/(60+4)` and every chunk the lexical arm
    also matched outranks it. `search_terms` asked the fused arm for `limit` chunks, so
    the band sat outside `fused[:limit]` — which was all the seat could see — and a
    chunk the reservation was created for could not take a seat however well the vector
    arm ranked it. Filling the seats in fused order is the same defect one step later:
    the lexical arm, which the seat exists to bypass, still chooses which semantic
    chunks get in.

    This chunk is the semantic arm's best and is in no lexical ranking. It must be
    seated; today it is unreachable.
    """
    first, _second, in_set, _out = two_sets
    document = in_set.document
    for index in range(4):
        make_chunk(
            document,
            ref=f"S9.{index}",
            text=f"alpha requirement number {index}",
            embedding=vec(0.0, 1.0),
        )
    seat_worthy = make_chunk(
        document,
        ref="§2.3",
        text="R 250,001 – R 500,000 / 2,500 / 2,000",
        embedding=vec(0.0, 0.0, 1.0),
    )

    result = search_terms(
        ["alpha"],
        question="what does gamma require?",
        standard_set=first,
        provider=FakeProvider(),
        limit=4,
    )

    ids = [chunk.chunk_id for chunk in result.chunks]
    assert result.lexical_only is False, "this test would pass vacuously without the vector arm"
    assert len(ids) == 4
    assert seat_worthy.pk in ids, (
        "the semantic arm's best chunk never reached a seat: "
        f"{[chunk.section_ref for chunk in result.chunks]}"
    )


def test_a_heading_cannot_consume_a_semantic_seat(two_sets):
    """A heading is not the clause a seat is reserved for.

    Measured 2026-11-02: the OPP's part heading *II. Membership fees, farm assessment
    fees, licensing fees* is 57 characters with no body under it, and it takes the
    semantic arm's **rank 1** for any fee question because its text names every fee the
    document charges. Section headings of a standard behave the same way. They are real
    corpus text and stay retrievable — but a reserved seat exists to bring a clause, and
    spending it on a phrase that states no rule is how the fourth-best clause misses.

    Three passages and one heading, three seats: all three passages must be seated.
    """
    first, _second, in_set, _out = two_sets
    document = in_set.document
    for index in range(2):
        make_chunk(
            document,
            ref=f"S9.{index}",
            text=f"alpha requirement number {index}",
            embedding=vec(0.0, 1.0),
        )
    heading = make_chunk(
        document,
        ref="§II",
        text="II. Membership fees, farm assessment fees, licensing fees",
        heading_path="II. Membership fees, farm assessment fees, licensing fees",
        embedding=vec(0.0, 0.0, 1.0),
    )
    passages = [
        make_chunk(
            document,
            ref=f"§2.{index}",
            text=f"The fee for band {index} is payable on assessment.",
            embedding=vec(0.0, 0.02 * index, 1.0),
        )
        for index in range(1, 4)
    ]

    result = search_terms(
        ["alpha"],
        question="what does gamma require?",
        standard_set=first,
        provider=FakeProvider(),
        limit=4,
    )

    ids = [chunk.chunk_id for chunk in result.chunks]
    assert len(ids) == 4
    assert all(p.pk in ids for p in passages), (
        "a heading consumed the seat the third clause needed: "
        f"{[chunk.section_ref for chunk in result.chunks]}"
    )


def test_without_a_question_the_or_query_is_still_the_semantic_query(two_sets):
    """A caller that has only terms gets the old behaviour, unchanged.

    `search_terms` is a library function; the chat is not its only caller, and a caller
    that never had the visitor's sentence must not lose the OR fallback.
    """
    first, second, in_set, out_of_set = two_sets
    DocumentChunk.objects.filter(pk=in_set.pk).update(embedding=vec(1.0))
    provider = FakeProvider()

    result = search_terms(
        ["alpha", "traceability"], standard_set=first, provider=provider
    )

    assert result.lexical_only is False
    assert provider.calls == 1
    assert provider.queries == ["alpha OR traceability"]
    assert in_set.pk in [chunk.chunk_id for chunk in result.chunks]


def test_a_question_about_an_unknown_material_gives_the_semantic_arm_the_budget(two_sets):
    """When the subject is a word the corpus lacks, the lexical arms search a proxy.

    "can I use cardboard from my neighbours?" -- `cardboard` has document frequency 0,
    so the rarest *known* word is `neighbours`, and searching it returned the child-
    labour clause while the inputs clause never arrived. The lexical match is kept as a
    two-chunk hedge (it is the only retrieval there is when no embedding key is set),
    but it must not fill the budget: the question's meaning gets the remaining seats.
    """
    first, second, in_set, out_of_set = two_sets
    decoy = make_chunk(
        in_set.document,
        ref="S23.9",
        text="Neither the operator nor their neighbours shall use child labour.",
    )
    DocumentChunk.objects.filter(pk=in_set.pk).update(embedding=vec(0.0, 0.0, 0.0, 1.0))
    provider = FakeProvider()
    question = "can I use cardboard from my delta neighbours?"

    result = search_terms(
        ["use", "cardboard", "delta", "neighbours"],
        question=question,
        standard_set=first,
        provider=provider,
        limit=3,
    )

    assert provider.queries == [question], "the OR string was embedded, not the question"
    assert result.query == question
    ids = [chunk.chunk_id for chunk in result.chunks]
    assert decoy.pk in ids, "the hedge chunk was expected; this test would pass vacuously"
    assert in_set.pk in ids, "the proxy word crowded the semantic result out of the budget"
    assert "cardboard" in " ".join(result.warnings)


# --- The lexical key is the rarest word that names the *subject* ------------#
# Both defects below were measured on the live surface on 2026-10-27
# (`CHAT_TRUTHFULNESS_PRD.md` F1): a verb outranked the topic, and a question with one
# out-of-vocabulary word lost the page that answers it while every known word was
# already in hand.


def test_a_verb_is_never_the_lexical_key(two_sets):
    """`count` occurs in one chunk, `biodiversity` in two — the verb still loses.

    Document frequency is a proxy for topicality, and it inverts on a verb: "does that
    count as GM?" made `count` (df 1) the key, and the arm returned §2.1.4 biodiversity
    reserve for a question about a definition. The tie-break is not the assertion; the
    *filler* is. Delete `FILLER_TERMS` from `lexical_key` and this test goes red.
    """
    first, _second, in_set, _out = two_sets
    document = in_set.document
    make_chunk(document, ref="S99.1", text="The operator must count the animals.")
    make_chunk(document, ref="S99.2", text="Biodiversity is maintained on the farm.")
    make_chunk(document, ref="S99.3", text="A biodiversity reserve protects habitat.")

    result = search_terms(["biodiversity", "count"], standard_set=first, limit=3)

    assert result.key == "biodiversity", (
        "a filler verb was chosen as the lexical key: " + repr(result.key)
    )
    assert "count" in FILLER_TERMS


def test_lexical_key_keeps_a_filler_only_question_searchable(two_sets):
    """`subject or known`: a question made only of filler words still searches one."""
    first, _second, in_set, _out = two_sets
    make_chunk(in_set.document, ref="S99.4", text="The operator must use approved inputs.")

    assert lexical_key(["use"], {"use": 1}) == "use"
    assert lexical_key(["cardboard"], {"cardboard": 0}) == "", (
        "a word the corpus does not contain is not a key"
    )


def test_an_unknown_word_hedges_two_bets(two_sets):
    """The hedge is two seats and two bets, not the rarest word twice.

    The question's subject is `genetically modified organism`; `saving` is absent from the
    corpus, which used to reduce the whole lexical arm to the rarest known word — `count`
    — and the page that defines the term never reached the model. The hedge must search
    the subject's words as well, or the refusal blames the documents for a retrieval bug.

    The corpus is shaped like the real one on purpose: the rarest subject word (`gm`) is
    in a *different* chunk from the words that carry the question. A key that lands on the
    right page anyway would let this test pass with the second bet removed.
    """
    first, _second, in_set, _out = two_sets
    document = in_set.document
    proxy = make_chunk(
        document,
        ref="general-principles",
        text="Any GM seeds or seedlings are expressly forbidden in organic agriculture.",
    )
    prohibition = make_chunk(
        document,
        ref="S2.3.1",
        text="The deliberate use of genetically modified material is prohibited.",
    )
    definitions = make_chunk(
        document,
        ref="S1",
        text=(
            "Genetically modified organism: an organism produced through techniques in "
            "which the genetic material has been altered by genetic engineering."
        ),
    )
    make_chunk(
        document,
        ref="S2.1.4",
        text="The farm must count plants inside a biodiversity reserve.",
    )
    question = (
        "what is the definition of a genetically modified organism? does saving count?"
    )

    result = search_terms(
        ["definition", "genetically", "modified", "organism", "saving", "gm", "count"],
        question=question,
        standard_set=first,
        provider=FakeProvider(),
        limit=4,
    )

    ids = [chunk.chunk_id for chunk in result.chunks]
    assert result.key == "gm", (
        "the rarest subject word is the first bet: " + repr(result.key)
    )
    assert proxy.pk in ids, "the proxy bet was not searched; this test would pass vacuously"
    assert definitions.pk in ids, (
        "the second bet was not searched: only the proxy word's chunks arrived "
        f"({[chunk.section_ref for chunk in result.chunks]})"
    )


def test_the_cost_question_reaches_the_membership_fee(opp_ingested, saoso_set):
    """G3: the question says `cost`, the OPP says `Membership Fees`, and both must answer.

    Measured 2026-10-27 on the shipped corpus: `search("cost")` returns §2.3, §2.4,
    pgs-sa, §2.2, §2.5 and never §2.1; `search("fee")` puts §2.1 at rank 2. The alias arm
    searches the second alone, because an OR of the two loses it again.
    """
    result = search_terms(
        ["yearly", "cost", "certified", "including", "farm", "visit"],
        standard_set=saoso_set,
        limit=8,
    )

    refs = [chunk.section_ref for chunk in result.chunks]
    assert "§2.1" in refs, f"the membership fee never arrived: {refs}"
    assert "§2.3" in refs, "the alias arm displaced the answer instead of the tail"


def test_an_alias_word_finds_the_clause_the_question_word_cannot(two_sets):
    """The alias arm exists for a clause no word in the question reaches.

    The OR-vs-alone half of this finding (`cost OR fee` loses §2.1, `fee` alone finds it
    at rank 2) is measured on the real corpus in `knowledge/aliases.py`, and cannot be
    shown here: the table holds one alias per question word, so OR-ing it is the same
    query. What this test proves is the arm itself — remove `ALIASES` and it goes red.
    """
    first, _second, in_set, _out = two_sets
    document = in_set.document
    make_chunk(document, ref="§2.3", text="The assessment cost is set on a sliding scale.")
    make_chunk(document, ref="§2.4", text="A cost per visit is payable by the participant.")
    make_chunk(document, ref="§2.5", text="Another cost for the use of a seal.")
    membership = make_chunk(document, ref="§2.1", text="Membership fees: R100 a year.")

    result = search_terms(["cost"], standard_set=first, limit=4)

    ids = [chunk.chunk_id for chunk in result.chunks]
    assert membership.pk in ids, (
        "the alias word was not searched: "
        f"{[chunk.section_ref for chunk in result.chunks]}"
    )


def test_a_question_with_no_alias_costs_nothing(two_sets):
    """An unrelated question must not gain the fee section through the alias arm."""
    first, _second, in_set, _out = two_sets
    make_chunk(in_set.document, ref="§2.1", text="Membership fees: R100 a year.")

    result = search_terms(["traceability"], standard_set=first, limit=4)

    refs = [chunk.section_ref for chunk in result.chunks]
    assert "§2.1" not in refs, refs


def test_the_definition_question_reaches_the_definitions_section(saoso_ingested, saoso_set):
    """The real extracted pages, the real question, the page that answers it (2026-10-27).

    `S1` is SAOSO's own definitions section; it holds both «Genetically Modified
    Organism (GMO)» and «Genetic Engineering», the second of which excludes natural
    hybridisation — i.e. the answer to "does selective seed saving count?".

    **This pins the old contract's disappearance, not each half of the fix.** The
    committed pages and the deployed corpus are not identical (here `gm` has document
    frequency 0, on the box 1), so with the filler guard removed the key is `count` and
    with the second bet removed the fixture corpus happens to recover the page anyway.
    Proved red against the code before this slice; the halves are proved separately by
    `test_a_verb_is_never_the_lexical_key` and
    `test_an_unknown_word_hedges_two_bets`.
    """
    result = search_terms(
        ["definition", "genetically", "modified", "selective", "seed", "saving", "count", "gm"],
        question=(
            "what is the definition of genetically modified? does selective seed saving "
            "count as GM?"
        ),
        standard_set=saoso_set,
        limit=8,
    )

    refs = [chunk.section_ref for chunk in result.chunks]
    assert "S1" in refs, f"the definitions section never arrived: {refs}"


