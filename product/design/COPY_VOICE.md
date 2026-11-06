# Copy voice — how to rewrite the Outeniqua PGS public site

**Paste this above `COPY_DECK.md` when you hand the deck to a writing pass.** It is written
for a writer or a model with no other context on this project: everything needed to rewrite
without damaging the site is in the two files.

The deck is 458 strings, about 4,200 words, in reading order. That is eight pages of prose.

---

## 1. The one rule that outranks every other rule

**Rewrite. Never add a fact.**

No new anecdotes. No new colour about land, soil, weather, family or heritage. No new
adjective describing a farm's produce. No "since 1998", no "hand-picked", no "our farmers
believe". A writing model's instinct is to add warmth, and on this site warmth is a legal
claim.

This is not a style preference. The public surface reproduces **only** the four FORM
outcomes and the **active** seals. These are producer statements, never PGS endorsements, and
they are forbidden:

> `pasture raised` · `GMO free` · `biodynamic` · `chemical-free` · `spray-free`

You may not introduce them, and you may not introduce anything that implies them. "Grown
without synthetic inputs", "untouched land", "pure" all fail the same test. The live
WordPress site publishes two of these phrases today; do not copy that site's enthusiasm,
only its concreteness.

Two more facts that may not be softened:

- **Membership is not certification.** Never write a sentence in which membership implies a
  certified status.
- **Every `OPP §x` citation chip is a promise.** If a card says "OPP §3.3", the sentence above
  it must still be true of §3.3 after you rewrite it. If you cannot check the section, leave
  that string alone and say so.

## 2. What you are allowed to do to a sentence

Rewrite it, merge it with its neighbour, or cut it. Cutting is encouraged.

A rewrite that must keep every string the same length **cannot fix the thing that is wrong
here.** The copy is uniform: nearly every card body is two or three sentences of about forty
words. Real writing is lumpy, and the lumpiness is part of sounding like a person. So:

- Some strings should come back **much shorter** than they went in.
- Two adjacent strings may be merged into one, leaving the other blank and marked as covered
  in a comment line.
- A string whose only job is an aphorism ("This is the part of a PGS that never appears on a
  certificate.") can be deleted. Write `new: -` and it will be reported, not deleted.

## 3. Who is reading

Three readers, in this order:

1. **A farmer deciding whether to join.** They want to know what happens, what it costs, how
   long it takes, and who will be on their farm. They will leave if the first screen sounds
   like a brochure.
2. **A market or retailer checking a claim.** They are looking for what the group can and
   cannot say. Vagueness alarms them.
3. **A farmer committee at PGS South Africa or SAOSO deciding whether to recognise the
   group.** They are reading for whether this group takes its own procedures seriously. Over-
   polished marketing language reads as a group that has something to hide.

None of them is impressed by adjectives. All of them are persuaded by a specific number, a
named step, or a plain statement of what will happen next.

## 4. The voice

Plain, declarative, first-person where the group speaks for itself. Short sentences. Concrete
nouns. British/ZAf spelling (`recognised`, `summarise`, `organise`, `programme`).

The best sentence already on the site is the live site's own, inventoried in
`product/design/content_inventory.md`:

> Any farmer growing food organically along the Outeniqua mountain range (roughly from Mossel
> Bay to the Crags) is welcome.

That is the register: a place you can find on a map, a plain condition, an open door. Note
there is no adjective about quality anywhere in it.

For sourcing the *content* of a sentence — never the style — the governing documents are
`pgs_docs/Outeniqua pgs principles, policies and procedures 2026.pdf` (the OPP) and
`pgs_docs/saoso-version-2.1-2026.pdf`. If you have them, use them to check that what you
write is true. If you do not, keep the fact and change only the shape.

**For the words a PGS body actually uses, there is `REFERENCE_COPY_CORPUS.md`** next to this
file: ~14,000 words pulled from the SAOSO, PGS South Africa, Western Cape Farmers' PGS and
IFOAM sites, with a URL and fetch date on every page. **Search it, do not read it.** `rg -n
"farm visit|the committee|outcome|pledge" REFERENCE_COPY_CORPUS.md` and read a few lines
around the hit. Two warnings that file also carries: those bodies use `certified` freely and
this group may not (membership is not certification, and no farm status is published), and
being as polished as an umbrella body's marketing page is not the bar — being plainer than it
is.

**Worked examples**, using only facts already on the page. The first two are *now live on the
home page* (round 1, 2026-11-05) - they are precedent, not suggestion. The third is proposed
and not yet applied.

*Cutting a tricolon, an em dash and a "not X"*

> old: We are a locally focused quality assurance group. Members assess one another against
> the SAOSO organic standard, on each other's farms, in the open - built on trust, social
> networks and knowledge exchange, not a distant inspector.
>
> **now:** We are a locally focused quality assurance group. Members assess one another's
> farms against the SAOSO organic standard, and the person whose farm is being visited sees
> who is coming.

*Killing an aphorism, giving the list a subject*

> old: Quarterly meetings, seed exchange and production problems solved by the people who
> have already met them. Members attend at least two other farm visits a year. This is the
> part of a PGS that never appears on a certificate.
>
> **now:** Members meet quarterly, exchange seed and bring production problems to people who
> have already met them. Everyone attends at least two other farm visits a year.

*Turning a topic announcement into a statement* - proposed, not yet applied

> old: Organic agriculture, and what a PGS adds
>
> new: What organic means here

## 5. The tells to remove
Measured on this tree, 2026-11-05. These are the specific things that make copy read as
machine-written, in order of how loudly they shout.

| Tell | Present | What to do |
|---|---|---|
| Em dash as a pause | **140** across the site | At most one per page, and only where a full stop would misrepresent the sentence. Prefer the full stop. |
| Uniform card rhythm | every `.element-card__body` | 35–45 words each, same shape. Vary: some 12 words, some 50. |
| Negate-then-assert | "Not a hired inspector, and…", "not a distant inspector", "This is the part of a PGS that never appears on a certificate" | Say the true thing directly. One such move per page is a voice; four is a template. |
| Topic-announcing headings | ", and what a PGS adds", "Guided by six basic elements", "Knowledge that moves between farms" | State something instead. Concrete subject, concrete verb. |
| Tricolons | "trust, social networks and knowledge exchange" | Two items or four. Three is the rhythm a model falls into — though a person writes it too; the budget is what matters, not the ban. |
| Abstract noun as subject | "Knowledge that moves between farms" | Put a person in the subject position: "Farmers phone each other about pests." |
| "we" versus "the group" | 23 vs 50 uses | Use "the group" when stating procedure (it is what a committee looks for). Use "we" only where the group is inviting someone in. Do not mix them inside one page. |

## 6. Field rules for the `Page metadata` section

Those rows are not prose in a paragraph; they land in fixed places and have length limits.
Breaking one breaks the layout.

| Field | Where it lands | Rule |
|---|---|---|
| `title` | `<title>` | ≤ 60 characters, keep the "— Outeniqua PGS" suffix |
| `description` | meta description | ≤ 160 characters, one sentence, no claim |
| `eyebrow` | small pill above the `h1` | ≤ 5 words, Title Case |
| `heading` + `heading_accent` | the `h1`, split over two lines, second line italic ochre | Keep both non-empty. The accent must be short — ≤ 6 words, and it must read as a continuation, not a fragment. |
| `lede` | paragraph under the `h1` | One or two sentences. This is the string most likely to sound like a brochure; treat it as the one that has to earn the scroll. |

## 7. How to hand it back

- Fill in **only** the `new:` blocks. Leave `old:` exactly as it is — it is the check that the
  deck still matches the file.
- Leave `new:` blank to keep the current string.
- Write `new: -` to mark a string for cutting.
- Rows marked `mode: locked` are citations, labels and fee figures. Do not rewrite them.
- Rows marked `mode: manual` carry inline markup or a `{{ }}` expression; `new:` will be
  ignored for those, so leave them out and list them in your reply if they need changing.
- One row per string. Do not reorder, rename or delete rows.

## 8. Before you return it

Read the deck top to bottom as a reader would, then check:

1. Have you introduced any fact that was not in the `old:` text? Search your output for a
   number, a date, a place name or a proper noun that was not already there. Remove it.
2. Does any sentence now imply a certification, or use one of the five forbidden phrases?
3. Is there more than one em dash on any page?
4. Are the card bodies still all about the same length? If so, you have not changed the
   rhythm — go back and cut harder.
5. Does the `lede` on every page make a claim you could not defend to the farmer whose farm
   it is about?

## 9. What happens after you return it

`python scripts/copy_deck.py --apply --dry-run` shows every change as a diff and refuses any
row whose `old:` no longer matches the tree. `--apply` then writes them, and re-extracts each
file to prove that no string other than the ones you edited changed. Then
`scripts/fast.sh --critical` runs the claim-discipline and architecture guards, and a human
reads the site aloud.

Nothing you write is final until a person has read it out loud. A sentence that survives
being spoken across a table is the only test that matters here.
