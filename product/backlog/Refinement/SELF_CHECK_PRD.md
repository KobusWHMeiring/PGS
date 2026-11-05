# PRD: The public self-check — "Before you apply"

**Status:** Refinement — shape decided (**D71**, 2026-10-29). Every control and its wording judged by
the product owner against its source; twenty of twenty decided. No code written.
**Owner:** Kobus Meiring (Product)
**Last Updated:** 2026-10-29
**Scope:** A public, unauthenticated page at `/before-you-apply/` that asks twenty questions, returns a
to-do list, a mirror of the farmer's own answers, and two separate consents; plus the consented
aggregate behind it. **Not in scope:** the application flow (MVP 1a Task A6), the pre-visit
questionnaire (Task C2), any reporting surface (MVP 3), any eligibility statement.
**Reference:**
- Decision and full wording ledger — `product/design/d71_self_check_questions.html` (D71)
- Target-state spec — `PGS_PLATFORM_SPEC.md` §7 (Flow A), §8 (Flow B), §11 (POPIA), §18.3 D31, D64, D68, D71
- Plan — `ready/MVP1A_PLAN.md` (Task A6 lands first; Task A8 is this work)
- Build rules — `product/docs/context/build_principles.md` §I, §II, §III
- Design — `product/design/DESIGN.md` §1 (claim discipline), §2 (tokens)
- Source documents — OPP §I.2, §2.3, §V, §VI; SAOSO 1.4.1–1.4.2, 2.3.2, 4.1.1, 4.2.2–4.2.3, 4.6;
  FORM Sheets A, B.1, I §1–§3

---

## 1. Problem Statement

**What exists today.** A farmer can find the site, ask the assistant a question and read the
standard. Then the journey stops. `/become-a-member/` ends in *"Contact the administrator →"*, and
`/contact/` renders `<span class="chip">email</span> <span class="chip">phone</span>
<span class="chip">contact details to confirm</span>` (`core/templates/public/contact.html:35–39`).
A motivated farmer's next step is currently nothing, and it is already logged in `todo.md`.

**What a farmer does not know at that moment, and cannot find out:**

1. **What a visit actually looks at.** The assessment form asks the farmer **77 numbered
   sub-questions** across 38 Question blocks, and checks seven records for a Crops farm
   (FORM Sheet I §2 a–f plus the soil/water line; g–i are agro-processing only). None of that is
   visible before applying.
2. **Whether a missing record disqualifies them.** It does not — `MVP1A_PRD` §5.8 already specifies
   that a `MISSING` record is a recorded fact, not a blocker, and that only a *blank* stops a
   finalise — but nothing public says so.
3. **When their land could be assessable.** Two governing documents disagree (SAOSO 4.2.3: 12
   months for annuals; OPP §V: 18), D31 recorded the conflict and refused to resolve it, and no
   surface publishes either number.
4. **What it costs.** The fee scale is on `/become-a-member/`, but a farmer has to work out their own
   band first.

**What the group cannot know.** Why farmers who read the site do not join. Every respondent to the
assessment form has already joined, so the group's only data about demand is data from people who
said yes. The gap is invisible by construction.

**Why now.** MVP 1a's application flow (Task A6) is the next thing to build. This page is its front
door, and it is the only place in the slice where a farmer who *is not ready* is given something
useful instead of a dead end.

---

## 2. Strategic Goal

> **A farmer who has read the standard can find out, in five minutes and without an account, what a
> visit checks, what they already have, when their land could be assessable, what it would cost —
> and where to start. The group learns, in totals, why the ones who never apply did not.**

**Success looks like:** a farmer finishes the check on a phone, reads a to-do list that cites the
form rather than advice we invented, understands that nothing they answered is a judgement, and
either starts an application or leaves knowing exactly what to gather. Months later the group can
answer *"how many prospective farmers in this catchment have no sales records, and what stops
them?"* from a report, without one farm being identifiable.

---

## 3. Proposed Solution

**A public page, twenty controls, nothing stored unless consented.** Grouped as:

| Group | Controls | Source |
|---|---|---|
| **A — your operation** (5) | category · total land band · pasture band · land-history band · **turnover band** | FORM Sheet A, B.1 Q2–Q3; OPP §2.3 |
| **B — records a visit checks** (7) | farm sketch · field diagrams · farm diary · input records · sales records · input/output reconciliation · soil and water tests | FORM Sheet I §2 a–f + the soil/water line |
| **C — practices** (5) | own compost · purchased compost · seed source · non-GMO seed · buying in produce | FORM B.1 Q4.2, 5.1, 11.1, 11.2; Sheet A aggregation |
| **D — on your way out** (1) | why you are not applying yet (closed list + 280 chars) | new |
| **E — consents** (2) | research (aggregate) · demographic (separate) | D64's rule; FORM Sheet A census |

### 3.1 The three things a farmer gets back (B, C and D of the brainstorm)

- **A to-do list.** Every item is a record they do not have, phrased with what will satisfy a visit.
  **No advice copy is authored** — where a clause exists in the corpus the item cites it, and where
  it does not the citation is FORM Sheet I §2 as plain text.
- **A mirror, not a verdict.** *"Of the seven records a visit checks, your answers show four in
  place."* Counts out of a known denominator. Never a score, never a percentage, never the words
  *eligible*, *ready*, *approved* or *certified*.
- **The two facts nobody publishes**: the land-history note (both thresholds, and that the group has
  not settled which applies) and the fee band they declared (OPP §2.3 figures, from
  `core/services/_public.py` `FEE_BANDS`).

### 3.2 Two fixed lines, on every result

> **"The farm visit decides. This is only what your answers show, and the visit happens after you
> apply."**

> **"A missing record does not stop an assessment. The visit records it, and you and the group agree
> what happens next."**

The second is not reassurance copy: it is `MVP1A_PRD` §5.8 in a farmer's words. **A test asserts the
two agree** — the service that computes the result reads the same constant the visit's finalise gate
uses for "not a blocker", so a future change to §5.8 cannot leave the public promise behind.

### 3.3 "Why we ask" on every control

A native `<details>` disclosure naming the clause, not a tooltip: a tooltip needs JavaScript and a
hover, is unreachable on a phone and invisible in print; a disclosure works with the keyboard, with
no JS, and prints open. This exists because it was the dominant note in the wording review — every
question that felt intrusive or arbitrary was answered by naming the source, not by softening the
question.

### 3.4 The wording is data, in two places, and neither is a migration

- **Derived controls** (B1–B7, C1–C5) are questions or `RecordCheck` items that already exist in the
  frozen Crops template. They gain `"self_check": {"tier": 1, "why": "…"}` in the schema, so the
  front door and the visit **cannot drift apart in wording** — the thing the wording review was most
  worried about.
- **Own controls** (A1–A5, D1, E1–E2) have no template question. They live in a single
  `SELF_CHECK_ITEMS` structure in `core/services/_selfcheck.py`, beside the fee bands.

Both are **data seeded per deployment** (§I, "code encodes the process; data encodes the standard").
Retargeting to another standard changes JSON and a constant, not a migration.

### 3.5 The fourth answer

Every record control accepts **Yes / Partly / No / Rather not say**. It exists because the review
flagged the records as private, and because a front door that only offers "yes" and "no" turns a
privacy concern into a false answer. `RATHER_NOT_SAY`:

- produces **no to-do item** (we are not nagging),
- is **not counted as missing** in the mirror,
- renders one line — *"the visit will still ask"* — because that is true and hiding it would be a
  different kind of dishonesty.

### 3.6 Consent — D64's rule, twice

Unticked by default, so silence is not consent. With **neither** box ticked, **no row is written**:
the result renders from the submitted form in the same request. Ticking research consent writes a
`SelfCheckReport`; ticking demographic consent as well writes a `SelfCheckDemographic`, and it is
**refused without research consent**.

The demographic fields are `census_gender`, `census_age_band`, `census_demographic_group` — the same
names and the same classification as `Farm`'s, reused deliberately so an export cannot tell them
apart by accident. They are a **separate table**, so "excluded from every serializer" holds by
construction rather than by remembering, and so withdrawal can delete one without the other.

The consent text **names the recipients** (PGS South Africa, SAOSA) rather than saying "research
purposes", states **totals only, never farm by farm**, gives a small-count rule, offers a withdrawal
route that works without an account, and — per the review — states plainly that **funding
applications are not covered** (§9 Q1).

---

## 4. Technical Requirements

### 4.1 Models — new file `core/models/_selfcheck.py` (one migration)

```python
class SelfCheckReport(models.Model):
    public_uuid       = UUIDField(default=uuid4, unique=True, editable=False)   # §I: no sequential ids publicly
    created_on        = DateField(auto_now_add=True)
    category          = ForeignKey(Category, null=True, on_delete=PROTECT)      # Categories are data
    other_categories  = JSONField(default=list)      # labels, not FKs: a tick is not an application
    hectares_band     = CharField(blank=True)
    pasture_band      = CharField(blank=True)
    land_history_band = CharField(blank=True)
    turnover_band     = CharField(blank=True)        # the OPP §2.3 label, DECLARED (build §III)
    records_held      = JSONField(default=dict)      # {"B1": "YES"|"PARTLY"|"NO"|"RATHER_NOT_SAY", ...}
    practices         = JSONField(default=dict)      # {"C1": "YES"|..., ...}
    exit_reason       = CharField(blank=True)
    exit_note         = CharField(max_length=280, blank=True)
    research_consent_at   = DateTimeField(null=True)
    consent_text_version  = CharField(max_length=32)


class SelfCheckDemographic(models.Model):
    report                = OneToOneField(SelfCheckReport, on_delete=CASCADE, related_name="demographic")
    census_gender         = CharField(blank=True)
    census_age_band       = CharField(blank=True)
    census_demographic_group = CharField(blank=True)
```

**Rules.** No FK to `Member` or `Farm` — most visitors will never have either, and a report must not
become an application record. Every band is a label, never a number derived from another. No
`is_*` derived field of any kind: nothing here is a status.

### 4.2 Service surface — `core/services/_selfcheck.py`

```python
def build_check(category: str = "CROPS") -> SelfCheckForm:
    """
    In:   category: str — one of the seeded Category keys.
    Out:  SelfCheckForm (frozen): the groups, the controls in order, and each control's
          "why" copy, resolved from the Crops template's `self_check` markers plus
          SELF_CHECK_ITEMS.
    Side Effects: none.
    Fails: UnknownCategoryError.
    """

def evaluate(answers: Mapping[str, Any]) -> SelfCheckResult:
    """
    In:   answers: the submitted form values, already validated by the form.
    Out:  SelfCheckResult (frozen): per-group counts, the to-do items with their
          citations, the land-history note key, the declared fee band and its OPP §2.3
          figures, the two fixed lines, and the honest category caveat.
    Side Effects: none. Never writes. This is what makes "nothing is kept" true.
    Fails: nothing — an unanswered control is omitted, never an exception.
    """

def submit(
    answers: Mapping[str, Any], *,
    research_consent: bool, demographic_consent: bool,
    demographic: Mapping[str, str] | None = None,
) -> SelfCheckReport | None:
    """
    In:   the validated form values; the two consents; the demographic values, if given.
    Out:  the SelfCheckReport written, or None when no consent was given.
          None is a normal, expected result, not a failure.
    Side Effects: writes SelfCheckReport and, when consented, SelfCheckDemographic.
    Fails: DemographicConsentRequiredError — demographic consent without research consent.
    Idempotency: not required (single browser POST, no queue).
    """

def withdraw(public_uuid: UUID) -> None:
    """
    In:   public_uuid: the visitor's own reference.
    Out:  None.
    Side Effects: deletes the report and cascades the demographic row. No tombstone: the
          consent promises deletion, and a tombstone would itself be the personal data.
    Fails: ReportNotFoundError.
    """
```

### 4.3 View, URL, page metadata

`core/views/_public.py::before_you_apply` — under 20 lines: parse, call `submit` or `evaluate`,
render. A `Page` entry joins `PAGES` in `core/services/_public.py` (title, heading, description), so
the route is swept by the existing claim-discipline tests the moment it exists.

`core/urls.py` — `path("before-you-apply/", before_you_apply, name="before_you_apply")` in the public
section. Linked from `/become-a-member/` above the fee tables, from `/how-it-works/` step 1, and from
an `/ask/` refusal when the question is about the visitor's own eligibility.

### 4.4 Throttle and honeypot

Per-IP budget using the mechanism `/ask/` already has, plus a honeypot field. A public form that
writes to a research table is worth spamming, and a bot can make *"70% of prospective farmers lack
sales records"* false about a catchment of a few dozen farms.

### 4.5 The aggregate is a command, not a page

`core/management/commands/report_self_check.py` — prints counts per band, uptake on each record
control, the exit reasons, and the demographic cut **only** when `--demographics` is passed *and*
the cell meets `--min-count` (default 5). No view, no template, no MVP 3 reporting surface. Internal
first: a report for the group and for PGS SA/SAOSA, not a published page. A published figure is a
public claim about the group's own catchment and inherits DESIGN §1.

### 4.6 Template schema addition (Task B1) and markers (Task B3)

`validate_schema` accepts one new **optional** per-question key:

```jsonc
{ "key": "crops.Q4.2", "ref": "4.2", "respondent": "FARMER", "type": "YES_NO",
  "text": "Do you make your own compost?",
  "self_check": { "tier": 1, "why": "The FORM's verdict V4 calls adequate on-farm composting…" } }
```

Unknown keys still fail. `tier` is 1 only, for now — a second tier is a decision, not a default.
Task B3 marks the twelve derived controls; `test_crops_template.py` asserts the count and that every
control the self-check claims to derive **resolves to a question that exists**.

---

## 5. Execution Steps

1. **A6 first.** The application flow must exist, because it is the exit (§1). This PRD's page
   ships *after* it, in the same slice.
2. **B1 with the field, then B3 with the markers.** The schema key must be decided before the
   template is authored — bolting it on later means editing the artefact the plan calls its
   irreversibility risk.
3. **Models + migration** (`_selfcheck.py`), then the service surface, test-first.
4. **The page** — template, form, view, URL, `Page` entry, navigation links.
5. **The guards** (§6), each proven by breaking it.
6. **`report_self_check`** with the small-count rule.
7. **Prefill — as a C2 addendum, not a dependency.** When the portal questionnaire exists, a farmer
   who completed the check keeps their answers; until then the CTA is the application form and the
   answers are re-entered there. Recorded as `C2a` so A8 is never blocked on C2.

---

## 6. Success Criteria

- [ ] Twenty controls render at 390 px with no horizontal scroll, ≥44 px targets, in the `brand-*` palette
- [ ] **With neither consent ticked, zero rows are written** (asserted by row count, not by reading the code)
- [ ] Both consent boxes render **unticked**, and demographic consent without research consent is refused
- [ ] Withdrawal deletes the report **and** the demographic row
- [ ] The result contains no score, no percentage, no seal, and none of *eligible* / *ready* / *approved* / *certified*
- [ ] The land-history note prints **both** thresholds and says the group has not settled which applies
- [ ] The fee band is the **declared** one, and no band is shown if the farmer says they would rather not
- [ ] Every to-do citation either resolves to a passage in the corpus or is in the declared text-only list
- [ ] A non-Crops category gets an honest caveat, never an empty form
- [ ] `report_self_check` refuses any cell below the small-count threshold
- [ ] The two fixed lines are asserted against the same constant the finalise gate uses
- [ ] The route is in `PUBLIC_URLS`, so the existing claim-discipline sweep covers it

**Judgement (UAT, `tests/uat/self_check_uat.md`):** does the result read as a mirror or a verdict;
is the land-history note comprehensible to a farmer who has never read the OPP; does "Rather not
say" feel like a real answer or a way of saying no; does the consent read as a real choice; on a
phone, in sunlight.

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **Selection bias in the aggregate.** Farmers who abandon at question three are not in it, so the dataset flatters the funnel it is meant to describe. | Report start-to-result counts alongside answers (a per-step counter, anonymous), and state the bias in the report's own header. A number that cannot be misread is better than a clean one. |
| **Re-identification in a small catchment.** Category + hectares + turnover + land history in a few dozen farms is a person — which is the same risk the live `/endorsed-farms/` presentational claims carried. | Bands only, no nearest town, no crops list, no free text except inside a consented row; small-count rule on every cut; the demographic table is separate and doubly consented. |
| **A consent text that over-promises.** "Anonymised" is a promise the group cannot keep at this scale. | The text says **de-identified, totals only, never farm by farm, never published below a threshold**, and names the recipients. |
| **The page becomes advice.** A to-do list is one edit away from telling a farmer what the standard will decide. | No authored advice: every item cites a source, and the second fixed line is asserted against the finalise gate's own constant. |
| **Two questionnaires that disagree.** The front door and the visit drift in wording. | The twelve derived controls carry `self_check` markers in the frozen template, so the wording has one home; a test asserts each claim resolves. |
| **The research table pollutes.** A public write endpoint is worth spamming. | Per-IP budget, honeypot, and the small-count rule in the report. |
| **D31 is silently resolved.** Someone "cleans up" the land-history note into one number. | Both thresholds are read from data (OPP §V and SAOSO 4.2.3 constants), and a test asserts both appear and that neither is hardcoded in a template. |
| **A promise to the farmer the platform cannot keep.** The page says a missing record is not a blocker. | That sentence is generated from the same constant the visit's completeness gate uses; if §5.8 changes, the public page changes with it or the build fails. |

---

## 8. What This Is Not

- **Not the questionnaire.** 20 controls, bands, about five minutes. The visit asks 77 things and
  records evidence.
- **Not a verdict, an eligibility check or an application.** It writes nothing that could be mistaken
  for an assessment record, and it has no FK to `Member` or `Farm`.
- **Not a reporting surface.** The aggregate is a management command. MVP 3 owns reporting.
- **Not Crops-plus.** Only Crops has a full check (D28). The other three categories get an honest
  caveat and the administrator.

---

## 9. Open Questions

| # | Question | Who decides | Default this PRD takes |
|---|---|---|---|
| Q1 | **Does the group want a funding-application dataset?** That is a new processing purpose: its own consent text, its own fields, its own retention answer. The census fields do not cover what a funder asks for. | Group / committee | **Not built.** The consent text states plainly that funding applications are not covered. |
| Q2 | **Is there an unwritten freshness rule for soil and water tests?** No document states one: SAOSO's only laboratory sampling is the group's own (1.4.2), and the form asks for results without a date. Homtini's test is several years old and the farm remains verified. | Group | The page says only *"tell us when it was taken"*. It asserts no maximum age in either direction. |
| Q3 | **Is "a mix" sufficient for the seed question at assessment?** The FORM records the status of each seed lot as a baseline, so no — the front door says so and does not pretend otherwise. | Group / second reader | The disclosed asymmetry stays; a farmer who answers "a mix" learns what it costs later. |
| Q4 | **What is the small-count threshold?** | Product owner | **5**. It is a plausible denominator for "several farms in this catchment" and it is in the consent text as "a handful". |
| Q5 | **Who is the responsible party for the transfer to PGS SA/SAOSA?** | Group | Not answered. The consent names the recipients; it does not yet name who is accountable for their handling. |
| Q6 | **Route name.** `/before-you-apply/` is a position in the journey, not a claim. `/can-i-join/` was rejected: it promises an answer about eligibility. | Product owner | `/before-you-apply/`. |

---

## 10. 2026-10-29 — Design (D71)

The design of the wording was reviewed as a running page rather than a document:
`product/design/d71_self_check_questions.html`. Every control is shown against its FORM source
verbatim, with the change and its reason, and a `Why we ask` disclosure. The product owner judged all
twenty.

**The review changed the shape, not only the words.** Ten controls came back *reword* on the first
pass, and reading the ten notes together produced one conclusion: **every question in the records
group read as a demand until it said what happens when the answer is no.** That became the spine of
the page (§3.2, §3.5) rather than a series of copy edits.

**What the notes produced:**

| Note | Result |
|---|---|
| "make it explicit — *do you have these records*" | Group B is a question with the header *"None of them are needed to apply"*, and every item reads *Do you have…* |
| "not critical" | Not copy: `MVP1A_PRD` §5.8 already says a `MISSING` record is a recorded fact, not a blocker. The page now states the rule the server enforces, and a test holds the two together. |
| "feels like quite private info" | The *why* says the group asks **what** was bought, not what it cost; `RATHER_NOT_SAY` is a fourth answer on every record. |
| "farmers will push back on sales records" | The reason is stated: a **traceability** check, not an income check (OPP §VI.3 asks for quantity and which farm, not price). |
| "we could help capture those going forward" | Said explicitly for the reconciliation: a record you build forward, not one you had to keep. |
| "our soil test is 5/6 years old and we are still verified" | Measured: neither SAOSO nor the form sets a maximum age. The page says an older test is a starting point. |
| "is a mix enough?" | Enough here, not enough at the visit — the FORM's own note explains why, and the page quotes it. |
| "some are GMO and some aren't… tooltips might help" | `Some are, some aren’t` added; the tooltip became a `<details>` disclosure **on all twenty**, because a tooltip needs a hover and a phone has none. |
| "what does a yes mean / we plan to start buying in" | OPP §VI.1–6.5 is quoted in the disclosure, and **No, but we plan to** added. |
| "something else needs to say what that something else is" | One optional 280-character line, acceptable only because a consented row is the only row that can hold it. |
| "what is the census for / what about funding?" | Answered in the FORM's own words; funding declared out of scope (§9 Q1). |

**One correction to an earlier draft, recorded so it is not repeated:** land area was first justified
as "which fee scale you are in". That is wrong — fees follow **turnover** (OPP §2.3), which is why
**A5** exists and why the result can print the fee at all.

**Two revisions to the wording were kept rather than resolved**, and are marked `reserved` in the
ledger: A4 (land history — the bands sit on the threshold D31 has not settled) and E2 (demographic
consent — a committee decision about the group's own data, not a design one).

---

## 11. 2026-11-04 — the account at the end of the flow

**Decision (product owner, this session):** the result page offers an **opt-in** *"Save my details and
create an account"*, so a farmer who has decided they are serious can keep what they just entered and
use it when they start an official visit. It does not change §3.6: with the box unticked, nothing is
written and the result renders from the submitted form.

The seam already exists. `PGS_PLATFORM_SPEC` §3.1: *"an account is created when they engage further,
and `User.graduated_from_public_at` records when a public user became a member."* This addendum says
what "further" is here, and what the account can honestly hold.

### 11.1 What the check can and cannot carry forward

The check was designed to collect **no identity data**. So "save my details" saves less than the
words suggest, and the difference is worth stating before it is built:

| Carries forward | How |
|---|---|
| Category ticks | → `FarmCategory` rows **at application**, status `APPLIED` — never at the check |
| Turnover band | → `AssessmentFee.turnover_band` / `band_label` — label to label, no inference |
| Records held, practices | → prefill the questionnaire (already **C2a**, plan line 521) |
| **Farm name, nearest town, address, contact** | **the check never asks for any of them** |
| **Total hectares** | **cannot:** the check stores a *band*; `Farm.total_hectares` is a number. §III's "declared, not computed" cuts both ways |

So an account created purely from the check's answers holds an email address and some bands. To have a
farm profile at that point the account step must **ask three new questions** — farm name, nearest
town, contact person — which is new collection and a third consent, not a save button.

### 11.2 What the account is, in schema terms

Three candidate shapes were tested against the models Task A1 landed (`core/models/_core.py`,
commit `243cedd`):

| Shape | Verdict |
|---|---|
| `User` only | Cheapest, and honest — but "save my details" then saves nothing a farmer would miss, and the whole point is not retyping |
| **`User` + `Member{APPLICANT}` + `Farm`** | **Recommended.** Flow A step 1 already creates exactly this at self-registration, *before* the pledge, categories, turnover and fee — so it is structurally the same row, not a new state. A7 already makes `assert_eligible_for_assessment` raise for `APPLICANT`, so **no gate changes** |
| A sixth `Member.status` (`PROSPECT`) | Rejected. `Member.status` is frozen at five values by a guard test in A1, because `status` gates `assert_eligible_for_assessment` and feeds `FarmCategory` downstream |
| `Farm` with no `Member` | Not possible: `Farm.member` is a non-null FK (A1) |

**Wording consequence.** `APPLICANT` is the internal state; the public page must not say "application"
until they apply. The account CTA reads *"Create an account"*, and the step after it is still the
application flow (A6).

### 11.3 Two things this must not do

1. **It must not link `SelfCheckReport` to `Member` or `Farm`.** §4.1's "no FK to `Member` or `Farm`"
   stands, and §8's "writes nothing that could be mistaken for an assessment record" depends on it. The
   account captures its own fields by **prefill from the submitted form**, not by joining to a
   consented research row.
2. **It must not create `FarmCategory` rows.** "A tick is not an application" (A1 guard test
   `test_a_tick_is_not_an_application`): `FarmCategory.status` has no pre-application value, so the
   ticks wait for A6.

### 11.4 Decided 2026-11-04

| # | Question | Decision |
|---|---|---|
| Q7 | Are the three new fields (farm name, nearest town, contact) collected at account creation, or deferred to A6? | **Collected at account creation.** Otherwise the farm profile is empty and the account saves nothing a farmer would miss. The three fields are new collection and need the consent in Q8. |
| Q8 | The third consent: holding an account is a processing purpose separate from research and demographics. | **Yes, a third consent is required and does not exist yet.** It is not research consent (that one is about aggregate reporting) and not demographic consent (that one is about the census). It needs a retention answer, which this PRD deliberately does not have, and it is written by the group rather than by the build. |
| Q9 | Does an account require a verified email before it can be used again? | **Yes — but not in 1a: there is no mail provider (D84, 2026-11-05).** `User.email_verified_at` already exists for exactly this and stays null; the account step must say verification is unavailable rather than imply it happened. Until a provider exists an address is accepted as given, and the account is usable immediately. |

**Consequence for the build order, stated so it is not discovered late:** Q8 means the account
step cannot ship before its consent text exists. The self-check result page can therefore ship with
the account CTA **visible but the consent copy absent** only if the CTA is absent too — a form that
collects a farm name under the research consent would be a purpose mismatch, which is the one thing
§3.6 was written to prevent.

---|---|---|---|
| Q7 | Are the three new fields (farm name, nearest town, contact) collected at account creation, or deferred to A6? | Product owner | **Collected** — otherwise the farm profile is empty and the account only saves an email |
| Q8 | The third consent: holding an account is a new processing purpose, separate from research and demographics. Who writes and who approves that text? | Group / product owner | **Drafted by the build as a DRAFT to correct** (§11.6, 2026-11-05), because a group cannot approve a blank page. Two markers remain the group's: the retention period and the withdrawal address. The group approves the wording; the build does not. |
| Q9 | Does an account require a verified email before it can be used again? | Product owner | No — `User.email_verified_at` exists; verification is a friction decision, not a schema one |

---


### 11.5 Shape changed to a stepped wizard (2026-11-04)

The product owner judged the prototype and asked for **steps, not a long scroll**: a numbered nav at
the top and next/back paging. The five groups A–E become steps 1–5, the result is screen 6, and the
account is screen 7 (reached only from the result).

**What this does not change.** §4.3's contract holds exactly: one route, one view, parse → call a
service → render. The steps are client-side; no answer leaves the page until `submit`, and the
no-consent path still renders the result from the submitted form in the same request.

**What it does change, and the two traps it creates:**

- **Step boundaries are not validation.** A step can be left unanswered — the check is not a demand,
  and §3.5's "rather not say" logic already assumes silence is acceptable. No step may gate the next
  on completeness; only the *result* degrades, and it says so.
- **The dependency in §3.6 crosses a step boundary.** Demographic consent (E2) is refused without
  research consent (E1), and both sit on step 5 — so the disabled state is intra-step. If E2 is ever
  moved to its own screen, the refusal must survive a re-render or a reload, not just a checkbox
  toggle. A server-side test is required either way; the prototype only proves the UI.

**Contrast against the scrolling version, measured on the prototype** (`playwright`, 390/768/1280):
the records step holds seven controls, so it was the only group that scrolled materially on a phone.
It is rendered as compact rows (question + four answer chips on one line) rather than seven tall
cards, which is what makes "no scrolling" true rather than aspirational.

### 11.6 The third consent — **DRAFT**, for group approval (written 2026-11-05)

> **DRAFT — not approved, not for release.** Q8 says this text *"is written by the group rather than
> by the build"*, and the build cannot write it — but a build cannot ask a group to approve a blank
> page either. So this is a **draft to correct**, not a text to ship. Two answers below are still the
> group's and are marked `[DECIDE]`: the **retention period** and the **address to write to**. The
> text must not ship while either marker remains, and A6 must refuse to create an account without
> this consent (Q8's consequence: a farm name collected under the research consent is a purpose
> mismatch, which is what §3.6 exists to prevent).

**The checkbox and its explanation** — what a farmer reads on the account step:

> **May we keep your details so you can come back to this?**
>
> We hold your name, how to reach you, your farm's name and nearest town, and who to speak to about
> a visit. We use them to keep your application in one place and to contact you about it — nothing
> else. The committee and the administrator can see them; nobody outside the group can, and we never
> publish them. We keep them while your account is open and for **[DECIDE: proposed 12 months]** after
> the last time you contacted us, then we delete them. You can ask us to delete them at any time by
> writing to **[DECIDE: the administrator's email/phone — not yet published, `todo.md`]**, and we will
> do it within 30 days.
>
> *Unticked by default. Without it no account is created — but your result page still shows, and
> nothing about you is stored.*

**The "why we ask" body** — the result page and the help panel, in the voice the other two consents
use:

> This is not the research question and not the census question. Research consent asks whether your
> answers may be counted in totals for PGS South Africa and SAOSO; the demographic question asks
> whether census details may be counted too. This one is about the **account itself** — the name,
> contact and farm details the group needs in order to keep a conversation with you about an
> application.
>
> It sits after those two rather than beside them because holding an account is a purpose of its own.
> A consent that let "research" quietly cover it would be exactly the purpose mismatch the group's
> own POPIA position forbids.
>
> And leaving it unticked refuses nothing else. The check, the result and the to-do list still work
> and still store nothing. What it withholds is the account — because an account is the thing that
> needs your details to exist.
>
> *Source: POPIA s11 (consent as an act, not a default), s13 (purpose), s14 (retention). Q7's three
> fields are the collection this text covers.*

**What this draft assumes, stated so the group can reject any of it:**

- The fields are **Q7's**: name, email, farm name, nearest town, contact person. Anything else
  collected later (turnover, land history, the pledge) is covered by the application's own step, not
  by this consent — the pledge attests to land and sits where D83 put it.
- **Withdrawal works without an account**, as the research consent already promises: writing in is
  enough, and no login is required to be deleted.
- **English only until reviewed** (D44). This text is *not* machine-translated; an Afrikaans version
  lands when a named Afrikaans-speaking reader has reviewed it.
- It is **versioned, not edited**: `consent_text_version` records which text a member agreed to, so a
  later tightening of the wording is a new version and an existing member's consent keeps its meaning
  (the same rule as the frozen `Assessment.template_schema`).
- It is a consent to **hold and contact**, never to **publish**. A public farm profile is a separate,
  later, purpose-specific consent (`Farm.publish_consent_at` already exists for it).

**If the group prefers a shorter text**, the one sentence that cannot be dropped is the retention
answer. "How long do you keep it" is the question a POPIA information officer asks first, and it is
the one thing this PRD said it did not have.

## Pre-Flight Checklist

- [x] Models in a domain module — `core/models/_selfcheck.py`, re-exported from `core/models/__init__.py`
- [x] Views in `core/views/_public.py` (< 20 lines; the page is public, and the existing public views live there)
- [x] Forms in `core/forms/_selfcheck.py`
- [x] Services in `core/services/_selfcheck.py`, each with a Data Flow Contract
- [x] URLs in the public section of `core/urls.py`
- [x] Tests in `core/tests/test_selfcheck.py`
- [x] Migration: two new tables, additive only, no `AlterField`, reversible
- [x] No `select_related` needed beyond `category`; the report command aggregates in SQL
- [x] `transaction.atomic()` on `submit` — two tables, and a half-written consent is worse than none
- [x] No logic in templates — the result arrives as a frozen dataclass, money via `format_zar`
- [ ] **Second reader for the "why" copy** — the same human gate as the Crops template: a test can
      prove the citation resolves, not that the sentence says what the clause means
