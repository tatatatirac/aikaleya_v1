from django.contrib import admin

from clients.models import BusinessClient, ClientApiSettings


@admin.register(BusinessClient)
class BusinessClientAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "package", "language", "kaleya_enabled", "work_start", "work_end")
    list_filter = ("package", "language", "kaleya_enabled")
    search_fields = ("name", "public_name", "owner__email", "owner__username")


@admin.register(ClientApiSettings)
class ClientApiSettingsAdmin(admin.ModelAdmin):
    list_display = ("business_client", "ai_provider", "ai_model", "voice_provider", "voice_model", "updated_at")
    search_fields = ("business_client__name", "ai_provider", "ai_model", "voice_provider")

