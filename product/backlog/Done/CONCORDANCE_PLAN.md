# The Concordance — Implementation Plan

**Status:** **Done** — all eleven tasks landed 2026-10-27; **UAT SIGNED 2026-10-28** — `tests/uat/concordance_uat.md` carries eleven **PASS** results, signed by Kobus (Product) against commit `4e02d71`; applied by `scripts/uat_signoff.py`. The PGS administrator, committee reviewer and consumer-member seats are still empty (D4).
The implementation
notes that differ from this plan are in §12, at the end.
**Read first:** §0.2 (this machine's `PublicDocument` rows need `publish_documents` before anything
is measurable) and §0.4 (the dry run).
**Owner:** Kobus Meiring (Product) · Build
**PRD:** `CONCORDANCE_PRD.md` (decisions in §7, findings in §10.5–10.8, UAT impact in §11)
**Decision record:** `product/design/d68_concordance_open_questions.html` (the eight answers)
**UAT:** `tests/uat/concordance_uat.md` — **drafted before implementation** (shift-left)
**Reference:** `build_principles.md` §I, §II, §V · `testing_hazards.md` §1.6, §1.9, §1.32, §1.33, §3.7
**Baseline commit:** `e84bab5` (the decision), on top of `ca47d80`

---

**Goal:** `/documents/<code>/read/` becomes the concordance — the document's printed structure as
its navigation, one open branch, a citation that opens on the line it quotes, and a page that says
which printed sections the corpus does not hold.

**Architecture:** one new library module (`knowledge/concordance.py`) derives branches from
`DocumentChunk` rows — no chunking, no embedding, no retrieval change, no `core` import. The printed
table of contents is stored once per document (`StandardDocument.toc`) because it is the only honest
source of a branch's *name*. Passage anchors stop being order-derived: the disambiguator becomes a
slug of the passage's own words, so the anchor is a property of the text. `core/services/_documents.py`
gains a `Reader` with a selected branch; the view passes `?section=` through; the template renders a
tree, one pane, and an omission note.

**Tech stack:** Django 5.2, PostgreSQL (JSONB), server-rendered templates, one stylesheet, zero JS
for the concordance itself (a native `<details>` disclosure on the phone).

---

## 0. How to execute

- **TDD, always.** Each task states its failing test first. Run it, watch it fail for the *right*
  reason, then implement. A test that has never failed is decoration (`testing_hazards.md` §0).
- **One commit per task**, prefixed with the task id: `feat(c3): branches from the printed TOC`.
- **Schema before logic.** Task 1 is the only migration and it lands before anything reads `toc`.
- **Verify against the real corpus, not a fixture,** for every claim the PRD measured
  (`testing_hazards.md` §1.33: the committed fixtures are not the deployed corpus).

### 0.1 A note on the other session's work — read before Task 6

`core/services/_chatbot.py`, `core/templates/chatbot/_thread.html` and
`core/templates/chatbot/answer_page.html` are also being edited by a concurrent session. **Tasks 6
and 10 are the only tasks that touch them.** Do Task 1–5 and 7–9 first; before starting Task 6, run
`git status --short core/` and rebase onto whatever landed. If the tree is dirty in those files, wait
or coordinate — a conflicting three-way merge in `_chatbot.py` costs more than the task.

### 0.2 Repair this machine's data before measuring anything

On the developer machine all eight `PublicDocument` rows hold absolute paths, so `corpus_for()`
returns `None`, every citation fails to resolve, and the reader shows "not published the text".
Measured 2026-10-27. It is stale data, not a code defect — `_recorded_source()` has written
repository-relative paths since `4c94c09`.

```bash
python manage.py publish_documents
python - <<'PY'
import django, os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pgs.settings"); django.setup()
from core.models import PublicDocument
from core.services._documents import corpus_for
for d in PublicDocument.objects.all():
    print(d.code, bool(corpus_for(d)))
PY
```

Expected: `saoso-standard-v2.1 True`, `opp True`, `basic-production-principles True`,
`certification-landscape True`, and `False` for the four forms/checklists (they have no corpus, by
D41 — the reader says so honestly).

### 0.3 Baseline

```bash
python -m pytest knowledge core -q
```

Record the number. Every later task must leave it green and strictly larger.

---

### 0.4 What was verified before this plan was written

`scripts/probe_concordance.py` (committed, read-only) runs this plan's own arithmetic against the
live corpus — 366 passages — without touching the repo. It is the reason the numbers below are
quoted rather than hoped for. Run it before Task 1 and again after Task 4:

```bash
python scripts/probe_concordance.py --toc     # --toc reads SAOSO's printed TOC from the fixture,
                                             # because the field does not exist until Task 1
```

It exits 0 and prints `ambiguous anchors=0`. Before Task 4 it prints nothing different — the probe
implements the plan's derivation, not the shipped one — so use it to check the *branches and
titles*, and use Task 4's guard test to prove the anchors.

| Claim | Measured by the dry run |
|---|---|
| SAOSO's tree with the stored TOC | **23 rows / 319 passages** — 22 branches plus the reserved `10 to 19` |
| Branch names | `1. Definitions`, `Appendix 2. Fertilizers Conditioners and Soil Conditioners` — both correct |
| Printed sections the corpus does not hold | **6**, exactly: Section A's three clauses and Appendices A–C |
| OPP / landscape / BPP | 8 / 6 / 4 rows, 30 / 8 / 9 passages — no branch lost |
| Anchors after the Task 4 derivation | **0 ambiguous of 366** (today: 57), and the first row of a group keeps its bare anchor |
| Sample anchors | `#appendix-2` (first, unchanged), `#appendix-2-guano`, `#appendix-2-source-separated-human-excrement` |

The two things the dry run did **not** establish: the page's weight after the change, and the
phone layout. Both are Task 9 and the UAT.

---

## File map

| File | Change |
|---|---|
| `knowledge/models.py` | **+** `StandardDocument.toc` (JSONField, default `list`) |
| `knowledge/migrations/0003_standarddocument_toc.py` | **new** — additive, nullable-equivalent default |
| `knowledge/sections/toc.py` | **+** `toc_from_pages(pages)` — page selection, not a new parser |
| `knowledge/ingest.py` | **+** read and store `toc` on create (both ingest paths) |
| `knowledge/concordance.py` | **new** — `ConcordanceSection`, `build_concordance()`, `concordance_sections()`, `Concordance.missing`, `REVIEWED_BRANCH_TITLES` |
| `knowledge/reading.py` | **~** `passage_anchors()` replaces the numeric suffix; **−** `contents()`, `ReadingEntry` |
| `core/services/_documents.py` | **~** `Reader.sections/selected/section/missing`; `reader_for(document, query, section)` |
| `core/services/_chatbot.py` | **~** `Citation.reading_anchor` resolves through `passage_anchors()`; `read_url` carries `?section=` |
| `core/views/_documents.py` | **~** `?section=`, per-branch `<title>`, canonical |
| `core/templates/public/document_reader.html` | **~** tree + pane + crumb + omission note |
| `core/templates/chatbot/_thread.html`, `answer_page.html` | **~** "View this line", new tab, announced |
| `core/static/css/reader.css` | **~** `.reader__tree`, disclosure at ≤900 px, 44 px rows |
| `knowledge/tests/test_concordance.py` | **new** |
| `knowledge/tests/test_anchors.py` | **new** — the 366-passage guard |
| `knowledge/tests/test_reading.py` | **~** `contents()` tests →
  `passage_anchors()` tests |
| `core/tests/test_document_reader.py` | **~** branch selection, citation copy, title/canonical |

**No file will exceed 30 KB** (`build_principles.md` §8): `knowledge/concordance.py` is estimated
at 8–10 KB, and `reading.py` *shrinks* because `contents()` is deleted.

---

### Task 1: Store the printed table of contents on the document

The one migration. It exists because **a branch's name cannot be recovered from the chunks** —
`S1`'s opener carries no heading (`CONCORDANCE_PRD` §10.1) and Appendix 2's first heading names its
first sub-table, not the appendix (§10.5).

**Files:**
- Modify: `knowledge/models.py`
- Create: `knowledge/migrations/0003_standarddocument_toc.py`
- Test: `knowledge/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# knowledge/tests/test_models.py
def test_a_document_starts_with_no_stored_toc(document):
    """The field is additive: every document ingested before today has no TOC, and the
    concordance must fall back to headings rather than fail on a missing key."""
    assert document.toc == []


def test_the_toc_survives_a_round_trip_as_json(document):
    """JSONB, not a string: the concordance reads entry["label"], and a serialised blob
    would make the page's structure a parsing problem."""
    entry = {
        "part": None,
        "kind": "RANGE",
        "label": "10 to 19",
        "title": "Left blank to facilitate future enterprises",
        "printed_page": None,
    }
    document.toc = [entry]
    document.save(update_fields=["toc"])

    assert StandardDocument.objects.get(pk=document.pk).toc == [entry]
```

- [ ] **Step 2: Run it and watch it fail**

```bash
python -m pytest knowledge/tests/test_models.py -k toc -q
```
Expected: FAIL — `AttributeError: 'StandardDocument' object has no attribute 'toc'`.

- [ ] **Step 3: Add the field**

```python
# knowledge/models.py, inside StandardDocument, after `section_scheme`
    toc = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "The document's printed table of contents, as a list of "
            "{part, kind, label, title, printed_page} — the only source of a branch's "
            "*name* for the concordance (D68). Empty for a document that prints none, "
            "and for every document ingested before the field existed."
        ),
    )
```

- [ ] **Step 4: Make the migration**

```bash
python manage.py makemigrations knowledge --name standarddocument_toc
python manage.py migrate
```
Expected: `0003_standarddocument_toc` — additive, `default=list`, no `RunPython`, no data migration.
`build_principles.md` §I: new fields are nullable or defaulted.

- [ ] **Step 5: Run the tests**

```bash
python -m pytest knowledge/tests/test_models.py -q && python manage.py makemigrations --check --dry-run
```
Expected: PASS, and `No changes detected` (the check is what proves the migration matches the model).

- [ ] **Step 6: Commit**

```bash
git add knowledge/models.py knowledge/migrations/0003_standarddocument_toc.py knowledge/tests/test_models.py
git commit -m "feat(c1): store the printed table of contents, for a branch's name"
```

---

### Task 2: Read the TOC at ingest

`parse_toc()` exists and has **no production caller** (§10.8). This task wires it — bounded to the
pages that print a contents heading, because `parse_toc`'s clause regex is the same shape as a
printed body clause and would otherwise file body headings as contents entries.

**Files:**
- Modify: `knowledge/sections/toc.py`, `knowledge/ingest.py`
- Test: `knowledge/tests/test_toc_map.py`, `knowledge/tests/test_ingest.py`

- [ ] **Step 1: Write the failing parser test (real fixture, not a hand-written string)**

```python
# knowledge/tests/test_toc_map.py
from knowledge.sections.toc import toc_from_pages

def test_the_toc_is_read_from_the_page_that_prints_it(fixture):
    """`saoso_toc.txt` is a verbatim `pdftotext -layout` extract of printed p.2.

    A hand-written TOC would encode the same assumption as the regex it tests
    (`testing_hazards.md` §3.7). Measured 2026-10-27: 29 entries, of which one is the
    reserved range and three are the appendices the corpus does not contain (§10.6).
    """
    entries = toc_from_pages([fixture("saoso_toc")])

    assert len(entries) == 29
    assert [entry.kind for entry in entries].count("RANGE") == 1
    assert [entry.label for entry in entries if entry.kind == "APPENDIX"][-3:] == [
        "Appendix A", "Appendix B", "Appendix C",
    ]


def test_a_page_with_no_contents_heading_yields_nothing(fixture):
    """Bounded on purpose: `APPENDICES` appears in the body too, and a body clause matches
    the TOC's clause pattern. A body page must produce no entries."""
    assert toc_from_pages([fixture("saoso_part_b")]) == []
```

- [ ] **Step 2: Run it and watch it fail**

```bash
python -m pytest knowledge/tests/test_toc_map.py -k "prints_it or no_contents_heading" -q
```
Expected: FAIL — `ImportError: cannot import name 'toc_from_pages'`.

- [ ] **Step 3: Implement page selection and the dict shape**

```python
# knowledge/sections/toc.py — add near the other regexes
#: The heading a contents page prints. Only pages carrying it are parsed: `TOC_CLAUSE`
#: matches a printed body clause too, so parsing the whole document would file body
#: headings as contents entries.
CONTENTS_HEADING = re.compile(r"(TABLE OF CONTENTS|^\s*CONTENTS\s*$)", re.IGNORECASE | re.MULTILINE)


def toc_from_pages(pages: Sequence[str]) -> list[TocEntry]:
    """In: extracted pages, in order. Out: the entries of the page(s) printing a contents list.

    In:  `pages` — raw or de-columned page text; `parse_toc` is indifferent to which
         (proved by `test_section_parsers.test_the_toc_parses_the_same_de_columned`).
    Out: `TocEntry` list in printed order; **empty** when no page prints a contents heading,
         which is the honest answer for a document with no TOC and the state every document
         ingested before this task is in.
    Side effects: none.
    Fails: never deliberately. A contents page that parses to nothing returns `[]` and the
        concordance falls back to headings.
    """
    selected = [page for page in pages if CONTENTS_HEADING.search(page)]
    return parse_toc("\f".join(selected)) if selected else []
```

```python
# knowledge/sections/toc.py — add to TocEntry
    def as_dict(self) -> dict:
        """The stored shape (`StandardDocument.toc`). A dict, not a tuple: the concordance
        reads `entry["label"]` and the field is JSONB."""
        return {
            "part": self.part,
            "kind": self.kind,
            "label": self.label,
            "title": self.title,
            "printed_page": self.printed_page,
        }
```

- [ ] **Step 4: Run the parser tests**

```bash
python -m pytest knowledge/tests/test_toc_map.py -q
```
Expected: PASS, including the pre-existing 29-entry assertions.

- [ ] **Step 5: Write the failing ingest test — through the real writer**

```python
# knowledge/tests/test_ingest.py
def test_ingest_stores_the_printed_toc(saoso_pdf, standard_set, stub_ingest_extraction):
    """Through `ingest_standard`, not by setting the field (`testing_hazards.md` §1.32):
    the claim is about what the writer stores, so the writer must produce it.
    """
    report = ingest_standard(
        pdf_path=saoso_pdf, standard_set=standard_set, doc_key="saoso", embed=False
    )

    toc = StandardDocument.objects.get(pk=report.document_id).toc

    assert len(toc) == 29
    assert {"part", "kind", "label", "title", "printed_page"} == set(toc[0])
    assert [e["label"] for e in toc if e["kind"] == "RANGE"] == ["10 to 19"]
```

- [ ] **Step 6: Run it and watch it fail**

```bash
python -m pytest knowledge/tests/test_ingest.py -k stored_the_printed_toc -q
```
Expected: FAIL — `assert 0 == 29` (the field exists, nothing writes it).

- [ ] **Step 7: Wire it into ingest**

```python
# knowledge/ingest.py, inside ingest_standard, immediately after `pages, layout_pages = ...`
        # The printed TOC is read from the *raw* pages, before de-columning and reflow: it is
        # a record of what the document prints, not of how we read the body.
        toc_pages = pages
```

```python
# knowledge/ingest.py, after `chunks = table_chunks`, before the transaction
    # Stored once per document (D68 §7.5). `--from-corpus` has no `pages`, so the PDF is read
    # again for this one purpose: the TOC is a property of the *printed* document, and the
    # reviewed artefact does not carry it.
    toc = [
        entry.as_dict()
        for entry in toc_from_pages(toc_pages if corpus_sections is None else extract_pages(path))
    ]
```

```python
# knowledge/ingest.py, in StandardDocument.objects.create(...)
            section_scheme=descriptor["section_scheme"],
            chunk_count=len(chunks),
            toc=toc,
```

Imports: `from knowledge.sections.toc import toc_from_pages` at the top of `ingest.py`.

- [ ] **Step 8: Run the ingest suite and the whole knowledge app**

```bash
python -m pytest knowledge -q
```
Expected: PASS. If another document's fixture pages contain a page with the word `CONTENTS`, its
`toc` is non-empty — check the assertion you are about to add rather than assuming.

- [ ] **Step 9: Commit**

```bash
git add knowledge/sections/toc.py knowledge/ingest.py knowledge/tests/test_toc_map.py knowledge/tests/test_ingest.py
git commit -m "feat(c2): read the printed TOC at ingest and store it"
```


---

### Task 3: The tree — branches, titles, the reserved range, and what is missing

One new module. It reads chunks and returns sections; it knows nothing about URLs
(`build_principles.md` §I) and nothing about `core`.

**Files:**
- Create: `knowledge/concordance.py`
- Test: `knowledge/tests/test_concordance.py`

- [ ] **Step 1: Write the failing test for the three grouping rules**

```python
# knowledge/tests/test_concordance.py
"""The tree is the document's own structure, derived from chunks.

The three rules below were found by running the derivation over the shipped corpus
(`CONCORDANCE_PRD` §10.1–10.3) and each silently mis-files passages if it is dropped.
"""

from __future__ import annotations

import pytest

from knowledge.concordance import concordance_sections
from knowledge.models import DocumentChunk, StandardDocument, StandardSet

pytestmark = pytest.mark.django_db


@pytest.fixture
def document(db) -> StandardDocument:
    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    return StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.1",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="0" * 64,
        section_scheme="saoso",
    )


def chunk(document, section_ref, page, text, heading_path="", anchor=""):
    return DocumentChunk.objects.create(
        document=document,
        section_ref=section_ref,
        heading_path=heading_path,
        page=page,
        text=text,
        anchor=anchor,
    )


def test_an_opening_chunk_stays_in_its_own_section(document):
    """SAOSO prints `1. DEFINITIONS` as a chunk with a reference and *no* heading.

    A heading-first grouping files the section's title page under the *next* section —
    the one thing a table of contents must never do (§10.1).
    """
    opener = chunk(document, "S1", 22, "1. DEFINITIONS")
    body = chunk(document, "S2.1", 30, "Ecosystem management.", "2. ORGANIC ECOSYSTEMS > 2.1 Ecosystem")

    sections = {section.key: section for section in concordance_sections(document)}

    assert [c.pk for c, _a in sections["S1"].passages] == [opener.pk]
    assert [c.pk for c, _a in sections["S2"].passages] == [body.pk]


def test_a_roman_heading_merges_with_its_decimal_body(document):
    """The OPP prints `§II` as the heading and numbers the body `2.1`–`2.5` (§10.2).

    Without the roman→decimal conversion the same section is two branches, one a stub.
    """
    stub = chunk(document, "§II", 1, "II. Membership fees")
    body = chunk(document, "§2.1", 1, "2.1 Membership Fees")

    sections = {c.pk: section for section in concordance_sections(document) for c, _a in section.passages}

    assert sections[stub.pk] is sections[body.pk]
    assert sections[stub.pk].key == "§2"


def test_a_heading_shared_by_several_branches_is_not_a_title(document):
    """SAOSO prints `APPENDICES` above Appendices 1–7 (§10.3): seven branches named after
    the divider give a reader no way to choose one."""
    for number in (1, 2):
        chunk(document, f"Appendix {number}", 70 + number, f"Appendix {number} body", "APPENDICES > x")

    titles = [section.title for section in concordance_sections(document)]

    assert "APPENDICES" not in titles
    assert titles == ["Appendix 1", "Appendix 2"]

```

- [ ] **Step 2: Run it and watch it fail**

```bash
python -m pytest knowledge/tests/test_concordance.py -q
```
Expected: FAIL — `ModuleNotFoundError: No module named 'knowledge.concordance'`.

- [ ] **Step 3: Write the module's grouping half**

```python
# knowledge/concordance.py
"""The document's own structure, as the reader's navigation (D68).

A branch is a **printed division**: the top-level reference a chunk carries (`S5.1.9` → `S5`,
`§4.5(2)(c)` → `§4`, `Appendix 2` whole), or — for a document that prints no numbering — the
first component of its heading trail. Nothing here is stored: the grouping is computed from
`DocumentChunk` per request, so it cannot drift from the corpus the way a second store would.

Three rules come from measurement, not taste (`CONCORDANCE_PRD` §10.1–10.3) and each is a test
in `knowledge/tests/test_concordance.py`:

1. grouping is by **reference first**, because a section's opening chunk carries the reference
   and no heading (`1. DEFINITIONS`);
2. a roman section heading converts to its decimal body (`§II` covers `2.1`–`2.5`);
3. a heading used by more than one branch is a **divider** (`APPENDICES`), never a title.

What a branch is *called* comes from the document's printed TOC when it has one (D68 §7.5),
because the alternative misnames the two branches a reader consults most (§10.5).

No `core` import (`build_principles.md` §I): this module knows documents and chunks, not URLs.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from knowledge.models import DocumentChunk, StandardDocument
from knowledge.reading import unique_anchors, reading_chunks

#: Roman section numbers the OPP prints beside decimal body numbering (`§II` covers `2.1`).
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}

#: Where a chunk with neither a reference nor a heading goes. Guessing instead would file a
#: document's front matter inside section 1, which is worse than naming it for what it is.
PRELIMINARY = "Preliminary pages"


def _ref_key(section_ref: str) -> str:
    """`S5.1.9` → `S5`, `§4.5(2)(c)` → `§4`, `§II` → `§2`, `Appendix 2` unchanged."""
    ref = section_ref.strip()
    for prefix in ("S", "§"):
        if ref.startswith(prefix):
            head = ref.split(".", 1)[0].strip()[len(prefix) :]
            if head.upper() in _ROMAN:
                return f"{prefix}{_ROMAN[head.upper()]}"
            return f"{prefix}{head}"
    return ref


def _branch_key(at: DocumentChunk) -> str:
    """Which branch a chunk belongs to: its reference, else its first heading, else the front."""
    if at.section_ref:
        return _ref_key(at.section_ref)
    if at.heading_path:
        return at.heading_path.split(" > ", 1)[0].strip()
    return PRELIMINARY


def _first_heading(chunks: list[DocumentChunk]) -> str | None:
    for at in chunks:
        if at.heading_path:
            return at.heading_path.split(" > ", 1)[0].strip()
    return None
```

- [ ] **Step 4: Write the section dataclass and the derivation**

```python
# knowledge/concordance.py — continue
@dataclass(frozen=True)
class ConcordanceSection:
    """One branch: a printed division, its passages, and — when the text has one — its name."""

    key: str
    title: str
    anchor: str
    page: int | None
    passages: tuple[tuple[DocumentChunk, str], ...] = ()
    #: True for a number the printed standard reserves and does not use (`10 to 19`).
    #: A reserved row is a row with no passages: the standard says these do not exist yet.
    reserved: bool = False

    @property
    def chunk_count(self) -> int:
        return len(self.passages)


def _match_key(label: str) -> str:
    """The key a TOC label and a branch key can be compared on.

    The TOC prints a clause as `5. …` and the body cites it as `S5.1.9`; the OPP prints `II.` and
    numbers `2.1`. Both name the same printed division, so the prefix has to come off or nothing
    ever matches. `Appendix 2` keeps its word: that is how both the TOC and the body print it.
    """
    ref = label.strip()
    if len(ref) > 1 and ref[0] in "S§" and ref[1].isdigit():
        return ref[1:]
    return ref


def _toc_title(entry: dict) -> str:
    """`1` + `Definitions` → `1. Definitions`; a range keeps its own wording."""
    label = entry["label"].strip()
    title = (entry.get("title") or "").strip()
    return f"{label}. {title}" if title else label


def _reference_title(key: str, chunks: list[DocumentChunk]) -> str:
    """The branch's own reference, made readable: `S1` → `Section 1`, `§I` stays `§I`."""
    section_ref = chunks[0].section_ref if chunks else None
    if section_ref and re.fullmatch(r"S\d+", section_ref):
        return f"Section {section_ref[1:]}"
    return section_ref or key

```

- [ ] **Step 5: Add the TOC match, the renderer, and the printed-order walk**

```python
# knowledge/concordance.py — continue
@dataclass(frozen=True)
class Concordance:
    """The tree, plus the printed sections the corpus does not hold."""

    sections: tuple[ConcordanceSection, ...]
    #: Printed sections with text that no branch covers — SAOSO's Section A (pp. 4–11) and
    #: Appendices A–C (pp. 93–96), measured 2026-10-27 (§10.6). The page states these; a
    #: tree of 22 branches presented as "the standard" would claim more than the corpus has.
    missing: tuple[str, ...] = ()


#: Branch titles that the document's own printed heading gets wrong. Reviewed data, keyed by
#: `(source_file, branch key)` in the same idiom as `knowledge.tables.TABLE_ROWS`: the
#: correction lives beside the corpus that needs it, and a test proves each entry both matches
#: a real branch and is used. Only entries for a document with *no* TOC belong here — where a
#: printed TOC exists it is the source of names, never a hand-written map (D68 §7.5).
REVIEWED_BRANCH_TITLES: dict[tuple[str, str], str] = {
    ("pgs_docs/PGS Certification landscape_Final.pdf", "R500"): "Cost of joining a PGS group",
    ("pgs_docs/PGS Certification landscape_Final.pdf", "PGS SA."): "Working with PGS South Africa",
}


def build_concordance(document: StandardDocument) -> Concordance:
    """In: a document. Out: its printed structure, one branch per division, in printed order.

    In:  nothing beyond the document.
    Out: `Concordance` — branches (with reserved rows interleaved where the printed TOC puts
         them) and the printed sections the corpus does not hold.
    Side effects: one query for the chunks.
    Fails: never deliberately. A document with no TOC and no headings is one branch.
    """
    pairs = unique_anchors(reading_chunks(document))
    order: list[str] = []
    grouped: dict[str, list[DocumentChunk]] = {}
    anchored: dict[str, list[tuple[DocumentChunk, str]]] = {}
    for at, anchor in pairs:
        key = _branch_key(at)
        if key not in grouped:
            order.append(key)
            grouped[key] = []
            anchored[key] = []
        grouped[key].append(at)
        anchored[key].append((at, anchor))

    headings = {key: _first_heading(grouped[key]) for key in order}
    shared = Counter(heading for heading in headings.values() if heading)
    toc: list[dict] = list(document.toc or [])
    reviewed = {
        key: title for (source, key), title in REVIEWED_BRANCH_TITLES.items()
        if source == document.source_file
    }

    def first_page(key: str) -> int | None:
        pages = [at.page for at in grouped[key] if at.page is not None]
        return min(pages) if pages else None

    #: TOC label → the branches that could answer to it. Section A prints `1. Introduction` on
    #: p4 and Section B prints `1. Definitions` on p22, so a label alone is not a match.
    by_label: dict[str, list[str]] = {}
    for key in order:
        by_label.setdefault(_match_key(key), []).append(key)

    def branch_for(entry: dict) -> str | None:
        """The branch this TOC entry names, or None when the corpus does not hold it.

        Label **and** printed page must agree, which is a measurement rather than a guess: every
        section the corpus holds matches its TOC entry's printed page exactly (22, 30, 33 … 76,
        70), and the two entries that share a label differ only in page (4 vs 22). A page-less
        entry falls back to the label, because a reserved row or a reprint may omit it.
        """
        keys = [key for key in by_label.get(_match_key(entry["label"]), []) if key not in matched]
        if not keys:
            return None
        page = entry.get("printed_page")
        if page is None:
            return keys[0]
        exact = [key for key in keys if first_page(key) == page]
        return exact[0] if exact else None

    def render(key: str, entry: dict | None = None) -> ConcordanceSection:
        passages = tuple(anchored[key])
        heading = headings[key]
        if entry is not None:
            title = _toc_title(entry)
        elif key in reviewed:
            title = reviewed[key]
        elif heading and shared[heading] == 1:
            title = heading
        else:
            title = _reference_title(key, grouped[key])
        return ConcordanceSection(
            key=key, title=title, anchor=passages[0][1], page=first_page(key), passages=passages
        )

    # Printed order: walk the TOC so a reserved row lands between §9 and §20 where the standard
    # prints it, then append any branch the TOC does not mention (a document with no TOC, or a
    # section the TOC omits) in document order.
    sections: list[ConcordanceSection] = []
    matched: set[str] = set()
    missing: list[str] = []
    for entry in toc:
        if entry.get("kind") == "RANGE":
            sections.append(
                ConcordanceSection(
                    key=_match_key(entry["label"]),
                    title=_toc_title(entry),
                    anchor=slugify(entry["label"]),
                    page=entry.get("printed_page"),
                    reserved=True,
                )
            )
            continue
        key = branch_for(entry)
        if key is None:
            # Printed, and not in the corpus. Not an error: Section A and Appendices A–C are
            # absent today (§10.6), and the page says so instead of pretending they are not there.
            missing.append(_toc_title(entry))
            continue
        matched.add(key)
        sections.append(render(key, entry))

    for key in order:
        if key not in matched:
            sections.append(render(key))

    return Concordance(sections=tuple(sections), missing=tuple(missing))


def concordance_sections(document: StandardDocument) -> list[ConcordanceSection]:
    """The branches alone. A thin alias, so a test can name what it is asserting."""
    return list(build_concordance(document).sections)
```

Imports to add: `from django.utils.text import slugify`.

- [ ] **Step 6: Run the grouping tests**

```bash
python -m pytest knowledge/tests/test_concordance.py -q
```
Expected: PASS (3 tests). If the shared-heading test fails, the divider rule is missing — do not
weaken the test.

- [ ] **Step 7: Write the failing tests for names, reserved rows and the missing list**

```python
# knowledge/tests/test_concordance.py — append
def test_a_branch_is_named_from_the_printed_toc(document):
    """The TOC is the only source that names a branch correctly (§10.5): `S1`'s chunks carry
    no heading at all, and Appendix 2's first heading names its first sub-table."""
    document.toc = [
        {"part": "B", "kind": "CLAUSE", "label": "1", "title": "Definitions", "printed_page": 22},
        {"part": "B", "kind": "RANGE", "label": "10 to 19",
         "title": "Left blank to facilitate future enterprises", "printed_page": None},
        {"part": "B", "kind": "APPENDIX", "label": "Appendix 2",
         "title": "Fertilizers Conditioners and Soil Conditioners", "printed_page": 76},
    ]
    document.save(update_fields=["toc"])
    chunk(document, "S1", 22, "1. DEFINITIONS")
    chunk(document, "Appendix 2", 76, "Farmyard manure, slurry and urine",
          "Appendix 2 - Farmyard manure, slurry and urine")

    sections = concordance_sections(document)

    assert [s.title for s in sections] == [
        "1. Definitions",
        "10 to 19. Left blank to facilitate future enterprises",
        "Appendix 2. Fertilizers Conditioners and Soil Conditioners",
    ]


def test_a_reserved_row_has_no_passages(document):
    """`10 to 19. Left blank…` is a row a reader can see and cannot open (§10.8)."""
    document.toc = [{"part": "B", "kind": "RANGE", "label": "10 to 19",
                     "title": "Left blank to facilitate future enterprises", "printed_page": None}]
    document.save(update_fields=["toc"])
    chunk(document, "S9", 57, "9. AQUACULTURE")

    reserved = [s for s in concordance_sections(document) if s.reserved]

    assert len(reserved) == 1
    assert reserved[0].chunk_count == 0
    assert reserved[0].anchor == "10-to-19"


def test_the_tree_reports_the_printed_sections_the_corpus_does_not_hold(document):
    """Section A prints clauses 1–3 on pp. 4–11 and Section C prints Appendices A–C on
    pp. 93–96; neither is ingested (§10.6). The page must be able to say so."""
    document.toc = [
        {"part": "A", "kind": "CLAUSE", "label": "1", "title": "Introduction", "printed_page": 4},
        {"part": "A", "kind": "CLAUSE", "label": "2", "title": "General", "printed_page": 7},
        {"part": "B", "kind": "CLAUSE", "label": "1", "title": "Definitions", "printed_page": 22},
        {"part": "C", "kind": "APPENDIX", "label": "Appendix A", "title": "SAOSO Organic Logos",
         "printed_page": 93},
    ]
    document.save(update_fields=["toc"])
    chunk(document, "S1", 22, "1. DEFINITIONS")

    concordance = build_concordance(document)

    assert [s.title for s in concordance.sections] == ["1. Definitions"]
    assert concordance.missing == (
        "1. Introduction", "2. General", "Appendix A. SAOSO Organic Logos",
    )
```

- [ ] **Step 8: Run them; they should fail f
ail for the right reason**

```bash
python -m pytest knowledge/tests/test_concordance.py -q
```
Expected: the two failed lookups are `title == "Section 1"` (not `1. Definitions`) and
`missing == ()`. Nothing else.

- [ ] **Step 9: Make them pass, then run the app's suite**

```bash
python -m pytest knowledge -q
```
Expected: PASS.

- [ ] **Step 10: The reviewed-title tests, through the real ingest**

Add `from knowledge.concordance import build_concordance, concordance_sections`,
`from knowledge.reading import reading_chunks` and `from knowledge.concordance import _branch_key`
to the test module's imports (a private name is acceptable *in a test that asserts the data matches
the corpus*).

```python
# knowledge/tests/test_concordance.py — append
def test_the_landscape_branches_are_named_for_what_they_are(standard_set):
    """Measured 2026-10-27: the certification landscape's heading scheme reads a price line
    (`R500`) and a truncation (`PGS SA.`) as headings, so two of six branches were named after
    table cells (§10.5). Reviewed titles live in `REVIEWED_BRANCH_TITLES`.

    Ingested, not hand-built: the claim is about what the ingest and the derivation produce
    together (`testing_hazards.md` §1.32).
    """
    report = ingest_standard(
        pdf_path=PDFS["landscape"], standard_set=standard_set, doc_key="landscape", embed=False
    )
    document = StandardDocument.objects.get(pk=report.document_id)

    titles = [section.title for section in concordance_sections(document)]

    assert "R500" not in titles, "a price line is still a branch title"
    assert "Cost of joining a PGS group" in titles
    assert "Working with PGS South Africa" in titles


def test_every_reviewed_title_matches_a_real_branch(standard_set):
    """A reviewed correction that matches nothing is a stale entry: it must fail rather than
    sit there looking authoritative (the `CORPUS_EDITS` idiom)."""
    report = ingest_standard(
        pdf_path=PDFS["landscape"], standard_set=standard_set, doc_key="landscape", embed=False
    )
    document = StandardDocument.objects.get(pk=report.document_id)
    keys = {_branch_key(at) for at in reading_chunks(document)}

    for (source, key) in REVIEWED_BRANCH_TITLES:
        if source == document.source_file:
            assert key in keys, f"reviewed title for {key!r} matches no branch"
```

- [ ] **Step 11: Run and commit**

```bash
python -m pytest knowledge/tests/test_concordance.py -q
git add knowledge/concordance.py knowledge/tests/test_concordance.py
git commit -m "feat(c3): the tree — branches, TOC titles, reserved rows, what is missing"
```

---

### Task 4: An anchor is a property of the text, not of its position

**This is the Q8 / D68 fix, and it is a bug fix before it is a feature.**
Measured 2026-10-27: **57 of 366 passages share a citation anchor**; the reader adds `-2`, `-3` …,
and `Citation.reading_anchor` does not, so a citation to 29 of Appendix 2's 30 rows opens the first
one. The numeric suffix is ingest order — a sequential id on a public surface (`build_principles.md` §I).

**Compatibility rule:** the *first* passage of a group keeps the bare anchor it has today, so every
link shipped on 2026-10-27 still resolves to the same passage. Only the second and later passages
change, and they change to something derived from their own words.

**Files:**
- Modify: `knowledge/reading.py`
- Create: `knowledge/tests/test_anchors.py`

- [ ] **Step 1: Write the failing unit test**

```python
# knowledge/tests/test_anchors.py
"""The anchor a citation carries must identify the passage it quotes.

Measured 2026-10-27: 57 of 366 passages share their reference (Appendix 2 ×30, `S1` ×8,
`Appendix 1` ×6 …), so a reference alone is not an identifier. The disambiguator is derived from
the passage's own words, never from its index: an index-derived suffix repoints at a different
substance when a row is inserted into the reviewed artefact and the document is re-ingested
(`testing_hazards.md` §0 — a wrong answer that still resolves).
"""

from __future__ import annotations

import pytest

from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.reading import unique_anchors

pytestmark = pytest.mark.django_db


@pytest.fixture
def document(db) -> StandardDocument:
    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    return StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.1",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="0" * 64,
        section_scheme="saoso",
    )


def test_the_first_passage_of_a_group_keeps_the_bare_anchor(document):
    """Backwards compatibility: links shipped on 2026-10-27 carry `#appendix-2` and they must
    keep landing on the passage they land on today."""
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=76,
                                 text="Farmyard manure, slurry and urine")
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=76, text="Guano")

    anchors = [anchor for _chunk, anchor in unique_anchors(list(document.chunks.order_by("id")))]

    assert anchors[0] == "appendix-2"


def test_a_shared_reference_is_disambiguated_by_the_passage_itself(document):
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=76,
                                 text="Farmyard manure, slurry and urine")
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=77,
                                 text="Wood, bark and sawdust, only if not chemically treated.")

    anchors = [anchor for _chunk, anchor in unique_anchors(list(document.chunks.order_by("id")))]

    assert anchors[1] == "appendix-2-wood-bark-and-sawdust", "an index-derived suffix is not a locator"


def test_the_suffix_does_not_move_when_an_earlier_row_is_inserted(document):
    """The property the numeric suffix cannot have: inserting a passage before an existing one
    must not rename the existing one."""
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=76,
                                 text="Farmyard manure, slurry and urine")
    wood = DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=77,
                                       text="Wood, bark and sawdust, only if not chemically treated.")
    before = dict((chunk.pk, anchor) for chunk, anchor in unique_anchors(list(document.chunks.order_by("id"))))

    # A row is reviewed into the middle of the appendix: new chunk, lower id is impossible, but
    # a re-ingest rebuilds the whole table, so order it as the artefact now prints it.
    document.chunks.all().delete()
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=76,
                                 text="Farmyard manure, slurry and urine")
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=76,
                                 text="Guano")
    wood_after = DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=77,
                                             text="Wood, bark and sawdust, only if not chemically treated.")
    after = dict((chunk.pk, anchor) for chunk, anchor in unique_anchors(list(document.chunks.order_by("id"))))

    assert after[wood_after.pk] == before[wood.pk] == "appendix-2-wood-bark-and-sawdust"

```

- [ ] **Step 2: Run and watch it fail**

```bash
python -m pytest knowledge/tests/test_anchors.py -q
```
Expected: FAIL on the second and third tests — `appendix-2-2` instead of
`appendix-2-wood-bark-and-sawdust`.

- [ ] **Step 3: Replace the numeric suffix**

```python
# knowledge/reading.py — replace the body of unique_anchors and add the two helpers above it
#: How much of a passage's own words may appear in its anchor: the first few words, so the anchor
#: reads like a locator a person can check in the URL (`#appendix-2-wood-bark-and-sawdust`) rather
#: than a hash, and stays short enough to be one.
DISAMBIGUATOR_WORDS = 4
MAX_DISAMBIGUATOR_CHARS = 40


def _content_slug(chunk: DocumentChunk) -> str:
    """A slug of the passage's own words: its content anchor, else its first line, else its heading.

    The order is deliberate. `anchor` is already content-derived (the ingest sets it for a block the
    source never numbered), then the printed first line, then the last heading — so the
    disambiguator is a property of the text in every case, and of the file only when the text is
    empty. Words, not characters: a 40-character cut leaves `…only-if-not-chemica`, which reads as
    a typo rather than a locator.
    """
    for candidate in (
        chunk.anchor,
        (chunk.text or "").split("\n", 1)[0],
        chunk.heading_path.split(" > ")[-1],
    ):
        slug = _slugify_locator(candidate) if candidate and candidate.strip() else ""
        if slug:
            words = slug.split("-")[:DISAMBIGUATOR_WORDS]
            # A slug that ends on a connective reads like a typo (`…slurry-and`). Cheapest fix
            # in the world, and the anchor is a thing a person may read in the address bar.
            while len(words) > 1 and words[-1] in {"and", "or", "of", "the", "with", "for", "to"}:
                words.pop()
            return "-".join(words)[:MAX_DISAMBIGUATOR_CHARS].strip("-")
    return "passage"


def unique_anchors(chunks: list[DocumentChunk]) -> list[tuple[DocumentChunk, str]]:
    """In: chunks in order. Out: `(chunk, anchor)` with the anchor unique within the document.

    The **first** passage of a shared reference keeps the bare anchor, because that is the anchor
    every citation shipped before 2026-10-27 carries (`#appendix-2`); later ones are suffixed with
    a slug of their own words (`#appendix-2-wood-bark-and-sawdust`). The old `-2`, `-3` suffix is
    gone: it was ingest order wearing a locator's clothes (`build_principles.md` §I).

    A numeric suffix survives only as a last resort, when two passages begin with the same words —
    and then the anchor is still stable for unchanged text.
    """
    used: set[str] = set()
    pairs: list[tuple[DocumentChunk, str]] = []
    for chunk in chunks:
        base = reading_anchor(chunk.section_ref, chunk.anchor, chunk.heading_path)
        if base not in used:
            used.add(base)
            pairs.append((chunk, base))
            continue
        candidate = f"{base}-{_content_slug(chunk)}"
        attempt = 1
        while candidate in used:
            attempt += 1
            candidate = f"{base}-{attempt}"
        used.add(candidate)
        pairs.append((chunk, candidate))
    return pairs


def passage_anchors(source_files: list[str] | tuple[str, ...]) -> dict[int, str]:
    """In: the source files a turn cites. Out: `{chunk_id: anchor}` for every chunk in them.

    In:  `source_files` — `StandardDocument.source_file` values (2–4 per answer).
    Out: a map for every chunk of those documents. One entry per chunk, unique within its
         document, produced by `unique_anchors` — the same function the reader uses.
    Side effects: one query for the document ids, one per document.
    Fails: never deliberately. A source file with no chunks contributes nothing.

    It exists because a citation arrives with a chunk, not with the chunk's position among its
    siblings: `Citation.reading_anchor` cannot know whether the passage it quotes is the first
    of its reference, so it asks the same function the page does.
    """
    document_ids = (
        DocumentChunk.objects.filter(document__source_file__in=list(source_files))
        .values_list("document_id", flat=True)
        .distinct()
    )
    anchors: dict[int, str] = {}
    for document_id in document_ids:
        chunks = list(DocumentChunk.objects.filter(document_id=document_id).order_by("id"))
        anchors.update({chunk.pk: anchor for chunk, anchor in unique_anchors(chunks)})
    return anchors
```

- [ ] **Step 4: Run the unit tests**

```bash
python -m pytest knowledge/tests/test_anchors.py knowledge/tests/test_reading.py -q
```
Expected: PASS. `test_reading.py` still passes because its three fixture chunks have distinct
references.

- [ ] **Step 5: The guard — over the real corpus, not a fixture**

```python
# knowledge/tests/test_anchors.py — append
def test_every_passage_of_the_real_corpus_resolves_to_itself():
    """The guard D68 asks for, and the one that would have caught the defect.

    A fixture of three chunks with one duplicate passes while 57 real passages are wrong
    (`testing_hazards.md` §1.33). This walks the ingested corpus: for every passage, the anchor
    a citation would carry must resolve to that passage and to no other.

    Skips (loudly) when no corpus is ingested — run it on a machine with the corpus:
        python manage.py ingest_standard --doc saoso --file 'pgs_docs/saoso-version-2.1-2026.pdf'
    """
    from knowledge.concordance import build_concordance

    documents = list(StandardDocument.objects.all())
    if not documents:
        pytest.skip("no corpus ingested on this instance — this guard needs the real corpus")

    #: anchor → the passages that anchor names. Exactly one is the only correct answer.
    resolved: dict[str, set[int]] = {}
    for document in documents:
        for section in build_concordance(document).sections:
            for chunk, anchor in section.passages:
                resolved.setdefault(anchor, set()).add(chunk.pk)

    ambiguous = {anchor: pks for anchor, pks in resolved.items() if len(pks) > 1}

    assert ambiguous == {}, f"{len(ambiguous)} anchors name more than one passage: {list(ambiguous)[:5]}"
```

- [ ] **Step 6: Run it — and check the guard can fail**

Break `_content_slug` on purpose (return `"passage"`), run this test, watch it fail, restore. If it
stays green with a constant slug, the test is decoration.

```bash
python -m pytest knowledge/tests/test_anchors.py -q
```

- [ ] **Step 7: Commit**

```bash
git add knowledge/reading.py knowledge/tests/test_anchors.py
git commit -m "fix(chat): a passage anchor is its own words, not its index"
```

---

### Task 5: The citation and the search list use the same anchors as the page

⚠️ **Touches `core/services/_chatbot.py`, which a concurrent session is editing — see §0.1.**

**Files:**
- Modify: `core/services/_chatbot.py`, `knowledge/reading.py` (`search_in_document`)
- Test: `core/tests/test_chat_grounding.py`, `knowledge/tests/test_reading.py`

- [ ] **Step 1: Write the failing test for the search list**

```python
# knowledge/tests/test_reading.py — append
def test_a_search_hit_carries_the_anchor_that_names_its_own_passage(document):
    """The hit list links to the passage it quotes. Before 2026-10-27 every hit on a shared
    reference linked to the group's first passage (`CONCORDANCE_PRD` §10.7)."""
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=76,
                                 text="Farmyard manure, slurry and urine")
    DocumentChunk.objects.create(document=document, section_ref="Appendix 2", page=77,
                                 text="Wood, bark and sawdust, only if not chemically treated.")

    hits = search_in_document(document, "sawdust")

    assert [hit.anchor for hit in hits] == ["appendix-2-wood-bark-and-sawdust"]
```

- [ ] **Step 2: Run it and watch it fail**

```bash
python -m pytest knowledge/tests/test_reading.py -k names_its_own_passage -q
```
Expected: FAIL — `['appendix-2']`.

- [ ] **Step 3: Pass the anchors in**

```python
# knowledge/reading.py — search_in_document gains an optional map
def search_in_document(
    document: StandardDocument,
    query: str,
    *,
    limit: int = 20,
    anchors: dict[int, str] | None = None,
) -> list[SearchHit]:
```

and in `_hit(chunk, words, anchors)` use `anchors.get(chunk.pk) or reading_anchor(...)`. In
`search_in_document`, default `anchors` to
`{chunk.pk: anchor for chunk, anchor in unique_anchors(reading_chunks(document))}` when it is
`None` — one query, and the caller that already has the map passes it.

- [ ] **Step 4: Run it**

```bash
python -m pytest knowledge/tests/test_reading.py -q
```
Expected: PASS.

- [ ] **Step 5: Write the failing test for a citation's anchor**

```python
# core/tests/test_chat_grounding.py — append
def test_a_citation_carries_the_anchor_of_the_passage_it_quotes(seeded_corpus):
    """`Citation.reading_anchor` must be the same string the reader uses for that chunk.

    The second Appendix 2 row is the case that fails today: both rows are cited `Appendix 2`,
    and the citation resolves to the first (`CONCORDANCE_PRD` §10.7).
    """
    from core.services._chatbot import _citation_anchors
    from knowledge.models import DocumentChunk
    from knowledge.services import RetrievedChunk

    second = DocumentChunk.objects.filter(section_ref="Appendix 2").order_by("id")[1]
    matched = RetrievedChunk(
        chunk_id=second.pk, document_title="SAOSO", document_version="2.1",
        section_ref="Appendix 2", heading_path="", page=second.page,
        anchor="", text=second.text, score=1.0,
        document_source_file=second.document.source_file,
    )

    assert _citation_anchors([matched])[second.pk].startswith("appendix-2-")
```

- [ ] **Step 6: Run it and watch it fail**

```bash
python -m pytest core/tests/test_chat_grounding.py -k carries_the_anchor -q
```
Expected: FAIL — `ImportError: cannot import name '_citation_anchors'`.

- [ ] **Step 7: Add the resolver and use it**

```python
# core/services/_chatbot.py, beside the citation builder
def _citation_anchors(matched: list[RetrievedChunk]) -> dict[int, str]:
    """In: the chunks a turn actually cited. Out: `{chunk_id: reading anchor}`.

    In:  `matched` — audited citations, so at most `MAX_CITATIONS` chunks.
    Out: the map `passage_anchors` produces, scoped to the documents those chunks came from.
    Side effects: one query, plus one per cited document.
    Fails: never deliberately. A chunk missing from the map falls back to its own reference,
        which is today's behaviour and still lands in the right branch.
    """
    sources = sorted({c.document_source_file for c in matched if c.document_source_file})
    return passage_anchors(sources) if sources else {}
```

then in the citation loop (around `reading_anchor=reading_anchor(...)`):

```python
        anchors = _citation_anchors([matched for matched in ...])   # collect first, then assign
        ...
                reading_anchor=anchors.get(matched.chunk_id) or reading_anchor(
                    matched.section_ref, matched.anchor, matched.heading_path
                ),
```

Build `anchors` **once per turn**, before the loop over `raw_citations`: the candidates are already
in the address book, so use `{chunk.chunk_id for candidates in book.values() for chunk in candidates}`
to scope it, or collect the accepted `matched` chunks in a first pass. Do not query per citation.

- [ ] **Step 8: Run the chat suites**

```bash
python -m pytest core/tests/test_chat_grounding.py core/tests/test_chatbot_guardrails.py core/tests/test_ask_answer_page.py -q
```
Expected: PASS. Any assertion that expected a `-2` suffix is now wrong and must be updated to the
content anchor — check each one against the database rather than renaming it.

- [ ] **Step 9: Commit**

```bash
git add core/services/_chatbot.py knowledge/reading.py core/tests/test_chat_grounding.py knowledge/tests/test_reading.py
git commit -m "fix(chat): the citation, the search list and the page agree on an anchor"
```

---

### Task 6: The reader service returns a tree and one open branch

**Files:**
- Modify: `core/services/_documents.py`, `knowledge/reading.py` (delete `contents`, `ReadingEntry`)
- Test: `core/tests/test_document_reader.py`

- [ ] **Step 1: Write the failing service tests**

```python
# core/tests/test_document_reader.py — append
def test_the_reader_opens_the_first_branch_when_nothing_selects_one(seeded_documents):
    """No `?section=`: the document's beginning, not a wall of text."""
    from core.services._documents import reader_for

    reader = reader_for(PublicDocument.objects.get(code="saoso-standard-v2.1"))

    assert reader.selected is not None
    assert reader.selected.anchor == reader.sections[0].anchor
    assert all(p.anchor.startswith("appendix-2") for p in reader.passages)


def test_a_citation_anchor_selects_the_branch_that_contains_it(seeded_documents):
    """A citation names a *passage*; the tree navigates by *section*. The join is the feature."""
    from core.services._documents import reader_for

    reader = reader_for(PublicDocument.objects.get(code="saoso-standard-v2.1"), section="appendix-2-1")

    assert reader.selected.key == "Appendix 2.1"
    assert [p.text for p in reader.passages] == ["Wood, bark and sawdust, only if not chemically treated."]


def test_an_unknown_section_falls_back_rather_than_404ing(seeded_documents):
    """A stale link must still show the document it names."""
    from core.services._documents import reader_for

    reader = reader_for(PublicDocument.objects.get(code="saoso-standard-v2.1"), section="no-such-thing")

    assert reader.selected.key == reader.sections[0].key


def test_only_the_open_branch_is_returned(seeded_documents):
    """The weight reduction is a property of the service, so it is asserted here and not
    inferred from a page-size measurement."""
    from core.services._documents import reader_for

    reader = reader_for(PublicDocument.objects.get(code="saoso-standard-v2.1"), section="appendix-2")

    assert len(reader.sections) == 2
    assert [p.locator for p in reader.passages] == ["Appendix 2"]
```

- [ ] **Step 2: Run them and watch them fail**

```bash
python -m pytest core/tests/test_document_reader.py -q
```
Expected: FAIL — `TypeError: reader_for() got an unexpected keyword argument 'section'`.

- [ ] **Step 3: Change the `Reader` and the function**

```python
# core/services/_documents.py
from knowledge.concordance import ConcordanceSection, build_concordance
from knowledge.reading import SearchHit, search_in_document, unique_anchors, reading_chunks


@dataclass(frozen=True)
class Reader:
    """Everything `/documents/<code>/read/` renders — the concordance.

    One section at a time, with the document's own structure as the navigation: the reader is
    the standard's table of contents, not a page of text with a list beside it. That is also what
    makes the page light — only the selected branch is rendered, so a 319-passage document costs
    one branch's markup instead of 333 KB of it (D68).
    """

    document: PublicDocument
    corpus: StandardDocument | None
    sections: tuple[ConcordanceSection, ...]
    selected: ConcordanceSection | None
    passages: tuple[ReaderPassage, ...]
    #: Printed sections with text that no branch covers — stated on the page (§10.6).
    missing: tuple[str, ...]
    hits: tuple[SearchHit, ...]
    query: str
    section: str


def _select_section(sections: list[ConcordanceSection], wanted: str) -> ConcordanceSection | None:
    """Which branch the reader is on. Accepts a branch anchor **or** any passage anchor.

    Both are needed and they are not the same thing: the tree navigates by section, while a
    citation names a passage (`s20-1-1`), and a citation's link must land on the branch that
    contains that passage. An unknown value falls back to the first branch rather than 404ing —
    a stale link should still show the reader the document.
    """
    if not sections:
        return None
    if not wanted:
        return sections[0]
    for section in sections:
        if section.anchor == wanted:
            return section
    for section in sections:
        if any(anchor == wanted for _chunk, anchor in section.passages):
            return section
    return sections[0]


def reader_for(document: PublicDocument, query: str = "", section: str = "") -> Reader:
    """In: a published document, what the reader searched for, and which branch. Out: a `Reader`.

    In:  `query` — free text from the search box; `section` — the branch to open, by branch
         anchor or by any passage anchor (a citation names a passage, not a section).
    Out: the document's section tree (including reserved rows), the selected branch, that
         branch's passages, the printed sections the corpus does not hold, and any search hits —
         searched across the **whole** document, not the open branch, because a reader who
         searches is looking for where a word is, not whether it is here.
    Side effects: at most four queries.
    Fails: never. A published document whose text has not been ingested returns `corpus=None`;
        the view explains, because a citation pointing here must not 404.
    """
    document_row = corpus_for(document)
    if document_row is None:
        return Reader(document, None, (), None, (), (), (), query.strip(), section.strip())

    concordance = build_concordance(document_row)
    sections = list(concordance.sections)
    selected = _select_section(sections, section.strip())
    pairs = {
        chunk.pk: anchor for chunk, anchor in unique_anchors(reading_chunks(document_row))
    }
    passages = tuple(
        ReaderPassage(
            anchor=pairs[chunk.pk],
            locator=chunk.section_ref or chunk.anchor or chunk.heading_path or f"p{chunk.page}",
            page=chunk.page,
            heading_path=chunk.heading_path,
            text=chunk.text,
        )
        for chunk, _anchor in (selected.passages if selected is not None else ())
    )
    return Reader(
        document=document,
        corpus=document_row,
        sections=tuple(sections),
        selected=selected,
        passages=passages,
        missing=concordance.missing,
        hits=tuple(search_in_document(document_row, query, anchors=pairs)) if query.strip() else (),
        query=query.strip(),
        section=section.strip(),
    )
```

- [ ] **Step 4: Delete the flat-view code**

```bash
# `contents()` and `ReadingEntry` are now unused; the tree replaces them.
grep -rn "contents(\|ReadingEntry" --include=*.py . | grep -v "/tests/"
```
Remove `contents()`, `ReadingEntry` and their `__all__` entries from `knowledge/reading.py`; delete
the two `contents` tests in `knowledge/tests/test_reading.py` (their property — one anchor per chunk,
in order — is now asserted by `test_anchors.py`).

- [ ] **Step 5: Run the reader tests**

```bash
python -m pytest core/tests/test_document_reader.py knowledge/tests/test_reading.py -q
```
Expected: PASS, except the tests in `test_document_reader.py` that assert on the old flat page —
those are Task 7's, and they will be rewritten there.

- [ ] **Step 6: Commit**

```bash
git add core/services/_documents.py knowledge/reading.py knowledge/tests/test_reading.py core/tests/test_document_reader.py
git commit -m "feat(c4): the reader service returns a tree and one open branch"
```

---

### Task 7: The route — `?section=`, a per-branch title, and a canonical link

**Files:**
- Modify: `core/views/_documents.py`, `core/services/_documents.py`
- Test: `core/tests/test_document_reader.py`

- [ ] **Step 1: Write the failing tests**

```python
# core/tests/test_document_reader.py — append
def test_a_branch_is_in_the_title_and_canonical_link(client, seeded_documents):
    """D68 §7.7: the standard's own words at a stable address are the one surface where SEO is
    honest — so a branch says which branch it is, and names one address for itself."""
    body = client.get("/documents/saoso-standard-v2.1/read/?section=appendix-2").content.decode()

    assert "<title>SAOSO Organic Standard v2.1 — Appendix 2" in body
    assert 'rel="canonical"' in body
    assert 'href="http://testserver/documents/saoso-standard-v2.1/read/?section=appendix-2"' in body


def test_the_page_renders_one_branch_and_says_nothing_about_the_others(client, seeded_documents):
    body = client.get("/documents/saoso-standard-v2.1/read/?section=appendix-2").content.decode()

    assert "free of significant contaminants" in body
    assert "Wood, bark and sawdust" not in body


def test_the_tree_marks_the_open_branch(client, seeded_documents):
    body = client.get("/documents/saoso-standard-v2.1/read/?section=appendix-2-1").content.decode()

    assert 'aria-current="page"' in body
```

- [ ] **Step 2: Run them and watch them fail**

```bash
python -m pytest core/tests/test_document_reader.py -q
```
Expected: FAIL — the title is the old one and there is no canonical link.

- [ ] **Step 3: Put the branch's identity in the service, not the template**

```python
# core/services/_documents.py — add to Reader
    @property
    def title(self) -> str:
        """The document and the open branch — what a `<title>` says, and what a search result
        shows. A branch page is about a section, not about the whole document."""
        if self.selected is None:
            return self.document.title
        return f"{self.document.title} — {self.selected.title}"

    @property
    def canonical_path(self) -> str:
        """The one address for this branch. The `?section=` form, because the branch has to
        travel in the query string: a browser never sends the fragment to the server (§6.4)."""
        base = reverse("core:document_reader", kwargs={"code": self.document.code})
        return f"{base}?section={self.selected.anchor}" if self.selected else base
```

- [ ] **Step 4: Wire the view (still under 20 lines)**

```python
# core/views/_documents.py
    reader = reader_for(
        document,
        request.GET.get("q", ""),
        request.GET.get("section", ""),
    )
    page = Page(
        key="document-reader",
        title=reader.title,
        description=(
            f"{reader.document.title}, as we ingested it — the branch a citation names, "
            "with the passages it quotes."
        ),
        eyebrow="The documents",
        heading=document.title,
        lede=(
            "The standard's own structure, section by section, as we ingested it. Choose a "
            "section, search the whole document, or follow a citation straight to the line "
            "it quotes."
        ),
    )
    return render(
        request,
        "public/document_reader.html",
        chrome_context(page) | {"reader": reader, "canonical": request.build_absolute_uri(reader.canonical_path)},
    )
```

- [ ] **Step 5: Run and commit**

```bash
python -m pytest core/tests/test_document_reader.py -q
git add core/views/_documents.py core/services/_documents.py core/tests/test_document_reader.py
git commit -m "feat(c5): ?section= selects a branch, and a branch names itself"
```

---

### Task 8: The template — tree, pane, crumb, and the omission note

**Files:**
- Modify: `core/templates/public/document_reader.html`
- Test: `core/tests/test_document_reader.py`

- [ ] **Step 1: Write the failing tests**

```python
# core/tests/test_document_reader.py — append
def test_the_page_states_the_printed_sections_it_does_not_hold(client, seeded_documents):
    """§10.6: the corpus is 22 of 28 printed sections. A tree presented as "the standard"
    would claim more than the corpus holds, so the page says what is absent."""
    document = StandardDocument.objects.get(source_file="pgs_docs/saoso-version-2.1-2026.pdf")
    document.toc = [{"part": "A", "kind": "CLAUSE", "label": "3",
                     "title": "Minimum Inspection Requirements", "printed_page": 11}]
    document.save(update_fields=["toc"])

    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()

    assert "not in the corpus" in body
    assert "Minimum Inspection Requirements" in body


def test_a_reserved_row_is_visible_and_is_not_a_link(client, seeded_documents):
    """`10 to 19. Left blank…`: a reader can see it, and cannot open it, because it is not text."""
    document = StandardDocument.objects.get(source_file="pgs_docs/saoso-version-2.1-2026.pdf")
    document.toc = [{"part": "B", "kind": "RANGE", "label": "10 to 19",
                     "title": "Left blank to facilitate future enterprises", "printed_page": None}]
    document.save(update_fields=["toc"])

    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()

    assert "Left blank to facilitate future enterprises" in body
    assert 'href="?section=10-to-19"' not in body


def test_a_search_hit_links_to_its_own_passage(client, seeded_documents):
    body = client.get("/documents/saoso-standard-v2.1/read/?q=sawdust").content.decode()

    assert 'href="?section=appendix-2-1#appendix-2-1"' in body
```

- [ ] **Step 2: Run them and watch them fail**

```bash
python -m pytest core/tests/test_document_reader.py -q
```
Expected: FAIL — no omission note, no reserved row, and the hit link is still `href="#…"`.

- [ ] **Step 3: Replace the contents list with the tree, and the passage column with the pane**

```django
{# core/templates/public/document_reader.html — replace the `reader__body` div #}
        <div class="reader__body">
          <nav class="reader__tree" aria-label="Document contents">
            <p class="reader__tree-title">Contents</p>
            <ol class="reader__tree-list">
              {% for branch in reader.sections %}
                <li>
                  {% if branch.reserved %}
                    <span class="reader__tree-link reader__tree-link--reserved">
                      <span class="reader__tree-name">{{ branch.title }}</span>
                    </span>
                  {% else %}
                    <a class="reader__tree-link"
                       href="?section={{ branch.anchor }}#{{ branch.anchor }}"
                       {% if reader.selected and branch.anchor == reader.selected.anchor %}aria-current="page"{% endif %}>
                      <span class="reader__tree-name">{{ branch.title }}</span>
                      {% if branch.page %}<span class="reader__page">p. {{ branch.page }}</span>{% endif %}
                    </a>
                  {% endif %}
                </li>
              {% endfor %}
            </ol>

            {% comment %} A tree of 22 branches presented as "the standard" claims more than the
               corpus holds: Section A and Appendices A–C are not ingested (§10.6). Saying so is
               the claim-discipline rule applied to structure instead of words. {% endcomment %}
            {% if reader.missing %}
              <p class="reader__tree-note">
                Printed sections not in the corpus, and so not shown here:
                {% for title in reader.missing %}{{ title }}{% if not forloop.last %}, {% endif %}{% endfor %}.
              </p>
            {% endif %}
          </nav>

          <div class="reader__passages">
            {% if reader.selected %}
              <p class="reader__crumb">
                {{ reader.document.title }} &rsaquo; {{ reader.selected.title }}
                {% if reader.selected.page %} &middot; printed p. {{ reader.selected.page }}{% endif %}
              </p>
              {% for passage in reader.passages %}
                <article class="passage" id="{{ passage.anchor }}">
                  <p class="passage__locator">
                    {{ passage.locator }}{% if passage.page %} &middot; printed p. {{ passage.page }}{% endif %}
                  </p>
                  <p class="passage__text">{{ passage.text|linebreaksbr }}</p>
                </article>
              {% empty %}
                <p class="reader__no-hits">
                  This branch is reserved and blank in the printed standard.
                </p>
              {% endfor %}
            {% else %}
              <p class="reader__no-hits">This document has no passages to show.</p>
            {% endif %}
          </div>
        </div>
```

and change each search hit's link from `href="#{{ hit.anchor }}"` to
`href="?section={{ hit.anchor }}#{{ hit.anchor }}"`.

- [ ] **Step 4: Add the canonical link**

```django
{# after the `extra_css` block #}
{% block head_extra %}
  <link rel="canonical" href="{{ canonical }}">
{% endblock %}
```

- [ ] **Step 5: Update the page's own comment block** — it still says the page renders "the text, passage by passage". Say what it is now, and keep the `PUBLIC_URLS` exemption paragraph verbatim: the reason has not changed, and `test_claim_discipline.py` quotes it.

- [ ] **Step 6: Run the reader tests**

```bash
python -m pytest core/tests/test_document_reader.py -q
```
Expected: PASS. If `test_the_reader_is_reachable_at_the_published_code` now fails, it is because the
fixture's first branch is Appendix 2, not the text it asserts — fix the *fixture's* ordering
assumption, not the assertion.

- [ ] **Step 7: Commit**

```bash
git add core/templates/public/document_reader.html core/tests/test_document_reader.py
git commit -m "feat(c6): the tree, the pane, and what the corpus does not hold"
```

---

### Task 9: The stylesheet — sticky tree, phone disclosure, 44 px rows

**Files:**
- Modify: `core/static/css/reader.css`
- Test: `core/tests/test_public.py` (the token/touch-target guards already there)

- [ ] **Step 1: Read the guards before writing CSS**

```bash
grep -n "44\|hex\|reader" core/tests/test_public.py | head -20
```
They are the reason this task has no new test: **no raw hex outside `root.css`**, and the 44 px
target rule. Obey them; `test_public.py` fails the build otherwise.

- [ ] **Step 2: Rename and extend the contents rules**

Apply, in `core/static/css/reader.css`:

* `.reader__contents*` → `.reader__tree*` (the class names in the template now say `tree`).
* Every branch row is `min-height: 2.75rem` (44 px) and `display: flex` with the page number in a
  `flex: none` column — the phone's whole table of contents is this list, and a mis-tap costs a page
  load (`build_principles.md` §IV).
* The open branch is marked with a left rule, not a fill: `.reader__tree-link[aria-current="page"]`
  → `box-shadow: inset 3px 0 0 var(--brand-ochre)` on `var(--brand-cream)` (DESIGN §3 — a second
  ground inside the warm ground would be a third surface in one column).
* `.reader__tree-link--reserved` is muted, not a link: `color: var(--brand-muted)`, no hover.
* `.reader__tree-note` is `--text-micro`, `--brand-muted`, `margin-top: 0.75rem`.
* `.reader__crumb` is `--text-micro`, `--brand-muted`, `margin-bottom: 1rem`.
* Keep the existing `:target` highlight rule and the `≥900px` sticky rule that already wraps
  `.reader__contents`; it becomes `.reader__tree`.

- [ ] **Step 3: The phone case — a disclosure, not 22 rows**

```css
/* Below 900 px the tree is the text's preface: 22 rows of 44 px is ~968 px of scrolling before a
   single clause. Collapse to the open branch and let the reader ask for the list. Form-first on a
   phone, structure-first on a desk (D68 §7.4). */
@media (max-width: 899px) {
  .reader__tree-list li:not(:has([aria-current="page"])) { display: none; }
  .reader__tree[open] .reader__tree-list li { display: block; }
}
```

Wrap the `<nav class="reader__tree">` in `<details class="reader__tree-details" {% if reader.section %}open{% endif %}>`
in the template with a `<summary class="reader__tree-summary">Contents — {{ reader.selected.title }}</summary>`,
and let `.reader__tree` be the inner `<nav>`. `details` needs no JavaScript, which is the point:
`build_principles.md` §IV allows HTMX but never requires it, and a `<details>` works with scripting
off. If `:has()` is unavailable on the target browser, use `li[hidden]` set by the template instead —
decide with the phone in hand, not from the spec.

- [ ] **Step 4: Look at it**

```bash
python manage.py runserver
```
Open `/documents/saoso-standard-v2.1/read/` at 1280 px and at 390 px. This step is the only place the
layout is judged before UAT; do not skip it and do not treat it as UAT.

- [ ] **Step 5: Run the public guards**

```bash
python -m pytest core/tests/test_public.py -q
```
Expected: PASS. A failure naming a hex value is the palette rule, not the test being over-eager.

- [ ] **Step 6: Commit**

```bash
git add core/static/css/reader.css core/templates/public/document_reader.html
git commit -m "feat(c7): the tree is sticky on a desk and a disclosure on a phone"
```

---

### Task 10: "View this line", in a new tab, announced

⚠️ **Touches `core/services/_chatbot.py`, `_thread.html` and `answer_page.html` — see §0.1.**
If Task 5 already touched `_chatbot.py`, this is a two-line change on top of it.

**Files:**
- Modify: `core/services/_chatbot.py` (`Citation.read_url`), `core/templates/chatbot/_thread.html`,
  `core/templates/chatbot/answer_page.html`
- Test: `core/tests/test_document_reader.py`

- [ ] **Step 1: Write the failing tests**

```python
# core/tests/test_document_reader.py — append
def test_a_citation_link_selects_the_branch_and_scrolls_to_the_passage(seeded_documents):
    """The fragment scrolls, the query parameter selects: a browser never sends the fragment to
    the server, so both are needed in one link (§6.4)."""
    from core.services._chatbot import Citation

    citation = Citation(section_ref="Appendix 2.1", quote="Wood", document_code="saoso-standard-v2.1",
                        reading_anchor="appendix-2-wood-bark-and-sawdust")

    assert citation.read_url == (
        "/documents/saoso-standard-v2.1/read/"
        "?section=appendix-2-wood-bark-and-sawdust#appendix-2-wood-bark-and-sawdust"
    )


def test_the_citation_link_says_view_this_line_and_announces_the_new_tab(client, seeded_documents):
    """D68 §7.2. The words are the promise: "Read it in SAOSO" describes a file, "View this line"
    describes a place. The hidden suffix is the mitigation for a phone, where a new tab is
    otherwise invisible."""
    body = client.get("/ask/").content.decode()   # or an answer page fixture with one citation

    assert "View this line" in body
    assert 'target="_blank"' in body
    assert 'rel="noopener"' in body
    assert "(opens in a new tab)" in body
```

> If `/ask/` has no cited card on a clean instance, build the assertion against a rendered
> `answer_page.html` with a stored `citations` snapshot — that is how `test_ask_answer_page.py`
> already works. Do not assert against a template file on disk.

- [ ] **Step 2: Run them and watch them fail**

```bash
python -m pytest core/tests/test_document_reader.py -q
```
Expected: FAIL — `read_url` has no `?section=`.

- [ ] **Step 3: Change `read_url`**

```python
# core/services/_chatbot.py — Citation.read_url
        # `?section=` **and** the fragment: a browser never sends the fragment to the server, so
        # the branch has to be chosen by a query parameter, and the fragment is what scrolls the
        # reader to the passage itself.
        return (
            reverse("core:document_reader", kwargs={"code": self.document_code})
            + f"?section={self.reading_anchor}#{self.reading_anchor}"
        )
```

- [ ] **Step 4: Change the two templates**

```django
{# _thread.html #}
<a class="cite__read" href="{{ citation.read_url }}" target="_blank" rel="noopener">
  View this line in {{ citation.document }} &rarr;<span class="visually-hidden"> (opens in a new tab)</span>
</a>

{# answer_page.html #}
<a class="answer__read"
   href="{% url 'core:document_reader' code=citation.document_code %}?section={{ citation.reading_anchor }}#{{ citation.reading_anchor }}"
   target="_blank" rel="noopener">
  View this line &rarr;<span class="visually-hidden"> in {{ citation.document }} (opens in a new tab)</span>
</a>
```

`visually-hidden` already exists in the stylesheet; do not add a second utility class.

- [ ] **Step 5: Run the chat and answer-page suites**

```bash
python -m pytest core/tests/test_chatbot_surface.py core/tests/test_ask_answer_page.py core/tests/test_claim_discipline.py -q
```
Expected: PASS, including the claim sweep — "View this line" contains no forbidden term, and the
reader's exemption reason is unchanged.

- [ ] **Step 6: Commit**

```bash
git add core/services/_chatbot.py core/templates/chatbot/_thread.html core/templates/chatbot/answer_page.html core/tests/test_document_reader.py
git commit -m "feat(c8): a citation opens the line it quotes, in a new tab"
```

---

### Task 11: Close the loop

- [ ] **Step 1: The whole gate**

```bash
python -m pytest -q
python manage.py makemigrations --check --dry-run
python -m lint-imports          # knowledge must still not import core
```
Expected: PASS; `No changes detected`; the `knowledge` → `core` contract still kept.

- [ ] **Step 2: Re-measure the numbers the PRD claims** — with the branch rendering in place, the
before/after weight is measurable rather than estimated:

```bash
python scripts/probe_concordance.py            # branches, titles, missing sections, anchors
```
Record the new page weight (raw and gzipped) for SAOSO's first branch in the PRD §3, and correct the
figure there if it differs from the median-branch estimate.

- [ ] **Step 3: Update the documents that are now wrong**

- `CONCORDANCE_PRD.md` status → *Ready* → then move `CONCORDANCE_PRD.md` and this plan to
  `product/backlog/ready/`, and set both `Status:` lines to `Ready`. Directory is the source of truth.
- `knowledge/reading.py`'s module docstring still says the duplicate-`section_ref` ratchet "makes a
  section reference a usable anchor" — that was the assumption this slice disproved. Rewrite it to
  say what is now true (§10.7).
- `tests/uat/ask_surface_uat.md` Scenario 3 now belongs here; leave the scenario in place (it still
  holds) and add one line pointing at `tests/uat/concordance_uat.md` for the widened judgement.
- `HANDOVER.md` — one paragraph: the reader is a concordance, the citation is "View this line", and
  the anchor defect is closed. Keep it to three lines; the detail is in the PRD.

- [ ] **Step 4: Regenerate the backlog index and commit**

```bash
python product/backlog.py --apply
git add product/backlog tests/uat knowledge core HANDOVER.md
git commit -m "docs(c9): the concordance is built — status, handover, backlog"
```

- [ ] **Step 5: Hand the UAT over**

`tests/uat/concordance_uat.md`, seven scenarios, each with a `Judgement:` clause. Preflight it with
`python manage.py publish_documents` — see §0.2; on a machine where the corpus was never ingested
the reader shows no text at all, and every judgement would be about a broken page. **Tests passing is
not completion for a surface a human must judge.** Do not mark this feature done before the
sign-off table has names in it — and do not ask the reviewer to confirm anything in the *Automated
coverage* table; that table exists so they do not have to.

---

## 12. Implementation notes — what differed from this plan

Built 2026-10-27, one commit per task. The gate is green at **954 passed, 1 skipped** (the
real-corpus anchor guard skips on the scratch database by design) and Playwright at **53**.
These are the places the code does not match the plan above; each was found by running it.

1. **Task 2 — the TOC is read from the raw pages.** The plan's snippet captured `pages` after
   `apply_layout`, contradicting its own comment. `ingest_standard` now keeps `raw_pages` and
   passes those to `toc_from_pages`, so the stored TOC is a record of what the document prints.
   `--from-corpus` extracts the PDF once more for this purpose only (the artefact carries no TOC).
2. **Task 4 — the plan's claim that `test_reading.py` "still passes" was wrong.** Its
   `test_a_repeated_reference_keeps_the_plain_anchor_first` deliberately duplicates a reference,
   so it asserted `appendix-2-2`; it now asserts `appendix-2-straw-is-listed`. Measured on the
   shipped 366 passages: **0 ambiguous anchors**, and the first row of every group keeps its bare
   anchor. **One last-resort numeric suffix remains** — `appendix-2-2`, because two Appendix 2
   rows both begin "Trace elements, e.g." — which is the fallback the plan allows.
3. **Task 5 — no `_citation_anchors`/`passage_anchors` was added.** The chat had already grown
   `_reader_anchors()` (F7), which resolves through `reader_anchor_map()` → `unique_anchors()`, so
   it inherited the content-derived anchors from Task 4 with no code change. The work that
   remained was the search list (`search_in_document(anchors=)`), the two docstrings that still
   described positional suffixes, and the citation tests that asserted `s1-2`.
4. **Task 6 — two page-level tests became service-level.** Only the selected branch renders now,
   so `test_every_chunk_has_its_anchor_on_the_page` asserts the tree's passages, and the F7 test
   asserts the branch's anchors instead of both ids on one page. Task 7/8 re-add the page-level
   assertions through `?section=`.
5. **Task 9 — a closed `<details>` hides its content through `::details-content`, not through the
   child's `display`.** `display: block` on the nav is not enough on current Chromium; the desktop
   rule also needs `.reader__tree-details:not([open])::details-content { content-visibility:
   visible; display: block; }`. Found by looking at the page (the desktop tree was invisible while
   every assertion stayed green), which is why Step 4 exists.
6. **Task 10 — the answer page's citations are dicts, not `Citation` objects.** `answer_page.html`
   builds its href from `citation.document_code`/`reading_anchor` in the template; only
   `_thread.html` can use the `read_url` property.
7. **Dev data.** `ingest_standard` is idempotent on the PDF's sha256, so a plain re-run does not
   write the new `toc` field. The dev database's four documents had their `toc` written directly
   (the ingest path is what is tested); a `--force` re-ingest was avoided because it would have
   re-embedded 366 chunks and dropped `ChatMessage.retrieved_chunks` evidence links.
