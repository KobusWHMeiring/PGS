# Session 1k — 2026-11-05 — the fee scale is data, the gate is a service, and my own tests were the weak part

**Tag:** `1k` — `1j` is this strand's; `1g` and `1h` are the sibling's on `main`.
**Worktree:** `../pgs-visit`, branch `feat/mvp1a-visit`, on top of `781cf37`. `main` was never touched.
**Task:** **A5 — fees and the assessment fee gate**, on the default I proposed (land the guard as
a service; do not pull `FarmVisit` forward).

---

## 1. What landed

`66977cb` — `TurnoverBand`, `AssessmentFee`, migration `0013`, `declare_assessment_fee`,
`band_for`, `fee_cents_for`, `assert_fees_paid_for_assessment`, the OPP §2.3 scale seeded,
32 tests in `core/tests/test_fees.py`.

The OPP's notes under the table, not the table alone, decided the design. Four rules came out of
them and each one is cited at the function that applies it: fees are **per farm assessment visit**
(so `farm` is required — spec §4.1's member + visit line could not say it), payable **prior to**
the visit, only **fully paid-up members** are eligible, and renewal applies only where **no
significant change** has occurred. That last one is refused, not re-priced: *"the group may
require"* an initial-rate assessment is the group's discretion, and a computation that overrode a
declared field would be an adjudication — A3's lesson, applied to money.

## 2. The scale is data, and the printed table has a hole

`TurnoverBand` is a seeded table (§4.8, D12). The acceptance test for retargetability is exercised
directly: change a band's amount in the database and `fee_cents_for` follows — no migration, no
code edit. `AssessmentFee` **snapshots** the band code, its printed label and the amount, because
the schedule is policy that changes at an AGM while the row is what somebody was asked to pay.

The finding: the table reads *"Below R 250,000"* and then *"R 250,001 – R 500,000"*. A turnover of
R250,000.50 belongs to neither, as printed. Storing half-open bounds (`min` inclusive, `max`
exclusive) and keeping the printed text as `label` closes the hole with one rule instead of two —
rounding to whole rand would have been a second, invented rule.

## 3. Three things I got wrong, all caught by the repo's own habits

### 3.1 The "no hole" test could not see closed bounds

It swept cents in steps of 3 333 333 and compared each band's `max` to the next band's `min`.
Closing the bounds (`<=` instead of `<`) turns a gap into a one-cent **overlap** at exactly the
values the sweep never lands on, so the mutation passed. Rewritten to probe `min`, `min+1`,
`max-1`, `max`, `max+1` for every band and to assert a band never covers its own `max`; the
mutation now fails it and only it. **§1.39.**

### 3.2 A scripted slice move still imports

Cutting the two fee models out of `_membership.py` (which had crossed 30 KB) was scripted by
splitting on top-level `class` lines. `import core.models` passed; the suite did not —
`pledge_evidence_storage_location`, a plain `def` sitting *between* two classes, travelled into
`_fees.py`, and the `@deconstructible` decorator was stripped from the file that needed it. Only
A3's test that **writes a file** noticed. **§3.32.**

### 3.3 I skipped the red step on the first implementation pass

The tests were written first and the implementation second, but I ran them only after
implementing, so nothing was ever seen failing. The mutation pass is what actually proved the
guards (six probes, each failing exactly one named test), and then caught the hole in the first
one. Recording it because the TDD rule exists for exactly this: a test written before the code and
never watched failing is a test whose failing condition was assumed.

## 4. Two smaller things the suite caught

- `test_seed_deployment_seeds_categories_seals_and_committee_terms` pins the *key set* of
  `seed_deployment()`'s result, and the new `turnover_bands` key broke it. That test is doing its
  job; updated with the reason written down.
- The gate could not start at all: `--create-db` with a leftover `test_pgs_verify` from an
  interrupted run (`DuplicateDatabase`, then `ObjectInUse`) — `testing_hazards.md` §3.15–§3.16,
  which `verify.sh` guards by dropping the database first. Running the four steps **by hand** means
  running that DROP too; the script now lives in `_scratch/a5/dropdb.py`.

## 5. The gate

    1759 passed / 1 skipped / 8 xfailed in 172.19 s   (--create-db, cold)
    manage.py check ............................. no issues
    makemigrations --check ...................... no changes
    lint-imports ................................ 1 kept, 0 broken
    context budgets ............................. 0 breaches   (after the fees slice)

`core/models/_membership.py` was 31 KB with the fee models in it. They now live in
`core/models/_fees.py` — the OPP's own seam, §II ("Membership fees, farm assessment fees,
licensing fees") — at 24 KB / 9 KB.

## 6. What is next

**A6 (the application flow)** — the self-check's only exit. It needs two things from the product
owner that A5 did not: **Q8's third consent text** and the **SMTP** decision. Without them the
account step can still be built, but it cannot honestly claim to verify an email address.
Then B1 + B3 (`self_check` markers), then A8. Still open: the four roster/`APPLICANT` questions
from 1i.
