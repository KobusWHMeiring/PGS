# Session 0z — 2026-11-03 — the landscape is signed, and "As above" is the paper's word

**Task:** sign the landscape tables UAT, which the handover named as the only thing keeping
`LANDSCAPE_TABLES_PRD` out of `Done/`.

**Outcome:** signed. **6 PASS · 0 FAIL · 0 N/A**, Kobus (Product), applied by
`scripts/uat_signoff.py`; `LANDSCAPE_TABLES_PRD` moved to `Done/` with `TABLE_BANDS` and the
corpus-level table-page guard named and carried into D80. One finding, recorded rather than fixed.

---

## 1. Presenting it

Followed `pgs-presenting-uat`: prepare → present → close.

- **Prepare.** `manage.py uat_seed --check` → `preflight: ready — no blocking failure`:
  corpus 401 chunks, 0 unembedded, 8 documents published, extraction tool Xpdf 4.00. One warning,
  `celery_worker=error` — a dev box often has none, and this slice is the reader, not the chatbot.
- **Present.** `scripts/uat_runner.py --file tests/uat/landscape_tables_uat.md --preflight … --database pgs`
  → `product/design/uat/landscape_tables.html`, rebuilt against `ecd3c8d` (clean), **6 scenarios,
  6 applicable, 0 N/A**. The committed artefact was stale from 2026-11-01 and grew 47,275 → 47,453
  bytes carrying the new commit, so it ships with the sign-off.
- **Close.** `uat_signoff.py` applied the export; a **second run changed nothing** (idempotent,
  checked with `diff -q`). The diff is six `**Result:**` lines, the sign-off table and the
  per-scenario table — nothing else.

Checks from the skill's own list, all green: `grep -c "http://\|https://\|src=\|href="` → **0**;
every `Judgement:` clause present verbatim; `pytest tests/e2e/test_uat_artefact.py` → **6 passed in
17.09 s** (the only check that executes the page's script).

## 2. The finding: a Fee cell that says "As above"

The reviewer reported that the *PGS seals and their use* grid shows a Fee cell reading **"As above"**
with nothing above it. **Checked against the paper before touching anything** — `pdftotext -layout`
of printed p. 6 shows exactly that, for both rows. The referent is the previous table's Step 3 fee
cell in `ESTABLISHING A PGS GROUP`:

> Recommended annual fee for the use of stickers (paid by individual farmers): R350 [to be divided
> between PGS SA (30%) and PGS groups (70%) …]

So the artefact is **faithful**, and it already declares the problem in its own header legend —
*"Both rows' Fee cell reads 'As above', which is the fee stated on the previous table."* — which
renders as `p.reader__grid-legend` immediately above the grid (verified on the running instance,
not inferred from the template).

**What is ours is smaller and real:** on the deep link `?section=pgs-seals-and-their-use` there is
no previous table in view, and "the previous table" names no heading and is not a link. A reader
arriving from a citation or a search hits exactly that case.

The obvious repair — writing `R350` into the cell — is **forbidden twice**: D72.2 (an amount is
never published on its own) and Scenario 6 (the page may not print a word the paper does not print).
Filed as `product/backlog/BugFixes/landscape_fee_as_above_referent.md` with the legend-shaped fix
and a note that it needs **no re-ingest** (the legend is artefact header, not chunk text — though
the artefact hash moves, so `corpus_check` will report landscape drift until a deliberate
`corpus_refresh --apply`).

**The reviewer accepted the page as is.** The defect is the source document's, and it is now carried
by name instead of in chat. I did **not** put a note into their signature: the note field came back
empty and inventing one would have put words in a reviewer's mouth in a signed file.

## 3. A gap in the UAT itself

No scenario asked this question. Scenario 1 is the fee question but scoped to the *establishing*
branch; Scenario 4 is legibility and resizing; Scenario 6 is claims. The seals table's Fee column
fell between all three. Recorded in the bug file, not repaired in a signed file — a signature is
not the place to rewrite the question that was answered.

## 4. Closing the loop

- `LANDSCAPE_TABLES_PRD`: `Status:` line corrected (it still claimed steps 2–6 unbuilt while §12c–§12g
  recorded them built — the stale line was also what `backlog.md` was printing), a §12h record
  added, and `product/backlog.py --apply` moved the file to `Done/` and regenerated the index.
- `tests/uat/landscape_tables_uat.md`: header `Status:` now reads **SIGNED 2026-11-01**, 6 PASS,
  against `ecd3c8d`; the PRD path now points at `Done/`.
- `HANDOVER.md`: state block rewritten, `0z` added to the archive.

**Two things left open, and named:** the signature dates are the reviewer's own export dates
(2026-11-01) while the artefact was rebuilt on 2026-11-03 — raised, and the export applied as
submitted rather than edited. And the live box is still behind: it needs a deploy plus a deliberate
`corpus_refresh --apply` there, not just a pull.
