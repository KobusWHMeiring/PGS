<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0q. 2026-10-30 (session 4) — step 5: the front matter, and four probes that were zero

**State: green, committed, and the dev box's landscape is current at 17 chunks.** `fast.sh` **1419
passed / 1 skipped in 38.6 s** (warm) and `verify.sh` **1433 passed / 1 skipped in 53.3 s**
(`--create-db`, 5433). Code at `8674d7a`; this documentation commit follows. The live box is still
`8d2839d` (see the top).

### 0q.1 The four zeros, and what each resolves to now

§1.4 measured four probes at **0 chunks** because the PDF parser opens no section on pages 2–3.
They are now one chunk each, asserted in `test_corpus_landscape.py`:

| Probe | Chunk |
|---|---|
| `Participatory Guarantee Systems` | `## INTRODUCTION` (p2) |
| `six basic elements` | `## SIX BASIC ELEMENTS` (p2; the reviewer's heading supplies “six” — the paper prints `6`) |
| `First-Party` | `## First-Party Claim` (p3) |
| `Third-Party` | `## Third-Party Certification` (p3) |

The three route headings are the paper's own Title case — `First-Party Claim`, `Second-Party
Certification`, `Third-Party Certification` — which is exactly why the UPPERCASE-only
`HeadingParser` skipped them. `INTRODUCTION`, `SIX BASIC ELEMENTS` and `COLOPHON` are the
reviewer's; a test asserts those three words are **not** printed on the page. The colophon carries
the funders, the copyright and the disclaimer on p9 (which prints no page number, so D42's `page`
is `None` while the block is on PDF 9).

### 0q.2 The one glyph the no-invention guard caught

The paper's text layer closes `“owned` with a **single** quote (U+2019) on both renderings. The
artefact first typed `”`, and `test_it_invents_no_character` failed on exactly one character. It now
reproduces the page rather than correcting it — whether it is the paper's typo or the extractor's is
a `CORPUS_EDITS` decision, not a silent fix. This is the first thing the no-invention guard has
caught since it was written, and it is the kind of thing a per-line word check cannot see (every
word was right).

### 0q.3 The count, and the second re-ingest

**17 chunks**: 8 rows + 3 table-prose blocks + 6 front-matter sections. Page 1 is a cover whose only
line is the running header, and page 10 is blank; neither contributes a chunk, and `COVERED` says
so. The dev box: **11 → 17 chunks**, all embedded, **0 evidence links dropped**,
`relink_evidence --apply` **0 relinked / 0 no-longer-has**; **394 chunks, 0 unembedded**.

### 0q.4 What the reader (step 6) will need

- The rows are quotable, but the public page still renders the five columns as a definition list.
  §5.4's measurement stands: the printed row is **323 characters** wide against a **38 rem**
  measure, so the fit is a design decision (four options; choose one in a mock in `product/design/`).
- **`TABLE_BANDS`** — the measured column offsets — is still unbuilt. It is what pins a line to the
  column it is filed under, and it belongs with the reader because that is the surface that measures
  the columns.
- The corpus-level table-page guard is still unbuilt; it needs a cross-document definition of
  “table-shaped”.

**Do not run `scripts/build_corpus.py --force --doc landscape`.** The generator has no table-block
rule; the per-line guard fails loudly if it does, but the command has no other defence.

---
