from django.contrib import admin

from integrations.models import IntegrationConnection


@admin.register(IntegrationConnection)
class IntegrationConnectionAdmin(admin.ModelAdmin):
    list_display = ("business_client", "provider", "enabled", "status", "public_number", "updated_at")
    list_filter = ("provider", "enabled", "status")
    search_fields = ("business_client__name", "public_number")

