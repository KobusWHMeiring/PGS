"""The reader probe must measure the shipped rules, not a copy of them.

The first version of `probe_reader_structure.py` held its own copy of the proposed dividers, its own
locator comparison and three resolver functions for section and appendix references — a second
implementation of the thing it was reporting on. That is precisely how `probe_chat.py` came to print
a grounded answer for a question `/ask/` refuses: a measuring tool that measures a different path
(`testing_hazards.md` §2.7, §21's G8).

Three guarantees, each mutation-checked:

* the copied constants are gone, and cannot come back;
* the locator and reference rules come from `knowledge`, by import;
* there is no resolver in the probe at all — if one reappears, this file says so.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import probe_reader_structure


def _source() -> str:
    return Path(probe_reader_structure.__file__).read_text(encoding="utf-8")


def test_the_probe_holds_no_copy_of_the_table_data():
    """Mutation: re-adding `PROPOSED_DIVIDERS = {}` makes this red."""
    assert not hasattr(probe_reader_structure, "PROPOSED_DIVIDERS")
    assert not hasattr(probe_reader_structure, "COLUMN_HEADERS")
    assert "PROPOSED_DIVIDERS" not in _source()


def test_the_probe_imports_the_rules_it_reports_on():
    """Mutation: writing the locator comparison out again makes this red."""
    source = _source()

    assert "from knowledge.tables import TABLE_SECTIONS" in source
    assert "from knowledge.references import build_reference_index, matches" in source
    assert "from knowledge.reading import branch_texts, passage_locator, printed_locators" in source
    assert "from knowledge.glossary import" in source


def test_the_probe_has_no_resolver_of_its_own():
    """A second implementation of a rule is a second answer to the same question."""
    source = _source()

    assert "def resolve_" not in source
    assert "chunk.page) != previous" not in source


@pytest.mark.django_db
def test_the_probe_says_what_to_do_when_the_corpus_is_empty(capsys):
    """It refuses to print numbers it cannot measure, and names the command that would fix it."""
    with pytest.raises(SystemExit) as raised:
        probe_reader_structure.main([])

    assert "ingest_standard" in str(raised.value)
