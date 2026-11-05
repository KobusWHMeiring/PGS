# Session 1j — 2026-11-05 — the pledge lands, and two guards that were green for the wrong reason

**Tag:** `1j` — `1i` is this strand's; `1g` and `1h` are the sibling's on `main`.
**Worktree:** `../pgs-visit`, branch `feat/mvp1a-visit`, on top of `781cf37`. `main` was never touched.
**Task:** **A3 — the pledge**, per the handover's "what is next" and the corrected D83 rule.

---

## 1. What landed

| Commit | What |
|---|---|
| `3f79284` | `docs(handover)`: session 1i's archive line, **which the close left out** — `tests/tools/test_handover.py` was red at `e05a954` |
| `ab42443` | `refactor(models)`: the seam cut, `_core.py` (21 KB) → `_membership.py` |
| `a4b2e4b` | `feat(a3)`: `Pledge`, `record_pledge`, migration `0012`, 30 tests |

**A3 is 30 tests**, not the 5 the plan named: the plan's five, the band as a parametrised table
stated in the documents' own numbers, the three constraints each proven by inserting the bad row
through the ORM, the consumer/farmer distinction, and the private-media boundary.

## 2. The seam cut, and the measurement that decided it

`_core.py` was 21 285 bytes against the 30 KB cap with `Pledge` still to add, and A6 and A4 to
follow. The spec already names the seam — §4.1 is *"Core & Membership"* — so `_core.py` keeps the
account (`User`, `UserRole`, `Role`, `Language`) and `_membership.py` takes the membership record
and what hangs off it, `Pledge` included, 24.7 KB with room.

Moved verbatim, proven by `makemigrations --check` reporting no change and the suite returning the
same count it had before the move (1687 / 1 / 8).

## 3. The band, and the test I wrote wrong first

The rule is `min_reading <= declared < max_reading` (D83) and it is implemented that way:
`ClearanceReading` holds what each document prints, `conflict_band()` returns `None` when they agree
(pasture, 12/12), and `lands_in_conflict()` is the half-open comparison. Correcting OPP §V later is
one line in the table plus a deliberate change to the expectations — not a migration.

**My first draft of the test widened the band.** I wrote `annual = 11 → True`, reasoning that "the
flag reports 'a human must look'". That is the same error D83 corrects, from the other side: below
the lower reading both documents agree, so there is no documentary conflict to report, and calling
it one turns a record of an ambiguity into a verdict on the farmer (D31). Caught before any
implementation code existed, and the test now says so by name:
`test_a_period_below_both_readings_is_not_a_documentary_conflict`.

**Why the flag is stored where `is_paid_up` is derived.** `is_paid_up` moves with the calendar, so a
stored boolean goes stale (D39). A signed declaration does not move, and the flag is evidence of
what the two documents said *on the day it was signed* (§I, Immutable History). Stated in the model
docstring, because the next reader will otherwise "fix" it into a property.

## 4. Two guards that were green and proved nothing — both now hazards

- **§1.37 — a `CheckConstraint` that evaluates to `NULL` is satisfied.** `in_conversion_months IN
  (12,18)` with a NULL month is `NULL`, not `FALSE`, so "in-conversion with no period selected" —
  the exact row the constraint exists to refuse — inserted cleanly. Found by the test asserting the
  exception; fixed with an explicit `__isnull=False` arm.
- **§1.38 — `FileField(storage=callable)` resolves the callable once, at field definition.** A
  storage built from `settings.PRIVATE_MEDIA_ROOT` at import cannot be redirected by
  `override_settings`, so the test asserting *where* evidence is written failed while the file sat
  in the repo's `private_media/`. Worse, `0012` was about to serialise this machine's path. Evidence
  now writes through a `@deconstructible PrivateMediaStorage` whose `location` is a property, and
  `base_url` is `None` — private media has no public URL at all.

## 5. Proving the guards can fail

Four mutations, each restored from a copy in `_scratch/a3/` (never `git checkout` — §1.36), each
failing exactly the intended test and nothing else:

| Mutation | Red |
|---|---|
| band half-open on the wrong side | the parametrised band table (perennial 18) |
| `PROTECT` → `CASCADE` | `test_a_recorded_pledge_cannot_be_deleted_by_deleting_its_member` |
| storage → default (public root) | `test_the_evidence_document_is_uploaded_under_the_private_root` |
| service stops refusing consumer declarations | `test_a_consumer_pledge_cannot_carry_a_land_history` |

The constraint mutation is in §1.37 — that one was caught before the mutation pass, by the test
itself.

## 6. The gate, and the harness that could not run it

`scripts/verify.sh` picks `python3` because `../pgs-visit` has no `.venv`, and `python3` here has no
`celery`, so the gate died in step 2 with an import error that reads like a broken tree
(**§3.31**). Its four steps were run with `python`, the interpreter the suite uses:

    1732 passed / 1 skipped / 8 xfailed in 218.71 s   (--create-db, cold)
    manage.py check ............................. no issues
    makemigrations --check ...................... no changes
    lint-imports ................................ 1 kept, 0 broken
    context budgets ............................. 0 breaches

One unexplained event, recorded rather than hidden: the first `fast.sh` run after the schema change
errored at setup in two `test_chatbot_grounding` tests (an empty `PublicDocumentQuerySet`); the next
three runs, including the full cold gate, were green. Not reproduced, so not diagnosed.

## 7. Two spec lines that contradicted the decision record

Corrected in `PGS_PLATFORM_SPEC.md` in the same commit, because leaving them made the spec disagree
with itself:

- §4.1's `Pledge` schema listed `evidence_photo` and omitted the declared periods and the flag.
- §7 step 3 said the method is `WRITTEN` or `VERBAL_RECORDED` — vocabulary that appears **nowhere**
  in code or in §4.1 (`SIGNATURE` / `DISTINCTIVE_MARK` / `VERBAL_WITNESSED`).

## 8. What is next

**A5 (fees)**, then A6 (the application flow), B1 + B3 (`self_check` markers), then A8. A4 and A7 can
move after A8. Still blocking the *account step only*: the third consent text (Q8) and SMTP.
Still unanswered from session 1i: the three roster ambiguities, and whether `APPLICANT` is the right
word for an account that has not applied.
