from django import forms
from django.contrib import admin

from integrations.models import IntegrationConnection


class IntegrationConnectionAdminForm(forms.ModelForm):
    class Meta:
        model = IntegrationConnection
        fields = ("business_client", "provider", "enabled", "status", "public_number")
        labels = {
            "business_client": "Client",
            "provider": "Channel / service",
            "enabled": "Enabled",
            "status": "Connection status",
            "public_number": "Public number or account",
            "webhook_url": "Webhook URL",
            "config": "Advanced configuration",
            "last_error": "Last error",
        }
        help_texts = {
            "business_client": "Select the company/client this integration belongs to. One client can have WhatsApp, Viber, Telegram, SMS and phone.",
            "provider": "Select the channel to connect. Example: WhatsApp for messages, SMS for plain text messages, Phone for phone calls.",
            "enabled": "Enable only when the integration is ready to use. If setup is incomplete, leave disabled.",
            "status": "Draft means setup in progress, Connected means live, Paused means paused, Error means there is a problem to resolve.",
            "public_number": "Enter the phone number, username or public account the client uses for this channel. Example: +381641234567.",
            "webhook_url": "URL where the external service sends events to the Kaleya backend. Can be left empty until the provider is connected.",
            "config": "Advanced JSON field for provider settings. Leave {} if you are not sure what to enter.",
            "last_error": "Stores the last technical error from the integration. Usually not filled in manually.",
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
            "Integration",
            {
                "description": "Simple channel setup for the selected client.",
                "fields": ("business_client", "provider", "enabled", "status", "public_number"),
            },
        ),
    )

    @admin.display(description="Client")
    def client_name(self, obj):
        return obj.business_client

    @admin.display(description="Channel")
    def provider_name(self, obj):
        return obj.get_provider_display()

    @admin.display(description="Enabled")
    def enabled_name(self, obj):
        return "Yes" if obj.enabled else "No"

    @admin.display(description="Status")
    def status_name(self, obj):
        labels = {
            "draft": "Draft",
            "connected": "Connected",
            "paused": "Paused",
            "error": "Error",
        }
        return labels.get(obj.status, obj.status)
