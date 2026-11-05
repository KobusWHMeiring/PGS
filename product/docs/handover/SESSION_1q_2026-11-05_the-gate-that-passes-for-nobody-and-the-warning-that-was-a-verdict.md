# Session 1q — 2026-11-05 — the gate that passes for nobody, and the warning that had to be a verdict

**Tag:** `1q` (after `1p`).
**Worktree:** `../pgs-visit`, branch `feat/mvp1a-visit`. `main` was never touched.
**Commit:** A7 plus this doc close.
**Gate:** 1960 passed / 1 skipped / 8 xfailed — **117 s cold and 118 s warm**, the test database
dropped before the cold run. The cold run reported **one failure**: `tests/tools/test_handover.py`
wanted an index line for this session, which did not exist yet. Both numbers are quoted with that
fact, because a count with a failure in it is not the same measurement as a green one.

---

## 1. What A7 asked for, and what it turned out to be

Seven lines of contract: `assert_eligible_for_assessment(member)` raises for `APPLICANT`, `LAPSED`
and `TERMINATED`, raises for an unpaid membership, passes for `ACTIVE` + paid up, and passes
`PROBATION` *with a warning*. Four rejections and one pass, each its own named error, tests first.

Sub-plan A is now **seven of eight**. B stays four of four.

| Piece | Where | Size |
|---|---|---|
| The family, the verdict and the gate | `core/services/_eligibility.py` | 9 KB |
| The two names `_membership` still raises, imported and re-exported | `core/services/_membership.py` | +12 lines, −7.5 KB |
| 16 tests, including the gap that has no code | `core/tests/test_eligibility.py` | 12 KB |
| 12 mutations, all caught | `_scratch/a7/mutate.py` | gitignored |

## 2. The first decision: `PROBATION` "passes with a warning" is not a shape

A function that raises has no return value to carry a flag. Two shapes were available and the
plan left the choice open:

- **return a frozen result**, or
- **raise nothing and let the caller read `member.status`.**

The second is the cheaper one and it is wrong here. OPP §4.6's exception — *"membership and the
right to use our logo will not be revoked, but the member will be under probation for one calendar
year"* — would then live in every caller, and the first caller that forgot it would refuse a
member the OPP explicitly protects. The gate is the one place the clause is cited, so the warning
is produced there.

So the gate returns `EligibilityVerdict(warnings=(EligibilityWarning(code, message),))`, and the
verdict has **two deliberate absences**:

- **no `allowed` field** — a field that can only ever be `True` invites `if verdict.allowed:` and
  then doing nothing about the refusal, which is the failure the raise exists to prevent. A
  refusal is an exception, not a value.
- **no `status` field** — the status lives on `Member.status`, and a copy in a frozen value object
  is a second source of truth, the same objection D39 raises to a stored `is_paid_up`.

The warning carries a **code** and a **sentence**: a view renders the sentence, a later guard
branches on the code, and no caller matches on English (the reason `MISSING_RECORD_BLOCKS_FINALISE`
is a constant). `probation_until` is printed when the group recorded it — otherwise D38's field is
write-only in both directions, set by nobody and read by nobody.

Two tests pin the shape: `test_probation_passes_with_a_warning`, and
`test_probation_does_not_excuse_an_unpaid_subscription` — **probation softens the standing rule,
never the money rule** (OPP §2.3's "fully paid-up" is not exceptioned by §4.6).

## 3. The second decision: in a running instance the gate passes for nobody — and that is now a test

`record_membership_fee()` and `record_membership_payment()` exist and are tested; **no view calls
them**. So every self-registration stays `APPLICANT` and unpaid, and A7's gate — being correct —
refuses all of them. A7 is the caller that makes the gap load-bearing.

The three options were a one-screen administrator page, the committee's surface (C1), or the gate
now with the surface named as the pilot blocker. **The third is what shipped, because the choice is
not the build's to make**, and it is recorded for the product owner in `todo.md::MISSING_FEE_SURFACE`
with the cheapest honest form of each:

1. two Django-admin actions on a new `MembershipFee` registration that call the two services —
   **not** an editable `paid_on` field, which leaves the member `APPLICANT` while the row looks paid;
2. C1's committee surface, which does not exist yet;
3. the gate now, the surface named (this session).

What was *not* done, because both would have made the demo lie: no `paid_on` the group never
received, and no test that reaches `ACTIVE` by writing the status.

The gap is asserted rather than described. `test_nothing_in_a_running_instance_records_a_membership_fee`
parses every module under `core/` (AST, not a substring — a docstring naming the service in
backticks is not a surface) and fails if a call to either service appears outside `_membership.py`.
The day somebody builds the surface, that test goes red and its message says exactly what to do:
delete it, close `MISSING_FEE_SURFACE`, and make sure the surface calls the services.

## 4. Three things the build corrected, and one mistake worth recording

1. **The code went to `core/services/_eligibility.py`, not `_membership.py`.** Adding the gate took
   `_membership.py` from 24.9 KB to **33.3 KB**, past the 30 KB cap. Slicing it back to 25.3 KB was
   the cap doing its job: `_membership` records what a member attested and invoiced, `_eligibility`
   decides what standing those records add up to. The plan's A7 section is amended in place with the
   dated reason, as A8's were.
2. **`MembershipUnpaidError` is reused and re-exported, not duplicated.** `_membership`'s fee gate
   raises the same refusal, so the class has to be one class.
3. **The order is standing-then-money**, matching `assert_fees_paid_for_assessment()`: telling a
   terminated member they owe a subscription is the wrong conversation. Pinned by
   `test_the_status_is_checked_before_the_payment`.
4. **The mistake.** While moving the class, it was briefly *defined* in both modules — two
   `MembershipUnpaidError`s, so `except MembershipUnpaidError` from the fee gate would not have
   caught the eligibility gate's refusal. Nothing failed, because nothing yet catches it. The fix is
   an import, and the guard is `test_the_two_modules_refuse_with_one_class`, which asserts **class
   identity** and which the mutation harness breaks on purpose. A green suite does not see a
   duplicated exception class any more than it saw A8's invisible form (§1.40): both are absence
   defects, and absence is what a test has to be written to look for.

**One hazard added to the harness, not the docs:** `python -m pytest` here is fine, but a Python
script that writes a repo file with `Path.write_text()` on this box turns **every** line ending into
CRLF — the tree then shows a whole-file diff that is not a change. `_scratch/a7/mutate.py` reads and
writes with `newline=""`, and two files it touched were normalised back to LF before the gate.

## 5. The gate

The five steps, run with `python` because `scripts/verify.sh` picks `python3` in a worktree with no
`.venv` (`testing_hazards.md` §3.31): `context.py --check` (0 breaches), `manage.py check` (no
issues), `makemigrations --check --dry-run` (no changes), `lint-imports --no-cache --no-logo`
(1 contract kept), then `pytest` with `PDFTOTEXT_BIN=scripts/_no_extractor` and the test database
dropped first (§3.15).

**117 s cold** (`--create-db`) and **118 s warm** (`--reuse-db`), same tree. The cold run was
**1959 passed, 1 failed**: the failure was `test_every_archived_session_is_in_the_index`, because this
file had no index line yet — a doc-shaped failure, fixed before the warm run. So the honest claim is
*"1960 passed / 1 skipped / 8 xfailed warm, 117 s cold"*, not *"green at 117 s"*.

**Mutations:** 12, in `_scratch/a7/mutate.py`, **all caught** — refuse probation, drop the warning,
let probation excuse arrears, drop the recorded end date, check money before standing, re-allow
lapsed/terminated/applicant, let an unrecognised status through, remove the unpaid refusal,
duplicate the exception class, and add a `record_membership_fee` call to a view.

## 6. What the next agent gets

- **Next: A4 — and A4 only.** Sub-plan A is finished when A4 lands. Do not roll it into this
  context.
- **The demo still needs its three data acts** and the dev database still has none of them:
  `python manage.py migrate` (0015–0017 unapplied), `seed_deployment`, then
  `load_template core/templates_data/crops.v1.json --activate`.
- **A7's gate has no caller either.** C1's `confirm_visit()` is where `assert_eligible_for_assessment`
  and `assert_fees_paid_for_assessment` meet — the member half and the farm half — and A5's fee gate
  deliberately still does its own paid-up check, so the two are not yet chained.
- **Waiting on the product owner, unchanged:** `todo.md::MISSING_FEE_SURFACE` (three options, above);
  the `1i` roster ambiguities; whether `APPLICANT` is the right word; the two `[DECIDE]` markers in
  `SELF_CHECK_PRD` §11.6 plus the same retention answer for the two public consents; the FORM's V21
  child as Yes/No or a percentage; five of the seven record "why" sentences that name no clause; and
  the `/ask/` eligibility-refusal link `SELF_CHECK_PRD` §4.3 asks for.
