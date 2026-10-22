# Spike: `0∥` — Offline capture on the assessor's real device

**Status:** Spike — not started. Brief written from the spec; no code, no decision yet.
**Owner:** Build (whoever runs the two days) · Decision owner: Kobus Meiring (Product)
**Last Updated:** 2026-10-22
**Scope:** Throwaway code, two days, one real iPhone, one real low-signal location. **No
production tables, no migrations, no merged app.** The deliverable is a *measurement*, not a library.
**Reference:** `Refinement/PGS_PLATFORM_SPEC.md` §19 (slice **0∥**), §10 (compatibility, quota
safety), R6 (device storage risk), §18.3 **D25**/**D26** ·
`../ready/MVP1A_PLAN.md` §0, §2 (sub-plan G) · `product/design/d1_mvp1_shape_exploration.html`

---

## 1. Why this exists

`PGS_PLATFORM_SPEC.md` §19 names `0∥` as a delivery step in its own right, and D26 makes it a
**hard gate**, not a parallel track:

> The spike's outcome determines what `VisitSyncEnvelope` must carry: if persisted storage holds,
> the design stands; if eviction or quota kills long sessions, the envelope needs checkpointing or a
> file-export fallback (envelope v2); if offline is not viable on the target devices at all, `1b` is
> re-planned and only `1a` ships. **Freezing a contract before that answer is known is the most
> expensive sequencing error available in this slice.**

**This file existed nowhere in the backlog until 2026-10-22**, while the two items it gates
(`ready/MVP1A_PLAN.md`, `ready/MVP1A_PRD.md`) sat in `ready/` and sub-plan G sat unresolvable at
"Blocked on `1∥`". The gate was only visible in `HANDOVER.md` §3 and the spec. Recorded here so the
next reader of the index sees *why* `ready/` is not executable yet.

## 2. The question, and the three answers that matter

One question only: **does offline-first work on the device the assessor actually carries?**
D26 collapses to three mutually exclusive outcomes, and the spike must land on exactly one:

| # | Answer | Consequence for `1∥` |
|---|--------|----------------------|
| **A** | Persisted browser storage holds for a whole visit | The design stands. `VisitSyncEnvelope` v1 freezes as specified |
| **B** | Eviction or quota kills a long session | v1 **gains checkpointing or a file-export fallback** → envelope v2 |
| **C** | Offline is not viable on the target devices at all | `1b` is re-planned; **only `1a` ships**; the MVP 1 claim (D25) does not attach |

Anything that is not one of those three is not a result.

## 3. What to measure

Record numbers, with the device, OS version and location noted, because a "felt fine" note is not
evidence.

- [ ] **Does IndexedDB persist** across app backgrounding, a screen lock, and killing Safari? Time to
      data loss, if any.
- [ ] **Quota**: `navigator.storage.estimate()` before and after — usage, quota, and whether
      `navigator.storage.persist()` is even granted on iOS Safari ≥16 (§10 quota safety, R6).
- [ ] **A long session**: the paper equivalent is a multi-hour visit. Does a session of that length
      survive it, or does the frame get evicted while the assessor is still walking?
- [ ] **Photo capture**: can the device camera feed a blob into IndexedDB at the size a visit needs,
      and does the store survive ten of them?
- [ ] **Dead-zone behaviour**: what the app can do with genuinely no signal — not throttled, not
      "airplane mode on wifi".
- [ ] **The sync edge**: does a single background/foreground cycle mid-capture corrupt anything? This
      is the assumption the "three-phase split-sync" rests on.

## 4. Out of scope — deliberately

- The service worker, the IndexedDB schema, `visitPack` and `VisitSyncEnvelope` themselves. Those are
  `1b` and `1∥`. **Writing them here is the error the gate exists to prevent.**
- Any template, verdict or assessment-domain code. That is `1a` sub-plans A–F and is **not** gated on
  this spike — `ready/MVP1A_PLAN.md` §2: *"Domain work starts immediately."*
- Polish, offline UX, or anything a user would see. Two days, one device.
- Anything that stays in the repository as production code. If the prototype turns out to be useful,
  it is evidence that a rewrite is cheap — the numbers still carry the decision.

## 5. What it blocks, and what it does not

| | |
|---|---|
| **Blocks** | `1∥` (the seam contract), `ready/MVP1A_PLAN.md` sub-plan **G1–G5**, and all of `1b` |
| **Does not block** | `ready/MVP1A_PLAN.md` sub-plans **A–F** — the in-office domain work, including Task B3's Crops template |
| **Gate status in HANDOVER** | §3 "0∥ spike complete — ⚠️ Not done. Before `1∥` freezes `visitPack`/`VisitSyncEnvelope`" |

## 6. How this closes

There is no UAT for a spike — nothing user-facing ships. Closing it means:

1. The measurements above are written down, with the device named.
2. **One** of the three answers in §2 is recorded, and D26's row in
   `Refinement/PGS_PLATFORM_SPEC.md` §18.3 is updated in place with the outcome and its date.
3. If the answer is B or C, the consequence is scheduled explicitly — a v2 envelope task, or a
   re-plan of `1b` — rather than absorbed into "we'll deal with it in 1b".
4. This file moves to `Done/` and `HANDOVER.md` §3's gate row flips.

## 7. Risks

| Risk | Mitigation |
|------|------------|
| The spike is skipped because `1a` "can start anyway" | True for A–F, false for G — and G is where the irreversible contract is. The gate is on `1∥`, not on the whole of `1a` |
| It runs but produces opinion, not numbers | §3's list is the evidence bar; a result without a device name is not a result |
| The throwaway prototype is promoted to production | §4. A prototype promoted without the rewrite is a `1b` that was built on a guess — the exact error D26 names |
| Someone freezes `1∥` "provisionally" while it runs | D26: not permitted. Contract-tested against both sides means *both sides exist* |
