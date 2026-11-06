# Session `1u` — the copy deck lands, and the gate it was hiding

**Date:** 2026-11-06 · **From:** the copy-deck landing · **For:** the next agent, who starts on UI
refinement

## 1. What this session was

The owner asked for two things, in order: **"work the copy deck work into main as well"**, then
"small frontend refinements — let me know when you're ready". The first is this session. The second
became `Refinement/UI_REFINEMENT_PRD.md`, four open questions, and nothing built.

The copy-deck work had been sitting in this working tree, uncommitted, since session `1t` (which had
stashed it, merged the visit strand, and restored it — `§3.47`). Committing it meant three jobs: get
`copy_deck.py` under the 30 KB cap, regenerate the deck against the tree it had rewritten, and then
answer the question the previous handover could not: **is `verify.sh` green?**

## 2. The split found the seam, so the split is cheap to read

`copy_deck.py` was **32 KB** against `build_principles.md` §II's 30 KB, and that is what step 1 of
the gate had been red on. `_scratch/split_copy_deck.py` did the surgery **by line range, not by
retyping**, and asserted the properties that matter: both halves `ast.parse`, the moved text is
verbatim (`extract.endswith(moved)`), **no line of the original is missing from the pair**, and the
only lines added are its own headers. 32 KB → **23 KB** + `copy_deck_extract.py` **11 KB**.

The seam is real, not a size trick: `copy_deck_extract.py` reads a string and writes nothing — it
holds no `ROOT`, so `copy_deck_selftest.py`'s `cd.ROOT = tmp` monkeypatch still points at the real
templates through the module that reads them. `--apply`'s guarantees (which region is replaced, and
the refusal of a stale `old:`) all stayed in `copy_deck.py`.

`ROOT` had to move above the sibling import, because `python scripts/copy_deck.py` puts `scripts/`
on `sys.path`, not the repo root — the same shim `uat_runner.py` uses, comment included.

## 3. Two defects found by looking, not by testing

**(a) A page was invisible to the writing pass.** Every `--check` run printed
`template not in GROUPS … before_you_apply.html` and `1 template(s) outside the deck`. That is A8's
public self-check — the page the hero links and the demo pivots on — and the deck's contract is
"every string a visitor reads". It is in the deck now, after *How it works*: **458 → 527 strings**.

**(b) `--apply` was writing CRLF.** Three `write_text()` calls had no `newline="\n"`, so on Windows
every write flipped the endings of the whole file it touched — the tool was manufacturing exactly
the trap `testing_hazards.md` §1.41 documents, and the deck came back CRLF every regeneration. All
three now pass `newline="\n"`, and the five new files were normalised to LF before commit (they had
been created on Windows and were still untracked, so `git add` had never rewritten them).

## 4. The gate was red for a reason that was not the deck's

`verify.sh` was green after the split — except for two tests, and they were red for a third reason:

    $ PDFTOTEXT_BIN=$PWD/scripts/_no_extractor pytest -q --reuse-db \
        tests/tools/test_new_document_ingest.py
    knowledge\ingest.py:368: in ingest_standard
        toc_pages = extract_pages(path)
    E   knowledge.extraction.ExtractionError: `.../scripts/_no_extractor` not found.
    2 failed
    $ pytest -q --reuse-db tests/tools/test_new_document_ingest.py    # Xpdf 4.00 on PATH
    2 passed in 7.37s

Neither side is wrong. `ingest_standard` re-reads the PDF's **printed table of contents** even when
a reviewed artefact supplies the text — deliberately, D68 §7.5. `verify.sh` poisons `PDFTOTEXT_BIN`
on purpose (D57, §2.9) and `test_verify_gate.py` asserts both the export and that the poisoned path
cannot exist. Put together, those two tests were red **in the gate** from `665b1fb` (2026-11-05),
and nobody saw it because **step 1 stopped the run before pytest**, so every suite number quoted
for this tree came from a `--reuse-db` run with a real reader on PATH.

The fix is the rule, not a deletion: `a_real_reader` names `shutil.which("pdftotext")` itself and
skips with a printed reason when the box has none. The gate stays green on a machine without
poppler, and the two tests — the only proof of `INGESTION_ENGINE_PRD` §6's first criterion — still
run wherever one exists. Deleting or xfailing them would have removed the proof to make a number.

That lesson is `testing_hazards.md` **§3.48**: *a gate that fails at step 1 is not evidence about
steps 2–4.* The fix went in **first** (`abb5a9a`), so the deck landed on a tree whose gate could be
quoted.

## 5. The deck as it landed

    $ python scripts/copy_deck.py
    copy_deck: wrote product\design\COPY_DECK.md - 527 strings, 4697 words
      auto=348 manual=39 locked=140
    $ python scripts/copy_deck.py --check
    copy_deck: 527 strings on the site, 527 in the deck
      0 not yet in the deck, 0 whose old: has drifted, 0 with a rewrite waiting to apply
      0 template(s) outside the deck
    $ python scripts/copy_deck_selftest.py
    result: PASS

The **first rewrite is applied** — `home.html`, `_key_facts.html`, `_why_join.html` and the `home`
`Page` in `_public.py` — and the deck regenerated so `old:` matches the tree. Verified in the
browser rather than in a diff: `127.0.0.1:8000` serves `a farmer-led organic guarantee` and
`on each other's farms.` What is left is **477 of 527 strings**, a writer's labour, and it is a
`todo.md` line under Content with the two commands that apply a `new:` block.

## 6. Gate, measured once, cold

    $ DATABASE_URL=postgres://pgs:pgs@localhost:5433/pgs_verify ./scripts/verify.sh
    ==> 1/4  context budgets  0 breaches
    ==> 2/4  manage.py check  clean · makemigrations --check  No changes detected
    ==> 3/4  lint-imports      knowledge must never import core KEPT
    ==> 4/4  pytest           2090 passed, 1 skipped, 8 xfailed in 321.27 s (0:05:21)
    ✅ verify passed — this tree is shippable

Warm for the same tree: **76.57 s** (`-q --reuse-db`). Quote both, or neither (§3.17).

## 7. Commits

    abb5a9a  Gate: a test that needs a reader names one, and the gate can no longer hide it
    1cb2667  Copy deck: 527 strings in the deck, 0 drift, and the first rewrite applied
    66bc6c1  Handover + backlog: the copy deck is landed, and the gate is green again

All pushed; `git rev-list --count origin/main..HEAD` = 0.

## 8. What the next session does

**UI refinement**, and the owner's brief is one sentence: *"header sizes being too big, placing
relevant back buttons where they are needed, basic UI improvements."* `Refinement/UI_REFINEMENT_PRD.md`
stages it and — deliberately — **contains no design decisions**:

- §3 is **four questions only the owner can answer**: which "header" (page `h1`, section `h2`, or the
  sticky site header), which surfaces first, where a back button belongs, and which screen the
  complaint was judged on.
- §4 is the measurement pass: screenshots at **375 / 768 / 1440** into `_scratch/`, the rendered
  `h1`/`h2` px and the measure recorded per page, and the findings written into the PRD's §6 as a
  table the owner picks from. **No CSS before that table exists.**
- §5 is the second act the owner asked for: a short investigation into UI-refinement practice
  (WCAG 2.2 target size and contrast, the heuristic lists, type-scale ratios) **before** writing a
  local `pgs-refining-ui` skill — four `pgs-*` skills exist and none of them is about the browser. It
  must encode this repo's loop (spec before template, one `brand-*` palette, no build pipeline,
  one screenshot per pass), not a theory.
- §2 is the only hint: `DESIGN.md` §4 already gives the numbers (`h1` is `md:text-6xl`; `h2` is
  `sm:text-4xl`), and Lora is intentionally *not* bold, so the answer is probably a size or a
  measure, not a weight.

**One caution for that session.** "Basic UI improvements" is the phrase that invites a redesign. The
live WordPress site is the content baseline, not the design reference
(`product/design/content_inventory.md`), four palettes exist under `product/design/` and exactly one
is the design system, and this tree has been burned by a view that was changed before it was looked
at. Measure, photograph once, change `DESIGN.md` before the template.
