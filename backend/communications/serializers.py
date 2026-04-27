from rest_framework import serializers

from appointments.models import Customer
from appointments.serializers import CustomerSerializer
from communications.models import CallSession, Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = (
            "id",
            "conversation",
            "direction",
            "message_type",
            "sender_label",
            "body",
            "provider_message_id",
            "raw_payload",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_conversation(self, value):
        business_client = self.context.get("business_client")
        if business_client and value.business_client_id != business_client.id:
            raise serializers.ValidationError("Razgovor ne pripada ovom klijentu.")
        return value


class ConversationSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        source="customer",
        queryset=Customer.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "customer",
            "customer_id",
            "channel",
            "status",
            "external_thread_id",
            "language",
            "last_message_at",
            "metadata",
            "messages",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "customer", "messages", "created_at", "updated_at")

    def validate_customer_id(self, value):
        if value is None:
            return value
        business_client = self.context.get("business_client")
        if business_client and value.business_client_id != business_client.id:
            raise serializers.ValidationError("Korisnik ne pripada ovom klijentu.")
        return value


class CallSessionSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        source="customer",
        queryset=Customer.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CallSession
        fields = (
            "id",
            "conversation",
            "customer",
            "customer_id",
            "provider",
            "external_call_id",
            "status",
            "from_number",
            "to_number",
            "transcript",
            "recording_url",
            "metadata",
            "started_at",
            "ended_at",
            "created_at",
        )
        read_only_fields = ("id", "customer", "created_at")

    def validate_conversation(self, value):
        if value is None:
            return value
        business_client = self.context.get("business_client")
        if business_client and value.business_client_id != business_client.id:
            raise serializers.ValidationError("Razgovor ne pripada ovom klijentu.")
        return value

    def validate_customer_id(self, value):
        if value is None:
            return value
        business_client = self.context.get("business_client")
        if business_client and value.business_client_id != business_client.id:
            raise serializers.ValidationError("Korisnik ne pripada ovom klijentu.")
        return value
