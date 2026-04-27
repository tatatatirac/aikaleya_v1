from rest_framework import serializers

from notifications.models import NotificationJob, NotificationRule


class NotificationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRule
        fields = (
            "id",
            "event",
            "channel",
            "offset_minutes",
            "language",
            "template",
            "is_enabled",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class NotificationJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationJob
        fields = (
            "id",
            "appointment",
            "customer",
            "channel",
            "status",
            "scheduled_for",
            "sent_at",
            "payload",
            "attempts",
            "last_error",
            "created_at",
        )
        read_only_fields = ("id", "sent_at", "attempts", "last_error", "created_at")
