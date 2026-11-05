"""The self-check's reviewed wording — **data**, in one place, so a page cannot invent a sentence.

Split out of `_selfcheck.py` when that file passed the 30 KB cap (`build_principles.md` §II), along
the seam the PRD itself draws: `SELF_CHECK_PRD` §3.4 says the wording lives "in two places, and
neither is a migration" — the eleven *derived* controls in the frozen Crops template, the nine *own*
ones (A1–A5, C5, D1, E1–E2) in code.

This module is the code half: answer sets, band labels, the caveats, the land-history notes and the
nine controls whose sentences were judged line by line in the D71 ledger
(`product/design/d71_self_check_questions.html`, 2026-11-04), pasted here verbatim. **Nothing here
is logic** — `_selfcheck.py` decides; this file says what the visitor reads.

Two rules a later editor must keep:

- A derived control's `why` stays **empty** here. It arrives from the template marker at
  `build_check()` time, so the front door and the visit cannot drift apart. If you find yourself
  pasting it in, the test `test_the_service_carries_no_copy_for_a_derived_control` will fail, and
  it is right to.
- A band label is what the visitor *declared* (build §III). Changing one is a data decision that
  orphans stored labels, which is why the report table stores the label and not a code.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.services._public import FEE_BANDS

@dataclass(frozen=True)
class Option:
    """One answer chip. `code` is what the database keeps; `label` is what the farmer reads."""

    code: str
    label: str


# --- Answers ------------------------------------------------------------------------------
#
# Record controls store a *code* (the PRD's own vocabulary), because the report command counts
# uptake and a label is a sentence. Band controls store the **printed label**, because a band is
# what the visitor declared and the OPP's wording is the datum (build §III: declared, never derived).

ANSWER_YES = "YES"
ANSWER_PARTLY = "PARTLY"
ANSWER_NO = "NO"
ANSWER_RATHER_NOT_SAY = "RATHER_NOT_SAY"

RECORD_ANSWERS: tuple[Option, ...] = (
    Option(ANSWER_YES, "Yes"),
    Option(ANSWER_PARTLY, "Partly"),
    Option(ANSWER_NO, "No"),
    Option(ANSWER_RATHER_NOT_SAY, "Rather not say"),
)

#: Bands, as the OPP and the FORM print them. The top band's label is OPP §2.3's own wording.
HECTARES_BANDS = (
    "Less than 1 ha",
    "1–5 ha",
    "5–20 ha",
    "20–100 ha",
    "More than 100 ha",
)
PASTURE_BANDS = ("None", "Less than 1 ha", "1–5 ha", "5–20 ha", "More than 20 ha")
LAND_HISTORY_BANDS = (
    "Not yet",
    "Under 12 months",
    "12–17 months",
    "18 months or more",
    "I am not sure",
)
TURNOVER_SKIP = "I would rather not say"

#: FORM Sheet A, census (row 28–31 of `6. A. Details of applicant`). The FORM prints the categories,
#: so the FORM's words are the ones stored; "rather not say" is added because §3.5's rule is not a
#: courtesy that stops at the records step.
CENSUS_GENDER = ("Male", "Female", "Rather not say")
CENSUS_AGE_BAND = ("18-34", "34-50", "50-70", "> 70", "Rather not say")
CENSUS_DEMOGRAPHIC_GROUP = ("African", "Coloured", "Indian", "White", "Rather not say")

EXIT_REASONS = (
    ("COST", "The cost"),
    ("RECORDS", "Records and paperwork"),
    ("LAND", "Land history / conversion time"),
    ("TIME", "Time"),
    ("NOT_RIGHT", "I am not sure the group is right for me"),
    ("SOMETHING_ELSE", "Something else"),
)

#: The seven Sheet I §2 lines a to-do item may cite, reviewed once. FORM-only citations are declared
#: here rather than looked up in the corpus, because the FORM is a source document and not an
#: ingested standard — a citation that pretends to be a clause would be worse than one that says
#: "the FORM's own form".
TEXT_ONLY_CITATIONS = (
    "FORM Sheet I §2 a",
    "FORM Sheet I §2 b",
    "FORM Sheet I §2 c",
    "FORM Sheet I §2 d",
    "FORM Sheet I §2 e",
    "FORM Sheet I §2 f",
    "FORM Sheet I §2 (unnumbered line)",
)


# --- The control table --------------------------------------------------------------------


@dataclass(frozen=True)
class Control:
    """One of the twenty questions. `why` is empty for a derived control, and that is the rule."""

    key: str
    group: str
    kind: str  # SINGLE (one answer) | MULTI (several) | RECORD | CONSENT
    title: str
    help: str
    source: str
    options: tuple[Option, ...] = ()
    short: str = ""
    why: str = ""
    template_key: str = ""
    template_text: str = ""


@dataclass(frozen=True)
class Group:
    key: str
    title: str
    lede: str
    controls: tuple[Control, ...]


GROUPS: tuple[tuple[str, str, str], ...] = (
    (
        "A",
        "About your farm",
        "Five things about the farm. Bands only — the application asks for exact figures.",
    ),
    (
        "B",
        "Records a visit checks",
        "Do you have these? None of them are needed to apply. A missing record does not stop an "
        "assessment — the visit records it and you agree what happens next. What does stop a visit "
        "is a question left blank.",
    ),
    ("C", "Practices the visit looks at", "How you farm, in five questions the visit asks too."),
    ("D", "On your way out", "Only if you are not applying yet. Skip it if you are."),
    (
        "E",
        "Two consents",
        "Both are unticked. Nothing is stored unless you tick the first one.",
    ),
)


#: The nine controls with no template question (SELF_CHECK_PRD §3.4). Wording from the D71 ledger,
#: pasted rather than re-written: the sentences were judged once, with the product owner, and a
#: second draft here would be a second opinion nobody asked for.
SELF_CHECK_ITEMS: tuple[Control, ...] = (
    Control(
        key="A1",
        group="A",
        kind="MULTI",
        title="What do you produce?",
        help="Tick everything that applies.",
        source="FORM Sheet A",
        why=(
            "The group assesses crops, livestock, seed and processing under different "
            "questionnaires, and a seed producer should not be asked about compost. Telling us which "
            "one you are under means the next page is the right one."
        ),
    ),
    Control(
        key="A2",
        group="A",
        kind="SINGLE",
        title="How much land do you farm in total?",
        help="Your best estimate is fine — the application asks for the exact figure.",
        source="FORM B.1 Q2.1–2.3",
        options=tuple(Option(band, band) for band in HECTARES_BANDS),
        why=(
            "Land area is <strong>not</strong> used to set your fee — fees follow turnover (OPP "
            "§2.3). It is asked because the visit checks field diagrams against acreage (FORM "
            "Sheet I §2 b), and because the group reports the scale of farms it serves."
        ),
    ),
    Control(
        key="A3",
        group="A",
        kind="SINGLE",
        title="How much of that is pasture or grazing?",
        help="Skip if none of your land is grazed.",
        source="FORM B.1 Q2.2",
        options=tuple(Option(band, band) for band in PASTURE_BANDS),
        why=(
            "Pasture and meadow have their own conversion period — 12 months before grazing or "
            "harvest (SAOSO 4.2.3 b) — which is different from other perennials. Without this "
            "answer the timing note would be wrong for a grazing farm."
        ),
    ),
    Control(
        key="A4",
        group="A",
        kind="SINGLE",
        title="How long has this land been farmed organically?",
        help=(
            "The land, not you — count from when the last non-organic input was used on it."
        ),
        source="FORM B.1 Q3.1",
        options=tuple(Option(band, band) for band in LAND_HISTORY_BANDS),
        why=(
            "The conversion period is the most common reason someone is not yet assessable. The "
            "standard sets it at 12 months for annuals, 12 for pasture, 18 for other perennials, "
            "and 36 where inputs not permitted by organic principles were used (SAOSO 4.2.3). The "
            "group’s In-Conversion seal applies for less than 18 months for annuals (OPP §V). We ask "
            "so we can tell you which applies — not to judge you."
        ),
    ),
    Control(
        key="A5",
        group="A",
        kind="SINGLE",
        title="Roughly what was your turnover last year?",
        help="This is what the group’s fee scale uses. Bands only — and you can skip it.",
        source="OPP §2.3",
        options=tuple(Option(band.label, band.label) for band in FEE_BANDS)
        + (Option(TURNOVER_SKIP, TURNOVER_SKIP),),
        why=(
            "Fees follow a six-band turnover scale (OPP §2.3), and turnover is "
            "<strong>self-declared by the farmer and peer-reviewed</strong> — the platform stores "
            "the band you choose and never calculates one from sales data. If you would rather not "
            "say, you simply will not see a fee figure here; the public table on "
            "/become-a-member/ is there either way."
        ),
    ),
    Control(
        key="C5",
        group="C",
        kind="SINGLE",
        title="Do you buy in produce from other farmers to sell on?",
        help="Buying in other people’s produce is allowed, with conditions.",
        source="FORM Sheet A, Aggregation",
        options=(
            Option("NO", "No"),
            Option("YES", "Yes"),
            Option("PLAN", "No, but we plan to"),
        ),
        why=(
            "Buying in produce is allowed, and OPP §VI sets the conditions: the group assesses each "
            "case, every supplying farm signs a declaration and commits to progressing towards "
            "certification within six months, traceability runs through invoices and delivery "
            "notes, organic and conventional produce are physically separated, and batches are "
            "labelled by production method (OPP §VI.1–6.5). A \"yes\" changes what the visit "
            "checks, not whether you can join."
        ),
    ),
    Control(
        key="D1",
        group="D",
        kind="SINGLE",
        title="If you are not going to apply just yet, what would need to change?",
        help="Optional. It never appears on your application.",
        source="—",
        options=tuple(Option(code, label) for code, label in EXIT_REASONS),
        why=(
            "Nobody who completes the assessment form can tell us why people stop before it — by "
            "definition. This is the only question that can, and it is not part of your "
            "application."
        ),
    ),
    Control(
        key="E1",
        group="E",
        kind="CONSENT",
        title="May we count your answers?",
        help="Unticked by default. Nothing is stored unless you tick this.",
        source="D64, 2026-10-23",
        why=(
            "The group is asked by PGS South Africa and SAOSO what farmers are looking for and what "
            "stands in the way, and today it can only answer from the farms that already joined — "
            "which is the one group guaranteed to be positive about joining. Your answers, in "
            "totals, are what makes that answer honest."
        ),
    ),
    Control(
        key="E2",
        group="E",
        kind="CONSENT",
        title="May we include your demographic details in those totals?",
        help="Separately from the question above. Unticked by default.",
        source="FORM Sheet A, census; POPIA special information",
        why=(
            "The assessment form collects gender, age group and demographic group and states the "
            "purpose on the form itself: \"for census purposes — PGS SA & SAOSO collect this data "
            "to profile small-scale organic farmers in South Africa for advocacy & support "
            "purposes\". That is the whole of what it is for. <strong>Funding applications are not "
            "covered by this consent</strong> — they would need different information and a "
            "separate agreement."
        ),
    ),
)


#: The eleven controls the **active Crops template** carries as `self_check` markers.
#:
#: `template_key` is the map, and it is explicit on purpose: `crops.R01` → B1 is not arithmetic a
#: later reader should have to trust. The title, the answer set and the source are the front door's
#: reviewed wording (D71); `why` and `template_text` arrive from the frozen template in
#: `build_check()`, which is what keeps the front door and the visit saying the same thing.
DERIVED_CONTROLS: tuple[Control, ...] = (
    Control(
        key="B1",
        group="B",
        kind="RECORD",
        title="Do you have a sketch of the farm?",
        help="Layout, buildings, production areas, natural bush, access roads, neighbours.",
        short="A farm sketch",
        source="FORM Sheet I §2 a",
        options=RECORD_ANSWERS,
        template_key="crops.R01",
    ),
    Control(
        key="B2",
        group="B",
        kind="RECORD",
        title="Do you have sketches or diagrams of your fields?",
        help="Acreage, what is growing where, grazing areas, stock numbers.",
        short="Field diagrams",
        source="FORM Sheet I §2 b",
        options=RECORD_ANSWERS,
        template_key="crops.R02",
    ),
    Control(
        key="B3",
        group="B",
        kind="RECORD",
        title="Do you have a farm diary?",
        help="Plantings, harvest quantities, anything you apply to the land.",
        short="A farm diary",
        source="FORM Sheet I §2 c",
        options=RECORD_ANSWERS,
        template_key="crops.R03",
    ),
    Control(
        key="B4",
        group="B",
        kind="RECORD",
        title="Do you have records of the inputs you buy or receive?",
        help="Including seeds and seedlings, and donations as well as purchases.",
        short="Input records",
        source="FORM Sheet I §2 d",
        options=RECORD_ANSWERS,
        template_key="crops.R04",
    ),
    Control(
        key="B5",
        group="B",
        kind="RECORD",
        title="Do you have sales records?",
        help="Whatever form they take — a book, slips, a spreadsheet, invoices.",
        short="Sales records",
        source="FORM Sheet I §2 e",
        options=RECORD_ANSWERS,
        template_key="crops.R05",
    ),
    Control(
        key="B6",
        group="B",
        kind="RECORD",
        title="Do you have an input/output reconciliation?",
        help=(
            "Your sales compared against what you produced, to show nothing came in from outside."
        ),
        short="An input/output reconciliation",
        source="FORM Sheet I §2 f",
        options=RECORD_ANSWERS,
        template_key="crops.R06",
    ),
    Control(
        key="B7",
        group="B",
        kind="RECORD",
        title="Do you have soil and water test results?",
        help=(
            "Including soil organic matter and cation exchange capacity, if your lab reports them."
        ),
        short="Soil and water test results",
        source="FORM Sheet I §2 (unnumbered line)",
        options=RECORD_ANSWERS,
        template_key="crops.R07",
    ),
    Control(
        key="C1",
        group="C",
        kind="SINGLE",
        title="Do you make your own compost?",
        help="",
        source="FORM B.1 Q4.2",
        options=(Option("YES", "Yes"), Option("NO", "No")),
        template_key="crops.Q4.2",
    ),
    Control(
        key="C2",
        group="C",
        kind="SINGLE",
        title="Do you buy in compost?",
        help="Purchased compost has to come from an acceptable source.",
        source="FORM B.1 Q5.1",
        options=(Option("YES", "Yes"), Option("NO", "No")),
        template_key="crops.Q5.1",
    ),
    Control(
        key="C3",
        group="C",
        kind="SINGLE",
        title="Where do your seeds come from?",
        help="Tick the one that is most of it.",
        source="FORM B.1 Q11.1",
        options=(
            Option("ORGANIC", "Organic seed"),
            Option("CONVENTIONAL_UNTREATED", "Conventional, untreated"),
            Option("CONVENTIONAL_TREATED", "Conventional, treated"),
            Option("SAVED", "I save my own"),
            Option("MIX", "A mix"),
        ),
        template_key="crops.Q11.1",
    ),
    Control(
        key="C4",
        group="C",
        kind="SINGLE",
        title="Are all your seeds non-GMO?",
        help=(
            "If you buy conventional seed, the group will ask for a letter from the supplier saying "
            "the seed is not treated and not GMO."
        ),
        source="FORM B.1 Q11.2",
        options=(
            Option("YES", "Yes"),
            Option("NO", "No"),
            Option("SOME", "Some are, some aren’t"),
            Option("UNKNOWN", "I do not know"),
        ),
        template_key="crops.Q11.2",
    ),
)


#: The caveat a non-Crops visitor sees. §3.1's "honest category caveat": an empty form would look
#: like a clean bill of health, and pretending the other sheets are written would be a claim.
CAVEAT_NOT_WRITTEN = (
    "Only a <strong>crops</strong> farm has a full check today. The {label} questionnaire is still "
    "being written — so treat the records list above as an example, not as your list."
)
CAVEAT_NOT_LIVE = (
    "The crops questionnaire is not live on this deployment yet, so the records a visit checks "
    "cannot be listed here. Your answers are still yours; ask the administrator before relying on "
    "this page."
)
CAVEAT_OTHER_TICKED = (
    "You ticked more than one category, and only a <strong>crops</strong> farm has a full check "
    "today. The records list above is the crops one."
)
CAVEAT_NOT_SEEDED = (
    "This group has not published its assessment categories yet, so there is no records list to "
    "show here. Your answers are still yours; ask the administrator before relying on this page."
)


# --- Land history, in the farmer's words (D31 shown, never resolved) -----------------------

LAND_HISTORY_NOTES: dict[str, str] = {
    "Not yet": (
        "Your land has not started its organic period. On the shortest reading that is 12 months; "
        "on the group’s own seal page it is 18 months before sowing or planting for annuals."
    ),
    "Under 12 months": (
        "You are inside both thresholds, so the answer is the same either way: not yet assessable "
        "as organic, and In-Conversion is where you would start."
    ),
    "12–17 months": (
        "You are past 12 months and short of 18 months. This is the band where the two documents "
        "disagree, so the answer depends on what you grow — and the group has not yet settled "
        "which applies."
    ),
    "18 months or more": "You are past both thresholds. The disagreement no longer affects you.",
    "I am not sure": (
        "That is a normal answer. The visit establishes it from your records rather than from "
        "memory."
    ),
}


