from django.contrib import admin

from notifications.models import NotificationJob, NotificationRule


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = ("business_client", "event", "channel", "offset_minutes", "language", "is_enabled")
    list_filter = ("business_client", "event", "channel", "is_enabled")


@admin.register(NotificationJob)
class NotificationJobAdmin(admin.ModelAdmin):
    list_display = ("business_client", "channel", "status", "scheduled_for", "sent_at", "attempts")
    list_filter = ("business_client", "channel", "status")
    search_fields = ("last_error",)
