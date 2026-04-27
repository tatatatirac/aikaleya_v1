from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from clients.models import BusinessClient


class Customer(models.Model):
    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="customers")
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    preferred_channel = models.CharField(max_length=30, default="phone")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("first_name", "last_name")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name


class Appointment(models.Model):
    STATUS_CONFIRMED = "confirmed"
    STATUS_MOVED = "moved"
    STATUS_CANCELLED = "cancelled"
    STATUS_PENDING = "pending"
    STATUS_BLOCKED = "blocked"

    STATUS_CHOICES = (
        (STATUS_CONFIRMED, "Zakazano"),
        (STATUS_MOVED, "Pomereno"),
        (STATUS_CANCELLED, "Otkazano"),
        (STATUS_PENDING, "Za proveru"),
        (STATUS_BLOCKED, "Blokirano"),
    )

    CHANNEL_CHOICES = (
        ("phone", "Phone"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("viber", "Viber"),
        ("telegram", "Telegram"),
        ("email", "Email"),
        ("instagram", "Instagram"),
        ("tiktok", "TikTok"),
        ("web", "Web"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="appointments")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="appointments", null=True, blank=True)
    staff_member = models.ForeignKey(
        "staff_services.StaffMember",
        on_delete=models.SET_NULL,
        related_name="appointments",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        "staff_services.Service",
        on_delete=models.SET_NULL,
        related_name="appointments",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    channel = models.CharField(max_length=30, choices=CHANNEL_CHOICES, default="phone")
    source = models.CharField(max_length=80, default="manual")
    notes = models.TextField(blank=True)
    cancelled_reason = models.CharField(max_length=240, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("date", "start_time")
        indexes = [
            models.Index(fields=("business_client", "date", "start_time")),
            models.Index(fields=("business_client", "status")),
        ]

    @property
    def end_time(self):
        start_dt = datetime.combine(self.date, self.start_time)
        return (start_dt + timedelta(minutes=self.duration_minutes)).time()

    @property
    def is_active_booking(self):
        return self.status in {self.STATUS_CONFIRMED, self.STATUS_MOVED, self.STATUS_PENDING, self.STATUS_BLOCKED}

    def clean(self):
        if self.duration_minutes <= 0:
            raise ValidationError({"duration_minutes": "Trajanje termina mora biti vece od 0."})
        if self.service_id and self.duration_minutes == 30:
            self.duration_minutes = self.service.duration_minutes

        work_start = self.business_client.work_start
        work_end = self.business_client.work_end
        if self.start_time < work_start or self.end_time > work_end:
            raise ValidationError("Termin mora biti unutar radnog vremena klijenta.")

        if not self.is_active_booking:
            return

        current_start = datetime.combine(self.date, self.start_time)
        current_end = current_start + timedelta(minutes=self.duration_minutes)

        appointments = Appointment.objects.filter(
            business_client=self.business_client,
            date=self.date,
            status__in=[self.STATUS_CONFIRMED, self.STATUS_MOVED, self.STATUS_PENDING, self.STATUS_BLOCKED],
        )
        if self.staff_member_id:
            appointments = appointments.filter(Q(staff_member_id=self.staff_member_id) | Q(staff_member__isnull=True))
        if self.pk:
            appointments = appointments.exclude(pk=self.pk)

        for appointment in appointments:
            other_start = datetime.combine(appointment.date, appointment.start_time)
            other_end = other_start + timedelta(minutes=appointment.duration_minutes)
            if current_start < other_end and current_end > other_start:
                raise ValidationError("Termin se preklapa sa postojecim zauzetim slotom.")

    def __str__(self):
        label = self.customer.full_name if self.customer else self.title or "Blokirano"
        return f"{label} - {self.date} {self.start_time}"
