# Evidence

Machine output that a claim depends on, kept as a file so the claim stays checkable after the
session that made it.

**What belongs here.** The output of a measurement whose numbers appear in a PRD, a spec row or a
handover line: a JSON result, a dump, a score table. Small, diffable, and regenerable by a command
the file or the PRD names.

**What does not.** Page fixtures (those live in `knowledge/tests/fixtures/`, pinned by sha256 in a
manifest), design artifacts and decision pages (`product/design/`), and anything a test could assert
(a test is better than a file).

| File | What it is | Regenerate with |
|---|---|---|
| `2026-11-03_s2_docling_scores.json` | Docling 2.146.0 scored against the eight shapes from `knowledge/tests/shape_fixtures.py`; the source of `INGESTION_ENGINE_PRD.md` §3.5 | `python scripts/eval_extractors.py --json <path>` in a venv that has `docling` |
