from django.contrib import admin

from support.models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("business_client", "subject", "priority", "status", "created_at")
    list_filter = ("priority", "status")
    search_fields = ("business_client__name", "subject", "message")

