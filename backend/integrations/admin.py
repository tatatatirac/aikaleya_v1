from django import forms
from django.contrib import admin

from integrations.models import IntegrationConnection


class IntegrationConnectionAdminForm(forms.ModelForm):
    class Meta:
        model = IntegrationConnection
        fields = ("business_client", "provider", "enabled", "status", "public_number")
        labels = {
            "business_client": "Klijent",
            "provider": "Kanal / servis",
            "enabled": "Uključeno",
            "status": "Status povezivanja",
            "public_number": "Javni broj ili nalog",
            "webhook_url": "Webhook URL",
            "config": "Napredna konfiguracija",
            "last_error": "Poslednja greška",
        }
        help_texts = {
            "business_client": "Izaberi firmu/klijenta kome ova integracija pripada. Jedan klijent može imati WhatsApp, Viber, Telegram, SMS i telefon.",
            "provider": "Izaberi kanal koji povezuješ. Primer: WhatsApp za poruke, SMS za obične tekstualne poruke, Phone Call za telefonske pozive.",
            "enabled": "Uključi samo kada je integracija spremna za korišćenje. Ako nije podešena do kraja, ostavi isključeno.",
            "status": "Draft znači priprema, Connected znači povezano, Paused znači pauzirano, Error znači da postoji problem koji treba rešiti.",
            "public_number": "Ovde se unosi broj telefona, korisničko ime ili javni nalog koji klijent koristi za ovaj kanal. Primer: +381641234567.",
            "webhook_url": "Adresa na koju spoljni servis šalje događaje ka Kaleya backendu. Za sada može ostati prazno dok ne povežemo pravog providera.",
            "config": "Napredno JSON polje za provider podešavanja. Za sada ostavi {} ako ne znaš tačno šta treba.",
            "last_error": "Ovde se čuva poslednja tehnička greška iz integracije. Ručno se uglavnom ne popunjava.",
        }


@admin.register(IntegrationConnection)
class IntegrationConnectionAdmin(admin.ModelAdmin):
    form = IntegrationConnectionAdminForm
    change_list_template = "admin/integrations/integrationconnection/change_list.html"
    change_form_template = "admin/integrations/integrationconnection/change_form.html"
    list_display = ("client_name", "provider_name", "enabled_name", "status_name", "public_number", "updated_at")
    list_filter = ("provider", "enabled", "status")
    search_fields = ("business_client__name", "public_number")
    fieldsets = (
        (
            "Integracija",
            {
                "description": "Jednostavno podešavanje kanala koji Kaleya sme da koristi za izabranog klijenta.",
                "fields": ("business_client", "provider", "enabled", "status", "public_number"),
            },
        ),
    )

    @admin.display(description="Klijent")
    def client_name(self, obj):
        return obj.business_client

    @admin.display(description="Kanal")
    def provider_name(self, obj):
        return obj.get_provider_display()

    @admin.display(description="Uključeno")
    def enabled_name(self, obj):
        return "Da" if obj.enabled else "Ne"

    @admin.display(description="Status")
    def status_name(self, obj):
        labels = {
            "draft": "Priprema",
            "connected": "Povezano",
            "paused": "Pauzirano",
            "error": "Greška",
        }
        return labels.get(obj.status, obj.status)
