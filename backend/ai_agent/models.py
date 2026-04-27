from django.db import models

from appointments.models import Customer
from clients.models import BusinessClient


class AIIntent(models.Model):
    INTENT_CHOICES = (
        ("book_appointment", "Zakazivanje termina"),
        ("reschedule_appointment", "Pomeranje termina"),
        ("cancel_appointment", "Otkazivanje termina"),
        ("check_availability", "Provera slobodnih termina"),
        ("business_info", "Informacije o firmi"),
        ("support_handoff", "Prebacivanje supportu"),
        ("unknown", "Nepoznato"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="ai_intents")
    conversation = models.ForeignKey(
        "communications.Conversation",
        on_delete=models.SET_NULL,
        related_name="ai_intents",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, related_name="ai_intents", null=True, blank=True)
    intent = models.CharField(max_length=60, choices=INTENT_CHOICES, default="unknown")
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    input_text = models.TextField()
    language = models.CharField(max_length=10, default="en")
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("business_client", "intent", "created_at"))]

    def __str__(self):
        return f"{self.intent} - {self.business_client}"


class AIToolRun(models.Model):
    STATUS_CHOICES = (
        ("planned", "Planirano"),
        ("success", "Uspesno"),
        ("failed", "Greska"),
        ("skipped", "Preskoceno"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="ai_tool_runs")
    intent = models.ForeignKey(AIIntent, on_delete=models.SET_NULL, related_name="tool_runs", null=True, blank=True)
    tool_name = models.CharField(max_length=120)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="planned")
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("business_client", "tool_name", "status"))]

    def __str__(self):
        return f"{self.tool_name} - {self.status}"
