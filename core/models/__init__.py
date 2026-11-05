"""Domain models, sliced vertically.

Every model is re-exported here so callers write `from core.models import Farm`
and never reach into a private module (`core.models._core`). Django discovers
models by importing this package, so a model that is not re-exported here does
not exist as far as the ORM is concerned.

Slices (see MVP0_PLAN_V2.md §2):
    _core.py           User, UserRole, Role, Language
    _membership.py     Member, Farm, FarmAlias, FarmCategory, FarmContact,
                       CommitteePosition, CommitteeTerm, MembershipFee
    _certification.py  Seal, Category (Certificate and Assessment* arrive in MVP 1/2)
    _public.py         PublicDocument (the files the group publishes, D22)
    _chat.py           ChatSession, ChatMessage, EscalatedQuery, PublicQuestion

Keep each slice under the 30 KB cap (build_principles.md). When a slice
approaches it, cut a new slice along a domain seam — do not grow the file.
"""

from core.models._certification import Category, Seal
from core.models._chat import (
    REFUSAL_NOTES,
    ChatMessage,
    ChatSession,
    EscalatedQuery,
    EscalationReason,
    PublicQuestion,
)
from core.models._core import (
    ASSESSOR_CAPABILITY,
    Language,
    Role,
    User,
    UserRole,
)
from core.models._membership import (
    CommitteePosition,
    CommitteeTerm,
    Farm,
    FarmAlias,
    FarmCategory,
    FarmContact,
    Member,
    MembershipFee,
)
from core.models._public import PublicDocument

__all__ = [
    "ASSESSOR_CAPABILITY",
    "Category",
    "ChatMessage",
    "ChatSession",
    "CommitteePosition",
    "CommitteeTerm",
    "EscalatedQuery",
    "EscalationReason",
    "Farm",
    "FarmAlias",
    "FarmCategory",
    "FarmContact",
    "Language",
    "Member",
    "MembershipFee",
    "PublicDocument",
    "PublicQuestion",
    "REFUSAL_NOTES",
    "Role",
    "Seal",
    "User",
    "UserRole",
]
