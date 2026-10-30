# PRD: The escalation answer path — a refusal that can reach a person

**Status:** Refinement — design needed, no code written
**Owner:** Product owner + build
**Public title:** A question we cannot answer reaches a person
**Summary:** When the assistant cannot answer from the documents, its refusal should reach a person who can answer, instead of ending at a message.
**Public:** yes
**Last Updated:** 2026-10-21
**MVP:** MVP 0 follow-up (`/ask/` D) — a refusal is not shippable if the person it points to cannot be reached.
**Scope:** What happens after `EscalatedQuery` is written. **Not** in scope: the
machine-answer work (`CHAT_ANSWER_COVERAGE_PRD.md`), or the chatbot answering from email.
**Reference:** `core/models/_chat.py::EscalatedQuery`; `core/templates/chatbot/_thread.html`;
`core/templates/public/contact.html`; `core/services/_public.py` `PAGES["contact"]`;
`PGS_PLATFORM_SPEC.md` §13; `core/tests/test_chatbot_grounding.py`.

---

## 1. Problem Statement

Every refusal writes an `EscalatedQuery` with `status=OPEN`, and the refusal bubble offers
*"→ Send this question to the administrator"*. That link goes to `/contact/`, which renders
three chips — `email`, `phone`, `contact details to confirm` — and **no address, no phone
number and no form**. The visitor cannot send the question, cannot leave a way to be
answered, and cannot tell whether anything was recorded. The promise is empty, and the
`EscalatedQuery` row is invisible to the person who created it.

This is a trust failure, not a UX nicety: the refusal is the product's central claim
(D17), and the refusal's follow-up is the only thing that makes a gap useful.

## 2. Strategic Goal

A refused question reaches a person who can answer it, and the visitor knows what happened.

## 3. Options to decide (in order)

**D-A. Is the administrator's contact detail published at all?** `contact.html` withholds it
pending the group's confirmation (`C1_BUILD_PLAN.md` §6 #1). Until that is confirmed, an
escalation form is the only honest route, because it does not publish a personal address.

**D-B. Where does the visitor land after clicking the refusal link?**
1. **An escalation form** at `/ask/escalated/<public_uuid>/` (recommended): the question is
   pre-filled, an optional email field, a consent checkbox (POPIA), and a reference the
   visitor can quote. The `EscalatedQuery` row already exists, so the form attaches contact
   details rather than creating a second record.
2. A contact page with a real address — smallest change, but publishes a personal detail and
   still cannot tell the visitor what happened.
3. A mailto link — no tracking, leaks the question into a mail client, not auditable.

**D-C. How does the answer get back?** Options: an email to the address left on the
form (D10 is email-only); a reference the visitor returns with; both. Whatever is chosen,
the administrator's answer must be visible somewhere durable — the admin already edits
`EscalatedQuery.answer`, `answered_by`, `answered_at`.

**D-D. What is stored, and for how long?** An email address is personal data. POPIA consent
must be recorded per escalation, and the row needs a retention decision. The existing
`ChatSession.ip_hash` pattern — hash, never the address — is the precedent for what *not*
to store.

## 4. Technical Requirements (for the chosen option)

1. The refusal bubble must say what actually happened: *"This question has been recorded
   for the administrator"* plus the reference, not *"Send this question"* if nothing is sent.
2. The link must never point at a page with placeholder chips as if it were a contact route.
3. `EscalatedQuery` gains no new required field; contact details are nullable (an anonymous
   visitor may decline to leave one).
4. No email is sent by the chatbot service. The notification is a separate, retried task
   (`build_principles.md` §VII: `autoretry_for`, `max_retries`, `default_retry_delay`).
5. The question text is already preserved on the row (`question` survives message deletion).
6. A visitor's email must never appear in a public page or a log line.

## 5. Success Criteria

- [ ] A visitor who clicks the follow-up can send the question and receives a reference.
- [ ] An administrator sees the escalation, with contact details if given, in the admin.
- [ ] The visitor is told what happens next and (if email chosen) receives the answer.
- [ ] No placeholder chip is presented as a way to contact the group.
- [ ] UAT: a human asks an unanswerable question, follows the refusal, and is satisfied that
      a person will answer it.

## 6. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Collecting email without consent | Explicit checkbox, recorded with the escalation; retention decision before build |
| A form becomes a spam channel | The per-IP rate limit and `EscalatedQuery` dedupe already exist; reuse them |
| The promise is still too strong | Wording is a UAT judgement, not a test: "recorded" ≠ "answered by Friday" |
| Admin answers in the admin but nobody is notified | The notification task is part of the definition of done, not a follow-up |
