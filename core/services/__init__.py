"""Business logic. The single owner of each rule.

Views call services; services call models. Nothing calls back up into views.
Every external call takes an explicit `timeout=` and every exception path
reports to Sentry — never `except: pass` (HANDOVER §6.5).

Slices:
    _seed.py     seed_deployment — data, not migrations (A4)
    _health.py   health check aggregation (A5)
    _public.py   public-site content: page metadata, nav, the OPP fee schedule (C1)
    _chatbot.py  grounded answering + refusal (D) -- the contract: answer, cache, refusals
    _chat_prompt.py  the prompt text, PROMPT_VERSION and `build_prompt`
    _chat_audit.py   the citation audit and its advisory warnings
    _chat_text.py    tokens, locators and digests shared by all of the above
    _chat_values.py  what the chatbot returns, raises, and needs from a provider

The model provider still lives in `_chatbot.py`; it leaves next
(`product/backlog/ready/CONTEXT_CUTS_PRD.md`).
"""
