"""Admin for identity.

A custom user model needs its own `UserAdmin` registration. Without it Django
registers nothing and the account is unreachable from `/admin/` — and, worse, the
default `UserAdmin` field lists refer to fields this model does not have.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from core.services._ask import approve, reject

from core.models import (
    Category,
    ChatMessage,
    ChatSession,
    EscalatedQuery,
    PublicQuestion,
    Seal,
    User,
    UserRole,
)


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 0
    # Roles are granted deliberately; they are not a free-text field.


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "preferred_language", "is_staff", "role_list")
    list_filter = ("preferred_language", "is_staff", "is_superuser", "roles__role")
    inlines = [UserRoleInline]

    # `fieldsets` must be extended, not replaced: the base sets are the password
    # and permission sections, and losing them makes the admin unable to set one.
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "PGS",
            {
                "fields": (
                    "phone",
                    "preferred_language",
                    "email_verified_at",
                    "popia_consent_at",
                    "graduated_from_public_at",
                )
            },
        ),
    )

    @admin.display(description="roles")
    def role_list(self, obj: User) -> str:
        return ", ".join(obj.roles.values_list("role", flat=True)) or "—"


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")


# `Role` is a TextChoices enum, not a model: the seven roles are code, not data
# (build_principles §I), so there is no table to register. The `role` choice on
# `UserRole` is the only editable surface, and it is constrained by the enum.


# --- Certification data -----------------------------------------------------
#
# `Seal` and `Category` are editable because they are **data** (§4.8): a group
# retargeting to another standard, or publishing a category FORM has finished
# developing, must be able to do it without a release. The one thing the admin must
# not make easy is issuing the deferred pasture-raised seal — `is_active` is
# therefore shown as a labelled column rather than being silently editable
# everywhere, and the note explains the decision to whoever opens the row.


@admin.register(Seal)
class SealAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "standard_ref", "is_active", "criteria_defined")
    list_filter = ("is_active", "criteria_defined")
    search_fields = ("code", "label")
    readonly_fields = ("display_note",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "display_order", "is_active", "standard_ref")
    list_filter = ("is_active",)
    search_fields = ("code", "label")
    ordering = ("display_order", "code")


# --- Chat (sub-plan D) ------------------------------------------------------
#
# History is evidence: a refusal is the product's central claim, and an administrator
# reviewing one needs to see what was asked and what the model was given. The message
# rows are therefore read-only. `EscalatedQuery` is the one mutable chat record: it is
# the gap in the corpus, and answering it is the administrator's job.


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("public_uuid", "user", "standard_set", "message_count", "created_at")
    list_filter = ("standard_set",)
    search_fields = ("public_uuid", "user__username", "user__email")
    readonly_fields = ("public_uuid", "created_at", "ip_hash", "user_agent")
    date_hierarchy = "created_at"

    @admin.display(description="messages")
    def message_count(self, obj: ChatSession) -> int:
        return obj.messages.count()


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "short_content", "model", "latency_ms")
    list_filter = ("role", "model")
    search_fields = ("content", "session__public_uuid")
    readonly_fields = (
        "session",
        "role",
        "content",
        "created_at",
        "latency_ms",
        "model",
        "prompt_tokens",
        "completion_tokens",
        "retrieved_chunks",
    )

    @admin.display(description="content")
    def short_content(self, obj: ChatMessage) -> str:
        return obj.content[:80]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.register(EscalatedQuery)
class EscalatedQueryAdmin(admin.ModelAdmin):
    list_display = ("id", "reason", "status", "short_question", "created_at", "answered_at")
    list_filter = ("reason", "status")
    search_fields = ("question", "answer")
    readonly_fields = ("message", "question", "reason", "created_at")
    date_hierarchy = "created_at"

    @admin.display(description="question")
    def short_question(self, obj: EscalatedQuery) -> str:
        return obj.question[:80]

    def save_model(self, request, obj, form, change):
        """Answering is an act with a timestamp and a name, not a free-text edit."""
        if (obj.answer or "").strip() and obj.answered_at is None:
            obj.answered_at = timezone.now()
            if obj.answered_by_id is None:
                obj.answered_by = request.user
            obj.status = EscalatedQuery.Status.ANSWERED
        super().save_model(request, obj, form, change)


# --- The ask board (D62, D64–D66) -------------------------------------------
#
# This is the only place a card is published. Two things the form must make possible, because
# the consent label promises them: **editing the question before approval** (that is where a
# third party's name comes out) and **writing what the answer does not cover** (the page
# requires it). The two actions are the reviewer's normal path; the change form is the
# deliberate one.


@admin.register(PublicQuestion)
class PublicQuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "status", "topic", "ask_count", "checked_at", "approved_at")
    list_filter = ("status", "topic")
    search_fields = ("question", "answer")
    readonly_fields = (
        "asked_key",
        "ask_count",
        "first_asked_at",
        "last_asked_at",
        "approved_by",
        "approved_at",
    )
    date_hierarchy = "last_asked_at"
    actions = ("publish_cards", "reject_cards")

    fieldsets = (
        (
            "The published question",
            {
                "fields": ("question", "topic", "status"),
                "description": (
                    "Edit the wording before publishing. A question is free text from a public "
                    "form: remove anyone else's name or farm here, not after it is live."
                ),
            },
        ),
        ("The answer", {"fields": ("answer", "covers", "citations")}),
        (
            "Review",
            {
                "fields": (
                    "checked_at",
                    "approved_by",
                    "approved_at",
                    "ask_count",
                    "first_asked_at",
                    "last_asked_at",
                    "escalated_query",
                    "asked_key",
                )
            },
        ),
    )

    @admin.action(description="Publish the selected questions")
    def publish_cards(self, request, queryset):
        for card in queryset:
            approve(card.pk, user=request.user)

    @admin.action(description="Do not publish the selected questions")
    def reject_cards(self, request, queryset):
        for card in queryset:
            reject(card.pk, user=request.user)
