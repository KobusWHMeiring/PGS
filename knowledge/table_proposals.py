"""The structure a document's tables were read from, as committed data (S3).

`INGESTION_ENGINE_PRD.md` §3.14 splits the problem in two and gives each half to a different tool:
**structure** from an extractor's layout read, **characters** from the page's own text layer, verified
per cell. This module is the first half, as data — one JSON per document under
`knowledge/proposals/`, written by `scripts/propose_tables.py` from a cached response and reviewed
only in the fields no extractor can produce (`<doc>.reviewed.json`).

**Why the lookup is by sha256 and not by `CORPUS_DOCUMENTS` key.** The point of the composite is that
a new document is data, not code (`build_principles.md` §I): a standard or group retarget must not
need a migration, an enum entry or a registry edit. A proposal names the bytes it describes, so the
generator finds it by the same digest every artefact header already carries — and a document nobody
has proposed simply has none, which is a smaller fact than an error.

**What this module deliberately cannot do.** It does not read a PDF, does not extract, does not
decide whether the arm was right, and does not hold a cell anyone typed. The emitter
(`scripts/table_blocks.py`) verifies every cell against the page and refuses the ones that are not
there; the harness (`knowledge/table_harness.py`) judges what the emitter wrote. Requirement 10's rule
is that the gate needs no extractor, and nothing here does.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from knowledge.corpus_tables import EXTRACTION_MODES

#: Where the committed proposals live. `directory` parameters exist for the tests, not for callers.
PROPOSAL_DIR = Path(__file__).resolve().parent / "proposals"


class ProposalError(ValueError):
    """A proposal that cannot describe a table. Never swallowed: a silent default here is a block
    whose structure nobody proposed."""


@dataclass(frozen=True)
class ProposedRow:
    """One row the arm returned: its cells in printed column order, whitespace as it came."""

    cells: tuple[str, ...]


@dataclass(frozen=True)
class ProposedDivider:
    """A heading printed *inside* the table, attached to the row beneath it.

    `before_row` is a 0-based row index, because that is where the paper prints it. The emitter
    resolves each one against the page (a divider is printed on a line of its own) and writes it as
    `<!-- row-divider: … -->`, so the block carries the label and R6 can claim it exactly once.
    """

    before_row: int
    text: str
    kind: str = "qualifier"


@dataclass(frozen=True)
class ProposedLocator:
    """The reviewed spelling one cell is *found* by, where the arm's transcription is not the page's.

    `row` is 0-based and `column` 1-based, matching `ProposedTail` and the refusal messages an
    operator reads. It is a locator and not a cell, in exactly the sense Appendix 2's continued rows
    are: the emitter still resolves it against the page and slices the page's own characters, so a
    reviewed locator cannot put a character the paper did not print into the corpus. It exists
    because an arm may transcribe rather than read — Appendix 7's Layout Parser read returns the
    degree sign as `\\(70^{\\circ}C\\)` where the page prints `70oC` (S5-c).
    """

    row: int
    column: int
    text: str


@dataclass(frozen=True)
class ProposedTail:
    """A cell's last words, printed at the top of the next page (requirement 4's own case).

    `row` is 0-based and `column` 1-based, matching the refusal messages an operator reads. `page`
    is the **printed** page the words are on, and `text` is the locator: the emitter verifies it is
    the first line printed on that page and refuses otherwise. A continuation that is inferred
    instead of declared is how `(iii) fermentation.` was once transcribed from printed 79.
    """

    row: int
    column: int
    page: int
    text: str


@dataclass(frozen=True)
class ProposedProfile:
    """The block fields no extractor produces — `reviewed.json`'s half of the composite.

    Every one is reviewed data: the renderer infers none of them, and the generator writes them
    through unchanged so that regenerating an artefact is silent against the review that produced it
    (`knowledge/proposals/README.md`).
    """

    legend: str = ""
    layout: str = "grid"
    titles: tuple[str, ...] = ()
    fee_labels: tuple[str, ...] = ()
    branch: int | None = None
    #: The labels the reader prints, when the paper's header is not one line the emitter can slice
    #: (Appendix 6a prints two levels of type across four lines). Reviewed wording, flat.
    columns: tuple[str, ...] = ()
    #: Printed page -> where each printed column starts on that page's line grid. A table whose
    #: cells share every printed line cannot be read without it: `TABLE_BANDS` measured Appendix
    #: 2's one boundary (declared as the two-column shorthand, `{76: 60}`), and Appendix 7's four
    #: columns need every left edge (`{88: [0, 4, 32, 60, 89]}`, the gutter first). The emitter
    #: refuses a cell whose words cross a boundary, and refuses a row on a page nobody measured.
    band: dict[int, tuple[int, ...]] = field(default_factory=dict)
    #: How many of the arm's leading columns are the printed **row number** rather than a column the
    #: reader prints. Appendix 7's gutter is one column, and it becomes the row's label (a citation's
    #: `heading_path`) instead of a column of numbers beside every cell (S5-c).
    gutter: int = 0
    #: The cells the arm transcribed rather than read, and the reviewed spelling they are found by.
    locators: tuple[ProposedLocator, ...] = ()
    #: The headings printed inside the table, in printed order.
    dividers: tuple[ProposedDivider, ...] = ()
    #: A cell that continues onto the next page, declared rather than inferred.
    tails: tuple[ProposedTail, ...] = ()
    #: What the reader prints where a cell is empty, for a table whose silence is a reviewed fact
    #: (Appendix 2: `no condition printed`). Empty means an empty cell renders as nothing, which is
    #: what every other table wants.
    silence: str = ""

    def __post_init__(self) -> None:
        """Normalise the two-column band shorthand to the internal invariant.

        `reviewed.json` declares a two-column table's boundary as one number (`{76: 60}`), which
        `_band` widens to `(0, 60)`; a caller that builds a profile directly gets the same
        treatment here, so every reader of `profile.band` sees one shape — the left edge of every
        printed column.
        """
        if any(isinstance(cut, int) for cut in self.band.values()):
            object.__setattr__(
                self,
                "band",
                {page: (0, cut) if isinstance(cut, int) else cut for page, cut in self.band.items()},
            )



@dataclass(frozen=True)
class ProposedTable:
    """One table: the arm's grid, the pages it was read from, and the pass its cells came from."""

    index: int
    pdf_pages: tuple[int, ...]
    columns: tuple[str, ...]
    rows: tuple[ProposedRow, ...]
    extraction: str
    structure: str
    processor: str
    profile: ProposedProfile = field(default_factory=ProposedProfile)

    #: Where this table's structure came from, when it is not the file's arm read: a table whose
    #: rows were promoted from a review (`--continue`) names that review, because the banner's
    #: `structure` describes the arm that read the *other* pages and claiming otherwise is a false
    #: banner (`INGESTION_ENGINE_S5_PLAN.md` §4).
    continued_from: str = ""

    @property
    def where(self) -> str:
        """How a refusal names it: the arm (or the review), and which of its tables."""
        return f"{self.continued_from or self.structure} table {self.index + 1}"

    def band_for(self, printed: int | None) -> tuple[int, ...] | None:
        """Where each printed column starts on one printed page, or None."""
        return None if printed is None else self.profile.band.get(printed)

    def locator_for(self, row: int, column: int) -> str | None:
        """The reviewed locator for one cell, or None when the arm's own text is used."""
        for locator in self.profile.locators:
            if locator.row == row and locator.column == column:
                return locator.text
        return None

    def divider_cells(self) -> dict[int, tuple[ProposedDivider, ...]]:
        """Row index -> the dividers printed immediately above it, in printed order."""
        out: dict[int, list[ProposedDivider]] = {}
        for divider in self.profile.dividers:
            out.setdefault(divider.before_row, []).append(divider)
        return {row: tuple(entries) for row, entries in out.items()}

    def tail_for(self, row: int, column: int) -> ProposedTail | None:
        """The declared continuation of one cell, or None."""
        for tail in self.profile.tails:
            if tail.row == row and tail.column == column:
                return tail
        return None


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ProposalError(f"{path.name}: not JSON ({error})") from None


def _band(raw: object, path: Path, index: int, width: int) -> dict[int, tuple[int, ...]]:
    """`{"76": 60}` or `{"88": [0, 4, 32, 60, 89]}` -> the left edge of every printed column.

    A band says where a line's columns start, and a table whose cells share every printed line
    cannot be sliced without it. Two spellings, because the tables have two shapes:

    * a **two-column** table declares one boundary (`{76: 60}`) — where the second column starts,
      which is the number `TABLE_BANDS` measured and S5-b declared;
    * a **wider** table declares every column's left edge, in printed order, and the first is 0 —
      Appendix 7 needs all four (`{88: [0, 4, 32, 60, 89]}`) because `Air,` is printed beside
      `using gaseous oxygen` and only a boundary can say which column it belongs to (S5-c).

    A list on a two-column table is refused rather than silently accepted: two spellings for one
    number is a declaration a reviewer cannot diff against the measurement.
    """
    if not raw:
        return {}
    out: dict[int, tuple[int, ...]] = {}
    for page, cut in dict(raw).items():
        try:
            printed = int(page)
        except (TypeError, ValueError):
            raise ProposalError(
                f"{path.name} table {index + 1}: `band` wants printed page -> the column's left "
                f"edge (or one edge per column), and {page!r} is not a whole number."
            ) from None
        if isinstance(cut, (list, tuple)):
            if width == 2:
                raise ProposalError(
                    f"{path.name} table {index + 1}: a two-column table declares one boundary "
                    f"(`band: {{'{printed}': 60}}`), not a list. Two spellings for one number is "
                    "a declaration nobody can diff against the measurement."
                )
            try:
                starts = tuple(int(value) for value in cut)
            except (TypeError, ValueError):
                raise ProposalError(
                    f"{path.name} table {index + 1}: the band on printed page {printed} is not a "
                    "list of whole numbers."
                ) from None
            if len(starts) != width:
                raise ProposalError(
                    f"{path.name} table {index + 1}: the band on printed page {printed} names "
                    f"{len(starts)} column(s) and the arm read {width}. Every cell is sliced "
                    "between its column's left edge and the next, so a short list leaves the last "
                    "column no boundary and a long one cuts a column in two."
                )
            if starts[0] != 0:
                raise ProposalError(
                    f"{path.name} table {index + 1}: the band on printed page {printed} starts at "
                    f"column {starts[0]}. The first column is the leftmost characters of the "
                    "printed line, so a list that does not start at 0 is missing one."
                )
            for before, after in zip(starts, starts[1:]):
                if after <= before:
                    raise ProposalError(
                        f"{path.name} table {index + 1}: the band on printed page {printed} "
                        f"names column edges {list(starts)}, which do not move rightwards. A "
                        "column with no characters is a cell nobody can read."
                    )
            out[printed] = starts
            continue
        try:
            at = int(cut)
        except (TypeError, ValueError):
            raise ProposalError(
                f"{path.name} table {index + 1}: `band` wants printed page -> column, and "
                f"{page!r}: {cut!r} is not a whole number (or one per column)."
            ) from None
        if width != 2:
            raise ProposalError(
                f"{path.name} table {index + 1}: a single `band` is the boundary between a "
                f"table's two columns, and this table has {width}. A boundary on a wider table "
                "would silently cut the third column into the second; name every column's left "
                "edge instead."
            )
        if at <= 0:
            raise ProposalError(
                f"{path.name} table {index + 1}: the band on printed page {printed} starts at "
                f"column {at}. A boundary at or before column 0 would leave the first cell no "
                "characters at all."
            )
        out[printed] = (0, at)
    return out


def _gutter(raw: object, path: Path, index: int, width: int) -> int:
    """How many of the arm's leading columns are the printed row number — 0 or 1.

    A gutter is not a column the reader prints: it is where the paper puts the row's number, and a
    citation files the row under it. More than one is refused because the block has one row label,
    and a table that needed two of the arm's columns for it is a table nobody has read yet.
    """
    try:
        gutter = int(raw or 0)
    except (TypeError, ValueError):
        raise ProposalError(
            f"{path.name} table {index + 1}: `gutter: {raw!r}` is not a whole number of columns."
        ) from None
    if gutter not in (0, 1):
        raise ProposalError(
            f"{path.name} table {index + 1}: `gutter: {gutter}` of {width} columns. A row has one "
            "label, so the printed row number is at most one of the arm's columns."
        )
    if gutter and width - gutter < 2:
        raise ProposalError(
            f"{path.name} table {index + 1}: `gutter: {gutter}` leaves {width - gutter} column "
            "for the arm's {width}. A table that is only a row number is a list, not a table."
        )
    return gutter


def _locators(
    raw: object, path: Path, index: int, rows: int, width: int
) -> tuple[ProposedLocator, ...]:
    """The reviewed spellings for cells the arm transcribed rather than read.

    Each names a cell that exists and carries words the emitter must find on the page — the same
    refusal a cell with no locator gets, applied to a locator a person wrote. It replaces the arm's
    text; it never supplies characters, which is why a locator naming nothing is refused here.
    """
    out: list[ProposedLocator] = []
    seen: set[tuple[int, int]] = set()
    for entry in raw or ():
        entry = dict(entry)
        text = " ".join(str(entry.get("text", "")).split())
        try:
            row, column = int(entry["row"]), int(entry["column"])
        except (KeyError, TypeError, ValueError):
            raise ProposalError(
                f"{path.name} table {index + 1}: a `locator` needs `row`, `column` and `text`."
            ) from None
        if not 0 <= row < rows:
            raise ProposalError(
                f"{path.name} table {index + 1}: a locator names row {row} of {rows}."
            )
        if not 1 <= column <= width:
            raise ProposalError(
                f"{path.name} table {index + 1}: a locator names column {column} of {width}."
            )
        if not text:
            raise ProposalError(
                f"{path.name} table {index + 1}: the locator on row {row} column {column} has no "
                "words. A locator that names nothing cannot be found on the page."
            )
        if (row, column) in seen:
            raise ProposalError(
                f"{path.name} table {index + 1}: two locators for row {row}, column {column}. "
                "One cell is found one way."
            )
        seen.add((row, column))
        out.append(ProposedLocator(row=row, column=column, text=text))
    return tuple(out)


def _dividers(raw: object, path: Path, index: int, rows: int) -> tuple[ProposedDivider, ...]:
    """The printed headings inside the table, refused unless each names a row beneath it."""
    out: list[ProposedDivider] = []
    previous = -1
    for entry in raw or ():
        entry = dict(entry)
        before = entry.get("before")
        text = " ".join(str(entry.get("text", "")).split())
        kind = str(entry.get("kind", "qualifier"))
        try:
            before = int(before)
        except (TypeError, ValueError):
            raise ProposalError(
                f"{path.name} table {index + 1}: a divider names `before: {entry.get('before')!r}`, "
                "which is not a row index."
            ) from None
        if not 0 <= before < rows:
            raise ProposalError(
                f"{path.name} table {index + 1}: a divider is attached to row {before} of {rows}. "
                "A divider qualifies the row beneath it; one that names no row is a label the "
                "reader would lose."
            )
        if before < previous:
            raise ProposalError(
                f"{path.name} table {index + 1}: the dividers are not in printed order (row "
                f"{before} follows row {previous}). The block writes them where they are read."
            )
        if not text:
            raise ProposalError(
                f"{path.name} table {index + 1}: a divider before row {before} is blank."
            )
        if kind not in ("part", "qualifier"):
            raise ProposalError(
                f"{path.name} table {index + 1}: divider kind {kind!r} is not `part` or "
                "`qualifier`. The reader draws the two differently, so a third word would be "
                "silently one of them."
            )
        out.append(ProposedDivider(before_row=before, text=text, kind=kind))
        previous = before
    return tuple(out)


def _tails(raw: object, path: Path, index: int, rows: int, width: int) -> tuple[ProposedTail, ...]:
    """The declared cross-page continuations, refused unless each names a cell that exists."""
    out: list[ProposedTail] = []
    seen: set[tuple[int, int]] = set()
    for entry in raw or ():
        entry = dict(entry)
        text = " ".join(str(entry.get("text", "")).split())
        try:
            row, column, page = int(entry["row"]), int(entry["column"]), int(entry["page"])
        except (KeyError, TypeError, ValueError):
            raise ProposalError(
                f"{path.name} table {index + 1}: a `tail` needs `row`, `column`, `page` and "
                "`text` as whole numbers and words."
            ) from None
        if not 0 <= row < rows:
            raise ProposalError(
                f"{path.name} table {index + 1}: a tail names row {row} of {rows}."
            )
        if not 1 <= column <= width:
            raise ProposalError(
                f"{path.name} table {index + 1}: a tail names column {column} of {width}."
            )
        if not text:
            raise ProposalError(
                f"{path.name} table {index + 1}: the tail on row {row} has no words. A "
                "continuation that names nothing cannot be found on the page."
            )
        if (row, column) in seen:
            raise ProposalError(
                f"{path.name} table {index + 1}: two tails for row {row}, column {column}. "
                "One cell continues onto one page."
            )
        seen.add((row, column))
        out.append(ProposedTail(row=row, column=column, page=page, text=text))
    return tuple(out)


def _profile(raw: dict, path: Path, index: int, rows: int, width: int) -> ProposedProfile:
    titles = tuple(raw.get("titles", ()) or ())
    fee_labels = tuple(raw.get("fee_labels", ()) or ())
    for name, values in (("titles", titles), ("fee_labels", fee_labels)):
        if values and len(values) != rows:
            raise ProposalError(
                f"{path.name} table {index + 1}: {len(values)} {name} for {rows} rows. The block "
                "format pairs them one-to-one, so a short list would silently shift every label "
                "onto the row above."
            )
    columns = tuple(raw.get("columns", ()) or ())
    gutter = _gutter(raw.get("gutter"), path, index, width)
    if columns:
        # **The gutter is not a column the reader prints.** It is the paper's row number, written as
        # the row's label, so the reviewed labels are one per *printed* column — `width - gutter`.
        printed_columns = width - gutter
        if len(columns) != printed_columns:
            raise ProposalError(
                f"{path.name} table {index + 1}: {len(columns)} reviewed column labels for "
                f"{printed_columns} printed columns"
                + (f" ({width} read by the arm, {gutter} of them the row number)" if gutter else "")
                + ". R2 attaches every cell to its printed column, so a label list that is short "
                "or long attaches a value to the wrong heading — the defect the declaration "
                "exists to prevent."
            )
        if any(not str(label).strip() for label in columns):
            raise ProposalError(
                f"{path.name} table {index + 1}: a reviewed column label is blank. A blank label "
                "is the Appendix 6a defect with a human's signature on it."
            )
    elif gutter:
        raise ProposalError(
            f"{path.name} table {index + 1}: `gutter: {gutter}` means the arm's first column is "
            "the printed row number, so the columns the reader prints are reviewed labels — a "
            "blank arm header cannot supply them."
        )
    branch = raw.get("branch")
    if branch is not None and not 0 <= int(branch) < rows:
        raise ProposalError(
            f"{path.name} table {index + 1}: `branch: {branch}` names no row of {rows}. A fork that "
            "points at nothing renders two paths that are the same path."
        )
    layout = raw.get("layout", "grid")
    from knowledge.corpus_tables import TABLE_LAYOUTS

    if layout not in TABLE_LAYOUTS:
        raise ProposalError(
            f"{path.name} table {index + 1}: `layout: {layout}` is not a shape the reader draws "
            f"({', '.join(TABLE_LAYOUTS)})."
        )
    return ProposedProfile(
        legend=str(raw.get("legend", "")),
        layout=layout,
        titles=titles,
        fee_labels=fee_labels,
        branch=None if branch is None else int(branch),
        columns=tuple(str(label) for label in columns),
        band=_band(raw.get("band"), path, index, width),
        gutter=gutter,
        locators=_locators(raw.get("locators"), path, index, rows, width),
        dividers=_dividers(raw.get("dividers"), path, index, rows),
        tails=_tails(raw.get("tails"), path, index, rows, width),
        silence=" ".join(str(raw.get("silence", "")).split()),
    )


def _tables(payload: dict, path: Path, reviewed: dict | None) -> tuple[ProposedTable, ...]:
    structure = str(payload.get("structure", ""))
    processor = str(payload.get("processor", ""))
    if not structure or not processor:
        raise ProposalError(
            f"{path.name}: no `structure`/`processor` banner. A proposal whose arm is unknown is a "
            "structure nobody can re-derive — regenerate it with `scripts/propose_tables.py`."
        )
    raw_tables = payload.get("tables") or []
    if not raw_tables:
        raise ProposalError(f"{path.name}: no tables. An empty proposal is not a table with no rows.")
    reviews = (reviewed or {}).get("tables") or []
    if reviews and len(reviews) != len(raw_tables):
        raise ProposalError(
            f"{path.name}: {len(raw_tables)} table(s) and the review names {len(reviews)}. The review "
            "pairs with the structure by index, so a short list would attach one table's legend to "
            "another."
        )
    out: list[ProposedTable] = []
    for index, raw in enumerate(raw_tables):
        columns = tuple(raw.get("columns") or ())
        profile_raw = reviews[index] if reviews else {}
        # **A continued table has no arm columns.** Its rows were read by a person from the paper,
        # so the labels are in the review (`reviewed.json`) and the structure file does not pretend
        # an extractor produced them (`scripts/propose_tables.py --continue`).
        reviewed_columns = tuple(str(label) for label in profile_raw.get("columns") or ())
        width = len(columns) or len(reviewed_columns)
        rows = tuple(ProposedRow(tuple(row.get("cells") or ())) for row in raw.get("rows") or ())
        if not columns and not reviewed_columns:
            raise ProposalError(
                f"{path.name} table {index + 1}: no columns and no reviewed labels. R2 needs the "
                "printed labels, and a table without them is Appendix 6a's shape — the one the "
                "format cannot express."
            )
        if not rows:
            raise ProposalError(f"{path.name} table {index + 1}: no rows")
        for number, row in enumerate(rows, 1):
            if len(row.cells) != width:
                raise ProposalError(
                    f"{path.name} table {index + 1} row {number}: {len(row.cells)} cells for "
                    f"{width} columns. The emitter needs a rectangle: a short row is a cell "
                    "the arm dropped, and padding it would put a cell nobody read into the corpus."
                )
        continued_from = str(raw.get("continued_from", ""))
        pages = tuple(int(page) for page in raw.get("pdf_pages") or ())
        if not pages:
            raise ProposalError(
                f"{path.name} table {index + 1}: no `pdf_pages`, so the row's page cannot be traced."
            )
        extraction = str(raw.get("extraction", ""))
        if extraction not in EXTRACTION_MODES:
            raise ProposalError(
                f"{path.name} table {index + 1}: `extraction: {extraction}` is not an extraction "
                f"mode ({', '.join(EXTRACTION_MODES)}). The gate judges every cell against this "
                "rendering, so a proposal cannot leave it out."
            )
        profile_raw = reviews[index] if reviews else {}
        out.append(
            ProposedTable(
                index=index,
                pdf_pages=pages,
                columns=columns or reviewed_columns,
                rows=rows,
                extraction=extraction,
                structure=structure,
                processor=processor,
                continued_from=continued_from,
                profile=_profile(profile_raw, path, index, len(rows), width),
            )
        )
    return tuple(out)


def proposals_for(sha256: str, directory: Path | None = None) -> tuple[ProposedTable, ...]:
    """In: a PDF's sha256. Out: the tables that document's proposal describes, or `()`.

    In:  `sha256` — the digest the artefact header records; `directory` — the committed proposals
         (tests only).
    Out: one `ProposedTable` per table, in document order, with the reviewed block fields merged in.
    Side Effects: none — it reads two small JSON files per document.
    Fails: `ProposalError` for a malformed structure or review, and for **two files claiming one
         digest**: a proposal is found by the bytes it describes, so a collision means the tree
         cannot say which structure built this artefact.
    """
    directory = Path(directory) if directory is not None else PROPOSAL_DIR
    if not directory.is_dir():
        return ()
    matches: list[Path] = []
    for path in sorted(directory.glob("*.structure.json")):
        if _load(path).get("sha256") == sha256:
            matches.append(path)
    if not matches:
        return ()
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise ProposalError(
            f"{len(matches)} proposals claim the same document ({names}). A proposal is found by the "
            "bytes it describes, so two of them is a tree that cannot say which structure built it."
        )
    structure_path = matches[0]
    payload = _load(structure_path)
    reviewed_path = structure_path.with_name(
        structure_path.name.replace(".structure.json", ".reviewed.json")
    )
    reviewed = _load(reviewed_path) if reviewed_path.exists() else None
    return _tables(payload, structure_path, reviewed)
