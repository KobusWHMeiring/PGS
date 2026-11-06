# Session 1r — 2026-11-05 — the last brick, and the denial rule written twice

**Tag:** `1r` (after `1q`). **The tag namespace has diverged:** `main`'s strand also uses `1n`–`1q`
for different sessions. The tag is only unique within a strand, so every index line for this branch
names the strand (`feat/mvp1a-visit`) and **nothing was renamed** — a rename would break the link
from an older session that says "after 1q".
**Worktree:** `../pgs-visit`, branch `feat/mvp1a-visit`. `main` was never touched.
**Commit:** A4 plus this doc close.
**Gate:** the five steps, run with `python` because `scripts/verify.sh` cannot start here
(`testing_hazards.md` §3.31) — **1971 passed / 1 skipped / 8 xfailed**, **220 s cold** with the test
database dropped first and **197 s warm** on the final tree.

---

## 1. What A4 asked for, and what it turned out to be

Fourteen lines of contract: `PriorCertification(farm, kind ∈ PGS|THIRD_PARTY, body_name,
certificate_ref, outcome ∈ GRANTED|DENIED, expires_on, denial_reason)` from FORM Sheet A, with a
`DENIED` row required to carry a reason (D30: *"a denial is materially relevant to a certification
decision"*; OPP §4.5 makes misuse of a third-party logo serious misconduct, which is why the body's
name is a column and not prose).

| Piece | Where | Size |
|---|---|---|
| The model, its guard and its three constraints | `core/models/_membership.py` | 24.0 → **28.7 KB** |
| The migration | `core/migrations/0018_mvp1a_a4_prior_certification.py` | new |
| 11 tests | `core/tests/test_prior_certification.py` | 7 KB |
| 4 mutations, all caught | `_scratch/a4/mutate.py` | gitignored |

**Sub-plan A is 8 of 8.** B remains 4 of 4. That is the whole of the sub-plan, and the only checklist
still open in `MVP1A_PLAN.md` §3 is the Definition of done for **all** of 1a — deliberately untouched.

## 2. The first decision: the file, and it is now nearly full

The plan's A4 section named `core/models/_core.py`, which is `User`/`UserRole`/`Role`/`Language` now.
`Farm`, `FarmAlias` and `FarmContact` live in `_membership.py`, so the new model went beside them.

Measured, not estimated: **24,067 → 29,409 bytes (28.7 KB)**, inside the 30 KB cap
(`build_principles.md` §II), so no `_prior.py` seam. That leaves **1.3 KB** — the next Farm-side
model cuts the slice rather than growing the file, and `_eligibility.py` (A7) is the precedent for
that cut. The plan's A4 section is amended in place with the dated reason, as A7's and A8's were.

## 3. The second decision: the denial rule is written twice, and the first mutation was wrong

`objects.create()` calls `save()` and never `full_clean()`, so a rule in `clean()` alone is green in
a form and absent from every test. The rule therefore lives in a `save()` guard **and** a
`CheckConstraint`, and each has its own test: the guard is what a caller sees, the constraint is what
a writer that bypasses `save()` (`bulk_create`, a data migration) cannot avoid. The guard is
deliberately a little stricter — whitespace-only is blank to a person, and a check constraint cannot
express `strip()` portably — so neither is a copy of the other.

`denial_reason` is `NOT NULL, default=""` and the check reads `~Q(denial_reason="")`, per §1.37.

**The mistake worth recording.** The mutation intended to prove §1.37 — "make the constraint read
NULL" — was written as `~Q(outcome="DENIED") | Q(denial_reason__isnull=True)`, and it was
**not caught**. The reason: on a `NOT NULL` column `denial_reason IS NULL` is `False`, never `NULL`,
so the constraint stayed exactly as strict as before. That is §1.37 read backwards — the trap is not
"a check that mentions `isnull`"; it is "a check whose *expression* evaluates to `NULL`", and only a
**nullable column** can produce one.

The honest mutation, and the one that is now in `_scratch/a4/mutate.py`, reverts the column to
`null=True` with no default in both the model and `0018`, rebuilds the test database, and inserts the
row the way a caller with nothing to say writes it:

```python
PriorCertification.objects.bulk_create([_row(farm, outcome=DENIED)])   # reason omitted, not ""
```

On the nullable column that stores `NULL`, `NOT (NULL = '')` is `NULL`, Postgres satisfies the
constraint, and the insert succeeds — `DID NOT RAISE IntegrityError`. The test is written with the
reason **omitted** rather than passed as `""` for exactly this reason: passing `""` would keep the
bad row out even under the mutation, and the test would prove nothing.

## 4. The third and fourth decisions: no expiry on a denial, and nothing invented

**A `DENIED` row may not carry `expires_on`.** A denial issued no certificate, so an expiry on it
describes an instrument that never existed — D38's trap, a field that can be entered and means
nothing. Both the guard and a constraint refuse it, for the same bypass reason as the reason rule. On
a `GRANTED` row the date is **optional**, because "we do not know when it lapsed" is a real answer
and a required date would be invented from nothing; one of the three rows in the multi-row test
carries no expiry and says so.

**Nothing beyond §4.1's list was added** — no `declared_on`, no source document, no "verified" flag.
A test pins the field set, so the next person who wants a verification flag has to argue with the
spec's line 207 rather than quietly adding one.

**No writer in 1a, and no gap test.** C2's questionnaire renders Sheet A; the visit and its report
read the rows. Unlike A7's fee surface, nothing is refused on a missing prior-certification row, so
the gap is one sentence in the model docstring and no source-parsing test. A test asserting a gap
nobody depends on gets deleted by the first person who needs it, and that deletion would take a real
guard with it.

## 5. A hazard this session paid for: `read_text()` hides the CRLF it is meant to reveal

The multi-line mutation anchor "not found in `core/models/_membership.py`" while `grep` showed the
text present. The model files in this checkout are **CRLF** (`_core.py` too, so it is the checkout and
not this session's edits) and the anchor was written with `\n`. The trap is the *diagnosis*: the probe
that "proved" the file was LF counted `\r\n` on `Path.read_text()` output, which is universal-newline
text mode and has already converted every `\r\n` to `\n` — so it reported `0` with the file 632 lines
of CRLF. Only `open(..., newline="")` or binary mode tells the truth. Appended to
`testing_hazards.md` §1.41. The harness now adapts an anchor to the file's own line endings, and
`git diff --numstat` after the run reads **107 added, 0 deleted** — the file was restored byte for
byte, not re-normalised.

## 6. The gate

Five steps with `python` (§3.31): `context.py --check` (every budget holds), `manage.py check` (no
issues), `makemigrations --check --dry-run` (no changes), `lint-imports --no-cache --no-logo`
(1 contract kept, 0 broken), then `pytest`, the test database dropped first (§3.15):

- **cold, `--create-db`: 1971 passed, 1 skipped, 8 xfailed, 220 s**
- **warm, `--reuse-db`: 1971 passed, 1 skipped, 8 xfailed, 197 s** on the final tree (two earlier
  warm runs of the same count measured 286 s and 311 s)

The count is 11 above `1q`'s 1960, which is A4's test file exactly. The times are **not** the
120 s the last session measured, and the ordering is not stable — warm measured slower than cold
twice and faster once, across 197–311 s for one tree. That is the box, not the change: the sibling
worktree was active throughout (§3.17: quote both, or claim nothing). What the numbers are evidence
for is the **count**, and that every run is green. `tests/tools/test_handover.py` was re-run last,
after this file and its index line were written: 4 passed.

**Mutations:** 4, in `_scratch/a4/mutate.py`, **all caught** — drop the denial guard, drop the
`body_name` guard, let a `DENIED` row carry an expiry, and revert `denial_reason` to a nullable
column (which edits the migration too and rebuilds the database, because a constraint the database
never got is a constraint nobody has seen refuse anything).

## 7. What the next agent gets

- **Sub-plan A is finished: A is 8 of 8, B is 4 of 4.** The next decision is not a task — it is
  **merge `feat/mvp1a-visit` to `main` (both strands have rewritten HANDOVER's START HERE, so that
  merge conflicts by design) or start C1** (`confirm_visit()`, where A5's fee gate and A7's standing
  gate finally meet, and the answer to `MISSING_FEE_SURFACE` is most likely to land).
- **The demo still needs three data acts, and the dev database has fewer migrations than the last
  handover claimed.** `python manage.py showmigrations core` on this box shows the last applied
  migration is **`0009`**; **`0010`–`0018` are unapplied** (not "at 0012"). So: `migrate`,
  `seed_deployment`, `load_template core/templates_data/crops.v1.json --activate`. Not run here —
  A4 is a model task and the dev database is not this session's to move.
- **`PriorCertification` is empty in the demo and nothing refuses anything because of it.** C2 is
  the writer.
- **Waiting on the product owner, unchanged and none of it actioned here:** `todo.md::
  MISSING_FEE_SURFACE` (three options); the `1i` roster ambiguities; whether `APPLICANT` is the right
  word; the two `[DECIDE]` markers in `SELF_CHECK_PRD` §11.6 and the same retention answer for the
  two public consents; the FORM's V21 child as Yes/No or a percentage; five of the seven record "why"
  sentences that name no clause; and the `/ask/` eligibility-refusal link `SELF_CHECK_PRD` §4.3 asks
  for and A8 did not build. **Nothing new was parked**: A4 raised no question that is the owner's
  rather than the build's — a prior certification with no `certificate_ref` is a real answer, so the
  field is optional rather than a decision anyone has to take.
