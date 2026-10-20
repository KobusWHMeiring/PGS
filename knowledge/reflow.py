"""Rejoin a word hyphenated across a line break, so it is quotable as printed.

`pdftotext -layout` breaks lines where the page breaks them, and a page breaks inside
a hyphenated word:

    The percentage of non-organic feed may not exceed 10% dry matter per ruminant
    and 15% dry matter per non-

    ruminant calculated on an annual basis.

A reader sees `non-ruminant`. The stored chunk says `non-\\n\\nruminant`, and
`audit_citations` compares whitespace-normalised text — so the stored form is
`non- ruminant`, which no one writes and which the model, quite reasonably, refused to
reproduce: two live answers on 2026-10-21 elided the word with `...` and were refused
for a defect the corpus owned (CHAT_ANSWER_COVERAGE_PRD.md G1, G2).

Measured on the four governed documents (2026-10-21): 20 wraps, every one a genuine
compound — `post-harvest`, `cross-pollination`, `in-conversion`, `non-organically`,
`non-ruminant`, `non-organic`, `nature-identical`, `cobalt-sulphate`,
`semi-sparkling`, `non-compliance`, `inter-member`, `free-range`, `on-farm`,
`re-usable`, `in-country`, `well-being`, `self-assessment`. No page ends inside such a
word, which is why a per-page pass is complete; `test_reflow.py` pins both facts.

Three decisions worth keeping:

- **The hyphen stays.** Joining `post-` and `harvest` as `postharvest` would invent a
  spelling; the printed word has the hyphen.
- **Blank lines are crossed.** SAOSO prints its body double-spaced, so the halves of a
  wrapped word are usually a blank line apart. Requiring strict adjacency would repair
  almost nothing.
- **There is no "smart" dehyphenation dictionary.** A join happens only when the line
  ends in letter-hyphen and the next non-blank line starts with a lowercase letter.
  That is decided by the page, not by a word list, so a retarget to another standard
  needs no data (the same rule as `columns.py`).

Pure: a function of a page string. No Django, no PDF library, no locale. It runs at
ingest, beside the column transform — **not** in the citation audit. Loosening
`_normalise_text` would accept quotes that are not substrings of the page; repairing the
page keeps the audit strict, and `testing_hazards.md` §1.22 is the record of why.
"""

from __future__ import annotations

import re

#: A line whose last printed character is a hyphen preceded by a letter.
WRAPPED = re.compile(r"[A-Za-z]-$")


def _ends_in_a_wrapped_word(line: str) -> bool:
    """True when `line` stops inside a hyphenated word."""
    return bool(WRAPPED.search(line.rstrip()))


def _continues_a_word(line: str) -> bool:
    """True when `line` reads as the second half of a word, not a new sentence.

    Lowercase only. A capital after a hyphen (`non-` / `Organic`) is a new sentence or
    a list item, and a digit or punctuation is not a word at all.
    """
    stripped = line.lstrip()
    return bool(stripped) and stripped[0].islower()


def join_hyphenated(page: str) -> str:
    """The page with every word the PDF wrapped rejoined; unchanged otherwise.

    In:  `page` — one page of `pdftotext -layout` output in reading order (run it
         **after** `de_column`, so line adjacency is reading adjacency).
    Out: the repaired page, or **the same string object** when there was nothing to
         join. The fallback is never a guess.
    Fails: never.
    """
    lines = page.split("\n")
    out: list[str] = []
    index = 0
    joined = 0
    while index < len(lines):
        merged = lines[index]
        cursor = index + 1
        while _ends_in_a_wrapped_word(merged):
            candidate = cursor
            while candidate < len(lines) and not lines[candidate].strip():
                candidate += 1
            if candidate >= len(lines) or not _continues_a_word(lines[candidate]):
                break
            merged = merged.rstrip() + lines[candidate].lstrip()
            cursor = candidate + 1
            joined += 1
        out.append(merged)
        index = cursor
    if not joined:
        return page
    return "\n".join(out)


def reflow_pages(pages: list[str]) -> tuple[list[str], tuple[int, ...]]:
    """Rejoin every page and report the 1-based **PDF** pages that changed.

    In:  `pages` — de-columned pages, `pages[N - 1]` is PDF page N.
    Out: `(repaired_pages, changed)`, mirroring `columns.apply_layout`, so the ingest
         report and the operator's log can see that the transform ran instead of
         inferring it from a better answer.
    Fails: never.
    """
    repaired: list[str] = []
    changed: list[int] = []
    for number, page in enumerate(pages, 1):
        fixed = join_hyphenated(page)
        if fixed != page:
            changed.append(number)
        repaired.append(fixed)
    return repaired, tuple(changed)


__all__ = ["join_hyphenated", "reflow_pages"]
