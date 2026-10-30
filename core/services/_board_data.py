"""The public board's published set — GENERATED, do not edit by hand.

Written by `scripts/board.py` from the `**Public:** yes` PRDs under
`product/backlog/`. Regenerate before a push that will be deployed:

    python scripts/board.py

`scripts/board.py --check` (and `deploy/deploy.sh`, before it backs anything up)
fails when this file disagrees with the tree, so a stale board aborts the deploy
instead of shipping. Remove a card by deleting its `**Public:** yes` line and
regenerating — never by editing this file.

The shape and the column titles are `core/services/_board.py`'s; this module is data.
"""

from __future__ import annotations

SOURCE_DIGEST = 'sha256:c8466b739245c2962b80917b3bcb7b914f96d5964489480fc66ae61d2f9219c9'

COLUMN_ORDER: tuple[str, ...] = ('refinement', 'ready', 'in_progress', 'done')

#: (title, summary, column, updated) — one sentence per card, no paths, no statuses,
#: no owners. `updated` orders the Shipped column and is never rendered.
CURATED: tuple[dict[str, str], ...] = (
    {
        'title': 'A question we cannot answer reaches a person',
        'summary': 'When the assistant cannot answer from the documents, its refusal should reach a person who can answer, instead of ending at a message.',
        'column': 'refinement',
        'updated': '2026-10-21',
    },
    {
        'title': 'Readable tables in the certification landscape',
        'summary': 'Five table pages in the certification landscape document become readable rows, instead of text flattened into a paragraph.',
        'column': 'refinement',
        'updated': '2026-10-29',
    },
    {
        'title': 'Applying for assessment, online',
        'summary': 'Applying for assessment becomes an online form — membership, pledge, turnover and the pre-visit questionnaire — instead of paper sent to the team.',
        'column': 'ready',
        'updated': '2026-10-20',
    },
    {
        'title': 'Every document can be opened and read',
        'summary': 'Every document on the Documents page opens to be read on screen, not only to be downloaded.',
        'column': 'done',
        'updated': '2026-10-28',
    },
    {
        'title': 'Reading the standard on this site',
        'summary': 'The standard and our procedures can now be read as text on this site, and every citation in an answer opens the exact line it quotes.',
        'column': 'done',
        'updated': '2026-10-27',
    },
    {
        'title': 'Lists in the standard read as lists',
        'summary': 'Lists inside the standard now read as lists: lettered conditions and definitions no longer run together as one block of text.',
        'column': 'done',
        'updated': '2026-10-27',
    },
)
