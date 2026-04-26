from rest_framework import serializers

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

