---
name: pgs-writing-explorations
description: Use when a decision needs to be explored or explained in a shareable HTML page — comparing options, showing evidence for and against, or diagramming a flow — before a spec section or plan is written. Produces a self-contained decision artifact in product/design/.
---

# Writing Exploration Artifacts

## Overview

An **exploration artifact** is a self-contained HTML page whose job is to get **one decision
made** by a specific person. It is not a proposal deck, a status report, or a design mockup. It
is the written form of an argument: here is the question, here is what is actually true, here
are the options, here is the evidence, here is what the literature says (including where it
disagrees), here is my recommendation, here is what would change my mind.

The output is a page a stakeholder can read alone, at their pace, and act on.

**This is not `designing-in-html`.** That skill prototypes production UI with CDNs and the
Modern Pastoralist tokens. This skill produces *decision documents* — no CDN, no build step, no
Tailwind, and it never becomes a production template.

## When to use

- A decision is close enough that it needs evidence laid out, not a recommendation in chat.
- The options have different failure modes and someone will ask "why not the other one?"
- Diagrams would replace several paragraphs (a pipeline, a sequence, a dependency graph).
- The user says "explore", "lay it out", "explain the trade-offs", "show me the options".
- A spec §18 decision needs a rationale a future reader can audit.

**Do not use it for:**

- A decision that is genuinely obvious — write the spec line and move on. A page implies
  contestability; making one for a settled question wastes the reader's trust.
- Production UI prototypes → `designing-in-html`.
- Handover or status → a markdown file.
- Anything already decided where the page would only rationalise it. If the analysis cannot
  change the answer, it is not an exploration.

## Hard rules

1. **Self-contained.** One file. No CDN, no build step, no external fonts, no network. It must
   open from the filesystem on a laptop in a room with no wifi — which is exactly where these
   get read.
2. **Lives in `product/design/`.** Never in the backlog; these are not backlog items. Name it
   `<decision-id>_<slug>.html`, e.g. `d1_mvp1_shape_exploration.html`.
3. **Use the PGS palette.** Copy the `:root` tokens from an existing artifact
   (`decisions_review.html`, `mvp0_scope_and_open_questions.html`). Do not invent a new visual
   language — the third page in a different style reads as a different project.
4. **Record the decision in the page.** Radio options, a notes box, `localStorage` autosave, and
   an **export** that produces a markdown row usable in `PGS_PLATFORM_SPEC.md` §18.3. A page that
   produces no artefact leaves the decision in chat, which is where decisions go to die.
5. **Print clean.** `@media print`: hide the sticky bar and dialogs, remove shadows, avoid
   breaking cards. Reviewers print these.
6. **State the decision at the top.** The question, in the hero, in one sentence, before any
   context.

## Required structure

Order matters; each section answers the question the previous one provokes.

| Section | Answers | Failure if skipped |
|---|---|---|
| **Hero + the question** | What are we deciding? | Reader doesn't know what they're reading for |
| **How to read this** | What kind of document is this? | Treated as a proposal, argued with on the wrong axis |
| **Part 1 — What is actually true** | Inventory, enumerated from source | The options are evaluated against assumptions |
| **Part 2 — The shape of the problem** | Why it's hard; the asymmetry that drives it | Reader can't weigh the criteria |
| **Part 3 — The options** | Two to four, each with a diagram | Only the author's favourite is really considered |
| **Part 4 — Evidence for and against** | Strongest case for each, then its weaknesses | One-sided; reader spots it and distrusts the page |
| **Part 5 — What the literature says** | Principles, and where they disagree | Rationalising instead of analysing |
| **Part 6 — Comparison** | Unweighted matrix with reasons | Precision theatre |
| **Part 7 — Recommendation** | One answer, what it changes, what would change it | A menu with no decision |
| **Part 8 — Your decision** | Control + export | Decision never lands anywhere |

## Evidence discipline

The most valuable part of an artifact is the part that was **checked**. Apply these:

- **Distinguish verified from inferred, visibly.** Quote the actual file, the actual text, the
  actual command output. If a claim came from reading a document rather than running something,
  say so.
- **Run the thing before recommending it.** In this repo that has repeatedly meant extracting
  text from `pgs_docs/*.pdf` and grepping it. A plausible-sounding assumption about source
  format is the single most common way these documents mislead. A 10-line script beats a
  paragraph of confidence.
- **Name the assumption** whenever an argument only works because of one. ("This argument
  survives only if the contract cannot be discovered early.")
- **Count, don't characterise.** "16 tables, 4 flows, 3 endpoints" persuades; "substantial
  server-side work" does not.
- **Cite locatably** — `spec §4.5`, `MVP0_PLAN_V2.md` Task B2, `OPP §V`, a `file:line`.

## Diagrams

Pick by question, not by preference:

| Question | Diagram |
|---|---|
| What is in this slice, in what order? Which parts are online? | Horizontal pipeline of steps, colour-coded by tier |
| Where are the module boundaries? What crosses them? | Two/three-column band with the contract in the middle |
| What is the interaction protocol? What is idempotent? | Sequence diagram (lifelines + ordered arrows) |
| What does the build order depend on? | Dependency graph or ordered pipeline |
| Under which conditions does the answer change? | Decision table (condition → consequence) |

Rules:

- **Label every edge.** An unlabelled arrow is decoration. If you cannot label it, it does not
  belong in the diagram.
- **Map colour to a legend, and never to colour alone.** Use position and labels too — printed
  greyscale and colour-blind readers both need the annotation.
- **Wrap on mobile.** Flex with `flex-wrap` for pipelines; `viewBox` + `width="100%"` for SVG.
- **ASCII-hyphen arrows (`->`), never Unicode arrows** inside code blocks; they survive every
  font and every diff.
- A sequence diagram earns its place when the *ordering* is a correctness property. If the order
  does not matter, a list is better.

## Anti-patterns

| Anti-pattern | Why it's wrong | Do instead |
|---|---|---|
| **Fake precision** — weighted scores from invented numbers | Manufactures authority | Unweighted matrix; state the criteria; let the reader weigh |
| **Straw-man alternatives** | Reader recognises it and discounts the whole page | Give every option its strongest case |
| **Philosophy as decoration** — naming Cockburn or Parnas without mapping to the decision | Signals erudition, persuades nobody | One row per principle: what it says → which option → whether it actually holds *here* |
| **Cherry-picked principles** | All arrows pointing one way is a tell | Show the ones that disagree, and say how you break the tie |
| **No recommendation** | Deciding is the deliverable | Recommend, then state what would change your mind |
| **Wall of prose in place of a diagram** | Unread | Diagram + three sentences |
| **A page for a settled question** | Cheapest way to lose the reader | Ask whether the analysis could change the answer first |

## Verification before you call it done

- [ ] Opens with no network; no external requests in the markup (`grep -c "https://"` = 0)
- [ ] HTML is well-formed (unbalanced-tag parse passes)
- [ ] Reads top-to-bottom in under 15 minutes
- [ ] Every claim that could be checked has been, and is quoted
- [ ] Every option has a real "against" list
- [ ] The recommendation is unambiguous, and "what would change my mind" is present
- [ ] Diagrams have labelled edges and a legend
- [ ] Decision control autosaves; export produces a §18.3-compatible row
- [ ] Print preview does not cut a card in half or print the sticky bar
- [ ] Mobile width (390 px) does not produce horizontal scroll

## Closing the loop

A completed artifact is not the end of the work:

1. Export the decision and paste it into `PGS_PLATFORM_SPEC.md` §18.3 as the next `D<n>`.
2. Apply any consequent edits to the spec, PRD or plan **in the same session** — a decision
   recorded but not applied is drift waiting to happen.
3. If the decision moves scope, update the PRD's §9 (open questions) so the list stays true.
4. Commit the artifact with the decision, and say in the message which `D` it produced.
5. Regenerate the backlog index if a file moved: `python product/backlog.py --write`.

## Worked examples

| Artifact | Decision it served | Why it's a good reference |
|---|---|---|
| `product/design/d1_mvp1_shape_exploration.html` | Is MVP 1 one slice or two? | Full structure; pipeline + seam + sequence diagrams; a literature table that disagrees with itself; spike-as-precondition insight |
| `product/design/mvp0_scope_and_open_questions.html` | Eleven MVP 0 decisions at once | Bulk-decision variant: fix cards (not choices) separated from question cards |
| `product/design/decisions_review.html` | Override review | Simplest form: one card per decision, recommendation + notes |
