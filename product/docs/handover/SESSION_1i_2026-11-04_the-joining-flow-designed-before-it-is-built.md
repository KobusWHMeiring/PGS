# Session 1i — 2026-11-04 — the joining flow is designed before it is built, and two of my own findings were wrong

**Tag:** `1i` — chosen after checking `main`, where the sibling worktree had already taken `1g` and
`1h`. Two agents, two worktrees, one repo: the tag was picked from what was there, not from what came
next.

**Worktree:** `../pgs-visit`, branch `feat/mvp1a-visit`, on top of `781cf37`. `main` was never touched.

---

## 1. What the session was asked for, and what it turned out to be

The request was *"start work on the farm-visit checklist while the other agent does Docling."*
"Checklist" named four different things in this repo, so the first job was to find out which:

| Phrase | What it actually is |
|---|---|
| The visit records checklist | Task **E8**, Sheet I §2 — 26th of 40 tasks |
| Attachment readiness | Task **C3** |
| The three paper participant checklists 7.a–7.c | Out of scope; participants stay on paper |
| **"Am I ready to join?"** | **`/before-you-apply/`, Task A8, decision D71** |

The product owner's second message settled it: *"I've read the site, asked some questions, scrolled the
docs, and now I'm interested in joining so I want to assess my readiness."* That is A8.

## 2. The drift, named because it happened

A8 is sequenced behind the application flow (`SELF_CHECK_PRD` §5 step 1: *"A6 first… because it is the
exit"*). The product owner approved starting at **A1** as step one of that chain. **A1 was needed**:
the account at the end of the check creates `Member` + `Farm`.

**A2 was not on that path.** `CommitteeTerm` and the 2026 roster serve `validate_assessment_team()`
and visit scheduling — Task D. I called it "small and unblocks the roster seed" without saying the
roster did not move the checklist at all. Two turns were spent off the destination, and the product
owner caught it: *"wait I thought we were building the pre-joining checklist flow?"*

The response was to stop proposing, show the real dependency chain, and offer the prototype. That is
what turned the session around.

## 3. What landed

- **A1** (`243cedd`) — `Member`, `Farm`, `FarmAlias`, `FarmCategory`, `FarmContact`, `MembershipFee`,
  migration `0010`. 19 tests. `is_paid_up` derived from the fee row's own period (D39); no catchment
  (D37), no `current_status` (D35), no geometry column (D34); `FarmCategory.status` admits no
  pre-application value (D36); census fields on `Member`, never on `Farm`.
- **A2** (`4e86a81`) — `CommitteePosition` (eleven OPP §3.1 values), `CommitteeTerm`, the OPP §VII
  roster seeded from the reviewed corpus. 12 tests. `elected_on` null throughout because the source
  names only the AGM year; a blank `holder_name` **is** a vacancy.
- **D83** — the pledge stays in the application, after the account. Spec §18.3 row, `SELF_CHECK_PRD`
  §11.4 and §11.5, and the A3 rule corrected.
- **The approved prototype** (`0cc2112`) — `/before-you-apply/` as a stepped wizard.

## 4. The two corrections I had to publish

### 4.1 I proposed the wrong fix for a real finding

The three-way land-history table is verified and stands: **SAOSO 4.2.3 and the OPP pledge both say
12/12/18; OPP §V alone says 18/12/12.** The plan's rule referenced OPP §V, which is the lone outlier.

But the fix I recommended in `d83_pledge_placement.html` §4.1 — *"make the conflict a constant, not a
computation"* — was wrong. The premise (a boolean that is always true carries no information) was
sound; the claim that it would be always true was not. The correct rule is
`min_reading <= declared < max_reading`: the **band where the answer depends on which document you
read**. At 12 months for annuals the flag is genuinely `True`, and a farmer who signed the pledge as
printed is exactly the person it should flag. Pasture has no such band — both documents say 12.

Rewritten in the plan (with two added tests: past both readings, and pasture), in the spec's D83 row,
and in the artifact §4.1 — where the correction is visible rather than quietly edited, because the
artifact is a decision document and its §4.1 was a finding someone else may act on.

**The general lesson:** "the reference is wrong" and "the computation is wrong" are different
findings. Collapsing them produced a recommendation that would have deleted a working flag.

### 4.2 Two test-shaped traps, both now in `testing_hazards.md`

- **§1.35** — the plan's own A1 test hardcoded a fee period (`2025-03-01..2026-02-28`) and began
  failing on 2026-03-01 for a reason unrelated to the code. Any assertion about *now* derives its
  dates from `timezone.localdate()`.
- **§1.36** — `git checkout <file>` is not a mutation-testing restore. It restores HEAD, so it deleted
  this session's uncommitted model and the next run failed on an import. Restore from a copy outside
  the tree.

A third, found by mutation rather than by reading: A2's vacated-seat test **renamed the holder**, which
changed the natural key, so it could not detect the overwrite it claimed to guard — it passed against a
deliberately broken seeder. Rewritten to vacate a seated holder in place; the mutation now fails it and
only it.

## 5. The prototype, and what driving it changed

`product/design/before_you_apply_prototype.html`, approved 2026-11-04.

- **Generated, not retyped.** The 20 questions, help text, record answer set and every "why we ask"
  body come out of `d71_self_check_questions.html` (the wording ledger judged 2026-10-29) via
  `_scratch/dump_controls.js` → `_scratch/controls.json`. The prototype cannot paraphrase the decision
  it illustrates.
- **This repo's design system, not the generic skill's.** `designing-in-html` points at `--m-*`
  tokens and Inter + Playfair; that is another project's system and DESIGN.md §0 names it superseded.
  `brand-*` from `root.css`, real self-hosted Lora + Mulish, one forest beat for the result.
- **The shape was revised on the product owner's judgement** from one scroll to a stepped wizard
  (nav at the top, next/back paging). Recorded as `SELF_CHECK_PRD` §11.5 with the two traps steps
  create: a step boundary is **not** validation, and §3.6's E2-without-E1 refusal now crosses a step
  boundary and must survive a re-render.

Driven with Playwright at 390/768/1280. It found three bugs and one in my own verification:

1. Mobile counter read "Step 0 of 5" on the intro and "Step 6 of 5" on the account screen.
2. To-do wording read *"You do not fully have: sketches or diagrams…"* — lowercase, and identical for
   **No** and **Partly**. Now *"Not yet in place"* / *"Partly there"*, capitalised, each with its FORM
   citation, plus a second mirror sentence for rather-not-say answers (§3.5).
3. **My overflow check was not a check** — it compared `scrollWidth <= 391`. Measured properly, every
   width overflowed: the slide-in animation's 26 px transform extended the document's scrollable area
   for 220 ms. `main` is now `overflow-x: clip`; clean mid-animation.

## 6. What is next

**A3 (the pledge)** — with the corrected conflict rule. Then **A5** (fees), **A6** (the application
flow, the page's only exit), **B1 + B3** (`self_check` markers on the Crops template), then **A8**.
A4 and A7 can move after A8.

Blocking the *account step only*: the third consent text (`SELF_CHECK_PRD` Q8) and SMTP.

Unanswered from the review I offered: the three roster ambiguities (first-name-only holders, whether
Lilani Pretorius is a co-treasurer, Guy and Jacques unrecorded), and whether `APPLICANT` is the right
word for an account that has not applied.
