from django import forms
from django.contrib import admin

from ai_core.models import AlarmSettings, GlobalAISettings, KaleyaCommandLog, VoiceSettings


class GlobalAISettingsAdminForm(forms.ModelForm):
    class Meta:
        model = GlobalAISettings
        fields = ("enabled", "ai_provider", "ai_model", "ai_api_key", "voice_provider", "voice_model", "voice_api_key")
        labels = {
            "enabled": "AI uključen",
            "ai_provider": "AI provider",
            "ai_model": "AI model",
            "ai_api_key": "AI API ključ",
            "voice_provider": "Voice provider",
            "voice_model": "Voice model",
            "voice_api_key": "Voice API ključ",
        }
        help_texts = {
            "ai_provider": "Za Claude koristi anthropic.",
            "ai_model": "Za Claude Haiku 4.5 koristi claude-haiku-4-5-20251001.",
            "voice_provider": "Za ElevenLabs koristi elevenlabs.",
        }


class VoiceSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = VoiceSettings
        fields = ("business_client", "language", "voice_id", "speed", "stability", "similarity_boost")
        labels = {
            "business_client": "Klijent",
            "language": "Jezik glasa",
            "voice_id": "Voice ID",
            "speed": "Brzina",
            "stability": "Stabilnost",
            "similarity_boost": "Sličnost glasa",
        }
        help_texts = {
            "voice_id": "ID glasa iz ElevenLabs voice library.",
            "speed": "1.00 je normalna brzina.",
            "stability": "Veća vrednost znači stabilniji glas.",
            "similarity_boost": "Veća vrednost pokušava da bolje sačuva karakter glasa.",
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
            "business_client": "Klijent",
            "notifications_enabled": "Obaveštenja",
            "urgent_enabled": "Hitni alarm",
            "announcement_enabled": "Najava reda",
            "notification_sound": "Zvuk obaveštenja",
            "urgent_sound": "Hitni zvuk",
            "announcement_sound": "Zvuk najave",
            "notification_volume": "Jačina obaveštenja",
            "urgent_volume": "Jačina hitnog alarma",
            "announcement_volume": "Jačina najave",
        }


@admin.register(GlobalAISettings)
class GlobalAISettingsAdmin(admin.ModelAdmin):
    form = GlobalAISettingsAdminForm
    list_display = ("ai_provider", "ai_model", "voice_provider", "enabled")
    fieldsets = (
        ("Globalni AI", {"fields": ("enabled", "ai_provider", "ai_model", "ai_api_key")}),
        ("Globalni glas", {"fields": ("voice_provider", "voice_model", "voice_api_key")}),
    )


@admin.register(VoiceSettings)
class VoiceSettingsAdmin(admin.ModelAdmin):
    form = VoiceSettingsAdminForm
    list_display = ("business_client", "language", "voice_id", "speed")
    search_fields = ("business_client__name", "voice_id")
    fieldsets = (
        ("Glas klijenta", {"fields": ("business_client", "language", "voice_id")}),
        ("Fino podešavanje", {"fields": ("speed", "stability", "similarity_boost")}),
    )


@admin.register(AlarmSettings)
class AlarmSettingsAdmin(admin.ModelAdmin):
    form = AlarmSettingsAdminForm
    list_display = ("business_client", "notifications_enabled", "urgent_enabled", "announcement_enabled")
    search_fields = ("business_client__name",)
    fieldsets = (
        ("Uključi/isključi", {"fields": ("business_client", "notifications_enabled", "urgent_enabled", "announcement_enabled")}),
        ("Zvukovi", {"fields": ("notification_sound", "urgent_sound", "announcement_sound")}),
        ("Jačina", {"fields": ("notification_volume", "urgent_volume", "announcement_volume")}),
    )


@admin.register(KaleyaCommandLog)
class KaleyaCommandLogAdmin(admin.ModelAdmin):
    list_display = ("business_client", "command", "language", "channel", "success", "created_at")
    list_filter = ("command", "language", "channel", "success")
    search_fields = ("business_client__name", "input_text", "output_text")
    readonly_fields = ("business_client", "command", "input_text", "output_text", "language", "channel", "success", "created_at")
    fieldsets = (
        ("Log komande", {"fields": ("business_client", "command", "language", "channel", "success", "created_at")}),
        ("Tekst", {"fields": ("input_text", "output_text")}),
    )

    def has_add_permission(self, request):
        return False
