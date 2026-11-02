<!-- Archived from HANDOVER.md on 2026-11-02. Verbatim: do not edit. -->
## 0c. 2026-10-27 — the concordance is built; the reader is the document's tree

`/documents/<code>/read/` now renders the printed table of contents as its navigation, with one
branch open; a citation reads **"View this line"**, opens in a new tab, and lands on
`?section=<passage anchor>#<passage anchor>`; and the page names the printed sections the corpus does
not hold (Section A, Appendices A–C). The anchor defect is closed — 57 of 366 passages shared one, and
later passages in a group are now named for their own words (`appendix-2-wood-bark-and-sawdust`) —
with `StandardDocument.toc` (`knowledge/0003`) as the only new field. Gate **954**, Playwright **53**.
**The UAT is unsigned** (`tests/uat/concordance_uat.md`): the feature is not done without names in
that table.

---
