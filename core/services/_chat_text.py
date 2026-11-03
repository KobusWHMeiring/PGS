"""The chatbot's string work: tokens, locators and the digests of both.

Split out of `_chatbot.py` (CONTEXT_CUTS_PRD step 1) because the prompt, the audit and
the answer cache all need the *same* rendering of a locator and the *same* comparison
key for a reference. One expression, one place: a copy of `locator_of` in the relinker
would let the two drift into never matching.

Nothing here decides anything. There is no policy in this module -- no prompt text, no
audit verdict, no cache key. It turns a question or a chunk into a string that something
else judges, which is why every function is small and every one is pure.
"""

from __future__ import annotations

import hashlib
import re

from knowledge.models import DocumentChunk
from knowledge.services import RetrievedChunk


def normalise_question(question: str) -> str:
    """The cache key's input: case- and whitespace-insensitive, otherwise untouched."""
    return " ".join((question or "").lower().split())


#: English function words that carry no retrieval signal. Postgres's `english`
#: configuration removes them from the *document* vector but `websearch_to_tsquery`
#: joins every remaining word with AND — so "What does the standard require for
#: traceability?" becomes `standard & require & traceabl` and matches nothing when the
#: chunk says "Records must be kept...". Measured on the shipped corpus 2026-10-19.
_STOPWORDS = frozenset(
    """a about above across after again against all also am an and any are as at be
    because been before being below between both but by can could did do does doing
    down during each few for from further had has have having he her here hers him
    his how i if in into is it its just me more most my no nor not of off on once
    only or other our out over own same say says said she should so some such than
    that the their them then there these they this those through to too under until
    up very was we were what when where which while who whom why will with would you
    your""".split()
)


def _words(text: str) -> list[str]:
    """Lowercased alphanumeric tokens, punctuation dropped."""
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _content_words(text: str) -> list[str]:
    """The tokens that carry subject matter: `_words` without English function words."""
    return [word for word in _words(text) if word not in _STOPWORDS]


def _normalise_text(text: str) -> str:
    """Whitespace-normalise for substring checks; punctuation and case stay exact."""
    return " ".join((text or "").split())


def locator_of(chunk: RetrievedChunk | DocumentChunk) -> str:
    """The string a citation must use for this chunk.

    SAOSO and the OPP have a `section_ref`. The BPP and the landscape print no clause
    numbers, so their locator is the content-derived `anchor` (D42/D43); a page number
    is the last resort only because it is at least checkable against the paper.

    Both a `RetrievedChunk` and a `DocumentChunk` qualify: this reads three attributes,
    and a corpus rebuild has to render the locator from the stored row (`_evidence.py`
    matches a grounding snapshot back onto new chunks). One expression, one place — a copy
    in the relinker would let the two drift into never matching.
    """
    return (
        chunk.section_ref
        or chunk.anchor
        or (f"p.{chunk.page}" if chunk.page is not None else "")
    )


#: A Markdown heading marker at the very start of a passage: the corpus format (D53) carries
#: headings as `#`-level Markdown, so the same clause states as `4.1. Processing…` from the
#: PDF path and as `## 4.1. Processing…` from the reviewed artefact. It is presentation.
_HEADING_PREFIX = re.compile(r"^#{1,6}[ 	]+", re.MULTILINE)


def text_sha(text: str | None) -> str:
    """The digest a grounding snapshot records for a passage's text.

    One expression, one place: `_grounding_snapshot` writes it and `_evidence.py` matches
    against it after a rebuild. Truncated to 16 hex characters because it answers "is this
    the same passage?" inside one database row, not "is this file intact?".

    **Hashed over its words, not its layout.** A leading Markdown heading marker is stripped
    (the artefact states `## 4.1. …` where the PDF path stated `4.1. …`) and runs of
    whitespace are collapsed — the same normalisation the citation audit uses to compare a
    quote with a passage. Without it, the first artefact rebuild read **230 of 291** passages
    as changed text (measured 2026-10-28) and the evidence that a rebuild did *not* alter a
    passage stopped relinking. A changed *word* still changes the digest, which is the point.
    """
    normalised = " ".join(_HEADING_PREFIX.sub("", text or "").split())
    return hashlib.sha256(normalised.encode()).hexdigest()[:16]


def _normalise_ref(value: str) -> str:
    """The comparison key for a locator or a sub-ref: spelling in, identity out.

    The prompt prints each locator exactly as `locator_of` renders it, and the model
    usually copies it. When it does not, the difference is typography rather than
    substance: `§4.2` vs `4.2` (the OPP never prints the sign — D43), `Section 6.3`
    vs `§6.3`, `4.2 (12)` vs `4.2(12)`. Lowercasing, dropping a `§`/`Section` prefix
    and removing spaces unites those.

    Nothing is **accepted** on the strength of this key alone: `audit_citations`
    resolves a key to a stored locator only when exactly one stored locator produces
    it, so two different addresses can never collapse into one citation. The `S`
    prefix is deliberately *not* stripped — D14 stores it because `1.1.1` exists in
    both Section A and Section B, and conflating them would be a wrong citation.

    **The document label is stripped, not the substance.** The prompt used to print a
    passage's locator joined to its document (`Appendix 2 — SAOSO Standard … v2.1,
    page 77`), and the model cited that whole string. The audit resolved only bare
    locators, refused, and turned a correct, properly quoted answer into "I cannot
    find a definitive answer" on the live site (2026-10-22). The prompt now prints a
    `LOCATOR:` line, and this is the belt to that braces: everything from a dash on is
    decoration, never identity. It does not weaken anything — the key still has to
    resolve to exactly one stored locator, the quote still has to be a substring of
    that chunk, and the `sub_ref` still has to exist.
    """
    text = " ".join((value or "").split()).lower()
    for separator in ("\u2014", "\u2013", " | "):
        text = text.split(separator, 1)[0]
    text = text.replace("§", "")
    if text.startswith("section "):
        text = text[len("section ") :]
    return text.replace(" ", "")


def _sub_ref_names(chunk: RetrievedChunk) -> set[str]:
    return {
        entry.get("ref", "")
        for entry in chunk.sub_refs
        if isinstance(entry, dict) and entry.get("ref")
    }


def _resolve_sub_ref(sub_ref: str, names: set[str]) -> str | None:
    """Return the stored sub-ref the model meant, or None when it is not real.

    The canonical form is `4.2(12)`. A model sometimes returns `12` or `(12)`,
    because that is the item marker a reader sees in the passage, and sometimes
    `§4.2(12)`; all three name the same stored ref. Accepting a spelling is safe
    **only** when exactly one stored ref matches it; if two could, the citation is
    ambiguous and is refused. Depth is still never inferred: `4.5(2)(c)(4)` matches
    nothing and stays a hallucination.
    """
    by_key: dict[str, list[str]] = {}
    for name in names:
        by_key.setdefault(_normalise_ref(name), []).append(name)

    key = _normalise_ref(sub_ref)
    exact = by_key.get(key, [])
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None

    item = key[1:-1] if key.startswith("(") and key.endswith(")") else key
    matches = [name for name in names if _normalise_ref(name).endswith(f"({item})")]
    return matches[0] if len(matches) == 1 else None
