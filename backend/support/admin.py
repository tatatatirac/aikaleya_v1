from django import forms
from django.contrib import admin

from support.models import SupportTicket


class SupportTicketAdminForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ("business_client", "subject", "message", "priority", "status")
        labels = {
            "business_client": "Klijent",
            "subject": "Naslov",
            "message": "Poruka",
            "priority": "Prioritet",
            "status": "Status",
        }
        help_texts = {
            "business_client": "Klijent kome treba human support.",
            "priority": "Normal ili Urgent.",
            "status": "Open, In progress, Resolved ili Closed.",
        }


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    form = SupportTicketAdminForm
    list_display = ("business_client", "subject", "priority", "status", "created_at")
    list_filter = ("priority", "status")
    search_fields = ("business_client__name", "subject", "message")
    fieldsets = (
        ("Support zahtev", {"fields": ("business_client", "subject", "message")}),
        ("Stanje", {"fields": ("priority", "status")}),
    )
