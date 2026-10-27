"""No glyph the paper prints may reach the corpus as U+FFFD.

The reader reproduces the document's own words, so a character the extraction loses is a
character the document no longer says: `moving freely around 360�` is not the standard's
sentence, and the citation audit compares a model's quote against exactly this text — so a
loss here also makes a *faithful* quote unquotable.

Measured 2026-10-27 (HANDOVER §0e item 6, `BugFixes/saoso_text_glyphs_and_boundaries.md`
§1): 83 characters across the four ingested documents were U+FFFD. The cause was not the
PDF. Xpdf 4.00 writes Latin-1 unless `-enc UTF-8` is asked for (`knowledge/extraction.py`
now does), and the old `decode("utf-8", errors="replace")` turned every 8-bit byte of it
into U+FFFD. All 83 were recoverable.

These guards are over the **committed pages every extraction test reads** (D57), so they
run on a machine with no PDF reader and they fail the moment a fixture is regenerated
with the wrong encoding. They are not a substitute for `scripts/check_extraction.py`,
which is what proves the *current* extractor still produces these bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge.tests.page_fixtures import MANIFEST, pages

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
REPLACEMENT = "\ufffd"

#: `(document, the characters the paper prints)`. Each string was read off the page or off
#: the corrected extraction, and each is a character the old decode destroyed: `°`, `²`,
#: an en dash, `é`, `ü` and a section sign. A guard that only counts U+FFFD would not
#: notice a decode that replaced them with `?`; this one would.
PRINTED = (
    ("saoso", "moving freely around 360°"),
    ("saoso", "100 m² of the house/building"),
    ("saoso", "not exceed 45°C"),
    # `rosé` and `Mèthode`: the second is the *document's* spelling — the page prints a
    # grave accent, and the extraction reproduces it rather than correcting it. That is the
    # point of these guards: the reader quotes the standard, it does not tidy it.
    ("saoso", "For white and rosé"),
    ("saoso", "Quality wines (Mèthode"),
    ("saoso", "See Section B – Appendix 6"),
    ("saoso", "dairy – 90 days"),
    ("opp", "R 250,001 – R 500,000"),
    ("opp", "SAOSO standard – details"),
    ("landscape", "Gesellschaft für"),
)

MODE_KEYS = sorted(MANIFEST["pages"])


def test_no_committed_page_holds_a_replacement_character():
    """The whole page corpus, every mode, every document: zero U+FFFD.

    Mutation: reverting `-enc UTF-8`, or regenerating the fixtures on a build whose default
    output encoding is Latin-1, puts 275 of them back. Breaking this test is the cheapest
    possible signal that the contract has moved.
    """
    offenders = []
    for key in MODE_KEYS:
        record = MANIFEST["pages"][key]
        text = (Path(__file__).resolve().parents[2] / record["file"]).read_text(
            encoding="utf-8"
        )
        count = text.count(REPLACEMENT)
        if count:
            offenders.append(f"{key}: {count}")

    assert offenders == [], (
        "a page fixture holds U+FFFD, so the extraction lost a printed character: "
        + ", ".join(offenders)
    )


def test_no_range_fixture_loses_a_glyph():
    """The manifest's own count, per range fixture, is the ratchet: it must stay zero.

    The field exists (`scripts/extract_fixtures.py` writes `replacement_char_count`) so a
    regeneration that loses a glyph says so in the diff of a reviewed file, not only in a
    test that happened to run.
    """
    counted = {
        name: record["replacement_char_count"]
        for name, record in MANIFEST["fixtures"].items()
        if record["replacement_char_count"]
    }
    assert counted == {}


@pytest.mark.parametrize("doc_key,printed", PRINTED, ids=[f"{d}:{p[:24]}" for d, p in PRINTED])
def test_the_printed_characters_survive_extraction(doc_key, printed):
    """The characters themselves, not just the absence of a marker.

    `360°`, `100 m²`, `45°C`, `Section B – Appendix 6`, `rosé`, `Mèthode Cap Classique`,
    the OPP's fee en dash and the landscape's `für`. Each was U+FFFD in the shipped corpus.
    """
    body = "\f".join(pages(doc_key))
    assert printed in body, f"{doc_key}: {printed!r} is not in the committed pages"


def test_the_manifest_records_the_encoding_it_was_made_with():
    """The fixture's provenance names the encoding, so a later reader can tell which
    contract produced these bytes without re-running the extractor."""
    extraction_command = MANIFEST["extraction_command"]
    assert "-enc UTF-8" in extraction_command, extraction_command
