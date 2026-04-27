from rest_framework import serializers

from ai_agent.models import AIIntent, AIToolRun


class AIIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIIntent
        fields = (
            "id",
            "conversation",
            "customer",
            "intent",
            "confidence",
            "input_text",
            "language",
            "raw_response",
            "created_at",
        )
        read_only_fields = fields


class AIToolRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIToolRun
        fields = (
            "id",
            "intent",
            "tool_name",
            "status",
            "input_payload",
            "output_payload",
            "error",
            "created_at",
        )
        read_only_fields = fields


class InboundTextSerializer(serializers.Serializer):
    text = serializers.CharField()
    channel = serializers.CharField(required=False, default="web")
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    customer_id = serializers.IntegerField(required=False, allow_null=True)
