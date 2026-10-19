"""HTTP layer: thin views only.

A view parses the request, calls exactly one service, and renders. No business
logic, no ORM queries beyond the service's return value
(build_principles.md — thin views, service ownership).

Slices:
    _public.py     home, about, members, contact
    _documents.py  /documents/ and deep-links (D22)
    _chatbot.py    chatbot surface + SSE/HTMX endpoints
    _health.py     /health/ (A5)
"""
