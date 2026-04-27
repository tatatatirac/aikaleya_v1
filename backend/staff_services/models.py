from django.core.exceptions import ValidationError
from django.db import models

from clients.models import BusinessClient


class StaffMember(models.Model):
    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="staff_members")
    full_name = models.CharField(max_length=160)
    role_title = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    color = models.CharField(max_length=20, default="#3b82f6")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("full_name",)
        indexes = [models.Index(fields=("business_client", "is_active"))]

    def __str__(self):
        return self.full_name


class Service(models.Model):
    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="EUR")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("category", "name")
        unique_together = ("business_client", "name")

    def clean(self):
        if self.duration_minutes <= 0:
            raise ValidationError({"duration_minutes": "Trajanje usluge mora biti vece od 0 minuta."})

    def __str__(self):
        return self.name


class StaffService(models.Model):
    staff_member = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="staff_services")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="staff_services")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("staff_member", "service")

    def __str__(self):
        return f"{self.staff_member} - {self.service}"


class WorkingHours(models.Model):
    WEEKDAY_CHOICES = (
        (0, "Ponedeljak"),
        (1, "Utorak"),
        (2, "Sreda"),
        (3, "Cetvrtak"),
        (4, "Petak"),
        (5, "Subota"),
        (6, "Nedelja"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="working_hours")
    staff_member = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        related_name="working_hours",
        null=True,
        blank=True,
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField(default="09:00")
    end_time = models.TimeField(default="16:00")
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ("weekday", "start_time")
        unique_together = ("business_client", "staff_member", "weekday")

    def clean(self):
        if not self.is_closed and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "Kraj radnog vremena mora biti posle pocetka."})

    def __str__(self):
        scope = self.staff_member.full_name if self.staff_member else self.business_client.name
        return f"{scope} - {self.get_weekday_display()}"


class BlockedTime(models.Model):
    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="blocked_times")
    staff_member = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        related_name="blocked_times",
        null=True,
        blank=True,
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=80, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("start_at",)
        indexes = [models.Index(fields=("business_client", "start_at", "end_at"))]

    def clean(self):
        if self.end_at <= self.start_at:
            raise ValidationError({"end_at": "Kraj blokade mora biti posle pocetka."})

    def __str__(self):
        return f"{self.business_client} - {self.start_at}"
