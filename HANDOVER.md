# Handover — Final PRD Review

**For:** the next developer, doing a final review of the product spec before implementation.
**From:** design session, 2026-10-18
**Repo state:** greenfield. No application code, no git history, no Docker. Spec and plan only.

---

## What to review, in order

| # | Artifact | What it is | Time |
|---|----------|-----------|------|
| 1 | `product/backlog/Refinement/PGS_PLATFORM_SPEC.md` | The aimed (target-state) spec. 19 sections + traceability appendix. | 45 min |
| 2 | `product/docs/context/build_principles.md` | The governing rules, reconciled from Harvester + Homtini. | 10 min |
| 3 | `product/backlog/Refinement/MVP0_PLAN.md` | MVP 0 implementation plan, four sub-plans. | 30 min, skim |
| 4 | `tests/uat/mvp0_standards_and_public_site_uat.md` | The UAT — read the `Judgement:` clauses carefully. | 10 min |
| 5 | `pgs_docs/` | The authoritative source documents. **Spot-check the spec against these.** | as needed |
| 6 | `product/design/*.html` | Two review artifacts: the decisions review and the O4 explainer. | optional |

**Do not read `prd.md` as the spec.** It is the original input, now superseded. It is kept only as provenance. It is escaped Markdown (a pasted chat log) and its three-app split was rejected.

---

## The starting position

The original PRD was strong on the two hardest constraints — zero-build monolith, offline-first split-sync — and thin on almost everything else. The session produced an aimed spec by reading the four governing documents properly. The headline number: **the OPP was only half-read when the first draft was written, and the unread half contained three material gaps.** That is the main reason to review rather than trust.

### Seven overrides (spec §18.1)

| # | Override | Reviewer should ask |
|---|----------|---------------------|
| O1 | Normalised `AssessmentAnswer`/`AssessmentVerdict` rows + raw payload, instead of one JSON blob | Is the queryability worth the extra rows? (§4.7) |
| O2 | Photos as `Blob`s, not Base64 | Safe. |
| O3 | Escalation on a structured `insufficient_context` flag, not substring matching | Safe. |
| O4 | `knowledge/` as a one-way standards library; `core/` for everything user-facing | **The split line moved mid-session.** Read §18.2 — the case is now narrower and Option A is defensible. |
| O5 | Roles plural per user (`UserRole`), plus a separate visit role | Safe. |
| O6 | Added missing models and sign-off gates | Check the gates aren't over-restrictive: `CERTIFIED` is blocked while a Critical action is open, and certificates are blocked unless paid up. |
| O7 | Three gaps found in the unread half of the OPP: the third seal, aggregation (§VI), committee positions | Verify against OPP §V, §VI, §3.1, §VII. |

### Thirteen decisions (spec §18.3)

D1 HTMX allowed · D2 filesystem media, no S3 · D3 Gemini · D4 both review cadences · D5 password accounts · D6 free text, voice deferred · D7 bilingual · D8 this app *is* the website · D9 keep originals · D10 email only · D11 pasture-raised deferred · D12 retargetability required · D13 aggregation data now, workflow later.

**The three expensive-to-reverse ones are D1, D2 and D3.** D2 in particular converted a Medium risk into the spec's highest-severity one (R11).

---

## Where I would look hardest

These are the places I am least confident, ranked. If you only check five things, check these.

1. **§16 R11 — the accepted backup gap.** Filesystem media plus a single external hard drive means one disk failure, theft or fire loses every piece of certification evidence. The risk is recorded and *accepted*, not solved. Confirm the group understands that.
2. **§4.3 + §12 — the claim-discipline rule.** The spec says the public surface may reproduce only the four FORM outcomes and the two *active* seals, and never "pasture raised" or "GMO free". This is a legal-adjacent posture (DALRRD; Consumer Protection Act). Confirm it is the right posture, not just the cautious one.
3. **§9–§10 — the offline design.** This is the hardest part of the whole platform and has never been tested on a real device in a real dead zone. **MVP 0 does not touch it.** The plan includes a two-day throwaway spike (§19) — argue if you think it should come first.
4. **§4.8 — retargetability.** The claim "a retarget must not require a migration" is testable and is an acceptance criterion. Check the code/data line is drawn in the right place; `Seal` and `Category` as tables is the part most likely to be wrong.
5. **§18.2 — the O4 split.** Read the honest note at the end. `knowledge/` is about four files. If you think the second app is ceremony for its own sake, say so — it is a small edit to collapse it.

### Open, unresolvable from here

- **Existing certificate data.** The live WordPress site is a de-facto registry (§12.1), but outcomes for 2023 and 2024 are **missing** from it. Only one certificate is currently valid (Favour Farm, Feb 2026); one lapses in November 2026 and the rest expired years ago. Confirm with the group before seeding anything.
- **Consent for already-published personal data.** Farmer and consumer *names* are published on the current site. `publish_consent` is modelled but nobody has been asked. This is a POPIA obligation, not a formality.
- **Server and hosting.** Not decided anywhere. The backup script assumes a machine with an attached drive.
- **The OPP's section numbering collides with numbered list items.** Flagged in `MVP0_PLAN.md` sub-plan B; the parser may need a guard. Expect to fix this during ingestion.

---

## Two deliberate divergences from Harvester's build principles

Both are recorded rather than done quietly (spec §0):

1. **`core/models/` is a package, not a single file.** Harvester mandates one `models.py`; Homtini's 30KB cap makes that impossible at this domain size. Harvester's own `models.py` already exceeds the cap.
2. **Two apps, not one.** Harvester's baseline is a single Monolithic Core; it does permit sibling apps "when the domain is sufficiently distinct", so this is within the letter of the rules.

---

## What is deliberately *not* built

The spec separates permanent exclusions (§17.1) from post-MVP deferrals (§17.2). Of note: **voice notes are fully designed but not built** — the schema ships in the first migration, the recorder UI and transcription do not. That is the single largest deferral and was chosen because voice adds a capture surface, a second binary queue, a transcription pipeline, a human-review step and a POPIA consent gate.

---

## Backlog mechanics

This repo uses the **Harvester backlog convention** (`product/backlog/CONVENTION.md`).

```bash
python product/backlog.py            # dry-run: drift + suggested moves
python product/backlog.py --write    # regenerate the index
python product/backlog.py --apply    # move files to match Status:
```

Use the **local** skills `.agents/skills/pgs-reading-the-backlog` and `pgs-maintaining-the-backlog`. Do not use the generic `reading-the-backlog` / `maintaining-the-backlog` skills — they assume a River-style layout.

Both artifacts currently sit in `Refinement/` because they are awaiting this review. On approval, the convention is:

- `PGS_PLATFORM_SPEC.md` → stays (it is a living target-state document, not a build item).
- `MVP0_PLAN.md` → `ready/`, with `Status:` updated to `Ready`.
- On completion → `Done/`, and only after the UAT sign-off table is complete.

**Not yet set up:** `summarise.py` / `product/docs/state/` (premature without code), `docker-compose.yml`, the git repository itself. The plan's Task A1 does `git init` as its first step.

---

## Review output I would find most useful

1. **Contradictions against the source documents** — anything in the spec that the OPP, SAOSO, FORM or prep list does not support.
2. **Missing domain areas** — the unread half of the OPP yielded three; assume there may be a fourth.
3. **Scope arguments** — particularly whether the registry should launch seeded from existing records at all, and whether MVP 0's order is right.
4. **A verdict on O4** — accept the two-app split, or collapse to one.
