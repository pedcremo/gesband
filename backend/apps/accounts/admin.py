from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AccessInvitation, Account

admin.site.register(Account, UserAdmin)


@admin.register(AccessInvitation)
class AccessInvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "association", "member", "created_at", "expires_at", "sent_at", "accepted_at", "revoked_at")
    list_filter = ("association", "accepted_at", "revoked_at")
    search_fields = ("email", "member__first_name", "member__last_name")
    readonly_fields = (
        "association",
        "member",
        "email",
        "token_digest",
        "created_by",
        "revoked_by",
        "created_at",
        "expires_at",
        "sent_at",
        "accepted_at",
        "revoked_at",
        "last_send_error",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
