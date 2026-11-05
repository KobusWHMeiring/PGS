# Proposals — the structure a document's tables were read from

One pair of files per document, both keyed by the PDF's **sha256** (which the file records, and the
artefact header records the same digest). A renamed document is a different document, and a reprint
finds no proposal — which is the truthful outcome: nobody has read its tables yet.

| File | Who writes it | What it holds |
|---|---|---|
| `<doc>.structure.json` | `scripts/propose_tables.py`, from a cached extractor response | the arm's grid: columns, rows, the pages, and the banner (`structure`, `processor`, `project`, `captured`, `reduced_from`) |
| `<doc>.reviewed.json` | a person, once per table | the block fields **no extractor produces**: `legend`, `layout`, `titles`, `fee_labels`, `branch` |

**What must never be edited by hand** is `.structure.json`. It is a transcription of what the arm
returned, and hand-editing it would make the one thing in this path that is *not* a guess into one.
If the arm's read is wrong, the cell is wrong in the diff — the emitter verifies every cell against
the page's own text layer and refuses the ones the arm got wrong, naming them.

**What must never be put here** is a typed-out table. The cell characters come from the page
(`scripts/table_blocks.py` slices them out of the artefact's body stream); a cell typed here would be
a quote nobody verified, and the harness would pass it.

`reviewed` entries are matched to tables by **index, in document order**, and a review that names an
index the structure does not have is an error rather than an ignored line.

## Regenerating

```bash
python scripts/propose_tables.py \
    --response _scratch/adc/responses/layout16pro__numeric_row.json \
    --structure documentai-layout-v1.6-pro \
    --processor 68e47c3bc90cc6ab@pretrained-layout-parser-v1.6-pro-2025-12-01 \
    --project 803140233794 --shape numeric_row --doc opp \
    --json knowledge/proposals/opp.structure.json
```

The raw response is cached under `_scratch/` and is **not committed** (it is 8–28 KB per page and
the credential that produced it belongs to the owner, not the repository) — the same rule
`product/docs/evidence/README.md` records for the S2 arms. For a document the shape registry does not
know, pass `--pdf` and `--pages` instead of `--shape`.
