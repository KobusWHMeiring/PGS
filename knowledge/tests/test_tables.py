"""Appendix 2's rows, checked against the printed page — read from the artefact's block.

The rows used to be Python literals in `knowledge/tables.py`. S5-b emitted the `<!-- table … -->`
block from the page and deleted them, so this suite now reads what the corpus actually holds: the
pairing is data the artefact carries, and the assertions below did not change when their source did
— that is the point of the slice.

The pairing assertions are not redundant with the presence checks. "Both cells are on
the page" is true for a wrong pairing too — that is exactly how the straw answer acquired
the wood condition. Pinning which condition belongs to which substance is the point.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from knowledge.tests.page_fixtures import pages

from knowledge.corpus import CORPUS_EDITS
from knowledge.corpus import load_document
from knowledge.table_chunks import chunks_for_parsed_section
from knowledge.tables import TABLE_BANDS

REPO_ROOT = Path(__file__).resolve().parents[2]
SAOSO_PDF = REPO_ROOT / "pgs_docs" / "saoso-version-2.1-2026.pdf"


def _normalise(text: str) -> str:
    return " ".join(text.split())


def _words(text: str) -> list[str]:
    """A cell and a page are compared as words, not characters.

    The extraction carries two artefacts that are not the document's: a hyphen that a
    line break split (`cobalt- sulphate`) and a stray list comma at the start of a
    wrapped condition. Neither changes a single word, and neither should make the
    curated table look wrong — but a changed *word* must fail.
    """
    return [
        core
        for core in (word.strip(".,;:()[]").lower() for word in _normalise(text).split())
        if core
    ]


def _contains(haystack: str, needle: str) -> bool:
    hay = _words(haystack)
    want = _words(needle)
    if not want:
        return True
    return any(hay[i : i + len(want)] == want for i in range(len(hay) - len(want) + 1))


#: `pdftotext` prints the page's furniture (registration, footer, page number) inside the
#: right column's x-range, so it would sit between two halves of a condition that crosses
#: a page break. It is not part of any cell; drop it before joining pages.
_FURNITURE = (
    "Registration",
    "Postnet Suite",
    "Tel:",
    "Page",
    "Sector Organisation",
    "Bag X153",
)


def _join_lines(lines: list[str]) -> str:
    """Join a column's lines, undoing a hyphen that the line break introduced.

    "cobalt-" at the end of a line and "sulphate" at the start of the next is one
    printed word (`cobalt-sulphate`), not two. The same rule applies to the curated
    cell, so this is applied to both sides of the comparison — it is the one place the
    reconstruction is allowed to differ from the raw extraction.
    """
    joined: list[str] = []
    for line in lines:
        line = line.strip()
        if not line or any(marker in line for marker in _FURNITURE):
            continue
        if joined and joined[-1].endswith("-") and line[:1].islower():
            joined[-1] = joined[-1] + line
        else:
            joined.append(line)
    return _normalise("\n".join(joined))


@pytest.fixture(scope="module")
def table_pages() -> list[str]:
    """The SAOSO PDF as `pdftotext -table` renders it, one string per PDF page."""
    return pages("saoso", "table")


def _printed_page(pages: list[str], printed: int) -> str:
    """SAOSO prints `pdf - 1`, so printed page 76 is `pages[76]` (0-indexed)."""
    return _normalise(pages[printed])


def _streams(pages: list[str], printed: int) -> tuple[str, str]:
    """The left and right columns of a printed page, as separate text streams.

    `pdftotext -table` aligns a row but still prints both cells on one line, so a cell
    that wraps is interrupted by its neighbour. Splitting at the measured band (data,
    not a guess) restores each cell's own reading order.
    """
    band = TABLE_BANDS[printed]
    left: list[str] = []
    right: list[str] = []
    for line in pages[printed].splitlines():
        cut = line[:band].rstrip()
        rest = line[band:].strip()
        if cut.strip():
            left.append(cut)
        if rest:
            right.append(rest)
    return _join_lines(left), _join_lines(right)


@dataclass(frozen=True)
class Row:
    """One row of the artefact's Appendix 2 block, in the shape the old literals had.

    `raw` is the cells as the block stores them — the page's own lines, blank lines and all —
    because `text` has to be the chunk text the ingest writes. `substance` and `condition` are the
    same words with the printed line breaks joined, which is what a comparison with a page stream
    can use.
    """

    page: int
    raw: tuple[str, ...]

    @property
    def substance(self) -> str:
        return _join_lines(self.raw[0].splitlines()) if self.raw else ""

    @property
    def condition(self) -> str:
        return _join_lines(self.raw[1].splitlines()) if len(self.raw) > 1 else ""

    @property
    def text(self) -> str:
        return "\n".join(self.raw)


def _appendix_2():
    """The artefact's Appendix 2 section, its block, and its rows in printed order (S5-b)."""
    document = load_document(REPO_ROOT / "knowledge" / "corpus" / "saoso.md")
    section = next(s for s in document.sections if s.section_ref == "Appendix 2")
    table = section.tables[0]
    rows = tuple(
        Row(page=row.page, raw=tuple(cell.text for cell in row.cells)) for row in table.rows
    )
    return section, table, rows


APPENDIX_2_ROWS = _appendix_2()[2]


@pytest.mark.parametrize("row", APPENDIX_2_ROWS, ids=lambda row: row.substance[:40])
def test_every_substance_cell_is_on_its_printed_page(table_pages, row):
    left, _right = _streams(table_pages, row.page)
    assert _contains(left, row.substance), (
        f"{row.substance!r} is not in the left column of printed page {row.page}: the "
        "curated table has drifted from the document"
    )


@pytest.mark.parametrize("row", APPENDIX_2_ROWS, ids=lambda row: row.substance[:40])
def test_every_condition_cell_is_on_its_printed_page_or_the_next(table_pages, row):
    if not row.condition:
        return
    _left, right = _streams(table_pages, row.page)
    if row.page + 1 in TABLE_BANDS:
        # A condition may continue at the top of the next page (seaweed's
        # `iii) fermentation.`). Append the raw next page: the band on a continuation
        # page is not the table body's, and only the continuation is of interest here.
        right = f"{right} {_normalise(table_pages[row.page + 1])}"
    assert _contains(right, row.condition), (
        f"the condition for {row.substance[:40]!r} is not in the right column of "
        f"printed page {row.page} (or the page after it)"
    )


def _by_substance(prefix: str) -> object:
    matches = [row for row in APPENDIX_2_ROWS if row.substance.startswith(prefix)]
    assert len(matches) == 1, f"{prefix!r} matched {len(matches)} rows"
    return matches[0]


# --- The pairings this increment exists to get right -------------------------


def test_wood_carries_the_untreated_condition():
    assert _by_substance("Wood, bark, sawdust").condition == "Only if not chemically treated"


def test_crop_residues_carry_no_condition():
    """Straw's only requirement is that it is a listed plant material.

    The live 2026-10-21 answer said straw must be untreated. That condition is printed
    beside wood; this row must stay unconditioned or the answer regresses.
    """
    assert _by_substance("Crop residues and plant materials").condition == ""


def test_biodegradable_by_products_carry_the_contaminants_condition():
    row = _by_substance("Biodegradable processing by-products, plant or animal origin")
    assert row.condition.startswith("Free of significant contaminants")
    assert "composted before bringing onto organic land" in row.condition


def test_the_condition_does_not_leak_onto_the_unconditioned_rows():
    """`Free of significant contaminants` sits beside three unconditioned rows.

    The product owner reviewed the pairing on 2026-10-21: it belongs to the
    by-products row only. A future edit that repeats it onto its neighbours fails here.
    """
    for prefix in ("Vermicastings", "Blood meal", "Hoof and horn meal"):
        assert _by_substance(prefix).condition == ""


def test_trace_elements_carry_the_deficiency_restriction():
    row = _by_substance("Trace elements")
    assert "boric acid, sodium borate" in row.substance
    assert "soil/plant nutrient deficiency is documented" in row.condition
    assert "chloride or nitrate forms are prohibited" in row.condition
    assert "defoliant, herbicide, or desiccant" in row.condition


def test_peat_is_prohibited_for_soil_conditioning_and_restricted_to_horticulture():
    row = _by_substance("Peat")
    assert row.condition.startswith("Excluding synthetic additives")
    assert "horticulture (floriculture, nursery plants, potting mixes)" in row.condition


def test_urban_compost_carries_the_heavy_metal_limits():
    row = _by_substance("Urban composts")
    for limit in ("cadmium: 0,7", "copper: 70", "chromium (VI): 0"):
        assert limit in row.condition


# --- Cross-page and structural expectations ----------------------------------


def test_the_seaweed_condition_crosses_the_page_break(table_pages):
    """The tail is the first line of printed 77, and it prints `(iii)` — with a bracket.

    **This test could not tell, until 2026-11-05.** It asserted `endswith("iii) fermentation.")`
    and `"iii) fermentation." in <printed 77>`, and both were true of the artefact's spelling
    *and* of the page's, because the shorter string is a substring of the longer one: the review
    had dropped the opening bracket and nothing failed. The owner found it by reading the page.
    The page it came from is **printed 79**, where Appendix 3 prints `iii) fermentation.` beside
    `Coffee grounds` — a different table, two pages later.

    So the assertion is character-level here, and it is the same rule the emitter applies: a
    cell's characters are the page's.
    """
    row = _by_substance("Seaweed and seaweed products")
    assert row.condition.endswith("(iii) fermentation."), (
        "the seaweed row's tail is printed as `(iii) fermentation.` — with the opening bracket"
    )
    assert "(iii) fermentation." not in _normalise(table_pages[76]), (
        "the cross-page continuation was pasted from the wrong page"
    )
    printed_77 = _normalise(table_pages[77])
    assert printed_77.lstrip().startswith("(iii) fermentation."), (
        "the continuation is the first line of printed 77, not merely somewhere on it"
    )
    assert "Coffee grounds" in _normalise(table_pages[79]), (
        "the other spelling of this phrase (`iii)` without the bracket) is printed beside "
        "`Coffee grounds` on printed 79; this test exists because that is where the review's "
        "spelling came from"
    )


def test_rows_are_in_printed_order():
    pages = [row.page for row in APPENDIX_2_ROWS]
    assert pages == sorted(pages)
    assert pages[0] == 76 and pages[-1] == 78


def test_a_condition_never_appears_inside_a_substance_cell():
    """A paste error that duplicated a condition into the left column would pass the
    presence test on both cells but make the model quote a row that never existed."""
    conditions = {row.condition for row in APPENDIX_2_ROWS if row.condition}
    for row in APPENDIX_2_ROWS:
        for condition in conditions:
            if condition == row.condition:
                continue
            assert condition not in row.substance, row.substance


def test_one_chunk_per_row_and_none_of_them_invented():
    section, _table, rows = _appendix_2()
    chunks = [
        chunk
        for chunk in chunks_for_parsed_section(section)
        if chunk.heading_path.startswith("Appendix 2 — ")
    ]
    assert len(chunks) == len(rows)
    assert all(chunk.section_ref == "Appendix 2" for chunk in chunks)
    for chunk, row in zip(chunks, rows):
        assert chunk.text == row.text
        assert chunk.page == row.page
        assert chunk.heading_path.startswith("Appendix 2 — ")


def test_a_section_with_no_table_keeps_the_ordinary_chunker():
    """The one storage's counterpart: an unreviewed section is prose, chunked as prose.

    It used to assert `rows_for("Appendix 3") == ()` — a lookup into the Python rows that S5-b
    deleted. The claim it protected is that the table mechanism does not reach a section that
    prints no block, and that is what this says now.
    """
    document = load_document(REPO_ROOT / "knowledge" / "corpus" / "saoso.md")
    section = next(s for s in document.sections if s.section_ref == "Appendix 3")
    assert section.tables == ()
    assert chunks_for_parsed_section(section)


# --- Appendix 6a: twenty classes, twenty stocking rates ---------------------
#
# Read from the page on 2026-10-28 (`BugFixes/saoso_text_glyphs_and_boundaries.md` §5).
# `-layout` put five values on a neighbour's line and piled the other fifteen at the foot
# of the page, so "how many laying hens per hectare?" was unanswerable from the appendix
# that answers it. The pairing is the table's meaning, which is why the guard pins the
# pairing and not merely the presence of the words.


def _six_a():
    """Appendix 6a as the corpus holds it: a `<!-- table -->` block in the artefact (S5).

    It used to be 20 Python literals (`APPENDIX_6A_ROWS`); the assertions below did not change,
    their source did. That is the point of S5 — the pairing is data the artefact carries, not a
    reconstruction beside it.
    """
    document = load_document(REPO_ROOT / "knowledge" / "corpus" / "saoso.md")
    section = next(s for s in document.sections if s.section_ref == "Appendix 6a")
    return section, tuple(
        (row.cells[0].text, row.cells[1].text, row.page) for row in section.tables[0].rows
    )


def test_appendix_6a_is_twenty_classes_and_1_2_3_4_5_6_7_8_9_10_11_12_13_14_15_16_17_18_19_20_values():
    section, rows = _six_a()
    assert section.section_ref == "Appendix 6a"
    assert len(rows) == 20, "the paper prints twenty classes"
    assert all(value for _substance, value, _page in rows), (
        "every 6a row prints a stocking rate: a silent row would divide by nothing"
    )
    assert all(page == 85 for _substance, _value, page in rows)


def _corrected(page: str) -> str:
    """The page as the artefact states it, with the review's declared corrections applied.

    Two Appendix 6a cells are printed in *tracking*, so the extraction holds one token per
    letter (`b o v i n e a n i m a l s`). `knowledge/corpus.py` records the review that joins
    them; a guard that compared the curated cell to the letterspaced extraction would demand
    the defect back. The corrections themselves are justified in `test_corpus_saoso.py`.
    """
    for edit in CORPUS_EDITS["saoso"]:
        page = page.replace(edit.original, edit.replacement)
    return page


@pytest.mark.parametrize("row", _six_a()[1], ids=lambda row: row[0][:40])
def test_every_six_a_class_is_in_the_left_column_of_its_page(table_pages, row):
    substance, _value, page = row
    left, _right = _streams([_corrected(one) for one in table_pages], page)
    assert _contains(left, substance), (
        f"{substance!r} is not in the left column of printed page {page}"
    )


def _follows(line: str, substance: str, value: str) -> bool:
    """Are `value`'s words on `line`, after `substance`'s words? The pairing, in one predicate.

    Not a column slice: the declared correction to a letterspaced cell shortens the line, so a
    fixed band would compare the value against the wrong characters. A class name in this
    appendix holds no digits, so a numeric value cannot match one by accident.
    """
    words = _words(line)
    head = _words(substance)
    tail = _words(value)
    for start in range(len(words) - len(head) + 1):
        if words[start : start + len(head)] != head:
            continue
        rest = words[start + len(head) :]
        if any(rest[i : i + len(tail)] == tail for i in range(len(rest) - len(tail) + 1)):
            return True
    return False


@pytest.mark.parametrize("row", _six_a()[1], ids=lambda row: row[0][:40])
def test_every_six_a_value_is_paired_with_its_class_on_one_line(table_pages, row):
    """The `-layout` defect in one assertion: the value must sit on the class's own line.

    A presence check would pass on the broken pairing too — every value is on the page, and
    five of them were on a *neighbour's* line while fifteen piled up at the foot of it. This
    is the guard that says which class owns which number.
    """
    substance, value, page = row
    lines = [
        line
        for line in _corrected(table_pages[page]).splitlines()
        if _contains(line, substance)
    ]
    assert lines, f"{substance!r} is not on printed page {page}"
    assert any(_follows(line, substance, value) for line in lines), (
        f"printed p.{page}: {value!r} is not on the line of {substance!r} "
        f"— the curated pairing has drifted from the paper"
    )


def test_one_chunk_per_six_a_row_and_none_of_them_invented():
    """The block's rows *are* the chunks, and each carries its column meaning (R2).

    Twenty row chunks, and two prose chunks the block does not swallow: the printed title and
    header above it (`NUMBER OF ANIMALS PER HA EQUIVALENT TO 170 KG N/HA/YEAR`, `Source: EU
    2092/91`, and the two labels) and the part banner the section's body carries onto the next
    page. Those are the page's own words, and the header is where a citation of *per hectare*
    comes from — before S5 they were dropped together with the interleaved cells.
    """
    section, rows = _six_a()
    chunks = chunks_for_parsed_section(section)
    assert all(chunk.section_ref == "Appendix 6a" for chunk in chunks)
    row_chunks = [chunk for chunk in chunks if chunk.heading_path.startswith("Appendix 6a — ")]
    assert len(row_chunks) == 20
    for chunk, (substance, value, _page) in zip(row_chunks, rows):
        assert chunk.text == substance + chr(10) + value
        assert "Class or species:" in chunk.embedding_text
        assert "Maximum number of animals per ha" in chunk.embedding_text
    prose = [chunk.text for chunk in chunks if chunk not in row_chunks]
    assert len(prose) == 2, prose
    assert "NUMBER OF ANIMALS PER HA" in prose[0] and "Source: EU 2092/91" in prose[0]
    assert prose[1].strip().endswith("SOUTH AFRICAN specific")
