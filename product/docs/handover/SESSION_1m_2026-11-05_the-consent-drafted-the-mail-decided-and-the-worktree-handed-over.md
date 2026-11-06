# Session 1m — 2026-11-05 — the consent drafted, the mail decision taken, and the worktree handed over

**Tag:** `1m` (after `1k`; `1g`/`1h` are the sibling's on `main`).
**Worktree:** `../pgs-visit`, branch `feat/mvp1a-visit`, on top of `781cf37`. `main` was never touched.
**Why a third record for one day:** each of `1j`, `1k`, `1m` ended at a task boundary — A3, A5, and
the close — and the repo's rule is one record per session block, not one per conversation.

---

## 1. What this block did

| Commit | What |
|---|---|
| `af94eec` | `docs(q8)`: the third consent **drafted and marked DRAFT** (`SELF_CHECK_PRD` §11.6) |
| `10bc6cc` | `decide(d84)`: **1a sends no mail**, and the interface must say so |
| this close | the state file rewritten for the handover |

## 2. Q8 — a draft, not a decision, and why that is the honest shape

Q8 says the account-keeping consent *"is written by the group rather than by the build"*. That is
right, and it is also why it stayed blank for a month: a group cannot approve a page nobody has
written. So `§11.6` now carries the checkbox wording, a "why we ask" body in the voice of the other
two consents, and an explicit list of what the draft assumes, so any of it can be **rejected** rather
than argued with.

Two markers are `[DECIDE]`, deliberately not invented, because inventing either would put a promise
in a consent text the group has not made:

- **the retention period** — POPIA s14 is why it cannot be omitted, and it is the one thing the PRD
  said it lacked. Proposed 12 months after last contact.
- **the address to write to** — the administrator's contact is still unpublished (`todo.md`), so the
  text cannot name it. That is now a blocker with a name rather than a vague gap.

The rule that keeps it honest later: it is **versioned, not edited** (`consent_text_version`), so a
later tightening is a new version and an existing member's consent keeps its meaning.

## 3. D84 — no mail in 1a, stated in the interface

The decision, from the product owner, ahead of the PGS demo: **no transactional provider in 1a.**
Q9 already allowed the address to be accepted as given; D84 turns that from a gap into a decision
with a visible consequence — `email_verified_at` stays null and the account step must render
*"email not verified — verification is not available yet"*. Never silence, never a fake tick.

The *boundary* is still built (`EMAIL_*` from env, one `send_email()` with an explicit timeout,
`locmem` in tests, a mailer-not-configured state that is visible), so choosing a provider later is
configuration rather than surgery. `todo.md` records what picking it up means: the provider, the
published administrator address (it is also the `Reply-To` — a `no-reply` sender silently loses
every escalation reply), and SPF/DKIM/DMARC on `organicguarantee.africa`.

**A rejected option, recorded so it is not revisited:** a local MTA. The host is a shared VPS; port
25 outbound and PTR make it a spam-folder generator, not a mail path.

## 4. What the next agent gets

- **The path, first, because it is the whole handover:** the A-sub-plan's code exists **only** in
  `C:/Users/Kobus Meiring/Documents/Dev/pgs-visit`. `pgs` is the sibling's `main`.
- **18 commits, none pushed.** Not a problem for the demo; pushing makes the branch visible to the
  sibling agent, so it is a deliberate act.
- **The gate cannot be run as `scripts/verify.sh` on this worktree** (§3.31: no `.venv`, so it picks
  a `python3` without celery and dies in step 2 with what looks like a broken tree). Run the five
  steps in §5, and drop the leftover test database first (§3.15, `_scratch/a5/dropdb.py`).
- **A merge will conflict in `HANDOVER.md` by design** — both strands rewrote the START HERE block.
  Keep both strands' state; do not pick one.
- **A6 is scoped in the START HERE block** (self-register → Q8 consent → account → pledge → categories
  → turnover → membership fee), including the rule that survived two tasks: build guards as services,
  never as forward dependencies on `FarmVisit`.

## 5. The gate, as this block leaves it

    1759 passed / 1 skipped / 8 xfailed in 172.19 s   (--create-db, cold; last full run, session 1k)
    tests/tools ................................. 185 passed   (after every doc edit in this block)
    context budgets ............................. 0 breaches

This block changed documents only — the spec, `todo.md`, `SELF_CHECK_PRD` and `HANDOVER.md` — so the
suite was not re-run whole; the two guards that read those files (`test_handover`,
`test_context::test_every_decision_row_link_resolves`) are in `tests/tools` and both ran. One of
them caught D84's first draft: a backticked `todo.md` is a link that does not resolve, and decision
rows are checked for that by a test now (`§3.29` is why it exists).
