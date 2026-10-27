"""What the reader actually renders, measured on the corpus in the database.

Read-only: no writes, no network, no model calls. It exists to answer three questions with numbers
instead of impressions, and every number it prints comes from the **shipped** code:

1. **Does Appendix 2 read as the paper's table?** The reviewed rows, the cells the paper leaves
   empty, the dividers and where they sit relative to the row they name, and the pages the column
   headers are printed on.
2. **How many locator lines does one-per-run save?** Per document, then for the whole corpus.
3. **Which references resolve, and which cannot be decided?** Every printed mention, its target, and
   the ambiguous ones named. Plus the glossary: how many headwords the document defines.

**It imports the product's rules rather than re-implementing them.** The first version of this
script held its own copy of the proposed dividers, its own locator comparison and its own three
reference resolvers — and a copy is free to stay right while the product goes wrong, which is exactly
how `probe_chat.py` came to report a grounded answer for a question `/ask/` refuses (§21, G8). There
is one implementation, in `knowledge/`, and this prints what it says.

    python scripts/probe_reader_structure.py            # every document in the database
    python scripts/probe_reader_structure.py --doc saoso
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings")

import django  # noqa: E402

django.setup()

from knowledge.concordance import build_concordance  # noqa: E402
from knowledge.glossary import GLOSSARY_BRANCH, glossary_entries, with_term_anchors  # noqa: E402
from knowledge.models import StandardDocument  # noqa: E402
from knowledge.passages import passage_blocks  # noqa: E402
from knowledge.reading import branch_texts, passage_locator, printed_locators  # noqa: E402
from knowledge.references import build_reference_index, matches  # noqa: E402
from knowledge.tables import TABLE_SECTIONS, rows_for  # noqa: E402
from knowledge.tests.page_fixtures import MANIFEST, pages  # noqa: E402

#: Which fixture pages hold which document, so the printed page can be located without a reader.
DOC_KEYS = {
    "saoso-version-2.1-2026.pdf": "saoso",
    "Outeniqua pgs principles, policies and procedures 2026.pdf": "opp",
    "Basic Production Principles_ENG_PRINT.pdf": "bpp",
    "PGS Certification Landscape_Final.pdf": "landscape",
    "PGS Certification landscape_Final.pdf": "landscape",
}


def squash(text: str) -> str:
    return " ".join((text or "").split())


def head(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def probe_table(document: StandardDocument) -> None:
    """The rows, the empty cells, the dividers' adjacency and the header pages."""
    concordance = build_concordance(document)
    doc_key = DOC_KEYS.get(Path(document.source_file).name)
    mode = "table" if doc_key and f"{doc_key}.table" in MANIFEST["pages"] else "layout"
    printed = pages(doc_key, mode) if doc_key else []

    for section in concordance.sections:
        rows = rows_for(section.key)
        if not rows:
            continue
        head(f"{Path(document.source_file).name} · {section.key} ({len(rows)} reviewed rows)")

        empty = [row.substance for row in rows if not row.condition]
        print(f"rows with no printed condition : {len(empty)} of {len(rows)}")
        for substance in empty[:6]:
            print(f"    - {substance[:60]}")
        if len(empty) > 6:
            print(f"    … and {len(empty) - 6} more")
        print(f"printed pages                  : {sorted({row.page for row in rows})}")

        structure = TABLE_SECTIONS.get(section.key)
        if structure is None:
            print("no reviewed structure — the branch renders as plain passages")
            continue

        print(f"\nlegend                         : {structure.legend[:60]}…")
        print(f"columns                        : {structure.columns[0]} · {structure.columns[1]}")
        print(f"dividers                       : {len(structure.dividers)}")

        if not printed:
            print("  no committed page fixtures for this document — adjacency not checked")
            continue

        # Line-based, because the claim is adjacency: the printed row starts on the next line after
        # the divider. The first 25 characters of a substance tell one row from another here, except
        # rows 0 and 1, which print the same substance twice on purpose.
        for divider in structure.dividers:
            row = rows[divider.before_row]
            needle = squash(row.substance)[:25]
            found_at = None
            for number, page in enumerate(printed, 1):
                lines = page.splitlines()
                for index, line in enumerate(lines):
                    if divider.text not in squash(line):
                        continue
                    following = next(
                        (squash(other) for other in lines[index + 1 :] if other.strip()), ""
                    )
                    if following.startswith(needle):
                        found_at = number
                        break
                if found_at:
                    break
            where = f"PDF p{found_at}" if found_at else "NOT FOUND"
            state = "immediately above" if found_at else "NOT above the row it names"
            print(
                f"  row {divider.before_row:2} ({divider.kind:9}) {divider.text[:30]!r:34} "
                f"{where:9} {state}"
            )

        for column in structure.columns:
            # The paper prints the header in capitals and wraps it across lines, so the case-
            # sensitive first word is what locates it: prose prints the same words in lower case.
            word = column.split()[0].upper()
            found = [n + 1 for n, page in enumerate(printed) if word in page]
            print(f"  column {column[:38]!r:42} {word} on PDF pages {found or 'NONE'}")


def probe_locators(documents: list[StandardDocument]) -> None:
    """The printed locator lines before and after one-per-run, per document and in total."""
    head("Locator runs")
    print(f"  {'document':46} {'passages':>8} {'today':>6} {'printed':>7} {'-':>4}")
    total = printed = 0
    for document in documents:
        concordance = build_concordance(document)
        passages = runs = 0
        for section in concordance.sections:
            rows = [(passage_locator(chunk), chunk.page) for chunk, _anchor in section.passages]
            passages += len(rows)
            runs += sum(printed_locators(rows))
        total += passages
        printed += runs
        print(
            f"  {Path(document.source_file).name[:46]:46} {passages:8} {passages:6} {runs:7} "
            f"{passages - runs:4}"
        )
    print(f"  {'ALL':46} {total:8} {total:6} {printed:7} {total - printed:4}")


def probe_references(document: StandardDocument) -> None:
    """Every mention, where it goes, and the ones that cannot be decided."""
    head(f"References · {Path(document.source_file).name}")
    concordance = build_concordance(document)
    index = build_reference_index(document, concordance.sections)
    branch_of = {
        chunk.pk: section.key for section in concordance.sections for chunk, _anchor in section.passages
    }

    linked: Counter = Counter()
    plain: Counter = Counter()
    total = 0
    for section in concordance.sections:
        for chunk, _anchor in section.passages:
            for match in matches(chunk.text or "", index, open_branch=branch_of[chunk.pk]):
                total += 1
                if match.branch:
                    linked[(squash(match.text), match.branch)] += 1
                elif match.fragment:
                    linked[(squash(match.text), match.fragment)] += 1
                else:
                    plain[(squash(match.text), match.title)] += 1

    print(f"  mentions {total} · resolved {sum(linked.values())} · left as text {sum(plain.values())}")
    print("\nresolved:")
    for (printed, target), count in sorted(linked.items()):
        print(f"  {count:2}x {printed[:46]!r:50} -> {target}")
    print("\nleft as text:")
    for (printed, title), count in sorted(plain.items()):
        reason = title or "no target and nothing to say"
        print(f"  {count:2}x {printed[:46]!r:50} -> {reason[:46]}")


def probe_glossary(document: StandardDocument) -> None:
    """The headwords the document defines, as the reader anchors them."""
    head(f"Glossary · {Path(document.source_file).name}")
    key = GLOSSARY_BRANCH.get(document.source_file)
    if key is None:
        print("  no glossary branch recorded for this document")
        return

    concordance = build_concordance(document)
    branch = next((section for section in concordance.sections if section.key == key), None)
    if branch is None:
        print(f"  GLOSSARY_BRANCH names {key!r}, which is not a branch of this document")
        return

    blocks = [
        block for text in branch_texts(branch.passages) for block in passage_blocks(text)
    ]
    entries = glossary_entries(document.source_file, blocks, branch.anchor)
    anchored = [
        block
        for block in with_term_anchors(blocks)
        if block.kind == "term" and getattr(block, "anchor", "")
    ]

    print(f"  branch {key} ({branch.title}) · {len(branch.passages)} passages")
    print(f"  headwords {len(entries)} · ids {len({block.anchor for block in anchored})}")
    print(f"  first five: {', '.join(entry.term for entry in entries[:5])}")


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
    by_key = {
        doc_key: document
        for document in documents
        for name, doc_key in DOC_KEYS.items()
        if name in document.source_file
    }
    if args.doc:
        if args.doc not in by_key:
            raise SystemExit(f"{args.doc!r} is not ingested; have {sorted(by_key)}")
        documents = [by_key[args.doc]]

    for document in documents:
        probe_table(document)
    probe_locators(documents)
    for document in documents:
        probe_references(document)
    for document in documents:
        probe_glossary(document)

    print(f"\nfixtures recorded by: {MANIFEST.get('extractor')}")
    print(f"extraction:           {MANIFEST.get('extraction_command')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
