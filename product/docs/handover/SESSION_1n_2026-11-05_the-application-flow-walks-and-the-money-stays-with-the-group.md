# Session 1n — 2026-11-05 — the application flow walks, and the money stays with the group

**Tag:** `1n` (after `1m`).
**Worktree:** `../pgs-visit`, branch `feat/mvp1a-visit`, on top of `781cf37`. `main` was never touched.
**Commit:** `5f64fd6` — `feat(a6): the application flow, and the funds stay with the group`.

---

## 1. What landed

**A6, the application flow (spec §7, D83, Q8, D84).** The applicant's own path, in one walkable
sequence: self-register → the Q8 consent → the account → the pledge → categories → turnover → a
summary that says what is owed and who records it. Then B1 + B3, then A8 — unchanged.

| Piece | Where |
|---|---|
| `ConsentText`, `ConsentRecord`, `ConsentPurpose` | `core/models/_consent.py`, migration `0014` |
| The Q8 draft as data, seeded create-only | `core/services/_seed.py` (`ACCOUNT_CONSENT`) |
| The flow's rules (account, consent, steps, ticks) | `core/services/_application.py` (new slice) |
| Membership fee + payment recording | `core/services/_membership.py` (no view calls them) |
| Four steps, a summary, sign-in/out | `core/views/_portal.py`, `core/forms/_application.py` |
| Pages and CSS | `core/templates/portal/`, `core/static/css/portal.css` |
| 32 tests, one seed guard | `core/tests/test_application.py`, `test_seed_deployment.py` |

**Gate (its five steps run with `python`; `scripts/verify.sh` cannot start here — §3.31):**
`context.py --check` 0 breaches · `manage.py check` clean · `makemigrations --check` clean ·
`lint-imports` 1 kept / 0 broken · **1794 passed / 1 skipped / 8 xfailed in 152.70 s** `--create-db`,
after dropping the leftover `test_pgs` (§3.15). Warm run without `--create-db`: 153.55 s. Quote both
(§3.17) — they agree here because the database was created once in each.

## 2. Three refusals, which are the substance

**No consent, no account.** `ConsentText` is versioned, never edited, and the account step posts the
version it *rendered*. A form opened before the wording changed is refused
(`ConsentTextChangedError`) rather than recorded against text the farmer did not read — a consent
record naming the wrong wording is worse than none, because it looks like evidence. With no
`ACCOUNT` row at all the page says the wording has not been written and creates nothing: the
checkbox never exists without a text behind it.

**The applicant cannot pay.** No view writes a `MembershipFee` row. The fee year is the group's
(D39: "payable by end of February" is policy, and the OPP states no fee year at all), so a
self-registration that wrote a period would invent policy; and a `paid_on` written by the applicant
would make `assert_fees_paid_for_assessment()` lie. `record_membership_fee()` (explicit period and
amount) and `record_membership_payment()` (sets `paid_on`, moves `APPLICANT → ACTIVE`, never out of
`TERMINATED` — OPP §4.7 makes reinstatement a committee act after a calendar year) are built and
tested and called by no view. That is A5's pattern: `assert_fees_paid_for_assessment()` waited for
C1's `confirm_visit()`. **Consequence, recorded in `todo.md`:** in a running instance every applicant
stays `APPLICANT` and unpaid, so A7's gate passes for nobody until a recording surface exists. That
surface is A7's or a one-screen administrator page — a decision, not a gap to discover late.

**The pledge is history.** A second POST to `/apply/pledge/` redirects forward instead of appending a
second attestation. `land_history_conflict` is still A3's: the view test posts the OPP's printed
12/12/18 and asserts `True`, which is the band where SAOSO 4.2.3 and OPP §V disagree (D31).

## 3. The shape that makes a demo feel real

**Steps are derived from rows, never from a session.** "Where am I?" is a query — a pledge exists,
categories exist, a fee is declared — so a refreshed tab, a bookmarked URL and a stale back button
all resolve to the same honest answer. `/apply/` is the single entry point and resumes at the first
open step; the order is enforced in `_step` by `assert_step_ready()`, not by URL shape, and a step
reached too early redirects rather than rendering a half-filled later form.

**The Q8 draft is shown as a draft.** The two `[DECIDE]` markers are rendered on the page a farmer
reads, with a banner saying the group has not approved the wording — not hidden in the PRD. The
account is allowed under it, because refusing every account until approval dead-ends the flow the
demo exists to show; §11.6's "must not ship" is a release rule. Approval is one data edit
(`approved_at`), the banner disappears, and nothing else changes. Written up as `SELF_CHECK_PRD`
§11.7 so the product owner can overrule it with one line.

**D84 is visible, not implied.** The account step says email verification is unavailable; the
summary says the address is not verified. Two ways in the test: the context flag
(`email_verification_available is False`) and the sentence. A test of the sentence alone passes while
the flag says otherwise, and the flag is what a later provider decision turns on.

## 4. Five guards, each watched failing

Mutation-testing script: `_scratch/a6/mutate.sh` (restores from copies, never `git checkout` — §1.36).
All five were caught:

| Mutation | Test that caught it |
|---|---|
| `if not consent_given` → `if False` | `test_registration_without_consent_is_refused` |
| `if consent_version != text.version` → `if False` | `test_a_form_rendered_before_the_wording_changed_is_refused` |
| `assert_step_ready(...)` → `pass` in `_step` | `test_a_step_cannot_be_reached_before_the_step_before_it` |
| `if member.status == APPLICANT` → `if True` | `test_recording_payment_does_not_reinstate_a_terminated_member` |
| seed rewrites the consent body | `test_seeding_never_rewrites_a_consent_wording` |

The script checks the mutated file still parses before it runs the test, because a mutation that is
a syntax error "fails" a test without proving anything.

## 5. What the next agent gets

- **Still `../pgs-visit` only.** Nothing pushed; 19 commits ahead of `781cf37`; `main` in `pgs` is
  the sibling's.
- **Next: B1 + B3** (the template's `self_check` markers), **then A8** (the public self-check — its
  only exit is this flow, which now exists). **A7** (eligibility gates) can move after A8.
- **A7 needs the payment surface first** if it is to be demonstrable; the transition it reads exists
  (`record_membership_payment`), the way to reach it does not. See `todo.md`.
- **The Q8 questions are still the group's:** the retention period, the withdrawal address, and
  whether `APPLICANT` is the right word. None blocks A8's structure.
- **No UAT checklist for A6.** 32 automated tests and one human judgement left (does the flow read as
  one thing on a phone, is the consent readable before it is ticked). Listed in `todo.md` rather than
  written, because nothing here has been seen in a browser yet.
- **A merge will still conflict in `HANDOVER.md` by design** — keep both strands' state.
