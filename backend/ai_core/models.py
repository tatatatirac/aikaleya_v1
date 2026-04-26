from django.db import models

from clients.models import BusinessClient


class GlobalAISettings(models.Model):
    ai_provider = models.CharField(max_length=80, default="openai")
    ai_model = models.CharField(max_length=120, default="gpt-4o-mini")
    ai_api_key = models.CharField(max_length=500, blank=True)
    voice_provider = models.CharField(max_length=80, default="elevenlabs")
    voice_model = models.CharField(max_length=120, blank=True)
    voice_api_key = models.CharField(max_length=500, blank=True)
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Global AI settings"

    def __str__(self):
        return f"{self.ai_provider} / {self.ai_model}"


class VoiceSettings(models.Model):
    business_client = models.OneToOneField(BusinessClient, on_delete=models.CASCADE, related_name="voice_settings")
    language = models.CharField(max_length=10, default="en")
    voice_id = models.CharField(max_length=160, blank=True)
    speed = models.DecimalField(max_digits=4, decimal_places=2, default=1.00)
    stability = models.DecimalField(max_digits=4, decimal_places=2, default=0.50)
    similarity_boost = models.DecimalField(max_digits=4, decimal_places=2, default=0.75)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Voice settings: {self.business_client}"


class AlarmSettings(models.Model):
    business_client = models.OneToOneField(BusinessClient, on_delete=models.CASCADE, related_name="alarm_settings")
    notifications_enabled = models.BooleanField(default=True)
    urgent_enabled = models.BooleanField(default=True)
    announcement_enabled = models.BooleanField(default=True)
    notification_sound = models.CharField(max_length=160, default="soft-bell")
    urgent_sound = models.CharField(max_length=160, default="urgent-pulse")
    announcement_sound = models.CharField(max_length=160, default="airport-chime")
    notification_volume = models.PositiveIntegerField(default=55)
    urgent_volume = models.PositiveIntegerField(default=85)
    announcement_volume = models.PositiveIntegerField(default=70)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Alarm settings: {self.business_client}"


class KaleyaCommandLog(models.Model):
    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="kaleya_command_logs")
    command = models.CharField(max_length=120)
    input_text = models.TextField(blank=True)
    output_text = models.TextField(blank=True)
    language = models.CharField(max_length=10, default="en")
    channel = models.CharField(max_length=30, default="web")
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.business_client} - {self.command}"

