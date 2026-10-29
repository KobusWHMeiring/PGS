# PRD: The `/ask/` panel — the answered board, and a way to start over

**Status:** Refinement — the product owner's request, 2026-10-28, for the next session. Two items; the
first may not be the problem it looks like (see §1.2), so the session starts by settling which of
three causes it is.
**Owner:** Kobus Meiring (Product) · Build
**Last Updated:** 2026-10-28
**MVP:** MVP 0 — a refinement of the shipped `/ask/` surface (D62), not new scope for MVP 1a.
**Scope:** The `/ask/` panel only: what a visitor sees of *Questions we have answered*, and a control
to clear the conversation on screen. **Not** the answer page (`/ask/<slug>/`), not the chatbot's
retrieval, prompt contract or audit, and not the board's data model.
**Reference:**
- `product/backlog/In Progress/ASK_SURFACE_PRD.md` — the surface this refines (D62, §4a)
- `core/templates/chatbot/panel.html`, `_thread.html`, `_board.html`
- `core/views/_chatbot.py` (`ask`), `core/services/_ask.py` (`board_context`)
- `core/models/_chat.py` (`ChatSession`, `PublicQuestion`), `core/admin.py` (`publish_cards`)
- `product/design/DESIGN.md` — the panel is a product surface: `brand-*` tokens, ≥44 px targets
- Retentions and evidence: **D59** (keep every transcript) and **P2.5a** (`ChatMessage.citations`,
  `grounding`) — these constrain what "clear" is allowed to mean

---

## 1. The two requests, as given

> "make some refinements to the `/ask/` interface including hooking up Questions we have answered,
> and allowing for a 'clear conversation' button."

### 1.1 A clear conversation button

**There is no such control today.** Measured 2026-10-28: `grep -rn "clear\|reset\|new conversation"`
over the three chatbot templates, `core/services/_ask.py` and `core/views/_chatbot.py` returns
nothing. A visitor's only way to start over is to clear their browser cookies, because the panel
renders every message in `session.messages` (`core/views/_chatbot.py:157`) and keeps the conversation
in the Django session under `CHAT_SESSION_KEY`.

### 1.2 "Hooking up Questions we have answered" — already wired on the server

**The board is not unwired.** The panel includes `_board.html` (`panel.html:106`) inside its own
section below the composer, and `core/views/_chatbot.py:158` passes
`board_context(request.GET.get("topic", ""))`, which (**three queries**, `core/services/_ask.py:184`)
returns cards, topics, a published count and a waiting count.

What is true is that the board renders **only `APPROVED` cards** (`PublicQuestion.objects.published()`,
`core/models/_chat.py:366`), and the **only way to publish one is a Django-admin action**
(`core/admin.py:224 publish_cards`). So on a fresh instance — including the one at
`127.0.0.1:8002` — the board is an empty state by construction.

That makes this one of three different pieces of work, and they have different sizes:

| Reading | Evidence for | The work |
|---|---|---|
| **A. It is empty because nothing has been published** | `published()` filters `APPROVED`; `publish_cards` is the only writer | Nothing to wire — seed or publish real cards, and check the board reads well with 1, 5 and 24 of them |
| **B. There is no review surface the owner will use** | Admin-only publishing; the OPP's process is a *person* answering a question, and asking an administrator to work in Django admin is not that | A staff review surface (the escalation queue, `Refinement/ESCALATION_ANSWER_PATH_PRD.md`) — a much larger slice |
| **C. The empty state and the jump are weak** | The board sits below a long panel; `answer_page.html:51` links to `#questions` | Smaller: an anchor/teaser above the composer ("N answered questions →"), and a better zero state |

**The first task of the next session is to say which one it is — with the owner, at the instance** —
before any of them is built. Writing a PRD that assumes B would be inventing scope the request did
not ask for.

## 2. Requirement — clear conversation

**What it must do.** A visible control on `/ask/` that returns the panel to an empty conversation:
the thread shows nothing, the composer is ready, and the next question starts a new conversation.

**The one decision it forces (D72 candidate).** *Does "clear" delete the transcript, or only stop
showing it?*

- **Recommendation: stop showing it.** Drop the session key (and mark the session ended, if the model
  has such a state); **keep every `ChatMessage` row.** D59 decided to keep every transcript until the
  group sets a retention schedule, and P2.5a exists precisely so an answer's citations and grounding
  survive — a "clear" that deletes rows would destroy the evidence that decision ordered kept, from a
  public button, with no confirmation.
- **Rejected:** deleting the rows. It contradicts D59, it is an unauthenticated destructive write on a
  public form, and it removes the data `chat_review` and the escalation queue read.
- **Also rejected:** a per-message "delete this turn" control — same objection, and it would make the
  transcript a partial record that cannot be audited.

**Behaviour to settle in the plan.** Whether the control is a form POST (browser-safe, works without
JS) or an HTMX request; whether the old conversation stays reachable by URL (it has a `public_uuid`,
but no route serves it); and the copy — "Start a new conversation" reads better than "Clear" if the
transcript is kept, and is honest about what happens.

## 3. Requirement — the board, once §1.2 is settled

- [ ] If **A**: `uat_seed` (or a documented admin path) can produce board content for a demo, and the
      board is judged with **1, 5 and 24** cards plus zero — the empty state is a designed state
      (DESIGN §7.9), not a gap.
- [ ] If **C**: a visitor who lands to ask a question can see that answered questions exist **before**
      scrolling past the composer, without the composer being pushed below the fold.
- [ ] If **B**: stop and write the review-surface PRD first. It is `ESCALATION_ANSWER_PATH_PRD.md`'s
      subject, not this one's.

## 4. What must not change

- The composer stays the first thing on the page. The page is called *ask*; the library is the payoff,
  not the entry point (`_board.html` docstring, D62).
- No card is published by anything except a person. The consent checkbox writes an **unpublished**
  card; that line does not move.
- The panel is a product surface: `brand-*` tokens, Lora + Mulish, ≥44 px targets, works at 390 px, and
  the form posts without JavaScript (HTMX only swaps `#chat-thread`).
- No new query per request beyond the board's existing three.

## 5. Acceptance criteria

- [ ] The control is reachable by keyboard, ≥44 px, has an accessible name, and says what it does.
- [ ] Clicking it clears the visible thread; the next question works; no 500 and no 404 on reload.
- [ ] `ChatMessage` count is **unchanged** by a clear (asserted, not assumed) — the D59 line.
- [ ] A clear does not orphan the answer page: a card already published from that conversation still
      renders.
- [ ] The board's three readings are distinguished in the plan with the owner's answer recorded, and
      the chosen one is built.
- [ ] UAT: a human judges the empty state, the control's wording, and the phone layout — a UAT file in
      `tests/uat/`, signed before this is called done.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Building B (a review surface) because the board is empty | §1.2 says the board is wired; the session establishes the cause first |
| "Clear" quietly deleting evidence | The D59 assertion in §5 — a test, not a comment |
| A destructive-looking control next to a public form | Copy that says what is kept; confirm only if anything is destroyed (and nothing is) |
| The panel growing a fourth section and losing the composer above the fold | Judge at 390 px and 1280 px before and after |

---

## Pre-Flight Checklist

- [ ] No model change, no migration (unless "clear" needs a session state — prefer not to)
- [ ] View stays thin: the clear is one service call plus a redirect; no logic in the template
- [ ] Any new service function documents `In: / Out: / Side Effects: / Fails:`
- [ ] Tests in `core/tests/test_chat_surface.py` (or the existing `/ask/` module), including the
      "messages are kept" assertion
- [ ] No new query; `board_context`'s three stay three
- [ ] `DESIGN.md` followed; no new colour family
- [ ] UAT drafted **before** the build (shift-left), and signed before Done
