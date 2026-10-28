# Bug: a wrapped clause renders as two paragraphs, and copies back glued

**Status:** **Open** — found 2026-10-28 by the product owner reading `?section=s23` at
`S23.3 · printed p. 67`, where the clause breaks mid-sentence and the next clause number runs into it.
**Severity:** **readability and copying.** A quoted clause cannot be selected as one sentence, and a
reader who copies it gets `…property or documents.23.5. Operators shall…` — no break, no space.
**Owner:** Build (display rule in `knowledge/passages.py`) · Product (nothing to decide)
**Affected:** **25 of 319** SAOSO chunks, at least; the reader only. Retrieval, anchors, the citation
audit and the stored text are untouched, and the fix needs **no re-ingest**.
**Reference:** `knowledge/passages.py` (`flush_paragraph`, the centred-line rule) ·
`product/backlog/Done/PASSAGE_LAYOUT_PRD.md` §3 ·
`tests/uat/concordance_uat.md` Scenario 8 (the scenario this defect failed in life, not in UAT) ·
`testing_hazards.md` §3.14 (the same rule, the other way round)

---

## 1. What is stored, and what the reader prints

`S23.3` is stored as two lines, because the paper wraps the clause and `pdftotext` keeps the wrap:

```
23.3. Operators shall not use forced or involuntary labour or apply any pressure such as retaining part of the
         workers' wages, property or documents.
```

The first line starts at column 0; the continuation is indented by ~9 columns (the printed hanging
indent). `passage_blocks()` renders that as **two paragraphs**:

| block | text |
|---|---|
| `Paragraph` | `23.3. Operators shall not use forced or involuntary labour or apply any pressure such as retaining part of the` |
| `Paragraph` | `workers' wages, property or documents.` |

Copied from the page, the two paragraphs arrive as `…property or documents.23.5. Operators shall…`
because the next clause is its own `<p>` with no whitespace between the elements.

**Measured 2026-10-28** over the shipped SAOSO: **25 of 319 chunks** render a final paragraph that
begins with a lower-case word — a wrapped continuation that was split off. Samples:

| chunk | split-off fragment |
|---|---|
| `S23.1` | `organic.` |
| `S23.3` | `workers' wages, property or documents.` |
| `S23.4` | `organize and to bargain collectively, free from interference, intimida…` |
| `S1` | `than 25kg weight/m .` (this one is the `m²` split — §2 of the corpus bug, not this one) |
| `S4.8.6` | `certifiers using this standard.` (genuinely centred on the paper) |

## 2. The cause, in one line of code

```python
if paragraph and paragraph_indent is not None and abs(indent - paragraph_indent) >= 6:
    flush_paragraph()        # "a centred line is its own block"
```

The rule was added for **centred** labels (`Regional or other exception`, `South African specific`) —
a line set at column ≥10 cannot be body text. But `abs(...) >= 6` also fires on a **hanging indent**
of 6–9 columns, which is exactly how SAOSO prints a clause's continuation. So the rule that was
supposed to catch a centred label catches every wrapped clause instead.

The evidence that it is a *mis-fire* and not a tuning knob: the label path already has its own
threshold (`paragraph_indent >= 10` in the same function, and `_QUALIFIER_CHARS` since §3.14). The
two rules disagree, and the wrong one wins first.

## 3. The fix

A line opens its own block **only when it is centred** — `indent >= 10` while the paragraph's own
indent is below that — not when it merely differs by six. Concretely: replace the `abs(...) >= 6`
condition with the same `>= 10` test the centred-line branch uses, so the two cannot drift apart.

Expected effect, to be pinned by the test rather than assumed:
`S23.3` becomes **one** paragraph; `S4.8.6`'s `certifiers using this standard.` stays its own block
(it is printed centred, indent 30); `S5.1.3`'s list and `S8.1`'s nesting are unchanged
(`flatten()` reproduces every chunk, as it does today).

## 4. Guards (each must be seen failing before it is trusted)

1. **Reader level:** `S23.3` renders one paragraph whose text ends `property or documents.`, and the
   page has no `<p class="passage__text">workers'` element.
2. **Corpus level:** over the shipped SAOSO, **no** chunk's rendered blocks end in a paragraph that
   starts with a lower-case word — with a recorded exception list for the two known corpus defects
   (`S1`'s `m²`, `S4.8.6`'s centred note), so a new split is a failure and not noise.
3. **Losslessness:** `flatten(passage_blocks(text))` still reproduces every chunk of the real corpus —
   the existing guard in `knowledge/tests/test_passages.py`, which must stay green untouched.
4. **UAT Scenario 8** is re-judged after the fix: *does a quoted clause now read, and copy, as one
   sentence?* The scenario is already signed PASS for the list rendering; this adds the clause case to
   the reviewer's list rather than reopening it.

## 5. Why this is display-only

The words, their order and their punctuation do not change: two paragraphs become one, which is a
whitespace decision the reader already owns (`strip_overlap` does the same kind of trimming). No
`DocumentChunk`, no artefact, no embeddings, no citation audit, no `--force`.

## 6. Definition of done

- [ ] `S23.3`, `S23.1`, `S23.4` each render as one paragraph on `/read/?section=s23`.
- [ ] The 25-of-319 measurement is re-run and every remaining case is either fixed or named in the
      exception list with its reason.
- [ ] `test_passages.py`'s losslessness guard is still green, unmodified.
- [ ] UAT Scenario 8 carries a re-judged result for the clause case.
- [ ] Gate green; Playwright green; `testing_hazards.md` §3.14 gains the hanging-indent case.
