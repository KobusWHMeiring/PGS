# Passage layout — Implementation Plan

**Status:** **In Progress** — all six tasks landed 2026-10-27; UAT Scenario 8 unsigned. Implementation
notes are in §7.
**PRD:** `PASSAGE_LAYOUT_PRD.md`
**Reference:** `build_principles.md` §I, §II, §IV, §VIII · `testing_hazards.md` §1.6, §1.32, §1.33
**Baseline:** `934a2cc` (the sticky tree and search), gate green at 954.

**Goal:** one chunk of extracted text becomes a small block tree — paragraphs, headings and real
`<ol>` lists — without changing a word. The reader renders that tree instead of `linebreaksbr`.

**Architecture:** one pure module (`knowledge/passages.py`, no Django) with `passage_blocks(text)`
and `flatten(blocks)`; `core/services/_documents.py` puts the blocks on `ReaderPassage`; one template
partial renders them recursively; CSS styles the list markers and hanging indents.

---

## File map

| File | Change |
|---|---|
| `knowledge/passages.py` | **new** — blocks, marker parsing, grouping, `flatten()` |
| `knowledge/tests/test_passages.py` | **new** — shape tests + the real-ingest lossless guard |
| `core/services/_documents.py` | **~** `ReaderPassage.blocks` |
| `core/templates/public/_passage_blocks.html` | **new** — recursive block renderer |
| `core/templates/public/document_reader.html` | **~** use the partial; provenance sentence |
| `core/static/css/reader.css` | **~** `.passage__list`, `.passage__item`, `.passage__heading` |
| `core/tests/test_document_reader.py` | **~** the verbatim test becomes a block test; one list renders |
| `tests/uat/concordance_uat.md` | **~** Scenario 8 |

---

### Task 1: The block model and `flatten`

- [ ] **Step 1: failing test** — the API exists and round-trips:

```python
def test_flatten_reproduces_the_block_text():
    blocks = passage_blocks("a  First item;\n\nb  Second item.")
    assert flatten(blocks) == "a First item; b Second item."


def test_flatten_keeps_the_marker_as_printed():
    blocks = passage_blocks("1.  Sign the pledge.")
    assert "1." in flatten(blocks)
```

- [ ] **Step 2:** run — `ModuleNotFoundError`.

- [ ] **Step 3:** create the module with `Paragraph`, `Heading`, `ListBlock`, `ListItem`,
  `passage_blocks()` returning one paragraph (the naive implementation) and `flatten()`.

- [ ] **Step 4:** green; commit `feat(c10): a passage is blocks, not one string`.

### Task 2: Prose — joins and headings

- [ ] **Step 1: failing tests**

```python
def test_hard_wrapped_prose_becomes_one_paragraph():
    text = "The first line ends mid-sentence\n\nand continues here."
    assert passage_blocks(text) == (Paragraph("The first line ends mid-sentence and continues here."),)


def test_a_markdown_heading_from_the_bpp_artefact_is_a_heading_block():
    assert passage_blocks("## INTRODUCTION\nThe PGS operates…") == (
        Heading("INTRODUCTION"),
        Paragraph("The PGS operates…"),
    )


def test_a_numbered_caps_opener_is_a_heading_not_a_one_item_list():
    assert passage_blocks("1. DEFINITIONS") == (Heading("1. DEFINITIONS"),)


def test_a_title_case_numbered_line_is_a_list_item():
    blocks = passage_blocks("1. Ecosystem Management")
    assert blocks[0].kind == "list" and blocks[0].items[0].text == "Ecosystem Management"
```

- [ ] **Step 2:** run, watch them fail.
- [ ] **Step 3:** implement line classification (blank lines are extraction spacing, not meaning),
  heading rules, paragraph accumulation, `## ` removal (recorded in `flatten`'s docstring).
- [ ] **Step 4:** green; commit.

### Task 3: Lists — sequence, family, nesting, continuations

- [ ] **Step 1: failing tests** (each is a real clause shape, paraphrased so the test is readable;
  the real text is pinned in Task 4)

```python
def test_bare_letters_with_unreliable_indents_are_one_list():
    text = "a  First;\n\n      b  Second;\n\nc  Third;"
    block = passage_blocks(text)[0]
    assert [item.marker for item in block.items] == ["a", "b", "c"]
    assert block.style == "lower-alpha"


def test_a_restarted_letter_sequence_is_a_new_list():
    text = "a  One;\nb  Two;\n\nHeading\n\na  Again;"
    kinds = [block.kind for block in passage_blocks(text)]
    assert kinds == ["list", "paragraph", "list"]


def test_a_roman_list_under_a_letter_nests():
    text = "a  Parent:\n   i. First;\n   ii. Second;\nb  Next;"
    outer = passage_blocks(text)[0]
    assert outer.items[0].children[0].style == "lower-roman"
    assert [item.marker for item in outer.items] == ["a", "b"]


def test_a_restarted_decimal_after_a_nested_list_starts_a_new_list():
    text = "1. One;\n2. Two:\n      a. Sub;\n      b. Sub;\n3. Three;"
    blocks = passage_blocks(text)
    assert blocks[0].kind == "list" and blocks[0].items[0].children
    assert [item.marker for item in blocks[0].items] == ["1.", "2."]


def test_a_wrapped_line_at_the_body_column_continues_the_item():
    text = "a  First line\n\n   second line;\nb  Next;"
    item = passage_blocks(text)[0].items[0]
    assert item.text == "First line second line;"


def test_a_centred_heading_ends_the_list():
    text = "a  One;\n\n                    South African specific\n\nAreas are…"
    kinds = [block.kind for block in passage_blocks(text)]
    assert kinds == ["list", "paragraph", "paragraph"]


def test_a_line_starting_with_a_single_space_letter_is_prose():
    assert passage_blocks("a lot of things")[0].kind == "paragraph"
```

- [ ] **Step 2:** run, watch them fail.
- [ ] **Step 3:** implement the marker regex, the level stack, the sequence check, the family/nesting
  rule, the continuation tolerance and the fallbacks. Never raise.
- [ ] **Step 4:** green; commit.

### Task 4: The guard — every real chunk survives

- [ ] **Step 1: failing test** (real ingest through the committed pages, in the gate)

```python
def test_every_ingested_passage_survives_the_layout(standard_set):
    ingest_standard(pdf_path=PDFS["saoso"], standard_set=standard_set, doc_key="saoso", embed=False)
    chunks = DocumentChunk.objects.order_by("id")
    for chunk in chunks:
        source = HASH_HEADING.sub("", chunk.text)          # the one documented normalisation
        assert normalise(flatten(passage_blocks(chunk.text))) == normalise(source), chunk.section_ref


def test_the_measured_shapes_are_actually_lists(standard_set):
    …
    s513 = DocumentChunk.objects.get(section_ref="S5.1.3")
    block = passage_blocks(s513.text)[0]
    assert block.kind == "list" and len(block.items) == 6
    assert "for poultry" in block.items[5].text
```

- [ ] **Step 2:** run. The equality fails for at least one shape; fix the formatter, not the assertion.
- [ ] **Step 3:** also assert a floor (e.g. `> 60` list blocks across the corpus) so a formatter that
  parses nothing cannot pass.
- [ ] **Step 4:** commit.

### Task 5: The reader renders the blocks

- [ ] **Step 1: failing tests**

```python
def test_the_page_renders_a_lettered_list_as_a_list(client, seeded_documents):
    ...  # a chunk whose text is "a  One;\nb  Two;"
    body = client.get(".../?section=…").content.decode()
    assert 'class="passage__list passage__list--lower-alpha"' in body
    assert "<li" in body and "Two;" in body


def test_the_stored_words_are_all_on_the_page(...):
    # a paragraph chunk: the flatten of the rendered blocks equals the stored text
```

- [ ] **Step 2:** add `blocks` to `ReaderPassage`; render via the partial; keep `text` (the offline
  fallback). Rewrite `test_the_text_is_the_stored_text_not_a_reformatting` to the lossless form.
- [ ] **Step 3:** green; commit.

### Task 6: CSS, the provenance sentence, and close-out

- [ ] Style `.passage__list` (hanging indent, marker spacing, nested indent), `.passage__item`,
  `.passage__heading` (weight, not a heading tag). No raw colours; 44 px is not required for
  non-interactive text.
- [ ] Change the provenance line to: the words and punctuation are unchanged; line breaks are
  reflowed for reading.
- [ ] Look at `S5.1.3` at 1280 px and 390 px.
- [ ] Update the PRD status, move PRD + plan to `In Progress/`, add UAT Scenario 8, `HANDOVER.md`,
  `python product/backlog.py --apply`.
- [ ] Gate + Playwright.

---

## What this plan does not do

No stored text changes. No `PROMPT_VERSION` bump (retrieval unchanged). No re-ingest. No new
migration.

---

## 7. Implementation notes

1. **The marker regex needs a weak pass.** SAOSO prints `m Dry stone walls;` with **one** space
   inside a list that otherwise indents by fourteen columns (`S2.1.4`). A bare letter with one space
   is therefore accepted only when it continues an open lettered list; everywhere else `a lot of
   things` stays prose.
2. **Continuation is conditional on the item's own sentence.** `a  ACB` + the definition at column 0
   is one item, but `b  Two;` followed by a new sentence at column 0 is the prose after the list. The
   discriminator is whether the item has already ended its sentence (terminal punctuation). This is
   why `S2.1.4`'s second list is separate from its first.
3. **A BPP numbered heading absorbs the paragraph under it.** `1. Ecosystem Management` has no
   terminal punctuation, so the paragraph that follows stays with the item rather than becoming a
   separate block. No text is lost; the UAT judges whether it reads.
4. **Paragraphs split on a large indent change (≥6 columns).** That is what makes SAOSO's centred
   `South African specific` its own block instead of the tail of the paragraph before it.
5. **The guard is one test, not two.** A module-scoped ingest fixture leaked its rows into later
   tests (183 errors); the lossless check and the "structures are actually found" check share one
   function-scoped ingest.
6. **The desktop `<details>` rule from the concordance still applies**, and the list markers are CSS
   (`list-style-type`), never text: the corpus prints a bare `a`.
