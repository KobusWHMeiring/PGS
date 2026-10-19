#!/usr/bin/env python
"""Extract verbatim fixtures from the shipped PDFs for the ingestion tests.

This script exists because of the most expensive error in this project's history
(HANDOVER §6.6): a parser was written against an *assumed* document format, matched
zero lines of the real document, **and its tests passed — because the fixtures were
hand-written.** Hand-written fixtures encode the same assumption as the parser, so
they cannot catch it. These fixtures are extracted from the real bytes instead.

Run it with:

    python scripts/extract_fixtures.py

Two rules make that guarantee real, and both matter more than the extraction itself:

1. **Anchors are verified, never assumed.** MVP0_PLAN_V2.md A10 states page ranges
   (``saoso_part_b`` from "pp. 60-62", the TOC from "p. 1", appendices from
   "pp. 70-73"). Measured against the shipped PDFs, **all of them are wrong**:

   ============================  ==============  ==========================
   Fixture                       Plan says       Actually
   ============================  ==============  ==========================
   ``saoso_part_b``              pp. 60-62       p61 (`SECTION B` is on 61;
                                                 page 60 is the tail of §9.6,
                                                 aquaculture)
   ``saoso_toc``                 p. 1            p2 (p1 is the cover page)
   ``saoso_appendices``          pp. 70-73       p71 (`APPENDIX 1`)
   ============================  ==============  ==========================

   Taking the plan at its word would have spliced the end of the aquaculture
   section into the "processing and handling" fixture — silently, exactly like v1.
   So each extract declares an ``anchor`` that must be present on its start page,
   and the script **fails** if it is not. A page number is a claim; the anchor is
   the evidence.

2. **Output is deterministic and self-describing.** Re-running produces
   byte-identical files (no timestamps in the fixtures; no locale-dependent
   formatting), and ``MANIFEST.json`` records each source PDF's ``sha256`` plus the
   byte range taken from the full-document text, so B2 can assert the fixtures have
   not drifted from the governing documents.

Encoding and page separators are fixed: UTF-8, ``\\n`` line endings, and a form feed
(``\\f``) between pages. The form feed is kept deliberately — SPEC §4.5 reality 2 and
4 require *page-aware* extraction (the TOC must be excluded, appendices must be
driven by a page map). A fixture that flattened the pages could not test that.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = REPO_ROOT / "pgs_docs"
FIXTURE_DIR = REPO_ROOT / "knowledge" / "tests" / "fixtures"

SAOSO = "saoso-version-2.1-2026.pdf"
OPP = "Outeniqua pgs principles, policies and procedures 2026.pdf"
BPP = "Basic Production Principles_ENG_PRINT.pdf"
LANDSCAPE = "PGS Certification landscape_Final.pdf"

# Every corpus document, so B6's ingest can verify it read the same bytes this
# manifest was built from. D16 fixes the corpus as SAOSO + OPP + BPP + LANDSCAPE.
CORPUS = (SAOSO, OPP, BPP, LANDSCAPE)


@dataclass
class Extract:
    """One fixture: a page range of one PDF, whose start page is anchor-verified."""

    name: str
    source: str
    start_page: int  # 1-based, as `pdftotext -f` and the form-feed split agree on
    end_page: int
    anchor: str
    anchor_page: int
    why: str
    flags: int = 0
    notes: list[str] = field(default_factory=list)


EXTRACTS: tuple[Extract, ...] = (
    Extract(
        name="saoso_part_b",
        source=SAOSO,
        start_page=61,
        end_page=63,
        anchor=r"^\s*SECTION B\s*$",
        anchor_page=61,
        why=(
            "The processing-and-handling block: the SECTION B body heading and clauses "
            "20.1. / 20.1.1. / 20.1.2. B2's clause parser is written against this. "
            "NOTE: page 60 is the tail of section 9.6 (aquaculture) — including it, as "
            "the plan's 'pp. 60-62' would, grafts unrelated text onto the fixture."
        ),
        notes=[
            "SECTION B also appears as a running page header on many pages, and as a body "
            "heading three times (SPEC §4.5 reality 1). This fixture contains the body "
            "heading on its first page, immediately before '20. PROCESSING AND HANDLING'.",
            "The part letter is mandatory: '1.1.1' occurs in more than one part, so a bare "
            "clause number is ambiguous (SPEC §4.5 reality 3).",
        ],
    ),
    Extract(
        name="saoso_toc",
        source=SAOSO,
        start_page=2,
        end_page=3,
        anchor=r"^\s*TABLE OF CONTENTS\s*$",
        anchor_page=2,
        why=(
            "The table of contents. Its purpose in the fixture set is negative: the TOC "
            "matches the clause pattern ('1.   Introduction - ...   4'), so an ingestion "
            "run that does not exclude these pages ingests 60+ duplicate clauses "
            "(SPEC §4.5 reality 2). B3 asserts the exclusion using this file. Page 1 is "
            "the cover, not the TOC."
        ),
        notes=[
            "Lists appendices, which is why a naive 'find appendix headings' strategy "
            "appears to work until it is run on the body.",
        ],
    ),
    Extract(
        name="saoso_appendices",
        source=SAOSO,
        start_page=71,
        end_page=73,
        anchor=r"^\s*APPENDIX 1\s*$",
        anchor_page=71,
        why=(
            "Appendix content, for the case where the boundary comes from the TOC page map "
            "rather than heading detection (SPEC §4.5 reality 4). APPENDIX 1 begins on p71; "
            "the plan's 'pp. 70-73' starts one page early, in the tail of clause 23.x."
        ),
        notes=[
            "The body prints 'APPENDIX 1' in UPPERCASE and indented ~62 columns. The "
            "TOC prints 'Appendix 1' in title case. MVP0_PLAN_V2.md B2's APPX regex "
            "(r'^Appendix\\s+\\d+...') is title-case and column-0 anchored, so against the "
            "real body it matches NOTHING (reality 4 is correct) but FALSE-POSITIVES on "
            "p63, where 'Appendix 4.' starts a mid-sentence line. Both cases are in this "
            "fixture set: p63 is inside saoso_part_b.",
        ],
    ),
    Extract(
        name="opp_4_1",
        source=OPP,
        start_page=4,
        end_page=4,
        anchor=r"^\s{0,7}4\.1\s+Preparation",
        anchor_page=4,
        why=(
            "§4.1 Preparation, with items '1.'- '3.' and the '5 days notice' rule that "
            "SPEC §4.5 cites as §4.1(1). Uses the '1.' item marker."
        ),
        notes=["Heading is at column 0; item marker is '1.' (not '1)')."],
    ),
    Extract(
        name="opp_4_2",
        source=OPP,
        start_page=5,
        end_page=5,
        anchor=r"^\s{0,7}4\.2\s+Assessment",
        anchor_page=5,
        why=(
            "§4.2 Assessment, whose items run '1)' … '12)' and carry two of the reference "
            "citations in SPEC §4.5: §4.2(5) (conclusion within 5 days) and §4.2(12) "
            "(traceability). Uses the '1)' item marker, unlike §4.1."
        ),
        notes=["Three item markers exist across the OPP ('1.', '1)', 'a.') — this fixture and opp_4_1 are why."],
    ),
    Extract(
        name="opp_4_5",
        source=OPP,
        start_page=6,
        end_page=7,
        anchor=r"^\s{0,7}4\.5\s+Non-compliance",
        anchor_page=6,
        why=(
            "§4.5 Non-compliance and discipline — the hardest block in either document, and "
            "the reason reference depth is bounded at three (SPEC §4.5 reality 6). It "
            "contains the missing item 3, a nested 'a./b./c.' list whose (c) branch restarts "
            "numbering at 1, an unnumbered 'First warning / Second warning / Serious "
            "misconduct' block, and — across the p6/p7 break — a list split by a page footer."
        ),
        notes=[
            "SPEC §4.5 says '§4.5 has no item 3 (numbering runs 1, 2, 4, 5)'. The extract is "
            "verbatim, so B2 can assert exactly that rather than trusting it.",
            "The (c) attendee list is half-numbered: items 1-3 are numbered and the "
            "'at least one additional group member' clause is not.",
            "The unnumbered blocks take a content-derived anchor "
            "('4.5#action-first-warning') rather than a fabricated reference.",
        ],
    ),
    Extract(
        name="opp_seals",
        source=OPP,
        start_page=8,
        end_page=9,
        anchor=r"^\s{0,7}[IVX]+\.\s+Seals",
        anchor_page=8,
        why=(
            "OPP §V Seals and §VI Aggregation. §V is the source of A4's seed data — three "
            "marks, of which 'PGS pasture-raised' states its criteria are 'details on this "
            "forthcoming' — and §VI is the aggregation sub-domain. Both are reached by an "
            "*indented* Roman-numeral regex: a column-0 pattern misses §VI at indent 6."
        ),
        notes=[
            "'V. Seals' is at column 0; 'VI. Aggregation' is at indent 6 (SPEC §4.5 "
            "reality 5). The anchor allows 0-7 and the fixture contains both, so B2 can "
            "prove the indentation tolerance is necessary.",
            "Reproduces the pasture-raised criteria line verbatim; this is the evidence A4's "
            "is_active=False decision rests on.",
        ],
    ),
)


def run_pdftotext(pdf: Path) -> str:
    """Full-document text with `-layout`, exactly as the extractor sees it.

    In:  `pdf` — a path under ``pgs_docs/``.
    Out: the document text, decoded UTF-8 with replacement.
    Fails: RuntimeError if pdftotext is missing or exits non-zero.
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(
            "pdftotext not found. It is part of poppler-utils (A10's stated dependency)."
        ) from exc
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        raise RuntimeError(f"pdftotext failed on {pdf.name}: {exc.stderr!r}") from exc

    return result.stdout.decode("utf-8", errors="replace")


def split_pages(text: str) -> list[str]:
    """Split on form feed. Page N (1-based) is ``pages[N-1]``."""
    return text.split("\f")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_anchor(pages: list[str], extract: Extract) -> None:
    """Fail loudly if the anchor is not on the declared page.

    This is the guard against v1's failure. A page number copied from a plan is a
    claim; the anchor on that page is the evidence. If they disagree, the script
    stops rather than writing a fixture containing the wrong text.
    """
    if extract.anchor_page > len(pages):
        raise SystemExit(
            f"[{extract.name}] anchor_page {extract.anchor_page} is beyond the document "
            f"({len(pages)} pages)."
        )

    page = pages[extract.anchor_page - 1]
    if not re.search(extract.anchor, page, re.MULTILINE):
        # Show what IS on that page, so the fix is obvious without re-running pdftotext.
        head = [line for line in page.splitlines() if line.strip()][:3]
        raise SystemExit(
            f"[{extract.name}] anchor {extract.anchor!r} NOT found on page "
            f"{extract.anchor_page} of {extract.source}.\n"
            f"  That page actually begins:\n"
            + "\n".join(f"    {line.strip()[:80]!r}" for line in head)
            + "\n  The declared page is wrong, or the PDF has changed. Do not 'fix' this by "
              "deleting the anchor — that is the check that stops the fixture being wrong."
        )


def normalise(text: str) -> str:
    """Make the text byte-stable across platforms and runs.

    ``\\r\\n`` -> ``\\n`` (pdftotext honours the platform's line separator), and strip
    trailing whitespace on each line. Page separators are already ``\\f`` because
    ``split_pages`` consumed the originals.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n"))


def main() -> int:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "generated_by": "scripts/extract_fixtures.py",
        "description": (
            "Verbatim fixtures for the standards-ingestion tests. Extracted from the "
            "shipped PDFs by `pdftotext -layout`. Never hand-edit: hand-written fixtures "
            "encode the same assumption as the parser they test, which is how v1 passed "
            "its tests while matching zero lines of the real document."
        ),
        "extraction_command": "pdftotext -layout <pdf> -",
        "line_endings": "\\n",
        "page_separator": "\\f",
        "encoding_caveat": (
            "Fixtures are UTF-8. Glyphs the PDFs fail to map to Unicode become U+FFFD "
            "(REPLACEMENT CHARACTER). This is a fidelity loss in the SOURCE documents, "
            "not in the extraction: pdftotext -enc Latin1 emits 0xFF and -enc ASCII7 "
            "emits '-', so the byte is not valid UTF-8 and no encoding recovers the real "
            "character. Concretely, the OPP's 'Pasture raised is not defined by the SAOSO "
            "standard <0xFF> details on this forthcoming' carries an en-dash in SPEC §4.3 "
            "that no extractor produces. Do NOT hand-edit these files to 'fix' it — a "
            "hand-corrected fixture stops being evidence, which is exactly how v1's parser "
            "passed its tests while matching nothing in the real document. Assert on text "
            "that survives extraction, or normalise explicitly in the parser."
        ),
        "note_on_page_numbers": (
            "MVP0_PLAN_V2.md A10's page ranges are wrong (saoso_part_b pp.60-62 vs p61; "
            "saoso_toc p.1 vs p2; appendices pp.70-73 vs p71). Each extract declares an "
            "`anchor` that must appear on its `anchor_page`, verified at extraction time."
        ),
        "corpus_sources": {},
        "fixtures": {},
    }

    # Every corpus document's hash, so a later run can prove the manifest still
    # describes the files in pgs_docs/ (A10's acceptance criterion).
    for name in CORPUS:
        path = PDF_DIR / name
        if not path.exists():  # pragma: no cover - environment guard
            raise SystemExit(f"corpus document missing: {path}")
        manifest["corpus_sources"][name] = {
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
        }

    # Cache the full text per source: extracting all fixtures from one document
    # should not run pdftotext four times.
    full_text: dict[str, str] = {}

    for extract in EXTRACTS:
        if extract.source not in full_text:
            full_text[extract.source] = run_pdftotext(PDF_DIR / extract.source)

        pages = split_pages(full_text[extract.source])
        verify_anchor(pages, extract)

        if extract.end_page < extract.start_page:
            raise SystemExit(f"[{extract.name}] end_page precedes start_page")

        # `\f` between pages, as pdftotext emitted them: B2/B3 need page-aware
        # extraction, so flattening the pages here would remove the ability to test it.
        chunk = "\f".join(pages[extract.start_page - 1 : extract.end_page])
        body = normalise(chunk)

        # Byte range in the FULL document text. Recorded so drift from the PDF is
        # detectable, and so a reader can locate the excerpt without the script.
        whole = full_text[extract.source].replace("\r\n", "\n")
        start_byte = whole.find(pages[extract.start_page - 1])
        end_page_text = pages[extract.end_page - 1]
        end_byte = whole.find(end_page_text)
        end_byte = end_byte + len(end_page_text) if end_byte != -1 else -1

        out = FIXTURE_DIR / f"{extract.name}.txt"
        # newline="" so Python does not translate \n to os.linesep on Windows — that
        # would make the fixtures differ between this box and the VPS, and the
        # determinism check would pass locally and fail in CI.
        with open(out, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)

        data = out.read_bytes()
        manifest["fixtures"][extract.name] = {
            "file": f"knowledge/tests/fixtures/{extract.name}.txt",
            "source": extract.source,
            "pages": f"{extract.start_page}-{extract.end_page}",
            "anchor": extract.anchor,
            "anchor_page": extract.anchor_page,
            # Hashed from the bytes we actually wrote, so the manifest describes the
            # artefact rather than the intent.
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "byte_range_in_source_text": [start_byte, end_byte],
            "why": extract.why,
            "notes": extract.notes,
            "replacement_char_count": body.count("�"),
        }
        print(f"  {extract.name}.txt  <- {extract.source} pp.{extract.start_page}-{extract.end_page}  ({len(data)} bytes)")

    manifest_path = FIXTURE_DIR / "MANIFEST.json"
    with open(manifest_path, "w", encoding="utf-8", newline="") as fh:
        # sort_keys + indent: deterministic output, so the file itself is diffable.
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print(f"\n{len(EXTRACTS)} fixtures -> {FIXTURE_DIR}")
    print(f"manifest       -> {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
