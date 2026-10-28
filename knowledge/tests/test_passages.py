"""A passage's display layout — paragraphs, headings and lists, without changing a word.

The shapes below are the ones the shipped corpus actually has (`CONCORDANCE_PRD` §10 and the
passage-layout PRD §1): SAOSO prints lettered conditions with no punctuation and unreliable
indentation, the OPP numbers and letters at once, and the BPP artefact carries markdown headings.

The guard at the end runs the **real ingest** and asserts that flattening the rendered blocks
reproduces every chunk's text. A formatter that drops a line or swallows a marker fails there,
not in a hand-written fixture (`testing_hazards.md` §1.32).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from knowledge.ingest import ingest_standard
from knowledge.models import DocumentChunk, StandardSet
from knowledge.passages import flatten, passage_blocks
from knowledge.tests.page_fixtures import stub_ingest_extraction

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parents[2]
SAOSO_PDF = REPO_ROOT / "pgs_docs" / "saoso-version-2.1-2026.pdf"
HASH_HEADING = re.compile(r"^#{1,6}[ \t]+", re.MULTILINE)


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@pytest.fixture(autouse=True)
def committed_extraction(monkeypatch):
    stub_ingest_extraction(monkeypatch)


@pytest.fixture
def standard_set(db):
    return StandardSet.objects.create(
        code="outeniqua", label="Outeniqua", is_default=True
    )


# --- The contract ------------------------------------------------------------


def test_flatten_reproduces_the_block_text():
    blocks = passage_blocks("a  First item;\n\nb  Second item.")

    assert normalise(flatten(blocks)) == "a First item; b Second item."


def test_flatten_keeps_the_marker_as_printed():
    blocks = passage_blocks("1.  Sign the pledge.")

    assert "1." in flatten(blocks)


def test_an_empty_text_is_no_blocks():
    """A chunk with no text must not invent a paragraph or raise."""
    assert passage_blocks("") == ()
    assert passage_blocks("   \n\n  ") == ()


# --- Prose -------------------------------------------------------------------


def test_hard_wrapped_prose_becomes_one_paragraph():
    blocks = passage_blocks(
        "The first line ends mid-sentence\n\nand continues here, because the page is double-spaced."
    )

    assert [block.kind for block in blocks] == ["paragraph"]
    assert blocks[0].text == (
        "The first line ends mid-sentence and continues here, because the page is double-spaced."
    )


def test_a_markdown_heading_from_the_bpp_artefact_is_a_heading_block():
    blocks = passage_blocks("## INTRODUCTION\nThe PGS operates on six elements.")

    assert [block.kind for block in blocks] == ["heading", "paragraph"]
    assert blocks[0].text == "INTRODUCTION"


def test_a_numbered_caps_opener_is_a_heading_not_a_one_item_list():
    assert [block.kind for block in passage_blocks("1. DEFINITIONS")] == ["heading"]


def test_a_section_opener_without_caps_is_also_a_heading():
    """`I. Membership procedure` is the OPP's section title, not a one-row list."""
    assert [block.kind for block in passage_blocks("I. Membership procedure")] == ["heading"]


def test_a_glossary_term_is_its_own_block():
    """`S1` prints a term on one line and its definition under it; the reader must not glue the
    two into one paragraph, or the definitions page becomes a wall of text."""
    text = (
        "ACB\n\nAccredited Certification Body. Accredited to ISO 17065.\n\n"
        "Acceptable\n\nAcceptable to the authority administering this Standard."
    )

    blocks = passage_blocks(text)

    assert [block.kind for block in blocks] == ["term", "paragraph", "term", "paragraph"]
    assert blocks[0].text == "ACB"
    assert blocks[2].text == "Acceptable"


def test_a_title_case_numbered_line_is_a_list_item():
    blocks = passage_blocks(
        "Intro line.\n\n1. Ecosystem Management\nThe PGS maintains habitats."
    )

    assert blocks[1].kind == "list"
    assert blocks[1].items[0].text == "Ecosystem Management The PGS maintains habitats."


# --- Lists: sequence, family, nesting, continuations -------------------------


def test_bare_letters_with_unreliable_indents_are_one_list():
    """S5.6 prints its first item at column 8 and the rest at 0; `a, b, c` is still one list."""
    text = "a      First;\n\n\nb  Second;\n\nc  Third;"

    block = passage_blocks(text)[0]

    assert block.kind == "list"
    assert [item.marker for item in block.items] == ["a", "b", "c"]
    assert block.style == "lower-alpha"
    assert block.start == 1


def test_a_restarted_letter_sequence_is_a_new_list():
    text = "a  One;\nb  Two;\n\nSome prose.\n\na  Again;\nb  Again too;"

    kinds = [block.kind for block in passage_blocks(text)]

    assert kinds == ["list", "paragraph", "list"]


def test_a_roman_list_under_a_letter_nests():
    text = (
        "a  Farmyard manure:\n\n   i. from organic holdings;\n   ii. or satisfying Appendix 2;\n\n"
        "b  Products of agricultural origin."
    )

    outer = passage_blocks(text)[0]

    assert [item.marker for item in outer.items] == ["a", "b"]
    assert outer.items[0].children[0].style == "lower-roman"
    assert [item.marker for item in outer.items[0].children[0].items] == ["i.", "ii."]


def test_a_restarted_decimal_after_a_nested_list_starts_a_new_list():
    text = (
        "1. One;\n2. Two:\n      a. A sub-point;\n      b. Another;\n1. Supply information;\n2. Read the standard."
    )

    blocks = passage_blocks(text)

    assert len(blocks) == 2
    assert [item.marker for item in blocks[0].items] == ["1.", "2."]
    assert blocks[0].items[1].children[0].style == "lower-alpha"
    assert [item.marker for item in blocks[1].items] == ["1.", "2."]


def test_a_wrapped_line_at_the_body_column_continues_the_item():
    text = "a  First line\n\n   second line;\nb  Next;"

    item = passage_blocks(text)[0].items[0]

    assert item.text == "First line second line;"


def test_a_line_at_column_zero_continues_a_lettered_item():
    """SAOSO's glossary prints `a  ACB` and the definition at column 0 — it belongs to the item."""
    text = "a  ACB\nAccredited Certification Body.\nb  Additive\nA substance not normally consumed."

    block = passage_blocks(text)[0]

    assert [item.marker for item in block.items] == ["a", "b"]
    assert block.items[0].text == "ACB Accredited Certification Body."


def test_a_centred_label_ends_the_list_and_is_not_a_heading():
    """The paper's casing separates its two centred shapes, and the reader must too.

    `South African specific` is a marginal label printed above the definition or clause it
    qualifies — 26 of them in `S1` alone. Set at heading weight it read as a section heading, which
    is what a reader reported on 2026-10-27. `SECTION B` is a division title, and stays one.
    """
    label = "a  One;\n\n                    South African specific\n\nAreas are defined in the Act."
    division = "a  One;\n\n                    SECTION B\n\nAreas are defined in the Act."

    assert [block.kind for block in passage_blocks(label)] == ["list", "qualifier", "paragraph"]
    assert passage_blocks(label)[1].text == "South African specific"
    assert [block.kind for block in passage_blocks(division)] == ["list", "heading", "paragraph"]


def test_a_wrapped_clause_is_one_paragraph_and_copies_as_one_sentence():
    """SAOSO prints a clause's continuation on a hanging indent of 6–9 columns.

    `S23.3` is stored as two lines because the paper wraps it; the reader split them into two
    paragraphs, so a quoted clause could not be selected as one sentence and copying it gave
    `…property or documents.23.5. Operators…` — no break, no space. Measured on the shipped
    corpus: 25 of 319 chunks carried a split-off continuation (`BugFixes/reader_clause_line_breaks.md`).
    """
    text = (
        "23.3. Operators shall not use forced or involuntary labour or apply any pressure such as "
        "retaining part of the\n"
        "         workers' wages, property or documents.\n"
        "\n"
        "23.5. Operators shall provide their employees and contractors equal opportunity."
    )

    blocks = passage_blocks(text)

    assert [block.kind for block in blocks] == ["paragraph", "paragraph"]
    assert blocks[0].text.endswith("workers' wages, property or documents.")
    assert blocks[1].text.startswith("23.5.")


def test_a_centred_note_between_two_paragraphs_is_still_its_own_block():
    """The hanging indent joins; the centred line still splits, in both directions.

    `S4.8.6` prints a footnote whose tail (`certifiers using this standard.`) is centred at column
    46 — that one stays apart, and so does the prose printed *after* a centred label. A rule that
    only looked at the incoming line would join the label to the sentence below it.
    """
    note = (
        " This Section combines the conversion periods of the IFOAM Norms with the EU 2018-848 "
        "in order to derive guidance for those\n"
        "                                              certifiers using this standard."
    )
    label = "                    South African specific\n\nAreas are defined in the Act."

    assert [block.kind for block in passage_blocks(note)] == ["paragraph", "paragraph"]
    assert passage_blocks(note)[1].text == "certifiers using this standard."
    assert [block.kind for block in passage_blocks(label)] == ["qualifier", "paragraph"]


def test_a_line_starting_with_a_single_space_letter_is_prose():
    assert passage_blocks("a lot of things happen on a farm.")[0].kind == "paragraph"


def test_a_number_without_punctuation_is_not_a_list_marker():
    """`5.2.2     Conversion periods…` is a printed clause number, not a list row."""
    assert passage_blocks("5.2.2     Conversion periods are set out below.")[0].kind == "paragraph"


def test_a_word_that_happens_to_be_roman_letters_is_not_a_list():
    """`mix` is spelled from roman letters; it is not a numeral."""
    assert passage_blocks("mix  the compost thoroughly.")[0].kind == "paragraph"


def test_a_list_starting_later_reports_its_own_start_value():
    text = "c  Third;\nd  Fourth;"

    block = passage_blocks(text)[0]

    assert block.start == 3
    assert block.style == "lower-alpha"


def test_the_opp_bullet_is_a_list_marker():
    """`●` (U+25CF) is what the OPP actually prints — 66 times.

    It only reached the corpus on 2026-10-27: the extraction had been dropping the glyph
    outright (Xpdf writing Latin-1, `knowledge/extraction.py`), so the OPP's `●` lists
    arrived as bare sentences and every one of them read as prose. A shape this corpus
    really has belongs in the unit tests, not only in the fixture-level guards.
    """
    blocks = passage_blocks(
        "● Members are required to attend our annual group meeting.\n\n"
        "● All farmers are to attend at least two other farm visits annually."
    )

    assert [block.kind for block in blocks] == ["list"]
    assert blocks[0].style == "disc"
    assert len(blocks[0].items) == 2


def test_the_formatter_never_raises_and_never_drops_text():
    """Adversarial shapes: no marker, stray markers, a marker with no body line following."""
    for text in (
        "a",
        "a ",
        "1.",
        "\n\n\n",
        "a  b\n1. c\n(i) d\n- e",
        "## \n## Heading with no body",
    ):
        blocks = passage_blocks(text)
        assert isinstance(blocks, tuple)
        assert normalise(flatten(blocks)) == normalise(HASH_HEADING.sub("", text))


# --- The guard: the real corpus ---------------------------------------------


def test_the_real_corpus_survives_the_layout_and_produces_lists(standard_set):
    """Two guards in one ingest (six seconds): nothing is lost, and structure is actually found.

    The lossless half is the PRD's promise: for every chunk of the shipped SAOSO, flattening the
    rendered blocks reproduces the stored text (whitespace aside, and with the BPP artefact's `## `
    prefix accounted for). The second half stops a formatter that returns one paragraph per chunk
    from passing it.
    """
    ingest_standard(pdf_path=SAOSO_PDF, standard_set=standard_set, doc_key="saoso", embed=False)
    chunks = list(DocumentChunk.objects.order_by("id"))
    assert len(chunks) == 338  # 319 + the 19 reviewed Appendix 6a rows

    for chunk in chunks:
        source = normalise(HASH_HEADING.sub("", chunk.text))
        rendered = normalise(flatten(passage_blocks(chunk.text)))
        assert rendered == source, f"{chunk.section_ref}: the layout changed the text"

    # The store itself: no character the paper prints may be sitting here as U+FFFD. The
    # fixture guards (`test_corpus_glyphs.py`) prove the extraction keeps its characters;
    # this proves the *ingest* does, end to end, on the real corpus.
    assert "\ufffd" not in "".join(chunk.text for chunk in chunks), (
        "the ingested text holds a replacement character, so a printed glyph was lost"
    )

    by_ref = {chunk.section_ref: chunk for chunk in chunks}

    s513 = next(block for block in passage_blocks(by_ref["S5.1.3"].text) if block.kind == "list")
    assert [item.marker for item in s513.items] == ["a", "b", "c", "d", "e", "f"]
    assert "for poultry" in s513.items[5].text

    s81 = next(block for block in passage_blocks(by_ref["S8.1"].text) if block.kind == "list")
    assert s81.items[0].children[0].style == "lower-roman"

    s214 = passage_blocks(by_ref["S2.1.4"].text)
    lists = [block for block in s214 if block.kind == "list"]
    assert len(lists) == 2, "S2.1.4 prints two lettered lists and the second restarts at a"

    s513_blocks = passage_blocks(by_ref["S5.1.3"].text)
    qualifiers = [block.text for block in s513_blocks if block.kind == "qualifier"]
    assert "Regional or other exception" in qualifiers
    assert "SOUTH AFRICAN specific" in qualifiers

    # The measured ratio (§3.12's neighbour): the shipped SAOSO centres 62 blocks, and 58 of them
    # are printer's labels in mixed case. None of them may render at a division title's weight.
    every_block = [
        block for chunk in chunks for block in passage_blocks(chunk.text)
    ]
    labels = [b.text for b in every_block if b.kind == "qualifier"]
    headings = [b.text for b in every_block if b.kind == "heading"]
    assert sum(1 for text in labels if "South African" in text) >= 25
    assert not any("South African specific" == text for text in headings)
    assert not any("Regional or other exception" == text for text in headings)
    # The part banner is the page's running head, not a division title in the text: since
    # 2026-10-28 the parser drops it (`SaosoParser.body_lines`), which is what stops twelve
    # branches ending with a part title and nothing after it
    # (`BugFixes/saoso_text_glyphs_and_boundaries.md` §3). The division-vs-label rule itself
    # is pinned on a fixture by `test_a_centred_label_ends_the_list_and_is_not_a_heading`.
    assert not any("SECTION B" == text for text in headings)

    s1_terms = [
        block.text
        for chunk in chunks
        if chunk.section_ref == "S1"
        for block in passage_blocks(chunk.text)
        if block.kind == "term"
    ]
    assert {"ACB", "Habitat", "Genetically Modified Organism (GMO)"} <= set(s1_terms)

    everything = [block for chunk in chunks for block in passage_blocks(chunk.text)]
    assert sum(1 for block in everything if block.kind == "list") > 60
    assert sum(1 for block in everything if block.kind == "term") > 100


#: How many paragraphs of the shipped corpus that are **not** the chunk's first block begin with a
#: lower-case word, by section: measured 2026-10-28 after the hanging-indent fix (0 before it: 20).
#: Every remaining one is a **corpus** defect named in
#: `BugFixes/saoso_text_glyphs_and_boundaries.md` — the reader cannot join them without inventing
#: text — so they are recorded here rather than left to hide the next split:
#:
#: * `S1` — the `m²` superscript of *Factory farming* is its own extracted line, so the sentence
#:   resumes after it ("…more / 2 / than 25kg weight/m .", §2 there: a corpus edit);
#: * `S4.8.6` — the tail of a footnote, printed centred at column 46, correctly gets its own block
#:   (§3: the section banner is a parser concern);
#: * `Appendix 1`, `Appendix 3`, `Appendix 7` — table cells whose text came away from its label
#:   (§5), and `Appendix 6b`, whose two-column table lost its rows entirely (§5).
_SPLIT_BLOCK_EXCEPTIONS = {
    "S1",
    "S4.8.6",
    "Appendix 1",
    "Appendix 3",
    "Appendix 6b",
    "Appendix 7",
}


def test_no_clause_is_split_off_its_own_sentence(standard_set):
    """The measurement in the bug, as a guard: 13 chunks of 319 ended in a dangling continuation.

    A hanging indent (6–9 columns) is how SAOSO prints a wrapped clause, and the block-splitting
    rule treated it as a centred label — so a sentence arrived in two pieces and copying it glued
    the next clause on (`…property or documents.23.5. Operators…`). The guard is over the real
    corpus because a three-line fixture passes while the document is wrong (`testing_hazards.md`
    §1.6). It counts a paragraph that is not the chunk's **first** block, because a chunk that
    begins mid-sentence opens with a lower-case word and that is the chunker's, not the layout's.

    A *new* dangling paragraph is a new defect; the recorded ones are corpus edits.
    """
    ingest_standard(pdf_path=SAOSO_PDF, standard_set=standard_set, doc_key="saoso", embed=False)
    chunks = list(DocumentChunk.objects.order_by("id"))
    assert len(chunks) == 338

    split = []
    for chunk in chunks:
        for index, block in enumerate(passage_blocks(chunk.text)):
            if index == 0 or block.kind != "paragraph" or not block.text:
                continue
            if block.text.split(" ", 1)[0][:1].islower():
                split.append((chunk.section_ref, block.text[:60]))

    unexpected = [case for case in split if case[0] not in _SPLIT_BLOCK_EXCEPTIONS]
    assert not unexpected, f"a clause is split from its own sentence: {unexpected}"
