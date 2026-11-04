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
| `2026-11-04_s2b_openrouter_scores.json` | Two VLMs (`gemini-3.1-flash-lite`, `claude-sonnet-5.5`) × three prompt forms × the same eight shapes, scored by the same `mismatches()`; the source of §3.7. 189 KB because it keeps four sampled rows per shape per cell; cells are clipped at 200 characters | `python scripts/eval_openrouter.py --json <path>` with `OPENROUTER_API_KEY` in the shell and `pypdfium2` in a throwaway venv. Raw provider responses are cached per (model, shape, dpi, form), so a re-score inside one working tree needs no network call; a fresh clone re-runs the 48 calls for about $0.55 |
