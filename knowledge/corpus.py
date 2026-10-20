"""The canonical corpus format — document text as reviewed data (D53).

Every other part of ingestion trusts this module. A `*.md` file under
`knowledge/corpus/` is *the* text of a governed document: the chunker slices it, the
chatbot quotes it, and a human has read it. The PDF is still the source of truth, but it
is read **once**, by `scripts/build_corpus.py`, and the result is reviewed in a diff
instead of being re-derived by layout heuristics on every ingest.

That is a deliberate inversion of D46/D51/D52. Those decisions kept repairing the
extractor (`columns.py`, `tables.py`, `reflow.py`) because the extractor was on the
runtime path: every layout defect was a production bug in the chatbot. Here the
extractor becomes a generator that runs per *edition*, and the reviewed artefact — not
the heuristic — is what ships.

The format is Markdown with machine annotations, because the two audiences are a human
with a red pen and a parser with no opinions:

    <!-- corpus
    doc_key: bpp
    source: pgs_docs/Basic Production Principles_ENG_PRINT.pdf
    sha256: 9f3a…
    generator: knowledge corpusgen v1
    -->
    <!-- page: 3 printed: none -->
    ## INTRODUCTION

    The terms of reference for these principles …

Rules the reader enforces, because each one is a silent corruption otherwise:

1. **A page marker before any text.** `<!-- page: N printed: M -->` — `N` is the PDF
   page index (1-based) and `M` the number the document prints, or `none` (D42: the BPP
   prints no page numbers). A block with no page is a block whose quote cannot be traced
   to paper, so it is an error, not a default.
2. **Provenance is per block, not per section.** A section may span pages; the page marker
   in force when a block starts is that block's page. `ParsedSection.page` stays what D42
   says it is — the *printed* page of the section's heading.
3. **A heading is `#`-level Markdown.** Depth is the number of `#`s and exists only to
   build `heading_path`; it is never part of a citation. `section_ref` comes from an
   optional `<!-- ref: S20.1.1 -->` annotation immediately before the heading, so the
   reader needs no per-document scheme — BPP has none, SAOSO emits one.
4. **Everything else is text, verbatim.** Blank lines included: they are the chunker's
   paragraph boundaries, and a reader that "tidies" them changes chunk boundaries.

Reviewed edits are *not* annotated in the file. The artefact says what the document says;
which lines needed a human is recorded as data in `knowledge/corpus.py` (`CORPUS_EDITS`),
so the traceability test can prove the edit was necessary (its `original` is on that
page) and applied (its `replacement` is in the file). An edit nobody can justify is a
failing test, not a comment.

Pure: text in, `ParsedSection`s out. No Django, no PDF, no clock, no network.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from knowledge.sections import ParsedSection, slug


class CorpusFormatError(ValueError):
    """The artefact is malformed. Never swallowed: a silent default loses provenance."""


#: `<!-- page: 12 printed: 11 -->` — PDF page and the number the document prints.
PAGE = re.compile(r"^<!--\s*page:\s*(\d+)\s+printed:\s*(\d+|none)\s*-->\s*$")

#: `<!-- ref: S20.1.1 -->` — the citation for the heading that follows.
REF = re.compile(r"^<!--\s*ref:\s*(\S.*?)\s*-->\s*$")

#: `<!-- corpus` … `-->` at the top of the file.
HEADER_OPEN = re.compile(r"^<!--\s*corpus\s*$")
HEADER_CLOSE = re.compile(r"^-->\s*$")
HEADER_FIELD = re.compile(r"^\s*([a-z0-9_]+):\s*(.*?)\s*$")

#: `## INTRODUCTION`
HEADING = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$")

#: A comment that *looks* like an annotation. It must parse strictly, or it is an error:
#: silently ignoring `<!-- page: three -->` would drop the provenance of every block
#: after it.
ANNOTATION = re.compile(r"^<!--\s*(corpus|page|ref)\b")

#: Any other HTML comment: a reviewer's note. Ignored, and never emitted as text.
COMMENT = re.compile(r"^<!--.*-->\s*$")

REQUIRED_HEADER_FIELDS = ("doc_key", "source", "sha256", "generator")


@dataclass(frozen=True)
class Block:
    """One paragraph of document text with the page it came from.

    `page` is the **PDF** page (provenance: what the traceability test checks against);
    `printed` is the number the document shows the reader (D42). They are different
    things and confusing them is how a citation points at the wrong paper.
    """

    page: int
    printed: int | None
    text: str


@dataclass(frozen=True)
class CorpusDocument:
    """One reviewed document: its metadata, its text blocks and its sections."""

    doc_key: str
    source: str
    sha256: str
    generator: str
    sections: tuple[ParsedSection, ...]
    blocks: tuple[Block, ...]
    path: Path | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def digest(self) -> str:
        """sha256 of the artefact file — recorded on ingest so drift is visible."""
        if self.path is None or not self.path.exists():  # pragma: no cover - tests
            return ""
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    @property
    def text(self) -> str:
        """The whole document as one string, sections in order — what gets chunked."""
        return "\n\n".join(section.text for section in self.sections)


def _parse_header(lines: list[str], index: int) -> tuple[dict[str, str], int]:
    """Read the `<!-- corpus … -->` header. Returns the fields and the next line index."""
    if not lines or not HEADER_OPEN.match(lines[0]):
        raise CorpusFormatError(
            "expected a `<!-- corpus` header on line 1; without it the artefact has no "
            "source PDF and no sha256, so nothing downstream can tell where it came from"
        )
    fields: dict[str, str] = {}
    while index < len(lines):
        line = lines[index]
        index += 1
        if HEADER_CLOSE.match(line):
            break
        match = HEADER_FIELD.match(line)
        if not match:
            raise CorpusFormatError(f"header line {index} is not `key: value`: {line!r}")
        fields[match.group(1)] = match.group(2)
    else:  # pragma: no cover - unreachable without a broken file
        raise CorpusFormatError("the header comment is never closed with `-->`")
    missing = [name for name in REQUIRED_HEADER_FIELDS if not fields.get(name)]
    if missing:
        raise CorpusFormatError(f"header is missing {', '.join(missing)}")
    return fields, index


def parse_blocks(text: str) -> CorpusDocument:
    """Parse an artefact's text into sections and page-attributed blocks.

    In:  `text` — the contents of a `knowledge/corpus/*.md` file.
    Out: a `CorpusDocument`. Sections partition the text: a section's `text` is its
         heading plus every body line up to the next heading, exactly as written.
    Fails: `CorpusFormatError` for a missing header, an unparseable page marker, or body
         text before the first page marker.
    """
    lines = text.split("\n")
    fields, index = _parse_header(lines, 1)

    sections: list[ParsedSection] = []
    blocks: list[Block] = []
    stack: list[tuple[int, str]] = []
    pending_ref: str | None = None
    page: int | None = None
    printed: int | None = None
    current: dict | None = None
    new_block = True

    def flush() -> None:
        if current is None:
            return
        body = current["body"]
        while body and not body[-1].strip():
            body.pop()
        sections.append(
            ParsedSection(
                section_ref=current["ref"],
                text="\n".join([current["heading"], *body]).strip(),
                heading_path=(
                    " > ".join(title for _, title in stack) or current["title"]
                ),
                page=current["page"],
                anchor=slug(current["title"]),
            )
        )

    while index < len(lines):
        line = lines[index]
        index += 1

        marker = PAGE.match(line)
        if marker:
            page = int(marker.group(1))
            printed = None if marker.group(2) == "none" else int(marker.group(2))
            continue

        ref = REF.match(line)
        if ref:
            if current is not None and not current["body"]:
                raise CorpusFormatError(
                    f"a `ref:` annotation must come before its heading, not after "
                    f"{current['heading']!r}"
                )
            pending_ref = ref.group(1)
            continue

        heading = HEADING.match(line)
        if heading:
            flush()
            depth = len(heading.group(1))
            title = heading.group(2)
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, title))
            if page is None:
                raise CorpusFormatError(
                    f"heading {title!r} has no page marker before it; every block must "
                    "be traceable to a PDF page"
                )
            new_block = True
            current = {
                "ref": pending_ref,
                "heading": line.rstrip(),
                "title": title,
                "page": printed,
                "body": [],
            }
            pending_ref = None
            continue

        if COMMENT.match(line):
            if ANNOTATION.match(line):
                raise CorpusFormatError(
                    f"line {index}: malformed annotation, expected "
                    f"`<!-- page: N printed: M -->` or `<!-- ref: X -->`: {line!r}"
                )
            continue  # a reviewer's note, never text

        if line.lstrip().startswith("<!--"):
            raise CorpusFormatError(f"line {index}: malformed comment: {line!r}")

        if current is None:
            if line.strip():
                raise CorpusFormatError(
                    f"line {index} has text before any heading: {line!r}"
                )
            continue

        current["body"].append(line)
        if not line.strip():
            new_block = True
            continue
        if page is None:
            raise CorpusFormatError(
                f"block on line {index} has no page marker: {line[:60]!r}"
            )
        if new_block or not blocks or blocks[-1].page != page or blocks[-1].printed != printed:
            blocks.append(Block(page=page, printed=printed, text=line))
        else:
            # Consecutive non-blank lines are one block; a blank line ends it.
            previous = blocks[-1]
            blocks[-1] = Block(
                page=previous.page,
                printed=previous.printed,
                text=f"{previous.text}\n{line}",
            )
        new_block = False

    flush()
    if not sections:
        raise CorpusFormatError("the artefact contains no headings, so no sections")
    return CorpusDocument(
        doc_key=fields["doc_key"],
        source=fields["source"],
        sha256=fields["sha256"],
        generator=fields["generator"],
        sections=tuple(sections),
        blocks=tuple(blocks),
        extra={
            key: value
            for key, value in fields.items()
            if key not in REQUIRED_HEADER_FIELDS
        },
    )


def load_document(path: str | Path) -> CorpusDocument:
    """Load one artefact from disk. In: a `knowledge/corpus/*.md` path."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    document = parse_blocks(text)
    return CorpusDocument(
        doc_key=document.doc_key,
        source=document.source,
        sha256=document.sha256,
        generator=document.generator,
        sections=document.sections,
        blocks=document.blocks,
        path=path,
        extra=document.extra,
    )


def flat(text: str) -> str:
    """Exactly what `audit_citations` compares: whitespace-normalised text."""
    return " ".join((text or "").split())


__all__ = [
    "Block",
    "CORPUS_EDITS",
    "CorpusDocument",
    "CorpusFormatError",
    "CorpusEdit",
    "flat",
    "load_document",
    "parse_blocks",
]


@dataclass(frozen=True)
class CorpusEdit:
    """One reviewed correction, and the evidence that it was necessary.

    In:  `page` — the PDF page; `original` — the text the *PDF* produces there (the
         defact being repaired); `replacement` — what the artefact now says;
         `reason` — how the defect arose, in one sentence, so the generator can be
         improved rather than the symptom patched forever.
    Out: data consumed by the traceability test. `original` must be found on `page`, and
         `replacement` must be found in the artefact, which is what stops this table
         becoming a place to hide text nobody checked.
    """

    page: int
    original: str
    replacement: str
    reason: str
    #: `replace` (a correction), `drop` (furniture removed) or `move` (the same text at a
    #: new position). The distinction matters to the coverage test: a move changes no
    #: character, so counting it as a substitution would invent text.
    kind: str = "replace"


#: Reviewed corrections, per corpus document. **Every entry is a generator defect that
#: was found by reading the artefact.** Keeping them here rather than as comments in the
#: Markdown is deliberate: a comment cannot fail a test, and this table can.
CORPUS_EDITS: dict[str, tuple[CorpusEdit, ...]] = {
    "bpp": (
        CorpusEdit(
            kind="drop",
            page=3,
            original="02",
            replacement="",
            reason=(
                "The printed page number is furniture. `-raw` puts it on its own line "
                "before the body and `-layout` glues it to the footnote's last line; "
                "either way it is not text."
            ),
        ),
        CorpusEdit(
            kind="move",
            page=4,
            original=(
                "must be preferably composted 2 Sustainable means: meeting the needs of "
                "the present without compromising the ability of future generations to "
                "meet their own needs; conserving an ecological balance by avoiding "
                "depletion or destruction of natural resources.(IFOAM: Organics "
                "International 3.0)"
            ),
            replacement=(
                "land available will not be allowed. 2 Sustainable means: meeting the "
                "needs of the present without compromising the ability of future "
                "generations to meet their own needs; conserving an ecological balance "
                "by avoiding depletion or destruction of natural resources.(IFOAM: "
                "Organics International 3.0)"
            ),
            reason=(
                "`-raw` emits footnote 2 at the end of page 4, which is inside the "
                "manure sentence (`must be preferably composted` / footnote / `prior to "
                "application`), so the BPP's most-quoted sentence was unquotable. The "
                "footnote moved to the bullet that carries its marker."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=8,
            original="ii. Preventativemethods(disruption,",
            replacement="ii. Preventative methods (disruption,",
            reason=(
                "The PDF's text layer has no spaces in this line, so no extractor can "
                "recover them; read from the page, it is two words and a parenthesis."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=8,
            original=(
                "The Principle Of Health. The Principle Of Ecology. The Principle Of "
                "Fairness. The Principle Of Care."
            ),
            replacement="",
            reason=(
                "The brochure prints the four-principle strip on pages 1, 6, 8 and 10. "
                "The first occurrence (page 6) carries the content and sits at a "
                "paragraph boundary; the repeats interrupt numbered lists, so they are "
                "dropped rather than moved."
            ),
        ),
        CorpusEdit(
            kind="drop",
            page=10,
            original=(
                "The Principle Of Health. The Principle Of Ecology. The Principle Of "
                "Fairness. The Principle Of Care."
            ),
            replacement="",
            reason="The same repeated strip; see the page-8 entry.",
        ),
    ),
}
