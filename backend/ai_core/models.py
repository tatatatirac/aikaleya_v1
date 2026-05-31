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


class AlarmEvent(models.Model):
    """
    A queued alarm/announcement that the dashboard (and optionally
    WhatsApp/SMS) will play for staff. Created either by the appointment
    scheduler (5-min "next in line") or by the voice pipeline ([TRANSFER]).
    """

    KIND_NEXT_IN_LINE = "next_in_line"   # "Ana is next in line at 10:30"
    KIND_URGENT = "urgent"               # "Ana wants to speak with you" (transfer)
    KIND_NOTIFICATION = "notification"   # generic info bell

    KIND_CHOICES = (
        (KIND_NEXT_IN_LINE, "Next in line"),
        (KIND_URGENT, "Urgent — direct conversation requested"),
        (KIND_NOTIFICATION, "Notification"),
    )

    business_client = models.ForeignKey(
        BusinessClient, on_delete=models.CASCADE, related_name="alarm_events"
    )
    kind = models.CharField(max_length=30, choices=KIND_CHOICES, default=KIND_NOTIFICATION)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)

    # TTS line the dashboard speaks aloud (already localized)
    speak_text = models.TextField(blank=True)
    speak_lang = models.CharField(max_length=10, default="en")

    # Optional links
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        related_name="alarm_events",
        null=True, blank=True,
    )
    target_staff = models.ForeignKey(
        "staff_services.StaffMember",
        on_delete=models.SET_NULL,
        related_name="alarm_events",
        null=True, blank=True,
    )

    # Lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    # Which channels we already dispatched to (e.g. ["dashboard", "whatsapp"])
    channels = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("business_client", "dismissed_at", "-created_at")),
            models.Index(fields=("appointment", "kind")),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.title}"

