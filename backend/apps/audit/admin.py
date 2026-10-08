"""Read-only admin configuration for AuditLog."""

from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Immutable, read-only admin for AuditLog."""

    list_display = ("timestamp", "action", "actor", "target_user", "ip_address")
    list_filter = ("action", "timestamp")
    search_fields = ("actor__email", "target_user__email", "ip_address", "action")
    readonly_fields = (
        "id",
        "action",
        "actor",
        "target_user",
        "ip_address",
        "user_agent",
        "metadata",
        "timestamp",
    )
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
