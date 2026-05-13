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


class CustomerMemory(models.Model):
    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"

    RISK_CHOICES = (
        (RISK_LOW, "Low"),
        (RISK_MEDIUM, "Medium"),
        (RISK_HIGH, "High"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="customer_memories")
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="ai_memory")
    summary = models.TextField(blank=True)
    routine_notes = models.TextField(blank=True)
    preferences = models.JSONField(default=dict, blank=True)
    identifiers = models.JSONField(default=dict, blank=True)
    last_service = models.ForeignKey(
        "staff_services.Service",
        on_delete=models.SET_NULL,
        related_name="customer_memories",
        null=True,
        blank=True,
    )
    preferred_staff_member = models.ForeignKey(
        "staff_services.StaffMember",
        on_delete=models.SET_NULL,
        related_name="customer_memories",
        null=True,
        blank=True,
    )
    appointment_count = models.PositiveIntegerField(default=0)
    cancellation_count = models.PositiveIntegerField(default=0)
    reschedule_count = models.PositiveIntegerField(default=0)
    no_show_risk = models.CharField(max_length=20, choices=RISK_CHOICES, default=RISK_LOW)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_appointment_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=80, default="kaleya_ai")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("customer__first_name", "customer__last_name")
        indexes = [
            models.Index(fields=("business_client", "no_show_risk")),
            models.Index(fields=("business_client", "updated_at")),
        ]

    def __str__(self):
        return f"{self.customer.full_name} memory"
