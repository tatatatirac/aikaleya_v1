from django import forms
from django.contrib import admin

from appointments.models import Appointment, Customer


class CustomerAdminForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("business_client", "first_name", "last_name", "phone", "email", "preferred_channel", "notes")
        labels = {
            "business_client": "Client",
            "first_name": "First name",
            "last_name": "Last name",
            "phone": "Phone",
            "email": "Email",
            "preferred_channel": "Preferred channel",
            "notes": "Notes",
        }
        help_texts = {
            "business_client": "The business where this customer books appointments.",
            "preferred_channel": "Example: phone, sms, whatsapp, viber, telegram.",
            "notes": "Internal note, optional.",
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
            "business_client": "Client",
            "customer": "Customer",
            "title": "Title if no customer",
            "status": "Appointment status",
            "date": "Date",
            "start_time": "Start time",
            "duration_minutes": "Duration",
            "channel": "Channel",
            "notes": "Notes",
            "cancelled_reason": "Cancellation reason",
        }
        help_texts = {
            "title": "Used to block a slot or add an appointment manually without a customer.",
            "duration_minutes": "For example 30, 60, 120 minutes.",
            "channel": "Channel through which the appointment came: phone, sms, whatsapp, viber, telegram or web.",
        }


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    form = CustomerAdminForm
    list_display = ("full_name", "business_client", "phone", "email", "preferred_channel")
    list_filter = ("business_client", "preferred_channel")
    search_fields = ("first_name", "last_name", "phone", "email")
    fieldsets = (
        ("Customer", {"fields": ("business_client", "first_name", "last_name", "phone", "email", "preferred_channel")}),
        ("Notes", {"fields": ("notes",)}),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    form = AppointmentAdminForm
    list_display = ("business_client", "customer", "title", "status", "date", "start_time", "duration_minutes")
    list_filter = ("business_client", "status", "date", "channel")
    search_fields = ("customer__first_name", "customer__last_name", "customer__phone", "title")
    fieldsets = (
        ("Appointment", {"fields": ("business_client", "customer", "title", "status")}),
        ("Time", {"fields": ("date", "start_time", "duration_minutes")}),
        ("Communication", {"fields": ("channel", "notes", "cancelled_reason")}),
    )
