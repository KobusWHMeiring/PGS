"""Admin for identity.

A custom user model needs its own `UserAdmin` registration. Without it Django
registers nothing and the account is unreachable from `/admin/` — and, worse, the
default `UserAdmin` field lists refer to fields this model does not have.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from core.models import User, UserRole


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
