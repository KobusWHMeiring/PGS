"""Probe the reader's structure against the corpus in this database.

Read-only. Prints what `product/backlog/In Progress/READER_STRUCTURE_PRD.md` claims, so the claims
can be checked before Task 1 is started and again after it lands:

1. **A table branch as rows** — how many reviewed rows, how many print no condition, how many print
   the same locator as the row above, and whether each divider the PRD proposes is really on the
   printed page above the row it names (read from the committed page fixtures, so this needs no PDF
   reader — D57).
2. **Locator runs** — printed locator lines today against one per run, per document.
3. **References** — every `Section <part> – <n>` and `Appendi(x|ces) <n>` in the text, what it would
   resolve to, and which ones are ambiguous or point into a part the corpus does not hold.
4. **Glossary candidates** — the `Term` blocks in `S1`, how often each occurs elsewhere, and how many
   are prose rather than headwords. This is the list §5.1 says must be reviewed by a human, so the
   probe prints it rather than deciding it.

Usage:
    python scripts/probe_reader_structure.py                 # every ingested document
    python scripts/probe_reader_structure.py --doc saoso     # one

Before running it on a developer machine:

    python manage.py ingest_standard --doc saoso \\
        --file pgs_docs/saoso-version-2.1-2026.pdf --no-embed   # if the corpus is empty

Two things this does **not** establish: how the page *looks* with the dividers in it, and whether a
reader trusts it. Those are `tests/uat/concordance_uat.md` Scenarios 9–11.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")

import django  # noqa: E402

django.setup()

from knowledge.concordance import build_concordance  # noqa: E402
from knowledge.models import StandardDocument  # noqa: E402
from knowledge.passages import passage_blocks  # noqa: E402
from knowledge.tables import TABLE_ROWS  # noqa: E402
from knowledge.tests.page_fixtures import MANIFEST, pages  # noqa: E402

#: The dividers the PRD proposes for Appendix 2, measured against `-table` output on PDF pp. 77–79.
#: `(before_row, printed text, kind)` — kept here so the probe can falsify the table before the data
#: exists in `knowledge/tables.py`.
PROPOSED_DIVIDERS = {
    "Appendix 2": (
        (0, "I. PLANT AND ANIMAL ORIGIN", "part"),
        (1, "South African specific", "qualifier"),
        (3, "South African specific", "qualifier"),
        (14, "South African specific", "qualifier"),
        (15, "II. MINERAL ORIGIN", "part"),
        (26, "III. MICROBIOLOGICAL", "part"),
        (28, "IV. OTHERS", "part"),
    ),
}

COLUMN_HEADERS = {
    "Appendix 2": ("SUBSTANCES DESCRIPTION, COMPOSITIONAL", "CONDITIONS FOR USE"),
}

SECTION_PART = re.compile(r"Section\s+([A-Z])\s*(?:[^\w\s]{1,3}\s*)?(\d{1,2})(?:\.(\d+))?")
#: `Section 4.6.2`, `section 5.7` — the paper also cites a section with no part letter. Printed in a
#: Part-B passage, an unqualified "Section n" means a section of the part it appears in, so the part
#: is not guessed: it is the part of the branch the passage belongs to (the TOC says which).
SECTION_BARE = re.compile(r"Section\s+(\d{1,2})(?:\.(\d+))*", re.IGNORECASE)
APPENDIX = re.compile(r"Appendi(?:x|ces)\s+(\d{1,2})([a-z])?(\s+[A-Z][^.;\n]{0,60})?")

#: Which fixture pages hold which document, so the printed page can be located without a reader.
DOC_KEYS = {
    "saoso-version-2.1-2026.pdf": "saoso",
    "Outeniqua pgs principles, policies and procedures 2026.pdf": "opp",
    "Basic Production Principles_ENG_PRINT.pdf": "bpp",
    "PGS Certification landscape_Final.pdf": "landscape",
}


def squash(text: str) -> str:
    return " ".join((text or "").split())


def head(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def probe_table(doc: StandardDocument) -> None:
    """§1.1 and §3.1: the rows, the empty cells, the repeated locators, the dividers."""
    concordance = build_concordance(doc)
    doc_key = DOC_KEYS.get(Path(doc.source_file).name)
    # `-table` where the fixtures have it: `-layout` prints a centred qualifier on the same text
    # line as the row beside it, so "the next thing after the divider" is only readable row by row
    # in the row-aligned extraction (the same reason `TABLE_ROWS` was verified with `-table`).
    mode = "table" if doc_key and f"{doc_key}.table" in MANIFEST["pages"] else "layout"
    printed = pages(doc_key, mode) if doc_key else []

    for section in concordance.sections:
        rows = TABLE_ROWS.get(section.key)
        if not rows:
            continue
        head(f"{doc.source_file.split('/')[-1]} · {section.key} ({len(rows)} reviewed rows)")

        empty = [row.substance for row in rows if not row.condition]
        print(f"rows with no printed condition : {len(empty)} of {len(rows)}")
        for substance in empty[:6]:
            print(f"    - {substance[:60]}")
        if len(empty) > 6:
            print(f"    … and {len(empty) - 6} more")

        keys = [(chunk.section_ref or chunk.anchor, chunk.page) for chunk, _a in section.passages]
        repeats = sum(1 for before, after in zip(keys, keys[1:]) if before == after)
        runs = sum(1 for before, after in zip(keys, keys[1:]) if before != after) + 1
        print(f"locator lines today            : {len(keys)}")
        print(f"… printed once per run         : {runs}  (suppressed: {repeats})")
        print(f"printed pages                  : {sorted({chunk.page for chunk, _a in section.passages})}")

        dividers = PROPOSED_DIVIDERS.get(section.key, ())
        print()
        print(f"dividers proposed              : {len(dividers)}")
        if not printed:
            print("  no committed page fixtures for this document — order not checked")
            continue

        # Line-based, because the claim is adjacency: the printed row starts on the next line
        # after the divider. The first 25 characters of a substance are enough to tell one row
        # from another here — except rows 0 and 1, which print the same substance cell twice (the
        # point of the qualifier between them), so `matched` means "a row that reads like this".
        for before, divider, kind in dividers:
            needle = " ".join(rows[before].substance.split())[:25]
            hits = []
            for number, page in enumerate(printed, 1):
                lines = page.splitlines()
                for index, line in enumerate(lines):
                    if divider not in squash(line):
                        continue
                    following = next(
                        (squash(other) for other in lines[index + 1 :] if other.strip()), ""
                    )
                    hits.append((number, following.startswith(needle), following[:44]))
            resolved = [hit for hit in hits if hit[1]]
            where = f"PDF p{resolved[0][0]}" if resolved else "NOT FOUND"
            state = "immediately above" if resolved else f"seen {len(hits)}x, none followed by the row"
            print(
                f"  row {before:2} ({kind:9}) {divider[:30]!r:34} {where:10} {state:38} "
                f"{rows[before].substance[:30]!r}"
            )

        for header in COLUMN_HEADERS.get(section.key, ()):
            found = [n + 1 for n, page in enumerate(printed) if header in page]
            print(f"\ncolumn header {header[:44]!r}: PDF pages {found or 'NOT FOUND'}")


def probe_locators(documents: list[StandardDocument]) -> None:
    """§1.2: the printed locator lines, today and after one-per-run."""
    head("Locator runs")
    print(f"  {'document':46} {'passages':>8} {'today':>6} {'after':>6} {'-':>4}")
    total = runs = 0
    for doc in documents:
        concordance = build_concordance(doc)
        count = run_count = 0
        for section in concordance.sections:
            previous = None
            for chunk, _anchor in section.passages:
                key = (chunk.section_ref or chunk.anchor or chunk.heading_path, chunk.page)
                count += 1
                if key != previous:
                    run_count += 1
                previous = key
        total += count
        runs += run_count
        print(
            f"  {Path(doc.source_file).name[:46]:46} {count:8} {count:6} {run_count:6} "
            f"{count - run_count:4}"
        )
    print(f"  {'ALL':46} {total:8} {total:6} {runs:6} {total - runs:4}")


def resolve_section(doc: StandardDocument, keys: set[str], part: str, label: str) -> str:
    """Part B + label n -> `S<n>`; Part A -> the missing note; anything else -> nothing."""
    entry = next(
        (
            row
            for row in (doc.toc or [])
            if row.get("part") == part and row.get("label") == str(label)
        ),
        None,
    )
    if entry is None:
        return "NO TOC ENTRY"
    if part == "B":
        return f"S{label}" if f"S{label}" in keys else "MISSING BRANCH"
    return f"Part {part} is printed and NOT in the corpus"


def resolve_bare_section(doc: StandardDocument, keys: set[str], number: str, parent_part: str) -> str:
    """An unqualified `Section n` inside a passage: the same part, section `n`.

    In:  `number` — the printed section number; `parent_part` — the TOC part the passage is in, or
         "" when the document has no TOC.
    Out: `S<n>` when that branch exists; otherwise a stated reason, never a guess.
    """
    if not parent_part:
        return "NO PART (document has no TOC) — undecidable"
    if parent_part != "B":
        return f"inside Part {parent_part}: nothing to link"
    return f"S{number}" if f"S{number}" in keys else "MISSING BRANCH"


def resolve_appendix(keys: set[str], titles: dict[str, str], number: str, letter: str, words: str) -> str:
    candidates = [
        key
        for key in keys
        if re.fullmatch(rf"Appendix {number}[a-z]?|Appendix {number}\. Table \d", key)
    ]
    if letter:
        exact = f"Appendix {number}{letter}"
        return exact if exact in keys else "MISSING BRANCH"
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        return "NO BRANCH"
    tokens = [token.strip(",.").lower() for token in words.split()][:4]
    for key in candidates:
        if tokens and all(token in titles[key].lower() for token in tokens):
            return key
    return f"AMBIGUOUS {candidates}"


def probe_references(doc: StandardDocument) -> None:
    """§1.3 and §4.2: every reference, where it would go, and which ones cannot be decided."""
    head(f"References · {Path(doc.source_file).name}")
    concordance = build_concordance(doc)
    keys = {section.key for section in concordance.sections}
    titles = {section.key: section.title for section in concordance.sections}

    #: `S<n>` -> the TOC part the branch was named from, so an unqualified `Section n` can be
    #: resolved inside the part it is printed in rather than guessed.
    part_by_key = {
        f"S{entry['label']}": entry.get("part", "")
        for entry in (doc.toc or [])
        if entry.get("kind") == "CLAUSE"
    }

    sections: Counter = Counter()
    bare_sections: Counter = Counter()
    appendices: Counter = Counter()
    for section in concordance.sections:
        for chunk, _anchor in section.passages:
            text = chunk.text or ""
            for match in SECTION_PART.finditer(text):
                printed = squash(match.group(0))
                target = resolve_section(doc, keys, match.group(1), match.group(2))
                sections[(printed, target)] += 1
            for match in SECTION_BARE.finditer(text):
                printed = squash(match.group(0))
                target = resolve_bare_section(
                    doc, keys, match.group(1), part_by_key.get(section.key, "")
                )
                bare_sections[(printed, target)] += 1
            for match in APPENDIX.finditer(text):
                printed = squash(match.group(0))
                target = resolve_appendix(
                    keys, titles, match.group(1), match.group(2), match.group(3) or ""
                )
                appendices[(printed, target)] += 1

    print("\nSection <part> – <n>:")
    for (printed, target), count in sorted(sections.items()):
        print(f"  {count:2}x {printed[:44]!r:48} -> {target}")
    print("\nAppendi(x|ces) <n>:")
    for (printed, target), count in sorted(appendices.items()):
        print(f"  {count:2}x {printed[:44]!r:48} -> {target}")
    print("\nSection <n> (no part letter — resolved inside the part it is printed in):")
    for (printed, target), count in sorted(bare_sections.items()):
        print(f"  {count:2}x {printed[:44]!r:48} -> {target}")

    # A reference to the branch the passage is already in is a no-op, so the reader does not
    # link it. Count it, because a rule with no instances is a rule nobody has tested.
    self_refs = 0
    for section in concordance.sections:
        for chunk, _anchor in section.passages:
            text = chunk.text or ""
            for match in SECTION_PART.finditer(text):
                if resolve_section(doc, keys, match.group(1), match.group(2)) == section.key:
                    self_refs += 1
            for match in APPENDIX.finditer(text):
                target = resolve_appendix(
                    keys, titles, match.group(1), match.group(2), match.group(3) or ""
                )
                if target == section.key:
                    self_refs += 1
    print()
    print(f"references to the branch they are printed in: {self_refs}")


def probe_glossary(doc: StandardDocument, everything: list[StandardDocument]) -> None:
    """§1.4 and §5.1: the candidate terms, their frequency, and the prose the heuristic mistakes."""
    head("Glossary candidates (S1's Term blocks — review required)")
    terms = []
    for chunk in doc.chunks.filter(section_ref="S1").order_by("id"):
        for block in passage_blocks(chunk.text or ""):
            if block.kind == "term":
                terms.append(block.text.strip())

    blob = squash(" ".join((chunk.text or "") for chunk in _all_chunks(everything)))
    counts = Counter()
    for term in terms:
        counts[term] = len(
            re.findall(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", blob)
        )

    print(f"candidate terms                : {len(terms)}")
    print(f"occurrences across the corpus  : {sum(counts.values())}")
    print(f"never used again               : {sum(1 for n in counts.values() if n <= 1)}")
    print("\nmost frequent (a headword that reads as prose is a false positive):")
    for term, count in counts.most_common(12):
        print(f"  {count:3}x  {term}")


def _all_chunks(documents: list[StandardDocument]):
    for doc in documents:
        yield from doc.chunks.all()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", help="Only this document (a corpus key, e.g. saoso).")
    args = parser.parse_args(argv)

    documents = list(StandardDocument.objects.order_by("id"))
    if not documents:
        raise SystemExit(
            "no corpus in this database — run `manage.py ingest_standard --doc saoso "
            "--file pgs_docs/saoso-version-2.1-2026.pdf --no-embed` first"
        )
    by_key = {doc_key: doc for doc in documents for name, doc_key in DOC_KEYS.items() if name in doc.source_file}
    if args.doc:
        if args.doc not in by_key:
            raise SystemExit(f"{args.doc!r} is not ingested; have {sorted(by_key)}")
        documents = [by_key[args.doc]]

    for doc in documents:
        probe_table(doc)
    probe_locators(documents)
    for doc in documents:
        probe_references(doc)
    if args.doc in (None, "saoso"):
        probe_glossary(by_key["saoso"], list(StandardDocument.objects.all()))

    print(f"\nfixtures recorded by: {MANIFEST.get('extractor')}")
    print(f"extraction:           {MANIFEST.get('extraction_command')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
