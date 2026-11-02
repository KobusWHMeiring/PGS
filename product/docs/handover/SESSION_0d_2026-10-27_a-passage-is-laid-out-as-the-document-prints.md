<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0d. 2026-10-27 — a passage is laid out as the document prints it

The reader now renders each passage as blocks: paragraphs with their hard wraps joined, the
printed headings, **real lists** — `a.`–`f.` for SAOSO's conditions, with the roman sub-list nested
inside its item (`S8.1`) — and **glossary terms** (`ACB`, `Habitat`, `Extensive Farming`) above
their definitions. `S1`'s eight chunks overlap by 21–57 words on purpose (retrieval); the reader now
trims that overlap for display, so the definitions page no longer prints the previous chunk's last
paragraph again. The marker is a CSS list marker, never text: the corpus prints a bare `a`, and
`flatten(blocks)` reproduces every chunk of the shipped SAOSO exactly (a guard in
`knowledge/tests/test_passages.py`). Stored text, retrieval, anchors and the citation audit are
untouched — this is display-only (`PASSAGE_LAYOUT_PRD.md`). The concordance's own spacing was
refined in the same pass: a 72 rem working column, a 38 rem reading measure (~85 characters), one
hairline per printed clause, sticky search and tree. **UAT Scenario 8 is unsigned.**

---
