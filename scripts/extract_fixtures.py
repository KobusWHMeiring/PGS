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

import argparse
import hashlib
import subprocess
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# `knowledge/extraction.py` owns the `pdftotext` call, so the fixtures and B6's ingest
# cannot drift apart: a parser tested against one rendering and run against another is
# exactly how v1 matched zero lines of the real document. The script is run as
# `python scripts/extract_fixtures.py`, so the repo root has to be importable.
sys.path.insert(0, str(REPO_ROOT))

from knowledge.extraction import (  # noqa: E402  (import after sys.path)
    PAGE_SEPARATOR,
    extract_pages,
    normalise,
    pdftotext_bin,
    pdftotext_text as run_pdftotext,
    sha256_of,
)
from knowledge.columns import apply_layout  # noqa: E402  (import after sys.path)
from knowledge.reflow import reflow_pages  # noqa: E402  (import after sys.path)

PDF_DIR = REPO_ROOT / "pgs_docs"
FIXTURE_DIR = REPO_ROOT / "knowledge" / "tests" / "fixtures"
PAGE_FIXTURE_DIR = FIXTURE_DIR / "pages"

SAOSO = "saoso-version-2.1-2026.pdf"
OPP = "Outeniqua pgs principles, policies and procedures 2026.pdf"
BPP = "Basic Production Principles_ENG_PRINT.pdf"
LANDSCAPE = "PGS Certification landscape_Final.pdf"

#: The pipeline this script records in `MANIFEST.json`. Bump the suffix when the
#: transform changes, so a fixture that predates the change is visibly stale rather
#: than silently different from what ingest would produce. `+ reflow` is D52: a word
#: the PDF hyphenated across a line break is rejoined exactly as `ingest_standard`
#: rejoins it, so the fixture's `post-harvest` is what the parser and the audit see.
PIPELINE = "pdftotext -layout + de_column + reflow v2"

#: Source filename -> `CORPUS_DOCUMENTS` key, so `apply_layout` can consult the
#: exclusion table for the same document ingest sees.
DOC_KEYS = {SAOSO: "saoso", OPP: "opp", BPP: "bpp", LANDSCAPE: "landscape"}

#: Every page of every governed document, exactly as `extract_pages` returns it.
#: These are the *inputs* of the transform tests, not transformed text: `test_columns`,
#: `test_reflow`, `test_section_parsers` and `test_corpus_bpp` apply the transform
#: themselves, so committing the pages removes the extractor from the gate without
#: touching a single assertion (D57).
#:
#: `table` exists only for SAOSO: `-table` is an **Xpdf-4-only flag** (poppler exits 99 with
#: a usage message), and Appendix 2's cells are verified against it. Committing that output
#: is what lets the gate run on a machine whose extractor cannot produce it.
PAGE_MODES = {SAOSO: ("layout", "raw", "table"), OPP: ("layout", "raw"),
              BPP: ("layout", "raw"), LANDSCAPE: ("layout", "raw")}


def extractor_banner() -> str:
    """The first line of `pdftotext -v`: which build produced these bytes.

    Xpdf prints the banner to stderr and exits **1** (hazard section 3.10), so `check=False`
    and the text is read from either stream.
    """
    result = subprocess.run(
        [pdftotext_bin(), "-v"], capture_output=True, text=True, check=False
    )
    banner = (result.stderr or result.stdout or "").strip().splitlines()
    return banner[0] if banner else "unknown extractor"


def _recorded_extractor() -> str:
    """The banner recorded by the last run, or "" when there is no manifest yet."""
    path = FIXTURE_DIR / "MANIFEST.json"
    if not path.exists():
        return ""
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("extractor", "")
    except (OSError, ValueError):  # a corrupt manifest must not block regeneration
        return ""


def write_page_fixtures(manifest: dict, *, force: bool = False) -> None:
    """Write the whole-document page fixtures and record their provenance.

    In: `manifest` — the dict about to be serialised; `force` — regenerate even when the
        extractor build differs from the recorded one.
    Fails: `SystemExit` when the extractor has changed, naming both banners. A different
        build wraps lines and detects columns differently, so regenerating silently would
        rewrite the goldens a review approved without anybody deciding to.
    """
    banner = extractor_banner()
    recorded = _recorded_extractor()
    if recorded and recorded != banner and not force:
        raise SystemExit(
            "The extractor changed since these fixtures were written:\n"
            f"  recorded: {recorded}\n"
            f"  now:      {banner}\n"
            "Poppler and Xpdf wrap lines and detect columns differently, so this is a\n"
            "re-baseline of the goldens, not a refresh. Run `scripts/check_extraction.py`\n"
            "to see what would change, review the diff, then re-run with --force.\n"
            "(Set PDFTOTEXT_BIN to pin the build the fixtures were measured on.)"
        )

    PAGE_FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    manifest["extractor"] = banner
    manifest["pages"] = {}

    for source, modes in PAGE_MODES.items():
        doc_key = DOC_KEYS[source]
        pdf = PDF_DIR / source
        pdf_digest = sha256_of(pdf)
        for mode in modes:
            pages = extract_pages(pdf, mode=mode)
            body = PAGE_SEPARATOR.join(pages)
            out = PAGE_FIXTURE_DIR / f"{doc_key}.{mode}.txt"
            # newline="" for the same reason the range fixtures use it: no os.linesep
            # translation, or the fixture differs between this box and the VPS.
            with open(out, "w", encoding="utf-8", newline="") as fh:
                fh.write(body)
            data = out.read_bytes()
            manifest["pages"][f"{doc_key}.{mode}"] = {
                "file": f"knowledge/tests/fixtures/pages/{out.name}",
                "source": f"pgs_docs/{source}",
                "mode": mode,
                "pages": len(pages),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "pdf_sha256": pdf_digest,
                "extractor": banner,
            }
            print(f"  pages/{out.name}  ({len(pages)} pages, {len(data)} bytes)")

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
            "real body it matches NOTHING but FALSE-POSITIVES on p63, where 'Appendix 4.' "
            "starts a mid-sentence line. Both cases are in this fixture set: p63 is inside "
            "saoso_part_b.",
            "Corrected 2026-10-19 by measurement: SPEC §4.5 reality 4 overstated this. All "
            "twelve appendix headings DO appear in the body in UPPERCASE — but across four "
            "separator shapes (', ' / ':' / '.' / none) and indentation 0-62 columns, so a "
            "single tolerant regex is required. The TOC map's job is to supply the "
            "*canonical label* ('Appendix 4. Table 2' where the body prints 'APPENDIX 4 "
            "TABLE 2:'), not the boundary.",
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
    Extract(
        name="bpp_intro",
        source=BPP,
        start_page=3,
        end_page=4,
        anchor=r"^\s{0,8}INTRODUCTION\b",
        anchor_page=3,
        why=(
            "The Basic Production Principles' introduction and general principles, for "
            "`heading.py` — the BPP carries no clause numbering at all, so its citation is "
            "page + heading (SPEC §4.5 reality table)."
        ),
        notes=[
            "Two columns, so `pdftotext -layout` puts left- and right-column text on the "
            "same line ('INTRODUCTION' and 'DEFINITION OF ORGANIC' share line 1). Any "
            "heading regex must therefore tolerate trailing column text and must not be "
            "anchored with `$`.",
            "'GENERAL PRINCIPLES' (p4) is also followed by right-column text on the same "
            "line; '1. Ecosystem Management' is a Title Case subheading in the left column.",
        ],
    ),
    Extract(
        name="landscape_seals",
        source=LANDSCAPE,
        start_page=6,
        end_page=8,
        anchor=r"^\s*PGS SEALS AND THEIR USE\s*$",
        anchor_page=6,
        why=(
            "The certification landscape's seals section. LANDSCAPE is the other "
            "heading-only document (SPEC §4.5 reality table) and the second consumer of "
            "`heading.py`."
        ),
        notes=[
            "Spans three pages on purpose: 'SOUTH AFRICAN ORGANIC CERTIFICATION LANDSCAPE' "
            "is a *running header* on most pages, so a heading detector that does not "
            "suppress lines repeating across pages emits it as a section once per page.",
        ],
    ),
)


def split_pages(text: str) -> list[str]:
    """Split on form feed. Page N (1-based) is ``pages[N-1]``."""
    return text.split("\f")


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--force",
        action="store_true",
        help="regenerate the page fixtures even if the extractor build changed",
    )
    args = parser.parse_args(argv)
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
        "pipeline": PIPELINE,
        "pipeline_note": (
            "Each page is passed through `knowledge.columns.apply_layout` after "
            "`pdftotext -layout`, with the same doc_key ingest uses, and then through "
            "`knowledge.reflow.reflow_pages`, so the fixture bytes are what the parser "
            "sees in production. Pages that are column-laid-out but must not be "
            "transformed (SAOSO pdf 2, 82, 83; OPP pdf 11) are listed with their reason "
            "in `PAGE_LAYOUT_EXCLUSIONS`. `layout_pages` names the pages de-columning "
            "changed; `reflow_pages` names the pages where a hyphenated word was "
            "rejoined."
        ),
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
    # should not run pdftotext four times. The transformed page list is cached too,
    # because `apply_layout` is a function of the whole document's page numbers (an
    # exclusion is keyed by absolute PDF page, not by the extract's local index).
    full_text: dict[str, str] = {}
    raw_pages: dict[str, list[str]] = {}
    laid_out_pages: dict[str, list[str]] = {}
    reflowed_pages: dict[str, list[str]] = {}

    for extract in EXTRACTS:
        if extract.source not in full_text:
            full_text[extract.source] = run_pdftotext(PDF_DIR / extract.source)
            raw_pages[extract.source] = split_pages(full_text[extract.source])
            laid_out_pages[extract.source] = apply_layout(
                raw_pages[extract.source], doc_key=DOC_KEYS.get(extract.source)
            )[0]
            # Reflowed last, as in `ingest_standard`: line adjacency is reading
            # adjacency only after the columns are in order (D52).
            reflowed_pages[extract.source] = reflow_pages(
                laid_out_pages[extract.source]
            )[0]

        pages = reflowed_pages[extract.source]
        verify_anchor(pages, extract)

        if extract.end_page < extract.start_page:
            raise SystemExit(f"[{extract.name}] end_page precedes start_page")

        # `\f` between pages, as pdftotext emitted them: B2/B3 need page-aware
        # extraction, so flattening the pages here would remove the ability to test it.
        chunk = "\f".join(pages[extract.start_page - 1 : extract.end_page])
        body = normalise(chunk)

        # Byte range in the FULL document text. Recorded so drift from the PDF is
        # detectable, and so a reader can locate the excerpt without the script.
        # Measured against the RAW pages, because that is what the PDF contains.
        whole = full_text[extract.source].replace("\r\n", "\n")
        raw = raw_pages[extract.source]
        start_byte = whole.find(raw[extract.start_page - 1])
        end_page_text = raw[extract.end_page - 1]
        end_byte = whole.find(end_page_text)
        end_byte = end_byte + len(end_page_text) if end_byte != -1 else -1

        # The hash of each raw page *before* the transform: a later change to
        # `de_column` makes the manifest comparison fail instead of letting the
        # fixture drift away from the PDF silently.
        raw_page_sha256 = {
            str(number): hashlib.sha256(
                normalise(raw[number - 1]).encode("utf-8")
            ).hexdigest()
            for number in range(extract.start_page, extract.end_page + 1)
        }
        changed = [
            number
            for number in range(extract.start_page, extract.end_page + 1)
            if laid_out_pages[extract.source][number - 1] != raw[number - 1]
        ]
        # Recorded separately from `layout_pages`, which stays the de-column answer: one
        # number that means two different transforms is not a measurement.
        rejoined = [
            number
            for number in range(extract.start_page, extract.end_page + 1)
            if pages[number - 1] != laid_out_pages[extract.source][number - 1]
        ]

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
            "pipeline": PIPELINE,
            "layout_pages": changed,
            "reflow_pages": rejoined,
            "raw_page_sha256": raw_page_sha256,
            "byte_range_in_source_text": [start_byte, end_byte],
            "why": extract.why,
            "notes": extract.notes,
            "replacement_char_count": body.count("�"),
        }
        print(f"  {extract.name}.txt  <- {extract.source} pp.{extract.start_page}-{extract.end_page}  ({len(data)} bytes)")

    write_page_fixtures(manifest, force=args.force)

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
