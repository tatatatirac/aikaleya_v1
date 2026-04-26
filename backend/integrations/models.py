from django.db import models

from clients.models import BusinessClient


class IntegrationConnection(models.Model):
    PROVIDER_CHOICES = (
        ("whatsapp", "WhatsApp"),
        ("viber", "Viber"),
        ("telegram", "Telegram"),
        ("sms", "SMS"),
        ("phone", "Phone Call"),
    )

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("connected", "Connected"),
        ("paused", "Paused"),
        ("error", "Error"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="integrations")
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    enabled = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    public_number = models.CharField(max_length=80, blank=True)
    webhook_url = models.URLField(blank=True)
    config = models.JSONField(default=dict, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("business_client", "provider")
        ordering = ("provider",)

    def __str__(self):
        return f"{self.business_client} - {self.provider}"

