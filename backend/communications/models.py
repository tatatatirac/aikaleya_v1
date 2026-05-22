from django.db import models

from appointments.models import Customer
from clients.models import BusinessClient


class Conversation(models.Model):
    CHANNEL_CHOICES = (
        ("phone", "Telefon"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("viber", "Viber"),
        ("telegram", "Telegram"),
        ("email", "Email"),
        ("instagram", "Instagram"),
        ("tiktok", "TikTok"),
        ("web", "Web"),
    )

    STATUS_CHOICES = (
        ("open", "Otvoren"),
        ("waiting", "Ceka odgovor"),
        ("closed", "Zatvoren"),
        ("handoff", "Prebaceno supportu"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="conversations")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, related_name="conversations", null=True, blank=True)
    channel = models.CharField(max_length=30, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="open")
    external_thread_id = models.CharField(max_length=180, blank=True)
    language = models.CharField(max_length=10, default="en")
    last_message_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-last_message_at", "-created_at")
        indexes = [
            models.Index(fields=("business_client", "channel", "status")),
            models.Index(fields=("external_thread_id",)),
        ]

    def __str__(self):
        customer = self.customer.full_name if self.customer else "Nepoznat korisnik"
        return f"{customer} - {self.channel}"


class Message(models.Model):
    DIRECTION_CHOICES = (
        ("inbound", "Dolazna"),
        ("outbound", "Odlazna"),
        ("internal", "Interna"),
    )

    MESSAGE_TYPE_CHOICES = (
        ("text", "Tekst"),
        ("voice", "Glas"),
        ("email", "Email"),
        ("system", "Sistem"),
    )

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    direction = models.CharField(max_length=30, choices=DIRECTION_CHOICES)
    message_type = models.CharField(max_length=30, choices=MESSAGE_TYPE_CHOICES, default="text")
    sender_label = models.CharField(max_length=120, blank=True)
    body = models.TextField(blank=True)
    provider_message_id = models.CharField(max_length=180, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("conversation", "created_at"))]

    def __str__(self):
        return f"{self.direction} - {self.conversation}"


class CallSession(models.Model):
    STATUS_CHOICES = (
        ("ringing", "Zvoni"),
        ("active", "Aktivan"),
        ("transferred", "Prenet na vlasnika"),
        ("completed", "Zavrsen"),
        ("missed", "Propusten"),
        ("failed", "Greska"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="call_sessions")
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        related_name="call_sessions",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, related_name="call_sessions", null=True, blank=True)
    provider = models.CharField(max_length=80, default="manual")
    external_call_id = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="ringing")
    from_number = models.CharField(max_length=60, blank=True)
    to_number = models.CharField(max_length=60, blank=True)
    transcript = models.TextField(blank=True)
    recording_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("business_client", "status", "created_at"))]

    def __str__(self):
        return f"{self.provider} - {self.from_number}"
