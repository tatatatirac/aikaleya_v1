from django.contrib import admin

from audit_log.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "business_client", "actor", "action", "object_type", "object_id", "channel")
    list_filter = ("business_client", "action", "channel", "created_at")
    search_fields = ("action", "object_type", "object_id")
    readonly_fields = ("created_at",)
