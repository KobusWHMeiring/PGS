"""`/health/` — the load balancer's only question (build_principles.md §VII.1).

Thin view (§II): call one service, serialise its report. No queries, no logic.

The status code is the answer: 200 when every dependency is up, 503 when any is not.
The body is deliberately terse — check names and `ok`/`error` only, never exception
text or configuration — because this endpoint is unauthenticated by necessity: a
load balancer has no session, so anything served here is served to the internet.
"""

from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from core.services._health import check_health


@never_cache
def health(request):
    report = check_health()
    return JsonResponse(
        {"status": report.status, "checks": report.checks},
        status=200 if report.is_ok else 503,
    )
