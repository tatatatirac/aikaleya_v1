from rest_framework import serializers

from billing.services import enforce_channel_allowed, enforce_client_api_override_allowed, enforce_elevenlabs_voice_allowed
from clients.models import BusinessClient, ClientApiSettings


class ClientApiSettingsSerializer(serializers.ModelSerializer):
    has_ai_api_key = serializers.SerializerMethodField()
    has_voice_api_key = serializers.SerializerMethodField()
    ai_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    voice_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ClientApiSettings
        fields = (
            "id",
            "ai_provider",
            "ai_model",
            "ai_api_key",
            "has_ai_api_key",
            "voice_provider",
            "voice_model",
            "voice_api_key",
            "has_voice_api_key",
            "voice_id",
            "updated_at",
        )
        read_only_fields = ("id", "has_ai_api_key", "has_voice_api_key", "updated_at")

    def get_has_ai_api_key(self, obj):
        return bool(obj.ai_api_key)

    def get_has_voice_api_key(self, obj):
        return bool(obj.voice_api_key)

    def validate(self, attrs):
        business_client = attrs.get("business_client") or getattr(self.instance, "business_client", None)
        if not business_client:
            return attrs

        wants_client_ai_override = any(
            key in attrs and str(attrs.get(key) or "").strip()
            for key in ("ai_api_key", "ai_model")
        )
        wants_client_voice_override = any(
            key in attrs and str(attrs.get(key) or "").strip()
            for key in ("voice_api_key", "voice_model", "voice_id")
        )

        if wants_client_ai_override:
            enforce_client_api_override_allowed(business_client)
        if wants_client_voice_override:
            enforce_elevenlabs_voice_allowed(business_client)
        return attrs


class BusinessClientSerializer(serializers.ModelSerializer):
    api_settings = ClientApiSettingsSerializer(read_only=True)
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_phone = serializers.CharField(source="owner.profile.phone", read_only=True)

    class Meta:
        model = BusinessClient
        fields = (
            "id",
            "name",
            "public_name",
            "owner_name",
            "owner_email",
            "owner_phone",
            "package",
            "language",
            "interface_language",
            "voice_language",
            "timezone",
            "kaleya_enabled",
            "work_start",
            "work_end",
            "slot_interval_minutes",
            "time_format",
            "date_format",
            "week_start",
            "allow_phone_calls",
            "allow_sms",
            "allow_whatsapp",
            "allow_viber",
            "allow_telegram",
            "api_settings",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "api_settings")

    def get_owner_name(self, obj):
        full_name = f"{obj.owner.first_name} {obj.owner.last_name}".strip()
        return full_name or obj.owner.email or obj.owner.username

    def validate(self, attrs):
        work_start = attrs.get("work_start", getattr(self.instance, "work_start", None))
        work_end = attrs.get("work_end", getattr(self.instance, "work_end", None))
        slot_interval = attrs.get("slot_interval_minutes", getattr(self.instance, "slot_interval_minutes", 30))
        business_client = self.instance

        if work_start and work_end and work_end <= work_start:
            raise serializers.ValidationError({"work_end": "Kraj radnog vremena mora biti posle pocetka."})
        if slot_interval not in (15, 20, 30, 45, 60):
            raise serializers.ValidationError({"slot_interval_minutes": "Interval termina mora biti 15, 20, 30, 45 ili 60 minuta."})
        if business_client:
            channel_fields = {
                "allow_whatsapp": "whatsapp",
                "allow_viber": "viber",
                "allow_telegram": "telegram",
                "allow_sms": "sms",
                "allow_phone_calls": "phone",
            }
            for field, channel in channel_fields.items():
                if attrs.get(field) is True:
                    enforce_channel_allowed(business_client, channel)
        return attrs
