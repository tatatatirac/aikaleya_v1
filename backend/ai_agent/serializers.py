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
    external_thread_id = serializers.CharField(required=False, allow_blank=True)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    appointment_id = serializers.IntegerField(required=False, allow_null=True)
    service_id = serializers.IntegerField(required=False, allow_null=True)
    service_hint = serializers.CharField(required=False, allow_blank=True)
    staff_member_id = serializers.IntegerField(required=False, allow_null=True)
    staff_hint = serializers.CharField(required=False, allow_blank=True)
    date = serializers.DateField(required=False, allow_null=True)
    time = serializers.TimeField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField(required=False, min_value=5, max_value=720)
    title = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    cancelled_reason = serializers.CharField(required=False, allow_blank=True)
    use_ai = serializers.BooleanField(required=False, default=True)
    include_voice = serializers.BooleanField(required=False, default=False)


class TextToSpeechSerializer(serializers.Serializer):
    text = serializers.CharField()
