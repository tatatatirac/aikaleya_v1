from django import forms
from django.contrib import admin

from appointments.models import Appointment, Customer


class CustomerAdminForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("business_client", "first_name", "last_name", "phone", "email", "preferred_channel", "notes")
        labels = {
            "business_client": "Klijent",
            "first_name": "Ime",
            "last_name": "Prezime",
            "phone": "Telefon",
            "email": "Email",
            "preferred_channel": "Omiljeni kanal",
            "notes": "Beleške",
        }
        help_texts = {
            "business_client": "Firma kod koje krajnji korisnik zakazuje termin.",
            "preferred_channel": "Primer: phone, sms, whatsapp, viber, telegram.",
            "notes": "Interna beleška, nije obavezna.",
        }


class AppointmentAdminForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = (
            "business_client",
            "customer",
            "title",
            "status",
            "date",
            "start_time",
            "duration_minutes",
            "channel",
            "notes",
            "cancelled_reason",
        )
        labels = {
            "business_client": "Klijent",
            "customer": "Krajnji korisnik",
            "title": "Naslov ako nema korisnika",
            "status": "Status termina",
            "date": "Datum",
            "start_time": "Vreme početka",
            "duration_minutes": "Trajanje",
            "channel": "Kanal",
            "notes": "Beleške",
            "cancelled_reason": "Razlog otkazivanja",
        }
        help_texts = {
            "title": "Koristi se za blokiranje termina ili ručni unos bez osobe.",
            "duration_minutes": "Na primer 30, 60, 120 minuta.",
            "channel": "Preko čega je termin došao: phone, sms, whatsapp, viber, telegram ili web.",
        }


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    form = CustomerAdminForm
    list_display = ("full_name", "business_client", "phone", "email", "preferred_channel")
    list_filter = ("business_client", "preferred_channel")
    search_fields = ("first_name", "last_name", "phone", "email")
    fieldsets = (
        ("Krajnji korisnik", {"fields": ("business_client", "first_name", "last_name", "phone", "email", "preferred_channel")}),
        ("Beleške", {"fields": ("notes",)}),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    form = AppointmentAdminForm
    list_display = ("business_client", "customer", "title", "status", "date", "start_time", "duration_minutes")
    list_filter = ("business_client", "status", "date", "channel")
    search_fields = ("customer__first_name", "customer__last_name", "customer__phone", "title")
    fieldsets = (
        ("Termin", {"fields": ("business_client", "customer", "title", "status")}),
        ("Vreme", {"fields": ("date", "start_time", "duration_minutes")}),
        ("Komunikacija", {"fields": ("channel", "notes", "cancelled_reason")}),
    )
