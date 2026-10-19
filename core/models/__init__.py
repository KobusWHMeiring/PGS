"""Domain models, sliced vertically.

Every model is re-exported here so callers write `from core.models import Farm`
and never reach into a private module (`core.models._core`). Django discovers
models by importing this package, so a model that is not re-exported here does
not exist as far as the ORM is concerned.

Slices (see MVP0_PLAN_V2.md §2):
    _core.py           User, UserRole, Role, Category, Member, Farm, ...
    _certification.py  Seal, Assessment*, Certificate (MVP 1/2 forward)
    _chat.py           ChatSession, ChatMessage, ChatCitation

Keep each slice under the 30 KB cap (build_principles.md). When a slice
approaches it, cut a new slice along a domain seam — do not grow the file.
"""
