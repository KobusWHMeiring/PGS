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

from core.views._documents import document_file, documents
from core.views._health import health
from core.views._public import (
    become_a_member,
    contact,
    home,
    how_it_works,
    members,
    organics,
)

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
    path("become-a-member/", become_a_member, name="become_a_member"),
    path("contact/", contact, name="contact"),
]
