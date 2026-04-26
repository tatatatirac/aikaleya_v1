from rest_framework import serializers

from ai_core.models import AlarmSettings, GlobalAISettings, KaleyaCommandLog, VoiceSettings


class GlobalAISettingsSerializer(serializers.ModelSerializer):
    ai_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    voice_api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_ai_api_key = serializers.SerializerMethodField()
    has_voice_api_key = serializers.SerializerMethodField()

    class Meta:
        model = GlobalAISettings
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
            "enabled",
            "updated_at",
        )
        read_only_fields = ("id", "has_ai_api_key", "has_voice_api_key", "updated_at")

    def get_has_ai_api_key(self, obj):
        return bool(obj.ai_api_key)

    def get_has_voice_api_key(self, obj):
        return bool(obj.voice_api_key)


class VoiceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceSettings
        fields = ("id", "language", "voice_id", "speed", "stability", "similarity_boost", "updated_at")
        read_only_fields = ("id", "updated_at")


class AlarmSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlarmSettings
        fields = (
            "id",
            "notifications_enabled",
            "urgent_enabled",
            "announcement_enabled",
            "notification_sound",
            "urgent_sound",
            "announcement_sound",
            "notification_volume",
            "urgent_volume",
            "announcement_volume",
            "updated_at",
        )
        read_only_fields = ("id", "updated_at")


class KaleyaCommandLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = KaleyaCommandLog
        fields = ("id", "command", "input_text", "output_text", "language", "channel", "success", "created_at")
        read_only_fields = ("id", "output_text", "language", "success", "created_at")


class KaleyaCommandSerializer(serializers.Serializer):
    command = serializers.CharField(max_length=120)
    input_text = serializers.CharField(required=False, allow_blank=True)
    channel = serializers.CharField(required=False, default="web", max_length=30)

