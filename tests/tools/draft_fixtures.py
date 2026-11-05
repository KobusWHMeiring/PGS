"""The drafting body stream, built from the committed pages (S3).

`scripts/build_corpus.pages_of` is the only part of the drafting path that needs a PDF, and the gate
runs with `PDFTOTEXT_BIN=/usr/bin/true` (`testing_hazards.md` §2.9) — so any test of the *generator*
has to feed itself the way `page_fixtures` feeds the parsers: committed text, the same transforms.

This is not a second implementation of `pages_of`. The one decision it makes — which rendering a page
comes from — is `scripts.corpus_pages.choose_pages`, the same function the generator calls, and the
page markers are written by `scripts.build_corpus.assemble_body`, also the same function. A test body
built any other way would be a body the generator never produces.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def chosen_pages(doc_key: str) -> list[str]:
    """The document's pages, rendered and chosen exactly as `pages_of` chooses them."""
    from knowledge.columns import apply_layout
    from knowledge.reflow import reflow_pages
    from knowledge.tests import page_fixtures
    from scripts.corpus_pages import choose_pages

    laid, _ = apply_layout(page_fixtures.pages(doc_key, "layout"), doc_key=doc_key)
    laid, _ = reflow_pages(laid)
    raw, _ = reflow_pages(page_fixtures.pages(doc_key, "raw"))
    chosen, _used = choose_pages(laid, raw)
    return chosen


def fixture_body(doc_key: str) -> list[str]:
    """The body stream `build()` drafts from, page markers and blank lines included."""
    from knowledge.sections.heading import page_stamp
    from scripts.build_corpus import assemble_body
    from scripts.corpus_pages import flatten

    chosen = chosen_pages(doc_key)
    printed = {number: page_stamp(page) for number, page in enumerate(chosen, 1)}
    body, _last = assemble_body(flatten(chosen)[0], printed, lambda line: True)
    return body
