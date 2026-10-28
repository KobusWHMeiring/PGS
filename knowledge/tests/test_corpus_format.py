"""The canonical corpus format (D53) — the reader's contract.

These tests describe the format itself, on synthetic artefacts: no PDF, no database, no
Poppler. The real document is tested in `test_corpus_bpp.py`, which is where the
traceability and review guards live.

The rule behind all of them: a block with no page is a quote no one can find on paper,
so every structural mistake must raise rather than default.
"""

from __future__ import annotations

import pytest

from knowledge.corpus import CorpusFormatError, parse_blocks

HEADER = """<!-- corpus
doc_key: bpp
source: pgs_docs/example.pdf
sha256: 0000000000000000000000000000000000000000000000000000000000000000
generator: knowledge corpusgen v1
-->"""


def artefact(body: str, header: str = HEADER) -> str:
    return f"{header}\n{body}\n"


def test_a_minimal_artefact_yields_one_section():
    document = parse_blocks(
        artefact(
            """<!-- page: 3 printed: none -->
## INTRODUCTION
The terms of reference for these principles are the SAOSO Standard."""
        )
    )
    assert [section.anchor for section in document.sections] == ["introduction"]
    assert document.sections[0].section_ref is None
    assert document.sections[0].page is None
    assert document.sections[0].heading_path == "INTRODUCTION"
    assert "The terms of reference" in document.sections[0].text


def test_the_page_marker_sets_the_printed_page_of_the_section():
    document = parse_blocks(
        artefact(
            """<!-- page: 61 printed: 60 -->
## S20.1 Processing and handling
Operators shall process organic products separately."""
        )
    )
    assert document.sections[0].page == 60, "D42: the printed page, not the PDF index"


def test_a_page_marker_between_blocks_re_attributes_what_follows():
    document = parse_blocks(
        artefact(
            """<!-- page: 3 printed: none -->
## GENERAL PRINCIPLES
first paragraph

second paragraph

<!-- page: 4 printed: none -->
third paragraph"""
        )
    )
    pages = [block.page for block in document.blocks if block.text.strip()]
    assert pages == [3, 3, 4]
    assert document.sections[0].page is None


def test_blocks_keep_their_own_whitespace_verbatim():
    document = parse_blocks(
        artefact(
            """<!-- page: 3 printed: none -->
## GENERAL PRINCIPLES
  indented line
second line"""
        )
    )
    assert document.blocks[0].text == "  indented line\nsecond line"


def test_a_ref_annotation_sets_the_section_ref():
    document = parse_blocks(
        artefact(
            """<!-- page: 61 printed: 60 -->
<!-- ref: S20.1 -->
## 20.1. Processing and handling
Operators shall process organic products separately."""
        )
    )
    assert document.sections[0].section_ref == "S20.1"
    assert document.sections[0].text.startswith("20.1. Processing"), (
        "an annotated heading is the cited line, so the marker is not part of the text"
    )


def test_a_heading_without_a_ref_keeps_its_marker():
    """The BPP's headings are real headings: `## INTRODUCTION` renders as one.

    Only an annotated heading loses the marker (`_heading_text`), because only there does the
    annotation say the heading is the document's own cited line.
    """
    document = parse_blocks(
        artefact(
            """<!-- page: 3 printed: none -->
## INTRODUCTION
The terms of reference."""
        )
    )
    assert document.sections[0].text.startswith("## INTRODUCTION")


def test_nested_headings_build_heading_path():
    document = parse_blocks(
        artefact(
            """<!-- page: 61 printed: 60 -->
# SECTION B
## 20. Processing and handling
### 20.1.1. Operators shall
Operators shall process organic products separately."""
        )
    )
    assert [section.heading_path for section in document.sections] == [
        "SECTION B",
        "SECTION B > 20. Processing and handling",
        "SECTION B > 20. Processing and handling > 20.1.1. Operators shall",
    ], "the path includes the section itself: it is the only form that is useful alone"


def test_a_reviewer_comment_is_ignored_and_never_becomes_text():
    document = parse_blocks(
        artefact(
            """<!-- page: 3 printed: none -->
## INTRODUCTION
<!-- this line was repaired by hand -->
The terms of reference."""
        )
    )
    assert "repaired by hand" not in document.sections[0].text


def test_text_before_a_page_marker_is_an_error():
    with pytest.raises(CorpusFormatError, match="no page marker"):
        parse_blocks(
            artefact(
                """## INTRODUCTION
The terms of reference."""
            )
        )


def test_a_malformed_page_marker_is_an_error_not_an_ignored_comment():
    with pytest.raises(CorpusFormatError, match="malformed annotation"):
        parse_blocks(
            artefact(
                """<!-- page: three printed: none -->
## INTRODUCTION
Text."""
            )
        )


def test_text_before_any_heading_is_an_error():
    with pytest.raises(CorpusFormatError, match="before any heading"):
        parse_blocks(
            artefact(
                """<!-- page: 3 printed: none -->
stray text with no heading."""
            )
        )


def test_a_missing_header_field_is_an_error():
    header = HEADER.replace("doc_key: bpp\n", "")
    with pytest.raises(CorpusFormatError, match="doc_key"):
        parse_blocks(artefact("<!-- page: 3 printed: none -->\n## X\nText.", header))


def test_a_missing_header_is_an_error():
    with pytest.raises(CorpusFormatError, match="expected a `<!-- corpus` header"):
        parse_blocks("## INTRODUCTION\nText.")


def test_an_artefact_with_no_sections_is_an_error():
    with pytest.raises(CorpusFormatError, match="no headings"):
        parse_blocks(artefact("<!-- page: 3 printed: none -->"))


def test_the_header_extra_fields_are_kept_but_not_required():
    header = HEADER.replace(
        "generator: knowledge corpusgen v1",
        "generator: knowledge corpusgen v1\nreviewed_on: 2026-10-22",
    )
    document = parse_blocks(
        artefact("<!-- page: 3 printed: none -->\n## X\nText.", header)
    )
    assert document.extra == {"reviewed_on": "2026-10-22"}


def test_a_section_with_no_body_is_followed_by_the_next_sections_ref():
    """A clause that *is* its own heading has no body, so the next `ref:` follows immediately.

    Found on 2026-10-28 by generating the SAOSO artefact: `2.2.5. Operators shall prevent or
    remedy soil and water salinization…` is printed as one line, so its section has no body
    line between its heading and `<!-- ref: S2.2.6 -->`. The parser read that as a misplaced
    annotation and refused the 101-page draft (`reading.py`'s neighbour: `section.text` is the
    heading alone).
    """
    document = parse_blocks(
        artefact(
            """<!-- page: 33 printed: 32 -->
<!-- ref: S2.2.5 -->
### 2.2.5. Operators shall prevent salinization.
<!-- ref: S2.2.6 -->
### 2.2.6. Operators shall not deplete water resources.
They shall recycle rainwater."""
        )
    )

    assert [section.section_ref for section in document.sections] == ["S2.2.5", "S2.2.6"]
    assert document.sections[0].text == "2.2.5. Operators shall prevent salinization."
    assert document.sections[1].text.endswith("They shall recycle rainwater.")


def test_a_ref_in_the_middle_of_a_body_is_still_an_error():
    """The rule the allowance above must not weaken: a ref annotates the heading below it."""
    with pytest.raises(CorpusFormatError, match="immediately before"):
        parse_blocks(
            artefact(
                """<!-- page: 33 printed: 32 -->
<!-- ref: S2.2.5 -->
### 2.2.5. Operators shall prevent salinization.
<!-- ref: S2.2.6 -->
Some body text that belongs to 2.2.5.
### 2.2.6. Operators shall not deplete water resources."""
            )
        )


def test_two_refs_in_a_row_are_an_error():
    """Two annotations for one heading means one of them is being silently discarded."""
    with pytest.raises(CorpusFormatError, match="One reference per heading"):
        parse_blocks(
            artefact(
                """<!-- page: 33 printed: 32 -->
<!-- ref: S2.2.5 -->
<!-- ref: S2.2.6 -->
### 2.2.5. Operators shall prevent salinization."""
            )
        )


def test_a_long_clause_heading_gets_an_anchor_that_fits_the_column():
    """`DocumentChunk.anchor` is 128 characters; a clause heading is a whole sentence.

    The SAOSO artefact's first ingest failed with `value too long for type character
    varying(128)` (2026-10-28) on `20.1.1. Handlers and processors shall not co-mingle…`.
    The slug is truncated at a word boundary, and only ever shortens a *fallback* locator:
    a section with a `section_ref` is addressed by its reference.
    """
    heading = (
        "20.1.1. Handlers and processors shall not co-mingle organic products with "
        "non-organic products, and shall keep them identifiable at every stage."
    )
    document = parse_blocks(
        artefact(f"<!-- page: 61 printed: 60 -->\n<!-- ref: S20.1.1 -->\n### {heading}")
    )

    anchor = document.sections[0].anchor
    assert 0 < len(anchor) <= 128, anchor
    assert not anchor.endswith("-"), "truncated mid-word or on a separator"
    assert anchor.startswith("20-1-1-handlers")
