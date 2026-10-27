# Bug: a citation opens the wrong passage when its reference is shared

**Status:** Open — found 2026-10-27 while pricing the concordance (SPEC §18.3 **D68**, Q8).
**Severity:** A visitor following "Read it in SAOSO v2.1" on an answer page can land on a different
passage from the one quoted. The answer page's own quote is correct; the link's target is not.
**Owner:** Build
**Affected:** `/documents/<code>/read/` (the anchor a link carries), `Citation.read_url`, the
reader's in-document search results.
**Reference:** `CONCORDANCE_PRD.md` §10.7, §7.8 · `product/design/d68_concordance_open_questions.html`
Q8 · `knowledge/reading.py` (`reading_anchor`, `unique_anchors`) · `core/services/_chatbot.py`
(`Citation.read_url`) · `build_principles.md` §I (no sequential id on a public surface)

---

## 1. What happens

`knowledge/reading.py` has two anchor functions that disagree:

```python
reading_anchor(section_ref, anchor, heading_path)   # one anchor per chunk — no suffix
unique_anchors(chunks)                              # the same, plus -2, -3 … for collisions
```

The reader uses `unique_anchors()`, so its own links are unique. `Citation.reading_anchor` and
`SearchHit.anchor` call `reading_anchor()` directly, so a citation's link is the **first** passage
that carries that reference. Where several passages share a reference, every citation to the rest
opens the first one.

## 2. How many

Measured on the local corpus, 2026-10-27 (`_scratch/concordance/verify_branches.py`, read-only):

| Document | Passages | Groups sharing an anchor | Passages that land on someone else |
|---|---:|---:|---:|
| SAOSO v2.1 | 319 | 8 | 48 |
| OPP | 30 | 2 | 2 |
| Certification landscape | 8 | 2 | 2 |
| Basic Production Principles | 9 | 1 | 5 |
| **Total** | **366** | **13** | **57 (15.6%)** |

The worst group is Appendix 2: **30 chunks, all cited `Appendix 2`.** A citation to 29 of the 30
substance rows carries `#appendix-2` and lands on the first row's text — *"Farmyard manure, slurry
and urine"*.

## 3. Why it matters now

Twenty-nine of the thirty rows are unaddressable, and Appendix 2 is the appendix the most-asked
question in the corpus lives in (`D50`, `D51`: "cardboard", "horse manure"). The answer page prints
the right quote and links to the wrong line, which is the failure mode the "View this line" change
exists to prevent.

The reader's `-N` suffix is not a fix: it is derived from ingest order, so inserting a row into the
reviewed Appendix 2 artefact (`CORPUS_CANONICAL_FORMAT_PRD.md`, D53) and re-ingesting repoints
`#appendix-2-4` at a different substance while still resolving. A wrong answer that looks right is
worse than a link that fails. `build_principles.md` §I forbids exactly this shape.

## 4. The fix (decided as D68 Q8)

1. When more than one passage shares a `section_ref`, add a disambiguator derived from the passage
   itself — its own words, slugified — so the anchor is a property of the text and not of its
   position (`#appendix-2-wood-bark-and-sawdust`).
2. Keep the bare `#appendix-2` working as an alias, because links shipped on 2026-10-27 exist in
   stored answer snapshots and in messages people have sent each other.
3. `?section=`/`_select_section` must accept a branch anchor, a new passage anchor, and a bare alias.

## 5. The guard, and why a fixture cannot be it

A test that walks **all 366 passages of the real corpus** and asserts each passage's own anchor
resolves to that passage. A fixture of three chunks with one duplicate passes while the product is
wrong — that is the shape of `testing_hazards.md` §1.6.

## 6. Definition of done

- [ ] Anchor derivation is content-derived for a shared reference and the bare anchor still resolves.
- [ ] The guard test exists, **has been watched to fail** against the current derivation, and passes.
- [ ] A stored citation from an Appendix 2 row (not the first) opens that row's text.
- [ ] `SearchHit.anchor` and `Citation.reading_anchor` use the same derivation as the reader. No
      second anchor function.
