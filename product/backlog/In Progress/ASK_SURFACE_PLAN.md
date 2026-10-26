# The ask board, the answer page and the document reader — Implementation Plan

**Goal:** `/ask/` becomes a question-first board with a permalink per answer, and every citation
opens the ingested text at the clause it quotes — with no chat behaviour lost.

**Architecture:** three additions and one repair. A `PublicQuestion` table (a content store with a
publish flag, not the one-hour cache) is fed by the existing `answer_question` service through one
new service call; the board and the answer page read that table; and a document reader resolves a
citation's `document_code` to a rendered, searchable view of the stored chunks, anchored on the
section reference the citation already carries. The repair is that a citation has never been
clickable: it carries a document *title*, not a `code`.

**Tech Stack:** Django 5.2, PostgreSQL full-text search (`search_vector` on `DocumentChunk`),
semantic CSS (no build step, no CDN), HTMX already vendored for `/ask/`.

**UAT:** `tests/uat/ask_surface_uat.md` — drafted before implementation.

**Status (2026-10-23):** Tasks A1–A2, B1–B4, C1–C4, D1–D2 **built**; the gate is green at
**896 tests** (from 845), `lint-imports` kept, and `tests/e2e` green at 49. Tasks **E1–E2** are
part-done: the gate and the browser suite ran, the reader's page weight is **not yet measured**
(it needs the deployed corpus), and the UAT is drafted but unsigned. Three deviations from the
plan as written, each made while building and each recorded here rather than quietly:

1. **`published()` is wider than `APPROVED`.** Publishing a *question* is one act and answering
   it is another: an administrator who publishes a refusal creates a **gap page** (`status =
   WAITING` plus a slug), because a visible gap is the product's argument (D62) and a reviewed
   gap is as publishable as a reviewed answer. `is_published` therefore means "a person
   published this", not "it has an answer".
2. **A pre-existing defect had to be fixed first.** `publish_documents` recorded
   `PublicDocument.source_path` as an **absolute** path, so it could never equal
   `StandardDocument.source_file` and no citation would have been clickable on a second
   machine. It records the repository-relative path now, and
   `core/tests/test_documents.test_the_recorded_source_is_the_path_a_citation_joins_on` asserts
   the value the *command* writes rather than a literal (`testing_hazards.md` §1.32).
3. **The answer page got its own claim sweep.** It quotes the corpus in its clause block, so it
   is outside `PUBLIC_URLS` for the same reason the reader is; the sweep strips the
   `<blockquote>` and asserts the quotation really does trip the forbidden list, so the strip
   cannot pass vacuously.

---

## 0. Scope, and what is deliberately out

In scope (PRD §4 items 1–4, §7 DoD): the board, the answer page, the consent control, the
citation's document link, and the **text viewer/citator** the product owner named instead of a PDF
`#page=` link.

Out of scope, and why:

| Not built | Why |
|---|---|
| `/console/ask/` trace console | PRD §4 item 5. It needs stored arm/rank/score additions (P2.5a records `grounding` without them); shipping it here would smuggle in a schema change for an instrument. |
| The wider-reading tier | PRD §4 item 6 and open question 2: there are no documents behind it. A tier of names that do nothing is decoration. |
| Stage-2 rewrite of a follow-up | PRD §4 item 7 — deliberately not bought. |
| Cohort search across the whole corpus | The viewer searches **one document**. Cross-document search is retrieval, and retrieval already has one path (`default_retrieval`); a second one on a public page would be a second thing to keep honest. |

## 0.1 Decisions this plan ships on

D64–D66 are recorded in `PGS_PLATFORM_SPEC.md` §18.3 when the slice closes. Until then they are the
conservative defaults, listed here so a "no" later changes one flag rather than the build:

| # | Decision | Shipped default | Reversal cost |
|---|---|---|---|
| D64 | May a visitor's question be published? | **Opt-in only**, unticked by default. The card lands `AWAITING`; an administrator **edits the question text** before approving (that edit is where a third party's name comes out). `REJECTED` hides, never deletes. | Set `ASK_PUBLISHING_ENABLED = False` → the consent control disappears and no card is ever created; the board still renders. |
| D65 | Does generated prose live at a permanent URL? | **Only for an approved card.** *What this does not cover* is required by the answer-page template (a page without it fails a test, not a review). Every page carries `checked <date>`. | Un-approving a card removes its page (404). |
| D66 | Who re-checks a card? | The administrator, on re-approval, which bumps `checked_at`. **No automatic re-check** — that needs a model call and would silently republish prose nobody read. | — |

## 0.2 Two findings that reshape the work

**1. A citation cannot link, and the fix is not a PDF fragment.** `Citation` carries
`document` = `"SAOSO Organic Standard v2.1"` while the public route is keyed on
`saoso-standard-v2.1`; nothing maps one to the other. And `document_file()` serves
`as_attachment=True`, so `#page=76` downloads. **The product owner's call (2026-10-23): citations
link to a text viewer of the ingested documents, not to the PDF.** That is also the cheaper and
more verifiable shape — the text is already in the database, and a quote can be *found* on a
rendered page but only *hoped for* in a PDF viewer.

**2. Verbatim corpus text cannot satisfy the claim sweep, and must not be made to.** Measured on
the shipped PDFs:

```
saoso-version-2.1-2026.pdf   → 5 × "Biodynamic" / "biodynamic"
Outeniqua pgs principles…    → "pasture raised", "Pasture raised", "pasture-raised"
```

Every one of those is in the corpus and in `FORBIDDEN` (`core/tests/test_claim_discipline.py`). The
reader therefore **must not** join `PUBLIC_URLS`: the group's claims are not its quotes. Task B4
adds the sweep's exemption *and* a test that proves the sweep would still fail if the reader were
added to it — a guard that cannot fail is not a guard (`testing_hazards.md` §1.6).

## 0.3 Files touched

| File | New/Modify | Why |
|---|---|---|
| `knowledge/reading.py` | new | The reader's model: ordered chunks, stable anchors, in-document search. No `core` import. |
| `knowledge/services.py` | modify | `RetrievedChunk.document_source_file`, so a code can be resolved |
| `core/services/_documents.py` | modify | `public_codes_by_source()`, `reader_context()`, `reader_index()` |
| `core/services/_chatbot.py` | modify | `Citation.document_code` + `reading_anchor`; record them |
| `core/services/_ask.py` | new | The board and the answer page: record, approve, publish |
| `core/models/_chat.py` | modify | `PublicQuestion` |
| `core/views/_chatbot.py` | modify | Consent field, reader link, answer-page route |
| `core/views/_documents.py` | modify | `document_reader` |
| `core/forms/_chatbot.py` | modify | `publish` checkbox |
| `core/templates/public/document_reader.html` | new | The citizen's reading surface |
| `core/templates/chatbot/_board.html` | new | Board fragment (also HTMX-swappable) |
| `core/templates/chatbot/answer_page.html` | new | `/ask/<slug>/` |
| `core/templates/chatbot/panel.html`, `_thread.html` | modify | Board below the composer; citation link |
| `core/static/css/reader.css` | new | Reader styles, loaded only on the reader (`site.css` is 21.9 KB of a 30 KB cap) |
| `core/static/js/chat.js` | modify | Copy-citation button (progressive enhancement) |
| `core/admin.py` | modify | Approve / reject / re-check actions |
| `core/urls.py` | modify | `/ask/<slug:slug>/`, `/documents/<code>/read/` |
| `core/tests/test_ask_board.py`, `test_ask_answer_page.py`, `test_document_reader.py`, `test_claim_discipline.py`, `test_chat_grounding.py` | new/modify | Evidence |

## 0.4 Anchors, and why they are derived rather than stored

The citation already carries `section_ref` (`S5.1.9`, `§2.1`, `Appendix 2`) and
`ingest`'s ratchet holds **duplicate section refs at 0** (`knowledge/tests/test_ingest.py`), so a
section reference is a stable, unique, human-meaningful anchor that survives a `--force` re-ingest.
A chunk id does **not** survive one, and `build_principles.md` §I forbids a sequential id on a
public surface anyway. So the anchor is `slugify(section_ref or heading…)`, computed in one place
(`knowledge.reading.reading_anchor`) and used by both the reader and the citation link.

---

## Task A1 — The reader's model in `knowledge`

**Files:**
- Create: `knowledge/reading.py`
- Test: `knowledge/tests/test_reading.py`

- [ ] **Step 1: Write the failing test**

```python
"""A document as a reader sees it — the model behind /documents/<code>/read/.

The fixture builds chunks directly instead of ingesting a PDF: this module tests ordering,
anchors and search, and none of those depend on extraction. The corpus and the reader are
joined by one integration test in `core/tests/test_document_reader.py`, which uses the real
route against a real `StandardDocument`.
"""

from __future__ import annotations

import pytest

from knowledge.models import DocumentChunk, StandardDocument, StandardSet
from knowledge.reading import (
    SearchHit,
    contents,
    reading_anchor,
    reading_chunks,
    search_in_document,
    unique_anchors,
)

pytestmark = pytest.mark.django_db

CHUNKS = [
    ("Appendix 2", "", "APPENDICES > Appendix 2", 76,
     "Biodegradable processing by-products, plant or animal origin. Condition: free of "
     "significant contaminants; or composted before bringing onto organic land."),
    ("Appendix 2.1", "", "APPENDICES > Appendix 2", 77,
     "Wood, bark and sawdust, only if not chemically treated."),
    (None, "straw-mulch", "APPENDICES > Appendix 3", 80,
     "Straw is listed with crop residues and plant materials, with no condition attached."),
]


@pytest.fixture
def document(db) -> StandardDocument:
    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    doc = StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard",
        version="2.1",
        source_file="pgs_docs/saoso-version-2.1-2026.pdf",
        sha256="0" * 64,
        section_scheme="saoso",
    )
    for section_ref, anchor, heading_path, page, text in CHUNKS:
        DocumentChunk.objects.create(
            document=doc,
            section_ref=section_ref,
            anchor=anchor,
            heading_path=heading_path,
            page=page,
            text=text,
        )
    doc.chunk_count = len(CHUNKS)
    doc.save(update_fields=["chunk_count"])
    return doc


def test_anchors_are_stable_unique_and_url_safe(document):
    pairs = unique_anchors(reading_chunks(document))
    anchors = [anchor for _chunk, anchor in pairs]
    assert len(anchors) == len(set(anchors)), "two chunks share an anchor"
    assert anchors == ["appendix-2", "appendix-2-1", "straw-mulch"]
    assert all(a == a.lower() for a in anchors)


def test_a_repeated_reference_keeps_the_plain_anchor_first(document):
    """A section reference is a citation's target, so the first passage keeps the name.

    Duplicate `section_ref`s are held at zero by the ingest ratchet, but a *heading* scheme
    document can repeat a heading across pages, and a citation must still land on the first
    occurrence rather than a suffixed one nobody can guess.
    """
    chunk = document.chunks.get(anchor="straw-mulch")
    chunk.section_ref = None
    chunk.heading_path = "APPENDICES > Appendix 2"
    chunk.save(update_fields=["section_ref", "heading_path"])
    anchors = [a for _c, a in unique_anchors(reading_chunks(document))]
    assert anchors[:2] == ["appendix-2", "appendix-2-2"]
    assert reading_anchor(None, "", "APPENDICES > Appendix 2") == "appendix-2"


def test_reading_chunks_are_in_document_order(document):
    chunks = reading_chunks(document)
    assert [c.pk for c in chunks] == sorted(c.pk for c in chunks)
    assert len(chunks) == document.chunk_count


def test_contents_names_every_anchor_once(document):
    entries = contents(document)
    assert [e.anchor for e in entries] == [a for _c, a in unique_anchors(reading_chunks(document))]
    assert all(e.locator for e in entries), "an entry with no locator is unreadable in a contents list"


def test_search_finds_a_stored_clause(document):
    hits = search_in_document(document, "contaminants")
    hit = hits[0]
    assert isinstance(hit, SearchHit)
    assert "contaminants" in hit.hit.lower()
    assert hit.anchor == "appendix-2"
    assert hit.before + hit.hit + hit.after  # a snippet, not an empty window


def test_search_falls_back_to_any_of_the_words(document):
    """`websearch_to_tsquery` ANDs its terms into zero rows (testing_hazards §2.4).

    The box is a search box, not a query language: a two-word query must find the passage
    that has one of the words rather than render "no matches" for a query a person typed.
    """
    assert search_in_document(document, "cardboard sawdust"), "the OR pass did not run"


def test_an_empty_query_searches_nothing(document):
    """Guarded explicitly: an empty query that matched everything would render the whole
    document as a 'result', and the page would look broken but pass a `!= []` assertion."""
    assert search_in_document(document, "   ") == []
```

- [ ] **Step 2: Run the tests and watch them fail for the right reason**

Run: `python -m pytest knowledge/tests/test_reading.py -q`
Expected: `ModuleNotFoundError: No module named 'knowledge.reading'`.

- [ ] **Step 3: Write `knowledge/reading.py`**

```python
"""A document as a reader sees it: ordered passages, stable anchors, and a search box.

`/documents/<code>/read/` is where a citation lands. It cannot be the PDF: the file is
served as an attachment, and a `#page=` fragment has no viewer to land in. It is also the
*cheaper* surface — the text is already in `DocumentChunk`, and a quote can be found on a
rendered page in a way it cannot be found by hoping a PDF viewer scrolls to a number.

**The anchor is derived, never stored.** `section_ref` survives a `--force` re-ingest; a
chunk id does not, and `build_principles.md` §I forbids a sequential id on a public surface.
The duplicate-`section_ref` ratchet is held at zero (`tests/test_ingest.py`), which is what
makes a section reference a usable anchor rather than a collision.

No `core` import, ever (`build_principles.md` §I). This module knows about documents and
chunks; it does not know what a URL is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import QuerySet
from django.utils.text import slugify

from knowledge.models import DocumentChunk, StandardDocument

#: Where a search result shows. Wide enough to read a rule, narrow enough to scan.
SNIPPET_CHARS = 240

#: The generated `search_vector` is built with `config="english"`; a query with any other
#: configuration silently matches nothing (`testing_hazards.md` §2.4 is the same family).
SEARCH_CONFIG = "english"


def reading_chunks(document: StandardDocument) -> list[DocumentChunk]:
    """In: a document. Out: its chunks in document order. Side effects: one query.

    Ordered by primary key, not by page: `bulk_create` writes chunks in document order,
    and `Meta.ordering` is deliberately empty ("B7 fuses ranked queries, it does not
    page"). Page order alone would interleave chunks inside one page arbitrarily.
    """
    return list(document.chunks.order_by("id"))


def reading_anchor(
    section_ref: str | None, anchor: str = "", heading_path: str = ""
) -> str:
    """In: a chunk's locators. Out: a URL fragment, stable across re-ingest.

    `section_ref` first because it is what a citation quotes and what survives a rebuild.
    Falls back to the content-derived `anchor` and then to the heading trail, so no chunk
    is unreachable — `ingest` only guarantees one of the three is set.
    """
    for candidate in (section_ref, anchor, heading_path.split(" > ")[-1]):
        if candidate and candidate.strip():
            slug = slugify(candidate, allow_unicode=False)[:64].strip("-_")
            if slug:
                return slug
    return "passage"


def unique_anchors(chunks: list[DocumentChunk]) -> list[tuple[DocumentChunk, str]]:
    """In: chunks in order. Out: `(chunk, anchor)` with collisions suffixed `-2`, `-3`…

    A suffix is a local disambiguator, not an identity: the *first* chunk with a
    reference keeps the plain anchor, so a citation's link lands on the passage a reader
    searching for that reference expects first.
    """
    seen: dict[str, int] = {}
    pairs: list[tuple[DocumentChunk, str]] = []
    for chunk in chunks:
        base = reading_anchor(chunk.section_ref, chunk.anchor, chunk.heading_path)
        count = seen.get(base, 0) + 1
        seen[base] = count
        pairs.append((chunk, base if count == 1 else f"{base}-{count}"))
    return pairs


@dataclass(frozen=True)
class ReadingEntry:
    """One line of the reader's contents list."""

    anchor: str
    locator: str
    page: int | None
    heading_path: str


def contents(document: StandardDocument) -> list[ReadingEntry]:
    """In: a document. Out: one entry per chunk, in order. Side effects: one query."""
    return [
        ReadingEntry(
            anchor=anchor,
            locator=chunk.section_ref or chunk.anchor or chunk.heading_path or f"p{chunk.page}",
            page=chunk.page,
            heading_path=chunk.heading_path,
        )
        for chunk, anchor in unique_anchors(reading_chunks(document))
    ]


@dataclass(frozen=True)
class SearchHit:
    """One in-document search result. `before`/`hit`/`after` so a template escapes each."""

    anchor: str
    locator: str
    page: int | None
    before: str
    hit: str
    after: str


def _words(query: str) -> list[str]:
    return [word for word in re.split(r"[^\w§.-]+", query) if len(word) > 1]


def search_in_document(
    document: StandardDocument, query: str, *, limit: int = 20
) -> list[SearchHit]:
    """In: a document and what a person typed. Out: matching passages, best first.

    In:  `query` — free text from the reader's box; `limit` — how many passages.
    Out: `SearchHit` rows; empty when the query is empty or nothing matches.
    Side effects: none (read-only).
    Fails: never deliberately. A search box that raises is worse than one that finds
        nothing, and this page has no error surface for it.

    Two passes, because a search box is not a query language. `websearch_to_tsquery`
    ANDs its terms, so "cardboard neighbour" finds only a passage containing both — a
    real question typed into a search box usually means *any* of its words. The first
    pass keeps phrase behaviour honest ("free of significant contaminants"); the second
    ORs the words and runs only when the first found nothing.
    """
    words = _words(query)
    if not words:
        return []

    base = document.chunks.all()
    for search_query in (
        SearchQuery(query, config=SEARCH_CONFIG, search_type="websearch"),
        SearchQuery(" | ".join(words), config=SEARCH_CONFIG, search_type="raw"),
    ):
        ranked = (
            base.filter(search_vector=search_query)
            .annotate(rank=SearchRank("search_vector", search_query))
            .order_by("-rank", "id")[:limit]
        )
        hits = [_hit(chunk, words) for chunk in ranked]
        if hits:
            return hits
    return []


def _hit(chunk: DocumentChunk, words: list[str]) -> SearchHit:
    """The passage, sliced around the first word the reader typed."""
    text = chunk.text or ""
    lowered = text.lower()
    positions = [pos for pos in (lowered.find(word.lower()) for word in words) if pos >= 0]
    at = min(positions) if positions else 0
    start = max(0, at - SNIPPET_CHARS // 3)
    end = min(len(text), start + SNIPPET_CHARS)
    window = text[start:end]
    word_at = max(0, at - start)
    length = len(next((w for w in words if lowered.find(w.lower()) == at), ""))
    return SearchHit(
        anchor=reading_anchor(chunk.section_ref, chunk.anchor, chunk.heading_path),
        locator=chunk.section_ref or chunk.anchor or chunk.heading_path or f"p{chunk.page}",
        page=chunk.page,
        before=window[:word_at],
        hit=window[word_at : word_at + length] or window[word_at : word_at + 1],
        after=window[word_at + length :],
    )


__all__ = [
    "ReadingEntry",
    "SearchHit",
    "contents",
    "reading_anchor",
    "reading_chunks",
    "search_in_document",
    "unique_anchors",
]
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest knowledge/tests/test_reading.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add knowledge/reading.py knowledge/tests/test_reading.py
git commit -m "feat(knowledge): a document as a reader sees it — ordered chunks, stable anchors, in-document search"
```

---

## Task A2 — A citation learns which document it is in

**Files:**
- Modify: `knowledge/services.py` (`RetrievedChunk.document_source_file`)
- Modify: `core/services/_documents.py` (`public_codes_by_source`)
- Modify: `core/services/_chatbot.py` (`Citation`, `audit_citations`, `_citation_record`, `answer_question`)
- Test: `core/tests/test_chat_grounding.py`

- [ ] **Step 1: Write the failing test**

```python
def test_a_citation_knows_the_public_document_it_came_from(turn):
    """A citation carries a *title* today, and the public route is keyed on a *code*.

    The join is `PublicDocument.source_path == StandardDocument.source_file` — both
    already hold `pgs_docs/<file>.pdf`, and `source_path` exists precisely so a published
    file can be traced to the shipped document. No migration, and no new mapping table
    that could disagree with the two seeds that already exist.
    """
    answer = turn("Can I use cardboard from my neighbour?")
    citation = answer.citations[0]
    assert citation.document_code == "saoso-standard-v2.1"
    assert citation.reading_anchor  # the fragment the reader will land on


def test_a_corpus_document_with_no_published_twin_carries_no_code(turn_with_unpublished_corpus):
    """The link must be *absent*, not broken: an empty code renders no anchor tag.

    A corpus may be ingested from a document the group does not publish (a draft, an
    internal edition). A citation from it is still showable — the quote is the evidence —
    but a link to nowhere is worse than plain text.
    """
    answer = turn_with_unpublished_corpus("Can I use cardboard from my neighbour?")
    assert answer.citations[0].document_code == ""
```

- [ ] **Step 2: Run and watch them fail**

Run: `python -m pytest core/tests/test_chat_grounding.py -q -k "document it came from or no published twin"`
Expected: `AttributeError: 'Citation' object has no attribute 'document_code'`.

- [ ] **Step 3: Add the field to `RetrievedChunk`**

In `knowledge/services.py`, add to the dataclass and to `_retrieved` (the one construction site,
`select_related("document")` is already there so this costs no query):

```python
    #: The file the corpus was ingested from, e.g. `pgs_docs/saoso-version-2.1-2026.pdf`.
    #: Carried so a *caller* can map a chunk to whatever public address that document has
    #: — `knowledge` does not know what a URL is, and must not learn (build_principles §I).
    document_source_file: str = ""
```

```python
        document_source_file=chunk.document.source_file,
```

- [ ] **Step 4: Resolve codes in `core/services/_documents.py`**

```python
def public_codes_by_source() -> dict[str, str]:
    """In: nothing. Out: `{source_file: code}` for the published documents. One query.

    The join that makes a citation clickable without a migration: `PublicDocument.source_path`
    and `StandardDocument.source_file` are both `pgs_docs/<file>.pdf`, seeded from the same
    filenames. A corpus document with no published twin is simply absent from the mapping,
    and the template must then render text rather than a link.
    """
    return {
        document.source_path: document.code
        for document in PublicDocument.objects.published().exclude(source_path="")
    }
```

- [ ] **Step 5: Attach it in the audit**

In `core/services/_chatbot.py`:

```python
class Citation:
    ...
    document_code: str = ""
    reading_anchor: str = ""
```

`audit_citations` gains one keyword parameter and uses it at the one construction site:

```python
def audit_citations(
    raw_citations: Sequence[dict],
    chunks: Sequence[RetrievedChunk],
    *,
    standard_set_id: int | None,
    document_codes: Mapping[str, str] | None = None,
) -> tuple[list[Citation], tuple[str, ...]]:
```

```python
            Citation(
                ...
                document_code=(document_codes or {}).get(matched.document_source_file, ""),
                reading_anchor=reading_anchor(
                    matched.section_ref, matched.anchor, matched.heading_path
                ),
            )
```

`answer_question` resolves the mapping once per turn — one query, not one per citation:

```python
    citations, problems = audit_citations(
        reply.citations,
        chunks,
        standard_set_id=session.standard_set_id,
        document_codes=public_codes_by_source(),
    )
```

And `_citation_record` records both, because a **card** outlives the corpus and its link must
still resolve after a re-ingest:

```python
                "document_code": citation.document_code,
                "reading_anchor": citation.reading_anchor,
```

- [ ] **Step 6: Run**

Run: `python -m pytest core/tests/test_chat_grounding.py core/tests/test_chatbot_grounding.py -q`
Expected: PASS, and the two new tests pass with the rest.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(chat): a citation knows the public document it came from, and the anchor it lands on"
```

---

## Task B1 — Resolve a public document to the text we ingested

**Files:**
- Modify: `core/services/_documents.py`
- Modify: `core/services/_public.py` (a chrome helper for pages whose `Page` is per request)
- Modify: `core/urls.py`, `core/views/_documents.py`
- Test: `core/tests/test_document_reader.py`

- [ ] **Step 1: Write the failing test**

```python
"""The document reader — the surface a citation lands on.

Three properties are load-bearing and none of them is visual: the text is **verbatim from
the stored corpus** (a reader who checks a quote against this page must find it), the
anchors are **the ones citations use** (`knowledge.reading.reading_anchor`), and the page
never exposes a sequential id or a media path (`build_principles.md` §I, §VI).
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from knowledge.models import DocumentChunk, StandardDocument, StandardSet

pytestmark = pytest.mark.django_db

CORPUS_SOURCE = "pgs_docs/saoso-version-2.1-2026.pdf"


@pytest.fixture
def ingested(public_documents):
    """One ingested document whose `source_file` matches the published row's `source_path`."""
    corpus = StandardSet.objects.create(code="outeniqua", label="Outeniqua", is_default=True)
    document = StandardDocument.objects.create(
        standard_set=corpus,
        kind=StandardDocument.Kind.STANDARD,
        issuing_body="SAOSO",
        title="SAOSO Standard for Organic Production and Processing",
        version="2.1",
        source_file=CORPUS_SOURCE,
        sha256="a" * 64,
        section_scheme="saoso",
    )
    DocumentChunk.objects.create(
        document=document,
        section_ref="Appendix 2",
        heading_path="APPENDICES > Appendix 2",
        page=76,
        text="Biodegradable processing by-products … free of significant contaminants.",
    )
    return document


def test_the_reader_is_reachable_at_the_published_code(client, ingested):
    response = client.get("/documents/saoso-standard-v2.1/read/")
    assert response.status_code == 200
    assert b"free of significant contaminants" in response.content


def test_the_text_is_the_stored_text_not_a_reformatting(client, ingested):
    """Asserted against the database, not against a fixture string.

    A reader checking a quotation against this page is the whole point of the surface; a
    template that rewrapped, truncated or re-flowed the text would still look right.
    """
    chunk = DocumentChunk.objects.get()
    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()
    assert chunk.text in body


def test_an_unpublished_document_has_no_reader(client, public_documents):
    public_documents.update(is_published=False)
    assert client.get("/documents/saoso-standard-v2.1/read/").status_code == 404


def test_a_published_document_with_no_ingested_text_says_so(client, public_documents):
    """Not a 404 and not a 500: the document exists, its *text* is what is missing.

    A citation link pointing here must land on an explanation with the PDF behind it,
    because a reader following a citation is holding a quote they cannot otherwise check.
    """
    response = client.get("/documents/opp/read/")
    assert response.status_code == 200
    assert b"not published the text" in response.content


def test_the_reader_never_renders_a_sequential_id_or_a_media_path(client, ingested):
    chunk = DocumentChunk.objects.get()
    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode()
    assert f'id="{chunk.pk}"' not in body
    assert "/media/" not in body
```

- [ ] **Step 2: Run and watch it fail**

Run: `python -m pytest core/tests/test_document_reader.py -q`
Expected: 404s — the route does not exist.

- [ ] **Step 3: The service**

In `core/services/_documents.py`:

```python
@dataclass(frozen=True)
class ReaderPassage:
    """One passage as the reader renders it. `text` is the stored chunk, unmodified."""

    anchor: str
    locator: str
    page: int | None
    heading_path: str
    text: str


@dataclass(frozen=True)
class Reader:
    """Everything `/documents/<code>/read/` renders. A dataclass, so a test can assert it."""

    document: PublicDocument
    corpus: StandardDocument | None
    passages: tuple[ReaderPassage, ...]
    contents: tuple[ReadingEntry, ...]
    hits: tuple[SearchHit, ...]
    query: str


def corpus_for(document: PublicDocument) -> StandardDocument | None:
    """In: a published document. Out: the ingested twin, or None. One query.

    The join is provenance, not guesswork: `source_path` and `source_file` are both
    `pgs_docs/<file>.pdf` because the seed and the ingest read the same filenames. When a
    document exists in two corpora the deployed default wins, so the reader shows the text
    the assistant is answering from.
    """
    return (
        StandardDocument.objects.filter(source_file=document.source_path)
        .select_related("standard_set")
        .order_by("-standard_set__is_default", "id")
        .first()
    )


def reader_for(document: PublicDocument, query: str = "") -> Reader:
    """In: a published document and what the reader searched for. Out: a `Reader`.

    In:  `query` — free text from the search box; empty for the plain view.
    Out: passages in document order, the contents list, and any search hits.
    Side effects: at most three queries.
    Fails: never. A published document whose text has not been ingested returns
        `corpus=None`; the view renders an explanation, because a citation pointing here
        must not 404.
    """
    document_row = corpus_for(document)
    if document_row is None:
        return Reader(document, None, (), (), (), query.strip())
    pairs = unique_anchors(reading_chunks(document_row))
    passages = tuple(
        ReaderPassage(
            anchor=anchor,
            locator=chunk.section_ref or chunk.anchor or chunk.heading_path or f"p{chunk.page}",
            page=chunk.page,
            heading_path=chunk.heading_path,
            text=chunk.text,
        )
        for chunk, anchor in pairs
    )
    return Reader(
        document=document,
        corpus=document_row,
        passages=passages,
        contents=tuple(contents(document_row)),
        hits=tuple(search_in_document(document_row, query)) if query.strip() else (),
        query=query.strip(),
    )
```

- [ ] **Step 4: A chrome helper, so a per-request page is not a special case**

In `core/services/_public.py`, extract the dict and add the entry point used by the reader and
the answer page:

```python
def chrome_context(page: Page) -> dict:
    """The chrome for a page whose `Page` is built per request.

    `/ask/<slug>/` and `/documents/<code>/read/` have no entry in `PAGES` — they are rows,
    not routes — but they still need the nav, the footer and the fee figures the home page
    reads. Passing a `Page` instance keeps one shape for `base.html`'s `og:` tags.
    """
    return {
        "page": page,
        "nav": NAV,
        "pages": PAGES,
        "membership_farmer_cents": MEMBERSHIP_FARMER_CENTS,
        "membership_pgs_sa_cents": MEMBERSHIP_PGS_SA_CENTS,
        "fee_bands": FEE_BANDS,
    }


def public_context(page_key: str) -> dict:
    ...  # unchanged, but its body becomes `return chrome_context(PAGES[page_key])`
```

- [ ] **Step 5: The route and the view**

`core/urls.py` — beside the existing document routes:

```python
    # The reader: the text we ingested, at the code the citation names. Deliberately NOT
    # under `/media/` and deliberately not a PDF fragment — `document_file` downloads, so
    # a `#page=` fragment has no viewer to land in.
    path("documents/<str:code>/read/", document_reader, name="document_reader"),
```
`core/views/_documents.py` — thin by rule:

```python
def document_reader(request, code: str):
    """The ingested text of one published document, searchable and anchorable.

    Unpublished and unknown codes are the same 404, for the same reason the download is:
    `is_published` is the only gate.
    """
    document = get_object_or_404(PublicDocument.objects.published(), code=code)
    reader = reader_for(document, request.GET.get("q", ""))
    page = Page(
        key="document-reader",
        title=f"{document.title} — the text, as we ingested it",
        description=(
            f"The text of {document.title} that the assistant answers from, with the "
            "passages a citation names."
        ),
        eyebrow="The documents",
        heading=document.title,
        lede=(
            "This is the text we ingested, passage by passage. Search it, or follow a "
            "citation straight to the clause it quotes."
        ),
    )
    return render(
        request,
        "public/document_reader.html",
        chrome_context(page) | {"reader": reader},
    )
```

- [ ] **Step 6: Write the template (Task B2) before committing**

The tests in Step 1 cannot pass until `public/document_reader.html` exists. This is the plan's
only cross-task dependency, and it is stated rather than hidden: B1 and B2 land in one commit.

- [ ] **Step 7: Run**

Run: `python -m pytest core/tests/test_document_reader.py -q`
Expected: PASS (5 tests) once B2's template exists.

---

## Task B2 — The reader page

**Files:**
- Create: `core/templates/public/document_reader.html`
- Create: `core/static/css/reader.css`
- Modify: `core/templates/base.html` (one block)
- Test: `core/tests/test_document_reader.py` (add)

- [ ] **Step 1: Add the missing head block to `base.html`**

```html
  {% block head_extra %}{% endblock %}
```

Immediately after the `og:` tags. It exists because an answer page whose card is not approved
must carry `noindex`, and the only page that needs that today (`uat/console.html`) is a
standalone template. One block, used by one page, rather than a second base.

- [ ] **Step 2: The template**

```html
{% extends "base.html" %}
{% load static %}
{% comment %}
  The reader — where a citation lands (the product owner's decision, 2026-10-23: a citation
  opens the text we ingested, not a PDF page).

  **This page renders the document's own words and nothing else.** It is not in
  `PUBLIC_URLS` (`core/tests/test_public.py`) because the corpus contains words the claim
  sweep forbids the *group* to use — "biodynamic" appears in SAOSO, "pasture raised" in the
  OPP. Quoting is not claiming; Task B4 makes that exemption explicit and proves the sweep
  still fails when it should.
{% endcomment %}

{% block extra_css %}
  <link rel="stylesheet" href="{% static 'css/reader.css' %}">
{% endblock %}

{% block content %}
  <header class="page-head page-head--reader">
    <div class="container">
      <p class="eyebrow">{{ page.eyebrow }}</p>
      <h1 class="serif-title page-head__title">{{ page.h1 }}</h1>
      <p class="page-head__lede">{{ page.lede }}</p>
    </div>
  </header>

  <section class="section">
    <div class="container reader">

      {% if not reader.corpus %}
        <div class="reader__missing">
          <h2 class="serif-title">We have not published the text of this document yet</h2>
          <p>
            This document is published as a file, and its text has not been ingested on this
            deployment — so a citation from it cannot open here. The file itself is complete.
          </p>
          <p>
            <a class="btn btn--forest"
               href="{% url 'core:document_file' code=reader.document.code %}">
              Open {{ reader.document.title }}
            </a>
          </p>
        </div>
      {% else %}
        <form class="reader__search" method="get"
              action="{% url 'core:document_reader' code=reader.document.code %}">
          <label class="reader__search-label" for="reader-q">Search this document</label>
          <div class="reader__search-row">
            <input class="input" id="reader-q" type="search" name="q" value="{{ reader.query }}"
                   placeholder="e.g. contaminants, manure, seal licence" autocomplete="off">
            <button class="btn btn--ochre" type="submit">Search</button>
          </div>
          {% if reader.query %}
            <p class="reader__search-note">
              {{ reader.hits|length }} passage{{ reader.hits|length|pluralize }} matching
              &ldquo;{{ reader.query }}&rdquo; &middot;
              <a href="{% url 'core:document_reader' code=reader.document.code %}">clear</a>
            </p>
          {% endif %}
        </form>

        {% if reader.hits %}
          <ol class="reader__hits">
            {% for hit in reader.hits %}
              <li class="reader__hit">
                <a class="reader__hit-locator" href="#{{ hit.anchor }}">
                  {{ hit.locator }}{% if hit.page %} &middot; p. {{ hit.page }}{% endif %}
                </a>
                <p class="reader__hit-text">&hellip;{{ hit.before }}<mark>{{ hit.hit }}</mark>{{ hit.after }}&hellip;</p>
              </li>
            {% endfor %}
          </ol>
        {% elif reader.query %}
          <p class="reader__no-hits">
            No passage in this document matches &ldquo;{{ reader.query }}&rdquo;. That is
            usually the answer to a question the documents cannot settle.
          </p>
        {% endif %}

        <div class="reader__body">
          <nav class="reader__contents" aria-label="Contents">
            <p class="reader__contents-title">Contents</p>
            <ol class="reader__contents-list">
              {% for entry in reader.contents %}
                <li>
                  <a href="#{{ entry.anchor }}">{{ entry.locator }}</a>
                  {% if entry.page %}<span class="reader__page">p. {{ entry.page }}</span>{% endif %}
                </li>
              {% endfor %}
            </ol>
          </nav>

          <div class="reader__passages">
            {% for passage in reader.passages %}
              <article class="passage" id="{{ passage.anchor }}">
                <p class="passage__locator">
                  {{ passage.locator }}{% if passage.page %} &middot; printed p. {{ passage.page }}{% endif %}
                </p>
                <p class="passage__text">{{ passage.text|linebreaksbr }}</p>
              </article>
            {% endfor %}
          </div>
        </div>
      {% endif %}

      <p class="reader__provenance">
        Text ingested from
        <a href="{% url 'core:document_file' code=reader.document.code %}">{{ reader.document.title }}</a>.
        Every passage above is the document's own words, reproduced without editing. The
        assistant answers only from text like this.
      </p>
    </div>
  </section>
{% endblock %}
```

- [ ] **Step 3: The stylesheet**

Create `core/static/css/reader.css` with semantic classes only (DESIGN §6), every colour from
`root.css` (no raw hex), and one breakpoint: below 900 px the contents list moves above the text
and becomes a `<details>`-free horizontal strip is **not** acceptable — it stays a list, collapsed
behind a `details`/`summary` toggle. Touch targets ≥44 px on every contents link (DESIGN rule 5).

Two rules are load-bearing:

```css
/* The anchor a citation names. Not a colour change: the reader must be able to see
   *where the clause is* without losing the passages around it. */
.passage:target {
  background: var(--brand-cream-warm);
  border-left: 3px solid var(--brand-ochre);
  padding-left: 0.75rem;
  scroll-margin-top: 5rem; /* the sticky header must not cover the landed-on line */
}
```

`scroll-margin-top` is not cosmetic: without it the site header covers the first line of the
target passage, and the reader lands one line short of the clause on a laptop.

- [ ] **Step 4: Run**

Run: `python -m pytest core/tests/test_document_reader.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Look at it, at two widths**

Run: `python manage.py runserver`, open `/documents/saoso-standard-v2.1/read/`, then the same URL
at 390 px. No test replaces UAT Scenario 3 or 5.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(documents): a reader for the ingested text — searchable, anchored, verbatim"
```

---

## Task B3 — A citation opens the clause

**Files:**
- Modify: `core/templates/chatbot/_thread.html`
- Modify: `core/services/_chatbot.py` (`Citation.read_url` — one place, not two templates)
- Test: `core/tests/test_chatbot_surface.py`

- [ ] **Step 1: Write the failing test**

```python
def test_a_citation_links_to_the_reader_at_its_anchor(client, answer_with_citations):
    """The link is built once, in the service, because two surfaces render a citation.

    A template that assembled the URL would be a second place to keep in step, and the
    failure mode is silent: a link that 200s on the wrong document's front page.
    """
    html = client.get("/ask/").content.decode()
    assert 'href="/documents/saoso-standard-v2.1/read/#appendix-2"' in html


def test_a_citation_with_no_document_code_renders_no_link(...):
    """A corpus document the group does not publish has no public address.

    The quote is still shown — it is the evidence — but it is not a link to nowhere.
    """
```

- [ ] **Step 2: Add the property**

```python
    @property
    def read_url(self) -> str:
        """The reader URL this citation lands on, or "" when the document is not published.

        A property rather than a `reverse()` in a template: `_thread.html` and the answer
        page both render citations, and two call sites assembling one URL is two things to
        keep honest. `build_principles.md` §II — logic lives in the service.
        """
        if not self.document_code:
            return ""
        return f"{reverse('core:document_reader', kwargs={'code': self.document_code})}#{self.reading_anchor}"
```

- [ ] **Step 3: Use it in `_thread.html`**

Inside the `<details>` block, after the source line:

```html
                {% if citation.read_url %}
                  <p class="cite-source">
                    <a class="cite__read" href="{{ citation.read_url }}">
                      Read it in {{ citation.document }} &rarr;
                    </a>
                  </p>
                {% endif %}
```

- [ ] **Step 4: Run**

Run: `python -m pytest core/tests/test_chatbot_surface.py core/tests/test_follow_up.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(chat): every citation opens the clause it quotes"
```

---

## Task B4 — The claim sweep, and the one route it must not cover

**Files:**
- Modify: `core/tests/test_claim_discipline.py`
- Test: same

**Why this is a task and not a footnote.** The reader renders the corpus verbatim, and the corpus
contains the words the sweep forbids the group to use. Measured on the shipped PDFs:
`saoso-version-2.1-2026.pdf` contains `Biodynamic`/`biodynamic` **5 times**, and the OPP contains
`pasture raised`, `Pasture raised` and `pasture-raised`. Adding the reader to `PUBLIC_URLS` would
either fail the build or — worse — tempt someone to add the reader to an allow-list *without* a
test, which is how a sweep stops sweeping.

- [ ] **Step 1: Write the failing tests**

```python
#: Routes that reproduce a document's own words. They are **exempt from the term sweep and
#: not exempt from it in spirit**: the sweep asks whether *the group* makes an unsupported
#: claim, and a quotation is not a claim. Every entry names its reason and its evidence, and
#: `test_the_exemption_is_necessary` proves the exemption is load-bearing rather than a
#: convenience.
VERBATIM_ROUTES: dict[str, str] = {
    "/documents/saoso-standard-v2.1/read/": (
        "SAOSO v2.1 uses 'biodynamic' 5 times and the OPP prints 'pasture raised'; both are "
        "in FORBIDDEN. Reproducing a standard is not endorsing it."
    ),
}


def test_the_exemption_list_has_a_reason_per_route():
    assert VERBATIM_ROUTES, "an empty exemption list is a list that exempts nothing"
    assert all(reason.strip() for reason in VERBATIM_ROUTES.values())


def test_the_exemption_is_necessary(client, ingested_reader):
    """Prove the guard can fail: the reader *does* render a forbidden term.

    Without this, the exemption is indistinguishable from a route that happens to be clean,
    and the next person deletes it without noticing what it protected.
    """
    html = client.get("/documents/saoso-standard-v2.1/read/").content.decode().lower()
    assert "biodynamic" in html


def test_the_reader_adds_no_claim_of_its_own(client, ingested_reader):
    """Strip the document's words; sweep what is left — the group's own copy.

    This is the half of the sweep the exemption must not lose: the chrome, the head, the
    search box and the provenance line are the group speaking, and none of them may make a
    certification claim or render a seal.
    """
    body = client.get("/documents/saoso-standard-v2.1/read/").content.decode().lower()
    our_words = re.sub(r'<article class="passage".*?</article>', "", body, flags=re.S)
    our_words = re.sub(r'<p class="reader__hit-text">.*?</p>', "", our_words, flags=re.S)
    for term in FORBIDDEN:
        assert term not in our_words, f"{term!r} appears in the reader's own copy"
```

- [ ] **Step 2: Run and watch them fail**

Run: `python -m pytest core/tests/test_claim_discipline.py -q -k "exemption or own claim"`
Expected: FAIL — `VERBATIM_ROUTES` and the `ingested_reader` fixture do not exist.

- [ ] **Step 3: Implement**

Add the three tests, the `VERBATIM_ROUTES` mapping and an `ingested_reader` fixture (reusing
`core/tests/test_document_reader.py`'s fixture shape, with one chunk whose text contains
`biodynamic preparations`, which is SAOSO's own phrase). **Do not** add the reader to `PAGES` or to
`PUBLIC_URLS`.

- [ ] **Step 4: Run the whole sweep**

Run: `python -m pytest core/tests/test_claim_discipline.py -q`
Expected: PASS — including the pre-existing parametrised sweeps, unchanged.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test(claims): the reader is exempt from the term sweep for a reason it has to prove"
```

---

## Task C1 — `PublicQuestion`: a table with a publish flag

**Files:**
- Modify: `core/models/_chat.py`
- Create: `core/migrations/0007_publicquestion.py`
- Test: `core/tests/test_ask_board.py`

**Why a model and not the cache.** PRD §5.5: *the cache is not the archive.* A cache entry is
keyed on a normalised question and dies in an hour; a card is `asked 21 times`, `checked
2026-10-23`, `approved by Kobus`, and is part of the site's sitemap. D62 already decided this;
the model is the decision's mechanical consequence.

- [ ] **Step 1: Write the failing test**

```python
def test_a_card_defaults_to_unpublished(db):
    """The single most important default on this model.

    A visitor's free text may never reach a public page without a person reading it, so the
    default cannot be `APPROVED` and it cannot be "whatever the form posted". Asserted
    directly, because a future migration that flips the default would still pass every board
    test that approves its own fixture first (testing_hazards.md §1.6).
    """
    card = PublicQuestion.objects.create(question="Can I use cardboard?", asked_key="k")
    assert card.status == PublicQuestion.Status.AWAITING
    assert card.slug is None, "an unpublished card has no public address"
    assert not card.is_published
    assert card.noindex
```

- [ ] **Step 2: Write the model**

Append to `core/models/_chat.py` (the module docstring gains a fourth bullet: the board is a
*content store*, and the cache is not it):

```python
class PublicQuestionQuerySet(models.QuerySet):
    """`published()` is the only filter a public view may use.

    Published means **a person published this question** — a slug exists and an administrator
    approved it. Deliberately wider than "answered": a refusal the group is willing to show is
    the most honest row on the board, and it is published by the same act, with the same review,
    as an answer (see the status note above, deviation 1).
    """

    def published(self) -> PublicQuestionQuerySet:
        return self.filter(
            slug__isnull=False,
            status__in=[PublicQuestion.Status.APPROVED, PublicQuestion.Status.WAITING],
        )


class PublicQuestion(models.Model):
    """A question and its answer, kept because a person approved publishing it.

    This is the board's content store (D62). It is **not** the answer cache: a cache entry
    is keyed on a normalised question, lives an hour and is not a record; a card is asked
    many times, checked on a date, approved by a named person and reachable at a permalink.

    **`question` is the published wording, not the visitor's.** The administrator edits it
    before approving — that edit is where a third party's name comes out (D64). The original
    stays in `ChatMessage`, where D59 already governs its retention.

    `status` starts at `AWAITING` and only a person moves it. `REJECTED` hides rather than
    deletes, so "we decided not to publish this" is answerable later.
    """

    class Status(models.TextChoices):
        AWAITING = "AWAITING", "Awaiting review"
        APPROVED = "APPROVED", "Published"
        WAITING = "WAITING", "Waiting on a person"
        REJECTED = "REJECTED", "Not published"

    #: NULL until a person approves: the address is generated from the **edited** question
    #: at approval time, so a redacted question gets a clean slug and an unpublished card has
    #: no public address at all (Postgres allows many NULLs under a unique index).
    slug = models.SlugField(max_length=120, unique=True, null=True, blank=True)
    question = models.TextField()
    asked_key = models.CharField(
        max_length=64,
        db_index=True,
        help_text=(
            "sha256 of the normalised question as the visitor typed it — the dedupe key. "
            "Separate from `question` because an administrator edits that one, and two "
            "visitors asking the same thing must not diverge when the wording is redacted."
        ),
    )
    answer = models.TextField(blank=True, default="")
    covers = models.TextField(
        blank=True,
        default="",
        help_text=(
            "What this answer does not cover, one item per line. Required on the page: an "
            "answer that states its boundary is the honest counterpart to a grounded quote."
        ),
    )
    citations = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "The accepted citations as they were shown — document_code, reading_anchor, "
            "section_ref, sub_ref, page, quote, document. A snapshot, not a lookup: the "
            "corpus can be re-ingested and this page must still say what was claimed."
        ),
    )
    topic = models.CharField(
        max_length=60,
        blank=True,
        default="",
        help_text=(
            "The board's filter chip, e.g. 'Inputs', 'Animals', 'Money'. Free text, not a "
            "choice list: adding a topic must not require a migration "
            "(build_principles.md §I)."
        ),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AWAITING,
        help_text="Only a person moves this. The public board reads APPROVED only.",
    )
    ask_count = models.PositiveIntegerField(
        default=1,
        help_text="How many times this question has been asked. Incremented, never recomputed.",
    )
    #: `auto_now` is deliberately not used: it would bump on an approval edit and report a
    #: false "last asked" date. Written explicitly by the service (`testing_hazards.md` §1.x
    #: family — a field that changes when something unrelated is saved).
    first_asked_at = models.DateTimeField(auto_now_add=True)
    last_asked_at = models.DateTimeField(db_index=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_questions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    checked_at = models.DateField(
        null=True,
        blank=True,
        help_text="When a person last verified the answer against the documents (D66).",
    )
    escalated_query = models.ForeignKey(
        EscalatedQuery,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="published_questions",
        help_text="Set on a Waiting card: the gap this question exposed.",
    )

    objects = PublicQuestionQuerySet.as_manager()

    class Meta:
        ordering = ["-last_asked_at", "-id"]
        indexes = [
            models.Index(fields=["status", "-last_asked_at"], name="ask_card_status_recent"),
            models.Index(fields=["topic"], name="ask_card_topic"),
        ]
        verbose_name = "public question"
        verbose_name_plural = "public questions"

    def __str__(self) -> str:  # pragma: no cover - admin convenience
        return f"{self.question[:56]} ({self.status})"

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.APPROVED

    @property
    def noindex(self) -> bool:
        """True unless the page is a published answer.

        A gap page stays reachable — it is where a Waiting card points — but it must not be
        indexed: a search result for a question we cannot answer is a promise we break.
        """
        return self.status != self.Status.APPROVED

    @property
    def covers_items(self) -> list[str]:
        """`covers` as the list the page renders. A template never splits a string."""
        return [line.strip() for line in (self.covers or "").splitlines() if line.strip()]
```

- [ ] **Step 3: Migrate**

Run: `python manage.py makemigrations core --name publicquestion`
Expected: `0007_publicquestion.py`, additive only (one new table, two new indexes).
Run: `python manage.py migrate`

- [ ] **Step 4: Register in the admin, minimally, so the fixture can be approved by hand**

```python
@admin.register(PublicQuestion)
class PublicQuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "status", "topic", "ask_count", "checked_at", "approved_at")
    list_filter = ("status", "topic")
    search_fields = ("question", "answer")
    readonly_fields = ("approved_by", "approved_at", "ask_count", "first_asked_at", "last_asked_at")
    actions = ("publish_cards", "reject_cards")

    @admin.action(description="Publish the selected cards (approved)")
    def publish_cards(self, request, queryset):
        for card in queryset:
            approve(card.pk, user=request.user)

    @admin.action(description="Do not publish the selected cards")
    def reject_cards(self, request, queryset):
        for card in queryset:
            reject(card.pk, user=request.user)
```

- [ ] **Step 5: Run and commit**

Run: `python -m pytest core/tests/test_ask_board.py -q`
Expected: PASS (1 test).

```bash
git add -A
git commit -m "feat(ask): a public question is a table with a publish flag, not a cache entry"
```

---

## Task C2 — The consent control, and the four states it must keep

**Files:**
- Create: `core/services/_ask.py`
- Modify: `core/forms/_chatbot.py`, `core/views/_chatbot.py`, `core/templates/chatbot/panel.html`
- Test: `core/tests/test_ask_board.py` (add four)

The prototype pinned this contract (`d61a_ask_board_refinement.html`, *What the checkbox does*).
It is the whole of the consent story, so it is tested as four states rather than one happy path.

- [ ] **Step 1: Write the four failing tests**

```python
def test_a_consenting_grounded_question_waits_for_a_person(client, grounded_answer):
    """The label promises an administrator reads it, so the code has to keep that promise.

    `AWAITING`, never `APPROVED`: a card that is live before review makes the consent label
    a lie, and no template can repair that.
    """
    post_question(client, "Can I use cardboard from my neighbour?", publish=True)
    card = PublicQuestion.objects.get()
    assert card.status == PublicQuestion.Status.AWAITING
    assert card.citations, "the card must carry the clauses it was approved on"
    assert card.slug is None


def test_a_consenting_refusal_becomes_a_waiting_card(client, refused_answer):
    """A refusal is a *state*, never an error (SPEC §13) — and on the board it is the most
    valuable row there is: the visible list of what the documents do not settle."""
    post_question(client, "Do I need EU certification to export to Germany?", publish=True)
    card = PublicQuestion.objects.get()
    assert card.status == PublicQuestion.Status.WAITING
    assert card.escalated_query_id, "a Waiting card must point at the escalation it records"


def test_an_unticked_box_publishes_nothing(client, grounded_answer):
    post_question(client, "Can I use cardboard from my neighbour?", publish=False)
    assert PublicQuestion.objects.count() == 0


def test_the_same_question_twice_is_one_card_asked_twice(client, grounded_answer):
    """Dedupe on the *visitor's* wording, not the published wording.

    An administrator may redact a question before approving it; a second visitor asking the
    same thing must still find that card rather than queue a second, and a redaction must
    not orphan the count.
    """
    post_question(client, "Can I use cardboard?", publish=True)
    post_question(client, "can i use   CARDBOARD?", publish=True)
    assert PublicQuestion.objects.count() == 1
    assert PublicQuestion.objects.get().ask_count == 2
```

- [ ] **Step 2: Add the form field**

```python
    publish = forms.BooleanField(
        required=False,
        label="Add this question to the public questions database",
        help_text=(
            "Other visitors will see the question and the answer, without your name. "
            "Don't include anyone else's name or farm. An administrator reads it before "
            "it appears."
        ),
    )
```

The help text is the console's promise, copied from the prototype: **it is the reason
`AWAITING` exists**, so it ships with the control rather than in a separate copy edit.

- [ ] **Step 3: Write `core/services/_ask.py`**

```python
"""The ask board — the questions a person allowed us to publish (D62, D64–D66).

`_chatbot.py` owns answering; this module owns *keeping*. The split is the one the PRD
states as a requirement: **the cache is not the archive.** A cache entry is keyed on a
normalised question and dies in an hour; a card is asked many times, checked on a date and
approved by a named person.

**Nothing here publishes anything.** `record_public_question` writes an `AWAITING` (or, for a
refusal, a `WAITING`) row, and `approve` is reachable only from the admin. That asymmetry is
the consent label's whole meaning: the control says *an administrator reads it before it
appears*, so the code path a visitor can reach must never set `APPROVED`.
"""

from __future__ import annotations

import hashlib

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core.models import EscalatedQuery, PublicQuestion
from core.services._chatbot import REFUSAL, GroundedAnswer, citation_records, normalise_question

#: How many cards one answer page offers as "questions next to this one".
NEIGHBOURS = 3


def _asked_key(question: str) -> str:
    """The dedupe key: the visitor's wording, normalised. Case and spacing only."""
    return hashlib.sha256(normalise_question(question).encode("utf-8")).hexdigest()


@transaction.atomic
def record_public_question(*, question: str, answer: GroundedAnswer) -> PublicQuestion | None:
    """Keep a question the visitor consented to publish, without publishing it.

    In:  `question` — as the visitor typed it; `answer` — the `GroundedAnswer` the chat
         service just produced (its text, citations, refusal flag and escalation id).
    Out: the card, or None when nothing was recorded (an empty question).
    Side effects: creates or updates one `PublicQuestion` row.
    Fails: never deliberately — a board failure must not break a visitor's answer.
    Idempotency: on the normalised question. A repeat increments `ask_count`; it does not
        queue a second card, and it never re-publishes one an administrator rejected.

    The four states, and why each is what it is:

    * grounded + consent → `AWAITING`. A person must read it (D64).
    * refusal + consent  → `WAITING`, pointing at its `EscalatedQuery`. The gap becomes
      visible and counted instead of disappearing with the session.
    * already on the board → `ask_count += 1`, `last_asked_at` moves. A `REJECTED` card is
      not resurrected: the decision was a person's, and the count is how the next reviewer
      sees the demand behind it.
    * a `WAITING` card asked again, now answerable → the answer is stored and the card goes
      back to `AWAITING`. The corpus changed; a person still decides whether to publish.
    """
    key = _asked_key(question)
    refused = answer.insufficient_context or not answer.citations
    card = (
        PublicQuestion.objects.select_for_update()
        .filter(asked_key=key)
        .exclude(status=PublicQuestion.Status.REJECTED)
        .first()
    )
    if card is not None:
        card.ask_count += 1
        card.last_asked_at = timezone.now()
        fields = ["ask_count", "last_asked_at"]
        if refused and card.status == PublicQuestion.Status.AWAITING:
            card.status = PublicQuestion.Status.WAITING
            fields.append("status")
        if not refused and card.status == PublicQuestion.Status.WAITING:
            card.answer = answer.text
            card.citations = citation_records(answer.citations)
            card.status = PublicQuestion.Status.AWAITING
            fields += ["answer", "citations", "status"]
        if answer.escalated_query_id and card.escalated_query_id is None:
            card.escalated_query = EscalatedQuery.objects.get(pk=answer.escalated_query_id)
            fields.append("escalated_query")
        card.save(update_fields=fields)
        return card

    rejected = PublicQuestion.objects.filter(asked_key=key).first()
    if rejected is not None:
        # The demand is still evidence, and it is the only thing that changes: the card
        # stays unpublished and the count keeps the decision honest.
        rejected.ask_count += 1
        rejected.last_asked_at = timezone.now()
        rejected.save(update_fields=["ask_count", "last_asked_at"])
        return rejected

    return PublicQuestion.objects.create(
        asked_key=key,
        question=" ".join(question.split()),
        answer="" if refused else answer.text,
        citations=[] if refused else citation_records(answer.citations),
        status=PublicQuestion.Status.WAITING if refused else PublicQuestion.Status.AWAITING,
        last_asked_at=timezone.now(),
        escalated_query_id=answer.escalated_query_id,
    )

def _slug_for(question: str) -> str:
    """A public address from the published wording, suffixed rather than reused."""
    base = slugify(question)[:100].strip("-") or "question"
    candidate, n = base, 2
    while PublicQuestion.objects.filter(slug=candidate).exists():
        candidate, n = f"{base}-{n}", n + 1
    return candidate


@transaction.atomic
def approve(
    card_id: int,
    *,
    user,
    question: str | None = None,
    topic: str | None = None,
    covers: str | None = None,
    answer: str | None = None,
) -> PublicQuestion:
    """Publish a card. The only path to `APPROVED`, and it requires a person (`user`).

    In:  the card id; the administrator; optionally the edited wording, topic, *what this
         does not cover*, and answer text.
    Out: the updated card, now with a slug and a `checked_at` date.
    Side effects: one row.
    Fails: `PublicQuestion.DoesNotExist` for an unknown id.
    Idempotency: yes — re-approving regenerates nothing and merely bumps `checked_at`
        (D66: re-checking a card is an explicit act with a date on it).
    """
    card = PublicQuestion.objects.select_for_update().get(pk=card_id)
    for field, value in (
        ("question", question),
        ("topic", topic),
        ("covers", covers),
        ("answer", answer),
    ):
        if value is not None:
            setattr(card, field, value)
    if not card.slug:
        card.slug = _slug_for(card.question)
    # Publishing is one act; *answering* is a different one.
    card.status = (
        PublicQuestion.Status.APPROVED if card.answer.strip() else PublicQuestion.Status.WAITING
    )
    card.approved_by = user
    card.approved_at = card.approved_at or timezone.now()
    card.checked_at = timezone.localdate()
    card.save()
    return card


@transaction.atomic
def reject(card_id: int, *, user) -> PublicQuestion:
    """Stop publishing a card. Hidden, never deleted — the decision stays answerable."""
    card = PublicQuestion.objects.select_for_update().get(pk=card_id)
    card.status = PublicQuestion.Status.REJECTED
    card.save(update_fields=["status"])
    return card
```

- [ ] **Step 4: Export one citation snapshot builder from `_chatbot.py`**

Rename the accepted-list builder so the board reuses it — one shape for a citation snapshot,
whichever surface stores it:

```python
def citation_records(citations: Sequence[Citation]) -> list[dict]:
    """The accepted citations as `_citation_record` stores them: one shape, two callers.

    The board stores the same dicts the transcript does, so a card's clause block and a
    turn's evidence trail cannot disagree about what was cited.
    """
```

- [ ] **Step 5: One line in the view**

In `core/views/_chatbot.py`, inside the successful POST branch, after `answer = answer_question(...)`:

```python
                if form.cleaned_data.get("publish"):
                    record_public_question(
                        question=form.cleaned_data["question"], answer=answer
                    )
```

The service never raises deliberately, and it runs *after* the visitor's answer is committed:
a board failure surfaces as a 500 on a page that already answered. Accept that coupling — a
swallowed board write is a card nobody sees, and `build_principles.md` §VII.5 says fail loudly.

- [ ] **Step 6: The control in `panel.html`**

Between the textarea and the send button (a checkbox after the button reads as an afterthought,
and the help text is two sentences):

```html
          <div class="chat-form__consent">
            {{ form.publish }}
            <label for="{{ form.publish.id_for_label }}">{{ form.publish.label }}</label>
            <p class="chat-form__consent-note">{{ form.publish.help_text }}</p>
          </div>
```

- [ ] **Step 7: Run**

Run: `python -m pytest core/tests/test_ask_board.py -q`
Expected: PASS (5 tests).

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(ask): consent is opt-in, the card waits for a person, and a refusal stays visible"
```

---

## Task C3 — The board below the composer

**Files:**
- Modify: `core/services/_ask.py` (`board_context`)
- Create: `core/templates/chatbot/_board.html`
- Modify: `core/templates/chatbot/panel.html`, `core/views/_chatbot.py`
- Modify: `core/static/css/chat.css`
- Test: `core/tests/test_ask_board.py` (add)

- [ ] **Step 1: Write the failing tests**

```python
def test_the_board_shows_approved_cards_and_no_others(client, cards):
    """`cards` creates one card per status. Only APPROVED may reach the board.

    Parametrised over statuses rather than asserting on one fixture: a board that filtered
    on `status__in=[APPROVED, AWAITING]` would still pass a test written against one
    approved card.
    """
    body = client.get("/ask/").content.decode()
    assert "Do I need to know where my horse manure comes from?" in body
    for hidden in ("Awaiting question", "Rejected question"):
        assert hidden not in body
    assert "Waiting question" in body  # a gap stays visible — that is the point of the shape


def test_the_composer_comes_first(client, cards):
    """D62: the page is called *ask*, so the box precedes the library (DESIGN §7.9 aside)."""
    body = client.get("/ask/").content.decode()
    assert body.index('id="id_question"') < body.index("Questions we have answered")


def test_the_filter_is_a_url_parameter_and_the_board_says_so(client, cards):
    """`build_principles.md` §IV — context preservation: a filter is state in the URL."""
    body = client.get("/ask/?topic=Animals").content.decode()
    assert "Money question" not in body
    assert "Do I need to know where my horse manure comes from?" in body
```

- [ ] **Step 2: `board_context`**

```python
def board_context(topic: str = "") -> dict:
    """In: an optional topic. Out: the board's context. Two queries.

    Only `APPROVED` cards are cards; the others are counted so the page can say how many
    questions are waiting on a person, which is the number that makes the Waiting state
    credible rather than decorative.
    """
    published = PublicQuestion.objects.published()
    if topic:
        published = published.filter(topic=topic)
    return {
        "cards": list(published.select_related("approved_by")[:24]),
        "topics": list(
            PublicQuestion.objects.published()
            .exclude(topic="")
            .order_by("topic")
            .values_list("topic", flat=True)
            .distinct()
        ),
        "topic": topic,
        "card_count": PublicQuestion.objects.published().count(),
        "waiting_count": PublicQuestion.objects.filter(
            status=PublicQuestion.Status.WAITING
        ).count(),
    }
```

- [ ] **Step 3: The fragment**

`core/templates/chatbot/_board.html` — a light band under the dark ask section: heading
*Questions we have answered* with the count and the `Waiting` count, the filter chips as links
(`?topic=…`), then one `card` per row with its question as the link text (`{% url
'core:ask_answer' slug=card.slug %}`), the answer's first sentence as the summary, its topic
chip, `asked {{ card.ask_count }} times`, `checked {{ card.checked_at }}`, and — for a Waiting
card — the escalation line instead of an answer. Empty state: *No questions have been published
yet.* Then the mandatory line from SPEC/OPP: **Membership is not certification.**

Keep the copy in the template to a minimum and the numbers in the service; there is no logic
here beyond `{% if %}`.

- [ ] **Step 4: Wire it into `/ask/`**

`panel.html` gains, after the dark `section--ask`:

```html
  <section class="section section--board" id="questions">
    {% include "chatbot/_board.html" %}
  </section>
```

`core/views/_chatbot.py` adds one context key:

```python
        "board": board_context(request.GET.get("topic", "")),
```

- [ ] **Step 5: CSS**

Add to `chat.css`: `.board`, `.board__head`, `.board__filters`, `.chip`, `.chip--active`,
`.card`, `.card__question`, `.card__summary`, `.card__meta`, `.card--waiting` (warm tint, never
red — DESIGN §7.9 applies to cards as well as bubbles), `.board__empty`. `site.css` does not
grow: it is 21.9 KB of a 30 KB cap, and this is chat's surface.

- [ ] **Step 6: Run**

Run: `python -m pytest core/tests/test_ask_board.py core/tests/test_chatbot_surface.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(ask): the board sits below the composer, and a Waiting card keeps the gap visible"
```

---

## Task C4 — Only a person publishes

**Files:**
- Test: `core/tests/test_ask_board.py` (add)

- [ ] **Step 1: Write the failing tests**

```python
def test_approval_generates_the_slug_from_the_edited_question(card, administrator):
    """The slug follows the *published* wording — that is what redaction is for.

    A slug generated at ask time would carry the third party's name into a public URL even
    after the administrator removed it from the text (D64).
    """
    approved = approve(
        card.pk,
        user=administrator,
        question="Can I use a neighbour's cardboard?",
        topic="Inputs",
        covers="Whether your supply is contaminated.",
    )
    assert approved.slug == "can-i-use-a-neighbours-cardboard"
    assert approved.status == PublicQuestion.Status.APPROVED
    assert approved.checked_at == timezone.localdate()


def test_re_approval_bumps_the_checked_date_and_changes_nothing_else(card, administrator):
    """D66: a re-check is an act with a date on it, and the URL does not move."""
    first = approve(card.pk, user=administrator, topic="Inputs")
    slug, approved_at = first.slug, first.approved_at
    PublicQuestion.objects.update(checked_at=date(2020, 1, 1))
    again = approve(card.pk, user=administrator)
    assert again.slug == slug, "a permalink that moves is not a permalink"
    assert again.approved_at == approved_at
    assert again.checked_at == timezone.localdate()


def test_a_rejected_card_is_hidden_and_keeps_the_demand(client, card, administrator):
    reject(card.pk, user=administrator)
    assert client.get("/ask/").content.decode().count(card.question) == 0
    post_question(client, card.question, publish=True)
    card.refresh_from_db()
    assert card.status == PublicQuestion.Status.REJECTED
    assert card.ask_count == 2, "the demand behind a rejection is evidence too"


def test_no_visitor_reachable_route_sets_approved(client, grounded_answer):
    """The consent label's promise, asserted structurally.

    Every POST a visitor can reach goes through `record_public_question`, so the assertion
    is that after *any* successful ask — consenting or not — nothing is `APPROVED`.
    """
    post_question(client, "Can I use cardboard from my neighbour?", publish=True)
    post_question(client, "What does the standard say about manure?", publish=True)
    assert not PublicQuestion.objects.published().exists()
```

- [ ] **Step 2: Run**

Run: `python -m pytest core/tests/test_ask_board.py -q`
Expected: PASS (9 tests). The `administrator` fixture is a `create_user` with the PGS
administrator role, taken from `core/tests/factories.py` rather than hand-built.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "test(ask): only a person publishes, and redaction decides the slug"
```

---

## Task D1 — `/ask/<slug>/`: the answer as a page

**Files:**
- Modify: `core/services/_ask.py` (`AnswerPage`, `answer_page`)
- Modify: `core/urls.py`, `core/views/_chatbot.py`
- Create: `core/templates/chatbot/answer_page.html`
- Modify: `core/static/css/chat.css`
- Test: `core/tests/test_ask_answer_page.py`

- [ ] **Step 1: Write the failing tests**

```python
"""The answer page — one question, one URL, and the boundary stated on it."""

import pytest
from django.urls import reverse

from core.models import PublicQuestion

pytestmark = pytest.mark.django_db


def test_an_approved_card_has_a_page_with_its_clauses(client, published_card):
    response = client.get(reverse("core:ask_answer", kwargs={"slug": published_card.slug}))
    assert response.status_code == 200
    body = response.content.decode()
    assert published_card.question in body
    assert "Read it in" in body  # the clause link, from B3
    assert "does not cover" in body.lower()


def test_an_unapproved_card_has_no_page(client, card):
    """`AWAITING` is not a page with a notice; it is not a page.

    A 200 would put unread visitor text at a public URL the moment someone guessed the slug,
    and the consent label says an administrator reads it first.
    """
    assert client.get(f"/ask/{card.question[:20]}/").status_code == 404
    card.slug = "an-unapproved-question"
    card.save(update_fields=["slug"])
    assert client.get("/ask/an-unapproved-question/").status_code == 404


def test_a_waiting_card_has_a_page_that_is_not_indexed(client, waiting_card):
    """A gap page is reachable — it is where the Waiting card points — and `noindex`.

    A search result for a question we cannot answer is a promise we break; a 404 at the end
    of a visible card is a dead end we created.
    """
    body = client.get(reverse("core:ask_answer", kwargs={"slug": waiting_card.slug})).content.decode()
    assert 'name="robots" content="noindex' in body
    assert "administrator" in body.lower()


def test_the_page_carries_membership_is_not_certification(client, published_card):
    """OPP requirement, asserted here as well as on the board: the page lists answers."""
    body = client.get(reverse("core:ask_answer", kwargs={"slug": published_card.slug})).content.decode()
    assert "Membership is not certification" in body
```

- [ ] **Step 2: The service**

```python
@dataclass(frozen=True)
class AnswerPage:
    """One card as a page. `gap` is true for a Waiting card, which renders boundary copy."""

    card: PublicQuestion
    citations: tuple[dict, ...]
    neighbours: tuple[PublicQuestion, ...]
    cite_text: str
    gap: bool


def _cite_text(card: PublicQuestion) -> str:
    """The citation as it should read pasted into a message or a FORM.

    Built from the stored snapshot, not from the corpus: the page must still be able to say
    what it claimed after a re-ingest, and a citation that silently re-resolves is a citation
    nobody can audit.
    """
    parts = []
    for citation in card.citations:
        locator = citation.get("sub_ref") or citation.get("section_ref") or ""
        page = f" (p.{citation['page']})" if citation.get("page") else ""
        parts.append(
            f"{citation.get('document', '')}, {locator}{page}: "
            f"\u201c{citation.get('quote', '')}\u201d"
        )
    return "\n".join(parts)


def answer_page(slug: str) -> AnswerPage | None:
    """In: a slug. Out: the page, or None when there is nothing to show.

    In:  `slug` — the public address generated at approval.
    Out: an `AnswerPage` for an `APPROVED` card, a `gap=True` page for a `WAITING` one, and
        **None** for `AWAITING`/`REJECTED`/unknown — the caller 404s.
    Side effects: at most two queries.
    Fails: never deliberately.
    """
    card = (
        PublicQuestion.objects.select_related("escalated_query")
        .filter(
            slug=slug,
            status__in=[PublicQuestion.Status.APPROVED, PublicQuestion.Status.WAITING],
        )
        .first()
    )
    if card is None:
        return None
    others = PublicQuestion.objects.published().exclude(pk=card.pk)
    neighbours = list(
        (others.filter(topic=card.topic) if card.topic else others)[:NEIGHBOURS]
    )
    return AnswerPage(
        card=card,
        citations=tuple(card.citations),
        neighbours=tuple(neighbours),
        cite_text=_cite_text(card),
        gap=card.status == PublicQuestion.Status.WAITING,
    )
```

- [ ] **Step 3: Route and view**

```python
    # One question, one URL (D62/C). After `/ask/` so the composer is never shadowed, and
    # `<slug:…>` never matches the empty string.
    path("ask/<slug:slug>/", ask_answer, name="ask_answer"),
```

```python
def ask_answer(request, slug: str):
    """One published card as a page. Unknown, awaiting and rejected are the same 404."""
    page = answer_page(slug)
    if page is None:
        raise Http404("No such answer")
    return render(
        request,
        "chatbot/answer_page.html",
        chrome_context(
            Page(
                key="ask-answer",
                title=f"{page.card.question} — Outeniqua PGS",
                description=page.cite_text[:200],
                eyebrow="Questions we have answered",
                heading=page.card.question,
                lede="",
            )
        )
        | {"answer": page, "refusal": REFUSAL},
    )
```

- [ ] **Step 4: The template**

Sections in order, each an `h2` (the card's question is the `h1`, so the page marks up correctly
and is quotable): the answer prose → **The clause it comes from** (each citation: quote, document
· section · printed page, *Read it in …* link from B3) → **What this answer does not cover**
(`{% for item in answer.card.covers_items %}`) → **Questions next to this one** → **Cite this
answer** (`<p class="cite-copy__text">{{ answer.cite_text }}</p>` plus a copy button) →
the checked line, `Read from the documents. This page explains what the documents say. It is not
a certification decision.` → **Membership is not certification.**

`{% block head_extra %}{% if answer.card.noindex %}<meta name="robots" content="noindex,
follow">{% endif %}{% endblock %}` — and `follow` rather than `nofollow`: a gap page's links
(contact, the neighbouring answers) are the useful part.

- [ ] **Step 5: Run**

Run: `python -m pytest core/tests/test_ask_answer_page.py -q`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(ask): a permalink per answer — the clause, the boundary, and a citation you can copy"
```

---

## Task D2 — The copy button, and the empty board's honesty

**Files:**
- Modify: `core/static/js/chat.js`, `core/templates/chatbot/_board.html`,
  `core/templates/chatbot/answer_page.html`
- Test: `core/tests/test_ask_answer_page.py` (add)

- [ ] **Step 1: Write the failing test**

```python
def test_the_citation_block_is_selectable_without_javascript(client, published_card):
    """Progressive enhancement, asserted as *content*.

    The copy button is a convenience; the citation text is the feature. A page that put the
    citation only in a `data-` attribute or a JS template would be uncopyable on a phone with
    JavaScript disabled, which is a shape farms actually use.
    """
    body = client.get(reverse("core:ask_answer", kwargs={"slug": published_card.slug})).content.decode()
    assert published_card.citations[0]["quote"] in body
    assert 'data-copy' in body
```

- [ ] **Step 2: The button and its handler**

```html
<button class="btn btn--forest btn--compact" type="button"
        data-copy-target="#cite-text">Copy citation</button>
```

In `chat.js`, one delegated listener: on click, copy the target's `textContent` with
`navigator.clipboard.writeText`, and on success set the button's text to `Copied` for 2 s. When
`navigator.clipboard` is absent, do nothing at all — do **not** fall back to an alert or a
`document.execCommand` shim: the text is already selectable, and a broken button is worse than
no button.

- [ ] **Step 3: Run**

Run: `python -m pytest core/tests/test_ask_answer_page.py -q`
Expected: PASS (5 tests).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(ask): copy the citation, and degrade to selecting it"
```

---

## Task E1 — The gate

- [ ] **Step 1: Run the full gate**

Run: `bash scripts/verify.sh`
Expected: green. Check the count rose from 845 and that `lint-imports` still reports **1 contract,
0 broken** — `knowledge/reading.py` must not have introduced a `core` import.

- [ ] **Step 2: Run the browser suite**

Run: `python -m pytest tests/e2e -q`
Expected: green. Add `/documents/saoso-standard-v2.1/read/` to the e2e route list **only** if it
is reachable without a seeded corpus; otherwise assert the reader's contract in `core/tests` and
leave the e2e list alone (a route added to a sweep that 404s in CI is a test that always skips).

- [ ] **Step 3: Check the reader's weight, measured rather than assumed**

Run: `python - <<'EOF'` against the dev database for the SAOSO document, printing the byte size
of the rendered page and the query count with `assertNumQueries`.
Expected: under ~1.5 MB and ≤ 3 queries. **If it exceeds that**, split the reader by chapter
(one route segment per top-level reference) rather than shipping a page a farm connection cannot
load — and record the measurement in the PRD §4 as the reason.

---

## Task E2 — Close the loop

- [ ] **Step 1: Record the decisions**

Add D64–D66 to `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` §18.3, in the existing row
format, with the product owner's confirmations (or the defaults from §0.1 of this plan if they
were not given — stated as defaults, never as decisions).

- [ ] **Step 2: Update the PRD**

`ASK_SURFACE_PRD.md`: §4 items 1–4 become *built*, with the tests named; §6 questions get their
answers or their remaining owner; §7 DoD gets its checkboxes ticked except the UAT line.

- [ ] **Step 3: Present the UAT**

`tests/uat/ask_surface_uat.md` → the judgement surface (`pgs-presenting-uat`). The board, the
answer page and the reader are all visual surfaces a human must judge; a green suite does not
close them.

- [ ] **Step 4: Ballot for the backlog**

Run: `python product/backlog.py` — dry run first, then `--apply` once the moves are the ones you
mean. `_ask.py` is new, so check `HANDOVER.md`'s file map too.
