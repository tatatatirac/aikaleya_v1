from django import forms
from django.contrib import admin

from ai_core.models import AlarmSettings, GlobalAISettings, KaleyaCommandLog, VoiceSettings


class GlobalAISettingsAdminForm(forms.ModelForm):
    class Meta:
        model = GlobalAISettings
        fields = ("enabled", "ai_provider", "ai_model", "ai_api_key", "voice_provider", "voice_model", "voice_api_key")
        labels = {
            "enabled": "AI enabled",
            "ai_provider": "AI provider",
            "ai_model": "AI model",
            "ai_api_key": "AI API key",
            "voice_provider": "Voice provider",
            "voice_model": "Voice model",
            "voice_api_key": "Voice API key",
        }
        help_texts = {
            "ai_provider": "Use anthropic for Claude.",
            "ai_model": "Use claude-haiku-4-5-20251001 for Claude Haiku 4.5.",
            "voice_provider": "Use elevenlabs for ElevenLabs.",
        }


class VoiceSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = VoiceSettings
        fields = ("business_client", "language", "voice_id", "speed", "stability", "similarity_boost")
        labels = {
            "business_client": "Client",
            "language": "Voice language",
            "voice_id": "Voice ID",
            "speed": "Speed",
            "stability": "Stability",
            "similarity_boost": "Voice similarity",
        }
        help_texts = {
            "voice_id": "Voice ID from ElevenLabs voice library.",
            "speed": "1.00 is normal speed.",
            "stability": "Higher value means more stable voice.",
            "similarity_boost": "Higher value attempts to better preserve voice character.",
        }


class AlarmSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = AlarmSettings
        fields = (
            "business_client",
            "notifications_enabled",
            "urgent_enabled",
            "announcement_enabled",
            "notification_sound",
            "urgent_sound",
            "announcement_sound",
            "notification_volume",
            "urgent_volume",
            "announcement_volume",
        )
        labels = {
            "business_client": "Client",
            "notifications_enabled": "Notifications",
            "urgent_enabled": "Urgent alert",
            "announcement_enabled": "Queue announcement",
            "notification_sound": "Notification sound",
            "urgent_sound": "Urgent sound",
            "announcement_sound": "Announcement sound",
            "notification_volume": "Notification volume",
            "urgent_volume": "Urgent volume",
            "announcement_volume": "Announcement volume",
        }


@admin.register(GlobalAISettings)
class GlobalAISettingsAdmin(admin.ModelAdmin):
    form = GlobalAISettingsAdminForm
    list_display = ("ai_provider", "ai_model", "voice_provider", "enabled")
    fieldsets = (
        ("Global AI", {"fields": ("enabled", "ai_provider", "ai_model", "ai_api_key")}),
        ("Global voice", {"fields": ("voice_provider", "voice_model", "voice_api_key")}),
    )


@admin.register(VoiceSettings)
class VoiceSettingsAdmin(admin.ModelAdmin):
    form = VoiceSettingsAdminForm
    list_display = ("business_client", "language", "voice_id", "speed")
    search_fields = ("business_client__name", "voice_id")
    fieldsets = (
        ("Client voice", {"fields": ("business_client", "language", "voice_id")}),
        ("Fine tuning", {"fields": ("speed", "stability", "similarity_boost")}),
    )


@admin.register(AlarmSettings)
class AlarmSettingsAdmin(admin.ModelAdmin):
    form = AlarmSettingsAdminForm
    list_display = ("business_client", "notifications_enabled", "urgent_enabled", "announcement_enabled")
    search_fields = ("business_client__name",)
    fieldsets = (
        ("Enable/disable", {"fields": ("business_client", "notifications_enabled", "urgent_enabled", "announcement_enabled")}),
        ("Sounds", {"fields": ("notification_sound", "urgent_sound", "announcement_sound")}),
        ("Volume", {"fields": ("notification_volume", "urgent_volume", "announcement_volume")}),
    )


@admin.register(KaleyaCommandLog)
class KaleyaCommandLogAdmin(admin.ModelAdmin):
    list_display = ("business_client", "command", "language", "channel", "success", "created_at")
    list_filter = ("command", "language", "channel", "success")
    search_fields = ("business_client__name", "input_text", "output_text")
    readonly_fields = ("business_client", "command", "input_text", "output_text", "language", "channel", "success", "created_at")
    fieldsets = (
        ("Command log", {"fields": ("business_client", "command", "language", "channel", "success", "created_at")}),
        ("Text", {"fields": ("input_text", "output_text")}),
    )

    def has_add_permission(self, request):
        return False
