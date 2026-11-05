"""Assessment templates: the schema, and the validator that keeps it honest.

A template is **JSON data imported by a file**, never code (spec §4.8, D28): a new standard's
questionnaire, a corrected FORM, or a second category is a new file and a `load_template` run.
`Assessment.template_schema` freezes a full copy at visit creation, so a template edit can never
alter a past assessment — which is also why the validator here is strict about *keys*: a key is what
an answer is stored against, and a key that changes silently orphans the answers that used it.

The grammar the plan fixes (and this module implements) is:

    <prefix>.V<nn><suffix?>      a verdict, e.g. `crops.V04`, and `crops.V32b` for the FORM's
                                 one printed-twice verdict (Q31 and Q32 both print "V32")
    <prefix>.Q<n>(.<m>)?         a question or a numbered sub-item, e.g. `crops.Q4.2`
    <prefix>.V<nn>.<a-z>         a *child* of a verdict, e.g. `crops.V04.a`

The third form is why the validator has a pattern the B1 regex in the plan does not: B3's own example
of a structured sub-verdict is `{"key": "crops.V04.a", …}`, and `^[a-z_]+\\.(V\\d{2}[a-z]?|Q\\d+(\\.\\d+)?)$`
cannot match it. A child is validated against its parent instead of against the top-level grammar, and
a child may never also exist as its own verdict row (the 37-row completeness invariant counts parents).

**Everything is reported, not the first thing.** `validate_schema` returns a list; `load_template`
prints all of it and exits non-zero. An author correcting a 38-question file one error per run is an
author who stops reading the messages.
"""

from __future__ import annotations

import re
from typing import Any

from django.db import transaction

from core.models import AssessmentTemplate, Category

#: The only schema version this code understands. A later version is a code change *and* a file,
#: deliberately: silently accepting an unknown version is how a renderer meets a key it cannot draw.
SCHEMA_VERSION = 1

#: `<prefix>.(V..|Q..|R..)`, the grammar B1 fixes, plus `R` for a Sheet I §2 record check.
#: The `R` branch is not in B1's regex because B1 predates the records' home: D71 and `SELF_CHECK_PRD`
#: §3.4 make the seven record checks template data (they are what a `RecordCheck` is verified
#: against), so they need keys, and `R01`.. is the only shape that cannot collide with a question.
KEY_PATTERN = re.compile(r"^(?P<prefix>[a-z_]+)\.(?P<body>V\d{2}[a-z]?|Q\d+(?:\.\d+)?|R\d{2})$")
QUESTION_BODY = re.compile(r"^Q(?P<ref>\d+(?:\.\d+)?)$")
RECORD_BODY = re.compile(r"^R(?P<index>\d{2})$")
VERDICT_REF = re.compile(r"^V\d{2}$")
CHILD_KEY_PATTERN = re.compile(
    r"^(?P<parent>[a-z_]+\.V\d{2}[a-z]?)\.(?P<letter>[a-z])$"
)

#: FORM's two roles. `BOTH` exists because some cells are filled in with the farmer during the visit
#: rather than by one side alone, and a renderer that had to guess would show the wrong half.
RESPONDENTS = ("FARMER", "ASSESSOR", "BOTH")

#: The control types a renderer exists for. Adding one is a deliberate edit here **and** a renderer;
#: a type this list does not name is a question nobody can answer.
QUESTION_TYPES = ("TEXT", "TEXTAREA", "YES_NO", "NUMBER", "CHOICE", "LIST", "DATE")

#: D27: polarity is template data, and these are the three the FORM's verdicts actually take.
#: `INFORMATIONAL` is V3's ("Is there need for a transition period?"): answering it neither passes
#: nor fails a farm, and scoring it would invent a judgement the FORM does not make.
POLARITIES = ("POSITIVE", "NEGATIVE", "INFORMATIONAL")

#: D71 / `SELF_CHECK_PRD` §4.6: a `self_check` marker is `{"tier": 1, "why": "…"}` and nothing else.
#: The closed key set is what stops a typo'd `whyy` from becoming copy that renders empty on the
#: front door; `tier` is 1 only because a second tier is a decision, not a default.
SELF_CHECK_KEYS = frozenset({"tier", "why"})
SELF_CHECK_TIERS = (1,)


class SchemaValidationError(Exception):
    """A template file that must not be loaded. Carries **every** problem, not the first.

    `load_template` prints `problems` and exits non-zero; it never writes a template it could not
    validate, because a partially valid questionnaire is worse than none — the visit would capture
    answers against a shape nobody agreed to.
    """

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__(
            f"{len(self.problems)} schema problem(s): " + "; ".join(self.problems[:3])
            + ("…" if len(self.problems) > 3 else "")
        )


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_self_check(block: Any, path: str, problems: list[str]) -> None:
    """D71's marker: exactly `tier` and `why`, tier 1, and a `why` that says something."""
    if not isinstance(block, dict):
        problems.append(f"{path}: self_check must be an object with 'tier' and 'why'")
        return
    unknown = set(block) - SELF_CHECK_KEYS
    if unknown:
        problems.append(
            f"{path}: self_check has unknown key(s) {sorted(unknown)} — "
            f"only {sorted(SELF_CHECK_KEYS)} are allowed"
        )
    missing = SELF_CHECK_KEYS - set(block)
    if missing:
        problems.append(f"{path}: self_check is missing {sorted(missing)}")
    if block.get("tier") not in SELF_CHECK_TIERS:
        problems.append(
            f"{path}: self_check.tier must be one of {list(SELF_CHECK_TIERS)}, "
            f"got {block.get('tier')!r}"
        )
    if "why" in block and not _text(block.get("why")):
        problems.append(f"{path}: self_check.why must be a sentence, not empty")


def _validate_options(value: Any, path: str, problems: list[str], *, required: bool) -> None:
    if value is None and not required:
        return
    if not isinstance(value, list) or not value or not all(_text(option) for option in value):
        problems.append(f"{path}: options must be a non-empty list of strings")


def _validate_question(
    question: Any, path: str, prefix: str, problems: list[str], seen: dict[str, str],
    *, nested: bool = False,
) -> None:
    if not isinstance(question, dict):
        problems.append(f"{path}: a question must be an object")
        return

    key = question.get("key")
    if not isinstance(key, str):
        problems.append(f"{path}.key: missing")
    else:
        match = KEY_PATTERN.match(key)
        if not match:
            problems.append(
                f"{path}.key: {key!r} does not match <prefix>.Q<n>[.<m>] "
                "(lower-case prefix, `Q`, digits)"
            )
        else:
            if key in seen:
                problems.append(f"{path}.key: duplicate key {key!r} (already used at {seen[key]})")
            else:
                seen[key] = path
            key_prefix = match.group("prefix")
            if prefix and key_prefix != prefix:
                problems.append(
                    f"{path}.key: prefix {key_prefix!r} differs from the template's {prefix!r} — "
                    "one template is one category"
                )
            body = QUESTION_BODY.match(match.group("body"))
            ref = question.get("ref")
            if body is None:
                problems.append(f"{path}.key: {key!r} is a verdict key, not a question key")
            elif _text(ref) and key != f"{key_prefix}.Q{ref}":
                problems.append(
                    f"{path}.key: {key!r} disagrees with its ref {ref!r} — "
                    f"expected {key_prefix + '.Q' + str(ref)!r}"
                )

    if not _text(question.get("ref")):
        problems.append(f"{path}.ref: missing")

    # A numbered question is a **container** for the printed sub-items (4.1, 4.2, …): the FORM's
    # "Question 4" is a heading, and the answerable things are its items. A container therefore
    # need not carry `text`/`respondent`/`type` itself, but everything it holds must; an item may
    # not hold items, because the FORM has exactly one level of numbering.
    items = question.get("items")
    if items is not None:
        if not isinstance(items, list) or not items:
            problems.append(f"{path}.items: must be a non-empty list or omitted")
        elif nested:
            problems.append(f"{path}.items: an item may not itself hold items (one level of numbering)")
        else:
            for index, item in enumerate(items):
                _validate_question(
                    item, f"{path}.items[{index}]", prefix, problems, seen, nested=True
                )
    elif nested or _text(question.get("text")):
        if not _text(question.get("text")):
            problems.append(f"{path}.text: missing — an item with no wording cannot be asked")
        if question.get("respondent") not in RESPONDENTS:
            problems.append(
                f"{path}.respondent: must be one of {list(RESPONDENTS)}, "
                f"got {question.get('respondent')!r}"
            )
        qtype = question.get("type")
        if qtype not in QUESTION_TYPES:
            problems.append(
                f"{path}.type: must be one of {list(QUESTION_TYPES)}, got {qtype!r}"
            )
        if qtype == "CHOICE":
            _validate_options(question.get("options"), f"{path}.options", problems, required=True)
    else:
        problems.append(
            f"{path}: a question needs `text`, `respondent` and `type`, or an `items` list"
        )

    if "attachments" in question:
        attachments = question.get("attachments")
        if not isinstance(attachments, list) or not all(_text(item) for item in attachments):
            problems.append(f"{path}.attachments: must be a list of strings")
    if "links_to" in question and not _text(question.get("links_to")):
        problems.append(f"{path}.links_to: must be a form name, e.g. 'INPUT_REGISTER'")
    if "standard_ref" in question and question["standard_ref"] is not None:
        if not _text(question["standard_ref"]):
            problems.append(f"{path}.standard_ref: must be a clause or null, not an empty string")
    if "self_check" in question:
        _validate_self_check(question["self_check"], path, problems)


def _validate_child(
    child: Any, path: str, parent_key: str, problems: list[str], seen: dict[str, str]
) -> None:
    """A printed child row of a verdict: `crops.V04.a`, with its own polarity and options."""
    if not isinstance(child, dict):
        problems.append(f"{path}: a sub-question must be an object")
        return
    key = child.get("key")
    if not isinstance(key, str):
        problems.append(f"{path}.key: missing")
    else:
        match = CHILD_KEY_PATTERN.match(key)
        if not match:
            problems.append(
                f"{path}.key: {key!r} does not match <parent verdict key>.<a-z> (e.g. crops.V04.a)"
            )
        else:
            if key in seen:
                problems.append(f"{path}.key: duplicate key {key!r} (already used at {seen[key]})")
            else:
                seen[key] = path
            if parent_key and match.group("parent") != parent_key:
                problems.append(
                    f"{path}.key: {key!r} belongs to {match.group('parent')!r}, "
                    f"not to its parent {parent_key!r}"
                )
    if not _text(child.get("text")):
        problems.append(f"{path}.text: missing")
    if child.get("polarity") not in POLARITIES:
        problems.append(
            f"{path}.polarity: must be one of {list(POLARITIES)}, got {child.get('polarity')!r}"
        )
    if "options" in child:
        _validate_options(child.get("options"), f"{path}.options", problems, required=True)
    if "required" in child and not isinstance(child["required"], bool):
        problems.append(f"{path}.required: must be true or false")


def _validate_verdict(
    verdict: Any, path: str, prefix: str, problems: list[str], seen: dict[str, str]
) -> None:
    if not isinstance(verdict, dict):
        problems.append(f"{path}: a verdict must be an object")
        return

    key = verdict.get("key")
    if not isinstance(key, str):
        problems.append(f"{path}.key: missing")
    else:
        match = KEY_PATTERN.match(key)
        if not match:
            problems.append(
                f"{path}.key: {key!r} does not match <prefix>.V<nn>[a-z?] (lower-case prefix, `V`+2 digits)"
            )
        else:
            if key in seen:
                problems.append(f"{path}.key: duplicate key {key!r} (already used at {seen[key]})")
            else:
                seen[key] = path
            key_prefix = match.group("prefix")
            if prefix and key_prefix != prefix:
                problems.append(
                    f"{path}.key: prefix {key_prefix!r} differs from the template's {prefix!r} — "
                    "one template is one category"
                )
            if QUESTION_BODY.match(match.group("body")):
                problems.append(f"{path}.key: {key!r} is a question key, not a verdict key")
            ref = verdict.get("ref")
            if _text(ref) and not key.startswith(f"{key_prefix}.{ref}"):
                problems.append(
                    f"{path}.key: {key!r} disagrees with its ref {ref!r} — "
                    f"expected {key_prefix + '.' + str(ref)!r} (optionally with a letter suffix)"
                )

    if not _text(verdict.get("ref")):
        problems.append(f"{path}.ref: missing")
    elif not VERDICT_REF.match(verdict["ref"]):
        problems.append(f"{path}.ref: must be 'V' plus two digits, got {verdict['ref']!r}")
    if not _text(verdict.get("text")):
        problems.append(f"{path}.text: missing — the assessor is answering this sentence")
    if verdict.get("polarity") not in POLARITIES:
        problems.append(
            f"{path}.polarity: must be one of {list(POLARITIES)}, got {verdict.get('polarity')!r} "
            "— a verdict with no polarity cannot be scored, and guessing one invents a judgement"
        )
    if "standard_ref" in verdict and verdict["standard_ref"] is not None:
        if not _text(verdict["standard_ref"]):
            problems.append(f"{path}.standard_ref: must be a clause or null, not an empty string")
    question_ref = verdict.get("question_ref")
    if question_ref is not None and not (
        isinstance(question_ref, str) and question_ref.isdigit()
    ):
        problems.append(
            f"{path}.question_ref: must be the numbered question's ref as a string, "
            f"e.g. \"4\", got {question_ref!r}"
        )
    if "guidance" in verdict and not _text(verdict.get("guidance")):
        problems.append(f"{path}.guidance: must be the FORM's own note, not an empty string")
    if "self_check" in verdict:
        _validate_self_check(verdict["self_check"], path, problems)
    if "sub_questions" in verdict:
        children = verdict["sub_questions"]
        if not isinstance(children, list) or not children:
            problems.append(f"{path}.sub_questions: must be a non-empty list or omitted")
        else:
            for index, child in enumerate(children):
                _validate_child(
                    child, f"{path}.sub_questions[{index}]",
                    key if isinstance(key, str) else "", problems, seen,
                )


def validate_schema(schema: Any) -> list[str]:
    """Every problem in a template schema, in document order. `[]` means loadable.

    In:  `schema` — the parsed JSON, as any type; a non-object is reported, not raised.
    Out: a list of human-readable problems, each naming its path
         (`verdicts[12].polarity`), so an author can fix the file rather than the first error.
    Side Effects: none. No database, no settings — `load_template` validates before it writes,
         and this file's tests run without a template existing.
    Fails: never. A caller that must not proceed uses `assert_valid_schema`.
    """
    problems: list[str] = []
    if not isinstance(schema, dict):
        return [f"the schema must be an object (a dict), not {type(schema).__name__}"]

    if schema.get("schema_version") != SCHEMA_VERSION:
        problems.append(
            f"schema_version must be {SCHEMA_VERSION}, got {schema.get('schema_version')!r}"
        )

    gaps = schema.get("allowed_ref_gaps", [])
    if not isinstance(gaps, list) or not all(
        isinstance(gap, str) and VERDICT_REF.match(gap) for gap in gaps
    ):
        problems.append("allowed_ref_gaps must be a list of verdict refs like 'V15'")

    sections = schema.get("sections")
    if not isinstance(sections, list) or not sections:
        problems.append("sections must be a non-empty list")
        sections = []
    verdicts = schema.get("verdicts")
    if not isinstance(verdicts, list) or not verdicts:
        problems.append("verdicts must be a non-empty list")
        verdicts = []

    # One template is one category. A second prefix in a file is a copy-paste defect, and it would
    # let two categories' answers collide in one `question_key` column.
    records = schema.get("records", [])
    if not isinstance(records, list):
        problems.append("records must be a list when present")
        records = []

    prefixes = {
        match.group("prefix")
        for item in [*sections, *records, *verdicts]
        if isinstance(item, dict)
        for candidate in _keys_of(item)
        for match in [KEY_PATTERN.match(candidate)]
        if match
    }
    if len(prefixes) > 1:
        problems.append(
            f"one template must use one key prefix; found {sorted(prefixes)}"
        )
    prefix = next(iter(prefixes)) if len(prefixes) == 1 else ""

    seen: dict[str, str] = {}
    for index, section in enumerate(sections):
        path = f"sections[{index}]"
        if not isinstance(section, dict):
            problems.append(f"{path}: a section must be an object")
            continue
        if not _text(section.get("title")):
            problems.append(f"{path}.title: missing — a section with no heading has no place on a page")
        if "key" in section and not _text(section.get("key")):
            problems.append(f"{path}.key: must be a non-empty string when given")
        questions = section.get("questions")
        if not isinstance(questions, list) or not questions:
            problems.append(f"{path}.questions: must be a non-empty list")
            continue
        for q_index, question in enumerate(questions):
            _validate_question(question, f"{path}.questions[{q_index}]", prefix, problems, seen)

    for index, record in enumerate(records):
        _validate_record(record, f"records[{index}]", prefix, problems, seen)

    verdict_keys = {
        verdict["key"] for verdict in verdicts if isinstance(verdict, dict) and _text(verdict.get("key"))
    }
    for index, verdict in enumerate(verdicts):
        path = f"verdicts[{index}]"
        _validate_verdict(verdict, path, prefix, problems, seen)
        if not isinstance(verdict, dict):
            continue
        for c_index, child in enumerate(verdict.get("sub_questions") or []):
            child_key = child.get("key") if isinstance(child, dict) else None
            if isinstance(child_key, str) and child_key in verdict_keys:
                problems.append(
                    f"{path}.sub_questions[{c_index}].key: {child_key!r} is also a top-level verdict — "
                    "a printed child row never gets its own row (the verdict count is the invariant)"
                )
    return problems


def _keys_of(item: dict) -> list[str]:
    """Every `key` a section or verdict carries, including its children's and questions'."""
    keys: list[str] = []
    if isinstance(item.get("key"), str):
        keys.append(item["key"])
    for child in item.get("sub_questions") or []:
        if isinstance(child, dict) and isinstance(child.get("key"), str):
            keys.append(child["key"])
    for question in item.get("questions") or []:
        if isinstance(question, dict) and isinstance(question.get("key"), str):
            keys.append(question["key"])
    return keys


def assert_valid_schema(schema: Any) -> None:
    """Raise `SchemaValidationError` carrying every problem. Used by `load_template`.

    In:  `schema` — the parsed JSON.
    Out: None when the schema is loadable.
    Side Effects: none.
    Fails: `SchemaValidationError`, whose `.problems` is the full list to print.
    """
    found = validate_schema(schema)
    if found:
        raise SchemaValidationError(found)


# --- Versioning: which template a new visit may use -------------------------
#
# The rule these four functions exist to keep is one sentence: **an assessment freezes a full copy of
# the schema when it starts**, so a template that has ever been used is history and the only correct
# way to change a questionnaire is a new version. Nothing here edits a schema; the flag is what moves.


class InactiveTemplateError(Exception):
    """A visit (or a self-check) asked for a template the group has not made live.

    Raised instead of quietly using the last active one: the wrong questionnaire produces a valid
    look that a committee could certify against, and there is no later moment that would notice.
    """


class NoActiveTemplateError(Exception):
    """A category has no active template at all — a deployment fault, not an empty questionnaire."""


@transaction.atomic
def activate_template(template: AssessmentTemplate) -> AssessmentTemplate:
    """Make `template` the one a new visit may use, and stand the previous one down.

    In:  `template` — an existing, validated row for a category.
    Out: the same row, `is_active=True`.
    Side Effects: sets `is_active=False` on every other template of that category (only), then
         activates this one. Two UPDATEs, one transaction.
    Fails: `SchemaValidationError` **before any write** when the schema does not validate — a
         malformed questionnaire must not be reachable by an admin edit either.
    Idempotency: yes. Activating the already-active template is a no-op that leaves one active row.
    """
    assert_valid_schema(template.schema)
    # Both UPDATEs are unconditional on purpose: the object handed in may be stale (its
    # `is_active` can say True for a row the database stood down an hour ago), and branching on a
    # stale flag made re-activating a superseded version a silent no-op — caught by
    # `test_reactivating_a_superseded_version_moves_the_flag_back`. Two writes are cheaper than a
    # read-then-decide that can disagree with the row.
    AssessmentTemplate.objects.filter(category_id=template.category_id, is_active=True).exclude(
        pk=template.pk
    ).update(is_active=False)
    AssessmentTemplate.objects.filter(pk=template.pk).update(is_active=True)
    template.is_active = True
    return template


def current_template(category: Category) -> AssessmentTemplate:
    """The active template for a category.

    In:  `category` — a seeded `Category` row.
    Out: its one active `AssessmentTemplate`.
    Side Effects: one query.
    Fails: `NoActiveTemplateError` when there is none. Returning None would let a caller render a
         questionnaire with no questions and call the result a visit.
    """
    template = (
        AssessmentTemplate.objects.filter(category=category, is_active=True)
        .order_by("-effective_from", "-id")
        .first()
    )
    if template is None:
        raise NoActiveTemplateError(
            f"no active assessment template for {category.code!r} — "
            "load one and activate it (load_template --activate) before a visit is scheduled"
        )
    return template


def assert_template_usable(template: AssessmentTemplate) -> None:
    """The guard every path that starts an assessment calls first (spec §4.2).

    In:  `template` — the row a caller resolved, or resolved from `FarmCategory`.
    Out: None. Returns quietly when the template is active.
    Side Effects: none (reads the instance it was given; no query).
    Fails: `InactiveTemplateError`. Deliberately not a database lookup: a caller that already holds
         the row must be refused even if the object it holds is stale, because a stale active flag
         is the failure this catches.
    """
    if not template.is_active:
        raise InactiveTemplateError(
            f"{template.category_id}:{template.version} is not active — a visit may only be "
            "started against the category's current template (spec §4.2)"
        )


def _validate_record(record: Any, path: str, prefix: str, problems: list[str], seen: dict[str, str]) -> None:
    """One Sheet I §2 record check — the documents a visit asks to see (spec §4.2 `RecordCheck`).

    It is template data, not a constant, for the reason `SELF_CHECK_PRD` §3.4 gives: the public
    self-check's seven record controls must carry the same wording as the visit's checklist, and two
    copies are two copies that drift. `ref` is the FORM's own letter (a–f) or a short slug for the one
    line the FORM prints without a letter.
    """
    if not isinstance(record, dict):
        problems.append(f"{path}: a record must be an object")
        return
    key = record.get("key")
    if not isinstance(key, str):
        problems.append(f"{path}.key: missing")
    else:
        match = KEY_PATTERN.match(key)
        if not match:
            problems.append(
                f"{path}.key: {key!r} does not match <prefix>.R<nn> (e.g. crops.R01)"
            )
        else:
            if key in seen:
                problems.append(f"{path}.key: duplicate key {key!r} (already used at {seen[key]})")
            else:
                seen[key] = path
            if prefix and match.group("prefix") != prefix:
                problems.append(
                    f"{path}.key: prefix {match.group('prefix')!r} differs from the template's "
                    f"{prefix!r} — one template is one category"
                )
            if RECORD_BODY.match(match.group("body")) is None:
                problems.append(f"{path}.key: {key!r} is not a record key")
    if not _text(record.get("ref")):
        problems.append(f"{path}.ref: missing — the FORM's own letter, or a slug where it prints none")
    if not _text(record.get("text")):
        problems.append(f"{path}.text: missing — the record has to be named")
    if "self_check" in record:
        _validate_self_check(record["self_check"], path, problems)
