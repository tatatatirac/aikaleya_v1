from django.db import models

from appointments.models import Appointment, Customer
from clients.models import BusinessClient


class NotificationRule(models.Model):
    EVENT_CHOICES = (
        ("appointment_created", "Termin zakazan"),
        ("appointment_changed", "Termin promenjen"),
        ("appointment_cancelled", "Termin otkazan"),
        ("reminder_before", "Podsetnik pre termina"),
        ("support_needed", "Potreban support"),
        ("daily_report", "Dnevni izvestaj"),
    )

    CHANNEL_CHOICES = (
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("viber", "Viber"),
        ("email", "Email"),
        ("push", "Push"),
        ("dashboard", "Dashboard"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="notification_rules")
    event = models.CharField(max_length=60, choices=EVENT_CHOICES)
    channel = models.CharField(max_length=30, choices=CHANNEL_CHOICES)
    offset_minutes = models.IntegerField(default=0)
    language = models.CharField(max_length=10, default="en")
    template = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("event", "channel", "offset_minutes")

    def __str__(self):
        return f"{self.business_client} - {self.event} - {self.channel}"


class NotificationJob(models.Model):
    STATUS_CHOICES = (
        ("pending", "Ceka"),
        ("processing", "Obradjuje se"),
        ("sent", "Poslato"),
        ("failed", "Greska"),
        ("cancelled", "Otkazano"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="notification_jobs")
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, related_name="notification_jobs", null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, related_name="notification_jobs", null=True, blank=True)
    channel = models.CharField(max_length=30)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    scheduled_for = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("scheduled_for",)
        indexes = [models.Index(fields=("business_client", "status", "scheduled_for"))]

    def __str__(self):
        return f"{self.business_client} - {self.channel} - {self.status}"
