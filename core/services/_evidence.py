"""Rebuilding a turn's evidence links after a `--force` re-ingest.

**The problem this closes.** `ingest_standard --force` deletes the document and its chunks
inside one transaction, and `ChatMessage.retrieved_chunks` cascades with them: every
historical answer loses the rows that say what it stood on. The `grounding` snapshot
(migration `core/0006`, plan P2.5a) was added so the *record* survives; this service is the
other half — it turns that snapshot back into links **where the passage is unchanged**, and
names the ones where it cannot. `HANDOVER.md` §17 records the cost that made this necessary
("`--force` stays out of `deploy.sh` — it destroys every `ChatMessage.retrieved_chunks`
trail"), and the SAOSO corpus work (`BugFixes/saoso_text_glyphs_and_boundaries.md` §2–§5)
needs more than one re-ingest.

**Why a sha and not a locator.** 30 Appendix 2 rows share `section_ref="Appendix 2"`, so a
locator-only match would attach *cardboard* to *Farmyard manure* — precisely the defect
D68 Q8 fixed in the reader, reintroduced by the repair tool. The match is
`(document title, locator, text sha)`, where the sha is the same 16 hex characters
`_grounding_snapshot` wrote.

**Why a changed passage is left unlinked.** Re-pointing a link at different words turns a
stale link into a *wrong* one that resolves — `build_principles.md` §I forbids exactly that
("a wrong answer that looks right is worse than a link that fails"). The three letterspaced
lines and the `m²` superscript are passages whose text the corpus work is about to change,
so this case is the normal one, not an edge case: it is reported, and the snapshot remains
the record.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.models import ChatMessage
from core.services._chatbot import locator_of, text_sha
from knowledge.models import DocumentChunk

#: A snapshot entry matched a locator, but no chunk there holds that text any more.
TEXT_CHANGED = "text changed"

#: The document no longer prints that locator at all (a section the artefact removed).
GONE = "gone"


class NothingToRelink(RuntimeError):
    """No assistant turns on this instance — almost certainly not the database you meant.

    Raised rather than returning a zero report: "relinked 0" is indistinguishable from
    "there was nothing to relink", which is the silent-green shape `testing_hazards.md`
    §1.6 exists to prevent.
    """


@dataclass(frozen=True)
class UnresolvedPassage:
    """A snapshot entry this run could not turn back into a link, and why."""

    message_id: int
    locator: str
    document: str
    reason: str


@dataclass(frozen=True)
class RelinkReport:
    """What the run found. `written` is False for the default, report-only mode."""

    written: bool = False
    examined: int = 0
    without_snapshot: int = 0
    relinked: int = 0
    already_linked: int = 0
    unresolved: tuple[UnresolvedPassage, ...] = ()

    @property
    def text_changed(self) -> int:
        return sum(1 for passage in self.unresolved if passage.reason == TEXT_CHANGED)

    @property
    def gone(self) -> int:
        return sum(1 for passage in self.unresolved if passage.reason == GONE)

    @property
    def pending(self) -> int:
        """Links this run would write (or did, when `written`)."""
        return self.relinked


@dataclass(frozen=True)
class _Passage:
    """One stored chunk as the snapshot describes it."""

    pk: int
    locator: str
    sha: str
    page: int | None


def _index_by_document() -> dict[str, list[_Passage]]:
    """Every chunk in the corpus, keyed by document title. One query.

    Whole corpus, not one document: a message's snapshot names the document, and a run
    must be able to relink turns from all four at once. 366 rows is one query and a few
    milliseconds; narrowing it would need the snapshot scanned twice.
    """
    index: dict[str, list[_Passage]] = {}
    for chunk in DocumentChunk.objects.select_related("document").iterator():
        index.setdefault(chunk.document.title, []).append(
            _Passage(
                pk=chunk.pk,
                locator=locator_of(chunk),
                sha=text_sha(chunk.text),
                page=chunk.page,
            )
        )
    return index


def _match(entry: dict, passages: list[_Passage]) -> _Passage | None:
    """The passage a snapshot entry names: same locator **and** same text.

    The page is a tiebreak, not a criterion: a rebuild may legitimately move a passage to
    another page while its words are unchanged, and the sha is the stronger fact. Two
    passages that share locator and sha hold identical text, so either is the passage.
    """
    same_locator = [passage for passage in passages if passage.locator == entry.get("locator")]
    same_text = [passage for passage in same_locator if passage.sha == entry.get("text_sha")]
    if not same_text:
        return None
    return next(
        (passage for passage in same_text if passage.page == entry.get("page")), same_text[0]
    )


def relink_evidence(*, write: bool = False) -> RelinkReport:
    """In: `write` — apply the links, or only report them.

    Out: a `RelinkReport` — how many turns were examined, how many passages were relinked,
    already linked, or cannot be (with the reason and the locator for each).
    Side effects: with `write`, adds `ChatMessage.retrieved_chunks` rows; never removes one.
    Fails: `NothingToRelink` when the instance has no assistant turns.
    Idempotent: a second run finds every passage already linked and writes nothing.
    """
    turns = ChatMessage.objects.filter(role=ChatMessage.Role.ASSISTANT).order_by("id")
    if not turns.exists():
        raise NothingToRelink(
            "no assistant turns on this instance: there is no chat evidence to relink. "
            "Check DATABASE_URL before assuming the command did its job."
        )

    passages = _index_by_document()
    examined = without_snapshot = relinked = already_linked = 0
    unresolved: list[UnresolvedPassage] = []

    for message in turns.iterator():
        examined += 1
        snapshot = message.grounding or []
        if not snapshot:
            without_snapshot += 1
            continue

        linked = set(message.retrieved_chunks.values_list("pk", flat=True))
        to_add: list[int] = []
        for entry in snapshot:
            match = _match(entry, passages.get(entry.get("document", ""), []))
            if match is None:
                same_locator = any(
                    passage.locator == entry.get("locator")
                    for passage in passages.get(entry.get("document", ""), [])
                )
                unresolved.append(
                    UnresolvedPassage(
                        message_id=message.pk,
                        locator=entry.get("locator", ""),
                        document=entry.get("document", ""),
                        reason=TEXT_CHANGED if same_locator else GONE,
                    )
                )
                continue
            if match.pk in linked:
                already_linked += 1
                continue
            linked.add(match.pk)
            to_add.append(match.pk)
            relinked += 1

        if write and to_add:
            message.retrieved_chunks.add(*to_add)

    return RelinkReport(
        written=write,
        examined=examined,
        without_snapshot=without_snapshot,
        relinked=relinked,
        already_linked=already_linked,
        unresolved=tuple(unresolved),
    )


def render_relink_report(report: RelinkReport) -> str:
    """Out: the lines an operator reads. No colour, no globbing: it is often piped to a log."""
    verb = "relinked" if report.written else "relinkable"
    lines = [
        f"{report.examined} assistant turn(s) examined; "
        f"{report.without_snapshot} with no grounding snapshot (nothing to relink)",
        f"{report.relinked} passage(s) {verb}; {report.already_linked} already linked",
        f"{report.text_changed} passage(s) with the same locator but different text "
        f"(left unlinked on purpose); {report.gone} passage(s) the document no longer has",
    ]
    if report.unresolved:
        lines.append("")
        lines.append("unresolved:")
        for passage in report.unresolved[:20]:
            lines.append(
                f"  message #{passage.message_id}  {passage.document} · {passage.locator or '(no locator)'}"
                f"  — {passage.reason}"
            )
        if len(report.unresolved) > 20:
            lines.append(f"  … and {len(report.unresolved) - 20} more")
    if report.relinked and not report.written:
        lines.append("")
        lines.append("Nothing was written. Re-run with --apply to restore the links.")
    return "\n".join(lines)
