# Corpus Column-Aware Extraction — Implementation Plan

**Status:** In Progress — C0–C9 landed 2026-10-20; **UAT Scenario 9 signed 2026-10-21** by the product owner.
**Owner:** Build — knowledge ingestion (sub-plan B), grounded chat (sub-plan D)
**Last Updated:** 2026-10-19
**MVP:** MVP 0 — defect fix. Blocks the UAT scenario 1 judgement (D23); must land before MVP 1a.
**Goal:** Every passage a reader can find on the printed page of the four governed documents
is quotable verbatim (whitespace-normalised) from a stored `DocumentChunk`, so
`audit_citations` can accept a faithful citation instead of refusing it as a corpus gap.

**Architecture:** A new pure module `knowledge/columns.py` detects vertical whitespace
bands per page and re-emits the page in reading order (column 1 top-to-bottom, then column
2, …), or returns the page unchanged when no band qualifies. It is applied once, at ingest,
between `extract_pages()` and the section parser, and by `scripts/extract_fixtures.py` so
fixtures stay evidence. No model, no migration, no `layout` flag: layout is a measured
property of a page. The pages the transform touches are pinned by a golden table in tests,
and pages that must not be transformed are an asserted exclusion list with reasons.

**Tech Stack:** Python 3.13, `pdftotext -layout` (poppler) via `knowledge/extraction.py`,
Django 5.2 (ingest only), pytest + pytest-django. No new dependencies.

**PRD:** `product/backlog/ready/CORPUS_COLUMN_EXTRACTION_PRD.md` (this plan supersedes its
§5 execution steps where they disagree — see §0.2 errata).

**UAT:** `tests/uat/mvp0_standards_and_public_site_uat.md` — PRD §10. No new UAT file: this
is a defect fix on an existing surface, and its human checks belong beside the standards-
corpus checks already there. Drafted (in the PRD) before implementation, as required.

**Plan file convention:** the repo keeps plans in the same backlog bucket as their PRD
(`MVP1A_PLAN.md`, `MVP0_PLAN_V2.md`), not appended to the PRD. This file follows that.

---

## 0. How to execute this plan

1. Work task by task, C0 → C9. Every task ends in a green suite and a commit.
2. **Tests first, and prove the test can fail.** Break the assertion, watch it go red,
   restore it. `product/docs/context/testing_hazards.md` is mandatory reading before C1.
3. Do not start C7 (ingest wiring) before C4's reading-order review is filled in. Wiring
   before review means re-ingesting a corpus that silently reorders tables.
4. C8 is the only task that touches a database. Everything before it is pure functions and
   parser output.
5. If a golden expectation and the detector disagree, **the detector does not get an
   allow-list** — the page is excluded with a reason (CO-1) or the detector is fixed.

### 0.1 Baseline re-measured for this plan (2026-10-19, this session)

The PRD's inventory was re-measured independently with the §3.2 algorithm, from
`extract_pages()` on the shipped PDFs. Commands are in §5. Results:

| Claim | Verdict | Evidence |
|---|---|---|
| 32 of 139 pages are column-laid-out | **Confirmed**, with 1 page reclassified | BPP 8 (pdf 3–10), landscape 8 (pdf 2–9), OPP 3 (pdf 4, 11, 12), SAOSO 13 (pdf 77,78,80,82,83,84,86,87,88,89,90,91,92) |
| SAOSO printed page = PDF page − 1 | **Confirmed** | printed 76–91 ⇔ pdf 77–92; the PRD's `range(76,92) - {78,80,84}` reproduces exactly |
| The two success-gate sentences become contiguous | **Confirmed** | BPP "Animal manure must be preferably composted prior to application…" contiguous across pdf 4→5 and inside one chunk (`anchor=general-principles`); Appendix 2 "Shall not constitute the main source of nitrogen…" contiguous on SAOSO pdf 77, in a chunk with `section_ref="Appendix 2"`, `page=76` |
| Non-space character multiset preserved | **Confirmed** on all 139 pages | 0 violations |
| Single-column controls byte-identical | **Confirmed** | SAOSO pdf 40, 60; OPP pdf 1, 6, 8; BPP pdf 1, 2 — all `out == page` |
| No band ⇒ no-op | **Confirmed** | returned as the same object, not merely an equal string |
| Section sets unchanged by the transform | **Confirmed for SAOSO/OPP/BPP, FALSE for landscape** | 271/28/4 sections identical; landscape loses every `page` (all `None`) — CO-3 |
| Chunk counts unchanged | **False, and that is fine** | SAOSO 298 → 292 chunks; section sets identical, packing differs. `_corpus_fingerprint()` handles the cache |

### 0.2 PRD errata — correct these; do not build around them

Seven statements in the PRD are contradicted by measurement. Each is cheap now and
expensive after C7.

| # | PRD says | Measured | Resolution in this plan |
|---|---|---|---|
| E1 | "**312** pages must remain byte-identical" (§3.1, §6) | 139 − 32 = **107** | Use 107 everywhere |
| E2 | Golden table is `range(76, 92) - {78, 80, 84}` (§3.4) | Those are **printed** page numbers; the code sees **PDF** page numbers (`extract_pages()[n-1]`) | Golden table in **PDF** page numbers: `range(77, 93) - {79, 81, 85}`. Tasks assert PDF numbers only |
| E3 | 13 SAOSO column pages (§3.1) | The detector also flags **SAOSO pdf 2** (the table of contents) ⇒ 14 detected, 13 in scope | pdf 2 is a **measured exclusion**, not a silent omission — CO-1 |
| E4 | "A page that is column-laid-out but fails a golden check … stays byte-identical" (§3.4) | `de_column()` has no way to decline once a band is found | Add the exclusion table + `apply_layout()` (CO-1). Without it §3.4 is unimplementable |
| E5 | Requirement 2: "a page whose bands vanish is a no-op" | BPP p4 and OPP p11 become band-free (**stable**); **landscape pdf 4 is not** — 3 new bands appear and a second pass reorders it further | Assert what is true: not idempotent, and a second pass still preserves the multiset. Ingest runs it once |
| E6 | Step 4's fixture list: "at least `bpp_intro`, `landscape_seals`, `saoso_appendices`, `opp_4_1`" | Affected: `bpp_intro` (3–4), `landscape_seals` (6–8), `opp_4_1` (4), and **`saoso_toc` (2–3)**. `saoso_appendices` (71–73) is **not** affected | Regenerate 4 fixtures; `saoso_toc` is the one the PRD missed. If CO-1 excludes SAOSO pdf 2, `saoso_toc` reverts to unchanged → 3 fixtures |
| E7 | Success criterion 3 / step 7: "the model's real 2026-10-19 reply … passes `audit_citations`" | That reply's quote is a **paraphrase** ("must preferably be composted and sourced from farms under organic management or extensive farming practices…"), not the corpus sentence. `audit_citations` is an exact whitespace-normalised substring match, so it is refused **even against a perfect corpus** | Replace with two checks: (a) the *verbatim corpus sentence* is accepted against the re-ingested chunk; (b) a live re-run whose quote **is** verbatim is accepted (UAT). Record both causes in the release note |

Two further measured details that will otherwise produce tests that fail for the wrong
reason (both cost real time in this session):

- The BPP sentence is **contiguous modulo line breaks** (`"Animal manure\nmust be preferably
  composted\nprior to applicat…"`). Assert with `" ".join(text.split())`, exactly as
  `_normalise_text` does. A raw `in` substring fails.
- The non-space multiset test must strip **newlines as well as spaces**; counting newlines
  reports every transformed page as a loss and looks like catastrophic data loss.

### 0.3 Decisions frozen for this plan

**CO-1 — An exclusion table, not a per-document flag.** Detection stays generic (D46).
`knowledge/columns.py` carries a module-level data table keyed by `doc_key` whose entries
are `(pdf_page → reason)`, and `apply_layout()` consults it. `de_column()` stays a pure
function of a page string (requirement 1). This is the mechanism PRD §3.4 assumes exists and
does not specify.

Required by measurement, not taste: transforming SAOSO pdf 2 (the TOC) takes `parse_toc`
from **29 entries to 8** and corrupts `appendix_spans` — Appendix 1's last page becomes 80
instead of 75, and Appendix 2/3 entries disappear. Appendix 2 is exactly the page range the
success gate depends on. The TOC's page-number column is what makes the transform wrong
there, and no parameter fixes that.

**CO-2 — Reading order is judged per page, before wiring.** All 33 detected pages get one
review row in Task C4: `accept` or `exclude`, with the observed reading order as evidence.
Measured already:

- **OPP pdf 11 — exclude (recommended).** A 3-column table with one detected band:
  `"Self-claim organic | Applies where there is no organic certification and the organic
  claim is self- label or seal. | declared."` — every character preserved, reading order
  wrong. That is precisely the failure mode PRD §3.4 anticipated.
- **OPP pdf 4** (committee roles): characters preserved, but each role's description is
  detached to the end of the page. PRD §3.5 accepts lost row association; the prose
  (§3.2, §3.3) reads correctly. **Accept**, and record the row-association loss.
- **SAOSO pdf 82–84** (Appendix 4 Tables 1–2, printed 81–83): judge in C4.

**CO-3 — `heading.py::_page_stamp` must change.** After de-columning, the landscape's bare
page number is no longer the last non-blank line (it lands ~line 50 of 90), so
`_page_stamp` returns `None` for every landscape page and all six landscape sections lose
their `page`. Verified fix: search **anywhere** for the last line that is exactly a bare
number. That restores landscape `[4, 4, 6, 7, 7, 9]` and leaves SAOSO, OPP and BPP
**byte-identical in output** (BPP stays `[None, None, None, 10]`; the SAOSO/OPP labelled
`Page | N` path runs first and is untouched). A test pins all four sets.

**CO-4 — The acceptance gate is the verbatim sentence, plus a live turn.** See E7. The test
that feeds a *recorded model reply* is still worth writing — but it asserts the reply is
**refused**, with the paraphrase named, so the audit's strictness is pinned rather than
quietly relaxed.

### 0.4 Files touched

| File | Change |
|---|---|
| `knowledge/columns.py` | **new** — bands, `de_column`, exclusions, `apply_layout` |
| `knowledge/tests/test_columns.py` | **new** — C1–C4 tests |
| `knowledge/sections/heading.py` | `_page_stamp` fix; delete the two false docstring paragraphs |
| `knowledge/tests/test_section_parsers.py` | page-set pin for landscape + BPP |
| `knowledge/ingest.py` | `apply_layout` wiring; `IngestReport.layout_pages` |
| `knowledge/tests/test_ingest.py` | layout assertions |
| `scripts/extract_fixtures.py` | run the transform; record pipeline + raw page hash |
| `knowledge/tests/fixtures/{bpp_intro,landscape_seals,opp_4_1[,saoso_toc]}.txt`, `MANIFEST.json` | regenerated |
| `tests/uat/mvp0_standards_and_public_site_uat.md` | PRD §10 additions |
| `product/docs/context/testing_hazards.md` | §3 below |
| `product/backlog/backlog.md` | regenerated by `product/backlog.py --write` |

Nothing else. No models, no migrations, no views, no URLs, no templates, no design tokens.

---

## 1. The transform — final shape

Prototyped and measured in this session; hand it over as-is unless a test says otherwise.

```python
"""Column-aware reading order for extracted PDF pages (D46).

`pdftotext -layout` keeps both columns of a two-column page on one visual line, so a
page read line by line alternates columns and no sentence that spans the gutter is a
quotable substring. This module re-emits such a page in reading order — column 1
top to bottom, then column 2 — and leaves every other page byte-identical.

Pure: a function of a page string. No Django, no PDF library, no clock, no locale.
"""

from __future__ import annotations

#: A gutter index qualifies when this fraction of the lines that *cross* it are blank
#: at it. Measured on the four governed documents: 0.70-1.0 on column pages, 0.16-0.17
#: on prose. The gap is wide enough that no per-document allow-list is needed.
MIN_COVERAGE = 0.70
#: A band inside a handful of lines is noise, not a gutter.
MIN_CROSSING_LINES = 6
#: Both sides must carry real text, or the band is the page margin.
MIN_CHAR_SHARE = 0.12


def column_bands(page: str) -> list[tuple[int, int]]:
    """Maximal vertical whitespace bands: `(start, end)` column indices, left to right.

    In:  `page` — one page as `pdftotext -layout` emits it.
    Out: the bands, or `[]` when the page is not column-laid-out.
    Fails: never. A page with no lines, or one line, has no bands.
    """


def de_column(page: str, *, bands: list[tuple[int, int]] | None = None) -> str:
    """The page in reading order.

    In:  `page`; `bands` to override detection (tests, and re-running a chosen band).
    Out: the reordered page, or **the same string object** when there is no band.
    Fails: never.
    """


#: Pages that are column-laid-out but must NOT be transformed, with the measured reason.
#: Data, not a `layout` field: a retarget to another standard needs no migration, and a
#: new edition that starts mis-detecting fails a test rather than silently degrading.
PAGE_LAYOUT_EXCLUSIONS: dict[str, dict[int, str]] = {
    "saoso": {
        2: (
            "table of contents: its right-hand column IS the printed page numbers, so "
            "de-columning detaches every entry from its page and takes `parse_toc` from "
            "29 entries to 8 (appendix_spans then reports Appendix 1 ending on p.80 "
            "instead of p.75). Measured 2026-10-19."
        ),
    },
}


def apply_layout(
    pages: list[str], *, doc_key: str | None = None
) -> tuple[list[str], tuple[int, ...]]:
    """Transform every page except the recorded exclusions.

    In:  `pages` — normalised pages, `pages[N - 1]` is PDF page N; `doc_key` — a
         `CORPUS_DOCUMENTS` name, so exclusions can be applied.
    Out: `(transformed_pages, changed)` where `changed` is the 1-based **PDF** page
         numbers whose text is different.
    Fails: never.
    """
```

`column_bands` — the loop, exactly:

```python
    lines = page.split("\n")
    width = max((len(line) for line in lines), default=0)
    if not width:
        return []
    non_space_total = sum(len(line.replace(" ", "")) for line in lines)

    def coverage(i: int) -> float:
        crossing = blank = 0
        for line in lines:
            if not line[:i].rstrip() or not line[i:].lstrip():
                continue          # the line does not cross this index
            crossing += 1
            if i < len(line) and line[i] == " ":
                blank += 1
        if crossing < MIN_CROSSING_LINES:
            return 0.0
        return blank / crossing

    def side_share(i: int) -> float:
        if not non_space_total:
            return 0.0
        left = sum(len(line[:i].replace(" ", "")) for line in lines)
        right = sum(len(line[i:].replace(" ", "")) for line in lines)
        return min(left, right) / non_space_total

    bands: list[tuple[int, int]] = []
    i = 0
    while i < width:
        if coverage(i) >= MIN_COVERAGE and side_share(i) >= MIN_CHAR_SHARE:
            start = i
            while i < width and coverage(i) >= MIN_COVERAGE and side_share(i) >= MIN_CHAR_SHARE:
                i += 1
            bands.append((start, i))
        else:
            i += 1
    return bands
```

`de_column` — the loop, exactly (note `not all(blank)` ⇒ keep the line whole):

```python
    if bands is None:
        bands = column_bands(page)
    if not bands:
        return page                      # the fallback is a no-op, never a guess

    columns: dict[int, list[str]] = {}
    for line in page.split("\n"):
        if any(line[start:end].strip() for start, end in bands):
            fragments = [(0, line)]      # a spanning line is never cut
        else:
            fragments = []
            cursor = 0
            for start, end in bands:
                fragments.append((cursor, line[cursor:start]))
                cursor = end
            fragments.append((cursor, line[cursor:]))
        for offset, text in fragments:
            # Assign by the fragment's OWN start position. Assigning by index in the
            # cut list is the bug that reordered the OPP labelling table: a line that
            # ends before a band has fewer fragments, and the rest shift left.
            columns.setdefault(sum(1 for start, _ in bands if offset >= start), []).append(text)

    blocks = []
    for index in sorted(columns):
        rows = [text.rstrip() for text in columns[index]]
        while rows and not rows[0].strip():
            rows.pop(0)
        while rows and not rows[-1].strip():
            rows.pop()
        blocks.extend(rows)
    return "\n".join(blocks)
```

### Task C1: The transform — synthetic contract, red first

**Files:** Create `knowledge/columns.py`, `knowledge/tests/test_columns.py`

- [ ] **Step 1: Write the failing tests** (no Poppler, no DB — this file is a pure unit test)

```python
import pytest
from knowledge.columns import column_bands, de_column

LEFT = ["The organic farm", "is an element of", "an environment or", "ecosystem. The",
        "balanced management", "of this system is", "important and it", "must be documented."]
RIGHT = ["A clear long term", "soil fertility plan", "must be in place", "on every farm and",
         "should include the", "mechanisms and", "practices that", "increase organic matter."]
PAGE = "\n".join(f"{left:<28}{right}" for left, right in zip(LEFT, RIGHT))
BAND = [(22, 28)]

def test_columns_are_emitted_left_to_right():
    assert de_column(PAGE, bands=BAND) == "\n".join(LEFT + RIGHT)

def test_a_line_that_crosses_the_band_is_kept_whole():
    spanning = PAGE + "\n" + "a footnote spanning the whole width of the page".center(50)
    out = de_column(spanning, bands=BAND)
    assert "a footnote spanning the whole width of the page" in out.split("\n")

def test_blank_runs_inside_a_column_are_preserved():
    page = "\n".join(f"{left:<28}{right}" for left, right in zip(LEFT[:4], RIGHT[:4]))
    page = page.split("\n")
    page.insert(2, "")
    out = de_column("\n".join(page), bands=BAND).split("\n")
    assert out[2] == "" and out[3] == LEFT[2]

def test_no_band_returns_the_same_object():
    prose = "A single column of prose.\nWith no gutter anywhere.\n"
    assert de_column(prose) is prose
```

- [ ] **Step 2: Run — expect `ModuleNotFoundError: No module named 'knowledge.columns'`**

Run: `pytest knowledge/tests/test_columns.py -v`

- [ ] **Step 3: Implement** `knowledge/columns.py` per §1. Keep the dataclass-free, stdlib-only
      form; add the Data Flow Contract docstrings (`In/Out/Fails`).

- [ ] **Step 4: Run — expect 4 passed.**

- [ ] **Step 5: Commit** — `feat(corpus): the column-aware page transform, with its contract tests`

### Task C2: The reported defect, and the two success-gate sentences

**Files:** Modify `knowledge/tests/test_columns.py`

These read the real PDFs (as `test_ingest.py` already does — Poppler is a test dependency of
this repo, not a new one; 1.2 s for all four documents).

- [ ] **Step 1: Write the failing tests.** Add a module-scoped fixture:

```python
from pathlib import Path
from knowledge.extraction import extract_pages
from knowledge.sections import registry
from knowledge.chunking import chunk_sections

PDFS = {
    "saoso": "saoso-version-2.1-2026.pdf",
    "bpp": "Basic Production Principles_ENG_PRINT.pdf",
    "landscape": "PGS Certification landscape_Final.pdf",
    "opp": "Outeniqua pgs principles, policies and procedures 2026.pdf",
}
PDF_DIR = Path(__file__).resolve().parents[2] / "pgs_docs"

@pytest.fixture(scope="module")
def corpus():
    return {key: extract_pages(PDF_DIR / name) for key, name in PDFS.items()}

def chunks_of(pages, scheme):
    return chunk_sections(registry.get(scheme).parse("\f".join(pages)))

def flat(text):                     # exactly what audit_citations does
    return " ".join(text.split())
```

```python
BPP_SENTENCE = (
    "Animal manure must be preferably composted prior to application, and must be "
    "sourced from farms under organic management, or from extensive farming practice."
)
APPENDIX_2_CONDITION = (
    "Shall not constitute the main source of nitrogen in the absence of complimentary "
    "and additional nitrogen generating practices on farm and shall not be from "
    "conventional intensive livestock production systems without prior permission "
    "from the control body"
)

def test_the_bpp_manure_sentence_is_quotable_from_one_chunk(corpus):
    # Spans PDF pages 4->5, so it is only meaningful on post-ingest chunk text.
    chunks = chunks_of([de_column(p) for p in corpus["bpp"]], "heading")
    carriers = [c for c in chunks if flat(BPP_SENTENCE) in flat(c.text)]
    assert len(carriers) == 1
    assert carriers[0].anchor == "general-principles"

def test_the_appendix_2_condition_is_quotable(corpus):
    chunks = chunks_of([de_column(p) for p in corpus["saoso"]], "saoso")
    carriers = [c for c in chunks if flat(APPENDIX_2_CONDITION) in flat(c.text)]
    assert len(carriers) == 1
    assert carriers[0].section_ref == "Appendix 2"
    assert carriers[0].page == 76        # printed page, D42
```

- [ ] **Step 2: Run — expect both to fail with `len(carriers) == 0`** (this is the reported
      defect: on today's corpus neither sentence is contiguous). If they *pass*, the fixture
      is wrong — a chunk carrying a sentence that the live question could not cite is the
      exact "passes for the wrong reason" failure.

- [ ] **Step 3: Run again with the transform in place — expect 2 passed.**

- [ ] **Step 4: Prove the guard can fail.** Temporarily change `de_column`'s first line to
      `return page`; watch both go red; restore. Record in the commit message that both
      directions were observed.

- [ ] **Step 5: Commit** — `test(corpus): the manure and Appendix 2 sentences are quotable post-transform`

### Task C3: The golden page set, the loss-free proof, and the single-column controls

**Files:** Modify `knowledge/tests/test_columns.py`

The multiset test alone is worthless: it passes happily if `de_column` never transforms
anything. It is only a guard when paired with the golden set, so both live here.

- [ ] **Step 1: Write the failing tests**

```python
from collections import Counter

#: The pages the transform MUST change, as **PDF** page numbers — `extract_pages()[n-1]`.
#: The PRD's §3.4 table is in *printed* numbers; SAOSO prints pdf - 1 (D42).
EXPECTED_TRANSFORMED_PAGES = {
    "bpp": {3, 4, 5, 6, 7, 8, 9, 10},
    "landscape": {2, 3, 4, 5, 6, 7, 8, 9},
    "opp": {4, 11, 12},                          # narrowed by Task C4
    "saoso": set(range(77, 93)) - {79, 81, 85},  # printed 76-91 minus 78, 80, 84
}

def non_space(text: str) -> Counter:
    # Newlines are NOT part of the invariant: reordering necessarily changes them, and
    # counting them reports all 32 transformed pages as data loss.
    return Counter(text.replace(" ", "").replace("\n", ""))

@pytest.mark.parametrize("doc_key", ["saoso", "bpp", "landscape", "opp"])
def test_no_non_space_character_is_lost_on_any_page(corpus, doc_key):
    losses = [
        number
        for number, page in enumerate(corpus[doc_key], 1)
        if non_space(page) != non_space(de_column(page))
    ]
    assert losses == []

@pytest.mark.parametrize("doc_key", ["saoso", "bpp", "landscape", "opp"])
def test_exactly_the_expected_pages_are_transformed(corpus, doc_key):
    changed = {
        number
        for number, page in enumerate(corpus[doc_key], 1)
        if de_column(page) != page
    }
    assert changed == EXPECTED_TRANSFORMED_PAGES[doc_key]

@pytest.mark.parametrize(
    "doc_key,pages",
    [("saoso", [40, 60]), ("opp", [1, 6, 8]), ("bpp", [1, 2])],
)
def test_single_column_control_pages_are_byte_identical(corpus, doc_key, pages):
    for number in pages:
        assert de_column(corpus[doc_key][number - 1]) == corpus[doc_key][number - 1]
```

- [ ] **Step 2: Run.** The multiset test and the controls pass; the golden test fails on
      `opp` (11 is currently transformed) and on `saoso` (PDF 2 is transformed but not in
      the golden set). **That failure is the point of C4** — do not "fix" it by adding 2 to
      the golden set.

- [ ] **Step 3: Prove the loss guard can fail.** Temporarily drop one fragment in
      `de_column` (`fragments = fragments[1:]`); watch the multiset test go red; restore.

- [ ] **Step 4: Commit** — `test(corpus): 32 golden pages, 107 byte-identical, lossless on all 139`

### Task C4: Reading-order review — the accepted/excluded table (CO-1, CO-2)

**Files:** Modify `knowledge/columns.py` (the exclusion table), `knowledge/tests/test_columns.py`

This is the only judgement task. It cannot be automated, and it is why PRD §3.4 exists.

- [ ] **Step 1: Dump every detected page, before and after, into `_scratch/review/`.** Read
      each `after` dump. Verdict per page: `accept` (reading order correct) or `exclude`
      (with the observed defect quoted verbatim as the reason — a reason is evidence, not an
      adjective).

- [ ] **Step 2: Fill `PAGE_LAYOUT_EXCLUSIONS`.** Measured verdicts to start from:

      | Page | Verdict | Evidence |
      |---|---|---|
      | SAOSO pdf 2 | **exclude** (recorded) | `parse_toc` 29 → 8 entries; `appendix_spans` puts Appendix 1's end on p.80 instead of p.75 |
      | OPP pdf 11 | **exclude** | 3-column table, one band: `Self-claim organic \| Applies where there is no organic certification and the organic claim is self- label or seal. \| declared.` |
      | OPP pdf 4 | accept | prose (§3.2, §3.3) reads correctly; the roles table's descriptions are detached to the page end — lost *row association*, accepted by PRD §3.5 |
      | SAOSO pdf 82–84 (Appendix 4 Tables 1–2) | **judge** | this is the table the PRD flagged as at-risk; decide from the dump |
      | BPP 3–10, landscape 2–9, SAOSO 77, 78, 80, 83, 86–92, OPP 12 | **judge** | accept unless the dump shows a reordered passage |

- [ ] **Step 3: Write the two guard tests**

```python
def test_excluded_pages_are_byte_identical(corpus):
    for doc_key, exclusions in PAGE_LAYOUT_EXCLUSIONS.items():
        for number in exclusions:
            page = corpus[doc_key][number - 1]
            assert de_column(page) == page, f"{doc_key} pdf {number} must not be transformed"

def test_every_detected_page_is_either_transformed_or_excluded(corpus):
    # A page that is column-laid-out and falls between the two lists is the silent
    # failure this whole PRD exists to prevent.
    for doc_key, pages in corpus.items():
        for number, page in enumerate(pages, 1):
            if not column_bands(page):
                continue
            excluded = number in PAGE_LAYOUT_EXCLUSIONS.get(doc_key, {})
            transformed = number in EXPECTED_TRANSFORMED_PAGES[doc_key]
            assert excluded or transformed, f"{doc_key} pdf {number} is unaccounted for"
```

- [ ] **Step 4: Re-run C3's golden test — expect green.** If any Appendix 4 page is
      excluded, remove it from `EXPECTED_TRANSFORMED_PAGES` and add the reason to the same
      table in one commit.

- [ ] **Step 5: Commit** — `feat(corpus): a reviewable exclusion table; OPP §6.5 and the SAOSO TOC are not transformed`

### Task C5: Parser compatibility — and the page stamp that breaks (CO-3)

**Files:** Modify `knowledge/sections/heading.py`, `knowledge/tests/test_section_parsers.py`

Requirement 6 of the PRD assumes the parsers come out unchanged. Three do. The landscape
does not: its bare page number is the last non-blank line of the **raw** page but lands
around line 50 of 90 after reordering, so `_page_stamp` returns `None` for all six sections
and every landscape citation silently loses its page (D42). Measured, not feared.

- [ ] **Step 1: Write the failing tests**

```python
# knowledge/tests/test_section_parsers.py
from knowledge.columns import de_column

#: Today's values, measured. The transform must not move a single one.
EXPECTED_PAGES = {
    "saoso": [22, 30, 30, 30, 31, 31, 31, 31],   # printed numbers, D42
    "landscape": [4, 4, 6, 7, 7, 9],
    "bpp": [None, None, None, 10],
}

@pytest.mark.parametrize("doc_key", ["saoso", "landscape", "bpp"])
def test_page_attribution_survives_the_transform(corpus, doc_key, scheme_of, parser):
    raw = parser(scheme_of[doc_key]).parse("\f".join(corpus[doc_key]))
    fixed = parser(scheme_of[doc_key]).parse(
        "\f".join(de_column(page) for page in corpus[doc_key])
    )
    assert [section.page for section in raw] == EXPECTED_PAGES[doc_key]
    assert [(s.section_ref, s.anchor, s.page) for s in fixed] == [
        (s.section_ref, s.anchor, s.page) for s in raw
    ]

def test_the_toc_map_is_unchanged(corpus):
    # Appendix 2's boundary comes from this map; SAOSO pdf 2 is excluded for this reason.
    pages = [de_column(page) for page in corpus["saoso"]]
    assert parse_toc("\f".join(pages)) == parse_toc("\f".join(corpus["saoso"]))
```

- [ ] **Step 2: Run — expect the landscape case to fail on `[None, None, None, None, None, None]`.**

- [ ] **Step 3: Fix `_page_stamp`** — the labelled stamp first (unchanged), then the *last*
      bare-number line anywhere on the page:

```python
    @staticmethod
    def _page_stamp(page_text: str) -> int | None:
        """`Page | 6` (SAOSO) or a bare `6` (the certification landscape).

        The bare stamp is searched for anywhere, not just at the end: the stamp is
        page furniture, and re-ordering a two-column page moves it into the middle.
        Searching the tail found it before the column transform and lost it after.
        """
        labelled = page_number(page_text)
        if labelled is not None:
            return labelled
        stamps = [
            int(line.strip())
            for line in page_text.splitlines()
            if BARE_PAGE.match(line.strip())
        ]
        return stamps[-1] if stamps else None
```

- [ ] **Step 4: Run — expect green, including `bpp == [None, None, None, 10]`** (the change
      must not invent page numbers the BPP never printed) and the SAOSO/OPP stamp path
      untouched.

- [ ] **Step 5: Delete the two false docstring paragraphs** in `heading.py`: "Body
      attribution in a two-column document is approximate…" and "…a column-aware extractor
      is deferred". Replace with one accurate paragraph: body attribution is now exact
      because the page is de-columned at ingest; `COLUMN_GAP` segment splitting stays,
      because a line that still holds two headings side by side is not cut by the transform.
      Also correct the claim that "the BPP stamps none" — it stamps on some pages (measured:
      `None, None, None, 10`).

- [ ] **Step 6: Commit** — `fix(parsers): keep the landscape's page attribution after de-columning`

### Task C6: Fixtures through the identical pipeline

**Files:** Modify `scripts/extract_fixtures.py`, `knowledge/tests/fixtures/MANIFEST.json`,
`knowledge/tests/fixtures/{bpp_intro,landscape_seals,opp_4_1}.txt`

Affected fixtures, measured: `bpp_intro` (pdf 3–4), `landscape_seals` (6–8), `opp_4_1` (4).
**`saoso_appendices` (71–73) is NOT affected** — the PRD's step 4 lists it in error; its
pages carry no band. `saoso_toc` (2–3) would be affected, but SAOSO pdf 2 is excluded (C4),
so it must come out **byte-identical** — which is a useful negative control.

- [ ] **Step 1: Apply the layout in the script**, immediately after the page range is taken
      and before the anchor check, with the same `doc_key` ingest uses:

```python
from knowledge.columns import apply_layout

pages, _ = apply_layout(pages, doc_key=doc_key_of(extract.source))
```

- [ ] **Step 2: Extend `MANIFEST.json`** per fixture with:
      `"pipeline": "pdftotext -layout + de_column v1"` and
      `"raw_page_sha256": {"3": "<sha of the pre-transform page>"}` — so the fixture stays
      checkable evidence rather than a hand edit, and a later change to the transform fails
      the manifest comparison instead of silently drifting.

- [ ] **Step 3: Regenerate** — `python scripts/extract_fixtures.py`. Anchors must still
      verify (`INTRODUCTION` on bpp p3, etc.). `git diff --stat` must show exactly three
      changed fixtures plus `MANIFEST.json`; a fourth changed fixture means a page was
      detected that C3/C4 does not account for — stop and reconcile.

- [ ] **Step 4: Run the fixture-dependent suites** — `pytest knowledge/tests/test_section_parsers.py
      knowledge/tests/test_toc_map.py knowledge/tests/test_chunking.py`. Any assertion that
      pinned the old interleaved bytes gets **re-derived from the new fixture**, not
      loosened. Where a test's expectation changes, say in the commit message which page and
      why.

- [ ] **Step 5: Commit** — `chore(corpus): regenerate the three column-page fixtures through the new pipeline`

### Task C7: Wire the transform into ingest, and report what it touched

**Files:** Modify `knowledge/ingest.py`, `knowledge/management/commands/ingest_standard.py`,
`knowledge/tests/test_ingest.py`

- [ ] **Step 1: Write the failing tests**

```python
from knowledge.tests.test_columns import EXPECTED_TRANSFORMED_PAGES  # single source of truth

@pytest.mark.parametrize("doc_key", ["bpp", "landscape", "opp", "saoso"])
def test_the_ingest_reports_the_pages_it_transformed(doc_key, standard_set):
    report = ingest_standard(
        pdf_path=PDF_DIR / SOURCE_FILES[doc_key],
        standard_set=standard_set,
        doc_key=doc_key,
        embed=False,
    )
    assert set(report.layout_pages) == EXPECTED_TRANSFORMED_PAGES[doc_key]

def test_bpp_reports_eight_layout_pages(standard_set):
    # A literal on purpose: if the detector regresses to zero, the golden set and the
    # report would agree with each other and both be wrong.
    report = ingest_standard(pdf_path=PDF_DIR / SOURCE_FILES["bpp"], standard_set=standard_set,
                             doc_key="bpp", embed=False)
    assert len(report.layout_pages) == 8
```

- [ ] **Step 2: Run — expect `AttributeError: 'IngestReport' object has no attribute 'layout_pages'`.**

- [ ] **Step 3: Implement.** `IngestReport` gains
      `layout_pages: tuple[int, ...] = ()` (a default, so the `created=False` path and the
      existing constructor calls keep working). In `ingest_standard`:

```python
    parser = registry.get(descriptor["section_scheme"])
    pages, layout_pages = apply_layout(extract_pages(path), doc_key=doc_key)
```

      Exclusions are keyed by `doc_key`. A new standard ingested with explicit metadata has
      no exclusion table — generic detection, no special case (D16, and the retarget rule in
      `build_principles.md` §I). Say so in the docstring rather than leaving it implicit.

- [ ] **Step 4: Print it** in the management command, next to the chunk count:
      `f"{len(report.layout_pages)} layout pages"` — the operator's log is how a human sees
      that the transform ran, rather than inferring it from better answers.

- [ ] **Step 5: Run the whole ingest suite** — `pytest knowledge/tests/test_ingest.py`.
      Existing assertions (`test_pages_are_the_printed_numbers`,
      `test_appendix_content_is_cited_as_an_appendix`,
      `test_the_ingest_read_the_bytes_a10_extracted`) must stay green; the last one compares
      the PDF sha256 with `MANIFEST.json` and is unaffected by the transform.

- [ ] **Step 6: Run the full gate** — `./scripts/verify.sh` (Django check, `lint-imports`
      `knowledge ↛ core`, pytest). `knowledge/columns.py` imports nothing, so `lint-imports`
      should be untouched; if the contract needs widening, that is a stop-and-review, not a
      config edit.

- [ ] **Step 7: Commit** — `feat(corpus): de-column the page at ingest and report the pages touched`

### Task C8: Re-ingest, then prove the stored chunk is quotable

**Files:** Modify `knowledge/tests/test_ingest.py`, `knowledge/tests/test_chatbot_grounding.py`

- [ ] **Step 1: Two failing database tests** — the real gate, on stored bytes:

```python
def test_the_stored_bpp_chunk_carries_the_whole_manure_sentence(standard_set):
    ingest_standard(pdf_path=PDF_DIR / SOURCE_FILES["bpp"], standard_set=standard_set,
                    doc_key="bpp", embed=False)
    chunk = DocumentChunk.objects.get(
        document__title__contains="Basic Production", text__contains="Animal manure"
    )
    assert "sourced from farms under organic management, or from extensive farming" in flat(chunk.text)

def test_the_stored_appendix_2_chunk_carries_the_condition(standard_set):
    ingest_standard(pdf_path=PDF_DIR / SOURCE_FILES["saoso"], standard_set=standard_set,
                    doc_key="saoso", embed=False)
    chunk = DocumentChunk.objects.get(
        document__kind=StandardDocument.Kind.STANDARD, section_ref="Appendix 2",
        text__contains="Shall not constitute the main source",
    )
    assert "without prior permission from the control body" in flat(chunk.text)
```

- [ ] **Step 2: Run — expect both to fail on the text assertion** (the rows exist; the
      sentence does not span the chunk). This is the defect, in the database, where the
      audit sees it.

- [ ] **Step 3: Add the audit-level test** — build a `RetrievedChunk` from the stored row and
      run the real `audit_citations`:

```python
def test_the_verbatim_corpus_sentence_is_accepted_by_the_audit(standard_set):
    ingest_standard(pdf_path=PDF_DIR / SOURCE_FILES["bpp"], standard_set=standard_set,
                    doc_key="bpp", embed=False)
    chunk = DocumentChunk.objects.get(document__title__contains="Basic Production",
                                      text__contains="Animal manure")
    retrieved = RetrievedChunk(
        chunk_id=chunk.pk, document_title=chunk.document.title,
        document_version=chunk.document.version, section_ref=chunk.section_ref,
        heading_path=chunk.heading_path, page=chunk.page, anchor=chunk.anchor,
        text=chunk.text, score=1.0, standard_set_id=standard_set.pk,
    )
    citations, problems = audit_citations(
        [{"section_ref": chunk.section_ref or chunk.anchor, "quote": BPP_SENTENCE}],
        [retrieved], standard_set_id=standard_set.pk,
    )
    assert problems == ()
    assert citations[0].quote == BPP_SENTENCE

def test_the_paraphrased_live_reply_is_still_refused(standard_set):
    # CO-4: the 2026-10-19 reply paraphrased the standard ("must preferably be composted
    # and sourced from farms under organic management or extensive farming practices").
    # A perfect corpus does not make a paraphrase verbatim, and the audit must not be
    # loosened to make a recorded answer pass. This pins that.
    ...
    assert problems == (f"{locator}: the quote is not in the cited chunk",)
```

- [ ] **Step 4: Run — expect the verbatim case green and the paraphrase case refused.**

- [ ] **Step 5: Re-ingest the four documents locally** (needs the docker-compose Postgres).
      Delete first — `ingest_standard` is idempotent on sha256, so a re-ingest without a
      delete is a no-op and would leave the corrupted chunks in place:

```bash
python manage.py shell -c "from knowledge.models import StandardDocument as D; D.objects.all().delete()"
for doc in saoso opp bpp landscape; do
  python manage.py ingest_standard --doc $doc --file "pgs_docs/<name>.pdf" --no-embed
done
```

      Record in the session notes: per document `created`, `chunk_count`, `layout_pages`.
      Expected layout pages: 8 / 3 (+1 if C4 accepts OPP 11) / 8 / 13 (minus any Appendix 4
      exclusion).

- [ ] **Step 6: Commit** — `test(corpus): the stored chunk answers the manure question, and a paraphrase still fails`

### Task C9: Live run, UAT, hazards, close the loop

**Files:** Modify `tests/uat/mvp0_standards_and_public_site_uat.md`,
`product/docs/context/testing_hazards.md`, `HANDOVER.md`;
`product/backlog/backlog.md` (generated)

- [ ] **Step 1: One live call** for the product owner's question — *"Do I need to know where
      horse manure comes from before I can use it?"* — against the re-ingested corpus. Pass:
      a grounded answer, at least one BPP citation and one Appendix 2 citation, and each
      quote findable on the printed page. Record the exact reply and its quotes in the
      session notes: that reply is the next session's evidence, and its quote must be
      verbatim this time.

- [ ] **Step 2: Add the UAT items** (PRD §10, unchanged) and mark them human-only. Three
      scenarios plus the fresh-conversation check; the third (OPP §6.5) may legitimately
      refuse — what it must not be is a refusal caused by a mangled table. If OPP 11 is
      excluded, say so in the expected outcome, and name the follow-up.

- [ ] **Step 3: Append the hazards to `testing_hazards.md`** — one numbered entry each, with
      the evidence, because each cost real time in this session:

      1. A non-space multiset check that does not also exclude **newlines** reports every
         reordered page as total data loss. Reordering changes newlines by definition.
      2. A raw `in` substring assertion fails on a contiguous sentence, because pdftotext
         breaks lines inside it. Normalise with `" ".join(text.split())` — the rule
         `audit_citations` already uses.
      3. A loss-free/multiset test **passes for the wrong reason** when the transform never
         runs. It is only a guard beside the golden page set.
      4. Reordering page furniture invalidates any parser that reads a stamp by position
         (`heading.py::_page_stamp` did). Pin `(section_ref, anchor, page)` sets per document
         before trusting a layout change.
      5. The PRD's recorded "correct quote" was a **paraphrase**; a test written against it
         can never pass, and chasing it would have led to loosening the audit.
      6. A synthetic two-column test page whose left lines overflow the gutter is kept whole
         by rule 2 and looks like a transform bug. Build synthetic pages with gutters the
         text respects, and test detection against real bytes instead.

- [ ] **Step 4: Update `HANDOVER.md`** — the corpus defect is closed, chunk counts changed,
      the answer cache invalidates via `_corpus_fingerprint()`, and the exclusions are named.

- [ ] **Step 5: Backlog** — `python product/backlog.py --write`; move the PRD and this plan to
      `In Progress/` at the start of the build and `Done/` at the end (`--apply`). The PRD's
      errata E1–E7 were folded into the PRD on 2026-10-19 (its "2026-10-19 Errata" section),
      so §0.2 here is a summary of a correct document, not a list of outstanding repairs.

- [ ] **Step 6: Commit** — `docs(corpus): close the column-extraction defect — UAT, hazards, handover`

---

## 2. Verification gates

| Gate | Command | Pass |
|---|---|---|
| Unit + corpus | `pytest knowledge/tests/test_columns.py -v` | green; both success-gate sentences contiguous |
| No regression | `pytest knowledge/tests/` | green; `(section_ref, anchor, page)` sets unchanged (C5) |
| Architecture | `lint-imports --no-cache` | `knowledge` does not import `core`; unchanged |
| Full gate | `./scripts/verify.sh` | green, 477 existing plus the new tests |
| Fixtures are evidence | `python scripts/extract_fixtures.py && git diff --stat` | only the expected fixtures + manifest change |
| Stored corpus | C8 tests | both sentences quotable from `DocumentChunk.text` |
| Audit | C8 tests | verbatim accepted, paraphrase refused |
| Human | PRD §10 / UAT | the manure question answers with two findable quotes |

## 3. Follow-ups (named, not fixed here)

- **3-column tables** (OPP §6.5, and any Appendix 4 page excluded in C4): the detector finds
  one gutter where the page has two. Needs a multi-gutter treatment — and `de_column(bands=…)`
  already supports a per-page band override if a data table is preferred to a smarter
  detector.
- **Table row association** after de-columning (PRD §3.5): cells are separated, not paired.
- **The vector arm** — 0 of 345 chunks carry an embedding (separate defect).
- **Retrieval ranking** — the rarest-term arm returning Appendix 6b for "horse" (separate PRD).
- **Latent, noticed while planning:** `knowledge/tests/test_ingest.py` names the landscape
  `"PGS Certification Landscape_Final.pdf"` with a capital L; the shipped file is
  `landscape_Final.pdf`. It passes on Windows and will fail on a Linux CI. One-line fix,
  its own commit.

---

## 4. What "done" looks like

1. `knowledge/columns.py` exists, is pure, and is the only place layout is decided.
2. Two sentences that a farmer's question depends on are quotable from a stored chunk, and
   a test says so on post-ingest text.
3. 33 detected pages each carry a verdict; 107 pages are byte-identical; 139 pages are
   loss-free.
4. No parser moved a `page` or an `anchor`, including the landscape, whose page attribution
   this work had to rescue.
5. The recorded paraphrase is still refused — the audit was not weakened to make a bad quote
   look good.
6. The product owner's question answers with a BPP quote and an Appendix 2 quote they can
   find on paper.
