"""Business logic. The single owner of each rule.

Views call services; services call models. Nothing calls back up into views.
Every external call takes an explicit `timeout=` and every exception path
reports to Sentry — never `except: pass` (HANDOVER §6.5).

Slices:
    _seed.py     seed_deployment — data, not migrations (A4)
    _health.py   health check aggregation (A5)
    _chatbot.py  grounded answering + refusal (D)
"""
