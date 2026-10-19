"""`core` URLconf.

Routed from `pgs/urls.py` under no prefix, so paths here are the public paths.
App boundaries are not URL boundaries (`build_principles.md` §I) — the public site,
the portal, the PWA and the JSON API are separate prefixes in the root URLconf
regardless of how many Django apps exist.
"""

from django.urls import path

from core.views._health import health

app_name = "core"

urlpatterns = [
    # `/health/` is deliberately unversioned and unprefixed: the load balancer and
    # the uptime monitor are configured with this exact path (§VII.1).
    path("health/", health, name="health"),
]
