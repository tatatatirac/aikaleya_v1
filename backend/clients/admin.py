from django import forms
from django.contrib import admin

from clients.models import BusinessClient, BusinessKnowledgeEntry, ClientApiSettings


class BusinessClientAdminForm(forms.ModelForm):
    class Meta:
        model = BusinessClient
        fields = (
            "owner",
            "name",
            "public_name",
            "package",
            "is_demo",
            "kaleya_enabled",
            "work_start",
            "work_end",
            "slot_interval_minutes",
            "interface_language",
            "voice_language",
            "time_format",
            "date_format",
            "week_start",
            "allow_phone_calls",
            "allow_sms",
            "allow_whatsapp",
            "allow_viber",
            "allow_telegram",
        )
        labels = {
            "owner": "Client login account",
            "name": "Internal name",
            "public_name": "Display name",
            "package": "Plan",
            "kaleya_enabled": "Kaleya enabled",
            "work_start": "Working hours from",
            "work_end": "Working hours to",
            "slot_interval_minutes": "Appointment length",
            "interface_language": "Interface language",
            "voice_language": "Voice language",
            "time_format": "Time format",
            "date_format": "Date format",
            "week_start": "First day of week",
            "allow_phone_calls": "Phone calls",
            "allow_sms": "SMS",
            "allow_whatsapp": "WhatsApp",
            "allow_viber": "Viber",
            "allow_telegram": "Telegram",
        }
        help_texts = {
            "owner": "User who logs in as this client.",
            "name": "Name for internal administration.",
            "public_name": "Name the client sees in the app.",
            "kaleya_enabled": "Disable if you want Kaleya to temporarily stop working for this client.",
            "slot_interval_minutes": "Usually 30 minutes. Can be 15, 20, 30, 45 or 60.",
            "week_start": "Monday for most countries, Sunday for USA.",
        }


class ClientApiSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = ClientApiSettings
        fields = (
            "business_client",
            "ai_provider",
            "ai_model",
            "ai_api_key",
            "voice_provider",
            "voice_model",
            "voice_api_key",
            "voice_id",
            "master_prompt",
        )
        labels = {
            "business_client": "Client",
            "ai_provider": "AI provider",
            "ai_model": "AI model",
            "ai_api_key": "AI API key",
            "voice_provider": "Voice provider",
            "voice_model": "Voice model",
            "voice_api_key": "Voice API key",
            "voice_id": "Voice ID",
            "master_prompt": "Master prompt",
        }
        help_texts = {
            "ai_provider": "Enter anthropic for Claude. Enter openai for OpenAI.",
            "ai_model": "Use claude-haiku-4-5-20251001 for Claude Haiku 4.5.",
            "ai_api_key": "Private key. Never goes to frontend or GitHub.",
            "voice_provider": "Enter elevenlabs for ElevenLabs.",
            "voice_api_key": "Private ElevenLabs key.",
            "voice_id": "Voice ID from ElevenLabs voice library.",
            "master_prompt": "Additional tone, style and behavior rules for Kaleya for this client.",
        }


@admin.register(BusinessClient)
class BusinessClientAdmin(admin.ModelAdmin):
    form = BusinessClientAdminForm
    list_display = ("display_name", "owner", "package", "is_demo", "kaleya_status", "work_time")
    list_filter = ("package", "is_demo", "kaleya_enabled", "interface_language")
    search_fields = ("name", "public_name", "owner__email", "owner__username")
    fieldsets = (
        ("Client", {"fields": ("owner", "name", "public_name", "package", "is_demo", "kaleya_enabled")}),
        ("Working hours and language", {"fields": ("work_start", "work_end", "slot_interval_minutes", "interface_language", "voice_language", "time_format", "date_format", "week_start")}),
        ("Channels", {"fields": ("allow_phone_calls", "allow_sms", "allow_whatsapp", "allow_viber", "allow_telegram")}),
    )

    @admin.display(description="Client")
    def display_name(self, obj):
        return obj.public_name or obj.name

    @admin.display(description="Kaleya")
    def kaleya_status(self, obj):
        return "Online" if obj.kaleya_enabled else "Offline"

    @admin.display(description="Working hours")
    def work_time(self, obj):
        return f"{obj.work_start:%H:%M}-{obj.work_end:%H:%M}"


@admin.register(ClientApiSettings)
class ClientApiSettingsAdmin(admin.ModelAdmin):
    form = ClientApiSettingsAdminForm
    list_display = ("business_client", "ai_provider", "ai_model", "voice_provider", "has_voice_id")
    search_fields = ("business_client__name", "ai_provider", "ai_model", "voice_provider")
    fieldsets = (
        ("AI", {"description": "Configure the AI model for this client.", "fields": ("business_client", "ai_provider", "ai_model", "ai_api_key", "master_prompt")}),
        ("Voice", {"description": "Configure ElevenLabs or another voice provider.", "fields": ("voice_provider", "voice_model", "voice_api_key", "voice_id")}),
    )

    @admin.display(description="Voice ID")
    def has_voice_id(self, obj):
        return "Set" if obj.voice_id else "Not set"


@admin.register(BusinessKnowledgeEntry)
class BusinessKnowledgeEntryAdmin(admin.ModelAdmin):
    list_display = ("business_client", "title", "category", "language", "is_active")
    list_filter = ("category", "language", "is_active")
    search_fields = ("business_client__name", "business_client__public_name", "title", "answer", "keywords")
    fieldsets = (
        ("Client", {"fields": ("business_client", "category", "language", "is_active")}),
        ("Content", {"fields": ("title", "answer", "keywords")}),
    )
