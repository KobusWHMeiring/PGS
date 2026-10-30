"""The retrieval eval set, and what it resolves to in the ingested corpus.

The first half of the instrument in `product/backlog/spike/RETRIEVAL_EVAL_SPIKE.md` §3.1:
the committed ground truth (`knowledge/tests/data/retrieval_eval.json`), its schema, and the
one rule that keeps it honest — **an expected locator must resolve**, or the run stops.

Two things live here and nothing else, because both are shared by the runner
(`scripts/eval_retrieval.py`) and its integrity tests:

* `load_eval_set` — strict parsing. A typo'd key (`"expect": [...]`) would turn a graded
  question into a refusal item, which scores *better*; so unknown keys raise.
* `resolve` — every expected `{doc, locator, contains}` mapped to real chunk ids, failing
  loudly and completely when the corpus has moved out from under the set (spike §3.1
  rule 4, "set rot").

It knows nothing about retrieval. It answers "which chunks would count as this passage?",
never "which chunks came back".
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The committed ground truth. Data, in the repo, reviewable in a diff (spike §3.1).
DEFAULT_SET = REPO_ROOT / "knowledge" / "tests" / "data" / "retrieval_eval.json"

#: Where a question came from. Refusing an unknown value keeps a typo from quietly becoming
#: a new provenance class — the set is only as honest as its labels (spike §6).
SOURCES = ("escalation", "probe", "uat", "curated", "design")

GRADES = (0, 1, 2)


class EvalSetError(RuntimeError):
    """The set, a locator, or the corpus it names is not usable. Never swallowed.

    A locator that resolves to nothing is a hard error, not a miss: re-ingesting a
    document re-splits its chunks, and a question that silently stopped matching would
    delete itself from the measurement while the run stayed green (spike §3.1 rule 4).
    """


class VariantUnavailable(RuntimeError):
    """This variant has not been built, so there is no number to report for it."""


# --- The eval set -----------------------------------------------------------


@dataclass(frozen=True)
class Expected:
    """One graded passage: a document, a locator, and what it is worth."""

    doc: str
    locator: str
    grade: int = 2
    #: A literal string the matching chunk must contain, case-insensitive and
    #: whitespace-collapsed. It exists because one locator is genuinely shared: Appendix
    #: 6a's twenty rows all print `Appendix 6a`, Appendix 2's thirty all print `Appendix
    #: 2`, and S1's eight all print `S1`. Without it, "the ewes row was found" cannot be
    #: distinguished from "any row on page 85 was found" — which is the whole question D73
    #: is being priced for.
    contains: str = ""


@dataclass(frozen=True)
class EvalItem:
    id: str
    question: str
    asked_by: str
    expected: tuple[Expected, ...]
    note: str = ""

    @property
    def answerable(self) -> bool:
        """True when the corpus is supposed to contain the answer.

        A refusal item (`expected: []`) is excluded from recall and MRR: there is nothing
        to find, and scoring it as a permanent miss would make the aggregate lie in the
        other direction. It is reported separately, which is what makes over-retrieval
        measurable at all (spike §3.1 rule 3).
        """
        return any(entry.grade > 0 for entry in self.expected)

    @property
    def distractors(self) -> tuple[Expected, ...]:
        return tuple(entry for entry in self.expected if entry.grade == 0)


@dataclass(frozen=True)
class EvalSet:
    name: str
    items: tuple[EvalItem, ...]
    about: tuple[str, ...] = ()

    @property
    def answerable(self) -> tuple[EvalItem, ...]:
        return tuple(item for item in self.items if item.answerable)

    @property
    def refusals(self) -> tuple[EvalItem, ...]:
        return tuple(item for item in self.items if not item.answerable)


def load_eval_set(path: str | Path = DEFAULT_SET) -> EvalSet:
    """Parse and validate the set.

    In:  a JSON file — `{"items": [...]}`, or a bare list of items.
    Out: an `EvalSet`.
    Fails: `EvalSetError` naming the offending item on a duplicate id, an unknown
        `asked_by`, a grade outside 0–2, or a malformed expected entry. Validation is
        strict because a silently ignored typo (`"expect": [...]`) turns a graded question
        into a refusal item, which reads as a *better* score.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise EvalSetError(f"{path}: cannot be read ({error})") from error
    except json.JSONDecodeError as error:
        raise EvalSetError(f"{path}: is not valid JSON ({error})") from error
    if isinstance(raw, dict):
        records = raw.get("items") or []
        about = tuple(raw.get("about") or ())
        name = str(raw.get("name") or Path(path).stem)
    else:
        records, about, name = raw, (), Path(path).stem

    items: list[EvalItem] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        where = f"item {index} ({record.get('id', '?')})"
        if not isinstance(record, dict):
            raise EvalSetError(f"{where}: expected an object")
        unknown = set(record) - {"id", "question", "asked_by", "expected", "note"}
        if unknown:
            raise EvalSetError(f"{where}: unknown key(s) {sorted(unknown)}")
        item_id = str(record.get("id") or "").strip()
        question = str(record.get("question") or "").strip()
        asked_by = str(record.get("asked_by") or "").strip()
        if not item_id or not question:
            raise EvalSetError(f"{where}: needs a non-empty id and question")
        if item_id in seen:
            raise EvalSetError(f"{where}: duplicate id")
        if asked_by not in SOURCES:
            raise EvalSetError(
                f"{where}: asked_by {asked_by!r} is not one of {sorted(SOURCES)}"
            )
        expected: list[Expected] = []
        for entry in record.get("expected") or ():
            if not isinstance(entry, dict):
                raise EvalSetError(f"{where}: an expected entry is not an object")
            extra = set(entry) - {"doc", "locator", "grade", "contains"}
            if extra:
                raise EvalSetError(f"{where}: expected entry has unknown key(s) {sorted(extra)}")
            doc = str(entry.get("doc") or "").strip()
            locator = str(entry.get("locator") or "").strip()
            grade = entry.get("grade", 2)
            if not doc or not locator:
                raise EvalSetError(f"{where}: an expected entry needs doc and locator")
            if grade not in GRADES:
                raise EvalSetError(f"{where}: grade {grade!r} is not one of {GRADES}")
            expected.append(
                Expected(
                    doc=doc,
                    locator=locator,
                    grade=int(grade),
                    contains=str(entry.get("contains") or "").strip(),
                )
            )
        seen.add(item_id)
        items.append(
            EvalItem(
                id=item_id,
                question=question,
                asked_by=asked_by,
                expected=tuple(expected),
                note=str(record.get("note") or "").strip(),
            )
        )
    if not items:
        raise EvalSetError(f"{path}: the set contains no questions")
    return EvalSet(name=name, items=tuple(items), about=about)


# --- Resolving expected locators against the corpus -------------------------


def _flat(text: str) -> str:
    """Comparison form for a `contains` check: case-folded, whitespace collapsed."""
    return " ".join((text or "").split()).casefold()


def _locator_matches(stored: str, wanted: str) -> bool:
    """Does a stored locator satisfy an expected one?

    Exact, or a **section prefix** at a boundary: `S20.1` covers `S20.1.2`, because a
    clause split across two chunks is still one clause to a reader. `S2` does **not**
    cover `S20.1` — the separator is required, or `S2` would match everything in the
    twenties and every locator in the set would resolve to something.
    """
    stored, wanted = _flat(stored), _flat(wanted)
    if not stored or not wanted:
        return False
    return stored == wanted or stored.startswith(wanted + ".") or stored.startswith(
        wanted + " "
    )


def _document_locators(standard_set) -> dict[int, tuple[str, str]]:
    """`{chunk id: (doc key, its locator)}` for every chunk in the set, in one query.

    The locator is rendered by `core.services._chatbot.locator_of` — one expression, one
    place. A copy here would let the instrument and the citation audit disagree about
    where a passage is, which is the class of defect that made the model's own citation
    of a correct answer fail on the live site (2026-10-22).
    """
    from core.services._chatbot import locator_of
    from knowledge.ingest import CORPUS_DOCUMENTS
    from knowledge.models import DocumentChunk

    key_by_title = {
        descriptor["title"]: key for key, descriptor in CORPUS_DOCUMENTS.items()
    }
    rows = DocumentChunk.objects.filter(
        document__standard_set=standard_set
    ).select_related("document")
    locators: dict[int, tuple[str, str]] = {}
    for row in rows:
        key = key_by_title.get(row.document.title)
        if key is None:
            # A document in the corpus that the eval set cannot name: the set would have
            # no way to grade a passage from it, and a typo'd title would look like a miss.
            raise EvalSetError(
                f"corpus document {row.document.title!r} has no CORPUS_DOCUMENTS key; "
                f"known titles: {sorted(key_by_title)}"
            )
        locators[row.pk] = (key, locator_of(row))
    return locators


def resolve(items, standard_set) -> dict[str, dict[int, set[int]]]:
    """Map every expected passage to the chunk ids that satisfy it.

    In:  `items` — eval items; `standard_set` — the ingested corpus.
    Out: `{item id: {index into item.expected: {chunk ids}}}`.
    Fails: `EvalSetError` listing **every** unresolvable locator at once.
    """
    locators = _document_locators(standard_set)
    texts = _chunk_texts(list(locators))
    resolved: dict[str, dict[int, set[int]]] = {}
    problems: list[str] = []
    for item in items:
        per_item: dict[int, set[int]] = {}
        for index, expected in enumerate(item.expected):
            wanted = _flat(expected.contains)
            matches = {
                chunk_id
                for chunk_id, (doc, locator) in locators.items()
                if doc == expected.doc
                and _locator_matches(locator, expected.locator)
                and (not wanted or wanted in texts[chunk_id])
            }
            if not matches:
                detail = f"doc={expected.doc!r} locator={expected.locator!r}"
                if expected.contains:
                    detail += f" contains={expected.contains!r}"
                problems.append(f"{item.id}: nothing resolves for {detail}")
            per_item[index] = matches
        resolved[item.id] = per_item
    if problems:
        raise EvalSetError(
            "the eval set names passages the ingested corpus does not have:\n  "
            + "\n  ".join(problems)
        )
    return resolved


def _chunk_texts(ids: list[int]) -> dict[int, str]:
    from knowledge.models import DocumentChunk

    if not ids:
        return {}
    return {
        pk: _flat(text)
        for pk, text in DocumentChunk.objects.filter(pk__in=ids).values_list("id", "text")
    }


# --- The corpus, described so a number can be re-checked --------------------


@dataclass(frozen=True)
class CorpusInfo:
    """What the numbers were measured against. A result without this is a rumour."""

    chunk_count: int
    digest: str
    documents: tuple[tuple[str, int], ...]

    def as_dict(self) -> dict:
        return {
            "chunk_count": self.chunk_count,
            "sha256": self.digest,
            "documents": dict(self.documents),
        }

    def line(self) -> str:
        per_doc = ", ".join(f"{key} {count}" for key, count in self.documents)
        return f"{self.chunk_count} chunks (sha256:{self.digest[:12]}) — {per_doc}"


def corpus_info(standard_set) -> CorpusInfo:
    """A digest of the corpus: the ingested bytes plus the chunk shape they produced.

    The document `sha256` alone would not notice a re-chunk (same PDF, different splits),
    and the chunk count alone would not notice a swapped file with the same shape. Both,
    plus the set's own chunk ids, is what lets a later reader tell whether the corpus moved
    since a recorded number (spike §7, "numbers quoted without provenance").
    """
    from knowledge.ingest import CORPUS_DOCUMENTS
    from knowledge.models import DocumentChunk

    key_by_title = {
        descriptor["title"]: key for key, descriptor in CORPUS_DOCUMENTS.items()
    }
    documents = list(
        standard_set.documents.order_by("kind", "title").values_list("title", "sha256")
    )
    counts: dict[str, int] = {}
    hasher = hashlib.sha256()
    for title, sha in documents:
        key = key_by_title.get(title, title)
        count = DocumentChunk.objects.filter(document__title=title).count()
        counts[key] = count
        hasher.update(f"{key}|{sha}|{count}\n".encode())
    total = DocumentChunk.objects.filter(document__standard_set=standard_set).count()
    hasher.update(f"total|{total}\n".encode())
    return CorpusInfo(
        chunk_count=total,
        digest=hasher.hexdigest(),
        documents=tuple(sorted(counts.items())),
    )
