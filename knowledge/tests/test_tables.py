"""The reviewed Appendix 2 rows, checked against the printed page.

`knowledge/tables.py` is a hand-curated reconstruction, so this suite is the guard that
stops it drifting from the paper. It is deliberately built on `pdftotext -table`, which
aligns the table's rows; `-layout` is what interleaves them, and testing against it
would re-assert the defect.

The pairing assertions are not redundant with the presence checks. "Both cells are on
the page" is true for a wrong pairing too — that is exactly how the straw answer acquired
the wood condition. Pinning which condition belongs to which substance is the point.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge.tests.page_fixtures import pages

from knowledge.extraction import extract_pages
from knowledge.corpus import CORPUS_EDITS
from knowledge.tables import (
    APPENDIX_2_ROWS,
    APPENDIX_6A_ROWS,
    TABLE_BANDS,
    chunks_for_rows,
    rows_for,
)

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
    not a guess) restores each cell's own reading order — and this is only a *test*
    oracle: the corpus rows are already curated, and nothing splits at runtime.
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
    row = _by_substance("Seaweed and seaweed products")
    assert row.condition.endswith("iii) fermentation.")
    assert "iii) fermentation." not in _normalise(table_pages[76]), (
        "the cross-page continuation was pasted from the wrong page"
    )
    assert "iii) fermentation." in _normalise(table_pages[77])


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
    chunks = chunks_for_rows("Appendix 2")
    assert len(chunks) == len(APPENDIX_2_ROWS)
    assert all(chunk.section_ref == "Appendix 2" for chunk in chunks)
    for chunk, row in zip(chunks, APPENDIX_2_ROWS):
        assert chunk.text == row.text
        assert chunk.page == row.page
        assert chunk.heading_path.startswith("Appendix 2 — ")


def test_an_unreviewed_section_has_no_rows():
    assert rows_for("Appendix 3") == ()
    assert rows_for(None) == ()


# --- Appendix 6a: twenty classes, twenty stocking rates ---------------------
#
# Read from the page on 2026-10-28 (`BugFixes/saoso_text_glyphs_and_boundaries.md` §5).
# `-layout` put five values on a neighbour's line and piled the other fifteen at the foot
# of the page, so "how many laying hens per hectare?" was unanswerable from the appendix
# that answers it. The pairing is the table's meaning, which is why the guard pins the
# pairing and not merely the presence of the words.


def test_appendix_6a_is_twenty_classes_and_1_2_3_4_5_6_7_8_9_10_11_12_13_14_15_16_17_18_19_20_values():
    assert len(APPENDIX_6A_ROWS) == 20, "the paper prints twenty classes"
    assert all(row.condition for row in APPENDIX_6A_ROWS), (
        "every 6a row prints a stocking rate: a silent row would divide by nothing"
    )
    assert all(row.section_ref == "Appendix 6a" for row in APPENDIX_6A_ROWS)
    assert all(row.page == 85 for row in APPENDIX_6A_ROWS)


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


@pytest.mark.parametrize("row", APPENDIX_6A_ROWS, ids=lambda row: row.substance[:40])
def test_every_six_a_class_is_in_the_left_column_of_its_page(table_pages, row):
    left, _right = _streams([_corrected(page) for page in table_pages], row.page)
    assert _contains(left, row.substance), (
        f"{row.substance!r} is not in the left column of printed page {row.page}"
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


@pytest.mark.parametrize("row", APPENDIX_6A_ROWS, ids=lambda row: row.substance[:40])
def test_every_six_a_value_is_paired_with_its_class_on_one_line(table_pages, row):
    """The `-layout` defect in one assertion: the value must sit on the class's own line.

    A presence check would pass on the broken pairing too — every value is on the page, and
    five of them were on a *neighbour's* line while fifteen piled up at the foot of it. This
    is the guard that says which class owns which number.
    """
    lines = [
        line
        for line in _corrected(table_pages[row.page]).splitlines()
        if _contains(line, row.substance)
    ]
    assert lines, f"{row.substance!r} is not on printed page {row.page}"
    assert any(_follows(line, row.substance, row.condition) for line in lines), (
        f"printed p.{row.page}: {row.condition!r} is not on the line of {row.substance!r} "
        f"— the curated pairing has drifted from the paper"
    )


def test_one_chunk_per_six_a_row_and_none_of_them_invented():
    chunks = chunks_for_rows("Appendix 6a")
    assert len(chunks) == 20
    assert all(chunk.section_ref == "Appendix 6a" for chunk in chunks)
    assert all(chunk.heading_path.startswith("Appendix 6a — ") for chunk in chunks)
    for chunk, row in zip(chunks, APPENDIX_6A_ROWS):
        assert chunk.text == row.text
