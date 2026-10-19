"""Which parser reads which document — chosen by data, not by a branch (D24, §4.5).

`StandardDocument.section_scheme` holds a scheme name; this module maps it to a
parser. Adding a standard therefore means adding a parser module and a
`StandardDocument` row — **not a migration**, and not an `if` in the ingestion
service (`build_principles.md` §I: code encodes the process, data encodes the
standard).

A missing scheme raises. The tempting alternative — silently falling back to the
heading parser, which never fails because it accepts anything — would ingest a
numbered standard as an unnumbered one and produce citations the reader cannot find,
with no error anywhere. `test_registry_fails_loudly_on_an_unknown_scheme` holds that
door shut.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from knowledge.sections.heading import HeadingParser
from knowledge.sections.opp import OppParser
from knowledge.sections.saoso import SaosoParser

if TYPE_CHECKING:  # pragma: no cover - typing only, keeps knowledge import-light
    from knowledge.models import StandardDocument

#: Scheme name -> parser class. The keys are the values B6 writes to
#: `StandardDocument.section_scheme`; `schemes()` is public so a management command
#: can list them instead of hardcoding the set in a `--help` string.
_PARSERS = {
    "saoso": SaosoParser,
    "opp": OppParser,
    "heading": HeadingParser,
}


class UnknownSectionScheme(ValueError):
    """Raised for a `section_scheme` with no registered parser."""


def schemes() -> tuple[str, ...]:
    """Every registered scheme name, sorted."""
    return tuple(sorted(_PARSERS))


def get(scheme: str):
    """In:  `scheme` — a `StandardDocument.section_scheme` value.
    Out: a fresh parser instance.
    Fails: `UnknownSectionScheme`, listing the registered schemes.
    """
    try:
        parser = _PARSERS[scheme]
    except KeyError as exc:
        raise UnknownSectionScheme(
            f"No section parser for scheme {scheme!r}. Registered: {', '.join(schemes())}."
        ) from exc
    return parser()


def get_for(document: "StandardDocument"):
    """The parser for a document row — B2's acceptance test.

    In:  `document` — anything with a `section_scheme` attribute.
    Out: a parser instance. No code change is needed to add a document that reuses an
         existing scheme.
    """
    return get(document.section_scheme)


__all__ = ["UnknownSectionScheme", "get", "get_for", "schemes"]
