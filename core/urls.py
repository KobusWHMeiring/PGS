"""`core` URLconf.

Routed from `pgs/urls.py` under no prefix, so paths here are the public paths.
App boundaries are not URL boundaries (`build_principles.md` §I) — the public site,
the portal, the PWA and the JSON API are separate prefixes in the root URLconf
regardless of how many Django apps exist.

The public paths are not free choices: they are the redirect map in
`product/design/content_inventory.md` §4, which retires the WordPress URLs
`/organics/`, `/about-2/` → `/how-it-works/`, `/members-2/` `/farmer-members/`
`/consumers/` → `/members/`, `/become-a-member/` and `/contact/`. Keeping the path
shape now is what makes the MVP 2 cutover a redirect table rather than a rewrite.
"""

from django.urls import path

from core.views._documents import document_file, document_reader, documents
from core.views._health import health
from core.views._uat import console as uat_console, run as uat_run
from core.views._public import (
    become_a_member,
    building,
    contact,
    home,
    how_it_works,
    members,
    organics,
)
from core.views._chatbot import ask, ask_answer

app_name = "core"

urlpatterns = [
    # `/health/` is deliberately unversioned and unprefixed: the load balancer and
    # the uptime monitor are configured with this exact path (§VII.1).
    path("health/", health, name="health"),
    path("", home, name="home"),
    path("organics/", organics, name="organics"),
    path("how-it-works/", how_it_works, name="how_it_works"),
    path("members/", members, name="members"),
    # `/documents/` is the index; `/documents/<code>/` is one file. The code, never a
    # media path: `content_inventory.md` §4 makes the WordPress cutover a redirect
    # table, and D22's dossiers must be unreachable by construction (they are not rows).
    path("documents/", documents, name="documents"),
    path("documents/<str:code>/", document_file, name="document_file"),
    # The reader: the text we ingested, at the code a citation names. Deliberately not a PDF
    # fragment — `document_file` streams with `as_attachment=True`, so a `#page=` fragment has
    # no viewer to land in — and deliberately not under `/media/` (§VI).
    path("documents/<str:code>/read/", document_reader, name="document_reader"),
    path("become-a-member/", become_a_member, name="become_a_member"),
    # The grounded assistant. `/ask/` is the real surface; the home page's showcase
    # is an illustration of it, not a second implementation.
    path("ask/", ask, name="ask"),
    # One question, one URL (D62/C). After `/ask/` so the composer is never shadowed, and a
    # `<slug:…>` converter never matches the empty string.
    path("ask/<slug:slug>/", ask_answer, name="ask_answer"),
    # The roadmap (D74). Public, but generated and curated: a card exists only where a PRD
    # carries `**Public:** yes`, and the artefact is refreshed before a deploy rather than
    # read from the backlog directory at request time.
    path("building/", building, name="building"),
    path("contact/", contact, name="contact"),
    # The UAT console: staff-only, and deliberately **not** in `_public.PAGES`, so the
    # public sweeps (claim discipline, the Playwright route list) do not treat it as a
    # page the group publishes. It exists because a `file://` artefact cannot run
    # `manage.py`, and the setup commands should be buttons rather than homework.
    path("uat/", uat_console, name="uat_console"),
    path("uat/run/<str:action>/", uat_run, name="uat_run"),
]
