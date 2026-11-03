"""The citation contract the model is given — D47, and the locator it copies.

`build_prompt` is what turns retrieved passages into the only thing the model sees.
These tests assert the prompt's own words, because the audit can only refuse a quote
the prompt did not permit — the contract has to be stated where the model reads it.

The second half is the locator: the string on its own line that a model actually
copies. It was asserted against the live `/ask/` on 2026-10-22, so these are the shapes
the production prompt produces, not a fixture's idea of them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.services._chatbot import SYSTEM_PROMPT, audit_citations, build_prompt
from core.tests.chat_helpers import retrieved_from_stored as _retrieved_from_stored

pytestmark = pytest.mark.django_db


# --- D47: the citation contract the model is given --------------------------
#
# Two live turns on 2026-10-20 were refused for citation-format reasons, not corpus
# reasons: one invented a `sub_ref` from a heading, the other joined two passages with
# an ellipsis. The decision (D47, option A) is to fix the contract the model is given,
# not to loosen the audit. These tests pin the contract text and the two passage shapes
# that make it actionable.

def _prompt_for(chunk, standard_set, question="What does the passage say?"):
    from core.services._chatbot import build_prompt

    return build_prompt(question, [_retrieved_from_stored(chunk, standard_set)], [])


def test_the_system_prompt_requires_a_character_for_character_quote():
    lowered = SYSTEM_PROMPT.lower()
    assert "character-for-character" in lowered
    assert "paraphrase" in lowered
    assert "ellipsis" in lowered
    assert "`...`" in SYSTEM_PROMPT


def test_the_system_prompt_forbids_a_sub_ref_that_is_not_listed():
    lowered = SYSTEM_PROMPT.lower()
    assert "omit `sub_ref`" in lowered
    assert "numbered sub-clauses available" in lowered
    assert "heading" in lowered, (
        "the live failure was a heading returned as a sub_ref; name it explicitly"
    )


def test_a_passage_with_no_sub_refs_tells_the_model_to_omit_them(
    chat_corpus, chat_standard_set
):
    prompt = _prompt_for(chat_corpus.fee, chat_standard_set)

    assert "Numbered sub-clauses available: none" in prompt
    assert "omit `sub_ref`" in prompt


def test_a_passage_with_a_stored_sub_ref_lists_it(chat_corpus, chat_standard_set):
    prompt = _prompt_for(chat_corpus.minutes, chat_standard_set)

    assert "Numbered sub-clauses available: 4.5(2)(c)" in prompt
    assert "none" not in prompt.split("Numbered sub-clauses available:")[1].split("\n")[0]


def test_the_system_prompt_forbids_a_stitched_quote():
    """A quote that joins two non-adjacent sentences is not checkable on paper.

    Observed live on 2026-10-20 on "can i use horse manure?": the model returned
    citations with `...` between separate passages. The audit refused the whole answer,
    correctly, but the prompt had not made the one-contiguous-excerpt rule explicit
    enough. This pins that rule and the escape hatch: one citation per excerpt.
    """
    lowered = SYSTEM_PROMPT.lower()
    assert "one contiguous excerpt" in lowered
    assert "single unbroken span" in lowered
    assert "separate citation" in lowered
    assert "stitch" in lowered


def test_the_quote_schema_describes_the_same_contract():
    """The schema is the second place the model reads the contract, so it must agree."""
    from core.services._chatbot import ANSWER_SCHEMA

    quote = ANSWER_SCHEMA["properties"]["citations"]["items"]["properties"]["quote"]
    description = quote["description"].lower()
    assert "contiguous" in description
    assert "no ellipses" in description
    assert "separate citation" in description


def test_the_landscape_fee_is_quotable_from_its_reviewed_row(chat_corpus, chat_standard_set):
    """The reader's question (`LANDSCAPE_TABLES_PRD` §11): what does it cost to join?

    The reviewed artefact carries the whole merged Fee cell in **one** row chunk, so the annual
    membership fee, the once-off customisation and the local fee are citable together — the
    condition that makes the amounts readable (D72.2: a fee is a cell, never a derived fact).
    The chunk is read from `knowledge/corpus/landscape.md`, the artefact the box now serves;
    a hand-built chunk would prove the audit, not the artefact.
    """
    from knowledge.corpus import load_document
    from knowledge.ingest import chunks_for_sections
    from knowledge.models import DocumentChunk

    art = Path(__file__).resolve().parents[2] / "knowledge" / "corpus" / "landscape.md"
    sections = list(load_document(art).sections)
    chunk = next(
        candidate
        for candidate in chunks_for_sections(sections)
        if "R500" in candidate.text and "R1 000" in candidate.text
    )
    row = DocumentChunk.objects.create(
        document=chat_corpus.document,
        section_ref=chunk.section_ref,
        heading_path=chunk.heading_path,
        page=chunk.page,
        anchor=chunk.anchor,
        text=chunk.text,
    )

    citations, problems = audit_citations(
        [
            {
                "section_ref": chunk.anchor,
                "quote": "Annual membership fee (paid by the PGS group to PGS SA): R500",
            }
        ],
        [_retrieved_from_stored(row, chat_standard_set)],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].page == 4
    assert citations[0].anchor == chunk.anchor


def test_a_reviewed_table_row_is_one_citable_passage(chat_corpus, chat_standard_set):
    """A row chunk joins two printed cells; a quote may cover the row.

    `knowledge/tables.py` reconstructs Appendix 2 as one chunk per printed row, so the
    substance and its condition are adjacent even though the page prints them in two
    columns. The audit is unchanged: it checks a whitespace-normalised substring of the
    chunk, and "substance + condition" is one. This pins that contract so a future
    chunker change cannot split the pair apart again.
    """
    from knowledge.models import DocumentChunk

    row = DocumentChunk.objects.create(
        document=chat_corpus.document,
        section_ref="Appendix 2",
        heading_path="Appendix 2 — Wood, bark, sawdust",
        page=76,
        text=(
            "Wood, bark, sawdust, wood shavings, wood ash, wood charcoal\n"
            "Only if not chemically treated"
        ),
    )

    citations, problems = audit_citations(
        [
            {
                "section_ref": "Appendix 2",
                "quote": (
                    "Wood, bark, sawdust, wood shavings, wood ash, wood charcoal "
                    "Only if not chemically treated"
                ),
            }
        ],
        [_retrieved_from_stored(row, chat_standard_set)],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].section_ref == "Appendix 2"
    assert citations[0].page == 76


# --- The locator a model actually copies (2026-10-22, live on /ask/) ---------
#
# The passage header used to read `[6] Appendix 2 — SAOSO Standard for Organic
# Production and Processing v2.1, page 77`: locator and document glued together with an
# em dash. Asked "can i use borax powder?" on the live site, the model answered
# correctly, quoted the Appendix 2 trace-elements row verbatim, and set `section_ref` to
# that whole header. The audit looked for a locator it had never been given, refused, and
# the visitor was told "I cannot find a definitive answer". `why_refused.py` on the box:
#
#     citations: 1 raw, 0 audited
#     AUDIT: REFUSED
#       ! Appendix 2 — SAOSO Standard … v2.1: not present in the retrieved set
#
# Two defences, and the cause is the first one: the prompt now prints `LOCATOR:` on its
# own line, and the audit treats everything from a dash on as decoration.


def test_a_passage_prints_its_locator_on_its_own_line(chat_corpus, chat_standard_set):
    """The locator must not share a line with the document it belongs to."""
    prompt = _prompt_for(chat_corpus.fee, chat_standard_set)
    header = next(line for line in prompt.splitlines() if line.startswith("LOCATOR:"))

    assert header.startswith("LOCATOR: "), header
    assert chat_corpus.fee.document.title not in header, (
        "the document title is metadata, and sharing the line invited the model to cite it"
    )
    assert f"Document: {chat_corpus.fee.document.title}" in prompt


def test_a_passage_number_is_not_part_of_its_address(chat_corpus, chat_standard_set):
    """No number may sit near the locator, because the model appends it to the address.

    Measured 2026-10-27, deterministically: `[6] LOCATOR: S2.3.1` → `S6.2.3.1`; `[2]
    LOCATOR: S1` → `S2` in 3 runs of 3; and `PASSAGE 5` on its own line with locator
    `S4.8` → `S5` in 2 runs of 3. Moving the number to its own line was not enough, so
    it is gone: 3 runs of 3 grounded afterwards, 7/7 citations audited. Delete this
    test and the numbering comes back as a harmless label — it is not harmless.
    """
    prompt = _prompt_for(chat_corpus.fee, chat_standard_set)

    assert "LOCATOR: " in prompt
    assert "PASSAGE" not in prompt, "a passage number is printed where the model reads it"
    body = [line for line in prompt.split("Passages:", 1)[1].splitlines() if line.strip()]
    assert body[0].startswith("LOCATOR: "), body[0]
    assert "not part of any address" in SYSTEM_PROMPT, (
        "the rule the layout depends on is not stated to the model"
    )


def test_the_system_prompt_forbids_deciding_an_outcome():
    """Rule 4b (D-3, 2026-10-27): state the rule, do not pronounce on organic status.

    Two accepted answers told a visitor their fruit and their seeds "would not be
    considered organic" on the strength of one clause prohibiting the *use* of GE seed.
    The audit cannot see it — it checks quotes, not entailment — and the OPP reserves
    certification decision-making to the administrator and the committee.
    """
    lowered = SYSTEM_PROMPT.lower()
    assert "4b. do not decide an outcome" in lowered
    assert "do not state the outcome" in lowered
    assert "belongs to the certification body" in lowered
    assert 'leading "no" or "yes"' in lowered, (
        "a bare verdict word is how the rule was dodged: measured 2 runs of 2 before this "
        "clause, 3 runs of 3 opened with the rule after it"
    )


def test_the_system_prompt_forbids_an_item_marker_as_a_sub_ref():
    """The Appendix 1 refusal: `2.2.` printed in the text is not a stored sub-clause.

    Six recorded refusals are this shape (`2.2`, `2.3`, `3`, `4`, `5`, `6`), all
    Appendix 1, all on a chunk whose stored sub-clause map is empty — so a correct
    answer was withheld for an address the audit could not resolve.
    """
    lowered = SYSTEM_PROMPT.lower()
    assert "item marker" in lowered
    assert "not one of the passage's stored sub-clauses" in lowered


def test_the_system_prompt_says_which_value_is_the_address():
    lowered = SYSTEM_PROMPT.lower()
    assert "locator:" in lowered
    assert "nothing else" in lowered
    assert "never the document title" in lowered


def test_a_locator_decorated_with_the_document_label_still_audits(
    chat_corpus, chat_standard_set
):
    """The live borax citation, verbatim: it must be accepted, not refused."""
    chunk = chat_corpus.fee
    decorated = f"{chunk.section_ref} — {chunk.document.title} v{chunk.document.version}"

    citations, problems = audit_citations(
        [{"section_ref": decorated, "quote": chunk.text[:60].strip()}],
        [_retrieved_from_stored(chunk, chat_standard_set)],
        standard_set_id=chat_standard_set.pk,
    )

    assert problems == ()
    assert citations[0].section_ref == chunk.section_ref, (
        "the citation must resolve to the stored locator, not echo the decoration"
    )


def test_a_decorated_locator_that_is_ambiguous_still_refuses(chat_corpus, chat_standard_set):
    """Stripping the label widens format tolerance, never identity.

    `4.2` and `§4.2` are the same address spelled two ways, so the key unites them — and
    the audit refuses to resolve a citation through a key that two stored locators
    produce. The decoration strip must not reopen that: the live failure must be fixed
    for a bare locator without ever making an ambiguous one acceptable.
    """
    from knowledge.models import DocumentChunk

    plain = DocumentChunk.objects.create(
        document=chat_corpus.document,
        section_ref="4.2",
        heading_path="4.2 Fees",
        page=30,
        text="Fees are payable in February each year.",
    )
    signed = DocumentChunk.objects.create(
        document=chat_corpus.document,
        section_ref="§4.2",
        heading_path="§4.2 Fees (second printing)",
        page=31,
        text="Fees are payable in February each year.",
    )

    citations, problems = audit_citations(
        [
            {
                "section_ref": f"{plain.section_ref} — {plain.document.title}",
                "quote": plain.text,
            }
        ],
        [
            _retrieved_from_stored(plain, chat_standard_set),
            _retrieved_from_stored(signed, chat_standard_set),
        ],
        standard_set_id=chat_standard_set.pk,
    )

    assert citations == []
    assert any("ambiguous" in problem for problem in problems), problems


