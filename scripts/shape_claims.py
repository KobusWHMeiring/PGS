"""What the eight-shape answer key claims, one reviewable claim at a time (D85).

`knowledge/tests/shape_fixtures.py` holds the key as `ShapeCase`s — a header tuple, a row count, the
page each row starts on, dividers, and a handful of asserted cells. That structure is right for a
scorer and wrong for a human: a reviewer cannot say *why* a shape failed if the only unit is a pass.
So this module flattens each case into **named claims** with stable ids, a question a person can
answer, and the answer text the paper must contain:

    numeric_row.header              does the paper print these 3 column labels, in this order?
    numeric_row.rows                does it print exactly 6 data rows?
    numeric_row.pages               does each row start on the page the key names?
    qualifier.divider.1.qualifier   is "South African specific" a divider above row 2?
    numeric_row.cell.0.1            row 1, column "Initial certification fee (R)": is it "1,500"?

`Claim.expected` is the canonical one-line form of the claim. It exists for one reason: a signature
must not outlive what it signed. `scripts/shape_review_signoff.py` writes it into
`knowledge/tests/shape_review.json`, and `drift()` fails the moment a later edit changes it — so
"the owner reviewed this key" stays a fact about *this* key rather than about a file name.

Nothing here reads a page, an image or a PDF. The claims are derived from the fixtures alone, so the
gate can rebuild and compare them with no extractor installed (requirement 10).
"""

from __future__ import annotations

from dataclasses import dataclass

from knowledge.tests.shape_fixtures import Cell, ShapeCase, SHAPES, flat

#: What a reviewer may say about a claim. `no` and `unsure` must carry a reason.
VERDICTS = ("yes", "no", "unsure")


@dataclass(frozen=True)
class Claim:
    """One thing the key asserts about one page, and the question that judges it."""

    id: str
    kind: str
    question: str
    answer: str
    #: The canonical claim text a signature is pinned to (`shape_review.json`).
    expected: str
    row: int = -1
    column: int = -1


def _q(text: str) -> str:
    """A claim's text, quoted the way the page prints it (whitespace collapsed, one line)."""
    return f"“{flat(text)}”"


def _cell_predicate(cell: Cell) -> str:
    """The cell claim as the reviewer's question: what the paper must print, exactly."""
    parts: list[str] = []
    if cell.text is not None:
        parts.append(f"print exactly {_q(cell.text)}")
    if cell.starts:
        parts.append(f"start with {_q(cell.starts)}")
    if cell.ends:
        parts.append(f"end with {_q(cell.ends)}")
    if cell.contains:
        parts.append(f"contain {_q(cell.contains)}")
    if cell.at_least:
        parts.append(f"hold at least {cell.at_least:,} characters")
    return " and ".join(parts)


def _cell_answer(cell: Cell) -> str:
    if cell.empty:
        return "The paper prints nothing in this cell — blank is the claim."
    parts: list[str] = []
    if cell.text is not None:
        parts.append(f"The printed cell is {_q(cell.text)}.")
    if cell.starts:
        parts.append(f"It starts with {_q(cell.starts)}.")
    if cell.ends:
        parts.append(f"It ends with {_q(cell.ends)}.")
    if cell.contains:
        parts.append(f"It contains {_q(cell.contains)}.")
    if cell.at_least:
        parts.append(f"It holds at least {cell.at_least:,} characters.")
    return " ".join(parts)


def cell_spec(cell: Cell) -> str:
    """The cell claim in one canonical line — what `shape_review.json` pins a verdict to."""
    fields = []
    if cell.text is not None:
        fields.append(f"text={flat(cell.text)}")
    if cell.empty:
        fields.append("empty")
    for name in ("starts", "ends", "contains"):
        value = getattr(cell, name)
        if value:
            fields.append(f"{name}={flat(value)}")
    if cell.at_least:
        fields.append(f"at_least={cell.at_least}")
    return "; ".join(fields)


def _pages_answer(case: ShapeCase) -> str:
    pairs = sorted(set(zip(range(len(case.row_pages)), case.row_pages)))
    if len({page for _, page in pairs}) == 1:
        return f"All {len(case.row_pages)} rows start on printed page {pairs[0][1]}."
    return "; ".join(f"row {row + 1} starts on printed page {page}" for row, page in pairs) + "."


def claims(case: ShapeCase) -> list[Claim]:
    """Every claim the key makes about this shape, in reading order. Ids are stable and unique."""
    found: list[Claim] = [
        Claim(
            id=f"{case.key}.header",
            kind="header",
            question=(
                f"Does the paper print exactly these {len(case.columns)} column labels, in this "
                "order, as the header of this table?"
            ),
            answer=" · ".join(_q(column) for column in case.columns),
            expected=" | ".join(flat(column) for column in case.columns),
        ),
        Claim(
            id=f"{case.key}.rows",
            kind="rows",
            question=(
                f"Does the paper print exactly {case.row_count} data rows under that header — "
                "no more, no fewer?"
            ),
            answer=f"{case.row_count} rows.",
            expected=str(case.row_count),
        ),
    ]
    if case.row_pages:
        found.append(
            Claim(
                id=f"{case.key}.pages",
                kind="pages",
                question="Does each row start on the page the key names?",
                answer=_pages_answer(case),
                expected=",".join(str(page) for page in case.row_pages),
            )
        )
    for row, text, kind in case.dividers:
        found.append(
            Claim(
                id=f"{case.key}.divider.{row}.{kind}",
                kind="divider",
                question=(
                    f"Is {_q(text)} printed above row {row + 1} as a {kind} divider — a line "
                    "between rows, not a row and not a heading?"
                ),
                answer=f"Row {row + 1} is separated by {_q(text)}, a {kind}.",
                expected=f"{row}|{flat(text)}|{kind}",
            )
        )
    for cell in case.cells:
        column = case.columns[cell.column] if cell.column < len(case.columns) else "?"
        found.append(
            Claim(
                id=f"{case.key}.cell.{cell.row}.{cell.column}",
                kind="cell",
                question=(
                    f"Row {cell.row + 1}, column {_q(column)}: does the printed cell "
                    f"{_cell_predicate(cell)}?"
                ),
                answer=_cell_answer(cell),
                expected=cell_spec(cell),
                row=cell.row,
                column=cell.column,
            )
        )
    return found


def all_claims() -> list[Claim]:
    return [claim for case in SHAPES for claim in claims(case)]


def claim_ids() -> list[str]:
    return [claim.id for claim in all_claims()]
