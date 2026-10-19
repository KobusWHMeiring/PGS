"""Task B4 — the chunker.

D15's rule is the whole design: **chunks stay section-level.** Sub-item boundaries
never split a chunk, they produce offsets into it. Splitting at every enumerated item
would fragment the OPP into hundreds of context-poor chunks and degrade retrieval
(the task's own acceptance: a chunk count in the low tens, not the low hundreds).

The properties asserted here are the ones a downstream failure would hide:

- a short section is exactly one chunk, carrying every `sub_ref` unchanged (the common
  case — if this were broken, retrieval would look fine and citations would be lost);
- a long section splits on **paragraph** boundaries, so a chunk is never a sentence
  fragment;
- every `sub_ref` lands in **exactly one** chunk, with offsets re-based to that chunk,
  and every slice still resolves to real text. Two chunks claiming the same `sub_ref`
  would make a citation ambiguous; a stale offset would make it wrong.
- `validate_sub_refs` (B1's contract, and the DB's) accepts every chunk produced.

The OPP fixtures are the input for the load-bearing cases, because §4.5 is the block
with nested items, a missing item 3, and a list split across a page break.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge.chunking import (
    CHARS_PER_TOKEN,
    OVERLAP_TOKENS,
    TARGET_TOKENS,
    Chunk,
    chunk_section,
    chunk_sections,
    estimate_tokens,
)
from knowledge.models import validate_sub_refs
from knowledge.sections import ParsedSection, SubRef
from knowledge.sections.opp import OppParser
from knowledge.sections.saoso import SaosoParser

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")


def opp_sections():
    return OppParser().parse(fixture("opp_4_5"))


def paragraph(count: int = 1) -> str:
    return "\n".join(
        f"Paragraph {index}: " + ("traceability of organic produce " * 12).strip()
        for index in range(count)
    )


# --- The token estimate ------------------------------------------------------


def test_token_estimate_is_chars_over_four():
    """No tokeniser in the request path — SPEC §4.5's chunking section.

    A tokeniser here would put a model dependency inside ingestion and make the
    chunker's output non-deterministic; a four-character rule is wrong by a known
    margin and cheap to reason about.
    """
    assert CHARS_PER_TOKEN == 4
    assert estimate_tokens("a" * 400) == 100
    assert estimate_tokens("") == 0


def test_the_target_is_the_documented_eight_hundred_tokens():
    assert TARGET_TOKENS == 800
    assert 0 < OVERLAP_TOKENS < TARGET_TOKENS


# --- A short section is one chunk -------------------------------------------


def test_short_section_is_exactly_one_chunk():
    section = ParsedSection(
        section_ref="§4.1",
        text=paragraph(3),
        sub_refs=(SubRef(ref="4.1(1)", start=0, end=12),),
    )
    chunks = chunk_section(section)
    assert len(chunks) == 1
    assert chunks[0].text == section.text
    assert chunks[0].token_count == estimate_tokens(section.text)


def test_short_section_keeps_every_sub_ref_unchanged():
    section = ParsedSection(
        section_ref="§4.2",
        text="one two three four five six seven eight nine ten",
        sub_refs=(
            SubRef(ref="4.2(1)", start=0, end=3),
            SubRef(ref="4.2(2)", start=4, end=7),
        ),
    )
    chunks = chunk_section(section)
    assert [ref.ref for ref in chunks[0].sub_refs] == ["4.2(1)", "4.2(2)"]
    assert [(ref.start, ref.end) for ref in chunks[0].sub_refs] == [(0, 3), (4, 7)]


def test_chunk_carries_the_section_identity():
    """B6 creates `DocumentChunk` rows straight from these fields."""
    section = ParsedSection(
        section_ref="§4.5",
        text="Non-compliance and discipline.",
        heading_path="4.5 Non-compliance",
        page=6,
        anchor="",
    )
    kwargs = chunk_section(section)[0].as_chunk_kwargs()
    assert kwargs["section_ref"] == "§4.5"
    assert kwargs["heading_path"] == "4.5 Non-compliance"
    assert kwargs["page"] == 6


# --- A long section splits on paragraph boundaries ---------------------------


def test_long_section_splits_into_several_chunks():
    section = ParsedSection(
        section_ref="§4.5",
        text="\n\n".join(paragraph(1) for _ in range(40)),
    )
    chunks = chunk_section(section)
    assert len(chunks) > 1
    assert all(chunk.token_count <= TARGET_TOKENS + OVERLAP_TOKENS for chunk in chunks)


def test_split_happens_between_paragraphs_not_inside_them():
    """A chunk boundary mid-paragraph is a citation that starts mid-sentence."""
    body = "\n\n".join(f"PARAGRAPH-{index} " + "word " * 150 for index in range(12))
    section = ParsedSection(section_ref="§4.5", text=body)
    for chunk in chunk_section(section)[:-1]:
        # Overlap means a chunk may end inside a paragraph only where the next one
        # resumes; the assertion that matters is that chunk starts are paragraph
        # starts, which keeps every chunk's beginning quotable.
        assert chunk.text.lstrip().startswith("PARAGRAPH-"), chunk.text[:40]


def test_a_single_paragraph_larger_than_the_target_is_split_at_lines():
    """§4.5's opening paragraph is ~200 words on its own; it must still be chunked."""
    one_paragraph = "\n".join("word " * 10 for _ in range(200))
    section = ParsedSection(section_ref="§4.5", text=one_paragraph)
    chunks = chunk_section(section)
    assert len(chunks) > 1
    limit = (TARGET_TOKENS + OVERLAP_TOKENS) * CHARS_PER_TOKEN + 64
    assert all(len(chunk.text) <= limit for chunk in chunks)


def test_chunks_never_bridge_two_sections():
    sections = [
        ParsedSection(section_ref="§4.1", text=paragraph(2)),
        ParsedSection(section_ref="§4.2", text=paragraph(2)),
    ]
    for chunk in chunk_sections(sections):
        assert chunk.section_ref in {"§4.1", "§4.2"}
        source = next(section for section in sections if section.section_ref == chunk.section_ref)
        assert chunk.text in source.text


# --- sub_refs: exactly one chunk each, offsets re-based ----------------------


def test_every_sub_ref_lands_in_exactly_one_chunk():
    for section in opp_sections():
        if not section.sub_refs:
            continue
        seen = [
            ref.ref for chunk in chunk_section(section) for ref in chunk.sub_refs
        ]
        assert len(seen) == len(set(seen)), f"{section.section_ref} duplicated a sub_ref"
        assert set(seen) == {ref.ref for ref in section.sub_refs}


def test_real_opp_section_keeps_all_of_its_sub_refs():
    """The concrete case: §4.5's 4.5(1), 4.5(2)(c), 4.5(4), 4.5(5) … all survive."""
    sections = {section.section_ref: section for section in opp_sections()}
    section = sections["§4.5"]
    kept = {ref.ref for chunk in chunk_section(section) for ref in chunk.sub_refs}
    assert {"4.5(1)", "4.5(2)(c)", "4.5(4)", "4.5(5)"} <= kept
    assert kept == {ref.ref for ref in section.sub_refs}


def test_sub_ref_offsets_are_rebased_to_their_chunk():
    """Offsets are into *this chunk's* text (D15), not into the parent section."""
    section = opp_sections()[2]  # §4.5, the long one
    chunks = chunk_section(section)
    for chunk in chunks:
        for ref in chunk.sub_refs:
            assert 0 <= ref.start < ref.end <= len(chunk.text)
            assert chunk.text[ref.start : ref.end].strip(), f"{ref.ref} slices nothing"


def test_every_chunk_passes_the_database_contract():
    """B1's `validate_sub_refs` is the same check the column will enforce."""
    for name in ("opp_4_1", "opp_4_2", "opp_4_5", "opp_seals"):
        for section in OppParser().parse(fixture(name)):
            for chunk in chunk_section(section):
                validate_sub_refs([ref.as_dict() for ref in chunk.sub_refs], chunk.text)


def test_sub_refs_are_never_duplicated_across_chunks_of_a_long_section():
    section = opp_sections()[2]
    refs = [ref.ref for chunk in chunk_section(section) for ref in chunk.sub_refs]
    assert len(refs) == len(set(refs))


def _depth(ref: str) -> int:
    return ref.count("(")


def _parent(ref: str) -> str:
    return ref.split("(", 1)[0]


def test_sibling_sub_refs_do_not_overlap():
    """The plan's "sub_refs never overlap", asserted where it can hold.

    Nested refs nest by design — `4.5(2)` contains `(a)`, `(b)`, `(c)`, and a citation
    for `4.5(2)` that stopped at its own sub-items would quote a heading and nothing
    else. What must never happen is two *siblings* covering the same characters: a
    reader quoting `4.5(2)(a)` would get part of `(b)`.
    """
    for name in ("opp_4_1", "opp_4_2", "opp_4_5", "opp_seals"):
        for section in OppParser().parse(fixture(name)):
            spans = [(ref.ref, ref.start, ref.end) for ref in section.sub_refs]
            for index, (ref_a, start_a, end_a) in enumerate(spans):
                for ref_b, start_b, end_b in spans[index + 1 :]:
                    if _parent(ref_a) == _parent(ref_b) and _depth(ref_a) == _depth(ref_b):
                        assert end_a <= start_b or end_b <= start_a, (
                            f"{ref_a} and {ref_b} overlap in {section.section_ref}"
                        )


def test_the_chunks_cover_the_whole_section_text():
    """No gap between chunks: a dropped span is text that cannot be retrieved.

    With overlap, chunk starts are inside the previous chunk; the invariant that can
    fail is a *gap*, so the assertion is one-sided.
    """
    for section in opp_sections():
        chunks = chunk_section(section)
        assert chunks[0].source_start == 0
        assert chunks[-1].source_end == len(section.text)
        for earlier, later in zip(chunks, chunks[1:]):
            assert later.source_start <= earlier.source_end


def test_saoso_sections_chunk_without_sub_refs():
    """SAOSO emits no `sub_refs` in B2; the chunker must accept that."""
    chunks = chunk_sections(SaosoParser().parse(fixture("saoso_part_b")))
    assert chunks
    assert all(chunk.sub_refs == () for chunk in chunks)
    assert all(chunk.section_ref for chunk in chunks)


# --- Overlap, and the acceptance number -------------------------------------


def test_consecutive_chunks_overlap_by_a_bounded_amount():
    """Overlap exists so a sentence quoted at a boundary is not cut in half.

    Measured through the source offsets rather than by string containment: an
    assertion built on `or True` (the first draft) would have passed with overlap set
    to zero, which is the failure this test exists to catch.
    """
    section = ParsedSection(
        section_ref="§4.5",
        text="\n\n".join(paragraph(1) for _ in range(40)),
    )
    chunks = chunk_section(section)
    for earlier, later in zip(chunks, chunks[1:]):
        overlap_chars = earlier.source_end - later.source_start
        assert 0 < overlap_chars <= OVERLAP_TOKENS * CHARS_PER_TOKEN + 8


def test_chunk_overlap_does_not_swallow_a_chunk():
    section = ParsedSection(
        section_ref="§4.5",
        text="\n\n".join(paragraph(1) for _ in range(40)),
    )
    chunks = chunk_section(section)
    assert all(chunk.token_count > OVERLAP_TOKENS for chunk in chunks[1:])


def test_opp_chunk_count_is_in_the_low_tens():
    """B4's acceptance test: hundreds would mean sub-items are being split.

    The floor is meaningful too — one chunk per section is the minimum, so a count
    below it means a section was dropped rather than merged.
    """
    sections = []
    for name in ("opp_4_1", "opp_4_2", "opp_4_5", "opp_seals"):
        sections.extend(OppParser().parse(fixture(name)))
    chunks = chunk_sections(sections)
    assert len(chunks) >= len(sections), "a section produced no chunk"
    assert len(chunks) < 40, f"{len(chunks)} chunks — sub-items are being split"


def test_chunk_is_frozen():
    chunk = Chunk(section_ref="§4.1", text="x", token_count=1)
    with pytest.raises(Exception):
        chunk.text = "y"
