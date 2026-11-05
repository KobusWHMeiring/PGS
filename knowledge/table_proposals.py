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

    @property
    def where(self) -> str:
        """How a refusal names it: the arm, and which of its tables."""
        return f"{self.structure} table {self.index + 1}"


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ProposalError(f"{path.name}: not JSON ({error})") from None


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
    if columns:
        if len(columns) != width:
            raise ProposalError(
                f"{path.name} table {index + 1}: {len(columns)} reviewed column labels for "
                f"{width} columns. R2 attaches every cell to its printed column, so a label list "
                "that is short or long attaches a value to the wrong heading — the defect the "
                "declaration exists to prevent."
            )
        if any(not str(label).strip() for label in columns):
            raise ProposalError(
                f"{path.name} table {index + 1}: a reviewed column label is blank. A blank label "
                "is the Appendix 6a defect with a human's signature on it."
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
        rows = tuple(ProposedRow(tuple(row.get("cells") or ())) for row in raw.get("rows") or ())
        if not columns:
            raise ProposalError(
                f"{path.name} table {index + 1}: no columns. R2 needs the printed labels, and a "
                "table without them is Appendix 6a's shape — the one the format cannot express."
            )
        if not rows:
            raise ProposalError(f"{path.name} table {index + 1}: no rows")
        for number, row in enumerate(rows, 1):
            if len(row.cells) != len(columns):
                raise ProposalError(
                    f"{path.name} table {index + 1} row {number}: {len(row.cells)} cells for "
                    f"{len(columns)} columns. The emitter needs a rectangle: a short row is a cell "
                    "the arm dropped, and padding it would put a cell nobody read into the corpus."
                )
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
                columns=columns,
                rows=rows,
                extraction=extraction,
                structure=structure,
                processor=processor,
                profile=_profile(profile_raw, path, index, len(rows), len(columns)),
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
