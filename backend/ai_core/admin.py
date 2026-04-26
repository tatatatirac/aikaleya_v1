from django.contrib import admin

from ai_core.models import AlarmSettings, GlobalAISettings, KaleyaCommandLog, VoiceSettings


@admin.register(GlobalAISettings)
class GlobalAISettingsAdmin(admin.ModelAdmin):
    list_display = ("ai_provider", "ai_model", "voice_provider", "enabled", "updated_at")


@admin.register(VoiceSettings)
class VoiceSettingsAdmin(admin.ModelAdmin):
    list_display = ("business_client", "language", "voice_id", "speed", "updated_at")
    search_fields = ("business_client__name", "voice_id")


@admin.register(AlarmSettings)
class AlarmSettingsAdmin(admin.ModelAdmin):
    list_display = ("business_client", "notifications_enabled", "urgent_enabled", "announcement_enabled", "updated_at")
    search_fields = ("business_client__name",)


@admin.register(KaleyaCommandLog)
class KaleyaCommandLogAdmin(admin.ModelAdmin):
    list_display = ("business_client", "command", "language", "channel", "success", "created_at")
    list_filter = ("command", "language", "channel", "success")
    search_fields = ("business_client__name", "input_text", "output_text")

