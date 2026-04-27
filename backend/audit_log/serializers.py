from rest_framework import serializers

from audit_log.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    business_name = serializers.CharField(source="business_client.name", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "business_client",
            "business_name",
            "actor",
            "actor_email",
            "action",
            "object_type",
            "object_id",
            "channel",
            "ip_address",
            "metadata",
            "created_at",
        )
        read_only_fields = fields
