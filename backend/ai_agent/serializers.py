from rest_framework import serializers

from ai_agent.models import AIIntent, AIToolRun, CustomerMemory


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


class CustomerMemorySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    last_service_name = serializers.CharField(source="last_service.name", read_only=True)
    preferred_staff_member_name = serializers.CharField(source="preferred_staff_member.full_name", read_only=True)
    favorite_service = serializers.SerializerMethodField()
    favorite_time = serializers.SerializerMethodField()

    class Meta:
        model = CustomerMemory
        fields = (
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "customer_email",
            "summary",
            "routine_notes",
            "preferences",
            "identifiers",
            "last_service",
            "last_service_name",
            "preferred_staff_member",
            "preferred_staff_member_name",
            "appointment_count",
            "cancellation_count",
            "reschedule_count",
            "no_show_risk",
            "favorite_service",
            "favorite_time",
            "last_seen_at",
            "last_appointment_at",
            "source",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "customer_email",
            "preferences",
            "identifiers",
            "last_service",
            "last_service_name",
            "preferred_staff_member",
            "preferred_staff_member_name",
            "appointment_count",
            "cancellation_count",
            "reschedule_count",
            "favorite_service",
            "favorite_time",
            "last_seen_at",
            "last_appointment_at",
            "source",
            "created_at",
            "updated_at",
        )

    def get_favorite_service(self, obj):
        services = (obj.preferences or {}).get("services") or {}
        if not services:
            return ""
        return max(services.items(), key=lambda item: item[1])[0]

    def get_favorite_time(self, obj):
        times = (obj.preferences or {}).get("times") or {}
        if not times:
            return ""
        return max(times.items(), key=lambda item: item[1])[0]


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
