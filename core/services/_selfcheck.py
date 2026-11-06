"""The public self-check — `/before-you-apply/` (D71, `SELF_CHECK_PRD`) — as rules, not pages.

What this module is for, in one sentence: **answer twenty questions without an account, get a mirror
back, and leave nothing behind unless you say so.** Everything here follows from that.

Three boundaries are deliberate, and each one is a place a view could otherwise decide something it
is not allowed to:

- **`evaluate()` never writes.** It is the function that makes "nothing is kept" true rather than
  promised: the result renders from the submitted answers in the same request, and the only writer is
  `submit()` — which returns `None` when the research box is unticked. `None` is a normal result.
- **The wording has two homes, and only two.** The eleven *derived* controls (the seven Sheet I §2
  records and the four Crops-sheet practices) take their question and their "why" from the **active
  Crops template's `self_check` markers** — so the front door and the farm visit cannot drift apart.
  The nine *own* controls (A1–A5, C5, D1, E1–E2) have no template question and live in
  `SELF_CHECK_ITEMS`, copied verbatim from the reviewed D71 ledger
  (`product/design/d71_self_check_questions.html`). C5 is an own control because FORM Sheet A asks it,
  not Sheet B.1 (`SELF_CHECK_PRD` §3.4's correction, 2026-11-05).
- **Nothing here is a verdict.** There is no score, no percentage, no `is_eligible`. `evaluate` counts
  out of a known denominator and names what is missing; the visit decides, and the two fixed lines
  come from `MISSING_RECORD_BLOCKS_FINALISE` — the same constant the visit's finalise gate will read
  (`MVP1A_PRD` §5.8). A page that grew its own copy of that promise could disagree with the gate, and
  the farmer would find out on the day.

**A consent is an act, never a default** (§3.6): both boxes are unticked by default, and the
demographic consent is *refused* without the research consent rather than quietly ignored. The
wording is `ConsentText` (data, versioned, draft until the group adopts it) and the act is a
timestamp on the report — not a `ConsentRecord`, which needs a `User` the visitor does not have and
must not be given by answering a questionnaire.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Mapping

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import (
    AssessmentTemplate,
    Category,
    ConsentPurpose,
    ConsentText,
    SelfCheckDemographic,
    SelfCheckReport,
)
from core.services._application import ConsentTextChangedError
from core.services._chat_guard import RateLimitedError, check_rate_limit
from core.services._public import FEE_BANDS
from core.services._selfcheck_items import (
    ANSWER_NO,
    ANSWER_PARTLY,
    ANSWER_RATHER_NOT_SAY,
    ANSWER_YES,
    CENSUS_AGE_BAND,
    CENSUS_DEMOGRAPHIC_GROUP,
    CENSUS_GENDER,
    CAVEAT_NOT_LIVE,
    CAVEAT_NOT_SEEDED,
    CAVEAT_NOT_WRITTEN,
    CAVEAT_OTHER_TICKED,
    DERIVED_CONTROLS,
    GROUPS,
    LAND_HISTORY_NOTES,
    SELF_CHECK_ITEMS,
    TEXT_ONLY_CITATIONS,
    TURNOVER_SKIP,
    Control,
    Group,
    Option,
)
from core.services._templates import NoActiveTemplateError, current_template
from core.templatetags.pgs_extras import format_zar

__all__ = [
    "ANSWER_NO",
    "ANSWER_PARTLY",
    "ANSWER_RATHER_NOT_SAY",
    "ANSWER_YES",
    "DERIVED_CONTROLS",
    "MISSING_RECORD_BLOCKS_FINALISE",
    "MISSING_RECORD_IS_A_RECORD_NOT_A_BLOCKER",
    "SELF_CHECK_ITEMS",
    "TEXT_ONLY_CITATIONS",
    "VISIT_DECIDES",
    "ConsentNotWrittenError",
    "DemographicConsentRequiredError",
    "MarkerMissingError",
    "ReportNotFoundError",
    "SelfCheckError",
    "UnknownCategoryError",
    "build_check",
    "check_submit_budget",
    "evaluate",
    "resolve_category",
    "submit",
    "withdraw",
]

# --- The finalise gate's own constant (C1 imports this, it does not restate it) -----------
#
# SELF_CHECK_PRD §3.2 is unusually specific about *where* these two sentences live: "the service
# that computes the result reads the same constant the visit's finalise gate uses for 'not a
# blocker'". A5 set the precedent with `assert_fees_paid_for_assessment` (a guard left waiting for
# its caller); this is the same move — the visit's finalise gate (C1/E) reads
# `MISSING_RECORD_BLOCKS_FINALISE` and the farmer's promise cannot fall behind it.

#: §5.8: a MISSING record is a recorded fact, not a blocker. What stops a visit is a *blank*
#: unanswered question. Flipping this to True is a policy change and turns the second fixed line
#: into a false statement, which is why the two are tested together.
MISSING_RECORD_BLOCKS_FINALISE = False

MISSING_RECORD_IS_A_RECORD_NOT_A_BLOCKER = (
    "A missing record does not stop an assessment. The visit records it, and you and the group "
    "agree what happens next."
)

#: The other fixed line. A promise about what the page is, not a reassurance: the page cannot decide
#: anything, and the sentence has to survive a future product owner reading it.
VISIT_DECIDES = (
    "The farm visit decides. This is only what your answers show, and the visit happens after you "
    "apply."
)

#: D31: the two thresholds the documents disagree about. **Shown, never resolved** — the group has
#: not settled it, and a page that picked one would be inventing policy.
LAND_HISTORY_DISAGREEMENT_LINE = (
    "The two documents disagree — 12 months and 18 months — and the group has not yet settled "
    "which applies. We will not tell you it is one number when it is not."
)


class SelfCheckError(Exception):
    """Base for everything a view must turn into a message, never a 500."""


class UnknownCategoryError(SelfCheckError):
    """A category key that is not a seeded row. A typo, not an empty questionnaire."""


class ConsentNotWrittenError(SelfCheckError):
    """No research wording exists for this deployment, so no consent can be recorded.

    Fails closed, exactly as A6's account does: a checkbox with no text behind it records agreement
    to nothing.
    """


class DemographicConsentRequiredError(SelfCheckError):
    """Demographic consent without research consent (§3.6). Refused, not silently dropped."""


class MarkerMissingError(SelfCheckError):
    """A derived control names a template key the questionnaire does not carry.

    A deployment fault, and it must be loud: the alternative is a front door that silently shows
    nineteen controls while the visit asks twenty.
    """


class ReportNotFoundError(SelfCheckError):
    """No report for that reference — already withdrawn, or never written."""


# --- The frozen results --------------------------------------------------------------------


@dataclass(frozen=True)
class GroupCount:
    key: str
    title: str
    in_place: int
    answered: int
    total: int


@dataclass(frozen=True)
class Citation:
    """Where a to-do item comes from. `TEXT_ONLY` is declared, never a shrug (§D68)."""

    kind: str  # "TEXT_ONLY" | "CLAUSE"
    label: str = ""
    anchor: str = ""


@dataclass(frozen=True)
class TodoItem:
    key: str
    framing: str
    title: str
    citation: Citation


@dataclass(frozen=True)
class FeeBandNote:
    label: str
    note: str


@dataclass(frozen=True)
class SelfCheckForm:
    """The questions, in order, with each control's reviewed wording (§4.2's contract)."""

    category: Category | None
    groups: tuple[Group, ...]
    caveat: str
    research_consent: ConsentText | None
    demographic_consent: ConsentText | None

    @property
    def controls(self) -> tuple[Control, ...]:
        return tuple(control for group in self.groups for control in group.controls)

    @property
    def research_version(self) -> str:
        return self.research_consent.version if self.research_consent else ""


@dataclass(frozen=True)
class SelfCheckResult:
    """What the page shows. Frozen, counted, and never a verdict (§3.1)."""

    mirror: str
    groups: tuple[GroupCount, ...]
    records_in_place: int
    records_missing: int
    records_not_said: int
    todo: tuple[TodoItem, ...]
    land_history_note: str
    land_history_disagreement: str
    fee_band: FeeBandNote | None
    caveat: str
    fixed_lines: dict[str, str]


# --- Building the check --------------------------------------------------------------------


def _markers(template: AssessmentTemplate) -> dict[str, dict[str, Any]]:
    """Every node in the frozen schema carrying a `self_check` block, keyed by its own key."""
    found: dict[str, dict[str, Any]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "self_check" in node and isinstance(node.get("key"), str):
                found[node["key"]] = node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(template.schema)
    return found


def _category_options() -> tuple[Option, ...]:
    """A1's ticks are the group's **active** categories — data, never a hardcoded four."""
    return tuple(
        Option(category.code, category.label)
        for category in Category.objects.filter(is_active=True).order_by("display_order", "code")
    )


def build_check(category: str = "CROPS") -> SelfCheckForm:
    """The questions a visitor sees, resolved from data and the active template.

    In:  `category` — one of the seeded `Category` keys.
    Out: a frozen `SelfCheckForm`: five groups, the controls in order, each derived control's
         `why` and `template_text`, and the two consent texts.
    Side Effects: reads (`Category`, the active template, up to three `ConsentText` rows).
    Fails: `UnknownCategoryError` when the deployment **has** categories and this key is not one
         of them (a typo); `MarkerMissingError` when the template is live but a named marker is
         absent.

    A deployment with **no** categories seeded at all renders a shell instead of raising: every other
    public page renders with nothing published (`/documents/` with no rows is normal), and a fresh
    checkout that 500s on a public route is a worse first impression than an honest empty one.
    """
    row = Category.objects.filter(code=category).first()
    if row is None and Category.objects.exists():
        raise UnknownCategoryError(f"no category {category!r} in this deployment")

    caveat = ""
    template: AssessmentTemplate | None = None
    if row is None:
        caveat = CAVEAT_NOT_SEEDED
    else:
        try:
            template = current_template(row)
        except NoActiveTemplateError:
            caveat = (
                CAVEAT_NOT_LIVE
                if AssessmentTemplate.objects.filter(category=row).exists()
                else CAVEAT_NOT_WRITTEN.format(label=row.label)
            )

    markers = _markers(template) if template is not None else {}
    own = {control.key: control for control in SELF_CHECK_ITEMS}
    own["A1"] = dataclasses.replace(own["A1"], options=_category_options())

    derived: list[Control] = []
    for spec in DERIVED_CONTROLS:
        marker = markers.get(spec.template_key)
        if marker is None:
            if template is not None:
                raise MarkerMissingError(
                    f"{spec.key} resolves {spec.template_key!r}, which the active "
                    f"{row.code} template does not carry — the front door and the visit disagree"
                )
            continue
        derived.append(
            dataclasses.replace(
                spec,
                why=marker["self_check"]["why"],
                template_text=marker["text"],
            )
        )

    by_key = {control.key: control for control in list(own.values()) + derived}
    groups = tuple(
        Group(
            key=key,
            title=title,
            lede=lede,
            controls=tuple(
                by_key[control.key]
                for control in (*SELF_CHECK_ITEMS,) + DERIVED_CONTROLS
                if control.group == key and control.key in by_key
            ),
        )
        for key, title, lede in GROUPS
    )
    return SelfCheckForm(
        category=row,
        groups=groups,
        caveat=caveat,
        research_consent=ConsentText.objects.current(ConsentPurpose.RESEARCH),
        demographic_consent=ConsentText.objects.current(ConsentPurpose.DEMOGRAPHICS),
    )


def resolve_category(answers: Mapping[str, Any]) -> str:
    """Which questionnaire the answers are about: Crops when ticked, else the first tick (§3.1)."""
    ticked = _as_list(answers.get("A1"))
    if "CROPS" in ticked or not ticked:
        return "CROPS"
    return ticked[0]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [str(item) for item in value if str(item)]


# --- Evaluate: the mirror, and nothing else ----------------------------------------------


def _citation_for(control: Control) -> Citation:
    if control.source in TEXT_ONLY_CITATIONS:
        return Citation(kind="TEXT_ONLY", label=control.source)
    return Citation(kind="CLAUSE", label=control.source, anchor=control.source)


def _group_counts(check: SelfCheckForm, answers: Mapping[str, Any]) -> tuple[GroupCount, ...]:
    counts = []
    for group in check.groups:
        answered = 0
        in_place = 0
        for control in group.controls:
            answer = answers.get(control.key)
            if not answer:
                continue
            answered += 1
            if control.kind == "RECORD" and answer in (ANSWER_YES, ANSWER_PARTLY):
                in_place += 1
        counts.append(
            GroupCount(group.key, group.title, in_place, answered, len(group.controls))
        )
    return tuple(counts)


def evaluate(
    answers: Mapping[str, Any], *, check: SelfCheckForm | None = None
) -> SelfCheckResult:
    """Turn answered values into the mirror, the to-do list and the two published facts.

    In:  `answers` — the posted values, already validated by the form; `check` — the resolved
         question set when the caller already has it (the view does).
    Out: a frozen `SelfCheckResult`.
    Side Effects: none. **Never writes** — this is what makes "nothing is kept" true.
    Fails: nothing. An unanswered control is omitted, never an exception (§4.2).
    """
    if check is None:
        check = build_check(resolve_category(answers))

    controls = check.controls
    records = [control for control in controls if control.kind == "RECORD"]
    held = {control.key: answers.get(control.key) for control in records}
    in_place = sum(1 for answer in held.values() if answer in (ANSWER_YES, ANSWER_PARTLY))
    missing = sum(1 for answer in held.values() if answer == ANSWER_NO)
    not_said = sum(1 for answer in held.values() if answer == ANSWER_RATHER_NOT_SAY)

    mirror = (
        f"Of the seven records a visit checks, your answers show <b>{in_place} in place</b>."
    )
    if not_said:
        mirror += (
            f" {not_said} of them you would rather not say — the visit will still ask, and that "
            "is your call."
        )
    if missing == 0 and not_said == 0 and in_place == len(records):
        mirror += " Nothing on this list. Every record the visit checks is one you say you hold."

    todo = tuple(
        TodoItem(
            key=control.key,
            framing=(
                "Partly there" if held[control.key] == ANSWER_PARTLY else "Not yet in place"
            ),
            title=control.short,
            citation=_citation_for(control),
        )
        for control in records
        if held[control.key] in (ANSWER_NO, ANSWER_PARTLY)
    )

    land_band = answers.get("A4") or ""
    land_note = LAND_HISTORY_NOTES.get(land_band, "")

    fee_note = None
    declared = answers.get("A5") or ""
    if declared and declared != TURNOVER_SKIP:
        band = next((candidate for candidate in FEE_BANDS if candidate.label == declared), None)
        if band is not None:
            fee_note = FeeBandNote(
                label=band.label,
                note=(
                    f"On the band you declared — <b>{band.label}</b> — the assessment fee is "
                    f"<b>{format_zar(band.initial_cents)}</b> for an initial assessment."
                ),
            )

    caveat = check.caveat
    ticked = _as_list(answers.get("A1"))
    if not caveat and len(ticked) > 1:
        caveat = CAVEAT_OTHER_TICKED

    return SelfCheckResult(
        mirror=mirror,
        groups=_group_counts(check, answers),
        records_in_place=in_place,
        records_missing=missing,
        records_not_said=not_said,
        todo=todo,
        land_history_note=land_note,
        land_history_disagreement=LAND_HISTORY_DISAGREEMENT_LINE,
        fee_band=fee_note,
        caveat=caveat,
        fixed_lines={
            "visit_decides": VISIT_DECIDES,
            "missing_record": MISSING_RECORD_IS_A_RECORD_NOT_A_BLOCKER,
        },
    )


# --- Submit: the only writer --------------------------------------------------------------


def _report_fields(
    answers: Mapping[str, Any], check: SelfCheckForm
) -> dict[str, Any]:
    """The columns a report keeps, from the answers. Bands as labels; answers as codes."""
    ticked = _as_list(answers.get("A1"))
    # A tick is not an application: the FK is the category the check was *about*, and only when
    # the visitor actually ticked it. An unticked A1 leaves both columns empty rather than guessing.
    primary = check.category if check.category and check.category.code in ticked else None
    return {
        "category": primary,
        "other_categories": [code for code in ticked if code != (primary.code if primary else None)],
        "hectares_band": answers.get("A2") or "",
        "pasture_band": answers.get("A3") or "",
        "land_history_band": answers.get("A4") or "",
        "turnover_band": answers.get("A5") or "",
        "records_held": {
            control.key: answers[control.key]
            for control in check.controls
            if control.kind == "RECORD" and answers.get(control.key)
        },
        "practices": {
            control.key: answers[control.key]
            for control in check.controls
            if control.kind == "SINGLE" and control.group == "C" and answers.get(control.key)
        },
        "exit_reason": answers.get("D1") or "",
        "exit_note": (answers.get("D1_note") or "")[:280],
    }


_DEMOGRAPHIC_FIELDS = ("census_gender", "census_age_band", "census_demographic_group")


def submit(
    answers: Mapping[str, Any],
    *,
    research_consent: bool,
    demographic_consent: bool,
    demographic: Mapping[str, str] | None = None,
    check: SelfCheckForm | None = None,
) -> SelfCheckReport | None:
    """Write the report — only when research consent was given.

    In:  `answers` — validated form values; the two consents as acts; the census values, if given.
    Out: the `SelfCheckReport` written, or **None** when no consent was given. `None` is a normal,
         expected result and the page renders from the answers in the same request.
    Side Effects: one INSERT, plus one `SelfCheckDemographic` when the second consent was given.
    Fails: `DemographicConsentRequiredError` (demographic without research); `ConsentNotWrittenError`
         (no wording to consent to); `ConsentTextChangedError` (the wording changed under the form).
    Idempotency: not required — a single browser POST, no queue.
    """
    if demographic_consent and not research_consent:
        raise DemographicConsentRequiredError(
            "The census details can only be counted as part of the research totals, so that "
            "consent has to be given first."
        )
    if not research_consent:
        return None

    text = ConsentText.objects.current(ConsentPurpose.RESEARCH)
    if text is None:
        raise ConsentNotWrittenError(
            "The wording for counting answers has not been written for this group yet, so there is "
            "nothing to consent to and nothing is stored."
        )
    if (answers.get("consent_version") or "") != text.version:
        raise ConsentTextChangedError(
            "The consent wording changed while this page was open. Please read it again and "
            "re-confirm."
        )

    if check is None:
        check = build_check(resolve_category(answers))
    fields = _report_fields(answers, check)

    with transaction.atomic():
        report = SelfCheckReport.objects.create(
            research_consent_at=timezone.now(),
            consent_text_version=text.version,
            **fields,
        )
        if demographic_consent:
            values = {
                name: (demographic or {}).get(name, "")[:64] for name in _DEMOGRAPHIC_FIELDS
            }
            SelfCheckDemographic.objects.create(report=report, **values)
    return report


@transaction.atomic
def withdraw(public_uuid) -> None:
    """Delete one visitor's report and, by cascade, their census answer set.

    In: `public_uuid` — the reference the visitor kept.
    Out: None.
    Side Effects: one DELETE (the demographic row cascades). **No tombstone**: the consent promises
         deletion, and a tombstone would itself be the personal data.
    Fails: `ReportNotFoundError` — a second withdrawal is not a crash.
    """
    report = SelfCheckReport.objects.filter(public_uuid=public_uuid).first()
    if report is None:
        raise ReportNotFoundError("no report with that reference — it may already be withdrawn")
    report.delete()


# --- The per-IP budget (§4.4) -------------------------------------------------------------


def check_submit_budget(ip_hash: str, *, now: float | None = None) -> None:
    """Count one submission against the client's budget, using `/ask/`'s mechanism.

    In:  `ip_hash` — sha256 of the client IP (never the address); `now` — injectable clock.
    Out: None.
    Side Effects: one cache increment.
    Fails: `RateLimitedError` when the budget is spent. A public form that writes to a research
         table is worth spamming: a bot can make "70% of prospective farmers lack sales records"
         false about a catchment of a few dozen farms.
    """
    check_rate_limit(
        ip_hash,
        now=now,
        namespace="selfcheck",
        limit=int(getattr(settings, "SELF_CHECK_RATE_LIMIT", 5)),
        window=int(getattr(settings, "SELF_CHECK_RATE_WINDOW_SECONDS", 3600)),
    )
