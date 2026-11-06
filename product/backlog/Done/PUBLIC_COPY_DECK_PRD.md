# The public copy deck — every string a visitor reads, in one artefact

**Status:** **Done** — the instrument landed 2026-11-06 (`1cb2667`, pushed) and the first rewrite
pass with it. The writing pass over the remaining strings has **no PRD** and is a line in
`todo.md`, because it is a writer's act, not a build.
**Owner:** Kobus Meiring (Product) — the voice and the sign-off · build — the tool
**Artefacts:** `product/design/COPY_DECK.md` (generated) · `COPY_VOICE.md` (the brief pasted above
it) · `REFERENCE_COPY_CORPUS.md` (a register sample, to search and not to read)
**Tools:** `scripts/copy_deck.py` + `copy_deck_extract.py` + `copy_deck_selftest.py` ·
`scripts/fetch_reference_copy.py`
**Reference:** `build_principles.md` §II (the 30 KB cap) · `product/design/DESIGN.md` §7.4 (the
element definitions are quoted verbatim) · `core/tests/test_claim_discipline.py` ·
`testing_hazards.md` §3.48
**Commit:** `1cb2667` on `04200f0`; the gate fix this needed first is `abb5a9a`.

---

## The problem it answers

The public site's copy lived in eighteen templates plus one `PAGES` dict. Nobody could see it
whole, so nobody could hold a voice across it, and a rewrite meant editing markup by hand in eight
files. A writing pass — a person or a model told to rewrite and not to add facts — needs the strings
in reading order, with the surrounding markup out of the way, and it needs a way to come back that
cannot silently damage the tree.

## What a row is

    ### WHY-JOIN-004 - p.element-card__body
    `core/templates/public/sections/_why_join.html` line 29 - mode: `auto`

    old: |
      The committee records one of four outcomes against the SAOSO standard. ...
    new: |

`old:` is the guard and a writer never touches it: `--apply` refuses any row whose `old:` no longer
matches the file. `new:` is the only thing a rewrite edits, and a blank `new:` means unchanged.

Three modes, because not every string is safe to rewrite:

- `auto` — one contiguous run of plain text. Rewritten in place.
- `manual` — the run holds inline markup (`<strong>`, `<a>`) or a `{{ }}` expression. `--apply`
  skips it; the file is edited by hand.
- `locked` — a citation chip (`OPP §3.3`), a step label, or a fee-table cell. Facts, not prose:
  rewriting one would break the claim it cites.

`--apply` replaces the exact source region a run occupies and splices several rewrites in one file
back to front, so offsets cannot drift. A rewrite of a `PAGES` field keeps `_public.py` parseable or
refuses.

## Measured (2026-11-06, this tree)

| | |
|---|---|
| strings · words | **527 - 4697** |
| `auto` · `manual` · `locked` | 348 · 39 · 140 |
| not yet in the deck | 0 |
| rows whose `old:` has drifted | 0 |
| templates outside the deck | 0 |
| `copy_deck_selftest.py` | **PASS** (six properties) |
| `copy_deck.py` · `copy_deck_extract.py` | 23 KB · 11 KB (both under §II's 30 KB) |

Two gaps this act closed on the way: **`before_you_apply.html` was outside the deck** — A8's public
self-check, invisible to a writing pass, and reported as "1 template outside the deck" on every run;
and **`copy_deck.py` was 32 KB against the 30 KB cap**, which is what had made step 1 of
`verify.sh` red. The split is at a real seam: `copy_deck_extract.py` reads a string and writes
nothing (so it is testable without a filesystem and holds no `ROOT`), while `copy_deck.py` keeps
every guarantee about writing the tree.

## What is not done

- **50 of 527 strings carry a rewrite** — the rest are still the original copy. The deck, the brief
  and the corpus are all in place; the pass is labour.
- **No UAT sign-off.** The rewritten copy is user-facing and is judged by the product owner in a
  browser, not by a test. `build_principles.md` §VIII: an unsigned surface is partial.
- **`REFERENCE_COPY_CORPUS.md` cannot be regenerated from a clean checkout** — `--refresh` needs the
  network and the page list; the cache it otherwise reads (`_scratch/reference_html/`) is not in the
  repository. The artefact is committed, so only *refreshing* is affected.

## The rule the deck exists to carry

**Rewrite. Never add a fact.** A writing model's instinct is to add warmth, and on this site warmth
is a legal claim: the public surface reproduces only the four FORM outcomes and the *active* seals.
`COPY_VOICE.md` §1 names the forbidden phrases, and `core/tests/test_claim_discipline.py` still
fails the build on them — the deck does not replace that guard, and nothing in the tool judges
whether a sentence is true.
