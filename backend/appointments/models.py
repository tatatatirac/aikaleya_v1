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
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_MOVED, "Rescheduled"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_PENDING, "Pending"),
        (STATUS_BLOCKED, "Blocked"),
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
        from appointments.services import aware_client_datetime, blocked_times_for_date, effective_working_hours

        if self.duration_minutes <= 0:
            raise ValidationError({"duration_minutes": "Trajanje termina mora biti vece od 0."})
        if self.service_id and self.duration_minutes == 30:
            self.duration_minutes = self.service.duration_minutes

        work_window = effective_working_hours(
            self.business_client,
            self.date,
            staff_member_id=self.staff_member_id,
        )
        if work_window["is_closed"]:
            raise ValidationError("Izabrani dan je zatvoren za zakazivanje.")
        if self.start_time < work_window["start"] or self.end_time > work_window["end"]:
            raise ValidationError("Termin mora biti unutar radnog vremena klijenta ili zaposlenog.")

        if not self.is_active_booking:
            return

        current_start = datetime.combine(self.date, self.start_time)
        current_end = current_start + timedelta(minutes=self.duration_minutes)
        current_start_aware = aware_client_datetime(self.business_client, self.date, self.start_time)
        current_end_aware = current_start_aware + timedelta(minutes=self.duration_minutes)

        for blocked_time in blocked_times_for_date(self.business_client, self.date, staff_member_id=self.staff_member_id):
            if current_start_aware < blocked_time.end_at and current_end_aware > blocked_time.start_at:
                raise ValidationError("Termin se preklapa sa blokiranim vremenom ili pauzom.")

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
                raise ValidationError("This appointment overlaps with an existing booked slot.")

    def __str__(self):
        label = self.customer.full_name if self.customer else self.title or "Blocked"
        return f"{label} - {self.date} {self.start_time}"
