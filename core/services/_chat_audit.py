"""The audit: what the prompt promised, checked against what retrieval supplied.

Split out of `_chatbot.py` (CONTEXT_CUTS_PRD step 4). This module says what is wrong with
the model's citations; `_chatbot.answer_question` decides what to do about it, which is
always the same thing -- refuse the whole answer and escalate. Nothing here answers, and
nothing here is a policy: a problem is a fact, and the refusal is the contract's.

`looks_like_cost_question` is imported from `_chat_prompt` rather than copied: it is a
prompt-shaping decision (D78, the cost rule rides with the question), and the warning below
has to fire on exactly the answers that rule was rendered for. One predicate, one place, and
the arrow points this way -- the audit depends on the prompt, never the prompt on the audit.
"""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from core.services._chat_prompt import looks_like_cost_question
from core.services._chat_text import (
    _normalise_ref,
    _normalise_text,
    _resolve_sub_ref,
    _sub_ref_names,
    locator_of,
)
from core.services._chat_values import Citation
from knowledge.models import DocumentChunk
from knowledge.reading import reader_anchor_map
from knowledge.services import RetrievedChunk
from knowledge.table_context import column_label_for

#: The most citations one answer may carry, and so the most the audit will accept before
#: it stops looking. A model that returns more has not answered the question; it has
#: listed everything it read. `_chatbot` re-exports it: `eval_retrieval` and the tests
#: read it from there.
MAX_CITATIONS = 8


# --- Citation audit ---------------------------------------------------------


def _address_book(
    chunks: Sequence[RetrievedChunk],
) -> dict[str, dict[str, list[RetrievedChunk]]]:
    """`normalised locator -> {stored locator: the chunks that print it}`.

    Two levels, not one, because "the same locator on two chunks" is ordinary (a long
    section split across chunks) while "two different locators under one key" is an
    ambiguity, and a citation must not be resolved through a guess.
    """
    book: dict[str, dict[str, list[RetrievedChunk]]] = {}
    for chunk in chunks:
        locator = locator_of(chunk)
        if locator:
            book.setdefault(_normalise_ref(locator), {}).setdefault(
                locator, []
            ).append(chunk)
    return book


def _reader_anchors(chunks: Sequence[RetrievedChunk]) -> dict[int, str]:
    """`{chunk id: the fragment the reader renders for it}` for the supplied passages.

    In:  the retrieved chunks.
    Out: one anchor per chunk that is a stored row; empty for a chunk the database does
         not have (a test double), whose citation falls back to the section anchor.
    Side Effects: one query, plus one per distinct document — uniqueness is decided within the
         document's ordered chunk list, so the map can only be computed there, which is what
         the reader does (`knowledge.reading.reader_anchor_map`).

    Why this exists: eight SAOSO §1 chunks share the locator `S1`, so every citation of a
    definition linked to `#s1` — the top of a 21 000-character section — while the reader
    renders a content-derived anchor for the rest (`s1-genetically-modified-organism-gmo`).
    A citation chip that opens three thousand characters above its own quote is a link that
    technically works (F7).
    """
    ids = [chunk.chunk_id for chunk in chunks]
    if not ids:
        return {}
    rows = DocumentChunk.objects.filter(pk__in=ids).select_related("document")
    per_document: dict[int, dict[int, str]] = {}
    anchors: dict[int, str] = {}
    for row in rows:
        mapping = per_document.get(row.document_id)
        if mapping is None:
            mapping = reader_anchor_map(row.document)
            per_document[row.document_id] = mapping
        anchor = mapping.get(row.pk)
        if anchor:
            anchors[row.pk] = anchor
    return anchors


def audit_citations(    raw_citations: Sequence[dict],
    chunks: Sequence[RetrievedChunk],
    *,
    standard_set_id: int | None,
    document_codes: Mapping[str, str] | None = None,
) -> tuple[list[Citation], tuple[str, ...]]:
    """Validate the model's citations against the retrieved chunks.

    In:  `raw_citations` from the model; `chunks` â€” exactly what retrieval supplied;
         `standard_set_id` â€” the session's boundary, checked again defensively.
    Out: `(valid_citations, problems)`. `problems` is empty only when every citation
        survived. A caller must treat any problem as ungrounded.
    Fails: never â€” malformed input becomes a problem, not an exception.

    The rule that matters: a citation is accepted only if it can be checked. A
    reference the retriever never returned, a sub-reference absent from the chunk's
    offset map, or a quote that is not in the chunk is a hallucination, and the whole
    answer is refused rather than trimmed (one invented citation makes the rest
    untrustworthy).
    """
    if not raw_citations:
        return [], ("the model returned no citations",)

    # A chunk is addressable by exactly one locator. `standard_set_id` is checked
    # here, not only in retrieval, so a bug in a future retrieval implementation
    # cannot smuggle another corpus's text into an answer. The book is keyed on the
    # normalised spelling so a model that drops a `§` still lands on the chunk, but a
    # key that names two stored locators is ambiguous and is refused, never guessed.
    in_scope = [
        chunk
        for chunk in chunks
        if standard_set_id is None or chunk.standard_set_id == standard_set_id
    ]
    if len(in_scope) != len(chunks):
        return [], ("retrieval returned a chunk from outside the session's corpus",)

    book = _address_book(in_scope)
    anchors = _reader_anchors(in_scope)

    seen: set[tuple[str, str | None, str]] = set()
    citations: list[Citation] = []
    problems: list[str] = []

    for raw in raw_citations:
        if not isinstance(raw, dict):
            problems.append("a citation was not an object")
            continue

        ref = (raw.get("section_ref") or "").strip()
        quote = (raw.get("quote") or "").strip()
        sub_ref = (raw.get("sub_ref") or "").strip() or None

        if not ref:
            problems.append("a citation had no section_ref")
            continue
        if not quote:
            problems.append(f"{ref}: the citation had no quote")
            continue

        stored = book.get(_normalise_ref(ref), {})
        if not stored:
            problems.append(f"{ref}: not present in the retrieved set")
            continue
        if len(stored) > 1:
            problems.append(
                f"{ref}: ambiguous, more than one stored locator matches it "
                f"({', '.join(sorted(stored))})"
            )
            continue
        locator, candidates = next(iter(stored.items()))

        quote_key = _normalise_text(quote)
        matched = next(
            (chunk for chunk in candidates if quote_key in _normalise_text(chunk.text)),
            None,
        )
        if matched is None:
            problems.append(f"{ref}: the quote is not in the cited chunk")
            continue

        resolved_sub_ref = None
        if sub_ref is not None:
            resolved_sub_ref = _resolve_sub_ref(sub_ref, _sub_ref_names(matched))
            if resolved_sub_ref is None:
                problems.append(
                    f"{ref}: sub_ref {sub_ref!r} does not exist in the chunk"
                )
                continue

        identity = (locator, resolved_sub_ref, quote)
        if identity in seen:
            continue
        seen.add(identity)

        citations.append(
            Citation(
                section_ref=locator,
                quote=quote,
                chunk_id=matched.chunk_id,
                sub_ref=resolved_sub_ref,
                page=matched.page,
                anchor=matched.anchor,
                heading_path=matched.heading_path,
                document=(
                    matched.document_title
                    + (
                        f" v{matched.document_version}"
                        if matched.document_version
                        else ""
                    )
                ),
                document_code=(document_codes or {}).get(matched.document_source_file, ""),
                # The reader's own id for *this* chunk, not the section's: eight SAOSO §1
                # chunks share `S1`, so `reading_anchor` alone links every definition to
                # the top of the section (F7). Falls back to the section anchor when the
                # chunk is not a stored row (a test double, or a corpus that was
                # re-ingested under the answer).
                reading_anchor=anchors.get(matched.chunk_id)
                or reading_anchor(
                    matched.section_ref, matched.anchor, matched.heading_path
                ),
                row_label=(
                    matched.table.row_label if matched.table is not None else ""
                ),
                column_label=column_label_for(matched.table, quote),
            )
        )

        if len(citations) >= MAX_CITATIONS:
            break

    return citations, tuple(problems)


#: Words that turn a sentence into a verdict about organic status. Rule 4b forbids the
#: verdict; this list exists so a reviewer can find the sentences that still make one.
#: Measured need, 2026-10-27: two accepted answers told a visitor their fruit and their
#: seeds "would not be considered organic" on the strength of one sentence prohibiting the
#: *use* of GE seed, and the citation audit passed both — it checks quotes, not entailment.
OUTCOME_PHRASES = (
    "considered organic",
    "is organic",
    "are organic",
    "not organic",
    "become organic",
    "remains organic",
    "remain organic",
    "certified organic",
    "certified as organic",
)


def cost_question_warnings(question: str, answer: str) -> tuple[str, ...]:
    """A cost answer that names an amount and says nothing about what it leaves out.

    In:  the question as asked; the answer as shown.
    Out: one advisory string, or an empty tuple. **Never a reason to refuse** — the caller
         writes it to `ChatMessage.review_notes` and the log, and a person reads it, exactly
         as `outcome_claim_warnings` does.

    Why advisory: the requirement is that the answer says what cannot be totalled, and
    whether a sentence *means* that is an entailment question — a second model call and a
    threshold, which is the shape of check that turns grounded answers into refusals
    (G10's second finding: one run in five refused a correct answer, and the visitor could
    not tell it from "the corpus cannot answer this").

    Why a phrase list rather than the components: the components are what the passages say,
    not what the code knows, and the code must not become a second source for the fee
    schedule (§I: data encodes the standard). The list is the vocabulary of *limitation*, so
    it fires on the measured defect — an answer of two fees and no exclusion — and stays
    quiet on an answer that says the assessment is "charged separately". It is a tripwire,
    not a proof: a false negative is quiet, which is the right way for a tripwire to fail.
    """
    if not looks_like_cost_question(question) or not (answer or "").strip():
        return ()
    lowered = answer.lower()
    if any(phrase in lowered for phrase in COST_LIMIT_PHRASES):
        return ()
    return (
        "a cost answer states no limit — nothing says what the answer leaves out or what "
        f"cannot be totalled: {answer.strip()[:160]!r}",
    )


#: The vocabulary of a stated limit. Not a grammar of exclusions: one of these in the answer
#: is evidence that the model said, in some words, "and this is not the whole". Measured
#: 2026-11-01 against the two answers G10 recorded — the membership-only answer contains
#: none of them and is recorded; the complete answer's "charged separately" is in the list
#: and is not.
COST_LIMIT_PHRASES = (
    "separate",
    "not include",
    "doesn't include",
    "does not include",
    "exclud",
    "in addition to",
    "on top of",
    "not a total",
    "only applies",
    "depends on",
    "additional fee",
    "aside from",
    "beyond the",
    "plus the",
)


def outcome_claim_warnings(
    answer: str, citations: Sequence[Citation]
) -> tuple[str, ...]:
    """Sentences that pronounce an outcome their verified quotes do not state.

    In:  the answer as shown; the citations the audit accepted.
    Out: one advisory string per offending sentence; empty when every outcome sentence is
         echoed by a quote the audit verified. **Never a reason to refuse** — the strings
         go to `ChatMessage.review_notes` and the log, and a person reads them.

    Why advisory: an entailment test is a second model call and a threshold, and a check
    that turns grounded answers into refusals is the failure this feature exists to
    prevent (`CHAT_TRUTHFULNESS_PRD.md` §5.5).

    Why "an outcome", not "a claim unshared by any quote": the obvious cheap check — every
    answer sentence must share a content word with a quote — passes the exact answer that
    motivated this. *"The fruit would not be considered organic"* shares `organic` with
    *"Any GM seeds or seedlings are expressly forbidden in organic agriculture."* The
    verdict is the signal, not the vocabulary.
    """
    quoted = " ".join((citation.quote or "").lower() for citation in citations)
    supported = {phrase for phrase in OUTCOME_PHRASES if phrase in quoted}
    warnings: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", (answer or "").strip()):
        lowered = sentence.lower()
        unsupported = [
            phrase
            for phrase in OUTCOME_PHRASES
            if phrase in lowered and phrase not in supported
        ]
        if unsupported:
            warnings.append(
                f"states an outcome the quotes do not: {sentence.strip()!r}"
            )
    return tuple(warnings)
