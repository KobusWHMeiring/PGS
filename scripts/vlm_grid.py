"""The grid the model proposes, turned into a `TableRead` the page can vouch for.

`scripts/eval_openrouter.py` is the runner: it renders pages, calls a model, and scores the answer
with S0's `mismatches()`. This module is everything between the model's JSON and that score — the
three mappings (verbatim lines, first/last anchors, line numbers), the printed-order bands, and the
one declared normalisation. It is separate from the runner because the repo's rule is that a file over
30 KB is two files (`build_principles.md` §II), and because the resolver is the part worth testing on
its own: it never touches a network, a key or a rasteriser.

Nothing here is imported by the application. It is an evaluation instrument, and requirement 10 says
the gate must never need an extractor — a pure function over committed page text is not one.
"""

from __future__ import annotations

from knowledge.tests.shape_fixtures import (
    TableRead,
    flat,
    normalised_lines,
)

#: A letter-spaced run is at least this many single letters in a row ('t h a n' is 4, 'o n e' is 3).
#: Kept for the report: it names what a page looks like when the normalisation is doing work.
_SPACED_RUN = 3


def despace(text: str) -> str:
    """The one declared normalisation: drop every space, so 'b o v i n e' and 'bovine' compare equal.

    The paper letter-spaces some words (Appendix 6a) and the extraction pass keeps that spacing, so the
    page's characters cannot supply the reviewed literal. The fixture says what to do about it: rejoin
    them, and *declare* it. Measured 2026-11-04 — the first version joined runs of single letters and
    produced 'bovineanimals', because the extraction renders the gap between two letter-spaced words
    exactly like the gap inside one. There is no boundary to find in the text; only a whole-string
    comparison is honest, and it is the reason this normalisation is recorded per cell.
    """
    return text.replace(" ", "")


def page_runs(case) -> dict[int, str]:
    """Each of the shape's printed pages as one flat line: the resolver's only source of text."""
    printed = dict(zip(case.pdf_pages, case.printed_pages))
    return {printed_page: flat(case_text(case, pdf_page)) for pdf_page, printed_page in printed.items()}


def case_text(case, pdf_page: int) -> str:
    from knowledge.tests.shape_fixtures import page_text

    return page_text(case, pdf_page)


def resolve(text: str, runs: dict[int, str], cursor: dict[int, int]) -> dict:
    """Resolve one quoted line against its page: `(ok, resolved, normalisation, page)`.

    Two steps, and the second only ever runs when the first fails:

    1. **exact** — the quote is a contiguous run of the page's flat text. The characters returned are
       the *page's*, sliced out of the run, so a quote with different whitespace cannot smuggle a
       character in.
    2. **letter_spacing** — the quote is a contiguous run once every space is dropped from both sides.
       The characters returned are then the **model's**, which is only admissible because the page's
       own characters prove the same sequence is there; the normalisation is recorded per cell.

    `cursor` carries the position reached per page, in the same space-free coordinate system, so a
    cell's lines must appear in printed order (requirement 3's second half) and a read cannot stitch a
    line from the top of the page into a cell at the bottom.
    """
    quoted = flat(text or "")
    if not quoted:
        return {"ok": True, "text": "", "normalisation": [], "page": None, "end": None}
    wanted = despace(quoted)
    if not wanted:
        return {"ok": True, "text": "", "normalisation": [], "page": None, "end": None}
    for page, run in runs.items():
        position = despace(run).find(wanted, cursor.get(page, 0))
        if position < 0:
            # Distinguish 'the page prints it, but above this cell' from 'the page does not print it':
            # both fail, and the reason is what tells a reviewer which one the model did.
            if despace(run).find(wanted) >= 0:
                return {
                    "ok": False,
                    "text": quoted,
                    "page": page,
                    "reason": "out of printed order on page %d" % page,
                }
            continue
        cursor[page] = position + len(wanted)
        end = position + len(wanted)
        if quoted in run:
            start = run.find(quoted)
            return {
                "ok": True,
                "text": run[start : start + len(quoted)],
                "normalisation": [],
                "page": page,
                "end": end,
            }
        return {"ok": True, "text": quoted, "normalisation": ["letter_spacing"], "page": page, "end": end}
    return {"ok": False, "text": quoted, "page": None, "reason": "not a contiguous run of any page"}


def read_from(proposal: dict, case, runs: dict[int, str]) -> tuple[TableRead, list[dict]]:
    """Map the model's proposal onto `TableRead`, and every cell that would not resolve.

    The grid is the model's: a cell the model leaves `""` is scored empty, because that is what it
    proposed. A cell whose line is not on the page is a violation and is reported with the quote, so a
    paraphrase is visible as a quote rather than as a low score.

    **The ordering constraint is per row, not per table.** Measured 2026-11-04 on the first run: a
    global cursor failed 65 cells on Appendix 7 alone, because a tall row's cells are interleaved in
    the extraction — the page prints line 1 of every column, then line 2 of every column, so a cell's
    second line comes *after* its neighbour's first. The rule that survives contact with the paper is
    that every character of row *k* precedes every character of row *k+1*: each row resolves inside the
    band the previous row left off at, each cell's own lines stay in order, and a row that starts
    above the band fails (requirement 3).
    """
    printed_for = dict(zip(range(1, len(case.pdf_pages) + 1), case.printed_pages))
    band: dict[int, int] = {}
    violations: list[dict] = []
    body: list[tuple[str, ...]] = []
    pages: list[int] = []
    for row_index, row in enumerate(proposal.get("rows") or []):
        if not isinstance(row, dict):
            violations.append({"row": row_index, "reason": "row is not an object"})
            continue
        image = row.get("page") or 1
        page = printed_for.get(image)
        if page is None:
            violations.append({"row": row_index, "reason": f"page {image!r} is not an image sent"})
            page = case.printed_pages[0]
        pages.append(page)
        start = band.get(page, 0)
        reach = start
        cells = []
        for column, cell in enumerate(row.get("cells") or []):
            here = start
            resolved, normalisation = [], set()
            for line in str(cell or "").splitlines():
                found = resolve(line, runs, {page: here})
                if not found["ok"]:
                    violations.append(
                        {
                            "row": row_index,
                            "column": column,
                            "quote": found["text"][:200],
                            "reason": found["reason"],
                        }
                    )
                    resolved.append(found["text"])
                    continue
                resolved.append(found["text"])
                normalisation.update(found["normalisation"])
                if found["end"] is not None:
                    here = found["end"]
                    reach = max(reach, found["end"])
            cells.append("\n".join(resolved))
        band[page] = reach
        body.append(tuple(cells))
    columns = tuple(flat(str(column)) for column in (proposal.get("columns") or []))
    dividers = []
    for divider in proposal.get("dividers") or []:
        if not isinstance(divider, dict):
            continue
        text = flat(str(divider.get("text") or ""))
        # A divider is printed *between* rows, so it is resolved against the whole page: banding it
        # would need the row order the model is being scored on.
        found = resolve(text, runs, {})
        if not found["ok"]:
            violations.append({"divider": text[:200], "reason": found["reason"]})
        dividers.append(
            (int(divider.get("before_row") or 0), text, str(divider.get("kind") or "qualifier"))
        )
    return (
        TableRead(columns=columns, rows=tuple(body), pages=tuple(pages), dividers=tuple(dividers)),
        violations,
    )


def has_letter_spacing(text: str) -> bool:
    """Whether the page prints a run of single letters ('t h a n') in this text."""
    run = 0
    for token in text.split(" "):
        if len(token) == 1 and token.isalpha():
            run += 1
            if run >= _SPACED_RUN:
                return True
        else:
            run = 0
    return False


def index_map(run: str) -> tuple[str, list[int]]:
    """The space-free form of a page run, and where each of its characters sits in the run."""
    chars: list[str] = []
    positions: list[int] = []
    for position, character in enumerate(run):
        if character != " ":
            chars.append(character)
            positions.append(position)
    return "".join(chars), positions


def slice_span(first: str, last: str, run: str, mapped, start: int = 0) -> dict:
    """The page's own characters between two anchors: `(ok, text, end)`.

    This is the arm's whole claim in one function. The model names a cell's first and last words; the
    characters between them are sliced out of the **extraction pass**, including the page's line
    breaks and spacing, so a cell can never hold a character the page did not print. What the model
    owns is the boundary, and a wrong boundary is visible as a wrong cell rather than as a wrong quote.

    `first` and `last` may overlap (a short cell is its own anchor), and the slice never runs backwards.
    """
    nospace, positions = mapped
    head = despace(flat(first))
    tail = despace(flat(last))
    if not head and not tail:
        return {"ok": True, "text": "", "end": None}
    if not head:
        head = tail
    begin = nospace.find(head, start)
    if begin < 0:
        return {"ok": False, "text": flat(first or last)[:200], "reason": "its first words are not on the page"}
    finish = begin + len(head)
    if tail:
        found = nospace.find(tail, begin)
        if found < 0:
            return {"ok": False, "text": flat(last)[:200], "reason": "its last words are not on the page"}
        finish = max(finish, found + len(tail))
    return {
        "ok": True,
        "text": run[positions[begin] : positions[finish - 1] + 1],
        "end": finish,
    }


def numbered_pages(case) -> tuple[str, dict[int, list[str]]]:
    """The shape's pages as numbered lines — what the `indices` mode is asked to point at.

    The text is the same extraction pass the other two modes are verified against, so a cell built
    from line numbers cannot contain a character the pass did not print. The numbering restarts at 1 on
    every page, because the model is looking at one image at a time.
    """
    printed = dict(zip(case.pdf_pages, case.printed_pages))
    numbered: dict[int, list[str]] = {}
    blocks: list[str] = []
    for image, (pdf_page, printed_page) in enumerate(printed.items(), start=1):
        lines = normalised_lines(case_text(case, pdf_page))
        numbered[printed_page] = lines
        blocks.append(f"PAGE {image} (printed page {printed_page})")
        blocks.extend(f"{index}: {line}" for index, line in enumerate(lines, start=1))
    return chr(10).join(blocks), numbered


def read_from_indices(
    proposal: dict, case, runs: dict[int, str], numbered: dict[int, list[str]]
) -> tuple[TableRead, list[dict]]:
    """Map a line-number proposal onto `TableRead`. No character here came from the model."""
    printed_for = dict(zip(range(1, len(case.pdf_pages) + 1), case.printed_pages))
    band: dict[int, int] = {}
    violations: list[dict] = []
    body: list[tuple[str, ...]] = []
    pages: list[int] = []

    def lines_of(page: int, indices) -> tuple[str, int | None]:
        source = numbered.get(page, [])
        taken, highest = [], None
        for value in indices or []:
            try:
                index = int(value)
            except (TypeError, ValueError):
                violations.append({"page": page, "index": value, "reason": "not a line number"})
                continue
            if not 1 <= index <= len(source):
                violations.append(
                    {"page": page, "index": index, "reason": f"the page prints {len(source)} lines"}
                )
                continue
            taken.append(source[index - 1])
            highest = index if highest is None else max(highest, index)
        return chr(10).join(taken), highest

    for row_index, row in enumerate(proposal.get("rows") or []):
        if not isinstance(row, dict):
            violations.append({"row": row_index, "reason": "row is not an object"})
            continue
        image = row.get("page") or 1
        page = printed_for.get(image)
        if page is None:
            violations.append({"row": row_index, "reason": f"page {image!r} is not an image sent"})
            page = case.printed_pages[0]
        pages.append(page)
        start = band.get(page, 0)
        reach = start
        cells = []
        for column, cell in enumerate(row.get("cells") or []):
            text, highest = lines_of(page, cell)
            if highest is not None:
                if highest < start:
                    violations.append(
                        {
                            "row": row_index,
                            "column": column,
                            "quote": text[:120],
                            "reason": "above the row band: these lines are printed earlier",
                        }
                    )
                reach = max(reach, highest)
            cells.append(text)
        band[page] = reach
        body.append(tuple(cells))

    columns = []
    for column in proposal.get("columns") or []:
        text, _ = lines_of(case.printed_pages[0], column if isinstance(column, list) else [column])
        columns.append(flat(text))
    dividers = []
    for divider in proposal.get("dividers") or []:
        if not isinstance(divider, dict):
            continue
        text, _ = lines_of(case.printed_pages[0], [divider.get("line")])
        dividers.append(
            (int(divider.get("before_row") or 0), text, str(divider.get("kind") or "qualifier"))
        )
    return (
        TableRead(
            columns=tuple(columns), rows=tuple(body), pages=tuple(pages), dividers=tuple(dividers)
        ),
        violations,
    )


def read_from_anchors(proposal: dict, case, runs: dict[int, str]) -> tuple[TableRead, list[dict]]:
    """Map an anchor proposal onto `TableRead`. Same banding as `read_from`, same violations."""
    printed_for = dict(zip(range(1, len(case.pdf_pages) + 1), case.printed_pages))
    mapped = {page: index_map(run) for page, run in runs.items()}
    band: dict[int, int] = {}
    violations: list[dict] = []
    body: list[tuple[str, ...]] = []
    pages: list[int] = []
    for row_index, row in enumerate(proposal.get("rows") or []):
        if not isinstance(row, dict):
            violations.append({"row": row_index, "reason": "row is not an object"})
            continue
        image = row.get("page") or 1
        page = printed_for.get(image)
        if page is None:
            violations.append({"row": row_index, "reason": f"page {image!r} is not an image sent"})
            page = case.printed_pages[0]
        pages.append(page)
        run = runs.get(page, "")
        start = band.get(page, 0)
        reach = start
        cells = []
        for column, cell in enumerate(row.get("cells") or []):
            if isinstance(cell, str):
                first = last = cell
            elif isinstance(cell, dict):
                first = str(cell.get("first") or "")
                last = str(cell.get("last") or first)
            else:
                first = last = ""
            found = slice_span(first, last, run, mapped.get(page, ("", [])), start)
            if not found["ok"]:
                violations.append(
                    {
                        "row": row_index,
                        "column": column,
                        "quote": found["text"],
                        "reason": found["reason"],
                    }
                )
                cells.append("")
                continue
            if found["end"] is not None:
                reach = max(reach, found["end"])
            cells.append(found["text"])
        band[page] = reach
        body.append(tuple(cells))
    columns = tuple(flat(str(column)) for column in (proposal.get("columns") or []))
    dividers = []
    for divider in proposal.get("dividers") or []:
        if not isinstance(divider, dict):
            continue
        text = flat(str(divider.get("text") or ""))
        found = resolve(text, runs, {})
        if not found["ok"]:
            violations.append({"divider": text[:200], "reason": found["reason"]})
        dividers.append(
            (int(divider.get("before_row") or 0), text, str(divider.get("kind") or "qualifier"))
        )
    return (
        TableRead(columns=columns, rows=tuple(body), pages=tuple(pages), dividers=tuple(dividers)),
        violations,
    )


