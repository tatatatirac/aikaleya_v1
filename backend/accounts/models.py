import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class Profile(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_CLIENT = "client"
    ROLE_EMPLOYEE = "employee"

    ROLE_CHOICES = (
        (ROLE_ADMIN, "God Mode admin"),
        (ROLE_CLIENT, "Administrator / company"),
        (ROLE_EMPLOYEE, "Employee"),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    business_client = models.ForeignKey(
        "clients.BusinessClient",
        on_delete=models.SET_NULL,
        related_name="employee_profiles",
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=40, blank=True)
    is_onboarded = models.BooleanField(default=False)
    deletion_scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email or self.user.username} ({self.role})"


class AccountSetupToken(models.Model):
    """One-time token emailed to new owners after payment — lets them set their password."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="setup_token",
    )
    token = models.CharField(max_length=128, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at

    @classmethod
    def generate_for(cls, user, hours=48):
        token = secrets.token_urlsafe(48)
        obj, _ = cls.objects.update_or_create(
            user=user,
            defaults={
                "token": token,
                "expires_at": timezone.now() + timedelta(hours=hours),
                "used_at": None,
            },
        )
        return obj

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    def __str__(self):
        return f"SetupToken({self.user.email}, valid={self.is_valid})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        role = Profile.ROLE_ADMIN if instance.is_staff or instance.is_superuser else Profile.ROLE_CLIENT
        Profile.objects.create(user=instance, role=role)
        return

    if hasattr(instance, "profile"):
        expected_role = Profile.ROLE_ADMIN if instance.is_staff or instance.is_superuser else instance.profile.role
        if instance.profile.role != expected_role:
            instance.profile.role = expected_role
            instance.profile.save(update_fields=["role", "updated_at"])
