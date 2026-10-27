"""Words the corpus answers under another name — reviewed aliases, not a classifier.

A visitor asks about "cost"; the OPP's section is called **Membership Fees**. Nothing in
the question's vocabulary occurs in that paragraph, so no amount of ranking finds it —
the gap is lexical, and the only honest fix is to say which question word the document
calls something else.

Why a table and not a model call: `CHAT_ANSWER_COVERAGE_PRD.md` G5 keeps a classifier out
on evidence — it would not have fixed any measured failure, and a wrong label hides the
right passage. A reviewed row cannot hide anything: it is a list of words, it is printable,
and each entry names the question and the measurement that put it there.

Why the search is one word, not the alias set OR-ed: measured on 2026-10-27 against the
shipped corpus —

    search("fee")           -> §2.3, §2.1, §2.2, §2.4, §2.5, r500     (§2.1 at rank 2)
    search("cost OR fee")   -> §2.3, §2.4, pgs-sa, §2.2, §2.5, r500    (§2.1 absent)

which is the same lesson `search_terms` learned about the question's own words: a common
word in an OR outranks the rare one that carries the question. The alias arm therefore
searches the rarest alias alone, exactly as the primary arm searches the rarest subject
word.

Adding an entry costs one FTS query per question that uses it, so an entry needs a
measurement: the question, the clause it missed, and the rank the alias puts it at.
"""

from __future__ import annotations

#: `question word -> the words the corpus uses for it`. Lowercase, already tokenised the
#: way `significant_terms` produces them (alphanumeric only, no punctuation).
ALIASES: dict[str, tuple[str, ...]] = {
    # G3, 2026-10-27. "What is the yearly cost to get certified, including the farm
    # visit?" was answered from §2.2, §2.3, §2.4 and §2.5 and never mentioned §2.1's
    # annual membership fee. `cost` (df 7) appears in the OPP seven times; the word it
    # wants is `fee` (df 13), and searching it alone puts §2.1 at rank 2. The earlier
    # diagnosis of this gap — "no sibling-section expansion" — was wrong twice over: the
    # question's lexical key was `get` at the time (df 1), and §2.1 shares no word with
    # the question at all (`CHAT_TRUTHFULNESS_PRD.md` §3 F1).
    "cost": ("fee",),
    "costs": ("fee",),
}
