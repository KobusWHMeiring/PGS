## 0y. 2026-11-02 (session 11) — slice 3: the context is a row *and a column*, and both surfaces say so

**What was asked.** Read `HANDOVER.md` and implement the next slice — which was G11/D79's third
slice, the *"context, not quotation"* distinction as a design pass over the answer and reader
surfaces.

**What the slice had to fix that was not in its own description.** The shipped minimum rendered
`Table row: Below R 250,000` beside the quote — but only in the **transcript**. The answer page
read `citation.row_label` off a stored snapshot that `citation_records` never wrote, so it
silently rendered no context at all. Two surfaces, one citation, disagreeing. Slice 3 therefore
started by making the frame part of the stored record, not by choosing colours.

### The frame is a row **and a column**, both from the reviewed table

`knowledge.table_context.column_label_for` names the printed heading a quoted cell sits under,
from the same `TableContext` the prompt already carries:

- exactly one cell contains the quote → that cell's column (`900` → *Renewal fee (R)*);
- the quote spans cells (D79-2 allows consecutive cells) → the row context stays, **no column**;
- nothing matches → neither.

The asymmetry is deliberate. E's one real risk is a citation that displays text the reader cannot
reconcile with the quote; silence beats a plausible guess, the same rule `align_artefact_grid`
already follows.

`Citation.column_label` carries it, `citation_records` stores `row_label` + `column_label`, and one
partial (`_citation_context.html`) renders `Table row: … · Column: …` on both surfaces.

### The legend, once per answer

`_citation_legend.html` — one sentence, same words on the transcript and the answer page:

> The dashed line is context, not a quotation: it names the table row and column the quoted cell
> sits in, taken from the same printed table. The document does not print those words beside the
> cell. The text under the solid rule is the document's own.

Once per answer, never once per citation: a citation chip is already dense, and the legend exists
to teach the rule, not to be re-read. `GroundedAnswer.has_row_context` and `AnswerPage.has_row_context`
decide when it appears, so the template does no `any()`.

### The reader got its counterpart

`Citation.read_url` now appends `&quote=` when a row frames the citation. The reader resolves it
against the printed grid (`_cited_row`): the row is washed and dashed, the quoted cell carries a
**solid** ochre inset rule, and `reader__grid-cited` above the table names the column. The same
dashed/solid pair as the answer surface, so a visitor who learns it in one place can read the
other. A quote that matches no cell marks nothing; one that spans cells marks the row and no cell.

`ReaderGridRow` gained `is_cited`, `cited_cell` and `cell_texts` — the raw cell text has to be kept
because the grid otherwise only holds laid-out blocks, and a citation's quote needs the cell it came
from, not a rendering of it.

### Design decisions worth remembering

- **The marks are a vocabulary, not decoration.** Dashed + muted = the page is pointing; solid
  ochre = the document's own characters. DESIGN.md §7.9a records it as a rule, so the next surface
  inherits it rather than inventing a third treatment.
- **The answer-page URL moved into the service.** `answer_page.html` assembled `?section=…#…`
  itself — a second copy of `Citation.read_url` and the copy that silently missed `&quote=`.
  `_stored_read_url` builds it once for a snapshot dict; the template renders a string.
- **Old cards are not migrated.** A stored citation with no `row_label` renders no context and no
  legend — the same page it always had. The snapshot is a record of what was shown, not a projection
  of today's data model.

### Guards, each proved by breaking it

| Guard | Broken by | Went red |
|---|---|---|
| `test_the_quoted_cell_names_its_printed_column` | `column_label_for` returns `""` | yes |
| `test_the_thread_renders_the_row_and_column_as_context` | `read_url` drops `&quote=` | yes |
| `test_the_reader_link_carries_the_quote_only_when_a_row_frames_it` | same break | yes |
| `test_a_rows_context_and_the_legend_are_rendered_on_the_answer_page` | legend include removed | yes |
| `test_a_cited_quote_marks_its_row_its_cell_and_names_the_column` | `_cited_row` returns `None` | yes |

Ten new tests in all (knowledge 2, grounding 4, answer page 2, reader 3, chat surface 2 — two
existing fixtures were extended rather than duplicated).

### What is left

- **The judgement is still a human's.** UAT Scenario 8 (`tests/uat/ask_surface_uat.md`) has been
  updated to the shipped wording and now also checks the reader mark. D79's fallback to option A
  stays on record until someone signs it. **This is the only thing between slice 3 and "done".**
- **Context cuts 4.2/4.3** — `_chatbot.py` is 99 KB and `_documents.py` 48 KB, both far over §II's
  cap; both grew again here. 4.2 (`--check`'s 14 over-budget spec rows) is untouched.
- **G12/X2** — the eight-shape fixture set is D80's first commit.
- The landscape UAT sign-off is still the only thing keeping `LANDSCAPE_TABLES_PRD` out of `Done/`.

### Gate

`scripts/verify.sh` **1593 passed, 1 skipped in 59.50 s** (`--create-db`,
`DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify`, warm page cache). `scripts/fast.sh`
**1578 passed, 1 skipped in 42.40 s** warm; `--critical` **217 passed, 4 deselected in 11.28 s**.
No migration, no corpus change: the four artefacts and 401 chunks are untouched.
