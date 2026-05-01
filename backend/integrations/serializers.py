from rest_framework import serializers

from billing.services import enforce_channel_allowed
from integrations.models import IntegrationConnection


class IntegrationConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationConnection
        fields = (
            "id",
            "provider",
            "enabled",
            "status",
            "public_number",
            "webhook_url",
            "config",
            "last_error",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        business_client = self.context.get("business_client") or getattr(self.instance, "business_client", None)
        provider = attrs.get("provider", getattr(self.instance, "provider", ""))
        enabled = attrs.get("enabled", getattr(self.instance, "enabled", False))
        status = attrs.get("status", getattr(self.instance, "status", "draft"))
        if business_client and (enabled or status == "connected"):
            enforce_channel_allowed(business_client, provider)
        return attrs
