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
| `2026-11-04_s2_docling_gutter_scores.json` | Docling 2.146.0 re-scored with the **declared row-number gutter** as a third reading (Appendix 7 passes: `rows 7/7, cols 5/4`); the source of `INGESTION_ENGINE_PRD.md` §3.8 | `python scripts/eval_extractors.py --json <path>` in the Docling venv |
| `2026-11-04_s2_documentai_scores.json` | Document AI on the owner's project, ADC (no key file): Form Parser v2.1 **1/8**, Layout Parser v1.6-pro **2/8 with 8/8 tables found**; the source of `INGESTION_ENGINE_PRD.md` §3.9. Raw responses cached in `_scratch/adc/responses/` (not committed) so a key fix re-scores for free | `python scripts/eval_documentai.py --processor form=ID@VERSION --project P --location us --json <path>` with ADC and `pypdfium2`+`google-auth` in a throwaway venv |
| `2026-11-04_s2b_openrouter_scores.json` | Two VLMs (`gemini-3.1-flash-lite`, `claude-sonnet-5.5`) × three prompt forms × the same eight shapes, scored by the same `mismatches()`; the source of §3.7. 189 KB because it keeps four sampled rows per shape per cell; cells are clipped at 200 characters | `python scripts/eval_openrouter.py --json <path>` with `OPENROUTER_API_KEY` in the shell and `pypdfium2` in a throwaway venv. Raw provider responses are cached per (model, shape, dpi, form), so a re-score inside one working tree needs no network call; a fresh clone re-runs the 48 calls for about $0.55 |
| `2026-11-05_s2_rescore_docling.json` | Docling 2.146.0 re-scored against the **signed** key after the `long_cell` amendment (§3.12): **identical to the 2026-11-04 gutter run — 0 of 8 shapes changed**, because it returns no table on that page and the amended cell is never consulted | `python scripts/eval_extractors.py --json <path>` in the Docling venv (545 s; this arm has no response cache, so the re-score costs a re-run) |
| `2026-11-05_s2_rescore_documentai.json` | The same two processors and versions re-scored from the cached raw responses against the signed key: Form Parser v2.1 **1/8, unchanged** (its `long_cell` read is the bare label `Step 3`, so the claim fails `contains` instead of `starts`); Layout Parser v1.6-pro **2/8 → 3/8**, because `long_cell` now passes outright. The source of §3.12 | `python scripts/eval_documentai.py --processor form21=3da842fc37f31e08@pretrained-form-parser-v2.1-2023-06-26 --processor layout16pro=68e47c3bc90cc6ab@pretrained-layout-parser-v1.6-pro-2025-12-01 --project 803140233794 --json <path>`; replays from `_scratch/adc/responses/` with no network call and no credential |
| `2026-11-05_s2b_rescore_openrouter.json` | Both VLMs × three prompt forms × eight shapes re-scored from cache against the signed key: **passes unchanged**; `long_cell` moves from a structural fail (1 mismatch) to **0 mismatches with 4–11 cells whose characters our committed pass does not confirm**. The source of §3.12 | `python scripts/eval_openrouter.py --model google/gemini-3.1-flash-lite --model anthropic/claude-sonnet-5.5 --json <path>`; replays from `_scratch/or/responses/` with no key and no network call |
