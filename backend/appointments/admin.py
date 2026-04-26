from django.contrib import admin

from appointments.models import Appointment, Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "business_client", "phone", "email", "preferred_channel")
    list_filter = ("business_client", "preferred_channel")
    search_fields = ("first_name", "last_name", "phone", "email")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("business_client", "customer", "title", "status", "date", "start_time", "duration_minutes")
    list_filter = ("business_client", "status", "date", "channel")
    search_fields = ("customer__first_name", "customer__last_name", "customer__phone", "title")

