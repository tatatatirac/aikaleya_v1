from django import forms
from django.contrib import admin

from clients.models import BusinessClient, ClientApiSettings


class BusinessClientAdminForm(forms.ModelForm):
    class Meta:
        model = BusinessClient
        fields = (
            "owner",
            "name",
            "public_name",
            "package",
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
            "owner": "Login nalog klijenta",
            "name": "Interni naziv",
            "public_name": "Naziv koji se prikazuje",
            "package": "Paket",
            "kaleya_enabled": "Kaleya uključena",
            "work_start": "Radno vreme od",
            "work_end": "Radno vreme do",
            "slot_interval_minutes": "Dužina termina",
            "interface_language": "Jezik aplikacije",
            "voice_language": "Jezik glasa",
            "time_format": "Format vremena",
            "date_format": "Format datuma",
            "week_start": "Prvi dan u nedelji",
            "allow_phone_calls": "Telefon",
            "allow_sms": "SMS",
            "allow_whatsapp": "WhatsApp",
            "allow_viber": "Viber",
            "allow_telegram": "Telegram",
        }
        help_texts = {
            "owner": "Korisnik koji se loguje kao ovaj klijent.",
            "name": "Naziv za internu administraciju.",
            "public_name": "Naziv koji klijent vidi u aplikaciji.",
            "kaleya_enabled": "Isključi ako želiš da Kaleya privremeno ne radi za ovog klijenta.",
            "slot_interval_minutes": "Najčešće 30 minuta. Može 15, 20, 30, 45 ili 60.",
            "week_start": "Za Srbiju najčešće Monday, za USA često Sunday.",
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
        )
        labels = {
            "business_client": "Klijent",
            "ai_provider": "AI provider",
            "ai_model": "AI model",
            "ai_api_key": "AI API ključ",
            "voice_provider": "Voice provider",
            "voice_model": "Voice model",
            "voice_api_key": "Voice API ključ",
            "voice_id": "Voice ID",
        }
        help_texts = {
            "ai_provider": "Za Claude upiši anthropic. Za OpenAI upiši openai.",
            "ai_model": "Za Claude Haiku 4.5 koristi claude-haiku-4-5-20251001.",
            "ai_api_key": "Privatan ključ. Ne ide u frontend i ne ide na GitHub.",
            "voice_provider": "Za ElevenLabs upiši elevenlabs.",
            "voice_api_key": "Privatan ElevenLabs ključ.",
            "voice_id": "ID glasa iz ElevenLabs voice library.",
        }


@admin.register(BusinessClient)
class BusinessClientAdmin(admin.ModelAdmin):
    form = BusinessClientAdminForm
    list_display = ("display_name", "owner", "package", "kaleya_status", "work_time")
    list_filter = ("package", "kaleya_enabled", "interface_language")
    search_fields = ("name", "public_name", "owner__email", "owner__username")
    fieldsets = (
        ("Klijent", {"fields": ("owner", "name", "public_name", "package", "kaleya_enabled")}),
        ("Radno vreme i jezik", {"fields": ("work_start", "work_end", "slot_interval_minutes", "interface_language", "voice_language", "time_format", "date_format", "week_start")}),
        ("Kanali", {"fields": ("allow_phone_calls", "allow_sms", "allow_whatsapp", "allow_viber", "allow_telegram")}),
    )

    @admin.display(description="Klijent")
    def display_name(self, obj):
        return obj.public_name or obj.name

    @admin.display(description="Kaleya")
    def kaleya_status(self, obj):
        return "Online" if obj.kaleya_enabled else "Offline"

    @admin.display(description="Radno vreme")
    def work_time(self, obj):
        return f"{obj.work_start:%H:%M}-{obj.work_end:%H:%M}"


@admin.register(ClientApiSettings)
class ClientApiSettingsAdmin(admin.ModelAdmin):
    form = ClientApiSettingsAdminForm
    list_display = ("business_client", "ai_provider", "ai_model", "voice_provider", "has_voice_id")
    search_fields = ("business_client__name", "ai_provider", "ai_model", "voice_provider")
    fieldsets = (
        ("AI", {"description": "Ovde se podešava AI model za izabranog klijenta.", "fields": ("business_client", "ai_provider", "ai_model", "ai_api_key")}),
        ("Glas", {"description": "Ovde se podešava ElevenLabs ili drugi voice provider.", "fields": ("voice_provider", "voice_model", "voice_api_key", "voice_id")}),
    )

    @admin.display(description="Voice ID")
    def has_voice_id(self, obj):
        return "Unet" if obj.voice_id else "Nije unet"
